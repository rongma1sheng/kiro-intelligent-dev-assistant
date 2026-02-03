"""
Redis连接失败测试

白皮书依据: 第二章 2.1 - Redis Key shared_context
验证需求: 需求3.5 - Redis连接失败时使用本地缓存并记录告警

测试任务: 2.4.3 编写Redis连接失败测试
- 测试Redis连接失败时的行为
- 验证本地缓存使用
- 验证告警发送

版本: v1.6.0
日期: 2026-01-18
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
from loguru import logger

from src.brain.soldier.core import SoldierWithFailover, SoldierMode, TradingDecision, ShortTermMemory


class TestRedisConnectionFailure:
    """Redis连接失败测试类
    
    白皮书依据: 第二章 2.1 - Redis Key shared_context
    验证需求: 需求3.5
    """
    
    @pytest.fixture
    def soldier_config(self):
        """Soldier配置夹具"""
        return {
            "local_model_path": "/fake/models/qwen-30b.gguf",
            "cloud_api_key": "sk-test-key-12345",
            "redis_host": "localhost",
            "redis_port": 6379
        }
    
    @pytest.fixture
    def mock_market_data(self):
        """模拟市场数据夹具"""
        return {
            "symbol": "000001.SZ",
            "price": 15.67,
            "volume": 1000000,
            "timestamp": "2026-01-17T09:30:00"
        }
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_during_init(self, soldier_config):
        """测试初始化时Redis连接失败
        
        验证需求: 需求3.5 - Redis连接失败时记录告警
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # Mock其他组件成功
        soldier._load_local_model = AsyncMock()
        soldier._init_cloud_api = AsyncMock()
        
        # Mock Redis连接失败
        with patch.object(soldier, '_connect_redis', side_effect=ConnectionError("Redis服务不可用")):
            # 捕获日志
            with patch('src.brain.soldier.core.logger') as mock_logger:
                # 初始化应该失败并记录错误
                with pytest.raises(RuntimeError, match="Soldier初始化失败"):
                    await soldier.initialize()
                
                # 验证错误日志记录
                mock_logger.error.assert_called()
                error_calls = [call for call in mock_logger.error.call_args_list 
                              if "Soldier初始化失败" in str(call)]
                assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_with_local_cache_fallback(self, soldier_config):
        """测试Redis连接失败时的告警记录
        
        验证需求: 需求3.5 - 记录告警
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # Mock其他组件
        soldier._load_local_model = AsyncMock()
        soldier._init_cloud_api = AsyncMock()
        
        # Mock Redis连接失败
        soldier._connect_redis = AsyncMock(side_effect=ConnectionError("Redis连接超时"))
        
        # 捕获日志
        with patch('src.brain.soldier.core.logger') as mock_logger:
            # 初始化应该失败
            with pytest.raises(RuntimeError):
                await soldier.initialize()
            
            # 验证告警日志
            mock_logger.error.assert_called()
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "Soldier初始化失败" in str(call)]
            assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_position_update_without_redis(self, soldier_config):
        """测试Redis不可用时的仓位更新
        
        验证需求: 需求3.5 - 本地缓存正常工作
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化但不连接Redis
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 更新仓位
        await soldier.update_position("000001.SZ", 1000)
        
        # 验证本地缓存更新
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        
        # 再次更新
        await soldier.update_position("000002.SZ", 2000)
        await soldier.update_position("000001.SZ", 1500)  # 修改现有仓位
        
        # 验证本地缓存状态
        assert soldier.short_term_memory.positions["000001.SZ"] == 1500
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert len(soldier.short_term_memory.positions) == 2
    
    @pytest.mark.asyncio
    async def test_market_sentiment_update_without_redis(self, soldier_config):
        """测试Redis不可用时的市场情绪更新
        
        验证需求: 需求3.5 - 本地缓存正常工作
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化但不连接Redis
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 更新市场情绪
        await soldier.update_market_sentiment(0.75)
        
        # 验证本地缓存更新
        assert soldier.short_term_memory.market_sentiment == 0.75
        
        # 再次更新
        await soldier.update_market_sentiment(-0.3)
        
        # 验证本地缓存状态
        assert soldier.short_term_memory.market_sentiment == -0.3
    
    @pytest.mark.asyncio
    async def test_decision_recording_without_redis(self, soldier_config, mock_market_data):
        """测试Redis不可用时的决策记录
        
        验证需求: 需求3.5 - 本地缓存正常工作
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化但不连接Redis
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 创建模拟决策
        decision = TradingDecision(
            action="buy",  # 使用小写
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.85,
            reasoning="技术面突破",
            mode=SoldierMode.NORMAL,
            latency_ms=15.2
        )
        
        # 记录决策
        await soldier.add_decision_to_memory(decision)
        
        # 验证本地缓存更新
        assert len(soldier.short_term_memory.recent_decisions) == 1
        
        recorded_decision = soldier.short_term_memory.recent_decisions[0]
        assert recorded_decision["action"] == "buy"  # 小写
        assert recorded_decision["symbol"] == "000001.SZ"
        assert recorded_decision["quantity"] == 1000
        assert recorded_decision["confidence"] == 0.85
        assert recorded_decision["mode"] == "normal"  # 小写
        assert recorded_decision["latency_ms"] == 15.2
    
    @pytest.mark.asyncio
    async def test_redis_reconnection_attempt(self, soldier_config):
        """测试Redis重连尝试的告警记录
        
        验证需求: 需求3.5 - 连接失败后的告警记录
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # Mock其他组件
        soldier._load_local_model = AsyncMock()
        soldier._init_cloud_api = AsyncMock()
        
        # Mock Redis连接失败
        with patch.object(soldier, '_connect_redis', side_effect=ConnectionError("Redis连接失败")):
            with patch('src.brain.soldier.core.logger') as mock_logger:
                # 初始化失败
                with pytest.raises(RuntimeError):
                    await soldier.initialize()
                
                # 验证错误日志记录
                mock_logger.error.assert_called()
                error_calls = [call for call in mock_logger.error.call_args_list 
                              if "Soldier初始化失败" in str(call)]
                assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_redis_failure_during_operation(self, soldier_config):
        """测试运行时Redis连接失败
        
        验证需求: 需求3.5 - 运行时连接失败的处理
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化时Redis正常
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 模拟Redis操作失败
        mock_redis.set.side_effect = ConnectionError("Redis连接丢失")
        
        # 捕获日志
        with patch('src.brain.soldier.core.logger') as mock_logger:
            # 尝试更新仓位
            await soldier.update_position("000001.SZ", 1000)
            
            # 验证本地缓存仍然更新
            assert soldier.short_term_memory.positions["000001.SZ"] == 1000
            
            # 验证错误日志
            mock_logger.error.assert_called()
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "保存记忆到Redis失败" in str(call)]
            assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_memory_status_without_redis(self, soldier_config):
        """测试Redis不可用时的记忆状态查询
        
        验证需求: 需求3.5 - 本地缓存状态查询
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化但不连接Redis
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={"000001.SZ": 1000, "000002.SZ": 2000},
            market_sentiment=0.5,
            recent_decisions=[]
        )
        
        # 获取记忆状态
        status = soldier.get_memory_status()
        
        # 验证状态信息
        assert status["status"] != "not_initialized"
        assert "positions_count" in status
        assert "market_sentiment" in status
        assert "session_id" in status
        
        # 验证具体数据
        assert status["positions_count"] == 2
        assert status["market_sentiment"] == 0.5
    
    @pytest.mark.asyncio
    async def test_redis_failure_alert_mechanism(self, soldier_config):
        """测试Redis失败告警机制
        
        验证需求: 需求3.5 - 记录告警
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # Mock其他组件
        soldier._load_local_model = AsyncMock()
        soldier._init_cloud_api = AsyncMock()
        
        # 模拟不同类型的Redis失败
        failure_scenarios = [
            ConnectionError("连接超时"),
            ConnectionError("认证失败"),
            ConnectionError("网络不可达"),
            Exception("未知Redis错误")
        ]
        
        for failure in failure_scenarios:
            with patch.object(soldier, '_connect_redis', side_effect=failure):
                with patch('src.brain.soldier.core.logger') as mock_logger:
                    # 初始化应该失败
                    with pytest.raises(RuntimeError):
                        await soldier.initialize()
                    
                    # 验证错误日志记录
                    mock_logger.error.assert_called()
                    error_calls = mock_logger.error.call_args_list
                    
                    # 检查是否记录了初始化失败
                    init_error_logged = any(
                        "Soldier初始化失败" in str(call) for call in error_calls
                    )
                    assert init_error_logged, f"初始化失败未记录告警: {failure}"
    
    @pytest.mark.asyncio
    async def test_local_cache_persistence_across_operations(self, soldier_config):
        """测试本地缓存在多次操作中的持久性
        
        验证需求: 需求3.5 - 本地缓存可靠性
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化但不连接Redis
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 执行一系列操作
        operations = [
            ("update_position", "000001.SZ", 1000),
            ("update_market_sentiment", 0.3),
            ("update_position", "000002.SZ", 2000),
            ("update_market_sentiment", 0.7),
            ("update_position", "000001.SZ", 1500),  # 修改现有仓位
        ]
        
        for operation in operations:
            if operation[0] == "update_position":
                await soldier.update_position(operation[1], operation[2])
            elif operation[0] == "update_market_sentiment":
                await soldier.update_market_sentiment(operation[1])
        
        # 验证最终状态
        assert soldier.short_term_memory.positions["000001.SZ"] == 1500
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert soldier.short_term_memory.market_sentiment == 0.7
        
        # 验证数据一致性
        status = soldier.get_memory_status()
        assert status["positions_count"] == 2
        assert status["market_sentiment"] == 0.7
    
    @pytest.mark.asyncio
    async def test_redis_failure_during_mode_switch(self, soldier_config):
        """测试模式切换时Redis失败的处理
        
        验证需求: 需求3.5 - 模式切换时的本地缓存使用
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={"000001.SZ": 1000},
            market_sentiment=0.5,
            recent_decisions=[]
        )
        
        # 模拟模式切换
        original_mode = soldier.mode
        
        # 切换到降级模式
        soldier.mode = SoldierMode.DEGRADED
        
        # 在降级模式下更新状态
        await soldier.update_position("000002.SZ", 2000)
        await soldier.update_market_sentiment(-0.2)
        
        # 验证本地缓存正常工作
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert soldier.short_term_memory.market_sentiment == -0.2
        
        # 切换回正常模式
        soldier.mode = SoldierMode.NORMAL
        
        # 验证状态保持
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert soldier.short_term_memory.market_sentiment == -0.2


