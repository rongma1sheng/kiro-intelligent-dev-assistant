"""Soldier核心类单元测试

白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)
测试覆盖: SoldierMode, TradingDecision, SoldierWithFailover
"""

import pytest
import asyncio
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.soldier.core import SoldierMode, TradingDecision, SoldierWithFailover


class TestSoldierMode:
    """测试SoldierMode枚举
    
    白皮书依据: 第二章 2.1
    """
    
    def test_soldier_mode_values(self):
        """测试枚举值的有效性"""
        assert SoldierMode.NORMAL.value == "normal"
        assert SoldierMode.DEGRADED.value == "degraded"
    
    def test_soldier_mode_count(self):
        """测试枚举数量"""
        assert len(SoldierMode) == 2
    
    def test_soldier_mode_comparison(self):
        """测试枚举比较"""
        assert SoldierMode.NORMAL != SoldierMode.DEGRADED
        assert SoldierMode.NORMAL == SoldierMode.NORMAL


class TestTradingDecision:
    """测试TradingDecision数据类
    
    白皮书依据: 第二章 2.1
    """

    def test_trading_decision_creation(self):
        """测试交易决策创建"""
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.85,
            reasoning="技术面突破"
        )
        
        assert decision.action == "buy"
        assert decision.symbol == "000001.SZ"
        assert decision.quantity == 1000
        assert decision.confidence == 0.85
        assert decision.reasoning == "技术面突破"
        assert decision.timestamp is not None
        assert decision.mode is None
        assert decision.latency_ms is None
    
    def test_trading_decision_timestamp_auto_set(self):
        """测试时间戳自动设置"""
        before = time.time()
        decision = TradingDecision(
            action="sell",
            symbol="000002.SZ",
            quantity=500,
            confidence=0.75,
            reasoning="止损"
        )
        after = time.time()
        
        assert before <= decision.timestamp <= after
    
    def test_trading_decision_confidence_validation(self):
        """测试置信度验证"""
        # 有效置信度
        decision = TradingDecision(
            action="hold",
            symbol="000001.SZ",
            quantity=0,
            confidence=0.5,
            reasoning="观望"
        )
        assert decision.confidence == 0.5
        
        # 边界值
        decision_min = TradingDecision(
            action="hold",
            symbol="000001.SZ",
            quantity=0,
            confidence=0.0,
            reasoning="观望"
        )
        assert decision_min.confidence == 0.0
        
        decision_max = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=1.0,
            reasoning="强烈看好"
        )
        assert decision_max.confidence == 1.0
    
    def test_trading_decision_confidence_invalid(self):
        """测试无效置信度"""
        # 置信度 < 0
        with pytest.raises(ValueError, match="置信度必须在\\[0,1\\]范围内"):
            TradingDecision(
                action="buy",
                symbol="000001.SZ",
                quantity=1000,
                confidence=-0.1,
                reasoning="测试"
            )
        
        # 置信度 > 1
        with pytest.raises(ValueError, match="置信度必须在\\[0,1\\]范围内"):
            TradingDecision(
                action="buy",
                symbol="000001.SZ",
                quantity=1000,
                confidence=1.1,
                reasoning="测试"
            )
    
    def test_trading_decision_action_validation(self):
        """测试交易动作验证"""
        # 有效动作
        valid_actions = ["buy", "sell", "hold"]
        for action in valid_actions:
            decision = TradingDecision(
                action=action,
                symbol="000001.SZ",
                quantity=1000,
                confidence=0.8,
                reasoning="测试"
            )
            assert decision.action == action
        
        # 无效动作
        with pytest.raises(ValueError, match="无效的交易动作"):
            TradingDecision(
                action="invalid",
                symbol="000001.SZ",
                quantity=1000,
                confidence=0.8,
                reasoning="测试"
            )


