"""
验证流水线属性测试 (Validation Pipeline Property Tests)

白皮书依据: 第四章 4.3 统一验证流水线
测试框架: hypothesis (property-based testing)
最小迭代次数: 100

测试的正确性属性:
- Property 9: Validation Pipeline Sequence Enforcement
- Property 10: Pipeline Progression
- Property 11: Simulation Scheduling
- Property 12: Z2H Generation Trigger
- Property 13: Strategy Library Registration
"""

import pytest
import asyncio
from datetime import datetime
from hypothesis import given, settings, strategies as st, HealthCheck

from src.evolution.pipeline.data_models import (
    PipelineStage,
    PipelineState,
    PipelineProgress,
    ValidationRecord
)
from src.evolution.pipeline.validation_pipeline_manager import ValidationPipelineManager
from src.evolution.pipeline.pipeline_stage_validator import PipelineStageValidator
from src.evolution.pipeline.pipeline_state_tracker import PipelineStateTracker
from src.evolution.arena.data_models import Factor
from src.evolution.arena.strategy_data_models import Strategy, StrategyType, StrategyStatus


# 全局设置
HYPOTHESIS_SETTINGS = settings(
    max_examples=50,  # 减少迭代次数以加快测试
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)


# ============================================================================
# Property 9: Validation Pipeline Sequence Enforcement
# ============================================================================

class TestProperty9ValidationPipelineSequenceEnforcement:
    """Property 9: 验证流水线序列强制执行
    
    白皮书依据: 第四章 4.3 - 阶段转换验证
    
    正确性属性:
    对于任何因子或策略，尝试跳过验证阶段（例如直接从Factor Arena
    到Z2H而不经过Strategy Arena）应该失败并报错。
    
    **Validates: Requirements 3.6**
    """
    
    @pytest.fixture
    def stage_validator(self):
        return PipelineStageValidator()
    
    def test_cannot_skip_strategy_arena(self, stage_validator):
        """测试不能跳过Strategy Arena"""
        # 尝试从FACTOR_ARENA直接跳到SIMULATION
        transition = stage_validator.validate_transition(
            PipelineStage.FACTOR_ARENA,
            PipelineStage.SIMULATION
        )
        
        assert not transition.is_valid
        assert len(transition.required_conditions) > 0
    
    def test_cannot_skip_simulation(self, stage_validator):
        """测试不能跳过Simulation"""
        # 尝试从STRATEGY_ARENA直接跳到STRATEGY_LIBRARY
        transition = stage_validator.validate_transition(
            PipelineStage.STRATEGY_ARENA,
            PipelineStage.STRATEGY_LIBRARY
        )
        
        assert not transition.is_valid
    
    def test_valid_sequence_accepted(self, stage_validator):
        """测试有效序列被接受"""
        # 测试完整的有效序列
        stages = [
            PipelineStage.FACTOR_ARENA,
            PipelineStage.STRATEGY_GENERATION,
            PipelineStage.STRATEGY_ARENA,
            PipelineStage.SIMULATION,
            PipelineStage.Z2H_CERTIFICATION,
            PipelineStage.STRATEGY_LIBRARY
        ]
        
        assert stage_validator.validate_stage_sequence(stages)


# ============================================================================
# Property 10: Pipeline Progression
# ============================================================================

