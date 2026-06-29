from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.base import get_db
from core.redis_client import redis_client
from core.response import UnifiedResponse, get_request_id

router = APIRouter(tags=["健康检查"])

/*
1. 收到GET /healthz 请求
2. 识别依赖 Depends(get_db)
   ↓【第一次 next(gen) 在这里插入执行】
   ├─ get_db 运行：创建db会话 → yield db 暂停
   └─ 拿到db，注入接口参数
3. 运行 health_check 全部业务代码
   ├─ db.execute(text("SELECT 1"))
   ├─ redis_client.ping()
   └─ return UnifiedResponse(...)
   ↓【第二次 next(gen) 在这里插入执行】
4. 唤醒get_db，执行finally → db.close()
5. 返回HTTP响应给浏览器
*/

@router.get("/healthz", summary="全局健康检查")
def health_check(db: Session = Depends(get_db)):
    """
    全链路健康检测：应用 + 数据库 + 缓存
    全部正常返回 200，任意异常返回 503
    """
    status = "healthy"
    details = {}

    # 1. 应用自身：能执行到这里即代表应用进程正常
    details["app"] = "ok"

    # 2. 检测 PostgreSQL 连接
    try:
        db.execute(text("SELECT 1"))
        details["postgres"] = "ok"
    except Exception as e:
        details["postgres"] = f"error: {str(e)[:50]}"
        status = "unhealthy"

    # 3. 检测 Redis 连接
    try:
        redis_client.ping()
        details["redis"] = "ok"
    except Exception as e:
        details["redis"] = f"error: {str(e)[:50]}"
        status = "unhealthy"

    return UnifiedResponse(
        code=200 if status == "healthy" else 503,
        message=status,
        data=details,
        request_id=get_request_id(),
    )
