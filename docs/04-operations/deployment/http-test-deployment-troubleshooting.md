# HTTP 测试部署故障排查手册

> 用途：复用本次 `/StarChart-AI/` HTTP 测试部署中实际遇到的故障、根因和验证方法。
> 状态：2026-07-28 实机部署复盘；配合运行手册使用，不替代生产发布清单。
> 安全边界：不记录主机地址、账号标识、密码、Token、Cookie、真实 `.env`、Provider 请求或回答正文。
> 相关入口：`docs/04-operations/deployment/http-test-deployment-runbook.md`、`docs/06-evidence/platform/http-test-server-validation.json`。

## 1. 使用方法

先在下表按现象定位，再阅读对应章节。每次只验证一个边界，不要在未知根因时同时修改 Nginx、systemd、数据库和应用代码。

| 现象 | 优先检查 | 章节 |
| --- | --- | ---: |
| SSH 输入密码时没有任何显示 | SSH 密码输入规则 | 2.1 |
| 输入密码后立即 `Connection closed` 或退出码 255 | SSH 身份、授权密钥和服务端日志 | 2.2 |
| 交互窗口一闪而过 | 启动器是否保留退出码和暂停提示 | 2.3 |
| Linux 脚本出现 `pipefail\r` 或解释器路径异常 | 发布包中的 CRLF | 3.1 |
| 服务器没有 `unzip` | 使用已有 Python 解压 | 3.2 |
| 本机 `.venv` 存在但 Python 无法启动 | `pyvenv.cfg` 指向失效解释器 | 4.1 |
| 依赖下载长期无进展 | 源可达性、锁文件与隔离运行时 | 4.2 |
| 应用启动时报 runtime state backend 未实现 | 部署档使用了未实现配置值 | 4.3 |
| `systemctl is-active` 为 active，但健康请求拒绝连接 | 服务尚未完成监听 | 5.1 |
| systemd 服务能运行，手工命令却读不到环境或数据库 | 执行身份、工作目录和环境加载不同 | 5.2 |
| 子路径首页正常，静态资源或 API 404 | 公共前缀投影或 Nginx 前缀剥离 | 6.1 |
| 精确旧站小组件路由 404 | `alias` 与 `try_files` 组合 | 6.2 |
| 新部署破坏旧 `/chat`、`/health` 或小组件 | 旧站精确兼容路由缺失 | 6.3 |
| Agent 测试报 `no such table` | 运行了错误数据库或未初始化迁移 | 7.1 |
| 数据库存在但独立命令打不开 | 目录遍历、文件权限或身份不一致 | 7.2 |
| 登录后 Agent sessions 显示关闭 | 部署环境未启用会话能力 | 8.1 |
| 创建 Agent 会话返回 500 | 已存在未开始会话且异常未映射 | 8.2 |
| 验证显示通过，但脱敏报告复制失败 | Windows 中文绝对路径传给 SCP | 9.1 |
| 验证进程退出码 0，但业务状态是 failed | 把“报告已生成”误当成“验证通过” | 9.2 |
| 验证耗时不断扩大 | 没有按改动范围选择门禁 | 10 |

## 2. SSH 与交互终端

### 2.1 密码输入没有字符或星号

**现象**

SSH、`sudo`、Python `getpass` 提示输入密码时，键盘输入没有任何回显。

**根因**

这是终端的标准安全行为，不是键盘失效。终端同时隐藏字符和星号，避免旁观者推断密码长度。

**推荐处理**

1. 保持终端焦点；
2. 正常输入密码；
3. 按 Enter 提交；
4. 不把密码复制到命令参数、环境变量、聊天或日志。

**验证**

成功后应出现下一条非敏感状态；失败时只记录退出码和错误类型，不截图密码输入过程。

**避免误判**

不要因为“没有显示”而重复粘贴密码。重复输入会把多次内容合并成一个错误密码。

### 2.2 输入密码后立即关闭连接

**现象**

终端显示 `Connection closed`，或 SSH key 安装脚本返回 255。

**根因**

常见原因是密码认证未成功、目标用户不允许该认证方式、授权密钥未安装到正确 home，或 `.ssh` 权限不符合 OpenSSH 要求。客户端窗口自动关闭会掩盖真正的 SSH 错误。

**推荐处理**

