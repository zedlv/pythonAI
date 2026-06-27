from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """
    聊天接口请求入参校验模型
    统一校验用户ID、会话ID、提问文本长度，并自动清洗消息文本
    """
    # 用户唯一标识，长度1~32位
    user_id: str = Field(
        min_length=1,
        max_length=32,
        description="用户唯一ID"
    )
    # 对话会话ID，长度10~64位，区分同一用户多轮对话
    session_id: str = Field(
        min_length=10,
        max_length=64,
        description="会话唯一ID"
    )
    # 用户提问内容，限制1~200字符，防止超长文本
    message: str = Field(
        min_length=1,
        max_length=200,
        description="用户聊天内容，最长200字符"
    )

    @field_validator("message")
    @classmethod
    def clean_input_message(cls, value: str) -> str:
        """
        消息字段自定义校验/清洗钩子
        统一格式化用户输入，消除换行、制表、多空格差异，提升Redis缓存命中率
        :param value: 用户原始输入文本
        :return: 清洗后标准格式文本
        """
        # 去除首尾空白
        cleaned = value.strip()
        # 换行、制表符统一替换为单个空格
        cleaned = cleaned.replace("\n", " ").replace("\t", " ")
        # 循环压缩连续多个空格为单个空格
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        return cleaned