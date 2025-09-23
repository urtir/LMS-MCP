@echo off
echo ========================================
echo Starting LMS MCP Webapp with Admin Panel
echo ========================================

cd /d "c:\Users\risqu\Desktop\LMS MCP"

echo All configuration loaded from config.json
echo No hardcoded environment variables used

echo.
echo Starting webapp server...
echo Admin panel will be available at config-defined host:port/admin
echo Check config.json for flask.FLASK_HOST and flask.FLASK_PORT values
echo.
echo Note: Login as 'admin' user to access admin panel
echo.

python -m src.webapp.webapp_chatbot

pause