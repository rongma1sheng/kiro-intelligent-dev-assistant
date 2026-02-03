"""成本熔断器单元测试

白皮书依据: 第八章 8.T.1 单元测试要求
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from src.monitoring.circuit_breaker import CostCircuitBreaker


class TestCostCircuitBreaker:
    """成本熔断器测试类
    
    白皮书依据: 第八章 8.T.1 单元测试要求
    测试覆盖率目标: 100%
    """
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis客户端"""
        redis = Mock()
        redis.get = MagicMock(return_value=None)
        redis.set = MagicMock()
        redis.delete = MagicMock()
        return redis
    
    @pytest.fixture
    def breaker(self, mock_redis):
        """创建成本熔断器实例"""
        return CostCircuitBreaker(mock_redis)
    
    def test_init_success(self, mock_redis):
        """测试正常初始化"""
        breaker = CostCircuitBreaker(mock_redis, daily_budget=100.0, monthly_budget=3000.0)
        
        assert breaker.redis == mock_redis
        assert breaker.daily_budget == 100.0
        assert breaker.monthly_budget == 3000.0
    
    def test_init_invalid_daily_budget(self, mock_redis):
        """测试无效日预算"""
        with pytest.raises(ValueError, match="日预算必须 > 0"):
            CostCircuitBreaker(mock_redis, daily_budget=0)
        
        with pytest.raises(ValueError, match="日预算必须 > 0"):
            CostCircuitBreaker(mock_redis, daily_budget=-10)
    
    def test_init_invalid_monthly_budget(self, mock_redis):
        """测试无效月预算"""
        with pytest.raises(ValueError, match="月预算必须 > 0"):
            CostCircuitBreaker(mock_redis, monthly_budget=0)
        
        with pytest.raises(ValueError, match="月预算必须 > 0"):
            CostCircuitBreaker(mock_redis, monthly_budget=-100)
    
    def test_check_budget_normal(self, breaker, mock_redis):
        """测试正常预算检查"""
        # 模拟日成本30元，未超预算
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        result = breaker.check_budget()
        
        assert result is True
        # 熔断器不应该被打开
        mock_redis.set.assert_not_called()
    
    def test_check_budget_exceeded(self, breaker, mock_redis):
        """测试超预算检查"""
        # 模拟日成本60元，超过预算50元
        mock_redis.get = MagicMock(return_value=b'60.0')
        
        result = breaker.check_budget()
        
        assert result is False
        # 熔断器应该被打开
        mock_redis.set.assert_called_with('cost:circuit_breaker', 'open')
    
    def test_check_budget_exactly_at_limit(self, breaker, mock_redis):
        """测试刚好达到预算限制"""
        # 模拟日成本刚好50元
        mock_redis.get = MagicMock(return_value=b'50.0')
        
        result = breaker.check_budget()
        
        # 刚好等于预算，不触发熔断
        assert result is True
    
    def test_is_open_when_closed(self, breaker, mock_redis):
        """测试熔断器关闭状态"""
        mock_redis.get = MagicMock(return_value=None)
        
        result = breaker.is_open()
        
        assert result is False
    
    def test_is_open_when_open(self, breaker, mock_redis):
        """测试熔断器打开状态"""
        mock_redis.get = MagicMock(return_value=b'open')
        
        result = breaker.is_open()
        
        assert result is True
    
    def test_is_open_with_string_value(self, breaker, mock_redis):
        """测试字符串类型的熔断器状态"""
        mock_redis.get = MagicMock(return_value='open')
        
        result = breaker.is_open()
        
        assert result is True
    
    def test_close(self, breaker, mock_redis):
        """测试关闭熔断器"""
        breaker.close()
        
        mock_redis.delete.assert_called_with('cost:circuit_breaker')
    
    def test_get_status_normal(self, breaker, mock_redis):
        """测试获取正常状态"""
        # 模拟日成本30元，熔断器关闭
        def mock_get(key):
            if 'daily:' in key:
                return b'30.0'
            return None
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        status = breaker.get_status()
        
        assert status['is_open'] is False
        assert status['daily_cost'] == 30.0
        assert status['daily_budget'] == 50.0
        assert status['daily_remaining'] == 20.0
        assert status['daily_utilization'] == 0.6
    
    def test_get_status_exceeded(self, breaker, mock_redis):
        """测试获取超预算状态"""
        # 模拟日成本60元，熔断器打开
        def mock_get(key):
            if 'daily:' in key:
                return b'60.0'
            elif 'circuit_breaker' in key:
                return b'open'
            return None
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        status = breaker.get_status()
        
        assert status['is_open'] is True
        assert status['daily_cost'] == 60.0
        assert status['daily_remaining'] == 0.0  # 不能为负
        assert status['daily_utilization'] == 1.2
    
    def test_force_open(self, breaker, mock_redis):
        """测试强制打开熔断器"""
        breaker.force_open()
        
        mock_redis.set.assert_called_with('cost:circuit_breaker', 'open')
    
    def test_check_budget_zero_cost(self, breaker, mock_redis):
        """测试零成本情况"""
        mock_redis.get = MagicMock(return_value=b'0.0')
        
        result = breaker.check_budget()
        
        assert result is True
    
    def test_check_budget_no_data(self, breaker, mock_redis):
        """测试无数据情况"""
        mock_redis.get = MagicMock(return_value=None)
        
        result = breaker.check_budget()
        
        # 无数据视为0成本，不触发熔断
        assert result is True
    
    def test_multiple_check_budget_calls(self, breaker, mock_redis):
        """测试多次检查预算"""
        # 第一次检查：正常
        mock_redis.get = MagicMock(return_value=b'30.0')
        assert breaker.check_budget() is True
        
        # 第二次检查：超预算
        mock_redis.get = MagicMock(return_value=b'60.0')
        assert breaker.check_budget() is False
        
        # 第三次检查：恢复正常
        mock_redis.get = MagicMock(return_value=b'40.0')
        assert breaker.check_budget() is True
    
    def test_get_status_with_zero_budget(self):
        """测试零预算情况（边界条件）"""
        mock_redis = Mock()
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        # 这应该在初始化时就失败
        with pytest.raises(ValueError):
            CostCircuitBreaker(mock_redis, daily_budget=0)


