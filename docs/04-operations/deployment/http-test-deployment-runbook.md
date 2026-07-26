# HTTP 子路径测试部署运行手册

> 用途：在不破坏旧站的前提下，部署、验证、停止和回滚 `/StarChart-AI/` HTTP 测试候选。
> 状态：本地可执行手册；服务器、Provider、HTTPS、备份恢复和回滚均未据此执行。
> 日期：2026-07-27。
> 权威性：命令以 `deploy/http-test/` 当前覆盖层为准；本手册不构成生产发布证明。

## 1. 结论与硬边界

- **本地整改候选**：只有本地专项门禁和全量门禁真实通过后才可判定 `GO`。
- **HTTP 服务器部署**：完成本手册的服务器实测前保持 `NO-GO`。
- **生产发布**：保持 `NO-GO`。HTTP 测试通过不能替代 HTTPS、合规、容量、告警、备份恢复、回滚和外部签收。
- 公网 8001 只使用 `deterministic` Provider；8002 只监听 `127.0.0.1`，不配置公网或 Nginx 入口。
- 不在命令参数、聊天、Git、日志或 shell history 中输入真实 secret、账号、密码、API Key、Cookie 或 Token。
- 两个 EnvironmentFile 均由 root 交互编辑，所有者为 root，分别归属对应服务的专用组，权限固定为 `0640`；两个服务身份不能读取对方文件。
- HTTP 流量可被窃听或篡改。只使用虚构测试数据，禁止真实姓名、联系方式、头像、对话、文件和其他隐私数据。
- 登录后不自动导入游客历史；游客浏览器数据与测试账号服务端数据保持隔离。

任何 SSH、安装、服务启动、Nginx reload、数据库创建或真实 Provider 调用，都需要用户对目标主机和目标提交的单独明确授权。

## 2. 角色、目录和占位变量

| 场景 | 执行身份 | 工作目录 |
| --- | --- | --- |
| 本地构建与检查 | 本地仓库维护者 | 仓库根目录 `ai-nav-fullstack/` |
| 文件安装、备份、Nginx、systemd | 服务器 sudo 管理员 | `/opt/starchart-ai/current` 或命令明确指定的目录 |
| 公网测试进程与账号初始化 | 专用用户 `starchart-ai-http-test` | `/opt/starchart-ai/current` |
| Provider 预览进程与账号初始化 | 专用用户 `starchart-ai-provider-preview` | `/opt/starchart-ai/current` |
| SSH 隧道 | 操作人本机账号 | 任意本机目录 |

以下变量都不是秘密，可在服务器管理员的临时 shell 中设置：

```bash
export RELEASE_SHA="REPLACE_WITH_VERIFIED_COMMIT"
export RELEASE_ARCHIVE="/path/to/verified-release.zip"
export RELEASE_ROOT="/opt/starchart-ai/releases/${RELEASE_SHA}"
export BACKUP_TAG="$(date -u +%Y%m%dT%H%M%SZ)"
```

不要用环境变量传递密码或 API Key。

## 3. 本地发布前门禁

执行身份：本地仓库维护者。工作目录：仓库根目录。

```powershell
.\scripts\verify-http-test-deployment.ps1
.\scripts\build-release-package.ps1 -ValidateOnly
python scripts/check-no-secrets.py --paths docs deploy README.md
git diff --check
```

记录本次退出码、测试计数、manifest 哈希和目标 Git 提交。不得复用历史 CI 数字。发布包必须来自同一目标提交，并在上传前独立校验 SHA-256。

