"""因子组合与交互因子算子

白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器
"""

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class FactorCombinationConfig:
    """因子组合配置

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器
    """

    # 窗口期参数
    interaction_window: int = 60  # 交互项计算窗口
    timing_window: int = 120  # 择时信号窗口
    synergy_window: int = 90  # 协同效应窗口

    # 阈值参数
    correlation_threshold: float = 0.3  # 相关性阈值
    timing_threshold: float = 0.5  # 择时阈值
    synergy_threshold: float = 0.6  # 协同阈值

    # 组合参数
    max_factors: int = 5  # 最大因子数量
    interaction_order: int = 2  # 交互阶数
    neutralization_method: str = "orthogonal"  # 中性化方法


def factor_interaction_term(factor1: pd.Series, factor2: pd.Series, method: str = "multiply") -> pd.Series:
    """因子交互项

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    计算两个因子之间的交互效应。

    Args:
        factor1: 第一个因子
        factor2: 第二个因子
        method: 交互方法 ('multiply', 'add', 'divide', 'subtract')

    Returns:
        pd.Series: 交互因子值
    """
    try:
        if factor1.empty or factor2.empty:
            return pd.Series(dtype=np.float64)

        # 对齐索引
        common_index = factor1.index.intersection(factor2.index)
        f1 = factor1.loc[common_index]
        f2 = factor2.loc[common_index]

        # 计算交互项
        if method == "multiply":
            interaction = f1 * f2
        elif method == "add":
            interaction = f1 + f2
        elif method == "divide":
            interaction = f1 / (f2 + 1e-8)
        elif method == "subtract":
            interaction = f1 - f2
        else:
            logger.warning(f"未知的交互方法: {method}, 使用multiply")
            interaction = f1 * f2

        # 标准化
        interaction = (interaction - interaction.mean()) / (interaction.std() + 1e-8)
        interaction = interaction.fillna(0.0)

        return interaction

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"因子交互项计算失败: {e}")
        return pd.Series(0.0, index=factor1.index if not factor1.empty else factor2.index)


def nonlinear_factor_combination(
    factors: Dict[str, pd.Series], method: str = "polynomial", degree: int = 2
) -> pd.Series:
    """非线性因子组合

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    使用非线性方法组合多个因子。

    Args:
        factors: 因子字典 {name: series}
        method: 组合方法 ('polynomial', 'exponential', 'logarithmic')
        degree: 多项式阶数

    Returns:
        pd.Series: 组合因子值
    """
    try:
        if not factors:
            return pd.Series(dtype=np.float64)

        # 获取公共索引
        common_index = None
        for factor in factors.values():
            if common_index is None:
                common_index = factor.index
            else:
                common_index = common_index.intersection(factor.index)

        if common_index is None or len(common_index) == 0:
            return pd.Series(dtype=np.float64)

        # 对齐所有因子
        aligned_factors = {name: factor.loc[common_index] for name, factor in factors.items()}

        # 转换为DataFrame
        factor_df = pd.DataFrame(aligned_factors)

        # 非线性组合
        if method == "polynomial":
            # 多项式组合
            result = pd.Series(0.0, index=common_index)
            for col in factor_df.columns:
                for d in range(1, degree + 1):
                    result += factor_df[col] ** d / d

        elif method == "exponential":
            # 指数组合
            result = pd.Series(1.0, index=common_index)
            for col in factor_df.columns:
                result *= np.exp(factor_df[col] / len(factors))

        elif method == "logarithmic":
            # 对数组合
            result = pd.Series(0.0, index=common_index)
            for col in factor_df.columns:
                # 确保正值
                shifted = factor_df[col] - factor_df[col].min() + 1
                result += np.log(shifted + 1e-8)

        else:
            logger.warning(f"未知的组合方法: {method}, 使用polynomial")
            result = factor_df.mean(axis=1)

        # 标准化
        result = (result - result.mean()) / (result.std() + 1e-8)
        result = result.fillna(0.0)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"非线性因子组合计算失败: {e}")
        return pd.Series(0.0, index=list(factors.values())[0].index if factors else pd.Index([]))


def conditional_factor_exposure(factor: pd.Series, condition: pd.Series, threshold: float = 0.0) -> pd.Series:
    """条件因子暴露

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    根据条件调整因子暴露度。

    Args:
        factor: 原始因子
        condition: 条件因子
        threshold: 条件阈值

    Returns:
        pd.Series: 条件因子值
    """
    try:
        if factor.empty or condition.empty:
            return pd.Series(dtype=np.float64)

        # 对齐索引
        common_index = factor.index.intersection(condition.index)
        f = factor.loc[common_index]
        c = condition.loc[common_index]

        # 标准化条件
        c_normalized = (c - c.mean()) / (c.std() + 1e-8)

        # 条件暴露
        # 当条件满足时增强因子,否则减弱
        condition_mask = c_normalized > threshold

        conditional_factor = f.copy()
        conditional_factor[condition_mask] = f[condition_mask] * (1 + c_normalized[condition_mask])
        conditional_factor[~condition_mask] = f[~condition_mask] * (1 + c_normalized[~condition_mask] * 0.5)

        # 标准化
        conditional_factor = (conditional_factor - conditional_factor.mean()) / (conditional_factor.std() + 1e-8)
        conditional_factor = conditional_factor.fillna(0.0)

        return conditional_factor

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"条件因子暴露计算失败: {e}")
        return pd.Series(0.0, index=factor.index if not factor.empty else condition.index)


