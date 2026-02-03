"""DoomsdaySwitch单元测试

白皮书依据: 第十二章 12.3 末日开关与应急响应

测试覆盖:
- 初始化验证
- 触发条件检查
- 触发执行
- 密码复位
- 状态管理
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.core.doomsday_switch import (
    DoomsdaySwitch,
    DoomsdayTriggerType,
    DoomsdayTriggerConfig,
    DoomsdayStatus
)


class TestDoomsdayTriggerType:
    """DoomsdayTriggerType枚举测试"""
    
    def test_trigger_type_values(self):
        """测试触发类型枚举值"""
        assert DoomsdayTriggerType.REDIS_FAILURE.value == "redis_failure"
        assert DoomsdayTriggerType.GPU_FAILURE.value == "gpu_failure"
        assert DoomsdayTriggerType.MEMORY_CRITICAL.value == "memory_critical"
        assert DoomsdayTriggerType.DISK_CRITICAL.value == "disk_critical"
        assert DoomsdayTriggerType.LOSS_THRESHOLD.value == "loss_threshold"
        assert DoomsdayTriggerType.MANUAL.value == "manual"


class TestDoomsdayTriggerConfig:
    """DoomsdayTriggerConfig配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = DoomsdayTriggerConfig()
        
        assert config.redis_failure_threshold == 3
        assert config.gpu_failure_threshold == 3
        assert config.memory_critical_threshold == 0.95
        assert config.disk_critical_threshold == 0.95
        assert config.loss_threshold == -0.10
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = DoomsdayTriggerConfig(
            redis_failure_threshold=5,
            gpu_failure_threshold=5,
            memory_critical_threshold=0.90,
            loss_threshold=-0.05
        )
        
        assert config.redis_failure_threshold == 5
        assert config.gpu_failure_threshold == 5
        assert config.memory_critical_threshold == 0.90
        assert config.loss_threshold == -0.05


class TestDoomsdayStatus:
    """DoomsdayStatus状态测试"""
    
    def test_default_status(self):
        """测试默认状态"""
        status = DoomsdayStatus()
        
        assert status.is_triggered is False
        assert status.trigger_time is None
        assert status.trigger_reason is None
        assert status.triggers_fired == []
    
    def test_triggered_status(self):
        """测试触发状态"""
        now = datetime.now()
        status = DoomsdayStatus(
            is_triggered=True,
            trigger_time=now,
            trigger_reason="Test reason",
            triggers_fired=["Redis failures: 3"]
        )
        
        assert status.is_triggered is True
        assert status.trigger_time == now
        assert status.trigger_reason == "Test reason"
        assert len(status.triggers_fired) == 1


class TestDoomsdaySwitchInit:
    """DoomsdaySwitch初始化测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            assert switch.redis is None
            assert switch.status.is_triggered is False
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            assert switch.redis is mock_redis
    
    def test_init_with_existing_lock_file(self):
        """测试存在锁文件时初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = os.path.join(tmpdir, "test.lock")
            
            # 创建锁文件
            with open(lock_path, 'w') as f:
                f.write("test")
            
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(config=config)
            
            assert switch.status.is_triggered is True


