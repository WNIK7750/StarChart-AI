# Agent 真实设备与读屏验收清单

本清单只补齐阶段 5 最后两项人工证据，不连接数据库、真实 Provider 或 API Key。建议优先使用手机实机与 Windows Narrator；验收完成后立即关闭临时公开链接和本地服务。

## 1. 启动隔离验收页

在项目根目录打开 PowerShell：

```powershell
& "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -Command ". .\scripts\python-runtime.ps1; `$python = Resolve-AiNavPython -Root (Get-Location); & `$python scripts\serve-agent-stage5-acceptance.py"
```

看到以下地址后保持窗口开启：

```text
http://127.0.0.1:8090/assistant.html
```

该服务只绑定本机回环地址，模拟会话能力和一个 20 秒慢请求。按 `Ctrl+C` 可停止。

## 2. 手机真实设备

以下流程使用 Cloudflare 官方 Quick Tunnel。它仅用于开发验收，会生成随机临时域名，不需要 Cloudflare 账号；官方不提供可用性保证，并明确不支持 SSE。本隔离验收页使用普通 HTTP 请求，因此不依赖 SSE。

1. 确认隔离验收页已经在 `127.0.0.1:8090` 运行。
2. 在另一个 PowerShell 窗口下载并启动 Cloudflare 官方 Windows 单文件客户端：

   ```powershell
   $acceptanceDir = Join-Path $env:TEMP "ai-nav-stage5-acceptance"
   New-Item -ItemType Directory -Path $acceptanceDir -Force | Out-Null
   $cloudflared = Join-Path $acceptanceDir "cloudflared.exe"
   Invoke-WebRequest -UseBasicParsing `
     -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
     -OutFile $cloudflared
   & $cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8090
   ```

3. 等待终端显示随机的 `https://...trycloudflare.com` 地址。若刚生成时打不开，等待几秒后刷新；不要把该地址发送给无关人员。
4. 在手机任意现代浏览器打开终端给出的地址，再进入 `/assistant.html`。
5. 依次验收：
   - 首屏没有横向滚动，文字、输入框和发送按钮没有遮挡。
   - 点击“会话”，抽屉完整显示；点击“关闭”后回到对话页。
   - 竖屏与横屏各检查一次。
   - 输入 4000 个字符时输入框可滚动，页面不横向溢出。
   - 系统开启“移除动画”后，页面没有依赖动画才能完成的操作。
6. 记录手机系统、浏览器版本、竖屏/横屏结果和发现的问题；各保留一张截图。无需记录或回传设备序列号、手机号、IP 或账号。
7. 验收后在 Quick Tunnel 窗口和隔离服务窗口分别按 `Ctrl+C`，确认临时地址已失效。

Cloudflare 官方说明：
https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/

## 3. Windows Narrator

Microsoft 官方 Narrator 指南：
https://support.microsoft.com/en-us/windows/complete-guide-to-narrator-e4397a0d-ef4f-b386-d8ae-c172f109bdb1

官方快捷键列表：
https://support.microsoft.com/en-us/windows/appendix-b-narrator-keyboard-commands-and-touch-gestures-8bdab3f4-b3e9-4554-7f28-8b15bd37410a

1. 电脑浏览器打开 `http://127.0.0.1:8090/assistant.html`；读屏验收始终使用本机地址，不经过临时公开链接。
2. 按 `Windows + Ctrl + Enter` 启动 Narrator。
3. 只使用 `Tab`、`Shift+Tab`、方向键、`Enter` 和 `Esc` 完成：
   - 导航到“向助手提问”输入框，确认名称被正确朗读。
   - 输入任意非敏感测试文字并发送，确认“检索中”被宣布。
   - 按 `Esc`，确认“已停止生成”被宣布，焦点回到输入框。
   - 导航到引用区域、会话按钮和停止按钮，确认名称和用途清楚且没有重复焦点。
4. 如需可视审计朗读历史，按 `Narrator + Alt + X` 打开 Microsoft 提供的 speech recap。
5. 记录 Windows 版本、浏览器及版本、Narrator 结果和任何漏读/重复朗读。
6. 按 `Windows + Ctrl + Enter` 关闭 Narrator。

## 4. 回传最小证据

只需回传以下内容，不要包含账号、问题正文或其他个人信息：

```text
真实设备：
- 型号 / 系统 / 浏览器版本：
- 竖屏：通过 / 失败
- 横屏：通过 / 失败
- 会话抽屉：通过 / 失败
- 长文本与 reduced motion：通过 / 失败

Narrator：
- Windows / 浏览器版本：
- 输入框名称：通过 / 失败
- 检索中状态：通过 / 失败
- Esc 停止与焦点归还：通过 / 失败
- 重复或漏读：无 / 说明
```

收到结果后，将其转写为不含用户内容和设备标识的阶段 5 审计结论。
