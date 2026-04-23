from pydantic import BaseModel
from typing import Optional, Generic, TypeVar
from pydantic.generics import GenericModel

DataT = TypeVar("DataT")

class BaseResponse(GenericModel, Generic[DataT]):
    code: int = 0
    message: str = "success"
    data: Optional[DataT] = None