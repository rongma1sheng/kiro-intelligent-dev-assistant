"""
共享内存缓冲区单元测试

白皮书依据: 第一章 1.5.1 战备态任务调度
测试范围: SharedMemoryBuffer的环形缓冲区和数据共享功能
"""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock

from src.infra.shared_memory import (
    RingBuffer,
    SharedMemoryBuffer,
    BufferStatus,
    BufferStats,
    BufferNames,
    get_shared_memory
)


class TestBufferStatus:
    """BufferStatus枚举测试"""
    
    def test_status_values(self):
        """测试状态枚举值"""
        assert BufferStatus.EMPTY.value == "空"
        assert BufferStatus.PARTIAL.value == "部分填充"
        assert BufferStatus.FULL.value == "满"
        assert BufferStatus.OVERFLOW.value == "溢出"


class TestBufferStats:
    """BufferStats统计类测试"""
    
    def test_stats_creation(self):
        """测试统计创建"""
        stats = BufferStats(
            total_writes=100,
            total_reads=50,
            overflow_count=5,
            current_size=50,
            max_size=100
        )
        
        assert stats.total_writes == 100
        assert stats.total_reads == 50
        assert stats.overflow_count == 5
    
    def test_stats_to_dict(self):
        """测试统计转字典"""
        stats = BufferStats(total_writes=10)
        
        result = stats.to_dict()
        
        assert result["total_writes"] == 10


class TestRingBuffer:
    """RingBuffer环形缓冲区测试"""
    
    @pytest.fixture
    def buffer(self):
        """创建缓冲区实例"""
        return RingBuffer[int](capacity=10, overwrite=True)
    
    def test_init_default(self):
        """测试默认初始化"""
        buffer = RingBuffer[int]()
        
        assert buffer.capacity == 10000
        assert buffer.overwrite is True
    
    def test_init_custom(self):
        """测试自定义初始化"""
        buffer = RingBuffer[str](capacity=100, overwrite=False)
        
        assert buffer.capacity == 100
        assert buffer.overwrite is False
    
    def test_init_invalid_capacity(self):
        """测试无效容量"""
        with pytest.raises(ValueError):
            RingBuffer[int](capacity=0)
        
        with pytest.raises(ValueError):
            RingBuffer[int](capacity=-1)
    
    def test_write_single(self, buffer):
        """测试单个写入"""
        result = buffer.write(42)
        
        assert result is True
        assert buffer.size() == 1
    
    def test_write_batch(self, buffer):
        """测试批量写入"""
        data = [1, 2, 3, 4, 5]
        written = buffer.write_batch(data)
        
        assert written == 5
        assert buffer.size() == 5
    
    def test_read_single(self, buffer):
        """测试单个读取"""
        buffer.write(42)
        
        data = buffer.read()
        
        assert data == 42
        assert buffer.size() == 0
    
    def test_read_empty(self, buffer):
        """测试空缓冲区读取"""
        data = buffer.read()
        
        assert data is None
    
    def test_read_batch(self, buffer):
        """测试批量读取"""
        buffer.write_batch([1, 2, 3, 4, 5])
        
        data = buffer.read_batch(3)
        
        assert data == [1, 2, 3]
        assert buffer.size() == 2
    
    def test_peek(self, buffer):
        """测试查看不移除"""
        buffer.write(42)
        
        data = buffer.peek()
        
        assert data == 42
        assert buffer.size() == 1  # 数据仍在
    
    def test_peek_all(self, buffer):
        """测试查看所有"""
        buffer.write_batch([1, 2, 3])
        
        data = buffer.peek_all()
        
        assert data == [1, 2, 3]
        assert buffer.size() == 3  # 数据仍在
    
    def test_clear(self, buffer):
        """测试清空"""
        buffer.write_batch([1, 2, 3])
        buffer.clear()
        
        assert buffer.size() == 0
        assert buffer.is_empty() is True
    
    def test_is_empty(self, buffer):
        """测试空检查"""
        assert buffer.is_empty() is True
        
        buffer.write(1)
        assert buffer.is_empty() is False
    
    def test_is_full(self, buffer):
        """测试满检查"""
        assert buffer.is_full() is False
        
        buffer.write_batch(list(range(10)))
        assert buffer.is_full() is True
    
    def test_overwrite_mode(self):
        """测试覆盖模式"""
        buffer = RingBuffer[int](capacity=3, overwrite=True)
        
        buffer.write_batch([1, 2, 3, 4, 5])
        
        # 覆盖模式下，旧数据被覆盖
        assert buffer.size() == 3
        data = buffer.peek_all()
        assert data == [3, 4, 5]
    
    def test_no_overwrite_mode(self):
        """测试非覆盖模式"""
        buffer = RingBuffer[int](capacity=3, overwrite=False)
        
        buffer.write_batch([1, 2, 3])
        result = buffer.write(4)  # 应该失败
        
        assert result is False
        assert buffer.size() == 3
    
    def test_get_status(self, buffer):
        """测试获取状态"""
        assert buffer.get_status() == BufferStatus.EMPTY
        
        buffer.write_batch([1, 2, 3])
        assert buffer.get_status() == BufferStatus.PARTIAL
        
        buffer.write_batch(list(range(10)))
        assert buffer.get_status() == BufferStatus.FULL
    
    def test_get_stats(self, buffer):
        """测试获取统计"""
        buffer.write_batch([1, 2, 3])
        buffer.read()
        
        stats = buffer.get_stats()
        
        assert stats.total_writes == 3
        assert stats.total_reads == 1
        assert stats.current_size == 2


