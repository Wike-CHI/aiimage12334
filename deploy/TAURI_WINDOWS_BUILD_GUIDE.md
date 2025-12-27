# Tauri Windows 桌面端打包指南

本文档详细介绍如何在本地 Windows 电脑上打包 Tauri 桌面应用。

## 环境要求

### 1. 系统要求
- Windows 10 1809+ 或 Windows 11
- 至少 8GB RAM（推荐 16GB）
- 至少 10GB 磁盘空间

### 2. 必需软件

#### 2.1 Node.js 18+
```bash
# 访问 https://nodejs.org/ 下载 LTS 版本
# 推荐使用 nvm-windows 管理 Node.js 版本
```

#### 2.2 Rust
```bash
# 访问 https://rustup.rs/ 下载 rustup-init.exe
# 安装时选择默认配置即可
```

#### 2.3 WebView2
- Windows 11 已内置
- Windows 10 需要单独安装
- 下载地址: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

#### 2.4 Visual Studio Build Tools
```bash
# 访问 https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 下载 "Build Tools for Visual Studio 2022"
# 安装时选择 "使用 C++ 的桌面开发" 工作负载
```

## 项目配置

### 1. 设置 API 地址

在打包前，需要将前端 API 地址指向您的服务器。

**方法一：创建环境变量文件**

在项目根目录创建 `.env.production.local` 文件：

```env
VITE_API_URL=http://129.211.218.135:8001
```

**方法二：修改配置文件**

编辑 [src/config/index.ts](src/config/index.ts)：

```typescript
export const API_CONFIG = {
  baseURL: getEnvRequired('VITE_API_URL'),  // 确保从环境变量读取
  timeout: 30000,
};
```

### 2. 构建前端

```bash
# 进入项目目录
cd C:\path\to\aiimage12334

# 安装依赖
npm install

# 构建生产版本
npm run build
```

## 打包步骤

### 1. 安装 Tauri CLI

```bash
# 全局安装
npm install -g @tauri-apps/cli

# 或者在项目中安装
npm install -D @tauri-apps/cli
```

### 2. 执行打包

```bash
# 执行打包命令
npm run tauri build
```

打包过程可能需要 5-15 分钟，取决于电脑性能。

### 3. 打包选项配置

编辑 [src-tauri/tauri.conf.json](src-tauri/tauri.conf.json) 自定义打包配置：

```json
{
  "productName": "白底图生成器",
  "version": "1.0.0",
  "identifier": "com.whitebg.app",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:8080",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "白底图生成器",
        "width": 1200,
        "height": 800,
        "minWidth": 800,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false
      }
    ]
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "shortName": "白底图",
    "category": "Productivity",
    "copyright": "2025",
    "deb": {
      "depends": ["webview2"]
    },
    "windows": {
      "certificateThumbprint": null,
      "digestAlgorithm": "sha256",
      "timestampUrl": ""
    }
  }
}
```

## 输出文件

打包完成后，安装包位于以下目录：

```
src-tauri\target\release\bundle\
├── msi/
│   ├── 白底图生成器_1.0.0_x64.msi
│   └── 白底图生成器_1.0.0_x64_en-US.msi
├── exe/
│   ├── 白底图生成器_1.0.0_x64-setup.exe
│   └── 白底图生成器_1.0.0_x64-setup.exe.bundle
└── zip/
    └── 白底图生成器_1.0.0_x64.zip
```

### 安装包说明

| 文件类型 | 说明 | 推荐场景 |
|---------|------|---------|
| .msi | Windows Installer 包 | 企业部署 |
| .exe | NSIS 安装程序 | 个人用户分发 |
| .zip | 便携版 | 临时使用 |

## 常见问题

### 1. 打包失败 - 权限错误
```bash
# 以管理员身份运行命令提示符或 PowerShell
```

### 2. WebView2 安装失败
```powershell
# 使用以下命令手动安装
winget install Microsoft.WebView2
```

### 3. Rust 版本不兼容
```bash
# 检查 Rust 版本
rustc --version

# 如需更新
rustup update stable
```

### 4. 内存不足
```bash
# 减少编译线程数
set CARGO_BUILD_JOBS=2
npm run tauri build
```

### 5.  antivirus 阻止打包
```bash
# 将项目目录添加到 antivirus 排除列表
```

## 签名证书（可选）

### 生成自签名证书

```powershell
# 使用 PowerShell（以管理员身份）
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=白底图生成器" -KeyUsage DigitalSignature -FriendlyName "白底图生成器签名证书" -CertStoreLocation "Cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(5)

# 导出证书
$pwd = ConvertTo-SecureString -String "your-password" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "C:\path\to\certificate.pfx" -Password $pwd
```

### 配置签名

编辑 [src-tauri/tauri.conf.json](src-tauri/tauri.conf.json)：

```json
{
  "bundle": {
    "windows": {
      "certificateThumbprint": "YOUR_CERTIFICATE_THUMBPRINT",
      "timestampUrl": "http://timestamp.digicert.com"
    }
  }
}
```

## 分发说明

### 1. 安装前准备
- 确保服务器上的后端服务已启动
- 确认服务器防火墙开放 8001 端口
- 准备数据库和文件存储目录

### 2. 用户安装步骤
1. 下载安装包（.msi 或 .exe）
2. 运行安装程序
3. 安装完成后启动应用
4. 首次启动可能需要几秒钟加载 WebView2

### 3. 验证安装
- 检查应用能否正常启动
- 尝试登录或使用功能
- 确认能连接到服务器 API

## 服务端部署验证

在安装桌面端之前，先验证服务端已正常运行：

```bash
# 在服务器上执行
curl http://localhost:8001/health

# 或从外部访问
curl http://129.211.218.135:8001/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "database": {"status": "healthy"},
  "queue": {...}
}
```

## 相关文档

- 后端服务部署: [deploy/backend/deploy-systemctl.sh](deploy/backend/deploy-systemctl.sh)
- Systemd 服务配置: [deploy/backend/aiimage-backend.service](deploy/backend/aiimage-backend.service)
- 环境变量配置: [backend/.env.example](backend/.env.example)
- 前端环境变量: [.env.example](.env.example)

