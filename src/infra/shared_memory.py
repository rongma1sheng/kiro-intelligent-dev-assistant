"""
共享内存缓冲区 (Shared Memory Buffer)

白皮书依据: 第一章 1.5.1 战备态任务调度
- 环形缓冲区
- 高性能数据共享
- 进程间通信

功能:
- 提供高性能环形缓冲区
- 支持多生产者多消费者
- 低延迟数据传输
"""

import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from loguru import logger

T = TypeVar("T")


class BufferStatus(Enum):
    """缓冲区状态"""

    EMPTY = "空"
    PARTIAL = "部分填充"
    FULL = "满"
    OVERFLOW = "溢出"


@dataclass
class BufferStats:
    """缓冲区统计

    Attributes:
        total_writes: 总写入次数
        total_reads: 总读取次数
        overflow_count: 溢出次数
        current_size: 当前大小
        max_size: 最大容量
        avg_latency_us: 平均延迟(微秒)
    """

    total_writes: int = 0
    total_reads: int = 0
    overflow_count: int = 0
    current_size: int = 0
    max_size: int = 0
    avg_latency_us: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_writes": self.total_writes,
            "total_reads": self.total_reads,
            "overflow_count": self.overflow_count,
            "current_size": self.current_size,
            "max_size": self.max_size,
            "avg_latency_us": self.avg_latency_us,
        }


class RingBuffer(Generic[T]):
    """环形缓冲区

    白皮书依据: 第一章 1.5.1 环形缓冲区

    高性能环形缓冲区，支持SPSC(单生产者单消费者)模式。

    Attributes:
        capacity: 缓冲区容量
        overwrite: 满时是否覆盖旧数据

    Example:
        >>> buffer = RingBuffer[TickData](capacity=10000)
        >>> buffer.write(tick)
        >>> data = buffer.read()
    """

    def __init__(self, capacity: int = 10000, overwrite: bool = True):
        """初始化环形缓冲区

        Args:
            capacity: 缓冲区容量
            overwrite: 满时是否覆盖旧数据
        """
        if capacity <= 0:
            raise ValueError(f"容量必须大于0，当前: {capacity}")

        self.capacity = capacity
        self.overwrite = overwrite

        self._buffer: deque = deque(maxlen=capacity if overwrite else None)
        self._lock = threading.RLock()

        # 统计信息
        self._stats = BufferStats(max_size=capacity)
        self._latencies: deque = deque(maxlen=1000)

        logger.debug(f"环形缓冲区初始化: 容量={capacity}, 覆盖={overwrite}")

    def write(self, data: T) -> bool:
        """写入数据

        Args:
            data: 要写入的数据

        Returns:
            是否成功写入
        """
        start_time = time.perf_counter()

        with self._lock:
            if not self.overwrite and len(self._buffer) >= self.capacity:
                self._stats.overflow_count += 1
                return False

            self._buffer.append(data)
            self._stats.total_writes += 1
            self._stats.current_size = len(self._buffer)

        # 记录延迟
        latency_us = (time.perf_counter() - start_time) * 1_000_000
        self._latencies.append(latency_us)
        self._update_avg_latency()

        return True

    def write_batch(self, data_list: List[T]) -> int:
        """批量写入数据

        Args:
            data_list: 数据列表

        Returns:
            成功写入的数量
        """
        written = 0

        with self._lock:
            for data in data_list:
                if self.write(data):
                    written += 1
                elif not self.overwrite:
                    break

        return written

    def read(self) -> Optional[T]:
        """读取数据

        Returns:
            读取的数据，缓冲区为空返回None
        """
        with self._lock:
            if not self._buffer:
                return None

            data = self._buffer.popleft()
            self._stats.total_reads += 1
            self._stats.current_size = len(self._buffer)

            return data

    def read_batch(self, count: int) -> List[T]:
        """批量读取数据

        Args:
            count: 读取数量

        Returns:
            数据列表
        """
        result = []

        with self._lock:
            for _ in range(min(count, len(self._buffer))):
                data = self._buffer.popleft()
                result.append(data)
                self._stats.total_reads += 1

            self._stats.current_size = len(self._buffer)

        return result

    def peek(self) -> Optional[T]:
        """查看数据但不移除

        Returns:
            缓冲区头部数据
        """
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[0]

    def peek_all(self) -> List[T]:
        """查看所有数据但不移除

        Returns:
            所有数据的副本
        """
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        """清空缓冲区"""
        with self._lock:
            self._buffer.clear()
            self._stats.current_size = 0

    def _update_avg_latency(self) -> None:
        """更新平均延迟"""
        if self._latencies:
            self._stats.avg_latency_us = sum(self._latencies) / len(self._latencies)

    def size(self) -> int:
        """获取当前大小

        Returns:
            当前数据量
        """
        with self._lock:
            return len(self._buffer)

    def is_empty(self) -> bool:
        """检查是否为空

        Returns:
            是否为空
        """
        with self._lock:
            return len(self._buffer) == 0

    def is_full(self) -> bool:
        """检查是否已满

        Returns:
            是否已满
        """
        with self._lock:
            return len(self._buffer) >= self.capacity

    def get_status(self) -> BufferStatus:
        """获取缓冲区状态

        Returns:
            缓冲区状态
        """
        with self._lock:
            size = len(self._buffer)

            if size == 0:  # pylint: disable=no-else-return
                return BufferStatus.EMPTY
            elif size >= self.capacity:
                return BufferStatus.FULL
            else:
                return BufferStatus.PARTIAL

    def get_stats(self) -> BufferStats:
        """获取统计信息

        Returns:
            统计信息
        """
        with self._lock:
            self._stats.current_size = len(self._buffer)
            return BufferStats(
                total_writes=self._stats.total_writes,
                total_reads=self._stats.total_reads,
                overflow_count=self._stats.overflow_count,
                current_size=self._stats.current_size,
                max_size=self._stats.max_size,
                avg_latency_us=self._stats.avg_latency_us,
            )


