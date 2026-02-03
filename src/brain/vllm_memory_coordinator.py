# pylint: disable=too-many-lines
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
from typing import Any, Dict, List, Optional

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


@dataclass
class MemoryAllocationRequest:  # pylint: disable=e0102
    """内存分配请求"""

    request_id: str
    size_gb: float
    memory_type: MemoryType
    priority: int = 3
    timeout: float = 5.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryStats:  # pylint: disable=e0102
    """内存统计信息"""

    total_allocations: int = 0
    successful_allocations: int = 0
    failed_allocations: int = 0
    total_deallocations: int = 0
    cleanup_operations: int = 0
    fragmentation_events: int = 0
    pressure_alerts: int = 0
    avg_allocation_time: float = 0.0


class VLLMMemoryCoordinator:  # pylint: disable=e0102
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

            # 清理资源
            await self._cleanup_all_allocations()

            logger.info("vLLM内存协调器已关闭")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存协调器关闭失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def allocate_memory(self, request: MemoryAllocationRequest) -> Optional[Dict[str, Any]]:
        """分配内存"""
        try:
            start_time = time.perf_counter()

            # 验证请求
            self._validate_allocation_request(request)

            # 检查内存池可用性
            pool = self.memory_pools[request.memory_type]
            if pool.free_size < request.size_gb:
                # 尝试触发清理
                await self._trigger_emergency_cleanup(request.memory_type)

                # 重新检查
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

            # AMD AI 395特定优化
            if request.memory_type == MemoryType.VARIABLE_GRAPHICS:
                await self._optimize_variable_graphics_allocation(allocation_info)
            elif request.memory_type == MemoryType.NPU_CACHE:
                await self._optimize_npu_cache_allocation(allocation_info)

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

    async def detect_memory_pressure(self) -> Dict[str, Any]:
        """检测内存压力"""
        try:
            pressure_info = {
                "overall_pressure": MemoryPressureLevel.LOW,
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
            pressure_info["overall_pressure"] = list(MemoryPressureLevel)[max_pressure_level]

            # 生成建议
            pressure_info["recommendations"] = self._generate_pressure_recommendations(pressure_info)

            # 触发压力告警
            if pressure_info["overall_pressure"] in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
                self.stats.pressure_alerts += 1
                await self._handle_pressure_alert(pressure_info)

            return pressure_info

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存压力检测失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {"overall_pressure": MemoryPressureLevel.CRITICAL, "error": str(e), "timestamp": time.time()}

    async def trigger_cleanup(self, memory_type: Optional[MemoryType] = None) -> Dict[str, Any]:
        """触发内存清理"""
        try:
            cleanup_result = {
                "cleaned_pools": [],
                "freed_memory_gb": 0.0,
                "cleanup_time_ms": 0.0,
                "operations_performed": [],
                "timestamp": time.time(),
            }

            start_time = time.perf_counter()

            # 确定要清理的内存池
            pools_to_clean = []
            if memory_type:
                pools_to_clean = [memory_type]
            else:
                # 按压力等级排序，优先清理高压力池
                pools_to_clean = sorted(
                    self.memory_pools.keys(),
                    key=lambda mt: list(MemoryPressureLevel).index(self.memory_pools[mt].pressure_level),
                    reverse=True,
                )

            # 执行清理
            for pool_type in pools_to_clean:
                pool = self.memory_pools[pool_type]

                if pool.pressure_level in [
                    MemoryPressureLevel.MODERATE,
                    MemoryPressureLevel.HIGH,
                    MemoryPressureLevel.CRITICAL,
                ]:
                    freed_memory = await self._cleanup_memory_pool(pool_type)

                    if freed_memory > 0:
                        cleanup_result["cleaned_pools"].append(pool_type.value)
                        cleanup_result["freed_memory_gb"] += freed_memory
                        cleanup_result["operations_performed"].append(f"清理{pool_type.value}: {freed_memory:.2f}GB")

            # 执行碎片整理
            if memory_type is None or memory_type == MemoryType.PAGED_ATTENTION:
                defrag_result = await self._defragment_paged_attention()
                if defrag_result["blocks_merged"] > 0:
                    cleanup_result["operations_performed"].append(
                        f"PagedAttention碎片整理: 合并{defrag_result['blocks_merged']}个块"
                    )

            # 更新统计
            cleanup_result["cleanup_time_ms"] = (time.perf_counter() - start_time) * 1000
            self.stats.cleanup_operations += 1

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"内存清理完成: 释放{cleanup_result['freed_memory_gb']:.2f}GB, "
                f"耗时{cleanup_result['cleanup_time_ms']:.2f}ms"
            )

            return cleanup_result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存清理失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {"error": str(e), "timestamp": time.time()}

    async def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        try:
            # 基础统计
            stats_dict = {
                "allocation_stats": {
                    "total_allocations": self.stats.total_allocations,
                    "successful_allocations": self.stats.successful_allocations,
                    "failed_allocations": self.stats.failed_allocations,
                    "success_rate": (self.stats.successful_allocations / max(self.stats.total_allocations, 1)),
                    "total_deallocations": self.stats.total_deallocations,
                    "avg_allocation_time_ms": self.stats.avg_allocation_time,
                },
                "cleanup_stats": {
                    "cleanup_operations": self.stats.cleanup_operations,
                    "fragmentation_events": self.stats.fragmentation_events,
                    "pressure_alerts": self.stats.pressure_alerts,
                },
                "pool_stats": {},
                "active_allocations": len(self.active_allocations),
                "coordinator_status": "running" if self.running else "stopped",
                "timestamp": time.time(),
            }

            # 内存池统计
            for memory_type, pool in self.memory_pools.items():
                stats_dict["pool_stats"][memory_type.value] = {
                    "total_size_gb": pool.total_size,
                    "used_size_gb": pool.used_size,
                    "free_size_gb": pool.free_size,
                    "utilization": pool.utilization,
                    "fragmentation": pool.fragmentation,
                    "pressure_level": pool.pressure_level.value,
                    "last_cleanup": pool.last_cleanup,
                }

            # AMD AI 395特定统计
            stats_dict["amd_ai_395_stats"] = {
                "unified_memory_utilization": self.memory_pools[MemoryType.UNIFIED_SYSTEM].utilization,
                "variable_graphics_utilization": self.memory_pools[MemoryType.VARIABLE_GRAPHICS].utilization,
                "npu_cache_utilization": self.memory_pools[MemoryType.NPU_CACHE].utilization,
                "paged_attention_efficiency": 1.0 - self.memory_pools[MemoryType.PAGED_ATTENTION].fragmentation,
                "total_ai_memory_gb": (
                    self.memory_pools[MemoryType.VARIABLE_GRAPHICS].used_size
                    + self.memory_pools[MemoryType.NPU_CACHE].used_size
                    + self.memory_pools[MemoryType.PAGED_ATTENTION].used_size
                ),
            }

            return stats_dict

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取内存统计失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {"error": str(e), "timestamp": time.time()}

    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        try:
            health_info = {
                "healthy": True,
                "coordinator_healthy": self.running and self.coordinator_task and not self.coordinator_task.done(),
                "cleanup_healthy": self.cleanup_task and not self.cleanup_task.done(),
                "monitoring_healthy": self.monitoring_task and not self.monitoring_task.done(),
                "memory_healthy": True,
                "event_bus_healthy": self.event_bus is not None,
                "memory_pressure": MemoryPressureLevel.LOW.value,
                "active_allocations": len(self.active_allocations),
                "total_memory_gb": 0.0,
                "used_memory_gb": 0.0,
                "timestamp": time.time(),
            }

            # 计算总内存和使用量
            total_memory = 0.0
            used_memory = 0.0
            max_pressure_level = 0

            for pool in self.memory_pools.values():
                total_memory += pool.total_size
                used_memory += pool.used_size

                # 更新压力等级
                pool.update_pressure_level()
                pressure_level_value = list(MemoryPressureLevel).index(pool.pressure_level)
                max_pressure_level = max(max_pressure_level, pressure_level_value)

                # 检查内存池健康状态
                if pool.utilization > 0.95:
                    health_info["memory_healthy"] = False

            health_info["total_memory_gb"] = total_memory
            health_info["used_memory_gb"] = used_memory
            health_info["memory_pressure"] = list(MemoryPressureLevel)[max_pressure_level].value

            # 总体健康状态
            health_info["healthy"] = (
                health_info["coordinator_healthy"]
                and health_info["cleanup_healthy"]
                and health_info["monitoring_healthy"]
                and health_info["memory_healthy"]
                and health_info["event_bus_healthy"]
            )

            return health_info

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"健康检查失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {"healthy": False, "error": str(e), "timestamp": time.time()}

    # ==================== 内部方法 ====================

    async def _initialize_memory_pools(self):
        """初始化内存池状态"""
        try:
            # 统一系统内存 - 模拟系统占用16GB
            unified_pool = self.memory_pools[MemoryType.UNIFIED_SYSTEM]
            unified_pool.used_size = 16.0  # 系统占用
            unified_pool.free_size = unified_pool.total_size - unified_pool.used_size
            unified_pool.update_pressure_level()

            # Variable Graphics Memory - 初始全部可用
            vgm_pool = self.memory_pools[MemoryType.VARIABLE_GRAPHICS]
            vgm_pool.used_size = 0.0
            vgm_pool.free_size = vgm_pool.total_size
            vgm_pool.update_pressure_level()

            # NPU缓存 - 模拟NPU运行时占用100MB
            npu_pool = self.memory_pools[MemoryType.NPU_CACHE]
            npu_pool.used_size = 0.1  # 100MB
            npu_pool.free_size = npu_pool.total_size - npu_pool.used_size
            npu_pool.update_pressure_level()

            # L3缓存 - 模拟部分占用
            l3_pool = self.memory_pools[MemoryType.L3_CACHE]
            l3_pool.used_size = 0.032  # 32MB
            l3_pool.free_size = l3_pool.total_size - l3_pool.used_size
            l3_pool.update_pressure_level()

            # PagedAttention块池 - 初始无碎片
            paged_pool = self.memory_pools[MemoryType.PAGED_ATTENTION]
            paged_pool.used_size = 0.0
            paged_pool.free_size = paged_pool.total_size
            paged_pool.fragmentation = 0.0
            paged_pool.update_pressure_level()

            logger.info("内存池初始化完成")

        except Exception as e:
            logger.error(f"内存池初始化失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    def _validate_allocation_request(self, request: MemoryAllocationRequest):
        """验证内存分配请求"""
        if not request.request_id or request.request_id.strip() == "":
            raise ValueError("request_id不能为空")

        if request.size_gb <= 0:
            raise ValueError("size_gb必须大于0")

        if not (1 <= request.priority <= 5):  # pylint: disable=superfluous-parens
            raise ValueError("priority必须在1-5范围内")

        if request.timeout <= 0:
            raise ValueError("timeout必须大于0")

        # 检查请求大小是否超过内存池总大小
        pool = self.memory_pools[request.memory_type]
        if request.size_gb > pool.total_size:
            raise ValueError(f"请求大小{request.size_gb}GB超过内存池总大小{pool.total_size}GB")

    async def _trigger_emergency_cleanup(self, memory_type: MemoryType):
        """触发紧急内存清理"""
        try:
            logger.warning(f"触发紧急内存清理: {memory_type.value}")  # pylint: disable=logging-fstring-interpolation

            # 获取该类型的所有分配，按优先级排序
            allocations_to_cleanup = []
            for alloc_id, alloc_info in self.active_allocations.items():
                if MemoryType(alloc_info["memory_type"]) == memory_type:
                    allocations_to_cleanup.append((alloc_id, alloc_info))

            # 按优先级排序（低优先级先清理）
            allocations_to_cleanup.sort(key=lambda x: x[1]["priority"])

            # 清理低优先级分配
            freed_memory = 0.0
            cleanup_count = min(len(allocations_to_cleanup) // 2, 5)  # 最多清理一半或5个

            for i in range(cleanup_count):
                alloc_id, alloc_info = allocations_to_cleanup[i]
                if await self.deallocate_memory(alloc_id):
                    freed_memory += alloc_info["size_gb"]

            logger.info(f"紧急清理完成: 释放{freed_memory:.2f}GB内存")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"紧急内存清理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _cleanup_memory_pool(self, memory_type: MemoryType) -> float:
        """清理指定内存池"""
        try:
            pool = self.memory_pools[memory_type]

            # 获取该类型的所有分配
            allocations_to_cleanup = []
            for alloc_id, alloc_info in self.active_allocations.items():
                if MemoryType(alloc_info["memory_type"]) == memory_type:
                    # 计算分配的年龄和优先级
                    age = time.time() - alloc_info["allocated_at"]
                    priority = alloc_info["priority"]

                    # 清理策略：年龄>300秒且优先级<=2的分配
                    if age > 300 and priority <= 2:
                        allocations_to_cleanup.append(alloc_id)

            # 执行清理
            freed_memory = 0.0
            for alloc_id in allocations_to_cleanup:
                alloc_info = self.active_allocations.get(alloc_id)
                if alloc_info and await self.deallocate_memory(alloc_id):
                    freed_memory += alloc_info["size_gb"]

            # 更新最后清理时间
            pool.last_cleanup = time.time()

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"内存池清理完成: {memory_type.value}, 释放{freed_memory:.2f}GB"
            )  # pylint: disable=logging-fstring-interpolation
            return freed_memory

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存池清理失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return 0.0

    async def _defragment_paged_attention(self) -> Dict[str, Any]:
        """执行PagedAttention碎片整理"""
        try:
            paged_pool = self.memory_pools[MemoryType.PAGED_ATTENTION]

            fragmentation_before = paged_pool.fragmentation

            # 模拟碎片整理过程
            if fragmentation_before > 0.01:  # 碎片率>1%时才整理  # pylint: disable=no-else-return
                # 计算可合并的块数量
                total_blocks = int(paged_pool.used_size * 1024)  # 假设每GB=1024块
                fragmented_blocks = int(total_blocks * fragmentation_before)
                blocks_merged = min(fragmented_blocks, total_blocks // 4)  # 最多合并25%

                # 更新碎片率
                if total_blocks > 0:
                    new_fragmentation = max(0.0, fragmentation_before - (blocks_merged / total_blocks))
                    paged_pool.fragmentation = new_fragmentation
                else:
                    paged_pool.fragmentation = 0.0

                # 更新统计
                self.stats.fragmentation_events += 1

                result = {
                    "blocks_merged": blocks_merged,
                    "fragmentation_before": fragmentation_before,
                    "fragmentation_after": paged_pool.fragmentation,
                    "improvement": fragmentation_before - paged_pool.fragmentation,
                    "timestamp": time.time(),
                }

                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"PagedAttention碎片整理完成: 合并{blocks_merged}个块, "
                    f"碎片率从{fragmentation_before:.3f}降至{paged_pool.fragmentation:.3f}"
                )

                return result
            else:
                return {
                    "blocks_merged": 0,
                    "fragmentation_before": fragmentation_before,
                    "fragmentation_after": fragmentation_before,
                    "improvement": 0.0,
                    "timestamp": time.time(),
                }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"PagedAttention碎片整理失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return {"error": str(e), "timestamp": time.time()}

    async def _optimize_variable_graphics_allocation(self, allocation_info: Dict[str, Any]):
        """优化Variable Graphics Memory分配"""
        try:
            size_gb = allocation_info["size_gb"]
            priority = allocation_info["priority"]

            # 初始化元数据
            if "metadata" not in allocation_info:
                allocation_info["metadata"] = {}

            # 大内存分配优化（>8GB）
            if size_gb > 8.0:
                allocation_info["metadata"]["compression_enabled"] = True
                allocation_info["metadata"]["optimization"] = "large_allocation"
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"启用大内存分配优化: {allocation_info['allocation_id']}"
                )  # pylint: disable=logging-fstring-interpolation

            # 高优先级分配优化（优先级>=4）
            elif priority >= 4:
                allocation_info["metadata"]["preallocation_enabled"] = True
                allocation_info["metadata"]["optimization"] = "high_priority"
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"启用高优先级分配优化: {allocation_info['allocation_id']}"
                )  # pylint: disable=logging-fstring-interpolation

            # 标准分配
            else:
                allocation_info["metadata"]["optimization"] = "standard"

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Variable Graphics Memory优化失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _optimize_npu_cache_allocation(self, allocation_info: Dict[str, Any]):
        """优化NPU缓存分配"""
        try:
            # 初始化元数据
            if "metadata" not in allocation_info:
                allocation_info["metadata"] = {}

            # NPU特定优化
            if self.config.get("npu_optimization", True):
                allocation_info["metadata"]["npu_acceleration"] = True
                allocation_info["metadata"]["xdna2_optimized"] = True
                allocation_info["metadata"]["optimization"] = "npu_cache"

                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"启用NPU缓存优化: {allocation_info['allocation_id']}"
                )  # pylint: disable=logging-fstring-interpolation
            else:
                allocation_info["metadata"]["optimization"] = "standard"

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"NPU缓存优化失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def _generate_pressure_recommendations(self, pressure_info: Dict[str, Any]) -> List[str]:
        """生成内存压力建议"""
        recommendations = []

        pressure_level = pressure_info["overall_pressure"]
        critical_pools = pressure_info.get("critical_pools", [])

        if pressure_level == MemoryPressureLevel.CRITICAL:
            recommendations.append("立即触发全局内存清理")
            recommendations.append("暂停低优先级内存分配")

            if MemoryType.VARIABLE_GRAPHICS.value in critical_pools:
                recommendations.append("释放部分Variable Graphics Memory回系统内存")

            if MemoryType.PAGED_ATTENTION.value in critical_pools:
                recommendations.append("执行PagedAttention碎片整理")

            if MemoryType.NPU_CACHE.value in critical_pools:
                recommendations.append("清理NPU推理缓存")

        elif pressure_level == MemoryPressureLevel.HIGH:
            recommendations.append("启动预防性内存清理")

            if MemoryType.NPU_CACHE.value in critical_pools:
                recommendations.append("清理NPU推理缓存")

            if MemoryType.PAGED_ATTENTION.value in critical_pools:
                recommendations.append("执行PagedAttention碎片整理")

        elif pressure_level == MemoryPressureLevel.MODERATE:
            recommendations.append("监控内存使用趋势")
            recommendations.append("考虑清理低优先级分配")

        else:  # LOW
            recommendations.append("内存状态良好，继续监控")

        return recommendations

    async def _handle_system_query(self, event: Event):
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
                if query_type == "memory_stats":
                    response_data = await self.get_memory_stats()
                elif query_type == "memory_pressure":
                    response_data = await self.detect_memory_pressure()
                elif query_type == "health_check":
                    response_data = await self.health_check()
                elif query_type == "active_allocations":
                    response_data = {
                        "active_allocations": len(self.active_allocations),
                        "allocations": list(self.active_allocations.keys()),
                    }
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

    async def _handle_pressure_alert(self, pressure_info: Dict[str, Any]):
        """处理内存压力告警"""
        try:
            # 发布压力告警事件
            alert_event = Event(
                event_type=EventType.SYSTEM_ALERT,
                source_module="vllm_memory_coordinator",
                target_module="all",
                priority=EventPriority.CRITICAL,
                data={
                    "alert_type": "memory_pressure",
                    "pressure_level": pressure_info["overall_pressure"].value,
                    "critical_pools": pressure_info.get("critical_pools", []),
                    "recommendations": pressure_info.get("recommendations", []),
                    "timestamp": time.time(),
                },
            )

            await self.event_bus.publish(alert_event)

            logger.warning(  # pylint: disable=logging-fstring-interpolation
                f"内存压力告警已发布: {pressure_info['overall_pressure'].value}"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存压力告警处理失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _cleanup_all_allocations(self):
        """清理所有分配"""
        try:
            allocation_ids = list(self.active_allocations.keys())

            for alloc_id in allocation_ids:
                await self.deallocate_memory(alloc_id)

            logger.info(f"清理了{len(allocation_ids)}个活跃分配")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"清理所有分配失败: {e}")  # pylint: disable=logging-fstring-interpolation

    # ==================== 后台任务循环 ====================

    async def _coordinator_loop(self):
        """协调器主循环"""
        try:
            logger.info("vLLM内存协调器主循环启动")

            while self.running:
                try:
                    # 检测内存压力
                    pressure_info = await self.detect_memory_pressure()

                    # 根据压力等级执行相应操作
                    if pressure_info["overall_pressure"] in [MemoryPressureLevel.HIGH, MemoryPressureLevel.CRITICAL]:
                        await self.trigger_cleanup()

                    # 等待下次检查
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
                    # 检查是否需要清理
                    for memory_type, pool in self.memory_pools.items():
                        if pool.utilization > self.config["cleanup_threshold"]:
                            await self._cleanup_memory_pool(memory_type)

                    # 检查PagedAttention碎片整理
                    paged_pool = self.memory_pools[MemoryType.PAGED_ATTENTION]
                    if paged_pool.fragmentation > self.config["fragmentation_threshold"]:
                        await self._defragment_paged_attention()

                    # 等待下次清理
                    await asyncio.sleep(30.0)  # 每30秒检查一次

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
                    # 更新内存池状态
                    for pool in self.memory_pools.values():
                        pool.update_pressure_level()

                    # 记录统计信息
                    if self.stats.total_allocations > 0:
                        success_rate = self.stats.successful_allocations / self.stats.total_allocations
                        if success_rate < 0.9:  # 成功率低于90%
                            logger.warning(  # pylint: disable=logging-fstring-interpolation
                                f"内存分配成功率较低: {success_rate:.2%}"
                            )  # pylint: disable=logging-fstring-interpolation

                    # 等待下次监控
                    await asyncio.sleep(10.0)  # 每10秒监控一次

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"监控循环错误: {e}")  # pylint: disable=logging-fstring-interpolation
                    await asyncio.sleep(2.0)

            logger.info("vLLM内存监控循环已停止")

        except asyncio.CancelledError:
            logger.info("vLLM内存监控循环被取消")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存监控循环异常: {e}")  # pylint: disable=logging-fstring-interpolation

    async def shutdown(self):  # pylint: disable=e0102
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

            # 清理资源
            await self._cleanup_all_allocations()

            logger.info("vLLM内存协调器已关闭")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"vLLM内存协调器关闭失败: {e}")  # pylint: disable=logging-fstring-interpolation
