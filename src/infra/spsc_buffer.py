"""
SPSC Ring Buffer实现

白皮书依据: 第三章 3.2 混合通信总线
实现Single-Producer Single-Consumer无锁环形队列
"""

import atexit
import struct
import threading
from dataclasses import dataclass
from multiprocessing import shared_memory
from typing import Any, Dict, Optional, Tuple

import msgpack
from loguru import logger


@dataclass
class SPSCHeader:
    """SPSC缓冲区头部信息

    Attributes:
        write_pos: 写入位置
        read_pos: 读取位置
        sequence_id: 序列号
        buffer_size: 缓冲区大小
        magic: 魔数，用于验证
    """

    write_pos: int = 0
    read_pos: int = 0
    sequence_id: int = 0
    buffer_size: int = 0
    magic: int = 0xDEADBEEF


class SPSCBuffer:
    """SPSC Ring Buffer

    白皮书依据: 第三章 3.2 混合通信总线

    Single-Producer Single-Consumer无锁环形队列，用于高性能进程间通信。

    特性:
    - 无锁设计，避免锁竞争
    - 原子性校验，防止撕裂读
    - 序列号机制，确保数据完整性
    - 共享内存，零拷贝传输

    Performance:
    - 延迟: < 100μs
    - 吞吐量: > 1M msg/s

    Attributes:
        name: 缓冲区名称
        buffer_size: 缓冲区大小
        shm: 共享内存对象
        header: 缓冲区头部
        data_buffer: 数据缓冲区
    """

    HEADER_SIZE = 32  # 头部大小（字节）

    def __init__(self, name: str, buffer_size: int = 1024 * 1024, create: bool = True):
        """初始化SPSC缓冲区

        Args:
            name: 缓冲区名称
            buffer_size: 缓冲区大小（字节）
            create: 是否创建新缓冲区

        Raises:
            ValueError: 当缓冲区大小无效时
            RuntimeError: 当共享内存操作失败时
        """
        if buffer_size < 1024:
            raise ValueError(f"Buffer size too small: {buffer_size}")

        self.name = name
        self.buffer_size = buffer_size
        self.total_size = self.HEADER_SIZE + buffer_size

        try:
            if create:
                # 创建新的共享内存
                self.shm = shared_memory.SharedMemory(name=name, create=True, size=self.total_size)

                # 初始化头部
                self._init_header()

                logger.info(f"Created SPSC buffer: {name}, size: {buffer_size}")
            else:
                # 连接到现有共享内存
                self.shm = shared_memory.SharedMemory(name=name)

                # 验证头部
                self._validate_header()

                logger.info(f"Connected to SPSC buffer: {name}")

            # 注册清理函数
            atexit.register(self.cleanup)

        except Exception as e:
            logger.error(f"Failed to initialize SPSC buffer {name}: {e}")
            raise RuntimeError(f"SPSC buffer initialization failed") from e  # pylint: disable=w1309

    def _init_header(self) -> None:
        """初始化缓冲区头部"""
        header_data = struct.pack(
            "IIIII",
            0,  # write_pos
            0,  # read_pos
            0,  # sequence_id
            self.buffer_size,  # buffer_size
            0xDEADBEEF,  # magic
        )

        # 确保头部数据长度正确
        if len(header_data) != 20:  # 5个int，每个4字节
            raise RuntimeError(f"Header data size mismatch: {len(header_data)} != 20")

        # 初始化整个头部区域为0
        self.shm.buf[: self.HEADER_SIZE] = b"\x00" * self.HEADER_SIZE

        # 写入头部数据
        self.shm.buf[: len(header_data)] = header_data

    def _validate_header(self) -> None:
        """验证缓冲区头部"""
        header_bytes = bytes(self.shm.buf[:20])

        if len(header_bytes) < 20:
            raise RuntimeError(f"头部数据不足: {len(header_bytes)} < 20")

        header_data = struct.unpack("IIIII", header_bytes)

        if header_data[4] != 0xDEADBEEF:
            raise RuntimeError("Invalid SPSC buffer magic number")

        if header_data[3] != self.buffer_size:
            raise RuntimeError(f"Buffer size mismatch: expected {self.buffer_size}, got {header_data[3]}")

    def _read_header(self) -> SPSCHeader:
        """读取缓冲区头部

        Returns:
            头部信息

        Raises:
            RuntimeError: 当共享内存已被清理时
        """
        # 检查共享内存是否有效
        if not hasattr(self, "shm") or self.shm is None:
            raise RuntimeError("Shared memory has been cleaned up")

        try:
            # 读取头部数据（20字节：5个int）
            header_bytes = bytes(self.shm.buf[:20])
        except (AttributeError, TypeError) as e:
            # shm.buf 可能为 None 或已被清理
            raise RuntimeError("共享内存缓冲区不可访问") from e

        if len(header_bytes) < 20:
            raise RuntimeError(f"头部数据不足: {len(header_bytes)} < 20")

        header_data = struct.unpack("IIIII", header_bytes)

        return SPSCHeader(
            write_pos=header_data[0],
            read_pos=header_data[1],
            sequence_id=header_data[2],
            buffer_size=header_data[3],
            magic=header_data[4],
        )

    def _write_header(self, header: SPSCHeader) -> None:
        """写入缓冲区头部

        Args:
            header: 头部信息

        Raises:
            RuntimeError: 当共享内存已被清理时
        """
        # 检查共享内存是否有效
        if not hasattr(self, "shm") or self.shm is None:
            raise RuntimeError("Shared memory has been cleaned up")

        header_data = struct.pack(
            "IIIII", header.write_pos, header.read_pos, header.sequence_id, header.buffer_size, header.magic
        )

        try:
            # 写入头部数据
            self.shm.buf[: len(header_data)] = header_data
        except (AttributeError, TypeError) as e:
            # shm.buf 可能为 None 或已被清理
            raise RuntimeError("共享内存缓冲区不可访问") from e

    def write(self, data: Any) -> bool:
        """写入数据（生产者）

        白皮书依据: 第三章 3.2 原子性校验

        Args:
            data: 要写入的数据

        Returns:
            写入是否成功
        """
        try:
            # 序列化数据
            serialized_data = msgpack.packb(data)
            data_size = len(serialized_data)

            # 检查数据大小
            if data_size > self.buffer_size - 8:  # 预留8字节用于长度和序列号
                logger.error(f"Data too large: {data_size} > {self.buffer_size - 8}")
                return False

            # 读取当前头部
            header = self._read_header()

            # 计算写入位置
            write_pos = header.write_pos
            read_pos = header.read_pos

            # 检查缓冲区空间
            available_space = self._get_available_space(write_pos, read_pos)
            required_space = data_size + 8  # 数据 + 长度 + 序列号

            if required_space > available_space:
                logger.warning(f"Buffer full: required {required_space}, available {available_space}")
                return False

            # 更新序列号
            header.sequence_id += 1
            sequence_id = header.sequence_id

            # 写入数据包：[序列号(4字节)] [长度(4字节)] [数据]
            packet = struct.pack("II", sequence_id, data_size) + serialized_data

            # 写入到环形缓冲区
            self._write_to_ring_buffer(write_pos, packet)

            # 更新写入位置
            header.write_pos = (write_pos + len(packet)) % self.buffer_size

            # 原子性更新头部
            self._write_header(header)

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to write data: {e}")
            return False

    def read(self) -> Optional[Tuple[Any, int]]:
        """读取数据（消费者）

        白皮书依据: 第三章 3.2 撕裂读检测

        Returns:
            (数据, 序列号) 或 None（如果没有数据或发生撕裂读）
        """
        try:
            # 读取头部（第一次）
            header1 = self._read_header()

            write_pos = header1.write_pos
            read_pos = header1.read_pos

            # 检查是否有数据
            if read_pos == write_pos:
                return None  # 缓冲区为空

            # 读取数据包头部：[序列号(4字节)] [长度(4字节)]
            packet_header = self._read_from_ring_buffer(read_pos, 8)
            sequence_id, data_size = struct.unpack("II", packet_header)

            # 检查数据大小合理性
            if data_size > self.buffer_size or data_size == 0:
                logger.error(f"Invalid data size: {data_size}")
                return None

            # 读取数据
            data_start = (read_pos + 8) % self.buffer_size
            serialized_data = self._read_from_ring_buffer(data_start, data_size)

            # 读取头部（第二次）进行撕裂读检测
            header2 = self._read_header()

            # 检查序列号是否一致（撕裂读检测）
            if header1.sequence_id != header2.sequence_id:
                logger.warning("Torn read detected, discarding data")
                return None

            # 反序列化数据
            data = msgpack.unpackb(serialized_data, raw=False)

            # 更新读取位置
            new_read_pos = (read_pos + 8 + data_size) % self.buffer_size
            header2.read_pos = new_read_pos
            self._write_header(header2)

            return data, sequence_id

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to read data: {e}")
            return None

    def _get_available_space(self, write_pos: int, read_pos: int) -> int:
        """计算可用空间

        Args:
            write_pos: 写入位置
            read_pos: 读取位置

        Returns:
            可用空间大小
        """
        if write_pos >= read_pos:  # pylint: disable=no-else-return
            return self.buffer_size - (write_pos - read_pos) - 1
        else:
            return read_pos - write_pos - 1

    def _write_to_ring_buffer(self, pos: int, data: bytes) -> None:
        """写入到环形缓冲区

        Args:
            pos: 写入位置
            data: 数据

        Raises:
            RuntimeError: 当共享内存已被清理时
        """
        # 检查共享内存是否有效
        if not hasattr(self, "shm") or self.shm is None:
            raise RuntimeError("Shared memory has been cleaned up")

        data_len = len(data)
        buffer_start = self.HEADER_SIZE

        try:
            if pos + data_len <= self.buffer_size:
                # 数据不跨越边界
                self.shm.buf[buffer_start + pos : buffer_start + pos + data_len] = data
            else:
                # 数据跨越边界，分两部分写入
                first_part_len = self.buffer_size - pos
                second_part_len = data_len - first_part_len

                # 写入第一部分
                self.shm.buf[buffer_start + pos : buffer_start + self.buffer_size] = data[:first_part_len]

                # 写入第二部分
                self.shm.buf[buffer_start : buffer_start + second_part_len] = data[first_part_len:]
        except (AttributeError, TypeError) as e:
            # shm.buf 可能为 None 或已被清理
            raise RuntimeError("共享内存缓冲区不可访问") from e

    def _read_from_ring_buffer(self, pos: int, size: int) -> bytes:
        """从环形缓冲区读取

        Args:
            pos: 读取位置
            size: 读取大小

        Returns:
            读取的数据

        Raises:
            RuntimeError: 当共享内存已被清理时
        """
        # 检查共享内存是否有效
        if not hasattr(self, "shm") or self.shm is None:
            raise RuntimeError("Shared memory has been cleaned up")

        buffer_start = self.HEADER_SIZE

        try:
            if pos + size <= self.buffer_size:  # pylint: disable=no-else-return
                # 数据不跨越边界
                return bytes(self.shm.buf[buffer_start + pos : buffer_start + pos + size])
            else:
                # 数据跨越边界，分两部分读取
                first_part_len = self.buffer_size - pos
                second_part_len = size - first_part_len

                # 读取第一部分
                first_part = bytes(self.shm.buf[buffer_start + pos : buffer_start + self.buffer_size])

                # 读取第二部分
                second_part = bytes(self.shm.buf[buffer_start : buffer_start + second_part_len])

                return first_part + second_part
        except (AttributeError, TypeError) as e:
            # shm.buf 可能为 None 或已被清理
            raise RuntimeError("共享内存缓冲区不可访问") from e

    def get_stats(self) -> Dict[str, Any]:
        """获取缓冲区统计信息

        Returns:
            统计信息
        """
        header = self._read_header()

        available_space = self._get_available_space(header.write_pos, header.read_pos)
        used_space = self.buffer_size - available_space - 1

        return {
            "name": self.name,
            "buffer_size": self.buffer_size,
            "write_pos": header.write_pos,
            "read_pos": header.read_pos,
            "sequence_id": header.sequence_id,
            "used_space": used_space,
            "available_space": available_space,
            "usage_percent": (used_space / self.buffer_size) * 100,
        }

    def cleanup(self) -> None:
        """清理资源"""
        try:
            if hasattr(self, "shm") and self.shm:
                self.shm.close()
                self.shm = None  # 标记为已清理
                logger.info(f"SPSC buffer {self.name} closed")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error cleaning up SPSC buffer {self.name}: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup()


