@echo off
echo Starting AI Survey Assistant...
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境并运行
venv\Scripts\python.exe run_all.py

pause

