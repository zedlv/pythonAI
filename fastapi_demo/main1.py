from fastapi import FastAPI

# 创建应用实例
app = FastAPI()

# 旧：同步接口（之前写的）
@app.get("/ping")
def ping():
    return {"ok": True}

# 新：异步接口（今日核心！async + 异步路由）
@app.get("/async-ping")
async def async_ping():
    # async 定义异步函数
    return {"ok": True, "type": "async"}

# 进阶：带 await 的异步接口（模拟异步操作）
import asyncio
@app.get("/async-wait")
async def async_wait():
    # await 等待异步操作（比如请求接口、查询数据库）
    await asyncio.sleep(5)
    return {"msg": "异步等待完成", "code": 200}