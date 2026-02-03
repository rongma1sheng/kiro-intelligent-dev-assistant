"""BarSynthesizer单元测试

白皮书依据: 第三章 3.3 Bar Synthesizer

测试覆盖:
- Tick到Bar转换
- OHLCV计算正确性
- 多周期并发合成
- 时间窗口边界
- Bar质量验证
- 异常处理

Author: MIA Team
Date: 2026-01-22
"""

import pytest
from datetime import datetime, timedelta
from src.infra.bar_synthesizer import (
    BarSynthesizer,
    Tick,
    Bar,
    BarBuffer,
    get_bar_synthesizer
)


class TestBarSynthesizerInitialization:
    """测试BarSynthesizer初始化"""
    
    def test_initialization_default_periods(self):
        """测试默认周期初始化"""
        synthesizer = BarSynthesizer()
        
        assert len(synthesizer.supported_periods) == 6
        assert '1m' in synthesizer.supported_periods
        assert '5m' in synthesizer.supported_periods
        assert '15m' in synthesizer.supported_periods
        assert '30m' in synthesizer.supported_periods
        assert '1h' in synthesizer.supported_periods
        assert '1d' in synthesizer.supported_periods
    
    def test_initialization_custom_periods(self):
        """测试自定义周期初始化"""
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        assert len(synthesizer.supported_periods) == 2
        assert '1m' in synthesizer.supported_periods
        assert '5m' in synthesizer.supported_periods
    
    def test_initialization_invalid_period(self):
        """测试无效周期"""
        with pytest.raises(ValueError, match="不支持的周期"):
            BarSynthesizer(periods=['1m', '10m'])  # 10m不支持
    
    def test_empty_buffers_on_init(self):
        """测试初始化时缓冲区为空"""
        synthesizer = BarSynthesizer()
        
        assert len(synthesizer.buffers) == 0
        assert len(synthesizer.completed_bars) == 0


class TestTickProcessing:
    """测试Tick处理"""
    
    def test_process_single_tick(self):
        """测试处理单个Tick"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        
        completed_bars = synthesizer.process_tick(tick)
        
        # 第一个Tick不会完成Bar
        assert len(completed_bars) == 0
        
        # 检查缓冲区
        buffer_key = ('000001.SZ', '1m')
        assert buffer_key in synthesizer.buffers
        
        buffer = synthesizer.buffers[buffer_key]
        assert buffer.open == 10.0
        assert buffer.high == 10.0
        assert buffer.low == 10.0
        assert buffer.close == 10.0
        assert buffer.volume == 100
        assert buffer.tick_count == 1
    
    def test_process_multiple_ticks_same_period(self):
        """测试同一周期内处理多个Tick"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 第一个Tick
        tick1 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick1)
        
        # 第二个Tick（同一分钟）
        tick2 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 30),
            price=10.5,
            volume=200,
            amount=2100.0
        )
        synthesizer.process_tick(tick2)
        
        # 第三个Tick（同一分钟）
        tick3 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 50),
            price=9.8,
            volume=150,
            amount=1470.0
        )
        completed_bars = synthesizer.process_tick(tick3)
        
        # 仍在同一周期，不应完成Bar
        assert len(completed_bars) == 0
        
        # 检查缓冲区OHLCV
        buffer = synthesizer.buffers[('000001.SZ', '1m')]
        assert buffer.open == 10.0  # 第一个Tick的价格
        assert buffer.high == 10.5  # 最高价
        assert buffer.low == 9.8    # 最低价
        assert buffer.close == 9.8  # 最后一个Tick的价格
        assert buffer.volume == 450  # 100 + 200 + 150
        assert buffer.amount == 4570.0  # 1000 + 2100 + 1470
        assert buffer.tick_count == 3
    
    def test_process_tick_period_boundary(self):
        """测试周期边界处理"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 第一个周期的Tick
        tick1 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 30),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick1)
        
        # 下一个周期的Tick（应该完成上一个Bar）
        tick2 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 31, 0),
            price=10.5,
            volume=200,
            amount=2100.0
        )
        completed_bars = synthesizer.process_tick(tick2)
        
        # 应该完成一个Bar
        assert len(completed_bars) == 1
        
        bar = completed_bars[0]
        assert bar.symbol == '000001.SZ'
        assert bar.period == '1m'
        assert bar.timestamp == datetime(2024, 1, 1, 9, 30, 0)
        assert bar.open == 10.0
        assert bar.close == 10.0
        assert bar.volume == 100
        assert bar.tick_count == 1
    
    def test_process_tick_invalid_price(self):
        """测试无效价格"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=-10.0,  # 无效价格
            volume=100,
            amount=1000.0
        )
        
        with pytest.raises(ValueError, match="无效的价格"):
            synthesizer.process_tick(tick)
    
    def test_process_tick_invalid_volume(self):
        """测试无效成交量"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=-100,  # 无效成交量
            amount=1000.0
        )
        
        with pytest.raises(ValueError, match="无效的成交量"):
            synthesizer.process_tick(tick)


class TestMultiPeriodSynthesis:
    """测试多周期并发合成"""
    
    def test_multi_period_synthesis(self):
        """测试多周期并发合成"""
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        # 生成5分钟的Tick数据
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        for minute in range(6):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(minutes=minute),
                price=10.0 + minute * 0.1,
                volume=100,
                amount=1000.0
            )
            completed_bars = synthesizer.process_tick(tick)
            
            if minute == 5:
                # 第6分钟应该完成1m和5m的Bar
                assert len(completed_bars) == 2
                
                # 检查周期
                periods = {bar.period for bar in completed_bars}
                assert '1m' in periods
                assert '5m' in periods
    
    def test_multi_symbol_synthesis(self):
        """测试多标的并发合成"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 两个不同标的的Tick
        tick1 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        
        tick2 = Tick(
            symbol='600000.SH',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=20.0,
            volume=200,
            amount=4000.0
        )
        
        synthesizer.process_tick(tick1)
        synthesizer.process_tick(tick2)
        
        # 应该有两个缓冲区
        assert len(synthesizer.buffers) == 2
        assert ('000001.SZ', '1m') in synthesizer.buffers
        assert ('600000.SH', '1m') in synthesizer.buffers