class TestDoomsdaySwitchCheckTriggers:
    """DoomsdaySwitch触发条件检查测试"""
    
    @pytest.fixture
    def switch(self):
        """创建测试用开关"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = None
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            yield DoomsdaySwitch(redis_client=mock_redis, config=config)
    
    def test_check_triggers_none(self, switch):
        """测试无触发条件"""
        switch.redis.get.return_value = 0
        
        with patch.object(switch, '_get_memory_percent', return_value=0.5):
            with patch.object(switch, '_get_disk_percent', return_value=0.5):
                triggers = switch.check_triggers()
        
        assert len(triggers) == 0
    
    def test_check_triggers_redis_failure(self, switch):
        """测试Redis失败触发"""
        def mock_get(key):
            if key == DoomsdaySwitch.REDIS_KEY_REDIS_FAILURES:
                return 5
            return 0
        
        switch.redis.get.side_effect = mock_get
        
        with patch.object(switch, '_get_memory_percent', return_value=0.5):
            with patch.object(switch, '_get_disk_percent', return_value=0.5):
                triggers = switch.check_triggers()
        
        assert any("Redis failures" in t for t in triggers)
    
    def test_check_triggers_gpu_failure(self, switch):
        """测试GPU失败触发"""
        def mock_get(key):
            if key == DoomsdaySwitch.REDIS_KEY_GPU_FAILURES:
                return 5
            return 0
        
        switch.redis.get.side_effect = mock_get
        
        with patch.object(switch, '_get_memory_percent', return_value=0.5):
            with patch.object(switch, '_get_disk_percent', return_value=0.5):
                triggers = switch.check_triggers()
        
        assert any("GPU failures" in t for t in triggers)
    
    def test_check_triggers_memory_critical(self, switch):
        """测试内存临界触发"""
        switch.redis.get.return_value = 0
        
        with patch.object(switch, '_get_memory_percent', return_value=0.98):
            with patch.object(switch, '_get_disk_percent', return_value=0.5):
                triggers = switch.check_triggers()
        
        assert any("Memory critical" in t for t in triggers)
    
    def test_check_triggers_disk_critical(self, switch):
        """测试磁盘临界触发"""
        switch.redis.get.return_value = 0
        
        with patch.object(switch, '_get_memory_percent', return_value=0.5):
            with patch.object(switch, '_get_disk_percent', return_value=0.98):
                triggers = switch.check_triggers()
        
        assert any("Disk critical" in t for t in triggers)
    
    def test_check_triggers_loss_threshold(self, switch):
        """测试亏损阈值触发"""
        def mock_get(key):
            if key == DoomsdaySwitch.REDIS_KEY_DAILY_PNL:
                return -150000
            if key == DoomsdaySwitch.REDIS_KEY_INITIAL_CAPITAL:
                return 1000000
            return 0
        
        switch.redis.get.side_effect = mock_get
        
        with patch.object(switch, '_get_memory_percent', return_value=0.5):
            with patch.object(switch, '_get_disk_percent', return_value=0.5):
                triggers = switch.check_triggers()
        
        assert any("Loss threshold" in t for t in triggers)


class TestDoomsdaySwitchTrigger:
    """DoomsdaySwitch触发测试"""
    
    def test_trigger(self):
        """测试触发末日开关"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            switch.trigger("Test reason")
            
            assert switch.status.is_triggered is True
            assert switch.status.trigger_reason == "Test reason"
            assert switch.status.trigger_time is not None
            assert Path(config.lock_file_path).exists()
            mock_redis.set.assert_called()
    
    def test_trigger_creates_lock_file(self):
        """测试触发创建锁文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = os.path.join(tmpdir, "subdir", "test.lock")
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(config=config)
            
            switch.trigger("Test reason")
            
            assert Path(lock_path).exists()
            
            # 验证锁文件内容
            with open(lock_path, 'r') as f:
                content = f.read()
                assert "Test reason" in content


class TestDoomsdaySwitchReset:
    """DoomsdaySwitch复位测试"""
    
    def test_reset_success(self):
        """测试成功复位"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = "correct_password"
            
            lock_path = os.path.join(tmpdir, "test.lock")
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 先触发
            switch.trigger("Test reason")
            assert switch.status.is_triggered is True
            
            # 复位
            result = switch.reset("correct_password")
            
            assert result is True
            assert switch.status.is_triggered is False
            assert not Path(lock_path).exists()
    
    def test_reset_wrong_password(self):
        """测试错误密码复位"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = "correct_password"
            
            lock_path = os.path.join(tmpdir, "test.lock")
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 先触发
            switch.trigger("Test reason")
            
            # 尝试用错误密码复位
            result = switch.reset("wrong_password")
            
            assert result is False
            assert switch.status.is_triggered is True
    
    def test_reset_no_lock_file(self):
        """测试无锁文件时复位"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = "password"
            
            lock_path = os.path.join(tmpdir, "test.lock")
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 不触发，直接复位
            result = switch.reset("password")
            
            assert result is True


class TestDoomsdaySwitchIsTriggered:
    """DoomsdaySwitch触发状态检查测试"""
    
    def test_is_triggered_false(self):
        """测试未触发状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            assert switch.is_triggered() is False
    
    def test_is_triggered_by_status(self):
        """测试通过状态判断触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            switch.status.is_triggered = True
            
            assert switch.is_triggered() is True
    
    def test_is_triggered_by_lock_file(self):
        """测试通过锁文件判断触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = os.path.join(tmpdir, "test.lock")
            
            # 创建锁文件
            with open(lock_path, 'w') as f:
                f.write("test")
            
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(config=config)
            
            assert switch.is_triggered() is True


class TestDoomsdaySwitchGetters:
    """DoomsdaySwitch getter方法测试"""
    
    def test_get_status(self):
        """测试获取状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            switch.status.is_triggered = True
            
            status = switch.get_status()
            
            assert status.is_triggered is True


