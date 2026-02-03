"""高频微观结构因子挖掘器单元测试

白皮书依据: 第四章 4.1.6 高频微观结构因子挖掘器
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.high_frequency import (
    HighFrequencyMicrostructureFactorMiner,
    HighFrequencyConfig,
    order_flow_imbalance,
    price_impact_curve,
    tick_direction_momentum,
    bid_ask_bounce,
    trade_size_clustering,
    quote_stuffing_detection,
    hidden_liquidity_probe,
    market_maker_inventory,
    adverse_selection_cost,
    effective_spread_decomposition
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=200, freq='min')
    
    # 生成高频价格数据
    data = pd.DataFrame({
        'stock_A': 100 + np.cumsum(np.random.randn(200) * 0.1),
        'stock_B': 100 + np.cumsum(np.random.randn(200) * 0.1),
        'stock_C': 100 + np.cumsum(np.random.randn(200) * 0.1)
    }, index=dates)
    
    return data


@pytest.fixture
def sample_returns(sample_data):
    """生成收益率数据"""
    returns = sample_data.pct_change().mean(axis=1)
    return returns.fillna(0)


@pytest.fixture
def sample_volume():
    """生成成交量数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=200, freq='min')
    
    volume = pd.DataFrame({
        'stock_A': np.random.randint(10000, 50000, 200),
        'stock_B': np.random.randint(10000, 50000, 200),
        'stock_C': np.random.randint(10000, 50000, 200)
    }, index=dates)
    
    return volume


@pytest.fixture
def miner():
    """创建挖掘器实例"""
    config = EvolutionConfig(population_size=10, max_generations=5)
    hf_config = HighFrequencyConfig(tick_window=50, imbalance_threshold=0.3)
    return HighFrequencyMicrostructureFactorMiner(config=config, hf_config=hf_config)


