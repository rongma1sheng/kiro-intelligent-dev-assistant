"""
因子Arena Property-Based Tests

白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统

Property-Based Testing配置: 最少100次迭代
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta

from src.evolution.arena.data_models import Factor, MarketType
from src.evolution.arena.factor_arena import FactorArenaSystem
from src.evolution.arena.factor_performance_monitor import FactorPerformanceMonitor
from src.infra.event_bus import EventBus


# Hypothesis策略定义
@st.composite
def factor_strategy(draw):
    """生成测试用因子"""
    factor_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    name = draw(st.text(min_size=1, max_size=50))
    description = draw(st.text(min_size=1, max_size=200))
    expression = "close.pct_change()"  # 简化的因子表达式
    category = draw(st.sampled_from(['technical', 'fundamental', 'alternative_data']))
    
    return Factor(
        id=factor_id,
        name=name,
        description=description,
        expression=expression,
        category=category
    )


@st.composite
def market_data_strategy(draw, min_size=100, max_size=500):
    """生成测试用市场数据
    
    注意: 生成的数据需要满足以下条件:
    - historical_data 至少100个样本
    - returns_data 至少100个样本 (pct_change后会少1个)
    
    因此实际生成 min_size + 1 个样本
    """
    # 生成 min_size + 1 个样本，确保 pct_change().dropna() 后仍有 min_size 个样本
    size = draw(st.integers(min_value=min_size + 1, max_value=max_size + 1))
    
    # 生成价格序列
    initial_price = draw(st.floats(min_value=10.0, max_value=1000.0))
    returns = draw(st.lists(
        st.floats(min_value=-0.1, max_value=0.1),
        min_size=size,
        max_size=size
    ))
    
    prices = [initial_price]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    # 生成成交量序列
    volumes = draw(st.lists(
        st.integers(min_value=1000, max_value=1000000),
        min_size=size,
        max_size=size
    ))
    
    # 创建DataFrame
    dates = pd.date_range(start='2020-01-01', periods=size, freq='D')
    df = pd.DataFrame({
        'close': prices[1:],  # 去掉初始价格
        'volume': volumes
    }, index=dates)
    
    # 计算收益率 (pct_change后会少1个样本，但我们生成了size+1个，所以仍有size个)
    returns_series = df['close'].pct_change().dropna()
    
    return df, returns_series


# Property Test 1: Factor Arena Three-Track Completion
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    factor=factor_strategy(),
    data=market_data_strategy(min_size=100, max_size=200)
)
async def test_property_1_arena_three_track_completion(factor, data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 1: Factor Arena Three-Track Completion
    
    **Validates: Requirements 1.1, 1.3, 1.5, 1.7**
    
    For any factor submitted to the Arena, the system should execute 
    all three tracks (Reality, Hell, Cross-Market) and calculate an 
    overall Arena score.
    """
    # 解包数据
    historical_data, returns_data = data
    
    # 创建EventBus
    event_bus = EventBus()
    await event_bus.initialize()
    
    try:
        # 创建Arena系统
        arena = FactorArenaSystem(event_bus)
        
        # 执行测试
        result = await arena.test_factor(
            factor=factor,
            historical_data=historical_data,
            returns_data=returns_data
        )
        
        # 验证所有三轨都执行了
        assert result.reality_result is not None, "Reality Track结果不能为空"
        assert result.hell_result is not None, "Hell Track结果不能为空"
        assert result.cross_market_result is not None, "Cross-Market Track结果不能为空"
        
        # 验证综合评分已计算
        assert result.overall_score is not None, "综合评分不能为空"
        assert 0.0 <= result.overall_score <= 1.0, f"综合评分必须在[0, 1]范围内: {result.overall_score}"
        
        # 验证因子状态已更新
        assert factor.arena_tested is True, "因子arena_tested标志应为True"
        assert factor.arena_score is not None, "因子arena_score不能为空"
        assert factor.arena_score == result.overall_score, "因子arena_score应等于测试结果的overall_score"
        
    finally:
        await event_bus.shutdown()


