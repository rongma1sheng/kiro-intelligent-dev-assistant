"""
MIA系统基础数据模型测试

测试目标: src/base/models.py
覆盖率目标: 100%
测试策略: 全面测试所有数据模型的创建、验证、计算和边界情况
"""

import sys
from datetime import datetime
from unittest.mock import patch

import pytest

# 添加src路径
sys.path.insert(0, "src")

from base.models import (
    BarData,
    OrderData,
    SimulationResult,
    Strategy,
    TickData,
)


class TestStrategy:
    """测试策略基础模型"""

    def test_strategy_creation_minimal(self):
        """测试策略最小参数创建"""
        strategy = Strategy(strategy_id="test_001", name="测试策略", type="momentum", description="测试用动量策略")

        assert strategy.strategy_id == "test_001"
        assert strategy.name == "测试策略"
        assert strategy.type == "momentum"
        assert strategy.description == "测试用动量策略"
        assert strategy.version == "1.0.0"  # 默认值
        assert isinstance(strategy.created_at, datetime)
        assert isinstance(strategy.updated_at, datetime)
        assert strategy.parameters is None

    def test_strategy_creation_full(self):
        """测试策略完整参数创建"""
        created_time = datetime(2026, 1, 1, 10, 0, 0)
        updated_time = datetime(2026, 1, 2, 15, 30, 0)
        parameters = {"lookback": 20, "threshold": 0.02}

        strategy = Strategy(
            strategy_id="test_002",
            name="完整测试策略",
            type="mean_reversion",
            description="完整参数测试策略",
            version="2.1.0",
            created_at=created_time,
            updated_at=updated_time,
            parameters=parameters,
        )

        assert strategy.strategy_id == "test_002"
        assert strategy.name == "完整测试策略"
        assert strategy.type == "mean_reversion"
        assert strategy.description == "完整参数测试策略"
        assert strategy.version == "2.1.0"
        assert strategy.created_at == created_time
        assert strategy.updated_at == updated_time
        assert strategy.parameters == parameters

    def test_strategy_post_init_auto_timestamps(self):
        """测试策略自动时间戳设置"""
        with patch("base.models.datetime") as mock_datetime:
            mock_now = datetime(2026, 2, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            strategy = Strategy(
                strategy_id="test_003", name="自动时间戳策略", type="arbitrage", description="测试自动时间戳"
            )

            assert strategy.created_at == mock_now
            assert strategy.updated_at == mock_now

    def test_strategy_post_init_partial_timestamps(self):
        """测试策略部分时间戳设置"""
        created_time = datetime(2026, 1, 1, 10, 0, 0)

        with patch("base.models.datetime") as mock_datetime:
            mock_now = datetime(2026, 2, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            strategy = Strategy(
                strategy_id="test_004",
                name="部分时间戳策略",
                type="pairs_trading",
                description="测试部分时间戳",
                created_at=created_time,
            )

            assert strategy.created_at == created_time
            assert strategy.updated_at == mock_now

    def test_strategy_dataclass_features(self):
        """测试策略数据类特性"""
        strategy1 = Strategy(
            strategy_id="test_005", name="数据类测试", type="statistical_arbitrage", description="测试数据类特性"
        )

        strategy2 = Strategy(
            strategy_id="test_005",
            name="数据类测试",
            type="statistical_arbitrage",
            description="测试数据类特性",
            version="1.0.0",
            created_at=strategy1.created_at,
            updated_at=strategy1.updated_at,
            parameters=None,
        )

        # 测试相等性
        assert strategy1 == strategy2

        # 测试字符串表示
        str_repr = str(strategy1)
        assert "test_005" in str_repr
        assert "数据类测试" in str_repr

        # 测试repr
        repr_str = repr(strategy1)
        assert "Strategy" in repr_str
        assert "test_005" in repr_str

    def test_strategy_parameters_types(self):
        """测试策略参数类型"""
        # 测试不同类型的参数
        complex_params = {
            "string_param": "test_value",
            "int_param": 42,
            "float_param": 3.14,
            "bool_param": True,
            "list_param": [1, 2, 3],
            "dict_param": {"nested": "value"},
            "none_param": None,
        }

        strategy = Strategy(
            strategy_id="test_006",
            name="参数类型测试",
            type="multi_factor",
            description="测试各种参数类型",
            parameters=complex_params,
        )

        assert strategy.parameters == complex_params
        assert strategy.parameters["string_param"] == "test_value"
        assert strategy.parameters["int_param"] == 42
        assert strategy.parameters["float_param"] == 3.14
        assert strategy.parameters["bool_param"] is True
        assert strategy.parameters["list_param"] == [1, 2, 3]
        assert strategy.parameters["dict_param"] == {"nested": "value"}
        assert strategy.parameters["none_param"] is None


class TestSimulationResult:
    """测试模拟回测结果模型"""

    def test_simulation_result_creation_minimal(self):
        """测试模拟结果最小参数创建"""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 12, 31)
        daily_returns = [0.01, -0.005, 0.02, 0.0, -0.01]

        result = SimulationResult(
            strategy_id="sim_001",
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0,
            final_capital=110000.0,
            total_return=0.10,
            annual_return=0.10,
            sharpe_ratio=1.5,
            max_drawdown=0.05,
            volatility=0.15,
            win_rate=0.60,
            daily_returns=daily_returns,
            calmar_ratio=2.0,
        )

        assert result.strategy_id == "sim_001"
        assert result.start_date == start_date
        assert result.end_date == end_date
        assert result.initial_capital == 100000.0
        assert result.final_capital == 110000.0
        assert result.total_return == 0.10
        assert result.annual_return == 0.10
        assert result.sharpe_ratio == 1.5
        assert result.max_drawdown == 0.05
        assert result.volatility == 0.15
        assert result.win_rate == 0.60
        assert result.daily_returns == daily_returns
        assert result.calmar_ratio == 2.0

        # 测试默认值
        assert result.information_ratio is not None  # 由post_init计算
        assert result.downside_deviation is not None  # 由post_init计算
        assert result.monthly_turnover is None
        assert result.position_count is None

    def test_simulation_result_creation_full(self):
        """测试模拟结果完整参数创建"""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 12, 31)
        daily_returns = [0.01, -0.005, 0.02, 0.0, -0.01]

        result = SimulationResult(
            strategy_id="sim_002",
            start_date=start_date,
            end_date=end_date,
            initial_capital=500000.0,
            final_capital=650000.0,
            total_return=0.30,
            annual_return=0.30,
            sharpe_ratio=2.1,
            max_drawdown=0.08,
            volatility=0.18,
            win_rate=0.65,
            daily_returns=daily_returns,
            calmar_ratio=3.75,
            information_ratio=1.8,
            downside_deviation=0.12,
            monthly_turnover=0.25,
            position_count=150,
        )

        assert result.strategy_id == "sim_002"
        assert result.information_ratio == 1.8
        assert result.downside_deviation == 0.12
        assert result.monthly_turnover == 0.25
        assert result.position_count == 150

    def test_simulation_result_post_init_information_ratio(self):
        """测试信息比率自动计算"""
        daily_returns = [0.01, -0.005, 0.02, 0.0, -0.01, 0.015, -0.008]

        result = SimulationResult(
            strategy_id="sim_003",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            initial_capital=100000.0,
            final_capital=110000.0,
            total_return=0.10,
            annual_return=0.10,
            sharpe_ratio=1.5,
            max_drawdown=0.05,
            volatility=0.15,
            win_rate=0.60,
            daily_returns=daily_returns,
            calmar_ratio=2.0,
        )

        # 信息比率应该被自动计算
        assert result.information_ratio is not None
        assert isinstance(result.information_ratio, float)
        assert result.information_ratio != 0.0

    def test_simulation_result_post_init_downside_deviation(self):
        """测试下行偏差自动计算"""
        daily_returns = [0.01, -0.005, 0.02, 0.0, -0.01, 0.015, -0.008, -0.012]

        result = SimulationResult(
            strategy_id="sim_004",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            initial_capital=100000.0,
            final_capital=110000.0,
            total_return=0.10,
            annual_return=0.10,
            sharpe_ratio=1.5,
            max_drawdown=0.05,
            volatility=0.15,
            win_rate=0.60,
            daily_returns=daily_returns,
            calmar_ratio=2.0,
        )

        # 下行偏差应该被自动计算
        assert result.downside_deviation is not None
        assert isinstance(result.downside_deviation, float)
        assert result.downside_deviation > 0.0

    def test_simulation_result_post_init_edge_cases(self):
        """测试模拟结果边界情况"""
        # 测试空收益列表
        result_empty = SimulationResult(
            strategy_id="sim_005",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            initial_capital=100000.0,
            final_capital=100000.0,
            total_return=0.0,
            annual_return=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            volatility=0.0,
            win_rate=0.0,
            daily_returns=[],
            calmar_ratio=0.0,
        )

        # 空收益列表时，这些值保持为None（因为没有数据计算）
        assert result_empty.information_ratio is None
        assert result_empty.downside_deviation is None

    def test_simulation_result_post_init_single_return(self):
        """测试单个收益值情况"""
        result_single = SimulationResult(
            strategy_id="sim_006",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 2),
            initial_capital=100000.0,
            final_capital=101000.0,
            total_return=0.01,
            annual_return=0.01,
            sharpe_ratio=0.5,
            max_drawdown=0.0,
            volatility=0.01,
            win_rate=1.0,
            daily_returns=[0.01],
            calmar_ratio=1.0,
        )

        assert result_single.information_ratio == 0.0  # 单个值标准差为0
        assert result_single.downside_deviation == 0.0  # 无负收益

    def test_simulation_result_post_init_zero_std(self):
        """测试零标准差情况"""
        # 所有收益相同，标准差为0
        daily_returns = [0.01, 0.01, 0.01, 0.01, 0.01]

        result = SimulationResult(
            strategy_id="sim_007",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 5),
            initial_capital=100000.0,
            final_capital=105000.0,
            total_return=0.05,
            annual_return=0.05,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            volatility=0.0,
            win_rate=1.0,
            daily_returns=daily_returns,
            calmar_ratio=0.0,
        )

        assert result.information_ratio == 0.0  # 标准差为0时设为0
        assert result.downside_deviation == 0.0  # 无负收益

    def test_simulation_result_post_init_only_negative_returns(self):
        """测试只有负收益情况"""
        daily_returns = [-0.01, -0.005, -0.02, -0.008, -0.015]

        result = SimulationResult(
            strategy_id="sim_008",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 5),
            initial_capital=100000.0,
            final_capital=95000.0,
            total_return=-0.05,
            annual_return=-0.05,
            sharpe_ratio=-1.0,
            max_drawdown=0.05,
            volatility=0.02,
            win_rate=0.0,
            daily_returns=daily_returns,
            calmar_ratio=-1.0,
        )

        assert result.information_ratio is not None
        assert result.downside_deviation > 0.0  # 所有收益都是负的

    def test_simulation_result_post_init_only_positive_returns(self):
        """测试只有正收益情况"""
        daily_returns = [0.01, 0.005, 0.02, 0.008, 0.015]

        result = SimulationResult(
            strategy_id="sim_009",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 5),
            initial_capital=100000.0,
            final_capital=105000.0,
            total_return=0.05,
            annual_return=0.05,
            sharpe_ratio=2.0,
            max_drawdown=0.0,
            volatility=0.02,
            win_rate=1.0,
            daily_returns=daily_returns,
            calmar_ratio=10.0,
        )

        assert result.information_ratio > 0.0
        assert result.downside_deviation == 0.0  # 无负收益


