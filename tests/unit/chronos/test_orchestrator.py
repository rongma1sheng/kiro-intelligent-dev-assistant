"""
五态状态机（Main Orchestrator）单元测试

白皮书依据: 第一章 1.0-1.4 柯罗诺斯生物钟与资源调度
测试覆盖率目标: ≥ 90%
"""

import pytest
import time
from datetime import datetime, time as dt_time
from unittest.mock import Mock, patch, MagicMock
from enum import Enum

from src.chronos.orchestrator import (
    SystemState,
    MainOrchestrator,
    StateTransitionError,
    ServiceStartupError,
)


class TestSystemState:
    """测试系统状态枚举
    
    白皮书依据: 第一章 1.0-1.4 五态定义
    """
    
    def test_system_state_values(self):
        """测试系统状态枚举值"""
        assert SystemState.MAINTENANCE.value == 0
        assert SystemState.PREP.value == 1
        assert SystemState.WAR.value == 2
        assert SystemState.TACTICAL.value == 3
        assert SystemState.EVOLUTION.value == 4
    
    def test_system_state_completeness(self):
        """测试系统状态枚举完整性"""
        states = list(SystemState)
        assert len(states) == 5
        assert SystemState.MAINTENANCE in states
        assert SystemState.PREP in states
        assert SystemState.WAR in states
        assert SystemState.TACTICAL in states
        assert SystemState.EVOLUTION in states


