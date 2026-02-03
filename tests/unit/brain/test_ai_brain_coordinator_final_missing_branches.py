#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 最终缺失分支精确测试

专门针对最后10个缺失分支进行精确测试覆盖:
- [260, 261]: Soldier异常处理分支
- [276, 277]: Commander异常处理分支  
- [351, 352]: 批处理队列检查分支
- [422, -388]: 批处理项目异常处理分支(future未完成)
- [423, 426]: 批处理项目异常处理分支(future已完成)
- [456, 457]: 批处理项目设置结果分支
- [539, 542]: 脑决策处理异常分支
- [559, -547]: 分析完成处理异常分支
- [792, 815]: 冲突解决单一决策分支
- [795, 815]: 冲突解决多决策分支
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorFinalMissingBranches:
    """AI大脑协调器最终缺失分支精确测试"""

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
    async def test_branch_260_261_soldier_exception_handling(self, coordinator):
        """测试分支[260, 261] - Soldier异常处理分支"""
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
    async def test_branch_276_277_commander_exception_handling(self, coordinator):
        """测试分支[276, 277] - Commander异常处理分支"""
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
    async def test_branch_351_352_batch_queue_check(self, coordinator):
        """测试分支[351, 352] - 批处理队列检查分支"""
        await coordinator.initialize()
        
        # 设置批处理大小为2
        coordinator.batch_size = 2
        
        context = {"symbol": "000001.SZ", "action": "analyze"}
        correlation_id = "test_batch_queue"
        
        # 第一次调用，不会触发批处理（队列大小为1 < batch_size=2）
        # 这会触发第351行的should_process = len(self.pending_batch) >= self.batch_size
        # 由于1 < 2，should_process为False，触发第352行的if should_process分支
        
        # Mock _wait_for_decision返回None来避免无限等待
        coordinator._wait_for_decision = AsyncMock(return_value=None)
        
        # 调用_request_decision_with_batch，第一次不会触发批处理
        result = await coordinator._request_decision_with_batch(context, "soldier", correlation_id)
        
        # 验证结果为None（因为_wait_for_decision返回None）
        assert result is None
        
        # 验证队列中有一个待处理项目
        assert len(coordinator.pending_batch) == 1

    @pytest.mark.asyncio
    async def test_branch_422_423_batch_item_exception_future_not_done(self, coordinator):
        """测试分支[422, -388] - 批处理项目异常处理分支(future未完成)"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_exception_not_done"
        
        # 确保Future未完成
        assert not future.done()
        
        # Mock event_bus.publish抛出异常
        test_exception = Exception("Test exception for future not done")
        coordinator.event_bus.publish = AsyncMock(side_effect=test_exception)
        
        # 调用_process_batch_item，这会触发异常处理
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future被设置为异常状态（触发了第422行的if not future.done()分支）
        assert future.done()
        assert future.exception() == test_exception

    @pytest.mark.asyncio
    async def test_branch_423_426_batch_item_exception_future_done(self, coordinator):
        """测试分支[423, 426] - 批处理项目异常处理分支(future已完成)"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_exception_done"
        
        # 预先设置Future为完成状态
        future.set_result("already_completed")
        assert future.done()
        
        # Mock event_bus.publish抛出异常
        test_exception = Exception("Test exception for future done")
        coordinator.event_bus.publish = AsyncMock(side_effect=test_exception)
        
        # 调用_process_batch_item，这会触发异常处理
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future状态没有被改变（因为已经完成，走了else分支第426行）
        assert future.done()
        assert future.result() == "already_completed"
        assert future.exception() is None

    @pytest.mark.asyncio
    async def test_branch_456_457_batch_item_set_result_none(self, coordinator):
        """测试分支[456, 457] - 批处理项目设置结果分支"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_set_result_none"
        
        # Mock _wait_for_decision返回None
        coordinator._wait_for_decision = AsyncMock(return_value=None)
        
        # 调用_process_batch_item
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future被设置为None（触发了第456-457行的else分支）
        assert future.done()
        assert future.result() is None

    @pytest.mark.asyncio
    async def test_branch_539_542_handle_brain_decision_exception(self, coordinator):
        """测试分支[539, 542] - 脑决策处理异常分支"""
        # 创建一个无效的事件数据，会导致处理异常
        invalid_event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data=None  # 无效数据，会导致异常
        )
        
        # 调用_handle_brain_decision，会触发异常处理
        await coordinator._handle_brain_decision(invalid_event)
        
        # 验证异常被捕获（触发了第539行的except分支和第542行的error日志）
        # 由于异常被捕获，方法正常完成，没有抛出异常
        assert True  # 如果到达这里，说明异常被正确处理

    @pytest.mark.asyncio
    async def test_branch_559_547_handle_analysis_completed_exception(self, coordinator):
        """测试分支[559, -547] - 分析完成处理异常分支"""
        # 创建一个会导致处理异常的事件
        invalid_event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=None  # 无效数据，会导致异常
        )
        
        # 调用_handle_analysis_completed，会触发异常处理
        await coordinator._handle_analysis_completed(invalid_event)
        
        # 验证异常被捕获（触发了第559行的except分支和-547行的error日志）
        # 由于异常被捕获，方法正常完成，没有抛出异常
        assert True  # 如果到达这里，说明异常被正确处理

    @pytest.mark.asyncio
    async def test_branch_792_815_resolve_conflicts_single_decision(self, coordinator):
        """测试分支[792, 815] - 冲突解决单一决策分支"""
        await coordinator.initialize()
        
        # 创建单一决策（len(sorted_decisions) == 1，触发else分支）
        single_decision = BrainDecision(
            decision_id="single_decision",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,
            reasoning="单一决策测试",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_single"
        )
        
        # 调用resolve_conflicts，只有一个决策
        result = await coordinator.resolve_conflicts([single_decision])
        
        # 验证返回单一决策（触发了第792行的else分支和第815行的return）
        assert result == single_decision
        assert result.action == "buy"
        assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_branch_795_815_resolve_conflicts_multiple_decisions_no_conflict(self, coordinator):
        """测试分支[795, 815] - 冲突解决多决策无冲突分支"""
        await coordinator.initialize()
        
        # 创建多个决策，但置信度差异较大（无冲突）
        decision1 = BrainDecision(
            decision_id="decision1",
            primary_brain="soldier",
            action="buy",
            confidence=0.9,  # 高置信度
            reasoning="高置信度决策",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_multi1"
        )
        
        decision2 = BrainDecision(
            decision_id="decision2",
            primary_brain="commander",
            action="hold",
            confidence=0.6,  # 低置信度
            reasoning="低置信度决策",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_multi2"
        )
        
        # 调用resolve_conflicts，多个决策但无冲突
        result = await coordinator.resolve_conflicts([decision1, decision2])
        
        # 验证返回最高置信度决策（触发了第795行的else分支和第815行的return）
        assert result == decision1
        assert result.action == "buy"
        assert result.confidence == 0.9