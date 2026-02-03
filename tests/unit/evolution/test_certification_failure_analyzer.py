"""认证失败分析器单元测试

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 失败分析

测试覆盖：
- 失败分析报告生成
- 失败类别识别
- 阶段和层级分析
- 未达标指标提取
- 与达标策略对比
- 改进建议生成
- 失败统计
- 报告导出

Author: MIA System
Version: 1.0.0
"""

import pytest
from datetime import datetime
from typing import Dict, Any
import json
import tempfile
import os

from src.evolution.certification_failure_analyzer import (
    CertificationFailureAnalyzer,
    FailureCategory,
    FailedMetric,
    LayerFailureDetail,
    StageFailureDetail,
    ComparisonWithSuccessful,
    ImprovementSuggestion,
    FailureAnalysisReport
)
from src.evolution.z2h_data_models import CertificationLevel


class TestCertificationFailureAnalyzer:
    """测试CertificationFailureAnalyzer类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return CertificationFailureAnalyzer()
    
    @pytest.fixture
    def sample_arena_result_failed_layer1(self):
        """示例Arena结果 - 第一层失败"""
        return {
            "overall_score": 0.70,
            "layer_results": {
                "layer_1": {
                    "name": "投研级指标验证",
                    "score": 0.65,
                    "required_score": 0.80,
                    "passed": False,
                    "metrics": {
                        "sharpe_ratio": 1.0,
                        "max_drawdown": 0.20,
                        "win_rate": 0.50
                    },
                    "thresholds": {
                        "sharpe_ratio": 1.5,
                        "max_drawdown": 0.15,
                        "win_rate": 0.55
                    },
                    "failed_metrics": ["sharpe_ratio", "max_drawdown", "win_rate"],
                    "failure_reason": "投研级指标未达标"
                },
                "layer_2": {
                    "name": "时间稳定性验证",
                    "score": 0.85,
                    "required_score": 0.75,
                    "passed": True,
                    "metrics": {},
                    "thresholds": {},
                    "failed_metrics": []
                }
            }
        }
    
    @pytest.fixture
    def sample_simulation_result_failed(self):
        """示例模拟盘结果 - 失败"""
        return {
            "passed": False,
            "overall_metrics": {
                "monthly_return": 0.03,
                "sharpe_ratio": 1.0,
                "max_drawdown": 0.18,
                "win_rate": 0.52
            },
            "failed_criteria": ["monthly_return", "sharpe_ratio", "max_drawdown", "win_rate"]
        }
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert isinstance(analyzer.failure_statistics, dict)
        assert len(analyzer.failure_statistics) == 0
        assert isinstance(analyzer.successful_strategies_benchmark, dict)
    
    def test_generate_failure_analysis_report_arena_layer1_failed(
        self, analyzer, sample_arena_result_failed_layer1
    ):
        """测试生成失败分析报告 - Arena第一层失败"""
        report = analyzer.generate_failure_analysis_report(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            failed_stage="斯巴达Arena评估",
            arena_result=sample_arena_result_failed_layer1,
            simulation_result=None
        )
        
        # 验证报告基本信息
        assert isinstance(report, FailureAnalysisReport)
        assert report.strategy_id == "strategy_001"
        assert report.strategy_name == "测试策略"
        assert report.failed_stage == "斯巴达Arena评估"
        assert report.failure_category == FailureCategory.ARENA_LAYER1_FAILED
        
        # 验证失败指标
        assert report.total_failed_metrics > 0
        assert len(report.failed_metrics_summary) > 0
        
        # 验证改进建议
        assert len(report.improvement_suggestions) > 0
        
        # 验证阶段失败详情
        assert len(report.stage_failure_details) > 0
    
    def test_generate_failure_analysis_report_simulation_failed(
        self, analyzer, sample_simulation_result_failed
    ):
        """测试生成失败分析报告 - 模拟盘失败"""
        report = analyzer.generate_failure_analysis_report(
            strategy_id="strategy_002",
            strategy_name="模拟盘失败策略",
            failed_stage="模拟盘验证",
            arena_result=None,
            simulation_result=sample_simulation_result_failed
        )
        
        assert report.failure_category == FailureCategory.SIMULATION_FAILED
        assert report.total_failed_metrics > 0
        assert len(report.improvement_suggestions) > 0
    
    def test_determine_failure_category_layer1(
        self, analyzer, sample_arena_result_failed_layer1
    ):
        """测试确定失败类别 - 第一层失败"""
        category = analyzer._determine_failure_category(
            "斯巴达Arena评估",
            sample_arena_result_failed_layer1,
            None
        )
        
        assert category == FailureCategory.ARENA_LAYER1_FAILED
    
    def test_determine_failure_category_simulation(
        self, analyzer, sample_simulation_result_failed
    ):
        """测试确定失败类别 - 模拟盘失败"""
        category = analyzer._determine_failure_category(
            "模拟盘验证",
            None,
            sample_simulation_result_failed
        )
        
        assert category == FailureCategory.SIMULATION_FAILED
    
    def test_determine_failure_category_risk_exceeded(self, analyzer):
        """测试确定失败类别 - 风险超标"""
        simulation_result = {
            "passed": False,
            "risk_metrics": {
                "max_drawdown": 0.25  # 超过20%阈值
            }
        }
        
        category = analyzer._determine_failure_category(
            "模拟盘验证",
            None,
            simulation_result
        )
        
        assert category == FailureCategory.RISK_LIMIT_EXCEEDED
    
    def test_analyze_stage_failures(
        self, analyzer, sample_arena_result_failed_layer1
    ):
        """测试分析阶段失败详情"""
        stage_failures = analyzer._analyze_stage_failures(
            "斯巴达Arena评估",
            sample_arena_result_failed_layer1,
            None
        )
        
        assert len(stage_failures) > 0
        assert isinstance(stage_failures[0], StageFailureDetail)
        assert stage_failures[0].stage_name == "斯巴达Arena评估"
        assert len(stage_failures[0].layer_failures) > 0
    
    def test_analyze_layer_failed_metrics(self, analyzer):
        """测试分析层级失败指标"""
        layer_data = {
            "metrics": {
                "sharpe_ratio": 1.0,
                "max_drawdown": 0.20
            },
            "thresholds": {
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.15
            },
            "failed_metrics": ["sharpe_ratio", "max_drawdown"]
        }
        
        failed_metrics = analyzer._analyze_layer_failed_metrics(1, layer_data)
        
        assert len(failed_metrics) == 2
        assert all(isinstance(m, FailedMetric) for m in failed_metrics)
        
        # 验证夏普比率指标
        sharpe_metric = next(m for m in failed_metrics if m.metric_name == "sharpe_ratio")
        assert sharpe_metric.actual_value == 1.0
        assert sharpe_metric.threshold_value == 1.5
        assert sharpe_metric.deviation_percentage > 0
    
    def test_determine_metric_severity(self, analyzer):
        """测试确定指标严重程度"""
        assert analyzer._determine_metric_severity(60) == "critical"
        assert analyzer._determine_metric_severity(40) == "high"
        assert analyzer._determine_metric_severity(20) == "medium"
        assert analyzer._determine_metric_severity(10) == "low"
    
    def test_extract_failed_metrics_from_arena(
        self, analyzer, sample_arena_result_failed_layer1
    ):
        """测试从Arena结果提取失败指标"""
        failed_metrics = analyzer._extract_failed_metrics(
            sample_arena_result_failed_layer1,
            None
        )
        
        assert len(failed_metrics) > 0
        assert all(isinstance(m, FailedMetric) for m in failed_metrics)
        
        # 验证包含预期的失败指标
        metric_names = [m.metric_name for m in failed_metrics]
        assert "sharpe_ratio" in metric_names
        assert "max_drawdown" in metric_names
    
    def test_extract_failed_metrics_from_simulation(
        self, analyzer, sample_simulation_result_failed
    ):
        """测试从模拟盘结果提取失败指标"""
        failed_metrics = analyzer._extract_failed_metrics(
            None,
            sample_simulation_result_failed
        )
        
        assert len(failed_metrics) > 0
        metric_names = [m.metric_name for m in failed_metrics]
        assert "monthly_return" in metric_names
        assert "sharpe_ratio" in metric_names
    
    def test_compare_with_successful_strategies(self, analyzer):
        """测试与达标策略对比"""
        failed_metrics = [
            FailedMetric(
                metric_name="sharpe_ratio",
                actual_value=1.0,
                threshold_value=1.5,
                deviation_percentage=33.3,
                severity="high"
            ),
            FailedMetric(
                metric_name="max_drawdown",
                actual_value=0.20,
                threshold_value=0.15,
                deviation_percentage=33.3,
                severity="high"
            )
        ]
        
        comparisons = analyzer._compare_with_successful_strategies(
            failed_metrics,
            FailureCategory.ARENA_LAYER1_FAILED
        )
        
        assert len(comparisons) > 0
        assert all(isinstance(c, ComparisonWithSuccessful) for c in comparisons)
        
        # 验证对比数据
        sharpe_comparison = next(
            c for c in comparisons if c.metric_name == "sharpe_ratio"
        )
        assert sharpe_comparison.failed_strategy_value == 1.0
        assert sharpe_comparison.successful_avg_value > 0
        assert sharpe_comparison.gap_percentage > 0
    
    def test_get_successful_strategies_benchmark(self, analyzer):
        """测试获取达标策略基准数据"""
        benchmark = analyzer._get_successful_strategies_benchmark(
            FailureCategory.ARENA_LAYER1_FAILED
        )
        
        assert isinstance(benchmark, dict)
        assert "sharpe_ratio" in benchmark
        assert "max_drawdown" in benchmark
        
        # 验证基准数据结构
        sharpe_bench = benchmark["sharpe_ratio"]
        assert "avg" in sharpe_bench
        assert "min" in sharpe_bench
        assert "max" in sharpe_bench
    
    def test_generate_improvement_suggestions(self, analyzer):
        """测试生成改进建议"""
        failed_metrics = [
            FailedMetric(
                metric_name="sharpe_ratio",
                actual_value=1.0,
                threshold_value=1.5,
                deviation_percentage=33.3,
                severity="high"
            )
        ]
        
        comparisons = [
            ComparisonWithSuccessful(
                metric_name="sharpe_ratio",
                failed_strategy_value=1.0,
                successful_avg_value=2.0,
                successful_min_value=1.5,
                successful_max_value=3.0,
                gap_percentage=50.0
            )
        ]
        
        suggestions = analyzer._generate_improvement_suggestions(
            FailureCategory.ARENA_LAYER1_FAILED,
            failed_metrics,
            comparisons
        )
        
        assert len(suggestions) > 0
        assert all(isinstance(s, ImprovementSuggestion) for s in suggestions)
        
        # 验证建议包含必要字段
        for suggestion in suggestions:
            assert suggestion.category
            assert suggestion.priority in ["critical", "high", "medium", "low"]
            assert suggestion.suggestion
            assert suggestion.expected_impact
            assert suggestion.implementation_difficulty in ["easy", "medium", "hard"]
    
    def test_get_category_specific_suggestions(self, analyzer):
        """测试获取类别特定建议"""
        suggestions = analyzer._get_category_specific_suggestions(
            FailureCategory.ARENA_LAYER1_FAILED
        )
        
        assert len(suggestions) > 0
        assert all(isinstance(s, ImprovementSuggestion) for s in suggestions)
        
        # 验证建议与类别相关
        categories = [s.category for s in suggestions]
        assert any("投研级指标" in cat or "回撤控制" in cat for cat in categories)
    
    def test_get_metric_specific_suggestions(self, analyzer):
        """测试获取指标特定建议"""
        failed_metric = FailedMetric(
            metric_name="sharpe_ratio",
            actual_value=1.0,
            threshold_value=1.5,
            deviation_percentage=33.3,
            severity="high"
        )
        
        suggestions = analyzer._get_metric_specific_suggestions(failed_metric)
        
        assert len(suggestions) > 0
        assert suggestions[0].category == "夏普比率优化"
        assert "夏普比率" in suggestions[0].suggestion
    
    def test_get_gap_specific_suggestion(self, analyzer):
        """测试获取差距特定建议"""
        comparison = ComparisonWithSuccessful(
            metric_name="sharpe_ratio",
            failed_strategy_value=1.0,
            successful_avg_value=2.0,
            successful_min_value=1.5,
            successful_max_value=3.0,
            gap_percentage=60.0  # 大于50%，应该是high优先级
        )
        
        suggestion = analyzer._get_gap_specific_suggestion(comparison)
        
        assert suggestion is not None
        assert isinstance(suggestion, ImprovementSuggestion)
        assert suggestion.priority == "high"
        assert "差距" in suggestion.suggestion
    
    def test_get_gap_specific_suggestion_small_gap(self, analyzer):
        """测试获取差距特定建议 - 小差距"""
        comparison = ComparisonWithSuccessful(
            metric_name="sharpe_ratio",
            failed_strategy_value=1.8,
            successful_avg_value=2.0,
            successful_min_value=1.5,
            successful_max_value=3.0,
            gap_percentage=10.0
        )
        
        suggestion = analyzer._get_gap_specific_suggestion(comparison)
        
        # 差距小于30%应该返回None
        assert suggestion is None
    
    def test_deduplicate_suggestions(self, analyzer):
        """测试去重建议"""
        suggestions = [
            ImprovementSuggestion(
                category="优化1",
                priority="high",
                suggestion="建议1",
                expected_impact="影响1",
                implementation_difficulty="medium"
            ),
            ImprovementSuggestion(
                category="优化1",
                priority="high",
                suggestion="建议1",  # 重复
                expected_impact="影响1",
                implementation_difficulty="medium"
            ),
            ImprovementSuggestion(
                category="优化2",
                priority="medium",
                suggestion="建议2",
                expected_impact="影响2",
                implementation_difficulty="easy"
            )
        ]
        
        unique = analyzer._deduplicate_suggestions(suggestions)
        
        assert len(unique) == 2
        assert unique[0].category == "优化1"
        assert unique[1].category == "优化2"
    
    def test_priority_order(self, analyzer):
        """测试优先级排序"""
        assert analyzer._priority_order("critical") < analyzer._priority_order("high")
        assert analyzer._priority_order("high") < analyzer._priority_order("medium")
        assert analyzer._priority_order("medium") < analyzer._priority_order("low")
    
    def test_generate_overall_failure_reason(self, analyzer):
        """测试生成总体失败原因"""
        stage_failures = [
            StageFailureDetail(
                stage_name="斯巴达Arena评估",
                failure_reason="第一层验证未通过",
                layer_failures=[
                    LayerFailureDetail(
                        layer_number=1,
                        layer_name="投研级指标验证",
                        layer_score=0.65,
                        required_score=0.80,
                        failed_metrics=[],
                        failure_reason="未达标"
                    )
                ],
                failed_at=datetime.now()
            )
        ]
        
        reason = analyzer._generate_overall_failure_reason(
            FailureCategory.ARENA_LAYER1_FAILED,
            stage_failures
        )
        
        assert isinstance(reason, str)
        assert len(reason) > 0
        assert "投研级指标" in reason or "第1层" in reason
    
    def test_update_failure_statistics(self, analyzer):
        """测试更新失败统计"""
        analyzer._update_failure_statistics(FailureCategory.ARENA_LAYER1_FAILED)
        analyzer._update_failure_statistics(FailureCategory.ARENA_LAYER1_FAILED)
        analyzer._update_failure_statistics(FailureCategory.SIMULATION_FAILED)
        
        stats = analyzer.get_failure_statistics()
        
        assert stats["arena_layer1_failed"] == 2
        assert stats["simulation_failed"] == 1
    
    def test_get_failure_statistics(self, analyzer):
        """测试获取失败统计"""
        analyzer._update_failure_statistics(FailureCategory.ARENA_LAYER1_FAILED)
        
        stats = analyzer.get_failure_statistics()
        
        assert isinstance(stats, dict)
        assert "arena_layer1_failed" in stats
        assert stats["arena_layer1_failed"] == 1
    
    def test_get_failure_rate_by_category(self, analyzer):
        """测试获取按类别的失败率"""
        analyzer._update_failure_statistics(FailureCategory.ARENA_LAYER1_FAILED)
        analyzer._update_failure_statistics(FailureCategory.ARENA_LAYER1_FAILED)
        analyzer._update_failure_statistics(FailureCategory.SIMULATION_FAILED)
        analyzer._update_failure_statistics(FailureCategory.RISK_LIMIT_EXCEEDED)
        
        rates = analyzer.get_failure_rate_by_category()
        
        assert isinstance(rates, dict)
        assert rates["arena_layer1_failed"] == 0.5  # 2/4
        assert rates["simulation_failed"] == 0.25   # 1/4
        assert rates["risk_limit_exceeded"] == 0.25  # 1/4
    
    def test_get_failure_rate_by_category_empty(self, analyzer):
        """测试获取失败率 - 空统计"""
        rates = analyzer.get_failure_rate_by_category()
        
        assert isinstance(rates, dict)
        assert len(rates) == 0
    
    def test_update_successful_strategies_benchmark(self, analyzer):
        """测试更新达标策略基准数据"""
        benchmark_data = {
            "sharpe_ratio": {"avg": 2.5, "min": 2.0, "max": 3.0},
            "max_drawdown": {"avg": 0.10, "min": 0.08, "max": 0.12}
        }
        
        analyzer.update_successful_strategies_benchmark(benchmark_data)
        
        assert analyzer.successful_strategies_benchmark == benchmark_data
    
    def test_export_failure_analysis_report(
        self, analyzer, sample_arena_result_failed_layer1
    ):
        """测试导出失败分析报告"""
        report = analyzer.generate_failure_analysis_report(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            failed_stage="斯巴达Arena评估",
            arena_result=sample_arena_result_failed_layer1,
            simulation_result=None
        )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            # 导出报告
            analyzer.export_failure_analysis_report(report, output_path)
            
            # 验证文件存在
            assert os.path.exists(output_path)
            
            # 读取并验证JSON内容
            with open(output_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            assert report_data["strategy_id"] == "strategy_001"
            assert report_data["strategy_name"] == "测试策略"
            assert report_data["failure_category"] == "arena_layer1_failed"
            assert "improvement_suggestions" in report_data
            assert len(report_data["improvement_suggestions"]) > 0
            
        finally:
            # 清理临时文件
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_export_failure_analysis_report_invalid_path(
        self, analyzer, sample_arena_result_failed_layer1
    ):
        """测试导出到无效路径"""
        report = analyzer.generate_failure_analysis_report(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            failed_stage="斯巴达Arena评估",
            arena_result=sample_arena_result_failed_layer1,
            simulation_result=None
        )
        
        # 使用一个在所有平台上都无效的路径（包含非法字符）
        invalid_path = "Z:\\nonexistent_drive_12345\\invalid\\path\\report.json"
        
        with pytest.raises((IOError, OSError)):
            analyzer.export_failure_analysis_report(report, invalid_path)


class TestFailureCategory:
    """测试FailureCategory枚举"""
    
    def test_failure_category_values(self):
        """测试失败类别枚举值"""
        assert FailureCategory.ARENA_LAYER1_FAILED.value == "arena_layer1_failed"
        assert FailureCategory.ARENA_LAYER2_FAILED.value == "arena_layer2_failed"
        assert FailureCategory.ARENA_LAYER3_FAILED.value == "arena_layer3_failed"
        assert FailureCategory.ARENA_LAYER4_FAILED.value == "arena_layer4_failed"
        assert FailureCategory.ARENA_OVERALL_LOW.value == "arena_overall_low"
        assert FailureCategory.SIMULATION_FAILED.value == "simulation_failed"
        assert FailureCategory.RISK_LIMIT_EXCEEDED.value == "risk_limit_exceeded"
        assert FailureCategory.PERFORMANCE_INSUFFICIENT.value == "performance_insufficient"


class TestDataModels:
    """测试数据模型"""
    
    def test_failed_metric_creation(self):
        """测试FailedMetric创建"""
        metric = FailedMetric(
            metric_name="sharpe_ratio",
            actual_value=1.0,
            threshold_value=1.5,
            deviation_percentage=33.3,
            severity="high"
        )
        
        assert metric.metric_name == "sharpe_ratio"
        assert metric.actual_value == 1.0
        assert metric.threshold_value == 1.5
        assert metric.deviation_percentage == 33.3
        assert metric.severity == "high"
    
    def test_layer_failure_detail_creation(self):
        """测试LayerFailureDetail创建"""
        layer_failure = LayerFailureDetail(
            layer_number=1,
            layer_name="投研级指标验证",
            layer_score=0.65,
            required_score=0.80,
            failed_metrics=[],
            failure_reason="未达标"
        )
        
        assert layer_failure.layer_number == 1
        assert layer_failure.layer_name == "投研级指标验证"
        assert layer_failure.layer_score == 0.65
        assert layer_failure.required_score == 0.80
    
    def test_improvement_suggestion_creation(self):
        """测试ImprovementSuggestion创建"""
        suggestion = ImprovementSuggestion(
            category="优化建议",
            priority="high",
            suggestion="建议内容",
            expected_impact="预期影响",
            implementation_difficulty="medium"
        )
        
        assert suggestion.category == "优化建议"
        assert suggestion.priority == "high"
        assert suggestion.suggestion == "建议内容"
        assert suggestion.expected_impact == "预期影响"
        assert suggestion.implementation_difficulty == "medium"
