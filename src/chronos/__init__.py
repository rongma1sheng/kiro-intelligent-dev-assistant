"""Chronos时空调度器

白皮书依据: 第一章 柯罗诺斯生物钟与资源调度

Chronos调度器实现"时空折叠"哲学，将从微秒到年的所有时间尺度统一管理。
采用分布式五态生物钟进行严格的资源分时调度。

核心组件:
- scheduler: 主调度器
- orchestrator: 五态状态机（主编排器）
- gpu_watchdog: GPU看门狗
- Priority: 任务优先级枚举
- TimeScale: 时间尺度枚举
- Task: 任务数据类
- SystemState: 系统状态枚举
- GPUStatus: GPU状态枚举
"""

from .gpu_watchdog import GPUMetrics, GPUStatus, GPUWatchdog
from .orchestrator import (
    MainOrchestrator,
    ServiceStartupError,
    StateTransitionError,
    SystemState,
)
from .scheduler import ChronosScheduler, Priority, Task, TimeScale

__all__ = [
    "ChronosScheduler",
    "Priority",
    "TimeScale",
    "Task",
    "MainOrchestrator",
    "SystemState",
    "StateTransitionError",
    "ServiceStartupError",
    "GPUWatchdog",
    "GPUStatus",
    "GPUMetrics",
]
