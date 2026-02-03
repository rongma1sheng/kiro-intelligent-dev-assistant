"""网络关系因子挖掘器单元测试

白皮书依据: 第四章 4.1.13 网络关系因子挖掘器
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.network_relationship import (
    NetworkRelationshipFactorMiner,
    NetworkRelationshipConfig,
    stock_correlation_network,
    supply_chain_network,
    capital_flow_network,
    information_propagation,
    industry_ecosystem,
    network_centrality
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # 生成5只股票的价格数据
    data = pd.DataFrame({
        'stock_A': 100 + np.cumsum(np.random.randn(100) * 2),
        'stock_B': 100 + np.cumsum(np.random.randn(100) * 2),
        'stock_C': 100 + np.cumsum(np.random.randn(100) * 2),
        'stock_D': 100 + np.cumsum(np.random.randn(100) * 2),
        'stock_E': 100 + np.cumsum(np.random.randn(100) * 2)
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
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    volume = pd.DataFrame({
        'stock_A': np.random.randint(1000000, 5000000, 100),
        'stock_B': np.random.randint(1000000, 5000000, 100),
        'stock_C': np.random.randint(1000000, 5000000, 100),
        'stock_D': np.random.randint(1000000, 5000000, 100),
        'stock_E': np.random.randint(1000000, 5000000, 100)
    }, index=dates)
    
    return volume


@pytest.fixture
def industry_map():
    """生成行业映射"""
    return {
        'stock_A': '科技',
        'stock_B': '科技',
        'stock_C': '制造业',
        'stock_D': '制造业',
        'stock_E': '金融'
    }


@pytest.fixture
def miner():
    """创建挖掘器实例"""
    config = EvolutionConfig(population_size=10, max_generations=5)
    network_config = NetworkRelationshipConfig(
        correlation_window=20,
        min_correlation=0.3,
        centrality_method='degree'
    )
    return NetworkRelationshipFactorMiner(config=config, network_config=network_config)


class TestNetworkRelationshipConfig:
    """测试网络关系配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = NetworkRelationshipConfig()
        
        assert config.correlation_window == 60
        assert config.min_correlation == 0.3
        assert config.centrality_method == 'degree'
        assert config.network_threshold == 0.5
        assert config.max_nodes == 100
        assert config.propagation_steps == 3
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = NetworkRelationshipConfig(
            correlation_window=30,
            min_correlation=0.4,
            centrality_method='eigenvector'
        )
        
        assert config.correlation_window == 30
        assert config.min_correlation == 0.4
        assert config.centrality_method == 'eigenvector'


