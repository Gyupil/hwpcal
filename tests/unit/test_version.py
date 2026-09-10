import re
import tomllib
from pathlib import Path

import pytest

from hwpcal.infra import version as version_module
from hwpcal.infra.version import UNKNOWN_VERSION, __version__, resolve_version


def test_version_looks_like_pep440() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", __version__), __version__


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    assert __version__ == data["project"]["version"]


def test_package_exposes_version() -> None:
    import hwpcal

    assert hwpcal.__version__ == __version__


def test_fallback_when_nothing_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(version_module, "_version_from_pyproject", lambda: None)
    monkeypatch.setattr(version_module, "_version_from_metadata", lambda: None)
    assert resolve_version() == UNKNOWN_VERSION


def test_pyproject_reader_ignores_foreign_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_pkg = tmp_path / "pkg" / "infra" / "version.py"
    fake_pkg.parent.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "other"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    monkeypatch.setattr(version_module, "__file__", str(fake_pkg))
    assert version_module._version_from_pyproject() is None
