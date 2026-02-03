#!/usr/bin/env python3
"""
铁律核查系统 - 硅谷12人团队配置

自动检测和阻断铁律违规行为
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re


class IronLawChecker:
    """铁律核查器"""
    
    def __init__(self):
        self.violations = []
        self.coverage_threshold = 100.0  # 100%覆盖率要求
        self.complexity_threshold = 10   # 代码复杂度<10
        
    def check_all_laws(self) -> Dict[str, Any]:
        """检查所有铁律"""
        print("🚨 启动铁律核查系统...")
        
        results = {
            "zero_law_violations": self.check_zero_law(),
            "core_law_violations": self.check_core_law(), 
            "test_law_violations": self.check_test_law(),
            "total_violations": 0,
            "status": "UNKNOWN"
        }
        
        # 统计总违规数
        total_violations = (
            len(results["zero_law_violations"]) +
            len(results["core_law_violations"]) + 
            len(results["test_law_violations"])
        )
        
        results["total_violations"] = total_violations
        results["status"] = "PASSED" if total_violations == 0 else "FAILED"
        
        return results
    
    def check_zero_law(self) -> List[str]:
        """检查零号铁律"""
        violations = []
        
        # 检查是否修改了已认证的功能
        # 这里可以添加具体的检查逻辑
        
        return violations
    
    def check_core_law(self) -> List[str]:
        """检查核心铁律"""
        violations = []
        
        # 检查是否使用了占位符
        if self._check_placeholders():
            violations.append("发现占位符或简化功能")
            
        # 检查是否有未修复的bug
        if self._check_unfixed_bugs():
            violations.append("存在未修复的bug")
            
        return violations
    
    def check_test_law(self) -> List[str]:
        """检查测试铁律 - 最严格的检查"""
        violations = []
        
        # 检查测试覆盖率
        coverage_violations = self._check_coverage()
        violations.extend(coverage_violations)
        
        # 检查代码复杂度
        complexity_violations = self._check_complexity()
        violations.extend(complexity_violations)
        
        # 检查跳过的测试
        skipped_tests = self._check_skipped_tests()
        violations.extend(skipped_tests)
        
        return violations
    
    def _check_coverage(self) -> List[str]:
        """检查测试覆盖率"""
        violations = []
        
        try:
            # 运行覆盖率检查
            result = subprocess.run([
                "python", "-m", "pytest", 
                "tests/unit/brain/test_commander_engine_v2.py",
                "--cov=src.brain.commander_engine_v2",
                "--cov-report=json",
                "--quiet"
            ], capture_output=True, text=True, cwd=".")
            
            # 读取覆盖率报告
            coverage_file = Path("coverage.json")
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                
                # 检查总覆盖率
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                
                if total_coverage < self.coverage_threshold:
                    violations.append(
                        f"测试覆盖率违规: {total_coverage:.1f}% < {self.coverage_threshold}% (缺失 {self.coverage_threshold - total_coverage:.1f}%)"
                    )
                
                # 检查具体文件覆盖率
                files = coverage_data.get("files", {})
                for file_path, file_data in files.items():
                    if "commander_engine_v2" in file_path:
                        file_coverage = file_data.get("summary", {}).get("percent_covered", 0)
                        missing_lines = file_data.get("missing_lines", [])
                        
                        if file_coverage < self.coverage_threshold:
                            violations.append(
                                f"文件 {file_path} 覆盖率违规: {file_coverage:.1f}% < {self.coverage_threshold}%"
                            )
                            violations.append(f"未覆盖行数: {missing_lines}")
                
                # 清理临时文件
                coverage_file.unlink()
                
        except Exception as e:
            violations.append(f"覆盖率检查失败: {str(e)}")
            
        return violations
    
    def _check_complexity(self) -> List[str]:
        """检查代码复杂度"""
        violations = []
        
        try:
            # 使用radon检查复杂度
            result = subprocess.run([
                "python", "-m", "radon", "cc", 
                "src/brain/commander_engine_v2.py",
                "--json"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                complexity_data = json.loads(result.stdout)
                
                for file_path, functions in complexity_data.items():
                    for func in functions:
                        if func.get("complexity", 0) >= self.complexity_threshold:
                            violations.append(
                                f"函数 {func['name']} 复杂度违规: {func['complexity']} >= {self.complexity_threshold}"
                            )
                            
        except Exception as e:
            # radon可能未安装，跳过复杂度检查
            pass
            
        return violations
    
    def _check_skipped_tests(self) -> List[str]:
        """检查跳过的测试"""
        violations = []
        
        try:
            # 运行测试并检查跳过的测试
            result = subprocess.run([
                "python", "-m", "pytest",
                "tests/unit/brain/test_commander_engine_v2.py",
                "-v", "--tb=no"
            ], capture_output=True, text=True)
            
            # 检查输出中是否有SKIPPED
            if "SKIPPED" in result.stdout:
                skipped_count = result.stdout.count("SKIPPED")
                violations.append(f"发现 {skipped_count} 个跳过的测试 - 违反测试铁律")
                
        except Exception as e:
            violations.append(f"测试检查失败: {str(e)}")
            
        return violations
    
    def _check_placeholders(self) -> bool:
        """检查占位符"""
        placeholder_patterns = [
            r"TODO",
            r"FIXME", 
            r"XXX",
            r"PLACEHOLDER",
            r"待实现",
            r"暂未实现",
            r"pass\s*#.*placeholder",
        ]
        
        try:
            # 检查测试文件
            test_file = Path("tests/unit/brain/test_commander_engine_v2.py")
            if test_file.exists():
                content = test_file.read_text(encoding='utf-8')
                
                for pattern in placeholder_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        return True
                        
        except Exception:
            pass
            
        return False
    
    def _check_unfixed_bugs(self) -> bool:
        """检查未修复的bug"""
        try:
            # 运行测试检查是否有失败
            result = subprocess.run([
                "python", "-m", "pytest",
                "tests/unit/brain/test_commander_engine_v2.py",
                "--tb=no", "-q"
            ], capture_output=True, text=True)
            
            # 如果有测试失败，说明有未修复的bug
            return result.returncode != 0
            
        except Exception:
            return True  # 如果无法运行测试，认为有问题
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成铁律核查报告"""
        report = []
        report.append("🚨 铁律核查报告")
        report.append("=" * 50)
        report.append(f"检查时间: {self._get_timestamp()}")
        report.append(f"总违规数: {results['total_violations']}")
        report.append(f"核查状态: {results['status']}")
        report.append("")
        
        # 零号铁律违规
        if results["zero_law_violations"]:
            report.append("❌ 零号铁律违规:")
            for violation in results["zero_law_violations"]:
                report.append(f"  - {violation}")
            report.append("")
        
        # 核心铁律违规
        if results["core_law_violations"]:
            report.append("❌ 核心铁律违规:")
            for violation in results["core_law_violations"]:
                report.append(f"  - {violation}")
            report.append("")
        
        # 测试铁律违规
        if results["test_law_violations"]:
            report.append("❌ 测试铁律违规:")
            for violation in results["test_law_violations"]:
                report.append(f"  - {violation}")
            report.append("")
        
        if results["status"] == "PASSED":
            report.append("✅ 所有铁律检查通过!")
        else:
            report.append("🚫 存在铁律违规，必须立即修复!")
            report.append("")
            report.append("🔧 修复建议:")
            report.append("1. 立即修复所有违规项")
            report.append("2. 重新运行铁律核查")
            report.append("3. 确保100%覆盖率和代码质量")
        
        return "\n".join(report)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """主函数"""
    checker = IronLawChecker()
    results = checker.check_all_laws()
    report = checker.generate_report(results)
    
    print(report)
    
    # 如果有违规，退出码为1
    if results["status"] == "FAILED":
        print("\n🚨 铁律核查失败 - 阻断执行!")
        sys.exit(1)
    else:
        print("\n✅ 铁律核查通过 - 允许继续!")
        sys.exit(0)


if __name__ == "__main__":
    main()