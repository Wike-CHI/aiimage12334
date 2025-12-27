#!/bin/bash
set -e

PROJECT_DIR="/www/wwwroot/生图网站/aiimage12334/backend"
SERVICE_FILE="/etc/systemd/system/aiimage-backend.service"
ENV_FILE="$PROJECT_DIR/.env"

echo "=== 白底图生成器后端部署脚本 ==="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "警告: 当前用户不是 root，可能需要 sudo 权限"
    echo "建议使用: sudo $0"
    echo ""
fi

# 1. 安装依赖
echo "[1/7] 安装 Python 依赖..."
cd $PROJECT_DIR

# 检查虚拟环境是否存在
if [ ! -d ".venv312" ]; then
    echo "  - 错误: 虚拟环境不存在，请先创建虚拟环境"
    echo "  - 创建命令: python3 -m venv .venv312"
    exit 1
fi

# 检查虚拟环境中的 pip
if [ ! -f ".venv312/bin/pip" ]; then
    echo "  - 错误: 虚拟环境中的 pip 不存在"
    exit 1
fi

source .venv312/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "  - 依赖安装完成"

# 2. 创建环境变量文件（如果不存在）
echo "[2/7] 检查环境变量配置..."
if [ ! -f "$ENV_FILE" ]; then
    echo "  - 创建环境变量文件..."
    cat > "$ENV_FILE" << 'ENVEOF'
# API 服务配置
API_HOST=0.0.0.0
API_PORT=8001
DEBUG=false

# 数据库配置
# 请根据实际情况修改以下配置
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/aiimage

# JWT 密钥
# 请修改为安全的随机字符串
SECRET_KEY=your-secret-key-here-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 前端URL（允许跨域）
FRONTEND_URL=http://localhost:34345

# 文件存储路径
UPLOAD_DIR=/www/wwwroot/生图网站/aiimage12334/backend/uploads
RESULTS_DIR=/www/wwwroot/生图网站/aiimage12334/backend/results
ENVEOF
    echo "  - 已创建 .env 文件模板，请编辑 $ENV_FILE 配置数据库等信息"
else
    echo "  - 环境变量文件已存在"
fi

# 3. 设置目录权限
echo "[3/7] 设置目录权限..."
chown -R www:www $PROJECT_DIR 2>/dev/null || sudo chown -R www:www $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
mkdir -p uploads results
chown -R www:www uploads results 2>/dev/null || sudo chown -R www:www uploads results
echo "  - 权限设置完成"

# 4. 创建 systemd 服务
echo "[4/7] 创建 systemd 服务..."
cat > /tmp/aiimage-backend.service << 'SERVICEEOF'
[Unit]
Description=白底图生成器后端服务
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=notify
User=www
Group=www
WorkingDirectory=/www/wwwroot/生图网站/aiimage12334/backend
Environment="PATH=/www/wwwroot/生图网站/aiimage12334/backend/.venv/bin"
Environment="PYTHONPATH=/www/wwwroot/生图网站/aiimage12334/backend"
ExecStart=/www/wwwroot/生图网站/aiimage12334/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aiimage-backend

[Install]
WantedBy=multi-user.target
SERVICEEOF

if [ "$EUID" -eq 0 ]; then
    cp /tmp/aiimage-backend.service $SERVICE_FILE
    echo "  - 服务文件已创建: $SERVICE_FILE"
else
    echo "  - 请手动复制服务文件: sudo cp /tmp/aiimage-backend.service $SERVICE_FILE"
fi

# 5. 重新加载 systemd 并启动服务
echo "[5/7] 配置并启动服务..."
if [ "$EUID" -eq 0 ]; then
    systemctl daemon-reload
    systemctl enable aiimage-backend.service
    systemctl restart aiimage-backend.service
    echo "  - 服务已启动"
else
    echo "  - 请手动执行以下命令:"
    echo "    sudo systemctl daemon-reload"
    echo "    sudo systemctl enable aiimage-backend.service"
    echo "    sudo systemctl restart aiimage-backend.service"
fi

# 6. 等待服务启动
echo "[6/7] 等待服务启动..."
sleep 3

# 7. 验证服务状态
echo "[7/7] 验证服务状态..."
if curl -s --connect-timeout 5 http://localhost:8001/health > /dev/null 2>&1; then
    echo "  - 服务启动成功!"
    echo ""
    echo "  健康检查响应:"
    curl -s http://localhost:8001/health | head -c 500
    echo ""
else
    echo "  - 警告: 服务可能未正常启动"
    if [ "$EUID" -eq 0 ]; then
        echo ""
        echo "  查看日志: sudo journalctl -u aiimage-backend.service -n 50"
    else
        echo ""
        echo "  查看日志: sudo journalctl -u aiimage-backend.service -n 50"
    fi
fi

echo ""
echo "=========================================="
echo "部署完成!"
echo ""
echo "服务管理命令:"
echo "  查看状态: sudo systemctl status aiimage-backend"
echo "  查看日志: sudo journalctl -u aiimage-backend -f"
echo "  重启服务: sudo systemctl restart aiimage-backend"
echo "  停止服务: sudo systemctl stop aiimage-backend"
echo ""
echo "API 地址: http://129.211.218.135:8001"
echo "文档地址: http://129.211.218.135:8001/docs"
echo "=========================================="

