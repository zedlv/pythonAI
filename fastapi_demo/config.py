# 导入工具
from dotenv import load_dotenv
import os

# 异常处理：捕获文件读取失败
try:
    # 文件读写：加载 .env 文件
    load_dotenv()
except Exception as e:
    print(f"配置加载失败：{e}")

# 类：封装所有配置
class AppConfig:
    def __init__(self):
        # 读取环境变量
        self.api_key = os.getenv("API_KEY")
        self.api_token = os.getenv("API_TOKEN", "mytoken123456")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_user = os.getenv("DB_USER")
        self.db_pwd = os.getenv("DB_PWD")

    # 安全打印：不泄露密钥
    def show_config(self):
        print("=== 项目配置 ===")
        print(f"数据库地址：{self.db_host}")
        print(f"数据库端口：{self.db_port}")
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