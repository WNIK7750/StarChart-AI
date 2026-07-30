# HTTP 正式网页路由设计

## 目标

HTTP 测试部署必须使用没有 `.html` 的正式网页地址，并在本地 8088 与
`/StarChart-AI/` 子路径部署中保持同一套行为。旧地址只作为兼容入口，不再由
站内导航生成，也不能在跳转后留在浏览器地址栏。

本设计只覆盖网页路由和部署验收。API、静态资源、上传路径、deterministic
Provider、账号隔离和生产发布边界保持不变；本批次不合并 `master`，不启动真实
Provider，也不把 HTTP 测试结论写成生产结论。

## 规范地址

| 页面 | 规范地址 |
| --- | --- |
| 首页 | `/` |
| 助手 | `/assistant` |
| 学习路线 | `/learn` |
| 学习节点 | `/learn/{slug}` |
| 工具目录 | `/tools` |
| 设置 | `/settings` |

在 HTTP 子路径部署中，上述地址统一加已校验的公共前缀，例如
`/StarChart-AI/assistant` 和 `/StarChart-AI/learn/rag`。除首页外，规范地址不以
斜杠结尾；尾斜杠请求使用 `308` 跳转到无尾斜杠地址。

学习节点 `slug` 只允许小写字母、数字和连字符，且长度有界。合法但不存在的
节点仍由现有 Learning 页面错误边界展示“未找到”，不新增数据库查询到静态页面
路由。

## 旧地址兼容

旧入口使用 `308 Permanent Redirect`：

| 旧地址 | 目标地址 |
| --- | --- |
| `/index.html` | `/` |
| `/assistant.html` | `/assistant` |
| `/learn.html` | `/learn` |
| `/learn-node.html?slug=rag` | `/learn/rag` |
| `/tools.html` | `/tools` |
| `/settings.html` | `/settings` |

普通查询参数必须保留，例如 `tools.html?q=RAG` 跳转到 `tools?q=RAG`。
`learn-node.html` 的 `slug` 转入路径，其余安全查询参数继续保留。URL fragment
不会发送到服务器；浏览器按标准重定向行为保留 fragment，并由浏览器测试验证。
缺少合法 `slug` 的旧学习节点入口跳转到 `/learn`。

重定向目标必须使用当前已校验的公共部署前缀。服务器收到
`X-Forwarded-Prefix: /StarChart-AI` 时，不能把用户重定向到站点根目录的
`/assistant`，避免逃逸到旧站。

## 应用与 Nginx 边界

FastAPI 在根静态挂载之前注册一个小型网页路由适配层：

- 规范路由返回现有 HTML 文件，不复制页面；
- 旧路由产生前缀感知的 `308`；
- `/learn/{slug}` 返回 `learn-node.html`；
- API、`/uploads` 和 `/assets` 继续由现有边界处理。

Nginx 继续剥离 `/StarChart-AI` 前缀并把请求交给 8001。它不复制一套页面映射，
只负责公共前缀、缓存、压缩、限流和代理头；规范化逻辑由应用统一负责，因此本地
8088 和服务器 8001 不会出现两套不同路由。

`Location` 响应必须包含 `/StarChart-AI` 前缀。Nginx 配置回归测试同时证明旧站
`/old-ai-nav/`、`/chat`、`/health` 和 `/chat-widget.js` 没有被新网页路由接管。

## 前端链接生成

所有静态导航、搜索结果、认证菜单、Learning 跳转、助手工作流跳转和设置页返回
地址改为规范地址。站内代码不得再生成六个产品页面的 `.html` URL。

`safeInternalHref` 在安全校验后集中兼容后端或旧数据库中残留的 `.html` href：

- 已知旧页面被投影为规范路径；
- `learn-node.html?slug=...` 被投影为 `/learn/{slug}`；
- 未知文件、外部 URL、编码分隔符和路径遍历继续拒绝或按原规则处理；
- 公共前缀只添加一次。

这样无需为了 URL 外观修改既有用户数据或历史内容。后续新内容只能写规范路径。

`learn-node.html` 会被服务在两级路径 `/learn/{slug}`。该页面自己的静态资源和
静态导航使用可在本地与子路径下正确解析的上级相对路径；动态链接继续通过
`safeInternalHref` 添加公共前缀。

## 缓存与错误处理

- 规范 HTML 与重定向继续使用 `no-cache`，不引入未指纹长缓存。
- 指纹 SVG 的 immutable 规则保持不变。
- 未知规范页面返回 404，不回退到首页，避免“软 404”。
- 非法学习 slug 返回 404；路径遍历、编码斜杠和重复公共前缀继续拒绝。
- 旧地址重定向不携带认证信息，不记录查询正文、Cookie 或 Token。

## 验证

实施采用 TDD，至少覆盖：

1. 本地 TestClient 的六类规范路由返回 200，地址栏不需要 `.html`；
2. 旧地址返回带正确公共前缀的 308，并保留安全查询参数；
3. `/learn/rag` 的 CSS、JS、图片、站内导航与 Learning API 全部正常；
4. Node 契约扫描确认站内产品链接不再生成 `.html`；
5. `safeInternalHref` 将旧 API/数据库 href 投影为规范地址，同时保持路径安全；
6. Nginx 子路径、gzip、缓存、旧站兼容和 API 路由回归通过；
7. 本地 8088 与服务器 `/StarChart-AI/` 的 clean-route smoke 全部通过；
8. Playwright 从首页逐页点击，最终地址均为规范地址，查询参数、fragment、登录
   门禁和前进/后退正常；
9. 服务器部署后复核旧 `.html` 入口的 308、规范页面的 200、API/资源状态、旧站
   路由和 deterministic 游客问答。

发布前继续运行 Frontend、Foundation、Quality、HTTP deployment、秘密扫描和
release allowlist。只有当前固定提交、发布包 SHA-256、服务器 `nginx -t`、
8001、旧站/新站 smoke 和浏览器验收全部通过，当前 HTTP release 才可写 `GO`。

## 回滚

本批次不修改数据库 schema。失败时把 `/opt/starchart-ai/current` 指回服务器上
实际确认的上一不可变 release，重启 8001，并在 `nginx -t` 后 reload。保留故障
release 和隔离数据用于诊断，不删除或覆盖现有数据库。

未真实执行回滚时，回滚演练保持 `NOT RUN`。即使 HTTP clean-route 部署通过，
生产发布仍为 `NO-GO`。
