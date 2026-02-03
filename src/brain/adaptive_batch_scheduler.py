"""
自适应批处理调度器 - vLLM优化组件

白皮书依据: 第二章 2.1 AI三脑架构 + vLLM集成优化
需求: 8.3, 8.5, 8.6 - 自适应批处理调度器

核心功能:
- 动态批大小调整算法
- 基于延迟目标的性能优化
- 请求优先级排序（Soldier > Commander > Scholar）
- 自适应负载均衡
- 内存压力感知调度
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from ..core.dependency_container import LifecycleScope, injectable
from ..infra.event_bus import EventBus


class RequestPriority(Enum):
    """请求优先级"""

    CRITICAL = 1  # Soldier - 实时决策
    HIGH = 2  # Commander - 策略分析
    NORMAL = 3  # Scholar - 因子研究
    LOW = 4  # 后台任务


@dataclass
class BatchRequest:
    """批处理请求"""

    request_id: str
    source_module: str
    priority: RequestPriority
    prompt: str
    max_tokens: int
    temperature: float
    timestamp: float
    deadline: float  # 截止时间
    callback: Optional[callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchConfig:
    """批处理配置"""

    # 延迟目标 (毫秒)
    soldier_target_latency: float = 10.0  # Soldier < 10ms
    commander_target_latency: float = 200.0  # Commander < 200ms
    scholar_target_latency: float = 1000.0  # Scholar < 1s

    # 批大小范围
    min_batch_size: int = 1
    max_batch_size: int = 32
    initial_batch_size: int = 4

    # 调度参数
    batch_timeout_ms: float = 50.0  # 批处理超时
    queue_timeout_ms: float = 5000.0  # 队列超时
    memory_pressure_threshold: float = 0.8  # 内存压力阈值

    # 自适应参数
    latency_window_size: int = 100  # 延迟统计窗口
    adjustment_factor: float = 0.1  # 调整因子
    min_adjustment_interval: float = 1.0  # 最小调整间隔(秒)


@injectable(LifecycleScope.SINGLETON)
class AdaptiveBatchScheduler:
    """自适应批处理调度器

    白皮书依据: 第二章 2.1 AI三脑架构 - vLLM集成优化
    需求: 8.3, 8.5, 8.6 - 自适应批处理调度器
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """初始化自适应批处理调度器"""
        self.config = config or BatchConfig()
        self.state = "IDLE"

        # 请求队列 (按优先级分组)
        self.request_queues: Dict[RequestPriority, deque] = {priority: deque() for priority in RequestPriority}

        # 当前批大小 (按优先级)
        self.current_batch_sizes: Dict[RequestPriority, int] = {
            RequestPriority.CRITICAL: self.config.initial_batch_size,
            RequestPriority.HIGH: self.config.initial_batch_size * 2,
            RequestPriority.NORMAL: self.config.initial_batch_size * 4,
            RequestPriority.LOW: self.config.initial_batch_size * 8,
        }

        # 延迟统计
        self.latency_history: Dict[RequestPriority, deque] = {
            priority: deque(maxlen=self.config.latency_window_size) for priority in RequestPriority
        }

        # 调度统计
        self.stats = {
            "total_requests": 0,
            "batches_processed": 0,
            "avg_batch_size": 0.0,
            "avg_latency_ms": 0.0,
            "queue_overflow_count": 0,
            "memory_pressure_events": 0,
            "batch_size_adjustments": 0,
            "priority_stats": {
                priority.name: {"requests": 0, "avg_latency_ms": 0.0, "current_batch_size": size}
                for priority, size in self.current_batch_sizes.items()
            },
        }

        # 内存监控
        self.memory_pressure = 0.0
        self.last_adjustment_time = 0.0

        # 事件总线
        self.event_bus: Optional[EventBus] = None

        # 调度任务
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info("[AdaptiveBatchScheduler] Initialized with adaptive batching")

    async def initialize(self):
        """初始化调度器"""
        try:
            logger.info("[AdaptiveBatchScheduler] Starting initialization...")

            # 获取事件总线
            from ..infra.event_bus import get_event_bus  # pylint: disable=import-outside-toplevel

            self.event_bus = await get_event_bus()

            # 启动调度循环
            await self.start_scheduler()

            self.state = "READY"
            logger.info("[AdaptiveBatchScheduler] Initialization completed")

        except Exception as e:
            self.state = "ERROR"
            logger.error(f"[AdaptiveBatchScheduler] Initialization failed: {e}")
            raise RuntimeError(f"AdaptiveBatchScheduler initialization failed: {e}") from e

    async def start_scheduler(self):
        """启动调度器"""
        if self._running:
            logger.warning("[AdaptiveBatchScheduler] Scheduler already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("[AdaptiveBatchScheduler] Scheduler started")

    async def stop_scheduler(self):
        """停止调度器"""
        if not self._running:
            return

        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("[AdaptiveBatchScheduler] Scheduler stopped")

    async def submit_request(  # pylint: disable=too-many-positional-arguments
        self,
        request_id: str,
        source_module: str,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        deadline_ms: Optional[float] = None,
        callback: Optional[callable] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """提交推理请求

        白皮书依据: 第二章 2.1 AI三脑架构 - 请求优先级排序
        需求: 8.5, 8.6 - 请求优先级排序

        Args:
            request_id: 请求ID
            source_module: 来源模块 (soldier/commander/scholar)
            prompt: 推理提示
            max_tokens: 最大token数
            temperature: 温度参数
            deadline_ms: 截止时间(毫秒)，None表示使用默认
            callback: 回调函数
            metadata: 元数据

        Returns:
            str: 请求ID

        Raises:
            ValueError: 当参数无效时
            RuntimeError: 当队列满时
        """
        if not self._running:
            raise RuntimeError("Scheduler not running")

        # 确定优先级
        priority = self._determine_priority(source_module)

        # 计算截止时间
        current_time = time.time()
        if deadline_ms is None:
            deadline_ms = self._get_default_deadline(priority)

        deadline = current_time + (deadline_ms / 1000.0)

        # 创建请求
        request = BatchRequest(
            request_id=request_id,
            source_module=source_module,
            priority=priority,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timestamp=current_time,
            deadline=deadline,
            callback=callback,
            metadata=metadata or {},
        )

        # 检查队列容量
        queue = self.request_queues[priority]
        max_queue_size = self._get_max_queue_size(priority)

        if len(queue) >= max_queue_size:
            self.stats["queue_overflow_count"] += 1
            logger.warning(f"[AdaptiveBatchScheduler] Queue overflow for {priority.name}")
            raise RuntimeError(f"Queue full for priority {priority.name}")

        # 添加到队列
        queue.append(request)
        self.stats["total_requests"] += 1
        self.stats["priority_stats"][priority.name]["requests"] += 1

        logger.debug(f"[AdaptiveBatchScheduler] Request submitted: {request_id} ({priority.name})")

        return request_id

    def _determine_priority(self, source_module: str) -> RequestPriority:
        """确定请求优先级

        白皮书依据: 第二章 2.1 AI三脑架构 - 优先级定义
        需求: 8.5 - 请求优先级排序（Soldier > Commander > Scholar）

        Args:
            source_module: 来源模块

        Returns:
            RequestPriority: 请求优先级
        """
        source_lower = source_module.lower()

        if "soldier" in source_lower:  # pylint: disable=no-else-return
            return RequestPriority.CRITICAL  # Soldier - 实时决策，最高优先级
        elif "commander" in source_lower:
            return RequestPriority.HIGH  # Commander - 策略分析，高优先级
        elif "scholar" in source_lower:
            return RequestPriority.NORMAL  # Scholar - 因子研究，普通优先级
        else:
            return RequestPriority.LOW  # 其他 - 后台任务，低优先级

    def _get_default_deadline(self, priority: RequestPriority) -> float:
        """获取默认截止时间(毫秒)

        白皮书依据: 第二章 2.1 AI三脑架构 - 延迟目标
        需求: 8.6 - 延迟目标优化

        Args:
            priority: 请求优先级

        Returns:
            float: 截止时间(毫秒)
        """
        if priority == RequestPriority.CRITICAL:  # pylint: disable=no-else-return
            return self.config.soldier_target_latency
        elif priority == RequestPriority.HIGH:
            return self.config.commander_target_latency
        elif priority == RequestPriority.NORMAL:
            return self.config.scholar_target_latency
        else:
            return self.config.scholar_target_latency * 2  # 后台任务更宽松

    def _get_max_queue_size(self, priority: RequestPriority) -> int:
        """获取队列最大大小"""
        if priority == RequestPriority.CRITICAL:  # pylint: disable=no-else-return
            return 100  # Soldier队列较小，保证低延迟
        elif priority == RequestPriority.HIGH:
            return 200  # Commander队列中等
        elif priority == RequestPriority.NORMAL:
            return 500  # Scholar队列较大
        else:
            return 1000  # 后台任务队列最大

    async def _scheduler_loop(self):
        """调度循环

        白皮书依据: 第二章 2.1 AI三脑架构 - 自适应调度
        需求: 8.3 - 动态批大小调整算法
        """
        logger.info("[AdaptiveBatchScheduler] Scheduler loop started")

        while self._running:
            try:
                # 更新内存压力
                await self._update_memory_pressure()

                # 处理各优先级队列
                for priority in RequestPriority:
                    await self._process_priority_queue(priority)

                # 自适应调整批大小
                await self._adaptive_batch_size_adjustment()

                # 清理过期请求
                await self._cleanup_expired_requests()

                # 短暂休眠
                await asyncio.sleep(0.01)  # 10ms调度间隔

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"[AdaptiveBatchScheduler] Scheduler loop error: {e}")
                await asyncio.sleep(0.1)

        logger.info("[AdaptiveBatchScheduler] Scheduler loop stopped")

    async def _process_priority_queue(self, priority: RequestPriority):
        """处理优先级队列

        Args:
            priority: 请求优先级
        """
        queue = self.request_queues[priority]
        if not queue:
            return

        # 获取当前批大小
        batch_size = self.current_batch_sizes[priority]

        # 内存压力调整
        if self.memory_pressure > self.config.memory_pressure_threshold:
            batch_size = max(1, batch_size // 2)  # 内存压力下减小批大小

        # 收集批请求
        batch_requests = []
        current_time = time.time()

        while len(batch_requests) < batch_size and queue:
            request = queue[0]

            # 检查是否过期
            if current_time > request.deadline:
                expired_request = queue.popleft()
                logger.warning(f"[AdaptiveBatchScheduler] Request expired: {expired_request.request_id}")
                continue

            batch_requests.append(queue.popleft())

        # 处理批请求
        if batch_requests:
            await self._process_batch(batch_requests, priority)

    async def _process_batch(self, batch_requests: List[BatchRequest], priority: RequestPriority):
        """处理批请求

        Args:
            batch_requests: 批请求列表
            priority: 请求优先级
        """
        batch_start_time = time.time()

        try:
            logger.debug(f"[AdaptiveBatchScheduler] Processing batch: {len(batch_requests)} requests ({priority.name})")

            # 模拟批处理推理
            await self._simulate_batch_inference(batch_requests)

            # 计算延迟
            batch_latency = (time.time() - batch_start_time) * 1000  # 毫秒

            # 更新统计
            self._update_batch_statistics(batch_requests, batch_latency, priority)

            # 执行回调
            for request in batch_requests:
                if request.callback:
                    try:
                        await request.callback(request.request_id, "success", {"latency_ms": batch_latency})
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.error(f"[AdaptiveBatchScheduler] Callback error: {e}")

            logger.debug(f"[AdaptiveBatchScheduler] Batch completed: {batch_latency:.2f}ms ({priority.name})")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AdaptiveBatchScheduler] Batch processing failed: {e}")

            # 错误回调
            for request in batch_requests:
                if request.callback:
                    try:
                        await request.callback(request.request_id, "error", {"error": str(e)})
                    except Exception as callback_error:  # pylint: disable=broad-exception-caught
                        logger.error(f"[AdaptiveBatchScheduler] Error callback failed: {callback_error}")

    async def _simulate_batch_inference(self, batch_requests: List[BatchRequest]):
        """模拟批处理推理

        Args:
            batch_requests: 批请求列表
        """
        # 模拟推理延迟 (基于批大小和复杂度)
        batch_size = len(batch_requests)
        avg_tokens = sum(req.max_tokens for req in batch_requests) / batch_size

        # 基础延迟 + 批大小影响 + token数影响
        base_latency = 0.005  # 5ms基础延迟
        batch_overhead = batch_size * 0.001  # 每个请求1ms开销
        token_latency = avg_tokens * 0.0001  # 每个token 0.1ms

        total_latency = base_latency + batch_overhead + token_latency

        await asyncio.sleep(total_latency)

    def _update_batch_statistics(
        self, batch_requests: List[BatchRequest], batch_latency: float, priority: RequestPriority
    ):
        """更新批处理统计

        Args:
            batch_requests: 批请求列表
            batch_latency: 批延迟(毫秒)
            priority: 请求优先级
        """
        # 更新延迟历史
        self.latency_history[priority].append(batch_latency)

        # 更新全局统计
        self.stats["batches_processed"] += 1

        # 更新平均批大小
        total_batches = self.stats["batches_processed"]
        current_avg = self.stats["avg_batch_size"]
        self.stats["avg_batch_size"] = (current_avg * (total_batches - 1) + len(batch_requests)) / total_batches

        # 更新平均延迟
        current_avg_latency = self.stats["avg_latency_ms"]
        self.stats["avg_latency_ms"] = (current_avg_latency * (total_batches - 1) + batch_latency) / total_batches

        # 更新优先级统计
        priority_stats = self.stats["priority_stats"][priority.name]
        priority_requests = priority_stats["requests"]
        if priority_requests > 0:
            current_priority_avg = priority_stats["avg_latency_ms"]
            priority_stats["avg_latency_ms"] = (
                current_priority_avg * (priority_requests - len(batch_requests)) + batch_latency * len(batch_requests)
            ) / priority_requests

        priority_stats["current_batch_size"] = self.current_batch_sizes[priority]

    async def _adaptive_batch_size_adjustment(self):
        """自适应批大小调整

        白皮书依据: 第二章 2.1 AI三脑架构 - 动态批大小调整
        需求: 8.3 - 动态批大小调整算法
        """
        current_time = time.time()

        # 检查调整间隔
        if current_time - self.last_adjustment_time < self.config.min_adjustment_interval:
            return

        for priority in RequestPriority:
            await self._adjust_priority_batch_size(priority)

        self.last_adjustment_time = current_time

    async def _adjust_priority_batch_size(self, priority: RequestPriority):
        """调整优先级批大小

        Args:
            priority: 请求优先级
        """
        latency_history = self.latency_history[priority]
        if len(latency_history) < 10:  # 需要足够的历史数据
            return

        # 计算平均延迟
        avg_latency = np.mean(list(latency_history))
        target_latency = self._get_default_deadline(priority)

        current_batch_size = self.current_batch_sizes[priority]

        # 延迟过高，减小批大小
        if avg_latency > target_latency * 1.2:
            new_batch_size = max(
                self.config.min_batch_size, int(current_batch_size * (1 - self.config.adjustment_factor))
            )
        # 延迟过低，增大批大小
        elif avg_latency < target_latency * 0.8:
            new_batch_size = min(
                self.config.max_batch_size, int(current_batch_size * (1 + self.config.adjustment_factor))
            )
        else:
            return  # 延迟在目标范围内，不调整

        if new_batch_size != current_batch_size:
            self.current_batch_sizes[priority] = new_batch_size
            self.stats["batch_size_adjustments"] += 1

            logger.info(
                f"[AdaptiveBatchScheduler] Batch size adjusted for {priority.name}: "
                f"{current_batch_size} -> {new_batch_size} "
                f"(avg_latency: {avg_latency:.2f}ms, target: {target_latency:.2f}ms)"
            )

    async def _update_memory_pressure(self):
        """更新内存压力"""
        try:
            # 模拟内存压力检测
            # 实际实现中应该从系统监控获取真实内存使用率
            import psutil  # pylint: disable=import-outside-toplevel

            memory_info = psutil.virtual_memory()
            self.memory_pressure = memory_info.percent / 100.0

            if self.memory_pressure > self.config.memory_pressure_threshold:
                self.stats["memory_pressure_events"] += 1
                logger.warning(f"[AdaptiveBatchScheduler] High memory pressure: {self.memory_pressure:.2%}")

        except ImportError:
            # 如果没有psutil，使用模拟值
            self.memory_pressure = 0.3  # 30%内存使用率
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AdaptiveBatchScheduler] Memory pressure update failed: {e}")
            self.memory_pressure = 0.5  # 默认50%

    async def _cleanup_expired_requests(self):
        """清理过期请求"""
        current_time = time.time()
        expired_count = 0

        for priority in RequestPriority:
            queue = self.request_queues[priority]

            # 从队列前端移除过期请求
            while queue and current_time > queue[0].deadline:
                expired_request = queue.popleft()
                expired_count += 1

                # 执行过期回调
                if expired_request.callback:
                    try:
                        await expired_request.callback(
                            expired_request.request_id, "timeout", {"reason": "Request expired"}
                        )
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.error(f"[AdaptiveBatchScheduler] Expired callback error: {e}")

        if expired_count > 0:
            logger.warning(f"[AdaptiveBatchScheduler] Cleaned up {expired_count} expired requests")

    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        # 计算队列状态
        queue_status = {}
        for priority in RequestPriority:
            queue = self.request_queues[priority]
            queue_status[priority.name] = {
                "queue_size": len(queue),
                "max_queue_size": self._get_max_queue_size(priority),
                "current_batch_size": self.current_batch_sizes[priority],
                "avg_latency_ms": (
                    np.mean(list(self.latency_history[priority])) if self.latency_history[priority] else 0.0
                ),
                "target_latency_ms": self._get_default_deadline(priority),
            }

        return {
            **self.stats,
            "state": self.state,
            "memory_pressure": self.memory_pressure,
            "running": self._running,
            "queue_status": queue_status,
            "config": {
                "soldier_target_latency": self.config.soldier_target_latency,
                "commander_target_latency": self.config.commander_target_latency,
                "scholar_target_latency": self.config.scholar_target_latency,
                "max_batch_size": self.config.max_batch_size,
                "memory_pressure_threshold": self.config.memory_pressure_threshold,
            },
        }

    async def shutdown(self):
        """关闭调度器"""
        logger.info("[AdaptiveBatchScheduler] Shutting down...")

        await self.stop_scheduler()

        # 清空队列
        for queue in self.request_queues.values():
            queue.clear()

        self.state = "SHUTDOWN"
        logger.info("[AdaptiveBatchScheduler] Shutdown completed")


# 测试代码
if __name__ == "__main__":

    async def test_adaptive_batch_scheduler():
        """测试自适应批处理调度器"""
        print("AdaptiveBatchScheduler Test")
        print("=" * 50)

        scheduler = AdaptiveBatchScheduler()
        await scheduler.initialize()

        # 提交测试请求
        for i in range(10):
            source = ["soldier", "commander", "scholar"][i % 3]
            await scheduler.submit_request(
                request_id=f"test_{i}", source_module=source, prompt=f"Test prompt {i}", max_tokens=50
            )

        # 等待处理
        await asyncio.sleep(1.0)

        # 获取统计
        stats = scheduler.get_statistics()
        print(f"Total requests: {stats['total_requests']}")
        print(f"Batches processed: {stats['batches_processed']}")
        print(f"Average batch size: {stats['avg_batch_size']:.2f}")
        print(f"Average latency: {stats['avg_latency_ms']:.2f}ms")

        await scheduler.shutdown()
        print("Test completed!")

    asyncio.run(test_adaptive_batch_scheduler())