class TestMainOrchestrator:
    """测试主调度器
    
    白皮书依据: 第一章 柯罗诺斯生物钟
    """
    
    @pytest.fixture
    def orchestrator(self):
        """创建测试用的调度器实例"""
        return MainOrchestrator()
    
    def test_orchestrator_initialization(self, orchestrator):
        """测试调度器初始化
        
        验证:
        - 初始状态为MAINTENANCE
        - 所有服务未启动
        - 调度器未运行
        """
        assert orchestrator.current_state == SystemState.MAINTENANCE
        assert not orchestrator.is_running
        assert orchestrator.services == {}
    
    def test_orchestrator_initialization_with_config(self):
        """测试带配置的调度器初始化"""
        config = {
            'prep_time': '08:30',
            'war_time': '09:15',
            'tactical_time': '15:00',
            'evolution_time': '20:00',
        }
        orchestrator = MainOrchestrator(config=config)
        assert orchestrator.config == config
    
    def test_get_current_state(self, orchestrator):
        """测试获取当前状态"""
        assert orchestrator.get_current_state() == SystemState.MAINTENANCE
    
    @patch.object(MainOrchestrator, 'is_trading_day', return_value=True)
    def test_transition_to_prep_state(self, mock_is_trading_day, orchestrator):
        """测试转换到战备态
        
        白皮书依据: 第一章 1.1 State 1: 战备态
        """
        orchestrator.transition_to(SystemState.PREP)
        assert orchestrator.current_state == SystemState.PREP
    
    def test_transition_to_war_state(self, orchestrator):
        """测试转换到战争态
        
        白皮书依据: 第一章 1.2 State 2: 战争态
        """
        orchestrator.transition_to(SystemState.PREP)
        orchestrator.transition_to(SystemState.WAR)
        assert orchestrator.current_state == SystemState.WAR
    
    def test_transition_to_tactical_state(self, orchestrator):
        """测试转换到诊疗态
        
        白皮书依据: 第一章 1.3 State 3: 诊疗态
        """
        orchestrator.transition_to(SystemState.TACTICAL)
        assert orchestrator.current_state == SystemState.TACTICAL
    
    def test_transition_to_evolution_state(self, orchestrator):
        """测试转换到进化态
        
        白皮书依据: 第一章 1.4 State 4: 进化态
        """
        orchestrator.transition_to(SystemState.EVOLUTION)
        assert orchestrator.current_state == SystemState.EVOLUTION
    
    def test_invalid_state_transition(self, orchestrator):
        """测试无效的状态转换"""
        with pytest.raises(StateTransitionError):
            orchestrator.transition_to("INVALID_STATE")
    
    @patch.object(MainOrchestrator, 'is_trading_day', return_value=True)
    def test_state_transition_callback(self, mock_is_trading_day, orchestrator):
        """测试状态转换回调"""
        callback_called = []
        
        def on_state_change(old_state, new_state):
            callback_called.append((old_state, new_state))
        
        orchestrator.on_state_change = on_state_change
        orchestrator.transition_to(SystemState.PREP)
        
        assert len(callback_called) == 1
        assert callback_called[0] == (SystemState.MAINTENANCE, SystemState.PREP)
    
    @patch('src.chronos.orchestrator.datetime')
    def test_is_trading_day(self, mock_datetime, orchestrator):
        """测试交易日判断
        
        白皮书依据: 第一章 1.1 日历感知
        """
        # 模拟工作日
        mock_datetime.now.return_value = datetime(2026, 1, 20)  # 星期二
        assert orchestrator.is_trading_day() is True
        
        # 模拟周末
        mock_datetime.now.return_value = datetime(2026, 1, 18)  # 星期日
        assert orchestrator.is_trading_day() is False
    
    @patch('src.chronos.orchestrator.datetime')
    def test_get_target_state_by_time(self, mock_datetime, orchestrator):
        """测试根据时间获取目标状态
        
        白皮书依据: 第一章 1.1-1.4 时间段定义
        """
        # 08:30 - 09:15: PREP
        mock_datetime.now.return_value.time.return_value = dt_time(8, 30)
        assert orchestrator.get_target_state_by_time() == SystemState.PREP
        
        # 09:15 - 15:00: WAR
        mock_datetime.now.return_value.time.return_value = dt_time(10, 0)
        assert orchestrator.get_target_state_by_time() == SystemState.WAR
        
        # 15:00 - 20:00: TACTICAL
        mock_datetime.now.return_value.time.return_value = dt_time(16, 0)
        assert orchestrator.get_target_state_by_time() == SystemState.TACTICAL
        
        # 20:00 - 08:30: EVOLUTION
        mock_datetime.now.return_value.time.return_value = dt_time(22, 0)
        assert orchestrator.get_target_state_by_time() == SystemState.EVOLUTION
    
    def test_start_service(self, orchestrator):
        """测试启动服务
        
        白皮书依据: 第一章 1.1 服务启动
        """
        mock_service = Mock()
        orchestrator.register_service('test_service', mock_service)
        orchestrator.start_service('test_service')
        
        mock_service.start.assert_called_once()
        assert orchestrator.services['test_service'].status == 'running'
    
    def test_stop_service(self, orchestrator):
        """测试停止服务"""
        mock_service = Mock()
        orchestrator.register_service('test_service', mock_service)
        orchestrator.start_service('test_service')
        orchestrator.stop_service('test_service')
        
        mock_service.stop.assert_called_once()
        assert orchestrator.services['test_service'].status == 'stopped'
    
    def test_start_nonexistent_service(self, orchestrator):
        """测试启动不存在的服务"""
        with pytest.raises(ServiceStartupError):
            orchestrator.start_service('nonexistent_service')
    
    def test_register_service(self, orchestrator):
        """测试注册服务"""
        mock_service = Mock()
        orchestrator.register_service('test_service', mock_service)
        
        assert 'test_service' in orchestrator.services
        assert orchestrator.services['test_service'].instance == mock_service
    
    def test_unregister_service(self, orchestrator):
        """测试注销服务"""
        mock_service = Mock()
        orchestrator.register_service('test_service', mock_service)
        orchestrator.unregister_service('test_service')
        
        assert 'test_service' not in orchestrator.services
    
    def test_get_service_status(self, orchestrator):
        """测试获取服务状态"""
        mock_service = Mock()
        orchestrator.register_service('test_service', mock_service)
        
        status = orchestrator.get_service_status('test_service')
        assert status == 'stopped'
        
        orchestrator.start_service('test_service')
        status = orchestrator.get_service_status('test_service')
        assert status == 'running'
    
    def test_start_orchestrator(self, orchestrator):
        """测试启动调度器"""
        orchestrator.start()
        assert orchestrator.is_running is True
    
    def test_stop_orchestrator(self, orchestrator):
        """测试停止调度器"""
        orchestrator.start()
        orchestrator.stop()
        assert orchestrator.is_running is False
    
    def test_orchestrator_already_running(self, orchestrator):
        """测试重复启动调度器"""
        orchestrator.start()
        with pytest.raises(RuntimeError, match="Orchestrator is already running"):
            orchestrator.start()
    
    def test_orchestrator_not_running(self, orchestrator):
        """测试停止未运行的调度器"""
        with pytest.raises(RuntimeError, match="Orchestrator is not running"):
            orchestrator.stop()


