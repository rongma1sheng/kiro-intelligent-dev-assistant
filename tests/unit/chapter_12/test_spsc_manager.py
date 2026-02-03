"""SPSCManager单元测试

白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

测试覆盖:
- 初始化验证
- 原子读写
- 撕裂读检测
- 上下文管理器
- 清理机制
"""

import pytest
import struct
import threading
from unittest.mock import Mock, patch, MagicMock

from src.infra.spsc_manager import (
    SPSCManager,
    SPSCStats,
    get_spsc_manager,
    cleanup_all_managers,
    SHARED_MEMORY_AVAILABLE
)


class TestSPSCStats:
    """SPSCStats统计测试"""
    
    def test_default_stats(self):
        """测试默认统计"""
        stats = SPSCStats()
        
        assert stats.total_writes == 0
        assert stats.total_reads == 0
        assert stats.torn_reads == 0
        assert stats.avg_write_latency_us == 0.0
        assert stats.avg_read_latency_us == 0.0
    
    def test_record_write(self):
        """测试记录写入"""
        stats = SPSCStats()
        
        stats.record_write(10.0)
        stats.record_write(20.0)
        
        assert stats.total_writes == 2
        assert stats.avg_write_latency_us == 15.0
    
    def test_record_read_success(self):
        """测试记录成功读取"""
        stats = SPSCStats()
        
        stats.record_read(5.0)
        stats.record_read(15.0)
        
        assert stats.total_reads == 2
        assert stats.torn_reads == 0
        assert stats.avg_read_latency_us == 10.0
    
    def test_record_read_torn(self):
        """测试记录撕裂读"""
        stats = SPSCStats()
        
        stats.record_read(5.0, is_torn=True)
        
        assert stats.total_reads == 1
        assert stats.torn_reads == 1
        # 撕裂读不计入平均延迟
        assert stats.avg_read_latency_us == 0.0
    
    def test_latency_window_limit(self):
        """测试延迟窗口限制"""
        stats = SPSCStats()
        
        # 记录超过100次
        for i in range(150):
            stats.record_write(float(i))
        
        # 窗口应该只保留最近100个
        assert len(stats._write_latencies) == 100


class TestSPSCManagerInit:
    """SPSCManager初始化测试"""
    
    def test_init_invalid_name(self):
        """测试无效的名称"""
        with pytest.raises(ValueError, match="共享内存名称不能为空"):
            SPSCManager("", 1024)
    
    def test_init_invalid_size(self):
        """测试无效的大小"""
        # HEADER_SIZE + FOOTER_SIZE = 20
        with pytest.raises(ValueError, match="共享内存大小必须"):
            SPSCManager("test", 10)
    
    def test_init_mock_mode(self):
        """测试模拟模式初始化"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_mock", 1024, create=True)
            
            assert manager.name == "test_mock"
            assert manager.size == 1024
            assert manager.is_producer is True
            assert hasattr(manager, '_mock_buffer')
            
            manager.cleanup()
    
    @pytest.mark.skipif(not SHARED_MEMORY_AVAILABLE, reason="SharedMemory not available")
    def test_init_create_mode(self):
        """测试创建模式初始化"""
        import uuid
        name = f"test_spsc_{uuid.uuid4().hex[:8]}"
        
        try:
            manager = SPSCManager(name, 1024, create=True)
            
            assert manager.name == name
            assert manager.size == 1024
            assert manager.is_producer is True
            assert manager.shm is not None
        finally:
            manager.cleanup()


class TestSPSCManagerContextManager:
    """SPSCManager上下文管理器测试"""
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            with SPSCManager("test_ctx", 1024, create=True) as manager:
                assert manager.name == "test_ctx"
                assert manager._cleaned is False
            
            # 退出后应该已清理
            assert manager._cleaned is True


class TestSPSCManagerCleanup:
    """SPSCManager清理测试"""
    
    def test_cleanup_mock_mode(self):
        """测试模拟模式清理"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_cleanup", 1024, create=True)
            
            manager.cleanup()
            
            assert manager._cleaned is True
    
    def test_cleanup_idempotent(self):
        """测试清理幂等性"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_idem", 1024, create=True)
            
            manager.cleanup()
            manager.cleanup()  # 第二次调用不应出错
            
            assert manager._cleaned is True


class TestSPSCManagerAtomicWrite:
    """SPSCManager原子写入测试"""
    
    def test_atomic_write_mock_mode(self):
        """测试模拟模式原子写入"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_write", 1024, create=True)
            
            result = manager.atomic_write({'key': 'value'})
            
            assert result is True
            assert manager.stats.total_writes == 1
            
            manager.cleanup()
    
    def test_atomic_write_data_too_large(self):
        """测试数据过大"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_large", 50, create=True)
            
            # 尝试写入大数据
            large_data = "x" * 100
            result = manager.atomic_write(large_data)
            
            assert result is False
            
            manager.cleanup()
    
    def test_atomic_write_no_buffer(self):
        """测试无缓冲区"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_nobuf", 1024, create=True)
            
            # 删除mock缓冲区
            delattr(manager, '_mock_buffer')
            manager.shm = None
            
            result = manager.atomic_write({'key': 'value'})
            
            assert result is False