先通过云控制台或已有可信管理通道，在目标用户 home 安装公钥：

```bash
install -d -m 0700 "${TARGET_HOME}/.ssh"
printf '%s\n' 'REPLACE_WITH_APPROVED_PUBLIC_KEY' >> "${TARGET_HOME}/.ssh/authorized_keys"
chown -R "${TARGET_USER}:${TARGET_GROUP}" "${TARGET_HOME}/.ssh"
chmod 0600 "${TARGET_HOME}/.ssh/authorized_keys"
```

随后从本机验证非交互密钥认证：

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 TARGET_USER@TARGET_HOST "id"
```

**验证**

- 退出码为 0；
- 服务端 `id` 是获批用户；
- 后续不再要求传递服务器密码。

**避免误判**

`Connection closed` 只说明会话结束，不能单独证明密钥安装失败。必须同时检查客户端退出码和服务端授权文件权限。

### 2.3 交互窗口执行后自动关闭

**现象**

脚本输出了一些服务状态，窗口随即关闭，无法确认最终结论。

**根因**

GUI 启动器在子进程结束后直接关闭窗口，或者脚本只返回进程退出码，没有输出业务验证状态。

**推荐处理**

交互启动器末尾保留：

```powershell
Write-Host "Process exit code: $LASTEXITCODE"
Read-Host "Press Enter to close"
```

对业务验证同时打印 `validationStatus`、总数、通过数和失败数。密码继续使用隐藏输入。

**验证**

窗口在最终摘要后保持打开，直到人工按 Enter；摘要不包含凭据、请求体或响应体。

## 3. 发布包与 Linux 文件格式

### 3.1 PowerShell 生成的 Shell 脚本带 CRLF

**现象**

Linux 执行部署脚本时报 `pipefail\r`、`bad interpreter` 或看似正确的命令无法识别。

**根因**

Windows 工作树中的 `.sh` 使用 CRLF，ZIP 保留了回车字符。

**推荐处理**

在发布包暂存阶段统一把 `.sh` 转成 LF，而不是在服务器逐个修：

```powershell
$content = Get-Content -LiteralPath $scriptPath -Raw
$content = $content -replace "`r`n", "`n"
[IO.File]::WriteAllText($scriptPath, $content, [Text.UTF8Encoding]::new($false))
```

仓库继续使用 `.gitattributes` 约束：

```text
*.sh text eol=lf
```

**验证**

```bash
bash -n deploy/http-test/scripts/preflight.sh
bash -n deploy/http-test/scripts/install-overlay.sh
bash -n deploy/http-test/scripts/smoke-test.sh
```

发布测试还应直接检查 ZIP 内所有 `.sh` 不含 `\r\n`。

### 3.2 服务器没有 `unzip`

**现象**

发布包哈希正确，但安装阶段提示 `unzip: command not found`。

**根因**

最小化服务器镜像没有安装 unzip。

**推荐处理**

如果已存在受控 Python 运行时，无需临时增加系统包：

```bash
python -m zipfile -e RELEASE_ARCHIVE RELEASE_ROOT
```

解压到新的不可变 release 目录，再切换 `current` 符号链接。不要覆盖当前 release。

**验证**

```bash
test -f "${RELEASE_ROOT}/backend/run.py"
readlink -f /opt/starchart-ai/current
```

### 3.3 发布包哈希与目标提交

**推荐处理**

本地和服务器分别计算 SHA-256，两个值必须完全一致：

```powershell
Get-FileHash -Algorithm SHA256 RELEASE_ARCHIVE
```

```bash
sha256sum RELEASE_ARCHIVE
```

**避免误判**

文件名包含短提交号不等于发布内容来自该提交。证据应同时记录完整提交、归档 SHA-256 和当前 release 解析路径。

## 4. Python 与依赖

### 4.1 `.venv` 存在但解释器已经失效

**现象**

`.venv/Scripts/python.exe` 存在，但启动时报找不到旧的系统 Python；`pyvenv.cfg` 指向已卸载路径。

**根因**

Windows venv 启动器依赖创建它的基础解释器。移动或卸载基础 Python 后，仅保留 `.venv` 目录不能保证可用。

**推荐处理**

1. 读取 `.venv/pyvenv.cfg`；
2. 验证 `executable` 真实存在且能执行 `import sys`；
3. 不要把其他 Python 的 site-packages 强行混入损坏 venv；
4. 使用锁定版本的独立 Python 重建 venv。

验证脚本应允许显式解释器，并拒绝混用另一 venv 的 site-packages。

**避免误判**

`Test-Path .venv/Scripts/python.exe` 通过不代表解释器可用。必须实际运行：

```powershell
& $python -c "import sys; print(sys.version)"
```

### 4.2 依赖下载长时间停滞

**现象**

官方包索引或 CDN 长时间无进展，部署看似卡死。

**根因**

服务器出口到包源不稳定，不是应用测试超时。

**推荐处理**

- 使用锁文件；
- 保持 Python 安装和项目依赖在 `/opt/starchart-ai/` 隔离；
- 只使用运维方批准的 HTTPS 镜像；
- 安装后运行依赖一致性检查；
- 不修改系统 Python。

**验证**

```bash
/opt/starchart-ai/venv/bin/python --version
/opt/starchart-ai/venv/bin/python -m pip check
```

如果使用的工具不提供 `pip` 模块，使用该工具对应的依赖检查命令；不要把命令不存在误记为依赖冲突。

### 4.3 runtime state backend 配置值未实现

**现象**

应用导入配置时抛出 `AI_NAV_AGENT_RUNTIME_STATE_BACKEND is not implemented`。

**根因**

部署环境模板写入了设计名称，但当前代码只实现了另一枚举值。

**推荐处理**

以 `backend/app/core/config.py` 的启动期校验为权威，环境模板只能使用当前已实现值。修改模板后增加回归测试，保证两个 HTTP 测试模板一致。

**验证**

在完全合成且禁用 dotenv 的环境中导入配置；随后检查公开 runtime 端点只暴露能力布尔值，不暴露内部 backend。

## 5. systemd 启动与执行身份

### 5.1 active 不等于端口已就绪

**现象**

`systemctl is-active` 返回 `active`，紧接着的 curl 得到 connection refused。

**根因**

systemd 已启动进程，但 ASGI 应用仍在导入、迁移或绑定端口。

**推荐处理**

使用有上限的条件轮询，不增加一个很大的固定 sleep：

```bash
for attempt in {1..20}; do
  if curl --fail --silent --max-time 3 \
    http://127.0.0.1:8001/api/v1/health >/dev/null; then
    echo "ready"
    break
  fi
  sleep 1
