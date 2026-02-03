#!/bin/bash

echo "========================================"
echo "   MIA 智能量化交易系统 - macOS安装"
echo "========================================"
echo

echo "检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    echo "安装方法: brew install python3"
    echo "或访问: https://www.python.org/downloads/"
    exit 1
fi

python3 --version

echo
echo "创建虚拟环境..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "错误: 虚拟环境创建失败"
    exit 1
fi

echo
echo "激活虚拟环境..."
source venv/bin/activate

echo
echo "升级pip..."
python -m pip install --upgrade pip

echo
echo "安装项目依赖..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi

echo
echo "========================================"
echo "    安装完成！"
echo "========================================"
echo
echo "使用方法:"
echo "1. 激活环境: source venv/bin/activate"
echo "2. 运行测试: python -m pytest tests/"
echo "3. 启动系统: python src/main.py"
echo
echo "更多信息请查看 README.md"
echo