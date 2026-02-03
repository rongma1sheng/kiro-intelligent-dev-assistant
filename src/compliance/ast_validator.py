"""AST白名单验证器

白皮书依据: 第七章 7.2 AST白名单验证

本模块实现基于AST分析的代码安全验证，确保AI生成的代码只使用白名单函数和模块。
"""

import ast
from dataclasses import dataclass, field
from typing import List, Set

from loguru import logger


@dataclass
class ValidationResult:
    """验证结果

    白皮书依据: 第七章 7.2 AST白名单验证

    Attributes:
        approved: 是否通过验证
        reason: 验证失败原因
        violations: 违规项列表
        execution_time_ms: 验证耗时（毫秒）
        content_hash: 内容哈希
    """

    approved: bool
    reason: str = ""
    violations: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    content_hash: str = ""


class ASTValidationError(Exception):
    """AST验证错误"""


class ASTWhitelistValidator:
    """AST白名单验证器

    白皮书依据: 第七章 7.2 AST白名单验证

    基于AST分析验证代码安全性，确保只使用白名单函数和模块。

    Attributes:
        whitelist_functions: 白名单函数集合
        blacklist_functions: 黑名单函数集合
        blacklist_modules: 黑名单模块集合
        max_complexity: 最大复杂度限制
    """

    def __init__(
        self,
        whitelist_functions: Set[str] = None,
        blacklist_functions: Set[str] = None,
        blacklist_modules: Set[str] = None,
        max_complexity: int = 50,
    ):
        """初始化ASTWhitelistValidator

        白皮书依据: 第七章 7.2 AST白名单验证

        Args:
            whitelist_functions: 白名单函数集合，默认使用预定义集合
            blacklist_functions: 黑名单函数集合，默认使用预定义集合
            blacklist_modules: 黑名单模块集合，默认使用预定义集合
            max_complexity: 最大复杂度限制，默认50
        """
        # 白名单函数：允许的安全函数
        self.whitelist_functions: Set[str] = whitelist_functions or {
            # Python内置函数（安全子集）
            "abs",
            "min",
            "max",
            "sum",
            "round",
            "len",
            "range",
            "int",
            "float",
            "str",
            "bool",
            "list",
            "dict",
            "tuple",
            "set",
            "sorted",
            "reversed",
            "enumerate",
            "zip",
            "map",
            "filter",
            "any",
            "all",
            "isinstance",
            "type",
            "print",
            # Pandas函数
            "pd.Series",
            "pd.DataFrame",
            "pd.concat",
            "pd.merge",
            "pd.read_csv",
            "pd.to_datetime",
            "pd.cut",
            "pd.qcut",
            # NumPy函数
            "np.array",
            "np.zeros",
            "np.ones",
            "np.arange",
            "np.linspace",
            "np.mean",
            "np.std",
            "np.var",
            "np.median",
            "np.percentile",
            "np.sum",
            "np.prod",
            "np.min",
            "np.max",
            "np.abs",
            "np.sqrt",
            "np.exp",
            "np.log",
            "np.log10",
            "np.power",
            "np.sin",
            "np.cos",
            "np.tan",
            "np.arcsin",
            "np.arccos",
            "np.arctan",
            "np.corrcoef",
            "np.cov",
            "np.dot",
            "np.matmul",
            "np.where",
            "np.select",
            "np.clip",
            "np.nan",
            "np.inf",
            # 因子算子（白皮书第四章定义）
            "rank",
            "delay",
            "delta",
            "ts_sum",
            "ts_mean",
            "ts_std",
            "ts_max",
            "ts_min",
            "ts_rank",
            "ts_corr",
            "ts_cov",
            "sign",
            "log",
            "power",
            "scale",
            "normalize",
        }

        # 黑名单函数：危险函数
        self.blacklist_functions: Set[str] = blacklist_functions or {
            # 代码执行
            "eval",
            "exec",
            "compile",
            "__import__",
            "globals",
            "locals",
            "vars",
            # 文件操作
            "open",
            "file",
            "input",
            "raw_input",
            # 系统操作
            "os.system",
            "os.popen",
            "os.spawn*",
            "os.exec*",
            "os.fork",
            # 子进程
            "subprocess.call",
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.check_call",
            "subprocess.check_output",
            # 网络操作
            "socket.socket",
            "urllib.request",
            "urllib.urlopen",
            "requests.get",
            "requests.post",
            "httplib.HTTPConnection",
            # 序列化（不安全）
            "pickle.load",
            "pickle.loads",
            "pickle.dump",
            "pickle.dumps",
            "marshal.load",
            "marshal.loads",
            "marshal.dump",
            "marshal.dumps",
            # 反射和动态加载
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
            "__getattribute__",
            "__setattr__",
            "__delattr__",
            "importlib.import_module",
            "importlib.__import__",
            # 其他危险操作
            "ctypes.*",
            "multiprocessing.*",
            "threading.*",
            "exit",
            "quit",
            "reload",
            "help",
        }

        # 黑名单模块：禁止导入的模块
        self.blacklist_modules: Set[str] = blacklist_modules or {
            "os",
            "sys",
            "subprocess",
            "socket",
            "pickle",
            "marshal",
            "ctypes",
            "multiprocessing",
            "threading",
            "importlib",
            "urllib",
            "urllib.request",
            "urllib.parse",
            "urllib.error",
            "requests",
            "httplib",
            "http.client",
            "shutil",
            "tempfile",
            "glob",
            "pathlib",
            "__builtin__",
            "builtins",
            "__main__",
        }

        self.max_complexity: int = max_complexity

        logger.info(
            f"初始化ASTWhitelistValidator: "
            f"whitelist={len(self.whitelist_functions)}, "
            f"blacklist_functions={len(self.blacklist_functions)}, "
            f"blacklist_modules={len(self.blacklist_modules)}, "
            f"max_complexity={max_complexity}"
        )

    def validate(self, code: str) -> ValidationResult:
        """验证代码

        白皮书依据: 第七章 7.2 AST白名单验证

        检查项：
        1. 黑名单函数调用
        2. 黑名单模块导入
        3. 代码复杂度

        Args:
            code: Python代码字符串

        Returns:
            验证结果

        Raises:
            ASTValidationError: AST解析失败
        """
        import hashlib  # pylint: disable=import-outside-toplevel
        import time  # pylint: disable=import-outside-toplevel

        start_time = time.perf_counter()

        if not code or not code.strip():
            return ValidationResult(
                approved=False, reason="代码为空", violations=["空代码"], execution_time_ms=0.0, content_hash=""
            )

        # 计算内容哈希
        content_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

        try:
            # 解析AST
            tree = ast.parse(code)
        except SyntaxError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"AST解析失败: {e}")
            return ValidationResult(
                approved=False,
                reason=f"语法错误: {e}",
                violations=[f"语法错误: {e}"],
                execution_time_ms=elapsed_ms,
                content_hash=content_hash,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"AST解析异常: {e}")
            return ValidationResult(
                approved=False,
                reason=f"解析异常: {e}",
                violations=[f"解析异常: {e}"],
                execution_time_ms=elapsed_ms,
                content_hash=content_hash,
            )

        violations: List[str] = []

        # 检查黑名单函数调用
        function_violations = self._check_function_calls(tree)
        violations.extend(function_violations)

        # 检查黑名单模块导入
        import_violations = self._check_imports(tree)
        violations.extend(import_violations)

        # 检查代码复杂度
        complexity_violations = self._check_complexity(tree)
        violations.extend(complexity_violations)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if violations:
            logger.warning(f"AST验证失败: {len(violations)}个违规项, " f"耗时: {elapsed_ms:.2f}ms")
            return ValidationResult(
                approved=False,
                reason=f"发现{len(violations)}个违规项",
                violations=violations,
                execution_time_ms=elapsed_ms,
                content_hash=content_hash,
            )

        logger.info(f"AST验证通过, 耗时: {elapsed_ms:.2f}ms")
        return ValidationResult(
            approved=True, reason="验证通过", violations=[], execution_time_ms=elapsed_ms, content_hash=content_hash
        )

    def _check_function_calls(self, tree: ast.AST) -> List[str]:
        """检查函数调用

        白皮书依据: 第七章 7.2 AST白名单验证

        Args:
            tree: AST树

        Returns:
            违规项列表
        """
        violations: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name(node.func)

                if func_name:
                    # 检查是否在黑名单中
                    if self._is_blacklisted_function(func_name):
                        violations.append(f"黑名单函数: {func_name}")
                        logger.warning(f"检测到黑名单函数调用: {func_name}")

        return violations

    def _check_imports(self, tree: ast.AST) -> List[str]:
        """检查模块导入

        白皮书依据: 第七章 7.2 AST白名单验证

        Args:
            tree: AST树

        Returns:
            违规项列表
        """
        violations: List[str] = []

        for node in ast.walk(tree):
            # 检查 import xxx
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if self._is_blacklisted_module(module_name):
                        violations.append(f"黑名单模块: import {module_name}")
                        logger.warning(f"检测到黑名单模块导入: import {module_name}")

            # 检查 from xxx import yyy
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                if self._is_blacklisted_module(module_name):
                    violations.append(f"黑名单模块: from {module_name} import ...")
                    logger.warning(f"检测到黑名单模块导入: from {module_name} import ...")

        return violations

    def _check_complexity(self, tree: ast.AST) -> List[str]:
        """检查代码复杂度

        白皮书依据: 第七章 7.2 AST白名单验证

        使用简化的圈复杂度计算：统计决策点数量

        Args:
            tree: AST树

        Returns:
            违规项列表
        """
        violations: List[str] = []

        # 统计决策点
        decision_points = 0

        for node in ast.walk(tree):
            # 条件语句
            if isinstance(node, (ast.If, ast.IfExp)):
                decision_points += 1
            # 循环语句
            elif isinstance(node, (ast.For, ast.While)):
                decision_points += 1
            # 异常处理
            elif isinstance(node, ast.ExceptHandler):
                decision_points += 1
            # 布尔运算
            elif isinstance(node, ast.BoolOp):
                decision_points += len(node.values) - 1

        if decision_points > self.max_complexity:
            violations.append(f"代码复杂度过高: {decision_points} > {self.max_complexity}")
            logger.warning(f"代码复杂度超限: {decision_points} > {self.max_complexity}")

        return violations

    def _get_function_name(self, node: ast.AST) -> str:
        """获取函数名称

        Args:
            node: AST节点

        Returns:
            函数名称字符串
        """
        if isinstance(node, ast.Name):  # pylint: disable=no-else-return
            return node.id
        elif isinstance(node, ast.Attribute):
            # 处理 obj.method 形式
            value_name = self._get_function_name(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
            return node.attr
        elif isinstance(node, ast.Call):
            # 处理链式调用
            return self._get_function_name(node.func)
        else:
            return ""

    def _is_blacklisted_function(self, func_name: str) -> bool:
        """检查函数是否在黑名单中

        Args:
            func_name: 函数名称

        Returns:
            是否在黑名单中
        """
        # 精确匹配
        if func_name in self.blacklist_functions:
            return True

        # 通配符匹配（如 os.spawn*）
        for blacklisted in self.blacklist_functions:
            if "*" in blacklisted:
                prefix = blacklisted.replace("*", "")
                if func_name.startswith(prefix):
                    return True

        return False

    def _is_blacklisted_module(self, module_name: str) -> bool:
        """检查模块是否在黑名单中

        Args:
            module_name: 模块名称

        Returns:
            是否在黑名单中
        """
        # 精确匹配
        if module_name in self.blacklist_modules:
            return True

        # 前缀匹配（如 urllib.request 匹配 urllib）
        for blacklisted in self.blacklist_modules:
            if module_name.startswith(blacklisted + "."):
                return True

        return False
