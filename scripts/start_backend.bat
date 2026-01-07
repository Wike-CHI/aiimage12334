@echo off
# 后端服务启动脚本 (Windows)
chcp 65001 >nul
SETLOCAL EnableDelayedExpansion

REM 设置变量
SET "PORT=8000"
SET "PROJECT_ROOT=%~dp0.."
SET "BACKEND_DIR=%PROJECT_ROOT%\backend"
SET "VENV_SCRIPT=%PROJECT_ROOT%\.venv\Scripts\activate.bat"

echo ======================================
echo   后端服务启动脚本 (Windows)
echo ======================================
echo.

REM 检查并激活虚拟环境
IF EXIST "%VENV_SCRIPT%" (
    echo [INFO] 正在激活虚拟环境...
    CALL "%VENV_SCRIPT%"
) ELSE (
    echo [WARN] 未找到虚拟环境 %VENV_SCRIPT%，将使用系统 Python
)

REM 清理端口
echo [INFO] 检查端口 %PORT% 是否被占用...
FOR /F "tokens=5" %%a IN ('netstat -aon ^| findstr /R ":%PORT% .*LISTENING"') DO (
    SET "PID=%%a"
    echo [WARN] 端口 %PORT% 被进程 !PID! 占用，正在终止...
    taskkill /F /PID !PID! >nul 2>&1
    IF !ERRORLEVEL! EQU 0 (
        echo [INFO] 进程 !PID! 已终止
    ) ELSE (
        echo [ERROR] 无法终止进程 !PID!
    )
)

REM 切换目录并启动
echo.
echo [INFO] 启动后端服务...
echo [INFO] 端口: %PORT%
echo.

CD /D "%BACKEND_DIR%"
python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload

ENDLOCAL
