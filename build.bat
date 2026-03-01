@echo off
chcp 65001 >nul
echo ====================================
echo Building Finance System Executable
echo ====================================
echo.
echo 1. Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo 2. Generating .exe using PyInstaller...
rem --noconfirm: Overwrite existing build
rem --onefile: Create a single executable file
rem --windowed: Do not show a console window
rem --icon: Specify a program icon (optional, you can add an icon.ico here if you have one)
pyinstaller --noconfirm --onefile --windowed finance_system.py

echo.
echo ====================================
echo Done! The executable is located in the "dist" folder.
echo You can upload the generated 'dist\finance_system.exe' to GitHub.
echo ====================================
pause
