"""反向黑名单库属性测试

白皮书依据: 第五章 5.3.4 反向黑名单

本模块测试反向黑名单库的正确性属性。

**Feature: chapter-5-darwin-visualization-redis**
**Property 12: 反向模式记录完整性**
**Property 13: 反向模式查询正确性**
**Property 14: 反向模式存储正确性**
**Property 15: 反向模式相似度计算**
**Validates: Requirements 4.1-4.9**
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import pytest

from src.brain.darwin_data_models import FailureStep
from src.brain.anti_pattern_library import AntiPatternLibrary
from src.brain.redis_storage import RedisStorageManager


@pytest.fixture
async def clean_storage():
    """提供干净的Redis存储实例"""
    storage = RedisStorageManager(use_memory_fallback=True)
    await storage.initialize()
    
    # 清理所有反向模式数据
    try:
        await storage._redis_client.delete("mia:knowledge:anti_patterns")
    except:
        pass  # 如果键不存在，忽略错误
    
    yield storage
    
    # 测试后清理
    try:
        await storage._redis_client.delete("mia:knowledge:anti_patterns")
    except:
        pass
    
    await storage.close()


# ===== Property 12: 反向模式记录完整性 =====

class TestAntiPatternRecordCompleteness:
    """反向模式记录完整性测试
    
    **Property 12: 反向模式记录完整性**
    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """
    
    @pytest.mark.asyncio
    async def test_pattern_contains_description(self, clean_storage) -> None:
        """反向模式应包含失败模式描述
        
        **Validates: Requirements 4.1**
        """
        library = AntiPatternLibrary(clean_storage)
        
        pattern = await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="未来函数检测失败",
            failure_step=FailureStep.FUTURE_FUNCTION_DETECTION,
        )
        
        assert pattern.description is not None
        assert len(pattern.description) > 0
    
    @pytest.mark.asyncio
    async def test_pattern_contains_failure_count(self, clean_storage) -> None:
        """反向模式应包含失败次数统计
        
        **Validates: Requirements 4.2**
        """
        library = AntiPatternLibrary(clean_storage)
        
        pattern = await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="测试失败",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        assert pattern.failure_count == 1
        
        # 记录相同模式的失败
        pattern2 = await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="再次失败",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        assert pattern2.failure_count == 2
    
    @pytest.mark.asyncio
    async def test_pattern_contains_failure_cases(self, clean_storage) -> None:
        """反向模式应包含失败案例列表
        
        **Validates: Requirements 4.3**
        """
        library = AntiPatternLibrary(clean_storage)
        
        pattern = await library.record_failure(
            factor_expression="rank(close) * volume",
            failure_reason="因子分析失败",
            failure_step=FailureStep.FACTOR_ANALYSIS,
        )
        
        assert len(pattern.failure_cases) == 1
        assert pattern.failure_cases[0].factor_expression == "rank(close) * volume"
        assert pattern.failure_cases[0].failure_reason == "因子分析失败"
    
    @pytest.mark.asyncio
    async def test_pattern_contains_avoidance_suggestions(self, clean_storage) -> None:
        """反向模式应包含避免建议
        
        **Validates: Requirements 4.4**
        """
        library = AntiPatternLibrary(clean_storage)
        
        pattern = await library.record_failure(
            factor_expression="close / 0",
            failure_reason="除零错误",
            failure_step=FailureStep.FACTOR_ANALYSIS,
        )
        
        assert pattern.avoidance_suggestions is not None
        assert len(pattern.avoidance_suggestions) > 0


# ===== Property 13: 反向模式查询正确性 =====

class TestAntiPatternQueryCorrectness:
    """反向模式查询正确性测试
    
    **Property 13: 反向模式查询正确性**
    **Validates: Requirements 4.5, 4.6**
    """
    
    @pytest.mark.asyncio
    async def test_check_pattern_returns_match(self, clean_storage) -> None:
        """查询应返回匹配的失败模式
        
        **Validates: Requirements 4.5**
        """
        library = AntiPatternLibrary(clean_storage)
        
        # 记录失败模式
        await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="测试失败",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        # 检查相同表达式
        match = await library.check_pattern("close / delay(close, 1) - 1")
        
        assert match is not None
    
    @pytest.mark.asyncio
    async def test_check_pattern_returns_none_for_no_match(self, clean_storage) -> None:
        """查询不匹配的表达式应返回None
        
        **Validates: Requirements 4.5**
        """
        library = AntiPatternLibrary(clean_storage)
        
        # 记录失败模式
        await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="测试失败",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        # 检查完全不同的表达式
        match = await library.check_pattern("volume * open")
        
        assert match is None
    
    @pytest.mark.asyncio
    async def test_get_top_failures_returns_sorted(self, clean_storage) -> None:
        """获取失败次数最多的模式应按次数排序
        
        **Validates: Requirements 4.6**
        """
        library = AntiPatternLibrary(clean_storage)
        
        # 记录多个失败模式（使用完全不同的表达式）
        await library.record_failure(
            factor_expression="close / delay(close, 1) - 1",
            failure_reason="失败A",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        # 记录另一个完全不同的模式两次
        await library.record_failure(
            factor_expression="rank(volume) * open / high",
            failure_reason="失败B1",
            failure_step=FailureStep.FACTOR_ANALYSIS,
        )
        await library.record_failure(
            factor_expression="rank(volume) * open / high",
            failure_reason="失败B2",
            failure_step=FailureStep.FACTOR_ANALYSIS,
        )
        
        top = await library.get_top_failures(limit=2)
        
        assert len(top) == 2
        assert top[0].failure_count >= top[1].failure_count


# ===== Property 14: 反向模式存储正确性 =====

class TestAntiPatternStorageCorrectness:
    """反向模式存储正确性测试
    
    **Property 14: 反向模式存储正确性**
    **Validates: Requirements 4.7, 4.8**
    """
    
    @pytest.mark.asyncio
    async def test_pattern_saved_to_redis(self, clean_storage) -> None:
        """反向模式应保存到Redis
        
        **Validates: Requirements 4.7**
        """
        library = AntiPatternLibrary(clean_storage)
        
        await library.record_failure(
            factor_expression="test_expression",
            failure_reason="测试失败",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        # 验证已保存到Redis
        saved_patterns = await clean_storage.get_anti_patterns()
        assert len(saved_patterns) == 1
    
    @pytest.mark.asyncio
    async def test_pattern_loaded_from_redis(self, clean_storage) -> None:
        """反向模式应能从Redis加载
        
        **Validates: Requirements 4.7**
        """
        # 创建并保存模式
        library1 = AntiPatternLibrary(clean_storage)
        pattern = await library1.record_failure(
            factor_expression="test_expression",
            failure_reason="测试失败",
            failure_step=FailureStep.ARENA_TEST,
        )
        
        # 创建新实例并加载
        library2 = AntiPatternLibrary(clean_storage)
        patterns = await library2.get_all_patterns()
        
        assert len(patterns) == 1
        assert patterns[0].pattern_id == pattern.pattern_id


# ===== Property 15: 反向模式相似度计算 =====

class TestAntiPatternSimilarityCalculation:
    """反向模式相似度计算测试
    
    **Property 15: 反向模式相似度计算**
    **Validates: Requirements 4.9**
    """
    
    @pytest.mark.asyncio
    async def test_identical_expressions_similarity_is_one(self, clean_storage) -> None:
        """相同表达式的相似度应为1
        
        **Validates: Requirements 4.9**
        """
        library = AntiPatternLibrary(clean_storage)
        
        expr = "close / delay(close, 1) - 1"
        similarity = library.calculate_similarity(expr, expr)
        
        assert similarity == 1.0
    
    @pytest.mark.asyncio
    async def test_similarity_in_valid_range(self, clean_storage) -> None:
        """相似度应在[0, 1]范围内
        
        **Validates: Requirements 4.9**
        """
        library = AntiPatternLibrary(clean_storage)
        
        test_cases = [
            ("close", "open"),
            ("close / delay(close, 1)", "close / delay(close, 2)"),
            ("rank(close)", "rank(volume)"),
            ("a + b", "x * y"),
        ]
        
        for expr1, expr2 in test_cases:
            similarity = library.calculate_similarity(expr1, expr2)
            assert 0 <= similarity <= 1, f"相似度超出范围: {similarity}"
    
    @pytest.mark.asyncio
    async def test_empty_expression_similarity_is_zero(self, clean_storage) -> None:
        """空表达式的相似度应为0
        
        **Validates: Requirements 4.9**
        """
        library = AntiPatternLibrary(clean_storage)
        
        assert library.calculate_similarity("", "test") == 0.0
        assert library.calculate_similarity("test", "") == 0.0
        assert library.calculate_similarity("", "") == 0.0
    
    @pytest.mark.asyncio
    async def test_pattern_signature_extraction(self, clean_storage) -> None:
        """模式签名提取应正确标准化表达式
        
        **Validates: Requirements 4.9**
        """
        library = AntiPatternLibrary(clean_storage)
        
        # 测试数字替换
        sig1 = library.extract_pattern_signature("delay(close, 1)")
        sig2 = library.extract_pattern_signature("delay(close, 5)")
        assert sig1 == sig2  # 数字应被替换为相同占位符
        
        # 测试空白字符处理
        sig3 = library.extract_pattern_signature("close + open")
        sig4 = library.extract_pattern_signature("close+open")
        assert sig3 == sig4  # 空白字符应被移除


# ===== 边界条件测试 =====

class TestAntiPatternEdgeCases:
    """反向黑名单边界条件测试"""
    
    @pytest.mark.asyncio
    async def test_empty_expression_raises_error(self, clean_storage) -> None:
        """空因子表达式应抛出错误"""
        library = AntiPatternLibrary(clean_storage)
        
        with pytest.raises(ValueError, match="因子表达式不能为空"):
            await library.record_failure(
                factor_expression="",
                failure_reason="测试",
                failure_step=FailureStep.ARENA_TEST,
            )
    
    @pytest.mark.asyncio
    async def test_empty_reason_raises_error(self, clean_storage) -> None:
        """空失败原因应抛出错误"""
        library = AntiPatternLibrary(clean_storage)
        
        with pytest.raises(ValueError, match="失败原因不能为空"):
            await library.record_failure(
                factor_expression="test",
                failure_reason="",
                failure_step=FailureStep.ARENA_TEST,
            )
    
    @pytest.mark.asyncio
    async def test_check_empty_expression_raises_error(self, clean_storage) -> None:
        """检查空表达式应抛出错误"""
        library = AntiPatternLibrary(clean_storage)
        
        with pytest.raises(ValueError, match="因子表达式不能为空"):
            await library.check_pattern("")
    
    @pytest.mark.asyncio
    async def test_get_statistics_empty_library(self, clean_storage) -> None:
        """空库的统计信息应正确"""
        library = AntiPatternLibrary(clean_storage)
        
        stats = await library.get_statistics()
        
        assert stats["total_patterns"] == 0
        assert stats["total_failures"] == 0
