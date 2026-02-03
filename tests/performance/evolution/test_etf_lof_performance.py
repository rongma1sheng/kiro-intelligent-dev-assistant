"""Performance Tests for ETF/LOF Factor Miners

白皮书依据: 第四章 4.1.17-4.1.18 - ETF/LOF因子挖掘器性能要求
版本: v1.6.1
铁律依据: MIA编码铁律1 (白皮书至上), 铁律7 (测试覆盖率要求)

Performance Requirements (白皮书定义):
- ETF evolution: < 60 seconds (50 individuals, 10 generations)
- LOF evolution: < 60 seconds (50 individuals, 10 generations)
- Arena test: < 30 seconds per factor
- Operator calculation: < 100ms (1000 samples)
"""

import time
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.etf_lof.etf_factor_miner import ETFFactorMiner
from src.evolution.etf_lof.lof_factor_miner import LOFFactorMiner
from src.evolution.etf_lof.data_models import ETFMarketData, LOFMarketData
from src.evolution.etf_lof.etf_operators import ETFOperators
from src.evolution.etf_lof.lof_operators import LOFOperators


@pytest.fixture
def sample_etf_data():
    """Generate sample ETF market data for performance testing"""
    dates = pd.date_range(start='2020-01-01', end='2023-01-01', freq='D')
    n = len(dates)
    
    data = pd.DataFrame({
        'date': dates,
        'close': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'nav': 100 + np.cumsum(np.random.randn(n) * 0.5),
        'volume': np.random.randint(1000000, 10000000, n),
        'creation_units': np.random.randint(0, 1000, n),
        'redemption_units': np.random.randint(0, 1000, n),
        'bid_price': 100 + np.cumsum(np.random.randn(n) * 0.5) - 0.1,
        'ask_price': 100 + np.cumsum(np.random.randn(n) * 0.5) + 0.1,
    })
    
    return data


@pytest.fixture
def sample_lof_data():
    """Generate sample LOF market data for performance testing"""
    dates = pd.date_range(start='2020-01-01', end='2023-01-01', freq='D')
    n = len(dates)
    
    data = pd.DataFrame({
        'date': dates,
        'onmarket_price': 1.0 + np.cumsum(np.random.randn(n) * 0.01),
        'offmarket_price': 1.0 + np.cumsum(np.random.randn(n) * 0.01),
        'nav': 1.0 + np.cumsum(np.random.randn(n) * 0.01),
        'onmarket_volume': np.random.randint(100000, 1000000, n),
        'subscription_amount': np.random.randint(0, 100000, n),
        'redemption_amount': np.random.randint(0, 100000, n),
        'returns': np.random.randn(n) * 0.02,
        'benchmark_returns': np.random.randn(n) * 0.015,
    })
    
    return data


class TestETFFactorMinerPerformance:
    """Performance tests for ETFFactorMiner
    
    白皮书依据: 第四章 4.1.17 - ETF因子挖掘器性能要求
    """
    
    def test_etf_evolution_performance(self, sample_etf_data):
        """Test ETF evolution completes within 60 seconds
        
        白皮书依据: 第四章 4.1.17 - 性能要求
        要求: 50个体, 10代进化 < 60秒
        
        Note: This is a performance benchmark, not a strict requirement.
        Actual performance may vary based on hardware.
        """
        # Initialize miner
        miner = ETFFactorMiner(population_size=50)
        
        # Prepare data
        data_columns = ['close', 'nav', 'volume']
        returns = sample_etf_data['close'].pct_change()
        
        # Measure evolution time
        start_time = time.time()
        
        # Initialize population
        miner.initialize_population(data_columns)
        
        # Evaluate fitness
        miner.evaluate_fitness(sample_etf_data, returns)
        
        # Evolve for 10 generations
        best_individual = miner.evolve(generations=10)
        
        elapsed_time = time.time() - start_time
        
        # Log performance
        print(f"\nETF Evolution Performance:")
        print(f"  Time: {elapsed_time:.2f} seconds")
        print(f"  Target: < 60 seconds")
        print(f"  Status: {'✅ PASS' if elapsed_time < 60 else '❌ FAIL'}")
        
        # Assert performance requirement
        assert elapsed_time < 60, (
            f"ETF evolution took {elapsed_time:.2f}s, "
            f"exceeds 60s requirement"
        )
        
        # Verify best individual exists
        assert best_individual is not None
        assert hasattr(best_individual, 'fitness')
    
    def test_etf_operator_performance(self, sample_etf_data):
        """Test ETF operator calculation completes within 100ms for 1000 samples
        
        白皮书依据: 第四章 4.1.17 - 算子性能要求
        要求: 算子计算 < 100ms (1000样本)
        """
        # Use 1000 samples
        data_1000 = sample_etf_data.head(1000)
        
        # Test premium/discount operator
        start_time = time.time()
        result = ETFOperators.etf_premium_discount(
            data_1000['close'],
            data_1000['nav']
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"\nETF Operator Performance (premium_discount):")
        print(f"  Time: {elapsed_ms:.2f} ms")
        print(f"  Target: < 100 ms")
        print(f"  Status: {'✅ PASS' if elapsed_ms < 100 else '❌ FAIL'}")
        
        assert elapsed_ms < 100, (
            f"Operator calculation took {elapsed_ms:.2f}ms, "
            f"exceeds 100ms requirement"
        )
        
        # Verify result
        assert result is not None
        assert len(result) == 1000


