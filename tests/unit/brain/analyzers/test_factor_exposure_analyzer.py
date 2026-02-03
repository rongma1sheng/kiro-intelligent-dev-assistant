"""因子暴露分析器单元测试

白皮书依据: 第五章 5.2.16 因子暴露分析
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.brain.analyzers.factor_exposure_analyzer import FactorExposureAnalyzer
from src.brain.analyzers.data_models import FactorExposureAnalysis


class TestFactorExposureAnalyzer:
    """因子暴露分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return FactorExposureAnalyzer()
    
    @pytest.fixture
    def sample_returns(self):
        """创建样本收益率序列"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.015, 252), index=dates)
        return returns
    
    @pytest.fixture
    def sample_factor_returns(self):
        """创建样本因子收益率数据"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        data = {
            'market': np.random.normal(0.0008, 0.012, 252),
            'size': np.random.normal(0.0003, 0.008, 252),
            'value': np.random.normal(0.0005, 0.010, 252),
            'momentum': np.random.normal(0.0007, 0.015, 252),
            'quality': np.random.normal(0.0004, 0.009, 252),
            'volatility': np.random.normal(-0.0002, 0.011, 252),
            'liquidity': np.random.normal(0.0001, 0.007, 252)
        }
        return pd.DataFrame(data, index=dates)
    
    @pytest.fixture
    def sample_holdings(self):
        """创建样本持仓数据"""
        data = {
            'symbol': ['000001', '000002', '000003'],
            'weight': [0.4, 0.35, 0.25],
            'sector': ['finance', 'technology', 'consumer']
        }
        return pd.DataFrame(data)
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert isinstance(analyzer, FactorExposureAnalyzer)
    
    def test_analyze_basic(self, analyzer, sample_returns, sample_factor_returns):
        """测试基本分析功能"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证返回类型
        assert isinstance(result, FactorExposureAnalysis)
        assert result.strategy_id == 'test_strategy'
        
        # 验证因子暴露度
        assert isinstance(result.factor_exposures, dict)
        assert len(result.factor_exposures) > 0
        
        # 验证关键因子暴露
        assert isinstance(result.market_beta, float)
        assert isinstance(result.size_exposure, float)
        assert isinstance(result.value_exposure, float)
        assert isinstance(result.momentum_exposure, float)
    
    def test_analyze_with_holdings(self, analyzer, sample_returns, sample_factor_returns, sample_holdings):
        """测试带持仓数据的分析"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns,
            holdings=sample_holdings
        )
        
        # 验证行业暴露
        assert isinstance(result.sector_exposures, dict)
        if result.sector_exposures:
            # 行业权重和应该为1
            sector_sum = sum(result.sector_exposures.values())
            assert abs(sector_sum - 1.0) < 0.01
    
    def test_factor_exposures(self, analyzer, sample_returns, sample_factor_returns):
        """测试因子暴露度计算"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证所有因子都有暴露度
        expected_factors = ['market', 'size', 'value', 'momentum', 'quality', 'volatility', 'liquidity']
        for factor in expected_factors:
            assert factor in result.factor_exposures
            assert isinstance(result.factor_exposures[factor], float)
    
    def test_style_exposures(self, analyzer, sample_returns, sample_factor_returns):
        """测试风格暴露度"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证风格暴露
        assert isinstance(result.style_exposures, dict)
        expected_styles = ['growth', 'value', 'size', 'quality']
        for style in expected_styles:
            if style in result.style_exposures:
                assert isinstance(result.style_exposures[style], float)
    
    def test_factor_contribution(self, analyzer, sample_returns, sample_factor_returns):
        """测试因子收益贡献"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证因子贡献
        assert isinstance(result.factor_contribution, dict)
        assert len(result.factor_contribution) > 0
    
    def test_alpha_and_r_squared(self, analyzer, sample_returns, sample_factor_returns):
        """测试Alpha和R²"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证Alpha
        assert isinstance(result.alpha, float)
        
        # 验证R²
        assert isinstance(result.r_squared, float)
        assert 0 <= result.r_squared <= 1
    
    def test_tracking_error(self, analyzer, sample_returns, sample_factor_returns):
        """测试跟踪误差"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证跟踪误差
        assert isinstance(result.tracking_error, float)
        assert result.tracking_error >= 0
    
    def test_information_ratio(self, analyzer, sample_returns, sample_factor_returns):
        """测试信息比率"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证信息比率
        assert isinstance(result.information_ratio, float)
    
    def test_factor_timing(self, analyzer, sample_returns, sample_factor_returns):
        """测试因子择时能力"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证因子择时
        assert isinstance(result.factor_timing, float)
        assert 0 <= result.factor_timing <= 1
    
    def test_factor_selection(self, analyzer, sample_returns, sample_factor_returns):
        """测试因子选择能力"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证因子选择
        assert isinstance(result.factor_selection, float)
        assert 0 <= result.factor_selection <= 1
    
    def test_risk_decomposition(self, analyzer, sample_returns, sample_factor_returns):
        """测试风险分解"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证风险分解
        assert isinstance(result.risk_decomposition, dict)
        assert 'total' in result.risk_decomposition
        assert 'systematic' in result.risk_decomposition
        assert 'idiosyncratic' in result.risk_decomposition
        
        # 验证系统性风险和特异性风险
        assert isinstance(result.systematic_risk, float)
        assert isinstance(result.idiosyncratic_risk, float)
        assert result.systematic_risk >= 0
        assert result.idiosyncratic_risk >= 0
    
    def test_concentration_analysis(self, analyzer, sample_returns, sample_factor_returns):
        """测试集中度分析"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证集中度分析
        assert isinstance(result.concentration_analysis, dict)
        assert 'herfindahl_index' in result.concentration_analysis
        assert 'max_exposure' in result.concentration_analysis
        assert 'top3_concentration' in result.concentration_analysis
    
    def test_factor_correlation(self, analyzer, sample_returns, sample_factor_returns):
        """测试因子相关性矩阵"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证因子相关性
        assert isinstance(result.factor_correlation, dict)
        
        # 验证相关性矩阵的对称性
        for factor1 in result.factor_correlation:
            for factor2 in result.factor_correlation[factor1]:
                corr12 = result.factor_correlation[factor1][factor2]
                corr21 = result.factor_correlation[factor2][factor1]
                assert abs(corr12 - corr21) < 0.01
    
    def test_exposure_stability(self, analyzer, sample_returns, sample_factor_returns):
        """测试暴露度稳定性"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证暴露度稳定性
        assert isinstance(result.exposure_stability, float)
        assert 0 <= result.exposure_stability <= 1
        
        # 验证暴露度漂移
        assert isinstance(result.exposure_drift, float)
        assert result.exposure_drift >= 0
    
    def test_rebalancing_needs(self, analyzer, sample_returns, sample_factor_returns):
        """测试再平衡需求"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证再平衡需求
        assert isinstance(result.rebalancing_needs, list)
    
    def test_hedging_recommendations(self, analyzer, sample_returns, sample_factor_returns):
        """测试对冲建议"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证对冲建议
        assert isinstance(result.hedging_recommendations, list)
    
    def test_factor_rotation_signals(self, analyzer, sample_returns, sample_factor_returns):
        """测试因子轮动信号"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        
        # 验证因子轮动信号
        assert isinstance(result.factor_rotation_signals, list)
    
    def test_invalid_input_no_common_dates(self, analyzer):
        """测试无效输入：没有共同日期"""
        returns = pd.Series([0.01, 0.02], index=pd.date_range('2023-01-01', periods=2))
        factor_returns = pd.DataFrame({
            'market': [0.01, 0.02]
        }, index=pd.date_range('2024-01-01', periods=2))
        
        with pytest.raises(ValueError, match="没有共同的日期"):
            analyzer.analyze(
                strategy_id='test_strategy',
                returns=returns,
                factor_returns=factor_returns
            )
    
    def test_performance_requirement(self, analyzer, sample_returns, sample_factor_returns):
        """测试性能要求：因子回归延迟 < 3秒"""
        start_time = datetime.now()
        result = analyzer.analyze(
            strategy_id='test_strategy',
            returns=sample_returns,
            factor_returns=sample_factor_returns
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 验证性能要求
        assert elapsed < 3.0, f"因子回归延迟({elapsed:.2f}秒)超过3秒要求"
        assert isinstance(result, FactorExposureAnalysis)
