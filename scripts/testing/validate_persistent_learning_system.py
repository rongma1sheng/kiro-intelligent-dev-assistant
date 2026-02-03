#!/usr/bin/env python3
"""
验证持久化学习事件系统

使用新的持久化系统验证学习事件记录和存储功能。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
from datetime import datetime, timedelta
import logging

# 导入持久化系统
from implement_learning_events_persistence import PersistentLearningEventsSystem
from team_skills_meta_learning.models import LearningEventType, LearningOutcome

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_persistent_system_functionality():
    """测试持久化系统功能"""
    logger.info("🔍 测试持久化系统功能...")
    
    # 创建持久化系统实例
    persistent_system = PersistentLearningEventsSystem()
    
    # 测试1: 检查现有事件
    existing_events = persistent_system.get_learning_events()
    logger.info(f"现有学习事件数量: {len(existing_events)}")
    
    # 测试2: 创建新的学习事件
    new_event_id = persistent_system.record_learning_event(
        role="Algorithm Engineer",
        skill_id="python_programming",
        event_type=LearningEventType.SKILL_IMPROVEMENT,
        outcome=LearningOutcome.SUCCESS,
        context={
            "method": "algorithm_optimization",
            "focus": "performance_tuning",
            "duration_hours": 3,
            "validation_test": True
        }
    )
    
    logger.info(f"新创建事件ID: {new_event_id}")
    
    # 测试3: 验证事件持久化
    updated_events = persistent_system.get_learning_events()
    logger.info(f"更新后事件数量: {len(updated_events)}")
    
    # 测试4: 重新加载系统验证持久化
    new_persistent_system = PersistentLearningEventsSystem()
    reloaded_events = new_persistent_system.get_learning_events()
    logger.info(f"重新加载后事件数量: {len(reloaded_events)}")
    
    # 测试5: 按角色过滤事件
    architect_events = persistent_system.get_learning_events(role="Software Architect")
    engineer_events = persistent_system.get_learning_events(role="Full-Stack Engineer")
    
    logger.info(f"Software Architect 事件数量: {len(architect_events)}")
    logger.info(f"Full-Stack Engineer 事件数量: {len(engineer_events)}")
    
    # 测试6: 按时间过滤事件
    recent_events = persistent_system.get_learning_events(days=1)
    logger.info(f"最近1天事件数量: {len(recent_events)}")
    
    return {
        "existing_events": len(existing_events),
        "new_event_created": new_event_id is not None,
        "events_after_creation": len(updated_events),
        "events_after_reload": len(reloaded_events),
        "persistence_working": len(reloaded_events) > 0,
        "architect_events": len(architect_events),
        "engineer_events": len(engineer_events),
        "recent_events": len(recent_events)
    }

def analyze_learning_patterns():
    """分析学习模式"""
    logger.info("📊 分析学习模式...")
    
    persistent_system = PersistentLearningEventsSystem()
    all_events = persistent_system.get_learning_events()
    
    if not all_events:
        logger.warning("没有学习事件数据可供分析")
        return {}
    
    # 按角色统计
    role_stats = {}
    for event in all_events:
        role = event.role_name
        if role not in role_stats:
            role_stats[role] = {
                "total_events": 0,
                "success_events": 0,
                "skills": set(),
                "event_types": set()
            }
        
        role_stats[role]["total_events"] += 1
        if event.outcome == LearningOutcome.SUCCESS:
            role_stats[role]["success_events"] += 1
        role_stats[role]["skills"].add(event.skill_id)
        role_stats[role]["event_types"].add(event.event_type.value)
    
    # 转换为可序列化格式
    analysis_result = {}
    for role, stats in role_stats.items():
        analysis_result[role] = {
            "total_events": stats["total_events"],
            "success_events": stats["success_events"],
            "success_rate": round(stats["success_events"] / stats["total_events"] * 100, 1),
            "unique_skills": len(stats["skills"]),
            "skills_list": list(stats["skills"]),
            "event_types": list(stats["event_types"])
        }
    
    # 整体统计
    total_events = len(all_events)
    success_events = sum(1 for e in all_events if e.outcome == LearningOutcome.SUCCESS)
    unique_skills = len(set(e.skill_id for e in all_events))
    unique_roles = len(set(e.role_name for e in all_events))
    
    overall_stats = {
        "total_events": total_events,
        "success_events": success_events,
        "overall_success_rate": round(success_events / total_events * 100, 1) if total_events > 0 else 0,
        "unique_skills": unique_skills,
        "active_roles": unique_roles,
        "average_events_per_role": round(total_events / unique_roles, 1) if unique_roles > 0 else 0
    }
    
    logger.info(f"学习模式分析完成:")
    logger.info(f"  • 总事件数: {overall_stats['total_events']}")
    logger.info(f"  • 成功率: {overall_stats['overall_success_rate']}%")
    logger.info(f"  • 涉及技能: {overall_stats['unique_skills']} 个")
    logger.info(f"  • 活跃角色: {overall_stats['active_roles']} 个")
    
    return {
        "overall_statistics": overall_stats,
        "role_statistics": analysis_result
    }

def generate_learning_recommendations():
    """生成学习建议"""
    logger.info("💡 生成学习建议...")
    
    persistent_system = PersistentLearningEventsSystem()
    stats = persistent_system.get_system_stats()
    
    recommendations = []
    
    # 基于事件数量的建议
    total_events = stats.get("total_learning_events", 0)
    if total_events < 10:
        recommendations.append({
            "type": "activity",
            "priority": "high",
            "title": "增加学习活动频率",
            "description": f"当前仅有{total_events}个学习事件，建议增加学习活动记录",
            "action": "每周至少记录2-3个学习事件"
        })
    
    # 基于角色参与度的建议
    all_events = persistent_system.get_learning_events()
    active_roles = set(e.role_name for e in all_events)
    total_roles = 12  # 硅谷12人团队
    
    if len(active_roles) < total_roles * 0.7:
        recommendations.append({
            "type": "participation",
            "priority": "medium",
            "title": "提高团队参与度",
            "description": f"只有{len(active_roles)}/{total_roles}个角色有学习记录",
            "action": "鼓励所有角色参与技能学习和记录"
        })
    
    # 基于技能覆盖的建议
    covered_skills = set(e.skill_id for e in all_events)
    if len(covered_skills) < 5:
        recommendations.append({
            "type": "skill_diversity",
            "priority": "medium", 
            "title": "扩展技能学习范围",
            "description": f"当前只涉及{len(covered_skills)}种技能",
            "action": "增加不同类型技能的学习，如软技能、工具技能等"
        })
    
    # 基于成功率的建议
    success_events = sum(1 for e in all_events if e.outcome == LearningOutcome.SUCCESS)
    success_rate = (success_events / len(all_events) * 100) if all_events else 0
    
    if success_rate < 80:
        recommendations.append({
            "type": "quality",
            "priority": "high",
            "title": "提高学习效果",
            "description": f"当前学习成功率为{success_rate:.1f}%",
            "action": "分析失败原因，改进学习方法和支持机制"
        })
    
    logger.info(f"生成了{len(recommendations)}条学习建议")
    return recommendations

def main():
    """主函数"""
    logger.info("🚀 启动持久化学习事件系统验证...")
    
    try:
        # 测试系统功能
        functionality_test = test_persistent_system_functionality()
        
        # 分析学习模式
        learning_analysis = analyze_learning_patterns()
        
        # 生成学习建议
        recommendations = generate_learning_recommendations()
        
        # 生成综合报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "validation_status": "completed",
            "functionality_test": functionality_test,
            "learning_analysis": learning_analysis,
            "recommendations": recommendations,
            "summary": {
                "persistence_working": functionality_test.get("persistence_working", False),
                "total_events": functionality_test.get("events_after_reload", 0),
                "system_health": "healthy" if functionality_test.get("persistence_working") else "needs_attention"
            }
        }
        
        # 输出结果
        logger.info("📋 持久化学习事件系统验证报告:")
        logger.info(f"  • 持久化功能: {'✅ 正常' if functionality_test.get('persistence_working') else '❌ 异常'}")
        logger.info(f"  • 事件总数: {functionality_test.get('events_after_reload', 0)}")
        logger.info(f"  • 活跃角色: {learning_analysis.get('overall_statistics', {}).get('active_roles', 0)}")
        logger.info(f"  • 整体成功率: {learning_analysis.get('overall_statistics', {}).get('overall_success_rate', 0)}%")
        logger.info(f"  • 改进建议: {len(recommendations)} 条")
        
        if recommendations:
            logger.info("💡 主要建议:")
            for i, rec in enumerate(recommendations[:3], 1):  # 显示前3条
                logger.info(f"  {i}. {rec['title']}")
        
        # 保存详细报告
        report_path = ".kiro/reports/persistent_learning_system_validation.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细报告已保存到: {report_path}")
        
        # 判断验证是否成功
        success = (
            functionality_test.get("persistence_working", False) and
            functionality_test.get("events_after_reload", 0) > 0
        )
        
        if success:
            logger.info("✅ 持久化学习事件系统验证成功!")
        else:
            logger.warning("⚠️ 持久化学习事件系统验证发现问题")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 验证过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)