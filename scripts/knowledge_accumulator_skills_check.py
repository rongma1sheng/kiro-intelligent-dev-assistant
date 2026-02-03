#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能学习效果检查知识积累脚本

将技能学习效果检查的经验和发现存储到记忆系统中
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem
from kiro_memory.models import MemoryType


def accumulate_skills_check_knowledge():
    """积累技能检查知识"""
    memory_system = KiroMemorySystem('.kiro/memory', enable_learning=True)
    
    knowledge_patterns = [
        {
            'type': MemoryType.BEST_PRACTICE,
            'content': {
                'title': '团队技能学习效果的全面评估方法',
                'description': '对团队技能学习系统进行全面评估的最佳实践：1)系统健康检查-评估团队规模、技能覆盖、活跃度、平均熟练度 2)学习效果分析-技能分布分析、熟练度进展、学习模式识别、技能缺口分析 3)系统集成检查-与记忆系统、GitHub、Hook系统的集成效果 4)性能指标测试-响应时间、内存使用、存储效率、并发处理能力 5)综合评分-基于多维度指标计算总体评分 6)改进建议-提供具体的短期、中期、长期改进建议。这种方法确保技能学习系统的全面评估和持续优化',
                'context': '团队技能学习效果评估',
                'tags': ['技能评估', '学习效果', '团队管理', '系统检查'],
                'code_example': '''
# 技能学习效果评估框架
class SkillsLearningChecker:
    def comprehensive_check(self):
        results = {}
        
        # 1. 系统健康检查
        health_score = self.check_system_health()
        results['health'] = health_score
        
        # 2. 学习效果分析
        learning_score = self.analyze_learning_effectiveness()
        results['learning'] = learning_score
        
        # 3. 系统集成检查
        integration_score = self.check_integration()
        results['integration'] = integration_score
        
        # 4. 性能测试
        performance_score = self.test_performance()
        results['performance'] = performance_score
        
        # 5. 综合评分
        overall_score = sum(results.values()) / len(results)
        
        return {
            'overall_score': overall_score,
            'detailed_results': results,
            'recommendations': self.generate_recommendations(results)
        }
'''
            }
        },
        {
            'type': MemoryType.CODE_PATTERN,
            'content': {
                'title': '技能缺口识别和分析的算法模式',
                'description': '识别团队技能缺口的算法模式：通过分析关键技能的覆盖率，识别团队中缺失或覆盖不足的重要技能。算法考虑技能的重要性、当前覆盖人数、团队规模等因素，计算技能缺口的严重程度',
                'context': '技能缺口分析',
                'tags': ['技能分析', '缺口识别', '算法设计', '团队评估'],
                'code_example': '''
# 技能缺口识别算法
def analyze_skill_gaps(team_profiles, critical_skills):
    """分析技能缺口"""
    gaps = []
    
    for critical_skill in critical_skills:
        coverage_count = 0
        total_proficiency = 0
        
        # 统计技能覆盖情况
        for role_name, profile in team_profiles.items():
            skills = profile.get_all_skills()
            for skill in skills:
                if critical_skill.lower() in skill.name.lower():
                    coverage_count += 1
                    total_proficiency += skill.proficiency
        
        # 计算缺口严重程度
        coverage_ratio = coverage_count / len(team_profiles)
        avg_proficiency = total_proficiency / coverage_count if coverage_count > 0 else 0
        
        # 确定缺口等级
        if coverage_count == 0:
            severity = 'critical'
        elif coverage_count < 2:
            severity = 'high'
        elif coverage_ratio < 0.3:
            severity = 'medium'
        else:
            severity = 'low'
        
        if severity in ['critical', 'high', 'medium']:
            gaps.append({
                'skill': critical_skill,
                'coverage_count': coverage_count,
                'coverage_ratio': coverage_ratio,
                'avg_proficiency': avg_proficiency,
                'severity': severity
            })
    
    return sorted(gaps, key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x['severity']], reverse=True)
'''
            }
        },
        {
            'type': MemoryType.BEST_PRACTICE,
            'content': {
                'title': '学习模式识别和分析的方法论',
                'description': '识别团队学习模式的方法论：1)热门技能模式识别-统计多个角色共同掌握的技能，识别团队的核心能力 2)专业化角色模式-识别掌握多项技能的专业化角色，作为知识传播者 3)技能协作模式-分析技能重叠情况，发现协作机会 4)学习路径模式-基于技能关联性分析学习路径 5)能力互补模式-识别技能互补的角色组合。这种方法帮助团队优化学习策略和资源配置',
                'context': '学习模式识别',
                'tags': ['学习模式', '模式识别', '团队分析', '知识管理'],
                'code_example': '''
# 学习模式识别系统
class LearningPatternAnalyzer:
    def identify_patterns(self, team_profiles):
        patterns = []
        
        # 1. 热门技能模式
        skill_counts = self.count_skill_frequency(team_profiles)
        popular_skills = [skill for skill, count in skill_counts.items() if count >= 3]
        if popular_skills:
            patterns.append({
                'type': 'popular_skills',
                'description': f'发现{len(popular_skills)}个热门技能',
                'skills': popular_skills,
                'value': '团队核心能力，可作为协作基础'
            })
        
        # 2. 专业化角色模式
        specialized_roles = []
        for role_name, profile in team_profiles.items():
            skill_count = len(profile.get_all_skills())
            if skill_count >= 3:
                specialized_roles.append({
                    'role': role_name,
                    'skill_count': skill_count,
                    'proficiency': profile.calculate_overall_proficiency()
                })
        
        if specialized_roles:
            patterns.append({
                'type': 'specialized_roles',
                'description': f'发现{len(specialized_roles)}个专业化角色',
                'roles': specialized_roles,
                'value': '可作为技能导师和知识传播者'
            })
        
        # 3. 技能协作模式
        collaboration_opportunities = self.find_collaboration_opportunities(team_profiles)
        if collaboration_opportunities:
            patterns.append({
                'type': 'collaboration_opportunities',
                'description': f'发现{len(collaboration_opportunities)}个协作机会',
                'opportunities': collaboration_opportunities,
                'value': '促进团队内部知识分享'
            })
        
        return patterns
'''
            }
        },
        {
            'type': MemoryType.ERROR_SOLUTION,
            'content': {
                'title': '技能统计数据不一致问题的解决方案',
                'description': '解决技能系统中统计数据不一致问题的完整方案：问题表现为实际技能数量与统计显示不符。根因分析：1)统计算法可能存在重复计算 2)数据缓存未及时更新 3)技能去重逻辑有问题。解决方案：1)修复统计算法-确保正确的去重逻辑 2)清除统计缓存-强制重新计算 3)数据一致性检查-定期验证数据完整性 4)实时同步机制-确保数据变更时统计同步更新',
                'context': '技能系统数据一致性',
                'tags': ['数据一致性', '统计错误', '缓存问题', '数据同步'],
                'error_symptoms': [
                    '实际技能数量与统计显示不符',
                    '角色技能统计不准确',
                    '系统报告数据矛盾',
                    '缓存数据过期'
                ],
                'solution_steps': [
                    '1. 分析统计算法：检查技能计数逻辑是否正确',
                    '2. 清除统计缓存：强制系统重新计算统计数据',
                    '3. 验证数据完整性：对比实际数据和统计结果',
                    '4. 修复去重逻辑：确保技能名称正确去重',
                    '5. 实施实时同步：数据变更时立即更新统计',
                    '6. 建立一致性检查：定期验证数据一致性'
                ]
            }
        },
        {
            'type': MemoryType.BEST_PRACTICE,
            'content': {
                'title': '技能学习系统性能优化的最佳实践',
                'description': '优化技能学习系统性能的最佳实践：1)响应时间优化-使用缓存机制、异步处理、数据预加载 2)内存使用优化-对象池、延迟加载、内存回收 3)存储效率优化-数据压缩、索引优化、分层存储 4)并发处理优化-线程安全、锁优化、无锁数据结构 5)性能监控-实时监控关键指标、性能基准测试、瓶颈识别。通过这些优化技术，技能系统可以达到毫秒级响应时间和高并发处理能力',
                'context': '技能系统性能优化',
                'tags': ['性能优化', '响应时间', '内存管理', '并发处理'],
                'code_example': '''
# 技能系统性能优化
class PerformanceOptimizedSkillsSystem:
    def __init__(self):
        self.cache = {}  # 缓存机制
        self.stats_cache = None  # 统计缓存
        self.cache_ttl = 300  # 缓存5分钟
        
    def get_system_stats(self):
        """优化的统计获取"""
        current_time = time.time()
        
        # 检查缓存
        if (self.stats_cache and 
            current_time - self.stats_cache['timestamp'] < self.cache_ttl):
            return self.stats_cache['data']
        
        # 重新计算统计
        stats = self.calculate_stats()
        
        # 更新缓存
        self.stats_cache = {
            'data': stats,
            'timestamp': current_time
        }
        
        return stats
    
    def calculate_stats(self):
        """高效的统计计算"""
        # 使用集合去重，避免重复计算
        unique_skills = set()
        total_proficiency = 0
        role_count = 0
        
        for profile in self.role_profiles.values():
            skills = profile.get_all_skills()
            for skill in skills:
                unique_skills.add(skill.name)
            
            total_proficiency += profile.calculate_overall_proficiency()
            role_count += 1
        
        return {
            'total_roles': role_count,
            'total_skills': len(unique_skills),
            'average_proficiency': total_proficiency / role_count if role_count > 0 else 0,
            'active_roles': role_count,
            'skill_categories': len(set(skill.category for profile in self.role_profiles.values() 
                                      for skill in profile.get_all_skills()))
        }
'''
            }
        }
    ]
    
    # 存储知识模式
    stored_count = 0
    for pattern_data in knowledge_patterns:
        try:
            pattern_id = memory_system.store_pattern(
                content=pattern_data['content'],
                pattern_type=pattern_data['type'],
                tags=pattern_data['content'].get('tags', []),
                source="skills_check_analysis"
            )
            stored_count += 1
            print(f"✅ 已存储: {pattern_data['content']['title']}")
        except Exception as e:
            print(f"❌ 存储失败: {pattern_data['content']['title']} - {e}")
    
    print(f"\n📊 技能检查知识积累完成: 成功存储 {stored_count}/{len(knowledge_patterns)} 个模式")
    
    return stored_count


def main():
    """主函数"""
    print("🧠 技能学习效果检查知识积累")
    print("=" * 50)
    
    try:
        stored_count = accumulate_skills_check_knowledge()
        
        if stored_count > 0:
            print(f"\n🎉 知识积累成功！共存储 {stored_count} 个技能检查经验模式")
            print("💡 这些知识将帮助未来的技能系统评估和优化工作")
            return 0
        else:
            print("\n⚠️ 没有成功存储任何知识模式")
            return 1
            
    except Exception as e:
        print(f"\n❌ 知识积累失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())