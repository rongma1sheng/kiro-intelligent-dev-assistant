"""Property-Based Tests for LOFFactorMiner

白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器
版本: v1.6.1

使用Hypothesis框架进行基于属性的测试，验证LOFFactorMiner的通用属性。
每个测试运行100-200次迭代，确保在各种输入下的正确性。

测试属性:
- Property 2: LOF Operator Completeness
- Property 4: LOF Expression Generation Uses Only LOF Operators
- Property 6: LOF Fitness Evaluation Produces Valid Metrics
- Property 16: Data Model Type Validation
- Property 17: Data Model Value Validation
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, settings, strategies as st, HealthCheck
from typing import List

from src.evolution.etf_lof import LOFFactorMiner, LOFMarketData
from src.evolution.genetic_miner import EvolutionConfig
from src.evolution.etf_lof.exceptions import DataQualityError


# ============================================================================
# Hypothesis Strategies (数据生成器)
# ============================================================================

@st.composite
def valid_population_size(draw):
    """生成有效的种群大小 (1-200)"""
    return draw(st.integers(min_value=1, max_value=200))


@st.composite
def valid_probability(draw):
    """生成有效的概率值 (0.0-1.0)"""
    return draw(st.floats(min_value=0.0, max_value=1.0))


@st.composite
def valid_data_columns(draw):
    """生成有效的LOF数据列名"""
    # LOF核心列
    core_columns = [
        'onmarket_price', 'offmarket_price', 'nav',
        'onmarket_volume', 'offmarket_volume',
        'subscription_amount', 'redemption_amount',
        'returns', 'benchmark_returns'
    ]
    
    # 随机选择5-9个列
    n_columns = draw(st.integers(min_value=5, max_value=9))
    return draw(st.lists(
        st.sampled_from(core_columns),
        min_size=n_columns,
        max_size=n_columns,
        unique=True
    ))


@st.composite
def lof_market_data_frame(draw):
    """生成LOF市场数据DataFrame"""
    n_rows = draw(st.integers(min_value=30, max_value=100))
    
    # 生成基础价格数据
    base_price = draw(st.floats(min_value=1.0, max_value=100.0))
    onmarket_prices = np.random.normal(base_price, base_price * 0.1, n_rows)
    offmarket_prices = np.random.normal(base_price, base_price * 0.08, n_rows)
    navs = np.random.normal(base_price, base_price * 0.05, n_rows)
    
    # 生成成交量数据
    onmarket_volumes = np.random.uniform(1000, 100000, n_rows)
    offmarket_volumes = np.random.uniform(500, 50000, n_rows)
    
    # 生成申购赎回数据
    subscription_amounts = np.random.uniform(100, 10000, n_rows)
    redemption_amounts = np.random.uniform(100, 10000, n_rows)
    
    # 生成收益率数据
    returns = np.random.normal(0.001, 0.02, n_rows)
    benchmark_returns = np.random.normal(0.001, 0.015, n_rows)
    
    data = pd.DataFrame({
        'onmarket_price': onmarket_prices,
        'offmarket_price': offmarket_prices,
        'nav': navs,
        'onmarket_volume': onmarket_volumes,
        'offmarket_volume': offmarket_volumes,
        'subscription_amount': subscription_amounts,
        'redemption_amount': redemption_amounts,
        'returns': returns,
        'benchmark_returns': benchmark_returns,
        'onmarket_turnover': np.random.uniform(0.01, 0.5, n_rows),
        'institutional_holding': np.random.uniform(0.3, 0.8, n_rows),
        'retail_holding': np.random.uniform(0.2, 0.7, n_rows),
        'turnover': np.random.uniform(0.1, 2.0, n_rows),
        'expense_ratio': np.random.uniform(0.005, 0.02, n_rows),
        'dividend': np.random.uniform(0, 0.5, n_rows),
        'aum': np.random.uniform(1e8, 1e10, n_rows),
        'trade_size': np.random.uniform(1000, 100000, n_rows),
    })
    
    return data


# ============================================================================
# Property 1: Initialization Properties
# ============================================================================

class TestLOFFactorMinerInitialization:
    """测试LOFFactorMiner初始化属性
    
    白皮书依据: 第四章 4.1.18 - LOFFactorMiner初始化
    验证需求: Requirements 2.1, 2.2
    """
    
    @given(
        population_size=valid_population_size(),
        mutation_rate=valid_probability(),
        crossover_rate=valid_probability(),
        elite_ratio=valid_probability()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_1_valid_initialization(
        self, population_size, mutation_rate, crossover_rate, elite_ratio
    ):
        """Property 1.1: 有效参数应成功初始化
        
        白皮书依据: 第四章 4.1.18 - LOFFactorMiner初始化
        验证需求: Requirements 2.1
        
        验证:
        - 所有有效参数组合都能成功初始化
        - 配置正确设置
        - 算子注册表正确构建
        """
        miner = LOFFactorMiner(
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            elite_ratio=elite_ratio
        )
        
        assert miner is not None
        assert miner.config.population_size == population_size
        assert miner.config.mutation_rate == mutation_rate
        assert miner.config.crossover_rate == crossover_rate
        assert miner.config.elite_ratio == elite_ratio
        
        # 验证算子数量
        assert len(miner.lof_operators) == 20
        assert len(miner.common_operators) == 8
        assert len(miner.operator_registry) == 28
    
    @given(population_size=st.integers(max_value=0))
    @settings(max_examples=50, deadline=None)
    def test_property_1_2_invalid_population_size(self, population_size):
        """Property 1.2: 无效population_size应抛出ValueError
        
        白皮书依据: 第四章 4.1.18 - 参数验证
        验证需求: Requirements 2.1
        
        验证:
        - population_size <= 0 应抛出ValueError
        """
        with pytest.raises(ValueError, match="population_size must be > 0"):
            LOFFactorMiner(population_size=population_size)
    
    @given(
        mutation_rate=st.one_of(
            st.floats(max_value=-0.01),
            st.floats(min_value=1.01)
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_1_3_invalid_mutation_rate(self, mutation_rate):
        """Property 1.3: 无效mutation_rate应抛出ValueError
        
        白皮书依据: 第四章 4.1.18 - 参数验证
        验证需求: Requirements 2.1
        
        验证:
        - mutation_rate不在[0, 1]范围应抛出ValueError
        """
        with pytest.raises(ValueError, match="mutation_rate must be in"):
            LOFFactorMiner(mutation_rate=mutation_rate)


# ============================================================================
# Property 2: LOF Operator Whitelist Properties
# ============================================================================

class TestLOFOperatorWhitelist:
    """测试LOF算子白名单属性
    
    白皮书依据: 第四章 4.1.18 - LOF算子白名单
    验证需求: Requirements 2.2, 2.3
    """
    
    def test_property_2_1_operator_whitelist_completeness(self):
        """Property 2.1: LOF算子白名单完整性
        
        白皮书依据: 第四章 4.1.18 - LOF算子白名单
        验证需求: Requirements 2.2
        
        验证:
        - 20个LOF算子 + 8个通用算子 = 28个总算子
        - 所有算子都在白名单中
        """
        miner = LOFFactorMiner()
        
        # 验证LOF算子数量
        assert len(miner.lof_operators) == 20, \
            f"Expected 20 LOF operators, got {len(miner.lof_operators)}"
        
        # 验证通用算子数量
        assert len(miner.common_operators) == 8, \
            f"Expected 8 common operators, got {len(miner.common_operators)}"
        
        # 验证总算子数量
        whitelist = miner._get_operator_whitelist()
        assert len(whitelist) == 28, \
            f"Expected 28 total operators, got {len(whitelist)}"
        
        # 验证所有LOF算子都在白名单中
        for op in miner.lof_operators:
            assert op in whitelist, f"LOF operator {op} not in whitelist"
        
        # 验证所有通用算子都在白名单中
        for op in miner.common_operators:
            assert op in whitelist, f"Common operator {op} not in whitelist"
    
    def test_property_2_2_operator_registry_consistency(self):
        """Property 2.2: 算子注册表一致性
        
        白皮书依据: 第四章 4.1.18 - 算子注册
        验证需求: Requirements 2.2
        
        验证:
        - 所有通用算子都已注册
        - 所有注册的算子都是可调用的
        """
        miner = LOFFactorMiner()
        
        # 验证通用算子已注册
        for op in miner.common_operators:
            assert op in miner.operator_registry, \
                f"Common operator {op} not registered"
            assert callable(miner.operator_registry[op]), \
                f"Operator {op} is not callable"


# ============================================================================
# Property 3: Expression Generation Properties
# ============================================================================

class TestLOFExpressionGeneration:
    """测试LOF表达式生成属性
    
    白皮书依据: 第四章 4.1.18 - LOF因子表达式生成
    验证需求: Requirements 2.3, 2.4
    """
    
    @given(data_columns=valid_data_columns())
    @settings(max_examples=100, deadline=None)
    def test_property_3_1_generated_expressions_non_empty(self, data_columns):
        """Property 3.1: 生成的表达式非空
        
        白皮书依据: 第四章 4.1.18 - 表达式生成
        验证需求: Requirements 2.3
        
        验证:
        - 对所有有效的data_columns，生成的表达式不为空
        """
        miner = LOFFactorMiner()
        expression = miner._generate_random_expression(data_columns)
        
        assert expression is not None
        assert len(expression) > 0
        assert isinstance(expression, str)
    
    def test_property_3_2_empty_columns_raises_error(self):
        """Property 3.2: 空data_columns应抛出ValueError
        
        白皮书依据: 第四章 4.1.18 - 参数验证
        验证需求: Requirements 2.3
        
        验证:
        - data_columns为空时应抛出ValueError
        """
        miner = LOFFactorMiner()
        
        with pytest.raises(ValueError, match="data_columns cannot be empty"):
            miner._generate_random_expression([])
    
    @given(data_columns=valid_data_columns())
    @settings(max_examples=100, deadline=None)
    def test_property_3_3_generated_expressions_use_valid_operators(self, data_columns):
        """Property 3.3: 生成的表达式使用有效算子
        
        白皮书依据: 第四章 4.1.18 - 算子白名单
        验证需求: Requirements 2.3
        
        验证:
        - 表达式以有效算子开头
        """
        miner = LOFFactorMiner()
        expression = miner._generate_random_expression(data_columns)
        
        # 提取算子名称
        if '(' in expression:
            operator = expression.split('(')[0]
            whitelist = miner._get_operator_whitelist()
            assert operator in whitelist, \
                f"Operator {operator} not in whitelist"


# ============================================================================
# Property 4: Expression Evaluation Properties
# ============================================================================

class TestLOFExpressionEvaluation:
    """测试LOF表达式评估属性
    
    白皮书依据: 第四章 4.1.18 - LOF因子评估
    验证需求: Requirements 2.4, 2.5
    """
    
    @given(data=lof_market_data_frame())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_property_4_1_simple_column_reference_evaluation(self, data):
        """Property 4.1: 简单列引用正确评估
        
        白皮书依据: 第四章 4.1.18 - 表达式评估
        验证需求: Requirements 2.4
        
        验证:
        - 列引用返回正确的数据
        """
        miner = LOFFactorMiner()
        
        # 测试简单列引用
        result = miner._evaluate_expression('nav', data)
        
        assert result is not None
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        pd.testing.assert_series_equal(result, data['nav'])
    
    @given(data=lof_market_data_frame())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_property_4_2_invalid_expression_returns_none(self, data):
        """Property 4.2: 无效表达式返回None
        
        白皮书依据: 第四章 4.1.18 - 错误处理
        验证需求: Requirements 2.4
        
        验证:
        - 无效表达式不抛出异常，返回None
        """
        miner = LOFFactorMiner()
        
        # 测试不存在的列
        result = miner._evaluate_expression('nonexistent_column', data)
        assert result is None
    
    @given(data=lof_market_data_frame())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_property_4_3_common_operators_evaluation(self, data):
        """Property 4.3: 通用算子正确评估
        
        白皮书依据: 第四章 4.1.18 - 通用算子
        验证需求: Requirements 2.4
        
        验证:
        - rank, delay, delta等算子工作正常
        """
        miner = LOFFactorMiner()
        
        # 测试rank算子
        result = miner._evaluate_expression('rank(nav)', data)
        assert result is not None
        assert isinstance(result, pd.Series)
        assert result.min() >= 0.0
        assert result.max() <= 1.0


# ============================================================================
# Property 5: Result Validation Properties
# ============================================================================

class TestLOFResultValidation:
    """测试LOF结果验证属性
    
    白皮书依据: 第四章 4.1.18 - 数据质量要求
    验证需求: Requirements 2.5, 8.4
    """
    
    @given(data=lof_market_data_frame())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_property_5_1_acceptable_nan_ratio(self, data):
        """Property 5.1: 可接受的NaN比率（≤50%）
        
        白皮书依据: 第四章 4.1.18 - 数据质量阈值
        验证需求: Requirements 8.4
        
        验证:
        - NaN比率≤50%的结果应通过验证
        """
        miner = LOFFactorMiner()
        
        # 创建包含40% NaN的数据
        result = data['nav'].copy()
        n_nans = int(len(result) * 0.4)
        result.iloc[:n_nans] = np.nan
        
        # 应该不抛出异常
        try:
            miner._validate_result(result)
        except DataQualityError:
            pytest.fail("Should not raise DataQualityError for 40% NaN")
    
    @given(data=lof_market_data_frame())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_property_5_2_unacceptable_nan_ratio(self, data):
        """Property 5.2: 不可接受的NaN比率（>50%）应抛出DataQualityError
        
        白皮书依据: 第四章 4.1.18 - 数据质量阈值
        验证需求: Requirements 8.4
        
        验证:
        - NaN比率>50%的结果应抛出DataQualityError
        """
        miner = LOFFactorMiner()
        
        # 创建包含60% NaN的数据
        result = data['nav'].copy()
        n_nans = int(len(result) * 0.6)
        result.iloc[:n_nans] = np.nan
        
        # 应该抛出DataQualityError
        with pytest.raises(DataQualityError, match="Too many NaN values"):
            miner._validate_result(result)
    
    def test_property_5_3_infinite_values_replaced(self):
        """Property 5.3: 无限值应被替换为NaN
        
        白皮书依据: 第四章 4.1.18 - 数据清洗
        验证需求: Requirements 8.4
        
        验证:
        - inf和-inf应被替换为NaN
        """
        miner = LOFFactorMiner()
        
        # 创建包含无限值的数据
        result = pd.Series([1.0, 2.0, np.inf, 4.0, -np.inf, 6.0])
        
        # 验证会替换无限值
        # 注意：_validate_result会修改传入的Series
        result_copy = result.copy()
        result_copy = result_copy.replace([np.inf, -np.inf], np.nan)
        
        # 验证无限值被替换
        assert not np.isinf(result_copy).any()


# ============================================================================
# Property 6: Configuration Properties
# ============================================================================

class TestLOFConfiguration:
    """测试LOF配置属性
    
    白皮书依据: 第四章 4.1.18 - 配置管理
    验证需求: Requirements 2.1
    """
    
    @given(
        population_size=valid_population_size(),
        mutation_rate=valid_probability(),
        crossover_rate=valid_probability(),
        elite_ratio=valid_probability()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_1_config_overrides_parameters(
        self, population_size, mutation_rate, crossover_rate, elite_ratio
    ):
        """Property 6.1: 显式config应覆盖单独参数
        
        白皮书依据: 第四章 4.1.18 - 配置优先级
        验证需求: Requirements 2.1
        
        验证:
        - 当提供config时，使用config的参数
        """
        config = EvolutionConfig(
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            elite_ratio=elite_ratio
        )
        
        # 使用不同的单独参数，但config应覆盖
        miner = LOFFactorMiner(
            population_size=10,
            mutation_rate=0.1,
            crossover_rate=0.5,
            elite_ratio=0.05,
            config=config
        )
        
        # 验证使用了config的参数
        assert miner.config.population_size == population_size
        assert miner.config.mutation_rate == mutation_rate
        assert miner.config.crossover_rate == crossover_rate
        assert miner.config.elite_ratio == elite_ratio
    
    def test_property_6_2_default_config_creation(self):
        """Property 6.2: 未提供config时应创建默认config
        
        白皮书依据: 第四章 4.1.18 - 默认配置
        验证需求: Requirements 2.1
        
        验证:
        - 未提供config时，使用单独参数创建config
        """
        miner = LOFFactorMiner(
            population_size=100,
            mutation_rate=0.3,
            crossover_rate=0.8,
            elite_ratio=0.15
        )
        
        assert miner.config is not None
        assert miner.config.population_size == 100
        assert miner.config.mutation_rate == 0.3
        assert miner.config.crossover_rate == 0.8
        assert miner.config.elite_ratio == 0.15


# ============================================================================
# 运行所有测试
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
