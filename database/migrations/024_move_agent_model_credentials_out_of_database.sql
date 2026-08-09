CREATE TABLE user_agent_model_settings_without_credentials (
  user_id INTEGER PRIMARY KEY,
  provider_name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  model_id TEXT NOT NULL,
  max_output_tokens INTEGER NOT NULL DEFAULT 1200
    CHECK (max_output_tokens BETWEEN 256 AND 8192),
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

INSERT INTO user_agent_model_settings_without_credentials(
  user_id, provider_name, base_url, model_id, max_output_tokens, enabled,
  connection_status, connection_error_code, connection_checked_at,
  version, created_at, updated_at
)
SELECT
  user_id, provider_name, base_url, model_id, max_output_tokens, enabled,
  'needs_retest', NULL, NULL, version + 1, created_at, CURRENT_TIMESTAMP
FROM user_agent_model_settings;

DROP TABLE user_agent_model_settings;

ALTER TABLE user_agent_model_settings_without_credentials
RENAME TO user_agent_model_settings;
