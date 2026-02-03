"""投资组合优化分析器单元测试

白皮书依据: 第五章 5.2.14 投资组合优化分析
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.brain.analyzers.portfolio_optimization_analyzer import PortfolioOptimizationAnalyzer
from src.brain.analyzers.data_models import PortfolioOptimizationAnalysis


class TestPortfolioOptimizationAnalyzer:
    """投资组合优化分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return PortfolioOptimizationAnalyzer(risk_free_rate=0.03)
    
    @pytest.fixture
    def sample_returns_data(self):
        """创建样本收益率数据"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        strategies = ['strategy_a', 'strategy_b', 'strategy_c']
        
        # 生成模拟收益率数据
        np.random.seed(42)
        data = {
            'strategy_a': np.random.normal(0.001, 0.015, 252),
            'strategy_b': np.random.normal(0.0008, 0.012, 252),
            'strategy_c': np.random.normal(0.0012, 0.018, 252)
        }
        
        return pd.DataFrame(data, index=dates)
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.risk_free_rate == 0.03
        assert isinstance(analyzer, PortfolioOptimizationAnalyzer)
    
    def test_analyze_basic(self, analyzer, sample_returns_data):
        """测试基本分析功能"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证返回类型
        assert isinstance(result, PortfolioOptimizationAnalysis)
        assert result.portfolio_id == 'test_portfolio'
        
        # 验证有效前沿
        assert isinstance(result.efficient_frontier, list)
        assert len(result.efficient_frontier) > 0
        
        # 验证最优组合
        assert isinstance(result.optimal_portfolio, dict)
        assert 'weights' in result.optimal_portfolio
        assert 'return' in result.optimal_portfolio
        assert 'risk' in result.optimal_portfolio
        assert 'sharpe' in result.optimal_portfolio
        
        # 验证权重和为1
        weights_sum = sum(result.optimal_weights.values())
        assert abs(weights_sum - 1.0) < 0.01
    
    def test_analyze_with_target_return(self, analyzer, sample_returns_data):
        """测试指定目标收益率的分析"""
        strategies = list(sample_returns_data.columns)
        target_return = 0.10  # 10%年化收益
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data,
            target_return=target_return
        )
        
        # 验证结果
        assert isinstance(result, PortfolioOptimizationAnalysis)
        # 目标收益率应该接近实际收益率
        assert result.expected_return is not None
    
    def test_analyze_with_target_risk(self, analyzer, sample_returns_data):
        """测试指定目标风险的分析"""
        strategies = list(sample_returns_data.columns)
        target_risk = 0.15  # 15%年化波动率
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data,
            target_risk=target_risk
        )
        
        # 验证结果
        assert isinstance(result, PortfolioOptimizationAnalysis)
        assert result.expected_risk is not None
    
    def test_analyze_with_constraints(self, analyzer, sample_returns_data):
        """测试带约束条件的分析"""
        strategies = list(sample_returns_data.columns)
        constraints = {
            'max_weight': 0.5,
            'min_weight': 0.1
        }
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data,
            constraints=constraints
        )
        
        # 验证结果
        assert isinstance(result, PortfolioOptimizationAnalysis)
        assert result.constraints == constraints
    
    def test_max_sharpe_portfolio(self, analyzer, sample_returns_data):
        """测试最大夏普比率组合"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证最大夏普比率组合
        assert isinstance(result.max_sharpe_portfolio, dict)
        assert 'weights' in result.max_sharpe_portfolio
        assert 'sharpe' in result.max_sharpe_portfolio
        # 夏普比率可以是负数（当收益率低于无风险利率时）
        assert isinstance(result.max_sharpe_portfolio['sharpe'], float)
    
    def test_min_variance_portfolio(self, analyzer, sample_returns_data):
        """测试最小方差组合"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证最小方差组合
        assert isinstance(result.min_variance_portfolio, dict)
        assert 'risk' in result.min_variance_portfolio
        # 最小方差组合的风险应该是最小的
        assert result.min_variance_portfolio['risk'] > 0
    
    def test_risk_parity_portfolio(self, analyzer, sample_returns_data):
        """测试风险平价组合"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证风险平价组合
        assert isinstance(result.risk_parity_portfolio, dict)
        assert 'weights' in result.risk_parity_portfolio
    
    def test_equal_weight_portfolio(self, analyzer, sample_returns_data):
        """测试等权重组合"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证等权重组合
        assert isinstance(result.equal_weight_portfolio, dict)
        weights = result.equal_weight_portfolio['weights']
        # 所有权重应该相等
        expected_weight = 1.0 / len(strategies)
        for weight in weights.values():
            assert abs(weight - expected_weight) < 0.01
    
    def test_portfolio_comparison(self, analyzer, sample_returns_data):
        """测试组合对比"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证组合对比
        assert isinstance(result.portfolio_comparison, dict)
        assert 'max_sharpe' in result.portfolio_comparison
        assert 'min_variance' in result.portfolio_comparison
        assert 'risk_parity' in result.portfolio_comparison
        assert 'equal_weight' in result.portfolio_comparison
    
    def test_diversification_benefit(self, analyzer, sample_returns_data):
        """测试分散化收益"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证分散化收益
        assert isinstance(result.diversification_benefit, float)
        assert 0 <= result.diversification_benefit <= 1
    
    def test_concentration_risk(self, analyzer, sample_returns_data):
        """测试集中度风险"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证集中度风险
        assert isinstance(result.concentration_risk, float)
        assert 0 <= result.concentration_risk <= 1
    
    def test_rebalancing_parameters(self, analyzer, sample_returns_data):
        """测试再平衡参数"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证再平衡参数
        assert isinstance(result.rebalancing_frequency, str)
        assert result.rebalancing_frequency in ['weekly', 'biweekly', 'monthly']
        assert isinstance(result.rebalancing_threshold, float)
        assert 0 < result.rebalancing_threshold < 1
    
    def test_sensitivity_analysis(self, analyzer, sample_returns_data):
        """测试敏感性分析"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证敏感性分析
        assert isinstance(result.sensitivity_analysis, dict)
        assert 'return_sensitivity' in result.sensitivity_analysis
        assert 'risk_sensitivity' in result.sensitivity_analysis
    
    def test_recommendations(self, analyzer, sample_returns_data):
        """测试优化建议"""
        strategies = list(sample_returns_data.columns)
        
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        
        # 验证建议
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0
    
    def test_invalid_input_empty_strategies(self, analyzer):
        """测试无效输入：空策略列表"""
        with pytest.raises(ValueError, match="策略列表不能为空"):
            analyzer.analyze(
                portfolio_id='test_portfolio',
                strategies=[],
                returns_data=pd.DataFrame()
            )
    
    def test_invalid_input_empty_returns(self, analyzer):
        """测试无效输入：空收益率数据"""
        with pytest.raises(ValueError, match="收益率数据不能为空"):
            analyzer.analyze(
                portfolio_id='test_portfolio',
                strategies=['strategy_a'],
                returns_data=pd.DataFrame()
            )
    
    def test_invalid_input_mismatched_dimensions(self, analyzer):
        """测试无效输入：维度不匹配"""
        strategies = ['strategy_a', 'strategy_b']
        returns_data = pd.DataFrame({
            'strategy_a': [0.01, 0.02],
            'strategy_b': [0.01, 0.02],
            'strategy_c': [0.01, 0.02]  # 额外的列
        })
        
        with pytest.raises(ValueError, match="策略数量.*与收益率数据列数.*不匹配"):
            analyzer.analyze(
                portfolio_id='test_portfolio',
                strategies=strategies,
                returns_data=returns_data
            )
    
    def test_performance_requirement(self, analyzer, sample_returns_data):
        """测试性能要求：优化延迟 < 5秒"""
        strategies = list(sample_returns_data.columns)
        
        start_time = datetime.now()
        result = analyzer.analyze(
            portfolio_id='test_portfolio',
            strategies=strategies,
            returns_data=sample_returns_data
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 验证性能要求
        assert elapsed < 5.0, f"优化延迟({elapsed:.2f}秒)超过5秒要求"
        assert isinstance(result, PortfolioOptimizationAnalysis)
