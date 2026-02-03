"""
服务管理器测试

白皮书依据: 第一章 1.1 服务启动管理
测试ServiceManager和各种服务的功能
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from src.chronos.services import (
    ServiceManager, ServiceType, ServiceStatus,
    SanitizerService, ExecutionService, AuditorService, RadarService
)


class TestServiceManager:
    """服务管理器测试"""
    
    @pytest.fixture
    def service_manager(self):
        """创建服务管理器实例"""
        return ServiceManager()
    
    def test_init(self, service_manager):
        """测试初始化"""
        assert len(service_manager.services) == 4
        assert ServiceType.SANITIZER in service_manager.services
        assert ServiceType.EXECUTION in service_manager.services
        assert ServiceType.AUDITOR in service_manager.services
        assert ServiceType.RADAR in service_manager.services
    
    @pytest.mark.asyncio
    async def test_start_service_success(self, service_manager):
        """测试启动服务成功"""
        # Mock服务启动
        service = service_manager.services[ServiceType.SANITIZER]
        service.start = AsyncMock(return_value=True)
        
        result = await service_manager.start_service(ServiceType.SANITIZER)
        
        assert result is True
        service.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_service_failure(self, service_manager):
        """测试启动服务失败"""
        # Mock服务启动失败
        service = service_manager.services[ServiceType.SANITIZER]
        service.start = AsyncMock(return_value=False)
        
        result = await service_manager.start_service(ServiceType.SANITIZER)
        
        assert result is False
        service.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_unknown_service(self, service_manager):
        """测试启动未知服务"""
        # 创建一个不存在的服务类型
        fake_service_type = Mock()
        fake_service_type.value = "fake_service"
        
        result = await service_manager.start_service(fake_service_type)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_stop_service_success(self, service_manager):
        """测试停止服务成功"""
        # Mock服务停止
        service = service_manager.services[ServiceType.SANITIZER]
        service.stop = AsyncMock(return_value=True)
        
        result = await service_manager.stop_service(ServiceType.SANITIZER)
        
        assert result is True
        service.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_all_services(self, service_manager):
        """测试启动所有服务"""
        # Mock所有服务启动
        for service in service_manager.services.values():
            service.start = AsyncMock(return_value=True)
        
        results = await service_manager.start_all_services()
        
        assert len(results) == 4
        assert all(results.values())
        
        # 验证所有服务都被调用
        for service in service_manager.services.values():
            service.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_all_services(self, service_manager):
        """测试停止所有服务"""
        # Mock所有服务停止
        for service in service_manager.services.values():
            service.stop = AsyncMock(return_value=True)
        
        results = await service_manager.stop_all_services()
        
        assert len(results) == 4
        assert all(results.values())
        
        # 验证所有服务都被调用
        for service in service_manager.services.values():
            service.stop.assert_called_once()
    
    def test_get_service_status(self, service_manager):
        """测试获取服务状态"""
        # Mock服务健康状态
        mock_status = {
            "service": "数据清洗服务",
            "status": "running",
            "uptime": 100
        }
        
        service = service_manager.services[ServiceType.SANITIZER]
        service.get_health_status = Mock(return_value=mock_status)
        
        status = service_manager.get_service_status(ServiceType.SANITIZER)
        
        assert status == mock_status
        service.get_health_status.assert_called_once()
    
    def test_get_all_services_status(self, service_manager):
        """测试获取所有服务状态"""
        # Mock所有服务状态
        for service_type, service in service_manager.services.items():
            mock_status = {
                "service": service_type.value,
                "status": "running"
            }
            service.get_health_status = Mock(return_value=mock_status)
        
        all_status = service_manager.get_all_services_status()
        
        assert len(all_status) == 4
        assert all(status["status"] == "running" for status in all_status.values())


class TestSanitizerService:
    """数据清洗服务测试"""
    
    @pytest.fixture
    def sanitizer_service(self):
        """创建数据清洗服务实例"""
        return SanitizerService()
    
    def test_init(self, sanitizer_service):
        """测试初始化"""
        assert sanitizer_service.service_type == ServiceType.SANITIZER
        assert sanitizer_service.status == ServiceStatus.STOPPED
        assert sanitizer_service.cleaning_queue_size == 0
        assert sanitizer_service.processed_count == 0
    
    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_start_success(self, mock_popen, sanitizer_service):
        """测试启动成功"""
        # Mock进程
        mock_process = Mock()
        mock_process.poll.return_value = None  # 进程正在运行
        mock_popen.return_value = mock_process
        
        result = await sanitizer_service.start()
        
        assert result is True
        assert sanitizer_service.status == ServiceStatus.RUNNING
        assert sanitizer_service.process == mock_process
        assert sanitizer_service.start_time is not None
    
    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_start_failure(self, mock_popen, sanitizer_service):
        """测试启动失败"""
        # Mock进程启动失败
        mock_process = Mock()
        mock_process.poll.return_value = 1  # 进程已退出
        mock_popen.return_value = mock_process
        
        result = await sanitizer_service.start()
        
        assert result is False
        assert sanitizer_service.status == ServiceStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, sanitizer_service):
        """测试启动已运行的服务"""
        sanitizer_service.status = ServiceStatus.RUNNING
        
        result = await sanitizer_service.start()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_stop_success(self, sanitizer_service):
        """测试停止成功"""
        # Mock进程
        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        
        sanitizer_service.process = mock_process
        sanitizer_service.status = ServiceStatus.RUNNING
        
        result = await sanitizer_service.stop()
        
        assert result is True
        assert sanitizer_service.status == ServiceStatus.STOPPED
        assert sanitizer_service.process is None
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_already_stopped(self, sanitizer_service):
        """测试停止已停止的服务"""
        result = await sanitizer_service.stop()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_stop_force_kill(self, sanitizer_service):
        """测试强制终止服务"""
        import subprocess
        
        # Mock进程
        mock_process = Mock()
        mock_process.terminate = Mock()
        # wait第一次抛出TimeoutExpired，第二次正常返回
        mock_process.wait = Mock(side_effect=[subprocess.TimeoutExpired(cmd="test", timeout=10), None])
        mock_process.kill = Mock()
        
        sanitizer_service.process = mock_process
        sanitizer_service.status = ServiceStatus.RUNNING
        
        result = await sanitizer_service.stop()
        
        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
    
    def test_get_health_status(self, sanitizer_service):
        """测试获取健康状态"""
        sanitizer_service.start_time = time.time() - 100
        sanitizer_service.cleaning_queue_size = 5
        sanitizer_service.processed_count = 100
        
        status = sanitizer_service.get_health_status()
        
        assert status["service"] == "数据清洗服务"
        assert status["status"] == "stopped"
        assert status["queue_size"] == 5
        assert status["processed_count"] == 100
        assert status["uptime"] >= 100
    
    @patch('psutil.Process')
    def test_get_metrics_success(self, mock_process_class, sanitizer_service):
        """测试获取服务指标成功"""
        # Mock进程和psutil
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process_instance = Mock()
        mock_process_instance.cpu_percent.return_value = 10.5
        mock_process_instance.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
        mock_process_class.return_value = mock_process_instance
        
        sanitizer_service.process = mock_process
        sanitizer_service.status = ServiceStatus.RUNNING
        sanitizer_service.start_time = time.time() - 100
        
        metrics = sanitizer_service.get_metrics()
        
        assert metrics is not None
        assert metrics.cpu_percent == 10.5
        assert metrics.memory_mb == 100.0
        assert metrics.uptime_seconds >= 100
        assert metrics.last_heartbeat > 0
    
    def test_get_metrics_not_running(self, sanitizer_service):
        """测试获取未运行服务的指标"""
        metrics = sanitizer_service.get_metrics()
        
        assert metrics is None


class TestExecutionService:
    """交易执行服务测试"""
    
    @pytest.fixture
    def execution_service(self):
        """创建交易执行服务实例"""
        return ExecutionService()
    
    def test_init(self, execution_service):
        """测试初始化"""
        assert execution_service.service_type == ServiceType.EXECUTION
        assert execution_service.status == ServiceStatus.STOPPED
        assert execution_service.orders_processed == 0
        assert execution_service.last_order_time is None
    
    def test_get_health_status(self, execution_service):
        """测试获取健康状态"""
        execution_service.orders_processed = 50
        execution_service.last_order_time = time.time()
        
        status = execution_service.get_health_status()
        
        assert status["service"] == "交易执行服务"
        assert status["orders_processed"] == 50
        assert status["last_order_time"] is not None


class TestAuditorService:
    """审计服务测试"""
    
    @pytest.fixture
    def auditor_service(self):
        """创建审计服务实例"""
        return AuditorService()
    
    def test_init(self, auditor_service):
        """测试初始化"""
        assert auditor_service.service_type == ServiceType.AUDITOR
        assert auditor_service.status == ServiceStatus.STOPPED
        assert auditor_service.audit_events == 0
        assert auditor_service.last_audit_time is None


class TestRadarService:
    """雷达服务测试"""
    
    @pytest.fixture
    def radar_service(self):
        """创建雷达服务实例"""
        return RadarService()
    
    def test_init(self, radar_service):
        """测试初始化"""
        assert radar_service.service_type == ServiceType.RADAR
        assert radar_service.status == ServiceStatus.STOPPED
        assert radar_service.signals_processed == 0
        assert radar_service.last_signal_time is None