class TestOHLCVCalculation:
    """测试OHLCV计算正确性"""
    
    def test_ohlcv_calculation(self):
        """测试OHLCV计算"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 模拟一分钟内的价格波动
        prices = [10.0, 10.5, 10.3, 9.8, 10.2]
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        for i, price in enumerate(prices):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(seconds=i*10),
                price=price,
                volume=100,
                amount=price * 100
            )
            synthesizer.process_tick(tick)
        
        # 触发Bar完成
        tick_next = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 31, 0),
            price=10.1,
            volume=100,
            amount=1010.0
        )
        completed_bars = synthesizer.process_tick(tick_next)
        
        assert len(completed_bars) == 1
        bar = completed_bars[0]
        
        # 验证OHLCV
        assert bar.open == 10.0  # 第一个价格
        assert bar.high == 10.5  # 最高价
        assert bar.low == 9.8    # 最低价
        assert bar.close == 10.2  # 最后一个价格
        assert bar.volume == 500  # 5个Tick，每个100
    
    def test_single_tick_bar(self):
        """测试单个Tick形成的Bar"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        tick1 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick1)
        
        # 下一周期
        tick2 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 31, 0),
            price=10.5,
            volume=200,
            amount=2100.0
        )
        completed_bars = synthesizer.process_tick(tick2)
        
        bar = completed_bars[0]
        
        # 单个Tick的Bar，OHLC应该相同
        assert bar.open == 10.0
        assert bar.high == 10.0
        assert bar.low == 10.0
        assert bar.close == 10.0


