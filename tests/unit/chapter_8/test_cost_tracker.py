"""成本追踪器单元测试

白皮书依据: 第八章 8.T.1 单元测试要求
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from src.monitoring.cost_tracker import CostTracker


class TestCostTracker:
    """成本追踪器测试类
    
    白皮书依据: 第八章 8.T.1 单元测试要求
    测试覆盖率目标: 100%
    """
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis客户端"""
        redis = Mock()
        redis.get = MagicMock(return_value=b'0')
        redis.incrbyfloat = MagicMock(return_value=1.0)
        redis.lpush = MagicMock()
        redis.ltrim = MagicMock()
        redis.delete = MagicMock()
        return redis
    
    @pytest.fixture
    def tracker(self, mock_redis):
        """创建成本追踪器实例"""
        return CostTracker(mock_redis)
    
    def test_init_success(self, mock_redis):
        """测试正常初始化"""
        tracker = CostTracker(mock_redis, daily_budget=100.0, monthly_budget=3000.0)
        
        assert tracker.redis == mock_redis
        assert tracker.daily_budget == 100.0
        assert tracker.monthly_budget == 3000.0
        assert 'deepseek-chat' in tracker.prices
        assert tracker.prices['deepseek-chat'] == 0.1
    
    def test_init_invalid_daily_budget(self, mock_redis):
        """测试无效日预算"""
        with pytest.raises(ValueError, match="日预算必须 > 0"):
            CostTracker(mock_redis, daily_budget=0)
        
        with pytest.raises(ValueError, match="日预算必须 > 0"):
            CostTracker(mock_redis, daily_budget=-10)
    
    def test_init_invalid_monthly_budget(self, mock_redis):
        """测试无效月预算"""
        with pytest.raises(ValueError, match="月预算必须 > 0"):
            CostTracker(mock_redis, monthly_budget=0)
        
        with pytest.raises(ValueError, match="月预算必须 > 0"):
            CostTracker(mock_redis, monthly_budget=-100)
    
    def test_track_api_call_success(self, tracker, mock_redis):
        """测试成功追踪API调用"""
        cost = tracker.track_api_call('llm', 'deepseek-chat', 1000, 500)
        
        # 验证成本计算: (1000 + 500) / 1000000 * 0.1 = 0.00015
        assert cost == pytest.approx(0.00015, rel=1e-6)
        
        # 验证Redis调用 (4次: daily, model, service, total)
        assert mock_redis.incrbyfloat.call_count == 4
        today = datetime.now().strftime('%Y%m%d')
        mock_redis.incrbyfloat.assert_any_call(f'cost:daily:{today}', cost)
        mock_redis.incrbyfloat.assert_any_call('cost:model:deepseek-chat', cost)
        mock_redis.incrbyfloat.assert_any_call('cost:total', cost)
    
    def test_track_api_call_invalid_input_tokens(self, tracker):
        """测试无效输入token数"""
        with pytest.raises(ValueError, match="输入token数不能为负"):
            tracker.track_api_call('llm', 'deepseek-chat', -100, 500)
    
    def test_track_api_call_invalid_output_tokens(self, tracker):
        """测试无效输出token数"""
        with pytest.raises(ValueError, match="输出token数不能为负"):
            tracker.track_api_call('llm', 'deepseek-chat', 1000, -500)
    
    def test_track_api_call_unknown_model(self, tracker, mock_redis):
        """测试未知模型（使用默认价格）"""
        cost = tracker.track_api_call('llm', 'unknown-model', 1000, 0)
        
        # 使用默认价格0.1
        assert cost == pytest.approx(0.0001, rel=1e-6)
    
    def test_track_api_call_budget_exceeded(self, tracker, mock_redis):
        """测试超预算触发告警"""
        # 模拟当前成本已超预算
        mock_redis.get = MagicMock(return_value=b'60.0')
        
        tracker.track_api_call('llm', 'deepseek-chat', 1000, 500)
        
        # 验证告警被触发
        assert mock_redis.lpush.called
        assert mock_redis.ltrim.called
    
    def test_get_daily_cost_today(self, tracker, mock_redis):
        """测试获取今日成本"""
        mock_redis.get = MagicMock(return_value=b'25.5')
        
        cost = tracker.get_daily_cost()
        
        assert cost == 25.5
        today = datetime.now().strftime('%Y%m%d')
        mock_redis.get.assert_called_with(f'cost:daily:{today}')
    
    def test_get_daily_cost_specific_date(self, tracker, mock_redis):
        """测试获取指定日期成本"""
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        date = datetime(2026, 1, 15)
        cost = tracker.get_daily_cost(date)
        
        assert cost == 30.0
        mock_redis.get.assert_called_with('cost:daily:20260115')
    
    def test_get_daily_cost_no_data(self, tracker, mock_redis):
        """测试无数据时返回0"""
        mock_redis.get = MagicMock(return_value=None)
        
        cost = tracker.get_daily_cost()
        
        assert cost == 0.0
    
    def test_get_model_cost(self, tracker, mock_redis):
        """测试获取模型成本"""
        mock_redis.get = MagicMock(return_value=b'100.5')
        
        cost = tracker.get_model_cost('deepseek-chat')
        
        assert cost == 100.5
        mock_redis.get.assert_called_with('cost:model:deepseek-chat')
    
    def test_get_total_cost(self, tracker, mock_redis):
        """测试获取总成本"""
        mock_redis.get = MagicMock(return_value=b'500.75')
        
        cost = tracker.get_total_cost()
        
        assert cost == 500.75
        mock_redis.get.assert_called_with('cost:total')
    
    def test_check_budget_normal(self, tracker, mock_redis):
        """测试正常预算检查"""
        # 模拟日成本30，月成本900
        def mock_get(key):
            if 'daily' in key:
                return b'30.0'
            return b'0'
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        result = tracker.check_budget()
        
        assert result['daily_cost'] == 30.0
        assert result['daily_budget'] == 50.0
        assert result['daily_utilization'] == 0.6
        assert result['daily_exceeded'] is False
    
    def test_check_budget_exceeded(self, tracker, mock_redis):
        """测试超预算检查"""
        # 模拟日成本60，超过预算50
        def mock_get(key):
            if 'daily' in key:
                return b'60.0'
            return b'0'
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        result = tracker.check_budget()
        
        assert result['daily_cost'] == 60.0
        assert result['daily_exceeded'] is True
    
    def test_reset_daily_cost(self, tracker, mock_redis):
        """测试重置日成本"""
        tracker.reset_daily_cost()
        
        today = datetime.now().strftime('%Y%m%d')
        mock_redis.delete.assert_called_with(f'cost:daily:{today}')
    
    def test_reset_daily_cost_specific_date(self, tracker, mock_redis):
        """测试重置指定日期成本"""
        date = datetime(2026, 1, 15)
        tracker.reset_daily_cost(date)
        
        mock_redis.delete.assert_called_with('cost:daily:20260115')
    
    def test_trigger_budget_alert(self, tracker, mock_redis):
        """测试预算告警触发"""
        tracker._trigger_budget_alert(60.0)
        
        # 验证告警被记录
        assert mock_redis.lpush.called
        assert mock_redis.ltrim.called
        
        # 验证告警数据
        call_args = mock_redis.lpush.call_args
        assert 'cost:alerts' in call_args[0]
    
    def test_track_multiple_models(self, tracker, mock_redis):
        """测试追踪多个模型"""
        tracker.track_api_call('llm', 'deepseek-chat', 1000, 500)
        tracker.track_api_call('llm', 'qwen-next-80b', 2000, 1000)
        tracker.track_api_call('llm', 'deepseek-r1', 1500, 750)
        
        # 验证每个模型都被追踪 (4次/模型: daily, model, service, total)
        assert mock_redis.incrbyfloat.call_count == 12  # 3个模型 * 4次调用
    
    def test_cost_calculation_precision(self, tracker):
        """测试成本计算精度"""
        # 测试大数值
        cost = tracker.track_api_call('llm', 'qwen-next-80b', 1_000_000, 500_000)
        expected = (1_000_000 + 500_000) / 1_000_000 * 1.0
        assert cost == pytest.approx(expected, rel=1e-9)
        
        # 测试小数值
        cost = tracker.track_api_call('llm', 'deepseek-chat', 10, 5)
        expected = (10 + 5) / 1_000_000 * 0.1
        assert cost == pytest.approx(expected, rel=1e-9)
    
    def test_zero_tokens(self, tracker):
        """测试零token调用"""
        cost = tracker.track_api_call('llm', 'deepseek-chat', 0, 0)
        assert cost == 0.0


@pytest.mark.parametrize("model,price", [
    ('deepseek-chat', 0.1),
    ('qwen-next-80b', 1.0),
    ('deepseek-r1', 0.5),
    ('qwen-scholar', 1.0),
])
def test_model_prices(model, price):
    """参数化测试：验证模型价格"""
    mock_redis = Mock()
    tracker = CostTracker(mock_redis)
    
    assert tracker.prices[model] == price


@pytest.mark.parametrize("input_tokens,output_tokens,model,expected_cost", [
    (1000, 500, 'deepseek-chat', 0.00015),
    (10000, 5000, 'qwen-next-80b', 0.015),
    (5000, 2500, 'deepseek-r1', 0.00375),
    (0, 0, 'deepseek-chat', 0.0),
])
def test_cost_calculations(input_tokens, output_tokens, model, expected_cost):
    """参数化测试：验证成本计算"""
    mock_redis = Mock()
    mock_redis.get = MagicMock(return_value=b'0')
    mock_redis.incrbyfloat = MagicMock()
    
    tracker = CostTracker(mock_redis)
    cost = tracker.track_api_call("llm", model, input_tokens, output_tokens)
    
    assert cost == pytest.approx(expected_cost, rel=1e-6)
