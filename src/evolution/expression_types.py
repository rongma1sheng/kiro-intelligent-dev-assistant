"""因子表达式类型系统

白皮书依据: 第四章 4.1 遗传算法 - 类型约束系统
工程目标: Phase 2 升级 - 防止语义错误的表达式
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from loguru import logger


class ExpressionType(Enum):
    """表达式类型

    白皮书依据: 第四章 4.1 类型系统
    """

    PRICE = "price"  # 价格类型 (close, open, high, low)
    VOLUME = "volume"  # 成交量类型
    RETURN = "return"  # 收益率类型
    RATIO = "ratio"  # 比率类型 (无量纲)
    VOLATILITY = "volatility"  # 波动率类型
    INDICATOR = "indicator"  # 技术指标类型
    BOOLEAN = "boolean"  # 布尔类型
    UNKNOWN = "unknown"  # 未知类型


@dataclass
class TypedOperator:
    """类型化算子

    Attributes:
        name: 算子名称
        input_types: 输入类型列表
        output_type: 输出类型
        commutative: 是否可交换
    """

    name: str
    input_types: List[ExpressionType]
    output_type: ExpressionType
    commutative: bool = False

    def is_valid_inputs(self, actual_types: List[ExpressionType]) -> bool:
        """检查输入类型是否有效

        Args:
            actual_types: 实际输入类型

        Returns:
            bool: 是否有效
        """
        if len(actual_types) != len(self.input_types):
            return False

        for actual, expected in zip(actual_types, self.input_types):
            if actual != expected and actual != ExpressionType.UNKNOWN:  # pylint: disable=r1714
                return False

        return True


class TypeSystem:
    """类型系统

    白皮书依据: 第四章 4.1 类型约束系统
    Phase 2 升级: 防止语义错误

    核心规则:
    - price × price → price²  (允许)
    - price ÷ volatility → ratio (允许)
    - price + volume → INVALID (禁止，量纲不匹配)
    - volume + volume → volume (允许)
    """

    def __init__(self):
        """初始化类型系统"""
        # 列类型映射
        self.column_types: Dict[str, ExpressionType] = {
            "close": ExpressionType.PRICE,
            "open": ExpressionType.PRICE,
            "high": ExpressionType.PRICE,
            "low": ExpressionType.PRICE,
            "volume": ExpressionType.VOLUME,
            "amount": ExpressionType.VOLUME,  # 成交额也视为volume类型
        }

        # 算子类型规则
        self.operator_rules = self._initialize_operator_rules()

        logger.info("类型系统初始化完成")

    def _initialize_operator_rules(self) -> Dict[str, List[TypedOperator]]:
        """初始化算子类型规则

        Returns:
            Dict: 算子名称到类型规则列表的映射
        """
        rules = {}

        # 加法规则：相同类型才能相加
        rules["+"] = [
            TypedOperator("+", [ExpressionType.PRICE, ExpressionType.PRICE], ExpressionType.PRICE, commutative=True),
            TypedOperator("+", [ExpressionType.VOLUME, ExpressionType.VOLUME], ExpressionType.VOLUME, commutative=True),
            TypedOperator("+", [ExpressionType.RETURN, ExpressionType.RETURN], ExpressionType.RETURN, commutative=True),
            TypedOperator("+", [ExpressionType.RATIO, ExpressionType.RATIO], ExpressionType.RATIO, commutative=True),
        ]

        # 减法规则：相同类型才能相减
        rules["-"] = [
            TypedOperator("-", [ExpressionType.PRICE, ExpressionType.PRICE], ExpressionType.PRICE),
            TypedOperator("-", [ExpressionType.VOLUME, ExpressionType.VOLUME], ExpressionType.VOLUME),
            TypedOperator("-", [ExpressionType.RETURN, ExpressionType.RETURN], ExpressionType.RETURN),
            TypedOperator("-", [ExpressionType.RATIO, ExpressionType.RATIO], ExpressionType.RATIO),
        ]

        # 乘法规则：更灵活
        rules["*"] = [
            TypedOperator(
                "*", [ExpressionType.PRICE, ExpressionType.PRICE], ExpressionType.RATIO, commutative=True
            ),  # price² → ratio
            TypedOperator("*", [ExpressionType.PRICE, ExpressionType.RATIO], ExpressionType.PRICE, commutative=True),
            TypedOperator("*", [ExpressionType.VOLUME, ExpressionType.RATIO], ExpressionType.VOLUME, commutative=True),
            TypedOperator("*", [ExpressionType.RATIO, ExpressionType.RATIO], ExpressionType.RATIO, commutative=True),
        ]

        # 除法规则：产生比率
        rules["/"] = [
            TypedOperator("/", [ExpressionType.PRICE, ExpressionType.PRICE], ExpressionType.RATIO),
            TypedOperator("/", [ExpressionType.VOLUME, ExpressionType.VOLUME], ExpressionType.RATIO),
            TypedOperator("/", [ExpressionType.PRICE, ExpressionType.VOLATILITY], ExpressionType.RATIO),
            TypedOperator("/", [ExpressionType.RATIO, ExpressionType.RATIO], ExpressionType.RATIO),
        ]

        # 比较运算符：产生布尔值
        for op in [">", "<", ">=", "<=", "==", "!="]:
            rules[op] = [
                TypedOperator(op, [ExpressionType.PRICE, ExpressionType.PRICE], ExpressionType.BOOLEAN),
                TypedOperator(op, [ExpressionType.VOLUME, ExpressionType.VOLUME], ExpressionType.BOOLEAN),
                TypedOperator(op, [ExpressionType.RATIO, ExpressionType.RATIO], ExpressionType.BOOLEAN),
            ]

        return rules

    def get_column_type(self, column_name: str) -> ExpressionType:
        """获取列的类型

        Args:
            column_name: 列名

        Returns:
            ExpressionType: 列类型
        """
        return self.column_types.get(column_name, ExpressionType.UNKNOWN)

    def infer_operation_type(
        self, operator: str, left_type: ExpressionType, right_type: ExpressionType
    ) -> Optional[ExpressionType]:
        """推断运算结果类型

        Args:
            operator: 运算符
            left_type: 左操作数类型
            right_type: 右操作数类型

        Returns:
            Optional[ExpressionType]: 结果类型，如果不合法则返回None
        """
        if operator not in self.operator_rules:
            return ExpressionType.UNKNOWN

        # 检查所有可能的类型规则
        for rule in self.operator_rules[operator]:
            if rule.is_valid_inputs([left_type, right_type]):
                return rule.output_type

            # 如果算子可交换，尝试交换参数
            if rule.commutative and rule.is_valid_inputs([right_type, left_type]):
                return rule.output_type

        # 没有匹配的规则
        return None

    def is_valid_operation(self, operator: str, left_type: ExpressionType, right_type: ExpressionType) -> bool:
        """检查运算是否合法

        Args:
            operator: 运算符
            left_type: 左操作数类型
            right_type: 右操作数类型

        Returns:
            bool: 是否合法
        """
        result_type = self.infer_operation_type(operator, left_type, right_type)
        return result_type is not None

    def get_invalid_reason(self, operator: str, left_type: ExpressionType, right_type: ExpressionType) -> str:
        """获取不合法的原因

        Args:
            operator: 运算符
            left_type: 左操作数类型
            right_type: 右操作数类型

        Returns:
            str: 不合法原因
        """
        if self.is_valid_operation(operator, left_type, right_type):
            return ""

        # 常见错误模式
        if operator in ["+", "-"]:
            if left_type != right_type:
                return f"量纲不匹配: 不能对 {left_type.value} 和 {right_type.value} 进行 {operator} 运算"

        if operator == "+" and left_type == ExpressionType.PRICE and right_type == ExpressionType.VOLUME:
            return "语义错误: 价格和成交量不能相加（量纲不匹配）"

        return f"类型错误: {operator} 不支持 ({left_type.value}, {right_type.value})"


class SemanticValidator:
    """语义验证器

    白皮书依据: 第四章 4.1 语义合法性检查
    Phase 2 升级: 防止生成语义错误的表达式
    """

    def __init__(self, type_system: TypeSystem):
        """初始化语义验证器

        Args:
            type_system: 类型系统
        """
        self.type_system = type_system

        # 语义规则
        self.semantic_rules = self._initialize_semantic_rules()

        logger.info("语义验证器初始化完成")

    def _initialize_semantic_rules(self) -> List[Dict]:
        """初始化语义规则

        Returns:
            List[Dict]: 语义规则列表
        """
        return [
            {
                "name": "no_price_volume_mix",
                "description": "禁止价格和成交量混合运算",
                "check": lambda op, left, right: not (
                    op in ["+", "-"] and {left, right} == {ExpressionType.PRICE, ExpressionType.VOLUME}
                ),
            },
            {
                "name": "no_meaningless_division",
                "description": "禁止无意义的除法（如 volume / price）",
                "check": lambda op, left, right: not (
                    op == "/" and left == ExpressionType.VOLUME and right == ExpressionType.PRICE
                ),
            },
            {
                "name": "no_boolean_arithmetic",
                "description": "禁止对布尔值进行算术运算",
                "check": lambda op, left, right: not (
                    op in ["+", "-", "*", "/"]
                    and (left == ExpressionType.BOOLEAN or right == ExpressionType.BOOLEAN)  # pylint: disable=r1714
                ),
            },
        ]

    def validate_expression(
        self, operator: str, left_type: ExpressionType, right_type: ExpressionType
    ) -> Tuple[bool, List[str]]:
        """验证表达式语义

        Args:
            operator: 运算符
            left_type: 左操作数类型
            right_type: 右操作数类型

        Returns:
            Tuple[bool, List[str]]: (是否合法, 错误信息列表)
        """
        errors = []

        # 1. 类型检查
        if not self.type_system.is_valid_operation(operator, left_type, right_type):
            reason = self.type_system.get_invalid_reason(operator, left_type, right_type)
            errors.append(f"类型错误: {reason}")

        # 2. 语义规则检查
        for rule in self.semantic_rules:
            if not rule["check"](operator, left_type, right_type):
                errors.append(f"语义错误: {rule['description']}")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.debug(
                f"表达式验证失败: {operator}({left_type.value}, {right_type.value}) - " f"错误: {', '.join(errors)}"
            )

        return is_valid, errors

    def suggest_fix(self, operator: str, left_type: ExpressionType, right_type: ExpressionType) -> Optional[str]:
        """建议修复方案

        Args:
            operator: 运算符
            left_type: 左操作数类型
            right_type: 右操作数类型

        Returns:
            Optional[str]: 修复建议
        """
        # 价格+成交量 → 建议改为除法
        if operator == "+" and {left_type, right_type} == {ExpressionType.PRICE, ExpressionType.VOLUME}:
            return "建议: 将 + 改为 / 以计算价格/成交量比率"

        # 成交量/价格 → 建议改为价格/成交量
        if operator == "/" and left_type == ExpressionType.VOLUME and right_type == ExpressionType.PRICE:
            return "建议: 交换操作数顺序，使用 price / volume"

        # 不同类型相加 → 建议先归一化
        if operator in ["+", "-"] and left_type != right_type:
            return "建议: 先对操作数进行归一化（如 rank 或 zscore）再进行运算"

        return None
