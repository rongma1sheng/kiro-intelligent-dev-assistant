#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统优化效果验证脚本

验证所有优化功能是否正常工作
"""

import sys
import time
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem
from team_skills_meta_learning import TeamSkillsMetaLearningSystem


def test_chinese_search_optimization():
    """测试中文搜索优化效果"""
    print("🔍 测试中文搜索优化效果")
    print("-" * 50)
    
    # 导入增强的搜索器
    sys.path.insert(0, str(Path(__file__).parent))
    from chinese_search_enhancer import ChineseSearchEnhancer
    
    enhancer = ChineseSearchEnhancer()
    
    # 测试中文搜索词
    test_queries = [
        "GitHub技能",
        "系统优化", 
        "错误解决",
        "团队协作",
        "Python编程",
        "代码审查",
        "测试覆盖率",
        "性能监控"
    ]
    
    total_results = 0
    for query in test_queries:
        start_time = time.time()
        results = enhancer.enhanced_search(query, max_results=5)
        search_time = (time.time() - start_time) * 1000
        
        print(f"   查询: '{query}' -> {len(results)}个结果 ({search_time:.1f}ms)")
        total_results += len(results)
    
    print(f"   总结果数: {total_results}")
    print(f"   平均每查询: {total_results/len(test_queries):.1f}个结果")
    
    return total_results > 0


def test_data_sync_fix():
    """测试数据同步修复效果"""
    print("\n🔄 测试数据同步修复效果")
    print("-" * 50)
    
    skills_system = TeamSkillsMetaLearningSystem('.kiro/team_skills', enable_learning=True)
    
    # 获取系统统计
    stats = skills_system.get_system_stats()
    print(f"   总角色数: {stats['total_roles']}")
    print(f"   总技能数: {stats['total_skills']}")
    print(f"   学习事件数: {stats['total_learning_events']}")
    print(f"   活跃角色数: {stats['active_roles']}")
    print(f"   平均熟练度: {stats['average_proficiency']:.1%}")
    
    # 检查角色熟练度分布
    print("\n   角色熟练度分布:")
    for role_name, profile in skills_system.role_profiles.items():
        proficiency = profile.calculate_overall_proficiency()
        skill_count = len(profile.get_all_skills())
        print(f"     {role_name}: {proficiency:.1%} ({skill_count}项技能)")
    
    return stats['total_roles'] == 12 and stats['total_skills'] > 0


def test_hook_matching_enhancement():
    """测试Hook匹配增强效果"""
    print("\n🎯 测试Hook匹配增强效果")
    print("-" * 50)
    
    # 导入增强的Hook匹配器
    sys.path.insert(0, str(Path(__file__).parent))
    from hook_matching_enhancer import HookMatchingEnhancer
    
    enhancer = HookMatchingEnhancer()
    
    # 测试不同类型的提示
    test_prompts = [
        "请帮我修复Python代码中的错误",
        "如何优化系统的性能表现",
        "团队技能管理的最佳实践",
        "GitHub集成遇到问题怎么解决",
        "代码审查的标准流程是什么",
        "测试覆盖率如何提升到100%"
    ]
    
    total_matches = 0
    for prompt in test_prompts:
        # 使用增强的Hook搜索
        start_time = time.time()
        results = enhancer.enhanced_hook_search(prompt, max_results=3)
        search_time = (time.time() - start_time) * 1000
        
        print(f"   提示: '{prompt[:30]}...' -> {len(results)}个匹配 ({search_time:.1f}ms)")
        total_matches += len(results)
    
    print(f"   总匹配数: {total_matches}")
    print(f"   平均匹配率: {total_matches/len(test_prompts):.1f}个/提示")
    
    return total_matches > 0


def test_system_performance():
    """测试系统整体性能"""
    print("\n⚡ 测试系统整体性能")
    print("-" * 50)
    
    memory_system = KiroMemorySystem('.kiro/memory', enable_learning=True)
    
    # 性能基准测试
    search_times = []
    for i in range(10):
        start_time = time.time()
        results = memory_system.search("测试", max_results=5)
        search_time = (time.time() - start_time) * 1000
        search_times.append(search_time)
    
    avg_search_time = sum(search_times) / len(search_times)
    max_search_time = max(search_times)
    min_search_time = min(search_times)
    
    print(f"   平均搜索时间: {avg_search_time:.1f}ms")
    print(f"   最快搜索时间: {min_search_time:.1f}ms")
    print(f"   最慢搜索时间: {max_search_time:.1f}ms")
    
    # 获取系统统计
    stats = memory_system.get_stats()
    print(f"   总模式数: {stats.total_patterns}")
    print(f"   存储大小: {stats.storage_size_mb:.2f}MB")
    
    return avg_search_time < 100  # 平均搜索时间应小于100ms


def main():
    """主函数"""
    print("🚀 Kiro系统优化效果验证")
    print("=" * 60)
    
    test_results = []
    
    # 1. 测试中文搜索优化
    try:
        result = test_chinese_search_optimization()
        test_results.append(("中文搜索优化", result))
    except Exception as e:
        print(f"   ❌ 中文搜索优化测试失败: {e}")
        test_results.append(("中文搜索优化", False))
    
    # 2. 测试数据同步修复
    try:
        result = test_data_sync_fix()
        test_results.append(("数据同步修复", result))
    except Exception as e:
        print(f"   ❌ 数据同步修复测试失败: {e}")
        test_results.append(("数据同步修复", False))
    
    # 3. 测试Hook匹配增强
    try:
        result = test_hook_matching_enhancement()
        test_results.append(("Hook匹配增强", result))
    except Exception as e:
        print(f"   ❌ Hook匹配增强测试失败: {e}")
        test_results.append(("Hook匹配增强", False))
    
    # 4. 测试系统整体性能
    try:
        result = test_system_performance()
        test_results.append(("系统整体性能", result))
    except Exception as e:
        print(f"   ❌ 系统整体性能测试失败: {e}")
        test_results.append(("系统整体性能", False))
    
    # 输出测试结果总结
    print("\n📊 优化效果验证结果")
    print("=" * 60)
    
    passed_tests = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed_tests += 1
    
    success_rate = passed_tests / len(test_results) * 100
    print(f"\n🎯 总体成功率: {success_rate:.1f}% ({passed_tests}/{len(test_results)})")
    
    if success_rate >= 75:
        print("🎉 系统优化效果优秀！")
        return 0
    elif success_rate >= 50:
        print("⚠️ 系统优化效果良好，但仍有改进空间")
        return 1
    else:
        print("❌ 系统优化效果不佳，需要进一步改进")
        return 2


if __name__ == "__main__":
    exit(main())