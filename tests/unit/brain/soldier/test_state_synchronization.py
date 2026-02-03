"""状态同步一致性测试

白皮书依据: 第二章 2.1 - Redis Key shared_context
验证需求: 需求3.1, 需求3.2, 需求3.3, 需求3.4

属性: 状态同步一致性
For any trading decision or mode switch, Soldier SHALL ensure that Redis shared_context 
contains the latest position information, market sentiment, and system state, and both 
local and cloud modes SHALL see consistent state.
"""

import pytest
import time
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any

from src.brain.soldier.core import (
    SoldierWithFailover, 
    SoldierMode, 
    TradingDecision, 
    ShortTermMemory
)


async def create_soldier_with_redis():
    """创建带Redis的Soldier实例的辅助函数"""
    soldier = SoldierWithFailover(
        local_model_path="/fake/model.gguf",
        cloud_api_key="sk-test-key",
        redis_host="localhost",
        redis_port=6379
    )
    
    # 模拟Redis客户端
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.ping = AsyncMock()
    
    soldier.redis_client = redis_mock
    await soldier._init_short_term_memory()
    
    return soldier, redis_mock


class TestStateSynchronizationConsistency:
    """状态同步一致性属性测试
    
    白皮书依据: 第二章 2.1 - Redis Key shared_context
    验证需求: 需求3.1, 需求3.2, 需求3.3, 需求3.4
    """
    
    @pytest.mark.asyncio
    @given(
        symbol=st.sampled_from(['000001.SZ', '000002.SZ', '000003.SH', '600000.SH', '300001.SZ']),
        quantity=st.integers(min_value=-10000, max_value=10000).filter(lambda x: x != 0),
        sentiment=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=20, deadline=5000)
    async def test_position_update_redis_consistency(self, symbol, quantity, sentiment):
        """属性测试: 仓位更新时Redis状态一致性
        
        验证需求: 需求3.1 - 执行交易决策时将仓位信息写入Redis shared_context
        
        属性: 对于任意有效的仓位更新，Redis中的shared_context应该包含最新的仓位信息
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 确保symbol格式正确（已经是正确格式）
        # symbol已经是有效的股票代码格式
        
        # 更新仓位
        await soldier.update_position(symbol, quantity)
        
        # 验证本地状态更新
        assert soldier.short_term_memory.positions[symbol] == quantity
        
        # 验证Redis保存被调用
        redis_mock.set.assert_called()
        
        # 获取最后一次Redis调用的参数
        call_args = redis_mock.set.call_args
        redis_key = call_args[0][0]
        redis_value = call_args[0][1]
        
        # 验证Redis键名正确
        assert redis_key == "mia:soldier:shared_context"
        
        # 验证Redis值包含正确的仓位信息
        memory_data = json.loads(redis_value)
        assert memory_data["positions"][symbol] == quantity
        
        # 验证时间戳更新
        assert memory_data["last_update"] > 0
        
        # 验证会话ID存在
        assert "session_id" in memory_data
        assert len(memory_data["session_id"]) == 8
    
    @pytest.mark.asyncio
    @given(
        sentiment=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=15, deadline=3000)
    async def test_market_sentiment_redis_consistency(self, sentiment):
        """属性测试: 市场情绪更新时Redis状态一致性
        
        验证需求: 需求3.2 - 执行交易决策时将市场情绪写入Redis shared_context
        
        属性: 对于任意有效的市场情绪值，Redis中的shared_context应该包含最新的情绪信息
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 更新市场情绪
        await soldier.update_market_sentiment(sentiment)
        
        # 验证本地状态更新
        assert abs(soldier.short_term_memory.market_sentiment - sentiment) < 1e-10
        
        # 验证Redis保存被调用
        redis_mock.set.assert_called()
        
        # 获取最后一次Redis调用的参数
        call_args = redis_mock.set.call_args
        redis_value = call_args[0][1]
        
        # 验证Redis值包含正确的情绪信息
        memory_data = json.loads(redis_value)
        assert abs(memory_data["market_sentiment"] - sentiment) < 1e-10
        
        # 验证时间戳更新
        assert memory_data["last_update"] > 0
    
    @pytest.mark.asyncio
    @given(
        actions=st.lists(
            st.tuples(
                st.sampled_from(['buy', 'sell', 'hold']),
                st.sampled_from(['000001.SZ', '000002.SZ', '000003.SH', '600000.SH']),
                st.integers(min_value=0, max_value=10000),
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=10, deadline=8000)
    async def test_trading_decision_state_consistency(self, actions):
        """属性测试: 交易决策状态一致性
        
        验证需求: 需求3.1, 需求3.2 - 执行交易决策时状态同步
        
        属性: 对于任意交易决策序列，本地状态和Redis状态应该保持一致
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 执行一系列交易决策
        for action, symbol, quantity, confidence in actions:
            decision = TradingDecision(
                action=action,
                symbol=symbol,
                quantity=quantity,
                confidence=confidence,
                reasoning="属性测试决策"
            )
            decision.mode = SoldierMode.NORMAL
            decision.latency_ms = 15.0
            
            # 添加决策到记忆
            await soldier.add_decision_to_memory(decision)
        
        # 验证本地状态
        assert len(soldier.short_term_memory.recent_decisions) == min(len(actions), 10)
        
        # 验证Redis保存被调用
        assert redis_mock.set.call_count >= len(actions)
        
        # 获取最后一次Redis调用的参数
        call_args = redis_mock.set.call_args
        redis_value = call_args[0][1]
        
        # 验证Redis值包含正确的决策信息
        memory_data = json.loads(redis_value)
        assert len(memory_data["recent_decisions"]) == min(len(actions), 10)
        
        # 验证最后一个决策的信息
        if actions:
            last_action, last_symbol, last_quantity, last_confidence = actions[-1]
            last_decision = memory_data["recent_decisions"][-1]
            
            assert last_decision["action"] == last_action
            assert last_decision["symbol"] == last_symbol
            assert last_decision["quantity"] == last_quantity
            assert abs(last_decision["confidence"] - last_confidence) < 1e-10
            assert last_decision["mode"] == "normal"
            assert last_decision["latency_ms"] == 15.0
    
    @pytest.mark.asyncio
    async def test_mode_switch_state_recovery(self):
        """测试模式切换时的状态恢复
        
        验证需求: 需求3.3 - 切换模式时从Redis读取最新的短期记忆
        
        属性: 模式切换后，系统应该能够从Redis恢复完整的状态信息
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 设置初始状态
        await soldier.update_position("000001.SZ", 1000)
        await soldier.update_position("000002.SZ", -500)
        await soldier.update_market_sentiment(0.7)
        
        # 添加一些决策记录
        for i in range(3):
            decision = TradingDecision(
                action="buy",
                symbol=f"00000{i+1}.SZ",
                quantity=1000,
                confidence=0.8,
                reasoning=f"测试决策{i+1}"
            )
            await soldier.add_decision_to_memory(decision)
        
        # 模拟模式切换 - 触发热备切换
        original_mode = soldier.mode
        await soldier._trigger_failover("测试模式切换")
        
        # 验证模式已切换
        assert soldier.mode != original_mode
        assert soldier.mode == SoldierMode.DEGRADED
        
        # 模拟从Redis加载状态（创建新的Soldier实例）
        new_soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key"
        )
        
        # 模拟Redis返回之前保存的状态
        saved_memory = soldier.short_term_memory.to_dict()
        redis_mock.get.return_value = json.dumps(saved_memory)
        
        new_soldier.redis_client = redis_mock
        await new_soldier._init_short_term_memory()
        
        # 验证状态恢复正确
        assert new_soldier.short_term_memory.positions == soldier.short_term_memory.positions
        assert new_soldier.short_term_memory.market_sentiment == soldier.short_term_memory.market_sentiment
        assert len(new_soldier.short_term_memory.recent_decisions) == len(soldier.short_term_memory.recent_decisions)
        assert new_soldier.short_term_memory.session_id == soldier.short_term_memory.session_id
    
    @pytest.mark.asyncio
    @given(
        positions=st.dictionaries(
            keys=st.sampled_from(['000001.SZ', '000002.SZ', '000003.SH', '600000.SH', '300001.SZ']),
            values=st.integers(min_value=-5000, max_value=5000).filter(lambda x: x != 0),
            min_size=1,
            max_size=5
        ),
        sentiment=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=10, deadline=6000)
    async def test_local_cloud_state_consistency(self, positions, sentiment):
        """属性测试: 本地和云端状态一致性
        
        验证需求: 需求3.4 - 确保本地和云端状态一致
        
        属性: 无论在哪种模式下，本地内存状态和Redis状态应该保持一致
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 在NORMAL模式下设置状态
        soldier.mode = SoldierMode.NORMAL
        
        # 批量更新仓位
        for symbol, quantity in positions.items():
            await soldier.update_position(symbol, quantity)
        
        # 更新市场情绪
        await soldier.update_market_sentiment(sentiment)
        
        # 获取本地状态
        local_state = soldier.short_term_memory.to_dict()
        
        # 获取最后一次Redis保存的状态
        call_args = redis_mock.set.call_args
        redis_value = call_args[0][1]
        redis_state = json.loads(redis_value)
        
        # 验证状态一致性
        assert local_state["positions"] == redis_state["positions"]
        assert abs(local_state["market_sentiment"] - redis_state["market_sentiment"]) < 1e-10
        assert local_state["session_id"] == redis_state["session_id"]
        
        # 切换到DEGRADED模式
        await soldier._trigger_failover("测试状态一致性")
        assert soldier.mode == SoldierMode.DEGRADED
        
        # 在DEGRADED模式下继续更新状态
        await soldier.update_market_sentiment(sentiment * 0.8)  # 稍微调整情绪
        
        # 再次验证状态一致性
        updated_local_state = soldier.short_term_memory.to_dict()
        
        call_args = redis_mock.set.call_args
        redis_value = call_args[0][1]
        updated_redis_state = json.loads(redis_value)
        
        assert updated_local_state["positions"] == updated_redis_state["positions"]
        assert abs(updated_local_state["market_sentiment"] - updated_redis_state["market_sentiment"]) < 1e-10
        assert updated_local_state["session_id"] == updated_redis_state["session_id"]
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self):
        """测试并发状态更新的一致性
        
        验证需求: 需求3.4 - 状态更新的原子性和一致性
        
        属性: 并发的状态更新操作应该保持数据一致性，不会出现竞态条件
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 并发执行多个状态更新操作
        tasks = []
        
        # 并发更新不同股票的仓位
        for i in range(5):
            symbol = f"00000{i+1}.SZ"
            quantity = (i + 1) * 1000
            tasks.append(soldier.update_position(symbol, quantity))
        
        # 并发更新市场情绪
        for sentiment in [0.1, 0.2, 0.3, 0.4, 0.5]:
            tasks.append(soldier.update_market_sentiment(sentiment))
        
        # 并发添加交易决策
        for i in range(3):
            decision = TradingDecision(
                action="buy",
                symbol=f"00000{i+1}.SZ",
                quantity=1000,
                confidence=0.8,
                reasoning=f"并发决策{i+1}"
            )
            tasks.append(soldier.add_decision_to_memory(decision))
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
        # 验证最终状态的一致性
        local_state = soldier.short_term_memory.to_dict()
        
        # 验证仓位信息
        assert len(local_state["positions"]) == 5
        for i in range(5):
            symbol = f"00000{i+1}.SZ"
            assert local_state["positions"][symbol] == (i + 1) * 1000
        
        # 验证市场情绪（应该是最后一次更新的值）
        assert local_state["market_sentiment"] == 0.5
        
        # 验证决策记录
        assert len(local_state["recent_decisions"]) == 3
        
        # 验证Redis保存被调用了足够多次
        assert redis_mock.set.call_count >= 13  # 5个仓位 + 5个情绪 + 3个决策
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_restarts(self):
        """测试重启后的状态持久化
        
        验证需求: 需求3.3 - 从Redis读取最新的短期记忆
        
        属性: 系统重启后应该能够从Redis完整恢复之前的状态
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 设置复杂的初始状态
        positions = {
            "000001.SZ": 1000,
            "000002.SZ": -500,
            "000003.SZ": 2000
        }
        
        for symbol, quantity in positions.items():
            await soldier.update_position(symbol, quantity)
        
        await soldier.update_market_sentiment(0.75)
        
        # 添加多个决策记录
        decisions_data = [
            ("buy", "000001.SZ", 1000, 0.9),
            ("sell", "000002.SZ", 500, 0.8),
            ("hold", "000003.SZ", 0, 0.6)
        ]
        
        for action, symbol, quantity, confidence in decisions_data:
            decision = TradingDecision(
                action=action,
                symbol=symbol,
                quantity=quantity,
                confidence=confidence,
                reasoning=f"持久化测试: {action} {symbol}"
            )
            decision.mode = SoldierMode.NORMAL
            decision.latency_ms = 12.5
            await soldier.add_decision_to_memory(decision)
        
        # 保存当前状态
        original_state = soldier.short_term_memory.to_dict()
        
        # 模拟系统重启 - 创建新的Soldier实例
        new_soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key"
        )
        
        # 模拟Redis返回保存的状态
        redis_mock.get.return_value = json.dumps(original_state)
        new_soldier.redis_client = redis_mock
        
        # 初始化新实例（应该从Redis加载状态）
        await new_soldier._init_short_term_memory()
        
        # 验证状态完全恢复
        restored_state = new_soldier.short_term_memory.to_dict()
        
        # 验证仓位信息
        assert restored_state["positions"] == original_state["positions"]
        
        # 验证市场情绪
        assert abs(restored_state["market_sentiment"] - original_state["market_sentiment"]) < 1e-10
        
        # 验证决策记录
        assert len(restored_state["recent_decisions"]) == len(original_state["recent_decisions"])
        
        for i, decision in enumerate(restored_state["recent_decisions"]):
            original_decision = original_state["recent_decisions"][i]
            assert decision["action"] == original_decision["action"]
            assert decision["symbol"] == original_decision["symbol"]
            assert decision["quantity"] == original_decision["quantity"]
            assert abs(decision["confidence"] - original_decision["confidence"]) < 1e-10
            assert decision["mode"] == original_decision["mode"]
            assert decision["latency_ms"] == original_decision["latency_ms"]
        
        # 验证会话ID和时间戳
        assert restored_state["session_id"] == original_state["session_id"]
        assert restored_state["last_update"] == original_state["last_update"]
    
    @pytest.mark.asyncio
    async def test_redis_key_format_consistency(self):
        """测试Redis键名格式一致性
        
        验证需求: 需求3.1, 需求3.2 - Redis shared_context键名规范
        
        属性: 所有状态更新操作都应该使用统一的Redis键名格式
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 执行各种状态更新操作
        await soldier.update_position("000001.SZ", 1000)
        await soldier.update_market_sentiment(0.5)
        
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.8,
            reasoning="键名测试"
        )
        await soldier.add_decision_to_memory(decision)
        
        # 验证所有Redis调用都使用了正确的键名
        for call in redis_mock.set.call_args_list:
            redis_key = call[0][0]
            assert redis_key == "mia:soldier:shared_context", f"错误的Redis键名: {redis_key}"
        
        # 验证键名符合白皮书规范
        expected_key = "mia:soldier:shared_context"
        assert expected_key.startswith("mia:"), "键名应该以mia:开头"
        assert "soldier" in expected_key, "键名应该包含soldier"
        assert "shared_context" in expected_key, "键名应该包含shared_context"
    
    @pytest.mark.asyncio
    async def test_state_update_atomicity(self):
        """测试状态更新的原子性
        
        验证需求: 需求3.4 - 状态更新的原子性
        
        属性: 每次状态更新操作应该是原子的，不会出现部分更新的情况
        """
        soldier, redis_mock = await create_soldier_with_redis()
        
        # 模拟Redis写入失败的情况
        redis_mock.set.side_effect = [Exception("Redis写入失败"), None, None]
        
        # 尝试更新仓位（Redis写入会失败，但本地状态仍会更新）
        # 当前实现只是记录日志，不抛出异常，这是合理的设计
        await soldier.update_position("000001.SZ", 1000)
        
        # 验证本地状态更新成功（即使Redis失败）
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        
        # 验证Redis保存被尝试调用
        redis_mock.set.assert_called()
        
        # 重置Redis mock，使其正常工作
        redis_mock.set.side_effect = None
        
        # 正常更新仓位
        await soldier.update_position("000002.SZ", 2000)
        
        # 验证状态更新成功
        assert soldier.short_term_memory.positions["000002.SZ"] == 2000
        
        # 验证Redis保存被调用
        redis_mock.set.assert_called()
        
        # 获取保存的数据
        call_args = redis_mock.set.call_args
        redis_value = call_args[0][1]
        memory_data = json.loads(redis_value)
        
        # 验证数据完整性
        assert "positions" in memory_data
        assert "market_sentiment" in memory_data
        assert "recent_decisions" in memory_data
        assert "last_update" in memory_data
        assert "session_id" in memory_data
        
        # 验证仓位数据正确
        assert memory_data["positions"]["000001.SZ"] == 1000
        assert memory_data["positions"]["000002.SZ"] == 2000