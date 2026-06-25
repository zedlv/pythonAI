from core.desensitize import log_safe
from core.logger import logger

SENSITIVE_WORDS = {
    "尼玛",
    "煞笔",
    "滚开",
}


def contains_sensitive(text: str) -> bool:
    """检查文本是否包含敏感内容，True 表示需拦截。"""
    text_lower = text.lower()
    for word in SENSITIVE_WORDS:
        if word.lower() in text_lower:
            logger.warning(
                f"[敏感内容拦截] 命中词: {word}, 内容摘要: {log_safe(text)}"
            )
            return True
    return False
