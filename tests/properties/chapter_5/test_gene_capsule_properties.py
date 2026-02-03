"""基因胶囊管理器属性测试

白皮书依据: 第五章 5.3.2 基因胶囊

本模块测试基因胶囊管理器的正确性属性。

**Feature: chapter-5-darwin-visualization-redis**
**Property 3: 基因胶囊完整性**
**Property 4: 基因胶囊存储正确性**
**Property 5: 基因胶囊查询正确性**
**Property 6: 基因胶囊版本历史**
**Property 7: 基因胶囊序列化往返**
**Validates: Requirements 2.1-2.9**
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, settings, strategies as st

from src.brain.darwin_data_models import (
    GeneCapsule,
    ArenaPerformance,
    AuditResult,
    EvolutionRecord,
    Z2HStampStatus,
    MutationType,
)
from src.brain.gene_capsule_manager import (
    GeneCapsuleManager,
    create_test_arena_performance,
    create_test_audit_result,
)
from src.brain.redis_storage import RedisStorageManager


@pytest.fixture
async def clean_storage():
    """提供干净的Redis存储实例，每个测试前清理数据"""
    storage = RedisStorageManager(use_memory_fallback=True)
    await storage.initialize()
    
    # 清理所有基因胶囊相关数据
    try:
        # 清理基因胶囊数据
        keys_to_delete = []
        async for key in storage._redis_client.scan_iter("mia:knowledge:gene_capsule:*"):
            keys_to_delete.append(key)
        async for key in storage._redis_client.scan_iter("mia:knowledge:capsule_family:*"):
            keys_to_delete.append(key)
        async for key in storage._redis_client.scan_iter("mia:knowledge:capsule_history:*"):
            keys_to_delete.append(key)
        
        if keys_to_delete:
            await storage._redis_client.delete(*keys_to_delete)
    except Exception:
        pass  # 如果键不存在或使用内存回退，忽略错误
    
    yield storage
    
    # 测试后清理
    try:
        keys_to_delete = []
        async for key in storage._redis_client.scan_iter("mia:knowledge:gene_capsule:*"):
            keys_to_delete.append(key)
        async for key in storage._redis_client.scan_iter("mia:knowledge:capsule_family:*"):
            keys_to_delete.append(key)
        async for key in storage._redis_client.scan_iter("mia:knowledge:capsule_history:*"):
            keys_to_delete.append(key)
        
        if keys_to_delete:
            await storage._redis_client.delete(*keys_to_delete)
    except Exception:
        pass
    
    await storage.close()


# ===== 测试辅助函数 =====

def create_test_evolution_record() -> EvolutionRecord:
    """创建测试用进化记录"""
    return EvolutionRecord(
        record_id="test_record_001",
        parent_capsule_id=None,
        mutation_type=MutationType.INITIAL,
        mutation_description="初始创建",
        fitness_before=0.0,
        fitness_after=0.8,
        timestamp=datetime.now(),
    )


def create_test_capsule_data() -> Dict[str, Any]:
    """创建测试用胶囊数据"""
    return {
        "strategy_code": "def strategy(): return 'buy'",
        "parameter_config": {"param1": 0.5, "param2": 100},
        "analysis_report": {"score": 85, "risk": "low"},
        "arena_performance": create_test_arena_performance(),
        "audit_result": create_test_audit_result(),
        "evolution_history": [create_test_evolution_record()],
        "z2h_status": Z2HStampStatus.PENDING,
    }


# ===== Property 3: 基因胶囊完整性 =====

class TestGeneCapsuleCompleteness:
    """基因胶囊完整性测试
    
    **Property 3: 基因胶囊完整性**
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    
    @pytest.mark.asyncio
    async def test_capsule_contains_strategy_code(self, clean_storage) -> None:
        """基因胶囊应包含策略代码
        
        **Validates: Requirements 2.1**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.strategy_code == data["strategy_code"]
    
    @pytest.mark.asyncio
    async def test_capsule_contains_parameter_config(self, clean_storage) -> None:
        """基因胶囊应包含参数配置
        
        **Validates: Requirements 2.1**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.parameter_config == data["parameter_config"]
    
    @pytest.mark.asyncio
    async def test_capsule_contains_29d_analysis_report(self, clean_storage) -> None:
        """基因胶囊应包含29维度分析报告
        
        **Validates: Requirements 2.1**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.analysis_report_29d == data["analysis_report"]
    
    @pytest.mark.asyncio
    async def test_capsule_contains_arena_performance(self, clean_storage) -> None:
        """基因胶囊应包含Arena表现
        
        **Validates: Requirements 2.2**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.arena_performance.sharpe_ratio == data["arena_performance"].sharpe_ratio
    
    @pytest.mark.asyncio
    async def test_capsule_contains_audit_result(self, clean_storage) -> None:
        """基因胶囊应包含魔鬼审计结果
        
        **Validates: Requirements 2.2**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.devil_audit_result.passed == data["audit_result"].passed
    
    @pytest.mark.asyncio
    async def test_capsule_contains_z2h_status(self, clean_storage) -> None:
        """基因胶囊应包含Z2H钢印状态
        
        **Validates: Requirements 2.3**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.z2h_stamp_status == data["z2h_status"]


