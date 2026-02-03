#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合分析任务知识积累脚本

分析技能学习效果检查任务的完整执行过程，提取系统评估和分析的知识模式
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem
from kiro_memory.models import MemoryType


def accumulate_comprehensive_analysis_knowledge():
    """积累综合分析知识"""
    memory_system = KiroMemorySystem('.kiro/memory', enable_learning=True)
    
    knowledge_patterns = [
        {
            'type': MemoryType.BEST_PRACTICE,
            'content': {
                'title': '复杂系统全面健康检查的设计模式',
                'description': '设计复杂系统全面健康检查的最佳实践：1)多维度评估框架-系统健康、功能效果、集成状态、性能指标 2)分层检查策略-基础健康→核心功能→系统集成→性能表现 3)量化评分体系-每个维度独立评分，加权计算总分 4)问题分级机制-根据严重程度分为关键、重要、一般问题 5)自动化检查流程-减少人工干预，提高检查一致性 6)详细报告生成-包含量化数据、问题分析、改进建议 7)知识积累机制-将检查经验存储供未来参考。这种模式确保系统评估的全面性和客观性',
                'context': '系统健康检查设计',
                'tags': ['系统检查', '健康评估', '设计模式', '质量保证'],
                'code_example': '''
# 复杂系统健康检查框架
class ComprehensiveSystemChecker:
    def __init__(self):
        self.check_dimensions = [
            'system_health',
            'functional_effectiveness', 
            'integration_status',
            'performance_metrics'
        ]
        self.scoring_weights = {
            'system_health': 0.3,
            'functional_effectiveness': 0.3,
            'integration_status': 0.2,
            'performance_metrics': 0.2
        }
        
    def run_comprehensive_check(self):
        """运行全面检查"""
        results = {}
        
        for dimension in self.check_dimensions:
            try:
                # 执行维度检查
                check_method = getattr(self, f'check_{dimension}')
                score, details = check_method()
                
                results[dimension] = {
                    'score': score,
                    'details': details,
                    'status': self.determine_status(score)
                }
            except Exception as e:
                results[dimension] = {
                    'score': 0,
                    'error': str(e),
                    'status': 'error'
                }
        
        # 计算综合评分
        overall_score = self.calculate_overall_score(results)
        
        # 生成报告
        report = self.generate_comprehensive_report(results, overall_score)
        
        return report
    
    def calculate_overall_score(self, results):
        """计算综合评分"""
        total_score = 0
        total_weight = 0
        
        for dimension, weight in self.scoring_weights.items():
            if dimension in results and 'score' in results[dimension]:
                total_score += results[dimension]['score'] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
'''
            }
        },
        {
            'type': MemoryType.CODE_PATTERN,
            'content': {
                'title': 'JSON序列化错误处理的通用解决模式',
                'description': '处理复杂对象JSON序列化错误的通用模式：当对象包含不可序列化的元素（如枚举、自定义类实例）时，通过递归检查和转换确保数据可以正确序列化。核心思想是先尝试序列化，失败时创建简化版本',
                'context': 'JSON序列化错误处理',
                'tags': ['JSON序列化', '错误处理', '数据转换', '通用模式'],
                'code_example': '''
# JSON序列化错误处理模式
import json
from enum import Enum

class SafeJSONSerializer:
    @staticmethod
    def serialize_safely(obj, max_length=200):
        """安全的JSON序列化"""
        try:
            # 尝试直接序列化
            json.dumps(obj)
            return obj
        except TypeError:
            # 处理不可序列化的对象
            return SafeJSONSerializer.create_serializable_version(obj, max_length)
    
    @staticmethod
    def create_serializable_version(obj, max_length=200):
        """创建可序列化版本"""
        if isinstance(obj, dict):
            serializable = {}
            for key, value in obj.items():
                try:
                    json.dumps(value)
                    serializable[key] = value
                except TypeError:
                    if isinstance(value, Enum):
                        serializable[key] = value.value
                    elif hasattr(value, '__dict__'):
                        serializable[key] = str(value)[:max_length]
                    else:
                        serializable[key] = str(value)[:max_length]
            return serializable
        
        elif isinstance(obj, list):
            return [SafeJSONSerializer.serialize_safely(item, max_length) for item in obj]
        
        elif isinstance(obj, Enum):
            return obj.value
        
        else:
            # 转换为字符串并截断
            str_repr = str(obj)
            return str_repr[:max_length] + '...' if len(str_repr) > max_length else str_repr

# 使用示例
def save_report_safely(report_data, file_path):
    """安全保存报告"""
    serializable_data = SafeJSONSerializer.serialize_safely(report_data)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)
'''
            }
        },
        {
            'type': MemoryType.BEST_PRACTICE,
            'content': {
                'title': '系统性能基准测试的实施方法',
                'description': '实施系统性能基准测试的最佳实践：1)多指标测试-响应时间、内存使用、存储效率、并发能力 2)多样本测试-多次测试取平均值，减少偶然误差 3)真实场景模拟-使用实际业务场景进行测试 4)基准对比-与历史数据和行业标准对比 5)瓶颈识别-通过测试识别性能瓶颈 6)持续监控-建立性能监控机制 7)优化验证-优化后重新测试验证效果。这种方法确保性能测试的准确性和实用性',
                'context': '系统性能测试',
                'tags': ['性能测试', '基准测试', '系统优化', '质量保证'],
                'code_example': '''
# 系统性能基准测试框架
import time
import psutil
import threading
from statistics import mean, median

class PerformanceBenchmark:
    def __init__(self, system_under_test):
        self.system = system_under_test
        self.benchmarks = {}
        
    def measure_response_time(self, operation, samples=10):
        """测量响应时间"""
        response_times = []
        
        for _ in range(samples):
            start_time = time.time()
            try:
                operation()
                end_time = time.time()
                response_times.append((end_time - start_time) * 1000)  # 转换为毫秒
            except Exception as e:
                print(f"操作执行失败: {e}")
        
        if response_times:
            return {
                'average': mean(response_times),
                'median': median(response_times),
                'min': min(response_times),
                'max': max(response_times),
                'samples': len(response_times)
            }
        return None
    
    def measure_memory_usage(self):
        """测量内存使用"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # 物理内存
            'vms_mb': memory_info.vms / 1024 / 1024,  # 虚拟内存
            'percent': process.memory_percent()
        }
    
    def test_concurrency(self, operation, concurrent_requests=5):
        """测试并发处理能力"""
        results = []
        threads = []
        
        def concurrent_operation():
            try:
                start_time = time.time()
                operation()
                end_time = time.time()
                results.append({
                    'success': True,
                    'duration': (end_time - start_time) * 1000
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e)
                })
        
        # 启动并发线程
        for _ in range(concurrent_requests):
            thread = threading.Thread(target=concurrent_operation)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) if results else 0
        
        return {
            'total_requests': len(results),
            'successful_requests': success_count,
            'success_rate': success_rate,
            'supported': success_rate >= 0.8
        }
    
    def run_full_benchmark(self):
        """运行完整基准测试"""
        print("🚀 开始性能基准测试...")
        
        # 响应时间测试
        response_time = self.measure_response_time(
            lambda: self.system.get_system_stats()
        )
        
        # 内存使用测试
        memory_usage = self.measure_memory_usage()
        
        # 并发测试
        concurrency = self.test_concurrency(
            lambda: self.system.get_system_stats()
        )
        
        benchmark_results = {
            'response_time': response_time,
            'memory_usage': memory_usage,
            'concurrency': concurrency,
            'timestamp': time.time()
        }
        
        # 计算性能评分
        performance_score = self.calculate_performance_score(benchmark_results)
        benchmark_results['performance_score'] = performance_score
        
        return benchmark_results
'''
            }
        },
        {
            'type': MemoryType.BEST_PRACTICE,
            'content': {
                'title': '多维度系统评估报告的生成方法',
                'description': '生成多维度系统评估报告的最佳实践：1)结构化报告格式-概述、详细结果、分析、建议 2)可视化数据展示-使用表格、图标、颜色编码 3)分层信息组织-从总体到细节的信息层次 4)量化与定性结合-数据支撑加文字分析 5)问题优先级排序-按严重程度和影响范围排序 6)可操作的改进建议-具体的实施步骤和时间规划 7)历史对比分析-与之前的检查结果对比 8)多格式输出-JSON数据+Markdown报告。这种方法确保报告的实用性和可读性',
                'context': '系统评估报告生成',
                'tags': ['报告生成', '数据可视化', '系统评估', '文档管理'],
                'code_example': '''
# 多维度评估报告生成器
class ComprehensiveReportGenerator:
    def __init__(self):
        self.status_icons = {
            'excellent': '🟢',
            'good': '🟡', 
            'needs_improvement': '🟠',
            'critical': '🔴',
            'error': '❌'
        }
        
    def generate_report(self, check_results, overall_score):
        """生成综合报告"""
        report = {
            'metadata': self.generate_metadata(overall_score),
            'executive_summary': self.generate_executive_summary(check_results, overall_score),
            'detailed_results': self.generate_detailed_results(check_results),
            'analysis': self.generate_analysis(check_results),
            'recommendations': self.generate_recommendations(check_results),
            'appendix': self.generate_appendix(check_results)
        }
        
        return report
    
    def generate_executive_summary(self, results, overall_score):
        """生成执行摘要"""
        status = self.determine_overall_status(overall_score)
        passed_checks = len([r for r in results.values() 
                           if r.get('status') in ['excellent', 'good']])
        total_checks = len(results)
        
        return {
            'overall_score': overall_score,
            'overall_status': f"{self.status_icons[status]} {status.title()}",
            'checks_passed': f"{passed_checks}/{total_checks}",
            'key_findings': self.extract_key_findings(results),
            'critical_issues': self.extract_critical_issues(results)
        }
    
    def generate_detailed_results(self, results):
        """生成详细结果"""
        detailed = {}
        
        for check_name, result in results.items():
            status = result.get('status', 'unknown')
            score = result.get('score', 0)
            
            detailed[check_name] = {
                'display_name': check_name.replace('_', ' ').title(),
                'status': f"{self.status_icons.get(status, '❓')} {status.title()}",
                'score': f"{score:.1f}/100" if score > 0 else "N/A",
                'details': self.format_details(result.get('details', {})),
                'metrics': result.get('metrics', {}),
                'issues': result.get('issues', [])
            }
        
        return detailed
    
    def generate_markdown_report(self, report_data):
        """生成Markdown格式报告"""
        markdown = f"""# 系统综合评估报告

## 🎯 评估概述

**评估时间**: {report_data['metadata']['timestamp']}  
**总体评分**: {report_data['executive_summary']['overall_score']:.1f}/100  
**总体状态**: {report_data['executive_summary']['overall_status']}  
**检查通过率**: {report_data['executive_summary']['checks_passed']}  

## 📊 检查结果总览

| 检查项目 | 状态 | 评分 | 关键指标 |
|----------|------|------|----------|
"""
        
        for check_name, details in report_data['detailed_results'].items():
            markdown += f"| {details['display_name']} | {details['status']} | {details['score']} | {self.format_key_metrics(details['metrics'])} |\n"
        
        markdown += f"""
## 🔍 详细分析

{report_data['analysis']['summary']}

### 主要发现
{self.format_findings_list(report_data['executive_summary']['key_findings'])}

### 关键问题
{self.format_issues_list(report_data['executive_summary']['critical_issues'])}

## 💡 改进建议

{self.format_recommendations(report_data['recommendations'])}

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**报告版本**: v1.0  
**状态**: 评估完成
"""
        
        return markdown
    
    def save_dual_format_report(self, report_data, base_path):
        """保存双格式报告"""
        # 保存JSON格式
        json_path = f"{base_path}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown格式
        markdown_path = f"{base_path}.md"
        markdown_content = self.generate_markdown_report(report_data)
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return json_path, markdown_path
'''
            }
        },
        {
            'type': MemoryType.CODE_PATTERN,
            'content': {
                'title': '动态方法调用和异常处理的安全模式',
                'description': '在系统检查中使用动态方法调用的安全模式：通过getattr动态获取检查方法，结合try-catch异常处理，确保单个检查失败不影响整体流程。这种模式特别适用于插件化的检查系统',
                'context': '动态方法调用',
                'tags': ['动态调用', '异常处理', '插件化', '系统检查'],
                'code_example': '''
# 动态方法调用安全模式
class DynamicMethodCaller:
    def __init__(self):
        self.check_methods = [
            'check_system_health',
            'check_learning_effectiveness', 
            'check_skills_integration',
            'check_performance_metrics'
        ]
        self.results = {}
        
    def execute_checks_safely(self):
        """安全执行所有检查方法"""
        passed_checks = 0
        total_checks = len(self.check_methods)
        
        for method_name in self.check_methods:
            try:
                # 动态获取方法
                if hasattr(self, method_name):
                    check_method = getattr(self, method_name)
                    
                    # 执行检查
                    print(f"🔍 执行检查: {method_name}")
                    result = check_method()
                    
                    # 记录结果
                    self.results[method_name] = {
                        'status': 'success',
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if result:  # 如果检查通过
                        passed_checks += 1
                        
                else:
                    print(f"⚠️ 检查方法不存在: {method_name}")
                    self.results[method_name] = {
                        'status': 'method_not_found',
                        'error': f"Method {method_name} not implemented"
                    }
                    
            except Exception as e:
                print(f"❌ 检查失败: {method_name} - {e}")
                self.results[method_name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return {
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'success_rate': passed_checks / total_checks if total_checks > 0 else 0,
            'detailed_results': self.results
        }
    
    def register_check_method(self, method_name, method_func):
        """动态注册检查方法"""
        setattr(self, method_name, method_func)
        if method_name not in self.check_methods:
            self.check_methods.append(method_name)
    
    def get_failed_checks(self):
        """获取失败的检查"""
        failed = []
        for method_name, result in self.results.items():
            if result.get('status') != 'success':
                failed.append({
                    'method': method_name,
                    'error': result.get('error', 'Unknown error'),
                    'status': result.get('status', 'unknown')
                })
        return failed

# 使用示例
class SystemChecker(DynamicMethodCaller):
    def check_system_health(self):
        # 具体的健康检查逻辑
        return True
    
    def check_performance_metrics(self):
        # 具体的性能检查逻辑  
        return True

# 执行检查
checker = SystemChecker()
results = checker.execute_checks_safely()
print(f"检查完成: {results['passed_checks']}/{results['total_checks']} 通过")
'''
            }
        },
        {
            'type': MemoryType.ERROR_SOLUTION,
            'content': {
                'title': '系统检查中的常见错误和解决方案',
                'description': '系统检查过程中常见错误的解决方案：1)JSON序列化错误-使用安全序列化方法处理复杂对象 2)方法调用失败-使用hasattr检查方法存在性 3)数据类型不匹配-添加类型检查和转换 4)资源访问错误-添加权限和存在性检查 5)并发访问冲突-使用线程安全的数据结构 6)内存不足-优化数据结构和及时释放资源。这些解决方案确保系统检查的稳定性和可靠性',
                'context': '系统检查错误处理',
                'tags': ['错误处理', '系统检查', '稳定性', '可靠性'],
                'error_symptoms': [
                    'Object of type X is not JSON serializable',
                    'AttributeError: object has no attribute method',
                    'TypeError: unsupported operand type(s)',
                    'FileNotFoundError: file not found',
                    'MemoryError: out of memory'
                ],
                'solution_steps': [
                    '1. JSON序列化错误：实现安全序列化方法，处理枚举和自定义对象',
                    '2. 方法调用错误：使用hasattr检查方法存在性，提供默认实现',
                    '3. 数据类型错误：添加类型检查，实现自动类型转换',
                    '4. 文件访问错误：检查文件存在性和访问权限',
                    '5. 内存错误：优化数据结构，实现分批处理',
                    '6. 并发错误：使用线程安全的数据结构和锁机制'
                ]
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
                source="comprehensive_analysis"
            )
            stored_count += 1
            print(f"✅ 已存储: {pattern_data['content']['title']}")
        except Exception as e:
            print(f"❌ 存储失败: {pattern_data['content']['title']} - {e}")
    
    print(f"\n📊 综合分析知识积累完成: 成功存储 {stored_count}/{len(knowledge_patterns)} 个模式")
    
    return stored_count


def analyze_task_execution_insights():
    """分析任务执行洞察"""
    print("🔍 分析任务执行洞察...")
    
    execution_insights = {
        'task_complexity': '高复杂度 - 多维度系统评估',
        'key_challenges': [
            'JSON序列化复杂对象的处理',
            '多线程并发测试的实现',
            '动态方法调用的安全性',
            '大量数据的报告生成',
            '错误处理的全面性'
        ],
        'successful_patterns': [
            '分层检查架构设计',
            '量化评分体系建立',
            '安全的JSON序列化处理',
            '多格式报告生成',
            '知识积累自动化'
        ],
        'technical_innovations': [
            '动态方法调用框架',
            '多维度评分算法',
            '安全序列化模式',
            '性能基准测试框架',
            '综合报告生成器'
        ],
        'lessons_learned': [
            '复杂对象序列化需要特殊处理',
            '系统检查需要全面的异常处理',
            '性能测试需要多样本统计',
            '报告生成需要结构化设计',
            '知识积累应该自动化进行'
        ],
        'reusable_components': [
            'ComprehensiveSystemChecker类',
            'SafeJSONSerializer工具',
            'PerformanceBenchmark框架',
            'ReportGenerator组件',
            'DynamicMethodCaller模式'
        ]
    }
    
    print("📋 任务执行洞察分析:")
    for key, value in execution_insights.items():
        if isinstance(value, list):
            print(f"   {key}: {len(value)}项")
            for item in value:
                print(f"     • {item}")
        else:
            print(f"   {key}: {value}")
    
    return execution_insights


def main():
    """主函数"""
    print("📚 综合分析任务知识积累器")
    print("=" * 50)
    
    try:
        # 分析任务执行洞察
        insights = analyze_task_execution_insights()
        
        # 积累知识到记忆系统
        stored_count = accumulate_comprehensive_analysis_knowledge()
        
        if stored_count > 0:
            print(f"\n🎉 综合分析知识积累成功！")
            print(f"📊 共存储 {stored_count} 个知识模式")
            print(f"🧠 涵盖系统检查、性能测试、报告生成等多个领域")
            print(f"💡 这些知识将显著提升未来系统评估工作的效率和质量")
            return 0
        else:
            print("\n⚠️ 没有成功存储任何知识模式")
            return 1
            
    except Exception as e:
        print(f"\n❌ 知识积累失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())