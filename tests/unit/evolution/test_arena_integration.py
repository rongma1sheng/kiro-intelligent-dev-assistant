"""Unit Tests for Arena Integration Module

白皮书依据: 第四章 4.2.1 - Arena集成单元测试
铁律依据: MIA编码铁律7 (测试覆盖率要求)

测试覆盖:
1. ArenaIntegration初始化
2. 因子提交功能
3. 重试机制
4. 因子验证
5. 结果处理
6. 统计信息
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np

from src.evolution.etf_lof.arena_integration import (
    ArenaIntegration,
    submit_to_arena
)
from src.evolution.etf_lof.data_models import ArenaTestResult
from src.evolution.etf_lof.exceptions import (
    FactorMiningError,
    ArenaSubmissionError,
    ArenaTestError
)
from src.evolution.factor_arena import (
    FactorArenaSystem,
    FactorTestResult,
    TrackType,
    ArenaTestConfig
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_arena_system():
    """创建mock Arena系统"""
    arena = Mock(spec=FactorArenaSystem)
    arena.is_running = True
    arena.pending_factors = []
    arena.testing_factors = {}
    arena.completed_tests = {}
    return arena


@pytest.fixture
def arena_integration(mock_arena_system):
    """创建Arena集成实例"""
    return ArenaIntegration(
        arena_system=mock_arena_system,
        max_retries=3,
        base_delay=0.1  # 测试时使用较短延迟
    )


@pytest.fixture
def sample_factor_expression():
    """示例因子表达式"""
    return "etf_premium_discount(close, nav)"


@pytest.fixture
def sample_arena_result():
    """示例Arena测试结果"""
    return FactorTestResult(
        factor_expression="etf_premium_discount(close, nav)",
        track_type=TrackType.REALITY,
        test_start_time=datetime.now() - timedelta(minutes=10),
        test_end_time=datetime.now(),
        
        # Reality Track指标
        ic_mean=0.06,
        ic_std=0.02,
        ir=3.0,
        sharpe_ratio=1.8,
        max_drawdown=-0.08,
        annual_return=0.25,
        win_rate=0.60,
        
        # Hell Track指标
        survival_rate=0.75,
        ic_decay_rate=0.15,
        recovery_ability=0.80,
        stress_score=0.30,
        
        # Cross-Market Track指标
        markets_passed=3,
        adaptability_score=0.70,
        consistency_score=0.65,
        
        passed=True
    )


# ============================================================================
# Test ArenaIntegration Initialization
# ============================================================================

class TestArenaIntegrationInit:
    """测试ArenaIntegration初始化"""
    
    def test_init_with_default_params(self):
        """测试默认参数初始化"""
        integration = ArenaIntegration()
        
        assert integration.arena_system is None
        assert integration.max_retries == 3
        assert integration.base_delay == 1.0
        assert integration.submission_history == []
        assert integration.stats['total_submissions'] == 0
    
    def test_init_with_custom_params(self, mock_arena_system):
        """测试自定义参数初始化"""
        integration = ArenaIntegration(
            arena_system=mock_arena_system,
            max_retries=5,
            base_delay=2.0
        )
        
        assert integration.arena_system == mock_arena_system
        assert integration.max_retries == 5
        assert integration.base_delay == 2.0
    
    def test_init_with_invalid_max_retries(self):
        """测试无效的max_retries"""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            ArenaIntegration(max_retries=-1)
    
    def test_init_with_invalid_base_delay(self):
        """测试无效的base_delay"""
        with pytest.raises(ValueError, match="base_delay must be > 0"):
            ArenaIntegration(base_delay=0)
    
    @pytest.mark.asyncio
    async def test_initialize_creates_arena_system(self):
        """测试initialize创建Arena系统"""
        integration = ArenaIntegration()
        
        with patch('src.evolution.etf_lof.arena_integration.FactorArenaSystem') as MockArena:
            mock_instance = AsyncMock()
            mock_instance.is_running = False
            MockArena.return_value = mock_instance
            
            await integration.initialize()
            
            assert integration.arena_system is not None
            mock_instance.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_with_existing_arena(self, arena_integration):
        """测试initialize使用已存在的Arena系统"""
        await arena_integration.initialize()
        
        # Arena系统应该保持不变
        assert arena_integration.arena_system.is_running


# ============================================================================
# Test Factor Submission
# ============================================================================

class TestFactorSubmission:
    """测试因子提交功能"""
    
    @pytest.mark.asyncio
    async def test_submit_valid_factor(self, arena_integration, sample_factor_expression):
        """测试提交有效因子"""
        await arena_integration.initialize()
        
        result = await arena_integration.submit_to_arena(
            factor_expression=sample_factor_expression,
            factor_type='etf',
            metadata={'test': True}
        )
        
        assert result.status == 'submitted'
        assert result.factor_expression == sample_factor_expression
        assert result.factor_type == 'etf'
        assert result.queue_position == 1
        assert arena_integration.stats['total_submissions'] == 1
        assert arena_integration.stats['successful_submissions'] == 1
    
    @pytest.mark.asyncio
    async def test_submit_empty_expression(self, arena_integration):
        """测试提交空表达式"""
        await arena_integration.initialize()
        
        with pytest.raises(ValueError, match="factor_expression不能为空"):
            await arena_integration.submit_to_arena(
                factor_expression="",
                factor_type='etf'
            )
    
    @pytest.mark.asyncio
    async def test_submit_invalid_factor_type(self, arena_integration, sample_factor_expression):
        """测试提交无效因子类型"""
        await arena_integration.initialize()
        
        with pytest.raises(ValueError, match="factor_type必须是'etf'或'lof'"):
            await arena_integration.submit_to_arena(
                factor_expression=sample_factor_expression,
                factor_type='invalid'
            )
    
    @pytest.mark.asyncio
    async def test_submit_with_validation_failure(self, arena_integration):
        """测试提交验证失败的因子"""
        await arena_integration.initialize()
        
        # 括号不匹配的表达式
        invalid_expression = "etf_premium_discount(close, nav"
        
        with pytest.raises(ArenaSubmissionError, match="因子验证失败"):
            await arena_integration.submit_to_arena(
                factor_expression=invalid_expression,
                factor_type='etf'
            )


# ============================================================================
# Test Retry Mechanism
# ============================================================================

class TestRetryMechanism:
    """测试重试机制"""
    
    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, arena_integration, sample_factor_expression):
        """测试连接错误时重试"""
        await arena_integration.initialize()
        
        # 模拟前2次失败,第3次成功
        attempt_count = [0]
        
        async def mock_submit(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ConnectionError("模拟连接错误")
            return ArenaTestResult(
                factor_expression=sample_factor_expression,
                factor_type='etf',
                submission_time=datetime.now(),
                status='submitted',
                queue_position=1
            )
        
        arena_integration._do_submit = mock_submit
        
        result = await arena_integration._submit_with_retry(
            sample_factor_expression, 'etf', None
        )
        
        assert result.status == 'submitted'
        assert attempt_count[0] == 3
        assert arena_integration.stats['retries_used'] == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self, arena_integration, sample_factor_expression):
        """测试重试耗尽"""
        await arena_integration.initialize()
        
        # 模拟所有尝试都失败
        async def mock_submit(*args, **kwargs):
            raise ConnectionError("持续连接错误")
        
        arena_integration._do_submit = mock_submit
        
        with pytest.raises(ArenaSubmissionError, match="已重试"):
            await arena_integration._submit_with_retry(
                sample_factor_expression, 'etf', None
            )
    
    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(self, arena_integration, sample_factor_expression):
        """测试验证错误不重试"""
        await arena_integration.initialize()
        
        attempt_count = [0]
        
        async def mock_submit(*args, **kwargs):
            attempt_count[0] += 1
            raise ValueError("验证错误")
        
        arena_integration._do_submit = mock_submit
        
        with pytest.raises(ArenaSubmissionError):
            await arena_integration._submit_with_retry(
                sample_factor_expression, 'etf', None
            )
        
        # 验证错误不应该重试
        assert attempt_count[0] == 1


# ============================================================================
# Test Factor Validation
# ============================================================================

class TestFactorValidation:
    """测试因子验证"""
    
    @pytest.mark.asyncio
    async def test_validate_valid_expression(self, arena_integration):
        """测试验证有效表达式"""
        result = await arena_integration.validate_factor_before_submission(
            "etf_premium_discount(close, nav)",
            "etf"
        )
        
        assert result['valid'] is True
        assert result['error'] is None
        assert result['complexity'] == 1
    
    @pytest.mark.asyncio
    async def test_validate_empty_expression(self, arena_integration):
        """测试验证空表达式"""
        result = await arena_integration.validate_factor_before_submission(
            "",
            "etf"
        )
        
        assert result['valid'] is False
        assert "不能为空" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_too_long_expression(self, arena_integration):
        """测试验证过长表达式"""
        long_expr = "a" * 1001
        
        result = await arena_integration.validate_factor_before_submission(
            long_expr,
            "etf"
        )
        
        assert result['valid'] is False
        assert "过长" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_unmatched_parentheses(self, arena_integration):
        """测试验证括号不匹配"""
        result = await arena_integration.validate_factor_before_submission(
            "etf_premium_discount(close, nav",
            "etf"
        )
        
        assert result['valid'] is False
        assert "括号" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_illegal_characters(self, arena_integration):
        """测试验证非法字符"""
        result = await arena_integration.validate_factor_before_submission(
            "etf_premium_discount(close, nav); DROP TABLE",
            "etf"
        )
        
        assert result['valid'] is False
        assert "非法字符" in result['error']
    
    @pytest.mark.asyncio
    async def test_validate_complexity_calculation(self, arena_integration):
        """测试复杂度计算"""
        result = await arena_integration.validate_factor_before_submission(
            "rank(delay(etf_premium_discount(close, nav), 5))",
            "etf"
        )
        
        assert result['valid'] is True
        assert result['complexity'] == 3  # 3个算子


# ============================================================================
# Test Result Processing
# ============================================================================

class TestResultProcessing:
    """测试结果处理"""
    
    @pytest.mark.asyncio
    async def test_process_passing_result(self, arena_integration, sample_arena_result):
        """测试处理通过的结果"""
        processed = await arena_integration.process_arena_result(sample_arena_result)
        
        assert processed.status == 'passed'
        assert processed.passed is True
        assert 0 <= processed.overall_score <= 100
        assert processed.reality_ic_mean == sample_arena_result.ic_mean
        assert processed.hell_survival_rate == sample_arena_result.survival_rate
        assert len(processed.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_process_failing_result(self, arena_integration):
        """测试处理失败的结果"""
        failing_result = FactorTestResult(
            factor_expression="bad_factor",
            track_type=TrackType.REALITY,
            test_start_time=datetime.now() - timedelta(minutes=10),
            test_end_time=datetime.now(),
            
            # 不满足通过条件
            ic_mean=0.02,  # < 0.05
            ic_std=0.01,
            ir=1.0,
            sharpe_ratio=1.0,  # < 1.5
            max_drawdown=-0.20,
            annual_return=0.10,
            win_rate=0.45,
            
            survival_rate=0.60,  # < 0.7
            ic_decay_rate=0.40,
            recovery_ability=0.50,
            stress_score=0.60,
            
            markets_passed=1,  # < 2
            adaptability_score=0.40,
            consistency_score=0.45,
            
            passed=False
        )
        
        processed = await arena_integration.process_arena_result(failing_result)
        
        assert processed.status == 'failed'
        assert processed.passed is False
        assert len(processed.recommendations) > 0
        # 应该包含改进建议
        assert any('IC过低' in rec or 'Reality Track' in rec for rec in processed.recommendations)
    
    @pytest.mark.asyncio
    async def test_process_result_with_invalid_times(self, arena_integration):
        """测试处理时间无效的结果"""
        invalid_result = FactorTestResult(
            factor_expression="test_factor",
            track_type=TrackType.REALITY,
            test_start_time=datetime.now(),
            test_end_time=datetime.now() - timedelta(minutes=10),  # 结束时间早于开始时间
            ic_mean=0.05,
            sharpe_ratio=1.5,
            survival_rate=0.7
        )
        
        with pytest.raises(ArenaTestError, match="测试结束时间早于开始时间"):
            await arena_integration.process_arena_result(invalid_result)


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """测试统计信息"""
    
    @pytest.mark.asyncio
    async def test_statistics_after_submissions(self, arena_integration, sample_factor_expression):
        """测试提交后的统计信息"""
        await arena_integration.initialize()
        
        # 提交3个因子
        for i in range(3):
            await arena_integration.submit_to_arena(
                factor_expression=f"{sample_factor_expression}_{i}",
                factor_type='etf'
            )
        
        stats = arena_integration.get_statistics()
        
        assert stats['total_submissions'] == 3
        assert stats['successful_submissions'] == 3
        assert stats['failed_submissions'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['avg_submission_time_ms'] > 0
        assert stats['history_size'] == 3
    
    def test_submission_history_limit(self, arena_integration):
        """测试提交历史记录限制"""
        # 添加超过1000条记录
        for i in range(1100):
            arena_integration._record_submission(
                f"factor_{i}", 'etf', None,
                ArenaTestResult(
                    factor_expression=f"factor_{i}",
                    factor_type='etf',
                    submission_time=datetime.now(),
                    status='submitted',
                    queue_position=i
                ),
                100.0
            )
        
        # 应该只保留最近1000条
        assert len(arena_integration.submission_history) == 1000


# ============================================================================
# Test Convenience Function
# ============================================================================

class TestConvenienceFunction:
    """测试便捷函数"""
    
    @pytest.mark.asyncio
    async def test_submit_to_arena_function(self, mock_arena_system):
        """测试submit_to_arena便捷函数"""
        with patch('src.evolution.etf_lof.arena_integration.ArenaIntegration') as MockIntegration:
            mock_instance = AsyncMock()
            mock_instance.submit_to_arena.return_value = ArenaTestResult(
                factor_expression="test",
                factor_type='etf',
                submission_time=datetime.now(),
                status='submitted',
                queue_position=1
            )
            MockIntegration.return_value = mock_instance
            
            result = await submit_to_arena(
                "test_factor",
                "etf",
                arena_system=mock_arena_system
            )
            
            assert result.status == 'submitted'
            mock_instance.initialize.assert_called_once()
            mock_instance.submit_to_arena.assert_called_once()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
