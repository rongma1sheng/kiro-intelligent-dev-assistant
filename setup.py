#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIA 智能量化交易系统 - 跨平台安装脚本
支持 Windows, macOS, Linux
"""

import subprocess
import sys
import platform
import os
from pathlib import Path

def print_banner():
    """打印安装横幅"""
    print("=" * 50)
    print("   MIA 智能量化交易系统 - 跨平台安装")
    print("=" * 50)
    print()

def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print("请访问 https://www.python.org/downloads/ 下载最新版本")
        return False
    
    print("✅ Python版本检查通过")
    return True

def create_virtual_environment():
    """创建虚拟环境"""
    print("\n创建虚拟环境...")
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ 虚拟环境创建成功")
        return True
    except subprocess.CalledProcessError:
        print("❌ 错误: 虚拟环境创建失败")
        return False

def get_activation_command():
    """获取虚拟环境激活命令"""
    system = platform.system().lower()
    
    if system == "windows":
        return "venv\\Scripts\\activate"
    else:  # macOS, Linux
        return "source venv/bin/activate"

def get_pip_path():
    """获取pip路径"""
    system = platform.system().lower()
    
    if system == "windows":
        return Path("venv") / "Scripts" / "pip"
    else:  # macOS, Linux
        return Path("venv") / "bin" / "pip"

def install_dependencies():
    """安装项目依赖"""
    print("\n安装项目依赖...")
    
    pip_path = get_pip_path()
    
    try:
        # 升级pip
        print("升级pip...")
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
        
        # 安装依赖
        print("安装requirements.txt中的依赖...")
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        
        print("✅ 依赖安装成功")
        return True
    except subprocess.CalledProcessError:
        print("❌ 错误: 依赖安装失败")
        return False

def print_usage_instructions():
    """打印使用说明"""
    system = platform.system().lower()
    activation_cmd = get_activation_command()
    
    print("\n" + "=" * 50)
    print("    安装完成！")
    print("=" * 50)
    print()
    print("使用方法:")
    print(f"1. 激活环境: {activation_cmd}")
    print("2. 运行测试: python -m pytest tests/")
    print("3. 启动系统: python src/main.py")
    print()
    print("配置文件:")
    print("- 基础配置: config/")
    print("- 平台配置: 3.0/base/, 3.0/win/, 3.0/mac/, 3.0/linux/")
    print()
    print("更多信息请查看 README.md")
    print()

def main():
    """主安装流程"""
    print_banner()
    
    # 检查Python版本
    if not check_python_version():
        return 1
    
    # 创建虚拟环境
    if not create_virtual_environment():
        return 1
    
    # 安装依赖
    if not install_dependencies():
        return 1
    
    # 打印使用说明
    print_usage_instructions()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 安装过程中发生错误: {e}")
        sys.exit(1)