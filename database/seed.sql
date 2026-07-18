PRAGMA foreign_keys = ON;

INSERT INTO app_settings(setting_key, setting_value, description) VALUES
('site_name', 'AI 知识导航', '站点名称'),
('site_tagline', '从知识地图到工具实践的一站式 AI 学习入口', '站点副标题');

INSERT INTO navigation_items(code, label, href, sort_order) VALUES
('home', '主页', 'index.html', 10),
('learn', '学习', 'learn.html', 20),
('tools', '工具', 'tools.html', 30),
('assistant', '助手', 'assistant.html', 40);

INSERT INTO difficulty_levels(code, name, color, sort_order) VALUES
('intro', '入门', '#16C76F', 10),
('basic', '基础', '#4CCBEA', 20),
('advanced', '进阶', '#FDBA3B', 30),
('practice', '实践', '#EB5AAF', 40),
('engineering', '工程', '#FF8A2A', 50),
('llm', 'LLM', '#744AEF', 60);

INSERT INTO knowledge_domains(code, name, color, glow_color, description, sort_order) VALUES
('core', 'AI 基础', '#6D5EF6', 'rgba(109,94,246,.18)', '建立 AI、Python 与数学概念底座。', 10),
('ml', '机器学习', '#0EA5E9', 'rgba(14,165,233,.18)', '传统机器学习任务、范式与评估闭环。', 20),
('dl', '深度学习与 LLM', '#C084FC', 'rgba(192,132,252,.18)', '神经网络、向量语义、Transformer 与大模型基础。', 30),
('app', '应用开发', '#14B8A6', 'rgba(20,184,166,.18)', 'Prompt、RAG、Agent 与 LLM 应用工程。', 40),
('ops', '工程治理', '#EF4444', 'rgba(239,68,68,.16)', '模型上线、监控、安全和评测治理。', 50);

INSERT INTO roadmap_nodes(slug, title, subtitle, difficulty_code, x, y, is_current, sort_order) VALUES
('ai-literacy', 'AI 通识', '概念、边界', 'intro', 10, 50, 1, 10),
('python', 'Python', '语法、环境', 'intro', 10, 130, 0, 20),
('math-foundation', '数学基础', '概率、线代', 'intro', 10, 210, 0, 30),
('machine-learning', '机器学习', '任务、范式', 'basic', 230, 50, 0, 40),
('supervised-learning', '监督学习', '分类、回归', 'advanced', 230, 130, 0, 50),
('unsupervised-learning', '无监督学习', '聚类、降维', 'advanced', 230, 210, 0, 60),
('training-evaluation', '训练评估', '指标、泛化', 'engineering', 230, 290, 0, 70),
('neural-network', '神经网络', '层、反传', 'practice', 450, 50, 0, 80),
('embedding', 'Embedding', '向量语义', 'advanced', 450, 130, 0, 90),
('transformer', 'Transformer', '注意力', 'llm', 450, 210, 0, 100),
('llm-foundation', 'LLM 基础', '上下文、Token', 'basic', 670, 130, 0, 110),
('fine-tuning-eval', '微调评测', 'SFT、LoRA', 'basic', 670, 210, 0, 120),
('prompt', 'Prompt', '结构化输出', 'basic', 890, 50, 0, 130),
('rag', 'RAG', '检索、向量库', 'basic', 890, 130, 0, 140),
('agent', 'Agent', '规划、调用', 'llm', 890, 210, 0, 150),
('model-ops', '上线治理', '监控、安全', 'engineering', 1110, 130, 0, 160);

