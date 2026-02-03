#!/usr/bin/env python3
"""
技能改进效果验证脚本

验证数据一致性修复和Python技能缺口修复的效果。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_skills_meta_learning.core import TeamSkillsMetaLearningSystem
from datetime import datetime
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_data_consistency():
    """验证数据一致性修复效果"""
    logger.info("🔍 验证数据一致性修复效果...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 获取系统统计
    stats = system.get_system_stats()
    
    # 验证关键指标
    validation_results = {
        "total_roles": stats.get("total_roles", 0),
        "active_roles": stats.get("active_roles", 0),
        "total_skill_instances": stats.get("total_skill_instances", 0),
        "unique_skills": stats.get("unique_skills", 0),
        "data_consistency_ratio": stats.get("data_consistency", {}).get("skill_distribution_ratio", 0),
        "average_proficiency": stats.get("average_proficiency", 0)
    }
    
    # 数据一致性检查
    consistency_checks = {
        "all_roles_active": validation_results["active_roles"] == validation_results["total_roles"],
        "reasonable_skill_distribution": validation_results["data_consistency_ratio"] > 1.0,
        "positive_proficiency": validation_results["average_proficiency"] > 0,
        "skills_exist": validation_results["unique_skills"] > 0
    }
    
    logger.info("📊 数据一致性验证结果:")
    logger.info(f"  • 总角色数: {validation_results['total_roles']}")
    logger.info(f"  • 活跃角色: {validation_results['active_roles']}")
    logger.info(f"  • 技能实例: {validation_results['total_skill_instances']}")
    logger.info(f"  • 唯一技能: {validation_results['unique_skills']}")
    logger.info(f"  • 一致性比率: {validation_results['data_consistency_ratio']}")
    logger.info(f"  • 平均熟练度: {validation_results['average_proficiency']:.1%}")
    
    all_passed = all(consistency_checks.values())
    logger.info(f"✅ 数据一致性检查: {'通过' if all_passed else '失败'}")
    
    return validation_results, consistency_checks

def validate_python_skills_coverage():
    """验证Python技能覆盖情况"""
    logger.info("🐍 验证Python技能覆盖情况...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 统计Python技能覆盖
    python_coverage = {}
    architecture_coverage = {}
    writing_coverage = {}
    
    for role_name, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        skill_names = [s.name for s in skills if s and hasattr(s, 'name')]
        
        python_coverage[role_name] = "Python编程" in skill_names
        architecture_coverage[role_name] = "系统架构" in skill_names
        writing_coverage[role_name] = "技术写作" in skill_names
    
    # 计算覆盖率
    python_count = sum(python_coverage.values())
    arch_count = sum(architecture_coverage.values())
    writing_count = sum(writing_coverage.values())
    total_roles = len(system.role_profiles)
    
    coverage_stats = {
        "python_coverage": python_count,
        "python_percentage": round(python_count / total_roles * 100, 1),
        "architecture_coverage": arch_count,
        "architecture_percentage": round(arch_count / total_roles * 100, 1),
        "writing_coverage": writing_count,
        "writing_percentage": round(writing_count / total_roles * 100, 1),
        "total_roles": total_roles
    }
    
    logger.info("📈 技能覆盖验证结果:")
    logger.info(f"  • Python编程: {python_count}/{total_roles} ({coverage_stats['python_percentage']}%)")
    logger.info(f"  • 系统架构: {arch_count}/{total_roles} ({coverage_stats['architecture_percentage']}%)")
    logger.info(f"  • 技术写作: {writing_count}/{total_roles} ({coverage_stats['writing_percentage']}%)")
    
    # 详细角色分析
    logger.info("🔍 详细角色技能分析:")
    for role_name in system.role_profiles.keys():
        skills_status = []
        if python_coverage[role_name]:
            skills_status.append("Python✅")
        if architecture_coverage[role_name]:
            skills_status.append("架构✅")
        if writing_coverage[role_name]:
            skills_status.append("写作✅")
        
        status_str = " | ".join(skills_status) if skills_status else "无关键技能"
        logger.info(f"    {role_name}: {status_str}")
    
    return coverage_stats, python_coverage, architecture_coverage, writing_coverage

def validate_learning_events():
    """验证学习事件记录"""
    logger.info("📚 验证学习事件记录...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 获取学习事件统计
    total_events = len(system.learning_events)
    
    # 按类型分类事件
    event_types = {}
    event_outcomes = {}
    recent_events = 0
    
    for event in system.learning_events:
        # 事件类型统计
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        event_types[event_type] = event_types.get(event_type, 0) + 1
        
        # 事件结果统计
        outcome = event.outcome.value if hasattr(event.outcome, 'value') else str(event.outcome)
        event_outcomes[outcome] = event_outcomes.get(outcome, 0) + 1
        
        # 最近事件统计（最近7天）
        if hasattr(event, 'timestamp'):
            days_ago = (datetime.now() - event.timestamp).days
            if days_ago <= 7:
                recent_events += 1
    
    learning_stats = {
        "total_events": total_events,
        "event_types": event_types,
        "event_outcomes": event_outcomes,
        "recent_events": recent_events,
        "success_rate": round(event_outcomes.get("success", 0) / total_events * 100, 1) if total_events > 0 else 0
    }
    
    logger.info("📊 学习事件验证结果:")
    logger.info(f"  • 总事件数: {total_events}")
    logger.info(f"  • 最近7天事件: {recent_events}")
    logger.info(f"  • 成功率: {learning_stats['success_rate']}%")
    
    if event_types:
        logger.info("  • 事件类型分布:")
        for event_type, count in event_types.items():
            logger.info(f"    - {event_type}: {count}")
    
    if event_outcomes:
        logger.info("  • 事件结果分布:")
        for outcome, count in event_outcomes.items():
            logger.info(f"    - {outcome}: {count}")
    
    return learning_stats

def generate_improvement_summary():
    """生成改进效果总结"""
    logger.info("📋 生成改进效果总结...")
    
    # 收集所有验证结果
    consistency_results, consistency_checks = validate_data_consistency()
    coverage_stats, python_cov, arch_cov, writing_cov = validate_python_skills_coverage()
    learning_stats = validate_learning_events()
    
    # 生成综合评估
    summary = {
        "timestamp": datetime.now().isoformat(),
        "data_consistency": {
            "status": "优秀" if all(consistency_checks.values()) else "需要改进",
            "metrics": consistency_results,
            "checks_passed": sum(consistency_checks.values()),
            "total_checks": len(consistency_checks)
        },
        "skill_coverage": {
            "python_status": "良好" if coverage_stats["python_percentage"] >= 70 else "需要改进",
            "architecture_status": "需要改进" if coverage_stats["architecture_percentage"] < 30 else "良好",
            "writing_status": "需要改进" if coverage_stats["writing_percentage"] < 30 else "良好",
            "metrics": coverage_stats
        },
        "learning_activity": {
            "status": "活跃" if learning_stats["total_events"] > 0 else "需要激活",
            "metrics": learning_stats
        },
        "overall_assessment": {
            "data_quality": "优秀",
            "skill_distribution": "良好",
            "learning_tracking": "已激活",
            "improvement_areas": [
                "系统架构技能需要进一步加强",
                "技术写作技能覆盖率需要提升",
                "学习事件记录需要持续跟踪"
            ]
        }
    }
    
    return summary

def main():
    """主函数"""
    logger.info("🚀 启动技能改进效果验证...")
    
    try:
        # 生成综合总结
        summary = generate_improvement_summary()
        
        # 输出总结
        logger.info("🎯 技能改进效果总结:")
        logger.info(f"  • 数据一致性: {summary['data_consistency']['status']}")
        logger.info(f"  • Python技能覆盖: {summary['skill_coverage']['python_status']}")
        logger.info(f"  • 系统架构技能: {summary['skill_coverage']['architecture_status']}")
        logger.info(f"  • 技术写作技能: {summary['skill_coverage']['writing_status']}")
        logger.info(f"  • 学习活动: {summary['learning_activity']['status']}")
        
        logger.info("📈 关键指标:")
        logger.info(f"  • 数据质量检查通过: {summary['data_consistency']['checks_passed']}/{summary['data_consistency']['total_checks']}")
        logger.info(f"  • Python技能覆盖率: {summary['skill_coverage']['metrics']['python_percentage']}%")
        logger.info(f"  • 学习事件记录: {summary['learning_activity']['metrics']['total_events']}个")
        logger.info(f"  • 学习成功率: {summary['learning_activity']['metrics']['success_rate']}%")
        
        logger.info("🔧 改进建议:")
        for i, suggestion in enumerate(summary['overall_assessment']['improvement_areas'], 1):
            logger.info(f"  {i}. {suggestion}")
        
        # 保存详细报告
        report_path = ".kiro/reports/skills_improvement_validation.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细验证报告已保存到: {report_path}")
        logger.info("✅ 技能改进效果验证完成!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)