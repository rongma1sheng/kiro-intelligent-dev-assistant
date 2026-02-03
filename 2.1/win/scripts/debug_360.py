#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全局360度无死角调试系统

测试铁律：
- 严禁跳过任何测试
- 所有问题必须溯源到根本原因
- 不得使用timeout作为跳过理由
- 必须修复问题而非绕过问题
- 测试超时必须溯源修复（源文件问题或测试逻辑问题）

测试超时溯源规则：
测试超时只有两种原因：
1. 源文件有问题：死循环、性能问题、资源泄漏、阻塞操作
2. 测试逻辑有问题：无限等待、错误的mock、不合理的超时设置
发现超时必须立即定位并修复根本原因！
"""

import argparse
import io
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


class Debug360System:
    """360度调试系统"""

    def __init__(self, strict_mode: bool = True):
        """初始化调试系统"""
        self.strict_mode = strict_mode
        self.project_root = Path.cwd()
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 检测结果
        self.issues: Dict[str, List[Dict[str, Any]]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}

        self.coverage_data: Dict[str, float] = {}
        self.root_cause_analysis: List[Dict[str, Any]] = []

    def run_full_scan(self) -> bool:
        """运行完整扫描"""
        print("=" * 60)
        print("360度调试系统 - 完整扫描")
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"模式: {'严格模式' if self.strict_mode else '宽松模式'}")
        print("=" * 60)

        all_passed = True

        # 1. 代码质量检测
        print("\n[1/4] 代码质量检测...")
        if not self._check_code_quality():
            all_passed = False

        # 2. 测试覆盖率检测
        print("\n[2/4] 测试覆盖率检测...")
        if not self._check_test_coverage():
            all_passed = False

        # 3. 功能完整性检测
        print("\n[3/4] 功能完整性检测...")
        if not self._check_functionality():
            all_passed = False

        # 4. 性能检测
        print("\n[4/4] 性能检测...")
        if not self._check_performance():
            all_passed = False

        # 生成报告
        self._generate_report()

        # 显示摘要
        self._print_summary(all_passed)

        return all_passed

    def _check_code_quality(self) -> bool:
        """检测代码质量"""
        print("  运行质量门禁检查...")

        try:
            result = subprocess.run(
                ["python", "scripts/quality_gate.py", "src"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                check=False,
            )

            if result.returncode == 0:
                print("  [OK] 代码质量检测通过")
                return True

            print("  [FAIL] 代码质量检测失败")
            self.issues["HIGH"].append(
                {
                    "category": "代码质量",
                    "description": "质量门禁检测失败",
                    "details": result.stdout,
                    "root_cause": "代码存在质量问题",
                }
            )
            return False

        except subprocess.TimeoutExpired as e:
            print(f"  [FAIL] 代码质量检测超时: {e}")
            root_cause = self._trace_timeout_issue("代码质量检测", str(e))
            self.issues["CRITICAL"].append(
                {"category": "代码质量", "description": f"检测超时: {e}", "details": str(e), "root_cause": root_cause}
            )
            return False
        except OSError as e:
            print(f"  [FAIL] 代码质量检测异常: {e}")
            root_cause = self._trace_exception("代码质量检测", e)
            self.issues["CRITICAL"].append(
                {"category": "代码质量", "description": f"检测异常: {e}", "details": str(e), "root_cause": root_cause}
            )
            return False

    def _check_test_coverage(self) -> bool:
        """检测测试覆盖率 - 严禁跳过"""
        print("  检查测试覆盖率...")

        try:
            coverage_file = self.project_root / "coverage.json"

            if not coverage_file.exists():
                print("  [FAIL] 未找到覆盖率报告")
                root_cause = self._trace_missing_coverage_report()

                self.issues["CRITICAL"].append(
                    {
                        "category": "测试覆盖率",
                        "description": "缺少覆盖率报告",
                        "details": "必须运行: pytest --cov=src --cov-report=json",
                        "root_cause": root_cause,
                    }
                )
                return False

            with open(coverage_file, "r", encoding="utf-8") as f:
                coverage_data = json.load(f)

            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            self.coverage_data["total"] = total_coverage

            print(f"  总覆盖率: {total_coverage:.2f}%")

            if total_coverage >= 100.0:
                print("  [OK] 测试覆盖率达到100%")
                return True

            print(f"  [FAIL] 测试覆盖率不足: {total_coverage:.2f}%")
            self._trace_coverage_issues(coverage_data)

            self.issues["HIGH"].append(
                {
                    "category": "测试覆盖率",
                    "description": f"覆盖率未达到100%: {total_coverage:.2f}%",
                    "details": "需要补充测试用例",
                    "root_cause": "部分代码未被测试覆盖",
                }
            )
            return False

        except json.JSONDecodeError as e:
            print(f"  [FAIL] 覆盖率报告格式错误: {e}")
            self.issues["CRITICAL"].append(
                {
                    "category": "测试覆盖率",
                    "description": f"JSON解析错误: {e}",
                    "details": str(e),
                    "root_cause": "coverage.json格式错误",
                }
            )
            return False
        except OSError as e:
            print(f"  [FAIL] 测试覆盖率检测异常: {e}")
            root_cause = self._trace_exception("测试覆盖率检测", e)

            self.issues["CRITICAL"].append(
                {"category": "测试覆盖率", "description": f"检测异常: {e}", "details": str(e), "root_cause": root_cause}
            )
            return False

    def _trace_coverage_issues(self, coverage_data: Dict[str, Any]):
        """溯源覆盖率问题"""
        print("\n  [TRACE] 溯源覆盖率不足的根本原因:")

        files_data = coverage_data.get("files", {})
        low_coverage_files = []

        for file_path, file_data in files_data.items():
            file_coverage = file_data["summary"].get("percent_covered", 0)
            if file_coverage < 100:
                missing_lines = file_data.get("missing_lines", [])
                low_coverage_files.append(
                    {"path": file_path, "coverage": file_coverage, "missing_lines": missing_lines}
                )

        low_coverage_files.sort(key=lambda x: x["coverage"])

        print(f"  - 发现 {len(low_coverage_files)} 个文件覆盖率不足100%")

        for i, file_info in enumerate(low_coverage_files[:5], 1):
            print(f"  {i}. {file_info['path']}: {file_info['coverage']:.2f}%")
            if file_info["missing_lines"]:
                print(f"     未覆盖行: {file_info['missing_lines'][:10]}")

        self.root_cause_analysis.append(
            {
                "issue": "测试覆盖率不足",
                "root_cause": f"{len(low_coverage_files)}个文件未达到100%覆盖率",
                "affected_files": [f["path"] for f in low_coverage_files[:10]],
                "action_required": "为未覆盖的代码行添加测试用例",
            }
        )

    def _trace_missing_coverage_report(self) -> str:
        """溯源缺少覆盖率报告的原因"""
        print("\n  [TRACE] 溯源缺少覆盖率报告的根本原因:")

        test_dirs = [self.project_root / "tests" / "unit", self.project_root / "tests" / "integration"]

        test_file_count = 0
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files = list(test_dir.rglob("test_*.py"))
                test_file_count += len(test_files)
                print(f"  - {test_dir}: {len(test_files)} 个测试文件")

        if test_file_count == 0:
            root_cause = "没有测试文件"
            print(f"  [FAIL] 根本原因: {root_cause}")
        else:
            root_cause = f"有{test_file_count}个测试文件，但未运行覆盖率检测"
            print(f"  [WARN] 根本原因: {root_cause}")
            print("  [TIP] 解决方案: 运行 pytest --cov=src --cov-report=json")

        self.root_cause_analysis.append(
            {
                "issue": "缺少覆盖率报告",
                "root_cause": root_cause,
                "test_file_count": test_file_count,
                "action_required": "运行覆盖率检测命令",
            }
        )

        return root_cause

    def _trace_exception(self, context: str, exception: Exception) -> str:
        """溯源异常原因"""
        print(f"\n  [TRACE] 溯源 {context} 异常的根本原因:")

        exception_type = type(exception).__name__
        exception_msg = str(exception)

        print(f"  - 异常类型: {exception_type}")
        print(f"  - 异常消息: {exception_msg}")

        if "timeout" in exception_msg.lower():
            root_cause = self._trace_timeout_issue(context, exception_msg)
        elif "permission" in exception_msg.lower():
            root_cause = "权限不足 - 需要检查文件访问权限"
        elif "not found" in exception_msg.lower():
            root_cause = "文件或命令不存在 - 需要检查依赖安装"
        elif "import" in exception_msg.lower():
            root_cause = "导入错误 - 需要检查模块依赖"
        else:
            root_cause = f"{exception_type}: {exception_msg}"

        print(f"  [FAIL] 根本原因: {root_cause}")

        tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)

        self.root_cause_analysis.append(
            {
                "issue": f"{context}异常",
                "root_cause": root_cause,
                "exception_type": exception_type,
                "exception_message": exception_msg,
                "traceback": "".join(tb_lines[-3:]),
            }
        )

        return root_cause

    def _trace_timeout_issue(self, context: str, error_msg: str) -> str:
        """
        溯源测试超时问题 - 严禁跳过，必须修复

        测试超时只有两种原因：
        1. 源文件有问题：死循环、性能问题、资源泄漏、阻塞操作
        2. 测试逻辑有问题：无限等待、错误的mock、不合理的超时设置
        """
        print("\n  🚨 [TIMEOUT TRACE] 测试超时溯源分析（严禁跳过，必须修复）:")
        print("  " + "=" * 50)

        # 分析可能的原因
        source_file_issues = [
            "死循环 - while True 或递归无终止条件",
            "性能问题 - O(n²)或更差的算法复杂度",
            "资源泄漏 - 未关闭的文件句柄、数据库连接、网络连接",
            "阻塞操作 - 无超时的网络请求、数据库查询、文件I/O",
        ]

        test_logic_issues = [
            "无限等待 - await without timeout",
            "错误的mock - 未正确模拟异步操作或阻塞调用",
            "不合理的超时设置 - 超时时间太短或太长",
            "测试数据量过大 - 测试数据超出合理范围",
        ]

        print("\n  📋 可能的源文件问题:")
        for i, issue in enumerate(source_file_issues, 1):
            print(f"     {i}. {issue}")

        print("\n  📋 可能的测试逻辑问题:")
        for i, issue in enumerate(test_logic_issues, 1):
            print(f"     {i}. {issue}")

        print("\n  🔍 溯源步骤:")
        print("     1. 检查超时的具体测试函数")
        print("     2. 分析测试调用的源代码")
        print("     3. 检查是否有死循环或无限等待")
        print("     4. 检查mock是否正确设置")
        print("     5. 检查超时设置是否合理")

        print("\n  🚫 禁止的处理方式:")
        print("     ❌ 使用 @pytest.mark.skip 跳过超时测试")
        print("     ❌ 使用 @pytest.mark.timeout(0) 禁用超时")
        print("     ❌ 增加超时时间而不修复根本原因")
        print("     ❌ 删除超时测试")

        print("\n  ✅ 正确的处理方式:")
        print("     ✓ 定位超时的根本原因")
        print("     ✓ 修复源文件中的性能问题")
        print("     ✓ 修复测试逻辑中的等待问题")
        print("     ✓ 优化算法复杂度")
        print("     ✓ 添加合理的超时和重试机制")

        print("  " + "=" * 50)

        root_cause = "执行超时 - 必须溯源修复（源文件问题或测试逻辑问题）"

        self.root_cause_analysis.append(
            {
                "issue": "测试超时",
                "root_cause": root_cause,
                "context": context,
                "error_message": error_msg,
                "possible_source_issues": source_file_issues,
                "possible_test_issues": test_logic_issues,
                "action_required": "必须定位并修复超时的根本原因，严禁跳过",
                "forbidden_actions": [
                    "使用 @pytest.mark.skip 跳过",
                    "使用 @pytest.mark.timeout(0) 禁用超时",
                    "增加超时时间而不修复根本原因",
                    "删除超时测试",
                ],
            }
        )

        return root_cause

    def _check_functionality(self) -> bool:
        """检测功能完整性"""
        print("  检查功能完整性...")

        critical_files = ["PRD.md", "src/__init__.py", "tests/__init__.py", "requirements.txt"]

        missing_files = []
        for file_path in critical_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"  [FAIL] 缺少关键文件: {', '.join(missing_files)}")
            self.issues["HIGH"].append(
                {
                    "category": "功能完整性",
                    "description": "缺少关键文件",
                    "details": f"缺失文件: {', '.join(missing_files)}",
                    "root_cause": "项目结构不完整",
                }
            )
            return False

        print("  [OK] 功能完整性检测通过")
        return True

    def _check_performance(self) -> bool:
        """检测性能问题"""
        print("  检查性能指标...")

        try:
            perf_test_dir = self.project_root / "tests" / "performance"
            if not perf_test_dir.exists():
                print("  [FAIL] 未找到性能测试目录")

                root_cause = "项目缺少性能测试目录 tests/performance"
                print(f"\n  [TRACE] 根本原因: {root_cause}")

                self.issues["HIGH"].append(
                    {
                        "category": "性能检测",
                        "description": "缺少性能测试",
                        "details": "必须创建 tests/performance 目录并添加性能测试",
                        "root_cause": root_cause,
                    }
                )

                self.root_cause_analysis.append(
                    {"issue": "缺少性能测试", "root_cause": root_cause, "action_required": "创建性能测试目录和测试用例"}
                )

                return False

            perf_test_files = list(perf_test_dir.glob("test_*.py"))
            if not perf_test_files:
                print("  [FAIL] 性能测试目录为空")

                root_cause = "性能测试目录存在但没有测试文件"
                print(f"\n  [TRACE] 根本原因: {root_cause}")

                self.issues["HIGH"].append(
                    {
                        "category": "性能检测",
                        "description": "性能测试目录为空",
                        "details": "必须添加性能测试用例",
                        "root_cause": root_cause,
                    }
                )

                self.root_cause_analysis.append(
                    {"issue": "性能测试目录为空", "root_cause": root_cause, "action_required": "添加性能测试用例"}
                )

                return False

            print(f"  找到 {len(perf_test_files)} 个性能测试文件")
            print("  [OK] 性能检测通过")
            return True

        except OSError as e:
            print(f"  [FAIL] 性能检测异常: {e}")
            root_cause = self._trace_exception("性能检测", e)

            self.issues["HIGH"].append(
                {"category": "性能检测", "description": f"检测异常: {e}", "details": str(e), "root_cause": root_cause}
            )
            return False

    def _generate_report(self):
        """生成详细报告"""
        report_file = self.reports_dir / f"debug_360_{self.timestamp}.json"

        report_data = {
            "timestamp": self.timestamp,
            "mode": "strict" if self.strict_mode else "relaxed",
            "issues": self.issues,
            "coverage": self.coverage_data,
            "root_cause_analysis": self.root_cause_analysis,
            "summary": {
                "total_issues": sum(len(issues) for issues in self.issues.values()),
                "critical_issues": len(self.issues["CRITICAL"]),
                "high_issues": len(self.issues["HIGH"]),
                "medium_issues": len(self.issues["MEDIUM"]),
                "low_issues": len(self.issues["LOW"]),
                "root_causes_identified": len(self.root_cause_analysis),
            },
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n[REPORT] 详细报告已生成: {report_file}")

        # 生成Markdown报告
        self._generate_markdown_report(report_data)

    def _generate_markdown_report(self, report_data: Dict[str, Any]):
        """生成Markdown格式的可读报告"""
        md_file = self.reports_dir / f"debug_360_{self.timestamp}.md"

        lines = []
        lines.append("# 全局360度调试报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**检测模式**: {'严格模式' if self.strict_mode else '宽松模式'}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 摘要
        summary = report_data["summary"]
        lines.append("## 检测摘要")
        lines.append("")
        lines.append(f"- **总问题数**: {summary['total_issues']}")
        lines.append(f"- **CRITICAL**: {summary['critical_issues']}")
        lines.append(f"- **HIGH**: {summary['high_issues']}")
        lines.append(f"- **MEDIUM**: {summary['medium_issues']}")
        lines.append(f"- **LOW**: {summary['low_issues']}")
        lines.append(f"- **根本原因已识别**: {summary['root_causes_identified']}")
        lines.append("")

        if self.coverage_data:
            lines.append(f"- **测试覆盖率**: {self.coverage_data.get('total', 0):.2f}%")
            lines.append("")

        # 根本原因分析
        if self.root_cause_analysis:
            lines.append("---")
            lines.append("")
            lines.append("## 根本原因分析")
            lines.append("")

            for i, rca in enumerate(self.root_cause_analysis, 1):
                lines.append(f"### {i}. {rca['issue']}")
                lines.append("")
                lines.append(f"**根本原因**: {rca['root_cause']}")
                lines.append("")

                if "affected_files" in rca:
                    lines.append("**受影响文件**:")
                    for f in rca["affected_files"][:5]:
                        lines.append(f"- `{f}`")
                    lines.append("")

                if "action_required" in rca:
                    lines.append(f"**必要行动**: {rca['action_required']}")
                    lines.append("")

        # 详细问题列表
        lines.append("---")
        lines.append("")
        lines.append("## 详细问题列表")
        lines.append("")

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if self.issues[severity]:
                lines.append(f"### {severity}")
                lines.append("")

                for i, issue in enumerate(self.issues[severity], 1):
                    lines.append(f"#### {i}. [{issue['category']}] {issue['description']}")
                    lines.append("")
                    lines.append(f"**详情**: {issue['details']}")
                    lines.append("")

                    if "root_cause" in issue:
                        lines.append(f"**根本原因**: {issue['root_cause']}")
                        lines.append("")

        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"[FILE] Markdown报告已生成: {md_file}")

    def _print_summary(self, all_passed: bool):
        """打印摘要"""
        print("\n" + "=" * 60)
        print("检测摘要")
        print("=" * 60)

        total_issues = sum(len(issues) for issues in self.issues.values())

        print(f"总问题数: {total_issues}")
        print(f"  CRITICAL: {len(self.issues['CRITICAL'])}")
        print(f"  HIGH:     {len(self.issues['HIGH'])}")
        print(f"  MEDIUM:   {len(self.issues['MEDIUM'])}")
        print(f"  LOW:      {len(self.issues['LOW'])}")

        if self.coverage_data:
            print(f"\n测试覆盖率: {self.coverage_data.get('total', 0):.2f}%")

        if self.root_cause_analysis:
            print(f"\n根本原因已识别: {len(self.root_cause_analysis)} 个")

        print("\n" + "=" * 60)
        if all_passed:
            print("[OK] 全局360度调试检测通过")
        else:
            print("[FAIL] 全局360度调试检测失败")
        print("=" * 60)

        # 显示详细问题和根本原因
        if total_issues > 0:
            print("\n问题详情:")
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                if self.issues[severity]:
                    print(f"\n{severity}:")
                    for i, issue in enumerate(self.issues[severity], 1):
                        print(f"  {i}. [{issue['category']}] {issue['description']}")
                        if "root_cause" in issue:
                            print(f"     [TRACE] 根本原因: {issue['root_cause']}")

        # 显示根本原因分析摘要
        if self.root_cause_analysis:
            print("\n" + "=" * 60)
            print("根本原因分析摘要")
            print("=" * 60)
            for i, rca in enumerate(self.root_cause_analysis, 1):
                print(f"{i}. {rca['issue']}")
                print(f"   根本原因: {rca['root_cause']}")
                if "action_required" in rca:
                    print(f"   必要行动: {rca['action_required']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="全局360度无死角调试系统")

    parser.add_argument("--full", action="store_true", help="运行完整扫描")

    parser.add_argument("--strict", action="store_true", default=True, help="严格模式（默认）")

    parser.add_argument("--relaxed", action="store_true", help="宽松模式")

    args = parser.parse_args()

    # 确定模式
    strict_mode = not args.relaxed

    # 创建调试系统
    debug_system = Debug360System(strict_mode=strict_mode)

    # 执行扫描
    success = debug_system.run_full_scan()

    # 返回状态码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
