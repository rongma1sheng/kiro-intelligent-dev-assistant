"""ETF/LOF因子挖掘器端到端集成测试

白皮书依据: 第四章 4.1.17, 4.1.18 - ETF/LOF因子挖掘系统
测试目标: 验证完整的ETF/LOF因子挖掘流程
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.etf_lof.etf_factor_miner import ETFFactorMiner
from src.evolution.etf_lof.lof_factor_miner import LOFFactorMiner
from src.evolution.etf_lof.data_models import ETFMarketData, LOFMarketData
from src.evolution.etf_lof.cross_market_alignment import (
    align_cross_market_data,
    calculate_cross_market_ic_correlation,
    detect_market_specific_factors,
    MarketType
)


class TestETFE2EWorkflow:
    """ETF因子挖掘端到端工作流测试"""
    
    @pytest.fixture
    def etf_market_data(self):
        """创建ETF市场数据"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        n_stocks = 50
        
        data = {
            'close': np.random.uniform(10, 100, (len(dates), n_stocks)),
            'nav': np.random.uniform(10, 100, (len(dates), n_stocks)),
            'volume': np.random.uniform(1000000, 10000000, (len(dates), n_stocks)),
            'creation_units': np.random.uniform(100, 1000, (len(dates), n_stocks)),
            'redemption_units': np.random.uniform(100, 1000, (len(dates), n_stocks)),
            'bid_price': np.random.uniform(9, 99, (len(dates), n_stocks)),
            'ask_price': np.random.uniform(10, 100, (len(dates), n_stocks)),
        }
        
        # 确保bid_price <= ask_price
        data['bid_price'] = np.minimum(data['bid_price'], data['ask_price'] - 0.01)
        
        df_dict = {}
        for key, values in data.items():
            df_dict[key] = pd.DataFrame(
                values,
                index=dates,
                columns=[f'ETF_{i:03d}' for i in range(n_stocks)]
            )
        
        return ETFMarketData(**df_dict)
    
    def test_etf_complete_workflow(self, etf_market_data):
        """测试ETF完整工作流: 初始化 → 生成表达式 → 评估"""
        # 1. 初始化挖掘器
        miner = ETFFactorMiner(
            market_data=etf_market_data,
            population_size=10,
            mutation_rate=0.2,
            crossover_rate=0.8,
            elite_ratio=0.1
        )
        
        assert miner is not None
        assert miner.population_size == 10
        
        # 2. 生成因子表达式
        expression = miner._generate_random_expression()
        assert expression is not None
        assert len(expression) > 0
        
        # 3. 评估表达式
        result = miner._evaluate_expression(expression, etf_market_data.close)
        
        # 验证结果
        if result is not None:
            assert isinstance(result, pd.Series)
            assert len(result) > 0
    
    def test_etf_operator_registry(self, etf_market_data):
        """测试ETF算子注册表完整性"""
        miner = ETFFactorMiner(market_data=etf_market_data)
        
        # 验证算子数量
        whitelist = miner._get_operator_whitelist()
        assert len(whitelist) >= 20  # 至少20个ETF算子
        
        # 验证关键算子存在
        key_operators = [
            'etf_premium_discount',
            'etf_tracking_error',
            'etf_arbitrage_opportunity',
            'etf_liquidity_premium',
            'etf_fund_flow'
        ]
        
        for op in key_operators:
            assert op in whitelist, f"关键算子 {op} 未找到"


