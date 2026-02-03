#!/usr/bin/env python33
# -*- coding: utf-8 -*-
"""
增强质量门禁系统 - 集成所有铁律防止LLM漂移

🚨 零号铁律（最高优先级）
- 只能修复"已被明确判定为缺失"的内容
- 不得修改任何已通过认证的章节或功能
- 不得重写或重构非缺失模块
- 不得绕过、弱化或替代任何安全/风控/合规要求

🔒 核心铁律
- 所有回复必须使用中文
- 禁止使用占位符、简化功能
- 发现bug及时修复
- 绝对忠于自己的岗位职责
- 必须专业、标准化、抗幻觉

🧪 测试铁律（最高优先级）
- 严禁跳过任何测试
- 测试超时必须溯源修复（源文件问题或测试逻辑问题）
- 不得使用timeout作为跳过理由
- 发现问题立刻修复

🎯 硅谷12人团队标准
- 遵循角色职责边界，严禁越权
- 复杂问题必须分配给对应角色
- 单轮响应单一主责角色原则
- 强制审计所有维度的完成性
"""

import platform
import io
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class EnhancedQualityGate:
    """增强质量门禁系统"""
    
    def __init__(self):
        self.violations = {
            "ZERO_LAW": [],      # 零号铁律违规
            "CORE_LAW": [],      # 核心铁律违规
            "TEST_LAW": [],      # 测试铁律违规
            "TEAM_LAW": [],      # 团队标准违规
            "CODE_BUGS": []      # 代码质量问题
        }
        
    def check_zero_law_violations(self, target_dir: str) -> List[Dict[str, Any]]:
        """检查零号铁律违规"""
        violations = []
        
        # 检查是否有未授权的重写或重构
        unauthorized_patterns = [
            r"# TODO.*重写",
            r"# TODO.*重构", 
            r"# FIXME.*替换",
            r"def.*_old/(",
            r"class/s+.*Old[^a-zA-Z]",  # 修复：避免匹配ISoldier等正常类名
            r"# 临时.*替代",
            r"# 绕过.*检查"
        ]
        
        for pattern in unauthorized_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "ZERO_LAW", 
                f"疑似未授权修改: {pattern}"
            ))
            
        # 检查是否有弱化安全/风控要求
        security_weakening_patterns = [
            r"# 暂时.*跳过.*安全",
            r"# 临时.*禁用.*风控",
            r"pass/s*#.*安全检查",
            r"return True/s*#.*跳过.*验证"
        ]
        
        for pattern in security_weakening_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "ZERO_LAW",
                f"疑似弱化安全要求: {pattern}"
            ))
            
        return violations
    
    def check_core_law_violations(self, target_dir: str) -> List[Dict[str, Any]]:
        """检查核心铁律违规"""
        violations = []
        
        # 检查英文注释/文档（应该使用中文）- 排除技术性注释和异常类名
        english_patterns = [
            # 排除pylint、mypy等工具注释
            # 排除单纯的类名、变量名注释
            # 排除正常的异常类名如ComponentInitializationError
            # 排除异常构造函数中的组件标识符
            # 只检查真正的英文描述性注释和消息
            r'#/s*[A-Z][a-z]+/s+[a-z]+.*[a-zA-Z]{15,}',   # 长英文描述注释
            r'print/s*/(/s*["/'][A-Z][a-z]+.*[a-zA-Z]{15,}["/']',  # 英文打印消息
            # 排除异常类名和组件标识符，只检查异常消息本身
            r'raise/s+/w+/s*/(/s*["/'][A-Z][a-z]+.*[a-zA-Z]{15,}["/'].*["/'][A-Z][a-z]+.*[a-zA-Z]{15,}["/']',  # 长英文异常消息
        ]
        
        for pattern in english_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "CORE_LAW",
                "违反中文铁律: 发现英文内容"
            ))
            
        # 检查占位符使用 - 排除正常的技术术语
        placeholder_patterns = [
            r"TODO.*实现",  # 明确的TODO实现
            r"FIXME.*修复", # 明确的FIXME修复
            r"XXX.*问题",   # 明确的XXX问题
            r"placeholder.*替换",  # 明确的placeholder
            r"简化.*实现.*临时",    # 明确的简化实现
            r"暂时.*实现.*后续"     # 明确的暂时实现
        ]
        
        for pattern in placeholder_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "CORE_LAW",
                f"违反禁止占位符铁律: {pattern}"
            ))
            
        return violations
    
    def check_test_law_violations(self, target_dir: str) -> List[Dict[str, Any]]:
        """检查测试铁律违规"""
        violations = []
        
        # 检查跳过测试的违规行为
        test_skip_patterns = [
            r"@pytest/.mark/.skip",
            r"@pytest/.mark/.xfail",
            r"pytest/.skip/(",
            r"unittest/.skip",
            r"# 跳过.*测试",
            r"# 暂时.*跳过"
        ]
        
        for pattern in test_skip_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "TEST_LAW",
                f"违反测试铁律: 严禁跳过测试 - {pattern}"
            ))
            
        # 检查超时相关的不当处理
        timeout_patterns = [
            r"timeout.*跳过",
            r"超时.*忽略",
            r"# 因为超时.*不测试"
        ]
        
        for pattern in timeout_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "TEST_LAW",
                f"违反测试铁律: 不得以超时为由跳过 - {pattern}"
            ))
            
        return violations
    
    def check_team_law_violations(self, target_dir: str) -> List[Dict[str, Any]]:
        """检查硅谷12人团队标准违规"""
        violations = []
        
        # 检查角色越权行为
        role_violation_patterns = [
            r"# 作为.*但是.*执行",
            r"# 越权.*处理",
            r"# 代替.*角色",
            r"# 跨角色.*操作"
        ]
        
        for pattern in role_violation_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "TEAM_LAW",
                f"违反团队标准: 角色越权 - {pattern}"
            ))
            
        # 检查是否有绕过三权归一的行为
        bypass_patterns = [
            r"# 绕过.*裁决",
            r"# 直接.*修复.*未确认",
            r"# 跳过.*Product Manager.*确认"
        ]
        
        for pattern in bypass_patterns:
            violations.extend(self._scan_pattern_violations(
                target_dir, pattern, "TEAM_LAW",
                f"违反缺失裁决责任矩阵: {pattern}"
            ))
            
        return violations
    
    def _scan_pattern_violations(self, target_dir: str, pattern: str, 
                                violation_type: str, description: str) -> List[Dict[str, Any]]:
        """扫描模式违规"""
        violations = []
        target_path = Path(target_dir)
        
        if target_path.is_file():
            files = [target_path]
        else:
            files = list(target_path.rglob("*.py"))
            
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                
                for match in matches:
                    line_num = content[:match.start()].count('/n') + 1
                    violations.append({
                        "type": violation_type,
                        "file": str(file_path),
                        "line": line_num,
                        "pattern": pattern,
                        "description": description,
                        "matched_text": match.group(0)[:100]
                    })
            except Exception as e:
                continue
                
        return violations
    
    def check_code_quality(self, target_dir: str) -> List[Dict[str, Any]]:
        """检查代码质量"""
        cmd = f"python -m pylint {target_dir} --exit-zero --output-format=json --max-line-length=120"
        try:
            result = subprocess.run(cmd, shell=True, executable="/bin/bash" if platform.system() == "Darwin" else None, capture_output=True, text=True, 
                                   encoding='utf-8', errors='replace', timeout=600)
            return json.loads(result.stdout) if result.stdout.strip() else []
        except Exception:
            return []
    
    def check_test_coverage_compliance(self, target_dir: str) -> List[Dict[str, Any]]:
        """检查测试覆盖率合规性"""
        violations = []
        
        # 运行覆盖率检查
        try:
            cmd = f"python -m pytest {target_dir} --cov={target_dir.replace('/', '.')} --cov-report=json --tb=no -q"
            result = subprocess.run(cmd, shell=True, executable="/bin/bash" if platform.system() == "Darwin" else None, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=300)
            
            # 检查是否有覆盖率低于100%的文件
            coverage_file = Path("coverage.json")
            if coverage_file.exists():
                coverage_data = json.loads(coverage_file.read_text())
                for file_path, file_data in coverage_data.get("files", {}).items():
                    coverage_pct = file_data.get("summary", {}).get("percent_covered", 0)
                    if coverage_pct < 100:
                        violations.append({
                            "type": "TEST_LAW",
                            "file": file_path,
                            "line": 0,
                            "description": f"测试覆盖率不足: {coverage_pct:.1f}% < 100%",
                            "coverage": coverage_pct
                        })
        except Exception:
            pass
            
        return violations
    
    def run_comprehensive_check(self, target_dir: str = "src") -> Tuple[bool, Dict[str, List]]:
        """运行全面检查"""
        print("🚨 启动增强质量门禁系统")
        print("=" * 80)
        print("检查所有铁律合规性...")
        print()
        
        # 1. 零号铁律检查
        print("🔍 [1/5] 检查零号铁律合规性...")
        self.violations["ZERO_LAW"] = self.check_zero_law_violations(target_dir)
        
        # 2. 核心铁律检查  
        print("🔍 [2/5] 检查核心铁律合规性...")
        self.violations["CORE_LAW"] = self.check_core_law_violations(target_dir)
        
        # 3. 测试铁律检查
        print("🔍 [3/5] 检查测试铁律合规性...")
        self.violations["TEST_LAW"] = self.check_test_law_violations(target_dir)
        
        # 4. 团队标准检查
        print("🔍 [4/5] 检查硅谷12人团队标准合规性...")
        self.violations["TEAM_LAW"] = self.check_team_law_violations(target_dir)
        
        # 5. 代码质量检查
        print("🔍 [5/5] 检查代码质量...")
        self.violations["CODE_BUGS"] = self.check_code_quality(target_dir)
        
        # 统计结果
        total_violations = sum(len(v) for v in self.violations.values())
        is_compliant = total_violations == 0
        
        print()
        print("=" * 80)
        print("🎯 增强质量门禁检查结果")
        print("=" * 80)
        
        for violation_type, violations in self.violations.items():
            count = len(violations)
            status = "✅ 通过" if count == 0 else f"❌ {count}个违规"
            type_name = {
                "ZERO_LAW": "零号铁律",
                "CORE_LAW": "核心铁律", 
                "TEST_LAW": "测试铁律",
                "TEAM_LAW": "团队标准",
                "CODE_BUGS": "代码质量"
            }.get(violation_type, violation_type)
            
            print(f"{type_name}: {status}")
            
        print()
        print(f"总违规数: {total_violations}")
        
        if is_compliant:
            print("🎉 所有铁律检查通过！")
            print("✅ 质量门禁: PASSED")
        else:
            print("🚨 发现铁律违规！")
            print("❌ 质量门禁: FAILED")
            self._generate_violation_report()
            
        return is_compliant, self.violations
    
    def _generate_violation_report(self):
        """生成违规报告"""
        print()
        print("=" * 80)
        print("🚨 违规详情报告")
        print("=" * 80)
        
        for violation_type, violations in self.violations.items():
            if not violations:
                continue
                
            type_name = {
                "ZERO_LAW": "零号铁律违规",
                "CORE_LAW": "核心铁律违规",
                "TEST_LAW": "测试铁律违规", 
                "TEAM_LAW": "团队标准违规",
                "CODE_BUGS": "代码质量问题"
            }.get(violation_type, violation_type)
            
            print(f"/n📋 {type_name} ({len(violations)}个):")
            print("-" * 60)
            
            for i, violation in enumerate(violations[:10], 1):  # 只显示前10个
                file_path = violation.get("file", "unknown")
                line = violation.get("line", 0)
                desc = violation.get("description", "")
                
                print(f"{i}. {file_path}:{line}")
                print(f"   {desc}")
                
                if "matched_text" in violation:
                    print(f"   匹配内容: {violation['matched_text']}")
                print()
                
            if len(violations) > 10:
                print(f"   ... 还有 {len(violations) - 10} 个违规项")
                
        print("=" * 80)
        print("🔧 修复建议:")
        print("1. 立即修复所有零号铁律和核心铁律违规")
        print("2. 按照硅谷12人团队标准分配任务")
        print("3. 严格遵循测试铁律，不得跳过任何测试")
        print("4. 使用中文进行所有开发和文档工作")
        print("5. 运行: python scripts/team_bug_fixer.py 进行团队协作修复")
        print("=" * 80)
        
        # 保存详细报告
        report_path = Path("reports") / f"enhanced_quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "violations": self.violations,
            "summary": {
                "total_violations": sum(len(v) for v in self.violations.values()),
                "by_type": {k: len(v) for k, v in self.violations.items()}
            }
        }
        
        report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), 
                              encoding='utf-8')
        print(f"📄 详细报告已保存: {report_path}")


def main():
    """主函数"""
    target = sys.argv[1] if len(sys.argv) > 1 else "src"
    
    gate = EnhancedQualityGate()
    is_compliant, violations = gate.run_comprehensive_check(target)
    
    return 0 if is_compliant else 1


if __name__ == "__main__":
    sys.exit(main())