done
```

超时后再读取本次服务日志：

```bash
systemctl status starchart-ai-http-test.service --no-pager
journalctl -u starchart-ai-http-test.service -n 80 --no-pager
```

**避免误判**

第一次 curl 失败不能直接判定部署失败；轮询结束仍失败才进入日志诊断。

### 5.2 systemd 成功，手工命令失败

**现象**

运行中的服务可以访问数据库，但管理员手工执行 Python 脚本时报配置或数据库错误。

**根因**

systemd 单元提供了固定 User、Group、WorkingDirectory、EnvironmentFile 和 ReadWritePaths；手工 shell 没有相同上下文。

**推荐处理**

诊断时分别检查：

```bash
systemctl show starchart-ai-http-test.service \
  -p User -p Group -p ProtectSystem -p ReadWritePaths --no-pager
namei -l /srv/starchart-ai-http-test/data/ai_nav.sqlite3
```

需要读取数据库时，以专用服务账号运行固定只读脚本。不要为了让管理员命令方便而放宽数据库权限。

## 6. Nginx 子路径与旧站兼容

### 6.1 子路径页面正常但资源或 API 404

**根因**

浏览器公共路径、Nginx 前缀剥离、`X-Forwarded-Prefix` 和应用内部路由没有形成同一契约。

**推荐处理**

- 浏览器只在显示边界加 `/StarChart-AI`；
- Nginx 转发 API 时剥离公共前缀；
- 应用内部继续使用 `/api/v1` 和 `/uploads`；
- 数据库不保存公共部署前缀；
- 拒绝绝对 URL、双前缀和路径遍历。

**验证**

分别检查首页、一个静态资源、健康 API、runtime API 和头像 URL。首页 200 不能替代其余四项。

### 6.2 `alias` 与 `try_files` 导致精确文件 404

**现象**

旧站首页正常，精确 `/chat-widget.js` 路由返回 404。

**根因**

精确 location 已用 `alias` 指向文件，又叠加不适配该上下文的 `try_files`，导致 Nginx 重新解析错误路径。

**推荐处理**

精确单文件 alias 保持最小配置：

```nginx
location = /chat-widget.js {
    alias /REPLACE_WITH_LEGACY_ROOT/chat-widget.js;
}
```

先执行 `nginx -t`，再 reload。为覆盖层配置增加结构回归测试。

### 6.3 新入口破坏旧站兼容

**推荐处理**

项目选择页使用根 `/`，旧站使用 `/old-ai-nav/`；旧 `/chat`、`/health` 和 `/chat-widget.js` 使用精确兼容路由，且定义在根静态 fallback 之前。

**验证**

```text
/
/old-ai-nav/
/chat
/health
/chat-widget.js
/StarChart-AI/
/StarChart-AI/api/v1/health
```

逐项记录状态码和耗时，不只检查浏览器首页。

## 7. SQLite 与唯一测试账号

### 7.1 `no such table`

**现象**

Agent 或 Tools 测试报 `sqlite3.OperationalError: no such table`。

**根因**

命令指向了未初始化或错误的数据库文件，而不是运行服务使用的隔离数据库。数据库文件存在不代表 schema 已应用。

**推荐处理**

- 测试使用一次性数据库并先执行 schema、seed 和全部迁移；
- 服务器账号初始化器只允许空账号库；
- 手工诊断不要依赖当前目录中的默认数据库名；
- 不用复制生产或旧站数据库来“快速修复”。

**验证**

检查迁移表、目标业务表和外键；服务器只读复核账号数量必须为 1，但不输出账号标识。

### 7.2 数据库权限与目录遍历

**推荐边界**

```text
/srv/starchart-ai-http-test/data/        0700 dedicated-service-account
ai_nav.sqlite3                           0600 dedicated-service-account
```

使用 `namei -l` 检查逐级目录权限，使用 `stat` 检查文件元数据。不要通过 `chmod 777` 解决打不开数据库的问题。

**避免误判**

备份、HTTP 测试、Provider 预览和旧站数据库必须是不同路径。账号数量正确不能证明数据库隔离，路径和服务身份也必须核对。

## 8. Agent 会话

### 8.1 登录会话能力没有启用

**现象**

登录、资料和工作流正常，但公开 runtime 显示 `authenticatedSessions=false`。

**根因**

HTTP 测试 EnvironmentFile 遗漏 `AI_NAV_AGENT_SESSIONS_ENABLED=1`，或模板和实际服务器配置不一致。

**推荐处理**

同步修改两个受控模板并增加模板回归；服务器 EnvironmentFile 通过 root 交互更新，保持原权限，然后重启 8001。

**验证**

公开 runtime 只应显示：

```json
{
  "agent": {
    "guestChat": true,
    "authenticatedSessions": true
  }
}
```

还必须实际执行登录用户的 list/create/chat 流，不能只相信能力布尔值。

### 8.2 已存在空会话时创建返回 500

**现象**

第一次验证留下了未开始会话；再次 POST 创建会话时服务层拒绝重复空会话，但 HTTP 返回 500。

**根因**

数据层“每个用户只保留一个未开始会话”的约束正确，创建路由漏掉了 `AgentSessionError` 到 HTTP 错误的映射。

**推荐处理**

- 保留单空会话约束；
- 路由把 `AGENT_SESSION_UNSTARTED_EXISTS` 映射为 409；
- 前端收到 409 后刷新列表并恢复现有空会话；
- 验证脚本先 list，再复用 `messageCount == 0` 的会话，不能每次盲目 create。

**验证**

1. 首次创建返回 201；
2. 未问答前再次创建返回受控 409；
3. 列表仍只有一个空会话；
4. 在该会话完成问答后允许创建新会话。

**避免误判**

不要删除数据库或放宽唯一约束来消除 409。409 是预期业务状态，500 才是路由缺口。

## 9. Windows、SCP 与脱敏报告

### 9.1 中文绝对路径导致 SCP 本地目标解析失败

**现象**

服务器验证 24/24 通过，但 SCP 报本地目标 `No such file or directory`，路径中出现八进制转义。

**根因**

Windows PowerShell、OpenSSH SCP 与含中文的绝对路径在参数转义上不一致。

**推荐处理**

先把 PowerShell 工作目录切到仓库根，再使用相对本地目标：

```powershell
Set-Location REPOSITORY_ROOT
scp TARGET_USER@TARGET_HOST:/tmp/redacted-validation.json `
  release/http-test-auth-validation.json
```