class TestSoldierWithFailover:
    """测试SoldierWithFailover类
    
    白皮书依据: 第二章 2.1
    """
    
    def test_soldier_initialization(self):
        """测试Soldier初始化"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        assert soldier.mode == SoldierMode.NORMAL
        assert soldier.failure_count == 0
        assert soldier.failure_threshold == 3
        assert soldier.local_timeout == 0.2
        assert soldier.local_model is None
        assert soldier.llm_gateway is None  # 使用llm_gateway而非cloud_api
        assert soldier.redis_client is None
    
    def test_soldier_initialization_with_custom_params(self):
        """测试自定义参数初始化"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123",
            redis_host="redis.example.com",
            redis_port=6380,
            failure_threshold=5,
            local_timeout=0.1
        )
        
        assert soldier.failure_threshold == 5
        assert soldier.local_timeout == 0.1
        assert soldier._redis_host == "redis.example.com"
        assert soldier._redis_port == 6380
    
    def test_soldier_initialization_invalid_params(self):
        """测试无效参数初始化"""
        # 无效失败阈值
        with pytest.raises(ValueError, match="失败阈值必须 > 0"):
            SoldierWithFailover(
                local_model_path="/models/qwen-30b.gguf",
                cloud_api_key="sk-test123",
                failure_threshold=0
            )
        
        # 无效超时时间
        with pytest.raises(ValueError, match="超时时间必须 > 0"):
            SoldierWithFailover(
                local_model_path="/models/qwen-30b.gguf",
                cloud_api_key="sk-test123",
                local_timeout=-0.1
            )
    
    @pytest.mark.asyncio
    async def test_soldier_async_initialization_success(self):
        """测试异步初始化成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock内部方法
        soldier._connect_redis = AsyncMock()
        soldier._init_short_term_memory = AsyncMock()
        soldier._init_llm_gateway = AsyncMock()
        soldier._load_local_model = AsyncMock()
        soldier._update_redis_status = AsyncMock()
        
        await soldier.initialize()
        
        # 验证调用
        soldier._connect_redis.assert_called_once_with("localhost", 6379)
        soldier._load_local_model.assert_called_once_with("/models/qwen-30b.gguf")
        soldier._init_llm_gateway.assert_called_once()
        soldier._update_redis_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_soldier_async_initialization_failure(self):
        """测试异步初始化失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock Redis连接失败
        soldier._connect_redis = AsyncMock(side_effect=ConnectionError("Redis连接失败"))
        soldier._load_local_model = AsyncMock()
        soldier._init_llm_gateway = AsyncMock()
        
        with pytest.raises(RuntimeError, match="Soldier初始化失败"):
            await soldier.initialize()

    @pytest.mark.asyncio
    async def test_make_decision_normal_mode_success(self):
        """测试正常模式决策成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock本地推理
        expected_decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.85,
            reasoning="本地模型推荐买入"
        )
        soldier._local_inference = AsyncMock(return_value=expected_decision)
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_timeout_condition = AsyncMock(return_value=False)
        soldier.add_decision_to_memory = AsyncMock()
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        decision = await soldier.make_decision(market_data)
        
        assert decision.action == "buy"
        assert decision.mode == SoldierMode.NORMAL
        assert decision.latency_ms is not None
        assert decision.latency_ms < 1000  # 应该很快
        assert soldier.failure_count == 0  # 成功后重置
    
    @pytest.mark.asyncio
    async def test_make_decision_timeout_triggers_failover(self):
        """测试超时触发热备切换"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123",
            local_timeout=0.05  # 50ms超时
        )
        
        # Mock本地推理超时
        async def slow_inference(market_data, timeout):
            await asyncio.sleep(0.1)  # 100ms，超过50ms超时
            return TradingDecision(
                action="hold",
                symbol="000001.SZ",
                quantity=0,
                confidence=0.5,
                reasoning="慢推理"
            )
        
        soldier._local_inference = slow_inference
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_timeout_condition = AsyncMock(return_value=True)
        soldier._trigger_failover = AsyncMock()
        soldier.add_decision_to_memory = AsyncMock()
        
        # Mock云端推理
        cloud_decision = TradingDecision(
            action="sell",
            symbol="000001.SZ",
            quantity=500,
            confidence=0.7,
            reasoning="云端推理"
        )
        soldier._cloud_inference = AsyncMock(return_value=cloud_decision)
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        decision = await soldier.make_decision(market_data)
        
        # 验证触发了热备切换
        soldier._trigger_failover.assert_called_once()
        assert decision.action == "sell"  # 云端决策
    
    @pytest.mark.asyncio
    async def test_make_decision_failure_count_triggers_failover(self):
        """测试连续失败触发热备切换"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123",
            failure_threshold=2  # 降低阈值便于测试
        )
        
        # Mock本地推理失败
        soldier._local_inference = AsyncMock(side_effect=RuntimeError("推理失败"))
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_consecutive_failure_condition = AsyncMock(side_effect=[False, True])
        soldier._trigger_failover = AsyncMock()
        soldier.add_decision_to_memory = AsyncMock()
        
        # Mock云端推理成功
        cloud_decision = TradingDecision(
            action="hold",
            symbol="000001.SZ",
            quantity=0,
            confidence=0.6,
            reasoning="云端兜底"
        )
        soldier._cloud_inference = AsyncMock(return_value=cloud_decision)
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        # 第一次失败
        decision1 = await soldier.make_decision(market_data)
        assert soldier.failure_count == 1
        
        # 第二次失败，触发切换
        decision2 = await soldier.make_decision(market_data)
        assert soldier.failure_count == 2
        soldier._trigger_failover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_decision_invalid_market_data(self):
        """测试无效市场数据"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 空数据
        with pytest.raises(ValueError, match="market_data不能为空"):
            await soldier.make_decision({})
        
        # None数据
        with pytest.raises(ValueError, match="market_data不能为空"):
            await soldier.make_decision(None)

    @pytest.mark.asyncio
    async def test_make_decision_degraded_mode(self):
        """测试降级模式决策"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置为降级模式
        soldier.mode = SoldierMode.DEGRADED
        soldier.add_decision_to_memory = AsyncMock()
        
        # Mock云端推理
        cloud_decision = TradingDecision(
            action="buy",
            symbol="000002.SZ",
            quantity=2000,
            confidence=0.9,
            reasoning="云端强烈推荐"
        )
        soldier._cloud_inference = AsyncMock(return_value=cloud_decision)
        
        market_data = {"symbol": "000002.SZ", "price": 15.8}
        decision = await soldier.make_decision(market_data)
        
        assert decision.action == "buy"
        assert decision.mode == SoldierMode.DEGRADED
        soldier._cloud_inference.assert_called_once_with(market_data)
    
    @pytest.mark.asyncio
    async def test_trigger_failover(self):
        """测试热备切换逻辑"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock依赖方法
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 初始状态
        assert soldier.mode == SoldierMode.NORMAL
        assert soldier.last_switch_time == 0
        
        # 触发切换
        before_time = time.time()
        await soldier._trigger_failover("测试原因")
        after_time = time.time()
        
        # 验证状态变化
        assert soldier.mode == SoldierMode.DEGRADED
        assert before_time <= soldier.last_switch_time <= after_time
        
        # 验证调用
        soldier._update_redis_status.assert_called_once()
        soldier._send_alert.assert_called_once()
        # 验证告警消息包含关键信息
        call_args = soldier._send_alert.call_args[0][0]
        assert "热备切换" in call_args or "DEGRADED" in call_args or "测试原因" in call_args
    
    @pytest.mark.asyncio
    async def test_trigger_failover_already_degraded(self):
        """测试已经是降级模式时的切换"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置为降级模式
        soldier.mode = SoldierMode.DEGRADED
        soldier.last_switch_time = 123456
        
        # Mock依赖方法
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 触发切换（应该不做任何事）
        await soldier._trigger_failover()
        
        # 验证状态不变
        assert soldier.mode == SoldierMode.DEGRADED
        assert soldier.last_switch_time == 123456
        
        # 验证没有调用
        soldier._update_redis_status.assert_not_called()
        soldier._send_alert.assert_not_called()
    
    def test_get_status(self):
        """测试状态获取"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 初始状态
        status = soldier.get_status()
        assert status["mode"] == "normal"
        assert status["failure_count"] == 0
        assert status["last_switch_time"] == 0
        assert status["local_model_loaded"] is False
        assert status["redis_connected"] is False
        # 检查llm_gateway_initialized而非cloud_api_initialized
        assert "llm_gateway_initialized" in status or "cloud_api_initialized" not in status
        
        # 模拟组件加载
        soldier.local_model = {"loaded": True}
        soldier.llm_gateway = {"initialized": True}
        soldier.redis_client = {"connected": True}
        soldier.failure_count = 2
        soldier.mode = SoldierMode.DEGRADED
        soldier.last_switch_time = 123456
        
        status = soldier.get_status()
        assert status["mode"] == "degraded"
        assert status["failure_count"] == 2
        assert status["last_switch_time"] == 123456
        assert status["local_model_loaded"] is True
        assert status["redis_connected"] is True


