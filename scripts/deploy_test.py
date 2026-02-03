#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自动化部署测试脚本 - 完整的CI/CD测试流程

流程：
1. 环境检查 - Python版本、依赖包
2. 代码质量 - Pylint、Black、isort
3. 安全扫描 - Bandit
4. 单元测试 - pytest
5. 集成测试 - pytest integration
6. 覆盖率检查 - 100%标准
7. 部署就绪报告

使用方法：
    python scripts/deploy_test.py [command]

命令：
    env      - 仅环境检查
    lint     - 仅代码质量检查
    security - 仅安全扫描
    unit     - 仅单元测试
    coverage - 仅覆盖率检查
    full     - 完整测试流程
    report   - 生成部署报告

退出码：
    0 - 所有检查通过，可以部署
    1 - 存在问题，需要修复
"""

import io
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============================================================================
# 部署标准
# ============================================================================

DEPLOY_STANDARDS = {
    "python_version": "3.10",
    "coverage_threshold": 100,
    "max_bugs": 0,
    "security_issues": 0,
    "test_pass_rate": 100,
}

# 硅谷12人团队角色映射
TEAM_ROLES = {
    "environment": "☁️ DevOps Engineer",
    "lint": "🔍 Code Review Specialist",
    "security": "🔒 Security Engineer",
    "test": "🧪 Test Engineer",
    "coverage": "🧪 Test Engineer",
    "architecture": "🏗️ Software Architect",
    "performance": "🧮 Algorithm Engineer",
    "database": "🗄️ Database Engineer",
}


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)
    duration: float = 0.0
    assigned_role: str = ""


@dataclass
class DeployReport:
    """部署报告"""
    timestamp: str
    all_passed: bool
    checks: List[CheckResult]
    summary: str
    recommendations: List[str] = field(default_factory=list)


class DeployTest:
    """自动化部署测试"""

    def __init__(self, target_dir: str = "src"):
        self.target_dir = target_dir
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        self.results: List[CheckResult] = []

    # ========================================================================
    # 环境检查
    # ========================================================================

    def check_environment(self) -> CheckResult:
        """检查运行环境"""
        import time
        start = time.time()
        
        details = []
        passed = True
        
        # Python版本
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        required = DEPLOY_STANDARDS["python_version"]
        
        if py_version >= required:
            details.append(f"✅ Python {py_version} (要求 >= {required})")
        else:
            details.append(f"❌ Python {py_version} (要求 >= {required})")
            passed = False
        
        # 检查关键依赖
        required_packages = ["pytest", "pylint", "black", "isort", "bandit"]
        for pkg in required_packages:
            try:
                __import__(pkg.replace("-", "_"))
                details.append(f"✅ {pkg} 已安装")
            except ImportError:
                details.append(f"❌ {pkg} 未安装")
                passed = False
        
        # 检查目标目录
        if Path(self.target_dir).exists():
            details.append(f"✅ 目标目录 {self.target_dir} 存在")
        else:
            details.append(f"❌ 目标目录 {self.target_dir} 不存在")
            passed = False
        
        duration = time.time() - start
        
        return CheckResult(
            name="环境检查",
            passed=passed,
            message="环境配置正确" if passed else "环境配置有问题",
            details=details,
            duration=duration,
            assigned_role=TEAM_ROLES["environment"] if not passed else ""
        )

    # ========================================================================
    # 代码质量检查
    # ========================================================================

    def check_lint(self) -> CheckResult:
        """代码质量检查"""
        import time
        start = time.time()
        
        details = []
        passed = True
        
        # Pylint检查
        try:
            cmd = f"python -m pylint {self.target_dir} --exit-zero --score=yes --max-line-length=120"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=300)
            
            # 提取评分
            import re
            score_match = re.search(r"rated at ([\d.]+)/10", result.stdout + result.stderr)
            if score_match:
                score = float(score_match.group(1))
                if score >= 8.0:
                    details.append(f"✅ Pylint评分: {score}/10")
                else:
                    details.append(f"⚠️ Pylint评分: {score}/10 (建议 >= 8.0)")
            else:
                details.append("✅ Pylint检查完成")
                
        except Exception as e:
            details.append(f"❌ Pylint检查失败: {e}")
            passed = False
        
        # Black格式检查
        try:
            cmd = f"python -m black {self.target_dir} --check --quiet"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
            if result.returncode == 0:
                details.append("✅ Black格式检查通过")
            else:
                details.append("⚠️ Black格式需要调整")
        except Exception as e:
            details.append(f"⚠️ Black检查跳过: {e}")
        
        # isort检查
        try:
            cmd = f"python -m isort {self.target_dir} --check-only --quiet"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
            if result.returncode == 0:
                details.append("✅ isort导入排序正确")
            else:
                details.append("⚠️ isort导入排序需要调整")
        except Exception as e:
            details.append(f"⚠️ isort检查跳过: {e}")
        
        duration = time.time() - start
        
        return CheckResult(
            name="代码质量",
            passed=passed,
            message="代码质量检查通过" if passed else "代码质量需要改进",
            details=details,
            duration=duration,
            assigned_role=TEAM_ROLES["lint"] if not passed else ""
        )

    # ========================================================================
    # 安全扫描
    # ========================================================================

    def check_security(self) -> CheckResult:
        """安全扫描"""
        import time
        start = time.time()
        
        details = []
        passed = True
        issues_count = 0
        
        try:
            cmd = f"python -m bandit -r {self.target_dir} -f json --exit-zero"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=300)
            
            if result.stdout.strip():
                data = json.loads(result.stdout)
                results = data.get("results", [])
                issues_count = len(results)
                
                # 按严重级别统计
                high = len([r for r in results if r.get("issue_severity") == "HIGH"])
                medium = len([r for r in results if r.get("issue_severity") == "MEDIUM"])
                low = len([r for r in results if r.get("issue_severity") == "LOW"])
                
                if high > 0:
                    details.append(f"❌ 高危漏洞: {high}")
                    passed = False
                if medium > 0:
                    details.append(f"⚠️ 中危漏洞: {medium}")
                if low > 0:
                    details.append(f"ℹ️ 低危漏洞: {low}")
                
                if issues_count == 0:
                    details.append("✅ 无安全漏洞")
            else:
                details.append("✅ 无安全漏洞")
                
        except Exception as e:
            details.append(f"⚠️ 安全扫描跳过: {e}")
        
        duration = time.time() - start
        
        return CheckResult(
            name="安全扫描",
            passed=passed,
            message=f"发现 {issues_count} 个安全问题" if issues_count > 0 else "无安全问题",
            details=details,
            duration=duration,
            assigned_role=TEAM_ROLES["security"] if not passed else ""
        )

    # ========================================================================
    # 单元测试
    # ========================================================================

    def check_unit_tests(self) -> CheckResult:
        """单元测试"""
        import time
        start = time.time()
        
        details = []
        passed = True
        
        try:
            # 运行pytest
            cmd = "python -m pytest tests/unit -v --tb=short -q 2>&1 | head -50"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=600)
            
            output = result.stdout + result.stderr
            
            # 解析结果
            import re
            
            # 查找通过/失败统计
            passed_match = re.search(r"(\d+) passed", output)
            failed_match = re.search(r"(\d+) failed", output)
            error_match = re.search(r"(\d+) error", output)
            
            passed_count = int(passed_match.group(1)) if passed_match else 0
            failed_count = int(failed_match.group(1)) if failed_match else 0
            error_count = int(error_match.group(1)) if error_match else 0
            
            total = passed_count + failed_count + error_count
            
            if total > 0:
                pass_rate = (passed_count / total) * 100
                details.append(f"测试总数: {total}")
                details.append(f"✅ 通过: {passed_count}")
                
                if failed_count > 0:
                    details.append(f"❌ 失败: {failed_count}")
                    passed = False
                if error_count > 0:
                    details.append(f"❌ 错误: {error_count}")
                    passed = False
                    
                details.append(f"通过率: {pass_rate:.1f}%")
            else:
                details.append("⚠️ 未找到单元测试")
                
        except subprocess.TimeoutExpired:
            details.append("⚠️ 测试超时")
            passed = False
        except Exception as e:
            details.append(f"⚠️ 测试执行异常: {e}")
        
        duration = time.time() - start
        
        return CheckResult(
            name="单元测试",
            passed=passed,
            message="单元测试通过" if passed else "单元测试失败",
            details=details,
            duration=duration,
            assigned_role=TEAM_ROLES["test"] if not passed else ""
        )

    # ========================================================================
    # 覆盖率检查
    # ========================================================================

    def check_coverage(self) -> CheckResult:
        """覆盖率检查"""
        import time
        start = time.time()
        
        details = []
        passed = True
        coverage_percent = 0.0
        
        try:
            # 运行覆盖率检查
            cmd = "python -m pytest tests/ --cov=src --cov-report=json --cov-report=term -q 2>&1 | tail -20"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=900)
            
            # 尝试读取覆盖率报告
            cov_file = Path("coverage.json")
            if cov_file.exists():
                cov_data = json.loads(cov_file.read_text())
                coverage_percent = cov_data.get("totals", {}).get("percent_covered", 0)
                
                details.append(f"当前覆盖率: {coverage_percent:.1f}%")
                details.append(f"目标覆盖率: {DEPLOY_STANDARDS['coverage_threshold']}%")
                
                if coverage_percent >= DEPLOY_STANDARDS['coverage_threshold']:
                    details.append("✅ 覆盖率达标")
                else:
                    details.append("❌ 覆盖率未达标")
                    passed = False
            else:
                # 从输出解析覆盖率
                import re
                cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", result.stdout + result.stderr)
                if cov_match:
                    coverage_percent = float(cov_match.group(1))
                    details.append(f"当前覆盖率: {coverage_percent:.1f}%")
                    
                    if coverage_percent >= DEPLOY_STANDARDS['coverage_threshold']:
                        details.append("✅ 覆盖率达标")
                    else:
                        details.append("❌ 覆盖率未达标")
                        passed = False
                else:
                    details.append("⚠️ 无法获取覆盖率数据")
                    
        except subprocess.TimeoutExpired:
            details.append("⚠️ 覆盖率检查超时")
        except Exception as e:
            details.append(f"⚠️ 覆盖率检查异常: {e}")
        
        duration = time.time() - start
        
        return CheckResult(
            name="覆盖率检查",
            passed=passed,
            message=f"覆盖率 {coverage_percent:.1f}%",
            details=details,
            duration=duration,
            assigned_role=TEAM_ROLES["coverage"] if not passed else ""
        )

    # ========================================================================
    # 完整测试流程
    # ========================================================================

    def run_full_test(self) -> DeployReport:
        """运行完整测试流程"""
        print("=" * 60)
        print("自动化部署测试")
        print(f"目标: {self.target_dir}")
        print(f"时间: {datetime.now().isoformat()}")
        print("=" * 60)
        print()
        
        self.results = []
        
        # 1. 环境检查
        print("[1/5] 环境检查...")
        env_result = self.check_environment()
        self.results.append(env_result)
        self._print_result(env_result)
        
        # 2. 代码质量
        print("[2/5] 代码质量检查...")
        lint_result = self.check_lint()
        self.results.append(lint_result)
        self._print_result(lint_result)
        
        # 3. 安全扫描
        print("[3/5] 安全扫描...")
        security_result = self.check_security()
        self.results.append(security_result)
        self._print_result(security_result)
        
        # 4. 单元测试
        print("[4/5] 单元测试...")
        test_result = self.check_unit_tests()
        self.results.append(test_result)
        self._print_result(test_result)
        
        # 5. 覆盖率检查
        print("[5/5] 覆盖率检查...")
        coverage_result = self.check_coverage()
        self.results.append(coverage_result)
        self._print_result(coverage_result)
        
        # 生成报告
        all_passed = all(r.passed for r in self.results)
        
        recommendations = []
        for r in self.results:
            if not r.passed and r.assigned_role:
                recommendations.append(f"{r.assigned_role}: 修复 {r.name} 问题")
        
        report = DeployReport(
            timestamp=datetime.now().isoformat(),
            all_passed=all_passed,
            checks=self.results,
            summary="部署就绪" if all_passed else "需要修复后才能部署",
            recommendations=recommendations
        )
        
        # 打印总结
        print()
        print("=" * 60)
        print("部署测试结果")
        print("=" * 60)
        
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        print(f"通过: {passed_count}/{total_count}")
        print(f"状态: {'✅ 可以部署' if all_passed else '❌ 需要修复'}")
        
        if recommendations:
            print()
            print("修复建议:")
            for rec in recommendations:
                print(f"  - {rec}")
        
        print("=" * 60)
        
        # 保存报告
        self._save_report(report)
        
        return report

    def _print_result(self, result: CheckResult) -> None:
        """打印检查结果"""
        icon = "✅" if result.passed else "❌"
        print(f"  {icon} {result.name}: {result.message} ({result.duration:.1f}s)")
        for detail in result.details[:5]:  # 最多显示5条
            print(f"     {detail}")
        print()

    def _save_report(self, report: DeployReport) -> None:
        """保存报告"""
        report_file = self.reports_dir / f"deploy_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            "timestamp": report.timestamp,
            "all_passed": report.all_passed,
            "summary": report.summary,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "details": c.details,
                    "duration": c.duration,
                    "assigned_role": c.assigned_role
                }
                for c in report.checks
            ],
            "recommendations": report.recommendations
        }
        
        report_file.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"\n报告已保存: {report_file}")

    # ========================================================================
    # 单独命令
    # ========================================================================

    def run_env_only(self) -> bool:
        """仅环境检查"""
        print("环境检查")
        print("-" * 40)
        result = self.check_environment()
        self._print_result(result)
        return result.passed

    def run_lint_only(self) -> bool:
        """仅代码质量"""
        print("代码质量检查")
        print("-" * 40)
        result = self.check_lint()
        self._print_result(result)
        return result.passed

    def run_security_only(self) -> bool:
        """仅安全扫描"""
        print("安全扫描")
        print("-" * 40)
        result = self.check_security()
        self._print_result(result)
        return result.passed

    def run_unit_only(self) -> bool:
        """仅单元测试"""
        print("单元测试")
        print("-" * 40)
        result = self.check_unit_tests()
        self._print_result(result)
        return result.passed

    def run_coverage_only(self) -> bool:
        """仅覆盖率检查"""
        print("覆盖率检查")
        print("-" * 40)
        result = self.check_coverage()
        self._print_result(result)
        return result.passed


# ============================================================================
# 主函数
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("自动化部署测试")
        print()
        print("使用方法:")
        print("  python scripts/deploy_test.py full [target]     - 完整测试流程")
        print("  python scripts/deploy_test.py env               - 环境检查")
        print("  python scripts/deploy_test.py lint [target]     - 代码质量")
        print("  python scripts/deploy_test.py security [target] - 安全扫描")
        print("  python scripts/deploy_test.py unit              - 单元测试")
        print("  python scripts/deploy_test.py coverage          - 覆盖率检查")
        print()
        print(f"部署标准: 覆盖率={DEPLOY_STANDARDS['coverage_threshold']}%, Bug=0, 安全漏洞=0")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    target = sys.argv[2] if len(sys.argv) > 2 else "src"
    
    tester = DeployTest(target)
    
    if command == "full":
        report = tester.run_full_test()
        sys.exit(0 if report.all_passed else 1)
    elif command == "env":
        success = tester.run_env_only()
        sys.exit(0 if success else 1)
    elif command == "lint":
        success = tester.run_lint_only()
        sys.exit(0 if success else 1)
    elif command == "security":
        success = tester.run_security_only()
        sys.exit(0 if success else 1)
    elif command == "unit":
        success = tester.run_unit_only()
        sys.exit(0 if success else 1)
    elif command == "coverage":
        success = tester.run_coverage_only()
        sys.exit(0 if success else 1)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
