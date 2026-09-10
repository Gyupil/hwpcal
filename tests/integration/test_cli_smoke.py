"""실제 프로세스로 `python -m hwpcal`을 띄워 설정·로그 파일이 생기는지 본다(M0 완료 기준)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from hwpcal.infra.version import __version__

pytestmark = pytest.mark.integration


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "hwpcal", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=120,
        check=False,
    )


def test_module_entry_creates_config_and_log(tmp_path: Path) -> None:
    data_dir = tmp_path / "smoke"
    result = _run("--data-dir", str(data_dir))
    assert result.returncode == 0, result.stderr
    assert (data_dir / "config.json").is_file()
    log = data_dir / "logs" / "hwpcal.log"
    assert log.is_file()
    assert "시작" in log.read_text(encoding="utf-8")
    assert "시작" in result.stderr


def test_module_entry_version() -> None:
    result = _run("--version")
    assert result.returncode == 0, result.stderr
    assert __version__ in result.stdout