class TestTickData:
    """测试Tick数据模型"""

    def test_tick_data_creation_minimal(self):
        """测试Tick数据最小参数创建"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        tick = TickData(symbol="000001.SZ", timestamp=timestamp, price=10.50, volume=1000)

        assert tick.symbol == "000001.SZ"
        assert tick.timestamp == timestamp
        assert tick.price == 10.50
        assert tick.volume == 1000
        assert tick.bid is None
        assert tick.ask is None
        assert tick.bid_size is None
        assert tick.ask_size is None

    def test_tick_data_creation_full(self):
        """测试Tick数据完整参数创建"""
        timestamp = datetime(2026, 2, 1, 9, 30, 15)

        tick = TickData(
            symbol="000002.SZ",
            timestamp=timestamp,
            price=25.80,
            volume=2500,
            bid=25.79,
            ask=25.81,
            bid_size=1500,
            ask_size=2000,
        )

        assert tick.symbol == "000002.SZ"
        assert tick.timestamp == timestamp
        assert tick.price == 25.80
        assert tick.volume == 2500
        assert tick.bid == 25.79
        assert tick.ask == 25.81
        assert tick.bid_size == 1500
        assert tick.ask_size == 2000

    def test_tick_data_edge_cases(self):
        """测试Tick数据边界情况"""
        # 测试零价格和零成交量
        tick_zero = TickData(symbol="TEST.SH", timestamp=datetime(2026, 2, 1, 9, 30, 0), price=0.0, volume=0)

        assert tick_zero.price == 0.0
        assert tick_zero.volume == 0

        # 测试极大值
        tick_large = TickData(
            symbol="LARGE.SH",
            timestamp=datetime(2026, 2, 1, 9, 30, 0),
            price=999999.99,
            volume=999999999,
            bid=999999.98,
            ask=1000000.00,
            bid_size=999999999,
            ask_size=999999999,
        )

        assert tick_large.price == 999999.99
        assert tick_large.volume == 999999999

    def test_tick_data_dataclass_features(self):
        """测试Tick数据类特性"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        tick1 = TickData(symbol="TEST.SZ", timestamp=timestamp, price=10.00, volume=1000)

        tick2 = TickData(symbol="TEST.SZ", timestamp=timestamp, price=10.00, volume=1000)

        # 测试相等性
        assert tick1 == tick2

        # 测试字符串表示
        str_repr = str(tick1)
        assert "TEST.SZ" in str_repr
        assert "10.0" in str_repr


