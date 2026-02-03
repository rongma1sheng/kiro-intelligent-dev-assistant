"""基因胶囊管理器

白皮书依据: 第五章 5.3.2 基因胶囊

本模块实现了基因胶囊管理器，负责：
- 基因胶囊的创建、存储、查询
- 版本历史管理
- JSON序列化和反序列化

定义: 策略的完整元数据封装
内容:
- 策略代码
- 参数配置
- 29维度分析报告
- Arena表现
- 魔鬼审计结果
- 进化历史
- Z2H钢印状态

存储: Redis + 知识库
Key: mia:knowledge:gene_capsule:{capsule_id}
TTL: 永久
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.brain.darwin_data_models import (
    ArenaPerformance,
    AuditResult,
    EvolutionRecord,
    GeneCapsule,
    Z2HStampStatus,
)
from src.brain.redis_storage import RedisStorageManager


class GeneCapsuleManager:
    """基因胶囊管理器

    白皮书依据: 第五章 5.3.2 基因胶囊

    负责基因胶囊的创建、存储、查询和更新。

    Attributes:
        redis_storage: Redis存储管理器
    """

    # 版本历史键前缀
    KEY_CAPSULE_HISTORY = "mia:knowledge:gene_capsule_history"

    def __init__(self, redis_storage: RedisStorageManager) -> None:
        """初始化基因胶囊管理器

        Args:
            redis_storage: Redis存储管理器实例

        Raises:
            ValueError: 当redis_storage为None时
        """
        if redis_storage is None:
            raise ValueError("Redis存储管理器不能为None")

        self._redis_storage = redis_storage
        logger.info("GeneCapsuleManager初始化完成")

    async def create_capsule(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_code: str,
        parameter_config: Dict[str, Any],
        analysis_report: Dict[str, Any],
        arena_performance: ArenaPerformance,
        audit_result: AuditResult,
        evolution_history: List[EvolutionRecord],
        z2h_status: Z2HStampStatus,
        family_id: Optional[str] = None,
    ) -> GeneCapsule:
        """创建基因胶囊

        白皮书依据: 第五章 5.3.2 基因胶囊

        创建基因胶囊时封装：
        - 策略代码
        - 参数配置
        - 29维度分析报告
        - Arena表现
        - 魔鬼审计结果
        - 进化历史
        - Z2H钢印状态

        Args:
            strategy_code: 策略代码
            parameter_config: 参数配置
            analysis_report: 29维度分析报告
            arena_performance: Arena表现
            audit_result: 魔鬼审计结果
            evolution_history: 进化历史
            z2h_status: Z2H钢印状态
            family_id: 策略家族ID（可选，默认生成新ID）

        Returns:
            GeneCapsule: 创建的基因胶囊

        Raises:
            ValueError: 当必需参数为空时
        """
        if not strategy_code:
            raise ValueError("策略代码不能为空")

        # 生成唯一ID
        capsule_id = str(uuid.uuid4())
        actual_family_id = family_id or str(uuid.uuid4())
        now = datetime.now()

        # 创建基因胶囊
        capsule = GeneCapsule(
            capsule_id=capsule_id,
            strategy_code=strategy_code,
            parameter_config=parameter_config,
            analysis_report_29d=analysis_report,
            arena_performance=arena_performance,
            devil_audit_result=audit_result,
            evolution_history=evolution_history,
            z2h_stamp_status=z2h_status,
            family_id=actual_family_id,
            created_at=now,
            updated_at=now,
            version=1,
        )

        # 存储到Redis
        await self._redis_storage.store_gene_capsule(capsule_id, capsule.to_dict())

        logger.info(f"创建基因胶囊: {capsule_id}, 家族: {actual_family_id}")
        return capsule

    async def get_capsule(self, capsule_id: str) -> Optional[GeneCapsule]:
        """按ID查询基因胶囊

        白皮书依据: 第五章 5.3.2 基因胶囊 - 需求2.6

        Args:
            capsule_id: 胶囊ID

        Returns:
            GeneCapsule: 基因胶囊，不存在返回None

        Raises:
            ValueError: 当capsule_id为空时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        data = await self._redis_storage.get_gene_capsule(capsule_id)
        if data:
            return GeneCapsule.from_dict(data)
        return None

    async def get_capsules_by_family(
        self,
        family_id: str,
    ) -> List[GeneCapsule]:
        """按策略家族查询基因胶囊

        白皮书依据: 第五章 5.3.2 基因胶囊 - 需求2.7

        Args:
            family_id: 家族ID

        Returns:
            List[GeneCapsule]: 该家族的所有基因胶囊

        Raises:
            ValueError: 当family_id为空时
        """
        if not family_id:
            raise ValueError("家族ID不能为空")

        capsule_dicts = await self._redis_storage.get_gene_capsules_by_family(family_id)
        capsules = [GeneCapsule.from_dict(d) for d in capsule_dicts]

        logger.debug(f"查询家族 {family_id} 的胶囊: {len(capsules)}个")
        return capsules

    async def update_capsule(
        self,
        capsule_id: str,
        updates: Dict[str, Any],
    ) -> GeneCapsule:
        """更新基因胶囊（保留历史版本）

        白皮书依据: 第五章 5.3.2 基因胶囊 - 需求2.8

        更新时会：
        1. 保存当前版本到历史记录
        2. 递增版本号
        3. 更新指定字段
        4. 更新updated_at时间戳

        Args:
            capsule_id: 胶囊ID
            updates: 要更新的字段字典

        Returns:
            GeneCapsule: 更新后的基因胶囊

        Raises:
            ValueError: 当capsule_id为空或胶囊不存在时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        # 获取当前版本
        current_capsule = await self.get_capsule(capsule_id)
        if current_capsule is None:
            raise ValueError(f"基因胶囊不存在: {capsule_id}")

        # 保存历史版本
        await self._save_to_history(current_capsule)

        # 创建更新后的数据
        current_data = current_capsule.to_dict()

        # 更新字段
        for key, value in updates.items():
            if key in current_data and key not in ("capsule_id", "created_at", "version"):
                if hasattr(value, "to_dict"):
                    current_data[key] = value.to_dict()
                elif isinstance(value, list) and value and hasattr(value[0], "to_dict"):
                    current_data[key] = [v.to_dict() for v in value]
                elif isinstance(value, Z2HStampStatus):
                    current_data[key] = value.value
                else:
                    current_data[key] = value

        # 递增版本号和更新时间
        current_data["version"] = current_capsule.version + 1
        current_data["updated_at"] = datetime.now().isoformat()

        # 存储更新后的胶囊
        await self._redis_storage.store_gene_capsule(capsule_id, current_data)

        # 返回更新后的胶囊
        updated_capsule = GeneCapsule.from_dict(current_data)
        logger.info(f"更新基因胶囊: {capsule_id}, 版本: {updated_capsule.version}")

        return updated_capsule

    async def _save_to_history(self, capsule: GeneCapsule) -> None:
        """保存胶囊到历史记录

        Args:
            capsule: 要保存的基因胶囊
        """
        history_key = f"{self.KEY_CAPSULE_HISTORY}:{capsule.capsule_id}"

        # 获取现有历史
        await self._redis_storage._redis_client.lrange(history_key, 0, -1)

        # 添加当前版本到历史
        capsule_json = json.dumps(capsule.to_dict(), ensure_ascii=False, default=str)
        await self._redis_storage._redis_client.lpush(history_key, capsule_json)

        logger.debug(f"保存胶囊历史: {capsule.capsule_id}, 版本: {capsule.version}")

    async def get_capsule_history(
        self,
        capsule_id: str,
    ) -> List[GeneCapsule]:
        """获取基因胶囊历史版本

        白皮书依据: 第五章 5.3.2 基因胶囊 - 需求2.8

        Args:
            capsule_id: 胶囊ID

        Returns:
            List[GeneCapsule]: 历史版本列表（按版本号降序）

        Raises:
            ValueError: 当capsule_id为空时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        history_key = f"{self.KEY_CAPSULE_HISTORY}:{capsule_id}"
        history_data = await self._redis_storage._redis_client.lrange(history_key, 0, -1)

        capsules = []
        for data_json in history_data:
            data = json.loads(data_json)
            capsules.append(GeneCapsule.from_dict(data))

        # 按版本号降序排序
        capsules.sort(key=lambda c: c.version, reverse=True)

        logger.debug(f"获取胶囊历史: {capsule_id}, {len(capsules)}个版本")
        return capsules

    def serialize(self, capsule: GeneCapsule) -> str:
        """序列化基因胶囊为JSON

        白皮书依据: 第五章 5.3.2 基因胶囊 - 需求2.9

        Args:
            capsule: 基因胶囊对象

        Returns:
            str: JSON字符串

        Raises:
            ValueError: 当capsule为None时
        """
        if capsule is None:
            raise ValueError("基因胶囊不能为None")

        return capsule.serialize()

    def deserialize(self, json_str: str) -> GeneCapsule:
        """从JSON反序列化基因胶囊

        白皮书依据: 第五章 5.3.2 基因胶囊 - 需求2.9

        Args:
            json_str: JSON字符串

        Returns:
            GeneCapsule: 基因胶囊对象

        Raises:
            ValueError: 当json_str为空或格式错误时
        """
        if not json_str:
            raise ValueError("JSON字符串不能为空")

        return GeneCapsule.deserialize(json_str)

    async def delete_capsule(self, capsule_id: str) -> bool:
        """删除基因胶囊

        Args:
            capsule_id: 胶囊ID

        Returns:
            bool: 是否删除成功

        Raises:
            ValueError: 当capsule_id为空时
        """
        if not capsule_id:
            raise ValueError("胶囊ID不能为空")

        # 删除主记录
        key = f"mia:knowledge:gene_capsule:{capsule_id}"
        result = await self._redis_storage.delete_key(key)

        # 删除历史记录
        history_key = f"{self.KEY_CAPSULE_HISTORY}:{capsule_id}"
        await self._redis_storage._redis_client.delete(history_key)

        logger.info(f"删除基因胶囊: {capsule_id}")
        return result

    async def get_all_capsule_ids(self) -> List[str]:
        """获取所有基因胶囊ID

        Returns:
            List[str]: 胶囊ID列表
        """
        return await self._redis_storage.get_all_gene_capsule_ids()

    async def count_capsules(self) -> int:
        """统计基因胶囊数量

        Returns:
            int: 胶囊数量
        """
        ids = await self.get_all_capsule_ids()
        return len(ids)

    async def get_capsules_by_z2h_status(
        self,
        status: Z2HStampStatus,
    ) -> List[GeneCapsule]:
        """按Z2H状态查询基因胶囊

        Args:
            status: Z2H钢印状态

        Returns:
            List[GeneCapsule]: 符合条件的基因胶囊列表
        """
        all_ids = await self.get_all_capsule_ids()
        capsules = []

        for capsule_id in all_ids:
            capsule = await self.get_capsule(capsule_id)
            if capsule and capsule.z2h_stamp_status == status:
                capsules.append(capsule)

        return capsules

    async def get_latest_capsules(
        self,
        limit: int = 10,
    ) -> List[GeneCapsule]:
        """获取最新的基因胶囊

        Args:
            limit: 返回数量限制

        Returns:
            List[GeneCapsule]: 最新的基因胶囊列表
        """
        all_ids = await self.get_all_capsule_ids()
        capsules = []

        for capsule_id in all_ids:
            capsule = await self.get_capsule(capsule_id)
            if capsule:
                capsules.append(capsule)

        # 按创建时间降序排序
        capsules.sort(key=lambda c: c.created_at, reverse=True)

        return capsules[:limit]


# 工厂函数
def create_test_arena_performance() -> ArenaPerformance:
    """创建测试用Arena表现数据"""
    return ArenaPerformance(
        reality_track_score=0.8,
        hell_track_score=0.7,
        cross_market_score=0.75,
        sharpe_ratio=1.5,
        max_drawdown=0.15,
        win_rate=0.6,
        profit_factor=1.8,
        test_date=datetime.now(),
    )


def create_test_audit_result() -> AuditResult:
    """创建测试用审计结果数据"""
    return AuditResult(
        passed=True,
        future_function_detected=False,
        issues=[],
        suggestions=["建议增加止损逻辑"],
        audit_date=datetime.now(),
        confidence=0.95,
    )
