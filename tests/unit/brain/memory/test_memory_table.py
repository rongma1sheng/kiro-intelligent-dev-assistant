"""MemoryTable单元测试

白皮书依据: 第二章 2.8.1 RAM/SSD记忆表
"""

import pytest
import numpy as np
import os
import tempfile
from src.brain.memory.memory_table import RAMMemoryTable, SSDMemoryTable


class TestRAMMemoryTable:
    """RAMMemoryTable单元测试类"""
    
    @pytest.fixture
    def table(self):
        """测试夹具 - 创建RAM记忆表"""
        return RAMMemoryTable(size=100, embedding_dim=64)
    
    def test_initialization_success(self):
        """测试初始化 - 正常情况"""
        table = RAMMemoryTable(size=100, embedding_dim=64)
        
        assert table.size == 100
        assert table.embedding_dim == 64
        assert table.memory_table.shape == (100, 64)
        assert table.occupied.shape == (100,)
    
    def test_initialization_invalid_size(self):
        """测试初始化 - 无效大小"""
        with pytest.raises(ValueError, match="记忆表大小必须 > 0"):
            RAMMemoryTable(size=0, embedding_dim=64)
        
        with pytest.raises(ValueError, match="记忆表大小必须 > 0"):
            RAMMemoryTable(size=-10, embedding_dim=64)
    
    def test_initialization_invalid_embedding_dim(self):
        """测试初始化 - 无效嵌入维度"""
        with pytest.raises(ValueError, match="嵌入向量维度必须 > 0"):
            RAMMemoryTable(size=100, embedding_dim=0)
        
        with pytest.raises(ValueError, match="嵌入向量维度必须 > 0"):
            RAMMemoryTable(size=100, embedding_dim=-5)
    
    def test_get_empty_slot(self, table):
        """测试获取 - 空槽位"""
        result = table.get(address=0)
        assert result is None
    
    def test_set_and_get(self, table):
        """测试设置和获取 - 正常情况"""
        embedding = np.random.randn(64).astype(np.float32)
        
        table.set(address=0, embedding=embedding)
        retrieved = table.get(address=0)
        
        assert retrieved is not None
        np.testing.assert_array_almost_equal(retrieved, embedding)
    
    def test_set_invalid_address(self, table):
        """测试设置 - 无效地址"""
        embedding = np.random.randn(64).astype(np.float32)
        
        with pytest.raises(ValueError, match="地址超出范围"):
            table.set(address=-1, embedding=embedding)
        
        with pytest.raises(ValueError, match="地址超出范围"):
            table.set(address=100, embedding=embedding)
    
    def test_get_invalid_address(self, table):
        """测试获取 - 无效地址"""
        with pytest.raises(ValueError, match="地址超出范围"):
            table.get(address=-1)
        
        with pytest.raises(ValueError, match="地址超出范围"):
            table.get(address=100)
    
    def test_set_wrong_dimension(self, table):
        """测试设置 - 错误维度"""
        wrong_embedding = np.random.randn(32).astype(np.float32)  # 应该是64
        
        with pytest.raises(ValueError, match="嵌入向量维度不匹配"):
            table.set(address=0, embedding=wrong_embedding)
    
    def test_overwrite_existing(self, table):
        """测试覆盖已存在的记忆"""
        embedding1 = np.ones(64, dtype=np.float32)
        embedding2 = np.ones(64, dtype=np.float32) * 2
        
        table.set(address=0, embedding=embedding1)
        table.set(address=0, embedding=embedding2)
        
        retrieved = table.get(address=0)
        np.testing.assert_array_almost_equal(retrieved, embedding2)
    
    def test_multiple_slots(self, table):
        """测试多个槽位"""
        embeddings = {
            0: np.ones(64, dtype=np.float32),
            5: np.ones(64, dtype=np.float32) * 2,
            99: np.ones(64, dtype=np.float32) * 3
        }
        
        for addr, emb in embeddings.items():
            table.set(address=addr, embedding=emb)
        
        for addr, emb in embeddings.items():
            retrieved = table.get(address=addr)
            np.testing.assert_array_almost_equal(retrieved, emb)
    
    def test_get_usage_stats(self, table):
        """测试获取使用统计"""
        # 初始状态
        stats = table.get_usage_stats()
        assert stats['total_slots'] == 100
        assert stats['occupied_slots'] == 0
        assert stats['usage_rate'] == 0.0
        assert stats['backend'] == 'ram'
        
        # 添加一些记忆
        for i in range(10):
            embedding = np.random.randn(64).astype(np.float32)
            table.set(address=i, embedding=embedding)
        
        stats = table.get_usage_stats()
        assert stats['occupied_slots'] == 10
        assert stats['usage_rate'] == 0.1
    
    def test_get_returns_copy(self, table):
        """测试获取返回副本（不是引用）"""
        embedding = np.ones(64, dtype=np.float32)
        table.set(address=0, embedding=embedding)
        
        retrieved1 = table.get(address=0)
        retrieved2 = table.get(address=0)
        
        # 修改retrieved1不应影响retrieved2
        retrieved1[0] = 999
        
        assert retrieved2[0] == 1.0


