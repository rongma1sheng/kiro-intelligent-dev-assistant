"""高频微观结构因子算子

白皮书依据: 第四章 4.1.6 高频微观结构因子挖掘器
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class HighFrequencyConfig:
    """高频微观结构因子配置

    Attributes:
        tick_window: Tick窗口大小
        imbalance_threshold: 订单流不平衡阈值
        impact_quantiles: 价格冲击分位数
        cluster_window: 聚类窗口大小
        stuffing_threshold: 报价填充检测阈值
        spread_window: 价差计算窗口
    """

    tick_window: int = 100
    imbalance_threshold: float = 0.3
    impact_quantiles: Tuple[float, ...] = (0.25, 0.5, 0.75)
    cluster_window: int = 50
    stuffing_threshold: float = 10.0
    spread_window: int = 20


def order_flow_imbalance(data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, window: int = 100) -> pd.Series:
    """订单流不平衡

    白皮书依据: 第四章 4.1.6 - order_flow_imbalance

    计算买卖订单流的不平衡程度。
    正值表示买方压力，负值表示卖方压力。

    Args:
        data: 价格数据
        volume: 成交量数据（可选）
        window: 滚动窗口期

    Returns:
        pd.Series: 订单流不平衡因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算价格变化方向（tick direction）
        price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]
        price_change = price.diff()

        # Tick方向：+1(上涨), -1(下跌), 0(不变)
        tick_direction = np.sign(price_change)

        # 如果有成交量，使用成交量加权
        if volume is not None and not volume.empty:
            vol = volume.mean(axis=1) if len(volume.columns) > 1 else volume.iloc[:, 0]
            weighted_direction = tick_direction * vol
        else:
            weighted_direction = tick_direction

        # 计算滚动订单流不平衡
        # OFI = (买单量 - 卖单量) / (买单量 + 卖单量)
        buy_flow = weighted_direction.clip(lower=0).rolling(window).sum()
        sell_flow = (-weighted_direction).clip(lower=0).rolling(window).sum()

        total_flow = buy_flow + sell_flow
        imbalance = (buy_flow - sell_flow) / (total_flow + 1e-8)

        # 标准化
        result = (imbalance - imbalance.mean()) / (imbalance.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"订单流不平衡计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def price_impact_curve(
    data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, quantiles: Tuple[float, ...] = (0.25, 0.5, 0.75)
) -> pd.Series:
    """价格冲击曲线

    白皮书依据: 第四章 4.1.6 - price_impact_curve

    衡量交易量对价格的冲击程度。
    大额交易对价格的冲击更大。

    Args:
        data: 价格数据
        volume: 成交量数据（可选）
        quantiles: 分位数

    Returns:
        pd.Series: 价格冲击因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change().mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0].pct_change()

        # 如果有成交量数据
        if volume is not None and not volume.empty:
            vol = volume.mean(axis=1) if len(volume.columns) > 1 else volume.iloc[:, 0]

            # 按成交量分组计算价格冲击
            vol_quantiles = vol.quantile(list(quantiles))

            # 计算不同成交量水平的平均收益率（价格冲击）
            impact_scores = pd.Series(0.0, index=data.index)

            for i, q in enumerate(quantiles):  # pylint: disable=unused-variable
                if i == 0:
                    mask = vol <= vol_quantiles.iloc[i]
                elif i == len(quantiles) - 1:
                    mask = vol > vol_quantiles.iloc[i - 1]
                else:
                    mask = (vol > vol_quantiles.iloc[i - 1]) & (vol <= vol_quantiles.iloc[i])

                # 高成交量对应高冲击
                impact_scores[mask] = abs(returns[mask]) * (i + 1)

            # 标准化
            result = (impact_scores - impact_scores.mean()) / (impact_scores.std() + 1e-8)

        else:
            # 简化版本：使用收益率波动作为代理
            result = returns.rolling(20).std()
            result = (result - result.mean()) / (result.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"价格冲击曲线计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def tick_direction_momentum(data: pd.DataFrame, window: int = 100) -> pd.Series:
    """Tick方向动量

    白皮书依据: 第四章 4.1.6 - tick_direction_momentum

    计算价格tick方向的动量。
    连续上涨的tick表示强劲的买方压力。

    Args:
        data: 价格数据
        window: 滚动窗口期

    Returns:
        pd.Series: Tick方向动量因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算平均价格
        price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]

        # 计算tick方向
        price_change = price.diff()
        tick_direction = np.sign(price_change)

        # 计算滚动tick方向动量
        # 正值表示上涨动量，负值表示下跌动量
        tick_momentum = tick_direction.rolling(window).sum()

        # 归一化到[-1, 1]
        tick_momentum = tick_momentum / window

        # 标准化
        result = (tick_momentum - tick_momentum.mean()) / (tick_momentum.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Tick方向动量计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def bid_ask_bounce(data: pd.DataFrame, window: int = 50) -> pd.Series:
    """买卖价反弹

    白皮书依据: 第四章 4.1.6 - bid_ask_bounce

    捕捉价格在买卖价之间的反弹效应。
    高频交易中的微观结构噪音。

    Args:
        data: 价格数据
        window: 滚动窗口期

    Returns:
        pd.Series: 买卖价反弹因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算平均价格
        price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]

        # 计算价格变化
        price_change = price.diff()

        # 检测反弹：价格变化方向连续反转
        direction_change = np.sign(price_change)
        direction_reversal = (direction_change * direction_change.shift(1)) < 0

        # 计算滚动反弹频率
        bounce_frequency = direction_reversal.astype(float).rolling(window).mean()

        # 计算反弹幅度
        bounce_amplitude = abs(price_change).rolling(window).mean()

        # 综合反弹因子 = 频率 × 幅度
        bounce_factor = bounce_frequency * bounce_amplitude

        # 标准化
        result = (bounce_factor - bounce_factor.mean()) / (bounce_factor.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"买卖价反弹计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def trade_size_clustering(data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, window: int = 50) -> pd.Series:
    """交易规模聚类

    白皮书依据: 第四章 4.1.6 - trade_size_clustering

    检测交易规模的聚类模式。
    大额交易聚集可能预示重要信息。

    Args:
        data: 价格数据
        volume: 成交量数据（可选）
        window: 滚动窗口期

    Returns:
        pd.Series: 交易规模聚类因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 如果有成交量数据
        if volume is not None and not volume.empty:
            vol = volume.mean(axis=1) if len(volume.columns) > 1 else volume.iloc[:, 0]

            # 计算成交量的变异系数（CV）
            vol_mean = vol.rolling(window).mean()
            vol_std = vol.rolling(window).std()
            cv = vol_std / (vol_mean + 1e-8)

            # 检测大额交易（超过均值+2倍标准差）
            large_trades = vol > (vol_mean + 2 * vol_std)

            # 计算大额交易的聚类程度
            # 使用滚动窗口内大额交易的频率
            clustering = large_trades.astype(float).rolling(window).mean()

            # 综合聚类因子 = 聚类频率 / 变异系数
            # 低CV + 高聚类频率 = 强聚类
            clustering_factor = clustering / (cv + 1e-8)

        else:
            # 简化版本：使用价格波动作为代理
            price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]
            returns = price.pct_change()

            # 检测大幅波动
            vol_threshold = returns.rolling(window).std() * 2
            large_moves = abs(returns) > vol_threshold

            clustering_factor = large_moves.astype(float).rolling(window).mean()

        # 标准化
        result = (clustering_factor - clustering_factor.mean()) / (clustering_factor.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"交易规模聚类计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def quote_stuffing_detection(data: pd.DataFrame, window: int = 20, threshold: float = 10.0) -> pd.Series:
    """报价填充检测

    白皮书依据: 第四章 4.1.6 - quote_stuffing_detection

    检测异常高频的报价更新（报价填充）。
    可能是市场操纵或高频交易策略。

    Args:
        data: 价格数据
        window: 滚动窗口期
        threshold: 异常阈值（倍数）

    Returns:
        pd.Series: 报价填充检测因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算平均价格
        price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]

        # 计算价格更新频率（价格变化的次数）
        price_changes = (price.diff() != 0).astype(float)
        update_frequency = price_changes.rolling(window).sum()

        # 计算正常更新频率
        normal_frequency = update_frequency.rolling(window * 5).mean()

        # 检测异常高频更新
        # 如果更新频率超过正常频率的threshold倍，视为报价填充
        stuffing_indicator = (update_frequency > threshold * normal_frequency).astype(float)

        # 计算填充强度
        stuffing_intensity = update_frequency / (normal_frequency + 1e-8)

        # 综合因子
        stuffing_factor = stuffing_indicator * stuffing_intensity

        # 标准化
        result = (stuffing_factor - stuffing_factor.mean()) / (stuffing_factor.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"报价填充检测失败: {e}")
        return pd.Series(0.0, index=data.index)


def hidden_liquidity_probe(data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, window: int = 50) -> pd.Series:
    """隐藏流动性探测

    白皮书依据: 第四章 4.1.6 - hidden_liquidity_probe

    探测市场中的隐藏流动性。
    大额交易但价格冲击小，表示有隐藏流动性。

    Args:
        data: 价格数据
        volume: 成交量数据（可选）
        window: 滚动窗口期

    Returns:
        pd.Series: 隐藏流动性因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change().mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0].pct_change()

        # 如果有成交量数据
        if volume is not None and not volume.empty:
            vol = volume.mean(axis=1) if len(volume.columns) > 1 else volume.iloc[:, 0]

            # 计算价格冲击 = |收益率| / 成交量
            # 低冲击 + 高成交量 = 隐藏流动性
            price_impact = abs(returns) / (vol + 1e-8)

            # 归一化成交量
            vol_normalized = (vol - vol.rolling(window).mean()) / (vol.rolling(window).std() + 1e-8)

            # 归一化价格冲击
            impact_normalized = (price_impact - price_impact.rolling(window).mean()) / (
                price_impact.rolling(window).std() + 1e-8
            )

            # 隐藏流动性 = 高成交量 + 低价格冲击
            hidden_liquidity = vol_normalized - impact_normalized

        else:
            # 简化版本：使用收益率波动率作为代理
            volatility = returns.rolling(window).std()

            # 低波动率可能表示有隐藏流动性吸收冲击
            hidden_liquidity = -volatility

        # 标准化
        result = (hidden_liquidity - hidden_liquidity.mean()) / (hidden_liquidity.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"隐藏流动性探测失败: {e}")
        return pd.Series(0.0, index=data.index)


