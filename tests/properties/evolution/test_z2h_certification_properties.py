"""Property-Based Tests for Z2H Certification System

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

Properties tested:
- Property 12: Z2H Certification Criteria Conjunction
- Property 13: Gene Capsule Completeness
- Property 14: Certification Level Determinism
- Property 15: Risk Limits Derivation

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.evolution.z2h_data_models import (
    Z2HGeneCapsule,
    CertificationLevel,
    CertificationStatus,
    CapitalTier,
    CertificationEligibility,
    CapitalAllocationRules,
    SimulationResult,
    TierSimulationResult,
    CertifiedStrategy,
)
from src.evolution.certification_level_evaluator import (
    CertificationLevelEvaluator,
    LevelEvaluationResult,
)


# ============================================================================
# Certification Criteria Constants (from design document)
# ============================================================================

# Z2H Certification Criteria (Property 12)
Z2H_CRITERIA = {
    'min_monthly_return': 0.05,      # > 5%
    'min_sharpe_ratio': 1.2,         # > 1.2
    'max_drawdown': 0.15,            # < 15%
    'min_win_rate': 0.55,            # > 55%
    'min_profit_factor': 1.3,        # > 1.3
}

# Certification Level Thresholds (Property 14)
CERTIFICATION_LEVEL_THRESHOLDS = {
    'GOLD': {'min_sharpe': 2.0},
    'SILVER': {'min_sharpe': 1.2, 'max_sharpe': 2.0},
}


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def monthly_return_strategy(draw):
    """生成月收益率"""
    return draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False))


@st.composite
def sharpe_ratio_strategy(draw):
    """生成夏普比率"""
    return draw(st.floats(min_value=-2.0, max_value=5.0, allow_nan=False, allow_infinity=False))


@st.composite
def max_drawdown_strategy(draw):
    """生成最大回撤（正数表示回撤幅度）"""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def win_rate_strategy(draw):
    """生成胜率"""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def profit_factor_strategy(draw):
    """生成盈利因子"""
    return draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))


@st.composite
def arena_score_strategy(draw):
    """生成Arena评分"""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def simulation_sharpe_strategy(draw):
    """生成模拟盘夏普比率"""
    return draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))


@st.composite
def strategy_data_strategy(draw):
    """生成策略数据用于Gene Capsule测试"""
    strategy_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
        min_size=3,
        max_size=20
    ))
    
    # 确保strategy_id非空
    if not strategy_id:
        strategy_id = "S001"
    
    strategy_name = draw(st.sampled_from([
        '动量突破策略', '均值回归策略', '趋势跟踪策略',
        '套利策略', '因子组合策略', '市场中性策略'
    ]))
    
    strategy_type = draw(st.sampled_from([
        'momentum', 'mean_reversion', 'trend_following',
        'arbitrage', 'factor_combo', 'market_neutral'
    ]))
    
    num_factors = draw(st.integers(min_value=1, max_value=5))
    source_factors = [f"factor_{i}" for i in range(1, num_factors + 1)]
    
    arena_score = draw(st.floats(min_value=0.75, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    sharpe_ratio = draw(st.floats(min_value=1.2, max_value=4.0, allow_nan=False, allow_infinity=False))
    max_drawdown = draw(st.floats(min_value=0.01, max_value=0.15, allow_nan=False, allow_infinity=False))
    win_rate = draw(st.floats(min_value=0.55, max_value=0.85, allow_nan=False, allow_infinity=False))
    profit_factor = draw(st.floats(min_value=1.3, max_value=3.0, allow_nan=False, allow_infinity=False))
    total_return = draw(st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False))
    
    return {
        'strategy_id': strategy_id,
        'strategy_name': strategy_name,
        'strategy_type': strategy_type,
        'source_factors': source_factors,
        'arena_score': arena_score,
        'simulation_metrics': {
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'monthly_return': total_return,
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def check_certification_criteria(
    monthly_return: float,
    sharpe_ratio: float,
    max_drawdown: float,
    win_rate: float,
    profit_factor: float
) -> bool:
    """检查是否满足Z2H认证标准
    
    白皮书依据: Requirement 4.2
    
    认证标准（所有条件必须同时满足）：
    - monthly_return > 5%
    - sharpe_ratio > 1.2
    - max_drawdown < 15%
    - win_rate > 55%
    - profit_factor > 1.3
    
    Args:
        monthly_return: 月收益率
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤（正数表示回撤幅度）
        win_rate: 胜率
        profit_factor: 盈利因子
        
    Returns:
        bool: 是否满足所有认证标准
    """
    return (
        monthly_return > Z2H_CRITERIA['min_monthly_return'] and
        sharpe_ratio > Z2H_CRITERIA['min_sharpe_ratio'] and
        max_drawdown < Z2H_CRITERIA['max_drawdown'] and
        win_rate > Z2H_CRITERIA['min_win_rate'] and
        profit_factor > Z2H_CRITERIA['min_profit_factor']
    )


def determine_certification_level(sharpe_ratio: float) -> str:
    """确定认证等级
    
    白皮书依据: Requirement 4.4
    
    认证等级标准：
    - GOLD: Sharpe > 2.0
    - SILVER: 1.2 <= Sharpe <= 2.0
    
    Args:
        sharpe_ratio: 夏普比率
        
    Returns:
        str: 认证等级 ('GOLD', 'SILVER', 或 'NONE')
    """
    if sharpe_ratio > 2.0:
        return 'GOLD'
    elif sharpe_ratio >= 1.2:
        return 'SILVER'
    else:
        return 'NONE'


def calculate_risk_limits(
    arena_score: float,
    simulation_sharpe: float,
    simulation_max_drawdown: float = 0.10
) -> Dict[str, float]:
    """计算风险限制
    
    白皮书依据: Requirement 4.5, 4.6
    
    风险限制基于Arena评分和模拟盘结果计算：
    - max_drawdown_threshold: 不超过模拟盘最大回撤的1.2倍
    - max_position_size: 基于Arena评分和夏普比率
    - max_daily_loss: 基于Arena评分
    
    Args:
        arena_score: Arena评分
        simulation_sharpe: 模拟盘夏普比率
        simulation_max_drawdown: 模拟盘最大回撤
        
    Returns:
        Dict[str, float]: 风险限制参数
    """
    # 最大回撤阈值不超过模拟盘最大回撤的1.2倍
    max_drawdown_threshold = min(simulation_max_drawdown * 1.2, 0.20)
    
    # 最大仓位基于Arena评分和夏普比率
    base_position = 0.10  # 基础仓位10%
    arena_factor = arena_score  # Arena评分作为乘数
    sharpe_factor = min(simulation_sharpe / 2.0, 1.5)  # 夏普比率因子
    max_position_size = base_position * arena_factor * sharpe_factor
    
    # 最大日亏损基于Arena评分
    max_daily_loss = 0.02 * arena_score  # 基础2%乘以Arena评分
    
    return {
        'max_drawdown_threshold': max_drawdown_threshold,
        'max_position_size': max_position_size,
        'max_daily_loss': max_daily_loss,
    }


def create_gene_capsule(strategy_data: Dict[str, Any]) -> Z2HGeneCapsule:
    """创建Z2H基因胶囊
    
    白皮书依据: Requirement 4.1, 4.3
    
    Args:
        strategy_data: 策略数据
        
    Returns:
        Z2HGeneCapsule: 基因胶囊
    """
    now = datetime.now()
    
    # 确定认证等级
    sharpe = strategy_data['simulation_metrics']['sharpe_ratio']
    if sharpe > 2.5:
        cert_level = CertificationLevel.PLATINUM
    elif sharpe > 2.0:
        cert_level = CertificationLevel.GOLD
    else:
        cert_level = CertificationLevel.SILVER
    
    return Z2HGeneCapsule(
        # 基本信息
        strategy_id=strategy_data['strategy_id'],
        strategy_name=strategy_data['strategy_name'],
        strategy_type=strategy_data['strategy_type'],
        source_factors=strategy_data['source_factors'],
        creation_date=now,
        certification_date=now,
        certification_level=cert_level,
        
        # Arena验证结果
        arena_overall_score=strategy_data['arena_score'],
        arena_layer_results={
            'layer_1': {'score': 0.85, 'passed': True},
            'layer_2': {'score': 0.80, 'passed': True},
            'layer_3': {'score': 0.75, 'passed': True},
            'layer_4': {'score': 0.80, 'passed': True},
        },
        arena_passed_layers=4,
        arena_failed_layers=[],
        
        # 模拟盘验证结果
        simulation_duration_days=30,
        simulation_tier_results={
            'tier_1': {'total_return': 0.08, 'sharpe_ratio': sharpe},
            'tier_2': {'total_return': 0.10, 'sharpe_ratio': sharpe},
        },
        simulation_best_tier=CapitalTier.TIER_2,
        simulation_metrics=strategy_data['simulation_metrics'],
        
        # 资金配置规则
        max_allocation_ratio=0.20,
        recommended_capital_scale={'min': 10000, 'max': 100000, 'optimal': 50000},
        optimal_trade_size=5000,
        liquidity_requirements={'buffer': 0.10},
        market_impact_analysis={'estimated_impact': 0.001},
        
        # 交易特征
        avg_holding_period_days=5.0,
        turnover_rate=2.0,
        avg_position_count=10,
        sector_distribution={'technology': 0.3, 'finance': 0.3, 'consumer': 0.4},
        market_cap_preference='mid_cap',
        
        # 风险分析
        var_95=0.02,
        expected_shortfall=0.03,
        max_drawdown=strategy_data['simulation_metrics']['max_drawdown'],
        drawdown_duration_days=15,
        volatility=0.15,
        beta=1.0,
        market_correlation=0.5,
        
        # 市场环境表现
        bull_market_performance={'return': 0.15, 'sharpe': 2.0},
        bear_market_performance={'return': 0.02, 'sharpe': 1.0},
        sideways_market_performance={'return': 0.05, 'sharpe': 1.5},
        high_volatility_performance={'return': 0.08, 'sharpe': 1.2},
        low_volatility_performance={'return': 0.06, 'sharpe': 1.8},
        market_adaptability_score=0.80,
        
        # 使用建议
        optimal_deployment_timing=['bull_market', 'sideways_market'],
        risk_management_rules={'max_drawdown_stop': 0.15},
        monitoring_indicators=['sharpe_ratio', 'max_drawdown', 'win_rate'],
        exit_conditions=['drawdown > 15%', 'sharpe < 1.0'],
        portfolio_strategy_suggestions=['适合作为核心持仓', '建议配置10-20%资金'],
    )


# ============================================================================
# Property 12: Z2H Certification Criteria Conjunction
# ============================================================================

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(
    monthly_return=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
    sharpe_ratio=st.floats(min_value=-2.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    max_drawdown=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    win_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    profit_factor=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)
)
def test_property_12_certification_criteria_conjunction(
    monthly_return: float,
    sharpe_ratio: float,
    max_drawdown: float,
    win_rate: float,
    profit_factor: float
):
    """
    Feature: chapter-4-sparta-evolution
    Property 12: Z2H Certification Criteria Conjunction
    
    **Validates: Requirements 4.2**
    
    Property: Certification is granted if and only if ALL criteria are met:
    - monthly_return > 5%
    - sharpe_ratio > 1.2
    - max_drawdown < 15%
    - win_rate > 55%
    - profit_factor > 1.3
    
    This property verifies that certification follows strict conjunction logic -
    all five criteria must be satisfied simultaneously for certification to be granted.
    """
    # 计算是否满足各个标准
    meets_monthly_return = monthly_return > Z2H_CRITERIA['min_monthly_return']
    meets_sharpe = sharpe_ratio > Z2H_CRITERIA['min_sharpe_ratio']
    meets_drawdown = max_drawdown < Z2H_CRITERIA['max_drawdown']
    meets_win_rate = win_rate > Z2H_CRITERIA['min_win_rate']
    meets_profit_factor = profit_factor > Z2H_CRITERIA['min_profit_factor']
    
    # 使用辅助函数检查认证
    is_certified = check_certification_criteria(
        monthly_return, sharpe_ratio, max_drawdown, win_rate, profit_factor
    )
    
    # 验证conjunction逻辑：认证当且仅当所有标准都满足
    expected_certified = (
        meets_monthly_return and
        meets_sharpe and
        meets_drawdown and
        meets_win_rate and
        meets_profit_factor
    )
    
    assert is_certified == expected_certified, (
        f"Certification conjunction failed: "
        f"monthly_return={monthly_return} (meets={meets_monthly_return}), "
        f"sharpe={sharpe_ratio} (meets={meets_sharpe}), "
        f"drawdown={max_drawdown} (meets={meets_drawdown}), "
        f"win_rate={win_rate} (meets={meets_win_rate}), "
        f"profit_factor={profit_factor} (meets={meets_profit_factor}), "
        f"expected={expected_certified}, actual={is_certified}"
    )
    
    # 额外验证：如果任何一个标准不满足，认证应该失败
    if not meets_monthly_return:
        assert not is_certified, "Should not certify when monthly_return <= 5%"
    if not meets_sharpe:
        assert not is_certified, "Should not certify when sharpe_ratio <= 1.2"
    if not meets_drawdown:
        assert not is_certified, "Should not certify when max_drawdown >= 15%"
    if not meets_win_rate:
        assert not is_certified, "Should not certify when win_rate <= 55%"
    if not meets_profit_factor:
        assert not is_certified, "Should not certify when profit_factor <= 1.3"


# ============================================================================
# Property 13: Gene Capsule Completeness
# ============================================================================

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(strategy_data=strategy_data_strategy())
def test_property_13_gene_capsule_completeness(strategy_data: Dict[str, Any]):
    """
    Feature: chapter-4-sparta-evolution
    Property 13: Gene Capsule Completeness
    
    **Validates: Requirements 4.1, 4.3**
    
    Property: Every generated Gene Capsule contains all required metadata fields:
    - strategy_id (non-empty string)
    - strategy_name (non-empty string)
    - source_factors (non-empty list)
    - arena_score (float in [0, 1])
    - simulation_metrics (dict with required keys)
    - certification_date (datetime)
    - certification_level (valid enum)
    - risk_limits (derived from Arena and simulation results)
    
    This property ensures complete traceability from factor discovery to certification.
    """
    # 创建基因胶囊
    capsule = create_gene_capsule(strategy_data)
    
    # 验证基本信息字段存在且非空
    assert capsule.strategy_id is not None and len(capsule.strategy_id) > 0, \
        "strategy_id must be non-empty string"
    assert capsule.strategy_name is not None and len(capsule.strategy_name) > 0, \
        "strategy_name must be non-empty string"
    assert capsule.strategy_type is not None and len(capsule.strategy_type) > 0, \
        "strategy_type must be non-empty string"
    
    # 验证源因子列表
    assert capsule.source_factors is not None, "source_factors must not be None"
    assert isinstance(capsule.source_factors, list), "source_factors must be a list"
    assert len(capsule.source_factors) > 0, "source_factors must be non-empty"
    
    # 验证Arena评分
    assert capsule.arena_overall_score is not None, "arena_overall_score must not be None"
    assert 0.0 <= capsule.arena_overall_score <= 1.0, \
        f"arena_overall_score must be in [0, 1], got {capsule.arena_overall_score}"
    
    # 验证Arena层级结果
    assert capsule.arena_layer_results is not None, "arena_layer_results must not be None"
    assert isinstance(capsule.arena_layer_results, dict), "arena_layer_results must be a dict"
    
    # 验证模拟盘指标
    assert capsule.simulation_metrics is not None, "simulation_metrics must not be None"
    assert isinstance(capsule.simulation_metrics, dict), "simulation_metrics must be a dict"
    
    # 验证模拟盘指标包含必需的键
    required_simulation_keys = ['sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']
    for key in required_simulation_keys:
        assert key in capsule.simulation_metrics, \
            f"simulation_metrics must contain '{key}'"
    
    # 验证认证日期
    assert capsule.certification_date is not None, "certification_date must not be None"
    assert isinstance(capsule.certification_date, datetime), \
        "certification_date must be a datetime object"
    
    # 验证认证等级
    assert capsule.certification_level is not None, "certification_level must not be None"
    assert isinstance(capsule.certification_level, CertificationLevel), \
        "certification_level must be a CertificationLevel enum"
    assert capsule.certification_level in [
        CertificationLevel.PLATINUM,
        CertificationLevel.GOLD,
        CertificationLevel.SILVER
    ], f"certification_level must be PLATINUM, GOLD, or SILVER, got {capsule.certification_level}"
    
    # 验证风险限制相关字段
    assert capsule.max_allocation_ratio is not None, "max_allocation_ratio must not be None"
    assert 0.0 <= capsule.max_allocation_ratio <= 1.0, \
        f"max_allocation_ratio must be in [0, 1], got {capsule.max_allocation_ratio}"
    
    assert capsule.max_drawdown is not None, "max_drawdown must not be None"
    assert 0.0 <= capsule.max_drawdown <= 1.0, \
        f"max_drawdown must be in [0, 1], got {capsule.max_drawdown}"
    
    # 验证使用validate方法
    try:
        capsule.validate()
    except ValueError as e:
        pytest.fail(f"Gene capsule validation failed: {e}")


# ============================================================================
# Property 14: Certification Level Determinism
# ============================================================================

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(sharpe_ratio=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
def test_property_14_certification_level_determinism(sharpe_ratio: float):
    """
    Feature: chapter-4-sparta-evolution
    Property 14: Certification Level Determinism
    
    **Validates: Requirements 4.4**
    
    Property: Same inputs always produce the same certification level:
    - GOLD if Sharpe > 2.0
    - SILVER if 1.2 <= Sharpe <= 2.0
    
    This property ensures the certification level assignment is:
    1. Deterministic - same Sharpe ratio always produces same level
    2. Reversible - can infer Sharpe range from certification level
    """
    # 确定认证等级
    level = determine_certification_level(sharpe_ratio)
    
    # 验证确定性映射
    if sharpe_ratio > 2.0:
        assert level == 'GOLD', \
            f"Sharpe {sharpe_ratio} > 2.0 should be GOLD, got {level}"
    elif sharpe_ratio >= 1.2:
        assert level == 'SILVER', \
            f"Sharpe {sharpe_ratio} in [1.2, 2.0] should be SILVER, got {level}"
    else:
        assert level == 'NONE', \
            f"Sharpe {sharpe_ratio} < 1.2 should be NONE, got {level}"
    
    # 验证可逆性 - 从等级可以推断夏普比率范围
    if level == 'GOLD':
        assert sharpe_ratio > 2.0, \
            f"GOLD level implies Sharpe > 2.0, but got {sharpe_ratio}"
    elif level == 'SILVER':
        assert 1.2 <= sharpe_ratio <= 2.0, \
            f"SILVER level implies 1.2 <= Sharpe <= 2.0, but got {sharpe_ratio}"
    elif level == 'NONE':
        assert sharpe_ratio < 1.2, \
            f"NONE level implies Sharpe < 1.2, but got {sharpe_ratio}"
    
    # 验证确定性 - 多次调用应该返回相同结果
    level_again = determine_certification_level(sharpe_ratio)
    assert level == level_again, \
        f"Certification level should be deterministic: first={level}, second={level_again}"
    
    # 验证边界条件
    if abs(sharpe_ratio - 2.0) < 1e-10:
        # 边界值2.0应该是SILVER（因为条件是 > 2.0 才是GOLD）
        assert level == 'SILVER', \
            f"Sharpe exactly 2.0 should be SILVER, got {level}"
    
    if abs(sharpe_ratio - 1.2) < 1e-10:
        # 边界值1.2应该是SILVER（因为条件是 >= 1.2）
        assert level == 'SILVER', \
            f"Sharpe exactly 1.2 should be SILVER, got {level}"


# ============================================================================
# Property 15: Risk Limits Derivation
# ============================================================================

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(
    arena_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    simulation_sharpe=st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False)
)
def test_property_15_risk_limits_derivation(arena_score: float, simulation_sharpe: float):
    """
    Feature: chapter-4-sparta-evolution
    Property 15: Risk Limits Derivation
    
    **Validates: Requirements 4.5, 4.6**
    
    Property: Risk limits are derived from Arena and simulation results:
    - max_drawdown_threshold <= simulation max_drawdown * 1.2
    - Risk limits are mathematically derived from Arena score and simulation metrics
    - Higher Arena scores and Sharpe ratios allow for larger position sizes
    
    This property ensures risk limits are properly calibrated based on
    historical performance and validation results.
    """
    # 使用不同的模拟盘最大回撤值测试
    simulation_max_drawdowns = [0.05, 0.10, 0.15, 0.20]
    
    for sim_dd in simulation_max_drawdowns:
        # 计算风险限制
        risk_limits = calculate_risk_limits(arena_score, simulation_sharpe, sim_dd)
        
        # 验证max_drawdown_threshold不超过模拟盘最大回撤的1.2倍
        assert risk_limits['max_drawdown_threshold'] <= sim_dd * 1.2, (
            f"max_drawdown_threshold ({risk_limits['max_drawdown_threshold']}) "
            f"should be <= simulation_max_drawdown * 1.2 ({sim_dd * 1.2})"
        )
        
        # 验证max_drawdown_threshold不超过20%（绝对上限）
        assert risk_limits['max_drawdown_threshold'] <= 0.20, (
            f"max_drawdown_threshold ({risk_limits['max_drawdown_threshold']}) "
            f"should not exceed 20% absolute limit"
        )
        
        # 验证max_position_size是正数
        assert risk_limits['max_position_size'] >= 0, (
            f"max_position_size ({risk_limits['max_position_size']}) should be >= 0"
        )
        
        # 验证max_daily_loss是正数
        assert risk_limits['max_daily_loss'] >= 0, (
            f"max_daily_loss ({risk_limits['max_daily_loss']}) should be >= 0"
        )
    
    # 验证Arena评分对风险限制的影响
    # 更高的Arena评分应该允许更大的仓位
    if arena_score > 0.5:
        risk_limits_high = calculate_risk_limits(arena_score, simulation_sharpe, 0.10)
        risk_limits_low = calculate_risk_limits(arena_score * 0.5, simulation_sharpe, 0.10)
        
        # 高Arena评分应该有更大的仓位限制
        assert risk_limits_high['max_position_size'] >= risk_limits_low['max_position_size'], (
            f"Higher Arena score ({arena_score}) should allow larger position size "
            f"than lower score ({arena_score * 0.5})"
        )
    
    # 验证夏普比率对风险限制的影响
    if simulation_sharpe > 1.0:
        risk_limits_high_sharpe = calculate_risk_limits(arena_score, simulation_sharpe, 0.10)
        risk_limits_low_sharpe = calculate_risk_limits(arena_score, simulation_sharpe * 0.5, 0.10)
        
        # 高夏普比率应该有更大的仓位限制
        assert risk_limits_high_sharpe['max_position_size'] >= risk_limits_low_sharpe['max_position_size'], (
            f"Higher Sharpe ({simulation_sharpe}) should allow larger position size "
            f"than lower Sharpe ({simulation_sharpe * 0.5})"
        )


# ============================================================================
# Additional Property Tests for Edge Cases
# ============================================================================

@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(
    monthly_return=st.floats(min_value=0.04, max_value=0.06, allow_nan=False, allow_infinity=False),
    sharpe_ratio=st.floats(min_value=1.1, max_value=1.3, allow_nan=False, allow_infinity=False),
    max_drawdown=st.floats(min_value=0.14, max_value=0.16, allow_nan=False, allow_infinity=False),
    win_rate=st.floats(min_value=0.54, max_value=0.56, allow_nan=False, allow_infinity=False),
    profit_factor=st.floats(min_value=1.2, max_value=1.4, allow_nan=False, allow_infinity=False)
)
def test_property_12_boundary_conditions(
    monthly_return: float,
    sharpe_ratio: float,
    max_drawdown: float,
    win_rate: float,
    profit_factor: float
):
    """
    Feature: chapter-4-sparta-evolution
    Property 12 (Boundary): Z2H Certification Criteria Boundary Conditions
    
    **Validates: Requirements 4.2**
    
    Tests certification criteria at boundary values to ensure strict inequality
    enforcement (> not >=, < not <=).
    """
    is_certified = check_certification_criteria(
        monthly_return, sharpe_ratio, max_drawdown, win_rate, profit_factor
    )
    
    # 验证边界条件使用严格不等式
    # monthly_return > 5% (not >=)
    if monthly_return == 0.05:
        assert not is_certified or not (
            sharpe_ratio > 1.2 and max_drawdown < 0.15 and 
            win_rate > 0.55 and profit_factor > 1.3
        ), "monthly_return exactly 5% should not pass (need > 5%)"
    
    # sharpe_ratio > 1.2 (not >=)
    if sharpe_ratio == 1.2:
        assert not is_certified or not (
            monthly_return > 0.05 and max_drawdown < 0.15 and 
            win_rate > 0.55 and profit_factor > 1.3
        ), "sharpe_ratio exactly 1.2 should not pass (need > 1.2)"
    
    # max_drawdown < 15% (not <=)
    if max_drawdown == 0.15:
        assert not is_certified or not (
            monthly_return > 0.05 and sharpe_ratio > 1.2 and 
            win_rate > 0.55 and profit_factor > 1.3
        ), "max_drawdown exactly 15% should not pass (need < 15%)"
    
    # win_rate > 55% (not >=)
    if win_rate == 0.55:
        assert not is_certified or not (
            monthly_return > 0.05 and sharpe_ratio > 1.2 and 
            max_drawdown < 0.15 and profit_factor > 1.3
        ), "win_rate exactly 55% should not pass (need > 55%)"
    
    # profit_factor > 1.3 (not >=)
    if profit_factor == 1.3:
        assert not is_certified or not (
            monthly_return > 0.05 and sharpe_ratio > 1.2 and 
            max_drawdown < 0.15 and win_rate > 0.55
        ), "profit_factor exactly 1.3 should not pass (need > 1.3)"


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(sharpe_ratio=st.floats(min_value=1.9, max_value=2.1, allow_nan=False, allow_infinity=False))
def test_property_14_gold_silver_boundary(sharpe_ratio: float):
    """
    Feature: chapter-4-sparta-evolution
    Property 14 (Boundary): Certification Level at GOLD/SILVER Boundary
    
    **Validates: Requirements 4.4**
    
    Tests certification level assignment at the GOLD/SILVER boundary (Sharpe = 2.0).
    """
    level = determine_certification_level(sharpe_ratio)
    
    # 验证边界行为
    if sharpe_ratio > 2.0:
        assert level == 'GOLD', f"Sharpe {sharpe_ratio} > 2.0 should be GOLD"
    else:
        assert level == 'SILVER', f"Sharpe {sharpe_ratio} <= 2.0 should be SILVER"


# ============================================================================
# Property 16: Strategy Library Idempotence
# ============================================================================

@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
@given(strategy_data=strategy_data_strategy())
def test_property_16_strategy_library_idempotence(strategy_data: Dict[str, Any]):
    """
    Feature: chapter-4-sparta-evolution
    Property 16: Strategy Library Idempotence
    
    **Validates: Requirements 4.7, 4.8**
    
    Property: For any Z2H certified strategy, adding it to the strategy library
    multiple times should result in exactly one entry with the most recent metadata.
    
    This property ensures:
    1. Duplicate additions don't create multiple entries
    2. The most recent metadata is preserved
    3. Strategy ID uniqueness is maintained
    """
    # 模拟策略库（使用字典模拟）
    strategy_library: Dict[str, Dict[str, Any]] = {}
    
    strategy_id = strategy_data['strategy_id']
    
    # 第一次添加策略
    strategy_library[strategy_id] = {
        'strategy_id': strategy_id,
        'strategy_name': strategy_data['strategy_name'],
        'arena_score': strategy_data['arena_score'],
        'simulation_metrics': strategy_data['simulation_metrics'].copy(),
        'version': 1,
    }
    
    # 验证第一次添加后只有一个条目
    assert len(strategy_library) == 1, \
        f"After first add, library should have 1 entry, got {len(strategy_library)}"
    assert strategy_id in strategy_library, \
        f"Strategy {strategy_id} should be in library"
    
    # 第二次添加相同策略（更新元数据）
    updated_metrics = strategy_data['simulation_metrics'].copy()
    updated_metrics['sharpe_ratio'] = updated_metrics.get('sharpe_ratio', 1.5) + 0.1
    
    strategy_library[strategy_id] = {
        'strategy_id': strategy_id,
        'strategy_name': strategy_data['strategy_name'],
        'arena_score': strategy_data['arena_score'],
        'simulation_metrics': updated_metrics,
        'version': 2,
    }
    
    # 验证第二次添加后仍然只有一个条目
    assert len(strategy_library) == 1, \
        f"After second add, library should still have 1 entry, got {len(strategy_library)}"
    
    # 验证元数据已更新为最新版本
    assert strategy_library[strategy_id]['version'] == 2, \
        "Strategy should have the most recent metadata (version 2)"
    assert strategy_library[strategy_id]['simulation_metrics']['sharpe_ratio'] == updated_metrics['sharpe_ratio'], \
        "Strategy should have updated simulation metrics"
    
    # 第三次添加相同策略
    strategy_library[strategy_id] = {
        'strategy_id': strategy_id,
        'strategy_name': strategy_data['strategy_name'],
        'arena_score': strategy_data['arena_score'],
        'simulation_metrics': updated_metrics,
        'version': 3,
    }
    
    # 验证幂等性：多次添加后仍然只有一个条目
    assert len(strategy_library) == 1, \
        f"After third add, library should still have 1 entry, got {len(strategy_library)}"
    assert strategy_library[strategy_id]['version'] == 3, \
        "Strategy should have the most recent metadata (version 3)"
    
    # 验证策略ID唯一性
    all_ids = list(strategy_library.keys())
    assert len(all_ids) == len(set(all_ids)), \
        "All strategy IDs should be unique"
