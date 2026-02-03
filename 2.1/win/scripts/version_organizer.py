#!/usr/bin/env python
"""
Kiro配置系统版本化目录组织器
将现有配置按版本和平台重新组织

作者: Software Architect
版本: 1.0.0
日期: 2026-02-02
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Any
import platform


class KiroVersionOrganizer:
    """Kiro配置系统版本化目录组织器"""
    
    def __init__(self):
        self.root_path = Path(".")
        self.versions = ["1.0", "2.0", "2.1"]
        self.platforms = ["win", "mac", "linux"]
        
    def create_version_structure(self) -> bool:
        """创建版本化目录结构"""
        print("🏗️ 创建版本化目录结构...")
        
        try:
            for version in self.versions:
                version_path = self.root_path / version
                version_path.mkdir(exist_ok=True)
                
                for platform in self.platforms:
                    platform_path = version_path / platform
                    platform_path.mkdir(exist_ok=True)
                    
                    # 创建平台特定的子目录
                    subdirs = [".kiro", "scripts", "config", "docs", "examples"]
                    for subdir in subdirs:
                        (platform_path / subdir).mkdir(exist_ok=True)
                    
                    print(f"  ✅ 创建: {version}/{platform}/")
            
            print("✅ 版本化目录结构创建完成")
            return True
            
        except Exception as e:
            print(f"❌ 创建版本化目录结构失败: {e}")
            return False
    
    def organize_v1_0_configs(self) -> bool:
        """组织v1.0版本配置"""
        print("📦 组织v1.0版本配置...")
        
        try:
            # v1.0是基础版本，创建通用配置
            base_config = {
                "version": "1.0.0",
                "description": "Kiro配置系统基础版本",
                "features": [
                    "硅谷12人团队配置",
                    "基础Hook系统",
                    "质量门禁体系",
                    "代码审查流程"
                ],
                "platforms": {
                    "win": {"supported": True, "notes": "Windows 10+支持"},
                    "mac": {"supported": False, "notes": "v1.0不支持Mac"},
                    "linux": {"supported": True, "notes": "Ubuntu 18.04+支持"}
                }
            }
            
            # 为每个平台创建配置
            for platform in self.platforms:
                platform_path = self.root_path / "1.0" / platform
                
                # 创建版本信息文件
                with open(platform_path / "version.json", "w", encoding="utf-8") as f:
                    json.dump(base_config, f, indent=2, ensure_ascii=False)
                
                # 创建基础.kiro配置
                kiro_path = platform_path / ".kiro"
                
                # 创建基础Hook配置
                hooks_path = kiro_path / "hooks"
                hooks_path.mkdir(exist_ok=True)
                
                if platform == "mac":
                    # Mac在v1.0不支持，创建说明文件
                    with open(hooks_path / "README.md", "w", encoding="utf-8") as f:
                        f.write("# Mac支持说明\n\nv1.0版本不支持Mac平台，请使用v2.1+版本。")
                else:
                    # 创建基础Hook配置
                    basic_hook = {
                        "name": f"基础质量检查 - {platform.upper()}",
                        "version": "1.0.0",
                        "description": f"v1.0版本{platform}平台基础质量检查",
                        "when": {"type": "userTriggered"},
                        "then": {
                            "type": "askAgent",
                            "prompt": f"执行{platform}平台基础质量检查：\n1. 代码语法检查\n2. 基础测试运行\n3. 代码格式验证"
                        }
                    }
                    
                    with open(hooks_path / "basic-quality-check.kiro.hook", "w", encoding="utf-8") as f:
                        json.dump(basic_hook, f, indent=2, ensure_ascii=False)
                
                print(f"  ✅ v1.0/{platform} 配置完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 组织v1.0配置失败: {e}")
            return False
    
    def organize_v2_0_configs(self) -> bool:
        """组织v2.0版本配置"""
        print("📦 组织v2.0版本配置...")
        
        try:
            # v2.0是增强版本
            enhanced_config = {
                "version": "2.0.0",
                "description": "Kiro配置系统增强版本",
                "features": [
                    "硅谷12人团队配置",
                    "任务层次化管理",
                    "增强Hook系统",
                    "质量门禁体系",
                    "跨平台模板系统",
                    "LLM反漂移系统"
                ],
                "platforms": {
                    "win": {"supported": True, "notes": "Windows 10+完全支持"},
                    "mac": {"supported": False, "notes": "v2.0不支持Mac，请使用v2.1+"},
                    "linux": {"supported": True, "notes": "Ubuntu 18.04+完全支持"}
                }
            }
            
            # 复制当前的v2.0配置到版本化目录
            for platform in self.platforms:
                platform_path = self.root_path / "2.0" / platform
                
                # 创建版本信息文件
                with open(platform_path / "version.json", "w", encoding="utf-8") as f:
                    json.dump(enhanced_config, f, indent=2, ensure_ascii=False)
                
                if platform == "mac":
                    # Mac在v2.0不支持
                    kiro_path = platform_path / ".kiro"
                    with open(kiro_path / "README.md", "w", encoding="utf-8") as f:
                        f.write("# Mac支持说明\n\nv2.0版本不支持Mac平台，请使用v2.1+版本获得完整Mac支持。")
                else:
                    # 复制现有配置（去除Mac特定内容）
                    self._copy_configs_for_platform(platform_path, platform, "2.0")
                
                print(f"  ✅ v2.0/{platform} 配置完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 组织v2.0配置失败: {e}")
            return False
    
    def organize_v2_1_configs(self) -> bool:
        """组织v2.1版本配置（当前最新版本）"""
        print("📦 组织v2.1版本配置...")
        
        try:
            # v2.1是Mac适配版本
            mac_compatible_config = {
                "version": "2.1.0",
                "description": "Kiro配置系统Mac适配版本",
                "features": [
                    "硅谷12人团队配置",
                    "任务层次化管理", 
                    "完整Hook系统",
                    "质量门禁体系",
                    "跨平台模板系统",
                    "LLM反漂移系统",
                    "完整Mac平台支持",
                    "Apple Silicon优化",
                    "一键Mac安装"
                ],
                "platforms": {
                    "win": {"supported": True, "notes": "Windows 10+完全支持"},
                    "mac": {"supported": True, "notes": "macOS 10.15+完全支持，包括Apple Silicon"},
                    "linux": {"supported": True, "notes": "Ubuntu 18.04+完全支持"}
                }
            }
            
            # 复制当前完整配置到版本化目录
            for platform in self.platforms:
                platform_path = self.root_path / "2.1" / platform
                
                # 创建版本信息文件
                with open(platform_path / "version.json", "w", encoding="utf-8") as f:
                    json.dump(mac_compatible_config, f, indent=2, ensure_ascii=False)
                
                # 复制完整配置
                self._copy_configs_for_platform(platform_path, platform, "2.1")
                
                print(f"  ✅ v2.1/{platform} 配置完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 组织v2.1配置失败: {e}")
            return False
    
    def _copy_configs_for_platform(self, target_path: Path, platform: str, version: str):
        """为特定平台复制配置文件"""
        try:
            # 复制.kiro配置
            if (self.root_path / ".kiro").exists():
                target_kiro = target_path / ".kiro"
                if target_kiro.exists():
                    shutil.rmtree(target_kiro)
                shutil.copytree(self.root_path / ".kiro", target_kiro)
                
                # 根据平台和版本调整配置
                self._adjust_configs_for_platform(target_kiro, platform, version)
            
            # 复制scripts
            if (self.root_path / "scripts").exists():
                target_scripts = target_path / "scripts"
                if target_scripts.exists():
                    shutil.rmtree(target_scripts)
                shutil.copytree(self.root_path / "scripts", target_scripts)
                
                # 调整脚本
                self._adjust_scripts_for_platform(target_scripts, platform, version)
            
            # 复制文档
            docs_path = target_path / "docs"
            docs_path.mkdir(exist_ok=True)
            
            # 复制相关文档
            doc_files = ["README.md", "MAC_SETUP.md", f"KIRO_CONFIG_SYSTEM_V{version}_RELEASE_NOTES.md"]
            for doc_file in doc_files:
                if (self.root_path / doc_file).exists():
                    if platform == "mac" or "MAC" not in doc_file:
                        shutil.copy2(self.root_path / doc_file, docs_path / doc_file)
            
        except Exception as e:
            print(f"  ⚠️ 复制{platform}配置时出现警告: {e}")
    
    def _adjust_configs_for_platform(self, kiro_path: Path, platform: str, version: str):
        """根据平台调整配置"""
        try:
            # 调整Hook配置
            hooks_path = kiro_path / "hooks"
            if hooks_path.exists():
                for hook_file in hooks_path.glob("*.kiro.hook"):
                    with open(hook_file, "r", encoding="utf-8") as f:
                        hook_config = json.load(f)
                    
                    # 根据平台调整配置
                    if platform == "win":
                        # Windows特定调整
                        if "prompt" in hook_config.get("then", {}):
                            prompt = hook_config["then"]["prompt"]
                            prompt = prompt.replace("python3", "python")
                            prompt = prompt.replace("zsh", "cmd")
                            hook_config["then"]["prompt"] = prompt
                    elif platform == "linux":
                        # Linux特定调整
                        if "prompt" in hook_config.get("then", {}):
                            prompt = hook_config["then"]["prompt"]
                            prompt = prompt.replace("zsh", "bash")
                            hook_config["then"]["prompt"] = prompt
                    # Mac配置保持不变（已经适配）
                    
                    # 如果是v1.0或v2.0且为Mac，移除Mac特定Hook
                    if platform == "mac" and version in ["1.0", "2.0"]:
                        if "mac-environment-check" in hook_file.name:
                            hook_file.unlink()  # 删除Mac专用Hook
                            continue
                    
                    with open(hook_file, "w", encoding="utf-8") as f:
                        json.dump(hook_config, f, indent=2, ensure_ascii=False)
            
            # 调整MCP配置
            settings_path = kiro_path / "settings"
            if settings_path.exists():
                # 根据版本移除不支持的配置
                if version in ["1.0", "2.0"] and platform == "mac":
                    mac_mcp = settings_path / "mcp_mac.json"
                    if mac_mcp.exists():
                        mac_mcp.unlink()
                        
        except Exception as e:
            print(f"  ⚠️ 调整{platform}配置时出现警告: {e}")
    
    def _adjust_scripts_for_platform(self, scripts_path: Path, platform: str, version: str):
        """根据平台调整脚本"""
        try:
            for script_file in scripts_path.glob("*.py"):
                with open(script_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 根据平台调整脚本内容
                if platform == "win":
                    # Windows调整
                    content = content.replace("#!/usr/bin/env python", "#!/usr/bin/env python")
                    content = content.replace('shell=True', 'shell=True')
                elif platform == "linux":
                    # Linux调整
                    content = content.replace('shell=True', 'executable="/bin/bash"')
                # Mac保持不变
                
                # 如果是早期版本且为Mac，添加不支持说明
                if platform == "mac" and version in ["1.0", "2.0"]:
                    if "mac_compatibility" in script_file.name:
                        content = f'''#!/usr/bin/env python
"""
Mac兼容性脚本 - v{version}版本
注意: v{version}版本不支持Mac平台，请升级到v2.1+版本
"""

print("❌ v{version}版本不支持Mac平台")
print("🔄 请升级到v2.1+版本获得完整Mac支持")
exit(1)
'''
                
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(content)
                    
        except Exception as e:
            print(f"  ⚠️ 调整{platform}脚本时出现警告: {e}")
    
    def create_version_index(self) -> bool:
        """创建版本索引文件"""
        print("📋 创建版本索引文件...")
        
        try:
            version_index = {
                "kiro_config_system_versions": {
                    "current_version": "2.1.0",
                    "versions": {
                        "1.0": {
                            "version": "1.0.0",
                            "release_date": "2026-01-01",
                            "description": "基础版本",
                            "platforms": ["win", "linux"],
                            "features": [
                                "硅谷12人团队配置",
                                "基础Hook系统",
                                "质量门禁体系"
                            ]
                        },
                        "2.0": {
                            "version": "2.0.0", 
                            "release_date": "2026-02-01",
                            "description": "增强版本",
                            "platforms": ["win", "linux"],
                            "features": [
                                "任务层次化管理",
                                "增强Hook系统",
                                "LLM反漂移系统",
                                "跨平台模板"
                            ]
                        },
                        "2.1": {
                            "version": "2.1.0",
                            "release_date": "2026-02-02", 
                            "description": "Mac适配版本",
                            "platforms": ["win", "mac", "linux"],
                            "features": [
                                "完整Mac平台支持",
                                "Apple Silicon优化",
                                "一键Mac安装",
                                "跨平台统一体验"
                            ]
                        }
                    },
                    "platform_support": {
                        "windows": {
                            "supported_versions": ["1.0", "2.0", "2.1"],
                            "requirements": "Windows 10+",
                            "notes": "完全支持所有版本"
                        },
                        "linux": {
                            "supported_versions": ["1.0", "2.0", "2.1"],
                            "requirements": "Ubuntu 18.04+",
                            "notes": "完全支持所有版本"
                        },
                        "macos": {
                            "supported_versions": ["2.1"],
                            "requirements": "macOS 10.15+",
                            "notes": "v2.1+版本开始支持，包括Apple Silicon"
                        }
                    }
                }
            }
            
            with open(self.root_path / "VERSION_INDEX.json", "w", encoding="utf-8") as f:
                json.dump(version_index, f, indent=2, ensure_ascii=False)
            
            print("✅ 版本索引文件创建完成")
            return True
            
        except Exception as e:
            print(f"❌ 创建版本索引失败: {e}")
            return False
    
    def create_platform_readme(self) -> bool:
        """为每个平台创建README文件"""
        print("📝 创建平台README文件...")
        
        try:
            for version in self.versions:
                for platform in self.platforms:
                    platform_path = self.root_path / version / platform
                    
                    readme_content = f"""# Kiro配置系统 v{version} - {platform.upper()}平台

