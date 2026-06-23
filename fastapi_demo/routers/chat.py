from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.response import UnifiedResponse, get_request_id
from db.base import get_db
from schemas.chat import ChatRequest
from services.chat_service import get_user_chat_history, process_chat_message

router = APIRouter()


@router.post("/chat", dependencies=[Depends(verify_token)])
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return await process_chat_message(
        db=db,
        user_id=req.user_id,
        session_id=req.session_id,
        user_msg=req.message,
    )


@router.get("/history", dependencies=[Depends(verify_token)], summary="按用户分页查询聊天历史")
async def chat_history(
    user_id: str = Query(..., description="用户唯一ID"),
    page: int = Query(1, ge=1, description="页码，最小为1"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数，1-100"),
    db: Session = Depends(get_db),
):
    page_data = await get_user_chat_history(db, user_id, page, page_size)
    return UnifiedResponse(
        code=200,
        message="查询成功",
        data=page_data.model_dump(),
        request_id=get_request_id(),
    )
