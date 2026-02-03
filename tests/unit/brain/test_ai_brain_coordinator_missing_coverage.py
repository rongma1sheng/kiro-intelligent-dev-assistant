"""
AI大脑协调器缺失覆盖率测试
专门针对未覆盖的代码行进行测试，确保100%覆盖率
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import ISoldierEngine, ICommanderEngine, IScholarEngine


@pytest.fixture
def mock_event_bus():
    """创建模拟事件总线"""
    event_bus = MagicMock(spec=EventBus)
    event_bus.subscribe = AsyncMock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def mock_container():
    """创建模拟依赖容器"""
    container = MagicMock(spec=DIContainer)
    
    # 创建模拟的AI脑实例
    mock_soldier = AsyncMock(spec=ISoldierEngine)
    mock_commander = AsyncMock(spec=ICommanderEngine)
    mock_scholar = AsyncMock(spec=IScholarEngine)
    
    # 配置容器返回模拟实例
    container.is_registered.return_value = True
    container.resolve.side_effect = lambda interface: {
        ISoldierEngine: mock_soldier,
        ICommanderEngine: mock_commander,
        IScholarEngine: mock_scholar
    }.get(interface)
    
    return container


@pytest.fixture
async def coordinator(mock_event_bus, mock_container):
    """创建协调器实例"""
    coordinator = AIBrainCoordinator(mock_event_bus, mock_container)
    await coordinator.initialize()
    return coordinator


class TestAIBrainCoordinatorMissingCoverage:
    """AI大脑协调器缺失覆盖率测试类"""

    @pytest.mark.asyncio
    async def test_initialization_exception_lines_114_116(self, mock_event_bus, mock_container):
        """测试初始化异常处理 (行114-116)"""
        # 让容器解析抛出异常
        mock_container.resolve.side_effect = Exception("Container resolve failed")
        
        coordinator = AIBrainCoordinator(mock_event_bus, mock_container)
        
        # 验证异常被正确抛出和记录
        with pytest.raises(Exception, match="Container resolve failed"):
            await coordinator.initialize()

    @pytest.mark.asyncio
    async def test_concurrent_semaphore_locked_lines_155_164(self, coordinator):
        """测试并发信号量锁定检测 (行155-164)"""
        # 模拟信号量被锁定
        coordinator.concurrent_semaphore.locked = MagicMock(return_value=True)
        
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 记录初始统计
        initial_hits = coordinator.stats.get("concurrent_limit_hits", 0)
        
        # 执行决策请求
        result = await coordinator.request_decision(context, "soldier")
        
        # 验证并发限制统计被更新
        assert coordinator.stats["concurrent_limit_hits"] > initial_hits
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_brain_type_lines_177_179(self, coordinator):
        """测试无效决策脑类型 (行177-179)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 测试无效的决策脑类型
        with pytest.raises(ValueError, match="不支持的决策脑"):
            await coordinator.request_decision(context, "invalid_brain")

    @pytest.mark.asyncio
    async def test_batch_processing_path_lines_188_191(self, coordinator):
        """测试批处理路径选择 (行188-191)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 启用批处理并测试commander
        coordinator.enable_batch_processing = True
        
        # 模拟批处理方法
        coordinator._request_decision_with_batch = AsyncMock(return_value=BrainDecision(
            decision_id="batch_test",
            primary_brain="commander",
            action="buy",
            confidence=0.8,
            reasoning="batch test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="batch_corr"
        ))
        
        result = await coordinator.request_decision(context, "commander")
        
        # 验证批处理方法被调用
        coordinator._request_decision_with_batch.assert_called_once()
        assert result.primary_brain == "commander"

    @pytest.mark.asyncio
    async def test_direct_processing_path_lines_192_194(self, coordinator):
        """测试直接处理路径选择 (行192-194)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 禁用批处理或使用soldier
        coordinator.enable_batch_processing = False
        
        # 模拟直接处理方法
        coordinator._request_decision_direct = AsyncMock(return_value=BrainDecision(
            decision_id="direct_test",
            primary_brain="soldier",
            action="sell",
            confidence=0.7,
            reasoning="direct test",
            supporting_data={},
            timestamp=datetime.now(),
            correlation_id="direct_corr"
        ))
        
        result = await coordinator.request_decision(context, "soldier")
        
        # 验证直接处理方法被调用
        coordinator._request_decision_direct.assert_called_once()
        assert result.primary_brain == "soldier"

    @pytest.mark.asyncio
    async def test_decision_success_path_lines_196_206(self, coordinator):
        """测试决策成功路径 (行196-206)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 配置soldier返回成功决策
        coordinator.soldier.decide = AsyncMock(return_value={
            'decision': {'action': 'buy', 'confidence': 0.9, 'reasoning': 'success test'},
            'metadata': {}
        })
        
        # 记录初始统计
        initial_total = coordinator.stats.get("total_decisions", 0)
        initial_soldier = coordinator.stats.get("soldier_decisions", 0)
        
        result = await coordinator.request_decision(context, "soldier")
        
        # 验证决策成功处理
        assert result is not None
        assert result.action == "buy"
        assert coordinator.stats["total_decisions"] > initial_total
        assert coordinator.stats["soldier_decisions"] > initial_soldier

    @pytest.mark.asyncio
    async def test_decision_timeout_path_lines_207_216(self, coordinator):
        """测试决策超时路径 (行207-216)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 模拟决策方法返回None（超时）
        coordinator._request_decision_direct = AsyncMock(return_value=None)
        
        # 记录初始统计
        initial_timeout = coordinator.stats.get("timeout_decisions", 0)
        
        result = await coordinator.request_decision(context, "soldier")
        
        # 验证超时处理
        assert result is not None
        assert "coordinator_fallback" in result.primary_brain
        assert coordinator.stats.get("timeout_decisions", 0) > initial_timeout

    @pytest.mark.asyncio
    async def test_decision_exception_path_lines_218_226(self, coordinator):
        """测试决策异常路径 (行218-226)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 让决策方法抛出异常
        coordinator._request_decision_direct = AsyncMock(side_effect=Exception("Decision failed"))
        
        # 记录初始统计
        initial_error = coordinator.stats.get("error_decisions", 0)
        
        result = await coordinator.request_decision(context, "soldier")
        
        # 验证异常处理
        assert result is not None
        assert "coordinator_fallback" in result.primary_brain
        assert coordinator.stats.get("error_decisions", 0) > initial_error
        assert "error_" in result.correlation_id

    @pytest.mark.asyncio
    async def test_batch_processing_commander_scholar_lines_242_250(self, coordinator):
        """测试批处理适用于commander和scholar (行242-250)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 启用批处理
        coordinator.enable_batch_processing = True
        
        # 测试commander使用批处理
        with patch.object(coordinator, '_request_decision_with_batch', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = BrainDecision(
                decision_id="batch_commander",
                primary_brain="commander",
                action="hold",
                confidence=0.6,
                reasoning="batch commander test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="batch_commander_corr"
            )
            
            result = await coordinator.request_decision(context, "commander")
            mock_batch.assert_called_once()
            assert result.primary_brain == "commander"
        
        # 测试scholar使用批处理
        with patch.object(coordinator, '_request_decision_with_batch', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = BrainDecision(
                decision_id="batch_scholar",
                primary_brain="scholar",
                action="research",
                confidence=0.7,
                reasoning="batch scholar test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="batch_scholar_corr"
            )
            
            result = await coordinator.request_decision(context, "scholar")
            mock_batch.assert_called_once()
            assert result.primary_brain == "scholar"

    @pytest.mark.asyncio
    async def test_soldier_direct_processing_lines_251_254(self, coordinator):
        """测试soldier使用直接处理 (行251-254)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 启用批处理，但soldier仍应使用直接处理
        coordinator.enable_batch_processing = True
        
        with patch.object(coordinator, '_request_decision_direct', new_callable=AsyncMock) as mock_direct:
            mock_direct.return_value = BrainDecision(
                decision_id="direct_soldier",
                primary_brain="soldier",
                action="quick_buy",
                confidence=0.8,
                reasoning="soldier direct test",
                supporting_data={},
                timestamp=datetime.now(),
                correlation_id="direct_soldier_corr"
            )
            
            result = await coordinator.request_decision(context, "soldier")
            mock_direct.assert_called_once()
            assert result.primary_brain == "soldier"

    @pytest.mark.asyncio
    async def test_correlation_id_generation_lines_183_185(self, coordinator):
        """测试correlation_id生成 (行183-185)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 模拟_generate_correlation_id方法
        with patch.object(coordinator, '_generate_correlation_id', return_value="test_correlation_123") as mock_gen:
            await coordinator.request_decision(context, "soldier")
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_decision_logging_lines_186_187(self, coordinator):
        """测试决策开始日志记录 (行186-187)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            await coordinator.request_decision(context, "soldier")
            
            # 验证日志被记录
            mock_logger.info.assert_called()
            log_calls = [call for call in mock_logger.info.call_args_list 
                        if "开始决策请求" in str(call)]
            assert len(log_calls) > 0

    @pytest.mark.asyncio
    async def test_stats_update_lines_197_200(self, coordinator):
        """测试统计信息更新 (行197-200)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 配置成功的决策
        coordinator.soldier.decide = AsyncMock(return_value={
            'decision': {'action': 'buy', 'confidence': 0.8, 'reasoning': 'stats test'},
            'metadata': {}
        })
        
        # 记录初始统计
        initial_stats = {
            "total_decisions": coordinator.stats.get("total_decisions", 0),
            "soldier_decisions": coordinator.stats.get("soldier_decisions", 0)
        }
        
        await coordinator.request_decision(context, "soldier")
        
        # 验证统计更新
        assert coordinator.stats["total_decisions"] == initial_stats["total_decisions"] + 1
        assert coordinator.stats["soldier_decisions"] == initial_stats["soldier_decisions"] + 1

    @pytest.mark.asyncio
    async def test_decision_completion_logging_lines_201_205(self, coordinator):
        """测试决策完成日志记录 (行201-205)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 配置成功的决策
        coordinator.soldier.decide = AsyncMock(return_value={
            'decision': {'action': 'sell', 'confidence': 0.9, 'reasoning': 'completion test'},
            'metadata': {}
        })
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            await coordinator.request_decision(context, "soldier")
            
            # 验证完成日志被记录
            completion_logs = [call for call in mock_logger.info.call_args_list 
                             if "决策完成" in str(call)]
            assert len(completion_logs) > 0

    @pytest.mark.asyncio
    async def test_timeout_warning_logging_lines_208_209(self, coordinator):
        """测试超时警告日志记录 (行208-209)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 模拟超时情况
        coordinator._request_decision_direct = AsyncMock(return_value=None)
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            await coordinator.request_decision(context, "soldier")
            
            # 验证超时警告日志
            warning_logs = [call for call in mock_logger.warning.call_args_list 
                           if "决策超时" in str(call)]
            assert len(warning_logs) > 0

    @pytest.mark.asyncio
    async def test_timeout_stats_update_lines_212_214(self, coordinator):
        """测试超时统计更新 (行212-214)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 模拟超时情况
        coordinator._request_decision_direct = AsyncMock(return_value=None)
        
        # 记录初始统计
        initial_timeout = coordinator.stats.get("timeout_decisions", 0)
        initial_total = coordinator.stats.get("total_decisions", 0)
        
        await coordinator.request_decision(context, "soldier")
        
        # 验证超时统计更新
        assert coordinator.stats.get("timeout_decisions", 0) == initial_timeout + 1
        assert coordinator.stats["total_decisions"] == initial_total + 1

    @pytest.mark.asyncio
    async def test_error_logging_lines_219_220(self, coordinator):
        """测试错误日志记录 (行219-220)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 让决策方法抛出异常
        coordinator._request_decision_direct = AsyncMock(side_effect=RuntimeError("Test error"))
        
        with patch('src.brain.ai_brain_coordinator.logger') as mock_logger:
            await coordinator.request_decision(context, "soldier")
            
            # 验证错误日志被记录
            error_logs = [call for call in mock_logger.error.call_args_list 
                         if "决策请求失败" in str(call)]
            assert len(error_logs) > 0

    @pytest.mark.asyncio
    async def test_error_correlation_id_generation_lines_221_221(self, coordinator):
        """测试错误correlation_id生成 (行221)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 让决策方法抛出异常
        coordinator._request_decision_direct = AsyncMock(side_effect=Exception("Test error"))
        
        result = await coordinator.request_decision(context, "soldier")
        
        # 验证错误correlation_id格式
        assert result.correlation_id.startswith("error_")
        assert "." in result.correlation_id  # 包含时间戳

    @pytest.mark.asyncio
    async def test_error_stats_update_lines_223_225(self, coordinator):
        """测试错误统计更新 (行223-225)"""
        context = {"symbol": "TEST", "action": "analyze"}
        
        # 让决策方法抛出异常
        coordinator._request_decision_direct = AsyncMock(side_effect=Exception("Test error"))
        
        # 记录初始统计
        initial_error = coordinator.stats.get("error_decisions", 0)
        
        await coordinator.request_decision(context, "soldier")
        
        # 验证错误统计更新
        assert coordinator.stats.get("error_decisions", 0) == initial_error + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])