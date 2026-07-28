-- User-owned long conversations are durable and separate from the short-term TTL cache.
CREATE TABLE agent_long_conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  source_session_uid TEXT NOT NULL,
  title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
  pinned_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE,
  UNIQUE (user_id, source_session_uid)
);

CREATE INDEX idx_agent_long_conversations_user_pinned
ON agent_long_conversations(user_id, pinned_at DESC, updated_at DESC, id DESC);

CREATE TABLE agent_long_conversation_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_uid TEXT NOT NULL UNIQUE,
  conversation_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 6000),
  request_id TEXT NOT NULL CHECK (length(request_id) BETWEEN 1 AND 128),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES agent_long_conversations(id) ON DELETE CASCADE,
  UNIQUE (conversation_id, request_id, role)
);

CREATE INDEX idx_agent_long_conversation_messages_order
ON agent_long_conversation_messages(conversation_id, id);
