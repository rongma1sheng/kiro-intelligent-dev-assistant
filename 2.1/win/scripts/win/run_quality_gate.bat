@echo off
chcp 65001 >nul
echo ============================================================
echo Quality Gate Check (Windows)
echo ============================================================
echo.

cd /d "%~dp0..\.."
python scripts/quality_gate.py src

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Quality Gate PASSED
) else (
    echo.
    echo [FAILED] Quality Gate FAILED, check report
)

pause