class TestOrderData:
    """测试订单数据模型"""

    def test_order_data_creation_minimal(self):
        """测试订单数据最小参数创建"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        order = OrderData(
            order_id="ORD_001",
            symbol="000001.SZ",
            side="buy",
            quantity=1000,
            price=10.50,
            order_type="limit",
            timestamp=timestamp,
        )

        assert order.order_id == "ORD_001"
        assert order.symbol == "000001.SZ"
        assert order.side == "buy"
        assert order.quantity == 1000
        assert order.price == 10.50
        assert order.order_type == "limit"
        assert order.timestamp == timestamp
        assert order.status == "pending"  # 默认值

    def test_order_data_creation_full(self):
        """测试订单数据完整参数创建"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        order = OrderData(
            order_id="ORD_002",
            symbol="000002.SZ",
            side="sell",
            quantity=2000,
            price=25.80,
            order_type="market",
            timestamp=timestamp,
            status="filled",
        )

        assert order.order_id == "ORD_002"
        assert order.symbol == "000002.SZ"
        assert order.side == "sell"
        assert order.quantity == 2000
        assert order.price == 25.80
        assert order.order_type == "market"
        assert order.timestamp == timestamp
        assert order.status == "filled"

    def test_order_data_side_values(self):
        """测试订单方向值"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        # 测试买单
        buy_order = OrderData(
            order_id="BUY_001",
            symbol="TEST.SZ",
            side="buy",
            quantity=1000,
            price=10.00,
            order_type="limit",
            timestamp=timestamp,
        )
        assert buy_order.side == "buy"

        # 测试卖单
        sell_order = OrderData(
            order_id="SELL_001",
            symbol="TEST.SZ",
            side="sell",
            quantity=1000,
            price=10.00,
            order_type="limit",
            timestamp=timestamp,
        )
        assert sell_order.side == "sell"

    def test_order_data_order_types(self):
        """测试订单类型"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        order_types = ["market", "limit", "stop", "stop_limit", "trailing_stop"]

        for order_type in order_types:
            order = OrderData(
                order_id=f"ORD_{order_type}",
                symbol="TEST.SZ",
                side="buy",
                quantity=1000,
                price=10.00,
                order_type=order_type,
                timestamp=timestamp,
            )
            assert order.order_type == order_type

    def test_order_data_status_values(self):
        """测试订单状态值"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        statuses = ["pending", "filled", "partially_filled", "cancelled", "rejected"]

        for status in statuses:
            order = OrderData(
                order_id=f"ORD_{status}",
                symbol="TEST.SZ",
                side="buy",
                quantity=1000,
                price=10.00,
                order_type="limit",
                timestamp=timestamp,
                status=status,
            )
            assert order.status == status

    def test_order_data_edge_cases(self):
        """测试订单数据边界情况"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        # 测试零数量（可能的撤单情况）
        zero_order = OrderData(
            order_id="ZERO_001",
            symbol="TEST.SZ",
            side="buy",
            quantity=0,
            price=10.00,
            order_type="limit",
            timestamp=timestamp,
        )
        assert zero_order.quantity == 0

        # 测试零价格（市价单可能情况）
        zero_price_order = OrderData(
            order_id="MARKET_001",
            symbol="TEST.SZ",
            side="buy",
            quantity=1000,
            price=0.0,
            order_type="market",
            timestamp=timestamp,
        )
        assert zero_price_order.price == 0.0


