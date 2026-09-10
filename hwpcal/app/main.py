"""엔트리 포인트.

M0: 저장 위치를 준비하고 로그·설정·처리 기록을 초기화한 뒤 종료한다.
단일 인스턴스(QLockFile), 트레이, 워커는 M4~M5에서 이 위에 얹는다.
"""

import argparse
import logging
import sys
from collections.abc import Sequence

from hwpcal.infra.config import ConfigError, load_config
from hwpcal.infra.logging import setup_logging
from hwpcal.infra.paths import ENV_DATA_DIR, AppPaths, resolve_paths
from hwpcal.infra.processed import ProcessedError, ProcessedStore
from hwpcal.infra.version import APP_DISPLAY_NAME, __version__

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hwpcal",
        description="HWP 일정표를 Google Calendar에 자동 동기화합니다.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_DISPLAY_NAME} {__version__}")
    parser.add_argument(
        "--data-dir",
        metavar="PATH",
        help=f"설정·로그를 둘 폴더 (기본: OS별 앱 데이터 폴더, 환경변수 {ENV_DATA_DIR})",
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=LOG_LEVELS, help="로그 수준 (기본 INFO)"
    )
    parser.add_argument("--quiet", action="store_true", help="콘솔(stderr)에 로그를 찍지 않음")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = resolve_paths(args.data_dir).ensure()
    except OSError as exc:
        print(f"데이터 폴더를 준비할 수 없습니다: {exc}", file=sys.stderr)
        return EXIT_ERROR

    log = setup_logging(paths, level=args.log_level, console=not args.quiet)
    try:
        return run(paths, log)
    except Exception:
        log.exception("예상하지 못한 오류로 종료합니다")
        return EXIT_ERROR


def run(paths: AppPaths, log: logging.Logger) -> int:
    log.info("%s %s 시작", APP_DISPLAY_NAME, __version__)
    log.info("데이터 폴더: %s", paths.data_dir)

    try:
        config = load_config(paths.config_file)
    except ConfigError as exc:
        log.error("설정 파일 오류: %s", exc)
        return EXIT_CONFIG

    try:
        processed = ProcessedStore.load(paths.processed_file)
    except ProcessedError as exc:
        log.error("처리 기록 오류: %s", exc)
        return EXIT_CONFIG

    log.info(
        "설정 로드 완료: 감시 폴더=%s, 계정 %d개(활성 %d개), 삭제 정책=%s",
        config.watch.folder or "(미지정)",
        len(config.accounts),
        len(config.enabled_accounts()),
        config.policy.missing,
    )
    log.info("처리 기록: 파일 %d개", len(processed))
    log.info("골격(M0) 실행 완료. 감시·동기화 기능은 다음 마일스톤에서 추가됩니다.")
    return EXIT_OK
