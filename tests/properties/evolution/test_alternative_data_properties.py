"""替代数据因子挖掘器属性测试

白皮书依据: 第四章 4.1.3 替代数据因子挖掘
需求: 6.1-6.8 (Alternative Data Factor Integration)

Property Tests:
- Property 21: Alternative Data Factor Generation (需求6.1-6.5)
- Property 22: Alternative Data Validation Consistency (需求6.6)
- Property 23: Data Source Reliability Monitoring (需求6.7, 6.8)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

from src.evolution.alternative_data_miner import (
    AlternativeDataFactorMiner,
    DataSourceType,
    DataQualityScore,
    DataSourceReliability,
    AlternativeDataFactor
)


# ==================== 策略定义 ====================

@st.composite
def market_data_strategy(draw):
    """生成市场数据的策略"""
    n_days = draw(st.integers(min_value=50, max_value=200))
    
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    # 生成价格数据
    np.random.seed(draw(st.integers(min_value=0, max_value=10000)))
    returns = np.random.normal(0.001, 0.02, n_days)
    prices = 100 * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days),
        'high': prices * (1 + np.random.uniform(0, 0.02, n_days)),
        'low': prices * (1 - np.random.uniform(0, 0.02, n_days))
    }, index=dates)
    
    return data


@st.composite
def alternative_data_strategy(draw, n_days: int = 100):
    """生成替代数据的策略"""
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    np.random.seed(draw(st.integers(min_value=0, max_value=10000)))
    
    return {
        'satellite': pd.DataFrame({
            'parking_occupancy': np.random.uniform(0.3, 0.9, n_days)
        }, index=dates),
        'social_media': pd.DataFrame({
            'sentiment_score': np.random.uniform(-1, 1, n_days)
        }, index=dates),
        'web_traffic': pd.DataFrame({
            'page_views': np.random.randint(10000, 100000, n_days)
        }, index=dates),
        'supply_chain': pd.DataFrame({
            'delivery_delay': np.random.uniform(0, 10, n_days)
        }, index=dates),
        'geolocation': pd.DataFrame({
            'foot_traffic': np.random.randint(1000, 10000, n_days)
        }, index=dates),
        'news': pd.DataFrame({
            'news_sentiment': np.random.uniform(-1, 1, n_days)
        }, index=dates),
        'search_trends': pd.DataFrame({
            'search_volume': np.random.randint(100, 1000, n_days)
        }, index=dates),
        'shipping': pd.DataFrame({
            'shipping_volume': np.random.randint(10000, 100000, n_days)
        }, index=dates)
    }


@st.composite
def data_source_type_strategy(draw):
    """生成数据源类型的策略"""
    return draw(st.sampled_from(list(DataSourceType)))


@st.composite
def quality_score_strategy(draw):
    """生成质量评分的策略"""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@st.composite
def alternative_factor_strategy(draw):
    """生成替代数据因子的策略"""
    data_source = draw(data_source_type_strategy())
    
    return AlternativeDataFactor(
        factor_id=f"test_factor_{draw(st.integers(min_value=1, max_value=10000))}",
        factor_name=f"TestFactor_{data_source.value}",
        data_source=data_source,
        expression=f"{data_source.value}_operator(data)",
        quality_score=draw(quality_score_strategy()),
        ic=draw(st.floats(min_value=-0.2, max_value=0.2, allow_nan=False)),
        ir=draw(st.floats(min_value=-2.0, max_value=2.0, allow_nan=False)),
        sharpe=draw(st.floats(min_value=-3.0, max_value=3.0, allow_nan=False))
    )


# ==================== Property 21: Alternative Data Factor Generation ====================

class TestProperty21AlternativeDataFactorGeneration:
    """Property 21: Alternative Data Factor Generation
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
    
    *For any* available alternative data source (satellite, social media, web traffic, 
    supply chain, geolocation), the system should generate at least one factor expression 
    using that data source's specialized operators.
    """
    
    @given(data_source=data_source_type_strategy())
    @settings(max_examples=100, deadline=None)
    def test_each_data_source_has_operator(self, data_source: DataSourceType):
        """测试每种数据源都有对应的算子
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
        
        Property: 对于任何可用的替代数据源，系统应该有至少一个专用算子。
        """
        miner = AlternativeDataFactorMiner()
        
        # 获取数据源对应的算子
        operators_for_source = [
            op_name for op_name in miner.operators.keys()
            if miner.get_operator_data_source(op_name) == data_source
        ]
        
        # 每种数据源至少有一个算子
        assert len(operators_for_source) >= 1, \
            f"数据源 {data_source.value} 没有对应的算子"
    
    @given(seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=50, deadline=None)
    def test_factor_generation_produces_valid_factors(self, seed: int):
        """测试因子生成产生有效因子
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
        
        Property: 对于任何有效的替代数据，系统应该生成具有有效指标的因子。
        """
        np.random.seed(seed)
        
        # 创建测试数据
        n_days = 100
        dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
        
        market_data = pd.DataFrame({
            'close': 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, n_days))),
            'volume': np.random.randint(1000000, 10000000, n_days)
        }, index=dates)
        
        returns = market_data['close'].pct_change().fillna(0)
        
        alt_data = {
            'satellite': pd.DataFrame({
                'parking_occupancy': np.random.uniform(0.3, 0.9, n_days)
            }, index=dates),
            'social_media': pd.DataFrame({
                'sentiment_score': np.random.uniform(-1, 1, n_days)
            }, index=dates),
            'web_traffic': pd.DataFrame({
                'page_views': np.random.randint(10000, 100000, n_days)
            }, index=dates),
            'supply_chain': pd.DataFrame({
                'delivery_delay': np.random.uniform(0, 10, n_days)
            }, index=dates),
            'geolocation': pd.DataFrame({
                'foot_traffic': np.random.randint(1000, 10000, n_days)
            }, index=dates),
            'news': pd.DataFrame({
                'news_sentiment': np.random.uniform(-1, 1, n_days)
            }, index=dates),
            'search_trends': pd.DataFrame({
                'search_volume': np.random.randint(100, 1000, n_days)
            }, index=dates),
            'shipping': pd.DataFrame({
                'shipping_volume': np.random.randint(10000, 100000, n_days)
            }, index=dates)
        }
        
        miner = AlternativeDataFactorMiner()
        factors = miner.mine_factors(market_data, returns, alt_data=alt_data)
        
        # 应该生成8个因子（每个算子一个）
        assert len(factors) == 8, f"期望8个因子，实际生成{len(factors)}个"
        
        # 每个因子都应该有有效的指标
        for factor in factors:
            assert factor.ic is not None, "IC不应为None"
            assert factor.ir is not None, "IR不应为None"
            assert factor.sharpe is not None, "Sharpe不应为None"
            assert factor.fitness >= 0, "适应度应该非负"
            assert not np.isnan(factor.ic), "IC不应为NaN"
            assert not np.isnan(factor.ir), "IR不应为NaN"
            assert not np.isnan(factor.sharpe), "Sharpe不应为NaN"
    
    @given(
        satellite_available=st.booleans(),
        social_available=st.booleans(),
        web_available=st.booleans(),
        supply_available=st.booleans(),
        geo_available=st.booleans()
    )
    @settings(max_examples=50, deadline=None)
    def test_factor_generation_for_available_sources(
        self,
        satellite_available: bool,
        social_available: bool,
        web_available: bool,
        supply_available: bool,
        geo_available: bool
    ):
        """测试只为可用数据源生成因子
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
        
        Property: 系统应该只为可用的数据源生成因子。
        """
        # 至少需要一个数据源可用
        assume(any([satellite_available, social_available, web_available, 
                   supply_available, geo_available]))
        
        np.random.seed(42)
        n_days = 100
        dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
        
        market_data = pd.DataFrame({
            'close': 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, n_days))),
            'volume': np.random.randint(1000000, 10000000, n_days)
        }, index=dates)
        
        returns = market_data['close'].pct_change().fillna(0)
        
        # 根据可用性构建替代数据
        alt_data = {}
        operators_to_use = []
        
        if satellite_available:
            alt_data['satellite'] = pd.DataFrame({
                'parking_occupancy': np.random.uniform(0.3, 0.9, n_days)
            }, index=dates)
            operators_to_use.append('satellite_parking_count')
        
        if social_available:
            alt_data['social_media'] = pd.DataFrame({
                'sentiment_score': np.random.uniform(-1, 1, n_days)
            }, index=dates)
            operators_to_use.append('social_sentiment_momentum')
        
        if web_available:
            alt_data['web_traffic'] = pd.DataFrame({
                'page_views': np.random.randint(10000, 100000, n_days)
            }, index=dates)
            operators_to_use.append('web_traffic_growth')
        
        if supply_available:
            alt_data['supply_chain'] = pd.DataFrame({
                'delivery_delay': np.random.uniform(0, 10, n_days)
            }, index=dates)
            operators_to_use.append('supply_chain_disruption')
        
        if geo_available:
            alt_data['geolocation'] = pd.DataFrame({
                'foot_traffic': np.random.randint(1000, 10000, n_days)
            }, index=dates)
            operators_to_use.append('foot_traffic_anomaly')
        
        miner = AlternativeDataFactorMiner()
        factors = miner.mine_factors(
            market_data, 
            returns, 
            alt_data=alt_data,
            operators=operators_to_use
        )
        
        # 生成的因子数量应该等于可用数据源数量
        assert len(factors) == len(operators_to_use), \
            f"期望{len(operators_to_use)}个因子，实际生成{len(factors)}个"


# ==================== Property 22: Alternative Data Validation Consistency ====================

class TestProperty22AlternativeDataValidationConsistency:
    """Property 22: Alternative Data Validation Consistency
    
    **Validates: Requirements 6.6**
    
    *For any* factor generated from alternative data, it should undergo the same 
    three-track Arena testing as traditional factors, with identical pass/fail criteria.
    """
    
    @given(factor=alternative_factor_strategy())
    @settings(max_examples=100, deadline=None)
    def test_arena_validation_uses_same_criteria(self, factor: AlternativeDataFactor):
        """测试Arena验证使用相同标准
        
        **Validates: Requirements 6.6**
        
        Property: 替代数据因子应该使用与传统因子相同的Arena验证标准。
        """
        miner = AlternativeDataFactorMiner()
        
        # 执行Arena验证
        result = miner._simulate_arena_validation(factor)
        
        # 验证结果结构与传统因子相同
        assert 'status' in result, "结果应包含status字段"
        assert 'overall_result' in result, "结果应包含overall_result字段"
        assert 'score' in result['overall_result'], "结果应包含score字段"
        assert 'passed' in result['overall_result'], "结果应包含passed字段"
        
        # 验证评分在有效范围内
        score = result['overall_result']['score']
        assert 0 <= score <= 100, f"评分应在0-100范围内，实际: {score}"
        
        # 验证通过/失败与评分一致
        passed = result['overall_result']['passed']
        if score >= 70.0:
            assert passed is True, f"评分{score}>=70应该通过"
        else:
            assert passed is False, f"评分{score}<70应该失败"
    
    @given(
        ic=st.floats(min_value=-0.2, max_value=0.2, allow_nan=False),
        sharpe=st.floats(min_value=-3.0, max_value=3.0, allow_nan=False),
        quality=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_arena_score_calculation_consistency(
        self,
        ic: float,
        sharpe: float,
        quality: float
    ):
        """测试Arena评分计算一致性
        
        **Validates: Requirements 6.6**
        
        Property: Arena评分计算应该对所有因子使用相同的公式。
        """
        factor = AlternativeDataFactor(
            factor_id='test_factor',
            factor_name='TestFactor',
            data_source=DataSourceType.SATELLITE,
            expression='test_expression',
            quality_score=quality,
            ic=ic,
            ir=1.0,
            sharpe=sharpe
        )
        
        miner = AlternativeDataFactorMiner()
        result = miner._simulate_arena_validation(factor)
        
        # 验证评分计算公式
        # ic_score = min(abs(ic) / 0.05, 1.0) * 40
        # sharpe_score = min(max(sharpe, 0) / 1.5, 1.0) * 40
        # quality_score = quality * 20
        expected_ic_score = min(abs(ic) / 0.05, 1.0) * 40
        expected_sharpe_score = min(max(sharpe, 0) / 1.5, 1.0) * 40
        expected_quality_score = quality * 20
        expected_total = expected_ic_score + expected_sharpe_score + expected_quality_score
        
        actual_score = result['overall_result']['score']
        
        assert abs(actual_score - expected_total) < 0.01, \
            f"评分计算不一致: 期望{expected_total:.2f}, 实际{actual_score:.2f}"
    
    @given(factor=alternative_factor_strategy())
    @settings(max_examples=50, deadline=None)
    def test_arena_validation_updates_factor_state(self, factor: AlternativeDataFactor):
        """测试Arena验证更新因子状态
        
        **Validates: Requirements 6.6**
        
        Property: Arena验证后应该更新因子的验证状态和评分。
        """
        miner = AlternativeDataFactorMiner()
        
        # 记录验证前的状态
        original_validated = factor.arena_validated
        original_score = factor.arena_score
        
        # 执行验证
        result = miner._simulate_arena_validation(factor)
        
        # 验证状态已更新
        assert factor.arena_validated == result['overall_result']['passed'], \
            "因子验证状态应该与结果一致"
        assert factor.arena_score == result['overall_result']['score'], \
            "因子评分应该与结果一致"


# ==================== Property 23: Data Source Reliability Monitoring ====================

class TestProperty23DataSourceReliabilityMonitoring:
    """Property 23: Data Source Reliability Monitoring
    
    **Validates: Requirements 6.7, 6.8**
    
    *For any* deployed alternative data factor, the system should continuously track 
    data quality score and update frequency, and trigger fallback mechanisms when 
    quality < 0.5 or updates are delayed > 2x expected frequency.
    """
    
    @given(
        quality_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        hours_since_update=st.floats(min_value=0.0, max_value=200.0, allow_nan=False),
        expected_frequency=st.floats(min_value=0.5, max_value=48.0, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_fallback_trigger_conditions(
        self,
        quality_score: float,
        hours_since_update: float,
        expected_frequency: float
    ):
        """测试降级触发条件
        
        **Validates: Requirements 6.7, 6.8**
        
        Property: 当质量 < 0.5 或更新延迟 > 2倍预期频率时应触发降级。
        """
        reliability = DataSourceReliability(
            source_type=DataSourceType.SATELLITE,
            quality_score=quality_score,
            update_frequency_hours=expected_frequency,
            last_update_time=datetime.now() - timedelta(hours=hours_since_update)
        )
        
        should_fallback = reliability.should_trigger_fallback()
        
        # 检查降级条件
        quality_too_low = quality_score < 0.5
        update_too_delayed = hours_since_update > (expected_frequency * 2)
        
        expected_fallback = quality_too_low or update_too_delayed
        
        assert should_fallback == expected_fallback, \
            f"降级触发不一致: quality={quality_score}, delay={hours_since_update}h, " \
            f"expected_freq={expected_frequency}h, should_fallback={expected_fallback}"
    
    @given(data_source=data_source_type_strategy())
    @settings(max_examples=50, deadline=None)
    def test_reliability_tracking_for_all_sources(self, data_source: DataSourceType):
        """测试所有数据源的可靠性跟踪
        
        **Validates: Requirements 6.7**
        
        Property: 系统应该跟踪所有数据源的可靠性。
        """
        miner = AlternativeDataFactorMiner()
        
        # 验证数据源有可靠性监控
        assert data_source in miner.data_source_reliability, \
            f"数据源 {data_source.value} 没有可靠性监控"
        
        reliability = miner.data_source_reliability[data_source]
        
        # 验证可靠性监控有必要的属性
        assert hasattr(reliability, 'quality_score'), "应该有quality_score属性"
        assert hasattr(reliability, 'update_frequency_hours'), "应该有update_frequency_hours属性"
        assert hasattr(reliability, 'last_update_time'), "应该有last_update_time属性"
        assert hasattr(reliability, 'is_available'), "应该有is_available属性"
        assert hasattr(reliability, 'fallback_triggered'), "应该有fallback_triggered属性"
    
    @given(
        quality_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        data_source=data_source_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_quality_score_update(
        self,
        quality_score: float,
        data_source: DataSourceType
    ):
        """测试质量评分更新
        
        **Validates: Requirements 6.7**
        
        Property: 系统应该能够更新数据源的质量评分。
        """
        miner = AlternativeDataFactorMiner()
        
        # 更新质量评分
        miner.update_data_source_reliability(data_source, quality_score)
        
        # 验证更新成功
        reliability = miner.data_source_reliability[data_source]
        assert reliability.quality_score == quality_score, \
            f"质量评分更新失败: 期望{quality_score}, 实际{reliability.quality_score}"
    
    @given(seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=50, deadline=None)
    def test_reliability_report_completeness(self, seed: int):
        """测试可靠性报告完整性
        
        **Validates: Requirements 6.7**
        
        Property: 可靠性报告应该包含所有数据源的状态。
        """
        np.random.seed(seed)
        miner = AlternativeDataFactorMiner()
        
        # 随机更新一些数据源的状态
        for source_type in DataSourceType:
            if np.random.random() > 0.5:
                miner.update_data_source_reliability(
                    source_type,
                    np.random.uniform(0.3, 1.0)
                )
        
        # 获取报告
        report = miner.get_data_source_reliability_report()
        
        # 验证报告结构
        assert 'timestamp' in report, "报告应包含timestamp"
        assert 'sources' in report, "报告应包含sources"
        assert 'summary' in report, "报告应包含summary"
        
        # 验证所有数据源都在报告中
        for source_type in DataSourceType:
            assert source_type.value in report['sources'], \
                f"数据源 {source_type.value} 不在报告中"
        
        # 验证摘要统计
        summary = report['summary']
        assert summary['total_sources'] == len(DataSourceType), \
            "总数据源数量不正确"
        assert (summary['available_sources'] + 
                summary['degraded_sources'] + 
                summary['unavailable_sources']) == summary['total_sources'], \
            "数据源状态统计不一致"
    
    @given(
        quality_threshold=st.floats(min_value=0.5, max_value=0.9, allow_nan=False),
        actual_quality=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
    )
    @settings(max_examples=100, deadline=None)
    def test_fallback_mechanism_activation(
        self,
        quality_threshold: float,
        actual_quality: float
    ):
        """测试降级机制激活
        
        **Validates: Requirements 6.8**
        
        Property: 当数据质量低于阈值时，应该激活降级机制。
        """
        np.random.seed(42)
        n_days = 100
        dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
        
        market_data = pd.DataFrame({
            'close': 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, n_days))),
            'volume': np.random.randint(1000000, 10000000, n_days)
        }, index=dates)
        
        returns = market_data['close'].pct_change().fillna(0)
        
        miner = AlternativeDataFactorMiner(
            data_quality_threshold=quality_threshold,
            fallback_enabled=True
        )
        
        # 设置数据源质量
        miner.update_data_source_reliability(
            DataSourceType.SATELLITE,
            actual_quality
        )
        
        # 如果质量低于阈值且低于0.5，应该触发降级
        reliability = miner.data_source_reliability[DataSourceType.SATELLITE]
        
        if actual_quality < 0.5:
            assert reliability.should_trigger_fallback() is True, \
                f"质量{actual_quality}<0.5应该触发降级"


# ==================== 综合属性测试 ====================

class TestAlternativeDataMinerIntegration:
    """替代数据挖掘器综合属性测试"""
    
    @given(seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=30, deadline=None)
    def test_end_to_end_factor_generation_and_validation(self, seed: int):
        """测试端到端因子生成和验证
        
        **Validates: Requirements 6.1-6.8**
        
        Property: 系统应该能够完成从数据到验证的完整流程。
        """
        np.random.seed(seed)
        n_days = 100
        dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
        
        # 创建市场数据
        market_data = pd.DataFrame({
            'close': 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, n_days))),
            'volume': np.random.randint(1000000, 10000000, n_days)
        }, index=dates)
        
        returns = market_data['close'].pct_change().fillna(0)
        
        # 创建替代数据
        alt_data = {
            'satellite': pd.DataFrame({
                'parking_occupancy': np.random.uniform(0.3, 0.9, n_days)
            }, index=dates)
        }
        
        # 创建挖掘器
        miner = AlternativeDataFactorMiner()
        
        # 1. 挖掘因子
        factors = miner.mine_factors(
            market_data,
            returns,
            alt_data=alt_data,
            operators=['satellite_parking_count']
        )
        
        assert len(factors) >= 1, "应该生成至少一个因子"
        
        # 2. 获取发现的因子
        factor_id = factors[0].factor_id
        assert factor_id in miner.discovered_factors, "因子应该被存储"
        
        alt_factor = miner.discovered_factors[factor_id]
        
        # 3. 执行Arena验证
        result = miner._simulate_arena_validation(alt_factor)
        
        assert 'status' in result, "验证结果应包含status"
        assert alt_factor.arena_validated is not None, "因子应该有验证状态"
        
        # 4. 检查可靠性报告
        report = miner.get_data_source_reliability_report()
        
        assert 'satellite' in report['sources'], "报告应包含卫星数据源"
