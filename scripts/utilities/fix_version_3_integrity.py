#!/usr/bin/env python3
"""
修复版本3.0完整性

作为🔧 DevOps Engineer，我负责修复3.0版本中缺失的文件，
确保版本结构的完整性。
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

class Version3IntegrityFixer:
    """版本3.0完整性修复器"""
    
    def __init__(self):
        self.version_3_path = Path("3.0")
        self.kiro_path = Path(".kiro")
        self.fix_log = []
        
    def fix_mac_performance_config(self):
        """修复Mac性能配置文件"""
        print("🍎 修复Mac性能配置文件...")
        
        mac_performance_path = self.version_3_path / "mac" / "settings" / "performance.json"
        source_path = self.kiro_path / "settings" / "mac_performance_config.json"
        
        if source_path.exists() and not mac_performance_path.exists():
            mac_performance_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, mac_performance_path)
            self.fix_log.append(f"复制Mac性能配置: {source_path} -> {mac_performance_path}")
            print(f"✅ 已复制: {mac_performance_path}")
        elif not source_path.exists():
            # 创建默认的Mac性能配置
            mac_performance_config = {
                "metadata": {
                    "platform": "darwin",
                    "version": "3.0.0",
                    "description": "macOS性能优化配置"
                },
                "system_optimization": {
                    "memory_management": {
                        "unified_memory_optimization": True,
                        "memory_pressure_handling": True,
                        "swap_usage_optimization": True
                    },
                    "cpu_optimization": {
                        "energy_efficiency": True,
                        "turbo_boost": True,
                        "thermal_management": True
                    },
                    "storage_optimization": {
                        "apfs_optimization": True,
                        "spotlight_indexing": True,
                        "trim_support": True
                    }
                },
                "development_environment": {
                    "xcode": {
                        "build_optimization": True,
                        "indexing_optimization": True,
                        "simulator_performance": True
                    },
                    "homebrew": {
                        "formula_caching": True,
                        "parallel_builds": True,
                        "cleanup_automation": True
                    },
                    "terminal": {
                        "zsh_optimization": True,
                        "completion_caching": True,
                        "history_optimization": True
                    }
                }
            }
            
            mac_performance_path.parent.mkdir(parents=True, exist_ok=True)
            with open(mac_performance_path, "w", encoding="utf-8") as f:
                json.dump(mac_performance_config, f, indent=2, ensure_ascii=False)
            
            self.fix_log.append(f"创建默认Mac性能配置: {mac_performance_path}")
            print(f"✅ 已创建: {mac_performance_path}")
    
    def fix_missing_hooks(self):
        """修复缺失的Hook文件"""
        print("🪝 修复缺失的Hook文件...")
        
        # 需要的Hook文件
        required_hooks = [
            "error-solution-finder.kiro.hook",
            "global-debug-360.kiro.hook", 
            "intelligent-monitoring-hub.kiro.hook",
            "knowledge-accumulator.kiro.hook",
            "smart-coding-assistant.kiro.hook"
        ]
        
        platforms = ["win", "mac", "linux"]
        
        for platform in platforms:
            platform_hooks_path = self.version_3_path / platform / "hooks"
            platform_hooks_path.mkdir(parents=True, exist_ok=True)
            
            for hook_file in required_hooks:
                hook_path = platform_hooks_path / hook_file
                source_path = self.kiro_path / "hooks" / hook_file
                
                if not hook_path.exists():
                    if source_path.exists():
                        shutil.copy2(source_path, hook_path)
                        self.fix_log.append(f"复制Hook: {source_path} -> {hook_path}")
                        print(f"✅ 已复制: {platform}/hooks/{hook_file}")
                    else:
                        print(f"⚠️ 源Hook文件不存在: {source_path}")
    
    def verify_and_create_missing_directories(self):
        """验证并创建缺失的目录"""
        print("📁 验证并创建缺失的目录...")
        
        required_dirs = [
            "3.0/win/steering",
            "3.0/win/docs", 
            "3.0/mac/steering",
            "3.0/linux/steering",
            "3.0/linux/docs"
        ]
        
        for dir_path in required_dirs:
            path = Path(dir_path)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                self.fix_log.append(f"创建目录: {path}")
                print(f"✅ 已创建目录: {path}")
    
    def create_platform_readme_files(self):
        """为每个平台创建README文件"""
        print("📝 创建平台README文件...")
        
        platform_info = {
            "win": {
                "name": "Windows",
                "features": ["PowerShell集成", "注册表支持", "Visual Studio优化", "Chocolatey支持"]
            },
            "mac": {
                "name": "macOS", 
                "features": ["Homebrew优化", "Zsh集成", "Spotlight集成", "Keychain支持"]
            },
            "linux": {
                "name": "Linux",
                "features": ["多包管理器支持", "Systemd集成", "容器支持", "性能调优"]
            }
        }
        
        for platform, info in platform_info.items():
            readme_path = self.version_3_path / platform / "README.md"
            
            if not readme_path.exists():
                readme_content = f"""# Kiro {info['name']} 配置

