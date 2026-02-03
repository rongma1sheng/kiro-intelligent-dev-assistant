"""测试S15 Algo Hunter (主力雷达) 策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系
"""

import pytest
from datetime import datetime

from src.strategies.meta_following.s15_algo_hunter import S15AlgoHunterStrategy
from src.strategies.data_models import StrategyConfig, Signal


@pytest.fixture
def strategy_config():
    """创建测试用策略配置"""
    return StrategyConfig(
        strategy_name="S15_Algo_Hunter",
        capital_tier="tier3_medium",
        max_position=0.6,
        max_single_stock=0.12,
        max_industry=0.25,
        stop_loss_pct=-0.08,
        take_profit_pct=0.15,
        trailing_stop_enabled=False,
        liquidity_threshold=1000000.0,
        max_order_pct_of_volume=0.05,
        trading_frequency="medium",
        holding_period_days=5,
    )


@pytest.fixture
def algo_hunter_strategy(strategy_config):
    """创建测试用主力雷达策略实例"""
    return S15AlgoHunterStrategy(config=strategy_config)


@pytest.fixture
def sample_algo_signals():
    """创建测试用AlgoHunter信号"""
    return {
        "AAPL": {
            "main_force_probability": 0.85,
            "behavior_type": "accumulation",
            "iceberg_probability": 0.70,
            "accumulation_probability": 0.75,
            "signal_duration_minutes": 10,
        },
        "GOOGL": {
            "main_force_probability": 0.65,  # 低于阈值
            "behavior_type": "accumulation",
            "iceberg_probability": 0.60,
            "accumulation_probability": 0.65,
            "signal_duration_minutes": 8,
        },
        "MSFT": {
            "main_force_probability": 0.80,
            "behavior_type": "iceberg_buy",
            "iceberg_probability": 0.85,
            "accumulation_probability": 0.60,
            "signal_duration_minutes": 12,
        },
    }


@pytest.fixture
def sample_order_book():
    """创建测试用订单簿数据"""
    return {
        "AAPL": {"total_bid_volume": 150000, "total_ask_volume": 100000},
        "GOOGL": {"total_bid_volume": 120000, "total_ask_volume": 130000},
        "MSFT": {"total_bid_volume": 200000, "total_ask_volume": 150000},
    }


class TestS15AlgoHunterInitialization:
    """测试S15主力雷达策略初始化"""

    def test_initialization(self, algo_hunter_strategy, strategy_config):
        """测试策略初始化"""
        assert algo_hunter_strategy.name == "S15_Algo_Hunter"
        assert algo_hunter_strategy.config == strategy_config
        assert algo_hunter_strategy.main_force_threshold == 0.7
        assert algo_hunter_strategy.iceberg_detection_threshold == 0.6

        assert algo_hunter_strategy.accumulation_threshold == 0.65
        assert algo_hunter_strategy.min_signal_duration == 5


