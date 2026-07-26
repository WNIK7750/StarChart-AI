# HTTP 子路径测试部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** 在不削弱现有 `production` 安全基线的前提下，实现 `/StarChart-AI/` HTTP 测试部署、单一受限测试账号、公开的确定性游客助手、隔离的真实 Provider 预览，以及可审计的部署覆盖层和验证证据。

**Architecture:** 应用内部继续使用根路径 `/api/v1`、`/uploads` 和静态前端；Nginx 在公网 8001 入口剥离 `/StarChart-AI` 前缀，前端通过统一公共路径模块生成浏览器 URL。`http_test` 和 `provider_preview` 是独立于 `production` 的严格配置档，分别使用独立数据库、上传目录、端口和 systemd 单元。游客助手只接受有界浏览器历史且不接触用户数据库；登录会话从服务端加载有界历史；部署策略在后端集中拒绝测试账号不允许的身份、恢复、隐私写入和删除操作。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、SQLite、原生 ES Modules、Node.js test runner、PowerShell 验证脚本、Nginx、systemd、GitHub Actions。

## Global Constraints

- 不读取、打印、提交、复制、移动或修改真实 `.env`。
- 不在源码、文档、测试、命令行参数、日志或证据中写入测试账号用户名、密码、API Key、Cookie、Token 或 SSH 私钥。
- 不调用真实 Provider，不产生付费或生产流量；真实 Provider 预览只能在最终人工检查点之后由用户显式执行。
- 不修改或放宽 `production` 的 HTTPS、Secure Cookie、外部持久化路径、Provider allowlist、单 worker 和成本限制。
- 公网 8001 始终使用 `deterministic` Provider；8002 仅绑定 `127.0.0.1`，通过 SSH 隧道访问。
- 测试账号登录后不自动导入游客历史；这是可复审的当前产品决策，不是永久迁移契约。
- 浏览器游客历史上限固定为 10 个会话、每会话 40 条消息、保存 7 天；发给后端的最近历史最多 12 条、合计最多 12,000 字符。
- 数据库内头像路径继续保存为 `/uploads/...`；部署前缀只在浏览器 URL 投影层添加。
- 所有新增后端入口使用严格 Pydantic 模型，未知字段拒绝；所有受限操作以后端拒绝为准，前端隐藏只用于改善体验。
- 每个任务先写失败测试，再做最小实现，再运行目标验证；不要一次性批量实现后补测试。
- 每完成一个任务，更新 `docs/00-index/http-test-deployment-file-index.md` 的批次、文件、真实命令、真实结果、残留风险和最小回滚路径。
- 不触碰或暂存仓库中的 `.tmp_ci.txt`、`.tmp_push_ci.txt` 或其他用户已有改动。

---

## Task 1: 固化基线与新增配置档安全契约

**Files:**

- Modify: `backend/app/core/config.py`
- Modify: `backend/run.py`
- Modify: `tests/test_users_services.py`
- Modify: `tests/test_agent_provider.py`
- Create: `tests/test_http_test_runtime.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```python
DEPLOYMENT_PROFILES = frozenset(
    {"development", "test", "http_test", "provider_preview", "production"}
)
PUBLIC_BASE_PATH: str
HTTP_TEST_ACCOUNT_USERNAME: str
HTTP_TEST_GUEST_AGENT_ENABLED: bool
APP_HOST: str
APP_PORT: int

def normalize_public_base_path(value: str) -> str: ...

def validate_runtime_security(
    environment: str,
    secret_key: str,
    cors_origins: tuple[str, ...],
    refresh_cookie_secure: bool,
    *,
    public_base_path: str = "",
    http_test_account_username: str = "",
    agent_provider: str = "deterministic",
    agent_provider_live_enabled: bool = False,
    ...
) -> None: ...
```

### Step 1: 写失败配置测试

- [ ] 在 `tests/test_http_test_runtime.py` 添加参数化测试，证明：
  - `http_test` 接受显式 `http://47.100.94.1` origin、`Secure=false`、外部数据库和上传路径。
  - `http_test` 拒绝默认/短 secret、源码树内数据路径、`RESET_DATABASE_ON_START=1`、空测试账号标识、非 `/StarChart-AI` 形式的公共前缀、live Provider 或非 deterministic Provider。
  - `provider_preview` 拒绝非 loopback host、非 8002 不是硬性条件但端口必须合法、非 HTTPS Provider URL、空 Provider allowlist、缺少成本边界、源码树内数据路径。
  - `production` 的原有 HTTPS 与 Secure Cookie 失败用例保持不变。
  - `normalize_public_base_path("") == ""`，`normalize_public_base_path("/StarChart-AI/") == "/StarChart-AI"`，并拒绝 URL、反斜杠、`..`、查询串和片段。
- [ ] 在 `tests/test_agent_provider.py` 添加 `provider_preview` 与 `production` 相同的 Provider HTTPS/allowlist/北京地域约束测试。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_runtime.py tests/test_agent_provider.py -q
```

Expected: 新测试因环境枚举、变量和验证逻辑尚不存在而失败；不得因导入真实 `.env` 获得假通过。

### Step 2: 最小实现配置档

- [ ] 将运行环境枚举扩展为五种配置档，但把通用“非开发安全条件”抽成内部 helper，禁止复制出互相漂移的 `if` 块。
- [ ] `http_test` 强制：
  - 非默认且至少 32 字符的 secret；
  - `RESET_DATABASE_ON_START=0`；
  - 数据库和上传目录位于源码树外；
  - 显式 HTTP origin；
  - `REFRESH_COOKIE_SECURE=0` 且 `SameSite=lax`；
  - `PUBLIC_BASE_PATH=/StarChart-AI`；
  - 非空测试账号标识；
  - deterministic Provider、live off。
- [ ] `provider_preview` 强制：
  - 与生产相同的 secret、持久化路径、Provider HTTPS、host allowlist、北京地域、成本和单 worker约束；
  - `APP_HOST=127.0.0.1`；
  - 独立数据库/上传目录；
  - live on 仅在 Provider 完整配置后允许。
- [ ] `backend/run.py` 改为读取已校验的 `APP_HOST`、`APP_PORT`，保留开发 reload 和单 worker 契约。
- [ ] 不在默认值中写公网 IP、账号或凭据；这些只存在于部署环境模板的空占位符中。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_runtime.py tests/test_agent_provider.py tests/test_users_services.py -q
python -m compileall -q backend/app backend/run.py
git diff --check
```

