CREATE TABLE IF NOT EXISTS user_auth_rate_limits (
  scope TEXT NOT NULL,
  subject_hash TEXT NOT NULL,
  window_key INTEGER NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 0 CHECK (request_count >= 0),
  expires_at INTEGER NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (scope, subject_hash)
);

CREATE INDEX IF NOT EXISTS idx_user_auth_rate_limits_expiry
ON user_auth_rate_limits(expires_at);
