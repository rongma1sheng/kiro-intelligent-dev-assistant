"""量价关系算子注册表

白皮书依据: 第四章 4.1.11 - 量价关系因子挖掘器
版本: v1.0.0

本模块实现12个量价关系专用算子:
1. volume_price_correlation - 量价相关性
2. obv_divergence - OBV背离
3. vwap_deviation - VWAP偏离度
4. volume_weighted_momentum - 成交量加权动量
5. price_volume_trend - 价量趋势
6. accumulation_distribution - 累积派发
7. money_flow_index - 资金流量指数
8. volume_surge_pattern - 成交量激增模式
9. price_volume_breakout - 价量突破
10. volume_profile_support - 成交量剖面支撑
11. tick_volume_analysis - Tick成交量分析
12. volume_weighted_rsi - 成交量加权RSI
"""

from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger


class OperatorError(Exception):
    """算子计算错误"""


class DataQualityError(Exception):
    """数据质量错误"""


class PriceVolumeOperatorRegistry:
    """量价关系算子注册表

    白皮书依据: 第四章 4.1.11 - 量价关系因子挖掘器

    提供:
    1. 12个量价关系算子的注册机制
    2. 算子验证和错误处理
    3. 数据质量检查
    4. 算子计算与日志记录

    Attributes:
        operators: 算子名称到计算函数的映射
        operator_metadata: 算子名称到元数据的映射
    """

    def __init__(self):
        """初始化量价关系算子注册表

        白皮书依据: 第四章 4.1.11 - 量价关系因子挖掘器
        """
        self.operators: Dict[str, Callable] = {}
        self.operator_metadata: Dict[str, Dict[str, Any]] = {}

        # 注册所有算子
        self._register_all_operators()

        logger.info(f"PriceVolumeOperatorRegistry初始化完成，共{len(self.operators)}个算子")

    def _register_all_operators(self) -> None:
        """注册所有12个量价关系算子

        白皮书依据: 第四章 4.1.11 - 量价关系因子挖掘器
        """
        # 1. 量价相关性
        self._register_operator(
            name="volume_price_correlation",
            func=self.volume_price_correlation,
            category="correlation",
            description="量价相关性",
            formula="rolling_corr(price, volume, window)",
        )

        # 2. OBV背离
        self._register_operator(
            name="obv_divergence",
            func=self.obv_divergence,
            category="divergence",
            description="OBV背离检测",
            formula="detect_divergence(price, obv)",
        )

        # 3. VWAP偏离度
        self._register_operator(
            name="vwap_deviation",
            func=self.vwap_deviation,
            category="deviation",
            description="VWAP偏离度",
            formula="(price - vwap) / vwap",
        )

        # 4. 成交量加权动量
        self._register_operator(
            name="volume_weighted_momentum",
            func=self.volume_weighted_momentum,
            category="momentum",
            description="成交量加权动量",
            formula="momentum * volume_weight",
        )

        # 5. 价量趋势
        self._register_operator(
            name="price_volume_trend",
            func=self.price_volume_trend,
            category="trend",
            description="价量趋势",
            formula="cumsum((close - prev_close) / prev_close * volume)",
        )

        # 6. 累积派发
        self._register_operator(
            name="accumulation_distribution",
            func=self.accumulation_distribution,
            category="flow",
            description="累积派发线",
            formula="cumsum(((close - low) - (high - close)) / (high - low) * volume)",
        )

        # 7. 资金流量指数
        self._register_operator(
            name="money_flow_index",
            func=self.money_flow_index,
            category="flow",
            description="资金流量指数",
            formula="100 - 100 / (1 + positive_flow / negative_flow)",
        )

        # 8. 成交量激增模式
        self._register_operator(
            name="volume_surge_pattern",
            func=self.volume_surge_pattern,
            category="pattern",
            description="成交量激增模式",
            formula="volume > volume_ma * surge_multiplier",
        )

        # 9. 价量突破
        self._register_operator(
            name="price_volume_breakout",
            func=self.price_volume_breakout,
            category="breakout",
            description="价量突破信号",
            formula="price_breakout & volume_surge",
        )

        # 10. 成交量剖面支撑
        self._register_operator(
            name="volume_profile_support",
            func=self.volume_profile_support,
            category="support",
            description="成交量剖面支撑位",
            formula="price_level_with_max_volume",
        )

        # 11. Tick成交量分析
        self._register_operator(
            name="tick_volume_analysis",
            func=self.tick_volume_analysis,
            category="tick",
            description="Tick成交量分析",
            formula="uptick_volume - downtick_volume",
        )

        # 12. 成交量加权RSI
        self._register_operator(
            name="volume_weighted_rsi",
            func=self.volume_weighted_rsi,
            category="momentum",
            description="成交量加权RSI",
            formula="rsi(price_change * volume_weight)",
        )

    def _register_operator(  # pylint: disable=too-many-positional-arguments
        self, name: str, func: Callable, category: str, description: str, formula: str
    ) -> None:  # pylint: disable=too-many-positional-arguments
        """注册算子及其元数据

        Args:
            name: 算子名称
            func: 算子计算函数
            category: 算子类别
            description: 算子描述
            formula: 数学公式
        """
        self.operators[name] = func
        self.operator_metadata[name] = {"category": category, "description": description, "formula": formula}

        logger.debug(f"注册算子: {name} ({category})")

    def get_operator(self, name: str) -> Optional[Callable]:
        """根据名称获取算子函数

        Args:
            name: 算子名称

        Returns:
            算子函数，如果不存在则返回None
        """
        return self.operators.get(name)

    def get_operator_names(self) -> list[str]:
        """获取所有算子名称列表

        Returns:
            算子名称列表
        """
        return list(self.operators.keys())

    def get_operators_by_category(self, category: str) -> Dict[str, Callable]:
        """获取指定类别的所有算子

        Args:
            category: 类别名称

        Returns:
            算子名称到函数的映射
        """
        return {
            name: func for name, func in self.operators.items() if self.operator_metadata[name]["category"] == category
        }

    def validate_operator_input(self, data: pd.DataFrame, required_columns: list[str]) -> None:
        """验证算子输入数据

        白皮书依据: 第四章 4.1 - 数据质量要求

        Args:
            data: 输入数据
            required_columns: 必需的列名

        Raises:
            OperatorError: 验证失败时
        """
        if data.empty:
            raise OperatorError("输入数据为空")

        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise OperatorError(f"缺少必需列: {missing_columns}")

        # 检查过多的NaN值 (>50%阈值)
        for col in required_columns:
            nan_ratio = data[col].isna().sum() / len(data)
            if nan_ratio > 0.5:
                raise DataQualityError(f"列 {col} 有 {nan_ratio:.1%} NaN值 (阈值: 50%)")

    # ========================================================================
    # 算子实现 (12个)
    # ========================================================================

    def volume_price_correlation(
        self, data: pd.DataFrame, price_col: str = "close", volume_col: str = "volume", window: int = 20
    ) -> pd.Series:
        """计算量价相关性

        白皮书依据: 第四章 4.1.11 - volume_price_correlation
        公式: rolling_corr(price, volume, window)

        量价相关性衡量价格和成交量的同步性。
        正相关表示量价配合良好，负相关可能预示反转。

        Args:
            data: 包含价格和成交量的数据框
            price_col: 价格列名
            volume_col: 成交量列名
            window: 滚动窗口大小（默认20天）

        Returns:
            量价相关性序列 [-1, 1]

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [price_col, volume_col])

            price = data[price_col]
            volume = data[volume_col]

            # 计算滚动相关系数
            correlation = price.rolling(window=window).corr(volume)

            logger.debug(f"计算volume_price_correlation: mean={correlation.mean():.4f}")

            return correlation

        except Exception as e:
            logger.error(f"volume_price_correlation计算失败: {e}")
            raise OperatorError(f"volume_price_correlation失败: {e}") from e

    def obv_divergence(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 20,
        threshold: float = 0.3,
    ) -> pd.Series:
        """检测OBV背离

        白皮书依据: 第四章 4.1.11 - obv_divergence
        公式: detect_divergence(price, obv)

        OBV背离是重要的反转信号：
        - 顶背离：价格创新高，OBV未创新高（看跌）
        - 底背离：价格创新低，OBV未创新低（看涨）

        Args:
            data: 包含价格和成交量的数据框
            price_col: 价格列名
            volume_col: 成交量列名
            window: 检测窗口
            threshold: 背离阈值

        Returns:
            背离信号 (1=顶背离, -1=底背离, 0=无背离)

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [price_col, volume_col])

            price = data[price_col]
            data[volume_col]  # pylint: disable=w0104

            # 计算OBV
            obv = self.on_balance_volume(data, price_col, volume_col)

            # 初始化背离信号
            divergence = pd.Series(0, index=data.index)

            # 计算滚动最高价和最低价
            price_high = price.rolling(window=window).max()
            price_low = price.rolling(window=window).min()

            # 计算OBV滚动最高和最低
            obv_high = obv.rolling(window=window).max()
            obv_low = obv.rolling(window=window).min()

            # 检测顶背离
            price_new_high = price >= price_high
            obv_not_high = obv < obv_high * (1 - threshold)
            divergence[price_new_high & obv_not_high] = 1

            # 检测底背离
            price_new_low = price <= price_low
            obv_not_low = obv > obv_low * (1 + threshold)
            divergence[price_new_low & obv_not_low] = -1

            logger.debug(
                f"计算obv_divergence: " f"顶背离={(divergence == 1).sum()}, " f"底背离={(divergence == -1).sum()}"
            )

            return divergence

        except Exception as e:
            logger.error(f"obv_divergence计算失败: {e}")
            raise OperatorError(f"obv_divergence失败: {e}") from e

    def vwap_deviation(
        self, data: pd.DataFrame, price_col: str = "close", volume_col: str = "volume", window: int = 20
    ) -> pd.Series:
        """计算VWAP偏离度

        白皮书依据: 第四章 4.1.11 - vwap_deviation
        公式: (price - vwap) / vwap

        VWAP偏离度衡量当前价格相对于成交量加权平均价的偏离程度。
        正偏离表示价格高于VWAP，负偏离表示价格低于VWAP。

        Args:
            data: 包含价格和成交量的数据框
            price_col: 价格列名
            volume_col: 成交量列名
            window: 滚动窗口大小

        Returns:
            VWAP偏离度序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [price_col, volume_col])

            price = data[price_col]
            volume = data[volume_col]

            # 计算VWAP
            typical_price = price  # 简化版本，完整版应使用(high+low+close)/3
            vwap = (typical_price * volume).rolling(window=window).sum() / volume.rolling(window=window).sum()

            # 计算偏离度
            deviation = (price - vwap) / (vwap + 1e-8)

            logger.debug(f"计算vwap_deviation: mean={deviation.mean():.4f}")

            return deviation

        except Exception as e:
            logger.error(f"vwap_deviation计算失败: {e}")
            raise OperatorError(f"vwap_deviation失败: {e}") from e

    def volume_weighted_momentum(
        self, data: pd.DataFrame, price_col: str = "close", volume_col: str = "volume", window: int = 20
    ) -> pd.Series:
        """计算成交量加权动量

        白皮书依据: 第四章 4.1.11 - volume_weighted_momentum
        公式: momentum * volume_weight

        成交量加权动量结合价格动量和成交量权重，
        成交量大的动量更可靠。

        Args:
            data: 包含价格和成交量的数据框
            price_col: 价格列名
            volume_col: 成交量列名
            window: 滚动窗口大小

        Returns:
            成交量加权动量序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [price_col, volume_col])

            price = data[price_col]
            volume = data[volume_col]

            # 计算价格动量
            momentum = price.pct_change(window)

            # 计算成交量权重（归一化）
            volume_ma = volume.rolling(window=window).mean()
            volume_weight = volume / (volume_ma + 1e-8)

            # 成交量加权动量
            weighted_momentum = momentum * volume_weight

            logger.debug(f"计算volume_weighted_momentum: mean={weighted_momentum.mean():.4f}")

            return weighted_momentum

        except Exception as e:
            logger.error(f"volume_weighted_momentum计算失败: {e}")
            raise OperatorError(f"volume_weighted_momentum失败: {e}") from e

    def price_volume_trend(self, data: pd.DataFrame, close_col: str = "close", volume_col: str = "volume") -> pd.Series:
        """计算价量趋势

        白皮书依据: 第四章 4.1.11 - price_volume_trend
        公式: cumsum((close - prev_close) / prev_close * volume)

        价量趋势(PVT)累积价格变化率与成交量的乘积，
        反映资金流向的累积效应。

        Args:
            data: 包含价格和成交量的数据框
            close_col: 收盘价列名
            volume_col: 成交量列名

        Returns:
            价量趋势序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [close_col, volume_col])

            close = data[close_col]
            volume = data[volume_col]

            # 计算价格变化率
            price_change_pct = close.pct_change()

            # 价量趋势 = 累积(价格变化率 * 成交量)
            pvt = (price_change_pct * volume).cumsum()

            logger.debug(f"计算price_volume_trend: final_value={pvt.iloc[-1]:.2f}")

            return pvt

        except Exception as e:
            logger.error(f"price_volume_trend计算失败: {e}")
            raise OperatorError(f"price_volume_trend失败: {e}") from e

    def accumulation_distribution(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
    ) -> pd.Series:
        """计算累积派发线

        白皮书依据: 第四章 4.1.11 - accumulation_distribution
        公式: cumsum(((close - low) - (high - close)) / (high - low) * volume)

        累积派发线(A/D Line)衡量资金的累积和派发。
        上升表示累积（买入），下降表示派发（卖出）。

        Args:
            data: 包含价格和成交量的数据框
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名

        Returns:
            累积派发线序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [high_col, low_col, close_col, volume_col])

            high = data[high_col]
            low = data[low_col]
            close = data[close_col]
            volume = data[volume_col]

            # 计算资金流乘数
            clv = ((close - low) - (high - close)) / (high - low + 1e-8)

            # 累积派发线
            ad_line = (clv * volume).cumsum()

            logger.debug(f"计算accumulation_distribution: final_value={ad_line.iloc[-1]:.2f}")

            return ad_line

        except Exception as e:
            logger.error(f"accumulation_distribution计算失败: {e}")
            raise OperatorError(f"accumulation_distribution失败: {e}") from e

    def money_flow_index(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
        volume_col: str = "volume",
        window: int = 14,
    ) -> pd.Series:
        """计算资金流量指数

        白皮书依据: 第四章 4.1.11 - money_flow_index
        公式: 100 - 100 / (1 + positive_flow / negative_flow)

        资金流量指数(MFI)是成交量加权的RSI，范围[0, 100]。
        MFI > 80表示超买，MFI < 20表示超卖。

        Args:
            data: 包含价格和成交量的数据框
            high_col: 最高价列名
            low_col: 最低价列名
            close_col: 收盘价列名
            volume_col: 成交量列名
            window: 滚动窗口大小（默认14天）

        Returns:
            资金流量指数序列 [0, 100]

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [high_col, low_col, close_col, volume_col])

            high = data[high_col]
            low = data[low_col]
            close = data[close_col]
            volume = data[volume_col]

            # 计算典型价格
            typical_price = (high + low + close) / 3

            # 计算资金流
            money_flow = typical_price * volume

            # 区分正负资金流
            positive_flow = pd.Series(0.0, index=data.index)
            negative_flow = pd.Series(0.0, index=data.index)

            price_change = typical_price.diff()
            positive_flow[price_change > 0] = money_flow[price_change > 0]
            negative_flow[price_change < 0] = money_flow[price_change < 0]

            # 计算滚动资金流比率
            positive_flow_sum = positive_flow.rolling(window=window).sum()
            negative_flow_sum = negative_flow.rolling(window=window).sum()

            # 计算MFI
            money_ratio = positive_flow_sum / (negative_flow_sum + 1e-8)
            mfi = 100 - (100 / (1 + money_ratio))

            logger.debug(f"计算money_flow_index: mean={mfi.mean():.2f}")

            return mfi

        except Exception as e:
            logger.error(f"money_flow_index计算失败: {e}")
            raise OperatorError(f"money_flow_index失败: {e}") from e

    def volume_surge_pattern(
        self, data: pd.DataFrame, volume_col: str = "volume", window: int = 20, multiplier: float = 2.0
    ) -> pd.Series:
        """检测成交量激增模式

        白皮书依据: 第四章 4.1.11 - volume_surge_pattern
        公式: volume > volume_ma * surge_multiplier

        成交量激增通常预示重要事件或趋势变化。

        Args:
            data: 包含成交量的数据框
            volume_col: 成交量列名
            window: 滚动窗口大小
            multiplier: 激增倍数阈值（默认2倍）

        Returns:
            成交量激增信号 (1=激增, 0=正常)

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [volume_col])

            volume = data[volume_col]

            # 计算成交量均值
            volume_ma = volume.rolling(window=window).mean()

            # 检测激增
            surge = (volume > volume_ma * multiplier).astype(int)

            logger.debug(f"计算volume_surge_pattern: surge_count={surge.sum()}")

            return surge

        except Exception as e:
            logger.error(f"volume_surge_pattern计算失败: {e}")
            raise OperatorError(f"volume_surge_pattern失败: {e}") from e

    def price_volume_breakout(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 20,
        volume_multiplier: float = 1.5,
    ) -> pd.Series:
        """检测价量突破

        白皮书依据: 第四章 4.1.11 - price_volume_breakout
        公式: price_breakout & volume_surge

        价量突破是价格突破关键位置且伴随成交量放大，
        是强势信号。

        Args:
            data: 包含价格和成交量的数据框
            price_col: 价格列名
            volume_col: 成交量列名
            window: 滚动窗口大小
            volume_multiplier: 成交量放大倍数

        Returns:
            突破信号 (1=向上突破, -1=向下突破, 0=无突破)

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [price_col, volume_col])

            price = data[price_col]
            volume = data[volume_col]

            # 计算价格突破
            price_high = price.rolling(window=window).max()
            price_low = price.rolling(window=window).min()

            price_breakout_up = price > price_high.shift(1)
            price_breakout_down = price < price_low.shift(1)

            # 计算成交量放大
            volume_ma = volume.rolling(window=window).mean()
            volume_surge = volume > volume_ma * volume_multiplier

            # 价量突破
            breakout = pd.Series(0, index=data.index)
            breakout[price_breakout_up & volume_surge] = 1
            breakout[price_breakout_down & volume_surge] = -1

            logger.debug(
                f"计算price_volume_breakout: "
                f"向上突破={(breakout == 1).sum()}, "
                f"向下突破={(breakout == -1).sum()}"
            )

            return breakout

        except Exception as e:
            logger.error(f"price_volume_breakout计算失败: {e}")
            raise OperatorError(f"price_volume_breakout失败: {e}") from e

    def volume_profile_support(
        self, data: pd.DataFrame, price_col: str = "close", volume_col: str = "volume", bins: int = 50
    ) -> pd.Series:
        """计算成交量剖面支撑位

        白皮书依据: 第四章 4.1.11 - volume_profile_support
        公式: price_level_with_max_volume

        成交量剖面分析价格区间的成交量分布，
        成交量最大的价格区间通常是重要支撑/阻力位。

        Args:
            data: 包含价格和成交量的数据框
            price_col: 价格列名
            volume_col: 成交量列名
            bins: 价格区间数量

        Returns:
            支撑强度序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [price_col, volume_col])

            price = data[price_col]
            volume = data[volume_col]

            # 计算价格区间
            price_min = price.min()
            price_max = price.max()
            price_bins = np.linspace(price_min, price_max, bins + 1)

            # 计算每个价格区间的成交量
            volume_profile = pd.Series(0.0, index=data.index)

            for i in range(len(price_bins) - 1):
                bin_low = price_bins[i]
                bin_high = price_bins[i + 1]

                # 找到在该价格区间的数据
                in_bin = (price >= bin_low) & (price < bin_high)
                bin_volume = volume[in_bin].sum()

                # 将该区间的成交量分配给该区间内的所有点
                volume_profile[in_bin] = bin_volume

            # 归一化
            volume_profile = volume_profile / (volume_profile.max() + 1e-8)

            logger.debug(f"计算volume_profile_support: mean={volume_profile.mean():.4f}")

            return volume_profile

        except Exception as e:
            logger.error(f"volume_profile_support计算失败: {e}")
            raise OperatorError(f"volume_profile_support失败: {e}") from e

    def tick_volume_analysis(
        self, data: pd.DataFrame, close_col: str = "close", volume_col: str = "volume"
    ) -> pd.Series:
        """Tick成交量分析

        白皮书依据: 第四章 4.1.11 - tick_volume_analysis
        公式: uptick_volume - downtick_volume

        Tick成交量分析区分上涨成交量和下跌成交量，
        反映买卖力量对比。

        Args:
            data: 包含价格和成交量的数据框
            close_col: 收盘价列名
            volume_col: 成交量列名

        Returns:
            Tick成交量差值序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [close_col, volume_col])

            close = data[close_col]
            volume = data[volume_col]

            # 计算价格变化
            price_change = close.diff()

            # 区分上涨和下跌成交量
            uptick_volume = pd.Series(0.0, index=data.index)
            downtick_volume = pd.Series(0.0, index=data.index)

            uptick_volume[price_change > 0] = volume[price_change > 0]
            downtick_volume[price_change < 0] = volume[price_change < 0]

            # Tick成交量差值
            tick_volume_diff = uptick_volume - downtick_volume

            logger.debug(f"计算tick_volume_analysis: mean={tick_volume_diff.mean():.2f}")

            return tick_volume_diff

        except Exception as e:
            logger.error(f"tick_volume_analysis计算失败: {e}")
            raise OperatorError(f"tick_volume_analysis失败: {e}") from e

    def volume_weighted_rsi(
        self, data: pd.DataFrame, close_col: str = "close", volume_col: str = "volume", window: int = 14
    ) -> pd.Series:
        """计算成交量加权RSI

        白皮书依据: 第四章 4.1.11 - volume_weighted_rsi
        公式: rsi(price_change * volume_weight)

        成交量加权RSI结合成交量信息，
        成交量大的价格变化权重更高。

        Args:
            data: 包含价格和成交量的数据框
            close_col: 收盘价列名
            volume_col: 成交量列名
            window: RSI窗口大小（默认14天）

        Returns:
            成交量加权RSI序列 [0, 100]

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [close_col, volume_col])

            close = data[close_col]
            volume = data[volume_col]

            # 计算价格变化
            price_change = close.diff()

            # 计算成交量权重
            volume_ma = volume.rolling(window=window).mean()
            volume_weight = volume / (volume_ma + 1e-8)

            # 成交量加权价格变化
            weighted_change = price_change * volume_weight

            # 区分上涨和下跌
            gain = pd.Series(0.0, index=data.index)
            loss = pd.Series(0.0, index=data.index)

            gain[weighted_change > 0] = weighted_change[weighted_change > 0]
            loss[weighted_change < 0] = -weighted_change[weighted_change < 0]

            # 计算平均涨跌幅
            avg_gain = gain.rolling(window=window).mean()
            avg_loss = loss.rolling(window=window).mean()

            # 计算RS和RSI
            rs = avg_gain / (avg_loss + 1e-8)
            rsi = 100 - (100 / (1 + rs))

            logger.debug(f"计算volume_weighted_rsi: mean={rsi.mean():.2f}")

            return rsi

        except Exception as e:
            logger.error(f"volume_weighted_rsi计算失败: {e}")
            raise OperatorError(f"volume_weighted_rsi失败: {e}") from e

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def on_balance_volume(self, data: pd.DataFrame, close_col: str = "close", volume_col: str = "volume") -> pd.Series:
        """计算OBV (On-Balance Volume)

        辅助方法，用于obv_divergence算子

        Args:
            data: 包含价格和成交量的数据框
            close_col: 收盘价列名
            volume_col: 成交量列名

        Returns:
            OBV序列
        """
        close = data[close_col]
        volume = data[volume_col]

        # 计算价格变化方向
        price_change = close.diff()

        # OBV计算
        obv = pd.Series(0.0, index=data.index)
        obv[price_change > 0] = volume[price_change > 0]
        obv[price_change < 0] = -volume[price_change < 0]

        # 累积
        obv = obv.cumsum()

        return obv
