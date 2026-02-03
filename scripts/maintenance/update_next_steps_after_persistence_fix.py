#!/usr/bin/env python3
"""
更新下一步规划 - 学习事件持久化修复完成后

基于学习事件持久化系统修复成功，更新团队技能发展的下一步规划。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
from datetime import datetime
import logging

# 导入持久化系统
from implement_learning_events_persistence import PersistentLearningEventsSystem

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def assess_current_system_status():
    """评估当前系统状态"""
    logger.info("📊 评估当前系统状态...")
    
    persistent_system = PersistentLearningEventsSystem()
    
    # 获取系统统计
    stats = persistent_system.get_system_stats()
    
    # 获取学习事件分析
    all_events = persistent_system.get_learning_events()
    
    # 分析技能覆盖情况
    skill_coverage = {}
    role_activity = {}
    
    for event in all_events:
        # 技能覆盖统计
        skill = event.skill_id
        if skill not in skill_coverage:
            skill_coverage[skill] = {"roles": set(), "events": 0}
        skill_coverage[skill]["roles"].add(event.role_name)
        skill_coverage[skill]["events"] += 1
        
        # 角色活跃度统计
        role = event.role_name
        if role not in role_activity:
            role_activity[role] = {"events": 0, "skills": set()}
        role_activity[role]["events"] += 1
        role_activity[role]["skills"].add(skill)
    
    # 转换为可序列化格式
    skill_coverage_serializable = {}
    for skill, data in skill_coverage.items():
        skill_coverage_serializable[skill] = {
            "roles": list(data["roles"]),
            "role_count": len(data["roles"]),
            "events": data["events"]
        }
    
    role_activity_serializable = {}
    for role, data in role_activity.items():
        role_activity_serializable[role] = {
            "events": data["events"],
            "skills": list(data["skills"]),
            "skill_count": len(data["skills"])
        }
    
    current_status = {
        "system_statistics": stats,
        "learning_events": {
            "total": len(all_events),
            "success_rate": round(sum(1 for e in all_events if e.outcome.value == "success") / len(all_events) * 100, 1) if all_events else 0,
            "active_roles": len(set(e.role_name for e in all_events)),
            "covered_skills": len(set(e.skill_id for e in all_events))
        },
        "skill_coverage": skill_coverage_serializable,
        "role_activity": role_activity_serializable,
        "persistence_status": "✅ 正常工作"
    }
    
    logger.info(f"系统状态评估完成:")
    logger.info(f"  • 学习事件总数: {current_status['learning_events']['total']}")
    logger.info(f"  • 成功率: {current_status['learning_events']['success_rate']}%")
    logger.info(f"  • 活跃角色: {current_status['learning_events']['active_roles']}/12")
    logger.info(f"  • 涉及技能: {current_status['learning_events']['covered_skills']} 种")
    
    return current_status

def identify_priority_actions():
    """识别优先行动项"""
    logger.info("🎯 识别优先行动项...")
    
    persistent_system = PersistentLearningEventsSystem()
    current_status = assess_current_system_status()
    
    priority_actions = []
    
    # 基于认证系统分析
    try:
        with open(".kiro/reports/skill_certification_system.json", 'r', encoding='utf-8') as f:
            cert_data = json.load(f)
            
        # 所有技能都处于"待认证"状态
        total_certifications = cert_data["statistics"]["total_certifications"]
        pending_certifications = cert_data["statistics"]["level_distribution"]["待认证"]
        
        if pending_certifications == total_certifications:
            priority_actions.append({
                "action": "启动技能认证提升计划",
                "priority": "高",
                "description": f"100%的技能({total_certifications}个)处于待认证状态",
                "target": "将至少50%的核心技能提升到初级认证水平",
                "estimated_time": "2-3周",
                "responsible": "各专业角色 + Code Review Specialist"
            })
    except Exception as e:
        logger.warning(f"无法读取认证系统数据: {e}")
    
    # 基于学习事件活跃度分析
    active_roles = current_status["learning_events"]["active_roles"]
    if active_roles < 10:  # 12人团队中少于10人活跃
        priority_actions.append({
            "action": "提高团队学习参与度",
            "priority": "中",
            "description": f"只有{active_roles}/12个角色有学习记录",
            "target": "实现至少10个角色的学习活动记录",
            "estimated_time": "1-2周",
            "responsible": "Scrum Master/Tech Lead"
        })
    
    # 基于技能覆盖分析
    covered_skills = current_status["learning_events"]["covered_skills"]
    if covered_skills < 8:  # 技能种类较少
        priority_actions.append({
            "action": "扩展技能学习范围",
            "priority": "中",
            "description": f"当前只涉及{covered_skills}种技能",
            "target": "增加到至少10种不同技能的学习记录",
            "estimated_time": "2-3周",
            "responsible": "各专业角色"
        })
    
    # 基于成功率分析
    success_rate = current_status["learning_events"]["success_rate"]
    if success_rate < 90:
        priority_actions.append({
            "action": "优化学习方法和支持机制",
            "priority": "中",
            "description": f"当前学习成功率为{success_rate}%",
            "target": "提升学习成功率到90%以上",
            "estimated_time": "持续改进",
            "responsible": "Product Manager + 各角色"
        })
    
    logger.info(f"识别出{len(priority_actions)}个优先行动项")
    return priority_actions

def create_skill_improvement_roadmap():
    """创建技能提升路线图"""
    logger.info("🗺️ 创建技能提升路线图...")
    
    # 基于认证系统数据创建路线图
    try:
        with open(".kiro/reports/skill_certification_system.json", 'r', encoding='utf-8') as f:
            cert_data = json.load(f)
        
        improvement_opportunities = cert_data["statistics"]["improvement_opportunities"]
        
        # 按改进需求排序（改进需求越小，越容易达成）
        sorted_opportunities = sorted(improvement_opportunities, key=lambda x: x["improvement_needed"])
        
        # 创建分阶段路线图
        phase_1_targets = []  # 改进需求 <= 0.02
        phase_2_targets = []  # 改进需求 <= 0.05
        phase_3_targets = []  # 改进需求 > 0.05
        
        for opp in sorted_opportunities:
            improvement_needed = opp["improvement_needed"]
            target = {
                "role": opp["role"],
                "skill": opp["skill"],
                "current_level": opp["current_level"],
                "target_level": opp["next_level"],
                "improvement_needed": improvement_needed
            }
            
            if improvement_needed <= 0.02:
                phase_1_targets.append(target)
            elif improvement_needed <= 0.05:
                phase_2_targets.append(target)
            else:
                phase_3_targets.append(target)
        
        roadmap = {
            "phase_1": {
                "name": "快速认证阶段",
                "duration": "1-2周",
                "description": "优先提升接近认证标准的技能",
                "targets": phase_1_targets,
                "success_criteria": f"完成{len(phase_1_targets)}个技能的初级认证"
            },
            "phase_2": {
                "name": "核心技能强化阶段", 
                "duration": "3-4周",
                "description": "重点提升核心技能到认证水平",
                "targets": phase_2_targets,
                "success_criteria": f"完成{len(phase_2_targets)}个核心技能的认证"
            },
            "phase_3": {
                "name": "全面技能发展阶段",
                "duration": "6-8周",
                "description": "系统性提升所有技能水平",
                "targets": phase_3_targets,
                "success_criteria": f"完成{len(phase_3_targets)}个技能的全面提升"
            }
        }
        
        logger.info(f"技能提升路线图创建完成:")
        logger.info(f"  • 阶段1: {len(phase_1_targets)} 个快速认证目标")
        logger.info(f"  • 阶段2: {len(phase_2_targets)} 个核心技能目标")
        logger.info(f"  • 阶段3: {len(phase_3_targets)} 个全面发展目标")
        
        return roadmap
        
    except Exception as e:
        logger.error(f"创建技能提升路线图失败: {e}")
        return {}

def generate_updated_next_steps():
    """生成更新的下一步规划"""
    logger.info("📋 生成更新的下一步规划...")
    
    current_status = assess_current_system_status()
    priority_actions = identify_priority_actions()
    skill_roadmap = create_skill_improvement_roadmap()
    
    # 生成综合规划
    updated_plan = {
        "timestamp": datetime.now().isoformat(),
        "status_update": "学习事件持久化系统修复完成",
        "current_achievements": {
            "learning_events_persistence": "✅ 已修复并验证",
            "total_learning_events": current_status["learning_events"]["total"],
            "system_success_rate": f"{current_status['learning_events']['success_rate']}%",
            "active_roles": f"{current_status['learning_events']['active_roles']}/12"
        },
        "immediate_priorities": {
            "next_1_week": [
                {
                    "task": "启动技能认证提升计划 - 阶段1",
                    "description": "重点提升接近认证标准的技能",
                    "targets": skill_roadmap.get("phase_1", {}).get("targets", [])[:5],  # 前5个目标
                    "responsible": "各专业角色",
                    "success_metric": "完成5个技能的初级认证"
                }
            ],
            "next_2_weeks": [
                {
                    "task": "扩展团队学习参与度",
                    "description": "确保所有角色都有学习活动记录",
                    "target": "实现12/12角色的学习记录",
                    "responsible": "Scrum Master/Tech Lead",
                    "success_metric": "学习事件覆盖所有角色"
                }
            ],
            "next_month": [
                {
                    "task": "实施技能认证提升计划 - 阶段2",
                    "description": "系统性提升核心技能水平",
                    "targets": len(skill_roadmap.get("phase_2", {}).get("targets", [])),
                    "responsible": "Product Manager + 各专业角色",
                    "success_metric": "50%以上技能达到初级认证"
                }
            ]
        },
        "priority_actions": priority_actions,
        "skill_improvement_roadmap": skill_roadmap,
        "success_metrics": {
            "short_term": {
                "learning_events_per_week": "≥10个",
                "team_participation_rate": "≥80%",
                "skill_certification_progress": "≥5个初级认证"
            },
            "medium_term": {
                "overall_certification_rate": "≥50%",
                "learning_success_rate": "≥90%",
                "skill_diversity": "≥10种技能"
            },
            "long_term": {
                "team_skill_maturity": "≥75%",
                "advanced_certifications": "≥20%",
                "mentorship_pairs": "≥6对"
            }
        }
    }
    
    return updated_plan

def main():
    """主函数"""
    logger.info("🚀 启动下一步规划更新...")
    
    try:
        # 生成更新的规划
        updated_plan = generate_updated_next_steps()
        
        # 输出关键信息
        logger.info("📋 更新的下一步规划:")
        logger.info(f"  • 当前状态: 学习事件持久化系统 ✅ 已修复")
        logger.info(f"  • 学习事件总数: {updated_plan['current_achievements']['total_learning_events']}")
        logger.info(f"  • 系统成功率: {updated_plan['current_achievements']['system_success_rate']}")
        logger.info(f"  • 优先行动项: {len(updated_plan['priority_actions'])} 个")
        
        logger.info("🎯 即时优先级:")
        for period, tasks in updated_plan["immediate_priorities"].items():
            logger.info(f"  • {period}:")
            for task in tasks:
                logger.info(f"    - {task['task']}")
        
        # 保存更新的规划
        report_path = ".kiro/reports/updated_next_steps_roadmap.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(updated_plan, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 更新的规划已保存到: {report_path}")
        
        # 生成执行建议
        logger.info("💡 执行建议:")
        logger.info("  1. 立即开始技能认证提升计划阶段1")
        logger.info("  2. 使用持久化学习事件系统记录所有学习活动")
        logger.info("  3. 每周监控学习进度和成功率")
        logger.info("  4. 建立角色间的技能指导机制")
        
        logger.info("✅ 下一步规划更新完成!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 更新规划过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)