Expected: 全部退出码 0；测试输出不包含真实账号或密钥。

- [ ] 更新文件索引并提交：

```powershell
git add backend/app/core/config.py backend/run.py tests/test_http_test_runtime.py tests/test_agent_provider.py tests/test_users_services.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: add isolated HTTP test runtime profiles"
```

---

## Task 2: 提供公开运行能力契约与公共路径投影

**Files:**

- Modify: `backend/app/platform/schemas.py`
- Modify: `backend/app/api/v1/routers/common.py`
- Create: `frontend/assets/js/public-path.js`
- Modify: `frontend/assets/js/api.js`
- Modify: `frontend/assets/js/auth-ui.js`
- Modify: `frontend/assets/js/settings.js`
- Create: `tests/test_public_path.mjs`
- Modify: `tests/test_frontend_api.mjs`
- Modify: `tests/test_auth_ui.mjs`
- Modify: `tests/test_users_frontend.mjs`
- Modify: `tests/test_http_test_runtime.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```python
class PublicAuthCapabilities(StrictModel):
    registration: bool
    recovery: bool
    identityChanges: bool
    privacyWrites: bool

class PublicAgentCapabilities(StrictModel):
    guestChat: bool
    authenticatedSessions: bool

class PublicRuntimeCapabilities(StrictModel):
    deploymentProfile: str
    publicBasePath: str
    auth: PublicAuthCapabilities
    agent: PublicAgentCapabilities
```

```javascript
export function normalizePublicBasePath(value) {}
export function detectPublicBasePath(moduleUrl = import.meta.url) {}
export function withPublicBasePath(path, basePath = PUBLIC_BASE_PATH) {}
export const PUBLIC_BASE_PATH = detectPublicBasePath();
export const API_BASE = `${PUBLIC_BASE_PATH}/api/v1`;
```

### Step 1: 写失败的 API 与 URL 测试

- [ ] `tests/test_http_test_runtime.py` 验证 `GET /api/v1/runtime/public`：
  - `http_test` 返回四个 auth 写能力为 `false`、游客聊天为 `true`、登录会话为配置值。
  - development/test 返回当前正常功能，不泄露 username、路径、Provider URL、secret 或 API key。
- [ ] `tests/test_public_path.mjs` 覆盖根部署、`/StarChart-AI/`、尾斜杠、上传路径、已经加前缀的路径、绝对 URL 拒绝和双前缀拒绝。
- [ ] 扩展前端测试，断言所有 refresh/login/profile/avatar API 都通过同一个 `API_BASE`；头像 `/uploads/...` 显示为 `/StarChart-AI/uploads/...`，数据库契约不变。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_runtime.py -q
node --test tests/test_public_path.mjs tests/test_frontend_api.mjs tests/test_auth_ui.mjs tests/test_users_frontend.mjs
```

Expected: 因 endpoint 与模块不存在而失败。

### Step 2: 实现单一 URL 来源

- [ ] 新增 `/runtime/public` 响应模型与路由，值只从已校验配置派生。
- [ ] `public-path.js` 从模块 URL 中剥离 `/assets/js/public-path.js` 得到部署前缀；允许测试或选择页通过 `window.AI_NAV_PUBLIC_BASE_PATH` 明确覆盖。
- [ ] `api.js` 导入并重新导出 `API_BASE`，所有 refresh 排除判断改为由 `API_BASE` 拼接。
- [ ] `auth-ui.js` 加载公开能力后隐藏注册/恢复入口；登录成功、登出和 token 失效时派发：

```javascript
window.dispatchEvent(new CustomEvent("ai-nav-auth-changed", {
  detail: { authenticated: Boolean(accessToken) }
}));
```

- [ ] `settings.js` 使用 `withPublicBasePath` 投影头像 URL，并根据公开能力隐藏身份修改、密码、安全问题和隐私写入区；资料、头像、偏好、会话、工作流保持可用。
- [ ] endpoint 失败时使用保守策略：不主动展示受限写入口，但后端仍是最终授权边界。

### Step 3: 回归并提交

- [ ] 运行本任务测试和：

```powershell
node --test tests/test_frontend_url_safety.mjs tests/test_frontend_entries.mjs
git diff --check
```

- [ ] 提交：

```powershell
git add backend/app/platform/schemas.py backend/app/api/v1/routers/common.py frontend/assets/js/public-path.js frontend/assets/js/api.js frontend/assets/js/auth-ui.js frontend/assets/js/settings.js tests/test_public_path.mjs tests/test_frontend_api.mjs tests/test_auth_ui.mjs tests/test_users_frontend.mjs tests/test_http_test_runtime.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: make public URLs deployment-prefix aware"
```

---

## Task 3: 集中执行测试账号策略

**Files:**

