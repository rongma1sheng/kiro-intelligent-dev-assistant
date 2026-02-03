"""网络关系因子算子

白皮书依据: 第四章 4.1.13 网络关系因子挖掘器
"""

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class NetworkRelationshipConfig:
    """网络关系因子配置

    Attributes:
        correlation_window: 相关性计算窗口期
        min_correlation: 最小相关性阈值
        centrality_method: 中心性计算方法 ('degree', 'betweenness', 'closeness', 'eigenvector')
        network_threshold: 网络构建阈值
        max_nodes: 最大节点数
        propagation_steps: 信息传播步数
    """

    correlation_window: int = 60
    min_correlation: float = 0.3
    centrality_method: str = "degree"
    network_threshold: float = 0.5
    max_nodes: int = 100
    propagation_steps: int = 3


def stock_correlation_network(data: pd.DataFrame, window: int = 60, threshold: float = 0.5) -> pd.Series:
    """股票相关性网络

    白皮书依据: 第四章 4.1.13 - stock_correlation_network

    构建股票相关性网络，计算每只股票的网络连接度。
    高连接度表示该股票与市场其他股票高度相关。

    Args:
        data: 价格数据，列为股票代码
        window: 滚动窗口期
        threshold: 相关性阈值

    Returns:
        pd.Series: 网络连接度因子
    """
    try:
        if data.empty or len(data.columns) < 2:
            logger.warning("数据不足，无法构建相关性网络")
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change()

        # 初始化结果
        network_degree = pd.DataFrame(0.0, index=data.index, columns=data.columns)

        # 滚动计算相关性网络
        for i in range(window, len(data)):
            window_returns = returns.iloc[i - window : i]

            # 计算相关性矩阵
            corr_matrix = window_returns.corr()

            # 构建网络：相关性超过阈值的连接
            adjacency = (corr_matrix.abs() > threshold).astype(int)

            # 去除自连接
            np.fill_diagonal(adjacency.values, 0)

            # 计算度中心性（连接数）
            degree = adjacency.sum(axis=1)

            # 归一化
            degree_norm = degree / (len(data.columns) - 1)

            network_degree.iloc[i] = degree_norm

        # 返回平均网络度
        result = network_degree.mean(axis=1)

        # 标准化
        result = (result - result.mean()) / (result.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"股票相关性网络计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def supply_chain_network(
    data: pd.DataFrame, industry_map: Optional[Dict[str, str]] = None, window: int = 60
) -> pd.Series:
    """供应链网络分析

    白皮书依据: 第四章 4.1.13 - supply_chain_network

    分析供应链网络中的传导效应。
    上游行业的变化会传导到下游行业。

    Args:
        data: 价格数据
        industry_map: 股票到行业的映射
        window: 滚动窗口期

    Returns:
        pd.Series: 供应链传导因子
    """
    try:  # pylint: disable=r1702
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 如果没有行业映射，使用简化版本
        if industry_map is None:
            # 使用股票间的领先滞后关系作为代理
            returns = data.pct_change()

            # 计算每只股票的领先指标
            lead_factor = pd.DataFrame(0.0, index=data.index, columns=data.columns)

            for col in data.columns:
                # 计算该股票与其他股票的领先相关性
                for lag in range(1, 6):  # 检查1-5天的领先关系
                    lagged_returns = returns[col].shift(lag)

                    for other_col in data.columns:
                        if other_col != col:
                            corr = lagged_returns.rolling(window).corr(returns[other_col])
                            lead_factor[col] += corr.abs()

            # 归一化
            result = lead_factor.mean(axis=1)
            result = (result - result.mean()) / (result.std() + 1e-8)

            return result.fillna(0.0)

        # 完整版本：使用行业映射
        returns = data.pct_change()
        supply_chain_factor = pd.Series(0.0, index=data.index)

        # 定义简化的供应链关系（上游->下游）
        supply_chain_links = {
            "原材料": ["制造业", "化工"],
            "制造业": ["零售", "服务业"],
            "能源": ["制造业", "交通运输"],
            "科技": ["制造业", "服务业"],
        }

        # 计算供应链传导效应
        for upstream, downstreams in supply_chain_links.items():
            # 获取上游股票
            upstream_stocks = [s for s, ind in industry_map.items() if ind == upstream]
            if not upstream_stocks:
                continue

            # 计算上游平均收益
            upstream_returns = returns[upstream_stocks].mean(axis=1)

            # 对每个下游行业
            for downstream in downstreams:
                downstream_stocks = [s for s, ind in industry_map.items() if ind == downstream]
                if not downstream_stocks:
                    continue

                # 计算传导效应（上游收益对下游收益的影响）
                for stock in downstream_stocks:
                    if stock in data.columns:
                        # 使用滞后相关性
                        lagged_upstream = upstream_returns.shift(1)
                        corr = lagged_upstream.rolling(window).corr(returns[stock])
                        supply_chain_factor += corr.abs()

        # 标准化
        result = (supply_chain_factor - supply_chain_factor.mean()) / (supply_chain_factor.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"供应链网络分析失败: {e}")
        return pd.Series(0.0, index=data.index)


