# 前端入口与运行责任审计

更新时间：2026-07-15

## 1. 当前结论

非 Agent 页面已经完成第一轮运行入口收口：每个页面只有一个显式入口脚本，公共页面壳层、Learning 页面渲染、Tools 页面渲染和 Users 页面逻辑按功能域组织。旧的 `home.js/learn.js/node.js/roadmap.js/tools.js/layout.js` 双轨脚本已删除。

本轮不建设 Agent。`assistant.html` 继续使用冻结兼容入口 `v2-api.js` 与现有 `assistant-page.js`，待其他模块归档后再处理。

## 2. 生产页面入口

| 页面 | 唯一入口 | 页面责任 |
| --- | --- | --- |
| `index.html` | `home-page.js` | 首页交互、学习地图和首页工具摘要 |
| `learn.html` | `learn-page.js` | 学习地图、资源和用户学习摘要 |
| `learn-node.html` | `learn-node-page.js` | 节点详情、内容标签和学习状态 |
| `tools.html` | `tools-entry.js` | 工具目录、搜索、分类和工作流展示 |
| `settings.html` | `settings.js` | Users 设置、隐私、资产和学习历史 |
| `assistant.html` | 冻结双入口 | 暂缓，不纳入本轮前端重构 |

`tests/test_frontend_entries.mjs` 强制检查五个非 Agent 页面只有一个外部脚本入口、没有内联运行脚本，并确认旧双轨文件不存在。

## 3. 共享模块

| 模块 | 所有权 |
| --- | --- |
| `api.js` | HTTP、认证刷新和统一错误模型 |
| `page-shell.js` | 导航、认证 UI、站内搜索、导航栏和通用动效 |
| `learning-api.js` | Learning HTTP 适配器 |
| `learning-pages.js` | 首页、学习总览和节点详情的数据渲染 |
| `learning-state.js` | Users 所有的学习状态交互 |
| `tools-page.js` | Tools 目录的唯一 DOM 渲染者 |
| `users-api.js` | Users/Auth HTTP 适配器 |

页面入口只负责组合这些模块，不维护领域事实。Tools 页面和站内搜索均读取后端 Tools API；Learning 页面均读取 Learning API。

## 4. 本轮修复

- 移除首页、学习总览和节点页的内联运行脚本。
- 将通用导航、认证、搜索、滚动和 reveal/spotlight 行为集中到 `page-shell.js`。
- 将原 `v2-api.js` 的 Learning 渲染迁入 `learning-pages.js`。
- Tools 改为通过统一 `apiGet` 读取目录，不再直接调用 `fetch`。
- 统一 API 客户端增加 10 秒默认超时、调用方取消、离线/网络错误码；只有 GET 会对网络错误或 502/503/504 重试一次，写请求和上传不自动重放。
- 增加共享 loading、empty、error、offline 反馈与重试动作；Learning 和 Tools 使用同一语义与安全文本渲染。
- 动态站内链接必须同源，资料和工具外链只允许 HTTP/HTTPS；所有新窗口链接使用 `noopener noreferrer`。
- 追加导航完整性迁移，助手指向真实 `assistant.html`，移除没有内容承载的 About 空入口。
- 修复节点标签从 `style.display` 迁移到 `hidden` 时的状态冲突，并补齐 tab/tabpanel ARIA 与键盘左右切换。
- 五个非 Agent 页面加载共享可见焦点与 `prefers-reduced-motion` 基线。
- Opera Browser Connector 已补充真实 Opera 页面读取与截图；Playwright 已覆盖 360、768、1440 三档视口下的五页自动交互矩阵，无水平溢出、框架错误遮罩或未解释控制台错误。
- 节点标签通过键盘左右切换并同步焦点、`aria-selected` 和可见面板；减少动画模式下动画与过渡最长为 `0.01ms`，平滑滚动关闭。

## 5. 仍需完成

- toast/dialog 已按真实使用点复核：破坏性确认仅属于设置页，Learning/Tools 已复用共享状态反馈，当前不增加全局框架。
- 继续将大型页面内联 CSS 渐进迁移到页面样式文件；不为迁移而重做视觉。
- 其他模块归档完成前保持 Agent 页面冻结。

## 6. 验证

```powershell
.\scripts\verify-foundation.ps1

# 模块级定位命令
.\scripts\verify-frontend.ps1
.\scripts\verify-learning.ps1
.\scripts\verify-tools.ps1
.\scripts\verify-users.ps1
```

Playwright 已覆盖首页桌面、学习页移动端、RAG 节点目录切换、工具页移动端搜索和工具目录故障态；所有场景均无非预期控制台错误和水平溢出。
