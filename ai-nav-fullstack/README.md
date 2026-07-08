# AI 知识导航前后端分离版

这是 `design/v2` 四个页面的前后端分离实现。前端负责页面结构、样式、动画和交互，所有导航、知识地图、学习资源、节点介绍、工具分类和工具列表都通过后端 API 获取。

当前学习区已经支持：

- 节点主资料、章节目录、建议学习时长和概览。
- 主资料合入资料列表，并显示“主资料”标签。
- 资料访问标签：“国内可访问”和“外网”。
- 每个学习模块至少包含多条国内可访问资料和视频资料。

## 目录结构

```text
ai-nav-fullstack/
  backend/             FastAPI 后端服务
  database/            SQLite schema、seed 和运行时数据库
  frontend/            静态前端页面与 JS/CSS 模块
  docs/                数据库与接口说明
```

## 启动

```powershell
cd D:\Web期末作业\ai-nav2\ai-nav-fullstack
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\run.py
```

打开：

- 首页：http://127.0.0.1:8088/index.html
- 学习页：http://127.0.0.1:8088/learn.html
- 节点页：http://127.0.0.1:8088/learn-node.html?slug=ai-literacy
- 工具页：http://127.0.0.1:8088/tools.html
- API 文档：http://127.0.0.1:8088/docs

## API

- `GET /api/v1/navigation`
- `GET /api/v1/learning/roadmap`
- `GET /api/v1/learning/resources?domain=core`
- `GET /api/v1/learning/nodes/{slug}`
- `GET /api/v1/tools/categories`
- `GET /api/v1/tools`
- `GET /api/v1/tools/latest`
- `GET /api/v1/tools/workflows`

## 数据维护

学习区内容集中维护在 `database/learning_content.sql`：

- `learning_materials`：每个节点的主资料。
- `learning_material_sections`：主资料目录和建议学习时长。
- `learning_node_tags`：节点标签。
- `learning_node_links`：补充资料、视频、文档和课程链接。

资料访问类型使用 `access_type` 标记：

- `cn`：国内可访问。
- `external`：外网资料。
