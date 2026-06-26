from uuid import uuid4
from fastapi import Request

from pydantic import BaseModel


class UnifiedResponse(BaseModel):
    code: int
    message: str
    data: dict | list | str | int | float | bool | None = None
    request_id: str | None = None



def get_request_id(request: Request = None) -> str:
    """获取当前请求的唯一ID，有则从 request.state 取，没有则生成新的"""
    if request and hasattr(request.state, "request_id"):
        return request.state.request_id
    return f"req_{uuid4().hex[:12]}"
