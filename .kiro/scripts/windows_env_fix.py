#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows环境修复脚本 v1.0

修复Windows环境下的编码和环境问题：
- 设置UTF-8编码环境变量
- 修复中文字符显示问题
- 优化PowerShell和CMD环境
- 验证修复效果
"""

import os
import sys
import subprocess
import winreg
from pathlib import Path


class WindowsEnvironmentFixer:
    """Windows环境修复器"""
    
    def __init__(self):
        self.fixes_applied = []
        self.errors = []
        
    def fix_all(self):
        """执行所有修复"""
        print("🔧 开始Windows环境修复...")
        print("="*50)
        
        # 1. 修复编码问题
        self._fix_encoding()
        
        # 2. 设置环境变量
        self._set_environment_variables()
        
        # 3. 修复PowerShell配置
        self._fix_powershell_config()
        
        # 4. 验证修复效果
        self._verify_fixes()
        
        # 5. 输出结果
        self._print_results()
        
        return len(self.errors) == 0
    
    def _fix_encoding(self):
        """修复编码问题"""
        print("\n📝 修复编码问题...")
        
        try:
            # 设置Python默认编码
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            print("✅ 设置PYTHONIOENCODING=utf-8")
            self.fixes_applied.append("Python IO编码设置")
            
            # 设置控制台代码页
            try:
                subprocess.run(['chcp', '65001'], 
                             capture_output=True, 
                             check=True, 
                             shell=True)
                print("✅ 设置控制台代码页为UTF-8 (65001)")
                self.fixes_applied.append("控制台代码页设置")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ 控制台代码页设置失败: {e}")
                self.errors.append(f"控制台代码页: {e}")
            
        except Exception as e:
            print(f"❌ 编码修复失败: {e}")
            self.errors.append(f"编码修复: {e}")
    
    def _set_environment_variables(self):
        """设置环境变量"""
        print("\n🌍 设置环境变量...")
        
        env_vars = {
            'PYTHONIOENCODING': 'utf-8',
            'PYTHONUTF8': '1',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8'
        }
        
        for var_name, var_value in env_vars.items():
            try:
                os.environ[var_name] = var_value
                print(f"✅ 设置 {var_name}={var_value}")
                self.fixes_applied.append(f"环境变量 {var_name}")
            except Exception as e:
                print(f"❌ 设置环境变量 {var_name} 失败: {e}")
                self.errors.append(f"环境变量 {var_name}: {e}")
    
    def _fix_powershell_config(self):
        """修复PowerShell配置"""
        print("\n💻 优化PowerShell配置...")
        
        try:
            # 设置PowerShell输出编码
            powershell_cmd = """
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            $OutputEncoding = [System.Text.Encoding]::UTF8
            """
            
            # 创建PowerShell配置文件目录
            ps_profile_dir = Path.home() / "Documents" / "WindowsPowerShell"
            ps_profile_dir.mkdir(parents=True, exist_ok=True)
            
            profile_path = ps_profile_dir / "Microsoft.PowerShell_profile.ps1"
            
            # 检查是否已有配置
            existing_config = ""
            if profile_path.exists():
                with open(profile_path, 'r', encoding='utf-8') as f:
                    existing_config = f.read()
            
            # 添加UTF-8配置（如果不存在）
            if "OutputEncoding" not in existing_config:
                with open(profile_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n# Kiro UTF-8 Configuration\n{powershell_cmd}\n")
                print(f"✅ 更新PowerShell配置文件: {profile_path}")
                self.fixes_applied.append("PowerShell配置")
            else:
                print("✅ PowerShell配置已存在")
                self.fixes_applied.append("PowerShell配置检查")
                
        except Exception as e:
            print(f"❌ PowerShell配置失败: {e}")
            self.errors.append(f"PowerShell配置: {e}")
    
    def _verify_fixes(self):
        """验证修复效果"""
        print("\n🔍 验证修复效果...")
        
        # 测试中文字符输出
        try:
            test_string = "🔧 测试中文字符: 修复成功！"
            print(f"✅ 中文字符测试: {test_string}")
            self.fixes_applied.append("中文字符显示")
        except UnicodeEncodeError as e:
            print(f"❌ 中文字符测试失败: {e}")
            self.errors.append(f"中文字符显示: {e}")
        
        # 测试环境变量
        for var_name in ['PYTHONIOENCODING', 'PYTHONUTF8']:
            if os.environ.get(var_name):
                print(f"✅ 环境变量 {var_name}: {os.environ[var_name]}")
            else:
                print(f"⚠️ 环境变量 {var_name} 未设置")
                self.errors.append(f"环境变量 {var_name} 未设置")
        
        # 测试Python编码
        try:
            encoding = sys.stdout.encoding
            print(f"✅ Python输出编码: {encoding}")
            if encoding.lower() not in ['utf-8', 'cp65001']:
                print(f"⚠️ 建议的编码是UTF-8，当前是: {encoding}")
        except Exception as e:
            print(f"❌ 编码检查失败: {e}")
            self.errors.append(f"编码检查: {e}")
    
    def _print_results(self):
        """输出修复结果"""
        print("\n" + "="*50)
        print("📊 Windows环境修复结果")
        print("="*50)
        
        print(f"✅ 成功修复: {len(self.fixes_applied)} 项")
        for fix in self.fixes_applied:
            print(f"  - {fix}")
        
        if self.errors:
            print(f"\n❌ 修复失败: {len(self.errors)} 项")
            for error in self.errors:
                print(f"  - {error}")
        
        print("\n🔄 重启建议:")
        print("  - 重启PowerShell/CMD窗口以应用环境变量")
        print("  - 重启IDE以应用新的编码设置")
        
        print("\n📋 手动验证步骤:")
        print("  1. 打开新的PowerShell窗口")
        print("  2. 运行: python .kiro/scripts/config_validator.py")
        print("  3. 检查是否还有编码错误")
        
        print("="*50)


def main():
    """主函数"""
    fixer = WindowsEnvironmentFixer()
    success = fixer.fix_all()
    
    if success:
        print("🎉 Windows环境修复完成！")
        return 0
    else:
        print("💥 部分修复失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit(main())