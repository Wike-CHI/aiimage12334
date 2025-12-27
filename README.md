# 白底图生成器

一个基于 AI 的白底图生成工具，可一键去除图片背景，生成纯净的白底商品图。

## 技术栈

- **前端框架**: React 18 + TypeScript + Vite
- **UI 组件**: shadcn/ui + Tailwind CSS
- **后端服务**: Supabase (Auth + Database + Edge Functions)
- **状态管理**: TanStack Query
- **AI 模型**: Gemini 3 Pro Image

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 主要功能

- 图片上传与预览
- AI 智能去除背景
- 可配置输出分辨率和宽高比
- 用户登录与积分系统
- 任务历史记录（实时更新）
- 图片下载

## 环境变量

需要配置以下环境变量（.env 文件）:

```env
VITE_SUPABASE_URL=你的Supabase项目URL
VITE_SUPABASE_PUBLISHABLE_KEY=你的Supabase发布密钥
VITE_SUPABASE_PROJECT_ID=你的Supabase项目ID
```