def market_maker_inventory(data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, window: int = 50) -> pd.Series:
    """做市商库存

    白皮书依据: 第四章 4.1.6 - market_maker_inventory

    估计做市商的库存水平。
    做市商库存过高会调整报价以减少库存。

    Args:
        data: 价格数据
        volume: 成交量数据（可选）
        window: 滚动窗口期

    Returns:
        pd.Series: 做市商库存因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算价格和收益率
        price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]
        returns = price.pct_change()

        # 如果有成交量数据
        if volume is not None and not volume.empty:
            vol = volume.mean(axis=1) if len(volume.columns) > 1 else volume.iloc[:, 0]

            # 估计做市商库存变化
            # 假设：价格上涨 + 高成交量 = 做市商卖出（库存减少）
            # 价格下跌 + 高成交量 = 做市商买入（库存增加）
            inventory_change = -returns * vol

            # 累积库存变化
            inventory = inventory_change.rolling(window).sum()

        else:
            # 简化版本：使用价格偏离均值作为代理
            price_mean = price.rolling(window).mean()
            inventory = price - price_mean

        # 标准化
        result = (inventory - inventory.mean()) / (inventory.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"做市商库存计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def adverse_selection_cost(data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, window: int = 50) -> pd.Series:
    """逆向选择成本

    白皮书依据: 第四章 4.1.6 - adverse_selection_cost

    衡量与知情交易者交易的成本。
    高逆向选择成本表示市场中有知情交易者。

    Args:
        data: 价格数据
        volume: 成交量数据（可选）
        window: 滚动窗口期

    Returns:
        pd.Series: 逆向选择成本因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change().mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0].pct_change()

        # 计算价格变化的持续性
        # 如果价格变化后继续朝同一方向移动，表示有知情交易
        returns.shift(1)
        returns.shift(2)

        # 计算收益率的自相关性
        # 正自相关表示趋势（知情交易），负自相关表示反转（噪音交易）
        autocorr = returns.rolling(window).apply(lambda x: x.autocorr(lag=1) if len(x) > 1 else 0, raw=False)

        # 如果有成交量数据，考虑成交量的影响
        if volume is not None and not volume.empty:
            vol = volume.mean(axis=1) if len(volume.columns) > 1 else volume.iloc[:, 0]

            # 大额交易的自相关性更重要
            vol_weight = vol / (vol.rolling(window).mean() + 1e-8)
            adverse_selection = autocorr * vol_weight
        else:
            adverse_selection = autocorr

        # 标准化
        result = (adverse_selection - adverse_selection.mean()) / (adverse_selection.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"逆向选择成本计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def effective_spread_decomposition(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """有效价差分解

    白皮书依据: 第四章 4.1.6 - effective_spread_decomposition

    将有效价差分解为逆向选择成本和订单处理成本。

    Args:
        data: 价格数据
        window: 滚动窗口期

    Returns:
        pd.Series: 有效价差分解因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算价格
        price = data.mean(axis=1) if len(data.columns) > 1 else data.iloc[:, 0]

        # 计算收益率
        returns = price.pct_change()

        # 估计有效价差
        # 使用Roll模型：spread = 2 * sqrt(-cov(r_t, r_{t-1}))
        returns_lag = returns.shift(1)

        # 计算滚动协方差
        rolling_cov = returns.rolling(window).cov(returns_lag)

        # 有效价差
        effective_spread = 2 * np.sqrt(-rolling_cov.clip(upper=0))

        # 分解为两部分：
        # 1. 逆向选择成本（价格变化的持续性）
        price_reversal = (returns * returns.shift(1)).rolling(window).mean()
        adverse_selection_component = -price_reversal

        # 2. 订单处理成本（剩余部分）
        effective_spread - adverse_selection_component  # pylint: disable=w0104

        # 返回逆向选择成本占比
        spread_decomposition = adverse_selection_component / (effective_spread + 1e-8)

        # 标准化
        result = (spread_decomposition - spread_decomposition.mean()) / (spread_decomposition.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"有效价差分解计算失败: {e}")
        return pd.Series(0.0, index=data.index)