## 🎯 平台特性

{info['name']}平台专门优化配置，包含以下特性：

{chr(10).join(f'- {feature}' for feature in info['features'])}

## 📁 目录结构

```
{platform}/
├── settings/        # 配置文件
├── hooks/          # Hook配置
├── steering/       # 引导文件
└── docs/           # 文档
```

## 🚀 使用方法

1. 将配置文件复制到`.kiro/`目录下
2. 根据需要调整平台特定设置
3. 重启Kiro以应用新配置

## 📝 配置说明

### MCP配置
- 继承自基础配置
- 包含{info['name']}特定优化
- 支持平台特有工具集成

### 性能配置
- 系统级优化设置
- 开发环境调优
- 资源使用优化

---

**版本**: 3.0.0  
**平台**: {info['name']}  
**更新日期**: {datetime.now().strftime('%Y-%m-%d')}
"""
                
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(readme_content)
                
                self.fix_log.append(f"创建平台README: {readme_path}")
                print(f"✅ 已创建: {platform}/README.md")
    
    def verify_final_integrity(self):
        """最终完整性验证"""
        print("🔍 最终完整性验证...")
        
        # 检查必需的平台目录和文件
        required_structure = {
            "base": ["mcp.json"],
            "win": ["settings/mcp.json", "settings/performance.json", "README.md"],
            "mac": ["settings/mcp.json", "settings/performance.json", "docs/development_guide.md", "README.md"],
            "linux": ["settings/mcp.json", "settings/performance.json", "README.md"]
        }
        
        integrity_issues = []
        
        for platform, required_files in required_structure.items():
            platform_path = self.version_3_path / platform
            
            if not platform_path.exists():
                integrity_issues.append(f"缺失平台目录: {platform}/")
                continue
            
            for required_file in required_files:
                file_path = platform_path / required_file
                if not file_path.exists():
                    integrity_issues.append(f"缺失文件: {platform}/{required_file}")
        
        # 检查文档文件
        docs = ["README.md", "MIGRATION_GUIDE.md"]
        for doc in docs:
            doc_path = self.version_3_path / doc
            if not doc_path.exists():
                integrity_issues.append(f"缺失文档: {doc}")
        
        # 检查Hook文件
        hook_files = [
            "error-solution-finder.kiro.hook",
            "global-debug-360.kiro.hook",
            "intelligent-monitoring-hub.kiro.hook", 
            "knowledge-accumulator.kiro.hook",
            "smart-coding-assistant.kiro.hook"
        ]
        
        for platform in ["win", "mac", "linux"]:
            hooks_path = self.version_3_path / platform / "hooks"
            if hooks_path.exists():
                for hook_file in hook_files:
                    hook_path = hooks_path / hook_file
                    if not hook_path.exists():
                        integrity_issues.append(f"缺失Hook: {platform}/hooks/{hook_file}")
        
        if integrity_issues:
            print("⚠️ 仍有完整性问题:")
            for issue in integrity_issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ 3.0版本结构完整")
            return True
    
    def generate_fix_report(self):
        """生成修复报告"""
        print("📊 生成修复报告...")
        
        report = {
            "metadata": {
                "fix_date": datetime.now().isoformat(),
                "fixer": "🔧 DevOps Engineer",
                "version": "3.0.0"
            },
            "fix_summary": {
                "total_fixes": len(self.fix_log),
                "integrity_restored": self.verify_final_integrity()
            },
            "fix_log": self.fix_log,
            "final_structure_status": "完整" if self.verify_final_integrity() else "仍有问题"
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/version_3_integrity_fix_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 修复报告已保存到: {report_path}")
        return report
    
    def execute_integrity_fix(self):
        """执行完整性修复"""
        print("🔧 开始修复版本3.0完整性...")
        print("=" * 60)
        
        try:
            # 1. 修复Mac性能配置
            self.fix_mac_performance_config()
            
            # 2. 修复缺失的Hook文件
            self.fix_missing_hooks()
            
            # 3. 验证并创建缺失的目录
            self.verify_and_create_missing_directories()
            
            # 4. 创建平台README文件
            self.create_platform_readme_files()
            
            # 5. 最终验证
            integrity_ok = self.verify_final_integrity()
            
            # 6. 生成报告
            report = self.generate_fix_report()
            
            print("=" * 60)
            print("🎉 完整性修复完成!")
            print(f"📊 执行修复: {len(self.fix_log)} 项")
            print(f"✅ 最终状态: {'完整' if integrity_ok else '仍有问题'}")
            
            return integrity_ok
            
        except Exception as e:
            print(f"❌ 修复过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔧 版本3.0完整性修复器")
    print("作为DevOps Engineer，我将修复3.0版本的完整性问题")
    print()
    
    fixer = Version3IntegrityFixer()
    success = fixer.execute_integrity_fix()
    
    if success:
        print("\n🎯 完整性修复成功!")
        print("📚 版本3.0现在结构完整")
    else:
        print("\n⚠️ 修复过程中遇到问题")

if __name__ == "__main__":
    main()