@pytest.mark.parametrize("daily_cost,daily_budget,expected_result", [
    (30.0, 50.0, True),   # 正常
    (50.0, 50.0, True),   # 刚好达到
    (60.0, 50.0, False),  # 超预算
    (0.0, 50.0, True),    # 零成本
    (100.0, 50.0, False), # 严重超预算
])
def test_check_budget_scenarios(daily_cost, daily_budget, expected_result):
    """参数化测试：验证预算检查场景"""
    mock_redis = Mock()
    mock_redis.get = MagicMock(return_value=str(daily_cost).encode())
    mock_redis.set = MagicMock()
    
    breaker = CostCircuitBreaker(mock_redis, daily_budget=daily_budget)
    result = breaker.check_budget()
    
    assert result == expected_result


@pytest.mark.parametrize("cost,budget,expected_utilization", [
    (25.0, 50.0, 0.5),
    (50.0, 50.0, 1.0),
    (75.0, 50.0, 1.5),
    (0.0, 50.0, 0.0),
])
def test_utilization_calculation(cost, budget, expected_utilization):
    """参数化测试：验证预算使用率计算"""
    mock_redis = Mock()
    
    def mock_get(key):
        if 'daily:' in key:
            return str(cost).encode()
        return None
    
    mock_redis.get = MagicMock(side_effect=mock_get)
    
    breaker = CostCircuitBreaker(mock_redis, daily_budget=budget)
    status = breaker.get_status()
    
    assert status['daily_utilization'] == pytest.approx(expected_utilization, rel=0.01)
