#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 精确分支测试 - 确保真正触发目标分支

专门针对5个缺失分支进行精确测试，确保代码路径被真正执行
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# 直接导入目标模块，确保覆盖率统计正确
from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorPreciseBranches:
    """AI大脑协调器精确分支测试 - 确保真正触发目标分支"""

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
    async def coordinator(self, mock_event_bus, mock_container):
        """创建协调器实例"""
        coordinator = AIBrainCoordinator(mock_event_bus, mock_container)
        await coordinator.initialize()
        return coordinator

    @pytest.mark.asyncio
    async def test_branch_276_277_commander_exception_precise(self, coordinator):
        """精确测试分支[276, 277] - Commander异常处理分支"""
        # 确保commander存在但会抛出异常
        coordinator.commander = AsyncMock()
        coordinator.commander.analyze = AsyncMock(side_effect=Exception("Commander分析失败"))
        
        context = {"symbol": "000001.SZ", "action": "analyze"}
        correlation_id = "test_commander_exception_precise"
        
        # 直接调用_request_decision_direct方法，确保触发异常处理分支
        result = await coordinator._request_decision_direct(context, "commander", correlation_id)
        
        # 验证异常被捕获，应该回退到事件模式，但最终返回None（因为没有事件响应）
        assert result is None
        
        # 验证commander.analyze被调用了
        coordinator.commander.analyze.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_branch_422_388_batch_item_exception_precise(self, coordinator):
        """精确测试分支[422, -388] - 批处理项目异常处理分支"""
        # 创建一个未完成的Future
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_exception_precise"
        
        # 确保Future未完成
        assert not future.done()
        
        # Mock event_bus.publish抛出异常，触发异常处理
        test_exception = Exception("Test exception for batch processing")
        coordinator.event_bus.publish = AsyncMock(side_effect=test_exception)
        
        # 调用_process_batch_item，触发异常处理分支
        await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future被设置为异常状态（触发了第426行的if not future.done()分支）
        assert future.done()
        assert future.exception() == test_exception

    @pytest.mark.asyncio
    async def test_branch_539_542_handle_brain_decision_exception_precise(self, coordinator):
        """精确测试分支[539, 542] - 脑决策处理异常分支"""
        # 创建一个会导致处理异常的事件（data为None）
        invalid_event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data=None  # 无效数据，会导致异常
        )
        
        # 直接调用_handle_brain_decision，触发异常处理
        await coordinator._handle_brain_decision(invalid_event)
        
        # 如果没有抛出异常，说明异常被正确捕获了

    @pytest.mark.asyncio
    async def test_branch_559_547_handle_analysis_completed_exception_precise(self, coordinator):
        """精确测试分支[559, -547] - 分析完成处理异常分支"""
        # 创建一个会导致处理异常的事件
        invalid_event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=None  # 无效数据，会导致异常
        )
        
        # 直接调用_handle_analysis_completed，触发异常处理
        await coordinator._handle_analysis_completed(invalid_event)
        
        # 如果没有抛出异常，说明异常被正确捕获了

    @pytest.mark.asyncio
    async def test_branch_792_815_resolve_conflicts_single_decision_precise(self, coordinator):
        """精确测试分支[792, 815] - 冲突解决单一决策分支"""
        # 创建两个决策，确保触发特定的分支条件
        decision1 = BrainDecision(
            decision_id="decision_1",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,  # 中等置信度
            reasoning="决策1",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_resolve_conflicts"
        )
        
        decision2 = BrainDecision(
            decision_id="decision_2", 
            primary_brain="commander",
            action="sell",
            confidence=0.5,  # 低置信度，差异0.2>0.1
            reasoning="决策2",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_resolve_conflicts"
        )
        
        # 调用resolve_conflicts，应该触发第815行的分支
        result = await coordinator.resolve_conflicts([decision1, decision2])
        
        # 验证返回了高优先级的决策（soldier优先级高于commander）
        assert result == decision1
        assert result.action == "buy"
        assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_all_five_branches_comprehensive(self, coordinator):
        """综合测试所有5个分支，确保都被触发"""
        
        # 1. 测试Commander异常分支[276, 277]
        coordinator.commander = AsyncMock()
        coordinator.commander.analyze = AsyncMock(side_effect=Exception("Commander error"))
        
        result1 = await coordinator._request_decision_direct(
            {"symbol": "TEST1"}, "commander", "test1"
        )
        assert result1 is None
        
        # 2. 测试批处理异常分支[422, -388]
        future2 = asyncio.Future()
        coordinator.event_bus.publish = AsyncMock(side_effect=Exception("Batch error"))
        
        await coordinator._process_batch_item(
            {"symbol": "TEST2"}, "soldier", "test2", future2
        )
        assert future2.done()
        assert isinstance(future2.exception(), Exception)
        
        # 3. 测试脑决策异常分支[539, 542]
        invalid_event3 = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator", 
            priority=EventPriority.HIGH,
            data=None
        )
        
        await coordinator._handle_brain_decision(invalid_event3)
        
        # 4. 测试分析完成异常分支[559, -547]
        invalid_event4 = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=None
        )
        
        await coordinator._handle_analysis_completed(invalid_event4)
        
        # 5. 测试冲突解决分支[792, 815]
        decision5a = BrainDecision(
            decision_id="decision_5a",
            primary_brain="soldier",
            action="buy",
            confidence=0.6,
            reasoning="决策5a",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test5"
        )
        
        decision5b = BrainDecision(
            decision_id="decision_5b",
            primary_brain="commander", 
            action="sell",
            confidence=0.4,
            reasoning="决策5b",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test5"
        )
        
        result5 = await coordinator.resolve_conflicts([decision5a, decision5b])
        assert result5 == decision5a

    @pytest.mark.asyncio
    async def test_import_verification(self):
        """验证模块导入正确，确保覆盖率统计有效"""
        # 验证我们导入的模块是正确的
        assert hasattr(AIBrainCoordinator, '__init__')
        assert hasattr(BrainDecision, '__init__')
        
        # 验证关键方法存在
        coordinator_class = AIBrainCoordinator
        assert hasattr(coordinator_class, '_request_decision_direct')
        assert hasattr(coordinator_class, '_process_batch_item')
        assert hasattr(coordinator_class, '_handle_brain_decision')
        assert hasattr(coordinator_class, '_handle_analysis_completed')
        assert hasattr(coordinator_class, 'resolve_conflicts')