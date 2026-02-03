"""狩猎雷达仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 4. 狩猎雷达 (Radar)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import json

from src.interface.radar_dashboard import (
    RadarDashboard,
    RadarSignal,
    SignalStatistics,
    SignalType
)


class TestSignalType:
    """SignalType枚举测试"""
    
    def test_signal_type_values(self):
        """测试信号类型值"""
        assert SignalType.ACCUMULATION.value == "吸筹"
        assert SignalType.WASHOUT.value == "洗盘"
        assert SignalType.BREAKOUT.value == "突破"
        assert SignalType.DIVERGENCE.value == "背离"
        assert SignalType.UNKNOWN.value == "未知"


class TestRadarSignal:
    """RadarSignal数据模型测试"""
    
    def test_creation(self):
        """测试创建信号"""
        signal = RadarSignal(
            timestamp=datetime.now(),
            symbol="000001",
            name="平安银行",
            signal_type=SignalType.ACCUMULATION,
            signal_strength=85,
            main_force_prob=72.5,
            price=12.50,
            change_pct=2.35
        )
        
        assert signal.symbol == "000001"
        assert signal.name == "平安银行"
        assert signal.signal_type == SignalType.ACCUMULATION
        assert signal.signal_strength == 85
        assert signal.main_force_prob == 72.5
    
    def test_to_dict(self):
        """测试转换为字典"""
        signal = RadarSignal(
            timestamp=datetime.now(),
            symbol="000001",
            name="平安银行",
            signal_type=SignalType.BREAKOUT,
            signal_strength=90,
            main_force_prob=80.0
        )
        
        result = signal.to_dict()
        
        assert isinstance(result, dict)
        assert result['symbol'] == "000001"
        assert result['signal_type'] == "突破"
        assert result['signal_strength'] == 90
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': '600519',
            'name': '贵州茅台',
            'signal_type': '吸筹',
            'signal_strength': 88,
            'main_force_prob': 75.0,
            'price': 1850.0,
            'change_pct': 1.25
        }
        
        signal = RadarSignal.from_dict(data)
        
        assert signal.symbol == '600519'
        assert signal.signal_type == SignalType.ACCUMULATION
        assert signal.signal_strength == 88
    
    def test_from_dict_unknown_type(self):
        """测试从字典创建（未知类型）"""
        data = {
            'symbol': '000001',
            'name': '平安银行',
            'signal_type': '未知类型',
            'signal_strength': 50,
            'main_force_prob': 50.0
        }
        
        signal = RadarSignal.from_dict(data)
        
        assert signal.signal_type == SignalType.UNKNOWN


class TestSignalStatistics:
    """SignalStatistics数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        stats = SignalStatistics()
        
        assert stats.total_count == 0
        assert stats.accuracy_rate == 0.0
        assert stats.avg_response_time_ms == 0.0
        assert stats.type_distribution == {}
    
    def test_custom_values(self):
        """测试自定义值"""
        stats = SignalStatistics(
            total_count=1256,
            accuracy_rate=72.5,
            avg_response_time_ms=15.3,
            type_distribution={"吸筹": 425, "洗盘": 312}
        )
        
        assert stats.total_count == 1256
        assert stats.accuracy_rate == 72.5
        assert stats.type_distribution["吸筹"] == 425
    
    def test_to_dict(self):
        """测试转换为字典"""
        stats = SignalStatistics(
            total_count=100,
            accuracy_rate=75.0
        )
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert result['total_count'] == 100
        assert result['accuracy_rate'] == 75.0


