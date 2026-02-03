#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将GitHub技能集成到记忆系统和团队技能系统

将下载的GitHub技能转换为记忆模式和团队技能。
"""

import sys
import json
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem
from team_skills_meta_learning import TeamSkillsMetaLearningSystem, LearningEventType, LearningOutcome


def integrate_skills():
    """集成GitHub技能到系统中"""
    print("🔗 集成GitHub技能到记忆系统和团队技能系统")
    print("="*60)
    
    # 初始化系统
    memory_system = KiroMemorySystem('.kiro/memory', enable_learning=True)
    skills_system = TeamSkillsMetaLearningSystem('.kiro/team_skills', enable_learning=True)
    
    # 读取技能信息
    skills_info_file = ".kiro/downloads/github_skills/skills_info.json"
    with open(skills_info_file, 'r', encoding='utf-8') as f:
        skills_info = json.load(f)
    
    skills = skills_info.get('skills', [])
    
    # 技能到角色的映射
    skill_role_mapping = {
        'frontend-design': ['UI/UX Engineer', 'Full-Stack Engineer'],
        'webapp-testing': ['Test Engineer', 'Full-Stack Engineer'],
        'docx': ['Product Manager', 'Code Review Specialist'],
        'pdf': ['Product Manager', 'Code Review Specialist'],
        'xlsx': ['Product Manager', 'Data Engineer'],
        'pptx': ['Product Manager', 'UI/UX Engineer'],
        'mcp-builder': ['Software Architect', 'Full-Stack Engineer'],
        'doc-coauthoring': ['Product Manager', 'Scrum Master/Tech Lead'],
        'algorithmic-art': ['Algorithm Engineer', 'UI/UX Engineer'],
        'canvas-design': ['UI/UX Engineer', 'Algorithm Engineer'],
        'brand-guidelines': ['UI/UX Engineer', 'Product Manager'],
        'web-artifacts-builder': ['Full-Stack Engineer', 'UI/UX Engineer'],
        'theme-factory': ['UI/UX Engineer', 'Full-Stack Engineer'],
        'slack-gif-creator': ['UI/UX Engineer', 'Full-Stack Engineer'],
        'skill-creator': ['Software Architect', 'Code Review Specialist'],
        'internal-comms': ['Product Manager', 'Scrum Master/Tech Lead']
    }
    
    # 技能分类到技能名称的映射
    skill_category_to_names = {
        'frontend': ['javascript_programming', 'html_css', 'react', 'ui_ux_design'],
        'testing': ['automation_testing', 'webapp_testing', 'quality_assurance'],
        'documentation': ['technical_writing', 'documentation', 'content_creation'],
        'development': ['python_programming', 'javascript_programming', 'web_development'],
        'design': ['ui_ux_design', 'visual_design', 'graphic_design'],
        'architecture': ['system_architecture', 'software_design', 'api_design'],
        'data': ['data_analysis', 'spreadsheet_management', 'data_visualization'],
        'communication': ['technical_writing', 'presentation_skills', 'team_communication']
    }
    
    stored_patterns = 0
    assigned_skills = 0
    learning_events = 0
    
    print("💾 存储技能到记忆系统...")
    
    for skill in skills:
        try:
            # 存储为最佳实践模式
            pattern_id = memory_system.store_best_practice(
                title=f"GitHub技能: {skill['name']}",
                description=f"{skill['description']} 来源: {skill['source']}",
                category='github_skills',
                tags=['github', 'anthropic', 'skills', skill['name'], skill.get('category', 'general')]
            )
            stored_patterns += 1
            print(f"   ✅ 存储: {skill['name']} -> {pattern_id[:8]}...")
            
        except Exception as e:
            print(f"   ❌ 存储失败: {skill['name']} - {e}")
    
    print(f"\n🎯 分配技能到团队角色...")
    
    for skill in skills:
        skill_name = skill['name']
        
        # 获取应该分配给哪些角色
        target_roles = skill_role_mapping.get(skill_name, [])
        
        if not target_roles:
            # 根据技能描述推断角色
            description = skill.get('description', '').lower()
            if any(keyword in description for keyword in ['frontend', 'ui', 'design', 'visual']):
                target_roles = ['UI/UX Engineer', 'Full-Stack Engineer']
            elif any(keyword in description for keyword in ['test', 'testing']):
                target_roles = ['Test Engineer']
            elif any(keyword in description for keyword in ['document', 'doc', 'writing']):
                target_roles = ['Product Manager', 'Code Review Specialist']
            elif any(keyword in description for keyword in ['mcp', 'server', 'api']):
                target_roles = ['Software Architect', 'Full-Stack Engineer']
            else:
                target_roles = ['Full-Stack Engineer']  # 默认分配
        
        # 为每个目标角色分配技能
        for role_name in target_roles:
            if role_name in skills_system.role_profiles:
                try:
                    # 创建模拟代码来触发技能识别
                    mock_code = f"""
