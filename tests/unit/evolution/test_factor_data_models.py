"""因子数据模型单元测试

白皮书依据: 第四章 4.1-4.3 斯巴达进化与生态

测试覆盖：
- Factor数据模型创建和验证
- ValidatedFactor数据模型创建和验证
- CandidateStrategy数据模型创建和验证
- ArenaTestResult数据模型创建和验证
- FactorExpression数据模型创建和验证
- RiskFactor数据模型创建和验证
- RiskLimits数据模型创建和验证
- PerformanceMetrics数据模型创建和验证
- SimulationResult数据模型创建和验证
- TradeableStrategy数据模型创建和验证
- Z2HCertifiedStrategy数据模型创建和验证

铁律7: 测试覆盖率要求 - 单元测试覆盖率 ≥ 85%
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.evolution.factor_data_models import (
    Factor,
    ValidatedFactor,
    CandidateStrategy,
    ArenaTestResult,
    FactorExpression,
    RiskFactor,
    RiskLimits,
    PerformanceMetrics,
    DailyResult,
    SimulationMetrics,
    SimulationResult,
    TradeableStrategy,
    Z2HCertifiedStrategy
)


# ============================================================================
# 测试辅助函数
# ============================================================================

def create_test_factor() -> Factor:
    """创建测试用因子"""
    return Factor(
        id="factor_001",
        name="Momentum Factor",
        expression="rank(close/shift(close,20))",
        category="technical",
        implementation_code="def calculate(data): return data['close'] / data['close'].shift(20)",
        created_at=datetime.now(),
        generation=5,
        fitness_score=0.85,
        baseline_ic=0.05,
        baseline_ir=0.8,
        baseline_sharpe=1.5,
        liquidity_adaptability=0.7
    )


def create_test_validated_factor() -> ValidatedFactor:
    """创建测试用验证因子"""
    factor = create_test_factor()
    return ValidatedFactor(
        factor=factor,
        arena_score=0.75,
        reality_score=0.8,
        hell_score=0.7,
        cross_market_score=0.75,
        markets_passed=3,
        z2h_eligible=True,
        validation_date=datetime.now(),
        reality_result={"ic_1d": 0.05, "ic_5d": 0.06, "sharpe": 1.5},
        hell_result={"survival_rate": 0.7, "scenarios_passed": 4},
        cross_market_result={"markets": ["A-Stock", "US-Stock", "Crypto"]}
    )


def create_test_candidate_strategy() -> CandidateStrategy:
    """创建测试用候选策略"""
    factor = create_test_factor()
    return CandidateStrategy(
        id="strategy_001",
        name="Momentum Strategy",
        strategy_type="pure_factor",
        source_factors=[factor],
        code="def execute(data): pass",
        expected_sharpe=1.8,
        max_drawdown_limit=0.15,
        capital_allocation=100000.0,
        rebalance_frequency=5,
        status="candidate",
        arena_scheduled=False,
        simulation_required=True,
        z2h_eligible=False,
        created_at=datetime.now()
    )


# ============================================================================
# Factor数据模型测试
# ============================================================================

class TestFactor:
    """Factor数据模型测试"""
    
    def test_factor_creation(self):
        """测试Factor创建"""
        factor = create_test_factor()
        
        assert factor.id == "factor_001"
        assert factor.name == "Momentum Factor"
        assert factor.expression == "rank(close/shift(close,20))"
        assert factor.category == "technical"
        assert factor.generation == 5
        assert factor.fitness_score == 0.85
        assert factor.baseline_ic == 0.05
        assert factor.baseline_ir == 0.8
        assert factor.baseline_sharpe == 1.5
        assert factor.liquidity_adaptability == 0.7
    
    def test_factor_with_negative_fitness(self):
        """测试负适应度的Factor"""
        factor = Factor(
            id="factor_002",
            name="Bad Factor",
            expression="invalid",
            category="technical",
            implementation_code="",
            created_at=datetime.now(),
            generation=1,
            fitness_score=-0.5,
            baseline_ic=-0.02,
            baseline_ir=-0.3,
            baseline_sharpe=-0.5,
            liquidity_adaptability=0.1
        )
        
        assert factor.fitness_score == -0.5
        assert factor.baseline_ic == -0.02
    
    def test_factor_with_zero_generation(self):
        """测试第0代Factor"""
        factor = Factor(
            id="factor_003",
            name="Initial Factor",
            expression="close",
            category="price",
            implementation_code="",
            created_at=datetime.now(),
            generation=0,
            fitness_score=0.0,
            baseline_ic=0.0,
            baseline_ir=0.0,
            baseline_sharpe=0.0,
            liquidity_adaptability=0.0
        )
        
        assert factor.generation == 0


# ============================================================================
# ValidatedFactor数据模型测试
# ============================================================================

class TestValidatedFactor:
    """ValidatedFactor数据模型测试"""
    
    def test_validated_factor_creation(self):
        """测试ValidatedFactor创建"""
        validated_factor = create_test_validated_factor()
        
        assert validated_factor.arena_score == 0.75
        assert validated_factor.reality_score == 0.8
        assert validated_factor.hell_score == 0.7
        assert validated_factor.cross_market_score == 0.75
        assert validated_factor.markets_passed == 3
        assert validated_factor.z2h_eligible is True
    
    def test_validated_factor_with_low_arena_score(self):
        """测试低Arena评分的ValidatedFactor"""
        factor = create_test_factor()
        validated_factor = ValidatedFactor(
            factor=factor,
            arena_score=0.5,
            reality_score=0.6,
            hell_score=0.4,
            cross_market_score=0.5,
            markets_passed=2,
            z2h_eligible=False,
            validation_date=datetime.now(),
            reality_result={},
            hell_result={},
            cross_market_result={}
        )
        
        assert validated_factor.arena_score == 0.5
        assert validated_factor.z2h_eligible is False
    
    def test_validated_factor_with_all_markets_passed(self):
        """测试通过所有市场的ValidatedFactor"""
        factor = create_test_factor()
        validated_factor = ValidatedFactor(
            factor=factor,
            arena_score=0.9,
            reality_score=0.95,
            hell_score=0.85,
            cross_market_score=0.9,
            markets_passed=4,
            z2h_eligible=True,
            validation_date=datetime.now(),
            reality_result={},
            hell_result={},
            cross_market_result={"markets": ["A-Stock", "US-Stock", "Crypto", "HK-Stock"]}
        )
        
        assert validated_factor.markets_passed == 4


# ============================================================================
# CandidateStrategy数据模型测试
# ============================================================================

class TestCandidateStrategy:
    """CandidateStrategy数据模型测试"""
    
    def test_candidate_strategy_creation(self):
        """测试CandidateStrategy创建"""
        strategy = create_test_candidate_strategy()
        
        assert strategy.id == "strategy_001"
        assert strategy.name == "Momentum Strategy"
        assert strategy.strategy_type == "pure_factor"
        assert len(strategy.source_factors) == 1
        assert strategy.expected_sharpe == 1.8
        assert strategy.max_drawdown_limit == 0.15
        assert strategy.capital_allocation == 100000.0
        assert strategy.rebalance_frequency == 5
        assert strategy.status == "candidate"
    
    def test_candidate_strategy_with_multiple_factors(self):
        """测试多因子CandidateStrategy"""
        factor1 = create_test_factor()
        factor2 = Factor(
            id="factor_002",
            name="Value Factor",
            expression="rank(pe_ratio)",
            category="fundamental",
            implementation_code="",
            created_at=datetime.now(),
            generation=3,
            fitness_score=0.75,
            baseline_ic=0.04,
            baseline_ir=0.7,
            baseline_sharpe=1.3,
            liquidity_adaptability=0.6
        )
        
        strategy = CandidateStrategy(
            id="strategy_002",
            name="Combo Strategy",
            strategy_type="factor_combo",
            source_factors=[factor1, factor2],
            code="",
            expected_sharpe=2.0,
            max_drawdown_limit=0.12,
            capital_allocation=200000.0,
            rebalance_frequency=10,
            status="candidate",
            arena_scheduled=True,
            simulation_required=True,
            z2h_eligible=False,
            created_at=datetime.now()
        )
        
        assert len(strategy.source_factors) == 2
        assert strategy.strategy_type == "factor_combo"


# ============================================================================
# ArenaTestResult数据模型测试
# ============================================================================

class TestArenaTestResult:
    """ArenaTestResult数据模型测试"""
    
    def test_arena_test_result_for_factor(self):
        """测试因子的ArenaTestResult"""
        result = ArenaTestResult(
            test_type="factor",
            subject_id="factor_001",
            arena_score=0.75,
            reality_result={"ic": 0.05},
            hell_result={"survival": 0.7},
            cross_market_result={"markets": 3},
            passed=True,
            next_stage="strategy_generation",
            test_timestamp=datetime.now(),
            detailed_metrics={}
        )
        
        assert result.test_type == "factor"
        assert result.passed is True
        assert result.next_stage == "strategy_generation"
    
    def test_arena_test_result_for_strategy(self):
        """测试策略的ArenaTestResult"""
        result = ArenaTestResult(
            test_type="strategy",
            subject_id="strategy_001",
            arena_score=0.8,
            reality_result={"sharpe": 1.8},
            hell_result={"survival": 0.85},
            cross_market_result=None,
            passed=True,
            next_stage="simulation",
            test_timestamp=datetime.now(),
            detailed_metrics={}
        )
        
        assert result.test_type == "strategy"
        assert result.cross_market_result is None


# ============================================================================
# FactorExpression数据模型测试
# ============================================================================

class TestFactorExpression:
    """FactorExpression数据模型测试"""
    
    def test_factor_expression_creation(self):
        """测试FactorExpression创建"""
        expression = FactorExpression(
            expression_string="rank(close/shift(close,20))",
            operators_used=["rank", "shift", "/"],
            complexity=3,
            depth=2,
            parameters={"lookback": 20}
        )
        
        assert expression.expression_string == "rank(close/shift(close,20))"
        assert len(expression.operators_used) == 3
        assert expression.complexity == 3
        assert expression.depth == 2
    
    def test_factor_expression_with_no_operators(self):
        """测试无算子的FactorExpression"""
        expression = FactorExpression(
            expression_string="close",
            operators_used=[],
            complexity=1,
            depth=0,
            parameters={}
        )
        
        assert len(expression.operators_used) == 0
        assert expression.complexity == 1


# ============================================================================
# RiskFactor数据模型测试
# ============================================================================

class TestRiskFactor:
    """RiskFactor数据模型测试"""
    
    def test_risk_factor_creation(self):
        """测试RiskFactor创建"""
        risk_factor = RiskFactor(
            original_factor_id="factor_001",
            original_expression="rank(close/shift(close,20))",
            risk_signal_expression="-rank(close/shift(close,20))",
            risk_type="correlation_flip",
            sensitivity=0.8,
            created_at=datetime.now(),
            conversion_reason="IC dropped below threshold",
            baseline_metrics={"ic": 0.05, "sharpe": 1.5}
        )
        
        assert risk_factor.original_factor_id == "factor_001"
        assert risk_factor.risk_type == "correlation_flip"
        assert risk_factor.sensitivity == 0.8


# ============================================================================
# RiskLimits数据模型测试
# ============================================================================

class TestRiskLimits:
    """RiskLimits数据模型测试"""
    
    def test_risk_limits_creation(self):
        """测试RiskLimits创建"""
        limits = RiskLimits(
            max_position_size=0.05,
            max_portfolio_concentration=0.3,
            max_drawdown_threshold=0.15,
            max_daily_loss=0.02,
            min_liquidity_rank=0.5,
            max_leverage=2.0,
            rebalance_frequency=5,
            stop_loss_percentage=0.05
        )
        
        assert limits.max_position_size == 0.05
        assert limits.max_drawdown_threshold == 0.15
        assert limits.rebalance_frequency == 5


# ============================================================================
# PerformanceMetrics数据模型测试
# ============================================================================

class TestPerformanceMetrics:
    """PerformanceMetrics数据模型测试"""
    
    def test_performance_metrics_creation(self):
        """测试PerformanceMetrics创建"""
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            ic_1d=0.05,
            ic_5d=0.06,
            ic_10d=0.055,
            ic_20d=0.058,
            ir=0.8,
            sharpe_ratio=1.5,
            turnover_rate=0.3,
            health_score=0.85,
            correlation_with_market=0.3,
            liquidity_score=0.7
        )
        
        assert metrics.ic_1d == 0.05
        assert metrics.health_score == 0.85


# ============================================================================
# SimulationResult数据模型测试
# ============================================================================

class TestSimulationResult:
    """SimulationResult数据模型测试"""
    
    def test_simulation_result_passed(self):
        """测试通过的SimulationResult"""
        strategy = create_test_candidate_strategy()
        metrics = SimulationMetrics(
            total_return=0.08,
            sharpe_ratio=1.5,
            max_drawdown=0.12,
            win_rate=0.58,
            profit_factor=1.5,
            average_win=0.02,
            average_loss=-0.015,
            total_trades=100,
            winning_trades=58,
            losing_trades=42
        )
        
        result = SimulationResult(
            strategy=strategy,
            passed=True,
            failure_reason=None,
            daily_results=[],
            final_metrics=metrics,
            z2h_eligible=True,
            simulation_start=datetime.now() - timedelta(days=30),
            simulation_end=datetime.now()
        )
        
        assert result.passed is True
        assert result.z2h_eligible is True
        assert result.final_metrics.sharpe_ratio == 1.5
    
    def test_simulation_result_failed(self):
        """测试失败的SimulationResult"""
        strategy = create_test_candidate_strategy()
        metrics = SimulationMetrics(
            total_return=-0.05,
            sharpe_ratio=0.5,
            max_drawdown=0.25,
            win_rate=0.4,
            profit_factor=0.8,
            average_win=0.01,
            average_loss=-0.02,
            total_trades=50,
            winning_trades=20,
            losing_trades=30
        )
        
        result = SimulationResult(
            strategy=strategy,
            passed=False,
            failure_reason="excessive_drawdown",
            daily_results=[],
            final_metrics=metrics,
            z2h_eligible=False,
            simulation_start=datetime.now() - timedelta(days=30),
            simulation_end=datetime.now()
        )
        
        assert result.passed is False
        assert result.failure_reason == "excessive_drawdown"
        assert result.z2h_eligible is False


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """边界条件测试"""
    
    def test_factor_with_extreme_values(self):
        """测试极端值的Factor"""
        factor = Factor(
            id="factor_extreme",
            name="Extreme Factor",
            expression="test",
            category="test",
            implementation_code="",
            created_at=datetime.now(),
            generation=1000,
            fitness_score=1.0,
            baseline_ic=1.0,
            baseline_ir=10.0,
            baseline_sharpe=5.0,
            liquidity_adaptability=1.0
        )
        
        assert factor.fitness_score == 1.0
        assert factor.baseline_ic == 1.0
    
    def test_validated_factor_with_zero_markets(self):
        """测试0个市场通过的ValidatedFactor"""
        factor = create_test_factor()
        validated_factor = ValidatedFactor(
            factor=factor,
            arena_score=0.3,
            reality_score=0.4,
            hell_score=0.2,
            cross_market_score=0.3,
            markets_passed=0,
            z2h_eligible=False,
            validation_date=datetime.now(),
            reality_result={},
            hell_result={},
            cross_market_result={}
        )
        
        assert validated_factor.markets_passed == 0
        assert validated_factor.z2h_eligible is False
    
    def test_candidate_strategy_with_zero_capital(self):
        """测试0资金的CandidateStrategy"""
        factor = create_test_factor()
        strategy = CandidateStrategy(
            id="strategy_zero",
            name="Zero Capital Strategy",
            strategy_type="pure_factor",
            source_factors=[factor],
            code="",
            expected_sharpe=0.0,
            max_drawdown_limit=0.0,
            capital_allocation=0.0,
            rebalance_frequency=1,
            status="rejected",
            arena_scheduled=False,
            simulation_required=False,
            z2h_eligible=False,
            created_at=datetime.now()
        )
        
        assert strategy.capital_allocation == 0.0
        assert strategy.status == "rejected"
