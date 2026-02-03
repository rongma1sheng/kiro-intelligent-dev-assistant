"""测试覆盖率分析器

白皮书依据: 第十四章 14.1 质量标准
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class CoverageReport:
    """覆盖率报告

    白皮书依据: 第十四章 14.1.1 测试覆盖率目标

    Attributes:
        module_name: 模块名称
        total_statements: 总语句数
        covered_statements: 已覆盖语句数
        coverage_percent: 覆盖率百分比
        missing_lines: 未覆盖行号列表
        branch_coverage: 分支覆盖率
    """

    module_name: str
    total_statements: int
    covered_statements: int
    coverage_percent: float
    missing_lines: List[int]
    branch_coverage: Optional[float] = None


@dataclass
class CoverageTarget:
    """覆盖率目标

    白皮书依据: 第十四章 14.1.1 测试覆盖率目标

    核心模块 (brain/, core/): ≥ 85%
    执行模块 (execution/): ≥ 80%
    基础设施 (infra/): ≥ 75%
    界面模块 (interface/): ≥ 60%
    总体覆盖率: ≥ 70%
    """

    core_modules: float = 85.0  # brain/, core/
    execution_modules: float = 80.0  # execution/
    infrastructure_modules: float = 75.0  # infra/
    interface_modules: float = 60.0  # interface/
    overall: float = 70.0


class TestCoverageAnalyzer:
    """测试覆盖率分析器

    白皮书依据: 第十四章 14.1 质量标准

    核心功能：
    1. 分析各模块的测试覆盖率
    2. 强制执行覆盖率门禁
    3. 生成覆盖率报告
    4. 识别未覆盖代码

    Attributes:
        project_root: 项目根目录
        coverage_targets: 覆盖率目标
        coverage_data: 覆盖率数据
    """

    def __init__(self, project_root: Optional[Path] = None):
        """初始化测试覆盖率分析器

        Args:
            project_root: 项目根目录，默认为当前目录
        """
        self.project_root = project_root or Path.cwd()
        self.coverage_targets = CoverageTarget()
        self.coverage_data: Dict[str, CoverageReport] = {}

        logger.info(f"初始化TestCoverageAnalyzer: project_root={self.project_root}")

    def analyze_coverage(self, coverage_file: Optional[Path] = None) -> Dict[str, CoverageReport]:
        """分析测试覆盖率

        白皮书依据: 第十四章 14.1.1 测试覆盖率目标

        Args:
            coverage_file: 覆盖率数据文件路径，默认为 .coverage

        Returns:
            模块名到覆盖率报告的字典

        Raises:
            FileNotFoundError: 当覆盖率文件不存在时
            ValueError: 当覆盖率数据格式错误时
        """
        if coverage_file is None:
            coverage_file = self.project_root / ".coverage"

        if not coverage_file.exists():
            raise FileNotFoundError(f"覆盖率文件不存在: {coverage_file}")

        logger.info(f"开始分析覆盖率: {coverage_file}")

        # 生成JSON格式的覆盖率报告
        json_report_path = self.project_root / "coverage.json"
        try:
            result = subprocess.run(  # pylint: disable=w1510
                ["coverage", "json", "-o", str(json_report_path)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise ValueError(f"生成覆盖率报告失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise ValueError("生成覆盖率报告超时")  # pylint: disable=w0707
        except FileNotFoundError:
            raise ValueError("coverage命令未找到，请安装: pip install coverage")  # pylint: disable=w0707

        # 解析JSON报告
        if not json_report_path.exists():
            raise ValueError(f"覆盖率JSON报告未生成: {json_report_path}")

        with open(json_report_path, "r", encoding="utf-8") as f:
            coverage_json = json.load(f)

        # 提取各模块覆盖率
        self.coverage_data = {}
        files = coverage_json.get("files", {})

        for file_path, file_data in files.items():
            # 转换为相对路径
            rel_path = (
                Path(file_path).relative_to(self.project_root) if Path(file_path).is_absolute() else Path(file_path)
            )
            module_name = str(rel_path).replace("\\", "/").replace(".py", "").replace("/", ".")

            # 提取覆盖率数据
            summary = file_data.get("summary", {})
            total_statements = summary.get("num_statements", 0)
            covered_statements = summary.get("covered_lines", 0)
            missing_lines = file_data.get("missing_lines", [])

            # 计算覆盖率
            coverage_percent = (covered_statements / total_statements * 100) if total_statements > 0 else 0.0

            # 分支覆盖率（如果有）
            branch_coverage = None
            if "num_branches" in summary and summary["num_branches"] > 0:
                covered_branches = summary.get("covered_branches", 0)
                branch_coverage = covered_branches / summary["num_branches"] * 100

            report = CoverageReport(
                module_name=module_name,
                total_statements=total_statements,
                covered_statements=covered_statements,
                coverage_percent=coverage_percent,
                missing_lines=missing_lines,
                branch_coverage=branch_coverage,
            )

            self.coverage_data[module_name] = report

        logger.info(f"覆盖率分析完成，共分析 {len(self.coverage_data)} 个模块")

        return self.coverage_data

    def get_module_category(self, module_name: str) -> str:
        """获取模块类别

        Args:
            module_name: 模块名称

        Returns:
            模块类别: 'core', 'execution', 'infrastructure', 'interface', 'other'
        """
        if module_name.startswith("src.brain.") or module_name.startswith(  # pylint: disable=no-else-return
            "src.core."
        ):  # pylint: disable=no-else-return
            return "core"
        elif module_name.startswith("src.execution."):
            return "execution"
        elif module_name.startswith("src.infra."):
            return "infrastructure"
        elif module_name.startswith("src.interface."):
            return "interface"
        else:
            return "other"

    def get_category_coverage(self, category: str) -> float:
        """获取某类别的平均覆盖率

        Args:
            category: 模块类别

        Returns:
            平均覆盖率百分比
        """
        if not self.coverage_data:
            return 0.0

        category_modules = [
            report
            for module_name, report in self.coverage_data.items()
            if self.get_module_category(module_name) == category
        ]

        if not category_modules:
            return 0.0

        total_statements = sum(m.total_statements for m in category_modules)
        covered_statements = sum(m.covered_statements for m in category_modules)

        return (covered_statements / total_statements * 100) if total_statements > 0 else 0.0

    def get_overall_coverage(self) -> float:
        """获取总体覆盖率

        Returns:
            总体覆盖率百分比
        """
        if not self.coverage_data:
            return 0.0

        total_statements = sum(m.total_statements for m in self.coverage_data.values())
        covered_statements = sum(m.covered_statements for m in self.coverage_data.values())

        return (covered_statements / total_statements * 100) if total_statements > 0 else 0.0

    def enforce_coverage_gates(self) -> Dict[str, Any]:
        """强制执行覆盖率门禁

        白皮书依据: 第十四章 14.1.1 测试覆盖率目标

        检查各模块覆盖率是否达标：
        - 核心模块 (brain/, core/): ≥ 85%
        - 执行模块 (execution/): ≥ 80%
        - 基础设施 (infra/): ≥ 75%
        - 界面模块 (interface/): ≥ 60%
        - 总体覆盖率: ≥ 70%

        Returns:
            门禁检查结果，包含：
            - passed: 是否通过
            - overall_coverage: 总体覆盖率
            - category_coverage: 各类别覆盖率
            - violations: 违规项列表

        Raises:
            ValueError: 当覆盖率数据未分析时
        """
        if not self.coverage_data:
            raise ValueError("覆盖率数据未分析，请先调用 analyze_coverage()")

        logger.info("开始执行覆盖率门禁检查")

        violations = []

        # 检查核心模块
        core_coverage = self.get_category_coverage("core")
        if core_coverage < self.coverage_targets.core_modules:
            violations.append(
                {
                    "category": "core",
                    "actual": core_coverage,
                    "target": self.coverage_targets.core_modules,
                    "message": f"核心模块覆盖率不达标: {core_coverage:.2f}% < {self.coverage_targets.core_modules}%",
                }
            )

        # 检查执行模块
        execution_coverage = self.get_category_coverage("execution")
        if execution_coverage < self.coverage_targets.execution_modules:
            violations.append(
                {
                    "category": "execution",
                    "actual": execution_coverage,
                    "target": self.coverage_targets.execution_modules,
                    "message": f"执行模块覆盖率不达标: {execution_coverage:.2f}% < {self.coverage_targets.execution_modules}%",
                }
            )

        # 检查基础设施模块
        infra_coverage = self.get_category_coverage("infrastructure")
        if infra_coverage < self.coverage_targets.infrastructure_modules:
            violations.append(
                {
                    "category": "infrastructure",
                    "actual": infra_coverage,
                    "target": self.coverage_targets.infrastructure_modules,
                    "message": f"基础设施模块覆盖率不达标: {infra_coverage:.2f}% < {self.coverage_targets.infrastructure_modules}%",
                }
            )

        # 检查界面模块
        interface_coverage = self.get_category_coverage("interface")
        if interface_coverage < self.coverage_targets.interface_modules:
            violations.append(
                {
                    "category": "interface",
                    "actual": interface_coverage,
                    "target": self.coverage_targets.interface_modules,
                    "message": f"界面模块覆盖率不达标: {interface_coverage:.2f}% < {self.coverage_targets.interface_modules}%",
                }
            )

        # 检查总体覆盖率
        overall_coverage = self.get_overall_coverage()
        if overall_coverage < self.coverage_targets.overall:
            violations.append(
                {
                    "category": "overall",
                    "actual": overall_coverage,
                    "target": self.coverage_targets.overall,
                    "message": f"总体覆盖率不达标: {overall_coverage:.2f}% < {self.coverage_targets.overall}%",
                }
            )

        passed = len(violations) == 0

        result = {
            "passed": passed,
            "overall_coverage": overall_coverage,
            "category_coverage": {
                "core": core_coverage,
                "execution": execution_coverage,
                "infrastructure": infra_coverage,
                "interface": interface_coverage,
            },
            "violations": violations,
        }

        if passed:
            logger.info("✅ 覆盖率门禁检查通过")
        else:
            logger.error(f"❌ 覆盖率门禁检查失败，共 {len(violations)} 项违规")
            for violation in violations:
                logger.error(f"  - {violation['message']}")

        return result

    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """生成覆盖率报告

        Args:
            output_file: 输出文件路径，默认为 coverage_report.json

        Returns:
            报告JSON字符串

        Raises:
            ValueError: 当覆盖率数据未分析时
        """
        if not self.coverage_data:
            raise ValueError("覆盖率数据未分析，请先调用 analyze_coverage()")

        report = {
            "timestamp": str(Path.cwd()),
            "overall_coverage": self.get_overall_coverage(),
            "category_coverage": {
                "core": self.get_category_coverage("core"),
                "execution": self.get_category_coverage("execution"),
                "infrastructure": self.get_category_coverage("infrastructure"),
                "interface": self.get_category_coverage("interface"),
            },
            "modules": {module_name: asdict(report) for module_name, report in self.coverage_data.items()},
            "targets": asdict(self.coverage_targets),
        }

        report_json = json.dumps(report, indent=2, ensure_ascii=False)

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_json)
            logger.info(f"覆盖率报告已生成: {output_file}")

        return report_json

    def identify_uncovered_code(self, min_coverage: float = 80.0) -> List[Dict[str, Any]]:
        """识别未覆盖代码

        Args:
            min_coverage: 最小覆盖率阈值，默认80%

        Returns:
            未达标模块列表，每项包含：
            - module_name: 模块名称
            - coverage_percent: 覆盖率
            - missing_lines: 未覆盖行号
            - priority: 优先级 (high/medium/low)

        Raises:
            ValueError: 当覆盖率数据未分析时
        """
        if not self.coverage_data:
            raise ValueError("覆盖率数据未分析，请先调用 analyze_coverage()")

        uncovered_modules = []

        for module_name, report in self.coverage_data.items():
            if report.coverage_percent < min_coverage:
                category = self.get_module_category(module_name)

                # 确定优先级
                if category == "core":
                    priority = "high"
                elif category in ["execution", "infrastructure"]:
                    priority = "medium"
                else:
                    priority = "low"

                uncovered_modules.append(
                    {
                        "module_name": module_name,
                        "coverage_percent": report.coverage_percent,
                        "missing_lines": report.missing_lines,
                        "total_statements": report.total_statements,
                        "covered_statements": report.covered_statements,
                        "category": category,
                        "priority": priority,
                    }
                )

        # 按优先级和覆盖率排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        uncovered_modules.sort(key=lambda x: (priority_order[x["priority"]], x["coverage_percent"]))

        logger.info(f"识别到 {len(uncovered_modules)} 个未达标模块（< {min_coverage}%）")

        return uncovered_modules
