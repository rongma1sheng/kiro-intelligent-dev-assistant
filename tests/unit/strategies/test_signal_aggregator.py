"""
信号聚合器单元测试

白皮书依据: 第一章 1.5.2 战争态任务调度
测试范围: SignalAggregator的信号收集、冲突解决和聚合功能
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.strategies.signal_aggregator import (
    SignalAggregator,
    TradingSignal,
    AggregatedSignal,
    SignalDirection,
    SignalStrength,
    ConflictResolution
)


class TestSignalDirection:
    """SignalDirection枚举测试"""
    
    def test_signal_direction_values(self):
        """测试信号方向枚举值"""
        assert SignalDirection.BUY.value == "买入"
        assert SignalDirection.SELL.value == "卖出"
        assert SignalDirection.HOLD.value == "持有"


class TestSignalStrength:
    """SignalStrength枚举测试"""
    
    def test_signal_strength_values(self):
        """测试信号强度枚举值"""
        assert SignalStrength.WEAK.value == "弱"
        assert SignalStrength.MEDIUM.value == "中"
        assert SignalStrength.STRONG.value == "强"


class TestConflictResolution:
    """ConflictResolution枚举测试"""
    
    def test_conflict_resolution_values(self):
        """测试冲突解决策略枚举值"""
        assert ConflictResolution.MAJORITY.value == "多数决"
        assert ConflictResolution.WEIGHTED.value == "加权"
        assert ConflictResolution.CONSERVATIVE.value == "保守"
        assert ConflictResolution.AGGRESSIVE.value == "激进"
        assert ConflictResolution.PRIORITY.value == "优先级"


class TestTradingSignal:
    """TradingSignal数据类测试"""
    
    def test_trading_signal_creation(self):
        """测试交易信号创建"""
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy_name="momentum",
            confidence=0.8,
            target_position=0.1,
            reason="动量突破"
        )
        
        assert signal.symbol == "000001.SZ"
        assert signal.direction == SignalDirection.BUY
        assert signal.strength == SignalStrength.STRONG
        assert signal.strategy_name == "momentum"
        assert signal.confidence == 0.8
        assert signal.target_position == 0.1
        assert signal.reason == "动量突破"
    
    def test_trading_signal_defaults(self):
        """测试交易信号默认值"""
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY
        )
        
        assert signal.strength == SignalStrength.MEDIUM
        assert signal.strategy_name == ""
        assert signal.confidence == 0.5
        assert signal.target_position == 0.0
    
    def test_trading_signal_to_dict(self):
        """测试交易信号转字典"""
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            confidence=0.8
        )
        
        result = signal.to_dict()
        
        assert result["symbol"] == "000001.SZ"
        assert result["direction"] == "买入"
        assert result["confidence"] == 0.8
        assert "timestamp" in result


class TestAggregatedSignal:
    """AggregatedSignal数据类测试"""
    
    def test_aggregated_signal_creation(self):
        """测试聚合信号创建"""
        signal = AggregatedSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.75,
            target_position=0.1,
            contributing_strategies=["momentum", "mean_reversion"],
            buy_count=3,
            sell_count=1,
            hold_count=1
        )
        
        assert signal.symbol == "000001.SZ"
        assert signal.direction == SignalDirection.BUY
        assert signal.confidence == 0.75
        assert len(signal.contributing_strategies) == 2
        assert signal.buy_count == 3
        assert signal.sell_count == 1
    
    def test_aggregated_signal_to_dict(self):
        """测试聚合信号转字典"""
        signal = AggregatedSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            buy_count=2,
            sell_count=1,
            hold_count=0
        )
        
        result = signal.to_dict()
        
        assert result["symbol"] == "000001.SZ"
        assert result["direction"] == "买入"
        assert result["buy_count"] == 2
        assert result["sell_count"] == 1


class TestSignalAggregator:
    """SignalAggregator聚合器测试"""
    
    @pytest.fixture
    def aggregator(self):
        """创建聚合器实例"""
        return SignalAggregator(
            resolution_strategy=ConflictResolution.WEIGHTED,
            min_confidence=0.3,
            signal_timeout=60.0
        )
    
    def test_init_default(self):
        """测试默认初始化"""
        aggregator = SignalAggregator()
        
        assert aggregator.resolution_strategy == ConflictResolution.WEIGHTED
        assert aggregator.min_confidence == 0.3
        assert aggregator.signal_timeout == 60.0
    
    def test_init_custom(self):
        """测试自定义初始化"""
        aggregator = SignalAggregator(
            resolution_strategy=ConflictResolution.MAJORITY,
            min_confidence=0.5,
            signal_timeout=30.0
        )
        
        assert aggregator.resolution_strategy == ConflictResolution.MAJORITY
        assert aggregator.min_confidence == 0.5
        assert aggregator.signal_timeout == 30.0
    
    def test_register_strategy(self, aggregator):
        """测试注册策略"""
        aggregator.register_strategy("momentum", weight=1.5, priority=8)
        
        assert "momentum" in aggregator.strategy_weights
        assert aggregator.strategy_weights["momentum"] == 1.5
        assert aggregator.strategy_priorities["momentum"] == 8
    
    def test_unregister_strategy(self, aggregator):
        """测试注销策略"""
        aggregator.register_strategy("momentum", weight=1.5)
        aggregator.unregister_strategy("momentum")
        
        assert "momentum" not in aggregator.strategy_weights
        assert "momentum" not in aggregator.strategy_priorities
    
    def test_get_registered_strategies(self, aggregator):
        """测试获取已注册策略"""
        aggregator.register_strategy("momentum")
        aggregator.register_strategy("mean_reversion")
        
        strategies = aggregator.get_registered_strategies()
        
        assert "momentum" in strategies
        assert "mean_reversion" in strategies
    
    def test_add_signal(self, aggregator):
        """测试添加信号"""
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            strategy_name="momentum",
            confidence=0.8
        )
        
        aggregator.add_signal(signal)
        
        assert aggregator.get_signal_count("000001.SZ") == 1
    
    def test_add_signals_batch(self, aggregator):
        """测试批量添加信号"""
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.6),
            TradingSignal(symbol="600000.SH", direction=SignalDirection.BUY, confidence=0.7)
        ]
        
        aggregator.add_signals(signals)
        
        assert aggregator.get_signal_count("000001.SZ") == 2
        assert aggregator.get_signal_count("600000.SH") == 1
    
    def test_aggregate_no_signals(self, aggregator):
        """测试无信号时聚合"""
        result = aggregator.aggregate("000001.SZ")
        
        assert result is None
    
    def test_aggregate_single_signal(self, aggregator):
        """测试单个信号聚合"""
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            strategy_name="momentum",
            confidence=0.8,
            target_position=0.1
        )
        
        aggregator.add_signal(signal)
        result = aggregator.aggregate("000001.SZ")
        
        assert result is not None
        assert result.direction == SignalDirection.BUY
        assert result.confidence == 1.0  # 单个信号100%一致
    
    def test_aggregate_majority_buy(self, aggregator):
        """测试多数决聚合 - 买入多数"""
        aggregator.resolution_strategy = ConflictResolution.MAJORITY
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.7),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.6)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        assert result.direction == SignalDirection.BUY
        assert result.buy_count == 2
        assert result.sell_count == 1
    
    def test_aggregate_majority_sell(self, aggregator):
        """测试多数决聚合 - 卖出多数"""
        aggregator.resolution_strategy = ConflictResolution.MAJORITY
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.7),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.6)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        assert result.direction == SignalDirection.SELL
    
    def test_aggregate_weighted(self, aggregator):
        """测试加权聚合"""
        aggregator.resolution_strategy = ConflictResolution.WEIGHTED
        aggregator.register_strategy("high_weight", weight=2.0)
        aggregator.register_strategy("low_weight", weight=0.5)
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, 
                         strategy_name="high_weight", confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, 
                         strategy_name="low_weight", confidence=0.8)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        # 高权重买入应该胜出
        assert result.direction == SignalDirection.BUY
    
    def test_aggregate_conservative(self, aggregator):
        """测试保守聚合 - 有卖出就卖出"""
        aggregator.resolution_strategy = ConflictResolution.CONSERVATIVE
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.9),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.5)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        # 保守策略：有卖出就卖出
        assert result.direction == SignalDirection.SELL
    
    def test_aggregate_aggressive(self, aggregator):
        """测试激进聚合 - 有买入就买入"""
        aggregator.resolution_strategy = ConflictResolution.AGGRESSIVE
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.9),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.5)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        # 激进策略：有买入就买入
        assert result.direction == SignalDirection.BUY
    
    def test_aggregate_priority(self, aggregator):
        """测试优先级聚合"""
        aggregator.resolution_strategy = ConflictResolution.PRIORITY
        aggregator.register_strategy("high_priority", priority=10)
        aggregator.register_strategy("low_priority", priority=1)
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, 
                         strategy_name="high_priority", confidence=0.5),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, 
                         strategy_name="low_priority", confidence=0.9)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        # 高优先级策略胜出
        assert result.direction == SignalDirection.SELL
    
    def test_aggregate_all(self, aggregator):
        """测试聚合所有标的"""
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="600000.SH", direction=SignalDirection.SELL, confidence=0.7),
            TradingSignal(symbol="000002.SZ", direction=SignalDirection.HOLD, confidence=0.6)
        ]
        
        aggregator.add_signals(signals)
        results = aggregator.aggregate_all()
        
        assert len(results) == 3
        assert "000001.SZ" in results
        assert "600000.SH" in results
        assert "000002.SZ" in results
    
    def test_filter_low_confidence(self, aggregator):
        """测试过滤低置信度信号"""
        aggregator.min_confidence = 0.5
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.2)  # 低于阈值
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        # 只有高置信度信号被考虑
        assert result.direction == SignalDirection.BUY
        assert result.buy_count == 1
    
    def test_clear_signals_single_symbol(self, aggregator):
        """测试清除单个标的信号"""
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="600000.SH", direction=SignalDirection.SELL, confidence=0.7)
        ]
        
        aggregator.add_signals(signals)
        aggregator.clear_signals("000001.SZ")
        
        assert aggregator.get_signal_count("000001.SZ") == 0
        assert aggregator.get_signal_count("600000.SH") == 1
    
    def test_clear_signals_all(self, aggregator):
        """测试清除所有信号"""
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="600000.SH", direction=SignalDirection.SELL, confidence=0.7)
        ]
        
        aggregator.add_signals(signals)
        aggregator.clear_signals()
        
        assert aggregator.get_signal_count() == 0
    
    def test_on_signal_callback(self, aggregator):
        """测试信号回调"""
        received_signals = []
        
        def on_signal(signal):
            received_signals.append(signal)
        
        aggregator.on_signal = on_signal
        
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            confidence=0.8
        )
        
        aggregator.add_signal(signal)
        aggregator.aggregate("000001.SZ")
        
        assert len(received_signals) == 1
        assert received_signals[0].symbol == "000001.SZ"
    
    def test_signal_strength_calculation(self, aggregator):
        """测试信号强度计算"""
        # 高置信度 -> 强信号
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.9),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.85)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        assert result.strength == SignalStrength.STRONG


class TestSignalAggregatorExpiredSignals:
    """过期信号测试"""
    
    def test_expired_signals_cleanup(self):
        """测试过期信号清理"""
        aggregator = SignalAggregator(signal_timeout=0.1)  # 100ms超时
        
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            confidence=0.8
        )
        
        aggregator.add_signal(signal)
        
        # 等待信号过期
        time.sleep(0.2)
        
        result = aggregator.aggregate("000001.SZ")
        
        # 信号已过期，应该返回None
        assert result is None


class TestSignalAggregatorThreadSafety:
    """线程安全测试"""
    
    @pytest.fixture
    def aggregator(self):
        """创建聚合器实例"""
        return SignalAggregator()
    
    def test_concurrent_add_signals(self, aggregator):
        """测试并发添加信号"""
        def add_signals(strategy_name):
            for i in range(10):
                signal = TradingSignal(
                    symbol="000001.SZ",
                    direction=SignalDirection.BUY,
                    strategy_name=strategy_name,
                    confidence=0.8
                )
                aggregator.add_signal(signal)
        
        threads = [
            threading.Thread(target=add_signals, args=(f"strategy_{i}",))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 应该有50个信号
        assert aggregator.get_signal_count("000001.SZ") == 50
    
    def test_concurrent_aggregate(self, aggregator):
        """测试并发聚合"""
        # 添加一些信号
        for i in range(10):
            signal = TradingSignal(
                symbol="000001.SZ",
                direction=SignalDirection.BUY,
                confidence=0.8
            )
            aggregator.add_signal(signal)
        
        results = []
        
        def aggregate():
            result = aggregator.aggregate("000001.SZ")
            if result:
                results.append(result)
        
        threads = [
            threading.Thread(target=aggregate)
            for _ in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有聚合应该成功
        assert len(results) == 5


class TestSignalAggregatorEdgeCases:
    """边界条件测试"""
    
    @pytest.fixture
    def aggregator(self):
        """创建聚合器实例"""
        return SignalAggregator()
    
    def test_all_signals_below_threshold(self, aggregator):
        """测试所有信号低于阈值"""
        aggregator.min_confidence = 0.9
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.5),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.6)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        assert result is None
    
    def test_equal_buy_sell_signals(self, aggregator):
        """测试买卖信号数量相等"""
        aggregator.resolution_strategy = ConflictResolution.MAJORITY
        
        signals = [
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.BUY, confidence=0.8),
            TradingSignal(symbol="000001.SZ", direction=SignalDirection.SELL, confidence=0.8)
        ]
        
        aggregator.add_signals(signals)
        result = aggregator.aggregate("000001.SZ")
        
        # 相等时应该返回HOLD
        assert result.direction == SignalDirection.HOLD
    
    def test_callback_exception_handling(self, aggregator):
        """测试回调异常处理"""
        def bad_callback(signal):
            raise ValueError("回调错误")
        
        aggregator.on_signal = bad_callback
        
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            confidence=0.8
        )
        
        aggregator.add_signal(signal)
        
        # 不应该抛出异常
        result = aggregator.aggregate("000001.SZ")
        assert result is not None
    
    def test_unregistered_strategy_weight(self, aggregator):
        """测试未注册策略的权重"""
        aggregator.resolution_strategy = ConflictResolution.WEIGHTED
        
        signal = TradingSignal(
            symbol="000001.SZ",
            direction=SignalDirection.BUY,
            strategy_name="unregistered",
            confidence=0.8
        )
        
        aggregator.add_signal(signal)
        result = aggregator.aggregate("000001.SZ")
        
        # 未注册策略使用默认权重1.0
        assert result is not None
