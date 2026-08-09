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
  link_status TEXT NOT NULL DEFAULT 'unchecked'
    CHECK (link_status IN ('unchecked', 'healthy', 'degraded', 'unavailable')),
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
  link_status TEXT NOT NULL DEFAULT 'unchecked'
    CHECK (link_status IN ('unchecked', 'healthy', 'degraded', 'unavailable')),
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
  aliases_json TEXT NOT NULL DEFAULT '[]',
  icon_path TEXT NOT NULL DEFAULT '',
  icon_fallbacks_json TEXT NOT NULL DEFAULT '[]',
  publication_status TEXT NOT NULL DEFAULT 'published'
    CHECK (publication_status IN ('draft', 'published', 'archived')),
  link_status TEXT NOT NULL DEFAULT 'unchecked'
    CHECK (link_status IN ('unchecked', 'healthy', 'degraded', 'unavailable')),
  last_checked_at TEXT,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_code) REFERENCES tool_categories(code),
  FOREIGN KEY (category_code, subcategory_name) REFERENCES tool_subcategories(category_code, name)
);

CREATE INDEX IF NOT EXISTS idx_ai_tools_category ON ai_tools(category_code);
CREATE INDEX IF NOT EXISTS idx_ai_tools_subcategory ON ai_tools(category_code, subcategory_name);
CREATE INDEX IF NOT EXISTS idx_ai_tools_latest ON ai_tools(is_latest, sort_order);

CREATE TABLE IF NOT EXISTS tool_placements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_slug TEXT NOT NULL,
  category_code TEXT NOT NULL,
  subcategory_name TEXT NOT NULL,
  heat INTEGER NOT NULL DEFAULT 0 CHECK (heat BETWEEN 0 AND 100),
  tag TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tool_slug) REFERENCES ai_tools(slug),
  FOREIGN KEY (category_code, subcategory_name) REFERENCES tool_subcategories(category_code, name),
  UNIQUE (tool_slug, category_code, subcategory_name)
);

CREATE INDEX IF NOT EXISTS idx_tool_placements_category
ON tool_placements(category_code, subcategory_name, sort_order);

CREATE INDEX IF NOT EXISTS idx_tool_placements_tool
ON tool_placements(tool_slug, sort_order);

CREATE TABLE IF NOT EXISTS tool_latest_slots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_slug TEXT NOT NULL,
  display_name TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT '',
  label TEXT NOT NULL DEFAULT '',
  mark TEXT NOT NULL DEFAULT 'AI',
  logo_class TEXT NOT NULL DEFAULT 'logo-chat',
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tool_slug) REFERENCES ai_tools(slug),
  UNIQUE (tool_slug)
);

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

CREATE TABLE IF NOT EXISTS user_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_uid TEXT NOT NULL UNIQUE,
  username TEXT UNIQUE,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  account_status TEXT NOT NULL DEFAULT 'active' CHECK (account_status IN ('active', 'pending', 'locked', 'disabled', 'deleted')),
  token_version INTEGER NOT NULL DEFAULT 0 CHECK (token_version >= 0),
  email_verified INTEGER NOT NULL DEFAULT 0 CHECK (email_verified IN (0, 1)),
  phone_verified INTEGER NOT NULL DEFAULT 0 CHECK (phone_verified IN (0, 1)),
  last_login_at TEXT,
  last_login_ip TEXT,
  deleted_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_accounts_status
ON user_accounts(account_status);

CREATE INDEX IF NOT EXISTS idx_user_accounts_created
ON user_accounts(created_at);