如果仍失败，先复制到纯 ASCII 临时目录，再用 PowerShell `Move-Item -LiteralPath` 移入工作区。

**验证**

比较服务器报告与本地报告 SHA-256；只读取脱敏 JSON，不读取服务器 EnvironmentFile。

### 9.2 进程退出码与业务验证状态

**现象**

脚本显示 `Validation process exit code: 0`，但报告中的 `validationStatus` 是 `failed`。

**根因**

退出码 0 只表示验证器成功写出了脱敏报告；业务检查可能包含失败项。

**推荐处理**

发布判断必须同时满足：

```text
process exit code == 0
validationStatus == passed
checksRecorded == passedChecks
failedChecks == 0
sensitiveDataRecorded == false
```

服务器证据必须由严格生成器读取脱敏报告；额外字段、计数不一致或失败检查应拒绝生成。

## 10. 控制验证时长

验证按改动风险分层，不要把增加 timeout 当成默认解决方案。

### 10.1 快速故障定位

只运行一个复现：

- Nginx：`nginx -t` 加单路由 curl；
- systemd：健康轮询加最近 80 行日志；
- Agent session：一个路由回归；
- SCP：复制一份脱敏小 JSON；
- 发布包：哈希和一个成员检查。

### 10.2 修复后的关键门禁

