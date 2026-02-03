"""测试S07 Morning Sniper (首板) 策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系
"""

import pytest
from datetime import datetime, time

from src.strategies.meta_momentum.s07_morning_sniper import S07MorningSniperStrategy
from src.strategies.data_models import StrategyConfig, Signal


@pytest.fixture
def strategy_config():
    """创建测试用策略配置"""
    return StrategyConfig(
        strategy_name="S07_Morning_Sniper",
        capital_tier="tier3_medium",
        max_position=0.6,
        max_single_stock=0.15,
        max_industry=0.30,
        stop_loss_pct=-0.05,
        take_profit_pct=0.10,
        trailing_stop_enabled=True,
        liquidity_threshold=5000000.0,
        max_order_pct_of_volume=0.05,
        trading_frequency="high",
        holding_period_days=1,
    )


@pytest.fixture
def morning_sniper_strategy(strategy_config):
    """创建测试用首板策略实例"""
    return S07MorningSniperStrategy(config=strategy_config)


@pytest.fixture
def sample_auction_data():
    """创建测试用竞价数据"""
    return {
        "current_time": datetime(2026, 1, 30, 9, 20, 0),  # 集合竞价时间
        "auction_data": {
            "STOCK1": {
                "volume_ratio": 5.0,  # 5倍量比
                "bid_price_change": 0.06,  # 6%涨幅
                "bid_volume": 1000000,
                "prev_close": 100.0,
                "themes": ["AI", "芯片"],
            },
            "STOCK2": {
                "volume_ratio": 2.0,  # 量比不足
                "bid_price_change": 0.07,
                "bid_volume": 500000,
                "prev_close": 50.0,
                "themes": ["新能源"],
            },
            "STOCK3": {
                "volume_ratio": 4.0,
                "bid_price_change": 0.08,  # 8%涨幅
                "bid_volume": 800000,
                "prev_close": 80.0,
                "themes": ["AI"],
            },
        },
        "sentiment_scores": {
            "STOCK1": 0.85,  # 高舆情
            "STOCK2": 0.60,
            "STOCK3": 0.75,
        },
        "hot_themes": ["AI", "芯片", "半导体"],
    }


class TestS07MorningSniperInitialization:
    """测试S07首板策略初始化"""

    def test_initialization(self, morning_sniper_strategy, strategy_config):
        """测试策略初始化"""
        assert morning_sniper_strategy.name == "S07_Morning_Sniper"
        assert morning_sniper_strategy.config == strategy_config
        assert morning_sniper_strategy.volume_ratio_threshold == 3.0
        assert morning_sniper_strategy.sentiment_threshold == 0.7
        assert morning_sniper_strategy.bid_price_threshold == 0.05
        assert morning_sniper_strategy.max_bid_price == 0.095
        assert morning_sniper_strategy.auction_start == time(9, 15)
        assert morning_sniper_strategy.auction_end == time(9, 25)
        assert morning_sniper_strategy.order_deadline == time(9, 24, 30)


class TestIsAuctionTime:
    """测试集合竞价时间判断"""

    def test_is_auction_time_within_window(self, morning_sniper_strategy):
        """测试在竞价时间窗口内"""
        test_time = datetime(2026, 1, 30, 9, 20, 0)
        assert morning_sniper_strategy._is_auction_time(test_time) is True

    def test_is_auction_time_at_start(self, morning_sniper_strategy):
        """测试在竞价开始时间"""
        test_time = datetime(2026, 1, 30, 9, 15, 0)
        assert morning_sniper_strategy._is_auction_time(test_time) is True

    def test_is_auction_time_at_end(self, morning_sniper_strategy):
        """测试在竞价结束时间"""
        test_time = datetime(2026, 1, 30, 9, 25, 0)
        assert morning_sniper_strategy._is_auction_time(test_time) is True

    def test_is_auction_time_before_window(self, morning_sniper_strategy):
        """测试在竞价时间窗口之前"""
        test_time = datetime(2026, 1, 30, 9, 10, 0)
        assert morning_sniper_strategy._is_auction_time(test_time) is False

    def test_is_auction_time_after_window(self, morning_sniper_strategy):
        """测试在竞价时间窗口之后"""
        test_time = datetime(2026, 1, 30, 9, 30, 0)
        assert morning_sniper_strategy._is_auction_time(test_time) is False