class TestDoomsdaySwitchInternalMethods:
    """DoomsdaySwitch内部方法测试"""
    
    def test_get_redis_failures_no_redis(self):
        """测试无Redis时获取失败次数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            result = switch._get_redis_failures()
            
            assert result == 0
    
    def test_get_redis_failures_with_redis(self):
        """测试有Redis时获取失败次数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = 5
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_redis_failures()
            
            assert result == 5
    
    def test_get_gpu_failures_no_redis(self):
        """测试无Redis时获取GPU失败次数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            result = switch._get_gpu_failures()
            
            assert result == 0
    
    def test_get_memory_percent_no_psutil(self):
        """测试无psutil时获取内存使用率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', False):
                result = switch._get_memory_percent()
            
            assert result == 0.0
    
    def test_get_disk_percent_no_psutil(self):
        """测试无psutil时获取磁盘使用率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', False):
                result = switch._get_disk_percent()
            
            assert result == 0.0
    
    def test_get_pnl_ratio_no_redis(self):
        """测试无Redis时获取盈亏比率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            result = switch._get_pnl_ratio()
            
            assert result == 0.0
    
    def test_get_pnl_ratio_with_redis(self):
        """测试有Redis时获取盈亏比率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            
            def mock_get(key):
                if key == DoomsdaySwitch.REDIS_KEY_DAILY_PNL:
                    return -50000
                if key == DoomsdaySwitch.REDIS_KEY_INITIAL_CAPITAL:
                    return 1000000
                return None
            
            mock_redis.get.side_effect = mock_get
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_pnl_ratio()
            
            assert result == pytest.approx(-0.05, rel=0.01)
    
    def test_get_reset_password_no_redis(self):
        """测试无Redis时获取复位密码"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            result = switch._get_reset_password()
            
            assert result is None
    
    def test_get_reset_password_bytes(self):
        """测试获取字节类型密码"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = b"password123"
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_reset_password()
            
            assert result == "password123"


class TestDoomsdaySwitchRedisIntegration:
    """DoomsdaySwitch Redis集成测试"""
    
    def test_update_redis_status(self):
        """测试更新Redis状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            switch._update_redis_status("Test reason")
            
            mock_redis.set.assert_any_call(
                DoomsdaySwitch.REDIS_KEY_DOOMSDAY,
                'triggered'
            )
    
    def test_update_redis_status_no_redis(self):
        """测试无Redis时更新状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            # 不应抛出异常
            switch._update_redis_status("Test reason")
    
    def test_stop_trading(self):
        """测试停止交易"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            switch._stop_trading()
            
            mock_redis.publish.assert_called_with(
                'trading:emergency_stop',
                'doomsday'
            )
    
    def test_stop_trading_no_redis(self):
        """测试无Redis时停止交易"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            # 不应抛出异常
            switch._stop_trading()


class TestDoomsdaySwitchLiquidation:
    """DoomsdaySwitch清仓测试"""
    
    def test_should_liquidate_true(self):
        """测试需要清仓"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            
            def mock_get(key):
                if key == DoomsdaySwitch.REDIS_KEY_DAILY_PNL:
                    return -200000  # -20%
                if key == DoomsdaySwitch.REDIS_KEY_INITIAL_CAPITAL:
                    return 1000000
                return None
            
            mock_redis.get.side_effect = mock_get
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._should_liquidate()
            
            assert result is True
    
    def test_should_liquidate_false(self):
        """测试不需要清仓"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            
            def mock_get(key):
                if key == DoomsdaySwitch.REDIS_KEY_DAILY_PNL:
                    return -50000  # -5%
                if key == DoomsdaySwitch.REDIS_KEY_INITIAL_CAPITAL:
                    return 1000000
                return None
            
            mock_redis.get.side_effect = mock_get
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._should_liquidate()
            
            assert result is False
    
    def test_emergency_liquidate(self):
        """测试紧急清仓"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            switch._emergency_liquidate()
            
            mock_redis.publish.assert_called_with(
                'trading:liquidate_all',
                'emergency'
            )
    
    def test_emergency_liquidate_no_redis(self):
        """测试无Redis时紧急清仓"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            # 不应抛出异常
            switch._emergency_liquidate()


class TestDoomsdaySwitchAlert:
    """DoomsdaySwitch告警测试"""
    
    def test_send_alert(self):
        """测试发送告警"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            # 不应抛出异常
            switch._send_alert("Test alert")



