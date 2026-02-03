"""基因胶囊序列化属性测试

白皮书依据: 第四章 4.3.1 Z2H认证系统

Property 7: Gene Capsule Serialization Round-Trip
验证需求: Requirements 3.8, 16.4

使用hypothesis进行属性测试，验证基因胶囊序列化后反序列化产生等价对象。
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
import json

from src.evolution.z2h_data_models import (
    Z2HGeneCapsule,
    CertificationLevel,
    CertificationStatus,
    CapitalTier
)


# ==================== Hypothesis策略定义 ====================

@st.composite
def gene_capsule_strategy(draw):
    """生成随机基因胶囊对象的策略
    
    生成符合业务规则的随机Z2HGeneCapsule对象用于测试。
    """
    # 生成基础字段
    strategy_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'))))
    strategy_name = draw(st.text(min_size=1, max_size=100))
    strategy_code = draw(st.text(min_size=10, max_size=500))
    
    # 生成枚举字段
    certification_level = draw(st.sampled_from(list(CertificationLevel)))
    certification_status = draw(st.sampled_from(list(CertificationStatus)))
    optimal_capital_tier = draw(st.sampled_from(list(CapitalTier)))
    
    # 生成数值字段
    overall_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    arena_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    simulation_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    # 生成日期字段
    base_date = datetime(2024, 1, 1)
    certification_date = base_date + timedelta(days=draw(st.integers(min_value=0, max_value=365)))
    expiry_date = certification_date + timedelta(days=draw(st.integers(min_value=30, max_value=365)))
    
    # 生成字典字段
    arena_results = {
        'layer_1_score': draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        'layer_2_score': draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        'layer_3_score': draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        'layer_4_score': draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    }
    
    simulation_results = {
        'tier_1_return': draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)),
        'tier_2_return': draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)),
        'tier_3_return': draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)),
        'tier_4_return': draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False))
    }
    
    capital_allocation_rules = {
        'base_allocation_ratio': draw(st.floats(min_value=0.05, max_value=0.25, allow_nan=False, allow_infinity=False)),
        'max_position_size': draw(st.floats(min_value=0.01, max_value=0.10, allow_nan=False, allow_infinity=False)),
        'risk_limit': draw(st.floats(min_value=0.01, max_value=0.20, allow_nan=False, allow_infinity=False))
    }
    
    metadata = {
        'version': draw(st.text(min_size=1, max_size=20)),
        'created_by': draw(st.text(min_size=1, max_size=50)),
        'tags': draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5))
    }
    
    # 创建基因胶囊对象
    return Z2HGeneCapsule(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        strategy_code=strategy_code,
        certification_level=certification_level,
        certification_status=certification_status,
        certification_date=certification_date,
        expiry_date=expiry_date,
        overall_score=overall_score,
        arena_score=arena_score,
        simulation_score=simulation_score,
        arena_results=arena_results,
        simulation_results=simulation_results,
        optimal_capital_tier=optimal_capital_tier,
        capital_allocation_rules=capital_allocation_rules,
        metadata=metadata
    )


# ==================== 属性测试 ====================

class TestGeneCapsuleSerializationProperty:
    """基因胶囊序列化属性测试
    
    白皮书依据: 第四章 4.3.1 - Z2H基因胶囊序列化
    验证需求: Requirements 3.8, 16.4
    """
    
    @given(capsule=gene_capsule_strategy())
    @settings(max_examples=100, deadline=None)
    def test_serialization_round_trip(self, capsule: Z2HGeneCapsule):
        """Property 7: 基因胶囊序列化往返测试
        
        验证需求: Requirements 3.8, 16.4
        
        属性: 对于任意有效的基因胶囊对象，序列化后反序列化应该产生等价的对象。
        
        测试步骤:
        1. 生成随机基因胶囊对象
        2. 序列化为字典
        3. 从字典反序列化
        4. 验证反序列化后的对象与原对象等价
        """
        # 序列化
        serialized = capsule.to_dict()
        
        # 验证序列化结果是字典
        assert isinstance(serialized, dict), "序列化结果必须是字典"
        
        # 验证必要字段存在
        required_fields = [
            'strategy_id', 'strategy_name', 'strategy_code',
            'certification_level', 'certification_status',
            'certification_date', 'expiry_date',
            'overall_score', 'arena_score', 'simulation_score',
            'arena_results', 'simulation_results',
            'optimal_capital_tier', 'capital_allocation_rules',
            'metadata'
        ]
        
        for field in required_fields:
            assert field in serialized, f"序列化结果缺少必要字段: {field}"
        
        # 反序列化
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        
        # 验证反序列化结果类型
        assert isinstance(deserialized, Z2HGeneCapsule), "反序列化结果必须是Z2HGeneCapsule对象"
        
        # 验证字段等价性
        assert deserialized.strategy_id == capsule.strategy_id
        assert deserialized.strategy_name == capsule.strategy_name
        assert deserialized.strategy_code == capsule.strategy_code
        assert deserialized.certification_level == capsule.certification_level
        assert deserialized.certification_status == capsule.certification_status
        assert deserialized.optimal_capital_tier == capsule.optimal_capital_tier
        
        # 验证数值字段（允许浮点误差）
        assert abs(deserialized.overall_score - capsule.overall_score) < 1e-6
        assert abs(deserialized.arena_score - capsule.arena_score) < 1e-6
        assert abs(deserialized.simulation_score - capsule.simulation_score) < 1e-6
        
        # 验证日期字段（转换为字符串比较，避免时区问题）
        assert deserialized.certification_date.date() == capsule.certification_date.date()
        assert deserialized.expiry_date.date() == capsule.expiry_date.date()
        
        # 验证字典字段
        assert deserialized.arena_results == capsule.arena_results
        assert deserialized.simulation_results == capsule.simulation_results
        assert deserialized.capital_allocation_rules == capsule.capital_allocation_rules
        assert deserialized.metadata == capsule.metadata
    
    @given(capsule=gene_capsule_strategy())
    @settings(max_examples=100, deadline=None)
    def test_json_serialization_round_trip(self, capsule: Z2HGeneCapsule):
        """Property 7.1: JSON序列化往返测试
        
        验证需求: Requirements 16.1, 16.2
        
        属性: 基因胶囊对象应该能够序列化为JSON字符串并正确反序列化。
        """
        # 序列化为字典
        dict_data = capsule.to_dict()
        
        # 转换为JSON字符串
        json_str = json.dumps(dict_data, ensure_ascii=False, default=str)
        
        # 验证JSON字符串有效
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # 从JSON字符串解析
        parsed_dict = json.loads(json_str)
        
        # 反序列化
        deserialized = Z2HGeneCapsule.from_dict(parsed_dict)
        
        # 验证核心字段
        assert deserialized.strategy_id == capsule.strategy_id
        assert deserialized.certification_level == capsule.certification_level
        assert deserialized.optimal_capital_tier == capsule.optimal_capital_tier
    
    @given(capsule=gene_capsule_strategy())
    @settings(max_examples=100, deadline=None)
    def test_serialization_preserves_types(self, capsule: Z2HGeneCapsule):
        """Property 7.2: 序列化保持类型信息
        
        验证需求: Requirements 16.3
        
        属性: 序列化后的数据应该保持正确的类型信息。
        """
        serialized = capsule.to_dict()
        
        # 验证枚举类型被正确序列化为字符串
        assert isinstance(serialized['certification_level'], str)
        assert isinstance(serialized['certification_status'], str)
        assert isinstance(serialized['optimal_capital_tier'], str)
        
        # 验证日期类型被正确序列化为字符串
        assert isinstance(serialized['certification_date'], str)
        assert isinstance(serialized['expiry_date'], str)
        
        # 验证数值类型
        assert isinstance(serialized['overall_score'], (int, float))
        assert isinstance(serialized['arena_score'], (int, float))
        assert isinstance(serialized['simulation_score'], (int, float))
        
        # 验证字典类型
        assert isinstance(serialized['arena_results'], dict)
        assert isinstance(serialized['simulation_results'], dict)
        assert isinstance(serialized['capital_allocation_rules'], dict)
        assert isinstance(serialized['metadata'], dict)
    
    @given(capsule=gene_capsule_strategy())
    @settings(max_examples=100, deadline=None)
    def test_serialization_idempotence(self, capsule: Z2HGeneCapsule):
        """Property 7.3: 序列化幂等性
        
        验证需求: Requirements 16.4
        
        属性: 多次序列化应该产生相同的结果。
        """
        # 第一次序列化
        serialized1 = capsule.to_dict()
        
        # 第二次序列化
        serialized2 = capsule.to_dict()
        
        # 验证两次序列化结果相同
        assert serialized1 == serialized2
        
        # 反序列化后再序列化
        deserialized = Z2HGeneCapsule.from_dict(serialized1)
        serialized3 = deserialized.to_dict()
        
        # 验证反序列化后再序列化的结果与原始序列化结果相同
        assert serialized3 == serialized1


# ==================== 边界条件测试 ====================

class TestGeneCapsuleSerializationEdgeCases:
    """基因胶囊序列化边界条件测试
    
    白皮书依据: 第四章 4.3.1 - Z2H基因胶囊序列化
    验证需求: Requirements 16.5, 16.6
    """
    
    def test_empty_metadata(self):
        """测试空元数据处理"""
        capsule = Z2HGeneCapsule(
            strategy_id="test_001",
            strategy_name="Test Strategy",
            strategy_code="# code",
            certification_level=CertificationLevel.SILVER,
            certification_status=CertificationStatus.ACTIVE,
            certification_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            overall_score=0.8,
            arena_score=0.75,
            simulation_score=0.85,
            arena_results={},
            simulation_results={},
            optimal_capital_tier=CapitalTier.TIER_2,
            capital_allocation_rules={},
            metadata={}
        )
        
        # 序列化和反序列化
        serialized = capsule.to_dict()
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        
        # 验证空字典被正确处理
        assert deserialized.metadata == {}
        assert deserialized.arena_results == {}
        assert deserialized.simulation_results == {}
        assert deserialized.capital_allocation_rules == {}
    
    def test_special_characters_in_strings(self):
        """测试字符串中的特殊字符处理"""
        special_chars = "测试\n换行\t制表符\"引号'单引号\\反斜杠"
        
        capsule = Z2HGeneCapsule(
            strategy_id="test_002",
            strategy_name=special_chars,
            strategy_code=f"# {special_chars}",
            certification_level=CertificationLevel.GOLD,
            certification_status=CertificationStatus.ACTIVE,
            certification_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            overall_score=0.9,
            arena_score=0.85,
            simulation_score=0.95,
            arena_results={'note': special_chars},
            simulation_results={},
            optimal_capital_tier=CapitalTier.TIER_3,
            capital_allocation_rules={},
            metadata={'description': special_chars}
        )
        
        # 序列化和反序列化
        serialized = capsule.to_dict()
        json_str = json.dumps(serialized, ensure_ascii=False, default=str)
        parsed = json.loads(json_str)
        deserialized = Z2HGeneCapsule.from_dict(parsed)
        
        # 验证特殊字符被正确保留
        assert deserialized.strategy_name == special_chars
        assert deserialized.metadata['description'] == special_chars
    
    def test_extreme_numeric_values(self):
        """测试极端数值处理"""
        capsule = Z2HGeneCapsule(
            strategy_id="test_003",
            strategy_name="Extreme Values Test",
            strategy_code="# code",
            certification_level=CertificationLevel.PLATINUM,
            certification_status=CertificationStatus.ACTIVE,
            certification_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            overall_score=0.0,  # 最小值
            arena_score=1.0,    # 最大值
            simulation_score=0.5,
            arena_results={
                'min_value': 0.0,
                'max_value': 1.0,
                'tiny_value': 1e-10,
                'large_value': 1e10
            },
            simulation_results={},
            optimal_capital_tier=CapitalTier.TIER_4,
            capital_allocation_rules={},
            metadata={}
        )
        
        # 序列化和反序列化
        serialized = capsule.to_dict()
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        
        # 验证极端数值被正确处理
        assert deserialized.overall_score == 0.0
        assert deserialized.arena_score == 1.0
        assert abs(deserialized.arena_results['tiny_value'] - 1e-10) < 1e-15
        assert abs(deserialized.arena_results['large_value'] - 1e10) < 1e5
    
    def test_large_data_volume(self):
        """测试大数据量处理"""
        # 创建包含大量数据的基因胶囊
        large_arena_results = {f'metric_{i}': float(i) for i in range(1000)}
        large_simulation_results = {f'day_{i}': float(i) * 0.01 for i in range(1000)}
        large_metadata = {f'key_{i}': f'value_{i}' * 10 for i in range(100)}
        
        capsule = Z2HGeneCapsule(
            strategy_id="test_004",
            strategy_name="Large Data Test",
            strategy_code="# code" * 100,  # 大量代码
            certification_level=CertificationLevel.GOLD,
            certification_status=CertificationStatus.ACTIVE,
            certification_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365),
            overall_score=0.85,
            arena_score=0.80,
            simulation_score=0.90,
            arena_results=large_arena_results,
            simulation_results=large_simulation_results,
            optimal_capital_tier=CapitalTier.TIER_2,
            capital_allocation_rules={},
            metadata=large_metadata
        )
        
        # 序列化和反序列化
        serialized = capsule.to_dict()
        json_str = json.dumps(serialized, ensure_ascii=False, default=str)
        
        # 验证JSON字符串大小合理（不超过10MB）
        assert len(json_str) < 10 * 1024 * 1024
        
        parsed = json.loads(json_str)
        deserialized = Z2HGeneCapsule.from_dict(parsed)
        
        # 验证大数据量被正确处理
        assert len(deserialized.arena_results) == 1000
        assert len(deserialized.simulation_results) == 1000
        assert len(deserialized.metadata) == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
