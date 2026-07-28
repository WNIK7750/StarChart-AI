CREATE TABLE IF NOT EXISTS user_learning_progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  node_slug TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
  progress_percent INTEGER NOT NULL DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
  started_at TEXT,
  completed_at TEXT,
  last_studied_at TEXT,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug),
  UNIQUE (user_id, node_slug)
);

CREATE INDEX IF NOT EXISTS idx_user_learning_progress_user
ON user_learning_progress(user_id, status, last_studied_at DESC);

CREATE TABLE IF NOT EXISTS user_learning_activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  activity_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  node_slug TEXT,
  target_type TEXT NOT NULL CHECK (target_type IN ('learning_node', 'learning_material', 'learning_link')),
  target_key TEXT NOT NULL,
  activity_type TEXT NOT NULL CHECK (activity_type IN ('view_node', 'start_material', 'open_resource', 'complete_section')),
  metadata_json TEXT,
  idempotency_key TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug),
  UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_user_learning_activity_user_time
ON user_learning_activity(user_id, created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS user_favorites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  favorite_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('learning_node', 'learning_material', 'learning_link', 'tool', 'workflow')),
  target_key TEXT NOT NULL,
  title_snapshot TEXT NOT NULL,
  description_snapshot TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  UNIQUE (user_id, target_type, target_key)
);

CREATE INDEX IF NOT EXISTS idx_user_favorites_user
ON user_favorites(user_id, target_type, created_at DESC);