class TestNetworkOperators:
    """测试网络关系算子"""
    
    def test_stock_correlation_network(self, sample_data):
        """测试股票相关性网络算子"""
        result = stock_correlation_network(sample_data, window=20, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert result.dtype == np.float64
    
    def test_stock_correlation_network_empty_data(self):
        """测试空数据"""
        empty_data = pd.DataFrame()
        result = stock_correlation_network(empty_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_supply_chain_network(self, sample_data, industry_map):
        """测试供应链网络算子"""
        result = supply_chain_network(sample_data, industry_map=industry_map, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_supply_chain_network_without_industry_map(self, sample_data):
        """测试无行业映射的供应链网络"""
        result = supply_chain_network(sample_data, industry_map=None, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_capital_flow_network(self, sample_data, sample_volume):
        """测试资金流网络算子"""
        result = capital_flow_network(sample_data, volume=sample_volume, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_capital_flow_network_without_volume(self, sample_data):
        """测试无成交量的资金流网络"""
        result = capital_flow_network(sample_data, volume=None, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_information_propagation(self, sample_data):
        """测试信息传播网络算子"""
        result = information_propagation(sample_data, window=20, max_steps=3)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_industry_ecosystem(self, sample_data, industry_map):
        """测试行业生态网络算子"""
        result = industry_ecosystem(sample_data, industry_map=industry_map, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_industry_ecosystem_without_industry_map(self, sample_data):
        """测试无行业映射的行业生态网络"""
        result = industry_ecosystem(sample_data, industry_map=None, window=20)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_network_centrality_degree(self, sample_data):
        """测试度中心性"""
        result = network_centrality(sample_data, method='degree', window=20, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_network_centrality_eigenvector(self, sample_data):
        """测试特征向量中心性"""
        result = network_centrality(sample_data, method='eigenvector', window=20, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_network_centrality_closeness(self, sample_data):
        """测试接近中心性"""
        result = network_centrality(sample_data, method='closeness', window=20, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_network_centrality_betweenness(self, sample_data):
        """测试介数中心性"""
        result = network_centrality(sample_data, method='betweenness', window=20, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_network_centrality_unknown_method(self, sample_data):
        """测试未知中心性方法"""
        result = network_centrality(sample_data, method='unknown', window=20, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)


class TestNetworkRelationshipFactorMiner:
    """测试网络关系因子挖掘器"""
    
    def test_initialization(self, miner):
        """测试初始化"""
        assert miner is not None
        assert isinstance(miner.network_config, NetworkRelationshipConfig)
        assert hasattr(miner, 'network_operators')
        assert len(miner.network_operators) == 6
    
    def test_operator_registration(self, miner):
        """测试算子注册"""
        expected_operators = [
            'stock_correlation_network',
            'supply_chain_network',
            'capital_flow_network',
            'information_propagation',
            'industry_ecosystem',
            'network_centrality'
        ]
        
        for op in expected_operators:
            assert op in miner.network_operators
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
        # 可能没有找到有效因子，但不应该报错
    
    @pytest.mark.asyncio
    async def test_mine_factors_with_industry_map(
        self, miner, sample_data, sample_returns, industry_map
    ):
        """测试带行业映射的因子挖掘"""
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2,
            industry_map=industry_map
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
    
    def test_calculate_network_factor(self, miner, sample_data):
        """测试计算单个网络因子"""
        factor = miner.calculate_network_factor(
            'stock_correlation_network',
            sample_data
        )
        
        assert isinstance(factor, pd.Series)
        assert len(factor) == len(sample_data)
    
    def test_calculate_network_factor_unknown_operator(self, miner, sample_data):
        """测试未知算子"""
        factor = miner.calculate_network_factor(
            'unknown_operator',
            sample_data
        )
        
        assert isinstance(factor, pd.Series)
        assert (factor == 0.0).all()
    
    def test_analyze_network_structure(self, miner, sample_data):
        """测试网络结构分析"""
        analysis = miner.analyze_network_structure(sample_data, threshold=0.5)
        
        assert isinstance(analysis, dict)
        assert 'num_nodes' in analysis
        assert 'num_edges' in analysis
        assert 'density' in analysis
        assert 'avg_degree' in analysis
        assert 'hub_nodes' in analysis
        assert 'isolated_nodes' in analysis
        
        assert analysis['num_nodes'] == len(sample_data.columns)
        assert analysis['density'] >= 0 and analysis['density'] <= 1
    
    def test_identify_communities(self, miner, sample_data):
        """测试社区识别"""
        communities = miner.identify_communities(
            sample_data,
            threshold=0.5,
            min_community_size=2
        )
        
        assert isinstance(communities, dict)
        # 检查社区大小
        for cid, stocks in communities.items():
            assert len(stocks) >= 2
    
    def test_calculate_network_metrics(self, miner, sample_data):
        """测试计算所有网络指标"""
        metrics = miner.calculate_network_metrics(sample_data)
        
        assert isinstance(metrics, pd.DataFrame)
        assert len(metrics) == len(sample_data)
        
        # 检查是否包含所有指标
        expected_metrics = [
            'correlation_network',
            'supply_chain',
            'capital_flow',
            'information_propagation',
            'industry_ecosystem',
            'centrality_degree',
            'centrality_eigenvector',
            'centrality_closeness'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics.columns


class TestNetworkOperatorsEdgeCases:
    """测试网络算子边界情况"""
    
    def test_single_stock(self):
        """测试单只股票"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'stock_A': 100 + np.cumsum(np.random.randn(100))
        }, index=dates)
        
        result = stock_correlation_network(data, window=20)
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
    
    def test_short_window(self, sample_data):
        """测试短窗口期"""
        result = stock_correlation_network(sample_data, window=5, threshold=0.5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_high_threshold(self, sample_data):
        """测试高阈值"""
        result = stock_correlation_network(sample_data, window=20, threshold=0.9)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
    
    def test_zero_threshold(self, sample_data):
        """测试零阈值"""
        result = stock_correlation_network(sample_data, window=20, threshold=0.0)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)


class TestNetworkPerformance:
    """测试网络算子性能"""
    
    def test_large_network_performance(self):
        """测试大规模网络性能"""
        import time
        
        # 生成50只股票的数据
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame(
            np.random.randn(100, 50).cumsum(axis=0) + 100,
            index=dates,
            columns=[f'stock_{i}' for i in range(50)]
        )
        
        start_time = time.time()
        result = stock_correlation_network(data, window=20, threshold=0.5)
        elapsed = time.time() - start_time
        
        assert isinstance(result, pd.Series)
        assert elapsed < 5.0  # 应该在5秒内完成
    
    def test_centrality_performance(self, sample_data):
        """测试中心性计算性能"""
        import time
        
        start_time = time.time()
        result = network_centrality(sample_data, method='degree', window=20)
        elapsed = time.time() - start_time
        
        assert isinstance(result, pd.Series)
        assert elapsed < 2.0  # 应该在2秒内完成


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