class TestSPSCManagerAtomicRead:
    """SPSCManager原子读取测试"""
    
    def test_atomic_read_mock_mode(self):
        """测试模拟模式原子读取"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_read", 1024, create=True)
            
            # 先写入
            manager.atomic_write("test_data")
            
            # 再读取
            result = manager.atomic_read()
            
            assert result == "test_data"
            assert manager.stats.total_reads == 1
            
            manager.cleanup()
    
    def test_atomic_read_no_buffer(self):
        """测试无缓冲区"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_nobuf_read", 1024, create=True)
            
            # 删除mock缓冲区
            delattr(manager, '_mock_buffer')
            manager.shm = None
            
            result = manager.atomic_read()
            
            assert result is None
    
    def test_atomic_read_invalid_length(self):
        """测试无效的数据长度"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_invalid", 1024, create=True)
            
            # 写入无效的长度
            buf = manager._get_buffer()
            struct.pack_into('Q', buf, 0, 12345)  # seq_id
            struct.pack_into('I', buf, 8, 0)  # data_len = 0
            
            result = manager.atomic_read()
            
            assert result is None
            
            manager.cleanup()
    
    def test_atomic_read_torn_detection(self):
        """测试撕裂读检测"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_torn", 1024, create=True)
            
            # 写入不一致的序列ID
            buf = manager._get_buffer()
            seq_id_start = 12345
            seq_id_end = 67890  # 不同的序列ID
            data = b"test"
            
            struct.pack_into('Q', buf, 0, seq_id_start)
            struct.pack_into('I', buf, 8, len(data))
            buf[12:12 + len(data)] = data
            struct.pack_into('Q', buf, 12 + len(data), seq_id_end)
            
            result = manager.atomic_read()
            
            assert result is None
            assert manager.stats.torn_reads == 1
            
            manager.cleanup()


class TestSPSCManagerGetters:
    """SPSCManager getter方法测试"""
    
    def test_get_stats(self):
        """测试获取统计"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_stats", 1024, create=True)
            manager.stats.total_writes = 10
            
            stats = manager.get_stats()
            
            assert stats.total_writes == 10
            
            manager.cleanup()
    
    def test_is_available_true(self):
        """测试可用性检查（可用）"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_avail", 1024, create=True)
            
            assert manager.is_available() is True
            
            manager.cleanup()
    
    def test_is_available_false(self):
        """测试可用性检查（不可用）"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_unavail", 1024, create=True)
            
            # 删除mock缓冲区
            delattr(manager, '_mock_buffer')
            manager.shm = None
            
            assert manager.is_available() is False
    
    def test_get_name(self):
        """测试获取名称"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_name", 1024, create=True)
            
            assert manager.get_name() == "test_name"
            
            manager.cleanup()
    
    def test_get_size(self):
        """测试获取大小"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_size", 2048, create=True)
            
            assert manager.get_size() == 2048
            
            manager.cleanup()


class TestSPSCManagerGetBuffer:
    """SPSCManager缓冲区获取测试"""
    
    def test_get_buffer_mock(self):
        """测试获取模拟缓冲区"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_buf", 1024, create=True)
            
            buf = manager._get_buffer()
            
            assert buf is not None
            assert len(buf) == 1024
            
            manager.cleanup()
    
    def test_get_buffer_none(self):
        """测试获取空缓冲区"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_none", 1024, create=True)
            
            # 删除所有缓冲区
            delattr(manager, '_mock_buffer')
            manager.shm = None
            
            buf = manager._get_buffer()
            
            assert buf is None


class TestGlobalSPSCManager:
    """全局SPSC管理器测试"""
    
    def setup_method(self):
        """每个测试前清理"""
        cleanup_all_managers()
    
    def teardown_method(self):
        """每个测试后清理"""
        cleanup_all_managers()
    
    def test_get_spsc_manager_singleton(self):
        """测试全局管理器单例"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager1 = get_spsc_manager("test_singleton", 1024, create=True)
            manager2 = get_spsc_manager("test_singleton", 1024, create=True)
            
            assert manager1 is manager2
    
    def test_get_spsc_manager_different_names(self):
        """测试不同名称的管理器"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager1 = get_spsc_manager("test_a", 1024, create=True)
            manager2 = get_spsc_manager("test_b", 1024, create=True)
            
            assert manager1 is not manager2
    
    def test_cleanup_all_managers(self):
        """测试清理所有管理器"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager1 = get_spsc_manager("test_clean1", 1024, create=True)
            manager2 = get_spsc_manager("test_clean2", 1024, create=True)
            
            cleanup_all_managers()
            
            assert manager1._cleaned is True
            assert manager2._cleaned is True