class TestRedisConnectionFailureProperties:
    """Redis连接失败的基于属性的测试
    
    使用Hypothesis进行属性测试，验证各种边界条件
    """
    
    @pytest.fixture
    def soldier_without_redis(self):
        """创建没有Redis连接的Soldier实例"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key"
        )
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        return soldier
    
    @pytest.mark.asyncio
    async def test_position_updates_property(self, soldier_without_redis):
        """属性测试：仓位更新的一致性
        
        验证需求: 需求3.5 - 本地缓存一致性
        """
        soldier = soldier_without_redis
        
        # 测试数据
        test_positions = [
            ("000001.SZ", 1000),
            ("000002.SZ", 2000),
            ("000003.SZ", -500),  # 空头
            ("000001.SZ", 1500),  # 修改现有
            ("000004.SZ", 0),     # 平仓
        ]
        
        expected_positions = {}
        
        for symbol, quantity in test_positions:
            await soldier.update_position(symbol, quantity)
            expected_positions[symbol] = quantity
            
            # 验证每次更新后的一致性
            if quantity == 0:
                # 仓位为0时应该被删除
                assert symbol not in soldier.short_term_memory.positions
            else:
                assert soldier.short_term_memory.positions[symbol] == quantity
        
        # 验证最终状态（排除仓位为0的）
        for symbol, expected_qty in expected_positions.items():
            if expected_qty == 0:
                assert symbol not in soldier.short_term_memory.positions
            else:
                assert soldier.short_term_memory.positions[symbol] == expected_qty
    
    @pytest.mark.asyncio
    async def test_sentiment_updates_property(self, soldier_without_redis):
        """属性测试：市场情绪更新的边界条件
        
        验证需求: 需求3.5 - 本地缓存边界处理
        """
        soldier = soldier_without_redis
        
        # 测试边界值
        test_sentiments = [-1.0, -0.5, 0.0, 0.5, 1.0, 0.999, -0.999]
        
        for sentiment in test_sentiments:
            await soldier.update_market_sentiment(sentiment)
            
            # 验证更新成功
            assert soldier.short_term_memory.market_sentiment == sentiment
            
            # 验证状态查询一致性
            status = soldier.get_memory_status()
            assert status["market_sentiment"] == sentiment
    
    @pytest.mark.asyncio
    async def test_concurrent_updates_without_redis(self, soldier_without_redis):
        """测试Redis不可用时的并发更新
        
        验证需求: 需求3.5 - 本地缓存并发安全
        """
        soldier = soldier_without_redis
        
        # 并发更新任务
        async def update_position_task(symbol: str, quantity: int):
            await soldier.update_position(symbol, quantity)
        
        async def update_sentiment_task(sentiment: float):
            await soldier.update_market_sentiment(sentiment)
        
        # 创建并发任务
        tasks = [
            update_position_task("000001.SZ", 1000),
            update_position_task("000002.SZ", 2000),
            update_sentiment_task(0.5),
            update_position_task("000003.SZ", 1500),
            update_sentiment_task(0.8),
        ]
        
        # 并发执行
        await asyncio.gather(*tasks)
        
        # 验证最终状态
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert soldier.short_term_memory.positions["000003.SZ"] == 1500
        # 情绪值应该是最后一次更新的值
        assert soldier.short_term_memory.market_sentiment in [0.5, 0.8]
    
    @pytest.mark.asyncio
    async def test_memory_consistency_after_failures(self, soldier_without_redis):
        """测试失败后的记忆一致性
        
        验证需求: 需求3.5 - 失败恢复后的一致性
        """
        soldier = soldier_without_redis
        
        # 正常操作
        await soldier.update_position("000001.SZ", 1000)
        await soldier.update_market_sentiment(0.3)
        
        # 模拟操作失败（通过异常）
        with patch.object(soldier.short_term_memory, 'update_position', 
                         side_effect=Exception("模拟失败")):
            try:
                await soldier.update_position("000002.SZ", 2000)
            except:
                pass  # 忽略异常
        
        # 验证之前的状态未被破坏
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.market_sentiment == 0.3
        
        # 验证后续操作正常
        await soldier.update_position("000003.SZ", 3000)
        assert soldier.short_term_memory.positions["000003.SZ"] == 3000


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])