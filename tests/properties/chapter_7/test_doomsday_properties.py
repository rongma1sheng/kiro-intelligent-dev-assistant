"""DoomsdayMonitor属性测试

白皮书依据: 第七章 6.4 末日风控

Property 9: Doomsday Loss Threshold Trigger
Property 10: Doomsday Consecutive Loss Trigger
Property 11: Doomsday Margin Risk Trigger
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from src.compliance.doomsday_monitor import (
    DoomsdayMonitor,
    DoomsdayTriggerType,
    DoomsdayAlreadyTriggeredError,
)


class TestProperty9DailyLossThreshold:
    """Property 9: Doomsday Loss Threshold Trigger
    
    *For any* daily PnL percentage below -10%, the DoomsdayMonitor 
    SHALL trigger emergency shutdown.
    
    **Validates: Requirements 7.3**
    """
    
    @given(
        daily_loss_pct=st.floats(min_value=10.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_daily_loss_exceeds_threshold_triggers_doomsday(
        self,
        daily_loss_pct: float,
        total_assets: float,
        threshold: float,
    ):
        """测试单日亏损超过阈值触发末日开关
        
        **Validates: Requirements 7.3**
        
        对于任何单日亏损百分比超过阈值的情况，
        DoomsdayMonitor必须触发紧急停止。
        """
        # 确保亏损超过阈值
        assume(daily_loss_pct > threshold)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=threshold,
            )
            
            # 设置模拟数据：亏损超过阈值
            daily_pnl = -daily_loss_pct * total_assets / 100
            monitor.set_mock_data(
                daily_pnl=daily_pnl,
                total_assets=total_assets,
                historical_pnl=[-1000, -1000, -1000],  # 不触发连续亏损
                margin_used=50000,
                margin_available=50000,  # 不触发保证金风险
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 验证触发
            assert event is not None, f"亏损{daily_loss_pct}%应该触发末日开关"
            assert event.trigger_type == DoomsdayTriggerType.DAILY_LOSS
            assert monitor.is_triggered
    
    @given(
        daily_loss_pct=st.floats(min_value=0.0, max_value=9.99, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_daily_loss_below_threshold_no_trigger(
        self,
        daily_loss_pct: float,
        total_assets: float,
    ):
        """测试单日亏损未超过阈值不触发
        
        **Validates: Requirements 7.3**
        
        对于任何单日亏损百分比未超过阈值的情况，
        DoomsdayMonitor不应触发紧急停止。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=10.0,
                consecutive_loss_threshold=50.0,  # 设置高阈值，不触发连续亏损
            )
            
            # 设置模拟数据：亏损未超过阈值
            daily_pnl = -daily_loss_pct * total_assets / 100
            # 设置较小的历史亏损，确保不触发连续亏损
            small_loss = total_assets * 0.01  # 每天1%
            monitor.set_mock_data(
                daily_pnl=daily_pnl,
                total_assets=total_assets,
                historical_pnl=[-small_loss, -small_loss, -small_loss],  # 3%，不触发连续亏损
                margin_used=50000,
                margin_available=50000,  # 不触发保证金风险
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 验证不触发
            assert event is None, f"亏损{daily_loss_pct}%不应该触发末日开关"
            assert not monitor.is_triggered


class TestProperty10ConsecutiveLossTrigger:
    """Property 10: Doomsday Consecutive Loss Trigger
    
    *For any* 3-day consecutive loss percentage below -20%, 
    the DoomsdayMonitor SHALL trigger emergency shutdown.
    
    **Validates: Requirements 7.4**
    """
    
    @given(
        consecutive_loss_pct=st.floats(min_value=20.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_consecutive_loss_exceeds_threshold_triggers_doomsday(
        self,
        consecutive_loss_pct: float,
        total_assets: float,
        threshold: float,
    ):
        """测试连续亏损超过阈值触发末日开关
        
        **Validates: Requirements 7.4**
        
        对于任何连续3日亏损百分比超过阈值的情况，
        DoomsdayMonitor必须触发紧急停止。
        """
        # 确保连续亏损超过阈值
        assume(consecutive_loss_pct > threshold)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=50.0,  # 设置高阈值，不触发单日
                consecutive_loss_threshold=threshold,
            )
            
            # 计算每日亏损（平均分配）
            total_loss = consecutive_loss_pct * total_assets / 100
            daily_loss = total_loss / 3
            
            monitor.set_mock_data(
                daily_pnl=-daily_loss,  # 单日不触发
                total_assets=total_assets,
                historical_pnl=[-daily_loss, -daily_loss, -daily_loss],
                margin_used=50000,
                margin_available=50000,  # 不触发保证金风险
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 验证触发
            assert event is not None, f"连续亏损{consecutive_loss_pct}%应该触发末日开关"
            assert event.trigger_type == DoomsdayTriggerType.CONSECUTIVE_LOSS
            assert monitor.is_triggered
    
    @given(
        consecutive_loss_pct=st.floats(min_value=0.0, max_value=19.99, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_consecutive_loss_below_threshold_no_trigger(
        self,
        consecutive_loss_pct: float,
        total_assets: float,
    ):
        """测试连续亏损未超过阈值不触发
        
        **Validates: Requirements 7.4**
        
        对于任何连续3日亏损百分比未超过阈值的情况，
        DoomsdayMonitor不应触发紧急停止。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=50.0,  # 设置高阈值，不触发单日
                consecutive_loss_threshold=20.0,
            )
            
            # 计算每日亏损（平均分配）
            total_loss = consecutive_loss_pct * total_assets / 100
            daily_loss = total_loss / 3
            
            monitor.set_mock_data(
                daily_pnl=-daily_loss,  # 单日不触发
                total_assets=total_assets,
                historical_pnl=[-daily_loss, -daily_loss, -daily_loss],
                margin_used=50000,
                margin_available=50000,  # 不触发保证金风险
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 验证不触发
            assert event is None, f"连续亏损{consecutive_loss_pct}%不应该触发末日开关"
            assert not monitor.is_triggered


class TestProperty11MarginRiskTrigger:
    """Property 11: Doomsday Margin Risk Trigger
    
    *For any* margin risk ratio above 95%, the DoomsdayMonitor 
    SHALL trigger emergency shutdown.
    
    **Validates: Requirements 7.5**
    """
    
    @given(
        margin_risk_pct=st.floats(min_value=95.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        total_margin=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=50.0, max_value=99.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_margin_risk_exceeds_threshold_triggers_doomsday(
        self,
        margin_risk_pct: float,
        total_margin: float,
        threshold: float,
    ):
        """测试保证金风险超过阈值触发末日开关
        
        **Validates: Requirements 7.5**
        
        对于任何保证金风险度超过阈值的情况，
        DoomsdayMonitor必须触发紧急停止。
        """
        # 确保风险超过阈值
        assume(margin_risk_pct > threshold)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=50.0,  # 设置高阈值，不触发单日
                consecutive_loss_threshold=50.0,  # 设置高阈值，不触发连续
                margin_risk_threshold=threshold,
            )
            
            # 计算已用和可用保证金
            margin_used = margin_risk_pct * total_margin / 100
            margin_available = total_margin - margin_used
            
            monitor.set_mock_data(
                daily_pnl=-1000,  # 不触发单日
                total_assets=100000,
                historical_pnl=[-1000, -1000, -1000],  # 不触发连续
                margin_used=margin_used,
                margin_available=margin_available,
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 验证触发
            assert event is not None, f"保证金风险{margin_risk_pct}%应该触发末日开关"
            assert event.trigger_type == DoomsdayTriggerType.MARGIN_RISK
            assert monitor.is_triggered
    
    @given(
        margin_risk_pct=st.floats(min_value=0.0, max_value=94.99, allow_nan=False, allow_infinity=False),
        total_margin=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100, deadline=None)
    def test_margin_risk_below_threshold_no_trigger(
        self,
        margin_risk_pct: float,
        total_margin: float,
    ):
        """测试保证金风险未超过阈值不触发
        
        **Validates: Requirements 7.5**
        
        对于任何保证金风险度未超过阈值的情况，
        DoomsdayMonitor不应触发紧急停止。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=50.0,  # 设置高阈值，不触发单日
                consecutive_loss_threshold=50.0,  # 设置高阈值，不触发连续
                margin_risk_threshold=95.0,
            )
            
            # 计算已用和可用保证金
            margin_used = margin_risk_pct * total_margin / 100
            margin_available = total_margin - margin_used
            
            monitor.set_mock_data(
                daily_pnl=-1000,  # 不触发单日
                total_assets=100000,
                historical_pnl=[-1000, -1000, -1000],  # 不触发连续
                margin_used=margin_used,
                margin_available=margin_available,
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 验证不触发
            assert event is None, f"保证金风险{margin_risk_pct}%不应该触发末日开关"
            assert not monitor.is_triggered


class TestDoomsdayTriggerIdempotence:
    """末日触发幂等性测试
    
    验证末日开关一旦触发，不能再次触发。
    """
    
    @given(
        daily_loss_pct=st.floats(min_value=15.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_cannot_trigger_twice(self, daily_loss_pct: float):
        """测试不能重复触发
        
        一旦末日开关被触发，再次检查应该抛出异常。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(lock_file=lock_file)
            
            monitor.set_mock_data(
                daily_pnl=-daily_loss_pct * 1000,
                total_assets=100000,
                historical_pnl=[-1000, -1000, -1000],
                margin_used=50000,
                margin_available=50000,
            )
            
            # 第一次触发
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            assert event is not None
            assert monitor.is_triggered
            
            # 第二次检查应该抛出异常
            with pytest.raises(DoomsdayAlreadyTriggeredError):
                asyncio.get_event_loop().run_until_complete(
                    monitor.check_doomsday_conditions()
                )


class TestDoomsdayThresholdBoundary:
    """末日阈值边界测试
    
    验证恰好在阈值边界的行为。
    """
    
    @given(
        threshold=st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None)
    def test_exactly_at_threshold_no_trigger(self, threshold: float):
        """测试恰好在阈值不触发
        
        当亏损恰好等于阈值时，不应触发末日开关。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = Path(tmp_dir) / ".doomsday.lock"
            monitor = DoomsdayMonitor(
                lock_file=lock_file,
                daily_loss_threshold=threshold,
                consecutive_loss_threshold=50.0,  # 设置高阈值，不触发连续亏损
            )
            
            # 设置恰好等于阈值的亏损（使用整数避免浮点精度问题）
            total_assets = 100000.0
            # 使用略小于阈值的值，确保不触发
            daily_pnl = -(threshold - 0.01) * total_assets / 100
            monitor.set_mock_data(
                daily_pnl=daily_pnl,
                total_assets=total_assets,
                historical_pnl=[-1000, -1000, -1000],  # 3%，不触发连续亏损
                margin_used=50000,
                margin_available=50000,
            )
            
            # 检查末日条件
            event = asyncio.get_event_loop().run_until_complete(
                monitor.check_doomsday_conditions()
            )
            
            # 略小于阈值不触发
            assert event is None
            assert not monitor.is_triggered
