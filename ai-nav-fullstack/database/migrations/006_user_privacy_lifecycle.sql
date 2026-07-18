CREATE TABLE IF NOT EXISTS user_privacy_consent_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  consent_type TEXT NOT NULL CHECK (consent_type IN ('privacy_policy', 'agent_memory')),
  policy_version TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('granted', 'revoked')),
  source TEXT NOT NULL CHECK (source IN ('settings', 'registration', 'admin', 'migration')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_privacy_consent_current
ON user_privacy_consent_events(user_id, consent_type, id DESC);

CREATE TABLE IF NOT EXISTS user_data_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  request_type TEXT NOT NULL CHECK (request_type IN ('export', 'deletion')),
  status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'cancelled', 'rejected')),
  reason_code TEXT,
  scheduled_for TEXT,
  retention_until TEXT,
  completed_at TEXT,
  cancelled_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_data_requests_user_time
ON user_data_requests(user_id, request_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_data_requests_lifecycle
ON user_data_requests(request_type, status, scheduled_for, retention_until);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_data_requests_active_deletion
ON user_data_requests(user_id)
WHERE request_type = 'deletion' AND status IN ('pending', 'processing');
