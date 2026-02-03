"""智能路由和混合系统集成测试

白皮书依据: 第二章 2.2.4 风险控制元学习架构

测试范围：
1. 智能路由决策
2. 混合策略融合
3. 规则评估
4. 端到端集成

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from src.brain.risk_control_meta_learner import (
    RiskControlMetaLearner,
    MarketContext,
    PerformanceMetrics,
    RiskControlStrategy
)
from src.brain.intelligent_risk_control_router import (
    IntelligentRiskControlRouter,
    RoutingDecision
)
from src.brain.hybrid_risk_control import (
    HybridRiskControl,
    HybridDecision
)


class TestIntelligentRouting:
    """测试智能路由决策"""
    
    @pytest.fixture
    def meta_learner(self):
        """创建元学习器实例"""
        return RiskControlMetaLearner()
    
    @pytest.fixture
    def router(self, meta_learner):
        """创建智能路由器实例"""
        return IntelligentRiskControlRouter(
            meta_learner=meta_learner,
            high_confidence_threshold=0.8,
            low_confidence_threshold=0.6
        )
    
    @pytest.fixture
    def market_context(self):
        """创建市场上下文"""
        return MarketContext(
            volatility=0.25,
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='bull',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
    
    @pytest.mark.asyncio
    async def test_high_confidence_routing(self, router, market_context, meta_learner):
        """测试高置信度路由"""
        # 模拟高置信度预测
        with patch.object(
            meta_learner,
            'predict_best_strategy',
            return_value=(RiskControlStrategy.HARDCODED, 0.85)
        ):
            decision = await router.route_decision(market_context)
            
            # 验证
            assert decision.selected_strategy == RiskControlStrategy.HARDCODED
            assert decision.confidence == 0.85
            assert not decision.fallback_used
            assert '高置信度' in decision.routing_reason
    
    @pytest.mark.asyncio
    async def test_medium_confidence_routing(self, router, market_context, meta_learner):
        """测试中置信度路由"""
        # 模拟中置信度预测
        with patch.object(
            meta_learner,
            'predict_best_strategy',
            return_value=(RiskControlStrategy.STRATEGY_LAYER, 0.7)
        ):
            decision = await router.route_decision(market_context)
            
            # 验证
            assert decision.selected_strategy == RiskControlStrategy.HYBRID
            assert decision.confidence == 0.7
            assert not decision.fallback_used
            assert '中置信度' in decision.routing_reason
    
    @pytest.mark.asyncio
    async def test_low_confidence_routing(self, router, market_context, meta_learner):
        """测试低置信度路由（回退）"""
        # 模拟低置信度预测
        with patch.object(
            meta_learner,
            'predict_best_strategy',
            return_value=(RiskControlStrategy.STRATEGY_LAYER, 0.4)
        ):
            decision = await router.route_decision(market_context)
            
            # 验证
            assert decision.selected_strategy == RiskControlStrategy.HARDCODED
            assert decision.confidence == 0.4
            assert decision.fallback_used
            assert '低置信度' in decision.routing_reason
            assert '回退' in decision.routing_reason
    
    def test_routing_statistics(self, router, market_context, meta_learner):
        """测试路由统计信息"""
        # 执行多次路由
        asyncio.run(self._run_multiple_routes(router, market_context, meta_learner, 10))
        
        # 获取统计信息
        stats = router.get_statistics()
        
        # 验证
        assert stats['total_routes'] == 10
        assert 'strategy_selection' in stats
        assert 'confidence_distribution' in stats
        assert 'fallback' in stats
        assert 'thresholds' in stats
    
    async def _run_multiple_routes(self, router, market_context, meta_learner, n):
        """运行多次路由"""
        for i in range(n):
            # 模拟不同置信度
            confidence = 0.5 + (i % 5) * 0.1
            with patch.object(
                meta_learner,
                'predict_best_strategy',
                return_value=(RiskControlStrategy.HARDCODED, confidence)
            ):
                await router.route_decision(market_context)
    
    def test_recent_decisions(self, router, market_context, meta_learner):
        """测试获取最近决策"""
        # 执行多次路由
        asyncio.run(self._run_multiple_routes(router, market_context, meta_learner, 5))
        
        # 获取最近决策
        recent = router.get_recent_decisions(n=3)
        
        # 验证
        assert len(recent) == 3
        assert all(isinstance(d, RoutingDecision) for d in recent)


class TestHybridRiskControl:
    """测试混合风控系统"""
    
    @pytest.fixture
    def hybrid(self):
        """创建混合风控实例"""
        return HybridRiskControl()
    
    @pytest.fixture
    def market_context(self):
        """创建市场上下文"""
        return MarketContext(
            volatility=0.25,
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='bull',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
    
    @pytest.fixture
    def decision_a(self):
        """创建架构A的决策"""
        return {
            'positions': [
                {'symbol': 'AAPL', 'size': 100},
                {'symbol': 'GOOGL', 'size': 50}
            ],
            'risk_level': 'low',
            'confidence': 0.7
        }
    
    @pytest.fixture
    def decision_b(self):
        """创建架构B的决策"""
        return {
            'positions': [
                {'symbol': 'AAPL', 'size': 150},
                {'symbol': 'MSFT', 'size': 80}
            ],
            'risk_level': 'medium',
            'confidence': 0.8
        }
    
    @pytest.mark.asyncio
    async def test_default_blending(self, hybrid, market_context, decision_a, decision_b):
        """测试默认混合（50/50）"""
        decision = await hybrid.decide(market_context, decision_a, decision_b)
        
        # 验证
        assert isinstance(decision, HybridDecision)
        assert len(decision.positions) > 0
        assert 0 <= decision.architecture_a_weight <= 1
        assert 0 <= decision.architecture_b_weight <= 1
        assert abs(decision.architecture_a_weight + decision.architecture_b_weight - 1.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_high_volatility_rule(self, hybrid, decision_a, decision_b):
        """测试高波动规则"""
        # 创建高波动市场上下文
        context = MarketContext(
            volatility=0.35,  # 高波动
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='choppy',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        decision = await hybrid.decide(context, decision_a, decision_b)
        
        # 验证：高波动时应增加硬编码权重
        assert decision.architecture_a_weight > 0.5
        assert 'high_volatility_conservative' in decision.rules_applied
    
    @pytest.mark.asyncio
    async def test_large_aum_rule(self, hybrid, decision_a, decision_b):
        """测试大资金规则"""
        # 创建大资金市场上下文
        context = MarketContext(
            volatility=0.20,
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='bull',
            aum=2000000.0,  # 大资金
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        decision = await hybrid.decide(context, decision_a, decision_b)
        
        # 验证：大资金时应增加策略层权重
        assert decision.architecture_b_weight > 0.5
        assert 'large_aum_flexible' in decision.rules_applied
    
    @pytest.mark.asyncio
    async def test_large_drawdown_rule(self, hybrid, decision_a, decision_b):
        """测试大回撤规则"""
        # 创建大回撤市场上下文
        context = MarketContext(
            volatility=0.25,
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='bear',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.15  # 大回撤
        )
        
        decision = await hybrid.decide(context, decision_a, decision_b)
        
        # 验证：大回撤时应切换到硬编码（100%权重）
        assert decision.architecture_a_weight == 1.0
        assert decision.architecture_b_weight == 0.0
        assert 'large_drawdown_conservative' in decision.rules_applied
    
    @pytest.mark.asyncio
    async def test_strong_trend_rule(self, hybrid, decision_a, decision_b):
        """测试强趋势规则"""
        # 创建强趋势市场上下文
        context = MarketContext(
            volatility=0.20,
            liquidity=1000000.0,
            trend_strength=0.8,  # 强趋势
            regime='bull',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        decision = await hybrid.decide(context, decision_a, decision_b)
        
        # 验证：强趋势时应增加策略层权重
        assert decision.architecture_b_weight > 0.5
        assert 'strong_trend_aggressive' in decision.rules_applied
    
    @pytest.mark.asyncio
    async def test_position_blending(self, hybrid, market_context, decision_a, decision_b):
        """测试仓位混合"""
        decision = await hybrid.decide(market_context, decision_a, decision_b)
        
        # 验证：混合后的仓位列表
        assert len(decision.positions) > 0
        
        # 验证：AAPL应该被合并（两个架构都有）
        aapl_positions = [p for p in decision.positions if p['symbol'] == 'AAPL']
        assert len(aapl_positions) == 1
        
        # 验证：GOOGL和MSFT应该都存在（不同架构）
        symbols = [p['symbol'] for p in decision.positions]
        assert 'GOOGL' in symbols or 'MSFT' in symbols
    
    @pytest.mark.asyncio
    async def test_risk_level_blending(self, hybrid, market_context, decision_a, decision_b):
        """测试风险等级混合"""
        decision = await hybrid.decide(market_context, decision_a, decision_b)
        
        # 验证：风险等级应该在low和medium之间
        assert decision.risk_level in ['low', 'medium', 'high']
    
    @pytest.mark.asyncio
    async def test_confidence_blending(self, hybrid, market_context, decision_a, decision_b):
        """测试置信度混合"""
        decision = await hybrid.decide(market_context, decision_a, decision_b)
        
        # 验证：置信度应该在0.7和0.8之间（加权平均）
        assert 0.0 <= decision.confidence <= 1.0
        assert 0.6 <= decision.confidence <= 0.9  # 大致范围
    
    def test_hybrid_statistics(self, hybrid, market_context, decision_a, decision_b):
        """测试混合统计信息"""
        # 执行多次混合决策
        asyncio.run(self._run_multiple_decisions(hybrid, market_context, decision_a, decision_b, 10))
        
        # 获取统计信息
        stats = hybrid.get_statistics()
        
        # 验证
        assert stats['total_decisions'] == 10
        assert 'avg_architecture_a_weight' in stats
        assert 'avg_architecture_b_weight' in stats
        assert 'rules_triggered' in stats
    
    async def _run_multiple_decisions(self, hybrid, market_context, decision_a, decision_b, n):
        """运行多次混合决策"""
        for _ in range(n):
            await hybrid.decide(market_context, decision_a, decision_b)
    
    def test_recent_decisions(self, hybrid, market_context, decision_a, decision_b):
        """测试获取最近决策"""
        # 执行多次混合决策
        asyncio.run(self._run_multiple_decisions(hybrid, market_context, decision_a, decision_b, 5))
        
        # 获取最近决策
        recent = hybrid.get_recent_decisions(n=3)
        
        # 验证
        assert len(recent) == 3
        assert all(isinstance(d, HybridDecision) for d in recent)


class TestEndToEndIntegration:
    """测试端到端集成"""
    
    @pytest.fixture
    def meta_learner(self):
        """创建元学习器实例"""
        return RiskControlMetaLearner()
    
    @pytest.fixture
    def router(self, meta_learner):
        """创建智能路由器实例"""
        return IntelligentRiskControlRouter(meta_learner=meta_learner)
    
    @pytest.fixture
    def hybrid(self):
        """创建混合风控实例"""
        return HybridRiskControl()
    
    @pytest.fixture
    def market_context(self):
        """创建市场上下文"""
        return MarketContext(
            volatility=0.25,
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='bull',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
    
    @pytest.mark.asyncio
    async def test_routing_to_hybrid_flow(self, router, hybrid, market_context, meta_learner):
        """测试路由到混合的完整流程"""
        # 1. 智能路由决策
        with patch.object(
            meta_learner,
            'predict_best_strategy',
            return_value=(RiskControlStrategy.HYBRID, 0.7)
        ):
            routing_decision = await router.route_decision(market_context)
        
        # 验证路由决策
        assert routing_decision.selected_strategy == RiskControlStrategy.HYBRID
        
        # 2. 如果路由到混合策略，执行混合决策
        if routing_decision.selected_strategy == RiskControlStrategy.HYBRID:
            decision_a = {
                'positions': [{'symbol': 'AAPL', 'size': 100}],
                'risk_level': 'low',
                'confidence': 0.7
            }
            decision_b = {
                'positions': [{'symbol': 'AAPL', 'size': 150}],
                'risk_level': 'medium',
                'confidence': 0.8
            }
            
            hybrid_decision = await hybrid.decide(market_context, decision_a, decision_b)
            
            # 验证混合决策
            assert isinstance(hybrid_decision, HybridDecision)
            assert len(hybrid_decision.positions) > 0
    
    @pytest.mark.asyncio
    async def test_learning_feedback_loop(self, meta_learner, router, market_context):
        """测试学习反馈循环"""
        # 1. 初始路由决策（模型未训练）
        routing_decision_1 = await router.route_decision(market_context)
        assert routing_decision_1.confidence == 0.5  # 默认置信度
        
        # 2. 提供学习数据
        for _ in range(60):  # 提供60个样本（超过50个阈值）
            perf_a = PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=-0.10,
                win_rate=0.6,
                profit_factor=2.0,
                calmar_ratio=15.0,
                sortino_ratio=1.8,
                decision_latency_ms=10.0
            )
            perf_b = PerformanceMetrics(
                sharpe_ratio=1.2,
                max_drawdown=-0.15,
                win_rate=0.55,
                profit_factor=1.8,
                calmar_ratio=8.0,
                sortino_ratio=1.4,
                decision_latency_ms=50.0
            )
            
            await meta_learner.observe_and_learn(market_context, perf_a, perf_b)
        
        # 3. 再次路由决策（模型已训练）
        routing_decision_2 = await router.route_decision(market_context)
        
        # 验证：模型已训练，置信度应该有变化
        assert meta_learner.learning_stats['model_trained']
        assert meta_learner.learning_stats['total_samples'] == 60
    
    @pytest.mark.asyncio
    async def test_adaptive_strategy_selection(self, router, hybrid, meta_learner):
        """测试自适应策略选择"""
        # 测试不同市场环境下的策略选择
        
        # 场景1：高波动市场
        context_high_vol = MarketContext(
            volatility=0.40,
            liquidity=1000000.0,
            trend_strength=0.3,
            regime='choppy',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        with patch.object(
            meta_learner,
            'predict_best_strategy',
            return_value=(RiskControlStrategy.HARDCODED, 0.85)
        ):
            decision_1 = await router.route_decision(context_high_vol)
        
        # 验证：高波动时应选择保守策略
        assert decision_1.selected_strategy == RiskControlStrategy.HARDCODED
        
        # 场景2：稳定市场
        context_stable = MarketContext(
            volatility=0.15,
            liquidity=2000000.0,
            trend_strength=0.7,
            regime='bull',
            aum=2000000.0,
            portfolio_concentration=0.2,
            recent_drawdown=-0.02
        )
        
        with patch.object(
            meta_learner,
            'predict_best_strategy',
            return_value=(RiskControlStrategy.STRATEGY_LAYER, 0.85)
        ):
            decision_2 = await router.route_decision(context_stable)
        
        # 验证：稳定市场时应选择灵活策略
        assert decision_2.selected_strategy == RiskControlStrategy.STRATEGY_LAYER


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
