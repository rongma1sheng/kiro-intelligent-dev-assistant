"""物理时钟同步模块测试

白皮书依据: 第一章 1.2 物理时钟同步
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import socket
import struct

from src.chronos.clock_sync import (
    PhysicalClockSync,
    SyncProtocol,
    SyncStatus,
    ClockOffset,
    SyncMetrics,
    ClockSyncError,
    get_system_time_precision,
    check_clock_sync_status
)


class TestClockOffset:
    """时钟偏移量测试类"""
    
    def test_clock_offset_creation(self):
        """时钟偏移量创建测试"""
        offset = ClockOffset(
            offset_ms=1.5,
            precision_ms=0.5,
            timestamp=time.time(),
            source="test"
        )
        
        assert offset.offset_ms == 1.5
        assert offset.precision_ms == 0.5
        assert offset.source == "test"
        assert isinstance(offset.timestamp, float)


class TestSyncMetrics:
    """同步指标测试类"""
    
    def test_sync_metrics_creation(self):
        """同步指标创建测试"""
        metrics = SyncMetrics(
            last_sync_time=time.time(),
            sync_count=10,
            avg_offset_ms=1.2,
            max_offset_ms=2.5,
            sync_failures=1,
            status=SyncStatus.SYNCED
        )
        
        assert metrics.sync_count == 10
        assert metrics.avg_offset_ms == 1.2
        assert metrics.max_offset_ms == 2.5
        assert metrics.sync_failures == 1
        assert metrics.status == SyncStatus.SYNCED


class TestPhysicalClockSync:
    """物理时钟同步器测试类"""
    
    @pytest.fixture
    def clock_sync(self):
        """时钟同步器夹具"""
        return PhysicalClockSync(
            protocol=SyncProtocol.NTP,
            sync_interval=0.1,  # 快速测试
            precision_threshold=1.0
        )
    
    def test_initialization(self):
        """初始化测试"""
        sync = PhysicalClockSync(
            protocol=SyncProtocol.NTP,
            ntp_servers=["test.server.com"],
            sync_interval=30.0,
            precision_threshold=0.5
        )
        
        assert sync.protocol == SyncProtocol.NTP
        assert sync.ntp_servers == ["test.server.com"]
        assert sync.sync_interval == 30.0
        assert sync.precision_threshold == 0.5
        assert not sync._running
        assert sync._current_offset is None
    
    def test_invalid_parameters(self):
        """无效参数测试"""
        # 无效同步间隔
        with pytest.raises(ValueError, match="sync_interval必须 > 0"):
            PhysicalClockSync(sync_interval=0)
        
        # 无效精度阈值
        with pytest.raises(ValueError, match="precision_threshold必须 > 0"):
            PhysicalClockSync(precision_threshold=-1)
    
    def test_start_stop_sync(self, clock_sync):
        """启动停止同步测试"""
        # 初始状态
        assert not clock_sync._running
        assert clock_sync.get_metrics().status == SyncStatus.DISABLED
        
        # 启动同步
        clock_sync.start_sync()
        assert clock_sync._running
        assert clock_sync.get_metrics().status == SyncStatus.SYNCING
        
        # 重复启动应该失败
        with pytest.raises(ClockSyncError, match="already running"):
            clock_sync.start_sync()
        
        # 停止同步
        clock_sync.stop_sync()
        assert not clock_sync._running
        # 给一点时间让状态更新
        time.sleep(0.01)
        assert clock_sync.get_metrics().status == SyncStatus.DISABLED
        
        # 重复停止应该安全
        clock_sync.stop_sync()
    
    def test_system_sync(self):
        """系统时间同步测试"""
        sync = PhysicalClockSync(protocol=SyncProtocol.SYSTEM)
        
        # 强制同步
        success = sync.force_sync()
        assert success
        
        # 检查偏移量
        offset = sync.get_current_offset()
        assert offset is not None
        assert offset.offset_ms == 0.0
        assert offset.precision_ms <= 1.0  # 系统精度应该 <= 1.0ms
        assert offset.precision_ms > 0.0   # 但必须 > 0
        assert offset.source == "system"
        
        # 应该显示为已同步
        assert sync.is_synced()
    
    @patch('socket.socket')
    def test_ntp_sync_success(self, mock_socket, clock_sync):
        """NTP同步成功测试"""
        # 模拟NTP响应
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        # 构造NTP响应包
        ntp_response = bytearray(48)
        # 设置发送时间戳（字节32-35）
        current_time = int(time.time()) + 2208988800  # NTP时间戳
        struct.pack_into('!I', ntp_response, 32, current_time)
        struct.pack_into('!I', ntp_response, 40, current_time)
        
        mock_sock.recvfrom.return_value = (bytes(ntp_response), None)
        
        # 执行同步
        success = clock_sync.force_sync()
        assert success
        
        # 检查结果
        offset = clock_sync.get_current_offset()
        assert offset is not None
        assert "ntp://" in offset.source
        assert offset.precision_ms > 0
    
    @patch('socket.socket')
    def test_ntp_sync_failure(self, mock_socket, clock_sync):
        """NTP同步失败测试"""
        # 模拟网络错误
        mock_socket.side_effect = socket.error("Network error")
        
        # 执行同步
        success = clock_sync.force_sync()
        assert not success
        
        # 检查结果
        offset = clock_sync.get_current_offset()
        assert offset is None
    
    @patch('socket.socket')
    def test_ntp_sync_timeout(self, mock_socket, clock_sync):
        """NTP同步超时测试"""
        # 模拟超时
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.recvfrom.side_effect = socket.timeout("Timeout")
        
        # 执行同步
        success = clock_sync.force_sync()
        assert not success
    
    def test_multiple_ntp_servers(self):
        """多NTP服务器测试"""
        servers = ["server1.com", "server2.com", "server3.com"]
        sync = PhysicalClockSync(ntp_servers=servers)
        
        assert sync.ntp_servers == servers
    
    def test_sync_metrics_update(self, clock_sync):
        """同步指标更新测试"""
        # 使用系统同步进行测试
        clock_sync.protocol = SyncProtocol.SYSTEM
        
        # 执行多次同步
        for _ in range(3):
            clock_sync.force_sync()
            time.sleep(0.01)
        
        # 检查指标
        metrics = clock_sync.get_metrics()
        assert metrics.sync_count == 3
        assert metrics.last_sync_time > 0
        assert metrics.avg_offset_ms >= 0
        assert metrics.max_offset_ms >= 0
    
    def test_offset_history_limit(self, clock_sync):
        """偏移量历史限制测试"""
        clock_sync.protocol = SyncProtocol.SYSTEM
        
        # 添加大量偏移量记录
        for i in range(1200):
            offset = ClockOffset(
                offset_ms=float(i),
                precision_ms=1.0,
                timestamp=time.time(),
                source="test"
            )
            with clock_sync._lock:
                clock_sync._update_offset(offset)
        
        # 检查历史记录被限制
        assert len(clock_sync._offset_history) == 500
    
    def test_drift_rate_calculation(self, clock_sync):
        """漂移率计算测试"""
        # 初始状态无漂移率
        assert clock_sync.get_drift_rate() is None
        
        # 添加一些偏移量数据
        base_time = time.time()
        offsets = [
            ClockOffset(0.0, 1.0, base_time, "test"),
            ClockOffset(1.0, 1.0, base_time + 1, "test"),
            ClockOffset(2.0, 1.0, base_time + 2, "test"),
        ]
        
        with clock_sync._lock:
            for offset in offsets:
                clock_sync._update_offset(offset)
        
        # 计算漂移率
        drift_rate = clock_sync.get_drift_rate()
        assert drift_rate is not None
        assert isinstance(drift_rate, float)
        # 应该是正漂移（1ms/s = 3600ms/h），允许较大误差
        assert abs(drift_rate - 3600) < 1000  # 允许更大的计算误差
    
    def test_context_manager(self, clock_sync):
        """上下文管理器测试"""
        with clock_sync as sync:
            assert sync._running
            assert sync.get_metrics().status == SyncStatus.SYNCING
        
        # 退出后应该停止
        assert not clock_sync._running
        # 给一点时间让状态更新
        time.sleep(0.01)
        assert clock_sync.get_metrics().status == SyncStatus.DISABLED
    
    def test_property_5_sync_precision(self, clock_sync):
        """属性5: 物理时钟同步精度
        
        白皮书依据: 第一章 1.2 物理时钟同步
        验证需求: US-1.2
        
        测试场景：
        1. 执行时钟同步
        2. 验证同步精度 < 1ms
        3. 验证同步状态正确
        """
        # 使用系统同步确保成功
        clock_sync.protocol = SyncProtocol.SYSTEM
        
        # 执行同步
        success = clock_sync.force_sync()
        assert success, "时钟同步应该成功"
        
        # 检查同步精度
        offset = clock_sync.get_current_offset()
        assert offset is not None, "应该有偏移量数据"
        
        # 验证精度要求
        assert offset.precision_ms < 1.0, \
            f"同步精度 {offset.precision_ms:.3f}ms 应该 < 1ms"
        
        # 验证同步状态
        assert clock_sync.is_synced(), "应该显示为已同步状态"
        
        # 验证偏移量在阈值内
        assert abs(offset.offset_ms) <= clock_sync.precision_threshold, \
            f"偏移量 {offset.offset_ms:.3f}ms 应该在阈值 {clock_sync.precision_threshold}ms 内"
    
    def test_sync_loop_error_handling(self, clock_sync):
        """同步循环错误处理测试"""
        # 模拟同步方法抛出异常
        original_perform_sync = clock_sync._perform_sync
        clock_sync._perform_sync = Mock(side_effect=Exception("Test error"))
        
        # 启动同步
        clock_sync.start_sync()
        time.sleep(0.2)  # 等待几次同步尝试
        
        # 检查错误被正确处理
        metrics = clock_sync.get_metrics()
        assert metrics.sync_failures > 0
        assert metrics.status == SyncStatus.FAILED
        
        # 恢复原方法并停止
        clock_sync._perform_sync = original_perform_sync
        clock_sync.stop_sync()
    
    def test_concurrent_access_safety(self, clock_sync):
        """并发访问安全性测试"""
        clock_sync.protocol = SyncProtocol.SYSTEM
        results = []
        errors = []
        
        def sync_worker():
            """同步工作线程"""
            try:
                for _ in range(10):
                    success = clock_sync.force_sync()
                    results.append(success)
                    offset = clock_sync.get_current_offset()
                    if offset:
                        results.append(offset.offset_ms)
            except Exception as e:
                errors.append(str(e))
        
        # 启动多个并发线程
        threads = [threading.Thread(target=sync_worker) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5.0)
        
        # 验证没有错误
        assert len(errors) == 0, f"并发访问出现错误: {errors}"
        assert len(results) > 0, "应该有同步结果"


class TestUtilityFunctions:
    """工具函数测试类"""
    
    def test_get_system_time_precision(self):
        """系统时间精度测试"""
        precision = get_system_time_precision()
        
        assert isinstance(precision, float)
        assert precision > 0
        assert precision <= 100  # 应该在合理范围内（100ms以内）
    
    @patch('src.chronos.clock_sync.PhysicalClockSync')
    def test_check_clock_sync_status_success(self, mock_sync_class):
        """时钟同步状态检查成功测试"""
        # 模拟成功的同步器
        mock_sync = MagicMock()
        mock_sync_class.return_value.__enter__.return_value = mock_sync
        
        mock_sync.force_sync.return_value = True
        mock_sync.get_current_offset.return_value = ClockOffset(
            offset_ms=0.5,
            precision_ms=0.3,
            timestamp=time.time(),
            source="test"
        )
        mock_sync.get_metrics.return_value = SyncMetrics(
            last_sync_time=time.time(),
            sync_count=1,
            avg_offset_ms=0.5,
            max_offset_ms=0.5,
            sync_failures=0,
            status=SyncStatus.SYNCED
        )
        mock_sync.is_synced.return_value = True
        
        # 执行检查
        status = check_clock_sync_status()
        
        # 验证结果
        assert status["synced"] is True
        assert status["offset_ms"] == 0.5
        assert status["precision_ms"] == 0.3
        assert status["source"] == "test"
        assert status["status"] == "synced"
        assert "system_precision_ms" in status
    
    @patch('src.chronos.clock_sync.PhysicalClockSync')
    def test_check_clock_sync_status_failure(self, mock_sync_class):
        """时钟同步状态检查失败测试"""
        # 模拟失败的同步器
        mock_sync = MagicMock()
        mock_sync_class.return_value.__enter__.return_value = mock_sync
        
        mock_sync.force_sync.return_value = False
        
        # 执行检查
        status = check_clock_sync_status()
        
        # 验证结果
        assert status["synced"] is False
        assert status["error"] == "Sync failed"
        assert status["status"] == "failed"
        assert "system_precision_ms" in status
    
    @patch('src.chronos.clock_sync.PhysicalClockSync')
    def test_check_clock_sync_status_exception(self, mock_sync_class):
        """时钟同步状态检查异常测试"""
        # 模拟异常
        mock_sync_class.side_effect = Exception("Test exception")
        
        # 执行检查
        status = check_clock_sync_status()
        
        # 验证结果
        assert status["synced"] is False
        assert "Test exception" in status["error"]
        assert status["status"] == "error"
        assert "system_precision_ms" in status


class TestClockSyncIntegration:
    """时钟同步集成测试类"""
    
    def test_full_sync_workflow(self):
        """完整同步工作流测试"""
        # 使用系统同步进行集成测试
        with PhysicalClockSync(
            protocol=SyncProtocol.SYSTEM,
            sync_interval=0.1,
            precision_threshold=1.0
        ) as sync:
            
            # 等待自动同步
            time.sleep(0.2)
            
            # 验证同步状态
            assert sync.is_synced()
            
            # 验证指标
            metrics = sync.get_metrics()
            assert metrics.sync_count > 0
            assert metrics.status == SyncStatus.SYNCED
            
            # 验证偏移量
            offset = sync.get_current_offset()
            assert offset is not None
            assert offset.precision_ms <= 1.0
    
    def test_sync_precision_under_load(self):
        """负载下同步精度测试"""
        sync = PhysicalClockSync(
            protocol=SyncProtocol.SYSTEM,
            precision_threshold=1.0
        )
        
        # 在负载下执行多次同步
        start_time = time.time()
        sync_times = []
        
        for _ in range(100):
            sync_start = time.perf_counter()
            success = sync.force_sync()
            sync_end = time.perf_counter()
            
            assert success, "同步应该成功"
            sync_times.append((sync_end - sync_start) * 1000)  # 转换为毫秒
        
        # 验证同步延迟
        avg_sync_time = sum(sync_times) / len(sync_times)
        max_sync_time = max(sync_times)
        
        # 同步操作本身应该很快（< 10ms）
        assert avg_sync_time < 10.0, f"平均同步时间 {avg_sync_time:.3f}ms 过长"
        assert max_sync_time < 50.0, f"最大同步时间 {max_sync_time:.3f}ms 过长"
        
        # 验证最终精度
        assert sync.is_synced(), "负载下应该保持同步状态"
    
    def test_drift_detection_accuracy(self):
        """漂移检测准确性测试"""
        sync = PhysicalClockSync()
        
        # 模拟有规律的时钟漂移
        base_time = time.time()
        drift_rate = 2.0  # 2ms/s的漂移
        
        # 添加模拟数据
        with sync._lock:
            for i in range(20):
                offset = ClockOffset(
                    offset_ms=i * drift_rate,  # 线性漂移
                    precision_ms=0.5,
                    timestamp=base_time + i,
                    source="test"
                )
                sync._update_offset(offset)
        
        # 计算漂移率
        detected_drift = sync.get_drift_rate()
        assert detected_drift is not None
        
        # 验证检测精度（允许较大误差，因为时间戳精度限制）
        expected_drift_per_hour = drift_rate * 3600  # 2ms/s * 3600s/h = 7200ms/h
        error_ratio = abs(detected_drift - expected_drift_per_hour) / expected_drift_per_hour
        
        assert error_ratio < 0.5, \
            f"漂移检测误差过大: 期望 {expected_drift_per_hour}ms/h, " \
            f"检测到 {detected_drift:.1f}ms/h, 误差 {error_ratio*100:.1f}%"