"""RiskControlMetaLearner属性测试

白皮书依据: 第二章 2.2.4 风险控制元学习架构

Property 1: Meta learner records all learning samples
验证需求: Requirements 1.2
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from datetime import datetime

from src.brain.meta_learning import (
    RiskControlMetaLearner,
    MarketContext,
    PerformanceMetrics
)


# 策略：生成有效的MarketContext
@st.composite
def market_context_strategy(draw):
    """生成有效的MarketContext"""
    return MarketContext(
        volatility=draw(st.floats(min_value=0.0, max_value=1.0)),
        liquidity=draw(st.floats(min_value=0.0, max_value=1.0)),
        trend_strength=draw(st.floats(min_value=-1.0, max_value=1.0)),
        regime=draw(st.sampled_from(['bull', 'bear', 'sideways'])),
        aum=draw(st.floats(min_value=0.0, max_value=1e10)),
        portfolio_concentration=draw(st.floats(min_value=0.0, max_value=1.0)),
        recent_drawdown=draw(st.floats(min_value=0.0, max_value=1.0))
    )


# 策略：生成有效的PerformanceMetrics
@st.composite
def performance_metrics_strategy(draw):
    """生成有效的PerformanceMetrics"""
    return PerformanceMetrics(
        sharpe_ratio=draw(st.floats(min_value=-3.0, max_value=5.0)),
        max_drawdown=draw(st.floats(min_value=0.0, max_value=1.0)),
        win_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        profit_factor=draw(st.floats(min_value=0.0, max_value=10.0)),
        calmar_ratio=draw(st.floats(min_value=-5.0, max_value=10.0)),
        sortino_ratio=draw(st.floats(min_value=-3.0, max_value=5.0)),
        decision_latency_ms=draw(st.floats(min_value=0.0, max_value=100.0))
    )


class TestProperty1MetaLearnerRecordsAllSamples:
    """Property 1: Meta learner records all learning samples
    
    验证需求: Requirements 1.2
    
    属性描述：
    对于任意有效的市场上下文和性能指标，元学习器必须记录所有学习样本。
    
    形式化：
    ∀ (market_context, perf_a, perf_b) ∈ ValidInputs:
        observe_and_learn(market_context, perf_a, perf_b)
        ⟹ len(experience_db) increases by 1
        ∧ learning_stats['total_samples'] increases by 1
    """
    
    @given(
        market_context=market_context_strategy(),
        perf_a=performance_metrics_strategy(),
        perf_b=performance_metrics_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_1_records_all_samples(
        self,
        market_context: MarketContext,
        perf_a: PerformanceMetrics,
        perf_b: PerformanceMetrics
    ):
        """Property 1: 元学习器记录所有学习样本
        
        **Validates: Requirements 1.2**
        
        验证：
        1. 每次调用observe_and_learn，experience_db长度增加1
        2. learning_stats['total_samples']增加1
        3. 记录的数据点包含正确的市场上下文和性能指标
        """
        # 创建元学习器
        learner = RiskControlMetaLearner(min_samples_for_training=1000)
        
        # 记录初始状态
        initial_db_size = len(learner.experience_db)
        initial_total_samples = learner.learning_stats['total_samples']
        
        # 执行观察学习
        asyncio.run(learner.observe_and_learn(market_context, perf_a, perf_b))
        
        # 验证：experience_db长度增加1
        assert len(learner.experience_db) == initial_db_size + 1, \
            f"experience_db应该增加1，实际: {len(learner.experience_db)} vs {initial_db_size}"
        
        # 验证：total_samples增加1
        assert learner.learning_stats['total_samples'] == initial_total_samples + 1, \
            f"total_samples应该增加1，实际: {learner.learning_stats['total_samples']} vs {initial_total_samples}"
        
        # 验证：记录的数据点包含正确的信息
        last_data_point = learner.experience_db[-1]
        assert last_data_point.market_context == market_context
        assert last_data_point.strategy_a_performance == perf_a
        assert last_data_point.strategy_b_performance == perf_b
        assert last_data_point.winner in ['A', 'B']
    
    @given(
        samples=st.lists(
            st.tuples(
                market_context_strategy(),
                performance_metrics_strategy(),
                performance_metrics_strategy()
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_property_1_records_multiple_samples(
        self,
        samples
    ):
        """Property 1: 元学习器记录多个学习样本
        
        **Validates: Requirements 1.2**
        
        验证：
        1. 多次调用observe_and_learn，experience_db长度正确增加
        2. learning_stats['total_samples']正确累加
        """
        # 创建元学习器
        learner = RiskControlMetaLearner(min_samples_for_training=1000)
        
        # 记录初始状态
        initial_db_size = len(learner.experience_db)
        initial_total_samples = learner.learning_stats['total_samples']
        
        # 执行多次观察学习
        for market_context, perf_a, perf_b in samples:
            asyncio.run(learner.observe_and_learn(market_context, perf_a, perf_b))
        
        # 验证：experience_db长度增加正确
        expected_db_size = initial_db_size + len(samples)
        assert len(learner.experience_db) == expected_db_size, \
            f"experience_db应该增加{len(samples)}，实际: {len(learner.experience_db)} vs {expected_db_size}"
        
        # 验证：total_samples增加正确
        expected_total_samples = initial_total_samples + len(samples)
        assert learner.learning_stats['total_samples'] == expected_total_samples, \
            f"total_samples应该增加{len(samples)}，实际: {learner.learning_stats['total_samples']} vs {expected_total_samples}"
    
    @given(
        market_context=market_context_strategy(),
        perf_a=performance_metrics_strategy(),
        perf_b=performance_metrics_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_property_1_winner_determination_is_consistent(
        self,
        market_context: MarketContext,
        perf_a: PerformanceMetrics,
        perf_b: PerformanceMetrics
    ):
        """Property 1: 获胜者判断是一致的
        
        **Validates: Requirements 1.2**
        
        验证：
        1. 对于相同的性能指标，获胜者判断结果一致
        2. 获胜者统计正确更新
        """
        # 创建元学习器
        learner = RiskControlMetaLearner(min_samples_for_training=1000)
        
        # 第一次观察学习
        asyncio.run(learner.observe_and_learn(market_context, perf_a, perf_b))
        first_winner = learner.experience_db[-1].winner
        
        # 第二次观察学习（相同的性能指标）
        asyncio.run(learner.observe_and_learn(market_context, perf_a, perf_b))
        second_winner = learner.experience_db[-1].winner
        
        # 验证：获胜者判断一致
        assert first_winner == second_winner, \
            f"相同性能指标应该产生相同的获胜者，实际: {first_winner} vs {second_winner}"
        
        # 验证：获胜者统计正确
        if first_winner == 'A':
            assert learner.learning_stats['strategy_a_wins'] == 2
            assert learner.learning_stats['strategy_b_wins'] == 0
        else:
            assert learner.learning_stats['strategy_a_wins'] == 0
            assert learner.learning_stats['strategy_b_wins'] == 2


class TestProperty1EdgeCases:
    """Property 1的边界条件测试"""
    
    def test_property_1_with_extreme_performance(self):
        """测试极端性能指标"""
        learner = RiskControlMetaLearner(min_samples_for_training=1000)
        
        # 极端好的性能
        extreme_good = PerformanceMetrics(
            sharpe_ratio=5.0,
            max_drawdown=0.0,
            win_rate=1.0,
            profit_factor=10.0,
            calmar_ratio=10.0,
            sortino_ratio=5.0,
            decision_latency_ms=1.0
        )
        
        # 极端差的性能
        extreme_bad = PerformanceMetrics(
            sharpe_ratio=-3.0,
            max_drawdown=1.0,
            win_rate=0.0,
            profit_factor=0.0,
            calmar_ratio=-5.0,
            sortino_ratio=-3.0,
            decision_latency_ms=100.0
        )
        
        market_context = MarketContext(
            volatility=0.5,
            liquidity=0.5,
            trend_strength=0.0,
            regime='sideways',
            aum=1000000.0,
            portfolio_concentration=0.5,
            recent_drawdown=0.5
        )
        
        # 应该能正常处理极端情况
        asyncio.run(learner.observe_and_learn(market_context, extreme_good, extreme_bad))
        
        assert len(learner.experience_db) == 1
        assert learner.experience_db[-1].winner == 'A'  # 极端好的应该获胜
    
    def test_property_1_with_zero_aum(self):
        """测试零资金规模"""
        learner = RiskControlMetaLearner(min_samples_for_training=1000)
        
        market_context = MarketContext(
            volatility=0.5,
            liquidity=0.5,
            trend_strength=0.0,
            regime='sideways',
            aum=0.0,  # 零资金
            portfolio_concentration=0.5,
            recent_drawdown=0.5
        )
        
        perf_a = PerformanceMetrics(
            sharpe_ratio=2.0,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=2.5,
            calmar_ratio=3.0,
            sortino_ratio=2.5,
            decision_latency_ms=15.0
        )
        
        perf_b = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=0.2,
            win_rate=0.55,
            profit_factor=2.0,
            calmar_ratio=2.5,
            sortino_ratio=2.0,
            decision_latency_ms=18.0
        )
        
        # 应该能正常处理零资金
        asyncio.run(learner.observe_and_learn(market_context, perf_a, perf_b))
        
        assert len(learner.experience_db) == 1
    
    def test_property_1_with_all_regimes(self):
        """测试所有市场状态"""
        learner = RiskControlMetaLearner(min_samples_for_training=1000)
        
        perf_a = PerformanceMetrics(
            sharpe_ratio=2.0,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=2.5,
            calmar_ratio=3.0,
            sortino_ratio=2.5,
            decision_latency_ms=15.0
        )
        
        perf_b = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=0.2,
            win_rate=0.55,
            profit_factor=2.0,
            calmar_ratio=2.5,
            sortino_ratio=2.0,
            decision_latency_ms=18.0
        )
        
        # 测试所有市场状态
        for regime in ['bull', 'bear', 'sideways']:
            market_context = MarketContext(
                volatility=0.5,
                liquidity=0.5,
                trend_strength=0.0,
                regime=regime,
                aum=1000000.0,
                portfolio_concentration=0.5,
                recent_drawdown=0.5
            )
            
            asyncio.run(learner.observe_and_learn(market_context, perf_a, perf_b))
        
        # 应该记录所有3个样本
        assert len(learner.experience_db) == 3
        assert learner.learning_stats['total_samples'] == 3
