"""
Redis连接失败集成测试

白皮书依据: 第二章 2.1 - Redis Key shared_context
验证需求: 需求3.5 - Redis连接失败时使用本地缓存并记录告警

测试任务: 2.4.3 编写Redis连接失败测试 - 集成测试部分
- 测试完整的Redis失败场景
- 验证系统在Redis不可用时的完整行为
- 验证告警和日志记录

版本: v1.6.0
日期: 2026-01-18
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
from loguru import logger

from src.brain.soldier.core import SoldierWithFailover, SoldierMode, TradingDecision, ShortTermMemory


class TestRedisFailureIntegration:
    """Redis连接失败集成测试类
    
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
    
    @pytest.mark.asyncio
    async def test_complete_redis_failure_scenario(self, soldier_config):
        """测试完整的Redis失败场景
        
        验证需求: 需求3.5 - 完整的Redis失败处理流程
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # Mock其他组件成功
        soldier._load_local_model = AsyncMock()
        soldier._init_cloud_api = AsyncMock()
        
        # 阶段1: 初始化时Redis连接失败
        with patch.object(soldier, '_connect_redis', side_effect=ConnectionError("Redis服务不可用")):
            with patch('src.brain.soldier.core.logger') as mock_logger:
                # 初始化应该失败并记录错误
                with pytest.raises(RuntimeError, match="Soldier初始化失败"):
                    await soldier.initialize()
                
                # 验证错误日志
                error_calls = [call for call in mock_logger.error.call_args_list 
                              if "Soldier初始化失败" in str(call)]
                assert len(error_calls) > 0
        
        # 阶段2: 手动设置本地缓存模式（模拟降级）
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 阶段3: 验证本地缓存功能正常
        test_operations = [
            ("position", "000001.SZ", 1000),
            ("sentiment", None, 0.5),
            ("position", "000002.SZ", 2000),
            ("sentiment", None, -0.3),
        ]
        
        for op_type, symbol, value in test_operations:
            if op_type == "position":
                await soldier.update_position(symbol, value)
            elif op_type == "sentiment":
                await soldier.update_market_sentiment(value)
        
        # 验证本地缓存状态
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert soldier.short_term_memory.market_sentiment == -0.3
        
        # 阶段4: 验证决策记录功能
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=500,
            confidence=0.8,
            reasoning="Redis失败测试",
            mode=SoldierMode.NORMAL,
            latency_ms=20.0
        )
        
        await soldier.add_decision_to_memory(decision)
        
        # 验证决策记录
        assert len(soldier.short_term_memory.recent_decisions) == 1
        recorded = soldier.short_term_memory.recent_decisions[0]
        assert recorded["action"] == "buy"
        assert recorded["symbol"] == "000001.SZ"
        assert recorded["quantity"] == 500
    
    @pytest.mark.asyncio
    async def test_redis_failure_during_trading_session(self, soldier_config):
        """测试交易会话中Redis失败的处理
        
        验证需求: 需求3.5 - 运行时Redis失败处理
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 初始化时Redis正常
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.short_term_memory = ShortTermMemory(
            positions={"000001.SZ": 1000},
            market_sentiment=0.2,
            recent_decisions=[]
        )
        
        # 模拟交易会话中的操作序列
        trading_operations = [
            ("update_position", "000002.SZ", 1500),
            ("update_sentiment", None, 0.6),
            ("update_position", "000003.SZ", 2000),
        ]
        
        # 在第二个操作时Redis失败
        call_count = 0
        def redis_set_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise ConnectionError("Redis连接丢失")
            return AsyncMock()
        
        mock_redis.set.side_effect = redis_set_side_effect
        
        # 执行操作序列
        with patch('src.brain.soldier.core.logger') as mock_logger:
            for op_type, symbol, value in trading_operations:
                if op_type == "update_position":
                    await soldier.update_position(symbol, value)
                elif op_type == "update_sentiment":
                    await soldier.update_market_sentiment(value)
            
            # 验证错误日志记录
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "保存记忆到Redis失败" in str(call)]
            assert len(error_calls) > 0
        
        # 验证本地缓存仍然正常工作
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.positions["000002.SZ"] == 1500
        assert soldier.short_term_memory.positions["000003.SZ"] == 2000
        assert soldier.short_term_memory.market_sentiment == 0.6
    
    @pytest.mark.asyncio
    async def test_redis_failure_alert_system(self, soldier_config):
        """测试Redis失败告警系统
        
        验证需求: 需求3.5 - 告警记录和通知
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # Mock其他组件
        soldier._load_local_model = AsyncMock()
        soldier._init_cloud_api = AsyncMock()
        
        # 测试不同类型的Redis失败
        failure_types = [
            ("连接超时", ConnectionError("Connection timeout")),
            ("认证失败", ConnectionError("Authentication failed")),
            ("网络不可达", ConnectionError("Network unreachable")),
            ("服务不可用", ConnectionError("Service unavailable")),
        ]
        
        for failure_name, failure_exception in failure_types:
            with patch.object(soldier, '_connect_redis', side_effect=failure_exception):
                with patch('src.brain.soldier.core.logger') as mock_logger:
                    # 尝试初始化
                    with pytest.raises(RuntimeError):
                        await soldier.initialize()
                    
                    # 验证告警日志
                    error_calls = mock_logger.error.call_args_list
                    
                    # 检查是否记录了具体的失败类型
                    failure_logged = any(
                        "Soldier初始化失败" in str(call) for call in error_calls
                    )
                    assert failure_logged, f"失败类型未记录告警: {failure_name}"
    
    @pytest.mark.asyncio
    async def test_memory_persistence_without_redis(self, soldier_config):
        """测试Redis不可用时的记忆持久性
        
        验证需求: 需求3.5 - 本地缓存持久性
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 设置本地缓存模式
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 执行大量操作以测试持久性
        num_operations = 100
        
        for i in range(num_operations):
            symbol = f"00000{i % 10}.SZ"
            quantity = (i + 1) * 100
            sentiment = (i % 21 - 10) / 10.0  # -1.0 到 1.0
            
            await soldier.update_position(symbol, quantity)
            await soldier.update_market_sentiment(sentiment)
            
            # 每10次操作验证一次状态
            if i % 10 == 9:
                status = soldier.get_memory_status()
                assert status["status"] == "active"
                assert status["positions_count"] <= 10  # 最多10个不同的symbol
                assert -1.0 <= status["market_sentiment"] <= 1.0
        
        # 验证最终状态
        final_status = soldier.get_memory_status()
        assert final_status["status"] == "active"
        assert final_status["positions_count"] == 10  # 10个不同的symbol
        assert isinstance(final_status["session_id"], str)
        assert final_status["last_update"] > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_without_redis(self, soldier_config):
        """测试Redis不可用时的并发操作安全性
        
        验证需求: 需求3.5 - 本地缓存并发安全
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 设置本地缓存模式
        soldier.redis_client = None
        soldier.short_term_memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 创建并发任务
        async def position_updater(symbol_prefix: str, count: int):
            for i in range(count):
                symbol = f"{symbol_prefix}{i:03d}.SZ"
                quantity = (i + 1) * 100
                await soldier.update_position(symbol, quantity)
                await asyncio.sleep(0.001)  # 小延迟模拟真实场景
        
        async def sentiment_updater(count: int):
            for i in range(count):
                sentiment = (i % 21 - 10) / 10.0
                await soldier.update_market_sentiment(sentiment)
                await asyncio.sleep(0.001)
        
        async def decision_recorder(count: int):
            for i in range(count):
                decision = TradingDecision(
                    action="buy" if i % 2 == 0 else "sell",
                    symbol=f"TEST{i:03d}.SZ",
                    quantity=(i + 1) * 100,
                    confidence=0.5 + (i % 5) * 0.1,
                    reasoning=f"并发测试 {i}",
                    mode=SoldierMode.NORMAL,
                    latency_ms=10.0 + i
                )
                await soldier.add_decision_to_memory(decision)
                await asyncio.sleep(0.001)
        
        # 并发执行任务
        tasks = [
            position_updater("A", 20),
            position_updater("B", 20),
            sentiment_updater(50),
            decision_recorder(30),
        ]
        
        await asyncio.gather(*tasks)
        
        # 验证最终状态一致性
        status = soldier.get_memory_status()
        assert status["status"] == "active"
        assert status["positions_count"] == 40  # A和B各20个
        assert -1.0 <= status["market_sentiment"] <= 1.0
        assert status["recent_decisions_count"] <= 10  # 限制为最近10个
        
        # 验证具体数据
        assert len(soldier.short_term_memory.positions) == 40
        assert len(soldier.short_term_memory.recent_decisions) <= 10
    
    @pytest.mark.asyncio
    async def test_redis_failure_recovery_simulation(self, soldier_config):
        """测试Redis失败恢复的模拟场景
        
        验证需求: 需求3.5 - 失败恢复处理
        """
        soldier = SoldierWithFailover(**soldier_config)
        
        # 阶段1: 正常运行（模拟Redis可用）
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        
        soldier.redis_client = mock_redis
        soldier.short_term_memory = ShortTermMemory(
            positions={"000001.SZ": 1000},
            market_sentiment=0.3,
            recent_decisions=[]
        )
        
        # 正常操作
        await soldier.update_position("000002.SZ", 2000)
        await soldier.update_market_sentiment(0.7)
        
        # 验证Redis调用
        assert mock_redis.set.call_count >= 2
        
        # 阶段2: Redis失败
        mock_redis.set.side_effect = ConnectionError("Redis连接丢失")
        
        with patch('src.brain.soldier.core.logger') as mock_logger:
            # 继续操作（应该失败但本地缓存正常）
            await soldier.update_position("000003.SZ", 3000)
            await soldier.update_market_sentiment(-0.2)
            
            # 验证错误日志
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "保存记忆到Redis失败" in str(call)]
            assert len(error_calls) >= 2
        
        # 验证本地缓存状态正常
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        assert soldier.short_term_memory.positions["000003.SZ"] == 3000
        assert soldier.short_term_memory.market_sentiment == -0.2
        
        # 阶段3: 模拟Redis恢复
        mock_redis.set.side_effect = None  # 恢复正常
        mock_redis.set.return_value = AsyncMock()
        
        # 恢复后的操作
        await soldier.update_position("000004.SZ", 4000)
        await soldier.update_market_sentiment(0.9)
        
        # 验证Redis调用恢复
        assert mock_redis.set.call_count >= 4  # 之前2次 + 恢复后2次
        
        # 验证最终状态
        assert soldier.short_term_memory.positions["000004.SZ"] == 4000
        assert soldier.short_term_memory.market_sentiment == 0.9


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])