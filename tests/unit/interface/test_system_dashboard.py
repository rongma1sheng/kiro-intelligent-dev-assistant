"""系统中枢仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 7. 系统中枢 (System)
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch

from src.interface.system_dashboard import (
    SystemDashboard,
    HardwareTelemetry,
    APICostData,
    HotTuningConfig,
    StrategySwitch,
    RiskPreference
)


class TestRiskPreference:
    """RiskPreference枚举测试"""
    
    def test_preference_values(self):
        """测试风险偏好值"""
        assert RiskPreference.CONSERVATIVE.value == "保守"
        assert RiskPreference.BALANCED.value == "平衡"
        assert RiskPreference.AGGRESSIVE.value == "激进"


class TestHardwareTelemetry:
    """HardwareTelemetry数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        telemetry = HardwareTelemetry()
        
        assert telemetry.cpu_usage == 0.0
        assert telemetry.memory_usage == 0.0
        assert telemetry.gpu_memory_usage == 0.0
    
    def test_custom_values(self):
        """测试自定义值"""
        telemetry = HardwareTelemetry(
            cpu_usage=45.5,
            memory_usage=62.3,
            gpu_memory_usage=78.5,
            gpu_memory_fragmentation=12.5,
            disk_usage=55.0,
            disk_free_gb=450.5,
            network_latency_ms=25.3
        )
        
        assert telemetry.cpu_usage == 45.5
        assert telemetry.memory_usage == 62.3
        assert telemetry.gpu_memory_usage == 78.5
    
    def test_to_dict(self):
        """测试转换为字典"""
        telemetry = HardwareTelemetry(
            cpu_usage=50.0,
            memory_usage=60.0
        )
        
        result = telemetry.to_dict()
        
        assert isinstance(result, dict)
        assert result['cpu_usage'] == 50.0
        assert 'update_time' in result


class TestAPICostData:
    """APICostData数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        cost = APICostData()
        
        assert cost.today_cost == 0.0
        assert cost.month_cost == 0.0
        assert cost.daily_limit == 50.0
        assert cost.monthly_limit == 1500.0
    
    def test_custom_values(self):
        """测试自定义值"""
        cost = APICostData(
            today_cost=35.50,
            month_cost=856.20,
            today_calls=1256,
            month_calls=38520
        )
        
        assert cost.today_cost == 35.50
        assert cost.month_cost == 856.20
        assert cost.today_calls == 1256
    
    def test_daily_warning_false(self):
        """测试日预警（未触发）"""
        cost = APICostData(today_cost=30.0, daily_limit=50.0)
        
        assert cost.daily_warning is False
    
    def test_daily_warning_true(self):
        """测试日预警（触发）"""
        cost = APICostData(today_cost=55.0, daily_limit=50.0)
        
        assert cost.daily_warning is True
    
    def test_monthly_warning_false(self):
        """测试月预警（未触发）"""
        cost = APICostData(month_cost=1000.0, monthly_limit=1500.0)
        
        assert cost.monthly_warning is False
    
    def test_monthly_warning_true(self):
        """测试月预警（触发）"""
        cost = APICostData(month_cost=1600.0, monthly_limit=1500.0)
        
        assert cost.monthly_warning is True
    
    def test_to_dict(self):
        """测试转换为字典"""
        cost = APICostData(today_cost=40.0)
        
        result = cost.to_dict()
        
        assert isinstance(result, dict)
        assert result['today_cost'] == 40.0
        assert 'daily_warning' in result


class TestStrategySwitch:
    """StrategySwitch数据模型测试"""
    
    def test_creation(self):
        """测试创建策略开关"""
        switch = StrategySwitch(
            strategy_id="S01",
            strategy_name="动量策略",
            enabled=True,
            position_limit=100.0
        )
        
        assert switch.strategy_id == "S01"
        assert switch.strategy_name == "动量策略"
        assert switch.enabled is True
        assert switch.position_limit == 100.0
    
    def test_default_values(self):
        """测试默认值"""
        switch = StrategySwitch(
            strategy_id="S01",
            strategy_name="动量策略"
        )
        
        assert switch.enabled is True
        assert switch.position_limit == 100.0


class TestHotTuningConfig:
    """HotTuningConfig数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = HotTuningConfig()
        
        assert config.risk_preference == RiskPreference.BALANCED
        assert config.strategy_switches == []
        assert config.global_position_limit == 80.0
    
    def test_custom_values(self):
        """测试自定义值"""
        switches = [
            StrategySwitch("S01", "动量策略", True, 100),
            StrategySwitch("S02", "均值回归", False, 50)
        ]
        
        config = HotTuningConfig(
            risk_preference=RiskPreference.AGGRESSIVE,
            strategy_switches=switches,
            global_position_limit=90.0
        )
        
        assert config.risk_preference == RiskPreference.AGGRESSIVE
        assert len(config.strategy_switches) == 2
        assert config.global_position_limit == 90.0


