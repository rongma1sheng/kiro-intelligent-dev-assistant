"""认证失败分析器

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 失败分析

本模块实现认证失败的详细分析，帮助策略开发者理解策略的不足并进行改进。

核心功能：
- 生成详细的失败分析报告
- 分析失败的具体阶段和层级
- 分析未达标的具体指标和阈值
- 与达标策略对比分析
- 生成改进建议和优化方向
- 失败原因分类统计

Author: MIA System
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class FailureCategory(Enum):
    """失败类别"""

    ARENA_LAYER1_FAILED = "arena_layer1_failed"  # 第一层验证失败
    ARENA_LAYER2_FAILED = "arena_layer2_failed"  # 第二层验证失败
    ARENA_LAYER3_FAILED = "arena_layer3_failed"  # 第三层验证失败
    ARENA_LAYER4_FAILED = "arena_layer4_failed"  # 第四层验证失败
    ARENA_OVERALL_LOW = "arena_overall_low"  # Arena综合评分过低
    SIMULATION_FAILED = "simulation_failed"  # 模拟盘验证失败
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"  # 风险限制超标
    PERFORMANCE_INSUFFICIENT = "performance_insufficient"  # 性能不足


@dataclass
class FailedMetric:
    """未达标指标"""

    metric_name: str
    actual_value: float
    threshold_value: float
    deviation_percentage: float
    severity: str  # low, medium, high, critical


@dataclass
class LayerFailureDetail:
    """层级失败详情"""

    layer_number: int
    layer_name: str
    layer_score: float
    required_score: float
    failed_metrics: List[FailedMetric]
    failure_reason: str


@dataclass
class StageFailureDetail:
    """阶段失败详情"""

    stage_name: str
    failure_reason: str
    layer_failures: List[LayerFailureDetail]
    failed_at: datetime


@dataclass
class ComparisonWithSuccessful:
    """与达标策略对比"""

    metric_name: str
    failed_strategy_value: float
    successful_avg_value: float
    successful_min_value: float
    successful_max_value: float
    gap_percentage: float


@dataclass
class ImprovementSuggestion:
    """改进建议"""

    category: str
    priority: str  # high, medium, low
    suggestion: str
    expected_impact: str
    implementation_difficulty: str  # easy, medium, hard


@dataclass
class FailureAnalysisReport:
    """失败分析报告

    白皮书依据: 第四章 4.3.2 认证失败分析报告
    """

    # 基本信息
    report_id: str
    strategy_id: str
    strategy_name: str
    analysis_date: datetime

    # 失败概况
    failed_stage: str
    failure_category: FailureCategory
    overall_failure_reason: str

    # 详细失败信息
    stage_failure_details: List[StageFailureDetail]
    failed_metrics_summary: List[FailedMetric]

    # 对比分析
    comparison_with_successful: List[ComparisonWithSuccessful]

    # 改进建议
    improvement_suggestions: List[ImprovementSuggestion]

    # 统计信息
    total_failed_metrics: int
    critical_issues_count: int
    high_priority_suggestions_count: int

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


class CertificationFailureAnalyzer:
    """认证失败分析器

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 失败分析

    核心功能：
    1. 生成详细的失败分析报告
    2. 分析失败的具体阶段和层级
    3. 分析未达标的具体指标和阈值
    4. 与达标策略对比分析
    5. 生成改进建议和优化方向
    6. 失败原因分类统计

    Attributes:
        failure_statistics: 失败统计信息
        successful_strategies_benchmark: 达标策略基准数据
    """

    def __init__(self):
        """初始化失败分析器"""
        self.failure_statistics: Dict[str, int] = {}
        self.successful_strategies_benchmark: Dict[str, Dict[str, float]] = {}
        logger.info("初始化CertificationFailureAnalyzer")

    def generate_failure_analysis_report(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        failed_stage: str,
        arena_result: Optional[Dict[str, Any]] = None,
        simulation_result: Optional[Dict[str, Any]] = None,
        certification_trace: Optional[Any] = None,  # pylint: disable=unused-argument
    ) -> FailureAnalysisReport:
        """生成失败分析报告

        白皮书依据: 第四章 4.3.2 认证失败分析

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            failed_stage: 失败阶段
            arena_result: Arena验证结果
            simulation_result: 模拟盘验证结果
            certification_trace: 认证追踪记录

        Returns:
            FailureAnalysisReport: 失败分析报告
        """
        logger.info(f"生成失败分析报告 - " f"strategy_id={strategy_id}, " f"failed_stage={failed_stage}")

        # 确定失败类别
        failure_category = self._determine_failure_category(failed_stage, arena_result, simulation_result)

        # 分析阶段失败详情
        stage_failures = self._analyze_stage_failures(failed_stage, arena_result, simulation_result)

        # 提取未达标指标
        failed_metrics = self._extract_failed_metrics(arena_result, simulation_result)

        # 与达标策略对比
        comparisons = self._compare_with_successful_strategies(failed_metrics, failure_category)

        # 生成改进建议
        suggestions = self._generate_improvement_suggestions(failure_category, failed_metrics, comparisons)

        # 统计关键信息
        critical_issues = sum(1 for m in failed_metrics if m.severity == "critical")
        high_priority_suggestions = sum(1 for s in suggestions if s.priority == "high")

        # 生成报告
        report = FailureAnalysisReport(
            report_id=f"failure_analysis_{strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            analysis_date=datetime.now(),
            failed_stage=failed_stage,
            failure_category=failure_category,
            overall_failure_reason=self._generate_overall_failure_reason(failure_category, stage_failures),
            stage_failure_details=stage_failures,
            failed_metrics_summary=failed_metrics,
            comparison_with_successful=comparisons,
            improvement_suggestions=suggestions,
            total_failed_metrics=len(failed_metrics),
            critical_issues_count=critical_issues,
            high_priority_suggestions_count=high_priority_suggestions,
            metadata={"arena_result": arena_result, "simulation_result": simulation_result},
        )

        # 更新失败统计
        self._update_failure_statistics(failure_category)

        logger.info(
            f"失败分析报告生成完成 - "
            f"report_id={report.report_id}, "
            f"category={failure_category.value}, "
            f"failed_metrics={len(failed_metrics)}, "
            f"suggestions={len(suggestions)}"
        )

        return report

    def _determine_failure_category(
        self, failed_stage: str, arena_result: Optional[Dict[str, Any]], simulation_result: Optional[Dict[str, Any]]
    ) -> FailureCategory:
        """确定失败类别

        Args:
            failed_stage: 失败阶段
            arena_result: Arena验证结果
            simulation_result: 模拟盘验证结果

        Returns:
            FailureCategory: 失败类别
        """
        if "arena" in failed_stage.lower() or "sparta" in failed_stage.lower():
            if arena_result:
                # 检查哪一层失败
                layer_results = arena_result.get("layer_results", {})
                for layer_num in range(1, 5):
                    layer_key = f"layer_{layer_num}"
                    if layer_key in layer_results:
                        if not layer_results[layer_key].get("passed", True):
                            return FailureCategory(f"arena_layer{layer_num}_failed")

                # 如果所有层都通过但综合评分低
                if arena_result.get("overall_score", 0) < 0.75:
                    return FailureCategory.ARENA_OVERALL_LOW

        elif "simulation" in failed_stage.lower() or "模拟盘" in failed_stage:
            if simulation_result:
                # 检查是否风险超标
                risk_metrics = simulation_result.get("risk_metrics", {})
                if risk_metrics.get("max_drawdown", 0) > 0.20:
                    return FailureCategory.RISK_LIMIT_EXCEEDED

                return FailureCategory.SIMULATION_FAILED

        return FailureCategory.PERFORMANCE_INSUFFICIENT

    def _analyze_stage_failures(
        self, failed_stage: str, arena_result: Optional[Dict[str, Any]], simulation_result: Optional[Dict[str, Any]]
    ) -> List[StageFailureDetail]:
        """分析阶段失败详情

        Args:
            failed_stage: 失败阶段
            arena_result: Arena验证结果
            simulation_result: 模拟盘验证结果

        Returns:
            List[StageFailureDetail]: 阶段失败详情列表
        """
        stage_failures = []

        if arena_result:
            layer_results = arena_result.get("layer_results", {})

            for layer_num in range(1, 5):
                layer_key = f"layer_{layer_num}"
                if layer_key in layer_results:
                    layer_data = layer_results[layer_key]

                    if not layer_data.get("passed", True):
                        # 分析该层的失败指标
                        failed_metrics = self._analyze_layer_failed_metrics(layer_num, layer_data)

                        layer_failure = LayerFailureDetail(
                            layer_number=layer_num,
                            layer_name=layer_data.get("name", f"第{layer_num}层"),
                            layer_score=layer_data.get("score", 0.0),
                            required_score=layer_data.get("required_score", 0.75),
                            failed_metrics=failed_metrics,
                            failure_reason=layer_data.get("failure_reason", "未达标"),
                        )

                        stage_failure = StageFailureDetail(
                            stage_name=failed_stage,
                            failure_reason=f"第{layer_num}层验证未通过",
                            layer_failures=[layer_failure],
                            failed_at=datetime.now(),
                        )

                        stage_failures.append(stage_failure)

        if simulation_result and not simulation_result.get("passed", False):
            # 分析模拟盘失败
            failed_criteria = simulation_result.get("failed_criteria", [])

            stage_failure = StageFailureDetail(
                stage_name="模拟盘验证",
                failure_reason=f"未通过{len(failed_criteria)}项达标标准",
                layer_failures=[],
                failed_at=datetime.now(),
            )

            stage_failures.append(stage_failure)

        return stage_failures

    def _analyze_layer_failed_metrics(
        self, layer_number: int, layer_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> List[FailedMetric]:  # pylint: disable=unused-argument
        """分析层级失败指标

        Args:
            layer_number: 层级编号
            layer_data: 层级数据

        Returns:
            List[FailedMetric]: 失败指标列表
        """
        failed_metrics = []

        metrics = layer_data.get("metrics", {})
        thresholds = layer_data.get("thresholds", {})
        failed_metric_names = layer_data.get("failed_metrics", [])

        for metric_name in failed_metric_names:
            if metric_name in metrics and metric_name in thresholds:
                actual = metrics[metric_name]
                threshold = thresholds[metric_name]

                # 计算偏差百分比
                if threshold != 0:
                    deviation = abs((actual - threshold) / threshold) * 100
                else:
                    deviation = 100.0

                # 确定严重程度
                severity = self._determine_metric_severity(deviation)

                failed_metric = FailedMetric(
                    metric_name=metric_name,
                    actual_value=actual,
                    threshold_value=threshold,
                    deviation_percentage=deviation,
                    severity=severity,
                )

                failed_metrics.append(failed_metric)

        return failed_metrics

    def _determine_metric_severity(self, deviation_percentage: float) -> str:
        """确定指标严重程度

        Args:
            deviation_percentage: 偏差百分比

        Returns:
            str: 严重程度 (low, medium, high, critical)
        """
        if deviation_percentage >= 50:  # pylint: disable=no-else-return
            return "critical"
        elif deviation_percentage >= 30:
            return "high"
        elif deviation_percentage >= 15:
            return "medium"
        else:
            return "low"

    def _extract_failed_metrics(
        self, arena_result: Optional[Dict[str, Any]], simulation_result: Optional[Dict[str, Any]]
    ) -> List[FailedMetric]:
        """提取所有未达标指标

        Args:
            arena_result: Arena验证结果
            simulation_result: 模拟盘验证结果

        Returns:
            List[FailedMetric]: 未达标指标列表
        """
        all_failed_metrics = []

        # 从Arena结果提取
        if arena_result:
            layer_results = arena_result.get("layer_results", {})
            for layer_num in range(1, 5):
                layer_key = f"layer_{layer_num}"
                if layer_key in layer_results:
                    layer_metrics = self._analyze_layer_failed_metrics(layer_num, layer_results[layer_key])
                    all_failed_metrics.extend(layer_metrics)

        # 从模拟盘结果提取
        if simulation_result:
            failed_criteria = simulation_result.get("failed_criteria", [])
            overall_metrics = simulation_result.get("overall_metrics", {})

            # 模拟盘达标标准的阈值
            simulation_thresholds = {
                "monthly_return": 0.05,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.15,
                "win_rate": 0.55,
                "var_95": 0.05,
                "profit_factor": 1.3,
                "turnover_rate": 5.0,
                "calmar_ratio": 1.0,
                "market_correlation": 0.7,
                "information_ratio": 0.8,
            }

            for criterion in failed_criteria:
                if criterion in overall_metrics and criterion in simulation_thresholds:
                    actual = overall_metrics[criterion]
                    threshold = simulation_thresholds[criterion]

                    if threshold != 0:
                        deviation = abs((actual - threshold) / threshold) * 100
                    else:
                        deviation = 100.0

                    failed_metric = FailedMetric(
                        metric_name=criterion,
                        actual_value=actual,
                        threshold_value=threshold,
                        deviation_percentage=deviation,
                        severity=self._determine_metric_severity(deviation),
                    )

                    all_failed_metrics.append(failed_metric)

        return all_failed_metrics

    def _compare_with_successful_strategies(
        self, failed_metrics: List[FailedMetric], failure_category: FailureCategory
    ) -> List[ComparisonWithSuccessful]:
        """与达标策略对比分析

        Args:
            failed_metrics: 失败指标列表
            failure_category: 失败类别

        Returns:
            List[ComparisonWithSuccessful]: 对比分析列表
        """
        comparisons = []

        # 获取达标策略的基准数据
        benchmark = self._get_successful_strategies_benchmark(failure_category)

        for failed_metric in failed_metrics:
            metric_name = failed_metric.metric_name

            if metric_name in benchmark:
                bench_data = benchmark[metric_name]

                gap = (
                    abs((failed_metric.actual_value - bench_data["avg"]) / bench_data["avg"] * 100)
                    if bench_data["avg"] != 0
                    else 100.0
                )

                comparison = ComparisonWithSuccessful(
                    metric_name=metric_name,
                    failed_strategy_value=failed_metric.actual_value,
                    successful_avg_value=bench_data["avg"],
                    successful_min_value=bench_data["min"],
                    successful_max_value=bench_data["max"],
                    gap_percentage=gap,
                )

                comparisons.append(comparison)

        return comparisons

    def _get_successful_strategies_benchmark(
        self, failure_category: FailureCategory  # pylint: disable=unused-argument
    ) -> Dict[str, Dict[str, float]]:  # pylint: disable=unused-argument
        """获取达标策略基准数据

        Args:
            failure_category: 失败类别

        Returns:
            Dict[str, Dict[str, float]]: 基准数据
        """
        # 如果已有基准数据，直接返回
        if self.successful_strategies_benchmark:
            return self.successful_strategies_benchmark

        # 默认基准数据（基于白皮书标准）
        default_benchmark = {
            "sharpe_ratio": {"avg": 2.0, "min": 1.5, "max": 3.0},
            "max_drawdown": {"avg": 0.12, "min": 0.08, "max": 0.15},
            "win_rate": {"avg": 0.60, "min": 0.55, "max": 0.70},
            "monthly_return": {"avg": 0.08, "min": 0.05, "max": 0.15},
            "var_95": {"avg": 0.03, "min": 0.02, "max": 0.05},
            "profit_factor": {"avg": 1.5, "min": 1.3, "max": 2.0},
            "calmar_ratio": {"avg": 1.5, "min": 1.0, "max": 2.5},
            "information_ratio": {"avg": 1.2, "min": 0.8, "max": 2.0},
            "turnover_rate": {"avg": 3.0, "min": 1.0, "max": 5.0},
            "market_correlation": {"avg": 0.5, "min": 0.3, "max": 0.7},
        }

        return default_benchmark

    def _generate_improvement_suggestions(
        self,
        failure_category: FailureCategory,
        failed_metrics: List[FailedMetric],
        comparisons: List[ComparisonWithSuccessful],
    ) -> List[ImprovementSuggestion]:
        """生成改进建议

        Args:
            failure_category: 失败类别
            failed_metrics: 失败指标列表
            comparisons: 对比分析列表

        Returns:
            List[ImprovementSuggestion]: 改进建议列表
        """
        suggestions = []

        # 根据失败类别生成通用建议
        category_suggestions = self._get_category_specific_suggestions(failure_category)
        suggestions.extend(category_suggestions)

        # 根据具体失败指标生成针对性建议
        for failed_metric in failed_metrics:
            metric_suggestions = self._get_metric_specific_suggestions(failed_metric)
            suggestions.extend(metric_suggestions)

        # 根据与达标策略的差距生成建议
        for comparison in comparisons:
            if comparison.gap_percentage > 30:  # 差距超过30%
                gap_suggestion = self._get_gap_specific_suggestion(comparison)
                if gap_suggestion:
                    suggestions.append(gap_suggestion)

        # 去重并按优先级排序
        unique_suggestions = self._deduplicate_suggestions(suggestions)
        unique_suggestions.sort(key=lambda x: self._priority_order(x.priority))

        return unique_suggestions

    def _get_category_specific_suggestions(self, failure_category: FailureCategory) -> List[ImprovementSuggestion]:
        """获取类别特定的改进建议

        Args:
            failure_category: 失败类别

        Returns:
            List[ImprovementSuggestion]: 改进建议列表
        """
        suggestions_map = {
            FailureCategory.ARENA_LAYER1_FAILED: [
                ImprovementSuggestion(
                    category="投研级指标优化",
                    priority="high",
                    suggestion="优化策略的夏普比率和收益风险比，建议调整仓位管理和止损策略",
                    expected_impact="提升20-30%的风险调整收益",
                    implementation_difficulty="medium",
                ),
                ImprovementSuggestion(
                    category="回撤控制",
                    priority="high",
                    suggestion="加强回撤控制机制，建议引入动态止损和仓位调整",
                    expected_impact="降低10-15%的最大回撤",
                    implementation_difficulty="medium",
                ),
            ],
            FailureCategory.ARENA_LAYER2_FAILED: [
                ImprovementSuggestion(
                    category="时间稳定性",
                    priority="high",
                    suggestion="提升策略的时间稳定性，建议使用滚动窗口验证和参数自适应",
                    expected_impact="提升策略在不同时间段的表现一致性",
                    implementation_difficulty="hard",
                )
            ],
            FailureCategory.ARENA_LAYER3_FAILED: [
                ImprovementSuggestion(
                    category="防过拟合",
                    priority="high",
                    suggestion="减少过拟合风险，建议简化模型、增加样本外验证",
                    expected_impact="提升策略的泛化能力",
                    implementation_difficulty="medium",
                )
            ],
            FailureCategory.ARENA_LAYER4_FAILED: [
                ImprovementSuggestion(
                    category="压力测试",
                    priority="high",
                    suggestion="提升极端市场环境下的表现，建议增加对冲机制和风险预算",
                    expected_impact="提升策略在极端市场的生存能力",
                    implementation_difficulty="hard",
                )
            ],
            FailureCategory.SIMULATION_FAILED: [
                ImprovementSuggestion(
                    category="实盘适应性",
                    priority="high",
                    suggestion="优化策略的实盘表现，建议考虑交易成本、滑点和流动性",
                    expected_impact="提升实盘收益10-20%",
                    implementation_difficulty="medium",
                )
            ],
            FailureCategory.RISK_LIMIT_EXCEEDED: [
                ImprovementSuggestion(
                    category="风险控制",
                    priority="critical",
                    suggestion="立即加强风险控制，建议降低杠杆、增加止损、分散持仓",
                    expected_impact="将风险降低到可接受范围",
                    implementation_difficulty="easy",
                )
            ],
        }

        return suggestions_map.get(failure_category, [])

    def _get_metric_specific_suggestions(self, failed_metric: FailedMetric) -> List[ImprovementSuggestion]:
        """获取指标特定的改进建议

        Args:
            failed_metric: 失败指标

        Returns:
            List[ImprovementSuggestion]: 改进建议列表
        """
        metric_name = failed_metric.metric_name
        severity = failed_metric.severity

        # 根据指标名称和严重程度生成建议
        suggestions_map = {
            "sharpe_ratio": ImprovementSuggestion(
                category="夏普比率优化",
                priority="high" if severity in ["high", "critical"] else "medium",
                suggestion=f"当前夏普比率{failed_metric.actual_value:.2f}，需提升至{failed_metric.threshold_value:.2f}以上。建议优化收益风险比，可通过提高胜率或降低波动率实现",  # pylint: disable=line-too-long
                expected_impact="提升风险调整收益",
                implementation_difficulty="medium",
            ),
            "max_drawdown": ImprovementSuggestion(
                category="回撤控制",
                priority="high" if severity in ["high", "critical"] else "medium",
                suggestion=f"当前最大回撤{failed_metric.actual_value:.2%}，需控制在{failed_metric.threshold_value:.2%}以内。建议加强止损机制和仓位管理",  # pylint: disable=line-too-long
                expected_impact="降低回撤风险",
                implementation_difficulty="medium",
            ),
            "win_rate": ImprovementSuggestion(
                category="胜率提升",
                priority="medium",
                suggestion=f"当前胜率{failed_metric.actual_value:.2%}，需提升至{failed_metric.threshold_value:.2%}以上。建议优化入场时机和出场策略",  # pylint: disable=line-too-long
                expected_impact="提升交易成功率",
                implementation_difficulty="hard",
            ),
            "monthly_return": ImprovementSuggestion(
                category="收益提升",
                priority="high" if severity in ["high", "critical"] else "medium",
                suggestion=f"当前月收益{failed_metric.actual_value:.2%}，需提升至{failed_metric.threshold_value:.2%}以上。建议优化因子选择和仓位配置",  # pylint: disable=line-too-long
                expected_impact="提升绝对收益",
                implementation_difficulty="medium",
            ),
        }

        suggestion = suggestions_map.get(metric_name)
        return [suggestion] if suggestion else []

    def _get_gap_specific_suggestion(self, comparison: ComparisonWithSuccessful) -> Optional[ImprovementSuggestion]:
        """获取差距特定的改进建议

        Args:
            comparison: 对比分析

        Returns:
            Optional[ImprovementSuggestion]: 改进建议
        """
        if comparison.gap_percentage > 50:
            priority = "high"
            difficulty = "hard"
        elif comparison.gap_percentage > 30:
            priority = "medium"
            difficulty = "medium"
        else:
            return None

        return ImprovementSuggestion(
            category=f"{comparison.metric_name}差距缩小",
            priority=priority,
            suggestion=f"该指标与达标策略平均值差距{comparison.gap_percentage:.1f}%，需要重点优化。达标策略平均值为{comparison.successful_avg_value:.4f}",  # pylint: disable=line-too-long
            expected_impact="缩小与达标策略的差距",
            implementation_difficulty=difficulty,
        )

    def _deduplicate_suggestions(self, suggestions: List[ImprovementSuggestion]) -> List[ImprovementSuggestion]:
        """去重建议

        Args:
            suggestions: 建议列表

        Returns:
            List[ImprovementSuggestion]: 去重后的建议列表
        """
        seen = set()
        unique = []

        for suggestion in suggestions:
            key = (suggestion.category, suggestion.suggestion)
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)

        return unique

    def _priority_order(self, priority: str) -> int:
        """优先级排序

        Args:
            priority: 优先级

        Returns:
            int: 排序值
        """
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return order.get(priority, 999)

    def _generate_overall_failure_reason(
        self, failure_category: FailureCategory, stage_failures: List[StageFailureDetail]
    ) -> str:
        """生成总体失败原因

        Args:
            failure_category: 失败类别
            stage_failures: 阶段失败详情列表

        Returns:
            str: 总体失败原因
        """
        category_reasons = {
            FailureCategory.ARENA_LAYER1_FAILED: "投研级指标验证未通过，策略的收益风险特征不达标",
            FailureCategory.ARENA_LAYER2_FAILED: "时间稳定性验证未通过，策略在不同时间段表现不一致",
            FailureCategory.ARENA_LAYER3_FAILED: "防过拟合验证未通过，策略存在过拟合风险",
            FailureCategory.ARENA_LAYER4_FAILED: "压力测试未通过，策略在极端市场环境下表现不佳",
            FailureCategory.ARENA_OVERALL_LOW: "Arena综合评分过低，整体表现未达到认证标准",
            FailureCategory.SIMULATION_FAILED: "模拟盘验证未通过，实盘表现不符合预期",
            FailureCategory.RISK_LIMIT_EXCEEDED: "风险限制超标，策略风险过高",
            FailureCategory.PERFORMANCE_INSUFFICIENT: "整体性能不足，未达到认证要求",
        }

        base_reason = category_reasons.get(failure_category, "认证验证未通过")

        if stage_failures:
            details = []
            for failure in stage_failures:
                if failure.layer_failures:
                    for layer_failure in failure.layer_failures:
                        details.append(
                            f"第{layer_failure.layer_number}层评分{layer_failure.layer_score:.2f}"
                            f"（要求≥{layer_failure.required_score:.2f}）"
                        )

            if details:
                base_reason += "。具体：" + "；".join(details)

        return base_reason

    def _update_failure_statistics(self, failure_category: FailureCategory) -> None:
        """更新失败统计

        Args:
            failure_category: 失败类别
        """
        category_key = failure_category.value
        self.failure_statistics[category_key] = self.failure_statistics.get(category_key, 0) + 1

        logger.debug(f"更新失败统计 - {category_key}: {self.failure_statistics[category_key]}")

    def get_failure_statistics(self) -> Dict[str, int]:
        """获取失败统计

        Returns:
            Dict[str, int]: 失败统计信息
        """
        return self.failure_statistics.copy()

    def get_failure_rate_by_category(self) -> Dict[str, float]:
        """获取按类别的失败率

        Returns:
            Dict[str, float]: 各类别失败率
        """
        total = sum(self.failure_statistics.values())

        if total == 0:
            return {}

        return {category: count / total for category, count in self.failure_statistics.items()}

    def update_successful_strategies_benchmark(self, benchmark_data: Dict[str, Dict[str, float]]) -> None:
        """更新达标策略基准数据

        Args:
            benchmark_data: 基准数据
        """
        self.successful_strategies_benchmark = benchmark_data
        logger.info(f"更新达标策略基准数据，包含{len(benchmark_data)}个指标")

    def export_failure_analysis_report(self, report: FailureAnalysisReport, output_path: str) -> None:
        """导出失败分析报告

        Args:
            report: 失败分析报告
            output_path: 输出文件路径

        Raises:
            IOError: 当文件写入失败时
        """
        import json  # pylint: disable=import-outside-toplevel

        # 转换为可序列化的字典
        report_dict = {
            "report_id": report.report_id,
            "strategy_id": report.strategy_id,
            "strategy_name": report.strategy_name,
            "analysis_date": report.analysis_date.isoformat(),
            "failed_stage": report.failed_stage,
            "failure_category": report.failure_category.value,
            "overall_failure_reason": report.overall_failure_reason,
            "stage_failure_details": [
                {
                    "stage_name": sf.stage_name,
                    "failure_reason": sf.failure_reason,
                    "failed_at": sf.failed_at.isoformat(),
                    "layer_failures": [
                        {
                            "layer_number": lf.layer_number,
                            "layer_name": lf.layer_name,
                            "layer_score": lf.layer_score,
                            "required_score": lf.required_score,
                            "failure_reason": lf.failure_reason,
                            "failed_metrics": [
                                {
                                    "metric_name": fm.metric_name,
                                    "actual_value": fm.actual_value,
                                    "threshold_value": fm.threshold_value,
                                    "deviation_percentage": fm.deviation_percentage,
                                    "severity": fm.severity,
                                }
                                for fm in lf.failed_metrics
                            ],
                        }
                        for lf in sf.layer_failures
                    ],
                }
                for sf in report.stage_failure_details
            ],
            "failed_metrics_summary": [
                {
                    "metric_name": fm.metric_name,
                    "actual_value": fm.actual_value,
                    "threshold_value": fm.threshold_value,
                    "deviation_percentage": fm.deviation_percentage,
                    "severity": fm.severity,
                }
                for fm in report.failed_metrics_summary
            ],
            "comparison_with_successful": [
                {
                    "metric_name": c.metric_name,
                    "failed_strategy_value": c.failed_strategy_value,
                    "successful_avg_value": c.successful_avg_value,
                    "successful_min_value": c.successful_min_value,
                    "successful_max_value": c.successful_max_value,
                    "gap_percentage": c.gap_percentage,
                }
                for c in report.comparison_with_successful
            ],
            "improvement_suggestions": [
                {
                    "category": s.category,
                    "priority": s.priority,
                    "suggestion": s.suggestion,
                    "expected_impact": s.expected_impact,
                    "implementation_difficulty": s.implementation_difficulty,
                }
                for s in report.improvement_suggestions
            ],
            "total_failed_metrics": report.total_failed_metrics,
            "critical_issues_count": report.critical_issues_count,
            "high_priority_suggestions_count": report.high_priority_suggestions_count,
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"失败分析报告已导出: {output_path}")

        except Exception as e:
            logger.error(f"导出失败分析报告失败: {e}")
            raise IOError(f"无法写入文件: {output_path}") from e
