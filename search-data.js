// =============================================
// AI 知识导航 — 统一搜索数据源
// URL 数据引用自 urls.js，本文件负责搜索逻辑和 UI 渲染数据
// =============================================

const TOOLS = [
  // ---- 对话助手 ----
  {
    id: 'kimi',
    name: 'Kimi',
    maker: '月之暗面',
    cat: 'chat',
    catName: '对话助手',
    desc: '长上下文对话，支持上传文件，免费使用',
    tags: ['免费', '对话'],
    url: TOOL_URLS.kimi.url,
    domain: TOOL_URLS.kimi.domain,
  },
  {
    id: 'tongyi',
    name: '通义千问',
    maker: '阿里巴巴',
    cat: 'chat',
    catName: '对话助手',
    desc: '阿里出品，支持多模态，代码能力强',
    tags: ['免费', '多模态'],
    url: TOOL_URLS.tongyi.url,
    domain: TOOL_URLS.tongyi.domain,
  },
  {
    id: 'wenxin',
    name: '文心一言',
    maker: '百度',
    cat: 'chat',
    catName: '对话助手',
    desc: '百度出品，中文理解优秀，搜索增强',
    tags: ['免费', '中文'],
    url: TOOL_URLS.wenxin.url,
    domain: TOOL_URLS.wenxin.domain,
  },
  {
    id: 'doubao',
    name: '豆包',
    maker: '字节跳动',
    cat: 'chat',
    catName: '对话助手',
    desc: '字节旗下，应用场景丰富，多模态能力强',
    tags: ['免费', '多模态'],
    url: TOOL_URLS.doubao.url,
    domain: TOOL_URLS.doubao.domain,
  },
  {
    id: 'zhipu',
    name: '智谱清言',
    maker: '智谱AI',
    cat: 'chat',
    catName: '对话助手',
    desc: 'GLM系列模型，学术/代码能力突出',
    tags: ['免费', '学术'],
    url: TOOL_URLS.zhipu.url,
    domain: TOOL_URLS.zhipu.domain,
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    maker: '深度求索',
    cat: 'chat',
    catName: '对话助手',
    desc: '国产顶尖推理模型，深度思考能力出色',
    tags: ['免费', '推理'],
    url: TOOL_URLS.deepseek.url,
    domain: TOOL_URLS.deepseek.domain,
  },

  // ---- 编程开发 ----
  {
    id: 'github-copilot',
    name: 'GitHub Copilot',
    maker: 'Microsoft / GitHub',
    cat: 'code',
    catName: '编程开发',
    desc: 'IDE内AI编程助手，代码补全与生成',
    tags: ['付费', 'IDE插件'],
    url: TOOL_URLS['github-copilot'].url,
    domain: TOOL_URLS['github-copilot'].domain,
  },
  {
    id: 'codebuddy',
    name: 'CodeBuddy',
    maker: '腾讯云',
    cat: 'code',
    catName: '编程开发',
    desc: '腾讯出品AI编程助手，支持多种IDE',
    tags: ['免费', '代码'],
    url: TOOL_URLS.codebuddy.url,
    domain: TOOL_URLS.codebuddy.domain,
  },
  {
    id: 'cursor',
    name: 'Cursor',
    maker: 'Cursor Inc.',
    cat: 'code',
    catName: '编程开发',
    desc: 'AI原生代码编辑器，深度集成大模型',
    tags: ['免费版', '编辑器'],
    url: TOOL_URLS.cursor.url,
    domain: TOOL_URLS.cursor.domain,
  },

  // ---- 图像生成 ----
  {
    id: 'midjourney',
    name: 'Midjourney',
    maker: 'Midjourney Inc.',
    cat: 'image',
    catName: '图像生成',
    desc: '顶尖AI绘图，艺术风格多样，画质出色',
    tags: ['付费', '图像'],
    url: TOOL_URLS.midjourney.url,
    domain: TOOL_URLS.midjourney.domain,
  },
  {
    id: 'wanxiang',
    name: '通义万相',
    maker: '阿里巴巴',
    cat: 'image',
    catName: '图像生成',
    desc: '免费国产AI绘图，支持中文描述生图',
    tags: ['免费', '图像'],
    url: TOOL_URLS.wanxiang.url,
    domain: TOOL_URLS.wanxiang.domain,
  },
  {
    id: 'stable-diffusion',
    name: 'Stable Diffusion',
    maker: 'Stability AI',
    cat: 'image',
    catName: '图像生成',
    desc: '开源图像生成模型，本地部署或在线使用',
    tags: ['开源', '图像'],
    url: TOOL_URLS['stable-diffusion'].url,
    domain: TOOL_URLS['stable-diffusion'].domain,
  },

  // ---- 写作办公 ----
  {
    id: 'notion',
    name: 'Notion AI',
    maker: 'Notion Labs',
    cat: 'write',
    catName: '写作办公',
    desc: '笔记+AI写作助手，内嵌于Notion工作区',
    tags: ['付费', '写作'],
    url: TOOL_URLS.notion.url,
    domain: TOOL_URLS.notion.domain,
  },
  {
    id: 'xunfei',
    name: '讯飞星火',
    maker: '科大讯飞',
    cat: 'write',
    catName: '写作办公',
    desc: '语音识别+大模型，办公写作场景友好',
    tags: ['免费版', '写作'],
    url: TOOL_URLS.xunfei.url,
    domain: TOOL_URLS.xunfei.domain,
  },

  // ---- 视频音频 ----
  {
    id: 'suno',
    name: 'Suno',
    maker: 'Suno AI',
    cat: 'video',
    catName: '视频音频',
    desc: '文字生成完整音乐，质量惊艳，含人声',
    tags: ['免费版', '音乐'],
    url: TOOL_URLS.suno.url,
    domain: TOOL_URLS.suno.domain,
  },
  {
    id: 'keling',
    name: '可灵 AI',
    maker: '快手',
    cat: 'video',
    catName: '视频音频',
    desc: '国产文生视频，效果优秀，支持中文',
    tags: ['免费版', '视频'],
    url: TOOL_URLS.keling.url,
    domain: TOOL_URLS.keling.domain,
  },

  // ---- 智能搜索 ----
  {
    id: 'perplexity',
    name: 'Perplexity',
    maker: 'Perplexity AI',
    cat: 'search',
    catName: '智能搜索',
    desc: 'AI搜索引擎，带来源引用的智能问答',
    tags: ['免费版', '搜索'],
    url: TOOL_URLS.perplexity.url,
    domain: TOOL_URLS.perplexity.domain,
  },
  {
    id: 'tiangong',
    name: '天工 AI',
    maker: '昆仑万维',
    cat: 'search',
    catName: '智能搜索',
    desc: '国产AI搜索+对话，实时联网获取信息',
    tags: ['免费', '搜索'],
    url: TOOL_URLS.tiangong.url,
    domain: TOOL_URLS.tiangong.domain,
  },
];

