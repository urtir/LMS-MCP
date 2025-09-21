@echo off
echo ========================================
echo Starting LMS MCP Webapp with Admin Panel
echo ========================================

cd /d "c:\Users\risqu\Desktop\LMS MCP"

echo Setting up environment...
set FLASK_DEBUG=false
set FLASK_HOST=127.0.0.1
set FLASK_PORT=5000

echo.
echo Starting webapp server...
echo Admin panel will be available at:
echo http://127.0.0.1:5000/admin
echo.
echo Note: Login as 'admin' user to access admin panel
echo.

python -m src.webapp.webapp_chatbot

pause