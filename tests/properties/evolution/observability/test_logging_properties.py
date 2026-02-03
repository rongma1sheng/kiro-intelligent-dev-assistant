"""Property-Based Tests for Logging and Observability

白皮书依据: 第四章 4.10 日志和可观测性

Properties tested:
- Property 52: Comprehensive Logging
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.evolution.observability.structured_logger import (
    StructuredLogger,
    LogLevel,
    LogEntry,
    get_logger
)
from src.evolution.observability.metrics_collector import MetricsCollector


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def arena_start_params_strategy(draw):
    """生成Arena开始参数"""
    return {
        'arena_type': draw(st.sampled_from(['factor', 'strategy'])),
        'entity_id': f"ENTITY_{draw(st.integers(min_value=1, max_value=1000))}",
        'parameters': {
            'min_ic': draw(st.floats(min_value=0.01, max_value=0.1)),
            'min_sharpe': draw(st.floats(min_value=0.5, max_value=3.0))
        }
    }


@st.composite
def track_completion_params_strategy(draw):
    """生成Track完成参数"""
    return {
        'track_name': draw(st.sampled_from(['reality', 'hell', 'cross_market'])),
        'entity_id': f"ENTITY_{draw(st.integers(min_value=1, max_value=1000))}",
        'score': draw(st.floats(min_value=0.0, max_value=1.0)),
        'metrics': {
            'ic': draw(st.floats(min_value=-1.0, max_value=1.0)),
            'ir': draw(st.floats(min_value=-10.0, max_value=10.0))
        }
    }


@st.composite
def validation_failure_params_strategy(draw):
    """生成验证失败参数"""
    return {
        'stage': draw(st.sampled_from(['factor_arena', 'strategy_arena', 'simulation', 'z2h'])),
        'entity_id': f"ENTITY_{draw(st.integers(min_value=1, max_value=1000))}",
        'reason': draw(st.sampled_from([
            'IC below threshold',
            'Sharpe ratio too low',
            'Drawdown exceeded',
            'Win rate insufficient'
        ])),
        'details': {
            'threshold': draw(st.floats(min_value=0.0, max_value=1.0)),
            'actual': draw(st.floats(min_value=0.0, max_value=1.0))
        }
    }


@st.composite
def z2h_certification_params_strategy(draw):
    """生成Z2H认证参数"""
    return {
        'strategy_id': f"STRATEGY_{draw(st.integers(min_value=1, max_value=1000))}",
        'certification_level': draw(st.sampled_from(['GOLD', 'SILVER'])),
        'capsule_id': f"CAPSULE_{draw(st.integers(min_value=1, max_value=1000))}",
        'metrics': {
            'sharpe_ratio': draw(st.floats(min_value=1.0, max_value=5.0)),
            'total_return': draw(st.floats(min_value=0.0, max_value=1.0))
        }
    }


@st.composite
def decay_detection_params_strategy(draw):
    """生成衰减检测参数"""
    return {
        'factor_id': f"FACTOR_{draw(st.integers(min_value=1, max_value=1000))}",
        'severity': draw(st.sampled_from(['mild', 'moderate', 'severe'])),
        'ic_value': draw(st.floats(min_value=-0.1, max_value=0.1)),
        'consecutive_days': draw(st.integers(min_value=1, max_value=60))
    }


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def logger_instance():
    """创建日志器实例"""
    return StructuredLogger("test_module", LogLevel.DEBUG)


@pytest.fixture
def metrics_collector():
    """创建指标收集器实例"""
    return MetricsCollector()


# ============================================================================
# Property 52: Comprehensive Logging
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(params=arena_start_params_strategy())
def test_property_52_arena_start_logging(logger_instance, params):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - Arena Start
    
    When Arena testing starts, the system should log the factor/strategy ID
    and test parameters with timestamps, module names, and correlation IDs.
    
    白皮书依据: 第四章 4.10.1 Arena日志 - Requirement 12.1
    Validates: Requirements 12.1, 12.7
    """
    # 清空之前的日志
    logger_instance.clear_entries()
    
    # 记录Arena开始
    entry = logger_instance.log_arena_start(
        arena_type=params['arena_type'],
        entity_id=params['entity_id'],
        parameters=params['parameters']
    )
    
    # 验证：日志条目应该存在
    assert entry is not None, "Arena开始日志应该被记录"
    
    # 验证：时间戳存在
    assert entry.timestamp is not None, "日志应该包含时间戳"
    assert len(entry.timestamp) > 0, "时间戳不应为空"
    
    # 验证：模块名存在
    assert entry.module == "test_module", "日志应该包含模块名"
    
    # 验证：关联ID存在
    assert entry.correlation_id is not None, "日志应该包含关联ID"
    assert len(entry.correlation_id) > 0, "关联ID不应为空"
    
    # 验证：上下文包含必要信息
    assert 'arena_type' in entry.context, "上下文应该包含arena_type"
    assert 'entity_id' in entry.context, "上下文应该包含entity_id"
    assert 'parameters' in entry.context, "上下文应该包含parameters"
    assert 'event_type' in entry.context, "上下文应该包含event_type"
    
    # 验证：事件类型正确
    assert entry.context['event_type'] == "ARENA_START", \
        "事件类型应该是ARENA_START"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(params=track_completion_params_strategy())
