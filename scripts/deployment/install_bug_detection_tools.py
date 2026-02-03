#!/usr/bin/env python
"""安装 Bug 检测工具

一键安装所有必需的 Python 包和 VS Code 扩展
"""

import subprocess
import sys


def install_python_packages():
    """安装 Python 包"""
    packages = [
        "pylint",
        "black",
        "isort",
        "bandit",
        "mypy",
        "pytest",
        "pytest-cov",
    ]
    
    print("📦 安装 Python 包...")
    for package in packages:
        print(f"  安装 {package}...")
        subprocess.run([sys.executable, "-m", "pip", "install", package, "-q"], check=False)
    
    print("✅ Python 包安装完成")


def install_vscode_extensions():
    """安装 VS Code 扩展"""
    extensions = [
        "sonarsource.sonarlint-vscode",
        "ms-python.python",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "ms-python.isort",
    ]
    
    print("\n📦 安装 VS Code 扩展...")
    for ext in extensions:
        print(f"  安装 {ext}...")
        subprocess.run(["code", "--install-extension", ext, "--force"], check=False, capture_output=True)
    
    print("✅ VS Code 扩展安装完成")
    print("\n⚠️ 注意: CodeRabbit 和 GitHub Copilot 需要手动安装和配置")
    print("  - CodeRabbit: https://coderabbit.ai/")
    print("  - GitHub Copilot: 需要 GitHub Copilot 订阅")


def main():
    print("=" * 60)
    print("🔧 Bug 检测工具安装程序")
    print("=" * 60 + "\n")
    
    install_python_packages()
    install_vscode_extensions()
    
    print("\n" + "=" * 60)
    print("✅ 安装完成！")
    print("=" * 60)
    print("\n使用方法:")
    print("  python scripts/auto_bug_detection.py scan     # 扫描")
    print("  python scripts/auto_bug_detection.py fix      # 修复")
    print("  python scripts/auto_bug_detection.py cycle    # 循环")
    print("  python scripts/auto_bug_detection.py security # 安全扫描")


if __name__ == "__main__":
    main()
