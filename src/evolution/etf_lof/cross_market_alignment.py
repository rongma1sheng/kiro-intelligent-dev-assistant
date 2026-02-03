"""
跨市场数据对齐模块 (Cross-Market Data Alignment)

白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track
铁律9依据: 文档同步律

文档同步状态:
- ✅ 白皮书已定义（第四章 4.2.1）
- ✅ 任务列表已更新（Task 10.1）
- ✅ 设计文档已定义（design.md - Cross-Market Testing）
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class MarketType(Enum):
    """市场类型枚举

    白皮书依据: 第四章 4.2.1 因子Arena - 支持的市场类型
    """

    A_STOCK = "A股"
    HK_STOCK = "港股"
    US_STOCK = "美股"


class CrossMarketDataError(Exception):
    """跨市场数据错误基类"""


class InsufficientDataError(CrossMarketDataError):
    """数据不足错误"""


class MarketDataMismatchError(CrossMarketDataError):
    """市场数据不匹配错误"""


@dataclass
class AlignedMarketData:
    """对齐后的市场数据

    白皮书依据: 第四章 4.2.1 因子Arena - 跨市场数据模型

    Attributes:
        market_type: 市场类型
        data: 对齐后的数据DataFrame
        common_dates: 共同日期列表
        original_size: 原始数据大小
        aligned_size: 对齐后数据大小
    """

    market_type: MarketType
    data: pd.DataFrame
    common_dates: List[pd.Timestamp]
    original_size: int
    aligned_size: int

    def __post_init__(self):
        """验证数据完整性"""
        if self.data.empty:
            raise ValueError(f"市场 {self.market_type.value} 的对齐数据为空")

        if self.aligned_size <= 0:
            raise ValueError(f"对齐后数据大小必须 > 0，当前: {self.aligned_size}")

        if len(self.common_dates) != self.aligned_size:
            raise ValueError(f"共同日期数量 ({len(self.common_dates)}) 与对齐数据大小 " f"({self.aligned_size}) 不一致")


def align_cross_market_data(
    market_data_dict: Dict[MarketType, pd.DataFrame], min_overlap_days: int = 100
) -> Dict[MarketType, AlignedMarketData]:
    """对齐跨市场数据

    白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track数据对齐
    铁律6依据: 性能要求必须满足

    该函数处理不同市场的数据格式差异，找到共同的日期范围，
    并对齐所有市场的数据到相同的时间索引。

    Args:
        market_data_dict: 各市场数据字典 {market_type: dataframe}
                         DataFrame必须包含日期索引和必需的列
        min_overlap_days: 最小重叠天数要求，默认100天

    Returns:
        对齐后的市场数据字典 {market_type: AlignedMarketData}

    Raises:
        ValueError: 当市场数量 < 2时
        InsufficientDataError: 当重叠天数 < min_overlap_days时
        MarketDataMismatchError: 当数据格式不匹配时

    Example:
        >>> a_stock_data = pd.DataFrame(...)  # A股ETF数据
        >>> hk_stock_data = pd.DataFrame(...)  # 港股ETF数据
        >>> market_data = {
        ...     MarketType.A_STOCK: a_stock_data,
        ...     MarketType.HK_STOCK: hk_stock_data
        ... }
        >>> aligned_data = align_cross_market_data(market_data)
        >>> print(f"对齐后A股数据: {len(aligned_data[MarketType.A_STOCK].data)} 天")

    白皮书依据: 第四章 4.2.1 - 跨市场数据对齐
    Requirements: 6.1-6.6
    """
    # 验证输入
    if len(market_data_dict) < 2:
        raise ValueError(f"跨市场测试需要至少2个市场，当前: {len(market_data_dict)}")

    logger.info(f"开始跨市场数据对齐，市场数量: {len(market_data_dict)}, " f"最小重叠天数: {min_overlap_days}")

    # 验证每个市场的数据格式
    for market_type, data in market_data_dict.items():
        _validate_market_data_format(market_type, data)

    # 找到共同日期范围
    common_dates = _find_common_date_range(market_data_dict)

    # 验证重叠天数
    if len(common_dates) < min_overlap_days:
        raise InsufficientDataError(
            f"跨市场数据重叠天数不足: {len(common_dates)} 天 "
            f"(需要至少 {min_overlap_days} 天)\n"
            f"市场日期范围:\n"
            + "\n".join(
                [
                    f"  {market.value}: {data.index.min()} 到 {data.index.max()} " f"({len(data)} 天)"
                    for market, data in market_data_dict.items()
                ]
            )
        )

    logger.info(f"找到共同日期范围: {len(common_dates)} 天")

    # 对齐所有市场数据
    aligned_data = {}
    for market_type, data in market_data_dict.items():
        try:
            aligned = _align_single_market(market_type, data, common_dates)
            aligned_data[market_type] = aligned

            logger.info(
                f"市场 {market_type.value} 对齐完成: "
                f"{aligned.original_size} 天 -> {aligned.aligned_size} 天 "
                f"(保留率: {aligned.aligned_size / aligned.original_size:.1%})"
            )

        except Exception as e:
            logger.error(f"市场 {market_type.value} 数据对齐失败: {e}")
            raise MarketDataMismatchError(f"无法对齐市场 {market_type.value} 的数据: {e}") from e

    logger.info(f"跨市场数据对齐完成，共 {len(aligned_data)} 个市场，" f"共同日期: {len(common_dates)} 天")

    return aligned_data


def _validate_market_data_format(market_type: MarketType, data: pd.DataFrame) -> None:
    """验证市场数据格式

    Args:
        market_type: 市场类型
        data: 市场数据DataFrame

    Raises:
        MarketDataMismatchError: 当数据格式不符合要求时
    """
    if data.empty:
        raise MarketDataMismatchError(f"市场 {market_type.value} 的数据为空")

    # 验证索引是否为日期类型
    if not isinstance(data.index, pd.DatetimeIndex):
        raise MarketDataMismatchError(
            f"市场 {market_type.value} 的索引必须是DatetimeIndex类型，" f"当前类型: {type(data.index)}"
        )

    # 验证必需的列
    required_columns = ["close", "volume"]
    missing_columns = [col for col in required_columns if col not in data.columns]

    if missing_columns:
        raise MarketDataMismatchError(
            f"市场 {market_type.value} 缺少必需的列: {missing_columns}\n" f"当前列: {list(data.columns)}"
        )

    # 验证数据质量
    if data["close"].isna().all():
        raise MarketDataMismatchError(f"市场 {market_type.value} 的close列全部为NaN")

    # 使用显式转换避免numpy兼容性问题
    close_values = data["close"].values
    invalid_count = int(np.sum(close_values <= 0))
    if invalid_count > 0:
        logger.warning(f"市场 {market_type.value} 存在 {invalid_count} 个非正价格，" f"将在对齐时过滤")


def _find_common_date_range(market_data_dict: Dict[MarketType, pd.DataFrame]) -> List[pd.Timestamp]:
    """找到所有市场的共同日期范围

    白皮书依据: 第四章 4.2.1 - 跨市场日期对齐

    Args:
        market_data_dict: 各市场数据字典

    Returns:
        排序后的共同日期列表

    Raises:
        InsufficientDataError: 当没有共同日期时
    """
    # 提取所有市场的日期集合
    date_sets = []
    for market_type, data in market_data_dict.items():
        # 只保留有效数据的日期
        valid_mask = data["close"].notna() & (data["close"] > 0) & data["volume"].notna() & (data["volume"] >= 0)
        valid_dates = set(data[valid_mask].index)
        date_sets.append(valid_dates)

        logger.debug(f"市场 {market_type.value} 有效日期: {len(valid_dates)} 天")

    # 计算交集
    common_dates_set = set.intersection(*date_sets)

    if not common_dates_set:
        raise InsufficientDataError(
            "没有找到所有市场的共同日期\n"
            "各市场日期范围:\n"
            + "\n".join(
                [
                    f"  {market.value}: {data.index.min()} 到 {data.index.max()}"
                    for market, data in market_data_dict.items()
                ]
            )
        )

    # 排序并返回
    common_dates = sorted(list(common_dates_set))

    return common_dates


def _align_single_market(
    market_type: MarketType, data: pd.DataFrame, common_dates: List[pd.Timestamp]
) -> AlignedMarketData:
    """对齐单个市场的数据到共同日期范围

    Args:
        market_type: 市场类型
        data: 原始市场数据
        common_dates: 共同日期列表

    Returns:
        对齐后的市场数据

    Raises:
        MarketDataMismatchError: 当对齐失败时
    """
    original_size = len(data)

    # 选择共同日期的数据 - 使用reindex避免numpy兼容性问题
    try:
        # 将common_dates转换为DatetimeIndex
        common_dates_index = pd.DatetimeIndex(common_dates)
        # 使用reindex而不是loc来避免numpy兼容性问题
        aligned_data = data.reindex(common_dates_index).copy()
    except Exception as e:
        raise MarketDataMismatchError(f"市场 {market_type.value} 无法定位到共同日期: {e}") from e

    # 验证对齐后的数据
    if aligned_data.empty:
        raise MarketDataMismatchError(f"市场 {market_type.value} 对齐后数据为空")

    # 再次验证数据质量 - 使用numpy直接计算避免兼容性问题
    close_values = aligned_data["close"].values
    nan_count = int(np.sum(np.isnan(close_values.astype(float))))
    nan_ratio = nan_count / len(aligned_data)
    if nan_ratio > 0.1:
        logger.warning(f"市场 {market_type.value} 对齐后数据存在 {nan_ratio:.1%} 的NaN值")

    aligned_size = len(aligned_data)

    return AlignedMarketData(
        market_type=market_type,
        data=aligned_data,
        common_dates=common_dates,
        original_size=original_size,
        aligned_size=aligned_size,
    )


def calculate_cross_market_ic_correlation(factor_ic_dict: Dict[MarketType, float]) -> pd.DataFrame:
    """计算跨市场IC相关性矩阵

    白皮书依据: 第四章 4.2.1 - 跨市场IC相关性分析
    铁律5依据: 完整的文档字符串

    该函数计算因子在不同市场的IC值之间的相关性，
    用于评估因子的跨市场稳定性。

    Args:
        factor_ic_dict: 各市场的IC值字典 {market_type: ic_value}

    Returns:
        IC相关性矩阵（对称矩阵，对角线为1.0）

    Raises:
        ValueError: 当市场数量 < 2时
        ValueError: 当IC值包含NaN或无穷大时

    Example:
        >>> ic_values = {
        ...     MarketType.A_STOCK: 0.08,
        ...     MarketType.HK_STOCK: 0.06,
        ...     MarketType.US_STOCK: 0.07
        ... }
        >>> corr_matrix = calculate_cross_market_ic_correlation(ic_values)
        >>> print(corr_matrix)

    白皮书依据: 第四章 4.2.1 - IC相关性计算
    Requirements: 6.8
    """
    if len(factor_ic_dict) < 2:
        raise ValueError(f"需要至少2个市场的IC值，当前: {len(factor_ic_dict)}")

    # 验证IC值有效性
    for market_type, ic_value in factor_ic_dict.items():
        if not np.isfinite(ic_value):
            raise ValueError(f"市场 {market_type.value} 的IC值无效: {ic_value}")

    logger.info(f"计算跨市场IC相关性，市场数量: {len(factor_ic_dict)}")

    # 创建IC值Series
    ic_series = pd.Series(  # pylint: disable=unused-variable
        {market.value: ic for market, ic in factor_ic_dict.items()}
    )  # pylint: disable=unused-variable

    # 计算相关性矩阵
    # 注意：对于单个IC值，我们使用简化的相关性计算
    # 实际应用中应该使用时间序列的IC值
    markets = list(factor_ic_dict.keys())
    n_markets = len(markets)

    # 创建相关性矩阵
    corr_matrix = pd.DataFrame(np.eye(n_markets), index=[m.value for m in markets], columns=[m.value for m in markets])

    # 计算非对角线元素
    # 使用IC值的相似度作为相关性的近似
    for i, market_i in enumerate(markets):
        for j, market_j in enumerate(markets):
            if i < j:
                ic_i = factor_ic_dict[market_i]
                ic_j = factor_ic_dict[market_j]

                # 相关性近似: 1 - abs(ic_i - ic_j) / max(abs(ic_i), abs(ic_j))
                max_ic = max(abs(ic_i), abs(ic_j))
                if max_ic > 0:
                    correlation = 1 - abs(ic_i - ic_j) / max_ic
                else:
                    correlation = 1.0

                # 确保相关性在[-1, 1]范围内
                correlation = np.clip(correlation, -1.0, 1.0)

                corr_matrix.iloc[i, j] = correlation
                corr_matrix.iloc[j, i] = correlation

    logger.info(
        f"IC相关性矩阵计算完成，平均相关性: " f"{corr_matrix.values[np.triu_indices(n_markets, k=1)].mean():.4f}"
    )

    return corr_matrix


def detect_market_specific_factors(
    factor_ic_dict: Dict[MarketType, float], ic_std_threshold: float = 0.05, min_correlation: float = 0.3
) -> Tuple[bool, Dict[str, float]]:
    """检测市场特定因子

    白皮书依据: 第四章 4.2.1 - 市场特定因子识别
    铁律3依据: 完整的错误处理

    该函数通过分析因子在不同市场的IC值分布，
    识别是否为市场特定因子（只在特定市场有效）。

    判断标准:
    1. IC值标准差 > ic_std_threshold: 表示跨市场表现差异大
    2. 跨市场IC相关性 < min_correlation: 表示跨市场一致性差

    Args:
        factor_ic_dict: 各市场的IC值字典
        ic_std_threshold: IC标准差阈值，默认0.05
        min_correlation: 最小相关性阈值，默认0.3

    Returns:
        (is_market_specific, metrics) 元组
        - is_market_specific: 是否为市场特定因子
        - metrics: 诊断指标字典

    Raises:
        ValueError: 当输入数据无效时

    Example:
        >>> ic_values = {
        ...     MarketType.A_STOCK: 0.10,
        ...     MarketType.HK_STOCK: 0.02,
        ...     MarketType.US_STOCK: 0.01
        ... }
        >>> is_specific, metrics = detect_market_specific_factors(ic_values)
        >>> if is_specific:
        ...     print(f"该因子为市场特定因子，IC标准差: {metrics['ic_std']:.4f}")

    白皮书依据: 第四章 4.2.1 - 市场特定因子检测
    Requirements: 6.7, 6.9
    """
    if len(factor_ic_dict) < 2:
        raise ValueError(f"需要至少2个市场的IC值，当前: {len(factor_ic_dict)}")

    logger.info(f"检测市场特定因子，市场数量: {len(factor_ic_dict)}")

    # 计算IC统计量
    ic_values = np.array(list(factor_ic_dict.values()))
    ic_mean = np.mean(ic_values)
    ic_std = np.std(ic_values)
    ic_min = np.min(ic_values)
    ic_max = np.max(ic_values)

    logger.info(f"IC统计: mean={ic_mean:.4f}, std={ic_std:.4f}, " f"min={ic_min:.4f}, max={ic_max:.4f}")

    # 计算跨市场IC相关性
    try:
        corr_matrix = calculate_cross_market_ic_correlation(factor_ic_dict)

        # 提取上三角相关系数（排除对角线）
        n_markets = len(factor_ic_dict)
        upper_triangle_indices = np.triu_indices(n_markets, k=1)
        correlations = corr_matrix.values[upper_triangle_indices]

        avg_correlation = np.mean(correlations)
        min_correlation_value = np.min(correlations)

        logger.info(f"跨市场相关性: avg={avg_correlation:.4f}, " f"min={min_correlation_value:.4f}")

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"计算跨市场相关性失败: {e}")
        avg_correlation = 0.0
        min_correlation_value = 0.0

    # 判断是否为市场特定因子
    is_market_specific = bool(ic_std > ic_std_threshold or avg_correlation < min_correlation)

    # 构建诊断指标
    metrics = {
        "ic_mean": float(ic_mean),
        "ic_std": float(ic_std),
        "ic_min": float(ic_min),
        "ic_max": float(ic_max),
        "avg_correlation": float(avg_correlation),
        "min_correlation": float(min_correlation_value),
        "ic_std_threshold": ic_std_threshold,
        "min_correlation_threshold": min_correlation,
        "std_exceeded": ic_std > ic_std_threshold,
        "correlation_below_threshold": avg_correlation < min_correlation,
    }

    if is_market_specific:
        logger.warning(
            f"检测到市场特定因子: "
            f"IC标准差={ic_std:.4f} (阈值={ic_std_threshold}), "
            f"平均相关性={avg_correlation:.4f} (阈值={min_correlation})"
        )
    else:
        logger.info(f"因子具有良好的跨市场稳定性: " f"IC标准差={ic_std:.4f}, 平均相关性={avg_correlation:.4f}")

    return is_market_specific, metrics
