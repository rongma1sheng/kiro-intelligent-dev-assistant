"""SPSC原子读写属性测试

白皮书依据: 第十二章 12.1.4 SharedMemory生命周期管理

**Property 9: SPSC Atomic Read-Write Round Trip**
**Validates: Requirements 4.4**

测试内容:
1. 写入-读取产生等价数据
2. 撕裂读检测
3. 数据完整性
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

from src.infra.spsc_manager import (
    SPSCManager,
    SPSCStats,
    get_spsc_manager,
    cleanup_all_managers
)


class TestSPSCRoundTripProperties:
    """SPSC原子读写属性测试
    
    **Validates: Requirements 4.4**
    """
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        """每个测试后清理"""
        yield
        cleanup_all_managers()
    
    @given(data=st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='_'
        )),
        values=st.one_of(
            st.integers(min_value=-1000000, max_value=1000000),
            st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
            st.text(min_size=0, max_size=50)
        ),
        min_size=1,
        max_size=10
    ))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_write_read_round_trip(self, data: dict):
        """Property 9: 写入-读取产生等价数据
        
        **Validates: Requirements 4.4**
        
        属性: 对于任意可序列化数据，write(data) 后 read() 应返回等价数据
        """
        # 使用唯一名称避免冲突
        name = f"test_roundtrip_{id(data)}_{time.time_ns()}"
        
        with SPSCManager(name, size=1024 * 1024, create=True) as manager:
            # 写入数据
            write_success = manager.atomic_write(data)
            assert write_success, "写入应该成功"
            
            # 读取数据
            read_data = manager.atomic_read()
            
            # 验证数据等价
            assert read_data is not None, "读取不应返回None"
            assert read_data == data, f"读取数据应等于写入数据: {read_data} != {data}"
    
    @given(
        int_value=st.integers(min_value=-1000000, max_value=1000000)
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_integer_round_trip(self, int_value: int):
        """Property: 整数往返
        
        **Validates: Requirements 4.4**
        
        属性: 整数写入后读取应保持不变
        """
        name = f"test_int_{id(int_value)}_{time.time_ns()}"
        
        with SPSCManager(name, size=1024, create=True) as manager:
            write_success = manager.atomic_write(int_value)
            assert write_success
            
            read_value = manager.atomic_read()
            assert read_value == int_value
    
    @given(
        float_value=st.floats(
            min_value=-1000,
            max_value=1000,
            allow_nan=False,
            allow_infinity=False
        )
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_float_round_trip(self, float_value: float):
        """Property: 浮点数往返
        
        **Validates: Requirements 4.4**
        
        属性: 浮点数写入后读取应保持不变（在精度范围内）
        """
        name = f"test_float_{id(float_value)}_{time.time_ns()}"
        
        with SPSCManager(name, size=1024, create=True) as manager:
            write_success = manager.atomic_write(float_value)
            assert write_success
            
            read_value = manager.atomic_read()
            assert abs(read_value - float_value) < 1e-10
    
    @given(
        list_data=st.lists(
            st.integers(min_value=-1000, max_value=1000),
            min_size=1,
            max_size=100
        )
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_list_round_trip(self, list_data: list):
        """Property: 列表往返
        
        **Validates: Requirements 4.4**
        
        属性: 列表写入后读取应保持不变
        """
        name = f"test_list_{id(list_data)}_{time.time_ns()}"
        
        with SPSCManager(name, size=1024 * 1024, create=True) as manager:
            write_success = manager.atomic_write(list_data)
            assert write_success
            
            read_value = manager.atomic_read()
            assert read_value == list_data
    
    @given(
        write_count=st.integers(min_value=1, max_value=10)
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_multiple_writes_last_value(self, write_count: int):
        """Property: 多次写入后读取最后值
        
        **Validates: Requirements 4.4**
        
        属性: 多次写入后，读取应返回最后写入的值
        """
        name = f"test_multi_{write_count}_{time.time_ns()}"
        
        with SPSCManager(name, size=1024, create=True) as manager:
            # 多次写入
            for i in range(write_count):
                manager.atomic_write({'value': i})
            
            # 读取应返回最后值
            read_value = manager.atomic_read()
            assert read_value == {'value': write_count - 1}


class TestSPSCStatsProperties:
    """SPSC统计属性测试"""
    
    @given(
        write_latencies=st.lists(
            st.floats(min_value=0.1, max_value=1000, allow_nan=False),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=50)
    def test_write_stats_accuracy(self, write_latencies: list):
        """Property: 写入统计准确性
        
        属性: 平均写入延迟应等于所有延迟的算术平均值
        """
        stats = SPSCStats()
        
        for latency in write_latencies:
            stats.record_write(latency)
        
        # 验证总数
        assert stats.total_writes == len(write_latencies)
        
        # 验证平均值（只保留最近100个）
        recent = write_latencies[-100:]
        expected_avg = sum(recent) / len(recent)
        assert abs(stats.avg_write_latency_us - expected_avg) < 0.001
    
    @given(
        read_count=st.integers(min_value=1, max_value=100),
        torn_count=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=50)
    def test_torn_read_counting(self, read_count: int, torn_count: int):
        """Property: 撕裂读计数
        
        属性: 撕裂读次数应正确累计
        """
        stats = SPSCStats()
        
        # 记录正常读取
        for _ in range(read_count):
            stats.record_read(10.0, is_torn=False)
        
        # 记录撕裂读
        for _ in range(torn_count):
            stats.record_read(0.0, is_torn=True)
        
        # 验证计数
        assert stats.total_reads == read_count + torn_count
        assert stats.torn_reads == torn_count


class TestSPSCManagerValidation:
    """SPSC管理器验证测试"""
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        """每个测试后清理"""
        yield
        cleanup_all_managers()
    
    def test_empty_name_raises_error(self):
        """Property: 空名称应抛出错误
        
        属性: name为空时应抛出ValueError
        """
        with pytest.raises(ValueError, match="共享内存名称不能为空"):
            SPSCManager("", size=1024, create=True)
    
    @given(size=st.integers(min_value=0, max_value=20))
    @settings(max_examples=20)
    def test_small_size_raises_error(self, size: int):
        """Property: 过小的大小应抛出错误
        
        属性: size <= HEADER_SIZE + FOOTER_SIZE 时应抛出ValueError
        """
        min_size = SPSCManager.HEADER_SIZE + SPSCManager.FOOTER_SIZE
        
        if size <= min_size:
            with pytest.raises(ValueError, match="共享内存大小必须"):
                SPSCManager(f"test_{size}", size=size, create=True)
    
    def test_context_manager_cleanup(self):
        """Property: 上下文管理器正确清理
        
        属性: 退出上下文后，共享内存应被清理
        """
        name = f"test_cleanup_{time.time_ns()}"
        
        with SPSCManager(name, size=1024, create=True) as manager:
            assert manager.is_available()
        
        # 退出后应已清理
        assert manager._cleaned


class TestSPSCDataIntegrity:
    """SPSC数据完整性测试"""
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        """每个测试后清理"""
        yield
        cleanup_all_managers()
    
    @given(
        nested_data=st.recursive(
            st.one_of(
                st.integers(min_value=-1000, max_value=1000),
                st.floats(min_value=-100, max_value=100, allow_nan=False, allow_infinity=False),
                st.text(min_size=0, max_size=20)
            ),
            lambda children: st.one_of(
                st.lists(children, max_size=5),
                st.dictionaries(
                    st.text(min_size=1, max_size=5, alphabet=st.characters(
                        whitelist_categories=('L', 'N')
                    )),
                    children,
                    max_size=5
                )
            ),
            max_leaves=20
        )
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
    )
    def test_nested_data_integrity(self, nested_data):
        """Property: 嵌套数据完整性
        
        **Validates: Requirements 4.4**
        
        属性: 嵌套数据结构写入后读取应保持完整
        """
        name = f"test_nested_{id(nested_data)}_{time.time_ns()}"
        
        with SPSCManager(name, size=1024 * 1024, create=True) as manager:
            write_success = manager.atomic_write(nested_data)
            
            if write_success:
                read_data = manager.atomic_read()
                assert read_data == nested_data
