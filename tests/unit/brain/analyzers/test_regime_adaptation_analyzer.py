"""市场状态适应分析器单元测试

白皮书依据: 第五章 5.2.15 市场状态适应分析
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.brain.analyzers.regime_adaptation_analyzer import RegimeAdaptationAnalyzer
from src.brain.analyzers.data_models import RegimeAdaptationAnalysis


class TestRegimeAdaptationAnalyzer:
    """市场状态适应分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return RegimeAdaptationAnalyzer(n_regimes=4)
    
    @pytest.fixture
    def sample_returns(self):
        """创建样本收益率序列"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.015, 252), index=dates)
        return returns
    
    @pytest.fixture
    def sample_market_data(self):
        """创建样本市场数据"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        data = {
            'index_return': np.random.normal(0.0008, 0.012, 252),
            'volatility': np.random.uniform(0.01, 0.03, 252),
            'volume': np.random.uniform(1e9, 5e9, 252)
        }
        return pd.DataFrame(data, index=dates)
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.n_regimes == 4
        assert isinstance(analyzer, RegimeAdaptationAnalyzer)
    
    def test_analyze_basic(self, analyzer, sample_returns, sample_market_data):
        """测试基本分析功能"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证返回类型
        assert isinstance(result, RegimeAdaptationAnalysis)
        assert result.strategy_id == 'test_strategy'
        
        # 验证市场状态分类
        assert isinstance(result.regime_classification, str)
        assert isinstance(result.current_regime, str)
        
        # 验证状态概率分布
        assert isinstance(result.regime_probability, dict)
        assert len(result.regime_probability) > 0
        # 概率和应该为1
        prob_sum = sum(result.regime_probability.values())
        assert abs(prob_sum - 1.0) < 0.01
    
    def test_regime_detection(self, analyzer, sample_returns, sample_market_data):
        """测试市场状态检测"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证状态检测方法
        assert result.regime_detection_method == 'kmeans_clustering'
        
        # 验证当前状态
        assert result.current_regime in ['bull_market', 'bear_market', 'sideways', 'transition']
        
        # 验证状态持续时间
        assert isinstance(result.regime_duration, int)
        assert result.regime_duration > 0
    
    def test_transition_matrix(self, analyzer, sample_returns, sample_market_data):
        """测试状态转移矩阵"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证转移矩阵
        assert isinstance(result.regime_transition_matrix, dict)
        
        # 验证转移概率和为1
        for from_regime, transitions in result.regime_transition_matrix.items():
            prob_sum = sum(transitions.values())
            assert abs(prob_sum - 1.0) < 0.01 or prob_sum == 0.0
    
    def test_performance_by_regime(self, analyzer, sample_returns, sample_market_data):
        """测试各状态下策略表现"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证各状态表现
        assert isinstance(result.strategy_performance_by_regime, dict)
        
        for regime, perf in result.strategy_performance_by_regime.items():
            assert 'mean_return' in perf
            assert 'volatility' in perf
            assert 'sharpe' in perf
            assert 'max_drawdown' in perf
            assert 'win_rate' in perf
    
    def test_best_worst_regimes(self, analyzer, sample_returns, sample_market_data):
        """测试最佳和最差适应状态"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证最佳和最差状态
        assert isinstance(result.best_regime, str)
        assert isinstance(result.worst_regime, str)
        assert result.best_regime != result.worst_regime
    
    def test_adaptation_score(self, analyzer, sample_returns, sample_market_data):
        """测试适应性评分"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证适应性评分
        assert isinstance(result.adaptation_score, float)
        assert 0 <= result.adaptation_score <= 1
    
    def test_regime_sensitivity(self, analyzer, sample_returns, sample_market_data):
        """测试状态敏感度"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证状态敏感度
        assert isinstance(result.regime_sensitivity, float)
        assert 0 <= result.regime_sensitivity <= 1
    
    def test_adaptation_recommendations(self, analyzer, sample_returns, sample_market_data):
        """测试适应性建议"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证建议
        assert isinstance(result.adaptation_recommendations, list)
    
    def test_parameter_adjustment_rules(self, analyzer, sample_returns, sample_market_data):
        """测试参数调整规则"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证参数调整规则
        assert isinstance(result.parameter_adjustment_rules, dict)
        
        for regime, rules in result.parameter_adjustment_rules.items():
            assert 'position_size' in rules
            assert 'stop_loss' in rules
            assert 'take_profit' in rules
    
    def test_dynamic_allocation_strategy(self, analyzer, sample_returns, sample_market_data):
        """测试动态配置策略"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证动态配置策略
        assert isinstance(result.dynamic_allocation_strategy, dict)
    
    def test_regime_forecast(self, analyzer, sample_returns, sample_market_data):
        """测试状态预测"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证状态预测
        assert isinstance(result.regime_forecast, str)
        assert isinstance(result.forecast_confidence, float)
        assert 0 <= result.forecast_confidence <= 1
    
    def test_early_warning_signals(self, analyzer, sample_returns, sample_market_data):
        """测试预警信号"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证预警信号
        assert isinstance(result.early_warning_signals, list)
    
    def test_hedging_recommendations(self, analyzer, sample_returns, sample_market_data):
        """测试对冲建议"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证对冲建议
        assert isinstance(result.hedging_recommendations, list)
    
    def test_with_regime_history(self, analyzer, sample_returns, sample_market_data):
        """测试带历史状态记录的分析"""
        regime_history = [
            {'date': '2023-01-01', 'regime': 'bull_market'},
            {'date': '2023-06-01', 'regime': 'sideways'}
        ]
        
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data,
            regime_history=regime_history
        )
        
        # 验证结果
        assert isinstance(result, RegimeAdaptationAnalysis)
    
    def test_invalid_input_empty_returns(self, analyzer, sample_market_data):
        """测试无效输入：空收益率序列"""
        with pytest.raises(ValueError, match="收益率序列不能为空"):
            analyzer.analyze(
                strategy_id='test_strategy',
                returns=pd.Series(),
                market_data=sample_market_data
            )
    
    def test_invalid_input_empty_market_data(self, analyzer, sample_returns):
        """测试无效输入：空市场数据"""
        with pytest.raises(ValueError, match="市场数据不能为空"):
            analyzer.analyze(
                strategy_id='test_strategy',
                returns=sample_returns,
                market_data=pd.DataFrame()
            )
    
    def test_invalid_input_mismatched_length(self, analyzer):
        """测试无效输入：长度不匹配"""
        returns = pd.Series([0.01, 0.02, 0.03])
        market_data = pd.DataFrame({
            'index_return': [0.01, 0.02],
            'volatility': [0.015, 0.018]
        })
        
        with pytest.raises(ValueError, match="收益率长度.*与市场数据长度.*不匹配"):
            analyzer.analyze(
                strategy_id='test_strategy',
                returns=returns,
                market_data=market_data
            )
    
    def test_performance_requirement(self, analyzer, sample_returns, sample_market_data):
        """测试性能要求：状态检测延迟 < 3秒"""
        start_time = datetime.now()
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            market_data=sample_market_data
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 验证性能要求
        assert elapsed < 3.0, f"状态检测延迟({elapsed:.2f}秒)超过3秒要求"
        assert isinstance(result, RegimeAdaptationAnalysis)
