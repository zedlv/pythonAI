from fastapi import APIRouter, Depends

from core.auth import verify_token
from schemas.chat import ChatRequest
from services.chat_service import process_chat_message

router = APIRouter()

@router.post("/chat", dependencies=[Depends(verify_token)])
async def chat(req: ChatRequest):
    return await process_chat_message(req.message)