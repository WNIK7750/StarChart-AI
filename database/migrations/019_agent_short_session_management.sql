-- Short-term session presentation metadata remains in the same user-owned TTL cache.
-- ai-nav:add-column-if-missing agent_chat_sessions title_customized INTEGER NOT NULL DEFAULT 0 CHECK (title_customized IN (0, 1))
-- ai-nav:add-column-if-missing agent_chat_sessions pinned_at TEXT

CREATE INDEX IF NOT EXISTS idx_agent_chat_sessions_user_pinned
ON agent_chat_sessions(user_id, pinned_at DESC, updated_at DESC, id DESC);
