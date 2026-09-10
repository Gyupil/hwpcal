import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from hwpcal.infra.logging import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    setup_logging,
    teardown_logging,
)
from hwpcal.infra.paths import AppPaths


def _file_handlers() -> list[RotatingFileHandler]:
    return [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]


def _stream_handlers() -> list[logging.StreamHandler[Any]]:
    return [
        h
        for h in logging.getLogger().handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    ]


def test_creates_log_file_with_kst_timestamp(app_paths: AppPaths) -> None:
    log = setup_logging(app_paths, console=False)
    log.info("안녕 %s", "hwpcal")
    for handler in _file_handlers():
        handler.flush()

    text = app_paths.log_file.read_text(encoding="utf-8")
    assert "안녕 hwpcal" in text
    assert "+09:00" in text
    assert "INFO" in text
    assert "hwpcal" in text


def test_rotation_settings_follow_design(app_paths: AppPaths) -> None:
    setup_logging(app_paths, console=False)
    (handler,) = _file_handlers()
    assert handler.maxBytes == LOG_MAX_BYTES == 5 * 1024 * 1024
    assert handler.backupCount == LOG_BACKUP_COUNT == 5
    assert handler.baseFilename == str(app_paths.log_file)


def test_setup_is_idempotent(app_paths: AppPaths) -> None:
    before_streams = len(_stream_handlers())
    setup_logging(app_paths, console=True)
    setup_logging(app_paths, console=True)
    assert len(_file_handlers()) == 1
    assert len(_stream_handlers()) == before_streams + 1


def test_console_handler_is_optional(app_paths: AppPaths) -> None:
    before_streams = len(_stream_handlers())
    setup_logging(app_paths, console=False)
    assert len(_stream_handlers()) == before_streams


def test_teardown_removes_managed_handlers(app_paths: AppPaths) -> None:
    other = logging.NullHandler()
    logging.getLogger().addHandler(other)
    try:
        setup_logging(app_paths, console=True)
        teardown_logging()
        assert _file_handlers() == []
        assert other in logging.getLogger().handlers
    finally:
        logging.getLogger().removeHandler(other)


def test_level_accepts_name(app_paths: AppPaths) -> None:
    setup_logging(app_paths, level="DEBUG", console=False)
    assert logging.getLogger().level == logging.DEBUG
