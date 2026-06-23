from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=32, description="用户唯一ID")
    session_id: str = Field(min_length=10, max_length=64, description="会话唯一ID")
    message: str = Field(min_length=1, max_length=100, description="用户聊天内容")
