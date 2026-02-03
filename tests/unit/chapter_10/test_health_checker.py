"""健康检查器单元测试

白皮书依据: 第十章 10.1 健康检查系统
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.core.health_checker import (
    HealthChecker,
    ComponentHealth,
    ComponentStatus,
    OverallStatus,
    HealthCheckResult
)


class TestHealthChecker:
    """HealthChecker单元测试"""
    
    def test_init_valid_parameters(self):
        """测试有效参数初始化"""
        checker = HealthChecker(
            redis_host="localhost",
            redis_port=6379,
            redis_timeout=5,
            check_interval=30
        )
        
        assert checker.redis_host == "localhost"
        assert checker.redis_port == 6379
        assert checker.redis_timeout == 5
        assert checker.check_interval == 30
    
    def test_init_invalid_timeout(self):
        """测试无效超时参数"""
        with pytest.raises(ValueError, match="Redis超时时间必须 > 0"):
            HealthChecker(redis_timeout=0)
        
        with pytest.raises(ValueError, match="Redis超时时间必须 > 0"):
            HealthChecker(redis_timeout=-1)
    
    def test_init_invalid_interval(self):
        """测试无效检查间隔"""
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            HealthChecker(check_interval=0)
        
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            HealthChecker(check_interval=-1)
    
    @patch('src.core.health_checker.redis')
    def test_check_redis_healthy(self, mock_redis_module):
        """测试Redis健康状态"""
        # Mock Redis客户端
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            'used_memory': 1024 * 1024 * 100,  # 100MB
            'connected_clients': 5
        }
        mock_redis_module.Redis.return_value = mock_client
        
        checker = HealthChecker()
        health = checker.check_redis()
        
        assert health.status == ComponentStatus.HEALTHY
        assert "Redis连接正常" in health.message
        assert "latency_ms" in health.metrics
        assert health.metrics["used_memory_mb"] == pytest.approx(100, rel=0.1)
        assert health.metrics["connected_clients"] == 5.0
    
    @patch('src.core.health_checker.redis')
    def test_check_redis_connection_error(self, mock_redis_module):
        """测试Redis连接错误"""
        # 定义ConnectionError异常类
        class MockConnectionError(Exception):
            pass
        
        mock_redis_module.ConnectionError = MockConnectionError
        
        # Mock Redis客户端抛出连接错误
        mock_client = Mock()
        mock_client.ping.side_effect = MockConnectionError("Connection refused")
        mock_redis_module.Redis.return_value = mock_client
        
        checker = HealthChecker()
        health = checker.check_redis()
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "Redis连接失败" in health.message
    
    @patch('src.core.health_checker.redis', None)
    def test_check_redis_module_not_installed(self):
        """测试Redis模块未安装"""
        checker = HealthChecker()
        health = checker.check_redis()
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "Redis库未安装" in health.message
    
    @patch('subprocess.run')
    def test_check_gpu_healthy(self, mock_run):
        """测试GPU健康状态"""
        # Mock rocm-smi成功输出
        mock_run.return_value = Mock(
            returncode=0,
            stdout="GPU memory info...",
            stderr=""
        )
        
        checker = HealthChecker()
        health = checker.check_gpu()
        
        assert health.status == ComponentStatus.HEALTHY
        assert "GPU状态正常" in health.message
        assert health.metrics["available"] == 1.0
    
    @patch('subprocess.run')
    def test_check_gpu_command_not_found(self, mock_run):
        """测试rocm-smi未安装"""
        mock_run.side_effect = FileNotFoundError()
        
        checker = HealthChecker()
        health = checker.check_gpu()
        
        assert health.status == ComponentStatus.DEGRADED
        assert "rocm-smi未安装" in health.message
    
    @patch('subprocess.run')
    def test_check_gpu_timeout(self, mock_run):
        """测试GPU检查超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("rocm-smi", 5)
        
        checker = HealthChecker()
        health = checker.check_gpu()
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "GPU检查超时" in health.message
    
    @patch('src.core.health_checker.redis')
    def test_attempt_redis_recovery_success_first_try(self, mock_redis_module):
        """测试Redis恢复成功（第1次尝试）"""
        # Mock Redis客户端
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            'used_memory': 1024 * 1024 * 100,
            'connected_clients': 5
        }
        mock_redis_module.Redis.return_value = mock_client
        
        checker = HealthChecker()
        
        start_time = time.time()
        result = checker.attempt_redis_recovery()
        elapsed = time.time() - start_time
        
        assert result is True
        # 第1次尝试等待1秒
        assert elapsed >= 1.0
        assert elapsed < 2.0
    
    @patch('src.core.health_checker.redis')
    def test_attempt_redis_recovery_success_second_try(self, mock_redis_module):
        """测试Redis恢复成功（第2次尝试）"""
        # 定义ConnectionError异常类
        class MockConnectionError(Exception):
            pass
        
        mock_redis_module.ConnectionError = MockConnectionError
        
        # Mock Redis客户端：第1次失败，第2次成功
        mock_client = Mock()
        
        # 第1次ping失败，第2次ping成功
        call_count = [0]
        def ping_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                raise MockConnectionError("First attempt fails")
            return True
        
        mock_client.ping.side_effect = ping_side_effect
        mock_client.info.return_value = {
            'used_memory': 1024 * 1024 * 100,
            'connected_clients': 5
        }
        mock_redis_module.Redis.return_value = mock_client
        
        checker = HealthChecker()
        
        start_time = time.time()
        result = checker.attempt_redis_recovery()
        elapsed = time.time() - start_time
        
        assert result is True
        # 第1次等待1秒 + 第2次等待2秒 = 3秒
        assert elapsed >= 3.0
        assert elapsed < 4.0
    
    @patch('src.core.health_checker.redis')
    def test_attempt_redis_recovery_all_failed(self, mock_redis_module):
        """测试Redis恢复全部失败"""
        # 定义ConnectionError异常类
        class MockConnectionError(Exception):
            pass
        
        mock_redis_module.ConnectionError = MockConnectionError
        
        # Mock Redis客户端：全部失败
        mock_client = Mock()
        mock_client.ping.side_effect = MockConnectionError("Always fails")
        mock_redis_module.Redis.return_value = mock_client
        
        checker = HealthChecker()
        
        start_time = time.time()
        result = checker.attempt_redis_recovery()
        elapsed = time.time() - start_time
        
        assert result is False
        # 1秒 + 2秒 + 4秒 = 7秒
        assert elapsed >= 7.0
        assert elapsed < 8.0
    
    @patch('socket.socket')
    def test_check_port_accessible(self, mock_socket):
        """测试端口可访问"""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # 连接成功
        mock_socket.return_value = mock_sock
        
        checker = HealthChecker()
        health = checker._check_port(8501, "Dashboard")
        
        assert health.status == ComponentStatus.HEALTHY
        assert "可访问" in health.message
        assert health.metrics["accessible"] == 1.0
    
    @patch('socket.socket')
    def test_check_port_not_accessible(self, mock_socket):
        """测试端口不可访问"""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1  # 连接失败
        mock_socket.return_value = mock_sock
        
        checker = HealthChecker()
        health = checker._check_port(8501, "Dashboard")
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "不可访问" in health.message
        assert health.metrics["accessible"] == 0.0
    
    @patch('shutil.disk_usage')
    def test_check_disk_space_healthy(self, mock_disk_usage):
        """测试磁盘空间充足"""
        # Mock磁盘使用：总1TB，已用500GB，剩余500GB（50%）
        mock_disk_usage.return_value = (
            1024**4,  # total: 1TB
            512 * 1024**3,  # used: 512GB
            512 * 1024**3  # free: 512GB
        )
        
        checker = HealthChecker()
        health = checker._check_disk_space()
        
        assert health.status == ComponentStatus.HEALTHY
        assert "磁盘空间充足" in health.message
        assert health.metrics["free_pct"] > 20
    
    @patch('shutil.disk_usage')
    def test_check_disk_space_degraded(self, mock_disk_usage):
        """测试磁盘空间偏低"""
        # Mock磁盘使用：总1TB，已用850GB，剩余150GB（15%）
        mock_disk_usage.return_value = (
            1024**4,  # total: 1TB
            850 * 1024**3,  # used: 850GB
            150 * 1024**3  # free: 150GB
        )
        
        checker = HealthChecker()
        health = checker._check_disk_space()
        
        assert health.status == ComponentStatus.DEGRADED
        assert "磁盘空间偏低" in health.message
        assert 10 < health.metrics["free_pct"] <= 20
    
    @patch('shutil.disk_usage')
    def test_check_disk_space_unhealthy(self, mock_disk_usage):
        """测试磁盘空间不足"""
        # Mock磁盘使用：总1TB，已用950GB，剩余50GB（5%）
        mock_disk_usage.return_value = (
            1024**4,  # total: 1TB
            950 * 1024**3,  # used: 950GB
            50 * 1024**3  # free: 50GB
        )
        
        checker = HealthChecker()
        health = checker._check_disk_space()
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "磁盘空间不足" in health.message
        assert health.metrics["free_pct"] <= 10
    
    @patch('psutil.virtual_memory')
    def test_check_memory_healthy(self, mock_memory):
        """测试内存使用正常"""
        mock_memory.return_value = Mock(
            total=16 * 1024**3,  # 16GB
            available=10 * 1024**3,  # 10GB可用
            percent=37.5  # 37.5%使用
        )
        
        checker = HealthChecker()
        health = checker._check_memory()
        
        assert health.status == ComponentStatus.HEALTHY
        assert "内存使用正常" in health.message
        assert health.metrics["used_pct"] < 80
    
    @patch('psutil.virtual_memory')
    def test_check_memory_degraded(self, mock_memory):
        """测试内存使用偏高"""
        mock_memory.return_value = Mock(
            total=16 * 1024**3,  # 16GB
            available=2 * 1024**3,  # 2GB可用
            percent=87.5  # 87.5%使用
        )
        
        checker = HealthChecker()
        health = checker._check_memory()
        
        assert health.status == ComponentStatus.DEGRADED
        assert "内存使用偏高" in health.message
        assert 80 <= health.metrics["used_pct"] < 90
    
    @patch('psutil.virtual_memory')
    def test_check_memory_unhealthy(self, mock_memory):
        """测试内存使用过高"""
        mock_memory.return_value = Mock(
            total=16 * 1024**3,  # 16GB
            available=0.5 * 1024**3,  # 0.5GB可用
            percent=96.9  # 96.9%使用
        )
        
        checker = HealthChecker()
        health = checker._check_memory()
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "内存使用过高" in health.message
        assert health.metrics["used_pct"] >= 90
    
    @patch('psutil.cpu_percent')
    def test_check_cpu_healthy(self, mock_cpu):
        """测试CPU使用正常"""
        mock_cpu.return_value = 45.0
        
        checker = HealthChecker()
        health = checker._check_cpu()
        
        assert health.status == ComponentStatus.HEALTHY
        assert "CPU使用正常" in health.message
        assert health.metrics["cpu_percent"] < 80
    
    @patch('psutil.cpu_percent')
    def test_check_cpu_degraded(self, mock_cpu):
        """测试CPU使用偏高"""
        mock_cpu.return_value = 85.0
        
        checker = HealthChecker()
        health = checker._check_cpu()
        
        assert health.status == ComponentStatus.DEGRADED
        assert "CPU使用偏高" in health.message
        assert 80 <= health.metrics["cpu_percent"] < 95
    
    @patch('psutil.cpu_percent')
    def test_check_cpu_unhealthy(self, mock_cpu):
        """测试CPU使用过高"""
        mock_cpu.return_value = 98.0
        
        checker = HealthChecker()
        health = checker._check_cpu()
        
        assert health.status == ComponentStatus.UNHEALTHY
        assert "CPU使用过高" in health.message
        assert health.metrics["cpu_percent"] >= 95
    
    def test_determine_overall_status_all_healthy(self):
        """测试所有组件健康时的整体状态"""
        checker = HealthChecker()
        
        components = {
            "redis": ComponentHealth(ComponentStatus.HEALTHY, "OK", {}),
            "disk": ComponentHealth(ComponentStatus.HEALTHY, "OK", {}),
            "memory": ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        }
        
        status = checker._determine_overall_status(components)
        assert status == OverallStatus.HEALTHY
    
    def test_determine_overall_status_has_degraded(self):
        """测试有组件降级时的整体状态"""
        checker = HealthChecker()
        
        components = {
            "redis": ComponentHealth(ComponentStatus.HEALTHY, "OK", {}),
            "disk": ComponentHealth(ComponentStatus.DEGRADED, "Low", {}),
            "memory": ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        }
        
        status = checker._determine_overall_status(components)
        assert status == OverallStatus.DEGRADED
    
    def test_determine_overall_status_has_unhealthy(self):
        """测试有组件不健康时的整体状态"""
        checker = HealthChecker()
        
        components = {
            "redis": ComponentHealth(ComponentStatus.UNHEALTHY, "Down", {}),
            "disk": ComponentHealth(ComponentStatus.HEALTHY, "OK", {}),
            "memory": ComponentHealth(ComponentStatus.DEGRADED, "High", {})
        }
        
        status = checker._determine_overall_status(components)
        assert status == OverallStatus.CRITICAL
    
    @patch('src.core.health_checker.HealthChecker.check_redis')
    @patch('src.core.health_checker.HealthChecker._check_port')
    @patch('src.core.health_checker.HealthChecker._check_disk_space')
    @patch('src.core.health_checker.HealthChecker._check_memory')
    @patch('src.core.health_checker.HealthChecker._check_cpu')
    @patch('src.core.health_checker.HealthChecker.check_gpu')
    def test_run_health_check_integration(
        self,
        mock_gpu,
        mock_cpu,
        mock_memory,
        mock_disk,
        mock_port,
        mock_redis
    ):
        """测试完整健康检查流程"""
        # Mock所有组件为健康状态
        mock_redis.return_value = ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        mock_port.return_value = ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        mock_disk.return_value = ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        mock_memory.return_value = ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        mock_cpu.return_value = ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        mock_gpu.return_value = ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        
        checker = HealthChecker()
        result = checker.run_health_check()
        
        assert isinstance(result, HealthCheckResult)
        assert result.overall_status == OverallStatus.HEALTHY
        assert "redis" in result.components
        assert "dashboard_8501" in result.components
        assert "dashboard_8502" in result.components
        assert "disk" in result.components
        assert "memory" in result.components
        assert "cpu" in result.components
        assert "gpu" in result.components
        assert isinstance(result.timestamp, datetime)


