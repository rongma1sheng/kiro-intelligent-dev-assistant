"""策略库集成管理器

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 策略库集成

本模块实现认证策略的自动注册和管理，确保只有经过Z2H认证的策略才能进入实盘交易。

核心功能：
- 认证后自动注册策略到策略库
- 保存Z2H基因胶囊元数据
- 配置资金分配权重
- 设置仓位限制
- 启用实时监控
- 提供查询接口
- 撤销时从策略库移除

Author: MIA System
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.z2h_data_models import CertificationLevel, CertifiedStrategy, Z2HGeneCapsule


class StrategyStatus(Enum):
    """策略状态"""

    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 非活跃
    SUSPENDED = "suspended"  # 暂停
    REMOVED = "removed"  # 已移除


@dataclass
class StrategyMetadata:
    """策略元数据"""

    strategy_id: str
    strategy_name: str
    certification_level: CertificationLevel
    gene_capsule: Z2HGeneCapsule
    registration_date: datetime
    status: StrategyStatus

    # 资金配置
    capital_allocation_weight: float  # 资金分配权重
    max_capital_ratio: float  # 最大资金配置比例
    recommended_capital_scale: float  # 推荐资金规模

    # 仓位限制
    max_position_size: float  # 最大单笔仓位
    max_total_position: float  # 最大总仓位

    # 监控配置
    monitoring_enabled: bool = True
    alert_enabled: bool = True

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyQueryResult:
    """策略查询结果"""

    total_count: int
    strategies: List[StrategyMetadata]
    query_time: datetime


class StrategyLibraryManager:
    """策略库集成管理器

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 策略库集成

    核心功能：
    1. 认证后自动注册策略到策略库
    2. 保存Z2H基因胶囊元数据
    3. 配置资金分配权重
    4. 设置仓位限制
    5. 启用实时监控
    6. 提供查询接口
    7. 撤销时从策略库移除

    Attributes:
        strategy_library: 策略库字典 {strategy_id: StrategyMetadata}
        registration_history: 注册历史记录
    """

    def __init__(self):
        """初始化策略库管理器"""
        self.strategy_library: Dict[str, StrategyMetadata] = {}
        self.registration_history: List[Dict[str, Any]] = []

        logger.info("初始化StrategyLibraryManager")

    def register_certified_strategy(self, certified_strategy: CertifiedStrategy) -> bool:
        """注册认证策略到策略库

        白皮书依据: 第四章 4.3.2 策略库自动注册

        Args:
            certified_strategy: 认证策略对象

        Returns:
            bool: 注册是否成功

        Raises:
            ValueError: 当策略已存在时
        """
        strategy_id = certified_strategy.strategy_id

        # 检查策略是否已存在
        if strategy_id in self.strategy_library:
            raise ValueError(f"策略 {strategy_id} 已存在于策略库中")

        # 根据认证等级确定资金配置
        capital_config = self._determine_capital_configuration(
            certified_strategy.certification_level, certified_strategy.gene_capsule
        )

        # 根据认证等级确定仓位限制
        position_limits = self._determine_position_limits(
            certified_strategy.certification_level, certified_strategy.gene_capsule
        )

        # 创建策略元数据
        metadata = StrategyMetadata(
            strategy_id=strategy_id,
            strategy_name=certified_strategy.strategy_name,
            certification_level=certified_strategy.certification_level,
            gene_capsule=certified_strategy.gene_capsule,
            registration_date=datetime.now(),
            status=StrategyStatus.ACTIVE,
            capital_allocation_weight=capital_config["weight"],
            max_capital_ratio=capital_config["max_ratio"],
            recommended_capital_scale=capital_config["recommended_scale"],
            max_position_size=position_limits["max_position_size"],
            max_total_position=position_limits["max_total_position"],
            monitoring_enabled=True,
            alert_enabled=True,
            metadata={"certification_date": certified_strategy.certification_date},
        )

        # 注册到策略库
        self.strategy_library[strategy_id] = metadata

        # 记录注册历史
        self.registration_history.append(
            {
                "strategy_id": strategy_id,
                "action": "register",
                "timestamp": datetime.now(),
                "certification_level": certified_strategy.certification_level.value,
            }
        )

        logger.info(
            f"策略已注册到策略库 - "
            f"strategy_id={strategy_id}, "
            f"level={certified_strategy.certification_level.value}, "
            f"weight={capital_config['weight']:.2%}"
        )

        return True

    def _determine_capital_configuration(
        self, level: CertificationLevel, gene_capsule: Z2HGeneCapsule
    ) -> Dict[str, float]:
        """确定资金配置

        白皮书依据: 第四章 4.3.2 资金配置规则

        Args:
            level: 认证等级
            gene_capsule: Z2H基因胶囊

        Returns:
            Dict[str, float]: 资金配置字典
        """
        # 基础配置比例（基于认证等级）
        base_ratios = {
            CertificationLevel.PLATINUM: 0.20,  # 20%
            CertificationLevel.GOLD: 0.15,  # 15%
            CertificationLevel.SILVER: 0.10,  # 10%
        }

        max_ratio = base_ratios.get(level, 0.05)

        # 初始权重（可以根据策略表现动态调整）
        initial_weight = max_ratio * 0.5  # 从最大比例的50%开始

        # 推荐资金规模（从基因胶囊中获取）
        # recommended_capital_scale是一个字典，包含min/max/optimal
        recommended_scale_dict = gene_capsule.recommended_capital_scale
        if isinstance(recommended_scale_dict, dict) and "optimal" in recommended_scale_dict:
            recommended_scale = recommended_scale_dict["optimal"]
        else:
            # 如果没有optimal字段，使用默认值
            recommended_scale = 100000.0

        return {"weight": initial_weight, "max_ratio": max_ratio, "recommended_scale": recommended_scale}

    def _determine_position_limits(
        self, level: CertificationLevel, gene_capsule: Z2HGeneCapsule  # pylint: disable=unused-argument
    ) -> Dict[str, float]:  # pylint: disable=unused-argument
        """确定仓位限制

        Args:
            level: 认证等级
            gene_capsule: Z2H基因胶囊

        Returns:
            Dict[str, float]: 仓位限制字典
        """
        # 基础仓位限制（基于认证等级）
        base_limits = {
            CertificationLevel.PLATINUM: {"single": 0.10, "total": 0.80},
            CertificationLevel.GOLD: {"single": 0.08, "total": 0.70},
            CertificationLevel.SILVER: {"single": 0.05, "total": 0.60},
        }

        limits = base_limits.get(level, {"single": 0.03, "total": 0.50})

        return {"max_position_size": limits["single"], "max_total_position": limits["total"]}

    def remove_revoked_strategy(self, strategy_id: str) -> bool:
        """移除被撤销的策略

        白皮书依据: 第四章 4.3.2 策略库移除

        Args:
            strategy_id: 策略ID

        Returns:
            bool: 移除是否成功

        Raises:
            ValueError: 当策略不存在时
        """
        if strategy_id not in self.strategy_library:
            raise ValueError(f"策略 {strategy_id} 不存在于策略库中")

        # 更新策略状态为已移除
        self.strategy_library[strategy_id].status = StrategyStatus.REMOVED

        # 记录移除历史
        self.registration_history.append(
            {
                "strategy_id": strategy_id,
                "action": "remove",
                "timestamp": datetime.now(),
                "reason": "certification_revoked",
            }
        )

        # 从策略库中删除
        del self.strategy_library[strategy_id]

        logger.info(f"策略已从策略库移除 - strategy_id={strategy_id}")

        return True

    def suspend_strategy(self, strategy_id: str, reason: str = "") -> bool:
        """暂停策略

        Args:
            strategy_id: 策略ID
            reason: 暂停原因

        Returns:
            bool: 暂停是否成功

        Raises:
            ValueError: 当策略不存在时
        """
        if strategy_id not in self.strategy_library:
            raise ValueError(f"策略 {strategy_id} 不存在于策略库中")

        self.strategy_library[strategy_id].status = StrategyStatus.SUSPENDED

        self.registration_history.append(
            {"strategy_id": strategy_id, "action": "suspend", "timestamp": datetime.now(), "reason": reason}
        )

        logger.info(f"策略已暂停 - strategy_id={strategy_id}, reason={reason}")

        return True

    def activate_strategy(self, strategy_id: str) -> bool:
        """激活策略

        Args:
            strategy_id: 策略ID

        Returns:
            bool: 激活是否成功

        Raises:
            ValueError: 当策略不存在时
        """
        if strategy_id not in self.strategy_library:
            raise ValueError(f"策略 {strategy_id} 不存在于策略库中")

        self.strategy_library[strategy_id].status = StrategyStatus.ACTIVE

        self.registration_history.append(
            {"strategy_id": strategy_id, "action": "activate", "timestamp": datetime.now()}
        )

        logger.info(f"策略已激活 - strategy_id={strategy_id}")

        return True

    def update_capital_weight(self, strategy_id: str, new_weight: float) -> bool:
        """更新策略资金权重

        Args:
            strategy_id: 策略ID
            new_weight: 新的资金权重

        Returns:
            bool: 更新是否成功

        Raises:
            ValueError: 当策略不存在或权重无效时
        """
        if strategy_id not in self.strategy_library:
            raise ValueError(f"策略 {strategy_id} 不存在于策略库中")

        metadata = self.strategy_library[strategy_id]

        # 验证权重不超过最大比例
        if new_weight > metadata.max_capital_ratio:
            raise ValueError(f"权重 {new_weight:.2%} 超过最大比例 {metadata.max_capital_ratio:.2%}")

        if new_weight < 0:
            raise ValueError(f"权重不能为负数: {new_weight}")

        old_weight = metadata.capital_allocation_weight
        metadata.capital_allocation_weight = new_weight

        logger.info(
            f"策略资金权重已更新 - " f"strategy_id={strategy_id}, " f"old={old_weight:.2%}, " f"new={new_weight:.2%}"
        )

        return True

    def get_strategy(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """获取策略元数据

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[StrategyMetadata]: 策略元数据，不存在则返回None
        """
        return self.strategy_library.get(strategy_id)

    def query_strategies(
        self,
        certification_level: Optional[CertificationLevel] = None,
        status: Optional[StrategyStatus] = None,
        min_weight: Optional[float] = None,
    ) -> StrategyQueryResult:
        """查询策略

        白皮书依据: 第四章 4.3.2 策略库查询

        Args:
            certification_level: 认证等级过滤
            status: 状态过滤
            min_weight: 最小权重过滤

        Returns:
            StrategyQueryResult: 查询结果
        """
        strategies = list(self.strategy_library.values())

        # 按认证等级过滤
        if certification_level:
            strategies = [s for s in strategies if s.certification_level == certification_level]

        # 按状态过滤
        if status:
            strategies = [s for s in strategies if s.status == status]

        # 按最小权重过滤
        if min_weight is not None:
            strategies = [s for s in strategies if s.capital_allocation_weight >= min_weight]

        result = StrategyQueryResult(total_count=len(strategies), strategies=strategies, query_time=datetime.now())

        logger.info(
            f"策略查询完成 - "
            f"total={result.total_count}, "
            f"level={certification_level.value if certification_level else 'all'}"
        )

        return result

    def get_active_strategies(self) -> List[StrategyMetadata]:
        """获取所有活跃策略

        Returns:
            List[StrategyMetadata]: 活跃策略列表
        """
        return [metadata for metadata in self.strategy_library.values() if metadata.status == StrategyStatus.ACTIVE]

    def get_total_capital_weight(self) -> float:
        """获取总资金权重

        Returns:
            float: 总资金权重
        """
        return sum(
            metadata.capital_allocation_weight
            for metadata in self.strategy_library.values()
            if metadata.status == StrategyStatus.ACTIVE
        )

    def get_strategy_count_by_level(self) -> Dict[str, int]:
        """获取按等级的策略数量

        Returns:
            Dict[str, int]: 等级分布字典
        """
        distribution = {}

        for metadata in self.strategy_library.values():
            level = metadata.certification_level.value
            distribution[level] = distribution.get(level, 0) + 1

        return distribution

    def get_registration_history(
        self, strategy_id: Optional[str] = None, action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取注册历史

        Args:
            strategy_id: 策略ID过滤
            action: 操作类型过滤

        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        history = self.registration_history

        if strategy_id:
            history = [h for h in history if h["strategy_id"] == strategy_id]

        if action:
            history = [h for h in history if h["action"] == action]

        return history

    def export_strategy_library(self, output_path: str) -> None:
        """导出策略库

        Args:
            output_path: 输出文件路径

        Raises:
            IOError: 当文件写入失败时
        """
        import json  # pylint: disable=import-outside-toplevel

        # 转换为可序列化的字典
        library_data = {
            "export_time": datetime.now().isoformat(),
            "total_strategies": len(self.strategy_library),
            "active_strategies": len(self.get_active_strategies()),
            "total_capital_weight": self.get_total_capital_weight(),
            "strategies": [
                {
                    "strategy_id": m.strategy_id,
                    "strategy_name": m.strategy_name,
                    "certification_level": m.certification_level.value,
                    "registration_date": m.registration_date.isoformat(),
                    "status": m.status.value,
                    "capital_allocation_weight": m.capital_allocation_weight,
                    "max_capital_ratio": m.max_capital_ratio,
                    "recommended_capital_scale": m.recommended_capital_scale,
                    "max_position_size": m.max_position_size,
                    "max_total_position": m.max_total_position,
                    "monitoring_enabled": m.monitoring_enabled,
                    "alert_enabled": m.alert_enabled,
                }
                for m in self.strategy_library.values()
            ],
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(library_data, f, ensure_ascii=False, indent=2)

            logger.info(f"策略库已导出: {output_path}")

        except Exception as e:
            logger.error(f"导出策略库失败: {e}")
            raise IOError(f"无法写入文件: {output_path}") from e