- Create: `backend/app/users/deployment_policy.py`
- Create: `backend/app/api/v1/dependencies/deployment_policy.py`
- Modify: `backend/app/api/v1/routers/auth.py`
- Modify: `backend/app/api/v1/routers/users.py`
- Modify: `backend/app/api/v1/routers/privacy.py`
- Create: `tests/test_http_test_policy.py`
- Modify: `tests/test_users_services.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```python
DeploymentAction = Literal[
    "register",
    "login",
    "identity_update",
    "password_update",
    "recovery",
    "security_questions_update",
    "privacy_consent_update",
    "privacy_export",
    "account_deletion_request",
    "account_deletion_cancel",
]

class DeploymentPolicyError(UsersError): ...

def enforce_deployment_action(
    action: DeploymentAction,
    *,
    login_identifier: str | None = None,
) -> None: ...

def require_deployment_action(action: DeploymentAction): ...
```

统一拒绝响应：

```json
{
  "detail": {
    "code": "DEMO_ACCOUNT_RESTRICTED",
    "message": "当前 HTTP 测试账号不允许执行此操作。"
  }
}
```

### Step 1: 以攻击路径写失败测试

- [ ] `tests/test_http_test_policy.py` 在隔离临时数据库中创建两个账号作为攻击夹具，但测试日志不打印任何明文密码。
- [ ] 覆盖：
  - `/auth/register`、username availability、全部 reset/recovery 入口返回 403。
  - 登录只接受服务端配置的唯一标识；不存在账号、其他用户名、email/phone 别名都使用不泄露账号存在性的统一失败响应。
  - `/users/me/account` PATCH、password PATCH、security questions PUT 返回 403。
  - privacy consent PUT、export POST、deletion request POST/cancel DELETE 返回 403。
  - profile PATCH、avatar POST、preferences PATCH、sessions list/revoke、saved workflows、Agent sessions、logout 仍成功。
  - read-only account/profile/privacy status 可以读取。
  - development/test 环境维持原有行为。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_policy.py -q
```

Expected: 受限入口当前仍可达，测试失败。

### Step 2: 实现集中策略并在路由入口调用

- [ ] 纯领域模块只根据已校验配置决定动作，不依赖 FastAPI。
- [ ] FastAPI dependency 将领域错误映射到统一 403；所有危险路由在业务 service 调用前执行。
- [ ] 登录标识先使用现有标准化函数规范化，再常量时间比较配置标识；不得把允许的标识写进错误消息。
- [ ] GET 能力与写能力分离；不要整体禁用 settings、Users 或 privacy router。
- [ ] 管理端 privacy execute/restore/anonymize 继续由原权限系统控制，普通测试账号不能取得管理权限；新增测试证明策略没有意外放行。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_policy.py tests/test_users_services.py -q
powershell -ExecutionPolicy Bypass -File scripts/verify-users.ps1
git diff --check
```

- [ ] 提交：

```powershell
git add backend/app/users/deployment_policy.py backend/app/api/v1/dependencies/deployment_policy.py backend/app/api/v1/routers/auth.py backend/app/api/v1/routers/users.py backend/app/api/v1/routers/privacy.py tests/test_http_test_policy.py tests/test_users_services.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: enforce HTTP test account boundaries"
```

---

## Task 4: 为登录会话补齐有界对话上下文

**Files:**

- Modify: `backend/app/agent/schemas.py`
- Modify: `backend/app/agent/sessions.py`
- Modify: `backend/app/agent/providers/base.py`
- Modify: `backend/app/agent/providers/openai_compatible.py`
- Modify: `backend/app/agent/orchestrator.py`
- Modify: `backend/app/api/v1/routers/agent.py`
- Modify: `tests/test_agent_sessions.py`
- Modify: `tests/test_agent_provider.py`
- Modify: `tests/test_agent_services.py`
- Modify: `tests/test_agent_replay.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```python
AgentHistoryRole = Literal["user", "assistant"]

class AgentHistoryMessage(StrictModel):
    role: AgentHistoryRole
    content: str = Field(min_length=1, max_length=6000)

class ProviderConversationMessage:
    role: AgentHistoryRole
    content: str

class ProviderRequest:
    ...
    history: tuple[ProviderConversationMessage, ...] = ()

class AgentSessionService:
    def context(
        self,
        user_id: int,
        session_uid: str,
        *,
        limit: int = 12,
        max_chars: int = 12_000,
    ) -> tuple[AgentHistoryMessage, ...]: ...
```

`AgentOrchestrator.respond` 的新增关键字参数：

```python
async def respond(
    self,
    request: AgentChatRequest,
    user_context: dict | None,
    *,
    history: tuple[AgentHistoryMessage, ...] = (),
    request_id: str,
    user_key: str,
    provider_allowed: bool,
    on_answer_delta=None,
) -> AgentStructuredResponse: ...
```

### Step 1: 写失败的顺序、边界和隔离测试

- [ ] Session 测试验证只返回当前 user 和 session 的最后 12 条、保持时间顺序、从最旧端裁剪到 12,000 字符、空会话返回空 tuple。
- [ ] Provider 测试验证消息顺序严格为：system → 有界历史 → 当前 user；历史中的内容不能进入 system/evidence 字段。
- [ ] Orchestrator 测试验证 deterministic 与 fake Provider 都接收同一历史契约，fallback 不把历史回显到日志或响应 meta。
- [ ] Router 测试验证加载历史发生在生成新回答之前，当前 exchange 只追加一次，replay hit 不重复追加。
- [ ] 运行：

```powershell
python -m pytest tests/test_agent_sessions.py tests/test_agent_provider.py tests/test_agent_services.py -q
```

Expected: 新接口不存在或历史未传递，测试失败。

### Step 2: 最小实现服务端历史

