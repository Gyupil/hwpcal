"""앱 이름과 버전.

버전의 단일 출처는 pyproject.toml이다(설계 §13). 소스 체크아웃에서는 pyproject.toml을
직접 읽고, 설치본·배포본(PyInstaller)에서는 패키지 메타데이터를 읽는다.
"""

import tomllib
from importlib import metadata
from pathlib import Path

APP_NAME = "hwpcal"
APP_DISPLAY_NAME = "HwpCal"
UNKNOWN_VERSION = "0.0.0+unknown"


def _version_from_pyproject() -> str | None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project")
    if not isinstance(project, dict) or project.get("name") != APP_NAME:
        return None
    version = project.get("version")
    return version if isinstance(version, str) and version else None


def _version_from_metadata() -> str | None:
    try:
        return metadata.version(APP_NAME)
    except metadata.PackageNotFoundError:
        return None


def resolve_version() -> str:
    """현재 실행 중인 코드의 버전 문자열을 구한다. 알 수 없으면 UNKNOWN_VERSION."""
    return _version_from_pyproject() or _version_from_metadata() or UNKNOWN_VERSION


__version__ = resolve_version()
