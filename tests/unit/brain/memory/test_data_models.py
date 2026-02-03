"""记忆系统数据模型单元测试

白皮书依据: 第二章 2.8.1 Engram记忆模块
"""

import pytest
import numpy as np
from src.brain.memory.data_models import MemoryQuery, MemoryRecord, MemoryStatistics


class TestMemoryQuery:
    """MemoryQuery单元测试类"""
    
    def test_initialization_minimal(self):
        """测试初始化 - 最小参数"""
        query = MemoryQuery(text="test query")
        
        assert query.text == "test query"
        assert query.context is None
        assert query.max_results == 1
    
    def test_initialization_full(self):
        """测试初始化 - 完整参数"""
        query = MemoryQuery(
            text="test query",
            context=["context 1", "context 2"],
            max_results=5
        )
        
        assert query.text == "test query"
        assert query.context == ["context 1", "context 2"]
        assert query.max_results == 5
    
    def test_initialization_empty_context(self):
        """测试初始化 - 空上下文"""
        query = MemoryQuery(text="test", context=[])
        
        assert query.context == []


class TestMemoryRecord:
    """MemoryRecord单元测试类"""
    
    def test_initialization_minimal(self):
        """测试初始化 - 最小参数"""
        embedding = np.random.randn(64).astype(np.float32)
        
        record = MemoryRecord(
            text="test text",
            context=["context"],
            embedding=embedding
        )
        
        assert record.text == "test text"
        assert record.context == ["context"]
        np.testing.assert_array_equal(record.embedding, embedding)
        assert record.metadata is None
    
    def test_initialization_with_metadata(self):
        """测试初始化 - 带元数据"""
        embedding = np.random.randn(64).astype(np.float32)
        metadata = {
            'timestamp': '2026-01-23',
            'source': 'test',
            'confidence': 0.95
        }
        
        record = MemoryRecord(
            text="test text",
            context=["context"],
            embedding=embedding,
            metadata=metadata
        )
        
        assert record.metadata == metadata
        assert record.metadata['timestamp'] == '2026-01-23'
        assert record.metadata['confidence'] == 0.95
    
    def test_initialization_empty_context(self):
        """测试初始化 - 空上下文"""
        embedding = np.random.randn(64).astype(np.float32)
        
        record = MemoryRecord(
            text="test text",
            context=[],
            embedding=embedding
        )
        
        assert record.context == []


class TestMemoryStatistics:
    """MemoryStatistics单元测试类"""
    
    def test_initialization_minimal(self):
        """测试初始化 - 最小参数"""
        stats = MemoryStatistics(
            total_queries=100,
            hit_count=80,
            miss_count=20,
            hit_rate=0.8,
            memory_usage={'backend': 'ram'}
        )
        
        assert stats.total_queries == 100
        assert stats.hit_count == 80
        assert stats.miss_count == 20
        assert stats.hit_rate == 0.8
        assert stats.memory_usage == {'backend': 'ram'}
        assert stats.total_slots == 0
        assert stats.occupied_slots == 0
        assert stats.usage_rate == 0.0
    
    def test_initialization_full(self):
        """测试初始化 - 完整参数"""
        memory_usage = {
            'backend': 'ram',
            'memory_mb': 100.5
        }
        
        stats = MemoryStatistics(
            total_queries=1000,
            hit_count=800,
            miss_count=200,
            hit_rate=0.8,
            memory_usage=memory_usage,
            total_slots=10000,
            occupied_slots=5000,
            usage_rate=0.5
        )
        
        assert stats.total_queries == 1000
        assert stats.hit_count == 800
        assert stats.miss_count == 200
        assert stats.hit_rate == 0.8
        assert stats.memory_usage == memory_usage
        assert stats.total_slots == 10000
        assert stats.occupied_slots == 5000
        assert stats.usage_rate == 0.5
    
    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        stats = MemoryStatistics(
            total_queries=100,
            hit_count=75,
            miss_count=25,
            hit_rate=0.75,
            memory_usage={}
        )
        
        # 验证命中率
        assert stats.hit_rate == 0.75
        assert stats.hit_count + stats.miss_count == stats.total_queries
    
    def test_zero_queries(self):
        """测试零查询"""
        stats = MemoryStatistics(
            total_queries=0,
            hit_count=0,
            miss_count=0,
            hit_rate=0.0,
            memory_usage={}
        )
        
        assert stats.total_queries == 0
        assert stats.hit_rate == 0.0
    
    def test_perfect_hit_rate(self):
        """测试完美命中率"""
        stats = MemoryStatistics(
            total_queries=100,
            hit_count=100,
            miss_count=0,
            hit_rate=1.0,
            memory_usage={}
        )
        
        assert stats.hit_rate == 1.0
    
    def test_zero_hit_rate(self):
        """测试零命中率"""
        stats = MemoryStatistics(
            total_queries=100,
            hit_count=0,
            miss_count=100,
            hit_rate=0.0,
            memory_usage={}
        )
        
        assert stats.hit_rate == 0.0