## 4. 服务器只读预检与备份

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`（首次部署时使用上传包所在目录）。

先确认目标提交、磁盘、旧服务和端口，不修改状态：

```bash
pwd
printf 'target release: %s\n' "${RELEASE_SHA}"
sha256sum "${RELEASE_ARCHIVE}"
df -h /opt /srv /var
systemctl status nginx --no-pager
ss -ltnp
sudo nginx -T
```

首次安装覆盖层前，`preflight.sh` 所要求的目录和 env 文件尚不存在，因此应在安装模板后、填写配置前运行。若是更新部署，则先运行：

```bash
sudo deploy/http-test/scripts/preflight.sh before-first-start
```

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。创建可恢复备份：

```bash
sudo install -d -m 0700 "/var/backups/starchart-ai/${BACKUP_TAG}"
sudo cp -a /etc/nginx/sites-available/ai-nav "/var/backups/starchart-ai/${BACKUP_TAG}/ai-nav" 2>/dev/null || true
sudo cp -a /etc/nginx/sites-enabled/ai-nav "/var/backups/starchart-ai/${BACKUP_TAG}/ai-nav-enabled" 2>/dev/null || true
sudo tar -C /opt -czf "/var/backups/starchart-ai/${BACKUP_TAG}/legacy-ai-nav.tar.gz" ai-nav2
sudo nginx -T | sudo tee "/var/backups/starchart-ai/${BACKUP_TAG}/nginx-expanded.txt" >/dev/null
```

备份文件可能包含服务器拓扑，应保持 root-only，不提交仓库。备份命令成功不等于恢复已验证；未做恢复演练时状态必须写 `NOT RUN`。

## 5. 安装不可变发布与覆盖层

执行身份：服务器 sudo 管理员。工作目录：发布包所在目录。

```bash
sudo install -d -o root -g root -m 0755 "${RELEASE_ROOT}"
sudo unzip -q "${RELEASE_ARCHIVE}" -d "${RELEASE_ROOT}"
sudo chown -R root:root "${RELEASE_ROOT}"
sudo ln -sfn "${RELEASE_ROOT}" /opt/starchart-ai/current
```

依赖安装应使用已锁定依赖，并保留上一版本虚拟环境或可重建材料：

```bash
sudo python3 -m venv /opt/starchart-ai/venv
sudo /opt/starchart-ai/venv/bin/pip install -r /opt/starchart-ai/current/backend/requirements-lock.txt
```

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudo deploy/http-test/scripts/install-overlay.sh
sudo chown root:starchart-ai-http-test /etc/starchart-ai/http-test.env
sudo chown root:starchart-ai-provider-preview /etc/starchart-ai/provider-preview.env
sudo chmod 0640 /etc/starchart-ai/http-test.env /etc/starchart-ai/provider-preview.env
sudo deploy/http-test/scripts/preflight.sh before-first-start
```

`install-overlay.sh` 会备份活动 Nginx 文件、安装模板、执行 `nginx -t`，并仅在语法通过时 reload；它不会生成凭据。首次安装时新路由可能在 8001 启动前短暂返回不可用，因此应在维护窗口内紧接着完成第 6–8 节。旧站 8000、`/chat`、`/health` 和 `/chat-widget.js` 必须持续检查。

## 6. 交互填写 8001 配置并初始化唯一账号

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudoedit /etc/starchart-ai/http-test.env
sudo chown root:starchart-ai-http-test /etc/starchart-ai/http-test.env
sudo chmod 0640 /etc/starchart-ai/http-test.env
sudo deploy/http-test/scripts/preflight.sh before-first-start
```

只填写模板中的空变量；`AI_NAV_SECRET_KEY` 使用服务器上安全生成的随机值，CORS 使用获批的 HTTP origin，账号标识使用获批的唯一测试标识。不要把实际值复制到工单或本手册。

账号初始化必须在交互式终端完成，不接受命令行密码或密码环境变量。执行身份最终降为 `starchart-ai-http-test`，工作目录为 `/opt/starchart-ai/current`：

```bash
sudo bash -lc '
  set -a
  source /etc/starchart-ai/http-test.env
  set +a
  export AI_NAV_DATABASE_PATH=/srv/starchart-ai-http-test/data/ai_nav.sqlite3
  export AI_NAV_UPLOAD_DIR=/srv/starchart-ai-http-test/uploads
  cd /opt/starchart-ai/current
  exec runuser -u starchart-ai-http-test --preserve-environment -- \
    /opt/starchart-ai/venv/bin/python scripts/provision-http-test-account.py
'
```

在隐藏提示中输入密码。初始化器只允许空账号库并创建一个普通账号；不要把输出与账号标识建立公开映射。若数据库已有账号，停止并调查，不能删除或覆盖后重试。

## 7. 启动并验证 8001

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudo systemctl enable --now starchart-ai-http-test.service
sudo systemctl status starchart-ai-http-test.service --no-pager
ss -ltnp "sport = :8001"
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8001/api/v1/health
```

`ss` 必须显示只监听 `127.0.0.1:8001`。失败时先停止服务，不要继续 Nginx 验证。

## 8. Nginx 验证、reload 与 smoke

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo deploy/http-test/scripts/smoke-test.sh
```

随后从公网人工验证项目选择页、旧站、旧聊天/健康/小组件、新站静态资源、API、头像路径、游客助手和唯一测试账号的允许/禁止功能。测试数据必须完全虚构；验证结果只记录状态码、耗时、提交和脱敏摘要，不记录正文、Cookie 或 Token。

失败时不要反复 reload。转到第 11 节回滚，并保持 HTTP 部署 `NO-GO`。

## 9. 手工 8002 Provider 预览

这一节需要用户对**真实 Provider 调用和费用**再次明确授权；未授权时全部记录 `NOT RUN`。

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudoedit /etc/starchart-ai/provider-preview.env
sudo chown root:starchart-ai-provider-preview /etc/starchart-ai/provider-preview.env
sudo chmod 0640 /etc/starchart-ai/provider-preview.env
sudo deploy/http-test/scripts/preflight.sh before-provider-preview
```

