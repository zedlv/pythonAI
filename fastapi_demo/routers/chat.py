# FastAPI路由、依赖注入、查询参数、请求对象
from fastapi import APIRouter, Depends, Query, Request
# 数据库会话
from sqlalchemy.orm import Session

# 全局鉴权依赖函数
from core.auth import verify_token
# 统一返回结构、生成链路追踪request_id工具
from core.response import UnifiedResponse, get_request_id
# 获取数据库会话的依赖函数
from db.base import get_db
# 聊天接口入参校验模型
from schemas.chat import ChatRequest
# 聊天业务逻辑服务层函数
from services.chat_service import get_user_chat_history, process_chat_message

# 创建独立路由实例，实现接口模块化拆分
router = APIRouter()


@router.post("/chat", dependencies=[Depends(verify_token)])
async def chat(
    req: ChatRequest,                     # 请求体，自动校验ChatRequest规则
    db: Session = Depends(get_db),        # 注入数据库会话
    request: Request = None               # 原始请求对象，用于性能埋点、日志
):
    """
    对话发送接口
    鉴权后接收用户提问，走缓存/LLM调用完整业务流程
    """
    # 调用业务层处理聊天主逻辑，直接返回结构化聊天结果
    return await process_chat_message(
        db=db,
        user_id=req.user_id,
        session_id=req.session_id,
        user_msg=req.message,
        request=request,
    )


@router.get(
    "/history",
    dependencies=[Depends(verify_token)],
    summary="按用户分页查询聊天历史"
)
async def chat_history(
    # URL查询参数：用户ID，必填
    user_id: str = Query(..., description="用户唯一ID"),
    # 页码，默认1，最小值限制1
    page: int = Query(1, ge=1, description="页码，最小为1"),
    # 分页大小，默认10，限制1~100防止一次性拉取大量数据
    page_size: int = Query(10, ge=1, le=100, description="每页条数，1-100"),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    查询用户历史聊天记录分页接口
    """
    # 调用服务层分页查询逻辑
    page_data = await get_user_chat_history(db, user_id, page, page_size, request)
    # 包装全局统一返回格式对外输出
    return UnifiedResponse(
        code=200,
        message="查询成功",
        data=page_data.model_dump(),  # 分页模型转字典放入data字段
        request_id=get_request_id(request),
    )