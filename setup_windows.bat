@echo off
echo ========================================
echo    MIA 智能量化交易系统 - Windows安装
echo ========================================
echo.

echo 检查Python版本...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo 创建虚拟环境...
python -m venv venv
if %errorlevel% neq 0 (
    echo 错误: 虚拟环境创建失败
    pause
    exit /b 1
)

echo.
echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo.
echo 升级pip...
python -m pip install --upgrade pip

echo.
echo 安装项目依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 使用方法:
echo 1. 激活环境: venv\Scripts\activate
echo 2. 运行测试: python -m pytest tests/
echo 3. 启动系统: python src/main.py
echo.
echo 更多信息请查看 README.md
echo.
pause