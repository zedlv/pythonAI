# 导入工具
from dotenv import load_dotenv
import os


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "1"


# 异常处理：捕获文件读取失败
try:
    load_dotenv()
except Exception as e:
    print(f"配置加载失败：{e}")

# 类：封装所有配置
class AppConfig:
    def __init__(self):
        docker_host = "host.docker.internal" if _running_in_docker() else "127.0.0.1"

        self.api_key = os.getenv("API_KEY")
        self.api_token = os.getenv("API_TOKEN", "mytoken123456")
        self.db_host = os.getenv("DB_HOST", docker_host)
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_user = os.getenv("DB_USER", "lvasia")
        self.db_pwd = os.getenv("DB_PWD", "123456")
        self.db_name = os.getenv("DB_NAME", "fastapi_chat_db")
        self.redis_host = os.getenv("REDIS_HOST", docker_host)
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.cache_ttl_normal = int(os.getenv("CACHE_TTL_NORMAL", "1800"))
        self.cache_ttl_empty = int(os.getenv("CACHE_TTL_EMPTY", "300"))

    # 安全打印：不泄露密钥
    def show_config(self):
        print("=== 项目配置 ===")
        print(f"数据库地址：{self.db_host}")
        print(f"数据库端口：{self.db_port}")
        print(f"数据库名称：{self.db_name}")
        print(f"数据库账号：{self.db_user}")
        # 脱敏处理：隐藏密钥，不打印原文
        print(f"API密钥：{self.api_key[:3]}***" if self.api_key else "未配置")
        print(f"数据库密码：***")
        print("===============")

# 创建配置实例
config = AppConfig()

# 测试运行
if __name__ == "__main__":
    config.show_config()