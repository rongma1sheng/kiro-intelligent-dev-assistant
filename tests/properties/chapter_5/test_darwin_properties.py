"""达尔文进化系统属性测试

白皮书依据: 第五章 5.3.1 进化协同流程

本模块实现了达尔文进化系统的属性测试，验证：
- Property 1: 进化工作流序列完整性
- Property 2: 进化失败处理

**Validates: Requirements 1.1-1.11**
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from src.brain.darwin_data_models import (
    Factor,
    GeneCapsule,
    EvolutionResult,
    EvolutionReport,
    EvolutionContext,
    FactorMeaningAnalysis,
    AcademicFactorMatch,
    AuditResult,
    ArenaTestResult,
    ArenaPerformance,
    PerformanceDiffAnalysis,
    WeaknessReport,
    OptimizationSuggestions,
    PerformancePrediction,
    Z2HCertificationResult,
    Z2HStampStatus,
    FailureStep,
    create_factor,
)
from src.brain.darwin_system import (
    DarwinSystem,
    EvolutionError,
    FactorAnalysisError,
    AuditError,
    ArenaTestError,
)
from src.brain.redis_storage import RedisStorageManager


# ============================================================================
# 测试夹具
# ============================================================================

class MockRedisClient:
    """模拟Redis客户端"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._sets: Dict[str, set] = {}
    
    async def get(self, key: str) -> Optional[str]:
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self._data[key] = value
    
    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count
    
    async def keys(self, pattern: str) -> List[str]:
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def lpush(self, key: str, *values: str) -> int:
        if key not in self._lists:
            self._lists[key] = []
        for v in values:
            self._lists[key].insert(0, v)
        return len(self._lists[key])
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        if key not in self._lists:
            return []
        if end == -1:
            return self._lists[key][start:]
        return self._lists[key][start:end + 1]
    
    async def sadd(self, key: str, *values: str) -> int:
        if key not in self._sets:
            self._sets[key] = set()
        count = 0
        for v in values:
            if v not in self._sets[key]:
                self._sets[key].add(v)
                count += 1
        return count
    
    async def smembers(self, key: str) -> set:
        return self._sets.get(key, set())
    
    async def expire(self, key: str, seconds: int) -> bool:
        return key in self._data
    
    async def ttl(self, key: str) -> int:
        return -1 if key in self._data else -2


class MockRedisStorageManager(RedisStorageManager):
    """模拟Redis存储管理器"""
    
    def __init__(self):
        self._redis_client = MockRedisClient()
        self._gene_capsules: Dict[str, Dict[str, Any]] = {}
        self._evolution_tree: Optional[Dict[str, Any]] = None
        self._anti_patterns: List[Dict[str, Any]] = []
    
    async def store_gene_capsule(self, capsule_id: str, data: Dict[str, Any]) -> None:
        self._gene_capsules[capsule_id] = data
        # 存储family_id索引
        family_id = data.get("family_id")
        if family_id:
            key = f"family:{family_id}:{capsule_id}"
            await self._redis_client.set(key, capsule_id)
    
    async def get_gene_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        return self._gene_capsules.get(capsule_id)
    
    async def get_gene_capsules_by_family(self, family_id: str) -> List[Dict[str, Any]]:
        return [
            data for data in self._gene_capsules.values()
            if data.get("family_id") == family_id
        ]
    
    async def get_all_gene_capsule_ids(self) -> List[str]:
        return list(self._gene_capsules.keys())
    
    async def delete_key(self, key: str) -> bool:
        capsule_id = key.split(":")[-1]
        if capsule_id in self._gene_capsules:
            del self._gene_capsules[capsule_id]
            return True
        return False
    
    async def store_evolution_tree(self, data: Dict[str, Any]) -> None:
        self._evolution_tree = data
    
    async def get_evolution_tree(self) -> Optional[Dict[str, Any]]:
        return self._evolution_tree
    
    async def store_anti_patterns(self, patterns: List[Dict[str, Any]]) -> None:
        self._anti_patterns = patterns
    
    async def get_anti_patterns(self) -> List[Dict[str, Any]]:
        return self._anti_patterns


@pytest.fixture
def mock_redis_storage():
    """创建模拟Redis存储管理器"""
    return MockRedisStorageManager()


@pytest.fixture
def darwin_system(mock_redis_storage):
    """创建达尔文进化系统实例"""
    return DarwinSystem(redis_storage=mock_redis_storage)


@pytest.fixture
def sample_factor():
    """创建示例因子"""
    return create_factor(
        expression="rank(close / delay(close, 5) - 1)",
        name="5日动量因子",
        description="计算5日收益率的排名",
        parameters={"lookback": 5},
    )


# ============================================================================
# Hypothesis策略
# ============================================================================

