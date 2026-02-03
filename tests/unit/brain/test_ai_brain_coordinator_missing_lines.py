#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 缺失行覆盖测试

专门针对缺失的191行代码进行测试覆盖
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorMissingLines:
    """AI大脑协调器缺失行覆盖测试"""

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
    async def test_initialize_soldier_not_registered(self, coordinator):
        """测试Soldier未注册的情况 - 覆盖行97"""
        # 只有Commander和Scholar注册
        def mock_is_registered(interface):
            return interface in [ICommanderEngine, IScholarEngine]
        
        coordinator.container.is_registered.side_effect = mock_is_registered
        
        await coordinator.initialize()
        
        assert coordinator.soldier is None
        assert coordinator.commander is not None
        assert coordinator.scholar is not None
        assert coordinator.coordination_active is True

    @pytest.mark.asyncio
    async def test_initialize_commander_not_registered(self, coordinator):
        """测试Commander未注册的情况 - 覆盖行102"""
        # 只有Soldier和Scholar注册
        def mock_is_registered(interface):
            return interface in [ISoldierEngine, IScholarEngine]
        
        coordinator.container.is_registered.side_effect = mock_is_registered
        
        await coordinator.initialize()
        
        assert coordinator.soldier is not None
        assert coordinator.commander is None
        assert coordinator.scholar is not None
        assert coordinator.coordination_active is True

    @pytest.mark.asyncio
    async def test_initialize_scholar_not_registered(self, coordinator):
        """测试Scholar未注册的情况 - 覆盖行105"""
        # 只有Soldier和Commander注册
        def mock_is_registered(interface):
            return interface in [ISoldierEngine, ICommanderEngine]
        
        coordinator.container.is_registered.side_effect = mock_is_registered
        
        await coordinator.initialize()
        
        assert coordinator.soldier is not None
        assert coordinator.commander is not None
        assert coordinator.scholar is None
        assert coordinator.coordination_active is True

    @pytest.mark.asyncio
    async def test_initialize_none_registered(self, coordinator):
        """测试无AI脑注册的情况 - 覆盖行97, 102, 105"""
        # 没有任何AI脑注册
        coordinator.container.is_registered.return_value = False
        
        await coordinator.initialize()
        
        assert coordinator.soldier is None
        assert coordinator.commander is None
        assert coordinator.scholar is None
        assert coordinator.coordination_active is True

    @pytest.mark.asyncio
    async def test_request_decision_direct_soldier_success(self, coordinator):
        """测试Soldier直接决策成功路径 - 覆盖行155-161"""
        await coordinator.initialize()
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_soldier_direct"
        
        result = await coordinator._request_decision_direct(context, "soldier", correlation_id)
        
        assert result is not None
        assert result.primary_brain == "soldier"
        assert result.action == "buy"
        assert result.confidence == 0.8
        assert result.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_request_decision_direct_commander_success(self, coordinator):
        """测试Commander直接决策成功路径 - 覆盖行181-190"""
        await coordinator.initialize()
        
        context = {"market": "bull"}
        correlation_id = "test_commander_direct"
        
        result = await coordinator._request_decision_direct(context, "commander", correlation_id)
        
        assert result is not None
        assert result.primary_brain == "commander"
        assert result.action == "buy"
        assert result.confidence == 0.7
        assert result.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_request_decision_direct_scholar_success(self, coordinator):
        """测试Scholar直接决策成功路径 - 覆盖行197-206"""
        await coordinator.initialize()
        
        context = {"factor": "momentum"}
        correlation_id = "test_scholar_direct"
        
        result = await coordinator._request_decision_direct(context, "scholar", correlation_id)
        
        assert result is not None
        assert result.primary_brain == "scholar"
        assert result.action == "buy"
        assert result.confidence == 0.75
        assert result.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_request_decision_direct_soldier_exception(self, coordinator):
        """测试Soldier直接决策异常 - 覆盖行164"""
        await coordinator.initialize()
        
        # 让Soldier抛出异常
        coordinator.soldier.decide.side_effect = Exception("Soldier error")
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_soldier_exception"
        
        # Mock事件发布和等待决策
        with patch.object(coordinator, '_wait_for_decision', return_value=None):
            result = await coordinator._request_decision_direct(context, "soldier", correlation_id)
            
            # 应该回退到事件模式，但由于等待超时返回None
            assert result is None

    @pytest.mark.asyncio
    async def test_request_decision_direct_commander_exception(self, coordinator):
        """测试Commander直接决策异常 - 覆盖行193"""
        await coordinator.initialize()
        
        # 让Commander抛出异常
        coordinator.commander.analyze.side_effect = Exception("Commander error")
        
        context = {"market": "bull"}
        correlation_id = "test_commander_exception"
        
        # Mock事件发布和等待决策
        with patch.object(coordinator, '_wait_for_decision', return_value=None):
            result = await coordinator._request_decision_direct(context, "commander", correlation_id)
            
            # 应该回退到事件模式，但由于等待超时返回None
            assert result is None

    @pytest.mark.asyncio
    async def test_request_decision_direct_scholar_exception(self, coordinator):
        """测试Scholar直接决策异常 - 覆盖行209"""
        await coordinator.initialize()
        
        # 让Scholar抛出异常
        coordinator.scholar.research.side_effect = Exception("Scholar error")
        
        context = {"factor": "momentum"}
        correlation_id = "test_scholar_exception"
        
        # Mock事件发布和等待决策
        with patch.object(coordinator, '_wait_for_decision', return_value=None):
            result = await coordinator._request_decision_direct(context, "scholar", correlation_id)
            
            # 应该回退到事件模式，但由于等待超时返回None
            assert result is None

    @pytest.mark.asyncio
    async def test_request_decision_direct_event_publish_exception(self, coordinator):
        """测试事件发布异常 - 覆盖行226"""
        await coordinator.initialize()
        
        # 让Soldier失败，强制走事件路径
        coordinator.soldier.decide.side_effect = Exception("Soldier failed")
        
        # 让事件发布也失败
        coordinator.event_bus.publish.side_effect = Exception("Event publish failed")
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_event_exception"
        
        result = await coordinator._request_decision_direct(context, "soldier", correlation_id)
        
        # 事件发布失败，应该返回None
        assert result is None

    @pytest.mark.asyncio
    async def test_request_decision_with_batch_success(self, coordinator):
        """测试批处理决策成功 - 覆盖行246-247"""
        await coordinator.initialize()
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_success"
        
        # Mock批处理结果
        mock_decision = BrainDecision(
            decision_id="batch_success",
            primary_brain="commander",
            action="buy",
            confidence=0.8,
            reasoning="batch success test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        # Mock Future
        future = asyncio.Future()
        future.set_result(mock_decision)
        
        with patch('asyncio.Future', return_value=future):
            with patch.object(coordinator, '_process_batch') as mock_process:
                # 模拟达到批处理大小
                coordinator.pending_batch = [None] * coordinator.batch_size
                
                result = await coordinator._request_decision_with_batch(context, "commander", correlation_id)
                
                assert result == mock_decision
                mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_decision_with_batch_timeout(self, coordinator):
        """测试批处理超时 - 覆盖行263"""
        await coordinator.initialize()
        
        context = {"symbol": "000001.SZ"}
        correlation_id = "test_batch_timeout"
        
        # Mock Future that never completes
        future = asyncio.Future()
        
        with patch('asyncio.Future', return_value=future):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError("Timeout")):
                result = await coordinator._request_decision_with_batch(context, "commander", correlation_id)
                
                assert result is None

    @pytest.mark.asyncio
    async def test_process_batch_empty(self, coordinator):
        """测试空批处理队列 - 覆盖行279"""
        # 确保批处理队列为空
        coordinator.pending_batch = []
        
        # 调用处理批处理
        await coordinator._process_batch()
        
        # 空队列应该直接返回，不做任何处理
        assert len(coordinator.pending_batch) == 0

    @pytest.mark.asyncio
    async def test_process_batch_item_exception(self, coordinator):
        """测试批处理项目异常 - 覆盖行315-317"""
        future = asyncio.Future()
        context = {"symbol": "000001.SZ"}
        
        # 让事件发布失败
        coordinator.event_bus.publish.side_effect = Exception("Batch item failed")
        
        await coordinator._process_batch_item(context, "soldier", "batch_item_corr", future)
        
        # Future应该被设置为异常
        assert future.done()
        assert isinstance(future.exception(), Exception)

    @pytest.mark.asyncio
    async def test_wait_for_decision_found(self, coordinator):
        """测试等待决策找到结果 - 覆盖行352"""
        correlation_id = "test_wait_found"
        
        # 预先添加决策结果
        test_decision = BrainDecision(
            decision_id="wait_found",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="wait found test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        coordinator.pending_decisions[correlation_id] = test_decision
        
        result = await coordinator._wait_for_decision(correlation_id, timeout=1.0)
        
        assert result == test_decision
        # 决策应该从pending中移除
        assert correlation_id not in coordinator.pending_decisions

    @pytest.mark.asyncio
    async def test_wait_for_decision_timeout_cleanup(self, coordinator):
        """测试等待决策超时清理 - 覆盖行370-372"""
        correlation_id = "test_wait_timeout_cleanup"
        
        # 不预先添加决策，让它真正超时
        # 使用很短的超时时间
        result = await coordinator._wait_for_decision(correlation_id, timeout=0.001)
        
        assert result is None
        # 超时后应该没有pending决策
        assert correlation_id not in coordinator.pending_decisions

    @pytest.mark.asyncio
    async def test_handle_brain_decision_missing_data(self, coordinator):
        """测试处理AI脑决策事件缺失数据 - 覆盖行419"""
        # 创建缺失数据的事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data={"action": "decision_result"}  # 缺失必要字段
        )
        
        # 应该不抛出异常，而是记录错误
        await coordinator._handle_brain_decision(event)
        
        # 验证没有决策被存储
        assert len(coordinator.pending_decisions) == 0

    @pytest.mark.asyncio
    async def test_handle_brain_decision_exception(self, coordinator):
        """测试处理AI脑决策事件异常 - 覆盖行422-424"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data=None  # None数据会导致异常
        )
        
        # 应该不抛出异常，而是记录错误
        await coordinator._handle_brain_decision(event)

    @pytest.mark.asyncio
    async def test_handle_analysis_completed_unknown_type(self, coordinator):
        """测试处理未知分析类型 - 覆盖行445"""
        event_data = {
            "analysis_type": "unknown_analysis",
            "result": "some result"
        }
        
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="commander",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=event_data
        )
        
        # 应该不抛出异常，未知类型不会触发任何动作
        await coordinator._handle_analysis_completed(event)

    @pytest.mark.asyncio
    async def test_handle_analysis_completed_exception(self, coordinator):
        """测试处理分析完成事件异常 - 覆盖行448"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="commander",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data=None  # None数据会导致异常
        )
        
        # 应该不抛出异常，而是记录错误
        await coordinator._handle_analysis_completed(event)

    @pytest.mark.asyncio
    async def test_handle_factor_discovered_exception(self, coordinator):
        """测试处理因子发现事件异常 - 覆盖行467"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data={}  # 空数据会导致异常
        )
        
        # 应该不抛出异常，而是记录错误
        await coordinator._handle_factor_discovered(event)

    def test_create_fallback_decision_high_position_risk(self, coordinator):
        """测试高仓位高风险备用决策 - 覆盖行499-502"""
        context = {
            "current_position": 0.9,  # 高仓位
            "risk_level": "high"      # 高风险
        }
        correlation_id = "fallback_high_pos_risk"
        
        decision = coordinator._create_fallback_decision(context, correlation_id)
        
        # 高仓位应该优先于高风险
        assert decision.action == "reduce"
        assert decision.confidence == 0.3
        assert "当前仓位过高" in decision.reasoning

    def test_create_fallback_decision_only_high_risk(self, coordinator):
        """测试仅高风险备用决策 - 覆盖行505"""
        context = {
            "current_position": 0.3,  # 正常仓位
            "risk_level": "high"      # 高风险
        }
        correlation_id = "fallback_only_high_risk"
        
        decision = coordinator._create_fallback_decision(context, correlation_id)
        
        assert decision.action == "sell"
        assert decision.confidence == 0.4
        assert "风险过高" in decision.reasoning

    def test_add_to_history_max_limit_exceeded(self, coordinator):
        """测试历史记录超限处理 - 覆盖行526"""
        # 设置较小的最大历史记录限制
        coordinator.max_history = 2
        
        # 添加3个决策，应该只保留最后2个
        for i in range(3):
            decision = BrainDecision(
                decision_id=f"history_limit_{i}",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning=f"history limit test {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"history_limit_corr_{i}"
            )
            coordinator._add_to_history(decision)
        
        # 应该只保留最后2个
        assert len(coordinator.decision_history) == 2
        assert coordinator.decision_history[0].decision_id == "history_limit_1"
        assert coordinator.decision_history[1].decision_id == "history_limit_2"

    def test_get_decision_history_with_brain_filter_no_match(self, coordinator):
        """测试决策历史脑过滤无匹配 - 覆盖行538-540"""
        # 添加不同脑的决策
        decision = BrainDecision(
            decision_id="filter_test",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="filter test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="filter_corr"
        )
        coordinator.decision_history.append(decision)
        
        # 过滤不存在的脑类型
        history = coordinator.get_decision_history(brain_filter="nonexistent")
        
        assert len(history) == 0

    def test_get_decision_history_with_limit_exceeds_available(self, coordinator):
        """测试决策历史限制超过可用数量 - 覆盖行542"""
        # 添加2个决策
        for i in range(2):
            decision = BrainDecision(
                decision_id=f"limit_exceed_{i}",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning=f"limit exceed test {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"limit_exceed_corr_{i}"
            )
            coordinator.decision_history.append(decision)
        
        # 请求5个，但只有2个可用
        history = coordinator.get_decision_history(limit=5)
        
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_resolve_conflicts_empty_list(self, coordinator):
        """测试空决策列表冲突解决 - 覆盖行549-551"""
        decisions = []
        
        result = await coordinator.resolve_conflicts(decisions)
        
        assert result.primary_brain == "coordinator_fallback_coordinator"
        assert result.action == "hold"

    @pytest.mark.asyncio
    async def test_resolve_conflicts_high_confidence_decision(self, coordinator):
        """测试高置信度决策优先 - 覆盖行568-570"""
        decisions = [
            BrainDecision(
                decision_id="high_conf",
                primary_brain="soldier",
                action="buy",
                confidence=0.85,  # 高置信度 > 0.8
                reasoning="high confidence test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="high_conf_corr"
            ),
            BrainDecision(
                decision_id="low_conf",
                primary_brain="commander",
                action="sell",
                confidence=0.6,
                reasoning="low confidence test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="low_conf_corr"
            )
        ]
        
        result = await coordinator.resolve_conflicts(decisions)
        
        # 应该选择高置信度决策
        assert result.action == "buy"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_resolve_conflicts_close_confidence_conflict(self, coordinator):
        """测试置信度相近冲突 - 覆盖行575, 585-586, 590"""
        decisions = [
            BrainDecision(
                decision_id="conflict1",
                primary_brain="soldier",
                action="buy",
                confidence=0.6,
                reasoning="conflict test 1",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="conflict1_corr"
            ),
            BrainDecision(
                decision_id="conflict2",
                primary_brain="commander",
                action="sell",
                confidence=0.65,  # 差异0.05 < 0.1，触发冲突
                reasoning="conflict test 2",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="conflict2_corr"
            )
        ]
        
        result = await coordinator.resolve_conflicts(decisions)
        
        # 应该生成保守决策
        assert result.primary_brain == "coordinator_conflict_resolution"
        assert coordinator.stats["coordination_conflicts"] >= 1

    @pytest.mark.asyncio
    async def test_resolve_conflicts_no_conflict_return_top(self, coordinator):
        """测试无冲突返回最高优先级 - 覆盖行606"""
        decisions = [
            BrainDecision(
                decision_id="top_priority",
                primary_brain="soldier",  # 最高优先级
                action="buy",
                confidence=0.6,
                reasoning="top priority test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="top_priority_corr"
            ),
            BrainDecision(
                decision_id="lower_priority",
                primary_brain="commander",
                action="sell",
                confidence=0.4,  # 差异0.2 >= 0.1，无冲突
                reasoning="lower priority test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="lower_priority_corr"
            )
        ]
        
        result = await coordinator.resolve_conflicts(decisions)
        
        # 应该返回最高优先级决策
        assert result.action == "buy"
        assert result.primary_brain == "soldier"

    def test_create_conservative_decision_sell_buy_conflict(self, coordinator):
        """测试卖买冲突保守决策 - 覆盖行637-639"""
        decisions = [
            BrainDecision(
                decision_id="sell_decision",
                primary_brain="soldier",
                action="sell",
                confidence=0.6,
                reasoning="sell test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="sell_corr"
            ),
            BrainDecision(
                decision_id="buy_decision",
                primary_brain="commander",
                action="buy",
                confidence=0.6,
                reasoning="buy test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="buy_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        assert result.action == "hold"
        assert "买卖决策冲突" in result.reasoning

    def test_create_conservative_decision_all_buy_hold(self, coordinator):
        """测试全部买入持有保守决策 - 覆盖行642, 644-647"""
        decisions = [
            BrainDecision(
                decision_id="buy_decision",
                primary_brain="soldier",
                action="buy",
                confidence=0.6,
                reasoning="buy test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="buy_corr"
            ),
            BrainDecision(
                decision_id="hold_decision",
                primary_brain="commander",
                action="hold",
                confidence=0.6,
                reasoning="hold test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="hold_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        assert result.action == "hold"
        assert "买入/持有决策" in result.reasoning

    def test_create_conservative_decision_with_reduce_action(self, coordinator):
        """测试包含减仓动作保守决策 - 覆盖行649-651"""
        decisions = [
            BrainDecision(
                decision_id="reduce_decision",
                primary_brain="soldier",
                action="reduce",
                confidence=0.6,
                reasoning="reduce test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="reduce_corr"
            ),
            BrainDecision(
                decision_id="hold_decision",
                primary_brain="commander",
                action="hold",
                confidence=0.6,
                reasoning="hold test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="hold_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        assert result.action == "reduce"
        assert "存在减仓建议" in result.reasoning

    def test_create_conservative_decision_default_case(self, coordinator):
        """测试默认保守决策情况 - 覆盖行653"""
        decisions = [
            BrainDecision(
                decision_id="unknown_decision",
                primary_brain="soldier",
                action="unknown_action",
                confidence=0.6,
                reasoning="unknown test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="unknown_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        assert result.action == "hold"
        assert "决策冲突，采用默认保守策略" in result.reasoning

    def test_get_statistics_zero_total_decisions(self, coordinator):
        """测试零总决策数统计 - 覆盖行671, 674, 676"""
        # 确保总决策数为0
        coordinator.stats["total_decisions"] = 0
        coordinator.decision_history = []
        
        stats = coordinator.get_statistics()
        
        # 验证零除法处理
        assert stats.get("soldier_percentage", 0) == 0
        assert stats.get("commander_percentage", 0) == 0
        assert stats.get("scholar_percentage", 0) == 0
        assert stats["average_confidence"] == 0.0
        assert stats["conflict_rate"] == 0.0

    def test_get_statistics_with_recent_decisions(self, coordinator):
        """测试有最近决策的统计 - 覆盖行687"""
        # 添加一些决策历史
        for i in range(5):
            decision = BrainDecision(
                decision_id=f"recent_{i}",
                primary_brain="soldier",
                action="buy",
                confidence=0.5 + (i * 0.1),  # 0.5, 0.6, 0.7, 0.8, 0.9
                reasoning=f"recent test {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"recent_corr_{i}"
            )
            coordinator.decision_history.append(decision)
        
        stats = coordinator.get_statistics()
        
        # 验证平均置信度计算
        expected_avg = (0.5 + 0.6 + 0.7 + 0.8 + 0.9) / 5  # 0.7
        assert abs(stats["average_confidence"] - expected_avg) < 0.01

    def test_get_statistics_decisions_per_minute_calculation(self, coordinator):
        """测试每分钟决策数计算 - 覆盖行690-692"""
        # 设置开始时间为1分钟前
        import datetime as dt
        coordinator.stats["start_time"] = dt.datetime.now() - dt.timedelta(minutes=1)
        coordinator.stats["total_decisions"] = 60
        
        stats = coordinator.get_statistics()
        
        # 验证每分钟决策数计算
        assert stats["decisions_per_minute"] > 50  # 应该接近60

    def test_get_statistics_concurrent_and_batch_rates(self, coordinator):
        """测试并发和批处理率计算 - 覆盖行694, 696"""
        coordinator.stats.update({
            "total_decisions": 100,
            "concurrent_decisions": 80,
            "batch_decisions": 60
        })
        
        stats = coordinator.get_statistics()
        
        assert stats["concurrent_rate"] == 80.0  # 80/100 * 100
        assert stats["batch_rate"] == 60.0      # 60/100 * 100

    @pytest.mark.asyncio
    async def test_get_coordination_status_detailed_info(self, coordinator):
        """测试获取详细协调状态 - 覆盖行715, 718-719, 722-723, 726"""
        await coordinator.initialize()
        
        # 设置一些状态
        coordinator.stats["total_decisions"] = 50
        coordinator.stats["start_time"] = datetime.now()
        
        # 添加pending决策
        coordinator.pending_decisions["test1"] = BrainDecision(
            decision_id="status_test",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,
            reasoning="status test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="status_corr"
        )
        
        # 添加历史决策
        for i in range(3):
            decision = BrainDecision(
                decision_id=f"status_history_{i}",
                primary_brain="soldier",
                action="buy",
                confidence=0.6,
                reasoning=f"status history {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"status_history_corr_{i}"
            )
            coordinator.decision_history.append(decision)
        
        status = await coordinator.get_coordination_status()
        
        # 验证详细状态信息
        assert status["coordination_active"] is True
        assert status["pending_decisions"] == 1
        assert status["decision_history_count"] == 3
        assert len(status["recent_decisions"]) == 3
        assert "stats" in status
        assert "uptime_seconds" in status["stats"]
        assert "decisions_per_minute" in status["stats"]

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, coordinator):
        """测试关闭清理 - 覆盖行763-764, 768"""
        # 设置一些状态
        coordinator.coordination_active = True
        coordinator.pending_decisions["test"] = BrainDecision(
            decision_id="shutdown_test",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,
            reasoning="shutdown test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="shutdown_corr"
        )
        
        await coordinator.shutdown()
        
        # 验证状态被清理
        assert coordinator.coordination_active is False
        assert len(coordinator.pending_decisions) == 0

    @pytest.mark.asyncio
    async def test_global_coordinator_singleton_behavior(self):
        """测试全局协调器单例行为 - 覆盖行786, 789"""
        from src.brain.ai_brain_coordinator import get_ai_brain_coordinator, _global_coordinator
        
        # 重置全局协调器
        import src.brain.ai_brain_coordinator as module
        module._global_coordinator = None
        
        # 第一次调用应该创建新实例
        coordinator1 = await get_ai_brain_coordinator()
        assert coordinator1 is not None
        
        # 第二次调用应该返回同一实例
        coordinator2 = await get_ai_brain_coordinator()
        assert coordinator1 is coordinator2

    @pytest.mark.asyncio
    async def test_request_ai_decision_convenience_function(self):
        """测试便捷决策函数 - 覆盖行815-816"""
        from src.brain.ai_brain_coordinator import request_ai_decision
        
        context = {"symbol": "000001.SZ"}
        
        # Mock全局协调器
        with patch('src.brain.ai_brain_coordinator.get_ai_brain_coordinator') as mock_get_coord:
            mock_coordinator = MagicMock()
            mock_coordinator.request_decision = AsyncMock(return_value=BrainDecision(
                decision_id="convenience_test",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning="convenience test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="convenience_corr"
            ))
            mock_get_coord.return_value = mock_coordinator
            
            result = await request_ai_decision(context, "soldier")
            
            assert result is not None
            assert result.action == "buy"
            mock_coordinator.request_decision.assert_called_once_with(context, "soldier")

    @pytest.mark.asyncio
    async def test_get_ai_coordination_status_convenience_function(self):
        """测试便捷状态函数 - 覆盖行836"""
        from src.brain.ai_brain_coordinator import get_ai_coordination_status
        
        # Mock全局协调器
        with patch('src.brain.ai_brain_coordinator.get_ai_brain_coordinator') as mock_get_coord:
            mock_coordinator = MagicMock()
            mock_coordinator.get_coordination_status = AsyncMock(return_value={
                "coordination_active": True,
                "test": "status"
            })
            mock_get_coord.return_value = mock_coordinator
            
            result = await get_ai_coordination_status()
            
            assert result is not None
            assert result["coordination_active"] is True
            mock_coordinator.get_coordination_status.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])