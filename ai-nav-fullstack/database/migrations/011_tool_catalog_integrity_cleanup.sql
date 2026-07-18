-- Keep legacy compatibility rows inactive and align the shared free/open-source flag.
UPDATE tool_subcategories
SET is_active = 0,
    updated_at = CURRENT_TIMESTAMP
WHERE category_code IN (
  SELECT code FROM tool_categories WHERE is_active = 0
);

UPDATE ai_tools
SET is_free = CASE
      WHEN EXISTS (
        SELECT 1
        FROM tool_placements placement
        WHERE placement.tool_slug = ai_tools.slug
          AND (
            placement.tag LIKE '%免费%'
            OR placement.tag LIKE '%开源%'
            OR lower(placement.tag) LIKE '%free%'
            OR lower(placement.tag) LIKE '%open%'
          )
      ) THEN 1
      ELSE 0
    END,
    updated_at = CURRENT_TIMESTAMP;
