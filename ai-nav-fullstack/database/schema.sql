PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_settings (
  setting_key TEXT PRIMARY KEY,
  setting_value TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS navigation_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  href TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS difficulty_levels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  color TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_domains (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  color TEXT NOT NULL,
  glow_color TEXT NOT NULL,
  description TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roadmap_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  subtitle TEXT NOT NULL,
  difficulty_code TEXT NOT NULL,
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  width INTEGER NOT NULL DEFAULT 170,
  height INTEGER NOT NULL DEFAULT 48,
  is_current INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (difficulty_code) REFERENCES difficulty_levels(code)
);

CREATE INDEX IF NOT EXISTS idx_roadmap_nodes_difficulty ON roadmap_nodes(difficulty_code);

CREATE TABLE IF NOT EXISTS roadmap_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_slug TEXT NOT NULL,
  to_slug TEXT NOT NULL,
  path_d TEXT NOT NULL,
  line_type TEXT NOT NULL DEFAULT 'dashed',
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (from_slug) REFERENCES roadmap_nodes(slug),
  FOREIGN KEY (to_slug) REFERENCES roadmap_nodes(slug)
);

CREATE INDEX IF NOT EXISTS idx_roadmap_edges_from ON roadmap_edges(from_slug);
CREATE INDEX IF NOT EXISTS idx_roadmap_edges_to ON roadmap_edges(to_slug);

CREATE TABLE IF NOT EXISTS roadmap_domain_nodes (
  domain_code TEXT NOT NULL,
  node_slug TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (domain_code, node_slug),
  FOREIGN KEY (domain_code) REFERENCES knowledge_domains(code),
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug)
);

CREATE TABLE IF NOT EXISTS learning_resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  node_slug TEXT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  cover_label TEXT NOT NULL,
  cover_text TEXT NOT NULL,
  cover_theme TEXT NOT NULL,
  href TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug)
);

CREATE INDEX IF NOT EXISTS idx_learning_resources_node ON learning_resources(node_slug);

CREATE TABLE IF NOT EXISTS learning_materials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node_slug TEXT NOT NULL,
  title TEXT NOT NULL,
  provider TEXT NOT NULL,
  material_type TEXT NOT NULL DEFAULT 'course',
  url TEXT NOT NULL,
  start_url TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'zh-CN',
  access_type TEXT NOT NULL DEFAULT 'external' CHECK (access_type IN ('cn', 'external')),
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
  cover_label TEXT NOT NULL DEFAULT 'CORE',
  cover_text TEXT NOT NULL DEFAULT 'AI',
  cover_theme TEXT NOT NULL DEFAULT 'g-purple',
  description TEXT NOT NULL,
  overview TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_materials_primary
ON learning_materials(node_slug, is_primary)
WHERE is_primary = 1;

CREATE INDEX IF NOT EXISTS idx_learning_materials_node
ON learning_materials(node_slug, sort_order);

CREATE TABLE IF NOT EXISTS learning_material_sections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  material_id INTEGER NOT NULL,
  chapter_no INTEGER NOT NULL,
  section_no INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 0,
  source_url TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (material_id) REFERENCES learning_materials(id),
  UNIQUE (material_id, chapter_no, section_no)
);

CREATE INDEX IF NOT EXISTS idx_learning_material_sections_material
ON learning_material_sections(material_id, sort_order);

CREATE TABLE IF NOT EXISTS learning_node_tags (
  node_slug TEXT NOT NULL,
  tag TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (node_slug, tag),
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug)
);

CREATE TABLE IF NOT EXISTS learning_node_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node_slug TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  url TEXT NOT NULL,
  link_type TEXT NOT NULL DEFAULT 'reference',
  access_type TEXT NOT NULL DEFAULT 'external' CHECK (access_type IN ('cn', 'external')),
  accent_color TEXT NOT NULL DEFAULT '#7C5CFF',
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (node_slug) REFERENCES roadmap_nodes(slug)
);

CREATE INDEX IF NOT EXISTS idx_learning_node_links_node
ON learning_node_links(node_slug, sort_order);

CREATE TABLE IF NOT EXISTS tool_categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  icon TEXT NOT NULL,
  logo_class TEXT NOT NULL,
  description TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_subcategories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category_code TEXT NOT NULL,
  name TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_code) REFERENCES tool_categories(code),
  UNIQUE (category_code, name)
);

CREATE TABLE IF NOT EXISTS ai_tools (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  category_code TEXT NOT NULL,
  subcategory_name TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  mark TEXT NOT NULL,
  tag TEXT NOT NULL,
  official_url TEXT NOT NULL DEFAULT '#',
  is_free INTEGER NOT NULL DEFAULT 0 CHECK (is_free IN (0, 1)),
  is_latest INTEGER NOT NULL DEFAULT 0 CHECK (is_latest IN (0, 1)),
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_code) REFERENCES tool_categories(code),
  FOREIGN KEY (category_code, subcategory_name) REFERENCES tool_subcategories(category_code, name)
);

CREATE INDEX IF NOT EXISTS idx_ai_tools_category ON ai_tools(category_code);
CREATE INDEX IF NOT EXISTS idx_ai_tools_subcategory ON ai_tools(category_code, subcategory_name);
CREATE INDEX IF NOT EXISTS idx_ai_tools_latest ON ai_tools(is_latest, sort_order);

CREATE TABLE IF NOT EXISTS tool_workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  badge TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_tools (
  workflow_code TEXT NOT NULL,
  tool_slug TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (workflow_code, tool_slug),
  FOREIGN KEY (workflow_code) REFERENCES tool_workflows(code),
  FOREIGN KEY (tool_slug) REFERENCES ai_tools(slug)
);
