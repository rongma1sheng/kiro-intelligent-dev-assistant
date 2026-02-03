"""Redis存储管理器属性测试

白皮书依据: 第五章 5.5 Redis数据结构

本模块测试Redis存储管理器和TTL管理器的正确性属性。

**Feature: chapter-5-darwin-visualization-redis**
**Property 20: Redis分析结果存储正确性**
**Property 21: Redis知识库存储正确性**
**Property 22: TTL管理正确性**
**Validates: Requirements 8.1-8.9, 9.1-9.7, 10.1-10.7**
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, settings, strategies as st

from src.brain.redis_storage import (
    TTLManager,
    RedisStorageManager,
    InMemoryStorage,
)


# ===== 测试策略 =====

@st.composite
def strategy_id_strategy(draw: st.DrawFn) -> str:
    """生成策略ID"""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"),
        min_size=1,
        max_size=50,
    ))


@st.composite
def symbol_strategy(draw: st.DrawFn) -> str:
    """生成股票代码"""
    code = draw(st.integers(min_value=1, max_value=999999))
    suffix = draw(st.sampled_from(["SZ", "SH"]))
    return f"{code:06d}.{suffix}"


@st.composite
def date_strategy(draw: st.DrawFn) -> str:
    """生成日期字符串"""
    year = draw(st.integers(min_value=2020, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    return f"{year}-{month:02d}-{day:02d}"


# ===== Property 22: TTL管理正确性 =====

class TestTTLManagerProperties:
    """TTL管理器属性测试
    
    **Property 22: TTL管理正确性**
    **Validates: Requirements 10.1-10.7**
    """
    
    @given(st.sampled_from([
        "mia:market:macro",
        "mia:market:sectors:2024-01-01",
        "mia:smart_money:deep_analysis:000001.SZ",
        "mia:recommendation:000001.SZ",
    ]))
    @settings(max_examples=100)
    def test_market_data_ttl_is_one_hour(self, key: str) -> None:
        """市场数据TTL应为1小时
        
        **Validates: Requirements 10.2**
        """
        ttl_manager = TTLManager()
        ttl = ttl_manager.get_ttl_for_key(key)
        assert ttl == TTLManager.TTL_MARKET, f"市场数据TTL应为{TTLManager.TTL_MARKET}，实际为{ttl}"
    
    @given(date_strategy())
    @settings(max_examples=100)
    def test_limit_up_data_ttl_is_30_days(self, date: str) -> None:
        """涨停板数据TTL应为30天
        
        **Validates: Requirements 10.3**
        """
        ttl_manager = TTLManager()
        key = f"mia:market:limit_up:{date}"
        ttl = ttl_manager.get_ttl_for_key(key)
        assert ttl == TTLManager.TTL_HISTORY, f"涨停板数据TTL应为{TTLManager.TTL_HISTORY}，实际为{ttl}"
    
    @given(st.sampled_from([
        "mia:knowledge:gene_capsule:test_id",
        "mia:knowledge:evolution_tree",
        "mia:knowledge:elite_strategies",
        "mia:knowledge:anti_patterns",
        "mia:analysis:essence:test_id",
        "mia:analysis:risk:test_id",
        "mia:analysis:overfitting:test_id",
    ]))
    @settings(max_examples=100)
    def test_knowledge_data_ttl_is_permanent(self, key: str) -> None:
        """知识库数据TTL应为永久
        
        **Validates: Requirements 10.4**
        """
        ttl_manager = TTLManager()
        ttl = ttl_manager.get_ttl_for_key(key)
        assert ttl == TTLManager.TTL_PERMANENT, f"知识库数据TTL应为{TTLManager.TTL_PERMANENT}，实际为{ttl}"
    
    @given(strategy_id_strategy())
    @settings(max_examples=100)
    def test_ttl_auto_detection_by_key_pattern(self, strategy_id: str) -> None:
        """TTL应根据键模式自动检测
        
        **Validates: Requirements 10.1**
        """
        ttl_manager = TTLManager()
        
        # 分析结果键 -> 永久
        analysis_key = f"mia:analysis:essence:{strategy_id}"
        assert ttl_manager.get_ttl_for_key(analysis_key) == TTLManager.TTL_PERMANENT
        
        # 知识库键 -> 永久
        knowledge_key = f"mia:knowledge:gene_capsule:{strategy_id}"
        assert ttl_manager.get_ttl_for_key(knowledge_key) == TTLManager.TTL_PERMANENT
        
        # 建议键 -> 1小时
        recommendation_key = f"mia:recommendation:{strategy_id}"
        assert ttl_manager.get_ttl_for_key(recommendation_key) == TTLManager.TTL_MARKET
    
    def test_empty_key_raises_error(self) -> None:
        """空键名应抛出错误"""
        ttl_manager = TTLManager()
        with pytest.raises(ValueError, match="键名不能为空"):
            ttl_manager.get_ttl_for_key("")


# ===== Property 20 & 21: Redis存储正确性 =====

class TestRedisStorageProperties:
    """Redis存储属性测试
    
    **Property 20: Redis分析结果存储正确性**
    **Property 21: Redis知识库存储正确性**
    **Validates: Requirements 8.1-8.9, 9.1-9.7**
    """
    
    @pytest.fixture
    def event_loop(self):
        """创建事件循环"""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    def test_essence_analysis_storage_roundtrip(self) -> None:
        """策略本质分析存储往返测试
        
        **Validates: Requirements 8.1**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                strategy_id = "test_strategy_001"
                data = {"score": 85.5, "risk_level": "low"}
                
                await storage.store_essence_analysis(strategy_id, data)
                retrieved = await storage.get_essence_analysis(strategy_id)
                
                assert retrieved is not None
                assert retrieved["score"] == data["score"]
                assert retrieved["risk_level"] == data["risk_level"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_risk_assessment_storage_roundtrip(self) -> None:
        """风险评估存储往返测试
        
        **Validates: Requirements 8.2**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                strategy_id = "test_strategy_002"
                data = {"var_95": 0.05, "max_drawdown": 0.15}
                
                await storage.store_risk_assessment(strategy_id, data)
                retrieved = await storage.get_risk_assessment(strategy_id)
                
                assert retrieved is not None
                assert retrieved["var_95"] == data["var_95"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_overfitting_detection_storage_roundtrip(self) -> None:
        """过拟合检测存储往返测试
        
        **Validates: Requirements 8.3**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                strategy_id = "test_strategy_003"
                data = {"in_sample_sharpe": 2.5, "out_sample_sharpe": 1.8}
                
                await storage.store_overfitting_detection(strategy_id, data)
                retrieved = await storage.get_overfitting_detection(strategy_id)
                
                assert retrieved is not None
                assert retrieved["in_sample_sharpe"] == data["in_sample_sharpe"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_smart_money_analysis_storage_roundtrip(self) -> None:
        """主力资金分析存储往返测试
        
        **Validates: Requirements 8.6**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                symbol = "000001.SZ"
                data = {"smart_money_type": "机构", "position_cost": 10.5}
                
                await storage.store_smart_money_analysis(symbol, data)
                retrieved = await storage.get_smart_money_analysis(symbol)
                
                assert retrieved is not None
                assert retrieved["smart_money_type"] == data["smart_money_type"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_recommendation_storage_roundtrip(self) -> None:
        """个股建议存储往返测试
        
        **Validates: Requirements 8.7**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                symbol = "000002.SZ"
                data = {"action": "买入", "confidence": 0.85}
                
                await storage.store_recommendation(symbol, data)
                retrieved = await storage.get_recommendation(symbol)
                
                assert retrieved is not None
                assert retrieved["action"] == data["action"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_limit_up_data_storage_roundtrip(self) -> None:
        """涨停板数据存储往返测试
        
        **Validates: Requirements 8.5**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                date = "2024-01-15"
                data = {"total_count": 50, "sectors": ["科技", "新能源"]}
                
                await storage.store_limit_up_data(date, data)
                retrieved = await storage.get_limit_up_data(date)
                
                assert retrieved is not None
                assert retrieved["total_count"] == data["total_count"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())

    
    def test_gene_capsule_storage_roundtrip(self) -> None:
        """基因胶囊存储往返测试
        
        **Validates: Requirements 9.1**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                capsule_id = "capsule_001"
                data = {
                    "capsule_id": capsule_id,
                    "strategy_code": "def strategy(): pass",
                    "family_id": "family_001",
                }
                
                await storage.store_gene_capsule(capsule_id, data)
                retrieved = await storage.get_gene_capsule(capsule_id)
                
                assert retrieved is not None
                assert retrieved["capsule_id"] == data["capsule_id"]
                assert retrieved["family_id"] == data["family_id"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_evolution_tree_storage_roundtrip(self) -> None:
        """演化树存储往返测试
        
        **Validates: Requirements 9.2**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree_data = {
                    "root_id": "root_node",
                    "nodes": {"root_node": {"fitness": 0.8}},
                }
                
                await storage.store_evolution_tree(tree_data)
                retrieved = await storage.get_evolution_tree()
                
                assert retrieved is not None
                assert retrieved["root_id"] == tree_data["root_id"]
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_elite_strategies_storage(self) -> None:
        """精英策略存储测试
        
        **Validates: Requirements 9.3**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                strategy_ids = ["elite_001", "elite_002", "elite_003"]
                
                for sid in strategy_ids:
                    await storage.add_elite_strategy(sid)
                
                retrieved = await storage.get_elite_strategies()
                
                for sid in strategy_ids:
                    assert sid in retrieved
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_failed_strategies_storage(self) -> None:
        """失败策略存储测试
        
        **Validates: Requirements 9.4**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                strategy_ids = ["failed_001", "failed_002"]
                
                for sid in strategy_ids:
                    await storage.add_failed_strategy(sid)
                
                retrieved = await storage.get_failed_strategies()
                
                for sid in strategy_ids:
                    assert sid in retrieved
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_anti_patterns_storage_roundtrip(self) -> None:
        """反向黑名单存储往返测试
        
        **Validates: Requirements 9.5**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                patterns = [
                    {"pattern_id": "p1", "description": "过拟合模式"},
                    {"pattern_id": "p2", "description": "未来函数模式"},
                ]
                
                await storage.store_anti_patterns(patterns)
                retrieved = await storage.get_anti_patterns()
                
                assert len(retrieved) == len(patterns)
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_batch_store_and_get(self) -> None:
        """批量存储和获取测试
        
        **Validates: Requirements 9.6**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                items = [
                    ("mia:analysis:essence:batch_001", {"score": 80}, None),
                    ("mia:analysis:essence:batch_002", {"score": 90}, None),
                ]
                
                await storage.batch_store(items)
                
                keys = [item[0] for item in items]
                retrieved = await storage.batch_get(keys)
                
                assert len(retrieved) == len(items)
            finally:
                await storage.close()
        
        asyncio.run(run_test())


# ===== 边界条件测试 =====

class TestRedisStorageEdgeCases:
    """Redis存储边界条件测试"""
    
    def test_empty_strategy_id_raises_error(self) -> None:
        """空策略ID应抛出错误"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                with pytest.raises(ValueError, match="策略ID不能为空"):
                    await storage.store_essence_analysis("", {"data": "test"})
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_empty_symbol_raises_error(self) -> None:
        """空股票代码应抛出错误"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                with pytest.raises(ValueError, match="股票代码不能为空"):
                    await storage.store_recommendation("", {"data": "test"})
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_nonexistent_key_returns_none(self) -> None:
        """不存在的键应返回None"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                result = await storage.get_essence_analysis("nonexistent_id")
                assert result is None
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_empty_batch_operations(self) -> None:
        """空批量操作应正常处理"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                await storage.batch_store([])
                result = await storage.batch_get([])
                assert result == {}
            finally:
                await storage.close()
        
        asyncio.run(run_test())
