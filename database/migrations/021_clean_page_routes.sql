UPDATE navigation_items SET href = '/' WHERE code = 'home';
UPDATE navigation_items SET href = '/learn' WHERE code = 'learn';
UPDATE navigation_items SET href = '/tools' WHERE code = 'tools';
UPDATE navigation_items SET href = '/assistant' WHERE code = 'assistant';

UPDATE learning_resources
SET href = '/learn/' || node_slug
WHERE href LIKE 'learn-node.html?slug=%';
