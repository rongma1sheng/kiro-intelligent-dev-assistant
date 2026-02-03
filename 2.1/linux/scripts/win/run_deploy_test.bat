@echo off
chcp 65001 >nul
echo ============================================================
echo Deploy Test (Windows)
echo ============================================================
echo.

cd /d "%~dp0..\.."
python scripts/deploy_test.py full

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Deploy test passed, ready to deploy
) else (
    echo.
    echo [FAILED] Deploy test failed, fix issues first
)

pause
