"""
因子生命周期管理器属性测试 (Factor Lifecycle Manager Property Tests)

白皮书依据: 第四章 4.2.4 因子生命周期管理
测试框架: pytest + hypothesis

Property 26: Factor Weight Adaptation
Property 27: Factor Lifecycle Archival Completeness
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.evolution.factor_lifecycle_manager import (
    FactorLifecycleManager,
    FactorInfo,
    FactorStatus,
    MarketRegime,
    ArchivedFactor,
    LifecycleReport
)
from src.evolution.arena.factor_performance_monitor import (
    FactorPerformanceMonitor,
    PerformanceMetrics,
    FactorDecayStatus,
    DegradationSeverity
)


# ========== Test Strategies ==========

@st.composite
def factor_registration_strategy(draw):
    """生成因子注册参数策略"""
    factor_id = draw(st.text(
        min_size=1, max_size=20,
        alphabet=st.characters(whitelist_categories=('L', 'N'))
    ))
    name = draw(st.text(
        min_size=1, max_size=50,
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'))
    ))
    expression = draw(st.text(
        min_size=1, max_size=100,
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Zs'))
    ))
    baseline_ic = draw(st.floats(
        min_value=-0.5, max_value=0.5,
        allow_nan=False, allow_infinity=False
    ))
    arena_score = draw(st.floats(
        min_value=0.0, max_value=1.0,
        allow_nan=False, allow_infinity=False
    ))
    z2h_certified = draw(st.booleans())
    
    return {
        'factor_id': factor_id,
        'name': name,
        'expression': expression,
        'baseline_ic': baseline_ic,
        'arena_score': arena_score,
        'z2h_certified': z2h_certified
    }


@st.composite
def performance_metrics_strategy(draw):
    """生成性能指标策略"""
    factor_id = draw(st.text(
        min_size=1, max_size=20,
        alphabet=st.characters(whitelist_categories=('L', 'N'))
    ))
    
    rolling_ic = {
        1: draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)),
        5: draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)),
        10: draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)),
        20: draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False))
    }
    
    return PerformanceMetrics(
        factor_id=factor_id,
        timestamp=datetime.now(),
        rolling_ic=rolling_ic,
        ir=draw(st.floats(min_value=-5.0, max_value=5.0, allow_nan=False)),
        sharpe_ratio=draw(st.floats(min_value=-3.0, max_value=5.0, allow_nan=False)),
        turnover_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        health_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        ic_decay_rate=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    )


@st.composite
def weight_adaptation_inputs_strategy(draw):
    """生成权重调整输入策略"""
    health_score = draw(st.floats(
        min_value=0.0, max_value=1.0,
        allow_nan=False, allow_infinity=False
    ))
    current_weight = draw(st.floats(
        min_value=0.1, max_value=3.0,
        allow_nan=False, allow_infinity=False
    ))
    
    return {
        'health_score': health_score,
        'current_weight': current_weight
    }


# ========== Property 26: Factor Weight Adaptation ==========

class TestProperty26FactorWeightAdaptation:
    """Property 26: 因子权重自适应
    
    **Validates: Requirements 7.4**
    
    验证因子权重调整的正确性:
    1. 权重始终在有效范围内 [MIN_WEIGHT, MAX_WEIGHT]
    2. 高健康评分导致权重增加
    3. 低健康评分导致权重降低
    4. 权重变化记录完整
    """
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weight_always_in_valid_range(self, params):
        """测试权重始终在有效范围内
        
        **Validates: Requirements 7.4**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        factor = manager.register_factor(**params)
        
        # 创建不同健康评分的性能指标
        for health_score in [0.0, 0.3, 0.5, 0.7, 1.0]:
            metrics = PerformanceMetrics(
                factor_id=params['factor_id'],
                timestamp=datetime.now(),
                rolling_ic={1: 0.05, 5: 0.05, 10: 0.05, 20: 0.05},
                ir=1.0,
                sharpe_ratio=1.5,
                turnover_rate=0.3,
                health_score=health_score,
                ic_decay_rate=0.1
            )
            
            new_weight = manager.adapt_factor_weight(params['factor_id'], metrics)
            
            # 验证权重范围
            assert manager.MIN_WEIGHT <= new_weight <= manager.MAX_WEIGHT, \
                f"权重超出范围: {new_weight}"
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_high_health_increases_weight(self, params):
        """测试高健康评分增加权重
        
        **Validates: Requirements 7.4**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        factor = manager.register_factor(**params)
        initial_weight = factor.weight
        
        # 高健康评分
        metrics = PerformanceMetrics(
            factor_id=params['factor_id'],
            timestamp=datetime.now(),
            rolling_ic={1: 0.1, 5: 0.1, 10: 0.1, 20: 0.1},
            ir=2.0,
            sharpe_ratio=2.0,
            turnover_rate=0.3,
            health_score=0.9,  # 高健康评分
            ic_decay_rate=0.0
        )
        
        new_weight = manager.adapt_factor_weight(params['factor_id'], metrics)
        
        # 验证权重增加（除非已达上限）
        if initial_weight < manager.MAX_WEIGHT:
            assert new_weight >= initial_weight, \
                f"高健康评分应增加权重: {initial_weight} -> {new_weight}"
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_low_health_decreases_weight(self, params):
        """测试低健康评分降低权重
        
        **Validates: Requirements 7.4**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        factor = manager.register_factor(**params)
        initial_weight = factor.weight
        
        # 低健康评分
        metrics = PerformanceMetrics(
            factor_id=params['factor_id'],
            timestamp=datetime.now(),
            rolling_ic={1: 0.01, 5: 0.01, 10: 0.01, 20: 0.01},
            ir=0.5,
            sharpe_ratio=0.5,
            turnover_rate=0.3,
            health_score=0.2,  # 低健康评分
            ic_decay_rate=0.5
        )
        
        new_weight = manager.adapt_factor_weight(params['factor_id'], metrics)
        
        # 验证权重降低（除非已达下限）
        if initial_weight > manager.MIN_WEIGHT:
            assert new_weight <= initial_weight, \
                f"低健康评分应降低权重: {initial_weight} -> {new_weight}"
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weight_history_recorded(self, params):
        """测试权重历史记录完整
        
        **Validates: Requirements 7.4**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 多次调整权重
        for i in range(5):
            metrics = PerformanceMetrics(
                factor_id=params['factor_id'],
                timestamp=datetime.now(),
                rolling_ic={1: 0.05, 5: 0.05, 10: 0.05, 20: 0.05},
                ir=1.0,
                sharpe_ratio=1.5,
                turnover_rate=0.3,
                health_score=0.5 + i * 0.1,
                ic_decay_rate=0.1
            )
            manager.adapt_factor_weight(params['factor_id'], metrics)
        
        # 验证历史记录
        history = manager.get_weight_history(params['factor_id'])
        assert len(history) >= 6, f"权重历史记录不完整: {len(history)}"  # 初始 + 5次调整
        
        # 验证时间戳递增
        for i in range(1, len(history)):
            assert history[i][0] >= history[i-1][0], "时间戳应递增"


# ========== Property 27: Factor Lifecycle Archival Completeness ==========

class TestProperty27FactorLifecycleArchivalCompleteness:
    """Property 27: 因子生命周期归档完整性
    
    **Validates: Requirements 7.8**
    
    验证因子归档的完整性:
    1. 退役因子包含完整元数据
    2. 归档因子包含性能历史
    3. 归档因子状态正确
    4. 归档因子可检索
    """
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_retired_factor_has_complete_metadata(self, params):
        """测试退役因子包含完整元数据
        
        **Validates: Requirements 7.8**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 退役因子
        archived = await manager.retire_factor(
            params['factor_id'],
            reason="测试退役",
            convert_to_risk=False
        )
        
        # 验证归档完整性
        assert archived is not None
        assert archived.factor_info.factor_id == params['factor_id']
        assert archived.factor_info.name == params['name']
        assert archived.factor_info.expression == params['expression']
        assert archived.retirement_reason == "测试退役"
        assert isinstance(archived.archived_at, datetime)
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_archived_factor_status_correct(self, params):
        """测试归档因子状态正确
        
        **Validates: Requirements 7.8**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 退役因子
        await manager.retire_factor(params['factor_id'], reason="测试退役")
        
        # 验证状态
        factor = manager.get_factor(params['factor_id'])
        assert factor.status == FactorStatus.RETIRED
        
        # 归档因子
        archived = manager.archive_factor(params['factor_id'])
        
        # 验证归档状态
        assert archived is not None
        assert archived.factor_info.status == FactorStatus.ARCHIVED
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_archived_factor_retrievable(self, params):
        """测试归档因子可检索
        
        **Validates: Requirements 7.8**
        """
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 退役并归档
        await manager.retire_factor(params['factor_id'], reason="测试退役")
        manager.archive_factor(params['factor_id'])
        
        # 检索归档因子
        archived = manager.get_archived_factor(params['factor_id'])
        
        assert archived is not None
        assert archived.factor_info.factor_id == params['factor_id']
        
        # 检索所有归档因子
        all_archived = manager.get_all_archived_factors()
        assert len(all_archived) >= 1
        assert any(a.factor_info.factor_id == params['factor_id'] for a in all_archived)


# ========== Additional Property Tests ==========

class TestFactorRegistration:
    """因子注册测试"""
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_factor_registration_creates_valid_factor(self, params):
        """测试因子注册创建有效因子"""
        manager = FactorLifecycleManager()
        
        factor = manager.register_factor(**params)
        
        # 验证因子信息
        assert factor.factor_id == params['factor_id']
        assert factor.name == params['name']
        assert factor.expression == params['expression']
        assert factor.baseline_ic == params['baseline_ic']
        assert factor.arena_score == params['arena_score']
        assert factor.z2h_certified == params['z2h_certified']
        assert factor.status == FactorStatus.ACTIVE
        assert factor.weight == 1.0
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_duplicate_registration_raises_error(self, params):
        """测试重复注册抛出错误"""
        manager = FactorLifecycleManager()
        
        # 第一次注册
        manager.register_factor(**params)
        
        # 第二次注册应抛出错误
        with pytest.raises(ValueError, match="已存在"):
            manager.register_factor(**params)


class TestMarketRegimeAdaptation:
    """市场环境适应测试"""
    
    @given(
        params=factor_registration_strategy(),
        regime=st.sampled_from(list(MarketRegime)),
        weight=st.floats(min_value=0.0, max_value=3.0, allow_nan=False)
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_regime_weight_setting(self, params, regime, weight):
        """测试市场环境权重设置"""
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 设置市场环境权重
        manager.set_regime_weight(params['factor_id'], regime, weight)
        
        # 验证权重设置
        factor = manager.get_factor(params['factor_id'])
        assert factor.regime_weights[regime.value] == weight
    
    @given(regime=st.sampled_from(list(MarketRegime)))
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_market_regime_update(self, regime):
        """测试市场环境更新"""
        manager = FactorLifecycleManager()
        
        # 更新市场环境
        manager.update_market_regime(regime)
        
        # 验证更新
        assert manager._current_regime == regime


class TestLifecycleReport:
    """生命周期报告测试"""
    
    def test_empty_report_generation(self):
        """测试空报告生成"""
        manager = FactorLifecycleManager()
        
        report = manager.generate_lifecycle_report()
        
        assert isinstance(report, LifecycleReport)
        assert report.total_factors == 0
        assert report.active_factors == 0
        assert report.degrading_factors == 0
        assert report.retired_factors == 0
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_report_with_factors(self, params):
        """测试有因子时的报告生成"""
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        report = manager.generate_lifecycle_report()
        
        assert report.total_factors == 1
        assert report.active_factors == 1
        assert isinstance(report.attribution_analysis, dict)


class TestDecayHandling:
    """衰减处理测试"""
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_mild_decay_reduces_weight(self, params):
        """测试轻微衰减降低权重"""
        manager = FactorLifecycleManager()
        
        # 注册因子
        factor = manager.register_factor(**params)
        initial_weight = factor.weight
        
        # 轻微衰减
        decay_status = FactorDecayStatus(
            factor_id=params['factor_id'],
            is_decaying=True,
            severity=DegradationSeverity.MILD,
            health_score=0.6,
            ic_decay_rate=0.3,
            recommendation="降低权重"
        )
        
        await manager.handle_factor_decay(params['factor_id'], decay_status)
        
        # 验证权重降低
        factor = manager.get_factor(params['factor_id'])
        assert factor.weight < initial_weight
        assert factor.status == FactorStatus.DEGRADING
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_moderate_decay_pauses_factor(self, params):
        """测试中度衰减暂停因子"""
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 中度衰减
        decay_status = FactorDecayStatus(
            factor_id=params['factor_id'],
            is_decaying=True,
            severity=DegradationSeverity.MODERATE,
            health_score=0.4,
            ic_decay_rate=0.5,
            recommendation="暂停使用"
        )
        
        await manager.handle_factor_decay(params['factor_id'], decay_status)
        
        # 验证状态
        factor = manager.get_factor(params['factor_id'])
        assert factor.status == FactorStatus.PAUSED
    
    @given(params=factor_registration_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_severe_decay_retires_factor(self, params):
        """测试严重衰减退役因子"""
        manager = FactorLifecycleManager()
        
        # 注册因子
        manager.register_factor(**params)
        
        # 严重衰减
        decay_status = FactorDecayStatus(
            factor_id=params['factor_id'],
            is_decaying=True,
            severity=DegradationSeverity.SEVERE,
            health_score=0.2,
            ic_decay_rate=0.8,
            recommendation="立即退役"
        )
        
        await manager.handle_factor_decay(params['factor_id'], decay_status)
        
        # 验证状态
        factor = manager.get_factor(params['factor_id'])
        assert factor.status == FactorStatus.RETIRED


# ========== Edge Case Tests ==========

class TestEdgeCases:
    """边界情况测试"""
    
    def test_get_nonexistent_factor_returns_none(self):
        """测试获取不存在的因子返回None"""
        manager = FactorLifecycleManager()
        
        factor = manager.get_factor("nonexistent")
        assert factor is None
    
    def test_empty_factor_id_raises_error(self):
        """测试空因子ID抛出错误"""
        manager = FactorLifecycleManager()
        
        with pytest.raises(ValueError, match="不能为空"):
            manager.register_factor(
                factor_id="",
                name="test",
                expression="close/open",
                baseline_ic=0.05
            )
    
    def test_empty_name_raises_error(self):
        """测试空名称抛出错误"""
        manager = FactorLifecycleManager()
        
        with pytest.raises(ValueError, match="不能为空"):
            manager.register_factor(
                factor_id="test",
                name="",
                expression="close/open",
                baseline_ic=0.05
            )
    
    def test_adapt_weight_nonexistent_factor_raises_error(self):
        """测试调整不存在因子的权重抛出错误"""
        manager = FactorLifecycleManager()
        
        metrics = PerformanceMetrics(
            factor_id="nonexistent",
            timestamp=datetime.now(),
            rolling_ic={1: 0.05, 5: 0.05, 10: 0.05, 20: 0.05},
            ir=1.0,
            sharpe_ratio=1.5,
            turnover_rate=0.3,
            health_score=0.7,
            ic_decay_rate=0.1
        )
        
        with pytest.raises(ValueError, match="不存在"):
            manager.adapt_factor_weight("nonexistent", metrics)
    
    def test_invalid_regime_weight_raises_error(self):
        """测试无效市场环境权重抛出错误"""
        manager = FactorLifecycleManager()
        
        manager.register_factor(
            factor_id="test",
            name="test",
            expression="close/open",
            baseline_ic=0.05
        )
        
        with pytest.raises(ValueError, match="权重必须在"):
            manager.set_regime_weight("test", MarketRegime.BULL, -1.0)
        
        with pytest.raises(ValueError, match="权重必须在"):
            manager.set_regime_weight("test", MarketRegime.BULL, 10.0)
