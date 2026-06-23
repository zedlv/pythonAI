import math
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class ChatHistoryItem(BaseModel):
    """单条聊天记录结构"""

    id: int
    user_id: str
    session_id: str
    user_content: str
    ai_content: str | None
    msg_status: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """通用分页返回体"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int



def build_total_pages(total: int, page_size: int) -> int:
    return math.ceil(total / page_size) if total > 0 else 0
