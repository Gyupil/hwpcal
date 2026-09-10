import json
import re
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from hwpcal.core.clock import KST
from hwpcal.core.models import Account
from hwpcal.infra import config as config_module
from hwpcal.infra.config import (
    CONFIG_VERSION,
    DEFAULT_FILENAME_DATE_REGEX,
    AppConfig,
    ConfigError,
    ParseConfig,
    PolicyConfig,
    WatchConfig,
    load_config,
    save_config,
)


def _account(account_id: str = "a1", **overrides: object) -> Account:
    base: dict[str, object] = {
        "id": account_id,
        "email": f"{account_id}@example.com",
        "added_at": datetime(2026, 9, 10, 9, 0, tzinfo=KST),
    }
    return Account.model_validate({**base, **overrides})


# ---------------------------------------------------------------- 파일 입출력


def test_missing_file_creates_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config = load_config(path)

    assert config == AppConfig()
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == CONFIG_VERSION
    assert data["watch"] == {
        "folder": None,
        "recursive": False,
        "polling": False,
        "extensions": [".hwp", ".hwpx"],
    }
    assert data["parse"]["filename_date_regex"] == DEFAULT_FILENAME_DATE_REGEX
    assert data["policy"] == {
        "missing": "confirm",
        "missing_threshold": 2,
        "default_duration_min": 60,
        "match_window_days": 7,
    }
    assert data["accounts"] == []
    assert data["matcher"] == {"llm": False}
    assert data["dev_mode"] is False


def test_missing_file_without_create_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="설정 파일이 없습니다"):
        load_config(tmp_path / "config.json", create=False)


def test_roundtrip_preserves_accounts(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(accounts=[_account("a1"), _account("a2", enabled=False)])
    config.watch.folder = "C:\\일정"
    config.policy.missing = "threshold"
    save_config(path, config)

    loaded = load_config(path)
    assert loaded == config
    assert loaded.watch.folder == "C:\\일정"
    assert [a.id for a in loaded.enabled_accounts()] == ["a1"]

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["accounts"][0]["added_at"] == "2026-09-10T09:00:00+09:00"


def test_corrupt_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError, match="올바른 JSON이 아닙니다"):
        load_config(path)


def test_unknown_key_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 1, "devmode": True}), encoding="utf-8")
    with pytest.raises(ConfigError, match="devmode"):
        load_config(path)


def test_newer_version_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": CONFIG_VERSION + 1}), encoding="utf-8")
    with pytest.raises(ConfigError, match="더 새로운 앱"):
        load_config(path)


def test_migration_is_applied_and_saved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": 1, "dev_mode": True}), encoding="utf-8")

    def to_v2(doc: dict[str, object]) -> dict[str, object]:
        return {**doc, "matcher": {"llm": True}}

    monkeypatch.setattr(config_module, "CONFIG_VERSION", 2)
    monkeypatch.setattr(config_module, "_MIGRATIONS", {1: to_v2})

    config = load_config(path)
    assert config.version == 2
    assert config.matcher.llm is True
    assert config.dev_mode is True
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 2


# ---------------------------------------------------------------- 검증 규칙


def test_extensions_are_normalized() -> None:
    watch = WatchConfig(extensions=["HWP", ".Hwpx", " hwp ", ".json"])
    assert watch.extensions == [".hwp", ".hwpx", ".json"]


@pytest.mark.parametrize("bad", [[], [""], ["."], ["  "]])
def test_extensions_must_be_non_empty(bad: list[str]) -> None:
    with pytest.raises(ValidationError, match="확장자"):
        WatchConfig(extensions=bad)


def test_default_regex_extracts_date_from_filename() -> None:
    match = re.search(DEFAULT_FILENAME_DATE_REGEX, "일정_20260910.hwp")
    assert match is not None
    assert match.groups() == ("2026", "09", "10")
    match = re.search(DEFAULT_FILENAME_DATE_REGEX, "2026-09-11 주간일정.hwpx")
    assert match is not None
    assert match.groups() == ("2026", "09", "11")


def test_invalid_regex_rejected() -> None:
    with pytest.raises(ValidationError, match="정규식 오류"):
        ParseConfig(filename_date_regex="(unclosed")


def test_regex_needs_three_groups() -> None:
    with pytest.raises(ValidationError, match="그룹이 3개"):
        ParseConfig(filename_date_regex=r"(\d{4})(\d{2})")


def test_policy_bounds() -> None:
    with pytest.raises(ValidationError):
        PolicyConfig(missing_threshold=0)
    with pytest.raises(ValidationError):
        PolicyConfig(default_duration_min=0)
    with pytest.raises(ValidationError):
        PolicyConfig(match_window_days=-1)
    with pytest.raises(ValidationError):
        PolicyConfig.model_validate({"missing": "sometimes"})


def test_duplicate_account_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="계정 id가 중복"):
        AppConfig(accounts=[_account("a1"), _account("a1")])


def test_naive_added_at_is_treated_as_kst() -> None:
    account = _account(added_at=datetime(2026, 9, 10, 9, 0))
    assert account.added_at.tzinfo is not None
    assert account.added_at.utcoffset() == datetime(2026, 9, 10, tzinfo=KST).utcoffset()


def test_wrong_version_value_rejected() -> None:
    with pytest.raises(ValidationError, match="version은"):
        AppConfig(version=CONFIG_VERSION + 5)
