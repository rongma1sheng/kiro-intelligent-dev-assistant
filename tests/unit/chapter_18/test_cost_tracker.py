"""Unit Tests for CostTracker

白皮书依据: 第十八章 18.2 成本监控与追踪

测试覆盖:
- API调用成本追踪
- 日/月成本统计
- 按服务统计成本
- 预算超限告警
- 边界条件和异常情况
"""

import pytest
from datetime import datetime, timedelta
from src.monitoring.cost_tracker import CostTracker


class TestCostTracker:
    """测试CostTracker类"""
    
    @pytest.fixture
    def tracker(self):
        """测试夹具：创建成本追踪器实例"""
        return CostTracker(daily_budget=50.0, monthly_budget=1500.0)
    
    def test_init_success(self):
        """测试初始化成功"""
        tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        
        assert tracker.daily_budget == 50.0
        assert tracker.monthly_budget == 1500.0
        assert len(tracker.prices) > 0
        assert tracker.total_calls == 0
        assert tracker._total_cost == 0.0
    
    def test_init_invalid_daily_budget(self):
        """测试初始化失败：无效的日预算"""
        with pytest.raises(ValueError, match="日预算必须 > 0"):
            CostTracker(daily_budget=0, monthly_budget=1500.0)
    
    def test_init_invalid_monthly_budget(self):
        """测试初始化失败：无效的月预算"""
        with pytest.raises(ValueError, match="月预算必须 > 0"):
            CostTracker(daily_budget=50.0, monthly_budget=-100)
    
    def test_track_api_call_success(self, tracker):
        """测试追踪API调用成功"""
        cost = tracker.track_api_call(
            model='deepseek-chat',
            input_tokens=1000,
            output_tokens=500
        )
        
        assert cost > 0
        assert tracker.total_calls == 1
        assert tracker.get_total_cost() == cost
        
        # 验证成本计算：(1000+500)/1000000 * 0.1 = 0.00015
        expected_cost = (1500 / 1_000_000) * 0.1
        assert abs(cost - expected_cost) < 0.0001
    
    def test_track_api_call_negative_input_tokens(self, tracker):
        """测试追踪API调用失败：负数输入token"""
        with pytest.raises(ValueError, match="输入token数不能为负"):
            tracker.track_api_call(
                model='deepseek-chat',
                input_tokens=-100,
                output_tokens=500
            )
    
    def test_track_api_call_negative_output_tokens(self, tracker):
        """测试追踪API调用失败：负数输出token"""
        with pytest.raises(ValueError, match="输出token数不能为负"):
            tracker.track_api_call(
                model='deepseek-chat',
                input_tokens=1000,
                output_tokens=-500
            )
    
    def test_track_api_call_unknown_model(self, tracker):
        """测试追踪API调用：未知模型使用默认价格"""
        cost = tracker.track_api_call(
            model='unknown-model',
            input_tokens=1000,
            output_tokens=500
        )
        
        # 应该使用默认价格0.1
        expected_cost = (1500 / 1_000_000) * 0.1
        assert abs(cost - expected_cost) < 0.0001
    
    def test_track_api_call_multiple_models(self, tracker):
        """测试追踪多个模型的API调用"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        tracker.track_api_call('qwen-next-80b', 2000, 1000)
        tracker.track_api_call('deepseek-r1', 1500, 750)
        
        assert tracker.total_calls == 3
        assert tracker.get_total_cost() > 0
    
    def test_get_daily_cost_today(self, tracker):
        """测试获取今日成本"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        tracker.track_api_call('qwen-next-80b', 2000, 1000)
        
        daily_cost = tracker.get_daily_cost()
        assert daily_cost > 0
        assert daily_cost == tracker.get_total_cost()
    
    def test_get_daily_cost_specific_date(self, tracker):
        """测试获取指定日期成本"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        
        cost = tracker.get_daily_cost()
        assert cost > 0
    
    def test_get_daily_cost_no_data(self, tracker):
        """测试获取成本：无数据"""
        # 使用datetime对象
        old_date = datetime(2020, 1, 1)
        cost = tracker.get_daily_cost(old_date)
        assert cost == 0.0
    
    def test_get_cost_by_service(self, tracker):
        """测试按模型获取成本"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        tracker.track_api_call('deepseek-chat', 2000, 1000)
        tracker.track_api_call('qwen-next-80b', 1000, 500)
        
        deepseek_cost = tracker.get_model_cost('deepseek-chat')
        qwen_cost = tracker.get_model_cost('qwen-next-80b')
        
        # deepseek-chat (0.1/M)，qwen-next-80b (1.0/M)
        # 所以qwen成本更高
        assert qwen_cost > deepseek_cost
    
    def test_get_monthly_cost(self, tracker):
        """测试获取月成本"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        tracker.track_api_call('qwen-next-80b', 2000, 1000)
        
        monthly_cost = tracker.get_monthly_cost()
        assert monthly_cost > 0
        assert monthly_cost == tracker.get_total_cost()
    
    def test_get_monthly_cost_specific_month(self, tracker):
        """测试获取指定月份成本"""
        year_month = datetime.now().strftime('%Y%m')
        tracker.track_api_call('deepseek-chat', 1000, 500)
        
        cost = tracker.get_monthly_cost(year_month)
        assert cost > 0
    
    def test_check_budget(self, tracker):
        """测试检查预算状态"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        
        status = tracker.check_budget()
        
        assert 'daily_cost' in status
        assert 'daily_budget' in status
        assert 'daily_utilization' in status
        assert 'daily_exceeded' in status
        assert 'monthly_cost' in status
        assert 'monthly_budget' in status
        assert 'monthly_utilization' in status
        assert 'monthly_exceeded' in status
        
        assert status['daily_budget'] == 50.0
        assert status['monthly_budget'] == 1500.0
        assert status['daily_exceeded'] is False
    
    def test_check_budget_exceeded(self, tracker):
        """测试检查预算状态：超限"""
        # 模拟大量调用导致超预算
        for _ in range(1000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        status = tracker.check_budget()
        assert status['daily_exceeded'] is True
    
    def test_get_statistics(self, tracker):
        """测试获取统计信息"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        tracker.track_api_call('qwen-next-80b', 2000, 1000)
        
        stats = tracker.get_statistics()
        
        assert stats['total_calls'] == 2
        assert stats['total_cost'] > 0
        assert stats['daily_budget'] == 50.0
        assert stats['monthly_budget'] == 1500.0
    
    def test_get_cost_history(self, tracker):
        """测试获取成本历史"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        
        history = tracker.get_cost_history(days=7)
        
        assert len(history) == 7
        assert isinstance(history, dict)
        
        # 今天应该有成本
        today = datetime.now().strftime('%Y%m%d')
        assert today in history
        assert history[today] > 0
    
    def test_get_cost_history_invalid_days(self, tracker):
        """测试获取成本历史失败：无效天数"""
        with pytest.raises(ValueError, match="天数必须 > 0"):
            tracker.get_cost_history(days=0)
    
    def test_reset_daily_cost(self, tracker):
        """测试重置日成本"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        
        assert tracker.get_daily_cost() > 0
        
        tracker.reset_daily_cost()
        assert tracker.get_daily_cost() == 0.0
    
    def test_clear_all_costs(self, tracker):
        """测试清空所有成本记录"""
        tracker.track_api_call('deepseek-chat', 1000, 500)
        tracker.track_api_call('qwen-next-80b', 2000, 1000)
        
        assert tracker.total_calls == 2
        assert tracker.get_total_cost() > 0
        
        tracker.clear_all_costs()
        
        assert tracker.total_calls == 0
        assert tracker.get_total_cost() == 0.0
    
    def test_add_model_price(self, tracker):
        """测试添加模型价格"""
        tracker.add_model_price('new-model', 2.0)
        
        assert tracker.get_model_price('new-model') == 2.0
    
    def test_add_model_price_empty_model(self, tracker):
        """测试添加模型价格失败：空模型名称"""
        with pytest.raises(ValueError, match="模型名称不能为空"):
            tracker.add_model_price('', 2.0)
    
    def test_add_model_price_negative_price(self, tracker):
        """测试添加模型价格失败：负数价格"""
        with pytest.raises(ValueError, match="价格必须 >= 0"):
            tracker.add_model_price('new-model', -1.0)
    
    def test_get_model_price_existing(self, tracker):
        """测试获取模型价格：存在的模型"""
        price = tracker.get_model_price('deepseek-chat')
        assert price == 0.1
    
    def test_get_model_price_nonexistent(self, tracker):
        """测试获取模型价格：不存在的模型返回默认值"""
        price = tracker.get_model_price('nonexistent-model')
        assert price == 0.1  # 默认价格
    
    def test_budget_alert_triggered(self, tracker):
        """测试预算告警触发"""
        # 模拟大量调用导致超预算
        for _ in range(1000):
            tracker.track_api_call('qwen-next-80b', 100000, 50000)
        
        assert tracker.alert_count > 0
    
    def test_local_model_free(self, tracker):
        """测试本地模型免费"""
        cost = tracker.track_api_call(
            model='local-model',
            input_tokens=1000000,
            output_tokens=1000000
        )
        
        assert cost == 0.0
    
    def test_zero_tokens(self, tracker):
        """测试零token调用"""
        cost = tracker.track_api_call(
            model='deepseek-chat',
            input_tokens=0,
            output_tokens=0
        )
        
        assert cost == 0.0

    def test_reset_daily_cost_with_existing_date(self, tracker):
        """测试重置已存在日期的成本"""
        # 添加一些成本
        tracker.track_api_call('qwen-next-80b', 1000, 500)
        
        # 确认成本存在
        cost_before = tracker.get_daily_cost()
        assert cost_before > 0
        
        # 重置成本
        tracker.reset_daily_cost()
        
        # 确认成本已被删除（返回0）
        cost_after = tracker.get_daily_cost()
        assert cost_after == 0.0
