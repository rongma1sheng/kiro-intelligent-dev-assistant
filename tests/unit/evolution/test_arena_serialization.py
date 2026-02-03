"""Arena验证结果序列化测试

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

测试Arena验证结果的序列化和反序列化功能。
"""

import pytest
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum

from src.evolution.z2h_data_models import (
    serialize_arena_result,
    deserialize_arena_result,
    arena_result_to_json,
    arena_result_from_json
)


# 模拟Arena相关的数据结构
class ValidationLayer(Enum):
    """验证层级"""
    LAYER_1_BASIC = "layer_1_basic"
    LAYER_2_STABILITY = "layer_2_stability"
    LAYER_3_OVERFITTING = "layer_3_overfitting"
    LAYER_4_STRESS = "layer_4_stress"


@dataclass
class LayerResult:
    """单层验证结果"""
    layer: ValidationLayer
    passed: bool
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    failure_reason: str = None
    rating: str = None


@dataclass
class ArenaTestResult:
    """Arena测试综合结果"""
    passed: bool
    overall_score: float
    layer_results: Dict[str, LayerResult] = field(default_factory=dict)
    layers_passed: int = 0
    layers_failed: int = 0
    total_layers: int = 4
    failed_layers: List[str] = field(default_factory=list)
    test_date: datetime = field(default_factory=datetime.now)
    strategy_name: str = None
    strategy_type: str = None


