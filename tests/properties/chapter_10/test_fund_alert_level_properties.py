"""Property-based tests for fund alert level monotonicity

白皮书依据: 第十章 10.2 资金监控系统
Property 6: Fund Alert Level Monotonicity
Validates: Requirements 2.6, 2.7, 2.8

测试资金告警级别的单调性：告警级别应随损失严重程度单调递增。
"""

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck

from src.core.fund_monitor import FundMonitor, AlertLevel


class TestFundAlertLevelProperties:
    """Property tests for fund alert level monotonicity
    
    白皮书依据: 第十章 10.2 资金监控系统
    Property 6: Fund Alert Level Monotonicity
    """
    
    @pytest.mark.property
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
    @given(
        loss_pct_1=st.floats(min_value=-20.0, max_value=10.0),
        loss_pct_2=st.floats(min_value=-20.0, max_value=10.0),
        drawdown_1=st.floats(min_value=0.0, max_value=30.0),
        drawdown_2=st.floats(min_value=0.0, max_value=30.0)
    )
    def test_property_alert_level_monotonicity(
        self,
        loss_pct_1: float,
        loss_pct_2: float,
        drawdown_1: float,
        drawdown_2: float
    ):
        """Property: Alert level increases with loss severity
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.6, 2.7, 2.8
        
        For any two scenarios where scenario 2 is strictly worse than scenario 1
        (either more loss OR more drawdown), the alert level for scenario 2
        should be greater than or equal to the alert level for scenario 1.
        
        Note: loss_pct is percentage value (e.g., -3.0 for -3%), drawdown is percentage value
        
        Args:
            loss_pct_1: First loss percentage (-20.0 to +10.0)
            loss_pct_2: Second loss percentage (-20.0 to +10.0)
            drawdown_1: First drawdown (0.0 to 30.0)
            drawdown_2: Second drawdown (0.0 to 30.0)
        """
        # Ensure scenario 2 is strictly worse: more loss AND more drawdown
        # (both conditions must be worse or equal, with at least one strictly worse)
        assume(loss_pct_2 <= loss_pct_1 and drawdown_2 >= drawdown_1)
        assume(loss_pct_2 < loss_pct_1 or drawdown_2 > drawdown_1)
        
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Execute: Determine alert levels
        level_1 = fund_monitor.determine_alert_level(loss_pct_1, drawdown_1)
        level_2 = fund_monitor.determine_alert_level(loss_pct_2, drawdown_2)
        
        # Define alert level ordering
        alert_order = {
            AlertLevel.NORMAL: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.DANGER: 2,
            AlertLevel.CRITICAL: 3
        }
        
        # Verify: Level should increase or stay same with worse conditions
        assert alert_order[level_2] >= alert_order[level_1], (
            f"Alert level decreased with worse conditions: "
            f"L1({loss_pct_1:.2f}%, {drawdown_1:.1f}%)={level_1.value}, "
            f"L2({loss_pct_2:.2f}%, {drawdown_2:.1f}%)={level_2.value}"
        )
    
    @pytest.mark.property
    @settings(max_examples=50, deadline=None)
    @given(
        loss_pct=st.floats(min_value=-20.0, max_value=10.0)
    )
    def test_property_threshold_boundaries_loss(
        self,
        loss_pct: float
    ):
        """Property: Alert levels respect loss threshold boundaries
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.6, 2.7, 2.8
        
        Thresholds (using > not >=):
        - WARNING: >3% loss
        - DANGER: >5% loss
        - CRITICAL: >8% loss
        
        Args:
            loss_pct: Loss percentage value (-20.0 to +10.0)
        """
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Execute: Determine alert level
        level = fund_monitor.determine_alert_level(loss_pct, drawdown=0.0)
        
        # Convert loss_pct (percentage value) to positive loss value for comparison
        # loss_pct is percentage value (e.g., -3.0 for -3%)
        loss_value = -loss_pct if loss_pct < 0 else 0
        
        # Verify: Level matches expected threshold (using > not >=)
        if loss_value <= 3.0:  # <=3% loss
            assert level == AlertLevel.NORMAL, (
                f"Expected NORMAL for {loss_pct:.2f}% loss (loss_value={loss_value:.2f}), got {level.value}"
            )
        elif loss_value <= 5.0:  # >3% and <=5% loss
            assert level == AlertLevel.WARNING, (
                f"Expected WARNING for {loss_pct:.2f}% loss (loss_value={loss_value:.2f}), got {level.value}"
            )
        elif loss_value <= 8.0:  # >5% and <=8% loss
            assert level == AlertLevel.DANGER, (
                f"Expected DANGER for {loss_pct:.2f}% loss (loss_value={loss_value:.2f}), got {level.value}"
            )
        else:  # >8% loss
            assert level == AlertLevel.CRITICAL, (
                f"Expected CRITICAL for {loss_pct:.2f}% loss (loss_value={loss_value:.2f}), got {level.value}"
            )
    
    @pytest.mark.property
    @settings(max_examples=50, deadline=None)
    @given(
        drawdown=st.floats(min_value=0.0, max_value=30.0)
    )
    def test_property_threshold_boundaries_drawdown(
        self,
        drawdown: float
    ):
        """Property: Alert levels respect drawdown threshold boundaries
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.6, 2.7, 2.8
        
        Thresholds (using > not >=):
        - WARNING: >10% drawdown
        - DANGER: >15% drawdown
        - CRITICAL: >20% drawdown
        
        Note: drawdown parameter is percentage value (e.g., 10.0 for 10%)
        
        Args:
            drawdown: Drawdown percentage value (0.0 to 30.0)
        """
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Execute: Determine alert level (no daily loss)
        level = fund_monitor.determine_alert_level(daily_pnl_pct=0.0, drawdown=drawdown)
        
        # Verify: Level matches expected threshold (using > not >=)
        if drawdown <= 10.0:  # <=10% drawdown
            assert level == AlertLevel.NORMAL, (
                f"Expected NORMAL for {drawdown:.1f}% drawdown, got {level.value}"
            )
        elif drawdown <= 15.0:  # >10% and <=15% drawdown
            assert level == AlertLevel.WARNING, (
                f"Expected WARNING for {drawdown:.1f}% drawdown, got {level.value}"
            )
        elif drawdown <= 20.0:  # >15% and <=20% drawdown
            assert level == AlertLevel.DANGER, (
                f"Expected DANGER for {drawdown:.1f}% drawdown, got {level.value}"
            )
        else:  # >20% drawdown
            assert level == AlertLevel.CRITICAL, (
                f"Expected CRITICAL for {drawdown:.1f}% drawdown, got {level.value}"
            )
    
    @pytest.mark.property
    @settings(max_examples=50, deadline=None)
    @given(
        loss_pct=st.floats(min_value=-20.0, max_value=10.0),
        drawdown=st.floats(min_value=0.0, max_value=30.0)
    )
    def test_property_alert_level_takes_maximum(
        self,
        loss_pct: float,
        drawdown: float
    ):
        """Property: Alert level is maximum of loss and drawdown levels
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.6, 2.7, 2.8
        
        When both loss and drawdown trigger alerts, the system should
        use the higher (more severe) alert level.
        
        Args:
            loss_pct: Loss percentage value (-20.0 to +10.0)
            drawdown: Drawdown percentage value (0.0 to 30.0)
        """
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Execute: Determine alert levels
        combined_level = fund_monitor.determine_alert_level(loss_pct, drawdown)
        loss_only_level = fund_monitor.determine_alert_level(loss_pct, 0.0)
        drawdown_only_level = fund_monitor.determine_alert_level(0.0, drawdown)
        
        # Define alert level ordering
        alert_order = {
            AlertLevel.NORMAL: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.DANGER: 2,
            AlertLevel.CRITICAL: 3
        }
        
        # Verify: Combined level should be max of individual levels
        expected_level_value = max(
            alert_order[loss_only_level],
            alert_order[drawdown_only_level]
        )
        actual_level_value = alert_order[combined_level]
        
        assert actual_level_value == expected_level_value, (
            f"Combined level {combined_level.value} (value={actual_level_value}) "
            f"not maximum of loss level {loss_only_level.value} "
            f"(value={alert_order[loss_only_level]}) and "
            f"drawdown level {drawdown_only_level.value} "
            f"(value={alert_order[drawdown_only_level]})"
        )
    
    @pytest.mark.property
    def test_property_exact_threshold_boundaries(self):
        """Property: Exact threshold values produce correct alert levels
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.6, 2.7, 2.8
        
        Test exact threshold values to ensure boundary conditions
        are handled correctly.
        
        Note: FundMonitor expects loss_pct as percentage value (e.g., -3.0 for -3%)
        Thresholds use > not >=.
        """
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Test exact loss thresholds
        # Note: Thresholds use > not >=, so exactly 3% is NORMAL, >3% is WARNING
        test_cases = [
            # (loss_pct, drawdown, expected_level)
            (-3.0, 0.0, AlertLevel.NORMAL),    # Exactly 3% loss (not >3%)
            (-4.0, 0.0, AlertLevel.WARNING),   # 4% loss (>3%)
            (-5.0, 0.0, AlertLevel.WARNING),   # Exactly 5% loss (not >5%)
            (-6.0, 0.0, AlertLevel.DANGER),    # 6% loss (>5%)
            (-8.0, 0.0, AlertLevel.DANGER),    # Exactly 8% loss (not >8%)
            (-9.0, 0.0, AlertLevel.CRITICAL),  # 9% loss (>8%)
            (0.0, 10.0, AlertLevel.NORMAL),     # Exactly 10% drawdown (not >10%)
            (0.0, 11.0, AlertLevel.WARNING),    # 11% drawdown (>10%)
            (0.0, 15.0, AlertLevel.WARNING),    # Exactly 15% drawdown (not >15%)
            (0.0, 16.0, AlertLevel.DANGER),     # 16% drawdown (>15%)
            (0.0, 20.0, AlertLevel.DANGER),     # Exactly 20% drawdown (not >20%)
            (0.0, 21.0, AlertLevel.CRITICAL),   # 21% drawdown (>20%)
            (-2.9, 0.0, AlertLevel.NORMAL),   # Just below 3% loss
        ]
        
        for loss_pct, drawdown, expected_level in test_cases:
            level = fund_monitor.determine_alert_level(loss_pct, drawdown)
            assert level == expected_level, (
                f"For loss={loss_pct:.2f}%, drawdown={drawdown:.1f}%: "
                f"expected {expected_level.value}, got {level.value}"
            )
    
    @pytest.mark.property
    @settings(max_examples=50, deadline=None)
    @given(
        loss_pct=st.floats(min_value=-20.0, max_value=-8.0)
    )
    def test_property_critical_loss_always_critical(
        self,
        loss_pct: float
    ):
        """Property: Loss >8% always triggers CRITICAL alert
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.8
        
        Any loss exceeding 8% should always result in CRITICAL alert,
        regardless of drawdown.
        
        Args:
            loss_pct: Loss percentage value (-20.0 to -8.0)
        """
        # Ensure loss > 8% (loss_pct < -8.0)
        assume(loss_pct < -8.0)
        
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Execute: Test with various drawdowns
        for drawdown in [0.0, 5.0, 10.0, 15.0, 20.0]:
            level = fund_monitor.determine_alert_level(loss_pct, drawdown)
            
            # Verify: Should always be CRITICAL
            assert level == AlertLevel.CRITICAL, (
                f"Loss {loss_pct:.2f}% with drawdown {drawdown:.1f}% "
                f"should be CRITICAL, got {level.value}"
            )
    
    @pytest.mark.property
    @settings(max_examples=50, deadline=None)
    @given(
        drawdown=st.floats(min_value=20.0, max_value=30.0)
    )
    def test_property_critical_drawdown_always_critical(
        self,
        drawdown: float
    ):
        """Property: Drawdown >20% always triggers CRITICAL alert
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.8
        
        Any drawdown exceeding 20% should always result in CRITICAL alert,
        regardless of daily loss.
        
        Args:
            drawdown: Drawdown percentage value (20.0 to 30.0 for 20%-30%)
        """
        # Ensure drawdown > 20%
        assume(drawdown > 20.0)
        
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Execute: Test with various loss percentages
        for loss_pct in [0.0, -2.0, -4.0, -6.0, -8.0]:
            level = fund_monitor.determine_alert_level(loss_pct, drawdown)
            
            # Verify: Should always be CRITICAL
            assert level == AlertLevel.CRITICAL, (
                f"Drawdown {drawdown:.1f}% with loss {loss_pct:.2f}% "
                f"should be CRITICAL, got {level.value}"
            )