# Property Test 2: Arena Metric Calculation Completeness
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    factor=factor_strategy(),
    data=market_data_strategy(min_size=100, max_size=200)
)
async def test_property_2_arena_metric_calculation_completeness(factor, data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 2: Arena Metric Calculation Completeness
    
    **Validates: Requirements 1.2, 1.4, 1.6**
    
    For any completed Arena track (Reality, Hell, or Cross-Market), 
    the system should calculate all required metrics.
    """
    historical_data, returns_data = data
    
    event_bus = EventBus()
    await event_bus.initialize()
    
    try:
        arena = FactorArenaSystem(event_bus)
        result = await arena.test_factor(
            factor=factor,
            historical_data=historical_data,
            returns_data=returns_data
        )
        
        # 验证Reality Track指标
        reality = result.reality_result
        assert reality.ic is not None, "IC不能为空"
        assert reality.ir is not None, "IR不能为空"
        assert reality.sharpe_ratio is not None, "夏普比率不能为空"
        assert reality.annual_return is not None, "年化收益率不能为空"
        assert reality.max_drawdown is not None, "最大回撤不能为空"
        assert reality.win_rate is not None, "胜率不能为空"
        assert 0.0 <= reality.win_rate <= 1.0, f"胜率必须在[0, 1]范围内: {reality.win_rate}"
        
        # 验证Hell Track指标
        hell = result.hell_result
        assert hell.survival_rate is not None, "存活率不能为空"
        assert 0.0 <= hell.survival_rate <= 1.0, f"存活率必须在[0, 1]范围内: {hell.survival_rate}"
        assert hell.crash_performance is not None, "崩盘场景表现不能为空"
        assert hell.flash_crash_performance is not None, "闪崩场景表现不能为空"
        assert hell.liquidity_crisis_performance is not None, "流动性危机表现不能为空"
        assert hell.volatility_spike_performance is not None, "波动率飙升表现不能为空"
        assert hell.correlation_breakdown_performance is not None, "相关性崩溃表现不能为空"
        
        # 验证Cross-Market Track指标
        cross_market = result.cross_market_result
        assert cross_market.a_stock_score is not None, "A股评分不能为空"
        assert cross_market.us_stock_score is not None, "美股评分不能为空"
        assert cross_market.crypto_score is not None, "加密货币评分不能为空"
        assert cross_market.hk_stock_score is not None, "港股评分不能为空"
        assert cross_market.adaptability_score is not None, "适应性评分不能为空"
        assert 0.0 <= cross_market.adaptability_score <= 1.0, \
            f"适应性评分必须在[0, 1]范围内: {cross_market.adaptability_score}"
        
    finally:
        await event_bus.shutdown()


# Property Test 3: Arena Validation Threshold
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    factor=factor_strategy(),
    data=market_data_strategy(min_size=100, max_size=200)
)
async def test_property_3_arena_validation_threshold(factor, data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 3: Arena Validation Threshold
    
    **Validates: Requirements 1.8**
    
    For any factor with an overall Arena score exceeding 0.7, 
    the system should mark it as Arena-validated (passed=True).
    """
    historical_data, returns_data = data
    
    event_bus = EventBus()
    await event_bus.initialize()
    
    try:
        arena = FactorArenaSystem(event_bus)
        result = await arena.test_factor(
            factor=factor,
            historical_data=historical_data,
            returns_data=returns_data
        )
        
        # 验证通过逻辑
        pass_threshold = arena.get_pass_threshold()
        assert pass_threshold == 0.7, f"默认通过阈值应为0.7，当前: {pass_threshold}"
        
        if result.overall_score > pass_threshold:
            assert result.passed is True, \
                f"评分 {result.overall_score:.4f} > {pass_threshold}，应标记为通过"
        else:
            assert result.passed is False, \
                f"评分 {result.overall_score:.4f} <= {pass_threshold}，应标记为未通过"
        
        # 验证阈值可配置
        new_threshold = 0.8
        arena.set_pass_threshold(new_threshold)
        assert arena.get_pass_threshold() == new_threshold, \
            f"阈值应更新为 {new_threshold}"
        
    finally:
        await event_bus.shutdown()


# Property Test 4: Arena Report Generation
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    factor=factor_strategy(),
    data=market_data_strategy(min_size=100, max_size=200)
)
async def test_property_4_arena_report_generation(factor, data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 4: Arena Report Generation
    
    **Validates: Requirements 1.9**
    
    For any completed Arena testing, the system should generate 
    a comprehensive test report containing all track results and 
    the overall score.
    """
    historical_data, returns_data = data
    
    event_bus = EventBus()
    await event_bus.initialize()
    
    try:
        arena = FactorArenaSystem(event_bus)
        result = await arena.test_factor(
            factor=factor,
            historical_data=historical_data,
            returns_data=returns_data
        )
        
        # 验证报告完整性
        assert result.factor_id == factor.id, "报告应包含因子ID"
        assert result.test_timestamp is not None, "报告应包含测试时间戳"
        assert isinstance(result.test_timestamp, datetime), "测试时间戳应为datetime类型"
        
        # 验证详细指标
        assert result.detailed_metrics is not None, "报告应包含详细指标"
        assert isinstance(result.detailed_metrics, dict), "详细指标应为字典类型"
        
        # 验证关键指标存在
        required_metrics = [
            'reality_score',
            'hell_score',
            'cross_market_score',
            'ic',
            'ir',
            'sharpe_ratio',
            'survival_rate',
            'adaptability_score'
        ]
        
        for metric in required_metrics:
            assert metric in result.detailed_metrics, \
                f"详细指标应包含 {metric}"
            assert result.detailed_metrics[metric] is not None, \
                f"指标 {metric} 不能为空"
        
        # 验证三轨结果完整性
        assert result.reality_result.reality_score == result.detailed_metrics['reality_score'], \
            "Reality评分应与详细指标一致"
        assert result.hell_result.hell_score == result.detailed_metrics['hell_score'], \
            "Hell评分应与详细指标一致"
        assert result.cross_market_result.cross_market_score == result.detailed_metrics['cross_market_score'], \
            "Cross-Market评分应与详细指标一致"
        
    finally:
        await event_bus.shutdown()
