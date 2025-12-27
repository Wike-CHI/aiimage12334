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
├── .env                  # 环境变量
└── README.md
```

## 快速开始

### 1. 后端服务（Python FastAPI）

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

### 2. 桌面应用（Tauri）

```bash
# 安装依赖
npm install

# 启动开发模式（同时启动前端和 Tauri）
npm run tauri dev

# 构建生产版本
npm run tauri build
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

### 前端（src/.env 或 Tauri 配置）

```env
VITE_API_URL=http://localhost:8000
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
