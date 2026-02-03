"""演化树属性测试

白皮书依据: 第五章 5.3.3 演化树

本模块测试演化树的正确性属性。

**Feature: chapter-5-darwin-visualization-redis**
**Property 8: 演化树结构正确性**
**Property 9: 演化树查询正确性**
**Property 10: 演化树存储正确性**
**Property 11: 演化树序列化往返**
**Validates: Requirements 3.1-3.9**
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

import pytest

from src.brain.darwin_data_models import MutationType
from src.brain.evolution_tree import EvolutionTree
from src.brain.redis_storage import RedisStorageManager


# ===== Property 8: 演化树结构正确性 =====

class TestEvolutionTreeStructure:
    """演化树结构正确性测试
    
    **Property 8: 演化树结构正确性**
    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    
    def test_root_node_is_initial_strategy(self) -> None:
        """根节点应是初代策略
        
        **Validates: Requirements 3.1**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="初代策略",
                    fitness=0.8,
                )
                
                assert root.generation == 0
                assert tree.root_node_id == root.node_id
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_child_node_represents_mutation(self) -> None:
        """子节点应表示变异后代
        
        **Validates: Requirements 3.2**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="初代策略",
                    fitness=0.8,
                )
                
                child, edge = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="变异策略",
                    fitness=0.85,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="参数优化",
                )
                
                assert child.generation == 1
                assert edge.parent_node_id == root.node_id
                assert edge.child_node_id == child.node_id
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_edge_contains_mutation_record(self) -> None:
        """边应包含变异记录和适应度变化
        
        **Validates: Requirements 3.3**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="初代策略",
                    fitness=0.8,
                )
                
                child, edge = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="变异策略",
                    fitness=0.85,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="参数优化",
                )
                
                assert edge.mutation_type == MutationType.PARAMETER_MUTATION
                assert edge.mutation_description == "参数优化"
                assert edge.fitness_change == pytest.approx(0.05, abs=0.001)
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_generation_increments_correctly(self) -> None:
        """代数应正确递增"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                assert root.generation == 0
                
                g1, _ = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="G1",
                    fitness=0.82,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="变异1",
                )
                assert g1.generation == 1
                
                g2, _ = await tree.add_child(
                    parent_node_id=g1.node_id,
                    capsule_id="capsule_003",
                    strategy_name="G2",
                    fitness=0.84,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="变异2",
                )
                assert g2.generation == 2
            finally:
                await storage.close()
        
        asyncio.run(run_test())


# ===== Property 9: 演化树查询正确性 =====

