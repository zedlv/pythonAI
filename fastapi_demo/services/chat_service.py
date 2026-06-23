import hashlib

from sqlalchemy.orm import Session

from core.exceptions import BusinessException
from core.redis_client import delete_cache, get_cache, set_cache
from llm_client import call_llm, is_llm_success
from models.chat import ChatMessage
from schemas.history import ChatHistoryItem, PageResult, build_total_pages


def _cache_key(user_msg: str) -> str:
    return f"chat:answer:{hashlib.md5(user_msg.encode()).hexdigest()}"


async def process_chat_message(db: Session, user_id: str, session_id: str, user_msg: str):
    cache_key = _cache_key(user_msg)

    cache_answer = get_cache(cache_key)
    if cache_answer and is_llm_success(cache_answer):
        new_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            user_content=user_msg,
            ai_content=cache_answer,
            msg_status=1,
        )
        db.add(new_msg)
        db.commit()
        return {
            "your_msg": user_msg,
            "llm_reply": cache_answer,
            "from_cache": True,
        }
    elif cache_answer:
        delete_cache(cache_key)

    new_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        user_content=user_msg,
        msg_status=2,
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    try:
        ai_reply = await call_llm(user_msg)

        if is_llm_success(ai_reply):
            set_cache(cache_key, ai_reply)
            new_msg.msg_status = 1
        else:
            new_msg.msg_status = 0

        new_msg.ai_content = ai_reply
        db.commit()

        return {
            "your_msg": user_msg,
            "llm_reply": ai_reply,
            "from_cache": False,
        }

    except Exception:
        new_msg.msg_status = 0
        db.commit()
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")


async def get_user_chat_history(
    db: Session,
    user_id: str,
    page: int = 1,
    page_size: int = 10,
) -> PageResult[ChatHistoryItem]:
    query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)

    total = query.count()
    offset = (page - 1) * page_size

    records = (
        query.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PageResult[ChatHistoryItem](
        items=[ChatHistoryItem.model_validate(record) for record in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=build_total_pages(total, page_size),
    )