def test_property_52_track_completion_logging(logger_instance, params):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - Track Completion
    
    When each track completes, the system should log the track results and scores.
    
    白皮书依据: 第四章 4.10.2 Track日志 - Requirement 12.2
    Validates: Requirements 12.2, 12.7
    """
    # 清空之前的日志
    logger_instance.clear_entries()
    
    # 记录Track完成
    entry = logger_instance.log_track_completion(
        track_name=params['track_name'],
        entity_id=params['entity_id'],
        score=params['score'],
        metrics=params['metrics']
    )
    
    # 验证：日志条目应该存在
    assert entry is not None, "Track完成日志应该被记录"
    
    # 验证：时间戳存在
    assert entry.timestamp is not None, "日志应该包含时间戳"
    
    # 验证：上下文包含必要信息
    assert 'track_name' in entry.context, "上下文应该包含track_name"
    assert 'entity_id' in entry.context, "上下文应该包含entity_id"
    assert 'score' in entry.context, "上下文应该包含score"
    assert 'metrics' in entry.context, "上下文应该包含metrics"
    assert 'event_type' in entry.context, "上下文应该包含event_type"
    
    # 验证：事件类型正确
    assert entry.context['event_type'] == "TRACK_COMPLETION", \
        "事件类型应该是TRACK_COMPLETION"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(params=validation_failure_params_strategy())
def test_property_52_validation_failure_logging(logger_instance, params):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - Validation Failure
    
    When validation fails, the system should log the failure reason and context.
    
    白皮书依据: 第四章 4.10.3 验证失败日志 - Requirement 12.3
    Validates: Requirements 12.3, 12.7
    """
    # 清空之前的日志
    logger_instance.clear_entries()
    
    # 记录验证失败
    entry = logger_instance.log_validation_failure(
        stage=params['stage'],
        entity_id=params['entity_id'],
        reason=params['reason'],
        details=params['details']
    )
    
    # 验证：日志条目应该存在
    assert entry is not None, "验证失败日志应该被记录"
    
    # 验证：日志级别是WARNING
    assert entry.level == "WARNING", "验证失败日志级别应该是WARNING"
    
    # 验证：上下文包含必要信息
    assert 'stage' in entry.context, "上下文应该包含stage"
    assert 'entity_id' in entry.context, "上下文应该包含entity_id"
    assert 'reason' in entry.context, "上下文应该包含reason"
    assert 'details' in entry.context, "上下文应该包含details"
    assert 'event_type' in entry.context, "上下文应该包含event_type"
    
    # 验证：事件类型正确
    assert entry.context['event_type'] == "VALIDATION_FAILURE", \
        "事件类型应该是VALIDATION_FAILURE"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(params=z2h_certification_params_strategy())
