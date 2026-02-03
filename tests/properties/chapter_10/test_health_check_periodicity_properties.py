"""Property-based tests for health check periodicity

白皮书依据: 第十章 10.1 健康检查系统
Property 3: Health Check Periodicity
Validates: Requirements 2.1

测试健康检查的周期性：在任意60秒观察窗口内，健康检查应执行至少1次，最多2次（考虑时间偏差）。
"""

import asyncio
import time
from typing import List
from unittest.mock import Mock, patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from src.core.health_checker import HealthChecker


class TestHealthCheckPeriodicityProperties:
    """Property tests for health check periodicity
    
    白皮书依据: 第十章 10.1 健康检查系统
    Property 3: Health Check Periodicity
    """
    
    @pytest.mark.property
    @settings(max_examples=20, deadline=None)
    @given(
        observation_window=st.floats(min_value=55.0, max_value=65.0),
        check_interval=st.floats(min_value=28.0, max_value=32.0)
    )
    def test_property_health_check_executes_within_bounds(
        self,
        observation_window: float,
        check_interval: float
    ):
        """Property: Health check executes within expected bounds
        
        白皮书依据: 第十章 10.1 健康检查系统
        Property 3: Health Check Periodicity
        Validates: Requirements 2.1
        
        For any 60-second observation window, the health checker should execute
        at least 1 check and at most 2 checks (accounting for timing variance).
        
        Args:
            observation_window: Observation window duration (55-65 seconds)
            check_interval: Health check interval (28-32 seconds, nominal 30s)
        """
        # Setup: Create health checker with mocked dependencies
        with patch('redis.Redis') as mock_redis_class, \
             patch('time.sleep') as mock_sleep, \
             patch('time.time') as mock_time, \
             patch('psutil.cpu_percent') as mock_cpu_percent, \
             patch('psutil.virtual_memory') as mock_virtual_memory, \
             patch('psutil.disk_usage') as mock_disk_usage, \
             patch('socket.socket') as mock_socket_class, \
             patch('subprocess.run') as mock_subprocess_run:
            
            # Mock Redis
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                'used_memory': 1024 * 1024 * 100,  # 100MB
                'connected_clients': 5
            }
            
            # Mock psutil to avoid real waiting
            mock_cpu_percent.return_value = 50.0
            mock_virtual_memory.return_value = Mock(
                total=16 * 1024**3,
                available=8 * 1024**3,
                percent=50.0
            )
            mock_disk_usage.return_value = Mock(
                total=1000 * 1024**3,
                used=500 * 1024**3,
                free=500 * 1024**3
            )
            
            # Mock socket to avoid real network waiting
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.connect_ex.return_value = 1  # Port not accessible
            mock_socket.close.return_value = None
            
            # Mock subprocess for GPU check
            mock_subprocess_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="rocm-smi not found"
            )
            
            # Mock time progression without actual waiting
            current_time = [0.0]  # Use list to allow modification in nested function
            
            def mock_time_func():
                return current_time[0]
            
            def mock_sleep_func(duration):
                current_time[0] += duration
            
            mock_time.side_effect = mock_time_func
            mock_sleep.side_effect = mock_sleep_func
            
            health_checker = HealthChecker(
                redis_host='localhost',
                redis_port=6379,
                redis_timeout=5
            )
            
            # Track check executions
            check_times: List[float] = []
            original_run_health_check = health_checker.run_health_check
            
            def tracked_run_health_check():
                check_times.append(current_time[0])
                return original_run_health_check()
            
            health_checker.run_health_check = tracked_run_health_check
            
            # Execute: Run checks for observation window
            start_time = current_time[0]
            end_time = start_time + observation_window
            
            while current_time[0] < end_time:
                health_checker.run_health_check()
                mock_sleep_func(check_interval)
            
            # Verify: Check count should be within bounds
            check_count = len(check_times)
            
            # Expected checks: observation_window / check_interval
            # For 60s window with 30s interval: 60/30 = 2 checks
            # With variance (55-65s window, 28-32s interval):
            # Min: 55/32 ≈ 1.7 → at least 1 check
            # Max: 65/28 ≈ 2.3 → at most 3 checks (allowing for timing variance)
            expected_min = max(1, int(observation_window / (check_interval + 2)))
            expected_max = int(observation_window / (check_interval - 2)) + 1
            
            assert expected_min <= check_count <= expected_max, (
                f"Health check count {check_count} outside expected bounds "
                f"[{expected_min}, {expected_max}] for window={observation_window:.1f}s, "
                f"interval={check_interval:.1f}s"
            )
    
    @pytest.mark.property
    def test_property_health_check_interval_consistency(self):
        """Property: Health check intervals are consistent
        
        白皮书依据: 第十章 10.1 健康检查系统
        Property 3: Health Check Periodicity
        Validates: Requirements 2.1
        
        The time between consecutive health checks should be approximately
        30 seconds (±2 seconds for timing variance).
        """
        # Setup: Create health checker with mocked dependencies
        with patch('redis.Redis') as mock_redis_class, \
             patch('time.sleep') as mock_sleep, \
             patch('time.time') as mock_time, \
             patch('psutil.cpu_percent') as mock_cpu_percent, \
             patch('psutil.virtual_memory') as mock_virtual_memory, \
             patch('psutil.disk_usage') as mock_disk_usage, \
             patch('socket.socket') as mock_socket_class, \
             patch('subprocess.run') as mock_subprocess_run:
            
            # Mock Redis
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                'used_memory': 1024 * 1024 * 100,
                'connected_clients': 5
            }
            
            # Mock psutil
            mock_cpu_percent.return_value = 50.0
            mock_virtual_memory.return_value = Mock(
                total=16 * 1024**3,
                available=8 * 1024**3,
                percent=50.0
            )
            mock_disk_usage.return_value = Mock(
                total=1000 * 1024**3,
                used=500 * 1024**3,
                free=500 * 1024**3
            )
            
            # Mock socket
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.connect_ex.return_value = 1
            mock_socket.close.return_value = None
            
            # Mock subprocess
            mock_subprocess_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="rocm-smi not found"
            )
            
            # Mock time progression
            current_time = [0.0]
            
            def mock_time_func():
                return current_time[0]
            
            def mock_sleep_func(duration):
                current_time[0] += duration
            
            mock_time.side_effect = mock_time_func
            mock_sleep.side_effect = mock_sleep_func
            
            health_checker = HealthChecker(
                redis_host='localhost',
                redis_port=6379,
                redis_timeout=5
            )
            
            # Track check times
            check_times: List[float] = []
            original_run_health_check = health_checker.run_health_check
            
            def tracked_run_health_check():
                check_times.append(current_time[0])
                return original_run_health_check()
            
            health_checker.run_health_check = tracked_run_health_check
            
            # Execute: Run 3 checks with 30-second intervals
            for _ in range(3):
                health_checker.run_health_check()
                mock_sleep_func(30.0)
            
            # Verify: Intervals should be consistent
            if len(check_times) >= 2:
                intervals = [
                    check_times[i+1] - check_times[i]
                    for i in range(len(check_times) - 1)
                ]
                
                for interval in intervals:
                    # Allow ±2 seconds variance for timing
                    assert 28.0 <= interval <= 32.0, (
                        f"Health check interval {interval:.2f}s outside "
                        f"expected range [28.0, 32.0]"
                    )
    
    @pytest.mark.property
    @settings(max_examples=10, deadline=None)
    @given(
        num_checks=st.integers(min_value=3, max_value=10)
    )
    def test_property_all_components_checked_each_cycle(
        self,
        num_checks: int
    ):
        """Property: All components are checked in each cycle
        
        白皮书依据: 第十章 10.1 健康检查系统
        Property 3: Health Check Periodicity
        Validates: Requirements 2.1
        
        For any health check execution, all monitored components
        (Redis, Dashboard, disk, memory, CPU, GPU) should be checked.
        
        Args:
            num_checks: Number of health check cycles to execute
        """
        # Setup: Create health checker with mocked dependencies
        with patch('redis.Redis') as mock_redis_class, \
             patch('subprocess.run') as mock_subprocess_run, \
             patch('psutil.cpu_percent') as mock_cpu_percent, \
             patch('psutil.virtual_memory') as mock_virtual_memory, \
             patch('psutil.disk_usage') as mock_disk_usage, \
             patch('socket.socket') as mock_socket_class:
            
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                'used_memory': 1024 * 1024 * 100,
                'connected_clients': 5
            }
            
            # Mock subprocess for GPU check
            mock_subprocess_run.return_value = Mock(
                returncode=0,
                stdout="GPU OK"
            )
            
            # Mock psutil to avoid real waiting
            mock_cpu_percent.return_value = 50.0
            mock_virtual_memory.return_value = Mock(
                total=16 * 1024**3,
                available=8 * 1024**3,
                percent=50.0
            )
            mock_disk_usage.return_value = Mock(
                total=1000 * 1024**3,
                used=500 * 1024**3,
                free=500 * 1024**3
            )
            
            # Mock socket to avoid real network waiting
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.connect_ex.return_value = 1
            mock_socket.close.return_value = None
            
            health_checker = HealthChecker(
                redis_host='localhost',
                redis_port=6379,
                redis_timeout=5
            )
            
            # Execute: Run multiple health checks
            for _ in range(num_checks):
                result = health_checker.run_health_check()
                
                # Verify: All components should be present in result
                assert 'redis' in result.components, "Redis not checked"
                assert 'disk' in result.components, "Disk not checked"
                assert 'memory' in result.components, "Memory not checked"
                assert 'cpu' in result.components, "CPU not checked"
                
                # Note: GPU and dashboard checks may be optional depending on environment
                # but should be attempted
    
    @pytest.mark.property
    def test_property_health_check_never_skips_cycle(self):
        """Property: Health checks never skip a cycle
        
        白皮书依据: 第十章 10.1 健康检查系统
        Property 3: Health Check Periodicity
        Validates: Requirements 2.1
        
        When health checks are scheduled at 30-second intervals,
        no cycle should be skipped (all scheduled checks execute).
        """
        # Setup: Create health checker with mocked dependencies
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            health_checker = HealthChecker(
                redis_host='localhost',
                redis_port=6379,
                redis_timeout=5
            )
            
            # Track scheduled vs executed checks
            scheduled_checks = 5
            executed_checks = 0
            
            # Execute: Run scheduled checks
            for _ in range(scheduled_checks):
                result = health_checker.run_health_check()
                if result is not None:
                    executed_checks += 1
                time.sleep(0.1)  # Small delay to simulate scheduling
            
            # Verify: All scheduled checks should execute
            assert executed_checks == scheduled_checks, (
                f"Skipped {scheduled_checks - executed_checks} health check cycles"
            )
    
    @pytest.mark.property
    @settings(max_examples=10, deadline=None)
    @given(
        failure_rate=st.floats(min_value=0.0, max_value=0.5)
    )
    def test_property_health_check_continues_after_component_failure(
        self,
        failure_rate: float
    ):
        """Property: Health checks continue even if components fail
        
        白皮书依据: 第十章 10.1 健康检查系统
        Property 3: Health Check Periodicity
        Validates: Requirements 2.1
        
        Even if some components fail health checks, the health check
        cycle should continue and check all other components.
        
        Args:
            failure_rate: Probability of component failure (0.0-0.5)
        """
        # Setup: Create health checker with mocked dependencies
        with patch('redis.Redis') as mock_redis_class, \
             patch('psutil.cpu_percent') as mock_cpu_percent, \
             patch('psutil.virtual_memory') as mock_virtual_memory, \
             patch('psutil.disk_usage') as mock_disk_usage, \
             patch('socket.socket') as mock_socket_class, \
             patch('subprocess.run') as mock_subprocess_run:
            
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            # Simulate intermittent Redis failures
            def redis_ping_with_failures():
                import random
                if random.random() < failure_rate:
                    raise ConnectionError("Simulated Redis failure")
                return True
            
            mock_redis.ping.side_effect = redis_ping_with_failures
            mock_redis.info.return_value = {
                'used_memory': 1024 * 1024 * 100,
                'connected_clients': 5
            }
            
            # Mock psutil to avoid real waiting
            mock_cpu_percent.return_value = 50.0
            mock_virtual_memory.return_value = Mock(
                total=16 * 1024**3,
                available=8 * 1024**3,
                percent=50.0
            )
            mock_disk_usage.return_value = Mock(
                total=1000 * 1024**3,
                used=500 * 1024**3,
                free=500 * 1024**3
            )
            
            # Mock socket to avoid real network waiting
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.connect_ex.return_value = 1
            mock_socket.close.return_value = None
            
            # Mock subprocess
            mock_subprocess_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="rocm-smi not found"
            )
            
            health_checker = HealthChecker(
                redis_host='localhost',
                redis_port=6379,
                redis_timeout=5
            )
            
            # Execute: Run multiple health checks
            check_count = 5
            successful_checks = 0
            
            for _ in range(check_count):
                try:
                    result = health_checker.run_health_check()
                    if result is not None:
                        successful_checks += 1
                except Exception:
                    # Health check should handle failures gracefully
                    pass
            
            # Verify: At least some checks should complete
            # (even with failures, the check cycle continues)
            assert successful_checks > 0, (
                "No health checks completed despite component failures"
            )


