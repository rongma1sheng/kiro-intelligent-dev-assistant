"""全息扫描仪仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 2. 全息扫描仪 (Scanner)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.interface.scanner_dashboard import (
    ScannerDashboard,
    StockSignal,
    StockDetail,
    FilterCriteria,
    RadarStatus,
    SignalStrength
)


class TestRadarStatus:
    """RadarStatus枚举测试"""
    
    def test_radar_status_values(self):
        """测试雷达状态值"""
        assert RadarStatus.ACCUMULATION.value == "吸筹"
        assert RadarStatus.WASHOUT.value == "洗盘"
        assert RadarStatus.NEUTRAL.value == "中性"
        assert RadarStatus.BREAKOUT.value == "突破"
        assert RadarStatus.DIVERGENCE.value == "背离"


class TestStockSignal:
    """StockSignal数据模型测试"""
    
    def test_creation(self):
        """测试创建信号"""
        signal = StockSignal(
            symbol="000001",
            name="平安银行",
            price=12.50,
            change_pct=2.35,
            signal_strength=95,
            radar_score=88,
            sentiment_score=82,
            radar_status=RadarStatus.ACCUMULATION
        )
        
        assert signal.symbol == "000001"
        assert signal.name == "平安银行"
        assert signal.price == 12.50
        assert signal.signal_strength == 95
        assert signal.radar_status == RadarStatus.ACCUMULATION
    
    def test_to_dict(self):
        """测试转换为字典"""
        signal = StockSignal(
            symbol="000001",
            name="平安银行",
            price=12.50,
            change_pct=2.35,
            signal_strength=95,
            radar_score=88,
            sentiment_score=82
        )
        
        result = signal.to_dict()
        
        assert isinstance(result, dict)
        assert result['symbol'] == "000001"
        assert result['price'] == 12.50
        assert 'update_time' in result


class TestStockDetail:
    """StockDetail数据模型测试"""
    
    def test_creation(self):
        """测试创建详情"""
        detail = StockDetail(
            symbol="000001",
            name="平安银行",
            price=12.50,
            change_pct=2.35,
            open_price=12.20,
            high_price=12.80,
            low_price=12.10,
            volume=15000000,
            amount=185000000,
            radar_status=RadarStatus.ACCUMULATION,
            radar_score=88,
            sentiment_score=82,
            ai_summary="主力资金持续流入"
        )
        
        assert detail.symbol == "000001"
        assert detail.open_price == 12.20
        assert detail.high_price == 12.80
        assert detail.ai_summary == "主力资金持续流入"
    
    def test_to_dict(self):
        """测试转换为字典"""
        detail = StockDetail(
            symbol="000001",
            name="平安银行",
            price=12.50,
            change_pct=2.35,
            open_price=12.20,
            high_price=12.80,
            low_price=12.10,
            volume=15000000,
            amount=185000000,
            radar_status=RadarStatus.ACCUMULATION,
            radar_score=88,
            sentiment_score=82
        )
        
        result = detail.to_dict()
        
        assert isinstance(result, dict)
        assert result['symbol'] == "000001"
        assert result['radar_status'] == "吸筹"


class TestFilterCriteria:
    """FilterCriteria数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        criteria = FilterCriteria()
        
        assert criteria.radar_status is None
        assert criteria.sentiment_min == 0
        assert criteria.sentiment_max == 100
        assert criteria.price_min == 0
    
    def test_custom_values(self):
        """测试自定义值"""
        criteria = FilterCriteria(
            radar_status=[RadarStatus.ACCUMULATION, RadarStatus.BREAKOUT],
            sentiment_min=50,
            sentiment_max=100,
            price_min=10,
            price_max=50
        )
        
        assert len(criteria.radar_status) == 2
        assert criteria.sentiment_min == 50
        assert criteria.price_min == 10