class TestHighFrequencyConfig:
    """测试高频配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = HighFrequencyConfig()
        
        assert config.tick_window == 100
        assert config.imbalance_threshold == 0.3
        assert config.impact_quantiles == (0.25, 0.5, 0.75)
        assert config.cluster_window == 50
        assert config.stuffing_threshold == 10.0
        assert config.spread_window == 20
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = HighFrequencyConfig(
            tick_window=50,
            imbalance_threshold=0.4,
            cluster_window=30
        )
        
        assert config.tick_window == 50
        assert config.imbalance_threshold == 0.4
        assert config.cluster_window == 30


class TestHighFrequencyOperators:
    """测试高频算子"""
    
    def test_order_flow_imbalance(self, sample_data, sample_volume):
        """测试订单流不平衡算子"""
        result = order_flow_imbalance(sample_data, volume=sample_volume, window=50)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_order_flow_imbalance_without_volume(self, sample_data):
        """测试无成交量的订单流不平衡"""
        result = order_flow_imbalance(sample_data, volume=None, window=50)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_price_impact_curve(self, sample_data, sample_volume):
        """测试价格冲击曲线算子"""
        result = price_impact_curve(sample_data, volume=sample_volume)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_tick_direction_momentum(self, sample_data):
        """测试Tick方向动量算子"""
        result = tick_direction_momentum(sample_data, window=50)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_bid_ask_bounce(self, sample_data):
        """测试买卖价反弹算子"""
        result = bid_ask_bounce(sample_data, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_trade_size_clustering(self, sample_data, sample_volume):
        """测试交易规模聚类算子"""
        result = trade_size_clustering(sample_data, volume=sample_volume, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_quote_stuffing_detection(self, sample_data):
        """测试报价填充检测算子"""
        result = quote_stuffing_detection(sample_data, window=20, threshold=10.0)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_hidden_liquidity_probe(self, sample_data, sample_volume):
        """测试隐藏流动性探测算子"""
        result = hidden_liquidity_probe(sample_data, volume=sample_volume, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_market_maker_inventory(self, sample_data, sample_volume):
        """测试做市商库存算子"""
        result = market_maker_inventory(sample_data, volume=sample_volume, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_adverse_selection_cost(self, sample_data, sample_volume):
        """测试逆向选择成本算子"""
        result = adverse_selection_cost(sample_data, volume=sample_volume, window=30)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_effective_spread_decomposition(self, sample_data):
        """测试有效价差分解算子"""
        result = effective_spread_decomposition(sample_data, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)


class TestHighFrequencyMicrostructureFactorMiner:
    """测试高频微观结构因子挖掘器"""
    
    def test_initialization(self, miner):
        """测试初始化"""
        assert miner is not None
        assert isinstance(miner.hf_config, HighFrequencyConfig)
        assert hasattr(miner, 'hf_operators')
        assert len(miner.hf_operators) == 10
    
    def test_operator_registration(self, miner):
        """测试算子注册"""
        expected_operators = [
            'order_flow_imbalance',
            'price_impact_curve',
            'tick_direction_momentum',
            'bid_ask_bounce',
            'trade_size_clustering',
            'quote_stuffing_detection',
            'hidden_liquidity_probe',
            'market_maker_inventory',
            'adverse_selection_cost',
            'effective_spread_decomposition'
        ]
        
        for op in expected_operators:
            assert op in miner.hf_operators
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
    
    @pytest.mark.asyncio
    async def test_mine_factors_with_volume(
        self, miner, sample_data, sample_returns, sample_volume
    ):
        """测试带成交量的因子挖掘"""
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2,
            volume=sample_volume
        )
        
        assert isinstance(factors, list)
    
    def test_calculate_hf_factor(self, miner, sample_data):
        """测试计算单个高频因子"""
        factor = miner.calculate_hf_factor(
            'tick_direction_momentum',
            sample_data
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) == len(sample_data)
    
    def test_calculate_hf_factor_with_volume(self, miner, sample_data, sample_volume):
        """测试带成交量的因子计算"""
        factor = miner.calculate_hf_factor(
            'order_flow_imbalance',
            sample_data,
            volume=sample_volume
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) == len(sample_data)
    
    def test_calculate_hf_factor_unknown_operator(self, miner, sample_data):
        """测试未知算子"""
        factor = miner.calculate_hf_factor(
            'unknown_operator',
            sample_data
        )
        
        assert isinstance(factor, pd.Series)
        assert (factor == 0.0).all()
    
    def test_calculate_all_hf_metrics(self, miner, sample_data, sample_volume):
        """测试计算所有高频指标"""
        metrics = miner.calculate_all_hf_metrics(sample_data, volume=sample_volume)
        
        assert isinstance(metrics, pd.DataFrame)
        assert len(metrics) == len(sample_data)
        assert len(metrics.columns) == 10
        
        expected_metrics = [
            'order_flow_imbalance',
            'price_impact',
            'tick_momentum',
            'bid_ask_bounce',
            'trade_clustering',
            'quote_stuffing',
            'hidden_liquidity',
            'mm_inventory',
            'adverse_selection',
            'spread_decomposition'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics.columns


class TestHighFrequencyOperatorsEdgeCases:
    """测试高频算子边界情况"""
    
    def test_empty_data(self):
        """测试空数据"""
        empty_data = pd.DataFrame()
        result = order_flow_imbalance(empty_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_single_stock(self):
        """测试单只股票"""
        dates = pd.date_range(start='2023-01-01', periods=200, freq='min')
        data = pd.DataFrame({
            'stock_A': 100 + np.cumsum(np.random.randn(200) * 0.1)
        }, index=dates)
        
        result = tick_direction_momentum(data, window=50)
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
    
    def test_short_window(self, sample_data):
        """测试短窗口期"""
        result = order_flow_imbalance(sample_data, window=10)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_large_window(self, sample_data):
        """测试大窗口期"""
        result = order_flow_imbalance(sample_data, window=150)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)


class TestHighFrequencyPerformance:
    """测试高频算子性能"""
    
    def test_operator_performance(self, sample_data):
        """测试算子计算性能"""
        import time
        
        start_time = time.time()
        result = tick_direction_momentum(sample_data, window=50)
        elapsed = time.time() - start_time
        
        assert isinstance(result, pd.Series)
        assert elapsed < 1.0  # 应该在1秒内完成
    
    def test_all_metrics_performance(self, miner, sample_data, sample_volume):
        """测试所有指标计算性能"""
        import time
        
        start_time = time.time()
        metrics = miner.calculate_all_hf_metrics(sample_data, volume=sample_volume)
        elapsed = time.time() - start_time
        
        assert isinstance(metrics, pd.DataFrame)
        assert elapsed < 5.0  # 应该在5秒内完成


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
