"""
行情数据订阅器单元测试

白皮书依据: 第一章 1.5.2 战争态任务调度
测试范围: MarketDataSubscriber的行情订阅和数据处理功能
"""

import pytest
import time
import threading
from datetime import datetime
from unittest.mock import patch, MagicMock, call

from src.execution.market_data import (
    MarketDataSubscriber,
    DataSource,
    SubscriptionStatus,
    TickData,
    BarData
)


class TestTickData:
    """TickData数据类测试"""
    
    def test_tick_data_creation(self):
        """测试Tick数据创建"""
        tick = TickData(
            symbol="000001.SZ",
            price=10.50,
            volume=1000,
            amount=10500.0,
            bid_price=10.49,
            ask_price=10.51,
            bid_volume=500,
            ask_volume=600
        )
        
        assert tick.symbol == "000001.SZ"
        assert tick.price == 10.50
        assert tick.volume == 1000
        assert tick.amount == 10500.0
        assert tick.bid_price == 10.49
        assert tick.ask_price == 10.51
        assert tick.bid_volume == 500
        assert tick.ask_volume == 600
        assert isinstance(tick.timestamp, datetime)
    
    def test_tick_data_defaults(self):
        """测试Tick数据默认值"""
        tick = TickData(symbol="000001.SZ", price=10.0)
        
        assert tick.volume == 0
        assert tick.amount == 0.0
        assert tick.bid_price == 0.0
        assert tick.ask_price == 0.0
    
    def test_tick_data_to_dict(self):
        """测试Tick数据转字典"""
        tick = TickData(
            symbol="000001.SZ",
            price=10.50,
            volume=1000
        )
        
        result = tick.to_dict()
        
        assert result["symbol"] == "000001.SZ"
        assert result["price"] == 10.50
        assert result["volume"] == 1000
        assert "timestamp" in result


class TestBarData:
    """BarData数据类测试"""
    
    def test_bar_data_creation(self):
        """测试Bar数据创建"""
        bar = BarData(
            symbol="000001.SZ",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.3,
            volume=10000,
            amount=103000.0
        )
        
        assert bar.symbol == "000001.SZ"
        assert bar.open == 10.0
        assert bar.high == 10.5
        assert bar.low == 9.8
        assert bar.close == 10.3
        assert bar.volume == 10000
        assert bar.amount == 103000.0
    
    def test_bar_data_to_dict(self):
        """测试Bar数据转字典"""
        bar = BarData(
            symbol="000001.SZ",
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.3
        )
        
        result = bar.to_dict()
        
        assert result["symbol"] == "000001.SZ"
        assert result["open"] == 10.0
        assert result["high"] == 10.5
        assert result["low"] == 9.8
        assert result["close"] == 10.3


class TestDataSource:
    """DataSource枚举测试"""
    
    def test_data_source_values(self):
        """测试数据源枚举值"""
        assert DataSource.QMT.value == "QMT"
        assert DataSource.SIMULATION.value == "模拟"
        assert DataSource.REPLAY.value == "回放"


class TestSubscriptionStatus:
    """SubscriptionStatus枚举测试"""
    
    def test_subscription_status_values(self):
        """测试订阅状态枚举值"""
        assert SubscriptionStatus.DISCONNECTED.value == "未连接"
        assert SubscriptionStatus.CONNECTING.value == "连接中"
        assert SubscriptionStatus.CONNECTED.value == "已连接"
        assert SubscriptionStatus.SUBSCRIBED.value == "已订阅"
        assert SubscriptionStatus.ERROR.value == "错误"


