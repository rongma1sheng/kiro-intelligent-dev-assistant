"""多账户管理器单元测试

白皮书依据: 第十七章 17.3.1 多账户管理系统
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.execution.multi_account_manager import MultiAccountManager
from src.execution.multi_account_data_models import (
    AccountConfig,
    AccountStatus,
    OrderRoutingResult
)
from src.evolution.qmt_broker_api import QMTConnectionConfig


class TestMultiAccountManager:
    """多账户管理器测试类"""
    
    @pytest.fixture
    def sample_qmt_config(self):
        """创建示例QMT配置"""
        return QMTConnectionConfig(
            account_id='123456',
            password='password',
            mini_qmt_path=r"C:\Program Files\XtMiniQMT"
        )
    
    @pytest.fixture
    def sample_account_config(self, sample_qmt_config):
        """创建示例账户配置"""
        return AccountConfig(
            account_id='test_account_001',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0,
            priority=8
        )
    
    @pytest.fixture
    def manager(self):
        """创建多账户管理器实例"""
        return MultiAccountManager(routing_strategy='balanced')
    
    # ==================== 初始化测试 ====================
    
    def test_init_default(self):
        """测试默认初始化"""
        manager = MultiAccountManager()
        
        assert manager.routing_strategy == 'balanced'
        assert len(manager.accounts) == 0
        assert len(manager.account_configs) == 0
        assert manager.total_orders_routed == 0
    
    def test_init_with_strategy(self):
        """测试指定路由策略初始化"""
        manager = MultiAccountManager(routing_strategy='priority')
        
        assert manager.routing_strategy == 'priority'
    
    def test_init_invalid_strategy(self):
        """测试无效路由策略"""
        with pytest.raises(ValueError, match="不支持的路由策略"):
            MultiAccountManager(routing_strategy='invalid')
    
    # ==================== 账户管理测试 ====================
    
    @pytest.mark.asyncio
    async def test_add_account_success(self, manager, sample_account_config):
        """测试成功添加账户"""
        result = await manager.add_account(sample_account_config, use_mock=True)
        
        assert result is True
        assert 'test_account_001' in manager.accounts
        assert 'test_account_001' in manager.account_configs
        assert manager.get_account_count() == 1
    
    @pytest.mark.asyncio
    async def test_add_account_duplicate(self, manager, sample_account_config):
        """测试添加重复账户"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        with pytest.raises(ValueError, match="账户ID已存在"):
            await manager.add_account(sample_account_config, use_mock=True)
    
    @pytest.mark.asyncio
    async def test_add_account_unsupported_broker(self, sample_qmt_config):
        """测试添加不支持的券商"""
        manager = MultiAccountManager()
        
        config = AccountConfig(
            account_id='test_account_002',
            broker_name='不支持的券商',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0
        )
        
        with pytest.raises(ValueError, match="不支持的券商"):
            await manager.add_account(config, use_mock=False)
    
    @pytest.mark.asyncio
    async def test_remove_account_success(self, manager, sample_account_config):
        """测试成功移除账户"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        result = await manager.remove_account('test_account_001')
        
        assert result is True
        assert 'test_account_001' not in manager.accounts
        assert manager.get_account_count() == 0
    
    @pytest.mark.asyncio
    async def test_remove_account_not_exists(self, manager):
        """测试移除不存在的账户"""
        result = await manager.remove_account('non_existent')
        
        assert result is False
    
    # ==================== 订单路由测试 ====================
    
    @pytest.mark.asyncio
    async def test_route_order_balanced(self, manager, sample_account_config):
        """测试均衡路由策略"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        order = {
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100,
            'price': 1800.0
        }
        
        result = await manager.route_order(order)
        
        assert isinstance(result, OrderRoutingResult)
        assert result.account_id == 'test_account_001'
        assert result.routing_strategy == 'balanced'
        assert 0 <= result.confidence <= 1
        assert manager.total_orders_routed == 1
    
    @pytest.mark.asyncio
    async def test_route_order_priority(self, sample_qmt_config):
        """测试优先级路由策略"""
        manager = MultiAccountManager(routing_strategy='priority')
        
        # 添加两个账户，优先级不同
        config1 = AccountConfig(
            account_id='account_low_priority',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0,
            priority=5
        )
        config2 = AccountConfig(
            account_id='account_high_priority',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0,
            priority=9
        )
        
        await manager.add_account(config1, use_mock=True)
        await manager.add_account(config2, use_mock=True)
        
        order = {
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100
        }
        
        result = await manager.route_order(order)
        
        assert result.account_id == 'account_high_priority'
        assert result.routing_strategy == 'priority'
    
    @pytest.mark.asyncio
    async def test_route_order_hash(self, sample_qmt_config):
        """测试哈希路由策略"""
        manager = MultiAccountManager(routing_strategy='hash')
        
        # 添加两个账户
        config1 = AccountConfig(
            account_id='account_001',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0
        )
        config2 = AccountConfig(
            account_id='account_002',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0
        )
        
        await manager.add_account(config1, use_mock=True)
        await manager.add_account(config2, use_mock=True)
        
        order = {
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100
        }
        
        result = await manager.route_order(order)
        
        assert result.account_id in ['account_001', 'account_002']
        assert result.routing_strategy == 'hash'
        assert result.confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_route_order_no_accounts(self, manager):
        """测试没有可用账户时路由"""
        order = {
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100
        }
        
        with pytest.raises(RuntimeError, match="没有可用账户"):
            await manager.route_order(order)
    
    @pytest.mark.asyncio
    async def test_route_order_missing_fields(self, manager, sample_account_config):
        """测试订单缺少必需字段"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        order = {
            'symbol': '600519.SH'
            # 缺少 side 和 quantity
        }
        
        with pytest.raises(ValueError, match="订单缺少必需字段"):
            await manager.route_order(order)
    
    # ==================== 统计功能测试 ====================
    
    @pytest.mark.asyncio
    async def test_get_total_assets(self, manager, sample_account_config):
        """测试获取总资产"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        total_assets = await manager.get_total_assets()
        
        assert isinstance(total_assets, float)
        assert total_assets >= 0
    
    @pytest.mark.asyncio
    async def test_get_all_positions(self, manager, sample_account_config):
        """测试获取所有持仓"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        positions = await manager.get_all_positions()
        
        assert isinstance(positions, list)
    
    @pytest.mark.asyncio
    async def test_get_all_account_status(self, manager, sample_account_config):
        """测试获取所有账户状态"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        status_dict = await manager.get_all_account_status()
        
        assert isinstance(status_dict, dict)
        assert 'test_account_001' in status_dict
        assert isinstance(status_dict['test_account_001'], AccountStatus)
    
    @pytest.mark.asyncio
    async def test_health_check(self, manager, sample_account_config):
        """测试健康检查"""
        await manager.add_account(sample_account_config, use_mock=True)
        
        health = await manager.health_check()
        
        assert health['total_accounts'] == 1
        assert health['healthy_accounts'] >= 0
        assert health['warning_accounts'] >= 0
        assert health['error_accounts'] >= 0
        assert 'total_assets' in health
        assert 'total_orders_routed' in health
        assert 'routing_distribution' in health
        assert 'details' in health
    
    def test_get_account_count(self, manager):
        """测试获取账户数量"""
        assert manager.get_account_count() == 0
    
    def test_get_routing_stats(self, manager):
        """测试获取路由统计"""
        stats = manager.get_routing_stats()
        
        assert 'total_orders' in stats
        assert 'routing_strategy' in stats
        assert 'distribution' in stats
        assert stats['total_orders'] == 0
        assert stats['routing_strategy'] == 'balanced'
    
    # ==================== 边界条件测试 ====================
    
    @pytest.mark.asyncio
    async def test_multiple_accounts(self, sample_qmt_config):
        """测试管理多个账户"""
        manager = MultiAccountManager()
        
        # 添加3个账户
        for i in range(3):
            config = AccountConfig(
                account_id=f'account_{i:03d}',
                broker_name='国金',
                account_type='模拟盘',
                qmt_config=sample_qmt_config,
                max_capital=10000000.0 * (i + 1),
                priority=5 + i
            )
            await manager.add_account(config, use_mock=True)
        
        assert manager.get_account_count() == 3
        
        # 测试路由
        order = {
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100
        }
        
        result = await manager.route_order(order)
        assert result.account_id in ['account_000', 'account_001', 'account_002']
    
    @pytest.mark.asyncio
    async def test_disabled_account(self, sample_qmt_config):
        """测试禁用的账户不参与路由"""
        manager = MultiAccountManager()
        
        # 添加一个禁用的账户
        config = AccountConfig(
            account_id='disabled_account',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0,
            enabled=False
        )
        await manager.add_account(config, use_mock=True)
        
        # 添加一个启用的账户
        config2 = AccountConfig(
            account_id='enabled_account',
            broker_name='国金',
            account_type='模拟盘',
            qmt_config=sample_qmt_config,
            max_capital=10000000.0,
            enabled=True
        )
        await manager.add_account(config2, use_mock=True)
        
        order = {
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100
        }
        
        result = await manager.route_order(order)
        
        # 应该路由到启用的账户
        assert result.account_id == 'enabled_account'
