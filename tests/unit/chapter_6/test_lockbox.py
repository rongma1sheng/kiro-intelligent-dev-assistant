"""LockBox单元测试

白皮书依据: 第六章 5.3 资本基因与诺亚方舟
"""

import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

from src.execution.lockbox import (
    LockBox,
    LockBoxConfig,
    LockBoxState,
    SafeAssetType
)


@pytest.fixture
def lockbox_config():
    """LockBox配置fixture"""
    return LockBoxConfig(
        profit_lock_ratio=0.3,
        min_lock_amount=10000.0,
        max_lock_ratio=0.5,
        primary_asset=SafeAssetType.GC001,
        fallback_asset=SafeAssetType.MONEY_ETF,
        auto_lock_enabled=True
    )


@pytest.fixture
def lockbox(lockbox_config):
    """LockBox实例fixture"""
    return LockBox(config=lockbox_config)


class TestLockBoxConfig:
    """LockBox配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = LockBoxConfig()
        
        assert config.profit_lock_ratio == 0.3
        assert config.min_lock_amount == 10000.0
        assert config.max_lock_ratio == 0.5
        assert config.primary_asset == SafeAssetType.GC001
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = LockBoxConfig(
            profit_lock_ratio=0.5,
            min_lock_amount=50000.0,
            primary_asset=SafeAssetType.MONEY_ETF
        )
        
        assert config.profit_lock_ratio == 0.5
        assert config.min_lock_amount == 50000.0
        assert config.primary_asset == SafeAssetType.MONEY_ETF


class TestLockBox:
    """LockBox测试"""
    
    def test_init(self, lockbox):
        """测试初始化"""
        assert lockbox.config.profit_lock_ratio == 0.3
        assert lockbox.state.total_locked_amount == 0.0
        assert lockbox.state.locked_assets == {}
    
    @pytest.mark.asyncio
    async def test_calculate_lockable_profit_no_profit(self, lockbox):
        """测试无盈利时计算可锁定金额"""
        portfolio_data = {
            'daily_pnl': 0,
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_lockable_profit_negative(self, lockbox):
        """测试亏损时计算可锁定金额"""
        portfolio_data = {
            'daily_pnl': -10000,
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_lockable_profit_below_min(self, lockbox):
        """测试盈利低于最小阈值"""
        portfolio_data = {
            'daily_pnl': 20000,  # 30% = 6000 < 10000
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_lockable_profit_normal(self, lockbox):
        """测试正常盈利计算"""
        portfolio_data = {
            'daily_pnl': 100000,  # 30% = 30000 > 10000
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 30000.0  # 100000 * 0.3
    
    @pytest.mark.asyncio
    async def test_calculate_lockable_profit_max_ratio(self, lockbox):
        """测试达到最大锁定比例"""
        lockbox.state.total_locked_amount = 400000  # 已锁定40%
        
        portfolio_data = {
            'daily_pnl': 500000,  # 30% = 150000
            'total_assets': 1000000  # 最多还能锁定100000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 100000.0  # 受最大比例限制
    
    @pytest.mark.asyncio
    async def test_execute_lock_zero_amount(self, lockbox):
        """测试锁定金额为0"""
        result = await lockbox.execute_lock(0)
        
        assert result['success'] is False
        assert result['amount'] == 0
    
    @pytest.mark.asyncio
    async def test_execute_lock_repo_simulation(self, lockbox):
        """测试模拟逆回购锁定"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        assert result['success'] is True
        assert result['amount'] == 50000  # 50000 / 1000 * 1000
        assert result['asset'] == 'GC001'
    
    @pytest.mark.asyncio
    async def test_execute_lock_repo_not_trading_time(self, lockbox):
        """测试非交易时间逆回购"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=False):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        assert result['success'] is False
        assert '非逆回购交易时间' in result['message']
    
    @pytest.mark.asyncio
    async def test_execute_lock_etf_simulation(self, lockbox):
        """测试模拟ETF锁定"""
        result = await lockbox.execute_lock(50000, SafeAssetType.MONEY_ETF)
        
        assert result['success'] is True
        assert result['asset'] == '511880'
    
    @pytest.mark.asyncio
    async def test_execute_lock_updates_state(self, lockbox):
        """测试锁定后状态更新"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        assert lockbox.state.total_locked_amount == 50000
        assert 'GC001' in lockbox.state.locked_assets
        assert lockbox.state.locked_assets['GC001'] == 50000
        assert len(lockbox.state.lock_history) == 1
    
    def test_get_state(self, lockbox):
        """测试获取状态"""
        state = lockbox.get_state()
        
        assert 'total_locked_amount' in state
        assert 'locked_assets' in state
        assert 'config' in state
        assert state['config']['profit_lock_ratio'] == 0.3
    
    def test_get_lock_history(self, lockbox):
        """测试获取锁定历史"""
        history = lockbox.get_lock_history()
        assert history == []
    
    def test_reset_state(self, lockbox):
        """测试重置状态"""
        lockbox.state.total_locked_amount = 100000
        lockbox.state.locked_assets = {'GC001': 100000}
        
        lockbox.reset_state()
        
        assert lockbox.state.total_locked_amount == 0.0
        assert lockbox.state.locked_assets == {}