class TestSoldierIntegration:
    """Soldier集成测试
    
    测试组件间的协同工作
    """
    
    @pytest.mark.asyncio
    async def test_full_decision_flow_normal_mode(self):
        """测试完整决策流程 - 正常模式"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock所有依赖
        soldier._connect_redis = AsyncMock()
        soldier._init_short_term_memory = AsyncMock()
        soldier._load_local_model = AsyncMock()
        soldier._init_llm_gateway = AsyncMock()
        soldier._update_redis_status = AsyncMock()
        
        # 初始化
        await soldier.initialize()
        
        # Mock本地推理成功
        expected_decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.85,
            reasoning="技术面突破，建议买入"
        )
        soldier._local_inference = AsyncMock(return_value=expected_decision)
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_timeout_condition = AsyncMock(return_value=False)
        soldier.add_decision_to_memory = AsyncMock()
        
        # 执行决策
        market_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "timestamp": time.time()
        }
        
        decision = await soldier.make_decision(market_data)
        
        # 验证结果
        assert decision.action == "buy"
        assert decision.symbol == "000001.SZ"
        assert decision.quantity == 1000
        assert decision.confidence == 0.85
        assert decision.mode == SoldierMode.NORMAL
        assert decision.latency_ms is not None
        assert decision.latency_ms < 100  # 应该很快
        
        # 验证状态
        assert soldier.mode == SoldierMode.NORMAL
        assert soldier.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_full_decision_flow_with_failover(self):
        """测试完整决策流程 - 包含热备切换"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123",
            failure_threshold=1  # 降低阈值便于测试
        )
        
        # Mock所有依赖
        soldier._connect_redis = AsyncMock()
        soldier._init_short_term_memory = AsyncMock()
        soldier._load_local_model = AsyncMock()
        soldier._init_llm_gateway = AsyncMock()
        soldier._update_redis_status = AsyncMock()
        soldier._send_alert = AsyncMock()
        
        # 初始化
        await soldier.initialize()
        
        # Mock本地推理失败
        soldier._local_inference = AsyncMock(side_effect=RuntimeError("GPU故障"))
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_consecutive_failure_condition = AsyncMock(return_value=True)
        soldier.add_decision_to_memory = AsyncMock()
        
        # Mock云端推理成功
        cloud_decision = TradingDecision(
            action="hold",
            symbol="000001.SZ",
            quantity=0,
            confidence=0.6,
            reasoning="云端模式：市场不确定，建议观望"
        )
        soldier._cloud_inference = AsyncMock(return_value=cloud_decision)
        
        # 执行决策
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        decision = await soldier.make_decision(market_data)
        
        # 验证结果
        assert decision.action == "hold"
        assert decision.mode == SoldierMode.DEGRADED
        
        # 验证状态变化
        assert soldier.mode == SoldierMode.DEGRADED
        assert soldier.failure_count == 1
        assert soldier.last_switch_time > 0
        
        # 验证告警发送
        soldier._send_alert.assert_called()


