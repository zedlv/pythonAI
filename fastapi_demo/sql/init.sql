CREATE TABLE IF NOT EXISTS chat_messages (
    id bigserial PRIMARY KEY,
    session_id varchar(64) NOT NULL,
    user_id varchar(32) NOT NULL DEFAULT 'default_user',
    user_content text NOT NULL,
    ai_content text NULL,
    msg_status smallint NOT NULL DEFAULT 1,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

COMMENT ON COLUMN chat_messages.id IS '自增主键ID';
COMMENT ON COLUMN chat_messages.session_id IS '会话唯一ID';
COMMENT ON COLUMN chat_messages.user_id IS '用户唯一标识';
COMMENT ON COLUMN chat_messages.user_content IS '用户输入的聊天消息';
COMMENT ON COLUMN chat_messages.ai_content IS 'AI模型回复内容';
COMMENT ON COLUMN chat_messages.msg_status IS '消息状态：0-失败 1-正常 2-处理中';
COMMENT ON COLUMN chat_messages.created_at IS '记录创建时间';
COMMENT ON COLUMN chat_messages.updated_at IS '记录最后更新时间';