def factor_timing_signal(factor: pd.Series, returns: pd.Series, window: int = 120) -> pd.Series:
    """因子择时信号

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    生成因子的择时信号,识别因子有效期。

    Args:
        factor: 因子值
        returns: 收益率
        window: 择时窗口

    Returns:
        pd.Series: 择时信号
    """
    try:
        if factor.empty or returns.empty:
            return pd.Series(dtype=np.float64)

        # 对齐索引
        common_index = factor.index.intersection(returns.index)
        f = factor.loc[common_index]
        r = returns.loc[common_index]

        # 计算滚动IC
        rolling_ic = pd.Series(index=common_index, dtype=float)

        for i in range(len(common_index)):
            if i < window:
                rolling_ic.iloc[i] = 0.0
                continue

            # 计算窗口内的IC
            window_factor = f.iloc[i - window : i]
            window_returns = r.iloc[i - window : i]

            if len(window_factor) > 0 and len(window_returns) > 0:
                ic = window_factor.corr(window_returns)
                rolling_ic.iloc[i] = ic if not np.isnan(ic) else 0.0
            else:
                rolling_ic.iloc[i] = 0.0

        # 生成择时信号
        # IC > 0 表示因子有效,IC < 0 表示因子失效
        timing_signal = rolling_ic.copy()

        # 平滑信号
        timing_signal = timing_signal.rolling(window=window // 4, min_periods=1).mean()

        # 标准化
        timing_signal = (timing_signal - timing_signal.mean()) / (timing_signal.std() + 1e-8)
        timing_signal = timing_signal.fillna(0.0)

        return timing_signal

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"因子择时信号计算失败: {e}")
        return pd.Series(0.0, index=factor.index if not factor.empty else returns.index)


def multi_factor_synergy(factors: Dict[str, pd.Series], window: int = 90) -> pd.Series:
    """多因子协同

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    识别多个因子之间的协同效应。

    Args:
        factors: 因子字典 {name: series}
        window: 协同窗口

    Returns:
        pd.Series: 协同因子值
    """
    try:
        if not factors or len(factors) < 2:
            return pd.Series(dtype=np.float64)

        # 获取公共索引
        common_index = None
        for factor in factors.values():
            if common_index is None:
                common_index = factor.index
            else:
                common_index = common_index.intersection(factor.index)

        if common_index is None or len(common_index) == 0:
            return pd.Series(dtype=np.float64)

        # 对齐所有因子
        aligned_factors = {name: factor.loc[common_index] for name, factor in factors.items()}
        factor_df = pd.DataFrame(aligned_factors)

        # 计算滚动相关性矩阵
        synergy_series = pd.Series(index=common_index, dtype=float)

        for i in range(len(common_index)):
            if i < window:
                synergy_series.iloc[i] = 0.0
                continue

            # 计算窗口内的相关性矩阵
            window_data = factor_df.iloc[i - window : i]

            if len(window_data) > 0:
                corr_matrix = window_data.corr()

                # 计算平均相关性(排除对角线)
                np.fill_diagonal(corr_matrix.values, np.nan)
                avg_corr = corr_matrix.abs().mean().mean()

                # 协同效应 = 平均相关性 * 因子数量
                synergy = avg_corr * len(factors) if not np.isnan(avg_corr) else 0.0
            else:
                synergy = 0.0

            synergy_series.iloc[i] = synergy

        # 标准化
        synergy_series = (synergy_series - synergy_series.mean()) / (synergy_series.std() + 1e-8)
        synergy_series = synergy_series.fillna(0.0)

        return synergy_series

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"多因子协同计算失败: {e}")
        return pd.Series(0.0, index=list(factors.values())[0].index if factors else pd.Index([]))


def factor_neutralization(
    factor: pd.Series, neutralize_factors: Dict[str, pd.Series], method: str = "orthogonal"
) -> pd.Series:
    """因子中性化

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    对因子进行中性化处理,去除其他因子的影响。

    Args:
        factor: 待中性化的因子
        neutralize_factors: 需要中性化的因子字典
        method: 中性化方法 ('orthogonal', 'regression')

    Returns:
        pd.Series: 中性化后的因子
    """
    try:
        if factor.empty or not neutralize_factors:
            return factor.copy()

        # 获取公共索引
        common_index = factor.index
        for nf in neutralize_factors.values():
            common_index = common_index.intersection(nf.index)

        if len(common_index) == 0:
            return factor.copy()

        # 对齐所有因子
        f = factor.loc[common_index]
        nf_df = pd.DataFrame({name: nf.loc[common_index] for name, nf in neutralize_factors.items()})

        if method == "orthogonal":
            # 正交化方法
            neutralized = f.copy()

            for col in nf_df.columns:
                # 计算投影
                nf_col = nf_df[col]
                projection = (neutralized.dot(nf_col) / (nf_col.dot(nf_col) + 1e-8)) * nf_col

                # 去除投影
                neutralized = neutralized - projection

        elif method == "regression":
            # 回归方法
            from sklearn.linear_model import LinearRegression  # pylint: disable=import-outside-toplevel

            # 准备数据
            X = nf_df.values
            y = f.values

            # 拟合回归
            model = LinearRegression()
            model.fit(X, y)

            # 计算残差
            predictions = model.predict(X)
            neutralized = pd.Series(y - predictions, index=common_index)

        else:
            logger.warning(f"未知的中性化方法: {method}, 使用orthogonal")
            neutralized = f.copy()

        # 标准化
        neutralized = (neutralized - neutralized.mean()) / (neutralized.std() + 1e-8)
        neutralized = neutralized.fillna(0.0)

        return neutralized

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"因子中性化计算失败: {e}")
        return factor.copy()