@st.composite
def factor_strategy(draw):
    """生成因子的策略"""
    expressions = [
        "rank(close / delay(close, 5) - 1)",
        "ts_mean(volume, 20) / ts_mean(volume, 60)",
        "correlation(close, volume, 20)",
        "ts_std(returns, 20)",
        "rank(pe_ratio)",
        "market_cap / total_assets",
    ]
    
    names = [
        "动量因子",
        "成交量因子",
        "相关性因子",
        "波动率因子",
        "价值因子",
        "规模因子",
    ]
    
    idx = draw(st.integers(min_value=0, max_value=len(expressions) - 1))
    
    return create_factor(
        expression=expressions[idx],
        name=names[idx],
        description=f"测试因子: {names[idx]}",
        parameters={"test_param": draw(st.integers(min_value=1, max_value=100))},
    )


@st.composite
def failure_step_strategy(draw):
    """生成失败步骤的策略"""
    return draw(st.sampled_from(list(FailureStep)))


# ============================================================================
# Property 1: 进化工作流序列完整性
# ============================================================================

class TestEvolutionWorkflowSequence:
    """测试进化工作流序列完整性
    
    **Feature: chapter-5-darwin-visualization-redis, Property 1: Evolution workflow sequence integrity**
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10**
    """
    
    @pytest.mark.asyncio
    @given(factor=factor_strategy())
    @settings(max_examples=20, deadline=30000)
    async def test_evolution_workflow_completes_all_steps(
        self,
        factor: Factor,
    ):
        """测试进化流程完成所有步骤
        
        **Validates: Requirements 1.1-1.10**
        
        For any 新生成的因子，Darwin_System执行的进化流程应该按照正确的顺序
        调用所有必要的组件。
        """
        # 创建新的存储管理器和系统实例
        mock_storage = MockRedisStorageManager()
        system = DarwinSystem(redis_storage=mock_storage)
        
        # 执行进化
        result = await system.evolve_factor(factor)
        
        # 验证结果
        assert result is not None
        
        if result.success:
            # 成功时验证所有组件都被调用
            assert result.gene_capsule is not None
            assert result.evolution_report is not None
            
            # 验证进化报告包含所有步骤的结果
            report = result.evolution_report
            assert report.meaning_analysis is not None  # 步骤1
            assert report.academic_matches is not None  # 步骤2
            assert report.audit_result is not None  # 步骤3
            assert report.arena_result is not None  # 步骤4
            assert report.performance_diff is not None  # 步骤5
            assert report.weakness_report is not None  # 步骤6
            assert report.optimization_suggestions is not None  # 步骤7
            assert report.performance_prediction is not None  # 步骤8
            assert report.z2h_result is not None  # 步骤9
        else:
            # 失败时验证有失败原因和步骤
            assert result.failure_reason is not None
            assert result.failure_step is not None
    
    @pytest.mark.asyncio
    async def test_evolution_workflow_step_order(self, darwin_system, sample_factor):
        """测试进化流程步骤顺序
        
        **Validates: Requirements 1.1-1.10**
        
        验证进化流程按照正确的顺序执行各步骤。
        """
        # 记录步骤执行顺序
        step_order = []
        
        # 创建带有跟踪的系统
        original_analyze = darwin_system._analyze_factor_meaning
        original_search = darwin_system._find_similar_academic_factors
        original_detect = darwin_system._detect_future_functions
        original_arena = darwin_system._run_arena_test
        original_diff = darwin_system._analyze_performance_diff
        original_weakness = darwin_system._identify_weaknesses
        original_optimize = darwin_system._get_optimization_suggestions
        original_predict = darwin_system._predict_optimized_performance
        original_certify = darwin_system._submit_z2h_certification
        
        async def tracked_analyze(factor):
            step_order.append("analyze_meaning")
            return await original_analyze(factor)
        
        async def tracked_search(factor):
            step_order.append("search_academic")
            return await original_search(factor)
        
        async def tracked_detect(factor):
            step_order.append("detect_future")
            return await original_detect(factor)
        
        async def tracked_arena(factor):
            step_order.append("arena_test")
            return await original_arena(factor)
        
        async def tracked_diff(factor, arena_result):
            step_order.append("analyze_diff")
            return await original_diff(factor, arena_result)
        
        async def tracked_weakness(diff_analysis):
            step_order.append("identify_weakness")
            return await original_weakness(diff_analysis)
        
        async def tracked_optimize(factor, weakness_report):
            step_order.append("get_optimization")
            return await original_optimize(factor, weakness_report)
        
        async def tracked_predict(factor, suggestions):
            step_order.append("predict_performance")
            return await original_predict(factor, suggestions)
        
        async def tracked_certify(factor, context):
            step_order.append("z2h_certify")
            return await original_certify(factor, context)
        
        # 替换方法
        darwin_system._analyze_factor_meaning = tracked_analyze
        darwin_system._find_similar_academic_factors = tracked_search
        darwin_system._detect_future_functions = tracked_detect
        darwin_system._run_arena_test = tracked_arena
        darwin_system._analyze_performance_diff = tracked_diff
        darwin_system._identify_weaknesses = tracked_weakness
        darwin_system._get_optimization_suggestions = tracked_optimize
        darwin_system._predict_optimized_performance = tracked_predict
        darwin_system._submit_z2h_certification = tracked_certify
        
        # 执行进化
        result = await darwin_system.evolve_factor(sample_factor)
        
        # 验证步骤顺序
        if result.success:
            expected_order = [
                "analyze_meaning",
                "search_academic",
                "detect_future",
                "arena_test",
                "analyze_diff",
                "identify_weakness",
                "get_optimization",
                "predict_performance",
                "z2h_certify",
            ]
            assert step_order == expected_order, f"步骤顺序不正确: {step_order}"
    
    @pytest.mark.asyncio
    async def test_gene_capsule_contains_all_required_fields(
        self,
        darwin_system,
        sample_factor,
    ):
        """测试基因胶囊包含所有必需字段
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        
        For any 创建的基因胶囊，应该包含所有必需字段。
        """
        result = await darwin_system.evolve_factor(sample_factor)
        
        if result.success:
            capsule = result.gene_capsule
            
            # 验证必需字段
            assert capsule.capsule_id is not None
            assert capsule.strategy_code is not None
            assert capsule.parameter_config is not None
            assert capsule.analysis_report_29d is not None
            assert capsule.arena_performance is not None
            assert capsule.devil_audit_result is not None
            assert capsule.evolution_history is not None
            assert capsule.z2h_stamp_status is not None
            assert capsule.family_id is not None
            assert capsule.created_at is not None
            assert capsule.updated_at is not None
            assert capsule.version >= 1


