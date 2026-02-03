"""Unit Tests for CircuitBreakerForCosts

白皮书依据: 第十八章 18.4 熔断与降级

测试覆盖:
- 成本限制检查（单次/日/月）
- 熔断器状态管理
- 非关键调用暂停
- 自动重置
- 边界条件和异常情况
"""

import pytest
from datetime import datetime
from src.monitoring.cost_tracker import CostTracker
from src.monitoring.circuit_breaker_costs import CircuitBreakerForCosts


class TestCircuitBreakerForCosts:
    """测试CircuitBreakerForCosts类"""
    
    @pytest.fixture
    def tracker(self):
        """测试夹具：创建成本追踪器"""
        return CostTracker(daily_budget=50.0, monthly_budget=1500.0)
    
    @pytest.fixture
    def breaker(self, tracker):
        """测试夹具：创建成本熔断器"""
        return CircuitBreakerForCosts(
            tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
    
    def test_init_success(self, tracker):
        """测试初始化成功"""
        breaker = CircuitBreakerForCosts(
            tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        assert breaker.cost_tracker == tracker
        assert breaker.per_request_limit == 0.10
        assert breaker.daily_limit == 50.0
        assert breaker.monthly_limit == 1500.0
        assert breaker.is_open is False
    
    def test_init_none_tracker(self):
        """测试初始化失败：None追踪器"""
        with pytest.raises(ValueError, match="cost_tracker不能为None"):
            CircuitBreakerForCosts(
                None,
                per_request_limit=0.10,
                daily_limit=50.0,
                monthly_limit=1500.0
            )
    
    def test_init_invalid_per_request_limit(self, tracker):
        """测试初始化失败：无效的单次请求限制"""
        with pytest.raises(ValueError, match="单次请求成本限制必须 > 0"):
            CircuitBreakerForCosts(
                tracker,
                per_request_limit=0,
                daily_limit=50.0,
                monthly_limit=1500.0
            )
    
    def test_init_invalid_daily_limit(self, tracker):
        """测试初始化失败：无效的日限制"""
        with pytest.raises(ValueError, match="日成本限制必须 > 0"):
            CircuitBreakerForCosts(
                tracker,
                per_request_limit=0.10,
                daily_limit=-10,
                monthly_limit=1500.0
            )
    
    def test_init_invalid_monthly_limit(self, tracker):
        """测试初始化失败：无效的月限制"""
        with pytest.raises(ValueError, match="月成本限制必须 > 0"):
            CircuitBreakerForCosts(
                tracker,
                per_request_limit=0.10,
                daily_limit=50.0,
                monthly_limit=0
            )
    
    def test_check_cost_limit_allow(self, breaker):
        """测试成本限制检查：允许"""
        result = breaker.check_cost_limit(estimated_cost=0.05, is_critical=True)
        
        assert result is True
        assert breaker.total_checks == 1
        assert breaker.blocked_requests == 0
    
    def test_check_cost_limit_per_request_exceeded(self, breaker):
        """测试成本限制检查：单次请求超限"""
        result = breaker.check_cost_limit(estimated_cost=0.20, is_critical=True)
        
        assert result is False
        assert breaker.blocked_requests == 1
    
    def test_check_cost_limit_daily_exceeded_critical(self, breaker, tracker):
        """测试成本限制检查：日限制超限（关键调用）"""
        # 模拟大量调用导致超日限制
        for _ in range(1000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        result = breaker.check_cost_limit(is_critical=True)
        
        # 关键调用即使超限也允许
        assert result is True
        assert breaker.is_open is True
    
    def test_check_cost_limit_daily_exceeded_non_critical(self, breaker, tracker):
        """测试成本限制检查：日限制超限（非关键调用）"""
        # 模拟大量调用导致超日限制
        for _ in range(1000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        result = breaker.check_cost_limit(is_critical=False)
        
        # 非关键调用应该被阻止
        assert result is False
        assert breaker.is_open is True
        assert breaker.blocked_requests == 1
    
    def test_check_cost_limit_circuit_open_non_critical(self, breaker):
        """测试成本限制检查：熔断器打开（非关键调用）"""
        # 手动打开熔断器
        breaker.pause_non_critical_calls()
        
        result = breaker.check_cost_limit(is_critical=False)
        
        assert result is False
        assert breaker.blocked_requests == 1
    
    def test_check_cost_limit_circuit_open_critical(self, breaker):
        """测试成本限制检查：熔断器打开（关键调用）"""
        # 手动打开熔断器
        breaker.pause_non_critical_calls()
        
        result = breaker.check_cost_limit(is_critical=True)
        
        # 关键调用即使熔断器打开也允许
        assert result is True
    
    def test_pause_non_critical_calls(self, breaker):
        """测试暂停非关键调用"""
        assert breaker.is_open is False
        
        breaker.pause_non_critical_calls()
        
        assert breaker.is_open is True
        assert breaker.open_reason == 'manual_pause'
        assert breaker.open_count == 1
    
    def test_pause_non_critical_calls_already_open(self, breaker):
        """测试暂停非关键调用：已经打开"""
        breaker.pause_non_critical_calls()
        initial_count = breaker.open_count
        
        breaker.pause_non_critical_calls()
        
        # 不应该增加计数
        assert breaker.open_count == initial_count
    
    def test_resume_calls(self, breaker):
        """测试恢复调用"""
        breaker.pause_non_critical_calls()
        assert breaker.is_open is True
        
        breaker.resume_calls()
        
        assert breaker.is_open is False
        assert breaker.open_reason is None
    
    def test_resume_calls_already_closed(self, breaker):
        """测试恢复调用：已经关闭"""
        assert breaker.is_open is False
        
        breaker.resume_calls()
        
        # 不应该有副作用
        assert breaker.is_open is False
    
    def test_get_status(self, breaker, tracker):
        """测试获取熔断器状态"""
        tracker.track_api_call('deepseek-chat', 10000, 5000)
        
        status = breaker.get_status()
        
        assert 'is_open' in status
        assert 'open_reason' in status
        assert 'open_timestamp' in status
        assert 'per_request_limit' in status
        assert 'daily_limit' in status
        assert 'monthly_limit' in status
        assert 'current_daily_cost' in status
        assert 'current_monthly_cost' in status
        
        assert status['is_open'] is False
        assert status['per_request_limit'] == 0.10
        assert status['daily_limit'] == 50.0
        assert status['monthly_limit'] == 1500.0
    
    def test_get_status_open(self, breaker):
        """测试获取熔断器状态：打开"""
        breaker.pause_non_critical_calls()
        
        status = breaker.get_status()
        
        assert status['is_open'] is True
        assert status['open_reason'] == 'manual_pause'
        assert status['open_timestamp'] is not None
    
    def test_get_statistics(self, breaker):
        """测试获取统计信息"""
        breaker.check_cost_limit(estimated_cost=0.05, is_critical=True)
        breaker.check_cost_limit(estimated_cost=0.20, is_critical=True)
        
        stats = breaker.get_statistics()
        
        assert stats['total_checks'] == 2
        assert stats['blocked_requests'] == 1
        assert stats['open_count'] == 0
        assert stats['is_open'] is False
        assert stats['block_rate'] == 0.5
    
    def test_reset_statistics(self, breaker):
        """测试重置统计信息"""
        breaker.check_cost_limit(estimated_cost=0.05, is_critical=True)
        breaker.check_cost_limit(estimated_cost=0.20, is_critical=True)
        
        assert breaker.total_checks == 2
        assert breaker.blocked_requests == 1
        
        breaker.reset_statistics()
        
        assert breaker.total_checks == 0
        assert breaker.blocked_requests == 0
        assert breaker.open_count == 0
    
    def test_auto_reset_if_possible_not_open(self, breaker):
        """测试自动重置：未打开"""
        result = breaker.auto_reset_if_possible()
        assert result is False
    
    def test_auto_reset_if_possible_can_reset(self, breaker, tracker):
        """测试自动重置：可以重置"""
        # 打开熔断器
        breaker.pause_non_critical_calls()
        assert breaker.is_open is True
        
        # 成本低于90%限制，应该可以重置
        result = breaker.auto_reset_if_possible()
        
        assert result is True
        assert breaker.is_open is False
    
    def test_auto_reset_if_possible_cannot_reset(self, breaker, tracker):
        """测试自动重置：不能重置"""
        # 模拟大量调用导致超限
        for _ in range(1000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        # 打开熔断器
        breaker.pause_non_critical_calls()
        assert breaker.is_open is True
        
        # 成本超过90%限制，不应该重置
        result = breaker.auto_reset_if_possible()
        
        assert result is False
        assert breaker.is_open is True
    
    def test_open_circuit_reason(self, breaker):
        """测试打开熔断器：记录原因"""
        breaker._open_circuit('test_reason', 100.0)
        
        assert breaker.is_open is True
        assert breaker.open_reason == 'test_reason'
        assert breaker.open_timestamp is not None
        assert breaker.open_count == 1
    
    def test_open_circuit_already_open(self, breaker):
        """测试打开熔断器：已经打开"""
        breaker._open_circuit('reason1', 100.0)
        initial_count = breaker.open_count
        
        breaker._open_circuit('reason2', 200.0)
        
        # 不应该增加计数
        assert breaker.open_count == initial_count
        assert breaker.open_reason == 'reason1'  # 保持第一次的原因
    
    def test_close_circuit(self, breaker):
        """测试关闭熔断器"""
        breaker._open_circuit('test_reason', 100.0)
        assert breaker.is_open is True
        
        breaker._close_circuit()
        
        assert breaker.is_open is False
        assert breaker.open_reason is None
        assert breaker.open_timestamp is None
    
    def test_monthly_limit_exceeded(self, breaker, tracker):
        """测试月限制超限"""
        # 模拟大量调用导致超月限制
        for _ in range(3000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        result = breaker.check_cost_limit(is_critical=False)
        
        # 应该被阻止
        assert result is False
        assert breaker.is_open is True
    
    def test_no_estimated_cost(self, breaker):
        """测试成本限制检查：无预估成本"""
        result = breaker.check_cost_limit(estimated_cost=None, is_critical=True)
        
        # 不检查单次成本，应该允许
        assert result is True

    def test_monthly_limit_exceeded_non_critical_blocked(self, breaker, tracker):
        """测试月限制超限时非关键调用被阻止"""
        # 模拟大量调用导致超月限制
        for _ in range(3000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        # 非关键调用应该被阻止
        result = breaker.check_cost_limit(estimated_cost=0.05, is_critical=False)
        
        assert result is False
        assert breaker.is_open is True
        assert breaker.blocked_requests > 0
