"""
Soldier Engine V2 单元测试

白皮书依据: 第二章 2.1 AI三脑架构 - Soldier (执行层)

测试当前实现的核心功能:
- 配置和数据类
- 核心决策方法
- 缓存功能
- 风险评估（架构A）
- 状态管理
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierConfig,
    SoldierMode,
    SoldierDecision,
    RiskLevel,
    RiskAssessment,
    SignalType,
    MarketSignal
)


class TestSoldierConfig:
    """测试Soldier配置 - 白皮书: 第二章 2.1.2 运行模式"""
    
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
        assert config.cache_key_prefix == "soldier:decision:"
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SoldierConfig(
            local_inference_timeout=0.01,
            cloud_timeout=3.0,
            failure_threshold=5,
            redis_host="custom_host",
            decision_cache_ttl=10
        )
        
        assert config.local_inference_timeout == 0.01
        assert config.cloud_timeout == 3.0
        assert config.failure_threshold == 5
        assert config.redis_host == "custom_host"
        assert config.decision_cache_ttl == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



class TestSoldierDataClasses:
    """测试Soldier数据类"""
    
    def test_soldier_decision_creation(self):
        """测试SoldierDecision创建"""
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
    
    def test_risk_level_enum(self):
        """测试RiskLevel枚举"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
    
    def test_risk_assessment_creation(self):
        """测试RiskAssessment创建"""
        assessment = RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            volatility=0.03,
            liquidity=500000.0,
            correlation=0.65,
            risk_score=0.45,
            factors={"symbol": "000001"},
            timestamp="2026-01-22T10:00:00"
        )
        
        assert assessment.risk_level == RiskLevel.MEDIUM
        assert assessment.volatility == 0.03
        assert assessment.liquidity == 500000.0
        assert assessment.correlation == 0.65
        assert assessment.risk_score == 0.45
        assert assessment.factors["symbol"] == "000001"
    
    def test_signal_type_enum(self):
        """测试SignalType枚举"""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"
    
    def test_market_signal_creation(self):
        """测试MarketSignal创建"""
        signal = MarketSignal(
            symbol="000001",
            signal_type=SignalType.BUY,
            strength=0.8,
            timestamp="2026-01-22T10:00:00",
            metadata={"source": "test"}
        )
        
        assert signal.symbol == "000001"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.8
        assert signal.metadata["source"] == "test"


class TestSoldierCore:
    """测试Soldier核心功能"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return SoldierConfig(
            local_inference_timeout=0.01,
            cloud_timeout=1.0,
            failure_threshold=2,
            decision_cache_ttl=1
        )
    
    @pytest.fixture
    def soldier_engine(self, config):
        """创建Soldier引擎实例"""
        engine = SoldierEngineV2(config)
        # Mock外部依赖
        engine.redis_client = AsyncMock()
        engine.event_bus = AsyncMock()
        engine.cache_enabled = False  # 禁用缓存以简化测试
        return engine
    
    @pytest.mark.asyncio
    async def test_initialization(self, soldier_engine):
        """测试初始化"""
        # Mock get_event_bus from the correct location
        with patch("src.infra.event_bus.get_event_bus", new_callable=AsyncMock) as mock_get_bus:
            mock_get_bus.return_value = AsyncMock()

            await soldier_engine.initialize()

            assert soldier_engine.state == "READY"
            assert soldier_engine.mode == SoldierMode.NORMAL
    
    @pytest.mark.asyncio
    async def test_decide_method(self, soldier_engine):
        """测试decide方法 - 核心决策接口"""
        context = {
            'symbol': 'AAPL',
            'market_data': {
                'price': 150.0,
                'volume': 1000000
            }
        }
        
        result = await soldier_engine.decide(context)
        
        # 验证返回结构
        assert 'decision' in result
        assert 'metadata' in result
        
        # 验证决策内容
        decision = result['decision']
        assert 'action' in decision
        assert 'confidence' in decision
        assert 'reasoning' in decision
        assert 'signal_strength' in decision
        assert 'risk_level' in decision
        assert 'execution_priority' in decision
        assert 'latency_ms' in decision
        assert 'source_mode' in decision
        
        # 验证元数据
        metadata = result['metadata']
        assert metadata['soldier_mode'] == SoldierMode.NORMAL.value
        assert 'timestamp' in metadata
        assert metadata['source'] == 'soldier_v2'
    
    @pytest.mark.asyncio
    async def test_get_status(self, soldier_engine):
        """测试get_status方法"""
        status = await soldier_engine.get_status()
        
        assert 'mode' in status
        assert 'state' in status
        assert 'failure_count' in status
        assert 'last_decision_time' in status
        assert 'stats' in status
        
        assert status['mode'] == SoldierMode.NORMAL.value
        assert status['state'] == "IDLE"
        assert status['failure_count'] == 0
    
    def test_get_state(self, soldier_engine):
        """测试get_state方法"""
        state = soldier_engine.get_state()
        
        assert state == "IDLE"
        
        # 修改状态后再测试
        soldier_engine.state = "READY"
        assert soldier_engine.get_state() == "READY"
    
    @pytest.mark.asyncio
    async def test_decide_with_error_handling(self, soldier_engine):
        """测试决策错误处理"""
        # 模拟决策过程中的错误
        with patch.object(soldier_engine, '_get_cached_decision', side_effect=Exception("Test error")):
            context = {'symbol': 'TEST'}
            
            result = await soldier_engine.decide(context)
            
            # 应该返回回退决策
            assert result['decision']['action'] == 'hold'
            assert result['decision']['confidence'] == 0.1
            assert result['metadata']['is_fallback'] is True
            assert soldier_engine.stats['error_count'] > 0
