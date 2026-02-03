"""认证流程可追溯性管理器单元测试

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 流程可追溯性

测试覆盖：
- 认证追踪的创建和管理
- 阶段执行记录
- 验证层级记录
- 决策记录
- 查询接口
- 审计报告生成
- 统计信息

Author: MIA System
Version: 1.0.0
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
import json
import tempfile
import os

from src.evolution.certification_traceability import (
    CertificationTraceabilityManager,
    StageType,
    DecisionType,
    StageExecutionRecord,
    ValidationLayerRecord,
    DecisionRecord,
    CertificationTrace
)
from src.evolution.z2h_data_models import CertificationLevel


class TestCertificationTraceabilityManager:
    """测试CertificationTraceabilityManager类"""
    
    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return CertificationTraceabilityManager()
    
    @pytest.fixture
    def sample_strategy_id(self):
        """示例策略ID"""
        return "strategy_001"
    
    @pytest.fixture
    def sample_strategy_name(self):
        """示例策略名称"""
        return "动量策略V1"
    
    def test_initialization(self, manager):
        """测试初始化"""
        assert isinstance(manager.traces, dict)
        assert len(manager.traces) == 0
    
    def test_start_certification_trace(self, manager, sample_strategy_id, sample_strategy_name):
        """测试开始认证追踪"""
        metadata = {"market_type": "A_STOCK", "version": "1.0"}
        
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name,
            metadata=metadata
        )
        
        # 验证trace_id格式
        assert trace_id.startswith(f"trace_{sample_strategy_id}_")
        
        # 验证追踪记录已创建
        assert trace_id in manager.traces
        trace = manager.traces[trace_id]
        
        assert trace.strategy_id == sample_strategy_id
        assert trace.strategy_name == sample_strategy_name
        assert trace.final_status == "in_progress"
        assert trace.metadata == metadata
        assert len(trace.stage_records) == 0
        assert len(trace.validation_layer_records) == 0
        assert len(trace.decision_records) == 0
    
    def test_record_stage_start(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录阶段开始"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        input_data = {"factor_count": 5, "market_type": "A_STOCK"}
        
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.FACTOR_ARENA,
            stage_name="因子Arena测试",
            input_data=input_data
        )
        
        trace = manager.traces[trace_id]
        assert len(trace.stage_records) == 1
        
        stage = trace.stage_records[0]
        assert stage.stage_type == StageType.FACTOR_ARENA
        assert stage.stage_name == "因子Arena测试"
        assert stage.status == "running"
        assert stage.input_data == input_data
        assert stage.end_time is None
    
    def test_record_stage_complete(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录阶段完成"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.FACTOR_ARENA,
            stage_name="因子Arena测试",
            input_data={}
        )
        
        output_data = {"passed": True, "score": 0.85}
        
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="因子Arena测试",
            output_data=output_data
        )
        
        trace = manager.traces[trace_id]
        stage = trace.stage_records[0]
        
        assert stage.status == "completed"
        assert stage.output_data == output_data
        assert stage.end_time is not None
        assert stage.duration_seconds is not None
        assert stage.duration_seconds >= 0
    
    def test_record_stage_failure(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录阶段失败"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.SPARTA_ARENA,
            stage_name="斯巴达Arena评估",
            input_data={}
        )
        
        error_message = "第一层验证未通过"
        
        manager.record_stage_failure(
            trace_id=trace_id,
            stage_name="斯巴达Arena评估",
            error_message=error_message
        )
        
        trace = manager.traces[trace_id]
        stage = trace.stage_records[0]
        
        assert stage.status == "failed"
        assert stage.error_message == error_message
        assert stage.end_time is not None
        assert stage.duration_seconds is not None
    
    def test_record_stage_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id记录阶段"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.record_stage_start(
                trace_id="invalid_trace_id",
                stage_type=StageType.FACTOR_ARENA,
                stage_name="测试",
                input_data={}
            )
    
    def test_record_stage_complete_with_invalid_stage(self, manager, sample_strategy_id, sample_strategy_name):
        """测试完成不存在的阶段"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        with pytest.raises(ValueError, match="找不到运行中的阶段"):
            manager.record_stage_complete(
                trace_id=trace_id,
                stage_name="不存在的阶段",
                output_data={}
            )
    
    def test_record_validation_layer(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录验证层级"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        metrics = {
            "sharpe_ratio": 2.5,
            "max_drawdown": 0.10,
            "win_rate": 0.65
        }
        thresholds = {
            "sharpe_ratio": 2.0,
            "max_drawdown": 0.12,
            "win_rate": 0.60
        }
        
        manager.record_validation_layer(
            trace_id=trace_id,
            layer_number=1,
            layer_name="投研级指标验证",
            score=0.95,
            passed=True,
            metrics=metrics,
            thresholds=thresholds,
            failed_metrics=[],
            execution_time_seconds=5.2
        )
        
        trace = manager.traces[trace_id]
        assert len(trace.validation_layer_records) == 1
        
        layer = trace.validation_layer_records[0]
        assert layer.layer_number == 1
        assert layer.layer_name == "投研级指标验证"
        assert layer.score == 0.95
        assert layer.passed is True
        assert layer.metrics == metrics
        assert layer.thresholds == thresholds
        assert layer.failed_metrics == []
        assert layer.execution_time_seconds == 5.2
    
    def test_record_validation_layer_failed(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录未通过的验证层级"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        metrics = {
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.20,
            "win_rate": 0.50
        }
        thresholds = {
            "sharpe_ratio": 2.0,
            "max_drawdown": 0.12,
            "win_rate": 0.60
        }
        failed_metrics = ["sharpe_ratio", "max_drawdown", "win_rate"]
        
        manager.record_validation_layer(
            trace_id=trace_id,
            layer_number=1,
            layer_name="投研级指标验证",
            score=0.60,
            passed=False,
            metrics=metrics,
            thresholds=thresholds,
            failed_metrics=failed_metrics,
            execution_time_seconds=5.2
        )
        
        trace = manager.traces[trace_id]
        layer = trace.validation_layer_records[0]
        
        assert layer.passed is False
        assert len(layer.failed_metrics) == 3
        assert "sharpe_ratio" in layer.failed_metrics
    
    def test_record_validation_layer_with_invalid_layer_number(self, manager, sample_strategy_id, sample_strategy_name):
        """测试使用无效层级编号"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        with pytest.raises(ValueError, match="层级编号必须在1-4之间"):
            manager.record_validation_layer(
                trace_id=trace_id,
                layer_number=5,
                layer_name="无效层级",
                score=0.8,
                passed=True,
                metrics={},
                thresholds={},
                failed_metrics=[],
                execution_time_seconds=1.0
            )
    
    def test_record_decision(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录决策"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        input_data = {
            "arena_score": 0.90,
            "layer_scores": [0.95, 0.88, 0.85, 0.92]
        }
        output_data = {
            "certification_level": "PLATINUM"
        }
        
        manager.record_decision(
            trace_id=trace_id,
            decision_type=DecisionType.LEVEL_DETERMINATION,
            decision_name="认证等级评定",
            input_data=input_data,
            output_data=output_data,
            decision_logic="Arena综合评分≥0.90且所有层级优秀",
            decision_result=CertificationLevel.PLATINUM,
            confidence_score=0.95
        )
        
        trace = manager.traces[trace_id]
        assert len(trace.decision_records) == 1
        
        decision = trace.decision_records[0]
        assert decision.decision_type == DecisionType.LEVEL_DETERMINATION
        assert decision.decision_name == "认证等级评定"
        assert decision.input_data == input_data
        assert decision.output_data == output_data
        assert decision.decision_result == CertificationLevel.PLATINUM
        assert decision.confidence_score == 0.95
    
    def test_complete_certification_trace(self, manager, sample_strategy_id, sample_strategy_name):
        """测试完成认证追踪"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.complete_certification_trace(
            trace_id=trace_id,
            certification_level=CertificationLevel.GOLD
        )
        
        trace = manager.traces[trace_id]
        assert trace.final_status == "completed"
        assert trace.certification_level == CertificationLevel.GOLD
        assert trace.end_time is not None
        assert trace.total_duration_seconds is not None
        assert trace.total_duration_seconds >= 0
    
    def test_fail_certification_trace(self, manager, sample_strategy_id, sample_strategy_name):
        """测试标记认证追踪失败"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.fail_certification_trace(
            trace_id=trace_id,
            failed_stage="斯巴达Arena评估",
            failure_reason="第一层验证未通过"
        )
        
        trace = manager.traces[trace_id]
        assert trace.final_status == "failed"
        assert trace.failed_stage == "斯巴达Arena评估"
        assert trace.failure_reason == "第一层验证未通过"
        assert trace.end_time is not None
        assert trace.total_duration_seconds is not None
    
    def test_get_trace(self, manager, sample_strategy_id, sample_strategy_name):
        """测试获取追踪记录"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        trace = manager.get_trace(trace_id)
        assert trace is not None
        assert trace.trace_id == trace_id
        
        # 测试不存在的trace_id
        non_existent_trace = manager.get_trace("non_existent_id")
        assert non_existent_trace is None
    
    def test_query_traces_by_strategy(self, manager):
        """测试按策略ID查询"""
        # 创建多个追踪记录
        trace_id_1 = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="策略1"
        )
        trace_id_2 = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="策略1"
        )
        trace_id_3 = manager.start_certification_trace(
            strategy_id="strategy_002",
            strategy_name="策略2"
        )
        
        # 查询strategy_001的追踪记录
        results = manager.query_traces_by_strategy("strategy_001")
        assert len(results) == 2
        assert all(trace.strategy_id == "strategy_001" for trace in results)
        
        # 查询strategy_002的追踪记录
        results = manager.query_traces_by_strategy("strategy_002")
        assert len(results) == 1
        assert results[0].strategy_id == "strategy_002"
        
        # 查询不存在的策略
        results = manager.query_traces_by_strategy("strategy_999")
        assert len(results) == 0
    
    def test_query_traces_by_date_range(self, manager):
        """测试按日期范围查询"""
        # 创建追踪记录
        trace_id = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="策略1"
        )
        
        # 查询包含当前时间的范围
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now() + timedelta(hours=1)
        
        results = manager.query_traces_by_date_range(start_date, end_date)
        assert len(results) == 1
        assert results[0].trace_id == trace_id
        
        # 查询不包含当前时间的范围
        start_date = datetime.now() - timedelta(days=2)
        end_date = datetime.now() - timedelta(days=1)
        
        results = manager.query_traces_by_date_range(start_date, end_date)
        assert len(results) == 0
    
    def test_query_traces_by_date_range_invalid(self, manager):
        """测试使用无效日期范围查询"""
        start_date = datetime.now()
        end_date = datetime.now() - timedelta(days=1)
        
        with pytest.raises(ValueError, match="开始日期不能晚于结束日期"):
            manager.query_traces_by_date_range(start_date, end_date)
    
    def test_query_traces_by_level(self, manager):
        """测试按认证等级查询"""
        # 创建并完成多个追踪记录
        trace_id_1 = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="策略1"
        )
        manager.complete_certification_trace(trace_id_1, CertificationLevel.PLATINUM)
        
        trace_id_2 = manager.start_certification_trace(
            strategy_id="strategy_002",
            strategy_name="策略2"
        )
        manager.complete_certification_trace(trace_id_2, CertificationLevel.GOLD)
        
        trace_id_3 = manager.start_certification_trace(
            strategy_id="strategy_003",
            strategy_name="策略3"
        )
        manager.complete_certification_trace(trace_id_3, CertificationLevel.PLATINUM)
        
        # 查询PLATINUM等级
        results = manager.query_traces_by_level(CertificationLevel.PLATINUM)
        assert len(results) == 2
        assert all(trace.certification_level == CertificationLevel.PLATINUM for trace in results)
        
        # 查询GOLD等级
        results = manager.query_traces_by_level(CertificationLevel.GOLD)
        assert len(results) == 1
        assert results[0].certification_level == CertificationLevel.GOLD
        
        # 查询SILVER等级
        results = manager.query_traces_by_level(CertificationLevel.SILVER)
        assert len(results) == 0
    
    def test_query_traces_by_status(self, manager):
        """测试按状态查询"""
        # 创建不同状态的追踪记录
        trace_id_1 = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="策略1"
        )
        manager.complete_certification_trace(trace_id_1, CertificationLevel.PLATINUM)
        
        trace_id_2 = manager.start_certification_trace(
            strategy_id="strategy_002",
            strategy_name="策略2"
        )
        manager.fail_certification_trace(trace_id_2, "Arena评估", "未通过")
        
        trace_id_3 = manager.start_certification_trace(
            strategy_id="strategy_003",
            strategy_name="策略3"
        )
        # 保持in_progress状态
        
        # 查询completed状态
        results = manager.query_traces_by_status("completed")
        assert len(results) == 1
        assert results[0].final_status == "completed"
        
        # 查询failed状态
        results = manager.query_traces_by_status("failed")
        assert len(results) == 1
        assert results[0].final_status == "failed"
        
        # 查询in_progress状态
        results = manager.query_traces_by_status("in_progress")
        assert len(results) == 1
        assert results[0].final_status == "in_progress"
    
    def test_query_traces_by_status_invalid(self, manager):
        """测试使用无效状态查询"""
        with pytest.raises(ValueError, match="无效的状态"):
            manager.query_traces_by_status("invalid_status")

    
    def test_generate_audit_report_basic(self, manager, sample_strategy_id, sample_strategy_name):
        """测试生成基本审计报告"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        # 添加一些记录
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.SPARTA_ARENA,
            stage_name="斯巴达Arena评估",
            input_data={"strategy_id": sample_strategy_id}
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="斯巴达Arena评估",
            output_data={"passed": True, "score": 0.90}
        )
        
        manager.record_validation_layer(
            trace_id=trace_id,
            layer_number=1,
            layer_name="投研级指标验证",
            score=0.95,
            passed=True,
            metrics={"sharpe_ratio": 2.5},
            thresholds={"sharpe_ratio": 2.0},
            failed_metrics=[],
            execution_time_seconds=5.0
        )
        
        manager.record_decision(
            trace_id=trace_id,
            decision_type=DecisionType.LEVEL_DETERMINATION,
            decision_name="认证等级评定",
            input_data={"arena_score": 0.90},
            output_data={"level": "PLATINUM"},
            decision_logic="Arena≥0.90",
            decision_result=CertificationLevel.PLATINUM
        )
        
        manager.complete_certification_trace(trace_id, CertificationLevel.PLATINUM)
        
        # 生成报告
        report = manager.generate_audit_report(trace_id, include_raw_data=False)
        
        # 验证报告结构
        assert "report_id" in report
        assert "trace_id" in report
        assert report["trace_id"] == trace_id
        assert report["strategy_id"] == sample_strategy_id
        assert report["strategy_name"] == sample_strategy_name
        assert report["final_status"] == "completed"
        assert report["certification_level"] == "platinum"
        
        # 验证阶段摘要
        assert "stage_summary" in report
        assert report["stage_summary"]["total_stages"] == 1
        assert report["stage_summary"]["completed_stages"] == 1
        assert report["stage_summary"]["failed_stages"] == 0
        
        # 验证阶段详情
        assert "stages" in report
        assert len(report["stages"]) == 1
        assert report["stages"][0]["stage_name"] == "斯巴达Arena评估"
        assert report["stages"][0]["status"] == "completed"
        
        # 验证验证层级摘要
        assert "validation_summary" in report
        assert report["validation_summary"]["total_layers"] == 1
        assert report["validation_summary"]["passed_layers"] == 1
        assert report["validation_summary"]["failed_layers"] == 0
        
        # 验证验证层级详情
        assert "validation_layers" in report
        assert len(report["validation_layers"]) == 1
        assert report["validation_layers"][0]["layer_number"] == 1
        assert report["validation_layers"][0]["passed"] is True
        
        # 验证决策摘要
        assert "decision_summary" in report
        assert report["decision_summary"]["total_decisions"] == 1
        
        # 验证决策详情
        assert "decisions" in report
        assert len(report["decisions"]) == 1
        assert report["decisions"][0]["decision_name"] == "认证等级评定"
    
    def test_generate_audit_report_with_raw_data(self, manager, sample_strategy_id, sample_strategy_name):
        """测试生成包含原始数据的审计报告"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name,
            metadata={"version": "1.0"}
        )
        
        input_data = {"strategy_id": sample_strategy_id}
        output_data = {"passed": True}
        
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.SPARTA_ARENA,
            stage_name="测试阶段",
            input_data=input_data
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="测试阶段",
            output_data=output_data
        )
        
        manager.complete_certification_trace(trace_id, CertificationLevel.GOLD)
        
        # 生成包含原始数据的报告
        report = manager.generate_audit_report(trace_id, include_raw_data=True)
        
        # 验证原始数据包含在报告中
        assert "input_data" in report["stages"][0]
        assert report["stages"][0]["input_data"] == input_data
        assert "output_data" in report["stages"][0]
        assert report["stages"][0]["output_data"] == output_data
        assert "trace_metadata" in report
        assert report["trace_metadata"]["version"] == "1.0"
    
    def test_generate_audit_report_failed_trace(self, manager, sample_strategy_id, sample_strategy_name):
        """测试生成失败追踪的审计报告"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.SPARTA_ARENA,
            stage_name="斯巴达Arena评估",
            input_data={}
        )
        manager.record_stage_failure(
            trace_id=trace_id,
            stage_name="斯巴达Arena评估",
            error_message="第一层验证未通过"
        )
        
        manager.fail_certification_trace(
            trace_id=trace_id,
            failed_stage="斯巴达Arena评估",
            failure_reason="第一层验证未通过"
        )
        
        report = manager.generate_audit_report(trace_id)
        
        assert report["final_status"] == "failed"
        assert report["failed_stage"] == "斯巴达Arena评估"
        assert report["failure_reason"] == "第一层验证未通过"
        assert report["stage_summary"]["failed_stages"] == 1
        assert report["stages"][0]["status"] == "failed"
        assert report["stages"][0]["error_message"] == "第一层验证未通过"
    
    def test_generate_audit_report_invalid_trace_id(self, manager):
        """测试使用无效trace_id生成报告"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.generate_audit_report("invalid_trace_id")
    
    def test_export_audit_report_json(self, manager, sample_strategy_id, sample_strategy_name):
        """测试导出审计报告为JSON"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.complete_certification_trace(trace_id, CertificationLevel.SILVER)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            # 导出报告
            manager.export_audit_report_json(trace_id, output_path)
            
            # 验证文件存在
            assert os.path.exists(output_path)
            
            # 读取并验证JSON内容
            with open(output_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            assert report["trace_id"] == trace_id
            assert report["strategy_id"] == sample_strategy_id
            assert report["certification_level"] == "silver"
            
        finally:
            # 清理临时文件
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_export_audit_report_json_invalid_path(self, manager, sample_strategy_id, sample_strategy_name):
        """测试导出到无效路径"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        manager.complete_certification_trace(trace_id, CertificationLevel.GOLD)
        
        # 使用一个在所有平台上都无效的路径
        invalid_path = "Z:\\nonexistent_drive_12345\\invalid\\path\\report.json"
        
        with pytest.raises((IOError, OSError)):
            manager.export_audit_report_json(trace_id, invalid_path)
    
    def test_get_statistics_empty(self, manager):
        """测试获取空统计信息"""
        stats = manager.get_statistics()
        
        assert stats["total_traces"] == 0
        assert stats["status_distribution"] == {}
        assert stats["level_distribution"] == {}
        assert stats["average_duration_seconds"] == 0.0
        assert stats["success_rate"] == 0.0
    
    def test_get_statistics_with_data(self, manager):
        """测试获取统计信息"""
        # 创建多个追踪记录
        trace_id_1 = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="策略1"
        )
        manager.complete_certification_trace(trace_id_1, CertificationLevel.PLATINUM)
        
        trace_id_2 = manager.start_certification_trace(
            strategy_id="strategy_002",
            strategy_name="策略2"
        )
        manager.complete_certification_trace(trace_id_2, CertificationLevel.GOLD)
        
        trace_id_3 = manager.start_certification_trace(
            strategy_id="strategy_003",
            strategy_name="策略3"
        )
        manager.fail_certification_trace(trace_id_3, "Arena评估", "未通过")
        
        trace_id_4 = manager.start_certification_trace(
            strategy_id="strategy_004",
            strategy_name="策略4"
        )
        # 保持in_progress状态
        
        stats = manager.get_statistics()
        
        assert stats["total_traces"] == 4
        assert stats["status_distribution"]["completed"] == 2
        assert stats["status_distribution"]["failed"] == 1
        assert stats["status_distribution"]["in_progress"] == 1
        assert stats["level_distribution"]["platinum"] == 1
        assert stats["level_distribution"]["gold"] == 1
        assert stats["average_duration_seconds"] >= 0
        assert stats["success_rate"] == 0.5  # 2 completed out of 4 total
    
    def test_multiple_stages_same_trace(self, manager, sample_strategy_id, sample_strategy_name):
        """测试同一追踪记录多个阶段"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        # 阶段1
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.FACTOR_ARENA,
            stage_name="因子Arena测试",
            input_data={}
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="因子Arena测试",
            output_data={"passed": True}
        )
        
        # 阶段2
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.STRATEGY_GENERATION,
            stage_name="策略生成",
            input_data={}
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="策略生成",
            output_data={"strategy_count": 3}
        )
        
        # 阶段3
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.SPARTA_ARENA,
            stage_name="斯巴达Arena评估",
            input_data={}
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="斯巴达Arena评估",
            output_data={"score": 0.85}
        )
        
        trace = manager.traces[trace_id]
        assert len(trace.stage_records) == 3
        assert all(stage.status == "completed" for stage in trace.stage_records)
    
    def test_multiple_validation_layers(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录多个验证层级"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        # 记录4个层级
        for layer_num in range(1, 5):
            manager.record_validation_layer(
                trace_id=trace_id,
                layer_number=layer_num,
                layer_name=f"第{layer_num}层验证",
                score=0.80 + layer_num * 0.03,
                passed=True,
                metrics={},
                thresholds={},
                failed_metrics=[],
                execution_time_seconds=5.0
            )
        
        trace = manager.traces[trace_id]
        assert len(trace.validation_layer_records) == 4
        assert all(layer.passed for layer in trace.validation_layer_records)
        
        # 验证层级编号正确
        layer_numbers = [layer.layer_number for layer in trace.validation_layer_records]
        assert layer_numbers == [1, 2, 3, 4]
    
    def test_multiple_decisions(self, manager, sample_strategy_id, sample_strategy_name):
        """测试记录多个决策"""
        trace_id = manager.start_certification_trace(
            strategy_id=sample_strategy_id,
            strategy_name=sample_strategy_name
        )
        
        # 决策1: 资格检查
        manager.record_decision(
            trace_id=trace_id,
            decision_type=DecisionType.ELIGIBILITY_CHECK,
            decision_name="资格检查",
            input_data={"arena_passed": True},
            output_data={"eligible": True},
            decision_logic="Arena通过且模拟盘达标",
            decision_result=True
        )
        
        # 决策2: 等级评定
        manager.record_decision(
            trace_id=trace_id,
            decision_type=DecisionType.LEVEL_DETERMINATION,
            decision_name="等级评定",
            input_data={"arena_score": 0.85},
            output_data={"level": "GOLD"},
            decision_logic="Arena≥0.80",
            decision_result=CertificationLevel.GOLD
        )
        
        # 决策3: 资金配置
        manager.record_decision(
            trace_id=trace_id,
            decision_type=DecisionType.CAPITAL_ALLOCATION,
            decision_name="资金配置",
            input_data={"level": "GOLD"},
            output_data={"max_ratio": 0.15},
            decision_logic="GOLD等级最大15%",
            decision_result=0.15
        )
        
        trace = manager.traces[trace_id]
        assert len(trace.decision_records) == 3
        
        # 验证决策类型
        decision_types = [d.decision_type for d in trace.decision_records]
        assert DecisionType.ELIGIBILITY_CHECK in decision_types
        assert DecisionType.LEVEL_DETERMINATION in decision_types
        assert DecisionType.CAPITAL_ALLOCATION in decision_types
    
    def test_complex_workflow(self, manager):
        """测试完整的复杂工作流"""
        # 开始追踪
        trace_id = manager.start_certification_trace(
            strategy_id="complex_strategy",
            strategy_name="复杂策略测试",
            metadata={"version": "2.0", "market": "A_STOCK"}
        )
        
        # 阶段1: 因子Arena
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.FACTOR_ARENA,
            stage_name="因子Arena测试",
            input_data={"factor_count": 10}
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="因子Arena测试",
            output_data={"passed_factors": 7}
        )
        
        # 阶段2: 策略生成
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.STRATEGY_GENERATION,
            stage_name="策略生成",
            input_data={"factor_count": 7}
        )
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="策略生成",
            output_data={"strategy_count": 5}
        )
        
        # 阶段3: 斯巴达Arena评估
        manager.record_stage_start(
            trace_id=trace_id,
            stage_type=StageType.SPARTA_ARENA,
            stage_name="斯巴达Arena评估",
            input_data={"strategy_id": "complex_strategy"}
        )
        
        # 记录4个验证层级
        for layer_num in range(1, 5):
            manager.record_validation_layer(
                trace_id=trace_id,
                layer_number=layer_num,
                layer_name=f"第{layer_num}层验证",
                score=0.85 + layer_num * 0.02,
                passed=True,
                metrics={"metric1": 0.9},
                thresholds={"metric1": 0.8},
                failed_metrics=[],
                execution_time_seconds=5.0 + layer_num
            )
        
        manager.record_stage_complete(
            trace_id=trace_id,
            stage_name="斯巴达Arena评估",
            output_data={"overall_score": 0.88}
        )
        
        # 决策: 等级评定
        manager.record_decision(
            trace_id=trace_id,
            decision_type=DecisionType.LEVEL_DETERMINATION,
            decision_name="认证等级评定",
            input_data={"arena_score": 0.88},
            output_data={"level": "GOLD"},
            decision_logic="Arena≥0.80且<0.90",
            decision_result=CertificationLevel.GOLD,
            confidence_score=0.92
        )
        
        # 完成追踪
        manager.complete_certification_trace(trace_id, CertificationLevel.GOLD)
        
        # 验证追踪记录
        trace = manager.traces[trace_id]
        assert trace.final_status == "completed"
        assert trace.certification_level == CertificationLevel.GOLD
        assert len(trace.stage_records) == 3
        assert len(trace.validation_layer_records) == 4
        assert len(trace.decision_records) == 1
        
        # 生成审计报告
        report = manager.generate_audit_report(trace_id, include_raw_data=True)
        assert report["stage_summary"]["total_stages"] == 3
        assert report["stage_summary"]["completed_stages"] == 3
        assert report["validation_summary"]["total_layers"] == 4
        assert report["validation_summary"]["passed_layers"] == 4
        assert report["decision_summary"]["total_decisions"] == 1


class TestStageExecutionRecord:
    """测试StageExecutionRecord类"""
    
    def test_stage_record_creation(self):
        """测试阶段记录创建"""
        record = StageExecutionRecord(
            stage_type=StageType.SPARTA_ARENA,
            stage_name="测试阶段",
            start_time=datetime.now(),
            input_data={"key": "value"}
        )
        
        assert record.stage_type == StageType.SPARTA_ARENA
        assert record.stage_name == "测试阶段"
        assert record.status == "running"
        assert record.end_time is None
        assert record.duration_seconds is None
    
    def test_stage_record_complete(self):
        """测试标记阶段完成"""
        record = StageExecutionRecord(
            stage_type=StageType.SPARTA_ARENA,
            stage_name="测试阶段",
            start_time=datetime.now()
        )
        
        output_data = {"result": "success"}
        record.complete(output_data)
        
        assert record.status == "completed"
        assert record.output_data == output_data
        assert record.end_time is not None
        assert record.duration_seconds is not None
        assert record.duration_seconds >= 0
    
    def test_stage_record_fail(self):
        """测试标记阶段失败"""
        record = StageExecutionRecord(
            stage_type=StageType.SPARTA_ARENA,
            stage_name="测试阶段",
            start_time=datetime.now()
        )
        
        error_message = "测试错误"
        record.fail(error_message)
        
        assert record.status == "failed"
        assert record.error_message == error_message
        assert record.end_time is not None
        assert record.duration_seconds is not None


class TestValidationLayerRecord:
    """测试ValidationLayerRecord类"""
    
    def test_layer_record_creation(self):
        """测试层级记录创建"""
        metrics = {"sharpe_ratio": 2.5, "max_drawdown": 0.10}
        thresholds = {"sharpe_ratio": 2.0, "max_drawdown": 0.12}
        
        record = ValidationLayerRecord(
            layer_number=1,
            layer_name="投研级指标验证",
            score=0.95,
            passed=True,
            metrics=metrics,
            thresholds=thresholds,
            failed_metrics=[],
            execution_time_seconds=5.2
        )
        
        assert record.layer_number == 1
        assert record.layer_name == "投研级指标验证"
        assert record.score == 0.95
        assert record.passed is True
        assert record.metrics == metrics
        assert record.thresholds == thresholds
        assert record.failed_metrics == []
        assert record.execution_time_seconds == 5.2


class TestDecisionRecord:
    """测试DecisionRecord类"""
    
    def test_decision_record_creation(self):
        """测试决策记录创建"""
        input_data = {"arena_score": 0.90}
        output_data = {"level": "PLATINUM"}
        
        record = DecisionRecord(
            decision_type=DecisionType.LEVEL_DETERMINATION,
            decision_name="认证等级评定",
            timestamp=datetime.now(),
            input_data=input_data,
            output_data=output_data,
            decision_logic="Arena≥0.90",
            decision_result=CertificationLevel.PLATINUM,
            confidence_score=0.95
        )
        
        assert record.decision_type == DecisionType.LEVEL_DETERMINATION
        assert record.decision_name == "认证等级评定"
        assert record.input_data == input_data
        assert record.output_data == output_data
        assert record.decision_logic == "Arena≥0.90"
        assert record.decision_result == CertificationLevel.PLATINUM
        assert record.confidence_score == 0.95


class TestCertificationTrace:
    """测试CertificationTrace类"""
    
    def test_trace_creation(self):
        """测试追踪记录创建"""
        trace = CertificationTrace(
            trace_id="trace_001",
            strategy_id="strategy_001",
            strategy_name="测试策略",
            start_time=datetime.now()
        )
        
        assert trace.trace_id == "trace_001"
        assert trace.strategy_id == "strategy_001"
        assert trace.strategy_name == "测试策略"
        assert trace.final_status == "in_progress"
        assert trace.end_time is None
        assert len(trace.stage_records) == 0
        assert len(trace.validation_layer_records) == 0
        assert len(trace.decision_records) == 0
    
    def test_trace_complete(self):
        """测试完成追踪"""
        trace = CertificationTrace(
            trace_id="trace_001",
            strategy_id="strategy_001",
            strategy_name="测试策略",
            start_time=datetime.now()
        )
        
        trace.complete(CertificationLevel.GOLD)
        
        assert trace.final_status == "completed"
        assert trace.certification_level == CertificationLevel.GOLD
        assert trace.end_time is not None
        assert trace.total_duration_seconds is not None
        assert trace.total_duration_seconds >= 0
    
    def test_trace_fail(self):
        """测试失败追踪"""
        trace = CertificationTrace(
            trace_id="trace_001",
            strategy_id="strategy_001",
            strategy_name="测试策略",
            start_time=datetime.now()
        )
        
        trace.fail("Arena评估", "第一层未通过")
        
        assert trace.final_status == "failed"
        assert trace.failed_stage == "Arena评估"
        assert trace.failure_reason == "第一层未通过"
        assert trace.end_time is not None
        assert trace.total_duration_seconds is not None



class TestEdgeCasesForFullCoverage:
    """测试边界情况以达到100%覆盖率"""
    
    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return CertificationTraceabilityManager()
    
    def test_record_stage_complete_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id完成阶段"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.record_stage_complete(
                trace_id="invalid_trace_id",
                stage_name="测试阶段",
                output_data={}
            )
    
    def test_record_stage_failure_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id记录阶段失败"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.record_stage_failure(
                trace_id="invalid_trace_id",
                stage_name="测试阶段",
                error_message="错误"
            )
    
    def test_record_validation_layer_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id记录验证层级"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.record_validation_layer(
                trace_id="invalid_trace_id",
                layer_number=1,
                layer_name="测试层级",
                score=0.8,
                passed=True,
                metrics={},
                thresholds={},
                failed_metrics=[],
                execution_time_seconds=1.0
            )
    
    def test_record_decision_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id记录决策"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.record_decision(
                trace_id="invalid_trace_id",
                decision_type=DecisionType.LEVEL_DETERMINATION,
                decision_name="测试决策",
                input_data={},
                output_data={},
                decision_logic="测试逻辑",
                decision_result="测试结果"
            )
    
    def test_complete_certification_trace_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id完成认证追踪"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.complete_certification_trace(
                trace_id="invalid_trace_id",
                certification_level=CertificationLevel.GOLD
            )
    
    def test_fail_certification_trace_with_invalid_trace_id(self, manager):
        """测试使用无效trace_id标记认证失败"""
        with pytest.raises(ValueError, match="追踪ID不存在"):
            manager.fail_certification_trace(
                trace_id="invalid_trace_id",
                failed_stage="测试阶段",
                failure_reason="测试原因"
            )
    
    def test_record_stage_failure_with_invalid_stage_name(self, manager):
        """测试使用无效阶段名称记录失败"""
        trace_id = manager.start_certification_trace(
            strategy_id="strategy_001",
            strategy_name="测试策略"
        )
        
        with pytest.raises(ValueError, match="找不到运行中的阶段"):
            manager.record_stage_failure(
                trace_id=trace_id,
                stage_name="不存在的阶段",
                error_message="错误"
            )
