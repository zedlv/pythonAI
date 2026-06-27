from fastapi import Request
from time import time
# 全局日志工具、生成请求唯一追踪ID
from core.logger import logger
from core.response import get_request_id

# 慢请求阈值：单次接口总耗时超过2000毫秒，输出WARN告警日志便于排查性能问题
SLOW_REQUEST_THRESHOLD_MS = 2000


async def log_requests_middleware(request: Request, call_next):
    """
    全局HTTP请求日志&性能埋点中间件
    作用：
    1. 生成全局唯一request_id挂载到请求上下文，全链路日志追踪
    2. 初始化性能统计容器，业务层记录缓存/DB/LLM各阶段耗时
    3. 请求入站打印请求路径、请求ID
    4. 请求结束统计总耗时，输出分层性能日志，慢请求单独告警
    :param request: FastAPI原始请求对象
    :param call_next: 执行后续路由/业务逻辑的回调函数
    :return: 接口响应response
    """
    # 记录请求进入的时间戳（秒）
    start_time = time()

    # 生成本次请求唯一链路ID，挂载到request.state供全链路传递
    request.state.request_id = get_request_id()
    # 初始化性能指标存储容器，业务PerfTimer会写入各模块耗时、缓存命中标记
    request.state.perf = {
        "cache_ms": 0,      # Redis缓存操作耗时(ms)
        "llm_ms": 0,        # LLM大模型调用耗时(ms)
        "db_ms": 0,         # 数据库操作耗时(ms)
        "cache_hit": False, # 是否命中缓存标记
    }

    # 获取当前请求方法、接口路径
    method = request.method
    path = request.url.path

    # 请求进入日志，标记请求ID方便链路检索
    logger.info(f"➡️  {method} {path} | request_id={request.state.request_id}")

    # 执行后续路由、业务逻辑，等待接口处理完成拿到响应
    response = await call_next(request)

    # 计算接口总耗时，转换为毫秒并保留2位小数
    total_ms = round((time() - start_time) * 1000, 2)
    # 取出业务层回填的各阶段性能数据
    perf = request.state.perf

    # 拼接完整性能指标日志文本
    perf_log = (
        f"[PERF] path={path} | method={method} | status={response.status_code} "
        f"| total_ms={total_ms} | cache_hit={perf['cache_hit']} "
        f"| cache_ms={perf['cache_ms']} | llm_ms={perf['llm_ms']} | db_ms={perf['db_ms']} "
        f"| request_id={request.state.request_id}"
    )

    # 判断是否为慢请求，超过阈值输出警告日志
    if total_ms >= SLOW_REQUEST_THRESHOLD_MS:
        logger.warning(f"⚠️  慢请求 | {perf_log}")
    else:
        # 正常请求打印返回摘要日志
        logger.info(f"⬅️  {method} {path} | status={response.status_code} | {total_ms}ms")
        # 打印细分性能耗时明细
        logger.info(perf_log)

    # 返回接口响应给客户端
    return response