from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# 项目核心模块导入
from core.logger import setup_logging          # 日志初始化函数
from core.middleware import log_requests_middleware  # 请求日志中间件
from core.response import UnifiedResponse, get_request_id  # 统一返回结构体、生成请求唯一ID
# 业务路由模块
from routers import ping, chat, health

# ====================== 服务初始化 ======================
# 全局日志初始化，统一日志格式、输出渠道
setup_logging()

# 创建FastAPI应用实例
app = FastAPI()

# 注册全局HTTP请求中间件，记录每个请求的入参、耗时、状态码等日志
app.middleware("http")(log_requests_middleware)


# ====================== 全局通用工具函数 ======================
def _error_response(code: int, message: str) -> JSONResponse:
    """
    统一构造错误格式返回体
    :param code: HTTP状态码
    :param message: 对外展示的错误提示文案
    :return: JSON格式标准响应
    """
    # 组装统一返回结构
    body = UnifiedResponse(
        code=code,
        message=message,
        request_id=get_request_id(),  # 绑定本次请求唯一标识，用于日志链路追踪
    )
    # 返回标准JSON响应
    return JSONResponse(status_code=code, content=body.model_dump())


def _extract_message(exc: Exception) -> str:
    """
    从异常对象中提取可读的错误提示信息
    兼容HTTPException、校验异常等多种detail格式
    :param exc: 捕获到的异常实例
    :return: 格式化后的错误文本
    """
    # 获取异常内置detail字段
    detail = getattr(exc, "detail", None)
    # 无detail时返回兜底提示
    if detail is None:
        return "服务器异常"
    # detail为普通字符串直接返回
    if isinstance(detail, str):
        return detail
    # detail为列表（参数校验异常标准格式），取第一条错误信息
    if isinstance(detail, list) and detail:
        first = detail[0]
        # 校验错误字典，提取msg字段
        if isinstance(first, dict):
            return first.get("msg", "参数错误")
        # 非字典类型直接转字符串
        return str(first)
    # 其他类型detail统一转字符串返回
    return str(detail)


# ====================== 全局异常捕获处理器 ======================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    捕获手动抛出的HTTPException异常
    如权限不足、资源不存在、主动业务报错等
    """
    err_msg = _extract_message(exc)
    return _error_response(exc.status_code, err_msg)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    捕获请求参数校验失败异常
    请求体/路径参数/查询参数不符合模型规则时触发
    """
    errors = exc.errors()
    # 取第一条参数错误信息，无错误列表则兜底文案
    message = errors[0]["msg"] if errors else "参数错误"
    # 返回400参数错误状态码
    return _error_response(status.HTTP_400_BAD_REQUEST, message)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局兜底异常处理器，捕获所有未被上面捕获的未知异常
    数据库报错、代码bug、第三方调用异常等都会进入这里
    """
    # 兼容自定义带status_code的业务异常
    if hasattr(exc, "status_code"):
        code = exc.status_code
        message = _extract_message(exc)
    else:
        # 普通未知异常统一500
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "服务器异常"

    return _error_response(code, message)


# ====================== 挂载业务路由 ======================
# 健康检测路由
app.include_router(ping.router)
# 对话业务路由
app.include_router(chat.router)
# 服务健康探针路由（k8s就绪/存活探针）
app.include_router(health.router)