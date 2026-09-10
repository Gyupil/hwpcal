import json
import os
from pathlib import Path

import pytest

from hwpcal.infra.atomic import atomic_write_json, atomic_write_text


def _entries(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def test_write_then_replace_leaves_no_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "f.json"
    atomic_write_json(target, {"a": 1})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}

    atomic_write_json(target, {"a": 2})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 2}
    assert _entries(tmp_path) == ["f.json"]


def test_creates_missing_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c.txt"
    atomic_write_text(target, "x")
    assert target.read_text(encoding="utf-8") == "x"


def test_json_is_utf8_lf_and_newline_terminated(tmp_path: Path) -> None:
    target = tmp_path / "k.json"
    atomic_write_json(target, {"제목": "회의", "n": [1, 2]})
    raw = target.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")
    assert "회의".encode() in raw  # ensure_ascii=False
    assert json.loads(raw.decode("utf-8")) == {"제목": "회의", "n": [1, 2]}


def test_failure_keeps_original_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "f.txt"
    atomic_write_text(target, "original")

    def boom(src: object, dst: object) -> None:
        raise OSError("simulated rename failure")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="simulated"):
        atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "original"
    assert _entries(tmp_path) == ["f.txt"]
