@echo off
cd /d "%~dp0"
if "%~1"=="" goto :usage
python fix_export.py "%~1" || py fix_export.py "%~1"
pause
exit /b
:usage
echo Drag the broken exported HTML file onto this file's icon.
pause
