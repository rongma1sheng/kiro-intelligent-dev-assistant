"""风格轮动因子挖掘器单元测试

白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.style_rotation import (
    StyleRotationFactorMiner,
    StyleRotationConfig,
    value_growth_spread,
    size_premium_cycle,
    momentum_reversal_switch,
    quality_junk_rotation,
    low_volatility_anomaly,
    dividend_yield_cycle,
    sector_rotation_signal,
    factor_crowding_index
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=150, freq='D')
    
    # 生成6只股票的价格数据,模拟不同风格
    data = pd.DataFrame({
        'value_stock_A': 100 + np.cumsum(np.random.randn(150) * 1),  # 低波动
        'value_stock_B': 100 + np.cumsum(np.random.randn(150) * 1),
        'growth_stock_A': 100 + np.cumsum(np.random.randn(150) * 3),  # 高波动
        'growth_stock_B': 100 + np.cumsum(np.random.randn(150) * 3),
        'large_cap': 200 + np.cumsum(np.random.randn(150) * 2),  # 大盘
        'small_cap': 50 + np.cumsum(np.random.randn(150) * 2)  # 小盘
    }, index=dates)
    
    return data


@pytest.fixture
def sample_returns(sample_data):
    """生成收益率数据"""
    returns = sample_data.pct_change().mean(axis=1)
    return returns.fillna(0)


@pytest.fixture
def sector_map():
    """生成行业映射"""
    return {
        'value_stock_A': '金融',
        'value_stock_B': '金融',
        'growth_stock_A': '科技',
        'growth_stock_B': '科技',
        'large_cap': '制造业',
        'small_cap': '消费'
    }


@pytest.fixture
def miner():
    """创建挖掘器实例"""
    config = EvolutionConfig(population_size=10, max_generations=5)
    style_config = StyleRotationConfig(
        spread_window=30,
        cycle_window=60,
        momentum_window=10
    )
    return StyleRotationFactorMiner(config=config, style_config=style_config)


class TestStyleRotationConfig:
    """测试风格轮动配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = StyleRotationConfig()
        
        assert config.spread_window == 60
        assert config.cycle_window == 120
        assert config.momentum_window == 20
        assert config.volatility_window == 60
        assert config.spread_threshold == 0.3
        assert config.value_quantile == 0.3
        assert config.growth_quantile == 0.7
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = StyleRotationConfig(
            spread_window=30,
            cycle_window=90,
            momentum_window=15
        )
        
        assert config.spread_window == 30
        assert config.cycle_window == 90
        assert config.momentum_window == 15


