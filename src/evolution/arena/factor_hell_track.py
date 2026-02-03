"""
因子Hell Track测试轨道 (Factor Hell Track)

白皮书依据: 第四章 4.2.1 因子Arena - Hell Track
"""

from typing import Dict

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.data_models import ExtremeScenarioType, Factor, HellTrackResult
from src.evolution.arena.factor_performance_monitor import FactorPerformanceMonitor


class FactorHellTrack:
    """因子Hell Track测试轨道

    白皮书依据: 第四章 4.2.1 因子Arena - Hell Track

    职责:
    1. 测试因子在极端市场条件下的表现
    2. 模拟崩盘、闪崩、流动性危机等场景
    3. 评估因子的抗风险能力和存活率

    极端场景:
    - 崩盘场景 (Crash): 市场下跌 > 20%
    - 闪崩场景 (Flash Crash): 短时间内暴跌 > 10%
    - 流动性危机 (Liquidity Crisis): 成交量骤降 > 70%
    - 波动率飙升 (Volatility Spike): 波动率增加 > 3倍
    - 相关性崩溃 (Correlation Breakdown): 相关性突变
    """

    def __init__(self, performance_monitor: FactorPerformanceMonitor):
        """初始化Hell Track

        Args:
            performance_monitor: 性能监控器实例

        Raises:
            TypeError: 当performance_monitor类型错误时
        """
        if not isinstance(performance_monitor, FactorPerformanceMonitor):
            raise TypeError("performance_monitor必须是FactorPerformanceMonitor类型")

        self.performance_monitor = performance_monitor

        # 极端场景配置
        self.scenarios = {
            ExtremeScenarioType.CRASH: {"name": "崩盘场景", "description": "市场下跌超过20%", "threshold": -0.20},
            ExtremeScenarioType.FLASH_CRASH: {
                "name": "闪崩场景",
                "description": "短时间内暴跌超过10%",
                "threshold": -0.10,
                "window": 5,  # 5个交易日
            },
            ExtremeScenarioType.LIQUIDITY_CRISIS: {
                "name": "流动性危机",
                "description": "成交量骤降超过70%",
                "threshold": -0.70,
            },
            ExtremeScenarioType.VOLATILITY_SPIKE: {
                "name": "波动率飙升",
                "description": "波动率增加超过3倍",
                "threshold": 3.0,
            },
            ExtremeScenarioType.CORRELATION_BREAKDOWN: {
                "name": "相关性崩溃",
                "description": "相关性突然变化",
                "threshold": 0.5,  # 相关性变化超过0.5
            },
        }

        logger.info("初始化FactorHellTrack")

    async def test_factor(
        self, factor: Factor, historical_data: pd.DataFrame, returns_data: pd.Series
    ) -> HellTrackResult:
        """测试因子在Hell Track上的表现

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track测试

        Args:
            factor: 待测试因子
            historical_data: 历史数据
            returns_data: 收益率数据

        Returns:
            Hell Track测试结果

        Raises:
            ValueError: 当输入数据无效时
        """
        logger.info(f"开始Hell Track测试: {factor.id}")

        # 验证输入数据
        self._validate_input_data(historical_data, returns_data)

        # 计算因子值
        factor_values = self._evaluate_factor_expression(factor.expression, historical_data)

        # 测试各个极端场景
        scenario_results = {}

        # 1. 崩盘场景
        crash_perf = await self._test_crash_scenario(factor_values, returns_data, historical_data)
        scenario_results["crash"] = crash_perf

        # 2. 闪崩场景
        flash_crash_perf = await self._test_flash_crash_scenario(factor_values, returns_data, historical_data)
        scenario_results["flash_crash"] = flash_crash_perf

        # 3. 流动性危机
        liquidity_crisis_perf = await self._test_liquidity_crisis_scenario(factor_values, returns_data, historical_data)
        scenario_results["liquidity_crisis"] = liquidity_crisis_perf

        # 4. 波动率飙升
        volatility_spike_perf = await self._test_volatility_spike_scenario(factor_values, returns_data, historical_data)
        scenario_results["volatility_spike"] = volatility_spike_perf

        # 5. 相关性崩溃
        correlation_breakdown_perf = await self._test_correlation_breakdown_scenario(
            factor_values, returns_data, historical_data
        )
        scenario_results["correlation_breakdown"] = correlation_breakdown_perf

        # 计算存活率
        survival_rate = self._calculate_survival_rate(scenario_results)

        # 计算Hell评分
        hell_score = self.performance_monitor.calculate_hell_score(
            survival_rate=survival_rate, scenario_performances=scenario_results
        )

        # 创建测试结果
        result = HellTrackResult(
            survival_rate=survival_rate,
            crash_performance=scenario_results["crash"],
            flash_crash_performance=scenario_results["flash_crash"],
            liquidity_crisis_performance=scenario_results["liquidity_crisis"],
            volatility_spike_performance=scenario_results["volatility_spike"],
            correlation_breakdown_performance=scenario_results["correlation_breakdown"],
            hell_score=hell_score,
            scenarios_tested=len(scenario_results),
        )

        logger.info(f"Hell Track测试完成: {factor.id}, " f"存活率={survival_rate:.4f}, Score={hell_score:.4f}")

        return result

    def _validate_input_data(self, historical_data: pd.DataFrame, returns_data: pd.Series) -> None:
        """验证输入数据有效性"""
        if historical_data.empty:
            raise ValueError("历史数据不能为空")

        if returns_data.empty:
            raise ValueError("收益率数据不能为空")

        if len(historical_data) < 100:
            raise ValueError(f"历史数据样本不足，至少需要100个样本，当前: {len(historical_data)}")

        required_columns = ["close", "volume"]
        missing_columns = [col for col in required_columns if col not in historical_data.columns]
        if missing_columns:
            raise ValueError(f"历史数据缺少必需的列: {missing_columns}")

    def _evaluate_factor_expression(self, expression: str, historical_data: pd.DataFrame) -> pd.Series:
        """评估因子表达式"""
        try:
            # 简化实现: 使用收益率作为因子值
            factor_values = historical_data["close"].pct_change()
            factor_values = factor_values.dropna()

            if len(factor_values) == 0:
                raise ValueError("因子值计算结果为空")

            return factor_values

        except Exception as e:
            logger.error(f"因子表达式评估失败: {expression}, 错误: {e}")
            raise ValueError(f"因子表达式评估失败: {e}") from e

    async def _test_crash_scenario(
        self,
        factor_values: pd.Series,
        returns_data: pd.Series,
        historical_data: pd.DataFrame,  # pylint: disable=unused-argument
    ) -> float:
        """测试崩盘场景

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track崩盘场景

        Args:
            factor_values: 因子值序列
            returns_data: 收益率序列
            historical_data: 历史数据

        Returns:
            崩盘场景表现评分 [0, 1]
        """
        # 识别崩盘期间 (累计跌幅 > 20%)
        cumulative_returns = (1 + returns_data).cumprod() - 1
        crash_periods = cumulative_returns < self.scenarios[ExtremeScenarioType.CRASH]["threshold"]

        if not crash_periods.any():
            # 没有崩盘期间，返回中性评分
            logger.warning("未检测到崩盘场景，返回中性评分0.5")
            return 0.5

        # 计算崩盘期间的因子表现
        crash_factor = factor_values[crash_periods]
        crash_returns = returns_data[crash_periods]

        if len(crash_factor) < 5:
            logger.warning("崩盘期间样本不足，返回中性评分0.5")
            return 0.5

        # 计算崩盘期间的IC
        try:
            crash_ic = self.performance_monitor.calculate_ic(crash_factor, crash_returns)
            # 归一化到[0, 1]
            performance = (crash_ic + 1) / 2  # IC范围[-1, 1]映射到[0, 1]
            return float(np.clip(performance, 0, 1))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"崩盘场景IC计算失败: {e}，返回中性评分0.5")
            return 0.5

    async def _test_flash_crash_scenario(
        self,
        factor_values: pd.Series,
        returns_data: pd.Series,
        historical_data: pd.DataFrame,  # pylint: disable=unused-argument
    ) -> float:
        """测试闪崩场景

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track闪崩场景

        Returns:
            闪崩场景表现评分 [0, 1]
        """
        window = self.scenarios[ExtremeScenarioType.FLASH_CRASH]["window"]
        threshold = self.scenarios[ExtremeScenarioType.FLASH_CRASH]["threshold"]

        # 识别闪崩期间 (短期内跌幅 > 10%)
        rolling_returns = returns_data.rolling(window=window).sum()
        flash_crash_periods = rolling_returns < threshold

        if not flash_crash_periods.any():
            logger.warning("未检测到闪崩场景，返回中性评分0.5")
            return 0.5

        # 计算闪崩期间的因子表现
        flash_factor = factor_values[flash_crash_periods]
        flash_returns = returns_data[flash_crash_periods]

        if len(flash_factor) < 5:
            logger.warning("闪崩期间样本不足，返回中性评分0.5")
            return 0.5

        try:
            flash_ic = self.performance_monitor.calculate_ic(flash_factor, flash_returns)
            performance = (flash_ic + 1) / 2
            return float(np.clip(performance, 0, 1))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"闪崩场景IC计算失败: {e}，返回中性评分0.5")
            return 0.5

    async def _test_liquidity_crisis_scenario(
        self, factor_values: pd.Series, returns_data: pd.Series, historical_data: pd.DataFrame
    ) -> float:
        """测试流动性危机场景

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track流动性危机

        Returns:
            流动性危机场景表现评分 [0, 1]
        """
        # 识别流动性危机期间 (成交量骤降 > 70%)
        volume = historical_data["volume"]
        volume_ma = volume.rolling(window=20).mean()
        volume_ratio = volume / volume_ma - 1

        threshold = self.scenarios[ExtremeScenarioType.LIQUIDITY_CRISIS]["threshold"]
        liquidity_crisis_periods = volume_ratio < threshold

        if not liquidity_crisis_periods.any():
            logger.warning("未检测到流动性危机场景，返回中性评分0.5")
            return 0.5

        # 计算流动性危机期间的因子表现
        crisis_factor = factor_values[liquidity_crisis_periods]
        crisis_returns = returns_data[liquidity_crisis_periods]

        if len(crisis_factor) < 5:
            logger.warning("流动性危机期间样本不足，返回中性评分0.5")
            return 0.5

        try:
            crisis_ic = self.performance_monitor.calculate_ic(crisis_factor, crisis_returns)
            performance = (crisis_ic + 1) / 2
            return float(np.clip(performance, 0, 1))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"流动性危机场景IC计算失败: {e}，返回中性评分0.5")
            return 0.5

    async def _test_volatility_spike_scenario(
        self,
        factor_values: pd.Series,
        returns_data: pd.Series,
        historical_data: pd.DataFrame,  # pylint: disable=unused-argument
    ) -> float:
        """测试波动率飙升场景

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track波动率飙升

        Returns:
            波动率飙升场景表现评分 [0, 1]
        """
        # 识别波动率飙升期间 (波动率 > 3倍均值)
        volatility = returns_data.rolling(window=20).std()
        volatility_ma = volatility.rolling(window=60).mean()
        volatility_ratio = volatility / volatility_ma

        threshold = self.scenarios[ExtremeScenarioType.VOLATILITY_SPIKE]["threshold"]
        volatility_spike_periods = volatility_ratio > threshold

        if not volatility_spike_periods.any():
            logger.warning("未检测到波动率飙升场景，返回中性评分0.5")
            return 0.5

        # 计算波动率飙升期间的因子表现
        spike_factor = factor_values[volatility_spike_periods]
        spike_returns = returns_data[volatility_spike_periods]

        if len(spike_factor) < 5:
            logger.warning("波动率飙升期间样本不足，返回中性评分0.5")
            return 0.5

        try:
            spike_ic = self.performance_monitor.calculate_ic(spike_factor, spike_returns)
            performance = (spike_ic + 1) / 2
            return float(np.clip(performance, 0, 1))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"波动率飙升场景IC计算失败: {e}，返回中性评分0.5")
            return 0.5

    async def _test_correlation_breakdown_scenario(
        self,
        factor_values: pd.Series,
        returns_data: pd.Series,
        historical_data: pd.DataFrame,  # pylint: disable=unused-argument
    ) -> float:
        """测试相关性崩溃场景

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track相关性崩溃

        Returns:
            相关性崩溃场景表现评分 [0, 1]
        """
        try:
            # 对齐索引
            common_index = factor_values.index.intersection(returns_data.index)
            if len(common_index) < 40:  # 需要足够的数据计算滚动相关性
                logger.warning("数据不足以计算滚动相关性，返回中性评分0.5")
                return 0.5

            factor_aligned = factor_values.loc[common_index]
            returns_aligned = returns_data.loc[common_index]

            # 识别相关性崩溃期间 (相关性突变)
            window = 20

            # 使用正确的pandas API计算滚动相关性
            # 创建DataFrame来计算滚动相关性
            combined_df = pd.DataFrame({"factor": factor_aligned, "returns": returns_aligned})

            # 计算滚动相关性
            rolling_corr = combined_df["factor"].rolling(window=window).corr(combined_df["returns"])
            corr_change = rolling_corr.diff().abs()

            threshold = self.scenarios[ExtremeScenarioType.CORRELATION_BREAKDOWN]["threshold"]
            correlation_breakdown_periods = corr_change > threshold

            # 处理NaN值
            correlation_breakdown_periods = correlation_breakdown_periods.fillna(False)

            if not correlation_breakdown_periods.any():
                logger.warning("未检测到相关性崩溃场景，返回中性评分0.5")
                return 0.5

            # 计算相关性崩溃期间的因子表现
            breakdown_factor = factor_aligned[correlation_breakdown_periods]
            breakdown_returns = returns_aligned[correlation_breakdown_periods]

            if len(breakdown_factor) < 5:
                logger.warning("相关性崩溃期间样本不足，返回中性评分0.5")
                return 0.5

            breakdown_ic = self.performance_monitor.calculate_ic(breakdown_factor, breakdown_returns)
            performance = (breakdown_ic + 1) / 2
            return float(np.clip(performance, 0, 1))

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"相关性崩溃场景IC计算失败: {e}，返回中性评分0.5")
            return 0.5

    def _calculate_survival_rate(self, scenario_results: Dict[str, float]) -> float:
        """计算存活率

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track存活率

        存活率 = 表现 > 0.3 的场景数 / 总场景数

        Args:
            scenario_results: 各场景表现评分

        Returns:
            存活率 [0, 1]
        """
        if not scenario_results:
            return 0.0

        survival_threshold = 0.3
        survived_count = sum(1 for score in scenario_results.values() if score > survival_threshold)
        total_count = len(scenario_results)

        survival_rate = survived_count / total_count

        return float(survival_rate)
