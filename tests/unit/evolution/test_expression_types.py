"""表达式类型系统测试

白皮书依据: 第四章 4.1 类型约束系统
Phase 2 升级测试
"""

import pytest
from src.evolution.expression_types import (
    ExpressionType, TypedOperator, TypeSystem, SemanticValidator
)


class TestExpressionType:
    """测试表达式类型枚举"""
    
    def test_expression_types_exist(self):
        """测试所有表达式类型存在"""
        assert ExpressionType.PRICE
        assert ExpressionType.VOLUME
        assert ExpressionType.RETURN
        assert ExpressionType.RATIO
        assert ExpressionType.VOLATILITY
        assert ExpressionType.INDICATOR
        assert ExpressionType.BOOLEAN
        assert ExpressionType.UNKNOWN


class TestTypedOperator:
    """测试类型化算子"""
    
    def test_typed_operator_creation(self):
        """测试类型化算子创建"""
        op = TypedOperator(
            name='+',
            input_types=[ExpressionType.PRICE, ExpressionType.PRICE],
            output_type=ExpressionType.PRICE,
            commutative=True
        )
        
        assert op.name == '+'
        assert len(op.input_types) == 2
        assert op.output_type == ExpressionType.PRICE
        assert op.commutative is True
    
    def test_is_valid_inputs_matching(self):
        """测试输入类型匹配"""
        op = TypedOperator(
            name='+',
            input_types=[ExpressionType.PRICE, ExpressionType.PRICE],
            output_type=ExpressionType.PRICE
        )
        
        # 匹配的输入
        assert op.is_valid_inputs([ExpressionType.PRICE, ExpressionType.PRICE])
        
        # 不匹配的输入
        assert not op.is_valid_inputs([ExpressionType.PRICE, ExpressionType.VOLUME])
        assert not op.is_valid_inputs([ExpressionType.PRICE])  # 数量不对


class TestTypeSystem:
    """测试类型系统"""
    
    @pytest.fixture
    def type_system(self):
        """创建类型系统实例"""
        return TypeSystem()
    
    def test_type_system_initialization(self, type_system):
        """测试类型系统初始化"""
        assert type_system.column_types is not None
        assert type_system.operator_rules is not None
        
        # 验证列类型映射
        assert type_system.column_types['close'] == ExpressionType.PRICE
        assert type_system.column_types['volume'] == ExpressionType.VOLUME
    
    def test_get_column_type(self, type_system):
        """测试获取列类型"""
        assert type_system.get_column_type('close') == ExpressionType.PRICE
        assert type_system.get_column_type('open') == ExpressionType.PRICE
        assert type_system.get_column_type('volume') == ExpressionType.VOLUME
        assert type_system.get_column_type('unknown_column') == ExpressionType.UNKNOWN
    
    def test_valid_operations(self, type_system):
        """测试合法运算
        
        验证: Phase 2 - 类型约束
        """
        # price + price → price (合法)
        assert type_system.is_valid_operation(
            '+', ExpressionType.PRICE, ExpressionType.PRICE
        )
        
        # volume + volume → volume (合法)
        assert type_system.is_valid_operation(
            '+', ExpressionType.VOLUME, ExpressionType.VOLUME
        )
        
        # price × price → ratio (合法)
        assert type_system.is_valid_operation(
            '*', ExpressionType.PRICE, ExpressionType.PRICE
        )
        
        # price ÷ volatility → ratio (合法)
        assert type_system.is_valid_operation(
            '/', ExpressionType.PRICE, ExpressionType.VOLATILITY
        )
    
    def test_invalid_operations(self, type_system):
        """测试不合法运算
        
        验证: Phase 2 - 语义错误检测
        """
        # price + volume → INVALID (量纲不匹配)
        assert not type_system.is_valid_operation(
            '+', ExpressionType.PRICE, ExpressionType.VOLUME
        )
        
        # price - volume → INVALID (量纲不匹配)
        assert not type_system.is_valid_operation(
            '-', ExpressionType.PRICE, ExpressionType.VOLUME
        )
    
    def test_infer_operation_type(self, type_system):
        """测试运算类型推断"""
        # price + price → price
        result_type = type_system.infer_operation_type(
            '+', ExpressionType.PRICE, ExpressionType.PRICE
        )
        assert result_type == ExpressionType.PRICE
        
        # price × price → ratio
        result_type = type_system.infer_operation_type(
            '*', ExpressionType.PRICE, ExpressionType.PRICE
        )
        assert result_type == ExpressionType.RATIO
        
        # price + volume → None (不合法)
        result_type = type_system.infer_operation_type(
            '+', ExpressionType.PRICE, ExpressionType.VOLUME
        )
        assert result_type is None
    
    def test_get_invalid_reason(self, type_system):
        """测试获取不合法原因"""
        # price + volume
        reason = type_system.get_invalid_reason(
            '+', ExpressionType.PRICE, ExpressionType.VOLUME
        )
        assert '量纲不匹配' in reason or '语义错误' in reason
        
        # 合法运算应该返回空字符串
        reason = type_system.get_invalid_reason(
            '+', ExpressionType.PRICE, ExpressionType.PRICE
        )
        assert reason == ""


class TestSemanticValidator:
    """测试语义验证器"""
    
    @pytest.fixture
    def validator(self):
        """创建语义验证器实例"""
        type_system = TypeSystem()
        return SemanticValidator(type_system)
    
    def test_semantic_validator_initialization(self, validator):
        """测试语义验证器初始化"""
        assert validator.type_system is not None
        assert validator.semantic_rules is not None
        assert len(validator.semantic_rules) > 0
    
    def test_validate_valid_expression(self, validator):
        """测试验证合法表达式"""
        # price + price (合法)
        is_valid, errors = validator.validate_expression(
            '+', ExpressionType.PRICE, ExpressionType.PRICE
        )
        assert is_valid
        assert len(errors) == 0
        
        # price × price (合法)
        is_valid, errors = validator.validate_expression(
            '*', ExpressionType.PRICE, ExpressionType.PRICE
        )
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_invalid_expression(self, validator):
        """测试验证不合法表达式
        
        验证: Phase 2 - 语义错误检测
        """
        # price + volume (不合法)
        is_valid, errors = validator.validate_expression(
            '+', ExpressionType.PRICE, ExpressionType.VOLUME
        )
        assert not is_valid
        assert len(errors) > 0
        
        # volume / price (无意义的除法)
        is_valid, errors = validator.validate_expression(
            '/', ExpressionType.VOLUME, ExpressionType.PRICE
        )
        assert not is_valid
        assert len(errors) > 0
    
    def test_suggest_fix(self, validator):
        """测试修复建议"""
        # price + volume → 建议改为除法
        suggestion = validator.suggest_fix(
            '+', ExpressionType.PRICE, ExpressionType.VOLUME
        )
        assert suggestion is not None
        assert '/' in suggestion or '除' in suggestion
        
        # volume / price → 建议交换操作数
        suggestion = validator.suggest_fix(
            '/', ExpressionType.VOLUME, ExpressionType.PRICE
        )
        assert suggestion is not None
        assert '交换' in suggestion or 'price / volume' in suggestion
    
    def test_semantic_rules(self, validator):
        """测试语义规则"""
        # 验证规则数量
        assert len(validator.semantic_rules) >= 3
        
        # 验证规则结构
        for rule in validator.semantic_rules:
            assert 'name' in rule
            assert 'description' in rule
            assert 'check' in rule
            assert callable(rule['check'])


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
