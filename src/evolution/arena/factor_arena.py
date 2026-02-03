"""
因子Arena系统 (Factor Arena System)

白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
from loguru import logger

from src.evolution.arena.cross_market_track import CrossMarketTrack
from src.evolution.arena.data_models import Factor, FactorTestResult, MarketType
from src.evolution.arena.factor_hell_track import FactorHellTrack
from src.evolution.arena.factor_performance_monitor import FactorPerformanceMonitor
from src.evolution.arena.factor_reality_track import FactorRealityTrack
from src.infra.event_bus import EventBus, EventPriority, EventType


class FactorArenaSystem:
    """因子Arena系统

    白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统

    核心理念: "No factor enters strategy generation without passing through the Arena"

    职责:
    1. 编排三轨测试流程 (Reality → Hell → Cross-Market)
    2. 计算综合Arena评分
    3. 判断因子是否通过Arena测试
    4. 发布Arena测试完成事件

    性能目标:
    - 三轨测试总时长 < 30秒 (P99)
    """

    def __init__(self, event_bus: EventBus):
        """初始化因子Arena系统

        Args:
            event_bus: 事件总线实例

        Raises:
            TypeError: 当event_bus类型错误时
        """
        if not isinstance(event_bus, EventBus):
            raise TypeError("event_bus必须是EventBus类型")

        self.event_bus = event_bus

        # 初始化性能监控器
        self.performance_monitor = FactorPerformanceMonitor()

        # 初始化三轨测试器
        self.reality_track = FactorRealityTrack(self.performance_monitor)
        self.hell_track = FactorHellTrack(self.performance_monitor)
        self.cross_market_track = CrossMarketTrack(self.performance_monitor)

        # Arena通过阈值
        self.pass_threshold = 0.7  # 综合评分 > 0.7 才能通过

        logger.info("初始化FactorArenaSystem")

    async def test_factor(  # pylint: disable=too-many-positional-arguments
        self,
        factor: Factor,
        historical_data: pd.DataFrame,
        returns_data: pd.Series,
        market_data: Optional[Dict[MarketType, pd.DataFrame]] = None,
        market_returns: Optional[Dict[MarketType, pd.Series]] = None,
    ) -> FactorTestResult:
        """测试因子通过三轨Arena

        白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统

        测试流程:
        1. Reality Track: 历史数据测试
        2. Hell Track: 极端场景测试
        3. Cross-Market Track: 跨市场测试
        4. 计算综合评分
        5. 判断是否通过
        6. 发布事件

        Args:
            factor: 待测试因子
            historical_data: 历史数据 (用于Reality和Hell Track)
            returns_data: 收益率数据 (用于Reality和Hell Track)
            market_data: 各市场历史数据 (用于Cross-Market Track)
            market_returns: 各市场收益率数据 (用于Cross-Market Track)

        Returns:
            因子测试结果

        Raises:
            ValueError: 当输入数据无效时
            RuntimeError: 当测试超时时
        """
        logger.info(f"开始Arena三轨测试: {factor.id}")
        start_time = time.perf_counter()

        try:
            # 验证输入数据
            self._validate_input_data(historical_data, returns_data, market_data, market_returns)

            # 并行执行三轨测试 (性能优化)
            reality_task = self.reality_track.test_factor(factor, historical_data, returns_data)

            hell_task = self.hell_track.test_factor(factor, historical_data, returns_data)

            # Cross-Market Track需要市场数据
            if market_data and market_returns:
                cross_market_task = self.cross_market_track.test_factor(factor, market_data, market_returns)
            else:
                # 如果没有提供市场数据，使用默认数据
                logger.warning("未提供市场数据，使用默认A股数据进行Cross-Market测试")
                default_market_data = {MarketType.A_STOCK: historical_data}
                default_market_returns = {MarketType.A_STOCK: returns_data}
                cross_market_task = self.cross_market_track.test_factor(
                    factor, default_market_data, default_market_returns
                )

            # 并行执行三轨测试
            reality_result, hell_result, cross_market_result = await asyncio.gather(
                reality_task, hell_task, cross_market_task
            )

            # 计算综合评分
            overall_score = self.performance_monitor.calculate_overall_score(
                reality_score=reality_result.reality_score,
                hell_score=hell_result.hell_score,
                cross_market_score=cross_market_result.cross_market_score,
            )

            # 判断是否通过
            passed = overall_score >= self.pass_threshold

            # 创建测试结果
            test_result = FactorTestResult(
                factor_id=factor.id,
                reality_result=reality_result,
                hell_result=hell_result,
                cross_market_result=cross_market_result,
                overall_score=overall_score,
                passed=passed,
                test_timestamp=datetime.now(),
                detailed_metrics={
                    "reality_score": reality_result.reality_score,
                    "hell_score": hell_result.hell_score,
                    "cross_market_score": cross_market_result.cross_market_score,
                    "ic": reality_result.ic,
                    "ir": reality_result.ir,
                    "sharpe_ratio": reality_result.sharpe_ratio,
                    "survival_rate": hell_result.survival_rate,
                    "adaptability_score": cross_market_result.adaptability_score,
                },
            )

            # 更新因子状态
            factor.arena_tested = True
            factor.arena_score = overall_score

            # 计算测试耗时
            elapsed_time = time.perf_counter() - start_time

            # 发布Arena测试完成事件
            await self._publish_arena_completed_event(factor, test_result, elapsed_time)

            logger.info(
                f"Arena三轨测试完成: {factor.id}, "
                f"综合评分={overall_score:.4f}, "
                f"通过={passed}, "
                f"耗时={elapsed_time:.2f}秒"
            )

            # 检查性能目标
            if elapsed_time > 30.0:
                logger.warning(f"Arena测试耗时超过性能目标: {elapsed_time:.2f}秒 > 30秒")

            return test_result

        except Exception as e:
            logger.error(f"Arena测试失败: {factor.id}, 错误: {e}")
            raise

    def _validate_input_data(
        self,
        historical_data: pd.DataFrame,
        returns_data: pd.Series,
        market_data: Optional[Dict[MarketType, pd.DataFrame]],
        market_returns: Optional[Dict[MarketType, pd.Series]],
    ) -> None:
        """验证输入数据有效性

        Args:
            historical_data: 历史数据
            returns_data: 收益率数据
            market_data: 市场数据
            market_returns: 市场收益率

        Raises:
            ValueError: 当数据无效时
        """
        if historical_data.empty:
            raise ValueError("历史数据不能为空")

        if returns_data.empty:
            raise ValueError("收益率数据不能为空")

        if len(historical_data) < 100:
            raise ValueError(f"历史数据样本不足，至少需要100个样本，当前: {len(historical_data)}")

        if len(returns_data) < 100:
            raise ValueError(f"收益率数据样本不足，至少需要100个样本，当前: {len(returns_data)}")

        # 检查必需的列
        required_columns = ["close", "volume"]
        missing_columns = [col for col in required_columns if col not in historical_data.columns]
        if missing_columns:
            raise ValueError(f"历史数据缺少必需的列: {missing_columns}")

        # 验证市场数据 (如果提供)
        if market_data is not None and market_returns is not None:
            if len(market_data) != len(market_returns):
                raise ValueError(f"市场数据和收益率数据数量不一致: " f"{len(market_data)} vs {len(market_returns)}")

    async def _publish_arena_completed_event(
        self, factor: Factor, test_result: FactorTestResult, elapsed_time: float
    ) -> None:
        """发布Arena测试完成事件

        白皮书依据: 第四章 4.2.1 因子Arena - 事件驱动通信

        Args:
            factor: 测试的因子
            test_result: 测试结果
            elapsed_time: 测试耗时(秒)
        """
        try:
            await self.event_bus.publish_simple(
                event_type=EventType.ARENA_TEST_COMPLETED,
                source_module="factor_arena",
                data={
                    "factor_id": factor.id,
                    "factor_name": factor.name,
                    "overall_score": test_result.overall_score,
                    "passed": test_result.passed,
                    "reality_score": test_result.reality_result.reality_score,
                    "hell_score": test_result.hell_result.hell_score,
                    "cross_market_score": test_result.cross_market_result.cross_market_score,
                    "elapsed_time": elapsed_time,
                    "test_timestamp": test_result.test_timestamp.isoformat(),
                },
                priority=EventPriority.HIGH,
            )

            logger.info(f"发布Arena测试完成事件: {factor.id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布Arena测试完成事件失败: {e}")

    def get_pass_threshold(self) -> float:
        """获取Arena通过阈值

        Returns:
            通过阈值 [0, 1]
        """
        return self.pass_threshold

    def set_pass_threshold(self, threshold: float) -> None:
        """设置Arena通过阈值

        Args:
            threshold: 新的通过阈值 [0, 1]

        Raises:
            ValueError: 当阈值不在有效范围时
        """
        if not 0 <= threshold <= 1:
            raise ValueError(f"通过阈值必须在[0, 1]范围内，当前值: {threshold}")

        old_threshold = self.pass_threshold
        self.pass_threshold = threshold

        logger.info(f"Arena通过阈值已更新: {old_threshold:.2f} → {threshold:.2f}")
