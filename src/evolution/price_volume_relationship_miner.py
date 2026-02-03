"""量价关系因子挖掘器

白皮书依据: 第四章 4.1.11 量价关系因子挖掘
需求: 10.1-10.14
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from loguru import logger


@dataclass
class PriceVolumeFactor:
    """量价关系因子数据结构

    Attributes:
        factor_name: 因子名称
        factor_values: 因子值序列
        signal_type: 信号类型（买入/卖出/中性）
        reliability: 信号可靠性评分
        volume_confirmed: 是否经过成交量确认
        metadata: 额外元数据
    """

    factor_name: str
    factor_values: pd.Series
    signal_type: str
    reliability: float
    volume_confirmed: bool
    metadata: Dict[str, Any]


class PriceVolumeRelationshipFactorMiner:
    """量价关系因子挖掘器

    白皮书依据: 第四章 4.1.11 量价关系因子挖掘
    需求: 10.1-10.14

    挖掘价格与成交量之间的关系因子，捕获供需动态和市场强度。
    支持12个核心量价算子，包括背离检测和突破确认机制。

    Attributes:
        operators: 12个量价算子字典
        volume_reliability_threshold: 成交量可靠性阈值
    """

    def __init__(self, volume_reliability_threshold: float = 0.8):
        """初始化量价关系因子挖掘器

        白皮书依据: 第四章 4.1.11
        需求: 10.1, 10.13

        Args:
            volume_reliability_threshold: 成交量可靠性阈值，默认0.8
        """
        self.operators: Dict[str, Callable] = self._initialize_operators()
        self.volume_reliability_threshold = volume_reliability_threshold

        logger.info(
            f"PriceVolumeRelationshipFactorMiner initialized with 12 operators, "
            f"reliability_threshold={volume_reliability_threshold}"
        )

        # 健康状态跟踪
        self._is_healthy = True
        self._error_count = 0

    def is_healthy(self) -> bool:
        """检查挖掘器健康状态

        Returns:
            是否健康
        """
        return self._is_healthy and self._error_count < 5

    def get_metadata(self) -> Dict:
        """获取挖掘器元数据

        Returns:
            元数据字典
        """
        return {
            "miner_type": "price_volume",
            "miner_name": "PriceVolumeRelationshipFactorMiner",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "volume_reliability_threshold": self.volume_reliability_threshold,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化12个量价算子

        白皮书依据: 第四章 4.1.11
        需求: 10.1-10.12, 10.13

        Returns:
            算子名称到函数的映射字典
        """
        return {
            "volume_price_correlation": self._volume_price_correlation,
            "obv_divergence": self._obv_divergence,
            "vwap_deviation": self._vwap_deviation,
            "volume_weighted_momentum": self._volume_weighted_momentum,
            "price_volume_trend": self._price_volume_trend,
            "accumulation_distribution": self._accumulation_distribution,
            "money_flow_index": self._money_flow_index,
            "volume_surge": self._volume_surge,
            "price_volume_breakout": self._price_volume_breakout,
            "volume_profile": self._volume_profile,
            "tick_volume": self._tick_volume,
            "volume_weighted_rsi": self._volume_weighted_rsi,
        }

    def mine_factors(
        self,
        price_data: pd.DataFrame,
        volume_data: pd.DataFrame,
        high_data: Optional[pd.DataFrame] = None,
        low_data: Optional[pd.DataFrame] = None,
    ) -> List[PriceVolumeFactor]:
        """挖掘量价关系因子

        白皮书依据: 第四章 4.1.11
        需求: 10.1-10.12

        Args:
            price_data: 价格数据（收盘价），索引为日期，列为股票代码
            volume_data: 成交量数据，索引为日期，列为股票代码
            high_data: 最高价数据（可选）
            low_data: 最低价数据（可选）

        Returns:
            量价关系因子列表

        Raises:
            ValueError: 当输入数据无效时
        """
        if price_data.empty:
            raise ValueError("价格数据不能为空")

        if volume_data.empty:
            raise ValueError("成交量数据不能为空")

        if price_data.shape != volume_data.shape:
            raise ValueError(f"价格和成交量数据形状不匹配: " f"price={price_data.shape}, volume={volume_data.shape}")

        logger.info(f"开始挖掘量价关系因子 - " f"股票数: {len(price_data.columns)}, " f"时间点: {len(price_data)}")

        # 验证成交量数据
        volume_valid = self._validate_volume_data(volume_data)
        if not volume_valid:
            logger.warning("成交量数据验证失败，部分因子可能不可靠")

        factors = []

        try:
            # 算子1: 量价相关性
            correlation_factor = self._volume_price_correlation(price_data, volume_data)
            factors.append(correlation_factor)

            # 算子2: OBV背离
            obv_factor = self._obv_divergence(price_data, volume_data)
            factors.append(obv_factor)

            # 算子3: VWAP偏离
            vwap_factor = self._vwap_deviation(price_data, volume_data)
            factors.append(vwap_factor)

            # 算子4: 成交量加权动量
            momentum_factor = self._volume_weighted_momentum(price_data, volume_data)
            factors.append(momentum_factor)

            # 算子5: 量价趋势
            trend_factor = self._price_volume_trend(price_data, volume_data)
            factors.append(trend_factor)

            # 算子6: 累积/派发
            ad_factor = self._accumulation_distribution(price_data, volume_data, high_data, low_data)
            factors.append(ad_factor)

            # 算子7: 资金流量指数
            mfi_factor = self._money_flow_index(price_data, volume_data, high_data, low_data)
            factors.append(mfi_factor)

            # 算子8: 成交量激增
            surge_factor = self._volume_surge(volume_data)
            factors.append(surge_factor)

            # 算子9: 量价突破
            breakout_factor = self._price_volume_breakout(price_data, volume_data)
            factors.append(breakout_factor)

            # 算子10: 成交量分布
            profile_factor = self._volume_profile(price_data, volume_data)
            factors.append(profile_factor)

            # 算子11: Tick成交量
            tick_factor = self._tick_volume(volume_data)
            factors.append(tick_factor)

            # 算子12: 成交量加权RSI
            rsi_factor = self._volume_weighted_rsi(price_data, volume_data)
            factors.append(rsi_factor)

            logger.info(f"成功挖掘 {len(factors)} 个量价关系因子")

            return factors

        except Exception as e:
            logger.error(f"挖掘量价关系因子失败: {e}")
            raise

    def _validate_volume_data(self, volume_data: pd.DataFrame) -> bool:
        """验证成交量数据

        白皮书依据: 第四章 4.1.11
        需求: 10.14

        检测缺失数据和异常值，标记不可靠的成交量数据。

        Args:
            volume_data: 成交量数据

        Returns:
            True如果数据可靠，False如果不可靠
        """
        try:
            # 检查缺失数据比例
            missing_ratio = volume_data.isna().sum().sum() / volume_data.size

            # 检查零值比例
            zero_ratio = (volume_data == 0).sum().sum() / volume_data.size

            # 检查异常值（超过均值10倍）
            mean_volume = volume_data.mean().mean()
            outlier_ratio = (volume_data > mean_volume * 10).sum().sum() / volume_data.size

            # 综合可靠性评分
            reliability = 1.0 - (missing_ratio + zero_ratio + outlier_ratio) / 3

            is_reliable = reliability >= self.volume_reliability_threshold

            logger.debug(
                f"成交量数据验证 - "
                f"缺失: {missing_ratio:.2%}, "
                f"零值: {zero_ratio:.2%}, "
                f"异常: {outlier_ratio:.2%}, "
                f"可靠性: {reliability:.2%}, "
                f"结果: {'可靠' if is_reliable else '不可靠'}"
            )

            return is_reliable

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"成交量数据验证失败: {e}")
            return False

    def _volume_price_correlation(
        self, price_data: pd.DataFrame, volume_data: pd.DataFrame, window: int = 20
    ) -> PriceVolumeFactor:
        """算子1: 量价相关性因子

        白皮书依据: 第四章 4.1.11
        需求: 10.1

        计算价格变化与成交量变化的相关性。
        正相关表示量价配合良好，负相关可能预示反转。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            window: 滚动窗口大小

        Returns:
            量价相关性因子
        """
        try:
            # 计算价格变化率
            price_change = price_data.pct_change()

            # 计算成交量变化率
            volume_change = volume_data.pct_change()

            # 计算滚动相关性
            correlation = pd.Series(0.0, index=price_data.columns)

            for symbol in price_data.columns:
                if symbol in volume_data.columns:
                    corr = price_change[symbol].rolling(window=window).corr(volume_change[symbol])
                    correlation[symbol] = corr.iloc[-1] if not corr.empty else 0.0

            # 填充NaN
            factor_values = correlation.fillna(0)

            # 计算可靠性
            reliability = 1.0 - (correlation.isna().sum() / len(correlation))

            logger.debug(f"量价相关性因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="volume_price_correlation",
                factor_values=factor_values,
                signal_type="中性",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "价格与成交量变化的相关性",
                    "window": window,
                    "mean_correlation": correlation.mean(),
                },
            )

        except Exception as e:
            logger.error(f"量价相关性计算失败: {e}")
            raise

    def _obv_divergence(
        self, price_data: pd.DataFrame, volume_data: pd.DataFrame, window: int = 20
    ) -> PriceVolumeFactor:
        """算子2: OBV背离因子

        白皮书依据: 第四章 4.1.11
        需求: 10.2

        检测价格与OBV（能量潮）指标的背离。
        背离通常预示着趋势反转。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            window: 背离检测窗口

        Returns:
            OBV背离因子
        """
        try:  # pylint: disable=r1702
            # 计算OBV
            price_change = price_data.diff()
            obv = pd.DataFrame(0.0, index=price_data.index, columns=price_data.columns)

            for symbol in price_data.columns:
                if symbol in volume_data.columns:
                    # OBV累积计算
                    obv_values = []
                    cumulative_obv = 0

                    for i in range(len(price_data)):
                        if i == 0:
                            obv_values.append(volume_data[symbol].iloc[i])
                        else:
                            if price_change[symbol].iloc[i] > 0:
                                cumulative_obv += volume_data[symbol].iloc[i]
                            elif price_change[symbol].iloc[i] < 0:
                                cumulative_obv -= volume_data[symbol].iloc[i]
                            obv_values.append(cumulative_obv)

                    obv[symbol] = obv_values

            # 检测背离：价格上涨但OBV下降（看跌背离）或价格下跌但OBV上升（看涨背离）
            price_trend = price_data.iloc[-1] - price_data.iloc[-window]
            obv_trend = obv.iloc[-1] - obv.iloc[-window]

            # 背离强度：价格和OBV趋势方向相反的程度
            divergence = -(price_trend * obv_trend)  # 负值表示背离

            # 标准化
            factor_values = (divergence / (divergence.abs().mean() + 1e-10)).fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"OBV背离因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="obv_divergence",
                factor_values=factor_values,
                signal_type="反转",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "价格与OBV指标的背离检测",
                    "window": window,
                    "divergence_count": (divergence < 0).sum(),
                },
            )

        except Exception as e:
            logger.error(f"OBV背离计算失败: {e}")
            raise

    def _vwap_deviation(self, price_data: pd.DataFrame, volume_data: pd.DataFrame) -> PriceVolumeFactor:
        """算子3: VWAP偏离因子

        白皮书依据: 第四章 4.1.11
        需求: 10.3

        计算当前价格与成交量加权平均价格(VWAP)的偏离度。
        偏离度反映了价格相对于平均成交价的位置。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据

        Returns:
            VWAP偏离因子
        """
        try:
            # 计算VWAP
            vwap = (price_data * volume_data).sum() / volume_data.sum()

            # 计算当前价格与VWAP的偏离
            current_price = price_data.iloc[-1]
            deviation = (current_price - vwap) / vwap

            # 标准化
            factor_values = (deviation / (deviation.abs().mean() + 1e-10)).fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"VWAP偏离因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="vwap_deviation",
                factor_values=factor_values,
                signal_type="均值回归",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "价格与VWAP的偏离度",
                    "mean_deviation": deviation.mean(),
                    "std_deviation": deviation.std(),
                },
            )

        except Exception as e:
            logger.error(f"VWAP偏离计算失败: {e}")
            raise

    def _volume_weighted_momentum(
        self, price_data: pd.DataFrame, volume_data: pd.DataFrame, window: int = 20
    ) -> PriceVolumeFactor:
        """算子4: 成交量加权动量因子

        白皮书依据: 第四章 4.1.11
        需求: 10.4

        计算成交量加权的价格动量。
        大成交量的价格变化权重更高。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            window: 动量计算窗口

        Returns:
            成交量加权动量因子
        """
        try:
            # 计算价格变化
            returns = price_data.pct_change()

            # 成交量加权动量
            weighted_momentum = (returns * volume_data).rolling(window=window).sum() / volume_data.rolling(
                window=window
            ).sum()

            # 取最新值
            factor_values = weighted_momentum.iloc[-1].fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"成交量加权动量因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="volume_weighted_momentum",
                factor_values=factor_values,
                signal_type="趋势",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "成交量加权的价格动量",
                    "window": window,
                    "mean_momentum": factor_values.mean(),
                },
            )

        except Exception as e:
            logger.error(f"成交量加权动量计算失败: {e}")
            raise

    def _price_volume_trend(self, price_data: pd.DataFrame, volume_data: pd.DataFrame) -> PriceVolumeFactor:
        """算子5: 量价趋势因子

        白皮书依据: 第四章 4.1.11
        需求: 10.5

        识别价格和成交量的同步或背离趋势。
        同步上涨是强势信号，背离可能预示反转。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据

        Returns:
            量价趋势因子
        """
        try:
            # 计算价格趋势（简单移动平均斜率）
            price_ma = price_data.rolling(window=20).mean()
            price_trend = price_ma.iloc[-1] - price_ma.iloc[-20]

            # 计算成交量趋势
            volume_ma = volume_data.rolling(window=20).mean()
            volume_trend = volume_ma.iloc[-1] - volume_ma.iloc[-20]

            # 量价趋势一致性：两者同向为正，反向为负
            trend_consistency = (price_trend * volume_trend) / (price_trend.abs() * volume_trend.abs() + 1e-10)

            # 标准化
            factor_values = trend_consistency.fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"量价趋势因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="price_volume_trend",
                factor_values=factor_values,
                signal_type="趋势",
                reliability=reliability,
                volume_confirmed=True,
                metadata={"description": "价格和成交量趋势的一致性", "mean_consistency": factor_values.mean()},
            )

        except Exception as e:
            logger.error(f"量价趋势计算失败: {e}")
            raise

    def _accumulation_distribution(
        self,
        price_data: pd.DataFrame,
        volume_data: pd.DataFrame,
        high_data: Optional[pd.DataFrame] = None,
        low_data: Optional[pd.DataFrame] = None,
    ) -> PriceVolumeFactor:
        """算子6: 累积/派发因子

        白皮书依据: 第四章 4.1.11
        需求: 10.6

        衡量买入压力与卖出压力的平衡。
        正值表示累积（买入），负值表示派发（卖出）。

        Args:
            price_data: 价格数据（收盘价）
            volume_data: 成交量数据
            high_data: 最高价数据
            low_data: 最低价数据

        Returns:
            累积/派发因子
        """
        try:
            if high_data is None or low_data is None:
                # 如果没有高低价，使用简化版本
                close_loc = (price_data - price_data.rolling(window=20).min()) / (
                    price_data.rolling(window=20).max() - price_data.rolling(window=20).min() + 1e-10
                )
            else:
                # 使用完整的CLV公式
                close_loc = ((price_data - low_data) - (high_data - price_data)) / (high_data - low_data + 1e-10)

            # 累积/派发线
            ad_line = (close_loc * volume_data).cumsum()

            # 取最新值并标准化
            factor_values = ad_line.iloc[-1]
            factor_values = ((factor_values - factor_values.mean()) / (factor_values.std() + 1e-10)).fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"累积/派发因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="accumulation_distribution",
                factor_values=factor_values,
                signal_type="买卖压力",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "买入压力与卖出压力的平衡",
                    "has_high_low": high_data is not None and low_data is not None,
                },
            )

        except Exception as e:
            logger.error(f"累积/派发计算失败: {e}")
            raise

    def _money_flow_index(  # pylint: disable=too-many-positional-arguments
        self,
        price_data: pd.DataFrame,
        volume_data: pd.DataFrame,
        high_data: Optional[pd.DataFrame] = None,
        low_data: Optional[pd.DataFrame] = None,
        window: int = 14,
    ) -> PriceVolumeFactor:
        """算子7: 资金流量指数因子

        白皮书依据: 第四章 4.1.11
        需求: 10.7

        结合价格和成交量计算资金流入流出。
        MFI类似于RSI，但考虑了成交量因素。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            high_data: 最高价数据
            low_data: 最低价数据
            window: MFI计算窗口

        Returns:
            资金流量指数因子
        """
        try:
            # 计算典型价格
            if high_data is not None and low_data is not None:
                typical_price = (high_data + low_data + price_data) / 3
            else:
                typical_price = price_data

            # 计算资金流量
            money_flow = typical_price * volume_data

            # 计算正负资金流量
            price_change = typical_price.diff()
            positive_flow = money_flow.where(price_change > 0, 0).rolling(window=window).sum()
            negative_flow = money_flow.where(price_change < 0, 0).rolling(window=window).sum()

            # 计算MFI
            money_ratio = positive_flow / (negative_flow + 1e-10)
            mfi = 100 - (100 / (1 + money_ratio))

            # 取最新值并标准化到[-1, 1]
            factor_values = (mfi.iloc[-1] - 50) / 50
            factor_values = factor_values.fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"资金流量指数因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="money_flow_index",
                factor_values=factor_values,
                signal_type="超买超卖",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "结合价格和成交量的资金流量指数",
                    "window": window,
                    "mean_mfi": (mfi.iloc[-1].mean() if not mfi.empty else 50),
                },
            )

        except Exception as e:
            logger.error(f"资金流量指数计算失败: {e}")
            raise

    def _volume_surge(self, volume_data: pd.DataFrame, threshold: float = 2.0) -> PriceVolumeFactor:
        """算子8: 成交量激增因子

        白皮书依据: 第四章 4.1.11
        需求: 10.8

        识别异常的成交量激增模式。
        成交量激增通常预示着重要的市场事件。

        Args:
            volume_data: 成交量数据
            threshold: 激增阈值（相对于平均值的倍数）

        Returns:
            成交量激增因子
        """
        try:
            # 计算成交量移动平均
            volume_ma = volume_data.rolling(window=20).mean()

            # 计算当前成交量相对于平均值的倍数
            volume_ratio = volume_data.iloc[-1] / (volume_ma.iloc[-1] + 1e-10)

            # 识别激增（超过阈值）
            surge_signal = (volume_ratio > threshold).astype(float)

            # 激增强度
            surge_strength = (volume_ratio - 1) * surge_signal

            # 标准化
            factor_values = (surge_strength / (surge_strength.mean() + 1e-10)).fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"成交量激增因子计算完成，可靠性: {reliability:.2%}, " f"激增数量: {surge_signal.sum()}")

            return PriceVolumeFactor(
                factor_name="volume_surge",
                factor_values=factor_values,
                signal_type="异常",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "异常成交量激增检测",
                    "threshold": threshold,
                    "surge_count": int(surge_signal.sum()),
                    "max_ratio": volume_ratio.max(),
                },
            )

        except Exception as e:
            logger.error(f"成交量激增计算失败: {e}")
            raise

    def _price_volume_breakout(
        self, price_data: pd.DataFrame, volume_data: pd.DataFrame, window: int = 20
    ) -> PriceVolumeFactor:
        """算子9: 量价突破因子

        白皮书依据: 第四章 4.1.11
        需求: 10.9

        用成交量确认价格突破的有效性。
        有成交量支持的突破更可靠。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            window: 突破检测窗口

        Returns:
            量价突破因子
        """
        try:
            # 计算价格突破
            price_high = price_data.rolling(window=window).max()
            price_low = price_data.rolling(window=window).min()

            current_price = price_data.iloc[-1]

            # 向上突破
            upward_breakout = (current_price > price_high.iloc[-2]).astype(float)

            # 向下突破
            downward_breakout = (current_price < price_low.iloc[-2]).astype(float)

            # 成交量确认（当前成交量高于平均）
            volume_ma = volume_data.rolling(window=window).mean()
            volume_confirmed = (volume_data.iloc[-1] > volume_ma.iloc[-1]).astype(float)

            # 突破信号：向上突破为正，向下突破为负，需要成交量确认
            breakout_signal = (upward_breakout - downward_breakout) * volume_confirmed

            factor_values = breakout_signal.fillna(0)

            # 计算可靠性
            reliability = volume_confirmed.mean()

            logger.debug(
                f"量价突破因子计算完成，可靠性: {reliability:.2%}, " f"突破数量: {(breakout_signal != 0).sum()}"
            )

            return PriceVolumeFactor(
                factor_name="price_volume_breakout",
                factor_values=factor_values,
                signal_type="突破",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "成交量确认的价格突破",
                    "window": window,
                    "upward_count": int(upward_breakout.sum()),
                    "downward_count": int(downward_breakout.sum()),
                    "confirmed_count": int((breakout_signal != 0).sum()),
                },
            )

        except Exception as e:
            logger.error(f"量价突破计算失败: {e}")
            raise

    def _volume_profile(self, price_data: pd.DataFrame, volume_data: pd.DataFrame, bins: int = 10) -> PriceVolumeFactor:
        """算子10: 成交量分布因子

        白皮书依据: 第四章 4.1.11
        需求: 10.10

        从成交量分布识别支撑/阻力位。
        高成交量区域通常形成重要的价格水平。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            bins: 价格区间数量

        Returns:
            成交量分布因子
        """
        try:
            # 对每个股票计算成交量分布
            profile_scores = pd.Series(0.0, index=price_data.columns)

            for symbol in price_data.columns:
                if symbol in volume_data.columns:
                    prices = price_data[symbol].dropna()
                    volumes = volume_data[symbol].dropna()

                    if len(prices) > 0 and len(volumes) > 0:
                        # 创建价格区间
                        price_bins = pd.cut(prices, bins=bins)

                        # 计算每个区间的成交量
                        volume_by_bin = volumes.groupby(price_bins).sum()

                        # 当前价格所在区间的成交量占比
                        current_price = prices.iloc[-1]
                        current_bin = pd.cut([current_price], bins=bins)[0]

                        if current_bin in volume_by_bin.index:
                            profile_scores[symbol] = volume_by_bin[current_bin] / (volume_by_bin.sum() + 1e-10)

            # 标准化
            factor_values = ((profile_scores - profile_scores.mean()) / (profile_scores.std() + 1e-10)).fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"成交量分布因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="volume_profile",
                factor_values=factor_values,
                signal_type="支撑阻力",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "成交量分布识别的支撑/阻力",
                    "bins": bins,
                    "mean_score": profile_scores.mean(),
                },
            )

        except Exception as e:
            logger.error(f"成交量分布计算失败: {e}")
            raise

    def _tick_volume(self, volume_data: pd.DataFrame, window: int = 20) -> PriceVolumeFactor:
        """算子11: Tick成交量因子

        白皮书依据: 第四章 4.1.11
        需求: 10.11

        衡量日内成交量模式。
        Tick成交量反映了交易活跃度。

        Args:
            volume_data: 成交量数据
            window: 分析窗口

        Returns:
            Tick成交量因子
        """
        try:
            # 计算成交量变化率
            volume_change = volume_data.pct_change()

            # 计算成交量波动性
            volume_volatility = volume_change.rolling(window=window).std()

            # 取最新值并标准化
            factor_values = volume_volatility.iloc[-1]
            factor_values = ((factor_values - factor_values.mean()) / (factor_values.std() + 1e-10)).fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"Tick成交量因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="tick_volume",
                factor_values=factor_values,
                signal_type="活跃度",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "日内成交量模式和活跃度",
                    "window": window,
                    "mean_volatility": volume_volatility.iloc[-1].mean(),
                },
            )

        except Exception as e:
            logger.error(f"Tick成交量计算失败: {e}")
            raise

    def _volume_weighted_rsi(
        self, price_data: pd.DataFrame, volume_data: pd.DataFrame, window: int = 14
    ) -> PriceVolumeFactor:
        """算子12: 成交量加权RSI因子

        白皮书依据: 第四章 4.1.11
        需求: 10.12

        将成交量纳入RSI计算。
        大成交量的价格变化对RSI影响更大。

        Args:
            price_data: 价格数据
            volume_data: 成交量数据
            window: RSI计算窗口

        Returns:
            成交量加权RSI因子
        """
        try:
            # 计算价格变化
            price_change = price_data.diff()

            # 成交量加权的涨跌
            weighted_gain = price_change.where(price_change > 0, 0) * volume_data
            weighted_loss = -price_change.where(price_change < 0, 0) * volume_data

            # 计算平均涨跌
            avg_gain = weighted_gain.rolling(window=window).sum() / volume_data.rolling(window=window).sum()
            avg_loss = weighted_loss.rolling(window=window).sum() / volume_data.rolling(window=window).sum()

            # 计算RS和RSI
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))

            # 取最新值并标准化到[-1, 1]
            factor_values = (rsi.iloc[-1] - 50) / 50
            factor_values = factor_values.fillna(0)

            # 计算可靠性
            reliability = 1.0 - (factor_values.isna().sum() / len(factor_values))

            logger.debug(f"成交量加权RSI因子计算完成，可靠性: {reliability:.2%}")

            return PriceVolumeFactor(
                factor_name="volume_weighted_rsi",
                factor_values=factor_values,
                signal_type="超买超卖",
                reliability=reliability,
                volume_confirmed=True,
                metadata={
                    "description": "成交量加权的RSI指标",
                    "window": window,
                    "mean_rsi": (rsi.iloc[-1].mean() * 50 + 50 if not rsi.empty else 50),
                },
            )

        except Exception as e:
            logger.error(f"成交量加权RSI计算失败: {e}")
            raise

    def get_operator_list(self) -> List[str]:
        """获取所有可用算子列表

        Returns:
            算子名称列表
        """
        return list(self.operators.keys())