CREATE TABLE IF NOT EXISTS user_auth_passwords (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  password_algo TEXT NOT NULL DEFAULT 'pbkdf2_sha256',
  password_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  failed_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_auth_passwords_locked_until
ON user_auth_passwords(locked_until);

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

CREATE TABLE IF NOT EXISTS user_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  avatar_url TEXT,
  bio TEXT,
  role_title TEXT,
  learning_level TEXT NOT NULL DEFAULT 'beginner' CHECK (learning_level IN ('beginner', 'intermediate', 'advanced')),
  target_direction TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  theme TEXT NOT NULL DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'system')),
  language TEXT NOT NULL DEFAULT 'zh-CN',
  cn_first INTEGER NOT NULL DEFAULT 1 CHECK (cn_first IN (0, 1)),
  free_first INTEGER NOT NULL DEFAULT 0 CHECK (free_first IN (0, 1)),
  show_external_resources INTEGER NOT NULL DEFAULT 1 CHECK (show_external_resources IN (0, 1)),
  agent_memory_enabled INTEGER NOT NULL DEFAULT 0 CHECK (agent_memory_enabled IN (0, 1)),
  preference_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE TABLE IF NOT EXISTS user_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  refresh_token_hash TEXT NOT NULL UNIQUE,
  device_name TEXT,
  user_agent TEXT,
  ip_address TEXT,
  country_region TEXT,
  is_persistent INTEGER NOT NULL DEFAULT 0 CHECK (is_persistent IN (0, 1)),
  is_revoked INTEGER NOT NULL DEFAULT 0 CHECK (is_revoked IN (0, 1)),
  revoked_at TEXT,
  expires_at TEXT NOT NULL,
  last_seen_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user
ON user_sessions(user_id, is_revoked, expires_at);

CREATE INDEX IF NOT EXISTS idx_user_sessions_expires
ON user_sessions(expires_at);

CREATE TABLE IF NOT EXISTS user_verification_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER,
  target TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (purpose IN ('email_verify', 'phone_verify', 'password_reset', 'email_change')),
  token_hash TEXT NOT NULL UNIQUE,
  consumed_at TEXT,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_verification_tokens_target
ON user_verification_tokens(target, purpose, expires_at);

CREATE TABLE IF NOT EXISTS roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT,
  is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  resource TEXT NOT NULL,
  action TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (resource, action)
);

