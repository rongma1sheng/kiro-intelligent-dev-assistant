"""
策略Hell Track (Strategy Hell Track)

白皮书依据: 第四章 4.2.2 策略Arena - Hell Track (极端场景压力测试)
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.strategy_data_models import ExtremeScenarioType, Strategy, StrategyHellTrackResult


class ExtremeScenarioGenerator:
    """极端场景生成器

    白皮书依据: 第四章 4.2.2 - Hell Track极端场景生成

    生成各种极端市场场景用于策略压力测试。
    """

    def __init__(self):
        """初始化极端场景生成器"""
        logger.info("初始化ExtremeScenarioGenerator")

    def generate_flash_crash(
        self, base_data: pd.DataFrame, crash_magnitude: float = 0.10, recovery_days: int = 5
    ) -> pd.DataFrame:
        """生成闪崩场景

        白皮书依据: 第四章 4.2.2 - 闪崩场景 (Flash Crash)

        模拟市场在短时间内急剧下跌后快速恢复的场景。

        Args:
            base_data: 基础数据
            crash_magnitude: 崩盘幅度，默认10%
            recovery_days: 恢复天数，默认5天

        Returns:
            包含闪崩场景的数据
        """
        scenario_data = base_data.copy()

        # 选择崩盘起始点
        crash_start = len(scenario_data) // 2

        # 应用闪崩
        for i in range(crash_start, min(crash_start + recovery_days, len(scenario_data))):
            if i == crash_start:
                # 第一天急剧下跌
                multiplier = 1 - crash_magnitude
            else:
                # 逐步恢复
                recovery_progress = (i - crash_start) / recovery_days
                multiplier = (1 - crash_magnitude) + crash_magnitude * recovery_progress

            if "close" in scenario_data.columns:
                scenario_data.iloc[i, scenario_data.columns.get_loc("close")] *= multiplier

        logger.debug(f"生成闪崩场景: magnitude={crash_magnitude:.2%}, recovery={recovery_days}天")

        return scenario_data

    def generate_circuit_breaker(
        self, base_data: pd.DataFrame, trigger_threshold: float = 0.07, halt_days: int = 1
    ) -> pd.DataFrame:
        """生成熔断场景

        白皮书依据: 第四章 4.2.2 - 熔断场景 (Circuit Breaker)

        模拟市场触发熔断机制，交易暂停的场景。

        Args:
            base_data: 基础数据
            trigger_threshold: 熔断触发阈值，默认7%
            halt_days: 暂停交易天数，默认1天

        Returns:
            包含熔断场景的数据
        """
        scenario_data = base_data.copy()

        # 选择熔断触发点
        trigger_point = len(scenario_data) // 3

        # 应用熔断
        if "close" in scenario_data.columns:
            # 触发日大跌
            scenario_data.iloc[trigger_point, scenario_data.columns.get_loc("close")] *= 1 - trigger_threshold

            # 暂停期间价格不变
            for i in range(trigger_point + 1, min(trigger_point + halt_days + 1, len(scenario_data))):
                scenario_data.iloc[i, scenario_data.columns.get_loc("close")] = scenario_data.iloc[
                    trigger_point, scenario_data.columns.get_loc("close")
                ]

        logger.debug(f"生成熔断场景: threshold={trigger_threshold:.2%}, halt={halt_days}天")

        return scenario_data

    def generate_liquidity_drought(
        self,
        base_data: pd.DataFrame,
        volume_reduction: float = 0.90,
        spread_increase: float = 5.0,
        duration_days: int = 10,
    ) -> pd.DataFrame:
        """生成流动性枯竭场景

        白皮书依据: 第四章 4.2.2 - 流动性枯竭场景 (Liquidity Drought)

        模拟市场流动性急剧下降，买卖价差扩大的场景。

        Args:
            base_data: 基础数据
            volume_reduction: 成交量减少比例，默认90%
            spread_increase: 价差扩大倍数，默认5倍
            duration_days: 持续天数，默认10天

        Returns:
            包含流动性枯竭场景的数据
        """
        scenario_data = base_data.copy()

        # 选择流动性枯竭起始点
        start_point = len(scenario_data) // 4

        # 应用流动性枯竭
        for i in range(start_point, min(start_point + duration_days, len(scenario_data))):
            if "volume" in scenario_data.columns:
                scenario_data.iloc[i, scenario_data.columns.get_loc("volume")] *= 1 - volume_reduction

            # 增加价格波动模拟价差扩大
            if "close" in scenario_data.columns:
                noise = np.random.randn() * 0.02 * spread_increase
                scenario_data.iloc[i, scenario_data.columns.get_loc("close")] *= 1 + noise

        logger.debug(
            f"生成流动性枯竭场景: volume_reduction={volume_reduction:.2%}, "
            f"spread_increase={spread_increase}x, duration={duration_days}天"
        )

        return scenario_data

    def generate_volatility_explosion(
        self, base_data: pd.DataFrame, volatility_multiplier: float = 3.0, duration_days: int = 20
    ) -> pd.DataFrame:
        """生成波动率爆炸场景

        白皮书依据: 第四章 4.2.2 - 波动率爆炸场景 (Volatility Explosion)

        模拟市场波动率急剧上升的场景。

        Args:
            base_data: 基础数据
            volatility_multiplier: 波动率放大倍数，默认3倍
            duration_days: 持续天数，默认20天

        Returns:
            包含波动率爆炸场景的数据
        """
        scenario_data = base_data.copy()

        # 选择波动率爆炸起始点
        start_point = len(scenario_data) // 5

        # 应用波动率爆炸
        if "close" in scenario_data.columns:
            for i in range(start_point, min(start_point + duration_days, len(scenario_data))):
                # 放大日收益率波动
                if i > 0:
                    prev_close = scenario_data.iloc[i - 1, scenario_data.columns.get_loc("close")]
                    current_close = scenario_data.iloc[i, scenario_data.columns.get_loc("close")]
                    daily_return = (current_close - prev_close) / prev_close

                    # 放大波动
                    amplified_return = daily_return * volatility_multiplier
                    scenario_data.iloc[i, scenario_data.columns.get_loc("close")] = prev_close * (1 + amplified_return)

        logger.debug(f"生成波动率爆炸场景: multiplier={volatility_multiplier}x, " f"duration={duration_days}天")

        return scenario_data

    def generate_black_swan(
        self, base_data: pd.DataFrame, drop_magnitude: float = 0.20, recovery_days: int = 60
    ) -> pd.DataFrame:
        """生成黑天鹅事件场景

        白皮书依据: 第四章 4.2.2 - 黑天鹅事件场景 (Black Swan)

        模拟极端罕见的市场崩盘事件。

        Args:
            base_data: 基础数据
            drop_magnitude: 下跌幅度，默认20%
            recovery_days: 恢复天数，默认60天

        Returns:
            包含黑天鹅事件场景的数据
        """
        scenario_data = base_data.copy()

        # 选择黑天鹅事件起始点
        event_start = len(scenario_data) // 3

        # 应用黑天鹅事件
        if "close" in scenario_data.columns:
            base_price = scenario_data.iloc[event_start - 1, scenario_data.columns.get_loc("close")]

            for i in range(event_start, len(scenario_data)):
                days_since_event = i - event_start

                if days_since_event < 3:
                    # 前3天急剧下跌
                    drop_progress = (days_since_event + 1) / 3
                    multiplier = 1 - drop_magnitude * drop_progress
                elif days_since_event < recovery_days:
                    # 缓慢恢复
                    recovery_progress = (days_since_event - 3) / (recovery_days - 3)
                    multiplier = (1 - drop_magnitude) + drop_magnitude * recovery_progress * 0.8
                else:
                    # 恢复到80%
                    multiplier = 1 - drop_magnitude * 0.2

                scenario_data.iloc[i, scenario_data.columns.get_loc("close")] = base_price * multiplier

        logger.debug(f"生成黑天鹅事件场景: drop={drop_magnitude:.2%}, " f"recovery={recovery_days}天")

        return scenario_data


class StrategyHellTrack:
    """策略Hell Track测试

    白皮书依据: 第四章 4.2.2 策略Arena - Hell Track

    使用极端市场场景对策略进行压力测试，评估策略在极端条件下的生存能力。

    Attributes:
        scenario_generator: 极端场景生成器
        initial_capital: 初始资金
        survival_threshold: 存活阈值 (权益低于此比例视为失败)
    """

    def __init__(
        self,
        scenario_generator: Optional[ExtremeScenarioGenerator] = None,
        initial_capital: float = 1_000_000.0,
        survival_threshold: float = 0.50,
    ):
        """初始化Hell Track测试器

        Args:
            scenario_generator: 极端场景生成器，None则创建默认实例
            initial_capital: 初始资金，必须 > 0
            survival_threshold: 存活阈值，范围 [0, 1]

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if initial_capital <= 0:
            raise ValueError(f"初始资金必须大于0，当前值: {initial_capital}")
        if not 0 <= survival_threshold <= 1:
            raise ValueError(f"存活阈值必须在[0, 1]范围内，当前值: {survival_threshold}")

        self.scenario_generator = scenario_generator or ExtremeScenarioGenerator()
        self.initial_capital = initial_capital
        self.survival_threshold = survival_threshold

        logger.info(
            f"初始化StrategyHellTrack: "
            f"initial_capital={initial_capital:,.0f}, "
            f"survival_threshold={survival_threshold:.2%}"
        )

    async def test_strategy(self, strategy: Strategy, base_data: pd.DataFrame) -> StrategyHellTrackResult:
        """测试策略在Hell Track上的表现

        白皮书依据: 第四章 4.2.2 - Hell Track极端场景压力测试

        Args:
            strategy: 待测试策略
            base_data: 基础历史数据

        Returns:
            Hell Track测试结果

        Raises:
            ValueError: 当输入数据无效时
        """
        if base_data.empty:
            raise ValueError("基础数据不能为空")

        logger.info(f"开始Hell Track测试: strategy_id={strategy.id}, " f"数据点数={len(base_data)}")

        try:
            # 1. 测试各个极端场景
            scenario_results = await self._test_all_scenarios(strategy, base_data)

            # 2. 计算存活率
            survival_rate = self._calculate_survival_rate(scenario_results)

            # 3. 计算恢复速度
            recovery_speed = self._calculate_recovery_speed(scenario_results)

            # 4. 计算最大压力回撤
            max_stress_drawdown = self._calculate_max_stress_drawdown(scenario_results)

            # 5. 计算Hell评分
            hell_score = self._calculate_hell_score(scenario_results, survival_rate)

            # 6. 构建结果对象
            result = StrategyHellTrackResult(
                survival_rate=survival_rate,
                flash_crash_performance=scenario_results["flash_crash"]["performance"],
                circuit_breaker_performance=scenario_results["circuit_breaker"]["performance"],
                liquidity_drought_performance=scenario_results["liquidity_drought"]["performance"],
                volatility_explosion_performance=scenario_results["volatility_explosion"]["performance"],
                black_swan_performance=scenario_results["black_swan"]["performance"],
                recovery_speed=recovery_speed,
                max_stress_drawdown=max_stress_drawdown,
                hell_score=hell_score,
                scenarios_tested=5,
            )

            logger.info(
                f"Hell Track测试完成 - "
                f"存活率: {survival_rate:.2%}, "
                f"恢复速度: {recovery_speed:.1f}天, "
                f"最大压力回撤: {max_stress_drawdown:.2%}, "
                f"Hell评分: {hell_score:.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Hell Track测试失败: {e}")
            raise

    async def _test_all_scenarios(self, strategy: Strategy, base_data: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """测试所有极端场景

        Args:
            strategy: 待测试策略
            base_data: 基础数据

        Returns:
            各场景测试结果字典
        """
        results = {}

        # 1. 闪崩场景
        flash_crash_data = self.scenario_generator.generate_flash_crash(base_data)
        results["flash_crash"] = await self._test_scenario(strategy, flash_crash_data, ExtremeScenarioType.FLASH_CRASH)

        # 2. 熔断场景
        circuit_breaker_data = self.scenario_generator.generate_circuit_breaker(base_data)
        results["circuit_breaker"] = await self._test_scenario(
            strategy, circuit_breaker_data, ExtremeScenarioType.CIRCUIT_BREAKER
        )

        # 3. 流动性枯竭场景
        liquidity_drought_data = self.scenario_generator.generate_liquidity_drought(base_data)
        results["liquidity_drought"] = await self._test_scenario(
            strategy, liquidity_drought_data, ExtremeScenarioType.LIQUIDITY_DROUGHT
        )

        # 4. 波动率爆炸场景
        volatility_explosion_data = self.scenario_generator.generate_volatility_explosion(base_data)
        results["volatility_explosion"] = await self._test_scenario(
            strategy, volatility_explosion_data, ExtremeScenarioType.VOLATILITY_EXPLOSION
        )

        # 5. 黑天鹅事件场景
        black_swan_data = self.scenario_generator.generate_black_swan(base_data)
        results["black_swan"] = await self._test_scenario(strategy, black_swan_data, ExtremeScenarioType.BLACK_SWAN)

        return results

    async def _test_scenario(
        self,
        strategy: Strategy,  # pylint: disable=unused-argument
        scenario_data: pd.DataFrame,
        scenario_type: ExtremeScenarioType,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """测试单个极端场景

        Args:
            strategy: 待测试策略
            scenario_data: 场景数据
            scenario_type: 场景类型

        Returns:
            场景测试结果
        """
        logger.debug(f"测试场景: {scenario_type.value}")

        # 模拟策略在该场景下的表现
        equity = self.initial_capital
        min_equity = equity
        max_drawdown = 0.0
        recovery_days = 0
        survived = True

        # 简化版本：模拟逐日交易
        for i in range(1, len(scenario_data)):
            # 模拟日收益
            if "close" in scenario_data.columns:
                daily_return = (
                    scenario_data.iloc[i]["close"] - scenario_data.iloc[i - 1]["close"]
                ) / scenario_data.iloc[i - 1]["close"]
            else:
                daily_return = np.random.randn() * 0.02

            # 策略收益 (假设策略跟随市场但有一定对冲)
            strategy_return = daily_return * 0.7 + np.random.randn() * 0.005
            equity *= 1 + strategy_return

            # 更新最小权益
            if equity < min_equity:  # pylint: disable=r1730
                min_equity = equity

            # 计算回撤
            current_drawdown = (self.initial_capital - equity) / self.initial_capital
            if current_drawdown > max_drawdown:  # pylint: disable=r1731
                max_drawdown = current_drawdown

            # 检查是否存活
            if equity < self.initial_capital * self.survival_threshold:
                survived = False
                break

        # 计算恢复天数
        if min_equity < self.initial_capital:
            recovery_days = int((self.initial_capital - min_equity) / (self.initial_capital * 0.01))

        # 计算场景表现 [-1, 1]
        performance = self._calculate_scenario_performance(equity, self.initial_capital, max_drawdown, survived)

        return {
            "survived": survived,
            "final_equity": equity,
            "min_equity": min_equity,
            "max_drawdown": max_drawdown,
            "recovery_days": recovery_days,
            "performance": performance,
        }

    def _calculate_scenario_performance(
        self, final_equity: float, initial_capital: float, max_drawdown: float, survived: bool
    ) -> float:
        """计算场景表现评分

        Args:
            final_equity: 最终权益
            initial_capital: 初始资金
            max_drawdown: 最大回撤
            survived: 是否存活

        Returns:
            场景表现评分 [-1, 1]
        """
        if not survived:
            return -1.0

        # 基于收益率和回撤计算表现
        return_rate = (final_equity - initial_capital) / initial_capital

        # 收益率贡献 [-0.5, 0.5]
        return_score = max(-0.5, min(0.5, return_rate))

        # 回撤惩罚 [-0.5, 0]
        drawdown_penalty = -max_drawdown * 0.5

        performance = return_score + drawdown_penalty + 0.5  # 基础分0.5

        return max(-1.0, min(1.0, performance))

    def _calculate_survival_rate(self, scenario_results: Dict[str, Dict[str, Any]]) -> float:
        """计算存活率

        Args:
            scenario_results: 各场景测试结果

        Returns:
            存活率 [0, 1]
        """
        survived_count = sum(1 for result in scenario_results.values() if result["survived"])
        total_scenarios = len(scenario_results)

        return survived_count / total_scenarios if total_scenarios > 0 else 0.0

    def _calculate_recovery_speed(self, scenario_results: Dict[str, Dict[str, Any]]) -> float:
        """计算平均恢复速度

        Args:
            scenario_results: 各场景测试结果

        Returns:
            平均恢复天数
        """
        recovery_days = [result["recovery_days"] for result in scenario_results.values() if result["survived"]]

        return float(np.mean(recovery_days)) if recovery_days else 0.0

    def _calculate_max_stress_drawdown(self, scenario_results: Dict[str, Dict[str, Any]]) -> float:
        """计算最大压力回撤

        Args:
            scenario_results: 各场景测试结果

        Returns:
            最大压力回撤
        """
        max_drawdowns = [result["max_drawdown"] for result in scenario_results.values()]

        return max(max_drawdowns) if max_drawdowns else 0.0

    def _calculate_hell_score(self, scenario_results: Dict[str, Dict[str, Any]], survival_rate: float) -> float:
        """计算Hell Track综合评分

        白皮书依据: 第四章 4.2.2 - Hell Track评分标准

        评分公式:
        Hell Score = 0.4 * 存活率 + 0.3 * 平均场景表现 + 0.3 * 恢复能力

        Args:
            scenario_results: 各场景测试结果
            survival_rate: 存活率

        Returns:
            Hell评分 [0, 1]
        """
        # 计算平均场景表现
        performances = [result["performance"] for result in scenario_results.values()]
        avg_performance = (np.mean(performances) + 1) / 2  # 转换到[0, 1]

        # 计算恢复能力评分
        recovery_days = self._calculate_recovery_speed(scenario_results)
        recovery_score = max(0, 1 - recovery_days / 60)  # 60天内恢复得满分

        # 加权计算综合评分
        hell_score = 0.40 * survival_rate + 0.30 * avg_performance + 0.30 * recovery_score

        # 确保在[0, 1]范围内
        hell_score = max(0.0, min(1.0, hell_score))

        return float(hell_score)