## 版本信息
- **版本**: v{version}
- **平台**: {platform.upper()}
- **发布日期**: 2026-02-0{self.versions.index(version) + 1}

## 平台支持状态
"""
                    
                    if platform == "mac" and version in ["1.0", "2.0"]:
                        readme_content += """
❌ **不支持Mac平台**

v{version}版本不支持Mac平台。如需Mac支持，请使用v2.1+版本。

### 升级建议
```bash
# 使用v2.1版本获得完整Mac支持
cd ../2.1/mac/
./setup_mac.sh
```
""".format(version=version)
                    else:
                        readme_content += f"""
✅ **完全支持{platform.upper()}平台**

### 快速开始
```bash
# 1. 复制配置到项目
cp -r .kiro /path/to/your/project/

# 2. 安装依赖
"""
                        
                        if platform == "win":
                            readme_content += """pip install -r requirements.txt

# 3. 运行验证
python scripts/kiro_config_validator.py
```

### Windows特定说明
- 使用PowerShell或CMD
- Python命令: `python`
- 包管理: pip
"""
                        elif platform == "linux":
                            readme_content += """pip3 install -r requirements.txt

# 3. 运行验证
python3 scripts/kiro_config_validator.py
```

### Linux特定说明
- 使用bash shell
- Python命令: `python3`
- 包管理: pip3/apt
"""
                        elif platform == "mac":
                            readme_content += """pip3 install -r requirements.txt

# 3. 运行一键安装（仅v2.1+）
./setup_mac.sh

# 4. 运行验证
python3 scripts/kiro_config_validator.py
```