class TestEvolutionTreeQuery:
    """演化树查询正确性测试
    
    **Property 9: 演化树查询正确性**
    **Validates: Requirements 3.4, 3.5, 3.6**
    """
    
    def test_trace_lineage_returns_complete_path(self) -> None:
        """全链溯源应返回从根到该节点的完整路径
        
        **Validates: Requirements 3.4**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                g1, _ = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="G1",
                    fitness=0.82,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="变异1",
                )
                
                g2, _ = await tree.add_child(
                    parent_node_id=g1.node_id,
                    capsule_id="capsule_003",
                    strategy_name="G2",
                    fitness=0.84,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="变异2",
                )
                
                lineage = await tree.trace_lineage(g2.node_id)
                
                assert len(lineage) == 3
                assert lineage[0].node_id == root.node_id
                assert lineage[1].node_id == g1.node_id
                assert lineage[2].node_id == g2.node_id
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_compare_family_returns_analysis(self) -> None:
        """家族对比应返回同家族策略的差异分析
        
        **Validates: Requirements 3.5**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                g1a, _ = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="G1A",
                    fitness=0.85,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="变异A",
                )
                
                g1b, _ = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_003",
                    strategy_name="G1B",
                    fitness=0.75,
                    mutation_type=MutationType.STRUCTURE_MUTATION,
                    mutation_description="变异B",
                )
                
                comparison = await tree.compare_family([g1a.node_id, g1b.node_id])
                
                assert comparison.family_id == tree.family_id
                assert len(comparison.members) == 2
                assert comparison.best_performer == g1a.node_id
                assert comparison.worst_performer == g1b.node_id
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_learn_from_failures_returns_lessons(self) -> None:
        """失败学习应返回失败分支的教训
        
        **Validates: Requirements 3.6**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                # 添加一个失败的变异（适应度下降）
                failed, _ = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="失败策略",
                    fitness=0.6,  # 适应度下降
                    mutation_type=MutationType.STRUCTURE_MUTATION,
                    mutation_description="结构变异失败",
                )
                
                learning = await tree.learn_from_failures()
                
                assert len(learning.failed_branches) >= 1
                assert failed.node_id in learning.failed_branches
                assert len(learning.lessons_learned) > 0
            finally:
                await storage.close()
        
        asyncio.run(run_test())


# ===== Property 10: 演化树存储正确性 =====

class TestEvolutionTreeStorage:
    """演化树存储正确性测试
    
    **Property 10: 演化树存储正确性**
    **Validates: Requirements 3.7, 3.8**
    """
    
    def test_tree_saved_to_redis(self) -> None:
        """演化树应保存到Redis
        
        **Validates: Requirements 3.7**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                # 验证已保存到Redis
                saved_data = await storage.get_evolution_tree()
                assert saved_data is not None
                assert saved_data["family_id"] == tree.family_id
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_tree_loaded_from_redis(self) -> None:
        """演化树应能从Redis加载
        
        **Validates: Requirements 3.7**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                # 创建并保存树
                tree1 = EvolutionTree(storage)
                root = await tree1.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                # 从Redis加载
                tree2 = await EvolutionTree.load_from_redis(storage)
                
                assert tree2 is not None
                assert tree2.family_id == tree1.family_id
                assert tree2.root_node_id == root.node_id
            finally:
                await storage.close()
        
        asyncio.run(run_test())


# ===== Property 11: 演化树序列化往返 =====

class TestEvolutionTreeSerializationRoundtrip:
    """演化树序列化往返测试
    
    **Property 11: 演化树序列化往返**
    **Validates: Requirements 3.9**
    """
    
    def test_serialization_roundtrip(self) -> None:
        """序列化后再反序列化应产生结构等价的树
        
        **Validates: Requirements 3.9**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                g1, _ = await tree.add_child(
                    parent_node_id=root.node_id,
                    capsule_id="capsule_002",
                    strategy_name="G1",
                    fitness=0.85,
                    mutation_type=MutationType.PARAMETER_MUTATION,
                    mutation_description="变异1",
                )
                
                # 序列化
                json_str = tree.serialize()
                
                # 反序列化
                deserialized = EvolutionTree.deserialize(json_str, storage)
                
                # 验证结构等价
                assert deserialized.family_id == tree.family_id
                assert deserialized.root_node_id == tree.root_node_id
                assert deserialized.node_count() == tree.node_count()
                assert deserialized.edge_count() == tree.edge_count()
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_serialization_produces_valid_json(self) -> None:
        """序列化应产生有效的JSON
        
        **Validates: Requirements 3.9**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                json_str = tree.serialize()
                
                # 验证是有效JSON
                parsed = json.loads(json_str)
                assert isinstance(parsed, dict)
                assert "family_id" in parsed
                assert "nodes" in parsed
                assert "edges" in parsed
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_nodes_preserved_in_serialization(self) -> None:
        """节点在序列化过程中应保持不变
        
        **Validates: Requirements 3.9**
        """
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                root = await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="测试策略",
                    fitness=0.8,
                )
                
                json_str = tree.serialize()
                deserialized = EvolutionTree.deserialize(json_str, storage)
                
                original_node = tree.nodes[root.node_id]
                restored_node = deserialized.nodes[root.node_id]
                
                assert restored_node.strategy_name == original_node.strategy_name
                assert restored_node.fitness == original_node.fitness
                assert restored_node.generation == original_node.generation
            finally:
                await storage.close()
        
        asyncio.run(run_test())


# ===== 边界条件测试 =====

class TestEvolutionTreeEdgeCases:
    """演化树边界条件测试"""
    
    def test_duplicate_root_raises_error(self) -> None:
        """重复创建根节点应抛出错误"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                await tree.create_root(
                    capsule_id="capsule_001",
                    strategy_name="G0",
                    fitness=0.8,
                )
                
                with pytest.raises(ValueError, match="根节点已存在"):
                    await tree.create_root(
                        capsule_id="capsule_002",
                        strategy_name="G0-2",
                        fitness=0.9,
                    )
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_add_child_to_nonexistent_parent_raises_error(self) -> None:
        """添加子节点到不存在的父节点应抛出错误"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                with pytest.raises(ValueError, match="父节点不存在"):
                    await tree.add_child(
                        parent_node_id="nonexistent",
                        capsule_id="capsule_001",
                        strategy_name="G1",
                        fitness=0.8,
                        mutation_type=MutationType.PARAMETER_MUTATION,
                        mutation_description="变异",
                    )
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_trace_lineage_nonexistent_node_raises_error(self) -> None:
        """追溯不存在的节点应抛出错误"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                
                with pytest.raises(ValueError, match="节点不存在"):
                    await tree.trace_lineage("nonexistent")
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_empty_json_raises_error(self) -> None:
        """反序列化空字符串应抛出错误"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                with pytest.raises(ValueError, match="JSON字符串不能为空"):
                    EvolutionTree.deserialize("", storage)
            finally:
                await storage.close()
        
        asyncio.run(run_test())
    
    def test_get_all_leaves_empty_tree(self) -> None:
        """空树应返回空叶子列表"""
        async def run_test():
            storage = RedisStorageManager(use_memory_fallback=True)
            await storage.initialize()
            
            try:
                tree = EvolutionTree(storage)
                leaves = await tree.get_all_leaves()
                assert leaves == []
            finally:
                await storage.close()
        
        asyncio.run(run_test())
