# README 实机截图

> 更新日期：2026-08-09
> 来源：本地实际运行的 `http://127.0.0.1:8088`，由 Playwright 驱动本机 Opera 截取。

本目录只保存可由 `scripts/capture-readme-screenshots.cjs` 重新生成的真实页面截图，不使用
设计稿、生成式图片或手工拼接界面。截图不得包含 API Key、密码、联系方式、访问令牌、
用户私有对话、真实用户名或设备信息。

当前截图：

- `home-desktop.png`：首页首屏；
- `learning-map-desktop.png`：学习总览与知识地图首屏；
- `tools-search-desktop.png`：工具页输入“代码”后的真实搜索状态；
- `assistant-preparing.jpg`：登录用户从助手输入框发送“RAG 怎么学？”后的真实准备阶段；
- `assistant-complete.jpg`：同一轮真实 Agent 请求的完整用户输入与最终回答。

助手截图使用用户自行配置的真实模型和已登录浏览器会话采集，README 直接引用原始 JPG，
不使用生成内容替代页面结果；展示时通过相同的 HTML 高度保持左右等高。公开前应再次确认
截图中没有 API Key、令牌、联系方式或其他敏感信息。

重新采集前先启动网站，然后设置本机浏览器路径：

```powershell
$env:NODE_PATH="<包含 playwright 的 node_modules>"
$env:AI_NAV_BROWSER_EXECUTABLE="<Opera 或 Chromium 可执行文件>"
node .\scripts\capture-readme-screenshots.cjs
```

每次更新截图后必须人工检查页面身份、裁切、敏感信息、控制台异常和 README 展示效果。
