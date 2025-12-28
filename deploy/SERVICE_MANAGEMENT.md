# 服务管理指南

本文档介绍如何使用 systemctl 管理白底图生成器后端服务，以及如何查看和分析日志。

## 服务文件位置

服务文件路径：`/www/wwwroot/生图网站/aiimage12334/deploy/whitebg.service`

安装到系统：
```bash
sudo cp /www/wwwroot/生图网站/aiimage12334/deploy/whitebg.service /etc/systemd/system/
```

## 基础服务管理命令

### 启动服务

```bash
# 启动服务
sudo systemctl start whitebg.service

# 启动并查看状态
sudo systemctl start whitebg.service && systemctl status whitebg.service
```

### 停止服务

```bash
# 停止服务
sudo systemctl stop whitebg.service
```

### 重启服务

```bash
# 重启服务（推荐，会先停止再启动）
sudo systemctl restart whitebg.service

# 热重载（不中断连接，适合配置更新）
sudo systemctl reload whitebg.service
```

### 查看服务状态

```bash
# 查看服务状态
sudo systemctl status whitebg.service

# 查看服务是否在运行
systemctl is-active whitebg.service

# 查看服务是否开机自启
systemctl is-enabled whitebg.service
```

### 开机自启管理

```bash
# 启用开机自启
sudo systemctl enable whitebg.service

# 禁用开机自启
sudo systemctl disable whitebg.service

# 查看所有已启用的服务
systemctl list-unit-files | grep enabled
```

## 日志查看

### 实时查看日志

```bash
# 实时查看服务日志
sudo journalctl -u whitebg.service -f

# 实时查看日志（最后100行开始）
sudo journalctl -u whitebg.service -n 100 -f
```

### 查看历史日志

```bash
# 查看今天的所有日志
sudo journalctl -u whitebg.service --since today

# 查看指定时间段的日志
sudo journalctl -u whitebg.service --since "2025-12-28 00:00:00" --until "2025-12-28 12:00:00"

# 查看昨天的日志
sudo journalctl -u whitebg.service --since yesterday

# 查看最近的50行日志
sudo journalctl -u whitebg.service -n 50

# 查看所有日志（不限时间）
sudo journalctl -u whitebg.service
```

### 日志级别过滤

```bash
# 只查看ERROR级别及以上的日志
sudo journalctl -u whitebg.service -p err

# 查看WARNING级别
sudo journalctl -u whitebg.service -p warning

# 查看INFO级别及以上
sudo journalctl -u whitebg.service -p info

# 查看DEBUG级别
sudo journalctl -u whitebg.service -p debug
```

### 日志导出

```bash
# 导出所有日志到文件
sudo journalctl -u whitebg.service > /tmp/whitebg.log

# 导出最近1000行日志
sudo journalctl -u whitebg.service -n 1000 > /tmp/whitebg_recent.log

# 导出今天的ERROR日志
sudo journalctl -u whitebg.service -p err --since today > /tmp/whitebg_errors.log
```

### 日志轮转配置

创建日志轮转配置 `/etc/logrotate.d/whitebg`：

```bash
sudo nano /etc/logrotate.d/whitebg
```

添加以下内容：

```
/var/log/whitebg.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 root root
    postrotate
        systemctl restart whitebg.service > /dev/null 2>&1 || true
    endscript
}
```

然后设置权限：

```bash
sudo chmod 644 /etc/logrotate.d/whitebg
```

## 常见问题排查

### 服务无法启动

```bash
# 1. 查看详细错误
sudo systemctl status whitebg.service

# 2. 查看最近日志
sudo journalctl -u whitebg.service -n 50

# 3. 检查端口占用
sudo netstat -tlnp | grep 8001

# 4. 检查Python环境
source /www/wwwroot/生图网站/aiimage12334/.venv312/bin/activate
python -c "import fastapi; print(fastapi.__version__)"
```

### 服务启动后立即停止