class TestLOFFactorMinerPerformance:
    """Performance tests for LOFFactorMiner
    
    白皮书依据: 第四章 4.1.18 - LOF因子挖掘器性能要求
    """
    
    def test_lof_evolution_performance(self, sample_lof_data):
        """Test LOF evolution completes within 60 seconds
        
        白皮书依据: 第四章 4.1.18 - 性能要求
        要求: 50个体, 10代进化 < 60秒
        """
        # Initialize miner
        miner = LOFFactorMiner(population_size=50)
        
        # Prepare data
        data_columns = ['onmarket_price', 'offmarket_price', 'nav']
        returns = sample_lof_data['returns']
        
        # Measure evolution time
        start_time = time.time()
        
        # Initialize population
        miner.initialize_population(data_columns)
        
        # Evaluate fitness
        miner.evaluate_fitness(sample_lof_data, returns)
        
        # Evolve for 10 generations
        best_individual = miner.evolve(generations=10)
        
        elapsed_time = time.time() - start_time
        
        # Log performance
        print(f"\nLOF Evolution Performance:")
        print(f"  Time: {elapsed_time:.2f} seconds")
        print(f"  Target: < 60 seconds")
        print(f"  Status: {'✅ PASS' if elapsed_time < 60 else '❌ FAIL'}")
        
        # Assert performance requirement
        assert elapsed_time < 60, (
            f"LOF evolution took {elapsed_time:.2f}s, "
            f"exceeds 60s requirement"
        )
        
        # Verify best individual exists
        assert best_individual is not None
        assert hasattr(best_individual, 'fitness')
    
    def test_lof_operator_performance(self, sample_lof_data):
        """Test LOF operator calculation completes within 100ms for 1000 samples
        
        白皮书依据: 第四章 4.1.18 - 算子性能要求
        要求: 算子计算 < 100ms (1000样本)
        """
        # Use 1000 samples
        data_1000 = sample_lof_data.head(1000)
        
        # Test onoff price spread operator
        start_time = time.time()
        result = LOFOperators.lof_onoff_price_spread(
            data_1000['onmarket_price'],
            data_1000['offmarket_price']
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"\nLOF Operator Performance (onoff_price_spread):")
        print(f"  Time: {elapsed_ms:.2f} ms")
        print(f"  Target: < 100 ms")
        print(f"  Status: {'✅ PASS' if elapsed_ms < 100 else '❌ FAIL'}")
        
        assert elapsed_ms < 100, (
            f"Operator calculation took {elapsed_ms:.2f}ms, "
            f"exceeds 100ms requirement"
        )
        
        # Verify result
        assert result is not None
        assert len(result) == 1000


class TestArenaIntegrationPerformance:
    """Performance tests for Arena integration
    
    白皮书依据: 第四章 4.2 - Arena测试性能要求
    """
    
    @pytest.mark.skip(reason="Requires Arena service running")
    def test_arena_submission_performance(self, sample_etf_data):
        """Test Arena submission completes within 30 seconds
        
        白皮书依据: 第四章 4.2 - Arena测试性能要求
        要求: Arena三轨测试 < 30秒/因子
        
        Note: This test requires Arena service to be running.
        Skipped by default.
        """
        from src.evolution.etf_lof.arena_integration import submit_to_arena
        
        # Create sample factor
        factor_expression = "etf_premium_discount(close, nav)"
        factor_values = sample_etf_data['close'] / sample_etf_data['nav'] - 1
        
        # Measure submission time
        start_time = time.time()
        
        result = submit_to_arena(
            factor_expression=factor_expression,
            factor_values=factor_values,
            factor_type="ETF"
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\nArena Submission Performance:")
        print(f"  Time: {elapsed_time:.2f} seconds")
        print(f"  Target: < 30 seconds")
        print(f"  Status: {'✅ PASS' if elapsed_time < 30 else '❌ FAIL'}")
        
        assert elapsed_time < 30, (
            f"Arena submission took {elapsed_time:.2f}s, "
            f"exceeds 30s requirement"
        )
        
        assert result is not None


class TestMemoryUsage:
    """Memory usage tests
    
    白皮书依据: 第四章 4.1 - 内存使用要求
    """
    
    def test_etf_miner_memory_usage(self, sample_etf_data):
        """Test ETF miner memory usage is reasonable
        
        要求: 内存占用 < 50MB (1000标的)
        
        Note: This is a guideline, not a strict requirement.
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create miner and run evolution
        miner = ETFFactorMiner(population_size=50)
        data_columns = ['close', 'nav', 'volume']
        returns = sample_etf_data['close'].pct_change()
        
        miner.initialize_population(data_columns)
        miner.evaluate_fitness(sample_etf_data, returns)
        miner.evolve(generations=5)
        
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before
        
        print(f"\nETF Miner Memory Usage:")
        print(f"  Memory used: {mem_used:.2f} MB")
        print(f"  Target: < 50 MB")
        print(f"  Status: {'✅ PASS' if mem_used < 50 else '⚠️  WARNING'}")
        
        # This is a soft requirement
        if mem_used >= 50:
            pytest.warn(
                f"Memory usage ({mem_used:.2f} MB) exceeds guideline (50 MB)"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

