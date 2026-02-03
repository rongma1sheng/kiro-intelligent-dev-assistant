"""成本预测器单元测试

白皮书依据: 第八章 8.T.1 单元测试要求
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from src.monitoring.cost_predictor import CostPredictor


class TestCostPredictor:
    """成本预测器测试类
    
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
    def predictor(self, mock_redis):
        """创建成本预测器实例"""
        return CostPredictor(mock_redis)
    
    def test_init_success(self, mock_redis):
        """测试正常初始化"""
        predictor = CostPredictor(mock_redis, prediction_window=14)
        
        assert predictor.redis == mock_redis
        assert predictor.prediction_window == 14
    
    def test_init_invalid_window(self, mock_redis):
        """测试无效预测窗口"""
        with pytest.raises(ValueError, match="预测窗口必须 > 0"):
            CostPredictor(mock_redis, prediction_window=0)
        
        with pytest.raises(ValueError, match="预测窗口必须 > 0"):
            CostPredictor(mock_redis, prediction_window=-5)
    
    def test_predict_monthly_cost_with_data(self, predictor, mock_redis):
        """测试有数据时的月度预测"""
        # 模拟7天数据，每天30元
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        result = predictor.predict_monthly_cost()
        
        assert result['avg_daily_cost'] == 30.0
        assert result['predicted_monthly'] == 900.0  # 30 * 30
        assert result['budget_monthly'] == 1500.0
        assert result['budget_utilization'] == 0.6
        assert result['sample_size'] == 7
        assert 0 <= result['confidence'] <= 1
    
    def test_predict_monthly_cost_no_data(self, predictor, mock_redis):
        """测试无数据时的月度预测"""
        mock_redis.get = MagicMock(return_value=None)
        
        result = predictor.predict_monthly_cost()
        
        assert result['avg_daily_cost'] == 0.0
        assert result['predicted_monthly'] == 0.0
        assert result['confidence'] == 0.0
    
    def test_predict_monthly_cost_varying_data(self, predictor, mock_redis):
        """测试变化数据的月度预测"""
        # 模拟变化的日成本
        costs = [b'20.0', b'25.0', b'30.0', b'35.0', b'40.0', b'45.0', b'50.0']
        mock_redis.get = MagicMock(side_effect=costs)
        
        result = predictor.predict_monthly_cost()
        
        # 平均值应该是35
        assert result['avg_daily_cost'] == pytest.approx(35.0, rel=0.01)
        assert result['predicted_monthly'] == pytest.approx(1050.0, rel=0.01)
    
    def test_predict_daily_cost_success(self, predictor, mock_redis):
        """测试日成本预测"""
        mock_redis.get = MagicMock(return_value=b'30.0')
        
        result = predictor.predict_daily_cost(days_ahead=1)
        
        assert result['predicted_cost'] == 30.0
        assert result['days_ahead'] == 1
        assert 0 <= result['confidence'] <= 1
    
    def test_predict_daily_cost_invalid_days(self, predictor):
        """测试无效预测天数"""
        with pytest.raises(ValueError, match="预测天数必须 > 0"):
            predictor.predict_daily_cost(days_ahead=0)
        
        with pytest.raises(ValueError, match="预测天数必须 > 0"):
            predictor.predict_daily_cost(days_ahead=-1)
    
    def test_predict_daily_cost_no_data(self, predictor, mock_redis):
        """测试无数据时的日成本预测"""
        mock_redis.get = MagicMock(return_value=None)
        
        result = predictor.predict_daily_cost()
        
        assert result['predicted_cost'] == 0.0
        assert result['confidence'] == 0.0
    
    def test_predict_model_cost_success(self, predictor, mock_redis):
        """测试模型成本预测"""
        mock_redis.get = MagicMock(return_value=b'300.0')
        
        result = predictor.predict_model_cost('deepseek-chat', days=30)
        
        assert result['model'] == 'deepseek-chat'
        assert result['days'] == 30
        assert result['avg_daily_cost'] == 10.0  # 300 / 30
        assert result['predicted_cost'] == 300.0  # 10 * 30
    
    def test_predict_model_cost_invalid_days(self, predictor):
        """测试无效预测天数"""
        with pytest.raises(ValueError, match="预测天数必须 > 0"):
            predictor.predict_model_cost('deepseek-chat', days=0)
    
    def test_get_recent_daily_costs(self, predictor, mock_redis):
        """测试获取最近日成本"""
        # 模拟5天有数据，2天无数据
        def mock_get(key):
            if '20260126' in key or '20260125' in key:
                return None
            return b'30.0'
        
        mock_redis.get = MagicMock(side_effect=mock_get)
        
        costs = predictor._get_recent_daily_costs(7)
        
        # 应该只返回有数据的5天
        assert len(costs) == 5
        assert all(cost == 30.0 for cost in costs)
    
    def test_calculate_confidence_high(self, predictor):
        """测试高置信度计算（数据稳定）"""
        # 数据非常稳定
        daily_costs = [30.0, 30.1, 29.9, 30.0, 30.1]
        
        confidence = predictor._calculate_confidence(daily_costs)
        
        # 变异系数很小，置信度应该很高
        assert confidence > 0.85
    
    def test_calculate_confidence_low(self, predictor):
        """测试低置信度计算（数据波动大）"""
        # 数据波动很大
        daily_costs = [10.0, 50.0, 20.0, 60.0, 30.0]
        
        confidence = predictor._calculate_confidence(daily_costs)
        
        # 变异系数很大，置信度应该较低
        assert confidence < 0.7
    
    def test_calculate_confidence_single_value(self, predictor):
        """测试单个数据点的置信度"""
        daily_costs = [30.0]
        
        confidence = predictor._calculate_confidence(daily_costs)
        
        # 单个数据点，返回默认置信度
        assert confidence == 0.5
    
    def test_calculate_confidence_zero_mean(self, predictor):
        """测试零均值的置信度"""
        daily_costs = [0.0, 0.0, 0.0]
        
        confidence = predictor._calculate_confidence(daily_costs)
        
        # 零均值，返回默认置信度
        assert confidence == 0.5
    
    def test_predict_with_different_windows(self, mock_redis):
        """测试不同预测窗口"""
        # 3天窗口
        predictor_3 = CostPredictor(mock_redis, prediction_window=3)
        assert predictor_3.prediction_window == 3
        
        # 14天窗口
        predictor_14 = CostPredictor(mock_redis, prediction_window=14)
        assert predictor_14.prediction_window == 14
    
    def test_predict_monthly_cost_edge_cases(self, predictor, mock_redis):
        """测试月度预测边界情况"""
        # 测试极小值
        mock_redis.get = MagicMock(return_value=b'0.01')
        result = predictor.predict_monthly_cost()
        assert result['predicted_monthly'] == pytest.approx(0.3, rel=0.01)
        
        # 测试极大值
        mock_redis.get = MagicMock(return_value=b'1000.0')
        result = predictor.predict_monthly_cost()
        assert result['predicted_monthly'] == pytest.approx(30000.0, rel=0.01)