// ---- 工具分类 ----
const TOOL_CATS = [
  { id: 'all',    name: '全部' },
  { id: 'chat',   name: '对话助手' },
  { id: 'code',   name: '编程开发' },
  { id: 'image',  name: '图像生成' },
  { id: 'write',  name: '写作办公' },
  { id: 'video',  name: '视频音频' },
  { id: 'search', name: '智能搜索' },
];

// ---- 为每个工具生成中文关键词（用于搜索匹配） ----
// 这些关键词在构建搜索结果时动态附加，不修改 TOOLS 原始数据
const TOOL_KEYWORDS_EXTRA = {
  kimi:       ['月之暗面', 'moonshot', '长文本', '长上下文', '文件上传'],
  tongyi:     ['通义', '阿里', 'alibaba', 'qwen', '千问', '多模态'],
  wenxin:     ['文心', '百度', 'baidu', 'ernie', '一言', '中文理解'],
  doubao:     ['字节', 'bytedance', '抖音', 'tiktok', '豆包ai'],
  zhipu:      ['智谱', 'glm', 'chatglm', '清华', '学术'],
  deepseek:   ['ds', '深度求索', 'deepseek-r1', 'deepseek-v3', '推理', '深度思考', 'cody'],
  'github-copilot': ['github', 'copilot', '微软', 'microsoft', 'vscode', '代码补全'],
  codebuddy:  ['腾讯', 'tencent', 'codebuddy', '代码助手'],
  cursor:     ['cursor编辑器', 'ai编辑器', '代码编辑器', 'ide'],
  midjourney: ['mj', 'ai绘画', 'ai绘图', '艺术', '生图', '图片生成'],
  wanxiang:   ['万相', '阿里', '通义万象', '文生图', '国产绘图'],
  'stable-diffusion': ['sd', 'stability', '开源绘图', '本地部署', 'ai绘画'],
  notion:     ['notion笔记', '笔记', '办公', '文档', '协作'],
  xunfei:     ['讯飞', '科大讯飞', '星火', 'iflytek', '语音', '语音识别'],
  suno:       ['suno ai', 'ai音乐', '音乐生成', '作曲', 'ai作曲'],
  keling:     ['可灵', '快手', 'kling', '视频生成', 'ai视频', '文生视频'],
  perplexity: ['plex', 'ai搜索引擎', '问答', '引用', '文献'],
  tiangong:   ['天工', '昆仑万维', 'kunlun', '联网搜索', '国产搜索'],
};

