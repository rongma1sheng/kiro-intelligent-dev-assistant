"""风格轮动因子算子

白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器
"""

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class StyleRotationConfig:
    """风格轮动配置

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器
    """

    # 窗口期参数
    spread_window: int = 60  # 价差计算窗口
    cycle_window: int = 120  # 周期识别窗口
    momentum_window: int = 20  # 动量计算窗口
    volatility_window: int = 60  # 波动率窗口

    # 阈值参数
    spread_threshold: float = 0.3  # 价差阈值
    cycle_threshold: float = 0.5  # 周期阈值
    momentum_threshold: float = 0.2  # 动量阈值
    crowding_threshold: float = 0.7  # 拥挤阈值

    # 分位数参数
    value_quantile: float = 0.3  # 价值股分位数
    growth_quantile: float = 0.7  # 成长股分位数
    size_quantile: float = 0.5  # 规模分位数
    quality_quantile: float = 0.7  # 质量分位数


def value_growth_spread(
    data: pd.DataFrame, window: int = 60, value_quantile: float = 0.3, growth_quantile: float = 0.7
) -> pd.Series:
    """价值成长价差

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    计算价值股和成长股之间的相对表现价差,识别风格轮动信号。

    Args:
        data: 价格数据,列为股票代码
        window: 计算窗口
        value_quantile: 价值股分位数阈值
        growth_quantile: 成长股分位数阈值

    Returns:
        pd.Series: 价值成长价差因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 计算滚动收益率(作为成长性代理)
        rolling_returns = returns.rolling(window=window, min_periods=window // 2).mean()

        # 计算滚动波动率(作为价值性代理,低波动=价值)
        rolling_vol = returns.rolling(window=window, min_periods=window // 2).std()

        # 识别价值股(低波动)和成长股(高收益)
        value_scores = -rolling_vol  # 负号使低波动得分高
        growth_scores = rolling_returns

        # 计算每个时间点的价值股和成长股组合收益
        spread_series = []

        for idx in data.index:
            if idx not in value_scores.index or idx not in growth_scores.index:
                spread_series.append(0.0)
                continue

            # 获取当期评分
            value_score = value_scores.loc[idx]
            growth_score = growth_scores.loc[idx]

            # 选择价值股和成长股
            value_stocks = value_score.nlargest(int(len(value_score) * value_quantile))
            growth_stocks = growth_score.nlargest(int(len(growth_score) * growth_quantile))

            # 计算价差(价值股收益 - 成长股收益)
            if idx in returns.index:
                value_return = returns.loc[idx, value_stocks.index].mean()
                growth_return = returns.loc[idx, growth_stocks.index].mean()
                spread = value_return - growth_return
            else:
                spread = 0.0

            spread_series.append(spread)

        result = pd.Series(spread_series, index=data.index)
        result = result.fillna(0.0)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"价值成长价差计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def size_premium_cycle(data: pd.DataFrame, window: int = 120, size_quantile: float = 0.5) -> pd.Series:
    """规模溢价周期

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别大盘股和小盘股之间的周期性轮动。

    Args:
        data: 价格数据
        window: 周期识别窗口
        size_quantile: 规模分位数

    Returns:
        pd.Series: 规模溢价周期因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 使用价格水平作为规模代理(简化版本)
        # 实际应用中应使用市值数据
        size_proxy = data.rolling(window=window // 2, min_periods=window // 4).mean()

        # 计算规模溢价
        premium_series = []

        for idx in data.index:
            if idx not in size_proxy.index or idx not in returns.index:
                premium_series.append(0.0)
                continue

            # 获取当期规模代理
            sizes = size_proxy.loc[idx]

            # 分为大盘股和小盘股
            large_cap = sizes.nlargest(int(len(sizes) * size_quantile))
            small_cap = sizes.nsmallest(int(len(sizes) * size_quantile))

            # 计算规模溢价(小盘股收益 - 大盘股收益)
            large_return = returns.loc[idx, large_cap.index].mean()
            small_return = returns.loc[idx, small_cap.index].mean()
            premium = small_return - large_return

            premium_series.append(premium)

        result = pd.Series(premium_series, index=data.index)

        # 计算周期性(使用滚动标准化)
        result_normalized = (result - result.rolling(window=window, min_periods=window // 2).mean()) / (
            result.rolling(window=window, min_periods=window // 2).std() + 1e-8
        )

        result_normalized = result_normalized.fillna(0.0)

        return result_normalized

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"规模溢价周期计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def momentum_reversal_switch(data: pd.DataFrame, momentum_window: int = 20, reversal_window: int = 60) -> pd.Series:
    """动量反转切换

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别市场在动量效应和反转效应之间的切换。

    Args:
        data: 价格数据
        momentum_window: 动量窗口
        reversal_window: 反转窗口

    Returns:
        pd.Series: 动量反转切换因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 计算短期动量(近期表现)
        short_momentum = returns.rolling(window=momentum_window, min_periods=momentum_window // 2).mean()

        # 计算长期反转(远期表现)
        long_reversal = returns.rolling(window=reversal_window, min_periods=reversal_window // 2).mean()

        # 计算动量和反转的相对强度
        switch_series = []

        for idx in data.index:
            if idx not in short_momentum.index or idx not in long_reversal.index:
                switch_series.append(0.0)
                continue

            # 获取当期动量和反转
            momentum_scores = short_momentum.loc[idx]
            reversal_scores = -long_reversal.loc[idx]  # 反转是负相关

            # 选择动量股和反转股
            momentum_stocks = momentum_scores.nlargest(int(len(momentum_scores) * 0.3))
            reversal_stocks = reversal_scores.nlargest(int(len(reversal_scores) * 0.3))

            # 计算当期收益
            if idx in returns.index:
                momentum_return = returns.loc[idx, momentum_stocks.index].mean()
                reversal_return = returns.loc[idx, reversal_stocks.index].mean()
                switch = momentum_return - reversal_return
            else:
                switch = 0.0

            switch_series.append(switch)

        result = pd.Series(switch_series, index=data.index)
        result = result.fillna(0.0)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"动量反转切换计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def quality_junk_rotation(data: pd.DataFrame, window: int = 60, quality_quantile: float = 0.7) -> pd.Series:
    """质量垃圾轮动

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别高质量股和低质量股之间的轮动。

    Args:
        data: 价格数据
        window: 计算窗口
        quality_quantile: 质量分位数

    Returns:
        pd.Series: 质量垃圾轮动因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 使用波动率和收益率的比率作为质量代理
        # 高质量 = 高收益低波动
        rolling_returns = returns.rolling(window=window, min_periods=window // 2).mean()
        rolling_vol = returns.rolling(window=window, min_periods=window // 2).std()

        quality_scores = rolling_returns / (rolling_vol + 1e-8)

        # 计算质量轮动
        rotation_series = []

        for idx in data.index:
            if idx not in quality_scores.index or idx not in returns.index:
                rotation_series.append(0.0)
                continue

            # 获取当期质量评分
            scores = quality_scores.loc[idx]

            # 选择高质量股和低质量股
            quality_stocks = scores.nlargest(int(len(scores) * quality_quantile))
            junk_stocks = scores.nsmallest(int(len(scores) * (1 - quality_quantile)))

            # 计算轮动(质量股收益 - 垃圾股收益)
            quality_return = returns.loc[idx, quality_stocks.index].mean()
            junk_return = returns.loc[idx, junk_stocks.index].mean()
            rotation = quality_return - junk_return

            rotation_series.append(rotation)

        result = pd.Series(rotation_series, index=data.index)
        result = result.fillna(0.0)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"质量垃圾轮动计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def low_volatility_anomaly(data: pd.DataFrame, window: int = 60) -> pd.Series:
    """低波动异象

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    捕捉低波动股票的超额收益异象。

    Args:
        data: 价格数据
        window: 波动率计算窗口

    Returns:
        pd.Series: 低波动异象因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 计算滚动波动率
        rolling_vol = returns.rolling(window=window, min_periods=window // 2).std()

        # 计算低波动异象
        anomaly_series = []

        for idx in data.index:
            if idx not in rolling_vol.index or idx not in returns.index:
                anomaly_series.append(0.0)
                continue

            # 获取当期波动率
            vols = rolling_vol.loc[idx]

            # 选择低波动股和高波动股
            low_vol_stocks = vols.nsmallest(int(len(vols) * 0.3))
            high_vol_stocks = vols.nlargest(int(len(vols) * 0.3))

            # 计算异象(低波动股收益 - 高波动股收益)
            low_vol_return = returns.loc[idx, low_vol_stocks.index].mean()
            high_vol_return = returns.loc[idx, high_vol_stocks.index].mean()
            anomaly = low_vol_return - high_vol_return

            anomaly_series.append(anomaly)

        result = pd.Series(anomaly_series, index=data.index)
        result = result.fillna(0.0)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"低波动异象计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def dividend_yield_cycle(data: pd.DataFrame, window: int = 120) -> pd.Series:
    """股息率周期

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别高股息股票的周期性表现。

    Args:
        data: 价格数据
        window: 周期识别窗口

    Returns:
        pd.Series: 股息率周期因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 使用价格倒数作为股息率代理(简化版本)
        # 实际应用中应使用真实股息率数据
        dividend_proxy = 1.0 / (data + 1e-8)

        # 标准化股息率代理
        dividend_normalized = (
            dividend_proxy - dividend_proxy.rolling(window=window // 2, min_periods=window // 4).mean()
        ) / (dividend_proxy.rolling(window=window // 2, min_periods=window // 4).std() + 1e-8)

        # 计算股息率周期
        cycle_series = []

        for idx in data.index:
            if idx not in dividend_normalized.index or idx not in returns.index:
                cycle_series.append(0.0)
                continue

            # 获取当期股息率
            dividends = dividend_normalized.loc[idx]

            # 选择高股息股
            high_div_stocks = dividends.nlargest(int(len(dividends) * 0.3))
            low_div_stocks = dividends.nsmallest(int(len(dividends) * 0.3))

            # 计算周期(高股息股收益 - 低股息股收益)
            high_div_return = returns.loc[idx, high_div_stocks.index].mean()
            low_div_return = returns.loc[idx, low_div_stocks.index].mean()
            cycle = high_div_return - low_div_return

            cycle_series.append(cycle)

        result = pd.Series(cycle_series, index=data.index)

        # 标准化周期
        result_normalized = (result - result.rolling(window=window, min_periods=window // 2).mean()) / (
            result.rolling(window=window, min_periods=window // 2).std() + 1e-8
        )

        result_normalized = result_normalized.fillna(0.0)

        return result_normalized

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"股息率周期计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def sector_rotation_signal(
    data: pd.DataFrame, sector_map: Optional[Dict[str, str]] = None, window: int = 60
) -> pd.Series:
    """行业轮动信号

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别行业之间的轮动信号。

    Args:
        data: 价格数据
        sector_map: 股票到行业的映射
        window: 计算窗口

    Returns:
        pd.Series: 行业轮动信号因子值
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 如果没有行业映射,使用聚类方法
        if sector_map is None:
            # 使用相关性聚类作为行业代理
            corr_matrix = returns.rolling(  # pylint: disable=unused-variable
                window=window, min_periods=window // 2
            ).corr()  # pylint: disable=unused-variable

            # 简化版本:使用平均相关性作为行业强度
            rotation_signal = returns.rolling(window=window // 2, min_periods=window // 4).mean().mean(axis=1)
            rotation_signal = rotation_signal.fillna(0.0)

            return rotation_signal

        # 使用行业映射计算轮动
        # 计算每个行业的平均收益
        sector_returns = {}
        for stock, sector in sector_map.items():
            if stock in returns.columns:
                if sector not in sector_returns:
                    sector_returns[sector] = []
                sector_returns[sector].append(stock)

        # 计算行业轮动信号
        rotation_series = []

        for idx in returns.index:
            # 计算各行业收益
            sector_perf = {}
            for sector, stocks in sector_returns.items():
                sector_perf[sector] = returns.loc[idx, stocks].mean()

            # 计算轮动信号(最强行业 - 最弱行业)
            if sector_perf:
                best_sector = max(sector_perf.values())
                worst_sector = min(sector_perf.values())
                rotation = best_sector - worst_sector
            else:
                rotation = 0.0

            rotation_series.append(rotation)

        result = pd.Series(rotation_series, index=data.index)
        result = result.fillna(0.0)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"行业轮动信号计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def factor_crowding_index(
    data: pd.DataFrame, window: int = 60, threshold: float = 0.7  # pylint: disable=unused-argument
) -> pd.Series:  # pylint: disable=unused-argument
    """因子拥挤指数

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别因子拥挤程度,预警风格反转风险。

    Args:
        data: 价格数据
        window: 计算窗口
        threshold: 拥挤阈值

    Returns:
        pd.Series: 因子拥挤指数
    """
    try:
        if data.empty:
            return pd.Series(dtype=np.float64)

        # 计算收益率
        returns = data.pct_change()

        # 计算滚动相关性矩阵
        rolling_corr = returns.rolling(window=window, min_periods=window // 2).corr()  # pylint: disable=unused-variable

        # 计算拥挤指数
        crowding_series = []

        for idx in data.index:
            try:
                # 获取当期相关性矩阵
                if idx in returns.index:
                    # 计算最近window期的相关性
                    recent_returns = returns.loc[:idx].tail(window)
                    if len(recent_returns) >= window // 2:
                        corr_matrix = recent_returns.corr()

                        # 计算平均相关性(排除对角线)
                        np.fill_diagonal(corr_matrix.values, np.nan)
                        avg_corr = corr_matrix.abs().mean().mean()

                        # 计算拥挤指数(高相关性 = 高拥挤)
                        crowding = avg_corr
                    else:
                        crowding = 0.0
                else:
                    crowding = 0.0

            except Exception:  # pylint: disable=broad-exception-caught
                crowding = 0.0

            crowding_series.append(crowding)

        result = pd.Series(crowding_series, index=data.index)
        result = result.fillna(0.0)

        # 标准化拥挤指数
        result_normalized = (result - result.rolling(window=window, min_periods=window // 2).mean()) / (
            result.rolling(window=window, min_periods=window // 2).std() + 1e-8
        )

        result_normalized = result_normalized.fillna(0.0)

        return result_normalized

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"因子拥挤指数计算失败: {e}")
        return pd.Series(0.0, index=data.index)