- [ ] 使用 session store 的现有消息表查询，不新建第二份聊天存储。
- [ ] 裁剪必须按完整消息执行，不截断单条内容；若单条超过总字符预算，则忽略更旧消息并保留允许范围内最新完整消息。
- [ ] Provider 序列化只接受 `user`/`assistant`；Pydantic 与 dataclass 双层类型约束，禁止 system/tool 注入。
- [ ] `_run_agent_request` 在 `require_owned` 后加载历史，通过关键字传给 orchestrator，再在成功响应后 append。
- [ ] `request_fingerprint` 必须包含服务器解析后的历史版本或 session 最新消息标识，防止相同 request id 在历史变化后命中旧响应；添加冲突测试。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
python -m pytest tests/test_agent_sessions.py tests/test_agent_provider.py tests/test_agent_services.py tests/test_agent_replay.py -q
powershell -ExecutionPolicy Bypass -File scripts/verify-agent.ps1
git diff --check
```

- [ ] 提交：

```powershell
git add backend/app/agent/schemas.py backend/app/agent/sessions.py backend/app/agent/providers/base.py backend/app/agent/providers/openai_compatible.py backend/app/agent/orchestrator.py backend/app/api/v1/routers/agent.py tests/test_agent_sessions.py tests/test_agent_provider.py tests/test_agent_services.py tests/test_agent_replay.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: feed bounded session history to agent"
```

---

## Task 5: 新增无用户态写入的游客助手入口

**Files:**

- Modify: `backend/app/agent/schemas.py`
- Modify: `backend/app/api/v1/routers/agent.py`
- Modify: `backend/app/agent/orchestrator.py`
- Create: `tests/test_agent_guest.py`
- Modify: `tests/test_agent_services.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```python
class AgentGuestChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AgentHistoryMessage] = Field(default_factory=list, max_length=12)
    pageContext: AgentPageContext = Field(default_factory=AgentPageContext)

    @model_validator(mode="after")
    def validate_history_budget(self): ...
```

```http
POST /api/v1/agent/guest/chat
Content-Type: application/json
X-Request-Id: optional
```

### Step 1: 写失败的匿名和负向测试

- [ ] 验证无需 Authorization 即可调用，并在 development/production 或功能关闭时返回 404/403，而不是自动启用。
- [ ] 验证历史超过 12 条、总字符超过 12,000、未知字段、`system`/`tool` role、超长 message、绝对 page URL 都返回 422。
- [ ] monkeypatch 用户 context、session service、workflow repository、Provider factory；任何一次调用都令测试失败，以证明游客路径无用户数据库/归档/真实 Provider 副作用。
- [ ] 验证响应 `meta.mode=deterministic`、`readOnly=true`，可返回 workflow draft，但不存在 save/archive 标识或用户 context。
- [ ] 验证 `X-Request-Id` 重放使用独立 `guest:<HMAC(client bucket)>` 空间；不得把原始 IP 写入 replay key、日志或响应。
- [ ] 运行：

```powershell
python -m pytest tests/test_agent_guest.py -q
```

Expected: endpoint 不存在，测试失败。

### Step 2: 实现独立游客路径

- [ ] 游客 handler 不复用 `get_current_user` 的“可选用户”模式，避免身份分支误入用户 service。
- [ ] 只在 `APP_ENV=http_test` 且 `HTTP_TEST_GUEST_AGENT_ENABLED=1` 时注册/放行。
- [ ] 强制 `provider_allowed=False`，即使进程环境误放 API key 也不得调用 Provider。
- [ ] 历史只传给 orchestrator；不创建 session、不 append、不保存 workflow。
- [ ] 客户端 bucket 使用服务端 secret 对受信代理解析后的 IP 做 HMAC，仅保留短摘要；观察性事件不得带原 IP 或消息正文。
- [ ] 继续依赖 Nginx 限流作为第一层，应用层保留 replay、请求大小和全局并发边界。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
python -m pytest tests/test_agent_guest.py tests/test_agent_services.py tests/test_agent_observability.py -q
powershell -ExecutionPolicy Bypass -File scripts/verify-agent.ps1
git diff --check
```

- [ ] 提交：

```powershell
git add backend/app/agent/schemas.py backend/app/api/v1/routers/agent.py backend/app/agent/orchestrator.py tests/test_agent_guest.py tests/test_agent_services.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: add deterministic guest agent endpoint"
```

---

## Task 6: 实现浏览器游客记忆与身份模式切换

**Files:**

- Create: `frontend/assets/js/guest-agent-memory.js`
- Modify: `frontend/assets/js/assistant-page.js`
- Modify: `frontend/assistant.html`
- Create: `tests/test_guest_agent_memory.mjs`
- Modify: `tests/test_agent_frontend.mjs`
- Modify: `tests/test_auth_ui.mjs`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```javascript
export const GUEST_MEMORY_LIMITS = Object.freeze({
  conversations: 10,
  messagesPerConversation: 40,
  ttlMs: 7 * 24 * 60 * 60 * 1000,
  requestMessages: 12,
  requestCharacters: 12000,
});

