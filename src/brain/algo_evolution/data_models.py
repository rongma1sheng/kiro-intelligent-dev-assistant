"""算法进化数据模型

白皮书依据: 第二章 2.5 AlgoEvolution Sentinel
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Paper:
    """学术论文

    白皮书依据: 第二章 2.5 AlgoEvolution Sentinel

    Attributes:
        title: 论文标题
        authors: 作者列表
        abstract: 摘要
        url: 论文URL
        published_date: 发布日期
        source: 来源，取值 'arxiv', 'github', 'conference'
        keywords: 关键词列表
    """

    title: str
    authors: List[str]
    abstract: str
    url: str
    published_date: datetime
    source: str
    keywords: List[str]

    def __post_init__(self):
        """验证参数"""
        if not self.title:
            raise ValueError("title不能为空")

        if not self.authors:
            raise ValueError("authors不能为空")

        if self.source not in ["arxiv", "github", "conference"]:
            raise ValueError(f"source必须是'arxiv', 'github'或'conference'，当前: {self.source}")


@dataclass
class Algorithm:
    """算法实现

    白皮书依据: 第二章 2.5 AlgoEvolution Sentinel

    Attributes:
        name: 算法名称
        source_paper: 源论文
        core_algorithm: 核心算法描述
        python_implementation: Python实现代码
        integration_interface: 集成接口代码
        potential_score: 潜力评分，范围 [0.0, 1.0]
        complexity_score: 复杂度评分，范围 [0.0, 1.0]
    """

    name: str
    source_paper: Paper
    core_algorithm: str
    python_implementation: str
    integration_interface: str
    potential_score: float
    complexity_score: float

    def __post_init__(self):
        """验证参数"""
        if not self.name:
            raise ValueError("name不能为空")

        if not 0.0 <= self.potential_score <= 1.0:
            raise ValueError(f"potential_score必须在[0.0, 1.0]范围内，当前: {self.potential_score}")

        if not 0.0 <= self.complexity_score <= 1.0:
            raise ValueError(f"complexity_score必须在[0.0, 1.0]范围内，当前: {self.complexity_score}")
