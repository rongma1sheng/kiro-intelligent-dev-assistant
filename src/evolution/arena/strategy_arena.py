"""
策略Arena系统 (Strategy Arena System)

白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.strategy_data_models import (
    Strategy,
    StrategyHellTrackResult,
    StrategyRealityTrackResult,
    StrategyTestResult,
)
from src.evolution.arena.strategy_hell_track import StrategyHellTrack
from src.evolution.arena.strategy_performance_calculator import StrategyPerformanceCalculator
from src.evolution.arena.strategy_reality_track import StrategyRealityTrack


class StrategyArenaSystem:
    """策略Arena系统

    白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统

    策略Arena是策略验证的核心组件，通过Reality Track和Hell Track
    双轨测试确保策略在正常和极端市场条件下都能表现良好。

    Attributes:
        reality_track: Reality Track测试器
        hell_track: Hell Track测试器
        performance_calculator: 性能计算器
        pass_threshold: Arena通过阈值，默认0.7
        sharpe_threshold: 夏普比率阈值，默认1.5
        max_drawdown_threshold: 最大回撤阈值，默认0.15 (15%)
        max_test_duration: 最大测试时长(秒)，默认60秒
    """

    # Arena通过标准
    DEFAULT_PASS_THRESHOLD = 0.7
    DEFAULT_SHARPE_THRESHOLD = 1.5
    DEFAULT_MAX_DRAWDOWN_THRESHOLD = 0.15
    DEFAULT_MAX_TEST_DURATION = 60.0

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        reality_track: Optional[StrategyRealityTrack] = None,
        hell_track: Optional[StrategyHellTrack] = None,
        performance_calculator: Optional[StrategyPerformanceCalculator] = None,
        pass_threshold: float = DEFAULT_PASS_THRESHOLD,
        sharpe_threshold: float = DEFAULT_SHARPE_THRESHOLD,
        max_drawdown_threshold: float = DEFAULT_MAX_DRAWDOWN_THRESHOLD,
        max_test_duration: float = DEFAULT_MAX_TEST_DURATION,
    ):
        """初始化策略Arena系统

        Args:
            reality_track: Reality Track测试器，None则创建默认实例
            hell_track: Hell Track测试器，None则创建默认实例
            performance_calculator: 性能计算器，None则创建默认实例
            pass_threshold: Arena通过阈值，范围 [0, 1]
            sharpe_threshold: 夏普比率阈值，必须 > 0
            max_drawdown_threshold: 最大回撤阈值，范围 [0, 1]
            max_test_duration: 最大测试时长(秒)，必须 > 0

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not 0 <= pass_threshold <= 1:
            raise ValueError(f"通过阈值必须在[0, 1]范围内，当前值: {pass_threshold}")
        if sharpe_threshold <= 0:
            raise ValueError(f"夏普比率阈值必须大于0，当前值: {sharpe_threshold}")
        if not 0 <= max_drawdown_threshold <= 1:
            raise ValueError(f"最大回撤阈值必须在[0, 1]范围内，当前值: {max_drawdown_threshold}")
        if max_test_duration <= 0:
            raise ValueError(f"最大测试时长必须大于0，当前值: {max_test_duration}")

        self.performance_calculator = performance_calculator or StrategyPerformanceCalculator()
        self.reality_track = reality_track or StrategyRealityTrack(performance_calculator=self.performance_calculator)
        self.hell_track = hell_track or StrategyHellTrack()

        self.pass_threshold = pass_threshold
        self.sharpe_threshold = sharpe_threshold
        self.max_drawdown_threshold = max_drawdown_threshold
        self.max_test_duration = max_test_duration

        logger.info(
            f"初始化StrategyArenaSystem: "
            f"pass_threshold={pass_threshold}, "
            f"sharpe_threshold={sharpe_threshold}, "
            f"max_drawdown_threshold={max_drawdown_threshold:.2%}, "
            f"max_test_duration={max_test_duration}s"
        )

    async def test_strategy(
        self, strategy: Strategy, historical_data: Optional[pd.DataFrame] = None
    ) -> StrategyTestResult:
        """测试策略

        白皮书依据: 第四章 4.2.2 - 策略Arena双轨测试

        执行Reality Track和Hell Track双轨测试，计算综合评分并判断是否通过。

        Args:
            strategy: 待测试策略
            historical_data: 历史数据，None则生成模拟数据

        Returns:
            策略测试结果

        Raises:
            ValueError: 当策略无效时
            TimeoutError: 当测试超时时
        """
        if not strategy.id:
            raise ValueError("策略ID不能为空")

        logger.info(f"开始策略Arena测试: strategy_id={strategy.id}, name={strategy.name}")

        start_time = time.time()

        try:
            # 生成或使用历史数据
            if historical_data is None:
                historical_data = self._generate_mock_data()

            # 并行执行双轨测试
            reality_result, hell_result = await asyncio.gather(
                self.reality_track.test_strategy(strategy, historical_data),
                self.hell_track.test_strategy(strategy, historical_data),
            )

            # 计算综合评分
            overall_score = self._calculate_overall_score(reality_result, hell_result)

            # 检查通过标准
            pass_criteria_met = self._check_pass_criteria(overall_score, reality_result, hell_result)

            # 判断是否通过
            passed = all(pass_criteria_met.values())

            # 计算测试耗时
            test_duration = time.time() - start_time

            # 检查是否超时
            if test_duration > self.max_test_duration:
                logger.warning(f"策略Arena测试超时: {test_duration:.2f}s > {self.max_test_duration}s")

            # 构建详细指标
            detailed_metrics = self._build_detailed_metrics(reality_result, hell_result, overall_score)

            # 构建结果对象
            result = StrategyTestResult(
                strategy_id=strategy.id,
                reality_result=reality_result,
                hell_result=hell_result,
                overall_score=overall_score,
                passed=passed,
                pass_criteria_met=pass_criteria_met,
                test_timestamp=datetime.now(),
                test_duration_seconds=test_duration,
                detailed_metrics=detailed_metrics,
            )

            logger.info(
                f"策略Arena测试完成 - "
                f"strategy_id={strategy.id}, "
                f"overall_score={overall_score:.3f}, "
                f"passed={passed}, "
                f"duration={test_duration:.2f}s"
            )

            # 发布事件
            await self._publish_arena_completed_event(strategy, result)

            return result

        except Exception as e:
            logger.error(f"策略Arena测试失败: strategy_id={strategy.id}, error={e}")
            raise

    def _generate_mock_data(self, days: int = 1095) -> pd.DataFrame:
        """生成模拟历史数据

        Args:
            days: 数据天数，默认1095天(3年)

        Returns:
            模拟历史数据DataFrame
        """
        logger.debug(f"生成模拟历史数据: {days}天")

        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

        # 生成模拟价格数据
        np.random.seed(42)
        returns = np.random.randn(days) * 0.02  # 日收益率约2%波动
        prices = 100 * np.exp(np.cumsum(returns))

        # 生成成交量
        volumes = np.random.randint(1000000, 10000000, days)

        data = pd.DataFrame(
            {
                "open": prices * (1 + np.random.randn(days) * 0.005),
                "high": prices * (1 + abs(np.random.randn(days) * 0.01)),
                "low": prices * (1 - abs(np.random.randn(days) * 0.01)),
                "close": prices,
                "volume": volumes,
            },
            index=dates,
        )

        return data

    def _calculate_overall_score(
        self, reality_result: StrategyRealityTrackResult, hell_result: StrategyHellTrackResult
    ) -> float:
        """计算综合评分

        白皮书依据: 第四章 4.2.2 - Arena综合评分计算

        综合评分 = 0.6 * Reality评分 + 0.4 * Hell评分

        Args:
            reality_result: Reality Track测试结果
            hell_result: Hell Track测试结果

        Returns:
            综合评分 [0, 1]
        """
        overall_score = 0.6 * reality_result.reality_score + 0.4 * hell_result.hell_score

        # 确保在[0, 1]范围内
        overall_score = max(0.0, min(1.0, overall_score))

        return float(overall_score)

    def _check_pass_criteria(
        self,
        overall_score: float,
        reality_result: StrategyRealityTrackResult,
        hell_result: StrategyHellTrackResult,  # pylint: disable=unused-argument
    ) -> Dict[str, bool]:
        """检查通过标准

        白皮书依据: 第四章 4.2.2 - Arena通过标准

        通过标准:
        1. Arena综合评分 > 0.7
        2. 夏普比率 > 1.5
        3. 最大回撤 < 15%

        Args:
            overall_score: 综合评分
            reality_result: Reality Track测试结果
            hell_result: Hell Track测试结果

        Returns:
            各项标准是否满足的字典
        """
        return {
            "arena_score": overall_score > self.pass_threshold,
            "sharpe_ratio": reality_result.sharpe_ratio > self.sharpe_threshold,
            "max_drawdown": reality_result.max_drawdown < self.max_drawdown_threshold,
        }

    def _build_detailed_metrics(
        self, reality_result: StrategyRealityTrackResult, hell_result: StrategyHellTrackResult, overall_score: float
    ) -> Dict[str, Any]:
        """构建详细指标

        Args:
            reality_result: Reality Track测试结果
            hell_result: Hell Track测试结果
            overall_score: 综合评分

        Returns:
            详细指标字典
        """
        return {
            "overall_score": overall_score,
            "reality_track": {
                "score": reality_result.reality_score,
                "sharpe_ratio": reality_result.sharpe_ratio,
                "sortino_ratio": reality_result.sortino_ratio,
                "calmar_ratio": reality_result.calmar_ratio,
                "max_drawdown": reality_result.max_drawdown,
                "annual_return": reality_result.annual_return,
                "win_rate": reality_result.win_rate,
                "profit_factor": reality_result.profit_factor,
                "total_trades": reality_result.total_trades,
                "avg_holding_period": reality_result.avg_holding_period,
                "test_period_days": reality_result.test_period_days,
            },
            "hell_track": {
                "score": hell_result.hell_score,
                "survival_rate": hell_result.survival_rate,
                "flash_crash_performance": hell_result.flash_crash_performance,
                "circuit_breaker_performance": hell_result.circuit_breaker_performance,
                "liquidity_drought_performance": hell_result.liquidity_drought_performance,
                "volatility_explosion_performance": hell_result.volatility_explosion_performance,
                "black_swan_performance": hell_result.black_swan_performance,
                "recovery_speed": hell_result.recovery_speed,
                "max_stress_drawdown": hell_result.max_stress_drawdown,
                "scenarios_tested": hell_result.scenarios_tested,
            },
            "pass_thresholds": {
                "arena_score": self.pass_threshold,
                "sharpe_ratio": self.sharpe_threshold,
                "max_drawdown": self.max_drawdown_threshold,
            },
        }

    async def _publish_arena_completed_event(self, strategy: Strategy, result: StrategyTestResult) -> None:
        """发布Arena测试完成事件

        白皮书依据: 第四章 4.2.2 - 事件驱动通信

        Args:
            strategy: 测试的策略
            result: 测试结果
        """
        try:
            from src.infra.event_bus import EventBus, EventType  # pylint: disable=import-outside-toplevel

            event_bus = EventBus()
            await event_bus.publish(  # pylint: disable=e1121
                EventType.STRATEGY_ARENA_COMPLETED,
                {
                    "strategy_id": strategy.id,
                    "strategy_name": strategy.name,
                    "overall_score": result.overall_score,
                    "passed": result.passed,
                    "pass_criteria_met": result.pass_criteria_met,
                    "test_timestamp": result.test_timestamp.isoformat(),
                    "test_duration_seconds": result.test_duration_seconds,
                },
            )

            logger.debug(f"已发布STRATEGY_ARENA_COMPLETED事件: strategy_id={strategy.id}")

        except ImportError:
            logger.warning("EventBus不可用，跳过事件发布")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"发布Arena完成事件失败: {e}")

    async def batch_test_strategies(
        self, strategies: List[Strategy], historical_data: Optional[pd.DataFrame] = None, max_concurrent: int = 5
    ) -> List[StrategyTestResult]:
        """批量测试策略

        白皮书依据: 第四章 4.2.2 - 批量策略测试

        Args:
            strategies: 待测试策略列表
            historical_data: 历史数据，None则生成模拟数据
            max_concurrent: 最大并发数，默认5

        Returns:
            测试结果列表
        """
        if not strategies:
            return []

        logger.info(f"开始批量策略Arena测试: 策略数={len(strategies)}, 最大并发={max_concurrent}")

        # 生成或使用历史数据
        if historical_data is None:
            historical_data = self._generate_mock_data()

        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def test_with_semaphore(strategy: Strategy) -> StrategyTestResult:
            async with semaphore:
                return await self.test_strategy(strategy, historical_data)

        # 并发执行测试
        results = await asyncio.gather(*[test_with_semaphore(s) for s in strategies], return_exceptions=True)

        # 过滤异常结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"策略测试失败: strategy_id={strategies[i].id}, error={result}")
            else:
                valid_results.append(result)

        logger.info(
            f"批量策略Arena测试完成: " f"成功={len(valid_results)}, " f"失败={len(strategies) - len(valid_results)}"
        )

        return valid_results

    def generate_arena_report(self, result: StrategyTestResult) -> Dict[str, Any]:
        """生成Arena测试报告

        白皮书依据: 第四章 4.2.2 - Arena测试报告生成

        Args:
            result: 测试结果

        Returns:
            测试报告字典
        """
        report = {
            "report_type": "strategy_arena_test",
            "generated_at": datetime.now().isoformat(),
            "strategy_id": result.strategy_id,
            "test_timestamp": result.test_timestamp.isoformat(),
            "test_duration_seconds": result.test_duration_seconds,
            "summary": {
                "overall_score": result.overall_score,
                "passed": result.passed,
                "pass_criteria_met": result.pass_criteria_met,
            },
            "reality_track": {
                "score": result.reality_result.reality_score,
                "sharpe_ratio": result.reality_result.sharpe_ratio,
                "max_drawdown": result.reality_result.max_drawdown,
                "annual_return": result.reality_result.annual_return,
                "win_rate": result.reality_result.win_rate,
                "profit_factor": result.reality_result.profit_factor,
                "test_period_days": result.reality_result.test_period_days,
            },
            "hell_track": {
                "score": result.hell_result.hell_score,
                "survival_rate": result.hell_result.survival_rate,
                "scenarios_tested": result.hell_result.scenarios_tested,
                "scenario_performances": {
                    "flash_crash": result.hell_result.flash_crash_performance,
                    "circuit_breaker": result.hell_result.circuit_breaker_performance,
                    "liquidity_drought": result.hell_result.liquidity_drought_performance,
                    "volatility_explosion": result.hell_result.volatility_explosion_performance,
                    "black_swan": result.hell_result.black_swan_performance,
                },
                "recovery_speed": result.hell_result.recovery_speed,
                "max_stress_drawdown": result.hell_result.max_stress_drawdown,
            },
            "recommendations": self._generate_recommendations(result),
        }

        logger.info(f"生成Arena测试报告: strategy_id={result.strategy_id}")

        return report

    def _generate_recommendations(self, result: StrategyTestResult) -> List[str]:
        """生成改进建议

        Args:
            result: 测试结果

        Returns:
            改进建议列表
        """
        recommendations = []

        # 检查各项指标并生成建议
        if not result.pass_criteria_met.get("arena_score", True):
            recommendations.append(f"Arena综合评分({result.overall_score:.3f})未达标，" f"建议优化策略逻辑提升整体表现")

        if not result.pass_criteria_met.get("sharpe_ratio", True):
            recommendations.append(
                f"夏普比率({result.reality_result.sharpe_ratio:.2f})未达标，" f"建议优化风险调整后收益"
            )

        if not result.pass_criteria_met.get("max_drawdown", True):
            recommendations.append(
                f"最大回撤({result.reality_result.max_drawdown:.2%})超标，" f"建议加强风险控制和止损机制"
            )

        if result.hell_result.survival_rate < 0.8:
            recommendations.append(
                f"极端场景存活率({result.hell_result.survival_rate:.2%})较低，" f"建议增强策略的抗风险能力"
            )

        if result.hell_result.recovery_speed > 30:
            recommendations.append(
                f"恢复速度({result.hell_result.recovery_speed:.1f}天)较慢，" f"建议优化策略的恢复机制"
            )

        if not recommendations:
            recommendations.append("策略表现良好，建议继续进入模拟盘验证阶段")

        return recommendations
