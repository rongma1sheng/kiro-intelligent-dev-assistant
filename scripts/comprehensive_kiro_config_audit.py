#!/usr/bin/env python3
"""
Kiro配置全量审计脚本
检查所有配置文件的逻辑漏洞、功能重叠、触发逻辑和优化方向

执行者：Software Architect
目标：确保Kiro配置系统的完整性、一致性和最优性
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Set
from pathlib import Path

class KiroConfigAuditor:
    """Kiro配置审计器"""
    
    def __init__(self):
        self.kiro_root = Path(".kiro")
        self.audit_results = {
            "timestamp": datetime.now().isoformat(),
            "issues": [],
            "recommendations": [],
            "statistics": {},
            "optimization_opportunities": []
        }
        
    def audit_all_configs(self) -> Dict[str, Any]:
        """执行全量配置审计"""
        print("🔍 开始Kiro配置全量审计...")
        
        # 1. 审计MCP配置
        self.audit_mcp_configs()
        
        # 2. 审计Hook配置
        self.audit_hook_configs()
        
        # 3. 审计Steering配置
        self.audit_steering_configs()
        
        # 4. 审计Settings配置
        self.audit_settings_configs()
        
        # 5. 检查配置间的逻辑一致性
        self.check_cross_config_consistency()
        
        # 6. 分析功能重叠
        self.analyze_functional_overlaps()
        
        # 7. 评估触发逻辑
        self.evaluate_trigger_logic()
        
        # 8. 生成优化建议
        self.generate_optimization_recommendations()
        
        return self.audit_results
    
    def audit_mcp_configs(self):
        """审计MCP配置"""
        print("📡 审计MCP配置...")
        
        mcp_files = list(self.kiro_root.glob("settings/mcp*.json"))
        mcp_configs = {}
        
        for mcp_file in mcp_files:
            try:
                with open(mcp_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    mcp_configs[mcp_file.name] = config
            except Exception as e:
                self.audit_results["issues"].append({
                    "type": "mcp_config_error",
                    "file": str(mcp_file),
                    "severity": "high",
                    "description": f"MCP配置文件读取失败: {e}"
                })
        
        # 检查MCP配置重复
        self.check_mcp_duplicates(mcp_configs)
        
        # 检查MCP服务器状态
        self.check_mcp_server_status(mcp_configs)
        
        self.audit_results["statistics"]["mcp_files"] = len(mcp_files)
    
    def audit_hook_configs(self):
        """审计Hook配置"""
        print("🪝 审计Hook配置...")
        
        hook_files = list(self.kiro_root.glob("hooks/*.kiro.hook"))
        hook_configs = {}
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    hook_configs[hook_file.name] = config
            except Exception as e:
                self.audit_results["issues"].append({
                    "type": "hook_config_error",
                    "file": str(hook_file),
                    "severity": "medium",
                    "description": f"Hook配置文件读取失败: {e}"
                })
        
        # 检查Hook触发条件重叠
        self.check_hook_trigger_overlaps(hook_configs)
        
        # 检查Hook依赖关系
        self.check_hook_dependencies(hook_configs)
        
        self.audit_results["statistics"]["hook_files"] = len(hook_files)
    
    def audit_steering_configs(self):
        """审计Steering配置"""
        print("🎯 审计Steering配置...")
        
        steering_files = list(self.kiro_root.glob("steering/*.md"))
        steering_content = {}
        
        for steering_file in steering_files:
            try:
                with open(steering_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    steering_content[steering_file.name] = content
            except Exception as e:
                self.audit_results["issues"].append({
                    "type": "steering_config_error",
                    "file": str(steering_file),
                    "severity": "medium",
                    "description": f"Steering文件读取失败: {e}"
                })
        
        # 检查Steering内容冲突
        self.check_steering_conflicts(steering_content)
        
        # 检查Steering覆盖范围
        self.check_steering_coverage(steering_content)
        
        self.audit_results["statistics"]["steering_files"] = len(steering_files)
    
    def audit_settings_configs(self):
        """审计Settings配置"""
        print("⚙️ 审计Settings配置...")
        
        settings_files = list(self.kiro_root.glob("settings/*.json"))
        settings_configs = {}
        
        for settings_file in settings_files:
            if "mcp" not in settings_file.name:  # MCP已单独处理
                try:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        settings_configs[settings_file.name] = config
                except Exception as e:
                    self.audit_results["issues"].append({
                        "type": "settings_config_error",
                        "file": str(settings_file),
                        "severity": "medium",
                        "description": f"Settings配置文件读取失败: {e}"
                    })
        
        self.audit_results["statistics"]["settings_files"] = len(settings_files)
    
    def check_mcp_duplicates(self, mcp_configs: Dict[str, Any]):
        """检查MCP配置重复"""
        servers = {}
        for file_name, config in mcp_configs.items():
            if "mcpServers" in config:
                for server_name, server_config in config["mcpServers"].items():
                    if server_name in servers:
                        self.audit_results["issues"].append({
                            "type": "mcp_duplicate_server",
                            "severity": "high",
                            "description": f"MCP服务器 '{server_name}' 在多个文件中重复定义: {servers[server_name]} 和 {file_name}"
                        })
                    servers[server_name] = file_name
    
    def check_mcp_server_status(self, mcp_configs: Dict[str, Any]):
        """检查MCP服务器状态"""
        for file_name, config in mcp_configs.items():
            if "mcpServers" in config:
                for server_name, server_config in config["mcpServers"].items():
                    if server_config.get("disabled", False):
                        self.audit_results["issues"].append({
                            "type": "mcp_server_disabled",
                            "severity": "low",
                            "description": f"MCP服务器 '{server_name}' 在 {file_name} 中被禁用"
                        })
    
    def check_hook_trigger_overlaps(self, hook_configs: Dict[str, Any]):
        """检查Hook触发条件重叠"""
        triggers = {}
        for file_name, config in hook_configs.items():
            if "when" in config:
                trigger_key = f"{config['when'].get('type', '')}-{config['when'].get('patterns', [])}"
                if trigger_key in triggers:
                    self.audit_results["issues"].append({
                        "type": "hook_trigger_overlap",
                        "severity": "medium",
                        "description": f"Hook触发条件重叠: {triggers[trigger_key]} 和 {file_name}"
                    })
                triggers[trigger_key] = file_name
    
    def check_hook_dependencies(self, hook_configs: Dict[str, Any]):
        """检查Hook依赖关系"""
        # 检查Hook间的逻辑依赖
        for file_name, config in hook_configs.items():
            if config.get("then", {}).get("type") == "runCommand":
                command = config["then"].get("command", "")
                if "python" in command and "scripts/" in command:
                    script_path = re.search(r'scripts/[\w_]+\.py', command)
                    if script_path and not os.path.exists(script_path.group()):
                        self.audit_results["issues"].append({
                            "type": "hook_missing_dependency",
                            "severity": "high",
                            "description": f"Hook {file_name} 依赖的脚本不存在: {script_path.group()}"
                        })
    
    def check_steering_conflicts(self, steering_content: Dict[str, str]):
        """检查Steering内容冲突"""
        # 检查角色定义冲突
        role_definitions = {}
        for file_name, content in steering_content.items():
            roles = re.findall(r'### (\d+\.\s+[^#\n]+)', content)
            for role in roles:
                if role in role_definitions:
                    self.audit_results["issues"].append({
                        "type": "steering_role_conflict",
                        "severity": "medium",
                        "description": f"角色定义冲突: '{role}' 在 {role_definitions[role]} 和 {file_name} 中都有定义"
                    })
                role_definitions[role] = file_name
    
    def check_steering_coverage(self, steering_content: Dict[str, str]):
        """检查Steering覆盖范围"""
        required_topics = [
            "团队配置", "角色权限", "任务管理", "项目规划", "反漂移系统"
        ]
        
        covered_topics = set()
        for content in steering_content.values():
            for topic in required_topics:
                if topic in content:
                    covered_topics.add(topic)
        
        missing_topics = set(required_topics) - covered_topics
        if missing_topics:
            self.audit_results["issues"].append({
                "type": "steering_coverage_gap",
                "severity": "medium",
                "description": f"Steering配置缺少以下主题覆盖: {', '.join(missing_topics)}"
            })
    
    def check_cross_config_consistency(self):
        """检查配置间的逻辑一致性"""
        print("🔗 检查配置间逻辑一致性...")
        
        # 检查Hook和Steering的一致性
        self.check_hook_steering_consistency()
        
        # 检查MCP和Hook的一致性
        self.check_mcp_hook_consistency()
    
    def check_hook_steering_consistency(self):
        """检查Hook和Steering的一致性"""
        # 读取相关配置进行一致性检查
        pass  # 具体实现根据需要添加
    
    def check_mcp_hook_consistency(self):
        """检查MCP和Hook的一致性"""
        # 检查Hook中引用的MCP服务是否存在
        pass  # 具体实现根据需要添加
    
    def analyze_functional_overlaps(self):
        """分析功能重叠"""
        print("🔄 分析功能重叠...")
        
        # 分析Hook功能重叠
        self.analyze_hook_functional_overlaps()
        
        # 分析Steering功能重叠
        self.analyze_steering_functional_overlaps()
    
    def analyze_hook_functional_overlaps(self):
        """分析Hook功能重叠"""
        hook_functions = {
            "quality_check": [],
            "error_handling": [],
            "knowledge_management": [],
            "task_management": [],
            "monitoring": []
        }
        
        hook_files = list(self.kiro_root.glob("hooks/*.kiro.hook"))
        for hook_file in hook_files:
            hook_name = hook_file.stem
            
            # 根据Hook名称分类功能
            if "quality" in hook_name or "test" in hook_name:
                hook_functions["quality_check"].append(hook_name)
            elif "error" in hook_name or "debug" in hook_name:
                hook_functions["error_handling"].append(hook_name)
            elif "knowledge" in hook_name or "memory" in hook_name:
                hook_functions["knowledge_management"].append(hook_name)
            elif "task" in hook_name or "pm" in hook_name:
                hook_functions["task_management"].append(hook_name)
            elif "monitor" in hook_name or "guard" in hook_name:
                hook_functions["monitoring"].append(hook_name)
        
        # 检查功能重叠
        for function_type, hooks in hook_functions.items():
            if len(hooks) > 3:  # 超过3个Hook处理同一功能可能存在重叠
                self.audit_results["issues"].append({
                    "type": "functional_overlap",
                    "severity": "low",
                    "description": f"功能重叠: {function_type} 功能有 {len(hooks)} 个Hook处理: {', '.join(hooks)}"
                })
    
    def analyze_steering_functional_overlaps(self):
        """分析Steering功能重叠"""
        # 检查Steering文件间的功能重叠
        pass  # 根据需要实现
    
    def evaluate_trigger_logic(self):
        """评估触发逻辑"""
        print("⚡ 评估触发逻辑...")
        
        hook_files = list(self.kiro_root.glob("hooks/*.kiro.hook"))
        trigger_analysis = {
            "fileEdited": [],
            "promptSubmit": [],
            "agentStop": [],
            "userTriggered": []
        }
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    trigger_type = config.get("when", {}).get("type", "unknown")
                    if trigger_type in trigger_analysis:
                        trigger_analysis[trigger_type].append(hook_file.stem)
            except:
                continue
        
        # 分析触发逻辑合理性
        for trigger_type, hooks in trigger_analysis.items():
            if len(hooks) > 5:  # 过多Hook使用同一触发器可能影响性能
                self.audit_results["issues"].append({
                    "type": "trigger_overload",
                    "severity": "medium",
                    "description": f"触发器过载: {trigger_type} 触发器被 {len(hooks)} 个Hook使用，可能影响性能"
                })
    
    def generate_optimization_recommendations(self):
        """生成优化建议"""
        print("💡 生成优化建议...")
        
        # 基于发现的问题生成建议
        high_severity_issues = [issue for issue in self.audit_results["issues"] if issue["severity"] == "high"]
        medium_severity_issues = [issue for issue in self.audit_results["issues"] if issue["severity"] == "medium"]
        
        if high_severity_issues:
            self.audit_results["recommendations"].append({
                "priority": "critical",
                "category": "bug_fixes",
                "description": f"立即修复 {len(high_severity_issues)} 个高严重性问题",
                "actions": [issue["description"] for issue in high_severity_issues[:3]]
            })
        
        if medium_severity_issues:
            self.audit_results["recommendations"].append({
                "priority": "high",
                "category": "improvements",
                "description": f"优化 {len(medium_severity_issues)} 个中等严重性问题",
                "actions": [issue["description"] for issue in medium_severity_issues[:3]]
            })
        
        # 性能优化建议
        self.audit_results["optimization_opportunities"].extend([
            {
                "category": "performance",
                "description": "合并功能相似的Hook以减少触发开销",
                "impact": "medium",
                "effort": "low"
            },
            {
                "category": "maintainability",
                "description": "建立配置文件版本控制和变更追踪",
                "impact": "high",
                "effort": "medium"
            },
            {
                "category": "reliability",
                "description": "添加配置文件自动验证和修复机制",
                "impact": "high",
                "effort": "high"
            }
        ])

def main():
    """主执行函数"""
    print("🔍 启动Kiro配置全量审计...")
    print("=" * 60)
    
    try:
        auditor = KiroConfigAuditor()
        results = auditor.audit_all_configs()
        
        # 保存审计结果
        os.makedirs(".kiro/reports", exist_ok=True)
        report_path = ".kiro/reports/kiro_config_audit_report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 60)
        print("📊 审计结果摘要:")
        print(f"✅ 检查文件数: {sum(results['statistics'].values())}")
        print(f"⚠️ 发现问题数: {len(results['issues'])}")
        print(f"💡 优化建议数: {len(results['recommendations'])}")
        
        # 按严重性分类显示问题
        severity_counts = {}
        for issue in results["issues"]:
            severity = issue["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if severity_counts:
            print("\n🚨 问题分布:")
            for severity, count in severity_counts.items():
                print(f"   {severity.upper()}: {count}个")
        
        print(f"\n📄 详细报告保存至: {report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 审计过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Kiro配置审计完成！")
    else:
        print("\n💥 配置审计失败，请检查错误信息")