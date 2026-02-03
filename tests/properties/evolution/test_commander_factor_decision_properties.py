"""Commander因子决策引擎属性测试

白皮书依据: 第四章 4.2.3 Commander因子集成

测试Commander因子决策引擎的核心属性：
- Property 28: Commander Integration Completeness
- Property 29: Multi-Factor Signal Combination
- Property 30: Recommendation Conflict Resolution
- Property 31: Regime-Based Weight Adjustment
- Property 32: Recommendation Attribution Completeness
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, List, Any

from src.evolution.commander_factor_decision import (
    CommanderFactorDecisionEngine,
    IntegratedFactor,
    FactorRecommendation,
    RecommendationAction,
    MarketRegime,
    RiskMetrics,
    FactorPerformanceTracker,
    FactorCorrelationMatrix
)


# ============================================================================
# 测试数据生成策略
# ============================================================================

@st.composite
def arena_result_strategy(draw) -> Dict[str, Any]:
    """生成Arena测试结果"""
    factor_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=3,
        max_size=10
    ))
    
    passed = draw(st.booleans())
    overall_score = draw(st.floats(min_value=0.5, max_value=1.0)) if passed else draw(st.floats(min_value=0.0, max_value=0.5))
    
    return {
        "factor_id": factor_id,
        "name": f"Factor_{factor_id}",
        "expression": f"close / delay(close, 1) - 1",
        "passed": passed,
        "overall_score": overall_score,
        "reality_score": draw(st.floats(min_value=0.01, max_value=0.1)),
        "z2h_eligible": passed and overall_score > 0.7
    }


@st.composite
def market_data_strategy(draw) -> pd.DataFrame:
    """生成市场数据"""
    n_days = draw(st.integers(min_value=20, max_value=100))
    n_stocks = draw(st.integers(min_value=5, max_value=20))
    
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
    
    # 生成价格数据
    data = {}
    for symbol in symbols:
        base_price = draw(st.floats(min_value=10.0, max_value=100.0))
        returns = np.random.normal(0.001, 0.02, n_days)
        prices = base_price * np.cumprod(1 + returns)
        data[symbol] = prices
    
    return pd.DataFrame(data, index=dates)


@st.composite
def factor_values_strategy(draw, symbols: List[str]) -> Dict[str, pd.Series]:
    """生成因子值"""
    n_factors = draw(st.integers(min_value=1, max_value=5))
    
    factor_values = {}
    for i in range(n_factors):
        factor_id = f"factor_{i}"
        values = draw(st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False),
            min_size=len(symbols),
            max_size=len(symbols)
        ))
        factor_values[factor_id] = pd.Series(values, index=symbols)
    
    return factor_values


# ============================================================================
# Property 28: Commander Integration Completeness
# ============================================================================

class TestProperty28CommanderIntegrationCompleteness:
    """Property 28: Commander集成完整性
    
    **Validates: Requirements 8.1, 8.2**
    
    验证Arena验证的因子能够正确集成到Commander决策引擎中，
    并且初始权重基于Arena得分正确计算。
    """
    
    @pytest.fixture
    def engine(self):
        """创建Commander因子决策引擎"""
        return CommanderFactorDecisionEngine()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(arena_results=st.lists(arena_result_strategy(), min_size=1, max_size=10))
    def test_passed_factors_are_integrated(self, engine, arena_results):
        """测试通过的因子被正确集成
        
        **Validates: Requirements 8.1**
        """
        # 执行集成
        integrated_count = asyncio.run(engine.integrate_arena_factors(arena_results))
        
        # 验证：通过的因子数量等于集成数量
        passed_count = sum(1 for r in arena_results if r.get("passed", False))
        assert integrated_count == passed_count
        
        # 验证：所有通过的因子都在validated_factors中
        for result in arena_results:
            if result.get("passed", False):
                assert result["factor_id"] in engine.validated_factors
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(arena_results=st.lists(arena_result_strategy(), min_size=1, max_size=10))
    def test_initial_weight_based_on_arena_score(self, engine, arena_results):
        """测试初始权重基于Arena得分计算
        
        **Validates: Requirements 8.2**
        """
        asyncio.run(engine.integrate_arena_factors(arena_results))
        
        for factor_id, factor in engine.validated_factors.items():
            # 验证：初始权重在有效范围内
            assert 0.1 <= factor.initial_weight <= 1.0
            
            # 验证：Z2H认证因子权重更高
            if factor.z2h_certified:
                # Z2H认证因子的权重应该有加成
                base_weight = factor.arena_score
                assert factor.initial_weight >= base_weight
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(arena_results=st.lists(arena_result_strategy(), min_size=1, max_size=5))
    def test_performance_tracker_initialized(self, engine, arena_results):
        """测试性能跟踪器正确初始化
        
        **Validates: Requirements 8.1**
        """
        asyncio.run(engine.integrate_arena_factors(arena_results))
        
        for factor_id in engine.validated_factors:
            # 验证：每个因子都有性能跟踪器
            assert factor_id in engine.factor_performance
            
            tracker = engine.factor_performance[factor_id]
            assert tracker.factor_id == factor_id
            assert tracker.baseline_ic > 0


# ============================================================================
# Property 29: Multi-Factor Signal Combination
# ============================================================================

class TestProperty29MultiFactorSignalCombination:
    """Property 29: 多因子信号组合
    
    **Validates: Requirements 8.3, 8.4**
    
    验证多个因子的信号能够正确组合，生成买入/卖出/持有建议。
    """
    
    @pytest.fixture
    def engine_with_factors(self):
        """创建带有因子的引擎"""
        engine = CommanderFactorDecisionEngine()
        
        # 添加测试因子
        arena_results = [
            {
                "factor_id": "factor_1",
                "name": "Momentum",
                "expression": "close / delay(close, 20) - 1",
                "passed": True,
                "overall_score": 0.8,
                "reality_score": 0.05,
                "z2h_eligible": True
            },
            {
                "factor_id": "factor_2",
                "name": "Value",
                "expression": "1 / pe_ratio",
                "passed": True,
                "overall_score": 0.75,
                "reality_score": 0.04,
                "z2h_eligible": True
            }
        ]
        
        asyncio.run(engine.integrate_arena_factors(arena_results))
        return engine
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(n_stocks=st.integers(min_value=10, max_value=50))
    def test_recommendations_generated_for_extreme_ranks(self, engine_with_factors, n_stocks):
        """测试极端排名股票生成建议
        
        **Validates: Requirements 8.3**
        """
        # 创建市场数据
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
        
        market_data = pd.DataFrame(
            np.random.uniform(10, 100, (30, n_stocks)),
            index=dates,
            columns=symbols
        )
        
        # 创建因子值
        factor_values = {
            "factor_1": pd.Series(np.linspace(0, 1, n_stocks), index=symbols),
            "factor_2": pd.Series(np.linspace(0.5, 1.5, n_stocks), index=symbols)
        }
        
        # 生成建议
        recommendations = asyncio.run(
            engine_with_factors.generate_factor_based_recommendations(
                market_data, factor_values
            )
        )
        
        # 验证：有建议生成
        assert len(recommendations) > 0
        
        # 验证：建议包含买入和/或卖出
        actions = {rec.action for rec in recommendations}
        assert RecommendationAction.BUY in actions or RecommendationAction.SELL in actions
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(n_stocks=st.integers(min_value=10, max_value=30))
    def test_factor_weights_applied(self, engine_with_factors, n_stocks):
        """测试因子权重正确应用
        
        **Validates: Requirements 8.4**
        """
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
        
        market_data = pd.DataFrame(
            np.random.uniform(10, 100, (30, n_stocks)),
            index=dates,
            columns=symbols
        )
        
        factor_values = {
            "factor_1": pd.Series(np.linspace(0, 1, n_stocks), index=symbols),
            "factor_2": pd.Series(np.linspace(0.5, 1.5, n_stocks), index=symbols)
        }
        
        recommendations = asyncio.run(
            engine_with_factors.generate_factor_based_recommendations(
                market_data, factor_values
            )
        )
        
        # 验证：所有建议的置信度在有效范围内
        for rec in recommendations:
            assert 0.0 <= rec.confidence <= 1.0
            assert 0.0 <= rec.target_weight <= 1.0
    
    def test_buy_sell_hold_actions_generated(self, engine_with_factors):
        """测试生成买入/卖出/持有建议
        
        **Validates: Requirements 8.4**
        """
        n_stocks = 20
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
        
        market_data = pd.DataFrame(
            np.random.uniform(10, 100, (30, n_stocks)),
            index=dates,
            columns=symbols
        )
        
        # 设置持仓（用于生成卖出建议）
        engine_with_factors.update_holdings({
            "STOCK_000": 0.1,
            "STOCK_001": 0.1
        })
        
        factor_values = {
            "factor_1": pd.Series(np.linspace(0, 1, n_stocks), index=symbols),
            "factor_2": pd.Series(np.linspace(0.5, 1.5, n_stocks), index=symbols)
        }
        
        recommendations = asyncio.run(
            engine_with_factors.generate_factor_based_recommendations(
                market_data, factor_values
            )
        )
        
        # 验证：建议动作是有效的枚举值
        for rec in recommendations:
            assert rec.action in [RecommendationAction.BUY, RecommendationAction.SELL, RecommendationAction.HOLD]


# ============================================================================
# Property 30: Recommendation Conflict Resolution
# ============================================================================

class TestProperty30RecommendationConflictResolution:
    """Property 30: 建议冲突解决
    
    **Validates: Requirements 8.5**
    
    验证当多个因子对同一股票产生冲突建议时，
    系统能够使用置信度正确解决冲突。
    """
    
    @pytest.fixture
    def engine(self):
        """创建引擎"""
        return CommanderFactorDecisionEngine()
    
    def test_conflict_resolved_by_confidence(self, engine):
        """测试冲突通过置信度解决
        
        **Validates: Requirements 8.5**
        """
        # 创建冲突建议
        buy_rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.BUY,
            target_weight=0.05,
            confidence=0.8,
            factor_source="factor_1",
            factor_value=0.9,
            factor_rank=0.9,
            reasoning="买入建议"
        )
        
        sell_rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.SELL,
            target_weight=0.0,
            confidence=0.3,
            factor_source="factor_2",
            factor_value=0.1,
            factor_rank=0.1,
            reasoning="卖出建议"
        )
        
        # 解决冲突
        resolved = asyncio.run(engine._resolve_conflicts([buy_rec, sell_rec]))
        
        # 验证：只有一个建议
        assert len(resolved) == 1
        
        # 验证：买入建议胜出（置信度更高）
        assert resolved[0].action == RecommendationAction.BUY
    
    def test_conflict_resolution_adjusts_confidence(self, engine):
        """测试冲突解决调整置信度
        
        **Validates: Requirements 8.5**
        """
        buy_rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.BUY,
            target_weight=0.05,
            confidence=0.6,
            factor_source="factor_1",
            factor_value=0.9,
            factor_rank=0.9,
            reasoning="买入建议"
        )
        
        sell_rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.SELL,
            target_weight=0.0,
            confidence=0.4,
            factor_source="factor_2",
            factor_value=0.1,
            factor_rank=0.1,
            reasoning="卖出建议"
        )
        
        resolved = asyncio.run(engine._resolve_conflicts([buy_rec, sell_rec]))
        
        # 验证：置信度被调整
        assert resolved[0].confidence < buy_rec.confidence
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        buy_confidence=st.floats(min_value=0.1, max_value=0.9),
        sell_confidence=st.floats(min_value=0.1, max_value=0.9)
    )
    def test_higher_confidence_wins(self, engine, buy_confidence, sell_confidence):
        """测试更高置信度的建议胜出
        
        **Validates: Requirements 8.5**
        """
        buy_rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.BUY,
            target_weight=0.05,
            confidence=buy_confidence,
            factor_source="factor_1",
            factor_value=0.9,
            factor_rank=0.9,
            reasoning="买入建议"
        )
        
        sell_rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.SELL,
            target_weight=0.0,
            confidence=sell_confidence,
            factor_source="factor_2",
            factor_value=0.1,
            factor_rank=0.1,
            reasoning="卖出建议"
        )
        
        resolved = asyncio.run(engine._resolve_conflicts([buy_rec, sell_rec]))
        
        # 验证：更高置信度的建议胜出
        if buy_confidence > sell_confidence:
            assert resolved[0].action == RecommendationAction.BUY
        else:
            assert resolved[0].action == RecommendationAction.SELL



# ============================================================================
# Property 31: Regime-Based Weight Adjustment
# ============================================================================

class TestProperty31RegimeBasedWeightAdjustment:
    """Property 31: 基于市场状态的权重调整
    
    **Validates: Requirements 8.6**
    
    验证当市场状态变化时，因子权重能够正确调整。
    """
    
    @pytest.fixture
    def engine_with_factors(self):
        """创建带有因子的引擎"""
        engine = CommanderFactorDecisionEngine()
        
        arena_results = [
            {
                "factor_id": "momentum",
                "name": "Momentum",
                "expression": "close / delay(close, 20) - 1",
                "passed": True,
                "overall_score": 0.8,
                "reality_score": 0.05,
                "z2h_eligible": True
            }
        ]
        
        asyncio.run(engine.integrate_arena_factors(arena_results))
        return engine
    
    def test_regime_change_updates_weights(self, engine_with_factors):
        """测试市场状态变化更新权重
        
        **Validates: Requirements 8.6**
        """
        initial_weight = engine_with_factors.factor_weights.get("momentum", 0.0)
        
        # 切换到牛市
        engine_with_factors.update_market_regime(MarketRegime.BULL)
        bull_weight = engine_with_factors.factor_weights.get("momentum", 0.0)
        
        # 切换到熊市
        engine_with_factors.update_market_regime(MarketRegime.BEAR)
        bear_weight = engine_with_factors.factor_weights.get("momentum", 0.0)
        
        # 验证：不同市场状态有不同权重
        assert bull_weight != bear_weight
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(regime=st.sampled_from(list(MarketRegime)))
    def test_all_regimes_have_valid_weights(self, engine_with_factors, regime):
        """测试所有市场状态都有有效权重
        
        **Validates: Requirements 8.6**
        """
        engine_with_factors.update_market_regime(regime)
        
        for factor_id, weight in engine_with_factors.factor_weights.items():
            # 验证：权重在有效范围内
            assert 0.1 <= weight <= 1.0
    
    def test_regime_weights_stored_per_factor(self, engine_with_factors):
        """测试每个因子存储市场状态权重
        
        **Validates: Requirements 8.6**
        """
        for factor_id, factor in engine_with_factors.validated_factors.items():
            # 验证：每个因子都有市场状态权重
            assert len(factor.regime_weights) > 0
            
            # 验证：所有市场状态都有权重
            for regime in MarketRegime:
                assert regime in factor.regime_weights


# ============================================================================
# Property 32: Recommendation Attribution Completeness
# ============================================================================

class TestProperty32RecommendationAttributionCompleteness:
    """Property 32: 建议归因完整性
    
    **Validates: Requirements 8.7, 8.8**
    
    验证建议包含完整的因子归因和置信度信息，
    并且命中率被正确跟踪。
    """
    
    @pytest.fixture
    def engine_with_factors(self):
        """创建带有因子的引擎"""
        engine = CommanderFactorDecisionEngine()
        
        arena_results = [
            {
                "factor_id": "factor_1",
                "name": "Momentum",
                "expression": "close / delay(close, 20) - 1",
                "passed": True,
                "overall_score": 0.8,
                "reality_score": 0.05,
                "z2h_eligible": True
            }
        ]
        
        asyncio.run(engine.integrate_arena_factors(arena_results))
        return engine
    
    def test_recommendation_has_factor_attribution(self, engine_with_factors):
        """测试建议包含因子归因
        
        **Validates: Requirements 8.7**
        """
        n_stocks = 20
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
        
        market_data = pd.DataFrame(
            np.random.uniform(10, 100, (30, n_stocks)),
            index=dates,
            columns=symbols
        )
        
        factor_values = {
            "factor_1": pd.Series(np.linspace(0, 1, n_stocks), index=symbols)
        }
        
        recommendations = asyncio.run(
            engine_with_factors.generate_factor_based_recommendations(
                market_data, factor_values
            )
        )
        
        # 验证：每个建议都有因子来源
        for rec in recommendations:
            assert rec.factor_source is not None
            assert rec.factor_source in engine_with_factors.validated_factors
    
    def test_recommendation_has_confidence_level(self, engine_with_factors):
        """测试建议包含置信度
        
        **Validates: Requirements 8.7**
        """
        n_stocks = 20
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
        
        market_data = pd.DataFrame(
            np.random.uniform(10, 100, (30, n_stocks)),
            index=dates,
            columns=symbols
        )
        
        factor_values = {
            "factor_1": pd.Series(np.linspace(0, 1, n_stocks), index=symbols)
        }
        
        recommendations = asyncio.run(
            engine_with_factors.generate_factor_based_recommendations(
                market_data, factor_values
            )
        )
        
        # 验证：每个建议都有置信度
        for rec in recommendations:
            assert 0.0 <= rec.confidence <= 1.0
    
    def test_hit_rate_tracking(self, engine_with_factors):
        """测试命中率跟踪
        
        **Validates: Requirements 8.8**
        """
        # 创建建议
        rec = FactorRecommendation(
            symbol="STOCK_001",
            action=RecommendationAction.BUY,
            target_weight=0.05,
            confidence=0.8,
            factor_source="factor_1",
            factor_value=0.9,
            factor_rank=0.9,
            reasoning="买入建议"
        )
        
        # 更新结果
        engine_with_factors.update_recommendation_result(rec, 0.05, True)
        engine_with_factors.update_recommendation_result(rec, -0.02, False)
        engine_with_factors.update_recommendation_result(rec, 0.03, True)
        
        # 验证：命中率被正确计算
        factor = engine_with_factors.validated_factors["factor_1"]
        assert factor.total_recommendations == 3
        assert factor.successful_recommendations == 2
        assert abs(factor.hit_rate - 2/3) < 0.01
    
    def test_factor_attribution_report(self, engine_with_factors):
        """测试因子归因报告
        
        **Validates: Requirements 8.7**
        """
        n_stocks = 20
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        symbols = [f"STOCK_{i:03d}" for i in range(n_stocks)]
        
        market_data = pd.DataFrame(
            np.random.uniform(10, 100, (30, n_stocks)),
            index=dates,
            columns=symbols
        )
        
        factor_values = {
            "factor_1": pd.Series(np.linspace(0, 1, n_stocks), index=symbols)
        }
        
        recommendations = asyncio.run(
            engine_with_factors.generate_factor_based_recommendations(
                market_data, factor_values
            )
        )
        
        # 获取归因报告
        attribution = engine_with_factors.get_factor_attribution(recommendations)
        
        # 验证：归因报告包含必要信息
        for factor_id, info in attribution.items():
            assert "factor_name" in info
            assert "arena_score" in info
            assert "z2h_certified" in info
            assert "current_weight" in info
            assert "recommendations" in info


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """边界条件测试"""
    
    @pytest.fixture
    def engine(self):
        """创建引擎"""
        return CommanderFactorDecisionEngine()
    
    def test_empty_arena_results_raises_error(self, engine):
        """测试空Arena结果抛出错误"""
        with pytest.raises(ValueError, match="Arena结果列表不能为空"):
            asyncio.run(engine.integrate_arena_factors([]))
    
    def test_no_factors_raises_error_on_recommendations(self, engine):
        """测试无因子时生成建议抛出错误"""
        market_data = pd.DataFrame({"STOCK_001": [100, 101, 102]})
        
        with pytest.raises(ValueError, match="没有可用的验证因子"):
            asyncio.run(engine.generate_factor_based_recommendations(market_data))
    
    def test_empty_market_data_raises_error(self, engine):
        """测试空市场数据抛出错误"""
        # 先添加因子
        arena_results = [{
            "factor_id": "factor_1",
            "name": "Test",
            "expression": "close",
            "passed": True,
            "overall_score": 0.8,
            "reality_score": 0.05,
            "z2h_eligible": True
        }]
        asyncio.run(engine.integrate_arena_factors(arena_results))
        
        with pytest.raises(ValueError, match="市场数据不能为空"):
            asyncio.run(engine.generate_factor_based_recommendations(pd.DataFrame()))
    
    def test_statistics_with_no_factors(self, engine):
        """测试无因子时的统计信息"""
        stats = engine.get_statistics()
        
        assert stats["total_factors"] == 0
        assert stats["z2h_certified_factors"] == 0
        assert stats["avg_arena_score"] == 0.0
    
    def test_correlation_matrix_with_single_factor(self, engine):
        """测试单因子相关性矩阵"""
        factor_values = {
            "factor_1": pd.Series([0.1, 0.2, 0.3], index=["A", "B", "C"])
        }
        
        engine.factor_correlations.update(factor_values)
        
        # 验证：单因子相关性矩阵
        assert engine.factor_correlations.correlation_matrix is not None
        assert engine.factor_correlations.correlation_matrix.shape == (1, 1)
    
    def test_redundant_pairs_with_no_correlation(self, engine):
        """测试无相关性时的冗余对"""
        # 空相关性矩阵
        redundant = engine.factor_correlations.get_redundant_pairs()
        assert redundant == []


# ============================================================================
# 性能跟踪器测试
# ============================================================================

class TestFactorPerformanceTracker:
    """因子性能跟踪器测试"""
    
    def test_update_performance(self):
        """测试更新性能"""
        tracker = FactorPerformanceTracker(
            factor_id="test",
            baseline_ic=0.05,
            expected_sharpe=1.5
        )
        
        # 更新多次
        for i in range(25):
            tracker.update_performance(
                ic=0.05 + np.random.normal(0, 0.01),
                realized_return=0.01 + np.random.normal(0, 0.005),
                predicted_direction=np.random.random() > 0.4
            )
        
        # 验证：保留最近20个数据点
        assert len(tracker.recent_ic) == 20
        assert len(tracker.recent_returns) == 20
    
    def test_get_recent_performance_empty(self):
        """测试空数据时的近期表现"""
        tracker = FactorPerformanceTracker(
            factor_id="test",
            baseline_ic=0.05,
            expected_sharpe=1.5
        )
        
        performance = tracker.get_recent_performance()
        
        assert performance["avg_ic"] == 0.05
        assert performance["hit_rate"] == 0.5
    
    @settings(max_examples=50)
    @given(
        n_updates=st.integers(min_value=1, max_value=50),
        hit_ratio=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_hit_rate_calculation(self, n_updates, hit_ratio):
        """测试命中率计算"""
        tracker = FactorPerformanceTracker(
            factor_id="test",
            baseline_ic=0.05,
            expected_sharpe=1.5
        )
        
        hits = int(n_updates * hit_ratio)
        misses = n_updates - hits
        
        for _ in range(hits):
            tracker.update_performance(0.05, 0.01, True)
        for _ in range(misses):
            tracker.update_performance(0.05, -0.01, False)
        
        performance = tracker.get_recent_performance()
        expected_hit_rate = hits / n_updates if n_updates > 0 else 0.5
        
        assert abs(performance["hit_rate"] - expected_hit_rate) < 0.01


# ============================================================================
# 相关性矩阵测试
# ============================================================================

class TestFactorCorrelationMatrix:
    """因子相关性矩阵测试"""
    
    def test_update_correlation_matrix(self):
        """测试更新相关性矩阵"""
        matrix = FactorCorrelationMatrix()
        
        factor_values = {
            "factor_1": pd.Series([0.1, 0.2, 0.3, 0.4, 0.5]),
            "factor_2": pd.Series([0.5, 0.4, 0.3, 0.2, 0.1])
        }
        
        matrix.update(factor_values)
        
        # 验证：矩阵已更新
        assert matrix.correlation_matrix is not None
        assert matrix.correlation_matrix.shape == (2, 2)
        assert matrix.last_update is not None
    
    def test_get_correlation(self):
        """测试获取相关性"""
        matrix = FactorCorrelationMatrix()
        
        factor_values = {
            "factor_1": pd.Series([0.1, 0.2, 0.3, 0.4, 0.5]),
            "factor_2": pd.Series([0.5, 0.4, 0.3, 0.2, 0.1])
        }
        
        matrix.update(factor_values)
        
        # 验证：自相关为1
        corr_11 = matrix.get_correlation("factor_1", "factor_1")
        assert abs(corr_11 - 1.0) < 0.01
        
        # 验证：负相关
        corr_12 = matrix.get_correlation("factor_1", "factor_2")
        assert corr_12 < 0
    
    def test_get_redundant_pairs(self):
        """测试获取冗余对"""
        matrix = FactorCorrelationMatrix()
        
        # 创建高度相关的因子
        factor_values = {
            "factor_1": pd.Series([0.1, 0.2, 0.3, 0.4, 0.5]),
            "factor_2": pd.Series([0.11, 0.21, 0.31, 0.41, 0.51]),  # 高度相关
            "factor_3": pd.Series([0.5, 0.4, 0.3, 0.2, 0.1])  # 负相关
        }
        
        matrix.update(factor_values)
        
        redundant = matrix.get_redundant_pairs(threshold=0.9)
        
        # 验证：factor_1和factor_2是冗余的
        assert len(redundant) >= 1
        factor_ids = [(r[0], r[1]) for r in redundant]
        assert ("factor_1", "factor_2") in factor_ids or ("factor_2", "factor_1") in factor_ids
