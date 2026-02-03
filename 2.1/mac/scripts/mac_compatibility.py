#!/usr/bin/env python3
"""
Mac兼容性适配脚本
为硅谷LLM反漂移协同系统提供Mac平台支持

作者: 硅谷项目开发经理
版本: 1.0.0
日期: 2026-02-01
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MacCompatibilityManager:
    """Mac兼容性管理器"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_mac = self.system == "Darwin"
        self.is_apple_silicon = self._detect_apple_silicon()
        self.homebrew_prefix = self._get_homebrew_prefix()
        
    def _detect_apple_silicon(self) -> bool:
        """检测是否为Apple Silicon芯片"""
        if not self.is_mac:
            return False
        try:
            result = subprocess.run(
                ["uname", "-m"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.stdout.strip() == "arm64"
        except Exception:
            return False
    
    def _get_homebrew_prefix(self) -> str:
        """获取Homebrew安装前缀"""
        if not self.is_mac:
            return ""
        
        if self.is_apple_silicon:
            return "/opt/homebrew"
        else:
            return "/usr/local"
    
    def check_dependencies(self) -> Dict[str, bool]:
        """检查Mac系统依赖"""
        dependencies = {
            "python3": self._check_python(),
            "git": self._check_git(),
            "homebrew": self._check_homebrew(),
            "xcode_tools": self._check_xcode_tools()
        }
        return dependencies
    
    def _check_python(self) -> bool:
        """检查Python安装"""
        try:
            result = subprocess.run(
                ["python3", "--version"], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_git(self) -> bool:
        """检查Git安装"""
        try:
            result = subprocess.run(
                ["git", "--version"], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_homebrew(self) -> bool:
        """检查Homebrew安装"""
        try:
            result = subprocess.run(
                ["brew", "--version"], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_xcode_tools(self) -> bool:
        """检查Xcode命令行工具"""
        try:
            result = subprocess.run(
                ["xcode-select", "-p"], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def install_dependencies(self) -> bool:
        """安装Mac系统依赖"""
        if not self.is_mac:
            print("❌ 当前系统不是macOS")
            return False
        
        print("🍎 开始安装Mac系统依赖...")
        
        # 安装Xcode命令行工具
        if not self._check_xcode_tools():
            print("📦 安装Xcode命令行工具...")
            try:
                subprocess.run(
                    ["xcode-select", "--install"], 
                    check=True, 
                    timeout=300
                )
                print("✅ Xcode命令行工具安装完成")
            except Exception as e:
                print(f"❌ Xcode命令行工具安装失败: {e}")
                return False
        
        # 安装Homebrew
        if not self._check_homebrew():
            print("🍺 安装Homebrew...")
            try:
                install_script = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                subprocess.run(install_script, shell=True, check=True, timeout=600)
                print("✅ Homebrew安装完成")
            except Exception as e:
                print(f"❌ Homebrew安装失败: {e}")
                return False
        
        # 安装Python开发工具
        brew_packages = [
            "python@3.11",
            "git",
            "node",
            "redis",
            "postgresql@15"
        ]
        
        for package in brew_packages:
            print(f"📦 安装 {package}...")
            try:
                subprocess.run(
                    ["brew", "install", package], 
                    check=True, 
                    timeout=300
                )
                print(f"✅ {package} 安装完成")
            except Exception as e:
                print(f"❌ {package} 安装失败: {e}")
        
        return True
    
    def adapt_scripts(self) -> bool:
        """适配脚本文件"""
        if not self.is_mac:
            return True
        
        print("🔧 开始适配Mac脚本...")
        
        script_adaptations = [
            self._adapt_quality_gate_scripts(),
            self._adapt_test_scripts(),
            self._adapt_monitoring_scripts()
        ]
        
        return all(script_adaptations)
    
    def _adapt_quality_gate_scripts(self) -> bool:
        """适配质量门禁脚本"""
        try:
            # 创建Mac专用的质量门禁脚本
            mac_script_content = '''#!/usr/bin/env python3
"""
Mac适配的质量门禁脚本
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command_mac(cmd: str, timeout: int = 300) -> tuple:
    """在Mac上运行命令"""
    try:
        # 使用zsh作为默认shell (macOS Catalina+)
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            executable="/bin/zsh"  # Mac默认shell
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_mac_environment():
    """检查Mac环境"""
    checks = {
        "python3": run_command_mac("python3 --version")[0] == 0,
        "pip3": run_command_mac("pip3 --version")[0] == 0,
        "git": run_command_mac("git --version")[0] == 0,
        "homebrew": run_command_mac("brew --version")[0] == 0
    }
    
    print("🍎 Mac环境检查:")
    for tool, status in checks.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {tool}")
    
    return all(checks.values())

if __name__ == "__main__":
    if not check_mac_environment():
        print("❌ Mac环境检查失败，请先安装必要依赖")
        sys.exit(1)
    
    print("✅ Mac环境检查通过")
'''
            
            mac_script_path = Path("scripts/mac_quality_gate.py")
            with open(mac_script_path, "w", encoding="utf-8") as f:
                f.write(mac_script_content)
            
            # 设置执行权限
            os.chmod(mac_script_path, 0o755)
            
            print("✅ Mac质量门禁脚本适配完成")
            return True
            
        except Exception as e:
            print(f"❌ Mac质量门禁脚本适配失败: {e}")
            return False
    
    def _adapt_test_scripts(self) -> bool:
        """适配测试脚本"""
        try:
            # 创建Mac专用测试配置
            mac_test_config = {
                "test_command": "python3 -m pytest",
                "coverage_command": "python3 -m coverage",
                "lint_command": "python3 -m pylint",
                "format_command": "python3 -m black",
                "shell": "/bin/zsh",
                "timeout": 600,
                "environment": {
                    "PYTHONPATH": "src:tests",
                    "PYTEST_CURRENT_TEST": "1"
                }
            }
            
            import json
            config_path = Path("config/mac_test_config.json")
            config_path.parent.mkdir(exist_ok=True)
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(mac_test_config, f, indent=2, ensure_ascii=False)
            
            print("✅ Mac测试脚本适配完成")
            return True
            
        except Exception as e:
            print(f"❌ Mac测试脚本适配失败: {e}")
            return False
    
    def _adapt_monitoring_scripts(self) -> bool:
        """适配监控脚本"""
        try:
            # 创建Mac专用监控配置
            mac_monitoring_script = '''#!/usr/bin/env python3
"""
Mac系统监控脚本
"""

import psutil
import subprocess
import json
from datetime import datetime

def get_mac_system_info():
    """获取Mac系统信息"""
    try:
        # 获取CPU信息
        cpu_info = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True
        ).stdout.strip()
        
        # 获取内存信息
        memory_info = psutil.virtual_memory()
        
        # 获取磁盘信息
        disk_info = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "macOS",
            "cpu": cpu_info,
            "memory": {
                "total": memory_info.total,
                "available": memory_info.available,
                "percent": memory_info.percent
            },
            "disk": {
                "total": disk_info.total,
                "free": disk_info.free,
                "percent": (disk_info.used / disk_info.total) * 100
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    info = get_mac_system_info()
    print(json.dumps(info, indent=2, ensure_ascii=False))
'''
            
            monitoring_script_path = Path("scripts/mac_system_monitor.py")
            with open(monitoring_script_path, "w", encoding="utf-8") as f:
                f.write(mac_monitoring_script)
            
            os.chmod(monitoring_script_path, 0o755)
            
            print("✅ Mac监控脚本适配完成")
            return True
            
        except Exception as e:
            print(f"❌ Mac监控脚本适配失败: {e}")
            return False
    
    def create_mac_setup_script(self) -> bool:
        """创建Mac一键设置脚本"""
        try:
            setup_script = '''#!/bin/bash
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
find scripts -name "*.py" -exec chmod +x {} \\;
find scripts -name "*.sh" -exec chmod +x {} \\;

echo "✅ Mac环境设置完成！"
echo ""
echo "🚀 下一步操作："
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 运行测试: python -m pytest tests/"
echo "3. 启动系统: python scripts/start_system.py"
echo ""
echo "📚 更多信息请查看 README.md"
'''
            
            setup_script_path = Path("setup_mac.sh")
            with open(setup_script_path, "w", encoding="utf-8") as f:
                f.write(setup_script)
            
            os.chmod(setup_script_path, 0o755)
            
            print("✅ Mac一键设置脚本创建完成")
            return True
            
        except Exception as e:
            print(f"❌ Mac一键设置脚本创建失败: {e}")
            return False
    
    def generate_compatibility_report(self) -> Dict:
        """生成兼容性报告"""
        from datetime import datetime
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "platform": platform.platform(),
                "system": self.system,
                "is_mac": self.is_mac,
                "is_apple_silicon": self.is_apple_silicon,
                "homebrew_prefix": self.homebrew_prefix
            },
            "dependencies": self.check_dependencies() if self.is_mac else {},
            "adaptations_completed": [
                "mac_quality_gate.py",
                "mac_test_config.json", 
                "mac_system_monitor.py",
                "setup_mac.sh"
            ],
            "recommendations": []
        }
        
        if self.is_mac:
            if not all(report["dependencies"].values()):
                report["recommendations"].append("运行 ./setup_mac.sh 安装缺失依赖")
            
            if self.is_apple_silicon:
                report["recommendations"].append("Apple Silicon芯片已优化，性能更佳")
            
            report["recommendations"].append("使用 source venv/bin/activate 激活虚拟环境")
        else:
            report["recommendations"].append("当前系统非macOS，Mac适配功能不适用")
        
        return report


def main():
    """主函数"""
    print("🍎 Mac兼容性适配工具")
    print("=" * 50)
    
    manager = MacCompatibilityManager()
    
    if not manager.is_mac:
        print("ℹ️ 当前系统不是macOS，将创建Mac适配文件供Mac用户使用")
    else:
        print(f"✅ 检测到macOS系统")
        if manager.is_apple_silicon:
            print("🔧 Apple Silicon芯片已检测")
        else:
            print("🔧 Intel芯片已检测")
    
    # 执行适配
    success = True
    success &= manager.adapt_scripts()
    success &= manager.create_mac_setup_script()
    
    # 生成报告
    report = manager.generate_compatibility_report()
    
    # 保存报告
    report_path = Path("reports/mac_compatibility_report.json")
    report_path.parent.mkdir(exist_ok=True)
    
    import json
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 兼容性报告已保存到: {report_path}")
    
    if success:
        print("\n✅ Mac兼容性适配完成！")
        if manager.is_mac:
            print("\n🚀 Mac用户可以运行以下命令开始使用:")
            print("   ./setup_mac.sh")
        else:
            print("\n📦 Mac适配文件已创建，Mac用户可以使用这些文件")
    else:
        print("\n❌ Mac兼容性适配过程中出现错误")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())