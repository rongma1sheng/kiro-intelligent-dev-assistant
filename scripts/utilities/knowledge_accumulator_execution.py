#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识积累器执行脚本

分析刚完成的任务，提取有价值的知识并存储到记忆系统中。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem


def extract_and_store_knowledge():
    """提取并存储知识"""
    print("🧠 知识积累器正在分析刚完成的任务...")
    print("="*60)
    
    # 初始化记忆系统
    memory = KiroMemorySystem('.kiro/memory', enable_learning=True)
    
    # 提取的知识模式
    knowledge_patterns = [
        {
            'type': 'best_practice',
            'title': '系统健康检查最佳实践',
            'description': '通过多维度检查确保复杂系统的健康状态：1)运行统计检查 2)功能测试验证 3)集成状态确认 4)性能指标监控 5)Hook系统响应验证。这种方法能够全面评估系统状态，及早发现潜在问题。',
            'category': 'system_monitoring',
            'tags': ['system_health', 'monitoring', 'testing', 'integration', 'best_practice']
        },
        {
            'type': 'code_pattern',
            'code': '''# 系统状态检查模式
def check_system_health():
    """多维度系统健康检查"""
    # 1. 统计信息检查
    stats = system.get_stats()
    print(f"总数据: {stats.total_items}")
    print(f"存储大小: {stats.storage_size_mb:.2f} MB")
    
    # 2. 功能测试
    test_results = run_all_tests()
    assert test_results.pass_rate == 1.0, "测试未全部通过"
    
    # 3. 性能验证
    performance = measure_performance()
    assert performance.response_time < threshold, "性能不达标"
    
    # 4. 集成状态检查
    integration_status = check_integrations()
    
    return {
        "status": "healthy", 
        "stats": stats,
        "performance": performance,
        "integrations": integration_status
    }''',
            'description': '系统健康检查的标准模式，包含统计、测试、性能、集成四个维度的全面验证',
            'file_type': 'python',
            'tags': ['health_check', 'system_monitoring', 'testing', 'python']
        },
        {
            'type': 'error_solution',
            'error_description': 'Hook系统激活但搜索没有找到相关模式',
            'solution': '这是正常现象，说明Hook系统正确响应了触发条件，但记忆系统中暂时没有匹配的模式。解决方案：1)检查搜索关键词是否准确 2)添加更多相关模式到记忆系统 3)调整搜索策略和相似度阈值 4)确认这是预期行为而非错误',
            'error_type': 'hook_integration',
            'tags': ['hook_system', 'memory_system', 'integration', 'normal_behavior', 'troubleshooting']
        },
        {
            'type': 'best_practice',
            'title': '多系统集成验证策略',
            'description': '验证多个系统集成时的最佳实践：1)独立系统功能验证-确保每个系统单独工作正常 2)系统间通信测试-验证API调用和数据传递 3)数据一致性检查-确保跨系统数据同步 4)性能影响评估-测试集成对性能的影响 5)错误传播控制-确保错误不会级联传播',
            'category': 'integration_testing',
            'tags': ['integration', 'testing', 'multi_system', 'verification', 'architecture']
        },
        {
            'type': 'code_pattern',
            'code': '''# 命令行工具诊断模式
import subprocess
import json
from datetime import datetime

def run_cli_diagnostics():
    """通过命令行工具进行系统诊断"""
    commands = [
        ("memory_stats", "python scripts/manage_memory_system.py stats"),
        ("team_overview", "python scripts/manage_team_skills.py overview"),
        ("memory_test", "python scripts/test_memory_system.py"),
        ("skills_test", "python scripts/test_skills_meta_learning.py")
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "diagnostics": {}
    }
    
    for name, cmd in commands:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, 
                text=True, timeout=60
            )
            results["diagnostics"][name] = {
                "command": cmd,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
                "output_lines": len(result.stdout.splitlines()),
                "has_errors": bool(result.stderr)
            }
        except subprocess.TimeoutExpired:
            results["diagnostics"][name] = {
                "command": cmd,
                "error": "timeout",
                "success": False
            }
    
    return results''',
            'description': '通过命令行工具进行系统诊断的标准模式，包含超时处理和结果结构化',
            'file_type': 'python',
            'tags': ['cli_tools', 'diagnostics', 'automation', 'system_check', 'subprocess']
        },
        {
            'type': 'best_practice',
            'title': 'Hook系统响应分析方法',
            'description': 'Hook系统响应分析的最佳实践：1)检查Hook配置文件语法正确性 2)验证触发条件是否匹配 3)确认Hook执行日志和输出 4)分析Hook提示内容的相关性 5)评估Hook系统与其他组件的集成效果。这种分析方法有助于理解Hook系统的工作机制。',
            'category': 'hook_system',
            'tags': ['hook_system', 'analysis', 'debugging', 'integration', 'configuration']
        }
    ]
    
    # 存储知识模式
    stored_count = 0
    failed_count = 0
    
    for pattern in knowledge_patterns:
        try:
            if pattern['type'] == 'best_practice':
                pattern_id = memory.store_best_practice(
                    title=pattern['title'],
                    description=pattern['description'],
                    category=pattern['category'],
                    tags=pattern['tags']
                )
            elif pattern['type'] == 'code_pattern':
                pattern_id = memory.store_code_pattern(
                    code=pattern['code'],
                    description=pattern['description'],
                    file_type=pattern['file_type'],
                    tags=pattern['tags']
                )
            elif pattern['type'] == 'error_solution':
                pattern_id = memory.store_error_solution(
                    error_description=pattern['error_description'],
                    solution=pattern['solution'],
                    error_type=pattern['error_type'],
                    tags=pattern['tags']
                )
            
            stored_count += 1
            title = pattern.get('title', pattern.get('description', '未命名'))[:50]
            print(f'✅ 存储知识模式: {pattern_id[:8]}... - {title}')
            
        except Exception as e:
            failed_count += 1
            print(f'❌ 存储失败: {e}')
    
    print(f'\n📊 知识积累完成:')
    print(f'   ✅ 成功存储: {stored_count} 个知识模式')
    print(f'   ❌ 存储失败: {failed_count} 个模式')
    print(f'   📈 成功率: {stored_count/(stored_count+failed_count)*100:.1f}%')
    
    # 显示更新后的统计信息
    print(f'\n📊 更新后的记忆系统统计:')
    stats = memory.get_stats()
    print(f'   总模式数: {stats.total_patterns}')
    print(f'   存储大小: {stats.storage_size_mb:.2f} MB')
    print(f'   按类型分布: {dict(stats.patterns_by_type)}')
    
    return stored_count, failed_count


if __name__ == "__main__":
    try:
        stored, failed = extract_and_store_knowledge()
        exit(0 if failed == 0 else 1)
    except Exception as e:
        print(f"❌ 知识积累失败: {e}")
        exit(1)