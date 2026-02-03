# pylint: disable=too-many-lines
"""Chronos时空调度器

白皮书依据: 第一章 柯罗诺斯生物钟与资源调度

实现"时空折叠"哲学，将从微秒到年的所有时间尺度统一管理。
"""

import asyncio
import heapq
import os

# 导入事件总线
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.infra.event_bus import Event as BusEvent  # pylint: disable=c0413
from src.infra.event_bus import EventPriority, EventType, get_event_bus  # pylint: disable=c0413


class Priority(Enum):
    """任务优先级

    白皮书依据: 第一章 1.3 任务优先级管理

    支持5个优先级等级，数值越大优先级越高。
    """

    CRITICAL = 5
    HIGH = 4
    NORMAL = 3
    LOW = 2
    IDLE = 1


class TimeScale(Enum):
    """时间尺度

    白皮书依据: 第一章 1.1 多时间尺度统一调度

    支持7个时间尺度，从微秒到年的完整覆盖。
    """

    MICROSECOND = "microsecond"
    MILLISECOND = "millisecond"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    YEAR = "year"


@dataclass
class Task:
    """调度任务

    白皮书依据: 第一章 1.1 多时间尺度统一调度

    表示一个可调度的任务，包含执行逻辑、优先级、时间间隔等信息。

    Attributes:
        task_id: 任务唯一标识
        name: 任务名称
        callback: 任务回调函数
        priority: 任务优先级
        interval: 执行间隔（秒）
        next_run: 下次执行时间（时间戳）
        enabled: 是否启用
        dependencies: 依赖的任务ID列表
        execution_count: 执行次数统计
        last_execution_time: 上次执行时间

    Example:
        >>> task = Task(
        ...     task_id="data_sync_001",
        ...     name="数据同步任务",
        ...     callback=lambda: print("同步数据"),
        ...     priority=Priority.HIGH,
        ...     interval=60.0,
        ...     next_run=time.time() + 60.0
        ... )
    """

    task_id: str
    name: str
    callback: Callable[[], None]
    priority: Priority
    interval: float
    next_run: float
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    execution_count: int = field(default=0, init=False)
    last_execution_time: Optional[float] = field(default=None, init=False)

    def __post_init__(self) -> None:
        """初始化后处理

        验证参数有效性并设置默认值。

        Raises:
            ValueError: 当参数不合法时
        """
        if not self.task_id:
            raise ValueError("task_id不能为空")

        if not self.name:
            raise ValueError("name不能为空")

        if not callable(self.callback):
            raise ValueError("callback必须是可调用对象")

        if self.interval <= 0:
            raise ValueError(f"interval必须 > 0，当前: {self.interval}")

        if self.next_run <= 0:
            raise ValueError(f"next_run必须 > 0，当前: {self.next_run}")

    def __lt__(self, other: "Task") -> bool:
        """用于优先队列排序

        排序规则：
        1. 按next_run升序（时间早的先执行）
        2. 时间相同时按priority降序（优先级高的先执行）

        Args:
            other: 另一个任务

        Returns:
            是否小于另一个任务
        """
        if self.next_run != other.next_run:
            return self.next_run < other.next_run
        return self.priority.value > other.priority.value

    def should_execute(self, current_time: float) -> bool:
        """判断是否应该执行

        Args:
            current_time: 当前时间戳

        Returns:
            是否应该执行
        """
        return self.enabled and self.next_run <= current_time

    def update_next_run(self, current_time: float) -> None:
        """更新下次执行时间

        Args:
            current_time: 当前时间戳
        """
        self.next_run = current_time + self.interval
        self.execution_count += 1
        self.last_execution_time = current_time


