#!/bin/bash
# 后端服务启动脚本
# 自动清理端口并启动服务

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
PORT=8000
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/.venv312"
CLEANUP_SCRIPT="$PROJECT_DIR/scripts/cleanup_ports.py"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  后端服务启动脚本${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# 检查 Python 虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}错误: 虚拟环境不存在: $VENV_DIR${NC}"
    exit 1
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 端口清理
echo -e "${YELLOW}检查端口 $PORT 是否被占用...${NC}"
if command -v python3 &> /dev/null; then
    python3 "$CLEANUP_SCRIPT" $PORT
    if [ $? -ne 0 ]; then
        echo -e "${RED}端口清理失败，尝试强制清理...${NC}"
        # 强制清理
        fuser -k ${PORT}/tcp 2>/dev/null || true
        sleep 1
    fi
else
    # 使用 lsof 或 fuser 直接清理
    if command -v fuser &> /dev/null; then
        fuser -k ${PORT}/tcp
        echo -e "${GREEN}已使用 fuser 清理端口 $PORT${NC}"
    elif command -v lsof &> /dev/null; then
        PIDS=$(lsof -ti:${PORT})
        if [ -n "$PIDS" ]; then
            echo "终止进程: $PIDS"
            kill -9 $PIDS 2>/dev/null || true
        fi
        echo -e "${GREEN}已使用 lsof 清理端口 $PORT${NC}"
    fi
fi

echo ""
echo -e "${GREEN}启动后端服务...${NC}"
echo -e "${YELLOW}端口: $PORT${NC}"
echo ""

# 切换到后端目录并启动
cd "$BACKEND_DIR"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload

