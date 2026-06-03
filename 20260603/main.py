# 导入 FastAPI 模块
from fastapi import FastAPI

# 创建应用实例
app = FastAPI()

# 定义 GET /ping 接口
@app.get("/ping")
def ping():
    # 返回要求的格式
    return {"ok": True}