class TestComponentHealth:
    """ComponentHealth数据类测试"""
    
    def test_component_health_creation(self):
        """测试ComponentHealth创建"""
        health = ComponentHealth(
            status=ComponentStatus.HEALTHY,
            message="All good",
            metrics={"latency": 10.5}
        )
        
        assert health.status == ComponentStatus.HEALTHY
        assert health.message == "All good"
        assert health.metrics["latency"] == 10.5


class TestHealthCheckResult:
    """HealthCheckResult数据类测试"""
    
    def test_health_check_result_creation(self):
        """测试HealthCheckResult创建"""
        components = {
            "redis": ComponentHealth(ComponentStatus.HEALTHY, "OK", {})
        }
        
        result = HealthCheckResult(
            overall_status=OverallStatus.HEALTHY,
            components=components,
            timestamp=datetime.now()
        )
        
        assert result.overall_status == OverallStatus.HEALTHY
        assert "redis" in result.components
        assert isinstance(result.timestamp, datetime)



class TestHealthCheckerEdgeCases:
    """测试HealthChecker边界情况和异常处理
    
    这些测试覆盖health_checker.py中未被覆盖的异常处理路径，
    以达到100%测试覆盖率目标。
    """
    
    def test_check_redis_timeout_error(self, monkeypatch):
        """测试Redis超时错误处理
        
        覆盖: health_checker.py lines 230-242 (TimeoutError handling)
        """
        import sys
        import types
        
        # 创建mock redis模块
        mock_redis_module = types.ModuleType('redis')
        
        class TimeoutError(Exception):
            pass
        
        class ConnectionError(Exception):
            pass
        
        class MockRedis:
            def __init__(self, *args, **kwargs):
                pass
            
            def ping(self):
                raise TimeoutError("Connection timeout")
        
        mock_redis_module.Redis = MockRedis
        mock_redis_module.TimeoutError = TimeoutError
        mock_redis_module.ConnectionError = ConnectionError
        
        sys.modules['redis'] = mock_redis_module
        monkeypatch.setattr('src.core.health_checker.redis', mock_redis_module)
        
        checker = HealthChecker()
        result = checker.check_redis()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "超时" in result.message
    
    def test_check_redis_generic_exception(self, monkeypatch):
        """测试Redis通用异常处理
        
        覆盖: health_checker.py lines 244-252 (generic Exception handling)
        """
        import sys
        import types
        
        # 创建mock redis模块
        mock_redis_module = types.ModuleType('redis')
        
        class ConnectionError(Exception):
            pass
        
        class TimeoutError(Exception):
            pass
        
        class MockRedis:
            def __init__(self, *args, **kwargs):
                pass
            
            def ping(self):
                raise RuntimeError("Unexpected error")
        
        mock_redis_module.Redis = MockRedis
        mock_redis_module.ConnectionError = ConnectionError
        mock_redis_module.TimeoutError = TimeoutError
        
        sys.modules['redis'] = mock_redis_module
        monkeypatch.setattr('src.core.health_checker.redis', mock_redis_module)
        
        checker = HealthChecker()
        result = checker.check_redis()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "异常" in result.message
    
    def test_check_gpu_subprocess_error(self, monkeypatch):
        """测试GPU检查subprocess错误
        
        覆盖: health_checker.py lines 305-307 (generic Exception in check_gpu)
        """
        def mock_run(*args, **kwargs):
            raise OSError("Subprocess error")
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        checker = HealthChecker()
        result = checker.check_gpu()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "异常" in result.message
    
    def test_check_port_socket_exception(self, monkeypatch):
        """测试端口检查socket异常
        
        覆盖: health_checker.py lines 377-379 (Exception in _check_port)
        """
        import socket
        
        def mock_socket(*args, **kwargs):
            raise OSError("Socket error")
        
        monkeypatch.setattr('socket.socket', mock_socket)
        
        checker = HealthChecker()
        result = checker._check_port(8501, "Test")
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "异常" in result.message
    
    def test_check_disk_space_exception(self, monkeypatch):
        """测试磁盘检查异常
        
        覆盖: health_checker.py lines 422-424 (Exception in _check_disk_space)
        """
        def mock_disk_usage(*args):
            raise OSError("Disk error")
        
        import shutil
        monkeypatch.setattr('shutil.disk_usage', mock_disk_usage)
        
        checker = HealthChecker()
        result = checker._check_disk_space()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "异常" in result.message
    
    def test_check_memory_psutil_not_installed(self, monkeypatch):
        """测试内存检查psutil未安装
        
        覆盖: health_checker.py lines 464-468 (ImportError in _check_memory)
        """
        def selective_import(name, *args, **kwargs):
            if name == 'psutil':
                raise ImportError("psutil not installed")
            # 使用原始import处理其他模块
            import importlib
            return importlib.import_module(name)
        
        import builtins
        monkeypatch.setattr('builtins.__import__', selective_import)
        
        checker = HealthChecker()
        result = checker._check_memory()
        
        assert result.status == ComponentStatus.DEGRADED
        assert "psutil未安装" in result.message
    
    def test_check_memory_exception(self, monkeypatch):
        """测试内存检查异常
        
        覆盖: health_checker.py lines 470-473 (Exception in _check_memory)
        """
        import sys
        import types
        
        # 创建mock psutil模块
        mock_psutil = types.ModuleType('psutil')
        
        def mock_virtual_memory():
            raise RuntimeError("Memory error")
        
        mock_psutil.virtual_memory = mock_virtual_memory
        
        sys.modules['psutil'] = mock_psutil
        
        checker = HealthChecker()
        result = checker._check_memory()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "异常" in result.message
    
    def test_check_cpu_psutil_not_installed(self, monkeypatch):
        """测试CPU检查psutil未安装
        
        覆盖: health_checker.py lines 506-510 (ImportError in _check_cpu)
        """
        def selective_import(name, *args, **kwargs):
            if name == 'psutil':
                raise ImportError("psutil not installed")
            # 使用原始import处理其他模块
            import importlib
            return importlib.import_module(name)
        
        import builtins
        monkeypatch.setattr('builtins.__import__', selective_import)
        
        checker = HealthChecker()
        result = checker._check_cpu()
        
        assert result.status == ComponentStatus.DEGRADED
        assert "psutil未安装" in result.message
    
    def test_check_cpu_exception(self, monkeypatch):
        """测试CPU检查异常
        
        覆盖: health_checker.py lines 512-515 (Exception in _check_cpu)
        """
        import sys
        import types
        
        # 创建mock psutil模块
        mock_psutil = types.ModuleType('psutil')
        
        def mock_cpu_percent(*args, **kwargs):
            raise RuntimeError("CPU error")
        
        mock_psutil.cpu_percent = mock_cpu_percent
        
        sys.modules['psutil'] = mock_psutil
        
        checker = HealthChecker()
        result = checker._check_cpu()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "异常" in result.message


