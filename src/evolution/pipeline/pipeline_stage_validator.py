"""
流水线阶段验证器 (Pipeline Stage Validator)

白皮书依据: 第四章 4.3 统一验证流水线 - 阶段转换验证
"""

from typing import Dict, List, Optional

from loguru import logger

from src.evolution.pipeline.data_models import PipelineProgress, PipelineStage, StageTransition


class PipelineStageValidator:
    """流水线阶段验证器

    白皮书依据: 第四章 4.3 - 阶段转换验证

    负责验证流水线阶段转换的合法性，确保不跳过任何必需的验证步骤。

    Attributes:
        valid_transitions: 有效的阶段转换映射
    """

    # 定义有效的阶段转换
    VALID_TRANSITIONS: Dict[PipelineStage, List[PipelineStage]] = {
        PipelineStage.FACTOR_DISCOVERY: [PipelineStage.FACTOR_ARENA],
        PipelineStage.FACTOR_ARENA: [PipelineStage.STRATEGY_GENERATION],
        PipelineStage.STRATEGY_GENERATION: [PipelineStage.STRATEGY_ARENA],
        PipelineStage.STRATEGY_ARENA: [PipelineStage.SIMULATION],
        PipelineStage.SIMULATION: [PipelineStage.Z2H_CERTIFICATION],
        PipelineStage.Z2H_CERTIFICATION: [PipelineStage.STRATEGY_LIBRARY],
        PipelineStage.STRATEGY_LIBRARY: [],  # 终点，无后续阶段
    }

    def __init__(self):
        """初始化阶段验证器"""
        logger.info("初始化PipelineStageValidator")

    def validate_transition(
        self, from_stage: PipelineStage, to_stage: PipelineStage, progress: Optional[PipelineProgress] = None
    ) -> StageTransition:
        """验证阶段转换

        白皮书依据: 第四章 4.3 - 阶段转换验证规则

        Args:
            from_stage: 源阶段
            to_stage: 目标阶段
            progress: 流水线进度（可选，用于检查前置条件）

        Returns:
            阶段转换对象，包含是否有效和必需条件
        """
        # 检查是否是有效的直接转换
        valid_next_stages = self.VALID_TRANSITIONS.get(from_stage, [])
        is_valid = to_stage in valid_next_stages

        required_conditions = []

        if not is_valid:
            required_conditions.append(f"不允许从{from_stage.value}直接转换到{to_stage.value}")

        # 如果提供了进度信息，检查前置阶段是否完成
        if progress and is_valid:
            # 获取所有前置阶段
            prerequisite_stages = self._get_prerequisite_stages(to_stage)

            for prereq_stage in prerequisite_stages:
                if not progress.is_stage_completed(prereq_stage):
                    is_valid = False
                    required_conditions.append(f"前置阶段{prereq_stage.value}未完成")

        transition = StageTransition(
            from_stage=from_stage, to_stage=to_stage, is_valid=is_valid, required_conditions=required_conditions
        )

        if not is_valid:
            logger.warning(f"无效的阶段转换: {from_stage.value} → {to_stage.value}, " f"原因: {required_conditions}")
        else:
            logger.debug(f"有效的阶段转换: {from_stage.value} → {to_stage.value}")

        return transition

    def _get_prerequisite_stages(self, stage: PipelineStage) -> List[PipelineStage]:
        """获取指定阶段的所有前置阶段

        Args:
            stage: 目标阶段

        Returns:
            前置阶段列表
        """
        # 定义阶段顺序
        stage_order = [
            PipelineStage.FACTOR_DISCOVERY,
            PipelineStage.FACTOR_ARENA,
            PipelineStage.STRATEGY_GENERATION,
            PipelineStage.STRATEGY_ARENA,
            PipelineStage.SIMULATION,
            PipelineStage.Z2H_CERTIFICATION,
            PipelineStage.STRATEGY_LIBRARY,
        ]

        try:
            stage_index = stage_order.index(stage)
            return stage_order[:stage_index]
        except ValueError:
            return []

    def get_next_stage(self, current_stage: PipelineStage) -> Optional[PipelineStage]:
        """获取下一个阶段

        Args:
            current_stage: 当前阶段

        Returns:
            下一个阶段，如果是终点则返回None
        """
        valid_next_stages = self.VALID_TRANSITIONS.get(current_stage, [])

        if not valid_next_stages:
            return None

        # 返回第一个有效的下一阶段
        return valid_next_stages[0]

    def is_terminal_stage(self, stage: PipelineStage) -> bool:
        """检查是否是终点阶段

        Args:
            stage: 流水线阶段

        Returns:
            是否是终点阶段
        """
        return stage == PipelineStage.STRATEGY_LIBRARY

    def validate_stage_sequence(self, stages: List[PipelineStage]) -> bool:
        """验证阶段序列是否有效

        白皮书依据: 第四章 4.3 - 流水线序列验证

        Args:
            stages: 阶段序列

        Returns:
            序列是否有效
        """
        if not stages:
            return True

        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]

            transition = self.validate_transition(current_stage, next_stage)
            if not transition.is_valid:
                logger.error(f"无效的阶段序列: 第{i}到{i+1}步转换失败 " f"({current_stage.value} → {next_stage.value})")
                return False

        return True

    def get_required_stages(self, entity_type: str) -> List[PipelineStage]:
        """获取指定实体类型的必需阶段

        Args:
            entity_type: 实体类型（'factor'或'strategy'）

        Returns:
            必需阶段列表
        """
        if entity_type == "factor":  # pylint: disable=no-else-return
            # 因子需要经过前两个阶段
            return [PipelineStage.FACTOR_DISCOVERY, PipelineStage.FACTOR_ARENA]
        elif entity_type == "strategy":
            # 策略需要经过所有阶段
            return [
                PipelineStage.STRATEGY_GENERATION,
                PipelineStage.STRATEGY_ARENA,
                PipelineStage.SIMULATION,
                PipelineStage.Z2H_CERTIFICATION,
                PipelineStage.STRATEGY_LIBRARY,
            ]
        else:
            raise ValueError(f"未知的实体类型: {entity_type}")

    def can_skip_stage(self, stage: PipelineStage) -> bool:  # pylint: disable=unused-argument
        """检查阶段是否可以跳过

        白皮书依据: 第四章 4.3 - 所有阶段都是必需的

        Args:
            stage: 流水线阶段

        Returns:
            是否可以跳过（始终返回False，因为所有阶段都是必需的）
        """
        # 根据白皮书，所有阶段都是必需的，不允许跳过
        return False
