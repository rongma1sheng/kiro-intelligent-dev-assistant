"""GPU看门狗单元测试

白皮书依据: 第一章 1.1 战备态 - GPU看门狗

测试覆盖:
1. 初始化测试
2. GPU状态检查测试
3. 碎片化检测测试
4. 驱动热重载测试
5. 看门狗循环测试
6. 异常处理测试
"""

import pytest
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock
from src.chronos.gpu_watchdog import (
    GPUWatchdog,
    GPUStatus,
    GPUMetrics
)


class TestGPUWatchdogInitialization:
    """测试GPU看门狗初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        watchdog = GPUWatchdog()
        
        assert watchdog.check_interval == 30
        assert watchdog.fragmentation_threshold == 0.3
        assert watchdog.status == GPUStatus.NORMAL
        assert watchdog.metrics is None
        assert not watchdog._running
    
    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        watchdog = GPUWatchdog(
            check_interval=60,
            fragmentation_threshold=0.5
        )
        
        assert watchdog.check_interval == 60
        assert watchdog.fragmentation_threshold == 0.5
    
    def test_invalid_check_interval(self):
        """测试无效的检查间隔"""
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            GPUWatchdog(check_interval=0)
        
        with pytest.raises(ValueError, match="检查间隔必须 > 0"):
            GPUWatchdog(check_interval=-10)
    
    def test_invalid_fragmentation_threshold(self):
        """测试无效的碎片化阈值"""
        with pytest.raises(ValueError, match="碎片化阈值必须在"):
            GPUWatchdog(fragmentation_threshold=0)
        
        with pytest.raises(ValueError, match="碎片化阈值必须在"):
            GPUWatchdog(fragmentation_threshold=1.0)
        
        with pytest.raises(ValueError, match="碎片化阈值必须在"):
            GPUWatchdog(fragmentation_threshold=-0.1)


class TestGPUStatusCheck:
    """测试GPU状态检查"""
    
    @patch('subprocess.run')
    def test_successful_gpu_check(self, mock_run):
        """测试成功的GPU检查"""
        # Mock rocm-smi输出
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 8589934592
            """
        )
        
        watchdog = GPUWatchdog()
        result = watchdog.check_gpu()
        
        assert result is True
        assert watchdog.status == GPUStatus.NORMAL
        assert watchdog.metrics is not None
        assert watchdog.metrics.memory_total > 0
        assert watchdog.metrics.memory_used > 0
    
    @patch('subprocess.run')
    def test_gpu_check_command_failure(self, mock_run):
        """测试rocm-smi命令失败"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Command failed"
        )
        
        watchdog = GPUWatchdog()
        result = watchdog.check_gpu()
        
        assert result is False
        assert watchdog.status == GPUStatus.UNAVAILABLE
    
    @patch('subprocess.run')
    def test_gpu_check_timeout(self, mock_run):
        """测试rocm-smi超时"""
        mock_run.side_effect = subprocess.TimeoutExpired('rocm-smi', 5.0)
        
        watchdog = GPUWatchdog()
        result = watchdog.check_gpu()
        
        assert result is False
        assert watchdog.status == GPUStatus.UNAVAILABLE
    
    @patch('subprocess.run')
    def test_gpu_check_not_found(self, mock_run):
        """测试rocm-smi未找到"""
        mock_run.side_effect = FileNotFoundError()
        
        watchdog = GPUWatchdog()
        result = watchdog.check_gpu()
        
        assert result is False
        assert watchdog.status == GPUStatus.UNAVAILABLE
    
    @patch('subprocess.run')
    def test_gpu_check_parse_error(self, mock_run):
        """测试解析错误"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Invalid output format"
        )
        
        watchdog = GPUWatchdog()
        result = watchdog.check_gpu()
        
        assert result is False
        assert watchdog.status == GPUStatus.UNAVAILABLE


