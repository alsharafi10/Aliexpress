@echo off
chcp 65001 >nul
echo Building Finance System Debug Executable
pyinstaller --noconfirm --onefile finance_system.py
echo Done.
pause
