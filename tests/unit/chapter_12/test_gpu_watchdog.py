"""GPUWatchdog单元测试

白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

测试覆盖:
- 初始化验证
- GPU健康检查
- 碎片化检测
- 驱动热重载
- 状态管理
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock

from src.core.gpu_watchdog import (
    GPUWatchdog,
    GPUHealthStatus,
    GPUHealthMetrics
)


class TestGPUHealthStatus:
    """GPUHealthStatus枚举测试"""
    
    def test_status_values(self):
        """测试状态枚举值"""
        assert GPUHealthStatus.HEALTHY.value == "healthy"
        assert GPUHealthStatus.DEGRADED.value == "degraded"
        assert GPUHealthStatus.UNHEALTHY.value == "unhealthy"
        assert GPUHealthStatus.UNAVAILABLE.value == "unavailable"


class TestGPUHealthMetrics:
    """GPUHealthMetrics数据类测试"""
    
    def test_metrics_creation(self):
        """测试指标创建"""
        metrics = GPUHealthMetrics(
            memory_used_mb=8192.0,
            memory_total_mb=32768.0,
            memory_free_mb=24576.0,
            fragmentation_ratio=0.15
        )
        
        assert metrics.memory_used_mb == 8192.0
        assert metrics.memory_total_mb == 32768.0
        assert metrics.memory_free_mb == 24576.0
        assert metrics.fragmentation_ratio == 0.15
        assert metrics.is_healthy is True
    
    def test_metrics_with_optional_fields(self):
        """测试带可选字段的指标"""
        metrics = GPUHealthMetrics(
            memory_used_mb=8192.0,
            memory_total_mb=32768.0,
            memory_free_mb=24576.0,
            fragmentation_ratio=0.15,
            temperature_celsius=65.0,
            utilization_percent=80.0,
            is_healthy=False
        )
        
        assert metrics.temperature_celsius == 65.0
        assert metrics.utilization_percent == 80.0
        assert metrics.is_healthy is False


class TestGPUWatchdogInit:
    """GPUWatchdog初始化测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        watchdog = GPUWatchdog()
        
        assert watchdog.redis is None
        assert watchdog.check_interval == 30
        assert watchdog.fragmentation_threshold == 0.3
        assert watchdog.failure_threshold == 3
        assert watchdog.status == GPUHealthStatus.HEALTHY
        assert watchdog.metrics is None
        assert watchdog.failure_count == 0
    
    def test_init_with_redis(self):
        """测试带Redis客户端初始化"""
        mock_redis = Mock()
        watchdog = GPUWatchdog(redis_client=mock_redis)
        
        assert watchdog.redis is mock_redis
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        watchdog = GPUWatchdog(
            check_interval=60,
            fragmentation_threshold=0.5,
            failure_threshold=5
        )
        
        assert watchdog.check_interval == 60
        assert watchdog.fragmentation_threshold == 0.5
        assert watchdog.failure_threshold == 5
    
    def test_init_invalid_check_interval(self):
        """测试无效的检查间隔"""
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            GPUWatchdog(check_interval=0)
    
    def test_init_invalid_fragmentation_threshold_low(self):
        """测试无效的碎片化阈值（过低）"""
        with pytest.raises(ValueError, match="碎片化阈值必须在"):
            GPUWatchdog(fragmentation_threshold=0)
    
    def test_init_invalid_fragmentation_threshold_high(self):
        """测试无效的碎片化阈值（过高）"""
        with pytest.raises(ValueError, match="碎片化阈值必须在"):
            GPUWatchdog(fragmentation_threshold=1.0)
    
    def test_init_invalid_failure_threshold(self):
        """测试无效的失败阈值"""
        with pytest.raises(ValueError, match="失败阈值必须 > 0"):
            GPUWatchdog(failure_threshold=0)


