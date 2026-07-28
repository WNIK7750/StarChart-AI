-- Link health is operational metadata owned by the existing content domains.
-- ai-nav:add-column-if-missing learning_materials link_status TEXT NOT NULL DEFAULT 'unchecked' CHECK (link_status IN ('unchecked', 'healthy', 'degraded', 'unavailable'))
-- ai-nav:add-column-if-missing learning_node_links link_status TEXT NOT NULL DEFAULT 'unchecked' CHECK (link_status IN ('unchecked', 'healthy', 'degraded', 'unavailable'))
-- ai-nav:add-column-if-missing ai_tools publication_status TEXT NOT NULL DEFAULT 'published' CHECK (publication_status IN ('draft', 'published', 'archived'))
-- ai-nav:add-column-if-missing ai_tools link_status TEXT NOT NULL DEFAULT 'unchecked' CHECK (link_status IN ('unchecked', 'healthy', 'degraded', 'unavailable'))
-- ai-nav:add-column-if-missing ai_tools last_checked_at TEXT

CREATE INDEX IF NOT EXISTS idx_learning_materials_link_status
ON learning_materials(publication_status, link_status, node_slug);

CREATE INDEX IF NOT EXISTS idx_learning_node_links_link_status
ON learning_node_links(publication_status, link_status, node_slug);

CREATE INDEX IF NOT EXISTS idx_ai_tools_publication_link
ON ai_tools(publication_status, link_status, sort_order);
