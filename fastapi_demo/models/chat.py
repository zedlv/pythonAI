from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, SmallInteger, String, Text

from db.base import Base


class ChatMessage(Base):
    """聊天记录 ORM 实体"""

    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    user_id = Column(String(32), nullable=False, default="default_user", comment="用户唯一标识")
    session_id = Column(String(64), nullable=False, comment="会话ID")
    user_content = Column(Text, nullable=False, comment="用户消息")
    ai_content = Column(Text, nullable=True, comment="AI回复内容")
    msg_status = Column(SmallInteger, nullable=False, default=1, comment="0失败 1正常 2处理中")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment="更新时间")
