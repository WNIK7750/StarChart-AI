-- Minimal, user-owned Agent session history.
-- Only the user message and the final validated assistant answer are retained.
CREATE TABLE agent_chat_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_agent_chat_sessions_user_updated
ON agent_chat_sessions(user_id, updated_at DESC, id DESC);

CREATE INDEX idx_agent_chat_sessions_expires
ON agent_chat_sessions(expires_at);

CREATE TABLE agent_chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_uid TEXT NOT NULL UNIQUE,
  session_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 6000),
  request_id TEXT NOT NULL CHECK (length(request_id) BETWEEN 1 AND 128),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES agent_chat_sessions(id) ON DELETE CASCADE,
  UNIQUE (session_id, request_id, role)
);

CREATE INDEX idx_agent_chat_messages_session_order
ON agent_chat_messages(session_id, id);
