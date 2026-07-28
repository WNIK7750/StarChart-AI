ALTER TABLE user_sessions ADD COLUMN token_family_uid TEXT;
ALTER TABLE user_sessions ADD COLUMN parent_session_id INTEGER;
ALTER TABLE user_sessions ADD COLUMN replaced_by_session_id INTEGER;
ALTER TABLE user_sessions ADD COLUMN revoked_reason TEXT CHECK (
  revoked_reason IS NULL OR revoked_reason IN ('logout', 'password_changed', 'password_reset', 'rotated', 'replay_detected', 'account_disabled')
);

UPDATE user_sessions
SET token_family_uid = session_uid
WHERE token_family_uid IS NULL;

CREATE INDEX IF NOT EXISTS idx_user_sessions_token_family
ON user_sessions(user_id, token_family_uid, is_revoked, expires_at);

CREATE INDEX IF NOT EXISTS idx_user_sessions_parent
ON user_sessions(parent_session_id);
