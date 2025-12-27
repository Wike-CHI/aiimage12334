# 白底图生成器部署指南

本文档提供完整的部署方案，包括后端服务 systemctl 部署和 Tauri Windows 桌面端打包。

## 目录结构

```
deploy/
├── backend/
│   ├── deploy-systemctl.sh     # 后端快速部署脚本
│   ├── aiimage-backend.service # Systemd 服务配置文件
│   └── docker-compose.yml      # Docker 部署配置（备用）
├── TAURI_WINDOWS_BUILD_GUIDE.md # Tauri Windows 打包详细指南
└── README.md                   # 本文件
```

## 快速开始

### 1. 后端服务部署（服务器端）

```bash
# 1. 进入部署目录
cd /www/wwwroot/生图网站/aiimage12334/deploy/backend

# 2. 复制并配置环境变量
cp ../../backend/.env.example ../../backend/.env
# 编辑 .env 文件，设置数据库密码等信息

# 3. 运行部署脚本
sudo ./deploy-systemctl.sh
```

### 2. Tauri Windows 桌面端打包（本地 Windows 电脑）

详细步骤请参考 [TAURI_WINDOWS_BUILD_GUIDE.md](TAURI_WINDOWS_BUILD_GUIDE.md)

```bash
# 1. 克隆项目到 Windows 电脑
git clone <your-repo-url>

# 2. 设置 API 地址
echo "VITE_API_URL=http://129.211.218.135:8001" > .env.production.local

# 3. 安装依赖并打包
npm install
npm run tauri build
```

## 架构说明

```
┌─────────────────────────────────────────────────────┐
│                    用户 Windows 电脑                  │
│  ┌─────────────────────────────────────────────┐   │
│  │           Tauri 桌面应用                      │   │
│  │  - React 前端                                │   │
│  │  - 调用远程 API                              │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                          │
                          │ HTTPS API 调用
                          ▼
┌─────────────────────────────────────────────────────┐
│               服务器 129.211.218.135                  │
│  ┌─────────────────────────────────────────────┐   │
│  │         后端服务 (端口 8001)                  │   │
│  │  - FastAPI 应用                              │   │
│  │  - Systemctl 管理                            │   │
│  │  - 自动重启和日志管理                        │   │
│  └─────────────────────────────────────────────┘   │
│                      │                              │
│          ┌───────────┴───────────┐                  │
│          ▼                       ▼                  │
│  ┌─────────────┐         ┌─────────────┐            │
│  │  MySQL 数据库 │         │  文件存储    │            │
│  └─────────────┘         └─────────────┘            │
└─────────────────────────────────────────────────────┘
```

## 服务管理命令

```bash
# 查看服务状态
sudo systemctl status aiimage-backend

# 查看实时日志
sudo journalctl -u aiimage-backend -f

# 重启服务
sudo systemctl restart aiimage-backend

# 停止服务
sudo systemctl stop aiimage-backend
```

## 验证部署

```bash
# 健康检查
curl http://localhost:8001/health

# 预期响应：
# {
#   "status": "healthy",
#   "version": "1.1.0",
#   "database": {"status": "healthy"},
#   "queue": {...}
# }
```

## 故障排除

### 1. 服务启动失败
```bash
# 查看详细错误
sudo journalctl -u aiimage-backend.service -xe

# 检查端口占用
sudo lsof -i :8001
```

### 2. 权限错误
```bash
# 设置目录权限
sudo chown -R www:www /www/wwwroot/生图网站/aiimage12334/backend
```

### 3. 数据库连接失败
- 检查 MySQL 服务状态
- 验证 .env 中的数据库配置
- 确保数据库已创建

### 4. 前端无法连接 API
- 确认服务器防火墙开放 8001 端口
- 检查前端 .env.production.local 中的 API 地址
- 验证后端服务的 CORS 配置

## 相关链接

- API 文档: http://129.211.218.135:8001/docs
- 健康检查: http://129.211.218.135:8001/health

