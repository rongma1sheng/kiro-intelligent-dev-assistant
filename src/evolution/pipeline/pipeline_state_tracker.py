"""
流水线状态追踪器 (Pipeline State Tracker)

白皮书依据: 第四章 4.3 统一验证流水线 - 进度追踪
"""

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.evolution.pipeline.data_models import PipelineProgress, PipelineStage, PipelineState, ValidationRecord


class PipelineStateTracker:
    """流水线状态追踪器

    白皮书依据: 第四章 4.3 - 流水线进度追踪

    负责追踪和管理流水线中每个实体的进度状态。

    Attributes:
        progress_store: 进度存储字典 {entity_id: PipelineProgress}
    """

    def __init__(self):
        """初始化状态追踪器"""
        self.progress_store: Dict[str, PipelineProgress] = {}
        logger.info("初始化PipelineStateTracker")

    def create_progress(
        self, entity_id: str, entity_type: str, initial_stage: PipelineStage = PipelineStage.FACTOR_DISCOVERY
    ) -> PipelineProgress:
        """创建新的进度记录

        Args:
            entity_id: 实体ID
            entity_type: 实体类型（'factor'或'strategy'）
            initial_stage: 初始阶段

        Returns:
            新创建的进度对象

        Raises:
            ValueError: 当实体ID已存在时
        """
        if entity_id in self.progress_store:
            raise ValueError(f"实体ID已存在: {entity_id}")

        progress = PipelineProgress(entity_id=entity_id, entity_type=entity_type, current_stage=initial_stage)

        self.progress_store[entity_id] = progress

        logger.info(
            f"创建进度记录: entity_id={entity_id}, "
            f"entity_type={entity_type}, "
            f"initial_stage={initial_stage.value}"
        )

        return progress

    def get_progress(self, entity_id: str) -> Optional[PipelineProgress]:
        """获取进度记录

        Args:
            entity_id: 实体ID

        Returns:
            进度对象，如果不存在则返回None
        """
        return self.progress_store.get(entity_id)

    def update_stage(self, entity_id: str, new_stage: PipelineStage) -> None:
        """更新当前阶段

        Args:
            entity_id: 实体ID
            new_stage: 新阶段

        Raises:
            ValueError: 当实体不存在时
        """
        progress = self.get_progress(entity_id)
        if not progress:
            raise ValueError(f"实体不存在: {entity_id}")

        old_stage = progress.current_stage
        progress.current_stage = new_stage
        progress.updated_at = datetime.now()

        logger.info(f"更新阶段: entity_id={entity_id}, " f"{old_stage.value} → {new_stage.value}")

    def start_stage(self, entity_id: str, stage: PipelineStage, metadata: Optional[Dict] = None) -> ValidationRecord:
        """开始一个阶段

        Args:
            entity_id: 实体ID
            stage: 流水线阶段
            metadata: 额外元数据

        Returns:
            新创建的验证记录

        Raises:
            ValueError: 当实体不存在时
        """
        progress = self.get_progress(entity_id)
        if not progress:
            raise ValueError(f"实体不存在: {entity_id}")

        # 创建验证记录
        record = ValidationRecord(
            stage=stage, state=PipelineState.IN_PROGRESS, started_at=datetime.now(), metadata=metadata or {}
        )

        # 添加到进度记录
        progress.validation_records.append(record)
        progress.current_stage = stage
        progress.updated_at = datetime.now()

        logger.info(f"开始阶段: entity_id={entity_id}, stage={stage.value}")

        return record

    def complete_stage(self, entity_id: str, stage: PipelineStage, result: Optional[Dict] = None) -> None:
        """完成一个阶段

        Args:
            entity_id: 实体ID
            stage: 流水线阶段
            result: 验证结果

        Raises:
            ValueError: 当实体不存在或阶段记录不存在时
        """
        progress = self.get_progress(entity_id)
        if not progress:
            raise ValueError(f"实体不存在: {entity_id}")

        # 查找阶段记录
        record = progress.get_stage_record(stage)
        if not record:
            raise ValueError(f"阶段记录不存在: {stage.value}")

        # 更新记录
        record.state = PipelineState.COMPLETED
        record.completed_at = datetime.now()
        record.duration_seconds = (record.completed_at - record.started_at).total_seconds()
        record.result = result

        progress.updated_at = datetime.now()

        logger.info(
            f"完成阶段: entity_id={entity_id}, " f"stage={stage.value}, " f"duration={record.duration_seconds:.2f}s"
        )

    def fail_stage(self, entity_id: str, stage: PipelineStage, error_message: str) -> None:
        """标记阶段失败

        Args:
            entity_id: 实体ID
            stage: 流水线阶段
            error_message: 错误信息

        Raises:
            ValueError: 当实体不存在或阶段记录不存在时
        """
        progress = self.get_progress(entity_id)
        if not progress:
            raise ValueError(f"实体不存在: {entity_id}")

        # 查找阶段记录
        record = progress.get_stage_record(stage)
        if not record:
            raise ValueError(f"阶段记录不存在: {stage.value}")

        # 更新记录
        record.state = PipelineState.FAILED
        record.completed_at = datetime.now()
        record.duration_seconds = (record.completed_at - record.started_at).total_seconds()
        record.error_message = error_message

        # 标记整个流水线失败
        progress.is_failed = True
        progress.updated_at = datetime.now()

        logger.error(f"阶段失败: entity_id={entity_id}, " f"stage={stage.value}, " f"error={error_message}")

    def mark_completed(self, entity_id: str) -> None:
        """标记整个流水线完成

        Args:
            entity_id: 实体ID

        Raises:
            ValueError: 当实体不存在时
        """
        progress = self.get_progress(entity_id)
        if not progress:
            raise ValueError(f"实体不存在: {entity_id}")

        progress.is_completed = True
        progress.updated_at = datetime.now()

        logger.info(f"流水线完成: entity_id={entity_id}")

    def get_all_progress(self) -> List[PipelineProgress]:
        """获取所有进度记录

        Returns:
            进度记录列表
        """
        return list(self.progress_store.values())

    def get_progress_by_stage(self, stage: PipelineStage) -> List[PipelineProgress]:
        """获取指定阶段的所有进度记录

        Args:
            stage: 流水线阶段

        Returns:
            进度记录列表
        """
        return [progress for progress in self.progress_store.values() if progress.current_stage == stage]

    def get_failed_progress(self) -> List[PipelineProgress]:
        """获取所有失败的进度记录

        Returns:
            失败的进度记录列表
        """
        return [progress for progress in self.progress_store.values() if progress.is_failed]

    def get_completed_progress(self) -> List[PipelineProgress]:
        """获取所有完成的进度记录

        Returns:
            完成的进度记录列表
        """
        return [progress for progress in self.progress_store.values() if progress.is_completed]

    def get_statistics(self) -> Dict[str, any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        total = len(self.progress_store)
        completed = len(self.get_completed_progress())
        failed = len(self.get_failed_progress())
        in_progress = total - completed - failed

        # 按阶段统计
        stage_counts = {}
        for stage in PipelineStage:
            stage_counts[stage.value] = len(self.get_progress_by_stage(stage))

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "completion_rate": (completed / total * 100) if total > 0 else 0.0,
            "failure_rate": (failed / total * 100) if total > 0 else 0.0,
            "stage_distribution": stage_counts,
        }

    def clear(self) -> None:
        """清空所有进度记录"""
        self.progress_store.clear()
        logger.info("清空所有进度记录")
