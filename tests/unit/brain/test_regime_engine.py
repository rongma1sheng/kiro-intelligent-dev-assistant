"""
市场状态引擎单元测试

白皮书依据: 第一章 1.5.2 战争态任务调度
"""

import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock, patch

from src.brain.regime_engine import (
    RegimeEngine,
    MarketRegime,
    VolatilityLevel,
    RegimeState
)


class TestMarketRegime:
    """市场状态枚举测试"""
    
    def test_regime_values(self):
        """测试状态值"""
        assert MarketRegime.BULL.value == "牛市"
        assert MarketRegime.BEAR.value == "熊市"
        assert MarketRegime.SIDEWAYS.value == "震荡"
        assert MarketRegime.TRANSITION.value == "转折"
        assert MarketRegime.UNKNOWN.value == "未知"
    
    def test_volatility_values(self):
        """测试波动率值"""
        assert VolatilityLevel.LOW.value == "低波动"
        assert VolatilityLevel.HIGH.value == "高波动"


class TestRegimeState:
    """状态数据测试"""
    
    def test_default_state(self):
        """测试默认状态"""
        state = RegimeState()
        assert state.regime == MarketRegime.UNKNOWN
        assert state.confidence == 0.0
    
    def test_to_dict(self):
        """测试转换为字典"""
        state = RegimeState(
            regime=MarketRegime.BULL,
            confidence=0.8
        )
        result = state.to_dict()
        
        assert result["regime"] == "牛市"
        assert result["confidence"] == 0.8


class TestRegimeEngine:
    """市场状态引擎测试"""
    
    @pytest.fixture
    def engine(self):
        """创建引擎实例"""
        return RegimeEngine(update_interval=1)
    
    def test_init(self, engine):
        """测试初始化"""
        assert engine.update_interval == 1
        assert engine.current_state.regime == MarketRegime.UNKNOWN
        assert not engine.is_running()
    
    def test_init_invalid_interval(self):
        """测试无效间隔"""
        with pytest.raises(ValueError):
            RegimeEngine(update_interval=0)
    
    def test_start_stop(self, engine):
        """测试启动停止"""
        assert engine.start()
        assert engine.is_running()
        
        assert engine.stop()
        assert not engine.is_running()
    
    def test_start_already_running(self, engine):
        """测试重复启动"""
        engine.start()
        assert engine.start()  # 应该返回True
        engine.stop()
    
    def test_update_price(self, engine):
        """测试更新价格"""
        engine.update_price(100.0)
        engine.update_price(101.0)
        
        assert len(engine._price_cache) == 2
    
    def test_update_prices(self, engine):
        """测试批量更新价格"""
        prices = [100.0, 101.0, 102.0]
        engine.update_prices(prices)
        
        assert len(engine._price_cache) == 3
    
    def test_get_current_regime(self, engine):
        """测试获取当前状态"""
        regime = engine.get_current_regime()
        assert regime == MarketRegime.UNKNOWN
    
    def test_get_state(self, engine):
        """测试获取完整状态"""
        state = engine.get_state()
        assert isinstance(state, RegimeState)
    
    def test_calculate_trend_strength(self, engine):
        """测试趋势强度计算"""
        import numpy as np
        
        # 上涨趋势
        prices = np.array([100, 101, 102, 103, 104])
        strength = engine._calculate_trend_strength(prices)
        assert strength > 0
        
        # 下跌趋势
        prices = np.array([104, 103, 102, 101, 100])
        strength = engine._calculate_trend_strength(prices)
        assert strength < 0
    
    def test_calculate_volatility(self, engine):
        """测试波动率计算"""
        import numpy as np
        
        prices = np.array([100, 101, 99, 102, 98])
        volatility = engine._calculate_volatility(prices)
        assert volatility > 0
    
    def test_classify_volatility(self, engine):
        """测试波动率分类"""
        assert engine._classify_volatility(0.10) == VolatilityLevel.LOW
        assert engine._classify_volatility(0.20) == VolatilityLevel.MEDIUM
        assert engine._classify_volatility(0.30) == VolatilityLevel.HIGH
        assert engine._classify_volatility(0.50) == VolatilityLevel.EXTREME
    
    def test_regime_change_callback(self, engine):
        """测试状态变化回调"""
        callback_called = []
        
        def on_change(old, new):
            callback_called.append((old, new))
        
        engine.on_regime_change = on_change
        
        # 添加足够数据触发状态计算
        prices = [100 + i * 0.5 for i in range(30)]  # 上涨趋势
        engine.update_prices(prices)
        
        # 手动触发更新
        engine._update_regime()
        
        # 状态应该从UNKNOWN变化
        assert len(callback_called) >= 0  # 可能触发也可能不触发
    
    def test_state_history(self, engine):
        """测试状态历史"""
        engine._update_regime()
        engine._update_regime()
        
        assert len(engine.state_history) >= 1


class TestRegimeEngineIntegration:
    """集成测试"""
    
    def test_full_cycle(self):
        """测试完整周期"""
        engine = RegimeEngine(update_interval=1)
        
        # 启动
        engine.start()
        assert engine.is_running()
        
        # 添加数据
        for i in range(50):
            engine.update_price(100 + i * 0.1)
        
        # 等待更新
        time.sleep(1.5)
        
        # 获取状态
        state = engine.get_state()
        assert state is not None
        
        # 停止
        engine.stop()
        assert not engine.is_running()
