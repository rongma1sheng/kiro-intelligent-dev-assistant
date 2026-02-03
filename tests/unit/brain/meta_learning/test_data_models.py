"""元学习数据模型单元测试

白皮书依据: 第二章 2.2.4 风险控制元学习架构
"""

import pytest
from datetime import datetime

from src.brain.meta_learning.data_models import (
    MarketContext,
    PerformanceMetrics,
    LearningDataPoint
)


class TestMarketContext:
    """MarketContext数据模型测试"""
    
    def test_valid_market_context(self):
        """测试有效的市场上下文创建"""
        context = MarketContext(
            volatility=0.5,
            liquidity=0.8,
            trend_strength=0.3,
            regime='bull',
            aum=1000000.0,
            portfolio_concentration=0.6,
            recent_drawdown=0.05
        )
        
        assert context.volatility == 0.5
        assert context.liquidity == 0.8
        assert context.trend_strength == 0.3
        assert context.regime == 'bull'
        assert context.aum == 1000000.0
        assert context.portfolio_concentration == 0.6
        assert context.recent_drawdown == 0.05
    
    def test_invalid_volatility(self):
        """测试无效的波动率"""
        with pytest.raises(ValueError, match="volatility必须在"):
            MarketContext(
                volatility=1.5,  # 超出范围
                liquidity=0.8,
                trend_strength=0.3,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.6,
                recent_drawdown=0.05
            )
    
    def test_invalid_regime(self):
        """测试无效的市场状态"""
        with pytest.raises(ValueError, match="regime必须是"):
            MarketContext(
                volatility=0.5,
                liquidity=0.8,
                trend_strength=0.3,
                regime='invalid',  # 无效状态
                aum=1000000.0,
                portfolio_concentration=0.6,
                recent_drawdown=0.05
            )
    
    def test_negative_aum(self):
        """测试负数资金规模"""
        with pytest.raises(ValueError, match="aum必须≥0"):
            MarketContext(
                volatility=0.5,
                liquidity=0.8,
                trend_strength=0.3,
                regime='bull',
                aum=-1000.0,  # 负数
                portfolio_concentration=0.6,
                recent_drawdown=0.05
            )
    
    def test_boundary_values(self):
        """测试边界值"""
        # 最小值
        context_min = MarketContext(
            volatility=0.0,
            liquidity=0.0,
            trend_strength=-1.0,
            regime='bear',
            aum=0.0,
            portfolio_concentration=0.0,
            recent_drawdown=0.0
        )
        assert context_min.volatility == 0.0
        
        # 最大值
        context_max = MarketContext(
            volatility=1.0,
            liquidity=1.0,
            trend_strength=1.0,
            regime='bull',
            aum=1000000000.0,
            portfolio_concentration=1.0,
            recent_drawdown=1.0
        )
        assert context_max.volatility == 1.0
    
    def test_invalid_liquidity(self):
        """测试无效的流动性"""
        with pytest.raises(ValueError, match="liquidity必须在"):
            MarketContext(
                volatility=0.5,
                liquidity=1.5,  # 超出范围
                trend_strength=0.3,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.6,
                recent_drawdown=0.05
            )
    
    def test_invalid_trend_strength(self):
        """测试无效的趋势强度"""
        with pytest.raises(ValueError, match="trend_strength必须在"):
            MarketContext(
                volatility=0.5,
                liquidity=0.8,
                trend_strength=1.5,  # 超出范围
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.6,
                recent_drawdown=0.05
            )
    
    def test_invalid_portfolio_concentration(self):
        """测试无效的组合集中度"""
        with pytest.raises(ValueError, match="portfolio_concentration必须在"):
            MarketContext(
                volatility=0.5,
                liquidity=0.8,
                trend_strength=0.3,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=1.5,  # 超出范围
                recent_drawdown=0.05
            )
    
    def test_invalid_recent_drawdown(self):
        """测试无效的近期回撤"""
        with pytest.raises(ValueError, match="recent_drawdown必须在"):
            MarketContext(
                volatility=0.5,
                liquidity=0.8,
                trend_strength=0.3,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.6,
                recent_drawdown=1.5  # 超出范围
            )


