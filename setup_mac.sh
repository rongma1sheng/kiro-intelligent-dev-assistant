#!/bin/bash
# Mac一键设置脚本 - 硅谷LLM反漂移协同系统
# 版本: 1.0.0
# 日期: 2026-02-01

set -e

echo "🍎 开始Mac环境设置..."

# 检查是否为Mac系统
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ 此脚本仅适用于macOS系统"
    exit 1
fi

# 检测芯片架构
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo "🔧 检测到Apple Silicon芯片"
    HOMEBREW_PREFIX="/opt/homebrew"
else
    echo "🔧 检测到Intel芯片"
    HOMEBREW_PREFIX="/usr/local"
fi

# 安装Xcode命令行工具
if ! command -v git &> /dev/null; then
    echo "📦 安装Xcode命令行工具..."
    xcode-select --install
    echo "⏳ 请完成Xcode命令行工具安装后继续..."
    read -p "按Enter键继续..."
fi

# 安装Homebrew
if ! command -v brew &> /dev/null; then
    echo "🍺 安装Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # 添加Homebrew到PATH
    echo "export PATH=$HOMEBREW_PREFIX/bin:$PATH" >> ~/.zshrc
    export PATH=$HOMEBREW_PREFIX/bin:$PATH
fi

# 更新Homebrew
echo "🔄 更新Homebrew..."
brew update

# 安装必要软件包
echo "📦 安装必要软件包..."
brew install python@3.11 git node redis postgresql@15

# 安装Python包管理工具
echo "🐍 安装Python包管理工具..."
pip3 install --upgrade pip
pip3 install virtualenv poetry

# 创建Python虚拟环境
echo "🏗️ 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装项目依赖
if [ -f "requirements.txt" ]; then
    echo "📋 安装项目依赖..."
    pip install -r requirements.txt
fi

if [ -f "requirements-dev.txt" ]; then
    echo "🛠️ 安装开发依赖..."
    pip install -r requirements-dev.txt
fi

# 设置Git配置
echo "⚙️ 配置Git..."
git config --global init.defaultBranch main
git config --global core.autocrlf input

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p logs reports exports data/memory

# 设置权限
echo "🔐 设置文件权限..."
find scripts -name "*.py" -exec chmod +x {} \;
find scripts -name "*.sh" -exec chmod +x {} \;

echo "✅ Mac环境设置完成！"
echo ""
echo "🚀 下一步操作："
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 运行测试: python -m pytest tests/"
echo "3. 启动系统: python scripts/start_system.py"
echo ""
echo "📚 更多信息请查看 README.md"
