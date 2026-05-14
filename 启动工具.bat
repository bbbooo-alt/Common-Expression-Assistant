@echo off
chcp 65001 >nul
echo 正在启动快捷键输入工具...
python "%~dp0hotkey_typer.py"
if errorlevel 1 (
    echo.
    echo [错误] 程序运行失败，请检查是否已安装依赖库
    echo 运行 install_requirements.bat 安装依赖
    pause
)
