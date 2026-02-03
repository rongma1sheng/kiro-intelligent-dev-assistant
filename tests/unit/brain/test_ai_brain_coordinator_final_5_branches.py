#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 最终5个缺失分支精确测试

专门针对最后5个缺失分支进行精确测试覆盖:
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


class TestAIBrainCoordinatorFinal5Branches:
    """AI大脑协调器最终5个缺失分支精确测试"""

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
    async def test_branch_276_277_commander_exception_warning(self, coordinator):
        """测试分支[276, 277] - Commander异常处理分支，确保触发warning日志"""
        await coordinator.initialize()
        
        # Mock commander抛出异常，触发第276行的except分支
        coordinator.commander.analyze = AsyncMock(side_effect=Exception("Commander分析失败"))
        
        context = {"symbol": "000001.SZ", "action": "analyze"}
        correlation_id = "test_commander_exception_warning"
        
        # 使用patch来捕获日志调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 调用_request_decision_direct，会触发commander异常处理
            result = await coordinator._request_decision_direct(context, "commander", correlation_id)
            
            # 验证异常被捕获，返回None（触发了第277行的warning日志）
            assert result is None
            
            # 验证warning日志被调用（可能被调用多次，包括超时警告）
            assert mock_logger.warning.call_count >= 1
            # 检查第一个warning调用是否包含预期内容
            first_warning_call = mock_logger.warning.call_args_list[0][0][0]
            assert "Commander直接调用失败" in first_warning_call
            assert "回退到事件模式" in first_warning_call

    @pytest.mark.asyncio
    async def test_branch_422_388_batch_item_exception_future_not_done(self, coordinator):
        """测试分支[422, -388] - 批处理项目异常处理分支(future未完成)"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_exception_not_done"
        
        # 确保Future未完成
        assert not future.done()
        
        # Mock event_bus.publish抛出异常
        test_exception = Exception("Test exception for future not done")
        coordinator.event_bus.publish = AsyncMock(side_effect=test_exception)
        
        # 使用patch来捕获日志调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 调用_process_batch_item，这会触发异常处理
            await coordinator._process_batch_item(context, "soldier", correlation_id, future)
            
            # 验证Future被设置为异常状态（触发了第422行的if not future.done()分支）
            assert future.done()
            assert future.exception() == test_exception
            
            # 验证error日志被调用
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            assert "批处理项目失败" in error_call
            assert correlation_id in error_call

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
        
        # 使用patch来捕获日志调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 调用_handle_brain_decision，会触发异常处理
            await coordinator._handle_brain_decision(invalid_event)
            
            # 验证异常被捕获（触发了第539行的except分支和第542行的error日志）
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            assert "Failed to handle brain decision" in error_call

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
        
        # 使用patch来捕获日志调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 调用_handle_analysis_completed，会触发异常处理
            await coordinator._handle_analysis_completed(invalid_event)
            
            # 验证异常被捕获（触发了第559行的except分支和-547行的error日志）
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args[0][0]
            assert "Failed to handle analysis completed" in error_call

    @pytest.mark.asyncio
    async def test_branch_792_815_resolve_conflicts_single_decision_return(self, coordinator):
        """测试分支[792, 815] - 冲突解决单一决策分支，确保返回单一决策"""
        await coordinator.initialize()
        
        # 创建两个决策，置信度都不高（<=0.8），且差异较大，触发第815行的无冲突分支
        decision1 = BrainDecision(
            decision_id="medium_confidence_decision",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,  # 中等置信度，不触发高置信度分支
            reasoning="中等置信度决策测试",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_medium_confidence"
        )
        
        decision2 = BrainDecision(
            decision_id="low_confidence_decision", 
            primary_brain="commander",
            action="sell",
            confidence=0.5,  # 低置信度，差异0.2>0.1，不触发冲突分支
            reasoning="低置信度决策测试",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_low_confidence"
        )
        
        # 使用patch来捕获日志调用
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 调用resolve_conflicts，置信度差异大且不高，触发第815行的info日志
            result = await coordinator.resolve_conflicts([decision1, decision2])
            
            # 验证返回高优先级决策（soldier优先级高于commander）
            assert result == decision1
            assert result.action == "buy"
            assert result.confidence == 0.7
            
            # 验证info日志被调用
            assert mock_logger.info.call_count >= 1
            # 检查是否有预期的日志调用
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("采用最高优先级决策" in call for call in info_calls)