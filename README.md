# HwpCal

HWP/HWPX 일정표 파일을 폴더에서 자동 인식해 Google Calendar(기본 캘린더)에 변경분만 반영하는
트레이 상주 앱입니다. Windows 배포가 목표이며, 개발과 테스트는 macOS에서 합니다.
코드는 100% 크로스플랫폼이고 패키징만 Windows에서 합니다.

현재 단계: **M0 프로젝트 골격** (설계 문서 §15 참조).

## 개발 환경

필요한 것은 [uv](https://docs.astral.sh/uv/) 하나입니다. Python 3.12은 uv가 `.python-version`을
읽어 자동으로 설치합니다.

```bash
uv sync                      # 가상환경 + 의존성 + 개발 도구
uv run pre-commit install    # 커밋 전에 ruff / mypy 자동 실행
```

## 실행

```bash
uv run hwpcal                          # = python -m hwpcal
uv run hwpcal --data-dir ./tmp-data    # 설정·로그 위치를 바꿔서 실행
uv run hwpcal --log-level DEBUG
uv run hwpcal --version
```

M0의 앱은 데이터 폴더를 만들고 `config.json`(기본값)과 `logs/hwpcal.log`를 생성한 뒤 종료합니다.

## 검사

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pytest --cov            # 커버리지 포함
```

CI(GitHub Actions)는 macOS와 Windows에서 같은 명령을 실행하고, 빈 앱을 실제로 띄워
설정·로그 파일이 생기는지 확인합니다.

## 데이터 위치

| OS | 폴더 |
|---|---|
| Windows | `%LOCALAPPDATA%\hwpcal\` |
| macOS | `~/Library/Application Support/hwpcal/` |

안에는 `config.json`, `processed.json`, `logs/hwpcal.log`(5MB × 5 회전), `hwpcal.lock`이 놓입니다.
환경변수 `HWPCAL_DATA_DIR` 또는 `--data-dir`로 바꿀 수 있습니다.

## 저장소 구조

```
hwpcal/
  app/        엔트리 포인트, (M5) 트레이·설정창·마법사
  core/       도메인 모델과 순수 로직 (M1~)
  adapters/   parsers / calendar / watcher / auth 구현체 (M2~)
  infra/      paths, logging, config, processed, version 등 기반 코드
tests/        unit / integration / fixtures
```
