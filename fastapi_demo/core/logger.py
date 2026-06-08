import logging
import sys

# 定义日志格式
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# 导出 logger 供全局使用
logger = logging.getLogger("app")