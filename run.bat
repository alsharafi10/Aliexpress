@echo off
chcp 65001 >nul
echo ==========================================
echo    AI Fashion Architect 环境初始化与启动
echo ==========================================

if not exist venv (
    echo [1/3] 正在创建 Python 虚拟环境 (venv)...
    python -m venv venv
) else (
    echo [1/3] 虚拟环境已存在。
)

echo [2/3] 正在激活虚拟环境并检查依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [3/3] 启动主程序...
python main.py

echo.
echo 程序已退出。
pause
