from fastapi import Request
from time import time
from core.logger import logger
from core.response import get_request_id

# 慢请求阈值：超过 2000ms 标记为慢请求，打 WARN 日志
SLOW_REQUEST_THRESHOLD_MS = 2000


async def log_requests_middleware(request: Request, call_next):
    start_time = time()

    # 初始化请求级性能上下文，业务层往里填数据
    request.state.request_id = get_request_id()
    request.state.perf = {
        "cache_ms": 0,
        "llm_ms": 0,
        "db_ms": 0,
        "cache_hit": False,
    }

    method = request.method
    path = request.url.path

    logger.info(f"➡️  {method} {path} | request_id={request.state.request_id}")

    response = await call_next(request)

    # 计算总耗时
    total_ms = round((time() - start_time) * 1000, 2)
    perf = request.state.perf

    # 组装统一性能日志
    perf_log = (
        f"[PERF] path={path} | method={method} | status={response.status_code} "
        f"| total_ms={total_ms} | cache_hit={perf['cache_hit']} "
        f"| cache_ms={perf['cache_ms']} | llm_ms={perf['llm_ms']} | db_ms={perf['db_ms']} "
        f"| request_id={request.state.request_id}"
    )

    # 慢请求打 WARN 级别，方便快速筛选
    if total_ms >= SLOW_REQUEST_THRESHOLD_MS:
        logger.warning(f"⚠️  慢请求 | {perf_log}")
    else:
        logger.info(f"⬅️  {method} {path} | status={response.status_code} | {total_ms}ms")
        logger.info(perf_log)

    return response