本次会话路由修复对应：

- HTTP 测试策略；
- Agent 会话专项；
- 前端身份/游客/Agent/公共前缀关键流；
- 发布 allowlist；
- 秘密扫描；
- 服务器 smoke 和交互式全功能流。

### 10.3 何时运行全量门禁

以下情况才重新运行完整质量套件：

- 修改共享认证、数据库迁移、依赖锁、全局配置或发布选择；
- 多个领域同时变化；
- 准备合并或正式发布；
- 关键专项暴露跨域回归。

仅修改文档时运行秘密扫描、JSON/路径检查和 `git diff --check`。不能用历史全量数字冒充本次运行，但也不应重复运行与改动无关的长套件。

## 11. 备份、回滚和 Provider 的结论边界

### 11.1 备份存在不等于恢复通过

`tar` 成功且 `gzip -t` 通过只证明归档存在且压缩流完整。只有真实恢复到隔离目标并验证应用/数据后，才能把 `backupRestore` 从 `NOT RUN` 改为通过。

### 11.2 有上一 release 不等于回滚通过

保留上一不可变 release 和 Nginx 备份只是具备回滚材料。未实际切回、验证旧站并恢复测试部署时，`rollbackExercise` 必须保持 `NOT RUN`。

### 11.3 deterministic Agent 不等于真实 Provider

公网 8001 使用 deterministic 模式。8002 保持 loopback 且关闭；没有明确的费用与真实 Provider 授权时，不写 API Key、不启动 8002、不发请求，也不声称真实 Agent 已验证。

### 11.4 HTTP 测试 GO 不等于生产 GO

HTTP 可被窃听或篡改，只能使用虚构数据。即使所有 HTTP 测试通过，HTTPS、容量、合规、恢复、回滚、告警和值守未签收时，生产发布仍为 `NO-GO`。

## 12. 推荐的排查顺序

遇到未知部署问题时按以下顺序，避免跨层猜测：

1. 确认目标 release 完整提交与归档 SHA-256；
2. 确认脚本 LF、发布成员和依赖运行时；
3. 确认 EnvironmentFile 权限和已实现配置值；
4. 确认 systemd 身份、工作目录、ReadWritePaths；
5. 等待 loopback 8001 健康；
6. 执行 `nginx -t` 后再 reload；
7. 检查旧站精确兼容路径；
8. 检查新站静态、API、头像和 runtime；
9. 运行游客流和唯一测试账号允许/禁止流；
10. 生成脱敏证据并检查业务状态；
11. 分开写 HTTP 测试、Provider 预览和生产结论；
12. 清理临时脚本与上传包，保留当前/上一 release、备份和隔离数据。