```bash
# 查看完整日志
sudo journalctl -u whitebg.service -e

# 检查配置文件
cat /www/wwwroot/生图网站/aiimage12334/backend/.env

# 手动测试启动
cd /www/wwwroot/生图网站/aiimage12334/backend
source /www/wwwroot/生图网站/aiimage12334/.venv312/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### API无响应

```bash
# 1. 检查服务状态
sudo systemctl status whitebg.service

# 2. 检查Nginx代理
curl -s http://127.0.0.1:8001/health

# 3. 检查端口监听
sudo netstat -tlnp | grep -E "8001|nginx"

# 4. 查看API错误日志
sudo journalctl -u whitebg.service | grep -i error
```

### 数据库连接失败

```bash
# 1. 检查MySQL服务
sudo systemctl status mysqld

# 2. 测试数据库连接
source /www/wwwroot/生图网站/aiimage12334/.venv312/bin/activate
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

# 3. 查看数据库相关日志
sudo journalctl -u whitebg.service | grep -i database
```

## 服务监控脚本

创建监控脚本 `/www/wwwroot/生图网站/aiimage12334/scripts/monitor.sh`：

```bash
#!/bin/bash

LOG_FILE="/var/log/whitebg_monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# 检查服务状态
if ! systemctl is-active --quiet whitebg.service; then
    echo "[$DATE] 警告：服务已停止，正在重启..." >> $LOG_FILE
    sudo systemctl restart whitebg.service
    echo "[$DATE] 服务已重启" >> $LOG_FILE
fi

# 检查磁盘空间
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$DATE] 警告：磁盘空间不足 ${DISK_USAGE}%" >> $LOG_FILE
fi

# 检查内存使用
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ $MEM_USAGE -gt 90 ]; then
    echo "[$DATE] 警告：内存使用率过高 ${MEM_USAGE}%" >> $LOG_FILE
fi

# 检查API响应
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/health)
if [ "$HTTP_STATUS" != "200" ]; then
    echo "[$DATE] 警告：API无响应 (HTTP $HTTP_STATUS)" >> $LOG_FILE
fi
```

添加执行权限：

```bash
chmod +x /www/wwwroot/生图网站/aiimage12334/scripts/monitor.sh
```

设置定时任务（每5分钟检查一次）：

```bash
crontab -e

# 添加
*/5 * * * * /www/wwwroot/生图网站/aiimage12334/scripts/monitor.sh
```

## 完整服务管理清单

```bash
# 完整的服务管理流程
sudo systemctl daemon-reload                    # 重新加载配置
sudo systemctl enable whitebg.service           # 启用开机自启
sudo systemctl start whitebg.service            # 启动服务
sudo systemctl status whitebg.service           # 查看状态
sudo journalctl -u whitebg.service -f           # 实时查看日志
sudo systemctl restart whitebg.service          # 重启服务
sudo systemctl stop whitebg.service             # 停止服务
sudo systemctl disable whitebg.service          # 禁用开机自启
```

## 快捷命令别名

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
# 服务管理别名
alias wbg-status='sudo systemctl status whitebg.service'
alias wbg-start='sudo systemctl start whitebg.service'
alias wbg-stop='sudo systemctl stop whitebg.service'
alias wbg-restart='sudo systemctl restart whitebg.service'
alias wbg-logs='sudo journalctl -u whitebg.service -f'
alias wbg-logs-err='sudo journalctl -u whitebg.service -p err -f'

# 重新加载配置
alias wbg-reload='sudo systemctl daemon-reload && sudo systemctl restart whitebg.service'
```

然后执行：

```bash
source ~/.bashrc
```

## 总结

| 操作 | 命令 |
|------|------|
| 启动服务 | `sudo systemctl start whitebg.service` |
| 停止服务 | `sudo systemctl stop whitebg.service` |
| 重启服务 | `sudo systemctl restart whitebg.service` |
| 查看状态 | `sudo systemctl status whitebg.service` |
| 实时日志 | `sudo journalctl -u whitebg.service -f` |
| 查看ERROR | `sudo journalctl -u whitebg.service -p err` |
| 开机自启 | `sudo systemctl enable whitebg.service` |
| 禁用自启 | `sudo systemctl disable whitebg.service` |