export function loadGuestConversations(now = Date.now()) {}
export function createGuestConversation(title, now = Date.now()) {}
export function appendGuestMessage(conversationId, role, content, now = Date.now()) {}
export function recentGuestHistory(conversationId, maxMessages = 12) {}
export function clearGuestConversations() {}
```

### Step 1: 写失败的本地存储测试

- [ ] 使用内存 localStorage stub 覆盖：
  - 第 11 个会话淘汰最旧项；
  - 第 41 条消息淘汰最旧项；
  - 7 天到期清除；
  - JSON 损坏、schema version 不匹配、安全 role 失败时返回空集合并自愈；
  - request history 最多 12 条和 12,000 字符；
  - clear 只删除本应用游客键。
- [ ] 页面测试覆盖：
  - 未登录提交调用 `/agent/guest/chat`，不创建服务端 session；
  - 登录后走原 `/agent/chat` 与服务端 sessions；
  - 登录事件不导入、不删除、不发送游客历史；
  - 登出后重新显示原浏览器游客历史；
  - 游客可以创建/编辑工作流草稿，但保存/归档按钮不可用并有清楚说明；
  - “清除游客历史”只在游客模式显示，需二次确认。
- [ ] 运行：

```powershell
node --test tests/test_guest_agent_memory.mjs tests/test_agent_frontend.mjs tests/test_auth_ui.mjs
```

Expected: 模块和模式分支不存在，测试失败。

### Step 2: 实现游客 UI，不混合数据边界

- [ ] localStorage 使用版本化键 `ai-nav:guest-agent:v1`，每次读取执行 TTL 和上限整理。
- [ ] `assistant-page.js` 通过 `getAccessToken()` 和 `ai-nav-auth-changed` 决定模式；不要把“401 后静默转游客”用于已登录写操作。
- [ ] 游客请求只发送当前会话的有界最近历史，响应成功后再 append assistant；失败时保留用户输入并允许重试。
- [ ] 工作流 draft 保持浏览器内存/本地存储对象；所有 `/agent/workflows/save`、session upgrade/archive 调用都要求已登录。
- [ ] 页面文案明确“游客记录仅保存在当前浏览器 7 天；登录不会自动导入”。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
node --test tests/test_guest_agent_memory.mjs tests/test_agent_frontend.mjs tests/test_auth_ui.mjs tests/test_agent_sse.mjs
powershell -ExecutionPolicy Bypass -File scripts/verify-frontend.ps1
git diff --check
```

- [ ] 提交：

```powershell
git add frontend/assets/js/guest-agent-memory.js frontend/assets/js/assistant-page.js frontend/assistant.html tests/test_guest_agent_memory.mjs tests/test_agent_frontend.mjs tests/test_auth_ui.mjs docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: add bounded guest assistant memory"
```

---

## Task 7: 提供无秘密的一次性测试账号初始化器

**Files:**

- Create: `scripts/provision-http-test-account.py`
- Create: `tests/test_provision_http_test_account.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Public interfaces:**

```python
def provision_http_test_account(
    username: str,
    password: str,
    *,
    database_path: Path,
    upload_dir: Path,
) -> dict[str, str]: ...
```

CLI 只允许：

```text
python scripts/provision-http-test-account.py
Username: [interactive input]
Password: [hidden getpass input]
```

### Step 1: 写失败的脚本测试

- [ ] 使用临时目录和 monkeypatch 输入验证：
  - 仅 `http_test`/`provider_preview` 可运行；
  - 数据库和上传目录必须位于源码外；
  - 空数据库成功创建一个普通账号；
  - 已有任意账号时拒绝，重复执行拒绝；
  - 输入 username 必须等于环境中允许的标识；
  - 创建后不存在活跃 refresh session；
  - stdout/stderr/返回对象不含明文密码、hash、token 或允许的用户名；
  - CLI 拒绝 `--password`、环境变量密码和管道明文参数。
- [ ] 运行：

```powershell
python -m pytest tests/test_provision_http_test_account.py -q
```

Expected: 脚本不存在，测试失败。

### Step 2: 实现交互式初始化

- [ ] 复用数据库 migration 与现有 AuthenticationService 密码哈希，不复制密码算法。
- [ ] 创建成功后立即撤销注册流程产生的 session。
- [ ] 输出只包含脱敏状态、用户 UID 的短摘要和数据库路径是否通过外部路径校验；不输出登录标识。
- [ ] 发生任何异常时事务回滚，不留下半初始化账号。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
python -m pytest tests/test_provision_http_test_account.py tests/test_users_services.py -q
git diff --check
```

- [ ] 提交：

```powershell
git add scripts/provision-http-test-account.py tests/test_provision_http_test_account.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: add secret-safe test account provisioning"
```

---

## Task 8: 创建完全隔离的 HTTP 测试部署覆盖层

**Files:**

- Create: `deploy/http-test/env.example`
- Create: `deploy/http-test/provider-preview.env.example`
- Create: `deploy/http-test/nginx/ai-nav.conf`
- Create: `deploy/http-test/systemd/starchart-ai-http-test.service`
- Create: `deploy/http-test/systemd/starchart-ai-provider-preview.service`
- Create: `deploy/http-test/project-hub/index.html`
- Create: `deploy/http-test/project-hub/assets/styles.css`
- Create: `deploy/http-test/scripts/install-overlay.sh`
- Create: `deploy/http-test/scripts/preflight.sh`
- Create: `deploy/http-test/scripts/smoke-test.sh`
- Create: `tests/test_http_test_overlay.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Required route contract:**

| Public path | Upstream/source | Required behavior |
| --- | --- | --- |
| `/` | project hub static | 显示新旧项目入口 |
| `/old-ai-nav/` | `/opt/ai-nav2` | 保留旧站 |
| `/chat` | `127.0.0.1:8000` | 保留旧聊天 |
| `/health` | `127.0.0.1:8000` | 保留旧健康检查 |
| `/chat-widget.js` | `/opt/ai-nav2` | 保留旧挂件 |
| `/StarChart-AI/` | `127.0.0.1:8001` | 剥离前缀后代理新项目 |
| `/StarChart-AI/api/v1/agent/guest/chat` | `127.0.0.1:8001` | 独立低速率限流 |

### Step 1: 写失败的静态部署验证

- [ ] `tests/test_http_test_overlay.py` 解析模板并验证：
  - upstream 仅为 loopback；
  - 公网没有 8002 location；
  - `/StarChart-AI` 与 `/old-ai-nav` 都规范化到尾斜杠；
  - `proxy_pass` 正确剥离 `/StarChart-AI/`；
  - guest route 有独立 `limit_req_zone`、小 burst、请求体上限和超时；
  - 旧 `/chat`、`/health`、`/chat-widget.js` 的优先级高于静态 fallback；
  - systemd 使用两个不同的 EnvironmentFile、数据库目录、上传目录、端口；
  - public 单元 deterministic/live off，preview 单元 loopback；
  - env 模板的 secret、username、password、API key 均为空；
  - 安装脚本先备份和 `nginx -t`，失败不 reload；
  - 不包含真实 IP、账号、密钥或本机路径。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_overlay.py -q
```

