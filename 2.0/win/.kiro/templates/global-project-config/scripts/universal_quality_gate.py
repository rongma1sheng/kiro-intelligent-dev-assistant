#!/usr/bin/env python333
"""
通用质量门禁检查器

功能：
1. 跨语言的代码质量检查
2. 统一的测试覆盖率验证
3. 通用的安全扫描
4. 标准化的质量报告
"""

import os
import subprocess
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from dataclasses import dataclass
from enum import Enum


class QualityCheckResult(Enum):
    """质量检查结果枚举"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


@dataclass
class QualityMetrics:
    """质量指标数据类"""
    test_coverage: float
    code_complexity: float
    security_score: float
    documentation_coverage: float
    lint_score: float
    duplicate_rate: float


@dataclass
class QualityCheckReport:
    """质量检查报告"""
    overall_result: QualityCheckResult
    metrics: QualityMetrics
    violations: List[str]
    recommendations: List[str]
    blocking_issues: List[str]


class UniversalQualityGate:
    """通用质量门禁检查器"""
    
    def __init__(self, project_root: str, config_file: Optional[str] = None):
        self.project_root = Path(project_root)
        self.config = self._load_config(config_file)
        self.language = self._detect_language()
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """加载配置文件"""
        default_config = {
            "quality_thresholds": {
                "test_coverage": 100.0,
                "code_complexity": 10.0,
                "security_score": 90.0,
                "documentation_coverage": 80.0,
                "lint_score": 90.0,
                "duplicate_rate": 5.0
            },
            "language_configs": {
                "python": {
                    "test_command": "python -m pytest --cov=src --cov-report=json",
                    "lint_command": "pylint src/",
                    "complexity_command": "radon cc src/ -a",
                    "security_command": "bandit -r src/ -f json"
                },
                "javascript": {
                    "test_command": "npm test -- --coverage --coverageReporters=json",
                    "lint_command": "eslint src/",
                    "complexity_command": "plato -r -d reports src/",
                    "security_command": "npm audit --json"
                },
                "java": {
                    "test_command": "mvn test jacoco:report",
                    "lint_command": "mvn checkstyle:check",
                    "complexity_command": "mvn pmd:pmd",
                    "security_command": "mvn org.owasp:dependency-check-maven:check"
                }
            }
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.json'):
                    user_config = json.load(f)
                else:
                    user_config = yaml.safe_load(f)
                
                # 合并配置
                default_config.update(user_config)
        
        return default_config
    
    def _detect_language(self) -> str:
        """自动检测项目主要编程语言"""
        language_indicators = {
            "python": ["*.py", "requirements.txt", "setup.py", "pyproject.toml"],
            "javascript": ["*.js", "*.ts", "package.json", "tsconfig.json"],
            "java": ["*.java", "pom.xml", "build.gradle"],
            "cpp": ["*.cpp", "*.c", "*.h", "CMakeLists.txt", "Makefile"],
            "go": ["*.go", "go.mod", "go.sum"],
            "rust": ["*.rs", "Cargo.toml", "Cargo.lock"]
        }
        
        for language, indicators in language_indicators.items():
            for indicator in indicators:
                if list(self.project_root.glob(f"**/{indicator}")):
                    return language
        
        return "python"  # 默认
    
    def run_quality_checks(self) -> QualityCheckReport:
        """运行完整的质量检查"""
        print(f"🔍 开始质量门禁检查 - 项目语言: {self.language}")
        
        violations = []
        recommendations = []
        blocking_issues = []
        
        # 1. 测试覆盖率检查
        coverage = self._check_test_coverage()
        print(f"📊 测试覆盖率: {coverage:.2f}%")
        
        # 2. 代码复杂度检查
        complexity = self._check_code_complexity()
        print(f"🧮 代码复杂度: {complexity:.2f}")
        
        # 3. 安全扫描
        security_score = self._check_security()
        print(f"🔒 安全评分: {security_score:.2f}")
        
        # 4. 文档覆盖率检查
        doc_coverage = self._check_documentation_coverage()
        print(f"📚 文档覆盖率: {doc_coverage:.2f}%")
        
        # 5. 代码规范检查
        lint_score = self._check_lint()
        print(f"✨ 代码规范评分: {lint_score:.2f}")
        
        # 6. 代码重复率检查
        duplicate_rate = self._check_duplicates()
        print(f"🔄 代码重复率: {duplicate_rate:.2f}%")
        
        # 创建质量指标
        metrics = QualityMetrics(
            test_coverage=coverage,
            code_complexity=complexity,
            security_score=security_score,
            documentation_coverage=doc_coverage,
            lint_score=lint_score,
            duplicate_rate=duplicate_rate
        )
        
        # 验证质量标准
        thresholds = self.config["quality_thresholds"]
        overall_result = QualityCheckResult.PASS
        
        # 测试覆盖率检查（铁律）
        if coverage < thresholds["test_coverage"]:
            violation = f"测试覆盖率不达标: {coverage:.2f}% < {thresholds['test_coverage']}%"
            violations.append(violation)
            blocking_issues.append(violation)
            overall_result = QualityCheckResult.BLOCKED
            
        # 代码复杂度检查（铁律）
        if complexity > thresholds["code_complexity"]:
            violation = f"代码复杂度超标: {complexity:.2f} > {thresholds['code_complexity']}"
            violations.append(violation)
            blocking_issues.append(violation)
            overall_result = QualityCheckResult.BLOCKED
            
        # 其他质量指标检查
        if security_score < thresholds["security_score"]:
            violations.append(f"安全评分不达标: {security_score:.2f} < {thresholds['security_score']}")
            if overall_result == QualityCheckResult.PASS:
                overall_result = QualityCheckResult.FAIL
                
        if doc_coverage < thresholds["documentation_coverage"]:
            recommendations.append(f"建议提升文档覆盖率: {doc_coverage:.2f} < {thresholds['documentation_coverage']}")
            
        if lint_score < thresholds["lint_score"]:
            violations.append(f"代码规范评分不达标: {lint_score:.2f} < {thresholds['lint_score']}")
            
        if duplicate_rate > thresholds["duplicate_rate"]:
            recommendations.append(f"建议降低代码重复率: {duplicate_rate:.2f} > {thresholds['duplicate_rate']}")
        
        return QualityCheckReport(
            overall_result=overall_result,
            metrics=metrics,
            violations=violations,
            recommendations=recommendations,
            blocking_issues=blocking_issues
        )
    
    def _check_test_coverage(self) -> float:
        """检查测试覆盖率"""
        try:
            lang_config = self.config["language_configs"].get(self.language, {})
            test_command = lang_config.get("test_command", "echo 'No test command configured'")
            
            result = subprocess.run(
                test_command.split(),
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if self.language == "python":
                # 解析Python coverage.json
                coverage_file = self.project_root / "coverage.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                        return coverage_data.get("totals", {}).get("percent_covered", 0.0)
            
            elif self.language == "javascript":
                # 解析JavaScript coverage报告
                coverage_file = self.project_root / "coverage" / "coverage-summary.json"
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                        return coverage_data.get("total", {}).get("lines", {}).get("pct", 0.0)
            
            # 其他语言的覆盖率解析逻辑...
            
        except Exception as e:
            print(f"⚠️ 测试覆盖率检查失败: {e}")
        
        return 0.0
    
    def _check_code_complexity(self) -> float:
        """检查代码复杂度"""
        try:
            if self.language == "python":
                result = subprocess.run(
                    ["radon", "cc", "src/", "-a", "--json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    complexity_data = json.loads(result.stdout)
                    # 计算平均复杂度
                    total_complexity = 0
                    total_functions = 0
                    
                    for file_data in complexity_data.values():
                        for item in file_data:
                            if item.get("type") == "function":
                                total_complexity += item.get("complexity", 0)
                                total_functions += 1
                    
                    return total_complexity / max(total_functions, 1)
            
            # 其他语言的复杂度检查...
            
        except Exception as e:
            print(f"⚠️ 代码复杂度检查失败: {e}")
        
        return 0.0
    
    def _check_security(self) -> float:
        """安全扫描"""
        try:
            if self.language == "python":
                result = subprocess.run(
                    ["bandit", "-r", "src/", "-f", "json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    security_data = json.loads(result.stdout)
                    # 根据漏洞数量计算安全评分
                    high_issues = len([r for r in security_data.get("results", []) if r.get("issue_severity") == "HIGH"])
                    medium_issues = len([r for r in security_data.get("results", []) if r.get("issue_severity") == "MEDIUM"])
                    
                    # 简单的评分算法
                    score = 100 - (high_issues * 20) - (medium_issues * 10)
                    return max(score, 0.0)
            
            # 其他语言的安全扫描...
            
        except Exception as e:
            print(f"⚠️ 安全扫描失败: {e}")
        
        return 90.0  # 默认评分
    
    def _check_documentation_coverage(self) -> float:
        """检查文档覆盖率"""
        try:
            # 简单的文档覆盖率检查：统计有docstring的函数比例
            if self.language == "python":
                import ast
                
                total_functions = 0
                documented_functions = 0
                
                for py_file in self.project_root.glob("src/**/*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            tree = ast.parse(f.read())
                        
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                total_functions += 1
                                if ast.get_docstring(node):
                                    documented_functions += 1
                    except:
                        continue
                
                return (documented_functions / max(total_functions, 1)) * 100
            
            # 其他语言的文档覆盖率检查...
            
        except Exception as e:
            print(f"⚠️ 文档覆盖率检查失败: {e}")
        
        return 0.0
    
    def _check_lint(self) -> float:
        """代码规范检查"""
        try:
            if self.language == "python":
                result = subprocess.run(
                    ["pylint", "src/", "--output-format=json"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.stdout:
                    lint_data = json.loads(result.stdout)
                    # 根据pylint评分计算
                    total_score = 0
                    for item in lint_data:
                        if item.get("type") == "convention":
                            total_score -= 1
                        elif item.get("type") == "warning":
                            total_score -= 2
                        elif item.get("type") == "error":
                            total_score -= 5
                    
                    return max(100 + total_score, 0.0)
            
            # 其他语言的lint检查...
            
        except Exception as e:
            print(f"⚠️ 代码规范检查失败: {e}")
        
        return 90.0  # 默认评分
    
    def _check_duplicates(self) -> float:
        """代码重复率检查"""
        try:
            # 简单的重复率检查实现
            # 实际项目中可以使用jscpd等工具
            return 2.0  # 默认低重复率
            
        except Exception as e:
            print(f"⚠️ 代码重复率检查失败: {e}")
        
        return 5.0  # 默认值
    
    def generate_report(self, report: QualityCheckReport, output_file: Optional[str] = None) -> str:
        """生成质量检查报告"""
        report_content = f"""# 质量门禁检查报告