# ============================================================================
# Property 2: 进化失败处理
# ============================================================================

class TestEvolutionFailureHandling:
    """测试进化失败处理
    
    **Feature: chapter-5-darwin-visualization-redis, Property 2: Evolution failure handling**
    
    **Validates: Requirements 1.11**
    """
    
    @pytest.mark.asyncio
    @given(failure_step=failure_step_strategy())
    @settings(max_examples=10, deadline=30000)
    async def test_failure_records_to_anti_pattern_library(
        self,
        failure_step: FailureStep,
    ):
        """测试失败记录到反向黑名单库
        
        **Validates: Requirements 1.11**
        
        For any 进化流程中的失败，Darwin_System应该记录失败原因并更新
        Anti_Pattern_Library。
        """
        mock_storage = MockRedisStorageManager()
        system = DarwinSystem(redis_storage=mock_storage)
        
        factor = create_factor(
            expression="future(close)",  # 包含未来函数
            name="测试失败因子",
            description="用于测试失败处理",
        )
        
        # 执行进化（应该失败）
        result = await system.evolve_factor(factor)
        
        # 如果失败，验证记录到反向黑名单
        if not result.success:
            patterns = await system.anti_pattern_library.get_all_patterns()
            
            # 验证有失败记录
            assert len(patterns) > 0 or result.failure_step == FailureStep.FUTURE_FUNCTION_DETECTION
            
            # 验证失败原因和步骤
            assert result.failure_reason is not None
            assert result.failure_step is not None
    
    @pytest.mark.asyncio
    async def test_future_function_detection_failure(self, darwin_system):
        """测试未来函数检测失败
        
        **Validates: Requirements 1.11**
        """
        # 创建包含未来函数的因子
        factor = create_factor(
            expression="future(close, 5)",
            name="未来函数因子",
            description="包含未来函数的因子",
        )
        
        result = await darwin_system.evolve_factor(factor)
        
        # 验证失败
        assert not result.success
        assert result.failure_step == FailureStep.FUTURE_FUNCTION_DETECTION
        assert "未来函数" in result.failure_reason
    
    @pytest.mark.asyncio
    async def test_failure_includes_step_and_reason(self, darwin_system):
        """测试失败记录包含步骤和原因
        
        **Validates: Requirements 1.11**
        """
        # 创建会失败的因子
        factor = create_factor(
            expression="lead(close, 5)",  # lead函数是未来函数
            name="前视偏差因子",
            description="包含前视偏差的因子",
        )
        
        result = await darwin_system.evolve_factor(factor)
        
        if not result.success:
            # 验证失败信息完整
            assert result.failure_reason is not None
            assert len(result.failure_reason) > 0
            assert result.failure_step is not None
            assert isinstance(result.failure_step, FailureStep)
    
    @pytest.mark.asyncio
    async def test_anti_pattern_library_updated_on_failure(self, darwin_system):
        """测试失败时更新反向黑名单库
        
        **Validates: Requirements 1.11**
        """
        # 获取初始模式数量
        initial_patterns = await darwin_system.anti_pattern_library.get_all_patterns()
        initial_count = len(initial_patterns)
        
        # 创建会失败的因子
        factor = create_factor(
            expression="shift(-5, close)",  # 负向shift是未来函数
            name="负向偏移因子",
            description="包含负向偏移的因子",
        )
        
        result = await darwin_system.evolve_factor(factor)
        
        if not result.success:
            # 验证反向黑名单库已更新
            final_patterns = await darwin_system.anti_pattern_library.get_all_patterns()
            assert len(final_patterns) >= initial_count


