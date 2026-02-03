#!/usr/bin/env python33
# -*- coding: utf-8 -*-
"""
硅谷12人团队协作Bug修复系统

🎯 团队角色分工修复违规问题
- 按照硅谷12人团队标准分配任务
- 严格遵循角色职责边界
- 确保所有铁律合规性

角色分工:
📊 Product Manager: 需求确认和优先级决策
🏗️ Software Architect: 架构问题和技术决策  
🧮 Algorithm Engineer: 算法和性能优化
🗄️ Database Engineer: 数据相关问题
🎨 UI/UX Engineer: 界面和用户体验
🚀 Full-Stack Engineer: 代码实现和集成
🔒 Security Engineer: 安全和合规问题
☁️ DevOps Engineer: 基础设施和部署
📈 Data Engineer: 数据管道和处理
🧪 Test Engineer: 测试策略和质量保证
🎯 Scrum Master/Tech Lead: 流程管理和协调
🔍 Code Review Specialist: 代码审查和质量验证
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class TeamBugFixer:
    """硅谷12人团队协作Bug修复系统"""
    
    def __init__(self):
        self.team_roles = {
            "Product Manager": {
                "emoji": "📊",
                "responsibilities": ["需求确认", "优先级决策", "业务规则"],
                "handles": ["ZERO_LAW", "business_logic", "requirements"]
            },
            "Software Architect": {
                "emoji": "🏗️", 
                "responsibilities": ["架构设计", "技术决策", "系统集成"],
                "handles": ["architecture", "design_patterns", "system_design"]
            },
            "Algorithm Engineer": {
                "emoji": "🧮",
                "responsibilities": ["算法优化", "性能分析", "复杂度优化"],
                "handles": ["performance", "algorithms", "optimization"]
            },
            "Database Engineer": {
                "emoji": "🗄️",
                "responsibilities": ["数据库设计", "查询优化", "数据模型"],
                "handles": ["database", "sql", "data_model"]
            },
            "UI/UX Engineer": {
                "emoji": "🎨",
                "responsibilities": ["界面设计", "用户体验", "可用性"],
                "handles": ["ui", "ux", "interface", "usability"]
            },
            "Full-Stack Engineer": {
                "emoji": "🚀",
                "responsibilities": ["代码实现", "API开发", "功能集成"],
                "handles": ["CODE_BUGS", "implementation", "api", "integration"]
            },
            "Security Engineer": {
                "emoji": "🔒",
                "responsibilities": ["安全架构", "合规检查", "风险评估"],
                "handles": ["security", "compliance", "vulnerability", "auth"]
            },
            "DevOps Engineer": {
                "emoji": "☁️",
                "responsibilities": ["基础设施", "部署管道", "环境管理"],
                "handles": ["deployment", "infrastructure", "ci_cd", "environment"]
            },
            "Data Engineer": {
                "emoji": "📈",
                "responsibilities": ["数据管道", "ETL流程", "数据质量"],
                "handles": ["data_pipeline", "etl", "data_processing"]
            },
            "Test Engineer": {
                "emoji": "🧪",
                "responsibilities": ["测试策略", "质量保证", "自动化测试"],
                "handles": ["TEST_LAW", "testing", "quality", "coverage"]
            },
            "Scrum Master/Tech Lead": {
                "emoji": "🎯",
                "responsibilities": ["流程管理", "团队协调", "项目管理"],
                "handles": ["TEAM_LAW", "process", "coordination", "management"]
            },
            "Code Review Specialist": {
                "emoji": "🔍",
                "responsibilities": ["代码审查", "质量标准", "最佳实践"],
                "handles": ["CORE_LAW", "code_review", "standards", "best_practices"]
            }
        }
    
    def analyze_violations(self, violations: Dict[str, List[Any]]) -> Dict[str, List[Dict]]:
        """分析违规并分配给对应角色"""
        role_assignments = {}
        
        for violation_type, violation_list in violations.items():
            if not violation_list:
                continue
                
            for violation in violation_list:
                assigned_role = self._assign_to_role(violation_type, violation)
                
                if assigned_role not in role_assignments:
                    role_assignments[assigned_role] = []
                    
                role_assignments[assigned_role].append({
                    "violation_type": violation_type,
                    "violation": violation,
                    "priority": self._get_priority(violation_type)
                })
        
        return role_assignments
    
    def _assign_to_role(self, violation_type: str, violation: Dict[str, Any]) -> str:
        """将违规分配给对应角色"""
        # 直接映射的违规类型
        direct_mappings = {
            "ZERO_LAW": "Product Manager",
            "CORE_LAW": "Code Review Specialist", 
            "TEST_LAW": "Test Engineer",
            "TEAM_LAW": "Scrum Master/Tech Lead",
            "CODE_BUGS": "Full-Stack Engineer"
        }
        
        if violation_type in direct_mappings:
            return direct_mappings[violation_type]
        
        # 基于文件路径和内容的智能分配
        file_path = violation.get("file", "").lower()
        description = violation.get("description", "").lower()
        
        # 安全相关
        if any(keyword in file_path or keyword in description 
               for keyword in ["security", "auth", "crypto", "ssl", "compliance"]):
            return "Security Engineer"
            
        # 数据库相关
        if any(keyword in file_path or keyword in description
               for keyword in ["database", "sql", "model", "migration"]):
            return "Database Engineer"
            
        # 测试相关
        if any(keyword in file_path or keyword in description
               for keyword in ["test", "spec", "coverage", "pytest"]):
            return "Test Engineer"
            
        # 基础设施相关
        if any(keyword in file_path or keyword in description
               for keyword in ["deploy", "docker", "ci", "cd", "infra"]):
            return "DevOps Engineer"
            
        # 数据处理相关
        if any(keyword in file_path or keyword in description
               for keyword in ["data", "etl", "pipeline", "processing"]):
            return "Data Engineer"
            
        # 算法和性能相关
        if any(keyword in file_path or keyword in description
               for keyword in ["algorithm", "performance", "optimization", "complexity"]):
            return "Algorithm Engineer"
            
        # UI/UX相关
        if any(keyword in file_path or keyword in description
               for keyword in ["ui", "ux", "interface", "dashboard", "frontend"]):
            return "UI/UX Engineer"
            
        # 架构相关
        if any(keyword in file_path or keyword in description
               for keyword in ["architecture", "design", "pattern", "system"]):
            return "Software Architect"
            
        # 默认分配给Full-Stack Engineer
        return "Full-Stack Engineer"
    
    def _get_priority(self, violation_type: str) -> str:
        """获取违规优先级"""
        priority_map = {
            "ZERO_LAW": "CRITICAL",
            "TEST_LAW": "CRITICAL", 
            "CORE_LAW": "HIGH",
            "TEAM_LAW": "HIGH",
            "CODE_BUGS": "MEDIUM"
        }
        return priority_map.get(violation_type, "LOW")
    
    def generate_team_assignments(self, violations: Dict[str, List[Any]]) -> str:
        """生成团队任务分配报告"""
        role_assignments = self.analyze_violations(violations)
        
        if not role_assignments:
            return "🎉 没有发现需要团队处理的违规问题！"
        
        report = []
        report.append("🎯 硅谷12人团队协作任务分配")
        report.append("=" * 80)
        report.append("")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总任务数: {sum(len(tasks) for tasks in role_assignments.values())}")
        report.append("")
        
        # 按优先级排序角色
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_roles = sorted(role_assignments.items(), 
                            key=lambda x: min(priority_order.get(task["priority"], 3) 
                                             for task in x[1]))
        
        for role_name, tasks in sorted_roles:
            role_info = self.team_roles[role_name]
            task_count = len(tasks)
            
            # 统计优先级
            priority_counts = {}
            for task in tasks:
                priority = task["priority"]
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            priority_str = ", ".join(f"{p}: {c}" for p, c in priority_counts.items())
            
            report.append(f"{role_info['emoji']} {role_name}")
            report.append(f"   任务数: {task_count} ({priority_str})")
            report.append(f"   职责: {', '.join(role_info['responsibilities'])}")
            report.append("")
            
            # 显示前5个任务
            for i, task in enumerate(tasks[:5], 1):
                violation = task["violation"]
                file_path = violation.get("file", "unknown")
                line = violation.get("line", 0)
                desc = violation.get("description", "")[:80]
                priority = task["priority"]
                
                priority_emoji = {
                    "CRITICAL": "🚨",
                    "HIGH": "⚠️",
                    "MEDIUM": "📋", 
                    "LOW": "💡"
                }.get(priority, "📋")
                
                report.append(f"   {i}. {priority_emoji} {file_path}:{line}")
                report.append(f"      {desc}")
                report.append("")
            
            if len(tasks) > 5:
                report.append(f"   ... 还有 {len(tasks) - 5} 个任务")
                report.append("")
            
            report.append("-" * 60)
            report.append("")
        
        # 添加协作指导
        report.append("🤝 团队协作指导")
        report.append("=" * 80)
        report.append("")
        report.append("1. 🚨 CRITICAL任务优先处理（零号铁律+测试铁律）")
        report.append("2. ⚠️ HIGH任务其次处理（核心铁律+团队标准）")
        report.append("3. 📋 MEDIUM任务最后处理（代码质量）")
        report.append("")
        report.append("角色协作原则:")
        report.append("- 每个角色专注自己的职责范围")
        report.append("- 跨角色问题需要协调讨论")
        report.append("- 严禁角色越权处理非本职责问题")
        report.append("- 所有修复必须经过Code Review Specialist审查")
        report.append("")
        report.append("修复流程:")
        report.append("1. 各角色按分配任务进行修复")
        report.append("2. 提交修复后运行质量门禁验证")
        report.append("3. 确保所有铁律合规性")
        report.append("4. 团队协作解决复杂问题")
        report.append("")
        
        return "/n".join(report)
    
    def save_team_report(self, violations: Dict[str, List[Any]]) -> Path:
        """保存团队分配报告"""
        report_content = self.generate_team_assignments(violations)
        
        # 保存文本报告
        report_path = Path("reports") / f"team_assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report_content, encoding='utf-8')
        
        # 保存JSON数据
        json_path = report_path.with_suffix('.json')
        role_assignments = self.analyze_violations(violations)
        
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": sum(len(tasks) for tasks in role_assignments.values()),
            "role_assignments": role_assignments,
            "team_roles": self.team_roles
        }
        
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), 
                            encoding='utf-8')
        
        return report_path


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python scripts/team_bug_fixer.py <violations_json_file>")
        print("或者: python scripts/team_bug_fixer.py src  # 自动运行质量检查")
        return 1
    
    target = sys.argv[1]
    
    # 如果参数是目录，先运行质量检查
    if Path(target).is_dir():
        print("🔍 运行质量检查...")
        from enhanced_quality_gate import EnhancedQualityGate
        
        gate = EnhancedQualityGate()
        is_compliant, violations = gate.run_comprehensive_check(target)
        
        if is_compliant:
            print("✅ 没有发现违规问题，无需团队修复！")
            return 0
    else:
        # 从JSON文件加载违规数据
        try:
            violations_file = Path(target)
            violations_data = json.loads(violations_file.read_text(encoding='utf-8'))
            violations = violations_data.get("violations", {})
        except Exception as e:
            print(f"❌ 无法加载违规数据: {e}")
            return 1
    
    # 生成团队分配
    fixer = TeamBugFixer()
    report_path = fixer.save_team_report(violations)
    
    print(fixer.generate_team_assignments(violations))
    print(f"📄 团队分配报告已保存: {report_path}")
    print(f"📄 JSON数据已保存: {report_path.with_suffix('.json')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())