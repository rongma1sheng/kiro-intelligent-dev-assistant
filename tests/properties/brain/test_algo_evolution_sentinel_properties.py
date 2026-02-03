"""AlgoEvolutionSentinel属性测试

白皮书依据: 第二章 2.5 AlgoEvolution Sentinel

属性测试验证通用正确性属性：
- Property 7: Paper filtering preserves relevant papers
- Property 8: High potential papers trigger translation
- Property 9: Translated algorithms undergo sandbox validation
- Property 10: Validated algorithms are integrated with events
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from typing import List

from src.brain.algo_evolution.algo_evolution_sentinel import (
    AlgoEvolutionSentinel,
    Paper,
    Algorithm
)
from src.infra.event_bus import EventBus, EventType


# 策略：生成论文数据
@st.composite
def paper_strategy(draw):
    """生成论文数据的策略"""
    # 关键词列表
    keywords = [
        'neural evolution', 'meta-learning', 'reinforcement learning',
        'transfer learning', 'few-shot learning', 'continual learning'
    ]
    
    # 随机选择是否包含关键词
    include_keyword = draw(st.booleans())
    
    if include_keyword:
        keyword = draw(st.sampled_from(keywords))
        title = f"Research on {keyword} and applications"
        abstract = f"This paper presents {keyword} approach for solving problems"
    else:
        title = draw(st.text(min_size=10, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))))
        abstract = draw(st.text(min_size=20, max_size=200, alphabet=st.characters(blacklist_categories=('Cs',))))
    
    return Paper(
        title=title,
        abstract=abstract,
        authors=draw(st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5)),
        url=f"http://example.com/paper{draw(st.integers(min_value=1, max_value=10000))}",
        source=draw(st.sampled_from(['arxiv', 'conference', 'journal', 'github'])),
        category=draw(st.sampled_from(['cs.LG', 'cs.AI', 'ICML', 'NeurIPS'])),
        published_date=draw(st.dates().map(str))
    )


class TestAlgoEvolutionSentinelProperties:
    """AlgoEvolutionSentinel属性测试"""
    
    @given(st.lists(paper_strategy(), min_size=0, max_size=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_7_paper_filtering_preserves_relevant_papers(self, papers: List[Paper]):
        """Property 7: Paper filtering preserves relevant papers
        
        **Validates: Requirements 3.2**
        
        属性：论文过滤保留所有相关论文
        
        对于任意论文列表，如果论文包含进化关键词，则过滤后的列表必须包含该论文。
        """
        sentinel = AlgoEvolutionSentinel()
        
        # 过滤论文
        relevant_papers = sentinel._filter_relevant_papers(papers)
        
        # 验证：所有包含关键词的论文都被保留
        for paper in papers:
            text = f"{paper.title} {paper.abstract}".lower()
            has_keyword = any(kw.lower() in text for kw in sentinel.evolution_keywords)
            
            if has_keyword:
                # 如果论文包含关键词，必须在过滤结果中
                assert paper in relevant_papers, \
                    f"论文 '{paper.title}' 包含关键词但未被过滤器保留"
        
        # 验证：过滤结果中的所有论文都包含关键词
        for paper in relevant_papers:
            text = f"{paper.title} {paper.abstract}".lower()
            has_keyword = any(kw.lower() in text for kw in sentinel.evolution_keywords)
            assert has_keyword, \
                f"论文 '{paper.title}' 不包含关键词但被过滤器保留"
    
    @given(st.lists(paper_strategy(), min_size=1, max_size=10))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_8_high_potential_papers_trigger_translation(self, papers: List[Paper]):
        """Property 8: High potential papers trigger translation
        
        **Validates: Requirements 3.3**
        
        属性：高潜力论文触发翻译
        
        对于任意论文，如果其潜力评分 > 0.7，则必须触发算法翻译。
        """
        sentinel = AlgoEvolutionSentinel()
        
        for paper in papers:
            # 分析论文
            analysis = await sentinel._analyze_paper(paper)
            
            # 如果潜力评分 > 0.7，验证翻译被触发
            if analysis['potential_score'] > 0.7:
                # 翻译论文
                algorithm = await sentinel._translate_to_algorithm(paper, analysis)
                
                # 验证：算法对象被创建
                assert isinstance(algorithm, Algorithm), \
                    "高潜力论文未触发算法翻译"
                assert algorithm.name == paper.title, \
                    "翻译的算法名称与论文标题不匹配"
                assert algorithm.source_paper == paper, \
                    "翻译的算法未关联源论文"
                assert algorithm.potential_score == analysis['potential_score'], \
                    "翻译的算法潜力评分不匹配"
    
    @given(st.lists(paper_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_9_translated_algorithms_undergo_sandbox_validation(self, papers: List[Paper]):
        """Property 9: Translated algorithms undergo sandbox validation
        
        **Validates: Requirements 3.4**
        
        属性：翻译的算法经过沙盒验证
        
        对于任意翻译的算法，必须经过沙盒验证才能集成。
        """
        sentinel = AlgoEvolutionSentinel()
        
        for paper in papers:
            # 分析论文
            analysis = await sentinel._analyze_paper(paper)
            
            # 翻译论文
            algorithm = await sentinel._translate_to_algorithm(paper, analysis)
            
            # 验证：算法必须经过沙盒验证
            validation_result = await sentinel._validate_in_sandbox(algorithm)
            
            # 验证：验证结果包含必要字段
            assert 'success' in validation_result, \
                "验证结果缺少 'success' 字段"
            assert 'function_score' in validation_result, \
                "验证结果缺少 'function_score' 字段"
            assert 'performance_score' in validation_result, \
                "验证结果缺少 'performance_score' 字段"
            assert 'comparison_score' in validation_result, \
                "验证结果缺少 'comparison_score' 字段"
            assert 'overall_score' in validation_result, \
                "验证结果缺少 'overall_score' 字段"
            
            # 验证：评分在有效范围内
            assert 0 <= validation_result['function_score'] <= 1, \
                "功能评分超出范围 [0, 1]"
            assert 0 <= validation_result['performance_score'] <= 1, \
                "性能评分超出范围 [0, 1]"
            assert 0 <= validation_result['comparison_score'] <= 1, \
                "对比评分超出范围 [0, 1]"
            assert 0 <= validation_result['overall_score'] <= 1, \
                "总体评分超出范围 [0, 1]"
    
    @given(st.lists(paper_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=500)
    @pytest.mark.asyncio
    async def test_property_10_validated_algorithms_are_integrated_with_events(self, papers: List[Paper]):
        """Property 10: Validated algorithms are integrated with events
        
        **Validates: Requirements 3.5**
        
        属性：验证通过的算法通过事件集成
        
        对于任意验证通过的算法，集成过程必须发布事件。
        """
        event_bus = EventBus()
        await event_bus.initialize()
        sentinel = AlgoEvolutionSentinel(event_bus=event_bus)
        
        # 记录发布的事件
        published_events = []
        
        async def event_handler(event):
            published_events.append(event)
        
        # 订阅事件
        await event_bus.subscribe(EventType.SYSTEM_ALERT, event_handler)
        
        for paper in papers:
            # 分析论文
            analysis = await sentinel._analyze_paper(paper)
            
            # 翻译论文
            algorithm = await sentinel._translate_to_algorithm(paper, analysis)
            
            # 创建验证成功的结果
            validation_result = {
                'success': True,
                'function_score': 0.8,
                'performance_score': 0.7,
                'comparison_score': 0.6,
                'overall_score': 0.7,
                'execution_time': 0.1,
                'memory_usage': 1000,
                'improvement_over_baseline': 0.5,
                'recommendations': []
            }
            
            # 评估集成价值
            integration_value = sentinel._assess_integration_value(algorithm, validation_result)
            
            # 如果集成价值足够高，验证事件被发布
            if integration_value >= 0.6:
                # 清空事件列表
                published_events.clear()
                
                # 集成算法
                await sentinel._integrate_algorithm(algorithm, validation_result)
                
                # 等待事件处理
                import asyncio
                await asyncio.sleep(0.1)
                
                # 验证：至少发布了一个事件
                assert len(published_events) > 0, \
                    "验证通过的算法集成时未发布事件"
                
                # 验证：事件包含正确的数据
                event = published_events[0]
                assert event.data['source'] == 'algo_evolution_sentinel', \
                    "事件来源不正确"
                assert event.data['action'] == 'algorithm_integrated', \
                    "事件动作不正确"
                assert event.data['algorithm_name'] == algorithm.name, \
                    "事件中的算法名称不匹配"
    
    @given(st.integers(min_value=1, max_value=3600))
    @settings(max_examples=20)
    def test_property_scan_interval_validation(self, scan_interval: int):
        """属性：扫描间隔验证
        
        对于任意正整数扫描间隔，初始化必须成功。
        """
        # 假设扫描间隔为正数
        assume(scan_interval > 0)
        
        # 创建哨兵
        sentinel = AlgoEvolutionSentinel(scan_interval=scan_interval)
        
        # 验证：扫描间隔被正确设置
        assert sentinel.scan_interval == scan_interval, \
            f"扫描间隔设置不正确: 期望 {scan_interval}, 实际 {sentinel.scan_interval}"
    
    @given(st.integers(min_value=-1000, max_value=0))
    @settings(max_examples=20)
    def test_property_invalid_scan_interval_raises_error(self, scan_interval: int):
        """属性：无效扫描间隔抛出错误
        
        对于任意非正整数扫描间隔，初始化必须抛出ValueError。
        """
        # 验证：无效扫描间隔抛出ValueError
        with pytest.raises(ValueError, match="扫描间隔必须 > 0"):
            AlgoEvolutionSentinel(scan_interval=scan_interval)
    
    @given(st.lists(paper_strategy(), min_size=0, max_size=50))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_filter_idempotence(self, papers: List[Paper]):
        """属性：过滤幂等性
        
        对于任意论文列表，多次过滤应该产生相同的结果。
        """
        sentinel = AlgoEvolutionSentinel()
        
        # 第一次过滤
        result1 = sentinel._filter_relevant_papers(papers)
        
        # 第二次过滤
        result2 = sentinel._filter_relevant_papers(papers)
        
        # 验证：两次过滤结果相同
        assert len(result1) == len(result2), \
            "多次过滤产生不同数量的结果"
        
        # 验证：结果中的论文相同
        for paper in result1:
            assert paper in result2, \
                f"论文 '{paper.title}' 在第二次过滤中丢失"
    
    @given(st.lists(paper_strategy(), min_size=0, max_size=20))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_filter_subset(self, papers: List[Paper]):
        """属性：过滤结果是输入的子集
        
        对于任意论文列表，过滤结果必须是输入的子集。
        """
        sentinel = AlgoEvolutionSentinel()
        
        # 过滤论文
        relevant_papers = sentinel._filter_relevant_papers(papers)
        
        # 验证：过滤结果是输入的子集
        for paper in relevant_papers:
            assert paper in papers, \
                f"过滤结果包含不在输入中的论文: '{paper.title}'"
        
        # 验证：过滤结果数量不超过输入
        assert len(relevant_papers) <= len(papers), \
            "过滤结果数量超过输入数量"
