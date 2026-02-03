"""风险因子数据模型Property-Based Testing

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统

测试属性:
- Property 1: 因子有效性（risk_value ∈ [0,1], confidence ∈ [0,1]）
- Property 2: 因子类型正确性（factor_type ∈ {flow, microstructure, portfolio}）
- Property 3: 序列化往返一致性（to_dict → from_dict preserves data）
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
from src.evolution.risk_mining.risk_factor import (
    RiskFactor,
    RiskEvent,
    RiskEventType
)


# ============================================================================
# Hypothesis Strategies (测试数据生成策略)
# ============================================================================

# 有效的因子类型
valid_factor_types = st.sampled_from(['flow', 'microstructure', 'portfolio'])

# 有效的风险值 [0, 1]
valid_risk_values = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 有效的置信度 [0, 1]
valid_confidences = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 有效的标的代码
valid_symbols = st.text(min_size=1, max_size=20, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    whitelist_characters='.'
))

# 有效的时间戳（最近30天）
valid_timestamps = st.datetimes(
    min_value=datetime.now() - timedelta(days=30),
    max_value=datetime.now() + timedelta(days=1)
)

# 有效的元数据
valid_metadata = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(
        st.floats(allow_nan=False, allow_infinity=False),
        st.integers(),
        st.text(max_size=50),
        st.lists(st.tuples(st.text(max_size=20), st.floats(allow_nan=False, allow_infinity=False)))
    ),
    max_size=5
)

# 完整的RiskFactor策略
risk_factor_strategy = st.builds(
    RiskFactor,
    factor_type=valid_factor_types,
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)


# ============================================================================
# Property 1: 因子有效性
# **Validates: Requirements 1.1-1.3**
# ============================================================================

@given(risk_factor_strategy)
def test_property_factor_validity(factor: RiskFactor):
    """Property 1: 所有因子字段在有效范围内
    
    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 数据验证
    
    属性:
    - risk_value ∈ [0, 1]
    - confidence ∈ [0, 1]
    - factor_type ∈ {flow, microstructure, portfolio}
    - symbol 非空
    - timestamp 是datetime对象
    - metadata 是dict
    """
    # 验证risk_value范围
    assert 0 <= factor.risk_value <= 1, \
        f"risk_value {factor.risk_value} not in [0, 1]"
    
    # 验证confidence范围
    assert 0 <= factor.confidence <= 1, \
        f"confidence {factor.confidence} not in [0, 1]"
    
    # 验证factor_type
    assert factor.factor_type in {'flow', 'microstructure', 'portfolio'}, \
        f"factor_type {factor.factor_type} not in valid types"
    
    # 验证symbol
    assert isinstance(factor.symbol, str) and len(factor.symbol) > 0, \
        f"symbol {factor.symbol} is not a non-empty string"
    
    # 验证timestamp
    assert isinstance(factor.timestamp, datetime), \
        f"timestamp {factor.timestamp} is not a datetime object"
    
    # 验证metadata
    assert isinstance(factor.metadata, dict), \
        f"metadata {factor.metadata} is not a dict"


@given(
    factor_type=valid_factor_types,
    symbol=valid_symbols,
    risk_value=st.floats(min_value=-10.0, max_value=-0.001),  # 无效：< 0
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_invalid_risk_value_lower(
    factor_type: str,
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 1.1: risk_value < 0 应该抛出异常"""
    with pytest.raises(ValueError, match="risk_value must be in"):
        RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata=metadata
        )


