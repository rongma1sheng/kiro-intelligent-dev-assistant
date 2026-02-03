"""战术复盘仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 5. 战术复盘 (Tactical)
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock

from src.interface.tactical_dashboard import (
    TacticalDashboard,
    TradeRecord,
    AIMarker,
    ReviewStatistics,
    KLineData,
    TradeDirection,
    OrderStatus
)


class TestTradeDirection:
    """TradeDirection枚举测试"""
    
    def test_direction_values(self):
        """测试交易方向值"""
        assert TradeDirection.BUY.value == "买入"
        assert TradeDirection.SELL.value == "卖出"


class TestOrderStatus:
    """OrderStatus枚举测试"""
    
    def test_status_values(self):
        """测试订单状态值"""
        assert OrderStatus.FILLED.value == "成交"
        assert OrderStatus.REJECTED.value == "废单"
        assert OrderStatus.PARTIAL.value == "部分成交"
        assert OrderStatus.CANCELLED.value == "已撤销"


class TestTradeRecord:
    """TradeRecord数据模型测试"""
    
    def test_creation(self):
        """测试创建交易记录"""
        record = TradeRecord(
            trade_id="T20260127001",
            timestamp=datetime.now(),
            symbol="000001",
            name="平安银行",
            direction=TradeDirection.BUY,
            price=12.35,
            quantity=5000,
            amount=61750,
            status=OrderStatus.FILLED,
            strategy_id="S01"
        )
        
        assert record.trade_id == "T20260127001"
        assert record.symbol == "000001"
        assert record.direction == TradeDirection.BUY
        assert record.quantity == 5000
    
    def test_to_dict(self):
        """测试转换为字典"""
        record = TradeRecord(
            trade_id="T001",
            timestamp=datetime.now(),
            symbol="000001",
            name="平安银行",
            direction=TradeDirection.SELL,
            price=12.50,
            quantity=1000,
            amount=12500
        )
        
        result = record.to_dict()
        
        assert isinstance(result, dict)
        assert result['trade_id'] == "T001"
        assert result['direction'] == "卖出"
    
    def test_default_values(self):
        """测试默认值"""
        record = TradeRecord(
            trade_id="T001",
            timestamp=datetime.now(),
            symbol="000001",
            name="平安银行",
            direction=TradeDirection.BUY,
            price=12.00,
            quantity=100,
            amount=1200
        )
        
        assert record.status == OrderStatus.FILLED
        assert record.strategy_id == ""
        assert record.audit_opinion == ""


class TestAIMarker:
    """AIMarker数据模型测试"""
    
    def test_creation(self):
        """测试创建AI标记"""
        marker = AIMarker(
            timestamp=datetime.now(),
            marker_type='buy',
            price=11.80,
            reason='主力资金流入'
        )
        
        assert marker.marker_type == 'buy'
        assert marker.price == 11.80
        assert marker.reason == '主力资金流入'
    
    def test_to_dict(self):
        """测试转换为字典"""
        marker = AIMarker(
            timestamp=datetime.now(),
            marker_type='sell',
            price=12.50
        )
        
        result = marker.to_dict()
        
        assert isinstance(result, dict)
        assert result['marker_type'] == 'sell'
        assert result['price'] == 12.50


class TestReviewStatistics:
    """ReviewStatistics数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        stats = ReviewStatistics()
        
        assert stats.win_rate == 0.0
        assert stats.profit_loss_ratio == 0.0
        assert stats.total_trades == 0
    
    def test_custom_values(self):
        """测试自定义值"""
        stats = ReviewStatistics(
            win_rate=62.5,
            profit_loss_ratio=1.85,
            avg_holding_days=3.2,
            max_consecutive_wins=8,
            max_consecutive_losses=3,
            total_trades=156,
            profitable_trades=98,
            losing_trades=58
        )
        
        assert stats.win_rate == 62.5
        assert stats.profit_loss_ratio == 1.85
        assert stats.total_trades == 156
    
    def test_to_dict(self):
        """测试转换为字典"""
        stats = ReviewStatistics(
            win_rate=60.0,
            total_trades=100
        )
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert result['win_rate'] == 60.0
        assert result['total_trades'] == 100


