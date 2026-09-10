"""processed.json(설계 §4.3): 처리한 파일의 기록.

역할: 같은 내용의 파일을 두 번 처리하지 않기, 계정별 미완료 추적, 처리 기록 UI.
이 파일이 지워져도 파이프라인은 멱등이므로 결과는 같다(API 호출만 늘어남).
"""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from hwpcal.infra.atomic import atomic_write_json
from hwpcal.infra.jsondoc import (
    JsonDocumentError,
    Migration,
    migrate_document,
    read_json_document,
)

PROCESSED_VERSION = 1

FileStatus = Literal["ok", "partial", "failed"]
"""ok: 모든 enabled 계정 성공 / partial: 일부 계정 미완료 / failed: 파싱 실패(§9.3)."""

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProcessedError(JsonDocumentError):
    """processed.json을 읽거나 해석할 수 없을 때."""


class FileRecord(BaseModel):
    """파일 한 개의 처리 결과. 키는 파일 내용의 SHA-256."""

    model_config = ConfigDict(extra="forbid")

    path: str
    base_date: date
    mtime: float
    processed_at: datetime
    status: FileStatus
    accounts_done: list[str] = Field(default_factory=list)
    accounts_pending: list[str] = Field(default_factory=list)
    items: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class ProcessedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = PROCESSED_VERSION
    files: dict[str, FileRecord] = Field(default_factory=dict)


_MIGRATIONS: dict[int, Migration] = {}


class ProcessedStore:
    """processed.json의 메모리 사본. 바꾼 뒤 save()를 불러야 디스크에 원자적으로 반영된다."""

    def __init__(self, path: Path, document: ProcessedDocument | None = None) -> None:
        self.path = path
        self._doc = document if document is not None else ProcessedDocument()

    @classmethod
    def load(cls, path: Path) -> Self:
        """파일이 없으면 빈 저장소(디스크에 만들지 않음). 손상되었으면 ProcessedError."""
        if not path.exists():
            return cls(path)
        try:
            raw = read_json_document(path, label="처리 기록")
            raw, migrated = migrate_document(
                raw, current_version=PROCESSED_VERSION, migrations=_MIGRATIONS, label="처리 기록"
            )
        except JsonDocumentError as exc:
            raise ProcessedError(str(exc)) from exc
        try:
            document = ProcessedDocument.model_validate(raw)
        except ValidationError as exc:
            raise ProcessedError(f"처리 기록 내용이 올바르지 않습니다: {path}\n{exc}") from exc
        store = cls(path, document)
        if migrated:
            store.save()
        return store

    def save(self) -> None:
        atomic_write_json(self.path, self._doc.model_dump(mode="json"))

    def get(self, sha256: str) -> FileRecord | None:
        return self._doc.files.get(sha256)

    def put(self, sha256: str, record: FileRecord) -> None:
        if not _SHA256_RE.fullmatch(sha256):
            raise ValueError(f"SHA-256 소문자 16진수 64자가 아닙니다: {sha256!r}")
        self._doc.files[sha256] = record

    def remove(self, sha256: str) -> bool:
        """기록을 지운다. 있었으면 True."""
        return self._doc.files.pop(sha256, None) is not None

    def is_done(self, sha256: str) -> bool:
        """status가 ok인 기록이 있으면 True. Watcher는 이런 파일을 건너뛴다(§5-4)."""
        record = self.get(sha256)
        return record is not None and record.status == "ok"

    def records(self) -> dict[str, FileRecord]:
        """모든 기록의 사본(sha256 -> FileRecord)."""
        return dict(self._doc.files)

    def __len__(self) -> int:
        return len(self._doc.files)

    def __contains__(self, sha256: object) -> bool:
        return sha256 in self._doc.files
