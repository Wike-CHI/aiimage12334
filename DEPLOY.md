# 部署指南

本文档详细介绍如何部署白底图生成器系统，包括使用systemctl管理后端服务，以及构建Tauri桌面应用。

## 目录

1. [系统要求](#系统要求)
2. [数据库部署](#数据库部署)
3. [后端服务部署](#后端服务部署)
4. [Tauri桌面应用构建](#tauri桌面应用构建)
5. [服务管理](#服务管理)
6. [故障排除](#故障排除)

---

## 系统要求

### 服务器要求

- 操作系统：Ubuntu 20.04/22.04 或 CentOS 7/8
- CPU：至少2核
- 内存：至少4GB
- 硬盘：至少50GB可用空间
- Python 3.10+
- MySQL 5.7+ 或 MariaDB 10.5+

### 本地构建要求（Windows）

- Windows 10/11 64位
- Visual Studio Build Tools 2022
- WebView2 运行时
- Rust 工具链（rustup）
- Node.js 18+
- Git

---

## 数据库部署

### 安装MySQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server -y

# CentOS/RHEL
sudo yum install mysql-server -y

# 启动MySQL服务
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

### 创建数据库和用户

```bash
# 登录MySQL
sudo mysql -u root -p

# 执行以下SQL语句
CREATE DATABASE white_bg_generator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'whitebg_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON white_bg_generator.* TO 'whitebg_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 初始化数据库

在后端项目中执行数据库初始化脚本：

```bash
cd /www/wwwroot/生图网站/aiimage12334/backend
source .venv/bin/activate
python init_db.py
```

---

## 后端服务部署

### 1. 安装Python环境和依赖

```bash
# 创建项目目录
sudo mkdir -p /www/wwwroot/生图网站/aiimage12334
cd /www/wwwroot/生图网站/aiimage12334

# 创建虚拟环境
python3 -m venv backend/.venv

# 激活虚拟环境
source backend/.venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑配置文件
nano backend/.env
```

配置文件内容：

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=whitebg_user
DB_PASSWORD=your_secure_password
DB_NAME=white_bg_generator

# JWT
SECRET_KEY=your-very-long-and-secure-secret-key-at-least-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI API (Gemini)
GEMINI_API_KEY=your_gemini_api_key

# CORS
FRONTEND_URL=http://localhost:5173
```

### 3. 配置systemctl服务

```bash
# 复制服务文件
sudo cp /www/wwwroot/生图网站/aiimage12334/deploy/whitebg.service /etc/systemd/system/

# 设置目录权限
sudo chown -R www:www /www/wwwroot/生图网站/aiimage12334
sudo chmod -R 755 /www/wwwroot/生图网站/aiimage12334

# 重新加载systemd
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable whitebg.service

# 启动服务
sudo systemctl start whitebg.service

# 检查服务状态
sudo systemctl status whitebg.service
```

### 4. 配置Nginx反向代理（可选但推荐）

```bash
# 安装Nginx
sudo apt install nginx -y

# 创建Nginx配置文件
sudo nano /etc/nginx/sites-available/whitebg
```

Nginx配置内容：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads/ {
        alias /www/wwwroot/生图网站/aiimage12334/backend/uploads/;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/whitebg /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Tauri桌面应用构建

### 1. 安装构建依赖

#### Windows系统

```powershell
# 1. 安装 Visual Studio Build Tools 2022
# 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 选择以下组件:
# - MSVC v143 - VS 2022 C++ x64/x86 构建工具
# - Windows 11 SDK（或 Windows 10 SDK）

# 2. 安装 WebView2 运行时
# 下载地址: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

# 3. 安装 Rust
winget install Rustlang.Rust.MSVC

# 4. 安装 Node.js
winget install OpenJS.NodeJS.LTS

# 5. 安装 Git
winget install Git.Git
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    curl \
    wget \
    libwebkit2gtk-4.0-dev \
    libappindicator3-dev \
    libsoup-3.0-dev \
    libjavascriptcoregtk-4.1-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev
```

#### CentOS/RHEL

```bash
sudo yum groupinstall "Development Tools" -y
sudo yum install -y \
    webkit2gtk3-devel \
    libappindicator-gtk3-devel \
    libsoup-devel \
    libjavascriptcoregtk-4.0-devel \
    gtk3-devel \
    libindicator-gtk3-devel \
    librsvg2-devel
```

### 2. 配置项目

```bash
# 克隆项目（如果在服务器上）
git clone https://github.com/your-repo/aiimage12334.git
cd aiimage12334

# 安装Node.js依赖
npm install

# 安装Tauri CLI
npm install -D @tauri-apps/cli

# 安装Rust依赖（首次运行会自动安装）
cargo install cargo-tauri
```

### 3. 配置Tauri构建选项

编辑 `src-tauri/tauri.conf.json`，确保以下配置正确：

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
    "withGlobalTauri": true,
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
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

### 4. 构建Windows版本

#### 方法一：使用npm命令

```powershell
# 设置环境变量（API地址改为你的服务器地址）
$env:VITE_API_URL="http://your-server-ip:8000"

# 构建前端
npm run build

# 构建Tauri应用
npm run tauri build
```

#### 方法二：使用Cargo命令

```powershell
# 设置环境变量
$env:VITE_API_URL="http://your-server-ip:8000"

# 构建前端
npm run build

# 直接使用cargo-tauri构建
cargo tauri build --target x86_64-pc-windows-msvc
```

### 5. 获取构建产物

构建完成后，Windows安装包位于：

```
src-tauri/target/release/bundle/msi/白底图生成器_1.0.0_x64_en-US.msi
```

或者：

```
src-tauri/target/release/bundle/nsis/白底图生成器_1.0.0_x64-setup.exe
```

### 6. 配置API地址

在Tauri应用中，API地址需要根据实际部署环境进行配置。编辑前端环境变量：

```bash
# 创建或编辑 .env 文件
echo "VITE_API_URL=http://your-server-ip:8000" > src/.env
```

如果需要动态配置，可以在Tauri的前端代码中添加服务器地址设置界面。

---

## 服务管理

### systemctl常用命令

```bash
# 查看服务状态
sudo systemctl status whitebg.service

# 启动服务
sudo systemctl start whitebg.service

# 停止服务
sudo systemctl stop whitebg.service

# 重启服务
sudo systemctl restart whitebg.service

# 重新加载配置
sudo systemctl daemon-reload

# 查看服务日志
sudo journalctl -u whitebg.service -f

# 查看最近100行日志
sudo journalctl -u whitebg.service -n 100

# 设置开机自启
sudo systemctl enable whitebg.service

# 取消开机自启
sudo systemctl disable whitebg.service
```

### 日志配置

服务日志默认通过journald管理。如需配置日志轮转，创建 `/etc/logrotate.d/whitebg`：

```
/var/log/whitebg.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 www www
    postrotate
        systemctl restart whitebg.service > /dev/null 2>&1 || true
    endscript
}
```

---

## 故障排除

### 后端服务启动失败

#### 检查Python环境

```bash
# 验证虚拟环境
source /www/wwwroot/生图网站/aiimage12334/backend/.venv/bin/activate
python -c "import fastapi; print(fastapi.__version__)"

# 检查依赖安装
pip list | grep -E "fastapi|uvicorn|pydantic"
```

#### 检查端口占用

```bash
# 检查8000端口
sudo lsof -i :8000
sudo netstat -tlnp | grep 8000

# 如果端口被占用，终止进程
sudo kill $(sudo lsof -t -i:8000)
```

#### 检查数据库连接

```bash
# 测试数据库连接
source /www/wwwroot/生图网站/aiimage12334/backend/.venv/bin/activate
python -c "
import pymysql
conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='whitebg_user',
    password='your_password',
    database='white_bg_generator'
)
print('数据库连接成功')
conn.close()
"
```

### Tauri构建失败

#### Windows构建问题

```powershell
# 验证Rust安装
rustc --version
cargo --version

# 验证Visual Studio
vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath

# 清理并重新构建
cargo clean
cargo tauri build
```

#### 依赖缺失

```bash
# Ubuntu/Debian安装缺失依赖
sudo apt install -y libwebkit2gtk-4.0-dev libappindicator3-dev libsoup-3.0-dev

# 验证依赖
ldconfig -p | grep webkit
ldconfig -p | grep appindicator
```

### 网络连接问题

#### 检查防火墙设置

```bash
# Ubuntu UFW
sudo ufw status
sudo ufw allow 8000/tcp

# CentOS firewalld
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

#### 检查SELinux（CentOS）

```bash
# 检查SELinux状态
getenforce

# 临时禁用（测试用）
sudo setenforce 0

# 永久禁用，编辑 /etc/selinux/config
sudo nano /etc/selinux/config
# 将 SELINUX=enforcing 改为 SELINUX=disabled
```

---

## 监控和维护

### 监控脚本

创建监控脚本 `/www/wwwroot/生图网站/aiimage12334/scripts/monitor.sh`：

```bash
#!/bin/bash

# 检查服务状态
if ! sudo systemctl is-active --quiet whitebg.service; then
    echo "[$(date)] 服务已停止，正在重启..."
    sudo systemctl restart whitebg.service
    echo "[$(date)] 服务已重启" >> /var/log/whitebg_monitor.log
fi

# 检查磁盘空间
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$(date)] 磁盘空间不足: ${DISK_USAGE}%" >> /var/log/whitebg_monitor.log
fi

# 检查内存使用
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ $MEM_USAGE -gt 90 ]; then
    echo "[$(date)] 内存使用率过高: ${MEM_USAGE}%" >> /var/log/whitebg_monitor.log
fi
```

添加定时任务：

```bash
# 编辑crontab
crontab -e

# 添加以下行（每5分钟检查一次）
*/5 * * * * /www/wwwroot/生图网站/aiimage12334/scripts/monitor.sh
```

### 备份策略

创建备份脚本 `/www/wwwroot/生图网站/aiimage12334/scripts/backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR=/backup/whitebg
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -u whitebg_user -p'your_password' white_bg_generator > $BACKUP_DIR/db_$DATE.sql

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /www/wwwroot/生图网站/aiimage12334/backend/uploads/

# 清理30天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "[$(date)] 备份完成" >> /var/log/whitebg_backup.log
```

添加定时任务：

```bash
# 每天凌晨2点执行备份
crontab -e

# 添加以下行
0 2 * * * /www/wwwroot/生图网站/aiimage12334/scripts/backup.sh
```

---

## 总结

本部署方案提供了完整的系统部署流程：

1. **后端服务**：使用systemctl管理，支持开机自启、日志管理和故障恢复
2. **Tauri桌面应用**：在本地Windows环境构建，跨平台运行
3. **监控维护**：提供监控和备份脚本，保障系统稳定运行

如有问题，请查看故障排除章节或联系技术支持。

