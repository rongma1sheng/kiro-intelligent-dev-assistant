"""
代码保留审计数据模型测试

测试覆盖:
- FileClassification枚举
- Evidence数据模型
- DependencyNode数据模型
- ClassificationResult数据模型
- AuditConfig数据模型
- AuditReport数据模型
- ExportManifest数据模型
"""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import tempfile
import yaml

from src.audit.retention.data_models import (
    FileClassification,
    Evidence,
    DependencyNode,
    ClassificationResult,
    AuditConfig,
    AuditReport,
    ExportManifest
)


class TestFileClassification:
    """文件分类枚举测试"""
    
    def test_file_classification_values(self):
        """测试文件分类枚举值"""
        assert FileClassification.CORE.value == "core"
        assert FileClassification.SUPPORTING.value == "supporting"
        assert FileClassification.CANDIDATE.value == "candidate"
        assert FileClassification.BLOCKED.value == "blocked"
    
    def test_file_classification_str(self):
        """测试文件分类字符串表示"""
        assert str(FileClassification.CORE) == "core"
        assert str(FileClassification.SUPPORTING) == "supporting"
        assert str(FileClassification.CANDIDATE) == "candidate"
        assert str(FileClassification.BLOCKED) == "blocked"
    
    def test_from_string_valid(self):
        """测试从有效字符串创建分类"""
        assert FileClassification.from_string("core") == FileClassification.CORE
        assert FileClassification.from_string("CORE") == FileClassification.CORE
        assert FileClassification.from_string("Core") == FileClassification.CORE
        assert FileClassification.from_string("supporting") == FileClassification.SUPPORTING
        assert FileClassification.from_string("candidate") == FileClassification.CANDIDATE
        assert FileClassification.from_string("blocked") == FileClassification.BLOCKED
    
    def test_from_string_invalid(self):
        """测试从无效字符串创建分类"""
        with pytest.raises(ValueError, match="无效的分类值"):
            FileClassification.from_string("invalid")
        
        with pytest.raises(ValueError, match="无效的分类值"):
            FileClassification.from_string("")


class TestEvidence:
    """证据数据模型测试"""
    
    def test_evidence_creation(self):
        """测试证据对象创建"""
        evidence = Evidence(
            evidence_type="import_reference",
            source="src/main.py",
            confidence=0.9,
            details={"line": 10, "import_statement": "from utils import helper"}
        )
        
        assert evidence.evidence_type == "import_reference"
        assert evidence.source == "src/main.py"
        assert evidence.confidence == 0.9
        assert evidence.details["line"] == 10
        assert evidence.timestamp is not None
    
    def test_evidence_defaults(self):
        """测试证据默认值"""
        evidence = Evidence(
            evidence_type="test_coverage",
            source="pytest",
            confidence=0.8
        )
        
        assert evidence.details == {}
        assert evidence.timestamp is not None
    
    def test_evidence_validation_empty_type(self):
        """测试空证据类型验证"""
        with pytest.raises(ValueError, match="evidence_type 不能为空"):
            Evidence(
                evidence_type="",
                source="test",
                confidence=0.5
            )
    
    def test_evidence_validation_empty_source(self):
        """测试空来源验证"""
        with pytest.raises(ValueError, match="source 不能为空"):
            Evidence(
                evidence_type="test",
                source="",
                confidence=0.5
            )
    
    def test_evidence_validation_confidence_range(self):
        """测试置信度范围验证"""
        with pytest.raises(ValueError, match="confidence 必须在"):
            Evidence(
                evidence_type="test",
                source="test",
                confidence=-0.1
            )
        
        with pytest.raises(ValueError, match="confidence 必须在"):
            Evidence(
                evidence_type="test",
                source="test",
                confidence=1.1
            )
    
    def test_evidence_to_dict(self):
        """测试证据转字典"""
        evidence = Evidence(
            evidence_type="whitepaper_binding",
            source="mia.md",
            confidence=0.95,
            details={"section": "1.2.3", "binding_type": "direct"},
            timestamp="2024-01-01T12:00:00"
        )
        
        result = evidence.to_dict()
        
        expected = {
            "type": "whitepaper_binding",
            "source": "mia.md",
            "confidence": 0.95,
            "details": {"section": "1.2.3", "binding_type": "direct"},
            "timestamp": "2024-01-01T12:00:00"
        }
        
        assert result == expected
    
    def test_evidence_from_dict(self):
        """测试从字典创建证据"""
        data = {
            "type": "test_coverage",
            "source": "pytest",
            "confidence": 0.85,
            "details": {"coverage_percent": 95},
            "timestamp": "2024-01-01T12:00:00"
        }
        
        evidence = Evidence.from_dict(data)
        
        assert evidence.evidence_type == "test_coverage"
        assert evidence.source == "pytest"
        assert evidence.confidence == 0.85
        assert evidence.details["coverage_percent"] == 95
        assert evidence.timestamp == "2024-01-01T12:00:00"
    
    def test_evidence_from_dict_legacy_type_field(self):
        """测试从包含legacy字段的字典创建证据"""
        data = {
            "evidence_type": "legacy_type",
            "source": "test",
            "confidence": 0.7
        }
        
        evidence = Evidence.from_dict(data)
        assert evidence.evidence_type == "legacy_type"
    
    def test_evidence_from_dict_missing_timestamp(self):
        """测试从缺少时间戳的字典创建证据"""
        data = {
            "type": "test",
            "source": "test",
            "confidence": 0.5
        }
        
        evidence = Evidence.from_dict(data)
        assert evidence.timestamp is not None


