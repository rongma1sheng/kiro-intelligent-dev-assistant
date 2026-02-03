"""测试示例动量策略

白皮书依据: 第四章 4.2 斯巴达竞技场
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.strategies.tier1_micro.example_momentum_strategy import (
    ExampleMomentumStrategy,
    create_from_arena_result,
)
from src.strategies.data_models import (
    StrategyConfig,
    ArenaTestResult,
    Signal,
    Position,
)


@pytest.fixture
def strategy_config():
    """创建测试用策略配置"""
    return StrategyConfig(
        strategy_name="test_momentum",
        capital_tier="tier1_micro",
        max_position=0.8,
        max_single_stock=0.15,
        max_industry=0.3,
        stop_loss_pct=-0.05,
        take_profit_pct=0.10,
        trailing_stop_enabled=False,
        liquidity_threshold=1000000.0,
        max_order_pct_of_volume=0.05,
        trading_frequency="medium",
        holding_period_days=5,
    )


@pytest.fixture
def momentum_strategy(strategy_config):
    """创建测试用动量策略实例"""
    return ExampleMomentumStrategy(name="test_momentum", config=strategy_config)


@pytest.fixture
def sample_market_data():
    """创建测试用市场数据"""
    return {
        "prices": {
            "AAPL": [100, 102, 105, 108, 110, 112, 115, 118, 120, 122, 125, 128, 130, 132, 135, 138, 140, 142, 145, 148, 150],  # 强势上涨
            "GOOGL": [200, 202, 204, 206, 208, 210, 212, 214, 216, 218, 220, 222, 224, 226, 228, 230, 232, 234, 236, 238, 240],  # 稳定上涨
            "MSFT": [150, 149, 148, 147, 146, 145, 144, 143, 142, 141, 140, 139, 138, 137, 136, 135, 134, 133, 132, 131, 130],  # 持续下跌
            "TSLA": [300, 298, 296, 294, 292, 290, 288, 286, 284, 282, 280, 278, 276, 274, 272, 270, 268, 266, 264, 262, 260],  # 强势下跌
            "AMZN": [180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180],  # 横盘
        },
        "volumes": {
            "AAPL": [1000000] * 21,
            "GOOGL": [800000] * 21,
            "MSFT": [900000] * 21,
            "TSLA": [1200000] * 21,
            "AMZN": [700000] * 21,
        },
        "timestamp": "2026-01-29",
    }


class TestExampleMomentumStrategy:
    """测试ExampleMomentumStrategy类"""

    def test_initialization(self, momentum_strategy, strategy_config):
        """测试策略初始化"""
        assert momentum_strategy.name == "test_momentum"
        assert momentum_strategy.config == strategy_config
        assert momentum_strategy.lookback_days == 20
        assert momentum_strategy.top_n == 10
        assert momentum_strategy.max_position == 0.8
        assert momentum_strategy.max_single_stock == 0.15

    @pytest.mark.asyncio
    async def test_generate_signals_with_valid_data(self, momentum_strategy, sample_market_data):
        """测试使用有效数据生成信号"""
        signals = await momentum_strategy.generate_signals(sample_market_data)

        # 应该生成信号
        assert len(signals) > 0

        # 检查买入信号（正动量）
        buy_signals = [s for s in signals if s.action == "buy"]
        assert len(buy_signals) > 0

        # AAPL应该有买入信号（最强势）
        aapl_buy = [s for s in buy_signals if s.symbol == "AAPL"]
        assert len(aapl_buy) > 0
        assert aapl_buy[0].confidence > 0
        assert "正动量" in aapl_buy[0].reason

        # 检查卖出信号（负动量）
        sell_signals = [s for s in signals if s.action == "sell"]
        assert len(sell_signals) > 0

        # TSLA应该有卖出信号（最弱势）
        tsla_sell = [s for s in sell_signals if s.symbol == "TSLA"]
        assert len(tsla_sell) > 0
        assert tsla_sell[0].confidence > 0
        assert "负动量" in tsla_sell[0].reason

    @pytest.mark.asyncio
    async def test_generate_signals_with_empty_data(self, momentum_strategy):
        """测试空数据生成信号"""
        empty_data = {"prices": {}, "timestamp": "2026-01-29"}
        signals = await momentum_strategy.generate_signals(empty_data)

        # 空数据应该返回空信号列表
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_with_insufficient_data(self, momentum_strategy):
        """测试数据不足时生成信号"""
        insufficient_data = {
            "prices": {
                "AAPL": [100, 102, 105],  # 只有3天数据，不足20天
            },
            "timestamp": "2026-01-29",
        }
        signals = await momentum_strategy.generate_signals(insufficient_data)

        # 数据不足应该返回空信号列表
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_generate_signals_momentum_calculation(self, momentum_strategy):
        """测试动量计算的正确性"""
        test_data = {
            "prices": {
                "TEST1": [100] * 20 + [150],  # 50%涨幅
                "TEST2": [100] * 20 + [50],   # 50%跌幅
            },
            "timestamp": "2026-01-29",
        }
        signals = await momentum_strategy.generate_signals(test_data)

        # 检查买入信号
        buy_signals = [s for s in signals if s.action == "buy" and s.symbol == "TEST1"]
        assert len(buy_signals) == 1
        # 50%动量应该有较高置信度
        assert buy_signals[0].confidence > 0.5

        # 检查卖出信号
        sell_signals = [s for s in signals if s.action == "sell" and s.symbol == "TEST2"]
        assert len(sell_signals) == 1
        assert sell_signals[0].confidence > 0.5

    @pytest.mark.asyncio
    async def test_generate_signals_only_positive_momentum_for_buy(self, momentum_strategy):
        """测试只对正动量生成买入信号"""
        test_data = {
            "prices": {
                "DOWN1": [100] * 20 + [90],  # 负动量
                "DOWN2": [100] * 20 + [80],  # 负动量
            },
            "timestamp": "2026-01-29",
        }
        signals = await momentum_strategy.generate_signals(test_data)

        # 不应该有买入信号
        buy_signals = [s for s in signals if s.action == "buy"]
        assert len(buy_signals) == 0

        # 应该有卖出信号
        sell_signals = [s for s in signals if s.action == "sell"]
        assert len(sell_signals) > 0

    @pytest.mark.asyncio
    async def test_generate_signals_confidence_capped_at_one(self, momentum_strategy):
        """测试置信度上限为1.0"""
        test_data = {
            "prices": {
                "EXTREME": [100] * 20 + [500],  # 极端涨幅
            },
            "timestamp": "2026-01-29",
        }
        signals = await momentum_strategy.generate_signals(test_data)

        buy_signals = [s for s in signals if s.action == "buy"]
        assert len(buy_signals) > 0
        # 置信度应该被限制在1.0
        assert all(s.confidence <= 1.0 for s in buy_signals)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_equal_weight(self, momentum_strategy):
        """测试等权重仓位分配"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test"),
            Signal(symbol="MSFT", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test"),
        ]

        positions = await momentum_strategy.calculate_position_sizes(signals)

        # 应该有3个仓位
        assert len(positions) == 3

        # 每个仓位应该约为 max_position / 3 = 0.267，但会被max_single_stock (0.15)限制
        # 所以实际每个仓位应该是0.15
        for pos in positions:
            assert pos.size == momentum_strategy.max_single_stock

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_confidence(self, momentum_strategy):
        """测试根据置信度调整仓位"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test"),
            Signal(symbol="GOOGL", action="buy", confidence=0.5, timestamp="2026-01-29", reason="test"),
        ]

        positions = await momentum_strategy.calculate_position_sizes(signals)

        # 应该有2个仓位
        assert len(positions) == 2

        # base_size = 0.8 / 2 = 0.4
        # AAPL: 0.4 * 1.0 = 0.4, 但被max_single_stock (0.15)限制 -> 0.15
        # GOOGL: 0.4 * 0.5 = 0.2, 但被max_single_stock (0.15)限制 -> 0.15
        # 由于都被限制了，所以两者相等
        aapl_pos = [p for p in positions if p.symbol == "AAPL"][0]
        googl_pos = [p for p in positions if p.symbol == "GOOGL"][0]
        
        # 两者都应该是max_single_stock
        assert aapl_pos.size == momentum_strategy.max_single_stock
        assert googl_pos.size == momentum_strategy.max_single_stock

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_confidence_affects_size(self, momentum_strategy):
        """测试置信度确实影响仓位大小（当不被max_single_stock限制时）"""
        # 使用更多信号，使得base_size更小，不会触发max_single_stock限制
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=1.0 if i == 0 else 0.5, timestamp="2026-01-29", reason="test")
            for i in range(10)
        ]

        positions = await momentum_strategy.calculate_position_sizes(signals)

        # 应该有10个仓位
        assert len(positions) == 10

        # base_size = 0.8 / 10 = 0.08
        # STOCK0: 0.08 * 1.0 = 0.08 (不超过0.15)
        # STOCK1-9: 0.08 * 0.5 = 0.04 (不超过0.15)
        stock0_pos = [p for p in positions if p.symbol == "STOCK0"][0]
        stock1_pos = [p for p in positions if p.symbol == "STOCK1"][0]
        
        assert stock0_pos.size > stock1_pos.size
        assert abs(stock0_pos.size - 0.08) < 0.01
        assert abs(stock1_pos.size - 0.04) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_respects_max_single_stock(self, momentum_strategy):
        """测试单股上限限制"""
        signals = [
            Signal(symbol="AAPL", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test"),
        ]

        positions = await momentum_strategy.calculate_position_sizes(signals)

        # 单个仓位不应超过max_single_stock
        assert all(p.size <= momentum_strategy.max_single_stock for p in positions)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_no_buy_signals(self, momentum_strategy):
        """测试没有买入信号时的仓位计算"""
        signals = [
            Signal(symbol="AAPL", action="sell", confidence=1.0, timestamp="2026-01-29", reason="test"),
        ]

        positions = await momentum_strategy.calculate_position_sizes(signals)

        # 没有买入信号应该返回空仓位列表
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_with_empty_signals(self, momentum_strategy):
        """测试空信号列表的仓位计算"""
        positions = await momentum_strategy.calculate_position_sizes([])

        # 空信号应该返回空仓位列表
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_apply_risk_controls(self, momentum_strategy):
        """测试风险控制应用"""
        positions = [
            Position(
                symbol="AAPL",
                size=0.2,
                entry_price=100.0,
                current_price=100.0,
                pnl_pct=0.0,
                holding_days=0,
                industry="科技",
            ),
        ]

        filtered_positions = await momentum_strategy.apply_risk_controls(positions)

        # 应该调用父类的风险控制
        assert isinstance(filtered_positions, list)


class TestCreateFromArenaResult:
    """测试从Arena结果创建策略"""

    def test_create_from_dict(self):
        """测试从字典创建策略"""
        arena_result = {
            "strategy_name": "momentum_v1",
            "test_tier": "tier1_micro",
            "initial_capital": 10000.0,
            "final_capital": 14500.0,
            "total_return_pct": 0.45,
            "sharpe_ratio": 2.5,
            "max_drawdown_pct": -0.12,
            "win_rate": 0.65,
            "evolved_params": {
                "max_position": 0.8,
                "max_single_stock": 0.15,
                "max_industry": 0.3,
                "stop_loss_pct": -0.05,
                "take_profit_pct": 0.10,
            },
            "avg_slippage_pct": 0.001,
            "avg_impact_cost_pct": 0.002,
            "test_start_date": "2025-01-01",
            "test_end_date": "2025-12-31",
        }

        strategy = create_from_arena_result(arena_result)

        assert strategy.name == "momentum_v1"
        assert strategy.config.max_position == 0.8
        assert strategy.config.max_single_stock == 0.15

    def test_create_from_arena_test_result(self):
        """测试从ArenaTestResult对象创建策略"""
        arena_result = ArenaTestResult(
            strategy_name="momentum_v2",
            test_tier="tier2_small",
            initial_capital=50000.0,
            final_capital=75000.0,
            total_return_pct=0.50,
            sharpe_ratio=3.0,
            max_drawdown_pct=-0.10,
            win_rate=0.70,
            evolved_params={
                "max_position": 0.9,
                "max_single_stock": 0.20,
                "max_industry": 0.35,
                "stop_loss_pct": -0.08,
                "take_profit_pct": 0.15,
            },
            avg_slippage_pct=0.001,
            avg_impact_cost_pct=0.002,
            test_start_date="2025-01-01",
            test_end_date="2025-12-31",
        )

        strategy = create_from_arena_result(arena_result)

        assert strategy.name == "momentum_v2"
        assert strategy.config.max_position == 0.9
        assert strategy.config.max_single_stock == 0.20


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_generate_signals_with_missing_timestamp(self, momentum_strategy, sample_market_data):
        """测试缺少时间戳的情况"""
        data_without_timestamp = {"prices": sample_market_data["prices"]}
        signals = await momentum_strategy.generate_signals(data_without_timestamp)

        # 应该仍然能生成信号，只是时间戳为空
        assert len(signals) > 0
        assert all(s.timestamp == "" for s in signals)

    @pytest.mark.asyncio
    async def test_generate_signals_with_zero_prices(self, momentum_strategy):
        """测试价格为零的情况"""
        test_data = {
            "prices": {
                "ZERO": [0] * 21,
            },
            "timestamp": "2026-01-29",
        }

        # 应该能处理除零错误
        signals = await momentum_strategy.generate_signals(test_data)
        # 零价格无法计算动量，应该返回空列表或跳过
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_total_not_exceeding_max(self, momentum_strategy):
        """测试总仓位不超过上限"""
        # 创建大量买入信号
        signals = [
            Signal(symbol=f"STOCK{i}", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test")
            for i in range(20)
        ]

        positions = await momentum_strategy.calculate_position_sizes(signals)

        # 总仓位不应超过max_position
        total_position = sum(p.size for p in positions)
        assert total_position <= momentum_strategy.max_position + 0.01  # 允许小误差

    @pytest.mark.asyncio
    async def test_calculate_position_sizes_exception_handling(self, momentum_strategy):
        """测试仓位计算异常处理"""
        # 创建一个会导致异常的信号（通过mock）
        from unittest.mock import patch
        
        signals = [
            Signal(symbol="TEST", action="buy", confidence=1.0, timestamp="2026-01-29", reason="test")
        ]
        
        # Mock Position构造函数抛出异常
        with patch('src.strategies.tier1_micro.example_momentum_strategy.Position', side_effect=Exception("Test error")):
            positions = await momentum_strategy.calculate_position_sizes(signals)
            
            # 异常被捕获，应该返回空列表
            assert positions == []
