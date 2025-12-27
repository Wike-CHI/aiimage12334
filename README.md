# 白底图生成器

一个基于 AI 的白底图生成工具，可一键去除图片背景，生成纯净的白底商品图。

## 技术栈

- **桌面应用**: Tauri 2.0 + React 18 + TypeScript
- **UI 组件**: shadcn/ui + Tailwind CSS
- **后端服务**: Python FastAPI
- **数据库**: MySQL
- **AI 模型**: Gemini 3 Pro Image

## 项目结构

```text
aiimage12334/
├── src/                  # React 前端源码
│   ├── components/       # React 组件
│   ├── pages/            # 页面
│   ├── hooks/            # 自定义 Hooks
│   ├── integrations/     # API 客户端等
│   └── ...
├── src-tauri/            # Tauri 桌面应用配置
│   ├── src/              # Rust 源码
│   ├── icons/            # 应用图标
│   ├── Cargo.toml
│   └── tauri.conf.json
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── routes/       # API 路由
│   │   ├── services/     # 业务逻辑
│   │   ├── models.py     # 数据模型
│   │   └── config.py     # 配置
│   └── requirements.txt
├── deploy/               # 部署配置
│   ├── whitebg.service   # systemctl 服务文件
│   └── .env              # Docker 部署环境变量
├── DEPLOY.md             # 详细部署指南
├── .env                  # 环境变量
└── README.md
```

## 部署方式

本项目支持以下两种部署方式：

- **服务器部署**: 使用 systemctl 管理后端服务
- **桌面应用**: 构建 Tauri 桌面应用（支持 Windows/macOS/Linux）

详细部署指南请参考 [DEPLOY.md](./DEPLOY.md)

### 服务器部署（systemctl）

#### 1. 环境准备

```bash
# 安装 Python 3.10+
sudo apt update
sudo apt install python3.10 python3-pip python3-venv -y

# 安装 MySQL
sudo apt install mysql-server -y
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

#### 2. 创建数据库

```bash
# 登录 MySQL
sudo mysql -u root -p

# 执行 SQL 创建数据库和用户
CREATE DATABASE white_bg_generator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'whitebg_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON white_bg_generator.* TO 'whitebg_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 3. 部署后端服务

```bash
# 进入项目目录
cd /www/wwwroot/生图网站/aiimage12334

# 创建虚拟环境
python3 -m venv backend/.venv

# 激活虚拟环境
source backend/.venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt

# 配置环境变量
cp backend/.env.example backend/.env
nano backend/.env

# 初始化数据库
python backend/init_db.py

# 复制 systemctl 服务文件
sudo cp deploy/whitebg.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable whitebg.service
sudo systemctl start whitebg.service

# 检查服务状态
sudo systemctl status whitebg.service
```

#### 4. 配置 Nginx（可选但推荐）

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/whitebg
```

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads/ {
        alias /www/wwwroot/生图网站/aiimage12334/backend/uploads/;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/whitebg /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Tauri 桌面应用构建（Windows）

#### 1. 安装构建工具（Windows）

```powershell
# 1. 安装 Visual Studio Build Tools 2022
# 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 选择组件: MSVC v143 - VS 2022 C++ x64/x86 构建工具

# 2. 安装 WebView2 运行时
# 下载地址: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

# 3. 安装 Rust
winget install Rustlang.Rust.MSVC

# 4. 安装 Node.js
winget install OpenJS.NodeJS.LTS

# 5. 安装 Git
winget install Git.Git
```

#### 2. 构建 Windows 版本

```powershell
# 克隆项目
git clone https://github.com/your-repo/aiimage12334.git
cd aiimage12334

# 安装依赖
npm install
npm install -D @tauri-apps/cli

# 配置 API 地址（改为你的服务器地址）
$env:VITE_API_URL="http://your-server-ip:8000"

# 构建前端
npm run build

# 构建 Tauri 应用
npm run tauri build
```

#### 3. 获取安装包

构建完成后，安装包位于：

```
src-tauri/target/release/bundle/msi/白底图生成器_1.0.0_x64_en-US.msi
```

或

```
src-tauri/target/release/bundle/nsis/白底图生成器_1.0.0_x64-setup.exe
```

## 服务管理

```bash
# 查看服务状态
sudo systemctl status whitebg.service

# 启动服务
sudo systemctl start whitebg.service

# 停止服务
sudo systemctl stop whitebg.service

# 重启服务
sudo systemctl restart whitebg.service

# 查看日志
sudo journalctl -u whitebg.service -f
```

## 环境变量

### 后端 (.env)

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=white_bg_generator

# JWT
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI API (Gemini)
GEMINI_API_KEY=your_gemini_api_key

# CORS
FRONTEND_URL=http://localhost:5173
```

### 前端（src/.env）

```env
VITE_API_URL=http://localhost:8000
```

## 本地开发

### 后端服务（Python FastAPI）

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入你的配置

# 初始化数据库
python init_db.py

# 启动后端服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端服务运行在 `http://localhost:8000`

### 桌面应用（Tauri）

```bash
# 安装依赖
npm install

# 启动开发模式（同时启动前端和 Tauri）
npm run tauri dev

# 构建生产版本
npm run tauri build
```

## 主要功能

- 图片上传与预览
- AI 智能去除背景（Gemini 3 Pro Image）
- 可配置输出分辨率和宽高比
- 用户注册与登录
- 积分系统
- 任务历史记录
- 图片下载
- 跨平台桌面应用（Tauri）