class TestDependencyNode:
    """依赖图节点测试"""
    
    def test_dependency_node_creation(self):
        """测试依赖节点创建"""
        node = DependencyNode(
            file_path=Path("src/main.py"),
            imports=[Path("src/utils.py"), Path("src/config.py")],
            imported_by=[Path("tests/test_main.py")],
            is_entry_point=True,
            has_circular=False
        )
        
        assert node.file_path == Path("src/main.py")
        assert len(node.imports) == 2
        assert Path("src/utils.py") in node.imports
        assert len(node.imported_by) == 1
        assert node.is_entry_point is True
        assert node.has_circular is False
    
    def test_dependency_node_defaults(self):
        """测试依赖节点默认值"""
        node = DependencyNode(file_path=Path("src/test.py"))
        
        assert node.imports == []
        assert node.imported_by == []
        assert node.is_entry_point is False
        assert node.has_circular is False
    
    def test_dependency_node_string_paths(self):
        """测试字符串路径自动转换"""
        node = DependencyNode(
            file_path="src/main.py",
            imports=["src/utils.py", "src/config.py"],
            imported_by=["tests/test_main.py"]
        )
        
        assert isinstance(node.file_path, Path)
        assert all(isinstance(p, Path) for p in node.imports)
        assert all(isinstance(p, Path) for p in node.imported_by)
    
    def test_dependency_node_add_import(self):
        """测试添加导入"""
        node = DependencyNode(file_path=Path("src/main.py"))
        
        node.add_import(Path("src/utils.py"))
        assert Path("src/utils.py") in node.imports
        
        # 重复添加不应该增加
        node.add_import(Path("src/utils.py"))
        assert len(node.imports) == 1
    
    def test_dependency_node_add_imported_by(self):
        """测试添加被导入记录"""
        node = DependencyNode(file_path=Path("src/utils.py"))
        
        node.add_imported_by(Path("src/main.py"))
        assert Path("src/main.py") in node.imported_by
        
        # 重复添加不应该增加
        node.add_imported_by(Path("src/main.py"))
        assert len(node.imported_by) == 1
    
    def test_dependency_node_to_dict(self):
        """测试依赖节点转字典"""
        node = DependencyNode(
            file_path=Path("src/main.py"),
            imports=[Path("src/utils.py")],
            imported_by=[Path("tests/test_main.py")],
            is_entry_point=True,
            has_circular=False
        )
        
        result = node.to_dict()
        
        # 使用Path对象来处理跨平台路径分隔符问题
        assert result["file_path"] == str(Path("src/main.py"))
        assert result["imports"] == [str(Path("src/utils.py"))]
        assert result["imported_by"] == [str(Path("tests/test_main.py"))]
        assert result["is_entry_point"] is True
        assert result["has_circular"] is False
    
    def test_dependency_node_from_dict(self):
        """测试从字典创建依赖节点"""
        data = {
            "file_path": "src/main.py",
            "imports": ["src/utils.py", "src/config.py"],
            "imported_by": ["tests/test_main.py"],
            "is_entry_point": True,
            "has_circular": False
        }
        
        node = DependencyNode.from_dict(data)
        
        assert node.file_path == Path("src/main.py")
        assert len(node.imports) == 2
        assert Path("src/utils.py") in node.imports
        assert len(node.imported_by) == 1
        assert node.is_entry_point is True
        assert node.has_circular is False