class TestGPUWatchdogCheckHealth:
    """GPUWatchdog健康检查测试"""
    
    @pytest.fixture
    def watchdog(self):
        """创建测试用看门狗"""
        return GPUWatchdog()
    
    def test_check_gpu_health_success(self, watchdog):
        """测试健康检查成功"""
        mock_output = """
GPU[0]		: VRAM Total Memory (B): 34359738368
GPU[0]		: VRAM Total Used Memory (B): 8589934592
        """
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        
        with patch('subprocess.run', return_value=mock_result):
            result = watchdog.check_gpu_health()
        
        assert result is True
        assert watchdog.status == GPUHealthStatus.HEALTHY
        assert watchdog.metrics is not None
        assert watchdog.failure_count == 0
    
    def test_check_gpu_health_high_fragmentation(self, watchdog):
        """测试高碎片化检测"""
        # 设置较低的阈值以触发高碎片化
        watchdog.fragmentation_threshold = 0.1
        
        mock_output = """
GPU[0]		: VRAM Total Memory (B): 34359738368
GPU[0]		: VRAM Total Used Memory (B): 17179869184
        """
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        
        with patch('subprocess.run', return_value=mock_result):
            result = watchdog.check_gpu_health()
        
        assert result is False
        assert watchdog.metrics is not None
        assert watchdog.metrics.is_healthy is False
    
    def test_check_gpu_health_command_failure(self, watchdog):
        """测试命令执行失败"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error"
        
        with patch('subprocess.run', return_value=mock_result):
            result = watchdog.check_gpu_health()
        
        assert result is False
        assert watchdog.failure_count == 1
    
    def test_check_gpu_health_timeout(self, watchdog):
        """测试命令超时"""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('rocm-smi', 5)):
            result = watchdog.check_gpu_health()
        
        assert result is False
        assert watchdog.failure_count == 1
    
    def test_check_gpu_health_not_found(self, watchdog):
        """测试rocm-smi未找到"""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = watchdog.check_gpu_health()
        
        assert result is False
        assert watchdog.status == GPUHealthStatus.UNAVAILABLE
    
    def test_check_gpu_health_parse_failure(self, watchdog):
        """测试解析失败"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Invalid output"
        
        with patch('subprocess.run', return_value=mock_result):
            result = watchdog.check_gpu_health()
        
        assert result is False
        assert watchdog.failure_count == 1


class TestGPUWatchdogFragmentation:
    """GPUWatchdog碎片化检测测试"""
    
    def test_detect_fragmentation_no_metrics(self):
        """测试无指标时的碎片化检测"""
        watchdog = GPUWatchdog()
        watchdog.metrics = None
        
        # Mock check_gpu_health to return False
        with patch.object(watchdog, 'check_gpu_health', return_value=False):
            result = watchdog.detect_fragmentation()
        
        assert result == -1.0
    
    def test_detect_fragmentation_with_metrics(self):
        """测试有指标时的碎片化检测"""
        watchdog = GPUWatchdog()
        watchdog.metrics = GPUHealthMetrics(
            memory_used_mb=8192.0,
            memory_total_mb=32768.0,
            memory_free_mb=24576.0,
            fragmentation_ratio=0.25
        )
        
        result = watchdog.detect_fragmentation()
        
        assert result == 0.25


class TestGPUWatchdogDriverReload:
    """GPUWatchdog驱动热重载测试"""
    
    @pytest.fixture
    def watchdog(self):
        """创建测试用看门狗"""
        mock_redis = Mock()
        return GPUWatchdog(redis_client=mock_redis)
    
    def test_trigger_driver_reload_success(self, watchdog):
        """测试驱动重载成功"""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            with patch.object(watchdog, 'check_gpu_health', return_value=True):
                with patch('time.sleep'):
                    result = watchdog.trigger_driver_reload()
        
        assert result is True
        watchdog.redis.set.assert_called()
    
    def test_trigger_driver_reload_failure(self, watchdog):
        """测试驱动重载失败"""
        mock_result = Mock()
        mock_result.returncode = 0
        
        with patch('subprocess.run', return_value=mock_result):
            with patch.object(watchdog, 'check_gpu_health', return_value=False):
                with patch('time.sleep'):
                    result = watchdog.trigger_driver_reload()
        
        assert result is False
    
    def test_trigger_driver_reload_timeout(self, watchdog):
        """测试驱动重载超时"""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('rocm-smi', 90)):
            result = watchdog.trigger_driver_reload()
        
        assert result is False
    
    def test_trigger_driver_reload_not_found(self, watchdog):
        """测试rocm-smi未找到"""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = watchdog.trigger_driver_reload()
        
        assert result is False


