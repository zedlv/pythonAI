from fastapi import Request
from time import time
from core.logger import logger

# 记录每个请求 + 耗时
async def log_requests_middleware(request: Request, call_next):
    start_time = time()

    # 记录请求进来
    logger.info(f"➡️  {request.method} {request.url.path}")

    # 执行接口
    response = await call_next(request)

    # 计算耗时
    duration = round((time() - start_time) * 1000, 2)

    # 记录完成 & 耗时
    logger.info(
        f"⬅️  {request.method} {request.url.path} "
        f"| status: {response.status_code} | {duration}ms"
    )

    return response