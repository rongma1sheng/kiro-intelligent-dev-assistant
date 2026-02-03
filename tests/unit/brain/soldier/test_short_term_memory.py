"""短期记忆管理测试

白皮书依据: 第二章 2.1 - Redis Key shared_context
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from src.brain.soldier.core import ShortTermMemory, SoldierWithFailover, TradingDecision, SoldierMode


class TestShortTermMemory:
    """短期记忆数据类测试"""
    
    def test_create_memory(self):
        """测试创建短期记忆"""
        memory = ShortTermMemory(
            positions={"000001.SZ": 1000},
            market_sentiment=0.5,
            recent_decisions=[]
        )
        
        assert memory.positions == {"000001.SZ": 1000}
        assert memory.market_sentiment == 0.5
        assert memory.recent_decisions == []
        assert memory.last_update is not None
        assert memory.session_id is not None
        assert len(memory.session_id) == 8
    
    def test_memory_validation(self):
        """测试记忆数据验证"""
        # 测试市场情绪范围验证
        with pytest.raises(ValueError, match="市场情绪必须在\\[-1,1\\]范围内"):
            ShortTermMemory(
                positions={},
                market_sentiment=1.5,  # 超出范围
                recent_decisions=[]
            )
        
        with pytest.raises(ValueError, match="市场情绪必须在\\[-1,1\\]范围内"):
            ShortTermMemory(
                positions={},
                market_sentiment=-1.5,  # 超出范围
                recent_decisions=[]
            )
    
    def test_update_position(self):
        """测试更新仓位"""
        memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 添加仓位
        memory.update_position("000001.SZ", 1000)
        assert memory.positions["000001.SZ"] == 1000
        
        # 更新仓位
        memory.update_position("000001.SZ", 1500)
        assert memory.positions["000001.SZ"] == 1500
        
        # 平仓（数量为0）
        memory.update_position("000001.SZ", 0)
        assert "000001.SZ" not in memory.positions
    
    def test_add_decision(self):
        """测试添加决策记录"""
        memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 添加决策
        decision_summary = {
            "action": "buy",
            "symbol": "000001.SZ",
            "quantity": 1000,
            "confidence": 0.8
        }
        
        memory.add_decision(decision_summary)
        
        assert len(memory.recent_decisions) == 1
        assert memory.recent_decisions[0]["action"] == "buy"
        assert memory.recent_decisions[0]["symbol"] == "000001.SZ"
        assert "timestamp" in memory.recent_decisions[0]
    
    def test_decision_limit(self):
        """测试决策记录数量限制"""
        memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 添加15个决策（超过10个限制）
        for i in range(15):
            decision_summary = {
                "action": "buy",
                "symbol": f"00000{i}.SZ",
                "quantity": 1000
            }
            memory.add_decision(decision_summary)
        
        # 应该只保留最后10个
        assert len(memory.recent_decisions) == 10
        assert memory.recent_decisions[0]["symbol"] == "000005.SZ"  # 第6个决策
        assert memory.recent_decisions[-1]["symbol"] == "0000014.SZ"  # 第15个决策
    
    def test_update_sentiment(self):
        """测试更新市场情绪"""
        memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=[]
        )
        
        # 更新情绪
        memory.update_sentiment(0.7)
        assert memory.market_sentiment == 0.7
        
        # 测试边界值
        memory.update_sentiment(-1.0)
        assert memory.market_sentiment == -1.0
        
        memory.update_sentiment(1.0)
        assert memory.market_sentiment == 1.0
        
        # 测试超出范围
        with pytest.raises(ValueError, match="市场情绪必须在\\[-1,1\\]范围内"):
            memory.update_sentiment(1.1)
    
    def test_to_dict_from_dict(self):
        """测试字典序列化和反序列化"""
        original_memory = ShortTermMemory(
            positions={"000001.SZ": 1000, "000002.SZ": -500},
            market_sentiment=0.3,
            recent_decisions=[
                {"action": "buy", "symbol": "000001.SZ", "timestamp": time.time()}
            ]
        )
        
        # 转换为字典
        memory_dict = original_memory.to_dict()
        
        # 从字典恢复
        restored_memory = ShortTermMemory.from_dict(memory_dict)
        
        # 验证数据一致性
        assert restored_memory.positions == original_memory.positions
        assert restored_memory.market_sentiment == original_memory.market_sentiment
        assert restored_memory.recent_decisions == original_memory.recent_decisions
        assert restored_memory.session_id == original_memory.session_id


class TestSoldierMemoryIntegration:
    """Soldier短期记忆集成测试"""
    
    @pytest.fixture
    async def soldier(self):
        """创建测试用的Soldier实例"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key",
            redis_host="localhost",
            redis_port=6379
        )
        
        # 模拟初始化
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value=None)
        soldier.redis_client.set = AsyncMock()
        soldier.redis_client.ping = AsyncMock()
        
        await soldier._init_short_term_memory()
        
        return soldier
    
    @pytest.mark.asyncio
    async def test_init_short_term_memory_new(self):
        """测试初始化新的短期记忆"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key",
            redis_host="localhost",
            redis_port=6379
        )
        
        # 模拟初始化
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value=None)
        soldier.redis_client.set = AsyncMock()
        soldier.redis_client.ping = AsyncMock()
        
        await soldier._init_short_term_memory()
        
        assert soldier.short_term_memory is not None
        assert soldier.short_term_memory.positions == {}
        assert soldier.short_term_memory.market_sentiment == 0.0
        assert soldier.short_term_memory.recent_decisions == []
        assert soldier.short_term_memory.session_id is not None
    
    @pytest.mark.asyncio
    async def test_init_short_term_memory_from_redis(self):
        """测试从Redis加载现有短期记忆"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key"
        )
        
        # 模拟Redis返回现有记忆
        existing_memory = {
            "positions": {"000001.SZ": 1000},
            "market_sentiment": 0.5,
            "recent_decisions": [],
            "last_update": time.time(),
            "session_id": "test1234"
        }
        
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value='{"positions": {"000001.SZ": 1000}, "market_sentiment": 0.5, "recent_decisions": [], "last_update": ' + str(time.time()) + ', "session_id": "test1234"}')
        soldier.redis_client.set = AsyncMock()
        
        await soldier._init_short_term_memory()
        
        assert soldier.short_term_memory.positions == {"000001.SZ": 1000}
        assert soldier.short_term_memory.market_sentiment == 0.5
        assert soldier.short_term_memory.session_id == "test1234"
    
    @pytest.mark.asyncio
    async def test_update_position(self):
        """测试更新仓位"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key",
            redis_host="localhost",
            redis_port=6379
        )
        
        # 模拟初始化
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value=None)
        soldier.redis_client.set = AsyncMock()
        soldier.redis_client.ping = AsyncMock()
        
        await soldier._init_short_term_memory()
        await soldier.update_position("000001.SZ", 1000)
        
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000
        # 验证Redis保存被调用
        soldier.redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_market_sentiment(self):
        """测试更新市场情绪"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key",
            redis_host="localhost",
            redis_port=6379
        )
        
        # 模拟初始化
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value=None)
        soldier.redis_client.set = AsyncMock()
        soldier.redis_client.ping = AsyncMock()
        
        await soldier._init_short_term_memory()
        await soldier.update_market_sentiment(0.7)
        
        assert soldier.short_term_memory.market_sentiment == 0.7
        # 验证Redis保存被调用
        soldier.redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_decision_to_memory(self):
        """测试添加决策到记忆"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key",
            redis_host="localhost",
            redis_port=6379
        )
        
        # 模拟初始化
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value=None)
        soldier.redis_client.set = AsyncMock()
        soldier.redis_client.ping = AsyncMock()
        
        await soldier._init_short_term_memory()
        
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.8,
            reasoning="测试决策"
        )
        decision.mode = SoldierMode.NORMAL
        decision.latency_ms = 15.5
        
        await soldier.add_decision_to_memory(decision)
        
        assert len(soldier.short_term_memory.recent_decisions) == 1
        decision_record = soldier.short_term_memory.recent_decisions[0]
        assert decision_record["action"] == "buy"
        assert decision_record["symbol"] == "000001.SZ"
        assert decision_record["quantity"] == 1000
        assert decision_record["confidence"] == 0.8
        assert decision_record["mode"] == "normal"
        assert decision_record["latency_ms"] == 15.5
        
        # 验证Redis保存被调用
        soldier.redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_memory_status(self):
        """测试获取记忆状态"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key",
            redis_host="localhost",
            redis_port=6379
        )
        
        # 模拟初始化
        soldier.redis_client = MagicMock()
        soldier.redis_client.get = AsyncMock(return_value=None)
        soldier.redis_client.set = AsyncMock()
        soldier.redis_client.ping = AsyncMock()
        
        await soldier._init_short_term_memory()
        
        # 添加一些数据
        await soldier.update_position("000001.SZ", 1000)
        await soldier.update_market_sentiment(0.3)
        
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.8,
            reasoning="测试"
        )
        await soldier.add_decision_to_memory(decision)
        
        # 获取状态
        memory_status = soldier.get_memory_status()
        
        assert memory_status["status"] == "active"
        assert memory_status["positions_count"] == 1
        assert memory_status["market_sentiment"] == 0.3
        assert memory_status["recent_decisions_count"] == 1
        assert memory_status["session_id"] is not None
        assert memory_status["last_update"] is not None
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """测试Redis连接失败时的处理"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model.gguf",
            cloud_api_key="sk-test-key"
        )
        
        # 模拟Redis连接失败
        soldier.redis_client = None
        
        # 初始化应该创建默认记忆
        await soldier._init_short_term_memory()
        
        assert soldier.short_term_memory is not None
        assert soldier.short_term_memory.positions == {}
        assert soldier.short_term_memory.market_sentiment == 0.0
        
        # 更新操作应该正常工作（只是不会保存到Redis）
        await soldier.update_position("000001.SZ", 1000)
        assert soldier.short_term_memory.positions["000001.SZ"] == 1000