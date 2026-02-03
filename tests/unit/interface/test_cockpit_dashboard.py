"""驾驶舱仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 1. 驾驶舱 (Cockpit)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.interface.cockpit_dashboard import (
    CockpitDashboard,
    RealTimeMetrics,
    MarketMacro,
    EmergencyControlState,
    MarketRegime,
    RiskLevel
)


class TestRealTimeMetrics:
    """RealTimeMetrics数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        metrics = RealTimeMetrics()
        
        assert metrics.total_assets == 0.0
        assert metrics.daily_pnl == 0.0
        assert metrics.daily_pnl_pct == 0.0
        assert metrics.position_count == 0
        assert metrics.risk_level == RiskLevel.LOW
    
    def test_custom_values(self):
        """测试自定义值"""
        metrics = RealTimeMetrics(
            total_assets=1000000.0,
            daily_pnl=50000.0,
            daily_pnl_pct=5.0,
            position_count=10,
            position_value=600000.0,
            position_ratio=60.0,
            risk_level=RiskLevel.MEDIUM,
            risk_score=45.0
        )
        
        assert metrics.total_assets == 1000000.0
        assert metrics.daily_pnl == 50000.0
        assert metrics.position_count == 10
        assert metrics.risk_level == RiskLevel.MEDIUM
    
    def test_to_dict(self):
        """测试转换为字典"""
        metrics = RealTimeMetrics(
            total_assets=1000000.0,
            daily_pnl=50000.0
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result['total_assets'] == 1000000.0
        assert result['daily_pnl'] == 50000.0
        assert 'update_time' in result


class TestMarketMacro:
    """MarketMacro数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        macro = MarketMacro()
        
        assert macro.advance_count == 0
        assert macro.decline_count == 0
        assert macro.adr == 1.0
        assert macro.regime == MarketRegime.OSCILLATION
    
    def test_custom_values(self):
        """测试自定义值"""
        macro = MarketMacro(
            advance_count=2500,
            decline_count=2000,
            adr=1.25,
            regime=MarketRegime.BULL,
            regime_confidence=0.85
        )
        
        assert macro.advance_count == 2500
        assert macro.decline_count == 2000
        assert macro.adr == 1.25
        assert macro.regime == MarketRegime.BULL
        assert macro.regime_confidence == 0.85
    
    def test_to_dict(self):
        """测试转换为字典"""
        macro = MarketMacro(
            advance_count=2500,
            regime=MarketRegime.BULL
        )
        
        result = macro.to_dict()
        
        assert isinstance(result, dict)
        assert result['advance_count'] == 2500
        assert result['regime'] == '牛市'


class TestMarketRegime:
    """MarketRegime枚举测试"""
    
    def test_regime_values(self):
        """测试市场状态值"""
        assert MarketRegime.BULL.value == "牛市"
        assert MarketRegime.BEAR.value == "熊市"
        assert MarketRegime.OSCILLATION.value == "震荡"
        assert MarketRegime.CRASH.value == "崩盘"


class TestRiskLevel:
    """RiskLevel枚举测试"""
    
    def test_risk_level_values(self):
        """测试风险等级值"""
        assert RiskLevel.LOW.value == "低风险"
        assert RiskLevel.MEDIUM.value == "中风险"
        assert RiskLevel.HIGH.value == "高风险"
        assert RiskLevel.CRITICAL.value == "极高风险"


class TestCockpitDashboard:
    """CockpitDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return CockpitDashboard()
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return CockpitDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
        assert dashboard.refresh_interval == 1
    
    def test_init_custom(self):
        """测试自定义初始化"""
        mock_redis = Mock()
        dashboard = CockpitDashboard(
            redis_client=mock_redis,
            refresh_interval=5
        )
        
        assert dashboard.redis_client is mock_redis
        assert dashboard.refresh_interval == 5
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'rise_primary' in dashboard.COLOR_SCHEME
        assert 'fall_primary' in dashboard.COLOR_SCHEME
        assert dashboard.COLOR_SCHEME['rise_primary'] == '#FF4D4F'
        assert dashboard.COLOR_SCHEME['fall_primary'] == '#52C41A'
    
    def test_get_realtime_metrics_mock(self, dashboard):
        """测试获取实时指标（模拟数据）"""
        metrics = dashboard.get_realtime_metrics()
        
        assert isinstance(metrics, RealTimeMetrics)
        assert metrics.total_assets > 0
        assert metrics.position_count >= 0
    
    def test_get_realtime_metrics_redis(self, dashboard_with_redis):
        """测试从Redis获取实时指标"""
        dashboard_with_redis.redis_client.hgetall.return_value = {
            'total_assets': '1000000',
            'daily_pnl': '50000',
            'position_value': '600000',
            'position_count': '10'
        }
        
        metrics = dashboard_with_redis.get_realtime_metrics()
        
        assert isinstance(metrics, RealTimeMetrics)
        assert metrics.total_assets == 1000000.0
        assert metrics.daily_pnl == 50000.0
    
    def test_get_market_macro_mock(self, dashboard):
        """测试获取市场宏观（模拟数据）"""
        macro = dashboard.get_market_macro()
        
        assert isinstance(macro, MarketMacro)
        assert macro.advance_count >= 0
        assert macro.decline_count >= 0
    
    def test_get_market_macro_redis(self, dashboard_with_redis):
        """测试从Redis获取市场宏观"""
        dashboard_with_redis.redis_client.hgetall.return_value = {
            'advance_count': '2500',
            'decline_count': '2000',
            'regime': 'BULL',
            'regime_confidence': '0.85'
        }
        
        macro = dashboard_with_redis.get_market_macro()
        
        assert isinstance(macro, MarketMacro)
        assert macro.advance_count == 2500
        assert macro.regime == MarketRegime.BULL
    
    def test_execute_liquidate_all_no_confirm(self, dashboard):
        """测试一键清仓（未确认）"""
        result = dashboard.execute_liquidate_all(confirm=False)
        
        assert result['success'] is False
        assert result['require_confirm'] is True
    
    def test_execute_liquidate_all_confirmed(self, dashboard):
        """测试一键清仓（已确认）"""
        result = dashboard.execute_liquidate_all(confirm=True)
        
        assert result['success'] is True
        assert 'timestamp' in result
    
    def test_execute_liquidate_all_with_redis(self, dashboard_with_redis):
        """测试一键清仓（带Redis）"""
        result = dashboard_with_redis.execute_liquidate_all(confirm=True)
        
        assert result['success'] is True
        dashboard_with_redis.redis_client.publish.assert_called()
    
    def test_execute_pause_buy(self, dashboard):
        """测试暂停买入"""
        result = dashboard.execute_pause_buy(pause=True)
        
        assert result['success'] is True
        assert result['buy_paused'] is True
    
    def test_execute_resume_buy(self, dashboard):
        """测试恢复买入"""
        result = dashboard.execute_pause_buy(pause=False)
        
        assert result['success'] is True
        assert result['buy_paused'] is False
    
    def test_execute_emergency_stop_no_confirm(self, dashboard):
        """测试末日开关（未确认）"""
        result = dashboard.execute_emergency_stop(confirm=False)
        
        assert result['success'] is False
        assert result['require_confirm'] is True
        assert 'warning' in result
    
    def test_execute_emergency_stop_confirmed(self, dashboard):
        """测试末日开关（已确认）"""
        result = dashboard.execute_emergency_stop(confirm=True)
        
        assert result['success'] is True
    
    def test_get_emergency_state(self, dashboard):
        """测试获取紧急控制状态"""
        state = dashboard.get_emergency_state()
        
        assert isinstance(state, EmergencyControlState)
        assert state.buy_paused is False
        assert state.emergency_stop is False
    
    def test_calculate_risk_score_low(self, dashboard):
        """测试计算风险评分（低风险）"""
        score = dashboard._calculate_risk_score(20.0, 1.0)
        
        assert score < 25
    
    def test_calculate_risk_score_medium(self, dashboard):
        """测试计算风险评分（中风险）"""
        score = dashboard._calculate_risk_score(50.0, -2.0)
        
        assert 25 <= score < 50
    
    def test_calculate_risk_score_high(self, dashboard):
        """测试计算风险评分（高风险）"""
        score = dashboard._calculate_risk_score(80.0, -3.0)
        
        assert score >= 50
    
    def test_get_risk_level_low(self, dashboard):
        """测试获取风险等级（低）"""
        level = dashboard._get_risk_level(20)
        
        assert level == RiskLevel.LOW
    
    def test_get_risk_level_medium(self, dashboard):
        """测试获取风险等级（中）"""
        level = dashboard._get_risk_level(40)
        
        assert level == RiskLevel.MEDIUM
    
    def test_get_risk_level_high(self, dashboard):
        """测试获取风险等级（高）"""
        level = dashboard._get_risk_level(60)
        
        assert level == RiskLevel.HIGH
    
    def test_get_risk_level_critical(self, dashboard):
        """测试获取风险等级（极高）"""
        level = dashboard._get_risk_level(80)
        
        assert level == RiskLevel.CRITICAL
    
    def test_get_regime_emoji(self, dashboard):
        """测试获取市场状态emoji"""
        assert dashboard._get_regime_emoji(MarketRegime.BULL) == "🐂"
        assert dashboard._get_regime_emoji(MarketRegime.BEAR) == "🐻"
        assert dashboard._get_regime_emoji(MarketRegime.OSCILLATION) == "〰️"
        assert dashboard._get_regime_emoji(MarketRegime.CRASH) == "💥"
    
    def test_get_risk_color(self, dashboard):
        """测试获取风险颜色"""
        assert dashboard._get_risk_color(RiskLevel.LOW) == dashboard.COLOR_SCHEME['success']
        assert dashboard._get_risk_color(RiskLevel.MEDIUM) == dashboard.COLOR_SCHEME['warning']
        assert dashboard._get_risk_color(RiskLevel.HIGH) == dashboard.COLOR_SCHEME['danger']


class TestEmergencyControlState:
    """EmergencyControlState测试"""
    
    def test_default_state(self):
        """测试默认状态"""
        state = EmergencyControlState()
        
        assert state.buy_paused is False
        assert state.emergency_stop is False
        assert state.last_liquidation is None
    
    def test_custom_state(self):
        """测试自定义状态"""
        now = datetime.now()
        state = EmergencyControlState(
            buy_paused=True,
            emergency_stop=True,
            last_liquidation=now
        )
        
        assert state.buy_paused is True
        assert state.emergency_stop is True
        assert state.last_liquidation == now
