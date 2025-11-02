@echo off
echo ============================================================
echo          AISOC MCP - PDF Guide Generator (Batch)
echo ============================================================
echo.

cd /d "c:\Users\risqu\Desktop\WAZUH MCP"

echo [1] Generating HTML Guide (Indonesian)...
python scripts/generate_html_guide.py
if %errorlevel% neq 0 (
    echo ERROR: HTML generation failed!
    pause
    exit /b 1
)

echo.
echo [2] Generating PDF with ReportLab (Indonesian)...
python scripts/generate_pdf_id.py
if %errorlevel% neq 0 (
    echo ERROR: PDF generation with ReportLab failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo                   GENERATION COMPLETE!
echo ============================================================
echo.
echo Files generated in: docs\pdf\
echo.
echo HTML Files:
dir /b docs\pdf\*.html 2>nul
echo.
echo PDF Files:
dir /b docs\pdf\*.pdf 2>nul
echo.
echo All documents are ready for use!
echo ============================================================

pause