def test_property_52_z2h_certification_logging(logger_instance, params):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - Z2H Certification
    
    When Z2H certification is granted, the system should log the certification details.
    
    白皮书依据: 第四章 4.10.4 Z2H认证日志 - Requirement 12.4
    Validates: Requirements 12.4, 12.7
    """
    # 清空之前的日志
    logger_instance.clear_entries()
    
    # 记录Z2H认证
    entry = logger_instance.log_z2h_certification(
        strategy_id=params['strategy_id'],
        certification_level=params['certification_level'],
        capsule_id=params['capsule_id'],
        metrics=params['metrics']
    )
    
    # 验证：日志条目应该存在
    assert entry is not None, "Z2H认证日志应该被记录"
    
    # 验证：上下文包含必要信息
    assert 'strategy_id' in entry.context, "上下文应该包含strategy_id"
    assert 'certification_level' in entry.context, "上下文应该包含certification_level"
    assert 'capsule_id' in entry.context, "上下文应该包含capsule_id"
    assert 'metrics' in entry.context, "上下文应该包含metrics"
    assert 'event_type' in entry.context, "上下文应该包含event_type"
    
    # 验证：事件类型正确
    assert entry.context['event_type'] == "Z2H_CERTIFICATION", \
        "事件类型应该是Z2H_CERTIFICATION"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(params=decay_detection_params_strategy())
def test_property_52_decay_detection_logging(logger_instance, params):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - Decay Detection
    
    When factor decay is detected, the system should log the decay metrics and severity.
    
    白皮书依据: 第四章 4.10.5 衰减检测日志 - Requirement 12.5
    Validates: Requirements 12.5, 12.7
    """
    # 清空之前的日志
    logger_instance.clear_entries()
    
    # 记录衰减检测
    entry = logger_instance.log_decay_detection(
        factor_id=params['factor_id'],
        severity=params['severity'],
        ic_value=params['ic_value'],
        consecutive_days=params['consecutive_days']
    )
    
    # 验证：日志条目应该存在
    assert entry is not None, "衰减检测日志应该被记录"
    
    # 验证：日志级别是WARNING
    assert entry.level == "WARNING", "衰减检测日志级别应该是WARNING"
    
    # 验证：上下文包含必要信息
    assert 'factor_id' in entry.context, "上下文应该包含factor_id"
    assert 'severity' in entry.context, "上下文应该包含severity"
    assert 'ic_value' in entry.context, "上下文应该包含ic_value"
    assert 'consecutive_days' in entry.context, "上下文应该包含consecutive_days"
    assert 'event_type' in entry.context, "上下文应该包含event_type"
    
    # 验证：事件类型正确
    assert entry.context['event_type'] == "DECAY_DETECTION", \
        "事件类型应该是DECAY_DETECTION"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    message=st.text(min_size=1, max_size=100),
    log_level=st.sampled_from([LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL])
)
def test_property_52_structured_json_format(message, log_level):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - JSON Format
    
    The system should use structured logging with JSON format.
    
    白皮书依据: 第四章 4.10.6 结构化日志 - Requirement 12.6
    Validates: Requirements 12.6
    """
    # 创建日志器
    logger_instance = StructuredLogger("json_test", LogLevel.DEBUG)
    
    # 记录日志
    log_func = getattr(logger_instance, log_level.value.lower())
    entry = log_func(message, test_key="test_value")
    
    # 验证：日志条目应该存在
    assert entry is not None, "日志应该被记录"
    
    # 验证：可以转换为JSON
    json_str = entry.to_json()
    assert json_str is not None, "日志应该可以转换为JSON"
    assert len(json_str) > 0, "JSON字符串不应为空"
    
    # 验证：可以转换为字典
    log_dict = entry.to_dict()
    assert 'timestamp' in log_dict, "字典应该包含timestamp"
    assert 'level' in log_dict, "字典应该包含level"
    assert 'module' in log_dict, "字典应该包含module"
    assert 'correlation_id' in log_dict, "字典应该包含correlation_id"
    assert 'message' in log_dict, "字典应该包含message"
    assert 'context' in log_dict, "字典应该包含context"


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    log_level=st.sampled_from([LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL])
)
def test_property_52_log_level_configuration(log_level):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 52: Comprehensive Logging - Log Level Configuration
    
    The system should support log level configuration.
    
    白皮书依据: 第四章 4.10.8 日志级别配置 - Requirement 12.8
    Validates: Requirements 12.8
    """
    # 创建日志器，设置日志级别
    logger_instance = StructuredLogger("level_test", log_level)
    
    # 验证：日志级别已设置
    assert logger_instance.log_level == log_level, \
        f"日志级别应该是{log_level}"
    
    # 测试日志过滤
    logger_instance.clear_entries()
    
    # 记录所有级别的日志
    logger_instance.debug("debug message")
    logger_instance.info("info message")
    logger_instance.warning("warning message")
    logger_instance.error("error message")
    logger_instance.critical("critical message")
    
    # 获取记录的日志
    entries = logger_instance.get_entries()
    
    # 验证：只有达到或超过设置级别的日志被记录
    level_order = {
        LogLevel.DEBUG: 0,
        LogLevel.INFO: 1,
        LogLevel.WARNING: 2,
        LogLevel.ERROR: 3,
        LogLevel.CRITICAL: 4
    }
    
    expected_count = 5 - level_order[log_level]
    assert len(entries) == expected_count, \
        f"应该记录{expected_count}条日志，实际: {len(entries)}"