class TestBarData:
    """测试K线数据模型"""

    def test_bar_data_creation_minimal(self):
        """测试K线数据最小参数创建"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        bar_data = BarData(
            symbol="000001.SZ", timestamp=timestamp, open=10.00, high=10.50, low=9.80, close=10.20, volume=1000000
        )

        assert bar_data.symbol == "000001.SZ"
        assert bar_data.timestamp == timestamp
        assert bar_data.open == 10.00
        assert bar_data.high == 10.50
        assert bar_data.low == 9.80
        assert bar_data.close == 10.20
        assert bar_data.volume == 1000000
        assert bar_data.interval == "1d"  # 默认值

    def test_bar_data_creation_full(self):
        """测试K线数据完整参数创建"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        bar_data = BarData(
            symbol="000002.SZ",
            timestamp=timestamp,
            open=25.00,
            high=25.80,
            low=24.50,
            close=25.60,
            volume=2500000,
            interval="5m",
        )

        assert bar_data.symbol == "000002.SZ"
        assert bar_data.timestamp == timestamp
        assert bar_data.open == 25.00
        assert bar_data.high == 25.80
        assert bar_data.low == 24.50
        assert bar_data.close == 25.60
        assert bar_data.volume == 2500000
        assert bar_data.interval == "5m"

    def test_bar_data_intervals(self):
        """测试K线时间间隔"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)
        intervals = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]

        for interval in intervals:
            bar_data = BarData(
                symbol="TEST.SZ",
                timestamp=timestamp,
                open=10.00,
                high=10.50,
                low=9.80,
                close=10.20,
                volume=1000000,
                interval=interval,
            )
            assert bar_data.interval == interval

    def test_bar_data_price_relationships(self):
        """测试K线价格关系"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        # 正常情况：low <= open,close <= high
        normal_bar = BarData(
            symbol="NORMAL.SZ", timestamp=timestamp, open=10.00, high=10.50, low=9.80, close=10.20, volume=1000000
        )

        assert normal_bar.low <= normal_bar.open <= normal_bar.high
        assert normal_bar.low <= normal_bar.close <= normal_bar.high

        # 涨停情况：open = high = close
        limit_up_bar = BarData(
            symbol="LIMIT_UP.SZ", timestamp=timestamp, open=10.00, high=11.00, low=10.00, close=11.00, volume=5000000
        )

        assert limit_up_bar.open == limit_up_bar.low
        assert limit_up_bar.high == limit_up_bar.close

        # 跌停情况：open = low = close
        limit_down_bar = BarData(
            symbol="LIMIT_DOWN.SZ", timestamp=timestamp, open=10.00, high=10.00, low=9.00, close=9.00, volume=8000000
        )

        assert limit_down_bar.open == limit_down_bar.high
        assert limit_down_bar.low == limit_down_bar.close

    def test_bar_data_edge_cases(self):
        """测试K线数据边界情况"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        # 测试零成交量
        zero_volume_bar = BarData(
            symbol="ZERO_VOL.SZ", timestamp=timestamp, open=10.00, high=10.00, low=10.00, close=10.00, volume=0
        )
        assert zero_volume_bar.volume == 0

        # 测试一字板（开高低收相等）
        flat_bar = BarData(
            symbol="FLAT.SZ", timestamp=timestamp, open=10.00, high=10.00, low=10.00, close=10.00, volume=1000000
        )

        assert flat_bar.open == flat_bar.high == flat_bar.low == flat_bar.close

    def test_bar_data_dataclass_features(self):
        """测试K线数据类特性"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        bar1 = BarData(
            symbol="TEST.SZ", timestamp=timestamp, open=10.00, high=10.50, low=9.80, close=10.20, volume=1000000
        )

        bar2 = BarData(
            symbol="TEST.SZ",
            timestamp=timestamp,
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.20,
            volume=1000000,
            interval="1d",
        )

        # 测试相等性
        assert bar1 == bar2

        # 测试字符串表示
        str_repr = str(bar1)
        assert "TEST.SZ" in str_repr
        assert "10.0" in str_repr


