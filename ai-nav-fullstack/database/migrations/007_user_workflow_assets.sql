CREATE TABLE IF NOT EXISTS user_saved_workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  source_type TEXT NOT NULL CHECK (source_type IN ('agent', 'builtin', 'manual')),
  source_ref TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  idempotency_key TEXT NOT NULL,
  archived_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_user_saved_workflows_list
ON user_saved_workflows(user_id, status, updated_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS user_saved_workflow_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  step_uid TEXT NOT NULL UNIQUE,
  workflow_id INTEGER NOT NULL,
  step_order INTEGER NOT NULL CHECK (step_order > 0),
  name TEXT NOT NULL,
  objective TEXT NOT NULL,
  tool_slug TEXT,
  tool_name_snapshot TEXT,
  tool_href_snapshot TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (workflow_id) REFERENCES user_saved_workflows(id) ON DELETE CASCADE,
  UNIQUE (workflow_id, step_order)
);

CREATE INDEX IF NOT EXISTS idx_user_saved_workflow_steps_workflow
ON user_saved_workflow_steps(workflow_id, step_order);
