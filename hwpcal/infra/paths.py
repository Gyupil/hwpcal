"""저장 위치(설계 §12).

Windows `%LOCALAPPDATA%\\hwpcal\\`, macOS `~/Library/Application Support/hwpcal/`.
개발·테스트용으로 환경변수 HWPCAL_DATA_DIR 또는 명시적 경로로 바꿀 수 있다.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import platformdirs

from hwpcal.infra.version import APP_NAME

ENV_DATA_DIR = "HWPCAL_DATA_DIR"

CONFIG_FILENAME = "config.json"
PROCESSED_FILENAME = "processed.json"
LOG_DIRNAME = "logs"
LOG_FILENAME = "hwpcal.log"
LOCK_FILENAME = "hwpcal.lock"


@dataclass(frozen=True)
class AppPaths:
    """앱이 사용하는 모든 파일 경로. data_dir 하나에서 파생된다."""

    data_dir: Path

    @property
    def config_file(self) -> Path:
        return self.data_dir / CONFIG_FILENAME

    @property
    def processed_file(self) -> Path:
        return self.data_dir / PROCESSED_FILENAME

    @property
    def log_dir(self) -> Path:
        return self.data_dir / LOG_DIRNAME

    @property
    def log_file(self) -> Path:
        return self.log_dir / LOG_FILENAME

    @property
    def lock_file(self) -> Path:
        return self.data_dir / LOCK_FILENAME

    def ensure(self) -> "AppPaths":
        """데이터 폴더와 로그 폴더를 만든다(이미 있으면 그대로)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return self


def default_data_dir() -> Path:
    """OS 규약에 따른 기본 데이터 폴더."""
    return Path(platformdirs.user_data_dir(APP_NAME, appauthor=False, roaming=False))


def resolve_paths(override: str | os.PathLike[str] | None = None) -> AppPaths:
    """우선순위: 명시적 override > 환경변수 HWPCAL_DATA_DIR > OS 기본 폴더."""
    env_value = os.environ.get(ENV_DATA_DIR)
    if override is not None:
        base = Path(override)
    elif env_value:
        base = Path(env_value)
    else:
        base = default_data_dir()
    return AppPaths(base.expanduser().resolve())
