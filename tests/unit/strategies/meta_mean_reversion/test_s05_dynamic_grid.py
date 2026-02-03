"""S05 Dynamic Grid (网格) 策略测试

测试目标: 100%覆盖率
测试策略: S05_Dynamic_Grid - 动态网格策略
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.strategies.meta_mean_reversion.s05_dynamic_grid import S05DynamicGridStrategy
from src.strategies.data_models import Position, Signal, StrategyConfig


@pytest.fixture
def strategy_config():
    """创建策略配置"""
    return StrategyConfig(
        strategy_name="S05_Dynamic_Grid",
        capital_tier="tier2_hundred_k",
        max_position=0.30,
        max_single_stock=0.10,
        max_industry=0.20,
        stop_loss_pct=-0.05,
        take_profit_pct=0.15,
        trailing_stop_enabled=False,
    )


@pytest.fixture
def strategy(strategy_config):
    """创建S05策略实例"""
    return S05DynamicGridStrategy(config=strategy_config)


class TestS05DynamicGridInitialization:
    """测试S05策略初始化"""

    def test_initialization(self, strategy):
        """测试策略初始化"""
        assert strategy.name == "S05_Dynamic_Grid"
        assert strategy.grid_levels == 5
        assert strategy.base_grid_spacing == 0.02
        assert strategy.volatility_adjustment is True
        assert strategy.min_grid_spacing == 0.01
        assert strategy.max_grid_spacing == 0.05
        assert strategy.active_grids == {}


class TestS05SignalGeneration:
    """测试S05信号生成"""

    @pytest.mark.asyncio
    async def test_generate_signals_empty_data(self, strategy):
        """测试空数据"""
        market_data = {"symbols": [], "prices": {}, "indicators": {}, "ai_predictions": {}}
        signals = await strategy.generate_signals(market_data)
        assert signals == []

    @pytest.mark.asyncio
    async def test_generate_signals_buy_signal(self, strategy):
        """测试生成买入信号"""
        # First create a grid at price 10.0
        strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        # Then test with lower price to trigger buy
        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 9.8}},  # 价格低于中心，触发买入
            "indicators": {
                "000001.SZ": {
                    "adx_14": 20.0,  # 震荡市
                    "bb_width": 0.10,
                    "atr_ratio": 0.02,
                    "volatility_20d": 0.02,
                }
            },
            "ai_predictions": {"000001.SZ": {"support": 9.5, "resistance": 10.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 1
        assert signals[0].symbol == "000001.SZ"
        assert signals[0].action == "buy"

    @pytest.mark.asyncio
    async def test_generate_signals_sell_signal(self, strategy):
        """测试生成卖出信号"""
        # First create a grid at price 10.0
        strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        # Then test with higher price to trigger sell
        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 10.2}},  # 价格高于中心，触发卖出
            "indicators": {
                "000001.SZ": {
                    "adx_14": 20.0,  # 震荡市
                    "bb_width": 0.10,
                    "atr_ratio": 0.02,
                    "volatility_20d": 0.02,
                }
            },
            "ai_predictions": {"000001.SZ": {"support": 9.5, "resistance": 10.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert len(signals) == 1
        assert signals[0].symbol == "000001.SZ"
        assert signals[0].action == "sell"

    @pytest.mark.asyncio
    async def test_generate_signals_invalid_price(self, strategy):
        """测试无效价格"""
        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 0}},
            "indicators": {
                "000001.SZ": {
                    "adx_14": 20.0,
                    "bb_width": 0.10,
                    "atr_ratio": 0.02,
                    "volatility_20d": 0.02,
                }
            },
            "ai_predictions": {"000001.SZ": {"support": 9.5, "resistance": 10.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert signals == []

    @pytest.mark.asyncio
    async def test_generate_signals_not_range_bound(self, strategy):
        """测试非震荡行情"""
        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 10.0}},
            "indicators": {
                "000001.SZ": {
                    "adx_14": 30.0,  # 趋势市
                    "bb_width": 0.10,
                    "atr_ratio": 0.02,
                    "volatility_20d": 0.02,
                }
            },
            "ai_predictions": {"000001.SZ": {"support": 9.5, "resistance": 10.5}},
        }

        signals = await strategy.generate_signals(market_data)
        assert signals == []

    @pytest.mark.asyncio
    async def test_generate_signals_exception_handling(self, strategy):
        """测试异常处理"""
        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 10.0}},
            "indicators": {"000001.SZ": {}},  # 缺少必要指标
            "ai_predictions": {},
        }

        # 应该捕获异常并继续
        signals = await strategy.generate_signals(market_data)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_generate_signals_with_exception_in_analysis(self, strategy):
        """测试分析过程中的异常"""
        # 使用Mock触发异常
        from unittest.mock import patch

        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 10.0}},
            "indicators": {
                "000001.SZ": {
                    "adx_14": 20.0,
                    "bb_width": 0.10,
                    "atr_ratio": 0.02,
                    "volatility_20d": 0.02,
                }
            },
            "ai_predictions": {"000001.SZ": {"support": 9.5, "resistance": 10.5}},
        }

        # Mock _analyze_grid_opportunity to raise exception
        with patch.object(strategy, "_analyze_grid_opportunity", side_effect=Exception("Test exception")):
            signals = await strategy.generate_signals(market_data)
            # Should handle exception and return empty list
            assert signals == []


class TestS05RangeBoundDetection:
    """测试震荡行情判断"""

    def test_is_range_bound_true(self, strategy):
        """测试震荡行情识别"""
        indicator_data = {"adx_14": 20.0, "bb_width": 0.10, "atr_ratio": 0.02}
        assert strategy._is_range_bound(indicator_data) is True

    def test_is_range_bound_high_adx(self, strategy):
        """测试高ADX（趋势市）"""
        indicator_data = {"adx_14": 30.0, "bb_width": 0.10, "atr_ratio": 0.02}
        assert strategy._is_range_bound(indicator_data) is False

    def test_is_range_bound_narrow_bb(self, strategy):
        """测试窄布林带"""
        indicator_data = {"adx_14": 20.0, "bb_width": 0.03, "atr_ratio": 0.02}
        assert strategy._is_range_bound(indicator_data) is False

    def test_is_range_bound_wide_bb(self, strategy):
        """测试宽布林带"""
        indicator_data = {"adx_14": 20.0, "bb_width": 0.20, "atr_ratio": 0.02}
        assert strategy._is_range_bound(indicator_data) is False

    def test_is_range_bound_high_atr(self, strategy):
        """测试高ATR"""
        indicator_data = {"adx_14": 20.0, "bb_width": 0.10, "atr_ratio": 0.05}
        assert strategy._is_range_bound(indicator_data) is False


class TestS05GridConfiguration:
    """测试网格配置"""

    def test_get_or_create_grid_new(self, strategy):
        """测试创建新网格"""
        grid = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        assert grid["center"] == 10.0
        assert grid["support"] == 9.5
        assert grid["resistance"] == 10.5
        assert len(grid["buy_levels"]) == 5
        assert len(grid["sell_levels"]) == 5
        assert grid["executed_buys"] == set()
        assert grid["executed_sells"] == set()

    def test_get_or_create_grid_existing(self, strategy):
        """测试获取已存在的网格"""
        # 先创建网格
        grid1 = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        # 再次获取（价格变化不大）
        grid2 = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.05,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        assert grid1 is grid2

    def test_get_or_create_grid_price_deviation(self, strategy):
        """测试价格偏离重新计算"""
        # 先创建网格
        strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        # 价格偏离超过10%，应该重新计算
        grid2 = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=11.5,  # 偏离15%
            volatility=0.02,
            ai_prediction={"support": 10.9, "resistance": 12.0},
        )

        assert grid2["center"] == 11.5

    def test_grid_spacing_with_volatility_adjustment(self, strategy):
        """测试波动率调整网格间距"""
        strategy.volatility_adjustment = True

        # 高波动率
        grid_high = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.04,  # 2倍基准波动率
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        # 低波动率
        grid_low = strategy._get_or_create_grid(
            symbol="000002.SZ",
            current_price=10.0,
            volatility=0.01,  # 0.5倍基准波动率
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        assert grid_high["grid_spacing"] > grid_low["grid_spacing"]

    def test_grid_spacing_without_volatility_adjustment(self, strategy):
        """测试不调整波动率"""
        strategy.volatility_adjustment = False

        grid = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.04,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        assert grid["grid_spacing"] == strategy.base_grid_spacing

    def test_grid_spacing_min_max_limits(self, strategy):
        """测试网格间距上下限"""
        strategy.volatility_adjustment = True

        # 极高波动率
        grid_max = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.10,  # 极高波动率
            ai_prediction={"support": 9.0, "resistance": 11.0},
        )

        # 极低波动率
        grid_min = strategy._get_or_create_grid(
            symbol="000002.SZ",
            current_price=10.0,
            volatility=0.002,  # 极低波动率
            ai_prediction={"support": 9.8, "resistance": 10.2},
        )

        assert grid_max["grid_spacing"] <= strategy.max_grid_spacing
        assert grid_min["grid_spacing"] >= strategy.min_grid_spacing

    def test_grid_default_ai_prediction(self, strategy):
        """测试默认AI预测值"""
        grid = strategy._get_or_create_grid(
            symbol="000001.SZ", current_price=10.0, volatility=0.02, ai_prediction={}  # 空预测
        )

        # 应该使用默认值
        assert grid["support"] == 10.0 * 0.95
        assert grid["resistance"] == 10.0 * 1.05


class TestS05GridAction:
    """测试网格交易动作"""

    def test_determine_grid_action_buy(self, strategy):
        """测试买入动作"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": set(),
            "executed_sells": set(),
        }

        action, level, confidence = strategy._determine_grid_action(9.8, grid_config)

        assert action == "buy"
        assert level == 1
        assert 0.6 <= confidence <= 0.85

    def test_determine_grid_action_sell(self, strategy):
        """测试卖出动作"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": set(),
            "executed_sells": set(),
        }

        action, level, confidence = strategy._determine_grid_action(10.2, grid_config)

        assert action == "sell"
        assert level == 1
        assert 0.6 <= confidence <= 0.85

    def test_determine_grid_action_hold(self, strategy):
        """测试持有动作"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": set(),
            "executed_sells": set(),
        }

        action, level, confidence = strategy._determine_grid_action(10.0, grid_config)

        assert action == "hold"
        assert level == 0
        assert confidence == 0.0

    def test_determine_grid_action_skip_executed_buy(self, strategy):
        """测试跳过已执行的买入层级"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": {1},  # 第1层已执行
            "executed_sells": set(),
        }

        # 价格在第2层
        action, level, confidence = strategy._determine_grid_action(9.6, grid_config)

        # 应该触发第2层
        assert action == "buy"
        assert level == 2

    def test_determine_grid_action_skip_executed_sell(self, strategy):
        """测试跳过已执行的卖出层级"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": set(),
            "executed_sells": {1},  # 第1层已执行
        }

        # 价格在第2层
        action, level, confidence = strategy._determine_grid_action(10.4, grid_config)

        # 应该触发第2层
        assert action == "sell"
        assert level == 2

    def test_determine_grid_action_deep_buy_level(self, strategy):
        """测试深层买入（置信度更高）"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": {1, 2, 3, 4},  # 前4层已执行
            "executed_sells": set(),
        }

        # 价格触及第5层
        action, level, confidence = strategy._determine_grid_action(9.0, grid_config)

        assert action == "buy"
        assert level == 5
        assert confidence >= 0.80  # 深层置信度更高

    def test_determine_grid_action_price_tolerance(self, strategy):
        """测试价格容差"""
        grid_config = {
            "buy_levels": [9.8, 9.6, 9.4, 9.2, 9.0],
            "sell_levels": [10.2, 10.4, 10.6, 10.8, 11.0],
            "executed_buys": set(),
            "executed_sells": set(),
        }

        # 买入容差测试（允许1%误差）
        # 9.8 * 1.01 = 9.898, 所以9.89应该触发
        action1, _, _ = strategy._determine_grid_action(9.89, grid_config)
        assert action1 == "buy"

        # 卖出容差测试（允许1%误差）
        # 10.2 * 0.99 = 10.098, 所以10.1应该触发
        action2, _, _ = strategy._determine_grid_action(10.1, grid_config)
        assert action2 == "sell"


class TestS05PositionCalculation:
    """测试仓位计算"""

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_empty(self, strategy):
        """测试空信号"""
        positions = await strategy.calculate_position_sizes([])
        assert positions == []

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_single_buy(self, strategy):
        """测试单个买入信号"""
        signals = [
            Signal(
                symbol="000001.SZ",
                action="buy",
                confidence=0.70,
                timestamp=datetime.now().isoformat(),
                reason="网格买入",
            )
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert len(positions) == 1
        assert positions[0].symbol == "000001.SZ"
        assert positions[0].size > 0
        assert positions[0].entry_price == 100.0  # Placeholder
        assert positions[0].current_price == 100.0  # Placeholder

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_multiple_buys(self, strategy):
        """测试多个买入信号"""
        signals = [
            Signal(
                symbol="000001.SZ",
                action="buy",
                confidence=0.70,
                timestamp=datetime.now().isoformat(),
                reason="网格买入1",
            ),
            Signal(
                symbol="000002.SZ",
                action="buy",
                confidence=0.75,
                timestamp=datetime.now().isoformat(),
                reason="网格买入2",
            ),
        ]

        positions = await strategy.calculate_position_sizes(signals)

        assert len(positions) == 2
        total_size = sum(p.size for p in positions)
        assert total_size <= strategy.max_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_per_level(self, strategy):
        """测试每层仓位计算"""
        signals = [
            Signal(
                symbol="000001.SZ",
                action="buy",
                confidence=0.70,
                timestamp=datetime.now().isoformat(),
                reason="网格买入",
            )
        ]

        positions = await strategy.calculate_position_sizes(signals)

        # 每层仓位 = max_position / grid_levels
        expected_per_level = strategy.max_position / strategy.grid_levels
        assert positions[0].size <= expected_per_level

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_max_position_limit(self, strategy):
        """测试总仓位上限"""
        # 创建大量信号
        signals = [
            Signal(
                symbol=f"00000{i}.SZ",
                action="buy",
                confidence=0.80,
                timestamp=datetime.now().isoformat(),
                reason=f"网格买入{i}",
            )
            for i in range(10)
        ]

        positions = await strategy.calculate_position_sizes(signals)

        total_size = sum(p.size for p in positions)
        assert total_size <= strategy.max_position

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_skip_sell_signals(self, strategy):
        """测试跳过卖出信号"""
        signals = [
            Signal(
                symbol="000001.SZ",
                action="sell",
                confidence=0.70,
                timestamp=datetime.now().isoformat(),
                reason="网格卖出",
            )
        ]

        positions = await strategy.calculate_position_sizes(signals)
        assert positions == []

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_min_size_threshold(self, strategy):
        """测试最小仓位阈值"""
        # 设置很小的max_position
        strategy.max_position = 0.01

        signals = [
            Signal(
                symbol=f"00000{i}.SZ",
                action="buy",
                confidence=0.50,
                timestamp=datetime.now().isoformat(),
                reason=f"网格买入{i}",
            )
            for i in range(10)
        ]

        positions = await strategy.calculate_position_sizes(signals)

        # 应该在达到最小阈值时停止
        assert len(positions) < len(signals)


class TestS05GridManagement:
    """测试网格管理"""

    def test_mark_grid_executed_buy(self, strategy):
        """测试标记买入执行"""
        # 先创建网格
        strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        strategy.mark_grid_executed("000001.SZ", "buy", 1)

        grid = strategy.active_grids["000001.SZ"]
        assert 1 in grid["executed_buys"]

    def test_mark_grid_executed_sell(self, strategy):
        """测试标记卖出执行"""
        # 先创建网格
        strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        strategy.mark_grid_executed("000001.SZ", "sell", 2)

        grid = strategy.active_grids["000001.SZ"]
        assert 2 in grid["executed_sells"]

    def test_mark_grid_executed_nonexistent(self, strategy):
        """测试标记不存在的网格"""
        # 不应该抛出异常
        strategy.mark_grid_executed("000001.SZ", "buy", 1)

    def test_reset_grid(self, strategy):
        """测试重置网格"""
        # 先创建网格
        strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        assert "000001.SZ" in strategy.active_grids

        strategy.reset_grid("000001.SZ")

        assert "000001.SZ" not in strategy.active_grids

    def test_reset_grid_nonexistent(self, strategy):
        """测试重置不存在的网格"""
        # 不应该抛出异常
        strategy.reset_grid("000001.SZ")


class TestS05EdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_missing_market_data_keys(self, strategy):
        """测试缺少市场数据键"""
        market_data = {}  # 完全空的数据
        signals = await strategy.generate_signals(market_data)
        assert signals == []

    @pytest.mark.asyncio
    async def test_partial_indicator_data(self, strategy):
        """测试部分指标数据"""
        market_data = {
            "symbols": ["000001.SZ"],
            "prices": {"000001.SZ": {"close": 10.0}},
            "indicators": {"000001.SZ": {"adx_14": 20.0}},  # 缺少其他指标
            "ai_predictions": {},
        }

        signals = await strategy.generate_signals(market_data)
        # 应该使用默认值处理
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_zero_confidence_signal(self, strategy):
        """测试零置信度信号"""
        signals = [
            Signal(
                symbol="000001.SZ",
                action="buy",
                confidence=0.0,
                timestamp=datetime.now().isoformat(),
                reason="测试",
            )
        ]

        positions = await strategy.calculate_position_sizes(signals)
        # 零置信度应该产生零仓位或很小仓位
        if positions:
            assert positions[0].size < 0.01

    def test_grid_levels_boundary(self, strategy):
        """测试网格层数边界"""
        strategy.grid_levels = 1  # 最小层数

        grid = strategy._get_or_create_grid(
            symbol="000001.SZ",
            current_price=10.0,
            volatility=0.02,
            ai_prediction={"support": 9.5, "resistance": 10.5},
        )

        assert len(grid["buy_levels"]) == 1
        assert len(grid["sell_levels"]) == 1

    def test_extreme_volatility(self, strategy):
        """测试极端波动率"""
        strategy.volatility_adjustment = True

        # 零波动率
        grid_zero = strategy._get_or_create_grid(
            symbol="000001.SZ", current_price=10.0, volatility=0.0, ai_prediction={}
        )

        # 极高波动率
        grid_high = strategy._get_or_create_grid(
            symbol="000002.SZ", current_price=10.0, volatility=1.0, ai_prediction={}
        )

        # 应该在min和max之间
        assert strategy.min_grid_spacing <= grid_zero["grid_spacing"] <= strategy.max_grid_spacing
        assert strategy.min_grid_spacing <= grid_high["grid_spacing"] <= strategy.max_grid_spacing
