"""风险因子数据模型单元测试

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统

测试覆盖:
- RiskFactor创建与验证
- RiskFactor序列化与反序列化
- RiskEvent创建与验证
- RiskEvent序列化与反序列化
"""

import pytest
from datetime import datetime, timedelta
from src.evolution.risk_mining.risk_factor import (
    RiskFactor,
    RiskEvent,
    RiskEventType
)


class TestRiskFactor:
    """RiskFactor数据模型测试"""
    
    def test_create_valid_risk_factor(self):
        """测试创建有效的风险因子"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={'signals': [('capital_retreat', 0.8)]}
        )
        
        assert factor.factor_type == 'flow'
        assert factor.symbol == '000001.SZ'
        assert factor.risk_value == 0.75
        assert factor.confidence == 0.85
        assert isinstance(factor.timestamp, datetime)
        assert 'signals' in factor.metadata
    
    def test_risk_value_validation_lower_bound(self):
        """测试risk_value下界验证"""
        with pytest.raises(ValueError, match="risk_value must be in"):
            RiskFactor(
                factor_type='flow',
                symbol='000001.SZ',
                risk_value=-0.1,  # 无效：< 0
                confidence=0.85,
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_risk_value_validation_upper_bound(self):
        """测试risk_value上界验证"""
        with pytest.raises(ValueError, match="risk_value must be in"):
            RiskFactor(
                factor_type='flow',
                symbol='000001.SZ',
                risk_value=1.1,  # 无效：> 1
                confidence=0.85,
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_risk_value_boundary_values(self):
        """测试risk_value边界值"""
        # 测试下界
        factor_min = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.0,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor_min.risk_value == 0.0
        
        # 测试上界
        factor_max = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=1.0,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor_max.risk_value == 1.0
    
    def test_confidence_validation_lower_bound(self):
        """测试confidence下界验证"""
        with pytest.raises(ValueError, match="confidence must be in"):
            RiskFactor(
                factor_type='flow',
                symbol='000001.SZ',
                risk_value=0.75,
                confidence=-0.1,  # 无效：< 0
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_confidence_validation_upper_bound(self):
        """测试confidence上界验证"""
        with pytest.raises(ValueError, match="confidence must be in"):
            RiskFactor(
                factor_type='flow',
                symbol='000001.SZ',
                risk_value=0.75,
                confidence=1.1,  # 无效：> 1
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_confidence_boundary_values(self):
        """测试confidence边界值"""
        # 测试下界
        factor_min = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.0,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor_min.confidence == 0.0
        
        # 测试上界
        factor_max = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=1.0,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor_max.confidence == 1.0
    
    def test_factor_type_validation_flow(self):
        """测试factor_type验证 - flow"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor.factor_type == 'flow'
    
    def test_factor_type_validation_microstructure(self):
        """测试factor_type验证 - microstructure"""
        factor = RiskFactor(
            factor_type='microstructure',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor.factor_type == 'microstructure'
    
    def test_factor_type_validation_portfolio(self):
        """测试factor_type验证 - portfolio"""
        factor = RiskFactor(
            factor_type='portfolio',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        assert factor.factor_type == 'portfolio'
    
    def test_factor_type_validation_invalid(self):
        """测试factor_type验证 - 无效类型"""
        with pytest.raises(ValueError, match="factor_type must be one of"):
            RiskFactor(
                factor_type='invalid_type',
                symbol='000001.SZ',
                risk_value=0.75,
                confidence=0.85,
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_symbol_validation_empty(self):
        """测试symbol验证 - 空字符串"""
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            RiskFactor(
                factor_type='flow',
                symbol='',
                risk_value=0.75,
                confidence=0.85,
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_symbol_validation_non_string(self):
        """测试symbol验证 - 非字符串"""
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            RiskFactor(
                factor_type='flow',
                symbol=None,
                risk_value=0.75,
                confidence=0.85,
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_timestamp_validation_invalid_type(self):
        """测试timestamp验证 - 无效类型"""
        with pytest.raises(ValueError, match="timestamp must be a datetime object"):
            RiskFactor(
                factor_type='flow',
                symbol='000001.SZ',
                risk_value=0.75,
                confidence=0.85,
                timestamp="2026-01-23",  # 字符串而非datetime
                metadata={}
            )
    
    def test_metadata_validation_invalid_type(self):
        """测试metadata验证 - 无效类型"""
        with pytest.raises(ValueError, match="metadata must be a dict"):
            RiskFactor(
                factor_type='flow',
                symbol='000001.SZ',
                risk_value=0.75,
                confidence=0.85,
                timestamp=datetime.now(),
                metadata="invalid"  # 字符串而非dict
            )
    
    def test_to_dict(self):
        """测试to_dict序列化"""
        timestamp = datetime(2026, 1, 23, 10, 30, 0)
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={'signals': [('capital_retreat', 0.8)]}
        )
        
        result = factor.to_dict()
        
        assert result['factor_type'] == 'flow'
        assert result['symbol'] == '000001.SZ'
        assert result['risk_value'] == 0.75
        assert result['confidence'] == 0.85
        assert result['timestamp'] == timestamp.isoformat()
        assert result['metadata'] == {'signals': [('capital_retreat', 0.8)]}
    
    def test_from_dict_valid(self):
        """测试from_dict反序列化 - 有效数据"""
        data = {
            'factor_type': 'flow',
            'symbol': '000001.SZ',
            'risk_value': 0.75,
            'confidence': 0.85,
            'timestamp': '2026-01-23T10:30:00',
            'metadata': {'signals': [('capital_retreat', 0.8)]}
        }
        
        factor = RiskFactor.from_dict(data)
        
        assert factor.factor_type == 'flow'
        assert factor.symbol == '000001.SZ'
        assert factor.risk_value == 0.75
        assert factor.confidence == 0.85
        assert factor.timestamp == datetime(2026, 1, 23, 10, 30, 0)
        assert factor.metadata == {'signals': [('capital_retreat', 0.8)]}
    
    def test_from_dict_with_datetime_object(self):
        """测试from_dict反序列化 - datetime对象"""
        timestamp = datetime(2026, 1, 23, 10, 30, 0)
        data = {
            'factor_type': 'flow',
            'symbol': '000001.SZ',
            'risk_value': 0.75,
            'confidence': 0.85,
            'timestamp': timestamp,
            'metadata': {}
        }
        
        factor = RiskFactor.from_dict(data)
        
        assert factor.timestamp == timestamp
    
    def test_from_dict_missing_field(self):
        """测试from_dict反序列化 - 缺少字段"""
        data = {
            'factor_type': 'flow',
            'symbol': '000001.SZ',
            # 缺少 risk_value
            'confidence': 0.85,
            'timestamp': '2026-01-23T10:30:00',
            'metadata': {}
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            RiskFactor.from_dict(data)
    
    def test_from_dict_invalid_data(self):
        """测试from_dict反序列化 - 无效数据"""
        data = {
            'factor_type': 'invalid_type',
            'symbol': '000001.SZ',
            'risk_value': 0.75,
            'confidence': 0.85,
            'timestamp': '2026-01-23T10:30:00',
            'metadata': {}
        }
        
        with pytest.raises(ValueError):
            RiskFactor.from_dict(data)
    
    def test_serialization_roundtrip(self):
        """测试序列化往返一致性"""
        original = RiskFactor(
            factor_type='microstructure',
            symbol='600000.SH',
            risk_value=0.65,
            confidence=0.90,
            timestamp=datetime(2026, 1, 23, 10, 30, 0),
            metadata={'orderbook_imbalance': 3.5}
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = RiskFactor.from_dict(data)
        
        # 验证一致性
        assert restored.factor_type == original.factor_type
        assert restored.symbol == original.symbol
        assert restored.risk_value == original.risk_value
        assert restored.confidence == original.confidence
        assert restored.timestamp == original.timestamp
        assert restored.metadata == original.metadata
    
    def test_repr(self):
        """测试__repr__字符串表示"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        repr_str = repr(factor)
        
        assert 'RiskFactor' in repr_str
        assert 'flow' in repr_str
        assert '000001.SZ' in repr_str
        assert '0.750' in repr_str
        assert '0.850' in repr_str
    
    def test_equality_same_values(self):
        """测试相等性 - 相同值"""
        timestamp = datetime(2026, 1, 23, 10, 30, 0)
        
        factor1 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        factor2 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        assert factor1 == factor2
    
    def test_equality_different_values(self):
        """测试相等性 - 不同值"""
        timestamp = datetime(2026, 1, 23, 10, 30, 0)
        
        factor1 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        factor2 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.80,  # 不同的risk_value
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        assert factor1 != factor2
    
    def test_equality_different_type(self):
        """测试相等性 - 不同类型"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        assert factor != "not a RiskFactor"
        assert factor != 123
        assert factor != None
    
    def test_hash_consistency(self):
        """测试哈希一致性"""
        timestamp = datetime(2026, 1, 23, 10, 30, 0)
        
        factor1 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        factor2 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        # 相等的对象应该有相同的哈希值
        assert hash(factor1) == hash(factor2)
    
    def test_hash_in_set(self):
        """测试哈希在集合中的使用"""
        timestamp = datetime(2026, 1, 23, 10, 30, 0)
        
        factor1 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        factor2 = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=timestamp,
            metadata={}
        )
        
        # 相等的对象在集合中应该被视为同一个
        factor_set = {factor1, factor2}
        assert len(factor_set) == 1


class TestRiskEvent:
    """RiskEvent数据模型测试"""
    
    def test_create_valid_risk_event(self):
        """测试创建有效的风险事件"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        event = RiskEvent(
            event_type=RiskEventType.RISK_FACTOR_GENERATED,
            symbol='000001.SZ',
            factor=factor,
            timestamp=datetime.now()
        )
        
        assert event.event_type == RiskEventType.RISK_FACTOR_GENERATED
        assert event.symbol == '000001.SZ'
        assert event.factor == factor
        assert isinstance(event.timestamp, datetime)
    
    def test_event_type_validation_invalid(self):
        """测试event_type验证 - 无效类型"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        with pytest.raises(ValueError, match="event_type must be a RiskEventType"):
            RiskEvent(
                event_type="invalid_type",  # 字符串而非枚举
                symbol='000001.SZ',
                factor=factor,
                timestamp=datetime.now()
            )
    
    def test_symbol_validation_empty(self):
        """测试symbol验证 - 空字符串"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            RiskEvent(
                event_type=RiskEventType.RISK_FACTOR_GENERATED,
                symbol='',
                factor=factor,
                timestamp=datetime.now()
            )
    
    def test_factor_validation_invalid_type(self):
        """测试factor验证 - 无效类型"""
        with pytest.raises(ValueError, match="factor must be a RiskFactor"):
            RiskEvent(
                event_type=RiskEventType.RISK_FACTOR_GENERATED,
                symbol='000001.SZ',
                factor="not a RiskFactor",
                timestamp=datetime.now()
            )
    
    def test_timestamp_validation_invalid_type(self):
        """测试timestamp验证 - 无效类型"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        with pytest.raises(ValueError, match="timestamp must be a datetime object"):
            RiskEvent(
                event_type=RiskEventType.RISK_FACTOR_GENERATED,
                symbol='000001.SZ',
                factor=factor,
                timestamp="2026-01-23"
            )
    
    def test_symbol_consistency_validation(self):
        """测试symbol一致性验证"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        with pytest.raises(ValueError, match="Event symbol .* does not match factor symbol"):
            RiskEvent(
                event_type=RiskEventType.RISK_FACTOR_GENERATED,
                symbol='600000.SH',  # 不同的symbol
                factor=factor,
                timestamp=datetime.now()
            )
    
    def test_to_dict(self):
        """测试to_dict序列化"""
        factor_timestamp = datetime(2026, 1, 23, 10, 30, 0)
        event_timestamp = datetime(2026, 1, 23, 10, 30, 1)
        
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=factor_timestamp,
            metadata={}
        )
        
        event = RiskEvent(
            event_type=RiskEventType.RISK_FACTOR_GENERATED,
            symbol='000001.SZ',
            factor=factor,
            timestamp=event_timestamp
        )
        
        result = event.to_dict()
        
        assert result['event_type'] == 'risk_factor_generated'
        assert result['symbol'] == '000001.SZ'
        assert result['timestamp'] == event_timestamp.isoformat()
        assert 'factor' in result
        assert result['factor']['factor_type'] == 'flow'
    
    def test_from_dict_valid(self):
        """测试from_dict反序列化 - 有效数据"""
        data = {
            'event_type': 'risk_factor_generated',
            'symbol': '000001.SZ',
            'factor': {
                'factor_type': 'flow',
                'symbol': '000001.SZ',
                'risk_value': 0.75,
                'confidence': 0.85,
                'timestamp': '2026-01-23T10:30:00',
                'metadata': {}
            },
            'timestamp': '2026-01-23T10:30:01'
        }
        
        event = RiskEvent.from_dict(data)
        
        assert event.event_type == RiskEventType.RISK_FACTOR_GENERATED
        assert event.symbol == '000001.SZ'
        assert event.factor.factor_type == 'flow'
        assert event.timestamp == datetime(2026, 1, 23, 10, 30, 1)
    
    def test_from_dict_with_datetime_object(self):
        """测试from_dict反序列化 - datetime对象"""
        timestamp = datetime(2026, 1, 23, 10, 30, 1)
        data = {
            'event_type': 'risk_factor_generated',
            'symbol': '000001.SZ',
            'factor': {
                'factor_type': 'flow',
                'symbol': '000001.SZ',
                'risk_value': 0.75,
                'confidence': 0.85,
                'timestamp': datetime(2026, 1, 23, 10, 30, 0),
                'metadata': {}
            },
            'timestamp': timestamp
        }
        
        event = RiskEvent.from_dict(data)
        
        assert event.timestamp == timestamp
    
    def test_from_dict_missing_field(self):
        """测试from_dict反序列化 - 缺少字段"""
        data = {
            'event_type': 'risk_factor_generated',
            # 缺少 symbol
            'factor': {
                'factor_type': 'flow',
                'symbol': '000001.SZ',
                'risk_value': 0.75,
                'confidence': 0.85,
                'timestamp': '2026-01-23T10:30:00',
                'metadata': {}
            },
            'timestamp': '2026-01-23T10:30:01'
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            RiskEvent.from_dict(data)
    
    def test_serialization_roundtrip(self):
        """测试序列化往返一致性"""
        factor = RiskFactor(
            factor_type='microstructure',
            symbol='600000.SH',
            risk_value=0.65,
            confidence=0.90,
            timestamp=datetime(2026, 1, 23, 10, 30, 0),
            metadata={}
        )
        
        original = RiskEvent(
            event_type=RiskEventType.RISK_FACTOR_GENERATED,
            symbol='600000.SH',
            factor=factor,
            timestamp=datetime(2026, 1, 23, 10, 30, 1)
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = RiskEvent.from_dict(data)
        
        # 验证一致性
        assert restored.event_type == original.event_type
        assert restored.symbol == original.symbol
        assert restored.factor == original.factor
        assert restored.timestamp == original.timestamp
    
    def test_repr(self):
        """测试__repr__字符串表示"""
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001.SZ',
            risk_value=0.75,
            confidence=0.85,
            timestamp=datetime.now(),
            metadata={}
        )
        
        event = RiskEvent(
            event_type=RiskEventType.RISK_FACTOR_GENERATED,
            symbol='000001.SZ',
            factor=factor,
            timestamp=datetime.now()
        )
        
        repr_str = repr(event)
        
        assert 'RiskEvent' in repr_str
        assert 'risk_factor_generated' in repr_str
        assert '000001.SZ' in repr_str


class TestRiskEventType:
    """RiskEventType枚举测试"""
    
    def test_enum_values(self):
        """测试枚举值"""
        assert RiskEventType.RISK_FACTOR_GENERATED.value == 'risk_factor_generated'
    
    def test_enum_membership(self):
        """测试枚举成员"""
        assert 'RISK_FACTOR_GENERATED' in RiskEventType.__members__
    
    def test_enum_from_value(self):
        """测试从值创建枚举"""
        event_type = RiskEventType('risk_factor_generated')
        assert event_type == RiskEventType.RISK_FACTOR_GENERATED
