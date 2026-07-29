# Assistant and Site Performance Design

## Goal

在不引入前端框架、打包器、Service Worker 或真实 Provider 调用的前提下，
让 HTTP 测试站点的助手回答、页面首次可交互和跨页跳转明显更快，同时保持
登录/游客数据边界、子路径部署和发布版本一致性。

## Confirmed root causes

- 助手默认问题“RAG 和微调应该先学哪个？”会落入通用问答，检索又把整句
  当作一个查询，因此确定性 Provider 没有可展示的站内回答。
- SSE 每个 delta 都写 `textContent` 并读取/写入滚动位置，造成重复字符串复制
  和布局；回答完成后还同步等待短期、长期两张会话列表。
- 公共页面先等待导航接口和完整登录恢复，再开始各自的公开数据请求；一次慢
  refresh 会阻塞首页、学习页和工具页的内容与交互。
- 搜索框每个输入事件立即发请求，旧请求既不取消，也可能晚到后覆盖新结果。
- 1,229,532 字节的 `logo.png` 同时用于 favicon 和隐藏登录对话框默认头像，
  每个页面都会承担不必要的冷加载成本。
- HTTP 子路径对全部响应统一 `no-cache`，能避免发布版本错配，但让 JS/CSS
  暖加载仍需网络重验证；当前未建立完整的静态资源指纹流水线，不能把所有
  未指纹资源直接改成 `immutable`。

## Chosen design

### Deterministic assistant example

把首个建议改为“RAG 怎么学？”。该问题会稳定进入 `learning_plan`，检索词
归一为 `RAG`，并只读返回站内 RAG 学习节点和学习步骤。其余建议继续覆盖工具
推荐、学习导航和工作流草案。

### Assistant rendering and list refresh

- 把 SSE delta 写入帧缓冲区，每个动画帧最多更新一次文本和滚动；完成、中止
  或异常时强制清空缓冲，最终仍以结构化响应覆盖完整答案。
- 回答渲染完成即恢复输入控件；会话列表在后台刷新，不再进入用户等待路径。
- 短期会话只刷新短期列表，长期会话只刷新长期列表；升级操作才刷新两者。
- 为列表请求增加递增版本号，迟到的旧响应不得覆盖更新后的列表。

### Public page initialization

- 页面壳层立即绑定搜索、登录弹窗和基础交互；导航水合与登录恢复并行后台运行。
- 首页、学习页、节点页和工具页不再用顶层 `await` 阻塞自己的交互与公开数据。
- 设置页仍严格等待登录恢复，因为其内容全部属于用户私有域。
- 登录弹窗事件只绑定一次；runtime capabilities 与登录恢复并行。

### Site-wide browser work

- 搜索输入使用 180 ms 去抖，取消上一请求，并以查询版本拒绝旧结果。
- 学习页的 roadmap、资源和用户 dashboard 并行启动；各自已有降级边界。
- navbar 与首页滚动进度合并到 `requestAnimationFrame`，每帧最多写一次样式。
- 在每页 `<head>` 预加载自己的入口 ES module，让大 HTML 尚未解析到底部时就
  开始下载入口及其依赖。
- 对明确的长页面下半区使用 `content-visibility:auto` 与固有尺寸占位，跳过
  首屏外布局和绘制，但不从无障碍树移除内容。

### Assets and HTTP delivery

- 新增内容指纹命名的轻量 SVG 品牌图标，替换所有 favicon、设置页品牌图和
  登录默认头像引用；保留旧文件但不再由页面加载，避免改动用户已有资产。
- Nginx 只对该指纹 SVG 返回一年 `immutable`；HTML、API 和未指纹 JS/CSS
  继续 `no-cache`，避免旧 HTML/新 module 混用。
- 为 HTML、CSS、JavaScript、JSON 和 SVG 开启 gzip 类型声明；不压缩已压缩
  的 PNG/ICO。

## Error and security behavior

- 取消搜索请求不显示错误；真正离线时仍走现有本地索引。
- 登录恢复失败继续渲染游客状态；公开 Learning/Tools 不因 Users 故障而失效。
- 任何优化均不读取真实 `.env`，不持久化访问令牌，不导入游客历史到测试账号，
  不调用真实 Provider。
- deterministic HTTP 测试结论与生产发布结论分开；缺少 HTTPS、容量、恢复、
  回滚和外部签收时，生产继续 `NO-GO`。

## Verification

- TDD 覆盖默认建议契约、帧缓冲、非阻塞页面入口、搜索最新结果、并行学习水合、
  指纹资源和 Nginx 缓存/压缩边界。
- 运行 Agent、Frontend、Foundation、Quality 和 HTTP 部署门禁；Python 运行时
  不可用时不得伪造结果，改在目标服务器或可用隔离运行时重跑。
- 在同一公网 HTTP 路径复测 HTML、入口模块、SVG、runtime、navigation 和
  deterministic guest chat 的状态码、缓存头、大小及耗时。
- 使用无头 Chrome 检查首页、助手页桌面/移动视口、控制台错误和一次建议问答
  交互；不得携带测试账号密码到日志或证据。
