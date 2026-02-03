"""达尔文进化体系集成测试

白皮书依据: 第五章 5.3 达尔文进化体系集成

测试达尔文进化系统组件的集成，验证进化流程和知识管理功能。

注意：本测试使用MockRedisStorageManager替代真正的RedisStorageManager，
避免Windows平台上Redis异步客户端在事件循环关闭后的问题。
"""

import json
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, patch

from src.brain.darwin_system import DarwinSystem
from src.brain.gene_capsule_manager import GeneCapsuleManager
from src.brain.evolution_tree import EvolutionTree
from src.brain.anti_pattern_library import AntiPatternLibrary
from src.brain.redis_storage import InMemoryStorage, TTLManager
from src.brain.darwin_data_models import (
    Factor,
    EvolutionContext,
    ArenaPerformance,
    AuditResult,
    Z2HStampStatus,
    FailureStep,
)


class MockRedisStorageManager:
    """模拟Redis存储管理器，使用纯内存存储避免事件循环问题
    
    完整实现RedisStorageManager的所有方法，使用内存存储替代Redis。
    """
    
    # 键前缀常量（与RedisStorageManager保持一致）
    KEY_ANALYSIS_ESSENCE = "mia:analysis:essence"
    KEY_KNOWLEDGE_GENE_CAPSULE = "mia:knowledge:gene_capsule"
    KEY_KNOWLEDGE_EVOLUTION_TREE = "mia:knowledge:evolution_tree"
    KEY_KNOWLEDGE_ANTI_PATTERNS = "mia:knowledge:anti_patterns"
    
    def __init__(self, *args, **kwargs) -> None:
        """初始化模拟存储（忽略所有参数）"""
        self._redis_client = InMemoryStorage()
        self._ttl_manager = TTLManager(self._redis_client)
        self._initialized = True
    
    async def initialize(self) -> None:
        """初始化（已在构造函数中完成）"""
        pass
    
    async def close(self) -> None:
        """关闭（内存存储无需关闭）"""
        pass
    
    async def _ensure_initialized(self) -> None:
        """确保已初始化"""
        pass
    
    @property
    def ttl_manager(self) -> TTLManager:
        """获取TTL管理器"""
        return self._ttl_manager

    async def store_essence_analysis(self, strategy_id: str, data: Dict[str, Any]) -> None:
        """存储策略本质分析"""
        key = f"{self.KEY_ANALYSIS_ESSENCE}:{strategy_id}"
        await self._redis_client.set(key, json.dumps(data, default=str))
    
    async def get_essence_analysis(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略本质分析"""
        key = f"{self.KEY_ANALYSIS_ESSENCE}:{strategy_id}"
        data = await self._redis_client.get(key)
        return json.loads(data) if data else None
    
    async def store_gene_capsule(self, capsule_id: str, data: Dict[str, Any]) -> None:
        """存储基因胶囊"""
        key = f"{self.KEY_KNOWLEDGE_GENE_CAPSULE}:{capsule_id}"
        await self._redis_client.set(key, json.dumps(data, default=str))
    
    async def get_gene_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        """获取基因胶囊"""
        key = f"{self.KEY_KNOWLEDGE_GENE_CAPSULE}:{capsule_id}"
        data = await self._redis_client.get(key)
        return json.loads(data) if data else None
    
    async def store_evolution_tree(self, data: Dict[str, Any]) -> None:
        """存储演化树"""
        key = self.KEY_KNOWLEDGE_EVOLUTION_TREE
        await self._redis_client.set(key, json.dumps(data, default=str))
    
    async def get_evolution_tree(self) -> Optional[Dict[str, Any]]:
        """获取演化树"""
        key = self.KEY_KNOWLEDGE_EVOLUTION_TREE
        data = await self._redis_client.get(key)
        return json.loads(data) if data else None
    
    async def store_anti_patterns(self, patterns: List[Dict[str, Any]]) -> None:
        """存储反向黑名单"""
        key = self.KEY_KNOWLEDGE_ANTI_PATTERNS
        # 先删除旧数据
        await self._redis_client.delete(key)
        # 添加新数据
        if patterns:
            json_patterns = [json.dumps(p, default=str) for p in patterns]
            for p in json_patterns:
                await self._redis_client.lpush(key, p)
    
    async def get_anti_patterns(self) -> List[Dict[str, Any]]:
        """获取所有反向模式"""
        key = self.KEY_KNOWLEDGE_ANTI_PATTERNS
        data = await self._redis_client.lrange(key, 0, -1)
        return [json.loads(d) for d in data] if data else []
    
    async def delete_key(self, key: str) -> bool:
        """删除键"""
        result = await self._redis_client.delete(key)
        return result > 0
    
    async def get_all_gene_capsule_ids(self) -> List[str]:
        """获取所有基因胶囊ID"""
        capsule_ids = []
        pattern = f"{self.KEY_KNOWLEDGE_GENE_CAPSULE}:*"
        _, keys = await self._redis_client.scan(0, match=pattern, count=100)
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            capsule_id = key_str.split(":")[-1]
            capsule_ids.append(capsule_id)
        return capsule_ids
    
    async def get_gene_capsules_by_family(self, family_id: str) -> List[Dict[str, Any]]:
        """按家族ID获取基因胶囊"""
        capsules = []
        capsule_ids = await self.get_all_gene_capsule_ids()
        for capsule_id in capsule_ids:
            capsule = await self.get_gene_capsule(capsule_id)
            if capsule and capsule.get("family_id") == family_id:
                capsules.append(capsule)
        return capsules


@pytest.fixture
def mock_storage():
    """创建模拟Redis存储管理器"""
    return MockRedisStorageManager()


class TestDarwinSystemIntegration:
    """达尔文进化系统集成测试"""
    
    @pytest.fixture
    def darwin_system(self, mock_storage: MockRedisStorageManager) -> DarwinSystem:
        """创建Darwin系统"""
        return DarwinSystem(
            redis_storage=mock_storage,
            strategy_analyzer=AsyncMock(),
            scholar_engine=AsyncMock(),
            devil_auditor=AsyncMock(),
            arena=AsyncMock(),
            commander_engine=AsyncMock(),
            z2h_certifier=AsyncMock(),
        )

    @pytest.fixture
    def sample_factor(self) -> Factor:
        """创建示例因子"""
        return Factor(
            factor_id="test_factor_001",
            name="动量因子",
            expression="close / delay(close, 20) - 1",
            description="基于价格动量的因子",
            parameters={"lookback": 20},
            created_at=datetime.now(),
        )
    
    def test_darwin_system_initialization(self, darwin_system: DarwinSystem) -> None:
        """测试Darwin系统初始化"""
        assert darwin_system is not None
        assert darwin_system._redis_storage is not None

    def test_darwin_system_has_required_components(self, darwin_system: DarwinSystem) -> None:
        """测试Darwin系统包含必需组件"""
        assert darwin_system._strategy_analyzer is not None
        assert darwin_system._scholar_engine is not None
        assert darwin_system._devil_auditor is not None
        assert darwin_system._arena is not None
        assert darwin_system._commander_engine is not None
        assert darwin_system._z2h_certifier is not None

    def test_evolution_context_creation(self, sample_factor: Factor) -> None:
        """测试进化上下文创建"""
        context = EvolutionContext(factor=sample_factor, parent_capsule_id=None)
        assert context is not None
        assert context.factor == sample_factor
        assert context.parent_capsule_id is None

    def test_factor_creation(self) -> None:
        """测试因子创建"""
        factor = Factor(
            factor_id="test_001",
            name="测试因子",
            expression="close / open - 1",
            description="测试用因子",
            parameters={},
            created_at=datetime.now(),
        )
        assert factor.factor_id == "test_001"
        assert factor.name == "测试因子"
        assert factor.expression == "close / open - 1"


class TestKnowledgeManagementIntegration:
    """知识管理组件集成测试"""
    
    def test_gene_capsule_manager_initialization(self, mock_storage: MockRedisStorageManager) -> None:
        """测试基因胶囊管理器初始化"""
        manager = GeneCapsuleManager(redis_storage=mock_storage)
        assert manager is not None
        assert manager._redis_storage is not None

    @pytest.mark.asyncio
    async def test_gene_capsule_creation(self, mock_storage: MockRedisStorageManager) -> None:
        """测试基因胶囊创建"""
        # 创建测试数据
        arena_performance = ArenaPerformance(
            reality_track_score=85.0,
            hell_track_score=75.0,
            cross_market_score=80.0,
            sharpe_ratio=1.5,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=1.8,
            test_date=datetime.now(),
        )
        audit_result = AuditResult(
            passed=True,
            future_function_detected=False,
            issues=[],
            suggestions=[],
            audit_date=datetime.now(),
            confidence=0.95,
        )
        
        # 创建管理器并测试
        manager = GeneCapsuleManager(redis_storage=mock_storage)
        capsule = await manager.create_capsule(
            strategy_code="def strategy(): pass",
            parameter_config={"lookback": 20},
            analysis_report={"score": 85},
            arena_performance=arena_performance,
            audit_result=audit_result,
            evolution_history=[],
            z2h_status=Z2HStampStatus.GOLD,
        )
        assert capsule is not None
        assert capsule.capsule_id is not None
        assert capsule.strategy_code == "def strategy(): pass"
        assert capsule.z2h_stamp_status == Z2HStampStatus.GOLD

    def test_evolution_tree_initialization(self, mock_storage: MockRedisStorageManager) -> None:
        """测试演化树初始化"""
        tree = EvolutionTree(redis_storage=mock_storage)
        assert tree is not None
        assert tree._redis_storage is not None
        assert tree.family_id is not None

    @pytest.mark.asyncio
    async def test_evolution_tree_root_creation(self, mock_storage: MockRedisStorageManager) -> None:
        """测试演化树根节点创建"""
        # 创建测试数据
        arena_performance = ArenaPerformance(
            reality_track_score=85.0,
            hell_track_score=75.0,
            cross_market_score=80.0,
            sharpe_ratio=1.5,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=1.8,
            test_date=datetime.now(),
        )
        audit_result = AuditResult(
            passed=True,
            future_function_detected=False,
            issues=[],
            suggestions=[],
            audit_date=datetime.now(),
            confidence=0.95,
        )
        
        # 创建管理器并测试
        manager = GeneCapsuleManager(redis_storage=mock_storage)
        tree = EvolutionTree(redis_storage=mock_storage)
        
        capsule = await manager.create_capsule(
            strategy_code="def strategy(): pass",
            parameter_config={},
            analysis_report={},
            arena_performance=arena_performance,
            audit_result=audit_result,
            evolution_history=[],
            z2h_status=Z2HStampStatus.SILVER,
        )
        root_node = await tree.create_root(
            capsule_id=capsule.capsule_id,
            strategy_name="根策略",
            fitness=0.8,
        )
        assert root_node is not None
        assert root_node.node_id is not None
        assert root_node.capsule_id == capsule.capsule_id
        assert root_node.strategy_name == "根策略"
        assert root_node.fitness == 0.8
        assert root_node.generation == 0
    
    def test_anti_pattern_library_initialization(self, mock_storage: MockRedisStorageManager) -> None:
        """测试反向黑名单库初始化"""
        library = AntiPatternLibrary(redis_storage=mock_storage)
        assert library is not None
        assert library._redis_storage is not None

    @pytest.mark.asyncio
    async def test_anti_pattern_recording(self, mock_storage: MockRedisStorageManager) -> None:
        """测试反向模式记录"""
        library = AntiPatternLibrary(redis_storage=mock_storage)
        pattern = await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="过拟合",
            failure_step=FailureStep.ARENA_TEST,
        )
        assert pattern is not None
        assert pattern.pattern_id is not None
        assert pattern.failure_count >= 1

    @pytest.mark.asyncio
    async def test_anti_pattern_check(self, mock_storage: MockRedisStorageManager) -> None:
        """测试反向模式检查"""
        library = AntiPatternLibrary(redis_storage=mock_storage)
        await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="过拟合",
            failure_step=FailureStep.ARENA_TEST,
        )
        result = await library.check_pattern(
            factor_expression="close / delay(close, 2) - 1",
        )
        assert result is None or result.pattern_id is not None


class TestRedisStorageIntegration:
    """Redis存储集成测试"""
    
    def test_redis_storage_initialization(self, mock_storage: MockRedisStorageManager) -> None:
        """测试Redis存储初始化"""
        assert mock_storage is not None
        assert mock_storage._initialized is True

    @pytest.mark.asyncio
    async def test_essence_analysis_storage(self, mock_storage: MockRedisStorageManager) -> None:
        """测试本质分析存储"""
        await mock_storage.store_essence_analysis(
            strategy_id="test_strategy",
            data={"type": "momentum", "score": 85},
        )
        result = await mock_storage.get_essence_analysis("test_strategy")
        assert result is not None
        assert result["type"] == "momentum"
        assert result["score"] == 85

    @pytest.mark.asyncio
    async def test_gene_capsule_storage(self, mock_storage: MockRedisStorageManager) -> None:
        """测试基因胶囊存储"""
        await mock_storage.store_gene_capsule(
            capsule_id="capsule_001",
            data={"name": "test", "version": 1},
        )
        result = await mock_storage.get_gene_capsule("capsule_001")
        assert result is not None
        assert result["name"] == "test"
        assert result["version"] == 1

    @pytest.mark.asyncio
    async def test_batch_storage_operations(self, mock_storage: MockRedisStorageManager) -> None:
        """测试批量存储操作"""
        for i in range(3):
            await mock_storage.store_essence_analysis(
                strategy_id=f"batch_{i}",
                data={"value": i},
            )
        for i in range(3):
            result = await mock_storage.get_essence_analysis(f"batch_{i}")
            assert result is not None
            assert result["value"] == i

    def test_ttl_manager_access(self, mock_storage: MockRedisStorageManager) -> None:
        """测试TTL管理器访问"""
        ttl_manager = mock_storage.ttl_manager
        assert ttl_manager is not None


class TestComponentIntegration:
    """组件集成测试"""
    
    def test_all_components_share_redis_storage(self, mock_storage: MockRedisStorageManager) -> None:
        """测试所有组件共享Redis存储"""
        gene_capsule_manager = GeneCapsuleManager(redis_storage=mock_storage)
        evolution_tree = EvolutionTree(redis_storage=mock_storage)
        anti_pattern_library = AntiPatternLibrary(redis_storage=mock_storage)
        assert gene_capsule_manager._redis_storage is mock_storage
        assert evolution_tree._redis_storage is mock_storage
        assert anti_pattern_library._redis_storage is mock_storage

    def test_data_models_serialization(self) -> None:
        """测试数据模型序列化"""
        factor = Factor(
            factor_id="test_001",
            name="测试因子",
            expression="close / open - 1",
            description="测试用因子",
            parameters={"lookback": 20},
            created_at=datetime.now(),
        )
        factor_dict = factor.to_dict()
        assert factor_dict["factor_id"] == "test_001"
        assert factor_dict["name"] == "测试因子"
        assert factor_dict["expression"] == "close / open - 1"
        restored_factor = Factor.from_dict(factor_dict)
        assert restored_factor.factor_id == factor.factor_id
        assert restored_factor.name == factor.name
        assert restored_factor.expression == factor.expression

    def test_arena_performance_validation(self) -> None:
        """测试Arena表现数据验证"""
        performance = ArenaPerformance(
            reality_track_score=85.0,
            hell_track_score=75.0,
            cross_market_score=80.0,
            sharpe_ratio=1.5,
            max_drawdown=0.15,
            win_rate=0.6,
            profit_factor=1.8,
            test_date=datetime.now(),
        )
        assert performance.win_rate == 0.6
        assert performance.max_drawdown == 0.15
        with pytest.raises(ValueError, match="胜率必须在"):
            ArenaPerformance(
                reality_track_score=85.0,
                hell_track_score=75.0,
                cross_market_score=80.0,
                sharpe_ratio=1.5,
                max_drawdown=0.15,
                win_rate=1.5,
                profit_factor=1.8,
                test_date=datetime.now(),
            )

    def test_audit_result_validation(self) -> None:
        """测试审计结果数据验证"""
        audit = AuditResult(
            passed=True,
            future_function_detected=False,
            issues=[],
            suggestions=["建议增加止损"],
            audit_date=datetime.now(),
            confidence=0.95,
        )
        assert audit.passed is True
        assert audit.confidence == 0.95
        with pytest.raises(ValueError, match="置信度必须在"):
            AuditResult(
                passed=True,
                future_function_detected=False,
                issues=[],
                suggestions=[],
                audit_date=datetime.now(),
                confidence=1.5,
            )