Expected: 文件不存在，测试失败。

### Step 2: 实现覆盖层

- [ ] Nginx 模板使用具名 upstream、规范 proxy headers、`X-Forwarded-Prefix /StarChart-AI`、合理 body/timeouts；guest 限流建议起点为 `10r/m`、`burst=5 nodelay`，最终值记录在运行手册。
- [ ] 项目选择页只包含相对链接，无追踪脚本、无内联秘密；旧项目与 StarChart-AI 两张明确卡片。
- [ ] systemd 使用专用非 root 用户、`NoNewPrivileges=true`、`PrivateTmp=true`、只写各自数据目录；preview 单元不设为默认自动启动。
- [ ] `install-overlay.sh` 不生成秘密；只安装已提供模板，创建目录并输出后续人工配置步骤。
- [ ] `preflight.sh` 只读检查端口、目录权限、配置文件权限、数据库隔离和 Nginx 语法。
- [ ] `smoke-test.sh` 只调用本机/public deterministic 路径，不调用 Provider，不创建账号。

### Step 3: 本地语法验证与提交

- [ ] 在可用 Linux/Nginx 环境运行 `nginx -t -c <staged-config>`；Windows 缺少 Nginx 时只记录为 `NOT RUN`，不得伪造。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_overlay.py -q
git diff --check
```

- [ ] 提交：

```powershell
git add deploy/http-test tests/test_http_test_overlay.py docs/00-index/http-test-deployment-file-index.md
git commit -m "feat: add isolated HTTP test deployment overlay"
```

---

## Task 9: 将覆盖层纳入发布包且保持秘密排除

**Files:**

- Modify: `scripts/build-release-package.ps1`
- Create: `tests/test_release_http_test_overlay.py`
- Modify: `tests/test_http_test_overlay.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

### Step 1: 写失败的发布包测试

- [ ] 验证 `deploy/http-test` 被 allowlist 纳入。
- [ ] 验证任何 `.env`、`.sqlite3`、上传内容、备份、日志、真实 systemd EnvironmentFile 和 Provider 响应证据都会令构建失败。
- [ ] 验证只有 `*.env.example` 可进入包。
- [ ] 构建临时 zip 后枚举成员，确认不包含 `.tmp_ci.txt`、`.tmp_push_ci.txt`、`.git`、测试结果或本地绝对路径。
- [ ] 运行：

```powershell
python -m pytest tests/test_release_http_test_overlay.py tests/test_http_test_overlay.py -q
```

Expected: 覆盖层尚不在 allowlist，测试失败。

### Step 2: 最小修改发布脚本

- [ ] 将 `deploy/http-test` 加入允许根目录。
- [ ] 保留 deny-first 规则；`.env.example` 通过显式后缀例外进入，普通 `.env` 继续拒绝。
- [ ] `-ValidateOnly` 输出增加 `deploymentOverlayCount`，不输出文件内容。

### Step 3: 回归并提交

- [ ] 运行：

```powershell
python -m pytest tests/test_release_http_test_overlay.py tests/test_http_test_overlay.py -q
powershell -ExecutionPolicy Bypass -File scripts/build-release-package.ps1 -ValidateOnly
git diff --check
```

- [ ] 提交：

```powershell
git add scripts/build-release-package.ps1 tests/test_release_http_test_overlay.py tests/test_http_test_overlay.py docs/00-index/http-test-deployment-file-index.md
git commit -m "build: package HTTP test deployment overlay safely"
```

---

## Task 10: 建立专项门禁和无秘密机器证据

**Files:**

- Create: `scripts/verify-http-test-deployment.ps1`
- Create: `scripts/build-http-test-deployment-manifest.py`
- Create: `scripts/check-no-secrets.py`
- Create: `docs/06-evidence/platform/http-test-deployment-manifest.json`
- Modify: `scripts/verify-foundation.ps1`
- Modify: `../.github/workflows/ai-nav-foundation-ci.yml`
- Create: `tests/test_http_test_manifest.py`
- Create: `tests/test_no_secrets.py`
- Modify: `docs/00-index/http-test-deployment-file-index.md`

**Manifest contract:**

```json
{
  "schemaVersion": 1,
  "generatedAt": "<UTC ISO-8601>",
  "sourceCommit": "<git sha or WORKTREE>",
  "checks": [
    {"name": "runtime", "passed": true, "count": 0},
    {"name": "policy", "passed": true, "count": 0},
    {"name": "agentHistory", "passed": true, "count": 0},
    {"name": "guestAgent", "passed": true, "count": 0},
    {"name": "frontend", "passed": true, "count": 0},
    {"name": "overlay", "passed": true, "count": 0},
    {"name": "release", "passed": true, "count": 0}
  ],
  "externalValidation": {
    "serverDeployment": "not_run",
    "providerPreview": "not_run",
    "https": "not_run",
    "backupRestore": "not_run",
    "rollback": "not_run"
  },
  "containsSecrets": false
}
```

