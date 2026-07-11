// Tool facts: one canonical record per tool; category display entries live in placements.
(function () {
  window.AINavToolData = {
  "version": 2,
  "categories": [
    {
      "id": "chat",
      "name": "AI 对话聊天",
      "icon": "💬",
      "logoClass": "logo-chat",
      "description": "通用聊天、角色扮演、搜索增强和学习助手，按热度优先展示。",
      "subcategories": [
        "全部",
        "通用对话",
        "国产大模型",
        "角色陪伴",
        "学习助手"
      ]
    },
    {
      "id": "text",
      "name": "AI 文本工具",
      "icon": "✍",
      "logoClass": "logo-text",
      "description": "写作、公文、论文、翻译和营销文案工具，适合内容生产者。",
      "subcategories": [
        "全部",
        "AI写作",
        "公文论文",
        "翻译润色",
        "营销文案"
      ]
    },
    {
      "id": "image",
      "name": "AI 绘画工具",
      "icon": "🎨",
      "logoClass": "logo-image",
      "description": "文生图、修图、设计素材和商品图工具，适合设计与内容创作。",
      "subcategories": [
        "全部",
        "文生图",
        "设计修图",
        "商品素材",
        "开源模型"
      ]
    },
    {
      "id": "video",
      "name": "AI 视频工具",
      "icon": "🎬",
      "logoClass": "logo-video",
      "description": "文生视频、数字人、剪辑、音乐和配音工具。",
      "subcategories": [
        "全部",
        "文生视频",
        "剪辑包装",
        "音频音乐",
        "数字人"
      ]
    },
    {
      "id": "code",
      "name": "AI 编程工具",
      "icon": "⌘",
      "logoClass": "logo-code",
      "description": "AI IDE、代码助手、测试、部署与低代码平台。",
      "subcategories": [
        "全部",
        "AI IDE",
        "代码补全",
        "低代码平台",
        "测试运维"
      ]
    },
    {
      "id": "office",
      "name": "AI 办公工具",
      "icon": "▣",
      "logoClass": "logo-office",
      "description": "文档、会议、知识库、流程自动化和团队协作。",
      "subcategories": [
        "全部",
        "文档知识",
        "会议纪要",
        "PPT表格",
        "自动化"
      ]
    },
    {
      "id": "data",
      "name": "AI 搜索与数据",
      "icon": "◈",
      "logoClass": "logo-data",
      "description": "联网搜索、研究、数据分析、商业洞察和知识检索工具。",
      "subcategories": [
        "全部",
        "AI搜索",
        "研究分析",
        "数据图表",
        "知识库"
      ]
    }
  ],
  "tools": [
    {
      "id": "chatgpt",
      "name": "ChatGPT",
      "aliases": [],
      "description": "OpenAI 旗舰通用 AI 助手，多模态、写作、代码和图像能力全面。",
      "mark": "CG",
      "url": "https://chatgpt.com/",
      "icon": "assets/icons/tools/chatgpt.webp",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/openai",
        "https://icons.duckduckgo.com/ip3/chatgpt.com.ico",
        "https://chatgpt.com/favicon.ico"
      ]
    },
    {
      "id": "claude",
      "name": "Claude",
      "aliases": [],
      "description": "Anthropic 出品，长文写作、代码理解和知识工作表现稳定。",
      "mark": "CL",
      "url": "https://claude.ai/",
      "icon": "assets/icons/tools/claude.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/anthropic",
        "https://icons.duckduckgo.com/ip3/claude.ai.ico",
        "https://claude.ai/favicon.ico"
      ]
    },
    {
      "id": "gemini",
      "name": "Gemini",
      "aliases": [],
      "description": "Google 多模态 AI，适合搜索、文档、代码和 Workspace 场景。",
      "mark": "GM",
      "url": "https://gemini.google.com/",
      "icon": "assets/icons/tools/gemini.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/googlegemini",
        "https://icons.duckduckgo.com/ip3/gemini.google.com.ico",
        "https://gemini.google.com/favicon.ico"
      ]
    },
    {
      "id": "deepseek",
      "name": "DeepSeek",
      "aliases": [],
      "description": "国产推理与编程强项模型，适合深度分析和代码任务。",
      "mark": "DS",
      "url": "https://chat.deepseek.com/",
      "icon": "assets/icons/tools/deepseek.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/deepseek",
        "https://icons.duckduckgo.com/ip3/chat.deepseek.com.ico",
        "https://chat.deepseek.com/favicon.ico"
      ]
    },
    {
      "id": "kimi-智能助手",
      "name": "Kimi 智能助手",
      "aliases": [],
      "description": "月之暗面长文本助手，适合资料阅读、网页搜索和文件总结。",
      "mark": "KM",
      "url": "https://www.kimi.com/",
      "icon": "assets/icons/tools/kimi-智能助手.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.kimi.com.ico",
        "https://www.kimi.com/favicon.ico"
      ]
    },
    {
      "id": "豆包",
      "name": "豆包",
      "aliases": [],
      "description": "字节跳动 AI 助手，聊天、写作、图片和视频能力整合度高。",
      "mark": "DB",
      "url": "https://www.doubao.com/",
      "icon": "assets/icons/tools/豆包.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.doubao.com.ico",
        "https://www.doubao.com/favicon.ico"
      ]
    },
    {
      "id": "通义千问",
      "name": "通义千问",
      "aliases": [],
      "description": "阿里大模型助手，中文、代码、多模态与开放模型生态完整。",
      "mark": "QW",
      "url": "https://www.tongyi.com/qianwen/",
      "icon": "assets/icons/tools/通义千问.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.tongyi.com.ico",
        "https://www.tongyi.com/favicon.ico"
      ]
    },
    {
      "id": "文心一言",
      "name": "文心一言",
      "aliases": [],
      "description": "百度大模型服务，中文知识、搜索增强和办公场景友好。",
      "mark": "WX",
      "url": "https://yiyan.baidu.com/",
      "icon": "assets/icons/tools/文心一言.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/yiyan.baidu.com.ico",
        "https://yiyan.baidu.com/favicon.ico"
      ]
    },
    {
      "id": "智谱清言-chatglm",
      "name": "智谱清言 ChatGLM",
      "aliases": [],
      "description": "智谱 AI 对话平台，GLM 模型、智能体和多模态能力丰富。",
      "mark": "ZP",
      "url": "https://chatglm.cn/",
      "icon": "assets/icons/tools/智谱清言-chatglm.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/chatglm.cn.ico",
        "https://chatglm.cn/favicon.ico"
      ]
    },
    {
      "id": "腾讯元宝",
      "name": "腾讯元宝",
      "aliases": [],
      "description": "腾讯混元大模型助手，微信生态资料处理和内容生成便利。",
      "mark": "YB",
      "url": "https://yuanbao.tencent.com/",
      "icon": "assets/icons/tools/腾讯元宝.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/yuanbao.tencent.com.ico",
        "https://yuanbao.tencent.com/favicon.ico"
      ]
    },
    {
      "id": "grok",
      "name": "Grok",
      "aliases": [],
      "description": "xAI 实时信息与推理助手，擅长逻辑、代码和热点信息总结。",
      "mark": "GK",
      "url": "https://grok.com/",
      "icon": "assets/icons/tools/grok.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/x",
        "https://icons.duckduckgo.com/ip3/grok.com.ico",
        "https://grok.com/favicon.ico"
      ]
    },
    {
      "id": "poe-ai",
      "name": "Poe AI",
      "aliases": [],
      "description": "Quora 的多模型聚合平台，可快速切换不同 AI 模型。",
      "mark": "PO",
      "url": "https://poe.com/",
      "icon": "assets/icons/tools/poe-ai.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/quora",
        "https://icons.duckduckgo.com/ip3/poe.com.ico",
        "https://poe.com/favicon.ico"
      ]
    },
    {
      "id": "character-ai",
      "name": "Character.AI",
      "aliases": [],
      "description": "角色对话社区，适合虚拟角色、陪伴和剧情互动。",
      "mark": "CA",
      "url": "https://character.ai/",
      "icon": "assets/icons/tools/character-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/character.ai.ico",
        "https://character.ai/favicon.ico"
      ]
    },
    {
      "id": "minimax-星野",
      "name": "MiniMax 星野",
      "aliases": [],
      "description": "MiniMax 角色互动产品，适合陪伴、剧情和多模态聊天。",
      "mark": "MX",
      "url": "https://www.xingyeai.com/",
      "icon": "assets/icons/tools/minimax-星野.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.xingyeai.com.ico",
        "https://www.xingyeai.com/favicon.ico"
      ]
    },
    {
      "id": "pi",
      "name": "Pi",
      "aliases": [],
      "description": "Inflection 的温和陪伴式 AI，适合日常沟通和情绪支持。",
      "mark": "PI",
      "url": "https://pi.ai/",
      "icon": "assets/icons/tools/pi.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/pi.ai.ico",
        "https://pi.ai/favicon.ico"
      ]
    },
    {
      "id": "youchat",
      "name": "YouChat",
      "aliases": [],
      "description": "You.com 的 AI 对话搜索助手，面向问答和网页资料整合。",
      "mark": "YC",
      "url": "https://you.com/",
      "icon": "assets/icons/tools/youchat.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/you.com.ico",
        "https://you.com/favicon.ico"
      ]
    },
    {
      "id": "huggingchat",
      "name": "HuggingChat",
      "aliases": [],
      "description": "Hugging Face 推出的开源模型聊天入口，适合模型体验。",
      "mark": "HF",
      "url": "https://huggingface.co/chat/",
      "icon": "assets/icons/tools/huggingchat.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/huggingface",
        "https://icons.duckduckgo.com/ip3/huggingface.co.ico",
        "https://huggingface.co/favicon.ico"
      ]
    },
    {
      "id": "chatpdf",
      "name": "ChatPDF",
      "aliases": [],
      "description": "PDF 文档问答工具，适合论文、合同和报告快速阅读。",
      "mark": "CP",
      "url": "https://www.chatpdf.com/",
      "icon": "assets/icons/tools/chatpdf.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.chatpdf.com.ico",
        "https://www.chatpdf.com/favicon.ico"
      ]
    },
    {
      "id": "秘塔-ai-搜索",
      "name": "秘塔 AI 搜索",
      "aliases": [],
      "description": "搜索式 AI 问答，适合资料检索、阅读和中文内容整理。",
      "mark": "MT",
      "url": "https://metaso.cn/",
      "icon": "assets/icons/tools/秘塔-ai-搜索.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/metaso.cn.ico",
        "https://metaso.cn/favicon.ico"
      ]
    },
    {
      "id": "monica",
      "name": "Monica",
      "aliases": [],
      "description": "浏览器侧边栏 AI 助手，适合网页总结、写作和翻译。",
      "mark": "MO",
      "url": "https://monica.im/",
      "icon": "assets/icons/tools/monica.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/monica.im.ico",
        "https://monica.im/favicon.ico"
      ]
    },
    {
      "id": "天工-ai",
      "name": "天工 AI",
      "aliases": [],
      "description": "昆仑万维 AI 搜索与对话工具，适合联网问答和内容生成。",
      "mark": "TG",
      "url": "https://www.tiangong.cn/",
      "icon": "assets/icons/tools/天工-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.tiangong.cn.ico",
        "https://www.tiangong.cn/favicon.ico"
      ]
    },
    {
      "id": "百小应",
      "name": "百小应",
      "aliases": [],
      "description": "百川智能助手，面向问答、写作和效率办公。",
      "mark": "BX",
      "url": "https://ying.baichuan-ai.com/",
      "icon": "assets/icons/tools/百小应.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/ying.baichuan-ai.com.ico",
        "https://ying.baichuan-ai.com/favicon.ico"
      ]
    },
    {
      "id": "讯飞绘文",
      "name": "讯飞绘文",
      "aliases": [],
      "description": "科大讯飞内容创作平台，覆盖文章、方案、脚本和营销文案。",
      "mark": "XF",
      "url": "https://turbodesk.xfyun.cn/",
      "icon": "assets/icons/tools/讯飞绘文.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/turbodesk.xfyun.cn.ico",
        "https://turbodesk.xfyun.cn/favicon.ico"
      ]
    },
    {
      "id": "蛙蛙写作",
      "name": "蛙蛙写作",
      "aliases": [],
      "description": "AI 小说与长文写作助手，支持润色、改写和扩写。",
      "mark": "WW",
      "url": "https://www.wawawriter.com/",
      "icon": "assets/icons/tools/蛙蛙写作.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.wawawriter.com.ico",
        "https://www.wawawriter.com/favicon.ico"
      ]
    },
    {
      "id": "notion-ai",
      "name": "Notion AI",
      "aliases": [],
      "description": "嵌入 Notion 工作区的写作、总结和知识管理助手。",
      "mark": "NA",
      "url": "https://www.notion.so/product/ai",
      "icon": "assets/icons/tools/notion-ai.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/notion",
        "https://icons.duckduckgo.com/ip3/www.notion.so.ico",
        "https://www.notion.so/favicon.ico"
      ]
    },
    {
      "id": "grammarly",
      "name": "Grammarly",
      "aliases": [],
      "description": "英文写作校对与重写工具，适合邮件、论文和商务文案。",
      "mark": "GR",
      "url": "https://www.grammarly.com/",
      "icon": "assets/icons/tools/grammarly.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/grammarly",
        "https://icons.duckduckgo.com/ip3/www.grammarly.com.ico",
        "https://www.grammarly.com/favicon.ico"
      ]
    },
    {
      "id": "deepl-write",
      "name": "DeepL Write",
      "aliases": [],
      "description": "英文润色和翻译辅助工具，适合跨语言写作。",
      "mark": "DL",
      "url": "https://www.deepl.com/write",
      "icon": "assets/icons/tools/deepl-write.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/deepl",
        "https://icons.duckduckgo.com/ip3/www.deepl.com.ico",
        "https://www.deepl.com/favicon.ico"
      ]
    },
    {
      "id": "秘塔写作猫",
      "name": "秘塔写作猫",
      "aliases": [],
      "description": "中文纠错、改写和长文写作工具，适合学生和编辑。",
      "mark": "MW",
      "url": "https://xiezuocat.com/",
      "icon": "assets/icons/tools/秘塔写作猫.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/xiezuocat.com.ico",
        "https://xiezuocat.com/favicon.ico"
      ]
    },
    {
      "id": "笔灵-ai-写作",
      "name": "笔灵 AI 写作",
      "aliases": [],
      "description": "多场景文案写作平台，覆盖公文、论文和短视频脚本。",
      "mark": "BL",
      "url": "https://ibiling.cn/",
      "icon": "assets/icons/tools/笔灵-ai-写作.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/ibiling.cn.ico",
        "https://ibiling.cn/favicon.ico"
      ]
    },
    {
      "id": "小鱼-ai-写作",
      "name": "小鱼 AI 写作",
      "aliases": [],
      "description": "在线智能写作平台，适合自媒体、简历和办公文档。",
      "mark": "XY",
      "url": "https://www.xiaoyuxiezuo.com/",
      "icon": "assets/icons/tools/小鱼-ai-写作.webp",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.xiaoyuxiezuo.com.ico",
        "https://www.xiaoyuxiezuo.com/favicon.ico"
      ]
    },
    {
      "id": "橙篇",
      "name": "橙篇",
      "aliases": [],
      "description": "百度文库知识检索与长文写作工具，适合资料型写作。",
      "mark": "CP",
      "url": "https://cp.baidu.com/",
      "icon": "assets/icons/tools/橙篇.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/cp.baidu.com.ico",
        "https://cp.baidu.com/favicon.ico"
      ]
    },
    {
      "id": "句子控-ai",
      "name": "句子控 AI",
      "aliases": [],
      "description": "面向灵感收集、句子改写和内容润色的小工具。",
      "mark": "JZ",
      "url": "https://www.juzikong.com/",
      "icon": "assets/icons/tools/句子控-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.juzikong.com.ico",
        "https://www.juzikong.com/favicon.ico"
      ]
    },
    {
      "id": "copy-ai",
      "name": "Copy.ai",
      "aliases": [],
      "description": "营销文案与销售邮件生成工具，适合增长团队。",
      "mark": "CY",
      "url": "https://www.copy.ai/",
      "icon": "assets/icons/tools/copy-ai.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/copydotcom",
        "https://icons.duckduckgo.com/ip3/www.copy.ai.ico",
        "https://www.copy.ai/favicon.ico"
      ]
    },
    {
      "id": "jasper",
      "name": "Jasper",
      "aliases": [],
      "description": "品牌营销内容平台，适合团队化内容生产。",
      "mark": "JP",
      "url": "https://www.jasper.ai/",
      "icon": "assets/icons/tools/jasper.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/jasper",
        "https://icons.duckduckgo.com/ip3/www.jasper.ai.ico",
        "https://www.jasper.ai/favicon.ico"
      ]
    },
    {
      "id": "writesonic",
      "name": "Writesonic",
      "aliases": [],
      "description": "营销文章、广告文案和 SEO 内容生成平台。",
      "mark": "WS",
      "url": "https://writesonic.com/",
      "icon": "assets/icons/tools/writesonic.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/writesonic",
        "https://icons.duckduckgo.com/ip3/writesonic.com.ico",
        "https://writesonic.com/favicon.ico"
      ]
    },
    {
      "id": "quillbot",
      "name": "QuillBot",
      "aliases": [],
      "description": "改写、摘要和语法检查工具，适合英文学习与论文。",
      "mark": "QB",
      "url": "https://quillbot.com/",
      "icon": "assets/icons/tools/quillbot.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/quillbot",
        "https://icons.duckduckgo.com/ip3/quillbot.com.ico",
        "https://quillbot.com/favicon.ico"
      ]
    },
    {
      "id": "火山写作",
      "name": "火山写作",
      "aliases": [],
      "description": "字节系中文写作与纠错工具，适合日常办公表达。",
      "mark": "HS",
      "url": "https://www.writingo.net/",
      "icon": "assets/icons/tools/火山写作.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.writingo.net.ico",
        "https://www.writingo.net/favicon.ico"
      ]
    },
    {
      "id": "九歌诗歌",
      "name": "九歌诗歌",
      "aliases": [],
      "description": "清华九歌诗歌生成系统，适合中文诗词创作体验。",
      "mark": "JG",
      "url": "https://jiuge.thunlp.org/",
      "icon": "assets/icons/tools/九歌诗歌.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/jiuge.thunlp.org.ico",
        "https://jiuge.thunlp.org/favicon.ico"
      ]
    },
    {
      "id": "万彩-ai",
      "name": "万彩 AI",
      "aliases": [],
      "description": "短文案、脚本和视频创作辅助工具，适合内容运营。",
      "mark": "WC",
      "url": "https://www.animiz.cn/ai/",
      "icon": "assets/icons/tools/万彩-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.animiz.cn.ico",
        "https://www.animiz.cn/favicon.ico"
      ]
    },
    {
      "id": "搭画快写",
      "name": "搭画快写",
      "aliases": [],
      "description": "AI 文案与新媒体写作工具，适合公众号和营销文章。",
      "mark": "DH",
      "url": "https://www.dahuaba.com/",
      "icon": "assets/icons/tools/搭画快写.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.dahuaba.com.ico",
        "https://www.dahuaba.com/favicon.ico"
      ]
    },
    {
      "id": "悟智写作",
      "name": "悟智写作",
      "aliases": [],
      "description": "中文写作平台，覆盖作文、报告和办公材料。",
      "mark": "WZ",
      "url": "https://www.wuz.com.cn/",
      "icon": "assets/icons/tools/悟智写作.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.wuz.com.cn.ico",
        "https://www.wuz.com.cn/favicon.ico"
      ]
    },
    {
      "id": "笔墨公文",
      "name": "笔墨公文",
      "aliases": [],
      "description": "面向公文写作的 AIGC 创作平台。",
      "mark": "BM",
      "url": "https://www.bimogongwen.com/",
      "icon": "assets/icons/tools/笔墨公文.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.bimogongwen.com.ico",
        "https://www.bimogongwen.com/favicon.ico"
      ]
    },
    {
      "id": "rytr",
      "name": "Rytr",
      "aliases": [],
      "description": "轻量级英文文案生成工具，适合快速起草。",
      "mark": "RY",
      "url": "https://rytr.me/",
      "icon": "assets/icons/tools/rytr.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/rytr.me.ico",
        "https://rytr.me/favicon.ico"
      ]
    },
    {
      "id": "midjourney",
      "name": "Midjourney",
      "aliases": [],
      "description": "高质量艺术图像生成工具，风格化和质感表现突出。",
      "mark": "MJ",
      "url": "https://www.midjourney.com/",
      "icon": "assets/icons/tools/midjourney.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/midjourney",
        "https://icons.duckduckgo.com/ip3/www.midjourney.com.ico",
        "https://www.midjourney.com/favicon.ico"
      ]
    },
    {
      "id": "chatgpt-图像",
      "name": "ChatGPT 图像",
      "aliases": [],
      "description": "OpenAI 图像生成与编辑能力，适合和文案上下文联动。",
      "mark": "OI",
      "url": "https://chatgpt.com/",
      "icon": "assets/icons/tools/chatgpt-图像.webp",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/chatgpt.com.ico",
        "https://chatgpt.com/favicon.ico"
      ]
    },
    {
      "id": "adobe-firefly",
      "name": "Adobe Firefly",
      "aliases": [],
      "description": "Adobe 商业友好的图像生成与设计编辑工具。",
      "mark": "AF",
      "url": "https://firefly.adobe.com/",
      "icon": "assets/icons/tools/adobe-firefly.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/adobe",
        "https://icons.duckduckgo.com/ip3/firefly.adobe.com.ico",
        "https://firefly.adobe.com/favicon.ico"
      ]
    },
    {
      "id": "stable-diffusion",
      "name": "Stable Diffusion",
      "aliases": [],
      "description": "开源图像生成模型生态，可本地部署和深度定制。",
      "mark": "SD",
      "url": "https://stability.ai/",
      "icon": "assets/icons/tools/stable-diffusion.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/stability.ai.ico",
        "https://stability.ai/favicon.ico"
      ]
    },
    {
      "id": "通义万相",
      "name": "通义万相",
      "aliases": [],
      "description": "阿里 AI 绘画平台，中文提示词和国产应用场景友好。",
      "mark": "WX",
      "url": "https://tongyi.aliyun.com/wanxiang/",
      "icon": "assets/icons/tools/通义万相.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/tongyi.aliyun.com.ico",
        "https://tongyi.aliyun.com/favicon.ico"
      ]
    },
    {
      "id": "即梦-ai",
      "name": "即梦 AI",
      "aliases": [],
      "description": "字节系图像与视频生成工具，适合社媒和视觉创意。",
      "mark": "JM",
      "url": "https://jimeng.jianying.com/",
      "icon": "assets/icons/tools/即梦-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/jimeng.jianying.com.ico",
        "https://jimeng.jianying.com/favicon.ico"
      ]
    },
    {
      "id": "文心一格",
      "name": "文心一格",
      "aliases": [],
      "description": "百度 AI 艺术和设计生成工具，适合中文创意出图。",
      "mark": "YG",
      "url": "https://yige.baidu.com/",
      "icon": "assets/icons/tools/文心一格.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/yige.baidu.com.ico",
        "https://yige.baidu.com/favicon.ico"
      ]
    },
    {
      "id": "leonardo-ai",
      "name": "Leonardo AI",
      "aliases": [],
      "description": "游戏资产、概念设计和商业素材生成平台。",
      "mark": "LD",
      "url": "https://leonardo.ai/",
      "icon": "assets/icons/tools/leonardo-ai.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/leonardo.ai.ico",
        "https://leonardo.ai/favicon.ico"
      ]
    },
    {
      "id": "canva-ai",
      "name": "Canva AI",
      "aliases": [],
      "description": "在线设计工具内置 AI 生图、抠图和排版能力。",
      "mark": "CV",
      "url": "https://www.canva.com/ai/",
      "icon": "assets/icons/tools/canva-ai.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/canva",
        "https://icons.duckduckgo.com/ip3/www.canva.com.ico",
        "https://www.canva.com/favicon.ico"
      ]
    },
    {
      "id": "recraft",
      "name": "Recraft",
      "aliases": [],
      "description": "面向品牌和矢量图形的 AI 设计生成工具。",
      "mark": "RC",
      "url": "https://www.recraft.ai/",
      "icon": "assets/icons/tools/recraft.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.recraft.ai.ico",
        "https://www.recraft.ai/favicon.ico"
      ]
    },
    {
      "id": "ideogram",
      "name": "Ideogram",
      "aliases": [],
      "description": "文字渲染能力较强的图像生成工具，适合海报和标语。",
      "mark": "ID",
      "url": "https://ideogram.ai/",
      "icon": "assets/icons/tools/ideogram.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/ideogram.ai.ico",
        "https://ideogram.ai/favicon.ico"
      ]
    },
    {
      "id": "krea-ai",
      "name": "Krea AI",
      "aliases": [],
      "description": "实时生成与图像增强工具，适合设计探索。",
      "mark": "KR",
      "url": "https://www.krea.ai/",
      "icon": "assets/icons/tools/krea-ai.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.krea.ai.ico",
        "https://www.krea.ai/favicon.ico"
      ]
    },
    {
      "id": "remove-bg",
      "name": "Remove.bg",
      "aliases": [],
      "description": "自动抠图工具，适合商品图和头像处理。",
      "mark": "RB",
      "url": "https://www.remove.bg/",
      "icon": "assets/icons/tools/remove-bg.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/removebg",
        "https://icons.duckduckgo.com/ip3/www.remove.bg.ico",
        "https://www.remove.bg/favicon.ico"
      ]
    },
    {
      "id": "美图设计室",
      "name": "美图设计室",
      "aliases": [],
      "description": "国产在线设计和 AI 图片处理工具。",
      "mark": "MT",
      "url": "https://www.x-design.com/",
      "icon": "assets/icons/tools/美图设计室.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.x-design.com.ico",
        "https://www.x-design.com/favicon.ico"
      ]
    },
    {
      "id": "稿定-ai",
      "name": "稿定 AI",
      "aliases": [],
      "description": "海报、电商图和运营图设计平台，适合营销素材。",
      "mark": "GD",
      "url": "https://www.gaoding.com/ai",
      "icon": "assets/icons/tools/稿定-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.gaoding.com.ico",
        "https://www.gaoding.com/favicon.ico"
      ]
    },
    {
      "id": "photoroom",
      "name": "Photoroom",
      "aliases": [],
      "description": "商品图背景替换、抠图和批量处理工具。",
      "mark": "PR",
      "url": "https://www.photoroom.com/",
      "icon": "assets/icons/tools/photoroom.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.photoroom.com.ico",
        "https://www.photoroom.com/favicon.ico"
      ]
    },
    {
      "id": "magnific-ai",
      "name": "Magnific AI",
      "aliases": [],
      "description": "图像超分和细节增强工具，适合高质量放大。",
      "mark": "MG",
      "url": "https://magnific.ai/",
      "icon": "assets/icons/tools/magnific-ai.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/magnific.ai.ico",
        "https://magnific.ai/favicon.ico"
      ]
    },
    {
      "id": "civitai",
      "name": "Civitai",
      "aliases": [],
      "description": "Stable Diffusion 模型和 LoRA 社区。",
      "mark": "CI",
      "url": "https://civitai.com/",
      "icon": "assets/icons/tools/civitai.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/civitai",
        "https://icons.duckduckgo.com/ip3/civitai.com.ico",
        "https://civitai.com/favicon.ico"
      ]
    },
    {
      "id": "liblibai",
      "name": "LiblibAI",
      "aliases": [],
      "description": "国内 AI 模型与绘图社区，适合模型查找和出图。",
      "mark": "LL",
      "url": "https://www.liblib.art/",
      "icon": "assets/icons/tools/liblibai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.liblib.art.ico",
        "https://www.liblib.art/favicon.ico"
      ]
    },
    {
      "id": "clipdrop",
      "name": "Clipdrop",
      "aliases": [],
      "description": "图像清理、重光照、抠图和创意编辑工具集合。",
      "mark": "CD",
      "url": "https://clipdrop.co/",
      "icon": "assets/icons/tools/clipdrop.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/clipdrop.co.ico",
        "https://clipdrop.co/favicon.ico"
      ]
    },
    {
      "id": "scenario",
      "name": "Scenario",
      "aliases": [],
      "description": "游戏素材和风格一致资产生成平台。",
      "mark": "SC",
      "url": "https://www.scenario.com/",
      "icon": "assets/icons/tools/scenario.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.scenario.com.ico",
        "https://www.scenario.com/favicon.ico"
      ]
    },
    {
      "id": "sora",
      "name": "Sora",
      "aliases": [],
      "description": "OpenAI 视频生成模型，适合高质量创意视频生成。",
      "mark": "SO",
      "url": "https://sora.chatgpt.com/",
      "icon": "assets/icons/tools/sora.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/openai",
        "https://icons.duckduckgo.com/ip3/sora.chatgpt.com.ico",
        "https://sora.chatgpt.com/favicon.ico"
      ]
    },
    {
      "id": "runway",
      "name": "Runway",
      "aliases": [],
      "description": "AI 视频生成与编辑平台，覆盖 Gen 系列模型和后期工具。",
      "mark": "RW",
      "url": "https://runwayml.com/",
      "icon": "assets/icons/tools/runway.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/runway",
        "https://icons.duckduckgo.com/ip3/runwayml.com.ico",
        "https://runwayml.com/favicon.ico"
      ]
    },
    {
      "id": "可灵-ai",
      "name": "可灵 AI",
      "aliases": [],
      "description": "快手文生视频工具，中文场景和人物运动表现强。",
      "mark": "KL",
      "url": "https://app.klingai.com/",
      "icon": "assets/icons/tools/可灵-ai.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/app.klingai.com.ico",
        "https://app.klingai.com/favicon.ico"
      ]
    },
    {
      "id": "pika",
      "name": "Pika",
      "aliases": [],
      "description": "轻量视频生成与动效工具，适合社媒短片。",
      "mark": "PK",
      "url": "https://pika.art/",
      "icon": "assets/icons/tools/pika.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/pika.art.ico",
        "https://pika.art/favicon.ico"
      ]
    },
    {
      "id": "luma-dream-machine",
      "name": "Luma Dream Machine",
      "aliases": [],
      "description": "高质量视频生成和镜头运动工具。",
      "mark": "LU",
      "url": "https://lumalabs.ai/dream-machine",
      "icon": "assets/icons/tools/luma-dream-machine.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/lumalabs.ai.ico",
        "https://lumalabs.ai/favicon.ico"
      ]
    },
    {
      "id": "即梦-ai-视频",
      "name": "即梦 AI 视频",
      "aliases": [],
      "description": "字节系视频生成能力，适合创意短视频和运营素材。",
      "mark": "JV",
      "url": "https://jimeng.jianying.com/",
      "icon": "assets/icons/tools/即梦-ai-视频.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/jimeng.jianying.com.ico",
        "https://jimeng.jianying.com/favicon.ico"
      ]
    },
    {
      "id": "剪映-ai",
      "name": "剪映 AI",
      "aliases": [],
      "description": "剪辑、字幕、口播、图文成片和模板化包装。",
      "mark": "JY",
      "url": "https://www.jianying.com/",
      "icon": "assets/icons/tools/剪映-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.jianying.com.ico",
        "https://www.jianying.com/favicon.ico"
      ]
    },
    {
      "id": "capcut-ai",
      "name": "CapCut AI",
      "aliases": [],
      "description": "海外版剪映，适合短视频剪辑和社媒内容。",
      "mark": "CC",
      "url": "https://www.capcut.com/",
      "icon": "assets/icons/tools/capcut-ai.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/capcut",
        "https://icons.duckduckgo.com/ip3/www.capcut.com.ico",
        "https://www.capcut.com/favicon.ico"
      ]
    },
    {
      "id": "heygen",
      "name": "HeyGen",
      "aliases": [],
      "description": "数字人视频、口播翻译和企业培训视频工具。",
      "mark": "HG",
      "url": "https://www.heygen.com/",
      "icon": "assets/icons/tools/heygen.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.heygen.com.ico",
        "https://www.heygen.com/favicon.ico"
      ]
    },
    {
      "id": "synthesia",
      "name": "Synthesia",
      "aliases": [],
      "description": "企业数字人视频生成平台，适合培训和说明视频。",
      "mark": "SY",
      "url": "https://www.synthesia.io/",
      "icon": "assets/icons/tools/synthesia.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.synthesia.io.ico",
        "https://www.synthesia.io/favicon.ico"
      ]
    },
    {
      "id": "d-id",
      "name": "D-ID",
      "aliases": [],
      "description": "头像驱动和数字人口播工具。",
      "mark": "DI",
      "url": "https://www.d-id.com/",
      "icon": "assets/icons/tools/d-id.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.d-id.com.ico",
        "https://www.d-id.com/favicon.ico"
      ]
    },
    {
      "id": "suno",
      "name": "Suno",
      "aliases": [],
      "description": "文字生成歌曲工具，支持完整音乐和人声。",
      "mark": "SN",
      "url": "https://suno.com/",
      "icon": "assets/icons/tools/suno.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/suno",
        "https://icons.duckduckgo.com/ip3/suno.com.ico",
        "https://suno.com/favicon.ico"
      ]
    },
    {
      "id": "udio",
      "name": "Udio",
      "aliases": [],
      "description": "AI 音乐生成工具，适合歌曲、配乐和创意实验。",
      "mark": "UD",
      "url": "https://www.udio.com/",
      "icon": "assets/icons/tools/udio.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.udio.com.ico",
        "https://www.udio.com/favicon.ico"
      ]
    },
    {
      "id": "elevenlabs",
      "name": "ElevenLabs",
      "aliases": [],
      "description": "高质量 AI 配音、语音克隆和多语种朗读工具。",
      "mark": "EL",
      "url": "https://elevenlabs.io/",
      "icon": "assets/icons/tools/elevenlabs.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/elevenlabs",
        "https://icons.duckduckgo.com/ip3/elevenlabs.io.ico",
        "https://elevenlabs.io/favicon.ico"
      ]
    },
    {
      "id": "mureka",
      "name": "Mureka",
      "aliases": [],
      "description": "AI 音乐创作平台，适合中文歌曲和灵感草稿。",
      "mark": "MR",
      "url": "https://www.mureka.ai/",
      "icon": "assets/icons/tools/mureka.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.mureka.ai.ico",
        "https://www.mureka.ai/favicon.ico"
      ]
    },
    {
      "id": "descript",
      "name": "Descript",
      "aliases": [],
      "description": "音视频剪辑与转录工具，通过编辑文本剪视频。",
      "mark": "DS",
      "url": "https://www.descript.com/",
      "icon": "assets/icons/tools/descript.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.descript.com.ico",
        "https://www.descript.com/favicon.ico"
      ]
    },
    {
      "id": "veed-io",
      "name": "Veed.io",
      "aliases": [],
      "description": "在线视频编辑器，集成字幕、翻译和 AI 工具。",
      "mark": "VE",
      "url": "https://www.veed.io/",
      "icon": "assets/icons/tools/veed-io.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.veed.io.ico",
        "https://www.veed.io/favicon.ico"
      ]
    },
    {
      "id": "opusclip",
      "name": "OpusClip",
      "aliases": [],
      "description": "长视频自动切条为短视频的 AI 工具。",
      "mark": "OC",
      "url": "https://www.opus.pro/",
      "icon": "assets/icons/tools/opusclip.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.opus.pro.ico",
        "https://www.opus.pro/favicon.ico"
      ]
    },
    {
      "id": "captions",
      "name": "Captions",
      "aliases": [],
      "description": "口播视频字幕、美化和 AI 剪辑工具。",
      "mark": "CA",
      "url": "https://www.captions.ai/",
      "icon": "assets/icons/tools/captions.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.captions.ai.ico",
        "https://www.captions.ai/favicon.ico"
      ]
    },
    {
      "id": "cursor",
      "name": "Cursor",
      "aliases": [],
      "description": "AI 原生代码编辑器，适合项目级代码理解和重构。",
      "mark": "CU",
      "url": "https://cursor.com/",
      "icon": "assets/icons/tools/cursor.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/cursor",
        "https://icons.duckduckgo.com/ip3/cursor.com.ico",
        "https://cursor.com/favicon.ico"
      ]
    },
    {
      "id": "github-copilot",
      "name": "GitHub Copilot",
      "aliases": [],
      "description": "经典代码补全与 Agent 编程助手，IDE 集成成熟。",
      "mark": "GH",
      "url": "https://github.com/features/copilot",
      "icon": "assets/icons/tools/github-copilot.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/githubcopilot",
        "https://icons.duckduckgo.com/ip3/github.com.ico",
        "https://github.com/favicon.ico"
      ]
    },
    {
      "id": "claude-code",
      "name": "Claude Code",
      "aliases": [],
      "description": "Anthropic 的终端/项目级编码助手，适合大型代码库。",
      "mark": "CC",
      "url": "https://www.anthropic.com/claude-code",
      "icon": "assets/icons/tools/claude-code.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.anthropic.com.ico",
        "https://www.anthropic.com/favicon.ico"
      ]
    },
    {
      "id": "windsurf",
      "name": "Windsurf",
      "aliases": [],
      "description": "AI IDE 和 Cascade Agent 工作流，适合连续开发。",
      "mark": "WS",
      "url": "https://windsurf.com/",
      "icon": "assets/icons/tools/windsurf.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/windsurf.com.ico",
        "https://windsurf.com/favicon.ico"
      ]
    },
    {
      "id": "trae",
      "name": "Trae",
      "aliases": [],
      "description": "字节系 AI IDE，面向国内开发者的智能编程工具。",
      "mark": "TR",
      "url": "https://www.trae.ai/",
      "icon": "assets/icons/tools/trae.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.trae.ai.ico",
        "https://www.trae.ai/favicon.ico"
      ]
    },
    {
      "id": "codebuddy",
      "name": "CodeBuddy",
      "aliases": [],
      "description": "腾讯云智能编程工具，适合云开发和 IDE 辅助。",
      "mark": "CB",
      "url": "https://copilot.tencent.com/",
      "icon": "assets/icons/tools/codebuddy.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/copilot.tencent.com.ico",
        "https://copilot.tencent.com/favicon.ico"
      ]
    },
    {
      "id": "通义灵码",
      "name": "通义灵码",
      "aliases": [],
      "description": "阿里云 AI 编码助手，代码补全、问答和单测生成。",
      "mark": "LM",
      "url": "https://lingma.aliyun.com/",
      "icon": "assets/icons/tools/通义灵码.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/lingma.aliyun.com.ico",
        "https://lingma.aliyun.com/favicon.ico"
      ]
    },
    {
      "id": "amazon-q-developer",
      "name": "Amazon Q Developer",
      "aliases": [],
      "description": "AWS 开发者 AI 助手，适合云上代码和运维。",
      "mark": "AQ",
      "url": "https://aws.amazon.com/q/developer/",
      "icon": "assets/icons/tools/amazon-q-developer.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/amazonwebservices",
        "https://icons.duckduckgo.com/ip3/aws.amazon.com.ico",
        "https://aws.amazon.com/favicon.ico"
      ]
    },
    {
      "id": "replit-agent",
      "name": "Replit Agent",
      "aliases": [],
      "description": "在线开发环境里的 AI 代理，适合快速原型。",
      "mark": "RP",
      "url": "https://replit.com/ai",
      "icon": "assets/icons/tools/replit-agent.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/replit",
        "https://icons.duckduckgo.com/ip3/replit.com.ico",
        "https://replit.com/favicon.ico"
      ]
    },
    {
      "id": "bolt-new",
      "name": "Bolt.new",
      "aliases": [],
      "description": "浏览器内 AI 生成全栈应用原型。",
      "mark": "BN",
      "url": "https://bolt.new/",
      "icon": "assets/icons/tools/bolt-new.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/bolt",
        "https://icons.duckduckgo.com/ip3/bolt.new.ico",
        "https://bolt.new/favicon.ico"
      ]
    },
    {
      "id": "lovable",
      "name": "Lovable",
      "aliases": [],
      "description": "通过自然语言生成 Web App 和产品原型。",
      "mark": "LV",
      "url": "https://lovable.dev/",
      "icon": "assets/icons/tools/lovable.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/lovable.dev.ico",
        "https://lovable.dev/favicon.ico"
      ]
    },
    {
      "id": "v0",
      "name": "v0",
      "aliases": [],
      "description": "Vercel 的 UI 生成工具，适合 React 组件和界面草图。",
      "mark": "V0",
      "url": "https://v0.dev/",
      "icon": "assets/icons/tools/v0.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/vercel",
        "https://icons.duckduckgo.com/ip3/v0.dev.ico",
        "https://v0.dev/favicon.ico"
      ]
    },
    {
      "id": "tabnine",
      "name": "Tabnine",
      "aliases": [],
      "description": "企业级代码补全工具，强调隐私和团队部署。",
      "mark": "TN",
      "url": "https://www.tabnine.com/",
      "icon": "assets/icons/tools/tabnine.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/tabnine",
        "https://icons.duckduckgo.com/ip3/www.tabnine.com.ico",
        "https://www.tabnine.com/favicon.ico"
      ]
    },
    {
      "id": "codeium",
      "name": "Codeium",
      "aliases": [],
      "description": "免费代码补全和聊天助手，支持多 IDE。",
      "mark": "CI",
      "url": "https://codeium.com/",
      "icon": "assets/icons/tools/codeium.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/codeium",
        "https://icons.duckduckgo.com/ip3/codeium.com.ico",
        "https://codeium.com/favicon.ico"
      ]
    },
    {
      "id": "sourcegraph-cody",
      "name": "Sourcegraph Cody",
      "aliases": [],
      "description": "面向代码搜索和大型代码库理解的 AI 助手。",
      "mark": "CO",
      "url": "https://sourcegraph.com/cody",
      "icon": "assets/icons/tools/sourcegraph-cody.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/sourcegraph.com.ico",
        "https://sourcegraph.com/favicon.ico"
      ]
    },
    {
      "id": "devin",
      "name": "Devin",
      "aliases": [],
      "description": "AI 软件工程师代理，适合自动化开发任务。",
      "mark": "DV",
      "url": "https://devin.ai/",
      "icon": "assets/icons/tools/devin.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/devin.ai.ico",
        "https://devin.ai/favicon.ico"
      ]
    },
    {
      "id": "qodo",
      "name": "Qodo",
      "aliases": [],
      "description": "AI 代码测试、审查和质量辅助工具。",
      "mark": "QD",
      "url": "https://www.qodo.ai/",
      "icon": "assets/icons/tools/qodo.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.qodo.ai.ico",
        "https://www.qodo.ai/favicon.ico"
      ]
    },
    {
      "id": "snyk-ai",
      "name": "Snyk AI",
      "aliases": [],
      "description": "安全扫描和修复建议工具，适合代码安全。",
      "mark": "SK",
      "url": "https://snyk.io/",
      "icon": "assets/icons/tools/snyk-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/snyk.io.ico",
        "https://snyk.io/favicon.ico"
      ]
    },
    {
      "id": "sentry",
      "name": "Sentry",
      "aliases": [],
      "description": "应用监控与错误追踪平台，适合前后端异常定位、性能监控和发布质量管理。",
      "mark": "SE",
      "url": "https://sentry.io/",
      "icon": "assets/icons/tools/sentry.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/sentry",
        "https://icons.duckduckgo.com/ip3/sentry.io.ico",
        "https://sentry.io/favicon.ico"
      ]
    },
    {
      "id": "microsoft-copilot",
      "name": "Microsoft Copilot",
      "aliases": [],
      "description": "Office 与 Windows 生态 AI 助手，适合文档、表格和会议。",
      "mark": "MS",
      "url": "https://copilot.microsoft.com/",
      "icon": "assets/icons/tools/microsoft-copilot.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/microsoftcopilot",
        "https://icons.duckduckgo.com/ip3/copilot.microsoft.com.ico",
        "https://copilot.microsoft.com/favicon.ico"
      ]
    },
    {
      "id": "google-notebooklm",
      "name": "Google NotebookLM",
      "aliases": [
        "NotebookLM"
      ],
      "description": "基于资料源的笔记、问答和播客摘要工具。",
      "mark": "NL",
      "url": "https://notebooklm.google.com/",
      "icon": "assets/icons/tools/google-notebooklm.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/googlenotebooklm",
        "https://icons.duckduckgo.com/ip3/notebooklm.google.com.ico",
        "https://notebooklm.google.com/favicon.ico"
      ]
    },
    {
      "id": "飞书智能伙伴",
      "name": "飞书智能伙伴",
      "aliases": [],
      "description": "飞书文档、会议和项目协作中的 AI 助手。",
      "mark": "FS",
      "url": "https://www.feishu.cn/product/ai",
      "icon": "assets/icons/tools/飞书智能伙伴.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.feishu.cn.ico",
        "https://www.feishu.cn/favicon.ico"
      ]
    },
    {
      "id": "钉钉-ai-助理",
      "name": "钉钉 AI 助理",
      "aliases": [],
      "description": "钉钉办公场景 AI 助手，适合企业协作和流程处理。",
      "mark": "DD",
      "url": "https://www.dingtalk.com/",
      "icon": "assets/icons/tools/钉钉-ai-助理.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.dingtalk.com.ico",
        "https://www.dingtalk.com/favicon.ico"
      ]
    },
    {
      "id": "gamma",
      "name": "Gamma",
      "aliases": [],
      "description": "AI 生成演示文稿、网页和文档。",
      "mark": "GA",
      "url": "https://gamma.app/",
      "icon": "assets/icons/tools/gamma.jpg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/gamma",
        "https://icons.duckduckgo.com/ip3/gamma.app.ico",
        "https://gamma.app/favicon.ico"
      ]
    },
    {
      "id": "beautiful-ai",
      "name": "Beautiful.ai",
      "aliases": [],
      "description": "自动排版的在线演示文稿工具。",
      "mark": "BA",
      "url": "https://www.beautiful.ai/",
      "icon": "assets/icons/tools/beautiful-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.beautiful.ai.ico",
        "https://www.beautiful.ai/favicon.ico"
      ]
    },
    {
      "id": "tome",
      "name": "Tome",
      "aliases": [],
      "description": "AI 故事化演示和文档生成平台。",
      "mark": "TM",
      "url": "https://tome.app/",
      "icon": "assets/icons/tools/tome.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/tome.app.ico",
        "https://tome.app/favicon.ico"
      ]
    },
    {
      "id": "夸克-ai-ppt",
      "name": "夸克 AI PPT",
      "aliases": [],
      "description": "国产 PPT 生成与资料整理工具。",
      "mark": "QP",
      "url": "https://www.quark.cn/",
      "icon": "assets/icons/tools/夸克-ai-ppt.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.quark.cn.ico",
        "https://www.quark.cn/favicon.ico"
      ]
    },
    {
      "id": "妙办画板",
      "name": "妙办画板",
      "aliases": [],
      "description": "中文在线白板和 AI 会议协作工具。",
      "mark": "MB",
      "url": "https://imiaoban.com/",
      "icon": "assets/icons/tools/妙办画板.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/imiaoban.com.ico",
        "https://imiaoban.com/favicon.ico"
      ]
    },
    {
      "id": "fireflies-ai",
      "name": "Fireflies.ai",
      "aliases": [],
      "description": "会议录音、转写和摘要工具。",
      "mark": "FF",
      "url": "https://fireflies.ai/",
      "icon": "assets/icons/tools/fireflies-ai.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/firefliesai",
        "https://icons.duckduckgo.com/ip3/fireflies.ai.ico",
        "https://fireflies.ai/favicon.ico"
      ]
    },
    {
      "id": "otter-ai",
      "name": "Otter.ai",
      "aliases": [],
      "description": "英文会议转写和协作笔记工具。",
      "mark": "OT",
      "url": "https://otter.ai/",
      "icon": "assets/icons/tools/otter-ai.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/otterdotai",
        "https://icons.duckduckgo.com/ip3/otter.ai.ico",
        "https://otter.ai/favicon.ico"
      ]
    },
    {
      "id": "read-ai",
      "name": "Read AI",
      "aliases": [],
      "description": "会议摘要、行动项和沟通分析工具。",
      "mark": "RA",
      "url": "https://www.read.ai/",
      "icon": "assets/icons/tools/read-ai.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.read.ai.ico",
        "https://www.read.ai/favicon.ico"
      ]
    },
    {
      "id": "zapier-ai",
      "name": "Zapier AI",
      "aliases": [],
      "description": "跨应用自动化和 AI 工作流连接平台。",
      "mark": "ZA",
      "url": "https://zapier.com/ai",
      "icon": "assets/icons/tools/zapier-ai.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/zapier",
        "https://icons.duckduckgo.com/ip3/zapier.com.ico",
        "https://zapier.com/favicon.ico"
      ]
    },
    {
      "id": "make",
      "name": "Make",
      "aliases": [],
      "description": "低代码自动化平台，可连接上千个应用和 AI 能力。",
      "mark": "MK",
      "url": "https://www.make.com/",
      "icon": "assets/icons/tools/make.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/make",
        "https://icons.duckduckgo.com/ip3/www.make.com.ico",
        "https://www.make.com/favicon.ico"
      ]
    },
    {
      "id": "gumloop",
      "name": "Gumloop",
      "aliases": [],
      "description": "AI 原生自动化工作流平台，适合研究和运营流程。",
      "mark": "GL",
      "url": "https://www.gumloop.com/",
      "icon": "assets/icons/tools/gumloop.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.gumloop.com.ico",
        "https://www.gumloop.com/favicon.ico"
      ]
    },
    {
      "id": "airtable-ai",
      "name": "Airtable AI",
      "aliases": [],
      "description": "表格数据库与 AI 工作流结合的团队工具。",
      "mark": "AT",
      "url": "https://www.airtable.com/ai",
      "icon": "assets/icons/tools/airtable-ai.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/airtable",
        "https://icons.duckduckgo.com/ip3/www.airtable.com.ico",
        "https://www.airtable.com/favicon.ico"
      ]
    },
    {
      "id": "miro-ai",
      "name": "Miro AI",
      "aliases": [],
      "description": "在线白板中的头脑风暴、整理和摘要工具。",
      "mark": "MI",
      "url": "https://miro.com/ai/",
      "icon": "assets/icons/tools/miro-ai.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/miro",
        "https://icons.duckduckgo.com/ip3/miro.com.ico",
        "https://miro.com/favicon.ico"
      ]
    },
    {
      "id": "perplexity",
      "name": "Perplexity",
      "aliases": [],
      "description": "带引用来源的 AI 搜索引擎，适合研究和事实核查。",
      "mark": "PX",
      "url": "https://www.perplexity.ai/",
      "icon": "assets/icons/tools/perplexity.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/perplexity",
        "https://icons.duckduckgo.com/ip3/www.perplexity.ai.ico",
        "https://www.perplexity.ai/favicon.ico"
      ]
    },
    {
      "id": "夸克-ai-搜索",
      "name": "夸克 AI 搜索",
      "aliases": [],
      "description": "面向中文用户的搜索、总结和学习场景工具。",
      "mark": "QK",
      "url": "https://www.quark.cn/",
      "icon": "assets/icons/tools/夸克-ai-搜索.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.quark.cn.ico",
        "https://www.quark.cn/favicon.ico"
      ]
    },
    {
      "id": "google-ai-mode",
      "name": "Google AI Mode",
      "aliases": [],
      "description": "Google 搜索的 AI 回答模式，适合全球资料检索。",
      "mark": "GO",
      "url": "https://www.google.com/search/about/",
      "icon": "assets/icons/tools/google-ai-mode.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.google.com.ico",
        "https://www.google.com/favicon.ico"
      ]
    },
    {
      "id": "consensus",
      "name": "Consensus",
      "aliases": [],
      "description": "学术论文搜索和证据总结工具。",
      "mark": "CS",
      "url": "https://consensus.app/",
      "icon": "assets/icons/tools/consensus.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/consensus",
        "https://icons.duckduckgo.com/ip3/consensus.app.ico",
        "https://consensus.app/favicon.ico"
      ]
    },
    {
      "id": "elicit",
      "name": "Elicit",
      "aliases": [],
      "description": "研究问题拆解、论文查找和证据表格工具。",
      "mark": "EL",
      "url": "https://elicit.com/",
      "icon": "assets/icons/tools/elicit.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/elicit.com.ico",
        "https://elicit.com/favicon.ico"
      ]
    },
    {
      "id": "scite",
      "name": "Scite",
      "aliases": [],
      "description": "论文引用语境分析工具，适合判断研究可信度。",
      "mark": "SC",
      "url": "https://scite.ai/",
      "icon": "assets/icons/tools/scite.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/scite.ai.ico",
        "https://scite.ai/favicon.ico"
      ]
    },
    {
      "id": "chatdoc",
      "name": "ChatDOC",
      "aliases": [],
      "description": "文档问答和资料阅读工具，适合报告、合同和论文。",
      "mark": "CD",
      "url": "https://chatdoc.com/",
      "icon": "assets/icons/tools/chatdoc.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/chatdoc.com.ico",
        "https://chatdoc.com/favicon.ico"
      ]
    },
    {
      "id": "glean",
      "name": "Glean",
      "aliases": [],
      "description": "企业知识搜索和内部问答平台。",
      "mark": "GN",
      "url": "https://www.glean.com/",
      "icon": "assets/icons/tools/glean.png",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.glean.com.ico",
        "https://www.glean.com/favicon.ico"
      ]
    },
    {
      "id": "dify",
      "name": "Dify",
      "aliases": [],
      "description": "开源 LLM 应用开发平台，适合搭建知识库问答。",
      "mark": "DF",
      "url": "https://dify.ai/",
      "icon": "assets/icons/tools/dify.svg",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/dify",
        "https://icons.duckduckgo.com/ip3/dify.ai.ico",
        "https://dify.ai/favicon.ico"
      ]
    },
    {
      "id": "coze-扣子",
      "name": "Coze 扣子",
      "aliases": [],
      "description": "字节 AI Bot 和工作流平台，适合智能体与知识库。",
      "mark": "CZ",
      "url": "https://www.coze.cn/",
      "icon": "assets/icons/tools/coze-扣子.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/www.coze.cn.ico",
        "https://www.coze.cn/favicon.ico"
      ]
    },
    {
      "id": "flowith",
      "name": "Flowith",
      "aliases": [],
      "description": "知识图谱式 AI 工作空间，适合研究和创意发散。",
      "mark": "FW",
      "url": "https://flowith.io/",
      "icon": "assets/icons/tools/flowith.svg",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/flowith.io.ico",
        "https://flowith.io/favicon.ico"
      ]
    },
    {
      "id": "julius-ai",
      "name": "Julius AI",
      "aliases": [],
      "description": "面向表格和数据分析的 AI 助手。",
      "mark": "JA",
      "url": "https://julius.ai/",
      "icon": "assets/icons/tools/julius-ai.ico",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/julius.ai.ico",
        "https://julius.ai/favicon.ico"
      ]
    },
    {
      "id": "chatgpt-data-analyst",
      "name": "ChatGPT Data Analyst",
      "aliases": [],
      "description": "上传表格进行分析、可视化和 Python 计算。",
      "mark": "DA",
      "url": "https://chatgpt.com/",
      "icon": "assets/icons/tools/chatgpt-data-analyst.webp",
      "iconFallbacks": [
        "https://icons.duckduckgo.com/ip3/chatgpt.com.ico",
        "https://chatgpt.com/favicon.ico"
      ]
    },
    {
      "id": "power-bi-copilot",
      "name": "Power BI Copilot",
      "aliases": [],
      "description": "微软 BI 分析与报表生成助手。",
      "mark": "PB",
      "url": "https://powerbi.microsoft.com/",
      "icon": "assets/icons/tools/power-bi-copilot.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/powerbi",
        "https://icons.duckduckgo.com/ip3/powerbi.microsoft.com.ico",
        "https://powerbi.microsoft.com/favicon.ico"
      ]
    },
    {
      "id": "tableau-pulse",
      "name": "Tableau Pulse",
      "aliases": [],
      "description": "数据洞察和指标解释工具，面向企业分析。",
      "mark": "TB",
      "url": "https://www.tableau.com/products/tableau-pulse",
      "icon": "assets/icons/tools/tableau-pulse.ico",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/tableau",
        "https://icons.duckduckgo.com/ip3/www.tableau.com.ico",
        "https://www.tableau.com/favicon.ico"
      ]
    },
    {
      "id": "rows-ai",
      "name": "Rows AI",
      "aliases": [],
      "description": "在线表格中的 AI 数据清洗、公式和分析工具。",
      "mark": "RS",
      "url": "https://rows.com/ai",
      "icon": "assets/icons/tools/rows-ai.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/rows",
        "https://icons.duckduckgo.com/ip3/rows.com.ico",
        "https://rows.com/favicon.ico"
      ]
    },
    {
      "id": "browse-ai",
      "name": "Browse AI",
      "aliases": [],
      "description": "网页数据抓取和监控自动化工具。",
      "mark": "BA",
      "url": "https://www.browse.ai/",
      "icon": "assets/icons/tools/browse-ai.png",
      "iconFallbacks": [
        "https://cdn.simpleicons.org/browseai",
        "https://icons.duckduckgo.com/ip3/www.browse.ai.ico",
        "https://www.browse.ai/favicon.ico"
      ]
    }
  ],
  "placements": [
    {
      "toolId": "chatgpt",
      "categoryId": "chat",
      "subcategory": "通用对话",
      "heat": 99,
      "tag": "热门"
    },
    {
      "toolId": "claude",
      "categoryId": "chat",
      "subcategory": "通用对话",
      "heat": 96,
      "tag": "写作"
    },
    {
      "toolId": "gemini",
      "categoryId": "chat",
      "subcategory": "通用对话",
      "heat": 94,
      "tag": "多模态"
    },
    {
      "toolId": "deepseek",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 93,
      "tag": "推理"
    },
    {
      "toolId": "kimi-智能助手",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 91,
      "tag": "长文本"
    },
    {
      "toolId": "豆包",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 90,
      "tag": "免费"
    },
    {
      "toolId": "通义千问",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 89,
      "tag": "中文"
    },
    {
      "toolId": "文心一言",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 87,
      "tag": "中文"
    },
    {
      "toolId": "智谱清言-chatglm",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 86,
      "tag": "智能体"
    },
    {
      "toolId": "腾讯元宝",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 84,
      "tag": "生态"
    },
    {
      "toolId": "grok",
      "categoryId": "chat",
      "subcategory": "通用对话",
      "heat": 82,
      "tag": "实时"
    },
    {
      "toolId": "poe-ai",
      "categoryId": "chat",
      "subcategory": "通用对话",
      "heat": 80,
      "tag": "聚合"
    },
    {
      "toolId": "character-ai",
      "categoryId": "chat",
      "subcategory": "角色陪伴",
      "heat": 78,
      "tag": "角色"
    },
    {
      "toolId": "minimax-星野",
      "categoryId": "chat",
      "subcategory": "角色陪伴",
      "heat": 76,
      "tag": "角色"
    },
    {
      "toolId": "pi",
      "categoryId": "chat",
      "subcategory": "角色陪伴",
      "heat": 74,
      "tag": "陪伴"
    },
    {
      "toolId": "youchat",
      "categoryId": "chat",
      "subcategory": "通用对话",
      "heat": 72,
      "tag": "搜索"
    },
    {
      "toolId": "huggingchat",
      "categoryId": "chat",
      "subcategory": "学习助手",
      "heat": 70,
      "tag": "开源"
    },
    {
      "toolId": "chatpdf",
      "categoryId": "chat",
      "subcategory": "学习助手",
      "heat": 69,
      "tag": "PDF"
    },
    {
      "toolId": "秘塔-ai-搜索",
      "categoryId": "chat",
      "subcategory": "学习助手",
      "heat": 68,
      "tag": "搜索"
    },
    {
      "toolId": "monica",
      "categoryId": "chat",
      "subcategory": "学习助手",
      "heat": 66,
      "tag": "插件"
    },
    {
      "toolId": "天工-ai",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 65,
      "tag": "搜索"
    },
    {
      "toolId": "百小应",
      "categoryId": "chat",
      "subcategory": "国产大模型",
      "heat": 63,
      "tag": "办公"
    },
    {
      "toolId": "讯飞绘文",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 93,
      "tag": "写作"
    },
    {
      "toolId": "蛙蛙写作",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 88,
      "tag": "小说"
    },
    {
      "toolId": "notion-ai",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 87,
      "tag": "办公"
    },
    {
      "toolId": "grammarly",
      "categoryId": "text",
      "subcategory": "翻译润色",
      "heat": 86,
      "tag": "英文"
    },
    {
      "toolId": "deepl-write",
      "categoryId": "text",
      "subcategory": "翻译润色",
      "heat": 84,
      "tag": "翻译"
    },
    {
      "toolId": "秘塔写作猫",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 82,
      "tag": "中文"
    },
    {
      "toolId": "笔灵-ai-写作",
      "categoryId": "text",
      "subcategory": "公文论文",
      "heat": 80,
      "tag": "公文"
    },
    {
      "toolId": "小鱼-ai-写作",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 78,
      "tag": "写作"
    },
    {
      "toolId": "橙篇",
      "categoryId": "text",
      "subcategory": "公文论文",
      "heat": 77,
      "tag": "资料"
    },
    {
      "toolId": "句子控-ai",
      "categoryId": "text",
      "subcategory": "翻译润色",
      "heat": 72,
      "tag": "润色"
    },
    {
      "toolId": "copy-ai",
      "categoryId": "text",
      "subcategory": "营销文案",
      "heat": 70,
      "tag": "营销"
    },
    {
      "toolId": "jasper",
      "categoryId": "text",
      "subcategory": "营销文案",
      "heat": 69,
      "tag": "品牌"
    },
    {
      "toolId": "writesonic",
      "categoryId": "text",
      "subcategory": "营销文案",
      "heat": 68,
      "tag": "SEO"
    },
    {
      "toolId": "quillbot",
      "categoryId": "text",
      "subcategory": "翻译润色",
      "heat": 66,
      "tag": "改写"
    },
    {
      "toolId": "火山写作",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 65,
      "tag": "中文"
    },
    {
      "toolId": "九歌诗歌",
      "categoryId": "text",
      "subcategory": "AI写作",
      "heat": 60,
      "tag": "诗歌"
    },
    {
      "toolId": "万彩-ai",
      "categoryId": "text",
      "subcategory": "营销文案",
      "heat": 59,
      "tag": "运营"
    },
    {
      "toolId": "搭画快写",
      "categoryId": "text",
      "subcategory": "营销文案",
      "heat": 58,
      "tag": "新媒"
    },
    {
      "toolId": "悟智写作",
      "categoryId": "text",
      "subcategory": "公文论文",
      "heat": 57,
      "tag": "办公"
    },
    {
      "toolId": "笔墨公文",
      "categoryId": "text",
      "subcategory": "公文论文",
      "heat": 56,
      "tag": "公文"
    },
    {
      "toolId": "rytr",
      "categoryId": "text",
      "subcategory": "营销文案",
      "heat": 55,
      "tag": "英文"
    },
    {
      "toolId": "midjourney",
      "categoryId": "image",
      "subcategory": "文生图",
      "heat": 98,
      "tag": "艺术"
    },
    {
      "toolId": "chatgpt-图像",
      "categoryId": "image",
      "subcategory": "文生图",
      "heat": 95,
      "tag": "多模态"
    },
    {
      "toolId": "adobe-firefly",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 91,
      "tag": "设计"
    },
    {
      "toolId": "stable-diffusion",
      "categoryId": "image",
      "subcategory": "开源模型",
      "heat": 90,
      "tag": "开源"
    },
    {
      "toolId": "通义万相",
      "categoryId": "image",
      "subcategory": "文生图",
      "heat": 86,
      "tag": "中文"
    },
    {
      "toolId": "即梦-ai",
      "categoryId": "image",
      "subcategory": "文生图",
      "heat": 84,
      "tag": "创意"
    },
    {
      "toolId": "文心一格",
      "categoryId": "image",
      "subcategory": "文生图",
      "heat": 82,
      "tag": "中文"
    },
    {
      "toolId": "leonardo-ai",
      "categoryId": "image",
      "subcategory": "商品素材",
      "heat": 80,
      "tag": "资产"
    },
    {
      "toolId": "canva-ai",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 79,
      "tag": "设计"
    },
    {
      "toolId": "recraft",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 77,
      "tag": "矢量"
    },
    {
      "toolId": "ideogram",
      "categoryId": "image",
      "subcategory": "文生图",
      "heat": 76,
      "tag": "文字"
    },
    {
      "toolId": "krea-ai",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 74,
      "tag": "实时"
    },
    {
      "toolId": "remove-bg",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 72,
      "tag": "抠图"
    },
    {
      "toolId": "美图设计室",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 70,
      "tag": "修图"
    },
    {
      "toolId": "稿定-ai",
      "categoryId": "image",
      "subcategory": "商品素材",
      "heat": 68,
      "tag": "电商"
    },
    {
      "toolId": "photoroom",
      "categoryId": "image",
      "subcategory": "商品素材",
      "heat": 66,
      "tag": "商品"
    },
    {
      "toolId": "magnific-ai",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 64,
      "tag": "增强"
    },
    {
      "toolId": "civitai",
      "categoryId": "image",
      "subcategory": "开源模型",
      "heat": 63,
      "tag": "模型"
    },
    {
      "toolId": "liblibai",
      "categoryId": "image",
      "subcategory": "开源模型",
      "heat": 62,
      "tag": "社区"
    },
    {
      "toolId": "clipdrop",
      "categoryId": "image",
      "subcategory": "设计修图",
      "heat": 61,
      "tag": "编辑"
    },
    {
      "toolId": "scenario",
      "categoryId": "image",
      "subcategory": "商品素材",
      "heat": 58,
      "tag": "游戏"
    },
    {
      "toolId": "sora",
      "categoryId": "video",
      "subcategory": "文生视频",
      "heat": 96,
      "tag": "视频"
    },
    {
      "toolId": "runway",
      "categoryId": "video",
      "subcategory": "文生视频",
      "heat": 94,
      "tag": "视频"
    },
    {
      "toolId": "可灵-ai",
      "categoryId": "video",
      "subcategory": "文生视频",
      "heat": 91,
      "tag": "国产"
    },
    {
      "toolId": "pika",
      "categoryId": "video",
      "subcategory": "文生视频",
      "heat": 86,
      "tag": "短片"
    },
    {
      "toolId": "luma-dream-machine",
      "categoryId": "video",
      "subcategory": "文生视频",
      "heat": 84,
      "tag": "镜头"
    },
    {
      "toolId": "即梦-ai-视频",
      "categoryId": "video",
      "subcategory": "文生视频",
      "heat": 82,
      "tag": "国产"
    },
    {
      "toolId": "剪映-ai",
      "categoryId": "video",
      "subcategory": "剪辑包装",
      "heat": 80,
      "tag": "剪辑"
    },
    {
      "toolId": "capcut-ai",
      "categoryId": "video",
      "subcategory": "剪辑包装",
      "heat": 78,
      "tag": "剪辑"
    },
    {
      "toolId": "heygen",
      "categoryId": "video",
      "subcategory": "数字人",
      "heat": 76,
      "tag": "数字人"
    },
    {
      "toolId": "synthesia",
      "categoryId": "video",
      "subcategory": "数字人",
      "heat": 74,
      "tag": "企业"
    },
    {
      "toolId": "d-id",
      "categoryId": "video",
      "subcategory": "数字人",
      "heat": 72,
      "tag": "头像"
    },
    {
      "toolId": "suno",
      "categoryId": "video",
      "subcategory": "音频音乐",
      "heat": 86,
      "tag": "音乐"
    },
    {
      "toolId": "udio",
      "categoryId": "video",
      "subcategory": "音频音乐",
      "heat": 84,
      "tag": "音乐"
    },
    {
      "toolId": "elevenlabs",
      "categoryId": "video",
      "subcategory": "音频音乐",
      "heat": 83,
      "tag": "配音"
    },
    {
      "toolId": "mureka",
      "categoryId": "video",
      "subcategory": "音频音乐",
      "heat": 76,
      "tag": "音乐"
    },
    {
      "toolId": "descript",
      "categoryId": "video",
      "subcategory": "剪辑包装",
      "heat": 70,
      "tag": "转录"
    },
    {
      "toolId": "veed-io",
      "categoryId": "video",
      "subcategory": "剪辑包装",
      "heat": 68,
      "tag": "在线"
    },
    {
      "toolId": "opusclip",
      "categoryId": "video",
      "subcategory": "剪辑包装",
      "heat": 66,
      "tag": "切条"
    },
    {
      "toolId": "captions",
      "categoryId": "video",
      "subcategory": "剪辑包装",
      "heat": 64,
      "tag": "字幕"
    },
    {
      "toolId": "cursor",
      "categoryId": "code",
      "subcategory": "AI IDE",
      "heat": 96,
      "tag": "IDE"
    },
    {
      "toolId": "github-copilot",
      "categoryId": "code",
      "subcategory": "代码补全",
      "heat": 94,
      "tag": "补全"
    },
    {
      "toolId": "claude-code",
      "categoryId": "code",
      "subcategory": "AI IDE",
      "heat": 91,
      "tag": "Agent"
    },
    {
      "toolId": "windsurf",
      "categoryId": "code",
      "subcategory": "AI IDE",
      "heat": 88,
      "tag": "IDE"
    },
    {
      "toolId": "trae",
      "categoryId": "code",
      "subcategory": "AI IDE",
      "heat": 86,
      "tag": "国产"
    },
    {
      "toolId": "codebuddy",
      "categoryId": "code",
      "subcategory": "代码补全",
      "heat": 84,
      "tag": "国产"
    },
    {
      "toolId": "通义灵码",
      "categoryId": "code",
      "subcategory": "代码补全",
      "heat": 82,
      "tag": "国产"
    },
    {
      "toolId": "amazon-q-developer",
      "categoryId": "code",
      "subcategory": "测试运维",
      "heat": 80,
      "tag": "云"
    },
    {
      "toolId": "replit-agent",
      "categoryId": "code",
      "subcategory": "低代码平台",
      "heat": 78,
      "tag": "原型"
    },
    {
      "toolId": "bolt-new",
      "categoryId": "code",
      "subcategory": "低代码平台",
      "heat": 77,
      "tag": "Web"
    },
    {
      "toolId": "lovable",
      "categoryId": "code",
      "subcategory": "低代码平台",
      "heat": 76,
      "tag": "产品"
    },
    {
      "toolId": "v0",
      "categoryId": "code",
      "subcategory": "低代码平台",
      "heat": 75,
      "tag": "UI"
    },
    {
      "toolId": "tabnine",
      "categoryId": "code",
      "subcategory": "代码补全",
      "heat": 72,
      "tag": "企业"
    },
    {
      "toolId": "codeium",
      "categoryId": "code",
      "subcategory": "代码补全",
      "heat": 70,
      "tag": "免费"
    },
    {
      "toolId": "sourcegraph-cody",
      "categoryId": "code",
      "subcategory": "代码补全",
      "heat": 68,
      "tag": "搜索"
    },
    {
      "toolId": "devin",
      "categoryId": "code",
      "subcategory": "AI IDE",
      "heat": 67,
      "tag": "代理"
    },
    {
      "toolId": "qodo",
      "categoryId": "code",
      "subcategory": "测试运维",
      "heat": 64,
      "tag": "测试"
    },
    {
      "toolId": "snyk-ai",
      "categoryId": "code",
      "subcategory": "测试运维",
      "heat": 62,
      "tag": "安全"
    },
    {
      "toolId": "sentry",
      "categoryId": "code",
      "subcategory": "????",
      "heat": 61,
      "tag": "??"
    },
    {
      "toolId": "microsoft-copilot",
      "categoryId": "office",
      "subcategory": "文档知识",
      "heat": 95,
      "tag": "办公"
    },
    {
      "toolId": "google-notebooklm",
      "categoryId": "office",
      "subcategory": "文档知识",
      "heat": 92,
      "tag": "资料"
    },
    {
      "toolId": "notion-ai",
      "categoryId": "office",
      "subcategory": "文档知识",
      "heat": 88,
      "tag": "知识库"
    },
    {
      "toolId": "飞书智能伙伴",
      "categoryId": "office",
      "subcategory": "文档知识",
      "heat": 86,
      "tag": "协作"
    },
    {
      "toolId": "钉钉-ai-助理",
      "categoryId": "office",
      "subcategory": "文档知识",
      "heat": 84,
      "tag": "企业"
    },
    {
      "toolId": "gamma",
      "categoryId": "office",
      "subcategory": "PPT表格",
      "heat": 82,
      "tag": "PPT"
    },
    {
      "toolId": "beautiful-ai",
      "categoryId": "office",
      "subcategory": "PPT表格",
      "heat": 78,
      "tag": "PPT"
    },
    {
      "toolId": "tome",
      "categoryId": "office",
      "subcategory": "PPT表格",
      "heat": 76,
      "tag": "演示"
    },
    {
      "toolId": "夸克-ai-ppt",
      "categoryId": "office",
      "subcategory": "PPT表格",
      "heat": 74,
      "tag": "国产"
    },
    {
      "toolId": "妙办画板",
      "categoryId": "office",
      "subcategory": "会议纪要",
      "heat": 72,
      "tag": "会议"
    },
    {
      "toolId": "fireflies-ai",
      "categoryId": "office",
      "subcategory": "会议纪要",
      "heat": 76,
      "tag": "纪要"
    },
    {
      "toolId": "otter-ai",
      "categoryId": "office",
      "subcategory": "会议纪要",
      "heat": 73,
      "tag": "转写"
    },
    {
      "toolId": "read-ai",
      "categoryId": "office",
      "subcategory": "会议纪要",
      "heat": 70,
      "tag": "会议"
    },
    {
      "toolId": "zapier-ai",
      "categoryId": "office",
      "subcategory": "自动化",
      "heat": 80,
      "tag": "自动化"
    },
    {
      "toolId": "make",
      "categoryId": "office",
      "subcategory": "自动化",
      "heat": 78,
      "tag": "自动化"
    },
    {
      "toolId": "gumloop",
      "categoryId": "office",
      "subcategory": "自动化",
      "heat": 72,
      "tag": "流程"
    },
    {
      "toolId": "airtable-ai",
      "categoryId": "office",
      "subcategory": "PPT表格",
      "heat": 69,
      "tag": "表格"
    },
    {
      "toolId": "miro-ai",
      "categoryId": "office",
      "subcategory": "文档知识",
      "heat": 67,
      "tag": "白板"
    },
    {
      "toolId": "perplexity",
      "categoryId": "data",
      "subcategory": "AI搜索",
      "heat": 96,
      "tag": "搜索"
    },
    {
      "toolId": "秘塔-ai-搜索",
      "categoryId": "data",
      "subcategory": "AI搜索",
      "heat": 90,
      "tag": "中文"
    },
    {
      "toolId": "夸克-ai-搜索",
      "categoryId": "data",
      "subcategory": "AI搜索",
      "heat": 86,
      "tag": "中文"
    },
    {
      "toolId": "google-ai-mode",
      "categoryId": "data",
      "subcategory": "AI搜索",
      "heat": 84,
      "tag": "搜索"
    },
    {
      "toolId": "consensus",
      "categoryId": "data",
      "subcategory": "研究分析",
      "heat": 82,
      "tag": "学术"
    },
    {
      "toolId": "elicit",
      "categoryId": "data",
      "subcategory": "研究分析",
      "heat": 80,
      "tag": "研究"
    },
    {
      "toolId": "scite",
      "categoryId": "data",
      "subcategory": "研究分析",
      "heat": 76,
      "tag": "论文"
    },
    {
      "toolId": "chatdoc",
      "categoryId": "data",
      "subcategory": "知识库",
      "heat": 74,
      "tag": "文档"
    },
    {
      "toolId": "glean",
      "categoryId": "data",
      "subcategory": "知识库",
      "heat": 72,
      "tag": "企业"
    },
    {
      "toolId": "dify",
      "categoryId": "data",
      "subcategory": "知识库",
      "heat": 70,
      "tag": "开源"
    },
    {
      "toolId": "coze-扣子",
      "categoryId": "data",
      "subcategory": "知识库",
      "heat": 69,
      "tag": "Bot"
    },
    {
      "toolId": "flowith",
      "categoryId": "data",
      "subcategory": "研究分析",
      "heat": 68,
      "tag": "图谱"
    },
    {
      "toolId": "julius-ai",
      "categoryId": "data",
      "subcategory": "数据图表",
      "heat": 76,
      "tag": "数据"
    },
    {
      "toolId": "chatgpt-data-analyst",
      "categoryId": "data",
      "subcategory": "数据图表",
      "heat": 75,
      "tag": "分析"
    },
    {
      "toolId": "power-bi-copilot",
      "categoryId": "data",
      "subcategory": "数据图表",
      "heat": 72,
      "tag": "BI"
    },
    {
      "toolId": "tableau-pulse",
      "categoryId": "data",
      "subcategory": "数据图表",
      "heat": 70,
      "tag": "BI"
    },
    {
      "toolId": "rows-ai",
      "categoryId": "data",
      "subcategory": "数据图表",
      "heat": 68,
      "tag": "表格"
    },
    {
      "toolId": "browse-ai",
      "categoryId": "data",
      "subcategory": "数据图表",
      "heat": 62,
      "tag": "采集"
    }
  ]
};

  window.AINavFindTool = function findTool(name) {
    const value = String(name || '').trim();
    return window.AINavToolData.tools.find((tool) => tool.name === value || tool.aliases.includes(value) || tool.id === value) || null;
  };
})();
