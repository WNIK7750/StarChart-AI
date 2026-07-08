// =============================================
// i18n.js — 中英文切换
// =============================================

var I18N_LANG = localStorage.getItem('i18n-lang') || 'zh';

var I18N_DICT = {
  zh: {
    siteName:          'AI 知识导航',
    langLabel:         '中',
    heroBadge:        'AI · 学习 · 工具 · 一站导航',
    heroTitle:        '从零开始探索 AI 世界',
    heroDesc:          '系统学习路径 · 主流模型对比 · 精选AI工具 · 国内免费AI入口一键直达',
    searchPlaceholder:  '搜索 AI 工具、模型、学习内容...',
    heroSearchPlaceholder: '试试搜索 DeepSeek、ChatGPT、提示工程...',
    hotSearchLabel:   '热门搜索：',
    videoTitle:       'AI 宣传视频',
    videoHint:         '此处放置宣传视频（支持 YouTube / Bilibili 嵌入）',
    videoSubHint:     '向上滚动滚轮即可打开视频；向下滚动离开后切换为小窗播放',
    learnTag:         '学习区',
    learnTitle:        '从零开始学 AI',
    learnDesc:         '分基础与进阶两条路径，每个课题配有精选学习资源链接',
    basicBadge:       '基础篇',
    basicTitle:        'AI 入门基础',
    advancedBadge:    '进阶篇',
    advancedTitle:     '大模型与前沿技术',
    t01title:         '什么是人工智能',
    t01desc:           'AI的定义、发展历史、核心概念与应用领域概览',
    t02title:         '机器学习基础',
    t02desc:           '监督学习、无监督学习、强化学习的基本概念与流程',
    t03title:         '深度学习入门',
    t03desc:           '神经网络原理、反向传播、激活函数、常见架构',
    t04title:         '常见模型类型',
    t04desc:           'CNN / RNN / Transformer 结构原理与适用场景',
    t05title:         '数学基础速览',
    t05desc:           '线性代数、概率论、微积分在 AI 中的核心应用',
    t06title:         'Python 与 AI 工具链',
    t06desc:           'NumPy / PyTorch / TensorFlow 快速上手',
    t07title:         '大语言模型原理',
    t07desc:           'Transformer 架构详解、自注意力机制、预训练与微调',
    t08title:         '提示工程',
    t08desc:           'Zero-shot / Few-shot / CoT / 结构化提示策略',
    t09title:         'RAG 与知识增强',
    t09desc:           '检索增强生成原理、向量数据库、知识库搭建',
    t10title:         'AI Agent 设计',
    t10desc:           'Agent 框架、规划与工具调用、多 Agent 协作',
    t11title:         'AI 应用开发实践',
    t11desc:           '调用主流 API、构建对话应用、部署与优化',
    t12title:         'AI 安全与伦理',
    t12desc:           '对齐问题、幻觉与风险、AI 治理框架概述',
    compareTag:       '模型对比',
    compareTitle:     '大模型基准测试对比',
    compareDesc:       '横向比较主流大模型在各标准测试集上的表现，数据来源于各官方技术报告（2024-2025）',
    metricLabel:       '选择维度：',
    metricOverall:     '综合评分',
    metricReasoning:   '推理能力',
    metricCoding:      '代码能力',
    metricMath:        '数学能力',
    modelLabel:        '显示模型：',
    barChartTitle:    '各基准测试得分对比（柱状图）',
    radarChartTitle:  '综合能力雷达图',
    benchmarkTitle:   '基准测试说明',
    bmMLU:            '涵盖57个学科的综合知识测试，衡量模型的广泛知识面',
    bmGPQA:           '专业级科学题目，需要博士水平知识才能解答',
    bmMATH:           '高校竞赛级数学题，测试数学推理与计算能力',
    bmHE:              '代码生成基准，通过编写Python函数解决编程问题',
    bmGSM:             '小学级数学应用题，评估基础推理与计算步骤',
    bmSWE:            '真实GitHub软件工程任务，测试代码修复能力',
    toolsTag:         '工具导航',
    toolsTitle:       'AI 工具精选导航',
    toolsDesc:         '精选各类实用 AI 工具，按使用场景分类，点击直达',
    filterAll:         '全部',
    filterChat:        '对话助手',
    filterCode:        '编程开发',
    filterImage:       '图像生成',
    filterWrite:       '写作办公',
    filterVideo:       '视频音频',
    filterSearch:       '智能搜索',
    tocTitle:          '本页目录',
    footerCopy:        'AI 知识导航 · 持续更新中',
    footerLearn:       '学习区',
    footerCompare:     '模型对比',
    footerTools:       '工具导航',
    backTop:           '↖ 回顶部',
    navLearn:          '学习区',
    navLearnBasic:     '基础篇',
    navLearnAdvanced:  '进阶篇',
    navLearnTopics:    '学习课题',
    navCompare:        '模型对比',
    navCompareOverall: '综合能力',
    navCompareDetail:  '指标详情',
    navTools:          'AI 工具',
    navToolsChat:      '对话助手',
    navToolsCode:      '编程开发',
    navToolsImage:     '图像生成',
    navToolsWrite:     '写作办公',
    navToolsVideo:     '视频音频',
    navToolsSearch:     '智能搜索',
  },

  en: {
    siteName:          'AI Knowledge Hub',
    langLabel:         'EN',
    heroBadge:         'AI · Learning · Tools · All-in-One',
    heroTitle:         'Explore the World of AI from Scratch',
    heroDesc:          'Structured learning paths · Model comparisons · Curated AI tools · Free AI access, one click away',
    searchPlaceholder:  'Search AI tools, models, learning resources...',
    heroSearchPlaceholder: 'Try: DeepSeek, ChatGPT, Prompt Engineering...',
    hotSearchLabel:    'Hot searches: ',
    videoTitle:        'AI Promo Video',
    videoHint:         'Promo video goes here (YouTube / Bilibili embed supported)',
    videoSubHint:       'Scroll wheel UP to open video; scrolls away to PiP mode',
    learnTag:         'Learning',
    learnTitle:        'Learn AI from Zero',
    learnDesc:         'Two paths: basics & advanced, each with curated learning resources',
    basicBadge:       'Basics',
    basicTitle:        'AI Fundamentals',
    advancedBadge:    'Advanced',
    advancedTitle:     'LLMs & Cutting-Edge Tech',
    t01title:         'What is Artificial Intelligence',
    t01desc:           'AI definitions, history, core concepts & application domains',
    t02title:         'Machine Learning Basics',
    t02desc:           'Supervised, unsupervised & reinforcement learning fundamentals',
    t03title:         'Deep Learning Intro',
    t03desc:           'Neural network principles, backpropagation, activations, common architectures',
    t04title:         'Common Model Types',
    t04desc:           'CNN / RNN / Transformer: structure & use cases',
    t05title:         'Math Foundations',
    t05desc:           'Linear algebra, probability & calculus in AI',
    t06title:         'Python & AI Toolchain',
    t06desc:           'NumPy / PyTorch / TensorFlow quickstart',
    t07title:         'LLM Principles',
    t07desc:           'Transformer architecture, self-attention, pretraining & fine-tuning',
    t08title:         'Prompt Engineering',
    t08desc:           'Zero-shot / Few-shot / CoT / structured prompting',
    t09title:         'RAG & Knowledge Augmentation',
    t09desc:           'Retrieval-augmented generation, vector DBs, knowledge bases',
    t10title:         'AI Agent Design',
    t10desc:           'Agent frameworks, planning & tool use, multi-agent collaboration',
    t11title:         'AI Application Development',
    t11desc:           'Call mainstream APIs, build chat apps, deploy & optimize',
    t12title:         'AI Safety & Ethics',
    t12desc:           'Alignment, hallucinations & risks, AI governance overview',
    compareTag:       'Model Compare',
    compareTitle:     'LLM Benchmark Comparison',
    compareDesc:       'Compare mainstream LLMs across standard benchmarks. Data from oficial tech reports (2024-2025)',
    metricLabel:       'Select dimension: ',
    metricOverall:     'Overall',
    metricReasoning:   'Reasoning',
    metricCoding:      'Coding',
    metricMath:        'Math',
    modelLabel:        'Show models: ',
    barChartTitle:    'Benchmark Scores Comparison (Bar Chart)',
    radarChartTitle:  'Comprehensive Radar Chart',
    benchmarkTitle:   'Benchmark Descriptions',
    bmMLU:            'Multi-task test across 57 subjects, measuring broad knowledge',
    bmGPQA:           'PhD-level science questions requiring expert knowledge',
    bmMATH:           'Competition-level math problems testing math reasoning',
    bmHE:              'Code generation benchmark via Python function writing',
    bmGSM:             'Grade-school math word problems, evaluating basic reasoning',
    bmSWE:            'Real-world GitHub software engineering tasks, code fix evaluation',
    toolsTag:         'AI Tools',
    toolsTitle:        'Curated AI Tools',
    toolsDesc:         'Practical AI tools by use case, click to visit',
    filterAll:         'Al',
    filterChat:        'Chat Assistants',
    filterCode:        'Code & Dev',
    filterImage:       'Image Generation',
    filterWrite:       'Writing & Office',
    filterVideo:       'Video & Audio',
    filterSearch:       'Smart Search',
    tocTitle:          'On This Page',
    footerCopy:        'AI Knowledge Hub · Continuously Updated',
    footerLearn:       'Learning',
    footerCompare:     'Compare',
    footerTools:       'Tools',
    backTop:           '↖ Back to Top',
    navLearn:          'Learning',
    navLearnBasic:     'Basics',
    navLearnAdvanced:  'Advanced',
    navLearnTopics:    'Topics',
    navCompare:        'Compare',
    navCompareOverall: 'Overall',
    navCompareDetail:  'Metrics',
    navTools:          'AI Tools',
    navToolsChat:      'Chat',
    navToolsCode:      'Code',
    navToolsImage:     'Image',
    navToolsWrite:     'Writing',
    navToolsVideo:     'Video',
    navToolsSearch:     'Search',
  }
};

