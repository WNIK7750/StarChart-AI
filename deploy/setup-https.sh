#!/bin/bash
# ============================================================
# AI 知识导航 — HTTPS 一键部署脚本（Let's Encrypt + certbot）
# 在服务器 root 下运行：bash /opt/ai-nav2/deploy/setup-https.sh
# ============================================================
set -e

# ---------- 配置区（请按需修改）----------
DOMAIN="ainav.cn"                          # 你的域名
EMAIL="your-email@example.com"             # 用于接收证书过期提醒（必填，改成你的邮箱）
PROJECT_DIR="/opt/ai-nav2"                 # 项目根目录
BACKEND_PORT="8000"                        # Agent 后端端口
# ----------------------------------------

echo "============================================================"
echo "  AI 知识导航 — HTTPS 部署"
echo "  域名: $DOMAIN"
echo "  邮箱: $EMAIL"
echo "============================================================"

# 检查域名是否解析到本机
SERVER_IP=$(curl -s ifconfig.me)
echo "本机公网 IP: $SERVER_IP"
echo "正在验证域名解析..."
RESOLVED_IP=$(getent hosts "$DOMAIN" | awk '{print $1}' || echo "")
if [ -z "$RESOLVED_IP" ]; then
    echo "❌ 错误：域名 $DOMAIN 未解析到任何 IP。"
    echo "   请先在域名服务商添加 A 记录：$DOMAIN -> $SERVER_IP"
    echo "   解析生效后重新运行此脚本。"
    exit 1
fi
echo "域名 $DOMAIN 解析到: $RESOLVED_IP"
if [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
    echo "⚠️  警告：域名解析 IP ($RESOLVED_IP) 与本机 IP ($SERVER_IP) 不一致！"
    echo "   请等待 DNS 生效后再试，或检查 A 记录配置。"
    read -p "是否仍要继续？(y/N) " yn
    [ "$yn" != "y" ] && exit 1
fi

# ---------- [1/6] 安装依赖 ----------
echo ""
echo "=== [1/6] 安装 certbot 及 nginx ==="
apt update -qq
apt install -y -qq nginx certbot python3-certbot-nginx > /dev/null
echo "✓ 依赖安装完成"

# ---------- [2/6] 写入 HTTP 配置（供 certbot 验证用） ----------
echo ""
echo "=== [2/6] 写入 Nginx HTTP 配置 ==="
cat > /etc/nginx/sites-available/ai-nav << NGX_HTTP
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    # /chat-widget.js 精确匹配，避免被 /chat 前缀代理吞掉
    location = /chat-widget.js {
        root $PROJECT_DIR;
    }

    # 静态前端
    location / {
        root $PROJECT_DIR;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API（聊天）
    location /chat {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
    }
}
NGX_HTTP

ln -sf /etc/nginx/sites-available/ai-nav /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
echo "✓ HTTP 配置已生效（80 端口）"

# ---------- [3/6] 申请 Let's Encrypt 证书 ----------
echo ""
echo "=== [3/6] 申请 SSL 证书（Let's Encrypt） ==="
certbot --nginx \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --redirect \
    --email "$EMAIL" \
    --no-eff-email
echo "✓ 证书申请成功，已自动配置 443 端口 + HTTP→HTTPS 跳转"

# ---------- [4/6] 优化 HTTPS 安全头 ----------
echo ""
echo "=== [4/6] 注入 HTTPS 安全头 ==="
CONF_FILE="/etc/nginx/sites-available/ai-nav"
# 在 443 server 块内追加安全头（HSTS / SSL 优化）
# certbot 已生成 443 块，我们用 sed 在 ssl_certificate 行后插入
if ! grep -q "ssl_protocols" "$CONF_FILE"; then
    sed -i "/ssl_certificate_key/a\\
    \\n    # --- SSL 优化 ---\\n    ssl_protocols TLSv1.2 TLSv1.3;\\n    ssl_prefer_server_ciphers on;\\n    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;\\n    ssl_session_cache shared:SSL:10m;\\n    ssl_session_timeout 1d;\\n\\n    # --- 安全响应头 ---\\n    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;\\n    add_header X-Content-Type-Options nosniff always;\\n    add_header X-Frame-Options SAMEORIGIN always;\\n    add_header Referrer-Policy strict-origin-when-cross-origin always;" "$CONF_FILE"
fi
nginx -t
systemctl reload nginx
echo "✓ 安全头已注入"

# ---------- [5/6] 配置自动续期 ----------
echo ""
echo "=== [5/6] 配置证书自动续期 ==="
# certbot 已自带 systemd timer，这里仅做验证
certbot renew --dry-run > /dev/null 2>&1 && echo "✓ 续期测试通过" || echo "⚠️  续期测试失败，请手动检查: certbot renew --dry-run"
systemctl enable --now certbot.timer 2>/dev/null || true
echo "  续期计划: 每天 2 次自动检查，到期前 30 天自动续"

# ---------- [6/6] 完成 ----------
echo ""
echo "=== [6/6] 验证服务状态 ==="
systemctl is-active --quiet nginx && echo "✓ Nginx 运行中" || echo "✗ Nginx 异常"
systemctl is-active --quiet ai-nav && echo "✓ AI Nav Agent 运行中" || echo "✗ AI Nav Agent 异常（请检查: systemctl status ai-nav）"

echo ""
echo "============================================================"
echo "  🎉 HTTPS 部署完成！"
echo ""
echo "  访问地址:  https://$DOMAIN"
echo "  HTTP 自动跳转 HTTPS"
echo ""
echo "  证书有效期: 90 天（自动续期）"
echo "  续期日志:   /var/log/letsencrypt/"
echo ""
echo "  常用命令:"
echo "    查看证书:   certbot certificates"
echo "    手动续期:   certbot renew"
echo "    查看 Nginx: nginx -t && systemctl reload nginx"
echo "============================================================"
