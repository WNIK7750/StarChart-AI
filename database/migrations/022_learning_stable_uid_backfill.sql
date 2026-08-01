UPDATE learning_materials
SET material_uid = 'mat_' || replace(node_slug, '-', '_') ||
  CASE WHEN is_primary = 1 THEN '_primary' ELSE '_' || id END
WHERE material_uid IS NULL OR trim(material_uid) = '';

UPDATE learning_material_sections
SET section_uid = 'sec_' || material_id || '_' || chapter_no || '_' || section_no
WHERE section_uid IS NULL OR trim(section_uid) = '';

UPDATE learning_node_links
SET link_uid = 'lnk_' || replace(node_slug, '-', '_') || '_' || id
WHERE link_uid IS NULL OR trim(link_uid) = '';
