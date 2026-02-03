"""EngramMemory单元测试

白皮书依据: 第二章 2.8.1 Engram记忆模块
"""

import pytest
import numpy as np
from src.brain.memory.engram_memory import EngramMemory
from src.brain.memory.data_models import MemoryStatistics


class TestEngramMemory:
    """EngramMemory单元测试类"""
    
    @pytest.fixture
    def memory(self):
        """测试夹具 - 创建Engram记忆实例"""
        return EngramMemory(
            ngram_size=4,
            embedding_dim=64,
            memory_size=1000,
            storage_backend='ram'
        )
    
    def test_initialization_success(self):
        """测试初始化 - 正常情况"""
        memory = EngramMemory(
            ngram_size=4,
            embedding_dim=64,
            memory_size=1000,
            storage_backend='ram'
        )
        
        assert memory.ngram_size == 4
        assert memory.embedding_dim == 64
        assert memory.memory_size == 1000
        assert memory.storage_backend == 'ram'
        assert memory.hash_router is not None
        assert memory.memory_table is not None
    
    def test_initialization_invalid_ngram_size(self):
        """测试初始化 - 无效N-gram大小"""
        with pytest.raises(ValueError, match="N-gram大小必须 > 0"):
            EngramMemory(ngram_size=0, embedding_dim=64, memory_size=1000)
        
        with pytest.raises(ValueError, match="N-gram大小必须 > 0"):
            EngramMemory(ngram_size=-1, embedding_dim=64, memory_size=1000)
    
    def test_initialization_invalid_embedding_dim(self):
        """测试初始化 - 无效嵌入维度"""
        with pytest.raises(ValueError, match="嵌入向量维度必须 > 0"):
            EngramMemory(ngram_size=4, embedding_dim=0, memory_size=1000)
    
    def test_initialization_invalid_memory_size(self):
        """测试初始化 - 无效记忆大小"""
        with pytest.raises(ValueError, match="记忆表大小必须 > 0"):
            EngramMemory(ngram_size=4, embedding_dim=64, memory_size=0)
    
    def test_initialization_invalid_storage_backend(self):
        """测试初始化 - 无效存储后端"""
        with pytest.raises(ValueError, match="不支持的存储后端"):
            EngramMemory(
                ngram_size=4,
                embedding_dim=64,
                memory_size=1000,
                storage_backend='invalid'
            )
    
    def test_store_and_query_memory(self, memory):
        """测试存储和查询 - 正常情况"""
        text = "this is a test sentence"
        context = ["previous sentence"]
        embedding = np.random.randn(64).astype(np.float32)
        
        # 存储记忆
        memory.store_memory(text, context, embedding)
        
        # 查询记忆
        retrieved = memory.query_memory(text, context)
        
        assert retrieved is not None
        assert retrieved.shape == (64,)
    
    def test_store_memory_empty_text(self, memory):
        """测试存储 - 空文本"""
        embedding = np.random.randn(64).astype(np.float32)
        
        with pytest.raises(ValueError, match="文本内容不能为空"):
            memory.store_memory("", [], embedding)
    
    def test_store_memory_wrong_dimension(self, memory):
        """测试存储 - 错误维度"""
        text = "test sentence"
        wrong_embedding = np.random.randn(32).astype(np.float32)  # 应该是64
        
        with pytest.raises(ValueError, match="嵌入向量维度不匹配"):
            memory.store_memory(text, [], wrong_embedding)
    
    def test_query_memory_empty_text(self, memory):
        """测试查询 - 空文本"""
        with pytest.raises(ValueError, match="查询文本不能为空"):
            memory.query_memory("")
    
    def test_query_memory_not_found(self, memory):
        """测试查询 - 未找到"""
        result = memory.query_memory("nonexistent text")
        assert result is None
    
    def test_extract_ngrams_normal(self, memory):
        """测试N-gram提取 - 正常情况"""
        text = "this is a test sentence"
        ngrams = memory._extract_ngrams(text, None)
        
        assert len(ngrams) > 0
        # 对于"this is a test sentence"（5个词），4-gram应该产生2个N-gram
        assert len(ngrams) == 2
    
    def test_extract_ngrams_with_context(self, memory):
        """测试N-gram提取 - 带上下文"""
        text = "current sentence"
        context = ["context 1", "context 2", "context 3", "context 4"]
        
        ngrams = memory._extract_ngrams(text, context)
        
        # 应该包含上下文（最近3句）
        assert len(ngrams) > 0
    
    def test_extract_ngrams_short_text(self, memory):
        """测试N-gram提取 - 短文本"""
        text = "hi"  # 只有1个词，少于ngram_size=4
        ngrams = memory._extract_ngrams(text, None)
        
        # 应该返回整个文本作为一个N-gram
        assert len(ngrams) == 1
        assert ngrams[0] == "hi"
    
    def test_extract_ngrams_empty_text(self, memory):
        """测试N-gram提取 - 空文本"""
        ngrams = memory._extract_ngrams("", None)
        assert ngrams == []
    
    def test_tokenize_normal(self, memory):
        """测试分词 - 正常情况"""
        text = "this is a test"
        tokens = memory._tokenize(text)
        
        assert tokens == ["this", "is", "a", "test"]
    
    def test_tokenize_multiple_spaces(self, memory):
        """测试分词 - 多个空格"""
        text = "this  is   a    test"
        tokens = memory._tokenize(text)
        
        assert tokens == ["this", "is", "a", "test"]
    
    def test_tokenize_leading_trailing_spaces(self, memory):
        """测试分词 - 前后空格"""
        text = "  this is a test  "
        tokens = memory._tokenize(text)
        
        assert tokens == ["this", "is", "a", "test"]
    
    def test_tokenize_empty_string(self, memory):
        """测试分词 - 空字符串"""
        tokens = memory._tokenize("")
        assert tokens == []
    
    def test_fuse_memory_vectors_single(self, memory):
        """测试向量融合 - 单个向量"""
        vector = np.ones(64, dtype=np.float32)
        
        fused = memory._fuse_memory_vectors([vector])
        
        np.testing.assert_array_almost_equal(fused, vector)
    
    def test_fuse_memory_vectors_multiple(self, memory):
        """测试向量融合 - 多个向量"""
        vector1 = np.ones(64, dtype=np.float32)
        vector2 = np.ones(64, dtype=np.float32) * 2
        vector3 = np.ones(64, dtype=np.float32) * 3
        
        fused = memory._fuse_memory_vectors([vector1, vector2, vector3])
        
        # 加权平均应该是2.0
        expected = np.ones(64, dtype=np.float32) * 2.0
        np.testing.assert_array_almost_equal(fused, expected)
    
    def test_get_statistics_initial(self, memory):
        """测试获取统计 - 初始状态"""
        stats = memory.get_statistics()
        
        assert isinstance(stats, MemoryStatistics)
        assert stats.total_queries == 0
        assert stats.hit_count == 0
        assert stats.miss_count == 0
        assert stats.hit_rate == 0.0
    
    def test_get_statistics_after_operations(self, memory):
        """测试获取统计 - 操作后"""
        text = "test sentence for statistics"
        embedding = np.random.randn(64).astype(np.float32)
        
        # 存储
        memory.store_memory(text, [], embedding)
        
        # 查询（命中）
        memory.query_memory(text, [])
        
        # 查询（未命中）
        memory.query_memory("nonexistent text", [])
        
        stats = memory.get_statistics()
        
        assert stats.total_queries == 2
        assert stats.hit_count > 0
        assert stats.miss_count > 0
    
    def test_multiple_store_and_query(self, memory):
        """测试多次存储和查询"""
        texts = [
            "first test sentence",
            "second test sentence",
            "third test sentence"
        ]
        
        embeddings = [
            np.random.randn(64).astype(np.float32) for _ in range(3)
        ]
        
        # 存储所有
        for text, emb in zip(texts, embeddings):
            memory.store_memory(text, [], emb)
        
        # 查询所有
        for text in texts:
            result = memory.query_memory(text, [])
            assert result is not None
    
    def test_ssd_backend(self):
        """测试SSD存储后端"""
        memory = EngramMemory(
            ngram_size=4,
            embedding_dim=64,
            memory_size=100,
            storage_backend='ssd'
        )
        
        text = "test sentence for ssd"
        embedding = np.random.randn(64).astype(np.float32)
        
        memory.store_memory(text, [], embedding)
        retrieved = memory.query_memory(text, [])
        
        assert retrieved is not None
    
    def test_query_with_partial_match(self, memory):
        """测试查询 - 部分匹配"""
        # 存储一个长句子
        long_text = "this is a very long test sentence with many words"
        embedding = np.random.randn(64).astype(np.float32)
        memory.store_memory(long_text, [], embedding)
        
        # 查询部分内容
        partial_text = "this is a very"
        result = memory.query_memory(partial_text, [])
        
        # 应该能找到（因为N-gram有重叠）
        assert result is not None
    
    def test_context_influence(self, memory):
        """测试上下文影响"""
        text = "test sentence"
        embedding = np.random.randn(64).astype(np.float32)
        
        # 带上下文存储
        context = ["context sentence 1", "context sentence 2"]
        memory.store_memory(text, context, embedding)
        
        # 带相同上下文查询
        result1 = memory.query_memory(text, context)
        
        # 不带上下文查询 - 可能找不到，因为N-gram不同
        result2 = memory.query_memory(text, None)
        
        # 带上下文的查询应该能找到
        assert result1 is not None
        # 不带上下文的查询可能找不到（因为N-gram不同）
        # 这是正常的，因为上下文会影响N-gram提取
    
    def test_unicode_text(self, memory):
        """测试Unicode文本"""
        text = "这是一个测试句子"
        embedding = np.random.randn(64).astype(np.float32)
        
        memory.store_memory(text, [], embedding)
        result = memory.query_memory(text, [])
        
        assert result is not None
    
    def test_special_characters(self, memory):
        """测试特殊字符"""
        text = "test@#$% sentence!?"
        embedding = np.random.randn(64).astype(np.float32)
        
        memory.store_memory(text, [], embedding)
        result = memory.query_memory(text, [])
        
        assert result is not None
    
    def test_long_text(self, memory):
        """测试长文本"""
        text = " ".join([f"word{i}" for i in range(100)])
        embedding = np.random.randn(64).astype(np.float32)
        
        memory.store_memory(text, [], embedding)
        result = memory.query_memory(text, [])
        
        assert result is not None
    
    def test_memory_overwrite(self, memory):
        """测试记忆覆盖"""
        text = "test sentence"
        embedding1 = np.ones(64, dtype=np.float32)
        embedding2 = np.ones(64, dtype=np.float32) * 2
        
        # 第一次存储
        memory.store_memory(text, [], embedding1)
        
        # 第二次存储（覆盖）
        memory.store_memory(text, [], embedding2)
        
        # 查询应该返回最新的
        result = memory.query_memory(text, [])
        assert result is not None
        # 由于可能有多个N-gram，结果可能是融合的
        assert np.mean(result) > 1.0  # 应该接近2.0
    
    def test_query_memory_no_ngrams_extracted(self, memory):
        """测试查询 - 无法提取N-gram（覆盖行136-138）"""
        # 使用只有空格的文本，无法提取有效N-gram
        text = "   "
        result = memory.query_memory(text, [])
        
        # 应该返回None，因为无法提取N-gram
        assert result is None
        assert memory.miss_count > 0
    
    def test_store_memory_no_ngrams_extracted(self, memory):
        """测试存储 - 无法提取N-gram（覆盖行197-198）"""
        # 使用只有空格的文本
        text = "   "
        embedding = np.random.randn(64).astype(np.float32)
        
        # 应该跳过存储（不会抛出异常）
        memory.store_memory(text, [], embedding)
        
        # 验证没有存储任何内容
        result = memory.query_memory("test", [])
        assert result is None
    
    def test_store_memory_hash_exception(self, memory, monkeypatch):
        """测试存储 - 哈希异常（覆盖行210-211）"""
        text = "test sentence"
        embedding = np.random.randn(64).astype(np.float32)
        
        # Mock memory_table.set to raise exception
        original_set = memory.memory_table.set
        call_count = [0]
        
        def mock_set_error(address, emb):
            call_count[0] += 1
            raise RuntimeError("Set error")
        
        monkeypatch.setattr(memory.memory_table, 'set', mock_set_error)
        
        # 应该捕获异常并继续（不会抛出）
        memory.store_memory(text, [], embedding)
        
        # 验证尝试了存储但失败了
        assert call_count[0] > 0
    
    def test_init_memory_table_unsupported_backend(self):
        """测试初始化记忆表 - 不支持的后端（覆盖行104 else分支）"""
        # 这个测试实际上在test_initialization_invalid_storage_backend中已经覆盖
        # 但为了明确覆盖_init_memory_table中的else分支，我们再次测试
        with pytest.raises(ValueError, match="不支持的存储后端"):
            memory = EngramMemory(
                ngram_size=4,
                embedding_dim=64,
                memory_size=1000,
                storage_backend='unsupported_backend'
            )
    
    def test_init_memory_table_else_branch_direct(self):
        """测试_init_memory_table的else分支 - 直接调用（覆盖行104）"""
        # 创建一个正常的memory实例
        memory = EngramMemory(
            ngram_size=4,
            embedding_dim=64,
            memory_size=1000,
            storage_backend='ram'
        )
        
        # 修改storage_backend为不支持的值，然后调用_init_memory_table
        memory.storage_backend = 'unsupported'
        
        with pytest.raises(ValueError, match="不支持的存储后端"):
            memory._init_memory_table()
