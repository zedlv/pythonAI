from fastapi import APIRouter

from schemas.chat import ChatRequest
from services.chat_service import process_chat_message

router = APIRouter()

@router.post("/chat")
async def chat(req: ChatRequest):
    return process_chat_message(req.message)
