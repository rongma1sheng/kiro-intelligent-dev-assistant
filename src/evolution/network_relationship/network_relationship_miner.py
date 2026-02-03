"""网络关系因子挖掘器

白皮书依据: 第四章 4.1.13 网络关系因子挖掘器
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner, Individual
from .network_relationship_operators import (
    NetworkRelationshipConfig,
    capital_flow_network,
    industry_ecosystem,
    information_propagation,
    network_centrality,
    stock_correlation_network,
    supply_chain_network,
)


class NetworkRelationshipFactorMiner(GeneticMiner):
    """网络关系因子挖掘器

    白皮书依据: 第四章 4.1.13 网络关系因子挖掘器

    使用图论和网络分析方法，挖掘股票之间的复杂关系和传导效应。

    核心算子 (6个):
    1. stock_correlation_network - 股票相关性网络
    2. supply_chain_network - 供应链网络分析
    3. capital_flow_network - 资金流网络
    4. information_propagation - 信息传播网络
    5. industry_ecosystem - 行业生态网络
    6. network_centrality - 网络中心性指标

    应用场景:
    - 识别核心股票和边缘股票
    - 分析行业传导效应
    - 捕捉资金流向
    - 预测信息传播路径
    """

    def __init__(
        self, config: Optional[EvolutionConfig] = None, network_config: Optional[NetworkRelationshipConfig] = None
    ):
        """初始化网络关系因子挖掘器

        Args:
            config: 进化配置
            network_config: 网络关系配置
        """
        if config is None:
            config = EvolutionConfig()

        super().__init__(config=config)

        self.network_config = network_config or NetworkRelationshipConfig()

        # 注册网络关系算子
        self._register_network_operators()

        logger.info(
            f"NetworkRelationshipFactorMiner初始化完成: "
            f"correlation_window={self.network_config.correlation_window}, "
            f"centrality_method={self.network_config.centrality_method}"
        )

    def _register_network_operators(self):
        """注册网络关系算子到算子白名单"""
        self.network_operators = {
            "stock_correlation_network": stock_correlation_network,
            "supply_chain_network": supply_chain_network,
            "capital_flow_network": capital_flow_network,
            "information_propagation": information_propagation,
            "industry_ecosystem": industry_ecosystem,
            "network_centrality": network_centrality,
        }

        # 确保operator_whitelist存在
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        # 添加到白名单
        for op_name in self.network_operators.keys():  # pylint: disable=consider-iterating-dictionary
            if op_name not in self.operator_whitelist:
                self.operator_whitelist.append(op_name)

        logger.info(f"注册了 {len(self.network_operators)} 个网络关系算子")

    async def mine_factors(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        returns: pd.Series,
        generations: int = 10,
        industry_map: Optional[Dict[str, str]] = None,
        volume: Optional[pd.DataFrame] = None,
    ) -> List[Individual]:
        """挖掘网络关系因子

        Args:
            data: 价格数据，列为股票代码
            returns: 收益率数据
            generations: 进化代数
            industry_map: 股票到行业的映射（可选）
            volume: 成交量数据（可选）

        Returns:
            List[Individual]: 挖掘出的因子列表
        """
        try:
            logger.info("开始挖掘网络关系因子")

            # 初始化种群
            if not self.population:
                await self.initialize_population(data.columns.tolist())

            # 存储额外数据供算子使用
            self.industry_map = industry_map  # pylint: disable=w0201
            self.volume_data = volume  # pylint: disable=w0201

            # 进化种群
            best_individual = await self.evolve(data, returns, generations)

            # 收集所有有效因子
            valid_factors = [
                ind for ind in self.population if ind.fitness > 0.1 and abs(ind.ic) > self.config.min_ic_threshold
            ]

            logger.info(
                f"网络关系因子挖掘完成: " f"发现 {len(valid_factors)} 个有效因子, " f"最佳IC={best_individual.ic:.4f}"
            )

            return valid_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"网络关系因子挖掘失败: {e}")
            return []

    def calculate_network_factor(self, operator_name: str, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算单个网络关系因子

        Args:
            operator_name: 算子名称
            data: 价格数据
            **kwargs: 额外参数

        Returns:
            pd.Series: 因子值
        """
        try:
            if operator_name not in self.network_operators:
                logger.error(f"未知的网络关系算子: {operator_name}")
                return pd.Series(0.0, index=data.index)

            operator_func = self.network_operators[operator_name]

            # 准备参数
            params = {"data": data, "window": self.network_config.correlation_window}

            # 添加算子特定参数
            if operator_name == "stock_correlation_network":
                params["threshold"] = self.network_config.network_threshold

            elif operator_name == "supply_chain_network":
                params["industry_map"] = kwargs.get("industry_map", self.industry_map)

            elif operator_name == "capital_flow_network":
                params["volume"] = kwargs.get("volume", self.volume_data)

            elif operator_name == "information_propagation":
                params["max_steps"] = self.network_config.propagation_steps

            elif operator_name == "industry_ecosystem":
                params["industry_map"] = kwargs.get("industry_map", self.industry_map)

            elif operator_name == "network_centrality":
                params["method"] = self.network_config.centrality_method
                params["threshold"] = self.network_config.network_threshold

            # 计算因子
            factor_values = operator_func(**params)

            return factor_values

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"计算网络关系因子失败 ({operator_name}): {e}")
            return pd.Series(0.0, index=data.index)

    def analyze_network_structure(self, data: pd.DataFrame, threshold: float = 0.5) -> Dict[str, Any]:
        """分析网络结构

        Args:
            data: 价格数据
            threshold: 相关性阈值

        Returns:
            Dict: 网络结构分析结果
        """
        try:
            # 计算收益率
            returns = data.pct_change().dropna()

            # 计算相关性矩阵
            corr_matrix = returns.corr()

            # 构建邻接矩阵
            adjacency = (corr_matrix.abs() > threshold).astype(int)
            import numpy as np  # pylint: disable=import-outside-toplevel

            np.fill_diagonal(adjacency.values, 0)

            # 计算网络统计量
            num_nodes = len(data.columns)
            num_edges = adjacency.sum().sum() // 2  # 无向图
            density = num_edges / (num_nodes * (num_nodes - 1) / 2) if num_nodes > 1 else 0

            # 计算度分布
            degree = adjacency.sum(axis=1)
            avg_degree = degree.mean()
            max_degree = degree.max()

            # 识别核心节点（度最高的节点）
            hub_nodes = degree.nlargest(5).index.tolist()

            # 识别孤立节点（度为0的节点）
            isolated_nodes = degree[degree == 0].index.tolist()

            analysis = {
                "num_nodes": num_nodes,
                "num_edges": num_edges,
                "density": density,
                "avg_degree": avg_degree,
                "max_degree": max_degree,
                "hub_nodes": hub_nodes,
                "isolated_nodes": isolated_nodes,
                "degree_distribution": degree.to_dict(),
            }

            logger.info(
                f"网络结构分析完成: "
                f"节点数={num_nodes}, "
                f"边数={num_edges}, "
                f"密度={density:.3f}, "
                f"平均度={avg_degree:.2f}"
            )

            return analysis

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"网络结构分析失败: {e}")
            return {}

    def identify_communities(
        self, data: pd.DataFrame, threshold: float = 0.5, min_community_size: int = 3
    ) -> Dict[int, List[str]]:
        """识别网络社区

        使用简化的社区检测算法识别股票群组。

        Args:
            data: 价格数据
            threshold: 相关性阈值
            min_community_size: 最小社区大小

        Returns:
            Dict[int, List[str]]: 社区ID到股票列表的映射
        """
        try:
            # 计算收益率
            returns = data.pct_change().dropna()

            # 计算相关性矩阵
            corr_matrix = returns.corr()

            # 简化的社区检测：使用层次聚类
            from scipy.cluster.hierarchy import fcluster, linkage  # pylint: disable=import-outside-toplevel
            from scipy.spatial.distance import squareform  # pylint: disable=import-outside-toplevel

            # 将相关性转换为距离
            distance_matrix = 1 - corr_matrix.abs()

            # 层次聚类
            linkage_matrix = linkage(squareform(distance_matrix), method="average")

            # 切割树形图得到社区
            # 使用距离阈值
            distance_threshold = 1 - threshold
            labels = fcluster(linkage_matrix, distance_threshold, criterion="distance")

            # 组织社区
            communities = {}
            for stock, label in zip(data.columns, labels):
                if label not in communities:
                    communities[label] = []
                communities[label].append(stock)

            # 过滤小社区
            communities = {cid: stocks for cid, stocks in communities.items() if len(stocks) >= min_community_size}

            logger.info(
                f"识别到 {len(communities)} 个社区, "
                f"平均社区大小: {sum(len(s) for s in communities.values()) / len(communities):.1f}"
            )

            return communities

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"社区识别失败: {e}")
            return {}

    def calculate_network_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有网络指标

        Args:
            data: 价格数据

        Returns:
            pd.DataFrame: 网络指标矩阵
        """
        try:
            metrics = pd.DataFrame(index=data.index)

            # 计算各个网络因子
            logger.info("计算股票相关性网络...")
            metrics["correlation_network"] = self.calculate_network_factor("stock_correlation_network", data)

            logger.info("计算供应链网络...")
            metrics["supply_chain"] = self.calculate_network_factor("supply_chain_network", data)

            logger.info("计算资金流网络...")
            metrics["capital_flow"] = self.calculate_network_factor("capital_flow_network", data)

            logger.info("计算信息传播网络...")
            metrics["information_propagation"] = self.calculate_network_factor("information_propagation", data)

            logger.info("计算行业生态网络...")
            metrics["industry_ecosystem"] = self.calculate_network_factor("industry_ecosystem", data)

            logger.info("计算网络中心性...")
            for method in ["degree", "eigenvector", "closeness"]:
                metrics[f"centrality_{method}"] = self.calculate_network_factor(
                    "network_centrality", data, method=method
                )

            logger.info(f"网络指标计算完成，共 {len(metrics.columns)} 个指标")

            return metrics

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"网络指标计算失败: {e}")
            return pd.DataFrame()
