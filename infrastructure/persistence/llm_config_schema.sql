-- LLM配置表创建脚本
-- 作者：孔利群

-- 大模型配置表
CREATE TABLE llm_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deepseek_api_key TEXT NOT NULL,        -- 加密存储的DeepSeek API密钥
    kimi_api_key TEXT NOT NULL,            -- 加密存储的Kimi API密钥
    encryption_key_hash TEXT NOT NULL,     -- 加密密钥的哈希值
    created_at TEXT NOT NULL,              -- 创建时间
    updated_at TEXT NOT NULL,              -- 更新时间
    
    -- 约束：加密密钥哈希不能为空
    CHECK (encryption_key_hash != '')
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_llm_config_created_at ON llm_config(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_config_updated_at ON llm_config(updated_at);

-- 插入默认配置（可选）
-- INSERT INTO llm_config (deepseek_api_key, kimi_api_key, encryption_key_hash, created_at, updated_at)
-- VALUES ('', '', 'default_hash', datetime('now'), datetime('now'));

-- 表注释
COMMENT ON TABLE llm_config IS '大模型API配置表';
COMMENT ON COLUMN llm_config.deepseek_api_key IS '加密存储的DeepSeek API密钥';
COMMENT ON COLUMN llm_config.kimi_api_key IS '加密存储的Kimi API密钥';
COMMENT ON COLUMN llm_config.encryption_key_hash IS '加密密钥的SHA256哈希值';
COMMENT ON COLUMN llm_config.created_at IS '配置创建时间';
COMMENT ON COLUMN llm_config.updated_at IS '配置最后更新时间';