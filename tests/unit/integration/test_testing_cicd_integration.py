"""Unit tests for Testing-CI/CD Integration

白皮书依据: 第十四章 14.1 质量标准, 第十二章 12.2 测试与CI/CD集成
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.integration.testing_cicd_integration import (
    TestingCICDIntegration,
    QualityGateResult,
    get_testing_cicd_integration,
    run_ci_quality_gates
)
from src.quality.test_coverage_analyzer import CoverageTarget
from src.quality.code_quality_checker import QualityMetrics
from src.infra.cross_chapter_event_bus import (
    CrossChapterEventBus,
    CrossChapterEventType,
    CrossChapterEvent
)
from src.infra.event_bus import EventBus, EventPriority


class TestTestingCICDIntegration:
    """测试Testing-CI/CD集成类"""
    
    @pytest.fixture
    def mock_event_bus(self):
        """创建模拟事件总线"""
        mock_base_bus = Mock(spec=EventBus)
        mock_base_bus.publish = AsyncMock(return_value=True)
        mock_base_bus.subscribe = AsyncMock(return_value="handler_id")
        
        mock_cross_bus = Mock(spec=CrossChapterEventBus)
        mock_cross_bus.base_event_bus = mock_base_bus
        mock_cross_bus.publish = AsyncMock(return_value=True)
        mock_cross_bus.subscribe = AsyncMock(return_value="handler_id")
        
        return mock_cross_bus
    
    @pytest.fixture
    def integration(self, mock_event_bus, tmp_path):
        """创建集成实例"""
        return TestingCICDIntegration(
            project_root=tmp_path,
            event_bus=mock_event_bus
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, integration):
        """测试初始化"""
        await integration.initialize()
        
        assert integration.stats['start_time'] is not None
        assert integration.coverage_analyzer is not None
        assert integration.quality_checker is not None
    
    @pytest.mark.asyncio
    async def test_initialization_without_event_bus(self, tmp_path):
        """测试无事件总线的初始化"""
        integration = TestingCICDIntegration(project_root=tmp_path)
        
        with patch('src.infra.cross_chapter_event_bus.get_cross_chapter_event_bus') as mock_get:
            mock_bus = Mock(spec=CrossChapterEventBus)
            mock_get.return_value = mock_bus
            
            await integration.initialize()
            
            assert integration.event_bus == mock_bus
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_quality_gates_all_pass(self, integration):
        """测试质量门禁检查 - 全部通过"""
        await integration.initialize()
        
        # Mock覆盖率分析器
        mock_coverage_result = {
            'passed': True,
            'overall_coverage': 85.0,
            'category_coverage': {
                'core': 90.0,
                'execution': 85.0,
                'infrastructure': 80.0,
                'interface': 70.0
            },
            'violations': []
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        # Mock质量检查器
        mock_quality_metrics = QualityMetrics(
            complexity_score=85.0,
            style_score=90.0,
            type_coverage=80.0,
            security_issues=0,
            passed=True
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        # 执行检查
        result = await integration.run_quality_gates()
        
        # 验证结果
        assert result.passed is True
        assert result.coverage_passed is True
        assert result.quality_passed is True
        assert len(result.violations) == 0
        
        # 验证统计信息
        assert integration.stats['total_checks'] == 1
        assert integration.stats['passed_checks'] == 1
        assert integration.stats['failed_checks'] == 0
    
    @pytest.mark.asyncio
    async def test_run_quality_gates_coverage_fail(self, integration):
        """测试质量门禁检查 - 覆盖率失败"""
        await integration.initialize()
        
        # Mock覆盖率分析器 - 失败
        mock_coverage_result = {
            'passed': False,
            'overall_coverage': 65.0,
            'category_coverage': {
                'core': 80.0,
                'execution': 75.0,
                'infrastructure': 70.0,
                'interface': 55.0
            },
            'violations': [
                {
                    'category': 'core',
                    'actual': 80.0,
                    'target': 85.0,
                    'message': '核心模块覆盖率不达标: 80.00% < 85%'
                }
            ]
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        # Mock质量检查器 - 通过
        mock_quality_metrics = QualityMetrics(
            complexity_score=85.0,
            style_score=90.0,
            type_coverage=80.0,
            security_issues=0,
            passed=True
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        # 执行检查
        result = await integration.run_quality_gates()
        
        # 验证结果
        assert result.passed is False
        assert result.coverage_passed is False
        assert result.quality_passed is True
        assert len(result.violations) == 1
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        assert published_event.event_type == CrossChapterEventType.COVERAGE_GATE_FAILED
        assert published_event.source_chapter == 14
        assert published_event.target_chapter == 17
        
        # 验证统计信息
        assert integration.stats['total_checks'] == 1
        assert integration.stats['passed_checks'] == 0
        assert integration.stats['failed_checks'] == 1
        assert integration.stats['coverage_failures'] == 1
    
    @pytest.mark.asyncio
    async def test_run_quality_gates_quality_fail(self, integration):
        """测试质量门禁检查 - 质量检查失败"""
        await integration.initialize()
        
        # Mock覆盖率分析器 - 通过
        mock_coverage_result = {
            'passed': True,
            'overall_coverage': 85.0,
            'category_coverage': {
                'core': 90.0,
                'execution': 85.0,
                'infrastructure': 80.0,
                'interface': 70.0
            },
            'violations': []
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        # Mock质量检查器 - 失败
        mock_quality_metrics = QualityMetrics(
            complexity_score=75.0,  # < 80.0
            style_score=70.0,  # < 80.0
            type_coverage=65.0,  # < 70.0
            security_issues=2,  # > 0
            passed=False
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        # 执行检查
        result = await integration.run_quality_gates()
        
        # 验证结果
        assert result.passed is False
        assert result.coverage_passed is True
        assert result.quality_passed is False
        assert len(result.violations) == 4  # complexity, style, type_coverage, security
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        assert published_event.event_type == CrossChapterEventType.QUALITY_CHECK_FAILED
        assert published_event.source_chapter == 14
        assert published_event.target_chapter == 17
        
        # 验证统计信息
        assert integration.stats['total_checks'] == 1
        assert integration.stats['passed_checks'] == 0
        assert integration.stats['failed_checks'] == 1
        assert integration.stats['quality_failures'] == 1
    
    @pytest.mark.asyncio
    async def test_run_quality_gates_both_fail(self, integration):
        """测试质量门禁检查 - 覆盖率和质量都失败"""
        await integration.initialize()
        
        # Mock覆盖率分析器 - 失败
        mock_coverage_result = {
            'passed': False,
            'overall_coverage': 65.0,
            'category_coverage': {},
            'violations': [{'message': '总体覆盖率不达标'}]
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        # Mock质量检查器 - 失败
        mock_quality_metrics = QualityMetrics(
            complexity_score=75.0,
            style_score=70.0,
            type_coverage=65.0,
            security_issues=1,
            passed=False
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        # 执行检查
        result = await integration.run_quality_gates()
        
        # 验证结果
        assert result.passed is False
        assert result.coverage_passed is False
        assert result.quality_passed is False
        assert len(result.violations) >= 5  # 至少1个覆盖率 + 4个质量
        
        # 验证事件发布（应该发布2个事件）
        assert integration.event_bus.publish.call_count == 2
        
        # 验证统计信息
        assert integration.stats['total_checks'] == 1
        assert integration.stats['passed_checks'] == 0
        assert integration.stats['failed_checks'] == 1
        assert integration.stats['coverage_failures'] == 1
        assert integration.stats['quality_failures'] == 1
    
    @pytest.mark.asyncio
    async def test_run_quality_gates_coverage_exception(self, integration):
        """测试质量门禁检查 - 覆盖率检查异常"""
        await integration.initialize()
        
        # Mock覆盖率分析器 - 抛出异常
        integration.coverage_analyzer.analyze_coverage = Mock(side_effect=Exception("Coverage error"))
        
        # Mock质量检查器 - 通过
        mock_quality_metrics = QualityMetrics(
            complexity_score=85.0,
            style_score=90.0,
            type_coverage=80.0,
            security_issues=0,
            passed=True
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        # 执行检查
        result = await integration.run_quality_gates()
        
        # 验证结果
        assert result.passed is False
        assert result.coverage_passed is False
        assert result.quality_passed is True
        assert any('Coverage error' in str(v) for v in result.violations)
    
    @pytest.mark.asyncio
    async def test_run_quality_gates_quality_exception(self, integration):
        """测试质量门禁检查 - 质量检查异常"""
        await integration.initialize()
        
        # Mock覆盖率分析器 - 通过
        mock_coverage_result = {
            'passed': True,
            'overall_coverage': 85.0,
            'category_coverage': {},
            'violations': []
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        # Mock质量检查器 - 抛出异常
        integration.quality_checker.check_all = Mock(side_effect=Exception("Quality error"))
        
        # 执行检查
        result = await integration.run_quality_gates()
        
        # 验证结果
        assert result.passed is False
        assert result.coverage_passed is True
        assert result.quality_passed is False
        assert any('Quality error' in str(v) for v in result.violations)
    
    @pytest.mark.asyncio
    async def test_check_coverage_only(self, integration):
        """测试仅检查覆盖率"""
        await integration.initialize()
        
        mock_coverage_result = {
            'passed': True,
            'overall_coverage': 85.0,
            'category_coverage': {},
            'violations': []
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        result = await integration.check_coverage_only()
        
        assert result['passed'] is True
        assert result['overall_coverage'] == 85.0
        integration.coverage_analyzer.analyze_coverage.assert_called_once()
        integration.coverage_analyzer.enforce_coverage_gates.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_coverage_only_fail(self, integration):
        """测试仅检查覆盖率 - 失败"""
        await integration.initialize()
        
        mock_coverage_result = {
            'passed': False,
            'overall_coverage': 65.0,
            'category_coverage': {},
            'violations': [{'message': '覆盖率不达标'}]
        }
        
        integration.coverage_analyzer.analyze_coverage = Mock()
        integration.coverage_analyzer.enforce_coverage_gates = Mock(return_value=mock_coverage_result)
        
        result = await integration.check_coverage_only()
        
        assert result['passed'] is False
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_quality_only(self, integration):
        """测试仅检查质量"""
        await integration.initialize()
        
        mock_quality_metrics = QualityMetrics(
            complexity_score=85.0,
            style_score=90.0,
            type_coverage=80.0,
            security_issues=0,
            passed=True
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        result = await integration.check_quality_only()
        
        assert result.passed is True
        assert result.complexity_score == 85.0
        integration.quality_checker.check_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_quality_only_fail(self, integration):
        """测试仅检查质量 - 失败"""
        await integration.initialize()
        
        mock_quality_metrics = QualityMetrics(
            complexity_score=75.0,
            style_score=70.0,
            type_coverage=65.0,
            security_issues=2,
            passed=False
        )
        
        integration.quality_checker.check_all = Mock(return_value=mock_quality_metrics)
        
        result = await integration.check_quality_only()
        
        assert result.passed is False
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_coverage_gate_failed_event(self, integration):
        """测试发布覆盖率门禁失败事件"""
        await integration.initialize()
        
        coverage_result = {
            'overall_coverage': 65.0,
            'category_coverage': {'core': 80.0},
            'violations': [{'message': '覆盖率不达标'}]
        }
        
        await integration._publish_coverage_gate_failed_event(coverage_result)
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        
        assert published_event.event_type == CrossChapterEventType.COVERAGE_GATE_FAILED
        assert published_event.source_chapter == 14
        assert published_event.target_chapter == 17
        assert published_event.priority == EventPriority.HIGH
        assert published_event.data['overall_coverage'] == 65.0
        
        # 验证统计信息
        assert integration.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_quality_check_failed_event(self, integration):
        """测试发布质量检查失败事件"""
        await integration.initialize()
        
        quality_metrics = QualityMetrics(
            complexity_score=75.0,
            style_score=70.0,
            type_coverage=65.0,
            security_issues=2,
            passed=False
        )
        
        await integration._publish_quality_check_failed_event(quality_metrics)
        
        # 验证事件发布
        integration.event_bus.publish.assert_called_once()
        published_event = integration.event_bus.publish.call_args[0][0]
        
        assert published_event.event_type == CrossChapterEventType.QUALITY_CHECK_FAILED
        assert published_event.source_chapter == 14
        assert published_event.target_chapter == 17
        assert published_event.priority == EventPriority.HIGH
        assert published_event.data['complexity_score'] == 75.0
        assert published_event.data['security_issues'] == 2
        
        # 验证统计信息
        assert integration.stats['events_published'] == 1
    
    @pytest.mark.asyncio
    async def test_publish_event_without_event_bus(self, tmp_path):
        """测试无事件总线时发布事件"""
        integration = TestingCICDIntegration(project_root=tmp_path, event_bus=None)
        await integration.initialize()
        
        # 设置event_bus为None
        integration.event_bus = None
        
        coverage_result = {
            'overall_coverage': 65.0,
            'category_coverage': {},
            'violations': []
        }
        
        # 应该不抛出异常，只是记录警告
        await integration._publish_coverage_gate_failed_event(coverage_result)
        
        # 验证统计信息未更新
        assert integration.stats['events_published'] == 0
    
    def test_get_stats(self, integration):
        """测试获取统计信息"""
        integration.stats['start_time'] = datetime.now()
        integration.stats['total_checks'] = 10
        integration.stats['passed_checks'] = 7
        integration.stats['failed_checks'] = 3
        integration.stats['coverage_failures'] = 2
        integration.stats['quality_failures'] = 1
        integration.stats['events_published'] = 3
        
        stats = integration.get_stats()
        
        assert stats['total_checks'] == 10
        assert stats['passed_checks'] == 7
        assert stats['failed_checks'] == 3
        assert stats['success_rate'] == 0.7
        assert stats['coverage_failure_rate'] == 0.2
        assert stats['quality_failure_rate'] == 0.1
        assert 'uptime_seconds' in stats
    
    def test_custom_coverage_targets(self, mock_event_bus, tmp_path):
        """测试自定义覆盖率目标"""
        custom_targets = CoverageTarget(
            core_modules=90.0,
            execution_modules=85.0,
            infrastructure_modules=80.0,
            interface_modules=70.0,
            overall=75.0
        )
        
        integration = TestingCICDIntegration(
            project_root=tmp_path,
            event_bus=mock_event_bus,
            coverage_targets=custom_targets
        )
        
        assert integration.coverage_analyzer.coverage_targets.core_modules == 90.0
        assert integration.coverage_analyzer.coverage_targets.overall == 75.0


class TestGlobalFunctions:
    """测试全局函数"""
    
    @pytest.mark.asyncio
    async def test_get_testing_cicd_integration(self, tmp_path):
        """测试获取全局集成实例"""
        # 重置全局实例
        import src.integration.testing_cicd_integration as module
        module._global_testing_cicd_integration = None
        
        mock_bus = Mock(spec=CrossChapterEventBus)
        
        integration = await get_testing_cicd_integration(
            project_root=tmp_path,
            event_bus=mock_bus
        )
        
        assert integration is not None
        assert integration.project_root == tmp_path
        assert integration.event_bus == mock_bus
        
        # 再次调用应该返回同一实例
        integration2 = await get_testing_cicd_integration()
        assert integration2 is integration
    
    @pytest.mark.asyncio
    async def test_run_ci_quality_gates(self, tmp_path):
        """测试全局质量门禁检查函数"""
        # 重置全局实例
        import src.integration.testing_cicd_integration as module
        module._global_testing_cicd_integration = None
        
        with patch('src.integration.testing_cicd_integration.get_testing_cicd_integration') as mock_get:
            mock_integration = Mock(spec=TestingCICDIntegration)
            mock_result = QualityGateResult(
                passed=True,
                coverage_passed=True,
                quality_passed=True,
                coverage_result={'passed': True},
                quality_metrics=QualityMetrics(85.0, 90.0, 80.0, 0, True),
                violations=[],
                timestamp=datetime.now()
            )
            mock_integration.run_quality_gates = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_integration
            
            result = await run_ci_quality_gates()
            
            assert result.passed is True
            mock_integration.run_quality_gates.assert_called_once()
