# Git 规划：用户设置页与密保找回密码

## 本次目标

完善用户模块的账号安全体验：

- 找回密码入口放在登录弹窗。
- 密保问题设置放在用户设置页。
- 头像菜单改为轻量快捷入口，可跳转到完整设置页。
- “我的空间”拆成更细的设置分区，方便后续扩展学习记录、收藏、Agent 工作流等能力。

## 建议提交拆分

### Commit 1：后端密保与找回密码

建议提交信息：

```text
feat(auth): 增加密保找回密码能力
```

包含文件：

- `backend/app/api/v1/routers/auth.py`
- `backend/app/api/v1/routers/users.py`
- `backend/app/db/database.py`
- `database/schema.sql`
- `docs/database-design.md`
- `docs/user-module-design.md`

主要内容：

- 新增 `user_security_questions` 表。
- 新增用户设置页读取和保存密保问题接口。
- 新增登录页密保找回密码三段式接口：
  - `POST /api/v1/auth/password-reset/security/start`
  - `POST /api/v1/auth/password-reset/security/verify`
  - `POST /api/v1/auth/password-reset/security/confirm`
- 重置密码后递增 `token_version`，旧访问令牌失效，并撤销旧会话。

### Commit 2：前端账号入口与设置页

建议提交信息：

```text
feat(user): 增加用户设置页和头像快捷菜单
```

包含文件：

- `frontend/assets/js/auth-ui.js`
- `frontend/assets/js/settings.js`
- `frontend/assets/js/api.js`
- `frontend/settings.html`

主要内容：

- 登录弹窗新增“忘记密码？”入口。
- 头像菜单改为 GitHub 风格的快捷入口。
- 新增独立用户设置页，分为公开资料、账号、安全与密保、登录设备、偏好、学习空间、工作流。
- 设置页数据全部调用后端接口；学习记录、收藏、工作流只渲染后端 reserved 响应，不造假数据。

### Commit 3：文档同步

建议提交信息：

```text
docs: 更新用户安全模块说明
```

包含文件：

- `README.md`
- `ai-nav-fullstack/README.md`
- `docs/git-plan-user-settings-security.md`

主要内容：

- 增加 `settings.html` 页面入口。
- 增加密保与找回密码 API 说明。
- 记录本次提交规划与验证方式。

## 验证记录

已执行：

```powershell
python -m py_compile ai-nav-fullstack/backend/app/api/v1/routers/auth.py ai-nav-fullstack/backend/app/api/v1/routers/users.py ai-nav-fullstack/backend/app/db/database.py
node --check ai-nav-fullstack/frontend/assets/js/api.js
node --check ai-nav-fullstack/frontend/assets/js/auth-ui.js
node --check ai-nav-fullstack/frontend/assets/js/settings.js
```

已用接口测试覆盖：

- 注册测试用户。
- 初始密保状态为空。
- 当前密码错误时不能设置密保。
- 当前密码正确时可以保存密保问题。
- 登录页找回密码可发起密保验证。
- 密保答案错误会拒绝。
- 密保答案正确可获取重置令牌。
- 重置密码后旧密码失效，新密码可登录。
- 重置密码后旧 access token 失效。

已用浏览器烟测覆盖：

- 登录弹窗可进入“忘记密码”流程。
- `settings.html#security` 可进入安全与密保分区。
- 设置页控制台无错误。

截图：

- `C:/Users/LEGION/AppData/Local/Temp/ai-nav-forgot-password.png`
- `C:/Users/LEGION/AppData/Local/Temp/ai-nav-settings-security.png`

## 提交前检查

```powershell
git status --short
git diff --stat
```

不要提交：

- `ai-nav-fullstack/uploads/`
- `.venv/`
- `*.log`
- 本地数据库备份或临时截图

