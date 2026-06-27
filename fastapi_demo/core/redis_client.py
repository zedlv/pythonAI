# redis 官方客户端
import redis
# 全局配置实例
from config import config
# 项目日志工具
from core.logger import logger

# 正常问答缓存过期时间（从配置读取）
CACHE_TTL_NORMAL = config.cache_ttl_normal
# 空结果/异常结果缓存过期时间（防缓存穿透、防重复报错）
CACHE_TTL_EMPTY = config.cache_ttl_empty
# 空数据标记：LLM返回无有效内容时存入此占位符
CACHE_EMPTY_MARKER = "__EMPTY__"
# 异常标记：LLM调用失败、接口异常时存入此占位符
CACHE_ERROR_MARKER = "__ERROR__"

# 创建全局Redis客户端单例
redis_client = redis.Redis(
    host=config.redis_host,        # Redis地址（自动区分本地/Docker）
    port=config.redis_port,        # Redis端口
    db=config.redis_db,            # 使用的Redis库编号
    decode_responses=True,         # 自动将bytes转为字符串，不用手动decode
    socket_connect_timeout=3,      # 连接超时3秒，防止卡死阻塞接口
)


def set_cache(key: str, value: str, expire_seconds: int = CACHE_TTL_NORMAL):
    """
    写入带过期时间的字符串缓存
    :param key: 缓存键
    :param value: 缓存值（正常回答/空标记/异常标记）
    :param expire_seconds: 过期秒数，默认普通缓存时长
    """
    try:
        # setex = set + expire，设置key同时指定TTL
        redis_client.setex(key, expire_seconds, value)
        logger.info(f"[缓存写入] key={key}, TTL={expire_seconds}s")
    except Exception as e:
        # Redis异常仅打警告日志，不阻断主业务流程
        logger.warning(f"[缓存写入失败] key={key}, 错误: {e}")


def get_cache(key: str) -> str | None:
    """
    读取缓存字符串
    :param key: 缓存键
    :return: 缓存值 / None（不存在/读取异常）
    """
    try:
        return redis_client.get(key)
    except Exception as e:
        logger.warning(f"[缓存读取失败] key={key}, 错误: {e}")
        # Redis故障时返回None，业务自动走LLM兜底
        return None


def get_ttl(key: str) -> int:
    """
    查询key剩余存活时间
    :param key: 缓存键
    :return:
        - 正数：剩余秒数
        - -1：key存在但无过期时间
        - -2：key不存在 / 查询异常
    """
    try:
        return redis_client.ttl(key)
    except Exception as e:
        logger.warning(f"[缓存TTL查询失败] key={key}, 错误: {e}")
        return -2


def delete_cache(key: str):
    """删除指定缓存key"""
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning(f"[缓存删除失败] key={key}, 错误: {e}")