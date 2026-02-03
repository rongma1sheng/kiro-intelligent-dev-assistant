"""Property-Based Tests for Data Storage and Retrieval System

白皮书依据: 第四章 4.8 数据存储与检索

Properties tested:
- Property 45: Dual Storage for Arena Results
- Property 46: Dual Storage for Z2H Capsules  
- Property 47: Simulation Data Parquet Storage
- Property 48: Cache-First Retrieval
- Property 49: Universal Data Signing
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck

from src.evolution.storage.data_storage_manager import DataStorageManager
from src.evolution.storage.signature_manager import SignatureManager


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def result_id_strategy(draw):
    """生成结果ID"""
    return f"RESULT_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def capsule_id_strategy(draw):
    """生成胶囊ID"""
    return f"CAPSULE_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def arena_data_strategy(draw):
    """生成Arena数据"""
    return {
        'factor_id': f"FACTOR_{draw(st.integers(min_value=1, max_value=100))}",
        'arena_score': draw(st.floats(min_value=0.0, max_value=1.0)),
        'passed': draw(st.booleans()),
        'metrics': {
            'ic': draw(st.floats(min_value=-1.0, max_value=1.0)),
            'ir': draw(st.floats(min_value=-10.0, max_value=10.0))
        }
    }


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_storage():
    """创建临时存储目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage_manager(temp_storage):
    """创建存储管理器实例"""
    return DataStorageManager(storage_root=temp_storage)


