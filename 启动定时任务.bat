@echo off
cd /d "%~dp0"
echo ========================================
echo 财经新闻采集机器人 - 定时任务模式
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
echo 提示：
echo   - 程序将立即执行一次任务
echo   - 之后每天定时自动执行
echo   - 按 Ctrl+C 可退出程序
echo.
echo ========================================
echo.
..\.venv\Scripts\python.exe financebot.py
echo.
echo ========================================
echo 程序已退出
echo ========================================
pause