INSERT INTO roadmap_domain_nodes(domain_code, node_slug) VALUES
('core', 'ai-literacy'), ('core', 'python'), ('core', 'math-foundation'),
('ml', 'math-foundation'), ('ml', 'machine-learning'), ('ml', 'supervised-learning'), ('ml', 'unsupervised-learning'), ('ml', 'training-evaluation'),
('dl', 'neural-network'), ('dl', 'embedding'), ('dl', 'transformer'), ('dl', 'llm-foundation'), ('dl', 'fine-tuning-eval'),
('app', 'embedding'), ('app', 'llm-foundation'), ('app', 'prompt'), ('app', 'rag'), ('app', 'agent'),
('ops', 'training-evaluation'), ('ops', 'fine-tuning-eval'), ('ops', 'rag'), ('ops', 'agent'), ('ops', 'model-ops');

INSERT INTO roadmap_edges(from_slug, to_slug, path_d, sort_order) VALUES
('ai-literacy', 'machine-learning', 'M 180 74 L 205 74', 10),
('python', 'supervised-learning', 'M 180 154 L 205 154', 20),
('math-foundation', 'unsupervised-learning', 'M 180 234 L 205 234', 30),
('machine-learning', 'neural-network', 'M 400 74 L 425 74 L 425 314 M 425 74 L 450 74 M 425 154 L 450 154 M 425 234 L 450 234', 40),
('training-evaluation', 'llm-foundation', 'M 400 314 L 645 314 L 645 234 M 620 74 L 645 74 L 645 234 L 620 234 M 620 154 L 645 154 M 620 234 L 645 234 M 645 154 L 670 154 M 645 234 L 670 234', 50),
('llm-foundation', 'prompt', 'M 840 154 L 865 154 M 840 234 L 865 234 M 865 74 L 865 234 M 865 74 L 890 74 M 865 154 L 890 154 M 865 234 L 890 234', 60),
('prompt', 'model-ops', 'M 1060 74 L 1085 74 M 1060 154 L 1085 154 M 1060 234 L 1085 234 M 1085 74 L 1085 234 M 1085 154 L 1110 154', 70);

INSERT INTO learning_resources(slug, node_slug, title, description, cover_label, cover_text, cover_theme, href, sort_order, is_featured) VALUES
('ai-literacy-course', 'ai-literacy', 'AI 通识 · 入门必读', '本节点讲解 AI 的定义、发展历史与核心概念', 'CORE', 'AI 通识', 'g-purple', 'learn-node.html?slug=ai-literacy', 10, 1),
('machine-learning-course', 'machine-learning', '机器学习基础', '监督学习、无监督学习、强化学习', 'FUND', 'ML', 'g-pink', 'learn-node.html?slug=machine-learning', 20, 1),
('deep-learning-course', 'neural-network', '深度学习与神经网络', '神经网络原理与常见架构详解', 'DEEP', 'DL', 'g-cyan', 'learn-node.html?slug=neural-network', 30, 1),
('llm-course', 'llm-foundation', '大语言模型原理', 'Transformer 架构与自注意力机制', 'LLM', 'LLM', 'g-green', 'learn-node.html?slug=llm-foundation', 40, 1),
('prompt-course', 'prompt', 'Prompt 工程实战', '结构化提示策略与 30+ 真实场景', 'PRMT', 'P', 'g-warm', 'learn-node.html?slug=prompt', 50, 1),
('rag-course', 'rag', 'RAG 与知识库搭建', '检索增强生成与端到端项目实战', 'RAG', 'R', 'g-yellow', 'learn-node.html?slug=rag', 60, 1);

INSERT INTO tool_categories(code, name, icon, logo_class, description, sort_order) VALUES
('chat', 'AI 对话聊天', '💬', 'logo-chat', '通用聊天、角色扮演、搜索增强和学习助手。', 10),
('text', 'AI 文本工具', '✍', 'logo-text', '写作、公文、论文、翻译和营销文案工具。', 20),
('image', 'AI 绘画工具', '🎨', 'logo-image', '文生图、修图、设计素材和商品图工具。', 30),
('video', 'AI 视频工具', '🎬', 'logo-video', '文生视频、数字人、剪辑、音乐和配音工具。', 40),
('code', 'AI 编程工具', '⌘', 'logo-code', 'AI IDE、代码助手、测试、部署与低代码平台。', 50),
('office', 'AI 办公工具', '▣', 'logo-office', '文档、会议、知识库、流程自动化和团队协作。', 60),
('data', 'AI 搜索与数据', '◎', 'logo-data', '联网搜索、研究、数据分析、商业洞察和知识检索。', 70),
('audio', 'AI 音频工具', '♫', 'logo-video', '语音合成、转写、音乐生成和播客制作。', 80),
('automation', 'AI 自动化', '⚙', 'logo-code', '工作流自动化、智能代理和跨应用连接。', 90);

