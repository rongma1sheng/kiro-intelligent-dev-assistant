"""Property-Based Tests for Configuration Management

白皮书依据: 第四章 4.9 配置管理

Properties tested:
- Property 50: Configuration Hot Reload
- Property 51: Invalid Configuration Handling
"""

import pytest
import tempfile
import shutil
import yaml
import json
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

from src.evolution.config.configuration_manager import ConfigurationManager
from src.evolution.config.data_models import (
    SpartaEvolutionConfig,
    ArenaConfig,
    SimulationConfig,
    Z2HConfig,
    DecayConfig,
    get_default_config
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def valid_arena_config_strategy(draw):
    """生成有效的Arena配置"""
    # 生成权重，确保和为1
    w1 = draw(st.floats(min_value=0.1, max_value=0.5))
    w2 = draw(st.floats(min_value=0.1, max_value=0.5))
    w3 = 1.0 - w1 - w2
    
    # 确保w3在有效范围内
    if w3 < 0.1 or w3 > 0.5:
        w1, w2, w3 = 0.4, 0.3, 0.3
    
    return {
        'min_ic': draw(st.floats(min_value=0.01, max_value=0.1)),
        'min_ir': draw(st.floats(min_value=0.1, max_value=2.0)),
        'min_sharpe': draw(st.floats(min_value=0.5, max_value=3.0)),
        'max_drawdown': draw(st.floats(min_value=0.05, max_value=0.3)),
        'pass_score': draw(st.floats(min_value=0.5, max_value=0.9)),
        'reality_track_weight': w1,
        'hell_track_weight': w2,
        'cross_market_weight': w3
    }


@st.composite
def valid_simulation_config_strategy(draw):
    """生成有效的模拟配置"""
    return {
        'duration_days': draw(st.integers(min_value=7, max_value=90)),
        'tier_1_capital': draw(st.floats(min_value=100000, max_value=10000000)),
        'tier_2_capital': draw(st.floats(min_value=50000, max_value=5000000)),
        'tier_3_capital': draw(st.floats(min_value=10000, max_value=1000000)),
        'tier_4_capital': draw(st.floats(min_value=1000, max_value=500000)),
        'commission_rate': draw(st.floats(min_value=0.0001, max_value=0.005)),
        'slippage_rate': draw(st.floats(min_value=0.0001, max_value=0.01)),
        'min_return': draw(st.floats(min_value=0.01, max_value=0.2)),
        'min_sharpe': draw(st.floats(min_value=0.5, max_value=3.0)),
        'max_drawdown': draw(st.floats(min_value=0.05, max_value=0.3)),
        'min_win_rate': draw(st.floats(min_value=0.4, max_value=0.7)),
        'min_profit_factor': draw(st.floats(min_value=1.0, max_value=3.0)),
        'early_termination_drawdown': draw(st.floats(min_value=0.1, max_value=0.5))
    }


@st.composite
def valid_z2h_config_strategy(draw):
    """生成有效的Z2H配置"""
    silver = draw(st.floats(min_value=1.0, max_value=2.0))
    gold = silver + draw(st.floats(min_value=0.1, max_value=1.0))
    
    return {
        'gold_sharpe_threshold': gold,
        'silver_sharpe_threshold': silver,
        'redis_ttl_days': draw(st.integers(min_value=30, max_value=730)),
        'file_storage_enabled': draw(st.booleans())
    }


@st.composite
def valid_decay_config_strategy(draw):
    """生成有效的衰减配置"""
    mild = draw(st.integers(min_value=3, max_value=10))
    moderate = mild + draw(st.integers(min_value=3, max_value=10))
    severe = moderate + draw(st.integers(min_value=5, max_value=20))
    
    return {
        'ic_warning_threshold': draw(st.floats(min_value=0.01, max_value=0.1)),
        'mild_decay_days': mild,
        'moderate_decay_days': moderate,
        'severe_decay_days': severe,
        'weight_reduction_ratio': draw(st.floats(min_value=0.1, max_value=0.5)),
        'sharpe_monitoring_threshold': draw(st.floats(min_value=0.5, max_value=2.0))
    }


@st.composite
def valid_config_strategy(draw):
    """生成有效的完整配置"""
    return {
        'arena': draw(valid_arena_config_strategy()),
        'simulation': draw(valid_simulation_config_strategy()),
        'z2h': draw(valid_z2h_config_strategy()),
        'decay': draw(valid_decay_config_strategy()),
        'version': f"{draw(st.integers(min_value=1, max_value=9))}.{draw(st.integers(min_value=0, max_value=9))}.{draw(st.integers(min_value=0, max_value=9))}"
    }


@st.composite
def invalid_arena_config_strategy(draw):
    """生成无效的Arena配置"""
    invalid_type = draw(st.sampled_from([
        'negative_ic',
        'invalid_weights',
        'out_of_range_score'
    ]))
    
    if invalid_type == 'negative_ic':
        return {'min_ic': -0.5}
    elif invalid_type == 'invalid_weights':
        return {
            'reality_track_weight': 0.5,
            'hell_track_weight': 0.5,
            'cross_market_weight': 0.5  # 和为1.5，无效
        }
    else:
        return {'pass_score': 1.5}  # 超出[0,1]范围


@st.composite
def invalid_simulation_config_strategy(draw):
    """生成无效的模拟配置"""
    invalid_type = draw(st.sampled_from([
        'negative_duration',
        'negative_capital',
        'invalid_rate'
    ]))
    
    if invalid_type == 'negative_duration':
        return {'duration_days': -10}
    elif invalid_type == 'negative_capital':
        return {'tier_1_capital': -1000000}
    else:
        return {'commission_rate': 0.5}  # 超出[0, 0.01]范围


@st.composite
def invalid_z2h_config_strategy(draw):
    """生成无效的Z2H配置"""
    return {
        'gold_sharpe_threshold': 1.0,
        'silver_sharpe_threshold': 2.0  # gold < silver，无效
    }


@st.composite
def invalid_decay_config_strategy(draw):
    """生成无效的衰减配置"""
    return {
        'mild_decay_days': 20,
        'moderate_decay_days': 10,  # moderate < mild，无效
        'severe_decay_days': 30
    }


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_config_dir():
    """创建临时配置目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def config_manager():
    """创建配置管理器实例（使用默认配置）"""
    return ConfigurationManager()


# ============================================================================
# Property 50: Configuration Hot Reload
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    initial_config=valid_config_strategy(),
    updated_config=valid_config_strategy()
)
def test_property_50_configuration_hot_reload(
    temp_config_dir,
    initial_config,
    updated_config
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 50: Configuration Hot Reload
    
    For any configuration change, the system should reload the configuration
    without requiring a restart.
    
    白皮书依据: 第四章 4.9.6 热重载 - Requirement 11.6
    Validates: Requirements 11.6
    """
    config_path = Path(temp_config_dir) / "sparta_config.yaml"
    
    # 写入初始配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(initial_config, f)
    
    # 创建配置管理器
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 验证：初始配置已加载
    assert manager.config.version == initial_config['version'], \
        "初始配置应该正确加载"
    
    # 记录初始Arena配置
    initial_pass_score = manager.arena.pass_score
    
    # 写入更新后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(updated_config, f)
    
    # 执行热重载
    reload_success = manager.reload()
    
    # 验证：重载应该成功
    assert reload_success, "配置热重载应该成功"
    
    # 验证：配置已更新
    assert manager.config.version == updated_config['version'], \
        "配置版本应该更新"
    
    # 验证：Arena配置已更新
    expected_pass_score = updated_config['arena']['pass_score']
    assert abs(manager.arena.pass_score - expected_pass_score) < 0.001, \
        f"Arena pass_score应该更新为{expected_pass_score}，实际: {manager.arena.pass_score}"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    config=valid_config_strategy()
)
def test_property_50_reload_callback_notification(
    temp_config_dir,
    config
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 50: Configuration Hot Reload - Callback Notification
    
    When configuration is reloaded, all registered callbacks should be notified.
    
    白皮书依据: 第四章 4.9.6 热重载 - Requirement 11.6
    Validates: Requirements 11.6
    """
    config_path = Path(temp_config_dir) / "sparta_config.yaml"
    
    # 写入配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
    
    # 创建配置管理器
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 注册回调
    callback_called = [False]
    received_config = [None]
    
    def on_reload(new_config):
        callback_called[0] = True
        received_config[0] = new_config
    
    manager.register_reload_callback(on_reload)
    
    # 执行重载
    manager.reload()
    
    # 验证：回调应该被调用
    assert callback_called[0], "重载回调应该被调用"
    
    # 验证：回调接收到正确的配置
    assert received_config[0] is not None, "回调应该接收到配置"
    assert received_config[0].version == config['version'], \
        "回调接收到的配置版本应该正确"


# ============================================================================
# Property 51: Invalid Configuration Handling
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    invalid_arena=invalid_arena_config_strategy()
)
def test_property_51_invalid_arena_config_handling(
    temp_config_dir,
    invalid_arena
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 51: Invalid Configuration Handling - Arena Config
    
    For any invalid Arena configuration value detected, the system should
    log an error and use default values.
    
    白皮书依据: 第四章 4.9.7 无效配置处理 - Requirement 11.7
    Validates: Requirements 11.7
    """
    config_path = Path(temp_config_dir) / "invalid_config.yaml"
    
    # 写入无效配置
    invalid_config = {'arena': invalid_arena}
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(invalid_config, f)
    
    # 创建配置管理器（应该使用默认配置）
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 验证：应该使用默认配置
    default_config = get_default_config()
    
    # 验证：Arena配置应该是默认值
    assert manager.arena.min_ic == default_config.arena.min_ic, \
        "无效配置时应该使用默认Arena配置"
    
    # 验证：应该记录错误
    assert len(manager.reload_errors) > 0 or manager.arena == default_config.arena, \
        "无效配置应该记录错误或使用默认值"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    invalid_simulation=invalid_simulation_config_strategy()
)
def test_property_51_invalid_simulation_config_handling(
    temp_config_dir,
    invalid_simulation
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 51: Invalid Configuration Handling - Simulation Config
    
    For any invalid Simulation configuration value detected, the system should
    log an error and use default values.
    
    白皮书依据: 第四章 4.9.7 无效配置处理 - Requirement 11.7
    Validates: Requirements 11.7
    """
    config_path = Path(temp_config_dir) / "invalid_config.yaml"
    
    # 写入无效配置
    invalid_config = {'simulation': invalid_simulation}
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(invalid_config, f)
    
    # 创建配置管理器（应该使用默认配置）
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 验证：应该使用默认配置
    default_config = get_default_config()
    
    # 验证：Simulation配置应该是默认值
    assert manager.simulation.duration_days == default_config.simulation.duration_days, \
        "无效配置时应该使用默认Simulation配置"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    invalid_z2h=invalid_z2h_config_strategy()
)
def test_property_51_invalid_z2h_config_handling(
    temp_config_dir,
    invalid_z2h
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 51: Invalid Configuration Handling - Z2H Config
    
    For any invalid Z2H configuration value detected, the system should
    log an error and use default values.
    
    白皮书依据: 第四章 4.9.7 无效配置处理 - Requirement 11.7
    Validates: Requirements 11.7
    """
    config_path = Path(temp_config_dir) / "invalid_config.yaml"
    
    # 写入无效配置
    invalid_config = {'z2h': invalid_z2h}
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(invalid_config, f)
    
    # 创建配置管理器（应该使用默认配置）
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 验证：应该使用默认配置
    default_config = get_default_config()
    
    # 验证：Z2H配置应该是默认值
    assert manager.z2h.gold_sharpe_threshold == default_config.z2h.gold_sharpe_threshold, \
        "无效配置时应该使用默认Z2H配置"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    invalid_decay=invalid_decay_config_strategy()
)
def test_property_51_invalid_decay_config_handling(
    temp_config_dir,
    invalid_decay
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 51: Invalid Configuration Handling - Decay Config
    
    For any invalid Decay configuration value detected, the system should
    log an error and use default values.
    
    白皮书依据: 第四章 4.9.7 无效配置处理 - Requirement 11.7
    Validates: Requirements 11.7
    """
    config_path = Path(temp_config_dir) / "invalid_config.yaml"
    
    # 写入无效配置
    invalid_config = {'decay': invalid_decay}
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(invalid_config, f)
    
    # 创建配置管理器（应该使用默认配置）
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 验证：应该使用默认配置
    default_config = get_default_config()
    
    # 验证：Decay配置应该是默认值
    assert manager.decay.mild_decay_days == default_config.decay.mild_decay_days, \
        "无效配置时应该使用默认Decay配置"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    valid_config=valid_config_strategy(),
    invalid_arena=invalid_arena_config_strategy()
)
def test_property_51_reload_with_invalid_config_preserves_old(
    temp_config_dir,
    valid_config,
    invalid_arena
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 51: Invalid Configuration Handling - Preserve Old Config on Reload Failure
    
    When reloading with invalid configuration, the system should preserve
    the old valid configuration.
    
    白皮书依据: 第四章 4.9.7 无效配置处理 - Requirement 11.7
    Validates: Requirements 11.7
    """
    config_path = Path(temp_config_dir) / "sparta_config.yaml"
    
    # 写入有效配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(valid_config, f)
    
    # 创建配置管理器
    manager = ConfigurationManager(config_path=str(config_path))
    
    # 记录原始配置
    original_version = manager.config.version
    original_pass_score = manager.arena.pass_score
    
    # 写入无效配置
    invalid_config = {'arena': invalid_arena}
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(invalid_config, f)
    
    # 尝试重载（应该失败）
    reload_success = manager.reload()
    
    # 验证：重载应该失败
    assert not reload_success, "使用无效配置重载应该失败"
    
    # 验证：应该保持原配置
    assert manager.config.version == original_version, \
        "重载失败时应该保持原配置版本"
    
    assert abs(manager.arena.pass_score - original_pass_score) < 0.001, \
        "重载失败时应该保持原Arena配置"
