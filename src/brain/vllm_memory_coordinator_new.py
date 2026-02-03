"""
vLLM内存协调器 - AMD AI 395优化版

白皮书依据: 第二章 2.8 统一记忆系统 - vLLM内存协同管理
版本: v1.6.0
作者: MIA Team
日期: 2026-01-19
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from src.infra.event_bus import Event, EventPriority, EventType, get_event_bus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryPressureLevel(Enum):
    """内存压力等级"""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryType(Enum):
    """内存类型 - AMD AI 395架构"""

    UNIFIED_SYSTEM = "unified_system"
    VARIABLE_GRAPHICS = "variable_graphics"
    NPU_CACHE = "npu_cache"
    L3_CACHE = "l3_cache"
    PAGED_ATTENTION = "paged_attention"


@dataclass
class MemoryPool:
    """内存池状态"""

    pool_type: MemoryType
    total_size: float
    used_size: float = 0.0
    free_size: float = 0.0
    fragmentation: float = 0.0
    pressure_level: MemoryPressureLevel = MemoryPressureLevel.LOW
    last_cleanup: float = field(default_factory=time.time)

    def __post_init__(self):
        self.free_size = self.total_size - self.used_size

    @property
    def utilization(self) -> float:
        return self.used_size / self.total_size if self.total_size > 0 else 0.0

    def update_pressure_level(self):
        utilization = self.utilization
        if utilization < 0.6:
            self.pressure_level = MemoryPressureLevel.LOW
        elif utilization < 0.8:
            self.pressure_level = MemoryPressureLevel.MODERATE
        elif utilization < 0.95:
            self.pressure_level = MemoryPressureLevel.HIGH
        else:
            self.pressure_level = MemoryPressureLevel.CRITICAL


@dataclass
class MemoryAllocationRequest:
    """内存分配请求"""

    request_id: str
    size_gb: float
    memory_type: MemoryType
    priority: int = 3
    timeout: float = 5.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryStats:
    """内存统计信息"""

    total_allocations: int = 0
    successful_allocations: int = 0
    failed_allocations: int = 0
    total_deallocations: int = 0
    cleanup_operations: int = 0
    fragmentation_events: int = 0
    pressure_alerts: int = 0
    avg_allocation_time: float = 0.0


class VLLMMemoryCoordinator:
    """vLLM内存协调器 - AMD AI 395优化版"""

    def __init__(self):
        """初始化vLLM内存协调器"""
        # AMD AI 395内存池配置
        self.memory_pools = {
            MemoryType.UNIFIED_SYSTEM: MemoryPool(
                pool_type=MemoryType.UNIFIED_SYSTEM, total_size=128.0  # 128GB统一内存
            ),
            MemoryType.VARIABLE_GRAPHICS: MemoryPool(
                pool_type=MemoryType.VARIABLE_GRAPHICS, total_size=96.0  # 最多96GB可作为VRAM
            ),
            MemoryType.NPU_CACHE: MemoryPool(pool_type=MemoryType.NPU_CACHE, total_size=2.0),  # XDNA2 NPU缓存(估算)
            MemoryType.L3_CACHE: MemoryPool(pool_type=MemoryType.L3_CACHE, total_size=0.064),  # 64MB L3缓存
            MemoryType.PAGED_ATTENTION: MemoryPool(
                pool_type=MemoryType.PAGED_ATTENTION, total_size=32.0  # PagedAttention块池
            ),
        }

        # 内存分配跟踪
        self.active_allocations = {}
        self.stats = MemoryStats()

        # 协调器状态
        self.running = False
        self.coordinator_task = None
        self.cleanup_task = None
        self.monitoring_task = None

        # 事件总线
        self.event_bus = None
        self.pending_queries = {}

        # 配置参数
        self.config = {
            "pressure_check_interval": 0.1,
            "cleanup_threshold": 0.8,
            "fragmentation_threshold": 0.05,
            "allocation_timeout": 5.0,
            "npu_optimization": True,
            "variable_graphics_ratio": 0.75,
        }

        logger.info("VLLMMemoryCoordinator初始化完成 - AMD AI 395优化版")

    async def initialize(self):
        """初始化内存协调器和事件总线连接"""
        try:
            logger.info("开始初始化vLLM内存协调器...")

            # 获取事件总线
            self.event_bus = await get_event_bus()

            # 订阅系统查询事件
            await self.event_bus.subscribe(
                EventType.SYSTEM_QUERY, self._handle_system_query, "vllm_memory_coordinator_query_handler"
            )

            # 初始化内存池状态
            await self._initialize_memory_pools()

            # 启动协调器任务
            self.running = True
            self.coordinator_task = asyncio.create_task(self._coordinator_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())

            logger.info("vLLM内存协调器初始化成功")

        except Exception as e:
            logger.error(f"vLLM内存协调器初始化失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise RuntimeError(f"内存协调器初始化失败: {e}")  # pylint: disable=w0707

    async def shutdown(self):
        """关闭内存协调器"""
        try:
            self.running = False

            # 取消所有任务
            tasks = [self.coordinator_task, self.cleanup_task, self.monitoring_task]
            for task in tasks:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            logger.info("vLLM内存协调器已关闭")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存协调器关闭失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def detect_memory_pressure(self) -> Dict[str, Any]:
        """检测内存压力"""
        try:
            pressure_info = {
                "overall_pressure": MemoryPressureLevel.LOW.value,
                "pool_pressures": {},
                "critical_pools": [],
                "recommendations": [],
                "timestamp": time.time(),
            }

            max_pressure_level = 0

            for memory_type, pool in self.memory_pools.items():
                pool.update_pressure_level()

                pressure_info["pool_pressures"][memory_type.value] = {
                    "level": pool.pressure_level.value,
                    "utilization": pool.utilization,
                    "fragmentation": pool.fragmentation,
                    "free_size_gb": pool.free_size,
                }

                # 记录关键内存池
                if pool.pressure_level in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
                    pressure_info["critical_pools"].append(memory_type.value)

                # 更新整体压力等级
                pressure_level_value = list(MemoryPressureLevel).index(pool.pressure_level)
                max_pressure_level = max(max_pressure_level, pressure_level_value)

            # 设置整体压力等级
            pressure_info["overall_pressure"] = list(MemoryPressureLevel)[max_pressure_level].value

            return pressure_info

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存压力检测失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {"overall_pressure": MemoryPressureLevel.CRITICAL.value, "error": str(e), "timestamp": time.time()}

    async def allocate_memory(self, request: MemoryAllocationRequest) -> Optional[Dict[str, Any]]:
        """分配内存"""
        try:
            start_time = time.perf_counter()

            # 检查内存池可用性
            pool = self.memory_pools[request.memory_type]
            if pool.free_size < request.size_gb:
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"内存不足: 请求{request.size_gb}GB, 可用{pool.free_size}GB"
                )  # pylint: disable=logging-fstring-interpolation
                self.stats.failed_allocations += 1
                return None

            # 执行分配
            allocation_id = f"{request.request_id}_{int(time.time() * 1000000)}"
            allocation_info = {
                "allocation_id": allocation_id,
                "request_id": request.request_id,
                "size_gb": request.size_gb,
                "memory_type": request.memory_type.value,
                "allocated_at": time.time(),
                "priority": request.priority,
                "metadata": request.metadata,
            }

            # 更新内存池状态
            pool.used_size += request.size_gb
            pool.free_size -= request.size_gb
            pool.update_pressure_level()

            # 记录分配
            self.active_allocations[allocation_id] = allocation_info

            # 更新统计
            elapsed = (time.perf_counter() - start_time) * 1000
            self.stats.total_allocations += 1
            self.stats.successful_allocations += 1
            self.stats.avg_allocation_time = (
                self.stats.avg_allocation_time * (self.stats.total_allocations - 1) + elapsed
            ) / self.stats.total_allocations

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"内存分配成功: {allocation_id}, 大小: {request.size_gb}GB, 延迟: {elapsed:.2f}ms"
            )  # pylint: disable=logging-fstring-interpolation

            return allocation_info

        except Exception as e:
            logger.error(f"内存分配失败: {e}")  # pylint: disable=logging-fstring-interpolation
            self.stats.failed_allocations += 1
            raise

    async def deallocate_memory(self, allocation_id: str) -> bool:
        """释放内存"""
        try:
            if allocation_id not in self.active_allocations:
                logger.warning(f"分配ID不存在: {allocation_id}")  # pylint: disable=logging-fstring-interpolation
                return False

            allocation_info = self.active_allocations.pop(allocation_id)

            # 更新内存池状态
            memory_type = MemoryType(allocation_info["memory_type"])
            pool = self.memory_pools[memory_type]
            pool.used_size -= allocation_info["size_gb"]
            pool.free_size += allocation_info["size_gb"]
            pool.update_pressure_level()

            # 更新统计
            self.stats.total_deallocations += 1

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"内存释放成功: {allocation_id}, 大小: {allocation_info['size_gb']}GB"
            )  # pylint: disable=logging-fstring-interpolation

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存释放失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return False

    async def _initialize_memory_pools(self):
        """初始化内存池状态"""
        try:
            # 统一系统内存 - 模拟系统占用16GB
            unified_pool = self.memory_pools[MemoryType.UNIFIED_SYSTEM]
            unified_pool.used_size = 16.0  # 系统占用
            unified_pool.free_size = unified_pool.total_size - unified_pool.used_size
            unified_pool.update_pressure_level()

            logger.info("内存池初始化完成")

        except Exception as e:
            logger.error(f"内存池初始化失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    async def _handle_system_query(self, event):
        """处理系统查询事件"""
        try:
            query_type = event.data.get("query_type")
            correlation_id = event.data.get("correlation_id")

            if not correlation_id:
                logger.warning("系统查询事件缺少correlation_id")
                return

            response_data = {}
            status = "success"

            try:
                if query_type == "memory_pressure":
                    response_data = await self.detect_memory_pressure()
                else:
                    status = "error"
                    response_data = {"error": f"不支持的查询类型: {query_type}"}

            except Exception as e:  # pylint: disable=broad-exception-caught
                status = "error"
                response_data = {"error": str(e)}

            # 发布响应事件
            response_event = Event(
                event_type=EventType.SYSTEM_RESPONSE,
                source_module="vllm_memory_coordinator",
                target_module=event.source_module,
                priority=EventPriority.HIGH,
                data={
                    "correlation_id": correlation_id,
                    "status": status,
                    "response_data": response_data,
                    "timestamp": time.time(),
                },
            )

            await self.event_bus.publish(response_event)

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"系统查询响应完成: {correlation_id}, 类型: {query_type}"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"系统查询处理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _coordinator_loop(self):
        """协调器主循环"""
        try:
            logger.info("vLLM内存协调器主循环启动")

            while self.running:
                try:
                    await asyncio.sleep(self.config["pressure_check_interval"])
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"协调器主循环错误: {e}")  # pylint: disable=logging-fstring-interpolation
                    await asyncio.sleep(1.0)

            logger.info("vLLM内存协调器主循环已停止")

        except asyncio.CancelledError:
            logger.info("vLLM内存协调器主循环被取消")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存协调器主循环异常: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _cleanup_loop(self):
        """清理任务循环"""
        try:
            logger.info("vLLM内存清理循环启动")

            while self.running:
                try:
                    await asyncio.sleep(30.0)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"清理循环错误: {e}")  # pylint: disable=logging-fstring-interpolation
                    await asyncio.sleep(5.0)

            logger.info("vLLM内存清理循环已停止")

        except asyncio.CancelledError:
            logger.info("vLLM内存清理循环被取消")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存清理循环异常: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _monitoring_loop(self):
        """监控任务循环"""
        try:
            logger.info("vLLM内存监控循环启动")

            while self.running:
                try:
                    await asyncio.sleep(10.0)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"监控循环错误: {e}")  # pylint: disable=logging-fstring-interpolation
                    await asyncio.sleep(2.0)

            logger.info("vLLM内存监控循环已停止")

        except asyncio.CancelledError:
            logger.info("vLLM内存监控循环被取消")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存监控循环异常: {e}")  # pylint: disable=logging-fstring-interpolation
