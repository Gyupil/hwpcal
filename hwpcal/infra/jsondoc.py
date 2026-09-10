"""버전이 붙은 JSON 문서(config.json, processed.json)의 공통 읽기·마이그레이션."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]
Migration = Callable[[JsonDict], JsonDict]
"""version N 문서를 받아 version N+1 문서를 돌려주는 함수. version 키는 호출자가 갱신한다."""


class JsonDocumentError(Exception):
    """JSON 문서를 읽거나 해석할 수 없을 때."""


def read_json_document(path: Path, *, label: str) -> JsonDict:
    """path의 JSON 객체를 읽는다. 읽기 실패·JSON 오류·최상위가 객체가 아니면 예외."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JsonDocumentError(f"{label} 파일을 읽을 수 없습니다: {path} ({exc})") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise JsonDocumentError(f"{label} 파일이 올바른 JSON이 아닙니다: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise JsonDocumentError(f"{label} 파일의 최상위는 JSON 객체여야 합니다: {path}")
    return data


def migrate_document(
    raw: JsonDict,
    *,
    current_version: int,
    migrations: Mapping[int, Migration],
    label: str,
) -> tuple[JsonDict, bool]:
    """raw["version"]을 current_version까지 단계별로 올린다.

    돌려주는 값: (문서, 변경 여부). 더 새로운 버전이거나 version이 이상하면 예외.
    """
    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise JsonDocumentError(f"{label}의 version 값이 올바르지 않습니다: {version!r}")
    if version > current_version:
        raise JsonDocumentError(
            f"{label}이(가) 더 새로운 앱에서 만들어졌습니다"
            f" (version={version}, 이 앱은 {current_version}까지 지원). 앱을 업데이트하세요."
        )
    changed = False
    while version < current_version:
        step = migrations.get(version)
        if step is None:
            raise JsonDocumentError(
                f"{label} version {version}에서 {version + 1}로 올리는 방법이 없습니다"
            )
        raw = step(dict(raw))
        version += 1
        raw["version"] = version
        changed = True
    return raw, changed