class TestGPUWatchdogStartStop:
    """GPUWatchdog启动停止测试"""
    
    def test_start(self):
        """测试启动看门狗"""
        watchdog = GPUWatchdog()
        
        watchdog.start()
        
        assert watchdog._running is True
        assert watchdog._thread is not None
        assert watchdog._thread.is_alive()
        
        # 清理
        watchdog.stop()
    
    def test_start_already_running(self):
        """测试重复启动"""
        watchdog = GPUWatchdog()
        watchdog.start()
        
        with pytest.raises(RuntimeError, match="GPU看门狗已经在运行"):
            watchdog.start()
        
        # 清理
        watchdog.stop()
    
    def test_stop(self):
        """测试停止看门狗"""
        watchdog = GPUWatchdog()
        watchdog.start()
        
        watchdog.stop()
        
        assert watchdog._running is False
    
    def test_stop_not_running(self):
        """测试停止未运行的看门狗"""
        watchdog = GPUWatchdog()
        
        # 不应抛出异常
        watchdog.stop()
        
        assert watchdog._running is False


class TestGPUWatchdogGetters:
    """GPUWatchdog getter方法测试"""
    
    def test_get_status(self):
        """测试获取状态"""
        watchdog = GPUWatchdog()
        watchdog.status = GPUHealthStatus.DEGRADED
        
        assert watchdog.get_status() == GPUHealthStatus.DEGRADED
    
    def test_get_metrics(self):
        """测试获取指标"""
        watchdog = GPUWatchdog()
        metrics = GPUHealthMetrics(
            memory_used_mb=8192.0,
            memory_total_mb=32768.0,
            memory_free_mb=24576.0,
            fragmentation_ratio=0.15
        )
        watchdog.metrics = metrics
        
        assert watchdog.get_metrics() is metrics
    
    def test_get_metrics_none(self):
        """测试获取空指标"""
        watchdog = GPUWatchdog()
        
        assert watchdog.get_metrics() is None
    
    def test_get_failure_count(self):
        """测试获取失败计数"""
        watchdog = GPUWatchdog()
        watchdog.failure_count = 5
        
        assert watchdog.get_failure_count() == 5


class TestGPUWatchdogHandleFailure:
    """GPUWatchdog失败处理测试"""
    
    def test_handle_failure_below_threshold(self):
        """测试失败次数低于阈值"""
        mock_redis = Mock()
        watchdog = GPUWatchdog(redis_client=mock_redis, failure_threshold=3)
        watchdog.failure_count = 0
        
        watchdog._handle_failure()
        
        assert watchdog.failure_count == 1
        assert watchdog.status == GPUHealthStatus.DEGRADED
    
    def test_handle_failure_at_threshold(self):
        """测试失败次数达到阈值"""
        mock_redis = Mock()
        watchdog = GPUWatchdog(redis_client=mock_redis, failure_threshold=3)
        watchdog.failure_count = 2
        
        with patch.object(watchdog, 'trigger_driver_reload', return_value=True):
            watchdog._handle_failure()
        
        assert watchdog.failure_count == 3
        assert watchdog.status == GPUHealthStatus.UNHEALTHY


