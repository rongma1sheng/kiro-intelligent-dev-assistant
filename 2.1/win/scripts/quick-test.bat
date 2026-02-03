@echo off
REM 快速测试脚本 - 运行核心测试

echo ========================================
echo 运行核心模块测试...
echo ========================================

set PYTHONIOENCODING=utf-8

pytest tests/unit/brain/soldier/ tests/integration/brain/ tests/e2e/ -v --tb=short --cov=src/brain/soldier --cov-report=term-missing

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 测试失败！
    exit /b 1
)

echo.
echo ✅ 所有测试通过！
exit /b 0
