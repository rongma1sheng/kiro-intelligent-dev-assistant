#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步修复脚本
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from team_skills_meta_learning import TeamSkillsMetaLearningSystem

class DataSyncFixer:
    """数据同步修复器"""
    
    def __init__(self):
        self.skills_system = TeamSkillsMetaLearningSystem('.kiro/team_skills', enable_learning=True)
    
    def fix_learning_events_count(self):
        """修复学习事件计数"""
        print("🔄 修复学习事件计数...")
        
        # 1. 重新计算学习事件
        total_events = 0
        for role_name, profile in self.skills_system.role_profiles.items():
            # 计算该角色的学习事件
            role_events = len([event for event in self.skills_system.learning_events 
                             if event.role == role_name])
            total_events += role_events
            print(f"   {role_name}: {role_events} 个学习事件")
        
        print(f"   总学习事件: {total_events}")
        
        # 2. 更新统计缓存
        self.skills_system._cached_stats = None  # 清除缓存
        
        # 3. 重新获取统计数据
        updated_stats = self.skills_system.get_system_stats()
        print(f"   更新后统计: {updated_stats}")
        
        return total_events
    
    def recalculate_all_statistics(self):
        """重新计算所有统计数据"""
        print("📊 重新计算所有统计数据...")
        
        # 1. 重新计算角色熟练度
        for role_name, profile in self.skills_system.role_profiles.items():
            old_proficiency = profile.calculate_overall_proficiency()
            
            # 重新计算技能熟练度
            all_skills = profile.get_all_skills()
            if all_skills:
                total_proficiency = sum(skill.proficiency for skill in all_skills)
                new_proficiency = total_proficiency / len(all_skills)
                print(f"   {role_name}: {old_proficiency:.1%} -> {new_proficiency:.1%}")
        
        # 2. 清除所有缓存
        if hasattr(self.skills_system, '_cached_stats'):
            self.skills_system._cached_stats = None
        
        print("   ✅ 统计数据重新计算完成")

if __name__ == "__main__":
    fixer = DataSyncFixer()
    
    # 修复学习事件计数
    total_events = fixer.fix_learning_events_count()
    
    # 重新计算统计数据
    fixer.recalculate_all_statistics()
    
    print(f"\n🎉 数据同步修复完成！总学习事件: {total_events}")
