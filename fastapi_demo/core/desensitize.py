import re


def text_summary(text: str, keep: int = 8, max_len: int = 20) -> str:
    """长文本截断摘要，用于日志打印。"""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return f"{text[:keep]}...{text[-keep:]}"


def mask_privacy(text: str) -> str:
    """自动识别并打码手机号、邮箱。"""
    if not text:
        return text

    text = re.sub(
        r"1[3-9]\d{9}",
        lambda m: f"{m.group()[:3]}****{m.group()[-4:]}",
        text,
    )
    text = re.sub(
        r"(\w{1,3})@(\w+\.\w+)",
        r"\1***@\2",
        text,
    )
    return text


def log_safe(text: str) -> str:
    """日志安全输出：先打码隐私，再截断摘要。"""
    return text_summary(mask_privacy(text))