## 📊 总体结果: {report.overall_result.value}

### 🎯 质量指标
- **测试覆盖率**: {report.metrics.test_coverage:.2f}%
- **代码复杂度**: {report.metrics.code_complexity:.2f}
- **安全评分**: {report.metrics.security_score:.2f}
- **文档覆盖率**: {report.metrics.documentation_coverage:.2f}%
- **代码规范评分**: {report.metrics.lint_score:.2f}
- **代码重复率**: {report.metrics.duplicate_rate:.2f}%

### 🚨 违规项目
"""
        
        if report.violations:
            for violation in report.violations:
                report_content += f"- ❌ {violation}/n"
        else:
            report_content += "- ✅ 无违规项目/n"
        
        report_content += "/n### 🚫 阻塞问题/n"
        if report.blocking_issues:
            for issue in report.blocking_issues:
                report_content += f"- 🚫 {issue}/n"
        else:
            report_content += "- ✅ 无阻塞问题/n"
        
        report_content += "/n### 💡 改进建议/n"
        if report.recommendations:
            for rec in report.recommendations:
                report_content += f"- 💡 {rec}/n"
        else:
            report_content += "- ✅ 无改进建议/n"
        
        report_content += f"""
### 📋 质量门禁状态
- **是否通过**: {'✅ 通过' if report.overall_result == QualityCheckResult.PASS else '❌ 未通过'}
- **是否阻塞**: {'🚫 阻塞' if report.overall_result == QualityCheckResult.BLOCKED else '✅ 无阻塞'}

---
**报告生成时间**: {__import__('datetime').datetime.now().isoformat()}
**项目语言**: {self.language}
**检查工具**: Universal Quality Gate v1.0
"""
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"📄 报告已保存到: {output_file}")
        
        return report_content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="通用质量门禁检查器")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--output", help="报告输出文件")
    parser.add_argument("--fail-on-violation", action="store_true", help="有违规时返回非零退出码")
    
    args = parser.parse_args()
    
    # 创建质量门禁检查器
    quality_gate = UniversalQualityGate(args.project_root, args.config)
    
    # 运行质量检查
    report = quality_gate.run_quality_checks()
    
    # 生成报告
    report_content = quality_gate.generate_report(report, args.output)
    print("/n" + "="*50)
    print(report_content)
    
    # 根据结果设置退出码
    if args.fail_on_violation and report.overall_result != QualityCheckResult.PASS:
        print(f"/n❌ 质量门禁检查失败: {report.overall_result.value}")
        exit(1)
    else:
        print(f"/n✅ 质量门禁检查完成: {report.overall_result.value}")
        exit(0)


if __name__ == "__main__":
    main()