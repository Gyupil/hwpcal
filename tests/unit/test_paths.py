import os
import sys
from pathlib import Path

import pytest

from hwpcal.infra.paths import ENV_DATA_DIR, AppPaths, default_data_dir, resolve_paths


def test_layout_derives_from_data_dir(tmp_path: Path) -> None:
    paths = AppPaths(tmp_path)
    assert paths.config_file == tmp_path / "config.json"
    assert paths.processed_file == tmp_path / "processed.json"
    assert paths.log_dir == tmp_path / "logs"
    assert paths.log_file == tmp_path / "logs" / "hwpcal.log"
    assert paths.lock_file == tmp_path / "hwpcal.lock"


def test_ensure_creates_data_and_log_dirs(tmp_path: Path) -> None:
    paths = AppPaths(tmp_path / "nested" / "hwpcal").ensure()
    assert paths.data_dir.is_dir()
    assert paths.log_dir.is_dir()
    # 두 번 불러도 문제 없음
    assert paths.ensure() is paths


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path / "from-env"))
    assert resolve_paths().data_dir == (tmp_path / "from-env").resolve()


def test_explicit_override_beats_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path / "from-env"))
    assert resolve_paths(tmp_path / "explicit").data_dir == (tmp_path / "explicit").resolve()


def test_empty_env_var_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, "")
    assert resolve_paths().data_dir == default_data_dir().resolve()


def test_default_dir_follows_os_convention(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_DATA_DIR, raising=False)
    data_dir = resolve_paths().data_dir
    assert data_dir.name == "hwpcal"
    if sys.platform == "darwin":
        expected = Path.home() / "Library" / "Application Support" / "hwpcal"
        assert data_dir == expected.resolve()
    elif sys.platform == "win32":
        expected = Path(os.environ["LOCALAPPDATA"]) / "hwpcal"
        assert data_dir == expected.resolve()
