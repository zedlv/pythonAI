# 导入环境变量加载工具、系统操作模块
from dotenv import load_dotenv
import os


def _running_in_docker() -> bool:
    """
    判断当前程序是否运行在Docker容器内
    判定依据：存在/.dockerenv文件 或 环境变量DOCKER_CONTAINER=1
    :return: 容器环境返回True，本地宿主机返回False
    """
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "1"


# 捕获.env文件读取异常，避免配置文件缺失导致服务启动崩溃
try:
    # 加载项目根目录下.env环境变量文件
    load_dotenv()
except Exception as e:
    # 仅打印警告，不中断程序，后续配置会使用默认值兜底
    print(f"配置加载失败：{e}")


class AppConfig:
    """
    全局应用配置类
    统一管理数据库、Redis、接口鉴权、缓存过期时间等所有环境配置
    自动区分本地宿主机 / Docker容器两种运行环境，自动切换数据库/Redis连接地址
    """
    def __init__(self):
        # 根据运行环境自动选择数据库/Redis host
        # Docker容器内使用host.docker.internal访问宿主机服务，本地使用127.0.0.1
        docker_host = "host.docker.internal" if _running_in_docker() else "127.0.0.1"

        # 接口鉴权密钥，无默认值，必须在.env中配置
        self.api_key = os.getenv("API_KEY")
        # 接口token默认值兜底，未配置时使用mytoken123456
        self.api_token = os.getenv("API_TOKEN", "mytoken123456")

        # PostgreSQL数据库配置
        self.db_host = os.getenv("DB_HOST", docker_host)    # 数据库地址
        self.db_port = os.getenv("DB_PORT", "5432")         # 数据库端口
        self.db_user = os.getenv("DB_USER", "lvasia")       # 数据库账号
        self.db_pwd = os.getenv("DB_PWD", "123456")         # 数据库密码
        self.db_name = os.getenv("DB_NAME", "fastapi_chat_db")  # 数据库名

        # Redis缓存配置
        self.redis_host = os.getenv("REDIS_HOST", docker_host)
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))  # 端口转数字
        self.redis_db = int(os.getenv("REDIS_DB", "0"))         # Redis库编号

        # 缓存过期时间（单位：秒）
        self.cache_ttl_normal = int(os.getenv("CACHE_TTL_NORMAL", "1800"))  # 正常数据缓存30分钟
        self.cache_ttl_empty = int(os.getenv("CACHE_TTL_EMPTY", "300"))    # 空数据缓存5分钟，防止缓存穿透

    def show_config(self):
        """
        安全打印当前运行配置，敏感密钥做脱敏处理，防止日志泄露账号密码
        仅用于启动调试查看配置是否加载正确
        """
        print("=== 项目配置 ===")
        print(f"数据库地址：{self.db_host}")
        print(f"数据库端口：{self.db_port}")
        print(f"数据库名称：{self.db_name}")
        print(f"数据库账号：{self.db_user}")
        # API密钥脱敏展示，只显示前3位，避免明文泄露
        print(f"API密钥：{self.api_key[:3]}***" if self.api_key else "未配置")
        # 数据库密码完全隐藏，不输出任何明文
        print(f"数据库密码：***")
        print("===============")


# 全局单例配置实例，项目全局统一导入使用
config = AppConfig()

# 单独运行本文件时执行配置打印，用于调试校验配置加载结果
if __name__ == "__main__":
    config.show_config()