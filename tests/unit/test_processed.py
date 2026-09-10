import json
from datetime import date, datetime
from pathlib import Path

import pytest

from hwpcal.core.clock import KST
from hwpcal.infra.processed import (
    PROCESSED_VERSION,
    FileRecord,
    FileStatus,
    ProcessedError,
    ProcessedStore,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def _record(status: FileStatus = "ok", **overrides: object) -> FileRecord:
    base: dict[str, object] = {
        "path": "C:\\일정\\일정_20260910.hwp",
        "base_date": date(2026, 9, 10),
        "mtime": 1789000000.0,
        "processed_at": datetime(2026, 9, 10, 9, 1, 22, tzinfo=KST),
        "status": status,
        "accounts_done": ["a1"],
        "accounts_pending": [],
        "items": 12,
        "warnings": ["3행: 시각 없음, 종일 처리"],
    }
    return FileRecord.model_validate({**base, **overrides})


def test_load_missing_file_is_empty_and_does_not_create(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    store = ProcessedStore.load(path)
    assert len(store) == 0
    assert store.records() == {}
    assert not path.exists()


def test_put_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    store = ProcessedStore.load(path)
    store.put(SHA_A, _record())
    store.put(SHA_B, _record("partial", accounts_done=[], accounts_pending=["a1"]))
    store.save()

    loaded = ProcessedStore.load(path)
    assert len(loaded) == 2
    assert loaded.get(SHA_A) == _record()
    partial = loaded.get(SHA_B)
    assert partial is not None
    assert partial.accounts_pending == ["a1"]
    assert SHA_A in loaded
    assert "c" * 64 not in loaded
    assert loaded.get("c" * 64) is None


def test_json_shape_matches_design(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    store = ProcessedStore.load(path)
    store.put(SHA_A, _record())
    store.save()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == PROCESSED_VERSION
    entry = data["files"][SHA_A]
    assert entry["path"] == "C:\\일정\\일정_20260910.hwp"
    assert entry["base_date"] == "2026-09-10"
    assert entry["mtime"] == 1789000000.0
    assert entry["processed_at"] == "2026-09-10T09:01:22+09:00"
    assert entry["status"] == "ok"
    assert entry["accounts_done"] == ["a1"]
    assert entry["accounts_pending"] == []
    assert entry["items"] == 12
    assert entry["warnings"] == ["3행: 시각 없음, 종일 처리"]


def test_is_done_only_for_ok(tmp_path: Path) -> None:
    store = ProcessedStore.load(tmp_path / "processed.json")
    store.put(SHA_A, _record("ok"))
    store.put(SHA_B, _record("partial"))
    assert store.is_done(SHA_A) is True
    assert store.is_done(SHA_B) is False
    assert store.is_done("c" * 64) is False


def test_remove(tmp_path: Path) -> None:
    store = ProcessedStore.load(tmp_path / "processed.json")
    store.put(SHA_A, _record())
    assert store.remove(SHA_A) is True
    assert store.remove(SHA_A) is False
    assert len(store) == 0


@pytest.mark.parametrize("bad", ["", "abc", "A" * 64, "g" * 64, "a" * 63])
def test_put_rejects_non_sha256_keys(tmp_path: Path, bad: str) -> None:
    store = ProcessedStore.load(tmp_path / "processed.json")
    with pytest.raises(ValueError, match="SHA-256"):
        store.put(bad, _record())


def test_records_returns_copy(tmp_path: Path) -> None:
    store = ProcessedStore.load(tmp_path / "processed.json")
    store.put(SHA_A, _record())
    copy = store.records()
    copy.clear()
    assert len(store) == 1


def test_corrupt_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    path.write_text("nope", encoding="utf-8")
    with pytest.raises(ProcessedError, match="올바른 JSON이 아닙니다"):
        ProcessedStore.load(path)


def test_newer_version_raises(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    path.write_text(json.dumps({"version": PROCESSED_VERSION + 1, "files": {}}), encoding="utf-8")
    with pytest.raises(ProcessedError, match="더 새로운 앱"):
        ProcessedStore.load(path)


def test_invalid_status_raises(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    entry = _record().model_dump(mode="json") | {"status": "done"}
    path.write_text(json.dumps({"version": 1, "files": {SHA_A: entry}}), encoding="utf-8")
    with pytest.raises(ProcessedError, match="올바르지 않습니다"):
        ProcessedStore.load(path)


def test_save_is_atomic_leaves_no_temp(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    store = ProcessedStore.load(path)
    store.put(SHA_A, _record())
    store.save()
    store.save()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["processed.json"]
