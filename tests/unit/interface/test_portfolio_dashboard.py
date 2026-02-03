"""资产与归因仪表盘单元测试

白皮书依据: 附录A 全息指挥台 - 3. 资产与归因 (Portfolio)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.interface.portfolio_dashboard import (
    PortfolioDashboard,
    Position,
    DualTrackComparison,
    StrategyAttribution,
    FactorAttribution
)


class TestPosition:
    """Position数据模型测试"""
    
    def test_creation(self):
        """测试创建持仓"""
        position = Position(
            symbol="000001",
            name="平安银行",
            quantity=10000,
            cost_price=11.50,
            current_price=12.50,
            market_value=125000,
            pnl=10000,
            pnl_pct=8.70,
            position_ratio=25.0,
            strategy_id="S01"
        )
        
        assert position.symbol == "000001"
        assert position.name == "平安银行"
        assert position.quantity == 10000
        assert position.cost_price == 11.50
        assert position.current_price == 12.50
        assert position.market_value == 125000
        assert position.pnl == 10000
        assert position.pnl_pct == 8.70
        assert position.position_ratio == 25.0
        assert position.strategy_id == "S01"
    
    def test_to_dict(self):
        """测试转换为字典"""
        position = Position(
            symbol="000001",
            name="平安银行",
            quantity=10000,
            cost_price=11.50,
            current_price=12.50,
            market_value=125000,
            pnl=10000,
            pnl_pct=8.70,
            position_ratio=25.0
        )
        
        result = position.to_dict()
        
        assert isinstance(result, dict)
        assert result['symbol'] == "000001"
        assert result['quantity'] == 10000
        assert result['pnl'] == 10000
    
    def test_default_strategy_id(self):
        """测试默认策略ID"""
        position = Position(
            symbol="000001",
            name="平安银行",
            quantity=10000,
            cost_price=11.50,
            current_price=12.50,
            market_value=125000,
            pnl=10000,
            pnl_pct=8.70,
            position_ratio=25.0
        )
        
        assert position.strategy_id == ""


class TestDualTrackComparison:
    """DualTrackComparison数据模型测试"""
    
    def test_default_values(self):
        """测试默认值"""
        comparison = DualTrackComparison()
        
        assert comparison.dates == []
        assert comparison.live_nav == []
        assert comparison.sim_nav == []
        assert comparison.slippage == 0.0
        assert comparison.execution_quality == 0.0
    
    def test_custom_values(self):
        """测试自定义值"""
        comparison = DualTrackComparison(
            dates=["2026-01-01", "2026-01-02"],
            live_nav=[1.0, 1.02],
            sim_nav=[1.0, 1.03],
            slippage=0.15,
            execution_quality=92.0
        )
        
        assert len(comparison.dates) == 2
        assert comparison.live_nav[1] == 1.02
        assert comparison.sim_nav[1] == 1.03
        assert comparison.slippage == 0.15
        assert comparison.execution_quality == 92.0


class TestStrategyAttribution:
    """StrategyAttribution数据模型测试"""
    
    def test_creation(self):
        """测试创建策略归因"""
        attribution = StrategyAttribution(
            strategy_id="S01",
            strategy_name="动量策略",
            alpha=0.85,
            beta=0.35,
            total_contribution=1.20,
            contribution_pct=28.5
        )
        
        assert attribution.strategy_id == "S01"
        assert attribution.strategy_name == "动量策略"
        assert attribution.alpha == 0.85
        assert attribution.beta == 0.35
        assert attribution.total_contribution == 1.20
        assert attribution.contribution_pct == 28.5
    
    def test_to_dict(self):
        """测试转换为字典"""
        attribution = StrategyAttribution(
            strategy_id="S01",
            strategy_name="动量策略",
            alpha=0.85,
            beta=0.35,
            total_contribution=1.20,
            contribution_pct=28.5
        )
        
        result = attribution.to_dict()
        
        assert isinstance(result, dict)
        assert result['strategy_id'] == "S01"
        assert result['alpha'] == 0.85
        assert result['contribution_pct'] == 28.5


class TestFactorAttribution:
    """FactorAttribution数据模型测试"""
    
    def test_creation(self):
        """测试创建因子归因"""
        attribution = FactorAttribution(
            factor_name="动量因子",
            contribution=0.35,
            contribution_pct=25.0
        )
        
        assert attribution.factor_name == "动量因子"
        assert attribution.contribution == 0.35
        assert attribution.contribution_pct == 25.0


class TestPortfolioDashboard:
    """PortfolioDashboard测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return PortfolioDashboard()
    
    @pytest.fixture
    def dashboard_with_redis(self):
        """创建带Redis的测试实例"""
        mock_redis = Mock()
        return PortfolioDashboard(redis_client=mock_redis)
    
    def test_init_default(self, dashboard):
        """测试默认初始化"""
        assert dashboard.redis_client is None
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        mock_redis = Mock()
        dashboard = PortfolioDashboard(redis_client=mock_redis)
        
        assert dashboard.redis_client is mock_redis
    
    def test_color_scheme(self, dashboard):
        """测试色彩方案"""
        assert 'rise' in dashboard.COLOR_SCHEME
        assert 'fall' in dashboard.COLOR_SCHEME
        assert dashboard.COLOR_SCHEME['rise'] == '#FF4D4F'
        assert dashboard.COLOR_SCHEME['fall'] == '#52C41A'
        assert 'alpha' in dashboard.COLOR_SCHEME
        assert 'beta' in dashboard.COLOR_SCHEME
    
    def test_get_positions_mock(self, dashboard):
        """测试获取持仓（模拟数据）"""
        positions = dashboard.get_positions()
        
        assert isinstance(positions, list)
        assert len(positions) > 0
        assert all(isinstance(p, Position) for p in positions)
    
    def test_get_positions_sorted_by_market_value(self, dashboard):
        """测试持仓按市值排序"""
        positions = dashboard.get_positions()
        
        for i in range(len(positions) - 1):
            assert positions[i].market_value >= positions[i + 1].market_value
    
    def test_get_dual_track_comparison_mock(self, dashboard):
        """测试获取双轨对比（模拟数据）"""
        comparison = dashboard.get_dual_track_comparison()
        
        assert isinstance(comparison, DualTrackComparison)
        assert len(comparison.dates) > 0
        assert len(comparison.live_nav) == len(comparison.dates)
        assert len(comparison.sim_nav) == len(comparison.dates)
    
    def test_get_strategy_attribution_mock(self, dashboard):
        """测试获取策略归因（模拟数据）"""
        attributions = dashboard.get_strategy_attribution()
        
        assert isinstance(attributions, list)
        assert len(attributions) > 0
        assert all(isinstance(a, StrategyAttribution) for a in attributions)
    
    def test_get_strategy_attribution_sorted(self, dashboard):
        """测试策略归因按贡献排序"""
        attributions = dashboard.get_strategy_attribution()
        
        for i in range(len(attributions) - 1):
            assert attributions[i].total_contribution >= attributions[i + 1].total_contribution
    
    def test_get_factor_attribution_mock(self, dashboard):
        """测试获取因子归因（模拟数据）"""
        attributions = dashboard.get_factor_attribution()
        
        assert isinstance(attributions, list)
        assert len(attributions) > 0
        assert all(isinstance(a, FactorAttribution) for a in attributions)
    
    def test_close_position_no_confirm(self, dashboard):
        """测试平仓（未确认）"""
        result = dashboard.close_position("000001", confirm=False)
        
        assert result['success'] is False
        assert result['require_confirm'] is True
    
    def test_close_position_confirmed(self, dashboard):
        """测试平仓（已确认）"""
        result = dashboard.close_position("000001", confirm=True)
        
        assert result['success'] is True
        assert 'timestamp' in result
    
    def test_close_position_with_redis(self, dashboard_with_redis):
        """测试平仓（带Redis）"""
        result = dashboard_with_redis.close_position("000001", confirm=True)
        
        assert result['success'] is True
        dashboard_with_redis.redis_client.publish.assert_called_once()