class TestFragmentationDetection:
    """测试碎片化检测"""
    
    @patch('subprocess.run')
    def test_low_fragmentation(self, mock_run):
        """测试低碎片化（正常状态）"""
        # 使用率20%，碎片化估算10%
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 6871947673
            """
        )
        
        watchdog = GPUWatchdog(fragmentation_threshold=0.3)
        watchdog.check_gpu()
        
        assert watchdog.status == GPUStatus.NORMAL
        assert watchdog.metrics.fragmentation < 0.3
    
    @patch('subprocess.run')
    def test_high_fragmentation_triggers_reload(self, mock_run):
        """测试高碎片化触发重载"""
        # 第一次调用：高碎片化
        # 第二次调用：重载命令
        # 第三次调用：重载后检查
        mock_run.side_effect = [
            # 第一次检查：高使用率80%，碎片化40%
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 27487790694
                """
            ),
            # 重载命令
            Mock(returncode=0, stdout="GPU reset successful"),
            # 重载后检查：低使用率
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 3435973836
                """
            )
        ]
        
        watchdog = GPUWatchdog(fragmentation_threshold=0.3)
        watchdog.check_gpu()
        
        # 应该触发重载并进入DEGRADED状态
        assert watchdog.status == GPUStatus.NORMAL  # 重载后恢复


class TestHotReload:
    """测试驱动热重载"""
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_successful_hot_reload(self, mock_sleep, mock_run):
        """测试成功的热重载"""
        mock_run.side_effect = [
            # 检测到高碎片化
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 27487790694
                """
            ),
            # 重载命令成功
            Mock(returncode=0, stdout="GPU reset successful"),
            # 重载后检查
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 3435973836
                """
            )
        ]
        
        watchdog = GPUWatchdog(fragmentation_threshold=0.3)
        watchdog.check_gpu()
        
        # 验证重载命令被调用
        assert mock_run.call_count >= 2
    
    @patch('subprocess.run')
    def test_hot_reload_failure(self, mock_run):
        """测试热重载失败"""
        mock_run.side_effect = [
            # 检测到高碎片化
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 27487790694
                """
            ),
            # 重载命令失败
            Mock(returncode=1, stderr="Reset failed")
        ]
        
        watchdog = GPUWatchdog(fragmentation_threshold=0.3)
        watchdog.check_gpu()
        
        # 应该保持DEGRADED状态
        assert watchdog.status == GPUStatus.DEGRADED
    
    @patch('subprocess.run')
    def test_hot_reload_timeout(self, mock_run):
        """测试热重载超时"""
        mock_run.side_effect = [
            # 检测到高碎片化
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 27487790694
                """
            ),
            # 重载命令超时
            subprocess.TimeoutExpired('rocm-smi', 90.0)
        ]
        
        watchdog = GPUWatchdog(fragmentation_threshold=0.3)
        watchdog.check_gpu()
        
        # 应该保持DEGRADED状态
        assert watchdog.status == GPUStatus.DEGRADED


class TestWatchdogLifecycle:
    """测试看门狗生命周期"""
    
    @patch('subprocess.run')
    def test_start_watchdog(self, mock_run):
        """测试启动看门狗"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 8589934592
            """
        )
        
        watchdog = GPUWatchdog(check_interval=1)
        watchdog.start()
        
        assert watchdog._running is True
        assert watchdog._thread is not None
        assert watchdog._thread.is_alive()
        
        # 等待至少一次检查
        time.sleep(1.5)
        
        watchdog.stop()
    
    def test_start_already_running(self):
        """测试重复启动"""
        watchdog = GPUWatchdog()
        watchdog.start()
        
        with pytest.raises(RuntimeError, match="已经在运行"):
            watchdog.start()
        
        watchdog.stop()
    
    @patch('subprocess.run')
    def test_stop_watchdog(self, mock_run):
        """测试停止看门狗"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 8589934592
            """
        )
        
        watchdog = GPUWatchdog(check_interval=1)
        watchdog.start()
        
        time.sleep(0.5)
        
        watchdog.stop()
        
        assert watchdog._running is False
        
        # 等待线程结束
        time.sleep(1.5)
        
        if watchdog._thread:
            assert not watchdog._thread.is_alive()
    
    def test_stop_not_running(self):
        """测试停止未运行的看门狗"""
        watchdog = GPUWatchdog()
        
        # 不应该抛出异常
        watchdog.stop()


class TestGetters:
    """测试获取器方法"""
    
    def test_get_status(self):
        """测试获取状态"""
        watchdog = GPUWatchdog()
        
        assert watchdog.get_status() == GPUStatus.NORMAL
        
        watchdog.status = GPUStatus.DEGRADED
        assert watchdog.get_status() == GPUStatus.DEGRADED
    
    @patch('subprocess.run')
    def test_get_metrics(self, mock_run):
        """测试获取指标"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 8589934592
            """
        )
        
        watchdog = GPUWatchdog()
        
        # 初始状态
        assert watchdog.get_metrics() is None
        
        # 检查后
        watchdog.check_gpu()
        metrics = watchdog.get_metrics()
        
        assert metrics is not None
        assert metrics.memory_total > 0
        assert metrics.memory_used > 0
        assert metrics.memory_free > 0
        assert 0 <= metrics.fragmentation <= 1


class TestMetricsParsing:
    """测试指标解析"""
    
    def test_parse_valid_output(self):
        """测试解析有效输出"""
        watchdog = GPUWatchdog()
        
        output = """
        GPU[0]		: VRAM Total Memory (B): 34359738368
        GPU[0]		: VRAM Total Used Memory (B): 8589934592
        """
        
        metrics = watchdog._parse_rocm_smi_output(output)
        
        assert metrics is not None
        assert metrics.memory_total == 34359738368 / (1024 ** 2)
        assert metrics.memory_used == 8589934592 / (1024 ** 2)
        assert metrics.memory_free == metrics.memory_total - metrics.memory_used
    
    def test_parse_invalid_output(self):
        """测试解析无效输出"""
        watchdog = GPUWatchdog()
        
        # 缺少总显存
        output1 = """
        GPU[0]		: VRAM Total Used Memory (B): 8589934592
        """
        assert watchdog._parse_rocm_smi_output(output1) is None
        
        # 缺少已使用显存
        output2 = """
        GPU[0]		: VRAM Total Memory (B): 34359738368
        """
        assert watchdog._parse_rocm_smi_output(output2) is None
        
        # 完全无效
        output3 = "Invalid output"
        assert watchdog._parse_rocm_smi_output(output3) is None


class TestThreadSafety:
    """测试线程安全"""
    
    @patch('subprocess.run')
    def test_concurrent_access(self, mock_run):
        """测试并发访问"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 8589934592
            """
        )
        
        watchdog = GPUWatchdog(check_interval=1)
        watchdog.start()
        
        # 并发读取状态和指标
        import threading
        
        def read_status():
            for _ in range(10):
                watchdog.get_status()
                time.sleep(0.1)
        
        def read_metrics():
            for _ in range(10):
                watchdog.get_metrics()
                time.sleep(0.1)
        
        threads = [
            threading.Thread(target=read_status),
            threading.Thread(target=read_metrics)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        watchdog.stop()
        
        # 不应该有异常


class TestEdgeCases:
    """测试边界条件"""
    
    @patch('subprocess.run')
    def test_zero_memory_used(self, mock_run):
        """测试零显存使用"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 0
            """
        )
        
        watchdog = GPUWatchdog()
        result = watchdog.check_gpu()
        
        assert result is True
        assert watchdog.metrics.memory_used == 0
        assert watchdog.metrics.fragmentation >= 0
    
    @patch('time.sleep')  # Mock sleep to avoid delays
    @patch('subprocess.run')
    def test_full_memory_used(self, mock_run, mock_sleep):
        """测试满显存使用"""
        # 设置高碎片化阈值，避免触发热重载
        mock_run.return_value = Mock(
            returncode=0,
            stdout="""
            GPU[0]		: VRAM Total Memory (B): 34359738368
            GPU[0]		: VRAM Total Used Memory (B): 34359738368
            """
        )
        
        # 使用高阈值避免触发重载
        watchdog = GPUWatchdog(fragmentation_threshold=0.9)
        result = watchdog.check_gpu()
        
        assert result is True
        assert watchdog.metrics.memory_free == 0
    
    @patch('time.sleep')  # Mock sleep to avoid delays
    @patch('subprocess.run')
    def test_exception_in_watchdog_loop(self, mock_run, mock_sleep):
        """测试看门狗循环中的异常"""
        # 第一次调用抛出异常，第二次正常
        mock_run.side_effect = [
            Exception("Unexpected error"),
            Mock(
                returncode=0,
                stdout="""
                GPU[0]		: VRAM Total Memory (B): 34359738368
                GPU[0]		: VRAM Total Used Memory (B): 8589934592
                """
            )
        ]
        
        watchdog = GPUWatchdog(check_interval=0.1)  # 使用短间隔
        watchdog.start()
        
        # 等待两次检查（使用真实sleep）
        time.sleep(0.3)
        
        watchdog.stop()
        
        # 看门狗应该继续运行，不会崩溃
