"""SharedMemory生命周期管理 - SPSC Manager

白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

问题: 进程异常退出导致SharedMemory泄漏
风险等级: 🟡 中

功能:
1. 上下文管理器支持
2. 原子写入（带序列ID）
3. 原子读取（撕裂读检测）
4. 自动清理机制

性能要求:
- 延迟: < 100μs
- 吞吐量: > 60Hz
"""

import atexit
import struct
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger

try:
    from multiprocessing import shared_memory

    import msgpack

    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    SHARED_MEMORY_AVAILABLE = False
    logger.warning("shared_memory或msgpack不可用，SPSCManager将使用模拟模式")


@dataclass
class SPSCStats:
    """SPSC统计信息

    白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

    Attributes:
        total_writes: 总写入次数
        total_reads: 总读取次数
        torn_reads: 撕裂读次数
        avg_write_latency_us: 平均写入延迟（微秒）
        avg_read_latency_us: 平均读取延迟（微秒）
    """

    total_writes: int = 0
    total_reads: int = 0
    torn_reads: int = 0
    avg_write_latency_us: float = 0.0
    avg_read_latency_us: float = 0.0
    _write_latencies: list = None
    _read_latencies: list = None

    def __post_init__(self):
        self._write_latencies = []
        self._read_latencies = []

    def record_write(self, latency_us: float) -> None:
        """记录写入"""
        self.total_writes += 1
        self._write_latencies.append(latency_us)
        if len(self._write_latencies) > 100:
            self._write_latencies.pop(0)
        self.avg_write_latency_us = sum(self._write_latencies) / len(self._write_latencies)

    def record_read(self, latency_us: float, is_torn: bool = False) -> None:
        """记录读取"""
        self.total_reads += 1
        if is_torn:
            self.torn_reads += 1
        else:
            self._read_latencies.append(latency_us)
            if len(self._read_latencies) > 100:
                self._read_latencies.pop(0)
            self.avg_read_latency_us = sum(self._read_latencies) / len(self._read_latencies)


