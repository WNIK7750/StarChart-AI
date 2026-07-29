# HTTP 测试助手与全站性能优化复验（2026-07-29）

## 1. 结论

本批次已完成助手默认示例、流式渲染、认证初始化、公共页面启动、全站搜索、
学习页并发、滚动与悬停调度、关键资源发现、品牌图传输和 HTTP 压缩/缓存边界
的最小化整改。

- 前端实现候选：`GO`，全体 Node 前端测试 73/73 通过，正式前端门禁 58/58
  通过，全部 JavaScript 语法检查和 `git diff --check` 通过。
- 完整仓库本地候选：`GO`。本次 `verify-quality.ps1`、`verify-foundation.ps1`
  和 `verify-http-test-deployment.ps1` 均通过；质量门禁运行 259 项 Python
  测试，分支覆盖率 86.4%，Ruff 和依赖审计通过。
- 本地运行实例：`GO`。普通 8088 实例的 10 个清单路径均为 200；隔离的
  deterministic `http_test` 浏览器流程和临时 `test` 登录流程通过。
- 本次 HTTP 性能候选部署：`NOT DEPLOYED`。本轮没有执行 SSH、服务器
  `nginx -t`、systemd、线上 smoke 或发布后公网性能探针，因此目标服务器仍
  只能按上一已验证 release 看待。
- 生产发布：`NO-GO`。HTTPS、真实 Provider 获批验证、容量、监控、备份恢复、
  回滚演练、合规和外部签收仍无本次真实证据。

本记录不包含账号标识、密码、Token、Cookie、真实 `.env` 或 Provider 内容。

## 2. 基线与根因

整改前的同一公网 HTTP 路径只读探针记录如下；这些数字是网络基线，不是本次
未部署候选的发布后数字。

| 资源 | 状态 | TTFB | 总耗时 | 传输大小 |
|---|---:|---:|---:|---:|
| `/StarChart-AI/` | 200 | 78.9 ms | 144.9 ms | 72,331 B |
| `assistant.html` | 200 | 71.2 ms | 71.3 ms | 6,567 B |
| `assistant-page.js` | 200 | 69.2 ms | 106.2 ms | 40,940 B |
| `page-shell.js` | 200 | 74.5 ms | 74.6 ms | 3,183 B |
| `auth-ui.js` | 200 | 83.9 ms | 114.6 ms | 22,041 B |
| `logo.png` | 200 | 72.7 ms | 304.5 ms | 1,229,532 B |

确认的根因：

1. “RAG 和微调应该先学哪个？”既不命中学习计划意图，也没有比较型确定性规则。
2. SSE 每个 delta 都修改文本并强制滚动，重复触发布局；回答后还同步刷新两类会话。
3. 公开页面先等待导航和完整登录恢复，再开始自己的公开内容请求。
4. 搜索每次输入立即请求，旧请求不取消且可能覆盖新结果。
5. 六个页面 favicon、隐藏登录面板和设置页都引用 1,229,532 B 的 `logo.png`。
6. 学习页三块独立数据串行；滚动和卡片悬停每个事件都做布局读写。
7. HTTP 覆盖层没有压缩类型声明，且所有资源统一 `no-cache`。

## 3. 实施内容

### 3.1 助手

- 首个示例改为“RAG 怎么学？”，稳定命中 `learning_plan`，检索词归一为 `RAG`，
  只读展示站内 RAG 学习节点和学习步骤。
- SSE delta 进入帧缓冲，每动画帧最多写一次文本和滚动；完成、中止和异常路径
  都强制 flush，保证最终文本不丢失。
- 回答后不再同步等待列表；短会话只后台刷新短列表，长期会话只刷新长列表。
- 短、长期列表分别维护请求版本，迟到响应不能覆盖新状态；DOM 用
  `DocumentFragment` 一次挂载。

### 3.2 页面启动与交互

- 认证能力和会话恢复并行；事件只绑定一次，登录占位立即可用；认证刷新使用
  generation 隔离，迟到的匿名结果不能覆盖刚完成的登录或清除新令牌。
- 首页、学习页、节点页、工具页和助手页不再等待页面壳层才启动公开内容；
  设置页继续严格等待登录，未降低私有域门禁。
- 搜索使用 180 ms 去抖、`AbortController` 和查询序号，取消或拒绝旧结果；
  真正离线仍保留本地索引降级。
- 学习页 roadmap 与公开资源并行首屏加载；登录恢复完成后再补齐路线进度、
  偏好和 dashboard，公共内容不等待私有状态，已登录用户也不会被误判为游客。
- 学习节点先渲染公开内容，登录恢复后再补齐活动和偏好并局部更新资源；
  设置页不再等待四个次要账号区域全部完成才绑定当前页面交互。
- 学习页监听页内登录；同一身份的认证事件与初始恢复只水合一次。退出或切换
  账号会中止旧身份 epoch、清除个人学习 DOM，并按访问令牌隔离 dashboard 与
  偏好缓存，迟到的旧账号结果不能覆盖新账号界面。
- navbar、首页进度、工具页进度、通用 spotlight 和工具卡片坐标更新均合并到
  `requestAnimationFrame`；调度器使用最新坐标。
- 长页面非首屏区块使用 `content-visibility:auto` 和固有尺寸占位；工具目录只在
  每个分类区块启用，未对整棵动态目录启用，避免展开时滚动位置跳变。

