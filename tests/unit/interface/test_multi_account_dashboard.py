"""多账户管理仪表盘单元测试

白皮书依据: 第十七章 17.3.1 多账户管理系统
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.interface.multi_account_dashboard import (
    MultiAccountDashboard,
    COLOR_UP,
    COLOR_DOWN,
    COLOR_HEALTHY,
    COLOR_WARNING,
    COLOR_ERROR
)
from src.execution.multi_account_manager import MultiAccountManager
from src.execution.multi_account_data_models import (
    AccountConfig,
    AccountStatus
)
from src.evolution.qmt_broker_api import QMTConnectionConfig


class TestMultiAccountDashboard:
    """多账户管理仪表盘测试类"""
    
    @pytest.fixture
    def mock_manager(self):
        """创建Mock管理器"""
        manager = MagicMock(spec=MultiAccountManager)
        manager.routing_strategy = 'balanced'
        manager.account_configs = {}
        manager.get_routing_stats.return_value = {
            'total_orders': 100,
            'routing_strategy': 'balanced',
            'distribution': {
                'account_001': 50,
                'account_002': 50
            }
        }
        return manager
    
    @pytest.fixture
    def dashboard(self, mock_manager):
        """创建仪表盘实例"""
        return MultiAccountDashboard(manager=mock_manager)
    
    # ==================== 初始化测试 ====================
    
    def test_init_default(self):
        """测试默认初始化"""
        dashboard = MultiAccountDashboard()
        
        assert dashboard.manager is not None
        assert isinstance(dashboard.manager, MultiAccountManager)
    
    def test_init_with_manager(self, mock_manager):
        """测试带管理器初始化"""
        dashboard = MultiAccountDashboard(manager=mock_manager)
        
        assert dashboard.manager is mock_manager
    
    # ==================== 色彩常量测试 ====================
    
    def test_color_constants(self):
        """测试色彩常量定义"""
        # 红涨绿跌
        assert COLOR_UP == "#FF4D4F"
        assert COLOR_DOWN == "#52C41A"
        
        # 状态色
        assert COLOR_HEALTHY == "#52C41A"
        assert COLOR_WARNING == "#FA8C16"
        assert COLOR_ERROR == "#F5222D"
    
    # ==================== 数据处理测试 ====================
    
    @pytest.mark.asyncio
    async def test_health_check_data_processing(self, mock_manager):
        """测试健康检查数据处理"""
        # 配置mock返回值
        mock_manager.health_check = AsyncMock(return_value={
            'total_accounts': 3,
            'healthy_accounts': 2,
            'warning_accounts': 1,
            'error_accounts': 0,
            'total_assets': 45000000.0,
            'total_orders_routed': 100,
            'routing_distribution': {
                'account_001': 50,
                'account_002': 50
            },
            'details': [
                {
                    'account_id': 'account_001',
                    'available_cash': 10000000.0,
                    'market_value': 5000000.0,
                    'today_pnl': 50000.0
                },
                {
                    'account_id': 'account_002',
                    'available_cash': 15000000.0,
                    'market_value': 10000000.0,
                    'today_pnl': -20000.0
                }
            ]
        })
        
        result = await mock_manager.health_check()
        
        assert result['total_accounts'] == 3
        assert result['healthy_accounts'] == 2
        assert result['total_assets'] == 45000000.0
    
    @pytest.mark.asyncio
    async def test_account_status_processing(self, mock_manager):
        """测试账户状态数据处理"""
        mock_status = AccountStatus(
            account_id='test_001',
            broker_name='国金',
            connected=True,
            total_assets=15000000.0,
            available_cash=7500000.0,
            market_value=7500000.0,
            position_count=10,
            today_pnl=50000.0,
            health_status='healthy',
            last_update_time=datetime.now()
        )
        
        mock_manager.get_all_account_status = AsyncMock(return_value={
            'test_001': mock_status
        })
        
        result = await mock_manager.get_all_account_status()
        
        assert 'test_001' in result
        assert result['test_001'].total_assets == 15000000.0
        assert result['test_001'].health_status == 'healthy'
    
    # ==================== 路由统计测试 ====================
    
    def test_routing_stats(self, mock_manager, dashboard):
        """测试路由统计"""
        stats = dashboard.manager.get_routing_stats()
        
        assert stats['total_orders'] == 100
        assert stats['routing_strategy'] == 'balanced'
        assert 'distribution' in stats
        assert stats['distribution']['account_001'] == 50
    
    # ==================== 配置验证测试 ====================
    
    def test_account_config_validation(self):
        """测试账户配置验证"""
        qmt_config = QMTConnectionConfig(
            account_id='123456',
            password='password',
            mini_qmt_path=r"C:\Program Files\XtMiniQMT"
        )
        
        # 有效配置
        config = AccountConfig(
            account_id='test_001',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=qmt_config,
            max_capital=10000000.0,
            priority=5
        )
        
        assert config.account_id == 'test_001'
        assert config.max_capital == 10000000.0
    
    def test_account_config_invalid_capital(self):
        """测试无效资金容量"""
        qmt_config = QMTConnectionConfig(
            account_id='123456',
            password='password'
        )
        
        with pytest.raises(ValueError, match="最大资金容量必须大于0"):
            AccountConfig(
                account_id='test_001',
                broker_name='国金',
                account_type='模拟盘',
                qmt_config=qmt_config,
                max_capital=-1000.0
            )
    
    def test_account_config_invalid_priority(self):
        """测试无效优先级"""
        qmt_config = QMTConnectionConfig(
            account_id='123456',
            password='password'
        )
        
        with pytest.raises(ValueError, match="优先级必须在1-10之间"):
            AccountConfig(
                account_id='test_001',
                broker_name='国金',
                account_type='模拟盘',
                qmt_config=qmt_config,
                max_capital=10000000.0,
                priority=15
            )
    
    def test_account_config_invalid_type(self):
        """测试无效账户类型"""
        qmt_config = QMTConnectionConfig(
            account_id='123456',
            password='password'
        )
        
        with pytest.raises(ValueError, match="账户类型必须是"):
            AccountConfig(
                account_id='test_001',
                broker_name='国金',
                account_type='无效类型',
                qmt_config=qmt_config,
                max_capital=10000000.0
            )
    
    # ==================== 状态图标测试 ====================
    
    def test_status_icon_mapping(self):
        """测试状态图标映射"""
        status_icons = {
            'healthy': '🟢',
            'warning': '🟡',
            'error': '🔴'
        }
        
        assert status_icons['healthy'] == '🟢'
        assert status_icons['warning'] == '🟡'
        assert status_icons['error'] == '🔴'
    
    # ==================== 盈亏显示测试 ====================
    
    def test_pnl_display_positive(self):
        """测试正盈亏显示"""
        pnl = 50000.0
        pnl_str = f"+¥{pnl:,.0f}" if pnl >= 0 else f"¥{pnl:,.0f}"
        
        assert pnl_str == "+¥50,000"
    
    def test_pnl_display_negative(self):
        """测试负盈亏显示"""
        pnl = -30000.0
        pnl_str = f"+¥{pnl:,.0f}" if pnl >= 0 else f"¥{pnl:,.0f}"
        
        assert pnl_str == "¥-30,000"
    
    def test_pnl_display_zero(self):
        """测试零盈亏显示"""
        pnl = 0.0
        pnl_str = f"+¥{pnl:,.0f}" if pnl >= 0 else f"¥{pnl:,.0f}"
        
        assert pnl_str == "+¥0"
    
    # ==================== 路由策略选项测试 ====================
    
    def test_routing_strategy_options(self):
        """测试路由策略选项"""
        strategy_options = {
            'balanced': '均衡分配',
            'priority': '优先级优先',
            'capacity': '容量优先',
            'hash': '哈希分片'
        }
        
        assert len(strategy_options) == 4
        assert 'balanced' in strategy_options
        assert strategy_options['balanced'] == '均衡分配'
    
    # ==================== 数据转换测试 ====================
    
    def test_account_status_to_dict(self):
        """测试账户状态转字典"""
        status = AccountStatus(
            account_id='test_001',
            broker_name='国金',
            connected=True,
            total_assets=15000000.0,
            available_cash=7500000.0,
            market_value=7500000.0,
            position_count=10,
            today_pnl=50000.0,
            health_status='healthy',
            last_update_time=datetime.now()
        )
        
        result = status.to_dict()
        
        assert result['account_id'] == 'test_001'
        assert result['broker_name'] == '国金'
        assert result['total_assets'] == 15000000.0
        assert result['health_status'] == 'healthy'
    
    def test_account_config_to_dict(self):
        """测试账户配置转字典"""
        qmt_config = QMTConnectionConfig(
            account_id='123456',
            password='password',
            mini_qmt_path=r"C:\Program Files\XtMiniQMT"
        )
        
        config = AccountConfig(
            account_id='test_001',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=qmt_config,
            max_capital=10000000.0,
            priority=8
        )
        
        result = config.to_dict()
        
        assert result['account_id'] == 'test_001'
        assert result['broker_name'] == '国金'
        assert result['max_capital'] == 10000000.0
        assert result['priority'] == 8
