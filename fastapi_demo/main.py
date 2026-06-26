from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.logger import setup_logging
from core.middleware import log_requests_middleware
from core.response import UnifiedResponse, get_request_id
from routers import ping, chat, health
# 项目入口、全局异常捕获、中间件/路由挂载
setup_logging()

app = FastAPI()

app.middleware("http")(log_requests_middleware)


def _error_response(code: int, message: str) -> JSONResponse:
    body = UnifiedResponse(
        code=code,
        message=message,
        request_id=get_request_id(),
    )
    return JSONResponse(status_code=code, content=body.model_dump())


def _extract_message(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if detail is None:
        return "服务器异常"
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, dict):
            return first.get("msg", "参数错误")
        return str(first)
    return str(detail)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _error_response(exc.status_code, _extract_message(exc))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "参数错误"
    return _error_response(status.HTTP_400_BAD_REQUEST, message)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if hasattr(exc, "status_code"):
        code = exc.status_code
        message = _extract_message(exc)
    else:
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "服务器异常"

    return _error_response(code, message)


app.include_router(ping.router)
app.include_router(chat.router)
app.include_router(health.router)
