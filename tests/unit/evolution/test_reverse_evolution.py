"""
反向进化单元测试

白皮书依据: 第一章 1.5.4 进化态任务调度
测试范围: ReverseEvolution的淘汰样本分析和失败模式提取功能
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from src.evolution.reverse_evolution import (
    ReverseEvolution,
    EliminatedSample,
    FailurePattern,
    AutopsyReport,
    FailureType,
    EliminationStage
)


class TestFailureType:
    """FailureType枚举测试"""
    
    def test_failure_type_values(self):
        """测试失败类型枚举值"""
        assert FailureType.LOW_IC.value == "IC过低"
        assert FailureType.HIGH_TURNOVER.value == "换手率过高"
        assert FailureType.OVERFITTING.value == "过拟合"
        assert FailureType.HIGH_DRAWDOWN.value == "回撤过大"


class TestEliminationStage:
    """EliminationStage枚举测试"""
    
    def test_elimination_stage_values(self):
        """测试淘汰阶段枚举值"""
        assert EliminationStage.FACTOR_ARENA.value == "因子Arena"
        assert EliminationStage.SPARTA_ARENA.value == "斯巴达Arena"
        assert EliminationStage.SIMULATION.value == "模拟盘"
        assert EliminationStage.LIVE.value == "实盘"


class TestEliminatedSample:
    """EliminatedSample数据类测试"""
    
    def test_sample_creation(self):
        """测试样本创建"""
        sample = EliminatedSample(
            sample_id="factor_001",
            sample_type="factor",
            name="动量因子",
            elimination_stage=EliminationStage.FACTOR_ARENA,
            elimination_date=date.today(),
            failure_types=[FailureType.LOW_IC],
            metrics={"ic": 0.01, "sharpe": 0.3}
        )
        
        assert sample.sample_id == "factor_001"
        assert sample.sample_type == "factor"
        assert sample.elimination_stage == EliminationStage.FACTOR_ARENA
    
    def test_sample_to_dict(self):
        """测试样本转字典"""
        sample = EliminatedSample(
            sample_id="factor_001",
            sample_type="factor",
            name="测试因子",
            elimination_stage=EliminationStage.FACTOR_ARENA,
            elimination_date=date.today()
        )
        
        result = sample.to_dict()
        
        assert result["sample_id"] == "factor_001"
        assert result["elimination_stage"] == "因子Arena"


class TestFailurePattern:
    """FailurePattern数据类测试"""
    
    def test_pattern_creation(self):
        """测试模式创建"""
        pattern = FailurePattern(
            pattern_id="pattern_low_ic",
            failure_type=FailureType.LOW_IC,
            occurrence_count=10,
            affected_samples=["f1", "f2", "f3"],
            suggestion="增加因子复杂度"
        )
        
        assert pattern.pattern_id == "pattern_low_ic"
        assert pattern.occurrence_count == 10
        assert len(pattern.affected_samples) == 3
    
    def test_pattern_to_dict(self):
        """测试模式转字典"""
        pattern = FailurePattern(
            pattern_id="pattern_test",
            failure_type=FailureType.OVERFITTING,
            occurrence_count=5
        )
        
        result = pattern.to_dict()
        
        assert result["failure_type"] == "过拟合"
        assert result["occurrence_count"] == 5


class TestReverseEvolution:
    """ReverseEvolution分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return ReverseEvolution(
            ic_threshold=0.03,
            sharpe_threshold=0.5,
            drawdown_threshold=0.2
        )
    
    @pytest.fixture
    def sample_low_ic(self):
        """创建低IC样本"""
        return EliminatedSample(
            sample_id="factor_001",
            sample_type="factor",
            name="低IC因子",
            elimination_stage=EliminationStage.FACTOR_ARENA,
            elimination_date=date.today(),
            metrics={"ic": 0.01, "sharpe": 0.8}
        )
    
    @pytest.fixture
    def sample_high_drawdown(self):
        """创建高回撤样本"""
        return EliminatedSample(
            sample_id="strategy_001",
            sample_type="strategy",
            name="高回撤策略",
            elimination_stage=EliminationStage.SPARTA_ARENA,
            elimination_date=date.today(),
            metrics={"ic": 0.05, "sharpe": 0.6, "max_drawdown": 0.35}
        )
    
    def test_init_default(self):
        """测试默认初始化"""
        analyzer = ReverseEvolution()
        
        assert analyzer.ic_threshold == 0.03
        assert analyzer.sharpe_threshold == 0.5
    
    def test_init_custom(self):
        """测试自定义初始化"""
        analyzer = ReverseEvolution(
            ic_threshold=0.05,
            sharpe_threshold=1.0
        )
        
        assert analyzer.ic_threshold == 0.05
        assert analyzer.sharpe_threshold == 1.0
    
    def test_add_eliminated_sample(self, analyzer, sample_low_ic):
        """测试添加淘汰样本"""
        analyzer.add_eliminated_sample(sample_low_ic)
        
        stats = analyzer.get_statistics()
        assert stats["total_samples"] == 1
    
    def test_add_eliminated_samples_batch(self, analyzer, sample_low_ic, sample_high_drawdown):
        """测试批量添加样本"""
        analyzer.add_eliminated_samples([sample_low_ic, sample_high_drawdown])
        
        stats = analyzer.get_statistics()
        assert stats["total_samples"] == 2
    
    def test_diagnose_failure_low_ic(self, analyzer):
        """测试诊断低IC失败"""
        sample = EliminatedSample(
            sample_id="test",
            sample_type="factor",
            name="测试",
            elimination_stage=EliminationStage.FACTOR_ARENA,
            elimination_date=date.today(),
            metrics={"ic": 0.01}
        )
        
        failures = analyzer._diagnose_failure(sample)
        
        assert FailureType.LOW_IC in failures
    
    def test_diagnose_failure_high_drawdown(self, analyzer):
        """测试诊断高回撤失败"""
        sample = EliminatedSample(
            sample_id="test",
            sample_type="strategy",
            name="测试",
            elimination_stage=EliminationStage.SPARTA_ARENA,
            elimination_date=date.today(),
            metrics={"max_drawdown": 0.35}
        )
        
        failures = analyzer._diagnose_failure(sample)
        
        assert FailureType.HIGH_DRAWDOWN in failures
    
    def test_diagnose_failure_overfitting(self, analyzer):
        """测试诊断过拟合"""
        sample = EliminatedSample(
            sample_id="test",
            sample_type="strategy",
            name="测试",
            elimination_stage=EliminationStage.SIMULATION,
            elimination_date=date.today(),
            metrics={"train_sharpe": 3.0, "test_sharpe": 1.0}
        )
        
        failures = analyzer._diagnose_failure(sample)
        
        assert FailureType.OVERFITTING in failures
    
    def test_analyze_empty(self, analyzer):
        """测试空样本分析"""
        report = analyzer.analyze()
        
        assert report.total_samples == 0
        assert len(report.improvement_suggestions) > 0
    
    def test_analyze_with_samples(self, analyzer, sample_low_ic, sample_high_drawdown):
        """测试有样本的分析"""
        analyzer.add_eliminated_samples([sample_low_ic, sample_high_drawdown])
        
        report = analyzer.analyze()
        
        assert report.total_samples == 2
        assert len(report.failure_patterns) > 0
        assert len(report.stage_distribution) > 0
    
    def test_analyze_stage_distribution(self, analyzer):
        """测试阶段分布分析"""
        samples = [
            EliminatedSample(
                sample_id=f"s{i}",
                sample_type="factor",
                name=f"因子{i}",
                elimination_stage=EliminationStage.FACTOR_ARENA,
                elimination_date=date.today(),
                metrics={"ic": 0.01}
            )
            for i in range(3)
        ]
        samples.append(EliminatedSample(
            sample_id="s4",
            sample_type="strategy",
            name="策略",
            elimination_stage=EliminationStage.SPARTA_ARENA,
            elimination_date=date.today(),
            metrics={"sharpe": 0.2}
        ))
        
        analyzer.add_eliminated_samples(samples)
        report = analyzer.analyze()
        
        assert report.stage_distribution["因子Arena"] == 3
        assert report.stage_distribution["斯巴达Arena"] == 1
    
    def test_analyze_type_distribution(self, analyzer):
        """测试类型分布分析"""
        samples = [
            EliminatedSample(
                sample_id="s1",
                sample_type="factor",
                name="因子1",
                elimination_stage=EliminationStage.FACTOR_ARENA,
                elimination_date=date.today(),
                failure_types=[FailureType.LOW_IC]
            ),
            EliminatedSample(
                sample_id="s2",
                sample_type="factor",
                name="因子2",
                elimination_stage=EliminationStage.FACTOR_ARENA,
                elimination_date=date.today(),
                failure_types=[FailureType.LOW_IC, FailureType.HIGH_TURNOVER]
            )
        ]
        
        analyzer.add_eliminated_samples(samples)
        report = analyzer.analyze()
        
        assert report.type_distribution["IC过低"] == 2
        assert report.type_distribution["换手率过高"] == 1
    
    def test_get_samples_by_failure(self, analyzer, sample_low_ic, sample_high_drawdown):
        """测试按失败类型获取样本"""
        analyzer.add_eliminated_samples([sample_low_ic, sample_high_drawdown])
        
        low_ic_samples = analyzer.get_samples_by_failure(FailureType.LOW_IC)
        
        assert len(low_ic_samples) >= 1
    
    def test_get_samples_by_stage(self, analyzer, sample_low_ic, sample_high_drawdown):
        """测试按阶段获取样本"""
        analyzer.add_eliminated_samples([sample_low_ic, sample_high_drawdown])
        
        arena_samples = analyzer.get_samples_by_stage(EliminationStage.FACTOR_ARENA)
        
        assert len(arena_samples) == 1
    
    def test_clear_samples(self, analyzer, sample_low_ic):
        """测试清除样本"""
        analyzer.add_eliminated_sample(sample_low_ic)
        analyzer.clear_samples()
        
        stats = analyzer.get_statistics()
        assert stats["total_samples"] == 0
    
    def test_get_statistics(self, analyzer, sample_low_ic, sample_high_drawdown):
        """测试获取统计"""
        analyzer.add_eliminated_samples([sample_low_ic, sample_high_drawdown])
        
        stats = analyzer.get_statistics()
        
        assert stats["total_samples"] == 2
        assert stats["factor_samples"] == 1
        assert stats["strategy_samples"] == 1


class TestAutopsyReport:
    """AutopsyReport报告类测试"""
    
    def test_report_creation(self):
        """测试报告创建"""
        report = AutopsyReport(
            report_date=date.today(),
            total_samples=10,
            improvement_suggestions=["建议1", "建议2"]
        )
        
        assert report.total_samples == 10
        assert len(report.improvement_suggestions) == 2
    
    def test_report_to_dict(self):
        """测试报告转字典"""
        report = AutopsyReport(
            report_date=date.today(),
            total_samples=5
        )
        
        result = report.to_dict()
        
        assert result["total_samples"] == 5
        assert "timestamp" in result


class TestReverseEvolutionAsync:
    """异步功能测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return ReverseEvolution()
    
    @pytest.mark.asyncio
    async def test_analyze_async(self, analyzer):
        """测试异步分析"""
        sample = EliminatedSample(
            sample_id="test",
            sample_type="factor",
            name="测试",
            elimination_stage=EliminationStage.FACTOR_ARENA,
            elimination_date=date.today(),
            metrics={"ic": 0.01}
        )
        
        analyzer.add_eliminated_sample(sample)
        report = await analyzer.analyze_async()
        
        assert isinstance(report, AutopsyReport)
        assert report.total_samples == 1
