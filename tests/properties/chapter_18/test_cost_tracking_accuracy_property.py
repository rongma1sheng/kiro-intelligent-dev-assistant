"""成本跟踪准确性属性测试

白皮书依据: 第十八章 18.1 成本跟踪

**Property 21: Cost Tracking Accuracy**
**Validates: Requirements 10.1**

测试内容:
1. 个别成本之和等于总成本
2. 服务成本之和等于总成本
3. 多次调用的成本累加准确性
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime

from src.monitoring.cost_tracker import CostTracker


class TestCostTrackingAccuracyProperties:
    """成本跟踪准确性属性测试
    
    **Validates: Requirements 10.1**
    """
    
    @given(
        calls=st.lists(
            st.tuples(
                st.sampled_from(['commander', 'soldier', 'scholar']),  # service
                st.sampled_from(['qwen-30b', 'deepseek-chat', 'qwen-next-80b']),  # model
                st.integers(min_value=100, max_value=10000),  # input_tokens
                st.integers(min_value=50, max_value=5000)  # output_tokens
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_individual_costs_sum_equals_total(self, calls):
        """Property 21: 个别成本之和等于总成本
        
        **Validates: Requirements 10.1**
        
        属性: 所有单次调用成本之和应等于总成本
        """
        # 创建新的跟踪器实例（避免hypothesis重用导致状态污染）
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        # 记录所有调用并收集成本
        individual_costs = []
        
        for service, model, input_tokens, output_tokens in calls:
            cost = tracker.track_api_call(service, model, input_tokens, output_tokens)
            individual_costs.append(cost)
        
        # 获取总成本
        total_cost = tracker.get_daily_cost()
        
        # 验证：个别成本之和 = 总成本
        sum_of_individual = sum(individual_costs)
        assert abs(sum_of_individual - total_cost) < 0.01, \
            f"个别成本之和 ({sum_of_individual:.4f}) 应等于总成本 ({total_cost:.4f})"
    
    @given(
        calls=st.lists(
            st.tuples(
                st.sampled_from(['commander', 'soldier', 'scholar']),
                st.sampled_from(['qwen-30b', 'deepseek-chat']),
                st.integers(min_value=100, max_value=5000),
                st.integers(min_value=50, max_value=2500)
            ),
            min_size=2,
            max_size=15
        )
    )
    @settings(max_examples=50)
    def test_service_costs_sum_equals_total(self, calls):
        """Property: 服务成本之和等于总成本
        
        **Validates: Requirements 10.1**
        
        属性: 所有服务的成本之和应等于总成本
        """
        # 创建新的跟踪器实例
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        # 记录所有调用
        for service, model, input_tokens, output_tokens in calls:
            tracker.track_api_call(service, model, input_tokens, output_tokens)
        
        # 获取总成本
        total_cost = tracker.get_daily_cost()
        
        # 获取各服务成本
        today = datetime.now().strftime('%Y%m%d')
        commander_cost = tracker.get_cost_by_service('commander', today)
        soldier_cost = tracker.get_cost_by_service('soldier', today)
        scholar_cost = tracker.get_cost_by_service('scholar', today)
        
        # 验证：服务成本之和 = 总成本
        sum_of_services = commander_cost + soldier_cost + scholar_cost
        assert abs(sum_of_services - total_cost) < 0.01, \
            f"服务成本之和 ({sum_of_services:.4f}) 应等于总成本 ({total_cost:.4f})"
    
    @given(
        service=st.sampled_from(['commander', 'soldier']),
        model=st.sampled_from(['qwen-30b', 'deepseek-chat']),
        call_count=st.integers(min_value=1, max_value=50),
        input_tokens=st.integers(min_value=100, max_value=5000),
        output_tokens=st.integers(min_value=50, max_value=2500)
    )
    @settings(max_examples=50)
    def test_repeated_calls_accumulate_correctly(
        self,
        service,
        model,
        call_count,
        input_tokens,
        output_tokens
    ):
        """Property: 重复调用的成本正确累加
        
        **Validates: Requirements 10.1**
        
        属性: N次相同调用的总成本应等于单次成本的N倍
        """
        # 创建新的跟踪器实例
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        # 第一次调用获取单次成本
        single_cost = tracker.track_api_call(service, model, input_tokens, output_tokens)
        
        # 重复调用 call_count-1 次
        for _ in range(call_count - 1):
            tracker.track_api_call(service, model, input_tokens, output_tokens)
        
        # 获取总成本
        total_cost = tracker.get_daily_cost()
        
        # 验证：总成本 = 单次成本 * 调用次数
        expected_total = single_cost * call_count
        assert abs(total_cost - expected_total) < 0.01, \
            f"总成本 ({total_cost:.4f}) 应等于单次成本 ({single_cost:.4f}) * {call_count} = {expected_total:.4f}"
    
    @given(
        calls=st.lists(
            st.tuples(
                st.sampled_from(['commander', 'soldier']),
                st.sampled_from(['qwen-30b', 'deepseek-chat']),
                st.integers(min_value=0, max_value=5000),  # 允许0 tokens
                st.integers(min_value=0, max_value=2500)
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_zero_token_calls_have_zero_cost(self, calls):
        """Property: 零token调用的成本为零
        
        **Validates: Requirements 10.1**
        
        属性: 如果input_tokens和output_tokens都为0，成本应为0
        """
        # 创建新的跟踪器实例
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        for service, model, input_tokens, output_tokens in calls:
            cost = tracker.track_api_call(service, model, input_tokens, output_tokens)
            
            if input_tokens == 0 and output_tokens == 0:
                assert cost == 0.0, \
                    f"零token调用的成本应为0，实际: {cost}"
    
    @given(
        calls=st.lists(
            st.tuples(
                st.sampled_from(['commander', 'soldier']),
                st.sampled_from(['qwen-30b', 'deepseek-chat']),
                st.integers(min_value=100, max_value=5000),
                st.integers(min_value=50, max_value=2500)
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_cost_is_non_negative(self, calls):
        """Property: 成本非负
        
        **Validates: Requirements 10.1**
        
        属性: 所有成本值应 >= 0
        """
        # 创建新的跟踪器实例
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        for service, model, input_tokens, output_tokens in calls:
            cost = tracker.track_api_call(service, model, input_tokens, output_tokens)
            assert cost >= 0.0, f"成本不能为负: {cost}"
        
        # 总成本也应非负
        total_cost = tracker.get_daily_cost()
        assert total_cost >= 0.0, f"总成本不能为负: {total_cost}"
    
    @given(
        calls=st.lists(
            st.tuples(
                st.sampled_from(['commander', 'soldier']),
                st.sampled_from(['qwen-30b', 'deepseek-chat']),
                st.integers(min_value=100, max_value=5000),
                st.integers(min_value=50, max_value=2500)
            ),
            min_size=2,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_cost_monotonically_increases(self, calls):
        """Property: 成本单调递增
        
        **Validates: Requirements 10.1**
        
        属性: 每次调用后，总成本应增加（或保持不变，如果是零成本调用）
        """
        # 创建新的跟踪器实例
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        previous_cost = 0.0
        
        for service, model, input_tokens, output_tokens in calls:
            tracker.track_api_call(service, model, input_tokens, output_tokens)
            current_cost = tracker.get_daily_cost()
            
            assert current_cost >= previous_cost, \
                f"成本应单调递增: {current_cost} < {previous_cost}"
            
            previous_cost = current_cost


class TestCostBreakdownAccuracy:
    """成本分解准确性测试"""
    
    @given(
        calls=st.lists(
            st.tuples(
                st.sampled_from(['commander', 'soldier', 'scholar']),
                st.sampled_from(['qwen-30b', 'deepseek-chat', 'qwen-next-80b']),
                st.integers(min_value=100, max_value=5000),
                st.integers(min_value=50, max_value=2500)
            ),
            min_size=1,
            max_size=15
        )
    )
    @settings(max_examples=50)
    def test_breakdown_sum_equals_total(self, calls):
        """Property: 成本分解之和等于总成本
        
        **Validates: Requirements 10.1**
        
        属性: get_cost_breakdown() 返回的所有服务成本之和应等于总成本
        """
        # 创建新的跟踪器实例
        tracker = CostTracker(daily_budget=1000.0, monthly_budget=30000.0)
        
        # 记录所有调用
        for service, model, input_tokens, output_tokens in calls:
            tracker.track_api_call(service, model, input_tokens, output_tokens)
        
        # 获取总成本
        total_cost = tracker.get_daily_cost()
        
        # 获取成本分解
        breakdown = tracker.get_cost_breakdown()
        
        # 验证：分解之和 = 总成本
        breakdown_sum = sum(breakdown.values())
        assert abs(breakdown_sum - total_cost) < 0.01, \
            f"成本分解之和 ({breakdown_sum:.4f}) 应等于总成本 ({total_cost:.4f})"