INSERT INTO tool_subcategories(category_code, name, sort_order) VALUES
('chat', '通用对话', 10), ('chat', '国产大模型', 20), ('chat', '角色陪伴', 30), ('chat', '学习助手', 40),
('text', 'AI写作', 10), ('text', '公文论文', 20), ('text', '翻译润色', 30), ('text', '营销文案', 40),
('image', '文生图', 10), ('image', '设计修图', 20), ('image', '商品素材', 30), ('image', '开源模型', 40),
('video', '文生视频', 10), ('video', '剪辑包装', 20), ('video', '音频音乐', 30), ('video', '数字人', 40),
('code', 'AI IDE', 10), ('code', '代码补全', 20), ('code', '低代码平台', 30), ('code', '测试运维', 40),
('office', '文档知识', 10), ('office', '会议纪要', 20), ('office', 'PPT表格', 30), ('office', '自动化', 40),
('data', 'AI搜索', 10), ('data', '研究分析', 20), ('data', '数据图表', 30), ('data', '知识库', 40),
('audio', '语音合成', 10), ('audio', '转写字幕', 20), ('audio', '音乐生成', 30), ('audio', '播客制作', 40),
('automation', '流程自动化', 10), ('automation', '智能代理', 20), ('automation', '应用连接', 30), ('automation', '企业集成', 40);