class TestDoomsdaySwitchPsutilIntegration:
    """DoomsdaySwitch psutil集成测试"""
    
    def test_get_memory_percent_with_psutil(self):
        """测试有psutil时获取内存使用率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', True):
                mock_memory = Mock()
                mock_memory.percent = 75.0
                with patch('src.core.doomsday_switch.psutil.virtual_memory', return_value=mock_memory):
                    result = switch._get_memory_percent()
            
            assert result == pytest.approx(0.75, rel=0.01)
    
    def test_get_memory_percent_exception(self):
        """测试获取内存使用率异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', True):
                with patch('src.core.doomsday_switch.psutil.virtual_memory', side_effect=Exception("Error")):
                    result = switch._get_memory_percent()
            
            assert result == 0.0
    
    def test_get_disk_percent_with_psutil(self):
        """测试有psutil时获取磁盘使用率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock"),
                disk_path=tmpdir
            )
            switch = DoomsdaySwitch(config=config)
            
            with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', True):
                mock_disk = Mock()
                mock_disk.percent = 80.0
                with patch('src.core.doomsday_switch.psutil.disk_usage', return_value=mock_disk):
                    result = switch._get_disk_percent()
            
            assert result == pytest.approx(0.80, rel=0.01)
    
    def test_get_disk_percent_exception(self):
        """测试获取磁盘使用率异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(config=config)
            
            with patch('src.core.doomsday_switch.PSUTIL_AVAILABLE', True):
                with patch('src.core.doomsday_switch.psutil.disk_usage', side_effect=Exception("Error")):
                    result = switch._get_disk_percent()
            
            assert result == 0.0


class TestDoomsdaySwitchRedisExceptions:
    """DoomsdaySwitch Redis异常测试"""
    
    def test_get_redis_failures_exception(self):
        """测试获取Redis失败次数异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_redis_failures()
            
            assert result == 0
    
    def test_get_gpu_failures_with_redis(self):
        """测试有Redis时获取GPU失败次数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = 3
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_gpu_failures()
            
            assert result == 3
    
    def test_get_gpu_failures_exception(self):
        """测试获取GPU失败次数异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_gpu_failures()
            
            assert result == 0
    
    def test_get_pnl_ratio_exception(self):
        """测试获取盈亏比率异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_pnl_ratio()
            
            assert result == 0.0
    
    def test_get_reset_password_exception(self):
        """测试获取复位密码异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            result = switch._get_reset_password()
            
            assert result is None
    
    def test_update_redis_status_exception(self):
        """测试更新Redis状态异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.set.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 不应抛出异常
            switch._update_redis_status("Test reason")
    
    def test_stop_trading_exception(self):
        """测试停止交易异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.publish.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 不应抛出异常
            switch._stop_trading()
    
    def test_emergency_liquidate_exception(self):
        """测试紧急清仓异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.publish.side_effect = Exception("Redis error")
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 不应抛出异常
            switch._emergency_liquidate()
    
    def test_reset_redis_exception(self):
        """测试复位时Redis异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            mock_redis.get.return_value = "password"
            mock_redis.delete.side_effect = Exception("Redis error")
            
            lock_path = os.path.join(tmpdir, "test.lock")
            config = DoomsdayTriggerConfig(lock_file_path=lock_path)
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            # 先触发
            switch.trigger("Test reason")
            
            # 复位应该成功（即使Redis出错）
            result = switch.reset("password")
            
            assert result is True


class TestDoomsdaySwitchLockFileExceptions:
    """DoomsdaySwitch锁文件异常测试"""
    
    def test_create_lock_file_exception(self):
        """测试创建锁文件异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用无效路径
            config = DoomsdayTriggerConfig(
                lock_file_path="/invalid/path/that/does/not/exist/test.lock"
            )
            switch = DoomsdaySwitch(config=config)
            
            # 不应抛出异常
            switch._create_lock_file("Test reason")


class TestDoomsdaySwitchTriggerWithLiquidation:
    """DoomsdaySwitch触发清仓测试"""
    
    def test_trigger_with_liquidation(self):
        """测试触发时需要清仓"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_redis = Mock()
            
            def mock_get(key):
                if key == DoomsdaySwitch.REDIS_KEY_DAILY_PNL:
                    return -200000  # -20%
                if key == DoomsdaySwitch.REDIS_KEY_INITIAL_CAPITAL:
                    return 1000000
                return None
            
            mock_redis.get.side_effect = mock_get
            config = DoomsdayTriggerConfig(
                lock_file_path=os.path.join(tmpdir, "test.lock")
            )
            switch = DoomsdaySwitch(redis_client=mock_redis, config=config)
            
            switch.trigger("Severe loss")
            
            # 验证清仓信号被发送
            mock_redis.publish.assert_any_call('trading:liquidate_all', 'emergency')