// ---- 构建搜索时使用的扩展字段（合并原始数据 + 额外关键词） ----
function getToolKeywords(tool) {
  const extra = TOOL_KEYWORDS_EXTRA[tool.id] || [];
  return [
    tool.name,
    tool.name.toLowerCase(),
    tool.maker,
    tool.catName,
    tool.desc,
    ...tool.tags,
    ...extra,
  ].filter(Boolean);
}

// ---- 学习路径条目（可搜索）---- 数据源来自 urls.js
const LEARN_ENTRIES = getSearchLearnEntries();

// ---- 模型条目（可搜索）---- 数据源来自 urls.js
const MODEL_ENTRIES = getSearchModelEntries();

// ---- 快捷搜索条目（常用问题直接给答案） ----
const QUICK_ENTRIES = [
  {
    trigger: ['免费ai', '免费的ai', '哪些ai免费', 'ai免费工具'],
    response: '推荐免费AI工具：Kimi、通义千问、文心一言、豆包、智谱清言、DeepSeek、CodeBuddy 均免费使用！点击下方卡片可直接访问。',
    highlightIds: ['kimi', 'tongyi', 'wenxin', 'doubao', 'zhipu', 'deepseek', 'codebuddy'],
  },
  {
    trigger: ['ai绘画', 'ai绘图', '图片生成', '文生图', 'ai画图'],
    response: '推荐AI绘画工具：Midjourney（付费，效果最好）、通义万相（免费国产）、Stable Diffusion（开源免费）。',
    highlightIds: ['midjourney', 'wanxiang', 'stable-diffusion'],
  },
  {
    trigger: ['编程', '写代码', 'ai编程', '编程助手', '代码助手'],
    response: '推荐AI编程工具：GitHub Copilot、CodeBuddy（腾讯免费）、Cursor（AI原生编辑器）、DeepSeek（推理强，适合写代码）。',
    highlightIds: ['github-copilot', 'codebuddy', 'cursor', 'deepseek'],
  },
  {
    trigger: ['ai搜索', 'ai搜索引擎', '联网搜索'],
    response: '推荐AI搜索工具：Perplexity（国际顶尖AI搜索引擎）、天工AI（国产免费联网搜索）。',
    highlightIds: ['perplexity', 'tiangong'],
  },
  {
    trigger: ['视频', 'ai视频', '视频生成', '文生视频'],
    response: '推荐视频/音频工具：可灵AI（快手出品，文生视频）、Suno（AI音乐生成）。',
    highlightIds: ['keling', 'suno'],
  },
  {
    trigger: ['大模型', 'llm', '模型对比', '哪个模型好', '哪个模型强'],
    response: '当前顶级大模型：DeepSeek-R1（推理最强）、Claude 3.7（综合均衡）、GPT-4o（生态最广）。详情见「模型对比」区域。',
    scrollTo: 'section-compare',
  },
];