# ===== Property 4 & 5: 基因胶囊存储和查询正确性 =====

class TestGeneCapsuleStorageAndQuery:
    """基因胶囊存储和查询测试
    
    **Property 4: 基因胶囊存储正确性**
    **Property 5: 基因胶囊查询正确性**
    **Validates: Requirements 2.4, 2.5, 2.6, 2.7**
    """
    
    @pytest.mark.asyncio
    async def test_capsule_storage_and_retrieval(self, clean_storage) -> None:
        """基因胶囊存储后应能正确检索
        
        **Validates: Requirements 2.4, 2.6**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        # 创建胶囊
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        # 检索胶囊
        retrieved = await manager.get_capsule(capsule.capsule_id)
        
        assert retrieved is not None
        assert retrieved.capsule_id == capsule.capsule_id
        assert retrieved.strategy_code == capsule.strategy_code
    
    @pytest.mark.asyncio
    async def test_capsule_query_by_family(self, clean_storage) -> None:
        """应能按家族ID查询基因胶囊
        
        **Validates: Requirements 2.7**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        family_id = "test_family_001"
        
        # 创建多个同家族胶囊
        capsule1 = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
            family_id=family_id,
        )
        
        capsule2 = await manager.create_capsule(
            strategy_code=data["strategy_code"] + " # v2",
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
            family_id=family_id,
        )
        
        # 按家族查询
        family_capsules = await manager.get_capsules_by_family(family_id)
        
        assert len(family_capsules) == 2
        capsule_ids = [c.capsule_id for c in family_capsules]
        assert capsule1.capsule_id in capsule_ids
        assert capsule2.capsule_id in capsule_ids
    
    @pytest.mark.asyncio
    async def test_nonexistent_capsule_returns_none(self, clean_storage) -> None:
        """查询不存在的胶囊应返回None
        
        **Validates: Requirements 2.6**
        """
        manager = GeneCapsuleManager(clean_storage)
        result = await manager.get_capsule("nonexistent_id")
        assert result is None


# ===== Property 6: 基因胶囊版本历史 =====

class TestGeneCapsuleVersionHistory:
    """基因胶囊版本历史测试
    
    **Property 6: 基因胶囊版本历史**
    **Validates: Requirements 2.8**
    """
    
    @pytest.mark.asyncio
    async def test_update_preserves_history(self, clean_storage) -> None:
        """更新胶囊应保留历史版本
        
        **Validates: Requirements 2.8**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        # 创建胶囊
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        original_code = capsule.strategy_code
        
        # 更新胶囊
        updated = await manager.update_capsule(
            capsule.capsule_id,
            {"strategy_code": "def strategy(): return 'sell'"},
        )
        
        # 检查版本号递增
        assert updated.version == 2
        
        # 检查历史记录
        history = await manager.get_capsule_history(capsule.capsule_id)
        assert len(history) >= 1
        assert history[0].strategy_code == original_code
    
    @pytest.mark.asyncio
    async def test_version_increments_on_update(self, clean_storage) -> None:
        """每次更新版本号应递增
        
        **Validates: Requirements 2.8**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        # 创建胶囊
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        assert capsule.version == 1
        
        # 多次更新
        updated1 = await manager.update_capsule(
            capsule.capsule_id,
            {"parameter_config": {"param1": 0.6}},
        )
        assert updated1.version == 2
        
        updated2 = await manager.update_capsule(
            capsule.capsule_id,
            {"parameter_config": {"param1": 0.7}},
        )
        assert updated2.version == 3


# ===== Property 7: 基因胶囊序列化往返 =====

