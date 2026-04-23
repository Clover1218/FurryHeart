from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass(frozen=True)
class AddHistoryInput:
    user_id: str
    session_id: str
    role: str
    content: str


@dataclass(frozen=True)
class AddHistoryOutput:
    success: bool


@dataclass(frozen=True)
class GetRecentHistoryInput:
    user_id: str
    limit: int


@dataclass(frozen=True)
class HistoryItem:
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class GetRecentHistoryOutput:
    items: List[HistoryItem]


@dataclass(frozen=True)
class GetHistoryByCursorInput:
    user_id: str
    cursor: Optional[datetime] = None
    limit: int = 20


@dataclass(frozen=True)
class GetHistoryByCursorOutput:
    items: List[dict]  # 格式: [{"role": "xxx", "text": "xxx"}, ...]
    next_cursor: Optional[datetime]


@dataclass(frozen=True)
class ClearUserHistoryInput:
    user_id: str


@dataclass(frozen=True)
class ClearUserHistoryOutput:
    success: bool
