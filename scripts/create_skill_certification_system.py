#!/usr/bin/env python3
"""
技能认证体系创建脚本

建立Python、架构、写作技能的认证标准和评估机制。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_skills_meta_learning.core import TeamSkillsMetaLearningSystem
from team_skills_meta_learning.models import Skill, SkillCategory, SkillLevel, LearningEvent, LearningEventType, LearningOutcome
from datetime import datetime
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 技能认证标准定义
CERTIFICATION_STANDARDS = {
    "Python编程": {
        "levels": {
            "初级": {
                "proficiency_threshold": 0.6,
                "requirements": [
                    "掌握Python基础语法",
                    "能够编写简单的脚本",
                    "理解面向对象编程概念",
                    "熟悉常用标准库"
                ],
                "assessment_criteria": [
                    "代码语法正确性",
                    "基础算法实现",
                    "代码可读性",
                    "错误处理能力"
                ]
            },
            "中级": {
                "proficiency_threshold": 0.75,
                "requirements": [
                    "熟练使用Python进行项目开发",
                    "掌握异常处理和调试技巧",
                    "了解性能优化方法",
                    "能够使用第三方库"
                ],
                "assessment_criteria": [
                    "项目架构设计",
                    "代码质量和规范",
                    "性能优化能力",
                    "测试覆盖率"
                ]
            },
            "高级": {
                "proficiency_threshold": 0.9,
                "requirements": [
                    "能够设计复杂的Python应用",
                    "掌握高级特性和设计模式",
                    "具备代码审查和指导能力",
                    "能够优化系统性能"
                ],
                "assessment_criteria": [
                    "系统设计能力",
                    "代码架构质量",
                    "技术领导力",
                    "创新解决方案"
                ]
            }
        }
    },
    "系统架构设计": {
        "levels": {
            "初级": {
                "proficiency_threshold": 0.65,
                "requirements": [
                    "理解基本的系统架构概念",
                    "能够设计简单的系统结构",
                    "了解常见的架构模式",
                    "掌握基础的设计原则"
                ],
                "assessment_criteria": [
                    "架构图绘制能力",
                    "组件划分合理性",
                    "接口设计清晰度",
                    "文档完整性"
                ]
            },
            "中级": {
                "proficiency_threshold": 0.8,
                "requirements": [
                    "能够设计中等复杂度的系统",
                    "掌握微服务架构原理",
                    "了解分布式系统设计",
                    "具备性能和扩展性考虑"
                ],
                "assessment_criteria": [
                    "架构决策合理性",
                    "可扩展性设计",
                    "性能优化方案",
                    "风险评估能力"
                ]
            },
            "高级": {
                "proficiency_threshold": 0.9,
                "requirements": [
                    "能够设计大型分布式系统",
                    "掌握云原生架构设计",
                    "具备架构演进规划能力",
                    "能够指导团队架构决策"
                ],
                "assessment_criteria": [
                    "复杂系统设计",
                    "架构演进规划",
                    "技术选型决策",
                    "团队技术指导"
                ]
            }
        }
    },
    "技术文档编写": {
        "levels": {
            "初级": {
                "proficiency_threshold": 0.6,
                "requirements": [
                    "能够编写清晰的技术文档",
                    "掌握Markdown等文档格式",
                    "了解文档结构和组织",
                    "具备基础的技术表达能力"
                ],
                "assessment_criteria": [
                    "文档结构清晰度",
                    "内容准确性",
                    "语言表达能力",
                    "格式规范性"
                ]
            },
            "中级": {
                "proficiency_threshold": 0.75,
                "requirements": [
                    "能够编写API文档和用户手册",
                    "掌握技术写作最佳实践",
                    "具备读者需求分析能力",
                    "能够维护文档版本管理"
                ],
                "assessment_criteria": [
                    "文档实用性",
                    "用户体验考虑",
                    "版本管理能力",
                    "协作写作能力"
                ]
            },
            "高级": {
                "proficiency_threshold": 0.85,
                "requirements": [
                    "能够制定文档标准和规范",
                    "具备技术传播和培训能力",
                    "能够指导团队文档工作",
                    "掌握多媒体文档制作"
                ],
                "assessment_criteria": [
                    "文档标准制定",
                    "知识传播效果",
                    "团队指导能力",
                    "创新表达方式"
                ]
            }
        }
    }
}

def create_certification_framework():
    """创建技能认证框架"""
    logger.info("🏆 创建技能认证框架...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 分析当前技能水平
    certification_results = {}
    
    for role_name, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        role_certifications = {}
        
        for skill in skills:
            if skill and hasattr(skill, 'name') and skill.name in CERTIFICATION_STANDARDS:
                skill_name = skill.name
                proficiency = getattr(skill, 'proficiency', 0.0)
                
                # 确定认证等级
                certification_level = determine_certification_level(skill_name, proficiency)
                
                role_certifications[skill_name] = {
                    "current_proficiency": proficiency,
                    "certification_level": certification_level,
                    "next_level": get_next_certification_level(skill_name, certification_level),
                    "improvement_needed": calculate_improvement_needed(skill_name, proficiency)
                }
        
        if role_certifications:
            certification_results[role_name] = role_certifications
    
    return certification_results

def determine_certification_level(skill_name, proficiency):
    """确定技能认证等级"""
    if skill_name not in CERTIFICATION_STANDARDS:
        return "未认证"
    
    levels = CERTIFICATION_STANDARDS[skill_name]["levels"]
    
    if proficiency >= levels["高级"]["proficiency_threshold"]:
        return "高级"
    elif proficiency >= levels["中级"]["proficiency_threshold"]:
        return "中级"
    elif proficiency >= levels["初级"]["proficiency_threshold"]:
        return "初级"
    else:
        return "待认证"

def get_next_certification_level(skill_name, current_level):
    """获取下一个认证等级"""
    level_progression = ["待认证", "初级", "中级", "高级"]
    
    if current_level == "未认证" or current_level not in level_progression:
        return "初级"
    
    current_index = level_progression.index(current_level)
    if current_index < len(level_progression) - 1:
        return level_progression[current_index + 1]
    else:
        return "已达最高级"

def calculate_improvement_needed(skill_name, current_proficiency):
    """计算达到下一等级所需的改进"""
    if skill_name not in CERTIFICATION_STANDARDS:
        return 0.0
    
    levels = CERTIFICATION_STANDARDS[skill_name]["levels"]
    
    for level_name, level_info in [("初级", levels["初级"]), ("中级", levels["中级"]), ("高级", levels["高级"])]:
        threshold = level_info["proficiency_threshold"]
        if current_proficiency < threshold:
            return round(threshold - current_proficiency, 2)
    
    return 0.0

def generate_certification_report():
    """生成技能认证报告"""
    logger.info("📊 生成技能认证报告...")
    
    certification_results = create_certification_framework()
    
    # 统计认证分布
    certification_stats = {
        "total_certifications": 0,
        "level_distribution": {"待认证": 0, "初级": 0, "中级": 0, "高级": 0},
        "skill_distribution": {},
        "improvement_opportunities": []
    }
    
    for role_name, certifications in certification_results.items():
        for skill_name, cert_info in certifications.items():
            certification_stats["total_certifications"] += 1
            
            level = cert_info["certification_level"]
            certification_stats["level_distribution"][level] = certification_stats["level_distribution"].get(level, 0) + 1
            
            if skill_name not in certification_stats["skill_distribution"]:
                certification_stats["skill_distribution"][skill_name] = {"待认证": 0, "初级": 0, "中级": 0, "高级": 0}
            
            certification_stats["skill_distribution"][skill_name][level] += 1
            
            # 识别改进机会
            if cert_info["improvement_needed"] > 0:
                certification_stats["improvement_opportunities"].append({
                    "role": role_name,
                    "skill": skill_name,
                    "current_level": level,
                    "next_level": cert_info["next_level"],
                    "improvement_needed": cert_info["improvement_needed"]
                })
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "certification_framework": CERTIFICATION_STANDARDS,
        "certification_results": certification_results,
        "statistics": certification_stats,
        "recommendations": generate_certification_recommendations(certification_stats)
    }
    
    return report

def generate_certification_recommendations(stats):
    """生成认证改进建议"""
    recommendations = []
    
    # 基于等级分布的建议
    total_certs = stats["total_certifications"]
    if total_certs > 0:
        waiting_ratio = stats["level_distribution"]["待认证"] / total_certs
        if waiting_ratio > 0.3:
            recommendations.append({
                "type": "urgent",
                "title": "大量技能待认证",
                "description": f"{waiting_ratio:.1%}的技能处于待认证状态，需要优先提升",
                "action": "制定技能提升计划，优先培训基础技能"
            })
    
    # 基于技能分布的建议
    for skill_name, distribution in stats["skill_distribution"].items():
        total_skill_certs = sum(distribution.values())
        if total_skill_certs > 0:
            advanced_ratio = distribution["高级"] / total_skill_certs
            if advanced_ratio < 0.2:
                recommendations.append({
                    "type": "improvement",
                    "title": f"{skill_name}高级人才不足",
                    "description": f"只有{advanced_ratio:.1%}的{skill_name}技能达到高级水平",
                    "action": f"培养{skill_name}领域的技术专家和导师"
                })
    
    # 基于改进机会的建议
    improvement_opps = stats["improvement_opportunities"]
    if len(improvement_opps) > 5:
        recommendations.append({
            "type": "opportunity",
            "title": "大量技能提升机会",
            "description": f"发现{len(improvement_opps)}个技能提升机会",
            "action": "实施系统性的技能发展计划"
        })
    
    return recommendations

def main():
    """主函数"""
    logger.info("🚀 启动技能认证体系创建...")
    
    try:
        # 生成认证报告
        report = generate_certification_report()
        
        # 输出关键信息
        logger.info("🏆 技能认证体系创建完成!")
        logger.info("📊 认证统计:")
        logger.info(f"  • 总认证数: {report['statistics']['total_certifications']}")
        logger.info(f"  • 等级分布:")
        for level, count in report['statistics']['level_distribution'].items():
            logger.info(f"    - {level}: {count}")
        
        logger.info("💡 改进建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            logger.info(f"  {i}. {rec['title']} ({rec['type']})")
            logger.info(f"     {rec['description']}")
        
        # 保存报告
        report_path = ".kiro/reports/skill_certification_system.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细认证报告已保存到: {report_path}")
        logger.info("✅ 技能认证体系建立成功!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 认证体系创建过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)