@echo off
echo ================================================================
echo             AISOC MCP - PDF Guide Generator
echo ================================================================
echo.

echo 🚀 Installing PDF generation dependencies...
pip install -r requirements-pdf.txt

echo.
echo 📖 Generating HTML guides...
python scripts/generate_html_guide.py

echo.
echo ✅ Generation complete!
echo.
echo 📋 Files generated in docs/pdf/ directory:
echo    - AISOC_MCP_Complete_Guide_YYYYMMDD.html
echo    - AISOC_MCP_Quick_Reference_YYYYMMDD.html
echo.
echo 💡 To convert to PDF:
echo    1. Open HTML files in browser
echo    2. Press Ctrl+P
echo    3. Save as PDF
echo.
pause