class ChronosScheduler:
    """Chronos时空调度器

    白皮书依据: 第一章 1.1 多时间尺度统一调度

    统一管理从微秒到年的所有时间尺度任务，实现时空折叠。
    支持任务优先级、依赖关系、动态调整等高级功能。

    Attributes:
        tasks: 任务字典 {task_id: Task}
        task_queue: 优先队列（按next_run和priority排序）
        running: 调度器运行状态
        scheduler_thread: 调度器线程
        lock: 线程锁

    Performance:
        调度延迟: < 1ms (P99)

    Example:
        >>> scheduler = ChronosScheduler()
        >>> task_id = scheduler.add_task(
        ...     name="test_task",
        ...     callback=lambda: print("Hello"),
        ...     interval=1.0,
        ...     priority=Priority.NORMAL
        ... )
        >>> scheduler.start()
        >>> # ... 任务会每秒执行一次
        >>> scheduler.stop()
    """

    def __init__(self) -> None:
        """初始化调度器"""
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []
        self.running: bool = False
        self.scheduler_thread: Optional[Thread] = None
        self.lock: Lock = Lock()
        self.wakeup_event: Event = Event()  # 用于事件驱动调度

        # 事件总线支持
        self.event_bus = None
        self.event_loop = None
        self.pending_responses = {}  # 存储待发送的响应 {correlation_id: response_data}

        # vLLM资源感知支持
        self.vllm_resource_state = {
            "memory_pressure": "low",
            "last_memory_check": 0.0,
            "memory_check_interval": 1.0,  # 每秒检查一次内存状态
            "resource_constraints": {
                "max_concurrent_tasks": 20,
                "current_concurrent_tasks": 0,
                "memory_threshold_high": 0.85,
                "memory_threshold_critical": 0.95,
            },
            "vllm_aware_scheduling": False,  # 默认禁用vLLM感知调度（避免测试环境问题）
            "adaptive_scheduling": True,  # 启用自适应调度
        }

        # 时间尺度转换表
        self._time_scale_conversions = {
            TimeScale.MICROSECOND: 1e-6,
            TimeScale.MILLISECOND: 1e-3,
            TimeScale.SECOND: 1.0,
            TimeScale.MINUTE: 60.0,
            TimeScale.HOUR: 3600.0,
            TimeScale.DAY: 86400.0,
            TimeScale.YEAR: 31536000.0,
        }

        logger.info("ChronosScheduler initialized (vLLM-aware)")

    async def initialize(self):
        """初始化事件总线连接和事件订阅

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - 事件驱动解耦
        """
        try:
            # 获取事件总线实例
            self.event_bus = await get_event_bus()

            # 订阅系统查询事件
            await self.event_bus.subscribe(
                EventType.SYSTEM_QUERY, self._handle_system_query, "chronos_scheduler_query_handler"
            )

            logger.info("ChronosScheduler事件订阅完成")

        except Exception as e:
            logger.error(f"ChronosScheduler初始化失败: {e}")
            raise

    async def _handle_system_query(self, event: BusEvent):
        """处理系统查询事件

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - 跨模块通信

        Args:
            event: 系统查询事件
        """
        try:
            query_type = event.data.get("query_type")
            correlation_id = event.data.get("correlation_id")
            requester = event.data.get("requester")

            if not correlation_id:
                logger.warning("系统查询事件缺少correlation_id")
                return

            logger.info(
                f"[ChronosScheduler] 收到系统查询: {query_type} from {requester}, correlation_id={correlation_id}"
            )

            # 根据查询类型生成响应数据（使用同步方法避免事件循环问题）
            response_data = {}

            if query_type == "schedule_info":
                # 使用同步方法获取调度状态
                response_data = self.get_current_schedule_sync()
            elif query_type == "task_stats":
                response_data = self.get_task_statistics()
            elif query_type == "scheduler_status":
                response_data = self.get_scheduler_status()
            elif query_type == "vllm_resource_info":
                # vLLM资源信息查询
                response_data = self.get_vllm_resource_info()
            elif query_type == "memory_allocation":
                # vLLM内存分配请求处理（简化为同步）
                memory_needed = event.data.get("memory_needed", 0.0)
                response_data = self._handle_memory_allocation_request_sync(memory_needed, requester)
            else:
                logger.warning(f"未知的查询类型: {query_type}")
                response_data = {"error": f"未知的查询类型: {query_type}"}

            logger.info(
                f"[ChronosScheduler] 准备发送响应: correlation_id={correlation_id}, data_keys={list(response_data.keys())}"
            )

            # 发布系统响应事件
            response_event = BusEvent(
                event_type=EventType.SYSTEM_RESPONSE,
                source_module="chronos_scheduler",
                target_module=requester,
                priority=EventPriority.HIGH,
                data={
                    "correlation_id": correlation_id,
                    "query_type": query_type,
                    "response_data": response_data,
                    "timestamp": time.time(),
                    "status": "success",
                },
            )

            await self.event_bus.publish(response_event)

            logger.info(f"[ChronosScheduler] 系统响应已发送: {correlation_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[ChronosScheduler] 系统查询处理失败: {e}", exc_info=True)

            # 发送错误响应
            if "correlation_id" in locals():
                error_event = BusEvent(
                    event_type=EventType.SYSTEM_RESPONSE,
                    source_module="chronos_scheduler",
                    target_module=event.data.get("requester", "unknown"),
                    priority=EventPriority.HIGH,
                    data={
                        "correlation_id": correlation_id,
                        "query_type": event.data.get("query_type", "unknown"),
                        "response_data": {"error": str(e)},
                        "timestamp": time.time(),
                        "status": "error",
                    },
                )

                try:
                    await self.event_bus.publish(error_event)
                except Exception as publish_error:  # pylint: disable=broad-exception-caught
                    logger.error(f"错误响应发送失败: {publish_error}")

    async def _handle_memory_allocation_request(self, memory_needed: float, requester: str) -> Dict[str, Any]:
        """处理vLLM内存分配请求（异步版本）

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - vLLM资源协同

        Args:
            memory_needed: 需要的内存大小（GB）
            requester: 请求者模块名

        Returns:
            处理结果
        """
        return self._handle_memory_allocation_request_sync(memory_needed, requester)

    def _handle_memory_allocation_request_sync(self, memory_needed: float, requester: str) -> Dict[str, Any]:
        """处理vLLM内存分配请求（同步版本）

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - vLLM资源协同

        Args:
            memory_needed: 需要的内存大小（GB）
            requester: 请求者模块名

        Returns:
            处理结果
        """
        try:
            logger.info(f"收到vLLM内存分配请求: {memory_needed}GB from {requester}")

            # 获取当前内存压力（不查询vLLM，使用缓存的状态）
            memory_pressure = self.vllm_resource_state["memory_pressure"]

            # 根据内存压力和请求大小决定是否批准分配
            if memory_pressure == "critical":  # pylint: disable=no-else-return
                # 严重压力：拒绝所有分配
                return {
                    "allocation_approved": False,
                    "reason": "内存压力严重，暂停新分配",
                    "memory_pressure": memory_pressure,
                    "recommendation": "等待内存清理完成",
                    "timestamp": time.time(),
                }

            elif memory_pressure == "high":
                # 高压力：只批准小于1GB的分配
                if memory_needed > 1.0:
                    return {
                        "allocation_approved": False,
                        "reason": "内存压力较高，限制大内存分配",
                        "memory_pressure": memory_pressure,
                        "max_allowed_gb": 1.0,
                        "recommendation": "减小分配大小或等待内存释放",
                        "timestamp": time.time(),
                    }

            elif memory_pressure == "moderate":
                # 中等压力：限制大于5GB的分配
                if memory_needed > 5.0:
                    return {
                        "allocation_approved": False,
                        "reason": "内存压力中等，限制超大内存分配",
                        "memory_pressure": memory_pressure,
                        "max_allowed_gb": 5.0,
                        "recommendation": "考虑分批分配",
                        "timestamp": time.time(),
                    }

            # 批准分配
            return {
                "allocation_approved": True,
                "memory_pressure": memory_pressure,
                "allocated_gb": memory_needed,
                "recommendation": "分配已批准，建议监控内存使用",
                "timestamp": time.time(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"处理内存分配请求失败: {e}")
            return {"allocation_approved": False, "reason": f"处理失败: {str(e)}", "timestamp": time.time()}

    async def get_current_schedule(self) -> Dict[str, Any]:
        """获取当前调度状态信息（异步版本）

        白皮书依据: 第一章 1.1 多时间尺度统一调度

        Returns:
            当前调度状态字典
        """
        return self.get_current_schedule_sync()

    def get_current_schedule_sync(self) -> Dict[str, Any]:
        """获取当前调度状态信息（同步版本）

        白皮书依据: 第一章 1.1 多时间尺度统一调度

        Returns:
            当前调度状态字典
        """
        try:
            with self.lock:
                current_time = time.time()

                # 统计任务信息
                total_tasks = len(self.tasks)
                enabled_tasks = sum(1 for task in self.tasks.values() if task.enabled)
                disabled_tasks = total_tasks - enabled_tasks

                # 统计即将执行的任务
                upcoming_tasks = []
                for task in self.task_queue[:5]:  # 前5个即将执行的任务
                    if task.enabled:
                        upcoming_tasks.append(
                            {
                                "task_id": task.task_id,
                                "name": task.name,
                                "next_run": task.next_run,
                                "time_until_run": max(0, task.next_run - current_time),
                                "priority": task.priority.name,
                                "execution_count": task.execution_count,
                            }
                        )

                # 统计优先级分布
                priority_stats = {}
                for priority in Priority:
                    count = sum(1 for task in self.tasks.values() if task.priority == priority and task.enabled)
                    priority_stats[priority.name] = count

                # 计算调度器负载
                next_task_time = self.task_queue[0].next_run if self.task_queue else None
                scheduler_load = min(1.0, enabled_tasks / 100.0)  # 假设100个任务为满负载

                # vLLM资源状态
                vllm_resource_info = {
                    "memory_pressure": self.vllm_resource_state["memory_pressure"],
                    "last_memory_check": self.vllm_resource_state["last_memory_check"],
                    "current_concurrent_tasks": self.vllm_resource_state["resource_constraints"][
                        "current_concurrent_tasks"
                    ],
                    "max_concurrent_tasks": self.vllm_resource_state["resource_constraints"]["max_concurrent_tasks"],
                    "vllm_aware_scheduling": self.vllm_resource_state["vllm_aware_scheduling"],
                    "adaptive_scheduling": self.vllm_resource_state["adaptive_scheduling"],
                }

                return {
                    "scheduler_running": self.running,
                    "total_tasks": total_tasks,
                    "enabled_tasks": enabled_tasks,
                    "disabled_tasks": disabled_tasks,
                    "upcoming_tasks": upcoming_tasks,
                    "priority_distribution": priority_stats,
                    "next_task_time": next_task_time,
                    "scheduler_load": scheduler_load,
                    "current_time": current_time,
                    "queue_size": len(self.task_queue),
                    "vllm_resource_state": vllm_resource_info,
                }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取调度状态失败: {e}")
            return {"error": str(e), "scheduler_running": self.running, "current_time": time.time()}

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息

        Returns:
            任务统计信息字典
        """
        try:
            with self.lock:
                total_executions = sum(task.execution_count for task in self.tasks.values())

                # 最活跃的任务
                most_active_tasks = sorted(
                    [(task.name, task.execution_count) for task in self.tasks.values()],
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]

                # 最近执行的任务
                recent_tasks = []
                for task in self.tasks.values():
                    if task.last_execution_time:
                        recent_tasks.append(
                            {
                                "name": task.name,
                                "last_execution": task.last_execution_time,
                                "execution_count": task.execution_count,
                            }
                        )

                recent_tasks.sort(key=lambda x: x["last_execution"], reverse=True)
                recent_tasks = recent_tasks[:5]

                return {
                    "total_executions": total_executions,
                    "most_active_tasks": most_active_tasks,
                    "recent_tasks": recent_tasks,
                    "average_executions_per_task": total_executions / max(len(self.tasks), 1),
                }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取任务统计失败: {e}")
            return {"error": str(e)}

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态信息

        Returns:
            调度器状态信息字典
        """
        try:
            return {
                "running": self.running,
                "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False,
                "event_bus_connected": self.event_bus is not None,
                "wakeup_event_set": self.wakeup_event.is_set(),
                "lock_locked": self.lock.locked(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取调度器状态失败: {e}")
            return {"error": str(e)}

    def add_task(  # pylint: disable=too-many-positional-arguments
        self,
        name: str,
        callback: Callable[[], None],
        interval: float,
        priority: Priority = Priority.NORMAL,
        time_scale: TimeScale = TimeScale.SECOND,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """添加调度任务

        白皮书依据: 第一章 1.1 多时间尺度统一调度

        Args:
            name: 任务名称
            callback: 任务回调函数
            interval: 执行间隔
            priority: 任务优先级
            time_scale: 时间尺度
            dependencies: 依赖的任务ID列表

        Returns:
            任务ID

        Raises:
            ValueError: 当参数不合法时

        Example:
            >>> task_id = scheduler.add_task(
            ...     name="data_sync",
            ...     callback=sync_data,
            ...     interval=60.0,
            ...     priority=Priority.HIGH
            ... )
        """
        # 参数验证
        if not name:
            raise ValueError("任务名称不能为空")

        if not callable(callback):
            raise ValueError("callback必须是可调用对象")

        if interval <= 0:
            raise ValueError(f"interval必须 > 0，当前: {interval}")

        # 转换时间尺度到秒
        interval_seconds = self._convert_to_seconds(interval, time_scale)

        # 生成任务ID
        task_id = f"{name}_{int(time.time() * 1000000)}"

        # 创建任务
        task = Task(
            task_id=task_id,
            name=name,
            callback=callback,
            priority=priority,
            interval=interval_seconds,
            next_run=time.time() + interval_seconds,
            dependencies=dependencies or [],
        )

        # 添加到任务字典和队列
        with self.lock:
            self.tasks[task_id] = task
            heapq.heappush(self.task_queue, task)
            # 唤醒调度器线程，立即处理新任务
            self.wakeup_event.set()

        logger.info(f"Task added: {name} (id={task_id}, " f"interval={interval_seconds}s, priority={priority.name})")

        return task_id

    def remove_task(self, task_id: str) -> bool:
        """移除调度任务

        Args:
            task_id: 任务ID

        Returns:
            是否移除成功
        """
        with self.lock:
            if task_id not in self.tasks:
                return False

            # 从任务字典中移除
            task = self.tasks.pop(task_id)

            # 禁用任务（从队列中移除会在下次调度时处理）
            task.enabled = False

            logger.info(f"Task removed: {task.name} (id={task_id})")
            return True

    def start(self) -> None:
        """启动调度器

        Raises:
            RuntimeError: 当调度器已经运行时
        """
        if self.running:
            raise RuntimeError("调度器已经在运行")

        self.running = True
        self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        logger.info("ChronosScheduler started")

    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            return

        self.running = False
        self.wakeup_event.set()  # 唤醒调度器线程以便退出

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1.0)

        logger.info("ChronosScheduler stopped")

    def get_task_info(self, task_id: str) -> Optional[Dict]:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，不存在时返回None
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

            return {
                "task_id": task.task_id,
                "name": task.name,
                "priority": task.priority.name,
                "interval": task.interval,
                "next_run": task.next_run,
                "enabled": task.enabled,
                "execution_count": task.execution_count,
                "last_execution_time": task.last_execution_time,
                "dependencies": task.dependencies.copy(),
            }

    def _convert_to_seconds(self, interval: float, time_scale: TimeScale) -> float:
        """将时间间隔转换为秒

        白皮书依据: 第一章 1.1 多时间尺度统一调度

        Args:
            interval: 时间间隔
            time_scale: 时间尺度

        Returns:
            秒数
        """
        return interval * self._time_scale_conversions[time_scale]

    def _scheduler_loop(self) -> None:
        """调度器主循环（内部方法）- 高性能优化版本（vLLM感知）

        白皮书依据: 第一章 1.1 多时间尺度统一调度

        性能要求: 调度延迟 < 1ms (P99)

        优化策略:
        1. 混合等待策略：远期任务使用Event.wait()，近期任务使用busy-wait
        2. 批量任务收集：一次性收集所有就绪任务，减少锁竞争
        3. 锁外执行：在锁外执行任务，避免阻塞调度循环
        4. 零延迟调度：对于即将到期的任务（< 2ms），使用busy-wait确保精确调度
        5. vLLM资源感知：根据vLLM内存压力动态调整任务调度策略
        """
        logger.info("Scheduler loop started (high-performance, vLLM-aware)")

        # 创建事件循环用于异步操作
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.event_loop = loop

        # vLLM资源状态更新计数器
        vllm_update_counter = 0
        vllm_update_interval = 10  # 每10次循环更新一次vLLM状态

        while self.running:
            current_time = time.time()
            ready_tasks = []
            next_task_time = None

            # === 阶段0: 定期更新vLLM资源状态 ===
            if self.vllm_resource_state["vllm_aware_scheduling"]:
                vllm_update_counter += 1
                if vllm_update_counter >= vllm_update_interval:
                    try:
                        # 使用create_task异步执行，避免阻塞事件循环
                        asyncio.create_task(self.update_vllm_resource_state())
                        vllm_update_counter = 0
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.error(f"更新vLLM资源状态失败: {e}")

            # === 阶段1: 快速收集就绪任务（持锁时间最小化） ===
            with self.lock:
                # 收集所有就绪任务
                while self.task_queue and self.task_queue[0].should_execute(current_time):
                    task = heapq.heappop(self.task_queue)

                    # 跳过已禁用的任务
                    if not task.enabled:
                        continue

                    # vLLM资源感知：检查是否应该限流
                    if self.should_throttle_task(task):
                        # 延迟任务执行
                        task.next_run = current_time + 1.0  # 延迟1秒
                        heapq.heappush(self.task_queue, task)
                        logger.debug(
                            f"任务被限流: {task.name}, 内存压力: {self.vllm_resource_state['memory_pressure']}"
                        )
                        continue

                    # 检查依赖
                    if not self._check_dependencies(task):
                        # 依赖未满足，延迟100ms后重试
                        task.next_run = current_time + 0.1
                        heapq.heappush(self.task_queue, task)
                        continue

                    ready_tasks.append(task)

                # 获取下一个任务的执行时间（用于智能等待）
                if self.task_queue:
                    next_task_time = self.task_queue[0].next_run

            # === 阶段2: 在锁外执行任务（避免阻塞） ===
            if ready_tasks:
                # 按优先级排序（优先级高的先执行）
                ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)

                # 更新并发任务计数
                self.vllm_resource_state["resource_constraints"]["current_concurrent_tasks"] = len(ready_tasks)

                # 执行所有就绪任务
                for task in ready_tasks:
                    self._execute_task(task)

                    # 更新下次执行时间
                    task.update_next_run(current_time)

                # 重置并发任务计数
                self.vllm_resource_state["resource_constraints"]["current_concurrent_tasks"] = 0

                # === 阶段3: 将任务重新加入队列 ===
                with self.lock:
                    for task in ready_tasks:
                        heapq.heappush(self.task_queue, task)

                    # 更新下一个任务时间
                    if self.task_queue:
                        next_task_time = self.task_queue[0].next_run

            # === 阶段4: 混合等待策略（事件驱动 + Busy-wait） ===
            if next_task_time is not None:
                # 计算需要等待的时间
                wait_time = next_task_time - time.time()

                if wait_time > 0.002:  # > 2ms，使用Event.wait()节省CPU
                    # 等待到距离下一个任务2ms的时候
                    self.wakeup_event.wait(timeout=wait_time - 0.002)
                    self.wakeup_event.clear()
                elif wait_time > 0:  # 0-2ms，使用busy-wait确保精确调度
                    # Busy-wait for precise timing
                    while time.time() < next_task_time and self.running:
                        pass  # Spin-wait for sub-millisecond precision
                # else: 任务已经到期，立即执行下一轮
            else:
                # 没有任务，等待新任务添加
                self.wakeup_event.wait(timeout=0.01)
                self.wakeup_event.clear()

        # 清理事件循环
        loop.close()

        logger.info("Scheduler loop stopped")

    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖是否满足（内部方法）

        Args:
            task: 要检查的任务

        Returns:
            依赖是否满足
        """
        if not task.dependencies:
            return True

        for dep_name in task.dependencies:
            # 首先尝试按任务ID查找
            dep_task = self.tasks.get(dep_name)

            # 如果按ID找不到，尝试按任务名称查找
            if not dep_task:
                for task_id, t in self.tasks.items():  # pylint: disable=unused-variable
                    if t.name == dep_name:
                        dep_task = t
                        break

            if not dep_task:
                logger.warning(f"Dependency not found: {dep_name} for task {task.task_id}")
                return False

            # 简单的依赖检查：依赖任务必须至少执行过一次
            if dep_task.execution_count == 0:
                return False

        return True

    def _execute_task(self, task: Task) -> None:
        """执行任务（内部方法）

        Args:
            task: 要执行的任务
        """
        try:
            start_time = time.perf_counter()

            # 执行回调
            task.callback()

            elapsed = time.perf_counter() - start_time

            logger.debug(
                f"Task executed: {task.name} " f"(elapsed={elapsed*1000:.2f}ms, count={task.execution_count + 1})"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Task execution failed: {task.name} (id={task.task_id}), " f"error={e}")

    # ==================== vLLM资源感知方法 ====================

    async def query_vllm_memory_state(self) -> Dict[str, Any]:
        """查询vLLM内存状态

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - vLLM资源协同

        通过事件总线查询VLLMMemoryCoordinator的内存状态，
        用于智能调度决策。

        Returns:
            vLLM内存状态字典
        """
        try:
            if not self.event_bus:
                logger.debug("事件总线未初始化，无法查询vLLM内存状态")
                return {"error": "事件总线未初始化"}

            correlation_id = f"chronos_vllm_query_{int(time.time() * 1000000)}"

            # 发布系统查询事件
            query_event = BusEvent(
                event_type=EventType.SYSTEM_QUERY,
                source_module="chronos_scheduler",
                target_module="vllm_memory_coordinator",
                priority=EventPriority.HIGH,
                data={
                    "query_type": "memory_pressure",
                    "correlation_id": correlation_id,
                    "requester": "chronos_scheduler",
                    "timestamp": time.time(),
                },
            )

            await self.event_bus.publish(query_event)

            # 等待响应（使用更短的超时避免阻塞，0.1秒）
            response = await self._wait_for_vllm_response(correlation_id, timeout=0.1)

            if response:  # pylint: disable=no-else-return
                return response
            else:
                logger.debug("vLLM内存状态查询超时（vllm_memory_coordinator可能未运行）")
                return {"error": "查询超时", "memory_pressure": "unknown"}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug(f"查询vLLM内存状态失败: {e}")
            return {"error": str(e), "memory_pressure": "unknown"}

    async def _wait_for_vllm_response(self, correlation_id: str, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """等待vLLM响应

        Args:
            correlation_id: 关联ID
            timeout: 超时时间（秒）

        Returns:
            响应数据，超时返回None
        """
        try:
            time.time()

            # 创建响应Future
            response_future = asyncio.Future()
            self.pending_responses[correlation_id] = response_future

            # 订阅响应事件（临时订阅）
            async def response_handler(event: BusEvent):
                if event.data.get("correlation_id") == correlation_id:
                    if not response_future.done():
                        response_future.set_result(event.data.get("response_data"))

            await self.event_bus.subscribe(
                EventType.SYSTEM_RESPONSE, response_handler, f"chronos_vllm_response_{correlation_id}"
            )

            # 等待响应
            try:
                response_data = await asyncio.wait_for(response_future, timeout=timeout)
                return response_data
            except asyncio.TimeoutError:
                return None
            finally:
                # 清理
                self.pending_responses.pop(correlation_id, None)
                # 取消订阅
                try:
                    await self.event_bus.unsubscribe(
                        EventType.SYSTEM_RESPONSE, f"chronos_vllm_response_{correlation_id}"
                    )
                except:  # pylint: disable=w0702
                    pass

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"等待vLLM响应失败: {e}")
            return None

    async def update_vllm_resource_state(self):
        """更新vLLM资源状态

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - vLLM资源感知

        定期查询vLLM内存状态，更新调度器的资源感知信息，
        用于自适应调度决策。
        """
        try:
            current_time = time.time()

            # 检查是否需要更新
            if (
                current_time - self.vllm_resource_state["last_memory_check"]
                < self.vllm_resource_state["memory_check_interval"]
            ):
                return

            # 查询vLLM内存状态（使用更短的超时避免阻塞）
            memory_state = await self.query_vllm_memory_state()

            if "error" not in memory_state:
                # 更新内存压力等级
                overall_pressure = memory_state.get("overall_pressure", "low")
                self.vllm_resource_state["memory_pressure"] = overall_pressure
                self.vllm_resource_state["last_memory_check"] = current_time

                # 根据内存压力调整并发任务限制
                await self._adjust_concurrent_task_limit(overall_pressure)

                logger.debug(f"vLLM资源状态已更新: 内存压力={overall_pressure}")
            else:
                # 查询失败时，更新检查时间避免频繁重试
                self.vllm_resource_state["last_memory_check"] = current_time
                logger.debug(f"vLLM资源状态更新失败（已跳过）: {memory_state.get('error')}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            # 更新检查时间避免频繁重试
            self.vllm_resource_state["last_memory_check"] = time.time()
            logger.debug(f"更新vLLM资源状态失败（已跳过）: {e}")

    async def _adjust_concurrent_task_limit(self, memory_pressure: str):
        """根据内存压力调整并发任务限制

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - 自适应调度

        Args:
            memory_pressure: 内存压力等级 (low/moderate/high/critical)
        """
        try:
            constraints = self.vllm_resource_state["resource_constraints"]

            # 根据内存压力调整最大并发任务数
            if memory_pressure == "critical":
                # 严重压力：降低到5个并发任务
                constraints["max_concurrent_tasks"] = 5
                logger.warning("vLLM内存压力严重，降低并发任务限制到5")

            elif memory_pressure == "high":
                # 高压力：降低到10个并发任务
                constraints["max_concurrent_tasks"] = 10
                logger.info("vLLM内存压力较高，降低并发任务限制到10")

            elif memory_pressure == "moderate":
                # 中等压力：15个并发任务
                constraints["max_concurrent_tasks"] = 15

            else:  # low
                # 低压力：恢复到20个并发任务
                constraints["max_concurrent_tasks"] = 20

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"调整并发任务限制失败: {e}")

    def should_throttle_task(self, task: Task) -> bool:
        """判断是否应该限流任务

        白皮书依据: 第一章 1.1 多时间尺度统一调度 - vLLM资源感知

        根据vLLM资源状态和任务优先级，决定是否应该延迟任务执行。

        Args:
            task: 要检查的任务

        Returns:
            是否应该限流
        """
        try:
            if not self.vllm_resource_state["vllm_aware_scheduling"]:
                return False

            constraints = self.vllm_resource_state["resource_constraints"]
            memory_pressure = self.vllm_resource_state["memory_pressure"]

            # 检查并发任务限制
            if constraints["current_concurrent_tasks"] >= constraints["max_concurrent_tasks"]:
                # 高优先级任务（CRITICAL）不限流
                if task.priority == Priority.CRITICAL:
                    return False
                return True

            # 根据内存压力和任务优先级决定
            if memory_pressure == "critical":  # pylint: disable=no-else-return
                # 严重压力：只允许CRITICAL任务
                return task.priority != Priority.CRITICAL

            elif memory_pressure == "high":
                # 高压力：只允许CRITICAL和HIGH任务
                return task.priority not in [Priority.CRITICAL, Priority.HIGH]

            elif memory_pressure == "moderate":
                # 中等压力：限流LOW和IDLE任务
                return task.priority in [Priority.LOW, Priority.IDLE]

            # 低压力：不限流
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"判断任务限流失败: {e}")
            return False

    def get_vllm_resource_info(self) -> Dict[str, Any]:
        """获取vLLM资源信息

        Returns:
            vLLM资源状态信息
        """
        try:
            return {
                "memory_pressure": self.vllm_resource_state["memory_pressure"],
                "last_memory_check": self.vllm_resource_state["last_memory_check"],
                "memory_check_interval": self.vllm_resource_state["memory_check_interval"],
                "resource_constraints": self.vllm_resource_state["resource_constraints"].copy(),
                "vllm_aware_scheduling": self.vllm_resource_state["vllm_aware_scheduling"],
                "adaptive_scheduling": self.vllm_resource_state["adaptive_scheduling"],
                "timestamp": time.time(),
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取vLLM资源信息失败: {e}")
            return {"error": str(e)}
