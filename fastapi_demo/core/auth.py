from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import config

security = HTTPBearer(auto_error=False)


async def verify_token(request: Request):
    credentials: HTTPAuthorizationCredentials = await security(request)

    if not credentials or credentials.credentials != config.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或未提供 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
