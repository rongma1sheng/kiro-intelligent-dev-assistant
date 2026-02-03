#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 100%覆盖率测试

🧪 Test Engineer 专门负责达到100%测试覆盖率
目标：覆盖剩余的6行代码：273-274, 457-461, 792->815

遵循测试铁律：
- 严禁跳过任何测试
- 测试超时必须溯源修复
- 不得使用timeout作为跳过理由
- 发现问题立刻修复
- 强制要求：测试覆盖率必须达到100%
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinator100Percent:
    """专门针对100%覆盖率的测试"""

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
    async def test_scholar_direct_call_exception_lines_273_274(self, coordinator):
        """测试Scholar直接调用异常处理 - 覆盖273-274行
        
        这个测试专门覆盖Scholar直接调用失败时的异常处理逻辑
        """
        # 设置Scholar实例但让其抛出异常
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=Exception("Scholar research failed"))
        coordinator.scholar = mock_scholar
        
        # 禁用批处理以确保走直接调用路径
        coordinator.enable_batch_processing = False
        
        context = {"research_topic": "test_factor"}
        
        # 执行决策请求，应该捕获异常并回退到事件模式
        result = await coordinator._request_decision_direct(context, "scholar", "test_correlation_id")
        
        # 验证Scholar被调用了
        mock_scholar.research.assert_called_once_with(context)
        
        # 由于异常，应该回退到事件模式，但事件发布也可能失败，所以返回None
        # 这会触发超时处理逻辑
        assert result is None

    @pytest.mark.asyncio
    async def test_batch_decision_exception_handling_lines_457_461(self, coordinator):
        """测试批量决策异常处理 - 覆盖457-461行
        
        这个测试专门覆盖批量决策中的异常处理和备用决策生成
        """
        # 创建会失败的请求
        requests = [
            ({"data": "test1"}, "soldier"),
            ({"data": "test2"}, "commander"),  # 这个会失败
            ({"data": "test3"}, "scholar")
        ]
        
        # Mock request_decision方法让第二个请求失败
        original_method = coordinator.request_decision
        
        async def mock_request_decision(context, brain):
            if context.get("data") == "test2":
                raise Exception("Commander decision failed")
            # 为其他请求返回正常决策
            return BrainDecision(
                decision_id=f"{brain}_test",
                primary_brain=brain,
                action="buy",
                confidence=0.8,
                reasoning="测试决策",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"test_{brain}"
            )
        
        coordinator.request_decision = AsyncMock(side_effect=mock_request_decision)
        
        # 执行批量决策
        results = await coordinator.request_decisions_batch(requests)
        
        # 验证结果
        assert len(results) == 3
        
        # 第一个和第三个应该成功
        assert results[0].primary_brain == "soldier"
        assert results[2].primary_brain == "scholar"
        
        # 第二个应该是备用决策（由于异常）
        assert "fallback" in results[1].decision_id
        assert results[1].primary_brain.startswith("coordinator_fallback")

    @pytest.mark.asyncio
    async def test_conflict_detection_lines_792_815(self, coordinator):
        """测试冲突检测逻辑 - 覆盖792->815行
        
        这个测试专门覆盖决策冲突检测和保守策略生成的完整流程
        """
        # 创建置信度相近的冲突决策（差异<0.1）
        decisions = [
            BrainDecision(
                decision_id="soldier_decision",
                primary_brain="soldier",
                action="buy",
                confidence=0.75,  # 基准置信度
                reasoning="Soldier建议买入",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="test_1"
            ),
            BrainDecision(
                decision_id="commander_decision", 
                primary_brain="commander",
                action="sell",
                confidence=0.74,  # 置信度差异0.01 < 0.1，会触发冲突检测
                reasoning="Commander建议卖出",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="test_2"
            ),
            BrainDecision(
                decision_id="scholar_decision",
                primary_brain="scholar", 
                action="hold",
                confidence=0.73,  # 置信度差异0.02 < 0.1
                reasoning="Scholar建议持有",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="test_3"
            )
        ]
        
        # 记录初始冲突统计
        initial_conflicts = coordinator.stats.get("coordination_conflicts", 0)
        
        # 执行冲突解决
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证冲突检测被触发
        assert coordinator.stats["coordination_conflicts"] > initial_conflicts
        
        # 验证返回了保守决策
        assert result is not None
        assert result.primary_brain == "coordinator_conflict_resolution"
        
        # 验证保守策略逻辑
        # 由于有买卖冲突，应该选择持有策略
        assert result.action in ["hold", "reduce"]  # 保守策略
        
        # 验证置信度被降低（平均值*0.6）
        expected_avg_confidence = (0.75 + 0.74 + 0.73) / 3 * 0.6
        assert abs(result.confidence - expected_avg_confidence) < 0.01
        
        # 验证支持数据包含冲突信息
        assert result.supporting_data["conflict_resolution"] is True
        assert len(result.supporting_data["conflicting_decisions"]) == 3

    @pytest.mark.asyncio
    async def test_comprehensive_coverage_scenario(self, coordinator):
        """综合测试场景 - 确保覆盖所有边界情况"""
        
        # 1. 测试Scholar异常处理
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=RuntimeError("Network error"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        # 这应该触发273-274行的异常处理
        result1 = await coordinator._request_decision_direct(
            {"topic": "test"}, "scholar", "correlation_1"
        )
        assert result1 is None  # 异常导致返回None
        
        # 2. 测试批量决策异常
        async def failing_request_decision(context, brain):
            if "fail" in context:
                raise ValueError("Simulated failure")
            return BrainDecision(
                decision_id="success",
                primary_brain=brain,
                action="hold",
                confidence=0.5,
                reasoning="Success",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="success"
            )
        
        coordinator.request_decision = AsyncMock(side_effect=failing_request_decision)
        
        # 这应该触发457-461行的异常处理
        batch_requests = [
            ({"normal": True}, "soldier"),
            ({"fail": True}, "commander"),  # 这个会失败
        ]
        
        results = await coordinator.request_decisions_batch(batch_requests)
        assert len(results) == 2
        assert results[0].decision_id == "success"
        assert "fallback" in results[1].decision_id
        
        # 3. 测试冲突检测的完整路径
        conflict_decisions = [
            BrainDecision(
                decision_id="d1", primary_brain="soldier", action="buy",
                confidence=0.80, reasoning="Buy signal", supporting_data={},
                timestamp=datetime.now(), correlation_id="c1"
            ),
            BrainDecision(
                decision_id="d2", primary_brain="commander", action="sell", 
                confidence=0.79, reasoning="Sell signal", supporting_data={},
                timestamp=datetime.now(), correlation_id="c2"
            )
        ]
        
        # 这应该触发792->815行的冲突检测逻辑
        conflict_result = await coordinator.resolve_conflicts(conflict_decisions)
        
        # 验证冲突被正确处理
        assert conflict_result.primary_brain == "coordinator_conflict_resolution"
        assert conflict_result.supporting_data["conflict_resolution"] is True

    @pytest.mark.asyncio
    async def test_edge_cases_for_complete_coverage(self, coordinator):
        """边界情况测试 - 确保100%覆盖率"""
        
        # 测试空的冲突决策列表（虽然这个在其他地方可能已经测试过）
        empty_result = await coordinator.resolve_conflicts([])
        assert "fallback" in empty_result.decision_id
        
        # 测试单个决策（无冲突）
        single_decision = [BrainDecision(
            decision_id="single", primary_brain="soldier", action="buy",
            confidence=0.9, reasoning="Single", supporting_data={},
            timestamp=datetime.now(), correlation_id="single"
        )]
        
        single_result = await coordinator.resolve_conflicts(single_decision)
        assert single_result == single_decision[0]  # 应该直接返回
        
        # 测试高置信度决策（>0.8）
        high_conf_decisions = [
            BrainDecision(
                decision_id="high", primary_brain="soldier", action="buy",
                confidence=0.85, reasoning="High confidence", supporting_data={},
                timestamp=datetime.now(), correlation_id="high"
            ),
            BrainDecision(
                decision_id="low", primary_brain="commander", action="sell",
                confidence=0.60, reasoning="Low confidence", supporting_data={},
                timestamp=datetime.now(), correlation_id="low"
            )
        ]
        
        high_conf_result = await coordinator.resolve_conflicts(high_conf_decisions)
        # 高置信度决策应该被直接采用
        assert high_conf_result.decision_id == "high"
        assert high_conf_result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_specific_line_coverage_verification(self, coordinator):
        """专门验证特定行的覆盖情况"""
        
        # 确保Scholar异常处理路径被覆盖（273-274行）
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=ConnectionError("Connection failed"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        # 直接调用_request_decision_direct来触发异常处理
        with patch.object(coordinator.event_bus, 'publish', AsyncMock(side_effect=Exception("Event publish failed"))):
            result = await coordinator._request_decision_direct(
                {"test": "data"}, "scholar", "test_id"
            )
            # 异常处理应该返回None
            assert result is None
        
        # 确保批量决策异常处理被覆盖（457-461行）
        def create_failing_request(fail_index):
            async def mock_request(context, brain):
                if context.get("index") == fail_index:
                    raise RuntimeError(f"Request {fail_index} failed")
                return BrainDecision(
                    decision_id=f"success_{context.get('index')}",
                    primary_brain=brain, action="hold", confidence=0.5,
                    reasoning="Success", supporting_data={},
                    timestamp=datetime.now(), correlation_id=f"corr_{context.get('index')}"
                )
            return mock_request
        
        coordinator.request_decision = AsyncMock(side_effect=create_failing_request(1))
        
        batch_requests = [
            ({"index": 0}, "soldier"),
            ({"index": 1}, "commander"),  # 这个会失败
            ({"index": 2}, "scholar")
        ]
        
        batch_results = await coordinator.request_decisions_batch(batch_requests)
        
        # 验证异常处理生成了备用决策
        assert len(batch_results) == 3
        assert batch_results[0].decision_id == "success_0"
        assert "fallback" in batch_results[1].decision_id  # 失败的请求
        assert batch_results[2].decision_id == "success_2"
        
        # 确保冲突检测路径被覆盖（792->815行）
        # 创建置信度非常接近的决策来触发冲突检测
        very_close_decisions = [
            BrainDecision(
                decision_id="close1", primary_brain="soldier", action="buy",
                confidence=0.7500, reasoning="Very close 1", supporting_data={},
                timestamp=datetime.now(), correlation_id="close1"
            ),
            BrainDecision(
                decision_id="close2", primary_brain="commander", action="sell",
                confidence=0.7499, reasoning="Very close 2", supporting_data={},  # 差异0.0001 < 0.1
                timestamp=datetime.now(), correlation_id="close2"
            )
        ]
        
        initial_conflicts = coordinator.stats.get("coordination_conflicts", 0)
        close_result = await coordinator.resolve_conflicts(very_close_decisions)
        
        # 验证冲突被检测到
        assert coordinator.stats["coordination_conflicts"] > initial_conflicts
        assert close_result.primary_brain == "coordinator_conflict_resolution"
        assert close_result.supporting_data["conflict_resolution"] is True


class TestSpecificLineCoverage:
    """专门针对特定行号的覆盖测试"""

    @pytest.fixture
    def coordinator(self):
        """创建基础协调器"""
        event_bus = MagicMock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        container = MagicMock(spec=DIContainer)
        return AIBrainCoordinator(event_bus, container)

    @pytest.mark.asyncio
    async def test_lines_273_274_scholar_exception(self, coordinator):
        """专门测试273-274行：Scholar直接调用异常处理"""
        # 设置Scholar但让其抛出异常
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(side_effect=TimeoutError("Scholar timeout"))
        coordinator.scholar = mock_scholar
        coordinator.enable_batch_processing = False
        
        # 调用应该触发异常处理
        result = await coordinator._request_decision_direct(
            {"query": "test"}, "scholar", "test_correlation"
        )
        
        # 验证异常被捕获，方法返回None（回退到事件模式）
        assert result is None
        mock_scholar.research.assert_called_once()

    @pytest.mark.asyncio
    async def test_lines_457_461_batch_exception(self, coordinator):
        """专门测试457-461行：批量决策异常处理"""
        # Mock request_decision让某些请求失败
        async def selective_failure(context, brain):
            if context.get("should_fail"):
                raise Exception("Intentional failure")
            return BrainDecision(
                decision_id="success", primary_brain=brain, action="hold",
                confidence=0.5, reasoning="OK", supporting_data={},
                timestamp=datetime.now(), correlation_id="ok"
            )
        
        coordinator.request_decision = AsyncMock(side_effect=selective_failure)
        
        # 创建包含失败请求的批次
        requests = [
            ({"should_fail": False}, "soldier"),
            ({"should_fail": True}, "commander"),  # 这个会失败
        ]
        
        results = await coordinator.request_decisions_batch(requests)
        
        # 验证异常处理生成了备用决策
        assert len(results) == 2
        assert results[0].decision_id == "success"
        assert "fallback" in results[1].decision_id

    @pytest.mark.asyncio
    async def test_lines_792_815_conflict_detection(self, coordinator):
        """专门测试792->815行：冲突检测逻辑"""
        # 创建置信度差异小于0.1的决策来触发冲突检测
        decisions = [
            BrainDecision(
                decision_id="d1", primary_brain="soldier", action="buy",
                confidence=0.750, reasoning="Buy", supporting_data={},
                timestamp=datetime.now(), correlation_id="d1"
            ),
            BrainDecision(
                decision_id="d2", primary_brain="commander", action="sell",
                confidence=0.751, reasoning="Sell", supporting_data={},  # 差异0.001 < 0.1
                timestamp=datetime.now(), correlation_id="d2"
            )
        ]
        
        initial_conflicts = coordinator.stats.get("coordination_conflicts", 0)
        
        # 执行冲突解决
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证冲突检测逻辑被触发
        assert coordinator.stats["coordination_conflicts"] > initial_conflicts
        assert result.primary_brain == "coordinator_conflict_resolution"
        
        # 验证保守决策生成
        assert result.supporting_data["conflict_resolution"] is True
        assert "conflicting_decisions" in result.supporting_data
        assert len(result.supporting_data["conflicting_decisions"]) == 2