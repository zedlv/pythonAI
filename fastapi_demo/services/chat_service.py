import hashlib

from sqlalchemy.orm import Session
from fastapi import Request

from core.desensitize import log_safe
from core.exceptions import BusinessException
from core.logger import logger
from core.perf import PerfTimer
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


async def process_chat_message(
    db: Session,
    user_id: str,
    session_id: str,
    user_msg: str,
    request: Request = None,
):
    # 初始化性能计时器
    perf = PerfTimer(request)
    clean_msg = user_msg.strip()
    safe_summary = log_safe(clean_msg)

    if not clean_msg:
        raise BusinessException("消息内容不能为空")

    if contains_sensitive(clean_msg):
        raise BusinessException("消息包含违规内容，请调整后重试")

    cache_key = _cache_key(clean_msg)

    # ========== 阶段1：缓存查询 ==========
    with perf.measure("cache"):
        cache_answer = get_cache(cache_key)

    # 空值缓存命中
    if cache_answer == CACHE_EMPTY_MARKER:
        perf.mark_cache_hit(True)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT-空值] key={cache_key}, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )
        perf.flush_to_request()
        raise BusinessException("AI未生成有效回答")

    # 异常缓存命中
    if cache_answer == CACHE_ERROR_MARKER:
        perf.mark_cache_hit(True)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT-异常] key={cache_key}, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )
        perf.flush_to_request()
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")

    # 正常缓存命中
    if cache_answer and is_llm_success(cache_answer):
        perf.mark_cache_hit(True)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT] key={cache_key}, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )

        # ========== 阶段2：写数据库 ==========
        with perf.measure("db"):
            new_msg = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                user_content=clean_msg,
                ai_content=cache_answer,
                msg_status=1,
            )
            db.add(new_msg)
            db.commit()

        perf.flush_to_request()
        return {
            "your_msg": clean_msg,
            "llm_reply": cache_answer,
            "from_cache": True,
        }

    # 有缓存但内容异常，删掉重走LLM
    if cache_answer:
        delete_cache(cache_key)

    # ========== 缓存未命中 ==========
    logger.info(
        f"[缓存未命中 MISS] key={cache_key}, "
        f"开始调用LLM接口, 消息摘要={safe_summary}"
    )

    # 阶段2：写数据库（处理中状态）
    with perf.measure("db"):
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
        # ========== 阶段3：LLM 调用 ==========
        with perf.measure("llm"):
            ai_reply = await call_llm(clean_msg)

        if not ai_reply or not ai_reply.strip():
            set_cache(cache_key, CACHE_EMPTY_MARKER, CACHE_TTL_EMPTY)
            with perf.measure("db"):
                new_msg.msg_status = 0
                db.commit()
            logger.warning(
                f"[空值缓存] key={cache_key}, LLM返回空，已缓存{CACHE_TTL_EMPTY}s, "
                f"消息摘要={safe_summary}"
            )
            perf.flush_to_request()
            raise BusinessException("AI未生成有效回答")

        if is_llm_success(ai_reply):
            set_cache(cache_key, ai_reply)
            with perf.measure("db"):
                new_msg.ai_content = ai_reply
                new_msg.msg_status = 1
                db.commit()
            logger.info(
                f"[LLM调用完成] key={cache_key}, "
                f"消息摘要={safe_summary}"
            )
            perf.flush_to_request()
            return {
                "your_msg": clean_msg,
                "llm_reply": ai_reply,
                "from_cache": False,
            }

        set_cache(cache_key, CACHE_ERROR_MARKER, CACHE_TTL_EMPTY)
        with perf.measure("db"):
            new_msg.ai_content = ai_reply
            new_msg.msg_status = 0
            db.commit()
        logger.error(
            f"[LLM调用失败] key={cache_key}, 返回摘要={log_safe(ai_reply)}, "
            f"消息摘要={safe_summary}"
        )
        perf.flush_to_request()
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")

    except BusinessException:
        perf.flush_to_request()
        raise
    except Exception as e:
        set_cache(cache_key, CACHE_ERROR_MARKER, CACHE_TTL_EMPTY)
        with perf.measure("db"):
            new_msg.msg_status = 0
            db.commit()
        logger.error(
            f"[LLM调用失败] key={cache_key}, 错误: {e}, 消息摘要={safe_summary}"
        )
        perf.flush_to_request()
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")


async def get_user_chat_history(
    db: Session,
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    request: Request = None,
) -> PageResult[ChatHistoryItem]:
    perf = PerfTimer(request)

    with perf.measure("db"):
        query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)
        total = query.count()
        offset = (page - 1) * page_size
        records = (
            query.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    perf.flush_to_request()

    return PageResult[ChatHistoryItem](
        items=[ChatHistoryItem.model_validate(record) for record in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=build_total_pages(total, page_size),
    )
