"""Unit tests for CodeQualityChecker

白皮书依据: 第十四章 14.1.2 代码质量标准
目标覆盖率: 100%
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess

from src.quality.code_quality_checker import (
    CodeQualityChecker,
    QualityMetrics,
    ComplexityReport,
    StyleIssue,
    SecurityIssue
)


class TestCodeQualityChecker:
    """CodeQualityChecker单元测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        checker = CodeQualityChecker()
        
        assert checker.project_root == Path.cwd()
        assert checker.max_function_complexity == 10
        assert checker.max_class_complexity == 50
        assert checker.max_line_length == 120
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        custom_root = Path('/custom/root')
        checker = CodeQualityChecker(
            project_root=custom_root,
            max_function_complexity=15,
            max_class_complexity=60,
            max_line_length=100
        )
        
        assert checker.project_root == custom_root
        assert checker.max_function_complexity == 15
        assert checker.max_class_complexity == 60
        assert checker.max_line_length == 100
    
    def test_check_complexity_path_not_exists(self):
        """测试目标路径不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = CodeQualityChecker(project_root=Path(tmpdir))
            
            with pytest.raises(ValueError, match="目标路径不存在"):
                checker.check_complexity(Path(tmpdir) / 'nonexistent')
    
    @patch('subprocess.run')
    def test_check_complexity_success(self, mock_run):
        """测试成功检查圈复杂度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            # 模拟radon输出
            radon_output = json.dumps({
                'test.py': [
                    {'name': 'func1', 'complexity': 5, 'lineno': 10},
                    {'name': 'func2', 'complexity': 15, 'lineno': 20}
                ]
            })
            
            mock_run.return_value = Mock(returncode=0, stdout=radon_output, stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            reports = checker.check_complexity(src_dir)
            
            assert len(reports) == 2
            assert reports[0].function_name == 'func1'
            assert reports[0].complexity == 5
            assert reports[1].function_name == 'func2'
            assert reports[1].complexity == 15
    
    @patch('subprocess.run')
    def test_check_complexity_command_failed(self, mock_run):
        """测试radon命令执行失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            
            with pytest.raises(ValueError, match="radon执行失败"):
                checker.check_complexity(src_dir)
    
    @patch('subprocess.run')
    def test_check_complexity_timeout(self, mock_run):
        """测试radon命令超时"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            mock_run.side_effect = subprocess.TimeoutExpired('radon', 60)
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            
            with pytest.raises(ValueError, match="radon执行超时"):
                checker.check_complexity(src_dir)
    
    @patch('subprocess.run')
    def test_check_complexity_command_not_found(self, mock_run):
        """测试radon命令未找到"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            mock_run.side_effect = FileNotFoundError()
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            
            with pytest.raises(ValueError, match="radon命令未找到"):
                checker.check_complexity(src_dir)
    
    @patch('subprocess.run')
    def test_check_style_success(self, mock_run):
        """测试成功检查代码风格"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            # 模拟flake8输出（文本格式）
            flake8_output = "test.py:10:5: E501 line too long\ntest.py:20:1: W291 trailing whitespace"
            
            mock_run.return_value = Mock(returncode=1, stdout=flake8_output, stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            issues = checker.check_style(src_dir)
            
            assert len(issues) == 2
            assert issues[0].code == 'E501'
            assert issues[1].code == 'W291'
    
    @patch('subprocess.run')
    def test_check_style_no_issues(self, mock_run):
        """测试无代码风格问题"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            issues = checker.check_style(src_dir)
            
            assert len(issues) == 0
    
    @patch('subprocess.run')
    def test_check_types_success(self, mock_run):
        """测试成功检查类型注解"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            # 模拟mypy输出
            mypy_output = "test.py:10: error: Incompatible types\ntest.py:20: warning: Unused variable"
            
            mock_run.return_value = Mock(returncode=1, stdout=mypy_output, stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            result = checker.check_types(src_dir)
            
            assert result['errors'] == 1
            assert result['warnings'] == 1
            assert len(result['issues']) == 2
    
    @patch('subprocess.run')
    def test_check_types_no_errors(self, mock_run):
        """测试无类型错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            result = checker.check_types(src_dir)
            
            assert result['errors'] == 0
            assert result['warnings'] == 0
    
    @patch('subprocess.run')
    def test_check_security_success(self, mock_run):
        """测试成功检查安全问题"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            # 模拟bandit输出
            bandit_output = json.dumps({
                'results': [
                    {
                        'filename': 'test.py',
                        'line_number': 10,
                        'issue_severity': 'HIGH',
                        'issue_confidence': 'HIGH',
                        'issue_text': 'Hardcoded password',
                        'test_id': 'B105'
                    }
                ]
            })
            
            mock_run.return_value = Mock(returncode=1, stdout=bandit_output, stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            issues = checker.check_security(src_dir)
            
            assert len(issues) == 1
            assert issues[0].issue_severity == 'HIGH'
            assert issues[0].test_id == 'B105'
    
    @patch('subprocess.run')
    def test_check_security_no_issues(self, mock_run):
        """测试无安全问题"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            bandit_output = json.dumps({'results': []})
            
            mock_run.return_value = Mock(returncode=0, stdout=bandit_output, stderr='')
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            issues = checker.check_security(src_dir)
            
            assert len(issues) == 0
    
    @patch.object(CodeQualityChecker, 'check_complexity')
    @patch.object(CodeQualityChecker, 'check_style')
    @patch.object(CodeQualityChecker, 'check_types')
    @patch.object(CodeQualityChecker, 'check_security')
    def test_check_all_success(self, mock_security, mock_types, mock_style, mock_complexity):
        """测试执行所有质量检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            # 模拟各检查返回值
            mock_complexity.return_value = [
                ComplexityReport('test.py', 'func1', 5, 10)
            ]
            mock_style.return_value = []
            mock_types.return_value = {'errors': 0, 'warnings': 0, 'notes': 0, 'issues': []}
            mock_security.return_value = []
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            metrics = checker.check_all(src_dir)
            
            assert metrics.passed is True
            assert metrics.complexity_score >= 80.0
            assert metrics.style_score >= 80.0
            assert metrics.type_coverage >= 70.0
            assert metrics.security_issues == 0
    
    @patch.object(CodeQualityChecker, 'check_complexity')
    @patch.object(CodeQualityChecker, 'check_style')
    @patch.object(CodeQualityChecker, 'check_types')
    @patch.object(CodeQualityChecker, 'check_security')
    def test_check_all_with_issues(self, mock_security, mock_types, mock_style, mock_complexity):
        """测试有质量问题时的检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            # 模拟有问题的返回值
            mock_complexity.return_value = [
                ComplexityReport('test.py', 'func1', 15, 10)  # 高复杂度
            ]
            mock_style.return_value = [
                StyleIssue('test.py', 10, 5, 'E501', 'line too long', 'error')
            ]
            mock_types.return_value = {'errors': 5, 'warnings': 0, 'notes': 0, 'issues': []}
            mock_security.return_value = [
                SecurityIssue('test.py', 10, 'HIGH', 'HIGH', 'Hardcoded password', 'B105')
            ]
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            metrics = checker.check_all(src_dir)
            
            assert metrics.passed is False
            assert metrics.security_issues > 0
    
    @patch.object(CodeQualityChecker, 'check_complexity')
    def test_check_all_complexity_exception(self, mock_complexity):
        """测试圈复杂度检查异常"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            src_dir = tmpdir_path / 'src'
            src_dir.mkdir()
            
            mock_complexity.side_effect = Exception("Test error")
            
            checker = CodeQualityChecker(project_root=tmpdir_path)
            metrics = checker.check_all(src_dir)
            
            # 检查失败时评分为0
            assert metrics.complexity_score == 0.0
    
    def test_quality_metrics_dataclass(self):
        """测试QualityMetrics数据类"""
        metrics = QualityMetrics(
            complexity_score=90.0,
            style_score=85.0,
            type_coverage=80.0,
            security_issues=0,
            passed=True
        )
        
        assert metrics.complexity_score == 90.0
        assert metrics.style_score == 85.0
        assert metrics.type_coverage == 80.0
        assert metrics.security_issues == 0
        assert metrics.passed is True
    
    def test_complexity_report_dataclass(self):
        """测试ComplexityReport数据类"""
        report = ComplexityReport(
            file_path='test.py',
            function_name='test_func',
            complexity=10,
            line_number=50
        )
        
        assert report.file_path == 'test.py'
        assert report.function_name == 'test_func'
        assert report.complexity == 10
        assert report.line_number == 50
    
    def test_style_issue_dataclass(self):
        """测试StyleIssue数据类"""
        issue = StyleIssue(
            file_path='test.py',
            line_number=10,
            column=5,
            code='E501',
            message='line too long',
            severity='error'
        )
        
        assert issue.file_path == 'test.py'
        assert issue.line_number == 10
        assert issue.column == 5
        assert issue.code == 'E501'
        assert issue.message == 'line too long'
        assert issue.severity == 'error'
    
    def test_security_issue_dataclass(self):
        """测试SecurityIssue数据类"""
        issue = SecurityIssue(
            file_path='test.py',
            line_number=10,
            issue_severity='HIGH',
            issue_confidence='HIGH',
            issue_text='Hardcoded password',
            test_id='B105'
        )
        
        assert issue.file_path == 'test.py'
        assert issue.line_number == 10
        assert issue.issue_severity == 'HIGH'
        assert issue.issue_confidence == 'HIGH'
        assert issue.issue_text == 'Hardcoded password'
        assert issue.test_id == 'B105'
