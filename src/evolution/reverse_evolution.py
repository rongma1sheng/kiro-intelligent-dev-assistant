"""
反向进化 (Reverse Evolution)

白皮书依据: 第一章 1.5.4 进化态任务调度
- Arena淘汰样本尸检分析
- 失败因子/策略分析
- 提取失败模式

功能:
- 分析被淘汰的因子和策略
- 提取失败原因和模式
- 生成改进建议
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Tuple

from loguru import logger


class FailureType(Enum):
    """失败类型"""

    LOW_IC = "IC过低"
    HIGH_TURNOVER = "换手率过高"
    POOR_STABILITY = "稳定性差"
    OVERFITTING = "过拟合"
    REGIME_SENSITIVE = "市场敏感"
    HIGH_CORRELATION = "高相关性"
    POOR_SHARPE = "夏普比率低"
    HIGH_DRAWDOWN = "回撤过大"
    LOW_WIN_RATE = "胜率过低"
    UNKNOWN = "未知原因"


class EliminationStage(Enum):
    """淘汰阶段"""

    FACTOR_ARENA = "因子Arena"
    SPARTA_ARENA = "斯巴达Arena"
    SIMULATION = "模拟盘"
    LIVE = "实盘"


@dataclass
class EliminatedSample:
    """被淘汰样本

    Attributes:
        sample_id: 样本ID
        sample_type: 样本类型 (factor/strategy)
        name: 名称
        elimination_stage: 淘汰阶段
        elimination_date: 淘汰日期
        failure_types: 失败类型列表
        metrics: 性能指标
        expression: 表达式/配置
        parent_id: 父样本ID
    """

    sample_id: str
    sample_type: str
    name: str
    elimination_stage: EliminationStage
    elimination_date: date
    failure_types: List[FailureType] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    expression: str = ""
    parent_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sample_id": self.sample_id,
            "sample_type": self.sample_type,
            "name": self.name,
            "elimination_stage": self.elimination_stage.value,
            "elimination_date": self.elimination_date.isoformat(),
            "failure_types": [f.value for f in self.failure_types],
            "metrics": self.metrics,
            "expression": self.expression,
            "parent_id": self.parent_id,
        }


@dataclass
class FailurePattern:
    """失败模式

    Attributes:
        pattern_id: 模式ID
        failure_type: 失败类型
        occurrence_count: 出现次数
        affected_samples: 受影响样本列表
        common_traits: 共同特征
        suggestion: 改进建议
    """

    pattern_id: str
    failure_type: FailureType
    occurrence_count: int = 0
    affected_samples: List[str] = field(default_factory=list)
    common_traits: Dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "failure_type": self.failure_type.value,
            "occurrence_count": self.occurrence_count,
            "affected_samples": self.affected_samples,
            "common_traits": self.common_traits,
            "suggestion": self.suggestion,
        }


@dataclass
class AutopsyReport:
    """尸检报告

    Attributes:
        report_date: 报告日期
        total_samples: 分析样本总数
        failure_patterns: 失败模式列表
        stage_distribution: 各阶段淘汰分布
        type_distribution: 各类型失败分布
        top_failures: 最常见失败原因
        improvement_suggestions: 改进建议
        timestamp: 生成时间
    """

    report_date: date
    total_samples: int = 0
    failure_patterns: List[FailurePattern] = field(default_factory=list)
    stage_distribution: Dict[str, int] = field(default_factory=dict)
    type_distribution: Dict[str, int] = field(default_factory=dict)
    top_failures: List[Tuple[str, int]] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_date": self.report_date.isoformat(),
            "total_samples": self.total_samples,
            "failure_patterns": [p.to_dict() for p in self.failure_patterns],
            "stage_distribution": self.stage_distribution,
            "type_distribution": self.type_distribution,
            "top_failures": self.top_failures,
            "improvement_suggestions": self.improvement_suggestions,
            "timestamp": self.timestamp.isoformat(),
        }


class ReverseEvolution:
    """反向进化分析器

    白皮书依据: 第一章 1.5.4 进化态任务调度

    负责分析被淘汰的因子和策略，提取失败模式，生成改进建议。

    Attributes:
        ic_threshold: IC阈值
        sharpe_threshold: 夏普比率阈值
        drawdown_threshold: 回撤阈值

    Example:
        >>> reverse_evo = ReverseEvolution()
        >>> reverse_evo.add_eliminated_sample(sample)
        >>> report = reverse_evo.analyze()
        >>> print(f"发现{len(report.failure_patterns)}个失败模式")
    """

    # 失败判定阈值
    IC_THRESHOLD = 0.03
    SHARPE_THRESHOLD = 0.5
    DRAWDOWN_THRESHOLD = 0.2
    WIN_RATE_THRESHOLD = 0.4
    TURNOVER_THRESHOLD = 0.5

    def __init__(self, ic_threshold: float = 0.03, sharpe_threshold: float = 0.5, drawdown_threshold: float = 0.2):
        """初始化反向进化分析器

        Args:
            ic_threshold: IC阈值
            sharpe_threshold: 夏普比率阈值
            drawdown_threshold: 回撤阈值
        """
        self.ic_threshold = ic_threshold
        self.sharpe_threshold = sharpe_threshold
        self.drawdown_threshold = drawdown_threshold

        self._eliminated_samples: List[EliminatedSample] = []
        self._failure_patterns: Dict[FailureType, FailurePattern] = {}

        logger.info(f"反向进化分析器初始化: " f"IC阈值={ic_threshold}, " f"夏普阈值={sharpe_threshold}")

    def add_eliminated_sample(self, sample: EliminatedSample) -> None:
        """添加被淘汰样本

        Args:
            sample: 被淘汰样本
        """
        # 自动诊断失败原因
        if not sample.failure_types:
            sample.failure_types = self._diagnose_failure(sample)

        self._eliminated_samples.append(sample)
        logger.debug(f"添加淘汰样本: {sample.name}")

    def add_eliminated_samples(self, samples: List[EliminatedSample]) -> None:
        """批量添加被淘汰样本

        Args:
            samples: 样本列表
        """
        for sample in samples:
            self.add_eliminated_sample(sample)

    def _diagnose_failure(self, sample: EliminatedSample) -> List[FailureType]:
        """诊断失败原因

        Args:
            sample: 被淘汰样本

        Returns:
            失败类型列表
        """
        failures = []
        metrics = sample.metrics

        # 检查IC
        ic = metrics.get("ic", 0)
        if abs(ic) < self.ic_threshold:
            failures.append(FailureType.LOW_IC)

        # 检查夏普比率
        sharpe = metrics.get("sharpe", 0)
        if sharpe < self.sharpe_threshold:
            failures.append(FailureType.POOR_SHARPE)

        # 检查回撤
        drawdown = metrics.get("max_drawdown", 0)
        if drawdown > self.drawdown_threshold:
            failures.append(FailureType.HIGH_DRAWDOWN)

        # 检查胜率
        win_rate = metrics.get("win_rate", 0.5)
        if win_rate < self.WIN_RATE_THRESHOLD:
            failures.append(FailureType.LOW_WIN_RATE)

        # 检查换手率
        turnover = metrics.get("turnover", 0)
        if turnover > self.TURNOVER_THRESHOLD:
            failures.append(FailureType.HIGH_TURNOVER)

        # 检查稳定性
        ic_std = metrics.get("ic_std", 0)
        if ic_std > 0.1:
            failures.append(FailureType.POOR_STABILITY)

        # 检查过拟合
        train_sharpe = metrics.get("train_sharpe", 0)
        test_sharpe = metrics.get("test_sharpe", 0)
        if train_sharpe > 0 and test_sharpe > 0:
            if train_sharpe / test_sharpe > 2:
                failures.append(FailureType.OVERFITTING)

        if not failures:
            failures.append(FailureType.UNKNOWN)

        return failures

    def analyze(self) -> AutopsyReport:
        """执行尸检分析

        白皮书依据: 第一章 1.5.4 反向进化

        Returns:
            尸检报告
        """
        logger.info(f"开始尸检分析，样本数量: {len(self._eliminated_samples)}")

        if not self._eliminated_samples:
            return AutopsyReport(report_date=date.today(), improvement_suggestions=["无淘汰样本需要分析"])

        # 1. 统计各阶段淘汰分布
        stage_distribution = self._analyze_stage_distribution()

        # 2. 统计各类型失败分布
        type_distribution = self._analyze_type_distribution()

        # 3. 提取失败模式
        failure_patterns = self._extract_failure_patterns()

        # 4. 找出最常见失败原因
        top_failures = sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)[:5]

        # 5. 生成改进建议
        suggestions = self._generate_suggestions(failure_patterns)

        report = AutopsyReport(
            report_date=date.today(),
            total_samples=len(self._eliminated_samples),
            failure_patterns=failure_patterns,
            stage_distribution=stage_distribution,
            type_distribution=type_distribution,
            top_failures=top_failures,
            improvement_suggestions=suggestions,
        )

        logger.info(f"尸检分析完成: " f"样本={len(self._eliminated_samples)}, " f"模式={len(failure_patterns)}")

        return report

    def _analyze_stage_distribution(self) -> Dict[str, int]:
        """分析各阶段淘汰分布"""
        distribution: Dict[str, int] = defaultdict(int)

        for sample in self._eliminated_samples:
            distribution[sample.elimination_stage.value] += 1

        return dict(distribution)

    def _analyze_type_distribution(self) -> Dict[str, int]:
        """分析各类型失败分布"""
        distribution: Dict[str, int] = defaultdict(int)

        for sample in self._eliminated_samples:
            for failure_type in sample.failure_types:
                distribution[failure_type.value] += 1

        return dict(distribution)

    def _extract_failure_patterns(self) -> List[FailurePattern]:
        """提取失败模式"""
        patterns: Dict[FailureType, FailurePattern] = {}

        for sample in self._eliminated_samples:
            for failure_type in sample.failure_types:
                if failure_type not in patterns:
                    patterns[failure_type] = FailurePattern(
                        pattern_id=f"pattern_{failure_type.name.lower()}", failure_type=failure_type
                    )

                pattern = patterns[failure_type]
                pattern.occurrence_count += 1
                pattern.affected_samples.append(sample.sample_id)

        # 为每个模式生成建议
        for failure_type, pattern in patterns.items():
            pattern.suggestion = self._get_suggestion_for_failure(failure_type)

        return list(patterns.values())

    def _get_suggestion_for_failure(self, failure_type: FailureType) -> str:
        """获取失败类型对应的建议"""
        suggestions = {
            FailureType.LOW_IC: "考虑增加因子复杂度或使用非线性组合",
            FailureType.HIGH_TURNOVER: "增加换手率惩罚项或使用更长周期因子",
            FailureType.POOR_STABILITY: "使用滚动窗口验证或增加样本外测试",
            FailureType.OVERFITTING: "减少参数数量，增加正则化，使用交叉验证",
            FailureType.REGIME_SENSITIVE: "增加市场状态适应性或使用多状态模型",
            FailureType.HIGH_CORRELATION: "进行因子正交化或选择低相关因子",
            FailureType.POOR_SHARPE: "优化风险调整收益或改进止损策略",
            FailureType.HIGH_DRAWDOWN: "加强风控措施或降低仓位集中度",
            FailureType.LOW_WIN_RATE: "优化入场时机或调整持仓周期",
            FailureType.UNKNOWN: "需要进一步分析具体原因",
        }

        return suggestions.get(failure_type, "需要进一步分析")

    def _generate_suggestions(self, patterns: List[FailurePattern]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 按出现次数排序
        sorted_patterns = sorted(patterns, key=lambda x: x.occurrence_count, reverse=True)

        for pattern in sorted_patterns[:5]:
            suggestions.append(
                f"[{pattern.failure_type.value}] " f"(出现{pattern.occurrence_count}次): " f"{pattern.suggestion}"
            )

        if not suggestions:
            suggestions.append("暂无明显的失败模式，继续观察")

        return suggestions

    def get_samples_by_failure(self, failure_type: FailureType) -> List[EliminatedSample]:
        """获取特定失败类型的样本

        Args:
            failure_type: 失败类型

        Returns:
            样本列表
        """
        return [s for s in self._eliminated_samples if failure_type in s.failure_types]

    def get_samples_by_stage(self, stage: EliminationStage) -> List[EliminatedSample]:
        """获取特定阶段淘汰的样本

        Args:
            stage: 淘汰阶段

        Returns:
            样本列表
        """
        return [s for s in self._eliminated_samples if s.elimination_stage == stage]

    def clear_samples(self) -> None:
        """清除所有样本"""
        self._eliminated_samples.clear()
        self._failure_patterns.clear()
        logger.info("淘汰样本已清除")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "total_samples": len(self._eliminated_samples),
            "factor_samples": sum(1 for s in self._eliminated_samples if s.sample_type == "factor"),
            "strategy_samples": sum(1 for s in self._eliminated_samples if s.sample_type == "strategy"),
            "stage_distribution": self._analyze_stage_distribution(),
            "type_distribution": self._analyze_type_distribution(),
        }

    async def analyze_async(self) -> AutopsyReport:
        """异步执行尸检分析

        Returns:
            尸检报告
        """
        return await asyncio.to_thread(self.analyze)
