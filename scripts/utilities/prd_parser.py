#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PRD文档解析器 - 动态解析PRD文档提取质量标准

基于设计文档 .kiro/specs/unified-bug-detection-system/design.md
实现PRDEngine接口的完整功能

功能：
1. detectPRDDocument - 检测PRD文档位置
2. parsePRDContent - 解析PRD内容
3. extractQualityStandards - 提取质量标准
4. mapRequirementsToCode - 需求条款映射
"""

import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


@dataclass
class PRDLocation:
    """PRD文档位置"""
    path: str
    format: str  # markdown, yaml, json
    version: str = "unknown"


@dataclass
class Requirement:
    """需求条款"""
    id: str
    name: str
    description: str
    section: str
    acceptance_criteria: List[str] = field(default_factory=list)
    priority: str = "P1"


@dataclass
class QualityStandard:
    """质量标准"""
    category: str  # code_quality, security, performance, testing
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
    functional_requirements: List[Requirement]
    quality_requirements: List[QualityStandard]
    acceptance_criteria: List[str]
    technical_constraints: List[str]
    raw_content: str = ""


class PRDParser:
    """PRD文档解析器"""

    # PRD文档搜索路径
    PRD_SEARCH_PATHS = [
        "PRD.md",
        "prd.md",
        "docs/PRD.md",
        ".kiro/specs/*/requirements.md",
    ]

    def __init__(self):
        self.prd_location: Optional[PRDLocation] = None
        self.prd_document: Optional[PRDDocument] = None

    def detect_prd_document(self, project_path: str = ".") -> Optional[PRDLocation]:
        """检测PRD文档位置
        
        Args:
            project_path: 项目根目录
            
        Returns:
            PRDLocation或None
        """
        project = Path(project_path)
        
        # 直接路径检查
        for pattern in self.PRD_SEARCH_PATHS:
            if "*" in pattern:
                # glob模式
                matches = list(project.glob(pattern))
                if matches:
                    prd_path = matches[0]
                    return PRDLocation(
                        path=str(prd_path),
                        format="markdown",
                        version=self._extract_version(prd_path)
                    )
            else:
                prd_path = project / pattern
                if prd_path.exists():
                    return PRDLocation(
                        path=str(prd_path),
                        format="markdown",
                        version=self._extract_version(prd_path)
                    )
        
        return None

    def _extract_version(self, prd_path: Path) -> str:
        """从PRD文档提取版本号"""
        try:
            content = prd_path.read_text(encoding="utf-8")
            # 匹配版本号模式
            patterns = [
                r"版本[：:]\s*v?([\d.]+)",
                r"Version[：:]\s*v?([\d.]+)",
                r"v([\d.]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return "unknown"

    def parse_prd_content(self, prd_path: str) -> PRDDocument:
        """解析PRD文档内容
        
        Args:
            prd_path: PRD文档路径
            
        Returns:
            PRDDocument对象
        """
        path = Path(prd_path)
        if not path.exists():
            raise FileNotFoundError(f"PRD文档不存在: {prd_path}")
        
        content = path.read_text(encoding="utf-8")
        
        return PRDDocument(
            title=self._extract_title(content),
            version=self._extract_version(path),
            goals=self._extract_goals(content),
            functional_requirements=self._extract_functional_requirements(content),
            quality_requirements=self._extract_quality_requirements(content),
            acceptance_criteria=self._extract_acceptance_criteria(content),
            technical_constraints=self._extract_technical_constraints(content),
            raw_content=content
        )

    def _extract_title(self, content: str) -> str:
        """提取文档标题"""
        # 匹配一级标题
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "未命名PRD"

    def _extract_goals(self, content: str) -> List[str]:
        """提取产品目标"""
        goals = []
        
        # 查找目标章节
        goal_section = self._extract_section(content, r"(?:产品目标|核心目标|目标|Goals?)")
        if goal_section:
            # 提取列表项
            items = re.findall(r"[-*]\s+(.+)", goal_section)
            goals.extend(items)
            
            # 提取编号项
            numbered = re.findall(r"\d+\.\s+(.+)", goal_section)
            goals.extend(numbered)
        
        return goals

    def _extract_functional_requirements(self, content: str) -> List[Requirement]:
        """提取功能需求"""
        requirements = []
        
        # 查找功能需求章节
        func_section = self._extract_section(content, r"(?:功能需求|功能描述|Features?|Functional)")
        if func_section:
            # 提取子章节
            subsections = re.findall(r"###\s+(.+?)(?=###|\Z)", func_section, re.DOTALL)
            
            for i, subsection in enumerate(subsections):
                lines = subsection.strip().split("\n")
                if lines:
                    name = lines[0].strip()
                    description = "\n".join(lines[1:]).strip()
                    
                    # 提取验收标准
                    criteria = re.findall(r"[-*]\s*\[[ x]\]\s*(.+)", description)
                    
                    requirements.append(Requirement(
                        id=f"FR-{i+1:03d}",
                        name=name,
                        description=description,
                        section="功能需求",
                        acceptance_criteria=criteria
                    ))
        
        return requirements

    def _extract_quality_requirements(self, content: str) -> List[QualityStandard]:
        """提取质量要求"""
        standards = []
        
        # 查找质量要求章节
        quality_section = self._extract_section(content, r"(?:质量要求|质量标准|非功能需求|NFR|Quality)")
        if quality_section:
            # 提取测试覆盖率
            coverage_match = re.search(r"(?:测试覆盖率|覆盖率|coverage)[：:]\s*[≥>=]*\s*(\d+)%", 
                                       quality_section, re.IGNORECASE)
            if coverage_match:
                standards.append(QualityStandard(
                    category="testing",
                    name="测试覆盖率",
                    requirement=f"测试覆盖率 ≥ {coverage_match.group(1)}%",
                    threshold=coverage_match.group(1),
                    metric="percentage"
                ))
            
            # 提取圈复杂度
            complexity_match = re.search(r"(?:圈复杂度|复杂度|complexity)[：:]\s*[≤<=]*\s*(\d+)", 
                                         quality_section, re.IGNORECASE)
            if complexity_match:
                standards.append(QualityStandard(
                    category="code_quality",
                    name="圈复杂度",
                    requirement=f"圈复杂度 ≤ {complexity_match.group(1)}",
                    threshold=complexity_match.group(1),
                    metric="number"
                ))
            
            # 提取响应时间
            latency_match = re.search(r"(?:响应时间|延迟|latency)[：:]\s*[≤<=]*\s*(\d+)\s*(ms|秒|s)", 
                                      quality_section, re.IGNORECASE)
            if latency_match:
                standards.append(QualityStandard(
                    category="performance",
                    name="响应时间",
                    requirement=f"响应时间 ≤ {latency_match.group(1)}{latency_match.group(2)}",
                    threshold=latency_match.group(1),
                    metric="milliseconds"
                ))
            
            # 提取安全要求
            if re.search(r"(?:零漏洞|无漏洞|zero.?vulnerabilit)", quality_section, re.IGNORECASE):
                standards.append(QualityStandard(
                    category="security",
                    name="安全漏洞",
                    requirement="零安全漏洞",
                    threshold="0",
                    metric="count"
                ))
        
        return standards

    def _extract_acceptance_criteria(self, content: str) -> List[str]:
        """提取验收标准"""
        criteria = []
        
        # 查找验收标准章节
        accept_section = self._extract_section(content, r"(?:验收标准|验收条件|Acceptance)")
        if accept_section:
            # 提取复选框项
            checkboxes = re.findall(r"[-*]\s*\[[ x]\]\s*(.+)", accept_section)
            criteria.extend(checkboxes)
            
            # 提取普通列表项
            items = re.findall(r"[-*]\s+(?!\[)(.+)", accept_section)
            criteria.extend(items)
        
        return criteria

    def _extract_technical_constraints(self, content: str) -> List[str]:
        """提取技术约束"""
        constraints = []
        
        # 查找技术约束章节
        tech_section = self._extract_section(content, r"(?:技术约束|技术限制|约束条件|Constraints?)")
        if tech_section:
            items = re.findall(r"[-*]\s+(.+)", tech_section)
            constraints.extend(items)
            
            numbered = re.findall(r"\d+\.\s+(.+)", tech_section)
            constraints.extend(numbered)
        
        return constraints

    def _extract_section(self, content: str, section_pattern: str) -> str:
        """提取指定章节内容"""
        # 匹配章节标题
        pattern = rf"##\s*{section_pattern}.*?\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def extract_quality_standards(self, prd: PRDDocument) -> Dict[str, Any]:
        """提取质量标准配置
        
        Args:
            prd: PRD文档对象
            
        Returns:
            质量标准配置字典
        """
        config = {
            "code_quality": {
                "max_complexity": 10,
                "max_function_lines": 50,
                "max_class_lines": 300,
                "max_line_length": 120,
            },
            "security": {
                "vulnerability_tolerance": "zero",
                "required_scans": ["bandit"],
            },
            "performance": {
                "response_time_ms": 200,
                "memory_limit_mb": 512,
            },
            "testing": {
                "coverage_threshold": 100,  # 强制100%覆盖率
                "required_test_types": ["unit", "integration"],
            }
        }
        
        # 从PRD质量要求更新配置
        for standard in prd.quality_requirements:
            if standard.category == "testing" and standard.name == "测试覆盖率":
                try:
                    config["testing"]["coverage_threshold"] = int(standard.threshold)
                except ValueError:
                    pass
            elif standard.category == "code_quality" and standard.name == "圈复杂度":
                try:
                    config["code_quality"]["max_complexity"] = int(standard.threshold)
                except ValueError:
                    pass
            elif standard.category == "performance" and standard.name == "响应时间":
                try:
                    config["performance"]["response_time_ms"] = int(standard.threshold)
                except ValueError:
                    pass
        
        return config

    def map_requirements_to_code(self, prd: PRDDocument) -> Dict[str, List[str]]:
        """建立需求条款与代码的映射关系
        
        Args:
            prd: PRD文档对象
            
        Returns:
            需求ID到相关文件路径的映射
        """
        mapping = {}
        
        # 基于需求名称推断相关代码文件
        keyword_to_path = {
            "安全": ["src/**/security/**", "src/**/auth/**"],
            "性能": ["src/**/performance/**", "src/**/optimization/**"],
            "数据库": ["src/**/database/**", "src/**/db/**"],
            "UI": ["src/**/ui/**", "src/**/components/**"],
            "API": ["src/**/api/**", "src/**/routes/**"],
            "测试": ["tests/**"],
        }
        
        for req in prd.functional_requirements:
            related_paths = []
            for keyword, paths in keyword_to_path.items():
                if keyword in req.name or keyword in req.description:
                    related_paths.extend(paths)
            
            if not related_paths:
                related_paths = ["src/**"]
            
            mapping[req.id] = related_paths
        
        return mapping

    def generate_detection_config(self, prd: PRDDocument) -> Dict[str, Any]:
        """基于PRD生成检测配置
        
        Args:
            prd: PRD文档对象
            
        Returns:
            检测工具配置
        """
        standards = self.extract_quality_standards(prd)
        
        # 生成pylint配置
        pylint_config = {
            "max-line-length": standards["code_quality"]["max_line_length"],
            "max-args": 7,
            "max-locals": 15,
            "max-branches": standards["code_quality"]["max_complexity"],
            "max-statements": standards["code_quality"]["max_function_lines"],
        }
        
        # 生成bandit配置
        bandit_config = {
            "skips": [],
            "severity": "low" if standards["security"]["vulnerability_tolerance"] == "zero" else "medium",
        }
        
        return {
            "pylint": pylint_config,
            "bandit": bandit_config,
            "coverage": {
                "threshold": standards["testing"]["coverage_threshold"],
            }
        }


def main():
    """主函数 - 演示PRD解析功能"""
    parser = PRDParser()
    
    print("=" * 60)
    print("PRD文档解析器")
    print("=" * 60)
    print()
    
    # 检测PRD文档
    print("[1] 检测PRD文档...")
    location = parser.detect_prd_document(".")
    
    if not location:
        print("  [WARN] 未找到PRD文档")
        print("  请创建 PRD.md 或 .kiro/specs/*/requirements.md")
        return
    
    print(f"  [OK] 找到PRD: {location.path}")
    print(f"  版本: {location.version}")
    print()
    
    # 解析PRD内容
    print("[2] 解析PRD内容...")
    prd = parser.parse_prd_content(location.path)
    
    print(f"  标题: {prd.title}")
    print(f"  目标数量: {len(prd.goals)}")
    print(f"  功能需求: {len(prd.functional_requirements)}")
    print(f"  质量标准: {len(prd.quality_requirements)}")
    print(f"  验收标准: {len(prd.acceptance_criteria)}")
    print()
    
    # 提取质量标准
    print("[3] 提取质量标准...")
    standards = parser.extract_quality_standards(prd)
    print(f"  代码质量: {json.dumps(standards['code_quality'], indent=4, ensure_ascii=False)}")
    print(f"  测试要求: {json.dumps(standards['testing'], indent=4, ensure_ascii=False)}")
    print()
    
    # 生成检测配置
    print("[4] 生成检测配置...")
    config = parser.generate_detection_config(prd)
    print(f"  Pylint配置: {json.dumps(config['pylint'], indent=4)}")
    print(f"  覆盖率阈值: {config['coverage']['threshold']}%")
    print()
    
    print("=" * 60)
    print("[完成] PRD解析成功")
    print("=" * 60)


if __name__ == "__main__":
    main()
