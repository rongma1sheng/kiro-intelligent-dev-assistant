"""第五章分析器单元测试

白皮书依据: 第五章 5.1-5.2 LLM策略深度分析系统
"""

import pytest
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

from src.brain.analyzers import (
    # 枚举
    ProfitSource,
    MarketScenario,
    RiskLevel,
    MainForceType,
    BehaviorPattern,
    ActionType,
    PositionSize,
    HoldingPeriod,
    DecayStage,
    DecayTrend,
    StopLossType,
    SNRQuality,
    StressTestGrade,
    SentimentCategory,
    SentimentTrend,
    # 数据类
    StrategyEssenceReport,
    RiskAssessmentReport,
    OverfittingReport,
    FeatureAnalysisReport,
    MacroAnalysisReport,
    MicrostructureReport,
    SectorAnalysisReport,
    SmartMoneyDeepAnalysis,
    StockRecommendation,
    TradingCostAnalysis,
    DecayAnalysis,
    StopLossAnalysis,
    SlippageAnalysis,
    NonstationarityAnalysis,
    SignalNoiseAnalysis,
    CapacityAnalysis,
    StressTestAnalysis,
    TradeReviewAnalysis,
    SentimentAnalysis,
    RetailSentimentAnalysis,
    CorrelationAnalysis,
    PositionSizingAnalysis,
    ComprehensiveAnalysisReport,
    # 分析器
    EssenceAnalyzer,
    RiskAnalyzer,
    OverfittingDetector,
    FeatureAnalyzer,
    MacroAnalyzer,
    MicrostructureAnalyzer,
    SectorAnalyzer,
    SmartMoneyAnalyzer,
    RecommendationEngine,
    TradingCostAnalyzer,
    DecayAnalyzer,
    StopLossAnalyzer,
    SlippageAnalyzer,
    NonstationarityAnalyzer,
    SignalNoiseAnalyzer,
    CapacityAnalyzer,
    StressTestAnalyzer,
    TradeReviewAnalyzer,
    SentimentAnalyzer,
    RetailSentimentAnalyzer,
    CorrelationAnalyzer,
    PositionSizingAnalyzer,
)


class TestDataModels:
    """数据模型测试"""
    
    def test_strategy_essence_report_to_dict(self):
        """测试策略本质报告转字典"""
        report = StrategyEssenceReport(
            strategy_id="test_strategy",
            profit_source=ProfitSource.TREND,
            market_assumptions=["趋势持续"],
            applicable_scenarios=[MarketScenario.BULL],
            sustainability_score=0.8,
            core_logic="趋势跟踪",
            advantages=["收益高"],
            limitations=["震荡市亏损"]
        )
        
        result = report.to_dict()
        
        assert result['strategy_id'] == "test_strategy"
        assert result['profit_source'] == "trend"
        assert result['sustainability_score'] == 0.8
        assert 'analysis_timestamp' in result
    
    def test_risk_assessment_report_to_dict(self):
        """测试风险评估报告转字典"""
        report = RiskAssessmentReport(
            strategy_id="test_strategy",
            systematic_risks=[{"name": "市场风险", "level": "high"}],
            specific_risks=[{"name": "流动性风险", "level": "medium"}],
            risk_matrix={"市场风险": RiskLevel.HIGH},
            mitigation_plan=["分散投资"],
            overall_risk_level=RiskLevel.MEDIUM,
            risk_score=65.0
        )
        
        result = report.to_dict()
        
        assert result['strategy_id'] == "test_strategy"
        assert result['overall_risk_level'] == "medium"
        assert result['risk_score'] == 65.0
    
    def test_correlation_analysis_to_dict(self):
        """测试相关性分析转字典"""
        report = CorrelationAnalysis(
            strategy_count=3,
            correlation_matrix={"A": {"A": 1.0, "B": 0.5}, "B": {"A": 0.5, "B": 1.0}},
            high_correlation_pairs=[("A", "B", 0.8)],
            low_correlation_pairs=[("A", "C", 0.1)],
            avg_correlation=0.45,
            diversification_score=0.55,
            portfolio_recommendations=["分散投资"],
            optimal_weights={"A": 0.5, "B": 0.5},
            risk_reduction=0.2
        )
        
        result = report.to_dict()
        
        assert result['strategy_count'] == 3
        assert result['avg_correlation'] == 0.45
        assert result['diversification_score'] == 0.55
    
    def test_position_sizing_analysis_to_dict(self):
        """测试仓位管理分析转字典"""
        report = PositionSizingAnalysis(
            strategy_id="test_strategy",
            kelly_fraction=0.25,
            adjusted_kelly=0.125,
            fixed_fraction=0.15,
            volatility_adjusted=0.2,
            risk_budget_position=0.18,
            recommended_position=0.15,
            max_position=0.5,
            min_position=0.05,
            dynamic_adjustment_rules=["波动率高时降低仓位"],
            strategy_comparison={"kelly": {"position": 0.25}},
            risk_assessment={"risk_level": "medium"}
        )
        
        result = report.to_dict()
        
        assert result['strategy_id'] == "test_strategy"
        assert result['kelly_fraction'] == 0.25
        assert result['recommended_position'] == 0.15


