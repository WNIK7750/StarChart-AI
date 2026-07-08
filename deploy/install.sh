#!/bin/bash
# 阿里云 ECS 一键部署脚本
# 运行方式：sudo bash install.sh

set -e

echo "=== AI Nav 部署脚本 ==="

# 1. 安装依赖
echo "[1/6] 安装系统依赖..."
apt update
apt install -y python3.12 python3.12-venv python3-pip nginx git curl

# 2. 创建目录
echo "[2/6] 创建项目目录..."
mkdir -p /opt/ai-nav2
chown -R root:root /opt/ai-nav2

# 3. 等待用户上传代码（手动步骤）
echo "[3/6] 请手动上传代码到 /opt/ai-nav2"
echo "    本地运行: scp -r ai-nav2/* root@47.100.94.1:/opt/ai-nav2/"
echo "    按回车继续..."
read

# 4. 创建虚拟环境
echo "[4/6] 创建 Python 虚拟环境..."
cd /opt/ai-nav2/agent
python3.12 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. 配置 systemd
echo "[5/6] 配置 systemd 服务..."
cat > /etc/systemd/system/ai-nav.service << 'EOF'
[Unit]
Description=AI Nav Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-nav2/agent
Environment=PATH=/opt/ai-nav2/agent/venv/bin
ExecStart=/opt/ai-nav2/agent/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ai-nav

# 6. 配置 nginx
echo "[6/6] 配置 nginx..."
cat > /etc/nginx/sites-available/ai-nav << 'EOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /opt/ai-nav2;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /chat {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ai-nav /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo ""
echo "=== 部署完成 ==="
echo "请执行以下操作："
echo "1. 创建 /opt/ai-nav2/agent/.env 文件（填入 API Key）"
echo "2. systemctl start ai-nav"
echo "3. 访问 http://47.100.94.1"