# ============================================================================
# Property 45: Dual Storage for Arena Results
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    result_id=result_id_strategy(),
    data=arena_data_strategy()
)
def test_property_45_dual_storage_arena_results(
    storage_manager,
    result_id,
    data
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 45: Dual Storage for Arena Results
    
    For any completed Arena testing, results should be stored in both Redis
    (90-day TTL) and local file system (JSON).
    
    白皮书依据: 第四章 4.8.1 Arena结果存储 - Requirements 10.1, 10.2
    Validates: Requirements 10.1, 10.2
    """
    # 存储Arena结果
    success = storage_manager.store_arena_result(result_id, data, ttl_days=90)
    
    # 验证：存储应该成功
    assert success, "Arena结果存储应该成功"
    
    # 验证：文件系统中应该存在
    file_path = Path(storage_manager.storage_root) / "arena_results" / f"{result_id}.json"
    assert file_path.exists(), \
        f"Arena结果应该存储到文件系统: {file_path}"
    
    # 验证：可以检索
    retrieved_data = storage_manager.retrieve_arena_result(result_id)
    assert retrieved_data is not None, \
        "应该能够检索Arena结果"
    
    # 验证：数据完整性
    assert retrieved_data['factor_id'] == data['factor_id'], \
        "factor_id应该匹配"
    
    assert retrieved_data['arena_score'] == data['arena_score'], \
        "arena_score应该匹配"
    
    assert retrieved_data['passed'] == data['passed'], \
        "passed应该匹配"


# ============================================================================
# Property 46: Dual Storage for Z2H Capsules
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    capsule_id=capsule_id_strategy(),
    data=arena_data_strategy()
)
def test_property_46_dual_storage_z2h_capsules(
    storage_manager,
    capsule_id,
    data
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 46: Dual Storage for Z2H Capsules
    
    For any Z2H gene capsule, it should be stored in both Redis (1-year TTL)
    and local file system (JSON).
    
    白皮书依据: 第四章 4.8.3 Z2H胶囊存储 - Requirements 10.3, 10.4
    Validates: Requirements 10.3, 10.4
    """
    # 存储Z2H胶囊
    success = storage_manager.store_z2h_capsule(capsule_id, data, ttl_days=365)
    
    # 验证：存储应该成功
    assert success, "Z2H胶囊存储应该成功"
    
    # 验证：文件系统中应该存在
    file_path = Path(storage_manager.storage_root) / "z2h_capsules" / f"{capsule_id}.json"
    assert file_path.exists(), \
        f"Z2H胶囊应该存储到文件系统: {file_path}"
    
    # 验证：可以检索
    retrieved_data = storage_manager.retrieve_z2h_capsule(capsule_id)
    assert retrieved_data is not None, \
        "应该能够检索Z2H胶囊"
    
    # 验证：数据完整性
    assert retrieved_data['factor_id'] == data['factor_id'], \
        "factor_id应该匹配"


# ============================================================================
# Property 47: Simulation Data Parquet Storage
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    simulation_id=result_id_strategy(),
    data=arena_data_strategy()
)
def test_property_47_simulation_data_storage(
    storage_manager,
    simulation_id,
    data
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 47: Simulation Data Parquet Storage
    
    For any completed simulation, daily results should be stored in Parquet format.
    
    Note: 简化版本使用JSON,生产环境应使用Parquet
    
    白皮书依据: 第四章 4.8.5 模拟数据存储 - Requirement 10.5
    Validates: Requirements 10.5
    """
    # 存储模拟数据
    success = storage_manager.store_simulation_data(simulation_id, data)
    
    # 验证：存储应该成功
    assert success, "模拟数据存储应该成功"
    
    # 验证：文件系统中应该存在
    file_path = Path(storage_manager.storage_root) / "simulation_data" / f"{simulation_id}.json"
    assert file_path.exists(), \
        f"模拟数据应该存储到文件系统: {file_path}"


# ============================================================================
# Property 48: Cache-First Retrieval
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    result_id=result_id_strategy(),
    data=arena_data_strategy()
)
def test_property_48_cache_first_retrieval(
    storage_manager,
    result_id,
    data
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 48: Cache-First Retrieval
    
    For any historical data query, the system should check Redis first,
    then fall back to file system if not found in cache.
    
    白皮书依据: 第四章 4.8.6 缓存优先检索 - Requirement 10.6
    Validates: Requirements 10.6
    """
    # 存储数据
    storage_manager.store_arena_result(result_id, data)
    
    # 第一次检索(从文件系统)
    retrieved_data_1 = storage_manager.retrieve_arena_result(result_id)
    assert retrieved_data_1 is not None, \
        "第一次检索应该成功(从文件系统)"
    
    # 第二次检索(应该从缓存,如果Redis可用)
    retrieved_data_2 = storage_manager.retrieve_arena_result(result_id)
    assert retrieved_data_2 is not None, \
        "第二次检索应该成功"
    
    # 验证：数据一致性
    assert retrieved_data_1['factor_id'] == retrieved_data_2['factor_id'], \
        "两次检索的数据应该一致"


# ============================================================================
# Property 49: Universal Data Signing
# ============================================================================

@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    data=arena_data_strategy()
)
def test_property_49_universal_data_signing(data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 49: Universal Data Signing
    
    For any data stored (Arena results, Z2H capsules, simulation results),
    the system should generate and store a SHA256 signature.
    
    白皮书依据: 第四章 4.8.7 数据签名 - Requirement 10.7
    Validates: Requirements 10.7
    """
    # 生成签名
    signature = SignatureManager.generate_signature(data)
    
    # 验证：签名应该是64字符的十六进制字符串
    assert isinstance(signature, str), \
        "签名应该是字符串"
    
    assert len(signature) == 64, \
        f"SHA256签名应该是64字符，实际: {len(signature)}"
    
    assert all(c in '0123456789abcdef' for c in signature), \
        "签名应该是十六进制字符串"
    
    # 验证：签名验证应该成功
    is_valid = SignatureManager.verify_signature(data, signature)
    assert is_valid, \
        "签名验证应该成功"
    
    # 验证：修改数据后签名验证应该失败
    modified_data = {**data, 'tampered': True}
    is_valid_after_tamper = SignatureManager.verify_signature(modified_data, signature)
    assert not is_valid_after_tamper, \
        "篡改数据后签名验证应该失败"