class TestHealthCheckerRemainingCoverage:
    """测试health_checker.py剩余未覆盖的代码路径"""
    
    def test_check_redis_ping_returns_false(self, monkeypatch):
        """测试Redis PING返回False的情况
        
        覆盖: health_checker.py line 215
        """
        import sys
        import types
        
        # 创建mock redis模块
        mock_redis_module = types.ModuleType('redis')
        
        class ConnectionError(Exception):
            pass
        
        class TimeoutError(Exception):
            pass
        
        class MockRedis:
            def __init__(self, *args, **kwargs):
                pass
            
            def ping(self):
                return False  # PING返回False
        
        mock_redis_module.Redis = MockRedis
        mock_redis_module.ConnectionError = ConnectionError
        mock_redis_module.TimeoutError = TimeoutError
        
        sys.modules['redis'] = mock_redis_module
        monkeypatch.setattr('src.core.health_checker.redis', mock_redis_module)
        
        checker = HealthChecker()
        result = checker.check_redis()
        
        assert result.status == ComponentStatus.UNHEALTHY
        assert "PING失败" in result.message
    
    def test_check_gpu_returncode_zero_empty_output(self, monkeypatch):
        """测试GPU检查返回零退出码但输出为空
        
        覆盖: health_checker.py line 277-280 (empty output branch)
        """
        import subprocess
        from unittest.mock import Mock
        
        mock_result = Mock()
        mock_result.returncode = 0  # 成功退出
        mock_result.stdout = ""  # 但输出为空
        mock_result.stderr = ""
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        checker = HealthChecker()
        result = checker.check_gpu()
        
        # 验证返回DEGRADED状态
        assert result.status == ComponentStatus.DEGRADED
        assert "GPU信息为空" in result.message
    
    def test_check_gpu_returncode_nonzero_with_stderr(self, monkeypatch):
        """测试GPU检查返回非零退出码且有stderr
        
        覆盖: health_checker.py line 283-285 (returncode != 0 branch)
        """
        import subprocess
        from unittest.mock import Mock
        
        mock_result = Mock()
        mock_result.returncode = 1  # 非零退出码
        mock_result.stdout = ""
        mock_result.stderr = "GPU error occurred"  # 有stderr输出
        
        def mock_run(*args, **kwargs):
            return mock_result
        
        monkeypatch.setattr('subprocess.run', mock_run)
        
        checker = HealthChecker()
        result = checker.check_gpu()
        
        # 验证返回UNHEALTHY状态且消息包含stderr
        assert result.status == ComponentStatus.UNHEALTHY
        assert "执行失败" in result.message
        assert "GPU error occurred" in result.message