class TestSafeAssetType:
    """安全资产类型测试"""
    
    def test_repo_types(self):
        """测试逆回购类型"""
        assert SafeAssetType.GC001.value == "GC001"
        assert SafeAssetType.GC002.value == "GC002"
        assert SafeAssetType.GC007.value == "GC007"
    
    def test_etf_types(self):
        """测试ETF类型"""
        assert SafeAssetType.MONEY_ETF.value == "511880"
        assert SafeAssetType.BOND_ETF.value == "511010"


class TestAllSafeAssetTypes:
    """测试所有安全资产类型
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    Requirements: 13.3
    """
    
    @pytest.mark.asyncio
    async def test_gc001_lock(self, lockbox):
        """测试GC001（1天期逆回购）锁定"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        assert result['success'] is True
        assert result['asset'] == 'GC001'
        assert result['amount'] == 50000
    
    @pytest.mark.asyncio
    async def test_gc002_lock(self, lockbox):
        """测试GC002（2天期逆回购）锁定"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC002)
        
        assert result['success'] is True
        assert result['asset'] == 'GC002'
        assert result['amount'] == 50000
    
    @pytest.mark.asyncio
    async def test_gc003_lock(self, lockbox):
        """测试GC003（3天期逆回购）锁定"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC003)
        
        assert result['success'] is True
        assert result['asset'] == 'GC003'
        assert result['amount'] == 50000
    
    @pytest.mark.asyncio
    async def test_gc007_lock(self, lockbox):
        """测试GC007（7天期逆回购）锁定"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC007)
        
        assert result['success'] is True
        assert result['asset'] == 'GC007'
        assert result['amount'] == 50000
    
    @pytest.mark.asyncio
    async def test_money_etf_lock(self, lockbox):
        """测试货币ETF锁定"""
        result = await lockbox.execute_lock(50000, SafeAssetType.MONEY_ETF)
        
        assert result['success'] is True
        assert result['asset'] == '511880'
        assert 'shares' in result
    
    @pytest.mark.asyncio
    async def test_bond_etf_lock(self, lockbox):
        """测试国债ETF锁定"""
        result = await lockbox.execute_lock(50000, SafeAssetType.BOND_ETF)
        
        assert result['success'] is True
        assert result['asset'] == '511010'
        assert 'shares' in result


class TestRepoTradingTime:
    """测试逆回购交易时间验证
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    Requirements: 13.4
    """
    
    def test_morning_trading_time(self, lockbox):
        """测试上午交易时间（9:30-11:30）"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(10, 0)
            assert lockbox._is_repo_trading_time() is True
    
    def test_afternoon_trading_time(self, lockbox):
        """测试下午交易时间（13:00-15:30）"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 0)
            assert lockbox._is_repo_trading_time() is True
    
    def test_before_morning_trading(self, lockbox):
        """测试上午开盘前"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(9, 0)
            assert lockbox._is_repo_trading_time() is False
    
    def test_lunch_break(self, lockbox):
        """测试午休时间"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(12, 0)
            assert lockbox._is_repo_trading_time() is False
    
    def test_after_closing(self, lockbox):
        """测试收盘后"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(16, 0)
            assert lockbox._is_repo_trading_time() is False
    
    def test_morning_boundary_start(self, lockbox):
        """测试上午开盘边界（9:30）"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(9, 30)
            assert lockbox._is_repo_trading_time() is True
    
    def test_morning_boundary_end(self, lockbox):
        """测试上午收盘边界（11:30）"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(11, 30)
            assert lockbox._is_repo_trading_time() is True
    
    def test_afternoon_boundary_start(self, lockbox):
        """测试下午开盘边界（13:00）"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(13, 0)
            assert lockbox._is_repo_trading_time() is True
    
    def test_afternoon_boundary_end(self, lockbox):
        """测试下午收盘边界（15:30）"""
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(15, 30)
            assert lockbox._is_repo_trading_time() is True


