UPDATE navigation_items
SET href = 'assistant.html'
WHERE code = 'assistant';

DELETE FROM navigation_items
WHERE code = 'about';
