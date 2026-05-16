@echo off
start "Backend" cmd /c "cd /d backend && python main.py"
start "Frontend" cmd /c "cd /d heartbot-frontend && npm run dev"
start "Redis" cmd /c "cd /d D:/Redis && .\run.bat"