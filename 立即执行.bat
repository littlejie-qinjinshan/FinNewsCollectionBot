@echo off
cd /d "%~dp0"
echo ========================================
echo 财经新闻采集机器人 - 立即执行
echo ========================================
echo.
echo 正在检查 Python 环境...
if not exist "..\.venv\Scripts\python.exe" (
    echo [错误] 找不到 Python 虚拟环境！
    pause
    exit /b 1
)
echo [OK] 找到 Python 环境
echo.
echo 正在执行任务...
echo ========================================
echo.
..\.venv\Scripts\python.exe financebot.py --now
echo.
echo ========================================
echo 任务执行完毕
echo ========================================
pause