CREATE TABLE IF NOT EXISTS role_permissions (
  role_id INTEGER NOT NULL,
  permission_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (role_id, permission_id),
  FOREIGN KEY (role_id) REFERENCES roles(id),
  FOREIGN KEY (permission_id) REFERENCES permissions(id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_permission
ON role_permissions(permission_id);

CREATE TABLE IF NOT EXISTS user_role_assignments (
  user_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL,
  assigned_by INTEGER,
  assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  FOREIGN KEY (role_id) REFERENCES roles(id),
  FOREIGN KEY (assigned_by) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_role_assignments_role
ON user_role_assignments(role_id);

CREATE TABLE IF NOT EXISTS user_login_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  login_identifier TEXT NOT NULL,
  result TEXT NOT NULL CHECK (result IN ('success', 'failed')),
  failure_reason TEXT,
  ip_address TEXT,
  user_agent TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_login_logs_user_time
ON user_login_logs(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_user_login_logs_identifier_time
ON user_login_logs(login_identifier, created_at);

CREATE TABLE IF NOT EXISTS user_auth_rate_limits (
  scope TEXT NOT NULL,
  subject_hash TEXT NOT NULL,
  window_key INTEGER NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 0 CHECK (request_count >= 0),
  expires_at INTEGER NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (scope, subject_hash)
);

CREATE INDEX IF NOT EXISTS idx_user_auth_rate_limits_expiry
ON user_auth_rate_limits(expires_at);

CREATE TABLE IF NOT EXISTS user_audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_user_id INTEGER,
  target_user_id INTEGER,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  ip_address TEXT,
  user_agent TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (actor_user_id) REFERENCES user_accounts(id),
  FOREIGN KEY (target_user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_audit_logs_actor
ON user_audit_logs(actor_user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_user_audit_logs_target
ON user_audit_logs(target_user_id, created_at);

CREATE TABLE IF NOT EXISTS user_privacy_consent_events (
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

CREATE INDEX IF NOT EXISTS idx_user_privacy_consent_current
ON user_privacy_consent_events(user_id, consent_type, id DESC);

CREATE TABLE IF NOT EXISTS user_data_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_uid TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  request_type TEXT NOT NULL CHECK (request_type IN ('export', 'deletion')),
  status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'cancelled', 'rejected')),
  reason_code TEXT,
  scheduled_for TEXT,
  retention_until TEXT,
  completed_at TEXT,
  cancelled_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_user_data_requests_user_time
ON user_data_requests(user_id, request_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_data_requests_lifecycle
ON user_data_requests(request_type, status, scheduled_for, retention_until);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_data_requests_active_deletion
ON user_data_requests(user_id)
WHERE request_type = 'deletion' AND status IN ('pending', 'processing');

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

CREATE TABLE IF NOT EXISTS user_learning_progress (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  node_slug TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
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
  target_type TEXT NOT NULL
    CHECK (target_type IN ('learning_node', 'learning_material', 'learning_link')),
  target_key TEXT NOT NULL,
  activity_type TEXT NOT NULL
    CHECK (activity_type IN ('view_node', 'start_material', 'open_resource', 'complete_section')),
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
  target_type TEXT NOT NULL
    CHECK (target_type IN ('learning_node', 'learning_material', 'learning_link', 'tool', 'workflow')),
  target_key TEXT NOT NULL,
  title_snapshot TEXT NOT NULL,
  description_snapshot TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id),
  UNIQUE (user_id, target_type, target_key)
);

CREATE INDEX IF NOT EXISTS idx_user_favorites_user
ON user_favorites(user_id, target_type, created_at DESC);

CREATE TABLE IF NOT EXISTS user_agent_model_settings (
  user_id INTEGER PRIMARY KEY,
  provider_name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  model_id TEXT NOT NULL,
  api_key_ciphertext TEXT NOT NULL DEFAULT '',
  max_output_tokens INTEGER NOT NULL DEFAULT 1200
    CHECK (max_output_tokens BETWEEN 256 AND 8192),
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  connection_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (connection_status IN ('pending', 'healthy', 'needs_retest', 'error')),
  connection_error_code TEXT,
  connection_checked_at TEXT,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO roles(code, name, description, is_system) VALUES
('user', '普通用户', '默认登录用户，可管理自己的资料、偏好和会话。', 1),
('admin', '系统管理员', '拥有用户、内容、工具和审计管理权限。', 1),
('operator', '内容运营', '维护学习资料、工具库和站内内容。', 1),
('reviewer', '审核员', '查看审计记录和处理风险内容。', 1);

INSERT OR IGNORE INTO permissions(code, name, resource, action, description) VALUES
('learning:read', '查看学习内容', 'learning', 'read', '查看公开学习路线、节点和资料。'),
('learning:manage', '管理学习内容', 'learning', 'manage', '维护学习路线、节点和资料。'),
('tools:read', '查看工具库', 'tools', 'read', '查看公开 AI 工具和工作流。'),
('tools:manage', '管理工具库', 'tools', 'manage', '维护 AI 工具分类、工具和工作流。'),
('agent:chat', '使用 Agent', 'agent', 'chat', '使用站内 Agent 问答和生成工作流。'),
('agent:manage', '管理 Agent', 'agent', 'manage', '管理 Agent 配置、评估和运行记录。'),
('users:read', '查看用户', 'users', 'read', '查看用户基础资料和状态。'),
('users:manage', '管理用户', 'users', 'manage', '管理账号状态和用户角色。'),
('audit:read', '查看审计', 'audit', 'read', '查看登录日志和审计日志。');

INSERT OR IGNORE INTO role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('learning:read', 'tools:read', 'agent:chat')
WHERE r.code = 'user';

INSERT OR IGNORE INTO role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('learning:read', 'learning:manage', 'tools:read', 'tools:manage', 'agent:chat')
WHERE r.code = 'operator';

INSERT OR IGNORE INTO role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON p.code IN ('learning:read', 'tools:read', 'agent:chat', 'audit:read')
WHERE r.code = 'reviewer';

INSERT OR IGNORE INTO role_permissions(role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p
WHERE r.code = 'admin';