class TestSystemDashboard:
    """SystemDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return SystemDashboard()
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return SystemDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        mock_redis = Mock()
        dashboard = SystemDashboard(redis_client=mock_redis)
        
        assert dashboard.redis_client is mock_redis
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'success' in dashboard.COLOR_SCHEME
        assert 'warning' in dashboard.COLOR_SCHEME
        assert 'danger' in dashboard.COLOR_SCHEME
        assert 'info' in dashboard.COLOR_SCHEME
    
    def test_get_hardware_telemetry(self, dashboard):
        """测试获取硬件遥测"""
        telemetry = dashboard.get_hardware_telemetry()
        
        assert isinstance(telemetry, HardwareTelemetry)
        assert telemetry.update_time is not None
    
    def test_get_api_cost_data_mock(self, dashboard):
        """测试获取API成本（模拟数据）"""
        cost = dashboard.get_api_cost_data()
        
        assert isinstance(cost, APICostData)
        assert cost.today_cost >= 0
        assert cost.month_cost >= 0
    
    def test_get_hot_tuning_config_mock(self, dashboard):
        """测试获取热调优配置（模拟数据）"""
        config = dashboard.get_hot_tuning_config()
        
        assert isinstance(config, HotTuningConfig)
        assert config.risk_preference in RiskPreference
        assert len(config.strategy_switches) > 0
    
    def test_update_risk_preference_no_confirm(self, dashboard):
        """测试更新风险偏好（未确认）"""
        result = dashboard.update_risk_preference(RiskPreference.AGGRESSIVE, confirm=False)
        
        assert result['success'] is False
        assert result['require_confirm'] is True
    
    def test_update_risk_preference_confirmed(self, dashboard):
        """测试更新风险偏好（已确认）"""
        result = dashboard.update_risk_preference(RiskPreference.AGGRESSIVE, confirm=True)
        
        assert result['success'] is True
        assert result['preference'] == "激进"
    
    def test_update_strategy_switch_no_confirm(self, dashboard):
        """测试更新策略开关（未确认）"""
        result = dashboard.update_strategy_switch("S01", False, confirm=False)
        
        assert result['success'] is False
        assert result['require_confirm'] is True
    
    def test_update_strategy_switch_confirmed(self, dashboard):
        """测试更新策略开关（已确认）"""
        result = dashboard.update_strategy_switch("S01", False, confirm=True)
        
        assert result['success'] is True
        assert result['enabled'] is False
    
    def test_update_position_limit_no_confirm(self, dashboard):
        """测试更新仓位上限（未确认）"""
        result = dashboard.update_position_limit(70.0, confirm=False)
        
        assert result['success'] is False
        assert result['require_confirm'] is True
    
    def test_update_position_limit_confirmed(self, dashboard):
        """测试更新仓位上限（已确认）"""
        result = dashboard.update_position_limit(70.0, confirm=True)
        
        assert result['success'] is True
        assert result['limit'] == 70.0
    
    def test_update_position_limit_invalid(self, dashboard):
        """测试更新仓位上限（无效值）"""
        result = dashboard.update_position_limit(150.0, confirm=True)
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_update_position_limit_strategy_specific(self, dashboard):
        """测试更新策略特定仓位上限"""
        result = dashboard.update_position_limit(60.0, strategy_id="S01", confirm=True)
        
        assert result['success'] is True
    
    def test_get_usage_color_low(self, dashboard):
        """测试使用率颜色（低）"""
        color = dashboard._get_usage_color(50)
        
        assert color == dashboard.COLOR_SCHEME['success']
    
    def test_get_usage_color_medium(self, dashboard):
        """测试使用率颜色（中）"""
        color = dashboard._get_usage_color(75)
        
        assert color == dashboard.COLOR_SCHEME['warning']
    
    def test_get_usage_color_high(self, dashboard):
        """测试使用率颜色（高）"""
        color = dashboard._get_usage_color(95)
        
        assert color == dashboard.COLOR_SCHEME['danger']


class TestSystemDashboardRedis:
    """SystemDashboard Redis集成测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis"""
        return Mock()
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """创建带Redis的测试实例"""
        return SystemDashboard(redis_client=mock_redis)
    
    def test_update_risk_preference_with_redis(self, dashboard, mock_redis):
        """测试更新风险偏好（带Redis）"""
        result = dashboard.update_risk_preference(RiskPreference.CONSERVATIVE, confirm=True)
        
        assert result['success'] is True
        mock_redis.hset.assert_called_once()
    
    def test_redis_error_fallback(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟数据"""
        mock_redis.hgetall.side_effect = Exception("Redis error")
        
        cost = dashboard.get_api_cost_data()
        
        assert isinstance(cost, APICostData)


class TestSystemDashboardEdgeCases:
    """SystemDashboard边界条件测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return SystemDashboard()
    
    def test_position_limit_boundary_zero(self, dashboard):
        """测试仓位上限边界（0）"""
        result = dashboard.update_position_limit(0.0, confirm=True)
        
        assert result['success'] is True
    
    def test_position_limit_boundary_hundred(self, dashboard):
        """测试仓位上限边界（100）"""
        result = dashboard.update_position_limit(100.0, confirm=True)
        
        assert result['success'] is True
    
    def test_position_limit_negative(self, dashboard):
        """测试仓位上限（负值）"""
        result = dashboard.update_position_limit(-10.0, confirm=True)
        
        assert result['success'] is False
    
    def test_api_cost_trend_data(self, dashboard):
        """测试API成本趋势数据"""
        cost = dashboard.get_api_cost_data()
        
        assert isinstance(cost.cost_trend, list)
        if cost.cost_trend:
            assert 'date' in cost.cost_trend[0]
            assert 'cost' in cost.cost_trend[0]
