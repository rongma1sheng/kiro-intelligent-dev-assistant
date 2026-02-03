"""测试S10 Northbound (北向) 策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系
"""

import pytest
from datetime import datetime

from src.strategies.meta_following.s10_northbound import S10NorthboundStrategy
from src.strategies.data_models import StrategyConfig, Signal


@pytest.fixture
def strategy_config():
    """创建测试用策略配置"""
    return StrategyConfig(
        strategy_name="S10_Northbound",
        capital_tier="tier3_medium",
        max_position=0.6,
        max_single_stock=0.12,
        max_industry=0.25,
        stop_loss_pct=-0.08,
        take_profit_pct=0.15,
        trailing_stop_enabled=False,
        liquidity_threshold=1000000.0,
        max_order_pct_of_volume=0.05,
        trading_frequency="low",
        holding_period_days=30,
    )


@pytest.fixture
def northbound_strategy(strategy_config):
    """创建测试用北向策略实例"""
    return S10NorthboundStrategy(config=strategy_config)


@pytest.fixture
def sample_northbound_data():
    """创建测试用北向资金数据"""
    return {
        "AAPL": {
            "holding_ratio": 0.05,  # 5%持股
            "holding_change_5d": 0.005,  # 5日增持0.5%
            "consecutive_inflow_days": 5,  # 连续流入5天
            "daily_inflow": 100_000_000,  # 日流入1亿
            "total_holding_value": 5_000_000_000,  # 总持仓50亿
        },
        "GOOGL": {
            "holding_ratio": 0.005,  # 0.5%持股，低于阈值
            "holding_change_5d": 0.002,
            "consecutive_inflow_days": 5,
            "daily_inflow": 80_000_000,
            "total_holding_value": 1_000_000_000,
        },
        "MSFT": {
            "holding_ratio": 0.03,
            "holding_change_5d": 0.003,
            "consecutive_inflow_days": 2,  # 连续流入天数不足
            "daily_inflow": 120_000_000,
            "total_holding_value": 3_000_000_000,
        },
    }


@pytest.fixture
def sample_prices():
    """创建测试用价格数据"""
    return {
        "AAPL": {"close": 150.0, "volume": 1000000},
        "GOOGL": {"close": 2800.0, "volume": 500000},
        "MSFT": {"close": 380.0, "volume": 800000},
    }


@pytest.fixture
def sample_fundamentals():
    """创建测试用基本面数据"""
    return {
        "AAPL": {"roe": 0.20, "pe_ratio": 25},
        "GOOGL": {"roe": 0.18, "pe_ratio": 28},
        "MSFT": {"roe": 0.15, "pe_ratio": 22},
    }


class TestS10NorthboundInitialization:
    """测试S10北向策略初始化"""

    def test_initialization(self, northbound_strategy, strategy_config):
        """测试策略初始化"""
        assert northbound_strategy.name == "S10_Northbound"
        assert northbound_strategy.config == strategy_config
        assert northbound_strategy.min_holding_ratio == 0.01
        assert northbound_strategy.min_inflow_days == 3
        assert northbound_strategy.min_daily_inflow == 50_000_000
        assert northbound_strategy.holding_change_threshold == 0.001


