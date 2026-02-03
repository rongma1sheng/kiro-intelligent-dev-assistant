"""
StressTestAnalyzer单元测试

测试极限压力测试分析器的5种场景测试功能

作者: MIA Team
日期: 2026-01-20
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.evolution.stress_test_analyzer import (
    StressTestAnalyzer,
    ScenarioType,
    ScenarioResult,
    StressTestResult
)


@pytest.fixture
def analyzer():
    """创建测试用的StressTestAnalyzer实例"""
    return StressTestAnalyzer(market_type='A_STOCK')


@pytest.fixture
def sample_strategy_returns():
    """生成样本策略收益率数据"""
    np.random.seed(42)
    # 生成250天的收益率数据 (约1年)
    returns = np.random.normal(0.001, 0.02, 250)  # 均值0.1%, 标准差2%
    return pd.Series(returns, index=pd.date_range('2023-01-01', periods=250))


@pytest.fixture
def sample_market_returns():
    """生成样本市场收益率数据"""
    np.random.seed(43)
    returns = np.random.normal(0.0005, 0.015, 250)  # 均值0.05%, 标准差1.5%
    return pd.Series(returns, index=pd.date_range('2023-01-01', periods=250))


@pytest.fixture
def sample_market_volume():
    """生成样本市场成交量数据"""
    np.random.seed(44)
    volume = np.random.lognormal(10, 0.5, 250)  # 对数正态分布
    return pd.Series(volume, index=pd.date_range('2023-01-01', periods=250))


class TestStressTestAnalyzer:
    """StressTestAnalyzer基础功能测试"""
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.market_type == 'A_STOCK'
        assert hasattr(analyzer, 'STRESS_TEST_STANDARDS')
        assert len(analyzer.STRESS_TEST_STANDARDS) == 5
    
    def test_stress_test_standards(self, analyzer):
        """测试压力测试标准定义"""
        standards = analyzer.STRESS_TEST_STANDARDS
        
        assert standards['crash_survival_rate'] == 0.8
        assert standards['bear_market_max_loss'] == 0.20
        assert standards['liquidity_crisis_survival'] == 0.7
        assert standards['black_swan_recovery_days'] == 30
        assert standards['correlation_breakdown_handling'] == 0.6



class TestCrashScenario:
    """崩盘场景测试"""
    
    @pytest.mark.asyncio
    async def test_crash_scenario_basic(self, analyzer, sample_strategy_returns, sample_market_returns):
        """测试崩盘场景基本功能"""
        result = await analyzer.run_crash_scenario(sample_strategy_returns, sample_market_returns)
        
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.CRASH
        assert result.survival_rate is not None
        assert 0 <= result.survival_rate <= 1
        assert result.score is not None
        assert 0 <= result.score <= 1
    
    @pytest.mark.asyncio
    async def test_crash_scenario_survival_rate(self, analyzer):
        """测试崩盘场景存活率计算"""
        # 创建一个在崩盘中表现良好的策略
        good_strategy = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02] * 50)
        market = pd.Series([-0.08, -0.06, -0.05, -0.04, -0.03] * 50)
        
        result = await analyzer.run_crash_scenario(good_strategy, market)
        
        # 良好策略应该有较高的存活率
        assert result.survival_rate > 0.7
        assert result.passed or result.survival_rate >= 0.75
    
    @pytest.mark.asyncio
    async def test_crash_scenario_failure(self, analyzer):
        """测试崩盘场景失败情况"""
        # 创建一个在崩盘中表现糟糕的策略
        bad_strategy = pd.Series([-0.10, -0.08, -0.12, -0.09, -0.11] * 50)
        market = pd.Series([-0.08, -0.06, -0.05, -0.04, -0.03] * 50)
        
        result = await analyzer.run_crash_scenario(bad_strategy, market)
        
        # 糟糕策略应该有较低的存活率
        assert result.survival_rate < 0.8
        if not result.passed:
            assert result.failure_reason is not None
            assert '存活率' in result.failure_reason


class TestBearMarketScenario:
    """熊市场景测试"""
    
    @pytest.mark.asyncio
    async def test_bear_market_basic(self, analyzer, sample_strategy_returns, sample_market_returns):
        """测试熊市场景基本功能"""
        result = await analyzer.run_bear_market_scenario(sample_strategy_returns, sample_market_returns)
        
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.BEAR_MARKET
        assert result.max_loss is not None
        assert result.max_loss >= 0
        assert result.score is not None
    
    @pytest.mark.asyncio
    async def test_bear_market_max_loss(self, analyzer):
        """测试熊市场景最大亏损计算"""
        # 创建一个在熊市中控制回撤的策略
        controlled_strategy = pd.Series([0.005, -0.01, 0.008, -0.005, 0.006] * 50)
        market = pd.Series([-0.02, -0.015, -0.01, -0.018, -0.012] * 50)
        
        result = await analyzer.run_bear_market_scenario(controlled_strategy, market)
        
        # 控制良好的策略最大亏损应该较小
        assert result.max_loss < 0.25
    
    @pytest.mark.asyncio
    async def test_bear_market_pass_criteria(self, analyzer):
        """测试熊市场景通过标准"""
        # 创建一个刚好达标的策略
        passing_strategy = pd.Series([0.01, -0.015, 0.012, -0.008, 0.009] * 50)
        market = pd.Series([-0.02, -0.015, -0.01, -0.018, -0.012] * 50)
        
        result = await analyzer.run_bear_market_scenario(passing_strategy, market)
        
        # 验证通过标准
        if result.passed:
            assert result.max_loss <= analyzer.STRESS_TEST_STANDARDS['bear_market_max_loss']



class TestLiquidityCrisisScenario:
    """流动性危机场景测试"""
    
    @pytest.mark.asyncio
    async def test_liquidity_crisis_basic(self, analyzer, sample_strategy_returns, sample_market_volume):
        """测试流动性危机场景基本功能"""
        result = await analyzer.run_liquidity_crisis_scenario(sample_strategy_returns, sample_market_volume)
        
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.LIQUIDITY_CRISIS
        assert result.survival_rate is not None
        assert result.adaptation_score is not None
    
    @pytest.mark.asyncio
    async def test_liquidity_crisis_without_volume(self, analyzer, sample_strategy_returns):
        """测试没有成交量数据时的流动性危机场景"""
        result = await analyzer.run_liquidity_crisis_scenario(sample_strategy_returns, None)
        
        # 应该使用模拟数据
        assert result is not None
        assert result.survival_rate is not None
    
    @pytest.mark.asyncio
    async def test_liquidity_crisis_survival(self, analyzer):
        """测试流动性危机存活率"""
        # 创建一个能应对流动性危机的策略
        resilient_strategy = pd.Series([0.008, 0.006, 0.007, 0.005, 0.009] * 50)
        
        result = await analyzer.run_liquidity_crisis_scenario(resilient_strategy, None)
        
        # 应该有合理的存活率
        assert result.survival_rate > 0.5


class TestBlackSwanScenario:
    """黑天鹅事件场景测试"""
    
    @pytest.mark.asyncio
    async def test_black_swan_basic(self, analyzer, sample_strategy_returns):
        """测试黑天鹅事件场景基本功能"""
        result = await analyzer.run_black_swan_scenario(sample_strategy_returns)
        
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.BLACK_SWAN
        assert result.recovery_days is not None
        assert result.recovery_days > 0
        assert result.max_loss is not None
    
    @pytest.mark.asyncio
    async def test_black_swan_recovery_time(self, analyzer):
        """测试黑天鹅事件恢复时间"""
        # 创建一个快速恢复的策略
        quick_recovery = pd.Series([0.02, 0.025, 0.03, 0.028, 0.022] * 50)
        
        result = await analyzer.run_black_swan_scenario(quick_recovery)
        
        # 快速恢复的策略恢复天数应该较短
        assert result.recovery_days <= 30
    
    @pytest.mark.asyncio
    async def test_black_swan_pass_criteria(self, analyzer, sample_strategy_returns):
        """测试黑天鹅事件通过标准"""
        result = await analyzer.run_black_swan_scenario(sample_strategy_returns)
        
        if result.passed:
            assert result.recovery_days <= analyzer.STRESS_TEST_STANDARDS['black_swan_recovery_days']
        else:
            assert result.failure_reason is not None
            assert '恢复天数' in result.failure_reason


class TestCorrelationBreakdownScenario:
    """相关性失效场景测试"""
    
    @pytest.mark.asyncio
    async def test_correlation_breakdown_basic(self, analyzer, sample_strategy_returns, sample_market_returns):
        """测试相关性失效场景基本功能"""
        result = await analyzer.run_correlation_breakdown_scenario(sample_strategy_returns, sample_market_returns)
        
        assert isinstance(result, ScenarioResult)
        assert result.scenario_type == ScenarioType.CORRELATION_BREAKDOWN
        assert result.adaptation_score is not None
        assert 0 <= result.adaptation_score <= 1
    
    @pytest.mark.asyncio
    async def test_correlation_breakdown_adaptation(self, analyzer):
        """测试相关性失效适应能力"""
        # 创建一个适应能力强的策略
        adaptive_strategy = pd.Series([0.01, 0.012, 0.009, 0.011, 0.010] * 50)
        market = pd.Series([0.005, -0.003, 0.008, -0.002, 0.006] * 50)
        
        result = await analyzer.run_correlation_breakdown_scenario(adaptive_strategy, market)
        
        # 适应能力强的策略评分应该较高
        assert result.adaptation_score > 0.4
    
    @pytest.mark.asyncio
    async def test_correlation_breakdown_pass_criteria(self, analyzer, sample_strategy_returns, sample_market_returns):
        """测试相关性失效通过标准"""
        result = await analyzer.run_correlation_breakdown_scenario(sample_strategy_returns, sample_market_returns)
        
        if result.passed:
            assert result.adaptation_score >= analyzer.STRESS_TEST_STANDARDS['correlation_breakdown_handling']



class TestAllScenarios:
    """所有场景综合测试"""
    
    @pytest.mark.asyncio
    async def test_run_all_scenarios(self, analyzer, sample_strategy_returns, sample_market_returns, sample_market_volume):
        """测试运行所有场景"""
        result = await analyzer.run_all_scenarios(
            sample_strategy_returns,
            sample_market_returns,
            sample_market_volume
        )
        
        assert isinstance(result, StressTestResult)
        assert len(result.scenario_results) == 5
        assert result.overall_score is not None
        assert 0 <= result.overall_score <= 1
        assert result.scenarios_passed + result.scenarios_failed == 5
    
    @pytest.mark.asyncio
    async def test_all_scenarios_scoring(self, analyzer, sample_strategy_returns, sample_market_returns):
        """测试所有场景综合评分"""
        result = await analyzer.run_all_scenarios(
            sample_strategy_returns,
            sample_market_returns,
            None
        )
        
        # 验证评分计算
        expected_score = (
            result.scenario_results['crash'].score * 0.25 +
            result.scenario_results['bear_market'].score * 0.20 +
            result.scenario_results['liquidity_crisis'].score * 0.20 +
            result.scenario_results['black_swan'].score * 0.20 +
            result.scenario_results['correlation_breakdown'].score * 0.15
        )
        
        assert abs(result.overall_score - expected_score) < 0.01
    
    @pytest.mark.asyncio
    async def test_all_scenarios_pass_criteria(self, analyzer, sample_strategy_returns, sample_market_returns):
        """测试所有场景通过标准"""
        result = await analyzer.run_all_scenarios(
            sample_strategy_returns,
            sample_market_returns,
            None
        )
        
        # 通过标准: 至少4个场景通过 且 综合评分≥0.7
        if result.passed:
            assert result.scenarios_passed >= 4
            assert result.overall_score >= 0.7
        else:
            assert result.scenarios_passed < 4 or result.overall_score < 0.7
    
    @pytest.mark.asyncio
    async def test_all_scenarios_failed_list(self, analyzer):
        """测试失败场景列表"""
        # 创建一个表现糟糕的策略
        bad_strategy = pd.Series([-0.05, -0.04, -0.06, -0.03, -0.07] * 50)
        market = pd.Series([-0.02, -0.015, -0.01, -0.018, -0.012] * 50)
        
        result = await analyzer.run_all_scenarios(bad_strategy, market, None)
        
        # 应该有失败的场景
        if result.scenarios_failed > 0:
            assert len(result.failed_scenarios) == result.scenarios_failed
            assert all(name in result.scenario_results for name in result.failed_scenarios)


class TestHelperMethods:
    """辅助方法测试"""
    
    def test_identify_crash_periods(self, analyzer, sample_market_returns):
        """测试识别崩盘期间"""
        # 创建包含崩盘的市场数据
        crash_market = sample_market_returns.copy()
        crash_market.iloc[50] = -0.08  # 单日暴跌8%
        crash_market.iloc[100:103] = [-0.04, -0.04, -0.03]  # 连续下跌
        
        periods = analyzer._identify_crash_periods(crash_market)
        
        assert isinstance(periods, list)
        assert len(periods) > 0
        assert all(isinstance(p, tuple) and len(p) == 2 for p in periods)
    
    def test_identify_bear_market_periods(self, analyzer, sample_market_returns):
        """测试识别熊市期间"""
        # 创建包含熊市的市场数据
        bear_market = sample_market_returns.copy()
        bear_market.iloc[0:80] = -0.005  # 持续下跌80天
        
        periods = analyzer._identify_bear_market_periods(bear_market)
        
        assert isinstance(periods, list)
        # 可能识别到熊市期间
        if periods:
            assert all(isinstance(p, tuple) and len(p) == 2 for p in periods)
    
    def test_merge_periods(self, analyzer):
        """测试合并重叠时间段"""
        periods = [(0, 10), (5, 15), (20, 30), (25, 35)]
        merged = analyzer._merge_periods(periods)
        
        assert len(merged) == 2
        assert merged[0] == (0, 15)
        assert merged[1] == (20, 35)
    
    def test_simulate_crash_scenario(self, analyzer):
        """测试模拟崩盘场景"""
        periods = analyzer._simulate_crash_scenario()
        
        assert isinstance(periods, list)
        assert len(periods) > 0
        assert all(isinstance(p, tuple) and len(p) == 2 for p in periods)
    
    def test_simulate_bear_market_scenario(self, analyzer):
        """测试模拟熊市场景"""
        periods = analyzer._simulate_bear_market_scenario()
        
        assert isinstance(periods, list)
        assert len(periods) > 0
        assert all(isinstance(p, tuple) and len(p) == 2 for p in periods)


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_empty_returns(self, analyzer):
        """测试空收益率序列"""
        empty_returns = pd.Series([], dtype=float)
        market_returns = pd.Series([0.01] * 10)
        
        # 应该能处理空数据而不崩溃
        try:
            result = await analyzer.run_crash_scenario(empty_returns, market_returns)
            assert result is not None
        except Exception as e:
            # 如果抛出异常，应该是有意义的异常
            assert isinstance(e, (ValueError, IndexError))
    
    @pytest.mark.asyncio
    async def test_single_day_returns(self, analyzer):
        """测试单日收益率"""
        single_return = pd.Series([0.01])
        market_return = pd.Series([0.005])
        
        result = await analyzer.run_black_swan_scenario(single_return)
        
        assert result is not None
        assert result.recovery_days is not None
    
    @pytest.mark.asyncio
    async def test_extreme_volatility(self, analyzer):
        """测试极端波动率"""
        # 创建极端波动的策略
        extreme_returns = pd.Series([0.10, -0.15, 0.20, -0.18, 0.12] * 50)
        market = pd.Series([0.02, -0.03, 0.025, -0.028, 0.022] * 50)
        
        result = await analyzer.run_all_scenarios(extreme_returns, market, None)
        
        # 应该能处理极端波动
        assert result is not None
        assert result.overall_score is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
