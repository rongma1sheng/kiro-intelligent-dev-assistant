"""
极限压力测试分析器

白皮书依据: 第四章 4.3.1 斯巴达Arena - 压力测试标准

功能:
- 崩盘场景测试 (Crash Scenario)
- 熊市场景测试 (Bear Market Scenario)
- 流动性危机测试 (Liquidity Crisis Scenario)
- 黑天鹅事件测试 (Black Swan Scenario)
- 相关性失效测试 (Correlation Breakdown Scenario)

作者: MIA Team
日期: 2026-01-20
版本: v1.0.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """压力测试场景类型"""

    CRASH = "crash"  # 崩盘场景
    BEAR_MARKET = "bear_market"  # 熊市场景
    LIQUIDITY_CRISIS = "liquidity_crisis"  # 流动性危机
    BLACK_SWAN = "black_swan"  # 黑天鹅事件
    CORRELATION_BREAKDOWN = "correlation_breakdown"  # 相关性失效


@dataclass
class ScenarioResult:
    """单个场景测试结果"""

    scenario_type: ScenarioType
    passed: bool
    score: float  # 0-1之间

    # 详细指标
    survival_rate: Optional[float] = None  # 存活率
    max_loss: Optional[float] = None  # 最大亏损
    recovery_days: Optional[int] = None  # 恢复天数
    adaptation_score: Optional[float] = None  # 适应能力评分

    # 详细数据
    daily_returns: List[float] = field(default_factory=list)
    portfolio_values: List[float] = field(default_factory=list)
    drawdowns: List[float] = field(default_factory=list)

    # 失败原因
    failure_reason: Optional[str] = None

    # 元数据
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: int = 0


@dataclass
class StressTestResult:
    """压力测试综合结果"""

    scenario_results: Dict[str, ScenarioResult]
    overall_score: float
    passed: bool

    # 统计信息
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    total_scenarios: int = 5

    # 失败场景列表
    failed_scenarios: List[str] = field(default_factory=list)

    # 测试时间
    test_date: datetime = field(default_factory=datetime.now)


class StressTestAnalyzer:
    """极限压力测试分析器

    白皮书依据: 第四章 4.3.1 斯巴达Arena - 压力测试标准

    执行5种极限场景测试:
    1. 崩盘场景 - 存活率≥80%
    2. 熊市场景 - 最大亏损≤20%
    3. 流动性危机 - 存活率≥70%
    4. 黑天鹅事件 - 恢复天数≤30天
    5. 相关性失效 - 处理能力≥60%
    """

    # 压力测试标准 (白皮书定义)
    STRESS_TEST_STANDARDS = {
        "crash_survival_rate": 0.8,  # 崩盘存活率80%
        "bear_market_max_loss": 0.20,  # 熊市最大亏损20%
        "liquidity_crisis_survival": 0.7,  # 流动性危机存活率70%
        "black_swan_recovery_days": 30,  # 黑天鹅恢复天数≤30天
        "correlation_breakdown_handling": 0.6,  # 相关性失效处理能力60%
    }

    # 历史极端事件日期 (A股市场)
    HISTORICAL_CRASHES = {
        "2015_stock_crash": ("2015-06-15", "2015-08-26"),  # 2015年股灾
        "2020_covid_crash": ("2020-02-03", "2020-03-23"),  # 2020年疫情暴跌
        "2018_trade_war": ("2018-01-29", "2018-10-19"),  # 2018年贸易战
    }

    BEAR_MARKET_PERIODS = {
        "2018_bear": ("2018-01-29", "2018-12-28"),  # 2018年熊市
        "2021_2022_bear": ("2021-02-18", "2022-04-27"),  # 2021-2022年熊市
    }

    def __init__(self, market_type: str = "A_STOCK"):
        """初始化压力测试分析器

        Args:
            market_type: 市场类型 ('A_STOCK', 'FUTURES', 'CRYPTO')
        """
        self.market_type = market_type
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"初始化StressTestAnalyzer: market_type={market_type}"
        )  # pylint: disable=logging-fstring-interpolation

    async def run_crash_scenario(self, strategy_returns: pd.Series, market_returns: pd.Series) -> ScenarioResult:
        """崩盘场景测试

        白皮书依据: 第四章 4.3.1 - 崩盘场景测试

        模拟2015年股灾、2020年3月暴跌等极端下跌场景

        Args:
            strategy_returns: 策略收益率序列
            market_returns: 市场收益率序列

        Returns:
            ScenarioResult: 崩盘场景测试结果
        """
        logger.info("开始崩盘场景测试")

        # 识别崩盘期间 (市场单日跌幅>5%或连续3日跌幅>10%)
        crash_periods = self._identify_crash_periods(market_returns)

        if not crash_periods:
            logger.warning("未识别到崩盘期间，使用模拟数据")
            crash_periods = self._simulate_crash_scenario()

        # 计算崩盘期间策略表现
        crash_returns = []
        crash_drawdowns = []
        portfolio_values = [1.0]  # 初始资金1.0

        for start_idx, end_idx in crash_periods:
            period_returns = strategy_returns.iloc[start_idx : end_idx + 1]

            for ret in period_returns:
                new_value = portfolio_values[-1] * (1 + ret)
                portfolio_values.append(new_value)
                crash_returns.append(ret)

                # 计算回撤
                peak = max(portfolio_values)
                drawdown = (new_value - peak) / peak
                crash_drawdowns.append(drawdown)

        # 计算存活率 (资金未归零的概率)
        min_portfolio_value = min(portfolio_values) if portfolio_values else 0
        survival_rate = min_portfolio_value / 1.0 if min_portfolio_value > 0 else 0

        # 计算最大回撤
        max_drawdown = abs(min(crash_drawdowns)) if crash_drawdowns else 0

        # 评分 (存活率权重70%, 回撤控制权重30%)
        score = survival_rate * 0.7 + max(0, 1 - max_drawdown / 0.5) * 0.3

        # 判断是否通过
        passed = survival_rate >= self.STRESS_TEST_STANDARDS["crash_survival_rate"]

        return ScenarioResult(
            scenario_type=ScenarioType.CRASH,
            passed=passed,
            score=score,
            survival_rate=survival_rate,
            max_loss=max_drawdown,
            daily_returns=crash_returns,
            portfolio_values=portfolio_values,
            drawdowns=crash_drawdowns,
            failure_reason=(
                None
                if passed
                else f"存活率{survival_rate:.2%} < 标准{self.STRESS_TEST_STANDARDS['crash_survival_rate']:.0%}"
            ),
            duration_days=len(crash_returns),
        )

    async def run_bear_market_scenario(self, strategy_returns: pd.Series, market_returns: pd.Series) -> ScenarioResult:
        """熊市场景测试

        白皮书依据: 第四章 4.3.1 - 熊市场景测试

        模拟2018年熊市、2022年下跌等持续下跌场景

        Args:
            strategy_returns: 策略收益率序列
            market_returns: 市场收益率序列

        Returns:
            ScenarioResult: 熊市场景测试结果
        """
        logger.info("开始熊市场景测试")

        # 识别熊市期间 (市场累计跌幅>20%且持续>60天)
        bear_periods = self._identify_bear_market_periods(market_returns)

        if not bear_periods:
            logger.warning("未识别到熊市期间，使用模拟数据")
            bear_periods = self._simulate_bear_market_scenario()

        # 计算熊市期间策略表现
        bear_returns = []
        portfolio_values = [1.0]
        drawdowns = []

        for start_idx, end_idx in bear_periods:
            period_returns = strategy_returns.iloc[start_idx : end_idx + 1]

            for ret in period_returns:
                new_value = portfolio_values[-1] * (1 + ret)
                portfolio_values.append(new_value)
                bear_returns.append(ret)

                peak = max(portfolio_values)
                drawdown = (new_value - peak) / peak
                drawdowns.append(drawdown)

        # 计算最大亏损
        max_loss = abs(min(drawdowns)) if drawdowns else 0

        # 计算相对市场表现 (超额收益)
        strategy_total_return = (portfolio_values[-1] - 1.0) if portfolio_values else 0

        # 评分 (亏损控制权重80%, 相对表现权重20%)
        loss_control_score = max(0, 1 - max_loss / 0.3)  # 亏损<30%得满分
        score = loss_control_score * 0.8 + min(1.0, (strategy_total_return + 0.2) / 0.2) * 0.2

        # 判断是否通过
        passed = max_loss <= self.STRESS_TEST_STANDARDS["bear_market_max_loss"]

        return ScenarioResult(
            scenario_type=ScenarioType.BEAR_MARKET,
            passed=passed,
            score=score,
            max_loss=max_loss,
            daily_returns=bear_returns,
            portfolio_values=portfolio_values,
            drawdowns=drawdowns,
            failure_reason=(
                None
                if passed
                else f"最大亏损{max_loss:.2%} > 标准{self.STRESS_TEST_STANDARDS['bear_market_max_loss']:.0%}"
            ),
            duration_days=len(bear_returns),
        )

    async def run_liquidity_crisis_scenario(
        self, strategy_returns: pd.Series, market_volume: Optional[pd.Series] = None
    ) -> ScenarioResult:
        """流动性危机场景测试

        白皮书依据: 第四章 4.3.1 - 流动性危机测试

        模拟极端流动性枯竭情况 (成交量骤降、买卖价差扩大)

        Args:
            strategy_returns: 策略收益率序列
            market_volume: 市场成交量序列 (可选)

        Returns:
            ScenarioResult: 流动性危机场景测试结果
        """
        logger.info("开始流动性危机场景测试")

        # 识别流动性危机期间 (成交量骤降>50%或连续缩量)
        if market_volume is not None:
            crisis_periods = self._identify_liquidity_crisis_periods(market_volume)
        else:
            logger.warning("未提供成交量数据，使用模拟流动性危机")
            crisis_periods = self._simulate_liquidity_crisis_scenario()

        # 模拟流动性危机对策略的影响
        # 假设: 流动性危机导致滑点扩大3-5倍，部分订单无法成交
        crisis_returns = []
        portfolio_values = [1.0]
        execution_failures = 0
        total_trades = 0

        for start_idx, end_idx in crisis_periods:
            period_returns = strategy_returns.iloc[start_idx : end_idx + 1]

            for ret in period_returns:
                total_trades += 1

                # 模拟流动性危机: 30%概率订单无法成交
                if np.random.random() < 0.3:
                    execution_failures += 1
                    adjusted_ret = 0  # 无法成交，收益为0
                else:
                    # 成交但滑点扩大 (假设滑点增加2-3%)
                    slippage_impact = np.random.uniform(0.02, 0.03)
                    adjusted_ret = ret - slippage_impact if ret > 0 else ret + slippage_impact

                new_value = portfolio_values[-1] * (1 + adjusted_ret)
                portfolio_values.append(new_value)
                crisis_returns.append(adjusted_ret)

        # 计算存活率
        min_portfolio_value = min(portfolio_values) if portfolio_values else 0
        survival_rate = min_portfolio_value / 1.0 if min_portfolio_value > 0 else 0

        # 计算订单执行成功率
        execution_success_rate = 1 - (execution_failures / total_trades) if total_trades > 0 else 0

        # 评分 (存活率权重60%, 执行成功率权重40%)
        score = survival_rate * 0.6 + execution_success_rate * 0.4

        # 判断是否通过
        passed = survival_rate >= self.STRESS_TEST_STANDARDS["liquidity_crisis_survival"]

        return ScenarioResult(
            scenario_type=ScenarioType.LIQUIDITY_CRISIS,
            passed=passed,
            score=score,
            survival_rate=survival_rate,
            adaptation_score=execution_success_rate,
            daily_returns=crisis_returns,
            portfolio_values=portfolio_values,
            failure_reason=(
                None
                if passed
                else f"存活率{survival_rate:.2%} < 标准{self.STRESS_TEST_STANDARDS['liquidity_crisis_survival']:.0%}"
            ),
            duration_days=len(crisis_returns),
        )

    async def run_black_swan_scenario(self, strategy_returns: pd.Series) -> ScenarioResult:
        """黑天鹅事件场景测试

        白皮书依据: 第四章 4.3.1 - 黑天鹅事件测试

        模拟突发重大事件冲击 (如疫情、战争、政策突变等)

        Args:
            strategy_returns: 策略收益率序列

        Returns:
            ScenarioResult: 黑天鹅事件场景测试结果
        """
        logger.info("开始黑天鹅事件场景测试")

        # 模拟黑天鹅事件: 突然单日暴跌10-15%，然后逐步恢复
        black_swan_returns = []
        portfolio_values = [1.0]

        # 第1天: 黑天鹅事件爆发，暴跌
        swan_impact = -np.random.uniform(0.10, 0.15)  # -10%到-15%
        strategy_ret_day1 = strategy_returns.iloc[0] if len(strategy_returns) > 0 else 0
        adjusted_ret_day1 = strategy_ret_day1 + swan_impact

        portfolio_values.append(portfolio_values[-1] * (1 + adjusted_ret_day1))
        black_swan_returns.append(adjusted_ret_day1)

        # 记录最低点
        min_value = portfolio_values[-1]
        recovery_day = None

        # 后续30天: 观察恢复情况
        for day in range(1, min(30, len(strategy_returns))):
            strategy_ret = strategy_returns.iloc[day]

            # 模拟市场逐步恢复，但波动加大
            volatility_multiplier = max(1.0, 2.0 - day / 30)  # 波动率逐步降低
            adjusted_ret = strategy_ret * volatility_multiplier

            new_value = portfolio_values[-1] * (1 + adjusted_ret)
            portfolio_values.append(new_value)
            black_swan_returns.append(adjusted_ret)

            # 检查是否恢复到初始水平
            if new_value >= 1.0 and recovery_day is None:
                recovery_day = day

        # 如果30天内未恢复，记录为30天
        if recovery_day is None:
            recovery_day = 30

        # 计算最大回撤
        max_drawdown = abs((min_value - 1.0) / 1.0)

        # 评分 (恢复速度权重70%, 回撤控制权重30%)
        recovery_score = max(0, 1 - recovery_day / 60)  # 恢复越快分数越高
        drawdown_score = max(0, 1 - max_drawdown / 0.3)
        score = recovery_score * 0.7 + drawdown_score * 0.3

        # 判断是否通过
        passed = recovery_day <= self.STRESS_TEST_STANDARDS["black_swan_recovery_days"]

        return ScenarioResult(
            scenario_type=ScenarioType.BLACK_SWAN,
            passed=passed,
            score=score,
            recovery_days=recovery_day,
            max_loss=max_drawdown,
            daily_returns=black_swan_returns,
            portfolio_values=portfolio_values,
            failure_reason=(
                None
                if passed
                else f"恢复天数{recovery_day}天 > 标准{self.STRESS_TEST_STANDARDS['black_swan_recovery_days']}天"
            ),
            duration_days=len(black_swan_returns),
        )

    async def run_correlation_breakdown_scenario(
        self, strategy_returns: pd.Series, market_returns: pd.Series
    ) -> ScenarioResult:
        """相关性失效场景测试

        白皮书依据: 第四章 4.3.1 - 相关性失效测试

        模拟市场相关性结构突变 (如风格切换、板块轮动加速等)

        Args:
            strategy_returns: 策略收益率序列
            market_returns: 市场收益率序列

        Returns:
            ScenarioResult: 相关性失效场景测试结果
        """
        logger.info("开始相关性失效场景测试")

        # 计算策略与市场的历史相关性
        historical_corr = strategy_returns.corr(market_returns)

        # 模拟相关性突变: 相关性降低50-80%
        correlation_breakdown_returns = []
        portfolio_values = [1.0]
        adaptation_scores = []

        # 分析策略在相关性失效期间的适应能力
        window_size = 20  # 20天滚动窗口

        for i in range(len(strategy_returns) - window_size):
            window_strategy = strategy_returns.iloc[i : i + window_size]
            window_market = market_returns.iloc[i : i + window_size]

            # 计算当前窗口相关性
            current_corr = window_strategy.corr(window_market)

            # 检测相关性是否失效 (相关性变化>50%)
            corr_change = abs(current_corr - historical_corr) / (abs(historical_corr) + 0.01)

            if corr_change > 0.5:  # 相关性失效
                # 模拟策略在相关性失效期间的表现
                # 假设: 相关性失效导致策略收益波动加大
                for j in range(window_size):
                    if i + j < len(strategy_returns):
                        ret = strategy_returns.iloc[i + j]

                        # 相关性失效导致收益不确定性增加
                        uncertainty_factor = 1 + corr_change * 0.5
                        adjusted_ret = ret * np.random.uniform(0.5, 1.5) * uncertainty_factor

                        new_value = portfolio_values[-1] * (1 + adjusted_ret)
                        portfolio_values.append(new_value)
                        correlation_breakdown_returns.append(adjusted_ret)

                        # 评估适应能力 (收益稳定性)
                        if len(correlation_breakdown_returns) >= 5:
                            recent_volatility = np.std(correlation_breakdown_returns[-5:])
                            adaptation_score = max(0, 1 - recent_volatility / 0.1)
                            adaptation_scores.append(adaptation_score)

        # 如果没有检测到相关性失效，使用模拟数据
        if not correlation_breakdown_returns:
            logger.warning("未检测到相关性失效，使用模拟数据")
            correlation_breakdown_returns, portfolio_values, adaptation_scores = (
                self._simulate_correlation_breakdown_scenario(strategy_returns)
            )

        # 计算平均适应能力评分
        avg_adaptation_score = np.mean(adaptation_scores) if adaptation_scores else 0.5

        # 计算最大回撤
        peak = max(portfolio_values)
        min_value = min(portfolio_values)
        max_drawdown = abs((min_value - peak) / peak) if peak > 0 else 0

        # 评分 (适应能力权重70%, 回撤控制权重30%)
        score = avg_adaptation_score * 0.7 + max(0, 1 - max_drawdown / 0.2) * 0.3

        # 判断是否通过
        passed = avg_adaptation_score >= self.STRESS_TEST_STANDARDS["correlation_breakdown_handling"]

        return ScenarioResult(
            scenario_type=ScenarioType.CORRELATION_BREAKDOWN,
            passed=passed,
            score=score,
            adaptation_score=avg_adaptation_score,
            max_loss=max_drawdown,
            daily_returns=correlation_breakdown_returns,
            portfolio_values=portfolio_values,
            failure_reason=(
                None
                if passed
                else f"适应能力{avg_adaptation_score:.2%} < 标准{self.STRESS_TEST_STANDARDS['correlation_breakdown_handling']:.0%}"  # pylint: disable=line-too-long
            ),
            duration_days=len(correlation_breakdown_returns),
        )

    async def run_all_scenarios(
        self, strategy_returns: pd.Series, market_returns: pd.Series, market_volume: Optional[pd.Series] = None
    ) -> StressTestResult:
        """运行所有压力测试场景

        白皮书依据: 第四章 4.3.1 - 压力测试综合评估

        Args:
            strategy_returns: 策略收益率序列
            market_returns: 市场收益率序列
            market_volume: 市场成交量序列 (可选)

        Returns:
            StressTestResult: 压力测试综合结果
        """
        logger.info("开始运行所有压力测试场景")

        # 运行5种场景测试
        crash_result = await self.run_crash_scenario(strategy_returns, market_returns)
        bear_result = await self.run_bear_market_scenario(strategy_returns, market_returns)
        liquidity_result = await self.run_liquidity_crisis_scenario(strategy_returns, market_volume)
        black_swan_result = await self.run_black_swan_scenario(strategy_returns)
        correlation_result = await self.run_correlation_breakdown_scenario(strategy_returns, market_returns)

        # 汇总结果
        scenario_results = {
            "crash": crash_result,
            "bear_market": bear_result,
            "liquidity_crisis": liquidity_result,
            "black_swan": black_swan_result,
            "correlation_breakdown": correlation_result,
        }

        # 计算综合评分
        overall_score = (
            crash_result.score * 0.25  # 崩盘场景权重25%
            + bear_result.score * 0.20  # 熊市场景权重20%
            + liquidity_result.score * 0.20  # 流动性危机权重20%
            + black_swan_result.score * 0.20  # 黑天鹅事件权重20%
            + correlation_result.score * 0.15  # 相关性失效权重15%
        )

        # 统计通过情况
        scenarios_passed = sum(1 for result in scenario_results.values() if result.passed)
        scenarios_failed = 5 - scenarios_passed
        failed_scenarios = [name for name, result in scenario_results.items() if not result.passed]

        # 判断整体是否通过 (至少4个场景通过 且 综合评分≥0.7)
        passed = scenarios_passed >= 4 and overall_score >= 0.7

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"压力测试完成: 通过{scenarios_passed}/5个场景, "
            f"综合评分{overall_score:.2%}, "
            f"整体{'通过' if passed else '未通过'}"
        )

        return StressTestResult(
            scenario_results=scenario_results,
            overall_score=overall_score,
            passed=passed,
            scenarios_passed=scenarios_passed,
            scenarios_failed=scenarios_failed,
            failed_scenarios=failed_scenarios,
        )

    # ==================== 辅助方法 ====================

    def _identify_crash_periods(self, market_returns: pd.Series) -> List[Tuple[int, int]]:
        """识别崩盘期间

        崩盘定义: 市场单日跌幅>5% 或 连续3日跌幅>10%
        """
        crash_periods = []

        for i in range(len(market_returns)):
            # 单日暴跌
            if market_returns.iloc[i] < -0.05:
                crash_periods.append((i, min(i + 10, len(market_returns) - 1)))

            # 连续下跌
            if i >= 2:
                three_day_return = (1 + market_returns.iloc[i - 2]) * (1 + market_returns.iloc[i - 1]) * (
                    1 + market_returns.iloc[i]
                ) - 1
                if three_day_return < -0.10:
                    crash_periods.append((i - 2, min(i + 10, len(market_returns) - 1)))

        # 合并重叠期间
        return self._merge_periods(crash_periods)

    def _identify_bear_market_periods(self, market_returns: pd.Series) -> List[Tuple[int, int]]:
        """识别熊市期间

        熊市定义: 市场累计跌幅>20% 且 持续>60天
        """
        bear_periods = []
        window_size = 60

        for i in range(len(market_returns) - window_size):
            window_returns = market_returns.iloc[i : i + window_size]
            cumulative_return = (1 + window_returns).prod() - 1

            if cumulative_return < -0.20:
                bear_periods.append((i, i + window_size))

        return self._merge_periods(bear_periods)

    def _identify_liquidity_crisis_periods(self, market_volume: pd.Series) -> List[Tuple[int, int]]:
        """识别流动性危机期间

        流动性危机定义: 成交量骤降>50% 或 连续缩量
        """
        crisis_periods = []
        avg_volume = market_volume.rolling(window=20).mean()

        for i in range(20, len(market_volume)):
            volume_drop = (market_volume.iloc[i] - avg_volume.iloc[i]) / avg_volume.iloc[i]

            if volume_drop < -0.50:
                crisis_periods.append((i, min(i + 10, len(market_volume) - 1)))

        return self._merge_periods(crisis_periods)

    def _merge_periods(self, periods: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """合并重叠的时间段"""
        if not periods:
            return []

        sorted_periods = sorted(periods, key=lambda x: x[0])
        merged = [sorted_periods[0]]

        for current in sorted_periods[1:]:
            last = merged[-1]
            if current[0] <= last[1]:
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)

        return merged

    def _simulate_crash_scenario(self) -> List[Tuple[int, int]]:
        """模拟崩盘场景 (当没有历史数据时)"""
        # 模拟3个崩盘期间，每个持续5-10天
        return [(0, 7), (50, 58), (120, 130)]

    def _simulate_bear_market_scenario(self) -> List[Tuple[int, int]]:
        """模拟熊市场景 (当没有历史数据时)"""
        # 模拟2个熊市期间，每个持续60-90天
        return [(0, 75), (150, 240)]

    def _simulate_liquidity_crisis_scenario(self) -> List[Tuple[int, int]]:
        """模拟流动性危机场景 (当没有历史数据时)"""
        # 模拟3个流动性危机期间，每个持续3-7天
        return [(10, 15), (80, 86), (180, 185)]

    def _simulate_correlation_breakdown_scenario(
        self, strategy_returns: pd.Series
    ) -> Tuple[List[float], List[float], List[float]]:
        """模拟相关性失效场景 (当没有检测到相关性失效时)"""
        returns = []
        portfolio_values = [1.0]
        adaptation_scores = []

        # 模拟30天的相关性失效期间
        for i in range(min(30, len(strategy_returns))):
            ret = strategy_returns.iloc[i] if i < len(strategy_returns) else 0

            # 模拟相关性失效: 收益波动加大
            adjusted_ret = ret * np.random.uniform(0.5, 1.8)

            new_value = portfolio_values[-1] * (1 + adjusted_ret)
            portfolio_values.append(new_value)
            returns.append(adjusted_ret)

            # 计算适应能力
            if len(returns) >= 5:
                recent_volatility = np.std(returns[-5:])
                adaptation_score = max(0, 1 - recent_volatility / 0.1)
                adaptation_scores.append(adaptation_score)

        return returns, portfolio_values, adaptation_scores
