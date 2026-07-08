// =============================================
// AI 知识导航 — 统一 URL 管理
// 所有跳转链接集中管理，由其他 JS 模块引用
// 最后核验更新: 2026-06-12 (22:40 安全性审计)
// =============================================

// ==================== 学习区链接 ====================

const LEARN_URLS = {
  // ---- 基础篇 ----
  'learn-01': {
    id: 'learn-01',
    name: '什么是人工智能',
    section: 'learn-basic',
    block: '基础篇',
    desc: 'AI的定义、发展历史、核心概念与应用领域概览',
    url: 'https://www.bilibili.com/video/BV1yC4y127uj/',
    keywords: ['人工智能', 'ai定义', 'ai历史', '入门', '概念', '什么是ai'],
  },
  'learn-02': {
    id: 'learn-02',
    name: '机器学习基础',
    section: 'learn-basic',
    block: '基础篇',
    desc: '监督学习、无监督学习、强化学习的基本概念与流程',
    url: 'https://www.bilibili.com/video/BV19B4y1W76i/',
    keywords: ['机器学习', '监督学习', '无监督学习', '强化学习', 'ml', '入门'],
  },
  'learn-03': {
    id: 'learn-03',
    name: '深度学习入门',
    section: 'learn-basic',
    block: '基础篇',
    desc: '神经网络原理、反向传播、激活函数、常见架构',
    url: 'https://www.bilibili.com/video/BV1if4y147hS/',
    keywords: ['深度学习', '神经网络', '反向传播', '激活函数', 'dl', '基础'],
  },
  'learn-04': {
    id: 'learn-04',
    name: '常见模型类型',
    section: 'learn-basic',
    block: '基础篇',
    desc: 'CNN / RNN / Transformer 结构原理与适用场景',
    url: 'https://www.bilibili.com/video/BV1PEUbBCELF/',
    keywords: ['cnn', 'rnn', 'transformer', '模型', '架构', '基础'],
  },
  'learn-05': {
    id: 'learn-05',
    name: '数学基础速览',
    section: 'learn-basic',
    block: '基础篇',
    desc: '线性代数、概率论、微积分在 AI 中的核心应用',
    url: 'https://www.bilibili.com/video/BV1gQ4y1E7iy/',
    keywords: ['数学', '线性代数', '概率论', '微积分', 'math', '基础'],
  },
  'learn-06': {
    id: 'learn-06',
    name: 'Python 与 AI 工具链',
    section: 'learn-basic',
    block: '基础篇',
    desc: 'NumPy / PyTorch / TensorFlow 快速上手',
    url: 'https://www.bilibili.com/video/BV1hE411t7RN/',
    keywords: ['python', 'numpy', 'pytorch', 'tensorflow', '工具', '基础'],
  },

  // ---- 进阶篇 ----
  'learn-07': {
    id: 'learn-07',
    name: '大语言模型原理',
    section: 'learn-advanced',
    block: '进阶篇',
    desc: 'Transformer 架构详解、自注意力机制、预训练与微调',
    url: 'https://www.bilibili.com/video/BV1pu411o7BE/',
    keywords: ['大语言模型', 'llm', '自注意力', '预训练', '微调', 'transformer', '进阶'],
  },
  'learn-08': {
    id: 'learn-08',
    name: '提示工程',
    section: 'learn-advanced',
    block: '进阶篇',
    desc: 'Zero-shot / Few-shot / CoT / 结构化提示策略',
    url: 'https://www.bilibili.com/video/BV1e8411o7NP/',
    keywords: ['提示工程', 'prompt', 'zero-shot', 'few-shot', 'cot', '思维链', '进阶'],
  },
  'learn-09': {
    id: 'learn-09',
    name: 'RAG 与知识增强',
    section: 'learn-advanced',
    block: '进阶篇',
    desc: '检索增强生成原理、向量数据库、知识库搭建',
    url: 'https://www.bilibili.com/video/BV1N2mqBYE8u/',
    keywords: ['rag', '检索增强', '向量数据库', '知识库', 'langchain', '进阶'],
  },
  'learn-10': {
    id: 'learn-10',
    name: 'AI Agent 设计',
    section: 'learn-advanced',
    block: '进阶篇',
    desc: 'Agent 框架、规划与工具调用、多 Agent 协作',
    url: 'https://www.bilibili.com/video/BV1DfrdByE2H/',
    keywords: ['agent', '智能体', '工具调用', '多agent', '规划', '协作', '进阶'],
  },
  'learn-11': {
    id: 'learn-11',
    name: 'AI 应用开发实践',
    section: 'learn-advanced',
    block: '进阶篇',
    desc: '调用主流 API、构建对话应用、部署与优化',
    url: 'https://www.bilibili.com/video/BV178w1z7EHQ/',
    keywords: ['api', '开发', '部署', '对话应用', 'openai api', 'langchain', '进阶'],
  },
  'learn-12': {
    id: 'learn-12',
    name: 'AI 安全与伦理',
    section: 'learn-advanced',
    block: '进阶篇',
    desc: '对齐问题、幻觉与风险、AI 治理框架概述',
    url: 'https://www.bilibili.com/video/BV1pf421z757/',
    keywords: ['安全', '伦理', '对齐', '幻觉', '风险', '治理', 'alignment', '进阶'],
  },
};

// ==================== 模型链接 ====================