class TestClassificationResult:
    """分类结果测试"""
    
    def test_classification_result_creation(self):
        """测试分类结果创建"""
        evidence = Evidence("test_coverage", "pytest", 0.9)
        
        result = ClassificationResult(
            file_path=Path("src/main.py"),
            classification=FileClassification.CORE,
            evidence_list=[evidence],
            confidence_score=0.85,
            recommended_action="RETAIN"
        )
        
        assert result.file_path == Path("src/main.py")
        assert result.classification == FileClassification.CORE
        assert len(result.evidence_list) == 1
        assert result.confidence_score == 0.85
        assert result.recommended_action == "RETAIN"
    
    def test_classification_result_candidate_defaults(self):
        """测试CANDIDATE分类的默认值"""
        evidence = Evidence("no_references", "analyzer", 0.8)
        
        result = ClassificationResult(
            file_path=Path("src/unused.py"),
            classification=FileClassification.CANDIDATE,
            evidence_list=[evidence],
            confidence_score=0.8
        )
        
        assert result.deletion_impact == "未评估删除影响"
        assert result.recommended_action == "REVIEW_FOR_DELETION"
    
    def test_classification_result_blocked_defaults(self):
        """测试BLOCKED分类的默认值"""
        evidence = Evidence("insufficient_info", "analyzer", 0.3)
        
        result = ClassificationResult(
            file_path=Path("src/unclear.py"),
            classification=FileClassification.BLOCKED,
            evidence_list=[evidence],
            confidence_score=0.3
        )
        
        assert result.blocked_reason == "证据不足或依赖关系不明确"
        assert result.recommended_action == "MANUAL_REVIEW"
    
    def test_classification_result_string_conversion(self):
        """测试字符串分类自动转换"""
        evidence = Evidence("test", "test", 0.5)
        
        result = ClassificationResult(
            file_path="src/test.py",
            classification="core",
            evidence_list=[evidence],
            confidence_score=0.5
        )
        
        assert isinstance(result.file_path, Path)
        assert result.classification == FileClassification.CORE
    
    def test_classification_result_validation_empty_evidence(self):
        """测试空证据列表验证"""
        with pytest.raises(ValueError, match="evidence_list 不能为空"):
            ClassificationResult(
                file_path=Path("src/test.py"),
                classification=FileClassification.CORE,
                evidence_list=[],
                confidence_score=0.5
            )
    
    def test_classification_result_validation_confidence_range(self):
        """测试置信度范围验证"""
        evidence = Evidence("test", "test", 0.5)
        
        with pytest.raises(ValueError, match="confidence_score 必须在"):
            ClassificationResult(
                file_path=Path("src/test.py"),
                classification=FileClassification.CORE,
                evidence_list=[evidence],
                confidence_score=-0.1
            )
    
    def test_classification_result_to_dict(self):
        """测试分类结果转字典"""
        evidence = Evidence("test_coverage", "pytest", 0.9)
        
        result = ClassificationResult(
            file_path=Path("src/main.py"),
            classification=FileClassification.CORE,
            evidence_list=[evidence],
            confidence_score=0.85,
            recommended_action="RETAIN"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["path"] == str(Path("src/main.py"))
        assert result_dict["classification"] == "core"
        assert len(result_dict["evidence"]) == 1
        assert result_dict["confidence_score"] == 0.85
        assert result_dict["recommended_action"] == "RETAIN"
    
    def test_classification_result_from_dict(self):
        """测试从字典创建分类结果"""
        data = {
            "path": "src/main.py",
            "classification": "core",
            "evidence": [
                {
                    "type": "test_coverage",
                    "source": "pytest",
                    "confidence": 0.9,
                    "details": {},
                    "timestamp": "2024-01-01T12:00:00"
                }
            ],
            "confidence_score": 0.85,
            "recommended_action": "RETAIN"
        }
        
        result = ClassificationResult.from_dict(data)
        
        assert result.file_path == Path("src/main.py")
        assert result.classification == FileClassification.CORE
        assert len(result.evidence_list) == 1
        assert result.confidence_score == 0.85
        assert result.recommended_action == "RETAIN"
    
    def test_classification_result_from_dict_no_evidence(self):
        """测试从无证据字典创建分类结果"""
        data = {
            "path": "src/main.py",
            "classification": "core",
            "confidence_score": 0.85
        }
        
        result = ClassificationResult.from_dict(data)
        
        # 应该创建默认证据
        assert len(result.evidence_list) == 1
        assert result.evidence_list[0].evidence_type == "loaded_from_report"


class TestAuditConfig:
    """审计配置测试"""
    
    def test_audit_config_creation(self):
        """测试审计配置创建"""
        config = AuditConfig(
            root_path=Path("/project"),
            entry_points=["src/main.py"],
            whitepaper_path=Path("docs/whitepaper.md"),
            coverage_path=Path("coverage.json"),
            include_tests=True
        )
        
        assert config.root_path == Path("/project")
        assert config.entry_points == ["src/main.py"]
        assert config.whitepaper_path == Path("docs/whitepaper.md")
        assert config.coverage_path == Path("coverage.json")
        assert config.include_tests is True
    
    def test_audit_config_defaults(self):
        """测试审计配置默认值"""
        config = AuditConfig(root_path=Path("/project"))
        
        assert len(config.entry_points) == 3  # 默认入口点
        assert config.whitepaper_path == Path("00_核心文档/mia.md")
        assert config.coverage_path == Path("coverage.json")
        assert config.export_destination is not None
        assert len(config.protected_patterns) > 0
        assert len(config.exclude_patterns) > 0
        assert config.include_tests is False
    
    def test_audit_config_string_paths(self):
        """测试字符串路径自动转换"""
        config = AuditConfig(
            root_path="/project",
            whitepaper_path="docs/whitepaper.md",
            coverage_path="coverage.json"
        )
        
        assert isinstance(config.root_path, Path)
        assert isinstance(config.whitepaper_path, Path)
        assert isinstance(config.coverage_path, Path)
    
    def test_audit_config_to_dict(self):
        """测试审计配置转字典"""
        config = AuditConfig(
            root_path=Path("/project"),
            entry_points=["src/main.py"],
            include_tests=True
        )
        
        result = config.to_dict()
        
        assert result["root_path"] == str(Path("/project"))
        assert result["entry_points"] == ["src/main.py"]
        assert result["include_tests"] is True
        assert "protected_patterns" in result
        assert "exclude_patterns" in result
    
    def test_audit_config_from_dict(self):
        """测试从字典创建审计配置"""
        data = {
            "root_path": "/project",
            "entry_points": ["src/main.py"],
            "whitepaper_path": "docs/whitepaper.md",
            "coverage_path": "coverage.json",
            "include_tests": True,
            "protected_patterns": ["*.md"],
            "exclude_patterns": ["__pycache__"]
        }
        
        config = AuditConfig.from_dict(data)
        
        assert config.root_path == Path("/project")
        assert config.entry_points == ["src/main.py"]
        assert config.whitepaper_path == Path("docs/whitepaper.md")
        assert config.coverage_path == Path("coverage.json")
        assert config.include_tests is True
        assert config.protected_patterns == ["*.md"]
        assert config.exclude_patterns == ["__pycache__"]


class TestAuditReport:
    """审计报告测试"""
    
    def test_audit_report_creation(self):
        """测试审计报告创建"""
        evidence = Evidence("test", "test", 0.5)
        result = ClassificationResult(
            file_path=Path("src/main.py"),
            classification=FileClassification.CORE,
            evidence_list=[evidence],
            confidence_score=0.8
        )
        
        report = AuditReport(
            metadata={"version": "1.0.0"},
            summary={"core": 1, "supporting": 0, "candidate": 0, "blocked": 0},
            files=[result]
        )
        
        assert report.metadata["version"] == "1.0.0"
        assert report.summary["core"] == 1
        assert len(report.files) == 1
    
    def test_audit_report_defaults(self):
        """测试审计报告默认值"""
        report = AuditReport()
        
        assert "version" in report.metadata
        assert "generated_at" in report.metadata
        assert report.summary["core"] == 0
        assert report.files == []
        assert report.human_review_queue == []
    
    def test_audit_report_update_summary(self):
        """测试更新摘要统计"""
        evidence = Evidence("test", "test", 0.5)
        
        results = [
            ClassificationResult(
                file_path=Path("src/core.py"),
                classification=FileClassification.CORE,
                evidence_list=[evidence],
                confidence_score=0.8
            ),
            ClassificationResult(
                file_path=Path("src/support.py"),
                classification=FileClassification.SUPPORTING,
                evidence_list=[evidence],
                confidence_score=0.7
            ),
            ClassificationResult(
                file_path=Path("src/unused.py"),
                classification=FileClassification.CANDIDATE,
                evidence_list=[evidence],
                confidence_score=0.6
            )
        ]
        
        report = AuditReport(files=results)
        report.update_summary()
        
        assert report.summary["core"] == 1
        assert report.summary["supporting"] == 1
        assert report.summary["candidate"] == 1
        assert report.summary["blocked"] == 0
        assert report.metadata["total_files_scanned"] == 3
    
    def test_audit_report_update_human_review_queue(self):
        """测试更新人工审批队列"""
        evidence = Evidence("test", "test", 0.5)
        
        results = [
            ClassificationResult(
                file_path=Path("src/core.py"),
                classification=FileClassification.CORE,
                evidence_list=[evidence],
                confidence_score=0.8
            ),
            ClassificationResult(
                file_path=Path("src/unused.py"),
                classification=FileClassification.CANDIDATE,
                evidence_list=[evidence],
                confidence_score=0.6
            ),
            ClassificationResult(
                file_path=Path("src/unclear.py"),
                classification=FileClassification.BLOCKED,
                evidence_list=[evidence],
                confidence_score=0.3
            )
        ]
        
        report = AuditReport(files=results)
        report.update_human_review_queue()
        
        # 只有CANDIDATE和BLOCKED文件应该在队列中
        assert len(report.human_review_queue) == 2
        paths = [item["path"] for item in report.human_review_queue]
        assert str(Path("src/unused.py")) in paths
        assert str(Path("src/unclear.py")) in paths
        assert str(Path("src/core.py")) not in paths
    
    def test_audit_report_to_dict(self):
        """测试审计报告转字典"""
        evidence = Evidence("test", "test", 0.5)
        result = ClassificationResult(
            file_path=Path("src/main.py"),
            classification=FileClassification.CORE,
            evidence_list=[evidence],
            confidence_score=0.8
        )
        
        report = AuditReport(files=[result])
        result_dict = report.to_dict()
        
        assert "metadata" in result_dict
        assert "summary" in result_dict
        assert "files" in result_dict
        assert "human_review_queue" in result_dict
        assert len(result_dict["files"]) == 1
    
    def test_audit_report_to_yaml(self):
        """测试审计报告转YAML"""
        evidence = Evidence("test", "test", 0.5)
        result = ClassificationResult(
            file_path=Path("src/main.py"),
            classification=FileClassification.CORE,
            evidence_list=[evidence],
            confidence_score=0.8
        )
        
        report = AuditReport(files=[result])
        yaml_content = report.to_yaml()
        
        assert isinstance(yaml_content, str)
        assert "metadata:" in yaml_content
        assert "files:" in yaml_content
        
        # 验证YAML可以被解析
        parsed = yaml.safe_load(yaml_content)
        assert "metadata" in parsed
        assert "files" in parsed
    
    def test_audit_report_from_dict(self):
        """测试从字典创建审计报告"""
        data = {
            "metadata": {"version": "1.0.0"},
            "summary": {"core": 1, "supporting": 0, "candidate": 0, "blocked": 0},
            "files": [
                {
                    "path": "src/main.py",
                    "classification": "core",
                    "evidence": [
                        {
                            "type": "test",
                            "source": "test",
                            "confidence": 0.5,
                            "details": {},
                            "timestamp": "2024-01-01T12:00:00"
                        }
                    ],
                    "confidence_score": 0.8,
                    "recommended_action": "RETAIN"
                }
            ],
            "human_review_queue": []
        }
        
        report = AuditReport.from_dict(data)
        
        assert report.metadata["version"] == "1.0.0"
        assert report.summary["core"] == 1
        assert len(report.files) == 1
        assert report.files[0].file_path == Path("src/main.py")
    
    def test_audit_report_from_yaml(self):
        """测试从YAML创建审计报告"""
        yaml_content = """
metadata:
  version: "1.0.0"
summary:
  core: 1
  supporting: 0
  candidate: 0
  blocked: 0
files:
  - path: "src/main.py"
    classification: "core"
    evidence:
      - type: "test"
        source: "test"
        confidence: 0.5
        details: {}
        timestamp: "2024-01-01T12:00:00"
    confidence_score: 0.8
    recommended_action: "RETAIN"
human_review_queue: []
"""
        
        report = AuditReport.from_yaml(yaml_content)
        
        assert report.metadata["version"] == "1.0.0"
        assert report.summary["core"] == 1
        assert len(report.files) == 1
    
    def test_audit_report_save_and_load(self):
        """测试保存和加载报告"""
        evidence = Evidence("test", "test", 0.5)
        result = ClassificationResult(
            file_path=Path("src/main.py"),
            classification=FileClassification.CORE,
            evidence_list=[evidence],
            confidence_score=0.8
        )
        
        report = AuditReport(files=[result])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # 保存报告
            report.save(temp_path)
            assert temp_path.exists()
            
            # 加载报告
            loaded_report = AuditReport.load(temp_path)
            
            assert len(loaded_report.files) == 1
            assert loaded_report.files[0].file_path == Path("src/main.py")
            assert loaded_report.files[0].classification == FileClassification.CORE
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_audit_report_load_nonexistent(self):
        """测试加载不存在的报告文件"""
        with pytest.raises(FileNotFoundError, match="报告文件不存在"):
            AuditReport.load(Path("nonexistent.yaml"))


class TestExportManifest:
    """导出清单测试"""
    
    def test_export_manifest_creation(self):
        """测试导出清单创建"""
        manifest = ExportManifest(
            destination=Path("/export"),
            source_root=Path("/project"),
            total_files=10
        )
        
        assert manifest.destination == Path("/export")
        assert manifest.source_root == Path("/project")
        assert manifest.total_files == 10
        assert manifest.export_time is not None
    
    def test_export_manifest_defaults(self):
        """测试导出清单默认值"""
        manifest = ExportManifest()
        
        assert manifest.destination.name == "mia-verified-codebase"
        assert manifest.source_root == Path(".")
        assert manifest.total_files == 0
        assert manifest.exported_files == []
        assert manifest.skipped_files == []
    
    def test_export_manifest_string_paths(self):
        """测试字符串路径自动转换"""
        manifest = ExportManifest(
            destination="/export",
            source_root="/project"
        )
        
        assert isinstance(manifest.destination, Path)
        assert isinstance(manifest.source_root, Path)
    
    def test_export_manifest_add_exported_file(self):
        """测试添加已导出文件"""
        manifest = ExportManifest()
        
        manifest.add_exported_file(
            source=Path("src/main.py"),
            destination=Path("/export/src/main.py"),
            classification=FileClassification.CORE,
            size_bytes=1024
        )
        
        assert len(manifest.exported_files) == 1
        assert manifest.total_files == 1
        
        exported = manifest.exported_files[0]
        assert exported["source"] == str(Path("src/main.py"))
        assert exported["destination"] == str(Path("/export/src/main.py"))
        assert exported["classification"] == "core"
        assert exported["size_bytes"] == 1024
    
    def test_export_manifest_add_skipped_file(self):
        """测试添加跳过的文件"""
        manifest = ExportManifest()
        
        manifest.add_skipped_file(
            path=Path("src/unused.py"),
            classification=FileClassification.CANDIDATE,
            reason="标记为删除候选"
        )
        
        assert len(manifest.skipped_files) == 1
        
        skipped = manifest.skipped_files[0]
        assert skipped["path"] == str(Path("src/unused.py"))
        assert skipped["classification"] == "candidate"
        assert skipped["reason"] == "标记为删除候选"
    
    def test_export_manifest_to_dict(self):
        """测试导出清单转字典"""
        manifest = ExportManifest(
            destination=Path("/export"),
            source_root=Path("/project"),
            total_files=5
        )
        
        manifest.add_exported_file(
            source=Path("src/main.py"),
            destination=Path("/export/src/main.py"),
            classification=FileClassification.CORE,
            size_bytes=1024
        )
        
        result = manifest.to_dict()
        
        assert "metadata" in result
        assert "summary" in result
        assert "exported_files" in result
        assert "skipped_files" in result
        
        assert result["metadata"]["destination"] == str(Path("/export"))
        assert result["summary"]["exported_files"] == 1
        assert len(result["exported_files"]) == 1
    
    def test_export_manifest_to_yaml(self):
        """测试导出清单转YAML"""
        manifest = ExportManifest()
        yaml_content = manifest.to_yaml()
        
        assert isinstance(yaml_content, str)
        assert "metadata:" in yaml_content
        assert "summary:" in yaml_content
        
        # 验证YAML可以被解析
        parsed = yaml.safe_load(yaml_content)
        assert "metadata" in parsed
        assert "summary" in parsed
    
    def test_export_manifest_from_dict(self):
        """测试从字典创建导出清单"""
        data = {
            "metadata": {
                "export_time": "2024-01-01T12:00:00",
                "destination": "/export",
                "source_root": "/project"
            },
            "summary": {
                "total_files": 5,
                "exported_files": 3,
                "skipped_files": 2
            },
            "exported_files": [
                {
                    "source": "src/main.py",
                    "destination": "/export/src/main.py",
                    "classification": "core",
                    "size_bytes": 1024
                }
            ],
            "skipped_files": [
                {
                    "path": "src/unused.py",
                    "classification": "candidate",
                    "reason": "标记为删除"
                }
            ]
        }
        
        manifest = ExportManifest.from_dict(data)
        
        assert manifest.export_time == "2024-01-01T12:00:00"
        assert manifest.destination == Path("/export")
        assert manifest.source_root == Path("/project")
        assert manifest.total_files == 5
        assert len(manifest.exported_files) == 1
        assert len(manifest.skipped_files) == 1
    
    def test_export_manifest_save(self):
        """测试保存导出清单"""
        manifest = ExportManifest()
        manifest.add_exported_file(
            source=Path("src/main.py"),
            destination=Path("/export/src/main.py"),
            classification=FileClassification.CORE,
            size_bytes=1024
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            manifest.save(temp_path)
            assert temp_path.exists()
            
            # 验证文件内容
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "metadata:" in content
                assert "exported_files:" in content
        finally:
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])