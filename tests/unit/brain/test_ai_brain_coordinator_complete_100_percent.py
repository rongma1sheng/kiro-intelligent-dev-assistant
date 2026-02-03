#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 完整100%覆盖率测试

🧪 Test Engineer 专门负责达到100%测试覆盖率
目标：覆盖所有剩余的未覆盖代码行，确保100%覆盖率

遵循测试铁律：严禁跳过任何测试，强制要求100%覆盖率

根据覆盖率报告，需要覆盖的未覆盖行：
103, 106, 155-164, 179, 190, 197-205, 218-226, 243-258, 261-274, 277-290, 
310-312, 351->355, 359-361, 372, 399-431, 511-517, 521-545, 558, 561, 575, 
590, 606, 644-646, 649-651, 715-726, 763-764, 768, 792-816, 834-835, 838-839, 
842-843, 891, 901, 906, 912-913, 1047-1048, 1053-1054
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision, get_ai_brain_coordinator, request_ai_decision, get_ai_coordination_status
from src.core.dependency_container import DIContainer
from src.infra.event_bus import EventBus, Event, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorComplete100Percent:
    """完整100%覆盖率测试"""

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
    async def test_initialization_container_resolve_exception_lines_103_106(self, coordinator):
        """测试初始化时容器解析异常（103, 106行）"""
        # 让容器解析抛出异常
        coordinator.container.resolve.side_effect = Exception("Container resolve failed")
        
        with pytest.raises(Exception, match="Container resolve failed"):
            await coordinator.initialize()

    @pytest.mark.asyncio
    async def test_setup_event_subscriptions_lines_155_164(self, coordinator):
        """测试设置事件订阅（155-164行）"""
        await coordinator._setup_event_subscriptions()
        
        # 验证所有事件订阅被调用
        assert coordinator.event_bus.subscribe.call_count == 3
        
        # 验证订阅的事件类型
        calls = coordinator.event_bus.subscribe.call_args_list
        event_types = [call[0][0] for call in calls]
        
        assert EventType.DECISION_MADE in event_types
        assert EventType.ANALYSIS_COMPLETED in event_types
        assert EventType.FACTOR_DISCOVERED in event_types

    @pytest.mark.asyncio
    async def test_request_decision_invalid_brain_lines_179_190(self, coordinator):
        """测试请求决策时无效的脑类型（179, 190行）"""
        with pytest.raises(ValueError, match="不支持的决策脑"):
            await coordinator.request_decision({"test": "data"}, "invalid_brain")

    @pytest.mark.asyncio
    async def test_execute_decision_request_exception_handling_lines_197_205(self, coordinator):
        """测试执行决策请求异常处理（197-205行）"""
        # 模拟_request_decision_direct抛出异常
        with patch.object(coordinator, '_request_decision_direct', side_effect=Exception("Direct request failed")):
            result = await coordinator._execute_decision_request({"test": "data"}, "soldier")
            
            # 验证返回备用决策
            assert result is not None
            assert result.primary_brain.startswith("coordinator_fallback")
            assert "备用决策" in result.reasoning

    @pytest.mark.asyncio
    async def test_execute_decision_request_timeout_fallback_lines_218_226(self, coordinator):
        """测试执行决策请求超时备用决策（218-226行）"""
        # 模拟超时情况 - 让_request_decision_direct返回None
        with patch.object(coordinator, '_request_decision_direct', return_value=None):
            result = await coordinator._execute_decision_request({"test": "data"}, "soldier")
            
            # 验证超时处理逻辑
            assert result is not None
            assert result.action == "hold"  # 备用决策
            assert "备用决策" in result.reasoning

    @pytest.mark.asyncio
    async def test_request_decision_direct_soldier_success_lines_243_258(self, coordinator):
        """测试直接请求Soldier决策成功（243-258行）"""
        # 设置Soldier实例
        mock_soldier = AsyncMock()
        mock_soldier.decide.return_value = {
            "decision": {
                "action": "buy",
                "confidence": 0.8,
                "reasoning": "test reasoning"
            },
            "metadata": {"test": "data"}
        }
        coordinator.soldier = mock_soldier
        
        result = await coordinator._request_decision_direct({"test": "data"}, "soldier", "test_corr")
        
        # 验证结果
        assert result is not None
        assert result.action == "buy"
        assert result.confidence == 0.8
        assert result.primary_brain == "soldier"

    @pytest.mark.asyncio
    async def test_request_decision_direct_commander_success_lines_261_274(self, coordinator):
        """测试直接请求Commander决策成功（261-274行）"""
        # 设置Commander实例
        mock_commander = AsyncMock()
        mock_commander.analyze.return_value = {
            "recommendation": "sell",
            "confidence": 0.7,
            "analysis": "test analysis"
        }
        coordinator.commander = mock_commander
        
        result = await coordinator._request_decision_direct({"test": "data"}, "commander", "test_corr")
        
        # 验证结果
        assert result is not None
        assert result.action == "sell"
        assert result.confidence == 0.7
        assert result.primary_brain == "commander"

    @pytest.mark.asyncio
    async def test_request_decision_direct_scholar_success_lines_277_290(self, coordinator):
        """测试直接请求Scholar决策成功（277-290行）"""
        # 设置Scholar实例
        mock_scholar = AsyncMock()
        mock_scholar.research.return_value = {
            "recommendation": "hold",
            "confidence": 0.6,
            "research_summary": "test research"
        }
        coordinator.scholar = mock_scholar
        
        result = await coordinator._request_decision_direct({"test": "data"}, "scholar", "test_corr")
        
        # 验证结果
        assert result is not None
        assert result.action == "hold"
        assert result.confidence == 0.6
        assert result.primary_brain == "scholar"

    @pytest.mark.asyncio
    async def test_request_decision_direct_event_publish_exception_lines_310_312(self, coordinator):
        """测试直接请求决策事件发布异常（310-312行）"""
        # 设置所有AI脑为None，强制使用事件模式
        coordinator.soldier = None
        coordinator.commander = None
        coordinator.scholar = None
        
        # Mock事件发布失败
        coordinator.event_bus.publish.side_effect = Exception("Event publish failed")
        
        result = await coordinator._request_decision_direct({"test": "data"}, "soldier", "test_corr")
        
        # 验证返回None
        assert result is None

    @pytest.mark.asyncio
    async def test_request_decision_with_batch_timeout_lines_351_355_359_361(self, coordinator):
        """测试批处理决策超时（351->355, 359-361行）"""
        coordinator.enable_batch_processing = True
        
        # Mock批处理锁
        with patch.object(coordinator, 'batch_lock', new_callable=AsyncMock) as mock_lock:
            mock_lock.__aenter__ = AsyncMock(return_value=mock_lock)
            mock_lock.__aexit__ = AsyncMock(return_value=None)
            
            # Mock asyncio.wait_for超时
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                result = await coordinator._request_decision_with_batch({"test": "data"}, "commander", "test_corr")
                
                # 验证超时返回None
                assert result is None

    @pytest.mark.asyncio
    async def test_process_batch_empty_queue_lines_372(self, coordinator):
        """测试处理空批处理队列（372行）"""
        # 确保批处理队列为空
        coordinator.pending_batch = []
        
        with patch.object(coordinator, 'batch_lock', new_callable=AsyncMock) as mock_lock:
            mock_lock.__aenter__ = AsyncMock(return_value=mock_lock)
            mock_lock.__aexit__ = AsyncMock(return_value=None)
            
            # 执行批处理，应该直接返回
            await coordinator._process_batch()
            
            # 验证没有进一步处理
            assert len(coordinator.pending_batch) == 0

    @pytest.mark.asyncio
    async def test_process_batch_item_event_publish_exception_lines_399_431(self, coordinator):
        """测试批处理项目事件发布异常（399-431行）"""
        future = asyncio.Future()
        
        # Mock事件发布失败
        coordinator.event_bus.publish.side_effect = Exception("Event publish failed")
        
        await coordinator._process_batch_item({"test": "data"}, "commander", "test_corr", future)
        
        # 验证Future被设置为异常
        assert future.done()
        assert isinstance(future.exception(), Exception)

    @pytest.mark.asyncio
    async def test_wait_for_decision_timeout_cleanup_lines_511_517(self, coordinator):
        """测试等待决策超时清理（511-517行）"""
        correlation_id = "test_timeout_corr"
        
        # 预设一个决策，但不会被找到（模拟超时）
        coordinator.pending_decisions["other_corr"] = BrainDecision(
            decision_id="other_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="other",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="other_corr"
        )
        
        result = await coordinator._wait_for_decision(correlation_id, timeout=0.1)
        
        # 验证超时返回None
        assert result is None
        
        # 验证残留决策被清理（如果存在）
        assert correlation_id not in coordinator.pending_decisions

    @pytest.mark.asyncio
    async def test_wait_for_decision_found_in_loop_lines_521_545(self, coordinator):
        """测试在循环中找到决策（521-545行）"""
        correlation_id = "test_found_corr"
        
        # 预设决策结果
        test_decision = BrainDecision(
            decision_id="test_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        # 在第二次检查时添加决策
        async def delayed_add():
            await asyncio.sleep(0.05)  # 短暂延迟
            coordinator.pending_decisions[correlation_id] = test_decision
        
        # 启动延迟添加任务
        asyncio.create_task(delayed_add())
        
        result = await coordinator._wait_for_decision(correlation_id, timeout=1.0)
        
        # 验证结果
        assert result == test_decision
        assert correlation_id not in coordinator.pending_decisions  # 应该被清理

    @pytest.mark.asyncio
    async def test_handle_brain_decision_missing_correlation_id_lines_558_561(self, coordinator):
        """测试处理脑决策事件缺少correlation_id（558, 561行）"""
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            data={
                "action": "decision_result",
                "decision_id": "test_001",
                "primary_brain": "soldier",
                "decision_action": "buy",
                "confidence": 0.8,
                "reasoning": "test",
                "supporting_data": {},
                # 缺少correlation_id
            }
        )
        
        await coordinator._handle_brain_decision(event)
        
        # 验证没有添加到pending_decisions（因为没有correlation_id）
        assert len(coordinator.pending_decisions) == 0

    @pytest.mark.asyncio
    async def test_handle_brain_decision_exception_lines_575(self, coordinator):
        """测试处理脑决策事件异常（575行）"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.DECISION_MADE,
            source_module="soldier",
            target_module="coordinator",
            data=None  # 这会导致异常
        )
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            await coordinator._handle_brain_decision(event)
            
            # 验证logger.error被调用
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_analysis_completed_market_analysis_lines_590(self, coordinator):
        """测试处理市场分析完成事件（590行）"""
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="commander",
            target_module="coordinator",
            data={
                "analysis_type": "market_analysis",
                "result": "test market analysis"
            }
        )
        
        with patch.object(coordinator, '_trigger_strategy_adjustment', new_callable=AsyncMock) as mock_trigger:
            await coordinator._handle_analysis_completed(event)
            
            # 验证触发策略调整
            mock_trigger.assert_called_once_with(event.data)

    @pytest.mark.asyncio
    async def test_handle_analysis_completed_factor_analysis_lines_606(self, coordinator):
        """测试处理因子分析完成事件（606行）"""
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="scholar",
            target_module="coordinator",
            data={
                "analysis_type": "factor_analysis",
                "result": "test factor analysis"
            }
        )
        
        with patch.object(coordinator, '_trigger_factor_validation', new_callable=AsyncMock) as mock_trigger:
            await coordinator._handle_analysis_completed(event)
            
            # 验证触发因子验证
            mock_trigger.assert_called_once_with(event.data)

    @pytest.mark.asyncio
    async def test_trigger_strategy_adjustment_lines_644_646(self, coordinator):
        """测试触发策略调整（644-646行）"""
        analysis_data = {"test": "market analysis data"}
        
        await coordinator._trigger_strategy_adjustment(analysis_data)
        
        # 验证事件发布
        coordinator.event_bus.publish.assert_called_once()
        
        # 验证事件内容
        call_args = coordinator.event_bus.publish.call_args[0][0]
        assert call_args.event_type == EventType.ANALYSIS_COMPLETED
        assert call_args.target_module == "commander"
        assert call_args.data["action"] == "adjust_strategy"

    @pytest.mark.asyncio
    async def test_trigger_factor_validation_lines_649_651(self, coordinator):
        """测试触发因子验证（649-651行）"""
        analysis_data = {"test": "factor analysis data"}
        
        await coordinator._trigger_factor_validation(analysis_data)
        
        # 验证事件发布
        coordinator.event_bus.publish.assert_called_once()
        
        # 验证事件内容
        call_args = coordinator.event_bus.publish.call_args[0][0]
        assert call_args.event_type == EventType.ANALYSIS_COMPLETED
        assert call_args.target_module == "auditor"
        assert call_args.data["action"] == "validate_factor"

    @pytest.mark.asyncio
    async def test_handle_factor_discovered_success_lines_715_726(self, coordinator):
        """测试处理因子发现事件成功（715-726行）"""
        event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="scholar",
            target_module="coordinator",
            data={
                "factor_info": {
                    "name": "test_factor",
                    "description": "test factor description"
                }
            }
        )
        
        await coordinator._handle_factor_discovered(event)
        
        # 验证事件发布
        coordinator.event_bus.publish.assert_called_once()
        
        # 验证事件内容
        call_args = coordinator.event_bus.publish.call_args[0][0]
        assert call_args.event_type == EventType.ANALYSIS_COMPLETED
        assert call_args.target_module == "auditor"
        assert call_args.data["action"] == "validate_factor"

    def test_create_fallback_decision_high_position_lines_763_764_768(self, coordinator):
        """测试创建备用决策高仓位情况（763-764, 768行）"""
        context = {"current_position": 0.9}  # 高仓位
        correlation_id = "test_corr"
        
        decision = coordinator._create_fallback_decision(context, correlation_id)
        
        # 验证高仓位时的备用策略
        assert decision.action == "reduce"
        assert "当前仓位过高" in decision.reasoning
        assert decision.confidence == 0.3

    def test_create_fallback_decision_high_risk_lines_792_816(self, coordinator):
        """测试创建备用决策高风险情况（792-816行）"""
        context = {"risk_level": "high"}  # 高风险
        correlation_id = "test_corr"
        
        decision = coordinator._create_fallback_decision(context, correlation_id)
        
        # 验证高风险时的备用策略
        assert decision.action == "sell"
        assert "风险过高" in decision.reasoning
        assert decision.confidence == 0.4

    @pytest.mark.asyncio
    async def test_resolve_conflicts_empty_decisions_lines_834_835(self, coordinator):
        """测试解决冲突空决策列表（834-835行）"""
        decisions = []
        
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证返回备用决策
        assert result is not None
        assert result.primary_brain.startswith("coordinator_fallback")

    @pytest.mark.asyncio
    async def test_resolve_conflicts_single_decision_lines_838_839(self, coordinator):
        """测试解决冲突单个决策（838-839行）"""
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
        
        result = await coordinator.resolve_conflicts([decision])
        
        # 验证直接返回单个决策
        assert result == decision

    @pytest.mark.asyncio
    async def test_resolve_conflicts_no_high_confidence_lines_842_843(self, coordinator):
        """测试解决冲突无高置信度决策（842-843行）"""
        decisions = [
            BrainDecision(
                decision_id="low_conf_1",
                primary_brain="commander",
                action="sell",
                confidence=0.6,  # 低置信度
                reasoning="low confidence 1",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="low_corr_1"
            ),
            BrainDecision(
                decision_id="low_conf_2",
                primary_brain="soldier",
                action="buy",
                confidence=0.75,  # 稍高置信度，避免冲突检测
                reasoning="low confidence 2",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="low_corr_2"
            )
        ]
        
        result = await coordinator.resolve_conflicts(decisions)
        
        # 验证返回最高优先级决策（soldier优先级最高）
        # 由于置信度差异>0.1，不会触发冲突检测，返回最高优先级决策
        assert result.decision_id == "low_conf_2"
        assert result.primary_brain == "soldier"

    def test_create_conservative_decision_buy_sell_conflict_lines_891(self, coordinator):
        """测试创建保守决策买卖冲突（891行）"""
        decisions = [
            BrainDecision(
                decision_id="buy_001",
                primary_brain="soldier",
                action="buy",
                confidence=0.6,
                reasoning="buy decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="buy_corr"
            ),
            BrainDecision(
                decision_id="sell_001",
                primary_brain="commander",
                action="sell",
                confidence=0.7,
                reasoning="sell decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="sell_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        # 验证买卖冲突时的保守策略
        assert result.action == "hold"
        assert "买卖决策冲突" in result.reasoning

    def test_create_conservative_decision_buy_hold_case_lines_901(self, coordinator):
        """测试创建保守决策买入持有情况（901行）"""
        decisions = [
            BrainDecision(
                decision_id="buy_001",
                primary_brain="soldier",
                action="buy",
                confidence=0.6,
                reasoning="buy decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="buy_corr"
            ),
            BrainDecision(
                decision_id="hold_001",
                primary_brain="commander",
                action="hold",
                confidence=0.7,
                reasoning="hold decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="hold_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        # 验证买入/持有时的保守策略
        assert result.action == "hold"
        assert "买入/持有决策" in result.reasoning

    def test_create_conservative_decision_reduce_case_lines_906(self, coordinator):
        """测试创建保守决策减仓情况（906行）"""
        decisions = [
            BrainDecision(
                decision_id="buy_001",
                primary_brain="soldier",
                action="buy",
                confidence=0.6,
                reasoning="buy decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="buy_corr"
            ),
            BrainDecision(
                decision_id="reduce_001",
                primary_brain="commander",
                action="reduce",
                confidence=0.7,
                reasoning="reduce decision",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="reduce_corr"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        # 验证有减仓建议时的策略
        assert result.action == "reduce"
        assert "存在减仓建议" in result.reasoning

    def test_create_conservative_decision_confidence_calculation_lines_912_913(self, coordinator):
        """测试创建保守决策置信度计算（912-913行）"""
        decisions = [
            BrainDecision(
                decision_id="test_001",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning="test 1",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="corr_001"
            ),
            BrainDecision(
                decision_id="test_002",
                primary_brain="commander",
                action="sell",
                confidence=0.6,
                reasoning="test 2",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="corr_002"
            )
        ]
        
        result = coordinator._create_conservative_decision(decisions)
        
        # 验证平均置信度计算（降低60%）
        expected_confidence = (0.8 + 0.6) / 2 * 0.6  # 平均后降低60%
        assert abs(result.confidence - expected_confidence) < 0.01

    @pytest.mark.asyncio
    async def test_shutdown_lines_1047_1048(self, coordinator):
        """测试关闭协调器（1047-1048行）"""
        # 设置一些状态
        coordinator.coordination_active = True
        coordinator.pending_decisions["test"] = BrainDecision(
            decision_id="test_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="corr_001"
        )
        
        await coordinator.shutdown()
        
        # 验证状态被清理
        assert coordinator.coordination_active is False
        assert len(coordinator.pending_decisions) == 0

    @pytest.mark.asyncio
    async def test_global_coordinator_initialization_lines_1053_1054(self):
        """测试全局协调器初始化（1053-1054行）"""
        # 重置全局变量
        import src.brain.ai_brain_coordinator as module
        module._global_coordinator = None
        
        # Mock依赖
        with patch('src.brain.ai_brain_coordinator.get_event_bus') as mock_get_event_bus, \
             patch('src.brain.ai_brain_coordinator.get_container') as mock_get_container:
            
            mock_event_bus = AsyncMock()
            mock_container = MagicMock()
            mock_get_event_bus.return_value = mock_event_bus
            mock_get_container.return_value = mock_container
            
            # 配置容器
            mock_container.is_registered.return_value = False
            
            # 调用全局协调器获取函数
            coordinator = await module.get_ai_brain_coordinator()
            
            # 验证协调器被创建和初始化
            assert coordinator is not None
            assert module._global_coordinator is coordinator

    @pytest.mark.asyncio
    async def test_convenience_functions(self):
        """测试便捷函数"""
        # 重置全局变量
        import src.brain.ai_brain_coordinator as module
        module._global_coordinator = None
        
        # Mock依赖
        with patch('src.brain.ai_brain_coordinator.get_event_bus') as mock_get_event_bus, \
             patch('src.brain.ai_brain_coordinator.get_container') as mock_get_container:
            
            mock_event_bus = AsyncMock()
            mock_container = MagicMock()
            mock_get_event_bus.return_value = mock_event_bus
            mock_get_container.return_value = mock_container
            
            # 配置容器
            mock_container.is_registered.return_value = False
            
            # 测试request_ai_decision便捷函数
            with patch.object(module.AIBrainCoordinator, 'request_decision', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = BrainDecision(
                    decision_id="test_001",
                    primary_brain="soldier",
                    action="buy",
                    confidence=0.8,
                    reasoning="test",
                    supporting_data={},
                    timestamp=datetime.now(),
                    correlation_id="corr_001"
                )
                
                result = await request_ai_decision({"test": "data"})
                assert result is not None
                assert result.action == "buy"
            
            # 测试get_ai_coordination_status便捷函数
            with patch.object(module.AIBrainCoordinator, 'get_coordination_status', new_callable=AsyncMock) as mock_status:
                mock_status.return_value = {"coordination_active": True}
                
                status = await get_ai_coordination_status()
                assert status["coordination_active"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])