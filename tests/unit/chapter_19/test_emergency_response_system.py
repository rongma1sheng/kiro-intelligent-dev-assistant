"""应急响应系统单元测试

白皮书依据: 第十九章 19.3 应急响应流程
"""

import pytest
from datetime import datetime, timedelta

from src.risk.emergency_response_system import (
    EmergencyResponseSystem,
    AlertLevel,
    EmergencyProcedure
)


class TestEmergencyResponseSystem:
    """应急响应系统测试"""
    
    @pytest.fixture
    def system(self):
        """创建应急响应系统实例"""
        return EmergencyResponseSystem()
    
    def test_init_success(self):
        """测试初始化成功"""
        system = EmergencyResponseSystem()
        
        assert system.response_time_sla[AlertLevel.WARNING] == 30 * 60
        assert system.response_time_sla[AlertLevel.DANGER] == 5 * 60
        assert system.response_time_sla[AlertLevel.CRITICAL] == 0
        assert system.emergency_history == []
    
    def test_register_alert_handler(self, system):
        """测试注册告警处理器"""
        def handler(description, context):
            pass
        
        system.register_alert_handler(AlertLevel.CRITICAL, handler)
        
        assert len(system.alert_handlers[AlertLevel.CRITICAL]) == 1
    
    def test_register_alert_handler_invalid_level(self, system):
        """测试注册无效的告警级别"""
        def handler(description, context):
            pass
        
        with pytest.raises(ValueError, match="告警级别必须是AlertLevel枚举"):
            system.register_alert_handler("critical", handler)
    
    def test_register_alert_handler_invalid_handler(self, system):
        """测试注册无效的处理器"""
        with pytest.raises(ValueError, match="处理器必须是可调用对象"):
            system.register_alert_handler(AlertLevel.CRITICAL, "not_callable")
    
    def test_trigger_alert_warning(self, system):
        """测试触发WARNING级告警"""
        procedure = system.trigger_alert(
            alert_level=AlertLevel.WARNING,
            description="测试WARNING告警"
        )
        
        assert procedure is not None
        assert procedure.alert_level == AlertLevel.WARNING
        assert procedure.description == "测试WARNING告警"
        assert procedure.success is True
        assert len(system.emergency_history) == 1
    
    def test_trigger_alert_danger(self, system):
        """测试触发DANGER级告警"""
        procedure = system.trigger_alert(
            alert_level=AlertLevel.DANGER,
            description="测试DANGER告警"
        )
        
        assert procedure.alert_level == AlertLevel.DANGER
        assert "P1级告警" in str(procedure.actions)
    
    def test_trigger_alert_critical(self, system):
        """测试触发CRITICAL级告警"""
        procedure = system.trigger_alert(
            alert_level=AlertLevel.CRITICAL,
            description="测试CRITICAL告警"
        )
        
        assert procedure.alert_level == AlertLevel.CRITICAL
        assert "P0级告警" in str(procedure.actions)
    
    def test_trigger_alert_with_context(self, system):
        """测试带上下文的告警"""
        context = {'error_code': 500, 'component': 'redis'}
        
        procedure = system.trigger_alert(
            alert_level=AlertLevel.CRITICAL,
            description="Redis故障",
            context=context
        )
        
        assert procedure is not None
        assert procedure.success is True
    
    def test_trigger_alert_invalid_level(self, system):
        """测试无效的告警级别"""
        with pytest.raises(ValueError, match="告警级别必须是AlertLevel枚举"):
            system.trigger_alert(
                alert_level="critical",
                description="测试"
            )
    
    def test_trigger_alert_empty_description(self, system):
        """测试空描述"""
        with pytest.raises(ValueError, match="告警描述不能为空"):
            system.trigger_alert(
                alert_level=AlertLevel.WARNING,
                description=""
            )
    
    def test_trigger_alert_with_handler(self, system):
        """测试带处理器的告警"""
        handler_called = []
        
        def handler(description, context):
            handler_called.append(description)
        
        system.register_alert_handler(AlertLevel.CRITICAL, handler)
        
        system.trigger_alert(
            alert_level=AlertLevel.CRITICAL,
            description="测试处理器"
        )
        
        assert len(handler_called) == 1
        assert handler_called[0] == "测试处理器"
    
    def test_trigger_alert_handler_failure(self, system):
        """测试处理器失败"""
        def failing_handler(description, context):
            raise Exception("处理器失败")
        
        system.register_alert_handler(AlertLevel.CRITICAL, failing_handler)
        
        procedure = system.trigger_alert(
            alert_level=AlertLevel.CRITICAL,
            description="测试处理器失败"
        )
        
        # 即使处理器失败，应急程序也应该记录
        assert procedure is not None
        assert procedure.success is False
    
    def test_execute_emergency_procedure_stop_trading(self, system):
        """测试停止交易程序"""
        result = system.execute_emergency_procedure("stop_trading")
        assert result is True
    
    def test_execute_emergency_procedure_liquidate(self, system):
        """测试清仓程序"""
        result = system.execute_emergency_procedure("liquidate")
        assert result is True
    
    def test_execute_emergency_procedure_failover(self, system):
        """测试故障转移程序"""
        result = system.execute_emergency_procedure("failover")
        assert result is True
    
    def test_execute_emergency_procedure_recovery(self, system):
        """测试系统恢复程序"""
        result = system.execute_emergency_procedure("recovery")
        assert result is True
    
    def test_execute_emergency_procedure_invalid_type(self, system):
        """测试无效的程序类型"""
        with pytest.raises(ValueError, match="不支持的程序类型"):
            system.execute_emergency_procedure("invalid_type")
    
    def test_get_response_time_sla(self, system):
        """测试获取响应时间SLA"""
        assert system.get_response_time_sla(AlertLevel.WARNING) == 30 * 60
        assert system.get_response_time_sla(AlertLevel.DANGER) == 5 * 60
        assert system.get_response_time_sla(AlertLevel.CRITICAL) == 0
    
    def test_get_response_time_sla_invalid(self, system):
        """测试无效的告警级别"""
        with pytest.raises(ValueError, match="告警级别必须是AlertLevel枚举"):
            system.get_response_time_sla("warning")
    
    def test_get_emergency_history_all(self, system):
        """测试获取所有应急历史"""
        # 触发几个告警
        system.trigger_alert(AlertLevel.WARNING, "告警1")
        system.trigger_alert(AlertLevel.DANGER, "告警2")
        system.trigger_alert(AlertLevel.CRITICAL, "告警3")
        
        history = system.get_emergency_history()
        assert len(history) == 3
    
    def test_get_emergency_history_filtered_by_level(self, system):
        """测试按级别过滤历史"""
        system.trigger_alert(AlertLevel.WARNING, "告警1")
        system.trigger_alert(AlertLevel.DANGER, "告警2")
        system.trigger_alert(AlertLevel.CRITICAL, "告警3")
        
        critical_history = system.get_emergency_history(alert_level=AlertLevel.CRITICAL)
        assert len(critical_history) == 1
        assert critical_history[0].alert_level == AlertLevel.CRITICAL
    
    def test_get_emergency_history_filtered_by_time(self, system):
        """测试按时间过滤历史"""
        system.trigger_alert(AlertLevel.WARNING, "告警1")
        
        # 获取最近1小时的历史
        history = system.get_emergency_history(hours=1)
        assert len(history) == 1
    
    def test_get_emergency_history_invalid_hours(self, system):
        """测试无效的小时数"""
        with pytest.raises(ValueError, match="小时数必须 > 0"):
            system.get_emergency_history(hours=0)
    
    def test_get_emergency_history_invalid_level(self, system):
        """测试无效的告警级别"""
        with pytest.raises(ValueError, match="告警级别必须是AlertLevel枚举"):
            system.get_emergency_history(alert_level="warning")
    
    def test_get_statistics(self, system):
        """测试获取统计信息"""
        # 触发几个告警
        system.trigger_alert(AlertLevel.WARNING, "告警1")
        system.trigger_alert(AlertLevel.DANGER, "告警2")
        system.trigger_alert(AlertLevel.CRITICAL, "告警3")
        
        stats = system.get_statistics()
        
        assert stats['total_procedures'] == 3
        assert stats['success_count'] == 3
        assert stats['success_rate'] == 1.0
        assert stats['recent_24h'] == 3
        assert 'level_counts' in stats
        assert 'last_procedure' in stats
    
    def test_get_statistics_empty(self, system):
        """测试空历史的统计"""
        stats = system.get_statistics()
        
        assert stats['total_procedures'] == 0
        assert stats['success_count'] == 0
        assert stats['success_rate'] == 1.0
        assert stats['last_procedure'] is None
    
    def test_clear_old_history(self, system):
        """测试清理旧历史"""
        # 触发几个告警
        system.trigger_alert(AlertLevel.WARNING, "告警1")
        system.trigger_alert(AlertLevel.DANGER, "告警2")
        
        assert len(system.emergency_history) == 2
        
        # 清理（保留30天内的）
        system.clear_old_history(days=30)
        
        # 由于告警是刚创建的，应该都保留
        assert len(system.emergency_history) == 2
    
    def test_clear_old_history_invalid_days(self, system):
        """测试无效的保留天数"""
        with pytest.raises(ValueError, match="保留天数必须 > 0"):
            system.clear_old_history(days=0)
    
    def test_multiple_alerts_same_level(self, system):
        """测试同级别多个告警"""
        for i in range(5):
            system.trigger_alert(AlertLevel.WARNING, f"告警{i+1}")
        
        assert len(system.emergency_history) == 5
        
        warning_history = system.get_emergency_history(alert_level=AlertLevel.WARNING)
        assert len(warning_history) == 5
    
    def test_alert_procedure_id_unique(self, system):
        """测试告警程序ID唯一性"""
        proc1 = system.trigger_alert(AlertLevel.WARNING, "告警1")
        proc2 = system.trigger_alert(AlertLevel.WARNING, "告警2")
        
        assert proc1.procedure_id != proc2.procedure_id