class TestPortfolioDashboardRedis:
    """PortfolioDashboard Redis集成测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis"""
        return Mock()
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """创建带Redis的测试实例"""
        return PortfolioDashboard(redis_client=mock_redis)
    
    def test_get_positions_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取持仓"""
        mock_redis.keys.return_value = ['mia:positions:000001', 'mia:positions:600519']
        mock_redis.hgetall.return_value = {
            'symbol': '000001',
            'name': '平安银行',
            'quantity': '10000',
            'cost_price': '11.50',
            'current_price': '12.50',
            'market_value': '125000',
            'pnl': '10000',
            'pnl_pct': '8.70',
            'strategy_id': 'S01'
        }
        
        positions = dashboard.get_positions()
        
        mock_redis.keys.assert_called_once()
        assert len(positions) == 2
    
    def test_get_dual_track_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取双轨对比"""
        mock_redis.lrange.side_effect = [
            [b'1.0', b'1.02'],  # live_nav
            [b'1.0', b'1.03'],  # sim_nav
            [b'2026-01-01', b'2026-01-02']  # dates
        ]
        mock_redis.get.side_effect = ['0.15', '92']
        
        comparison = dashboard.get_dual_track_comparison()
        
        assert comparison.slippage == 0.15
        assert comparison.execution_quality == 92.0
    
    def test_get_strategy_attribution_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取策略归因"""
        mock_redis.keys.return_value = ['mia:attribution:strategy:S01']
        mock_redis.hgetall.return_value = {
            'strategy_id': 'S01',
            'strategy_name': '动量策略',
            'alpha': '0.85',
            'beta': '0.35',
            'total_contribution': '1.20',
            'contribution_pct': '28.5'
        }
        
        attributions = dashboard.get_strategy_attribution()
        
        assert len(attributions) == 1
        assert attributions[0].strategy_id == 'S01'
    
    def test_get_factor_attribution_from_redis(self, dashboard, mock_redis):
        """测试从Redis获取因子归因"""
        mock_redis.hgetall.return_value = {
            '动量因子': '0.35',
            '价值因子': '0.28'
        }
        
        attributions = dashboard.get_factor_attribution()
        
        assert len(attributions) == 2
    
    def test_redis_error_fallback_to_mock(self, dashboard, mock_redis):
        """测试Redis错误时回退到模拟数据"""
        mock_redis.keys.side_effect = Exception("Redis connection error")
        
        positions = dashboard.get_positions()
        
        # 应该回退到模拟数据
        assert isinstance(positions, list)
        assert len(positions) > 0


class TestPortfolioDashboardEdgeCases:
    """PortfolioDashboard边界条件测试"""
    
    @pytest.fixture
    def dashboard(self):
        """创建测试实例"""
        return PortfolioDashboard()
    
    def test_empty_positions(self):
        """测试空持仓"""
        mock_redis = Mock()
        mock_redis.keys.return_value = []
        dashboard = PortfolioDashboard(redis_client=mock_redis)
        
        positions = dashboard.get_positions()
        
        # 空持仓时回退到模拟数据
        assert isinstance(positions, list)
    
    def test_position_with_zero_market_value(self, dashboard):
        """测试市值为零的持仓"""
        position = Position(
            symbol="000001",
            name="平安银行",
            quantity=0,
            cost_price=11.50,
            current_price=12.50,
            market_value=0,
            pnl=0,
            pnl_pct=0,
            position_ratio=0
        )
        
        assert position.market_value == 0
        assert position.position_ratio == 0
    
    def test_negative_pnl(self, dashboard):
        """测试负盈亏"""
        position = Position(
            symbol="000001",
            name="平安银行",
            quantity=10000,
            cost_price=12.50,
            current_price=11.50,
            market_value=115000,
            pnl=-10000,
            pnl_pct=-8.0,
            position_ratio=25.0
        )
        
        assert position.pnl < 0
        assert position.pnl_pct < 0
    
    def test_dual_track_empty_data(self):
        """测试空双轨数据"""
        comparison = DualTrackComparison()
        
        assert len(comparison.dates) == 0
        assert len(comparison.live_nav) == 0
        assert len(comparison.sim_nav) == 0
    
    def test_attribution_zero_contribution(self):
        """测试零贡献归因"""
        attribution = StrategyAttribution(
            strategy_id="S99",
            strategy_name="测试策略",
            alpha=0.0,
            beta=0.0,
            total_contribution=0.0,
            contribution_pct=0.0
        )
        
        assert attribution.total_contribution == 0.0
        assert attribution.contribution_pct == 0.0
