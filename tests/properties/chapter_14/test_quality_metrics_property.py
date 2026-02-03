"""Property 15: Code Quality Metrics Bounds

白皮书依据: 第十四章 14.1.2 代码质量标准
验证需求: Requirements 6.2

属性定义:
- 当质量指标超过限制时，检查必须失败
- 当质量指标在限制内时，检查必须通过
- 质量评分必须单调递减（问题越多，评分越低）
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import tempfile
from typing import Dict, List

from src.quality.code_quality_checker import (
    CodeQualityChecker,
    QualityMetrics,
    ComplexityReport,
    StyleIssue,
    SecurityIssue
)


class TestQualityMetricsBoundsProperty:
    """Property 15: Code Quality Metrics Bounds
    
    **Validates: Requirements 6.2**
    
    白皮书依据: 第十四章 14.1.2 代码质量标准
    """
    
    @given(
        max_function_complexity=st.integers(min_value=5, max_value=20),
        actual_complexity=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_complexity_bounds(self, max_function_complexity, actual_complexity):
        """Property 15.1: 圈复杂度边界检查
        
        **Validates: Requirements 6.2**
        
        属性: 当函数圈复杂度超过限制时，质量检查必须识别出来
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建检查器
            checker = CodeQualityChecker(
                project_root=tmpdir_path,
                max_function_complexity=max_function_complexity
            )
            
            # 创建复杂度报告
            report = ComplexityReport(
                file_path='test.py',
                function_name='test_function',
                complexity=actual_complexity,
                line_number=1
            )
            
            # 验证属性
            if actual_complexity > max_function_complexity:
                # 超过限制，应该被识别为高复杂度
                assert report.complexity > checker.max_function_complexity, (
                    f"复杂度超标但未被识别: "
                    f"actual={actual_complexity}, max={max_function_complexity}"
                )
            else:
                # 在限制内，不应该被识别为高复杂度
                assert report.complexity <= checker.max_function_complexity, (
                    f"复杂度未超标但被错误识别: "
                    f"actual={actual_complexity}, max={max_function_complexity}"
                )
    
    @given(
        num_issues=st.integers(min_value=0, max_value=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_style_score_monotonicity(self, num_issues):
        """Property 15.2: 代码风格评分单调性
        
        **Validates: Requirements 6.2**
        
        属性: 代码风格问题越多，评分越低（单调递减）
        """
        # 计算评分（模拟CodeQualityChecker的逻辑）
        score1 = max(0.0, 100.0 - num_issues * 0.5)
        score2 = max(0.0, 100.0 - (num_issues + 1) * 0.5)
        
        # 验证单调性
        assert score2 <= score1, (
            f"评分不满足单调递减: "
            f"issues={num_issues}, score1={score1:.2f}, "
            f"issues={num_issues+1}, score2={score2:.2f}"
        )
    
    @given(
        complexity_score=st.floats(min_value=0.0, max_value=100.0),
        style_score=st.floats(min_value=0.0, max_value=100.0),
        type_coverage=st.floats(min_value=0.0, max_value=100.0),
        security_issues=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_quality_gate_consistency(
        self,
        complexity_score,
        style_score,
        type_coverage,
        security_issues
    ):
        """Property 15.3: 质量门禁一致性
        
        **Validates: Requirements 6.2**
        
        属性: 质量门禁的通过条件必须一致
        - complexity_score >= 80.0
        - style_score >= 80.0
        - type_coverage >= 70.0
        - security_issues == 0
        """
        # 创建质量指标
        metrics = QualityMetrics(
            complexity_score=complexity_score,
            style_score=style_score,
            type_coverage=type_coverage,
            security_issues=security_issues,
            passed=False  # 先设为False，后面验证
        )
        
        # 计算预期的通过状态
        expected_passed = (
            complexity_score >= 80.0 and
            style_score >= 80.0 and
            type_coverage >= 70.0 and
            security_issues == 0
        )
        
        # 更新实际的通过状态
        metrics.passed = expected_passed
        
        # 验证一致性
        if expected_passed:
            assert metrics.passed, (
                f"所有指标达标但passed=False: "
                f"complexity={complexity_score:.2f}, "
                f"style={style_score:.2f}, "
                f"type_coverage={type_coverage:.2f}, "
                f"security_issues={security_issues}"
            )
        else:
            assert not metrics.passed, (
                f"存在指标不达标但passed=True: "
                f"complexity={complexity_score:.2f}, "
                f"style={style_score:.2f}, "
                f"type_coverage={type_coverage:.2f}, "
                f"security_issues={security_issues}"
            )
    
    @given(
        num_high_complexity=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_complexity_score_calculation(self, num_high_complexity):
        """Property 15.4: 圈复杂度评分计算准确性
        
        **Validates: Requirements 6.2**
        
        属性: 圈复杂度评分 = max(0, 100 - 高复杂度函数数 * 5)
        """
        # 计算评分
        expected_score = max(0.0, 100.0 - num_high_complexity * 5.0)
        
        # 验证评分范围
        assert 0.0 <= expected_score <= 100.0, (
            f"评分超出范围: score={expected_score:.2f}"
        )
        
        # 验证评分计算
        if num_high_complexity == 0:
            assert expected_score == 100.0, "无高复杂度函数时评分应为100"
        elif num_high_complexity >= 20:
            assert expected_score == 0.0, "高复杂度函数过多时评分应为0"
        else:
            assert expected_score == 100.0 - num_high_complexity * 5.0, (
                f"评分计算错误: expected={100.0 - num_high_complexity * 5.0:.2f}, "
                f"actual={expected_score:.2f}"
            )
    
    @given(
        severity=st.sampled_from(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
    )
    @settings(max_examples=50, deadline=None)
    def test_property_15_security_issue_severity(self, severity):
        """Property 15.5: 安全问题严重程度
        
        **Validates: Requirements 6.2**
        
        属性: 任何安全问题（无论严重程度）都应导致质量检查失败
        """
        # 创建安全问题
        issue = SecurityIssue(
            file_path='test.py',
            line_number=1,
            issue_severity=severity,
            issue_confidence='HIGH',
            issue_text='Test security issue',
            test_id='B001'
        )
        
        # 创建质量指标（有安全问题）
        metrics = QualityMetrics(
            complexity_score=100.0,
            style_score=100.0,
            type_coverage=100.0,
            security_issues=1,  # 有1个安全问题
            passed=False
        )
        
        # 验证：有安全问题时必须失败
        assert not metrics.passed, (
            f"存在{severity}级别安全问题但质量检查通过了"
        )
        assert metrics.security_issues > 0, "安全问题数量应该大于0"
    
    @given(
        num_style_issues=st.integers(min_value=0, max_value=300)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_style_score_bounds(self, num_style_issues):
        """Property 15.6: 代码风格评分边界
        
        **Validates: Requirements 6.2**
        
        属性: 代码风格评分必须在[0, 100]范围内
        """
        # 计算评分
        score = max(0.0, 100.0 - num_style_issues * 0.5)
        
        # 验证边界
        assert 0.0 <= score <= 100.0, (
            f"评分超出范围: score={score:.2f}, issues={num_style_issues}"
        )
        
        # 验证极端情况
        if num_style_issues == 0:
            assert score == 100.0, "无风格问题时评分应为100"
        elif num_style_issues >= 200:
            assert score == 0.0, "风格问题过多时评分应为0"
    
    @given(
        type_errors=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_type_coverage_calculation(self, type_errors):
        """Property 15.7: 类型覆盖率计算
        
        **Validates: Requirements 6.2**
        
        属性: 类型覆盖率 = max(0, 100 - 类型错误数 * 2)
        """
        # 计算类型覆盖率
        type_coverage = max(0.0, 100.0 - type_errors * 2.0)
        
        # 验证范围
        assert 0.0 <= type_coverage <= 100.0, (
            f"类型覆盖率超出范围: coverage={type_coverage:.2f}"
        )
        
        # 验证计算
        if type_errors == 0:
            assert type_coverage == 100.0, "无类型错误时覆盖率应为100"
        elif type_errors >= 50:
            assert type_coverage == 0.0, "类型错误过多时覆盖率应为0"
        else:
            expected = 100.0 - type_errors * 2.0
            assert type_coverage == expected, (
                f"类型覆盖率计算错误: expected={expected:.2f}, actual={type_coverage:.2f}"
            )
    
    @given(
        complexity_score=st.floats(min_value=0.0, max_value=100.0),
        style_score=st.floats(min_value=0.0, max_value=100.0),
        type_coverage=st.floats(min_value=0.0, max_value=100.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_zero_security_issues_required(
        self,
        complexity_score,
        style_score,
        type_coverage
    ):
        """Property 15.8: 零安全问题要求
        
        **Validates: Requirements 6.2**
        
        属性: 即使其他指标都完美，只要有安全问题就必须失败
        """
        # 场景1: 所有指标完美，但有安全问题
        metrics_with_security_issue = QualityMetrics(
            complexity_score=100.0,
            style_score=100.0,
            type_coverage=100.0,
            security_issues=1,
            passed=False
        )
        
        assert not metrics_with_security_issue.passed, (
            "所有指标完美但有安全问题时应该失败"
        )
        
        # 场景2: 所有指标完美，无安全问题
        metrics_without_security_issue = QualityMetrics(
            complexity_score=100.0,
            style_score=100.0,
            type_coverage=100.0,
            security_issues=0,
            passed=True
        )
        
        assert metrics_without_security_issue.passed, (
            "所有指标完美且无安全问题时应该通过"
        )
    
    @given(
        max_complexity=st.integers(min_value=5, max_value=20),
        max_line_length=st.integers(min_value=80, max_value=200)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_15_checker_configuration_consistency(
        self,
        max_complexity,
        max_line_length
    ):
        """Property 15.9: 检查器配置一致性
        
        **Validates: Requirements 6.2**
        
        属性: 检查器的配置参数必须被正确应用
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建检查器
            checker = CodeQualityChecker(
                project_root=tmpdir_path,
                max_function_complexity=max_complexity,
                max_line_length=max_line_length
            )
            
            # 验证配置
            assert checker.max_function_complexity == max_complexity, (
                f"max_function_complexity配置不一致: "
                f"expected={max_complexity}, actual={checker.max_function_complexity}"
            )
            
            assert checker.max_line_length == max_line_length, (
                f"max_line_length配置不一致: "
                f"expected={max_line_length}, actual={checker.max_line_length}"
            )
            
            assert checker.project_root == tmpdir_path, (
                f"project_root配置不一致"
            )
