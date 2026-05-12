@echo off
echo Starting FastAPI server with hot reload...
echo.

:: 设置环境变量（可选）
set HOST=0.0.0.0
set PORT=8000
set RELOAD=true

:: 启动服务器
python run.py

pause