class TestETFLockExecution:
    """测试ETF锁定执行细节
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    Requirements: 13.5
    """
    
    @pytest.mark.asyncio
    async def test_etf_price_calculation(self, lockbox):
        """测试ETF价格计算"""
        with patch.object(lockbox, '_get_etf_price', return_value=100.0):
            result = await lockbox.execute_lock(50000, SafeAssetType.MONEY_ETF)
        
        assert result['success'] is True
        assert result['shares'] == 500  # 50000 / 100 = 500股
    
    @pytest.mark.asyncio
    async def test_etf_minimum_shares(self, lockbox):
        """测试ETF最小购买数量（100股）"""
        with patch.object(lockbox, '_get_etf_price', return_value=100.0):
            result = await lockbox.execute_lock(5000, SafeAssetType.MONEY_ETF)
        
        # 5000 / 100 = 50股 < 100股，应该失败
        assert result['success'] is False
        assert '不足购买100股' in result['message']
    
    @pytest.mark.asyncio
    async def test_etf_shares_rounding(self, lockbox):
        """测试ETF股数取整（100股倍数）"""
        with patch.object(lockbox, '_get_etf_price', return_value=100.0):
            result = await lockbox.execute_lock(55000, SafeAssetType.MONEY_ETF)
        
        assert result['success'] is True
        # 55000 / 100 = 550股，取整到500股
        assert result['shares'] == 500
        assert result['amount'] == 50000  # 500 * 100
    
    @pytest.mark.asyncio
    async def test_etf_price_unavailable(self, lockbox):
        """测试ETF价格不可用"""
        with patch.object(lockbox, '_get_etf_price', return_value=0):
            result = await lockbox.execute_lock(50000, SafeAssetType.MONEY_ETF)
        
        assert result['success'] is False
        assert '无法获取ETF价格' in result['message']
    
    @pytest.mark.asyncio
    async def test_repo_minimum_amount(self, lockbox):
        """测试逆回购最小金额（1000元）"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(500, SafeAssetType.GC001)
        
        assert result['success'] is False
        assert '不足1000元' in result['message']
    
    @pytest.mark.asyncio
    async def test_repo_amount_rounding(self, lockbox):
        """测试逆回购金额取整（1000元倍数）"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            result = await lockbox.execute_lock(55000, SafeAssetType.GC001)
        
        assert result['success'] is True
        # 55000 / 1000 = 55，取整到55000
        assert result['amount'] == 55000