class TestArenaResultSerialization:
    """测试Arena结果序列化"""
    
    @pytest.fixture
    def sample_layer_result(self) -> LayerResult:
        """创建示例层级结果"""
        return LayerResult(
            layer=ValidationLayer.LAYER_1_BASIC,
            passed=True,
            score=0.85,
            details={
                'sharpe_ratio': 2.5,
                'max_drawdown': 0.12,
                'win_rate': 0.65
            },
            rating='QUALIFIED'
        )
    
    @pytest.fixture
    def sample_arena_result(self, sample_layer_result: LayerResult) -> ArenaTestResult:
        """创建示例Arena结果"""
        return ArenaTestResult(
            passed=True,
            overall_score=0.82,
            layer_results={
                'layer_1': sample_layer_result
            },
            layers_passed=4,
            layers_failed=0,
            total_layers=4,
            failed_layers=[],
            test_date=datetime(2024, 1, 15, 10, 30, 0),
            strategy_name='Test Strategy',
            strategy_type='momentum'
        )
    
    def test_serialize_arena_result_dict(self, sample_arena_result: ArenaTestResult):
        """测试序列化Arena结果为字典"""
        data = serialize_arena_result(sample_arena_result)
        
        # 验证基本字段
        assert isinstance(data, dict)
        assert data['passed'] is True
        assert data['overall_score'] == 0.82
        assert data['strategy_name'] == 'Test Strategy'
        
        # 验证日期序列化
        assert isinstance(data['test_date'], str)
        assert 'T' in data['test_date']
        
        # 验证嵌套对象
        assert 'layer_1' in data['layer_results']
        layer_data = data['layer_results']['layer_1']
        assert layer_data['passed'] is True
        assert layer_data['score'] == 0.85
        
        # 验证枚举序列化
        assert layer_data['layer'] == 'layer_1_basic'
    
    def test_deserialize_arena_result_dict(self, sample_arena_result: ArenaTestResult):
        """测试从字典反序列化Arena结果"""
        # 先序列化
        data = serialize_arena_result(sample_arena_result)
        
        # 再反序列化
        restored = deserialize_arena_result(data)
        
        # 验证基本字段
        assert isinstance(restored, dict)
        assert restored['passed'] is True
        assert restored['overall_score'] == 0.82
        
        # 验证日期恢复
        assert isinstance(restored['test_date'], datetime)
    
    def test_arena_result_to_json(self, sample_arena_result: ArenaTestResult):
        """测试Arena结果转换为JSON"""
        json_str = arena_result_to_json(sample_arena_result)
        
        # 验证是JSON字符串
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # 验证可以解析
        import json
        data = json.loads(json_str)
        assert isinstance(data, dict)
        assert data['passed'] is True
    
    def test_arena_result_from_json(self, sample_arena_result: ArenaTestResult):
        """测试从JSON创建Arena结果"""
        json_str = arena_result_to_json(sample_arena_result)
        restored = arena_result_from_json(json_str)
        
        # 验证基本字段
        assert isinstance(restored, dict)
        assert restored['passed'] is True
        assert restored['overall_score'] == 0.82
        assert restored['strategy_name'] == 'Test Strategy'
    
    def test_arena_result_json_round_trip(self, sample_arena_result: ArenaTestResult):
        """测试Arena结果JSON序列化往返"""
        json_str = arena_result_to_json(sample_arena_result)
        restored = arena_result_from_json(json_str)
        
        # 验证所有关键字段
        assert restored['passed'] == sample_arena_result.passed
        assert restored['overall_score'] == sample_arena_result.overall_score
        assert restored['layers_passed'] == sample_arena_result.layers_passed
        assert restored['strategy_name'] == sample_arena_result.strategy_name
        
        # 验证嵌套结构
        assert 'layer_1' in restored['layer_results']
        layer_data = restored['layer_results']['layer_1']
        assert layer_data['passed'] is True
        assert layer_data['score'] == 0.85
    
    def test_serialize_dict_directly(self):
        """测试直接序列化字典"""
        data = {
            'passed': True,
            'score': 0.85,
            'test_date': datetime(2024, 1, 15),
            'details': {
                'metric1': 1.5,
                'metric2': 2.0
            }
        }
        
        serialized = serialize_arena_result(data)
        
        # 验证日期被序列化
        assert isinstance(serialized['test_date'], str)
        
        # 验证嵌套字典保持不变
        assert serialized['details']['metric1'] == 1.5
    
    def test_serialize_invalid_type(self):
        """测试序列化无效类型"""
        invalid_data = "not a valid arena result"
        
        with pytest.raises(ValueError, match="不支持的Arena结果类型"):
            serialize_arena_result(invalid_data)
    
    def test_arena_result_from_json_invalid(self):
        """测试从无效JSON创建Arena结果"""
        invalid_json = "{ invalid json }"
        
        with pytest.raises(ValueError, match="JSON解析失败"):
            arena_result_from_json(invalid_json)
    
    def test_serialize_nested_objects(self):
        """测试序列化嵌套对象"""
        @dataclass
        class NestedObject:
            value: float
            timestamp: datetime
        
        @dataclass
        class ParentObject:
            name: str
            nested: NestedObject
        
        obj = ParentObject(
            name='test',
            nested=NestedObject(
                value=1.5,
                timestamp=datetime(2024, 1, 15)
            )
        )
        
        serialized = serialize_arena_result(obj)
        
        # 验证嵌套对象被序列化
        assert serialized['name'] == 'test'
        assert serialized['nested']['value'] == 1.5
        assert isinstance(serialized['nested']['timestamp'], str)
    
    def test_serialize_list_of_dicts(self):
        """测试序列化包含字典列表的对象"""
        data = {
            'name': 'test',
            'results': [
                {'score': 0.8, 'date': datetime(2024, 1, 1)},
                {'score': 0.9, 'date': datetime(2024, 1, 2)}
            ]
        }
        
        serialized = serialize_arena_result(data)
        
        # 验证列表中的日期被序列化
        assert isinstance(serialized['results'][0]['date'], str)
        assert isinstance(serialized['results'][1]['date'], str)
    
    def test_deserialize_preserves_structure(self):
        """测试反序列化保持结构完整"""
        data = {
            'passed': True,
            'score': 0.85,
            'layer_results': {
                'layer_1': {
                    'passed': True,
                    'score': 0.9,
                    'details': {
                        'metric1': 1.5,
                        'metric2': 2.0
                    }
                }
            },
            'test_date': '2024-01-15T10:30:00'
        }
        
        restored = deserialize_arena_result(data)
        
        # 验证结构完整
        assert restored['passed'] is True
        assert 'layer_1' in restored['layer_results']
        assert restored['layer_results']['layer_1']['details']['metric1'] == 1.5
        
        # 验证日期被恢复
        assert isinstance(restored['test_date'], datetime)
        assert restored['test_date'].year == 2024
    
    def test_serialize_with_to_dict_method(self):
        """测试序列化有to_dict方法的对象"""
        class CustomObject:
            def to_dict(self):
                return {'custom': 'data', 'value': 123}
        
        obj = CustomObject()
        serialized = serialize_arena_result(obj)
        
        assert serialized['custom'] == 'data'
        assert serialized['value'] == 123
    
    def test_serialize_arena_result_exception(self):
        """测试序列化时的异常处理"""
        # 创建一个会导致序列化失败的对象
        class BadObject:
            def __init__(self):
                self.value = object()  # 不可序列化
        
        with pytest.raises(ValueError, match="Arena结果序列化失败"):
            serialize_arena_result(BadObject())
    
    def test_deserialize_with_result_class_from_dict(self):
        """测试使用result_class和from_dict方法反序列化"""
        @dataclass
        class TestResult:
            value: float
            
            @classmethod
            def from_dict(cls, data):
                return cls(value=data['value'])
        
        data = {'value': 1.5}
        result = deserialize_arena_result(data, TestResult)
        
        assert isinstance(result, TestResult)
        assert result.value == 1.5
    
    def test_deserialize_with_result_class_constructor(self):
        """测试使用result_class构造函数反序列化"""
        @dataclass
        class TestResult:
            value: float
        
        data = {'value': 2.5}
        result = deserialize_arena_result(data, TestResult)
        
        assert isinstance(result, TestResult)
        assert result.value == 2.5
    
    def test_deserialize_arena_result_exception(self):
        """测试反序列化时的异常处理"""
        @dataclass
        class BadResult:
            required_field: str
        
        # 缺少必需字段
        data = {'wrong_field': 'value'}
        
        with pytest.raises(ValueError, match="Arena结果反序列化失败"):
            deserialize_arena_result(data, BadResult)
    
    def test_arena_result_to_json_exception(self):
        """测试JSON序列化时的异常处理"""
        # 创建一个无法序列化为JSON的对象
        class BadObject:
            pass
        
        with pytest.raises(ValueError, match="Arena结果JSON序列化失败"):
            arena_result_to_json(BadObject())
    
    def test_arena_result_from_json_exception(self):
        """测试JSON反序列化时的异常处理"""
        @dataclass
        class BadResult:
            required_field: str
        
        # JSON有效但数据无效
        json_str = '{"wrong_field": "value"}'
        
        with pytest.raises(ValueError, match="Arena结果JSON反序列化失败"):
            arena_result_from_json(json_str, BadResult)
    
    def test_restore_arena_dict_datetime_parse_error(self):
        """测试恢复字典时datetime解析错误"""
        from src.evolution.z2h_data_models import _restore_arena_dict
        
        # 包含看起来像ISO格式但实际无效的字符串
        data = {
            'date': '2024-13-45T99:99:99'  # 无效日期
        }
        
        restored = _restore_arena_dict(data)
        
        # 应该保持为字符串（解析失败）
        assert isinstance(restored['date'], str)
        assert restored['date'] == '2024-13-45T99:99:99'
    
    def test_process_arena_dict_with_object_having_dict(self):
        """测试处理有__dict__属性但不是dataclass的对象"""
        class CustomObject:
            def __init__(self):
                self.value = 123
                self.timestamp = datetime(2024, 1, 15)
        
        data = {
            'obj': CustomObject()
        }
        
        from src.evolution.z2h_data_models import _process_arena_dict
        processed = _process_arena_dict(data)
        
        # 验证嵌套对象被处理
        assert 'obj' in processed
        assert processed['obj']['value'] == 123
        assert isinstance(processed['obj']['timestamp'], str)
    
    def test_process_arena_dict_with_nested_custom_object(self):
        """测试处理嵌套的自定义对象（非dataclass）"""
        class InnerObject:
            def __init__(self):
                self.inner_value = 456
        
        class OuterObject:
            def __init__(self):
                self.outer_value = 789
                self.inner = InnerObject()
        
        data = {
            'nested': OuterObject()
        }
        
        from src.evolution.z2h_data_models import _process_arena_dict
        processed = _process_arena_dict(data)
        
        # 验证嵌套对象被递归处理
        assert 'nested' in processed
        assert processed['nested']['outer_value'] == 789
        assert processed['nested']['inner']['inner_value'] == 456
    
    def test_process_arena_dict_with_dataclass_object(self):
        """测试处理dataclass对象（覆盖line 789）"""
        @dataclass
        class DataClassObject:
            value: int
            name: str
        
        data = {
            'dc_obj': DataClassObject(value=999, name='test')
        }
        
        from src.evolution.z2h_data_models import _process_arena_dict
        processed = _process_arena_dict(data)
        
        # 验证dataclass对象被处理
        assert 'dc_obj' in processed
        assert processed['dc_obj']['value'] == 999
        assert processed['dc_obj']['name'] == 'test'