class TestPerformanceMetrics:
    """PerformanceMetrics数据模型测试"""
    
    def test_valid_performance_metrics(self):
        """测试有效的性能指标创建"""
        metrics = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            profit_factor=2.0,
            calmar_ratio=1.8,
            sortino_ratio=1.6,
            decision_latency_ms=15.0
        )
        
        assert metrics.sharpe_ratio == 1.5
        assert metrics.max_drawdown == 0.1
        assert metrics.win_rate == 0.6
        assert metrics.profit_factor == 2.0
        assert metrics.calmar_ratio == 1.8
        assert metrics.sortino_ratio == 1.6
        assert metrics.decision_latency_ms == 15.0
    
    def test_invalid_max_drawdown(self):
        """测试无效的最大回撤"""
        with pytest.raises(ValueError, match="max_drawdown必须在"):
            PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=1.5,  # 超出范围
                win_rate=0.6,
                profit_factor=2.0,
                calmar_ratio=1.8,
                sortino_ratio=1.6,
                decision_latency_ms=15.0
            )
    
    def test_invalid_win_rate(self):
        """测试无效的胜率"""
        with pytest.raises(ValueError, match="win_rate必须在"):
            PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=1.5,  # 超出范围
                profit_factor=2.0,
                calmar_ratio=1.8,
                sortino_ratio=1.6,
                decision_latency_ms=15.0
            )
    
    def test_negative_profit_factor(self):
        """测试负数盈亏比"""
        with pytest.raises(ValueError, match="profit_factor必须≥0"):
            PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=0.6,
                profit_factor=-1.0,  # 负数
                calmar_ratio=1.8,
                sortino_ratio=1.6,
                decision_latency_ms=15.0
            )
    
    def test_negative_latency(self):
        """测试负数延迟"""
        with pytest.raises(ValueError, match="decision_latency_ms必须≥0"):
            PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=0.6,
                profit_factor=2.0,
                calmar_ratio=1.8,
                sortino_ratio=1.6,
                decision_latency_ms=-5.0  # 负数
            )


class TestLearningDataPoint:
    """LearningDataPoint数据模型测试"""
    
    def test_valid_learning_data_point(self):
        """测试有效的学习数据点创建"""
        market_context = MarketContext(
            volatility=0.5,
            liquidity=0.8,
            trend_strength=0.3,
            regime='bull',
            aum=1000000.0,
            portfolio_concentration=0.6,
            recent_drawdown=0.05
        )
        
        perf_a = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            profit_factor=2.0,
            calmar_ratio=1.8,
            sortino_ratio=1.6,
            decision_latency_ms=15.0
        )
        
        perf_b = PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=0.15,
            win_rate=0.55,
            profit_factor=1.8,
            calmar_ratio=1.5,
            sortino_ratio=1.4,
            decision_latency_ms=20.0
        )
        
        data_point = LearningDataPoint(
            market_context=market_context,
            strategy_a_performance=perf_a,
            strategy_b_performance=perf_b,
            winner='A',
            timestamp=datetime.now()
        )
        
        assert data_point.winner == 'A'
        assert data_point.market_context == market_context
        assert data_point.strategy_a_performance == perf_a
        assert data_point.strategy_b_performance == perf_b
    
    def test_invalid_winner(self):
        """测试无效的获胜者"""
        market_context = MarketContext(
            volatility=0.5,
            liquidity=0.8,
            trend_strength=0.3,
            regime='bull',
            aum=1000000.0,
            portfolio_concentration=0.6,
            recent_drawdown=0.05
        )
        
        perf_a = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            profit_factor=2.0,
            calmar_ratio=1.8,
            sortino_ratio=1.6,
            decision_latency_ms=15.0
        )
        
        perf_b = PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=0.15,
            win_rate=0.55,
            profit_factor=1.8,
            calmar_ratio=1.5,
            sortino_ratio=1.4,
            decision_latency_ms=20.0
        )
        
        with pytest.raises(ValueError, match="winner必须是"):
            LearningDataPoint(
                market_context=market_context,
                strategy_a_performance=perf_a,
                strategy_b_performance=perf_b,
                winner='C',  # 无效
                timestamp=datetime.now()
            )