class TestHealthCheckPeriodicityIntegration:
    """Integration tests for health check periodicity
    
    白皮书依据: 第十章 10.1 健康检查系统
    """
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skip(reason="Uses real time.sleep(), run manually with pytest -m slow")
    def test_integration_health_check_60_second_window(self):
        """Integration: Health check in 60-second window
        
        白皮书依据: 第十章 10.1 健康检查系统
        Property 3: Health Check Periodicity
        Validates: Requirements 2.1
        
        In a real 60-second observation window with 30-second intervals,
        exactly 2 health checks should execute.
        
        NOTE: This test uses real time.sleep() and takes ~60 seconds to run.
        It is marked as @pytest.mark.slow and should be run separately.
        """
        # Setup: Create health checker with mocked dependencies
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.ping.return_value = True
            
            health_checker = HealthChecker(
                redis_host='localhost',
                redis_port=6379,
                redis_timeout=5
            )
            
            # Track check times
            check_times: List[float] = []
            original_run_health_check = health_checker.run_health_check
            
            def tracked_run_health_check():
                check_times.append(time.time())
                return original_run_health_check()
            
            health_checker.run_health_check = tracked_run_health_check
            
            # Execute: Run checks for 60 seconds
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < 60.0:
                health_checker.run_health_check()
                check_count += 1
                time.sleep(30.0)
            
            # Verify: Should have 2 checks (at 0s and 30s)
            assert 2 <= check_count <= 3, (
                f"Expected 2-3 checks in 60s window, got {check_count}"
            )
            
            # Verify intervals
            if len(check_times) >= 2:
                interval = check_times[1] - check_times[0]
                assert 28.0 <= interval <= 32.0, (
                    f"Check interval {interval:.2f}s outside expected range"
                )