@pytest.mark.parametrize("daily_costs,expected_confidence_range", [
    ([30.0, 30.0, 30.0, 30.0, 30.0], (0.85, 1.0)),  # 完全稳定
    ([25.0, 30.0, 35.0, 30.0, 25.0], (0.7, 0.9)),   # 中等波动
    ([10.0, 50.0, 20.0, 60.0, 15.0], (0.5, 0.7)),   # 高波动
])
def test_confidence_calculation_ranges(daily_costs, expected_confidence_range):
    """参数化测试：验证置信度计算范围"""
    mock_redis = Mock()
    predictor = CostPredictor(mock_redis)
    
    confidence = predictor._calculate_confidence(daily_costs)
    
    min_conf, max_conf = expected_confidence_range
    assert min_conf <= confidence <= max_conf


@pytest.mark.parametrize("avg_daily,days,expected_monthly", [
    (30.0, 30, 900.0),
    (50.0, 30, 1500.0),
    (25.0, 30, 750.0),
    (0.0, 30, 0.0),
])
def test_monthly_prediction_calculations(avg_daily, days, expected_monthly):
    """参数化测试：验证月度预测计算"""
    mock_redis = Mock()
    mock_redis.get = MagicMock(return_value=str(avg_daily).encode())
    
    predictor = CostPredictor(mock_redis)
    result = predictor.predict_monthly_cost()
    
    assert result['predicted_monthly'] == pytest.approx(expected_monthly, rel=0.01)
