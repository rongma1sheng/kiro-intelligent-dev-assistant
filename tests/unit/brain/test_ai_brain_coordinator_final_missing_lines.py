#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 最终缺失行覆盖测试

专门针对剩余的13行代码进行测试覆盖
Missing line numbers: [218, 219, 220, 223, 224, 226, 426, 457, 459, 460, 461, 585, 586]
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorFinalMissingLines:
    """AI大脑协调器最终缺失行覆盖测试"""

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
    async def test_request_decision_general_exception_with_error_stats(self, coordinator):
        """测试通用异常处理和错误统计 - 覆盖行218-220, 223-224, 226"""
        await coordinator.initialize()
        
        # 让所有AI脑都抛出异常
        coordinator.soldier.decide.side_effect = Exception("Soldier failed")
        coordinator.commander.analyze.side_effect = Exception("Commander failed")
        coordinator.scholar.research.side_effect = Exception("Scholar failed")
        
        context = {"symbol": "000001.SZ"}
        
        # 确保stats字典存在error_decisions键，并记录初始值
        coordinator.stats.setdefault("error_decisions", 0)
        initial_error_count = coordinator.stats["error_decisions"]
        
        # 模拟_request_decision_direct也抛出异常，这样会进入Exception处理分支
        with patch.object(coordinator, '_request_decision_direct', side_effect=Exception("Direct request failed")):
            result = await coordinator.request_decision(context, "soldier")
        
        # 验证返回了备用决策
        assert result is not None
        assert result.primary_brain.startswith("coordinator_fallback")
        assert result.action == "hold"
        assert "备用决策" in result.reasoning
        
        # 验证错误统计增加了1 - 异常处理中error_decisions会增加
        assert coordinator.stats["error_decisions"] == initial_error_count + 1

    @pytest.mark.asyncio
    async def test_process_batch_item_future_set_result_none(self, coordinator):
        """测试批处理项目设置None结果 - 覆盖行426"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_none"
        
        # Mock _request_decision_direct返回None
        with patch.object(coordinator, '_request_decision_direct', return_value=None):
            await coordinator._process_batch_item(context, "soldier", correlation_id, future)
        
        # 验证Future被设置为None
        assert future.done()
        assert future.result() is None

    @pytest.mark.asyncio
    async def test_request_decisions_batch_with_exceptions(self, coordinator):
        """测试批量决策请求异常处理 - 覆盖行457, 459-461"""
        await coordinator.initialize()
        
        # 准备请求列表
        requests = [
            ({"symbol": "000001.SZ"}, "soldier"),
            ({"symbol": "000002.SZ"}, "commander"),
            ({"symbol": "000003.SZ"}, "scholar")
        ]
        
        # 创建一个会抛出异常的mock函数
        async def mock_request_decision(context, primary_brain):
            if context.get("symbol") == "000002.SZ":
                raise Exception("Request failed for 000002.SZ")
            # 对于其他请求，返回正常的BrainDecision
            return BrainDecision(
                decision_id=f"test_{datetime.now().timestamp()}",
                primary_brain=primary_brain,
                action="buy",
                confidence=0.8,
                reasoning="test decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"test_{datetime.now().timestamp()}"
            )
        
        # Mock request_decision方法
        with patch.object(coordinator, 'request_decision', side_effect=mock_request_decision):
            results = await coordinator.request_decisions_batch(requests)
        
        # 验证结果
        assert len(results) == 3
        
        # 第一个和第三个应该成功
        assert results[0].action == "buy"
        assert results[2].action == "buy"
        
        # 第二个应该是备用决策（由于异常被gather捕获并处理）
        # 注意：备用决策的primary_brain格式是coordinator_fallback_{original_brain}
        assert results[1].primary_brain.startswith("coordinator_fallback")
        assert results[1].action == "hold"
        assert "备用决策" in results[1].reasoning

    @pytest.mark.asyncio
    async def test_handle_factor_discovered_exception(self, coordinator):
        """测试因子发现事件异常处理 - 覆盖行585-586"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data=None  # None数据会导致异常
        )
        
        # 应该不抛出异常，而是记录错误
        await coordinator._handle_factor_discovered(event)
        
        # 验证没有发布新事件（因为异常被捕获）
        coordinator.event_bus.publish.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])