#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
团队技能元学习系统管理脚本

提供团队技能系统的管理、分析和优化功能。
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from team_skills_meta_learning import (
    TeamSkillsMetaLearningSystem, LearningEventType, LearningOutcome
)


class TeamSkillsManager:
    """团队技能管理器"""
    
    def __init__(self):
        self.system = TeamSkillsMetaLearningSystem(
            storage_path=".kiro/team_skills",
            enable_learning=True
        )
    
    def show_team_overview(self):
        """显示团队概览"""
        print("👥 团队技能概览")
        print("="*50)
        
        stats = self.system.get_system_stats()
        
        print(f"团队规模: {stats.get('total_roles', 0)} 个角色")
        print(f"技能总数: {stats.get('total_skills', 0)} 项")
        print(f"平均熟练度: {stats.get('average_proficiency', 0):.1%}")
        print(f"活跃角色: {stats.get('active_roles', 0)} 个")
        print(f"学习事件: {stats.get('total_learning_events', 0)} 次")
        print(f"最近活动: {stats.get('recent_activity', 0)} 次")
        
        print("\n📊 角色技能分布:")
        for role_name, profile in self.system.role_profiles.items():
            skills_count = len(profile.get_all_skills())
            proficiency = profile.calculate_overall_proficiency()
            print(f"  {role_name}: {skills_count} 项技能 (熟练度: {proficiency:.1%})")
    
    def analyze_role_skills(self, role_name: str):
        """分析角色技能"""
        print(f"🔍 分析角色: {role_name}")
        print("="*50)
        
        if role_name not in self.system.role_profiles:
            print(f"❌ 角色 '{role_name}' 不存在")
            return
        
        profile = self.system.role_profiles[role_name]
        
        print(f"整体熟练度: {profile.calculate_overall_proficiency():.1%}")
        print(f"最后更新: {profile.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n🎯 核心技能 ({len(profile.primary_skills)} 项):")
        for skill in profile.primary_skills:
            print(f"  • {skill.name}: {skill.proficiency:.1%} (使用 {skill.usage_frequency} 次)")
        
        print(f"\n🔧 辅助技能 ({len(profile.secondary_skills)} 项):")
        for skill in profile.secondary_skills:
            print(f"  • {skill.name}: {skill.proficiency:.1%} (使用 {skill.usage_frequency} 次)")
        
        print(f"\n📚 学习中技能 ({len(profile.learning_skills)} 项):")
        for skill in profile.learning_skills:
            print(f"  • {skill.name}: {skill.proficiency:.1%} (使用 {skill.usage_frequency} 次)")
        
        print(f"\n⚠️ 技能缺口 ({len(profile.skill_gaps)} 个):")
        for gap in profile.skill_gaps:
            print(f"  • {gap.skill_name}: 优先级 {gap.priority:.1f} - {gap.impact}")
    
    def identify_team_gaps(self):
        """识别团队技能缺口"""
        print("🔍 团队技能缺口分析")
        print("="*50)
        
        team_balance = self.system.optimize_team_balance()
        
        print("💪 团队优势:")
        for strength in team_balance.get('team_strengths', []):
            print(f"  • {strength['skill']}: {strength['coverage']} 人掌握 (平均熟练度: {strength['average_proficiency']:.1%})")
        
        print("\n⚠️ 团队弱点:")
        for weakness in team_balance.get('team_weaknesses', []):
            print(f"  • {weakness['skill']}: 仅 {weakness['coverage']} 人掌握 - {weakness['risk']}")
        
        print("\n🤝 协作机会:")
        for opportunity in team_balance.get('collaboration_opportunities', []):
            print(f"  • {opportunity['skill']}: {', '.join(opportunity['roles'])} - {opportunity['opportunity']}")
        
        print("\n💡 重平衡建议:")
        for suggestion in team_balance.get('rebalancing_suggestions', []):
            print(f"  • [{suggestion['type']}] {suggestion['skill']}: {suggestion['suggestion']}")
    
    def recommend_skill_development(self, role_name: str):
        """推荐技能发展"""
        print(f"💡 {role_name} 技能发展建议")
        print("="*50)
        
        if role_name not in self.system.role_profiles:
            print(f"❌ 角色 '{role_name}' 不存在")
            return
        
        recommendations = self.system.recommend_skill_development(role_name)
        
        if not recommendations:
            print("🎉 当前技能配置良好，暂无紧急发展需求")
            return
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['skill_name']} (优先级: {rec['priority']:.1f})")
            print(f"   当前水平: {rec['current_level']} → 目标水平: {rec['target_level']}")
            print(f"   预估时间: {rec['estimated_time']} 小时")
            print(f"   影响: {rec['impact']}")
            
            print("   学习路径:")
            for step in rec['learning_path']:
                print(f"     • {step}")
            
            print("   成功指标:")
            for metric in rec['success_metrics']:
                print(f"     • {metric}")
    
    def analyze_code_skills(self, role_name: str, code_file: str):
        """分析代码技能"""
        print(f"🔍 分析 {role_name} 的代码技能")
        print("="*50)
        
        try:
            with open(code_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            skills = self.system.analyze_code_skills(role_name, code_content, code_file)
            
            print(f"从 {code_file} 中识别出 {len(skills)} 项技能:")
            for skill in skills:
                print(f"  • {skill.name}: 熟练度 {skill.proficiency:.1%}")
                print(f"    标签: {', '.join(skill.tags)}")
                print(f"    证据: {len(skill.evidence)} 项")
            
        except FileNotFoundError:
            print(f"❌ 文件 '{code_file}' 不存在")
        except Exception as e:
            print(f"❌ 分析失败: {e}")
    
    def record_learning_event(self, role_name: str, skill_name: str, event_type: str, outcome: str):
        """记录学习事件"""
        print(f"📝 记录学习事件")
        print("="*50)
        
        try:
            # 转换事件类型
            event_type_map = {
                "usage": LearningEventType.SKILL_USAGE,
                "learning": LearningEventType.SKILL_LEARNING,
                "improvement": LearningEventType.SKILL_IMPROVEMENT,
                "sharing": LearningEventType.KNOWLEDGE_SHARING,
                "collaboration": LearningEventType.COLLABORATION,
                "problem_solving": LearningEventType.PROBLEM_SOLVING
            }
            
            outcome_map = {
                "success": LearningOutcome.SUCCESS,
                "partial": LearningOutcome.PARTIAL_SUCCESS,
                "failure": LearningOutcome.FAILURE,
                "learning": LearningOutcome.LEARNING
            }
            
            event_type_enum = event_type_map.get(event_type.lower())
            outcome_enum = outcome_map.get(outcome.lower())
            
            if not event_type_enum:
                print(f"❌ 无效的事件类型: {event_type}")
                print(f"可用类型: {', '.join(event_type_map.keys())}")
                return
            
            if not outcome_enum:
                print(f"❌ 无效的结果类型: {outcome}")
                print(f"可用结果: {', '.join(outcome_map.keys())}")
                return
            
            event_id = self.system.record_learning_event(
                role=role_name,
                skill_id=skill_name,
                event_type=event_type_enum,
                outcome=outcome_enum,
                context={"manual_entry": True, "timestamp": datetime.now().isoformat()}
            )
            
            print(f"✅ 成功记录学习事件: {event_id}")
            print(f"   角色: {role_name}")
            print(f"   技能: {skill_name}")
            print(f"   类型: {event_type}")
            print(f"   结果: {outcome}")
            
        except Exception as e:
            print(f"❌ 记录失败: {e}")
    
    def create_learning_plan(self):
        """创建学习计划"""
        print("📋 创建团队学习计划")
        print("="*50)
        
        learning_goals = {
            "Full-Stack Engineer": ["docker_containerization", "kubernetes"],
            "DevOps Engineer": ["python_programming", "monitoring"],
            "Security Engineer": ["penetration_testing", "compliance"],
            "Data Engineer": ["stream_processing", "mlops"],
            "Test Engineer": ["automation_testing", "performance_testing"]
        }
        
        coordination_plan = self.system.meta_coordinator.coordinate_skill_learning(
            self.system.role_profiles, learning_goals
        )
        
        print("🎯 学习协调计划:")
        
        print(f"\n👥 学习小组 ({len(coordination_plan.get('learning_groups', []))} 个):")
        for group in coordination_plan.get('learning_groups', []):
            print(f"  • {group['skill']}: {', '.join(group['members'])}")
            print(f"    策略: {group['learning_strategy']}, 时长: {group['estimated_duration']}")
        
        print(f"\n🎓 导师配对 ({len(coordination_plan.get('mentoring_pairs', []))} 对):")
        for pair in coordination_plan.get('mentoring_pairs', []):
            print(f"  • {pair['skill']}: {pair['mentor']} → {pair['learner']}")
            print(f"    导师熟练度: {pair['mentor_proficiency']:.1%}, 时长: {pair['estimated_duration']}")
        
        print(f"\n📚 个人计划 ({len(coordination_plan.get('individual_plans', {}))} 个):")
        for role, plan in coordination_plan.get('individual_plans', {}).items():
            print(f"  • {role}: {len(plan['self_directed_skills'])} 项自主学习技能")
            print(f"    时间承诺: {plan['weekly_commitment']}")
        
        resource_allocation = coordination_plan.get('resource_allocation', {})
        time_allocation = resource_allocation.get('time_allocation', {})
        print(f"\n⏰ 资源分配:")
        print(f"  • 小组学习: {time_allocation.get('group_learning', '0小时/周')}")
        print(f"  • 导师指导: {time_allocation.get('mentoring', '0小时/周')}")
        print(f"  • 个人学习: {time_allocation.get('individual_learning', '0小时/周')}")
        print(f"  • 总时间承诺: {time_allocation.get('total_weekly_commitment', '0小时/周')}")
    
    def track_progress(self):
        """跟踪学习进度"""
        print("📈 学习进度跟踪")
        print("="*50)
        
        progress_report = self.system.meta_coordinator.track_learning_progress(
            self.system.role_profiles, self.system.learning_events
        )
        
        overall_progress = progress_report.get("overall_progress", {})
        print("🎯 整体进度:")
        print(f"  • 进度率: {overall_progress.get('progress_rate', 0):.1%}")
        print(f"  • 成功率: {overall_progress.get('success_rate', 0):.1%}")
        print(f"  • 活跃度: {overall_progress.get('activity_level', 0):.1%}")
        
        print(f"\n👤 角色进度:")
        for role, progress in progress_report.get("role_progress", {}).items():
            print(f"  • {role}: {progress['status']} (成功率: {progress['success_rate']:.1%})")
        
        bottlenecks = progress_report.get("bottlenecks", [])
        if bottlenecks:
            print(f"\n⚠️ 学习瓶颈 ({len(bottlenecks)} 个):")
            for bottleneck in bottlenecks[:5]:  # 显示前5个
                print(f"  • {bottleneck['role']}: {bottleneck['skill']} - {bottleneck['issue']}")
        
        recommendations = progress_report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 改进建议:")
            for rec in recommendations:
                print(f"  • {rec}")
    
    def export_team_snapshot(self, output_file: str):
        """导出团队快照"""
        print(f"📤 导出团队快照到 {output_file}")
        print("="*50)
        
        try:
            snapshot = self.system.get_team_snapshot()
            
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"✅ 成功导出团队快照")
            print(f"   快照ID: {snapshot.snapshot_id}")
            print(f"   角色数: {len(snapshot.role_profiles)}")
            print(f"   文件大小: {Path(output_file).stat().st_size / 1024:.1f} KB")
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="团队技能元学习系统管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 团队概览
    subparsers.add_parser('overview', help='显示团队技能概览')
    
    # 角色分析
    role_parser = subparsers.add_parser('analyze-role', help='分析角色技能')
    role_parser.add_argument('role_name', help='角色名称')
    
    # 技能缺口
    subparsers.add_parser('gaps', help='识别团队技能缺口')
    
    # 技能发展建议
    recommend_parser = subparsers.add_parser('recommend', help='推荐技能发展')
    recommend_parser.add_argument('role_name', help='角色名称')
    
    # 代码技能分析
    code_parser = subparsers.add_parser('analyze-code', help='分析代码技能')
    code_parser.add_argument('role_name', help='角色名称')
    code_parser.add_argument('code_file', help='代码文件路径')
    
    # 记录学习事件
    event_parser = subparsers.add_parser('record-event', help='记录学习事件')
    event_parser.add_argument('role_name', help='角色名称')
    event_parser.add_argument('skill_name', help='技能名称')
    event_parser.add_argument('event_type', help='事件类型 (usage/learning/improvement/sharing/collaboration/problem_solving)')
    event_parser.add_argument('outcome', help='结果 (success/partial/failure/learning)')
    
    # 学习计划
    subparsers.add_parser('plan', help='创建团队学习计划')
    
    # 进度跟踪
    subparsers.add_parser('progress', help='跟踪学习进度')
    
    # 导出快照
    export_parser = subparsers.add_parser('export', help='导出团队快照')
    export_parser.add_argument('output_file', help='输出文件路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = TeamSkillsManager()
        
        if args.command == 'overview':
            manager.show_team_overview()
        elif args.command == 'analyze-role':
            manager.analyze_role_skills(args.role_name)
        elif args.command == 'gaps':
            manager.identify_team_gaps()
        elif args.command == 'recommend':
            manager.recommend_skill_development(args.role_name)
        elif args.command == 'analyze-code':
            manager.analyze_code_skills(args.role_name, args.code_file)
        elif args.command == 'record-event':
            manager.record_learning_event(args.role_name, args.skill_name, args.event_type, args.outcome)
        elif args.command == 'plan':
            manager.create_learning_plan()
        elif args.command == 'progress':
            manager.track_progress()
        elif args.command == 'export':
            manager.export_team_snapshot(args.output_file)
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())