@given(
    factor_type=valid_factor_types,
    symbol=valid_symbols,
    risk_value=st.floats(min_value=1.001, max_value=10.0),  # 无效：> 1
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_invalid_risk_value_upper(
    factor_type: str,
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 1.2: risk_value > 1 应该抛出异常"""
    with pytest.raises(ValueError, match="risk_value must be in"):
        RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata=metadata
        )


@given(
    factor_type=valid_factor_types,
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=st.floats(min_value=-10.0, max_value=-0.001),  # 无效：< 0
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_invalid_confidence_lower(
    factor_type: str,
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 1.3: confidence < 0 应该抛出异常"""
    with pytest.raises(ValueError, match="confidence must be in"):
        RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata=metadata
        )


@given(
    factor_type=valid_factor_types,
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=st.floats(min_value=1.001, max_value=10.0),  # 无效：> 1
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_invalid_confidence_upper(
    factor_type: str,
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 1.4: confidence > 1 应该抛出异常"""
    with pytest.raises(ValueError, match="confidence must be in"):
        RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata=metadata
        )


# ============================================================================
# Property 2: 因子类型正确性
# **Validates: Requirements 1.1-1.3**
# ============================================================================

@given(
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_factor_type_flow(
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 2.1: factor_type='flow' 应该被接受"""
    factor = RiskFactor(
        factor_type='flow',
        symbol=symbol,
        risk_value=risk_value,
        confidence=confidence,
        timestamp=timestamp,
        metadata=metadata
    )
    assert factor.factor_type == 'flow'


@given(
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_factor_type_microstructure(
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 2.2: factor_type='microstructure' 应该被接受"""
    factor = RiskFactor(
        factor_type='microstructure',
        symbol=symbol,
        risk_value=risk_value,
        confidence=confidence,
        timestamp=timestamp,
        metadata=metadata
    )
    assert factor.factor_type == 'microstructure'


@given(
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_factor_type_portfolio(
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 2.3: factor_type='portfolio' 应该被接受"""
    factor = RiskFactor(
        factor_type='portfolio',
        symbol=symbol,
        risk_value=risk_value,
        confidence=confidence,
        timestamp=timestamp,
        metadata=metadata
    )
    assert factor.factor_type == 'portfolio'


@given(
    factor_type=st.text(min_size=1, max_size=20).filter(
        lambda x: x not in {'flow', 'microstructure', 'portfolio'}
    ),
    symbol=valid_symbols,
    risk_value=valid_risk_values,
    confidence=valid_confidences,
    timestamp=valid_timestamps,
    metadata=valid_metadata
)
def test_property_invalid_factor_type(
    factor_type: str,
    symbol: str,
    risk_value: float,
    confidence: float,
    timestamp: datetime,
    metadata: dict
):
    """Property 2.4: 无效的factor_type应该抛出异常"""
    with pytest.raises(ValueError, match="factor_type must be one of"):
        RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata=metadata
        )


# ============================================================================
# Property 3: 序列化往返一致性
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(risk_factor_strategy)
def test_property_serialization_roundtrip(factor: RiskFactor):
    """Property 3: 序列化往返一致性
    
    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 数据序列化
    
    属性:
    - to_dict() → from_dict() 应该保留所有数据
    - 往返后的对象应该与原对象相等
    """
    # 序列化
    data = factor.to_dict()
    
    # 验证序列化结果是dict
    assert isinstance(data, dict)
    
    # 反序列化
    restored = RiskFactor.from_dict(data)
    
    # 验证往返一致性
    assert restored.factor_type == factor.factor_type, \
        f"factor_type mismatch: {restored.factor_type} != {factor.factor_type}"
    
    assert restored.symbol == factor.symbol, \
        f"symbol mismatch: {restored.symbol} != {factor.symbol}"
    
    assert abs(restored.risk_value - factor.risk_value) < 1e-6, \
        f"risk_value mismatch: {restored.risk_value} != {factor.risk_value}"
    
    assert abs(restored.confidence - factor.confidence) < 1e-6, \
        f"confidence mismatch: {restored.confidence} != {factor.confidence}"
    
    assert restored.timestamp == factor.timestamp, \
        f"timestamp mismatch: {restored.timestamp} != {factor.timestamp}"
    
    assert restored.metadata == factor.metadata, \
        f"metadata mismatch: {restored.metadata} != {factor.metadata}"
    
    # 验证相等性
    assert restored == factor, \
        f"Restored factor not equal to original"


@given(risk_factor_strategy)
def test_property_to_dict_contains_all_fields(factor: RiskFactor):
    """Property 3.1: to_dict()应该包含所有必需字段"""
    data = factor.to_dict()
    
    required_fields = {'factor_type', 'symbol', 'risk_value', 'confidence', 'timestamp', 'metadata'}
    
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@given(risk_factor_strategy)
def test_property_from_dict_validates_data(factor: RiskFactor):
    """Property 3.2: from_dict()应该验证数据有效性"""
    data = factor.to_dict()
    
    # 修改为无效的risk_value
    data['risk_value'] = 1.5
    
    with pytest.raises(ValueError):
        RiskFactor.from_dict(data)


# ============================================================================
# Property 4: RiskEvent属性测试
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(
    factor=risk_factor_strategy,
    timestamp=valid_timestamps
)
def test_property_risk_event_validity(factor: RiskFactor, timestamp: datetime):
    """Property 4: RiskEvent有效性
    
    属性:
    - event_type 是RiskEventType枚举
    - symbol 与factor.symbol一致
    - factor 是RiskFactor对象
    - timestamp 是datetime对象
    """
    event = RiskEvent(
        event_type=RiskEventType.RISK_FACTOR_GENERATED,
        symbol=factor.symbol,
        factor=factor,
        timestamp=timestamp
    )
    
    assert isinstance(event.event_type, RiskEventType)
    assert event.symbol == factor.symbol
    assert isinstance(event.factor, RiskFactor)
    assert isinstance(event.timestamp, datetime)


@given(
    factor=risk_factor_strategy,
    symbol=valid_symbols.filter(lambda x: len(x) > 0),
    timestamp=valid_timestamps
)
def test_property_risk_event_symbol_consistency(
    factor: RiskFactor,
    symbol: str,
    timestamp: datetime
):
    """Property 4.1: RiskEvent的symbol必须与factor.symbol一致"""
    # 如果symbol与factor.symbol不同，应该抛出异常
    if symbol != factor.symbol:
        with pytest.raises(ValueError, match="Event symbol .* does not match factor symbol"):
            RiskEvent(
                event_type=RiskEventType.RISK_FACTOR_GENERATED,
                symbol=symbol,
                factor=factor,
                timestamp=timestamp
            )
    else:
        # 如果symbol与factor.symbol相同，应该成功创建
        event = RiskEvent(
            event_type=RiskEventType.RISK_FACTOR_GENERATED,
            symbol=symbol,
            factor=factor,
            timestamp=timestamp
        )
        assert event.symbol == factor.symbol


@given(
    factor=risk_factor_strategy,
    timestamp=valid_timestamps
)
def test_property_risk_event_serialization_roundtrip(
    factor: RiskFactor,
    timestamp: datetime
):
    """Property 4.2: RiskEvent序列化往返一致性"""
    event = RiskEvent(
        event_type=RiskEventType.RISK_FACTOR_GENERATED,
        symbol=factor.symbol,
        factor=factor,
        timestamp=timestamp
    )
    
    # 序列化
    data = event.to_dict()
    
    # 验证序列化结果是dict
    assert isinstance(data, dict)
    
    # 反序列化
    restored = RiskEvent.from_dict(data)
    
    # 验证往返一致性
    assert restored.event_type == event.event_type
    assert restored.symbol == event.symbol
    assert restored.factor == event.factor
    assert restored.timestamp == event.timestamp


# ============================================================================
# Property 5: 相等性和哈希属性
# **Validates: Requirements 1.1-1.3**
# ============================================================================

@given(risk_factor_strategy)
def test_property_equality_reflexive(factor: RiskFactor):
    """Property 5.1: 相等性是自反的（x == x）"""
    assert factor == factor


@given(risk_factor_strategy, risk_factor_strategy)
def test_property_equality_symmetric(factor1: RiskFactor, factor2: RiskFactor):
    """Property 5.2: 相等性是对称的（x == y → y == x）"""
    if factor1 == factor2:
        assert factor2 == factor1


@given(risk_factor_strategy)
def test_property_hash_consistency(factor: RiskFactor):
    """Property 5.3: 哈希一致性（相等的对象有相同的哈希值）"""
    # 创建相同的因子
    factor_copy = RiskFactor(
        factor_type=factor.factor_type,
        symbol=factor.symbol,
        risk_value=factor.risk_value,
        confidence=factor.confidence,
        timestamp=factor.timestamp,
        metadata=factor.metadata
    )
    
    if factor == factor_copy:
        assert hash(factor) == hash(factor_copy)


@given(st.lists(risk_factor_strategy, min_size=1, max_size=10))
def test_property_hash_in_set(factors: list):
    """Property 5.4: 哈希在集合中的使用"""
    # 将因子添加到集合
    factor_set = set(factors)
    
    # 集合大小应该 <= 列表大小（因为可能有重复）
    assert len(factor_set) <= len(factors)
    
    # 所有因子都应该能在集合中找到
    for factor in factors:
        assert factor in factor_set
