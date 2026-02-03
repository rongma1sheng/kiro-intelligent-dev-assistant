"""认证流程可追溯性管理器

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 流程可追溯性

本模块实现认证流程的完整可追溯性，记录每个阶段的执行细节、
决策依据和验证结果，支持审计和合规检查。

核心功能：
- 阶段执行跟踪（时间、输入、输出）
- 验证层级详细记录
- 决策点输入输出记录
- 查询接口（按策略、日期、等级）
- 审计报告导出

Author: MIA System
Version: 1.0.0
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.z2h_data_models import CertificationLevel


class StageType(Enum):
    """认证阶段类型"""

    FACTOR_ARENA = "factor_arena"
    STRATEGY_GENERATION = "strategy_generation"
    SPARTA_ARENA = "sparta_arena"
    SIMULATION = "simulation"
    Z2H_CERTIFICATION = "z2h_certification"
    STRATEGY_LIBRARY = "strategy_library"


class DecisionType(Enum):
    """决策类型"""

    ELIGIBILITY_CHECK = "eligibility_check"
    LEVEL_DETERMINATION = "level_determination"
    CAPITAL_ALLOCATION = "capital_allocation"
    CERTIFICATION_GRANT = "certification_grant"
    CERTIFICATION_REVOKE = "certification_revoke"
    CERTIFICATION_DOWNGRADE = "certification_downgrade"


@dataclass
class StageExecutionRecord:
    """阶段执行记录

    记录单个认证阶段的完整执行信息
    """

    stage_type: StageType
    stage_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str = "running"  # running, completed, failed
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, output_data: Dict[str, Any]) -> None:
        """标记阶段完成

        Args:
            output_data: 输出数据
        """
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = "completed"
        self.output_data = output_data

    def fail(self, error_message: str) -> None:
        """标记阶段失败

        Args:
            error_message: 错误信息
        """
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = "failed"
        self.error_message = error_message


@dataclass
class ValidationLayerRecord:
    """验证层级记录

    记录Arena四层验证的详细信息
    """

    layer_number: int
    layer_name: str
    score: float
    passed: bool
    metrics: Dict[str, float]
    thresholds: Dict[str, float]
    failed_metrics: List[str]
    execution_time_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DecisionRecord:
    """决策记录

    记录关键决策点的输入、输出和依据
    """

    decision_type: DecisionType
    decision_name: str
    timestamp: datetime
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    decision_logic: str
    decision_result: Any
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CertificationTrace:
    """认证追踪记录

    包含单次认证流程的完整追踪信息
    """

    trace_id: str
    strategy_id: str
    strategy_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    final_status: str = "in_progress"  # in_progress, completed, failed
    certification_level: Optional[CertificationLevel] = None

    # 阶段执行记录
    stage_records: List[StageExecutionRecord] = field(default_factory=list)

    # 验证层级记录
    validation_layer_records: List[ValidationLayerRecord] = field(default_factory=list)

    # 决策记录
    decision_records: List[DecisionRecord] = field(default_factory=list)

    # 失败信息
    failed_stage: Optional[str] = None
    failure_reason: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, certification_level: Optional[CertificationLevel]) -> None:
        """标记认证完成

        Args:
            certification_level: 认证等级
        """
        self.end_time = datetime.now()
        self.total_duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.final_status = "completed"
        self.certification_level = certification_level

    def fail(self, failed_stage: str, failure_reason: str) -> None:
        """标记认证失败

        Args:
            failed_stage: 失败阶段
            failure_reason: 失败原因
        """
        self.end_time = datetime.now()
        self.total_duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.final_status = "failed"
        self.failed_stage = failed_stage
        self.failure_reason = failure_reason


class CertificationTraceabilityManager:
    """认证流程可追溯性管理器

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 流程可追溯性

    核心功能：
    1. 阶段执行跟踪：记录每个阶段的开始/结束时间、输入/输出
    2. 验证层级详细记录：记录Arena四层验证的详细评分和指标
    3. 决策点记录：记录认证等级评定、资金配置等关键决策
    4. 查询接口：支持按策略名称、日期、等级查询
    5. 审计报告导出：生成完整的审计报告

    Attributes:
        traces: 认证追踪记录字典，key为trace_id
    """

    def __init__(self):
        """初始化可追溯性管理器"""
        self.traces: Dict[str, CertificationTrace] = {}
        self._trace_counter: int = 0
        logger.info("初始化CertificationTraceabilityManager")

    def start_certification_trace(
        self, strategy_id: str, strategy_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """开始认证追踪

        白皮书依据: 第四章 4.3.2 认证流程可追溯性

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            metadata: 元数据

        Returns:
            str: 追踪ID
        """
        now = datetime.now()
        self._trace_counter += 1
        trace_id = f"trace_{strategy_id}_{now.strftime('%Y%m%d_%H%M%S')}_{self._trace_counter}"

        trace = CertificationTrace(
            trace_id=trace_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            start_time=now,
            metadata=metadata or {},
        )

        self.traces[trace_id] = trace

        logger.info(
            f"开始认证追踪 - " f"trace_id={trace_id}, " f"strategy_id={strategy_id}, " f"strategy_name={strategy_name}"
        )

        return trace_id

    def record_stage_start(  # pylint: disable=too-many-positional-arguments
        self,
        trace_id: str,
        stage_type: StageType,
        stage_name: str,
        input_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录阶段开始

        Args:
            trace_id: 追踪ID
            stage_type: 阶段类型
            stage_name: 阶段名称
            input_data: 输入数据
            metadata: 元数据

        Raises:
            ValueError: 当trace_id不存在时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        stage_record = StageExecutionRecord(
            stage_type=stage_type,
            stage_name=stage_name,
            start_time=datetime.now(),
            input_data=input_data,
            metadata=metadata or {},
        )

        self.traces[trace_id].stage_records.append(stage_record)

        logger.info(f"记录阶段开始 - " f"trace_id={trace_id}, " f"stage={stage_name}")

    def record_stage_complete(self, trace_id: str, stage_name: str, output_data: Dict[str, Any]) -> None:
        """记录阶段完成

        Args:
            trace_id: 追踪ID
            stage_name: 阶段名称
            output_data: 输出数据

        Raises:
            ValueError: 当trace_id不存在或找不到对应阶段时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        # 找到最后一个匹配的阶段记录
        stage_record = None
        for record in reversed(self.traces[trace_id].stage_records):
            if record.stage_name == stage_name and record.status == "running":
                stage_record = record
                break

        if stage_record is None:
            raise ValueError(f"找不到运行中的阶段: {stage_name}")

        stage_record.complete(output_data)

        logger.info(
            f"记录阶段完成 - "
            f"trace_id={trace_id}, "
            f"stage={stage_name}, "
            f"duration={stage_record.duration_seconds:.2f}s"
        )

    def record_stage_failure(self, trace_id: str, stage_name: str, error_message: str) -> None:
        """记录阶段失败

        Args:
            trace_id: 追踪ID
            stage_name: 阶段名称
            error_message: 错误信息

        Raises:
            ValueError: 当trace_id不存在或找不到对应阶段时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        # 找到最后一个匹配的阶段记录
        stage_record = None
        for record in reversed(self.traces[trace_id].stage_records):
            if record.stage_name == stage_name and record.status == "running":
                stage_record = record
                break

        if stage_record is None:
            raise ValueError(f"找不到运行中的阶段: {stage_name}")

        stage_record.fail(error_message)

        logger.warning(f"记录阶段失败 - " f"trace_id={trace_id}, " f"stage={stage_name}, " f"error={error_message}")

    def record_validation_layer(  # pylint: disable=too-many-positional-arguments
        self,
        trace_id: str,
        layer_number: int,
        layer_name: str,
        score: float,
        passed: bool,
        metrics: Dict[str, float],
        thresholds: Dict[str, float],
        failed_metrics: List[str],
        execution_time_seconds: float,
    ) -> None:
        """记录验证层级结果

        Args:
            trace_id: 追踪ID
            layer_number: 层级编号（1-4）
            layer_name: 层级名称
            score: 层级评分
            passed: 是否通过
            metrics: 指标值
            thresholds: 阈值
            failed_metrics: 未通过的指标列表
            execution_time_seconds: 执行时间（秒）

        Raises:
            ValueError: 当trace_id不存在或layer_number无效时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        if not 1 <= layer_number <= 4:
            raise ValueError(f"层级编号必须在1-4之间: {layer_number}")

        layer_record = ValidationLayerRecord(
            layer_number=layer_number,
            layer_name=layer_name,
            score=score,
            passed=passed,
            metrics=metrics,
            thresholds=thresholds,
            failed_metrics=failed_metrics,
            execution_time_seconds=execution_time_seconds,
        )

        self.traces[trace_id].validation_layer_records.append(layer_record)

        logger.info(
            f"记录验证层级 - "
            f"trace_id={trace_id}, "
            f"layer={layer_number}, "
            f"score={score:.4f}, "
            f"passed={passed}"
        )

    def record_decision(  # pylint: disable=too-many-positional-arguments
        self,
        trace_id: str,
        decision_type: DecisionType,
        decision_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        decision_logic: str,
        decision_result: Any,
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录决策点

        Args:
            trace_id: 追踪ID
            decision_type: 决策类型
            decision_name: 决策名称
            input_data: 输入数据
            output_data: 输出数据
            decision_logic: 决策逻辑描述
            decision_result: 决策结果
            confidence_score: 置信度评分
            metadata: 元数据

        Raises:
            ValueError: 当trace_id不存在时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        decision_record = DecisionRecord(
            decision_type=decision_type,
            decision_name=decision_name,
            timestamp=datetime.now(),
            input_data=input_data,
            output_data=output_data,
            decision_logic=decision_logic,
            decision_result=decision_result,
            confidence_score=confidence_score,
            metadata=metadata or {},
        )

        self.traces[trace_id].decision_records.append(decision_record)

        logger.info(f"记录决策点 - " f"trace_id={trace_id}, " f"decision={decision_name}, " f"result={decision_result}")

    def complete_certification_trace(self, trace_id: str, certification_level: Optional[CertificationLevel]) -> None:
        """完成认证追踪

        Args:
            trace_id: 追踪ID
            certification_level: 认证等级

        Raises:
            ValueError: 当trace_id不存在时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        self.traces[trace_id].complete(certification_level)

        logger.info(
            f"完成认证追踪 - "
            f"trace_id={trace_id}, "
            f"level={certification_level}, "
            f"duration={self.traces[trace_id].total_duration_seconds:.2f}s"
        )

    def fail_certification_trace(self, trace_id: str, failed_stage: str, failure_reason: str) -> None:
        """标记认证追踪失败

        Args:
            trace_id: 追踪ID
            failed_stage: 失败阶段
            failure_reason: 失败原因

        Raises:
            ValueError: 当trace_id不存在时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        self.traces[trace_id].fail(failed_stage, failure_reason)

        logger.warning(
            f"认证追踪失败 - " f"trace_id={trace_id}, " f"failed_stage={failed_stage}, " f"reason={failure_reason}"
        )

    def get_trace(self, trace_id: str) -> Optional[CertificationTrace]:
        """获取认证追踪记录

        Args:
            trace_id: 追踪ID

        Returns:
            Optional[CertificationTrace]: 追踪记录，不存在时返回None
        """
        return self.traces.get(trace_id)

    def query_traces_by_strategy(self, strategy_id: str) -> List[CertificationTrace]:
        """按策略ID查询追踪记录

        Args:
            strategy_id: 策略ID

        Returns:
            List[CertificationTrace]: 追踪记录列表
        """
        results = [trace for trace in self.traces.values() if trace.strategy_id == strategy_id]

        # 按开始时间降序排序
        results.sort(key=lambda x: x.start_time, reverse=True)

        logger.info(f"按策略查询追踪记录 - " f"strategy_id={strategy_id}, " f"count={len(results)}")

        return results

    def query_traces_by_date_range(self, start_date: datetime, end_date: datetime) -> List[CertificationTrace]:
        """按日期范围查询追踪记录

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[CertificationTrace]: 追踪记录列表

        Raises:
            ValueError: 当日期范围无效时
        """
        if start_date > end_date:
            raise ValueError(f"开始日期不能晚于结束日期: {start_date} > {end_date}")

        results = [trace for trace in self.traces.values() if start_date <= trace.start_time <= end_date]

        # 按开始时间降序排序
        results.sort(key=lambda x: x.start_time, reverse=True)

        logger.info(f"按日期范围查询追踪记录 - " f"start={start_date}, " f"end={end_date}, " f"count={len(results)}")

        return results

    def query_traces_by_level(self, certification_level: CertificationLevel) -> List[CertificationTrace]:
        """按认证等级查询追踪记录

        Args:
            certification_level: 认证等级

        Returns:
            List[CertificationTrace]: 追踪记录列表
        """
        results = [trace for trace in self.traces.values() if trace.certification_level == certification_level]

        # 按开始时间降序排序
        results.sort(key=lambda x: x.start_time, reverse=True)

        logger.info(f"按认证等级查询追踪记录 - " f"level={certification_level}, " f"count={len(results)}")

        return results

    def query_traces_by_status(self, status: str) -> List[CertificationTrace]:
        """按状态查询追踪记录

        Args:
            status: 状态（in_progress, completed, failed）

        Returns:
            List[CertificationTrace]: 追踪记录列表

        Raises:
            ValueError: 当状态无效时
        """
        valid_statuses = ["in_progress", "completed", "failed"]
        if status not in valid_statuses:
            raise ValueError(f"无效的状态: {status}，必须是 {valid_statuses} 之一")

        results = [trace for trace in self.traces.values() if trace.final_status == status]

        # 按开始时间降序排序
        results.sort(key=lambda x: x.start_time, reverse=True)

        logger.info(f"按状态查询追踪记录 - " f"status={status}, " f"count={len(results)}")

        return results

    def generate_audit_report(self, trace_id: str, include_raw_data: bool = False) -> Dict[str, Any]:
        """生成审计报告

        白皮书依据: 第四章 4.3.2 认证流程可追溯性 - 审计报告

        Args:
            trace_id: 追踪ID
            include_raw_data: 是否包含原始数据

        Returns:
            Dict[str, Any]: 审计报告

        Raises:
            ValueError: 当trace_id不存在时
        """
        if trace_id not in self.traces:
            raise ValueError(f"追踪ID不存在: {trace_id}")

        trace = self.traces[trace_id]

        # 基本信息
        report = {
            "report_id": f"audit_{trace_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "trace_id": trace_id,
            "strategy_id": trace.strategy_id,
            "strategy_name": trace.strategy_name,
            "start_time": trace.start_time.isoformat(),
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "total_duration_seconds": trace.total_duration_seconds,
            "final_status": trace.final_status,
            "certification_level": trace.certification_level.value if trace.certification_level else None,
            "failed_stage": trace.failed_stage,
            "failure_reason": trace.failure_reason,
        }

        # 阶段执行摘要
        report["stage_summary"] = {
            "total_stages": len(trace.stage_records),
            "completed_stages": sum(1 for s in trace.stage_records if s.status == "completed"),
            "failed_stages": sum(1 for s in trace.stage_records if s.status == "failed"),
            "total_execution_time": sum(
                s.duration_seconds for s in trace.stage_records if s.duration_seconds is not None
            ),
        }

        # 阶段详情
        report["stages"] = []
        for stage in trace.stage_records:
            stage_info = {
                "stage_type": stage.stage_type.value,
                "stage_name": stage.stage_name,
                "start_time": stage.start_time.isoformat(),
                "end_time": stage.end_time.isoformat() if stage.end_time else None,
                "duration_seconds": stage.duration_seconds,
                "status": stage.status,
                "error_message": stage.error_message,
            }

            if include_raw_data:
                stage_info["input_data"] = stage.input_data
                stage_info["output_data"] = stage.output_data
                stage_info["metadata"] = stage.metadata

            report["stages"].append(stage_info)

        # 验证层级摘要
        report["validation_summary"] = {
            "total_layers": len(trace.validation_layer_records),
            "passed_layers": sum(1 for l in trace.validation_layer_records if l.passed),
            "failed_layers": sum(1 for l in trace.validation_layer_records if not l.passed),
            "average_score": (
                sum(l.score for l in trace.validation_layer_records) / len(trace.validation_layer_records)
                if trace.validation_layer_records
                else 0.0
            ),
        }

        # 验证层级详情
        report["validation_layers"] = []
        for layer in trace.validation_layer_records:
            layer_info = {
                "layer_number": layer.layer_number,
                "layer_name": layer.layer_name,
                "score": layer.score,
                "passed": layer.passed,
                "failed_metrics": layer.failed_metrics,
                "execution_time_seconds": layer.execution_time_seconds,
                "timestamp": layer.timestamp.isoformat(),
            }

            if include_raw_data:
                layer_info["metrics"] = layer.metrics
                layer_info["thresholds"] = layer.thresholds

            report["validation_layers"].append(layer_info)

        # 决策摘要
        report["decision_summary"] = {"total_decisions": len(trace.decision_records), "decision_types": {}}

        for decision in trace.decision_records:
            decision_type = decision.decision_type.value
            report["decision_summary"]["decision_types"][decision_type] = (
                report["decision_summary"]["decision_types"].get(decision_type, 0) + 1
            )

        # 决策详情
        report["decisions"] = []
        for decision in trace.decision_records:
            decision_info = {
                "decision_type": decision.decision_type.value,
                "decision_name": decision.decision_name,
                "timestamp": decision.timestamp.isoformat(),
                "decision_logic": decision.decision_logic,
                "decision_result": str(decision.decision_result),
                "confidence_score": decision.confidence_score,
            }

            if include_raw_data:
                decision_info["input_data"] = decision.input_data
                decision_info["output_data"] = decision.output_data
                decision_info["metadata"] = decision.metadata

            report["decisions"].append(decision_info)

        # 元数据
        if include_raw_data:
            report["trace_metadata"] = trace.metadata

        logger.info(
            f"生成审计报告 - "
            f"trace_id={trace_id}, "
            f"stages={report['stage_summary']['total_stages']}, "
            f"layers={report['validation_summary']['total_layers']}, "
            f"decisions={report['decision_summary']['total_decisions']}"
        )

        return report

    def export_audit_report_json(self, trace_id: str, output_path: str, include_raw_data: bool = False) -> None:
        """导出审计报告为JSON文件

        Args:
            trace_id: 追踪ID
            output_path: 输出文件路径
            include_raw_data: 是否包含原始数据

        Raises:
            ValueError: 当trace_id不存在时
            IOError: 当文件写入失败时
        """
        report = self.generate_audit_report(trace_id, include_raw_data)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"审计报告已导出: {output_path}")

        except Exception as e:
            logger.error(f"导出审计报告失败: {e}")
            raise IOError(f"无法写入文件: {output_path}") from e

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_traces = len(self.traces)

        if total_traces == 0:
            return {
                "total_traces": 0,
                "status_distribution": {},
                "level_distribution": {},
                "average_duration_seconds": 0.0,
                "success_rate": 0.0,
            }

        # 状态分布
        status_distribution = {}
        for trace in self.traces.values():
            status = trace.final_status
            status_distribution[status] = status_distribution.get(status, 0) + 1

        # 等级分布
        level_distribution = {}
        for trace in self.traces.values():
            if trace.certification_level:
                level = trace.certification_level.value
                level_distribution[level] = level_distribution.get(level, 0) + 1

        # 平均时长
        completed_traces = [trace for trace in self.traces.values() if trace.total_duration_seconds is not None]
        average_duration = (
            sum(t.total_duration_seconds for t in completed_traces) / len(completed_traces) if completed_traces else 0.0
        )

        # 成功率
        completed_count = status_distribution.get("completed", 0)
        success_rate = completed_count / total_traces if total_traces > 0 else 0.0

        return {
            "total_traces": total_traces,
            "status_distribution": status_distribution,
            "level_distribution": level_distribution,
            "average_duration_seconds": average_duration,
            "success_rate": success_rate,
        }