class TestSoldierInternalMethods:
    """测试Soldier内部方法
    
    提高测试覆盖率
    """
    
    @pytest.mark.asyncio
    async def test_load_local_model_success(self):
        """测试本地模型加载成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        await soldier._load_local_model("/models/qwen-30b.gguf")
        
        assert soldier.local_model is not None
        assert soldier.local_model["loaded"] is True
    
    @pytest.mark.asyncio
    async def test_load_local_model_failure(self):
        """测试本地模型加载失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock加载失败
        with patch('asyncio.sleep', side_effect=RuntimeError("模型文件损坏")):
            soldier._send_alert = AsyncMock()
            
            with pytest.raises(RuntimeError, match="本地模型加载失败"):
                await soldier._load_local_model("/invalid/path.gguf")
            
            # 验证自动切换到云端模式
            assert soldier.mode == SoldierMode.DEGRADED
            soldier._send_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_init_llm_gateway_success(self):
        """测试LLM网关初始化成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置redis_client以便LLM网关初始化
        soldier.redis_client = {"connected": True}
        
        await soldier._init_llm_gateway()
        
        assert soldier.llm_gateway is not None
    
    @pytest.mark.asyncio
    async def test_connect_redis_success(self):
        """测试Redis连接成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        await soldier._connect_redis("localhost", 6379)
        
        assert soldier.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_connect_redis_failure(self):
        """测试Redis连接失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock连接失败
        with patch('asyncio.sleep', side_effect=ConnectionError("Redis服务不可用")):
            with pytest.raises(ConnectionError, match="Redis连接失败"):
                await soldier._connect_redis("invalid-host", 6379)
    
    @pytest.mark.asyncio
    async def test_local_inference_success(self):
        """测试本地推理成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置本地模型已加载
        soldier.local_model = {"loaded": True}
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        decision = await soldier._local_inference(market_data, 0.2)
        
        assert isinstance(decision, TradingDecision)
        assert decision.symbol == "000001.SZ"
        assert "本地模型分析" in decision.reasoning
    
    @pytest.mark.asyncio
    async def test_local_inference_no_model(self):
        """测试本地模型未加载"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 本地模型未加载
        soldier.local_model = None
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        with pytest.raises(RuntimeError, match="本地模型未加载"):
            await soldier._local_inference(market_data, 0.2)
    
    @pytest.mark.asyncio
    async def test_local_inference_timeout(self):
        """测试本地推理超时"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置本地模型已加载
        soldier.local_model = {"loaded": True}
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        # Mock超时
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            with pytest.raises(TimeoutError, match="本地推理超时"):
                await soldier._local_inference(market_data, 0.01)  # 10ms超时

    @pytest.mark.asyncio
    async def test_cloud_inference_success(self):
        """测试云端推理成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置LLM网关已初始化
        soldier.llm_gateway = MagicMock()
        soldier.llm_gateway.call_llm = AsyncMock(return_value=MagicMock(
            success=True,
            content="动作: hold\n数量: 0\n置信度: 0.7\n理由: 云端分析",
            cost=0.001
        ))
        
        market_data = {"symbol": "000002.SZ", "price": 15.8}
        decision = await soldier._cloud_inference(market_data)
        
        assert isinstance(decision, TradingDecision)
        assert decision.symbol == "000002.SZ"
    
    @pytest.mark.asyncio
    async def test_cloud_inference_no_gateway(self):
        """测试LLM网关未初始化"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # LLM网关未初始化
        soldier.llm_gateway = None
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        with pytest.raises(RuntimeError, match="LLM网关未初始化"):
            await soldier._cloud_inference(market_data)
    
    @pytest.mark.asyncio
    async def test_cloud_inference_failure_fallback(self):
        """测试云端推理失败时的降级处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置LLM网关已初始化但调用失败
        soldier.llm_gateway = MagicMock()
        soldier.llm_gateway.call_llm = AsyncMock(return_value=MagicMock(
            success=False,
            error_message="API限流"
        ))
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        # 应该降级到模拟推理
        decision = await soldier._cloud_inference(market_data)
        
        assert isinstance(decision, TradingDecision)
        assert decision.action == "hold"  # 模拟推理默认返回hold
    
    @pytest.mark.asyncio
    async def test_update_redis_status_success(self):
        """测试Redis状态更新成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 设置Redis已连接
        soldier.redis_client = {"connected": True}
        
        # 应该不抛出异常
        await soldier._update_redis_status()
    
    @pytest.mark.asyncio
    async def test_update_redis_status_no_redis(self):
        """测试Redis未连接时的状态更新"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Redis未连接
        soldier.redis_client = None
        
        # 应该不抛出异常，只是记录警告
        await soldier._update_redis_status()
    
    @pytest.mark.asyncio
    async def test_send_alert_success(self):
        """测试告警发送成功"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 应该不抛出异常
        await soldier._send_alert("测试告警消息")
    
    @pytest.mark.asyncio
    async def test_make_decision_both_inference_fail(self):
        """测试本地和云端推理都失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123",
            failure_threshold=1
        )
        
        # Mock本地推理失败
        soldier._local_inference = AsyncMock(side_effect=RuntimeError("本地故障"))
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_consecutive_failure_condition = AsyncMock(return_value=True)
        
        # Mock云端推理也失败
        soldier._cloud_inference = AsyncMock(side_effect=RuntimeError("云端故障"))
        
        # Mock其他方法
        soldier._trigger_failover = AsyncMock()
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        with pytest.raises(RuntimeError, match="本地和云端推理都失败"):
            await soldier.make_decision(market_data)
        
        # 验证触发了热备切换
        soldier._trigger_failover.assert_called_once()


class TestSoldierEdgeCases:
    """测试Soldier边界条件
    
    测试各种边界情况和异常处理
    """
    
    @pytest.mark.asyncio
    async def test_make_decision_custom_timeout(self):
        """测试自定义超时时间"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock本地推理
        expected_decision = TradingDecision(
            action="hold",
            symbol="000001.SZ",
            quantity=0,
            confidence=0.5,
            reasoning="自定义超时测试"
        )
        soldier._local_inference = AsyncMock(return_value=expected_decision)
        soldier._detect_gpu_failure_condition = AsyncMock(return_value=False)
        soldier._detect_timeout_condition = AsyncMock(return_value=False)
        soldier.add_decision_to_memory = AsyncMock()
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        # 使用自定义超时（100ms）
        decision = await soldier.make_decision(market_data, timeout_ms=100)
        
        assert decision.action == "hold"
        assert decision.mode == SoldierMode.NORMAL
        
        # 验证使用了自定义超时
        soldier._local_inference.assert_called_once_with(market_data, 0.1)  # 100ms = 0.1s
    
    def test_trading_decision_with_explicit_timestamp(self):
        """测试显式设置时间戳的交易决策"""
        explicit_timestamp = 1642435200.0  # 2022-01-17 12:00:00
        
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.8,
            reasoning="显式时间戳测试",
            timestamp=explicit_timestamp
        )
        
        assert decision.timestamp == explicit_timestamp
    
    def test_trading_decision_with_mode_and_latency(self):
        """测试包含模式和延迟的交易决策"""
        decision = TradingDecision(
            action="sell",
            symbol="000002.SZ",
            quantity=500,
            confidence=0.75,
            reasoning="完整参数测试",
            mode=SoldierMode.DEGRADED,
            latency_ms=150.5
        )
        
        assert decision.mode == SoldierMode.DEGRADED
        assert decision.latency_ms == 150.5
    
    @pytest.mark.asyncio
    async def test_gpu_health_check(self):
        """测试GPU健康检查"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 在测试环境中应该返回True
        result = await soldier._check_gpu_health()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_detect_timeout_condition(self):
        """测试超时条件检测"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 未超时
        result = await soldier._detect_timeout_condition(100.0, 200.0)
        assert result is False
        
        # 超时
        result = await soldier._detect_timeout_condition(300.0, 200.0)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_detect_consecutive_failure_condition(self):
        """测试连续失败条件检测"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123",
            failure_threshold=3
        )
        
        # 未达到阈值
        soldier.failure_count = 2
        result = await soldier._detect_consecutive_failure_condition()
        assert result is False
        
        # 达到阈值
        soldier.failure_count = 3
        result = await soldier._detect_consecutive_failure_condition()
        assert result is True


class TestGPUHealthCheckBranches:
    """测试GPU健康检查的各个分支
    
    覆盖 _check_gpu_health 方法中的所有代码路径
    """
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_rocm_smi_success(self):
        """测试rocm-smi成功返回温度信息"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock环境变量检测，使其不在测试环境
        with patch.dict('os.environ', {}, clear=True):
            # Mock subprocess.run 返回成功结果
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Temperature: 45°C"
            
            with patch('subprocess.run', return_value=mock_result):
                result = await soldier._check_gpu_health()
                assert result is True
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_rocm_smi_success_lowercase_temp(self):
        """测试rocm-smi返回小写temp"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        with patch.dict('os.environ', {}, clear=True):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "gpu temp: 50"
            
            with patch('subprocess.run', return_value=mock_result):
                result = await soldier._check_gpu_health()
                assert result is True
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_rocm_smi_failure(self):
        """测试rocm-smi命令执行失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        with patch.dict('os.environ', {}, clear=True):
            mock_result = MagicMock()
            mock_result.returncode = 1  # 非零返回码表示失败
            mock_result.stdout = ""
            
            with patch('subprocess.run', return_value=mock_result):
                result = await soldier._check_gpu_health()
                assert result is False
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_rocm_smi_not_found(self):
        """测试rocm-smi不存在，回退到设备文件检查"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        with patch.dict('os.environ', {}, clear=True):
            # Mock subprocess.run 抛出 FileNotFoundError
            with patch('subprocess.run', side_effect=FileNotFoundError("rocm-smi not found")):
                # Mock pathlib.Path 检查设备文件
                with patch('pathlib.Path') as mock_path:
                    mock_path_instance = MagicMock()
                    mock_path_instance.exists.return_value = True
                    mock_path_instance.glob.return_value = ['/dev/dri/card0', '/dev/dri/card1']
                    mock_path.return_value = mock_path_instance
                    
                    result = await soldier._check_gpu_health()
                    # 有GPU设备文件，返回True
                    assert result is True
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_rocm_smi_timeout(self):
        """测试rocm-smi超时"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        import subprocess
        with patch.dict('os.environ', {}, clear=True):
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='rocm-smi', timeout=5)):
                with patch('pathlib.Path') as mock_path:
                    mock_path_instance = MagicMock()
                    mock_path_instance.exists.return_value = False  # /dev/dri 不存在
                    mock_path.return_value = mock_path_instance
                    
                    result = await soldier._check_gpu_health()
                    # 没有GPU设备文件，返回False
                    assert result is False
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_no_gpu_devices(self):
        """测试没有GPU设备文件"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        with patch.dict('os.environ', {}, clear=True):
            with patch('subprocess.run', side_effect=FileNotFoundError()):
                with patch('pathlib.Path') as mock_path:
                    mock_path_instance = MagicMock()
                    mock_path_instance.exists.return_value = True
                    mock_path_instance.glob.return_value = []  # 没有GPU设备
                    mock_path.return_value = mock_path_instance
                    
                    result = await soldier._check_gpu_health()
                    assert result is False
    
    @pytest.mark.asyncio
    async def test_gpu_health_check_exception(self):
        """测试GPU健康检查异常处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        with patch.dict('os.environ', {}, clear=True):
            # Mock subprocess 模块导入失败
            with patch('subprocess.run', side_effect=Exception("Unexpected error")):
                result = await soldier._check_gpu_health()
                assert result is False