// ---- 应用翻译 ----
function applyI18n() {
  var dict = I18N_DICT[I18N_LANG];
  if (!dict) return;

  document.querySelectorAll('[data-i18n]').forEach(function(el) {
    var key = el.dataset.i18n;
    if (dict[key] !== undefined) {
      el.textContent = dict[key];
    }
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
    var key = el.dataset.i18nPlaceholder;
    if (dict[key] !== undefined) {
      el.placeholder = dict[key];
    }
  });

  var btnLang = document.getElementById('btnLang');
  if (btnLang) {
    btnLang.querySelector('span').textContent = dict['langLabel'];
  }

  document.documentElement.lang = I18N_LANG === 'zh' ? 'zh-CN' : 'en';
}

// ---- 切换语言 ----
function toggleLang() {
  I18N_LANG = I18N_LANG === 'zh' ? 'en' : 'zh';
  localStorage.setItem('i18n-lang', I18N_LANG);
  applyI18n();
}

// ---- 暴露到 window，供 app.js 访问 ----
window.I18N     = I18N_DICT;
window.i18nLang = I18N_LANG;

// ---- 初始化 ----
document.addEventListener('DOMContentLoaded', function() {
  applyI18n();
  var btnLang = document.getElementById('btnLang');
  if (btnLang) {
    btnLang.addEventListener('click', toggleLang);
  }
});
