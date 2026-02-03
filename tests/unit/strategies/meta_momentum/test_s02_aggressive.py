"""测试S02 Aggressive (激进) 策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系
"""

import pytest
from datetime import datetime

from src.strategies.meta_momentum.s02_aggressive import S02AggressiveStrategy
from src.strategies.data_models import StrategyConfig, Signal


@pytest.fixture
def strategy_config():
    """创建测试用策略配置"""
    return StrategyConfig(
        strategy_name="S02_Aggressive",
        capital_tier="tier3_medium",
        max_position=0.6,
        max_single_stock=0.15,
        max_industry=0.30,
        stop_loss_pct=-0.10,
        take_profit_pct=0.20,
        trailing_stop_enabled=True,
        liquidity_threshold=2000000.0,
        max_order_pct_of_volume=0.10,
        trading_frequency="high",
        holding_period_days=7,
    )


@pytest.fixture
def aggressive_strategy(strategy_config):
    """创建测试用激进策略实例"""
    return S02AggressiveStrategy(config=strategy_config)


@pytest.fixture
def sample_market_data():
    """创建测试用市场数据"""
    return {
        "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
        "prices": {
            "AAPL": {"close": 155.0, "high_20d": 150.0},  # 突破
            "GOOGL": {"close": 2800.0, "high_20d": 2850.0},  # 未突破
            "MSFT": {"close": 385.0, "high_20d": 380.0},  # 突破
            "TSLA": {"close": 0, "high_20d": 250.0},  # 无效数据
        },
        "volumes": {
            "AAPL": {"volume": 3000000, "avg_volume_20d": 1500000},  # 2倍放大
            "GOOGL": {"volume": 800000, "avg_volume_20d": 1000000},  # 缩量
            "MSFT": {"volume": 2400000, "avg_volume_20d": 1500000},  # 1.6倍
            "TSLA": {"volume": 5000000, "avg_volume_20d": 3000000},
        },
        "indicators": {
            "AAPL": {"rsi_14": 65.0, "macd_hist": 0.5},  # 强势
            "GOOGL": {"rsi_14": 45.0, "macd_hist": -0.2},  # 弱势
            "MSFT": {"rsi_14": 58.0, "macd_hist": 0.3},  # 中等
            "TSLA": {"rsi_14": 70.0, "macd_hist": 0.8},
        },
    }


class TestS02AggressiveInitialization:
    """测试S02激进策略初始化"""

    def test_initialization(self, aggressive_strategy, strategy_config):
        """测试策略初始化"""
        assert aggressive_strategy.name == "S02_Aggressive"
        assert aggressive_strategy.config == strategy_config
        assert aggressive_strategy.breakout_period == 20
        assert aggressive_strategy.volume_multiplier == 1.5
        assert aggressive_strategy.rsi_threshold == 50.0
        assert aggressive_strategy.momentum_window == 10