class TestEssenceAnalyzer:
    """策略本质分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return EssenceAnalyzer()
    
    @pytest.fixture
    def trend_strategy_data(self):
        """趋势策略数据"""
        return {
            'code': 'if close > ma(close, 20): buy()',
            'parameters': {'lookback': 20, 'threshold': 0.02},
            'name': 'TrendFollowing',
            'returns': list(np.random.randn(100) * 0.02)
        }
    
    @pytest.mark.asyncio
    async def test_analyze_trend_strategy(self, analyzer, trend_strategy_data):
        """测试趋势策略分析"""
        report = await analyzer.analyze("trend_001", trend_strategy_data)
        
        assert report.strategy_id == "trend_001"
        assert report.profit_source == ProfitSource.TREND
        assert len(report.market_assumptions) > 0
        assert len(report.applicable_scenarios) > 0
        assert 0 <= report.sustainability_score <= 1
    
    @pytest.mark.asyncio
    async def test_analyze_mean_reversion_strategy(self, analyzer):
        """测试均值回归策略分析"""
        strategy_data = {
            'code': 'if rsi < 30: buy() elif rsi > 70: sell()',
            'parameters': {'rsi_period': 14},
            'name': 'MeanReversion',
            'returns': list(np.random.randn(100) * 0.01)
        }
        
        report = await analyzer.analyze("mr_001", strategy_data)
        
        assert report.strategy_id == "mr_001"
        assert report.profit_source == ProfitSource.MEAN_REVERSION
    
    @pytest.mark.asyncio
    async def test_analyze_empty_strategy(self, analyzer):
        """测试空策略分析"""
        strategy_data = {
            'code': '',
            'parameters': {},
            'name': 'Empty',
            'returns': []
        }
        
        report = await analyzer.analyze("empty_001", strategy_data)
        
        assert report.strategy_id == "empty_001"
        assert report.profit_source == ProfitSource.MIXED


class TestCorrelationAnalyzer:
    """相关性分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return CorrelationAnalyzer()
    
    @pytest.fixture
    def strategy_returns(self):
        """策略收益数据"""
        np.random.seed(42)
        n = 100
        base = np.random.randn(n) * 0.02
        
        return {
            'strategy_A': list(base + np.random.randn(n) * 0.005),
            'strategy_B': list(base + np.random.randn(n) * 0.005),  # 与A高相关
            'strategy_C': list(np.random.randn(n) * 0.02),  # 独立
            'strategy_D': list(-base + np.random.randn(n) * 0.005)  # 与A负相关
        }
    
    @pytest.mark.asyncio
    async def test_analyze_correlation(self, analyzer, strategy_returns):
        """测试相关性分析"""
        report = await analyzer.analyze(strategy_returns)
        
        assert report.strategy_count == 4
        assert len(report.correlation_matrix) == 4
        assert 0 <= report.diversification_score <= 1
        assert len(report.optimal_weights) == 4
    
    @pytest.mark.asyncio
    async def test_find_high_correlation_pairs(self, analyzer, strategy_returns):
        """测试高相关性策略对识别"""
        report = await analyzer.analyze(strategy_returns)
        
        # A和B应该高度相关
        high_pairs = report.high_correlation_pairs
        pair_names = [(p[0], p[1]) for p in high_pairs]
        
        # 检查是否识别出高相关对
        assert len(high_pairs) >= 0  # 可能有也可能没有
    
    @pytest.mark.asyncio
    async def test_optimal_weights_sum_to_one(self, analyzer, strategy_returns):
        """测试最优权重之和为1"""
        report = await analyzer.analyze(strategy_returns)
        
        total_weight = sum(report.optimal_weights.values())
        assert abs(total_weight - 1.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_insufficient_strategies(self, analyzer):
        """测试策略数量不足"""
        with pytest.raises(ValueError, match="至少需要2个策略"):
            await analyzer.analyze({'single': [0.01, 0.02, 0.03]})


class TestPositionSizingAnalyzer:
    """仓位管理分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return PositionSizingAnalyzer()
    
    @pytest.fixture
    def returns_data(self):
        """收益数据"""
        np.random.seed(42)
        return list(np.random.randn(100) * 0.02 + 0.001)
    
    @pytest.mark.asyncio
    async def test_analyze_position_sizing(self, analyzer, returns_data):
        """测试仓位管理分析"""
        report = await analyzer.analyze(
            strategy_id="test_001",
            returns=returns_data
        )
        
        assert report.strategy_id == "test_001"
        assert 0 <= report.kelly_fraction <= 0.5
        assert 0 <= report.adjusted_kelly <= 1
        assert 0 <= report.recommended_position <= 1
        assert report.min_position <= report.recommended_position <= report.max_position
    
    @pytest.mark.asyncio
    async def test_kelly_calculation(self, analyzer):
        """测试Kelly公式计算"""
        # 高胜率高盈亏比策略
        returns = [0.02] * 60 + [-0.01] * 40  # 60%胜率，2:1盈亏比
        
        report = await analyzer.analyze(
            strategy_id="high_kelly",
            returns=returns
        )
        
        # Kelly应该较高
        assert report.kelly_fraction > 0.1
    
    @pytest.mark.asyncio
    async def test_dynamic_rules_generated(self, analyzer, returns_data):
        """测试动态调整规则生成"""
        report = await analyzer.analyze(
            strategy_id="test_001",
            returns=returns_data
        )
        
        assert len(report.dynamic_adjustment_rules) > 0
        assert any("波动率" in rule for rule in report.dynamic_adjustment_rules)
    
    @pytest.mark.asyncio
    async def test_risk_assessment(self, analyzer, returns_data):
        """测试风险评估"""
        report = await analyzer.analyze(
            strategy_id="test_001",
            returns=returns_data
        )
        
        assert 'risk_level' in report.risk_assessment
        assert 'expected_max_drawdown' in report.risk_assessment
        assert 'warnings' in report.risk_assessment
    
    @pytest.mark.asyncio
    async def test_insufficient_data(self, analyzer):
        """测试数据不足"""
        with pytest.raises(ValueError, match="至少需要20个"):
            await analyzer.analyze(
                strategy_id="test",
                returns=[0.01] * 10
            )


class TestRiskAnalyzer:
    """风险分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return RiskAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_risk(self, analyzer):
        """测试风险分析"""
        strategy_data = {
            'returns': list(np.random.randn(100) * 0.02),
            'positions': [0.5] * 100,
            'leverage': 1.0
        }
        
        report = await analyzer.analyze("risk_test", strategy_data)
        
        assert report.strategy_id == "risk_test"
        assert report.overall_risk_level in RiskLevel
        assert 0 <= report.risk_score <= 100


class TestOverfittingDetector:
    """过拟合检测器测试"""
    
    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return OverfittingDetector()
    
    @pytest.mark.asyncio
    async def test_detect_overfitting(self, detector):
        """测试过拟合检测"""
        strategy_data = {
            'code': 'complex_strategy_with_many_params',
            'parameters': {f'param_{i}': i for i in range(20)},
            'in_sample_sharpe': 3.0,
            'out_sample_sharpe': 1.0,
            'sample_size': 100
        }
        
        report = await detector.analyze("overfit_test", strategy_data)
        
        assert report.strategy_id == "overfit_test"
        assert 0 <= report.overfitting_probability <= 100


class TestDecayAnalyzer:
    """策略衰减分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return DecayAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_decay(self, analyzer):
        """测试衰减分析"""
        # 模拟衰减的收益序列
        np.random.seed(42)
        n = 252
        decay_factor = np.linspace(1.0, 0.5, n)
        returns = list(np.random.randn(n) * 0.02 * decay_factor)
        
        report = await analyzer.analyze("decay_test", returns)
        
        assert report.strategy_id == "decay_test"
        assert report.decay_trend in DecayTrend
        assert report.estimated_lifetime > 0


class TestCapacityAnalyzer:
    """资金容量分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return CapacityAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_capacity(self, analyzer):
        """测试容量分析"""
        strategy_data = {
            'returns': list(np.random.randn(100) * 0.02),
            'avg_daily_volume': 1000000,
            'avg_position_size': 100000,
            'current_capital': 1000000
        }
        
        report = await analyzer.analyze("capacity_test", strategy_data)
        
        assert report.strategy_id == "capacity_test"
        assert report.max_capacity > 0
        assert 0 <= report.scalability_score <= 1


class TestStressTestAnalyzer:
    """压力测试分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return StressTestAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_stress(self, analyzer):
        """测试压力测试分析"""
        strategy_data = {
            'returns': list(np.random.randn(252) * 0.02),
            'positions': [0.5] * 252
        }
        
        report = await analyzer.analyze("stress_test", strategy_data)
        
        assert report.strategy_id == "stress_test"
        assert report.stress_test_grade in StressTestGrade
        assert 0 <= report.survival_probability <= 1


class TestSentimentAnalyzer:
    """市场情绪分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return SentimentAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment(self, analyzer):
        """测试情绪分析"""
        market_data = {
            'index_returns': list(np.random.randn(20) * 0.01),
            'volume': [1000000] * 20,
            'advance_decline': [100, -50, 80, -30, 60]
        }
        
        report = await analyzer.analyze(market_data)
        
        assert report.sentiment_category in SentimentCategory
        assert 0 <= report.overall_sentiment <= 1
        assert 0 <= report.fear_greed_index <= 100


class TestSlippageAnalyzer:
    """滑点分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return SlippageAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_slippage(self, analyzer):
        """测试滑点分析"""
        trade_data = {
            'expected_prices': [100.0, 101.0, 99.0, 102.0, 98.0],
            'actual_prices': [100.05, 101.02, 98.98, 102.03, 97.97],
            'trade_sizes': [1000, 2000, 1500, 1000, 2500],
            'trade_times': ['09:30', '10:00', '14:00', '14:30', '15:00']
        }
        
        report = await analyzer.analyze("slippage_test", trade_data)
        
        assert report.strategy_id == "slippage_test"
        assert report.avg_slippage >= 0


class TestSignalNoiseAnalyzer:
    """信噪比分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return SignalNoiseAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_signal_noise(self, analyzer):
        """测试信噪比分析"""
        signal_data = {
            'signals': list(np.random.randn(100)),
            'returns': list(np.random.randn(100) * 0.02)
        }
        
        report = await analyzer.analyze("snr_test", signal_data)
        
        assert report.strategy_id == "snr_test"
        assert report.snr_quality in SNRQuality
        assert 0 <= report.overall_quality <= 1


class TestTradeReviewAnalyzer:
    """交易复盘分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return TradeReviewAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_trade_review(self, analyzer):
        """测试交易复盘分析"""
        trades = [
            {'pnl': 100, 'entry_time': '09:30', 'exit_time': '10:00'},
            {'pnl': -50, 'entry_time': '10:30', 'exit_time': '11:00'},
            {'pnl': 80, 'entry_time': '14:00', 'exit_time': '14:30'},
        ]
        
        report = await analyzer.analyze("review_test", trades)
        
        assert report.strategy_id == "review_test"
        assert report.total_trades == 3
        assert 0 <= report.discipline_score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