class SharedMemoryBuffer:
    """共享内存缓冲区管理器

    白皮书依据: 第一章 1.5.1 共享内存

    管理多个命名的环形缓冲区，支持不同数据类型。

    Example:
        >>> smb = SharedMemoryBuffer()
        >>> smb.create_buffer("tick_data", capacity=10000)
        >>> smb.write("tick_data", tick)
        >>> data = smb.read("tick_data")
    """

    def __init__(self):
        """初始化共享内存缓冲区管理器"""
        self._buffers: Dict[str, RingBuffer] = {}
        self._lock = threading.RLock()

        logger.info("共享内存缓冲区管理器初始化")

    def create_buffer(self, name: str, capacity: int = 10000, overwrite: bool = True) -> bool:
        """创建命名缓冲区

        Args:
            name: 缓冲区名称
            capacity: 容量
            overwrite: 满时是否覆盖

        Returns:
            是否创建成功
        """
        with self._lock:
            if name in self._buffers:
                logger.warning(f"缓冲区{name}已存在")
                return False

            self._buffers[name] = RingBuffer(capacity=capacity, overwrite=overwrite)
            logger.info(f"创建缓冲区: {name}, 容量={capacity}")
            return True

    def delete_buffer(self, name: str) -> bool:
        """删除缓冲区

        Args:
            name: 缓冲区名称

        Returns:
            是否删除成功
        """
        with self._lock:
            if name not in self._buffers:
                return False

            del self._buffers[name]
            logger.info(f"删除缓冲区: {name}")
            return True

    def write(self, name: str, data: Any) -> bool:
        """写入数据到指定缓冲区

        Args:
            name: 缓冲区名称
            data: 数据

        Returns:
            是否成功
        """
        with self._lock:
            buffer = self._buffers.get(name)
            if not buffer:
                logger.warning(f"缓冲区{name}不存在")
                return False

            return buffer.write(data)

    def read(self, name: str) -> Optional[Any]:
        """从指定缓冲区读取数据

        Args:
            name: 缓冲区名称

        Returns:
            数据
        """
        with self._lock:
            buffer = self._buffers.get(name)
            if not buffer:
                return None

            return buffer.read()

    def read_batch(self, name: str, count: int) -> List[Any]:
        """批量读取数据

        Args:
            name: 缓冲区名称
            count: 读取数量

        Returns:
            数据列表
        """
        with self._lock:
            buffer = self._buffers.get(name)
            if not buffer:
                return []

            return buffer.read_batch(count)

    def get_buffer(self, name: str) -> Optional[RingBuffer]:
        """获取缓冲区实例

        Args:
            name: 缓冲区名称

        Returns:
            缓冲区实例
        """
        with self._lock:
            return self._buffers.get(name)

    def list_buffers(self) -> List[str]:
        """列出所有缓冲区名称

        Returns:
            缓冲区名称列表
        """
        with self._lock:
            return list(self._buffers.keys())

    def get_all_stats(self) -> Dict[str, BufferStats]:
        """获取所有缓冲区统计

        Returns:
            {名称: 统计信息}
        """
        with self._lock:
            return {name: buffer.get_stats() for name, buffer in self._buffers.items()}

    def clear_all(self) -> None:
        """清空所有缓冲区"""
        with self._lock:
            for buffer in self._buffers.values():
                buffer.clear()

        logger.info("所有缓冲区已清空")

    def get_total_size(self) -> int:
        """获取所有缓冲区总数据量

        Returns:
            总数据量
        """
        with self._lock:
            return sum(buffer.size() for buffer in self._buffers.values())


# 预定义的缓冲区名称常量
class BufferNames:
    """缓冲区名称常量"""

    TICK_DATA = "tick_data"
    BAR_DATA = "bar_data"
    SIGNAL_DATA = "signal_data"
    ORDER_DATA = "order_data"
    TRADE_DATA = "trade_data"
    RISK_DATA = "risk_data"


# 全局共享内存实例
_global_shared_memory: Optional[SharedMemoryBuffer] = None


def get_shared_memory() -> SharedMemoryBuffer:
    """获取全局共享内存实例

    Returns:
        共享内存实例
    """
    global _global_shared_memory  # pylint: disable=w0603

    if _global_shared_memory is None:
        _global_shared_memory = SharedMemoryBuffer()

        # 创建默认缓冲区
        _global_shared_memory.create_buffer(BufferNames.TICK_DATA, capacity=100000)
        _global_shared_memory.create_buffer(BufferNames.BAR_DATA, capacity=10000)
        _global_shared_memory.create_buffer(BufferNames.SIGNAL_DATA, capacity=1000)
        _global_shared_memory.create_buffer(BufferNames.ORDER_DATA, capacity=1000)
        _global_shared_memory.create_buffer(BufferNames.TRADE_DATA, capacity=1000)
        _global_shared_memory.create_buffer(BufferNames.RISK_DATA, capacity=1000)

    return _global_shared_memory
