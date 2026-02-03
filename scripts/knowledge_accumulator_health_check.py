#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统健康检查任务知识积累器

分析系统健康检查任务，提取有价值的知识并存储到记忆系统中。
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem


def extract_health_check_knowledge():
    """提取系统健康检查任务的知识"""
    print("🧠 知识积累器分析系统健康检查任务")
    print("="*60)
    
    # 初始化记忆系统
    memory = KiroMemorySystem('.kiro/memory', enable_learning=True)
    
    # 提取的知识模式
    knowledge_patterns = [
        {
            'type': 'best_practice',
            'title': '多维度系统健康检查方法论',
            'description': '全面的系统健康检查最佳实践：1)核心系统状态检查-验证各子系统基本功能 2)功能测试验证-执行完整的测试套件 3)Hook系统集成检查-验证自动化组件 4)文件系统结构检查-确保目录完整性 5)性能和资源检查-监控系统资源使用 6)配置一致性检查-验证配置版本和格式 7)集成测试验证-测试跨系统协作 8)生成详细报告-记录所有检查结果。这种系统性方法确保无遗漏的全面健康评估。',
            'category': 'system_monitoring',
            'tags': ['health_check', 'system_monitoring', 'testing', 'integration', 'best_practice']
        },
        {
            'type': 'code_pattern',
            'code': '''# 系统健康检查执行模式
import subprocess
import json
from datetime import datetime
from pathlib import Path

class SystemHealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.check_results = {
            'timestamp': datetime.now().isoformat(),
            'systems': {},
            'overall_status': 'unknown'
        }
    
    def run_full_health_check(self):
        """执行全量健康检查"""
        print("🏥 开始系统全量健康检查")
        
        # 1. 核心系统状态检查
        self.check_core_systems()
        
        # 2. 功能测试验证
        self.run_functional_tests()
        
        # 3. 集成状态检查
        self.check_integration_status()
        
        # 4. 性能基准测试
        self.run_performance_tests()
        
        # 5. 配置一致性检查
        self.check_configuration_consistency()
        
        # 6. 生成健康报告
        return self.generate_health_report()
    
    def check_core_systems(self):
        """检查核心系统状态"""
        systems = [
            ('memory_system', 'python scripts/manage_memory_system.py stats'),
            ('skills_system', 'python scripts/manage_team_skills.py overview'),
        ]
        
        for system_name, command in systems:
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, 
                    text=True, timeout=60
                )
                self.check_results['systems'][system_name] = {
                    'status': 'healthy' if result.returncode == 0 else 'error',
                    'exit_code': result.returncode,
                    'output_lines': len(result.stdout.splitlines())
                }
            except Exception as e:
                self.check_results['systems'][system_name] = {
                    'status': 'error',
                    'error': str(e)
                }
    
    def run_functional_tests(self):
        """运行功能测试"""
        test_commands = [
            'python scripts/test_memory_system.py',
            'python scripts/test_skills_meta_learning.py',
            'python scripts/test_memory_integration.py'
        ]
        
        test_results = []
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, 
                    text=True, timeout=120
                )
                test_results.append({
                    'command': cmd,
                    'success': result.returncode == 0,
                    'output': result.stdout
                })
            except Exception as e:
                test_results.append({
                    'command': cmd,
                    'success': False,
                    'error': str(e)
                })
        
        self.check_results['functional_tests'] = test_results
    
    def generate_health_report(self):
        """生成健康检查报告"""
        # 计算整体健康状态
        all_systems_healthy = all(
            s.get('status') == 'healthy' 
            for s in self.check_results['systems'].values()
        )
        
        all_tests_passed = all(
            t.get('success', False) 
            for t in self.check_results.get('functional_tests', [])
        )
        
        self.check_results['overall_status'] = (
            'excellent' if all_systems_healthy and all_tests_passed 
            else 'degraded'
        )
        
        return self.check_results''',
            'description': '系统健康检查的完整实现，包含多维度检查、测试执行和报告生成',
            'file_type': 'python',
            'tags': ['health_check', 'system_monitoring', 'automation', 'testing']
        },
        {
            'type': 'best_practice',
            'title': '系统性能基准测试策略',
            'description': '建立和维护系统性能基准的最佳实践：1)定义关键性能指标KPI-响应时间、吞吐量、资源使用 2)设定性能目标阈值-基于业务需求和行业标准 3)自动化性能测试-集成到健康检查流程 4)性能趋势监控-跟踪性能变化趋势 5)性能回归检测-识别性能下降问题 6)基准对比分析-与行业标准对比。这种方法确保系统性能持续优化。',
            'category': 'performance_testing',
            'tags': ['performance', 'benchmarking', 'monitoring', 'optimization']
        },
        {
            'type': 'error_solution',
            'error_description': '中文搜索词无法匹配记忆系统中存储的模式',
            'solution': '这是由于搜索索引机制对中文支持不完善导致的。解决方案：1)检查搜索算法是否支持Unicode字符 2)优化中文分词机制，使用jieba等中文分词库 3)建立中文关键词映射表 4)使用模糊匹配算法提高匹配率 5)添加拼音搜索支持 6)重建搜索索引确保中文内容被正确索引。',
            'error_type': 'search_localization',
            'tags': ['chinese_search', 'localization', 'indexing', 'unicode']
        },
        {
            'type': 'error_solution',
            'error_description': '团队技能系统统计显示的学习事件数与实际不符',
            'solution': '这是数据同步问题导致的统计不准确。解决方案：1)检查学习事件存储和读取逻辑的一致性 2)验证数据库连接和事务处理 3)添加数据同步验证机制 4)实现统计数据的实时更新 5)添加数据一致性检查和修复功能 6)建立定期数据校验任务。确保统计数据与实际数据保持同步。',
            'error_type': 'data_synchronization',
            'tags': ['data_sync', 'statistics', 'consistency', 'database']
        },
        {
            'type': 'error_solution',
            'error_description': 'Hook提示增强功能在某些情况下无法找到相关模式',
            'solution': '这是搜索策略和匹配算法需要优化的问题。解决方案：1)改进搜索关键词提取算法 2)使用语义相似度匹配而非简单字符匹配 3)建立同义词和相关词映射 4)降低匹配阈值以提高召回率 5)实现多轮搜索策略-先精确匹配再模糊匹配 6)添加上下文理解能力提高匹配准确性。',
            'error_type': 'search_enhancement',
            'tags': ['hook_enhancement', 'search_optimization', 'semantic_matching', 'nlp']
        },
        {
            'type': 'best_practice',
            'title': '系统健康报告生成和维护策略',
            'description': '生成高质量系统健康报告的最佳实践：1)结构化报告格式-使用统一的模板和格式 2)多维度数据展示-表格、图表、文字相结合 3)关键指标突出-使用颜色和图标标识状态 4)趋势分析-对比历史数据显示变化趋势 5)问题分级-按严重程度分类问题和建议 6)可操作建议-提供具体的修复步骤和优化建议 7)报告版本管理-保存历史报告便于对比。这种方法确保报告的实用性和可读性。',
            'category': 'reporting',
            'tags': ['reporting', 'documentation', 'health_check', 'visualization']
        },
        {
            'type': 'code_pattern',
            'code': '''# 系统优化问题诊断和修复模式
class SystemOptimizer:
    """系统优化器"""
    
    def __init__(self, memory_system, skills_system):
        self.memory_system = memory_system
        self.skills_system = skills_system
        self.optimization_results = []
    
    def optimize_chinese_search(self):
        """优化中文搜索功能"""
        print("🔍 优化中文搜索功能...")
        
        # 1. 检查当前搜索配置
        current_config = self.memory_system.get_search_config()
        
        # 2. 添加中文分词支持
        try:
            import jieba
            jieba.initialize()
            
            # 3. 重建搜索索引
            self.memory_system.rebuild_search_index(
                enable_chinese=True,
                tokenizer='jieba'
            )
            
            self.optimization_results.append({
                'component': 'chinese_search',
                'status': 'optimized',
                'changes': ['添加jieba分词', '重建搜索索引', '启用中文支持']
            })
            
        except ImportError:
            self.optimization_results.append({
                'component': 'chinese_search',
                'status': 'failed',
                'error': 'jieba库未安装'
            })
    
    def fix_data_synchronization(self):
        """修复数据同步问题"""
        print("🔄 修复数据同步问题...")
        
        # 1. 验证数据一致性
        memory_events = self.memory_system.get_learning_events_count()
        skills_events = self.skills_system.get_learning_events_count()
        
        if memory_events != skills_events:
            # 2. 同步数据
            self.skills_system.sync_learning_events_from_memory(
                self.memory_system
            )
            
            # 3. 重新计算统计数据
            self.skills_system.recalculate_statistics()
            
            self.optimization_results.append({
                'component': 'data_sync',
                'status': 'fixed',
                'changes': [f'同步了{abs(memory_events - skills_events)}个学习事件']
            })
    
    def enhance_hook_matching(self):
        """增强Hook匹配效果"""
        print("🎯 增强Hook匹配效果...")
        
        # 1. 优化搜索策略
        enhanced_config = {
            'similarity_threshold': 0.3,  # 降低阈值提高召回率
            'enable_semantic_search': True,
            'max_results': 10,
            'enable_fuzzy_matching': True
        }
        
        # 2. 更新Hook搜索配置
        self.memory_system.update_search_config(enhanced_config)
        
        # 3. 添加同义词映射
        synonyms = {
            'error': ['错误', 'bug', '问题', '异常'],
            'optimization': ['优化', '改进', '提升', '增强'],
            'testing': ['测试', '验证', '检查', '校验']
        }
        
        self.memory_system.add_synonym_mappings(synonyms)
        
        self.optimization_results.append({
            'component': 'hook_enhancement',
            'status': 'enhanced',
            'changes': ['降低匹配阈值', '启用语义搜索', '添加同义词映射']
        })
    
    def generate_optimization_report(self):
        """生成优化报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'optimizations': self.optimization_results,
            'success_count': len([r for r in self.optimization_results if r['status'] in ['optimized', 'fixed', 'enhanced']]),
            'total_count': len(self.optimization_results)
        }''',
            'description': '系统优化问题的诊断和修复实现，包含中文搜索、数据同步、Hook增强的完整解决方案',
            'file_type': 'python',
            'tags': ['system_optimization', 'chinese_search', 'data_sync', 'hook_enhancement']
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
            title = pattern.get('title', pattern.get('error_description', '未命名'))[:50]
            print(f'✅ 存储知识模式: {pattern_id[:8]}... - {title}')
            
        except Exception as e:
            failed_count += 1
            print(f'❌ 存储失败: {e}')
    
    print(f'\n📊 系统健康检查任务知识积累完成:')
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
        stored, failed = extract_health_check_knowledge()
        print(f"\n🎉 系统健康检查任务知识积累完成！")
        print(f"   总共积累: {stored} 个有价值的知识模式")
        exit(0)
    except Exception as e:
        print(f"❌ 知识积累失败: {e}")
        exit(1)