class TestSSDMemoryTable:
    """SSDMemoryTable单元测试类"""
    
    @pytest.fixture
    def temp_file(self):
        """测试夹具 - 创建临时文件"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            temp_path = f.name
        yield temp_path
        # 清理 - 等待一下确保文件被释放
        import time
        time.sleep(0.1)
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except PermissionError:
            # Windows上可能文件还在使用中，忽略
            pass
    
    @pytest.fixture
    def table(self, temp_file):
        """测试夹具 - 创建SSD记忆表"""
        return SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file, cache_size=10)
    
    def test_initialization_success(self, temp_file):
        """测试初始化 - 正常情况"""
        table = SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file)
        
        assert table.size == 100
        assert table.embedding_dim == 64
        assert os.path.exists(temp_file)
    
    def test_initialization_invalid_size(self, temp_file):
        """测试初始化 - 无效大小"""
        with pytest.raises(ValueError, match="记忆表大小必须 > 0"):
            SSDMemoryTable(size=0, embedding_dim=64, file_path=temp_file)
    
    def test_initialization_invalid_embedding_dim(self, temp_file):
        """测试初始化 - 无效嵌入维度"""
        with pytest.raises(ValueError, match="嵌入向量维度必须 > 0"):
            SSDMemoryTable(size=100, embedding_dim=0, file_path=temp_file)
    
    def test_get_empty_slot(self, table):
        """测试获取 - 空槽位"""
        result = table.get(address=0)
        assert result is None
    
    def test_set_and_get(self, table):
        """测试设置和获取 - 正常情况"""
        embedding = np.random.randn(64).astype(np.float32)
        
        table.set(address=0, embedding=embedding)
        retrieved = table.get(address=0)
        
        assert retrieved is not None
        np.testing.assert_array_almost_equal(retrieved, embedding, decimal=5)
    
    def test_set_invalid_address(self, table):
        """测试设置 - 无效地址"""
        embedding = np.random.randn(64).astype(np.float32)
        
        with pytest.raises(ValueError, match="地址超出范围"):
            table.set(address=-1, embedding=embedding)
        
        with pytest.raises(ValueError, match="地址超出范围"):
            table.set(address=100, embedding=embedding)
    
    def test_get_invalid_address(self, table):
        """测试获取 - 无效地址"""
        with pytest.raises(ValueError, match="地址超出范围"):
            table.get(address=-1)
        
        with pytest.raises(ValueError, match="地址超出范围"):
            table.get(address=100)
    
    def test_set_wrong_dimension(self, table):
        """测试设置 - 错误维度"""
        wrong_embedding = np.random.randn(32).astype(np.float32)
        
        with pytest.raises(ValueError, match="嵌入向量维度不匹配"):
            table.set(address=0, embedding=wrong_embedding)
    
    def test_cache_hit(self, table):
        """测试缓存命中"""
        embedding = np.random.randn(64).astype(np.float32)
        
        table.set(address=0, embedding=embedding)
        
        # 第一次获取 - 从SSD读取（缓存未命中）
        result1 = table.get(address=0)
        initial_misses = table.cache_misses
        
        # 第二次获取 - 从缓存读取（缓存命中）
        result2 = table.get(address=0)
        
        # 验证缓存命中
        assert table.cache_hits >= 1
        assert table.cache_misses == initial_misses  # 未命中次数不应增加
    
    def test_cache_eviction(self, table):
        """测试缓存淘汰"""
        # 填充超过缓存大小的数据
        for i in range(15):  # cache_size=10
            embedding = np.random.randn(64).astype(np.float32)
            table.set(address=i, embedding=embedding)
        
        # 缓存应该只保留最近的10个
        assert len(table.cache) <= table.cache_size
    
    def test_get_usage_stats(self, table):
        """测试获取使用统计"""
        stats = table.get_usage_stats()
        
        assert stats['total_slots'] == 100
        assert stats['backend'] == 'ssd'
        assert 'file_size_mb' in stats
        assert 'cache_hit_rate' in stats
        
        # 添加一些数据以确保采样能找到occupied槽位（覆盖行332）
        # 由于采样步长是 max(1, size // sample_size)，对于size=100，步长是1
        # 所以我们在索引0处设置数据，确保被采样到
        embedding = np.random.randn(64).astype(np.float32)
        table.set(address=0, embedding=embedding)
        
        stats = table.get_usage_stats()
        # 现在应该有occupied_count > 0
        assert stats['occupied_slots'] > 0
    
    def test_persistence(self, temp_file):
        """测试持久化 - 数据在重新打开后仍然存在"""
        embedding = np.random.randn(64).astype(np.float32)
        
        # 第一个表实例
        table1 = SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file)
        table1.set(address=0, embedding=embedding)
        del table1  # 关闭
        
        # 第二个表实例
        table2 = SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file)
        retrieved = table2.get(address=0)
        
        assert retrieved is not None
        np.testing.assert_array_almost_equal(retrieved, embedding, decimal=5)
    
    def test_destructor_cleanup(self, temp_file):
        """测试析构函数清理资源（覆盖行332）"""
        table = SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file)
        
        # 确保对象有memory_map和file属性
        assert hasattr(table, 'memory_map')
        assert hasattr(table, 'file')
        
        # 保存file对象的引用
        file_obj = table.file
        
        # 显式调用__del__来确保覆盖
        table.__del__()
        
        # 验证file已经关闭
        assert file_obj.closed
        
        # 文件应该仍然存在（只是关闭了）
        assert os.path.exists(temp_file)
    
    def test_destructor_without_attributes(self, temp_file):
        """测试析构函数 - 对象没有完整属性（覆盖行332的hasattr检查）"""
        table = SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file)
        
        # 先关闭并删除memory_map
        if hasattr(table, 'memory_map'):
            table.memory_map.close()
            delattr(table, 'memory_map')
        
        # 调用__del__应该仍然关闭file
        table.__del__()
        
        # 验证file已经关闭
        assert table.file.closed
        
        # 文件应该仍然存在
        assert os.path.exists(temp_file)
    
    def test_windows_mmap_fallback(self, temp_file, monkeypatch):
        """测试Windows mmap fallback（覆盖行210-212）"""
        import mmap
        
        # Mock mmap.mmap to raise ValueError on first call (模拟Windows行为)
        original_mmap = mmap.mmap
        call_count = [0]
        
        def mock_mmap(fileno, length, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1 and length == 0:
                # 第一次调用（length=0）抛出ValueError
                raise ValueError("Windows requires explicit length")
            # 第二次调用（带显式长度）成功
            return original_mmap(fileno, length, *args, **kwargs)
        
        monkeypatch.setattr('mmap.mmap', mock_mmap)
        
        # 创建表应该触发fallback逻辑
        table = SSDMemoryTable(size=100, embedding_dim=64, file_path=temp_file)
        
        # 验证mmap被调用了两次（第一次失败，第二次成功）
        assert call_count[0] == 2
        
        # 验证表仍然可以正常工作
        embedding = np.random.randn(64).astype(np.float32)
        table.set(address=0, embedding=embedding)
        retrieved = table.get(address=0)
        assert retrieved is not None
