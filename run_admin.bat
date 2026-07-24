@echo off
:: 以管理员身份运行 GitHub 加速器
:: 右键此文件 -> 以管理员身份运行

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: 获取脚本所在目录
cd /d "%~dp0"

:: 运行程序
if exist "dist\GitHub加速器.exe" (
    echo 启动 EXE 版本...
    start "" "dist\GitHub加速器.exe"
) else if exist "main.py" (
    echo 启动 Python 版本...
    python main.py --gui
) else (
    echo 错误: 未找到程序文件
    pause
)