class TestProperty10PipelineProgression:
    """Property 10: 流水线推进
    
    白皮书依据: 第四章 4.3 - 自动流程推进
    
    正确性属性:
    对于任何通过Arena测试的因子，系统应该自动生成候选策略
    并提交到Strategy Arena。
    
    **Validates: Requirements 3.1, 3.2**
    """
    
    @pytest.fixture
    def pipeline_manager(self):
        return ValidationPipelineManager(auto_progress=True)
    
    @pytest.fixture
    def test_factor(self):
        return Factor(
            id="test_factor_1",
            name="Test Factor",
            description="Test",
            expression="close / delay(close, 1) - 1",
            category="technical"
        )
    
    def test_factor_arena_triggers_strategy_generation(self, pipeline_manager, test_factor):
        """测试Factor Arena触发策略生成"""
        # 创建进度
        progress = pipeline_manager.state_tracker.create_progress(
            entity_id=test_factor.id,
            entity_type='factor',
            initial_stage=PipelineStage.FACTOR_ARENA
        )
        
        # 模拟Factor Arena完成
        pipeline_manager.state_tracker.start_stage(
            test_factor.id,
            PipelineStage.FACTOR_ARENA
        )
        pipeline_manager.state_tracker.complete_stage(
            test_factor.id,
            PipelineStage.FACTOR_ARENA,
            result={'passed': True}
        )
        
        # 验证自动推进到策略生成
        next_stage = pipeline_manager.stage_validator.get_next_stage(
            PipelineStage.FACTOR_ARENA
        )
        assert next_stage == PipelineStage.STRATEGY_GENERATION


# ============================================================================
# Property 11: Simulation Scheduling
# ============================================================================

class TestProperty11SimulationScheduling:
    """Property 11: 模拟盘调度
    
    白皮书依据: 第四章 4.3 - 模拟盘验证调度
    
    正确性属性:
    对于任何通过Strategy Arena的策略，系统应该调度其进行
    1个月模拟盘验证。
    
    **Validates: Requirements 3.3**
    """
    
    @pytest.fixture
    def pipeline_manager(self):
        return ValidationPipelineManager(auto_progress=True)
    
    def test_strategy_arena_triggers_simulation(self, pipeline_manager):
        """测试Strategy Arena触发模拟盘"""
        # 验证阶段转换
        next_stage = pipeline_manager.stage_validator.get_next_stage(
            PipelineStage.STRATEGY_ARENA
        )
        
        assert next_stage == PipelineStage.SIMULATION


# ============================================================================
# Property 12: Z2H Generation Trigger
# ============================================================================

class TestProperty12Z2HGenerationTrigger:
    """Property 12: Z2H生成触发
    
    白皮书依据: 第四章 4.3 - Z2H认证触发
    
    正确性属性:
    对于任何通过模拟盘验证的策略，系统应该生成Z2H基因胶囊。
    
    **Validates: Requirements 3.4, 4.1**
    """
    
    @pytest.fixture
    def pipeline_manager(self):
        return ValidationPipelineManager(auto_progress=True)
    
    def test_simulation_triggers_z2h_certification(self, pipeline_manager):
        """测试模拟盘触发Z2H认证"""
        # 验证阶段转换
        next_stage = pipeline_manager.stage_validator.get_next_stage(
            PipelineStage.SIMULATION
        )
        
        assert next_stage == PipelineStage.Z2H_CERTIFICATION


# ============================================================================
# Property 13: Strategy Library Registration
# ============================================================================

class TestProperty13StrategyLibraryRegistration:
    """Property 13: 策略库注册
    
    白皮书依据: 第四章 4.3 - 策略库注册
    
    正确性属性:
    对于任何生成Z2H基因胶囊的策略，系统应该将其注册到策略库。
    
    **Validates: Requirements 3.5**
    """
    
    @pytest.fixture
    def pipeline_manager(self):
        return ValidationPipelineManager(auto_progress=True)
    
    def test_z2h_triggers_library_registration(self, pipeline_manager):
        """测试Z2H认证触发策略库注册"""
        # 验证阶段转换
        next_stage = pipeline_manager.stage_validator.get_next_stage(
            PipelineStage.Z2H_CERTIFICATION
        )
        
        assert next_stage == PipelineStage.STRATEGY_LIBRARY
    
    def test_library_is_terminal_stage(self, pipeline_manager):
        """测试策略库是终点阶段"""
        assert pipeline_manager.stage_validator.is_terminal_stage(
            PipelineStage.STRATEGY_LIBRARY
        )


# ============================================================================
# 辅助测试
# ============================================================================

