from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=32, description="用户唯一ID")
    session_id: str = Field(min_length=10, max_length=64, description="会话唯一ID")
    message: str = Field(min_length=1, max_length=200, description="用户聊天内容，最长200字符")

    @field_validator("message")
    @classmethod
    def clean_input_message(cls, value: str) -> str:
        """自动规范化输入，提升缓存命中率，避免格式差异导致重复调用"""
        cleaned = value.strip()
        cleaned = cleaned.replace("\n", " ").replace("\t", " ")
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        return cleaned