### Step 1: 写失败的 manifest 与门禁测试

- [ ] 验证 manifest schema、固定 check 名称、真实计数非负、external 状态枚举、无账号/API key/绝对路径。
- [ ] 验证构建器只接受本次测试进程产生的结构化结果文件，不从历史文档数字推断。
- [ ] 验证任何失败 check 都让脚本非 0，且不覆盖上一份通过证据。
- [ ] `tests/test_no_secrets.py` 验证扫描器：
  - 支持文件和目录参数；
  - 检测私钥头、Bearer/Cookie 值、常见 Provider key 形状、非空敏感环境变量赋值；
  - 允许 `*.env.example` 中的空赋值和测试专用占位值；
  - 输出只包含文件、行号和规则名，不回显匹配值；
  - 二进制、数据库、上传和超大文件直接按禁止类型报告。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_manifest.py tests/test_no_secrets.py -q
```

Expected: 构建器和证据不存在，测试失败。

### Step 2: 实现专项门禁

- [ ] `verify-http-test-deployment.ps1` 顺序运行 Tasks 1–9 的 Python/Node 测试和 release validate，捕获每组真实计数到临时结构化文件。
- [ ] 所有检查成功后才原子替换 manifest；生成器只写计数、状态、commit，不写 stdout 原文。
- [ ] `check-no-secrets.py` 采用规则名与脱敏位置报告，供本地、CI、文档和 release 包统一调用；规则夹具只使用明确标记为测试数据的合成值。
- [ ] 把专项门禁加入 `verify-foundation.ps1` 和 foundation CI；保持 quality/agent/users job 的现有拆分。
- [ ] CI 不注入测试账号密码或 Provider key，所有测试使用临时夹具。

### Step 3: 运行并提交

- [ ] 运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-http-test-deployment.ps1
python -m pytest tests/test_http_test_manifest.py tests/test_no_secrets.py -q
git diff --check
```

Expected: 退出码 0；manifest 数字来自本次运行，external 项仍为 `not_run`。

- [ ] 提交：

```powershell
git add scripts/verify-http-test-deployment.ps1 scripts/build-http-test-deployment-manifest.py scripts/check-no-secrets.py docs/06-evidence/platform/http-test-deployment-manifest.json scripts/verify-foundation.ps1 ../.github/workflows/ai-nav-foundation-ci.yml tests/test_http_test_manifest.py tests/test_no_secrets.py docs/00-index/http-test-deployment-file-index.md
git commit -m "test: gate HTTP test deployment profile"
```

---

## Task 11: 编写可执行运行手册并同步文档治理

**Files:**

- Create: `docs/04-operations/deployment/http-test-deployment-runbook.md`
- Modify: `docs/02-architecture/deployment/http-subpath-test-deployment-design.md`
- Modify: `docs/00-index/http-test-deployment-file-index.md`
- Modify: `docs/00-index/documentation-map.md`
- Modify: `README.md`

### Step 1: 写运行手册内容检查

- [ ] 在 `tests/test_http_test_overlay.py` 增加文档契约断言：
  - 含备份、预检、安装、初始化测试账号、启动 8001、Nginx reload、smoke、8002 手工预览、停止、回滚。
  - 每个服务器命令明确执行身份和工作目录。
  - 明确不把真实 secret、账号或 API key 写进 shell history；建议使用权限为 600 的 EnvironmentFile 和交互式编辑。
  - 明确公网 HTTP 风险、测试数据可被窃听、禁止真实隐私数据。
  - 明确登录不自动导入游客历史。
  - HTTP 测试候选与生产发布分别给结论，生产继续 `NO-GO`。
- [ ] 运行：

```powershell
python -m pytest tests/test_http_test_overlay.py -q
```

Expected: 运行手册不存在，测试失败。

### Step 2: 编写并交叉链接

- [ ] 运行手册只引用模板变量名和服务器目标路径，不写实际值。
- [ ] 设计文档增加“实施对应表”，链接 Tasks 1–10 的实际文件。
- [ ] 文件索引从“候选”改为实际状态表，但只把真实已执行验证标为通过。
- [ ] 文档地图加入实施计划、运行手册和机器证据入口。
- [ ] README 只增加部署文档入口，不复制完整部署命令。

### Step 3: 文档自检并提交

- [ ] 运行：

```powershell
python scripts/check-content-links.py
python scripts/check-no-secrets.py --paths docs deploy README.md
git diff --check
```

Expected: 链接检查成功；秘密扫描仅允许模板中的空变量名，不得命中用户提供的凭据值。

- [ ] 提交：

```powershell
git add docs/04-operations/deployment/http-test-deployment-runbook.md docs/02-architecture/deployment/http-subpath-test-deployment-design.md docs/00-index/http-test-deployment-file-index.md docs/00-index/documentation-map.md README.md
git commit -m "docs: add HTTP test deployment runbook"
```

---

## Task 12: 执行全量本地复验并形成候选结论

**Files:**

- Modify only if facts changed: `docs/00-index/http-test-deployment-file-index.md`
- Modify only through generator: `docs/06-evidence/platform/http-test-deployment-manifest.json`

### Step 1: 干净地运行全部门禁