class TestTimeWindowAlignment:
    """测试时间窗口对齐"""
    
    def test_1m_period_alignment(self):
        """测试1分钟周期对齐"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 9:30:45的Tick应该属于9:30:00周期
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 45),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick)
        
        buffer = synthesizer.buffers[('000001.SZ', '1m')]
        assert buffer.start_time == datetime(2024, 1, 1, 9, 30, 0)
    
    def test_5m_period_alignment(self):
        """测试5分钟周期对齐"""
        synthesizer = BarSynthesizer(periods=['5m'])
        
        # 9:32:00的Tick应该属于9:30:00周期
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 32, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick)
        
        buffer = synthesizer.buffers[('000001.SZ', '5m')]
        assert buffer.start_time == datetime(2024, 1, 1, 9, 30, 0)
    
    def test_1d_period_alignment(self):
        """测试日线周期对齐"""
        synthesizer = BarSynthesizer(periods=['1d'])
        
        # 任何时间的Tick都应该属于当天00:00:00
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 14, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick)
        
        buffer = synthesizer.buffers[('000001.SZ', '1d')]
        assert buffer.start_time == datetime(2024, 1, 1, 0, 0, 0)


class TestBarValidation:
    """测试Bar质量验证"""
    
    def test_valid_bar(self):
        """测试有效的Bar"""
        bar = Bar(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period='1m',
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000,
            amount=10000.0,
            tick_count=10
        )
        
        synthesizer = BarSynthesizer()
        is_valid, errors = synthesizer.validate_bar(bar)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_hloc_high_low(self):
        """测试无效的HLOC（最高价<最低价）"""
        bar = Bar(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period='1m',
            open=10.0,
            high=9.5,  # 最高价 < 最低价
            low=10.0,
            close=10.0,
            volume=1000,
            amount=10000.0,
            tick_count=10
        )
        
        synthesizer = BarSynthesizer()
        is_valid, errors = synthesizer.validate_bar(bar)
        
        assert is_valid is False
        assert any("最高价" in err and "最低价" in err for err in errors)
    
    def test_invalid_hloc_high_open(self):
        """测试无效的HLOC（最高价<开盘价）"""
        bar = Bar(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period='1m',
            open=10.5,
            high=10.0,  # 最高价 < 开盘价
            low=9.8,
            close=10.0,
            volume=1000,
            amount=10000.0,
            tick_count=10
        )
        
        synthesizer = BarSynthesizer()
        is_valid, errors = synthesizer.validate_bar(bar)
        
        assert is_valid is False
        assert any("最高价" in err and "开盘价" in err for err in errors)
    
    def test_invalid_price_zero(self):
        """测试无效的价格（价格为0）"""
        bar = Bar(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period='1m',
            open=0.0,  # 无效价格
            high=10.0,
            low=9.8,
            close=10.0,
            volume=1000,
            amount=10000.0,
            tick_count=10
        )
        
        synthesizer = BarSynthesizer()
        is_valid, errors = synthesizer.validate_bar(bar)
        
        assert is_valid is False
        assert any("价格必须大于0" in err for err in errors)
    
    def test_invalid_negative_volume(self):
        """测试无效的成交量（负数）"""
        bar = Bar(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period='1m',
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=-1000,  # 负数成交量
            amount=10000.0,
            tick_count=10
        )
        
        synthesizer = BarSynthesizer()
        is_valid, errors = synthesizer.validate_bar(bar)
        
        assert is_valid is False
        assert any("成交量" in err and "不能为负" in err for err in errors)
    
    def test_invalid_tick_count(self):
        """测试无效的Tick数量"""
        bar = Bar(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            period='1m',
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000,
            amount=10000.0,
            tick_count=0  # 无效的Tick数量
        )
        
        synthesizer = BarSynthesizer()
        is_valid, errors = synthesizer.validate_bar(bar)
        
        assert is_valid is False
        assert any("Tick数量" in err for err in errors)


class TestBarRetrieval:
    """测试Bar获取"""
    
    def test_get_completed_bars_all(self):
        """测试获取所有已完成的Bar"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 生成多个Bar
        for minute in range(3):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=datetime(2024, 1, 1, 9, 30 + minute, 0),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            synthesizer.process_tick(tick)
        
        # 触发最后一个Bar完成
        tick_final = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 33, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick_final)
        
        bars = synthesizer.get_completed_bars()
        assert len(bars) == 3
    
    def test_get_completed_bars_by_symbol(self):
        """测试按标的过滤Bar"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 两个标的
        for symbol in ['000001.SZ', '600000.SH']:
            tick1 = Tick(
                symbol=symbol,
                timestamp=datetime(2024, 1, 1, 9, 30, 0),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            tick2 = Tick(
                symbol=symbol,
                timestamp=datetime(2024, 1, 1, 9, 31, 0),
                price=10.5,
                volume=200,
                amount=2100.0
            )
            synthesizer.process_tick(tick1)
            synthesizer.process_tick(tick2)
        
        bars = synthesizer.get_completed_bars(symbol='000001.SZ')
        assert len(bars) == 1
        assert bars[0].symbol == '000001.SZ'
    
    def test_get_completed_bars_clear(self):
        """测试清空已完成的Bar"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        tick1 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        tick2 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 31, 0),
            price=10.5,
            volume=200,
            amount=2100.0
        )
        synthesizer.process_tick(tick1)
        synthesizer.process_tick(tick2)
        
        bars = synthesizer.get_completed_bars(clear=True)
        assert len(bars) == 1
        
        # 再次获取应该为空
        bars = synthesizer.get_completed_bars()
        assert len(bars) == 0