INSERT INTO ai_tools(slug, category_code, subcategory_name, name, description, mark, tag, official_url, is_free, is_latest, sort_order) VALUES
('chatgpt', 'chat', '通用对话', 'ChatGPT', '通用对话、写作、代码与多模态助手。', 'GPT', '旗舰', 'https://chatgpt.com/', 0, 1, 10),
('claude', 'chat', '通用对话', 'Claude', '长文本阅读、写作和复杂推理体验优秀。', 'CL', '长文', 'https://claude.ai/', 0, 1, 20),
('deepseek', 'chat', '国产大模型', 'DeepSeek', '国产开源模型生态，中文与代码任务友好。', 'DS', '国产', 'https://www.deepseek.com/', 1, 1, 30),
('kimi', 'chat', '学习助手', 'Kimi', '长文档阅读、资料整理和学习问答。', 'KM', '中文', 'https://kimi.moonshot.cn/', 1, 0, 40),
('doubao', 'chat', '国产大模型', '豆包', '字节跳动 AI 助手，中文对话、写作和图像生成体验完整。', '豆', '国产', 'https://www.doubao.com/', 1, 1, 50),
('jasper', 'text', '营销文案', 'Jasper', '营销内容、品牌语气和多渠道文案工具。', 'JS', '营销', 'https://www.jasper.ai/', 0, 0, 10),
('grammarly', 'text', '翻译润色', 'Grammarly', '英文写作润色、语法检查和语气调整。', 'GR', '润色', 'https://www.grammarly.com/', 1, 0, 20),
('copy-ai', 'text', '营销文案', 'Copy.ai', '营销文案、销售邮件和增长内容生成。', 'CY', '营销', 'https://www.copy.ai/', 0, 0, 30),
('midjourney', 'image', '文生图', 'Midjourney', '高质量图像生成，适合概念视觉和风格探索。', 'MJ', '高质', 'https://www.midjourney.com/', 0, 1, 10),
('canva', 'image', '设计修图', 'Canva AI', '模板设计、素材生成和社媒图片制作。', 'CA', '设计', 'https://www.canva.com/', 1, 0, 20),
('adobe-firefly', 'image', '设计修图', 'Adobe Firefly', 'Adobe 创意生态中的商业友好生成式设计工具。', 'AF', '设计', 'https://firefly.adobe.com/', 1, 1, 30),
('runway', 'video', '文生视频', 'Runway', '视频生成、图生视频和创意短片工具。', 'RW', '视频', 'https://runwayml.com/', 0, 1, 10),
('capcut', 'video', '剪辑包装', 'CapCut', '短视频剪辑、字幕和模板包装。', 'CC', '剪辑', 'https://www.capcut.com/', 1, 0, 20),
('sora', 'video', '文生视频', 'Sora', 'OpenAI 视频生成工具，适合高质量叙事视频生成。', 'SO', '视频', 'https://sora.com/', 0, 1, 30),
('cursor', 'code', 'AI IDE', 'Cursor', 'AI 原生代码编辑器，适合项目级开发。', 'CR', 'IDE', 'https://cursor.com/', 0, 1, 10),
('copilot', 'code', '代码补全', 'GitHub Copilot', '代码补全、解释和 Pull Request 辅助。', 'CP', '开发', 'https://github.com/features/copilot', 0, 0, 20),
('v0', 'code', '低代码平台', 'v0', '用自然语言生成 React 页面和组件原型。', 'v0', '前端', 'https://v0.dev/', 1, 1, 30),
('notebooklm', 'office', '文档知识', 'NotebookLM', '基于资料库的阅读、摘要和播客化学习。', 'LM', '资料', 'https://notebooklm.google/', 1, 1, 10),
('gamma', 'office', 'PPT表格', 'Gamma', 'AI 演示文稿和网页式文档生成。', 'GA', 'PPT', 'https://gamma.app/', 1, 0, 20),
('perplexity', 'data', 'AI搜索', 'Perplexity', '联网搜索、来源引用和研究问答。', 'PX', '搜索', 'https://www.perplexity.ai/', 1, 1, 10),
('tableau', 'data', '数据图表', 'Tableau AI', '数据可视化、商业洞察和增强分析能力。', 'TB', 'BI', 'https://www.tableau.com/products/tableau-ai', 0, 0, 20),
('suno', 'audio', '音乐生成', 'Suno', '根据提示词生成歌曲、旋律和歌词。', 'SN', '音乐', 'https://suno.com/', 1, 1, 10),
('elevenlabs', 'audio', '语音合成', 'ElevenLabs', '高质量语音合成、配音和声音克隆。', 'EL', '语音', 'https://elevenlabs.io/', 1, 1, 20),
('zapier', 'automation', '流程自动化', 'Zapier', '连接数千应用的自动化平台，内置 AI 工作流能力。', 'ZP', '自动化', 'https://zapier.com/', 1, 1, 10),
('dify', 'automation', '智能代理', 'Dify', '开源 LLM 应用开发平台，支持工作流和 Agent。', 'DF', '开源', 'https://dify.ai/', 1, 1, 20);

INSERT INTO tool_workflows(code, title, description, badge, sort_order) VALUES
('creative-video', '创意短视频链路', '从脚本、分镜到视频生成与剪辑包装。', '创作', 10),
('research-writing', '研究写作链路', '资料检索、文献整理、长文写作与校对。', '学习', 20),
('dev-quality', '开发提效链路', '需求拆解、编码、代码补全、异常监控。', '工程', 30);

INSERT INTO workflow_tools(workflow_code, tool_slug, sort_order) VALUES
('creative-video', 'chatgpt', 10), ('creative-video', 'midjourney', 20), ('creative-video', 'runway', 30), ('creative-video', 'capcut', 40),
('research-writing', 'notebooklm', 10), ('research-writing', 'perplexity', 20), ('research-writing', 'claude', 30), ('research-writing', 'grammarly', 40),
('dev-quality', 'cursor', 10), ('dev-quality', 'copilot', 20), ('dev-quality', 'v0', 30);
