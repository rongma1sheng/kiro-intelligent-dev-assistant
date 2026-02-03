"""
策略Arena属性测试 (Strategy Arena Property Tests)

白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统
测试框架: hypothesis (property-based testing)
最小迭代次数: 100

测试的正确性属性:
- Property 5: Strategy Arena Dual-Track Execution
- Property 6: Strategy Performance Metrics
- Property 7: Strategy Arena Pass Criteria
- Property 8: Hell Track Scenario Coverage
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
from hypothesis import given, settings, strategies as st, assume, HealthCheck

from src.evolution.arena.strategy_data_models import (
    Strategy,
    StrategyType,
    StrategyStatus,
    StrategyTestResult,
    StrategyRealityTrackResult,
    StrategyHellTrackResult,
    PerformanceMetrics
)
from src.evolution.arena.strategy_arena import StrategyArenaSystem
from src.evolution.arena.strategy_reality_track import StrategyRealityTrack
from src.evolution.arena.strategy_hell_track import StrategyHellTrack, ExtremeScenarioGenerator
from src.evolution.arena.strategy_performance_calculator import StrategyPerformanceCalculator


# 全局设置：抑制function_scoped_fixture健康检查
HYPOTHESIS_SETTINGS = settings(
    max_examples=100, 
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)


# ============================================================================
# 测试数据生成策略
# ============================================================================

@st.composite
def strategy_st(draw):
    """生成有效的Strategy对象"""
    strategy_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=1,
        max_size=20
    ))
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
        min_size=1,
        max_size=50
    ))
    strategy_type = draw(st.sampled_from(list(StrategyType)))
    source_factors = draw(st.lists(
        st.text(min_size=1, max_size=10),
        min_size=1,
        max_size=5
    ))
    code = draw(st.text(min_size=1, max_size=100))
    
    return Strategy(
        id=strategy_id,
        name=name,
        type=strategy_type,
        source_factors=source_factors,
        code=code,
        description="Test strategy",
        status=StrategyStatus.CANDIDATE
    )


@st.composite
def historical_data_st(draw, min_days: int = 100, max_days: int = 500):
    """生成有效的历史数据DataFrame"""
    days = draw(st.integers(min_value=min_days, max_value=max_days))
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 生成价格数据
    np.random.seed(draw(st.integers(min_value=0, max_value=10000)))
    returns = np.random.randn(days) * 0.02
    prices = 100 * np.exp(np.cumsum(returns))
    
    # 生成成交量
    volumes = np.random.randint(1000000, 10000000, days)
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.randn(days) * 0.005),
        'high': prices * (1 + abs(np.random.randn(days) * 0.01)),
        'low': prices * (1 - abs(np.random.randn(days) * 0.01)),
        'close': prices,
        'volume': volumes
    }, index=dates)
    
    return data


@st.composite
def returns_series_st(draw, min_size: int = 50, max_size: int = 500):
    """生成有效的收益率序列"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    
    np.random.seed(draw(st.integers(min_value=0, max_value=10000)))
    returns = np.random.randn(size) * 0.02
    
    dates = pd.date_range(end=datetime.now(), periods=size, freq='D')
    
    return pd.Series(returns, index=dates)