class TestGenerateSignals:
    """测试信号生成"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(self, aggressive_strategy, sample_market_data):
        """测试使用有效数据生成信号"""
        signals = await aggressive_strategy.generate_signals(sample_market_data)

        # AAPL和MSFT符合条件，GOOGL不符合，TSLA数据无效
        assert len(signals) > 0
        assert all(s.action == "buy" for s in signals)
        assert all(s.confidence > 0 for s in signals)

    @pytest.mark.asyncio
    async def test_generate_signals_filters_no_breakout(self, aggressive_strategy):
        """测试过滤未突破的信号"""
        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 100.0, "high_20d": 105.0}},  # 未突破
            "volumes": {"TEST": {"volume": 3000000, "avg_volume_20d": 1500000}},
            "indicators": {"TEST": {"rsi_14": 65.0, "macd_hist": 0.5}},
        }

        signals = await aggressive_strategy.generate_signals(market_data)

        # 未突破应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_volume(self, aggressive_strategy):
        """测试过滤成交量不足的信号"""
        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 105.0, "high_20d": 100.0}},  # 突破
            "volumes": {"TEST": {"volume": 1000000, "avg_volume_20d": 1500000}},  # 缩量
            "indicators": {"TEST": {"rsi_14": 65.0, "macd_hist": 0.5}},
        }

        signals = await aggressive_strategy.generate_signals(market_data)

        # 成交量不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_rsi(self, aggressive_strategy):
        """测试过滤RSI不足的信号"""
        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 105.0, "high_20d": 100.0}},
            "volumes": {"TEST": {"volume": 3000000, "avg_volume_20d": 1500000}},
            "indicators": {"TEST": {"rsi_14": 45.0, "macd_hist": 0.5}},  # RSI < 50
        }

        signals = await aggressive_strategy.generate_signals(market_data)

        # RSI不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_negative_macd(self, aggressive_strategy):
        """测试过滤MACD为负的信号"""
        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 105.0, "high_20d": 100.0}},
            "volumes": {"TEST": {"volume": 3000000, "avg_volume_20d": 1500000}},
            "indicators": {"TEST": {"rsi_14": 65.0, "macd_hist": -0.2}},  # MACD < 0
        }

        signals = await aggressive_strategy.generate_signals(market_data)

        # MACD为负应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self, aggressive_strategy):
        """测试空数据"""
        market_data = {"symbols": [], "prices": {}, "volumes": {}, "indicators": {}}

        signals = await aggressive_strategy.generate_signals(market_data)

        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_invalid_price(self, aggressive_strategy):
        """测试无效价格数据"""
        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 0, "high_20d": 100.0}},  # 价格为0
            "volumes": {"TEST": {"volume": 3000000, "avg_volume_20d": 1500000}},
            "indicators": {"TEST": {"rsi_14": 65.0, "macd_hist": 0.5}},
        }

        signals = await aggressive_strategy.generate_signals(market_data)

        # 无效价格应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_exception_handling(self, aggressive_strategy):
        """测试异常处理"""
        from unittest.mock import patch

        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 105.0, "high_20d": 100.0}},
            "volumes": {"TEST": {"volume": 3000000, "avg_volume_20d": 1500000}},
            "indicators": {"TEST": {"rsi_14": 65.0, "macd_hist": 0.5}},
        }

        # Mock _analyze_symbol 抛出异常
        with patch.object(aggressive_strategy, "_analyze_symbol", side_effect=Exception("Test exception")):
            signals = await aggressive_strategy.generate_signals(market_data)

            # 异常被捕获，应该返回空列表
            assert signals == []


class TestCalculateConfidence:
    """测试置信度计算"""

    def test_calculate_confidence_strong_signal(self, aggressive_strategy):
        """测试强信号的置信度"""
        confidence = aggressive_strategy._calculate_confidence(
            current_price=110.0,
            high_20d=100.0,  # 10%突破
            current_volume=4000000,
            avg_volume=1500000,  # 2.67倍
            rsi=70.0,
            macd_hist=0.8,
        )

        # 强信号应该有较高置信度
        assert 0.80 < confidence <= 0.95

    def test_calculate_confidence_medium_signal(self, aggressive_strategy):
        """测试中等信号的置信度"""
        confidence = aggressive_strategy._calculate_confidence(
            current_price=103.0,
            high_20d=100.0,  # 3%突破
            current_volume=2400000,
            avg_volume=1500000,  # 1.6倍
            rsi=58.0,
            macd_hist=0.3,
        )

        # 中等信号应该有较高置信度（因为基础置信度+0.5的偏移）
        assert 0.80 < confidence <= 0.95

    def test_calculate_confidence_minimum_threshold(self, aggressive_strategy):
        """测试最低置信度阈值"""
        confidence = aggressive_strategy._calculate_confidence(
            current_price=100.1,
            high_20d=100.0,  # 0.1%突破
            current_volume=1600000,
            avg_volume=1500000,  # 1.07倍
            rsi=51.0,
            macd_hist=0.01,
        )

        # 置信度应该不低于0.5
        assert confidence >= 0.5

    def test_calculate_confidence_maximum_cap(self, aggressive_strategy):
        """测试最高置信度上限"""
        confidence = aggressive_strategy._calculate_confidence(
            current_price=150.0,
            high_20d=100.0,  # 50%突破
            current_volume=10000000,
            avg_volume=1000000,  # 10倍
            rsi=90.0,
            macd_hist=2.0,
        )

        # 置信度应该不超过0.95
        assert confidence <= 0.95


class TestCalculatePositionSizes:
    """测试仓位计算"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self, aggressive_strategy):
        """测试使用信号计算仓位"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
            Signal(symbol="MSFT", action="buy", confidence=0.70, timestamp="2026-01-30", reason="test"),
        ]

        positions = await aggressive_strategy.calculate_position_sizes(signals)

        # 应该生成仓位
        assert len(positions) == 3
        assert all(p.size > 0 for p in positions)
        # 占位价格应该为100.0
        assert all(p.entry_price == 100.0 for p in positions)
        assert all(p.current_price == 100.0 for p in positions)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_total(self, aggressive_strategy):
        """测试总仓位上限"""
        # 创建多个高置信度信号
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.90, timestamp="2026-01-30", reason="test")
            for i in range(10)
        ]

        positions = await aggressive_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过max_position
        total_position = sum(p.size for p in positions)
        assert total_position <= aggressive_strategy.max_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self, aggressive_strategy):
        """测试空信号列表"""
        positions = await aggressive_strategy.calculate_position_sizes([])

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self, aggressive_strategy):
        """测试过滤卖出信号"""
        signals = [
            Signal(symbol="AAPL", action="sell", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
        ]

        positions = await aggressive_strategy.calculate_position_sizes(signals)

        # 只应该有买入信号的仓位
        assert len(positions) == 1
        assert positions[0].symbol == "GOOGL"

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self, aggressive_strategy):
        """测试置信度影响仓位大小"""
        signals = [
            Signal(symbol="HIGH", action="buy", confidence=0.95, timestamp="2026-01-30", reason="test"),
            Signal(symbol="LOW", action="buy", confidence=0.60, timestamp="2026-01-30", reason="test"),
        ]

        positions = await aggressive_strategy.calculate_position_sizes(signals)

        # 高置信度应该有更大的仓位
        high_pos = next(p for p in positions if p.symbol == "HIGH")
        low_pos = next(p for p in positions if p.symbol == "LOW")
        assert high_pos.size > low_pos.size

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_stops_at_zero(self, aggressive_strategy):
        """测试达到上限时停止"""
        # 创建足够多的信号以超过max_position
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.90, timestamp="2026-01-30", reason="test")
            for i in range(20)
        ]

        positions = await aggressive_strategy.calculate_position_sizes(signals)

        # 总仓位应该接近max_position
        total_position = sum(p.size for p in positions)
        assert total_position <= aggressive_strategy.max_position
        assert total_position >= aggressive_strategy.max_position * 0.95


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(self, aggressive_strategy):
        """测试缺少键的数据"""
        market_data = {
            "symbols": ["TEST"],
            "prices": {"TEST": {"close": 105.0}},  # 缺少high_20d
            "volumes": {"TEST": {"volume": 3000000}},  # 缺少avg_volume_20d
            "indicators": {"TEST": {}},  # 空字典
        }

        signals = await aggressive_strategy.generate_signals(market_data)

        # 应该能处理缺失的键
        assert isinstance(signals, list)

    def test_calculate_confidence_with_zero_avg_volume(self, aggressive_strategy):
        """测试平均成交量为零的情况"""
        # 这种情况在实际代码中会导致除零，但get默认值为1
        confidence = aggressive_strategy._calculate_confidence(
            current_price=105.0,
            high_20d=100.0,
            current_volume=3000000,
            avg_volume=1,  # 默认值
            rsi=65.0,
            macd_hist=0.5,
        )

        # 应该能正常计算
        assert 0.5 <= confidence <= 0.95

    def test_calculate_confidence_with_extreme_values(self, aggressive_strategy):
        """测试极端值情况"""
        confidence = aggressive_strategy._calculate_confidence(
            current_price=1000.0,
            high_20d=100.0,  # 900%突破
            current_volume=100000000,
            avg_volume=1000000,  # 100倍
            rsi=100.0,
            macd_hist=10.0,
        )

        # 置信度应该被限制在0.95
        assert confidence <= 0.95