class TestStateTransitions:
    """测试状态转换逻辑
    
    白皮书依据: 第一章 状态转换规则
    """
    
    @pytest.fixture
    def orchestrator(self):
        """创建测试用的调度器实例"""
        return MainOrchestrator()
    
    @patch.object(MainOrchestrator, 'is_trading_day', return_value=True)
    def test_maintenance_to_prep_transition(self, mock_is_trading_day, orchestrator):
        """测试从维护态到战备态的转换"""
        orchestrator.transition_to(SystemState.PREP)
        assert orchestrator.current_state == SystemState.PREP
    
    def test_prep_to_war_transition(self, orchestrator):
        """测试从战备态到战争态的转换"""
        orchestrator.transition_to(SystemState.PREP)
        orchestrator.transition_to(SystemState.WAR)
        assert orchestrator.current_state == SystemState.WAR
    
    def test_war_to_tactical_transition(self, orchestrator):
        """测试从战争态到诊疗态的转换"""
        orchestrator.transition_to(SystemState.WAR)
        orchestrator.transition_to(SystemState.TACTICAL)
        assert orchestrator.current_state == SystemState.TACTICAL
    
    def test_tactical_to_evolution_transition(self, orchestrator):
        """测试从诊疗态到进化态的转换"""
        orchestrator.transition_to(SystemState.TACTICAL)
        orchestrator.transition_to(SystemState.EVOLUTION)
        assert orchestrator.current_state == SystemState.EVOLUTION
    
    @patch.object(MainOrchestrator, 'is_trading_day', return_value=True)
    def test_evolution_to_prep_transition(self, mock_is_trading_day, orchestrator):
        """测试从进化态到战备态的转换（新的一天）"""
        orchestrator.transition_to(SystemState.EVOLUTION)
        orchestrator.transition_to(SystemState.PREP)
        assert orchestrator.current_state == SystemState.PREP
    
    def test_any_state_to_maintenance_transition(self, orchestrator):
        """测试任何状态都可以转换到维护态（紧急情况）"""
        orchestrator.transition_to(SystemState.WAR)
        orchestrator.transition_to(SystemState.MAINTENANCE)
        assert orchestrator.current_state == SystemState.MAINTENANCE
    
    @patch.object(MainOrchestrator, 'is_trading_day', return_value=True)
    def test_state_transition_history(self, mock_is_trading_day, orchestrator):
        """测试状态转换历史记录"""
        orchestrator.transition_to(SystemState.PREP)
        orchestrator.transition_to(SystemState.WAR)
        orchestrator.transition_to(SystemState.TACTICAL)
        
        history = orchestrator.get_state_history()
        assert len(history) >= 4  # MAINTENANCE + PREP + WAR + TACTICAL
        # Find the indices of the states we care about
        state_sequence = [h[1] for h in history]
        assert SystemState.PREP in state_sequence
        assert SystemState.WAR in state_sequence
        assert SystemState.TACTICAL in state_sequence
        # Verify order
        prep_idx = state_sequence.index(SystemState.PREP)
        war_idx = state_sequence.index(SystemState.WAR)
        tactical_idx = state_sequence.index(SystemState.TACTICAL)
        assert prep_idx < war_idx < tactical_idx


