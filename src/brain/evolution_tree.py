"""演化树

白皮书依据: 第五章 5.3.3 演化树

本模块实现了演化树，负责：
- 策略家族谱系管理
- 全链溯源：追溯策略演化历史
- 家族对比：对比同家族策略差异
- 失败学习：从失败分支学习

定义: 策略家族谱系
结构:
- 根节点: 初代策略
- 子节点: 变异后代
- 边: 变异记录、适应度变化

存储: Redis
Key: mia:knowledge:evolution_tree
TTL: 永久
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.brain.darwin_data_models import (
    EvolutionEdge,
    EvolutionNode,
    FailureLearningResult,
    FamilyComparisonResult,
    MutationType,
)
from src.brain.redis_storage import RedisStorageManager


class EvolutionTree:
    """演化树

    白皮书依据: 第五章 5.3.3 演化树

    管理策略家族谱系，支持全链溯源、家族对比和失败学习。

    Attributes:
        redis_storage: Redis存储管理器
        nodes: 节点字典 {node_id: EvolutionNode}
        edges: 边列表
        root_node_id: 根节点ID
        family_id: 家族ID
    """

    def __init__(
        self,
        redis_storage: RedisStorageManager,
        family_id: Optional[str] = None,
    ) -> None:
        """初始化演化树

        Args:
            redis_storage: Redis存储管理器实例
            family_id: 家族ID（可选，默认生成新ID）

        Raises:
            ValueError: 当redis_storage为None时
        """
        if redis_storage is None:
            raise ValueError("Redis存储管理器不能为None")

        self._redis_storage = redis_storage
        self._family_id = family_id or str(uuid.uuid4())
        self._nodes: Dict[str, EvolutionNode] = {}
        self._edges: List[EvolutionEdge] = []
        self._root_node_id: Optional[str] = None
        self._children_map: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self._parent_map: Dict[str, str] = {}  # child_id -> parent_id

        logger.info(f"EvolutionTree初始化完成: family_id={self._family_id}")

    @property
    def family_id(self) -> str:
        """获取家族ID"""
        return self._family_id

    @property
    def root_node_id(self) -> Optional[str]:
        """获取根节点ID"""
        return self._root_node_id

    @property
    def nodes(self) -> Dict[str, EvolutionNode]:
        """获取所有节点"""
        return self._nodes.copy()

    @property
    def edges(self) -> List[EvolutionEdge]:
        """获取所有边"""
        return self._edges.copy()

    async def create_root(
        self,
        capsule_id: str,
        strategy_name: str,
        fitness: float,
    ) -> EvolutionNode:
        """创建根节点（初代策略）

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.1

        Args:
            capsule_id: 关联的基因胶囊ID
            strategy_name: 策略名称
            fitness: 适应度

        Returns:
            EvolutionNode: 创建的根节点

        Raises:
            ValueError: 当参数无效或根节点已存在时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")
        if not strategy_name:
            raise ValueError("策略名称不能为空")
        if self._root_node_id is not None:
            raise ValueError("根节点已存在，不能重复创建")

        node_id = str(uuid.uuid4())
        node = EvolutionNode(
            node_id=node_id,
            capsule_id=capsule_id,
            strategy_name=strategy_name,
            fitness=fitness,
            generation=0,
            created_at=datetime.now(),
        )

        self._nodes[node_id] = node
        self._root_node_id = node_id
        self._children_map[node_id] = []

        # 保存到Redis
        await self._save_to_redis()

        logger.info(f"创建根节点: {node_id}, 策略: {strategy_name}")
        return node

    async def add_child(  # pylint: disable=too-many-positional-arguments
        self,
        parent_node_id: str,
        capsule_id: str,
        strategy_name: str,
        fitness: float,
        mutation_type: MutationType,
        mutation_description: str,
    ) -> Tuple[EvolutionNode, EvolutionEdge]:
        """添加子节点（变异后代）

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.2, 3.3

        Args:
            parent_node_id: 父节点ID
            capsule_id: 关联的基因胶囊ID
            strategy_name: 策略名称
            fitness: 适应度
            mutation_type: 变异类型
            mutation_description: 变异描述

        Returns:
            Tuple[EvolutionNode, EvolutionEdge]: 创建的子节点和边

        Raises:
            ValueError: 当参数无效或父节点不存在时
        """
        if not parent_node_id:
            raise ValueError("父节点ID不能为空")
        if parent_node_id not in self._nodes:
            raise ValueError(f"父节点不存在: {parent_node_id}")
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")
        if not strategy_name:
            raise ValueError("策略名称不能为空")

        parent_node = self._nodes[parent_node_id]

        # 创建子节点
        node_id = str(uuid.uuid4())
        node = EvolutionNode(
            node_id=node_id,
            capsule_id=capsule_id,
            strategy_name=strategy_name,
            fitness=fitness,
            generation=parent_node.generation + 1,
            created_at=datetime.now(),
        )

        # 创建边
        edge_id = str(uuid.uuid4())
        fitness_change = fitness - parent_node.fitness
        edge = EvolutionEdge(
            edge_id=edge_id,
            parent_node_id=parent_node_id,
            child_node_id=node_id,
            mutation_type=mutation_type,
            mutation_description=mutation_description,
            fitness_change=fitness_change,
            created_at=datetime.now(),
        )

        # 更新数据结构
        self._nodes[node_id] = node
        self._edges.append(edge)
        self._children_map.setdefault(parent_node_id, []).append(node_id)
        self._children_map[node_id] = []
        self._parent_map[node_id] = parent_node_id

        # 保存到Redis
        await self._save_to_redis()

        logger.info(f"添加子节点: {node_id}, 父节点: {parent_node_id}, 变异类型: {mutation_type.value}")
        return node, edge

    async def trace_lineage(self, node_id: str) -> List[EvolutionNode]:
        """全链溯源：追溯策略演化历史

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.4

        从指定节点追溯到根节点的完整路径。

        Args:
            node_id: 节点ID

        Returns:
            List[EvolutionNode]: 从根到该节点的完整路径

        Raises:
            ValueError: 当节点不存在时
        """
        if not node_id:
            raise ValueError("节点ID不能为空")
        if node_id not in self._nodes:
            raise ValueError(f"节点不存在: {node_id}")

        lineage = []
        current_id = node_id

        while current_id is not None:
            lineage.append(self._nodes[current_id])
            current_id = self._parent_map.get(current_id)

        # 反转，使根节点在前
        lineage.reverse()

        logger.debug(f"追溯谱系: {node_id} -> {len(lineage)}个节点")
        return lineage

    async def compare_family(
        self,
        node_ids: List[str],
    ) -> FamilyComparisonResult:
        """家族对比：分析同家族策略差异

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.5

        Args:
            node_ids: 要对比的节点ID列表

        Returns:
            FamilyComparisonResult: 家族对比结果

        Raises:
            ValueError: 当节点列表为空或节点不存在时
        """
        if not node_ids:
            raise ValueError("节点ID列表不能为空")

        # 验证所有节点存在
        for nid in node_ids:
            if nid not in self._nodes:
                raise ValueError(f"节点不存在: {nid}")

        nodes = [self._nodes[nid] for nid in node_ids]

        # 找出最佳和最差表现者
        best_node = max(nodes, key=lambda n: n.fitness)
        worst_node = min(nodes, key=lambda n: n.fitness)

        # 分析共同特征和差异特征
        common_traits = self._analyze_common_traits(nodes)
        divergent_traits = self._analyze_divergent_traits(nodes)

        # 构建适应度分布
        fitness_distribution = {n.node_id: n.fitness for n in nodes}

        result = FamilyComparisonResult(
            family_id=self._family_id,
            members=[n.node_id for n in nodes],
            best_performer=best_node.node_id,
            worst_performer=worst_node.node_id,
            common_traits=common_traits,
            divergent_traits=divergent_traits,
            fitness_distribution=fitness_distribution,
        )

        logger.debug(f"家族对比: {len(nodes)}个成员, 最佳: {best_node.fitness:.4f}")
        return result

    def _analyze_common_traits(self, nodes: List[EvolutionNode]) -> List[str]:
        """分析共同特征"""
        traits = []

        # 分析代数分布
        generations = [n.generation for n in nodes]
        if len(set(generations)) == 1:
            traits.append(f"同代策略（第{generations[0]}代）")

        # 分析适应度范围
        fitnesses = [n.fitness for n in nodes]
        avg_fitness = sum(fitnesses) / len(fitnesses)
        traits.append(f"平均适应度: {avg_fitness:.4f}")

        return traits

    def _analyze_divergent_traits(self, nodes: List[EvolutionNode]) -> List[str]:
        """分析差异特征"""
        traits = []

        fitnesses = [n.fitness for n in nodes]
        fitness_range = max(fitnesses) - min(fitnesses)

        if fitness_range > 0.1:
            traits.append(f"适应度差异较大: {fitness_range:.4f}")

        generations = [n.generation for n in nodes]
        if len(set(generations)) > 1:
            traits.append(f"跨代策略: 第{min(generations)}-{max(generations)}代")

        return traits

    async def learn_from_failures(
        self,
        family_id: Optional[str] = None,
    ) -> FailureLearningResult:
        """失败学习：从失败分支学习

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.6

        Args:
            family_id: 家族ID（可选，默认使用当前家族）

        Returns:
            FailureLearningResult: 失败学习结果
        """
        actual_family_id = family_id or self._family_id

        # 找出失败分支（适应度下降的边）
        failed_branches = []
        failure_patterns = []

        for edge in self._edges:
            if edge.fitness_change < 0:
                failed_branches.append(edge.child_node_id)
                failure_patterns.append(
                    f"{edge.mutation_type.value}: {edge.mutation_description} "
                    f"(适应度下降 {abs(edge.fitness_change):.4f})"
                )

        # 生成教训和建议
        lessons_learned = self._extract_lessons(failed_branches)
        avoidance_recommendations = self._generate_recommendations(failure_patterns)

        result = FailureLearningResult(
            family_id=actual_family_id,
            failed_branches=failed_branches,
            failure_patterns=failure_patterns,
            lessons_learned=lessons_learned,
            avoidance_recommendations=avoidance_recommendations,
        )

        logger.debug(f"失败学习: {len(failed_branches)}个失败分支")
        return result

    def _extract_lessons(self, failed_branches: List[str]) -> List[str]:
        """提取教训"""
        lessons = []

        if not failed_branches:
            lessons.append("暂无失败分支，继续保持当前进化方向")
        else:
            lessons.append(f"共有{len(failed_branches)}个失败分支需要避免")

            # 分析失败原因
            for branch_id in failed_branches[:3]:  # 只分析前3个
                if branch_id in self._nodes:
                    node = self._nodes[branch_id]
                    lessons.append(f"策略'{node.strategy_name}'的变异方向不佳")

        return lessons

    def _generate_recommendations(self, failure_patterns: List[str]) -> List[str]:
        """生成避免建议"""
        recommendations = []

        # 统计变异类型
        mutation_counts: Dict[str, int] = {}
        for pattern in failure_patterns:
            mutation_type = pattern.split(":")[0]
            mutation_counts[mutation_type] = mutation_counts.get(mutation_type, 0) + 1

        # 生成建议
        for mutation_type, count in mutation_counts.items():
            if count >= 2:
                recommendations.append(f"减少'{mutation_type}'类型的变异，失败率较高")

        if not recommendations:
            recommendations.append("继续探索不同的变异方向")

        return recommendations

    async def get_subtree(self, node_id: str) -> Dict[str, Any]:
        """获取子树

        Args:
            node_id: 节点ID

        Returns:
            Dict: 子树结构

        Raises:
            ValueError: 当节点不存在时
        """
        if not node_id:
            raise ValueError("节点ID不能为空")
        if node_id not in self._nodes:
            raise ValueError(f"节点不存在: {node_id}")

        def build_subtree(nid: str) -> Dict[str, Any]:
            node = self._nodes[nid]
            children = self._children_map.get(nid, [])

            return {
                "node": node.to_dict(),
                "children": [build_subtree(cid) for cid in children],
            }

        return build_subtree(node_id)

    async def get_all_leaves(self) -> List[EvolutionNode]:
        """获取所有叶子节点

        Returns:
            List[EvolutionNode]: 叶子节点列表
        """
        leaves = []

        for node_id, node in self._nodes.items():
            children = self._children_map.get(node_id, [])
            if not children:
                leaves.append(node)

        return leaves

    async def get_node(self, node_id: str) -> Optional[EvolutionNode]:
        """获取节点

        Args:
            node_id: 节点ID

        Returns:
            EvolutionNode: 节点，不存在返回None
        """
        return self._nodes.get(node_id)

    async def get_children(self, node_id: str) -> List[EvolutionNode]:
        """获取子节点

        Args:
            node_id: 节点ID

        Returns:
            List[EvolutionNode]: 子节点列表
        """
        child_ids = self._children_map.get(node_id, [])
        return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    async def get_parent(self, node_id: str) -> Optional[EvolutionNode]:
        """获取父节点

        Args:
            node_id: 节点ID

        Returns:
            EvolutionNode: 父节点，不存在返回None
        """
        parent_id = self._parent_map.get(node_id)
        if parent_id:
            return self._nodes.get(parent_id)
        return None

    def serialize(self) -> str:
        """序列化演化树为JSON

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.9

        Returns:
            str: JSON字符串
        """
        data = {
            "family_id": self._family_id,
            "root_node_id": self._root_node_id,
            "nodes": {nid: node.to_dict() for nid, node in self._nodes.items()},
            "edges": [edge.to_dict() for edge in self._edges],
            "children_map": self._children_map,
            "parent_map": self._parent_map,
        }

        return json.dumps(data, ensure_ascii=False, default=str)

    @classmethod
    def deserialize(
        cls,
        json_str: str,
        redis_storage: RedisStorageManager,
    ) -> "EvolutionTree":
        """从JSON反序列化演化树

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.9

        Args:
            json_str: JSON字符串
            redis_storage: Redis存储管理器

        Returns:
            EvolutionTree: 演化树对象

        Raises:
            ValueError: 当json_str为空或格式错误时
        """
        if not json_str:
            raise ValueError("JSON字符串不能为空")

        data = json.loads(json_str)

        tree = cls(redis_storage, family_id=data["family_id"])
        tree._root_node_id = data["root_node_id"]
        tree._nodes = {nid: EvolutionNode.from_dict(node_data) for nid, node_data in data["nodes"].items()}
        tree._edges = [EvolutionEdge.from_dict(edge_data) for edge_data in data["edges"]]
        tree._children_map = data["children_map"]
        tree._parent_map = data["parent_map"]

        return tree

    async def _save_to_redis(self) -> None:
        """保存演化树到Redis

        白皮书依据: 第五章 5.3.3 演化树 - 需求3.7, 3.8

        Key: mia:knowledge:evolution_tree
        TTL: 永久
        """
        data = {
            "family_id": self._family_id,
            "root_node_id": self._root_node_id,
            "nodes": {nid: node.to_dict() for nid, node in self._nodes.items()},
            "edges": [edge.to_dict() for edge in self._edges],
            "children_map": self._children_map,
            "parent_map": self._parent_map,
        }

        await self._redis_storage.store_evolution_tree(data)
        logger.debug(f"保存演化树到Redis: {self._family_id}")

    @classmethod
    async def load_from_redis(
        cls,
        redis_storage: RedisStorageManager,
    ) -> Optional["EvolutionTree"]:
        """从Redis加载演化树

        Args:
            redis_storage: Redis存储管理器

        Returns:
            EvolutionTree: 演化树对象，不存在返回None
        """
        data = await redis_storage.get_evolution_tree()
        if not data:
            return None

        tree = cls(redis_storage, family_id=data["family_id"])
        tree._root_node_id = data["root_node_id"]
        tree._nodes = {nid: EvolutionNode.from_dict(node_data) for nid, node_data in data["nodes"].items()}
        tree._edges = [EvolutionEdge.from_dict(edge_data) for edge_data in data["edges"]]
        tree._children_map = data["children_map"]
        tree._parent_map = data["parent_map"]

        logger.info(f"从Redis加载演化树: {tree._family_id}")
        return tree

    def node_count(self) -> int:
        """获取节点数量"""
        return len(self._nodes)

    def edge_count(self) -> int:
        """获取边数量"""
        return len(self._edges)

    def max_generation(self) -> int:
        """获取最大代数"""
        if not self._nodes:
            return -1
        return max(node.generation for node in self._nodes.values())
