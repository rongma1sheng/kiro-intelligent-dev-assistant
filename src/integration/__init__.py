"""集成模块

白皮书依据: 第三章 3.1 高性能数据管道 + 第一章 1.1 多时间尺度统一调度

提供调度器与数据管道的集成功能。
"""

from .scheduler_pipeline import (
    DataPassingSink,
    DataPassingSource,
    PipelineTask,
    ScheduledPipelineManager,
    create_data_processing_chain,
)

__all__ = [
    "ScheduledPipelineManager",
    "PipelineTask",
    "DataPassingSource",
    "DataPassingSink",
    "create_data_processing_chain",
]
