import hashlib

from sqlalchemy.orm import Session
from fastapi import Request

# 公共工具、异常、日志、性能监控、Redis缓存客户端
from core.desensitize import log_safe
from core.exceptions import BusinessException
from core.logger import logger
from core.perf import PerfTimer
from core.redis_client import (
    CACHE_EMPTY_MARKER,    # 空结果缓存标记
    CACHE_ERROR_MARKER,    # LLM调用异常缓存标记
    CACHE_TTL_EMPTY,       # 空/异常缓存过期时间
    delete_cache,
    get_cache,
    get_ttl,
    set_cache,
)
from core.sensitive_filter import contains_sensitive  # 敏感词检测工具
from llm_client import call_llm, is_llm_success       # LLM大模型调用客户端、结果校验函数
from models.chat import ChatMessage                   # 聊天消息数据库ORM模型
from schemas.history import ChatHistoryItem, PageResult, build_total_pages  # 分页返回结构、分页计算工具


def _cache_key(user_msg: str) -> str:
    """
    根据用户提问生成Redis缓存Key
    使用MD5对原文摘要，避免超长key，统一前缀区分业务
    :param user_msg: 用户原始提问文本
    :return: 格式化后的缓存键名
    """
    return f"chat:answer:{hashlib.md5(user_msg.encode()).hexdigest()}"


async def process_chat_message(
    db: Session,
    user_id: str,
    session_id: str,
    user_msg: str,
    request: Request = None,
):
    """
    聊天消息主处理逻辑：敏感词校验 -> 缓存查询 -> LLM调用 -> 数据库落库
    完整缓存策略：正常回答缓存、空结果缓存防穿透、异常结果缓存防重复报错
    :param db: SQLAlchemy数据库会话
    :param user_id: 用户唯一ID
    :param session_id: 对话会话ID
    :param user_msg: 用户输入提问内容
    :param request: FastAPI请求对象，用于性能指标埋点
    :return: 结构化聊天返回结果（区分缓存/实时生成）
    :raises BusinessException: 参数非法、敏感词、空回答、LLM异常等业务错误
    """
    # 初始化性能计时器，统计缓存、DB、LLM各阶段耗时
    perf = PerfTimer(request)
    # 去除首尾空格，清理输入
    clean_msg = user_msg.strip()
    # 脱敏摘要，日志打印不泄露完整长文本
    safe_summary = log_safe(clean_msg)

    # 校验消息非空
    if not clean_msg:
        raise BusinessException("消息内容不能为空")

    # 敏感内容拦截
    if contains_sensitive(clean_msg):
        raise BusinessException("消息包含违规内容，请调整后重试")

    # 生成当前提问对应的缓存key
    cache_key = _cache_key(clean_msg)

    # ========== 阶段1：查询Redis缓存 ==========
    with perf.measure("cache"):
        cache_answer = get_cache(cache_key)

    # 分支1：命中空值缓存（之前LLM返回无有效内容）
    if cache_answer == CACHE_EMPTY_MARKER:
        perf.mark_cache_hit(True)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT-空值] key={cache_key}, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )
        # 上报性能指标到请求上下文
        perf.flush_to_request()
        raise BusinessException("AI未生成有效回答")

    # 分支2：命中异常缓存（之前LLM调用失败）
    if cache_answer == CACHE_ERROR_MARKER:
        perf.mark_cache_hit(True)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT-异常] key={cache_key}, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )
        perf.flush_to_request()
        raise BusinessException("AI服务调用异常，聊天记录已标记失败")

    # 分支3：命中正常有效回答缓存，直接返回，无需重调LLM
    if cache_answer and is_llm_success(cache_answer):
        perf.mark_cache_hit(True)
        remain_ttl = get_ttl(cache_key)
        logger.info(
            f"[缓存命中 HIT] key={cache_key}, "
            f"剩余TTL={remain_ttl}s, 消息摘要={safe_summary}"
        )

        # ========== 阶段2：缓存命中，写入聊天记录到数据库 ==========
        with perf.measure("db"):
            new_msg = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                user_content=clean_msg,
                ai_content=cache_answer,
                msg_status=1,  # 1=正常完成
            )
            db.add(new_msg)
            db.commit()

        perf.flush_to_request()
        return {
            "your_msg": clean_msg,
            "llm_reply": cache_answer,
            "from_cache": True,
        }

    # 缓存存在但内容无效，删除脏缓存，走实时LLM流程
    if cache_answer:
        delete_cache(cache_key)

    # ========== 缓存未命中，进入实时调用LLM流程 ==========
    logger.info(
        f"[缓存未命中 MISS] key={cache_key}, "
        f"开始调用LLM接口, 消息摘要={safe_summary}"
    )

    # 先入库一条处理中状态记录（msg_status=2）
    with perf.measure("db"):
        new_msg = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            user_content=clean_msg,
            msg_status=2,  # 2=处理中
        )
        db.add(new_msg)
        db.commit()
        db.refresh(new_msg)  # 刷新获取数据库自增ID等字段

    try:
        # ========== 阶段3：调用大模型接口获取回答 ==========
        with perf.measure("llm"):
            ai_reply = await call_llm(clean_msg)

        # 场景1：LLM返回空内容，写入空标记缓存，更新记录为失败状态
        if not ai_reply or not ai_reply.strip():
            set_cache(cache_key, CACHE_EMPTY_MARKER, CACHE_TTL_EMPTY)
            with perf.measure("db"):
                new_msg.msg_status = 0  # 0=失败
                db.commit()
            logger.warning(
                f"[空值缓存] key={cache_key}, LLM返回空，已缓存{CACHE_TTL_EMPTY}s, "
                f"消息摘要={safe_summary}"
            )
            perf.flush_to_request()
            raise BusinessException("AI未生成有效回答")

        # 场景2：LLM返回正常有效内容，写入正常缓存，更新记录为完成
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

        # 场景3：LLM返回内容格式异常，写入异常标记缓存
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

    # 业务异常直接抛出，不捕获覆盖
    except BusinessException:
        perf.flush_to_request()
        raise
    # 兜底捕获所有未知异常（网络、超时、内部报错等）
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
    """
    分页查询用户全部聊天历史记录
    :param db: 数据库会话
    :param user_id: 当前用户ID
    :param page: 当前页码，默认第1页
    :param page_size: 每页条数，默认10条
    :param request: 请求对象，用于性能埋点
    :return: 分页结构体：总条数、当前页数据、总页数、页码信息
    """
    perf = PerfTimer(request)

    # 数据库查询计时
    with perf.measure("db"):
        # 筛选当前用户所有聊天记录
        query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)
        # 查询总数据量用于分页计算
        total = query.count()
        # 计算分页偏移量
        offset = (page - 1) * page_size
        # 按创建时间、ID倒序，最新消息在前
        records = (
            query.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    # 上报本次查询耗时指标
    perf.flush_to_request()

    # ORM模型转Pydantic返回结构，组装分页信息
    return PageResult[ChatHistoryItem](
        items=[ChatHistoryItem.model_validate(record) for record in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=build_total_pages(total, page_size),
    )