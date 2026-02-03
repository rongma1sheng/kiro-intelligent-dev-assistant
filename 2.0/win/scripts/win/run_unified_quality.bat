@echo off
chcp 65001 >nul
echo ============================================================
echo Unified Quality System (Windows)
echo ============================================================
echo.

cd /d "%~dp0..\.."

if "%1"=="" (
    echo Usage:
    echo   run_unified_quality.bat check   - Full quality check
    echo   run_unified_quality.bat prd     - PRD parsing
    echo   run_unified_quality.bat config  - Config validation
    echo   run_unified_quality.bat gate    - Quality gate
    echo.
    set /p CMD="Enter command (check/prd/config/gate): "
) else (
    set CMD=%1
)

python scripts/unified_quality_system.py %CMD%

pause
