from uuid import uuid4

from pydantic import BaseModel


class UnifiedResponse(BaseModel):
    code: int
    message: str
    data: dict | list | str | int | float | bool | None = None
    request_id: str | None = None



def get_request_id() -> str:
    return str(uuid4())
