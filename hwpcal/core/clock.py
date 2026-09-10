"""시간대 정책: Asia/Seoul 고정(설계 전제 D)."""

from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now() -> datetime:
    """현재 시각을 KST 기준의 aware datetime으로 돌려준다."""
    return datetime.now(tz=KST)
