#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 终极100%覆盖率测试

🧪 Test Engineer 专门负责覆盖最后的2行代码：273-274, 792->815
目标：达到100%测试覆盖率

遵循测试铁律：
- 严禁跳过任何测试
- 测试超时必须溯源修复
- 不得使用timeout作为跳过理由
- 发现问题立刻修复
- 强制要求：测试覆盖率必须达到100%

专门针对未覆盖的2行代码：
- 273-274行：Scholar直接调用异常处理的logger.warning
- 792->815行：冲突检测分支的完整流程
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorUltimate100Percent:
    """终极100%覆盖率测试 - 专门针对最后2行代码"""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock事件总线"""
        event_bus = MagicMock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def mock_container(self):
        """Mock依赖容器"""
        container = MagicMock(spec=DIContainer)
        container.is_registered = MagicMock(return_value=True)
        return container

    @pytest.fixture
    def coordinator(self, mock_event_bus, mock_container):
        """创建协调器实例"""
        return AIBrainCoordinator(mock_event_bus, mock_container)

    @pytest.mark.asyncio
    async def test_lines_273_274_scholar_exception_logger_warning(self, coordinator):
        """精确测试273-274行：Scholar异常处理的logger.warning调用
        
        这个测试专门覆盖Scholar直接调用失败时的logger.warning语句
        确保覆盖273-274行的具体代码
        """
        # 设置Scholar实例但让其抛出异常
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=RuntimeError("Scholar research failed"))
        coordinator.scholar = mock_scholar
        
        # 禁用批处理以确保走直接调用路径
        coordinator.enable_batch_processing = False
        
        context = {"research_topic": "test_factor"}
        correlation_id = "test_correlation_id"
        
        # 使用patch来监控logger.warning调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行决策请求，应该触发273-274行的logger.warning
            result = await coordinator._request_decision_direct(context, "scholar", correlation_id)
            
            # 验证Scholar被调用了
            mock_scholar.research.assert_called_once_with(context)
            
            # 验证logger.warning被调用了（这就是273-274行）
            # 注意：可能会有多次warning调用（异常处理 + 超时），我们检查是否包含Scholar异常处理的调用
            mock_logger.warning.assert_called()
            warning_calls = mock_logger.warning.call_args_list
            scholar_warning_found = any("Scholar直接调用失败" in str(call) for call in warning_calls)
            assert scholar_warning_found, f"未找到Scholar异常处理的warning调用，实际调用: {warning_calls}"
            
            # 由于异常，应该回退到事件模式，但事件发布也可能失败，所以返回None
            assert result is None

    @pytest.mark.asyncio
    async def test_lines_792_815_conflict_detection_branch(self, coordinator):
        """精确测试792->815行：冲突检测分支的完整流程
        
        这个测试专门覆盖决策冲突检测和保守策略生成的完整流程
        确保覆盖792->815行的冲突检测逻辑
        """
        # 创建置信度差异小于0.1的冲突决策
        decisions = [
            BrainDecision(
                decision_id="soldier_decision",
                primary_brain="soldier",
                action="buy",
                confidence=0.7500,  # 基准置信度
                reasoning="Soldier建议买入",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="test_1"
            ),
            BrainDecision(
                decision_id="commander_decision", 
                primary_brain="commander",
                action="sell",
                confidence=0.7499,  # 置信度差异0.0001 < 0.1，会触发冲突检测
                reasoning="Commander建议卖出",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="test_2"
            )
        ]
        
        # 记录初始冲突统计
        initial_conflicts = coordinator.stats.get("coordination_conflicts", 0)
        
        # 使用patch来监控logger.warning调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行冲突解决，应该触发792->815行
            result = await coordinator.resolve_conflicts(decisions)
            
            # 验证冲突检测被触发（792->815行的逻辑）
            assert coordinator.stats["coordination_conflicts"] > initial_conflicts
            
            # 验证logger.warning被调用了（这是792->815行分支的一部分）
            mock_logger.warning.assert_called()
            warning_call_args = mock_logger.warning.call_args[0][0]
            assert "检测到决策冲突" in warning_call_args
            
            # 验证返回了保守决策
            assert result is not None
            assert result.primary_brain == "coordinator_conflict_resolution"
            
            # 验证保守策略逻辑
            # 由于有买卖冲突，应该选择持有策略
            assert result.action in ["hold", "reduce"]  # 保守策略
            
            # 验证置信度被降低（平均值*0.6）
            expected_avg_confidence = (0.7500 + 0.7499) / 2 * 0.6
            assert abs(result.confidence - expected_avg_confidence) < 0.01
            
            # 验证支持数据包含冲突信息
            assert result.supporting_data["conflict_resolution"] is True
            assert len(result.supporting_data["conflicting_decisions"]) == 2

    @pytest.mark.asyncio
    async def test_comprehensive_final_coverage_verification(self, coordinator):
        """综合最终覆盖率验证测试
        
        这个测试确保我们覆盖了所有剩余的代码路径
        """
        
        # 1. 测试Scholar异常处理路径（273-274行）
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=ConnectionError("Network error"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行Scholar决策请求
            scholar_result = await coordinator._request_decision_direct(
                {"topic": "test"}, "scholar", "scholar_test"
            )
            
            # 验证异常处理和logger调用
            assert scholar_result is None
            mock_scholar.research.assert_called_once()
            mock_logger.warning.assert_called()
            
            # 重置mock以便下一个测试
            mock_logger.reset_mock()
        
        # 2. 测试冲突检测路径（792->815行）
        conflict_decisions = [
            BrainDecision(
                decision_id="conflict1", primary_brain="soldier", action="buy",
                confidence=0.8000, reasoning="Strong buy", supporting_data={},
                timestamp=datetime.now(), correlation_id="conflict1"
            ),
            BrainDecision(
                decision_id="conflict2", primary_brain="commander", action="sell",
                confidence=0.7999, reasoning="Strong sell", supporting_data={},  # 差异0.0001 < 0.1
                timestamp=datetime.now(), correlation_id="conflict2"
            )
        ]
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行冲突解决
            conflict_result = await coordinator.resolve_conflicts(conflict_decisions)
            
            # 验证冲突解决
            assert conflict_result.primary_brain == "coordinator_conflict_resolution"
            assert conflict_result.supporting_data["conflict_resolution"] is True
            
            # 验证logger.warning被调用（792->815行分支）
            mock_logger.warning.assert_called()
            warning_call_args = mock_logger.warning.call_args[0][0]
            assert "检测到决策冲突" in warning_call_args
            
            # 验证统计信息更新
            assert coordinator.stats["coordination_conflicts"] > 0

    @pytest.mark.asyncio
    async def test_edge_cases_for_ultimate_coverage(self, coordinator):
        """边界情况测试确保终极覆盖率"""
        
        # 测试不同类型的Scholar异常
        exceptions_to_test = [
            ValueError("Invalid input"),
            TimeoutError("Request timeout"),
            ConnectionError("Connection lost"),
            RuntimeError("Runtime error")
        ]
        
        for i, exception in enumerate(exceptions_to_test):
            mock_scholar = AsyncMock(spec=IScholarEngine)
            mock_scholar.research = AsyncMock(side_effect=exception)
            coordinator.scholar = mock_scholar
            coordinator.enable_batch_processing = False
            
            with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
                # 执行决策请求
                result = await coordinator._request_decision_direct(
                    {"test": f"data_{i}"}, "scholar", f"test_{i}"
                )
                
                # 验证异常被正确处理
                assert result is None
                mock_scholar.research.assert_called_once()
                mock_logger.warning.assert_called()
        
        # 测试不同置信度差异的冲突检测 - 每次重置统计
        confidence_pairs = [
            (0.75, 0.7499),   # 差异0.0001 < 0.1
            (0.80, 0.7999),   # 差异0.0001 < 0.1
            (0.60, 0.5999),   # 差异0.0001 < 0.1
            (0.90, 0.8999),   # 差异0.0001 < 0.1
        ]
        
        for i, (conf1, conf2) in enumerate(confidence_pairs):
            # 重置统计以确保每次测试都能检测到冲突增加
            coordinator.stats["coordination_conflicts"] = 0
            
            decisions = [
                BrainDecision(
                    decision_id=f"edge1_{i}", primary_brain="soldier", action="buy",
                    confidence=conf1, reasoning=f"Edge test 1_{i}", supporting_data={},
                    timestamp=datetime.now(), correlation_id=f"edge1_{i}"
                ),
                BrainDecision(
                    decision_id=f"edge2_{i}", primary_brain="commander", action="sell",
                    confidence=conf2, reasoning=f"Edge test 2_{i}", supporting_data={},
                    timestamp=datetime.now(), correlation_id=f"edge2_{i}"
                )
            ]
            
            initial_conflicts = coordinator.stats.get("coordination_conflicts", 0)
            
            with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
                # 执行冲突解决
                result = await coordinator.resolve_conflicts(decisions)
                
                # 验证冲突被检测到
                assert coordinator.stats["coordination_conflicts"] > initial_conflicts
                assert result.primary_brain == "coordinator_conflict_resolution"
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_ultimate_verification_100_percent_coverage(self, coordinator):
        """终极验证测试 - 确保100%覆盖率
        
        这是最终的验证测试，确保我们覆盖了所有代码路径
        """
        
        # 确保Scholar异常处理被覆盖（273-274行）
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=Exception("Ultimate test exception"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 测试异常处理
            result = await coordinator._request_decision_direct(
                {"ultimate": "test"}, "scholar", "ultimate_test"
            )
            assert result is None
            mock_logger.warning.assert_called()
            
            # 验证logger.warning的具体调用
            warning_calls = mock_logger.warning.call_args_list
            assert any("Scholar直接调用失败" in str(call) for call in warning_calls)
            
            # 重置mock
            mock_logger.reset_mock()
        
        # 确保冲突检测被覆盖（792->815行）
        ultimate_decisions = [
            BrainDecision(
                decision_id="ultimate1", primary_brain="soldier", action="buy",
                confidence=0.7000, reasoning="Ultimate 1", supporting_data={},
                timestamp=datetime.now(), correlation_id="ultimate1"
            ),
            BrainDecision(
                decision_id="ultimate2", primary_brain="commander", action="sell",
                confidence=0.6999, reasoning="Ultimate 2", supporting_data={},  # 差异0.0001 < 0.1
                timestamp=datetime.now(), correlation_id="ultimate2"
            )
        ]
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 测试冲突检测
            ultimate_result = await coordinator.resolve_conflicts(ultimate_decisions)
            assert ultimate_result.primary_brain == "coordinator_conflict_resolution"
            mock_logger.warning.assert_called()
            
            # 验证logger.warning的具体调用
            warning_calls = mock_logger.warning.call_args_list
            assert any("检测到决策冲突" in str(call) for call in warning_calls)
        
        print("✅ 终极验证完成：所有关键路径已覆盖，应该达到100%覆盖率")


class TestSpecificLinesCoverageUltimate:
    """专门针对特定行号的终极覆盖测试"""

    @pytest.fixture
    def coordinator(self):
        """创建基础协调器"""
        event_bus = MagicMock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        container = MagicMock(spec=DIContainer)
        return AIBrainCoordinator(event_bus, container)

    @pytest.mark.asyncio
    async def test_exact_lines_273_274_with_logger_verification(self, coordinator):
        """精确覆盖273-274行并验证logger调用"""
        # 设置Scholar异常
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=Exception("Exact line test"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        # 监控logger调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 调用应该触发273-274行的异常处理
            result = await coordinator._request_decision_direct(
                {"exact": "test"}, "scholar", "exact_test"
            )
            
            # 验证异常被捕获，方法返回None
            assert result is None
            mock_scholar.research.assert_called_once()
            
            # 验证logger.warning被调用（这就是273-274行）
            # 注意：可能有多次warning调用，我们检查是否包含Scholar异常处理的调用
            mock_logger.warning.assert_called()
            warning_calls = mock_logger.warning.call_args_list
            scholar_warning_found = any("Scholar直接调用失败" in str(call) for call in warning_calls)
            assert scholar_warning_found, f"未找到Scholar异常处理的warning调用，实际调用: {warning_calls}"

    @pytest.mark.asyncio
    async def test_exact_lines_792_815_with_logger_verification(self, coordinator):
        """精确覆盖792->815行并验证logger调用"""
        # 创建置信度差异小于0.1的决策
        decisions = [
            BrainDecision(
                decision_id="exact1", primary_brain="soldier", action="buy",
                confidence=0.750, reasoning="Exact test", supporting_data={},
                timestamp=datetime.now(), correlation_id="exact1"
            ),
            BrainDecision(
                decision_id="exact2", primary_brain="commander", action="sell",
                confidence=0.749, reasoning="Exact test", supporting_data={},  # 差异0.001 < 0.1
                timestamp=datetime.now(), correlation_id="exact2"
            )
        ]
        
        initial_conflicts = coordinator.stats.get("coordination_conflicts", 0)
        
        # 监控logger调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行冲突解决，应该触发792->815行
            result = await coordinator.resolve_conflicts(decisions)
            
            # 验证冲突检测逻辑被触发
            assert coordinator.stats["coordination_conflicts"] > initial_conflicts
            assert result.primary_brain == "coordinator_conflict_resolution"
            
            # 验证logger.warning被调用（这是792->815行分支的一部分）
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "检测到决策冲突" in call_args
            
            # 验证保守决策生成
            assert result.supporting_data["conflict_resolution"] is True
            assert "conflicting_decisions" in result.supporting_data

    @pytest.mark.asyncio
    async def test_final_100_percent_verification(self, coordinator):
        """最终100%覆盖率验证"""
        
        # 测试1: 确保273-274行被覆盖
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=Exception("Final verification"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            result = await coordinator._request_decision_direct(
                {"final": "verification"}, "scholar", "final_verification"
            )
            assert result is None
            mock_logger.warning.assert_called()
            mock_logger.reset_mock()
        
        # 测试2: 确保792->815行被覆盖
        final_decisions = [
            BrainDecision(
                decision_id="final1", primary_brain="soldier", action="buy",
                confidence=0.7000, reasoning="Final verification", supporting_data={},
                timestamp=datetime.now(), correlation_id="final1"
            ),
            BrainDecision(
                decision_id="final2", primary_brain="commander", action="sell",
                confidence=0.6999, reasoning="Final verification", supporting_data={},
                timestamp=datetime.now(), correlation_id="final2"
            )
        ]
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            result = await coordinator.resolve_conflicts(final_decisions)
            assert result.primary_brain == "coordinator_conflict_resolution"
            mock_logger.warning.assert_called()
        
        print("✅ 最终100%覆盖率验证完成")