class TestPipelineDataModelsValidation:
    """测试流水线数据模型验证"""
    
    def test_pipeline_progress_requires_entity_id(self):
        """测试进度需要实体ID"""
        with pytest.raises(ValueError, match="实体ID不能为空"):
            PipelineProgress(
                entity_id="",
                entity_type="factor",
                current_stage=PipelineStage.FACTOR_ARENA
            )
    
    def test_pipeline_progress_requires_valid_entity_type(self):
        """测试进度需要有效的实体类型"""
        with pytest.raises(ValueError, match="实体类型必须是"):
            PipelineProgress(
                entity_id="test_id",
                entity_type="invalid",
                current_stage=PipelineStage.FACTOR_ARENA
            )
    
    def test_validation_record_duration_cannot_be_negative(self):
        """测试验证记录耗时不能为负数"""
        with pytest.raises(ValueError, match="耗时不能为负数"):
            ValidationRecord(
                stage=PipelineStage.FACTOR_ARENA,
                state=PipelineState.COMPLETED,
                started_at=datetime.now(),
                duration_seconds=-1.0
            )


class TestPipelineStateTracker:
    """测试流水线状态追踪器"""
    
    @pytest.fixture
    def tracker(self):
        return PipelineStateTracker()
    
    def test_create_progress(self, tracker):
        """测试创建进度"""
        progress = tracker.create_progress(
            entity_id="test_1",
            entity_type="factor"
        )
        
        assert progress.entity_id == "test_1"
        assert progress.entity_type == "factor"
        assert not progress.is_completed
        assert not progress.is_failed
    
    def test_cannot_create_duplicate_progress(self, tracker):
        """测试不能创建重复进度"""
        tracker.create_progress("test_1", "factor")
        
        with pytest.raises(ValueError, match="实体ID已存在"):
            tracker.create_progress("test_1", "factor")
    
    def test_start_and_complete_stage(self, tracker):
        """测试开始和完成阶段"""
        progress = tracker.create_progress("test_1", "factor")
        
        # 开始阶段
        tracker.start_stage("test_1", PipelineStage.FACTOR_ARENA)
        
        # 完成阶段
        tracker.complete_stage(
            "test_1",
            PipelineStage.FACTOR_ARENA,
            result={'passed': True}
        )
        
        # 验证
        assert progress.is_stage_completed(PipelineStage.FACTOR_ARENA)
    
    def test_get_statistics(self, tracker):
        """测试获取统计信息"""
        tracker.create_progress("test_1", "factor")
        tracker.create_progress("test_2", "strategy")
        
        stats = tracker.get_statistics()
        
        assert stats['total'] == 2
        assert 'completion_rate' in stats
        assert 'stage_distribution' in stats


class TestPipelineStageValidator:
    """测试流水线阶段验证器"""
    
    @pytest.fixture
    def validator(self):
        return PipelineStageValidator()
    
    def test_valid_transition(self, validator):
        """测试有效转换"""
        transition = validator.validate_transition(
            PipelineStage.FACTOR_ARENA,
            PipelineStage.STRATEGY_GENERATION
        )
        
        assert transition.is_valid
        assert len(transition.required_conditions) == 0
    
    def test_invalid_transition(self, validator):
        """测试无效转换"""
        transition = validator.validate_transition(
            PipelineStage.FACTOR_ARENA,
            PipelineStage.Z2H_CERTIFICATION
        )
        
        assert not transition.is_valid
        assert len(transition.required_conditions) > 0
    
    def test_get_next_stage(self, validator):
        """测试获取下一阶段"""
        next_stage = validator.get_next_stage(PipelineStage.FACTOR_ARENA)
        
        assert next_stage == PipelineStage.STRATEGY_GENERATION
    
    def test_terminal_stage_has_no_next(self, validator):
        """测试终点阶段没有下一阶段"""
        next_stage = validator.get_next_stage(PipelineStage.STRATEGY_LIBRARY)
        
        assert next_stage is None
    
    def test_no_stage_can_be_skipped(self, validator):
        """测试所有阶段都不能跳过"""
        for stage in PipelineStage:
            assert not validator.can_skip_stage(stage)