class TestMarketDataSubscriber:
    """MarketDataSubscriber订阅器测试"""
    
    @pytest.fixture
    def subscriber(self):
        """创建订阅器实例"""
        sub = MarketDataSubscriber(data_source=DataSource.SIMULATION)
        yield sub
        # 清理
        sub.disconnect()
    
    def test_init_default(self):
        """测试默认初始化"""
        subscriber = MarketDataSubscriber()
        
        assert subscriber.data_source == DataSource.SIMULATION
        assert subscriber.status == SubscriptionStatus.DISCONNECTED
        assert len(subscriber.subscribed_symbols) == 0
        
        subscriber.disconnect()
    
    def test_init_with_qmt(self):
        """测试QMT数据源初始化"""
        subscriber = MarketDataSubscriber(data_source=DataSource.QMT)
        
        assert subscriber.data_source == DataSource.QMT
        
        subscriber.disconnect()
    
    def test_init_with_buffer_size(self):
        """测试自定义缓冲区大小"""
        subscriber = MarketDataSubscriber(buffer_size=5000)
        
        assert subscriber.buffer_size == 5000
        
        subscriber.disconnect()
    
    def test_connect_simulation(self, subscriber):
        """测试连接模拟数据源"""
        result = subscriber.connect()
        
        assert result is True
        assert subscriber.status == SubscriptionStatus.CONNECTED
    
    def test_connect_already_connected(self, subscriber):
        """测试重复连接"""
        subscriber.connect()
        result = subscriber.connect()
        
        assert result is True
        assert subscriber.status == SubscriptionStatus.CONNECTED
    
    def test_disconnect(self, subscriber):
        """测试断开连接"""
        subscriber.connect()
        result = subscriber.disconnect()
        
        assert result is True
        assert subscriber.status == SubscriptionStatus.DISCONNECTED
    
    def test_subscribe_without_connect(self, subscriber):
        """测试未连接时订阅"""
        result = subscriber.subscribe(["000001.SZ"])
        
        assert result is False
    
    def test_subscribe_single_symbol(self, subscriber):
        """测试订阅单个标的"""
        subscriber.connect()
        result = subscriber.subscribe(["000001.SZ"])
        
        assert result is True
        assert "000001.SZ" in subscriber.subscribed_symbols
        assert subscriber.status == SubscriptionStatus.SUBSCRIBED
    
    def test_subscribe_multiple_symbols(self, subscriber):
        """测试订阅多个标的"""
        subscriber.connect()
        symbols = ["000001.SZ", "600000.SH", "000002.SZ"]
        result = subscriber.subscribe(symbols)
        
        assert result is True
        assert len(subscriber.subscribed_symbols) == 3
        for symbol in symbols:
            assert symbol in subscriber.subscribed_symbols
    
    def test_subscribe_duplicate_symbol(self, subscriber):
        """测试重复订阅"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        subscriber.subscribe(["000001.SZ", "600000.SH"])
        
        # 不应该有重复
        assert len(subscriber.subscribed_symbols) == 2
    
    def test_unsubscribe(self, subscriber):
        """测试取消订阅"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ", "600000.SH"])
        
        result = subscriber.unsubscribe(["000001.SZ"])
        
        assert result is True
        assert "000001.SZ" not in subscriber.subscribed_symbols
        assert "600000.SH" in subscriber.subscribed_symbols
    
    def test_unsubscribe_all(self, subscriber):
        """测试取消所有订阅"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ", "600000.SH"])
        
        result = subscriber.unsubscribe_all()
        
        assert result is True
        assert len(subscriber.subscribed_symbols) == 0
        assert subscriber.status == SubscriptionStatus.CONNECTED
    
    def test_is_connected(self, subscriber):
        """测试连接状态检查"""
        assert subscriber.is_connected() is False
        
        subscriber.connect()
        assert subscriber.is_connected() is True
        
        subscriber.disconnect()
        assert subscriber.is_connected() is False
    
    def test_is_subscribed(self, subscriber):
        """测试订阅状态检查"""
        assert subscriber.is_subscribed() is False
        
        subscriber.connect()
        assert subscriber.is_subscribed() is False
        
        subscriber.subscribe(["000001.SZ"])
        assert subscriber.is_subscribed() is True
    
    def test_get_statistics(self, subscriber):
        """测试获取统计信息"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        
        stats = subscriber.get_statistics()
        
        assert stats["status"] == "已订阅"
        assert stats["data_source"] == "模拟"
        assert stats["subscribed_count"] == 1
    
    def test_on_tick_callback(self, subscriber):
        """测试Tick回调"""
        received_ticks = []
        
        def on_tick(tick):
            received_ticks.append(tick)
        
        subscriber.on_tick = on_tick
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        
        # 等待一些数据
        time.sleep(0.3)
        
        assert len(received_ticks) > 0
        assert all(isinstance(t, TickData) for t in received_ticks)
    
    def test_on_status_change_callback(self, subscriber):
        """测试状态变化回调"""
        status_changes = []
        
        def on_status_change(status):
            status_changes.append(status)
        
        subscriber.on_status_change = on_status_change
        subscriber.connect()
        
        assert SubscriptionStatus.CONNECTING in status_changes
        assert SubscriptionStatus.CONNECTED in status_changes
    
    def test_get_latest_tick(self, subscriber):
        """测试获取最新Tick"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        
        # 等待数据
        time.sleep(0.3)
        
        tick = subscriber.get_latest_tick("000001.SZ")
        
        assert tick is not None
        assert tick.symbol == "000001.SZ"
    
    def test_get_latest_tick_not_subscribed(self, subscriber):
        """测试获取未订阅标的的Tick"""
        subscriber.connect()
        
        tick = subscriber.get_latest_tick("000001.SZ")
        
        assert tick is None
    
    def test_get_tick_history(self, subscriber):
        """测试获取Tick历史"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        
        # 等待数据
        time.sleep(0.5)
        
        history = subscriber.get_tick_history("000001.SZ", count=5)
        
        assert len(history) > 0
        assert len(history) <= 5
    
    def test_get_tick_history_not_subscribed(self, subscriber):
        """测试获取未订阅标的的历史"""
        subscriber.connect()
        
        history = subscriber.get_tick_history("000001.SZ")
        
        assert history == []


