# FastAPI基础异常、请求对象、HTTP状态码
from fastapi import HTTPException, Request, status
# Bearer Token 鉴权工具类、凭证封装对象
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# 全局项目配置，读取预设接口Token
from config import config

# 实例化Bearer鉴权工具，auto_error=False：关闭框架自动401，由我们自定义错误返回
security = HTTPBearer(auto_error=False)


async def verify_token(request: Request):
    """
    全局接口Token鉴权依赖函数
    挂载在路由dependencies中，访问接口前置校验Bearer Token
    规则：请求头 Authorization: Bearer {token} 必须与配置内api_token一致
    :param request: FastAPI原始请求对象
    :raises HTTPException: 未携带Token / Token不匹配时抛出401未授权异常
    """
    # 解析请求头中的Bearer凭证
    credentials: HTTPAuthorizationCredentials = await security(request)

    # 两种失败场景：1. 无Authorization头 2. token与配置不一致
    if not credentials or credentials.credentials != config.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # 401 未授权
            detail="无效或未提供 Token",                 # 错误提示文案
            headers={"WWW-Authenticate": "Bearer"},     # 标准鉴权响应头，告知客户端使用Bearer方式传参
        )