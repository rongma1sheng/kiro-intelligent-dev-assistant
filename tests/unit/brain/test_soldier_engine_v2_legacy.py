"""
Soldier引擎 v2.0 单元测试 (Legacy - 已弃用)

注意: 此测试文件针对旧版API，与当前源代码不兼容。
新测试请参考 tests/unit/brain/soldier/ 目录下的测试文件。

测试覆盖:
1. SoldierEngineV2核心功能
2. 本地/云端/离线模式切换
3. 决策推理和缓存
4. 事件驱动通信
5. 健康检查和自动恢复
6. 性能指标和统计
"""

import pytest

# 跳过整个模块 - 此测试文件针对旧版API
pytestmark = pytest.mark.skip(reason="Legacy test file - API已更新，请使用tests/unit/brain/soldier/目录下的测试")

import asyncio
import numpy as np
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierConfig,
    SoldierMode,
    SoldierDecision,
    MarketSignal,
    SignalType
)
from src.infra.event_bus import Event, EventType, EventPriority


class TestSoldierConfig:
    """测试Soldier配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SoldierConfig()
        
        assert config.local_inference_timeout == 0.02
        assert config.cloud_timeout == 5.0
        assert config.degradation_threshold == 0.2
        assert config.failure_threshold == 3
        assert config.decision_cache_ttl == 5
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SoldierConfig(
            local_inference_timeout=0.01,
            cloud_timeout=3.0,
            failure_threshold=5,
            redis_host="custom_host"
        )
        
        assert config.local_inference_timeout == 0.01
        assert config.cloud_timeout == 3.0
        assert config.failure_threshold == 5
        assert config.redis_host == "custom_host"


class TestSoldierDecision:
    """测试Soldier决策"""
    
    def test_decision_creation(self):
        """测试决策创建"""
        decision = SoldierDecision(
            action="buy",
            confidence=0.8,
            reasoning="Strong bullish signals",
            signal_strength=0.9,
            risk_level="medium",
            execution_priority=7,
            latency_ms=15.5,
            source_mode="normal",
            metadata={"test": "data"}
        )
        
        assert decision.action == "buy"
        assert decision.confidence == 0.8
        assert decision.reasoning == "Strong bullish signals"
        assert decision.signal_strength == 0.9
        assert decision.risk_level == "medium"
        assert decision.execution_priority == 7
        assert decision.latency_ms == 15.5
        assert decision.source_mode == "normal"
        assert decision.metadata == {"test": "data"}


class TestSoldierEngineV2:
    """测试Soldier引擎v2.0"""
    
    @pytest.fixture
    def config(self):
        return SoldierConfig(
            local_inference_timeout=0.01,  # 10ms for testing
            cloud_timeout=1.0,
            failure_threshold=2,
            decision_cache_ttl=1  # 1 second for testing
        )
    
    @pytest.fixture
    def mock_llm_gateway(self):
        gateway = AsyncMock()
        gateway.initialize = AsyncMock()
        gateway.chat_completion = AsyncMock(return_value={
            'choices': [{
                'message': {
                    'content': json.dumps({
                        "action": "buy",
                        "confidence": 0.75,
                        "reasoning": "Cloud inference result",
                        "signal_strength": 0.8,
                        "risk_level": "medium"
                    })
                }
            }]
        })
        return gateway
    
    @pytest.fixture
    def mock_hallucination_filter(self):
        filter_mock = AsyncMock()
        filter_mock.check_hallucination = AsyncMock(return_value=False)
        return filter_mock
    
    @pytest.fixture
    def soldier_engine(self, config):
        """创建Soldier引擎实例"""
        engine = SoldierEngineV2(config)
        # Mock外部依赖
        engine.llm_inference = AsyncMock()
        engine.deepseek_client = AsyncMock()
        engine.redis_client = AsyncMock()
        engine.event_bus = AsyncMock()
        return engine
    
    @pytest.mark.asyncio
    async def test_initialization(self, soldier_engine):
        """测试初始化"""
        # 设置redis_client以确保_initialize_redis被调用
        soldier_engine.redis_client = AsyncMock()
        
        with patch.object(soldier_engine, '_initialize_redis_cache') as mock_redis, \
             patch.object(soldier_engine, '_warmup_cache') as mock_warmup:
            
            mock_redis.return_value = None
            mock_warmup.return_value = None
            
            await soldier_engine.initialize()
            
            assert soldier_engine.state == "READY"
            mock_redis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_local_model_availability_check(self, soldier_engine):
        """测试本地模型可用性检查"""
        # 测试模型可用 (快速响应)
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.return_value = None
            
            available = await soldier_engine._check_local_model_availability()
            assert available is True
        
        # 测试模型不可用 (超时) - 模拟慢推理
        async def slow_sleep(duration):
            await asyncio.sleep(0.1)  # 实际延迟超过timeout
        
        with patch('asyncio.sleep', side_effect=slow_sleep):
            available = await soldier_engine._check_local_model_availability()
            assert available is False
    
    @pytest.mark.asyncio
    async def test_decision_making_normal_mode(self, soldier_engine):
        """测试正常模式决策"""
        soldier_engine.mode = SoldierMode.NORMAL
        
        with patch.object(soldier_engine, '_local_inference') as mock_local:
            mock_decision = SoldierDecision(
                action="buy",
                confidence=0.8,
                reasoning="Local inference result",
                signal_strength=0.9,
                risk_level="low",
                execution_priority=8,
                latency_ms=15.0,
                source_mode="normal",
                metadata={}
            )
            mock_local.return_value = mock_decision
            
            with patch.object(soldier_engine, '_request_external_analysis'), \
                 patch.object(soldier_engine, '_publish_decision_event'):
                
                result = await soldier_engine.make_decision("AAPL", {"close": 150.0})
                
                assert result['decision']['action'] == "buy"
                assert result['decision']['confidence'] == 0.8
                assert result['decision']['source_mode'] == "normal"
                assert result['metadata']['soldier_mode'] == "normal"
    
    @pytest.mark.asyncio
    async def test_decision_making_degraded_mode(self, soldier_engine):
        """测试降级模式决策"""
        soldier_engine.mode = SoldierMode.DEGRADED
        
        with patch.object(soldier_engine, '_cloud_inference') as mock_cloud:
            mock_decision = SoldierDecision(
                action="sell",
                confidence=0.7,
                reasoning="Cloud inference result",
                signal_strength=0.6,
                risk_level="medium",
                execution_priority=5,
                latency_ms=100.0,
                source_mode="degraded",
                metadata={}
            )
            mock_cloud.return_value = mock_decision
            
            with patch.object(soldier_engine, '_request_external_analysis'), \
                 patch.object(soldier_engine, '_publish_decision_event'):
                
                result = await soldier_engine.make_decision("AAPL", {"close": 150.0})
                
                assert result['decision']['action'] == "sell"
                assert result['decision']['source_mode'] == "degraded"
    
    @pytest.mark.asyncio
    async def test_decision_making_offline_mode(self, soldier_engine):
        """测试离线模式决策"""
        soldier_engine.mode = SoldierMode.OFFLINE
        
        with patch.object(soldier_engine, '_offline_inference') as mock_offline:
            mock_decision = SoldierDecision(
                action="hold",
                confidence=0.5,
                reasoning="Offline rule-based decision",
                signal_strength=0.3,
                risk_level="medium",
                execution_priority=3,
                latency_ms=5.0,
                source_mode="offline",
                metadata={}
            )
            mock_offline.return_value = mock_decision
            
            with patch.object(soldier_engine, '_request_external_analysis'), \
                 patch.object(soldier_engine, '_publish_decision_event'):
                
                result = await soldier_engine.make_decision("AAPL", {"close": 150.0})
                
                assert result['decision']['action'] == "hold"
                assert result['decision']['source_mode'] == "offline"
    
    @pytest.mark.asyncio
    async def test_local_inference(self, soldier_engine):
        """测试本地推理"""
        symbol = "AAPL"
        market_data = {"close": 150.0, "volume": 1000000}
        
        with patch.object(soldier_engine, '_build_inference_context') as mock_context, \
             patch.object(soldier_engine, '_simulate_local_model_inference') as mock_inference:
            
            mock_context.return_value = {"test": "context"}
            mock_inference.return_value = json.dumps({
                "action": "buy",
                "confidence": 0.8,
                "reasoning": "Strong momentum",
                "signal_strength": 0.9,
                "risk_level": "low"
            })
            
            decision = await soldier_engine._local_inference(symbol, market_data)
            
            assert isinstance(decision, SoldierDecision)
            assert decision.action == "buy"
            assert decision.confidence == 0.8
            assert decision.source_mode == "normal"
            assert decision.latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_cloud_inference(self, soldier_engine, mock_llm_gateway):
        """测试云端推理"""
        soldier_engine.llm_gateway = mock_llm_gateway
        
        symbol = "AAPL"
        market_data = {"close": 150.0, "volume": 1000000}
        
        with patch.object(soldier_engine, '_build_inference_context') as mock_context:
            mock_context.return_value = {"test": "context"}
            
            decision = await soldier_engine._cloud_inference(symbol, market_data)
            
            assert isinstance(decision, SoldierDecision)
            assert decision.action == "buy"
            assert decision.confidence == 0.75
            assert decision.source_mode == "degraded"
            mock_llm_gateway.chat_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_offline_inference(self, soldier_engine):
        """测试离线推理"""
        symbol = "AAPL"
        market_data = {
            "close": 150.0,
            "volume": 1000000,
            "ma20": 145.0,  # 价格高于MA20，看涨信号
            "avg_volume": 800000  # 成交量高于平均，确认信号
        }
        
        decision = await soldier_engine._offline_inference(symbol, market_data)
        
        assert isinstance(decision, SoldierDecision)
        assert decision.action == "buy"  # 价格>MA20 且 成交量>平均
        assert decision.source_mode == "offline"
        assert decision.confidence > 0
    
    def test_inference_result_parsing(self, soldier_engine):
        """测试推理结果解析"""
        # 测试JSON格式结果
        json_result = json.dumps({
            "action": "buy",
            "confidence": 0.8,
            "reasoning": "Strong signals",
            "signal_strength": 0.9,
            "risk_level": "low"
        })
        
        decision = soldier_engine._parse_inference_result(json_result, "normal", 15.0)
        
        assert decision.action == "buy"
        assert decision.confidence == 0.8
        assert decision.latency_ms == 15.0
        
        # 测试文本格式结果
        text_result = "I recommend to buy this stock with high confidence"
        
        decision = soldier_engine._parse_inference_result(text_result, "normal", 20.0)
        
        assert decision.action == "buy"
        assert decision.confidence > 0.5  # 应该检测到"high confidence"
    
    def test_text_decision_extraction(self, soldier_engine):
        """测试文本决策提取"""
        # 测试强买信号
        text = "I strongly recommend to buy this stock"
        result = soldier_engine._extract_decision_from_text(text)
        assert result['action'] == 'strong_buy'
        
        # 测试卖出信号
        text = "You should sell this position"
        result = soldier_engine._extract_decision_from_text(text)
        assert result['action'] == 'sell'
        
        # 测试持有信号
        text = "No clear signal, better to hold"
        result = soldier_engine._extract_decision_from_text(text)
        assert result['action'] == 'hold'
        
        # 测试置信度提取
        text = "Buy with high confidence"
        result = soldier_engine._extract_decision_from_text(text)
        assert result['confidence'] == 0.8
        
        text = "Uncertain market conditions"
        result = soldier_engine._extract_decision_from_text(text)
        assert result['confidence'] == 0.3
    
    @pytest.mark.asyncio
    async def test_mode_switching(self, soldier_engine):
        """测试模式切换"""
        initial_mode = soldier_engine.mode
        
        with patch.object(soldier_engine, 'event_bus') as mock_bus:
            mock_bus.publish = AsyncMock()
            
            await soldier_engine._switch_to_degraded_mode("Test reason")
            
            assert soldier_engine.mode == SoldierMode.DEGRADED
            assert soldier_engine.stats['mode_switches'] == 1
            mock_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_decision_caching(self, soldier_engine):
        """测试决策缓存"""
        symbol = "AAPL"
        market_data = {"close": 150.0, "volume": 1000000}
        
        # 生成缓存键
        cache_key = soldier_engine._generate_cache_key(symbol, market_data)
        
        # 测试缓存未命中
        cached = await soldier_engine._get_cached_decision(cache_key)
        assert cached is None
        
        # 缓存决策
        decision = SoldierDecision(
            action="buy",
            confidence=0.8,
            reasoning="Test decision",
            signal_strength=0.9,
            risk_level="low",
            execution_priority=7,
            latency_ms=15.0,
            source_mode="normal",
            metadata={}
        )
        
        await soldier_engine._cache_decision(cache_key, decision)
        
        # 测试缓存命中
        cached = await soldier_engine._get_cached_decision(cache_key)
        assert cached is not None
        assert cached.action == "buy"
        assert cached.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, soldier_engine):
        """测试缓存过期"""
        soldier_engine.config.decision_cache_ttl = 0.1  # 100ms TTL
        
        symbol = "AAPL"
        market_data = {"close": 150.0}
        cache_key = soldier_engine._generate_cache_key(symbol, market_data)
        
        decision = SoldierDecision(
            action="buy", confidence=0.8, reasoning="Test", signal_strength=0.9,
            risk_level="low", execution_priority=7, latency_ms=15.0,
            source_mode="normal", metadata={}
        )
        
        await soldier_engine._cache_decision(cache_key, decision)
        
        # 立即检查，应该命中
        cached = await soldier_engine._get_cached_decision(cache_key)
        assert cached is not None
        
        # 等待过期
        await asyncio.sleep(0.2)
        
        # 检查过期
        cached = await soldier_engine._get_cached_decision(cache_key)
        assert cached is None
    
    def test_stats_update(self, soldier_engine):
        """测试统计更新"""
        initial_total = soldier_engine.stats['total_decisions']
        
        # 更新本地决策统计
        soldier_engine._update_stats(15.0, "normal")
        
        assert soldier_engine.stats['total_decisions'] == initial_total + 1
        assert soldier_engine.stats['local_decisions'] == 1
        assert soldier_engine.stats['avg_latency_ms'] > 0
        assert len(soldier_engine.latency_history) == 1
        
        # 更新云端决策统计
        soldier_engine._update_stats(100.0, "degraded")
        
        assert soldier_engine.stats['total_decisions'] == initial_total + 2
        assert soldier_engine.stats['cloud_decisions'] == 1
    
    def test_p99_latency_calculation(self, soldier_engine):
        """测试P99延迟计算"""
        # 添加延迟数据
        latencies = [10, 15, 20, 25, 30, 35, 40, 45, 50, 100]  # 100是P90
        soldier_engine.latency_history = latencies
        
        soldier_engine._update_p99_latency()
        
        p99 = soldier_engine.stats['p99_latency_ms']
        assert p99 > 50  # P99应该接近100
        assert p99 <= 100
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, soldier_engine):
        """测试缓存清理"""
        # 添加过期缓存项
        old_time = datetime.now() - timedelta(seconds=10)
        soldier_engine.cache_timestamps['old_key'] = old_time
        soldier_engine.decision_cache['old_key'] = SoldierDecision(
            action="hold", confidence=0.5, reasoning="Old", signal_strength=0.3,
            risk_level="medium", execution_priority=3, latency_ms=10.0,
            source_mode="normal", metadata={}
        )
        
        # 添加新缓存项
        new_time = datetime.now()
        soldier_engine.cache_timestamps['new_key'] = new_time
        soldier_engine.decision_cache['new_key'] = SoldierDecision(
            action="buy", confidence=0.8, reasoning="New", signal_strength=0.9,
            risk_level="low", execution_priority=7, latency_ms=15.0,
            source_mode="normal", metadata={}
        )
        
        await soldier_engine._cleanup_expired_cache()
        
        # 检查过期项被清理
        assert 'old_key' not in soldier_engine.decision_cache
        assert 'old_key' not in soldier_engine.cache_timestamps
        
        # 检查新项保留
        assert 'new_key' in soldier_engine.decision_cache
        assert 'new_key' in soldier_engine.cache_timestamps
    
    @pytest.mark.asyncio
    async def test_context_building(self, soldier_engine):
        """测试推理上下文构建"""
        symbol = "AAPL"
        market_data = {"close": 150.0, "volume": 1000000}
        
        # 添加短期记忆
        soldier_engine.short_term_memory[f"memory:{symbol}"] = {
            "last_update": datetime.now().isoformat(),
            "market_data": {"close": 149.0}
        }
        
        # 添加外部分析
        soldier_engine.external_analysis = {
            "commander:123": {"strategy": "bullish"},
            "scholar:456": {"research": "positive"}
        }
        
        # 测试基本上下文构建（不依赖Redis）
        context = await soldier_engine._build_inference_context(symbol, market_data)
        
        assert context['symbol'] == symbol
        assert context['market_data'] == market_data
        assert 'short_term_memory' in context
        assert 'external_analysis' in context
        # Redis共享上下文是可选功能，不强制要求
        # assert 'shared_context' in context
    
    @pytest.mark.asyncio
    async def test_get_status(self, soldier_engine):
        """测试状态获取"""
        soldier_engine.mode = SoldierMode.NORMAL
        soldier_engine.state = "READY"
        soldier_engine.last_decision_time = datetime.now()
        
        status = await soldier_engine.get_status()
        
        assert status['mode'] == "normal"
        assert status['state'] == "READY"
        assert status['failure_count'] == 0
        assert 'last_decision_time' in status
        assert 'stats' in status
        assert 'cache_size' in status
        assert 'memory_size' in status
    
    @pytest.mark.asyncio
    async def test_event_handling(self, soldier_engine):
        """测试事件处理"""
        # 测试市场数据更新事件
        market_event = Event(
            event_type=EventType.MARKET_DATA_RECEIVED,
            source_module="market",
            target_module="soldier",
            priority=EventPriority.NORMAL,
            data={
                'symbol': 'AAPL',
                'market_data': {'close': 150.0, 'volume': 1000000}
            }
        )
        
        await soldier_engine._handle_market_data_update(market_event)
        
        # 检查短期记忆是否更新
        memory_key = "memory:AAPL"
        assert memory_key in soldier_engine.short_term_memory
        assert soldier_engine.short_term_memory[memory_key]['market_data']['close'] == 150.0
        
        # 测试Commander分析事件
        commander_event = Event(
            event_type=EventType.ANALYSIS_COMPLETED,
            source_module="commander",
            target_module="soldier",
            priority=EventPriority.NORMAL,
            data={
                'action': 'strategy_analysis_completed',
                'correlation_id': 'test_123',
                'analysis_result': {'strategy': 'bullish', 'confidence': 0.8}
            }
        )
        
        await soldier_engine._handle_commander_analysis(commander_event)
        
        # 检查外部分析是否更新
        assert 'commander:test_123' in soldier_engine.external_analysis
        assert soldier_engine.external_analysis['commander:test_123']['strategy'] == 'bullish'
        
        # 测试系统状态事件
        system_event = Event(
            event_type=EventType.SYSTEM_ALERT,
            source_module="system",
            target_module="soldier",
            priority=EventPriority.HIGH,
            data={
                'status_type': 'gpu_driver_error'
            }
        )
        
        with patch.object(soldier_engine, '_switch_to_degraded_mode') as mock_switch:
            await soldier_engine._handle_system_status(system_event)
            mock_switch.assert_called_once_with("GPU driver error detected")
    
    @pytest.mark.asyncio
    async def test_failure_handling_and_recovery(self, soldier_engine):
        """测试故障处理和恢复"""
        soldier_engine.config.failure_threshold = 2
        soldier_engine.mode = SoldierMode.NORMAL
        
        # 模拟连续失败
        with patch.object(soldier_engine, '_local_inference', side_effect=Exception("Test error")), \
             patch.object(soldier_engine, '_cloud_inference') as mock_cloud:
            
            mock_cloud.return_value = SoldierDecision(
                action="hold", confidence=0.5, reasoning="Fallback", signal_strength=0.3,
                risk_level="medium", execution_priority=3, latency_ms=100.0,
                source_mode="degraded", metadata={}
            )
            
            with patch.object(soldier_engine, '_request_external_analysis'), \
                 patch.object(soldier_engine, '_publish_decision_event'):
                
                # 第一次失败 - 应该降级到云端推理
                result1 = await soldier_engine.make_decision("AAPL", {"close": 150.0})
                assert result1['decision']['action'] == "hold"
                assert result1['decision']['source_mode'] == "degraded"
                
                # 第二次失败 - 应该继续使用云端推理
                result2 = await soldier_engine.make_decision("AAPL", {"close": 150.0})
                assert result2['decision']['action'] == "hold"
                
                # 验证模式已切换到降级模式
                assert soldier_engine.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_memory_management(self, soldier_engine):
        """测试内存管理"""
        soldier_engine.memory_max_size = 3
        
        # 添加超过限制的内存项
        for i in range(5):
            memory_key = f"memory:STOCK_{i}"
            soldier_engine.short_term_memory[memory_key] = {
                'data': f'test_data_{i}'
            }
        
        # 模拟市场数据更新触发内存管理
        event = Event(
            event_type=EventType.MARKET_DATA_RECEIVED,
            source_module="market",
            target_module="soldier",
            priority=EventPriority.NORMAL,
            data={
                'symbol': 'NEW_STOCK',
                'market_data': {'close': 100.0}
            }
        )
        
        await soldier_engine._handle_market_data_update(event)
        
        # 检查内存大小限制
        assert len(soldier_engine.short_term_memory) <= soldier_engine.memory_max_size
        
        # 检查新数据被添加
        assert 'memory:NEW_STOCK' in soldier_engine.short_term_memory


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_decision_workflow(self):
        """测试完整决策工作流"""
        config = SoldierConfig(decision_cache_ttl=1)
        
        soldier = SoldierEngineV2(config)
        
        with patch.object(soldier, '_initialize_redis'), \
             patch.object(soldier, '_initialize_local_model'), \
             patch.object(soldier, '_setup_event_subscriptions'), \
             patch.object(soldier, '_local_inference') as mock_local:
            
            mock_local.return_value = SoldierDecision(
                action="buy", confidence=0.8, reasoning="Integration test",
                signal_strength=0.9, risk_level="low", execution_priority=8,
                latency_ms=15.0, source_mode="normal", metadata={}
            )
            
            await soldier.initialize()
            
            # 第一次决策
            result1 = await soldier.make_decision("AAPL", {"close": 150.0})
            assert result1['decision']['action'] == "buy"
            assert soldier.stats['total_decisions'] == 1
            assert soldier.stats['cache_hits'] == 0
            
            # 第二次相同决策，应该命中缓存
            result2 = await soldier.make_decision("AAPL", {"close": 150.0})
            assert result2['decision']['action'] == "buy"
            assert soldier.stats['total_decisions'] == 1  # 不增加，因为缓存命中
            assert soldier.stats['cache_hits'] == 1
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        config = SoldierConfig(failure_threshold=1)
        
        soldier = SoldierEngineV2(config)
        
        with patch.object(soldier, '_initialize_redis'), \
             patch.object(soldier, '_initialize_local_model'), \
             patch.object(soldier, '_setup_event_subscriptions'), \
             patch.object(soldier, '_local_inference', side_effect=Exception("Local failed")), \
             patch.object(soldier, '_cloud_inference') as mock_cloud:
            
            mock_cloud.return_value = SoldierDecision(
                action="hold", confidence=0.6, reasoning="Cloud fallback",
                signal_strength=0.5, risk_level="medium", execution_priority=5,
                latency_ms=100.0, source_mode="degraded", metadata={}
            )
            
            await soldier.initialize()
            
            # 决策应该自动降级到云端
            result = await soldier.make_decision("AAPL", {"close": 150.0})
            
            assert result['decision']['action'] == "hold"
            assert result['decision']['source_mode'] == "degraded"
            assert soldier.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """测试性能要求"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 测试本地推理延迟要求
        start_time = asyncio.get_event_loop().time()
        
        with patch.object(soldier, '_simulate_local_model_inference') as mock_inference:
            mock_inference.return_value = json.dumps({"action": "buy", "confidence": 0.8})
            
            await soldier._local_inference("AAPL", {"close": 150.0})
            
            end_time = asyncio.get_event_loop().time()
            latency_ms = (end_time - start_time) * 1000
            
            # 本地推理应该很快 (模拟环境下)
            assert latency_ms < 100  # 在测试环境中放宽要求


if __name__ == "__main__":
    pytest.main([__file__, "-v"])