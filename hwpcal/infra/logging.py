"""로그 설정(설계 §12): logs/hwpcal.log, 5MB x 5 회전, KST 타임스탬프(전제 D).

setup_logging()은 여러 번 불러도 핸들러가 중복되지 않는다. 테스트는 teardown_logging()으로
파일 핸들러를 닫는다(Windows에서는 열린 로그 파일이 있으면 임시 폴더를 지울 수 없다).
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from hwpcal.core.clock import KST
from hwpcal.infra.paths import AppPaths

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

_managed_handlers: list[logging.Handler] = []


class KstFormatter(logging.Formatter):
    """asctime을 머신 로컬 시간이 아니라 KST(+09:00) ISO 8601로 찍는다."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        moment = datetime.fromtimestamp(record.created, tz=KST)
        if datefmt:
            return moment.strftime(datefmt)
        return moment.isoformat(timespec="milliseconds")


def setup_logging(
    paths: AppPaths, *, level: int | str = logging.INFO, console: bool = True
) -> logging.Logger:
    """루트 로거에 회전 파일 핸들러(와 선택적으로 stderr 핸들러)를 단다."""
    teardown_logging()
    paths.log_dir.mkdir(parents=True, exist_ok=True)

    formatter = KstFormatter(LOG_FORMAT)
    root = logging.getLogger()
    root.setLevel(level)

    file_handler = RotatingFileHandler(
        paths.log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    _attach(root, file_handler)

    if console and sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        _attach(root, stream_handler)

    logging.captureWarnings(True)
    return logging.getLogger("hwpcal")


def teardown_logging() -> None:
    """setup_logging()이 단 핸들러를 모두 떼고 닫는다."""
    root = logging.getLogger()
    while _managed_handlers:
        handler = _managed_handlers.pop()
        root.removeHandler(handler)
        handler.close()


def _attach(root: logging.Logger, handler: logging.Handler) -> None:
    root.addHandler(handler)
    _managed_handlers.append(handler)
