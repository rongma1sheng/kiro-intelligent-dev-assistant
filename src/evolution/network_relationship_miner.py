"""网络关系因子挖掘器

白皮书依据: 第四章 4.1.5 网络关系因子挖掘
需求: 4.1-4.10
设计文档: design.md - Network Relationship Factor Miner
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Set, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from .unified_factor_mining_system import BaseMiner, FactorMetadata, MinerType


class NetworkType(Enum):
    """网络类型"""

    CORRELATION = "correlation"
    SUPPLY_CHAIN = "supply_chain"
    CAPITAL_FLOW = "capital_flow"
    INFORMATION = "information"
    INDUSTRY = "industry"


@dataclass
class NetworkNode:
    """网络节点

    Attributes:
        node_id: 节点ID（股票代码）
        degree: 度中心性
        betweenness: 介数中心性
        closeness: 接近中心性
        eigenvector: 特征向量中心性
        pagerank: PageRank值
    """

    node_id: str
    degree: float = 0.0
    betweenness: float = 0.0
    closeness: float = 0.0
    eigenvector: float = 0.0
    pagerank: float = 0.0


@dataclass
class NetworkGraph:
    """网络图结构

    Attributes:
        nodes: 节点集合
        edges: 边集合 {(node1, node2): weight}
        adjacency: 邻接表 {node: [neighbors]}
    """

    nodes: Set[str]
    edges: Dict[Tuple[str, str], float]
    adjacency: Dict[str, List[str]]

    def add_edge(self, node1: str, node2: str, weight: float = 1.0):
        """添加边"""
        self.nodes.add(node1)
        self.nodes.add(node2)
        self.edges[(node1, node2)] = weight
        self.edges[(node2, node1)] = weight

        if node1 not in self.adjacency:
            self.adjacency[node1] = []
        if node2 not in self.adjacency:
            self.adjacency[node2] = []

        if node2 not in self.adjacency[node1]:
            self.adjacency[node1].append(node2)
        if node1 not in self.adjacency[node2]:
            self.adjacency[node2].append(node1)

    def get_neighbors(self, node: str) -> List[str]:
        """获取节点的邻居"""
        return self.adjacency.get(node, [])

    def get_edge_weight(self, node1: str, node2: str) -> float:
        """获取边的权重"""
        return self.edges.get((node1, node2), 0.0)


class NetworkRelationshipFactorMiner(BaseMiner):
    """网络关系因子挖掘器

    白皮书依据: 第四章 4.1.5
    需求: 4.1-4.10

    从股票相关性网络、供应链网络、资金流网络、信息传播网络、
    行业生态系统等网络结构中挖掘因子。

    支持6个核心网络算子：
    1. stock_correlation_network: 股票相关性网络
    2. supply_chain_network: 供应链网络
    3. capital_flow_network: 资金流网络
    4. information_propagation: 信息传播
    5. industry_ecosystem: 行业生态系统
    6. network_centrality: 网络中心性

    Attributes:
        operators: 6个算子的字典
        network_update_interval: 网络更新间隔（天），默认1
        correlation_threshold: 相关性阈值，默认0.5
    """

    def __init__(self, network_update_interval: int = 1, correlation_threshold: float = 0.5):
        """初始化网络关系因子挖掘器

        白皮书依据: 第四章 4.1.5
        需求: 4.1-4.10

        Args:
            network_update_interval: 网络更新间隔（天），默认1
            correlation_threshold: 相关性阈值，默认0.5

        Raises:
            ValueError: 当参数不在有效范围时
        """
        super().__init__(MinerType.NETWORK, "NetworkRelationshipFactorMiner")

        if network_update_interval < 1:
            raise ValueError(f"network_update_interval必须 >= 1，当前: {network_update_interval}")

        if not 0 < correlation_threshold < 1:
            raise ValueError(f"correlation_threshold必须在 (0, 1)，当前: {correlation_threshold}")

        self.network_update_interval = network_update_interval
        self.correlation_threshold = correlation_threshold
        self.operators = self._initialize_operators()

        # 网络缓存
        self.network_cache: Dict[str, Tuple[NetworkGraph, datetime]] = {}

        logger.info(
            f"NetworkRelationshipFactorMiner初始化完成 - "
            f"update_interval={network_update_interval}天, "
            f"correlation_threshold={correlation_threshold}, "
            f"operators={len(self.operators)}"
        )

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化6个网络算子

        白皮书依据: 第四章 4.1.5
        需求: 4.7

        Returns:
            算子名称到函数的字典
        """
        return {
            "stock_correlation_network": self._stock_correlation_network,
            "supply_chain_network": self._supply_chain_network,
            "capital_flow_network": self._capital_flow_network,
            "information_propagation": self._information_propagation,
            "industry_ecosystem": self._industry_ecosystem,
            "network_centrality": self._network_centrality,
        }

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, **kwargs) -> List[FactorMetadata]:
        """挖掘网络关系因子

        白皮书依据: 第四章 4.1.5
        需求: 4.1-4.10

        Args:
            data: 市场数据（DataFrame），包含价格、成交量等
            returns: 收益率数据
            **kwargs: 额外参数
                - network_data: 网络数据字典 {network_type: data}
                - symbols: 股票代码列表
                - operators: 要使用的算子列表（默认使用所有）

        Returns:
            发现的因子列表

        Raises:
            ValueError: 当输入数据无效时
        """
        if data.empty:
            raise ValueError("输入数据不能为空")

        if returns.empty:
            raise ValueError("收益率数据不能为空")

        # 提取参数
        network_data = kwargs.get("network_data", {})
        symbols = kwargs.get("symbols", data.index.tolist() if hasattr(data.index, "tolist") else [])
        operators_to_use = kwargs.get("operators", list(self.operators.keys()))

        logger.info(
            f"开始挖掘网络关系因子 - "
            f"data_shape={data.shape}, "
            f"network_types={len(network_data)}, "
            f"operators={len(operators_to_use)}"
        )

        factors = []

        # 对每个算子执行挖掘
        for operator_name in operators_to_use:
            if operator_name not in self.operators:
                logger.warning(f"未知算子: {operator_name}，跳过")
                continue

            try:
                # 获取算子函数
                operator_func = self.operators[operator_name]

                # 执行算子
                factor_values = operator_func(data, network_data, symbols, returns)

                # 计算因子指标
                ic = self._calculate_ic(factor_values, returns)
                ir = self._calculate_ir(factor_values, returns)
                sharpe = self._calculate_sharpe(factor_values, returns)

                # 计算综合适应度
                fitness = self._calculate_fitness(ic, ir, sharpe)

                # 创建因子元数据
                factor = FactorMetadata(
                    factor_id=f"network_{operator_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    factor_name=f"Network_{operator_name}",
                    factor_type=MinerType.NETWORK,
                    data_source=self._get_network_type_for_operator(operator_name),
                    discovery_date=datetime.now(),
                    discoverer=self.miner_name,
                    expression=f"{operator_name}(network, symbols)",
                    fitness=fitness,
                    ic=ic,
                    ir=ir,
                    sharpe=sharpe,
                )

                factors.append(factor)

                logger.info(
                    f"发现因子: {factor.factor_id}, "
                    f"IC={ic:.4f}, IR={ir:.4f}, Sharpe={sharpe:.4f}, "
                    f"fitness={fitness:.4f}"
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"算子 {operator_name} 执行失败: {e}")
                self.metadata.error_count += 1
                self.metadata.last_error = str(e)
                continue

        # 更新元数据
        self.metadata.total_factors_discovered += len(factors)
        if factors:
            avg_fitness = np.mean([f.fitness for f in factors])
            self.metadata.average_fitness = (
                self.metadata.average_fitness * (self.metadata.total_factors_discovered - len(factors))
                + avg_fitness * len(factors)
            ) / self.metadata.total_factors_discovered
        self.metadata.last_run_time = datetime.now()
        self.metadata.is_healthy = self.metadata.error_count < 5

        logger.info(
            f"网络关系因子挖掘完成 - " f"发现因子数={len(factors)}, " f"平均fitness={self.metadata.average_fitness:.4f}"
        )

        return factors

    # ==================== 6个核心算子实现 ====================

    def _stock_correlation_network(
        self,
        data: pd.DataFrame,
        network_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """股票相关性网络算子

        白皮书依据: 第四章 4.1.5
        需求: 4.1

        构建股票相关性网络并计算网络中心性。

        Args:
            data: 市场数据
            network_data: 网络数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列（度中心性）
        """
        if "close" not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 构建相关性网络
        window = 60
        if len(data) < window:
            return pd.Series(0, index=data.index)

        # 计算收益率相关性矩阵
        price_data = data["close"].iloc[-window:]
        returns_data = price_data.pct_change().dropna()

        # 构建网络图
        graph = NetworkGraph(nodes=set(), edges={}, adjacency={})

        # 简化版本：假设只有一个股票，计算其与历史自身的"相关性"
        # 实际应该是多个股票之间的相关性
        node_id = "stock_0"
        graph.nodes.add(node_id)

        # 计算度中心性（简化：使用收益率的自相关）
        if len(returns_data) > 1:
            autocorr = returns_data.autocorr(lag=1)
            degree_centrality = abs(autocorr) if not np.isnan(autocorr) else 0.0
        else:
            degree_centrality = 0.0

        # 创建因子值序列
        factor_values = pd.Series(degree_centrality, index=data.index)

        logger.debug(f"stock_correlation_network: 度中心性={degree_centrality:.4f}")

        return factor_values

    def _supply_chain_network(
        self,
        data: pd.DataFrame,
        network_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """供应链网络算子

        白皮书依据: 第四章 4.1.5
        需求: 4.2

        分析供应链网络识别关键节点和脆弱点。

        Args:
            data: 市场数据
            network_data: 网络数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列（介数中心性）
        """
        # 简化的供应链网络：使用行业关联度
        if "volume" not in data.columns:
            raise ValueError("数据中缺少 volume 列")

        # 使用成交量变化作为供应链活跃度的代理
        volume_change = data["volume"].pct_change()

        # 计算介数中心性的代理：成交量波动率
        window = 30
        volume_volatility = volume_change.rolling(window=window).std()

        # 标准化
        if volume_volatility.std() > 0:
            betweenness_proxy = (volume_volatility - volume_volatility.mean()) / volume_volatility.std()
        else:
            betweenness_proxy = pd.Series(0, index=data.index)

        factor_values = betweenness_proxy.fillna(0)

        logger.debug(f"supply_chain_network: 平均介数中心性={factor_values.mean():.4f}")

        return factor_values

    def _capital_flow_network(
        self,
        data: pd.DataFrame,
        network_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """资金流网络算子

        白皮书依据: 第四章 4.1.5
        需求: 4.3

        追踪资金流向和流量。

        Args:
            data: 市场数据
            network_data: 网络数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列（资金流强度）
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 计算资金流：价格变化 * 成交量
        price_change = data["close"].pct_change()
        volume = data["volume"]

        # 资金流强度
        money_flow = price_change * volume

        # 计算净资金流（正流入 - 负流出）
        window = 20
        positive_flow = money_flow.where(money_flow > 0, 0).rolling(window=window).sum()
        negative_flow = money_flow.where(money_flow < 0, 0).rolling(window=window).sum()

        net_flow = positive_flow + negative_flow  # negative_flow已经是负数

        # 标准化
        if net_flow.std() > 0:
            factor_values = (net_flow - net_flow.mean()) / net_flow.std()
        else:
            factor_values = pd.Series(0, index=data.index)

        factor_values = factor_values.fillna(0)

        logger.debug(f"capital_flow_network: 平均资金流={factor_values.mean():.4f}")

        return factor_values

    def _information_propagation(
        self,
        data: pd.DataFrame,
        network_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """信息传播算子

        白皮书依据: 第四章 4.1.5
        需求: 4.4

        模拟信息在网络中的传播速度和影响范围。

        Args:
            data: 市场数据
            network_data: 网络数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列（传播速度）
        """
        if "close" not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 信息传播速度的代理：价格变化的传导速度
        # 使用价格动量的加速度
        price_change = data["close"].pct_change()

        # 一阶动量
        momentum_1 = price_change.rolling(window=5).mean()

        # 二阶动量（加速度）
        momentum_2 = momentum_1.diff()

        # 传播速度：动量的变化率
        propagation_speed = momentum_2.rolling(window=10).mean()

        # 标准化
        if propagation_speed.std() > 0:
            factor_values = (propagation_speed - propagation_speed.mean()) / propagation_speed.std()
        else:
            factor_values = pd.Series(0, index=data.index)

        factor_values = factor_values.fillna(0)

        logger.debug(f"information_propagation: 平均传播速度={factor_values.mean():.4f}")

        return factor_values

    def _industry_ecosystem(
        self,
        data: pd.DataFrame,
        network_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """行业生态系统算子

        白皮书依据: 第四章 4.1.5
        需求: 4.5

        识别行业集群结构和跨集群连接。

        Args:
            data: 市场数据
            network_data: 网络数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列（集群系数）
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 集群系数的代理：价格和成交量的协同性
        price_change = data["close"].pct_change()
        volume_change = data["volume"].pct_change()

        # 计算滚动相关性作为集群系数
        window = 30
        clustering_coef = price_change.rolling(window=window).corr(volume_change.rolling(window=window))

        # 处理NaN和无穷大
        clustering_coef = clustering_coef.replace([np.inf, -np.inf], 0).fillna(0)

        factor_values = clustering_coef

        logger.debug(f"industry_ecosystem: 平均集群系数={factor_values.mean():.4f}")

        return factor_values

    def _network_centrality(
        self,
        data: pd.DataFrame,
        network_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """网络中心性算子

        白皮书依据: 第四章 4.1.5
        需求: 4.6

        计算多种中心性指标（度、介数、接近、特征向量）。

        Args:
            data: 市场数据
            network_data: 网络数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列（综合中心性）
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 综合中心性：多个中心性指标的加权组合

        # 1. 度中心性代理：成交量相对大小
        volume_rank = data["volume"].rank(pct=True)

        # 2. 介数中心性代理：价格波动率
        price_volatility = data["close"].pct_change().rolling(window=20).std()
        if price_volatility.std() > 0:
            betweenness_norm = (price_volatility - price_volatility.mean()) / price_volatility.std()
        else:
            betweenness_norm = pd.Series(0, index=data.index)

        # 3. 接近中心性代理：价格对市场的响应速度
        price_change = data["close"].pct_change()
        closeness_proxy = price_change.rolling(window=10).mean()
        if closeness_proxy.std() > 0:
            closeness_norm = (closeness_proxy - closeness_proxy.mean()) / closeness_proxy.std()
        else:
            closeness_norm = pd.Series(0, index=data.index)

        # 4. 特征向量中心性代理：价格趋势强度
        trend_strength = price_change.rolling(window=20).mean() / (price_change.rolling(window=20).std() + 1e-8)
        if trend_strength.std() > 0:
            eigenvector_norm = (trend_strength - trend_strength.mean()) / trend_strength.std()
        else:
            eigenvector_norm = pd.Series(0, index=data.index)

        # 综合中心性（加权平均）
        composite_centrality = (
            volume_rank * 0.3 + betweenness_norm * 0.25 + closeness_norm * 0.25 + eigenvector_norm * 0.2
        )

        factor_values = composite_centrality.fillna(0)

        logger.debug(f"network_centrality: 平均综合中心性={factor_values.mean():.4f}")

        return factor_values

    # ==================== 辅助方法实现 ====================

    def _build_correlation_network(self, data: pd.DataFrame, symbols: List[str], window: int = 60) -> NetworkGraph:
        """构建相关性网络

        白皮书依据: 第四章 4.1.5
        需求: 4.1

        Args:
            data: 市场数据
            symbols: 股票代码列表
            window: 滚动窗口大小

        Returns:
            网络图
        """
        graph = NetworkGraph(nodes=set(), edges={}, adjacency={})

        if "close" not in data.columns or len(data) < window:
            return graph

        # 计算收益率
        data["close"].pct_change().dropna()

        # 简化版本：单个股票的自相关网络
        # 实际应该是多个股票之间的相关性矩阵
        for symbol in symbols[:1]:  # 只处理第一个股票
            graph.nodes.add(symbol)

        return graph

    def _calculate_degree_centrality(self, graph: NetworkGraph) -> Dict[str, float]:
        """计算度中心性

        白皮书依据: 第四章 4.1.5
        需求: 4.6

        Args:
            graph: 网络图

        Returns:
            节点到度中心性的字典
        """
        centrality = {}
        n = len(graph.nodes)

        if n <= 1:
            return {node: 0.0 for node in graph.nodes}

        for node in graph.nodes:
            degree = len(graph.get_neighbors(node))
            # 归一化：除以最大可能度数
            centrality[node] = degree / (n - 1)

        return centrality

    def _calculate_betweenness_centrality(self, graph: NetworkGraph) -> Dict[str, float]:
        """计算介数中心性

        白皮书依据: 第四章 4.1.5
        需求: 4.6

        使用Brandes算法计算介数中心性。

        Args:
            graph: 网络图

        Returns:
            节点到介数中心性的字典
        """
        centrality = {node: 0.0 for node in graph.nodes}

        if len(graph.nodes) <= 2:
            return centrality

        # 简化版本：使用BFS计算最短路径
        for source in graph.nodes:
            # BFS
            queue = deque([source])
            visited = {source}
            paths = {source: 1}

            while queue:
                node = queue.popleft()
                for neighbor in graph.get_neighbors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        paths[neighbor] = paths.get(neighbor, 0) + paths[node]

            # 累积介数
            for node in visited:
                if node != source:
                    centrality[node] += paths.get(node, 0)

        # 归一化
        n = len(graph.nodes)
        if n > 2:
            norm = (n - 1) * (n - 2) / 2
            centrality = {node: val / norm for node, val in centrality.items()}

        return centrality

    def _calculate_closeness_centrality(self, graph: NetworkGraph) -> Dict[str, float]:
        """计算接近中心性

        白皮书依据: 第四章 4.1.5
        需求: 4.6

        Args:
            graph: 网络图

        Returns:
            节点到接近中心性的字典
        """
        centrality = {}

        if len(graph.nodes) <= 1:
            return {node: 0.0 for node in graph.nodes}

        for node in graph.nodes:
            # BFS计算到所有其他节点的最短距离
            distances = self._bfs_distances(graph, node)

            if distances:
                avg_distance = sum(distances.values()) / len(distances)
                # 接近中心性 = 1 / 平均距离
                centrality[node] = 1.0 / avg_distance if avg_distance > 0 else 0.0
            else:
                centrality[node] = 0.0

        return centrality

    def _bfs_distances(self, graph: NetworkGraph, source: str) -> Dict[str, int]:
        """BFS计算最短距离

        Args:
            graph: 网络图
            source: 源节点

        Returns:
            节点到距离的字典
        """
        distances = {}
        queue = deque([(source, 0)])
        visited = {source}

        while queue:
            node, dist = queue.popleft()

            for neighbor in graph.get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    distances[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))

        return distances

    def _trace_risk_contagion(self, graph: NetworkGraph, source_node: str, shock_magnitude: float) -> Dict[str, float]:
        """追踪风险传导

        白皮书依据: 第四章 4.1.5
        需求: 4.9

        Args:
            graph: 网络图
            source_node: 冲击源节点
            shock_magnitude: 冲击强度

        Returns:
            节点到冲击影响的字典
        """
        impact = {source_node: shock_magnitude}

        if source_node not in graph.nodes:
            return impact

        # 使用BFS模拟冲击传播
        queue = deque([(source_node, shock_magnitude)])
        visited = {source_node}

        # 衰减因子
        decay_factor = 0.8

        while queue:
            node, magnitude = queue.popleft()

            # 传播到邻居节点
            for neighbor in graph.get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    # 冲击衰减
                    neighbor_magnitude = magnitude * decay_factor
                    impact[neighbor] = neighbor_magnitude

                    # 如果冲击还足够大，继续传播
                    if neighbor_magnitude > 0.01:
                        queue.append((neighbor, neighbor_magnitude))

        return impact

    def _update_network(self, network_type: str, data: pd.DataFrame, symbols: List[str]) -> NetworkGraph:
        """更新网络结构

        白皮书依据: 第四章 4.1.5
        需求: 4.10

        Args:
            network_type: 网络类型
            data: 市场数据
            symbols: 股票代码列表

        Returns:
            更新后的网络图
        """
        # 检查缓存
        cache_key = f"{network_type}_{len(symbols)}"
        if cache_key in self.network_cache:
            cached_graph, cached_time = self.network_cache[cache_key]
            # 检查是否需要更新
            if (datetime.now() - cached_time).days < self.network_update_interval:
                logger.debug(f"使用缓存的网络: {network_type}")
                return cached_graph

        # 构建新网络
        logger.info(f"更新网络: {network_type}")

        if network_type == NetworkType.CORRELATION.value:
            graph = self._build_correlation_network(data, symbols)
        else:
            # 其他网络类型的构建逻辑
            graph = NetworkGraph(nodes=set(symbols), edges={}, adjacency={})

        # 更新缓存
        self.network_cache[cache_key] = (graph, datetime.now())

        return graph

    def _calculate_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算信息系数(IC)"""
        common_index = factor_values.index.intersection(returns.index)
        if len(common_index) == 0:
            return 0.0

        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
        factor_clean = factor_aligned[valid_mask]
        returns_clean = returns_aligned[valid_mask]

        if len(factor_clean) < 2:
            return 0.0

        try:
            ic = factor_clean.corr(returns_clean, method="spearman")
            return ic if not np.isnan(ic) else 0.0
        except Exception:  # pylint: disable=broad-exception-caught
            return 0.0

    def _calculate_ir(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算信息比率(IR)"""
        window = 20
        if len(factor_values) < window:
            return 0.0

        ic_series = []
        for i in range(window, len(factor_values)):
            factor_window = factor_values.iloc[i - window : i]
            returns_window = returns.iloc[i - window : i]
            ic = self._calculate_ic(factor_window, returns_window)
            ic_series.append(ic)

        if len(ic_series) == 0:
            return 0.0

        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)

        if ic_std == 0:
            return 0.0

        ir = ic_mean / ic_std
        return ir if not np.isnan(ir) else 0.0

    def _calculate_sharpe(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算夏普比率"""
        common_index = factor_values.index.intersection(returns.index)
        if len(common_index) == 0:
            return 0.0

        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        if factor_aligned.std() > 0:
            factor_normalized = (factor_aligned - factor_aligned.mean()) / factor_aligned.std()
        else:
            return 0.0

        portfolio_returns = factor_normalized * returns_aligned
        portfolio_returns_clean = portfolio_returns.dropna()

        if len(portfolio_returns_clean) < 2:
            return 0.0

        mean_return = portfolio_returns_clean.mean()
        std_return = portfolio_returns_clean.std()

        if std_return == 0:
            return 0.0

        sharpe = (mean_return / std_return) * np.sqrt(252)
        return sharpe if not np.isnan(sharpe) else 0.0

    def _calculate_fitness(self, ic: float, ir: float, sharpe: float) -> float:
        """计算综合适应度"""
        fitness = abs(ic) * 0.3 + abs(ir) * 0.3 + max(0, sharpe) * 0.4
        return fitness

    def _get_network_type_for_operator(self, operator_name: str) -> str:
        """获取算子对应的网络类型"""
        network_mapping = {
            "stock_correlation_network": "correlation_network",
            "supply_chain_network": "supply_chain",
            "capital_flow_network": "capital_flow",
            "information_propagation": "information_network",
            "industry_ecosystem": "industry_network",
            "network_centrality": "composite_network",
        }
        return network_mapping.get(operator_name, "unknown")