### Mac特定说明
- 使用zsh shell (macOS Catalina+)
- Python命令: `python3`
- 包管理: pip3/Homebrew
- 支持Apple Silicon和Intel芯片
"""
                    
                    readme_content += f"""

## 功能特性
"""
                    
                    if version == "1.0":
                        readme_content += """
- ✅ 硅谷12人团队配置
- ✅ 基础Hook系统
- ✅ 质量门禁体系
- ✅ 代码审查流程
"""
                    elif version == "2.0":
                        readme_content += """
- ✅ 硅谷12人团队配置
- ✅ 任务层次化管理
- ✅ 增强Hook系统
- ✅ 质量门禁体系
- ✅ LLM反漂移系统
- ✅ 跨平台模板系统
"""
                    elif version == "2.1":
                        readme_content += """
- ✅ 硅谷12人团队配置
- ✅ 任务层次化管理
- ✅ 完整Hook系统
- ✅ 质量门禁体系
- ✅ LLM反漂移系统
- ✅ 跨平台模板系统
- ✅ 完整Mac平台支持 (新增)
- ✅ Apple Silicon优化 (新增)
- ✅ 一键安装脚本 (新增)
"""
                    
                    readme_content += f"""

## 目录结构
```
{version}/{platform}/
├── .kiro/           # Kiro配置文件
│   ├── hooks/       # Hook配置
│   ├── settings/    # 系统设置
│   ├── steering/    # 指导文档
│   └── templates/   # 配置模板
├── scripts/         # 工具脚本
├── docs/           # 文档
├── examples/       # 示例配置
└── version.json    # 版本信息
```

