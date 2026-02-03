"""Simulation Manager for Orchestration

白皮书依据: 第四章 4.5.1 模拟管理器
"""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from src.evolution.simulation.data_models import (
    SimulationConfig,
    SimulationResult,
    SimulationState,
    StrategyTier,
)
from src.evolution.simulation.simulation_engine import SimulationEngine


class SimulationManager:
    """模拟管理器

    白皮书依据: 第四章 4.5.1 模拟管理器

    协调整个模拟流程，包括初始化、每日执行、提前终止检查、最终评估等。

    Attributes:
        config: 模拟配置
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        """初始化模拟管理器

        Args:
            config: 模拟配置，None则使用默认配置
        """
        self.config = config or SimulationConfig()

        logger.info(
            f"初始化SimulationManager: "
            f"duration={self.config.duration_days}天, "
            f"capital={self.config.initial_capital:.2f}"
        )

    def run_simulation(
        self, strategy_id: str, strategy_tier: StrategyTier, market_data_generator, signal_generator
    ) -> SimulationResult:
        """运行完整模拟

        白皮书依据: 第四章 4.5.1 模拟流程 - Requirement 6.1

        Args:
            strategy_id: 策略ID
            strategy_tier: 策略层级
            market_data_generator: 市场数据生成器（返回每日市场数据）
            signal_generator: 信号生成器（返回每日交易信号）

        Returns:
            模拟结果
        """
        logger.info(f"开始模拟: strategy_id={strategy_id}, tier={strategy_tier.value}")

        # 1. 初始化模拟引擎
        engine = SimulationEngine(self.config, strategy_tier)

        # 2. 设置开始日期
        start_date = datetime.now()
        current_date = start_date

        # 3. 运行每日模拟
        state = SimulationState.RUNNING
        failure_reason = None

        for day in range(self.config.duration_days):  # pylint: disable=unused-variable
            try:
                # 获取市场数据
                market_data = market_data_generator(current_date)

                # 生成交易信号
                signals = signal_generator(current_date, market_data)

                # 运行每日模拟
                daily_result = engine.run_daily_simulation(  # pylint: disable=unused-variable
                    date=current_date, market_data=market_data, signals=signals
                )  # pylint: disable=unused-variable

                # 检查提前终止（Requirement 6.6）
                if engine.check_early_termination():
                    state = SimulationState.FAILED
                    failure_reason = f"回撤超过{self.config.max_drawdown_threshold:.2%}阈值"
                    logger.warning(f"模拟提前终止: {failure_reason}")
                    break

                # 下一天
                current_date += timedelta(days=1)

            except Exception as e:  # pylint: disable=broad-exception-caught
                state = SimulationState.FAILED
                failure_reason = f"模拟执行错误: {str(e)}"
                logger.error(f"模拟失败: {failure_reason}", exc_info=True)
                break

        # 4. 计算最终指标（Requirement 6.7）
        if state == SimulationState.RUNNING:
            state = SimulationState.COMPLETED

        end_date = current_date
        tracker = engine.get_performance_tracker()

        total_return = tracker.get_total_return()
        sharpe_ratio = tracker.calculate_sharpe_ratio()
        max_drawdown = tracker.calculate_max_drawdown()
        win_rate = tracker.calculate_win_rate()
        profit_factor = tracker.calculate_profit_factor()
        final_capital = tracker.get_final_capital()

        # 5. 评估是否通过（Requirement 6.8）
        passed = self._evaluate_pass_criteria(
            state=state,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
        )

        # 6. 创建模拟结果
        result = SimulationResult(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            duration_days=len(tracker.daily_results),
            initial_capital=tracker.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            daily_results=tracker.daily_results,
            state=state,
            passed=passed,
            failure_reason=failure_reason,
        )

        logger.info(
            f"模拟完成: "
            f"strategy_id={strategy_id}, "
            f"state={state.value}, "
            f"passed={passed}, "
            f"return={total_return:.4f}, "
            f"sharpe={sharpe_ratio:.4f}, "
            f"dd={max_drawdown:.4f}"
        )

        return result

    def _evaluate_pass_criteria(  # pylint: disable=too-many-positional-arguments
        self,
        state: SimulationState,
        total_return: float,
        sharpe_ratio: float,
        max_drawdown: float,
        win_rate: float,
        profit_factor: float,
    ) -> bool:
        """评估是否通过模拟

        白皮书依据: 第四章 4.5.8 通过标准 - Requirement 6.8

        通过标准:
        - 状态为COMPLETED
        - 总收益率 > 5%
        - 夏普比率 > 1.2
        - 最大回撤 < 15%
        - 胜率 > 55%
        - 盈亏比 > 1.3

        Args:
            state: 模拟状态
            total_return: 总收益率
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率
            profit_factor: 盈亏比

        Returns:
            True表示通过
        """
        # 状态必须为COMPLETED
        if state != SimulationState.COMPLETED:
            logger.info(f"未通过: 状态为{state.value}")
            return False

        # 检查各项指标
        checks = [
            (total_return >= self.config.min_return, f"总收益率{total_return:.4f} >= {self.config.min_return:.4f}"),
            (sharpe_ratio >= self.config.min_sharpe, f"夏普比率{sharpe_ratio:.4f} >= {self.config.min_sharpe:.4f}"),
            (max_drawdown >= self.config.max_drawdown, f"最大回撤{max_drawdown:.4f} >= {self.config.max_drawdown:.4f}"),
            (win_rate >= self.config.min_win_rate, f"胜率{win_rate:.4f} >= {self.config.min_win_rate:.4f}"),
            (
                profit_factor >= self.config.min_profit_factor,
                f"盈亏比{profit_factor:.4f} >= {self.config.min_profit_factor:.4f}",
            ),
        ]

        all_passed = True
        for passed, message in checks:
            if not passed:
                logger.info(f"未通过: {message}")
                all_passed = False

        if all_passed:
            logger.info("✅ 所有指标均达标，模拟通过")

        return all_passed