class TestGenerateSignals:
    """测试信号生成"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(self, morning_sniper_strategy, sample_auction_data):
        """测试使用有效数据生成信号"""
        signals = await morning_sniper_strategy.generate_signals(sample_auction_data)

        # STOCK1和STOCK3符合条件
        assert len(signals) > 0
        assert all(s.action == "buy" for s in signals)
        assert all(s.confidence > 0 for s in signals)

    @pytest.mark.asyncio
    async def test_generate_signals_outside_auction_time(self, morning_sniper_strategy):
        """测试非竞价时间"""
        market_data = {
            "current_time": datetime(2026, 1, 30, 10, 0, 0),  # 非竞价时间
            "auction_data": {},
            "sentiment_scores": {},
            "hot_themes": [],
        }

        signals = await morning_sniper_strategy.generate_signals(market_data)

        # 非竞价时间应该返回空列表
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_after_deadline(self, morning_sniper_strategy):
        """测试超过下单截止时间"""
        market_data = {
            "current_time": datetime(2026, 1, 30, 9, 24, 45),  # 超过截止时间
            "auction_data": {},
            "sentiment_scores": {},
            "hot_themes": [],
        }

        signals = await morning_sniper_strategy.generate_signals(market_data)

        # 超过截止时间应该返回空列表
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self, morning_sniper_strategy):
        """测试空数据"""
        market_data = {
            "current_time": datetime(2026, 1, 30, 9, 20, 0),
            "auction_data": {},
            "sentiment_scores": {},
            "hot_themes": [],
        }

        signals = await morning_sniper_strategy.generate_signals(market_data)

        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_limits_to_top_5(self, morning_sniper_strategy):
        """测试信号数量限制为前5个"""
        # 创建10个符合条件的标的
        auction_data = {}
        sentiment_scores = {}
        for i in range(10):
            auction_data[f"STOCK{i}"] = {
                "volume_ratio": 5.0,
                "bid_price_change": 0.06,
                "bid_volume": 1000000,
                "prev_close": 100.0,
                "themes": ["AI"],
            }
            sentiment_scores[f"STOCK{i}"] = 0.85

        market_data = {
            "current_time": datetime(2026, 1, 30, 9, 20, 0),
            "auction_data": auction_data,
            "sentiment_scores": sentiment_scores,
            "hot_themes": ["AI"],
        }

        signals = await morning_sniper_strategy.generate_signals(market_data)

        # 应该只返回前5个
        assert len(signals) <= 5

    @pytest.mark.asyncio
    async def test_generate_signals_exception_handling(self, morning_sniper_strategy):
        """测试异常处理"""
        from unittest.mock import patch

        market_data = {
            "current_time": datetime(2026, 1, 30, 9, 20, 0),
            "auction_data": {
                "TEST": {
                    "volume_ratio": 5.0,
                    "bid_price_change": 0.06,
                    "bid_volume": 1000000,
                    "prev_close": 100.0,
                    "themes": ["AI"],
                }
            },
            "sentiment_scores": {"TEST": 0.85},
            "hot_themes": ["AI"],
        }

        # Mock _analyze_auction 抛出异常
        with patch.object(
            morning_sniper_strategy, "_analyze_auction", side_effect=Exception("Test exception")
        ):
            signals = await morning_sniper_strategy.generate_signals(market_data)

            # 异常被捕获，应该继续处理其他标的
            assert isinstance(signals, list)


class TestAnalyzeAuction:
    """测试竞价数据分析"""

    @pytest.mark.asyncio
    async def test_analyze_auction_all_conditions_met(self, morning_sniper_strategy):
        """测试所有条件都满足"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.06,
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["AI"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        assert signal is not None
        assert signal.symbol == "TEST"
        assert signal.action == "buy"
        assert signal.confidence > 0.5

    @pytest.mark.asyncio
    async def test_analyze_auction_low_volume_ratio(self, morning_sniper_strategy):
        """测试量比不足"""
        auction_data = {
            "volume_ratio": 2.0,  # 低于阈值3.0
            "bid_price_change": 0.06,
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["AI"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        # 满足3个条件（价格、舆情、题材），应该生成信号
        assert signal is not None

    @pytest.mark.asyncio
    async def test_analyze_auction_price_too_low(self, morning_sniper_strategy):
        """测试涨幅过低"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.03,  # 低于阈值5%
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["AI"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        # 满足3个条件（量比、舆情、题材），应该生成信号
        assert signal is not None

    @pytest.mark.asyncio
    async def test_analyze_auction_price_too_high(self, morning_sniper_strategy):
        """测试涨幅过高"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.10,  # 高于阈值9.5%
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["AI"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        # 满足3个条件（量比、舆情、题材），应该生成信号
        assert signal is not None

    @pytest.mark.asyncio
    async def test_analyze_auction_low_sentiment(self, morning_sniper_strategy):
        """测试舆情不足"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.06,
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["AI"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.60,  # 低于阈值0.7
            hot_themes=["AI"]
        )

        # 满足3个条件（量比、价格、题材），应该生成信号
        assert signal is not None

    @pytest.mark.asyncio
    async def test_analyze_auction_no_theme_match(self, morning_sniper_strategy):
        """测试题材不匹配"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.06,
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["其他"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        # 满足3个条件（量比、价格、舆情），应该生成信号
        assert signal is not None

    @pytest.mark.asyncio
    async def test_analyze_auction_invalid_prev_close(self, morning_sniper_strategy):
        """测试无效的前收盘价"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.06,
            "bid_volume": 1000000,
            "prev_close": 0,  # 无效价格
            "themes": ["AI"],
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        # 无效价格应该返回None
        assert signal is None

    @pytest.mark.asyncio
    async def test_analyze_auction_three_conditions_met(self, morning_sniper_strategy):
        """测试恰好满足3个条件"""
        auction_data = {
            "volume_ratio": 5.0,  # 满足
            "bid_price_change": 0.06,  # 满足
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": ["其他"],  # 不满足
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85,  # 满足
            hot_themes=["AI"]
        )

        # 满足3个条件，应该生成信号
        assert signal is not None


class TestCalculateAuctionConfidence:
    """测试竞价置信度计算"""

    def test_calculate_confidence_strong_signal(self, morning_sniper_strategy):
        """测试强信号的置信度"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=6.0,  # 高量比
            bid_price_change=0.06,  # 适中涨幅
            sentiment_score=0.90,  # 高舆情
            theme_match=True,  # 题材匹配
        )

        # 强信号应该有较高置信度
        assert 0.80 < confidence <= 0.95

    def test_calculate_confidence_medium_signal(self, morning_sniper_strategy):
        """测试中等信号的置信度"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=4.0,
            bid_price_change=0.08,
            sentiment_score=0.75,
            theme_match=False,
        )

        # 中等信号应该有中等到较高置信度
        assert 0.70 < confidence <= 0.90

    def test_calculate_confidence_weak_signal(self, morning_sniper_strategy):
        """测试弱信号的置信度"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=3.0,  # 刚达到阈值
            bid_price_change=0.10,  # 涨幅过高
            sentiment_score=0.70,  # 刚达到阈值
            theme_match=False,
        )

        # 弱信号应该有较低置信度
        assert 0.50 <= confidence <= 0.75

    def test_calculate_confidence_optimal_price_range(self, morning_sniper_strategy):
        """测试最优涨幅范围"""
        # 5-7%涨幅应该得到最高价格得分
        confidence1 = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=5.0, bid_price_change=0.06, sentiment_score=0.80, theme_match=True
        )

        # 7-9%涨幅得分稍低
        confidence2 = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=5.0, bid_price_change=0.08, sentiment_score=0.80, theme_match=True
        )

        # 其他涨幅得分更低
        confidence3 = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=5.0, bid_price_change=0.04, sentiment_score=0.80, theme_match=True
        )

        assert confidence1 >= confidence2 >= confidence3

    def test_calculate_confidence_minimum_threshold(self, morning_sniper_strategy):
        """测试最低置信度阈值"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=3.0, bid_price_change=0.10, sentiment_score=0.50, theme_match=False
        )

        # 置信度应该不低于0.5
        assert confidence >= 0.5

    def test_calculate_confidence_maximum_cap(self, morning_sniper_strategy):
        """测试最高置信度上限"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=10.0, bid_price_change=0.06, sentiment_score=1.0, theme_match=True
        )

        # 置信度应该不超过0.95
        assert confidence <= 0.95


