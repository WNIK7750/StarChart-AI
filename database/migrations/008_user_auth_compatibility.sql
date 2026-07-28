-- ai-nav:add-column-if-missing user_accounts token_version INTEGER NOT NULL DEFAULT 0 CHECK (token_version >= 0)

CREATE TABLE IF NOT EXISTS user_security_questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  question_order INTEGER NOT NULL CHECK (question_order BETWEEN 1 AND 3),
  question_text TEXT NOT NULL,
  answer_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  UNIQUE (user_id, question_order)
);

CREATE INDEX IF NOT EXISTS idx_user_security_questions_user
ON user_security_questions(user_id, question_order);
