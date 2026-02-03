# -*- coding: utf-8 -*-
"""
Signal Aggregator 简化测试 - 专注覆盖缺失行
"""

import pytest
from unittest.mock import Mock
from src.strategies.signal_aggregator import SignalAggregator, ConflictResolution, SignalDirection, TradingSignal


class TestSignalAggregatorSimple:
    """简化的Signal Aggregator测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.aggregator = SignalAggregator()
        
    def test_callback_execution(self):
        """测试回调执行"""
        callback_mock = Mock()
        self.aggregator.on_signal = callback_mock
        
        signal = TradingSignal(
            symbol="TEST",
            direction=SignalDirection.BUY,
            confidence=0.9,
            target_position=0.1,
            strategy_name="test_strategy"
        )
        
        result = self.aggregator.aggregate("TEST", [signal])
        
        # 验证回调被调用
        callback_mock.assert_called_once()
        
    def test_aggressive_fallback(self):
        """测试aggressive策略回退"""
        self.aggregator.resolution_strategy = ConflictResolution.AGGRESSIVE
        
        # 创建HOLD信号，应该回退到majority
        signals = [
            TradingSignal(
                symbol="TEST",
                direction=SignalDirection.HOLD,
                confidence=0.6,
                target_position=0.0,
                strategy_name="strategy1"
            )
        ]
        
        result = self.aggregator.aggregate("TEST", signals)
        assert result is not None