def capital_flow_network(data: pd.DataFrame, volume: Optional[pd.DataFrame] = None, window: int = 20) -> pd.Series:
    """资金流网络

    白皮书依据: 第四章 4.1.13 - capital_flow_network

    分析资金在股票间的流动网络。
    资金流入的股票往往表现更好。

    Args:
        data: 价格数据
        volume: 成交量数据
        window: 滚动窗口期

    Returns:
        pd.Series: 资金流网络因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change()

        # 如果有成交量数据，使用成交量加权
        if volume is not None and not volume.empty:
            # 计算资金流量 = 价格变化 * 成交量
            money_flow = returns * volume
        else:
            # 使用简化版本：仅使用收益率
            money_flow = returns

        # 计算资金流网络
        capital_flow_factor = pd.DataFrame(0.0, index=data.index, columns=data.columns)

        for i in range(window, len(data)):
            window_flow = money_flow.iloc[i - window : i]

            # 计算资金流相关性
            flow_corr = window_flow.corr()

            # 计算净资金流入（正相关的资金流入）
            net_inflow = (flow_corr > 0).sum(axis=1) - (flow_corr < 0).sum(axis=1)

            # 归一化
            net_inflow_norm = net_inflow / len(data.columns)

            capital_flow_factor.iloc[i] = net_inflow_norm

        # 返回平均资金流
        result = capital_flow_factor.mean(axis=1)

        # 标准化
        result = (result - result.mean()) / (result.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"资金流网络计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def information_propagation(data: pd.DataFrame, window: int = 20, max_steps: int = 3) -> pd.Series:
    """信息传播网络

    白皮书依据: 第四章 4.1.13 - information_propagation

    分析信息在股票网络中的传播效应。
    信息从领先股票传播到滞后股票。

    Args:
        data: 价格数据
        window: 滚动窗口期
        max_steps: 最大传播步数

    Returns:
        pd.Series: 信息传播因子
    """
    try:  # pylint: disable=r1702
        if data.empty or len(data.columns) < 2:
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change()

        # 初始化传播因子
        propagation_factor = pd.DataFrame(0.0, index=data.index, columns=data.columns)

        # 对每个时间窗口
        for i in range(window, len(data)):
            window_returns = returns.iloc[i - window : i]

            # 计算领先滞后矩阵
            lead_lag_matrix = np.zeros((len(data.columns), len(data.columns)))

            for j, col1 in enumerate(data.columns):
                for k, col2 in enumerate(data.columns):
                    if j != k:
                        # 计算col1领先col2的相关性
                        for lag in range(1, max_steps + 1):
                            lagged = window_returns[col1].shift(lag)
                            corr = lagged.corr(window_returns[col2])
                            if not np.isnan(corr):
                                lead_lag_matrix[j, k] += abs(corr)

            # 计算信息传播中心性（作为信息源的程度）
            info_centrality = lead_lag_matrix.sum(axis=1)

            # 归一化
            if info_centrality.sum() > 0:
                info_centrality = info_centrality / info_centrality.sum()

            propagation_factor.iloc[i] = info_centrality

        # 返回平均传播因子
        result = propagation_factor.mean(axis=1)

        # 标准化
        result = (result - result.mean()) / (result.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"信息传播网络计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def industry_ecosystem(
    data: pd.DataFrame, industry_map: Optional[Dict[str, str]] = None, window: int = 60
) -> pd.Series:
    """行业生态网络

    白皮书依据: 第四章 4.1.13 - industry_ecosystem

    分析行业生态系统中的相互依赖关系。
    生态系统中心行业的变化影响整个生态。

    Args:
        data: 价格数据
        industry_map: 股票到行业的映射
        window: 滚动窗口期

    Returns:
        pd.Series: 行业生态因子
    """
    try:
        if data.empty:
            return pd.Series(0.0, index=data.index)

        # 如果没有行业映射，使用简化版本
        if industry_map is None:
            # 使用聚类方法识别生态群组
            returns = data.pct_change()

            # 计算相关性矩阵
            returns.rolling(window).corr()

            # 简化：使用平均相关性作为生态中心性
            ecosystem_factor = pd.Series(0.0, index=data.index)

            for i in range(window, len(data)):
                window_returns = returns.iloc[i - window : i]
                corr = window_returns.corr()

                # 计算每只股票的平均相关性（生态中心性）
                avg_corr = corr.abs().mean(axis=1)
                ecosystem_factor.iloc[i] = avg_corr.mean()

            # 标准化
            result = (ecosystem_factor - ecosystem_factor.mean()) / (ecosystem_factor.std() + 1e-8)

            return result.fillna(0.0)

        # 完整版本：使用行业映射
        returns = data.pct_change()
        ecosystem_factor = pd.Series(0.0, index=data.index)

        # 按行业分组
        industry_groups = {}
        for stock, industry in industry_map.items():
            if stock in data.columns:
                if industry not in industry_groups:
                    industry_groups[industry] = []
                industry_groups[industry].append(stock)

        # 计算行业间相关性
        for i in range(window, len(data)):
            window_returns = returns.iloc[i - window : i]

            # 计算每个行业的平均收益
            industry_returns = {}
            for industry, stocks in industry_groups.items():
                if stocks:
                    industry_returns[industry] = window_returns[stocks].mean(axis=1)

            # 计算行业间相关性网络
            if len(industry_returns) > 1:
                industry_df = pd.DataFrame(industry_returns)
                industry_corr = industry_df.corr()

                # 计算生态中心性（行业间平均相关性）
                ecosystem_centrality = industry_corr.abs().mean().mean()
                ecosystem_factor.iloc[i] = ecosystem_centrality

        # 标准化
        result = (ecosystem_factor - ecosystem_factor.mean()) / (ecosystem_factor.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"行业生态网络计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def network_centrality(
    data: pd.DataFrame, method: str = "degree", window: int = 60, threshold: float = 0.5
) -> pd.Series:
    """网络中心性指标

    白皮书依据: 第四章 4.1.13 - network_centrality

    计算股票在网络中的中心性指标。
    支持多种中心性度量：度中心性、介数中心性、接近中心性、特征向量中心性。

    Args:
        data: 价格数据
        method: 中心性计算方法 ('degree', 'betweenness', 'closeness', 'eigenvector')
        window: 滚动窗口期
        threshold: 网络构建阈值

    Returns:
        pd.Series: 网络中心性因子
    """
    try:
        if data.empty or len(data.columns) < 2:
            return pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = data.pct_change()

        # 初始化中心性因子
        centrality_factor = pd.DataFrame(0.0, index=data.index, columns=data.columns)

        # 滚动计算中心性
        for i in range(window, len(data)):
            window_returns = returns.iloc[i - window : i]

            # 计算相关性矩阵
            corr_matrix = window_returns.corr()

            # 构建邻接矩阵
            adjacency = (corr_matrix.abs() > threshold).astype(float)
            np.fill_diagonal(adjacency.values, 0)

            # 根据方法计算中心性
            if method == "degree":
                # 度中心性：连接数
                centrality = adjacency.sum(axis=1)
                centrality = centrality / (len(data.columns) - 1)

            elif method == "eigenvector":
                # 特征向量中心性：使用幂迭代法
                centrality = _calculate_eigenvector_centrality(adjacency.values)
                centrality = pd.Series(centrality, index=data.columns)

            elif method == "closeness":
                # 接近中心性：到其他节点的平均距离的倒数
                centrality = _calculate_closeness_centrality(adjacency.values)
                centrality = pd.Series(centrality, index=data.columns)

            elif method == "betweenness":
                # 介数中心性：经过该节点的最短路径数
                centrality = _calculate_betweenness_centrality(adjacency.values)
                centrality = pd.Series(centrality, index=data.columns)

            else:
                logger.warning(f"未知的中心性方法: {method}，使用度中心性")
                centrality = adjacency.sum(axis=1) / (len(data.columns) - 1)

            centrality_factor.iloc[i] = centrality

        # 返回平均中心性
        result = centrality_factor.mean(axis=1)

        # 标准化
        result = (result - result.mean()) / (result.std() + 1e-8)

        return result.fillna(0.0)

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"网络中心性计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def _calculate_eigenvector_centrality(adjacency: np.ndarray, max_iter: int = 100) -> np.ndarray:
    """计算特征向量中心性

    使用幂迭代法计算邻接矩阵的主特征向量。

    Args:
        adjacency: 邻接矩阵
        max_iter: 最大迭代次数

    Returns:
        np.ndarray: 特征向量中心性
    """
    n = adjacency.shape[0]
    centrality = np.ones(n) / n

    for _ in range(max_iter):
        new_centrality = adjacency @ centrality
        norm = np.linalg.norm(new_centrality)

        if norm == 0:
            break

        new_centrality = new_centrality / norm

        # 检查收敛
        if np.allclose(centrality, new_centrality, atol=1e-6):
            break

        centrality = new_centrality

    return centrality


def _calculate_closeness_centrality(adjacency: np.ndarray) -> np.ndarray:
    """计算接近中心性

    接近中心性 = 1 / (到其他所有节点的平均距离)

    Args:
        adjacency: 邻接矩阵

    Returns:
        np.ndarray: 接近中心性
    """
    n = adjacency.shape[0]
    centrality = np.zeros(n)

    # 计算最短路径矩阵（使用Floyd-Warshall算法的简化版本）
    # 这里使用简化版本：直接使用邻接矩阵
    distance_matrix = np.where(adjacency > 0, 1, np.inf)
    np.fill_diagonal(distance_matrix, 0)

    for i in range(n):
        distances = distance_matrix[i]
        finite_distances = distances[np.isfinite(distances)]

        if len(finite_distances) > 1:
            avg_distance = finite_distances[finite_distances > 0].mean()
            if avg_distance > 0:
                centrality[i] = 1 / avg_distance

    return centrality


def _calculate_betweenness_centrality(adjacency: np.ndarray) -> np.ndarray:
    """计算介数中心性

    介数中心性 = 经过该节点的最短路径数 / 总最短路径数

    Args:
        adjacency: 邻接矩阵

    Returns:
        np.ndarray: 介数中心性
    """
    n = adjacency.shape[0]
    centrality = np.zeros(n)

    # 简化版本：使用度中心性作为代理
    # 完整的介数中心性计算需要BFS/DFS，计算复杂度较高
    degree = adjacency.sum(axis=1)

    if degree.sum() > 0:
        centrality = degree / degree.sum()

    return centrality
