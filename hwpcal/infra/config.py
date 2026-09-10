"""config.json(설계 §4.4): 스키마 버전, 검증, 기본값 생성, 원자적 저장.

토큰은 여기 없다(keyring, §10.2). 알 수 없는 키는 거부해 오타와 스키마 불일치를 바로 드러낸다.
"""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from hwpcal.core.models import Account
from hwpcal.infra.atomic import atomic_write_json
from hwpcal.infra.jsondoc import (
    JsonDocumentError,
    Migration,
    migrate_document,
    read_json_document,
)

CONFIG_VERSION = 1
DEFAULT_FILENAME_DATE_REGEX = r"(\d{4})[.\-_]?(\d{2})[.\-_]?(\d{2})"
DEFAULT_EXTENSIONS: tuple[str, ...] = (".hwp", ".hwpx")

MissingPolicy = Literal["immediate", "confirm", "threshold"]


class ConfigError(JsonDocumentError):
    """설정 파일을 읽거나 해석할 수 없을 때."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class WatchConfig(_StrictModel):
    """감시 폴더 설정(§5)."""

    folder: str | None = None
    recursive: bool = False
    polling: bool = False
    extensions: list[str] = Field(default_factory=lambda: list(DEFAULT_EXTENSIONS))

    @field_validator("extensions")
    @classmethod
    def _normalize_extensions(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in value:
            ext = raw.strip().lower()
            if not ext or ext == ".":
                raise ValueError("빈 확장자는 허용하지 않습니다")
            if not ext.startswith("."):
                ext = "." + ext
            if ext not in normalized:
                normalized.append(ext)
        if not normalized:
            raise ValueError("확장자가 하나 이상 필요합니다")
        return normalized


class ParseConfig(_StrictModel):
    """파서 설정(§6). 파일명에서 기준일을 뽑는 정규식은 연·월·일 그룹 3개를 가져야 한다."""

    filename_date_regex: str = DEFAULT_FILENAME_DATE_REGEX

    @field_validator("filename_date_regex")
    @classmethod
    def _regex_compiles(cls, value: str) -> str:
        try:
            pattern = re.compile(value)
        except re.error as exc:
            raise ValueError(f"정규식 오류: {exc}") from exc
        if pattern.groups < 3:
            raise ValueError("연, 월, 일을 잡는 그룹이 3개 필요합니다")
        return value


class PolicyConfig(_StrictModel):
    """삭제 정책과 시간 정책(§7.5, §8.4)."""

    missing: MissingPolicy = "confirm"
    missing_threshold: int = Field(default=2, ge=1)
    default_duration_min: int = Field(default=60, ge=1)
    match_window_days: int = Field(default=7, ge=0)


class MatcherConfig(_StrictModel):
    llm: bool = False


class AppConfig(_StrictModel):
    """config.json 전체."""

    version: int = CONFIG_VERSION
    watch: WatchConfig = Field(default_factory=WatchConfig)
    parse: ParseConfig = Field(default_factory=ParseConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    accounts: list[Account] = Field(default_factory=list)
    matcher: MatcherConfig = Field(default_factory=MatcherConfig)
    dev_mode: bool = False

    @field_validator("version")
    @classmethod
    def _version_is_current(cls, value: int) -> int:
        if value != CONFIG_VERSION:
            raise ValueError(f"version은 {CONFIG_VERSION}이어야 합니다 (받은 값: {value})")
        return value

    @field_validator("accounts")
    @classmethod
    def _account_ids_unique(cls, accounts: list[Account]) -> list[Account]:
        seen: set[str] = set()
        for account in accounts:
            if account.id in seen:
                raise ValueError(f"계정 id가 중복됩니다: {account.id}")
            seen.add(account.id)
        return accounts

    def enabled_accounts(self) -> list[Account]:
        return [account for account in self.accounts if account.enabled]


_MIGRATIONS: dict[int, Migration] = {}
"""version N -> N+1 마이그레이션. 스키마를 바꿀 때 CONFIG_VERSION을 올리고 여기 함수를 넣는다."""


def load_config(path: Path, *, create: bool = True) -> AppConfig:
    """config.json을 읽는다. 없으면(create=True) 기본값으로 만들어 저장한 뒤 돌려준다."""
    if not path.exists():
        if not create:
            raise ConfigError(f"설정 파일이 없습니다: {path}")
        config = AppConfig()
        save_config(path, config)
        return config
    try:
        raw = read_json_document(path, label="설정")
        raw, migrated = migrate_document(
            raw, current_version=CONFIG_VERSION, migrations=_MIGRATIONS, label="설정 파일"
        )
    except JsonDocumentError as exc:
        raise ConfigError(str(exc)) from exc
    try:
        config = AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"설정 파일 내용이 올바르지 않습니다: {path}\n{exc}") from exc
    if migrated:
        save_config(path, config)
    return config


def save_config(path: Path, config: AppConfig) -> None:
    """config를 원자적으로 저장한다."""
    atomic_write_json(path, config.model_dump(mode="json"))