class TestGPUWatchdogRedisIntegration:
    """GPUWatchdog Redis集成测试"""
    
    def test_update_redis_status(self):
        """测试更新Redis状态"""
        mock_redis = Mock()
        watchdog = GPUWatchdog(redis_client=mock_redis)
        
        watchdog._update_redis_status('DEGRADED')
        
        mock_redis.set.assert_called_with(
            GPUWatchdog.REDIS_KEY_SOLDIER_STATUS,
            'DEGRADED'
        )
    
    def test_update_redis_status_no_redis(self):
        """测试无Redis时更新状态"""
        watchdog = GPUWatchdog(redis_client=None)
        
        # 不应抛出异常
        watchdog._update_redis_status('DEGRADED')
    
    def test_update_redis_status_error(self):
        """测试Redis更新出错"""
        mock_redis = Mock()
        mock_redis.set.side_effect = Exception("Redis error")
        watchdog = GPUWatchdog(redis_client=mock_redis)
        
        # 不应抛出异常
        watchdog._update_redis_status('DEGRADED')
    
    def test_update_redis_failure_count(self):
        """测试更新Redis失败计数"""
        mock_redis = Mock()
        watchdog = GPUWatchdog(redis_client=mock_redis)
        watchdog.failure_count = 5
        
        watchdog._update_redis_failure_count()
        
        mock_redis.set.assert_called_with(
            GPUWatchdog.REDIS_KEY_GPU_FAILURES,
            5
        )


class TestGPUWatchdogParseOutput:
    """GPUWatchdog输出解析测试"""
    
    def test_parse_valid_output(self):
        """测试解析有效输出"""
        watchdog = GPUWatchdog()
        output = """
GPU[0]		: VRAM Total Memory (B): 34359738368
GPU[0]		: VRAM Total Used Memory (B): 8589934592
        """
        
        metrics = watchdog._parse_gpu_output(output)
        
        assert metrics is not None
        assert metrics.memory_total_mb == pytest.approx(32768.0, rel=0.01)
        assert metrics.memory_used_mb == pytest.approx(8192.0, rel=0.01)
        assert metrics.memory_free_mb == pytest.approx(24576.0, rel=0.01)
    
    def test_parse_invalid_output(self):
        """测试解析无效输出"""
        watchdog = GPUWatchdog()
        output = "Invalid output"
        
        metrics = watchdog._parse_gpu_output(output)
        
        assert metrics is None
    
    def test_parse_missing_total(self):
        """测试缺少总显存"""
        watchdog = GPUWatchdog()
        output = """
GPU[0]		: VRAM Total Used Memory (B): 8589934592
        """
        
        metrics = watchdog._parse_gpu_output(output)
        
        assert metrics is None
    
    def test_parse_missing_used(self):
        """测试缺少已用显存"""
        watchdog = GPUWatchdog()
        output = """
GPU[0]		: VRAM Total Memory (B): 34359738368
        """
        
        metrics = watchdog._parse_gpu_output(output)
        
        assert metrics is None



class TestGPUWatchdogWatchdogLoop:
    """GPUWatchdog看门狗循环测试"""
    
    def test_watchdog_loop_normal(self):
        """测试看门狗循环正常运行"""
        watchdog = GPUWatchdog()
        watchdog._running = True
        
        call_count = [0]
        
        def mock_check():
            call_count[0] += 1
            if call_count[0] >= 2:
                watchdog._running = False
            return True
        
        with patch.object(watchdog, 'check_gpu_health', side_effect=mock_check):
            with patch('time.sleep'):
                watchdog._watchdog_loop()
        
        assert call_count[0] == 2
    
    def test_watchdog_loop_exception(self):
        """测试看门狗循环异常处理"""
        watchdog = GPUWatchdog()
        watchdog._running = True
        
        call_count = [0]
        
        def mock_check():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Test error")
            watchdog._running = False
            return True
        
        with patch.object(watchdog, 'check_gpu_health', side_effect=mock_check):
            with patch('time.sleep'):
                watchdog._watchdog_loop()
        
        assert call_count[0] == 2


class TestGPUWatchdogDriverReloadException:
    """GPUWatchdog驱动重载异常测试"""
    
    def test_trigger_driver_reload_exception(self):
        """测试驱动重载异常"""
        mock_redis = Mock()
        watchdog = GPUWatchdog(redis_client=mock_redis)
        
        with patch('subprocess.run', side_effect=Exception("Unknown error")):
            result = watchdog.trigger_driver_reload()
        
        assert result is False
