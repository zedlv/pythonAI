import redis

from config import config
from core.logger import logger

redis_client = redis.Redis(
    host=config.redis_host,
    port=config.redis_port,
    db=config.redis_db,
    decode_responses=True,
    socket_connect_timeout=3,
)


def set_cache(key: str, value: str, expire_seconds: int = 1800):
    try:
        redis_client.setex(key, expire_seconds, value)
    except Exception as e:
        logger.warning(f"Redis写入失败: {e}")


def get_cache(key: str) -> str | None:
    try:
        return redis_client.get(key)
    except Exception as e:
        logger.warning(f"Redis读取失败: {e}")
        return None


def delete_cache(key: str):
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Redis删除失败: {e}")
