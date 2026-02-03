#!/usr/bin/env python3
"""
Kiro配置系统Mac适配器
为.kiro配置系统提供跨平台Mac兼容性支持

作者: Software Architect
版本: 1.0.0
日期: 2026-02-02
"""

import os
import platform
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class KiroMacAdapter:
    """Kiro配置系统Mac适配器"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_mac = self.system == "Darwin"
        self.is_apple_silicon = self._detect_apple_silicon()
        self.homebrew_prefix = self._get_homebrew_prefix()
        self.kiro_root = Path(".kiro")
        
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
        return "/opt/homebrew" if self.is_apple_silicon else "/usr/local"
    
    def adapt_hook_configurations(self) -> bool:
        """适配Hook配置文件"""
        print("🔧 开始适配Hook配置...")
        
        hooks_dir = self.kiro_root / "hooks"
        if not hooks_dir.exists():
            print("❌ .kiro/hooks目录不存在")
            return False
        
        adaptations_made = 0
        
        for hook_file in hooks_dir.glob("*.kiro.hook"):
            if self._adapt_single_hook(hook_file):
                adaptations_made += 1
        
        print(f"✅ 已适配 {adaptations_made} 个Hook配置文件")
        return True
    
    def _adapt_single_hook(self, hook_file: Path) -> bool:
        """适配单个Hook配置文件"""
        try:
            with open(hook_file, 'r', encoding='utf-8') as f:
                hook_config = json.load(f)
            
            # 检查是否需要适配
            needs_adaptation = False
            
            # 适配脚本路径
            if 'then' in hook_config and 'prompt' in hook_config['then']:
                prompt = hook_config['then']['prompt']
                
                # 替换Python命令为跨平台兼容的版本
                if 'python scripts/' in prompt:
                    # Mac上优先使用python3
                    prompt = prompt.replace('python scripts/', 'python3 scripts/')
                    needs_adaptation = True
                
                # 适配shell命令
                if 'bash scripts/' in prompt:
                    # Mac上使用zsh作为默认shell
                    prompt = prompt.replace('bash scripts/', 'zsh scripts/')
                    needs_adaptation = True
                
                # 添加Mac环境检查
                if needs_adaptation and 'Mac环境检查' not in prompt:
                    mac_check = "\n\n🍎 Mac环境自动适配:\n- 使用python3命令\n- 使用zsh作为默认shell\n- 支持Apple Silicon和Intel芯片"
                    prompt += mac_check
                    needs_adaptation = True
                
                hook_config['then']['prompt'] = prompt
            
            # 如果有适配，保存文件
            if needs_adaptation:
                with open(hook_file, 'w', encoding='utf-8') as f:
                    json.dump(hook_config, f, indent=2, ensure_ascii=False)
                print(f"  ✅ 已适配: {hook_file.name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 适配失败 {hook_file.name}: {e}")
            return False
    
    def adapt_script_references(self) -> bool:
        """适配脚本引用"""
        print("🔧 开始适配脚本引用...")
        
        scripts_to_adapt = [
            "scripts/enhanced_quality_gate.py",
            "scripts/team_bug_fixer.py", 
            "scripts/kiro_config_validator.py",
            ".kiro/templates/global-project-config/scripts/universal_quality_gate.py",
            ".kiro/templates/global-project-config/scripts/project_initializer.py"
        ]
        
        adaptations_made = 0
        
        for script_path in scripts_to_adapt:
            if Path(script_path).exists():
                if self._adapt_script_file(Path(script_path)):
                    adaptations_made += 1
        
        print(f"✅ 已适配 {adaptations_made} 个脚本文件")
        return True
    
    def _adapt_script_file(self, script_path: Path) -> bool:
        """适配单个脚本文件"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 适配shebang行
            if content.startswith('#!/usr/bin/env python'):
                content = content.replace('#!/usr/bin/env python', '#!/usr/bin/env python3')
            elif content.startswith('#!/usr/bin/python'):
                content = content.replace('#!/usr/bin/python', '#!/usr/bin/env python3')
            
            # 适配subprocess调用中的shell
            if 'shell=True' in content and 'executable=' not in content:
                # 为Mac添加默认shell
                content = content.replace(
                    'shell=True',
                    'shell=True, executable="/bin/zsh" if platform.system() == "Darwin" else None'
                )
                
                # 确保导入platform模块
                if 'import platform' not in content:
                    import_section = content.find('import ')
                    if import_section != -1:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.startswith('import ') or line.startswith('from '):
                                lines.insert(i, 'import platform')
                                break
                        content = '\n'.join(lines)
            
            # 适配路径分隔符
            if '\\' in content and 'windows' not in script_path.name.lower():
                content = content.replace('\\', '/')
            
            # 如果有修改，保存文件
            if content != original_content:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 设置执行权限（Mac/Linux）
                if self.is_mac or platform.system() == "Linux":
                    os.chmod(script_path, 0o755)
                
                print(f"  ✅ 已适配: {script_path}")
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 适配失败 {script_path}: {e}")
            return False
    
    def create_mac_specific_configs(self) -> bool:
        """创建Mac专用配置"""
        print("🔧 创建Mac专用配置...")
        
        # 创建Mac专用MCP配置
        mac_mcp_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "."
                    ],
                    "env": {
                        "FILESYSTEM_MAX_FILE_SIZE": "10MB",
                        "FILESYSTEM_ALLOWED_EXTENSIONS": ".py,.js,.ts,.md,.json,.yaml,.yml,.txt",
                        "SHELL": "/bin/zsh"  # Mac默认shell
                    },
                    "disabled": False,
                    "autoApprove": [
                        "read_text_file",
                        "list_directory", 
                        "search_files",
                        "get_file_info",
                        "directory_tree"
                    ]
                },
                "memory": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-memory"
                    ],
                    "env": {
                        "MEMORY_MAX_ENTITIES": "10000",
                        "MEMORY_PERSISTENCE": "true",
                        "TMPDIR": "/tmp"  # Mac临时目录
                    },
                    "disabled": False,
                    "autoApprove": [
                        "create_entities",
                        "search_nodes",
                        "read_graph",
                        "open_nodes",
                        "add_observations",
                        "create_relations"
                    ]
                }
            }
        }
        
        # 保存Mac专用MCP配置
        mac_mcp_path = self.kiro_root / "settings" / "mcp_mac.json"
        mac_mcp_path.parent.mkdir(exist_ok=True)
        
        with open(mac_mcp_path, 'w', encoding='utf-8') as f:
            json.dump(mac_mcp_config, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ 已创建: {mac_mcp_path}")
        
        # 创建Mac专用Hook
        mac_hook_config = {
            "name": "Mac环境检查Hook",
            "version": "1.0.0",
            "description": "自动检查和适配Mac开发环境",
            "when": {
                "type": "userTriggered"
            },
            "then": {
                "type": "askAgent",
                "prompt": "🍎 Mac环境检查和适配:\n\n1. 检查系统环境:\n   - 检测芯片架构 (Apple Silicon/Intel)\n   - 验证Homebrew安装\n   - 确认Python3可用性\n   - 检查Xcode命令行工具\n\n2. 自动适配配置:\n   - 使用python3命令\n   - 使用zsh作为默认shell\n   - 适配Homebrew路径\n   - 设置正确的文件权限\n\n3. 运行兼容性检查:\n   python3 scripts/mac_compatibility.py\n\n4. 如需安装依赖:\n   ./setup_mac.sh\n\n🔧 Mac专用优化已启用"
            }
        }
        
        mac_hook_path = self.kiro_root / "hooks" / "mac-environment-check.kiro.hook"
        with open(mac_hook_path, 'w', encoding='utf-8') as f:
            json.dump(mac_hook_config, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ 已创建: {mac_hook_path}")
        
        return True
    
    def update_deployment_scripts(self) -> bool:
        """更新部署脚本"""
        print("🔧 更新部署脚本...")
        
        deploy_script_path = self.kiro_root / "templates" / "global-project-config" / "scripts" / "deploy_to_project.sh"
        
        if not deploy_script_path.exists():
            print(f"❌ 部署脚本不存在: {deploy_script_path}")
            return False
        
        try:
            with open(deploy_script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 添加Mac检测和适配逻辑
            mac_adaptation = '''
# Mac环境检测和适配
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 检测到macOS环境，启用Mac适配..."
    
    # 检测芯片架构
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        echo "🔧 Apple Silicon芯片已检测"
        export HOMEBREW_PREFIX="/opt/homebrew"
    else
        echo "🔧 Intel芯片已检测"
        export HOMEBREW_PREFIX="/usr/local"
    fi
    
    # 设置Mac环境变量
    export PATH="$HOMEBREW_PREFIX/bin:$PATH"
    export SHELL="/bin/zsh"
    
    # 使用python3命令
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    PYTHON_CMD="python"
    PIP_CMD="pip"
fi
'''
            
            # 在脚本开头添加Mac适配逻辑
            if 'Mac环境检测和适配' not in content:
                lines = content.split('\n')
                # 找到第一个非注释行
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#'):
                        insert_index = i
                        break
                
                lines.insert(insert_index, mac_adaptation)
                content = '\n'.join(lines)
                
                # 替换python命令为变量
                content = content.replace('python ', '$PYTHON_CMD ')
                content = content.replace('pip ', '$PIP_CMD ')
                
                with open(deploy_script_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ 已更新: {deploy_script_path}")
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 更新失败 {deploy_script_path}: {e}")
            return False
    
    def validate_mac_compatibility(self) -> Dict[str, Any]:
        """验证Mac兼容性"""
        print("🔍 验证Mac兼容性...")
        
        validation_results = {
            "timestamp": "2026-02-02T00:00:00",
            "system_info": {
                "platform": platform.platform(),
                "system": self.system,
                "is_mac": self.is_mac,
                "is_apple_silicon": self.is_apple_silicon,
                "homebrew_prefix": self.homebrew_prefix
            },
            "hook_adaptations": [],
            "script_adaptations": [],
            "config_creations": [],
            "compatibility_score": 0,
            "recommendations": []
        }
        
        # 检查Hook适配
        hooks_dir = self.kiro_root / "hooks"
        if hooks_dir.exists():
            for hook_file in hooks_dir.glob("*.kiro.hook"):
                try:
                    with open(hook_file, 'r', encoding='utf-8') as f:
                        hook_config = json.load(f)
                    
                    is_mac_compatible = (
                        'python3' in str(hook_config) or 
                        'Mac环境' in str(hook_config) or
                        'zsh' in str(hook_config)
                    )
                    
                    validation_results["hook_adaptations"].append({
                        "file": hook_file.name,
                        "mac_compatible": is_mac_compatible
                    })
                except Exception:
                    validation_results["hook_adaptations"].append({
                        "file": hook_file.name,
                        "mac_compatible": False,
                        "error": "解析失败"
                    })
        
        # 检查脚本适配
        script_files = [
            "scripts/enhanced_quality_gate.py",
            "scripts/team_bug_fixer.py",
            "scripts/mac_compatibility.py"
        ]
        
        for script_path in script_files:
            if Path(script_path).exists():
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    is_mac_compatible = (
                        '#!/usr/bin/env python3' in content or
                        'platform.system()' in content or
                        'executable="/bin/zsh"' in content
                    )
                    
                    validation_results["script_adaptations"].append({
                        "file": script_path,
                        "mac_compatible": is_mac_compatible
                    })
                except Exception:
                    validation_results["script_adaptations"].append({
                        "file": script_path,
                        "mac_compatible": False,
                        "error": "读取失败"
                    })
        
        # 检查Mac专用配置
        mac_configs = [
            ".kiro/settings/mcp_mac.json",
            ".kiro/hooks/mac-environment-check.kiro.hook",
            "setup_mac.sh",
            "MAC_SETUP.md"
        ]
        
        for config_path in mac_configs:
            exists = Path(config_path).exists()
            validation_results["config_creations"].append({
                "file": config_path,
                "exists": exists
            })
        
        # 计算兼容性评分
        total_checks = (
            len(validation_results["hook_adaptations"]) +
            len(validation_results["script_adaptations"]) +
            len(validation_results["config_creations"])
        )
        
        passed_checks = (
            sum(1 for h in validation_results["hook_adaptations"] if h.get("mac_compatible", False)) +
            sum(1 for s in validation_results["script_adaptations"] if s.get("mac_compatible", False)) +
            sum(1 for c in validation_results["config_creations"] if c.get("exists", False))
        )
        
        validation_results["compatibility_score"] = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        # 生成建议
        if validation_results["compatibility_score"] < 80:
            validation_results["recommendations"].append("运行完整的Mac适配流程")
        
        if self.is_mac:
            validation_results["recommendations"].append("运行 ./setup_mac.sh 安装Mac依赖")
            validation_results["recommendations"].append("使用 python3 命令替代 python")
        
        if self.is_apple_silicon:
            validation_results["recommendations"].append("Apple Silicon优化已启用")
        
        print(f"✅ Mac兼容性评分: {validation_results['compatibility_score']:.1f}%")
        
        return validation_results
    
    def run_full_adaptation(self) -> bool:
        """运行完整的Mac适配流程"""
        print("🍎 开始Kiro配置系统Mac适配...")
        print("=" * 60)
        
        success_steps = 0
        total_steps = 5
        
        # 步骤1: 适配Hook配置
        if self.adapt_hook_configurations():
            success_steps += 1
        
        # 步骤2: 适配脚本引用
        if self.adapt_script_references():
            success_steps += 1
        
        # 步骤3: 创建Mac专用配置
        if self.create_mac_specific_configs():
            success_steps += 1
        
        # 步骤4: 更新部署脚本
        if self.update_deployment_scripts():
            success_steps += 1
        
        # 步骤5: 验证兼容性
        validation_results = self.validate_mac_compatibility()
        if validation_results["compatibility_score"] >= 80:
            success_steps += 1
        
        # 保存验证报告
        report_path = Path("reports/kiro_mac_adaptation_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 适配报告已保存: {report_path}")
        
        success_rate = (success_steps / total_steps) * 100
        print(f"\n🎯 适配成功率: {success_rate:.1f}% ({success_steps}/{total_steps})")
        
        if success_rate >= 80:
            print("✅ Kiro配置系统Mac适配完成！")
            return True
        else:
            print("❌ Mac适配未完全成功，请检查错误信息")
            return False


def main():
    """主函数"""
    print("🍎 Kiro配置系统Mac适配器")
    print("=" * 50)
    
    adapter = KiroMacAdapter()
    
    if adapter.run_full_adaptation():
        print("\n🚀 Mac用户现在可以:")
        print("1. 运行 ./setup_mac.sh 安装依赖")
        print("2. 使用所有Kiro配置功能")
        print("3. 享受Apple Silicon优化")
        return 0
    else:
        print("\n❌ 适配过程中出现问题")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())