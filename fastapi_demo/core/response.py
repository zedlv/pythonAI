# 生成全局唯一UUID
from uuid import uuid4
# FastAPI请求对象，用于读取请求上下文存储的request_id
from fastapi import Request

# Pydantic基础模型，用于统一接口返回JSON结构
from pydantic import BaseModel


class UnifiedResponse(BaseModel):
    """
    项目全局统一接口返回格式模型
    所有正常/异常接口响应均使用该结构，前后端交互标准统一
    """
    # HTTP业务状态码，200成功，4xx参数/权限错误，5xx服务异常
    code: int
    # 给前端展示的提示文案
    message: str
    # 业务返回数据，支持字典/列表/数字/字符串/布尔/空多种类型，不传默认为None
    data: dict | list | str | int | float | bool | None = None
    # 请求链路追踪ID，用于日志检索、问题定位
    request_id: str | None = None


def get_request_id(request: Request = None) -> str:
    """
    获取当前请求唯一追踪ID
    优先级：请求上下文已存在request_id > 现场生成新短UUID
    :param request: FastAPI原始请求对象（可选）
    :return: 格式化后的请求ID字符串，前缀req_ + 12位UUID
    """
    # 如果传入request且state中已提前存入request_id，直接复用（中间件提前生成）
    if request and hasattr(request.state, "request_id"):
        return request.state.request_id
    # 无上下文则现场生成短UUID，截取前12位十六进制字符缩短长度
    return f"req_{uuid4().hex[:12]}"