class TestGeneCapsuleSerializationRoundtrip:
    """基因胶囊序列化往返测试
    
    **Property 7: 基因胶囊序列化往返**
    **Validates: Requirements 2.9**
    """
    
    @pytest.mark.asyncio
    async def test_serialization_roundtrip(self, clean_storage) -> None:
        """序列化后再反序列化应产生等价对象
        
        **Validates: Requirements 2.9**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        # 创建胶囊
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        # 序列化
        json_str = manager.serialize(capsule)
        
        # 反序列化
        deserialized = manager.deserialize(json_str)
        
        # 验证等价性
        assert deserialized.capsule_id == capsule.capsule_id
        assert deserialized.strategy_code == capsule.strategy_code
        assert deserialized.parameter_config == capsule.parameter_config
        assert deserialized.z2h_stamp_status == capsule.z2h_stamp_status
        assert deserialized.version == capsule.version
    
    @pytest.mark.asyncio
    async def test_serialization_produces_valid_json(self, clean_storage) -> None:
        """序列化应产生有效的JSON
        
        **Validates: Requirements 2.9**
        """
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        capsule = await manager.create_capsule(
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report=data["analysis_report"],
            arena_performance=data["arena_performance"],
            audit_result=data["audit_result"],
            evolution_history=data["evolution_history"],
            z2h_status=data["z2h_status"],
        )
        
        json_str = manager.serialize(capsule)
        
        # 验证是有效JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        assert "capsule_id" in parsed
        assert "strategy_code" in parsed
    
    @pytest.mark.asyncio
    async def test_strategy_code_preserved_in_serialization(self, clean_storage) -> None:
        """策略代码在序列化过程中应保持不变
        
        **Validates: Requirements 2.9**
        """
        manager = GeneCapsuleManager(clean_storage)
        
        # 测试多种策略代码
        test_codes = [
            "def strategy(): return 'buy'",
            "class MyStrategy:\n    pass",
            "# 中文注释\ndef test(): pass",
            "import numpy as np\nreturn np.mean([1,2,3])",
        ]
        
        for code in test_codes:
            data = create_test_capsule_data()
            data["strategy_code"] = code
            
            capsule = await manager.create_capsule(
                strategy_code=data["strategy_code"],
                parameter_config=data["parameter_config"],
                analysis_report=data["analysis_report"],
                arena_performance=data["arena_performance"],
                audit_result=data["audit_result"],
                evolution_history=data["evolution_history"],
                z2h_status=data["z2h_status"],
            )
            
            json_str = manager.serialize(capsule)
            deserialized = manager.deserialize(json_str)
            
            assert deserialized.strategy_code == code


# ===== 边界条件测试 =====

class TestGeneCapsuleEdgeCases:
    """基因胶囊边界条件测试"""
    
    @pytest.mark.asyncio
    async def test_empty_strategy_code_raises_error(self, clean_storage) -> None:
        """空策略代码应抛出错误"""
        manager = GeneCapsuleManager(clean_storage)
        data = create_test_capsule_data()
        
        with pytest.raises(ValueError, match="策略代码不能为空"):
            await manager.create_capsule(
                strategy_code="",
                parameter_config=data["parameter_config"],
                analysis_report=data["analysis_report"],
                arena_performance=data["arena_performance"],
                audit_result=data["audit_result"],
                evolution_history=data["evolution_history"],
                z2h_status=data["z2h_status"],
            )
    
    @pytest.mark.asyncio
    async def test_empty_capsule_id_raises_error(self, clean_storage) -> None:
        """空胶囊ID应抛出错误"""
        manager = GeneCapsuleManager(clean_storage)
        
        with pytest.raises(ValueError, match="胶囊ID不能为空"):
            await manager.get_capsule("")
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_capsule_raises_error(self, clean_storage) -> None:
        """更新不存在的胶囊应抛出错误"""
        manager = GeneCapsuleManager(clean_storage)
        
        with pytest.raises(ValueError, match="基因胶囊不存在"):
            await manager.update_capsule(
                "nonexistent_id",
                {"strategy_code": "new code"},
            )
    
    @pytest.mark.asyncio
    async def test_serialize_none_raises_error(self, clean_storage) -> None:
        """序列化None应抛出错误"""
        manager = GeneCapsuleManager(clean_storage)
        
        with pytest.raises(ValueError, match="基因胶囊不能为None"):
            manager.serialize(None)
    
    @pytest.mark.asyncio
    async def test_deserialize_empty_string_raises_error(self, clean_storage) -> None:
        """反序列化空字符串应抛出错误"""
        manager = GeneCapsuleManager(clean_storage)
        
        with pytest.raises(ValueError, match="JSON字符串不能为空"):
            manager.deserialize("")
