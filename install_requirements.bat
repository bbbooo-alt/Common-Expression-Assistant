@echo off
chcp 65001 >nul
echo ==========================================
echo     快捷键输入工具 - 依赖安装脚本
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.7 或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检测到 Python，正在安装依赖库...
echo.

echo 安装 pynput...
pip install pynput -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [警告] pynput 安装失败，尝试使用默认源...
    pip install pynput
)

echo.
echo 安装 pyautogui...
pip install pyautogui -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [警告] pyautogui 安装失败，尝试使用默认源...
    pip install pyautogui
)

echo.
echo 安装 pywin32...
pip install pywin32 -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [警告] pywin32 安装失败，尝试使用默认源...
    pip install pywin32
)

echo.
echo ==========================================
echo     安装完成！
echo ==========================================
echo.
echo 现在可以运行 hotkey_typer.py 了
echo.
pause
