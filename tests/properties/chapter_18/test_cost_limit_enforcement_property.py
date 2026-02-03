"""成本限制执行属性测试

白皮书依据: 第十八章 18.4 成本熔断器

**Property 20: Cost Limit Enforcement**
**Validates: Requirements 10.4, 10.5, 10.6**

测试内容:
1. 超限时调用被阻止
2. 关键调用不受限制
3. 熔断器状态正确转换
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.monitoring.cost_tracker import CostTracker
from src.monitoring.circuit_breaker_costs import CircuitBreakerForCosts


class TestCostLimitEnforcementProperties:
    """成本限制执行属性测试
    
    **Validates: Requirements 10.4, 10.5, 10.6**
    """
    
    @given(
        call_count=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=50)
    def test_calls_blocked_when_daily_limit_exceeded(self, call_count):
        """Property 20: 超日限制时非关键调用被阻止
        
        **Validates: Requirements 10.4, 10.5**
        
        属性: 当日成本超限后，非关键调用应被阻止
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 模拟大量调用直到超限（每次¥0.15）
        calls_needed = int(50.0 / 0.15) + 1  # 超过50元
        
        for _ in range(calls_needed):
            tracker.track_api_call('commander', 'qwen-next-80b', 100000, 50000)
        
        # 验证：非关键调用应被阻止
        for _ in range(call_count):
            result = breaker.check_cost_limit(estimated_cost=0.05, is_critical=False)
            assert result is False, "超限后非关键调用应被阻止"
    
    @given(
        call_count=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=50)
    def test_critical_calls_always_allowed(self, call_count):
        """Property: 关键调用始终允许
        
        **Validates: Requirements 10.4**
        
        属性: 即使超限，关键调用也应被允许
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 模拟大量调用直到超限
        calls_needed = int(50.0 / 0.15) + 1
        
        for _ in range(calls_needed):
            tracker.track_api_call('commander', 'qwen-next-80b', 100000, 50000)
        
        # 验证：关键调用应被允许
        for _ in range(call_count):
            result = breaker.check_cost_limit(estimated_cost=0.05, is_critical=True)
            assert result is True, "关键调用应始终被允许"
    
    @given(
        estimated_cost=st.floats(min_value=0.11, max_value=1.0)
    )
    @settings(max_examples=50)
    def test_per_request_limit_enforced(self, estimated_cost):
        """Property: 单次请求限制被执行
        
        **Validates: Requirements 10.6**
        
        属性: 超过单次请求限制(¥0.10)的调用应被阻止
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 验证：超过单次限制的调用被阻止
        result = breaker.check_cost_limit(estimated_cost=estimated_cost, is_critical=False)
        assert result is False, f"超过单次限制(¥0.10)的调用(¥{estimated_cost:.2f})应被阻止"
    
    @given(
        estimated_cost=st.floats(min_value=0.01, max_value=0.09)
    )
    @settings(max_examples=50)
    def test_within_limit_calls_allowed(self, estimated_cost):
        """Property: 限制内的调用被允许
        
        **Validates: Requirements 10.4, 10.5, 10.6**
        
        属性: 未超限时，调用应被允许
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 验证：限制内的调用被允许
        result = breaker.check_cost_limit(estimated_cost=estimated_cost, is_critical=False)
        assert result is True, f"限制内的调用(¥{estimated_cost:.2f})应被允许"
    
    @given(
        call_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50)
    def test_circuit_opens_when_limit_exceeded(self, call_count):
        """Property: 超限时熔断器打开
        
        **Validates: Requirements 10.4, 10.5**
        
        属性: 超限后，熔断器应处于打开状态
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 模拟大量调用直到超限
        calls_needed = int(50.0 / 0.15) + 1
        
        for _ in range(calls_needed):
            tracker.track_api_call('commander', 'qwen-next-80b', 100000, 50000)
        
        # 触发熔断器检查
        breaker.check_cost_limit(estimated_cost=0.05, is_critical=False)
        
        # 验证：熔断器应打开
        assert breaker.is_open is True, "超限后熔断器应打开"
        
        # 验证：后续非关键调用被阻止
        for _ in range(call_count):
            result = breaker.check_cost_limit(estimated_cost=0.05, is_critical=False)
            assert result is False, "熔断器打开时非关键调用应被阻止"
    
    @given(
        call_count=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50)
    def test_blocked_requests_counted(self, call_count):
        """Property: 被阻止的请求被计数
        
        **Validates: Requirements 10.4, 10.5**
        
        属性: 被阻止的请求数应正确累计
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 模拟大量调用直到超限
        calls_needed = int(50.0 / 0.15) + 1
        
        for _ in range(calls_needed):
            tracker.track_api_call('commander', 'qwen-next-80b', 100000, 50000)
        
        # 记录初始被阻止数
        initial_blocked = breaker.blocked_requests
        
        # 尝试多次非关键调用
        for _ in range(call_count):
            breaker.check_cost_limit(estimated_cost=0.05, is_critical=False)
        
        # 验证：被阻止数增加
        final_blocked = breaker.blocked_requests
        assert final_blocked >= initial_blocked + call_count, \
            f"被阻止请求数应增加至少{call_count}，实际增加: {final_blocked - initial_blocked}"


class TestCircuitBreakerStateTransitions:
    """熔断器状态转换测试"""
    
    def test_initial_state_is_closed(self):
        """Property: 初始状态为关闭
        
        **Validates: Requirements 10.4**
        
        属性: 新创建的熔断器应处于关闭状态
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        assert breaker.is_open is False, "初始状态应为关闭"
    
    def test_pause_opens_circuit(self):
        """Property: 暂停操作打开熔断器
        
        **Validates: Requirements 10.4, 10.5**
        
        属性: pause_non_critical_calls() 应打开熔断器
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        breaker.pause_non_critical_calls()
        assert breaker.is_open is True, "暂停后熔断器应打开"
    
    def test_resume_closes_circuit(self):
        """Property: 恢复操作关闭熔断器
        
        **Validates: Requirements 10.4, 10.5**
        
        属性: resume_calls() 应关闭熔断器
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        # 先打开
        breaker.pause_non_critical_calls()
        assert breaker.is_open is True
        
        # 再关闭
        breaker.resume_calls()
        assert breaker.is_open is False, "恢复后熔断器应关闭"
    
    @given(
        open_close_cycles=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_state_transitions_are_idempotent(self, open_close_cycles):
        """Property: 状态转换是幂等的
        
        **Validates: Requirements 10.4, 10.5**
        
        属性: 多次打开/关闭操作应是幂等的
        """
        # 创建新的跟踪器和熔断器实例
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=50.0,
            monthly_limit=1500.0
        )
        
        for _ in range(open_close_cycles):
            # 打开
            breaker.pause_non_critical_calls()
            assert breaker.is_open is True
            
            # 再次打开（幂等）
            breaker.pause_non_critical_calls()
            assert breaker.is_open is True
            
            # 关闭
            breaker.resume_calls()
            assert breaker.is_open is False
            
            # 再次关闭（幂等）
            breaker.resume_calls()
            assert breaker.is_open is False


class TestMonthlyLimitEnforcement:
    """月限制执行测试"""
    
    @given(
        call_count=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=50)
    def test_monthly_limit_blocks_calls(self, call_count):
        """Property: 超月限制时调用被阻止
        
        **Validates: Requirements 10.4, 10.5, 10.6**
        
        属性: 当月成本超限后，非关键调用应被阻止
        """
        # 创建新的跟踪器和熔断器实例（低月预算）
        tracker = CostTracker(daily_budget=100.0, monthly_budget=100.0)
        breaker = CircuitBreakerForCosts(
            cost_tracker=tracker,
            per_request_limit=0.10,
            daily_limit=100.0,
            monthly_limit=100.0
        )
        
        # 模拟大量调用直到超月限制（每次¥0.15）
        calls_needed = int(100.0 / 0.15) + 1  # 超过100元
        
        for _ in range(calls_needed):
            tracker.track_api_call('commander', 'qwen-next-80b', 100000, 50000)
        
        # 验证：非关键调用应被阻止
        for _ in range(call_count):
            result = breaker.check_cost_limit(estimated_cost=0.05, is_critical=False)
            assert result is False, "超月限制后非关键调用应被阻止"
