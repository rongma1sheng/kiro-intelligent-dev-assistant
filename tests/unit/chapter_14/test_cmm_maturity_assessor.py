"""Unit tests for CMMMaturityAssessor

白皮书依据: 第十四章 14.1.3 CMM成熟度模型
目标覆盖率: 100%
"""

import pytest
import tempfile
from pathlib import Path

from src.quality.cmm_maturity_assessor import (
    CMMMaturityAssessor,
    CMMLevel,
    DimensionScore,
    MaturityAssessment
)


class TestCMMMaturityAssessor:
    """CMMMaturityAssessor单元测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        assessor = CMMMaturityAssessor()
        
        assert assessor.project_root == Path.cwd()
        assert assessor.target_level == CMMLevel.DEFINED
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        custom_root = Path('/custom/root')
        assessor = CMMMaturityAssessor(
            project_root=custom_root,
            target_level=CMMLevel.MANAGED
        )
        
        assert assessor.project_root == custom_root
        assert assessor.target_level == CMMLevel.MANAGED
    
    def test_assess_maturity(self):
        """测试评估成熟度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建一些必要的目录和文件
            (tmpdir_path / 'src' / 'core').mkdir(parents=True)
            (tmpdir_path / 'tests' / 'unit').mkdir(parents=True)
            (tmpdir_path / '00_核心文档').mkdir(parents=True)
            (tmpdir_path / '00_核心文档' / 'mia.md').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            assessment = assessor.assess_maturity()
            
            assert isinstance(assessment, MaturityAssessment)
            assert isinstance(assessment.overall_level, CMMLevel)
            assert 0.0 <= assessment.overall_score <= 5.0
            assert len(assessment.dimension_scores) == 7
    
    def test_assess_reliability(self):
        """测试评估可靠性维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建相关文件
            (tmpdir_path / 'src' / 'core').mkdir(parents=True)
            (tmpdir_path / 'src' / 'core' / 'health_checker.py').touch()
            (tmpdir_path / 'src' / 'brain').mkdir(parents=True)
            (tmpdir_path / 'src' / 'brain' / 'soldier_failover.py').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_reliability()
            
            assert isinstance(score, DimensionScore)
            assert score.dimension_name == '可靠性'
            assert 0.0 <= score.score <= 5.0
            assert isinstance(score.level, CMMLevel)
    
    def test_assess_test_coverage(self):
        """测试评估测试覆盖维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建测试目录
            tests_dir = tmpdir_path / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'unit').mkdir()
            (tests_dir / 'integration').mkdir()
            (tests_dir / 'properties').mkdir()
            
            # 创建一些测试文件
            for i in range(60):
                (tests_dir / 'unit' / f'test_{i}.py').touch()
            
            for i in range(15):
                (tests_dir / 'integration' / f'test_{i}.py').touch()
            
            for i in range(10):
                (tests_dir / 'properties' / f'test_{i}.py').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_test_coverage()
            
            assert score.dimension_name == '测试覆盖'
            assert score.score > 0.0
            assert len(score.strengths) > 0
    
    def test_assess_monitoring(self):
        """测试评估监控体系维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建监控相关文件
            (tmpdir_path / 'src' / 'monitoring').mkdir(parents=True)
            (tmpdir_path / 'src' / 'monitoring' / 'prometheus_collector.py').touch()
            (tmpdir_path / 'monitoring').mkdir()
            (tmpdir_path / 'monitoring' / 'grafana_dashboard.json').touch()
            (tmpdir_path / 'logs').mkdir()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_monitoring()
            
            assert score.dimension_name == '监控体系'
            assert score.score > 0.0
    
    def test_assess_security(self):
        """测试评估安全合规维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建安全相关文件
            (tmpdir_path / 'src' / 'security').mkdir(parents=True)
            (tmpdir_path / 'src' / 'security' / 'unified_security_gateway.py').touch()
            (tmpdir_path / 'src' / 'security' / 'auth_manager.py').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_security()
            
            assert score.dimension_name == '安全合规'
            assert score.score > 0.0
    
    def test_assess_performance(self):
        """测试评估性能优化维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建性能相关文件
            (tmpdir_path / 'src' / 'optimization').mkdir(parents=True)
            (tmpdir_path / 'src' / 'optimization' / 'performance_optimizer.py').touch()
            (tmpdir_path / 'tests' / 'performance').mkdir(parents=True)
            for i in range(10):
                (tmpdir_path / 'tests' / 'performance' / f'test_{i}.py').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_performance()
            
            assert score.dimension_name == '性能优化'
            assert score.score > 0.0
    
    def test_assess_documentation(self):
        """测试评估文档完整维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建文档相关文件
            (tmpdir_path / '00_核心文档').mkdir()
            (tmpdir_path / '00_核心文档' / 'mia.md').touch()
            (tmpdir_path / '00_核心文档' / 'DEVELOPMENT_GUIDE.md').touch()
            (tmpdir_path / 'README.md').touch()
            (tmpdir_path / 'ARCHITECTURE_DESIGN.md').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_documentation()
            
            assert score.dimension_name == '文档完整'
            assert score.score > 0.0
    
    def test_assess_operations(self):
        """测试评估运维标准维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建运维相关文件
            (tmpdir_path / 'docker').mkdir()
            (tmpdir_path / 'docker' / 'docker-compose.yml').touch()
            (tmpdir_path / 'config').mkdir()
            (tmpdir_path / 'config' / 'app.yaml').touch()
            (tmpdir_path / 'data' / 'backups').mkdir(parents=True)
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            score = assessor._assess_operations()
            
            assert score.dimension_name == '运维标准'
            assert score.score > 0.0
    
    def test_score_to_level(self):
        """测试评分转换为CMM级别"""
        assessor = CMMMaturityAssessor()
        
        assert assessor._score_to_level(5.0) == CMMLevel.OPTIMIZING
        assert assessor._score_to_level(4.5) == CMMLevel.OPTIMIZING
        assert assessor._score_to_level(4.0) == CMMLevel.MANAGED
        assert assessor._score_to_level(3.5) == CMMLevel.MANAGED
        assert assessor._score_to_level(3.0) == CMMLevel.DEFINED
        assert assessor._score_to_level(2.5) == CMMLevel.DEFINED
        assert assessor._score_to_level(2.0) == CMMLevel.REPEATABLE
        assert assessor._score_to_level(1.5) == CMMLevel.REPEATABLE
        assert assessor._score_to_level(1.0) == CMMLevel.INITIAL
        assert assessor._score_to_level(0.0) == CMMLevel.INITIAL
    
    def test_calculate_overall_score_empty(self):
        """测试空数据的总体评分"""
        assessor = CMMMaturityAssessor()
        
        score = assessor.calculate_overall_score({})
        
        assert score == 0.0
    
    def test_calculate_overall_score_with_data(self):
        """测试有数据的总体评分"""
        assessor = CMMMaturityAssessor()
        
        dimension_scores = {
            'reliability': DimensionScore('可靠性', 3.0, CMMLevel.DEFINED, [], []),
            'test_coverage': DimensionScore('测试覆盖', 2.0, CMMLevel.REPEATABLE, [], []),
            'monitoring': DimensionScore('监控体系', 4.0, CMMLevel.MANAGED, [], [])
        }
        
        score = assessor.calculate_overall_score(dimension_scores)
        
        # (3.0 + 2.0 + 4.0) / 3 = 3.0
        assert score == 3.0
    
    def test_identify_gaps_no_gaps(self):
        """测试无差距情况"""
        assessor = CMMMaturityAssessor(target_level=CMMLevel.REPEATABLE)
        
        assessment = MaturityAssessment(
            overall_score=3.0,
            overall_level=CMMLevel.DEFINED,
            dimension_scores={
                'reliability': DimensionScore('可靠性', 3.0, CMMLevel.DEFINED, ['优势1'], [])
            },
            recommendations=[],
            target_level=CMMLevel.REPEATABLE
        )
        
        gaps = assessor.identify_gaps(assessment)
        
        assert len(gaps) == 0
    
    def test_identify_gaps_with_gaps(self):
        """测试有差距情况"""
        assessor = CMMMaturityAssessor(target_level=CMMLevel.DEFINED)
        
        assessment = MaturityAssessment(
            overall_score=2.0,
            overall_level=CMMLevel.REPEATABLE,
            dimension_scores={
                'reliability': DimensionScore(
                    '可靠性',
                    2.0,
                    CMMLevel.REPEATABLE,
                    [],
                    ['缺少Redis高可用', '缺少监控告警']
                )
            },
            recommendations=[],
            target_level=CMMLevel.DEFINED
        )
        
        gaps = assessor.identify_gaps(assessment)
        
        assert len(gaps) == 2
        # gap格式为 "[dimension_key] gap_message"，其中dimension_key是英文key
        assert '[reliability]' in gaps[0]
        assert '缺少Redis高可用' in gaps[0]
    
    def test_generate_recommendations_at_target(self):
        """测试已达目标级别的建议生成"""
        assessor = CMMMaturityAssessor(target_level=CMMLevel.DEFINED)
        
        dimension_scores = {
            'reliability': DimensionScore('可靠性', 3.0, CMMLevel.DEFINED, [], [])
        }
        
        recommendations = assessor._generate_recommendations(
            dimension_scores,
            CMMLevel.DEFINED
        )
        
        # 已达目标，建议较少
        assert isinstance(recommendations, list)
    
    def test_generate_recommendations_below_target(self):
        """测试低于目标级别的建议生成"""
        assessor = CMMMaturityAssessor(target_level=CMMLevel.DEFINED)
        
        dimension_scores = {
            'reliability': DimensionScore(
                '可靠性',
                2.0,
                CMMLevel.REPEATABLE,
                [],
                ['缺少Redis高可用', '缺少监控告警', '缺少热备切换']
            )
        }
        
        recommendations = assessor._generate_recommendations(
            dimension_scores,
            CMMLevel.REPEATABLE
        )
        
        assert len(recommendations) > 0
        assert any('提升' in r for r in recommendations)
    
    def test_cmm_level_enum(self):
        """测试CMMLevel枚举"""
        assert CMMLevel.INITIAL.value == 1
        assert CMMLevel.REPEATABLE.value == 2
        assert CMMLevel.DEFINED.value == 3
        assert CMMLevel.MANAGED.value == 4
        assert CMMLevel.OPTIMIZING.value == 5
    
    def test_dimension_score_dataclass(self):
        """测试DimensionScore数据类"""
        score = DimensionScore(
            dimension_name='测试维度',
            score=3.5,
            level=CMMLevel.MANAGED,
            strengths=['优势1', '优势2'],
            gaps=['差距1']
        )
        
        assert score.dimension_name == '测试维度'
        assert score.score == 3.5
        assert score.level == CMMLevel.MANAGED
        assert len(score.strengths) == 2
        assert len(score.gaps) == 1
    
    def test_maturity_assessment_dataclass(self):
        """测试MaturityAssessment数据类"""
        dimension_scores = {
            'reliability': DimensionScore('可靠性', 3.0, CMMLevel.DEFINED, [], [])
        }
        
        assessment = MaturityAssessment(
            overall_score=3.0,
            overall_level=CMMLevel.DEFINED,
            dimension_scores=dimension_scores,
            recommendations=['建议1', '建议2'],
            target_level=CMMLevel.MANAGED
        )
        
        assert assessment.overall_score == 3.0
        assert assessment.overall_level == CMMLevel.DEFINED
        assert len(assessment.dimension_scores) == 1
        assert len(assessment.recommendations) == 2
        assert assessment.target_level == CMMLevel.MANAGED
    
    def test_assess_maturity_comprehensive(self):
        """测试综合成熟度评估"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # 创建完整的项目结构
            # 可靠性
            (tmpdir_path / 'src' / 'core').mkdir(parents=True)
            (tmpdir_path / 'src' / 'core' / 'health_checker.py').touch()
            (tmpdir_path / 'src' / 'brain').mkdir(parents=True)
            (tmpdir_path / 'src' / 'brain' / 'soldier_failover.py').touch()
            
            # 测试覆盖
            (tmpdir_path / 'tests' / 'unit').mkdir(parents=True)
            for i in range(60):
                (tmpdir_path / 'tests' / 'unit' / f'test_{i}.py').touch()
            
            # 监控
            (tmpdir_path / 'src' / 'monitoring').mkdir(parents=True)
            (tmpdir_path / 'src' / 'monitoring' / 'prometheus_collector.py').touch()
            
            # 安全
            (tmpdir_path / 'src' / 'security').mkdir(parents=True)
            (tmpdir_path / 'src' / 'security' / 'unified_security_gateway.py').touch()
            
            # 性能
            (tmpdir_path / 'src' / 'optimization').mkdir(parents=True)
            (tmpdir_path / 'src' / 'optimization' / 'performance_optimizer.py').touch()
            
            # 文档
            (tmpdir_path / '00_核心文档').mkdir()
            (tmpdir_path / '00_核心文档' / 'mia.md').touch()
            (tmpdir_path / 'README.md').touch()
            
            # 运维
            (tmpdir_path / 'docker').mkdir()
            (tmpdir_path / 'docker' / 'docker-compose.yml').touch()
            
            assessor = CMMMaturityAssessor(project_root=tmpdir_path)
            assessment = assessor.assess_maturity()
            
            # 验证所有维度都被评估
            assert len(assessment.dimension_scores) == 7
            assert 'reliability' in assessment.dimension_scores
            assert 'test_coverage' in assessment.dimension_scores
            assert 'monitoring' in assessment.dimension_scores
            assert 'security' in assessment.dimension_scores
            assert 'performance' in assessment.dimension_scores
            assert 'documentation' in assessment.dimension_scores
            assert 'operations' in assessment.dimension_scores
            
            # 验证总体评分合理
            assert 0.0 <= assessment.overall_score <= 5.0
            assert isinstance(assessment.overall_level, CMMLevel)
            
            # 验证建议列表
            assert isinstance(assessment.recommendations, list)
