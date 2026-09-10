"""공통 픽스처.

- app_paths: 임시 데이터 폴더를 가리키는 AppPaths(환경변수도 같이 설정).
- 모든 테스트 뒤에 로그 핸들러를 닫는다(Windows 임시 폴더 정리 문제 방지).
- real_api 마커는 --real-api 옵션이 있을 때만 실행한다.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from hwpcal.infra.logging import teardown_logging
from hwpcal.infra.paths import ENV_DATA_DIR, AppPaths


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--real-api",
        action="store_true",
        default=False,
        help="실제 Google API를 호출하는 테스트(real_api 마커)를 실행한다",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--real-api"):
        return
    skip = pytest.mark.skip(reason="--real-api 옵션이 없어 건너뜀")
    for item in items:
        if "real_api" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def app_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppPaths:
    data_dir = tmp_path / "hwpcal-data"
    monkeypatch.setenv(ENV_DATA_DIR, str(data_dir))
    return AppPaths(data_dir).ensure()


@pytest.fixture(autouse=True)
def _close_log_handlers() -> Iterator[None]:
    yield
    teardown_logging()
