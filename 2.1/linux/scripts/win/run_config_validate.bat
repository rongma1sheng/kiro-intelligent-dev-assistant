@echo off
chcp 65001 >nul
echo ============================================================
echo Kiro Config Validation (Windows)
echo ============================================================
echo.

cd /d "%~dp0..\.."
python scripts/validate_kiro_config.py

pause
