# pylint: disable=too-many-lines
"""知识库系统

白皮书依据: 第五章 5.5.2 知识库存储

知识库系统负责存储和管理MIA系统的知识资产，包括：
- 基因胶囊 (Gene Capsule): 认证策略的元数据和性能指标
- 演化树 (Evolution Tree): 策略演化关系图
- 精英策略: 高性能策略集合
- 失败案例: 失败策略的经验教训
- 反向黑名单: 已知的反模式和陷阱

性能要求:
- 基因胶囊存储延迟 < 10ms
- 知识检索延迟 < 50ms
- 演化树构建延迟 < 100ms
- Redis连接池: 50个连接
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from loguru import logger
from redis.connection import ConnectionPool


@dataclass
class GeneCapsule:
    """基因胶囊数据模型

    白皮书依据: 第五章 5.5.2 基因胶囊

    Attributes:
        capsule_id: 胶囊唯一标识
        strategy_id: 策略ID
        certification_tier: 认证层级 (Bronze/Silver/Gold/Platinum)
        performance_metrics: 性能指标
        metadata: 元数据
        created_at: 创建时间
    """

    capsule_id: str
    strategy_id: str
    certification_tier: str
    performance_metrics: Dict[str, float]
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class EvolutionNode:
    """演化树节点

    Attributes:
        node_id: 节点ID
        strategy_id: 策略ID
        parent_id: 父节点ID
        children_ids: 子节点ID列表
        generation: 代数
        fitness_score: 适应度评分
    """

    node_id: str
    strategy_id: str
    parent_id: Optional[str]
    children_ids: List[str]
    generation: int
    fitness_score: float


@dataclass
class EliteStrategy:
    """精英策略数据模型

    Attributes:
        strategy_id: 策略ID
        sharpe_ratio: 夏普比率
        annual_return: 年化收益率
        max_drawdown: 最大回撤
        win_rate: 胜率
        added_at: 添加时间
    """

    strategy_id: str
    sharpe_ratio: float
    annual_return: float
    max_drawdown: float
    win_rate: float
    added_at: str


@dataclass
class FailedStrategy:
    """失败策略数据模型

    Attributes:
        strategy_id: 策略ID
        failure_reason: 失败原因
        failure_type: 失败类型
        lessons_learned: 经验教训
        failed_at: 失败时间
    """

    strategy_id: str
    failure_reason: str
    failure_type: str
    lessons_learned: str
    failed_at: str


@dataclass
class AntiPattern:
    """反向黑名单数据模型

    Attributes:
        pattern_id: 模式ID
        pattern_name: 模式名称
        description: 描述
        detection_rules: 检测规则
        severity: 严重程度 (low/medium/high/critical)
        added_at: 添加时间
    """

    pattern_id: str
    pattern_name: str
    description: str
    detection_rules: Dict[str, Any]
    severity: str
    added_at: str


class KnowledgeBase:
    """知识库系统

    白皮书依据: 第五章 5.5.2 知识库存储

    管理MIA系统的知识资产，包括基因胶囊、演化树、精英策略、
    失败案例和反向黑名单。使用Redis作为存储后端。

    Attributes:
        redis_client: Redis客户端
        connection_pool: Redis连接池
    """

    def __init__(
        self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0, max_connections: int = 50
    ):
        """初始化知识库系统

        Args:
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            max_connections: 最大连接数
        """
        # 创建连接池
        self.connection_pool = ConnectionPool(
            host=redis_host, port=redis_port, db=redis_db, max_connections=max_connections, decode_responses=True
        )

        # 创建Redis客户端
        self.redis_client = redis.Redis(connection_pool=self.connection_pool)

        logger.info(
            f"初始化KnowledgeBase: "
            f"host={redis_host}, port={redis_port}, "
            f"db={redis_db}, max_connections={max_connections}"
        )

    # ==================== 基因胶囊管理 ====================

    def store_gene_capsule(self, capsule: GeneCapsule) -> bool:
        """存储基因胶囊

        白皮书依据: 第五章 5.5.2 基因胶囊存储

        Args:
            capsule: 基因胶囊对象

        Returns:
            是否存储成功

        Raises:
            ValueError: 当胶囊数据无效时
            redis.RedisError: 当Redis操作失败时
        """
        if not capsule.capsule_id:
            raise ValueError("胶囊ID不能为空")

        if not capsule.strategy_id:
            raise ValueError("策略ID不能为空")

        if capsule.certification_tier not in ["Bronze", "Silver", "Gold", "Platinum"]:
            raise ValueError(
                f"无效的认证层级: {capsule.certification_tier}, " f"必须是 Bronze/Silver/Gold/Platinum 之一"
            )

        try:
            # 构建Redis键
            key = f"mia:knowledge:gene_capsule:{capsule.capsule_id}"

            # 序列化为JSON
            capsule_json = json.dumps(asdict(capsule), ensure_ascii=False)

            # 存储到Redis (永久存储)
            self.redis_client.set(key, capsule_json)

            # 添加到精英策略集合
            self.redis_client.sadd("mia:knowledge:elite_strategies", capsule.strategy_id)

            logger.info(
                f"存储基因胶囊成功: capsule_id={capsule.capsule_id}, "
                f"strategy_id={capsule.strategy_id}, "
                f"tier={capsule.certification_tier}"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"存储基因胶囊失败: {e}")
            raise

    def get_gene_capsule(self, capsule_id: str) -> Optional[GeneCapsule]:
        """获取基因胶囊

        Args:
            capsule_id: 胶囊ID

        Returns:
            基因胶囊对象，如果不存在则返回None

        Raises:
            redis.RedisError: 当Redis操作失败时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        try:
            # 构建Redis键
            key = f"mia:knowledge:gene_capsule:{capsule_id}"

            # 从Redis获取
            capsule_json = self.redis_client.get(key)

            if not capsule_json:
                logger.warning(f"基因胶囊不存在: capsule_id={capsule_id}")
                return None

            # 反序列化
            capsule_dict = json.loads(capsule_json)
            capsule = GeneCapsule(**capsule_dict)

            logger.debug(f"获取基因胶囊成功: capsule_id={capsule_id}")

            return capsule

        except redis.RedisError as e:
            logger.error(f"获取基因胶囊失败: {e}")
            raise
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"解析基因胶囊数据失败: {e}")
            return None

    def get_gene_capsules_by_tier(self, tier: str) -> List[GeneCapsule]:
        """按认证层级获取基因胶囊列表

        Args:
            tier: 认证层级 (Bronze/Silver/Gold/Platinum)

        Returns:
            基因胶囊列表

        Raises:
            ValueError: 当层级无效时
        """
        if tier not in ["Bronze", "Silver", "Gold", "Platinum"]:
            raise ValueError(f"无效的认证层级: {tier}, " f"必须是 Bronze/Silver/Gold/Platinum 之一")

        try:
            # 扫描所有基因胶囊键
            pattern = "mia:knowledge:gene_capsule:*"
            capsules = []

            for key in self.redis_client.scan_iter(match=pattern):
                capsule_json = self.redis_client.get(key)
                if capsule_json:
                    capsule_dict = json.loads(capsule_json)
                    if capsule_dict.get("certification_tier") == tier:
                        capsules.append(GeneCapsule(**capsule_dict))

            logger.info(f"获取{tier}层级基因胶囊: 共{len(capsules)}个")

            return capsules

        except redis.RedisError as e:
            logger.error(f"获取基因胶囊列表失败: {e}")
            raise

    # ==================== 演化树管理 ====================

    def build_evolution_tree(self) -> Dict[str, Any]:
        """构建演化树

        白皮书依据: 第五章 5.5.2 演化树构建

        从Redis中读取所有演化节点，构建完整的演化树结构。

        Returns:
            演化树字典

        Raises:
            redis.RedisError: 当Redis操作失败时
        """
        try:
            # 从Redis获取演化树
            tree_json = self.redis_client.get("mia:knowledge:evolution_tree")

            if not tree_json:
                # 初始化空演化树
                tree = {
                    "nodes": {},
                    "root_nodes": [],
                    "max_generation": 0,
                    "total_nodes": 0,
                    "updated_at": datetime.now().isoformat(),
                }

                # 存储到Redis
                self.redis_client.set("mia:knowledge:evolution_tree", json.dumps(tree, ensure_ascii=False))

                logger.info("初始化演化树")

                return tree

            # 解析演化树
            tree = json.loads(tree_json)

            logger.debug(
                f"获取演化树: " f"节点数={tree.get('total_nodes', 0)}, " f"最大代数={tree.get('max_generation', 0)}"
            )

            return tree

        except redis.RedisError as e:
            logger.error(f"构建演化树失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"解析演化树数据失败: {e}")
            # 返回空演化树
            return {
                "nodes": {},
                "root_nodes": [],
                "max_generation": 0,
                "total_nodes": 0,
                "updated_at": datetime.now().isoformat(),
            }

    def update_evolution_tree(self, node: EvolutionNode) -> bool:
        """更新演化树

        添加新的演化节点到演化树中。

        Args:
            node: 演化节点

        Returns:
            是否更新成功

        Raises:
            ValueError: 当节点数据无效时
            redis.RedisError: 当Redis操作失败时
        """
        if not node.node_id:
            raise ValueError("节点ID不能为空")

        if not node.strategy_id:
            raise ValueError("策略ID不能为空")

        if node.generation < 0:
            raise ValueError(f"代数不能为负数: {node.generation}")

        try:
            # 获取当前演化树
            tree = self.build_evolution_tree()

            # 添加节点
            tree["nodes"][node.node_id] = asdict(node)

            # 更新根节点列表
            if node.parent_id is None:
                if node.node_id not in tree["root_nodes"]:
                    tree["root_nodes"].append(node.node_id)
            else:
                # 更新父节点的子节点列表
                if node.parent_id in tree["nodes"]:
                    parent = tree["nodes"][node.parent_id]
                    if node.node_id not in parent["children_ids"]:
                        parent["children_ids"].append(node.node_id)

            # 更新统计信息
            tree["total_nodes"] = len(tree["nodes"])
            tree["max_generation"] = max(tree["max_generation"], node.generation)
            tree["updated_at"] = datetime.now().isoformat()

            # 存储到Redis
            self.redis_client.set("mia:knowledge:evolution_tree", json.dumps(tree, ensure_ascii=False))

            logger.info(
                f"更新演化树成功: node_id={node.node_id}, "
                f"strategy_id={node.strategy_id}, "
                f"generation={node.generation}"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"更新演化树失败: {e}")
            raise

    def get_evolution_path(self, node_id: str) -> List[EvolutionNode]:
        """获取演化路径

        从指定节点回溯到根节点，返回完整的演化路径。

        Args:
            node_id: 节点ID

        Returns:
            演化路径（从根到当前节点）

        Raises:
            ValueError: 当节点不存在时
        """
        if not node_id:
            raise ValueError("节点ID不能为空")

        try:
            # 获取演化树
            tree = self.build_evolution_tree()

            if node_id not in tree["nodes"]:
                raise ValueError(f"节点不存在: {node_id}")

            # 回溯路径
            path = []
            current_id = node_id

            while current_id is not None:
                node_dict = tree["nodes"][current_id]
                node = EvolutionNode(**node_dict)
                path.insert(0, node)  # 插入到开头
                current_id = node.parent_id

            logger.debug(f"获取演化路径: node_id={node_id}, " f"路径长度={len(path)}")

            return path

        except redis.RedisError as e:
            logger.error(f"获取演化路径失败: {e}")
            raise

    # ==================== 精英策略管理 ====================

    def add_elite_strategy(self, strategy: EliteStrategy) -> bool:
        """添加精英策略

        白皮书依据: 第五章 5.5.2 精英策略存储

        Args:
            strategy: 精英策略对象

        Returns:
            是否添加成功

        Raises:
            ValueError: 当策略数据无效时
            redis.RedisError: 当Redis操作失败时
        """
        if not strategy.strategy_id:
            raise ValueError("策略ID不能为空")

        if strategy.sharpe_ratio <= 0:
            raise ValueError(f"夏普比率必须 > 0: {strategy.sharpe_ratio}")

        try:
            # 添加到精英策略集合
            self.redis_client.sadd("mia:knowledge:elite_strategies", strategy.strategy_id)

            # 存储策略详情
            key = f"mia:knowledge:elite_strategy:{strategy.strategy_id}"
            strategy_json = json.dumps(asdict(strategy), ensure_ascii=False)
            self.redis_client.set(key, strategy_json)

            logger.info(
                f"添加精英策略: strategy_id={strategy.strategy_id}, "
                f"sharpe={strategy.sharpe_ratio:.2f}, "
                f"return={strategy.annual_return:.2%}"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"添加精英策略失败: {e}")
            raise

    def get_elite_strategies(self, min_sharpe: float = 0.0, limit: int = 100) -> List[EliteStrategy]:
        """获取精英策略列表

        Args:
            min_sharpe: 最小夏普比率过滤条件
            limit: 返回数量限制

        Returns:
            精英策略列表（按夏普比率降序）

        Raises:
            redis.RedisError: 当Redis操作失败时
        """
        try:
            # 获取所有精英策略ID
            strategy_ids = self.redis_client.smembers("mia:knowledge:elite_strategies")

            # 获取策略详情
            strategies = []
            for strategy_id in strategy_ids:
                key = f"mia:knowledge:elite_strategy:{strategy_id}"
                strategy_json = self.redis_client.get(key)

                if strategy_json:
                    strategy_dict = json.loads(strategy_json)
                    strategy = EliteStrategy(**strategy_dict)

                    # 过滤
                    if strategy.sharpe_ratio >= min_sharpe:
                        strategies.append(strategy)

            # 按夏普比率降序排序
            strategies.sort(key=lambda s: s.sharpe_ratio, reverse=True)

            # 限制数量
            strategies = strategies[:limit]

            logger.info(f"获取精英策略: 共{len(strategies)}个, " f"min_sharpe={min_sharpe}")

            return strategies

        except redis.RedisError as e:
            logger.error(f"获取精英策略失败: {e}")
            raise

    def remove_elite_strategy(self, strategy_id: str) -> bool:
        """移除精英策略

        Args:
            strategy_id: 策略ID

        Returns:
            是否移除成功
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        try:
            # 从集合中移除
            removed = self.redis_client.srem("mia:knowledge:elite_strategies", strategy_id)

            # 删除详情
            key = f"mia:knowledge:elite_strategy:{strategy_id}"
            self.redis_client.delete(key)

            if removed:
                logger.info(f"移除精英策略: strategy_id={strategy_id}")
            else:
                logger.warning(f"精英策略不存在: strategy_id={strategy_id}")

            return bool(removed)

        except redis.RedisError as e:
            logger.error(f"移除精英策略失败: {e}")
            raise

    # ==================== 失败案例管理 ====================

    def add_failed_strategy(self, strategy: FailedStrategy) -> bool:
        """添加失败策略

        白皮书依据: 第五章 5.5.2 失败案例存储

        Args:
            strategy: 失败策略对象

        Returns:
            是否添加成功

        Raises:
            ValueError: 当策略数据无效时
            redis.RedisError: 当Redis操作失败时
        """
        if not strategy.strategy_id:
            raise ValueError("策略ID不能为空")

        if not strategy.failure_reason:
            raise ValueError("失败原因不能为空")

        try:
            # 添加到失败策略集合
            self.redis_client.sadd("mia:knowledge:failed_strategies", strategy.strategy_id)

            # 存储策略详情
            key = f"mia:knowledge:failed_strategy:{strategy.strategy_id}"
            strategy_json = json.dumps(asdict(strategy), ensure_ascii=False)
            self.redis_client.set(key, strategy_json)

            logger.info(
                f"添加失败策略: strategy_id={strategy.strategy_id}, "
                f"type={strategy.failure_type}, "
                f"reason={strategy.failure_reason}"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"添加失败策略失败: {e}")
            raise

    def get_failed_strategies(self, failure_type: Optional[str] = None, limit: int = 100) -> List[FailedStrategy]:
        """获取失败策略列表

        Args:
            failure_type: 失败类型过滤条件
            limit: 返回数量限制

        Returns:
            失败策略列表（按失败时间降序）

        Raises:
            redis.RedisError: 当Redis操作失败时
        """
        try:
            # 获取所有失败策略ID
            strategy_ids = self.redis_client.smembers("mia:knowledge:failed_strategies")

            # 获取策略详情
            strategies = []
            for strategy_id in strategy_ids:
                key = f"mia:knowledge:failed_strategy:{strategy_id}"
                strategy_json = self.redis_client.get(key)

                if strategy_json:
                    strategy_dict = json.loads(strategy_json)
                    strategy = FailedStrategy(**strategy_dict)

                    # 过滤
                    if failure_type is None or strategy.failure_type == failure_type:
                        strategies.append(strategy)

            # 按失败时间降序排序
            strategies.sort(key=lambda s: s.failed_at, reverse=True)

            # 限制数量
            strategies = strategies[:limit]

            logger.info(f"获取失败策略: 共{len(strategies)}个, " f"type={failure_type}")

            return strategies

        except redis.RedisError as e:
            logger.error(f"获取失败策略失败: {e}")
            raise

    def get_lessons_learned(self, failure_type: Optional[str] = None) -> List[str]:
        """获取经验教训

        从失败案例中提取经验教训。

        Args:
            failure_type: 失败类型过滤条件

        Returns:
            经验教训列表
        """
        try:
            # 获取失败策略
            failed_strategies = self.get_failed_strategies(failure_type=failure_type, limit=1000)

            # 提取经验教训
            lessons = []
            for strategy in failed_strategies:
                if strategy.lessons_learned:
                    lessons.append(strategy.lessons_learned)

            logger.info(f"获取经验教训: 共{len(lessons)}条, " f"type={failure_type}")

            return lessons

        except redis.RedisError as e:
            logger.error(f"获取经验教训失败: {e}")
            raise

    # ==================== 反向黑名单管理 ====================

    def add_anti_pattern(self, pattern: AntiPattern) -> bool:
        """添加反向黑名单

        白皮书依据: 第五章 5.5.2 反向黑名单存储

        Args:
            pattern: 反模式对象

        Returns:
            是否添加成功

        Raises:
            ValueError: 当模式数据无效时
            redis.RedisError: 当Redis操作失败时
        """
        if not pattern.pattern_id:
            raise ValueError("模式ID不能为空")

        if not pattern.pattern_name:
            raise ValueError("模式名称不能为空")

        if pattern.severity not in ["low", "medium", "high", "critical"]:
            raise ValueError(f"无效的严重程度: {pattern.severity}, " f"必须是 low/medium/high/critical 之一")

        try:
            # 存储到Redis列表
            pattern_json = json.dumps(asdict(pattern), ensure_ascii=False)
            self.redis_client.lpush("mia:knowledge:anti_patterns", pattern_json)

            logger.info(
                f"添加反向黑名单: pattern_id={pattern.pattern_id}, "
                f"name={pattern.pattern_name}, "
                f"severity={pattern.severity}"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"添加反向黑名单失败: {e}")
            raise

    def get_anti_patterns(self, severity: Optional[str] = None, limit: int = 100) -> List[AntiPattern]:
        """获取反向黑名单列表

        Args:
            severity: 严重程度过滤条件
            limit: 返回数量限制

        Returns:
            反模式列表

        Raises:
            redis.RedisError: 当Redis操作失败时
        """
        if severity and severity not in ["low", "medium", "high", "critical"]:
            raise ValueError(f"无效的严重程度: {severity}, " f"必须是 low/medium/high/critical 之一")

        try:
            # 从Redis列表获取
            pattern_jsons = self.redis_client.lrange("mia:knowledge:anti_patterns", 0, limit - 1)

            # 解析并过滤
            patterns = []
            for pattern_json in pattern_jsons:
                try:
                    pattern_dict = json.loads(pattern_json)
                    pattern = AntiPattern(**pattern_dict)

                    # 过滤
                    if severity is None or pattern.severity == severity:
                        patterns.append(pattern)

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"解析反模式数据失败: {e}")
                    continue

            logger.info(f"获取反向黑名单: 共{len(patterns)}个, " f"severity={severity}")

            return patterns

        except redis.RedisError as e:
            logger.error(f"获取反向黑名单失败: {e}")
            raise

    def check_anti_patterns(self, strategy_code: str) -> List[AntiPattern]:
        """检查策略代码是否匹配反向黑名单

        Args:
            strategy_code: 策略代码

        Returns:
            匹配的反模式列表
        """
        if not strategy_code:
            raise ValueError("策略代码不能为空")

        try:
            # 获取所有反模式
            patterns = self.get_anti_patterns(limit=1000)

            # 检查匹配
            matched_patterns = []
            for pattern in patterns:
                # 简单的关键词匹配（实际应该使用更复杂的规则引擎）
                detection_rules = pattern.detection_rules

                if "keywords" in detection_rules:
                    keywords = detection_rules["keywords"]
                    if any(keyword in strategy_code for keyword in keywords):
                        matched_patterns.append(pattern)

            if matched_patterns:
                logger.warning(f"检测到反模式: 共{len(matched_patterns)}个")
            else:
                logger.debug("未检测到反模式")

            return matched_patterns

        except redis.RedisError as e:
            logger.error(f"检查反模式失败: {e}")
            raise

    # ==================== 知识检索接口 ====================

    def search_knowledge(
        self, query: str, knowledge_types: Optional[List[str]] = None, limit: int = 10
    ) -> Dict[str, List[Any]]:
        """搜索知识库

        Args:
            query: 搜索查询
            knowledge_types: 知识类型列表 (gene_capsule/elite_strategy/failed_strategy/anti_pattern)
            limit: 每种类型的返回数量限制

        Returns:
            搜索结果字典

        Raises:
            ValueError: 当参数无效时
        """
        if not query:
            raise ValueError("搜索查询不能为空")

        # 默认搜索所有类型
        if knowledge_types is None:
            knowledge_types = ["gene_capsule", "elite_strategy", "failed_strategy", "anti_pattern"]

        # 验证知识类型
        valid_types = {"gene_capsule", "elite_strategy", "failed_strategy", "anti_pattern"}
        for kt in knowledge_types:
            if kt not in valid_types:
                raise ValueError(f"无效的知识类型: {kt}")

        results = {}

        try:
            # 搜索基因胶囊
            if "gene_capsule" in knowledge_types:
                capsules = []
                pattern = "mia:knowledge:gene_capsule:*"

                for key in self.redis_client.scan_iter(match=pattern):
                    capsule_json = self.redis_client.get(key)
                    if capsule_json and query.lower() in capsule_json.lower():
                        capsule_dict = json.loads(capsule_json)
                        capsules.append(GeneCapsule(**capsule_dict))

                        if len(capsules) >= limit:
                            break

                results["gene_capsules"] = capsules

            # 搜索精英策略
            if "elite_strategy" in knowledge_types:
                strategies = self.get_elite_strategies(limit=limit)
                # 简单的过滤（实际应该使用更复杂的搜索算法）
                filtered_strategies = [s for s in strategies if query.lower() in s.strategy_id.lower()]
                results["elite_strategies"] = filtered_strategies[:limit]

            # 搜索失败策略
            if "failed_strategy" in knowledge_types:
                strategies = self.get_failed_strategies(limit=limit)
                filtered_strategies = [
                    s
                    for s in strategies
                    if query.lower() in s.failure_reason.lower() or query.lower() in s.lessons_learned.lower()
                ]
                results["failed_strategies"] = filtered_strategies[:limit]

            # 搜索反模式
            if "anti_pattern" in knowledge_types:
                patterns = self.get_anti_patterns(limit=limit)
                filtered_patterns = [
                    p
                    for p in patterns
                    if query.lower() in p.pattern_name.lower() or query.lower() in p.description.lower()
                ]
                results["anti_patterns"] = filtered_patterns[:limit]

            logger.info(
                f"搜索知识库: query='{query}', "
                f"types={knowledge_types}, "
                f"结果数={sum(len(v) for v in results.values())}"
            )

            return results

        except redis.RedisError as e:
            logger.error(f"搜索知识库失败: {e}")
            raise

    def get_knowledge_statistics(self) -> Dict[str, int]:
        """获取知识库统计信息

        Returns:
            统计信息字典
        """
        try:
            stats = {}

            # 基因胶囊数量
            pattern = "mia:knowledge:gene_capsule:*"
            stats["gene_capsules"] = sum(1 for _ in self.redis_client.scan_iter(match=pattern))

            # 精英策略数量
            stats["elite_strategies"] = self.redis_client.scard("mia:knowledge:elite_strategies")

            # 失败策略数量
            stats["failed_strategies"] = self.redis_client.scard("mia:knowledge:failed_strategies")

            # 反模式数量
            stats["anti_patterns"] = self.redis_client.llen("mia:knowledge:anti_patterns")

            # 演化树节点数量
            tree = self.build_evolution_tree()
            stats["evolution_nodes"] = tree.get("total_nodes", 0)
            stats["max_generation"] = tree.get("max_generation", 0)

            logger.info(f"知识库统计: {stats}")

            return stats

        except redis.RedisError as e:
            logger.error(f"获取知识库统计失败: {e}")
            raise

    def clear_knowledge(self, knowledge_type: str) -> bool:
        """清空指定类型的知识

        Args:
            knowledge_type: 知识类型

        Returns:
            是否清空成功

        Raises:
            ValueError: 当知识类型无效时
        """
        valid_types = {"gene_capsule", "elite_strategy", "failed_strategy", "anti_pattern", "evolution_tree"}

        if knowledge_type not in valid_types:
            raise ValueError(f"无效的知识类型: {knowledge_type}")

        try:
            if knowledge_type == "gene_capsule":
                # 删除所有基因胶囊
                pattern = "mia:knowledge:gene_capsule:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    self.redis_client.delete(key)

            elif knowledge_type == "elite_strategy":
                # 清空精英策略集合
                self.redis_client.delete("mia:knowledge:elite_strategies")
                # 删除所有精英策略详情
                pattern = "mia:knowledge:elite_strategy:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    self.redis_client.delete(key)

            elif knowledge_type == "failed_strategy":
                # 清空失败策略集合
                self.redis_client.delete("mia:knowledge:failed_strategies")
                # 删除所有失败策略详情
                pattern = "mia:knowledge:failed_strategy:*"
                for key in self.redis_client.scan_iter(match=pattern):
                    self.redis_client.delete(key)

            elif knowledge_type == "anti_pattern":
                # 清空反模式列表
                self.redis_client.delete("mia:knowledge:anti_patterns")

            elif knowledge_type == "evolution_tree":
                # 清空演化树
                self.redis_client.delete("mia:knowledge:evolution_tree")

            logger.warning(f"清空知识库: type={knowledge_type}")

            return True

        except redis.RedisError as e:
            logger.error(f"清空知识库失败: {e}")
            raise

    def close(self):
        """关闭Redis连接"""
        try:
            self.redis_client.close()
            self.connection_pool.disconnect()
            logger.info("关闭KnowledgeBase连接")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"关闭连接失败: {e}")
