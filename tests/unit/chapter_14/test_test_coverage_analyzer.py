"""Unit tests for TestCoverageAnalyzer

白皮书依据: 第十四章 14.1.1 测试覆盖率目标
目标覆盖率: 100%
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.quality.test_coverage_analyzer import (
    TestCoverageAnalyzer,
    CoverageReport,
    CoverageTarget
)


class TestTestCoverageAnalyzer:
    """TestCoverageAnalyzer单元测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.project_root == Path.cwd()
        assert isinstance(analyzer.coverage_targets, CoverageTarget)
        assert analyzer.coverage_data == {}
    
    def test_init_custom_root(self):
        """测试自定义项目根目录"""
        custom_root = Path('/custom/root')
        analyzer = TestCoverageAnalyzer(project_root=custom_root)
        
        assert analyzer.project_root == custom_root
    
    def test_analyze_coverage_file_not_found(self):
        """测试覆盖率文件不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = TestCoverageAnalyzer(project_root=Path(tmpdir))
            
            with pytest.raises(FileNotFoundError, match="覆盖率文件不存在"):
                analyzer.analyze_coverage()
    
    @patch('subprocess.run')
    def test_analyze_coverage_success(self, mock_run):
        """测试成功分析覆盖率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建.coverage文件
            coverage_file = tmpdir_path / '.coverage'
            coverage_file.touch()
            
            # 模拟coverage json输出
            coverage_json = {
                'files': {
                    str(tmpdir_path / 'src' / 'test.py'): {
                        'summary': {
                            'num_statements': 100,
                            'covered_lines': 85,
                            'num_branches': 20,
                            'covered_branches': 18
                        },
                        'missing_lines': [10, 20, 30]
                    }
                }
            }
            
            # 创建coverage.json文件
            json_path = tmpdir_path / 'coverage.json'
            with open(json_path, 'w') as f:
                json.dump(coverage_json, f)
            
            # 模拟subprocess.run
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            result = analyzer.analyze_coverage()
            
            assert len(result) == 1
            assert 'src.test' in result
            assert result['src.test'].coverage_percent == 85.0
    
    @patch('subprocess.run')
    def test_analyze_coverage_command_failed(self, mock_run):
        """测试coverage命令执行失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            coverage_file = tmpdir_path / '.coverage'
            coverage_file.touch()
            
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='Error')
            
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            with pytest.raises(ValueError, match="生成覆盖率报告失败"):
                analyzer.analyze_coverage()
    
    @patch('subprocess.run')
    def test_analyze_coverage_timeout(self, mock_run):
        """测试coverage命令超时"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            coverage_file = tmpdir_path / '.coverage'
            coverage_file.touch()
            
            mock_run.side_effect = subprocess.TimeoutExpired('coverage', 30)
            
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            with pytest.raises(ValueError, match="生成覆盖率报告超时"):
                analyzer.analyze_coverage()
    
    @patch('subprocess.run')
    def test_analyze_coverage_command_not_found(self, mock_run):
        """测试coverage命令未找到"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            coverage_file = tmpdir_path / '.coverage'
            coverage_file.touch()
            
            mock_run.side_effect = FileNotFoundError()
            
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            with pytest.raises(ValueError, match="coverage命令未找到"):
                analyzer.analyze_coverage()
    
    def test_get_module_category_core(self):
        """测试核心模块分类"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_module_category('src.brain.soldier') == 'core'
        assert analyzer.get_module_category('src.core.health_checker') == 'core'
    
    def test_get_module_category_execution(self):
        """测试执行模块分类"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_module_category('src.execution.order_manager') == 'execution'
    
    def test_get_module_category_infrastructure(self):
        """测试基础设施模块分类"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_module_category('src.infra.redis_pool') == 'infrastructure'
    
    def test_get_module_category_interface(self):
        """测试界面模块分类"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_module_category('src.interface.dashboard') == 'interface'
    
    def test_get_module_category_other(self):
        """测试其他模块分类"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_module_category('src.utils.helpers') == 'other'
    
    def test_get_category_coverage_empty(self):
        """测试空数据的类别覆盖率"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_category_coverage('core') == 0.0
    
    def test_get_category_coverage_with_data(self):
        """测试有数据的类别覆盖率"""
        analyzer = TestCoverageAnalyzer()
        
        analyzer.coverage_data['src.brain.soldier'] = CoverageReport(
            module_name='src.brain.soldier',
            total_statements=100,
            covered_statements=85,
            coverage_percent=85.0,
            missing_lines=[]
        )
        
        analyzer.coverage_data['src.core.health'] = CoverageReport(
            module_name='src.core.health',
            total_statements=50,
            covered_statements=45,
            coverage_percent=90.0,
            missing_lines=[]
        )
        
        # (85 + 45) / (100 + 50) * 100 = 86.67%
        coverage = analyzer.get_category_coverage('core')
        assert abs(coverage - 86.67) < 0.01
    
    def test_get_overall_coverage_empty(self):
        """测试空数据的总体覆盖率"""
        analyzer = TestCoverageAnalyzer()
        
        assert analyzer.get_overall_coverage() == 0.0
    
    def test_get_overall_coverage_with_data(self):
        """测试有数据的总体覆盖率"""
        analyzer = TestCoverageAnalyzer()
        
        analyzer.coverage_data['module1'] = CoverageReport(
            module_name='module1',
            total_statements=100,
            covered_statements=80,
            coverage_percent=80.0,
            missing_lines=[]
        )
        
        analyzer.coverage_data['module2'] = CoverageReport(
            module_name='module2',
            total_statements=50,
            covered_statements=40,
            coverage_percent=80.0,
            missing_lines=[]
        )
        
        # (80 + 40) / (100 + 50) * 100 = 80%
        assert analyzer.get_overall_coverage() == 80.0
    
    def test_enforce_coverage_gates_no_data(self):
        """测试未分析数据时执行门禁"""
        analyzer = TestCoverageAnalyzer()
        
        with pytest.raises(ValueError, match="覆盖率数据未分析"):
            analyzer.enforce_coverage_gates()
    
    def test_enforce_coverage_gates_all_pass(self):
        """测试所有门禁通过"""
        analyzer = TestCoverageAnalyzer()
        
        # 设置达标的覆盖率数据
        analyzer.coverage_data['src.brain.soldier'] = CoverageReport(
            module_name='src.brain.soldier',
            total_statements=100,
            covered_statements=90,
            coverage_percent=90.0,
            missing_lines=[]
        )
        
        analyzer.coverage_data['src.execution.order'] = CoverageReport(
            module_name='src.execution.order',
            total_statements=100,
            covered_statements=85,
            coverage_percent=85.0,
            missing_lines=[]
        )
        
        analyzer.coverage_data['src.infra.redis'] = CoverageReport(
            module_name='src.infra.redis',
            total_statements=100,
            covered_statements=80,
            coverage_percent=80.0,
            missing_lines=[]
        )
        
        analyzer.coverage_data['src.interface.api'] = CoverageReport(
            module_name='src.interface.api',
            total_statements=100,
            covered_statements=70,
            coverage_percent=70.0,
            missing_lines=[]
        )
        
        result = analyzer.enforce_coverage_gates()
        
        assert result['passed'] is True
        assert len(result['violations']) == 0
    
    def test_enforce_coverage_gates_core_fail(self):
        """测试核心模块覆盖率不达标"""
        analyzer = TestCoverageAnalyzer()
        
        analyzer.coverage_data['src.brain.soldier'] = CoverageReport(
            module_name='src.brain.soldier',
            total_statements=100,
            covered_statements=70,  # < 85%
            coverage_percent=70.0,
            missing_lines=[]
        )
        
        result = analyzer.enforce_coverage_gates()
        
        assert result['passed'] is False
        assert len(result['violations']) > 0
        assert any(v['category'] == 'core' for v in result['violations'])
    
    def test_generate_report_no_data(self):
        """测试未分析数据时生成报告"""
        analyzer = TestCoverageAnalyzer()
        
        with pytest.raises(ValueError, match="覆盖率数据未分析"):
            analyzer.generate_report()
    
    def test_generate_report_success(self):
        """测试成功生成报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = TestCoverageAnalyzer(project_root=Path(tmpdir))
            
            analyzer.coverage_data['module1'] = CoverageReport(
                module_name='module1',
                total_statements=100,
                covered_statements=80,
                coverage_percent=80.0,
                missing_lines=[1, 2, 3]
            )
            
            report_json = analyzer.generate_report()
            
            assert isinstance(report_json, str)
            report_data = json.loads(report_json)
            assert 'overall_coverage' in report_data
            assert 'category_coverage' in report_data
            assert 'modules' in report_data
    
    def test_generate_report_with_file(self):
        """测试生成报告到文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            analyzer = TestCoverageAnalyzer(project_root=tmpdir_path)
            
            analyzer.coverage_data['module1'] = CoverageReport(
                module_name='module1',
                total_statements=100,
                covered_statements=80,
                coverage_percent=80.0,
                missing_lines=[]
            )
            
            output_file = tmpdir_path / 'report.json'
            analyzer.generate_report(output_file=output_file)
            
            assert output_file.exists()
            with open(output_file) as f:
                report_data = json.load(f)
            assert 'overall_coverage' in report_data
    
    def test_identify_uncovered_code_no_data(self):
        """测试未分析数据时识别未覆盖代码"""
        analyzer = TestCoverageAnalyzer()
        
        with pytest.raises(ValueError, match="覆盖率数据未分析"):
            analyzer.identify_uncovered_code()
    
    def test_identify_uncovered_code_all_covered(self):
        """测试所有代码都已覆盖"""
        analyzer = TestCoverageAnalyzer()
        
        analyzer.coverage_data['module1'] = CoverageReport(
            module_name='module1',
            total_statements=100,
            covered_statements=100,
            coverage_percent=100.0,
            missing_lines=[]
        )
        
        uncovered = analyzer.identify_uncovered_code(min_coverage=80.0)
        
        assert len(uncovered) == 0
    
    def test_identify_uncovered_code_with_gaps(self):
        """测试识别未覆盖代码"""
        analyzer = TestCoverageAnalyzer()
        
        analyzer.coverage_data['src.brain.soldier'] = CoverageReport(
            module_name='src.brain.soldier',
            total_statements=100,
            covered_statements=70,
            coverage_percent=70.0,
            missing_lines=[1, 2, 3]
        )
        
        analyzer.coverage_data['src.execution.order'] = CoverageReport(
            module_name='src.execution.order',
            total_statements=50,
            covered_statements=30,
            coverage_percent=60.0,
            missing_lines=[10, 20]
        )
        
        uncovered = analyzer.identify_uncovered_code(min_coverage=80.0)
        
        assert len(uncovered) == 2
        # 核心模块优先级高
        assert uncovered[0]['priority'] == 'high'
        assert uncovered[0]['category'] == 'core'
    
    def test_coverage_target_defaults(self):
        """测试覆盖率目标默认值"""
        target = CoverageTarget()
        
        assert target.core_modules == 85.0
        assert target.execution_modules == 80.0
        assert target.infrastructure_modules == 75.0
        assert target.interface_modules == 60.0
        assert target.overall == 70.0
    
    def test_coverage_report_dataclass(self):
        """测试CoverageReport数据类"""
        report = CoverageReport(
            module_name='test_module',
            total_statements=100,
            covered_statements=85,
            coverage_percent=85.0,
            missing_lines=[1, 2, 3],
            branch_coverage=90.0
        )
        
        assert report.module_name == 'test_module'
        assert report.total_statements == 100
        assert report.covered_statements == 85
        assert report.coverage_percent == 85.0
        assert report.missing_lines == [1, 2, 3]
        assert report.branch_coverage == 90.0
