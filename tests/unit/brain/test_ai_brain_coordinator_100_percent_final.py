#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Brain Coordinator 100%覆盖率测试 - 最终版本

🧪 Test Engineer 专门负责达到100%测试覆盖率
目标：覆盖所有剩余的未覆盖代码行，确保100%覆盖率

遵循测试铁律：严禁跳过任何测试，强制要求100%覆盖率
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import EventBus, Event, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinator100PercentFinal:
    """100%覆盖率测试 - 最终版本"""

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
    async def test_initialization_failure_lines_97_116(self, coordinator):
        """测试初始化失败（97-116行）"""
        # 让容器解析抛出异常
        coordinator.container.resolve.side_effect = Exception("Container resolve failed")
        
        with pytest.raises(Exception, match="Container resolve failed"):
            await coordinator.initialize()

    @pytest.mark.asyncio
    async def test_partial_brain_registration_lines_121_135(self, coordinator):
        """测试部分脑注册（121-135行）"""
        # 只注册Soldier，不注册Commander和Scholar
        def mock_is_registered(interface):
            return interface == ISoldierEngine
        
        coordinator.container.is_registered.side_effect = mock_is_registered
        coordinator.container.resolve.return_value = MagicMock()
        
        await coordinator.initialize()
        
        # 验证只有Soldier被设置
        assert coordinator.soldier is not None
        assert coordinator.commander is None
        assert coordinator.scholar is None
    @pytest.mark.asyncio
    async def test_execute_decision_request_timeout_lines_181_226(self, coordinator):
        """测试决策请求超时处理（181-226行）"""
        # 模拟超时情况 - 让_request_decision_direct返回None
        with patch.object(coordinator, '_request_decision_direct', return_value=None), \
             patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            
            result = await coordinator._execute_decision_request({"test": "data"}, "soldier")
            
            # 验证超时处理逻辑
            assert result is not None
            assert result.action == "hold"  # 备用决策
            assert "备用决策" in result.reasoning
            
            # 验证logger.warning被调用
            warning_calls = mock_logger.warning.call_args_list
            timeout_warning_found = False
            for call_obj in warning_calls:
                call_args = call_obj[0][0]
                if "决策超时，生成备用决策" in call_args:
                    timeout_warning_found = True
                    break
            
            assert timeout_warning_found, f"未找到超时警告，实际调用: {warning_calls}"

    @pytest.mark.asyncio
    async def test_request_decision_direct_event_fallback_lines_276_294(self, coordinator):
        """测试直接决策请求事件回退（276-294行）"""
        # 设置所有AI脑为None，强制使用事件模式
        coordinator.soldier = None
        coordinator.commander = None
        coordinator.scholar = None
        
        # Mock事件发布成功
        coordinator.event_bus.publish = AsyncMock()
        
        # Mock等待决策返回结果
        test_decision = BrainDecision(
            decision_id="test_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="event mode test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="test_corr"
        )
        
        with patch.object(coordinator, '_wait_for_decision', return_value=test_decision):
            result = await coordinator._request_decision_direct({"test": "data"}, "soldier", "test_corr")
            
            # 验证事件发布被调用
            coordinator.event_bus.publish.assert_called_once()
            
            # 验证返回了正确的决策
            assert result == test_decision

    @pytest.mark.asyncio
    async def test_request_decision_with_batch_future_handling_lines_445_467(self, coordinator):
        """测试批处理Future处理（445-467行）"""
        coordinator.enable_batch_processing = True
        
        # Mock批处理锁和队列
        with patch.object(coordinator, 'batch_lock', new_callable=AsyncMock) as mock_lock, \
             patch.object(coordinator, '_process_batch', new_callable=AsyncMock) as mock_process:
            
            # 设置批处理队列达到批处理大小
            coordinator.pending_batch = [None] * (coordinator.batch_size - 1)  # 4个元素
            
            # 创建一个Future来模拟批处理结果
            future = asyncio.Future()
            future.set_result(BrainDecision(
                decision_id="batch_001",
                primary_brain="commander",
                action="buy",
                confidence=0.8,
                reasoning="batch test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="batch_corr"
            ))
            
            # Mock批处理添加逻辑
            async def mock_batch_add(*args):
                coordinator.pending_batch.append(("context", "commander", "batch_corr", future))
                return len(coordinator.pending_batch) >= coordinator.batch_size
            
            mock_lock.__aenter__ = AsyncMock(return_value=mock_lock)
            mock_lock.__aexit__ = AsyncMock(return_value=None)
            
            # 执行批处理决策
            with patch('asyncio.wait_for', return_value=future.result()):
                result = await coordinator._request_decision_with_batch({"test": "data"}, "commander", "batch_corr")
                
                # 验证结果
                assert result is not None
                assert result.action == "buy"

    @pytest.mark.asyncio
    async def test_process_batch_concurrent_execution_lines_475_476(self, coordinator):
        """测试批处理并发执行（475-476行）"""
        # 设置批处理队列
        futures = [asyncio.Future() for _ in range(3)]
        for future in futures:
            future.set_result(None)
        
        coordinator.pending_batch = [
            ({"test": f"data_{i}"}, "commander", f"corr_{i}", futures[i])
            for i in range(3)
        ]
        
        with patch.object(coordinator, '_process_batch_item', new_callable=AsyncMock) as mock_process_item, \
             patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
            
            mock_gather.return_value = [None, None, None]
            
            await coordinator._process_batch()
            
            # 验证并发执行
            mock_gather.assert_called_once()
            assert mock_process_item.call_count == 3

    @pytest.mark.asyncio
    async def test_request_decisions_batch_exception_handling_lines_606(self, coordinator):
        """测试批量决策异常处理（606行）"""
        # 模拟request_decision方法抛出异常
        async def mock_request_decision(context, primary_brain):
            if context.get("symbol") == "000002.SZ":
                raise Exception("Second request failed")
            elif context.get("symbol") == "000001.SZ":
                return BrainDecision(
                    decision_id="test_001",
                    primary_brain="soldier",
                    action="buy",
                    confidence=0.8,
                    reasoning="test",
                    supporting_data={},
                    timestamp=datetime.now(),
                    correlation_id="corr_001"
                )
            else:
                return BrainDecision(
                    decision_id="test_003",
                    primary_brain="soldier",
                    action="sell",
                    confidence=0.7,
                    reasoning="test",
                    supporting_data={},
                    timestamp=datetime.now(),
                    correlation_id="corr_003"
                )
        
        requests = [
            ({"symbol": "000001.SZ"}, "soldier"),
            ({"symbol": "000002.SZ"}, "soldier"),
            ({"symbol": "000003.SZ"}, "soldier")
        ]
        
        with patch.object(coordinator, 'request_decision', side_effect=mock_request_decision), \
             patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            
            results = await coordinator.request_decisions_batch(requests)
            
            # 验证结果
            assert len(results) == 3
            assert results[0].action == "buy"
            assert results[1].primary_brain.startswith("coordinator_fallback")  # 异常时的备用决策
            assert results[2].action == "sell"
            
            # 验证logger.error被调用
            error_calls = mock_logger.error.call_args_list
            batch_error_found = False
            for call_obj in error_calls:
                call_args = call_obj[0][0]
                if "批量决策失败" in call_args:
                    batch_error_found = True
                    break
            
            assert batch_error_found, f"未找到批量决策失败错误，实际调用: {error_calls}"
    @pytest.mark.asyncio
    async def test_wait_for_decision_success_with_cleanup_lines_526_545(self, coordinator):
        """测试等待决策成功并清理（526-545行）"""
        correlation_id = "test_success_corr"
        
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
            await asyncio.sleep(0.1)  # 模拟延迟
            coordinator.pending_decisions[correlation_id] = test_decision
        
        # 启动延迟添加任务
        asyncio.create_task(delayed_add())
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            result = await coordinator._wait_for_decision(correlation_id, timeout=1.0)
            
            # 验证结果
            assert result == test_decision
            assert correlation_id not in coordinator.pending_decisions  # 应该被清理
            
            # 验证logger.debug被调用
            debug_calls = mock_logger.debug.call_args_list
            success_debug_found = False
            for call_obj in debug_calls:
                call_args = call_obj[0][0]
                if "收到决策结果" in call_args and correlation_id in call_args:
                    success_debug_found = True
                    break
            
            assert success_debug_found, f"未找到成功调试信息，实际调用: {debug_calls}"

    @pytest.mark.asyncio
    async def test_handle_analysis_completed_unknown_type_lines_637_676(self, coordinator):
        """测试处理未知分析类型（637-676行）"""
        # 测试未知分析类型
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="test",
            target_module="coordinator",
            data={"analysis_type": "unknown_analysis", "result": "test"}
        )
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行事件处理
            await coordinator._handle_analysis_completed(event)
            
            # 验证logger.debug被调用
            debug_calls = mock_logger.debug.call_args_list
            analysis_debug_found = False
            for call_obj in debug_calls:
                call_args = call_obj[0][0]
                if "Analysis completed" in call_args and "unknown_analysis" in call_args:
                    analysis_debug_found = True
                    break
            
            assert analysis_debug_found, f"未找到分析完成调试信息，实际调用: {debug_calls}"

    @pytest.mark.asyncio
    async def test_handle_analysis_completed_exception_lines_687_696(self, coordinator):
        """测试分析完成事件处理异常（687-696行）"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="test",
            target_module="coordinator",
            data=None  # 这会导致异常
        )
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行事件处理，应该捕获异常
            await coordinator._handle_analysis_completed(event)
            
            # 验证logger.error被调用
            error_calls = mock_logger.error.call_args_list
            analysis_error_found = False
            for call_obj in error_calls:
                call_args = call_obj[0][0]
                if "Failed to handle analysis completed" in call_args:
                    analysis_error_found = True
                    break
            
            assert analysis_error_found, f"未找到分析完成失败错误，实际调用: {error_calls}"

    @pytest.mark.asyncio
    async def test_handle_factor_discovered_exception_lines_715_726(self, coordinator):
        """测试因子发现事件处理异常（715-726行）"""
        # 创建会导致异常的事件
        event = Event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="test",
            target_module="coordinator",
            data={"factor_info": None}  # 这会导致异常
        )
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            # 执行事件处理，应该捕获异常
            await coordinator._handle_factor_discovered(event)
            
            # 验证logger.error被调用
            error_calls = mock_logger.error.call_args_list
            factor_error_found = False
            for call_obj in error_calls:
                call_args = call_obj[0][0]
                if "Failed to handle factor discovered" in call_args:
                    factor_error_found = True
                    break
            
            assert factor_error_found, f"未找到因子发现失败错误，实际调用: {error_calls}"

    def test_create_fallback_decision_with_primary_brain_lines_763_764(self, coordinator):
        """测试创建备用决策指定主脑（763-764行）"""
        context = {"test": "data"}
        correlation_id = "test_corr"
        primary_brain = "scholar"
        
        decision = coordinator._create_fallback_decision(context, correlation_id, primary_brain)
        
        # 验证主脑被正确设置
        assert decision.primary_brain == f"coordinator_fallback_{primary_brain}"
        assert decision.supporting_data["original_brain"] == primary_brain

    def test_add_to_history_debug_logging_lines_786_789(self, coordinator):
        """测试添加历史记录调试日志（786-789行）"""
        decision = BrainDecision(
            decision_id="test_001",
            primary_brain="soldier",
            action="buy",
            confidence=0.8,
            reasoning="test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="corr_001"
        )
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            coordinator._add_to_history(decision)
            
            # 验证logger.debug被调用
            debug_calls = mock_logger.debug.call_args_list
            history_debug_found = False
            for call_obj in debug_calls:
                call_args = call_obj[0][0]
                if "添加决策历史" in call_args and "test_001" in call_args:
                    history_debug_found = True
                    break
            
            assert history_debug_found, f"未找到历史记录调试信息，实际调用: {debug_calls}"
    def test_add_to_history_overflow_cleanup_lines_815_816(self, coordinator):
        """测试历史记录溢出清理（815-816行）"""
        coordinator.max_history = 3
        
        # 添加4个决策，触发溢出清理
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            for i in range(4):
                decision = BrainDecision(
                    decision_id=f"test_{i:03d}",
                    primary_brain="soldier",
                    action="buy",
                    confidence=0.8,
                    reasoning="test",
                    supporting_data={},
                    timestamp=datetime.now(),
                    correlation_id=f"corr_{i:03d}"
                )
                coordinator._add_to_history(decision)
            
            # 验证只保留最后3个
            assert len(coordinator.decision_history) == 3
            assert coordinator.decision_history[0].decision_id == "test_001"
            assert coordinator.decision_history[-1].decision_id == "test_003"
            
            # 验证logger.debug被调用（溢出清理）
            debug_calls = mock_logger.debug.call_args_list
            overflow_debug_found = False
            for call_obj in debug_calls:
                call_args = call_obj[0][0]
                if "历史记录超限，移除" in call_args:
                    overflow_debug_found = True
                    break
            
            assert overflow_debug_found, f"未找到溢出清理调试信息，实际调用: {debug_calls}"

    @pytest.mark.asyncio
    async def test_resolve_conflicts_high_confidence_decision_lines_836_847(self, coordinator):
        """测试高置信度决策优先（836-847行）"""
        decisions = [
            BrainDecision(
                decision_id="low_conf",
                primary_brain="commander",
                action="sell",
                confidence=0.6,
                reasoning="low confidence",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="low_corr"
            ),
            BrainDecision(
                decision_id="high_conf",
                primary_brain="soldier",  # 改为soldier，优先级最高
                action="buy",
                confidence=0.85,  # 高置信度 > 0.8
                reasoning="high confidence",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="high_corr"
            )
        ]
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            result = await coordinator.resolve_conflicts(decisions)
            
            # 验证高置信度决策被选中
            # 由于soldier优先级最高且置信度>0.8，应该被选中
            assert result.decision_id == "high_conf"
            assert result.confidence == 0.85
            
            # 验证logger.info被调用
            info_calls = mock_logger.info.call_args_list
            high_conf_info_found = False
            for call_obj in info_calls:
                call_args = call_obj[0][0]
                if "高置信度决策采用" in call_args and "0.85" in call_args:
                    high_conf_info_found = True
                    break
            
            assert high_conf_info_found, f"未找到高置信度决策信息，实际调用: {info_calls}"

    def test_create_conservative_decision_default_case_lines_884_955(self, coordinator):
        """测试保守决策默认情况（884-955行）"""
        # 创建不匹配任何特殊情况的决策
        decisions = [
            BrainDecision(
                decision_id="test_001",
                primary_brain="soldier",
                action="unknown_action",  # 不匹配任何特殊情况
                confidence=0.6,
                reasoning="test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="corr_001"
            ),
            BrainDecision(
                decision_id="test_002",
                primary_brain="commander",
                action="custom_action",  # 不匹配任何特殊情况
                confidence=0.7,
                reasoning="test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="corr_002"
            )
        ]
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            result = coordinator._create_conservative_decision(decisions)
            
            # 验证默认保守策略
            assert result.action == "hold"
            assert "决策冲突，采用默认保守策略" in result.reasoning
            assert result.primary_brain == "coordinator_conflict_resolution"
            
            # 验证平均置信度计算（降低60%）
            expected_confidence = (0.6 + 0.7) / 2 * 0.6  # 平均后降低60%
            assert abs(result.confidence - expected_confidence) < 0.01
            
            # 验证logger.info被调用
            info_calls = mock_logger.info.call_args_list
            conservative_info_found = False
            for call_obj in info_calls:
                call_args = call_obj[0][0]
                if "生成保守决策" in call_args:
                    conservative_info_found = True
                    break
            
            assert conservative_info_found, f"未找到保守决策信息，实际调用: {info_calls}"

    def test_get_statistics_with_zero_decisions_lines_963_965(self, coordinator):
        """测试零决策时的统计信息（963-965行）"""
        # 确保没有决策
        coordinator.stats["total_decisions"] = 0
        coordinator.decision_history = []
        
        stats = coordinator.get_statistics()
        
        # 验证零决策时的计算 - 检查实际返回的键
        # 当total_decisions为0时，brain_percentages字典为空
        assert stats["total_decisions"] == 0
        assert stats["average_confidence"] == 0.0
        assert stats["conflict_rate"] == 0.0
        assert stats["decisions_per_minute"] == 0.0
        
        # 验证百分比统计不存在（因为total_decisions为0）
        # 根据源代码，当total_decisions为0时，brain_percentages为空字典
        assert "soldier_percentage" not in stats
        assert "commander_percentage" not in stats
        assert "scholar_percentage" not in stats

    @pytest.mark.asyncio
    async def test_get_coordination_status_duplicate_method_lines_1021_1023(self, coordinator):
        """测试协调状态重复方法（1021-1023行）"""
        # 设置一些状态
        coordinator.coordination_active = True
        coordinator.soldier = MagicMock()
        coordinator.commander = None
        coordinator.scholar = MagicMock()
        
        # 添加一些决策历史
        for i in range(3):
            decision = BrainDecision(
                decision_id=f"test_{i:03d}",
                primary_brain="soldier",
                action="buy",
                confidence=0.8,
                reasoning="test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id=f"corr_{i:03d}"
            )
            coordinator.decision_history.append(decision)
        
        status = await coordinator.get_coordination_status()
        
        # 验证状态信息
        assert status["coordination_active"] is True
        assert status["brains_available"]["soldier"] is True
        assert status["brains_available"]["commander"] is False
        assert status["brains_available"]["scholar"] is True
        assert len(status["recent_decisions"]) == 3

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_lines_1047_1048(self, coordinator):
        """测试关闭清理（1047-1048行）"""
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
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            await coordinator.shutdown()
            
            # 验证状态被清理
            assert coordinator.coordination_active is False
            assert len(coordinator.pending_decisions) == 0
            
            # 验证logger.info被调用
            info_calls = mock_logger.info.call_args_list
            shutdown_info_found = False
            for call_obj in info_calls:
                call_args = call_obj[0][0]
                if "Shutdown completed" in call_args:
                    shutdown_info_found = True
                    break
            
            assert shutdown_info_found, f"未找到关闭完成信息，实际调用: {info_calls}"

    @pytest.mark.asyncio
    async def test_global_coordinator_singleton_lines_1053_1054(self):
        """测试全局协调器单例（1053-1054行）"""
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
            
            # 第一次调用
            coordinator1 = await module.get_ai_brain_coordinator()
            
            # 第二次调用应该返回同一个实例
            coordinator2 = await module.get_ai_brain_coordinator()
            
            assert coordinator1 is coordinator2
            
            # 验证初始化只被调用一次
            assert mock_get_event_bus.call_count == 1
            assert mock_get_container.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])