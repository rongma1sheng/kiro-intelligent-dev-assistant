"""
验证流水线数据模型 (Validation Pipeline Data Models)

白皮书依据: 第四章 4.3 统一验证流水线
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PipelineStage(Enum):
    """流水线阶段

    白皮书依据: 第四章 4.3 - 验证流水线阶段

    完整流程:
    FACTOR_DISCOVERY → FACTOR_ARENA → STRATEGY_GENERATION →
    STRATEGY_ARENA → SIMULATION → Z2H_CERTIFICATION → STRATEGY_LIBRARY
    """

    FACTOR_DISCOVERY = "factor_discovery"  # 因子发现
    FACTOR_ARENA = "factor_arena"  # 因子Arena测试
    STRATEGY_GENERATION = "strategy_generation"  # 策略生成
    STRATEGY_ARENA = "strategy_arena"  # 策略Arena测试
    SIMULATION = "simulation"  # 模拟盘验证
    Z2H_CERTIFICATION = "z2h_certification"  # Z2H认证
    STRATEGY_LIBRARY = "strategy_library"  # 策略库注册


class PipelineState(Enum):
    """流水线状态"""

    PENDING = "pending"  # 等待中
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    SKIPPED = "skipped"  # 跳过（仅用于可选阶段）


@dataclass
class ValidationRecord:
    """验证记录

    白皮书依据: 第四章 4.3 - 验证记录追踪

    Attributes:
        stage: 验证阶段
        state: 阶段状态
        started_at: 开始时间
        completed_at: 完成时间
        duration_seconds: 耗时(秒)
        result: 验证结果
        error_message: 错误信息（如果失败）
        metadata: 额外元数据
    """

    stage: PipelineStage
    state: PipelineState
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性"""
        if not isinstance(self.stage, PipelineStage):
            raise TypeError(f"stage必须是PipelineStage枚举，当前类型: {type(self.stage)}")
        if not isinstance(self.state, PipelineState):
            raise TypeError(f"state必须是PipelineState枚举，当前类型: {type(self.state)}")
        if self.duration_seconds < 0:
            raise ValueError(f"耗时不能为负数，当前值: {self.duration_seconds}")


@dataclass
class PipelineProgress:
    """流水线进度

    白皮书依据: 第四章 4.3 - 流水线进度追踪

    Attributes:
        entity_id: 实体ID（因子ID或策略ID）
        entity_type: 实体类型（factor或strategy）
        current_stage: 当前阶段
        validation_records: 验证记录列表
        created_at: 创建时间
        updated_at: 更新时间
        is_completed: 是否完成整个流水线
        is_failed: 是否失败
    """

    entity_id: str
    entity_type: str
    current_stage: PipelineStage
    validation_records: List[ValidationRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_completed: bool = False
    is_failed: bool = False

    def __post_init__(self):
        """验证数据有效性"""
        if not self.entity_id:
            raise ValueError("实体ID不能为空")
        if self.entity_type not in ["factor", "strategy"]:
            raise ValueError(f"实体类型必须是'factor'或'strategy'，当前值: {self.entity_type}")
        if not isinstance(self.current_stage, PipelineStage):
            raise TypeError(f"current_stage必须是PipelineStage枚举，当前类型: {type(self.current_stage)}")

    def get_stage_record(self, stage: PipelineStage) -> Optional[ValidationRecord]:
        """获取指定阶段的验证记录

        Args:
            stage: 流水线阶段

        Returns:
            验证记录，如果不存在则返回None
        """
        for record in self.validation_records:
            if record.stage == stage:
                return record
        return None

    def is_stage_completed(self, stage: PipelineStage) -> bool:
        """检查指定阶段是否已完成

        Args:
            stage: 流水线阶段

        Returns:
            是否已完成
        """
        record = self.get_stage_record(stage)
        return record is not None and record.state == PipelineState.COMPLETED

    def get_completion_percentage(self) -> float:
        """获取完成百分比

        Returns:
            完成百分比 [0, 100]
        """
        total_stages = len(PipelineStage)
        completed_stages = sum(1 for record in self.validation_records if record.state == PipelineState.COMPLETED)
        return (completed_stages / total_stages) * 100 if total_stages > 0 else 0.0


@dataclass
class StageTransition:
    """阶段转换

    白皮书依据: 第四章 4.3 - 阶段转换规则

    Attributes:
        from_stage: 源阶段
        to_stage: 目标阶段
        is_valid: 是否有效转换
        required_conditions: 必需条件列表
    """

    from_stage: PipelineStage
    to_stage: PipelineStage
    is_valid: bool
    required_conditions: List[str] = field(default_factory=list)

    def __post_init__(self):
        """验证数据有效性"""
        if not isinstance(self.from_stage, PipelineStage):
            raise TypeError(f"from_stage必须是PipelineStage枚举")  # pylint: disable=w1309
        if not isinstance(self.to_stage, PipelineStage):
            raise TypeError(f"to_stage必须是PipelineStage枚举")  # pylint: disable=w1309
