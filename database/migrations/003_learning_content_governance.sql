ALTER TABLE learning_materials ADD COLUMN material_uid TEXT;
ALTER TABLE learning_materials ADD COLUMN publication_status TEXT NOT NULL DEFAULT 'published'
CHECK (publication_status IN ('draft', 'published', 'archived'));
ALTER TABLE learning_materials ADD COLUMN content_version INTEGER NOT NULL DEFAULT 1
CHECK (content_version > 0);
ALTER TABLE learning_materials ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'unreviewed'
CHECK (quality_status IN ('unreviewed', 'verified', 'stale'));
ALTER TABLE learning_materials ADD COLUMN source_trust TEXT NOT NULL DEFAULT 'unknown'
CHECK (source_trust IN ('official', 'institutional', 'community', 'unknown'));
ALTER TABLE learning_materials ADD COLUMN last_verified_at TEXT;

UPDATE learning_materials
SET material_uid = 'mat_' || replace(node_slug, '-', '_') ||
  CASE WHEN is_primary = 1 THEN '_primary' ELSE '_' || id END
WHERE material_uid IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_materials_uid
ON learning_materials(material_uid);

CREATE INDEX IF NOT EXISTS idx_learning_materials_publication
ON learning_materials(publication_status, node_slug, sort_order);

ALTER TABLE learning_node_links ADD COLUMN link_uid TEXT;
ALTER TABLE learning_node_links ADD COLUMN publication_status TEXT NOT NULL DEFAULT 'published'
CHECK (publication_status IN ('draft', 'published', 'archived'));
ALTER TABLE learning_node_links ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'unreviewed'
CHECK (quality_status IN ('unreviewed', 'verified', 'stale'));
ALTER TABLE learning_node_links ADD COLUMN last_checked_at TEXT;

UPDATE learning_node_links
SET link_uid = 'lnk_' || replace(node_slug, '-', '_') || '_' || id
WHERE link_uid IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_node_links_uid
ON learning_node_links(link_uid);

CREATE INDEX IF NOT EXISTS idx_learning_node_links_publication
ON learning_node_links(publication_status, node_slug, sort_order);