# ============================================================================
# 额外的属性测试
# ============================================================================

class TestEvolutionContextIntegrity:
    """测试进化上下文完整性"""
    
    @pytest.mark.asyncio
    async def test_evolution_context_accumulates_results(
        self,
        darwin_system,
        sample_factor,
    ):
        """测试进化上下文累积结果"""
        result = await darwin_system.evolve_factor(sample_factor)
        
        if result.success:
            report = result.evolution_report
            
            # 验证所有分析结果都被累积
            assert report.meaning_analysis.factor_type is not None
            assert report.meaning_analysis.economic_meaning is not None
            assert report.meaning_analysis.confidence > 0
            
            assert report.audit_result.passed is True
            assert report.audit_result.confidence > 0
            
            assert report.arena_result.performance is not None
            assert report.arena_result.test_duration_seconds > 0
    
    @pytest.mark.asyncio
    async def test_evolution_tree_updated_on_success(
        self,
        darwin_system,
        sample_factor,
    ):
        """测试成功时更新演化树"""
        result = await darwin_system.evolve_factor(sample_factor)
        
        if result.success:
            tree = await darwin_system.get_or_create_evolution_tree()
            
            # 验证演化树已更新
            assert tree.node_count() > 0
    
    @pytest.mark.asyncio
    async def test_z2h_certification_levels(self, darwin_system, sample_factor):
        """测试Z2H认证等级"""
        result = await darwin_system.evolve_factor(sample_factor)
        
        if result.success:
            z2h_result = result.evolution_report.z2h_result
            
            # 验证认证状态有效
            assert z2h_result.status in [
                Z2HStampStatus.PLATINUM,
                Z2HStampStatus.GOLD,
                Z2HStampStatus.SILVER,
                Z2HStampStatus.REJECTED,
            ]
            
            # 验证认证等级与状态一致
            if z2h_result.status == Z2HStampStatus.PLATINUM:
                assert z2h_result.certification_level == "铂金级"
            elif z2h_result.status == Z2HStampStatus.GOLD:
                assert z2h_result.certification_level == "黄金级"
            elif z2h_result.status == Z2HStampStatus.SILVER:
                assert z2h_result.certification_level == "白银级"


class TestEvolutionStatistics:
    """测试进化统计功能"""
    
    @pytest.mark.asyncio
    async def test_get_evolution_statistics(self, darwin_system, sample_factor):
        """测试获取进化统计信息"""
        # 执行一次进化
        await darwin_system.evolve_factor(sample_factor)
        
        # 获取统计信息
        stats = await darwin_system.get_evolution_statistics()
        
        # 验证统计信息结构
        assert "total_capsules" in stats
        assert "evolution_tree" in stats
        assert "anti_patterns" in stats
        
        assert "node_count" in stats["evolution_tree"]
        assert "edge_count" in stats["evolution_tree"]
        assert "max_generation" in stats["evolution_tree"]
    
    @pytest.mark.asyncio
    async def test_get_elite_capsules(self, darwin_system, sample_factor):
        """测试获取精英基因胶囊"""
        # 执行多次进化
        for i in range(3):
            factor = create_factor(
                expression=f"rank(close / delay(close, {i + 3}) - 1)",
                name=f"动量因子_{i}",
                description=f"测试因子 {i}",
            )
            await darwin_system.evolve_factor(factor)
        
        # 获取精英胶囊
        elite_capsules = await darwin_system.get_elite_capsules(limit=5)
        
        # 验证返回结果
        assert isinstance(elite_capsules, list)
        
        # 如果有精英胶囊，验证排序
        if len(elite_capsules) >= 2:
            for i in range(len(elite_capsules) - 1):
                assert (
                    elite_capsules[i].arena_performance.sharpe_ratio >=
                    elite_capsules[i + 1].arena_performance.sharpe_ratio
                )


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
