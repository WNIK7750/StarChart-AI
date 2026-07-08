#!/bin/bash
# AI Nav 一键部署（在服务器 root 下运行）
set -e
echo "=== [1/5] 安装依赖 ==="
apt update && apt install -y python3 python3-venv nginx
echo "=== [2/5] 创建虚拟环境 ==="
cd /opt/ai-nav2/agent
python3 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q
echo "=== [3/5] 注册 systemd ==="
cat > /etc/systemd/system/ai-nav.service << 'UNIT'
[Unit]
Description=AI Nav Agent
After=network.target
[Service]
Type=simple
WorkingDirectory=/opt/ai-nav2/agent
ExecStart=/opt/ai-nav2/agent/venv/bin/python main.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable ai-nav
echo "=== [4/5] 配置 nginx ==="
cat > /etc/nginx/sites-available/ai-nav << 'NGX'
server {
    listen 80;
    server_name _;

    # 精确匹配，避免 /chat 前缀误伤 /chat-widget.js
    location = /chat-widget.js {
        root /opt/ai-nav2;
    }

    location / {
        root /opt/ai-nav2;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /chat {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
NGX
ln -sf /etc/nginx/sites-available/ai-nav /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
echo "=== [5/5] 启动服务 ==="
systemctl start ai-nav
sleep 3
systemctl status ai-nav --no-pager
echo ""
echo "=== 完成！访问 http://$(curl -s ifconfig.me) ==="