class TestStyleRotationOperators:
    """测试风格轮动算子"""
    
    def test_value_growth_spread(self, sample_data):
        """测试价值成长价差算子"""
        result = value_growth_spread(sample_data, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert result.dtype == np.float64
    
    def test_value_growth_spread_empty_data(self):
        """测试空数据"""
        empty_data = pd.DataFrame()
        result = value_growth_spread(empty_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_size_premium_cycle(self, sample_data):
        """测试规模溢价周期算子"""
        result = size_premium_cycle(sample_data, window=60)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_size_premium_cycle_short_window(self, sample_data):
        """测试短窗口规模溢价"""
        result = size_premium_cycle(sample_data, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_momentum_reversal_switch(self, sample_data):
        """测试动量反转切换算子"""
        result = momentum_reversal_switch(sample_data, momentum_window=10, reversal_window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_quality_junk_rotation(self, sample_data):
        """测试质量垃圾轮动算子"""
        result = quality_junk_rotation(sample_data, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_low_volatility_anomaly(self, sample_data):
        """测试低波动异象算子"""
        result = low_volatility_anomaly(sample_data, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_dividend_yield_cycle(self, sample_data):
        """测试股息率周期算子"""
        result = dividend_yield_cycle(sample_data, window=60)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_sector_rotation_signal_with_map(self, sample_data, sector_map):
        """测试带行业映射的行业轮动信号"""
        result = sector_rotation_signal(sample_data, sector_map=sector_map, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_sector_rotation_signal_without_map(self, sample_data):
        """测试无行业映射的行业轮动信号"""
        result = sector_rotation_signal(sample_data, sector_map=None, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_factor_crowding_index(self, sample_data):
        """测试因子拥挤指数算子"""
        result = factor_crowding_index(sample_data, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()


class TestStyleRotationFactorMiner:
    """测试风格轮动因子挖掘器"""
    
    def test_initialization(self, miner):
        """测试初始化"""
        assert miner is not None
        assert isinstance(miner.style_config, StyleRotationConfig)
        assert hasattr(miner, 'style_operators')
        assert len(miner.style_operators) == 8
    
    def test_operator_registration(self, miner):
        """测试算子注册"""
        expected_operators = [
            'value_growth_spread',
            'size_premium_cycle',
            'momentum_reversal_switch',
            'quality_junk_rotation',
            'low_volatility_anomaly',
            'dividend_yield_cycle',
            'sector_rotation_signal',
            'factor_crowding_index'
        ]
        
        for op in expected_operators:
            assert op in miner.style_operators
            assert op in miner.operator_whitelist
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, miner, sample_data, sample_returns):
        """测试因子挖掘"""
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2
        )
        
        assert isinstance(factors, list)
        # 可能没有找到有效因子,但不应该报错
    
    @pytest.mark.asyncio
    async def test_mine_factors_with_sector_map(
        self, miner, sample_data, sample_returns, sector_map
    ):
        """测试带行业映射的因子挖掘"""
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2,
            sector_map=sector_map
        )
        
        assert isinstance(factors, list)
    
    def test_calculate_style_factor(self, miner, sample_data):
        """测试计算单个风格因子"""
        factor = miner.calculate_style_factor(
            'value_growth_spread',
            sample_data
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) == len(sample_data)
    
    def test_calculate_style_factor_unknown_operator(self, miner, sample_data):
        """测试未知算子"""
        factor = miner.calculate_style_factor(
            'unknown_operator',
            sample_data
        )
        
        assert isinstance(factor, pd.Series)
        assert (factor == 0.0).all()
    
    def test_analyze_style_rotation(self, miner, sample_data):
        """测试风格轮动分析"""
        analysis = miner.analyze_style_rotation(sample_data, window=30)
        
        assert isinstance(analysis, dict)
        assert 'value_growth' in analysis
        assert 'size_premium' in analysis
        assert 'momentum_reversal' in analysis
        assert 'quality_junk' in analysis
        assert 'low_volatility' in analysis
        assert 'dividend_yield' in analysis
        assert 'crowding' in analysis
        
        # 检查每个因子都是Series
        for key, value in analysis.items():
            assert isinstance(value, pd.Series)
            assert len(value) == len(sample_data)
    
    def test_identify_dominant_style(self, miner, sample_data):
        """测试主导风格识别"""
        dominant = miner.identify_dominant_style(sample_data, window=30)
        
        assert isinstance(dominant, pd.Series)
        assert len(dominant) == len(sample_data)
        
        # 检查风格标签
        unique_styles = dominant.unique()
        assert len(unique_styles) > 0
    
    def test_calculate_style_timing_signal(self, miner, sample_data):
        """测试风格择时信号"""
        signals = miner.calculate_style_timing_signal(sample_data, window=30)
        
        assert isinstance(signals, pd.DataFrame)
        assert len(signals) == len(sample_data)
        
        # 检查是否包含综合信号
        assert 'composite' in signals.columns
    
    def test_calculate_all_style_metrics(self, miner, sample_data):
        """测试计算所有风格指标"""
        metrics = miner.calculate_all_style_metrics(sample_data)
        
        assert isinstance(metrics, pd.DataFrame)
        assert len(metrics) == len(sample_data)
        
        # 检查是否包含所有指标
        expected_metrics = [
            'value_growth_spread',
            'size_premium_cycle',
            'momentum_reversal_switch',
            'quality_junk_rotation',
            'low_volatility_anomaly',
            'dividend_yield_cycle',
            'sector_rotation_signal',
            'factor_crowding_index'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics.columns
    
    def test_calculate_all_style_metrics_with_sector_map(
        self, miner, sample_data, sector_map
    ):
        """测试带行业映射的风格指标计算"""
        metrics = miner.calculate_all_style_metrics(sample_data, sector_map=sector_map)
        
        assert isinstance(metrics, pd.DataFrame)
        assert len(metrics) == len(sample_data)


class TestStyleOperatorsEdgeCases:
    """测试风格算子边界情况"""
    
    def test_single_stock(self):
        """测试单只股票"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'stock_A': 100 + np.cumsum(np.random.randn(100))
        }, index=dates)
        
        result = value_growth_spread(data, window=20)
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
    
    def test_short_data(self):
        """测试短数据"""
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        data = pd.DataFrame({
            'stock_A': 100 + np.cumsum(np.random.randn(30)),
            'stock_B': 100 + np.cumsum(np.random.randn(30))
        }, index=dates)
        
        result = size_premium_cycle(data, window=60)
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
    
    def test_high_volatility_data(self):
        """测试高波动数据"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'stock_A': 100 + np.cumsum(np.random.randn(100) * 10),
            'stock_B': 100 + np.cumsum(np.random.randn(100) * 10)
        }, index=dates)
        
        result = low_volatility_anomaly(data, window=30)
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
    
    def test_zero_variance_data(self):
        """测试零方差数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'stock_A': [100] * 100,
            'stock_B': [100] * 100
        }, index=dates)
        
        result = quality_junk_rotation(data, window=30)
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)


class TestStylePerformance:
    """测试风格算子性能"""
    
    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        import time
        
        # 生成30只股票的数据
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')
        data = pd.DataFrame(
            np.random.randn(250, 30).cumsum(axis=0) + 100,
            index=dates,
            columns=[f'stock_{i}' for i in range(30)]
        )
        
        start_time = time.time()
        result = value_growth_spread(data, window=60)
        elapsed = time.time() - start_time
        
        assert isinstance(result, pd.Series)
        assert elapsed < 5.0  # 应该在5秒内完成
    
    def test_crowding_index_performance(self, sample_data):
        """测试拥挤指数计算性能"""
        import time
        
        start_time = time.time()
        result = factor_crowding_index(sample_data, window=30)
        elapsed = time.time() - start_time
        
        assert isinstance(result, pd.Series)
        assert elapsed < 3.0  # 应该在3秒内完成


class TestStyleRotationIntegration:
    """测试风格轮动集成功能"""
    
    def test_full_workflow(self, miner, sample_data, sample_returns, sector_map):
        """测试完整工作流程"""
        # 1. 计算所有风格指标
        metrics = miner.calculate_all_style_metrics(sample_data, sector_map=sector_map)
        assert isinstance(metrics, pd.DataFrame)
        
        # 2. 分析风格轮动
        analysis = miner.analyze_style_rotation(sample_data, window=30)
        assert isinstance(analysis, dict)
        
        # 3. 识别主导风格
        dominant = miner.identify_dominant_style(sample_data, window=30)
        assert isinstance(dominant, pd.Series)
        
        # 4. 计算择时信号
        signals = miner.calculate_style_timing_signal(sample_data, window=30)
        assert isinstance(signals, pd.DataFrame)
    
    def test_style_consistency(self, miner, sample_data):
        """测试风格因子一致性"""
        # 计算两次应该得到相同结果
        factor1 = miner.calculate_style_factor('value_growth_spread', sample_data)
        factor2 = miner.calculate_style_factor('value_growth_spread', sample_data)
        
        pd.testing.assert_series_equal(factor1, factor2)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