const MODEL_URLS = {
  'gpt4o':       { name: 'GPT-4o',       maker: 'OpenAI',      url: 'https://openai.com',            domain: 'openai.com' },
  'claude37':    { name: 'Claude 3.7',   maker: 'Anthropic',   url: 'https://claude.ai',             domain: 'anthropic.com' },
  'gemini20pro': { name: 'Gemini 2.0 Pro', maker: 'Google',    url: 'https://gemini.google.com',     domain: 'google.com' },
  'deepseek-r1': { name: 'DeepSeek-R1',  maker: '深度求索',     url: 'https://chat.deepseek.com',     domain: 'deepseek.com' },
  'deepseek-v3': { name: 'DeepSeek-V3',  maker: '深度求索',     url: 'https://chat.deepseek.com',     domain: 'deepseek.com' },
  'qwen25max':   { name: 'Qwen2.5-Max',  maker: '阿里巴巴',     url: 'https://tongyi.aliyun.com',     domain: 'tongyi.aliyun.com' },
  'kimi15':      { name: 'Kimi k1.5',    maker: '月之暗面',     url: 'https://kimi.moonshot.cn',      domain: 'kimi.moonshot.cn' },
};

// ==================== 工具链接 ====================

const TOOL_URLS = {
  // ---- 对话助手 ----
  'kimi':       { name: 'Kimi',           maker: '月之暗面',     cat: 'chat',  url: 'https://kimi.moonshot.cn',        domain: 'kimi.moonshot.cn' },
  'tongyi':     { name: '通义千问',        maker: '阿里巴巴',     cat: 'chat',  url: 'https://tongyi.aliyun.com',        domain: 'tongyi.aliyun.com' },
  'wenxin':     { name: '文心一言',        maker: '百度',        cat: 'chat',  url: 'https://yiyan.baidu.com',           domain: 'yiyan.baidu.com' },
  'doubao':     { name: '豆包',           maker: '字节跳动',     cat: 'chat',  url: 'https://www.doubao.com',            domain: 'doubao.com' },
  'zhipu':      { name: '智谱清言',        maker: '智谱AI',      cat: 'chat',  url: 'https://chatglm.cn',               domain: 'chatglm.cn' },
  'deepseek':   { name: 'DeepSeek',       maker: '深度求索',     cat: 'chat',  url: 'https://chat.deepseek.com',        domain: 'deepseek.com' },

  // ---- 编程开发 ----
  'github-copilot': { name: 'GitHub Copilot', maker: 'Microsoft/GitHub', cat: 'code', url: 'https://github.com/features/copilot', domain: 'github.com' },
  'codebuddy':      { name: 'CodeBuddy',      maker: '腾讯云',           cat: 'code', url: 'https://copilot.tencent.com',        domain: 'copilot.tencent.com' },
  'cursor':         { name: 'Cursor',         maker: 'Cursor Inc.',      cat: 'code', url: 'https://cursor.com',                domain: 'cursor.com' },

  // ---- 图像生成 ----
  'midjourney':       { name: 'Midjourney',      maker: 'Midjourney Inc.', cat: 'image', url: 'https://www.midjourney.com',    domain: 'midjourney.com' },
  'wanxiang':         { name: '通义万相',         maker: '阿里巴巴',        cat: 'image', url: 'https://tongyi.aliyun.com/wanxiang', domain: 'tongyi.aliyun.com' },
  'stable-diffusion': { name: 'Stable Diffusion', maker: 'Stability AI',   cat: 'image', url: 'https://stability.ai',           domain: 'stability.ai' },

  // ---- 写作办公 ----
  'notion':  { name: 'Notion AI', maker: 'Notion Labs', cat: 'write', url: 'https://www.notion.so/product/ai', domain: 'notion.so' },
  'xunfei':  { name: '讯飞星火',  maker: '科大讯飞',     cat: 'write', url: 'https://xinghuo.xfyun.cn',          domain: 'xinghuo.xfyun.cn' },

  // ---- 视频音频 ----
  'suno':   { name: 'Suno',    maker: 'Suno AI', cat: 'video', url: 'https://suno.com',              domain: 'suno.com' },
  'keling': { name: '可灵 AI',  maker: '快手',     cat: 'video', url: 'https://klingai.kuaishou.com',   domain: 'kuaishou.com' },

  // ---- 智能搜索 ----
  'perplexity': { name: 'Perplexity', maker: 'Perplexity AI', cat: 'search', url: 'https://www.perplexity.ai', domain: 'perplexity.ai' },
  'tiangong':   { name: '天工 AI',    maker: '昆仑万维',       cat: 'search', url: 'https://www.tiangong.cn',      domain: 'tiangong.cn' },
};

// ==================== 视频链接 ====================

const VIDEO_URLS = {
  bilibili: {
    bvid: 'BV1axBaBuEKa',
    url: 'https://player.bilibili.com/player.html?bvid=BV1axBaBuEKa&page=1&high_quality=1&autoplay=0',
    page: 'https://www.bilibili.com/video/BV1axBaBuEKa/',
  },
};

// ==================== 快捷入口链接 ====================

const QUICK_URLS = {
  github:   'https://github.com',
  zhihu:    'https://www.zhihu.com',
  bilibili: 'https://www.bilibili.com',
  csdn:     'https://www.csdn.net',
};

// ==================== 辅助函数 ====================

/**
 * 根据 LEARN_URLS + TOOL_URLS 生成搜索数据源用的数组
 */
function getSearchLearnEntries() {
  return Object.values(LEARN_URLS).map(e => ({
    id: e.id,
    name: e.name,
    section: e.section,
    block: e.block,
    desc: e.desc,
    url: e.url,
    keywords: e.keywords,
  }));
}

function getSearchToolEntries() {
  return Object.values(TOOL_URLS).map(t => ({
    id: t.name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''),
    name: t.name,
    maker: t.maker,
    cat: t.cat,
    url: t.url,
    domain: t.domain,
  }));
}

function getSearchModelEntries() {
  return Object.entries(MODEL_URLS).map(([id, m]) => ({
    id,
    name: m.name,
    maker: m.maker,
    domain: m.domain,
    url: m.url,
  }));
}
