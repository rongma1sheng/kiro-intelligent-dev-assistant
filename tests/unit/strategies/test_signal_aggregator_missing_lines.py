# -*- coding: utf-8 -*-
"""
Signal Aggregator 缺失行覆盖测试
目标：覆盖第270, 412, 436行，将覆盖率从96.24%提升到100%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.strategies.signal_aggregator import SignalAggregator, ConflictResolution, SignalDirection, SignalStrength, TradingSignal, AggregatedSignal


class TestSignalAggregatorMissingLines:
    """专门测试Signal Aggregator缺失行的测试套件"""
    
    def setup_method(self):
        """测试前置设置"""
        self.aggregator = SignalAggregator()
        
    def test_callback_execution_line_270(self):
        """测试第270行：信号回调执行"""
        # 设置回调函数
        callback_mock = Mock()
        self.aggregator.on_signal = callback_mock
        
        # 创建测试信号
        signal = TradingSignal(
            symbol="TEST",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.9,
            target_position=0.1,
            strategy_name="test_strategy"
        )
        
        # 添加信号并聚合
        self.aggregator.add_signal(signal)
        result = self.aggregator.aggregate("TEST")
        
        # 验证回调被调用（第270行）
        callback_mock.assert_called_once()
        assert callback_mock.call_args[0][0] == result
        
    def test_callback_exception_handling(self):
        """测试回调函数异常处理"""
        # 设置会抛出异常的回调函数
        def failing_callback(signal):
            raise Exception("Callback failed")
            
        self.aggregator.on_signal = failing_callback
        
        # 创建测试信号
        signal = TradingSignal(
            symbol="TEST",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.9,
            target_position=0.1,
            strategy_name="test_strategy"
        )
        
        # 添加信号并聚合，即使回调失败也应该正常返回结果
        self.aggregator.add_signal(signal)
        result = self.aggregator.aggregate("TEST")
        assert result is not None
        assert result.symbol == "TEST"
        
    def test_conservative_fallback_to_majority_line_412(self):
        """测试第412行：conservative策略回退到majority"""
        self.aggregator.resolution_strategy = ConflictResolution.CONSERVATIVE
        
        # 创建没有卖出信号的情况，触发回退到majority
        signals = [
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=0.6,
                target_position=0.1,
                strategy_name="strategy1"
            ),
            TradingSignal(
                symbol="TEST", 
                direction=SignalDirection.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                target_position=0.0,
                strategy_name="strategy2"
            )
        ]
        
        # 添加信号
        for signal in signals:
            self.aggregator.add_signal(signal)
            
        # 这应该触发第412行的回退逻辑（conservative策略没有卖出信号时回退到majority）
        result = self.aggregator.aggregate("TEST")
        assert result is not None
        assert result.symbol == "TEST"
        
    def test_aggressive_no_buy_signals_fallback_line_436(self):
        """测试第436行：aggressive策略没有买入信号时的回退"""
        self.aggregator.resolution_strategy = ConflictResolution.AGGRESSIVE
        
        # 创建只有卖出和持有信号的情况，没有买入信号
        signals = [
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.SELL,
                strength=SignalStrength.STRONG,
                confidence=0.9,
                target_position=-0.1,
                strategy_name="strategy1"
            ),
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.HOLD,
                strength=SignalStrength.MEDIUM,
                confidence=0.8,
                target_position=0.0,
                strategy_name="strategy2"
            )
        ]
        
        # 添加信号
        for signal in signals:
            self.aggregator.add_signal(signal)
        
        # 在aggressive模式下，如果没有买入信号，应该回退到majority
        # 这会触发第436行的逻辑
        result = self.aggregator.aggregate("TEST")
        assert result is not None
        # 由于没有买入信号，应该按majority逻辑处理
        assert result.direction in [SignalDirection.SELL, SignalDirection.HOLD]
        
    def test_aggressive_mixed_signals_buy_priority(self):
        """测试aggressive策略中买入信号优先"""
        self.aggregator.resolution_strategy = ConflictResolution.AGGRESSIVE
        
        # 创建混合信号，包含买入和卖出
        signals = [
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.BUY,
                strength=SignalStrength.STRONG,
                confidence=0.9,
                target_position=0.1,
                strategy_name="buy_strategy"
            ),
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=0.8,
                target_position=-0.05,
                strategy_name="sell_strategy"
            )
        ]
        
        # 添加信号
        for signal in signals:
            self.aggregator.add_signal(signal)
        
        # aggressive模式应该优先选择买入信号
        result = self.aggregator.aggregate("TEST")
        assert result is not None
        assert result.direction == SignalDirection.BUY
        assert "buy_strategy" in result.contributing_strategies
        
    def test_callback_with_none_result(self):
        """测试当聚合结果为None时不触发回调"""
        callback_mock = Mock()
        self.aggregator.on_signal = callback_mock
        
        # 聚合空信号列表
        result = self.aggregator.aggregate("TEST")
        
        # 结果为None时不应该调用回调
        callback_mock.assert_not_called()
        assert result is None
        
    def test_different_resolution_strategies_coverage(self):
        """测试不同解决策略的完整覆盖"""
        signal = TradingSignal(
            symbol="TEST",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.9,
            target_position=0.1,
            strategy_name="test_strategy"
        )
        
        # 测试所有解决策略
        strategies = [
            ConflictResolution.MAJORITY,
            ConflictResolution.AGGRESSIVE,
            ConflictResolution.CONSERVATIVE,
            ConflictResolution.PRIORITY,
            ConflictResolution.WEIGHTED
        ]
        
        for strategy in strategies:
            self.aggregator.resolution_strategy = strategy
            self.aggregator.clear_signals("TEST")  # 清除之前的信号
            self.aggregator.add_signal(signal)
            result = self.aggregator.aggregate("TEST")
            assert result is not None
            assert result.symbol == "TEST"
            
    def test_aggressive_edge_cases(self):
        """测试aggressive策略的边界情况"""
        self.aggregator.resolution_strategy = ConflictResolution.AGGRESSIVE
        
        # 测试只有HOLD信号的情况
        hold_signals = [
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.HOLD,
                strength=SignalStrength.MEDIUM,
                confidence=0.6,
                target_position=0.0,
                strategy_name="hold_strategy1"
            ),
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                target_position=0.0,
                strategy_name="hold_strategy2"
            )
        ]
        
        # 添加信号
        for signal in hold_signals:
            self.aggregator.add_signal(signal)
        
        # 应该回退到majority策略
        result = self.aggregator.aggregate("TEST")
        assert result is not None
        assert result.direction == SignalDirection.HOLD
        
    def test_callback_with_different_signal_types(self):
        """测试不同类型信号的回调"""
        callback_results = []
        
        def capture_callback(signal):
            callback_results.append(signal)
            
        self.aggregator.on_signal = capture_callback
        
        # 测试不同方向的信号
        signal_types = [
            (SignalDirection.BUY, 0.1),
            (SignalDirection.SELL, -0.1),
            (SignalDirection.HOLD, 0.0)
        ]
        
        for direction, position in signal_types:
            symbol = f"TEST_{direction.value}"
            signal = TradingSignal(
                symbol=symbol,
                direction=direction,
                strength=SignalStrength.STRONG,
                confidence=0.9,
                target_position=position,
                strategy_name=f"{direction.value}_strategy"
            )
            
            self.aggregator.add_signal(signal)
            result = self.aggregator.aggregate(symbol)
            assert result is not None
            
        # 验证所有回调都被执行
        assert len(callback_results) == 3
        
    def test_aggressive_no_valid_signals(self):
        """测试aggressive策略没有有效信号的情况"""
        self.aggregator.resolution_strategy = ConflictResolution.AGGRESSIVE
        self.aggregator.min_confidence = 0.5  # 设置最小置信度阈值
        
        # 创建低置信度信号（会被过滤掉）
        invalid_signals = [
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.BUY,
                strength=SignalStrength.WEAK,
                confidence=0.2,  # 低于最小置信度
                target_position=0.1,
                strategy_name="invalid_strategy"
            )
        ]
        
        # 添加信号
        for signal in invalid_signals:
            self.aggregator.add_signal(signal)
        
        # 应该返回None（没有有效信号）
        result = self.aggregator.aggregate("TEST")
        assert result is None
        
    def test_callback_exception_does_not_affect_result(self):
        """测试回调异常不影响聚合结果"""
        def exception_callback(signal):
            raise RuntimeError("Callback error")
            
        self.aggregator.on_signal = exception_callback
        
        signal = TradingSignal(
            symbol="TEST",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=0.9,
            target_position=0.1,
            strategy_name="test_strategy"
        )
        
        # 添加信号并聚合，即使回调抛出异常，聚合结果也应该正常返回
        self.aggregator.add_signal(signal)
        result = self.aggregator.aggregate("TEST")
        assert result is not None
        assert result.symbol == "TEST"
        assert result.direction == SignalDirection.BUY