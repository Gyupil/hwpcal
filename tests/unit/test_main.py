import json
from pathlib import Path

import pytest

from hwpcal.app import main as main_module
from hwpcal.app.main import EXIT_CONFIG, EXIT_ERROR, EXIT_OK, main
from hwpcal.infra.paths import ENV_DATA_DIR
from hwpcal.infra.version import __version__


def test_empty_app_creates_config_and_log(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    assert main(["--data-dir", str(data_dir), "--quiet"]) == EXIT_OK

    config = data_dir / "config.json"
    log = data_dir / "logs" / "hwpcal.log"
    assert config.is_file()
    assert log.is_file()
    assert json.loads(config.read_text(encoding="utf-8"))["version"] == 1
    text = log.read_text(encoding="utf-8")
    assert f"HwpCal {__version__} 시작" in text
    assert "설정 로드 완료" in text
    # processed.json은 기록이 생길 때 만들어진다
    assert not (data_dir / "processed.json").exists()


def test_running_twice_is_idempotent(tmp_path: Path) -> None:
    args = ["--data-dir", str(tmp_path), "--quiet"]
    assert main(args) == EXIT_OK
    first = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert main(args) == EXIT_OK
    assert (tmp_path / "config.json").read_text(encoding="utf-8") == first


def test_data_dir_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path / "env-data"))
    assert main(["--quiet"]) == EXIT_OK
    assert (tmp_path / "env-data" / "config.json").is_file()


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_corrupt_config_returns_config_exit_code(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{broken", encoding="utf-8")
    assert main(["--data-dir", str(tmp_path), "--quiet"]) == EXIT_CONFIG
    assert "설정 파일 오류" in (tmp_path / "logs" / "hwpcal.log").read_text(encoding="utf-8")


def test_corrupt_processed_returns_config_exit_code(tmp_path: Path) -> None:
    (tmp_path / "processed.json").write_text("[]", encoding="utf-8")
    assert main(["--data-dir", str(tmp_path), "--quiet"]) == EXIT_CONFIG
    assert "처리 기록 오류" in (tmp_path / "logs" / "hwpcal.log").read_text(encoding="utf-8")


def test_unexpected_error_is_logged_and_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(path: Path) -> None:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(main_module, "load_config", boom)
    assert main(["--data-dir", str(tmp_path), "--quiet"]) == EXIT_ERROR
    text = (tmp_path / "logs" / "hwpcal.log").read_text(encoding="utf-8")
    assert "예상하지 못한 오류" in text
    assert "kaboom" in text


def test_console_logging_goes_to_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--data-dir", str(tmp_path)]) == EXIT_OK
    captured = capsys.readouterr()
    assert "시작" in captured.err
    assert captured.out == ""
