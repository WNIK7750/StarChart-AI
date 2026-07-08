# HTTPS 部署指南（ainav.cn）

> 把 AI 知识导航从 `http://47.100.94.1` 升级到 `https://ainav.cn`

---

## 前置准备（在阿里云控制台完成）

### 1. 注册域名
- 登录 https://wanwang.aliyun.com/
- 搜索 `ainav.cn`，下单购买（.cn 首年约 9-29 元）
- 完成实名认证（个人传身份证，1-3 分钟通过）

### 2. 域名解析（A 记录）
进入 **阿里云域名控制台 → 解析设置 → 添加记录**：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|--------|-----|
| A | `@` | `47.100.94.1` | 10分钟 |
| A | `www` | `47.100.94.1` | 10分钟 |

> `@` 表示主域名 ainav.cn，`www` 表示 www.ainav.cn，两条都加。

### 3. 开放安全组 443 端口
**阿里云控制台 → ECS 实例 → 安全组 → 配置规则 → 入方向 → 手动添加**：

| 端口范围 | 授权对象 | 协议类型 | 说明 |
|---------|---------|---------|------|
| 443 | `0.0.0.0/0` | TCP | HTTPS |
| 80 | `0.0.0.0/0` | TCP | HTTP（跳转用） |

> 80 端口如果已开放则跳过。

---

## 部署步骤

### 步骤 1：上传项目代码到服务器
在本地项目根目录打开 PowerShell：
```powershell
.\deploy\upload.ps1
```
脚本会把整个项目（含新的 `assets/logo.png`、`deploy/setup-https.sh`）传到 `/opt/ai-nav2/`。

### 步骤 2：首次部署 HTTP（如果服务器上还没装）
```bash
ssh root@47.100.94.1
bash /opt/ai-nav2/deploy/setup.sh
```
此时访问 `http://47.100.94.1` 应能看到网站（含新 logo）。

### 步骤 3：修改 HTTPS 脚本里的邮箱
```bash
# 登录服务器
ssh root@47.100.94.1

# 编辑脚本，把 EMAIL 改成你的真实邮箱（用于证书过期提醒）
nano /opt/ai-nav2/deploy/setup-https.sh
# 找到这行，改成你的邮箱：
# EMAIL="your-email@example.com"  →  EMAIL="你的邮箱@qq.com"
# 保存退出：Ctrl+O 回车，Ctrl+X
```

### 步骤 4：运行 HTTPS 部署脚本
```bash
bash /opt/ai-nav2/deploy/setup-https.sh
```
脚本会自动完成：
1. ✅ 验证域名是否解析到本机
2. ✅ 安装 certbot
3. ✅ 配置 Nginx HTTP
4. ✅ 向 Let's Encrypt 申请 SSL 证书（免费，90天有效）
5. ✅ 自动配置 443 端口 + HTTP→HTTPS 301 跳转
6. ✅ 注入安全头（HSTS、X-Frame-Options 等）
7. ✅ 设置自动续期（每天检查，到期前 30 天自动续）

### 步骤 5：验证
浏览器访问：
- ✅ `https://ainav.cn` — 应看到绿色锁标
- ✅ `http://ainav.cn` — 应自动跳转到 https
- ✅ 网页标题栏 logo 已更新（A + 指南针图标）
- ✅ 浏览器标签页 favicon 也是新 logo

---

## 常用运维命令

```bash
# 查看证书状态
certbot certificates

# 手动续期测试
certbot renew --dry-run

# 手动续期（立即生效）
certbot renew && systemctl reload nginx

# 查看 Nginx 配置是否正确
nginx -t

# 重载 Nginx
systemctl reload nginx

# 查看后端服务状态
systemctl status ai-nav

# 查看后端日志
journalctl -u ai-nav -f

# 查看 Nginx 访问日志
tail -f /var/log/nginx/access.log
```

---

## 故障排查

### Q: 脚本报错"域名未解析到任何 IP"
A: DNS 还没生效。等 5-10 分钟后重新运行。可用 `dig ainav.cn` 或 https://tool.chinaz.com/dns 查询解析状态。

### Q: certbot 申请证书失败
A: 检查：
1. 安全组 80 和 443 端口是否都开放
2. 域名是否已实名认证（阿里云要求 .cn 必须实名后解析才生效）
3. 服务器 80 端口能否被外网访问（Let's Encrypt 需通过 80 端口验证）

### Q: 网页打开了但 logo 不显示
A: 确认 `assets/logo.png` 已上传到服务器：
```bash
ls -la /opt/ai-nav2/assets/logo.png
```
不存在则重新跑 `upload.ps1` 上传。

### Q: 聊天功能（/chat）报 502
A: 后端服务没起来：
```bash
systemctl status ai-nav
journalctl -u ai-nav --no-pager | tail -30
```
检查 `/opt/ai-nav2/agent/.env` 是否存在、API key 是否配置。
