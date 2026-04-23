from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GetOrCreateUserInput:
    open_id: str = None

@dataclass(frozen=True)
class GetOrCreateUserOutput:
    user_id: str


@dataclass(frozen=True)
class GetUserInput:
    open_id: str


@dataclass(frozen=True)
class GetUserOutput:
    user_id: str
    exist: bool
@dataclass(frozen=True)
class SaveTokenInput:
    user_id: str
    expire_days: int = 7


@dataclass(frozen=True)
class SaveTokenOutput:
    token: str
    success: bool


@dataclass(frozen=True)
class GetTokenInput:
    token: str
    

@dataclass(frozen=True)
class GetTokenOutput:
    exist: bool
    user_id: Optional[str] = None

@dataclass(frozen=True)
class DeleteTokenInput:
    token: str


@dataclass(frozen=True)
class DeleteTokenOutput:
    success: bool
