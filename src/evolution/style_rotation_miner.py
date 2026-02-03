"""风格轮动因子挖掘器

白皮书依据: 第四章 4.1.14 风格轮动因子挖掘
需求: 13.1-13.10
设计文档: design.md - Style Rotation Factor Mining

实现8个风格轮动算子，捕捉因子时机和拥挤效应。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from .unified_factor_mining_system import BaseMiner, FactorMetadata, MinerStatus, MinerType


class StyleType(Enum):
    """风格类型

    白皮书依据: 第四章 4.1.14 风格分类
    """

    VALUE = "value"
    GROWTH = "growth"
    SIZE = "size"
    MOMENTUM = "momentum"
    REVERSAL = "reversal"
    QUALITY = "quality"
    LOW_VOLATILITY = "low_volatility"
    DIVIDEND_YIELD = "dividend_yield"


@dataclass
class StyleMetrics:
    """风格指标

    Attributes:
        style_type: 风格类型
        spread: 风格价差
        premium: 风格溢价
        cycle_phase: 周期阶段
        crowding_index: 拥挤度指数
        rotation_signal: 轮动信号强度
    """

    style_type: StyleType
    spread: float
    premium: float
    cycle_phase: str
    crowding_index: float
    rotation_signal: float


class StyleRotationFactorMiner(BaseMiner):
    """风格轮动因子挖掘器

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘
    需求: 13.1-13.10

    实现8个风格轮动算子：
    1. value_growth_spread: 价值-成长价差
    2. size_premium_cycle: 规模溢价周期
    3. momentum_reversal_switch: 动量-反转切换
    4. quality_junk_rotation: 质量-垃圾轮动
    5. low_volatility_anomaly: 低波动异常
    6. dividend_yield_cycle: 股息率周期
    7. sector_rotation_signal: 行业轮动信号
    8. factor_crowding_index: 因子拥挤度指数

    Attributes:
        operators: 8个风格轮动算子
        crowding_threshold: 拥挤度预警阈值（默认0.8）
        lookback_window: 回溯窗口期（默认60天）
    """

    def __init__(self, crowding_threshold: float = 0.8, lookback_window: int = 60):
        """初始化风格轮动因子挖掘器

        白皮书依据: 第四章 4.1.14
        需求: 13.9, 13.10

        Args:
            crowding_threshold: 拥挤度预警阈值，默认0.8
            lookback_window: 回溯窗口期，默认60天

        Raises:
            ValueError: 当参数不在有效范围时
        """
        super().__init__(MinerType.STYLE_ROTATION, "StyleRotationFactorMiner")

        if not 0 < crowding_threshold <= 1:
            raise ValueError(f"crowding_threshold必须在 (0, 1]，当前: {crowding_threshold}")

        if lookback_window <= 0:
            raise ValueError(f"lookback_window必须 > 0，当前: {lookback_window}")

        self.crowding_threshold = crowding_threshold
        self.lookback_window = lookback_window
        self.operators = self._initialize_operators()

        logger.info(
            f"初始化风格轮动因子挖掘器 - "
            f"crowding_threshold={crowding_threshold}, "
            f"lookback_window={lookback_window}, "
            f"operators={len(self.operators)}"
        )

    def _initialize_operators(self) -> Dict[str, callable]:
        """初始化8个风格轮动算子

        白皮书依据: 第四章 4.1.14
        需求: 13.1-13.8

        Returns:
            算子字典
        """
        return {
            "value_growth_spread": self._value_growth_spread,
            "size_premium_cycle": self._size_premium_cycle,
            "momentum_reversal_switch": self._momentum_reversal_switch,
            "quality_junk_rotation": self._quality_junk_rotation,
            "low_volatility_anomaly": self._low_volatility_anomaly,
            "dividend_yield_cycle": self._dividend_yield_cycle,
            "sector_rotation_signal": self._sector_rotation_signal,
            "factor_crowding_index": self._factor_crowding_index,
        }

    def _value_growth_spread(self, data: pd.DataFrame) -> pd.Series:
        """计算价值-成长价差

        白皮书依据: 第四章 4.1.14 价值成长轮动
        需求: 13.1

        价值因子：市净率倒数（PB倒数）
        成长因子：营收增长率
        价差 = 价值因子收益 - 成长因子收益

        Args:
            data: 市场数据，包含pb_ratio, revenue_growth列

        Returns:
            价值-成长价差序列

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["pb_ratio", "revenue_growth", "returns"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        try:
            # 计算价值因子（PB倒数）
            value_factor = 1.0 / data["pb_ratio"].replace(0, np.nan)

            # 计算成长因子（营收增长率）
            growth_factor = data["revenue_growth"]

            # 计算因子收益（因子值与未来收益的相关性）
            window = min(self.lookback_window, len(data))

            value_returns = []
            growth_returns = []

            for i in range(window, len(data)):
                # 计算因子与未来收益的相关性
                value_ic = value_factor.iloc[i - window : i].corr(data["returns"].iloc[i - window : i])
                growth_ic = growth_factor.iloc[i - window : i].corr(data["returns"].iloc[i - window : i])

                value_returns.append(value_ic)
                growth_returns.append(growth_ic)

            # 计算价差
            spread = pd.Series(np.array(value_returns) - np.array(growth_returns), index=data.index[window:])

            # 填充前面的NaN值
            spread = spread.reindex(data.index, fill_value=0.0)

            logger.debug(f"价值-成长价差计算完成 - " f"均值={spread.mean():.4f}, " f"标准差={spread.std():.4f}")

            return spread

        except Exception as e:
            logger.error(f"价值-成长价差计算失败: {e}")
            raise

    def _size_premium_cycle(self, data: pd.DataFrame) -> pd.Series:
        """追踪规模溢价周期

        白皮书依据: 第四章 4.1.14 规模效应
        需求: 13.2

        规模溢价 = 小盘股收益 - 大盘股收益
        周期识别：使用移动平均识别周期阶段

        Args:
            data: 市场数据，包含market_cap, returns列

        Returns:
            规模溢价周期信号

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["market_cap", "returns"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        try:
            # 按市值分组（小盘vs大盘）
            market_cap_median = data["market_cap"].median()

            small_cap_mask = data["market_cap"] <= market_cap_median
            large_cap_mask = data["market_cap"] > market_cap_median

            # 计算小盘股和大盘股的平均收益
            small_cap_returns = data.loc[small_cap_mask, "returns"].groupby(data.index).mean()
            large_cap_returns = data.loc[large_cap_mask, "returns"].groupby(data.index).mean()

            # 计算规模溢价
            size_premium = small_cap_returns - large_cap_returns

            # 计算移动平均识别周期
            ma_short = size_premium.rolling(window=20).mean()
            ma_long = size_premium.rolling(window=60).mean()

            # 周期信号：短期均线 - 长期均线
            cycle_signal = ma_short - ma_long

            # 填充NaN值
            cycle_signal = cycle_signal.fillna(0.0)

            logger.debug(
                f"规模溢价周期计算完成 - "
                f"当前溢价={size_premium.iloc[-1]:.4f}, "
                f"周期信号={cycle_signal.iloc[-1]:.4f}"
            )

            return cycle_signal

        except Exception as e:
            logger.error(f"规模溢价周期计算失败: {e}")
            raise

    def _momentum_reversal_switch(self, data: pd.DataFrame) -> pd.Series:
        """识别动量-反转切换

        白皮书依据: 第四章 4.1.14 动量反转
        需求: 13.3

        动量因子：过去12个月收益
        反转因子：过去1个月收益（反向）
        切换信号：基于市场状态的动态权重

        Args:
            data: 市场数据，包含returns列

        Returns:
            动量-反转切换信号

        Raises:
            ValueError: 当必需列缺失时
        """
        if "returns" not in data.columns:
            raise ValueError("缺少必需列: returns")

        try:
            # 计算动量因子（12个月收益）
            momentum = data["returns"].rolling(window=252).sum()

            # 计算反转因子（1个月收益，反向）
            reversal = -data["returns"].rolling(window=21).sum()

            # 计算市场波动率（用于判断市场状态）
            volatility = data["returns"].rolling(window=60).std()
            volatility_ma = volatility.rolling(window=20).mean()

            # 高波动环境偏好反转，低波动环境偏好动量
            # 切换信号 = 动量权重 * 动量 + 反转权重 * 反转
            momentum_weight = 1.0 / (1.0 + (volatility / volatility_ma))
            reversal_weight = 1.0 - momentum_weight

            switch_signal = momentum_weight * momentum + reversal_weight * reversal

            # 标准化
            switch_signal = ((switch_signal - switch_signal.mean()) / switch_signal.std()).fillna(0.0)

            logger.debug(
                f"动量-反转切换计算完成 - "
                f"动量权重={momentum_weight.iloc[-1]:.4f}, "
                f"反转权重={reversal_weight.iloc[-1]:.4f}"
            )

            return switch_signal

        except Exception as e:
            logger.error(f"动量-反转切换计算失败: {e}")
            raise

    def _quality_junk_rotation(self, data: pd.DataFrame) -> pd.Series:
        """追踪质量-垃圾轮动

        白皮书依据: 第四章 4.1.14 质量因子
        需求: 13.4

        质量因子：ROE、低负债率
        垃圾因子：低ROE、高负债率
        轮动信号：质量溢价的周期性变化

        Args:
            data: 市场数据，包含roe, debt_ratio, returns列

        Returns:
            质量-垃圾轮动信号

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["roe", "debt_ratio", "returns"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        try:
            # 计算质量得分（ROE高、负债率低）
            quality_score = (data["roe"].rank(pct=True) + (1.0 - data["debt_ratio"].rank(pct=True))) / 2.0

            # 计算垃圾得分（ROE低、负债率高）
            1.0 - quality_score  # pylint: disable=w0104

            # 计算质量股和垃圾股的收益
            quality_threshold = quality_score.quantile(0.8)
            junk_threshold = quality_score.quantile(0.2)

            quality_returns = data.loc[quality_score >= quality_threshold, "returns"].groupby(data.index).mean()

            junk_returns = data.loc[quality_score <= junk_threshold, "returns"].groupby(data.index).mean()

            # 计算质量溢价
            quality_premium = quality_returns - junk_returns

            # 计算轮动信号（质量溢价的动量）
            rotation_signal = quality_premium.rolling(window=20).mean()

            # 标准化
            rotation_signal = ((rotation_signal - rotation_signal.mean()) / rotation_signal.std()).fillna(0.0)

            logger.debug(
                f"质量-垃圾轮动计算完成 - "
                f"质量溢价={quality_premium.iloc[-1]:.4f}, "
                f"轮动信号={rotation_signal.iloc[-1]:.4f}"
            )

            return rotation_signal

        except Exception as e:
            logger.error(f"质量-垃圾轮动计算失败: {e}")
            raise

    def _low_volatility_anomaly(self, data: pd.DataFrame) -> pd.Series:
        """分析低波动异常

        白皮书依据: 第四章 4.1.14 低波动异常
        需求: 13.5

        低波动异常：低波动股票往往有更高的风险调整收益
        异常强度：低波动组合相对高波动组合的超额收益

        Args:
            data: 市场数据，包含returns列

        Returns:
            低波动异常信号

        Raises:
            ValueError: 当必需列缺失时
        """
        if "returns" not in data.columns:
            raise ValueError("缺少必需列: returns")

        try:
            # 计算滚动波动率
            volatility = data["returns"].rolling(window=60).std()

            # 按波动率分组
            vol_quantiles = volatility.groupby(data.index).quantile([0.2, 0.8])

            low_vol_returns = []
            high_vol_returns = []

            for date in data.index.unique():
                if date not in vol_quantiles.index:
                    continue

                low_vol_threshold = vol_quantiles.loc[date, 0.2]
                high_vol_threshold = vol_quantiles.loc[date, 0.8]

                date_data = data.loc[data.index == date]
                date_vol = volatility.loc[volatility.index == date]

                # 低波动组合收益
                low_vol_mask = date_vol <= low_vol_threshold
                if low_vol_mask.sum() > 0:
                    low_vol_ret = date_data.loc[low_vol_mask, "returns"].mean()
                    low_vol_returns.append(low_vol_ret)
                else:
                    low_vol_returns.append(0.0)

                # 高波动组合收益
                high_vol_mask = date_vol >= high_vol_threshold
                if high_vol_mask.sum() > 0:
                    high_vol_ret = date_data.loc[high_vol_mask, "returns"].mean()
                    high_vol_returns.append(high_vol_ret)
                else:
                    high_vol_returns.append(0.0)

            # 计算低波动异常（低波动超额收益）
            anomaly = pd.Series(
                np.array(low_vol_returns) - np.array(high_vol_returns),
                index=data.index.unique()[: len(low_vol_returns)],
            )

            # 重新索引到原始数据
            anomaly = anomaly.reindex(data.index, method="ffill").fillna(0.0)

            logger.debug(f"低波动异常计算完成 - " f"异常强度={anomaly.iloc[-1]:.4f}")

            return anomaly

        except Exception as e:
            logger.error(f"低波动异常计算失败: {e}")
            raise

    def _dividend_yield_cycle(self, data: pd.DataFrame) -> pd.Series:
        """追踪股息率周期

        白皮书依据: 第四章 4.1.14 股息率因子
        需求: 13.6

        股息率周期：高股息率股票的相对表现周期
        周期识别：基于利率环境和市场状态

        Args:
            data: 市场数据，包含dividend_yield, returns列

        Returns:
            股息率周期信号

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["dividend_yield", "returns"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        try:
            # 按股息率分组
            div_yield_median = data["dividend_yield"].median()

            high_div_mask = data["dividend_yield"] >= div_yield_median
            low_div_mask = data["dividend_yield"] < div_yield_median

            # 计算高股息和低股息组合收益
            high_div_returns = data.loc[high_div_mask, "returns"].groupby(data.index).mean()
            low_div_returns = data.loc[low_div_mask, "returns"].groupby(data.index).mean()

            # 计算股息率溢价
            div_premium = high_div_returns - low_div_returns

            # 计算周期信号（使用双移动平均）
            ma_fast = div_premium.rolling(window=20).mean()
            ma_slow = div_premium.rolling(window=60).mean()

            cycle_signal = ma_fast - ma_slow

            # 标准化
            cycle_signal = ((cycle_signal - cycle_signal.mean()) / cycle_signal.std()).fillna(0.0)

            logger.debug(
                f"股息率周期计算完成 - "
                f"股息溢价={div_premium.iloc[-1]:.4f}, "
                f"周期信号={cycle_signal.iloc[-1]:.4f}"
            )

            return cycle_signal

        except Exception as e:
            logger.error(f"股息率周期计算失败: {e}")
            raise

    def _sector_rotation_signal(self, data: pd.DataFrame) -> pd.Series:
        """识别行业轮动信号

        白皮书依据: 第四章 4.1.14 行业轮动
        需求: 13.7

        行业轮动：不同行业在经济周期中的相对表现
        轮动信号：基于行业动量和相对强度

        Args:
            data: 市场数据，包含sector, returns列

        Returns:
            行业轮动信号

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["sector", "returns"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        try:
            # 计算每个行业的收益
            sector_returns = data.groupby(["sector", data.index])["returns"].mean()

            # 计算行业动量（过去3个月收益）
            sector_momentum = {}
            for sector in data["sector"].unique():
                if sector in sector_returns.index.get_level_values(0):
                    sector_data = sector_returns[sector]
                    momentum = sector_data.rolling(window=60).sum()
                    sector_momentum[sector] = momentum

            # 计算相对强度（行业收益 - 市场平均收益）
            market_returns = data.groupby(data.index)["returns"].mean()

            sector_relative_strength = {}
            for sector, momentum in sector_momentum.items():
                rs = momentum - market_returns.reindex(momentum.index)
                sector_relative_strength[sector] = rs

            # 计算轮动信号（最强行业 - 最弱行业）
            rotation_signals = []
            for date in data.index.unique():
                date_rs = {}
                for sector, rs in sector_relative_strength.items():
                    if date in rs.index:
                        date_rs[sector] = rs.loc[date]

                if date_rs:
                    strongest = max(date_rs.values())
                    weakest = min(date_rs.values())
                    rotation_signals.append(strongest - weakest)
                else:
                    rotation_signals.append(0.0)

            # 创建信号序列
            rotation_signal = pd.Series(rotation_signals, index=data.index.unique()[: len(rotation_signals)])

            # 重新索引到原始数据
            rotation_signal = rotation_signal.reindex(data.index, method="ffill").fillna(0.0)

            logger.debug(f"行业轮动信号计算完成 - " f"当前信号={rotation_signal.iloc[-1]:.4f}")

            return rotation_signal

        except Exception as e:
            logger.error(f"行业轮动信号计算失败: {e}")
            raise

    def _factor_crowding_index(self, data: pd.DataFrame) -> pd.Series:
        """计算因子拥挤度指数

        白皮书依据: 第四章 4.1.14 因子拥挤度
        需求: 13.8, 13.10

        拥挤度指标：
        1. 因子暴露集中度
        2. 因子收益波动率
        3. 因子换手率

        当拥挤度 > 0.8 时发出预警

        Args:
            data: 市场数据，包含factor_exposure, returns列

        Returns:
            因子拥挤度指数

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["factor_exposure", "returns"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        try:
            # 1. 计算因子暴露集中度（使用Herfindahl指数）
            exposure_squared = data["factor_exposure"] ** 2
            concentration = exposure_squared.groupby(data.index).sum()
            concentration = concentration / (data.groupby(data.index)["factor_exposure"].count())

            # 2. 计算因子收益波动率
            factor_returns = (data["factor_exposure"] * data["returns"]).groupby(data.index).sum()
            volatility = factor_returns.rolling(window=20).std()
            volatility_normalized = ((volatility - volatility.mean()) / volatility.std()).fillna(0.0)

            # 3. 计算因子换手率（暴露变化率）
            exposure_change = data["factor_exposure"].groupby(data.index).apply(lambda x: x.diff().abs().sum())
            turnover = exposure_change.rolling(window=20).mean()
            turnover_normalized = ((turnover - turnover.mean()) / turnover.std()).fillna(0.0)

            # 综合拥挤度指数（0-1范围）
            crowding_index = (
                0.4 * concentration + 0.3 * volatility_normalized.clip(0, 1) + 0.3 * turnover_normalized.clip(0, 1)
            )

            # 重新索引到原始数据
            crowding_index = crowding_index.reindex(data.index, method="ffill").fillna(0.0)

            # 检查拥挤度预警
            if crowding_index.iloc[-1] > self.crowding_threshold:
                logger.warning(
                    f"因子拥挤度预警！当前拥挤度={crowding_index.iloc[-1]:.4f} " f"> 阈值={self.crowding_threshold}"
                )

            logger.debug(f"因子拥挤度计算完成 - " f"拥挤度={crowding_index.iloc[-1]:.4f}")

            return crowding_index

        except Exception as e:
            logger.error(f"因子拥挤度计算失败: {e}")
            raise

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, **kwargs) -> List[FactorMetadata]:
        """挖掘风格轮动因子

        白皮书依据: 第四章 4.1.14
        需求: 13.1-13.10

        Args:
            data: 市场数据DataFrame
            returns: 收益率序列
            **kwargs: 额外参数

        Returns:
            发现的因子列表

        Raises:
            ValueError: 当输入数据无效时
        """
        if data.empty:
            raise ValueError("输入数据不能为空")

        if len(returns) == 0:
            raise ValueError("收益率数据不能为空")

        try:
            self.metadata.status = MinerStatus.RUNNING
            logger.info("开始挖掘风格轮动因子...")

            # 确保数据包含returns列
            if "returns" not in data.columns:
                data = data.copy()
                data["returns"] = returns

            factors = []

            # 执行所有8个算子
            for operator_name, operator_func in self.operators.items():
                try:
                    logger.info(f"执行算子: {operator_name}")

                    # 执行算子
                    factor_values = operator_func(data)

                    # 计算因子指标
                    ic = self._calculate_ic(factor_values, returns)
                    ir = self._calculate_ir(factor_values, returns)
                    sharpe = self._calculate_sharpe(factor_values, returns)

                    # 计算综合适应度
                    fitness = abs(ic) * 0.4 + abs(ir) * 0.3 + abs(sharpe) * 0.3

                    # 创建因子元数据
                    factor = FactorMetadata(
                        factor_id=f"style_rotation_{operator_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        factor_name=f"StyleRotation_{operator_name}",
                        factor_type=MinerType.STYLE_ROTATION,
                        data_source="market_data",
                        discovery_date=datetime.now(),
                        discoverer=self.miner_name,
                        expression=operator_name,
                        fitness=fitness,
                        ic=ic,
                        ir=ir,
                        sharpe=sharpe,
                    )

                    factors.append(factor)

                    logger.info(
                        f"算子 {operator_name} 完成 - "
                        f"IC={ic:.4f}, IR={ir:.4f}, Sharpe={sharpe:.4f}, "
                        f"Fitness={fitness:.4f}"
                    )

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"算子 {operator_name} 执行失败: {e}")
                    continue

            # 更新元数据
            self.metadata.status = MinerStatus.COMPLETED
            self.metadata.total_factors_discovered += len(factors)
            self.metadata.last_run_time = datetime.now()

            if factors:
                avg_fitness = sum(f.fitness for f in factors) / len(factors)
                self.metadata.average_fitness = (
                    self.metadata.average_fitness * (self.metadata.total_factors_discovered - len(factors))
                    + avg_fitness * len(factors)
                ) / self.metadata.total_factors_discovered

            logger.info(
                f"风格轮动因子挖掘完成 - "
                f"发现因子数={len(factors)}, "
                f"平均适应度={self.metadata.average_fitness:.4f}"
            )

            return factors

        except Exception as e:
            self.metadata.status = MinerStatus.FAILED
            self.metadata.error_count += 1
            self.metadata.last_error = str(e)
            self.metadata.is_healthy = self.metadata.error_count < 5
            logger.error(f"风格轮动因子挖掘失败: {e}")
            raise

    def _calculate_ic(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息系数（IC）

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            信息系数
        """
        try:
            # 对齐索引
            common_index = factor.index.intersection(returns.index)
            if len(common_index) == 0:
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            # 计算Spearman相关系数
            ic = factor_aligned.corr(returns_aligned, method="spearman")

            return ic if not np.isnan(ic) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IC计算失败: {e}")
            return 0.0

    def _calculate_ir(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息比率（IR）

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            信息比率
        """
        try:
            # 计算滚动IC
            window = min(60, len(factor))
            rolling_ic = []

            for i in range(window, len(factor)):
                ic = factor.iloc[i - window : i].corr(returns.iloc[i - window : i], method="spearman")
                if not np.isnan(ic):
                    rolling_ic.append(ic)

            if len(rolling_ic) == 0:
                return 0.0

            # IR = IC均值 / IC标准差
            ic_mean = np.mean(rolling_ic)
            ic_std = np.std(rolling_ic)

            ir = ic_mean / ic_std if ic_std > 0 else 0.0

            return ir if not np.isnan(ir) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IR计算失败: {e}")
            return 0.0

    def _calculate_sharpe(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算夏普比率

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            夏普比率
        """
        try:
            # 对齐索引
            common_index = factor.index.intersection(returns.index)
            if len(common_index) == 0:
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            # 计算因子收益（因子值 * 收益率）
            factor_returns = factor_aligned * returns_aligned

            # 夏普比率 = 收益均值 / 收益标准差
            mean_return = factor_returns.mean()
            std_return = factor_returns.std()

            sharpe = mean_return / std_return if std_return > 0 else 0.0

            # 年化（假设日频数据）
            sharpe_annualized = sharpe * np.sqrt(252)

            return sharpe_annualized if not np.isnan(sharpe_annualized) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Sharpe计算失败: {e}")
            return 0.0