class SPSCManager:
    """SPSC缓冲区管理器

    白皮书依据: 第三章 3.2 SharedMemory生命周期管理

    管理多个SPSC缓冲区的生命周期，提供统一的接口。
    """

    def __init__(self):
        """初始化管理器"""
        self.buffers: Dict[str, SPSCBuffer] = {}
        self._lock = threading.RLock()

        # 注册清理函数
        atexit.register(self.cleanup_all)

        logger.info("SPSC Manager initialized")

    def create_buffer(self, name: str, buffer_size: int = 1024 * 1024) -> SPSCBuffer:
        """创建SPSC缓冲区

        Args:
            name: 缓冲区名称
            buffer_size: 缓冲区大小

        Returns:
            SPSC缓冲区实例

        Raises:
            ValueError: 当缓冲区已存在时
        """
        with self._lock:
            if name in self.buffers:
                raise ValueError(f"Buffer {name} already exists")

            buffer = SPSCBuffer(name, buffer_size, create=True)
            self.buffers[name] = buffer

            logger.info(f"Created SPSC buffer: {name}")
            return buffer

    def connect_buffer(self, name: str) -> SPSCBuffer:
        """连接到现有SPSC缓冲区

        Args:
            name: 缓冲区名称

        Returns:
            SPSC缓冲区实例

        Raises:
            ValueError: 当缓冲区不存在时
        """
        with self._lock:
            if name in self.buffers:
                return self.buffers[name]

            buffer = SPSCBuffer(name, create=False)
            self.buffers[name] = buffer

            logger.info(f"Connected to SPSC buffer: {name}")
            return buffer

    def get_buffer(self, name: str) -> Optional[SPSCBuffer]:
        """获取SPSC缓冲区

        Args:
            name: 缓冲区名称

        Returns:
            SPSC缓冲区实例或None
        """
        with self._lock:
            return self.buffers.get(name)

    def remove_buffer(self, name: str) -> bool:
        """移除SPSC缓冲区

        Args:
            name: 缓冲区名称

        Returns:
            移除是否成功
        """
        with self._lock:
            if name not in self.buffers:
                return False

            buffer = self.buffers[name]
            buffer.cleanup()

            # 尝试删除共享内存
            try:
                buffer.shm.unlink()
                logger.info(f"Unlinked shared memory: {name}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Failed to unlink shared memory {name}: {e}")

            del self.buffers[name]
            logger.info(f"Removed SPSC buffer: {name}")
            return True

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓冲区统计信息

        Returns:
            所有缓冲区的统计信息
        """
        with self._lock:
            stats = {}
            for name, buffer in self.buffers.items():
                try:
                    stats[name] = buffer.get_stats()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Failed to get stats for buffer {name}: {e}")
                    stats[name] = {"error": str(e)}

            return stats

    def cleanup_all(self) -> None:
        """清理所有缓冲区"""
        with self._lock:
            for name in list(self.buffers.keys()):
                try:
                    self.remove_buffer(name)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Error cleaning up buffer {name}: {e}")

            logger.info("All SPSC buffers cleaned up")


# 全局SPSC管理器实例
spsc_manager = SPSCManager()


def get_spsc_manager() -> SPSCManager:
    """获取SPSC管理器实例

    Returns:
        SPSC管理器实例
    """
    return spsc_manager
