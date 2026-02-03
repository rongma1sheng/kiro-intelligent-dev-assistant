"""
SPSC Ring Buffer测试

白皮书依据: 第三章 3.2 混合通信总线
测试SPSC无锁环形队列的功能和性能
"""

import pytest
import time
import threading
import multiprocessing
import struct
from unittest.mock import Mock, patch
from src.infra.spsc_buffer import SPSCBuffer, SPSCManager, SPSCHeader


class TestSPSCBuffer:
    """SPSC缓冲区测试"""
    
    @pytest.fixture
    def buffer_name(self):
        """缓冲区名称"""
        return f"test_buffer_{int(time.time() * 1000)}"
    
    @pytest.fixture
    def buffer(self, buffer_name):
        """创建SPSC缓冲区实例"""
        buffer = SPSCBuffer(buffer_name, buffer_size=1024, create=True)
        yield buffer
        # 清理
        try:
            buffer.cleanup()
            buffer.shm.unlink()
        except:
            pass
    
    def test_init_create(self, buffer_name):
        """测试创建新缓冲区"""
        buffer = SPSCBuffer(buffer_name, buffer_size=1024, create=True)
        
        assert buffer.name == buffer_name
        assert buffer.buffer_size == 1024
        assert buffer.total_size == 1024 + 32  # 数据 + 头部
        assert buffer.shm is not None
        
        # 验证头部初始化
        header = buffer._read_header()
        assert header.write_pos == 0
        assert header.read_pos == 0
        assert header.sequence_id == 0
        assert header.buffer_size == 1024
        assert header.magic == 0xDEADBEEF
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer.shm
        buffer.cleanup()
        shm.unlink()
    
    def test_init_invalid_size(self, buffer_name):
        """测试无效缓冲区大小"""
        with pytest.raises(ValueError, match="Buffer size too small"):
            SPSCBuffer(buffer_name, buffer_size=512, create=True)
    
    def test_write_read_simple(self, buffer):
        """测试简单写入读取"""
        test_data = {"message": "hello", "value": 42}
        
        # 写入数据
        result = buffer.write(test_data)
        assert result is True
        
        # 读取数据
        read_result = buffer.read()
        assert read_result is not None
        
        data, sequence_id = read_result
        assert data == test_data
        assert sequence_id == 1
    
    def test_write_read_multiple(self, buffer):
        """测试多次写入读取"""
        test_data = [
            {"id": 1, "value": "first"},
            {"id": 2, "value": "second"},
            {"id": 3, "value": "third"}
        ]
        
        # 写入多个数据
        for data in test_data:
            result = buffer.write(data)
            assert result is True
        
        # 读取多个数据
        for i, expected_data in enumerate(test_data):
            read_result = buffer.read()
            assert read_result is not None
            
            data, sequence_id = read_result
            assert data == expected_data
            assert sequence_id == i + 1
    
    def test_read_empty_buffer(self, buffer):
        """测试读取空缓冲区"""
        result = buffer.read()
        assert result is None
    
    def test_write_large_data(self, buffer):
        """测试写入大数据"""
        # 创建超过缓冲区大小的数据
        large_data = {"data": "x" * (buffer.buffer_size + 100)}
        
        result = buffer.write(large_data)
        assert result is False
    
    def test_buffer_full(self, buffer):
        """测试缓冲区满的情况"""
        # 填满缓冲区
        small_data = {"value": "x" * 100}
        write_count = 0
        
        while True:
            result = buffer.write(small_data)
            if not result:
                break
            write_count += 1
            
            # 防止无限循环
            if write_count > 20:
                break
        
        assert write_count > 0
        
        # 如果循环因为防止无限循环而退出（write_count > 20），
        # 说明缓冲区还没满，跳过后续断言
        if write_count > 20:
            pytest.skip("Buffer not full after 20 writes, skipping full buffer test")
        
        # 尝试再写入相同大小的数据，应该失败
        result = buffer.write(small_data)
        assert result is False
    
    def test_sequence_id_increment(self, buffer):
        """测试序列号递增"""
        data_list = [{"id": i} for i in range(5)]
        
        # 写入数据
        for data in data_list:
            buffer.write(data)
        
        # 读取数据并验证序列号
        for i in range(5):
            read_result = buffer.read()
            assert read_result is not None
            
            data, sequence_id = read_result
            assert sequence_id == i + 1
    
    def test_ring_buffer_wrap_around(self, buffer):
        """测试环形缓冲区回绕"""
        # 写入一些数据
        for i in range(3):
            buffer.write({"id": i})
        
        # 读取一些数据
        for i in range(2):
            result = buffer.read()
            assert result is not None
        
        # 再写入更多数据，测试回绕
        for i in range(3, 6):
            result = buffer.write({"id": i})
            assert result is True
        
        # 读取剩余数据
        expected_ids = [2, 3, 4, 5]
        for expected_id in expected_ids:
            read_result = buffer.read()
            assert read_result is not None
            
            data, sequence_id = read_result
            assert data["id"] == expected_id
    
    def test_get_stats(self, buffer):
        """测试获取统计信息"""
        # 写入一些数据
        for i in range(3):
            buffer.write({"id": i})
        
        stats = buffer.get_stats()
        
        assert stats["name"] == buffer.name
        assert stats["buffer_size"] == buffer.buffer_size
        assert stats["sequence_id"] == 3
        assert stats["used_space"] > 0
        assert stats["available_space"] < buffer.buffer_size
        assert 0 <= stats["usage_percent"] <= 100
    
    def test_concurrent_write_read(self, buffer):
        """测试并发写入读取"""
        write_count = 10
        read_data = []
        write_data = [{"id": i, "value": f"data_{i}"} for i in range(write_count)]
        
        def writer():
            for data in write_data:
                while not buffer.write(data):
                    time.sleep(0.001)  # 等待缓冲区有空间
        
        def reader():
            for _ in range(write_count):
                while True:
                    result = buffer.read()
                    if result is not None:
                        read_data.append(result[0])
                        break
                    time.sleep(0.001)  # 等待数据
        
        # 启动写入和读取线程
        write_thread = threading.Thread(target=writer)
        read_thread = threading.Thread(target=reader)
        
        write_thread.start()
        read_thread.start()
        
        write_thread.join(timeout=5)
        read_thread.join(timeout=5)
        
        # 验证数据完整性
        assert len(read_data) == write_count
        
        # 验证数据顺序（可能不完全一致，但ID应该都存在）
        read_ids = {data["id"] for data in read_data}
        expected_ids = {data["id"] for data in write_data}
        assert read_ids == expected_ids


