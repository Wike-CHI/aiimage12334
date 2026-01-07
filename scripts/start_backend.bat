@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

REM ============================================================================
REM 后端服务启动脚本 (Windows) v2.0
REM 功能：自动激活环境、清理端口/自动切换端口、启动服务
REM ============================================================================

REM --- 配置 ---
set "DEFAULT_PORT=8000"
set "MAX_RETRIES=5"
set "PROJECT_ROOT=%~dp0.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

REM --- 日志函数前缀 ---
set "LOG_INFO=[INFO] "
set "LOG_WARN=[WARN] "
set "LOG_ERR=[ERROR] "

echo %LOG_INFO%正在初始化后端启动脚本...
echo %LOG_INFO%项目根目录: %PROJECT_ROOT%

REM --- 1. 虚拟环境检测与激活 ---
echo.
echo %LOG_INFO%正在检测虚拟环境...

set "VENV_ACTIVATED=0"
set "VENV_LIST=.venv312 .venv venv env"

for %%v in (%VENV_LIST%) do (
    if exist "%PROJECT_ROOT%\%%v\Scripts\activate.bat" (
        echo %LOG_INFO%发现虚拟环境: %%v
        call "%PROJECT_ROOT%\%%v\Scripts\activate.bat"
        if !ERRORLEVEL! EQU 0 (
            set "VENV_ACTIVATED=1"
            echo %LOG_INFO%虚拟环境已激活
            goto :VenvCheckDone
        ) else (
            echo %LOG_WARN%虚拟环境 %%v 激活失败
        )
    )
)

:VenvCheckDone
if "!VENV_ACTIVATED!"=="0" (
    echo %LOG_WARN%未找到或无法激活虚拟环境，将尝试使用系统 Python
    python --version >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo %LOG_ERR%未检测到系统 Python，请安装 Python 或修复环境。
        pause
        exit /b 1
    )
)

REM --- 2. 端口检查与处理 ---
set "CURRENT_PORT=%DEFAULT_PORT%"
set "PORT_AVAILABLE=0"

:CheckPortLoop
echo.
echo %LOG_INFO%正在检查端口 !CURRENT_PORT! ...

set "PID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r /c:":!CURRENT_PORT! .*LISTENING"') do (
    set "PID=%%a"
)

if defined PID (
    echo %LOG_WARN%端口 !CURRENT_PORT! 被进程 PID=!PID! 占用
    
    REM 尝试终止进程
    echo %LOG_INFO%尝试终止进程 !PID!...
    taskkill /F /PID !PID! >nul 2>&1
    
    REM 等待一小会儿让系统释放资源
    timeout /t 1 /nobreak >nul
    
    REM 再次检查是否释放
    set "PID_CHECK="
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r /c:":!CURRENT_PORT! .*LISTENING"') do (
        set "PID_CHECK=%%a"
    )
    
    if defined PID_CHECK (
        echo %LOG_ERR%无法终止进程 !PID_CHECK! ^(可能是权限不足或系统进程^)
        echo %LOG_INFO%尝试切换到下一个端口...
        set /a CURRENT_PORT+=1
        goto :CheckPortLoop
    ) else (
        echo %LOG_INFO%端口 !CURRENT_PORT! 已成功释放
        set "PORT_AVAILABLE=1"
    )
) else (
    echo %LOG_INFO%端口 !CURRENT_PORT! 可用
    set "PORT_AVAILABLE=1"
)

if "!PORT_AVAILABLE!"=="1" (
    goto :StartServer
)

REM --- 3. 启动服务 ---
:StartServer
echo.
echo ========================================================
echo   后端服务准备就绪
echo   端口: !CURRENT_PORT!
echo   时间: %date% %time%
echo ========================================================
echo.

if "!CURRENT_PORT!" NEQ "%DEFAULT_PORT%" (
    echo [ATTENTION] 注意：服务运行在备用端口 !CURRENT_PORT!
    echo [ATTENTION] 请确保前端配置或 API 请求指向此端口！
    echo.
)

cd /d "%BACKEND_DIR%"

REM 启动 uvicorn
REM 使用 call 避免脚本在 uvicorn 退出后立即关闭窗口，方便查看日志
python -m uvicorn app.main:app --host 0.0.0.0 --port !CURRENT_PORT! --reload

if !ERRORLEVEL! NEQ 0 (
    echo.
    echo %LOG_ERR%后端服务异常退出，错误代码: !ERRORLEVEL!
    echo %LOG_INFO%按任意键退出...
    pause
    exit /b !ERRORLEVEL!
)

endlocal
