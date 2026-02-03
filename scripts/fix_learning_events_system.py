#!/usr/bin/env python3
"""
学习事件记录系统修复脚本

修复学习事件记录功能，确保技能学习过程可追踪。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_skills_meta_learning.core import TeamSkillsMetaLearningSystem
from team_skills_meta_learning.models import LearningEvent, LearningEventType, LearningOutcome
from datetime import datetime
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose_learning_events_issue():
    """诊断学习事件记录问题"""
    logger.info("🔍 诊断学习事件记录系统问题...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 检查学习事件列表
    events_count = len(system.learning_events)
    logger.info(f"当前学习事件数量: {events_count}")
    
    # 检查系统统计
    stats = system.get_system_stats()
    stats_events = stats.get('total_learning_events', 0)
    logger.info(f"系统统计显示的事件数量: {stats_events}")
    
    # 检查最近的学习事件
    if system.learning_events:
        latest_event = system.learning_events[-1]
        logger.info(f"最新事件ID: {latest_event.event_id}")
        logger.info(f"最新事件角色: {latest_event.role_name}")
        logger.info(f"最新事件时间: {latest_event.timestamp}")
    
    # 诊断问题
    issues = []
    
    if events_count == 0:
        issues.append("学习事件列表为空")
    
    if events_count != stats_events:
        issues.append(f"事件数量不一致: 实际{events_count} vs 统计{stats_events}")
    
    # 检查事件持久化
    try:
        # 尝试添加测试事件
        test_event_id = system.record_learning_event(
            role="Test Engineer",
            skill_id="test_skill",
            event_type=LearningEventType.SKILL_LEARNING,
            outcome=LearningOutcome.SUCCESS,
            context={"test": "diagnostic"}
        )
        
        if test_event_id:
            logger.info(f"测试事件创建成功: {test_event_id}")
            # 检查是否能找到这个事件
            found = False
            for event in system.learning_events:
                if event.event_id == test_event_id:
                    found = True
                    break
            
            if not found:
                issues.append("事件创建后无法在列表中找到")
        else:
            issues.append("无法创建测试事件")
            
    except Exception as e:
        issues.append(f"事件创建失败: {e}")
    
    return issues

def fix_learning_events_persistence():
    """修复学习事件持久化问题"""
    logger.info("🔧 修复学习事件持久化问题...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 创建一些示例学习事件来测试系统
    test_events = [
        {
            "role": "Software Architect",
            "skill_id": "system_architecture",
            "event_type": LearningEventType.SKILL_ACQUISITION,
            "outcome": LearningOutcome.SUCCESS,
            "context": {
                "method": "architecture_training",
                "priority": "high",
                "focus_area": "system_design"
            }
        },
        {
            "role": "Full-Stack Engineer",
            "skill_id": "python_programming",
            "event_type": LearningEventType.SKILL_IMPROVEMENT,
            "outcome": LearningOutcome.SUCCESS,
            "context": {
                "method": "hands_on_practice",
                "priority": "medium",
                "focus_area": "backend_development"
            }
        },
        {
            "role": "Code Review Specialist",
            "skill_id": "technical_writing",
            "event_type": LearningEventType.SKILL_ACQUISITION,
            "outcome": LearningOutcome.SUCCESS,
            "context": {
                "method": "writing_workshop",
                "priority": "medium",
                "focus_area": "documentation"
            }
        }
    ]
    
    created_events = []
    
    for event_data in test_events:
        try:
            event_id = system.record_learning_event(
                role=event_data["role"],
                skill_id=event_data["skill_id"],
                event_type=event_data["event_type"],
                outcome=event_data["outcome"],
                context=event_data["context"],
                evidence=["training_completion", "skill_demonstration"]
            )
            
            if event_id:
                created_events.append(event_id)
                logger.info(f"✅ 创建学习事件: {event_data['role']} - {event_data['skill_id']}")
            else:
                logger.error(f"❌ 创建事件失败: {event_data['role']} - {event_data['skill_id']}")
                
        except Exception as e:
            logger.error(f"❌ 创建事件异常: {e}")
    
    return created_events

def validate_learning_events_fix():
    """验证学习事件修复效果"""
    logger.info("🔍 验证学习事件修复效果...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 获取当前状态
    events_count = len(system.learning_events)
    stats = system.get_system_stats()
    stats_events = stats.get('total_learning_events', 0)
    
    # 分析事件类型分布
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
        
        # 最近事件统计
        if hasattr(event, 'timestamp'):
            days_ago = (datetime.now() - event.timestamp).days
            if days_ago <= 1:  # 最近1天
                recent_events += 1
    
    validation_result = {
        "events_count": events_count,
        "stats_events": stats_events,
        "consistency": events_count == stats_events,
        "event_types": event_types,
        "event_outcomes": event_outcomes,
        "recent_events": recent_events,
        "success_rate": round(event_outcomes.get("success", 0) / events_count * 100, 1) if events_count > 0 else 0
    }
    
    logger.info("📊 学习事件修复验证结果:")
    logger.info(f"  • 事件总数: {events_count}")
    logger.info(f"  • 统计一致性: {'✅ 一致' if validation_result['consistency'] else '❌ 不一致'}")
    logger.info(f"  • 最近事件: {recent_events}")
    logger.info(f"  • 成功率: {validation_result['success_rate']}%")
    
    if event_types:
        logger.info("  • 事件类型分布:")
        for event_type, count in event_types.items():
            logger.info(f"    - {event_type}: {count}")
    
    return validation_result

def create_learning_events_report():
    """创建学习事件系统报告"""
    logger.info("📄 创建学习事件系统报告...")
    
    # 诊断问题
    issues = diagnose_learning_events_issue()
    
    # 修复问题
    created_events = fix_learning_events_persistence()
    
    # 验证修复
    validation = validate_learning_events_fix()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "diagnosis": {
            "issues_found": len(issues),
            "issues_list": issues
        },
        "fix_actions": {
            "events_created": len(created_events),
            "created_event_ids": created_events
        },
        "validation": validation,
        "recommendations": []
    }
    
    # 生成建议
    if validation["events_count"] == 0:
        report["recommendations"].append("需要激活学习事件记录功能")
    
    if not validation["consistency"]:
        report["recommendations"].append("需要修复事件统计一致性问题")
    
    if validation["success_rate"] < 80:
        report["recommendations"].append("需要提高学习事件成功率")
    
    return report

def main():
    """主函数"""
    logger.info("🚀 启动学习事件记录系统修复...")
    
    try:
        # 创建完整报告
        report = create_learning_events_report()
        
        # 输出结果
        logger.info("📋 学习事件系统修复报告:")
        logger.info(f"  • 发现问题: {report['diagnosis']['issues_found']} 个")
        logger.info(f"  • 创建事件: {report['fix_actions']['events_created']} 个")
        logger.info(f"  • 事件总数: {report['validation']['events_count']}")
        logger.info(f"  • 统计一致性: {'✅' if report['validation']['consistency'] else '❌'}")
        logger.info(f"  • 成功率: {report['validation']['success_rate']}%")
        
        if report["recommendations"]:
            logger.info("💡 改进建议:")
            for i, rec in enumerate(report["recommendations"], 1):
                logger.info(f"  {i}. {rec}")
        
        # 保存报告
        report_path = ".kiro/reports/learning_events_fix_report.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细报告已保存到: {report_path}")
        
        # 判断修复是否成功
        success = (
            report['validation']['events_count'] > 0 and
            report['validation']['consistency'] and
            report['validation']['success_rate'] >= 80
        )
        
        if success:
            logger.info("✅ 学习事件记录系统修复成功!")
        else:
            logger.warning("⚠️ 学习事件记录系统仍需进一步修复")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 修复过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)