class TestSPSCManagerRoundTrip:
    """SPSCManager往返测试"""
    
    def test_write_read_roundtrip(self):
        """测试写入读取往返"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_roundtrip", 1024, create=True)
            
            test_data = "hello world"
            
            # 写入
            write_result = manager.atomic_write(test_data)
            assert write_result is True
            
            # 读取
            read_result = manager.atomic_read()
            assert read_result == test_data
            
            manager.cleanup()
    
    def test_multiple_writes_reads(self):
        """测试多次写入读取"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_multi", 1024, create=True)
            
            for i in range(10):
                test_data = f"data_{i}"
                
                write_result = manager.atomic_write(test_data)
                assert write_result is True
                
                read_result = manager.atomic_read()
                assert read_result == test_data
            
            assert manager.stats.total_writes == 10
            assert manager.stats.total_reads == 10
            
            manager.cleanup()


class TestSPSCManagerThreadSafety:
    """SPSCManager线程安全测试"""
    
    def test_concurrent_writes(self):
        """测试并发写入"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_concurrent", 1024, create=True)
            errors = []
            
            def write_data(data):
                try:
                    for _ in range(10):
                        manager.atomic_write(data)
                except Exception as e:
                    errors.append(e)
            
            threads = [
                threading.Thread(target=write_data, args=(f"data_{i}",))
                for i in range(5)
            ]
            
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0
            assert manager.stats.total_writes == 50
            
            manager.cleanup()



class TestSPSCManagerExceptions:
    """SPSCManager异常测试"""
    
    def test_atomic_write_exception(self):
        """测试原子写入异常"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_write_exc", 1024, create=True)
            
            # Mock _get_buffer返回一个会导致异常的对象
            with patch.object(manager, '_get_buffer', side_effect=Exception("Buffer error")):
                result = manager.atomic_write("test")
            
            assert result is False
            
            manager.cleanup()
    
    def test_atomic_read_exception(self):
        """测试原子读取异常"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_read_exc", 1024, create=True)
            
            # Mock _get_buffer返回一个会导致异常的对象
            with patch.object(manager, '_get_buffer', side_effect=Exception("Buffer error")):
                result = manager.atomic_read()
            
            assert result is None
            
            manager.cleanup()


class TestSPSCManagerSharedMemoryMode:
    """SPSCManager共享内存模式测试"""
    
    @pytest.mark.skipif(not SHARED_MEMORY_AVAILABLE, reason="SharedMemory not available")
    def test_cleanup_shm_exception(self):
        """测试清理共享内存异常"""
        import uuid
        name = f"test_cleanup_exc_{uuid.uuid4().hex[:8]}"
        
        manager = SPSCManager(name, 1024, create=True)
        
        # Mock close抛出异常
        original_shm = manager.shm
        mock_shm = Mock()
        mock_shm.close.side_effect = Exception("Close error")
        manager.shm = mock_shm
        
        # 不应抛出异常
        manager.cleanup()
        
        assert manager._cleaned is True
        
        # 清理原始共享内存
        try:
            original_shm.close()
            original_shm.unlink()
        except Exception:
            pass


class TestSPSCManagerDataLengthValidation:
    """SPSCManager数据长度验证测试"""
    
    def test_atomic_read_data_length_too_large(self):
        """测试数据长度过大"""
        with patch('src.infra.spsc_manager.SHARED_MEMORY_AVAILABLE', False):
            manager = SPSCManager("test_large_len", 100, create=True)
            
            # 写入一个过大的长度值
            buf = manager._get_buffer()
            struct.pack_into('Q', buf, 0, 12345)  # seq_id
            struct.pack_into('I', buf, 8, 1000)  # data_len > size
            
            result = manager.atomic_read()
            
            assert result is None
            
            manager.cleanup()