class TestGenerateSignals:
    """测试信号生成"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(
        self, northbound_strategy, sample_northbound_data, sample_prices, sample_fundamentals
    ):
        """测试使用有效数据生成信号"""
        market_data = {
            "northbound_data": sample_northbound_data,
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # AAPL符合条件，GOOGL持股比例不足，MSFT连续流入天数不足
        assert len(signals) > 0
        assert all(s.action == "buy" for s in signals)
        assert all(s.confidence > 0 for s in signals)
        # 应该包含AAPL
        symbols = [s.symbol for s in signals]
        assert "AAPL" in symbols

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_holding_ratio(self, northbound_strategy, sample_prices, sample_fundamentals):
        """测试过滤持股比例不足的信号"""
        market_data = {
            "northbound_data": {
                "LOW": {
                    "holding_ratio": 0.005,  # 0.5%，低于1%阈值
                    "holding_change_5d": 0.002,
                    "consecutive_inflow_days": 5,
                    "daily_inflow": 80_000_000,
                    "total_holding_value": 1_000_000_000,
                }
            },
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 持股比例不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_insufficient_inflow_days(
        self, northbound_strategy, sample_prices, sample_fundamentals
    ):
        """测试过滤连续流入天数不足的信号"""
        market_data = {
            "northbound_data": {
                "SHORT": {
                    "holding_ratio": 0.03,
                    "holding_change_5d": 0.003,
                    "consecutive_inflow_days": 2,  # 低于3天阈值
                    "daily_inflow": 120_000_000,
                    "total_holding_value": 3_000_000_000,
                }
            },
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 连续流入天数不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_daily_inflow(
        self, northbound_strategy, sample_prices, sample_fundamentals
    ):
        """测试过滤日流入金额不足的信号"""
        market_data = {
            "northbound_data": {
                "LOW_INFLOW": {
                    "holding_ratio": 0.03,
                    "holding_change_5d": 0.003,
                    "consecutive_inflow_days": 5,
                    "daily_inflow": 30_000_000,  # 低于5000万阈值
                    "total_holding_value": 3_000_000_000,
                }
            },
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 日流入金额不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_negative_holding_change(
        self, northbound_strategy, sample_prices, sample_fundamentals
    ):
        """测试过滤持仓变化为负的信号"""
        market_data = {
            "northbound_data": {
                "NEGATIVE": {
                    "holding_ratio": 0.03,
                    "holding_change_5d": -0.001,  # 负值
                    "consecutive_inflow_days": 5,
                    "daily_inflow": 100_000_000,
                    "total_holding_value": 3_000_000_000,
                }
            },
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 持仓变化为负应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self, northbound_strategy):
        """测试空数据"""
        market_data = {"northbound_data": {}, "prices": {}, "fundamentals": {}}

        signals = await northbound_strategy.generate_signals(market_data)

        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_limits_to_top_10(
        self, northbound_strategy, sample_prices, sample_fundamentals
    ):
        """测试信号数量限制为10个"""
        # 创建15个符合条件的北向数据
        nb_data = {}
        for i in range(15):
            nb_data[f"STOCK{i}"] = {
                "holding_ratio": 0.02 + i * 0.001,
                "holding_change_5d": 0.002 + i * 0.0001,
                "consecutive_inflow_days": 5,
                "daily_inflow": 80_000_000 + i * 10_000_000,
                "total_holding_value": 2_000_000_000,
            }

        market_data = {
            "northbound_data": nb_data,
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 应该限制为10个
        assert len(signals) <= 10

    @pytest.mark.asyncio
    async def test_generate_signals_sorts_by_confidence(
        self, northbound_strategy, sample_prices, sample_fundamentals
    ):
        """测试信号按置信度排序"""
        nb_data = {
            "HIGH": {
                "holding_ratio": 0.08,
                "holding_change_5d": 0.01,
                "consecutive_inflow_days": 10,
                "daily_inflow": 500_000_000,
                "total_holding_value": 10_000_000_000,
            },
            "LOW": {
                "holding_ratio": 0.015,
                "holding_change_5d": 0.002,
                "consecutive_inflow_days": 3,
                "daily_inflow": 60_000_000,
                "total_holding_value": 1_500_000_000,
            },
        }

        market_data = {
            "northbound_data": nb_data,
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 信号应该按置信度降序排列
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                assert signals[i].confidence >= signals[i + 1].confidence


class TestCalculateNorthboundConfidence:
    """测试置信度计算"""

    def test_calculate_confidence_high_quality(self, northbound_strategy):
        """测试高质量标的的置信度"""
        confidence = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.08,
            holding_change=0.01,
            consecutive_inflow_days=10,
            daily_inflow=500_000_000,
            fundamental_data={"roe": 0.20, "pe_ratio": 25},
        )

        # 高质量标的应该有较高置信度
        assert 0.75 < confidence <= 0.90

    def test_calculate_confidence_medium_quality(self, northbound_strategy):
        """测试中等质量标的的置信度"""
        confidence = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.02,
            holding_change=0.003,
            consecutive_inflow_days=5,
            daily_inflow=100_000_000,
            fundamental_data={"roe": 0.12, "pe_ratio": 35},
        )

        # 中等质量标的应该有较高置信度（因为基础分数+0.4的偏移）
        assert 0.75 < confidence <= 0.90

    def test_calculate_confidence_minimum_threshold(self, northbound_strategy):
        """测试最低置信度阈值"""
        confidence = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.01,  # 刚好达标
            holding_change=0.001,  # 刚好达标
            consecutive_inflow_days=3,  # 刚好达标
            daily_inflow=50_000_000,  # 刚好达标
            fundamental_data={"roe": 0.05, "pe_ratio": 60},
        )

        # 置信度应该不低于0.5
        assert confidence >= 0.5

    def test_calculate_confidence_maximum_cap(self, northbound_strategy):
        """测试最高置信度上限"""
        confidence = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.15,
            holding_change=0.02,
            consecutive_inflow_days=20,
            daily_inflow=1_000_000_000,
            fundamental_data={"roe": 0.30, "pe_ratio": 20},
        )

        # 置信度应该不超过0.90
        assert confidence <= 0.90

    def test_calculate_confidence_with_good_fundamentals(self, northbound_strategy):
        """测试良好基本面的影响"""
        confidence_good = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.03,
            holding_change=0.003,
            consecutive_inflow_days=5,
            daily_inflow=100_000_000,
            fundamental_data={"roe": 0.20, "pe_ratio": 25},  # 优秀基本面
        )

        confidence_bad = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.03,
            holding_change=0.003,
            consecutive_inflow_days=5,
            daily_inflow=100_000_000,
            fundamental_data={"roe": 0.05, "pe_ratio": 60},  # 较差基本面
        )

        # 良好基本面应该提升置信度
        assert confidence_good > confidence_bad


class TestCalculatePositionSizes:
    """测试仓位计算"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self, northbound_strategy):
        """测试使用信号计算仓位"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
            Signal(symbol="MSFT", action="buy", confidence=0.70, timestamp="2026-01-30", reason="test"),
        ]

        positions = await northbound_strategy.calculate_position_sizes(signals)

        # 应该生成仓位
        assert len(positions) == 3
        assert all(p.size > 0 for p in positions)
        # 占位价格应该为100.0
        assert all(p.entry_price == 100.0 for p in positions)
        assert all(p.current_price == 100.0 for p in positions)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_total(self, northbound_strategy):
        """测试总仓位上限"""
        # 创建多个高置信度信号
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test")
            for i in range(10)
        ]

        positions = await northbound_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过max_position
        total_position = sum(p.size for p in positions)
        assert total_position <= northbound_strategy.max_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self, northbound_strategy):
        """测试空信号列表"""
        positions = await northbound_strategy.calculate_position_sizes([])

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self, northbound_strategy):
        """测试过滤卖出信号"""
        signals = [
            Signal(symbol="AAPL", action="sell", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
        ]

        positions = await northbound_strategy.calculate_position_sizes(signals)

        # 只应该有买入信号的仓位
        assert len(positions) == 1
        assert positions[0].symbol == "GOOGL"

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self, northbound_strategy):
        """测试置信度影响仓位大小"""
        signals = [
            Signal(symbol="HIGH", action="buy", confidence=0.90, timestamp="2026-01-30", reason="test"),
            Signal(symbol="LOW", action="buy", confidence=0.60, timestamp="2026-01-30", reason="test"),
        ]

        positions = await northbound_strategy.calculate_position_sizes(signals)

        # 高置信度应该有更大的仓位
        high_pos = next(p for p in positions if p.symbol == "HIGH")
        low_pos = next(p for p in positions if p.symbol == "LOW")
        assert high_pos.size > low_pos.size


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(
        self, northbound_strategy, sample_prices, sample_fundamentals
    ):
        """测试缺少键的数据"""
        market_data = {
            "northbound_data": {
                "INCOMPLETE": {
                    "holding_ratio": 0.03,
                    # 缺少其他键
                }
            },
            "prices": sample_prices,
            "fundamentals": sample_fundamentals,
        }

        signals = await northbound_strategy.generate_signals(market_data)

        # 应该能处理缺失的键
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_generate_signals_analyze_northbound_exception(self, northbound_strategy):
        """测试_analyze_northbound方法抛出异常时的处理"""
        from unittest.mock import patch

        market_data = {
            "northbound_data": {
                "TEST": {
                    "holding_ratio": 0.03,
                    "holding_change_5d": 0.003,
                    "consecutive_inflow_days": 5,
                    "daily_inflow": 100_000_000,
                    "total_holding_value": 3_000_000_000,
                }
            },
            "prices": {},
            "fundamentals": {},
        }

        # Mock _analyze_northbound 抛出异常
        with patch.object(
            northbound_strategy, "_analyze_northbound", side_effect=Exception("Test exception")
        ):
            signals = await northbound_strategy.generate_signals(market_data)

            # 异常被捕获，应该返回空列表
            assert signals == []

    def test_calculate_confidence_with_zero_values(self, northbound_strategy):
        """测试零值情况"""
        confidence = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.0,
            holding_change=0.0,
            consecutive_inflow_days=0,
            daily_inflow=0,
            fundamental_data={},
        )

        # 应该返回最低置信度
        assert confidence >= 0.5

    def test_calculate_confidence_with_missing_fundamental_keys(self, northbound_strategy):
        """测试缺少基本面键的情况"""
        confidence = northbound_strategy._calculate_northbound_confidence(
            holding_ratio=0.03,
            holding_change=0.003,
            consecutive_inflow_days=5,
            daily_inflow=100_000_000,
            fundamental_data={},  # 空字典
        )

        # 应该能处理缺失的键
        assert 0.5 <= confidence <= 0.90

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_stops_at_max_total(self, northbound_strategy):
        """测试达到总仓位上限时停止"""
        # 创建足够多的信号以超过max_position
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test")
            for i in range(20)
        ]

        positions = await northbound_strategy.calculate_position_sizes(signals)

        # 总仓位应该接近但不超过max_position
        total_position = sum(p.size for p in positions)
        assert total_position <= northbound_strategy.max_position
        assert total_position >= northbound_strategy.max_position * 0.9  # 至少达到90%