- [ ] 在运行前记录 `git status --short`，确认不触碰用户未跟踪文件。
- [ ] 顺序运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify-http-test-deployment.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify-users.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify-agent.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify-frontend.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify-quality.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify-foundation.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-release-package.ps1 -ValidateOnly
git diff --check
```

- [ ] 每条命令记录本次真实退出码、测试数、耗时和生成证据 SHA-256；不得复用历史 CI 数字。

### Step 2: 负向秘密和数据边界复验

- [ ] 扫描 tracked diff、release 成员和 manifest，确认无真实凭据、数据库、上传内容和绝对本机路径。
- [ ] 再运行游客路径的数据库 spy 测试、测试账号全部受限动作、跨用户 session 历史隔离、Provider 不调用测试。
- [ ] 把所有未执行的 Linux Nginx、systemd、服务器、Provider、备份恢复、回滚保持为 `NOT RUN`/`NO-GO`。

### Step 3: 独立审阅并提交证据

- [ ] 按设计逐条核对 URL、账号能力、游客记忆、Provider 预览、数据目录、回滚；发现事实错误只做最小修复并重跑受影响门禁。
- [ ] 更新索引：
  - `本地整改候选`: 仅在全部本地门禁与负向测试通过时可为 `GO`。
  - `HTTP 服务器部署`: 在 Task 13 前保持 `NO-GO`。
  - `生产发布`: 始终 `NO-GO`，直到 HTTPS、外部签收、容量、备份恢复和回滚有真实证据。
- [ ] 提交：

```powershell
git add docs/00-index/http-test-deployment-file-index.md docs/06-evidence/platform/http-test-deployment-manifest.json
git commit -m "test: record HTTP test deployment verification"
```

---

## Task 13: 人工授权后的服务器部署与回滚演练

**Files:**

- Server only after explicit user authorization; no local source file changes unless factual gaps are found.
- Modify after real execution: `docs/00-index/http-test-deployment-file-index.md`
- Generate after redaction: `docs/06-evidence/platform/http-test-server-validation.json`

### Step 1: 停在人工检查点

- [ ] 在进行任何 SSH、Nginx reload、systemd install/start、数据库创建或真实 Provider 操作前，向用户展示：
  - 目标主机和部署版本 commit；
  - 将新增/修改的服务器路径；
  - 旧站备份路径；
  - 8000/8001/8002 端口计划；
  - 回滚命令；
  - 哪些动作会改变外部状态。
- [ ] 获得用户对服务器变更的明确授权；本地计划批准不等于服务器执行授权。

### Step 2: 只部署 deterministic 公网实例

- [ ] 按运行手册执行只读预检、备份当前 Nginx 配置和旧站目录。
- [ ] 安装 release、覆盖层、空 EnvironmentFile；由用户在服务器安全输入 secret 和允许账号标识。
- [ ] 交互式初始化唯一测试账号；不得在聊天或命令参数中传递密码。
- [ ] 启动 8001，验证 loopback health，再 `nginx -t`，成功后才 reload。
- [ ] 验证公网 `/`、旧站、旧 chat/health/widget、新站静态、API、头像、游客助手、测试账号允许/禁止能力。
- [ ] 记录脱敏状态码、延迟、版本、哈希；不记录消息正文、账号或 token。

### Step 3: 独立验证 8002 Provider 预览

- [ ] 仅在用户再次明确授权真实 Provider 调用后：
  - 由用户在服务器权限 600 的 preview EnvironmentFile 写入 API key；
  - 初始化独立 preview 数据库与测试账号；
  - 手工启动 8002；
  - 确认 `ss` 仅监听 `127.0.0.1:8002`；
  - 建立 SSH 隧道并进行一条有成本上限的人工请求；
  - 记录脱敏 provider/model/成本/延迟状态，不记录提示或回答正文；
  - 停止 8002 并再次确认端口关闭。
- [ ] Provider 未授权或未调用时状态保持 `NOT RUN`，不影响 8001 deterministic 候选，但不能声称真实 Agent 已验证。

### Step 4: 回滚演练和结论

- [ ] 在用户允许的维护窗口执行一次覆盖层回滚演练：恢复 Nginx 备份、停止 8001/8002、验证旧 `/`、`/chat`、`/health`，然后按批准方式恢复测试部署。
- [ ] 若未实际回滚，记录 `NOT RUN`，不要从脚本存在推断通过。
- [ ] 服务器验证文件必须由脱敏生成器写入并通过 schema/秘密扫描后才能提交。
- [ ] 最终结论分开：
  - `本地整改候选`
  - `HTTP 测试部署`
  - `真实 Provider 预览`
  - `生产发布`
- [ ] 即使 HTTP 测试部署通过，生产发布仍保持 `NO-GO`，直到 HTTPS、合规、容量、备份恢复、回滚和外部签收全部获得真实证据。

---

## Final implementation self-review checklist

- [ ] 所有设计章节都有至少一个实现任务和一个验证点。
- [ ] 没有未决标记、延后处理语句或未定义的接口占位符。
- [ ] 所有新增函数签名、endpoint、环境变量、文件路径和错误码在任务间一致。
- [ ] 游客与登录会话只共享纯 Agent 编排，不共享身份、session 或持久化入口。
- [ ] 登录切换不会自动导入游客历史。
- [ ] 头像数据库值不含 `/StarChart-AI`。
- [ ] 公网配置中不存在 8002 或 live Provider。
- [ ] `production` 验证没有被 `http_test` 特例旁路。
- [ ] 任何真实凭据只通过服务器端受限交互注入。
- [ ] 发布包、文档、manifest 和日志均通过秘密扫描。
- [ ] 本地、HTTP 测试、Provider 预览和生产四种结论独立记录。

## Execution handoff

计划完成后有两种执行方式：

1. **Subagent-Driven（推荐）**：在当前任务中按 Task 1–13 逐项分派实现，每项完成后做规格审查和质量审查，再进入下一项。
2. **Inline Execution**：由当前 agent 在本工作区按任务顺序串行执行，每完成一至两个任务同步一次真实结果。

两种方式都必须从 Task 1 开始，严格执行 TDD、文件索引同步、秘密约束和 Task 13 的外部变更人工检查点。
