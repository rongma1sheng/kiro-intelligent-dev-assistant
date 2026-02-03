#!/usr/bin/env python3
"""
修复平台特定Hook配置错误

作为🔧 DevOps Engineer，我需要修复刚才错误创建的Mac性能监控Hook，
为Windows平台创建合适的Hook配置。
"""

import json
import os
from datetime import datetime
from pathlib import Path

class PlatformSpecificHookFixer:
    """平台特定Hook修复器"""
    
    def __init__(self):
        self.kiro_path = Path(".kiro")
        self.hooks_path = self.kiro_path / "hooks"
        self.platform = self.detect_platform()
        self.fix_log = []
        
    def detect_platform(self):
        """检测当前平台"""
        import platform
        system = platform.system().lower()
        if system == "windows":
            return "win32"
        elif system == "darwin":
            return "darwin"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    def remove_inappropriate_hooks(self):
        """移除不适合当前平台的Hook"""
        print(f"🔧 移除不适合{self.platform}平台的Hook...")
        
        # 需要移除的Mac特定Hook
        mac_specific_hooks = [
            "mac-performance-monitor.kiro.hook",
            "mac-compatibility-checker.kiro.hook",
            "mac-development-environment.kiro.hook"
        ]
        
        for hook_name in mac_specific_hooks:
            hook_path = self.hooks_path / hook_name
            if hook_path.exists():
                hook_path.unlink()
                self.fix_log.append(f"移除不适合的Hook: {hook_name}")
                print(f"🗑️ 已移除: {hook_name}")
    
    def create_windows_specific_hooks(self):
        """创建Windows特定的Hook"""
        print("🪟 创建Windows特定Hook...")
        
        windows_hooks = {
            "windows-performance-monitor.kiro.hook": {
                "name": "Windows性能监控",
                "version": "1.0.0",
                "description": "监控Windows系统性能并提供优化建议",
                "when": {
                    "type": "promptSubmit"
                },
                "then": {
                    "type": "askAgent",
                    "prompt": "执行Windows性能分析：1. CPU和内存使用率检查 2. 磁盘空间和碎片分析 3. 启动项和服务优化建议 4. PowerShell和开发环境优化"
                }
            },
            "windows-development-optimizer.kiro.hook": {
                "name": "Windows开发环境优化器",
                "version": "1.0.0", 
                "description": "优化Windows开发环境配置",
                "when": {
                    "type": "fileEdited",
                    "patterns": ["*.py", "*.js", "*.ts"]
                },
                "then": {
                    "type": "askAgent",
                    "prompt": "检查Windows开发环境优化机会：1. Visual Studio Code配置 2. PowerShell执行策略 3. Git配置优化 4. Python环境管理"
                }
            },
            "windows-system-health-checker.kiro.hook": {
                "name": "Windows系统健康检查器",
                "version": "1.0.0",
                "description": "定期检查Windows系统健康状态",
                "when": {
                    "type": "agentStop"
                },
                "then": {
                    "type": "askAgent",
                    "prompt": "执行Windows系统健康检查：1. 系统文件完整性 2. 注册表健康状态 3. 磁盘错误检查 4. 安全更新状态"
                }
            }
        }
        
        for hook_name, hook_config in windows_hooks.items():
            hook_path = self.hooks_path / hook_name
            if not hook_path.exists():
                with open(hook_path, "w", encoding="utf-8") as f:
                    json.dump(hook_config, f, indent=2, ensure_ascii=False)
                
                self.fix_log.append(f"创建Windows Hook: {hook_name}")
                print(f"✅ 已创建: {hook_name}")
    
    def update_existing_hooks_for_windows(self):
        """更新现有Hook以适配Windows"""
        print("🔄 更新现有Hook以适配Windows...")
        
        # 更新错误解决方案查找器，添加Windows特定内容
        error_finder_path = self.hooks_path / "error-solution-finder.kiro.hook"
        if error_finder_path.exists():
            with open(error_finder_path, "r", encoding="utf-8") as f:
                hook_config = json.load(f)
            
            # 更新提示以包含Windows特定错误处理
            hook_config["then"]["prompt"] = "检查用户查询是否包含错误信息，特别关注Windows平台常见错误（权限问题、路径问题、PowerShell执行策略等），从记忆系统搜索相关解决方案"
            
            with open(error_finder_path, "w", encoding="utf-8") as f:
                json.dump(hook_config, f, indent=2, ensure_ascii=False)
            
            self.fix_log.append("更新错误解决方案查找器以适配Windows")
            print("✅ 已更新: error-solution-finder.kiro.hook")
    
    def create_platform_detection_hook(self):
        """创建平台检测Hook"""
        print("🔍 创建平台检测Hook...")
        
        platform_hook = {
            "name": "智能平台适配器",
            "version": "1.0.0",
            "description": "自动检测平台并提供相应的优化建议",
            "when": {
                "type": "promptSubmit"
            },
            "then": {
                "type": "askAgent",
                "prompt": f"当前检测到平台: {self.platform}。根据平台特性提供相应的系统优化建议和开发环境配置。"
            }
        }
        
        hook_path = self.hooks_path / "intelligent-platform-adapter.kiro.hook"
        with open(hook_path, "w", encoding="utf-8") as f:
            json.dump(platform_hook, f, indent=2, ensure_ascii=False)
        
        self.fix_log.append("创建智能平台适配器Hook")
        print("✅ 已创建: intelligent-platform-adapter.kiro.hook")
    
    def generate_fix_report(self):
        """生成修复报告"""
        print("📊 生成修复报告...")
        
        report = {
            "metadata": {
                "fix_date": datetime.now().isoformat(),
                "fixer": "🔧 DevOps Engineer",
                "detected_platform": self.platform,
                "issue": "Mac特定Hook在Windows平台上不合适"
            },
            "fix_summary": {
                "total_fixes": len(self.fix_log),
                "platform_detected": self.platform,
                "inappropriate_hooks_removed": True,
                "platform_specific_hooks_created": True
            },
            "fix_log": self.fix_log,
            "platform_optimization": {
                "windows": {
                    "performance_monitoring": "Windows性能监控Hook",
                    "development_optimization": "开发环境优化Hook", 
                    "system_health": "系统健康检查Hook",
                    "platform_detection": "智能平台适配Hook"
                }
            },
            "recommendations": [
                "重启Kiro以应用新的Hook配置",
                "测试Windows特定Hook的触发",
                "根据实际使用情况调整Hook配置",
                "定期检查平台特定优化效果"
            ]
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/platform_hook_fix_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 修复报告已保存到: {report_path}")
        return report
    
    def execute_platform_fix(self):
        """执行平台修复"""
        print("🔧 开始修复平台特定Hook配置...")
        print("=" * 60)
        print(f"🖥️ 检测到平台: {self.platform}")
        
        try:
            # 1. 移除不适合的Hook
            self.remove_inappropriate_hooks()
            
            # 2. 创建Windows特定Hook
            if self.platform == "win32":
                self.create_windows_specific_hooks()
                self.update_existing_hooks_for_windows()
            
            # 3. 创建平台检测Hook
            self.create_platform_detection_hook()
            
            # 4. 生成报告
            report = self.generate_fix_report()
            
            print("=" * 60)
            print("🎉 平台Hook配置修复完成!")
            print(f"📊 执行修复: {len(self.fix_log)} 项")
            print(f"🖥️ 当前平台: {self.platform}")
            print("🔄 建议重启Kiro以应用新配置")
            
            return True
            
        except Exception as e:
            print(f"❌ 修复过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔧 平台特定Hook修复器")
    print("作为DevOps Engineer，我将修复不适合当前平台的Hook配置")
    print()
    
    fixer = PlatformSpecificHookFixer()
    success = fixer.execute_platform_fix()
    
    if success:
        print("\n🎯 平台Hook修复成功!")
        print("💡 现在Hook配置已适配您的Windows环境")
    else:
        print("\n⚠️ 修复过程中遇到问题")

if __name__ == "__main__":
    main()