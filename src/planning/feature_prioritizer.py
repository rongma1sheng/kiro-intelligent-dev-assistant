"""Feature Prioritizer - Business Value Based Feature Prioritization

白皮书依据: 第十五章 15.0 功能完善路线图

核心功能:
- 按业务价值对功能进行优先级排序
- 计算功能的业务价值评分
- 支持多维度评估（影响力、紧急度、成本、风险）
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from loguru import logger


class PriorityLevel(Enum):
    """优先级级别

    白皮书依据: 第十五章 15.0 功能完善路线图
    """

    P0 = 0  # Critical - 系统无法运行
    P1 = 1  # High - 重大业务价值
    P2 = 2  # Medium - 锦上添花
    P3 = 3  # Low - 未来增强


@dataclass
class Feature:
    """功能特性

    白皮书依据: 第十五章 15.0 功能完善路线图

    Attributes:
        name: 功能名称
        description: 功能描述
        impact: 影响力评分 (1-10)
        urgency: 紧急度评分 (1-10)
        cost: 成本评分 (1-10, 越高越贵)
        risk: 风险评分 (1-10, 越高风险越大)
        priority: 优先级级别
        business_value: 业务价值评分
    """

    name: str
    description: str
    impact: float = 5.0
    urgency: float = 5.0
    cost: float = 5.0
    risk: float = 5.0
    priority: PriorityLevel = PriorityLevel.P2
    business_value: float = 0.0


class FeaturePrioritizer:
    """功能优先级排序器 - 基于业务价值

    白皮书依据: 第十五章 15.0 功能完善路线图

    优先级定义:
    - P0 (Critical): 系统无法运行，必须立即实现
    - P1 (High): 重大业务价值，高优先级
    - P2 (Medium): 锦上添花，中等优先级
    - P3 (Low): 未来增强，低优先级

    业务价值计算:
    - 影响力权重: 40%
    - 紧急度权重: 30%
    - 成本权重: 20% (负向)
    - 风险权重: 10% (负向)

    Attributes:
        impact_weight: 影响力权重
        urgency_weight: 紧急度权重
        cost_weight: 成本权重
        risk_weight: 风险权重
    """

    def __init__(
        self,
        impact_weight: float = 0.4,
        urgency_weight: float = 0.3,
        cost_weight: float = 0.2,
        risk_weight: float = 0.1,
    ):
        """初始化功能优先级排序器

        Args:
            impact_weight: 影响力权重
            urgency_weight: 紧急度权重
            cost_weight: 成本权重（负向）
            risk_weight: 风险权重（负向）

        Raises:
            ValueError: 当权重之和不等于1.0时
        """
        total_weight = impact_weight + urgency_weight + cost_weight + risk_weight
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"权重之和必须等于1.0，当前: {total_weight}")

        self.impact_weight = impact_weight
        self.urgency_weight = urgency_weight
        self.cost_weight = cost_weight
        self.risk_weight = risk_weight

        logger.info(
            f"[FeaturePrioritizer] 初始化完成 - "
            f"影响力: {impact_weight:.1%}, "
            f"紧急度: {urgency_weight:.1%}, "
            f"成本: {cost_weight:.1%}, "
            f"风险: {risk_weight:.1%}"
        )

    def prioritize_features(self, features: List[Feature]) -> List[Feature]:
        """按业务价值对功能进行优先级排序

        白皮书依据: 第十五章 15.0 功能完善路线图

        排序流程:
        1. 计算每个功能的业务价值评分
        2. 按优先级级别分组
        3. 在同一优先级内按业务价值降序排序
        4. 合并所有优先级组

        Args:
            features: 功能列表

        Returns:
            排序后的功能列表

        Raises:
            ValueError: 当features为空时
        """
        if not features:
            raise ValueError("功能列表不能为空")

        logger.info(f"[FeaturePrioritizer] 开始排序 - 功能数: {len(features)}")

        # 1. 计算业务价值
        for feature in features:
            feature.business_value = self.calculate_business_value(feature)

        # 2. 按优先级级别分组
        priority_groups: Dict[PriorityLevel, List[Feature]] = {
            PriorityLevel.P0: [],
            PriorityLevel.P1: [],
            PriorityLevel.P2: [],
            PriorityLevel.P3: [],
        }

        for feature in features:
            priority_groups[feature.priority].append(feature)

        # 3. 在同一优先级内按业务价值降序排序
        for priority_level in priority_groups:  # pylint: disable=c0206
            priority_groups[priority_level].sort(key=lambda f: f.business_value, reverse=True)

        # 4. 合并所有优先级组
        sorted_features = []
        for priority_level in [PriorityLevel.P0, PriorityLevel.P1, PriorityLevel.P2, PriorityLevel.P3]:
            sorted_features.extend(priority_groups[priority_level])

        # 记录排序结果
        logger.info(
            f"[FeaturePrioritizer] 排序完成 - "
            f"P0: {len(priority_groups[PriorityLevel.P0])}, "
            f"P1: {len(priority_groups[PriorityLevel.P1])}, "
            f"P2: {len(priority_groups[PriorityLevel.P2])}, "
            f"P3: {len(priority_groups[PriorityLevel.P3])}"
        )

        return sorted_features

    def calculate_business_value(self, feature: Feature) -> float:
        """计算功能的业务价值评分

        白皮书依据: 第十五章 15.0 功能完善路线图

        计算公式:
        business_value = (
            impact * impact_weight +
            urgency * urgency_weight -
            cost * cost_weight -
            risk * risk_weight
        )

        评分范围: [-10, 10]
        - 正值: 业务价值为正
        - 负值: 业务价值为负（不建议实现）

        Args:
            feature: 功能特性

        Returns:
            业务价值评分

        Raises:
            ValueError: 当评分不在[1, 10]范围时
        """
        # 验证评分范围
        for score_name, score_value in [
            ("impact", feature.impact),
            ("urgency", feature.urgency),
            ("cost", feature.cost),
            ("risk", feature.risk),
        ]:
            if not 1 <= score_value <= 10:
                raise ValueError(f"{score_name}评分必须在[1, 10]范围内: {score_value}")

        # 计算业务价值
        business_value = (
            feature.impact * self.impact_weight
            + feature.urgency * self.urgency_weight
            - feature.cost * self.cost_weight
            - feature.risk * self.risk_weight
        )

        logger.debug(
            f"[FeaturePrioritizer] 计算业务价值 - "
            f"功能: {feature.name}, "
            f"影响力: {feature.impact}, "
            f"紧急度: {feature.urgency}, "
            f"成本: {feature.cost}, "
            f"风险: {feature.risk}, "
            f"业务价值: {business_value:.2f}"
        )

        return business_value

    def get_priority_summary(self, features: List[Feature]) -> Dict[str, Any]:
        """获取优先级汇总信息

        Args:
            features: 功能列表

        Returns:
            汇总信息字典，包含:
            - total_count: 总功能数
            - p0_count: P0功能数
            - p1_count: P1功能数
            - p2_count: P2功能数
            - p3_count: P3功能数
            - avg_business_value: 平均业务价值
            - top_features: 前5个功能
        """
        if not features:
            return {
                "total_count": 0,
                "p0_count": 0,
                "p1_count": 0,
                "p2_count": 0,
                "p3_count": 0,
                "avg_business_value": 0.0,
                "top_features": [],
            }

        # 计算业务价值
        for feature in features:
            if feature.business_value == 0.0:
                feature.business_value = self.calculate_business_value(feature)

        # 统计各优先级数量
        p0_count = sum(1 for f in features if f.priority == PriorityLevel.P0)
        p1_count = sum(1 for f in features if f.priority == PriorityLevel.P1)
        p2_count = sum(1 for f in features if f.priority == PriorityLevel.P2)
        p3_count = sum(1 for f in features if f.priority == PriorityLevel.P3)

        # 计算平均业务价值
        avg_business_value = sum(f.business_value for f in features) / len(features)

        # 获取前5个功能
        sorted_features = sorted(features, key=lambda f: (f.priority.value, -f.business_value))
        top_features = [
            {"name": f.name, "priority": f.priority.name, "business_value": f.business_value}
            for f in sorted_features[:5]
        ]

        return {
            "total_count": len(features),
            "p0_count": p0_count,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "p3_count": p3_count,
            "avg_business_value": avg_business_value,
            "top_features": top_features,
        }

    def recommend_next_features(self, features: List[Feature], count: int = 3) -> List[Feature]:
        """推荐下一批要实现的功能

        Args:
            features: 功能列表
            count: 推荐数量

        Returns:
            推荐的功能列表
        """
        if not features:
            return []

        # 排序功能
        sorted_features = self.prioritize_features(features)

        # 返回前N个
        recommended = sorted_features[:count]

        logger.info(f"[FeaturePrioritizer] 推荐功能 - " f"数量: {len(recommended)}")

        for i, feature in enumerate(recommended, 1):
            logger.info(
                f"  {i}. {feature.name} " f"({feature.priority.name}, " f"业务价值: {feature.business_value:.2f})"
            )

        return recommended
