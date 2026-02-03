"""
验证流水线系统 (Validation Pipeline System)

白皮书依据: 第四章 4.3 统一验证流水线
版本: v1.0.0
作者: MIA Team
日期: 2026-01-23

核心理念: 通过统一的验证流水线确保所有因子和策略都经过严格的质量检验，
从因子发现到策略部署的每个环节都有明确的标准和流程。

主要组件:
1. ValidationPipelineManager: 端到端验证流程编排器
2. PipelineStageValidator: 阶段转换验证器
3. PipelineStateTracker: 进度跟踪器
4. PipelineStage: 流水线阶段枚举
"""

from src.evolution.pipeline.data_models import PipelineProgress, PipelineStage, PipelineState, ValidationRecord
from src.evolution.pipeline.pipeline_stage_validator import PipelineStageValidator
from src.evolution.pipeline.pipeline_state_tracker import PipelineStateTracker
from src.evolution.pipeline.validation_pipeline_manager import ValidationPipelineManager

__all__ = [
    # Data Models
    "PipelineStage",
    "PipelineState",
    "ValidationRecord",
    "PipelineProgress",
    # Core Components
    "ValidationPipelineManager",
    "PipelineStageValidator",
    "PipelineStateTracker",
]
