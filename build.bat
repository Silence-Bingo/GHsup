@echo off
echo ========================================
echo   GitHub 加速器 - 打包脚本
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 安装依赖失败
    pause
    exit /b 1
)

REM 打包
echo.
echo [2/3] 打包为 EXE...
pyinstaller --onefile --windowed --name "GitHub加速器" --icon=NONE main.py
if errorlevel 1 (
    echo 错误: 打包失败
    pause
    exit /b 1
)

echo.
echo [3/3] 完成！
echo.
echo EXE 文件位于: dist\GitHub加速器.exe
echo.
echo 注意事项:
echo   1. 运行时需要管理员权限
echo   2. 首次运行会创建配置文件: %USERPROFILE%\.github-accelerator\config.json
echo   3. Hosts 文件备份在: C:\Windows\System32\drivers\etc\hosts_backups\
echo.
pause
