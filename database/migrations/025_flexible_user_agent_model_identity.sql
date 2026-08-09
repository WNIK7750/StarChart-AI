CREATE TABLE user_agent_model_settings_flexible (
  user_id INTEGER PRIMARY KEY,
  provider_key TEXT NOT NULL DEFAULT 'custom',
  provider_name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  model_display_name TEXT NOT NULL,
  model_id TEXT NOT NULL,
  max_output_tokens INTEGER
    CHECK (max_output_tokens IS NULL OR max_output_tokens BETWEEN 256 AND 65536),
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  connection_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (connection_status IN ('pending', 'healthy', 'needs_retest', 'error')),
  connection_error_code TEXT,
  connection_checked_at TEXT,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
);

INSERT INTO user_agent_model_settings_flexible(
  user_id, provider_key, provider_name, base_url,
  model_display_name, model_id, max_output_tokens, enabled,
  connection_status, connection_error_code, connection_checked_at,
  version, created_at, updated_at
)
SELECT
  user_id,
  CASE LOWER(provider_name)
    WHEN 'dashscope' THEN 'dashscope'
    WHEN 'openai' THEN 'openai'
    WHEN 'openrouter' THEN 'openrouter'
    WHEN 'deepseek' THEN 'deepseek'
    ELSE 'custom'
  END,
  CASE LOWER(provider_name)
    WHEN 'dashscope' THEN '阿里云百炼 / DashScope'
    WHEN 'openai' THEN 'OpenAI'
    WHEN 'openrouter' THEN 'OpenRouter'
    WHEN 'deepseek' THEN 'DeepSeek'
    ELSE provider_name
  END,
  base_url, model_id, model_id, max_output_tokens, enabled,
  connection_status, connection_error_code, connection_checked_at,
  version + 1, created_at, CURRENT_TIMESTAMP
FROM user_agent_model_settings;

DROP TABLE user_agent_model_settings;

ALTER TABLE user_agent_model_settings_flexible
RENAME TO user_agent_model_settings;