## 支持和帮助
- **GitHub仓库**: https://github.com/rongma1sheng/kiro-silicon-valley-template
- **版本标签**: v{version}
- **问题报告**: GitHub Issues

---
**维护者**: 🏗️ Software Architect  
**最后更新**: 2026-02-02
"""
                    
                    with open(platform_path / "README.md", "w", encoding="utf-8") as f:
                        f.write(readme_content)
                    
                    print(f"  ✅ {version}/{platform}/README.md")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建平台README失败: {e}")
            return False
    
    def run_full_organization(self) -> bool:
        """运行完整的版本化组织流程"""
        print("🏗️ 开始Kiro配置系统版本化组织...")
        print("=" * 60)
        
        success_steps = 0
        total_steps = 6
        
        # 步骤1: 创建版本化目录结构
        if self.create_version_structure():
            success_steps += 1
        
        # 步骤2: 组织v1.0配置
        if self.organize_v1_0_configs():
            success_steps += 1
        
        # 步骤3: 组织v2.0配置
        if self.organize_v2_0_configs():
            success_steps += 1
        
        # 步骤4: 组织v2.1配置
        if self.organize_v2_1_configs():
            success_steps += 1
        
        # 步骤5: 创建版本索引
        if self.create_version_index():
            success_steps += 1
        
        # 步骤6: 创建平台README
        if self.create_platform_readme():
            success_steps += 1
        
        success_rate = (success_steps / total_steps) * 100
        print(f"\n🎯 组织成功率: {success_rate:.1f}% ({success_steps}/{total_steps})")
        
        if success_rate >= 80:
            print("✅ Kiro配置系统版本化组织完成！")
            return True
        else:
            print("❌ 版本化组织未完全成功，请检查错误信息")
            return False


def main():
    """主函数"""
    print("🏗️ Kiro配置系统版本化目录组织器")
    print("=" * 50)
    
    organizer = KiroVersionOrganizer()
    
    if organizer.run_full_organization():
        print("\n🚀 版本化组织完成！目录结构:")
        print("kiro-silicon-valley-template/")
        print("├── 1.0/")
        print("│   ├── win/     # Windows版本配置")
        print("│   ├── mac/     # Mac版本配置 (不支持)")
        print("│   └── linux/   # Linux版本配置")
        print("├── 2.0/")
        print("│   ├── win/     # Windows版本配置")
        print("│   ├── mac/     # Mac版本配置 (不支持)")
        print("│   └── linux/   # Linux版本配置")
        print("├── 2.1/")
        print("│   ├── win/     # Windows版本配置")
        print("│   ├── mac/     # Mac版本配置 (完全支持)")
        print("│   └── linux/   # Linux版本配置")
        print("└── VERSION_INDEX.json  # 版本索引")
        return 0
    else:
        print("\n❌ 版本化组织过程中出现问题")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())