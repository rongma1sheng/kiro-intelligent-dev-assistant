"""RiskFactorRegistry Property-Based Testing

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 统一接口

测试属性:
- Property 1: 因子有效性（所有添加的因子都有效）
- Property 2: 风险值单调性（风险越大，risk_value越高）
- Property 3: 因子类型正确性（查询返回正确类型的因子）
- Property 4: 因子不重复（collect_factors返回的因子不重复）
- Property 5: 因子类型过滤正确性（get_latest_factor返回正确类型）
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.evolution.risk_mining.risk_factor_registry import RiskFactorRegistry
from src.evolution.risk_mining.risk_factor import RiskFactor
from src.infra.event_bus import EventBus


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
        st.text(max_size=50)
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


def create_mock_event_bus():
    """创建mock EventBus"""
    bus = Mock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


# ============================================================================
# Property 1: 因子有效性
# **Validates: Requirements 1.1-1.3, 2.1-2.3**
# ============================================================================

@given(st.lists(risk_factor_strategy, min_size=1, max_size=20))
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_all_added_factors_are_valid(factors: list):
    """Property 1: 所有添加到注册中心的因子都是有效的
    
    白皮书依据: 第四章 4.1.1 - 因子存储
    
    属性:
    - 添加的所有因子都满足有效性约束
    - risk_value ∈ [0, 1]
    - confidence ∈ [0, 1]
    - factor_type ∈ {flow, microstructure, portfolio}
    """
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 添加所有因子
    for factor in factors:
        await registry.add_factor(factor)
    
    # 收集所有因子
    all_factors = []
    for symbol in set(f.symbol for f in factors):
        symbol_factors = await registry.collect_factors(symbol)
        all_factors.extend(symbol_factors)
    
    # 验证所有因子都有效
    for factor in all_factors:
        assert 0 <= factor.risk_value <= 1, \
            f"Invalid risk_value: {factor.risk_value}"
        assert 0 <= factor.confidence <= 1, \
            f"Invalid confidence: {factor.confidence}"
        assert factor.factor_type in {'flow', 'microstructure', 'portfolio'}, \
            f"Invalid factor_type: {factor.factor_type}"


# ============================================================================
# Property 2: 风险值单调性
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(
    symbol=valid_symbols,
    factor_type=valid_factor_types,
    risk_values=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=10
    )
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_risk_value_ordering(
    symbol: str,
    factor_type: str,
    risk_values: list
):
    """Property 2: 风险值排序属性
    
    白皮书依据: 第四章 4.1.1 - 风险值单调性
    
    属性:
    - 添加多个因子后，collect_factors应该按时间戳降序返回
    - 最新的因子应该在列表开头
    """
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 添加因子（按时间顺序）
    base_time = datetime.now()
    for i, risk_value in enumerate(risk_values):
        factor = RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=0.9,
            timestamp=base_time + timedelta(seconds=i),
            metadata={'index': i}
        )
        await registry.add_factor(factor)
    
    # 收集因子
    factors = await registry.collect_factors(symbol)
    
    # 验证按时间戳降序排列
    for i in range(len(factors) - 1):
        assert factors[i].timestamp >= factors[i + 1].timestamp, \
            f"Factors not sorted by timestamp: {factors[i].timestamp} < {factors[i + 1].timestamp}"


@given(
    symbol=valid_symbols,
    factor_type=valid_factor_types,
    risk_values=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=10
    ).filter(lambda x: len(x) == len(set(x)))  # 确保risk_values不重复
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_latest_factor_has_latest_timestamp(
    symbol: str,
    factor_type: str,
    risk_values: list
):
    """Property 2.1: get_latest_factor返回时间戳最新的因子
    
    属性:
    - get_latest_factor返回的因子应该有最新的时间戳
    """
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 添加因子
    base_time = datetime.now()
    latest_timestamp = base_time
    latest_risk_value = risk_values[0]
    
    for i, risk_value in enumerate(risk_values):
        timestamp = base_time + timedelta(seconds=i)
        if timestamp > latest_timestamp:
            latest_timestamp = timestamp
            latest_risk_value = risk_value
        
        factor = RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=0.9,
            timestamp=timestamp,
            metadata={'index': i}
        )
        await registry.add_factor(factor)
    
    # 获取最新因子
    latest = await registry.get_latest_factor(symbol, factor_type)
    
    assert latest is not None
    assert latest.timestamp == latest_timestamp, \
        f"Latest factor timestamp mismatch: {latest.timestamp} != {latest_timestamp}"
    assert abs(latest.risk_value - latest_risk_value) < 1e-6, \
        f"Latest factor risk_value mismatch: {latest.risk_value} != {latest_risk_value}"


# ============================================================================
# Property 3: 因子类型正确性
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(
    symbol=valid_symbols,
    factors=st.lists(
        st.tuples(
            valid_factor_types,
            valid_risk_values,
            valid_confidences,
            valid_timestamps
        ),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_factor_type_correctness(
    symbol: str,
    factors: list
):
    """Property 3: 因子类型正确性
    
    白皮书依据: 第四章 4.1.1 - 因子类型过滤
    
    属性:
    - get_latest_factor(symbol, type)返回的因子类型应该与请求的类型一致
    - collect_factors返回的所有因子都应该有有效的类型
    """
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 添加因子
    for factor_type, risk_value, confidence, timestamp in factors:
        factor = RiskFactor(
            factor_type=factor_type,
            symbol=symbol,
            risk_value=risk_value,
            confidence=confidence,
            timestamp=timestamp,
            metadata={}
        )
        await registry.add_factor(factor)
    
    # 验证每种类型的最新因子
    for factor_type in ['flow', 'microstructure', 'portfolio']:
        latest = await registry.get_latest_factor(symbol, factor_type)
        
        if latest is not None:
            assert latest.factor_type == factor_type, \
                f"Factor type mismatch: {latest.factor_type} != {factor_type}"
    
    # 验证collect_factors返回的所有因子
    all_factors = await registry.collect_factors(symbol)
    for factor in all_factors:
        assert factor.factor_type in {'flow', 'microstructure', 'portfolio'}, \
            f"Invalid factor type: {factor.factor_type}"


@given(
    symbol=valid_symbols,
    factor_type=valid_factor_types,
    count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_get_latest_factor_returns_correct_type(
    symbol: str,
    factor_type: str,
    count: int
):
    """Property 3.1: get_latest_factor只返回请求类型的因子
    
    属性:
    - 即使有其他类型的因子，get_latest_factor也只返回请求类型的因子
    """
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 添加不同类型的因子
    base_time = datetime.now()
    for i in range(count):
        for ftype in ['flow', 'microstructure', 'portfolio']:
            factor = RiskFactor(
                factor_type=ftype,
                symbol=symbol,
                risk_value=0.5,
                confidence=0.9,
                timestamp=base_time + timedelta(seconds=i),
                metadata={'type': ftype, 'index': i}
            )
            await registry.add_factor(factor)
    
    # 获取指定类型的最新因子
    latest = await registry.get_latest_factor(symbol, factor_type)
    
    assert latest is not None
    assert latest.factor_type == factor_type, \
        f"Returned wrong factor type: {latest.factor_type} != {factor_type}"


# ============================================================================
# Property 4: 因子不重复
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(
    symbol=valid_symbols,
    factors=st.lists(risk_factor_strategy, min_size=1, max_size=20)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_no_duplicate_factors(symbol: str, factors: list):
    """Property 4: 因子不重复
    
    白皮书依据: 第四章 4.1.1 - 因子唯一性
    
    属性:
    - collect_factors返回的因子列表中不应该有重复的因子
    - 每个因子应该是唯一的（基于对象标识）
    """
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 修改所有因子的symbol为相同值
    for factor in factors:
        factor.symbol = symbol
        await registry.add_factor(factor)
    
    # 收集因子
    collected = await registry.collect_factors(symbol)
    
    # 验证没有重复（使用id比较）
    factor_ids = [id(f) for f in collected]
    assert len(factor_ids) == len(set(factor_ids)), \
        f"Duplicate factors found: {len(factor_ids)} != {len(set(factor_ids))}"


@given(
    symbol=valid_symbols,
    count=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_factor_count_consistency(symbol: str, count: int):
    """Property 4.1: 因子数量一致性
    
    属性:
    - 添加N个因子后，get_factor_count应该返回N（或max_factors_per_symbol）
    """
    registry = RiskFactorRegistry(create_mock_event_bus(), max_factors_per_symbol=100)
    
    # 添加因子
    for i in range(count):
        factor = RiskFactor(
            factor_type='flow',
            symbol=symbol,
            risk_value=0.5,
            confidence=0.9,
            timestamp=datetime.now() + timedelta(seconds=i),
            metadata={'index': i}
        )
        await registry.add_factor(factor)
    
    # 验证因子数量
    actual_count = registry.get_factor_count(symbol)
    expected_count = min(count, 100)  # 受max_factors_per_symbol限制
    
    assert actual_count == expected_count, \
        f"Factor count mismatch: {actual_count} != {expected_count}"


# ============================================================================
# Property 5: 因子类型过滤正确性
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(
    symbol=valid_symbols,
    flow_count=st.integers(min_value=0, max_value=5),
    micro_count=st.integers(min_value=0, max_value=5),
    portfolio_count=st.integers(min_value=0, max_value=5)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_factor_type_filtering(
    symbol: str,
    flow_count: int,
    micro_count: int,
    portfolio_count: int
):
    """Property 5: 因子类型过滤正确性
    
    白皮书依据: 第四章 4.1.1 - 因子类型过滤
    
    属性:
    - get_latest_factor应该只返回指定类型的因子
    - 不同类型的因子应该独立管理
    """
    assume(flow_count + micro_count + portfolio_count > 0)
    
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 添加不同类型的因子
    base_time = datetime.now()
    
    for i in range(flow_count):
        factor = RiskFactor(
            factor_type='flow',
            symbol=symbol,
            risk_value=0.5,
            confidence=0.9,
            timestamp=base_time + timedelta(seconds=i),
            metadata={'type': 'flow', 'index': i}
        )
        await registry.add_factor(factor)
    
    for i in range(micro_count):
        factor = RiskFactor(
            factor_type='microstructure',
            symbol=symbol,
            risk_value=0.6,
            confidence=0.85,
            timestamp=base_time + timedelta(seconds=i),
            metadata={'type': 'micro', 'index': i}
        )
        await registry.add_factor(factor)
    
    for i in range(portfolio_count):
        factor = RiskFactor(
            factor_type='portfolio',
            symbol=symbol,
            risk_value=0.7,
            confidence=0.8,
            timestamp=base_time + timedelta(seconds=i),
            metadata={'type': 'portfolio', 'index': i}
        )
        await registry.add_factor(factor)
    
    # 验证每种类型的最新因子
    if flow_count > 0:
        latest_flow = await registry.get_latest_factor(symbol, 'flow')
        assert latest_flow is not None
        assert latest_flow.factor_type == 'flow'
        assert latest_flow.metadata['type'] == 'flow'
    
    if micro_count > 0:
        latest_micro = await registry.get_latest_factor(symbol, 'microstructure')
        assert latest_micro is not None
        assert latest_micro.factor_type == 'microstructure'
        assert latest_micro.metadata['type'] == 'micro'
    
    if portfolio_count > 0:
        latest_portfolio = await registry.get_latest_factor(symbol, 'portfolio')
        assert latest_portfolio is not None
        assert latest_portfolio.factor_type == 'portfolio'
        assert latest_portfolio.metadata['type'] == 'portfolio'


@given(
    symbol=valid_symbols,
    factor_type=valid_factor_types,
    other_type=valid_factor_types
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_type_isolation(
    symbol: str,
    factor_type: str,
    other_type: str
):
    """Property 5.1: 因子类型隔离
    
    属性:
    - 添加一种类型的因子不应该影响其他类型的查询结果
    """
    assume(factor_type != other_type)
    
    registry = RiskFactorRegistry(create_mock_event_bus())
    
    # 只添加一种类型的因子
    factor = RiskFactor(
        factor_type=factor_type,
        symbol=symbol,
        risk_value=0.8,
        confidence=0.9,
        timestamp=datetime.now(),
        metadata={}
    )
    await registry.add_factor(factor)
    
    # 查询添加的类型应该有结果
    latest_added = await registry.get_latest_factor(symbol, factor_type)
    assert latest_added is not None
    assert latest_added.factor_type == factor_type
    
    # 查询其他类型应该没有结果
    latest_other = await registry.get_latest_factor(symbol, other_type)
    assert latest_other is None


# ============================================================================
# Property 6: 因子限制属性
# **Validates: Requirements 2.1-2.3**
# ============================================================================

@given(
    symbol=valid_symbols,
    max_factors=st.integers(min_value=1, max_value=20),
    add_count=st.integers(min_value=1, max_value=50)
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_property_factor_limit_enforcement(
    symbol: str,
    max_factors: int,
    add_count: int
):
    """Property 6: 因子数量限制强制执行
    
    白皮书依据: 第四章 4.1.1 - 因子数量限制
    
    属性:
    - 添加超过max_factors_per_symbol的因子后
    - 实际存储的因子数量不应该超过限制
    - 应该保留最新的因子
    """
    registry = RiskFactorRegistry(
        create_mock_event_bus(),
        max_factors_per_symbol=max_factors
    )
    
    # 添加因子
    base_time = datetime.now()
    for i in range(add_count):
        factor = RiskFactor(
            factor_type='flow',
            symbol=symbol,
            risk_value=0.5,
            confidence=0.9,
            timestamp=base_time + timedelta(seconds=i),
            metadata={'index': i}
        )
        await registry.add_factor(factor)
    
    # 验证因子数量不超过限制
    actual_count = registry.get_factor_count(symbol)
    assert actual_count <= max_factors, \
        f"Factor count exceeds limit: {actual_count} > {max_factors}"
    
    # 如果添加的因子数超过限制，验证保留的是最新的因子
    if add_count > max_factors:
        factors = await registry.collect_factors(symbol)
        
        # 验证保留的因子数量
        assert len(factors) == max_factors
        
        # 验证保留的是最新的因子（最后max_factors个）
        expected_indices = list(range(add_count - max_factors, add_count))
        actual_indices = sorted([f.metadata['index'] for f in factors])
        
        assert actual_indices == expected_indices, \
            f"Wrong factors retained: {actual_indices} != {expected_indices}"
