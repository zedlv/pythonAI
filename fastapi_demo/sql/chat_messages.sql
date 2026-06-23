-- D15: chat_messages 建表 + 注释 + 索引 + 测试数据
-- 用法: psql -U postgres -d fastapi_chat_db -f sql/chat_messages.sql
/*
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
PGPASSWORD=123456 psql -h localhost -p 5432 -U lvasia -d fastapi_chat_db \
  -f sql/chat_messages.sql
*/

-- ========== 1. 建表 ==========
CREATE TABLE IF NOT EXISTS chat_messages (
    id bigserial PRIMARY KEY,
    session_id varchar(64) NOT NULL,
    user_content text NOT NULL,
    ai_content text NULL,
    msg_status smallint NOT NULL DEFAULT 1,
    created_at timestamp NOT NULL DEFAULT now(),
    updated_at timestamp NOT NULL DEFAULT now()
);

-- ========== 2. 字段注释 ==========
COMMENT ON COLUMN chat_messages.id IS '自增主键ID';
COMMENT ON COLUMN chat_messages.session_id IS '会话唯一ID，关联同一场对话';
COMMENT ON COLUMN chat_messages.user_content IS '用户输入的聊天消息';
COMMENT ON COLUMN chat_messages.ai_content IS 'AI模型回复内容';
COMMENT ON COLUMN chat_messages.msg_status IS '消息状态：0-调用失败 1-正常完成 2-处理中';
COMMENT ON COLUMN chat_messages.created_at IS '记录创建时间';
COMMENT ON COLUMN chat_messages.updated_at IS '记录最后更新时间';

-- ========== 3. 业务索引 ==========
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

-- ========== D17 扩展：用户维度 ==========
ALTER TABLE chat_messages
ADD COLUMN IF NOT EXISTS user_id varchar(32) NOT NULL DEFAULT 'default_user';
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
COMMENT ON COLUMN chat_messages.user_id IS '用户唯一标识';

-- ========== 4. 测试：插入 ==========
INSERT INTO chat_messages (session_id, user_content, ai_content, msg_status)
VALUES (
    'sess_001_20260615',
    '学习PostgreSQL表设计',
    'PostgreSQL是高性能开源关系型数据库，适配FastAPI异步项目',
    1
);

-- ========== 5. 测试：查询 ==========
SELECT * FROM chat_messages
WHERE session_id = 'sess_001_20260615'
ORDER BY created_at ASC;

-- ========== 6. 测试：更新 ==========
UPDATE chat_messages
SET
    ai_content = '补充说明：搭配SQLAlchemy可快速实现Python项目数据持久化',
    updated_at = now(),
    msg_status = 1
WHERE id = 1;

-- ========== 7. 测试：查失败记录 ==========
SELECT * FROM chat_messages WHERE msg_status = 0;
