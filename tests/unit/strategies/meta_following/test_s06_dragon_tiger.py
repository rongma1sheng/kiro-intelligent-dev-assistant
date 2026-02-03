"""测试S06 Dragon Tiger (龙虎榜) 策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系
"""

import pytest
from datetime import datetime

from src.strategies.meta_following.s06_dragon_tiger import S06DragonTigerStrategy
from src.strategies.data_models import StrategyConfig, Signal


@pytest.fixture
def strategy_config():
    """创建测试用策略配置"""
    return StrategyConfig(
        strategy_name="S06_Dragon_Tiger",
        capital_tier="tier3_medium",
        max_position=0.6,
        max_single_stock=0.12,
        max_industry=0.25,
        stop_loss_pct=-0.08,
        take_profit_pct=0.15,
        trailing_stop_enabled=False,
        liquidity_threshold=1000000.0,
        max_order_pct_of_volume=0.05,
        trading_frequency="high",
        holding_period_days=3,
    )


@pytest.fixture
def dragon_tiger_strategy(strategy_config):
    """创建测试用龙虎榜策略实例"""
    return S06DragonTigerStrategy(config=strategy_config)


@pytest.fixture
def sample_dragon_tiger_data():
    """创建测试用龙虎榜数据"""
    return {
        "AAPL": {
            "buy_seats": [
                {"name": "华泰证券深圳益田路", "buy_amount": 15_000_000},
                {"name": "东方财富拉萨团结路", "buy_amount": 12_000_000},
                {"name": "普通席位A", "buy_amount": 8_000_000},
            ],
            "sell_seats": [
                {"name": "普通席位B", "sell_amount": 5_000_000},
            ],
            "total_buy": 35_000_000,
            "total_sell": 5_000_000,
            "reason": "日涨幅偏离值达7%",
        },
        "GOOGL": {
            "buy_seats": [
                {"name": "普通席位C", "buy_amount": 8_000_000},  # 低于最低买入金额
            ],
            "sell_seats": [],
            "total_buy": 8_000_000,
            "total_sell": 0,
            "reason": "日振幅达15%",
        },
        "MSFT": {
            "buy_seats": [
                {"name": "国泰君安上海江苏路", "buy_amount": 20_000_000},
                {"name": "中信证券上海溧阳路", "buy_amount": 18_000_000},
            ],
            "sell_seats": [
                {"name": "普通席位D", "sell_amount": 25_000_000},  # 净买入为负
            ],
            "total_buy": 38_000_000,
            "total_sell": 25_000_000,
            "reason": "日换手率达20%",
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


class TestS06DragonTigerInitialization:
    """测试S06龙虎榜策略初始化"""

    def test_initialization(self, dragon_tiger_strategy, strategy_config):
        """测试策略初始化"""
        assert dragon_tiger_strategy.name == "S06_Dragon_Tiger"
        assert dragon_tiger_strategy.config == strategy_config
        assert dragon_tiger_strategy.min_buy_amount == 10_000_000
        assert dragon_tiger_strategy.min_net_buy_ratio == 0.3
        assert dragon_tiger_strategy.famous_seat_weight == 1.5
        assert dragon_tiger_strategy.max_holding_days == 3

    def test_famous_seats_defined(self, dragon_tiger_strategy):
        """测试知名席位列表已定义"""
        assert len(dragon_tiger_strategy.FAMOUS_SEATS) > 0
        assert "华泰证券深圳益田路" in dragon_tiger_strategy.FAMOUS_SEATS
        assert "东方财富拉萨团结路" in dragon_tiger_strategy.FAMOUS_SEATS


class TestGenerateSignals:
    """测试信号生成"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(
        self, dragon_tiger_strategy, sample_dragon_tiger_data, sample_prices
    ):
        """测试使用有效数据生成信号"""
        market_data = {
            "dragon_tiger_data": sample_dragon_tiger_data,
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # AAPL符合条件（买入金额足够，净买入为正，有知名席位）
        # GOOGL不符合（买入金额不足）
        # MSFT不符合（净买入比例不足）
        assert len(signals) > 0
        assert all(s.action == "buy" for s in signals)
        assert all(s.confidence > 0 for s in signals)
        # 应该包含AAPL
        symbols = [s.symbol for s in signals]
        assert "AAPL" in symbols

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_buy_amount(self, dragon_tiger_strategy, sample_prices):
        """测试过滤买入金额不足的信号"""
        market_data = {
            "dragon_tiger_data": {
                "LOW": {
                    "buy_seats": [{"name": "普通席位", "buy_amount": 5_000_000}],  # 低于10M
                    "sell_seats": [],
                    "total_buy": 5_000_000,
                    "total_sell": 0,
                    "reason": "测试",
                }
            },
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 买入金额不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_negative_net_buy(self, dragon_tiger_strategy, sample_prices):
        """测试过滤净买入为负的信号"""
        market_data = {
            "dragon_tiger_data": {
                "NEG": {
                    "buy_seats": [{"name": "华泰证券深圳益田路", "buy_amount": 15_000_000}],
                    "sell_seats": [{"name": "普通席位", "sell_amount": 20_000_000}],  # 卖出更多
                    "total_buy": 15_000_000,
                    "total_sell": 20_000_000,
                    "reason": "测试",
                }
            },
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 净买入为负应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_net_buy_ratio(self, dragon_tiger_strategy, sample_prices):
        """测试过滤净买入比例不足的信号"""
        market_data = {
            "dragon_tiger_data": {
                "LOW_RATIO": {
                    "buy_seats": [{"name": "华泰证券深圳益田路", "buy_amount": 20_000_000}],
                    "sell_seats": [{"name": "普通席位", "sell_amount": 15_000_000}],
                    "total_buy": 20_000_000,
                    "total_sell": 15_000_000,  # 净买入比例25%，低于30%
                    "reason": "测试",
                }
            },
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 净买入比例不足应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self, dragon_tiger_strategy):
        """测试空数据"""
        market_data = {"dragon_tiger_data": {}, "prices": {}}

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_limits_to_top_5(self, dragon_tiger_strategy, sample_prices):
        """测试信号数量限制为5个"""
        # 创建10个符合条件的龙虎榜数据
        dt_data = {}
        for i in range(10):
            dt_data[f"STOCK{i}"] = {
                "buy_seats": [
                    {"name": "华泰证券深圳益田路", "buy_amount": 15_000_000 + i * 1_000_000},
                    {"name": "东方财富拉萨团结路", "buy_amount": 12_000_000},
                ],
                "sell_seats": [],
                "total_buy": 27_000_000 + i * 1_000_000,
                "total_sell": 5_000_000,
                "reason": f"测试{i}",
            }

        market_data = {"dragon_tiger_data": dt_data, "prices": sample_prices}

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 应该限制为5个
        assert len(signals) <= 5

    @pytest.mark.asyncio
    async def test_generate_signals_sorts_by_confidence(self, dragon_tiger_strategy, sample_prices):
        """测试信号按置信度排序"""
        dt_data = {
            "HIGH": {
                "buy_seats": [
                    {"name": "华泰证券深圳益田路", "buy_amount": 50_000_000},
                    {"name": "东方财富拉萨团结路", "buy_amount": 40_000_000},
                ],
                "sell_seats": [],
                "total_buy": 90_000_000,
                "total_sell": 10_000_000,
                "reason": "高置信度",
            },
            "LOW": {
                "buy_seats": [{"name": "普通席位", "buy_amount": 12_000_000}],
                "sell_seats": [],
                "total_buy": 12_000_000,
                "total_sell": 1_000_000,
                "reason": "低置信度",
            },
        }

        market_data = {"dragon_tiger_data": dt_data, "prices": sample_prices}

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 信号应该按置信度降序排列
        if len(signals) > 1:
            for i in range(len(signals) - 1):
                assert signals[i].confidence >= signals[i + 1].confidence


class TestIsFamousSeat:
    """测试知名席位判断"""

    def test_is_famous_seat_exact_match(self, dragon_tiger_strategy):
        """测试完全匹配的知名席位"""
        assert dragon_tiger_strategy._is_famous_seat("华泰证券深圳益田路")
        assert dragon_tiger_strategy._is_famous_seat("东方财富拉萨团结路")

    def test_is_famous_seat_partial_match(self, dragon_tiger_strategy):
        """测试部分匹配的知名席位"""
        assert dragon_tiger_strategy._is_famous_seat("华泰证券深圳益田路营业部")
        assert dragon_tiger_strategy._is_famous_seat("东方财富拉萨团结路第一营业部")

    def test_is_famous_seat_not_famous(self, dragon_tiger_strategy):
        """测试非知名席位"""
        assert not dragon_tiger_strategy._is_famous_seat("普通券商普通营业部")
        assert not dragon_tiger_strategy._is_famous_seat("未知席位")

    def test_is_famous_seat_empty_string(self, dragon_tiger_strategy):
        """测试空字符串"""
        assert not dragon_tiger_strategy._is_famous_seat("")


class TestCalculateDragonTigerConfidence:
    """测试置信度计算"""

    def test_calculate_confidence_with_famous_seats(self, dragon_tiger_strategy):
        """测试有知名席位的置信度"""
        confidence = dragon_tiger_strategy._calculate_dragon_tiger_confidence(
            total_buy_amount=50_000_000,
            net_buy_ratio=0.8,
            famous_buy_amount=40_000_000,
            famous_seat_count=2,
        )

        # 有知名席位应该有较高置信度
        assert 0.7 < confidence <= 0.90

    def test_calculate_confidence_without_famous_seats(self, dragon_tiger_strategy):
        """测试无知名席位的置信度"""
        confidence = dragon_tiger_strategy._calculate_dragon_tiger_confidence(
            total_buy_amount=15_000_000,
            net_buy_ratio=0.4,
            famous_buy_amount=0,
            famous_seat_count=0,
        )

        # 无知名席位置信度应该较低
        assert 0.5 <= confidence < 0.7

    def test_calculate_confidence_minimum_threshold(self, dragon_tiger_strategy):
        """测试最低置信度阈值"""
        confidence = dragon_tiger_strategy._calculate_dragon_tiger_confidence(
            total_buy_amount=10_000_000,  # 刚好达标
            net_buy_ratio=0.3,  # 刚好达标
            famous_buy_amount=0,
            famous_seat_count=0,
        )

        # 置信度应该不低于0.5
        assert confidence >= 0.5

    def test_calculate_confidence_maximum_cap(self, dragon_tiger_strategy):
        """测试最高置信度上限"""
        confidence = dragon_tiger_strategy._calculate_dragon_tiger_confidence(
            total_buy_amount=200_000_000,
            net_buy_ratio=1.0,
            famous_buy_amount=200_000_000,
            famous_seat_count=5,
        )

        # 置信度应该不超过0.90
        assert confidence <= 0.90

    def test_calculate_confidence_high_net_buy_ratio(self, dragon_tiger_strategy):
        """测试高净买入比例"""
        confidence = dragon_tiger_strategy._calculate_dragon_tiger_confidence(
            total_buy_amount=30_000_000,
            net_buy_ratio=0.9,  # 90%净买入
            famous_buy_amount=20_000_000,
            famous_seat_count=1,
        )

        # 高净买入比例应该提升置信度
        assert confidence > 0.6


class TestCalculatePositionSizes:
    """测试仓位计算"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self, dragon_tiger_strategy):
        """测试使用信号计算仓位"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
            Signal(symbol="MSFT", action="buy", confidence=0.70, timestamp="2026-01-30", reason="test"),
        ]

        positions = await dragon_tiger_strategy.calculate_position_sizes(signals)

        # 应该生成仓位
        assert len(positions) == 3
        assert all(p.size > 0 for p in positions)
        # 占位价格应该为100.0
        assert all(p.entry_price == 100.0 for p in positions)
        assert all(p.current_price == 100.0 for p in positions)

        # 总仓位不应超过30%（龙虎榜策略上限）
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.30

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_total(self, dragon_tiger_strategy):
        """测试总仓位上限"""
        # 创建多个高置信度信号
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test")
            for i in range(10)
        ]

        positions = await dragon_tiger_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过30%
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.30

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self, dragon_tiger_strategy):
        """测试空信号列表"""
        positions = await dragon_tiger_strategy.calculate_position_sizes([])

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self, dragon_tiger_strategy):
        """测试过滤卖出信号"""
        signals = [
            Signal(symbol="AAPL", action="sell", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
        ]

        positions = await dragon_tiger_strategy.calculate_position_sizes(signals)

        # 只应该有买入信号的仓位
        assert len(positions) == 1
        assert positions[0].symbol == "GOOGL"

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self, dragon_tiger_strategy):
        """测试置信度影响仓位大小"""
        signals = [
            Signal(symbol="HIGH", action="buy", confidence=0.90, timestamp="2026-01-30", reason="test"),
            Signal(symbol="LOW", action="buy", confidence=0.60, timestamp="2026-01-30", reason="test"),
        ]

        positions = await dragon_tiger_strategy.calculate_position_sizes(signals)

        # 高置信度应该有更大的仓位
        high_pos = next(p for p in positions if p.symbol == "HIGH")
        low_pos = next(p for p in positions if p.symbol == "LOW")
        assert high_pos.size > low_pos.size


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(self, dragon_tiger_strategy, sample_prices):
        """测试缺少键的数据"""
        market_data = {
            "dragon_tiger_data": {
                "INCOMPLETE": {
                    "buy_seats": [{"name": "华泰证券深圳益田路", "buy_amount": 15_000_000}],
                    # 缺少其他键
                }
            },
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 应该能处理缺失的键
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_buy_seats(self, dragon_tiger_strategy, sample_prices):
        """测试空买入席位列表"""
        market_data = {
            "dragon_tiger_data": {
                "EMPTY": {
                    "buy_seats": [],  # 空列表
                    "sell_seats": [],
                    "total_buy": 0,
                    "total_sell": 0,
                    "reason": "测试",
                }
            },
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 空买入席位应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_exception_handling(self, dragon_tiger_strategy, sample_prices):
        """测试异常处理"""
        market_data = {
            "dragon_tiger_data": {
                "ERROR": {
                    "buy_seats": [{"name": "华泰证券深圳益田路"}],  # 缺少buy_amount
                    "sell_seats": [],
                    "total_buy": None,  # 无效数据
                    "total_sell": None,
                    "reason": "测试",
                }
            },
            "prices": sample_prices,
        }

        signals = await dragon_tiger_strategy.generate_signals(market_data)

        # 异常应该被捕获，返回空列表
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_generate_signals_analyze_dragon_tiger_exception(self, dragon_tiger_strategy):
        """测试_analyze_dragon_tiger方法抛出异常时的处理"""
        from unittest.mock import patch
        
        market_data = {
            "dragon_tiger_data": {
                "TEST": {
                    "buy_seats": [{"name": "华泰证券深圳益田路", "buy_amount": 15_000_000}],
                    "sell_seats": [],
                    "total_buy": 15_000_000,
                    "total_sell": 0,
                    "reason": "测试",
                }
            },
            "prices": {},
        }

        # Mock _analyze_dragon_tiger 抛出异常
        with patch.object(
            dragon_tiger_strategy, 
            '_analyze_dragon_tiger', 
            side_effect=Exception("Test exception")
        ):
            signals = await dragon_tiger_strategy.generate_signals(market_data)
            
            # 异常被捕获，应该返回空列表
            assert signals == []

    def test_calculate_confidence_with_zero_total_buy(self, dragon_tiger_strategy):
        """测试总买入为零的情况"""
        confidence = dragon_tiger_strategy._calculate_dragon_tiger_confidence(
            total_buy_amount=0,
            net_buy_ratio=0.5,
            famous_buy_amount=0,
            famous_seat_count=0,
        )

        # 应该返回最低置信度
        assert confidence >= 0.5

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_stops_at_max_total(self, dragon_tiger_strategy):
        """测试达到总仓位上限时停止"""
        # 创建足够多的信号以超过30%上限
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test")
            for i in range(20)
        ]

        positions = await dragon_tiger_strategy.calculate_position_sizes(signals)

        # 总仓位应该接近但不超过30%
        total_position = sum(p.size for p in positions)
        assert 0.25 <= total_position <= 0.30
