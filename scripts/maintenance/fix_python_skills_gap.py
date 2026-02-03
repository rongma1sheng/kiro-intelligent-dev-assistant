#!/usr/bin/env python3
"""
Python技能缺口修复脚本

解决团队中Python编程技能缺失的问题，为关键角色分配Python技能。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_skills_meta_learning.core import TeamSkillsMetaLearningSystem
from team_skills_meta_learning.models import Skill, SkillCategory, SkillLevel, LearningEvent, LearningEventType, LearningOutcome
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_python_skill(role_suffix: str = "") -> Skill:
    """创建Python编程技能"""
    return Skill(
        id=f"python_programming_{role_suffix}",
        name="Python编程",
        category=SkillCategory.TECHNICAL,
        level=SkillLevel.INTERMEDIATE,
        proficiency=0.75,  # 75%熟练度
        usage_frequency=10,
        success_rate=0.85,
        last_used=datetime.now(),
        tags=["programming", "backend", "data", "automation", "scripting", role_suffix.lower()]
    )

def create_system_architecture_skill(role_suffix: str = "") -> Skill:
    """创建系统架构技能"""
    return Skill(
        id=f"system_architecture_{role_suffix}",
        name="系统架构",
        category=SkillCategory.TECHNICAL,
        level=SkillLevel.ADVANCED,
        proficiency=0.80,  # 80%熟练度
        usage_frequency=8,
        success_rate=0.90,
        last_used=datetime.now(),
        tags=["architecture", "design", "system", "planning", role_suffix.lower()]
    )

def create_technical_writing_skill(role_suffix: str = "") -> Skill:
    """创建技术写作技能"""
    return Skill(
        id=f"technical_writing_{role_suffix}",
        name="技术写作",
        category=SkillCategory.COMMUNICATION,
        level=SkillLevel.INTERMEDIATE,
        proficiency=0.70,  # 70%熟练度
        usage_frequency=6,
        success_rate=0.80,
        last_used=datetime.now(),
        tags=["documentation", "communication", "writing", "knowledge", role_suffix.lower()]
    )

def fix_python_skills_gap():
    """修复Python技能缺口"""
    logger.info("🔧 开始修复Python技能缺口...")
    
    # 初始化系统
    system = TeamSkillsMetaLearningSystem()
    
    # 需要Python技能的关键角色
    python_roles = [
        "Full-Stack Engineer",
        "Algorithm Engineer", 
        "Data Engineer",
        "DevOps Engineer",
        "Test Engineer"
    ]
    
    # 为关键角色添加Python技能
    for role in python_roles:
        if role in system.role_profiles:
            profile = system.role_profiles[role]
            
            # 检查是否已有Python技能
            existing_python = profile.get_skill_by_name("Python编程")
            if not existing_python:
                # 添加Python技能
                python_skill = create_python_skill(role.replace(" ", "_"))
                profile.add_skill(python_skill, "primary")
                
                # 记录学习事件
                event_id = system.record_learning_event(
                    role=role,
                    skill_id="python_programming",
                    event_type=LearningEventType.SKILL_ACQUISITION,
                    outcome=LearningOutcome.SUCCESS,
                    context={
                        "method": "skill_gap_fix",
                        "priority": "high",
                        "reason": "critical_skill_missing"
                    },
                    evidence=["automated_skill_assignment", "gap_analysis_result"]
                )
                
                logger.info(f"✅ 为 {role} 添加了Python编程技能 (事件ID: {event_id})")
            else:
                logger.info(f"ℹ️ {role} 已具备Python编程技能")
    
    return system

def fix_architecture_skills_gap():
    """修复系统架构技能缺口"""
    logger.info("🏗️ 开始修复系统架构技能缺口...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 需要系统架构技能的角色
    architecture_roles = [
        "Software Architect",
        "Full-Stack Engineer",
        "Algorithm Engineer"
    ]
    
    for role in architecture_roles:
        if role in system.role_profiles:
            profile = system.role_profiles[role]
            
            existing_arch = profile.get_skill_by_name("系统架构")
            if not existing_arch:
                arch_skill = create_system_architecture_skill(role.replace(" ", "_"))
                profile.add_skill(arch_skill, "primary")
                
                event_id = system.record_learning_event(
                    role=role,
                    skill_id="system_architecture",
                    event_type=LearningEventType.SKILL_ACQUISITION,
                    outcome=LearningOutcome.SUCCESS,
                    context={
                        "method": "skill_gap_fix",
                        "priority": "high" if role == "Software Architect" else "medium",
                        "reason": "architecture_capability_missing"
                    },
                    evidence=["automated_skill_assignment", "role_requirement_analysis"]
                )
                
                logger.info(f"✅ 为 {role} 添加了系统架构技能 (事件ID: {event_id})")
    
    return system

def fix_technical_writing_gap():
    """修复技术写作技能缺口"""
    logger.info("📝 开始修复技术写作技能缺口...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 所有角色都需要基础的技术写作能力
    writing_roles = [
        "Product Manager",
        "Software Architect", 
        "Code Review Specialist",
        "Test Engineer",
        "Scrum Master/Tech Lead"
    ]
    
    for role in writing_roles:
        if role in system.role_profiles:
            profile = system.role_profiles[role]
            
            existing_writing = profile.get_skill_by_name("技术写作")
            if not existing_writing:
                writing_skill = create_technical_writing_skill(role.replace(" ", "_"))
                profile.add_skill(writing_skill, "secondary")
                
                event_id = system.record_learning_event(
                    role=role,
                    skill_id="technical_writing",
                    event_type=LearningEventType.SKILL_ACQUISITION,
                    outcome=LearningOutcome.SUCCESS,
                    context={
                        "method": "skill_gap_fix",
                        "priority": "medium",
                        "reason": "communication_skill_enhancement"
                    },
                    evidence=["automated_skill_assignment", "team_communication_needs"]
                )
                
                logger.info(f"✅ 为 {role} 添加了技术写作技能 (事件ID: {event_id})")
    
    return system

def validate_fixes():
    """验证修复效果"""
    logger.info("🔍 验证技能缺口修复效果...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 统计Python技能覆盖
    python_count = 0
    arch_count = 0
    writing_count = 0
    
    for role, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        skill_names = [s.name for s in skills if s and hasattr(s, 'name')]
        
        if "Python编程" in skill_names:
            python_count += 1
        if "系统架构" in skill_names:
            arch_count += 1
        if "技术写作" in skill_names:
            writing_count += 1
    
    # 获取系统统计
    stats = system.get_system_stats()
    
    logger.info("📊 修复效果统计:")
    logger.info(f"  • Python编程技能覆盖: {python_count}/{len(system.role_profiles)} 角色")
    logger.info(f"  • 系统架构技能覆盖: {arch_count}/{len(system.role_profiles)} 角色")
    logger.info(f"  • 技术写作技能覆盖: {writing_count}/{len(system.role_profiles)} 角色")
    logger.info(f"  • 总学习事件: {stats.get('total_learning_events', 0)}")
    logger.info(f"  • 平均熟练度: {stats.get('average_proficiency', 0):.1%}")
    
    return {
        "python_coverage": python_count,
        "architecture_coverage": arch_count,
        "writing_coverage": writing_count,
        "total_events": stats.get('total_learning_events', 0),
        "avg_proficiency": stats.get('average_proficiency', 0)
    }

def main():
    """主函数"""
    logger.info("🚀 启动Python技能缺口修复程序...")
    
    try:
        # 修复各类技能缺口
        system1 = fix_python_skills_gap()
        system2 = fix_architecture_skills_gap() 
        system3 = fix_technical_writing_gap()
        
        # 验证修复效果
        results = validate_fixes()
        
        logger.info("✅ 技能缺口修复完成!")
        logger.info("📈 修复成果:")
        logger.info(f"  • Python技能: {results['python_coverage']} 个角色获得")
        logger.info(f"  • 架构技能: {results['architecture_coverage']} 个角色获得")
        logger.info(f"  • 写作技能: {results['writing_coverage']} 个角色获得")
        logger.info(f"  • 学习事件: {results['total_events']} 个记录")
        logger.info(f"  • 平均熟练度: {results['avg_proficiency']:.1%}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 修复过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)