class TestScannerDashboard:
    """ScannerDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return ScannerDashboard()
    
    @pytest.fixture
    def dashboard_admin(self):
        """创建Admin测试实例"""
        return ScannerDashboard(is_admin=True)
    
    @pytest.fixture
    def dashboard_guest(self):
        """创建Guest测试实例"""
        return ScannerDashboard(is_admin=False)
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return ScannerDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
        assert dashboard.is_admin is True
        assert dashboard.websocket_url == "ws://localhost:8502/radar"
    
    def test_init_guest(self, dashboard_guest):
        """测试Guest初始化"""
        assert dashboard_guest.is_admin is False
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'rise' in dashboard.COLOR_SCHEME
        assert 'fall' in dashboard.COLOR_SCHEME
        assert dashboard.COLOR_SCHEME['rise'] == '#FF4D4F'
        assert dashboard.COLOR_SCHEME['fall'] == '#52C41A'
    
    def test_get_top_signals_mock(self, dashboard):
        """测试获取Top信号（模拟数据）"""
        signals = dashboard.get_top_signals(5)
        
        assert isinstance(signals, list)
        assert len(signals) == 5
        assert all(isinstance(s, StockSignal) for s in signals)
    
    def test_get_top_signals_limit(self, dashboard):
        """测试获取Top信号（限制数量）"""
        signals = dashboard.get_top_signals(3)
        
        assert len(signals) == 3
    
    def test_get_top_signals_sorted(self, dashboard):
        """测试Top信号排序"""
        signals = dashboard.get_top_signals(5)
        
        # 验证按信号强度降序排列
        for i in range(len(signals) - 1):
            assert signals[i].signal_strength >= signals[i + 1].signal_strength
    
    def test_filter_stocks_mock(self, dashboard):
        """测试筛选股票（模拟数据）"""
        criteria = FilterCriteria()
        results = dashboard.filter_stocks(criteria)
        
        assert isinstance(results, list)
        assert len(results) > 0
    
    def test_filter_stocks_with_criteria(self, dashboard):
        """测试带条件筛选"""
        criteria = FilterCriteria(
            sentiment_min=50,
            sentiment_max=100,
            price_min=10,
            price_max=200
        )
        
        results = dashboard.filter_stocks(criteria)
        
        assert isinstance(results, list)
    
    def test_get_stock_detail_mock(self, dashboard):
        """测试获取股票详情（模拟数据）"""
        detail = dashboard.get_stock_detail("000001")
        
        assert isinstance(detail, StockDetail)
        assert detail.symbol == "000001"
    
    def test_get_stock_detail_has_technical_indicators(self, dashboard):
        """测试股票详情包含技术指标"""
        detail = dashboard.get_stock_detail("000001")
        
        assert 'RSI' in detail.technical_indicators
        assert 'MACD' in detail.technical_indicators
    
    def test_get_stock_detail_has_ai_summary(self, dashboard):
        """测试股票详情包含AI摘要"""
        detail = dashboard.get_stock_detail("000001")
        
        assert detail.ai_summary != ""


class TestScannerDashboardRedis:
    """ScannerDashboard Redis集成测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis"""
        return Mock()
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """创建带Redis的测试实例"""
        return ScannerDashboard(redis_client=mock_redis)
    
    def test_get_top_signals_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取Top信号"""
        mock_redis.zrevrange.return_value = [
            ('000001', 95),
            ('600519', 92)
        ]
        mock_redis.hgetall.return_value = {
            'name': '平安银行',
            'price': '12.50',
            'change_pct': '2.35',
            'radar_score': '88',
            'sentiment_score': '82',
            'radar_status': 'ACCUMULATION'
        }
        
        signals = dashboard.get_top_signals(2)
        
        mock_redis.zrevrange.assert_called_once()
        assert len(signals) == 2
    
    def test_get_stock_detail_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取股票详情"""
        mock_redis.hgetall.side_effect = [
            {
                'name': '平安银行',
                'price': '12.50',
                'change_pct': '2.35',
                'open': '12.20',
                'high': '12.80',
                'low': '12.10',
                'volume': '15000000',
                'amount': '185000000',
                'radar_status': 'ACCUMULATION',
                'radar_score': '88',
                'sentiment_score': '82'
            },
            {
                'rsi': '58.5',
                'macd': '0.125',
                'macd_signal': '0.098',
                'bb_upper': '13.50',
                'bb_lower': '11.50'
            }
        ]
        mock_redis.get.return_value = "主力资金持续流入"
        
        detail = dashboard.get_stock_detail("000001")
        
        assert detail is not None
        assert detail.name == '平安银行'
        assert detail.ai_summary == "主力资金持续流入"


class TestSignalStrength:
    """SignalStrength枚举测试"""
    
    def test_signal_strength_values(self):
        """测试信号强度值"""
        assert SignalStrength.WEAK.value == "弱"
        assert SignalStrength.MEDIUM.value == "中"
        assert SignalStrength.STRONG.value == "强"
        assert SignalStrength.VERY_STRONG.value == "极强"
