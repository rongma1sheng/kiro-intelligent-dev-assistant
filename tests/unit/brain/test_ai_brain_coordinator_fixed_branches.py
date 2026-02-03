#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 修复版分支测试

专门针对5个缺失分支进行精确测试覆盖:
- [276, 277]: Commander异常处理分支
- [422, -388]: 批处理项目异常处理分支(future未完成)
- [539, 542]: 脑决策处理异常分支
- [559, -547]: 分析完成处理异常分支
- [792, 815]: 冲突解决单一决策分支
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorFixedBranches:
    """AI大脑协调器修复版分支测试"""

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
    async def test_branch_276_277_commander_exception_direct_call(self, coordinator):
        """测试分支[276, 277] - Commander直接调用异常，触发warning日志"""
        await coordinator.initialize()
        
        # 确保commander存在但会抛出异常
        coordinator.commander.analyze = AsyncMock(side_effect=Exception("Commander分析失败"))
        
        context = {"symbol": "000001.SZ", "action": "analyze"}
        correlation_id = "test_commander_exception"
        
        # 直接调用_request_decision_direct方法，确保走commander分支
        result = await coordinator._request_decision_direct(context, "commander", correlation_id)
        
        # 验证异常被捕获，返回None（第277行的warning应该被触发）
        assert result is None
        
        # 验证commander.analyze被调用了
        coordinator.commander.analyze.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_branch_422_388_batch_processing_exception_future_not_done(self, coordinator):
        """测试分支[422, -388] - 批处理异常，future未完成时设置异常"""
        # 创建一个未完成的Future
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_exception"
        
        # 确保Future未完成
        assert not future.done()
        
        # Mock event_bus.publish抛出异常，触发第422行的异常处理
        test_exception = Exception("Event bus publish failed")
        coordinator.event_bus.publish = AsyncMock(side_effect=test_exception)
        
        # 调用_process_batch_item，这会触发异常处理
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future被设置为异常状态（触发了第422行的if not future.done()分支）
        assert future.done()
        assert future.exception() == test_exception

    @pytest.mark.asyncio
    async def test_branch_539_542_handle_brain_decision_exception(self, coordinator):
        """测试分支[539, 542] - 处理脑决策时异常"""
        # 创建一个会导致处理异常的事件（data为None）
        invalid_event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data=None  # 这会导致data.get()调用失败
        )
        
        # 调用_handle_brain_decision，会在第539行触发异常
        await coordinator._handle_brain_decision(invalid_event)
        
        # 异常应该被捕获，不会抛出到外部
        # 这个测试主要是确保异常处理分支被执行

    @pytest.mark.asyncio
    async def test_branch_559_547_handle_analysis_completed_exception(self, coordinator):
        """测试分支[559, -547] - 处理分析完成时异常"""
        # 创建一个会导致处理异常的事件
        invalid_event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=None  # 这会导致data.get()调用失败
        )
        
        # 调用_handle_analysis_completed，会在第559行触发异常
        await coordinator._handle_analysis_completed(invalid_event)
        
        # 异常应该被捕获，不会抛出到外部
        # 这个测试主要是确保异常处理分支被执行

    @pytest.mark.asyncio
    async def test_branch_792_815_resolve_conflicts_no_conflict_single_decision(self, coordinator):
        """测试分支[792, 815] - 无冲突情况，返回最高优先级决策"""
        await coordinator.initialize()
        
        # 创建两个决策，置信度差异大于0.1，不会触发冲突处理
        decision1 = BrainDecision(
            decision_id="high_priority_decision",
            primary_brain="soldier",  # soldier优先级最高
            action="buy",
            confidence=0.7,  # 不是高置信度(<=0.8)
            reasoning="高优先级决策",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_no_conflict"
        )
        
        decision2 = BrainDecision(
            decision_id="low_priority_decision", 
            primary_brain="commander",  # commander优先级较低
            action="sell",
            confidence=0.4,  # 置信度差异0.3 > 0.1，不触发冲突
            reasoning="低优先级决策",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_no_conflict_2"
        )
        
        # 调用resolve_conflicts，应该走到第815行的info日志
        result = await coordinator.resolve_conflicts([decision1, decision2])
        
        # 验证返回高优先级决策（soldier优先级高于commander）
        assert result == decision1
        assert result.action == "buy"
        assert result.primary_brain == "soldier"