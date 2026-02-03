#!/usr/bin/env python3
"""
技能验证一致性修复脚本

修复技能添加与验证之间的不一致问题，确保技能覆盖率统计准确。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_skills_meta_learning.core import TeamSkillsMetaLearningSystem
from team_skills_meta_learning.models import Skill, SkillCategory, SkillLevel
from datetime import datetime
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 技能名称标准化常量
SKILL_NAMES = {
    "PYTHON_PROGRAMMING": "Python编程",
    "SYSTEM_ARCHITECTURE": "系统架构设计",
    "TECHNICAL_WRITING": "技术文档编写",
    "CODE_REVIEW_WRITING": "代码审查写作",
    "REQUIREMENTS_WRITING": "需求文档写作",
    "MICROSERVICES_ARCHITECTURE": "微服务架构",
    "CLOUD_ARCHITECTURE": "云架构设计",
    "ALGORITHM_SYSTEM_ARCHITECTURE": "算法系统架构",
    "FULLSTACK_ARCHITECTURE": "全栈架构设计"
}

def diagnose_skill_validation_inconsistency():
    """诊断技能验证不一致问题"""
    logger.info("🔍 诊断技能验证不一致问题...")
    
    system = TeamSkillsMetaLearningSystem()
    
    inconsistencies = []
    
    # 检查每个角色的技能
    for role_name, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        
        logger.info(f"检查角色: {role_name}")
        logger.info(f"  技能数量: {len(skills)}")
        
        for skill in skills:
            if skill and hasattr(skill, 'name'):
                logger.info(f"  - {skill.name} (ID: {getattr(skill, 'id', 'N/A')})")
            else:
                inconsistencies.append(f"{role_name}: 发现无效技能对象")
    
    # 使用不同方法统计技能覆盖率
    python_count_method1 = 0
    python_count_method2 = 0
    arch_count_method1 = 0
    arch_count_method2 = 0
    
    # 方法1: 精确匹配
    for role_name, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        skill_names = [s.name for s in skills if s and hasattr(s, 'name')]
        
        if "Python编程" in skill_names:
            python_count_method1 += 1
        if "系统架构设计" in skill_names:
            arch_count_method1 += 1
    
    # 方法2: 模糊匹配
    for role_name, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        
        for skill in skills:
            if skill and hasattr(skill, 'name') and skill.name:
                skill_name = skill.name.lower()
                if "python" in skill_name or "Python" in skill.name:
                    python_count_method2 += 1
                    break
        
        for skill in skills:
            if skill and hasattr(skill, 'name') and skill.name:
                skill_name = skill.name.lower()
                if "架构" in skill.name or "architecture" in skill_name:
                    arch_count_method2 += 1
                    break
    
    logger.info("📊 技能统计对比:")
    logger.info(f"  Python技能 - 精确匹配: {python_count_method1}, 模糊匹配: {python_count_method2}")
    logger.info(f"  架构技能 - 精确匹配: {arch_count_method1}, 模糊匹配: {arch_count_method2}")
    
    if python_count_method1 != python_count_method2:
        inconsistencies.append(f"Python技能统计不一致: {python_count_method1} vs {python_count_method2}")
    
    if arch_count_method1 != arch_count_method2:
        inconsistencies.append(f"架构技能统计不一致: {arch_count_method1} vs {arch_count_method2}")
    
    return inconsistencies

def standardize_skill_names():
    """标准化技能名称"""
    logger.info("🔧 标准化技能名称...")
    
    system = TeamSkillsMetaLearningSystem()
    
    standardized_count = 0
    
    for role_name, profile in system.role_profiles.items():
        skills = profile.get_all_skills()
        
        for skill in skills:
            if skill and hasattr(skill, 'name') and skill.name:
                original_name = skill.name
                standardized_name = None
                
                # 标准化Python技能名称
                if "python" in original_name.lower() and "编程" not in original_name:
                    standardized_name = SKILL_NAMES["PYTHON_PROGRAMMING"]
                
                # 标准化架构技能名称
                elif "架构" in original_name and "设计" not in original_name:
                    if "系统" in original_name:
                        standardized_name = SKILL_NAMES["SYSTEM_ARCHITECTURE"]
                    elif "微服务" in original_name:
                        standardized_name = SKILL_NAMES["MICROSERVICES_ARCHITECTURE"]
                    elif "云" in original_name:
                        standardized_name = SKILL_NAMES["CLOUD_ARCHITECTURE"]
                    elif "算法" in original_name:
                        standardized_name = SKILL_NAMES["ALGORITHM_SYSTEM_ARCHITECTURE"]
                    elif "全栈" in original_name:
                        standardized_name = SKILL_NAMES["FULLSTACK_ARCHITECTURE"]
                
                # 标准化写作技能名称
                elif "写作" in original_name or "文档" in original_name:
                    if "技术" in original_name:
                        standardized_name = SKILL_NAMES["TECHNICAL_WRITING"]
                    elif "代码" in original_name or "审查" in original_name:
                        standardized_name = SKILL_NAMES["CODE_REVIEW_WRITING"]
                    elif "需求" in original_name:
                        standardized_name = SKILL_NAMES["REQUIREMENTS_WRITING"]
                
                if standardized_name and standardized_name != original_name:
                    skill.name = standardized_name
                    standardized_count += 1
                    logger.info(f"✅ 标准化技能名称: {role_name} - {original_name} → {standardized_name}")
    
    logger.info(f"📈 共标准化了 {standardized_count} 个技能名称")
    return standardized_count

def create_unified_skill_validation():
    """创建统一的技能验证函数"""
    logger.info("🔧 创建统一的技能验证函数...")
    
    def validate_skill_coverage_unified(system):
        """统一的技能覆盖率验证函数"""
        coverage_stats = {
            "python_programming": {"roles": [], "count": 0},
            "system_architecture": {"roles": [], "count": 0},
            "technical_writing": {"roles": [], "count": 0}
        }
        
        for role_name, profile in system.role_profiles.items():
            skills = profile.get_all_skills()
            
            for skill in skills:
                if skill and hasattr(skill, 'name') and skill.name:
                    skill_name = skill.name
                    
                    # Python技能检测
                    if skill_name == SKILL_NAMES["PYTHON_PROGRAMMING"]:
                        if role_name not in coverage_stats["python_programming"]["roles"]:
                            coverage_stats["python_programming"]["roles"].append(role_name)
                    
                    # 架构技能检测（包含所有架构相关技能）
                    elif any(arch_skill in skill_name for arch_skill in [
                        "系统架构", "微服务架构", "云架构", "算法系统架构", "全栈架构"
                    ]):
                        if role_name not in coverage_stats["system_architecture"]["roles"]:
                            coverage_stats["system_architecture"]["roles"].append(role_name)
                    
                    # 写作技能检测（包含所有写作相关技能）
                    elif any(writing_skill in skill_name for writing_skill in [
                        "技术文档", "代码审查写作", "需求文档"
                    ]):
                        if role_name not in coverage_stats["technical_writing"]["roles"]:
                            coverage_stats["technical_writing"]["roles"].append(role_name)
        
        # 计算覆盖率
        total_roles = len(system.role_profiles)
        for skill_type in coverage_stats:
            coverage_stats[skill_type]["count"] = len(coverage_stats[skill_type]["roles"])
            coverage_stats[skill_type]["percentage"] = round(
                coverage_stats[skill_type]["count"] / total_roles * 100, 1
            )
        
        return coverage_stats
    
    return validate_skill_coverage_unified

def validate_consistency_fix():
    """验证一致性修复效果"""
    logger.info("🔍 验证一致性修复效果...")
    
    system = TeamSkillsMetaLearningSystem()
    
    # 使用统一验证函数
    unified_validator = create_unified_skill_validation()
    coverage_stats = unified_validator(system)
    
    # 重新诊断问题
    remaining_issues = diagnose_skill_validation_inconsistency()
    
    validation_result = {
        "python_coverage": coverage_stats["python_programming"]["percentage"],
        "architecture_coverage": coverage_stats["system_architecture"]["percentage"],
        "writing_coverage": coverage_stats["technical_writing"]["percentage"],
        "remaining_issues": len(remaining_issues),
        "issues_list": remaining_issues,
        "detailed_coverage": coverage_stats
    }
    
    logger.info("📊 一致性修复验证结果:")
    logger.info(f"  • Python技能覆盖率: {validation_result['python_coverage']}%")
    logger.info(f"  • 架构技能覆盖率: {validation_result['architecture_coverage']}%")
    logger.info(f"  • 写作技能覆盖率: {validation_result['writing_coverage']}%")
    logger.info(f"  • 剩余问题: {validation_result['remaining_issues']} 个")
    
    return validation_result

def main():
    """主函数"""
    logger.info("🚀 启动技能验证一致性修复...")
    
    try:
        # 诊断问题
        initial_issues = diagnose_skill_validation_inconsistency()
        logger.info(f"发现 {len(initial_issues)} 个一致性问题")
        
        # 标准化技能名称
        standardized_count = standardize_skill_names()
        
        # 验证修复效果
        validation_result = validate_consistency_fix()
        
        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "initial_issues": len(initial_issues),
            "standardized_skills": standardized_count,
            "validation_result": validation_result,
            "success": validation_result["remaining_issues"] == 0
        }
        
        # 输出结果
        logger.info("📋 技能验证一致性修复报告:")
        logger.info(f"  • 初始问题: {report['initial_issues']} 个")
        logger.info(f"  • 标准化技能: {report['standardized_skills']} 个")
        logger.info(f"  • 剩余问题: {validation_result['remaining_issues']} 个")
        logger.info(f"  • 修复状态: {'✅ 成功' if report['success'] else '⚠️ 部分成功'}")
        
        # 保存报告
        report_path = ".kiro/reports/skill_validation_consistency_fix.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 详细报告已保存到: {report_path}")
        
        if report['success']:
            logger.info("✅ 技能验证一致性修复成功!")
        else:
            logger.warning("⚠️ 技能验证一致性仍需进一步修复")
        
        return report['success']
        
    except Exception as e:
        logger.error(f"❌ 修复过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)