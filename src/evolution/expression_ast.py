"""因子表达式AST（抽象语法树）

白皮书依据: 第四章 4.1 遗传算法 - 表达式结构化表示
工程目标: 支持真正的子树级交叉操作
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union


class NodeType(Enum):
    """AST节点类型"""

    COLUMN = "column"  # 数据列（叶子节点）
    CONSTANT = "constant"  # 常量（叶子节点）
    BINARY_OP = "binary_op"  # 二元运算符
    UNARY_OP = "unary_op"  # 一元运算符
    FUNCTION = "function"  # 函数调用


@dataclass
class ASTNode:
    """AST节点

    Attributes:
        node_type: 节点类型
        value: 节点值（列名、常量值、运算符名称等）
        children: 子节点列表
        parent: 父节点引用
    """

    node_type: NodeType
    value: Union[str, float, int]
    children: List["ASTNode"] = None
    parent: Optional["ASTNode"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def is_leaf(self) -> bool:
        """是否为叶子节点"""
        return self.node_type in [NodeType.COLUMN, NodeType.CONSTANT]

    def depth(self) -> int:
        """计算子树深度"""
        if self.is_leaf():
            return 1
        return 1 + max(child.depth() for child in self.children)

    def size(self) -> int:
        """计算子树节点数"""
        if self.is_leaf():
            return 1
        return 1 + sum(child.size() for child in self.children)

    def to_expression(self) -> str:
        """转换回表达式字符串"""
        if self.node_type == NodeType.COLUMN:  # pylint: disable=no-else-return
            return str(self.value)

        elif self.node_type == NodeType.CONSTANT:
            return str(self.value)

        elif self.node_type == NodeType.BINARY_OP:
            if len(self.children) != 2:
                raise ValueError(f"二元运算符需要2个子节点，当前: {len(self.children)}")
            left = self.children[0].to_expression()
            right = self.children[1].to_expression()
            return f"({left} {self.value} {right})"

        elif self.node_type == NodeType.UNARY_OP:
            if len(self.children) != 1:
                raise ValueError(f"一元运算符需要1个子节点，当前: {len(self.children)}")
            child = self.children[0].to_expression()
            return f"{self.value}({child})"

        elif self.node_type == NodeType.FUNCTION:
            if not self.children:
                raise ValueError("函数调用需要至少1个参数")
            args = ", ".join(child.to_expression() for child in self.children)
            return f"{self.value}({args})"

        else:
            raise ValueError(f"未知节点类型: {self.node_type}")

    def clone(self) -> "ASTNode":
        """深度克隆节点及其子树"""
        cloned = ASTNode(node_type=self.node_type, value=self.value, children=[])

        for child in self.children:
            cloned_child = child.clone()
            cloned_child.parent = cloned
            cloned.children.append(cloned_child)

        return cloned


class ExpressionParser:
    """轻量级表达式解析器

    白皮书依据: 第四章 4.1 遗传算法 - 表达式解析

    支持的语法:
    - 列名: close, volume, high, low
    - 常量: 数字
    - 二元运算: +, -, *, /
    - 函数调用: sma(close, 20), rsi(volume, 14)
    """

    def __init__(self):
        self.binary_operators = ["+", "-", "*", "/"]
        self.unary_operators = ["abs", "sqrt", "log"]
        self.functions = ["sma", "ema", "rsi", "macd", "bollinger", "safe_div"]

    def parse(self, expression: str) -> ASTNode:
        """解析表达式为AST

        Args:
            expression: 因子表达式字符串

        Returns:
            ASTNode: AST根节点
        """
        expression = expression.strip()

        # 尝试解析为列名
        if self._is_column(expression):
            return ASTNode(NodeType.COLUMN, expression)

        # 尝试解析为常量
        if self._is_constant(expression):
            return ASTNode(NodeType.CONSTANT, float(expression))

        # 尝试解析为括号表达式
        if expression.startswith("(") and expression.endswith(")"):
            inner = expression[1:-1]

            # 查找主运算符
            op_pos = self._find_main_operator(inner)
            if op_pos >= 0:
                op = inner[op_pos]
                left_expr = inner[:op_pos].strip()
                right_expr = inner[op_pos + 1 :].strip()

                node = ASTNode(NodeType.BINARY_OP, op)
                left_node = self.parse(left_expr)
                right_node = self.parse(right_expr)

                left_node.parent = node
                right_node.parent = node
                node.children = [left_node, right_node]

                return node

        # 尝试解析为函数调用
        if "(" in expression and expression.endswith(")"):
            func_name, args_str = expression.split("(", 1)
            func_name = func_name.strip()
            args_str = args_str[:-1].strip()  # 移除最后的')'

            if func_name in self.functions or func_name in self.unary_operators:
                node = ASTNode(NodeType.FUNCTION, func_name)

                # 解析参数
                args = self._split_arguments(args_str)
                for arg in args:
                    arg_node = self.parse(arg)
                    arg_node.parent = node
                    node.children.append(arg_node)

                return node

        # 无法解析，返回列名节点（兜底）
        return ASTNode(NodeType.COLUMN, expression)

    def _is_column(self, s: str) -> bool:
        """判断是否为列名"""
        return s.isidentifier() and not s.isdigit()

    def _is_constant(self, s: str) -> bool:
        """判断是否为常量"""
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _find_main_operator(self, expression: str) -> int:
        """查找主运算符位置

        主运算符是括号层级为0的第一个运算符
        """
        depth = 0
        for i, char in enumerate(expression):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0 and char in self.binary_operators:
                return i
        return -1

    def _split_arguments(self, args_str: str) -> List[str]:
        """分割函数参数

        考虑括号嵌套，正确分割参数
        """
        args = []
        current_arg = []
        depth = 0

        for char in args_str:
            if char == "(":
                depth += 1
                current_arg.append(char)
            elif char == ")":
                depth -= 1
                current_arg.append(char)
            elif char == "," and depth == 0:
                args.append("".join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)

        if current_arg:
            args.append("".join(current_arg).strip())

        return args


class ASTCrossover:
    """基于AST的交叉操作

    白皮书依据: 第四章 4.1 遗传算法 - 子树级交叉
    """

    def crossover(self, parent1: ASTNode, parent2: ASTNode) -> ASTNode:
        """执行子树级交叉

        Args:
            parent1: 父代1的AST
            parent2: 父代2的AST

        Returns:
            ASTNode: 后代AST
        """
        # 克隆父代1作为基础
        child = parent1.clone()

        # 从父代1中随机选择一个子树
        subtree1_nodes = self._collect_all_nodes(child)
        if not subtree1_nodes:
            return child

        import random  # pylint: disable=import-outside-toplevel

        subtree1 = random.choice(subtree1_nodes)

        # 从父代2中随机选择一个子树
        subtree2_nodes = self._collect_all_nodes(parent2)
        if not subtree2_nodes:
            return child

        subtree2 = random.choice(subtree2_nodes)

        # 克隆父代2的子树
        subtree2_clone = subtree2.clone()

        # 替换父代1的子树
        if subtree1.parent is None:  # pylint: disable=no-else-return
            # 替换根节点
            return subtree2_clone
        else:
            # 替换子节点
            parent_node = subtree1.parent
            for i, child_node in enumerate(parent_node.children):
                if child_node is subtree1:
                    parent_node.children[i] = subtree2_clone
                    subtree2_clone.parent = parent_node
                    break

        return child

    def _collect_all_nodes(self, root: ASTNode) -> List[ASTNode]:
        """收集所有节点"""
        nodes = [root]
        for child in root.children:
            nodes.extend(self._collect_all_nodes(child))
        return nodes
