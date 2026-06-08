from fastapi import FastAPI
from core.logger import setup_logging
from core.middleware import log_requests_middleware
from routers import ping, chat

# 启动日志
setup_logging()

app = FastAPI()

# 注册请求日志中间件
app.middleware("http")(log_requests_middleware)

# 挂载路由
app.include_router(ping.router)
app.include_router(chat.router)