class TestCalculatePositionSizes:
    """测试仓位计算"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_signals(self, morning_sniper_strategy):
        """测试使用信号计算仓位"""
        signals = [
            Signal(symbol="STOCK1", action="buy", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="STOCK2", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
            Signal(symbol="STOCK3", action="buy", confidence=0.70, timestamp="2026-01-30", reason="test"),
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 应该生成仓位
        assert len(positions) == 3
        assert all(p.size > 0 for p in positions)
        # 占位价格应该为100.0
        assert all(p.entry_price == 100.0 for p in positions)
        assert all(p.current_price == 100.0 for p in positions)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_single(self, morning_sniper_strategy):
        """测试单股仓位上限"""
        signals = [
            Signal(symbol="STOCK1", action="buy", confidence=0.95, timestamp="2026-01-30", reason="test"),
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 单股仓位不应超过5%（首板策略限制）
        assert positions[0].size <= 0.05

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_total(self, morning_sniper_strategy):
        """测试总仓位上限"""
        # 创建多个高置信度信号
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.90, timestamp="2026-01-30", reason="test")
            for i in range(10)
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过20%（首板策略限制）
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.20

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self, morning_sniper_strategy):
        """测试空信号列表"""
        positions = await morning_sniper_strategy.calculate_position_sizes([])

        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_filters_sell_signals(self, morning_sniper_strategy):
        """测试过滤卖出信号"""
        signals = [
            Signal(symbol="STOCK1", action="sell", confidence=0.85, timestamp="2026-01-30", reason="test"),
            Signal(symbol="STOCK2", action="buy", confidence=0.75, timestamp="2026-01-30", reason="test"),
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 只应该有买入信号的仓位
        assert len(positions) == 1
        assert positions[0].symbol == "STOCK2"

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self, morning_sniper_strategy):
        """测试置信度影响仓位大小"""
        signals = [
            Signal(symbol="HIGH", action="buy", confidence=0.95, timestamp="2026-01-30", reason="test"),
            Signal(symbol="LOW", action="buy", confidence=0.60, timestamp="2026-01-30", reason="test"),
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 高置信度应该有更大的仓位
        high_pos = next(p for p in positions if p.symbol == "HIGH")
        low_pos = next(p for p in positions if p.symbol == "LOW")
        assert high_pos.size > low_pos.size

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_stops_at_minimum(self, morning_sniper_strategy):
        """测试达到最小仓位时停止"""
        # 创建足够多的信号以超过max_total
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.90, timestamp="2026-01-30", reason="test")
            for i in range(20)
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 总仓位应该接近20%
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.20
        # 所有仓位应该大于等于1%
        assert all(p.size >= 0.01 for p in positions)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_adjusts_last_position(self, morning_sniper_strategy):
        """测试调整最后一个仓位以不超过总仓位上限"""
        # 创建信号使得最后一个需要调整
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=0.95, timestamp="2026-01-30", reason="test")
            for i in range(5)
        ]

        positions = await morning_sniper_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过20%
        total_position = sum(p.size for p in positions)
        assert total_position <= 0.20
        # 最后一个仓位可能被调整
        assert len(positions) >= 4


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_keys(self, morning_sniper_strategy):
        """测试缺少键的数据"""
        market_data = {
            "current_time": datetime(2026, 1, 30, 9, 20, 0),
            "auction_data": {
                "TEST": {
                    "volume_ratio": 5.0,
                    # 缺少其他键
                }
            },
        }

        signals = await morning_sniper_strategy.generate_signals(market_data)

        # 应该能处理缺失的键
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_generate_signals_with_default_current_time(self, morning_sniper_strategy):
        """测试使用默认当前时间"""
        market_data = {
            # 缺少current_time，应该使用datetime.now()
            "auction_data": {},
            "sentiment_scores": {},
            "hot_themes": [],
        }

        signals = await morning_sniper_strategy.generate_signals(market_data)

        # 应该能正常处理
        assert isinstance(signals, list)

    def test_calculate_confidence_with_extreme_volume_ratio(self, morning_sniper_strategy):
        """测试极端量比"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=100.0,  # 极端量比
            bid_price_change=0.06,
            sentiment_score=0.80,
            theme_match=True,
        )

        # 置信度应该被限制在0.95
        assert confidence <= 0.95

    def test_calculate_confidence_with_extreme_sentiment(self, morning_sniper_strategy):
        """测试极端舆情"""
        confidence = morning_sniper_strategy._calculate_auction_confidence(
            volume_ratio=5.0, bid_price_change=0.06, sentiment_score=2.0,  # 极端舆情
            theme_match=True
        )

        # 置信度应该被限制在0.95
        assert confidence <= 0.95

    @pytest.mark.asyncio
    async def test_analyze_auction_with_empty_themes(self, morning_sniper_strategy):
        """测试空题材列表"""
        auction_data = {
            "volume_ratio": 5.0,
            "bid_price_change": 0.06,
            "bid_volume": 1000000,
            "prev_close": 100.0,
            "themes": [],  # 空题材
        }

        signal = await morning_sniper_strategy._analyze_auction(
            "TEST", auction_data, sentiment_score=0.85, hot_themes=["AI"]
        )

        # 应该能正常处理
        assert isinstance(signal, (Signal, type(None)))