// ---- 搜索节名称映射 ----
const SECTION_LABELS = {
  'learn-basic': '学习区 · 基础篇',
  'learn-advanced': '学习区 · 进阶篇',
  'section-compare': '模型对比',
  'section-tools': 'AI工具导航',
};

// =============================================
// 搜索函数
// =============================================

/**
 * 计算相关性得分
 * 规则：完全匹配 > 前缀匹配 > 包含匹配 > 关键词中包含
 */
function calcRelevance(item, query, searchableText) {
  let score = 0;
  const q = query.toLowerCase();
  const name = item.name.toLowerCase();

  if (name === q) score += 100;
  else if (name.startsWith(q)) score += 60;
  else if (name.includes(q)) score += 40;

  for (const text of searchableText) {
    const t = text.toLowerCase();
    if (t === q) score += 50;
    else if (t.startsWith(q)) score += 30;
    else if (t.includes(q)) score += 15;
  }

  return score;
}

/**
 * 全局搜索入口
 * @param {string} query 用户输入的搜索词
 * @returns {Array} 排序后的搜索结果
 */
function searchAll(query) {
  if (!query || query.trim().length < 1) return [];
  const q = query.trim();

  // 1. 先检查快捷匹配
  for (const entry of QUICK_ENTRIES) {
    for (const t of entry.trigger) {
      if (t === q.toLowerCase()) {
        return [{ type: 'quick', data: entry, score: 999 }];
      }
    }
  }
  // 模糊匹配快捷条目
  for (const entry of QUICK_ENTRIES) {
    for (const t of entry.trigger) {
      if (t.includes(q.toLowerCase()) || q.toLowerCase().includes(t)) {
        return [{ type: 'quick', data: entry, score: 900 }];
      }
    }
  }

  const results = [];

  // 2. 搜索工具
  for (const tool of TOOLS) {
    const searchText = getToolKeywords(tool);
    const score = calcRelevance(tool, q, searchText);
    if (score > 0) {
      results.push({ type: 'tool', data: tool, score, searchText });
    }
  }

  // 3. 搜索学习路径
  for (const entry of LEARN_ENTRIES) {
    const searchText = [entry.name, entry.desc, entry.block, ...entry.keywords];
    const score = calcRelevance(entry, q, searchText);
    if (score > 0) {
      results.push({ type: 'learn', data: entry, score });
    }
  }

  // 4. 搜索模型
  for (const entry of MODEL_ENTRIES) {
    const searchText = [entry.name, entry.maker, entry.name.toLowerCase()];
    const score = calcRelevance(entry, q, searchText);
    if (score > 0) {
      results.push({ type: 'model', data: entry, score });
    }
  }

  // 按得分降序排列
  results.sort((a, b) => b.score - a.score);

  return results;
}

/**
 * 获取 favicon URL
 * @param {string} domain 域名
 * @param {number} size 尺寸 (可选，默认不传用原生尺寸)
 */
function getFaviconUrl(domain, size) {
  var base = 'https://favicon.im/' + domain;
  // favicon.im 支持 ?larger=true 返回更高分辨率
  if (size && size >= 48) {
    return base + '?larger=true';
  }
  return base;
}

/**
 * 根据工具 id 查找工具对象
 */
function getToolById(id) {
  return TOOLS.find(t => t.id === id);
}
