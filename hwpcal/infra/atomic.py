"""원자적 파일 쓰기: 같은 폴더의 임시 파일에 쓰고 fsync 후 rename(설계 §4.3).

어느 시점에 프로세스가 죽어도 대상 파일은 이전 내용 전체이거나 새 내용 전체다.
"""

import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

_REPLACE_RETRIES_WIN32 = 5
_REPLACE_RETRY_DELAY = 0.05


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """text를 path에 원자적으로 쓴다. 줄바꿈은 항상 LF."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    _fsync_dir(path.parent)


def atomic_write_json(path: Path, data: Any) -> None:
    """data를 사람이 읽기 좋은 JSON(UTF-8, 들여쓰기 2, 한글 그대로)으로 원자적으로 쓴다."""
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, text)


def _replace(src: Path, dst: Path) -> None:
    # Windows에서는 백신·인덱서가 대상 파일을 잠깐 잡고 있어 PermissionError가 날 수 있다.
    attempts = _REPLACE_RETRIES_WIN32 if sys.platform == "win32" else 1
    for attempt in range(1, attempts + 1):
        try:
            src.replace(dst)
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(_REPLACE_RETRY_DELAY * 2 ** (attempt - 1))
        else:
            return


def _fsync_dir(directory: Path) -> None:
    # 디렉터리 항목(rename 결과)까지 디스크에 반영. Windows는 디렉터리 fsync를 지원하지 않는다.
    # 플랫폼 분기를 if 블록 안에 두어야 mypy가 어느 OS에서도 도달 불가 문을 보고하지 않는다.
    if sys.platform != "win32":
        _fsync_dir_posix(directory)


def _fsync_dir_posix(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)