class TestRingBufferThreadSafety:
    """线程安全测试"""
    
    def test_concurrent_write(self):
        """测试并发写入"""
        buffer = RingBuffer[int](capacity=1000)
        
        def writer(start):
            for i in range(100):
                buffer.write(start + i)
        
        threads = [
            threading.Thread(target=writer, args=(i * 100,))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert buffer.size() == 500
    
    def test_concurrent_read_write(self):
        """测试并发读写"""
        buffer = RingBuffer[int](capacity=100)
        read_count = [0]
        
        def writer():
            for i in range(50):
                buffer.write(i)
                time.sleep(0.001)
        
        def reader():
            for _ in range(50):
                if buffer.read() is not None:
                    read_count[0] += 1
                time.sleep(0.001)
        
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        
        writer_thread.start()
        reader_thread.start()
        
        writer_thread.join()
        reader_thread.join()
        
        # 读取数量应该大于0
        assert read_count[0] > 0


class TestSharedMemoryBuffer:
    """SharedMemoryBuffer管理器测试"""
    
    @pytest.fixture
    def smb(self):
        """创建管理器实例"""
        return SharedMemoryBuffer()
    
    def test_create_buffer(self, smb):
        """测试创建缓冲区"""
        result = smb.create_buffer("test", capacity=100)
        
        assert result is True
        assert "test" in smb.list_buffers()
    
    def test_create_duplicate_buffer(self, smb):
        """测试创建重复缓冲区"""
        smb.create_buffer("test")
        result = smb.create_buffer("test")
        
        assert result is False
    
    def test_delete_buffer(self, smb):
        """测试删除缓冲区"""
        smb.create_buffer("test")
        result = smb.delete_buffer("test")
        
        assert result is True
        assert "test" not in smb.list_buffers()
    
    def test_delete_nonexistent_buffer(self, smb):
        """测试删除不存在的缓冲区"""
        result = smb.delete_buffer("nonexistent")
        
        assert result is False
    
    def test_write_read(self, smb):
        """测试写入读取"""
        smb.create_buffer("test")
        
        smb.write("test", 42)
        data = smb.read("test")
        
        assert data == 42
    
    def test_write_nonexistent_buffer(self, smb):
        """测试写入不存在的缓冲区"""
        result = smb.write("nonexistent", 42)
        
        assert result is False
    
    def test_read_nonexistent_buffer(self, smb):
        """测试读取不存在的缓冲区"""
        data = smb.read("nonexistent")
        
        assert data is None
    
    def test_read_batch(self, smb):
        """测试批量读取"""
        smb.create_buffer("test")
        
        for i in range(5):
            smb.write("test", i)
        
        data = smb.read_batch("test", 3)
        
        assert data == [0, 1, 2]
    
    def test_get_buffer(self, smb):
        """测试获取缓冲区实例"""
        smb.create_buffer("test")
        
        buffer = smb.get_buffer("test")
        
        assert buffer is not None
        assert isinstance(buffer, RingBuffer)
    
    def test_list_buffers(self, smb):
        """测试列出缓冲区"""
        smb.create_buffer("buffer1")
        smb.create_buffer("buffer2")
        
        buffers = smb.list_buffers()
        
        assert "buffer1" in buffers
        assert "buffer2" in buffers
    
    def test_get_all_stats(self, smb):
        """测试获取所有统计"""
        smb.create_buffer("test1")
        smb.create_buffer("test2")
        
        smb.write("test1", 1)
        smb.write("test2", 2)
        
        stats = smb.get_all_stats()
        
        assert "test1" in stats
        assert "test2" in stats
    
    def test_clear_all(self, smb):
        """测试清空所有"""
        smb.create_buffer("test1")
        smb.create_buffer("test2")
        
        smb.write("test1", 1)
        smb.write("test2", 2)
        
        smb.clear_all()
        
        assert smb.get_total_size() == 0
    
    def test_get_total_size(self, smb):
        """测试获取总大小"""
        smb.create_buffer("test1")
        smb.create_buffer("test2")
        
        smb.write("test1", 1)
        smb.write("test1", 2)
        smb.write("test2", 3)
        
        assert smb.get_total_size() == 3


class TestBufferNames:
    """BufferNames常量测试"""
    
    def test_buffer_names(self):
        """测试缓冲区名称常量"""
        assert BufferNames.TICK_DATA == "tick_data"
        assert BufferNames.BAR_DATA == "bar_data"
        assert BufferNames.SIGNAL_DATA == "signal_data"
        assert BufferNames.ORDER_DATA == "order_data"


class TestGlobalSharedMemory:
    """全局共享内存测试"""
    
    def test_get_shared_memory(self):
        """测试获取全局实例"""
        smb = get_shared_memory()
        
        assert smb is not None
        assert isinstance(smb, SharedMemoryBuffer)
    
    def test_default_buffers_created(self):
        """测试默认缓冲区已创建"""
        smb = get_shared_memory()
        
        buffers = smb.list_buffers()
        
        assert BufferNames.TICK_DATA in buffers
        assert BufferNames.BAR_DATA in buffers
        assert BufferNames.SIGNAL_DATA in buffers
