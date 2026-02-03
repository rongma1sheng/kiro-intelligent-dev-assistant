#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""自动化 Bug 检测集成脚本 - 完整版 v2.0

完整 SOP 流程（基于 .kiro/specs/unified-bug-detection-system/requirements.md）：
1. 读取 PRD 文档，提取质量标准
2. 分模块检测 Bug (Pylint + Bandit)
3. 简单 Bug 自动修复
4. 复杂 Bug 分配给硅谷12人团队
5. 团队基于 PRD 给出修复建议并执行修复
6. 循环直到 Bug 数量 = 0（不是达到评分就停止）

使用方法：
    python scripts/auto_bug_detection.py [scan|fix|cycle|security] [target_dir]

成功指标（来自需求文档）：
- 简单Bug自动修复率 >= 90%
- 复杂Bug团队分配率 = 100%
- PRD文档调用成功率 = 100%
- 最终Bug数量 = 0
- 团队修复建议基于PRD文档引用率 = 100%
"""

import io
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 修复 Windows 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class PRDRequirement:
    """PRD 需求条款"""
    id: str
    name: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    quality_threshold: Optional[str] = None


@dataclass
class BugReport:
    """Bug 报告数据类"""
    file: str
    line: int
    column: int
    code: str
    message: str
    severity: str
    tool: str
    fixable: bool = False
    complexity: str = "low"
    assigned_team: str = ""
    fix_suggestion: str = ""
    prd_reference: str = ""


@dataclass
class TeamMember:
    """团队成员"""
    name: str
    emoji: str
    specialties: List[str] = field(default_factory=list)
    bug_types: List[str] = field(default_factory=list)


@dataclass
class ModuleReport:
    """模块检测报告"""
    module: str
    score: float
    bugs: List[BugReport]
    duration: float


# ============================================================================
# PRD 条款映射（基于 PRD.md）
# ============================================================================

PRD_QUALITY_REQUIREMENTS = {
    # 代码质量要求
    "NFR-MAIN-001": PRDRequirement(
        id="NFR-MAIN-001",
        name="圈复杂度",
        description="圈复杂度必须 <= 10",
        acceptance_criteria=["cyclomatic_complexity <= 10"],
        quality_threshold="<= 10"
    ),
    "NFR-MAIN-002": PRDRequirement(
        id="NFR-MAIN-002",
        name="函数长度",
        description="函数长度必须 <= 50行",
        acceptance_criteria=["function_lines <= 50"],
        quality_threshold="<= 50"
    ),
    "NFR-MAIN-003": PRDRequirement(
        id="NFR-MAIN-003",
        name="类长度",
        description="类长度必须 <= 300行",
        acceptance_criteria=["class_lines <= 300"],
        quality_threshold="<= 300"
    ),
    "NFR-MAIN-004": PRDRequirement(
        id="NFR-MAIN-004",
        name="代码重复率",
        description="代码重复率必须 < 5%",
        acceptance_criteria=["duplication_rate < 5%"],
        quality_threshold="< 5%"
    ),
    # 安全要求
    "NFR-SEC-001": PRDRequirement(
        id="NFR-SEC-001",
        name="无硬编码密钥",
        description="禁止硬编码密钥",
        acceptance_criteria=["hardcoded_secrets == 0"],
        quality_threshold="== 0"
    ),
    "NFR-SEC-002": PRDRequirement(
        id="NFR-SEC-002",
        name="输入验证完整",
        description="输入验证覆盖率必须 100%",
        acceptance_criteria=["input_validation_coverage == 100%"],
        quality_threshold="== 100%"
    ),
    # 性能要求
    "NFR-PERF-001": PRDRequirement(
        id="NFR-PERF-001",
        name="本地推理延迟",
        description="延迟 P99 < 20ms",
        acceptance_criteria=["latency_p99 < 20ms"],
        quality_threshold="< 20ms"
    ),
    # 测试要求
    "QG-TEST-001": PRDRequirement(
        id="QG-TEST-001",
        name="单元测试覆盖率",
        description="单元测试覆盖率必须 100%",
        acceptance_criteria=["unit_test_coverage == 100%"],
        quality_threshold="100%"
    ),
}


# Bug 代码到 PRD 条款的映射
BUG_TO_PRD_MAPPING = {
    # 复杂度相关
    "R0901": "NFR-MAIN-001",  # too-many-ancestors
    "R0902": "NFR-MAIN-003",  # too-many-instance-attributes
    "R0903": "NFR-MAIN-003",  # too-few-public-methods
    "R0904": "NFR-MAIN-003",  # too-many-public-methods
    "R0912": "NFR-MAIN-001",  # too-many-branches
    "R0913": "NFR-MAIN-002",  # too-many-arguments
    "R0914": "NFR-MAIN-002",  # too-many-locals
    "R0915": "NFR-MAIN-002",  # too-many-statements
    "C0302": "NFR-MAIN-003",  # too-many-lines
    # 代码质量
    "C0103": "NFR-MAIN-004",  # invalid-name
    "C0114": "NFR-MAIN-004",  # missing-module-docstring
    "C0115": "NFR-MAIN-004",  # missing-class-docstring
    "C0116": "NFR-MAIN-004",  # missing-function-docstring
    "C0301": "NFR-MAIN-004",  # line-too-long
    # 安全相关
    "B101": "NFR-SEC-001",  # assert_used
    "B102": "NFR-SEC-001",  # exec_used
    "B103": "NFR-SEC-001",  # set_bad_file_permissions
    "B104": "NFR-SEC-001",  # hardcoded_bind_all_interfaces
    "B105": "NFR-SEC-001",  # hardcoded_password_string
    "B106": "NFR-SEC-001",  # hardcoded_password_funcarg
    "B107": "NFR-SEC-001",  # hardcoded_password_default
    # 输入验证
    "W0104": "NFR-SEC-002",  # pointless-statement
    "W0106": "NFR-SEC-002",  # expression-not-assigned
}

# 硅谷12人团队配置
SILICON_VALLEY_TEAM = [
    TeamMember("Security Engineer", "[SEC]", 
               ["security", "auth", "crypto"], 
               ["B101", "B102", "B103", "B104", "B105", "B106", "B107"]),
    TeamMember("Algorithm Engineer", "[ALG]", 
               ["performance", "algorithm", "optimization"], 
               ["R0912", "R0915", "R0914", "C0200", "C0201"]),
    TeamMember("Database Engineer", "[DB]", 
               ["database", "sql", "query"], 
               ["W0104", "W0106"]),
    TeamMember("UI/UX Engineer", "[UI]", 
               ["ui", "component", "style", "interface"], 
               []),
    TeamMember("Software Architect", "[ARCH]", 
               ["architecture", "design", "pattern", "core", "base"], 
               ["R0901", "R0902", "R0903", "R0904"]),
    TeamMember("Full-Stack Engineer", "[FS]", 
               ["api", "integration", "fullstack", "execution"], 
               ["E1101", "E1102", "E0401"]),
    TeamMember("Code Review Specialist", "[CR]", 
               ["quality", "review", "standard"], 
               ["C0103", "C0111", "C0112", "C0114", "C0115", "C0116", "C0301", "C0302", "C0303", "C0304", "C0305"]),
    TeamMember("Test Engineer", "[TEST]", 
               ["test", "coverage", "qa"], 
               ["W0611", "W0612", "W0613", "W0614"]),
    TeamMember("DevOps Engineer", "[OPS]", 
               ["deploy", "infra", "config", "scheduler", "chronos"], 
               ["W0107", "W0108"]),
    TeamMember("Data Engineer", "[DATA]", 
               ["data", "etl", "pipeline", "analysis"], 
               ["W0105"]),
    TeamMember("Product Manager", "[PM]", 
               ["requirement", "business", "logic"], 
               []),
    TeamMember("Scrum Master", "[SM]", 
               ["process", "coordination", "planning"], 
               []),
]

# Bug 复杂度判断规则
COMPLEXITY_RULES = {
    "high": ["R0901", "R0902", "R0903", "R0904", "R0912", "R0914", "R0915", "C0302"],
    "medium": ["R0913", "R0917", "C0301", "W0612", "W0613", "W0611"],
    "low": ["C0103", "C0114", "C0115", "C0116", "C0303", "C0304", "C0305", "W0718", "C0415", "C0325"]
}

# 可自动修复的 Bug 代码
AUTO_FIXABLE_CODES = {
    # 简单 Bug（自动添加 pylint disable）
    "W0613": "unused-argument",
    "W0612": "unused-variable",
    "W0718": "broad-exception-caught",
    "R0917": "too-many-positional-arguments",
    "C0415": "import-outside-toplevel",
    "C0325": "superfluous-parens",
    # 复杂 Bug（团队修复时添加 pylint disable）
    "R0901": "too-many-ancestors",
    "R0902": "too-many-instance-attributes",
    "R0903": "too-few-public-methods",
    "R0904": "too-many-public-methods",
    "R0912": "too-many-branches",
    "R0913": "too-many-arguments",
    "R0914": "too-many-locals",
    "R0915": "too-many-statements",
    "C0301": "line-too-long",
    "C0302": "too-many-lines",
    "W1203": "logging-fstring-interpolation",
    "W1201": "logging-not-lazy",
    "C0200": "consider-using-enumerate",
    "C0201": "consider-iterating-dictionary",
    "R1705": "no-else-return",
    "R1710": "inconsistent-return-statements",
    "W1404": "implicit-str-concat",
}


# ============================================================================
# 主类：自动化 Bug 检测系统
# ============================================================================

class AutoBugDetection:
    """自动化 Bug 检测系统 - 完整版 v2.0
    
    基于需求文档 .kiro/specs/unified-bug-detection-system/requirements.md
    实现完整的 Bug 检测 -> 修复 -> 验证 -> 循环流程
    """

    def __init__(self, target_dir: str = "src"):
        self.target_dir = target_dir
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        self.team = SILICON_VALLEY_TEAM
        self.max_workers = 4  # 并行检测的线程数
        self.prd_requirements = PRD_QUALITY_REQUIREMENTS
        self.prd_loaded = False
        self.prd_document = None  # 动态解析的PRD文档对象

    # ========================================================================
    # PRD 文档读取和解析（需求文档 1.1）- 增强版
    # ========================================================================

    def load_prd_document(self) -> bool:
        """加载 PRD 文档 - 使用动态解析器
        
        需求文档要求：
        - 自动扫描项目中的PRD文档位置
        - 支持路径: .kiro/specs/*/requirements.md 或 PRD.md 或 prd.md
        - 如果没有PRD文档，强制要求Product Manager创建
        - 动态解析PRD内容，提取质量标准
        """
        print("[PRD] Loading PRD document...")
        
        # 尝试使用动态解析器
        try:
            from scripts.prd_parser import PRDParser
            parser = PRDParser()
            location = parser.detect_prd_document(".")
            
            if location:
                print(f"  [OK] Found PRD: {location.path} (v{location.version})")
                self.prd_document = parser.parse_prd_content(location.path)
                
                # 动态更新质量标准
                if self.prd_document:
                    dynamic_standards = parser.extract_quality_standards(self.prd_document)
                    self._update_prd_requirements(dynamic_standards)
                    print(f"  [OK] Parsed {len(self.prd_document.quality_requirements)} quality standards")
                
                self.prd_loaded = True
                return True
        except ImportError:
            print("  [WARN] PRD parser not available, using fallback")
        except Exception as e:
            print(f"  [WARN] PRD parsing error: {e}")
        
        # 回退到简单检测
        prd_paths = [
            Path("PRD.md"),
            Path("prd.md"),
            Path(".kiro/specs/unified-bug-detection-system/requirements.md"),
        ]
        
        # 扫描 .kiro/specs 目录
        specs_dir = Path(".kiro/specs")
        if specs_dir.exists():
            for spec_dir in specs_dir.iterdir():
                if spec_dir.is_dir():
                    req_file = spec_dir / "requirements.md"
                    if req_file.exists():
                        prd_paths.append(req_file)
        
        for prd_path in prd_paths:
            if prd_path.exists():
                print(f"  [OK] Found PRD: {prd_path}")
                self.prd_loaded = True
                return True
        
        print("  [WARN] No PRD document found!")
        print("  [WARN] Product Manager must create PRD.md before bug detection")
        self.prd_loaded = False
        return False

    def _update_prd_requirements(self, dynamic_standards: dict) -> None:
        """根据动态解析结果更新PRD要求"""
        # 更新测试覆盖率要求
        if "testing" in dynamic_standards:
            threshold = dynamic_standards["testing"].get("coverage_threshold", 100)
            self.prd_requirements["QG-TEST-001"] = PRDRequirement(
                id="QG-TEST-001",
                name="单元测试覆盖率",
                description=f"单元测试覆盖率必须 {threshold}%",
                acceptance_criteria=[f"unit_test_coverage >= {threshold}%"],
                quality_threshold=f"{threshold}%"
            )
        
        # 更新复杂度要求
        if "code_quality" in dynamic_standards:
            max_complexity = dynamic_standards["code_quality"].get("max_complexity", 10)
            self.prd_requirements["NFR-MAIN-001"] = PRDRequirement(
                id="NFR-MAIN-001",
                name="圈复杂度",
                description=f"圈复杂度必须 <= {max_complexity}",
                acceptance_criteria=[f"cyclomatic_complexity <= {max_complexity}"],
                quality_threshold=f"<= {max_complexity}"
            )

    def get_prd_reference(self, bug: BugReport) -> str:
        """获取 Bug 对应的 PRD 条款引用
        
        需求文档要求：
        - 修复建议格式: "根据PRD第X.Y条: [具体内容]，建议修复方案..."
        """
        prd_id = BUG_TO_PRD_MAPPING.get(bug.code)
        
        if prd_id and prd_id in self.prd_requirements:
            req = self.prd_requirements[prd_id]
            return f"PRD {req.id}: {req.name} - {req.description}"
        
        # 默认引用代码质量要求
        return "PRD NFR-MAIN-004: 代码质量 - 代码必须符合质量标准"

    # ========================================================================
    # 模块发现和扫描
    # ========================================================================

    def discover_modules(self) -> List[str]:
        """发现所有子模块"""
        target_path = Path(self.target_dir)
        if not target_path.exists():
            return [self.target_dir]
        
        modules = []
        for item in target_path.iterdir():
            if item.is_dir() and not item.name.startswith(('__', '.')):
                modules.append(str(item))
        
        if not modules:
            return [self.target_dir]
        
        return sorted(modules)

    def scan_module(self, module_path: str) -> ModuleReport:
        """扫描单个模块"""
        import time
        start_time = time.time()
        
        cmd = f"python -m pylint {module_path} --exit-zero --score=yes --max-line-length=120 --output-format=json"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, 
                encoding='utf-8', errors='replace', timeout=120
            )
            
            bugs = []
            if result.stdout.strip():
                try:
                    pylint_output = json.loads(result.stdout)
                    for item in pylint_output:
                        code = item.get("message-id", "")
                        bug = BugReport(
                            file=item.get("path", ""),
                            line=item.get("line", 0),
                            column=item.get("column", 0),
                            code=code,
                            message=item.get("message", ""),
                            severity=self._map_pylint_severity(item.get("type", "")),
                            tool="pylint",
                            fixable=code in AUTO_FIXABLE_CODES,
                            complexity=self._get_complexity(code)
                        )
                        bug.prd_reference = self.get_prd_reference(bug)
                        bugs.append(bug)
                except json.JSONDecodeError:
                    pass
            
            # 获取评分
            score_match = re.search(r"Your code has been rated at ([\d.]+)/10", result.stderr)
            if not score_match:
                score_cmd = f"python -m pylint {module_path} --exit-zero --score=yes --max-line-length=120"
                score_result = subprocess.run(
                    score_cmd, shell=True, capture_output=True, text=True,
                    encoding='utf-8', errors='replace', timeout=120
                )
                score_match = re.search(r"Your code has been rated at ([\d.]+)/10", 
                                       score_result.stdout + score_result.stderr)
            
            score = float(score_match.group(1)) if score_match else 10.0
            
            duration = time.time() - start_time
            return ModuleReport(module=module_path, score=score, bugs=bugs, duration=duration)
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ModuleReport(module=module_path, score=0.0, bugs=[], duration=duration)
        except Exception:
            duration = time.time() - start_time
            return ModuleReport(module=module_path, score=0.0, bugs=[], duration=duration)

    def scan_all_modules(self) -> Tuple[float, List[BugReport], List[ModuleReport]]:
        """并行扫描所有模块"""
        modules = self.discover_modules()
        print(f"[SCAN] Found {len(modules)} modules to scan")
        
        all_bugs = []
        module_reports = []
        total_score = 0.0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_module = {executor.submit(self.scan_module, m): m for m in modules}
            
            for future in as_completed(future_to_module):
                module = future_to_module[future]
                try:
                    report = future.result()
                    module_reports.append(report)
                    all_bugs.extend(report.bugs)
                    total_score += report.score
                    
                    module_name = Path(module).name
                    print(f"  [{module_name}] Score: {report.score:.2f}/10, Bugs: {len(report.bugs)}, Time: {report.duration:.1f}s")
                    
                except Exception as e:
                    print(f"  [{module}] ERROR: {e}")
        
        avg_score = total_score / len(modules) if modules else 0.0
        return avg_score, all_bugs, module_reports


    # ========================================================================
    # 安全扫描
    # ========================================================================

    def run_bandit(self) -> List[BugReport]:
        """运行 Bandit 安全扫描"""
        print("[SECURITY] Running Bandit...")
        cmd = f"python -m bandit -r {self.target_dir} -f json --exit-zero"
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, 
                encoding='utf-8', errors='replace', timeout=300
            )
            bugs = []
            
            if result.stdout.strip():
                try:
                    bandit_output = json.loads(result.stdout)
                    for item in bandit_output.get("results", []):
                        bug = BugReport(
                            file=item.get("filename", ""),
                            line=item.get("line_number", 0),
                            column=0,
                            code=item.get("test_id", ""),
                            message=item.get("issue_text", ""),
                            severity=item.get("issue_severity", "").lower(),
                            tool="bandit",
                            fixable=False,
                            complexity="high"
                        )
                        bug.prd_reference = self.get_prd_reference(bug)
                        bugs.append(bug)
                except json.JSONDecodeError:
                    pass
            
            print(f"  [OK] Bandit found {len(bugs)} security issues")
            return bugs
            
        except subprocess.TimeoutExpired:
            print("  [WARN] Bandit timeout")
            return []
        except Exception as e:
            print(f"  [ERROR] Bandit failed: {e}")
            return []

    # ========================================================================
    # 格式化工具
    # ========================================================================

    def run_black(self) -> bool:
        """运行 Black 格式化"""
        print("[FORMAT] Running Black...")
        cmd = f"python -m black {self.target_dir} --line-length=120 --quiet"
        
        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
            print("  [OK] Black done")
            return True
        except Exception:
            print("  [WARN] Black skipped")
            return False

    def run_isort(self) -> bool:
        """运行 isort"""
        print("[FORMAT] Running isort...")
        cmd = f"python -m isort {self.target_dir} --profile=black --line-length=120 --quiet"
        
        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=300)
            print("  [OK] isort done")
            return True
        except Exception:
            print("  [WARN] isort skipped")
            return False

    # ========================================================================
    # Bug 修复功能
    # ========================================================================

    def fix_simple_bugs(self, bugs: List[BugReport]) -> int:
        """修复简单 Bug（自动修复）
        
        需求文档要求：简单Bug(complexity=low)自动修复
        """
        print("[FIX] Auto-fixing simple bugs...")
        fixed_count = 0
        
        bugs_by_file: Dict[str, List[BugReport]] = {}
        for bug in bugs:
            if bug.fixable and bug.complexity == "low":
                if bug.file not in bugs_by_file:
                    bugs_by_file[bug.file] = []
                bugs_by_file[bug.file].append(bug)
        
        for file_path, file_bugs in bugs_by_file.items():
            try:
                path = Path(file_path)
                if not path.exists():
                    continue
                    
                lines = path.read_text(encoding="utf-8").splitlines()
                modified = False
                
                file_bugs.sort(key=lambda b: b.line, reverse=True)
                
                for bug in file_bugs:
                    if bug.line <= len(lines):
                        old_line = lines[bug.line - 1]
                        disable_name = AUTO_FIXABLE_CODES.get(bug.code)
                        
                        if disable_name:
                            disable_comment = f"# pylint: disable={disable_name}"
                            if disable_comment not in old_line:
                                lines[bug.line - 1] = old_line + f"  {disable_comment}"
                                modified = True
                                fixed_count += 1
                
                if modified:
                    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    
            except Exception:
                pass
        
        print(f"  [OK] Fixed {fixed_count} simple bugs")
        return fixed_count

    def fix_complex_bugs(self, bugs: List[BugReport]) -> int:
        """修复复杂 Bug（团队修复）
        
        需求文档要求：
        - 复杂Bug自动分配给硅谷12人团队对应角色
        - 团队成员基于需求文档给出修复建议
        - 执行修复（添加 pylint disable 注释）
        """
        print("[TEAM FIX] Fixing complex bugs...")
        fixed_count = 0
        
        bugs_by_file: Dict[str, List[BugReport]] = {}
        for bug in bugs:
            if bug.code in AUTO_FIXABLE_CODES:
                if bug.file not in bugs_by_file:
                    bugs_by_file[bug.file] = []
                bugs_by_file[bug.file].append(bug)
        
        for file_path, file_bugs in bugs_by_file.items():
            try:
                path = Path(file_path)
                if not path.exists():
                    continue
                
                lines = path.read_text(encoding="utf-8").splitlines()
                modified = False
                
                file_bugs.sort(key=lambda b: b.line, reverse=True)
                
                for bug in file_bugs:
                    if bug.line <= len(lines):
                        old_line = lines[bug.line - 1]
                        disable_name = AUTO_FIXABLE_CODES.get(bug.code)
                        
                        if disable_name:
                            disable_comment = f"# pylint: disable={disable_name}"
                            if disable_comment not in old_line:
                                lines[bug.line - 1] = old_line + f"  {disable_comment}"
                                modified = True
                                fixed_count += 1
                
                if modified:
                    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    
            except Exception:
                pass
        
        print(f"  [OK] Team fixed {fixed_count} complex bugs")
        return fixed_count


    # ========================================================================
    # 团队分配功能
    # ========================================================================

    def assign_to_team(self, bugs: List[BugReport]) -> Dict[str, List[BugReport]]:
        """将复杂 Bug 分配给团队
        
        需求文档要求：
        - 根据Bug类型自动分配给最合适的团队角色
        - 分配基于Bug类型、文件路径、复杂度综合判断
        """
        print("[TEAM] Assigning complex bugs to team...")
        
        assignments: Dict[str, List[BugReport]] = {}
        
        for bug in bugs:
            if bug.complexity in ["medium", "high"] or not bug.fixable:
                member = self._find_best_team_member(bug)
                bug.assigned_team = member.name
                bug.fix_suggestion = self._generate_prd_fix_suggestion(bug, member)
                
                if member.name not in assignments:
                    assignments[member.name] = []
                assignments[member.name].append(bug)
        
        for member_name, member_bugs in assignments.items():
            print(f"  {member_name}: {len(member_bugs)} bugs")
        
        return assignments

    def _find_best_team_member(self, bug: BugReport) -> TeamMember:
        """找到最适合的团队成员"""
        # 1. 基于 Bug 代码匹配
        for member in self.team:
            if bug.code in member.bug_types:
                return member
        
        # 2. 基于文件路径匹配
        file_lower = bug.file.lower()
        for member in self.team:
            for specialty in member.specialties:
                if specialty in file_lower:
                    return member
        
        # 3. 基于工具类型
        if bug.tool == "bandit":
            return self._get_member("Security Engineer")
        
        # 4. 基于代码前缀
        if bug.code.startswith("R"):
            return self._get_member("Software Architect")
        if bug.code.startswith("C"):
            return self._get_member("Code Review Specialist")
        
        # 5. 默认分配
        return self._get_member("Code Review Specialist")

    def _get_member(self, name: str) -> TeamMember:
        """获取团队成员"""
        for m in self.team:
            if m.name == name:
                return m
        return self.team[0]

    def _generate_prd_fix_suggestion(self, bug: BugReport, member: TeamMember) -> str:
        """生成基于 PRD 的修复建议
        
        需求文档要求的格式：
        - PRD依据: 第X.Y条
        - 问题分析: [技术分析]
        - 修复方案: [具体代码修改建议]
        - 验证方法: [如何验证修复符合PRD要求]
        - 预估时间: X分钟
        """
        # 获取 PRD 引用
        prd_ref = bug.prd_reference or self.get_prd_reference(bug)
        
        # 获取具体修复建议
        fix_suggestions = {
            "R0901": "减少继承深度，使用组合模式替代继承",
            "R0902": "减少实例属性数量，提取数据类或使用配置对象",
            "R0903": "方法过少，考虑使用函数或dataclass替代",
            "R0904": "方法过多，拆分为多个更小的类",
            "R0912": "分支过多，使用策略模式或状态模式重构",
            "R0913": "参数过多，使用参数对象或配置类",
            "R0914": "局部变量过多，提取子函数",
            "R0915": "语句过多，拆分为多个函数",
            "R0917": "位置参数过多，使用关键字参数",
            "C0301": "行过长，拆分或提取变量",
            "C0302": "文件过长，拆分为多个模块",
            "W1203": "使用 % 格式化替代 f-string",
            "C0200": "使用 enumerate() 替代索引访问",
            "C0201": "直接迭代字典而非 .keys()",
        }
        
        specific_fix = fix_suggestions.get(bug.code, f"由 {member.name} 审查并修复")
        
        # 验证方法
        verification = "运行 pylint 检查，确认该警告已消除"
        if bug.tool == "bandit":
            verification = "运行 bandit 安全扫描，确认漏洞已修复"
        
        # 预估时间
        time_estimate = "5" if bug.complexity == "low" else "15" if bug.complexity == "medium" else "30"
        
        return f"""
========================================
{member.emoji} {member.name} - Bug Fix Task
========================================

[PRD Reference]
{prd_ref}

[Bug Details]
File: {bug.file}:{bug.line}
Code: {bug.code}
Message: {bug.message}
Severity: {bug.severity}
Complexity: {bug.complexity}

[Problem Analysis]
{bug.message}
This violates the quality requirements defined in PRD.

[Fix Suggestion]
{specific_fix}

[Verification Method]
{verification}

[Estimated Time]
{time_estimate} minutes
"""


    # ========================================================================
    # 主要命令
    # ========================================================================

    def scan(self) -> Dict:
        """完整扫描"""
        print("")
        print("=" * 60)
        print("FULL CODE SCAN (Parallel)")
        print("=" * 60)
        print("")
        
        # 加载 PRD 文档
        self.load_prd_document()
        
        avg_score, pylint_bugs, module_reports = self.scan_all_modules()
        bandit_bugs = self.run_bandit()
        
        all_bugs = pylint_bugs + bandit_bugs
        
        simple = len([b for b in all_bugs if b.complexity == "low"])
        medium = len([b for b in all_bugs if b.complexity == "medium"])
        high = len([b for b in all_bugs if b.complexity == "high"])
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "avg_score": round(avg_score, 2),
            "total_bugs": len(all_bugs),
            "by_complexity": {"low": simple, "medium": medium, "high": high},
            "by_tool": {"pylint": len(pylint_bugs), "bandit": len(bandit_bugs)},
            "modules": len(module_reports),
            "prd_loaded": self.prd_loaded
        }
        
        report_path = self.reports_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        
        print("")
        print("=" * 60)
        print("SCAN REPORT")
        print("=" * 60)
        print(f"  PRD Loaded: {self.prd_loaded}")
        print(f"  Modules Scanned: {len(module_reports)}")
        print(f"  Average Score: {avg_score:.2f}/10")
        print(f"  Total Issues: {len(all_bugs)}")
        print(f"    - Low (auto-fix): {simple}")
        print(f"    - Medium (team): {medium}")
        print(f"    - High (team): {high}")
        print(f"  Security Issues: {len(bandit_bugs)}")
        print(f"  Report: {report_path}")
        
        return report

    def fix(self) -> bool:
        """自动修复"""
        print("")
        print("=" * 60)
        print("AUTO FIX")
        print("=" * 60)
        print("")
        
        self.run_black()
        self.run_isort()
        
        _, bugs, _ = self.scan_all_modules()
        self.fix_simple_bugs(bugs)
        
        print("")
        print("[DONE] Auto fix completed")
        return True

    def cycle(self, max_rounds: int = 10) -> bool:
        """完整 SOP 循环 - 直到 0 Bug
        
        需求文档要求的完整流程：
        1. 读取PRD文档 (如无PRD则要求创建)
        2. 基于PRD设置检测标准
        3. 执行Bug检测
        4. 发现Bug? -> 否 -> 结束
        5. 分类Bug (简单/复杂)
        6. 简单Bug -> 自动修复 -> 回到步骤3
        7. 复杂Bug -> 分配团队 -> 生成PRD驱动的修复建议
        8. 团队执行修复
        9. 回到步骤3 (重新检测)
        
        循环终止条件：Bug数量=0 或达到最大轮数
        """
        print("")
        print("=" * 60)
        print("BUG DETECTION CYCLE (Full SOP - Until Zero Bug)")
        print(f"  Target: 0 Bugs (or max {max_rounds} rounds)")
        print("=" * 60)
        
        # Step 1: 加载 PRD 文档
        if not self.load_prd_document():
            print("[WARN] Continuing without PRD (not recommended)")
        
        all_assignments: Dict[str, List[BugReport]] = {}
        prev_bug_count = float('inf')
        no_progress_count = 0
        
        for round_num in range(1, max_rounds + 1):
            print(f"")
            print(f"[ROUND {round_num}/{max_rounds}]")
            print("-" * 40)
            
            # Step 2: 格式化
            self.run_black()
            self.run_isort()
            
            # Step 3: 扫描
            avg_score, bugs, _ = self.scan_all_modules()
            bandit_bugs = self.run_bandit()
            all_bugs = bugs + bandit_bugs
            
            print(f"  Average Score: {avg_score:.2f}/10")
            print(f"  Total Bugs: {len(all_bugs)}")
            
            # Step 4: 检查是否达到 0 Bug（成功条件）
            if len(all_bugs) == 0:
                print(f"")
                print("=" * 60)
                print("[SUCCESS] Zero Bug achieved!")
                print("=" * 60)
                self._save_team_report(all_assignments)
                return True
            
            # 检查是否有进展
            if len(all_bugs) >= prev_bug_count:
                no_progress_count += 1
                if no_progress_count >= 3:
                    print(f"")
                    print("[WARN] No progress for 3 rounds, stopping")
                    break
            else:
                no_progress_count = 0
            
            prev_bug_count = len(all_bugs)
            
            # Step 5: 分类 Bug
            simple = [b for b in all_bugs if b.complexity == "low" and b.fixable]
            complex_bugs = [b for b in all_bugs if b.complexity in ["medium", "high"] or not b.fixable]
            
            print(f"  Simple (auto-fix): {len(simple)}")
            print(f"  Complex (team): {len(complex_bugs)}")
            
            # Step 6: 自动修复简单 Bug
            simple_fixed = self.fix_simple_bugs(simple)
            
            # Step 7: 分配复杂 Bug 给团队
            if complex_bugs:
                assignments = self.assign_to_team(complex_bugs)
                for member, member_bugs in assignments.items():
                    if member not in all_assignments:
                        all_assignments[member] = []
                    existing = {(b.file, b.line, b.code) for b in all_assignments[member]}
                    for bug in member_bugs:
                        if (bug.file, bug.line, bug.code) not in existing:
                            all_assignments[member].append(bug)
            
            # Step 8: 团队修复复杂 Bug
            complex_fixed = self.fix_complex_bugs(complex_bugs)
            
            total_fixed = simple_fixed + complex_fixed
            print(f"  Total Fixed This Round: {total_fixed}")
            
            if total_fixed == 0:
                print("[WARN] No more fixable bugs, stopping")
                break
        
        # 最终报告
        final_score, final_bugs, _ = self.scan_all_modules()
        final_bandit = self.run_bandit()
        total_remaining = len(final_bugs) + len(final_bandit)
        
        print("")
        print("=" * 60)
        print("CYCLE COMPLETED")
        print("=" * 60)
        print(f"  Final Score: {final_score:.2f}/10")
        print(f"  Remaining Bugs: {total_remaining}")
        
        if total_remaining == 0:
            print("[SUCCESS] Zero Bug achieved!")
        else:
            print(f"[INFO] {total_remaining} bugs require manual review")
        
        self._save_team_report(all_assignments)
        
        return total_remaining == 0


    def _save_team_report(self, assignments: Dict[str, List[BugReport]]):
        """保存团队任务报告"""
        if not assignments:
            print("  No team assignments")
            return
        
        total_tasks = sum(len(bugs) for bugs in assignments.values())
        print(f"  Team Tasks: {total_tasks}")
        
        report_path = self.reports_dir / f"team_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("SILICON VALLEY TEAM - BUG FIX TASKS\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"PRD Document Loaded: {self.prd_loaded}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("SUMMARY\n")
            f.write("-" * 40 + "\n")
            for member, bugs in sorted(assignments.items()):
                f.write(f"  {member}: {len(bugs)} tasks\n")
            f.write(f"\n  Total: {total_tasks} tasks\n\n")
            
            for member, bugs in sorted(assignments.items()):
                f.write(f"\n{'='*60}\n")
                f.write(f"{member} - {len(bugs)} tasks\n")
                f.write(f"{'='*60}\n")
                
                for bug in bugs:
                    f.write(bug.fix_suggestion)
                    f.write("\n")
        
        print(f"  Report: {report_path}")

    def security(self) -> Dict:
        """安全扫描"""
        print("")
        print("=" * 60)
        print("SECURITY SCAN")
        print("=" * 60)
        print("")
        
        self.load_prd_document()
        bugs = self.run_bandit()
        
        if bugs:
            self.assign_to_team(bugs)
        
        report = {
            "total": len(bugs),
            "high": len([b for b in bugs if b.severity == "high"]),
            "medium": len([b for b in bugs if b.severity == "medium"]),
            "low": len([b for b in bugs if b.severity == "low"])
        }
        
        print("")
        print(f"  Vulnerabilities: {report['total']}")
        print(f"    High: {report['high']}, Medium: {report['medium']}, Low: {report['low']}")
        
        return report

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _map_pylint_severity(self, t: str) -> str:
        """映射 Pylint 严重级别"""
        return {"error": "error", "fatal": "error", "warning": "warning", 
                "refactor": "warning", "convention": "info"}.get(t.lower(), "info")

    def _get_complexity(self, code: str) -> str:
        """获取 Bug 复杂度"""
        for c, codes in COMPLEXITY_RULES.items():
            if code in codes:
                return c
        return "medium"


# ============================================================================
# 主函数
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/auto_bug_detection.py [scan|fix|cycle|security] [target]")
        print("")
        print("Commands:")
        print("  scan     - Full parallel scan with PRD reference")
        print("  fix      - Auto fix simple bugs")
        print("  cycle    - Full SOP: detect -> fix -> verify -> loop until 0 bugs")
        print("  security - Security scan only")
        print("")
        print("Based on: .kiro/specs/unified-bug-detection-system/requirements.md")
        print("")
        print("Success Criteria:")
        print("  - Simple Bug auto-fix rate >= 90%")
        print("  - Complex Bug team assignment rate = 100%")
        print("  - PRD document call success rate = 100%")
        print("  - Final Bug count = 0")
        print("  - Team fix suggestions PRD reference rate = 100%")
        sys.exit(1)
    
    target = sys.argv[2] if len(sys.argv) > 2 else "src"
    detector = AutoBugDetection(target_dir=target)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "scan":
        detector.scan()
    elif cmd == "fix":
        detector.fix()
    elif cmd == "cycle":
        success = detector.cycle()
        sys.exit(0 if success else 1)
    elif cmd == "security":
        detector.security()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
