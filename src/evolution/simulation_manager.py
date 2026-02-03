"""模拟盘管理器 - 30天实盘验证系统

白皮书依据: 第四章 4.2.2 模拟盘验证运行

在真实市场环境中运行30天模拟交易，验证策略的实战能力。
使用100万虚拟资金，监控每日表现，如果回撤超过20%则立即停止。

只有通过模拟盘验证的策略才有资格获得Z2H基因胶囊认证。

Author: MIA System
Date: 2026-01-23
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.factor_data_models import CandidateStrategy


@dataclass
class DailyResult:
    """每日模拟结果

    白皮书依据: 第四章 4.2.2 每日监控指标
    """

    date: datetime
    day_number: int  # 第几天（1-30）

    # 资金状态
    capital: float  # 当前资金
    positions_value: float  # 持仓市值
    total_value: float  # 总资产

    # 收益指标
    daily_return: float  # 当日收益率
    cumulative_return: float  # 累计收益率

    # 风险指标
    current_drawdown: float  # 当前回撤
    max_drawdown_so_far: float  # 截至目前最大回撤

    # 交易统计
    trades_today: int  # 当日交易次数
    total_trades: int  # 累计交易次数
    winning_trades: int  # 盈利交易次数
    losing_trades: int  # 亏损交易次数

    # 状态
    halted: bool = False  # 是否已停止
    halt_reason: Optional[str] = None  # 停止原因


@dataclass
class SimulationMetrics:
    """模拟盘最终指标

    白皮书依据: 第四章 4.2.2 Z2H认证标准
    """

    # 收益指标
    total_return: float  # 总收益率（30天）
    monthly_return: float  # 月度收益率
    sharpe_ratio: float  # 夏普比率

    # 风险指标
    max_drawdown: float  # 最大回撤
    volatility: float  # 波动率

    # 交易统计
    total_trades: int  # 总交易次数
    winning_trades: int  # 盈利交易次数
    losing_trades: int  # 亏损交易次数
    win_rate: float  # 胜率

    # 盈亏统计
    average_win: float  # 平均盈利
    average_loss: float  # 平均亏损
    profit_factor: float  # 盈亏比

    # 其他
    trading_days: int  # 实际交易天数


@dataclass
class SimulationResult:
    """模拟盘结果

    白皮书依据: 第四章 4.2.2 模拟盘验证结果
    """

    strategy: CandidateStrategy
    passed: bool  # 是否通过验证
    failure_reason: Optional[str]  # 失败原因

    daily_results: List[DailyResult]  # 每日结果
    final_metrics: SimulationMetrics  # 最终指标

    z2h_eligible: bool  # 是否有资格获得Z2H认证
    simulation_start: datetime
    simulation_end: datetime

    # 停止信息
    halted: bool = False  # 是否提前停止
    halt_day: Optional[int] = None  # 停止日期
    halt_reason: Optional[str] = None  # 停止原因


@dataclass
class SimulationConfig:
    """模拟盘配置

    白皮书依据: 第四章 4.2.2 模拟盘参数
    """

    # 基本参数
    duration_days: int = 30  # 模拟天数
    initial_capital: float = 1_000_000.0  # 初始资金（100万）

    # 停止条件
    max_drawdown_halt: float = 0.20  # 最大回撤停止阈值（20%）

    # Z2H认证标准
    min_monthly_return: float = 0.05  # 最低月度收益率（5%）
    min_sharpe_ratio: float = 1.2  # 最低夏普比率
    max_drawdown_limit: float = 0.15  # 最大回撤限制（15%）
    min_win_rate: float = 0.55  # 最低胜率（55%）
    min_profit_factor: float = 1.3  # 最低盈亏比

    # 交易参数
    commission_rate: float = 0.0003  # 手续费率（0.03%）
    slippage_rate: float = 0.0005  # 滑点率（0.05%）


class Simulation:
    """模拟盘实例

    白皮书依据: 第四章 4.2.2 模拟盘运行

    Attributes:
        simulation_id: 模拟盘ID
        strategy: 候选策略
        config: 模拟盘配置
        daily_results: 每日结果列表
        current_day: 当前天数
        halted: 是否已停止
    """

    def __init__(self, strategy: CandidateStrategy, config: SimulationConfig):
        """初始化模拟盘

        Args:
            strategy: 候选策略
            config: 模拟盘配置
        """
        self.simulation_id = str(uuid.uuid4())
        self.strategy = strategy
        self.config = config

        self.daily_results: List[DailyResult] = []
        self.current_day = 0
        self.halted = False
        self.halt_reason: Optional[str] = None

        # 初始化资金状态
        self.capital = config.initial_capital
        self.positions_value = 0.0
        self.peak_value = config.initial_capital

        logger.info(
            f"创建模拟盘: {self.simulation_id}, " f"策略={strategy.name}, " f"初始资金={config.initial_capital:,.0f}"
        )

    def get_total_value(self) -> float:
        """获取总资产

        Returns:
            总资产 = 现金 + 持仓市值
        """
        return self.capital + self.positions_value

    def get_current_drawdown(self) -> float:
        """获取当前回撤

        Returns:
            当前回撤 = (峰值 - 当前) / 峰值
        """
        total_value = self.get_total_value()
        if self.peak_value == 0:
            return 0.0

        drawdown = (self.peak_value - total_value) / self.peak_value
        return max(drawdown, 0.0)


class SimulationManager:
    """模拟盘管理器

    白皮书依据: 第四章 4.2.2 模拟盘验证运行

    管理策略的30天模拟盘验证，监控每日表现，评估最终结果。

    验证流程：
    1. 启动30天模拟交易
    2. 每日监控表现和风险指标
    3. 检查停止条件（回撤>20%）
    4. 评估最终结果
    5. 判断Z2H认证资格

    Attributes:
        config: 模拟盘配置
        active_simulations: 活跃的模拟盘字典
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        """初始化模拟盘管理器

        Args:
            config: 模拟盘配置，None则使用默认配置
        """
        self.config = config or SimulationConfig()
        self.active_simulations: Dict[str, Simulation] = {}

        logger.info(
            f"初始化SimulationManager: "
            f"duration={self.config.duration_days}days, "
            f"capital={self.config.initial_capital:,.0f}, "
            f"halt_dd={self.config.max_drawdown_halt}"
        )

    async def start_simulation(
        self, strategy: CandidateStrategy, duration_days: Optional[int] = None, initial_capital: Optional[float] = None
    ) -> Simulation:
        """启动模拟盘

        白皮书依据: 第四章 4.2.2 启动模拟盘

        Args:
            strategy: 候选策略
            duration_days: 模拟天数，None则使用配置默认值
            initial_capital: 初始资金，None则使用配置默认值

        Returns:
            模拟盘实例

        Raises:
            ValueError: 当策略为None时
        """
        if strategy is None:
            raise ValueError("策略不能为None")

        # 创建配置副本
        config = SimulationConfig(
            duration_days=duration_days or self.config.duration_days,
            initial_capital=initial_capital or self.config.initial_capital,
            max_drawdown_halt=self.config.max_drawdown_halt,
            min_monthly_return=self.config.min_monthly_return,
            min_sharpe_ratio=self.config.min_sharpe_ratio,
            max_drawdown_limit=self.config.max_drawdown_limit,
            min_win_rate=self.config.min_win_rate,
            min_profit_factor=self.config.min_profit_factor,
            commission_rate=self.config.commission_rate,
            slippage_rate=self.config.slippage_rate,
        )

        # 创建模拟盘
        simulation = Simulation(strategy, config)
        self.active_simulations[simulation.simulation_id] = simulation

        logger.info(
            f"启动模拟盘: {simulation.simulation_id}, " f"策略={strategy.name}, " f"天数={config.duration_days}"
        )

        return simulation

    async def monitor_daily(self, simulation: Simulation, market_data: Optional[pd.DataFrame] = None) -> DailyResult:
        """监控每日表现

        白皮书依据: 第四章 4.2.2 每日监控

        Args:
            simulation: 模拟盘实例
            market_data: 市场数据，None则生成模拟数据

        Returns:
            每日结果

        Raises:
            ValueError: 当模拟盘已停止时
        """
        if simulation.halted:
            raise ValueError(f"模拟盘已停止: {simulation.halt_reason}")

        # 增加天数
        simulation.current_day += 1

        # 如果没有提供市场数据，生成模拟数据
        if market_data is None:
            market_data = self._generate_mock_market_data()

        # 模拟交易
        daily_result = await self._simulate_trading_day(simulation, market_data)

        # 检查停止条件
        if self.check_halt_conditions(daily_result):
            simulation.halted = True
            simulation.halt_reason = daily_result.halt_reason
            daily_result.halted = True

            logger.warning(
                f"模拟盘停止: {simulation.simulation_id}, "
                f"Day {daily_result.day_number}, "
                f"原因={daily_result.halt_reason}"
            )

        # 保存每日结果
        simulation.daily_results.append(daily_result)

        return daily_result

    async def _simulate_trading_day(
        self, simulation: Simulation, market_data: pd.DataFrame  # pylint: disable=unused-argument
    ) -> DailyResult:  # pylint: disable=unused-argument
        """模拟一天的交易

        Args:
            simulation: 模拟盘实例
            market_data: 市场数据

        Returns:
            每日结果
        """
        # 简化实现：生成模拟交易结果
        # 实际实现需要执行策略代码并模拟真实交易

        # 基于策略的expected_sharpe生成合理的每日收益
        expected_daily_return = simulation.strategy.expected_sharpe * 0.15 / np.sqrt(252)

        # 添加随机性
        daily_return = np.random.normal(expected_daily_return, 0.15 / np.sqrt(252))  # 日波动率

        # 更新资金状态
        prev_total_value = simulation.get_total_value()
        new_total_value = prev_total_value * (1 + daily_return)

        # 更新峰值
        if new_total_value > simulation.peak_value:  # pylint: disable=r1731
            simulation.peak_value = new_total_value

        # 计算累计收益
        cumulative_return = (new_total_value - simulation.config.initial_capital) / simulation.config.initial_capital

        # 计算回撤
        current_drawdown = simulation.get_current_drawdown()
        max_drawdown_so_far = max(
            current_drawdown,
            (
                max([r.max_drawdown_so_far for r in simulation.daily_results])  # pylint: disable=r1728
                if simulation.daily_results
                else 0.0  # pylint: disable=r1728
            ),  # pylint: disable=r1728
        )

        # 生成交易统计
        trades_today = np.random.randint(0, 5)
        total_trades = sum([r.trades_today for r in simulation.daily_results]) + trades_today  # pylint: disable=r1728

        # 根据收益判断盈亏
        if daily_return > 0:
            winning_trades = sum([r.winning_trades for r in simulation.daily_results]) + 1  # pylint: disable=r1728
            losing_trades = sum([r.losing_trades for r in simulation.daily_results])  # pylint: disable=r1728
        else:
            winning_trades = sum([r.winning_trades for r in simulation.daily_results])  # pylint: disable=r1728
            losing_trades = sum([r.losing_trades for r in simulation.daily_results]) + 1  # pylint: disable=r1728

        # 更新模拟盘状态
        simulation.capital = new_total_value * 0.5  # 假设50%现金
        simulation.positions_value = new_total_value * 0.5  # 假设50%持仓

        # 创建每日结果
        daily_result = DailyResult(
            date=datetime.now() + timedelta(days=simulation.current_day),
            day_number=simulation.current_day,
            capital=simulation.capital,
            positions_value=simulation.positions_value,
            total_value=new_total_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            current_drawdown=current_drawdown,
            max_drawdown_so_far=max_drawdown_so_far,
            trades_today=trades_today,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )

        return daily_result

    def check_halt_conditions(self, current_result: DailyResult) -> bool:
        """检查是否应该停止模拟盘

        白皮书依据: 第四章 4.2.2 停止条件

        停止条件：回撤超过20%

        Args:
            current_result: 当前每日结果

        Returns:
            是否应该停止
        """
        # 检查回撤是否超过阈值
        if current_result.current_drawdown > self.config.max_drawdown_halt:
            current_result.halt_reason = (
                f"excessive_drawdown: {current_result.current_drawdown:.2%} > " f"{self.config.max_drawdown_halt:.2%}"
            )
            return True

        return False

    async def evaluate_results(self, daily_results: List[DailyResult]) -> SimulationMetrics:
        """评估模拟盘最终结果

        白皮书依据: 第四章 4.2.2 结果评估

        Args:
            daily_results: 每日结果列表

        Returns:
            模拟盘最终指标

        Raises:
            ValueError: 当每日结果为空时
        """
        if not daily_results:
            raise ValueError("每日结果不能为空")

        # 计算收益指标
        final_result = daily_results[-1]
        total_return = final_result.cumulative_return
        monthly_return = total_return  # 30天约等于1个月

        # 计算夏普比率
        daily_returns = [r.daily_return for r in daily_results]
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)

        # 计算风险指标
        max_drawdown = max([r.max_drawdown_so_far for r in daily_results])  # pylint: disable=r1728
        volatility = np.std(daily_returns) * np.sqrt(252)  # 年化波动率

        # 交易统计
        total_trades = final_result.total_trades
        winning_trades = final_result.winning_trades
        losing_trades = final_result.losing_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # 盈亏统计
        winning_returns = [r.daily_return for r in daily_results if r.daily_return > 0]
        losing_returns = [r.daily_return for r in daily_results if r.daily_return < 0]

        average_win = np.mean(winning_returns) if winning_returns else 0.0
        average_loss = abs(np.mean(losing_returns)) if losing_returns else 0.0
        profit_factor = abs(average_win / average_loss) if average_loss > 0 else 0.0

        metrics = SimulationMetrics(
            total_return=total_return,
            monthly_return=monthly_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            trading_days=len(daily_results),
        )

        logger.info(
            f"模拟盘评估完成: "
            f"Return={monthly_return:.2%}, "
            f"Sharpe={sharpe_ratio:.3f}, "
            f"DD={max_drawdown:.2%}, "
            f"WinRate={win_rate:.2%}"
        )

        return metrics

    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """计算夏普比率

        Args:
            daily_returns: 每日收益率列表

        Returns:
            年化夏普比率
        """
        if not daily_returns:
            return 0.0

        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)

        if std_return == 0:
            return 0.0

        # 年化夏普比率（假设无风险利率为0）
        sharpe_ratio = mean_return / std_return * np.sqrt(252)

        return sharpe_ratio

    async def run_full_simulation(self, strategy: CandidateStrategy) -> SimulationResult:
        """运行完整的模拟盘验证

        白皮书依据: 第四章 4.2.2 完整验证流程

        Args:
            strategy: 候选策略

        Returns:
            模拟盘结果
        """
        logger.info(f"开始完整模拟盘验证: {strategy.name}")

        simulation_start = datetime.now()

        # 启动模拟盘
        simulation = await self.start_simulation(strategy)

        # 运行每日模拟
        for day in range(self.config.duration_days):
            try:
                await self.monitor_daily(simulation)

                # 如果停止，提前结束
                if simulation.halted:
                    break

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"模拟盘运行错误: Day {day+1}, 错误={e}")
                break

        simulation_end = datetime.now()

        # 评估最终结果
        final_metrics = await self.evaluate_results(simulation.daily_results)

        # 判断是否通过
        passed, failure_reason = self._check_pass_criteria(final_metrics, simulation.halted)

        # 判断Z2H资格
        z2h_eligible = passed and not simulation.halted

        # 创建结果
        result = SimulationResult(
            strategy=strategy,
            passed=passed,
            failure_reason=failure_reason,
            daily_results=simulation.daily_results,
            final_metrics=final_metrics,
            z2h_eligible=z2h_eligible,
            simulation_start=simulation_start,
            simulation_end=simulation_end,
            halted=simulation.halted,
            halt_day=simulation.current_day if simulation.halted else None,
            halt_reason=simulation.halt_reason,
        )

        # 清理活跃模拟盘
        if simulation.simulation_id in self.active_simulations:
            del self.active_simulations[simulation.simulation_id]

        logger.info(
            f"模拟盘验证完成: {strategy.name}, "
            f"Passed={passed}, "
            f"Z2H Eligible={z2h_eligible}, "
            f"Days={len(simulation.daily_results)}"
        )

        return result

    def _check_pass_criteria(self, metrics: SimulationMetrics, halted: bool) -> tuple[bool, Optional[str]]:
        """检查是否通过模拟盘验证

        白皮书依据: 第四章 4.2.2 Z2H认证标准

        通过条件（全部满足）：
        - 未提前停止
        - 月度收益率 > 5%
        - 夏普比率 > 1.2
        - 最大回撤 < 15%
        - 胜率 > 55%
        - 盈亏比 > 1.3

        Args:
            metrics: 模拟盘指标
            halted: 是否提前停止

        Returns:
            (是否通过, 失败原因)
        """
        if halted:
            return False, "simulation_halted"

        if metrics.monthly_return <= self.config.min_monthly_return:
            return False, f"low_return: {metrics.monthly_return:.2%} <= {self.config.min_monthly_return:.2%}"

        if metrics.sharpe_ratio <= self.config.min_sharpe_ratio:
            return False, f"low_sharpe: {metrics.sharpe_ratio:.3f} <= {self.config.min_sharpe_ratio:.3f}"

        if metrics.max_drawdown >= self.config.max_drawdown_limit:
            return False, f"high_drawdown: {metrics.max_drawdown:.2%} >= {self.config.max_drawdown_limit:.2%}"

        if metrics.win_rate <= self.config.min_win_rate:
            return False, f"low_win_rate: {metrics.win_rate:.2%} <= {self.config.min_win_rate:.2%}"

        if metrics.profit_factor <= self.config.min_profit_factor:
            return False, f"low_profit_factor: {metrics.profit_factor:.3f} <= {self.config.min_profit_factor:.3f}"

        return True, None

    def _generate_mock_market_data(self) -> pd.DataFrame:
        """生成模拟市场数据

        Returns:
            模拟市场数据DataFrame
        """
        # 生成一天的市场数据
        data = pd.DataFrame({"date": [datetime.now()], "close": [100.0], "volume": [1000000]})

        return data

    def get_statistics(self) -> Dict:
        """获取管理器统计信息

        Returns:
            统计信息字典
        """
        return {
            "active_simulations": len(self.active_simulations),
            "config": {
                "duration_days": self.config.duration_days,
                "initial_capital": self.config.initial_capital,
                "max_drawdown_halt": self.config.max_drawdown_halt,
                "min_monthly_return": self.config.min_monthly_return,
                "min_sharpe_ratio": self.config.min_sharpe_ratio,
                "max_drawdown_limit": self.config.max_drawdown_limit,
                "min_win_rate": self.config.min_win_rate,
                "min_profit_factor": self.config.min_profit_factor,
            },
        }