class TestModelsIntegration:
    """测试模型集成场景"""

    def test_strategy_with_simulation_result(self):
        """测试策略与模拟结果的集成"""
        # 创建策略
        strategy = Strategy(
            strategy_id="integration_001",
            name="集成测试策略",
            type="momentum",
            description="用于集成测试的策略",
            parameters={"lookback": 20, "threshold": 0.02},
        )

        # 创建对应的模拟结果
        daily_returns = [0.01, -0.005, 0.02, 0.0, -0.01]
        result = SimulationResult(
            strategy_id=strategy.strategy_id,  # 使用相同的strategy_id
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 12, 31),
            initial_capital=100000.0,
            final_capital=110000.0,
            total_return=0.10,
            annual_return=0.10,
            sharpe_ratio=1.5,
            max_drawdown=0.05,
            volatility=0.15,
            win_rate=0.60,
            daily_returns=daily_returns,
            calmar_ratio=2.0,
        )

        # 验证关联
        assert strategy.strategy_id == result.strategy_id
        assert result.information_ratio is not None
        assert result.downside_deviation is not None

    def test_trading_workflow_models(self):
        """测试交易工作流模型"""
        timestamp = datetime(2026, 2, 1, 9, 30, 0)

        # 创建Tick数据
        tick = TickData(
            symbol="000001.SZ",
            timestamp=timestamp,
            price=10.50,
            volume=1000,
            bid=10.49,
            ask=10.51,
            bid_size=5000,
            ask_size=3000,
        )

        # 基于Tick数据创建订单
        order = OrderData(
            order_id="ORD_TICK_001",
            symbol=tick.symbol,
            side="buy",
            quantity=1000,
            price=tick.ask,  # 使用ask价格买入
            order_type="limit",
            timestamp=tick.timestamp,
        )

        # 创建对应的K线数据
        bar_data = BarData(
            symbol=tick.symbol,
            timestamp=timestamp,
            open=10.45,
            high=10.55,
            low=10.40,
            close=tick.price,  # 收盘价使用tick价格
            volume=1000000,
            interval="1m",
        )

        # 验证数据一致性
        assert tick.symbol == order.symbol == bar_data.symbol
        assert tick.timestamp == order.timestamp == bar_data.timestamp
        assert bar_data.low <= tick.price <= bar_data.high
        assert order.price == tick.ask

    def test_models_with_extreme_values(self):
        """测试模型极值情况"""
        # 测试极大的时间戳
        far_future = datetime(2099, 12, 31, 23, 59, 59)

        strategy = Strategy(
            strategy_id="extreme_001",
            name="极值测试策略",
            type="test",
            description="测试极值情况",
            created_at=far_future,
            updated_at=far_future,
        )

        assert strategy.created_at == far_future
        assert strategy.updated_at == far_future

        # 测试极大的价格和成交量
        extreme_tick = TickData(symbol="EXTREME.SZ", timestamp=far_future, price=999999.99, volume=999999999)

        assert extreme_tick.price == 999999.99
        assert extreme_tick.volume == 999999999

    def test_models_serialization_compatibility(self):
        """测试模型序列化兼容性"""
        import json  # pylint: disable=import-outside-toplevel
        from dataclasses import asdict  # pylint: disable=import-outside-toplevel

        # 测试Strategy序列化
        strategy = Strategy(
            strategy_id="serial_001",
            name="序列化测试",
            type="test",
            description="测试序列化",
            parameters={"test": "value"},
        )

        # 转换为字典
        strategy_dict = asdict(strategy)
        assert isinstance(strategy_dict, dict)
        assert strategy_dict["strategy_id"] == "serial_001"

        # 测试JSON序列化（需要处理datetime）
        strategy_dict["created_at"] = strategy_dict["created_at"].isoformat()
        strategy_dict["updated_at"] = strategy_dict["updated_at"].isoformat()

        json_str = json.dumps(strategy_dict)
        assert isinstance(json_str, str)
        assert "serial_001" in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
