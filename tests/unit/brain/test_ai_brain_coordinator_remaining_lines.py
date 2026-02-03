"""
AI三脑协调器剩余行测试

🧪 Test Engineer 专门针对AI Brain Coordinator剩余未覆盖行创建的测试
目标：将覆盖率从64.94%提升到100%

剩余缺失行分析：
- 97-116: 初始化方法
- 121-135: 事件订阅设置
- 179, 190: 并发控制逻辑
- 257-258, 261-274: 批处理相关
- 279: 异常处理
- 372: 等待决策逻辑
- 431: 事件处理
- 445-467: 分析完成事件处理
- 540: 冲突解决
- 559-561: 保守决策
- 590, 606: 统计信息
- 715-726: 历史记录管理
- 763-764, 771-816: 统计计算
- 829-872: 协调状态
- 891, 906, 912-913: 状态方法
- 965: 关闭方法
- 1034-1041, 1047-1048, 1053-1054: 全局函数
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brain.ai_brain_coordinator import (
    AIBrainCoordinator, 
    BrainDecision,
    get_ai_brain_coordinator,
    request_ai_decision,
    get_ai_coordination_status
)
from src.brain.interfaces import ICommanderEngine, IScholarEngine, ISoldierEngine
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority


class TestAIBrainCoordinatorRemainingLines:
    """AI三脑协调器剩余行测试"""
    
    @pytest.fixture
    def coordinator(self):
        """创建协调器实例"""
        event_bus = MagicMock(spec=EventBus)
        container = MagicMock(spec=DIContainer)
        return AIBrainCoordinator(event_bus, container)
    
    @pytest.mark.asyncio
    async def test_initialize_with_all_brains(self, coordinator):
        """测试初始化所有AI脑 - 覆盖行97-116"""
        # Mock所有AI脑实例
        mock_soldier = MagicMock(spec=ISoldierEngine)
        mock_commander = MagicMock(spec=ICommanderEngine)
        mock_scholar = MagicMock(spec=IScholarEngine)
        
        # 设置容器返回所有AI脑
        coordinator.container.is_registered.side_effect = lambda interface: True
        coordinator.container.resolve.side_effect = lambda interface: {
            ISoldierEngine: mock_soldier,
            ICommanderEngine: mock_commander,
            IScholarEngine: mock_scholar
        }[interface]
        
        # Mock事件订阅设置
        coordinator._setup_event_subscriptions = AsyncMock()
        
        # 执行初始化
        await coordinator.initialize()
        
        # 验证所有AI脑被正确设置
        assert coordinator.soldier == mock_soldier
        assert coordinator.commander == mock_commander
        assert coordinator.scholar == mock_scholar
        assert coordinator.coordination_active is True
        
        # 验证事件订阅被调用
        coordinator._setup_event_subscriptions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_with_partial_brains(self, coordinator):
        """测试部分AI脑初始化 - 覆盖行97-116"""
        # 只有Soldier可用
        mock_soldier = MagicMock(spec=ISoldierEngine)
        
        def mock_is_registered(interface):
            return interface == ISoldierEngine
        
        def mock_resolve(interface):
            if interface == ISoldierEngine:
                return mock_soldier
            raise Exception("Interface not registered")
        
        coordinator.container.is_registered.side_effect = mock_is_registered
        coordinator.container.resolve.side_effect = mock_resolve
        
        # Mock事件订阅设置
        coordinator._setup_event_subscriptions = AsyncMock()
        
        # 执行初始化
        await coordinator.initialize()
        
        # 验证只有Soldier被设置
        assert coordinator.soldier == mock_soldier
        assert coordinator.commander is None
        assert coordinator.scholar is None
        assert coordinator.coordination_active is True
    
    @pytest.mark.asyncio
    async def test_initialize_exception_handling(self, coordinator):
        """测试初始化异常处理 - 覆盖行97-116"""
        # Mock容器抛出异常
        coordinator.container.is_registered.side_effect = Exception("Container error")
        
        # 初始化应该抛出异常
        with pytest.raises(Exception, match="Container error"):
            await coordinator.initialize()
    
    @pytest.mark.asyncio
    async def test_setup_event_subscriptions(self, coordinator):
        """测试事件订阅设置 - 覆盖行121-135"""
        # Mock事件总线订阅
        coordinator.event_bus.subscribe = AsyncMock()
        
        # 执行事件订阅设置
        await coordinator._setup_event_subscriptions()
        
        # 验证所有事件类型都被订阅
        expected_calls = [
            (EventType.DECISION_MADE, coordinator._handle_brain_decision, "coordinator_decision_handler"),
            (EventType.ANALYSIS_COMPLETED, coordinator._handle_analysis_completed, "coordinator_analysis_handler"),
            (EventType.FACTOR_DISCOVERED, coordinator._handle_factor_discovered, "coordinator_factor_handler")
        ]
        
        assert coordinator.event_bus.subscribe.call_count == 3
        for call_args in coordinator.event_bus.subscribe.call_args_list:
            args = call_args[0]
            assert len(args) == 3
            assert args[0] in [EventType.DECISION_MADE, EventType.ANALYSIS_COMPLETED, EventType.FACTOR_DISCOVERED]
    
    @pytest.mark.asyncio
    async def test_concurrent_decision_processing(self, coordinator):
        """测试并发决策处理 - 覆盖行179, 190"""
        # 设置Mock Soldier
        mock_soldier = AsyncMock()
        mock_soldier.decide.return_value = {
            "decision": {"action": "buy", "confidence": 0.8, "reasoning": "test"},
            "metadata": {}
        }
        coordinator.soldier = mock_soldier
        
        # 创建多个并发请求
        tasks = []
        for i in range(5):
            task = coordinator.request_decision({"symbol": f"00000{i}.SZ"}, "soldier")
            tasks.append(task)
        
        # 并发执行所有请求
        results = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        assert len(results) == 5
        for result in results:
            assert result.action == "buy"
            assert result.confidence == 0.8
        
        # 验证并发统计被更新
        assert coordinator.stats["concurrent_decisions"] >= 5
    
    @pytest.mark.asyncio
    async def test_batch_processing_enabled(self, coordinator):
        """测试批处理启用 - 覆盖行257-258, 261-274"""
        coordinator.enable_batch_processing = True
        coordinator.batch_size = 2
        
        # Mock批处理方法
        coordinator._request_decision_with_batch = AsyncMock(return_value=BrainDecision(
            decision_id="batch_001",
            primary_brain="commander",
            action="hold",
            confidence=0.6,
            reasoning="batch test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="batch_corr"
        ))
        
        # 请求Commander决策（应该使用批处理）
        result = await coordinator._execute_decision_request({"symbol": "000001.SZ"}, "commander")
        
        # 验证使用了批处理
        coordinator._request_decision_with_batch.assert_called_once()
        assert result.primary_brain == "commander"
        assert result.action == "hold"
    
    @pytest.mark.asyncio
    async def test_batch_processing_disabled(self, coordinator):
        """测试批处理禁用 - 覆盖行257-258"""
        coordinator.enable_batch_processing = False
        
        # Mock直接决策方法
        coordinator._request_decision_direct = AsyncMock(return_value=BrainDecision(
            decision_id="direct_001",
            primary_brain="commander",
            action="buy",
            confidence=0.7,
            reasoning="direct test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="direct_corr"
        ))
        
        # 请求Commander决策（应该使用直接调用）
        result = await coordinator._execute_decision_request({"symbol": "000001.SZ"}, "commander")
        
        # 验证使用了直接调用
        coordinator._request_decision_direct.assert_called_once()
        assert result.primary_brain == "commander"
        assert result.action == "buy"
    
    @pytest.mark.asyncio
    async def test_soldier_direct_call_success(self, coordinator):
        """测试Soldier直接调用成功 - 覆盖行279"""
        # 设置Mock Soldier
        mock_soldier = AsyncMock()
        mock_soldier.decide.return_value = {
            "decision": {"action": "sell", "confidence": 0.9, "reasoning": "strong signal"},
            "metadata": {"signal_strength": 0.95}
        }
        coordinator.soldier = mock_soldier
        
        # 执行直接调用
        result = await coordinator._request_decision_direct(
            {"symbol": "000001.SZ"}, "soldier", "test_corr"
        )
        
        # 验证结果
        assert result is not None
        assert result.action == "sell"
        assert result.confidence == 0.9
        assert result.reasoning == "strong signal"
        assert result.primary_brain == "soldier"
        assert result.correlation_id == "test_corr"
    
    @pytest.mark.asyncio
    async def test_commander_direct_call_success(self, coordinator):
        """测试Commander直接调用成功 - 覆盖行279"""
        # 设置Mock Commander
        mock_commander = AsyncMock()
        mock_commander.analyze.return_value = {
            "recommendation": "reduce",
            "confidence": 0.75,
            "analysis": "market volatility high",
            "risk_level": "medium"
        }
        coordinator.commander = mock_commander
        
        # 执行直接调用
        result = await coordinator._request_decision_direct(
            {"symbol": "000001.SZ"}, "commander", "test_corr"
        )
        
        # 验证结果
        assert result is not None
        assert result.action == "reduce"
        assert result.confidence == 0.75
        assert result.reasoning == "market volatility high"
        assert result.primary_brain == "commander"
    
    @pytest.mark.asyncio
    async def test_wait_for_decision_success(self, coordinator):
        """测试等待决策成功 - 覆盖行372"""
        correlation_id = "test_wait_success"
        
        # 预设决策结果
        decision = BrainDecision(
            decision_id="wait_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="wait test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        # 在短时间后添加决策
        async def add_decision():
            await asyncio.sleep(0.01)
            coordinator.pending_decisions[correlation_id] = decision
        
        # 并发执行添加决策和等待
        add_task = asyncio.create_task(add_decision())
        wait_task = asyncio.create_task(coordinator._wait_for_decision(correlation_id, timeout=1.0))
        
        # 等待两个任务完成
        await add_task
        result = await wait_task
        
        # 验证结果
        assert result == decision
        assert correlation_id not in coordinator.pending_decisions  # 应该被移除
    
    @pytest.mark.asyncio
    async def test_handle_brain_decision_success(self, coordinator):
        """测试处理AI脑决策成功 - 覆盖行431"""
        # 创建决策事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            priority=EventPriority.HIGH,
            data={
                "action": "decision_result",
                "decision_id": "brain_001",
                "primary_brain": "soldier",
                "decision_action": "buy",
                "confidence": 0.85,
                "reasoning": "strong buy signal",
                "supporting_data": {"signal": "bullish"},
                "correlation_id": "brain_corr_001"
            }
        )
        
        # 处理事件
        await coordinator._handle_brain_decision(event)
        
        # 验证决策被正确存储
        assert "brain_corr_001" in coordinator.pending_decisions
        decision = coordinator.pending_decisions["brain_corr_001"]
        assert decision.action == "buy"
        assert decision.confidence == 0.85
        assert decision.primary_brain == "soldier"
    
    @pytest.mark.asyncio
    async def test_handle_analysis_completed_market_analysis(self, coordinator):
        """测试处理市场分析完成事件 - 覆盖行445-467"""
        # Mock策略调整触发
        coordinator._trigger_strategy_adjustment = AsyncMock()
        
        # 创建市场分析完成事件
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="commander",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data={
                "analysis_type": "market_analysis",
                "result": "bullish trend detected",
                "confidence": 0.8
            }
        )
        
        # 处理事件
        await coordinator._handle_analysis_completed(event)
        
        # 验证策略调整被触发
        coordinator._trigger_strategy_adjustment.assert_called_once_with(event.data)
    
    @pytest.mark.asyncio
    async def test_handle_analysis_completed_factor_analysis(self, coordinator):
        """测试处理因子分析完成事件 - 覆盖行445-467"""
        # Mock因子验证触发
        coordinator._trigger_factor_validation = AsyncMock()
        
        # 创建因子分析完成事件
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            priority=EventPriority.NORMAL,
            data={
                "analysis_type": "factor_analysis",
                "factor_name": "momentum_factor",
                "effectiveness": 0.75
            }
        )
        
        # 处理事件
        await coordinator._handle_analysis_completed(event)
        
        # 验证因子验证被触发
        coordinator._trigger_factor_validation.assert_called_once_with(event.data)
    
    @pytest.mark.asyncio
    async def test_resolve_conflicts_single_decision(self, coordinator):
        """测试单个决策冲突解决 - 覆盖行540"""
        # 创建单个决策
        decision = BrainDecision(
            decision_id="single_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="single decision",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="single_corr"
        )
        
        # 解决冲突
        result = await coordinator.resolve_conflicts([decision])
        
        # 验证返回原决策
        assert result == decision
    
    @pytest.mark.asyncio
    async def test_resolve_conflicts_high_confidence(self, coordinator):
        """测试高置信度决策冲突解决 - 覆盖行540"""
        # 创建高置信度决策
        high_conf_decision = BrainDecision(
            decision_id="high_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.95,  # 高置信度
            reasoning="very strong signal",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="high_corr"
        )
        
        low_conf_decision = BrainDecision(
            decision_id="low_001",
            primary_brain="commander",
            action="sell",
            confidence=0.6,
            reasoning="weak signal",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="low_corr"
        )
        
        # 解决冲突
        result = await coordinator.resolve_conflicts([high_conf_decision, low_conf_decision])
        
        # 验证返回高置信度决策
        assert result == high_conf_decision
    
    def test_create_conservative_decision_buy_sell_conflict(self, coordinator):
        """测试买卖冲突的保守决策 - 覆盖行559-561"""
        # 创建买卖冲突决策
        buy_decision = BrainDecision(
            decision_id="buy_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,
            reasoning="buy signal",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="buy_corr"
        )
        
        sell_decision = BrainDecision(
            decision_id="sell_001",
            primary_brain="commander",
            action="sell",
            confidence=0.6,
            reasoning="sell signal",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="sell_corr"
        )
        
        # 生成保守决策
        result = coordinator._create_conservative_decision([buy_decision, sell_decision])
        
        # 验证保守决策
        assert result.action == "hold"  # 买卖冲突 -> 持有
        assert result.primary_brain == "coordinator_conflict_resolution"
        assert "买卖决策冲突" in result.reasoning
    
    def test_create_conservative_decision_reduce_present(self, coordinator):
        """测试包含减仓建议的保守决策 - 覆盖行559-561"""
        # 创建包含减仓的决策
        buy_decision = BrainDecision(
            decision_id="buy_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.7,
            reasoning="buy signal",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="buy_corr"
        )
        
        reduce_decision = BrainDecision(
            decision_id="reduce_001",
            primary_brain="commander",
            action="reduce",
            confidence=0.8,
            reasoning="risk control",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="reduce_corr"
        )
        
        # 生成保守决策
        result = coordinator._create_conservative_decision([buy_decision, reduce_decision])
        
        # 验证保守决策
        assert result.action == "reduce"  # 有减仓建议 -> 减仓
        assert result.primary_brain == "coordinator_conflict_resolution"
        assert "风险控制策略" in result.reasoning
    
    def test_get_statistics_with_decisions(self, coordinator):
        """测试获取统计信息（有决策历史）- 覆盖行590, 606, 715-726, 763-764, 771-816"""
        # 添加一些决策历史
        for i in range(10):
            decision = BrainDecision(
                decision_id=f"stat_{i:03d}",
                primary_brain=["soldier", "commander", "scholar"][i % 3],
                action="buy",
                confidence=0.5 + (i * 0.05),
                reasoning=f"test decision {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"stat_corr_{i:03d}"
            )
            coordinator._add_to_history(decision)
        
        # 更新统计信息
        coordinator.stats.update({
            "total_decisions": 10,
            "soldier_decisions": 4,
            "commander_decisions": 3,
            "scholar_decisions": 3,
            "coordination_conflicts": 2,
            "concurrent_decisions": 5,
            "batch_decisions": 3
        })
        
        # 获取统计信息
        stats = coordinator.get_statistics()
        
        # 验证统计信息
        assert stats["total_decisions"] == 10
        assert stats["soldier_decisions"] == 4
        assert stats["commander_decisions"] == 3
        assert stats["scholar_decisions"] == 3
        assert stats["coordination_conflicts"] == 2
        
        # 验证百分比计算
        assert "soldier_percentage" in stats
        assert "commander_percentage" in stats
        assert "scholar_percentage" in stats
        
        # 验证平均置信度计算
        assert "average_confidence" in stats
        assert stats["average_confidence"] > 0
        
        # 验证其他统计信息
        assert "uptime_seconds" in stats
        assert "decisions_per_minute" in stats
        assert "coordination_active" in stats
    
    @pytest.mark.asyncio
    async def test_get_coordination_status_full(self, coordinator):
        """测试获取完整协调状态 - 覆盖行829-872, 891, 906, 912-913"""
        # 设置所有AI脑
        coordinator.soldier = MagicMock(spec=ISoldierEngine)
        coordinator.commander = MagicMock(spec=ICommanderEngine)
        coordinator.scholar = MagicMock(spec=IScholarEngine)
        coordinator.coordination_active = True
        
        # 添加一些决策历史
        for i in range(3):
            decision = BrainDecision(
                decision_id=f"status_{i:03d}",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning=f"status test {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"status_corr_{i:03d}"
            )
            coordinator._add_to_history(decision)
        
        # 更新统计信息
        coordinator.stats.update({
            "total_decisions": 3,
            "soldier_decisions": 3,
            "start_time": datetime.now()
        })
        
        # 获取协调状态
        status = await coordinator.get_coordination_status()
        
        # 验证状态信息
        assert status["coordination_active"] is True
        assert status["brains_available"]["soldier"] is True
        assert status["brains_available"]["commander"] is True
        assert status["brains_available"]["scholar"] is True
        assert status["decision_history_count"] == 3
        assert len(status["recent_decisions"]) == 3
        
        # 验证统计信息
        assert "stats" in status
        assert "uptime_seconds" in status["stats"]
        assert "decisions_per_minute" in status["stats"]
    
    @pytest.mark.asyncio
    async def test_shutdown(self, coordinator):
        """测试关闭协调器 - 覆盖行965"""
        # 添加一些待处理决策
        coordinator.pending_decisions["test1"] = BrainDecision(
            decision_id="shutdown_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="shutdown test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="shutdown_corr"
        )
        
        coordinator.coordination_active = True
        
        # 执行关闭
        await coordinator.shutdown()
        
        # 验证关闭状态
        assert coordinator.coordination_active is False
        assert len(coordinator.pending_decisions) == 0
    
    def test_decision_history_limit_enforcement(self, coordinator):
        """测试决策历史限制执行 - 覆盖行715-726"""
        # 设置较小的历史限制
        coordinator.max_history = 5
        
        # 添加超过限制的决策
        for i in range(10):
            decision = BrainDecision(
                decision_id=f"limit_{i:03d}",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning=f"limit test {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"limit_corr_{i:03d}"
            )
            coordinator._add_to_history(decision)
        
        # 验证历史记录被正确限制
        assert len(coordinator.decision_history) == 5
        
        # 验证保留的是最新的记录
        assert coordinator.decision_history[0].decision_id == "limit_005"
        assert coordinator.decision_history[-1].decision_id == "limit_009"
    
    def test_get_decision_history_with_filters(self, coordinator):
        """测试获取决策历史（带过滤器）- 覆盖行715-726"""
        # 添加不同类型的决策
        brain_types = ["soldier", "commander", "scholar"]
        for i in range(9):
            decision = BrainDecision(
                decision_id=f"filter_{i:03d}",
                primary_brain=brain_types[i % 3],
                action="buy",
                confidence=0.8,
                reasoning=f"filter test {i}",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"filter_corr_{i:03d}"
            )
            coordinator._add_to_history(decision)
        
        # 测试按脑类型过滤
        soldier_history = coordinator.get_decision_history(brain_filter="soldier")
        assert len(soldier_history) == 3
        for record in soldier_history:
            assert record["primary_brain"].startswith("soldier")
        
        # 测试限制数量
        limited_history = coordinator.get_decision_history(limit=5)
        assert len(limited_history) == 5
        
        # 测试组合过滤
        limited_commander = coordinator.get_decision_history(limit=2, brain_filter="commander")
        assert len(limited_commander) == 2
        for record in limited_commander:
            assert record["primary_brain"].startswith("commander")


class TestGlobalFunctions:
    """测试全局函数 - 覆盖行1034-1041, 1047-1048, 1053-1054"""
    
    @pytest.mark.asyncio
    async def test_get_ai_brain_coordinator_singleton(self):
        """测试获取全局AI三脑协调器单例"""
        # Mock全局依赖
        with patch('src.brain.ai_brain_coordinator.get_event_bus') as mock_get_event_bus, \
             patch('src.brain.ai_brain_coordinator.get_container') as mock_get_container:
            
            mock_event_bus = MagicMock(spec=EventBus)
            mock_container = MagicMock(spec=DIContainer)
            
            mock_get_event_bus.return_value = mock_event_bus
            mock_get_container.return_value = mock_container
            
            # Mock初始化
            with patch.object(AIBrainCoordinator, 'initialize') as mock_init:
                mock_init.return_value = None
                
                # 第一次调用
                coordinator1 = await get_ai_brain_coordinator()
                
                # 第二次调用应该返回同一个实例
                coordinator2 = await get_ai_brain_coordinator()
                
                # 验证单例模式
                assert coordinator1 is coordinator2
                
                # 验证初始化只被调用一次
                mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_ai_decision_convenience(self):
        """测试请求AI决策便捷函数"""
        with patch('src.brain.ai_brain_coordinator.get_ai_brain_coordinator') as mock_get_coordinator:
            mock_coordinator = MagicMock()
            mock_decision = BrainDecision(
                decision_id="convenience_001",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning="convenience test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="convenience_corr"
            )
            
            mock_coordinator.request_decision = AsyncMock(return_value=mock_decision)
            mock_get_coordinator.return_value = mock_coordinator
            
            # 调用便捷函数
            result = await request_ai_decision({"symbol": "000001.SZ"}, "soldier")
            
            # 验证结果
            assert result == mock_decision
            mock_coordinator.request_decision.assert_called_once_with({"symbol": "000001.SZ"}, "soldier")
    
    @pytest.mark.asyncio
    async def test_get_ai_coordination_status_convenience(self):
        """测试获取AI协调状态便捷函数"""
        with patch('src.brain.ai_brain_coordinator.get_ai_brain_coordinator') as mock_get_coordinator:
            mock_coordinator = MagicMock()
            mock_status = {
                "coordination_active": True,
                "brains_available": {"soldier": True, "commander": True, "scholar": True},
                "stats": {"total_decisions": 10}
            }
            
            mock_coordinator.get_coordination_status = AsyncMock(return_value=mock_status)
            mock_get_coordinator.return_value = mock_coordinator
            
            # 调用便捷函数
            result = await get_ai_coordination_status()
            
            # 验证结果
            assert result == mock_status
            mock_coordinator.get_coordination_status.assert_called_once()


class TestEdgeCasesAndErrorHandling:
    """测试边界情况和错误处理"""
    
    @pytest.fixture
    def coordinator(self):
        """创建协调器实例"""
        event_bus = MagicMock(spec=EventBus)
        container = MagicMock(spec=DIContainer)
        return AIBrainCoordinator(event_bus, container)
    
    @pytest.mark.asyncio
    async def test_trigger_strategy_adjustment(self, coordinator):
        """测试触发策略调整"""
        coordinator.event_bus.publish = AsyncMock()
        
        analysis_data = {
            "market_trend": "bullish",
            "confidence": 0.8,
            "recommendation": "increase_position"
        }
        
        await coordinator._trigger_strategy_adjustment(analysis_data)
        
        # 验证事件被发布
        coordinator.event_bus.publish.assert_called_once()
        call_args = coordinator.event_bus.publish.call_args[0][0]
        assert call_args.event_type == EventType.ANALYSIS_COMPLETED
        assert call_args.target_module == "commander"
        assert call_args.data["action"] == "adjust_strategy"
    
    @pytest.mark.asyncio
    async def test_trigger_factor_validation(self, coordinator):
        """测试触发因子验证"""
        coordinator.event_bus.publish = AsyncMock()
        
        analysis_data = {
            "factor_name": "momentum",
            "effectiveness": 0.75,
            "recommendation": "use_factor"
        }
        
        await coordinator._trigger_factor_validation(analysis_data)
        
        # 验证事件被发布
        coordinator.event_bus.publish.assert_called_once()
        call_args = coordinator.event_bus.publish.call_args[0][0]
        assert call_args.event_type == EventType.ANALYSIS_COMPLETED
        assert call_args.target_module == "auditor"
        assert call_args.data["action"] == "validate_factor"
    
    def test_statistics_with_zero_decisions(self, coordinator):
        """测试零决策时的统计信息"""
        # 确保没有决策历史
        coordinator.decision_history = []
        coordinator.stats["total_decisions"] = 0
        
        stats = coordinator.get_statistics()
        
        # 验证零除法被正确处理
        assert stats["average_confidence"] == 0.0
        assert stats["decisions_per_minute"] == 0.0
        
        # 验证百分比统计存在且合理
        if "soldier_percentage" in stats:
            assert stats["soldier_percentage"] == 0.0
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_empty_queue(self, coordinator):
        """测试空队列的批处理"""
        # 确保批处理队列为空
        coordinator.pending_batch = []
        
        # 处理空批次应该不会出错
        await coordinator._process_batch()
        
        # 验证没有异常抛出
        assert len(coordinator.pending_batch) == 0
    
    def test_fallback_decision_with_empty_context(self, coordinator):
        """测试空上下文的备用决策"""
        result = coordinator._create_fallback_decision({}, "test_corr", "soldier")
        
        # 验证备用决策的基本属性
        assert result.action == "hold"  # 默认保守策略
        assert result.confidence == 0.1  # 低置信度
        assert result.primary_brain == "coordinator_fallback_soldier"
        assert result.correlation_id == "test_corr"
        assert "备用决策" in result.reasoning