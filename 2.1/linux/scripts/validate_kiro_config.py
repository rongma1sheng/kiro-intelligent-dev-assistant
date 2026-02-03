#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kiro配置验证脚本 - 验证spec、hook、steering、mcp配置的完整性和正确性

检查项目：
1. Hooks配置 - 事件类型、动作类型、闭环机制
2. Steering配置 - front-matter、inclusion设置
3. Spec配置 - requirements/design/tasks完整性
4. MCP配置 - 服务器配置、autoApprove设置

使用方法：
    python scripts/validate_kiro_config.py
"""

import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


@dataclass
class ValidationResult:
    """验证结果"""
    category: str
    item: str
    status: str  # pass, warn, fail
    message: str


class KiroConfigValidator:
    """Kiro配置验证器"""

    # 有效的Hook事件类型
    VALID_HOOK_EVENTS = [
        "fileEdited", "fileCreated", "fileDeleted",
        "userTriggered", "promptSubmit", "agentStop"
    ]
    
    # 有效的Hook动作类型
    VALID_HOOK_ACTIONS = ["askAgent", "runCommand"]
    
    # runCommand只能与这些事件类型配合
    RUN_COMMAND_VALID_EVENTS = ["promptSubmit", "agentStop"]

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.kiro_dir = Path(".kiro")

    def validate_all(self) -> bool:
        """执行所有验证"""
        print("=" * 60)
        print("KIRO配置验证")
        print("=" * 60)
        print()
        
        self.validate_hooks()
        self.validate_steering()
        self.validate_specs()
        self.validate_mcp()
        
        return self.print_summary()

    def validate_hooks(self) -> None:
        """验证Hooks配置"""
        print("[HOOKS] 验证Hooks配置...")
        hooks_dir = self.kiro_dir / "hooks"
        
        if not hooks_dir.exists():
            self.results.append(ValidationResult(
                category="hooks",
                item="hooks目录",
                status="fail",
                message="hooks目录不存在"
            ))
            return
        
        hook_files = list(hooks_dir.glob("*.kiro.hook"))
        if not hook_files:
            self.results.append(ValidationResult(
                category="hooks",
                item="hook文件",
                status="warn",
                message="没有找到hook配置文件"
            ))
            return
        
        for hook_file in hook_files:
            self._validate_single_hook(hook_file)

    def _validate_single_hook(self, hook_file: Path) -> None:
        """验证单个Hook配置"""
        try:
            content = hook_file.read_text(encoding="utf-8")
            config = json.loads(content)
            
            hook_name = hook_file.stem.replace(".kiro", "")
            
            # 检查必需字段
            required_fields = ["name", "version", "when", "then"]
            for field in required_fields:
                if field not in config:
                    self.results.append(ValidationResult(
                        category="hooks",
                        item=hook_name,
                        status="fail",
                        message=f"缺少必需字段: {field}"
                    ))
                    return
            
            # 检查事件类型
            event_type = config.get("when", {}).get("type")
            if event_type not in self.VALID_HOOK_EVENTS:
                self.results.append(ValidationResult(
                    category="hooks",
                    item=hook_name,
                    status="fail",
                    message=f"无效的事件类型: {event_type}"
                ))
                return
            
            # 检查动作类型
            action_type = config.get("then", {}).get("type")
            if action_type not in self.VALID_HOOK_ACTIONS:
                self.results.append(ValidationResult(
                    category="hooks",
                    item=hook_name,
                    status="fail",
                    message=f"无效的动作类型: {action_type}"
                ))
                return
            
            # 检查runCommand与事件类型的兼容性
            if action_type == "runCommand" and event_type not in self.RUN_COMMAND_VALID_EVENTS:
                self.results.append(ValidationResult(
                    category="hooks",
                    item=hook_name,
                    status="warn",
                    message=f"runCommand不建议与{event_type}事件配合使用，建议改为askAgent"
                ))
            
            # 检查askAgent是否有prompt
            if action_type == "askAgent" and not config.get("then", {}).get("prompt"):
                self.results.append(ValidationResult(
                    category="hooks",
                    item=hook_name,
                    status="fail",
                    message="askAgent动作缺少prompt字段"
                ))
                return
            
            # 检查runCommand是否有command
            if action_type == "runCommand" and not config.get("then", {}).get("command"):
                self.results.append(ValidationResult(
                    category="hooks",
                    item=hook_name,
                    status="fail",
                    message="runCommand动作缺少command字段"
                ))
                return
            
            # 检查文件事件是否有patterns
            if event_type in ["fileEdited", "fileCreated", "fileDeleted"]:
                patterns = config.get("when", {}).get("patterns")
                if not patterns:
                    self.results.append(ValidationResult(
                        category="hooks",
                        item=hook_name,
                        status="warn",
                        message=f"{event_type}事件建议配置patterns字段"
                    ))
            
            # 通过验证
            self.results.append(ValidationResult(
                category="hooks",
                item=hook_name,
                status="pass",
                message=f"配置正确 ({event_type} -> {action_type})"
            ))
            
        except json.JSONDecodeError as e:
            self.results.append(ValidationResult(
                category="hooks",
                item=hook_file.name,
                status="fail",
                message=f"JSON解析错误: {e}"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                category="hooks",
                item=hook_file.name,
                status="fail",
                message=f"验证错误: {e}"
            ))

    def validate_steering(self) -> None:
        """验证Steering配置"""
        print("[STEERING] 验证Steering配置...")
        steering_dir = self.kiro_dir / "steering"
        
        if not steering_dir.exists():
            self.results.append(ValidationResult(
                category="steering",
                item="steering目录",
                status="fail",
                message="steering目录不存在"
            ))
            return
        
        steering_files = list(steering_dir.glob("*.md"))
        if not steering_files:
            self.results.append(ValidationResult(
                category="steering",
                item="steering文件",
                status="warn",
                message="没有找到steering配置文件"
            ))
            return
        
        for steering_file in steering_files:
            self._validate_single_steering(steering_file)

    def _validate_single_steering(self, steering_file: Path) -> None:
        """验证单个Steering配置"""
        try:
            content = steering_file.read_text(encoding="utf-8")
            steering_name = steering_file.stem
            
            # 检查front-matter
            if content.startswith("---"):
                # 提取front-matter
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    front_matter = parts[1].strip()
                    
                    # 检查inclusion设置
                    if "inclusion:" in front_matter:
                        if "always" in front_matter:
                            self.results.append(ValidationResult(
                                category="steering",
                                item=steering_name,
                                status="pass",
                                message="配置正确 (inclusion: always)"
                            ))
                        elif "manual" in front_matter:
                            self.results.append(ValidationResult(
                                category="steering",
                                item=steering_name,
                                status="pass",
                                message="配置正确 (inclusion: manual)"
                            ))
                        elif "fileMatch" in front_matter:
                            if "fileMatchPattern:" not in front_matter:
                                self.results.append(ValidationResult(
                                    category="steering",
                                    item=steering_name,
                                    status="warn",
                                    message="fileMatch模式缺少fileMatchPattern"
                                ))
                            else:
                                self.results.append(ValidationResult(
                                    category="steering",
                                    item=steering_name,
                                    status="pass",
                                    message="配置正确 (inclusion: fileMatch)"
                                ))
                    else:
                        self.results.append(ValidationResult(
                            category="steering",
                            item=steering_name,
                            status="warn",
                            message="front-matter缺少inclusion设置"
                        ))
                else:
                    self.results.append(ValidationResult(
                        category="steering",
                        item=steering_name,
                        status="warn",
                        message="front-matter格式不完整"
                    ))
            else:
                self.results.append(ValidationResult(
                    category="steering",
                    item=steering_name,
                    status="warn",
                    message="缺少front-matter，将使用默认inclusion: always"
                ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                category="steering",
                item=steering_file.name,
                status="fail",
                message=f"验证错误: {e}"
            ))

    def validate_specs(self) -> None:
        """验证Specs配置"""
        print("[SPECS] 验证Specs配置...")
        specs_dir = self.kiro_dir / "specs"
        
        if not specs_dir.exists():
            self.results.append(ValidationResult(
                category="specs",
                item="specs目录",
                status="warn",
                message="specs目录不存在"
            ))
            return
        
        spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
        if not spec_dirs:
            self.results.append(ValidationResult(
                category="specs",
                item="spec项目",
                status="warn",
                message="没有找到spec项目"
            ))
            return
        
        for spec_dir in spec_dirs:
            self._validate_single_spec(spec_dir)

    def _validate_single_spec(self, spec_dir: Path) -> None:
        """验证单个Spec配置"""
        spec_name = spec_dir.name
        required_files = ["requirements.md", "design.md", "tasks.md"]
        
        missing_files = []
        for req_file in required_files:
            if not (spec_dir / req_file).exists():
                missing_files.append(req_file)
        
        if missing_files:
            self.results.append(ValidationResult(
                category="specs",
                item=spec_name,
                status="warn",
                message=f"缺少文件: {', '.join(missing_files)}"
            ))
        else:
            # 检查tasks.md中的任务状态
            tasks_file = spec_dir / "tasks.md"
            tasks_content = tasks_file.read_text(encoding="utf-8")
            
            completed = len([m for m in tasks_content.split("\n") if "- [x]" in m])
            pending = len([m for m in tasks_content.split("\n") if "- [ ]" in m])
            
            self.results.append(ValidationResult(
                category="specs",
                item=spec_name,
                status="pass",
                message=f"配置完整 (任务: {completed}完成/{pending}待办)"
            ))

    def validate_mcp(self) -> None:
        """验证MCP配置"""
        print("[MCP] 验证MCP配置...")
        mcp_file = self.kiro_dir / "settings" / "mcp.json"
        
        if not mcp_file.exists():
            self.results.append(ValidationResult(
                category="mcp",
                item="mcp.json",
                status="warn",
                message="MCP配置文件不存在"
            ))
            return
        
        try:
            content = mcp_file.read_text(encoding="utf-8")
            config = json.loads(content)
            
            servers = config.get("mcpServers", {})
            if not servers:
                self.results.append(ValidationResult(
                    category="mcp",
                    item="mcpServers",
                    status="warn",
                    message="没有配置MCP服务器"
                ))
                return
            
            for server_name, server_config in servers.items():
                self._validate_single_mcp_server(server_name, server_config)
                
        except json.JSONDecodeError as e:
            self.results.append(ValidationResult(
                category="mcp",
                item="mcp.json",
                status="fail",
                message=f"JSON解析错误: {e}"
            ))
        except Exception as e:
            self.results.append(ValidationResult(
                category="mcp",
                item="mcp.json",
                status="fail",
                message=f"验证错误: {e}"
            ))

    def _validate_single_mcp_server(self, server_name: str, config: Dict[str, Any]) -> None:
        """验证单个MCP服务器配置"""
        # 检查必需字段
        if "command" not in config:
            self.results.append(ValidationResult(
                category="mcp",
                item=server_name,
                status="fail",
                message="缺少command字段"
            ))
            return
        
        if "args" not in config:
            self.results.append(ValidationResult(
                category="mcp",
                item=server_name,
                status="warn",
                message="缺少args字段"
            ))
        
        # 检查disabled状态
        disabled = config.get("disabled", False)
        status = "已禁用" if disabled else "已启用"
        
        # 检查autoApprove
        auto_approve = config.get("autoApprove", [])
        
        self.results.append(ValidationResult(
            category="mcp",
            item=server_name,
            status="pass",
            message=f"{status}, autoApprove: {len(auto_approve)}个工具"
        ))

    def print_summary(self) -> bool:
        """打印验证摘要"""
        print()
        print("=" * 60)
        print("验证结果摘要")
        print("=" * 60)
        print()
        
        # 按类别分组
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        total_pass = 0
        total_warn = 0
        total_fail = 0
        
        for category, results in categories.items():
            print(f"[{category.upper()}]")
            for result in results:
                icon = "✅" if result.status == "pass" else "⚠️" if result.status == "warn" else "❌"
                print(f"  {icon} {result.item}: {result.message}")
                
                if result.status == "pass":
                    total_pass += 1
                elif result.status == "warn":
                    total_warn += 1
                else:
                    total_fail += 1
            print()
        
        print("=" * 60)
        print(f"总计: ✅ {total_pass} 通过 | ⚠️ {total_warn} 警告 | ❌ {total_fail} 失败")
        print("=" * 60)
        
        return total_fail == 0


def main():
    validator = KiroConfigValidator()
    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