class TestForceComplete:
    """测试强制完成"""
    
    def test_force_complete_all_bars(self):
        """测试强制完成所有Bar"""
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        # 添加一些未完成的Tick
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 30),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        synthesizer.process_tick(tick)
        
        # 强制完成
        completed_bars = synthesizer.force_complete_all_bars()
        
        # 应该完成两个周期的Bar
        assert len(completed_bars) == 2
        
        # 缓冲区应该被清空
        assert len(synthesizer.buffers) == 0


class TestStatistics:
    """测试统计信息"""
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        # 生成一些Bar
        for minute in range(6):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=datetime(2024, 1, 1, 9, 30 + minute, 0),
                price=10.0,
                volume=100,
                amount=1000.0
            )
            synthesizer.process_tick(tick)
        
        stats = synthesizer.get_statistics()
        
        assert 'active_buffers' in stats
        assert 'completed_bars' in stats
        assert 'period_stats' in stats
        assert 'symbol_stats' in stats
        assert 'supported_periods' in stats
        
        assert stats['supported_periods'] == ['1m', '5m']


class TestGlobalSingleton:
    """测试全局单例"""
    
    def test_singleton_returns_same_instance(self):
        """测试单例返回相同实例"""
        s1 = get_bar_synthesizer()
        s2 = get_bar_synthesizer()
        
        assert s1 is s2
    
    def test_singleton_configuration(self):
        """测试单例配置"""
        s = get_bar_synthesizer(periods=['1m'])
        
        assert '1m' in s.supported_periods


class TestEdgeCases:
    """测试边界条件"""
    
    def test_zero_volume_tick(self):
        """测试零成交量Tick"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        tick = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=0,  # 零成交量
            amount=0.0
        )
        
        # 应该正常处理
        completed_bars = synthesizer.process_tick(tick)
        assert len(completed_bars) == 0
    
    def test_large_price_movement(self):
        """测试大幅价格波动"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 价格从10涨到100
        tick1 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 0),
            price=10.0,
            volume=100,
            amount=1000.0
        )
        tick2 = Tick(
            symbol='000001.SZ',
            timestamp=datetime(2024, 1, 1, 9, 30, 30),
            price=100.0,
            volume=100,
            amount=10000.0
        )
        
        synthesizer.process_tick(tick1)
        synthesizer.process_tick(tick2)
        
        buffer = synthesizer.buffers[('000001.SZ', '1m')]
        assert buffer.open == 10.0
        assert buffer.high == 100.0
        assert buffer.low == 10.0
        assert buffer.close == 100.0
    
    def test_many_ticks_in_one_period(self):
        """测试一个周期内大量Tick"""
        synthesizer = BarSynthesizer(periods=['1m'])
        
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        
        # 60个Tick（每秒一个）
        for second in range(60):
            tick = Tick(
                symbol='000001.SZ',
                timestamp=base_time + timedelta(seconds=second),
                price=10.0 + second * 0.01,
                volume=10,
                amount=100.0
            )
            synthesizer.process_tick(tick)
        
        buffer = synthesizer.buffers[('000001.SZ', '1m')]
        assert buffer.tick_count == 60
        assert buffer.volume == 600  # 60 * 10
