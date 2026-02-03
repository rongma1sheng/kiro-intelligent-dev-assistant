"""代码保留审计数据模型

白皮书依据: 待添加到白皮书

定义代码保留审计系统的核心数据模型，包括文件分类枚举、证据数据类、
依赖节点、分类结果、审计配置、审计报告和导出清单。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class FileClassification(Enum):
    """文件分类枚举

    白皮书依据: 待添加到白皮书

    定义文件的四种分类状态：
    - CORE: 核心文件，被入口引用、被测试覆盖、被PRD绑定
    - SUPPORTING: 支撑文件，被CORE依赖、用于配置/构建/部署
    - CANDIDATE: 可裁剪候选，未被引用、不在测试覆盖范围
    - BLOCKED: 裁决受阻，信息不足、依赖关系不明确
    """

    CORE = "core"
    SUPPORTING = "supporting"
    CANDIDATE = "candidate"
    BLOCKED = "blocked"

    def __str__(self) -> str:
        """返回分类的字符串表示"""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "FileClassification":
        """从字符串创建分类枚举

        Args:
            value: 分类字符串值

        Returns:
            对应的FileClassification枚举值

        Raises:
            ValueError: 当value不是有效的分类值时
        """
        value_lower = value.lower()
        for classification in cls:
            if classification.value == value_lower:
                return classification
        raise ValueError(f"无效的分类值: {value}，有效值为: {[c.value for c in cls]}")


@dataclass
class Evidence:
    """证据数据模型

    白皮书依据: 待添加到白皮书

    记录文件分类决策的证据，包括证据类型、来源、置信度和详细信息。

    Attributes:
        evidence_type: 证据类型，如 'import_reference', 'test_coverage', 'whitepaper_binding'
        source: 证据来源，如文件路径或分析工具名称
        confidence: 置信度，范围 [0.0, 1.0]
        details: 详细信息字典
        timestamp: 证据收集时间戳
    """

    evidence_type: str
    source: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self) -> None:
        """验证证据数据的有效性"""
        if not self.evidence_type:
            raise ValueError("evidence_type 不能为空")
        if not self.source:
            raise ValueError("source 不能为空")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence 必须在 [0.0, 1.0] 范围内，当前值: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            证据的字典表示
        """
        return {
            "type": self.evidence_type,
            "source": self.source,
            "confidence": self.confidence,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        """从字典创建Evidence实例

        Args:
            data: 包含证据信息的字典

        Returns:
            Evidence实例

        Raises:
            KeyError: 当缺少必要字段时
        """
        return cls(
            evidence_type=data.get("type", data.get("evidence_type", "")),
            source=data["source"],
            confidence=data["confidence"],
            details=data.get("details", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class DependencyNode:
    """依赖图节点

    白皮书依据: 待添加到白皮书

    表示依赖图中的一个文件节点，记录其导入关系和状态。

    Attributes:
        file_path: 文件路径
        imports: 该文件导入的文件路径列表
        imported_by: 导入该文件的文件路径列表
        is_entry_point: 是否为入口文件
        has_circular: 是否存在循环依赖
    """

    file_path: Path
    imports: List[Path] = field(default_factory=list)
    imported_by: List[Path] = field(default_factory=list)
    is_entry_point: bool = False
    has_circular: bool = False

    def __post_init__(self) -> None:
        """确保file_path是Path对象"""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        self.imports = [Path(p) if isinstance(p, str) else p for p in self.imports]
        self.imported_by = [Path(p) if isinstance(p, str) else p for p in self.imported_by]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            节点的字典表示
        """
        return {
            "file_path": str(self.file_path),
            "imports": [str(p) for p in self.imports],
            "imported_by": [str(p) for p in self.imported_by],
            "is_entry_point": self.is_entry_point,
            "has_circular": self.has_circular,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyNode":
        """从字典创建DependencyNode实例

        Args:
            data: 包含节点信息的字典

        Returns:
            DependencyNode实例
        """
        return cls(
            file_path=Path(data["file_path"]),
            imports=[Path(p) for p in data.get("imports", [])],
            imported_by=[Path(p) for p in data.get("imported_by", [])],
            is_entry_point=data.get("is_entry_point", False),
            has_circular=data.get("has_circular", False),
        )

    def add_import(self, imported_file: Path) -> None:
        """添加导入的文件

        Args:
            imported_file: 被导入的文件路径
        """
        if imported_file not in self.imports:
            self.imports.append(imported_file)

    def add_imported_by(self, importing_file: Path) -> None:
        """添加导入此文件的文件

        Args:
            importing_file: 导入此文件的文件路径
        """
        if importing_file not in self.imported_by:
            self.imported_by.append(importing_file)


@dataclass
class ClassificationResult:
    """分类结果

    白皮书依据: 待添加到白皮书

    记录单个文件的分类结果，包括分类、证据、置信度和建议操作。

    Attributes:
        file_path: 文件路径
        classification: 文件分类
        evidence_list: 支持该分类的证据列表
        confidence_score: 综合置信度分数
        deletion_impact: 删除影响评估（仅CANDIDATE文件）
        recommended_action: 建议操作
        blocked_reason: 阻塞原因（仅BLOCKED文件）
    """

    file_path: Path
    classification: FileClassification
    evidence_list: List[Evidence]
    confidence_score: float = 0.0
    deletion_impact: Optional[str] = None
    recommended_action: str = "RETAIN"
    blocked_reason: Optional[str] = None

    def __post_init__(self) -> None:
        """验证分类结果的有效性"""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        if isinstance(self.classification, str):
            self.classification = FileClassification.from_string(self.classification)
        if not self.evidence_list:
            raise ValueError("evidence_list 不能为空，每个分类必须有至少一条证据")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"confidence_score 必须在 [0.0, 1.0] 范围内，当前值: {self.confidence_score}")

        # CANDIDATE文件必须有deletion_impact
        if self.classification == FileClassification.CANDIDATE and self.deletion_impact is None:
            self.deletion_impact = "未评估删除影响"

        # BLOCKED文件必须有blocked_reason
        if self.classification == FileClassification.BLOCKED and self.blocked_reason is None:
            self.blocked_reason = "证据不足或依赖关系不明确"

        # 设置默认的recommended_action
        if self.recommended_action == "RETAIN":
            if self.classification == FileClassification.CANDIDATE:
                self.recommended_action = "REVIEW_FOR_DELETION"
            elif self.classification == FileClassification.BLOCKED:
                self.recommended_action = "MANUAL_REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            分类结果的字典表示
        """
        result = {
            "path": str(self.file_path),
            "classification": str(self.classification),
            "evidence": [e.to_dict() for e in self.evidence_list],
            "confidence_score": self.confidence_score,
            "recommended_action": self.recommended_action,
        }
        if self.deletion_impact is not None:
            result["deletion_impact"] = self.deletion_impact
        if self.blocked_reason is not None:
            result["blocked_reason"] = self.blocked_reason
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClassificationResult":
        """从字典创建ClassificationResult实例

        Args:
            data: 包含分类结果信息的字典

        Returns:
            ClassificationResult实例
        """
        evidence_list = [Evidence.from_dict(e) for e in data.get("evidence", [])]
        # 如果没有证据，创建一个默认证据以满足验证要求
        if not evidence_list:
            evidence_list = [
                Evidence(
                    evidence_type="loaded_from_report",
                    source="audit_report",
                    confidence=1.0,
                    details={"note": "从报告加载，原始证据未保存"},
                )
            ]

        return cls(
            file_path=Path(data["path"]),
            classification=FileClassification.from_string(data["classification"]),
            evidence_list=evidence_list,
            confidence_score=data.get("confidence_score", 0.0),
            deletion_impact=data.get("deletion_impact"),
            recommended_action=data.get("recommended_action", "RETAIN"),
            blocked_reason=data.get("blocked_reason"),
        )


@dataclass
class AuditConfig:
    """审计配置

    白皮书依据: 待添加到白皮书

    定义审计任务的配置参数。

    Attributes:
        root_path: 项目根目录
        entry_points: 入口文件列表
        whitepaper_path: 白皮书路径
        coverage_path: 覆盖率数据路径
        export_destination: 导出目标目录
        protected_patterns: 受保护文件模式列表
        exclude_patterns: 排除文件模式列表
        include_tests: 是否在导出中包含测试文件
    """

    root_path: Path
    entry_points: List[str] = field(
        default_factory=lambda: [
            "src/chronos/orchestrator.py",
            "src/brain/commander_engine_v2.py",
            "src/brain/soldier_engine_v2.py",
        ]
    )
    whitepaper_path: Path = field(default_factory=lambda: Path("00_核心文档/mia.md"))
    coverage_path: Optional[Path] = field(default_factory=lambda: Path("coverage.json"))
    export_destination: Optional[Path] = None
    protected_patterns: List[str] = field(
        default_factory=lambda: [
            "*.md",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.txt",
            "*.json",
            "__init__.py",
            "conftest.py",
        ]
    )
    exclude_patterns: List[str] = field(
        default_factory=lambda: [
            "__pycache__",
            "*.pyc",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".hypothesis",
            "htmlcov",
            "*.egg-info",
        ]
    )
    include_tests: bool = False

    def __post_init__(self) -> None:
        """确保路径是Path对象，设置默认导出目录"""
        if isinstance(self.root_path, str):
            self.root_path = Path(self.root_path)
        if isinstance(self.whitepaper_path, str):
            self.whitepaper_path = Path(self.whitepaper_path)
        if isinstance(self.coverage_path, str):
            self.coverage_path = Path(self.coverage_path)
        if self.export_destination is None:
            # 默认导出到桌面的 mia-verified-codebase 目录
            self.export_destination = Path.home() / "Desktop" / "mia-verified-codebase"
        elif isinstance(self.export_destination, str):
            self.export_destination = Path(self.export_destination)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            配置的字典表示
        """
        return {
            "root_path": str(self.root_path),
            "entry_points": self.entry_points,
            "whitepaper_path": str(self.whitepaper_path),
            "coverage_path": str(self.coverage_path) if self.coverage_path else None,
            "export_destination": str(self.export_destination) if self.export_destination else None,
            "protected_patterns": self.protected_patterns,
            "exclude_patterns": self.exclude_patterns,
            "include_tests": self.include_tests,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditConfig":
        """从字典创建AuditConfig实例

        Args:
            data: 包含配置信息的字典

        Returns:
            AuditConfig实例
        """
        return cls(
            root_path=Path(data["root_path"]),
            entry_points=data.get("entry_points", []),
            whitepaper_path=(
                Path(data["whitepaper_path"]) if data.get("whitepaper_path") else Path("00_核心文档/mia.md")
            ),
            coverage_path=Path(data["coverage_path"]) if data.get("coverage_path") else None,
            export_destination=Path(data["export_destination"]) if data.get("export_destination") else None,
            protected_patterns=data.get("protected_patterns", []),
            exclude_patterns=data.get("exclude_patterns", []),
            include_tests=data.get("include_tests", False),
        )


@dataclass
class AuditReport:
    """审计报告

    白皮书依据: 待添加到白皮书

    包含完整的审计结果，包括元数据、摘要、文件分类详情和人工审批队列。

    Attributes:
        metadata: 报告元数据
        summary: 分类摘要统计
        files: 文件分类结果列表
        human_review_queue: 需要人工审批的文件列表
    """

    metadata: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, int] = field(
        default_factory=lambda: {
            "core": 0,
            "supporting": 0,
            "candidate": 0,
            "blocked": 0,
        }
    )
    files: List[ClassificationResult] = field(default_factory=list)
    human_review_queue: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化默认元数据"""
        if not self.metadata:
            self.metadata = {
                "version": "1.0.0",
                "generated_at": datetime.now().isoformat(),
                "auditor_version": "1.0.0",
                "scan_scope": "",
                "total_files_scanned": 0,
            }

    def update_summary(self) -> None:
        """根据files列表更新摘要统计"""
        self.summary = {
            "core": 0,
            "supporting": 0,
            "candidate": 0,
            "blocked": 0,
        }
        for result in self.files:
            classification_key = result.classification.value
            self.summary[classification_key] = self.summary.get(classification_key, 0) + 1
        self.metadata["total_files_scanned"] = len(self.files)

    def update_human_review_queue(self) -> None:
        """根据files列表更新人工审批队列"""
        self.human_review_queue = []
        for result in self.files:
            if result.classification in (FileClassification.CANDIDATE, FileClassification.BLOCKED):
                self.human_review_queue.append(
                    {
                        "path": str(result.file_path),
                        "classification": str(result.classification),
                        "status": "pending",
                    }
                )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            报告的字典表示
        """
        return {
            "metadata": self.metadata,
            "summary": self.summary,
            "files": [f.to_dict() for f in self.files],
            "human_review_queue": self.human_review_queue,
        }

    def to_yaml(self) -> str:
        """转换为YAML格式字符串

        Returns:
            YAML格式的报告字符串
        """
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditReport":
        """从字典创建AuditReport实例

        Args:
            data: 包含报告信息的字典

        Returns:
            AuditReport实例
        """
        files = [ClassificationResult.from_dict(f) for f in data.get("files", [])]
        return cls(
            metadata=data.get("metadata", {}),
            summary=data.get("summary", {}),
            files=files,
            human_review_queue=data.get("human_review_queue", []),
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "AuditReport":
        """从YAML字符串创建AuditReport实例

        Args:
            yaml_content: YAML格式的报告字符串

        Returns:
            AuditReport实例
        """
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)

    def save(self, output_path: Path) -> None:
        """保存报告到文件

        Args:
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())

    @classmethod
    def load(cls, report_path: Path) -> "AuditReport":
        """从文件加载报告

        Args:
            report_path: 报告文件路径

        Returns:
            AuditReport实例

        Raises:
            FileNotFoundError: 当报告文件不存在时
        """
        report_path = Path(report_path)
        if not report_path.exists():
            raise FileNotFoundError(f"报告文件不存在: {report_path}")
        with open(report_path, "r", encoding="utf-8") as f:
            return cls.from_yaml(f.read())


@dataclass
class ExportManifest:
    """导出清单

    白皮书依据: 待添加到白皮书

    记录文件导出操作的详细信息。

    Attributes:
        export_time: 导出时间
        destination: 导出目标目录
        source_root: 源代码根目录
        total_files: 总文件数
        exported_files: 已导出文件列表
        skipped_files: 跳过的文件列表
    """

    export_time: str = field(default_factory=lambda: datetime.now().isoformat())
    destination: Path = field(default_factory=lambda: Path.home() / "Desktop" / "mia-verified-codebase")
    source_root: Path = field(default_factory=lambda: Path("."))
    total_files: int = 0
    exported_files: List[Dict[str, Any]] = field(default_factory=list)
    skipped_files: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """确保路径是Path对象"""
        if isinstance(self.destination, str):
            self.destination = Path(self.destination)
        if isinstance(self.source_root, str):
            self.source_root = Path(self.source_root)

    def add_exported_file(
        self,
        source: Path,
        destination: Path,
        classification: FileClassification,
        size_bytes: int,
    ) -> None:
        """添加已导出文件记录

        Args:
            source: 源文件路径
            destination: 目标文件路径
            classification: 文件分类
            size_bytes: 文件大小（字节）
        """
        self.exported_files.append(
            {
                "source": str(source),
                "destination": str(destination),
                "classification": str(classification),
                "size_bytes": size_bytes,
            }
        )
        self.total_files = len(self.exported_files)

    def add_skipped_file(
        self,
        path: Path,
        classification: FileClassification,
        reason: str,
    ) -> None:
        """添加跳过的文件记录

        Args:
            path: 文件路径
            classification: 文件分类
            reason: 跳过原因
        """
        self.skipped_files.append(
            {
                "path": str(path),
                "classification": str(classification),
                "reason": reason,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            清单的字典表示
        """
        return {
            "metadata": {
                "export_time": self.export_time,
                "destination": str(self.destination),
                "source_root": str(self.source_root),
            },
            "summary": {
                "total_files": self.total_files,
                "exported_files": len(self.exported_files),
                "skipped_files": len(self.skipped_files),
            },
            "exported_files": self.exported_files,
            "skipped_files": self.skipped_files,
        }

    def to_yaml(self) -> str:
        """转换为YAML格式字符串

        Returns:
            YAML格式的清单字符串
        """
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportManifest":
        """从字典创建ExportManifest实例

        Args:
            data: 包含清单信息的字典

        Returns:
            ExportManifest实例
        """
        metadata = data.get("metadata", {})
        summary = data.get("summary", {})
        return cls(
            export_time=metadata.get("export_time", datetime.now().isoformat()),
            destination=Path(metadata.get("destination", ".")),
            source_root=Path(metadata.get("source_root", ".")),
            total_files=summary.get("total_files", 0),
            exported_files=data.get("exported_files", []),
            skipped_files=data.get("skipped_files", []),
        )

    def save(self, output_path: Path) -> None:
        """保存清单到文件

        Args:
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())
