"""Z2H Certifier - Main Coordinator for Z2H Certification

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.z2h.capsule_storage import CapsuleStorage
from src.evolution.z2h.data_models import CertificationResult, Z2HGeneCapsule
from src.evolution.z2h.gene_capsule_generator import GeneCapsuleGenerator
from src.evolution.z2h.signature_manager import SignatureManager
from src.infra.event_bus import EventBus, EventType


class Z2HCertifier:
    """Z2H认证器

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    主要协调器，负责：
    1. 生成Z2H基因胶囊
    2. SHA256签名
    3. 双重存储（Redis + 文件系统）
    4. 签名验证
    5. 事件发布
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        event_bus: Optional[EventBus] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        storage_dir: str = "data/z2h_capsules",
    ):
        """初始化Z2H认证器

        Args:
            event_bus: 事件总线
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            storage_dir: 文件系统存储目录
        """
        self.event_bus = event_bus or EventBus()

        # 初始化组件
        self.generator = GeneCapsuleGenerator()
        self.signature_manager = SignatureManager()
        self.storage = CapsuleStorage(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            storage_dir=storage_dir,
        )

        logger.info("Z2HCertifier初始化完成")

    async def certify_strategy(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        source_factors: List[str],
        arena_score: float,
        simulation_metrics: Dict[str, float],
        metadata: Dict[str, Any] = None,
    ) -> Z2HGeneCapsule:
        """认证策略并生成Z2H基因胶囊

        白皮书依据: 第四章 4.3.2 Z2H认证流程

        完整流程：
        1. 生成基因胶囊
        2. SHA256签名
        3. 存储到Redis（1年TTL）
        4. 存储到文件系统（JSON）
        5. 发布Z2H_CERTIFIED事件

        Args:
            strategy_id: 策略唯一标识
            strategy_name: 策略名称
            source_factors: 源因子ID列表
            arena_score: Arena综合评分
            simulation_metrics: 模拟盘指标
            metadata: 额外元数据

        Returns:
            Z2H基因胶囊

        Raises:
            ValueError: 当策略不符合认证条件时
        """
        logger.info(f"开始Z2H认证流程: {strategy_id}")

        # 1. 生成基因胶囊
        try:
            capsule = self.generator.generate_capsule(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                source_factors=source_factors,
                arena_score=arena_score,
                simulation_metrics=simulation_metrics,
                metadata=metadata,
            )
        except ValueError as e:
            logger.error(f"生成基因胶囊失败: {e}")
            raise

        # 2. SHA256签名
        self.signature_manager.sign_capsule(capsule)

        # 3. 双重存储
        success = self.storage.store(capsule)

        if not success:
            logger.error(f"存储基因胶囊失败: {strategy_id}")
            raise RuntimeError(f"存储基因胶囊失败: {strategy_id}")

        # 4. 发布Z2H_CERTIFIED事件
        from src.infra.event_bus import Event, EventPriority  # pylint: disable=import-outside-toplevel

        event = Event(
            event_type=EventType.Z2H_CERTIFIED,
            source_module="z2h_certifier",
            priority=EventPriority.HIGH,
            data={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "certification_level": capsule.certification_level.value,
                "arena_score": arena_score,
                "sharpe_ratio": simulation_metrics.get("sharpe_ratio", 0.0),
                "max_drawdown": simulation_metrics.get("max_drawdown", 0.0),
                "certification_date": capsule.certification_date.isoformat(),
            },
        )
        await self.event_bus.publish(event)

        logger.info(
            f"Z2H认证完成: {strategy_id}, "
            f"认证等级: {capsule.certification_level.value}, "
            f"Arena评分: {arena_score:.3f}"
        )

        return capsule

    async def verify_capsule(self, strategy_id: str) -> bool:
        """验证基因胶囊的完整性和签名

        白皮书依据: 第四章 4.3.2 签名验证

        Args:
            strategy_id: 策略ID

        Returns:
            是否验证通过
        """
        # 1. 检索基因胶囊
        capsule = self.storage.retrieve(strategy_id)

        if capsule is None:
            logger.error(f"基因胶囊不存在: {strategy_id}")
            return False

        # 2. 验证签名
        if not self.signature_manager.verify_signature(capsule):
            logger.error(f"基因胶囊签名验证失败: {strategy_id}")

            # 发布安全警报事件
            from src.infra.event_bus import Event, EventPriority  # pylint: disable=import-outside-toplevel

            event = Event(
                event_type=EventType.SECURITY_ALERT,
                source_module="z2h_certifier",
                priority=EventPriority.CRITICAL,
                data={
                    "alert_type": "capsule_tampering",
                    "strategy_id": strategy_id,
                    "message": f"基因胶囊签名验证失败，可能被篡改",  # pylint: disable=w1309
                },
            )
            await self.event_bus.publish(event)

            return False

        # 3. 验证认证等级与指标一致性
        if not self.generator.validate_capsule(capsule):
            logger.error(f"基因胶囊认证等级与指标不一致: {strategy_id}")
            return False

        logger.info(f"基因胶囊验证通过: {strategy_id}")
        return True

    def get_capsule(self, strategy_id: str) -> Optional[Z2HGeneCapsule]:
        """获取基因胶囊

        Args:
            strategy_id: 策略ID

        Returns:
            Z2H基因胶囊，如果不存在则返回None
        """
        return self.storage.retrieve(strategy_id)

    def list_certified_strategies(self) -> List[str]:
        """列出所有已认证的策略ID

        Returns:
            策略ID列表
        """
        return self.storage.list_all()

    def revoke_certification(self, strategy_id: str) -> bool:
        """撤销认证（删除基因胶囊）

        Args:
            strategy_id: 策略ID

        Returns:
            是否撤销成功
        """
        logger.warning(f"撤销Z2H认证: {strategy_id}")

        success = self.storage.delete(strategy_id)

        if success:
            # 发布认证撤销事件
            from src.infra.event_bus import Event, EventPriority  # pylint: disable=import-outside-toplevel

            event = Event(
                event_type=EventType.Z2H_REVOKED,
                source_module="z2h_certifier",
                priority=EventPriority.HIGH,
                data={
                    "strategy_id": strategy_id,
                    "reason": "manual_revocation",
                },
            )
            self.event_bus.publish_sync(event)

        return success

    def check_certification_eligibility(
        self,
        arena_score: float,
        simulation_metrics: Dict[str, float],
    ) -> CertificationResult:
        """检查策略是否符合认证条件（不生成胶囊）

        Args:
            arena_score: Arena综合评分
            simulation_metrics: 模拟盘指标

        Returns:
            认证结果
        """
        return self.generator.determine_certification_level(arena_score, simulation_metrics)

    def get_statistics(self) -> Dict[str, Any]:
        """获取认证系统统计信息

        Returns:
            统计信息
        """
        storage_stats = self.storage.get_statistics()

        # 统计各认证等级的数量
        level_counts = {"PLATINUM": 0, "GOLD": 0, "SILVER": 0}

        for strategy_id in self.storage.list_all():
            capsule = self.storage.retrieve(strategy_id)
            if capsule:
                level_counts[capsule.certification_level.value] += 1

        stats = {
            "total_certified": storage_stats["total_capsules"],
            "certification_levels": level_counts,
            "storage_stats": storage_stats,
        }

        logger.info(
            f"Z2H认证统计: "
            f"总数={stats['total_certified']}, "
            f"PLATINUM={level_counts['PLATINUM']}, "
            f"GOLD={level_counts['GOLD']}, "
            f"SILVER={level_counts['SILVER']}"
        )

        return stats
