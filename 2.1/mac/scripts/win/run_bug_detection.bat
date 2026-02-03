@echo off
chcp 65001 >nul
echo ============================================================
echo Bug Detection and Fix (Windows)
echo ============================================================
echo.

cd /d "%~dp0..\.."

if "%1"=="" (
    echo Usage:
    echo   run_bug_detection.bat scan    - Scan bugs
    echo   run_bug_detection.bat fix     - Auto fix
    echo   run_bug_detection.bat cycle   - Full fix cycle
    echo   run_bug_detection.bat report  - Generate report
    echo.
    set /p CMD="Enter command (scan/fix/cycle/report): "
) else (
    set CMD=%1
)

python scripts/auto_bug_detection.py %CMD% src

pause
