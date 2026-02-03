"""IPC标准化协议单元测试

白皮书依据: 第三章 3.6 IPC标准化协议
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.infra.ipc_protocol import (
    TickData,
    BarData,
    OrderData,
    TradeData,
    PositionData,
    OrderSide,
    OrderType,
    OrderStatus,
    validate_ipc_data,
    serialize_ipc_data,
    deserialize_ipc_data
)


class TestTickData:
    """Tick数据测试"""
    
    def test_create_tick_data(self):
        """测试创建Tick数据"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.50,
            volume=1000000,
            turnover=10500000.0,
            bid_price_1=10.49,
            bid_volume_1=10000,
            ask_price_1=10.51,
            ask_volume_1=8000
        )
        
        assert tick.symbol == "000001.SZ"
        assert tick.last_price == 10.50
        assert tick.volume == 1000000
    
    def test_tick_symbol_validation(self):
        """测试标的代码验证"""
        # 有效代码
        tick = TickData(
            symbol="000001.sz",  # 小写会被转换为大写
            timestamp=datetime.now(),
            last_price=10.0,
            volume=1000
        )
        assert tick.symbol == "000001.SZ"
        
        # 无效代码
        with pytest.raises(ValidationError):
            TickData(
                symbol="001",  # 太短
                timestamp=datetime.now(),
                last_price=10.0,
                volume=1000
            )
    
    def test_tick_price_validation(self):
        """测试价格验证"""
        # 价格必须 > 0
        with pytest.raises(ValidationError):
            TickData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                last_price=0,  # 无效
                volume=1000
            )
        
        with pytest.raises(ValidationError):
            TickData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                last_price=-10.0,  # 无效
                volume=1000
            )
    
    def test_tick_price_consistency(self):
        """测试价格一致性"""
        # 正常情况
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.0,
            high_price=10.5,
            low_price=9.5,
            volume=1000
        )
        assert tick.high_price >= tick.low_price
        
        # 异常情况：high < low
        with pytest.raises(ValidationError):
            TickData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                last_price=10.0,
                high_price=9.0,
                low_price=10.0,
                volume=1000
            )
    
    def test_tick_get_mid_price(self):
        """测试获取中间价"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.0,
            volume=1000,
            bid_price_1=9.99,
            ask_price_1=10.01
        )
        
        mid_price = tick.get_mid_price()
        assert mid_price == 10.0
    
    def test_tick_get_spread(self):
        """测试获取买卖价差"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.0,
            volume=1000,
            bid_price_1=9.99,
            ask_price_1=10.01
        )
        
        spread = tick.get_spread()
        assert abs(spread - 0.02) < 0.0001  # 使用近似比较
    
    def test_tick_get_spread_bps(self):
        """测试获取买卖价差(基点)"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.0,
            volume=1000,
            bid_price_1=9.99,
            ask_price_1=10.01
        )
        
        spread_bps = tick.get_spread_bps()
        assert spread_bps is not None
        assert spread_bps > 0


class TestBarData:
    """K线数据测试"""
    
    def test_create_bar_data(self):
        """测试创建K线数据"""
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            interval="1m",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000000,
            turnover=10100000.0
        )
        
        assert bar.symbol == "000001.SZ"
        assert bar.interval == "1m"
        assert bar.open == 10.0
        assert bar.close == 10.2
    
    def test_bar_interval_validation(self):
        """测试K线周期验证"""
        # 有效周期
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '1d']
        for interval in valid_intervals:
            bar = BarData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                interval=interval,
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000
            )
            assert bar.interval == interval
        
        # 无效周期
        with pytest.raises(ValidationError):
            BarData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                interval="invalid",
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000
            )
    
    def test_bar_ohlc_validation(self):
        """测试OHLC一致性验证"""
        # 正常情况
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            interval="1m",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000
        )
        assert bar.high >= max(bar.open, bar.close)
        assert bar.low <= min(bar.open, bar.close)
        
        # 异常情况：high < close
        with pytest.raises(ValidationError):
            BarData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                interval="1m",
                open=10.0,
                high=10.0,
                low=9.8,
                close=10.5,  # close > high
                volume=1000
            )
        
        # 异常情况：low > open
        with pytest.raises(ValidationError):
            BarData(
                symbol="000001.SZ",
                timestamp=datetime.now(),
                interval="1m",
                open=10.0,
                high=10.5,
                low=10.2,  # low > open
                close=10.3,
                volume=1000
            )
    
    def test_bar_get_return(self):
        """测试获取收益率"""
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            interval="1m",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000
        )
        
        ret = bar.get_return()
        assert abs(ret - 0.02) < 0.0001  # 使用近似比较
    
    def test_bar_get_amplitude(self):
        """测试获取振幅"""
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            interval="1m",
            open=10.0,
            high=10.5,
            low=9.5,
            close=10.2,
            volume=1000
        )
        
        amplitude = bar.get_amplitude()
        assert amplitude == 0.1  # (10.5 - 9.5) / 10.0
    
    def test_bar_is_bullish(self):
        """测试是否阳线"""
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            interval="1m",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000
        )
        
        assert bar.is_bullish()
        assert not bar.is_bearish()


class TestOrderData:
    """订单数据测试"""
    
    def test_create_order_data(self):
        """测试创建订单数据"""
        order = OrderData(
            order_id="ORD001",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.50,
            quantity=1000
        )
        
        assert order.order_id == "ORD001"
        assert order.symbol == "000001.SZ"
        assert order.side == OrderSide.BUY
        assert order.quantity == 1000
    
    def test_order_filled_quantity_validation(self):
        """测试已成交数量验证"""
        # 正常情况
        order = OrderData(
            order_id="ORD002",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.0,
            quantity=1000,
            filled_quantity=500
        )
        assert order.filled_quantity == 500
        
        # 异常情况：filled > quantity
        with pytest.raises(ValidationError):
            OrderData(
                order_id="ORD003",
                symbol="000001.SZ",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=10.0,
                quantity=1000,
                filled_quantity=1500  # 超过委托数量
            )
    
    def test_order_get_average_price(self):
        """测试获取平均成交价"""
        order = OrderData(
            order_id="ORD004",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.0,
            quantity=1000,
            filled_quantity=500,
            filled_amount=5050.0
        )
        
        avg_price = order.get_average_price()
        assert avg_price == 10.1  # 5050 / 500
    
    def test_order_get_fill_ratio(self):
        """测试获取成交比例"""
        order = OrderData(
            order_id="ORD005",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.0,
            quantity=1000,
            filled_quantity=750
        )
        
        fill_ratio = order.get_fill_ratio()
        assert fill_ratio == 0.75
    
    def test_order_is_filled(self):
        """测试是否完全成交"""
        order = OrderData(
            order_id="ORD006",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.0,
            quantity=1000,
            filled_quantity=1000,
            status=OrderStatus.FILLED
        )
        
        assert order.is_filled()
    
    def test_order_is_active(self):
        """测试是否活跃订单"""
        order = OrderData(
            order_id="ORD007",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.0,
            quantity=1000,
            status=OrderStatus.SUBMITTED
        )
        
        assert order.is_active()
    
    def test_order_update_fill(self):
        """测试更新成交信息"""
        order = OrderData(
            order_id="ORD008",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=10.0,
            quantity=1000
        )
        
        # 部分成交
        order.update_fill(500, 5000.0)
        assert order.filled_quantity == 500
        assert order.status == OrderStatus.PARTIAL_FILLED
        
        # 完全成交
        order.update_fill(1000, 10000.0)
        assert order.filled_quantity == 1000
        assert order.status == OrderStatus.FILLED


class TestTradeData:
    """成交数据测试"""
    
    def test_create_trade_data(self):
        """测试创建成交数据"""
        trade = TradeData(
            trade_id="TRD001",
            order_id="ORD001",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            price=10.50,
            quantity=1000,
            amount=10500.0,
            commission=10.5,
            tax=0.0
        )
        
        assert trade.trade_id == "TRD001"
        assert trade.order_id == "ORD001"
        assert trade.price == 10.50
        assert trade.quantity == 1000
    
    def test_trade_get_net_amount(self):
        """测试获取净成交金额"""
        # 买入
        trade_buy = TradeData(
            trade_id="TRD002",
            order_id="ORD002",
            symbol="000001.SZ",
            side=OrderSide.BUY,
            price=10.0,
            quantity=1000,
            amount=10000.0,
            commission=10.0,
            tax=0.0
        )
        
        net_amount_buy = trade_buy.get_net_amount()
        assert net_amount_buy == 10010.0  # 10000 + 10 + 0
        
        # 卖出
        trade_sell = TradeData(
            trade_id="TRD003",
            order_id="ORD003",
            symbol="000001.SZ",
            side=OrderSide.SELL,
            price=10.0,
            quantity=1000,
            amount=10000.0,
            commission=10.0,
            tax=10.0
        )
        
        net_amount_sell = trade_sell.get_net_amount()
        assert net_amount_sell == 9980.0  # 10000 - 10 - 10


class TestPositionData:
    """持仓数据测试"""
    
    def test_create_position_data(self):
        """测试创建持仓数据"""
        position = PositionData(
            symbol="000001.SZ",
            quantity=1000,
            available_quantity=1000,
            avg_price=10.0,
            total_cost=10000.0,
            last_price=10.5,
            market_value=10500.0,
            pnl=500.0,
            pnl_ratio=0.05
        )
        
        assert position.symbol == "000001.SZ"
        assert position.quantity == 1000
        assert position.pnl == 500.0
    
    def test_position_available_quantity_validation(self):
        """测试可用数量验证"""
        # 正常情况
        position = PositionData(
            symbol="000001.SZ",
            quantity=1000,
            available_quantity=800,
            avg_price=10.0,
            total_cost=10000.0,
            last_price=10.5,
            market_value=10500.0,
            pnl=500.0,
            pnl_ratio=0.05
        )
        assert position.available_quantity == 800
        
        # 异常情况：available > quantity
        with pytest.raises(ValidationError):
            PositionData(
                symbol="000001.SZ",
                quantity=1000,
                available_quantity=1200,  # 超过总数量
                avg_price=10.0,
                total_cost=10000.0,
                last_price=10.5,
                market_value=10500.0,
                pnl=500.0,
                pnl_ratio=0.05
            )
    
    def test_position_calculate_derived_fields(self):
        """测试计算派生字段"""
        position = PositionData(
            symbol="000001.SZ",
            quantity=1000,
            available_quantity=1000,
            avg_price=10.0,
            last_price=10.5
        )
        
        # 自动计算的字段
        assert position.total_cost == 10000.0  # 1000 * 10.0
        assert position.market_value == 10500.0  # 1000 * 10.5
        assert position.pnl == 500.0  # 10500 - 10000
        assert position.pnl_ratio == 0.05  # 500 / 10000
    
    def test_position_update_price(self):
        """测试更新价格"""
        position = PositionData(
            symbol="000001.SZ",
            quantity=1000,
            available_quantity=1000,
            avg_price=10.0,
            last_price=10.0
        )
        
        # 更新价格
        position.update_price(11.0)
        
        assert position.last_price == 11.0
        assert position.market_value == 11000.0
        assert position.pnl == 1000.0
        assert position.pnl_ratio == 0.1


class TestIPCUtilities:
    """IPC工具函数测试"""
    
    def test_validate_ipc_data(self):
        """测试验证IPC数据"""
        # 有效数据
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.0,
            volume=1000
        )
        assert validate_ipc_data(tick)
        
        # 无效数据会在创建时抛出异常
        with pytest.raises(ValidationError):
            TickData(
                symbol="001",  # 无效
                timestamp=datetime.now(),
                last_price=10.0,
                volume=1000
            )
    
    def test_serialize_deserialize_ipc_data(self):
        """测试序列化和反序列化"""
        # 创建数据
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            last_price=10.50,
            volume=1000000,
            bid_price_1=10.49,
            ask_price_1=10.51
        )
        
        # 序列化
        data_bytes = serialize_ipc_data(tick)
        assert isinstance(data_bytes, bytes)
        assert len(data_bytes) > 0
        
        # 反序列化
        tick_restored = deserialize_ipc_data(data_bytes, TickData)
        assert tick_restored.symbol == tick.symbol
        assert tick_restored.last_price == tick.last_price
        assert tick_restored.volume == tick.volume


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
