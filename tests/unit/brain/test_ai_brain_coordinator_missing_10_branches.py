#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 缺失10个分支的精确测试

专门针对以下10个缺失分支进行精确测试覆盖:
- [260, 261]: 第260行的if分支
- [276, 277]: 第276行的if分支  
- [351, 352]: 第351行的if分支
- [422, -388]: 第422行的异常处理分支
- [423, 426]: 第423行的if分支
- [456, 457]: 第456行的if分支
- [539, 542]: 第539行的if分支
- [559, -547]: 第559行的异常处理分支
- [792, 815]: 第792行的if分支
- [795, 815]: 第795行的if分支
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorMissing10Branches:
    """AI大脑协调器缺失10个分支的精确测试"""

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
        
        # Mock AI引擎实例
        mock_soldier = AsyncMock(spec=ISoldierEngine)
        mock_soldier.decide = AsyncMock(return_value={
            'decision': {'action': 'buy', 'confidence': 0.8, 'reasoning': 'test'},
            'metadata': {}
        })
        
        mock_commander = AsyncMock(spec=ICommanderEngine)
        mock_commander.analyze = AsyncMock(return_value={
            'recommendation': 'buy', 'confidence': 0.7, 'analysis': 'test'
        })
        
        mock_scholar = AsyncMock(spec=IScholarEngine)
        mock_scholar.research = AsyncMock(return_value={
            'recommendation': 'buy', 'confidence': 0.75, 'research_summary': 'test'
        })
        
        container.resolve = MagicMock(side_effect=lambda interface: {
            ISoldierEngine: mock_soldier,
            ICommanderEngine: mock_commander,
            IScholarEngine: mock_scholar
        }.get(interface))
        
        return container

    @pytest.fixture
    def coordinator(self, mock_event_bus, mock_container):
        """创建协调器实例"""
        return AIBrainCoordinator(mock_event_bus, mock_container)

    @pytest.mark.asyncio
    async def test_branch_260_261_soldier_exception_fallback(self, coordinator):
        """测试分支[260, 261] - Soldier异常时的回退逻辑"""
        await coordinator.initialize()
        
        # Mock soldier抛出异常，触发第260行的except分支
        coordinator.soldier.decide = AsyncMock(side_effect=Exception("Soldier决策失败"))
        
        context = {"symbol": "000001.SZ", "action": "analyze"}
        correlation_id = "test_soldier_exception"
        
        # 调用_request_decision_direct，会触发soldier异常处理
        result = await coordinator._request_decision_direct(context, "soldier", correlation_id)
        
        # 验证异常被捕获，返回None（触发了第261行的warning日志）
        assert result is None

    @pytest.mark.asyncio
    async def test_branch_276_277_commander_exception_fallback(self, coordinator):
        """测试分支[276, 277] - Commander异常时的回退逻辑"""
        await coordinator.initialize()
        
        # Mock commander抛出异常，触发第276行的except分支
        coordinator.commander.analyze = AsyncMock(side_effect=Exception("Commander分析失败"))
        
        context = {"symbol": "000001.SZ", "action": "analyze"}
        correlation_id = "test_commander_exception"
        
        # 调用_request_decision_direct，会触发commander异常处理
        result = await coordinator._request_decision_direct(context, "commander", correlation_id)
        
        # 验证异常被捕获，返回None（触发了第277行的warning日志）
        assert result is None

    @pytest.mark.asyncio
    async def test_branch_351_352_batch_processing_trigger(self, coordinator):
        """测试分支[351, 352] - 批处理触发条件"""
        await coordinator.initialize()
        
        # 设置批处理大小为2，确保能触发批处理
        coordinator.batch_size = 2
        
        context1 = {"symbol": "000001.SZ"}
        context2 = {"symbol": "000002.SZ"}
        
        # 第一个请求不会触发批处理
        future1 = asyncio.Future()
        coordinator.pending_batch.append((context1, "soldier", "test1", future1))
        
        # 第二个请求会触发批处理（len(pending_batch) >= batch_size）
        # 这会触发第351行的should_process = True
        with patch.object(coordinator, '_process_batch', new_callable=AsyncMock) as mock_process:
            await coordinator._request_decision_with_batch(context2, "soldier", "test_batch_trigger")
            
            # 验证批处理被触发（第352行的if should_process分支）
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_branch_422_388_process_batch_item_exception_future_done(self, coordinator):
        """测试分支[422, -388] - 批处理项目异常且Future已完成"""
        await coordinator.initialize()
        
        # 创建已完成的Future
        future = asyncio.Future()
        future.set_result("already_done")
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_exception_done"
        
        # Mock事件发布抛出异常，触发第422行的except分支
        coordinator.event_bus.publish = AsyncMock(side_effect=Exception("Event publish failed"))
        
        # 调用_process_batch_item，会触发异常处理
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future状态保持不变（因为已完成，走了else分支到-388行）
        assert future.done() == True
        assert future.result() == "already_done"

    @pytest.mark.asyncio
    async def test_branch_423_426_process_batch_item_exception_future_not_done(self, coordinator):
        """测试分支[423, 426] - 批处理项目异常且Future未完成"""
        await coordinator.initialize()
        
        # 创建未完成的Future
        future = asyncio.Future()
        assert future.done() == False
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_exception_not_done"
        
        # Mock事件发布抛出异常，触发第422行的except分支
        test_exception = Exception("Event publish failed")
        coordinator.event_bus.publish = AsyncMock(side_effect=test_exception)
        
        # 调用_process_batch_item，会触发异常处理
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future被设置了异常（第423-426行的if分支）
        assert future.done() == True
        assert future.exception() is not None
        assert isinstance(future.exception(), Exception)

    @pytest.mark.asyncio
    async def test_branch_456_457_batch_request_exception_handling(self, coordinator):
        """测试分支[456, 457] - 批量请求异常处理"""
        await coordinator.initialize()
        
        # 创建会抛出异常的请求
        def failing_request(context, brain):
            raise Exception(f"Request failed for {brain}")
        
        # Mock request_decision方法抛出异常
        coordinator.request_decision = AsyncMock(side_effect=failing_request)
        
        requests = [
            ({"symbol": "000001.SZ"}, "soldier"),
            ({"symbol": "000002.SZ"}, "commander")
        ]
        
        # 调用批量请求，会触发异常处理
        results = await coordinator.request_decisions_batch(requests)
        
        # 验证异常被处理，生成了备用决策（第456-457行的if分支）
        assert len(results) == 2
        for result in results:
            assert isinstance(result, BrainDecision)
            assert "fallback" in result.decision_id or "batch_error" in result.decision_id

    @pytest.mark.asyncio
    async def test_branch_539_542_handle_brain_decision_with_correlation_id(self, coordinator):
        """测试分支[539, 542] - 处理带correlation_id的大脑决策"""
        await coordinator.initialize()
        
        # 创建带correlation_id的事件
        event_data = {
            "action": "decision_result",  # 必须设置这个字段才能触发决策处理
            "decision_id": "test_decision",
            "primary_brain": "soldier",
            "decision_action": "buy",  # 注意这里是decision_action，不是action
            "confidence": 0.8,
            "reasoning": "test reasoning",
            "supporting_data": {"test": "data"},
            "correlation_id": "test_correlation_123"  # 有correlation_id，触发第539行的if分支
        }
        
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=event_data
        )
        
        # 调用事件处理方法
        await coordinator._handle_brain_decision(event)
        
        # 验证决策被存储到pending_decisions中（第542行）
        correlation_id = event_data["correlation_id"]
        assert correlation_id in coordinator.pending_decisions
        stored_decision = coordinator.pending_decisions[correlation_id]
        assert stored_decision.action == "buy"
        assert stored_decision.confidence == 0.8

    @pytest.mark.asyncio
    async def test_branch_559_547_handle_analysis_completed_exception(self, coordinator):
        """测试分支[559, -547] - 处理分析完成事件异常"""
        await coordinator.initialize()
        
        # Mock _trigger_strategy_adjustment抛出异常
        coordinator._trigger_strategy_adjustment = AsyncMock(side_effect=Exception("Strategy adjustment failed"))
        
        # 创建市场分析完成事件
        event_data = {
            "analysis_type": "market_analysis",
            "result": {"trend": "bullish"}
        }
        
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=event_data
        )
        
        # 调用事件处理方法，会触发异常处理（第559行的except分支）
        await coordinator._handle_analysis_completed(event)
        
        # 验证异常被捕获并记录（跳转到-547行的日志记录）
        # 方法应该正常完成，不抛出异常
        assert True  # 如果到达这里，说明异常被正确处理

    @pytest.mark.asyncio
    async def test_branch_792_815_resolve_conflicts_multiple_decisions(self, coordinator):
        """测试分支[792, 815] - 多个决策的冲突解决"""
        await coordinator.initialize()
        
        # 创建多个置信度相近的决策，触发冲突检测
        decision1 = BrainDecision(
            decision_id="decision1",
            primary_brain="soldier",
            action="buy",
            confidence=0.65,  # 置信度相近
            reasoning="soldier reasoning",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test1"
        )
        
        decision2 = BrainDecision(
            decision_id="decision2", 
            primary_brain="commander",
            action="sell",
            confidence=0.66,  # 置信度差异 < 0.1，触发冲突
            reasoning="commander reasoning",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test2"
        )
        
        decisions = [decision1, decision2]
        
        # Mock _create_conservative_decision
        conservative_decision = BrainDecision(
            decision_id="conservative",
            primary_brain="coordinator",
            action="hold",
            confidence=0.5,
            reasoning="conservative strategy",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="conservative"
        )
        coordinator._create_conservative_decision = MagicMock(return_value=conservative_decision)
        
        # 调用冲突解决，会触发第792行的if分支（len(sorted_decisions) > 1）
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证返回了保守决策（第815行）
        assert result == conservative_decision
        assert coordinator.stats["coordination_conflicts"] >= 1

    @pytest.mark.asyncio
    async def test_branch_795_815_resolve_conflicts_confidence_diff_check(self, coordinator):
        """测试分支[795, 815] - 置信度差异检查分支"""
        await coordinator.initialize()
        
        # 创建置信度差异大于0.1的决策，确保不触发冲突
        decision1 = BrainDecision(
            decision_id="decision1",
            primary_brain="soldier", 
            action="buy",
            confidence=0.80,  # 高置信度
            reasoning="soldier reasoning",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test1"
        )
        
        decision2 = BrainDecision(
            decision_id="decision2",
            primary_brain="commander",
            action="sell", 
            confidence=0.60,  # 置信度差异 = 0.2，大于0.1，不触发冲突
            reasoning="commander reasoning",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test2"
        )
        
        decisions = [decision1, decision2]
        
        # 调用冲突解决
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证返回了最高置信度的决策（第795行的if条件不满足，跳到815行）
        assert result == decision1  # 置信度更高的决策
        assert result.confidence == 0.80
        assert result.action == "buy"
        
        # 验证没有增加冲突计数（因为置信度差异大于0.1）
        assert coordinator.stats.get("coordination_conflicts", 0) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])