class TestRadarDashboard:
    """RadarDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return RadarDashboard()
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return RadarDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
        assert dashboard.websocket_url == "ws://localhost:8502/radar"
        assert dashboard.max_signals == 100
    
    def test_init_custom(self):
        """测试自定义初始化"""
        mock_redis = Mock()
        dashboard = RadarDashboard(
            redis_client=mock_redis,
            websocket_url="ws://custom:8080/radar",
            max_signals=50
        )
        
        assert dashboard.redis_client is mock_redis
        assert dashboard.websocket_url == "ws://custom:8080/radar"
        assert dashboard.max_signals == 50
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'rise' in dashboard.COLOR_SCHEME
        assert 'fall' in dashboard.COLOR_SCHEME
        assert dashboard.COLOR_SCHEME['rise'] == '#FF4D4F'
        assert dashboard.COLOR_SCHEME['fall'] == '#52C41A'
    
    def test_signal_colors(self, dashboard):
        """测试信号类型颜色"""
        assert SignalType.ACCUMULATION in dashboard.SIGNAL_COLORS
        assert SignalType.BREAKOUT in dashboard.SIGNAL_COLORS
    
    def test_get_recent_signals_mock(self, dashboard):
        """测试获取最近信号（模拟数据）"""
        signals = dashboard.get_recent_signals(10)
        
        assert isinstance(signals, list)
        assert len(signals) <= 10
        assert all(isinstance(s, RadarSignal) for s in signals)
    
    def test_get_recent_signals_limit(self, dashboard):
        """测试获取信号数量限制"""
        signals = dashboard.get_recent_signals(5)
        
        assert len(signals) <= 5
    
    def test_get_signal_statistics_mock(self, dashboard):
        """测试获取信号统计（模拟数据）"""
        stats = dashboard.get_signal_statistics()
        
        assert isinstance(stats, SignalStatistics)
        assert stats.total_count > 0
        assert stats.accuracy_rate > 0
    
    def test_is_connected_default(self, dashboard):
        """测试默认连接状态"""
        assert dashboard.is_connected is False
    
    def test_get_buffered_signals_empty(self, dashboard):
        """测试空缓冲区"""
        signals = dashboard.get_buffered_signals()
        
        assert isinstance(signals, list)
        assert len(signals) == 0
    
    def test_get_strength_color_strong(self, dashboard):
        """测试信号强度颜色（强）"""
        color = dashboard._get_strength_color(85)
        
        assert color == '#FF4D4F'  # 红色
    
    def test_get_strength_color_medium(self, dashboard):
        """测试信号强度颜色（中）"""
        color = dashboard._get_strength_color(65)
        
        assert color == '#FA8C16'  # 橙色
    
    def test_get_strength_color_weak(self, dashboard):
        """测试信号强度颜色（弱）"""
        color = dashboard._get_strength_color(30)
        
        assert color == '#8C8C8C'  # 灰色


class TestRadarDashboardRedis:
    """RadarDashboard Redis集成测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis"""
        return Mock()
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """创建带Redis的测试实例"""
        return RadarDashboard(redis_client=mock_redis)
    
    def test_get_recent_signals_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取最近信号"""
        mock_redis.lrange.return_value = [
            json.dumps({
                'timestamp': datetime.now().isoformat(),
                'symbol': '000001',
                'name': '平安银行',
                'signal_type': '吸筹',
                'signal_strength': 85,
                'main_force_prob': 72.5
            })
        ]
        
        signals = dashboard.get_recent_signals(10)
        
        mock_redis.lrange.assert_called_once()
        assert len(signals) == 1
        assert signals[0].symbol == '000001'
    
    def test_get_signal_statistics_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取信号统计"""
        mock_redis.hgetall.side_effect = [
            {
                b'total_count': b'1256',
                b'accuracy_rate': b'72.5',
                b'avg_response_time_ms': b'15.3'
            },
            {
                'accumulation': 425,
                'washout': 312
            }
        ]
        
        stats = dashboard.get_signal_statistics()
        
        assert stats.total_count == 1256
        assert stats.accuracy_rate == 72.5
    
    def test_redis_error_fallback(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟数据"""
        mock_redis.lrange.side_effect = Exception("Redis error")
        
        signals = dashboard.get_recent_signals(10)
        
        # 应该回退到模拟数据
        assert isinstance(signals, list)