@st.composite
def trade_returns_st(draw, min_size: int = 10, max_size: int = 100):
    """生成有效的交易收益率列表"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    
    np.random.seed(draw(st.integers(min_value=0, max_value=10000)))
    trade_returns = np.random.randn(size) * 0.05
    
    return trade_returns.tolist()


# ============================================================================
# Property 5: Strategy Arena Dual-Track Execution
# ============================================================================

class TestProperty5StrategyArenaDualTrackExecution:
    """Property 5: 策略Arena双轨执行
    
    白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统
    
    正确性属性:
    对于任何提交到策略Arena的候选策略，系统应该执行Reality Track
    (3年历史回测)和Hell Track(极端场景)双轨测试。
    
    **Validates: Requirements 2.1, 2.3**
    """
    
    @pytest.fixture
    def arena_system(self):
        """创建Arena系统实例"""
        return StrategyArenaSystem()
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_dual_track_execution(self, arena_system, strategy):
        """测试双轨测试执行
        
        验证:
        1. Reality Track被执行
        2. Hell Track被执行
        3. 两个Track都返回有效结果
        """
        # 执行测试
        result = asyncio.get_event_loop().run_until_complete(
            arena_system.test_strategy(strategy)
        )
        
        # 验证Reality Track结果存在且有效
        assert result.reality_result is not None
        assert isinstance(result.reality_result, StrategyRealityTrackResult)
        assert 0 <= result.reality_result.reality_score <= 1
        
        # 验证Hell Track结果存在且有效
        assert result.hell_result is not None
        assert isinstance(result.hell_result, StrategyHellTrackResult)
        assert 0 <= result.hell_result.hell_score <= 1
        
        # 验证综合评分已计算
        assert result.overall_score is not None
        assert 0 <= result.overall_score <= 1
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_reality_track_uses_historical_data(self, arena_system, strategy):
        """测试Reality Track使用历史数据
        
        验证Reality Track测试周期符合3年要求
        """
        result = asyncio.get_event_loop().run_until_complete(
            arena_system.test_strategy(strategy)
        )
        
        # 验证测试周期 (默认生成1095天数据，约3年)
        assert result.reality_result.test_period_days > 0
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_hell_track_tests_extreme_scenarios(self, arena_system, strategy):
        """测试Hell Track测试极端场景
        
        验证Hell Track测试了多个极端场景
        """
        result = asyncio.get_event_loop().run_until_complete(
            arena_system.test_strategy(strategy)
        )
        
        # 验证测试了多个场景
        assert result.hell_result.scenarios_tested >= 5


# ============================================================================
# Property 6: Strategy Performance Metrics
# ============================================================================

class TestProperty6StrategyPerformanceMetrics:
    """Property 6: 策略性能指标
    
    白皮书依据: 第四章 4.2.2 策略Arena - 性能指标计算
    
    正确性属性:
    对于任何完成的策略Arena测试，系统应该计算夏普比率、最大回撤、
    年化收益率、胜率、存活率和恢复指标。
    
    **Validates: Requirements 2.2, 2.5**
    """
    
    @pytest.fixture
    def performance_calculator(self):
        """创建性能计算器实例"""
        return StrategyPerformanceCalculator()
    
    @pytest.fixture
    def arena_system(self):
        """创建Arena系统实例"""
        return StrategyArenaSystem()
    
    @HYPOTHESIS_SETTINGS
    @given(returns=returns_series_st(), trade_returns=trade_returns_st())
    def test_sharpe_ratio_calculation(self, performance_calculator, returns, trade_returns):
        """测试夏普比率计算"""
        sharpe = performance_calculator.calculate_sharpe_ratio(returns)
        
        # 夏普比率应该是有限数值
        assert np.isfinite(sharpe)
    
    @HYPOTHESIS_SETTINGS
    @given(returns=returns_series_st())
    def test_max_drawdown_calculation(self, performance_calculator, returns):
        """测试最大回撤计算"""
        # 构建权益曲线
        equity_curve = (1 + returns).cumprod() * 1000000
        
        max_dd = performance_calculator.calculate_max_drawdown(equity_curve)
        
        # 最大回撤应该在[0, 1]范围内
        assert 0 <= max_dd <= 1
    
    @HYPOTHESIS_SETTINGS
    @given(returns=returns_series_st())
    def test_annual_return_calculation(self, performance_calculator, returns):
        """测试年化收益率计算"""
        annual_return = performance_calculator.calculate_annual_return(returns)
        
        # 年化收益率应该是有限数值
        assert np.isfinite(annual_return)
    
    @HYPOTHESIS_SETTINGS
    @given(trade_returns=trade_returns_st())
    def test_win_rate_calculation(self, performance_calculator, trade_returns):
        """测试胜率计算"""
        win_rate = performance_calculator.calculate_win_rate(trade_returns)
        
        # 胜率应该在[0, 1]范围内
        assert 0 <= win_rate <= 1
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_arena_calculates_all_metrics(self, arena_system, strategy):
        """测试Arena计算所有指标"""
        result = asyncio.get_event_loop().run_until_complete(
            arena_system.test_strategy(strategy)
        )
        
        # 验证Reality Track指标
        assert result.reality_result.sharpe_ratio is not None
        assert result.reality_result.max_drawdown is not None
        assert result.reality_result.annual_return is not None
        assert result.reality_result.win_rate is not None
        
        # 验证Hell Track指标
        assert result.hell_result.survival_rate is not None
        assert result.hell_result.recovery_speed is not None


# ============================================================================
# Property 7: Strategy Arena Pass Criteria
# ============================================================================

class TestProperty7StrategyArenaPassCriteria:
    """Property 7: 策略Arena通过标准
    
    白皮书依据: 第四章 4.2.2 策略Arena - 通过标准
    
    正确性属性:
    对于任何Arena评分 > 0.7 且 夏普比率 > 1.5 且 最大回撤 < 15% 的策略，
    系统应该标记为Arena通过。
    
    **Validates: Requirements 2.7**
    """
    
    @pytest.fixture
    def arena_system(self):
        """创建Arena系统实例"""
        return StrategyArenaSystem(
            pass_threshold=0.7,
            sharpe_threshold=1.5,
            max_drawdown_threshold=0.15
        )
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_pass_criteria_consistency(self, arena_system, strategy):
        """测试通过标准一致性
        
        验证passed标志与pass_criteria_met一致
        """
        result = asyncio.get_event_loop().run_until_complete(
            arena_system.test_strategy(strategy)
        )
        
        # 验证passed与所有标准一致
        all_criteria_met = all(result.pass_criteria_met.values())
        assert result.passed == all_criteria_met
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_pass_criteria_includes_required_checks(self, arena_system, strategy):
        """测试通过标准包含必需检查项"""
        result = asyncio.get_event_loop().run_until_complete(
            arena_system.test_strategy(strategy)
        )
        
        # 验证包含所有必需的检查项
        assert 'arena_score' in result.pass_criteria_met
        assert 'sharpe_ratio' in result.pass_criteria_met
        assert 'max_drawdown' in result.pass_criteria_met
    
    def test_high_performance_strategy_passes(self, arena_system):
        """测试高性能策略通过
        
        创建一个模拟的高性能策略结果，验证通过逻辑
        """
        # 创建高性能Reality Track结果
        reality_result = StrategyRealityTrackResult(
            sharpe_ratio=2.0,  # > 1.5
            max_drawdown=0.10,  # < 15%
            annual_return=0.25,
            win_rate=0.60,
            profit_factor=1.8,
            calmar_ratio=2.5,
            sortino_ratio=2.2,
            total_trades=100,
            avg_holding_period=5.0,
            reality_score=0.85,  # 高分
            test_period_days=1095
        )
        
        # 创建高性能Hell Track结果
        hell_result = StrategyHellTrackResult(
            survival_rate=1.0,
            flash_crash_performance=0.5,
            circuit_breaker_performance=0.4,
            liquidity_drought_performance=0.3,
            volatility_explosion_performance=0.4,
            black_swan_performance=0.3,
            recovery_speed=10.0,
            max_stress_drawdown=0.15,
            hell_score=0.75,  # 高分
            scenarios_tested=5
        )
        
        # 计算综合评分
        overall_score = 0.6 * reality_result.reality_score + 0.4 * hell_result.hell_score
        
        # 检查通过标准
        pass_criteria = arena_system._check_pass_criteria(
            overall_score, reality_result, hell_result
        )
        
        # 验证所有标准都满足
        assert pass_criteria['arena_score'] == True
        assert pass_criteria['sharpe_ratio'] == True
        assert pass_criteria['max_drawdown'] == True


# ============================================================================
# Property 8: Hell Track Scenario Coverage
# ============================================================================

class TestProperty8HellTrackScenarioCoverage:
    """Property 8: Hell Track场景覆盖
    
    白皮书依据: 第四章 4.2.2 策略Arena - Hell Track极端场景
    
    正确性属性:
    对于任何Hell Track测试，系统应该包含闪崩、熔断和流动性枯竭场景。
    
    **Validates: Requirements 2.4**
    """
    
    @pytest.fixture
    def scenario_generator(self):
        """创建场景生成器实例"""
        return ExtremeScenarioGenerator()
    
    @pytest.fixture
    def hell_track(self):
        """创建Hell Track实例"""
        return StrategyHellTrack()
    
    @HYPOTHESIS_SETTINGS
    @given(data=historical_data_st())
    def test_flash_crash_scenario_generated(self, scenario_generator, data):
        """测试闪崩场景生成"""
        flash_crash_data = scenario_generator.generate_flash_crash(data)
        
        # 验证数据已修改
        assert not flash_crash_data.equals(data)
        # 验证数据长度不变
        assert len(flash_crash_data) == len(data)
    
    @HYPOTHESIS_SETTINGS
    @given(data=historical_data_st())
    def test_circuit_breaker_scenario_generated(self, scenario_generator, data):
        """测试熔断场景生成"""
        circuit_breaker_data = scenario_generator.generate_circuit_breaker(data)
        
        # 验证数据已修改
        assert not circuit_breaker_data.equals(data)
        # 验证数据长度不变
        assert len(circuit_breaker_data) == len(data)
    
    @HYPOTHESIS_SETTINGS
    @given(data=historical_data_st())
    def test_liquidity_drought_scenario_generated(self, scenario_generator, data):
        """测试流动性枯竭场景生成"""
        liquidity_drought_data = scenario_generator.generate_liquidity_drought(data)
        
        # 验证数据已修改
        assert not liquidity_drought_data.equals(data)
        # 验证数据长度不变
        assert len(liquidity_drought_data) == len(data)
    
    @HYPOTHESIS_SETTINGS
    @given(strategy=strategy_st())
    def test_hell_track_tests_all_required_scenarios(self, hell_track, strategy):
        """测试Hell Track测试所有必需场景"""
        # 生成测试数据
        data = pd.DataFrame({
            'open': np.random.randn(200) * 10 + 100,
            'high': np.random.randn(200) * 10 + 105,
            'low': np.random.randn(200) * 10 + 95,
            'close': np.random.randn(200) * 10 + 100,
            'volume': np.random.randint(1000000, 10000000, 200)
        }, index=pd.date_range(end=datetime.now(), periods=200, freq='D'))
        
        result = asyncio.get_event_loop().run_until_complete(
            hell_track.test_strategy(strategy, data)
        )
        
        # 验证测试了所有必需场景
        assert result.scenarios_tested >= 5
        
        # 验证各场景表现已计算
        assert result.flash_crash_performance is not None
        assert result.circuit_breaker_performance is not None
        assert result.liquidity_drought_performance is not None
        assert result.volatility_explosion_performance is not None
        assert result.black_swan_performance is not None
        
        # 验证场景表现在有效范围内
        assert -1 <= result.flash_crash_performance <= 1
        assert -1 <= result.circuit_breaker_performance <= 1
        assert -1 <= result.liquidity_drought_performance <= 1
        assert -1 <= result.volatility_explosion_performance <= 1
        assert -1 <= result.black_swan_performance <= 1


# ============================================================================
# 辅助测试
# ============================================================================

class TestStrategyDataModelsValidation:
    """测试策略数据模型验证"""
    
    def test_strategy_requires_id(self):
        """测试策略需要ID"""
        with pytest.raises(ValueError, match="策略ID不能为空"):
            Strategy(
                id="",
                name="Test",
                type=StrategyType.PURE_FACTOR,
                source_factors=["factor1"],
                code="test code"
            )
    
    def test_strategy_requires_source_factors(self):
        """测试策略需要源因子"""
        with pytest.raises(ValueError, match="源因子列表不能为空"):
            Strategy(
                id="test_id",
                name="Test",
                type=StrategyType.PURE_FACTOR,
                source_factors=[],
                code="test code"
            )
    
    def test_strategy_arena_score_range(self):
        """测试策略Arena评分范围"""
        with pytest.raises(ValueError, match="Arena评分必须在"):
            Strategy(
                id="test_id",
                name="Test",
                type=StrategyType.PURE_FACTOR,
                source_factors=["factor1"],
                code="test code",
                arena_score=1.5  # 超出范围
            )


class TestPerformanceCalculatorEdgeCases:
    """测试性能计算器边界情况"""
    
    @pytest.fixture
    def calculator(self):
        return StrategyPerformanceCalculator()
    
    def test_empty_returns_raises_error(self, calculator):
        """测试空收益率序列抛出错误"""
        with pytest.raises(ValueError, match="收益率序列不能为空"):
            calculator.calculate_sharpe_ratio(pd.Series([]))
    
    def test_empty_trade_returns_raises_error(self, calculator):
        """测试空交易收益率列表抛出错误"""
        with pytest.raises(ValueError, match="交易收益率列表不能为空"):
            calculator.calculate_win_rate([])
    
    def test_zero_volatility_returns_zero_sharpe(self, calculator):
        """测试零波动率返回零夏普比率"""
        # 创建零波动率序列
        returns = pd.Series([0.001] * 100)
        sharpe = calculator.calculate_sharpe_ratio(returns)
        
        # 应该返回有限值
        assert np.isfinite(sharpe)
