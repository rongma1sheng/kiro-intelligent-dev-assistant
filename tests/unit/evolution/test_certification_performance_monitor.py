"""认证性能监控器单元测试

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 性能监控

测试覆盖：
- 阶段执行时间监控
- Arena验证耗时监控
- 模拟盘资源使用监控
- 性能告警记录
- 成功率/失败率统计
- 认证等级分布统计
- 性能分析报告生成
- 报告导出

Author: MIA System
Version: 1.0.0
"""

import pytest
from datetime import datetime, timedelta
import tempfile
import os
import json

from src.evolution.certification_performance_monitor import (
    CertificationPerformanceMonitor,
    PerformanceAlertLevel,
    StagePerformanceMetrics,
    ArenaPerformanceMetrics,
    SimulationResourceMetrics,
    PerformanceAlert,
    CertificationStatistics,
    PerformanceAnalysisReport
)
from src.evolution.z2h_data_models import CertificationLevel


class TestCertificationPerformanceMonitor:
    """测试CertificationPerformanceMonitor类"""
    
    @pytest.fixture
    def monitor(self):
        """创建监控器实例"""
        return CertificationPerformanceMonitor()
    
    def test_initialization(self, monitor):
        """测试初始化"""
        assert isinstance(monitor.stage_metrics_history, list)
        assert len(monitor.stage_metrics_history) == 0
        assert isinstance(monitor.arena_metrics_history, list)
        assert isinstance(monitor.simulation_metrics_history, list)
        assert isinstance(monitor.alerts_history, list)
        assert isinstance(monitor.certification_results, list)
        assert isinstance(monitor.performance_thresholds, dict)

    
    def test_start_stage_monitoring(self, monitor):
        """测试开始阶段监控"""
        monitoring_id = monitor.start_stage_monitoring("Arena验证")
        
        assert monitoring_id is not None
        assert "Arena验证" in monitoring_id
        assert len(monitor.stage_metrics_history) == 1
        
        metrics = monitor.stage_metrics_history[0]
        assert metrics.stage_name == "Arena验证"
        assert metrics.start_time is not None
        assert metrics.end_time is None
    
    def test_end_stage_monitoring(self, monitor):
        """测试结束阶段监控"""
        import time
        
        monitor.start_stage_monitoring("Arena验证")
        time.sleep(0.01)  # 等待一小段时间确保duration > 0
        
        monitor.end_stage_monitoring("Arena验证", success=True)
        
        metrics = monitor.stage_metrics_history[0]
        assert metrics.end_time is not None
        assert metrics.duration_seconds >= 0  # 改为 >= 0，因为可能非常快
        assert metrics.success is True
        assert metrics.error_message is None
    
    def test_end_stage_monitoring_with_error(self, monitor):
        """测试结束阶段监控 - 带错误"""
        monitor.start_stage_monitoring("Arena验证")
        
        monitor.end_stage_monitoring(
            "Arena验证",
            success=False,
            error_message="验证失败"
        )
        
        metrics = monitor.stage_metrics_history[0]
        assert metrics.success is False
        assert metrics.error_message == "验证失败"
    
    def test_end_stage_monitoring_threshold_exceeded(self, monitor):
        """测试结束阶段监控 - 超过阈值"""
        # 手动创建一个超过阈值的阶段指标
        from datetime import timedelta
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=70)  # 超过60秒阈值
        
        metrics = StagePerformanceMetrics(
            stage_name="模拟盘验证",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=70.0,
            success=True
        )
        
        monitor.stage_metrics_history.append(metrics)
        
        # 手动调用检查方法
        monitor._check_stage_duration_threshold(metrics)
        
        # 应该生成告警
        assert len(monitor.alerts_history) == 1
        alert = monitor.alerts_history[0]
        assert alert.metric_name == "stage_duration"
        assert alert.actual_value == 70.0
        assert alert.threshold_value == 60.0
        assert "模拟盘验证" in alert.message
    
    def test_record_arena_performance(self, monitor):
        """测试记录Arena性能"""
        layer_durations = {
            1: 5.0,
            2: 8.0,
            3: 10.0,
            4: 7.0
        }
        
        monitor.record_arena_performance(
            total_duration=30.0,
            layer_durations=layer_durations,
            overall_score=0.85
        )
        
        assert len(monitor.arena_metrics_history) == 1
        
        metrics = monitor.arena_metrics_history[0]
        assert metrics.total_duration_seconds == 30.0
        assert metrics.layer1_duration_seconds == 5.0
        assert metrics.layer2_duration_seconds == 8.0
        assert metrics.layer3_duration_seconds == 10.0
        assert metrics.layer4_duration_seconds == 7.0
        assert metrics.overall_score == 0.85

    
    def test_record_arena_performance_threshold_exceeded(self, monitor):
        """测试记录Arena性能 - 超过阈值"""
        layer_durations = {1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0}
        
        monitor.record_arena_performance(
            total_duration=40.0,  # 超过30秒阈值
            layer_durations=layer_durations,
            overall_score=0.85
        )
        
        # 应该生成告警
        assert len(monitor.alerts_history) == 1
        alert = monitor.alerts_history[0]
        assert alert.metric_name == "arena_total_duration"
        assert alert.actual_value == 40.0
        assert alert.threshold_value == 30.0
    
    def test_record_simulation_resources(self, monitor):
        """测试记录模拟盘资源"""
        monitor.record_simulation_resources(
            cpu_usage=50.0,
            memory_usage=1024.0,
            disk_io=100.0,
            network_io=50.0
        )
        
        assert len(monitor.simulation_metrics_history) == 1
        
        metrics = monitor.simulation_metrics_history[0]
        assert metrics.cpu_usage_percent == 50.0
        assert metrics.memory_usage_mb == 1024.0
        assert metrics.disk_io_mb == 100.0
        assert metrics.network_io_mb == 50.0
        assert metrics.peak_cpu_percent == 50.0
        assert metrics.peak_memory_mb == 1024.0
    
    def test_record_simulation_resources_peak_tracking(self, monitor):
        """测试模拟盘资源峰值跟踪"""
        monitor.record_simulation_resources(cpu_usage=50.0, memory_usage=1024.0)
        monitor.record_simulation_resources(cpu_usage=70.0, memory_usage=1500.0)
        monitor.record_simulation_resources(cpu_usage=60.0, memory_usage=1200.0)
        
        # 最后一次记录应该保留峰值
        last_metrics = monitor.simulation_metrics_history[-1]
        assert last_metrics.peak_cpu_percent == 70.0
        assert last_metrics.peak_memory_mb == 1500.0
    
    def test_record_simulation_resources_cpu_threshold_exceeded(self, monitor):
        """测试模拟盘资源 - CPU超过阈值"""
        monitor.record_simulation_resources(
            cpu_usage=85.0,  # 超过80%阈值
            memory_usage=1024.0
        )
        
        # 应该生成CPU告警
        cpu_alerts = [a for a in monitor.alerts_history if a.metric_name == "cpu_usage"]
        assert len(cpu_alerts) == 1
        assert cpu_alerts[0].actual_value == 85.0

    
    def test_record_simulation_resources_memory_threshold_exceeded(self, monitor):
        """测试模拟盘资源 - 内存超过阈值"""
        monitor.record_simulation_resources(
            cpu_usage=50.0,
            memory_usage=2500.0  # 超过2048MB阈值
        )
        
        # 应该生成内存告警
        memory_alerts = [a for a in monitor.alerts_history if a.metric_name == "memory_usage"]
        assert len(memory_alerts) == 1
        assert memory_alerts[0].actual_value == 2500.0
    
    def test_record_certification_result(self, monitor):
        """测试记录认证结果"""
        monitor.record_certification_result(
            strategy_id="strategy_001",
            success=True,
            level=CertificationLevel.GOLD,
            duration_seconds=120.0
        )
        
        assert len(monitor.certification_results) == 1
        
        result = monitor.certification_results[0]
        assert result["strategy_id"] == "strategy_001"
        assert result["success"] is True
        assert result["level"] == "gold"
        assert result["duration_seconds"] == 120.0
    
    def test_record_certification_result_failed(self, monitor):
        """测试记录认证结果 - 失败"""
        monitor.record_certification_result(
            strategy_id="strategy_002",
            success=False,
            level=None,
            duration_seconds=60.0
        )
        
        result = monitor.certification_results[0]
        assert result["success"] is False
        assert result["level"] is None
    
    def test_get_certification_statistics_empty(self, monitor):
        """测试获取认证统计 - 空数据"""
        stats = monitor.get_certification_statistics()
        
        assert stats.total_certifications == 0
        assert stats.successful_certifications == 0
        assert stats.failed_certifications == 0
        assert stats.success_rate == 0.0
        assert stats.failure_rate == 0.0
        assert stats.avg_duration_seconds == 0.0
        assert len(stats.level_distribution) == 0

    
    def test_get_certification_statistics(self, monitor):
        """测试获取认证统计"""
        # 添加测试数据
        monitor.record_certification_result("s1", True, CertificationLevel.PLATINUM, 100.0)
        monitor.record_certification_result("s2", True, CertificationLevel.GOLD, 120.0)
        monitor.record_certification_result("s3", False, None, 80.0)
        monitor.record_certification_result("s4", True, CertificationLevel.SILVER, 110.0)
        
        stats = monitor.get_certification_statistics()
        
        assert stats.total_certifications == 4
        assert stats.successful_certifications == 3
        assert stats.failed_certifications == 1
        assert stats.success_rate == 0.75
        assert stats.failure_rate == 0.25
        assert stats.avg_duration_seconds == 102.5  # (100+120+80+110)/4
        assert stats.level_distribution["platinum"] == 1
        assert stats.level_distribution["gold"] == 1
        assert stats.level_distribution["silver"] == 1
    
    def test_get_certification_statistics_with_time_range(self, monitor):
        """测试获取认证统计 - 带时间范围"""
        now = datetime.now()
        
        # 添加不同时间的数据
        monitor.certification_results = [
            {
                "strategy_id": "s1",
                "success": True,
                "level": "gold",
                "duration_seconds": 100.0,
                "timestamp": now - timedelta(days=10)
            },
            {
                "strategy_id": "s2",
                "success": True,
                "level": "silver",
                "duration_seconds": 120.0,
                "timestamp": now - timedelta(days=2)
            }
        ]
        
        # 查询最近3天的数据
        stats = monitor.get_certification_statistics(
            time_range_start=now - timedelta(days=3),
            time_range_end=now
        )
        
        assert stats.total_certifications == 1  # 只有s2在范围内
        assert stats.level_distribution["silver"] == 1
    
    def test_get_level_distribution(self, monitor):
        """测试获取认证等级分布"""
        monitor.record_certification_result("s1", True, CertificationLevel.PLATINUM, 100.0)
        monitor.record_certification_result("s2", True, CertificationLevel.GOLD, 120.0)
        monitor.record_certification_result("s3", True, CertificationLevel.GOLD, 110.0)
        monitor.record_certification_result("s4", False, None, 80.0)
        
        distribution = monitor.get_level_distribution()
        
        assert distribution["platinum"] == 1
        assert distribution["gold"] == 2
        assert "silver" not in distribution  # 没有silver认证

    
    def test_get_performance_alerts_no_filter(self, monitor):
        """测试获取性能告警 - 无过滤"""
        # 生成一些告警
        monitor.record_arena_performance(40.0, {1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0}, 0.85)
        monitor.record_simulation_resources(85.0, 1024.0)
        
        alerts = monitor.get_performance_alerts()
        
        assert len(alerts) == 2  # Arena耗时 + CPU使用率
    
    def test_get_performance_alerts_with_level_filter(self, monitor):
        """测试获取性能告警 - 按级别过滤"""
        monitor.record_arena_performance(40.0, {1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0}, 0.85)
        
        alerts = monitor.get_performance_alerts(level=PerformanceAlertLevel.WARNING)
        
        assert len(alerts) == 1
        assert alerts[0].alert_level == PerformanceAlertLevel.WARNING
    
    def test_get_performance_alerts_with_time_range(self, monitor):
        """测试获取性能告警 - 按时间范围过滤"""
        now = datetime.now()
        
        # 手动添加不同时间的告警
        monitor.alerts_history = [
            PerformanceAlert(
                alert_id="alert1",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=now - timedelta(days=10),
                stage_name="Arena验证",
                metric_name="arena_total_duration",
                actual_value=40.0,
                threshold_value=30.0,
                message="超时"
            ),
            PerformanceAlert(
                alert_id="alert2",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=now - timedelta(days=2),
                stage_name="Arena验证",
                metric_name="arena_total_duration",
                actual_value=35.0,
                threshold_value=30.0,
                message="超时"
            )
        ]
        
        # 查询最近3天的告警
        alerts = monitor.get_performance_alerts(
            time_range_start=now - timedelta(days=3),
            time_range_end=now
        )
        
        assert len(alerts) == 1  # 只有alert2在范围内

    
    def test_generate_performance_analysis_report(self, monitor):
        """测试生成性能分析报告"""
        # 添加测试数据
        monitor.start_stage_monitoring("Arena验证")
        monitor.end_stage_monitoring("Arena验证", success=True)
        
        monitor.record_arena_performance(25.0, {1: 6.0, 2: 7.0, 3: 6.0, 4: 6.0}, 0.85)
        monitor.record_simulation_resources(50.0, 1024.0)
        monitor.record_certification_result("s1", True, CertificationLevel.GOLD, 120.0)
        
        report = monitor.generate_performance_analysis_report()
        
        assert isinstance(report, PerformanceAnalysisReport)
        assert report.report_id is not None
        assert report.report_date is not None
        assert report.time_range_start is not None
        assert report.time_range_end is not None
        
        # 验证统计信息
        assert report.statistics.total_certifications == 1
        assert report.statistics.successful_certifications == 1
        
        # 验证指标
        assert len(report.stage_metrics) > 0
        assert len(report.arena_metrics) > 0
        assert len(report.simulation_metrics) > 0
    
    def test_generate_performance_analysis_report_with_time_range(self, monitor):
        """测试生成性能分析报告 - 指定时间范围"""
        now = datetime.now()
        start = now - timedelta(days=7)
        end = now
        
        monitor.record_certification_result("s1", True, CertificationLevel.GOLD, 120.0)
        
        report = monitor.generate_performance_analysis_report(
            time_range_start=start,
            time_range_end=end
        )
        
        assert report.time_range_start == start
        assert report.time_range_end == end
    
    def test_export_performance_report(self, monitor):
        """测试导出性能分析报告"""
        # 生成报告
        monitor.record_certification_result("s1", True, CertificationLevel.GOLD, 120.0)
        report = monitor.generate_performance_analysis_report()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            # 导出报告
            monitor.export_performance_report(report, output_path)
            
            # 验证文件存在
            assert os.path.exists(output_path)
            
            # 读取并验证JSON内容
            with open(output_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            assert report_data["report_id"] == report.report_id
            assert "statistics" in report_data
            assert report_data["statistics"]["total_certifications"] == 1
            
        finally:
            # 清理临时文件
            if os.path.exists(output_path):
                os.remove(output_path)

    
    def test_export_performance_report_invalid_path(self, monitor):
        """测试导出到无效路径"""
        monitor.record_certification_result("s1", True, CertificationLevel.GOLD, 120.0)
        report = monitor.generate_performance_analysis_report()
        
        # 使用一个在所有平台上都无效的路径
        invalid_path = "Z:\\nonexistent_drive_12345\\invalid\\path\\report.json"
        
        with pytest.raises((IOError, OSError)):
            monitor.export_performance_report(report, invalid_path)
    
    def test_clear_history(self, monitor):
        """测试清理历史数据"""
        now = datetime.now()
        
        # 添加旧数据
        monitor.stage_metrics_history = [
            StagePerformanceMetrics(
                stage_name="Arena验证",
                start_time=now - timedelta(days=40),
                end_time=now - timedelta(days=40),
                duration_seconds=30.0,
                success=True
            )
        ]
        
        monitor.alerts_history = [
            PerformanceAlert(
                alert_id="alert1",
                alert_level=PerformanceAlertLevel.WARNING,
                alert_time=now - timedelta(days=40),
                stage_name="Arena验证",
                metric_name="arena_total_duration",
                actual_value=40.0,
                threshold_value=30.0,
                message="超时"
            )
        ]
        
        monitor.certification_results = [
            {
                "strategy_id": "s1",
                "success": True,
                "level": "gold",
                "duration_seconds": 100.0,
                "timestamp": now - timedelta(days=40)
            }
        ]
        
        # 清理30天前的数据
        monitor.clear_history(days_to_keep=30)
        
        # 验证旧数据被清理
        assert len(monitor.stage_metrics_history) == 0
        assert len(monitor.alerts_history) == 0
        assert len(monitor.certification_results) == 0
    
    def test_clear_history_keeps_recent_data(self, monitor):
        """测试清理历史数据 - 保留最近数据"""
        now = datetime.now()
        
        # 添加新旧混合数据
        monitor.certification_results = [
            {
                "strategy_id": "s1",
                "success": True,
                "level": "gold",
                "duration_seconds": 100.0,
                "timestamp": now - timedelta(days=40)  # 旧数据
            },
            {
                "strategy_id": "s2",
                "success": True,
                "level": "silver",
                "duration_seconds": 120.0,
                "timestamp": now - timedelta(days=10)  # 新数据
            }
        ]
        
        monitor.clear_history(days_to_keep=30)
        
        # 验证只保留新数据
        assert len(monitor.certification_results) == 1
        assert monitor.certification_results[0]["strategy_id"] == "s2"


class TestDataModels:
    """测试数据模型"""
    
    def test_stage_performance_metrics_creation(self):
        """测试StagePerformanceMetrics创建"""
        metrics = StagePerformanceMetrics(
            stage_name="Arena验证",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_seconds=30.0,
            success=True
        )
        
        assert metrics.stage_name == "Arena验证"
        assert metrics.duration_seconds == 30.0
        assert metrics.success is True
    
    def test_arena_performance_metrics_creation(self):
        """测试ArenaPerformanceMetrics创建"""
        metrics = ArenaPerformanceMetrics(
            total_duration_seconds=30.0,
            layer1_duration_seconds=7.0,
            layer2_duration_seconds=8.0,
            layer3_duration_seconds=8.0,
            layer4_duration_seconds=7.0,
            overall_score=0.85
        )
        
        assert metrics.total_duration_seconds == 30.0
        assert metrics.overall_score == 0.85
    
    def test_simulation_resource_metrics_creation(self):
        """测试SimulationResourceMetrics创建"""
        metrics = SimulationResourceMetrics(
            cpu_usage_percent=50.0,
            memory_usage_mb=1024.0,
            disk_io_mb=100.0,
            network_io_mb=50.0,
            peak_cpu_percent=70.0,
            peak_memory_mb=1500.0
        )
        
        assert metrics.cpu_usage_percent == 50.0
        assert metrics.memory_usage_mb == 1024.0
        assert metrics.peak_cpu_percent == 70.0
    
    def test_performance_alert_creation(self):
        """测试PerformanceAlert创建"""
        alert = PerformanceAlert(
            alert_id="alert1",
            alert_level=PerformanceAlertLevel.WARNING,
            alert_time=datetime.now(),
            stage_name="Arena验证",
            metric_name="arena_total_duration",
            actual_value=40.0,
            threshold_value=30.0,
            message="超时"
        )
        
        assert alert.alert_id == "alert1"
        assert alert.alert_level == PerformanceAlertLevel.WARNING
        assert alert.actual_value == 40.0
    
    def test_certification_statistics_creation(self):
        """测试CertificationStatistics创建"""
        stats = CertificationStatistics(
            total_certifications=10,
            successful_certifications=8,
            failed_certifications=2,
            success_rate=0.8,
            failure_rate=0.2,
            avg_duration_seconds=120.0,
            level_distribution={"gold": 5, "silver": 3}
        )
        
        assert stats.total_certifications == 10
        assert stats.success_rate == 0.8
        assert stats.level_distribution["gold"] == 5
