#!/usr/bin/env python
"""
系统部署状态检查器 - 硅谷项目开发经理设计
检查LLM反漂移协同系统的完整部署状态
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

class SystemDeploymentChecker:
    """系统部署状态检查器"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.deployment_status = {}
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('system_deployment_checker')
        logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler('logs/deployment_check.log', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def check_complete_deployment(self) -> Dict[str, Any]:
        """检查完整的系统部署状态"""
        self.logger.info("开始检查系统部署状态")
        
        deployment_report = {
            "timestamp": datetime.now().isoformat(),
            "system_name": "LLM反漂移协同系统",
            "version": "1.0.0",
            "components": {},
            "overall_status": "unknown",
            "deployment_progress": 0,
            "issues": [],
            "recommendations": []
        }
        
        # 检查各个组件
        components_to_check = [
            ("hook_system", "Hook系统", self._check_hook_system),
            ("steering_configs", "Steering配置", self._check_steering_configs),
            ("monitoring_scripts", "监控脚本", self._check_monitoring_scripts),
            ("config_management", "配置管理", self._check_config_management),
            ("behavior_constraints", "行为约束", self._check_behavior_constraints),
            ("permission_matrix", "权限矩阵", self._check_permission_matrix)
        ]
        
        total_components = len(components_to_check)
        deployed_components = 0
        
        for component_id, component_name, check_function in components_to_check:
            self.logger.info(f"检查组件: {component_name}")
            component_status = check_function()
            deployment_report["components"][component_id] = {
                "name": component_name,
                "status": component_status["status"],
                "details": component_status
            }
            
            if component_status["status"] == "deployed":
                deployed_components += 1
            elif component_status["status"] == "partial":
                deployed_components += 0.5
        
        # 计算部署进度
        deployment_report["deployment_progress"] = (deployed_components / total_components) * 100
        
        # 确定总体状态
        if deployment_report["deployment_progress"] == 100:
            deployment_report["overall_status"] = "fully_deployed"
        elif deployment_report["deployment_progress"] >= 80:
            deployment_report["overall_status"] = "mostly_deployed"
        elif deployment_report["deployment_progress"] >= 50:
            deployment_report["overall_status"] = "partially_deployed"
        else:
            deployment_report["overall_status"] = "minimal_deployment"
        
        # 收集问题和建议
        for component_data in deployment_report["components"].values():
            if component_data["details"].get("issues"):
                deployment_report["issues"].extend(component_data["details"]["issues"])
            if component_data["details"].get("recommendations"):
                deployment_report["recommendations"].extend(component_data["details"]["recommendations"])
        
        return deployment_report
    
    def _check_hook_system(self) -> Dict[str, Any]:
        """检查Hook系统"""
        result = {
            "status": "not_deployed",
            "files_found": [],
            "files_missing": [],
            "issues": [],
            "recommendations": []
        }
        
        # 检查核心Hook文件
        required_hooks = [
            "llm-execution-monitor.kiro.hook",
            "real-time-quality-guard.kiro.hook", 
            "context-consistency-anchor.kiro.hook"
        ]
        
        hooks_dir = Path(".kiro/hooks")
        if not hooks_dir.exists():
            result["issues"].append("Hook目录不存在")
            result["recommendations"].append("创建.kiro/hooks目录")
            return result
        
        for hook_file in required_hooks:
            hook_path = hooks_dir / hook_file
            if hook_path.exists():
                result["files_found"].append(hook_file)
                # 验证JSON格式
                try:
                    with open(hook_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    result["issues"].append(f"Hook文件JSON格式错误: {hook_file}")
            else:
                result["files_missing"].append(hook_file)
        
        # 确定状态
        if len(result["files_found"]) == len(required_hooks):
            result["status"] = "deployed"
        elif len(result["files_found"]) > 0:
            result["status"] = "partial"
        
        if result["files_missing"]:
            result["recommendations"].append(f"创建缺失的Hook文件: {result['files_missing']}")
        
        return result
    
    def _check_steering_configs(self) -> Dict[str, Any]:
        """检查Steering配置"""
        result = {
            "status": "not_deployed",
            "files_found": [],
            "files_missing": [],
            "issues": [],
            "recommendations": []
        }
        
        # 检查核心Steering文件
        required_steering = [
            "llm-anti-drift-system.md",
            "role-permission-matrix.md",
            "silicon-valley-team-config-optimized.md"
        ]
        
        steering_dir = Path(".kiro/steering")
        if not steering_dir.exists():
            result["issues"].append("Steering目录不存在")
            result["recommendations"].append("创建.kiro/steering目录")
            return result
        
        for steering_file in required_steering:
            steering_path = steering_dir / steering_file
            if steering_path.exists():
                result["files_found"].append(steering_file)
                # 检查文件大小（确保不是空文件）
                if steering_path.stat().st_size < 100:
                    result["issues"].append(f"Steering文件过小，可能内容不完整: {steering_file}")
            else:
                result["files_missing"].append(steering_file)
        
        # 确定状态
        if len(result["files_found"]) == len(required_steering):
            result["status"] = "deployed"
        elif len(result["files_found"]) > 0:
            result["status"] = "partial"
        
        if result["files_missing"]:
            result["recommendations"].append(f"创建缺失的Steering文件: {result['files_missing']}")
        
        return result
    
    def _check_monitoring_scripts(self) -> Dict[str, Any]:
        """检查监控脚本"""
        result = {
            "status": "not_deployed",
            "files_found": [],
            "files_missing": [],
            "issues": [],
            "recommendations": []
        }
        
        # 检查核心监控脚本
        required_scripts = [
            "llm_execution_monitor.py",
            "unified_config_manager.py",
            "hook_system_validator.py"
        ]
        
        scripts_dir = Path("scripts")
        if not scripts_dir.exists():
            result["issues"].append("Scripts目录不存在")
            result["recommendations"].append("创建scripts目录")
            return result
        
        for script_file in required_scripts:
            script_path = scripts_dir / script_file
            if script_path.exists():
                result["files_found"].append(script_file)
                # 检查脚本是否可执行
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "def main(" not in content and "__main__" not in content:
                            result["issues"].append(f"脚本缺少主函数: {script_file}")
                except Exception as e:
                    result["issues"].append(f"无法读取脚本文件: {script_file} - {e}")
            else:
                result["files_missing"].append(script_file)
        
        # 确定状态
        if len(result["files_found"]) == len(required_scripts):
            result["status"] = "deployed"
        elif len(result["files_found"]) > 0:
            result["status"] = "partial"
        
        if result["files_missing"]:
            result["recommendations"].append(f"创建缺失的监控脚本: {result['files_missing']}")
        
        return result
    
    def _check_config_management(self) -> Dict[str, Any]:
        """检查配置管理"""
        result = {
            "status": "not_deployed",
            "files_found": [],
            "files_missing": [],
            "issues": [],
            "recommendations": []
        }
        
        # 检查MCP配置
        mcp_config_path = Path(".kiro/settings/mcp.json")
        if mcp_config_path.exists():
            result["files_found"].append("mcp.json")
            try:
                with open(mcp_config_path, 'r', encoding='utf-8') as f:
                    mcp_config = json.load(f)
                    if "mcpServers" not in mcp_config:
                        result["issues"].append("MCP配置缺少mcpServers字段")
            except json.JSONDecodeError:
                result["issues"].append("MCP配置JSON格式错误")
        else:
            result["files_missing"].append("mcp.json")
        
        # 检查日志目录
        logs_dir = Path("logs")
        if logs_dir.exists():
            result["files_found"].append("logs目录")
        else:
            result["files_missing"].append("logs目录")
            result["recommendations"].append("创建logs目录用于日志记录")
        
        # 确定状态
        if len(result["files_missing"]) == 0:
            result["status"] = "deployed"
        elif len(result["files_found"]) > 0:
            result["status"] = "partial"
        
        return result
    
    def _check_behavior_constraints(self) -> Dict[str, Any]:
        """检查行为约束配置"""
        result = {
            "status": "not_deployed",
            "files_found": [],
            "files_missing": [],
            "issues": [],
            "recommendations": []
        }
        
        # 检查行为约束配置文件
        constraints_path = Path(".kiro/settings/llm-behavior-constraints.json")
        if constraints_path.exists():
            result["files_found"].append("llm-behavior-constraints.json")
            try:
                with open(constraints_path, 'r', encoding='utf-8') as f:
                    constraints_config = json.load(f)
                    
                    # 检查必需的配置节
                    required_sections = [
                        "instruction_constraints",
                        "context_protection", 
                        "quality_thresholds",
                        "violation_handling"
                    ]
                    
                    for section in required_sections:
                        if section not in constraints_config:
                            result["issues"].append(f"行为约束配置缺少{section}节")
                    
                    result["status"] = "deployed"
                    
            except json.JSONDecodeError:
                result["issues"].append("行为约束配置JSON格式错误")
                result["status"] = "partial"
        else:
            result["files_missing"].append("llm-behavior-constraints.json")
            result["recommendations"].append("创建LLM行为约束配置文件")
        
        return result
    
    def _check_permission_matrix(self) -> Dict[str, Any]:
        """检查权限矩阵"""
        result = {
            "status": "not_deployed",
            "files_found": [],
            "files_missing": [],
            "issues": [],
            "recommendations": []
        }
        
        # 检查权限矩阵文件
        matrix_path = Path(".kiro/steering/role-permission-matrix.md")
        if matrix_path.exists():
            result["files_found"].append("role-permission-matrix.md")
            
            # 检查文件内容
            try:
                with open(matrix_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 检查是否包含关键角色
                    key_roles = [
                        "Code Review Specialist",
                        "Full-Stack Engineer", 
                        "Software Architect",
                        "Security Engineer",
                        "Test Engineer"
                    ]
                    
                    missing_roles = []
                    for role in key_roles:
                        if role not in content:
                            missing_roles.append(role)
                    
                    if missing_roles:
                        result["issues"].append(f"权限矩阵缺少角色定义: {missing_roles}")
                    else:
                        result["status"] = "deployed"
                        
            except Exception as e:
                result["issues"].append(f"无法读取权限矩阵文件: {e}")
                result["status"] = "partial"
        else:
            result["files_missing"].append("role-permission-matrix.md")
            result["recommendations"].append("创建角色权限矩阵文件")
        
        return result
    
    def generate_deployment_report(self) -> str:
        """生成部署报告"""
        deployment_data = self.check_complete_deployment()
        
        report = []
        report.append("# LLM反漂移协同系统 - 部署状态报告")
        report.append(f"**生成时间**: {deployment_data['timestamp']}")
        report.append(f"**系统版本**: {deployment_data['version']}")
        report.append(f"**总体状态**: {deployment_data['overall_status']}")
        report.append(f"**部署进度**: {deployment_data['deployment_progress']:.1f}%")
        report.append("")
        
        # 状态图标
        status_icons = {
            "deployed": "✅",
            "partial": "⚠️", 
            "not_deployed": "❌"
        }
        
        # 组件状态
        report.append("## 组件部署状态")
        for component_id, component_data in deployment_data["components"].items():
            status = component_data["status"]
            icon = status_icons.get(status, "❓")
            report.append(f"### {icon} {component_data['name']} ({status})")
            
            details = component_data["details"]
            if details.get("files_found"):
                report.append("**已部署文件**:")
                for file in details["files_found"]:
                    report.append(f"- ✅ {file}")
            
            if details.get("files_missing"):
                report.append("**缺失文件**:")
                for file in details["files_missing"]:
                    report.append(f"- ❌ {file}")
            
            if details.get("issues"):
                report.append("**问题**:")
                for issue in details["issues"]:
                    report.append(f"- ⚠️ {issue}")
            
            report.append("")
        
        # 总体问题和建议
        if deployment_data["issues"]:
            report.append("## 🚨 发现的问题")
            for issue in deployment_data["issues"]:
                report.append(f"- {issue}")
            report.append("")
        
        if deployment_data["recommendations"]:
            report.append("## 💡 改进建议")
            for recommendation in deployment_data["recommendations"]:
                report.append(f"- {recommendation}")
            report.append("")
        
        # 下一步行动
        report.append("## 🎯 下一步行动")
        if deployment_data["deployment_progress"] == 100:
            report.append("- ✅ 系统已完全部署，可以开始功能测试")
            report.append("- 🧪 执行端到端测试验证系统功能")
            report.append("- 📊 开始性能监控和优化")
        elif deployment_data["deployment_progress"] >= 80:
            report.append("- 🔧 完成剩余组件的部署")
            report.append("- 🧪 开始部分功能测试")
            report.append("- 📋 准备完整系统测试")
        else:
            report.append("- 🚀 继续部署缺失的核心组件")
            report.append("- 🔍 解决发现的配置问题")
            report.append("- 📝 更新部署文档")
        
        return "\n".join(report)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='系统部署状态检查器')
    parser.add_argument('--check', action='store_true', help='检查部署状态')
    parser.add_argument('--report', action='store_true', help='生成部署报告')
    parser.add_argument('--output', type=str, help='报告输出文件')
    
    args = parser.parse_args()
    
    checker = SystemDeploymentChecker()
    
    if args.check or args.report:
        if args.report:
            report = checker.generate_deployment_report()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"部署报告已保存到: {args.output}")
            else:
                print(report)
        else:
            results = checker.check_complete_deployment()
            print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("请使用 --check 或 --report 参数")

if __name__ == "__main__":
    main()