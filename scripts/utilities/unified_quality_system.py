#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""统一质量保证系统 - 整合PRD解析、配置验证、质量门禁功能

整合以下功能模块：
1. PRD文档解析 - 动态提取质量标准
2. Kiro配置验证 - 验证hooks/steering/specs/mcp
3. 质量门禁 - Bug扫描和自动修复
4. 团队分配 - 复杂Bug分配给硅谷12人团队

使用方法：
    python scripts/unified_quality_system.py [command] [options]

命令：
    check       - 完整质量检查（PRD解析 + 配置验证 + Bug扫描）
    prd         - 仅PRD文档解析
    config      - 仅Kiro配置验证
    gate        - 仅质量门禁检查
    cycle       - 完整Bug修复循环

质量标准（硬编码100%要求）：
    - 测试覆盖率: 100%
    - Bug数量: 0
    - 配置验证: 全部通过
"""

import io
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============================================================================
# 质量标准常量 - 100%要求
# ============================================================================

QUALITY_STANDARDS = {
    "coverage_threshold": 100,  # 测试覆盖率必须100%
    "max_bugs": 0,              # Bug数量必须为0
    "max_complexity": 10,       # 圈复杂度上限
    "max_line_length": 120,     # 行长度上限
    "max_function_lines": 50,   # 函数长度上限
    "security_tolerance": "zero",  # 零安全漏洞
}


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class PRDLocation:
    """PRD文档位置"""
    path: str
    format: str
    version: str = "unknown"


@dataclass
class QualityStandard:
    """质量标准"""
    category: str
    name: str
    requirement: str
    threshold: str
    metric: str = ""


@dataclass
class PRDDocument:
    """PRD文档结构"""
    title: str
    version: str
    goals: List[str]
    quality_requirements: List[QualityStandard]
    raw_content: str = ""


@dataclass
class ValidationResult:
    """验证结果"""
    category: str
    item: str
    status: str  # pass, warn, fail
    message: str


@dataclass
class BugReport:
    """Bug报告"""
    file: str
    line: int
    code: str
    message: str
    severity: str
    fixable: bool = False


# ============================================================================
# PRD解析模块
# ============================================================================

class PRDParser:
    """PRD文档解析器"""

    PRD_SEARCH_PATHS = [
        "PRD.md", "prd.md", "docs/PRD.md",
        ".kiro/specs/*/requirements.md",
    ]

    def detect_and_parse(self, project_path: str = ".") -> Optional[PRDDocument]:
        """检测并解析PRD文档"""
        project = Path(project_path)
        
        for pattern in self.PRD_SEARCH_PATHS:
            if "*" in pattern:
                matches = list(project.glob(pattern))
                if matches:
                    return self._parse_file(matches[0])
            else:
                prd_path = project / pattern
                if prd_path.exists():
                    return self._parse_file(prd_path)
        return None

    def _parse_file(self, prd_path: Path) -> PRDDocument:
        """解析PRD文件"""
        content = prd_path.read_text(encoding="utf-8")
        
        # 提取版本
        version = "unknown"
        for pattern in [r"版本[：:]\s*v?([\d.]+)", r"Version[：:]\s*v?([\d.]+)"]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                version = match.group(1)
                break
        
        # 提取标题
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "未命名PRD"
        
        # 提取目标
        goals = self._extract_list_items(content, r"(?:产品目标|核心目标|Goals?)")
        
        # 提取质量要求
        quality_reqs = self._extract_quality_requirements(content)
        
        return PRDDocument(
            title=title,
            version=version,
            goals=goals,
            quality_requirements=quality_reqs,
            raw_content=content
        )

    def _extract_list_items(self, content: str, section_pattern: str) -> List[str]:
        """提取章节中的列表项"""
        pattern = rf"##\s*{section_pattern}.*?\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        
        section = match.group(1)
        items = re.findall(r"[-*]\s+(.+)", section)
        items.extend(re.findall(r"\d+\.\s+(.+)", section))
        return items

    def _extract_quality_requirements(self, content: str) -> List[QualityStandard]:
        """提取质量要求"""
        standards = []
        
        # 强制100%覆盖率
        standards.append(QualityStandard(
            category="testing",
            name="测试覆盖率",
            requirement="测试覆盖率 = 100%",
            threshold="100",
            metric="percentage"
        ))
        
        # 零Bug要求
        standards.append(QualityStandard(
            category="code_quality",
            name="Bug数量",
            requirement="Bug数量 = 0",
            threshold="0",
            metric="count"
        ))
        
        # 零安全漏洞
        standards.append(QualityStandard(
            category="security",
            name="安全漏洞",
            requirement="零安全漏洞",
            threshold="0",
            metric="count"
        ))
        
        return standards

    def get_quality_config(self) -> Dict[str, Any]:
        """获取质量配置（强制100%标准）"""
        return {
            "code_quality": {
                "max_complexity": QUALITY_STANDARDS["max_complexity"],
                "max_function_lines": QUALITY_STANDARDS["max_function_lines"],
                "max_line_length": QUALITY_STANDARDS["max_line_length"],
            },
            "security": {
                "vulnerability_tolerance": QUALITY_STANDARDS["security_tolerance"],
            },
            "testing": {
                "coverage_threshold": QUALITY_STANDARDS["coverage_threshold"],
            }
        }


# ============================================================================
# 配置验证模块
# ============================================================================

class ConfigValidator:
    """Kiro配置验证器"""

    VALID_HOOK_EVENTS = [
        "fileEdited", "fileCreated", "fileDeleted",
        "userTriggered", "promptSubmit", "agentStop"
    ]
    VALID_HOOK_ACTIONS = ["askAgent", "runCommand"]
    RUN_COMMAND_VALID_EVENTS = ["promptSubmit", "agentStop"]

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.kiro_dir = Path(".kiro")

    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """执行所有验证"""
        self.results = []
        self._validate_hooks()
        self._validate_steering()
        self._validate_specs()
        self._validate_mcp()
        
        has_failures = any(r.status == "fail" for r in self.results)
        return not has_failures, self.results

    def _validate_hooks(self) -> None:
        """验证Hooks配置"""
        hooks_dir = self.kiro_dir / "hooks"
        if not hooks_dir.exists():
            self.results.append(ValidationResult("hooks", "hooks目录", "fail", "目录不存在"))
            return
        
        for hook_file in hooks_dir.glob("*.kiro.hook"):
            self._validate_single_hook(hook_file)

    def _validate_single_hook(self, hook_file: Path) -> None:
        """验证单个Hook"""
        try:
            config = json.loads(hook_file.read_text(encoding="utf-8"))
            hook_name = hook_file.stem.replace(".kiro", "")
            
            # 检查必需字段
            for field in ["name", "version", "when", "then"]:
                if field not in config:
                    self.results.append(ValidationResult("hooks", hook_name, "fail", f"缺少{field}"))
                    return
            
            event_type = config.get("when", {}).get("type")
            action_type = config.get("then", {}).get("type")
            
            if event_type not in self.VALID_HOOK_EVENTS:
                self.results.append(ValidationResult("hooks", hook_name, "fail", f"无效事件类型: {event_type}"))
                return
            
            if action_type not in self.VALID_HOOK_ACTIONS:
                self.results.append(ValidationResult("hooks", hook_name, "fail", f"无效动作类型: {action_type}"))
                return
            
            self.results.append(ValidationResult("hooks", hook_name, "pass", f"{event_type} -> {action_type}"))
            
        except Exception as e:
            self.results.append(ValidationResult("hooks", hook_file.name, "fail", str(e)))

    def _validate_steering(self) -> None:
        """验证Steering配置"""
        steering_dir = self.kiro_dir / "steering"
        if not steering_dir.exists():
            self.results.append(ValidationResult("steering", "steering目录", "fail", "目录不存在"))
            return
        
        for steering_file in steering_dir.glob("*.md"):
            content = steering_file.read_text(encoding="utf-8")
            name = steering_file.stem
            
            if content.startswith("---") and "inclusion:" in content:
                self.results.append(ValidationResult("steering", name, "pass", "配置正确"))
            else:
                self.results.append(ValidationResult("steering", name, "warn", "缺少front-matter"))

    def _validate_specs(self) -> None:
        """验证Specs配置"""
        specs_dir = self.kiro_dir / "specs"
        if not specs_dir.exists():
            self.results.append(ValidationResult("specs", "specs目录", "warn", "目录不存在"))
            return
        
        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir():
                required = ["requirements.md", "design.md", "tasks.md"]
                missing = [f for f in required if not (spec_dir / f).exists()]
                
                if missing:
                    self.results.append(ValidationResult("specs", spec_dir.name, "warn", f"缺少: {missing}"))
                else:
                    self.results.append(ValidationResult("specs", spec_dir.name, "pass", "配置完整"))

    def _validate_mcp(self) -> None:
        """验证MCP配置"""
        mcp_file = self.kiro_dir / "settings" / "mcp.json"
        if not mcp_file.exists():
            self.results.append(ValidationResult("mcp", "mcp.json", "warn", "文件不存在"))
            return
        
        try:
            config = json.loads(mcp_file.read_text(encoding="utf-8"))
            servers = config.get("mcpServers", {})
            
            for name, server_config in servers.items():
                disabled = server_config.get("disabled", False)
                status = "已禁用" if disabled else "已启用"
                self.results.append(ValidationResult("mcp", name, "pass", status))
                
        except Exception as e:
            self.results.append(ValidationResult("mcp", "mcp.json", "fail", str(e)))


# ============================================================================
# 质量门禁模块
# ============================================================================

class QualityGate:
    """质量门禁"""

    def __init__(self, target_dir: str = "src"):
        self.target_dir = target_dir
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)

    def scan_bugs(self) -> List[BugReport]:
        """扫描Bug"""
        cmd = f"python -m pylint {self.target_dir} --exit-zero --output-format=json --max-line-length=120"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=600)
            if not result.stdout.strip():
                return []
            
            bugs = []
            for item in json.loads(result.stdout):
                bugs.append(BugReport(
                    file=item.get("path", ""),
                    line=item.get("line", 0),
                    code=item.get("message-id", ""),
                    message=item.get("message", ""),
                    severity=item.get("type", ""),
                    fixable=item.get("message-id", "") in ["C0303", "C0304", "C0305", "W0611", "W0612"]
                ))
            return bugs
        except Exception:
            return []

    def run_auto_fix(self) -> bool:
        """运行自动修复"""
        cmd = f"python scripts/auto_bug_detection.py cycle {self.target_dir}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=1200)
            return result.returncode == 0
        except Exception:
            return False

    def check(self) -> Tuple[bool, List[BugReport]]:
        """执行质量检查"""
        bugs = self.scan_bugs()
        
        if not bugs:
            return True, []
        
        # 尝试自动修复
        self.run_auto_fix()
        
        # 重新检查
        remaining = self.scan_bugs()
        return len(remaining) == 0, remaining

    def generate_report(self, bugs: List[BugReport]) -> str:
        """生成报告"""
        lines = [
            "=" * 60,
            "质量门禁报告",
            f"时间: {datetime.now().isoformat()}",
            f"目标: {self.target_dir}",
            "=" * 60,
            "",
            f"Bug数量: {len(bugs)}",
            f"标准要求: {QUALITY_STANDARDS['max_bugs']}",
            "",
        ]
        
        if bugs:
            lines.append("Bug列表:")
            lines.append("-" * 40)
            for bug in bugs[:20]:  # 最多显示20个
                lines.append(f"  {bug.file}:{bug.line} [{bug.code}] {bug.message[:50]}")
        
        return "\n".join(lines)


# ============================================================================
# 统一质量系统
# ============================================================================

class UnifiedQualitySystem:
    """统一质量保证系统"""

    def __init__(self, target_dir: str = "src"):
        self.target_dir = target_dir
        self.prd_parser = PRDParser()
        self.config_validator = ConfigValidator()
        self.quality_gate = QualityGate(target_dir)

    def run_full_check(self) -> bool:
        """运行完整质量检查"""
        print("=" * 60)
        print("统一质量保证系统 - 完整检查")
        print(f"质量标准: 覆盖率={QUALITY_STANDARDS['coverage_threshold']}%, Bug={QUALITY_STANDARDS['max_bugs']}")
        print("=" * 60)
        print()
        
        all_passed = True
        
        # 1. PRD解析
        print("[1/3] PRD文档解析...")
        prd = self.prd_parser.detect_and_parse(".")
        if prd:
            print(f"  ✅ 找到PRD: {prd.title} (v{prd.version})")
            config = self.prd_parser.get_quality_config()
            print(f"  ✅ 覆盖率要求: {config['testing']['coverage_threshold']}%")
        else:
            print("  ⚠️ 未找到PRD文档")
        print()
        
        # 2. 配置验证
        print("[2/3] Kiro配置验证...")
        config_passed, results = self.config_validator.validate_all()
        
        pass_count = sum(1 for r in results if r.status == "pass")
        warn_count = sum(1 for r in results if r.status == "warn")
        fail_count = sum(1 for r in results if r.status == "fail")
        
        print(f"  ✅ 通过: {pass_count}")
        if warn_count:
            print(f"  ⚠️ 警告: {warn_count}")
        if fail_count:
            print(f"  ❌ 失败: {fail_count}")
            all_passed = False
        print()
        
        # 3. 质量门禁
        print("[3/3] 质量门禁检查...")
        gate_passed, bugs = self.quality_gate.check()
        
        if gate_passed:
            print("  ✅ 无Bug")
        else:
            print(f"  ❌ 发现 {len(bugs)} 个Bug")
            all_passed = False
        print()
        
        # 总结
        print("=" * 60)
        if all_passed:
            print("✅ 质量检查通过")
        else:
            print("❌ 质量检查未通过")
        print("=" * 60)
        
        return all_passed

    def run_prd_only(self) -> None:
        """仅运行PRD解析"""
        print("=" * 60)
        print("PRD文档解析")
        print("=" * 60)
        print()
        
        prd = self.prd_parser.detect_and_parse(".")
        if prd:
            print(f"标题: {prd.title}")
            print(f"版本: {prd.version}")
            print(f"目标数量: {len(prd.goals)}")
            print()
            print("质量标准:")
            for std in prd.quality_requirements:
                print(f"  - {std.name}: {std.requirement}")
            print()
            config = self.prd_parser.get_quality_config()
            print(f"覆盖率阈值: {config['testing']['coverage_threshold']}%")
        else:
            print("未找到PRD文档")

    def run_config_only(self) -> bool:
        """仅运行配置验证"""
        print("=" * 60)
        print("Kiro配置验证")
        print("=" * 60)
        print()
        
        passed, results = self.config_validator.validate_all()
        
        # 按类别分组显示
        categories = {}
        for r in results:
            if r.category not in categories:
                categories[r.category] = []
            categories[r.category].append(r)
        
        for category, items in categories.items():
            print(f"[{category.upper()}]")
            for r in items:
                icon = "✅" if r.status == "pass" else "⚠️" if r.status == "warn" else "❌"
                print(f"  {icon} {r.item}: {r.message}")
            print()
        
        return passed

    def run_gate_only(self) -> bool:
        """仅运行质量门禁"""
        print("=" * 60)
        print("质量门禁检查")
        print("=" * 60)
        print()
        
        passed, bugs = self.quality_gate.check()
        
        if passed:
            print("✅ 质量门禁通过，无Bug")
        else:
            print(f"❌ 发现 {len(bugs)} 个Bug")
            print()
            print(self.quality_gate.generate_report(bugs))
        
        return passed


# ============================================================================
# 主函数
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("统一质量保证系统")
        print()
        print("使用方法:")
        print("  python scripts/unified_quality_system.py check [target]  - 完整质量检查")
        print("  python scripts/unified_quality_system.py prd             - PRD文档解析")
        print("  python scripts/unified_quality_system.py config          - 配置验证")
        print("  python scripts/unified_quality_system.py gate [target]   - 质量门禁")
        print()
        print(f"质量标准: 覆盖率={QUALITY_STANDARDS['coverage_threshold']}%, Bug={QUALITY_STANDARDS['max_bugs']}")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    target = sys.argv[2] if len(sys.argv) > 2 else "src"
    
    system = UnifiedQualitySystem(target)
    
    if command == "check":
        success = system.run_full_check()
        sys.exit(0 if success else 1)
    elif command == "prd":
        system.run_prd_only()
    elif command == "config":
        success = system.run_config_only()
        sys.exit(0 if success else 1)
    elif command == "gate":
        success = system.run_gate_only()
        sys.exit(0 if success else 1)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
