"""末日开关触发条件属性测试

白皮书依据: 第十二章 12.3 末日开关与应急响应

**Property 11: Doomsday Switch Trigger Conditions**
**Validates: Requirements 4.10, 11.4**

测试内容:
1. 各触发条件正确检测
2. 条件不满足时不触发
3. 密码认证复位
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

from src.core.doomsday_switch import (
    DoomsdaySwitch,
    DoomsdayTriggerConfig,
    DoomsdayTriggerType,
    DoomsdayStatus
)


class TestDoomsdayTriggerProperties:
    """末日开关触发条件属性测试
    
    **Validates: Requirements 4.10, 11.4**
    """
    
    @pytest.fixture
    def temp_lock_file(self, tmp_path):
        """临时锁文件路径"""
        return str(tmp_path / "DOOMSDAY_SWITCH.lock")
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        redis = MagicMock()
        redis.get = MagicMock(return_value=None)
        redis.set = MagicMock()
        redis.delete = MagicMock()
        redis.publish = MagicMock()
        return redis
    
    @given(
        redis_failures=st.integers(min_value=0, max_value=10),
        threshold=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_redis_failure_trigger(
        self,
        redis_failures: int,
        threshold: int,
        tmp_path
    ):
        """Property 11: Redis失败触发条件
        
        **Validates: Requirements 4.10, 11.4**
        
        属性: 当Redis连续失败次数 >= 阈值时，应触发末日开关
        """
        lock_file = str(tmp_path / f"lock_{redis_failures}_{threshold}.lock")
        
        config = DoomsdayTriggerConfig(
            redis_failure_threshold=threshold,
            lock_file_path=lock_file
        )
        
        # 模拟Redis返回失败次数
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(side_effect=lambda key: {
            'system:redis_failures': str(redis_failures).encode(),
            'system:gpu_failures': b'0',
            'portfolio:daily_pnl': b'0',
            'portfolio:initial_capital': b'1000000'
        }.get(key))
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 检查触发条件
        with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', False):
            triggers = switch.check_triggers()
        
        # 验证属性
        if redis_failures >= threshold:
            assert any('Redis failures' in t for t in triggers)
        else:
            assert not any('Redis failures' in t for t in triggers)
    
    @given(
        gpu_failures=st.integers(min_value=0, max_value=10),
        threshold=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_gpu_failure_trigger(
        self,
        gpu_failures: int,
        threshold: int,
        tmp_path
    ):
        """Property 11: GPU失败触发条件
        
        **Validates: Requirements 4.10, 11.4**
        
        属性: 当GPU连续失败次数 >= 阈值时，应触发末日开关
        """
        lock_file = str(tmp_path / f"lock_gpu_{gpu_failures}_{threshold}.lock")
        
        config = DoomsdayTriggerConfig(
            gpu_failure_threshold=threshold,
            lock_file_path=lock_file
        )
        
        # 模拟Redis返回失败次数
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(side_effect=lambda key: {
            'system:redis_failures': b'0',
            'system:gpu_failures': str(gpu_failures).encode(),
            'portfolio:daily_pnl': b'0',
            'portfolio:initial_capital': b'1000000'
        }.get(key))
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 检查触发条件
        with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', False):
            triggers = switch.check_triggers()
        
        # 验证属性
        if gpu_failures >= threshold:
            assert any('GPU failures' in t for t in triggers)
        else:
            assert not any('GPU failures' in t for t in triggers)
    
    @given(
        daily_pnl=st.floats(min_value=-200000, max_value=100000, allow_nan=False),
        initial_capital=st.floats(min_value=100000, max_value=10000000, allow_nan=False),
        loss_threshold=st.floats(min_value=-0.20, max_value=-0.01, allow_nan=False)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_loss_threshold_trigger(
        self,
        daily_pnl: float,
        initial_capital: float,
        loss_threshold: float,
        tmp_path
    ):
        """Property 11: 亏损阈值触发条件
        
        **Validates: Requirements 4.10, 11.4**
        
        属性: 当单日亏损比率 < 阈值时，应触发末日开关
        """
        lock_file = str(tmp_path / f"lock_loss_{id(daily_pnl)}.lock")
        
        config = DoomsdayTriggerConfig(
            loss_threshold=loss_threshold,
            lock_file_path=lock_file
        )
        
        # 模拟Redis返回盈亏数据
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(side_effect=lambda key: {
            'system:redis_failures': b'0',
            'system:gpu_failures': b'0',
            'portfolio:daily_pnl': str(daily_pnl).encode(),
            'portfolio:initial_capital': str(initial_capital).encode()
        }.get(key))
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 检查触发条件
        with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', False):
            triggers = switch.check_triggers()
        
        # 计算盈亏比率
        pnl_ratio = daily_pnl / initial_capital if initial_capital > 0 else 0
        
        # 验证属性
        if pnl_ratio < loss_threshold:
            assert any('Loss threshold' in t for t in triggers)
        else:
            assert not any('Loss threshold' in t for t in triggers)
    
    @given(
        memory_percent=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        threshold=st.floats(min_value=0.5, max_value=0.99, allow_nan=False)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_memory_critical_trigger(
        self,
        memory_percent: float,
        threshold: float,
        tmp_path
    ):
        """Property 11: 内存临界触发条件
        
        **Validates: Requirements 4.10, 11.4**
        
        属性: 当内存使用率 > 阈值时，应触发末日开关
        """
        lock_file = str(tmp_path / f"lock_mem_{id(memory_percent)}.lock")
        
        config = DoomsdayTriggerConfig(
            memory_critical_threshold=threshold,
            lock_file_path=lock_file
        )
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(return_value=b'0')
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 模拟psutil返回内存使用率
        mock_memory = MagicMock()
        mock_memory.percent = memory_percent * 100
        
        with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', True):
            with patch('src.core.doomsday_switch.psutil') as mock_psutil:
                mock_psutil.virtual_memory.return_value = mock_memory
                mock_psutil.disk_usage.return_value = MagicMock(percent=50)
                
                triggers = switch.check_triggers()
        
        # 验证属性：严格大于阈值才触发
        # 注意：由于浮点数精度问题，使用小的epsilon进行比较
        epsilon = 1e-9
        if memory_percent > threshold + epsilon:
            assert any('Memory critical' in t for t in triggers)
        elif memory_percent < threshold - epsilon:
            assert not any('Memory critical' in t for t in triggers)
        # 当 memory_percent ≈ threshold 时，不做断言（边界情况）


class TestDoomsdayResetProperties:
    """末日开关复位属性测试
    
    **Validates: Requirements 11.6**
    """
    
    @given(
        correct_password=st.text(min_size=4, max_size=20),
        wrong_password=st.text(min_size=4, max_size=20)
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_reset_requires_correct_password(
        self,
        correct_password: str,
        wrong_password: str,
        tmp_path
    ):
        """Property: 复位需要正确密码
        
        **Validates: Requirements 11.6**
        
        属性: 只有正确密码才能复位末日开关
        """
        # 确保密码不同
        if correct_password == wrong_password:
            wrong_password = wrong_password + "_wrong"
        
        lock_file = str(tmp_path / "lock_reset.lock")
        
        config = DoomsdayTriggerConfig(lock_file_path=lock_file)
        
        # 模拟Redis返回正确密码
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(side_effect=lambda key: {
            'config:doomsday:password': correct_password.encode()
        }.get(key))
        mock_redis.delete = MagicMock()
        mock_redis.set = MagicMock()
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 触发末日开关
        switch.trigger("Test trigger")
        assert switch.is_triggered()
        
        # 使用错误密码复位应失败
        result = switch.reset(wrong_password)
        assert result is False
        
        # 使用正确密码复位应成功
        result = switch.reset(correct_password)
        assert result is True
        assert not switch.is_triggered()
    
    def test_reset_clears_lock_file(self, tmp_path):
        """Property: 复位清除锁文件
        
        **Validates: Requirements 11.6**
        
        属性: 成功复位后，锁文件应被删除
        """
        lock_file = tmp_path / "lock_clear.lock"
        
        config = DoomsdayTriggerConfig(lock_file_path=str(lock_file))
        
        mock_redis = MagicMock()
        mock_redis.get = MagicMock(side_effect=lambda key: {
            'config:doomsday:password': b'test_password'
        }.get(key))
        mock_redis.delete = MagicMock()
        mock_redis.set = MagicMock()
        mock_redis.publish = MagicMock()
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 触发末日开关
        switch.trigger("Test trigger")
        assert lock_file.exists()
        
        # 复位
        switch.reset("test_password")
        assert not lock_file.exists()


class TestDoomsdayStatusProperties:
    """末日开关状态属性测试"""
    
    def test_initial_status_not_triggered(self, tmp_path):
        """Property: 初始状态未触发
        
        属性: 新创建的末日开关应处于未触发状态
        """
        lock_file = str(tmp_path / "lock_init.lock")
        
        config = DoomsdayTriggerConfig(lock_file_path=lock_file)
        switch = DoomsdaySwitch(config=config)
        
        assert not switch.is_triggered()
        assert switch.status.trigger_time is None
        assert switch.status.trigger_reason is None
    
    def test_existing_lock_file_means_triggered(self, tmp_path):
        """Property: 存在锁文件表示已触发
        
        属性: 如果锁文件存在，末日开关应处于已触发状态
        """
        lock_file = tmp_path / "lock_exist.lock"
        lock_file.touch()
        
        config = DoomsdayTriggerConfig(lock_file_path=str(lock_file))
        switch = DoomsdaySwitch(config=config)
        
        assert switch.is_triggered()
    
    @given(reason=st.text(min_size=1, max_size=100))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_trigger_records_reason(self, reason: str, tmp_path):
        """Property: 触发记录原因
        
        属性: 触发后应记录触发原因
        """
        lock_file = str(tmp_path / f"lock_reason_{id(reason)}.lock")
        
        config = DoomsdayTriggerConfig(lock_file_path=lock_file)
        
        mock_redis = MagicMock()
        mock_redis.set = MagicMock()
        mock_redis.publish = MagicMock()
        
        switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
        
        # 触发
        switch.trigger(reason)
        
        # 验证原因被记录
        assert switch.status.trigger_reason == reason
        assert switch.status.trigger_time is not None


class TestDoomsdayConfigValidation:
    """末日开关配置验证测试"""
    
    @given(
        redis_threshold=st.integers(min_value=1, max_value=10),
        gpu_threshold=st.integers(min_value=1, max_value=10),
        memory_threshold=st.floats(min_value=0.5, max_value=0.99, allow_nan=False),
        disk_threshold=st.floats(min_value=0.5, max_value=0.99, allow_nan=False),
        loss_threshold=st.floats(min_value=-0.50, max_value=-0.01, allow_nan=False)
    )
    @settings(max_examples=30)
    def test_config_values_preserved(
        self,
        redis_threshold: int,
        gpu_threshold: int,
        memory_threshold: float,
        disk_threshold: float,
        loss_threshold: float
    ):
        """Property: 配置值保持不变
        
        属性: 配置值应正确保存
        """
        config = DoomsdayTriggerConfig(
            redis_failure_threshold=redis_threshold,
            gpu_failure_threshold=gpu_threshold,
            memory_critical_threshold=memory_threshold,
            disk_critical_threshold=disk_threshold,
            loss_threshold=loss_threshold
        )
        
        assert config.redis_failure_threshold == redis_threshold
        assert config.gpu_failure_threshold == gpu_threshold
        assert config.memory_critical_threshold == memory_threshold
        assert config.disk_critical_threshold == disk_threshold
        assert config.loss_threshold == loss_threshold
