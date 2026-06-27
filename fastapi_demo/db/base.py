# SQLAlchemy 核心组件：创建数据库引擎、ORM基类、会话工厂
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 导入全局配置实例，读取数据库连接账号、地址、端口等信息
from config import config

# 拼接PostgreSQL标准连接字符串
# 格式：postgresql://用户名:密码@数据库地址:端口/数据库名
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{config.db_user}:{config.db_pwd}"
    f"@{config.db_host}:{config.db_port}/{config.db_name}"
)

# 创建数据库引擎，全局唯一，管理底层连接池
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # 连接池预检测：每次取用连接前ping数据库，自动剔除断开的无效连接，避免线上断连报错
    pool_pre_ping=True,
    # echo=False：关闭SQL语句打印，生产环境建议关闭；开发可改为True查看执行SQL
    echo=False,
)

# 会话工厂：用来生成数据库会话对象
# autocommit=False：关闭自动提交，必须手动commit事务
# autoflush=False：操作对象不会自动刷新到数据库，按需flush
# bind=engine：绑定上面创建的数据库引擎
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM模型基类，所有数据库表模型都要继承这个Base
# 后续 Base.metadata.create_all(engine) 可自动创建所有数据表
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖注入专用数据库会话生成器
    使用yield实现上下文管理，请求结束自动关闭会话释放连接
    使用方式：db: Session = Depends(get_db)
    """
    # 创建本次请求专属数据库会话
    db = SessionLocal()
    try:
        # 把会话提供给接口/业务函数使用
        yield db
    finally:
        # 无论请求正常/异常，最终都会执行close，归还连接到连接池
        db.close()