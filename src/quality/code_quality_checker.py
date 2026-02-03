"""代码质量检查器

白皮书依据: 第十四章 14.1.2 代码质量标准
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class QualityMetrics:
    """质量指标

    白皮书依据: 第十四章 14.1.2 代码质量标准

    Attributes:
        complexity_score: 圈复杂度评分
        style_score: 代码风格评分
        type_coverage: 类型注解覆盖率
        security_issues: 安全问题数量
        passed: 是否通过质量检查
    """

    complexity_score: float
    style_score: float
    type_coverage: float
    security_issues: int
    passed: bool


@dataclass
class ComplexityReport:
    """圈复杂度报告

    Attributes:
        file_path: 文件路径
        function_name: 函数名
        complexity: 圈复杂度
        line_number: 行号
    """

    file_path: str
    function_name: str
    complexity: int
    line_number: int


@dataclass
class StyleIssue:
    """代码风格问题

    Attributes:
        file_path: 文件路径
        line_number: 行号
        column: 列号
        code: 错误代码
        message: 错误信息
        severity: 严重程度
    """

    file_path: str
    line_number: int
    column: int
    code: str
    message: str
    severity: str


@dataclass
class SecurityIssue:
    """安全问题

    Attributes:
        file_path: 文件路径
        line_number: 行号
        issue_severity: 严重程度
        issue_confidence: 置信度
        issue_text: 问题描述
        test_id: 测试ID
    """

    file_path: str
    line_number: int
    issue_severity: str
    issue_confidence: str
    issue_text: str
    test_id: str


class CodeQualityChecker:
    """代码质量检查器

    白皮书依据: 第十四章 14.1.2 代码质量标准

    核心功能：
    1. 检查圈复杂度（使用radon）
    2. 检查代码风格（使用flake8）
    3. 检查类型注解（使用mypy）
    4. 检查安全问题（使用bandit）

    质量标准：
    - 函数圈复杂度 ≤ 10
    - 类圈复杂度 ≤ 50
    - 代码风格符合PEP8
    - 类型注解完整
    - 无安全漏洞

    Attributes:
        project_root: 项目根目录
        max_function_complexity: 最大函数圈复杂度
        max_class_complexity: 最大类圈复杂度
        max_line_length: 最大行长度
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        max_function_complexity: int = 10,
        max_class_complexity: int = 50,
        max_line_length: int = 120,
    ):
        """初始化代码质量检查器

        Args:
            project_root: 项目根目录，默认为当前目录
            max_function_complexity: 最大函数圈复杂度，默认10
            max_class_complexity: 最大类圈复杂度，默认50
            max_line_length: 最大行长度，默认120
        """
        self.project_root = project_root or Path.cwd()
        self.max_function_complexity = max_function_complexity
        self.max_class_complexity = max_class_complexity
        self.max_line_length = max_line_length

        logger.info(
            f"初始化CodeQualityChecker: "
            f"max_function_complexity={max_function_complexity}, "
            f"max_class_complexity={max_class_complexity}"
        )

    def check_complexity(self, target_path: Optional[Path] = None) -> List[ComplexityReport]:
        """检查圈复杂度

        白皮书依据: 第十四章 14.1.2 代码质量标准

        使用radon工具检查代码圈复杂度：
        - 函数圈复杂度 ≤ 10
        - 类圈复杂度 ≤ 50

        Args:
            target_path: 目标路径，默认为src/目录

        Returns:
            圈复杂度报告列表

        Raises:
            ValueError: 当radon命令未找到时
            ValueError: 当radon执行失败时
        """
        if target_path is None:
            target_path = self.project_root / "src"

        if not target_path.exists():
            raise ValueError(f"目标路径不存在: {target_path}")

        logger.info(f"开始检查圈复杂度: {target_path}")

        try:
            # 运行radon cc命令
            result = subprocess.run(  # pylint: disable=w1510
                ["radon", "cc", str(target_path), "-s", "-j"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise ValueError(f"radon执行失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise ValueError("radon执行超时")  # pylint: disable=w0707
        except FileNotFoundError:
            raise ValueError("radon命令未找到，请安装: pip install radon")  # pylint: disable=w0707

        # 解析JSON输出
        try:
            complexity_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ValueError(f"radon输出解析失败: {e}")  # pylint: disable=w0707

        # 提取复杂度报告
        reports = []
        for file_path, functions in complexity_data.items():
            for func_data in functions:
                report = ComplexityReport(
                    file_path=file_path,
                    function_name=func_data.get("name", "unknown"),
                    complexity=func_data.get("complexity", 0),
                    line_number=func_data.get("lineno", 0),
                )
                reports.append(report)

        # 过滤超标的复杂度
        high_complexity = [r for r in reports if r.complexity > self.max_function_complexity]

        if high_complexity:
            logger.warning(f"发现 {len(high_complexity)} 个高复杂度函数")
            for report in high_complexity[:5]:  # 只显示前5个
                logger.warning(
                    f"  - {report.file_path}:{report.line_number} "
                    f"{report.function_name} (complexity={report.complexity})"
                )
        else:
            logger.info("✅ 所有函数圈复杂度符合标准")

        return reports

    def check_style(self, target_path: Optional[Path] = None) -> List[StyleIssue]:
        """检查代码风格

        白皮书依据: 第十四章 14.1.2 代码质量标准

        使用flake8工具检查代码风格：
        - 符合PEP8规范
        - 最大行长度120

        Args:
            target_path: 目标路径，默认为src/目录

        Returns:
            代码风格问题列表

        Raises:
            ValueError: 当flake8命令未找到时
            ValueError: 当flake8执行失败时
        """
        if target_path is None:
            target_path = self.project_root / "src"

        if not target_path.exists():
            raise ValueError(f"目标路径不存在: {target_path}")

        logger.info(f"开始检查代码风格: {target_path}")

        try:
            # 运行flake8命令
            result = subprocess.run(  # pylint: disable=w1510
                ["flake8", str(target_path), f"--max-line-length={self.max_line_length}", "--format=json"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )

            # flake8返回非0表示有问题，但这是正常的
            # 只有在stderr有内容时才认为是错误
            if result.stderr and "error" in result.stderr.lower():
                raise ValueError(f"flake8执行失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise ValueError("flake8执行超时")  # pylint: disable=w0707
        except FileNotFoundError:
            raise ValueError("flake8命令未找到，请安装: pip install flake8")  # pylint: disable=w0707

        # 解析JSON输出
        issues = []
        if result.stdout:
            try:
                style_data = json.loads(result.stdout)

                for file_path, file_issues in style_data.items():
                    for issue_data in file_issues:
                        issue = StyleIssue(
                            file_path=file_path,
                            line_number=issue_data.get("line_number", 0),
                            column=issue_data.get("column_number", 0),
                            code=issue_data.get("code", ""),
                            message=issue_data.get("text", ""),
                            severity=issue_data.get("physical_line", "info"),
                        )
                        issues.append(issue)

            except json.JSONDecodeError:
                # flake8可能输出非JSON格式，尝试解析文本格式
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        parts = line.split(":", 4)
                        if len(parts) >= 4:
                            issue = StyleIssue(
                                file_path=parts[0],
                                line_number=int(parts[1]) if parts[1].isdigit() else 0,
                                column=int(parts[2]) if parts[2].isdigit() else 0,
                                code=parts[3].strip().split()[0] if len(parts) > 3 else "",
                                message=parts[4].strip() if len(parts) > 4 else "",
                                severity="warning",
                            )
                            issues.append(issue)

        if issues:
            logger.warning(f"发现 {len(issues)} 个代码风格问题")
            for issue in issues[:5]:  # 只显示前5个
                logger.warning(
                    f"  - {issue.file_path}:{issue.line_number}:{issue.column} " f"{issue.code}: {issue.message}"
                )
        else:
            logger.info("✅ 代码风格符合标准")

        return issues

    def check_types(self, target_path: Optional[Path] = None) -> Dict[str, Any]:
        """检查类型注解

        白皮书依据: 第十四章 14.1.2 代码质量标准

        使用mypy工具检查类型注解：
        - 类型注解完整
        - 类型使用正确

        Args:
            target_path: 目标路径，默认为src/目录

        Returns:
            类型检查结果，包含：
            - errors: 错误数量
            - warnings: 警告数量
            - notes: 提示数量
            - issues: 问题列表

        Raises:
            ValueError: 当mypy命令未找到时
        """
        if target_path is None:
            target_path = self.project_root / "src"

        if not target_path.exists():
            raise ValueError(f"目标路径不存在: {target_path}")

        logger.info(f"开始检查类型注解: {target_path}")

        try:
            # 运行mypy命令
            result = subprocess.run(  # pylint: disable=w1510
                ["mypy", str(target_path), "--ignore-missing-imports"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )

            # mypy返回非0表示有类型错误，这是正常的

        except subprocess.TimeoutExpired:
            raise ValueError("mypy执行超时")  # pylint: disable=w0707
        except FileNotFoundError:
            raise ValueError("mypy命令未找到，请安装: pip install mypy")  # pylint: disable=w0707

        # 解析输出
        errors = 0
        warnings = 0
        notes = 0
        issues = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            if "error:" in line:
                errors += 1
                issues.append({"type": "error", "message": line})
            elif "warning:" in line:
                warnings += 1
                issues.append({"type": "warning", "message": line})
            elif "note:" in line:
                notes += 1
                issues.append({"type": "note", "message": line})

        type_result = {"errors": errors, "warnings": warnings, "notes": notes, "issues": issues}

        if errors > 0:
            logger.warning(f"发现 {errors} 个类型错误")
            for issue in issues[:5]:  # 只显示前5个
                if issue["type"] == "error":
                    logger.warning(f"  - {issue['message']}")
        else:
            logger.info("✅ 类型注解检查通过")

        return type_result

    def check_security(self, target_path: Optional[Path] = None) -> List[SecurityIssue]:
        """检查安全问题

        白皮书依据: 第十四章 14.1.2 代码质量标准

        使用bandit工具检查安全问题：
        - 无硬编码密钥
        - 无SQL注入风险
        - 无命令注入风险

        Args:
            target_path: 目标路径，默认为src/目录

        Returns:
            安全问题列表

        Raises:
            ValueError: 当bandit命令未找到时
        """
        if target_path is None:
            target_path = self.project_root / "src"

        if not target_path.exists():
            raise ValueError(f"目标路径不存在: {target_path}")

        logger.info(f"开始检查安全问题: {target_path}")

        try:
            # 运行bandit命令
            result = subprocess.run(  # pylint: disable=w1510
                ["bandit", "-r", str(target_path), "-f", "json"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )

            # bandit返回非0表示有安全问题，这是正常的

        except subprocess.TimeoutExpired:
            raise ValueError("bandit执行超时")  # pylint: disable=w0707
        except FileNotFoundError:
            raise ValueError("bandit命令未找到，请安装: pip install bandit")  # pylint: disable=w0707

        # 解析JSON输出
        security_issues = []
        if result.stdout:
            try:
                bandit_data = json.loads(result.stdout)

                for issue_data in bandit_data.get("results", []):
                    issue = SecurityIssue(
                        file_path=issue_data.get("filename", ""),
                        line_number=issue_data.get("line_number", 0),
                        issue_severity=issue_data.get("issue_severity", "UNKNOWN"),
                        issue_confidence=issue_data.get("issue_confidence", "UNKNOWN"),
                        issue_text=issue_data.get("issue_text", ""),
                        test_id=issue_data.get("test_id", ""),
                    )
                    security_issues.append(issue)

            except json.JSONDecodeError as e:
                logger.warning(f"bandit输出解析失败: {e}")

        if security_issues:
            logger.warning(f"发现 {len(security_issues)} 个安全问题")
            for issue in security_issues[:5]:  # 只显示前5个
                logger.warning(
                    f"  - {issue.file_path}:{issue.line_number} " f"[{issue.issue_severity}] {issue.issue_text}"
                )
        else:
            logger.info("✅ 未发现安全问题")

        return security_issues

    def check_all(self, target_path: Optional[Path] = None) -> QualityMetrics:
        """执行所有质量检查

        白皮书依据: 第十四章 14.1.2 代码质量标准

        Args:
            target_path: 目标路径，默认为src/目录

        Returns:
            质量指标
        """
        if target_path is None:
            target_path = self.project_root / "src"

        logger.info(f"开始执行所有质量检查: {target_path}")

        # 1. 检查圈复杂度
        try:
            complexity_reports = self.check_complexity(target_path)
            high_complexity_count = sum(1 for r in complexity_reports if r.complexity > self.max_function_complexity)
            complexity_score = max(0.0, 100.0 - high_complexity_count * 5.0)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"圈复杂度检查失败: {e}")
            complexity_score = 0.0

        # 2. 检查代码风格
        try:
            style_issues = self.check_style(target_path)
            style_score = max(0.0, 100.0 - len(style_issues) * 0.5)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"代码风格检查失败: {e}")
            style_score = 0.0

        # 3. 检查类型注解
        try:
            type_result = self.check_types(target_path)
            type_errors = type_result["errors"]
            type_coverage = max(0.0, 100.0 - type_errors * 2.0)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"类型注解检查失败: {e}")
            type_coverage = 0.0

        # 4. 检查安全问题
        try:
            security_issues = self.check_security(target_path)
            security_issue_count = len(security_issues)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"安全检查失败: {e}")
            security_issue_count = 999  # 检查失败视为严重问题

        # 综合评分
        passed = (
            complexity_score >= 80.0 and style_score >= 80.0 and type_coverage >= 70.0 and security_issue_count == 0
        )

        metrics = QualityMetrics(
            complexity_score=complexity_score,
            style_score=style_score,
            type_coverage=type_coverage,
            security_issues=security_issue_count,
            passed=passed,
        )

        if passed:
            logger.info("✅ 所有质量检查通过")
        else:
            logger.error("❌ 质量检查未通过")

        logger.info(
            f"质量指标: "
            f"complexity={complexity_score:.2f}, "
            f"style={style_score:.2f}, "
            f"type_coverage={type_coverage:.2f}, "
            f"security_issues={security_issue_count}"
        )

        return metrics
