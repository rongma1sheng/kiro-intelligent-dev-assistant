@echo off
chcp 65001 >nul
echo ============================================================
echo Complete Quality Check (Windows)
echo ============================================================
echo.

cd /d "%~dp0..\.."

echo [1/4] Kiro Config Validation...
python scripts/validate_kiro_config.py
if %ERRORLEVEL% NEQ 0 goto :failed

echo.
echo [2/4] Unified Quality Check...
python scripts/unified_quality_system.py check
if %ERRORLEVEL% NEQ 0 goto :failed

echo.
echo [3/4] Quality Gate...
python scripts/quality_gate.py src
if %ERRORLEVEL% NEQ 0 goto :failed

echo.
echo [4/4] Deploy Test...
python scripts/deploy_test.py full
if %ERRORLEVEL% NEQ 0 goto :failed

echo.
echo ============================================================
echo [SUCCESS] All checks passed!
echo ============================================================
goto :end

:failed
echo.
echo ============================================================
echo [FAILED] Check failed, see errors above
echo ============================================================

:end
pause
