ALTER TABLE roadmap_edges
ADD COLUMN relation_type TEXT NOT NULL DEFAULT 'prerequisite'
CHECK (relation_type IN ('prerequisite', 'recommended_next', 'related'));

ALTER TABLE learning_material_sections
ADD COLUMN section_uid TEXT;

UPDATE learning_material_sections
SET section_uid = 'sec_' || material_id || '_' || chapter_no || '_' || section_no
WHERE section_uid IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_material_sections_uid
ON learning_material_sections(section_uid);

CREATE INDEX IF NOT EXISTS idx_roadmap_edges_relation
ON roadmap_edges(from_slug, relation_type, sort_order);

CREATE TABLE IF NOT EXISTS user_learning_section_progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  node_slug TEXT NOT NULL,
  section_uid TEXT NOT NULL,
  is_completed INTEGER NOT NULL DEFAULT 0 CHECK (is_completed IN (0, 1)),
  completed_at TEXT,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug),
  FOREIGN KEY (section_uid) REFERENCES learning_material_sections(section_uid),
  UNIQUE (user_id, section_uid)
);

CREATE INDEX IF NOT EXISTS idx_user_learning_section_progress_node
ON user_learning_section_progress(user_id, node_slug, is_completed);
