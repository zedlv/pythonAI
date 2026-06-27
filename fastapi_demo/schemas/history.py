import math
from datetime import datetime
# 泛型相关导入：Generic泛型基类、TypeVar类型变量
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class ChatHistoryItem(BaseModel):
    """
    单条聊天记录序列化模型
    用于数据库ChatMessage ORM实体转接口返回JSON
    """
    # 记录主键ID
    id: int
    # 用户唯一标识
    user_id: str
    # 对话会话ID，区分同一个用户多轮对话
    session_id: str
    # 用户发送的提问文本
    user_content: str
    # AI回复内容，可为空（失败/未生成时）
    ai_content: str | None
    # 消息状态：0失败 / 1成功 / 2处理中
    msg_status: int
    # 消息创建时间
    created_at: datetime

    # Pydantic v2 配置：支持直接从ORM模型对象自动赋值
    model_config = ConfigDict(from_attributes=True)


# 定义泛型类型变量T，代表分页列表内元素的类型
T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """
    通用分页统一返回泛型结构体
    任意列表分页接口均可复用，items会自动适配传入的模型类型
    """
    # 当前页数据列表，泛型，可传入ChatHistoryItem等任意Model
    items: list[T]
    # 符合条件的数据总条数
    total: int
    # 当前页码
    page: int
    # 每页展示条数
    page_size: int
    # 总页数
    total_pages: int


def build_total_pages(total: int, page_size: int) -> int:
    """
    根据总数据量、每页条数计算总页数
    :param total: 数据总条数
    :param page_size: 单页条数
    :return: 向上取整后的总页数；无数据返回0
    """
    # 有数据则向上取整除法，无数据直接返回0页
    return math.ceil(total / page_size) if total > 0 else 0