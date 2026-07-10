# 前端入口排查报告

更新时间：2026-07-11

## 结论

本次工具页首刷缺少大量工具的原因不是数据丢失，而是同一个生产页面存在两条渲染链路：

1. `frontend/tools.html` 内联脚本维护完整工具目录，渲染结果接近设计稿。
2. `frontend/assets/js/v2-api.js` 在 `tools.html` 加载后又调用后端 `/api/v1/tools*` 接口重绘 `#toolsSections`。

后端种子数据少于 `tools.html` 内联目录，所以页面会被覆盖成“工具数量很少”的版本。现已将工具页 API 自动覆盖改为显式开启：只有 `body[data-api-tools="true"]` 时才会使用 API 重绘工具页。

## 生产前端文件分类

| 文件 | 类型 | 当前是否作为生产入口 | 主要职责 | 依赖关系 | 备注 |
|---|---|---:|---|---|---|
| `frontend/index.html` | v2 生产页面 | 是 | 首页、路线图、首页工具区 | 内联脚本 + `assets/js/v2-api.js` | `v2-api.js` 负责导航、用户区、搜索、路线图与首页工具接口补水 |
| `frontend/learn.html` | v2 生产页面 | 是 | 学习路线页 | 内联脚本 + `assets/js/v2-api.js` | 学习数据由后端接口补水 |
| `frontend/learn-node.html` | v2 生产页面 | 是 | 学习节点介绍页 | 内联脚本 + `assets/js/v2-api.js` | 节点详情由后端接口补水 |
| `frontend/tools.html` | v2 生产页面 | 是 | 工具导航页完整目录 | 内联完整数据 + `assets/js/v2-api.js` | 工具目录以本页内联数据为准；`v2-api.js` 只保留导航、搜索、用户区能力 |
| `frontend/settings.html` | v2 生产页面 | 是 | 用户设置中心 | `assets/js/settings.js` | 用户资料、头像、安全设置等 |
| `frontend/assets/js/v2-api.js` | v2 共享增强脚本 | 是 | API 客户端、导航、搜索、用户区、学习页补水 | `api.js`、`auth-ui.js`、`site-search.js` | 已避免默认覆盖工具页完整目录 |
| `frontend/assets/js/site-search.js` | v2 共享搜索 | 是 | 顶部搜索、推荐、结果下拉、跳转定位 | `api.js` | 首页和工具页搜索同一能力 |
| `frontend/assets/js/auth-ui.js` | v2 共享用户区 | 是 | 登录弹窗、头像菜单、会话状态 | `api.js` | 顶部头像与用户菜单 |
| `frontend/assets/js/settings.js` | 设置页脚本 | 是 | 设置页表单、头像裁剪、密保 | `api.js` | 仅 `settings.html` 使用 |

## 历史或备用前端文件

| 文件/目录 | 类型 | 当前状态 | 关系与风险 |
|---|---|---|---|
| `frontend/assets/js/tools.js` | 旧模块化工具页脚本 | 当前生产页未引用 | 也会写 `#toolsSections`，若重新引入会再次与 `tools.html` 内联渲染冲突 |
| `frontend/assets/js/home.js` | 旧模块化首页脚本 | 当前生产页未引用 | 属于早期前后端分离尝试 |
| `frontend/assets/js/learn.js` | 旧模块化学习页脚本 | 当前生产页未引用 | 属于早期前后端分离尝试 |
| `frontend/assets/js/node.js` | 旧模块化节点页脚本 | 当前生产页未引用 | 属于早期前后端分离尝试 |
| `frontend/assets/js/layout.js` | 旧共享布局脚本 | 当前生产页未引用 | 被旧模块化脚本依赖 |
| `frontend/assets/js/roadmap.js` | 路线图模块脚本 | 间接使用 | 当前主要通过 `v2-api.js` 处理路线图 |
| `frontend - 副本/` | 备份目录 | 非生产入口 | 保留旧页面备份，不应作为服务入口 |
| 根目录 `index.html` | 旧版单页 | 非生产入口 | 与 fullstack 版本无直接依赖，容易造成误判 |
| `design/` | 设计稿与实验稿 | 非生产入口 | 用作视觉参考，不应由后端直接服务 |
| `design/v2/` | v2 设计稿 | 非生产入口 | 当前生产页主要从这里迁移而来 |

## 工具页当前规则

| 项目 | 当前规则 |
|---|---|
| 首刷数据源 | `frontend/assets/js/tool-data.js` 的工具事实数据 + `frontend/assets/js/tool-page-lists.js` 的页面展示列表 |
| API 覆盖 | 默认关闭；仅 `body[data-api-tools="true"]` 时开启 |
| 工具链接 | 工具本体在 `tool-data.js` 统一维护，卡片使用 `target="_blank"` 打开官方链接 |
| 工具图标 | 优先读取 `assets/icons/tools/` 本地图标，外部 favicon 只作为兜底 |
| 可见数量 | 每个分区分页显示 12 个，分区统计显示该分区完整数量 |

## 工具数据分层

| 文件 | 维护内容 | 不应维护 |
|---|---|---|
| `frontend/assets/js/tool-data.js` | 工具本体事实：名称、别名、描述、官网 URL、本地图标、图标兜底、唯一 ID | 是否推荐、最新推荐、页面运营位 |
| `frontend/assets/js/tool-data.js` 的 `placements` | 工具出现在哪个分类、子分类、热度和标签 | 重复维护工具名称、描述、官网和图标 |
| `frontend/assets/js/tool-page-lists.js` | 工具页展示列表，如最新滚动推荐 | 工具本体事实 |

当前工具数据已经去重为 135 个唯一工具、137 条分类展示关系。比如 `豆包` 只维护一条工具本体，但可以通过 `placements` 出现在需要的分类中。

## 工具资产维护命令

| 命令 | 作用 |
|---|---|
| `node scripts/audit-tool-data.mjs` | 检查工具数据、展示关系、最新推荐、本地图标是否完整，以及是否存在重复工具或孤儿图标 |
| `node scripts/sync-tool-icons.mjs` | 为缺失或错误的图标生成统一 SVG 兜底，并回写 `tool-data.js` 的图标路径 |

当前图标目录为 `frontend/assets/icons/tools/`，保持“一条工具本体对应一个图标文件”。如果后续替换官方图标，优先覆盖 `tool-data.js` 中该工具 `icon` 指向的文件，避免同一工具出现多套图标。

## 后续维护建议

| 优先级 | 建议 | 原因 |
|---|---|---|
| 高 | 将 `tools.html` 的 `categories/latestTools/toolMeta` 拆到独立数据文件或后端种子表 | 防止页面脚本继续膨胀，也方便后续后台管理 |
| 高 | 删除或归档旧模块化脚本的生产引用可能性 | 防止再次出现多个脚本写同一个容器 |
| 中 | 后端工具表补齐到与 `tools.html` 同量级后，再开启 `data-api-tools="true"` | 真正完成前后端分离时需要数据库成为唯一真实来源 |
| 中 | 为工具图标准备本地缓存或后端代理 | 外部 favicon 服务会偶发 404 或被浏览器策略拦截 |