class TestFundAlertLevelIntegration:
    """Integration tests for fund alert levels
    
    白皮书依据: 第十章 10.2 资金监控系统
    """
    
    @pytest.mark.integration
    def test_integration_alert_level_progression(self):
        """Integration: Alert level progression through thresholds
        
        白皮书依据: 第十章 10.2 资金监控系统
        Property 6: Fund Alert Level Monotonicity
        Validates: Requirements 2.6, 2.7, 2.8
        
        Test complete progression from NORMAL through WARNING, DANGER,
        to CRITICAL as losses increase.
        """
        # Setup: Create fund monitor
        fund_monitor = FundMonitor(
            initial_equity=100000.0,
            check_interval=60
        )
        
        # Test progression of loss percentages
        # Note: Thresholds use > not >=, so exactly 3% is NORMAL, >3% is WARNING
        test_sequence = [
            (0.0, AlertLevel.NORMAL),
            (-2.0, AlertLevel.NORMAL),
            (-3.0, AlertLevel.NORMAL),      # Exactly 3% loss (not >3%)
            (-4.0, AlertLevel.WARNING),     # 4% loss (>3%)
            (-5.0, AlertLevel.WARNING),     # Exactly 5% loss (not >5%)
            (-6.0, AlertLevel.DANGER),      # 6% loss (>5%)
            (-8.0, AlertLevel.DANGER),      # Exactly 8% loss (not >8%)
            (-9.0, AlertLevel.CRITICAL),    # 9% loss (>8%)
            (-10.0, AlertLevel.CRITICAL),
        ]
        
        previous_level_value = -1
        alert_order = {
            AlertLevel.NORMAL: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.DANGER: 2,
            AlertLevel.CRITICAL: 3
        }
        
        for loss_pct, expected_level in test_sequence:
            level = fund_monitor.determine_alert_level(loss_pct, drawdown=0.0)
            
            # Verify: Level matches expected
            assert level == expected_level, (
                f"For loss {loss_pct:.2f}%: expected {expected_level.value}, "
                f"got {level.value}"
            )
            
            # Verify: Level never decreases
            current_level_value = alert_order[level]
            assert current_level_value >= previous_level_value, (
                f"Alert level decreased from {previous_level_value} to {current_level_value}"
            )
            previous_level_value = current_level_value
