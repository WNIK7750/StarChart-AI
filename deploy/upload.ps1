# Windows PowerShell 上传脚本
# 用法: .\upload.ps1

$Server = "47.100.94.1"
$User = "root"
$LocalPath = "D:\Web期末作业\ai-nav2\*"
$RemotePath = "/opt/ai-nav2/"

Write-Host "=== 上传项目到服务器 ===" -ForegroundColor Green

# 确保服务器目录存在
Write-Host "[1/3] 创建服务器目录..."
ssh "${User}@${Server}" "mkdir -p /opt/ai-nav2"

# 上传文件（排除 agent/venv, agent/chroma_db, agent/__pycache__, deploy）
Write-Host "[2/3] 上传代码..."
scp -r `
  "$LocalPath" `
  "${User}@${Server}:${RemotePath}"

Write-Host "[3/3] 上传 .env（手动复制）" -ForegroundColor Yellow
Write-Host "请手动把 .env 复制到服务器："
Write-Host "  scp D:\Web期末作业\ai-nav2\agent\.env ${User}@${Server}:/opt/ai-nav2/agent/.env"
Write-Host ""
Write-Host "=== 部署方式 ===" -ForegroundColor Green
Write-Host ""
Write-Host "[首次部署 - HTTP] SSH 登录后运行："
Write-Host "  ssh ${User}@${Server}"
Write-Host "  bash /opt/ai-nav2/deploy/setup.sh"
Write-Host ""
Write-Host "[升级到 HTTPS] 域名解析生效后运行：" -ForegroundColor Cyan
Write-Host "  先编辑 /opt/ai-nav2/deploy/setup-https.sh 修改 DOMAIN 和 EMAIL"
Write-Host "  bash /opt/ai-nav2/deploy/setup-https.sh"
