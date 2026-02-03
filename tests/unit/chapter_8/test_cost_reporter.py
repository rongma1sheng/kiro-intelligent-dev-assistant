"""成本报表生成器单元测试

白皮书依据: 第八章 8.T.1 单元测试要求
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from src.monitoring.cost_reporter import CostReporter


class TestCostReporter:
    """成本报表生成器测试类
    
    白皮书依据: 第八章 8.T.1 单元测试要求
    测试覆盖率目标: 100%
    """
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis客户端"""
        redis = Mock()
        redis.get = MagicMock(return_value=b'0')
        return redis
    
    @pytest.fixture
    def reporter(self, mock_redis):
        """创建成本报表生成器实例"""
        return CostReporter(mock_redis)
    
    def test_init_success(self, mock_redis):
        """测试正常初始化"""
        reporter = CostReporter(mock_redis)
        
        assert reporter.redis == mock_redis
    
    def test_generate_daily_report(self, reporter, mock_redis):
        """测试生成日报表"""
        # 模拟数据
        def mock_get(key):
            if 'model:deepseek-chat' in key:
                return b'10.0'
            elif 'model:qwen-next-80b' in key:
                return b'20.0'
            elif 'model:deepseek-r1' in key:
                return b'5.0'
            elif 'model:qwen-scholar' in key:
                return b'15.0'
            elif 'daily:' in key:
                return b'35.0'
            return b'0'
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        date = datetime(2026, 1, 26)
        report = reporter.generate_daily_report(date)
        
        assert report['date'] == '20260126'
        assert report['total_cost'] == 35.0
        assert report['budget'] == 50.0
        assert report['budget_utilization'] == 0.7
        assert report['exceeded'] is False
        assert 'model_costs' in report
    
    def test_generate_daily_report_exceeded(self, reporter, mock_redis):
        """测试超预算日报表"""
        mock_redis.get = MagicMock(return_value=b'60.0')
        
        date = datetime(2026, 1, 26)
        report = reporter.generate_daily_report(date)
        
        assert report['total_cost'] == 60.0
        assert report['exceeded'] is True
    
    def test_generate_weekly_report(self, reporter, mock_redis):
        """测试生成周报表"""
        # 模拟每天30元
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        end_date = datetime(2026, 1, 26)
        report = reporter.generate_weekly_report(end_date)
        
        assert report['end_date'] == '20260126'
        assert report['total_cost'] == 210.0  # 30 * 7
        assert report['avg_daily_cost'] == 30.0
        assert report['budget'] == 350.0  # 50 * 7
        assert report['budget_utilization'] == 0.6
        assert report['exceeded'] is False
        assert len(report['daily_reports']) == 7
    
    def test_generate_monthly_report(self, reporter, mock_redis):
        """测试生成月报表"""
        # 模拟每天30元
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        report = reporter.generate_monthly_report(2026, 1)
        
        assert report['year'] == 2026
        assert report['month'] == 1
        assert report['days_in_month'] == 31
        assert report['total_cost'] == 930.0  # 30 * 31
        assert report['avg_daily_cost'] == 30.0
        assert report['budget'] == 1500.0
        assert report['budget_utilization'] == 0.62
        assert report['exceeded'] is False
    
    def test_generate_monthly_report_invalid_month(self, reporter):
        """测试无效月份"""
        with pytest.raises(ValueError, match="月份必须在1-12之间"):
            reporter.generate_monthly_report(2026, 0)
        
        with pytest.raises(ValueError, match="月份必须在1-12之间"):
            reporter.generate_monthly_report(2026, 13)
    
    def test_generate_monthly_report_december(self, reporter, mock_redis):
        """测试12月报表（跨年边界）"""
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        report = reporter.generate_monthly_report(2026, 12)
        
        assert report['year'] == 2026
        assert report['month'] == 12
        assert report['days_in_month'] == 31
    
    def test_generate_model_comparison_report(self, reporter, mock_redis):
        """测试生成模型对比报表"""
        # 模拟不同模型的成本
        def mock_get(key):
            if 'deepseek-chat' in key:
                return b'100.0'
            elif 'qwen-next-80b' in key:
                return b'200.0'
            elif 'deepseek-r1' in key:
                return b'50.0'
            elif 'qwen-scholar' in key:
                return b'150.0'
            return b'0'
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        report = reporter.generate_model_comparison_report()
        
        assert report['total_cost'] == 500.0
        assert report['model_costs']['deepseek-chat'] == 100.0
        assert report['model_costs']['qwen-next-80b'] == 200.0
        assert report['model_percentages']['deepseek-chat'] == 20.0
        assert report['model_percentages']['qwen-next-80b'] == 40.0
        assert report['most_expensive'] == 'qwen-next-80b'
    
    def test_generate_model_comparison_report_no_data(self, reporter, mock_redis):
        """测试无数据时的模型对比报表"""
        mock_redis.get = MagicMock(return_value=None)
        
        report = reporter.generate_model_comparison_report()
        
        assert report['total_cost'] == 0.0
        assert all(cost == 0.0 for cost in report['model_costs'].values())
    
    def test_daily_report_model_costs(self, reporter, mock_redis):
        """测试日报表中的模型成本"""
        def mock_get(key):
            if 'deepseek-chat' in key:
                return b'5.0'
            elif 'qwen-next-80b' in key:
                return b'10.0'
            return b'0'
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        date = datetime(2026, 1, 26)
        report = reporter.generate_daily_report(date)
        
        assert report['model_costs']['deepseek-chat'] == 5.0
        assert report['model_costs']['qwen-next-80b'] == 10.0
    
    def test_weekly_report_aggregation(self, reporter, mock_redis):
        """测试周报表聚合"""
        # 模拟变化的日成本
        costs = [b'20.0', b'25.0', b'30.0', b'35.0', b'40.0', b'45.0', b'50.0']
        mock_redis.get = MagicMock(side_effect=costs * 10)  # 重复以覆盖所有调用
        
        end_date = datetime(2026, 1, 26)
        report = reporter.generate_weekly_report(end_date)
        
        # 验证聚合计算
        assert report['total_cost'] > 0
        assert report['avg_daily_cost'] > 0
        assert len(report['daily_reports']) == 7


@pytest.mark.parametrize("year,month,expected_days", [
    (2026, 1, 31),   # 1月31天
    (2026, 2, 28),   # 2月28天（非闰年）
    (2024, 2, 29),   # 2月29天（闰年）
    (2026, 4, 30),   # 4月30天
    (2026, 12, 31),  # 12月31天
])
def test_monthly_report_days(year, month, expected_days):
    """参数化测试：验证月报表天数"""
    mock_redis = Mock()
    mock_redis.get = MagicMock(return_value=b'30.0')
    
    reporter = CostReporter(mock_redis)
    report = reporter.generate_monthly_report(year, month)
    
    assert report['days_in_month'] == expected_days


@pytest.mark.parametrize("total_cost,budget,expected_exceeded", [
    (30.0, 50.0, False),
    (50.0, 50.0, False),
    (60.0, 50.0, True),
    (0.0, 50.0, False),
])
def test_budget_exceeded_logic(total_cost, budget, expected_exceeded):
    """参数化测试：验证超预算逻辑"""
    mock_redis = Mock()
    mock_redis.get = MagicMock(return_value=str(total_cost).encode())
    
    reporter = CostReporter(mock_redis)
    date = datetime(2026, 1, 26)
    report = reporter.generate_daily_report(date)
    
    assert report['exceeded'] == expected_exceeded
