from pathlib import Path

import pytest

from hwpcal.infra.jsondoc import JsonDocumentError, migrate_document, read_json_document


def test_read_missing_file(tmp_path: Path) -> None:
    with pytest.raises(JsonDocumentError, match="읽을 수 없습니다"):
        read_json_document(tmp_path / "nope.json", label="테스트")


def test_read_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(JsonDocumentError, match="올바른 JSON이 아닙니다"):
        read_json_document(path, label="테스트")


def test_read_non_object(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(JsonDocumentError, match="JSON 객체"):
        read_json_document(path, label="테스트")


def test_read_object(tmp_path: Path) -> None:
    path = tmp_path / "ok.json"
    path.write_text('{"version": 1, "x": "한글"}', encoding="utf-8")
    assert read_json_document(path, label="테스트") == {"version": 1, "x": "한글"}


def test_migrate_current_version_is_noop() -> None:
    raw = {"version": 2, "a": 1}
    out, changed = migrate_document(raw, current_version=2, migrations={}, label="문서")
    assert out == raw
    assert changed is False


@pytest.mark.parametrize("bad", [None, "1", True, 0, -3, 1.0])
def test_migrate_rejects_bad_version(bad: object) -> None:
    with pytest.raises(JsonDocumentError, match="version 값이 올바르지 않습니다"):
        migrate_document({"version": bad}, current_version=1, migrations={}, label="문서")


def test_migrate_rejects_newer_version() -> None:
    with pytest.raises(JsonDocumentError, match="더 새로운 앱"):
        migrate_document({"version": 3}, current_version=2, migrations={}, label="문서")


def test_migrate_runs_steps_in_order() -> None:
    calls: list[int] = []

    def step1(doc: dict[str, object]) -> dict[str, object]:
        calls.append(1)
        return {**doc, "from1": True}

    def step2(doc: dict[str, object]) -> dict[str, object]:
        calls.append(2)
        return {**doc, "from2": True}

    out, changed = migrate_document(
        {"version": 1, "keep": "me"},
        current_version=3,
        migrations={1: step1, 2: step2},
        label="문서",
    )
    assert calls == [1, 2]
    assert changed is True
    assert out == {"version": 3, "keep": "me", "from1": True, "from2": True}


def test_migrate_missing_step_raises() -> None:
    with pytest.raises(JsonDocumentError, match="올리는 방법이 없습니다"):
        migrate_document({"version": 1}, current_version=2, migrations={}, label="문서")
