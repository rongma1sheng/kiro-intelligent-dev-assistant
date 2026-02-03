"""算法进化数据模型单元测试

白皮书依据: 第二章 2.5 AlgoEvolution Sentinel
"""

import pytest
from datetime import datetime

from src.brain.algo_evolution.data_models import Paper, Algorithm


class TestPaper:
    """Paper数据模型测试"""
    
    def test_valid_paper(self):
        """测试有效的论文创建"""
        paper = Paper(
            title="Deep Learning for Quantitative Finance",
            authors=["John Doe", "Jane Smith"],
            abstract="This paper presents a novel approach...",
            url="https://arxiv.org/abs/2024.12345",
            published_date=datetime(2024, 1, 15),
            source='arxiv',
            keywords=['deep learning', 'quantitative finance', 'trading']
        )
        
        assert paper.title == "Deep Learning for Quantitative Finance"
        assert len(paper.authors) == 2
        assert paper.source == 'arxiv'
        assert len(paper.keywords) == 3
    
    def test_empty_title(self):
        """测试空标题"""
        with pytest.raises(ValueError, match="title不能为空"):
            Paper(
                title="",  # 空标题
                authors=["John Doe"],
                abstract="Abstract",
                url="https://arxiv.org/abs/2024.12345",
                published_date=datetime(2024, 1, 15),
                source='arxiv',
                keywords=['deep learning']
            )
    
    def test_empty_authors(self):
        """测试空作者列表"""
        with pytest.raises(ValueError, match="authors不能为空"):
            Paper(
                title="Title",
                authors=[],  # 空列表
                abstract="Abstract",
                url="https://arxiv.org/abs/2024.12345",
                published_date=datetime(2024, 1, 15),
                source='arxiv',
                keywords=['deep learning']
            )
    
    def test_invalid_source(self):
        """测试无效的来源"""
        with pytest.raises(ValueError, match="source必须是"):
            Paper(
                title="Title",
                authors=["John Doe"],
                abstract="Abstract",
                url="https://example.com",
                published_date=datetime(2024, 1, 15),
                source='invalid',  # 无效来源
                keywords=['deep learning']
            )
    
    def test_all_valid_sources(self):
        """测试所有有效来源"""
        for source in ['arxiv', 'github', 'conference']:
            paper = Paper(
                title="Title",
                authors=["John Doe"],
                abstract="Abstract",
                url="https://example.com",
                published_date=datetime(2024, 1, 15),
                source=source,
                keywords=['deep learning']
            )
            assert paper.source == source


class TestAlgorithm:
    """Algorithm数据模型测试"""
    
    def test_valid_algorithm(self):
        """测试有效的算法创建"""
        paper = Paper(
            title="Novel Algorithm",
            authors=["John Doe"],
            abstract="Abstract",
            url="https://arxiv.org/abs/2024.12345",
            published_date=datetime(2024, 1, 15),
            source='arxiv',
            keywords=['algorithm']
        )
        
        algorithm = Algorithm(
            name="NovelAlgorithm",
            source_paper=paper,
            core_algorithm="Core algorithm description",
            python_implementation="def algorithm(): pass",
            integration_interface="class Interface: pass",
            potential_score=0.8,
            complexity_score=0.6
        )
        
        assert algorithm.name == "NovelAlgorithm"
        assert algorithm.source_paper == paper
        assert algorithm.potential_score == 0.8
        assert algorithm.complexity_score == 0.6
    
    def test_empty_name(self):
        """测试空名称"""
        paper = Paper(
            title="Title",
            authors=["John Doe"],
            abstract="Abstract",
            url="https://arxiv.org/abs/2024.12345",
            published_date=datetime(2024, 1, 15),
            source='arxiv',
            keywords=['algorithm']
        )
        
        with pytest.raises(ValueError, match="name不能为空"):
            Algorithm(
                name="",  # 空名称
                source_paper=paper,
                core_algorithm="Core algorithm",
                python_implementation="def algorithm(): pass",
                integration_interface="class Interface: pass",
                potential_score=0.8,
                complexity_score=0.6
            )
    
    def test_invalid_potential_score(self):
        """测试无效的潜力评分"""
        paper = Paper(
            title="Title",
            authors=["John Doe"],
            abstract="Abstract",
            url="https://arxiv.org/abs/2024.12345",
            published_date=datetime(2024, 1, 15),
            source='arxiv',
            keywords=['algorithm']
        )
        
        with pytest.raises(ValueError, match="potential_score必须在"):
            Algorithm(
                name="Algorithm",
                source_paper=paper,
                core_algorithm="Core algorithm",
                python_implementation="def algorithm(): pass",
                integration_interface="class Interface: pass",
                potential_score=1.5,  # 超出范围
                complexity_score=0.6
            )
    
    def test_invalid_complexity_score(self):
        """测试无效的复杂度评分"""
        paper = Paper(
            title="Title",
            authors=["John Doe"],
            abstract="Abstract",
            url="https://arxiv.org/abs/2024.12345",
            published_date=datetime(2024, 1, 15),
            source='arxiv',
            keywords=['algorithm']
        )
        
        with pytest.raises(ValueError, match="complexity_score必须在"):
            Algorithm(
                name="Algorithm",
                source_paper=paper,
                core_algorithm="Core algorithm",
                python_implementation="def algorithm(): pass",
                integration_interface="class Interface: pass",
                potential_score=0.8,
                complexity_score=-0.1  # 超出范围
            )
    
    def test_boundary_scores(self):
        """测试边界评分"""
        paper = Paper(
            title="Title",
            authors=["John Doe"],
            abstract="Abstract",
            url="https://arxiv.org/abs/2024.12345",
            published_date=datetime(2024, 1, 15),
            source='arxiv',
            keywords=['algorithm']
        )
        
        # 最小值
        algo_min = Algorithm(
            name="Algorithm",
            source_paper=paper,
            core_algorithm="Core algorithm",
            python_implementation="def algorithm(): pass",
            integration_interface="class Interface: pass",
            potential_score=0.0,
            complexity_score=0.0
        )
        assert algo_min.potential_score == 0.0
        
        # 最大值
        algo_max = Algorithm(
            name="Algorithm",
            source_paper=paper,
            core_algorithm="Core algorithm",
            python_implementation="def algorithm(): pass",
            integration_interface="class Interface: pass",
            potential_score=1.0,
            complexity_score=1.0
        )
        assert algo_max.potential_score == 1.0