class TestLOFE2EWorkflow:
    """LOF因子挖掘端到端工作流测试"""
    
    @pytest.fixture
    def lof_market_data(self):
        """创建LOF市场数据"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        n_funds = 50
        
        data = {
            'onmarket_price': np.random.uniform(1.0, 2.0, (len(dates), n_funds)),
            'offmarket_price': np.random.uniform(1.0, 2.0, (len(dates), n_funds)),
            'nav': np.random.uniform(1.0, 2.0, (len(dates), n_funds)),
            'onmarket_volume': np.random.uniform(100000, 1000000, (len(dates), n_funds)),
            'offmarket_volume': np.random.uniform(100000, 1000000, (len(dates), n_funds)),
            'fund_size': np.random.uniform(1e8, 1e10, (len(dates), n_funds)),
            'turnover_rate': np.random.uniform(0.01, 0.5, (len(dates), n_funds)),
        }
        
        df_dict = {}
        for key, values in data.items():
            df_dict[key] = pd.DataFrame(
                values,
                index=dates,
                columns=[f'LOF_{i:03d}' for i in range(n_funds)]
            )
        
        return LOFMarketData(**df_dict)
    
    def test_lof_complete_workflow(self, lof_market_data):
        """测试LOF完整工作流: 初始化 → 生成表达式 → 评估"""
        # 1. 初始化挖掘器
        miner = LOFFactorMiner(
            market_data=lof_market_data,
            population_size=10,
            mutation_rate=0.2,
            crossover_rate=0.8,
            elite_ratio=0.1
        )
        
        assert miner is not None
        assert miner.population_size == 10
        
        # 2. 生成因子表达式
        expression = miner._generate_random_expression()
        assert expression is not None
        assert len(expression) > 0
        
        # 3. 评估表达式
        result = miner._evaluate_expression(expression, lof_market_data.onmarket_price)
        
        # 验证结果
        if result is not None:
            assert isinstance(result, pd.Series)
            assert len(result) > 0
    
    def test_lof_operator_registry(self, lof_market_data):
        """测试LOF算子注册表完整性"""
        miner = LOFFactorMiner(market_data=lof_market_data)
        
        # 验证算子数量
        whitelist = miner._get_operator_whitelist()
        assert len(whitelist) >= 20  # 至少20个LOF算子
        
        # 验证关键算子存在
        key_operators = [
            'lof_onoff_price_spread',
            'lof_transfer_arbitrage_opportunity',
            'lof_premium_discount_rate',
            'lof_onmarket_liquidity',
            'lof_fund_manager_alpha'
        ]
        
        for op in key_operators:
            assert op in whitelist, f"关键算子 {op} 未找到"


class TestCrossMarketE2EWorkflow:
    """跨市场测试端到端工作流测试"""
    
    @pytest.fixture
    def multi_market_data(self):
        """创建多市场数据"""
        dates = pd.date_range(start='2024-01-01', periods=150, freq='D')
        n_stocks = 30
        
        markets = {}
        for market_name in ['A_SHARE', 'HONG_KONG', 'US']:
            data = pd.DataFrame(
                np.random.uniform(10, 100, (len(dates), n_stocks)),
                index=dates,
                columns=[f'{market_name}_{i:03d}' for i in range(n_stocks)]
            )
            markets[market_name] = data
        
        return markets
    
    def test_cross_market_alignment(self, multi_market_data):
        """测试跨市场数据对齐"""
        # 对齐数据
        aligned = align_cross_market_data(multi_market_data)
        
        # 验证对齐结果
        assert aligned is not None
        assert len(aligned.common_dates) >= 100  # 至少100天重叠
        assert len(aligned.aligned_data) == 3  # 3个市场
        
        # 验证所有市场数据长度一致
        lengths = [len(df) for df in aligned.aligned_data.values()]
        assert len(set(lengths)) == 1, "所有市场数据长度应该一致"
    
    def test_cross_market_ic_correlation(self, multi_market_data):
        """测试跨市场IC相关性计算"""
        # 模拟IC值
        ic_values = {
            MarketType.A_SHARE: 0.05,
            MarketType.HONG_KONG: 0.04,
            MarketType.US: 0.045
        }
        
        # 计算相关性矩阵
        corr_matrix = calculate_cross_market_ic_correlation(ic_values)
        
        # 验证相关性矩阵
        assert corr_matrix is not None
        assert corr_matrix.shape == (3, 3)
        
        # 验证对角线为1
        for i in range(3):
            assert abs(corr_matrix.iloc[i, i] - 1.0) < 1e-6
    
    def test_market_specific_factor_detection(self):
        """测试市场特定因子检测"""
        # 模拟稳定因子（低分歧）
        stable_ic = {
            MarketType.A_SHARE: 0.05,
            MarketType.HONG_KONG: 0.048,
            MarketType.US: 0.052
        }
        
        result = detect_market_specific_factors(stable_ic)
        assert result['is_market_specific'] is False
        
        # 模拟市场特定因子（高分歧）
        divergent_ic = {
            MarketType.A_SHARE: 0.10,
            MarketType.HONG_KONG: 0.02,
            MarketType.US: -0.05
        }
        
        result = detect_market_specific_factors(divergent_ic)
        assert result['is_market_specific'] is True


class TestIntegrationPerformance:
    """集成性能测试"""
    
    def test_etf_miner_initialization_performance(self):
        """测试ETF挖掘器初始化性能"""
        import time
        
        # 创建小规模数据
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        n_stocks = 20
        
        data = {
            'close': pd.DataFrame(
                np.random.uniform(10, 100, (len(dates), n_stocks)),
                index=dates,
                columns=[f'ETF_{i:03d}' for i in range(n_stocks)]
            ),
            'nav': pd.DataFrame(
                np.random.uniform(10, 100, (len(dates), n_stocks)),
                index=dates,
                columns=[f'ETF_{i:03d}' for i in range(n_stocks)]
            ),
            'volume': pd.DataFrame(
                np.random.uniform(1000000, 10000000, (len(dates), n_stocks)),
                index=dates,
                columns=[f'ETF_{i:03d}' for i in range(n_stocks)]
            ),
        }
        
        market_data = ETFMarketData(**data)
        
        # 测试初始化时间
        start = time.perf_counter()
        miner = ETFFactorMiner(market_data=market_data, population_size=10)
        elapsed = time.perf_counter() - start
        
        # 初始化应该很快（< 1秒）
        assert elapsed < 1.0, f"初始化时间过长: {elapsed:.3f}秒"
    
    def test_lof_miner_initialization_performance(self):
        """测试LOF挖掘器初始化性能"""
        import time
        
        # 创建小规模数据
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        n_funds = 20
        
        data = {
            'onmarket_price': pd.DataFrame(
                np.random.uniform(1.0, 2.0, (len(dates), n_funds)),
                index=dates,
                columns=[f'LOF_{i:03d}' for i in range(n_funds)]
            ),
            'offmarket_price': pd.DataFrame(
                np.random.uniform(1.0, 2.0, (len(dates), n_funds)),
                index=dates,
                columns=[f'LOF_{i:03d}' for i in range(n_funds)]
            ),
            'nav': pd.DataFrame(
                np.random.uniform(1.0, 2.0, (len(dates), n_funds)),
                index=dates,
                columns=[f'LOF_{i:03d}' for i in range(n_funds)]
            ),
        }
        
        market_data = LOFMarketData(**data)
        
        # 测试初始化时间
        start = time.perf_counter()
        miner = LOFFactorMiner(market_data=market_data, population_size=10)
        elapsed = time.perf_counter() - start
        
        # 初始化应该很快（< 1秒）
        assert elapsed < 1.0, f"初始化时间过长: {elapsed:.3f}秒"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
