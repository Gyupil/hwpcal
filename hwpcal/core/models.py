"""도메인 모델(설계 §4.1).

M0에서는 설정 파일이 필요로 하는 Account만 둔다. ScheduleItem, ParseResult,
NormalizedItem, RemoteEvent는 M1에서 추가한다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hwpcal.core.clock import KST


class Account(BaseModel):
    """등록된 Google 계정의 메타데이터. 토큰은 keyring에 두므로 여기 없다(§10.2)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    email: str = Field(min_length=1)
    enabled: bool = True
    needs_relogin: bool = False
    added_at: datetime

    @field_validator("added_at")
    @classmethod
    def _ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=KST)
        return value