# {skill['name']} skill implementation
# {skill['description']}

class {skill['name'].replace('-', '_').title()}Skill:
    def __init__(self):
        self.name = "{skill['name']}"
        self.description = "{skill['description'][:100]}..."
        self.category = "{skill.get('category', 'general')}"
    
    def execute(self):
        # Implementation for {skill['name']}
        pass
"""
                    
                    # 分析代码技能
                    recognized_skills = skills_system.analyze_code_skills(
                        role_name, mock_code, f"{skill['name']}_skill.py"
                    )
                    
                    if recognized_skills:
                        assigned_skills += len(recognized_skills)
                        
                        # 记录学习事件
                        event_id = skills_system.record_learning_event(
                            role=role_name,
                            skill_id=skill['name'],
                            event_type=LearningEventType.SKILL_LEARNING,
                            outcome=LearningOutcome.SUCCESS,
                            context={
                                "source": "github_skills",
                                "skill_type": skill.get('category', 'general'),
                                "description": skill['description'][:100]
                            }
                        )
                        learning_events += 1
                        
                        print(f"   ✅ {role_name}: 分配技能 {skill['name']} (事件: {event_id[:8]}...)")
                    
                except Exception as e:
                    print(f"   ❌ 分配失败: {role_name} <- {skill['name']} - {e}")
    
    print(f"\n📊 集成完成统计:")
    print(f"   存储模式: {stored_patterns} 个")
    print(f"   分配技能: {assigned_skills} 个")
    print(f"   学习事件: {learning_events} 个")
    
    # 显示更新后的系统状态
    print(f"\n📈 更新后的系统状态:")
    
    # 记忆系统状态
    memory_stats = memory_system.get_stats()
    print(f"   记忆系统: {memory_stats.total_patterns} 个模式 ({memory_stats.storage_size_mb:.2f} MB)")
    
    # 团队技能系统状态
    team_stats = skills_system.get_system_stats()
    print(f"   团队技能: {team_stats.get('total_skills', 0)} 项技能")
    print(f"   学习事件: {team_stats.get('total_learning_events', 0)} 次")
    print(f"   平均熟练度: {team_stats.get('average_proficiency', 0):.1%}")
    
    # 显示技能分布最高的角色
    print(f"\n🏆 技能分布前5名角色:")
    role_skill_counts = {}
    for role_name, profile in skills_system.role_profiles.items():
        skill_count = len(profile.get_all_skills())
        role_skill_counts[role_name] = skill_count
    
    sorted_roles = sorted(role_skill_counts.items(), key=lambda x: x[1], reverse=True)
    for i, (role, count) in enumerate(sorted_roles[:5], 1):
        proficiency = skills_system.role_profiles[role].calculate_overall_proficiency()
        print(f"   {i}. {role}: {count} 项技能 (熟练度: {proficiency:.1%})")
    
    return stored_patterns, assigned_skills, learning_events


if __name__ == "__main__":
    try:
        stored, assigned, events = integrate_skills()
        print(f"\n🎉 GitHub技能集成完成！")
        print(f"   记忆模式: {stored} 个")
        print(f"   技能分配: {assigned} 个") 
        print(f"   学习事件: {events} 个")
        exit(0)
    except Exception as e:
        print(f"❌ 集成失败: {e}")
        exit(1)