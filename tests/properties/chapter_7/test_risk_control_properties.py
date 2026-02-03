"""Risk Control Property-Based Tests

白皮书依据: 第六章 5.4 风险门闸

Property 19: MarginWatchdog Risk Level Calculation
Property 20: LockBox Lockable Profit Calculation
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis import HealthCheck

from src.execution.margin_watchdog import (
    MarginWatchdog,
    MarginWatchdogConfig,
    RiskLevel
)


class TestMarginWatchdogProperties:
    """MarginWatchdog属性测试
    
    白皮书依据: 第六章 5.4 风险门闸
    """
    
    @given(
        risk_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_19_risk_level_calculation(self, risk_ratio):
        """Property 19: MarginWatchdog Risk Level Calculation
        
        白皮书依据: 第六章 5.4 风险门闸
        验证需求: Requirements 12.2
        
        属性：对于任意风险度值，MarginWatchdog应该计算出正确的风险等级：
        - risk_ratio < 50%: SAFE
        - 50% ≤ risk_ratio < 70%: WARNING
        - 70% ≤ risk_ratio < 85%: DANGER
        - risk_ratio ≥ 85%: CRITICAL
        """
        # 创建Watchdog实例
        config = MarginWatchdogConfig(
            warning_risk_ratio=0.50,
            danger_risk_ratio=0.70,
            critical_risk_ratio=0.85
        )
        watchdog = MarginWatchdog(config=config)
        
        # 计算风险等级
        risk_level = watchdog._calculate_risk_level(risk_ratio)
        
        # 验证风险等级正确性
        if risk_ratio < 0.50:
            assert risk_level == RiskLevel.SAFE, \
                f"风险度{risk_ratio:.2f}应该是SAFE，但得到{risk_level.value}"
        elif 0.50 <= risk_ratio < 0.70:
            assert risk_level == RiskLevel.WARNING, \
                f"风险度{risk_ratio:.2f}应该是WARNING，但得到{risk_level.value}"
        elif 0.70 <= risk_ratio < 0.85:
            assert risk_level == RiskLevel.DANGER, \
                f"风险度{risk_ratio:.2f}应该是DANGER，但得到{risk_level.value}"
        else:  # risk_ratio >= 0.85
            assert risk_level == RiskLevel.CRITICAL, \
                f"风险度{risk_ratio:.2f}应该是CRITICAL，但得到{risk_level.value}"
    
    @given(
        warning_threshold=st.floats(min_value=0.1, max_value=0.6, allow_nan=False, allow_infinity=False),
        danger_threshold=st.floats(min_value=0.6, max_value=0.8, allow_nan=False, allow_infinity=False),
        critical_threshold=st.floats(min_value=0.8, max_value=0.95, allow_nan=False, allow_infinity=False),
        risk_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_19_custom_thresholds(
        self,
        warning_threshold,
        danger_threshold,
        critical_threshold,
        risk_ratio
    ):
        """Property 19扩展: 自定义阈值的风险等级计算
        
        白皮书依据: 第六章 5.4 风险门闸
        验证需求: Requirements 12.2
        
        属性：对于任意自定义阈值配置，风险等级计算应该遵循阈值规则
        """
        # 确保阈值递增
        assume(warning_threshold < danger_threshold < critical_threshold)
        
        # 创建自定义配置
        config = MarginWatchdogConfig(
            warning_risk_ratio=warning_threshold,
            danger_risk_ratio=danger_threshold,
            critical_risk_ratio=critical_threshold
        )
        watchdog = MarginWatchdog(config=config)
        
        # 计算风险等级
        risk_level = watchdog._calculate_risk_level(risk_ratio)
        
        # 验证风险等级正确性
        if risk_ratio < warning_threshold:
            assert risk_level == RiskLevel.SAFE
        elif warning_threshold <= risk_ratio < danger_threshold:
            assert risk_level == RiskLevel.WARNING
        elif danger_threshold <= risk_ratio < critical_threshold:
            assert risk_level == RiskLevel.DANGER
        else:
            assert risk_level == RiskLevel.CRITICAL
    
    @given(
        risk_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_19_idempotence(self, risk_ratio):
        """Property 19扩展: 风险等级计算的幂等性
        
        白皮书依据: 第六章 5.4 风险门闸
        
        属性：对于相同的风险度值，多次计算应该得到相同的风险等级
        """
        config = MarginWatchdogConfig()
        watchdog = MarginWatchdog(config=config)
        
        # 多次计算
        level1 = watchdog._calculate_risk_level(risk_ratio)
        level2 = watchdog._calculate_risk_level(risk_ratio)
        level3 = watchdog._calculate_risk_level(risk_ratio)
        
        # 验证幂等性
        assert level1 == level2 == level3, \
            f"风险度{risk_ratio:.2f}的风险等级计算不一致: {level1.value}, {level2.value}, {level3.value}"
    
    @given(
        risk_ratio1=st.floats(min_value=0.0, max_value=0.99, allow_nan=False, allow_infinity=False),
        risk_ratio2=st.floats(min_value=0.0, max_value=0.99, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_19_monotonicity(self, risk_ratio1, risk_ratio2):
        """Property 19扩展: 风险等级的单调性
        
        白皮书依据: 第六章 5.4 风险门闸
        
        属性：风险度越高，风险等级应该不降低（单调性）
        """
        assume(risk_ratio1 < risk_ratio2)
        
        config = MarginWatchdogConfig()
        watchdog = MarginWatchdog(config=config)
        
        level1 = watchdog._calculate_risk_level(risk_ratio1)
        level2 = watchdog._calculate_risk_level(risk_ratio2)
        
        # 定义风险等级的顺序
        level_order = {
            RiskLevel.SAFE: 0,
            RiskLevel.WARNING: 1,
            RiskLevel.DANGER: 2,
            RiskLevel.CRITICAL: 3
        }
        
        # 验证单调性：风险度更高，等级应该不降低
        assert level_order[level1] <= level_order[level2], \
            f"风险度从{risk_ratio1:.2f}增加到{risk_ratio2:.2f}，" \
            f"但风险等级从{level1.value}降低到{level2.value}"
    
    @given(
        risk_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_19_boundary_consistency(self, risk_ratio):
        """Property 19扩展: 边界一致性
        
        白皮书依据: 第六章 5.4 风险门闸
        
        属性：在阈值边界附近，风险等级应该正确转换
        """
        config = MarginWatchdogConfig(
            warning_risk_ratio=0.50,
            danger_risk_ratio=0.70,
            critical_risk_ratio=0.85
        )
        watchdog = MarginWatchdog(config=config)
        
        level = watchdog._calculate_risk_level(risk_ratio)
        
        # 验证边界一致性
        if risk_ratio < 0.50:
            assert level == RiskLevel.SAFE
            # 稍微增加一点应该进入WARNING
            level_above = watchdog._calculate_risk_level(0.50)
            assert level_above in [RiskLevel.WARNING, RiskLevel.DANGER, RiskLevel.CRITICAL]
        
        elif risk_ratio >= 0.85:
            assert level == RiskLevel.CRITICAL
            # 稍微减少一点应该不是CRITICAL
            level_below = watchdog._calculate_risk_level(0.849)
            assert level_below != RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    @given(
        total_assets=st.floats(min_value=100000, max_value=10000000, allow_nan=False, allow_infinity=False),
        margin_used=st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False),
        margin_available=st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_19_integration_with_check(
        self,
        total_assets,
        margin_used,
        margin_available
    ):
        """Property 19扩展: 与check_margin_risk集成测试
        
        白皮书依据: 第六章 5.4 风险门闸
        
        属性：check_margin_risk返回的风险等级应该与_calculate_risk_level一致
        """
        assume(margin_used + margin_available > 0)
        assume(margin_used <= total_assets)
        
        config = MarginWatchdogConfig()
        watchdog = MarginWatchdog(config=config)
        
        account_data = {
            'total_assets': total_assets,
            'margin_used': margin_used,
            'margin_available': margin_available,
            'derivative_positions': []
        }
        
        result = await watchdog.check_margin_risk(account_data)
        
        if result['success']:
            # 手动计算风险度
            total_margin = margin_used + margin_available
            expected_risk_ratio = margin_used / total_margin if total_margin > 0 else 0
            expected_level = watchdog._calculate_risk_level(expected_risk_ratio)
            
            # 验证一致性
            assert result['risk_level'] == expected_level.value, \
                f"check_margin_risk返回的风险等级{result['risk_level']}与" \
                f"_calculate_risk_level计算的{expected_level.value}不一致"


# Property 20: LockBox Lockable Profit Calculation
# 将在下一步实现LockBox测试时添加


class TestLockBoxProperties:
    """LockBox属性测试
    
    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    """
    
    @pytest.mark.asyncio
    @given(
        daily_pnl=st.floats(min_value=-1000000, max_value=1000000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=100000, max_value=10000000, allow_nan=False, allow_infinity=False),
        profit_lock_ratio=st.floats(min_value=0.1, max_value=0.5, allow_nan=False, allow_infinity=False),
        min_lock_amount=st.floats(min_value=1000, max_value=50000, allow_nan=False, allow_infinity=False),
        max_lock_ratio=st.floats(min_value=0.3, max_value=0.8, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_lockable_profit_calculation(
        self,
        daily_pnl,
        total_assets,
        profit_lock_ratio,
        min_lock_amount,
        max_lock_ratio
    ):
        """Property 20: LockBox Lockable Profit Calculation
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        验证需求: Requirements 13.2
        
        属性：对于任意正盈利的投资组合，LockBox应该计算出正确的可锁定利润：
        - profit_lock_ratio × daily_pnl, if result ≥ min_lock_amount
        - 0, if result < min_lock_amount
        - Capped by (max_lock_ratio × total_assets - already_locked)
        """
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        # 创建LockBox配置
        config = LockBoxConfig(
            profit_lock_ratio=profit_lock_ratio,
            min_lock_amount=min_lock_amount,
            max_lock_ratio=max_lock_ratio
        )
        lockbox = LockBox(config=config)
        
        # 设置已锁定金额（随机）
        already_locked = total_assets * max_lock_ratio * 0.5  # 已锁定50%的最大额度
        lockbox.state.total_locked_amount = already_locked
        
        portfolio_data = {
            'daily_pnl': daily_pnl,
            'total_assets': total_assets
        }
        
        # 计算可锁定利润
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        
        # 验证属性
        if daily_pnl <= 0:
            # 无盈利或亏损，不应锁定
            assert lockable == 0.0, \
                f"盈利{daily_pnl:.2f}≤0，但可锁定金额为{lockable:.2f}"
        else:
            # 计算预期锁定金额
            target_lock = daily_pnl * profit_lock_ratio
            
            if target_lock < min_lock_amount:
                # 低于最小阈值，不应锁定
                assert lockable == 0.0, \
                    f"目标锁定{target_lock:.2f}<最小阈值{min_lock_amount:.2f}，" \
                    f"但可锁定金额为{lockable:.2f}"
            else:
                # 计算最大可锁定金额
                max_lockable = total_assets * max_lock_ratio - already_locked
                
                if max_lockable <= 0:
                    # 已达到最大锁定比例
                    assert lockable == 0.0, \
                        f"已达到最大锁定比例，但可锁定金额为{lockable:.2f}"
                else:
                    # 应该锁定min(target_lock, max_lockable)
                    expected_lockable = min(target_lock, max_lockable)
                    assert abs(lockable - expected_lockable) < 0.01, \
                        f"预期可锁定{expected_lockable:.2f}，但实际为{lockable:.2f}"
    
    @pytest.mark.asyncio
    @given(
        daily_pnl=st.floats(min_value=50000, max_value=500000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000000, max_value=5000000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_positive_profit_lockable(
        self,
        daily_pnl,
        total_assets
    ):
        """Property 20扩展: 正盈利应该可锁定
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        
        属性：对于足够大的正盈利，应该能够锁定一部分利润
        """
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        config = LockBoxConfig(
            profit_lock_ratio=0.3,
            min_lock_amount=10000,
            max_lock_ratio=0.5
        )
        lockbox = LockBox(config=config)
        
        portfolio_data = {
            'daily_pnl': daily_pnl,
            'total_assets': total_assets
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        
        # 验证：足够大的盈利应该可以锁定
        target_lock = daily_pnl * 0.3
        if target_lock >= 10000:
            assert lockable > 0, \
                f"盈利{daily_pnl:.2f}足够大，但可锁定金额为0"
    
    @pytest.mark.asyncio
    @given(
        daily_pnl=st.floats(min_value=10000, max_value=100000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000000, max_value=5000000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_idempotence(
        self,
        daily_pnl,
        total_assets
    ):
        """Property 20扩展: 可锁定利润计算的幂等性
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        
        属性：对于相同的投资组合数据，多次计算应该得到相同的可锁定金额
        """
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        config = LockBoxConfig()
        lockbox = LockBox(config=config)
        
        portfolio_data = {
            'daily_pnl': daily_pnl,
            'total_assets': total_assets
        }
        
        # 多次计算
        lockable1 = await lockbox.calculate_lockable_profit(portfolio_data)
        lockable2 = await lockbox.calculate_lockable_profit(portfolio_data)
        lockable3 = await lockbox.calculate_lockable_profit(portfolio_data)
        
        # 验证幂等性
        assert lockable1 == lockable2 == lockable3, \
            f"可锁定利润计算不一致: {lockable1:.2f}, {lockable2:.2f}, {lockable3:.2f}"
    
    @pytest.mark.asyncio
    @given(
        daily_pnl1=st.floats(min_value=10000, max_value=100000, allow_nan=False, allow_infinity=False),
        daily_pnl2=st.floats(min_value=10000, max_value=100000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000000, max_value=5000000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_monotonicity(
        self,
        daily_pnl1,
        daily_pnl2,
        total_assets
    ):
        """Property 20扩展: 可锁定利润的单调性
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        
        属性：盈利越高，可锁定金额应该不降低（单调性）
        """
        assume(daily_pnl1 < daily_pnl2)
        
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        config = LockBoxConfig()
        lockbox = LockBox(config=config)
        
        portfolio_data1 = {
            'daily_pnl': daily_pnl1,
            'total_assets': total_assets
        }
        
        portfolio_data2 = {
            'daily_pnl': daily_pnl2,
            'total_assets': total_assets
        }
        
        lockable1 = await lockbox.calculate_lockable_profit(portfolio_data1)
        
        # 重置状态以确保公平比较
        lockbox.reset_state()
        
        lockable2 = await lockbox.calculate_lockable_profit(portfolio_data2)
        
        # 验证单调性：盈利更高，可锁定金额应该不降低
        assert lockable1 <= lockable2, \
            f"盈利从{daily_pnl1:.2f}增加到{daily_pnl2:.2f}，" \
            f"但可锁定金额从{lockable1:.2f}降低到{lockable2:.2f}"
    
    @pytest.mark.asyncio
    @given(
        daily_pnl=st.floats(min_value=50000, max_value=500000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000000, max_value=5000000, allow_nan=False, allow_infinity=False),
        profit_lock_ratio=st.floats(min_value=0.1, max_value=0.5, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_ratio_proportionality(
        self,
        daily_pnl,
        total_assets,
        profit_lock_ratio
    ):
        """Property 20扩展: 锁定比例的比例性
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        
        属性：可锁定金额应该与锁定比例成正比
        """
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        config = LockBoxConfig(
            profit_lock_ratio=profit_lock_ratio,
            min_lock_amount=1000,  # 设置较低以避免阈值影响
            max_lock_ratio=0.9  # 设置较高以避免上限影响
        )
        lockbox = LockBox(config=config)
        
        portfolio_data = {
            'daily_pnl': daily_pnl,
            'total_assets': total_assets
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        
        # 验证比例性
        if lockable > 0:
            expected_lockable = daily_pnl * profit_lock_ratio
            # 允许小的浮点误差
            assert abs(lockable - expected_lockable) < 1.0, \
                f"预期可锁定{expected_lockable:.2f}（{profit_lock_ratio*100:.0f}%），" \
                f"但实际为{lockable:.2f}"
    
    @pytest.mark.asyncio
    @given(
        daily_pnl=st.floats(min_value=100000, max_value=1000000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000000, max_value=5000000, allow_nan=False, allow_infinity=False),
        max_lock_ratio=st.floats(min_value=0.3, max_value=0.7, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_max_ratio_cap(
        self,
        daily_pnl,
        total_assets,
        max_lock_ratio
    ):
        """Property 20扩展: 最大锁定比例上限
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        
        属性：可锁定金额不应超过最大锁定比例限制
        """
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        config = LockBoxConfig(
            profit_lock_ratio=0.5,  # 高锁定比例
            min_lock_amount=1000,
            max_lock_ratio=max_lock_ratio
        )
        lockbox = LockBox(config=config)
        
        # 设置已锁定金额接近上限
        already_locked = total_assets * max_lock_ratio * 0.8
        lockbox.state.total_locked_amount = already_locked
        
        portfolio_data = {
            'daily_pnl': daily_pnl,
            'total_assets': total_assets
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        
        # 验证：锁定后不应超过最大比例
        total_locked_after = already_locked + lockable
        max_allowed = total_assets * max_lock_ratio
        
        assert total_locked_after <= max_allowed + 0.01, \
            f"锁定后总额{total_locked_after:.2f}超过最大允许{max_allowed:.2f}"
    
    @pytest.mark.asyncio
    @given(
        daily_pnl=st.floats(min_value=1000, max_value=100000, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000000, max_value=5000000, allow_nan=False, allow_infinity=False),
        min_lock_amount=st.floats(min_value=5000, max_value=50000, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_20_min_amount_threshold(
        self,
        daily_pnl,
        total_assets,
        min_lock_amount
    ):
        """Property 20扩展: 最小锁定金额阈值
        
        白皮书依据: 第六章 5.3 资本基因与诺亚方舟
        
        属性：如果计算出的锁定金额低于最小阈值，应该返回0
        """
        from src.execution.lockbox import LockBox, LockBoxConfig
        
        config = LockBoxConfig(
            profit_lock_ratio=0.3,
            min_lock_amount=min_lock_amount,
            max_lock_ratio=0.5
        )
        lockbox = LockBox(config=config)
        
        portfolio_data = {
            'daily_pnl': daily_pnl,
            'total_assets': total_assets
        }
        
        lockable = await lockbox.calculate_lockable_profit(portfolio_data)
        
        # 验证：要么为0，要么≥最小阈值
        if lockable > 0:
            assert lockable >= min_lock_amount - 0.01, \
                f"可锁定金额{lockable:.2f}低于最小阈值{min_lock_amount:.2f}"
        else:
            # 验证确实是因为低于阈值
            target_lock = daily_pnl * 0.3
            if target_lock < min_lock_amount:
                assert lockable == 0.0, \
                    f"目标锁定{target_lock:.2f}<最小阈值{min_lock_amount:.2f}，" \
                    f"应该返回0，但返回{lockable:.2f}"