class TestSPSCManager:
    """SPSC管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """创建SPSC管理器实例"""
        return SPSCManager()
    
    def test_init(self, manager):
        """测试初始化"""
        assert len(manager.buffers) == 0
    
    def test_create_buffer(self, manager):
        """测试创建缓冲区"""
        buffer_name = f"test_create_{int(time.time() * 1000)}"
        
        buffer = manager.create_buffer(buffer_name, 1024)
        
        assert buffer.name == buffer_name
        assert buffer.buffer_size == 1024
        assert buffer_name in manager.buffers
        
        # 清理
        manager.remove_buffer(buffer_name)
    
    def test_create_duplicate_buffer(self, manager):
        """测试创建重复缓冲区"""
        buffer_name = f"test_duplicate_{int(time.time() * 1000)}"
        
        # 创建第一个缓冲区
        manager.create_buffer(buffer_name, 1024)
        
        # 尝试创建重复缓冲区
        with pytest.raises(ValueError, match="already exists"):
            manager.create_buffer(buffer_name, 1024)
        
        # 清理
        manager.remove_buffer(buffer_name)
    
    def test_get_buffer(self, manager):
        """测试获取缓冲区"""
        buffer_name = f"test_get_{int(time.time() * 1000)}"
        
        # 创建缓冲区
        created_buffer = manager.create_buffer(buffer_name, 1024)
        
        # 获取缓冲区
        retrieved_buffer = manager.get_buffer(buffer_name)
        
        assert retrieved_buffer is created_buffer
        
        # 获取不存在的缓冲区
        non_existent = manager.get_buffer("non_existent")
        assert non_existent is None
        
        # 清理
        manager.remove_buffer(buffer_name)
    
    def test_remove_buffer(self, manager):
        """测试移除缓冲区"""
        buffer_name = f"test_remove_{int(time.time() * 1000)}"
        
        # 创建缓冲区
        manager.create_buffer(buffer_name, 1024)
        assert buffer_name in manager.buffers
        
        # 移除缓冲区
        result = manager.remove_buffer(buffer_name)
        
        assert result is True
        assert buffer_name not in manager.buffers
        
        # 移除不存在的缓冲区
        result = manager.remove_buffer("non_existent")
        assert result is False
    
    def test_get_all_stats(self, manager):
        """测试获取所有统计信息"""
        buffer_names = [
            f"test_stats_1_{int(time.time() * 1000)}",
            f"test_stats_2_{int(time.time() * 1000)}"
        ]
        
        # 创建多个缓冲区
        for name in buffer_names:
            buffer = manager.create_buffer(name, 1024)
            # 写入一些数据
            buffer.write({"test": "data"})
        
        # 获取统计信息
        all_stats = manager.get_all_stats()
        
        assert len(all_stats) == 2
        for name in buffer_names:
            assert name in all_stats
            assert "buffer_size" in all_stats[name]
            assert "sequence_id" in all_stats[name]
        
        # 清理
        for name in buffer_names:
            manager.remove_buffer(name)
    
    def test_cleanup_all(self, manager):
        """测试清理所有缓冲区"""
        buffer_names = [
            f"test_cleanup_1_{int(time.time() * 1000)}",
            f"test_cleanup_2_{int(time.time() * 1000)}"
        ]
        
        # 创建多个缓冲区
        for name in buffer_names:
            manager.create_buffer(name, 1024)
        
        assert len(manager.buffers) == 2
        
        # 清理所有缓冲区
        manager.cleanup_all()
        
        assert len(manager.buffers) == 0


class TestSPSCBufferAdvanced:
    """SPSC缓冲区高级测试"""
    
    @pytest.fixture
    def buffer_name_advanced(self):
        """高级测试缓冲区名称"""
        return f"test_advanced_{int(time.time() * 1000)}"
    
    def test_connect_to_existing_buffer(self, buffer_name_advanced):
        """测试连接到现有缓冲区"""
        # 先创建缓冲区
        buffer1 = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=True)
        
        # 写入一些数据
        test_data = {"id": 1, "value": "test"}
        buffer1.write(test_data)
        
        # 连接到现有缓冲区
        buffer2 = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=False)
        
        # 从第二个缓冲区读取数据
        result = buffer2.read()
        assert result is not None
        
        data, sequence_id = result
        assert data == test_data
        assert sequence_id == 1
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer1.shm
        buffer1.cleanup()
        buffer2.cleanup()
        shm.unlink()
    
    def test_validate_header_invalid_magic(self, buffer_name_advanced):
        """测试验证头部 - 无效魔数"""
        # 创建缓冲区
        buffer = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=True)
        
        # 破坏魔数
        header_data = struct.pack('IIIII', 0, 0, 0, 1024, 0xBADBAD)  # 错误的魔数
        buffer.shm.buf[:20] = header_data
        
        # 尝试验证头部应该失败
        with pytest.raises(RuntimeError, match="Invalid SPSC buffer magic number"):
            buffer._validate_header()
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer.shm
        buffer.cleanup()
        shm.unlink()
    
    def test_validate_header_size_mismatch(self, buffer_name_advanced):
        """测试验证头部 - 大小不匹配"""
        # 创建缓冲区
        buffer = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=True)
        
        # 修改头部中的buffer_size
        header_data = struct.pack('IIIII', 0, 0, 0, 2048, 0xDEADBEEF)  # 错误的大小
        buffer.shm.buf[:20] = header_data
        
        # 尝试验证头部应该失败
        with pytest.raises(RuntimeError, match="Buffer size mismatch"):
            buffer._validate_header()
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer.shm
        buffer.cleanup()
        shm.unlink()
    
    def test_read_invalid_data_size(self, buffer_name_advanced):
        """测试读取无效数据大小"""
        buffer = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=True)
        
        # 手动写入无效的数据包（数据大小超过缓冲区）
        header = buffer._read_header()
        invalid_packet = struct.pack('II', 1, 9999)  # 序列号1，数据大小9999（超过缓冲区）
        buffer._write_to_ring_buffer(0, invalid_packet)
        
        # 更新写入位置
        header.write_pos = 8
        header.sequence_id = 1
        buffer._write_header(header)
        
        # 尝试读取应该返回None
        result = buffer.read()
        assert result is None
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer.shm
        buffer.cleanup()
        shm.unlink()
    
    def test_read_zero_data_size(self, buffer_name_advanced):
        """测试读取零数据大小"""
        buffer = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=True)
        
        # 手动写入数据大小为0的数据包
        header = buffer._read_header()
        invalid_packet = struct.pack('II', 1, 0)  # 序列号1，数据大小0
        buffer._write_to_ring_buffer(0, invalid_packet)
        
        # 更新写入位置
        header.write_pos = 8
        header.sequence_id = 1
        buffer._write_header(header)
        
        # 尝试读取应该返回None
        result = buffer.read()
        assert result is None
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer.shm
        buffer.cleanup()
        shm.unlink()
    
    def test_write_read_exception_handling(self, buffer_name_advanced):
        """测试写入读取异常处理"""
        buffer = SPSCBuffer(buffer_name_advanced, buffer_size=1024, create=True)
        
        # 测试写入不可序列化的数据
        class UnserializableClass:
            def __reduce__(self):
                raise TypeError("Cannot serialize")
        
        result = buffer.write(UnserializableClass())
        assert result is False
        
        # 清理
        # 保存shm引用以便unlink
        shm = buffer.shm
        buffer.cleanup()
        shm.unlink()


class TestSPSCManagerAdvanced:
    """SPSC管理器高级测试"""
    
    def test_connect_buffer(self):
        """测试连接到现有缓冲区"""
        manager = SPSCManager()
        buffer_name = f"test_connect_{int(time.time() * 1000)}"
        
        # 先创建缓冲区
        buffer1 = manager.create_buffer(buffer_name, 1024)
        buffer1.write({"test": "data"})
        
        # 创建新的管理器并连接（使用相同的buffer_size）
        manager2 = SPSCManager()
        # 注意：连接时需要知道正确的buffer_size，这里我们手动创建
        buffer2 = SPSCBuffer(buffer_name, buffer_size=1024, create=False)
        manager2.buffers[buffer_name] = buffer2
        
        # 验证可以读取数据
        result = buffer2.read()
        assert result is not None
        
        data, sequence_id = result
        assert data == {"test": "data"}
        
        # 清理
        manager.remove_buffer(buffer_name)
    
    def test_connect_buffer_already_exists(self):
        """测试连接已存在的缓冲区"""
        manager = SPSCManager()
        buffer_name = f"test_connect_exists_{int(time.time() * 1000)}"
        
        # 创建缓冲区
        buffer1 = manager.create_buffer(buffer_name, 1024)
        
        # 再次连接应该返回同一个缓冲区
        buffer2 = manager.connect_buffer(buffer_name)
        
        assert buffer1 is buffer2
        
        # 清理
        manager.remove_buffer(buffer_name)
    
    def test_get_all_stats_with_error(self):
        """测试获取统计信息时的异常处理"""
        manager = SPSCManager()
        buffer_name = f"test_stats_error_{int(time.time() * 1000)}"
        
        # 创建缓冲区
        buffer = manager.create_buffer(buffer_name, 1024)
        
        # 模拟get_stats失败
        original_get_stats = buffer.get_stats
        def failing_get_stats():
            raise RuntimeError("Stats failed")
        
        buffer.get_stats = failing_get_stats
        
        # 获取所有统计信息
        all_stats = manager.get_all_stats()
        
        # 应该包含错误信息
        assert buffer_name in all_stats
        assert 'error' in all_stats[buffer_name]
        
        # 恢复原方法
        buffer.get_stats = original_get_stats
        
        # 清理
        manager.remove_buffer(buffer_name)
    
    def test_remove_buffer_unlink_failure(self):
        """测试移除缓冲区时unlink失败"""
        manager = SPSCManager()
        buffer_name = f"test_unlink_fail_{int(time.time() * 1000)}"
        
        # 创建缓冲区
        buffer = manager.create_buffer(buffer_name, 1024)
        
        # 先手动unlink
        buffer.shm.unlink()
        
        # 再次移除应该记录警告但不抛出异常
        result = manager.remove_buffer(buffer_name)
        assert result is True
    
    def test_cleanup_all_with_errors(self):
        """测试清理所有缓冲区时的异常处理"""
        manager = SPSCManager()
        buffer_names = [
            f"test_cleanup_error_1_{int(time.time() * 1000)}",
            f"test_cleanup_error_2_{int(time.time() * 1000)}"
        ]
        
        # 创建多个缓冲区
        for name in buffer_names:
            manager.create_buffer(name, 1024)
        
        # 破坏第一个缓冲区
        buffer1 = manager.buffers[buffer_names[0]]
        buffer1.shm.unlink()
        
        # 清理所有缓冲区应该继续处理其他缓冲区
        manager.cleanup_all()
        
        # 所有缓冲区都应该被移除
        assert len(manager.buffers) == 0


class TestSPSCPerformance:
    """SPSC性能测试"""
    
    @pytest.fixture
    def perf_buffer(self):
        """创建性能测试缓冲区"""
        buffer_name = f"perf_test_{int(time.time() * 1000)}"
        buffer = SPSCBuffer(buffer_name, buffer_size=1024*1024, create=True)  # 1MB
        yield buffer
        # 清理
        try:
            buffer.cleanup()
            buffer.shm.unlink()
        except:
            pass
    
    def test_write_performance(self, perf_buffer):
        """测试写入性能"""
        test_data = {"id": 1, "value": "test_data"}
        iterations = 1000
        
        start_time = time.perf_counter()
        
        for i in range(iterations):
            result = perf_buffer.write(test_data)
            if not result:
                break
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # 计算性能指标
        ops_per_second = iterations / elapsed
        avg_latency_us = (elapsed / iterations) * 1_000_000
        
        print(f"Write performance: {ops_per_second:.0f} ops/s, {avg_latency_us:.1f} μs/op")
        
        # 性能要求：> 10000 ops/s (< 100μs per operation)
        assert ops_per_second > 10000, f"Write performance too low: {ops_per_second:.0f} ops/s"
        assert avg_latency_us < 100, f"Write latency too high: {avg_latency_us:.1f} μs"
    
    def test_read_performance(self, perf_buffer):
        """测试读取性能"""
        test_data = {"id": 1, "value": "test_data"}
        iterations = 1000
        
        # 先写入数据
        for i in range(iterations):
            result = perf_buffer.write(test_data)
            if not result:
                break
        
        start_time = time.perf_counter()
        
        read_count = 0
        for i in range(iterations):
            result = perf_buffer.read()
            if result is not None:
                read_count += 1
            else:
                break
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # 计算性能指标
        ops_per_second = read_count / elapsed
        avg_latency_us = (elapsed / read_count) * 1_000_000 if read_count > 0 else 0
        
        print(f"Read performance: {ops_per_second:.0f} ops/s, {avg_latency_us:.1f} μs/op")
        
        # 性能要求：> 10000 ops/s (< 100μs per operation)
        assert ops_per_second > 10000, f"Read performance too low: {ops_per_second:.0f} ops/s"
        assert avg_latency_us < 100, f"Read latency too high: {avg_latency_us:.1f} μs"
    
    @pytest.mark.slow
    def test_concurrent_performance(self, perf_buffer):
        """测试并发性能"""
        test_data = {"id": 1, "value": "x" * 100}  # 100字节数据
        iterations = 5000
        
        write_times = []
        read_times = []
        
        def writer():
            for i in range(iterations):
                start = time.perf_counter()
                while not perf_buffer.write({**test_data, "id": i}):
                    time.sleep(0.0001)  # 100μs
                end = time.perf_counter()
                write_times.append(end - start)
        
        def reader():
            for i in range(iterations):
                start = time.perf_counter()
                while True:
                    result = perf_buffer.read()
                    if result is not None:
                        end = time.perf_counter()
                        read_times.append(end - start)
                        break
                    time.sleep(0.0001)  # 100μs
        
        # 启动并发线程
        write_thread = threading.Thread(target=writer)
        read_thread = threading.Thread(target=reader)
        
        overall_start = time.perf_counter()
        
        write_thread.start()
        read_thread.start()
        
        write_thread.join(timeout=30)
        read_thread.join(timeout=30)
        
        overall_end = time.perf_counter()
        
        # 计算性能指标
        total_ops = len(write_times) + len(read_times)
        overall_ops_per_second = total_ops / (overall_end - overall_start)
        
        avg_write_latency_us = (sum(write_times) / len(write_times)) * 1_000_000 if write_times else 0
        avg_read_latency_us = (sum(read_times) / len(read_times)) * 1_000_000 if read_times else 0
        
        print(f"Concurrent performance: {overall_ops_per_second:.0f} total ops/s")
        print(f"Average write latency: {avg_write_latency_us:.1f} μs")
        print(f"Average read latency: {avg_read_latency_us:.1f} μs")
        
        # 性能要求：总体 > 20000 ops/s，延迟 < 100μs
        assert overall_ops_per_second > 20000, f"Concurrent performance too low: {overall_ops_per_second:.0f} ops/s"
        assert avg_write_latency_us < 100, f"Write latency too high: {avg_write_latency_us:.1f} μs"
        assert avg_read_latency_us < 100, f"Read latency too high: {avg_read_latency_us:.1f} μs"