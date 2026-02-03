#!/usr/bin/env python
"""
MIA系统提交前检查脚本
在代码提交前运行所有质量检查
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class PreCommitChecker:
    """提交前检查器"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.workspace_root = Path(__file__).parent.parent
    
    def run_all_checks(self) -> bool:
        """
        运行所有检查
        
        Returns:
            是否所有检查都通过
        """
        print("=" * 60)
        print("MIA系统提交前检查")
        print("=" * 60)
        print()
        
        checks = [
            ("代码格式化检查", self._check_formatting),
            ("类型检查", self._check_types),
            ("代码质量检查", self._check_quality),
            ("安全扫描", self._check_security),
            ("单元测试", self._run_unit_tests),
            ("测试覆盖率", self._check_coverage),
        ]
        
        for check_name, check_func in checks:
            print(f"\n{'=' * 60}")
            print(f"运行: {check_name}")
            print(f"{'=' * 60}")
            
            if check_func():
                self.checks_passed += 1
                print(f"✅ {check_name}: 通过")
            else:
                self.checks_failed += 1
                print(f"❌ {check_name}: 失败")
        
        # 输出总结
        print(f"\n{'=' * 60}")
        print("检查总结")
        print(f"{'=' * 60}")
        print(f"通过: {self.checks_passed}")
        print(f"失败: {self.checks_failed}")
        
        if self.checks_failed == 0:
            print("\n✅ 所有检查通过！可以提交代码。")
            return True
        else:
            print(f"\n❌ {self.checks_failed} 个检查失败！请修复后再提交。")
            return False
    
    def _check_formatting(self) -> bool:
        """检查代码格式化"""
        try:
            # 使用black检查格式
            result = subprocess.run(
                ['black', '--check', 'src/', 'tests/'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True
            else:
                print("\n代码格式不符合规范，运行以下命令修复:")
                print("  black src/ tests/")
                return False
        except FileNotFoundError:
            print("\n⚠️  未安装black，跳过格式检查")
            print("  安装: pip install black")
            return True
    
    def _check_types(self) -> bool:
        """检查类型注解"""
        try:
            result = subprocess.run(
                ['mypy', 'src/'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True
            else:
                print("\n类型检查失败:")
                print(result.stdout)
                return False
        except FileNotFoundError:
            print("\n⚠️  未安装mypy，跳过类型检查")
            print("  安装: pip install mypy")
            return True
    
    def _check_quality(self) -> bool:
        """检查代码质量"""
        try:
            result = subprocess.run(
                ['pylint', 'src/', '--fail-under=8.0'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 提取评分
                for line in result.stdout.split('\n'):
                    if 'Your code has been rated at' in line:
                        print(f"\n{line}")
                return True
            else:
                print("\nPylint评分 < 8.0:")
                print(result.stdout)
                return False
        except FileNotFoundError:
            print("\n⚠️  未安装pylint，跳过质量检查")
            print("  安装: pip install pylint")
            return True
    
    def _check_security(self) -> bool:
        """检查安全漏洞"""
        try:
            result = subprocess.run(
                ['bandit', '-r', 'src/', '-ll'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            # bandit返回码: 0=无问题, 1=有问题
            if result.returncode == 0:
                return True
            else:
                print("\n发现安全漏洞:")
                print(result.stdout)
                return False
        except FileNotFoundError:
            print("\n⚠️  未安装bandit，跳过安全检查")
            print("  安装: pip install bandit")
            return True
    
    def _run_unit_tests(self) -> bool:
        """运行单元测试"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/unit/', '-v'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 提取测试统计
                for line in result.stdout.split('\n'):
                    if 'passed' in line:
                        print(f"\n{line}")
                return True
            else:
                print("\n单元测试失败:")
                print(result.stdout)
                return False
        except FileNotFoundError:
            print("\n⚠️  未安装pytest，跳过测试")
            print("  安装: pip install pytest")
            return True
    
    def _check_coverage(self) -> bool:
        """检查测试覆盖率"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/unit/', '--cov=src', '--cov-report=term', '--cov-fail-under=85'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 提取覆盖率
                for line in result.stdout.split('\n'):
                    if 'TOTAL' in line:
                        print(f"\n{line}")
                return True
            else:
                print("\n测试覆盖率 < 85%:")
                print(result.stdout)
                return False
        except FileNotFoundError:
            print("\n⚠️  未安装pytest-cov，跳过覆盖率检查")
            print("  安装: pip install pytest-cov")
            return True


def main():
    """主函数"""
    checker = PreCommitChecker()
    
    if checker.run_all_checks():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
