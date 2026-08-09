CREATE TABLE IF NOT EXISTS user_agent_model_settings (
  user_id INTEGER PRIMARY KEY,
  provider_name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  model_id TEXT NOT NULL,
  api_key_ciphertext TEXT NOT NULL,
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
