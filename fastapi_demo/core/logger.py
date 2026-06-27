# 日志标准库、标准输出流模块
import logging
import sys


def setup_logging():
    """
    全局日志初始化配置函数
    统一设置日志级别、日志打印格式、输出目标为控制台标准输出
    项目启动时调用一次即可全局生效
    """
    logging.basicConfig(
        # 日志输出级别：INFO及以上(INFO/WARNING/ERROR/CRITICAL)才会打印
        level=logging.INFO,
        # 日志格式化模板：时间 | 日志级别 | 日志内容
        format="%(asctime)s | %(levelname)s | %(message)s",
        # 日志处理器：输出到控制台标准输出stdout
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# 创建全局日志实例，标识名称为app，全项目统一使用此logger打印日志
logger = logging.getLogger("app")