class TestMaxLockRatio:
    """测试最大锁定比例
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    Requirements: 13.6
    """
    
    @pytest.mark.asyncio
    async def test_max_lock_ratio_enforcement(self, lockbox):
        """测试最大锁定比例强制执行"""
        lockbox.state.total_locked_amount = 450000  # 已锁定45%
        
        portfolio_data = {
            'daily_pnl': 200000,  # 30% = 60000
            'total_assets': 1000000  # 最多还能锁定50000（5%）
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 50000  # 受最大比例限制
    
    @pytest.mark.asyncio
    async def test_max_lock_ratio_reached(self, lockbox):
        """测试达到最大锁定比例"""
        lockbox.state.total_locked_amount = 500000  # 已锁定50%
        
        portfolio_data = {
            'daily_pnl': 100000,
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0  # 已达到最大比例
    
    @pytest.mark.asyncio
    async def test_max_lock_ratio_exceeded(self, lockbox):
        """测试超过最大锁定比例"""
        lockbox.state.total_locked_amount = 600000  # 已锁定60%
        
        portfolio_data = {
            'daily_pnl': 100000,
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0  # 超过最大比例


class TestAutoLockCheck:
    """测试自动锁定检查
    
    白皮书依据: 第一章 1.3 State 3: 诊疗态
    Requirements: 13.7
    """
    
    @pytest.mark.asyncio
    async def test_auto_lock_disabled(self, lockbox):
        """测试自动锁定禁用"""
        lockbox.config.auto_lock_enabled = False
        
        portfolio_data = {
            'daily_pnl': 100000,
            'total_assets': 1000000
        }
        
        result = await lockbox.auto_lock_check(portfolio_data)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_auto_lock_before_time(self, lockbox):
        """测试自动锁定时间未到"""
        lockbox.config.auto_lock_time = time(15, 30)
        
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 0)
            
            portfolio_data = {
                'daily_pnl': 100000,
                'total_assets': 1000000
            }
            
            result = await lockbox.auto_lock_check(portfolio_data)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_auto_lock_at_time(self, lockbox):
        """测试自动锁定时间到达"""
        lockbox.config.auto_lock_time = time(15, 30)
        
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(15, 30)
            
            with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
                portfolio_data = {
                    'daily_pnl': 100000,
                    'total_assets': 1000000
                }
                
                result = await lockbox.auto_lock_check(portfolio_data)
                assert result is not None
                assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_auto_lock_no_profit(self, lockbox):
        """测试自动锁定无盈利"""
        lockbox.config.auto_lock_time = time(15, 30)
        
        with patch('src.execution.lockbox.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(15, 30)
            
            portfolio_data = {
                'daily_pnl': 0,
                'total_assets': 1000000
            }
            
            result = await lockbox.auto_lock_check(portfolio_data)
            assert result is None


class TestStatePersistence:
    """测试状态持久化
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    Requirements: 13.8
    """
    
    @pytest.mark.asyncio
    async def test_state_updates_after_lock(self, lockbox):
        """测试锁定后状态更新"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        assert lockbox.state.total_locked_amount == 50000
        assert lockbox.state.locked_assets['GC001'] == 50000
        assert lockbox.state.last_lock_time is not None
        assert len(lockbox.state.lock_history) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_locks_accumulate(self, lockbox):
        """测试多次锁定累积"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            await lockbox.execute_lock(50000, SafeAssetType.GC001)
            await lockbox.execute_lock(30000, SafeAssetType.GC001)
        
        assert lockbox.state.total_locked_amount == 80000
        assert lockbox.state.locked_assets['GC001'] == 80000
        assert len(lockbox.state.lock_history) == 2
    
    @pytest.mark.asyncio
    async def test_different_assets_tracked_separately(self, lockbox):
        """测试不同资产分别跟踪"""
        with patch.object(lockbox, '_is_repo_trading_time', return_value=True):
            await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        await lockbox.execute_lock(30000, SafeAssetType.MONEY_ETF)
        
        assert lockbox.state.total_locked_amount == 80000
        assert lockbox.state.locked_assets['GC001'] == 50000
        assert lockbox.state.locked_assets['511880'] == 30000
        assert len(lockbox.state.lock_history) == 2
    
    def test_lock_history_tracking(self, lockbox):
        """测试锁定历史跟踪"""
        lockbox.state.lock_history = [
            {'timestamp': '2024-01-01T10:00:00', 'amount': 50000, 'asset': 'GC001'},
            {'timestamp': '2024-01-02T10:00:00', 'amount': 30000, 'asset': 'GC001'},
            {'timestamp': '2024-01-03T10:00:00', 'amount': 20000, 'asset': '511880'},
        ]
        
        history = lockbox.get_lock_history(limit=2)
        assert len(history) == 2
        assert history[0]['timestamp'] == '2024-01-02T10:00:00'
        assert history[1]['timestamp'] == '2024-01-03T10:00:00'


class TestEdgeCases:
    """测试边界条件
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    Requirements: 13.9
    """
    
    @pytest.mark.asyncio
    async def test_zero_profit(self, lockbox):
        """测试零利润"""
        portfolio_data = {
            'daily_pnl': 0,
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0
    
    @pytest.mark.asyncio
    async def test_negative_profit(self, lockbox):
        """测试负利润（亏损）"""
        portfolio_data = {
            'daily_pnl': -50000,
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0
    
    @pytest.mark.asyncio
    async def test_profit_below_minimum(self, lockbox):
        """测试利润低于最小锁定金额"""
        portfolio_data = {
            'daily_pnl': 20000,  # 30% = 6000 < 10000
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 0.0
    
    @pytest.mark.asyncio
    async def test_profit_exactly_minimum(self, lockbox):
        """测试利润恰好等于最小锁定金额"""
        portfolio_data = {
            'daily_pnl': 33334,  # 30% ≈ 10000
            'total_assets': 1000000
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable >= 10000
    
    @pytest.mark.asyncio
    async def test_very_large_profit(self, lockbox):
        """测试非常大的利润"""
        portfolio_data = {
            'daily_pnl': 10000000,  # 30% = 3000000
            'total_assets': 20000000  # 最多锁定10000000（50%）
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        assert lockable == 3000000  # 不受最大比例限制
    
    @pytest.mark.asyncio
    async def test_zero_total_assets(self, lockbox):
        """测试总资产为0"""
        portfolio_data = {
            'daily_pnl': 10000,
            'total_assets': 0
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        # 应该返回0或抛出异常，取决于实现
        assert lockable >= 0
    
    @pytest.mark.asyncio
    async def test_fallback_asset_on_exception(self, lockbox):
        """测试主资产异常时使用备选资产"""
        # 模拟主资产（GC001）抛出异常
        async def mock_execute_repo_lock(*args, **kwargs):
            raise Exception('逆回购执行异常')
        
        with patch.object(lockbox, '_execute_repo_lock', side_effect=mock_execute_repo_lock):
            result = await lockbox.execute_lock(50000, SafeAssetType.GC001)
        
        # 应该尝试备选资产（MONEY_ETF）
        assert result['success'] is True
        assert result['asset'] == '511880'  # MONEY_ETF
    
    @pytest.mark.asyncio
    async def test_negative_lock_amount(self, lockbox):
        """测试负数锁定金额"""
        result = await lockbox.execute_lock(-10000)
        
        assert result['success'] is False
        assert result['amount'] == 0
