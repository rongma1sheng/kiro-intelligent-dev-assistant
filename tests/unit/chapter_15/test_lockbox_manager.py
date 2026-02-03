"""Unit tests for LockBoxManager

白皮书依据: 第十五章 15.1 LockBox实体化交易

测试覆盖:
- 利润锁定执行
- 可用资金获取
- GC001订单构建
- 锁定历史记录
- 转移金额计算
"""

import pytest
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime
from src.core.lockbox_manager import LockBoxManager


class TestLockBoxManager:
    """LockBoxManager单元测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis客户端"""
        redis = Mock()
        redis.get = Mock(return_value='100000.0')
        redis.hset = Mock()
        redis.incrbyfloat = Mock()
        redis.hgetall = Mock(return_value={})
        return redis
    
    @pytest.fixture
    def mock_broker(self):
        """Mock券商接口"""
        broker = Mock()
        broker.submit_order = Mock(return_value={
            'status': 'success',
            'order_id': 'ORDER_123456'
        })
        return broker
    
    @pytest.fixture
    def manager(self, mock_redis, mock_broker):
        """创建LockBoxManager实例"""
        return LockBoxManager(mock_redis, mock_broker)
    
    # 初始化测试
    def test_init_success(self, mock_redis, mock_broker):
        """测试正常初始化"""
        manager = LockBoxManager(mock_redis, mock_broker)
        
        assert manager.redis == mock_redis
        assert manager.broker == mock_broker
        assert manager.min_transfer_amount == 10000.0
        assert manager.gc001_symbol == '204001'
        assert manager.gc001_exchange == 'SSE'
        assert manager.gc001_unit == 1000
    
    def test_init_redis_none(self, mock_broker):
        """测试Redis为None时初始化失败"""
        with pytest.raises(ValueError, match="redis_client不能为None"):
            LockBoxManager(None, mock_broker)
    
    def test_init_broker_none(self, mock_redis):
        """测试broker为None时初始化失败"""
        with pytest.raises(ValueError, match="broker不能为None"):
            LockBoxManager(mock_redis, None)
    
    # 利润锁定执行测试
    def test_execute_lockbox_transfer_success(self, manager, mock_redis, mock_broker):
        """测试成功执行利润锁定"""
        # 设置可用资金
        mock_redis.get.return_value = '50000.0'
        
        # 执行锁定
        result = manager.execute_lockbox_transfer(30000.0)
        
        # 验证结果
        assert result is not None
        assert result['status'] == 'success'
        assert result['order_id'] == 'ORDER_123456'
        assert result['amount'] == 30000.0
        assert result['symbol'] == '204001'
        
        # 验证订单提交
        mock_broker.submit_order.assert_called_once()
        
        # 验证Redis记录
        assert mock_redis.hset.called
        assert mock_redis.incrbyfloat.called
    
    def test_execute_lockbox_transfer_amount_too_small(self, manager, mock_redis):
        """测试转移金额过小"""
        # 设置可用资金
        mock_redis.get.return_value = '5000.0'
        
        # 执行锁定
        result = manager.execute_lockbox_transfer(5000.0)
        
        # 验证结果
        assert result is None
    
    def test_execute_lockbox_transfer_insufficient_cash(self, manager, mock_redis, mock_broker):
        """测试可用资金不足"""
        # 设置可用资金
        mock_redis.get.return_value = '15000.0'
        
        # 执行锁定（请求30000，但只有15000）
        result = manager.execute_lockbox_transfer(30000.0)
        
        # 验证结果
        assert result is not None
        assert result['amount'] == 15000.0  # 实际转移15000
    
    def test_execute_lockbox_transfer_invalid_amount(self, manager):
        """测试无效的转移金额"""
        with pytest.raises(ValueError, match="转移金额必须 > 0"):
            manager.execute_lockbox_transfer(0)
        
        with pytest.raises(ValueError, match="转移金额必须 > 0"):
            manager.execute_lockbox_transfer(-1000)
    
    def test_execute_lockbox_transfer_broker_failure(self, manager, mock_redis, mock_broker):
        """测试券商提交失败"""
        # 设置可用资金
        mock_redis.get.return_value = '50000.0'
        
        # 设置券商返回失败
        mock_broker.submit_order.return_value = {
            'status': 'failed',
            'message': 'Network error'
        }
        
        # 执行锁定
        result = manager.execute_lockbox_transfer(30000.0)
        
        # 验证结果
        assert result is None
    
    def test_execute_lockbox_transfer_broker_exception(self, manager, mock_redis, mock_broker):
        """测试券商抛出异常"""
        # 设置可用资金
        mock_redis.get.return_value = '50000.0'
        
        # 设置券商抛出异常
        mock_broker.submit_order.side_effect = Exception("Connection timeout")
        
        # 执行锁定
        result = manager.execute_lockbox_transfer(30000.0)
        
        # 验证结果
        assert result is None
    
    # 可用资金获取测试
    def test_get_available_cash_success(self, manager, mock_redis):
        """测试成功获取可用资金"""
        mock_redis.get.return_value = '123456.78'
        
        cash = manager._get_available_cash()
        
        assert cash == 123456.78
        mock_redis.get.assert_called_once_with('portfolio:available_cash')
    
    def test_get_available_cash_key_not_exists(self, manager, mock_redis):
        """测试键不存在"""
        mock_redis.get.return_value = None
        
        cash = manager._get_available_cash()
        
        assert cash == 0.0
    
    def test_get_available_cash_invalid_value(self, manager, mock_redis):
        """测试无效的值"""
        mock_redis.get.return_value = 'invalid'
        
        cash = manager._get_available_cash()
        
        assert cash == 0.0
    
    # GC001订单构建测试
    def test_build_gc001_order(self, manager):
        """测试构建GC001订单"""
        order = manager._build_gc001_order(100000.0)
        
        assert order['symbol'] == '204001'
        assert order['exchange'] == 'SSE'
        assert order['action'] == 'buy'
        assert order['amount'] == 1000  # 100000 / 100000 * 1000
        assert order['price'] == 0
        assert order['order_type'] == 'market'
    
    def test_build_gc001_order_rounding(self, manager):
        """测试订单数量向下取整"""
        # 150000 / 100000 = 1.5，向下取整为1
        order = manager._build_gc001_order(150000.0)
        assert order['amount'] == 1000
        
        # 250000 / 100000 = 2.5，向下取整为2
        order = manager._build_gc001_order(250000.0)
        assert order['amount'] == 2000
    
    # 锁定历史记录测试
    def test_record_transfer(self, manager, mock_redis):
        """测试记录锁定历史"""
        manager._record_transfer(30000.0, 'ORDER_123')
        
        # 验证hset调用
        assert mock_redis.hset.called
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "mia:lockbox"
        
        # 验证incrbyfloat调用
        mock_redis.incrbyfloat.assert_called_once_with(
            'lockbox:total_locked',
            30000.0
        )
    
    def test_record_transfer_exception(self, manager, mock_redis):
        """测试记录失败不影响主流程"""
        mock_redis.hset.side_effect = Exception("Redis error")
        
        # 不应抛出异常
        manager._record_transfer(30000.0, 'ORDER_123')
    
    # 累计锁定总额测试
    def test_get_total_locked_success(self, manager, mock_redis):
        """测试获取累计锁定总额"""
        mock_redis.get.return_value = '500000.0'
        
        total = manager.get_total_locked()
        
        assert total == 500000.0
        mock_redis.get.assert_called_once_with('lockbox:total_locked')
    
    def test_get_total_locked_key_not_exists(self, manager, mock_redis):
        """测试键不存在"""
        mock_redis.get.return_value = None
        
        total = manager.get_total_locked()
        
        assert total == 0.0
    
    def test_get_total_locked_invalid_value(self, manager, mock_redis):
        """测试无效的值"""
        mock_redis.get.return_value = 'invalid'
        
        total = manager.get_total_locked()
        
        assert total == 0.0
    
    # 锁定历史查询测试
    def test_get_transfer_history_success(self, manager, mock_redis):
        """测试获取锁定历史"""
        # 模拟Redis返回
        mock_redis.hgetall.return_value = {
            'transfer_2024-01-01T10:00:00': json.dumps({
                'amount': 30000.0,
                'order_id': 'ORDER_1',
                'timestamp': '2024-01-01T10:00:00'
            }),
            'transfer_2024-01-01T11:00:00': json.dumps({
                'amount': 20000.0,
                'order_id': 'ORDER_2',
                'timestamp': '2024-01-01T11:00:00'
            })
        }
        
        history = manager.get_transfer_history(limit=10)
        
        assert len(history) == 2
        assert history[0]['timestamp'] == '2024-01-01T11:00:00'  # 最新的在前
        assert history[1]['timestamp'] == '2024-01-01T10:00:00'
    
    def test_get_transfer_history_limit(self, manager, mock_redis):
        """测试历史记录数量限制"""
        # 模拟5条记录
        records = {}
        for i in range(5):
            records[f'transfer_{i}'] = json.dumps({
                'amount': 10000.0,
                'order_id': f'ORDER_{i}',
                'timestamp': f'2024-01-01T{i:02d}:00:00'
            })
        
        mock_redis.hgetall.return_value = records
        
        history = manager.get_transfer_history(limit=3)
        
        assert len(history) == 3
    
    def test_get_transfer_history_empty(self, manager, mock_redis):
        """测试空历史记录"""
        mock_redis.hgetall.return_value = {}
        
        history = manager.get_transfer_history()
        
        assert history == []
    
    def test_get_transfer_history_invalid_json(self, manager, mock_redis):
        """测试无效的JSON记录"""
        mock_redis.hgetall.return_value = {
            'transfer_1': 'invalid json',
            'transfer_2': json.dumps({
                'amount': 10000.0,
                'order_id': 'ORDER_2',
                'timestamp': '2024-01-01T10:00:00'
            })
        }
        
        history = manager.get_transfer_history()
        
        # 应该只返回有效的记录
        assert len(history) == 1
        assert history[0]['order_id'] == 'ORDER_2'
    
    def test_get_transfer_history_exception(self, manager, mock_redis):
        """测试获取历史异常"""
        mock_redis.hgetall.side_effect = Exception("Redis error")
        
        history = manager.get_transfer_history()
        
        assert history == []
    
    # 转移金额计算测试
    def test_calculate_transfer_amount_default_ratio(self, manager):
        """测试默认转移比例（50%）"""
        amount = manager.calculate_transfer_amount(profit=100000.0)
        
        assert amount == 50000.0
    
    def test_calculate_transfer_amount_custom_ratio(self, manager):
        """测试自定义转移比例"""
        amount = manager.calculate_transfer_amount(
            profit=100000.0,
            transfer_ratio=0.3
        )
        
        assert amount == 30000.0
    
    def test_calculate_transfer_amount_zero_profit(self, manager):
        """测试零利润"""
        amount = manager.calculate_transfer_amount(profit=0.0)
        
        assert amount == 0.0
    
    def test_calculate_transfer_amount_negative_profit(self, manager):
        """测试负利润"""
        with pytest.raises(ValueError, match="利润不能为负数"):
            manager.calculate_transfer_amount(profit=-1000.0)
    
    def test_calculate_transfer_amount_invalid_ratio(self, manager):
        """测试无效的转移比例"""
        with pytest.raises(ValueError, match="转移比例必须在\\[0, 1\\]范围内"):
            manager.calculate_transfer_amount(
                profit=100000.0,
                transfer_ratio=1.5
            )
        
        with pytest.raises(ValueError, match="转移比例必须在\\[0, 1\\]范围内"):
            manager.calculate_transfer_amount(
                profit=100000.0,
                transfer_ratio=-0.1
            )
    
    def test_calculate_transfer_amount_boundary_ratios(self, manager):
        """测试边界转移比例"""
        # 0%
        amount = manager.calculate_transfer_amount(
            profit=100000.0,
            transfer_ratio=0.0
        )
        assert amount == 0.0
        
        # 100%
        amount = manager.calculate_transfer_amount(
            profit=100000.0,
            transfer_ratio=1.0
        )
        assert amount == 100000.0