API Key 只在上述 root 管理、Provider 预览专用组可读的文件中交互填写。确认 HTTPS Provider URL、允许主机、模型、超时、重试以及单次/日/月成本上限后，按第 6 节相同方式运行初始化器，但改用 `provider-preview.env`、`/srv/starchart-ai-provider-preview/` 的独立数据库和上传目录。

```bash
sudo bash -lc '
  set -a
  source /etc/starchart-ai/provider-preview.env
  set +a
  export AI_NAV_DATABASE_PATH=/srv/starchart-ai-provider-preview/data/ai_nav.sqlite3
  export AI_NAV_UPLOAD_DIR=/srv/starchart-ai-provider-preview/uploads
  cd /opt/starchart-ai/current
  exec runuser -u starchart-ai-provider-preview --preserve-environment -- \
    /opt/starchart-ai/venv/bin/python scripts/provision-http-test-account.py
'
```

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudo systemctl start starchart-ai-provider-preview.service
sudo systemctl status starchart-ai-provider-preview.service --no-pager
ss -ltnp "sport = :8002"
```

`ss` 必须只显示 `127.0.0.1:8002`。操作人本机通过 SSH 隧道访问，执行身份为本机账号，工作目录任意：

```bash
ssh -N -L 8002:127.0.0.1:8002 SERVER_SSH_ALIAS
```

只执行获批的一条有成本上限的人工请求；记录脱敏 provider/model、状态、延迟和成本，不记录提示词或回答正文。验证后立即停止：

```bash
sudo systemctl stop starchart-ai-provider-preview.service
ss -ltnp "sport = :8002"
```

端口必须消失。8002 未启动、未真实调用或未停止，都不能宣称真实 Agent 已验证。

## 10. 正常停止

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。

```bash
sudo systemctl stop starchart-ai-provider-preview.service
sudo systemctl stop starchart-ai-http-test.service
ss -ltnp "sport = :8001"
ss -ltnp "sport = :8002"
```

如需暂时下线新路由，应恢复上一份 Nginx 配置并先运行 `nginx -t`，不要停止或删除旧站 8000。

## 11. 最小回滚

执行身份：服务器 sudo 管理员。工作目录：`/opt/starchart-ai/current`。先停止新实例并保留故障数据库和上传目录：

```bash
sudo systemctl stop starchart-ai-provider-preview.service starchart-ai-http-test.service
sudo cp -a /srv/starchart-ai-http-test "/var/backups/starchart-ai/${BACKUP_TAG}/http-test-failed-state"
sudo cp -a /srv/starchart-ai-provider-preview "/var/backups/starchart-ai/${BACKUP_TAG}/provider-preview-failed-state"
```

恢复上一份 Nginx 配置和上一发布软链接。`PREVIOUS_RELEASE` 必须由操作人从服务器实际目录确认：

```bash
export PREVIOUS_RELEASE="/opt/starchart-ai/releases/REPLACE_WITH_PREVIOUS_COMMIT"
sudo cp -a "/var/backups/starchart-ai/${BACKUP_TAG}/ai-nav" /etc/nginx/sites-available/ai-nav
sudo ln -sfn /etc/nginx/sites-available/ai-nav /etc/nginx/sites-enabled/ai-nav
sudo ln -sfn "${PREVIOUS_RELEASE}" /opt/starchart-ai/current
sudo nginx -t
sudo systemctl reload nginx
```

验证旧 `/`、`/chat`、`/health` 和 `/chat-widget.js`。数据库不做破坏性 down migration，不删除故障库。未实际执行上述步骤时，回滚状态保持 `NOT RUN`；脚本存在不等于回滚通过。

## 12. 记录模板

每次操作只记录以下脱敏字段：

- 操作窗口、执行角色、目标提交和发布包 SHA-256；
- 备份目录、旧/新 release 软链接目标；
- 8000/8001/8002 的监听范围；
- `nginx -t`、服务状态、smoke 的退出码和耗时；
- 公网旧站与新站的脱敏状态码；
- Provider 预览是否获批、是否调用、是否停止；
- 备份恢复、回滚、HTTPS、合规、容量和外部签收的真实状态；
- 四个独立结论：本地整改候选、HTTP 测试部署、真实 Provider 预览、生产发布。

缺少真实证据的字段必须写 `NOT RUN` 或 `NO-GO`，不得根据配置或本地测试推断通过。

## 13. 关联入口

- 架构边界：`docs/02-architecture/deployment/http-subpath-test-deployment-design.md`
- 实施计划：`docs/01-overview/http-subpath-test-deployment-implementation-plan.md`
- 文件与证据索引：`docs/00-index/http-test-deployment-file-index.md`
- 文档地图：`docs/00-index/documentation-map.md`
- 本地机器证据：`docs/06-evidence/platform/http-test-deployment-manifest.json`
- 部署覆盖层：`deploy/http-test/`
