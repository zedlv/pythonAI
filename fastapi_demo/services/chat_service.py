import hashlib
import time

from sqlalchemy.orm import Session

from core.desensitize import log_safe
from core.exceptions import BusinessException
from core.logger import logger
from core.redis_client import (
    CACHE_EMPTY_MARKER,
    CACHE_ERROR_MARKER,
    CACHE_TTL_EMPTY,
    delete_cache,
    get_cache,
    get_ttl,
    set_cache,
)
from core.sensitive_filter import contains_sensitive
from llm_client import call_llm, is_llm_success
from models.chat import ChatMessage
from schemas.history import ChatHistoryItem, PageResult, build_total_pages


def _cache_key(user_msg: str) -> str:
    return f"chat:answer:{hashlib.md5(user_msg.encode()).hexdigest()}"


async def process_chat_message(db: Session, user_id: str, session_id: str, user_msg: str):
    clean_msg = user_msg.strip()
    if not clean_msg:
        raise BusinessException("消息内容不能为空")

    if contains_sensitive(clean_msg):
        raise BusinessException("消息包含违规内容，请调整后重试")

    cache_key = _cache_key(clean_msg)
    safe_summary = log_safe(clean_msg)

    start_time = time.time()
    cache_answer = get_cache(cache_key)

    if cache_answer == CACHE_EMPTY_MARKER:
        cost_ms = round((time.time() - start_time) * 1000, 2)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT-空值] key={cache_key}, 耗时={cost_ms}ms, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )
        raise BusinessException("AI未生成有效回答")

    if cache_answer == CACHE_ERROR_MARKER:
        cost_ms = round((time.time() - start_time) * 1000, 2)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT-异常] key={cache_key}, 耗时={cost_ms}ms, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")

    if cache_answer and is_llm_success(cache_answer):
        cost_ms = round((time.time() - start_time) * 1000, 2)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT] key={cache_key}, 耗时={cost_ms}ms, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )

        new_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            user_content=clean_msg,
            ai_content=cache_answer,
            msg_status=1,
        )
        db.add(new_msg)
        db.commit()
        return {
            "your_msg": clean_msg,
            "llm_reply": cache_answer,
            "from_cache": True,
        }

    if cache_answer:
        delete_cache(cache_key)

    cost_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"[缓存未命中 MISS] key={cache_key}, 缓存查询耗时={cost_ms}ms, "
        f"开始调用LLM接口, 消息摘要={safe_summary}"
    )

    new_msg = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        user_content=clean_msg,
        msg_status=2,
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    try:
        llm_start = time.time()
        ai_reply = await call_llm(clean_msg)
        llm_cost_ms = round((time.time() - llm_start) * 1000, 2)

        if not ai_reply or not ai_reply.strip():
            set_cache(cache_key, CACHE_EMPTY_MARKER, CACHE_TTL_EMPTY)
            new_msg.msg_status = 0
            db.commit()
            logger.warning(
                f"[空值缓存] key={cache_key}, LLM返回空，已缓存{CACHE_TTL_EMPTY}s, "
                f"消息摘要={safe_summary}"
            )
            raise BusinessException("AI未生成有效回答")

        if is_llm_success(ai_reply):
            set_cache(cache_key, ai_reply)
            new_msg.ai_content = ai_reply
            new_msg.msg_status = 1
            db.commit()
            logger.info(
                f"[LLM调用完成] key={cache_key}, 接口耗时={llm_cost_ms}ms, "
                f"消息摘要={safe_summary}"
            )
            return {
                "your_msg": clean_msg,
                "llm_reply": ai_reply,
                "from_cache": False,
            }

        set_cache(cache_key, CACHE_ERROR_MARKER, CACHE_TTL_EMPTY)
        new_msg.ai_content = ai_reply
        new_msg.msg_status = 0
        db.commit()
        logger.error(
            f"[LLM调用失败] key={cache_key}, 返回摘要={log_safe(ai_reply)}, "
            f"消息摘要={safe_summary}"
        )
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")

    except BusinessException:
        raise
    except Exception as e:
        set_cache(cache_key, CACHE_ERROR_MARKER, CACHE_TTL_EMPTY)
        new_msg.msg_status = 0
        db.commit()
        logger.error(
            f"[LLM调用失败] key={cache_key}, 错误: {e}, 消息摘要={safe_summary}"
        )
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
