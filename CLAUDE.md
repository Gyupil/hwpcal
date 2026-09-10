# CLAUDE.md

hwpcal 저장소에서 작업할 때의 지침. 설계 문서와 함께 읽는다.

## 프로젝트

- HWP/HWPX 일정표 파일을 폴더에서 자동 인식해 Google Calendar(기본 캘린더)에 변경분만 반영하는
  트레이 상주 앱. Windows 배포가 목표, 개발·테스트는 macOS. 코드는 100% 크로스플랫폼.
- 설계 문서: `docs/design_v0.2.md`. `docs/`는 `.gitignore` 대상이라 저장소에는 없고 로컬에만 있다.
  구현 전에 해당 절(§)을 읽고, 설계와 다르게 하려면 먼저 설명한다.
- 마일스톤(§15)은 순서대로 진행한다. 이전 단계 산출물 위에서만 작업하고, 완료 기준을 만족해야 다음으로 간다.
  - M0 프로젝트 골격: 완료 (2026-09-10)
  - M1 코어 도메인 + FakeGateway: 다음

## 명령

```bash
uv sync                      # Python 3.12 + 의존성 + 개발 도구 (.python-version 참조)
uv run pre-commit install    # 최초 1회

uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest                # --cov 로 커버리지, --real-api 로 실제 Google API 테스트

uv run hwpcal --data-dir ./tmp-data   # 빈 앱 실행 (= uv run python -m hwpcal)
```

커밋 전에 위 검사 4개가 모두 통과해야 한다. CI(`.github/workflows/ci.yml`)는 macOS와 Windows에서
같은 검사를 돌리고 빈 앱 스모크 실행까지 한다.

## 구조와 원칙

```
hwpcal/
  app/        엔트리 포인트(main.py), 트레이·설정창·마법사(M5)
  core/       도메인 모델과 순수 로직. 파서·매처·게이트웨이는 인터페이스로만 의존
  adapters/   parsers / calendar / watcher / auth 구현체
  infra/      paths, logging, config, processed, atomic, jsondoc, version
tests/        unit / integration / fixtures
```

- Windows 전용 API를 쓰지 않는다. 플랫폼 분기는 `sys.platform`으로 최소화한다.
- 파일 쓰기는 `infra/atomic.py`(임시 파일 → fsync → rename)를 통한다.
- 시간대는 Asia/Seoul 고정. `core/clock.py`의 `KST`, `now()`를 쓴다. Windows용 `tzdata` 의존성이 그 이유다.
- 사용자에게 보이는 문구와 로그 메시지는 한국어. 식별자는 영어.
- 로컬 상태는 `config.json`, `processed.json` 뿐이다. 스키마를 바꾸면 `*_VERSION`을 올리고
  `_MIGRATIONS`에 단계 함수를 추가한다. 알 수 없는 키는 거부한다(`extra="forbid"`).
- 의존성은 그것을 쓰는 마일스톤에서 추가한다(M0에는 pydantic, platformdirs, tzdata만).
- 새 코드는 테스트와 함께 넣는다. mypy strict, ruff 규칙은 `pyproject.toml`이 기준이다.
- 로그 핸들러를 여는 테스트는 `teardown_logging()`으로 닫힌다(conftest autouse). Windows에서
  열린 로그 파일이 있으면 임시 폴더를 지울 수 없다.

## Git 워크플로

- `main`: 보호 브랜치. 릴리스 상태만 둔다.
- `develop`: 통합 브랜치. 모든 작업은 `develop` 또는 `develop`에서 딴 `feat/<주제>`, `fix/<주제>`
  브랜치에서 한다.
- **Claude는 `main`에 직접 커밋·병합·푸시하지 않는다.** `develop` → `main` 병합은 사용자만 결정하고
  실행한다. 요청받아도 "main과 병합"은 사용자에게 되묻는다.
- force push와 히스토리 재작성은 하지 않는다.
- 커밋과 푸시는 사용자가 요청할 때 한다.
- 릴리스 태그 `vX.Y.Z`는 `pyproject.toml`의 `version`과 같아야 한다.

## 커밋 컨벤션

[Conventional Commits](https://www.conventionalcommits.org/) 형식을 따른다.

```
<type>(<scope>): <subject>

<body>

<footer>
```

- `type`: `feat` 기능 · `fix` 버그 수정 · `docs` 문서 · `test` 테스트만 · `refactor` 동작 변화 없는 구조 변경 ·
  `chore` 빌드·설정·의존성 · `ci` CI 설정 · `perf` 성능 · `style` 포맷만
- `scope`(선택): `app`, `core`, `adapters`, `infra`, `tests`, `ci`, `docs` 또는 모듈명(`config`, `differ`).
  마일스톤 단위 작업이면 `m1`처럼 쓴다.
- `subject`: 한국어, 50자 이내, 마침표 없음. "~ 추가", "~ 수정", "~ 제거"처럼 끝낸다.
- `body`(선택): 무엇을 왜 바꿨는지. 72자에서 줄바꿈. 설계 절(§8.2)과 마일스톤(M1)을 인용한다.
- `footer`(선택): `BREAKING CHANGE: ...`, `Refs: #12`. Claude가 만든 커밋은 `Co-Authored-By` 트레일러를 남긴다.
- 커밋 하나에 논리적 변경 하나. 포맷팅만 바꾼 커밋은 섞지 않는다.

예시:

```
feat(core): ExactKeyMatcher와 Differ 규칙 추가

§7.6 정확 매처와 §8.2 diff 규칙을 구현한다. 순서 가드(§8.3)는
hwpcal_src 문자열 비교로 처리한다. M1.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

## 개발 환경 발견 사항

### iCloud Drive 동기화 폴더의 `.venv` (2026-09-10)

이 저장소는 `~/Desktop` 아래에 있고 `~/Desktop`은 iCloud Drive가 동기화한다. iCloud 데몬(bird)은
`.`으로 시작하는 항목이 생기면 약 30초 뒤 그 안의 모든 파일에 macOS `hidden` 플래그(UF_HIDDEN)를
재귀적으로 붙인다. Python 3.12.8+/3.13.1+의 `site`는 hidden 플래그가 있는 `.pth` 파일을 보안상 무시하므로
hatchling 편집 가능 설치(`_editable_impl_hwpcal.pth`)가 풀린다.

- 증상: `uv run hwpcal`이 `ModuleNotFoundError: No module named 'hwpcal'`. `uv run python -m hwpcal`과
  `uv run pytest`는 현재 폴더가 `sys.path`에 있어서 정상 동작. `python -v`에 "Skipping hidden .pth file".
- 코드 문제가 아니다. 이 증상을 보면 코드를 의심하기 전에 아래를 먼저 실행한다.

```bash
chflags -R nohidden .venv                              # 즉시 복구. iCloud가 다시 붙일 수 있음
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/hwpcal"    # 가상환경을 동기화 폴더 밖에 두기(권장)
```

또는 저장소를 iCloud 밖(예: `~/dev`)으로 옮긴다. CI에는 영향이 없다.

### Windows CI 콘솔 인코딩

GitHub Actions Windows 러너의 콘솔 인코딩은 cp1252다. 한글 로그를 stderr로 확인하는 서브프로세스 테스트는
자식 프로세스에 `PYTHONUTF8=1`을 준다(`tests/integration/test_cli_smoke.py`). 로그 파일은 항상 UTF-8이다.
