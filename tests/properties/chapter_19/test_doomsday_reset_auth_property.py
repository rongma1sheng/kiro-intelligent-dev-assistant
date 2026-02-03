"""Property 23: Doomsday Switch Reset Authentication

白皮书依据: 第十九章 19.4 末日开关

**Validates: Requirements 11.6**

Property: 末日开关重置必须通过密码认证
- 正确密码: 重置成功
- 错误密码: 重置失败

This property ensures that the doomsday switch can only be reset with
proper authentication, preventing unauthorized system recovery.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import MagicMock

from src.core.doomsday_switch import DoomsdaySwitch


# Strategy for generating passwords
password_strategy = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=8,
    max_size=32
)


@settings(max_examples=100)
@given(
    correct_password=password_strategy,
    wrong_password=password_strategy
)
def test_doomsday_reset_authentication_property(
    correct_password: str,
    wrong_password: str
):
    """Property 23: 末日开关重置需要正确密码
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: reset(correct_password) succeeds, reset(wrong_password) fails
    
    This ensures that:
    1. Only authorized personnel can reset the switch
    2. Wrong passwords are rejected
    3. System security is maintained
    """
    # Ensure passwords are different
    assume(correct_password != wrong_password)
    
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = correct_password.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    
    # Create fresh doomsday switch instance
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Trigger the switch
    switch.trigger(reason="Test trigger")
    assert switch.is_triggered() is True
    
    # Try to reset with wrong password - should fail
    result_wrong = switch.reset(password=wrong_password)
    assert result_wrong is False, (
        f"Reset should fail with wrong password"
    )
    assert switch.is_triggered() is True, (
        f"Switch should remain triggered after wrong password"
    )
    
    # Reset with correct password - should succeed
    result_correct = switch.reset(password=correct_password)
    assert result_correct is True, (
        f"Reset should succeed with correct password"
    )
    assert switch.is_triggered() is False, (
        f"Switch should be reset after correct password"
    )


@settings(max_examples=100)
@given(
    password=password_strategy,
    num_wrong_attempts=st.integers(min_value=1, max_value=10)
)
def test_doomsday_reset_multiple_wrong_attempts(
    password: str,
    num_wrong_attempts: int
):
    """Property 23: 多次错误密码尝试不应成功
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Multiple wrong password attempts should all fail
    
    This ensures that:
    1. Brute force attacks are prevented
    2. Switch remains secure under attack
    3. Only correct password works
    """
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = password.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Trigger the switch
    switch.trigger(reason="Test trigger")
    
    # Try multiple wrong passwords
    for i in range(num_wrong_attempts):
        wrong_password = f"wrong_password_{i}"
        assume(wrong_password != password)
        
        result = switch.reset(password=wrong_password)
        
        # Property: All wrong attempts should fail
        assert result is False, (
            f"Attempt {i+1} with wrong password should fail"
        )
        assert switch.is_triggered() is True, (
            f"Switch should remain triggered after attempt {i+1}"
        )


def test_doomsday_reset_empty_password():
    """Property 23: 空密码不应被接受
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Empty password should always fail
    
    This ensures that:
    1. Password validation is strict
    2. Empty passwords are rejected
    3. System security is maintained
    """
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = b"secure_password_123"
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Trigger the switch
    switch.trigger(reason="Test trigger")
    
    # Try to reset with empty password
    result = switch.reset(password="")
    
    # Property: Empty password should fail
    assert result is False, (
        f"Reset should fail with empty password"
    )
    assert switch.is_triggered() is True, (
        f"Switch should remain triggered after empty password"
    )


def test_doomsday_reset_case_sensitive():
    """Property 23: 密码区分大小写
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Password should be case-sensitive
    
    This ensures that:
    1. Password matching is strict
    2. Case variations are rejected
    3. Security is not weakened by case-insensitivity
    """
    password = "SecurePassword123"
    
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = password.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Trigger the switch
    switch.trigger(reason="Test trigger")
    
    # Try case variations
    case_variations = [
        password.lower(),  # "securepassword123"
        password.upper(),  # "SECUREPASSWORD123"
        password.swapcase()  # "sECUREpASSWORD123"
    ]
    
    for variation in case_variations:
        if variation == password:
            continue  # Skip if variation matches original
        
        result = switch.reset(password=variation)
        
        # Property: Case variations should fail
        assert result is False, (
            f"Reset should fail with case variation '{variation}'"
        )
        assert switch.is_triggered() is True, (
            f"Switch should remain triggered after case variation"
        )
    
    # Correct password should work
    result = switch.reset(password=password)
    assert result is True, (
        f"Reset should succeed with correct password"
    )


def test_doomsday_reset_idempotent():
    """Property 23: 重置操作的幂等性
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Resetting an already-reset switch should succeed
    
    This ensures that:
    1. Reset operation is idempotent
    2. Multiple resets don't cause errors
    3. System state is consistent
    """
    password = "test_password_123"
    
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = password.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Trigger the switch
    switch.trigger(reason="Test trigger")
    assert switch.is_triggered() is True
    
    # First reset
    result1 = switch.reset(password=password)
    assert result1 is True
    assert switch.is_triggered() is False
    
    # Second reset (already reset)
    result2 = switch.reset(password=password)
    assert result2 is True, (
        f"Reset should succeed even when already reset"
    )
    assert switch.is_triggered() is False


@settings(max_examples=50)
@given(
    password=password_strategy,
    num_cycles=st.integers(min_value=1, max_value=5)
)
def test_doomsday_reset_trigger_cycle(
    password: str,
    num_cycles: int
):
    """Property 23: 触发-重置循环的一致性
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Multiple trigger-reset cycles should work consistently
    
    This ensures that:
    1. Switch can be triggered and reset multiple times
    2. Authentication works consistently across cycles
    3. No state corruption occurs
    """
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = password.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    redis_mock.publish.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    for cycle in range(num_cycles):
        # Trigger
        switch.trigger(reason=f"Test trigger {cycle+1}")
        assert switch.is_triggered() is True, (
            f"Switch should be triggered in cycle {cycle+1}"
        )
        
        # Reset with correct password
        result = switch.reset(password=password)
        assert result is True, (
            f"Reset should succeed in cycle {cycle+1}"
        )
        assert switch.is_triggered() is False, (
            f"Switch should be reset in cycle {cycle+1}"
        )


def test_doomsday_reset_without_trigger():
    """Property 23: 未触发时重置应该成功
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Resetting a non-triggered switch should succeed
    
    This ensures that:
    1. Reset works regardless of current state
    2. No errors occur when resetting non-triggered switch
    3. System is robust
    """
    password = "test_password_123"
    
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = password.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Don't trigger, just try to reset
    assert switch.is_triggered() is False
    
    result = switch.reset(password=password)
    
    # Property: Reset should succeed even when not triggered
    assert result is True, (
        f"Reset should succeed even when switch is not triggered"
    )
    assert switch.is_triggered() is False


def test_doomsday_reset_password_immutable():
    """Property 23: 重置密码不可变
    
    白皮书依据: 第十九章 19.4 末日开关
    
    Property: Reset password should not change after initialization
    
    This ensures that:
    1. Password is set at initialization and cannot be changed
    2. Security is maintained throughout lifecycle
    3. No password modification attacks are possible
    """
    password1 = "initial_password"
    password2 = "different_password"
    
    # Create mock Redis client
    redis_mock = MagicMock()
    redis_mock.get.return_value = password1.encode()
    redis_mock.delete.return_value = None
    redis_mock.set.return_value = None
    redis_mock.publish.return_value = None
    
    switch = DoomsdaySwitch(redis_client=redis_mock)
    
    # Trigger and reset with initial password
    switch.trigger(reason="Test")
    result1 = switch.reset(password=password1)
    assert result1 is True
    
    # Trigger again and try with different password
    switch.trigger(reason="Test 2")
    result2 = switch.reset(password=password2)
    
    # Property: Different password should fail
    assert result2 is False, (
        f"Reset should fail with different password"
    )
    
    # Original password should still work
    result3 = switch.reset(password=password1)
    assert result3 is True, (
        f"Original password should still work"
    )
