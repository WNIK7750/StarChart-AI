# AI 知识导航

AI 知识导航是一个面向 AI 学习与工具检索的前后端分离项目。项目以 `design/v2` 中的页面为视觉参考，实现了首页、学习路径页、学习节点介绍页和工具页，并通过后端接口统一提供导航、知识地图、学习资料、节点目录和工具数据。

## 项目特点

- 前后端分离：前端页面通过 `/api/v1` 接口获取数据，不直接写死业务数据。
- 数据集中管理：学习路线、节点主资料、补充资料、工具分类等数据由 SQL 脚本维护。
- 国内学习友好：学习资料支持“国内可访问”和“外网”标签，每个学习模块都配置了国内可访问资源和视频资源。
- 工程化结构：后端、前端、数据库、文档按目录拆分，便于继续维护和扩展后台管理能力。

## 目录结构

```text
ai-nav2/
  design/               v2 页面参考稿与设计资产
  ai-nav-fullstack/     当前前后端分离实现
    backend/            FastAPI 后端服务
    database/           SQLite 表结构、基础数据和学习内容数据
    frontend/           静态页面、样式和前端 API 调用逻辑
    docs/               数据库说明与 Git 报告
  assets/               旧版静态资源
  README.md             项目总说明
```

## 快速启动

```powershell
cd D:\Web期末作业\ai-nav2\ai-nav-fullstack
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\run.py
```

启动后访问：

- 首页：`http://127.0.0.1:8088/index.html`
- 学习路径：`http://127.0.0.1:8088/learn.html`
- 学习节点介绍：`http://127.0.0.1:8088/learn-node.html?slug=ai-literacy`
- 工具页：`http://127.0.0.1:8088/tools.html`
- API 文档：`http://127.0.0.1:8088/docs`

## 核心接口

- `GET /api/v1/navigation`：顶部导航
- `GET /api/v1/learning/roadmap`：学习路径知识地图
- `GET /api/v1/learning/resources`：学习页推荐资源卡片
- `GET /api/v1/learning/nodes/{slug}`：学习节点介绍、主资料、目录和补充资料
- `GET /api/v1/tools/categories`：工具分类
- `GET /api/v1/tools`：工具列表
- `GET /api/v1/tools/latest`：最新工具
- `GET /api/v1/tools/workflows`：工具工作流

## 数据维护

主要数据文件位于：

- `ai-nav-fullstack/database/schema.sql`：数据库表结构
- `ai-nav-fullstack/database/seed.sql`：导航、路线图、工具库基础数据
- `ai-nav-fullstack/database/learning_content.sql`：学习节点主资料、目录、标签和补充资料

新增学习资料时，建议优先维护 `learning_content.sql` 中的 `learning_node_links`。其中：

- `access_type = 'cn'` 表示国内可访问。
- `access_type = 'external'` 表示需要外网访问。
- `link_type = 'video'` 表示视频资料。

## Git 使用建议

```powershell
git status
git add .
git commit -m "初始化 AI 知识导航前后端分离项目"
```

提交前建议确认：

- 没有把 `.venv/`、运行时数据库、测试截图等本地文件加入版本库。
- README、数据库说明和 Git 报告均为中文说明。
- 后端接口和前端页面可以正常运行。
