"""DeterministicHashRouter单元测试

白皮书依据: 第二章 2.8.1 确定性哈希路由
"""

import pytest
from src.brain.memory.hash_router import DeterministicHashRouter


class TestDeterministicHashRouter:
    """DeterministicHashRouter单元测试类"""
    
    @pytest.fixture
    def router(self):
        """测试夹具 - 创建路由器实例"""
        return DeterministicHashRouter(memory_size=1000)
    
    def test_initialization_success(self):
        """测试初始化 - 正常情况"""
        router = DeterministicHashRouter(memory_size=1000)
        assert router.memory_size == 1000
        assert router.hash_function is not None
    
    def test_initialization_invalid_size(self):
        """测试初始化 - 无效大小"""
        with pytest.raises(ValueError, match="记忆表大小必须 > 0"):
            DeterministicHashRouter(memory_size=0)
        
        with pytest.raises(ValueError, match="记忆表大小必须 > 0"):
            DeterministicHashRouter(memory_size=-100)
    
    def test_hash_deterministic(self, router):
        """测试哈希确定性 - 相同输入得到相同输出"""
        ngram = "hello world test ngram"
        
        hash1 = router.hash(ngram)
        hash2 = router.hash(ngram)
        hash3 = router.hash(ngram)
        
        assert hash1 == hash2 == hash3
    
    def test_hash_range(self, router):
        """测试哈希范围 - 输出在有效范围内"""
        ngrams = [
            "test ngram 1",
            "test ngram 2",
            "another test",
            "hello world",
            "machine learning"
        ]
        
        for ngram in ngrams:
            hash_value = router.hash(ngram)
            assert 0 <= hash_value < router.memory_size
    
    def test_hash_empty_string(self, router):
        """测试哈希 - 空字符串"""
        with pytest.raises(ValueError, match="N-gram不能为空"):
            router.hash("")
    
    def test_hash_different_inputs(self, router):
        """测试哈希 - 不同输入得到不同输出（大概率）"""
        ngram1 = "hello world"
        ngram2 = "world hello"
        
        hash1 = router.hash(ngram1)
        hash2 = router.hash(ngram2)
        
        # 不同输入应该得到不同哈希值（虽然理论上可能碰撞）
        assert hash1 != hash2
    
    def test_hash_batch(self, router):
        """测试批量哈希"""
        ngrams = ["test 1", "test 2", "test 3"]
        
        hashes = router.hash_batch(ngrams)
        
        assert len(hashes) == len(ngrams)
        for hash_value in hashes:
            assert 0 <= hash_value < router.memory_size
    
    def test_hash_batch_empty_list(self, router):
        """测试批量哈希 - 空列表"""
        hashes = router.hash_batch([])
        assert hashes == []
    
    def test_verify_distribution_success(self, router):
        """测试分布验证 - 正常情况"""
        # 生成大量样本
        sample_ngrams = [f"test ngram {i}" for i in range(1000)]
        
        stats = router.verify_distribution(sample_ngrams)
        
        assert stats['sample_size'] == 1000
        assert 0 <= stats['unique_addresses'] <= 1000
        assert 0 <= stats['collision_rate'] <= 1.0
        assert 0 <= stats['uniformity'] <= 1.0
        assert stats['avg_per_bucket'] > 0
        assert stats['std_dev'] >= 0
    
    def test_verify_distribution_empty_list(self, router):
        """测试分布验证 - 空列表"""
        with pytest.raises(ValueError, match="样本N-gram列表不能为空"):
            router.verify_distribution([])
    
    def test_verify_distribution_uniformity(self):
        """测试分布验证 - 均匀性"""
        # 使用大内存空间测试均匀性
        router = DeterministicHashRouter(memory_size=100000)
        
        # 生成大量样本
        sample_ngrams = [f"test ngram {i}" for i in range(10000)]
        
        stats = router.verify_distribution(sample_ngrams)
        
        # SHA256应该有很好的均匀性
        assert stats['uniformity'] > 0.8  # 均匀性应该很高
        assert stats['collision_rate'] < 0.2  # 碰撞率应该很低
    
    def test_hash_unicode(self, router):
        """测试哈希 - Unicode字符"""
        ngrams = [
            "你好 世界",
            "こんにちは 世界",
            "مرحبا العالم",
            "Привет мир"
        ]
        
        for ngram in ngrams:
            hash_value = router.hash(ngram)
            assert 0 <= hash_value < router.memory_size
    
    def test_hash_special_characters(self, router):
        """测试哈希 - 特殊字符"""
        ngrams = [
            "test@#$%",
            "hello\nworld",
            "tab\tseparated",
            "quote'test"
        ]
        
        for ngram in ngrams:
            hash_value = router.hash(ngram)
            assert 0 <= hash_value < router.memory_size
    
    def test_hash_long_string(self, router):
        """测试哈希 - 长字符串"""
        long_ngram = "test " * 1000  # 5000字符
        
        hash_value = router.hash(long_ngram)
        assert 0 <= hash_value < router.memory_size
    
    def test_hash_consistency_across_instances(self):
        """测试哈希一致性 - 不同实例相同结果"""
        router1 = DeterministicHashRouter(memory_size=1000)
        router2 = DeterministicHashRouter(memory_size=1000)
        
        ngram = "test consistency"
        
        hash1 = router1.hash(ngram)
        hash2 = router2.hash(ngram)
        
        assert hash1 == hash2
