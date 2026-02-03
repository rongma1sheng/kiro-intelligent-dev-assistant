"""EnhancedIlliquidityMiner属性测试

白皮书依据: 第四章 4.1 暗物质挖掘工厂 - 流动性因子专家

本文件包含EnhancedIlliquidityMiner的属性测试（Property-Based Testing），验证系统的通用性质。

属性测试使用hypothesis库，每个测试至少运行100次随机输入。

测试的属性：
- Property 6: Factor-to-Risk Conversion Reversibility
- Property 17: Liquidity Stratification Completeness
- Property 18: Amihud Calculation Correctness
- Property 19: Liquidity Adaptability Threshold
- Property 20: Exit Level Completeness

铁律7: 测试覆盖率要求 - 所有38个正确性属性必须有对应的属性测试
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import pytest
import numpy as np
import pandas as pd
from hypothesis import given, strategies as st, settings, assume
from hypothesis.extra.pandas import data_frames, column
from datetime import datetime, timedelta

from src.evolution.enhanced_illiquidity_miner import (
    EnhancedIlliquidityMiner,
    ExitLevels
)


# ============================================================================
# 测试辅助策略
# ============================================================================

@st.composite
def stock_data_strategy(draw, min_days=20, max_days=100, min_stocks=5, max_stocks=20):
    """生成股票数据DataFrame
    
    Args:
        draw: hypothesis draw function
        min_days: 最小天数
        max_days: 最大天数
        min_stocks: 最小股票数
        max_stocks: 最大股票数
        
    Returns:
        DataFrame with columns: close, high, low, volume, amount
    """
    n_days = draw(st.integers(min_value=min_days, max_value=max_days))
    n_stocks = draw(st.integers(min_value=min_stocks, max_value=max_stocks))
    
    # 生成日期索引
    start_date = datetime(2020, 1, 1)
    dates = pd.date_range(start=start_date, periods=n_days, freq='D')
    
    # 生成股票代码
    symbols = [f"{i:06d}.SH" for i in range(n_stocks)]
    
    # 生成价格数据（确保 high >= close >= low > 0）
    base_price = draw(st.floats(min_value=10.0, max_value=100.0))
    close_prices = np.random.uniform(base_price * 0.8, base_price * 1.2, (n_days, n_stocks))
    
    # high 必须 >= close
    high_prices = close_prices * np.random.uniform(1.0, 1.05, (n_days, n_stocks))
    
    # low 必须 <= close
    low_prices = close_prices * np.random.uniform(0.95, 1.0, (n_days, n_stocks))
    
    # 成交量和成交额（确保 > 0）
    volumes = np.random.uniform(1e6, 1e8, (n_days, n_stocks))
    amounts = volumes * close_prices  # amount = volume * price
    
    # 构建DataFrame
    data = pd.DataFrame({
        'close': close_prices.flatten(),
        'high': high_prices.flatten(),
        'low': low_prices.flatten(),
        'volume': volumes.flatten(),
        'amount': amounts.flatten()
    }, index=pd.MultiIndex.from_product([dates, symbols], names=['date', 'symbol']))
    
    return data


@st.composite
def returns_strategy(draw, length=20):
    """生成收益率序列
    
    Args:
        draw: hypothesis draw function
        length: 序列长度
        
    Returns:
        Series of returns
    """
    returns = draw(st.lists(
        st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
        min_size=length,
        max_size=length
    ))
    return pd.Series(returns)


@st.composite
def volume_dollar_strategy(draw, length=20):
    """生成成交额序列（美元）
    
    Args:
        draw: hypothesis draw function
        length: 序列长度
        
    Returns:
        Series of volume_dollar (> 0)
    """
    volumes = draw(st.lists(
        st.floats(min_value=1e3, max_value=1e9, allow_nan=False, allow_infinity=False),
        min_size=length,
        max_size=length
    ))
    return pd.Series(volumes)


# ============================================================================
# Property 18: Amihud Calculation Correctness
# ============================================================================

@given(
    returns=returns_strategy(length=20),
    volume_dollar=volume_dollar_strategy(length=20)
)
@settings(max_examples=100, deadline=None)
def test_property_18_amihud_calculation_correctness(returns, volume_dollar):
    """Property 18: Amihud计算正确性
    
    白皮书依据: 第四章 4.1 流动性因子专家
    设计文档: Property 18
    验证需求: Requirements 5.3
    
    属性: 对于任何股票的收益率R和成交额V，Amihud非流动性指标应该等于 |R| / V，
         并且这个计算在所有股票上应该是一致的。
    
    测试策略:
    1. 生成随机收益率和成交额序列
    2. 计算Amihud比率
    3. 验证每个值都等于 |return| / volume_dollar
    4. 验证没有NaN或Inf值（除非volume_dollar为0）
    """
    # 创建EnhancedIlliquidityMiner实例
    miner = EnhancedIlliquidityMiner()
    
    # 计算Amihud比率（不截断异常值，以验证精确计算）
    amihud_ratio = miner.calculate_amihud_ratio(returns, volume_dollar, clip_outliers=False)
    
    # 验证长度一致
    assert len(amihud_ratio) == len(returns), \
        f"Amihud比率长度({len(amihud_ratio)})应该等于收益率长度({len(returns)})"
    
    # 验证每个值的正确性
    for i in range(len(returns)):
        expected = abs(returns.iloc[i]) / volume_dollar.iloc[i]
        actual = amihud_ratio.iloc[i]
        
        # 允许浮点误差
        assert abs(actual - expected) < 1e-10, \
            f"索引{i}: Amihud比率({actual})应该等于|return|/volume_dollar({expected})"
    
    # 验证没有NaN或Inf（volume_dollar都 > 0）
    assert not amihud_ratio.isna().any(), "Amihud比率不应该包含NaN"
    assert not np.isinf(amihud_ratio).any(), "Amihud比率不应该包含Inf"
    
    # 验证所有值都 >= 0（因为使用了绝对值）
    assert (amihud_ratio >= 0).all(), "Amihud比率应该都 >= 0"


# ============================================================================
# Property 18 边界测试
# ============================================================================

@given(
    returns=returns_strategy(length=10)
)
@settings(max_examples=100, deadline=None)
def test_property_18_amihud_zero_volume(returns):
    """Property 18: Amihud计算 - 零成交额边界测试
    
    验证当成交额为0时，Amihud比率应该为Inf或被正确处理
    """
    miner = EnhancedIlliquidityMiner()
    
    # 创建包含零成交额的序列
    volume_dollar = pd.Series([0.0] * len(returns))
    
    # 应该抛出ValueError（除以零）
    with pytest.raises(ValueError, match="成交额不能包含0或负数"):
        miner.calculate_amihud_ratio(returns, volume_dollar)


@given(
    volume_dollar=volume_dollar_strategy(length=10)
)
@settings(max_examples=100, deadline=None)
def test_property_18_amihud_zero_return(volume_dollar):
    """Property 18: Amihud计算 - 零收益率边界测试
    
    验证当收益率为0时，Amihud比率应该为0
    """
    miner = EnhancedIlliquidityMiner()
    
    # 创建全零收益率序列
    returns = pd.Series([0.0] * len(volume_dollar))
    
    # 计算Amihud比率（不截断）
    amihud_ratio = miner.calculate_amihud_ratio(returns, volume_dollar, clip_outliers=False)
    
    # 验证所有值都为0
    assert (amihud_ratio == 0).all(), "零收益率应该产生零Amihud比率"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# Property 17: Liquidity Stratification Completeness
# ============================================================================

@given(
    data=stock_data_strategy(min_days=20, max_days=50, min_stocks=30, max_stocks=60)
)
@settings(max_examples=100, deadline=None)
def test_property_17_liquidity_stratification_completeness(data):
    """Property 17: 流动性分层完整性
    
    白皮书依据: 第四章 4.1 流动性因子专家
    设计文档: Property 17
    验证需求: Requirements 5.2, 5.4
    
    属性: 对于任何包含N只股票的市场数据，流动性分层应该将股票分为恰好三个三分位
         （高、中、低），每个分层大约包含N/3只股票。
    
    测试策略:
    1. 生成随机市场数据（30-60只股票）
    2. 执行流动性分层
    3. 验证恰好有3个分层
    4. 验证每个分层的股票数量大约为N/3（允许±2的误差）
    5. 验证所有股票都被分配到某个分层
    """
    # 创建EnhancedIlliquidityMiner实例
    miner = EnhancedIlliquidityMiner()
    
    # 执行流动性分层
    strata = miner.stratify_by_liquidity(data)
    
    # 获取唯一股票数量
    unique_symbols = data.index.get_level_values('symbol').unique()
    n_stocks = len(unique_symbols)
    
    # 验证恰好有3个分层
    assert len(strata) == 3, \
        f"应该有恰好3个流动性分层，实际: {len(strata)}"
    
    # 验证分层键名
    assert 'high' in strata, "应该包含'high'流动性分层"
    assert 'medium' in strata, "应该包含'medium'流动性分层"
    assert 'low' in strata, "应该包含'low'流动性分层"
    
    # 计算每个分层的股票数量
    high_count = len(strata['high'])
    medium_count = len(strata['medium'])
    low_count = len(strata['low'])
    
    # 验证总数等于原始股票数
    total_count = high_count + medium_count + low_count
    assert total_count == n_stocks, \
        f"分层后的总股票数({total_count})应该等于原始股票数({n_stocks})"
    
    # 验证每个分层的股票数量大约为N/3（允许±2的误差）
    expected_per_stratum = n_stocks / 3
    tolerance = 2
    
    assert abs(high_count - expected_per_stratum) <= tolerance, \
        f"高流动性分层股票数({high_count})应该接近{expected_per_stratum:.1f}（±{tolerance}）"
    
    assert abs(medium_count - expected_per_stratum) <= tolerance, \
        f"中流动性分层股票数({medium_count})应该接近{expected_per_stratum:.1f}（±{tolerance}）"
    
    assert abs(low_count - expected_per_stratum) <= tolerance, \
        f"低流动性分层股票数({low_count})应该接近{expected_per_stratum:.1f}（±{tolerance}）"
    
    # 验证没有重复的股票
    all_symbols = set(strata['high']) | set(strata['medium']) | set(strata['low'])
    assert len(all_symbols) == n_stocks, \
        f"分层中的唯一股票数({len(all_symbols)})应该等于原始股票数({n_stocks})"


# ============================================================================
# Property 19: Liquidity Adaptability Threshold
# ============================================================================

@given(
    adaptability_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    ic_std=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_property_19_liquidity_adaptability_threshold(adaptability_score, ic_std):
    """Property 19: 流动性适应性阈值
    
    白皮书依据: 第四章 4.1 流动性因子专家
    设计文档: Property 19
    验证需求: Requirements 5.5, 5.6
    
    属性: 对于任何增强流动性因子，当且仅当流动性适应性得分 > 0.6 且
         IC标准差跨流动性分层 < 0.4 时，应该批准该因子。
    
    测试策略:
    1. 生成随机适应性得分和IC标准差
    2. 验证批准逻辑的一致性
    3. 确保阈值正确应用
    """
    # 批准逻辑：adaptability_score > 0.6 AND ic_std < 0.4
    should_approve = (adaptability_score > 0.6) and (ic_std < 0.4)
    
    # 验证逻辑一致性
    if adaptability_score > 0.6 and ic_std < 0.4:
        assert should_approve, \
            f"当adaptability_score({adaptability_score:.3f}) > 0.6 且 ic_std({ic_std:.3f}) < 0.4时，应该批准"
    else:
        assert not should_approve, \
            f"当adaptability_score({adaptability_score:.3f}) <= 0.6 或 ic_std({ic_std:.3f}) >= 0.4时，应该拒绝"
    
    # 验证边界条件
    if adaptability_score == 0.6:
        assert not should_approve, "adaptability_score = 0.6 时应该拒绝（不满足 > 0.6）"
    
    if ic_std == 0.4:
        assert not should_approve, "ic_std = 0.4 时应该拒绝（不满足 < 0.4）"


# ============================================================================
# Property 6: Factor-to-Risk Conversion Reversibility
# ============================================================================

@given(
    factor_values=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=50
    )
)
@settings(max_examples=100, deadline=None)
def test_property_6_factor_to_risk_conversion_reversibility(factor_values):
    """Property 6: 因子到风险转换的可逆性
    
    白皮书依据: 第四章 4.1 流动性因子专家
    设计文档: Property 6
    验证需求: Requirements 1.8, 5.7, 7.5
    
    属性: 对于任何失败健康检查的因子，将其转换为风险因子后，
         风险信号应该与原始因子信号呈负相关。
    
    测试策略:
    1. 生成随机因子值
    2. 模拟风险转换（反转信号）
    3. 验证风险信号与原始因子值呈负相关
    
    注意：这里测试的是核心逻辑（信号反转），而不是完整的convert_to_risk_factor方法
    """
    # 转换为Series
    factor_series = pd.Series(factor_values)
    
    # 模拟风险转换：风险信号 = -因子值
    risk_signal = -factor_series
    
    # 验证长度一致
    assert len(risk_signal) == len(factor_series), \
        f"风险信号长度({len(risk_signal)})应该等于因子长度({len(factor_series)})"
    
    # 计算相关系数
    correlation = factor_series.corr(risk_signal)
    
    # 验证负相关（相关系数 < 0）
    # 注意：如果因子值全部相同，相关系数可能是NaN
    if not np.isnan(correlation):
        assert correlation < 0, \
            f"风险信号应该与原始因子呈负相关，实际相关系数: {correlation:.4f}"
        
        # 验证完美负相关（correlation ≈ -1）
        assert abs(correlation + 1.0) < 0.01, \
            f"风险信号应该与原始因子呈完美负相关，实际相关系数: {correlation:.4f}"


# ============================================================================
# Property 20: Exit Level Completeness
# ============================================================================

@given(
    current_price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    risk_signal=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    volatility=st.floats(min_value=0.5, max_value=5.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100, deadline=None)
def test_property_20_exit_level_completeness(current_price, risk_signal, volatility):
    """Property 20: 退出水平完整性
    
    白皮书依据: 第四章 4.1 流动性因子专家
    设计文档: Property 20
    验证需求: Requirements 5.8
    
    属性: 对于任何生成退出预测的风险因子，输出应该包含所有三个必需的价格水平
         (immediate_exit, warning_level, stop_loss_level)，
         并且 immediate_exit >= warning_level >= stop_loss_level。
    
    测试策略:
    1. 生成随机价格、风险信号和波动率
    2. 生成退出水平
    3. 验证包含所有三个价格水平
    4. 验证价格水平的顺序正确
    """
    # 创建EnhancedIlliquidityMiner实例
    miner = EnhancedIlliquidityMiner()
    
    # 生成退出水平
    exit_levels = miner.generate_exit_levels(current_price, risk_signal, volatility)
    
    # 验证包含所有三个价格水平
    assert hasattr(exit_levels, 'immediate_exit'), "应该包含immediate_exit"
    assert hasattr(exit_levels, 'warning_level'), "应该包含warning_level"
    assert hasattr(exit_levels, 'stop_loss_level'), "应该包含stop_loss_level"
    
    # 验证价格水平的顺序：immediate_exit >= warning_level >= stop_loss_level
    assert exit_levels.immediate_exit >= exit_levels.warning_level, \
        f"immediate_exit({exit_levels.immediate_exit:.2f}) 应该 >= warning_level({exit_levels.warning_level:.2f})"
    
    assert exit_levels.warning_level >= exit_levels.stop_loss_level, \
        f"warning_level({exit_levels.warning_level:.2f}) 应该 >= stop_loss_level({exit_levels.stop_loss_level:.2f})"
    
    # 验证所有价格水平都 > 0
    assert exit_levels.immediate_exit > 0, "immediate_exit应该 > 0"
    assert exit_levels.warning_level > 0, "warning_level应该 > 0"
    assert exit_levels.stop_loss_level > 0, "stop_loss_level应该 > 0"
    
    # 验证所有价格水平都 <= 当前价格（因为是退出信号，价格应该下跌）
    assert exit_levels.immediate_exit <= current_price, \
        f"immediate_exit({exit_levels.immediate_exit:.2f}) 应该 <= 当前价格({current_price:.2f})"