class TestShortTermMemoryEdgeCases:
    """测试短期记忆的边界情况"""
    
    def test_short_term_memory_decisions_limit(self):
        """测试决策列表超过10条时的截断"""
        from src.brain.soldier.core import ShortTermMemory
        
        # 创建超过10条决策的记忆
        decisions = [{"action": f"action_{i}"} for i in range(15)]
        memory = ShortTermMemory(
            positions={},
            market_sentiment=0.0,
            recent_decisions=decisions
        )
        
        # 验证被截断到10条
        assert len(memory.recent_decisions) == 10
        # 验证保留的是最后10条
        assert memory.recent_decisions[0]["action"] == "action_5"


class TestLLMGatewayInitFailure:
    """测试LLM网关初始化失败"""
    
    @pytest.mark.asyncio
    async def test_init_llm_gateway_failure(self):
        """测试LLM网关初始化失败时抛出异常"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock LLMGateway 构造函数抛出异常
        with patch('src.brain.soldier.core.LLMGateway', side_effect=Exception("Gateway init failed")):
            with pytest.raises(RuntimeError, match="LLM网关初始化失败"):
                await soldier._init_llm_gateway()


class TestRedisConnectionEdgeCases:
    """测试Redis连接的边界情况"""
    
    @pytest.mark.asyncio
    async def test_redis_import_error(self):
        """测试redis库未安装时的兼容模式"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock redis.asyncio 导入失败
        import sys
        original_modules = sys.modules.copy()
        
        # 移除redis模块模拟ImportError
        if 'redis' in sys.modules:
            del sys.modules['redis']
        if 'redis.asyncio' in sys.modules:
            del sys.modules['redis.asyncio']
        
        with patch.dict('sys.modules', {'redis': None, 'redis.asyncio': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'redis'")):
                # 这会触发兼容模式
                try:
                    await soldier._connect_redis("localhost", 6379)
                except (ImportError, ConnectionError):
                    pass  # 预期的异常
        
        # 恢复模块
        sys.modules.update(original_modules)


class TestLocalInferenceWithRealEngine:
    """测试本地推理使用真实引擎的分支"""
    
    @pytest.mark.asyncio
    async def test_local_inference_with_infer_method(self):
        """测试本地模型有infer方法时的推理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个有infer方法的mock模型
        mock_model = MagicMock()
        expected_decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.9,
            reasoning="Real engine decision"
        )
        mock_model.infer = AsyncMock(return_value=expected_decision)
        
        soldier.local_model = mock_model
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        decision = await soldier._local_inference(market_data, 0.2)
        
        assert decision == expected_decision
        mock_model.infer.assert_called_once_with(market_data, timeout_ms=200)


class TestRedisStatusUpdateEdgeCases:
    """测试Redis状态更新的边界情况"""
    
    @pytest.mark.asyncio
    async def test_update_redis_status_with_real_redis(self):
        """测试使用真实Redis客户端更新状态"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个有set方法的mock Redis客户端
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        
        soldier.redis_client = mock_redis
        
        await soldier._update_redis_status()
        
        # 验证调用了set方法
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_redis_status_exception(self):
        """测试Redis状态更新异常处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个会抛出异常的mock Redis客户端
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))
        
        soldier.redis_client = mock_redis
        
        # 应该不抛出异常，只记录日志
        await soldier._update_redis_status()


class TestMemoryOperationsEdgeCases:
    """测试记忆操作的边界情况"""
    
    @pytest.mark.asyncio
    async def test_update_position_no_memory(self):
        """测试短期记忆未初始化时更新仓位"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.short_term_memory = None
        
        # 应该不抛出异常，只记录警告
        await soldier.update_position("000001.SZ", 1000)
    
    @pytest.mark.asyncio
    async def test_update_position_exception(self):
        """测试更新仓位时异常处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个会抛出异常的mock记忆
        mock_memory = MagicMock()
        mock_memory.update_position = MagicMock(side_effect=Exception("Memory error"))
        
        soldier.short_term_memory = mock_memory
        
        # 应该不抛出异常，只记录日志
        await soldier.update_position("000001.SZ", 1000)
    
    @pytest.mark.asyncio
    async def test_update_market_sentiment_no_memory(self):
        """测试短期记忆未初始化时更新情绪"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.short_term_memory = None
        
        # 应该不抛出异常，只记录警告
        await soldier.update_market_sentiment(0.5)
    
    @pytest.mark.asyncio
    async def test_update_market_sentiment_exception(self):
        """测试更新情绪时异常处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        mock_memory = MagicMock()
        mock_memory.update_sentiment = MagicMock(side_effect=Exception("Sentiment error"))
        
        soldier.short_term_memory = mock_memory
        
        # 应该不抛出异常，只记录日志
        await soldier.update_market_sentiment(0.5)
    
    @pytest.mark.asyncio
    async def test_add_decision_to_memory_no_memory(self):
        """测试短期记忆未初始化时添加决策"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.short_term_memory = None
        
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.8,
            reasoning="Test"
        )
        
        # 应该不抛出异常，只记录警告
        await soldier.add_decision_to_memory(decision)
    
    @pytest.mark.asyncio
    async def test_add_decision_to_memory_exception(self):
        """测试添加决策时异常处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        mock_memory = MagicMock()
        mock_memory.add_decision = MagicMock(side_effect=Exception("Decision error"))
        
        soldier.short_term_memory = mock_memory
        
        decision = TradingDecision(
            action="buy",
            symbol="000001.SZ",
            quantity=1000,
            confidence=0.8,
            reasoning="Test"
        )
        
        # 应该不抛出异常，只记录日志
        await soldier.add_decision_to_memory(decision)
    
    def test_get_memory_status_no_memory(self):
        """测试短期记忆未初始化时获取状态"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.short_term_memory = None
        
        status = soldier.get_memory_status()
        assert status == {"status": "not_initialized"}


class TestSendAlertEdgeCases:
    """测试告警发送的边界情况"""
    
    @pytest.mark.asyncio
    async def test_send_alert_no_webhook(self):
        """测试没有配置webhook时的告警"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.config = {}  # 没有webhook配置
        
        # 应该不抛出异常
        await soldier._send_alert("Test alert")
    
    @pytest.mark.asyncio
    async def test_send_alert_with_webhook_success(self):
        """测试配置webhook时成功发送告警"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.config = {"wechat_webhook_url": "https://example.com/webhook"}
        
        # Mock aiohttp
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            await soldier._send_alert("Test alert")
    
    @pytest.mark.asyncio
    async def test_send_alert_with_webhook_failure(self):
        """测试配置webhook时发送失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.config = {"wechat_webhook_url": "https://example.com/webhook"}
        
        # Mock aiohttp 返回错误状态
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # 应该不抛出异常
            await soldier._send_alert("Test alert")
    
    @pytest.mark.asyncio
    async def test_send_alert_exception(self):
        """测试告警发送异常处理"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        soldier.config = {"wechat_webhook_url": "https://example.com/webhook"}
        
        with patch('aiohttp.ClientSession', side_effect=Exception("Network error")):
            # 应该不抛出异常
            await soldier._send_alert("Test alert")


class TestLocalInferenceExceptions:
    """测试本地推理的异常分支"""
    
    @pytest.mark.asyncio
    async def test_local_inference_general_exception(self):
        """测试本地推理一般异常"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个会抛出异常的mock模型
        mock_model = MagicMock()
        mock_model.infer = AsyncMock(side_effect=Exception("Inference failed"))
        
        soldier.local_model = mock_model
        
        market_data = {"symbol": "000001.SZ", "price": 10.5}
        
        with pytest.raises(RuntimeError, match="本地推理失败"):
            await soldier._local_inference(market_data, 0.2)


class TestLLMResponseParsing:
    """测试LLM响应解析的各种情况"""
    
    def test_parse_llm_response_quantity_parse_error(self):
        """测试数量解析失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        content = """动作: buy
数量: invalid_number
置信度: 0.8
理由: 测试"""
        
        market_data = {"symbol": "000001.SZ"}
        decision = soldier._parse_llm_response(content, market_data)
        
        assert decision.action == "buy"
        assert decision.quantity == 0  # 解析失败默认为0
    
    def test_parse_llm_response_confidence_parse_error(self):
        """测试置信度解析失败"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        content = """动作: sell
数量: 100
置信度: not_a_number
理由: 测试"""
        
        market_data = {"symbol": "000001.SZ"}
        decision = soldier._parse_llm_response(content, market_data)
        
        assert decision.action == "sell"
        assert decision.confidence == 0.5  # 解析失败默认为0.5
    
    def test_parse_llm_response_exception(self):
        """测试解析异常时返回默认决策"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 传入会导致异常的内容（None转字符串会失败）
        market_data = {"symbol": "000001.SZ"}
        
        # 直接传入一个会导致split失败的对象
        class BadContent:
            def strip(self):
                raise Exception("Parse error")
        
        # 由于_parse_llm_response期望字符串，我们测试空内容
        decision = soldier._parse_llm_response("", market_data)
        
        # 空内容应该返回默认值
        assert decision.action == "hold"
        assert decision.confidence == 0.5


class TestShortTermMemoryInitialization:
    """测试短期记忆初始化的各种情况"""
    
    @pytest.mark.asyncio
    async def test_init_short_term_memory_create_new(self):
        """测试创建新的短期记忆"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock _load_memory_from_redis 返回 None
        soldier._load_memory_from_redis = AsyncMock(return_value=None)
        soldier._save_memory_to_redis = AsyncMock()
        
        await soldier._init_short_term_memory()
        
        assert soldier.short_term_memory is not None
        assert soldier.short_term_memory.positions == {}
        soldier._save_memory_to_redis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_init_short_term_memory_exception(self):
        """测试短期记忆初始化异常"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # Mock _load_memory_from_redis 抛出异常
        soldier._load_memory_from_redis = AsyncMock(side_effect=Exception("Redis error"))
        
        await soldier._init_short_term_memory()
        
        # 应该创建默认记忆
        assert soldier.short_term_memory is not None
        assert soldier.short_term_memory.positions == {}


class TestLoadMemoryFromRedis:
    """测试从Redis加载记忆的各种情况"""
    
    @pytest.mark.asyncio
    async def test_load_memory_with_real_redis(self):
        """测试使用真实Redis加载记忆"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建有get方法的mock Redis
        mock_redis = MagicMock()
        memory_data = {
            "positions": {"000001.SZ": 1000},
            "market_sentiment": 0.5,
            "recent_decisions": [],
            "last_update": 123456.0,
            "session_id": "test123"
        }
        mock_redis.get = AsyncMock(return_value=json.dumps(memory_data))
        
        soldier.redis_client = mock_redis
        
        result = await soldier._load_memory_from_redis()
        
        assert result == memory_data
    
    @pytest.mark.asyncio
    async def test_load_memory_redis_returns_none(self):
        """测试Redis返回None"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        
        soldier.redis_client = mock_redis
        
        result = await soldier._load_memory_from_redis()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_load_memory_exception(self):
        """测试加载记忆异常"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        
        soldier.redis_client = mock_redis
        
        result = await soldier._load_memory_from_redis()
        
        assert result is None


class TestParseResponseException:
    """测试LLM响应解析异常分支"""
    
    def test_parse_llm_response_with_exception_in_parsing(self):
        """测试解析过程中抛出异常"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个会在第一次调用时抛异常，第二次正常的market_data
        call_count = [0]
        
        class PartialBadDict(dict):
            def get(self, key, default=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    # 第一次调用（在try块中）抛异常
                    raise Exception("Bad dict access")
                # 后续调用（在except块中）正常返回
                return super().get(key, default)
        
        # 正常内容但market_data第一次会抛异常
        content = """动作: buy
数量: 100
置信度: 0.8
理由: 测试"""
        
        bad_market_data = PartialBadDict({"symbol": "000001.SZ"})
        
        # 应该捕获异常并返回默认决策
        decision = soldier._parse_llm_response(content, bad_market_data)
        
        assert decision.action == "hold"
        assert decision.confidence == 0.5
        assert "解析失败" in decision.reasoning


class TestLoadMemoryJsonParseError:
    """测试从Redis加载记忆时JSON解析错误"""
    
    @pytest.mark.asyncio
    async def test_load_memory_json_parse_error(self):
        """测试Redis返回无效JSON"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        mock_redis = MagicMock()
        # 返回无效的JSON字符串
        mock_redis.get = AsyncMock(return_value="invalid json {{{")
        
        soldier.redis_client = mock_redis
        
        # 应该捕获异常并返回None
        result = await soldier._load_memory_from_redis()
        
        assert result is None


class TestLoadMemoryCompatibleMode:
    """测试从Redis加载记忆的兼容模式"""
    
    @pytest.mark.asyncio
    async def test_load_memory_compatible_mode(self):
        """测试兼容模式（redis_client没有get方法）"""
        soldier = SoldierWithFailover(
            local_model_path="/models/qwen-30b.gguf",
            cloud_api_key="sk-test123"
        )
        
        # 创建一个真正没有get方法的对象（不能用dict，因为dict有get方法）
        class NoGetClient:
            connected = True
            mode = "compatible"
        
        soldier.redis_client = NoGetClient()
        
        result = await soldier._load_memory_from_redis()
        
        # 兼容模式应该返回None
        assert result is None