class SPSCManager:
    """SPSC共享内存管理器

    白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

    提供单生产者单消费者（SPSC）模式的共享内存管理，
    支持原子读写和撕裂读检测。

    内存布局:
    [seq_id_start(8B)][data_len(4B)][data(N B)][seq_id_end(8B)]

    Attributes:
        name: 共享内存名称
        size: 共享内存大小（字节）
        is_producer: 是否为生产者
        shm: 共享内存对象
        stats: 统计信息
        _lock: 线程锁
        _cleaned: 是否已清理
    """

    # 头部大小: seq_id(8B) + data_len(4B) = 12B
    HEADER_SIZE = 12
    # 尾部大小: seq_id(8B) = 8B
    FOOTER_SIZE = 8

    def __init__(self, name: str, size: int, create: bool = False):
        """初始化SPSC管理器

        Args:
            name: 共享内存名称
            size: 共享内存大小（字节）
            create: 是否创建新的共享内存（生产者为True）

        Raises:
            ValueError: 当参数无效时
            RuntimeError: 当共享内存操作失败时
        """
        if not name:
            raise ValueError("共享内存名称不能为空")

        if size <= self.HEADER_SIZE + self.FOOTER_SIZE:
            raise ValueError(f"共享内存大小必须 > {self.HEADER_SIZE + self.FOOTER_SIZE}，" f"当前: {size}")

        self.name: str = name
        self.size: int = size
        self.is_producer: bool = create
        self.shm: Optional[Any] = None
        self.stats: SPSCStats = SPSCStats()

        self._lock: threading.RLock = threading.RLock()
        self._cleaned: bool = False

        if SHARED_MEMORY_AVAILABLE:
            try:
                if create:
                    # 先尝试清理可能存在的旧共享内存
                    try:
                        old_shm = shared_memory.SharedMemory(name=name)
                        old_shm.close()
                        old_shm.unlink()
                        logger.info(f"[SPSC] Cleaned up existing SharedMemory: {name}")
                    except FileNotFoundError:
                        pass

                    self.shm = shared_memory.SharedMemory(name=name, create=True, size=size)
                    logger.info(f"[SPSC] Created SharedMemory: {name} ({size} bytes)")
                else:
                    self.shm = shared_memory.SharedMemory(name=name)
                    logger.info(f"[SPSC] Connected to SharedMemory: {name}")

                # 注册清理函数
                atexit.register(self.cleanup)

            except Exception as e:
                logger.error(f"[SPSC] Failed to initialize SharedMemory: {e}")
                raise RuntimeError(f"SharedMemory初始化失败: {e}") from e
        else:
            logger.warning(f"[SPSC] SharedMemory not available, using mock mode")  # pylint: disable=w1309
            self._mock_buffer: bytes = bytearray(size)

    def __enter__(self) -> "SPSCManager":
        """上下文管理器入口

        Returns:
            self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪
        """
        self.cleanup()

    def cleanup(self) -> None:
        """清理共享内存

        白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理
        """
        with self._lock:
            if self._cleaned:
                return

            self._cleaned = True

            if self.shm is not None:
                try:
                    self.shm.close()
                    if self.is_producer:
                        self.shm.unlink()
                        logger.info(f"[SPSC] Cleaned up SharedMemory: {self.name}")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"[SPSC] Cleanup error: {e}")

    def atomic_write(self, data: Any) -> bool:
        """原子写入

        白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

        写入格式: [seq_id(8B)][data_len(4B)][data][seq_id(8B)]

        Args:
            data: 要写入的数据（可序列化）

        Returns:
            写入是否成功
        """
        start_time = time.perf_counter()

        try:
            # 生成序列ID（微秒时间戳）
            seq_id = int(time.time() * 1000000)

            # 序列化数据
            if SHARED_MEMORY_AVAILABLE:
                data_bytes = msgpack.packb(data)
            else:
                data_bytes = str(data).encode("utf-8")

            # 检查数据大小
            total_size = self.HEADER_SIZE + len(data_bytes) + self.FOOTER_SIZE
            if total_size > self.size:
                logger.error(f"[SPSC] Data too large: {total_size} > {self.size}")
                return False

            # 获取缓冲区
            buf = self._get_buffer()
            if buf is None:
                return False

            with self._lock:
                # 写入头部序列ID
                struct.pack_into("Q", buf, 0, seq_id)
                # 写入数据长度
                struct.pack_into("I", buf, 8, len(data_bytes))
                # 写入数据
                buf[12 : 12 + len(data_bytes)] = data_bytes
                # 写入尾部序列ID
                struct.pack_into("Q", buf, 12 + len(data_bytes), seq_id)

            # 记录统计
            latency_us = (time.perf_counter() - start_time) * 1000000
            self.stats.record_write(latency_us)

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SPSC] Write error: {e}")
            return False

    def atomic_read(self) -> Optional[Any]:
        """原子读取

        白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

        读取格式: [seq_id(8B)][data_len(4B)][data][seq_id(8B)]
        检测撕裂读：比较头尾序列ID

        Returns:
            读取的数据，如果撕裂读或失败则返回None
        """
        start_time = time.perf_counter()

        try:
            # 获取缓冲区
            buf = self._get_buffer()
            if buf is None:
                return None

            with self._lock:
                # 读取头部序列ID
                seq_id_start = struct.unpack_from("Q", buf, 0)[0]

                # 读取数据长度
                data_len = struct.unpack_from("I", buf, 8)[0]

                # 检查数据长度有效性
                if data_len <= 0 or data_len > self.size - self.HEADER_SIZE - self.FOOTER_SIZE:
                    return None

                # 读取数据
                data_bytes = bytes(buf[12 : 12 + data_len])

                # 读取尾部序列ID
                seq_id_end = struct.unpack_from("Q", buf, 12 + data_len)[0]

            # 检测撕裂读
            if seq_id_start != seq_id_end:
                logger.warning("[SPSC] Data torn, discarding")
                latency_us = (time.perf_counter() - start_time) * 1000000
                self.stats.record_read(latency_us, is_torn=True)
                return None

            # 反序列化数据
            if SHARED_MEMORY_AVAILABLE:
                data = msgpack.unpackb(data_bytes)
            else:
                data = data_bytes.decode("utf-8")

            # 记录统计
            latency_us = (time.perf_counter() - start_time) * 1000000
            self.stats.record_read(latency_us)

            return data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SPSC] Read error: {e}")
            return None

    def _get_buffer(self) -> Optional[Any]:
        """获取缓冲区（内部方法）

        Returns:
            缓冲区，如果不可用则返回None
        """
        if SHARED_MEMORY_AVAILABLE and self.shm is not None:  # pylint: disable=no-else-return
            return self.shm.buf
        elif hasattr(self, "_mock_buffer"):
            return self._mock_buffer
        return None

    def get_stats(self) -> SPSCStats:
        """获取统计信息

        Returns:
            统计信息
        """
        return self.stats

    def is_available(self) -> bool:
        """检查共享内存是否可用

        Returns:
            是否可用
        """
        return self.shm is not None or hasattr(self, "_mock_buffer")

    def get_name(self) -> str:
        """获取共享内存名称

        Returns:
            共享内存名称
        """
        return self.name

    def get_size(self) -> int:
        """获取共享内存大小

        Returns:
            共享内存大小（字节）
        """
        return self.size


# 全局管理器注册表
_managers: Dict[str, SPSCManager] = {}
_managers_lock: threading.Lock = threading.Lock()


def get_spsc_manager(name: str, size: int = 1024 * 1024, create: bool = False) -> SPSCManager:
    """获取或创建SPSC管理器

    白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

    Args:
        name: 共享内存名称
        size: 共享内存大小（字节），默认1MB
        create: 是否创建新的共享内存

    Returns:
        SPSC管理器实例
    """
    with _managers_lock:
        if name not in _managers:
            _managers[name] = SPSCManager(name, size, create)
        return _managers[name]


def cleanup_all_managers() -> None:
    """清理所有SPSC管理器

    主要用于测试目的。
    """
    with _managers_lock:
        for manager in _managers.values():
            manager.cleanup()
        _managers.clear()