### 3.3 资源与 HTTP

- 新增 352 B 的 `brand-mark.62793ed5.svg`，文件名前缀与内容 SHA-256 一致；
  相比旧品牌图单次候选传输减少 1,229,180 B（约 99.97%）。
- 六个页面、认证占位和设置页头像回退均使用该指纹 SVG，不再由这些路径下载
  1.23 MB 的旧品牌 PNG。
- 六个页面在 `<head>` 中 `modulepreload` 自己的关键入口。
- Nginx 对 CSS、JavaScript、JSON、SVG 启用 gzip。
- 只有带内容指纹的 352 B SVG 获得一年 `immutable`；HTML、API 及未指纹
  JS/CSS 继续 `no-cache`，避免旧 HTML 与新模块混用。

## 4. 权威策略依据

- [MDN `modulepreload`](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/modulepreload)：
  让浏览器更早下载并处理关键 ES module；本项目只预加载每页入口，没有预加载
  全目录资源。
- [MDN `content-visibility`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/content-visibility)：
  `auto` 可跳过屏外布局与绘制，同时保留无障碍树语义。
- [web.dev INP 优化](https://web.dev/articles/optimize-inp)：高频输入、指针和滚动
  处理应避免长任务与重复布局；本批次以取消、版本控制和每帧合并限制工作量。
- [web.dev LCP 优化](https://web.dev/articles/optimize-lcp)：关键资源应尽早可发现，
  不应让认证链阻塞公开首屏数据。
- [web.dev HTTP 缓存](https://web.dev/articles/http-cache) 与
  [MDN HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching)：
  长期 immutable 缓存必须配合内容指纹；因此没有把未指纹 JS/CSS/HTML
  直接设为长期缓存。

## 5. 本次真实验证

| 命令/检查 | 结果 |
|---|---|
| `node --test tests/*.mjs` | 73 passed，0 failed，270.9565 ms |
| `scripts/verify-frontend.ps1` | 58 passed，0 failed，177.5433 ms；所有目标 JS 语法通过 |
| `scripts/verify-quality.ps1` | 259 项 Python 测试通过；分支覆盖率 86.4%；Ruff 通过；依赖审计 0 个已知漏洞；发布选择 367/0/10 |
| `scripts/verify-foundation.ps1` | 通过；Frontend、Tools、Learning、Users、Agent 与 HTTP 部署集成门禁全部退出 0 |
| `scripts/verify-http-test-deployment.ps1` | 通过；runtime/policy/agentHistory/guestAgent/frontend/overlay/release 为 49/8/74/27/72/22/7 |
| 8088 只读 smoke | `/`、五个业务页面、指纹 SVG、navigation、runtime 和 capabilities 共 10 个路径均为 200；本轮约 3.2–233.3 ms |
| Playwright 浏览器复验 | 桌面五页与 390×844 助手页非空、无框架错误覆盖层、无横向溢出；游客 RAG、普通问答、工作流草稿、设置登录提示，以及合成账号注册、短会话创建和登录会话问答通过 |
| 助手前端契约 | 通过；旧示例不存在，帧缓冲和分区后台刷新契约存在 |
| 交互性能行为测试 | 2/2 通过；同帧只调度一次并使用最新坐标 |
| 指纹资源测试 | 352 B；SHA-256 前八位为 `62793ed5` |
| Nginx 源码边界测试 | gzip 存在；仅一个 immutable；泛路径保持 no-cache |
| 独立缺陷回测 | 鉴权迟到结果、长期列表失败、页内登录与账号切换学习状态、目录滚动占位、设置页大图回退和未跟踪发布文件均已纳入修复/测试 |
| `git diff --check` | 通过 |

浏览器复验使用本地 Playwright。匿名启动时 `/api/v1/auth/refresh` 返回预期
401，Chromium 将该请求记为一条资源错误；页面随后正确进入游客或登录门禁，
没有 `pageerror`、空白页或错误覆盖层。`http_test` 子路径在本地通过请求重写
模拟 Nginx 前缀剥离，因此这部分只属于浏览器功能证据，不能替代服务器
`nginx -t` 或真实覆盖层加载证据。

以下项目仍为 `NOT RUN`，不是失败，也不得写成通过：

- 当前性能提交的 SSH 部署、服务器 `nginx -t`、systemd、服务器 smoke 和发布后
  公网复测；
- 同一公网环境下的冷/暖缓存性能对比；
- 真实 Provider、HTTPS、容量、备份恢复、回滚演练、合规和生产签收。

## 6. 回滚与后续复验

源码最小回滚是撤销本批次列出的前端、测试、验证脚本和 Nginx 变更；没有数据库
schema 或数据迁移。部署后若发现问题，应创建新 release 并把
`/opt/starchart-ai/current` 指回上一不可变 release，再重启 8001；未实际执行
回滚前不能宣称回滚通过。

后续必须按顺序执行：

1. 复核精确 Git 差异、隐私边界和 allow-list 发布选择；
2. 只暂存当前仓库内已审计文件，提交并推送功能分支，等待 CI 全绿；
3. 获得目标提交和服务器操作授权后构建不可变发布；
4. 目标服务器执行 `nginx -t`、只重启 HTTP 测试服务，并复核旧站与新站；
5. 同条件复测公网资源、gzip/缓存头、deterministic 助手及冷/暖缓存，再决定
   本次 HTTP release 是否 `GO`。