class TestGenerateSignals:
    """测试信号生成"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(
        self, algo_hunter_strategy, sample_algo_signals, sample_order_book
    ):
        """测试使用有效数据生成信号"""
        market_data = {
            "algo_hunter_signals": sample_algo_signals,
            "tick_data": {},
            "order_book": sample_order_book,
        }

        signals = await algo_hunter_strategy.generate_signals(market_data)

        # 应该生成信号（AAPL和MSFT符合条件，GOOGL不符合）
        assert len(signals) > 0
        assert all(s.action == "buy" for s in signals)
        assert all(s.confidence > 0 for s in signals)

    @pytest.mark.asyncio
    async def test_generate_signals_filters_low_probability(self, algo_hunter_strategy, sample_order_book):
        """测试过滤低概率信号"""
        market_data = {
            "algo_hunter_signals": {
                "LOW": {
                    "main_force_probability": 0.50,  # 低于阈值0.7
                    "behavior_type": "accumulation",
                    "iceberg_probability": 0.60,
                    "accumulation_probability": 0.65,
                    "signal_duration_minutes": 10,
                }
            },
            "tick_data": {},
            "order_book": sample_order_book,
        }

        signals = await algo_hunter_strategy.generate_signals(market_data)

        # 低概率信号应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_short_duration(self, algo_hunter_strategy, sample_order_book):
        """测试过滤持续时间过短的信号"""
        market_data = {
            "algo_hunter_signals": {
                "SHORT": {
                    "main_force_probability": 0.85,
                    "behavior_type": "accumulation",
                    "iceberg_probability": 0.70,
                    "accumulation_probability": 0.75,
                    "signal_duration_minutes": 3,  # 低于阈值5
                }
            },
            "tick_data": {},
            "order_book": sample_order_book,
        }

        signals = await algo_hunter_strategy.generate_signals(market_data)

        # 持续时间过短应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_filters_bearish_behavior(self, algo_hunter_strategy, sample_order_book):
        """测试过滤看跌行为"""
        market_data = {
            "algo_hunter_signals": {
                "BEAR": {
                    "main_force_probability": 0.85,
                    "behavior_type": "distribution",  # 出货行为
                    "iceberg_probability": 0.70,
                    "accumulation_probability": 0.75,
                    "signal_duration_minutes": 10,
                }
            },
            "tick_data": {},
            "order_book": sample_order_book,
        }

        signals = await algo_hunter_strategy.generate_signals(market_data)

        # 看跌行为应该被过滤
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self, algo_hunter_strategy):
        """测试空数据"""
        market_data = {"algo_hunter_signals": {}, "tick_data": {}, "order_book": {}}

        signals = await algo_hunter_strategy.generate_signals(market_data)

        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_limits_to_top_5(self, algo_hunter_strategy, sample_order_book):
        """测试信号数量限制为5个"""
        # 创建10个符合条件的信号
        algo_signals = {}
        for i in range(10):
            algo_signals[f"STOCK{i}"] = {
                "main_force_probability": 0.75 + i * 0.01,
                "behavior_type": "accumulation",
                "iceberg_probability": 0.70,
                "accumulation_probability": 0.75,
                "signal_duration_minutes": 10,
            }

        market_data = {"algo_hunter_signals": algo_signals, "tick_data": {}, "order_book": {}}

        signals = await algo_hunter_strategy.generate_signals(market_data)

        # 应该限制为5个
        assert len(signals) <= 5


class TestAnalyzeOrderBook:
    """测试订单簿分析"""

    def test_analyze_order_book_bullish(self, algo_hunter_strategy):
        """测试买盘强势的订单簿"""
        order_book = {"total_bid_volume": 200000, "total_ask_volume": 100000}

        strength = algo_hunter_strategy._analyze_order_book(order_book)

        # 买卖比2:1，强度应该为1.0
        assert strength == 1.0

    def test_analyze_order_book_bearish(self, algo_hunter_strategy):
        """测试卖盘强势的订单簿"""
        order_book = {"total_bid_volume": 100000, "total_ask_volume": 200000}

        strength = algo_hunter_strategy._analyze_order_book(order_book)

        # 买卖比1:2，强度应该较低
        assert 0 < strength < 0.5

    def test_analyze_order_book_balanced(self, algo_hunter_strategy):
        """测试买卖平衡的订单簿"""
        order_book = {"total_bid_volume": 100000, "total_ask_volume": 100000}

        strength = algo_hunter_strategy._analyze_order_book(order_book)

        # 买卖比1:1，强度应该为0.5
        assert strength == 0.5

    def test_analyze_order_book_zero_ask(self, algo_hunter_strategy):
        """测试卖盘为零的情况"""
        order_book = {"total_bid_volume": 100000, "total_ask_volume": 0}

        strength = algo_hunter_strategy._analyze_order_book(order_book)

        # ask为0时，bid_ask_ratio默认为1.0，strength = min(1.0, 1.0/2.0) = 0.5
        assert strength == 0.5


class TestCalculateAlgoConfidence:
    """测试置信度计算"""

    def test_calculate_confidence_accumulation(self, algo_hunter_strategy):
        """测试吸筹行为的置信度"""
        confidence = algo_hunter_strategy._calculate_algo_confidence(
            main_force_prob=0.85,
            behavior_type="accumulation",
            iceberg_prob=0.70,
            accumulation_prob=0.75,
            bid_strength=0.8,
        )

        # 吸筹行为应该有较高置信度
        assert 0.7 < confidence <= 0.90

    def test_calculate_confidence_iceberg_buy(self, algo_hunter_strategy):
        """测试冰山单买入的置信度"""
        confidence = algo_hunter_strategy._calculate_algo_confidence(
            main_force_prob=0.80,
            behavior_type="iceberg_buy",
            iceberg_prob=0.85,
            accumulation_prob=0.60,
            bid_strength=0.7,
        )

        # 冰山单买入应该有较高置信度
        assert 0.65 < confidence <= 0.90

    def test_calculate_confidence_minimum_threshold(self, algo_hunter_strategy):
        """测试最低置信度阈值"""
        confidence = algo_hunter_strategy._calculate_algo_confidence(
            main_force_prob=0.70,  # 刚好达标
            behavior_type="wash_out_end",
            iceberg_prob=0.50,
            accumulation_prob=0.50,
            bid_strength=0.3,
        )

        # 置信度应该不低于0.5
        assert confidence >= 0.5

    def test_calculate_confidence_maximum_cap(self, algo_hunter_strategy):
        """测试最高置信度上限"""
        confidence = algo_hunter_strategy._calculate_algo_confidence(
            main_force_prob=0.95,
            behavior_type="accumulation",
            iceberg_prob=0.90,
            accumulation_prob=0.90,
            bid_strength=1.0,
        )

        # 置信度应该不超过0.90
        assert confidence <= 0.90


class TestCalculatePositionSizes:
    """测试仓位计算"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self, algo_hunter_strategy):
        """测试使用信号计算仓位"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
            Signal(symbol="MSFT", action="buy", confidence=0.70, timestamp="2026-01-30", reason="test"),
        ]

        positions = await algo_hunter_strategy.calculate_position_sizes(signals)

        # 应该生成仓位
        assert len(positions) == 3
        assert all(p.size > 0 for p in positions)
        # 占位价格应该为100.0
        assert all(p.entry_price == 100.0 for p in positions)
        assert all(p.current_price == 100.0 for p in positions)

        # 总仓位不应超过40%
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.40

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_total(self, algo_hunter_strategy):
        """测试总仓位上限"""
        # 创建多个高置信度信号
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test")
            for i in range(10)
        ]

        positions = await algo_hunter_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过40%
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.40

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self, algo_hunter_strategy):
        """测试空信号列表"""
        positions = await algo_hunter_strategy.calculate_position_sizes([])

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self, algo_hunter_strategy):
        """测试过滤卖出信号"""
        signals = [
            Signal(symbol="AAPL", action="sell", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
        ]

        positions = await algo_hunter_strategy.calculate_position_sizes(signals)

        # 只应该有买入信号的仓位
        assert len(positions) == 1
        assert positions[0].symbol == "GOOGL"


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(self, algo_hunter_strategy):
        """测试缺少键的数据"""
        market_data = {
            "algo_hunter_signals": {
                "INCOMPLETE": {
                    "main_force_probability": 0.85,
                    # 缺少其他键
                }
            },
            "tick_data": {},
            "order_book": {},
        }

        signals = await algo_hunter_strategy.generate_signals(market_data)

        # 应该能处理缺失的键
        assert isinstance(signals, list)

    def test_analyze_order_book_with_missing_keys(self, algo_hunter_strategy):
        """测试缺少键的订单簿"""
        order_book = {}  # 空订单簿

        strength = algo_hunter_strategy._analyze_order_book(order_book)

        # 空订单簿时，bid=0, ask=1, ratio=0, strength=0
        assert strength == 0.0
