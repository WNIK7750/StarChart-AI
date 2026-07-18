-- Preserve the user's remember-me choice across refresh-token rotation.
-- ai-nav:add-column-if-missing user_sessions is_persistent INTEGER NOT NULL DEFAULT 0 CHECK (is_persistent IN (0, 1))

-- Record explicit re-consent performed in the login dialog as its own source.
CREATE TABLE user_privacy_consent_events_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  consent_type TEXT NOT NULL CHECK (consent_type IN ('privacy_policy', 'agent_memory')),
  policy_version TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('granted', 'revoked')),
  source TEXT NOT NULL CHECK (source IN ('settings', 'registration', 'login', 'admin', 'migration')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

INSERT INTO user_privacy_consent_events_v2(
  id, event_uid, user_id, consent_type, policy_version, action, source, created_at
)
SELECT id, event_uid, user_id, consent_type, policy_version, action, source, created_at
FROM user_privacy_consent_events;

DROP TABLE user_privacy_consent_events;
ALTER TABLE user_privacy_consent_events_v2 RENAME TO user_privacy_consent_events;

CREATE INDEX idx_user_privacy_consent_current
ON user_privacy_consent_events(user_id, consent_type, id DESC);
