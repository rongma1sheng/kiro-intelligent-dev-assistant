"""Property 14: Test Coverage Threshold Enforcement

白皮书依据: 第十四章 14.1.1 测试覆盖率目标
验证需求: Requirements 6.1, 6.7

属性定义:
- 当覆盖率低于阈值时，部署必须被阻止
- 当覆盖率达到阈值时，部署必须被允许
- 覆盖率计算必须准确
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import json
import tempfile
from typing import Dict, List

from src.quality.test_coverage_analyzer import (
    TestCoverageAnalyzer,
    CoverageReport,
    CoverageTarget
)


# 策略：生成覆盖率数据
@st.composite
def coverage_data_strategy(draw):
    """生成覆盖率数据"""
    num_files = draw(st.integers(min_value=1, max_value=20))
    
    files = {}
    for i in range(num_files):
        # 随机选择模块类别
        category = draw(st.sampled_from(['brain', 'core', 'execution', 'infra', 'interface']))
        file_name = f"src/{category}/module_{i}.py"
        
        # 生成覆盖率数据
        total_statements = draw(st.integers(min_value=10, max_value=500))
        covered_statements = draw(st.integers(min_value=0, max_value=total_statements))
        
        # 生成未覆盖行号
        all_lines = list(range(1, total_statements + 1))
        missing_count = total_statements - covered_statements
        missing_lines = draw(st.lists(
            st.sampled_from(all_lines),
            min_size=missing_count,
            max_size=missing_count,
            unique=True
        )) if missing_count > 0 else []
        
        files[file_name] = {
            'summary': {
                'num_statements': total_statements,
                'covered_lines': covered_statements,
                'num_branches': draw(st.integers(min_value=0, max_value=100)),
                'covered_branches': draw(st.integers(min_value=0, max_value=100))
            },
            'missing_lines': sorted(missing_lines)
        }
    
    return {
        'files': files,
        'totals': {
            'num_statements': sum(f['summary']['num_statements'] for f in files.values()),
            'covered_lines': sum(f['summary']['covered_lines'] for f in files.values())
        }
    }


class TestCoverageEnforcementProperty:
    """Property 14: Test Coverage Threshold Enforcement
    
    **Validates: Requirements 6.1, 6.7**
    
    白皮书依据: 第十四章 14.1.1 测试覆盖率目标
    """
    
    @given(coverage_data=coverage_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_14_deployment_blocked_when_below_threshold(self, coverage_data):
        """Property 14.1: 覆盖率低于阈值时部署被阻止
        
        **Validates: Requirements 6.1, 6.7**
        
        属性: 当任何类别的覆盖率低于目标阈值时，enforce_coverage_gates() 必须返回 passed=False
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建覆盖率JSON文件
            coverage_json_path = tmpdir_path / 'coverage.json'
            with open(coverage_json_path, 'w') as f:
                json.dump(coverage_data, f)
            
            # 创建分析器
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            # 手动设置覆盖率数据（模拟analyze_coverage的结果）
            for file_path, file_data in coverage_data['files'].items():
                rel_path = Path(file_path)
                module_name = str(rel_path).replace('\\', '/').replace('.py', '').replace('/', '.')
                
                summary = file_data['summary']
                total_statements = summary['num_statements']
                covered_statements = summary['covered_lines']
                missing_lines = file_data['missing_lines']
                
                coverage_percent = (covered_statements / total_statements * 100) if total_statements > 0 else 0.0
                
                report = CoverageReport(
                    module_name=module_name,
                    total_statements=total_statements,
                    covered_statements=covered_statements,
                    coverage_percent=coverage_percent,
                    missing_lines=missing_lines
                )
                
                analyzer.coverage_data[module_name] = report
            
            # 执行门禁检查
            result = analyzer.enforce_coverage_gates()
            
            # 计算各类别实际覆盖率
            core_coverage = analyzer.get_category_coverage('core')
            execution_coverage = analyzer.get_category_coverage('execution')
            infra_coverage = analyzer.get_category_coverage('infrastructure')
            interface_coverage = analyzer.get_category_coverage('interface')
            overall_coverage = analyzer.get_overall_coverage()
            
            # 属性验证：如果任何类别低于阈值，必须不通过
            targets = analyzer.coverage_targets
            
            should_fail = (
                (core_coverage > 0 and core_coverage < targets.core_modules) or
                (execution_coverage > 0 and execution_coverage < targets.execution_modules) or
                (infra_coverage > 0 and infra_coverage < targets.infrastructure_modules) or
                (interface_coverage > 0 and interface_coverage < targets.interface_modules) or
                overall_coverage < targets.overall
            )
            
            if should_fail:
                assert not result['passed'], (
                    f"覆盖率低于阈值但门禁通过了！"
                    f"Core: {core_coverage:.2f}% (target: {targets.core_modules}%), "
                    f"Execution: {execution_coverage:.2f}% (target: {targets.execution_modules}%), "
                    f"Infra: {infra_coverage:.2f}% (target: {targets.infrastructure_modules}%), "
                    f"Interface: {interface_coverage:.2f}% (target: {targets.interface_modules}%), "
                    f"Overall: {overall_coverage:.2f}% (target: {targets.overall}%)"
                )
                assert len(result['violations']) > 0, "应该有违规项但violations为空"
    
    @given(
        core_coverage=st.floats(min_value=85.0, max_value=100.0),
        execution_coverage=st.floats(min_value=80.0, max_value=100.0),
        infra_coverage=st.floats(min_value=75.0, max_value=100.0),
        interface_coverage=st.floats(min_value=60.0, max_value=100.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_deployment_allowed_when_above_threshold(
        self,
        core_coverage,
        execution_coverage,
        infra_coverage,
        interface_coverage
    ):
        """Property 14.2: 覆盖率达到阈值时部署被允许
        
        **Validates: Requirements 6.1, 6.7**
        
        属性: 当所有类别的覆盖率都达到或超过目标阈值时，enforce_coverage_gates() 必须返回 passed=True
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建分析器
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            # 构造满足阈值的覆盖率数据
            # 核心模块
            analyzer.coverage_data['src.brain.soldier'] = CoverageReport(
                module_name='src.brain.soldier',
                total_statements=100,
                covered_statements=int(core_coverage),
                coverage_percent=core_coverage,
                missing_lines=[]
            )
            
            # 执行模块
            analyzer.coverage_data['src.execution.order_manager'] = CoverageReport(
                module_name='src.execution.order_manager',
                total_statements=100,
                covered_statements=int(execution_coverage),
                coverage_percent=execution_coverage,
                missing_lines=[]
            )
            
            # 基础设施模块
            analyzer.coverage_data['src.infra.redis_pool'] = CoverageReport(
                module_name='src.infra.redis_pool',
                total_statements=100,
                covered_statements=int(infra_coverage),
                coverage_percent=infra_coverage,
                missing_lines=[]
            )
            
            # 界面模块
            analyzer.coverage_data['src.interface.dashboard'] = CoverageReport(
                module_name='src.interface.dashboard',
                total_statements=100,
                covered_statements=int(interface_coverage),
                coverage_percent=interface_coverage,
                missing_lines=[]
            )
            
            # 执行门禁检查
            result = analyzer.enforce_coverage_gates()
            
            # 属性验证：所有类别都达标，必须通过
            assert result['passed'], (
                f"所有覆盖率都达标但门禁未通过！"
                f"Core: {core_coverage:.2f}%, "
                f"Execution: {execution_coverage:.2f}%, "
                f"Infra: {infra_coverage:.2f}%, "
                f"Interface: {interface_coverage:.2f}%, "
                f"Violations: {result['violations']}"
            )
            assert len(result['violations']) == 0, f"不应该有违规项: {result['violations']}"
    
    @given(coverage_data=coverage_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_14_coverage_calculation_accuracy(self, coverage_data):
        """Property 14.3: 覆盖率计算准确性
        
        **Validates: Requirements 6.1**
        
        属性: 覆盖率计算必须准确，覆盖率 = 已覆盖语句数 / 总语句数 * 100
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建分析器
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            # 手动设置覆盖率数据
            for file_path, file_data in coverage_data['files'].items():
                rel_path = Path(file_path)
                module_name = str(rel_path).replace('\\', '/').replace('.py', '').replace('/', '.')
                
                summary = file_data['summary']
                total_statements = summary['num_statements']
                covered_statements = summary['covered_lines']
                missing_lines = file_data['missing_lines']
                
                coverage_percent = (covered_statements / total_statements * 100) if total_statements > 0 else 0.0
                
                report = CoverageReport(
                    module_name=module_name,
                    total_statements=total_statements,
                    covered_statements=covered_statements,
                    coverage_percent=coverage_percent,
                    missing_lines=missing_lines
                )
                
                analyzer.coverage_data[module_name] = report
            
            # 验证每个模块的覆盖率计算
            for module_name, report in analyzer.coverage_data.items():
                expected_coverage = (
                    (report.covered_statements / report.total_statements * 100)
                    if report.total_statements > 0
                    else 0.0
                )
                
                assert abs(report.coverage_percent - expected_coverage) < 0.01, (
                    f"模块 {module_name} 覆盖率计算错误: "
                    f"expected={expected_coverage:.2f}%, actual={report.coverage_percent:.2f}%"
                )
            
            # 验证总体覆盖率计算
            total_statements = sum(r.total_statements for r in analyzer.coverage_data.values())
            total_covered = sum(r.covered_statements for r in analyzer.coverage_data.values())
            expected_overall = (total_covered / total_statements * 100) if total_statements > 0 else 0.0
            
            actual_overall = analyzer.get_overall_coverage()
            
            assert abs(actual_overall - expected_overall) < 0.01, (
                f"总体覆盖率计算错误: expected={expected_overall:.2f}%, actual={actual_overall:.2f}%"
            )
    
    @given(
        num_modules=st.integers(min_value=1, max_value=50),
        coverage_range=st.tuples(
            st.floats(min_value=0.0, max_value=100.0),
            st.floats(min_value=0.0, max_value=100.0)
        ).map(lambda x: (min(x), max(x)))
    )
    @settings(max_examples=50, deadline=None)
    def test_property_14_violations_consistency(self, num_modules, coverage_range):
        """Property 14.4: 违规项一致性
        
        **Validates: Requirements 6.7**
        
        属性: violations列表中的每一项都必须对应一个实际的覆盖率不达标情况
        """
        min_coverage, max_coverage = coverage_range
        assume(min_coverage < max_coverage)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建分析器
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            # 创建测试数据
            categories = ['core', 'execution', 'infrastructure', 'interface']
            for i in range(num_modules):
                category = categories[i % len(categories)]
                coverage = min_coverage + (max_coverage - min_coverage) * (i / num_modules)
                
                analyzer.coverage_data[f'src.{category}.module_{i}'] = CoverageReport(
                    module_name=f'src.{category}.module_{i}',
                    total_statements=100,
                    covered_statements=int(coverage),
                    coverage_percent=coverage,
                    missing_lines=[]
                )
            
            # 执行门禁检查
            result = analyzer.enforce_coverage_gates()
            
            # 验证每个violation都对应实际的不达标情况
            targets = analyzer.coverage_targets
            for violation in result['violations']:
                category = violation['category']
                actual = violation['actual']
                target = violation['target']
                
                # 验证actual确实低于target
                assert actual < target, (
                    f"Violation中的actual应该低于target: "
                    f"category={category}, actual={actual:.2f}%, target={target}%"
                )
                
                # 验证target值正确
                if category == 'core':
                    assert target == targets.core_modules
                elif category == 'execution':
                    assert target == targets.execution_modules
                elif category == 'infrastructure':
                    assert target == targets.infrastructure_modules
                elif category == 'interface':
                    assert target == targets.interface_modules
                elif category == 'overall':
                    assert target == targets.overall
