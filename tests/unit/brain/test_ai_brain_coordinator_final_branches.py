#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 最终分支覆盖测试

专门针对最后2个缺失分支进行测试覆盖
Missing branches: [[430, -388], [792, 815]]
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorFinalBranches:
    """AI大脑协调器最终分支覆盖测试"""

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
    async def test_process_batch_item_exception_future_already_done(self, coordinator):
        """测试批处理项目异常时Future已完成的分支 - 覆盖分支[430, -388]"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_exception_done"
        
        # 预先设置Future为完成状态
        future.set_result("already_completed")
        assert future.done()
        
        # Mock _request_decision_direct抛出异常
        test_exception = Exception("Test exception")
        with patch.object(coordinator, '_request_decision_direct', side_effect=test_exception):
            await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future状态没有被改变（因为已经完成，不会设置异常）
        assert future.done()
        assert future.result() == "already_completed"  # 原来的结果保持不变
        assert future.exception() is None  # 没有异常被设置

    @pytest.mark.asyncio
    async def test_resolve_conflicts_multiple_decisions_large_confidence_diff(self, coordinator):
        """测试协调决策多个决策但置信度差异大的分支 - 覆盖分支[792, 815]"""
        await coordinator.initialize()
        
        # 创建多个决策，但置信度差异很大（>0.1）
        decision1 = BrainDecision(
            decision_id="high_confidence_decision",
            primary_brain="soldier",
            action="buy",
            confidence=0.9,  # 高置信度
            reasoning="high confidence decision",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_large_diff"
        )
        
        decision2 = BrainDecision(
            decision_id="low_confidence_decision",
            primary_brain="commander",
            action="sell",
            confidence=0.6,  # 低置信度，差异0.3 > 0.1
            reasoning="low confidence decision",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_large_diff"
        )
        
        decisions = [decision1, decision2]
        
        # 调用协调决策方法
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证返回的是高置信度决策（无冲突分支）
        assert result == decision1
        assert result.primary_brain == "soldier"
        assert result.action == "buy"
        assert result.confidence == 0.9
        
        # 验证统计信息没有增加冲突计数（因为置信度差异大，不算冲突）
        assert coordinator.stats.get("coordination_conflicts", 0) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])