class TestKLineData:
    """KLineData数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        kline = KLineData()
        
        assert kline.dates == []
        assert kline.opens == []
        assert kline.closes == []
        assert kline.volumes == []
    
    def test_custom_values(self):
        """测试自定义值"""
        kline = KLineData(
            dates=['2026-01-01', '2026-01-02'],
            opens=[12.0, 12.5],
            highs=[12.8, 13.0],
            lows=[11.8, 12.2],
            closes=[12.5, 12.8],
            volumes=[1000000, 1200000]
        )
        
        assert len(kline.dates) == 2
        assert kline.closes[1] == 12.8


class TestTacticalDashboard:
    """TacticalDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return TacticalDashboard()
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return TacticalDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        mock_redis = Mock()
        dashboard = TacticalDashboard(redis_client=mock_redis)
        
        assert dashboard.redis_client is mock_redis
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'rise' in dashboard.COLOR_SCHEME
        assert 'fall' in dashboard.COLOR_SCHEME
        assert 'buy_marker' in dashboard.COLOR_SCHEME
        assert 'sell_marker' in dashboard.COLOR_SCHEME
        assert 'stop_loss_marker' in dashboard.COLOR_SCHEME
    
    def test_get_kline_data_mock(self, dashboard):
        """测试获取K线数据（模拟数据）"""
        kline = dashboard.get_kline_data("000001", 30)
        
        assert isinstance(kline, KLineData)
        assert len(kline.dates) > 0
        assert len(kline.opens) == len(kline.dates)
        assert len(kline.closes) == len(kline.dates)
    
    def test_get_ai_markers_mock(self, dashboard):
        """测试获取AI标记（模拟数据）"""
        markers = dashboard.get_ai_markers("000001")
        
        assert isinstance(markers, list)
        assert len(markers) > 0
        assert all(isinstance(m, AIMarker) for m in markers)
    
    def test_get_ai_markers_types(self, dashboard):
        """测试AI标记类型"""
        markers = dashboard.get_ai_markers("000001")
        
        marker_types = [m.marker_type for m in markers]
        assert 'buy' in marker_types
        assert 'sell' in marker_types
    
    def test_get_trade_records_mock(self, dashboard):
        """测试获取交易记录（模拟数据）"""
        records = dashboard.get_trade_records()
        
        assert isinstance(records, list)
        assert len(records) > 0
        assert all(isinstance(r, TradeRecord) for r in records)
    
    def test_get_trade_records_filter_rejected(self, dashboard):
        """测试筛选废单"""
        all_records = dashboard.get_trade_records(include_rejected=True)
        filtered_records = dashboard.get_trade_records(include_rejected=False)
        
        rejected_count = sum(1 for r in all_records if r.status == OrderStatus.REJECTED)
        
        if rejected_count > 0:
            assert len(filtered_records) < len(all_records)
    
    def test_get_trade_records_filter_symbol(self, dashboard):
        """测试按股票筛选"""
        records = dashboard.get_trade_records(symbol="000001")
        
        for record in records:
            assert record.symbol == "000001"
    
    def test_get_review_statistics_mock(self, dashboard):
        """测试获取复盘统计（模拟数据）"""
        stats = dashboard.get_review_statistics()
        
        assert isinstance(stats, ReviewStatistics)
        assert stats.win_rate > 0
        assert stats.total_trades > 0


class TestTacticalDashboardRedis:
    """TacticalDashboard Redis集成测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis"""
        return Mock()
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """创建带Redis的测试实例"""
        return TacticalDashboard(redis_client=mock_redis)
    
    def test_redis_error_fallback_kline(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟K线数据"""
        mock_redis.lrange.side_effect = Exception("Redis error")
        
        kline = dashboard.get_kline_data("000001", 30)
        
        assert isinstance(kline, KLineData)
        assert len(kline.dates) > 0
    
    def test_redis_error_fallback_markers(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟标记数据"""
        mock_redis.lrange.side_effect = Exception("Redis error")
        
        markers = dashboard.get_ai_markers("000001")
        
        assert isinstance(markers, list)
    
    def test_redis_error_fallback_statistics(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟统计数据"""
        mock_redis.hgetall.side_effect = Exception("Redis error")
        
        stats = dashboard.get_review_statistics()
        
        assert isinstance(stats, ReviewStatistics)


class TestTacticalDashboardEdgeCases:
    """TacticalDashboard边界条件测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return TacticalDashboard()
    
    def test_empty_kline_data(self):
        """测试空K线数据"""
        kline = KLineData()
        
        assert len(kline.dates) == 0
    
    def test_trade_record_with_audit_opinion(self):
        """测试带审计意见的交易记录"""
        record = TradeRecord(
            trade_id="T001",
            timestamp=datetime.now(),
            symbol="000001",
            name="平安银行",
            direction=TradeDirection.BUY,
            price=12.00,
            quantity=100,
            amount=1200,
            status=OrderStatus.REJECTED,
            audit_opinion="风险敞口超限"
        )
        
        assert record.status == OrderStatus.REJECTED
        assert record.audit_opinion == "风险敞口超限"
    
    def test_ai_marker_without_reason(self):
        """测试无原因的AI标记"""
        marker = AIMarker(
            timestamp=datetime.now(),
            marker_type='buy',
            price=12.00
        )
        
        assert marker.reason == ""