class TestServiceManagement:
    """测试服务管理
    
    白皮书依据: 第一章 1.1 服务启动管理
    """
    
    @pytest.fixture
    def orchestrator(self):
        """创建测试用的调度器实例"""
        return MainOrchestrator()
    
    def test_start_all_services(self, orchestrator):
        """测试启动所有服务"""
        mock_service1 = Mock()
        mock_service2 = Mock()
        
        orchestrator.register_service('service1', mock_service1)
        orchestrator.register_service('service2', mock_service2)
        
        orchestrator.start_all_services()
        
        mock_service1.start.assert_called_once()
        mock_service2.start.assert_called_once()
    
    def test_stop_all_services(self, orchestrator):
        """测试停止所有服务"""
        mock_service1 = Mock()
        mock_service2 = Mock()
        
        orchestrator.register_service('service1', mock_service1)
        orchestrator.register_service('service2', mock_service2)
        
        orchestrator.start_all_services()
        orchestrator.stop_all_services()
        
        mock_service1.stop.assert_called_once()
        mock_service2.stop.assert_called_once()
    
    def test_service_startup_failure(self, orchestrator):
        """测试服务启动失败"""
        mock_service = Mock()
        mock_service.start.side_effect = Exception("Startup failed")
        
        orchestrator.register_service('failing_service', mock_service)
        
        with pytest.raises(ServiceStartupError):
            orchestrator.start_service('failing_service')
    
    def test_service_health_check(self, orchestrator):
        """测试服务健康检查"""
        mock_service = Mock()
        mock_service.is_healthy.return_value = True
        
        orchestrator.register_service('test_service', mock_service)
        orchestrator.start_service('test_service')
        
        assert orchestrator.check_service_health('test_service') is True
    
    def test_service_restart(self, orchestrator):
        """测试服务重启"""
        mock_service = Mock()
        
        orchestrator.register_service('test_service', mock_service)
        orchestrator.start_service('test_service')
        orchestrator.restart_service('test_service')
        
        assert mock_service.stop.call_count == 1
        assert mock_service.start.call_count == 2  # 初始启动 + 重启


class TestIntegration:
    """集成测试
    
    白皮书依据: 第一章 完整工作流
    """
    
    @pytest.fixture
    def orchestrator(self):
        """创建测试用的调度器实例"""
        return MainOrchestrator()
    
    @patch('src.chronos.orchestrator.datetime')
    def test_full_day_cycle(self, mock_datetime, orchestrator):
        """测试完整的一天周期
        
        验证:
        - PREP (08:30) -> WAR (09:15) -> TACTICAL (15:00) -> EVOLUTION (20:00)
        """
        # 08:30: PREP
        mock_datetime.now.return_value.time.return_value = dt_time(8, 30)
        target_state = orchestrator.get_target_state_by_time()
        assert target_state == SystemState.PREP
        
        # 09:15: WAR
        mock_datetime.now.return_value.time.return_value = dt_time(9, 15)
        target_state = orchestrator.get_target_state_by_time()
        assert target_state == SystemState.WAR
        
        # 15:00: TACTICAL
        mock_datetime.now.return_value.time.return_value = dt_time(15, 0)
        target_state = orchestrator.get_target_state_by_time()
        assert target_state == SystemState.TACTICAL
        
        # 20:00: EVOLUTION
        mock_datetime.now.return_value.time.return_value = dt_time(20, 0)
        target_state = orchestrator.get_target_state_by_time()
        assert target_state == SystemState.EVOLUTION
    
    def test_service_lifecycle_management(self, orchestrator):
        """测试服务生命周期管理"""
        mock_service = Mock()
        
        # 注册服务
        orchestrator.register_service('test_service', mock_service)
        assert 'test_service' in orchestrator.services
        
        # 启动服务
        orchestrator.start_service('test_service')
        assert orchestrator.get_service_status('test_service') == 'running'
        
        # 停止服务
        orchestrator.stop_service('test_service')
        assert orchestrator.get_service_status('test_service') == 'stopped'
        
        # 注销服务
        orchestrator.unregister_service('test_service')
        assert 'test_service' not in orchestrator.services