class TestMarketDataSubscriberThreadSafety:
    """线程安全测试"""
    
    @pytest.fixture
    def subscriber(self):
        """创建订阅器实例"""
        sub = MarketDataSubscriber(data_source=DataSource.SIMULATION)
        yield sub
        sub.disconnect()
    
    def test_concurrent_subscribe(self, subscriber):
        """测试并发订阅"""
        subscriber.connect()
        
        def subscribe_symbols(symbols):
            subscriber.subscribe(symbols)
        
        threads = [
            threading.Thread(target=subscribe_symbols, args=(["000001.SZ"],)),
            threading.Thread(target=subscribe_symbols, args=(["600000.SH"],)),
            threading.Thread(target=subscribe_symbols, args=(["000002.SZ"],))
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(subscriber.subscribed_symbols) == 3
    
    def test_concurrent_unsubscribe(self, subscriber):
        """测试并发取消订阅"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ", "600000.SH", "000002.SZ"])
        
        def unsubscribe_symbol(symbol):
            subscriber.unsubscribe([symbol])
        
        threads = [
            threading.Thread(target=unsubscribe_symbol, args=("000001.SZ",)),
            threading.Thread(target=unsubscribe_symbol, args=("600000.SH",))
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(subscriber.subscribed_symbols) == 1
        assert "000002.SZ" in subscriber.subscribed_symbols


class TestMarketDataSubscriberEdgeCases:
    """边界条件测试"""
    
    @pytest.fixture
    def subscriber(self):
        """创建订阅器实例"""
        sub = MarketDataSubscriber(data_source=DataSource.SIMULATION)
        yield sub
        sub.disconnect()
    
    def test_subscribe_empty_list(self, subscriber):
        """测试订阅空列表"""
        subscriber.connect()
        result = subscriber.subscribe([])
        
        assert result is True
        assert len(subscriber.subscribed_symbols) == 0
    
    def test_unsubscribe_nonexistent_symbol(self, subscriber):
        """测试取消订阅不存在的标的"""
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        
        result = subscriber.unsubscribe(["999999.SZ"])
        
        assert result is True
        assert "000001.SZ" in subscriber.subscribed_symbols
    
    def test_callback_exception_handling(self, subscriber):
        """测试回调异常处理"""
        def bad_callback(tick):
            raise ValueError("回调错误")
        
        subscriber.on_tick = bad_callback
        subscriber.connect()
        subscriber.subscribe(["000001.SZ"])
        
        # 等待一些数据，不应该崩溃
        time.sleep(0.3)
        
        # 订阅器应该仍然运行
        assert subscriber.is_subscribed()
    
    def test_rapid_connect_disconnect(self, subscriber):
        """测试快速连接断开"""
        for _ in range(5):
            subscriber.connect()
            subscriber.subscribe(["000001.SZ"])
            subscriber.disconnect()
        
        assert subscriber.status == SubscriptionStatus.DISCONNECTED
