import redis

from config import config
from core.logger import logger

CACHE_TTL_NORMAL = 1800
CACHE_TTL_EMPTY = 300
CACHE_EMPTY_MARKER = "__EMPTY__"
CACHE_ERROR_MARKER = "__ERROR__"

redis_client = redis.Redis(
    host=config.redis_host,
    port=config.redis_port,
    db=config.redis_db,
    decode_responses=True,
    socket_connect_timeout=3,
)


def set_cache(key: str, value: str, expire_seconds: int = CACHE_TTL_NORMAL):
    try:
        redis_client.setex(key, expire_seconds, value)
        logger.info(f"[缓存写入] key={key}, TTL={expire_seconds}s")
    except Exception as e:
        logger.warning(f"[缓存写入失败] key={key}, 错误: {e}")


def get_cache(key: str) -> str | None:
    try:
        return redis_client.get(key)
    except Exception as e:
        logger.warning(f"[缓存读取失败] key={key}, 错误: {e}")
        return None


def get_ttl(key: str) -> int:
    try:
        return redis_client.ttl(key)
    except Exception as e:
        logger.warning(f"[缓存TTL查询失败] key={key}, 错误: {e}")
        return -2


def delete_cache(key: str):
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning(f"[缓存删除失败] key={key}, 错误: {e}")
