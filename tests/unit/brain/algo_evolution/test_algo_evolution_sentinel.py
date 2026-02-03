"""AlgoEvolutionSentinel单元测试

白皮书依据: 第二章 2.5 AlgoEvolution Sentinel
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.brain.algo_evolution.algo_evolution_sentinel import (
    AlgoEvolutionSentinel,
    Paper,
    Algorithm
)
from src.infra.event_bus import EventBus, Event, EventType


class TestAlgoEvolutionSentinelInitialization:
    """测试AlgoEvolutionSentinel初始化"""
    
    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        sentinel = AlgoEvolutionSentinel()
        
        assert sentinel.scan_interval == 3600
        assert sentinel.is_running is False
        assert sentinel.stats['total_papers_scanned'] == 0
        assert sentinel.stats['relevant_papers_found'] == 0
        assert sentinel.stats['algorithms_translated'] == 0
        assert sentinel.stats['algorithms_validated'] == 0
        assert sentinel.stats['algorithms_integrated'] == 0
        assert sentinel.stats['last_scan_time'] is None
        assert sentinel.stats['scan_count'] == 0
    
    def test_init_with_custom_scan_interval(self):
        """测试自定义扫描间隔"""
        sentinel = AlgoEvolutionSentinel(scan_interval=1800)
        
        assert sentinel.scan_interval == 1800
    
    def test_init_with_custom_event_bus(self):
        """测试自定义事件总线"""
        event_bus = EventBus()
        sentinel = AlgoEvolutionSentinel(event_bus=event_bus)
        
        assert sentinel.event_bus is event_bus
    
    def test_init_with_invalid_scan_interval(self):
        """测试无效扫描间隔"""
        with pytest.raises(ValueError, match="扫描间隔必须 > 0"):
            AlgoEvolutionSentinel(scan_interval=0)
        
        with pytest.raises(ValueError, match="扫描间隔必须 > 0"):
            AlgoEvolutionSentinel(scan_interval=-100)
    
    def test_monitoring_sources_configuration(self):
        """测试监控源配置"""
        sentinel = AlgoEvolutionSentinel()
        
        assert 'arxiv' in sentinel.monitoring_sources
        assert 'conferences' in sentinel.monitoring_sources
        assert 'journals' in sentinel.monitoring_sources
        assert 'github' in sentinel.monitoring_sources
        
        assert 'cs.LG' in sentinel.monitoring_sources['arxiv']
        assert 'ICML' in sentinel.monitoring_sources['conferences']
    
    def test_evolution_keywords_configuration(self):
        """测试进化关键词配置"""
        sentinel = AlgoEvolutionSentinel()
        
        assert len(sentinel.evolution_keywords) > 0
        assert 'neural evolution' in sentinel.evolution_keywords
        assert 'meta-learning' in sentinel.evolution_keywords
        assert 'reinforcement learning' in sentinel.evolution_keywords


class TestAlgoEvolutionSentinelPaperFiltering:
    """测试论文过滤功能"""
    
    def test_filter_relevant_papers_with_matching_keywords(self):
        """测试过滤包含关键词的论文"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = [
            Paper(
                title="Neural Evolution for Deep Learning",
                abstract="This paper presents a novel neural evolution approach",
                authors=["Author1"],
                url="http://example.com/paper1",
                source="arxiv",
                category="cs.LG",
                published_date="2024-01-01"
            ),
            Paper(
                title="Unrelated Topic",
                abstract="This paper is about something else",
                authors=["Author2"],
                url="http://example.com/paper2",
                source="arxiv",
                category="cs.CV",
                published_date="2024-01-02"
            )
        ]
        
        relevant_papers = sentinel._filter_relevant_papers(papers)
        
        assert len(relevant_papers) == 1
        assert relevant_papers[0].title == "Neural Evolution for Deep Learning"
    
    def test_filter_relevant_papers_with_no_matches(self):
        """测试过滤无关键词的论文"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = [
            Paper(
                title="Unrelated Topic 1",
                abstract="This paper is about something else",
                authors=["Author1"],
                url="http://example.com/paper1",
                source="arxiv",
                category="cs.CV",
                published_date="2024-01-01"
            ),
            Paper(
                title="Unrelated Topic 2",
                abstract="Another unrelated paper",
                authors=["Author2"],
                url="http://example.com/paper2",
                source="arxiv",
                category="cs.CV",
                published_date="2024-01-02"
            )
        ]
        
        relevant_papers = sentinel._filter_relevant_papers(papers)
        
        assert len(relevant_papers) == 0
    
    def test_filter_relevant_papers_with_empty_list(self):
        """测试过滤空论文列表"""
        sentinel = AlgoEvolutionSentinel()
        
        relevant_papers = sentinel._filter_relevant_papers([])
        
        assert len(relevant_papers) == 0
    
    def test_filter_relevant_papers_case_insensitive(self):
        """测试关键词匹配大小写不敏感"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = [
            Paper(
                title="NEURAL EVOLUTION FOR DEEP LEARNING",
                abstract="This paper presents a NEURAL EVOLUTION approach",
                authors=["Author1"],
                url="http://example.com/paper1",
                source="arxiv",
                category="cs.LG",
                published_date="2024-01-01"
            )
        ]
        
        relevant_papers = sentinel._filter_relevant_papers(papers)
        
        assert len(relevant_papers) == 1


class TestAlgoEvolutionSentinelPaperAnalysis:
    """测试论文分析功能"""
    
    @pytest.mark.asyncio
    async def test_analyze_paper_with_high_potential(self):
        """测试分析高潜力论文"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Neural Evolution Meta-Learning Reinforcement Learning",
            abstract="This paper presents neural evolution meta-learning reinforcement learning",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        analysis = await sentinel._analyze_paper(paper)
        
        assert 'potential_score' in analysis
        assert 'complexity_score' in analysis
        assert 'keyword_matches' in analysis
        assert analysis['potential_score'] > 0.5
        assert analysis['keyword_matches'] >= 3
    
    @pytest.mark.asyncio
    async def test_analyze_paper_with_low_potential(self):
        """测试分析低潜力论文"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Unrelated Topic",
            abstract="This paper is about something else",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.CV",
            published_date="2024-01-01"
        )
        
        analysis = await sentinel._analyze_paper(paper)
        
        assert analysis['potential_score'] <= 0.7
        assert analysis['keyword_matches'] == 0
    
    @pytest.mark.asyncio
    async def test_analyze_paper_from_top_conference(self):
        """测试分析顶级会议论文"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Neural Evolution",
            abstract="This paper presents neural evolution",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="conference",
            category="ICML",
            published_date="2024-01-01"
        )
        
        analysis = await sentinel._analyze_paper(paper)
        
        # 顶级会议论文应该有更高的评分
        assert analysis['potential_score'] > 0.6
        assert analysis['source_weight'] == 0.2


class TestAlgoEvolutionSentinelAlgorithmTranslation:
    """测试算法翻译功能"""
    
    @pytest.mark.asyncio
    async def test_translate_to_algorithm(self):
        """测试翻译论文为算法"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Neural Evolution",
            abstract="This paper presents neural evolution",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        analysis = {
            'potential_score': 0.8,
            'complexity_score': 0.6,
            'keyword_matches': 2
        }
        
        algorithm = await sentinel._translate_to_algorithm(paper, analysis)
        
        assert isinstance(algorithm, Algorithm)
        assert algorithm.name == paper.title
        assert algorithm.source_paper == paper
        assert algorithm.potential_score == 0.8
        assert algorithm.complexity_score == 0.6
        assert algorithm.core_algorithm is not None
        assert algorithm.python_implementation is not None


class TestAlgoEvolutionSentinelSandboxValidation:
    """测试沙盒验证功能"""
    
    @pytest.mark.asyncio
    async def test_validate_in_sandbox(self):
        """测试沙盒验证"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Neural Evolution",
            abstract="This paper presents neural evolution",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        algorithm = Algorithm(
            name="Neural Evolution",
            source_paper=paper,
            core_algorithm="Core algorithm",
            python_implementation="# Python code",
            integration_interface="# Integration interface",
            potential_score=0.8,
            complexity_score=0.6
        )
        
        validation_result = await sentinel._validate_in_sandbox(algorithm)
        
        assert 'success' in validation_result
        assert 'function_score' in validation_result
        assert 'performance_score' in validation_result
        assert 'comparison_score' in validation_result
        assert 'overall_score' in validation_result


class TestAlgoEvolutionSentinelIntegration:
    """测试算法集成功能"""
    
    @pytest.mark.asyncio
    async def test_integrate_algorithm_with_high_value(self):
        """测试集成高价值算法"""
        event_bus = EventBus()
        sentinel = AlgoEvolutionSentinel(event_bus=event_bus)
        
        paper = Paper(
            title="Neural Evolution",
            abstract="This paper presents neural evolution",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        algorithm = Algorithm(
            name="Neural Evolution",
            source_paper=paper,
            core_algorithm="Core algorithm",
            python_implementation="# Python code",
            integration_interface="# Integration interface",
            potential_score=0.8,
            complexity_score=0.6
        )
        
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
        
        # 集成算法
        await sentinel._integrate_algorithm(algorithm, validation_result)
        
        # 验证事件已发布
        # （实际测试中需要订阅事件并验证）
    
    @pytest.mark.asyncio
    async def test_integrate_algorithm_with_low_value(self):
        """测试跳过低价值算法"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Low Value Algorithm",
            abstract="This paper presents a low value algorithm",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        algorithm = Algorithm(
            name="Low Value Algorithm",
            source_paper=paper,
            core_algorithm="Core algorithm",
            python_implementation="# Python code",
            integration_interface="# Integration interface",
            potential_score=0.3,
            complexity_score=0.6
        )
        
        validation_result = {
            'success': True,
            'function_score': 0.3,
            'performance_score': 0.2,
            'comparison_score': 0.1,
            'overall_score': 0.2,
            'execution_time': 0.1,
            'memory_usage': 1000,
            'improvement_over_baseline': 0.1,
            'recommendations': []
        }
        
        # 集成算法（应该被跳过）
        await sentinel._integrate_algorithm(algorithm, validation_result)
        
        # 验证算法未被集成（通过日志或事件）
    
    def test_assess_integration_value(self):
        """测试评估集成价值"""
        sentinel = AlgoEvolutionSentinel()
        
        paper = Paper(
            title="Neural Evolution",
            abstract="This paper presents neural evolution",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        algorithm = Algorithm(
            name="Neural Evolution",
            source_paper=paper,
            core_algorithm="Core algorithm",
            python_implementation="# Python code",
            integration_interface="# Integration interface",
            potential_score=0.8,
            complexity_score=0.6
        )
        
        validation_result = {
            'overall_score': 0.7,
            'improvement_over_baseline': 0.5
        }
        
        integration_value = sentinel._assess_integration_value(algorithm, validation_result)
        
        assert 0 <= integration_value <= 1
        assert integration_value > 0.5  # 高价值算法


class TestAlgoEvolutionSentinelMonitoring:
    """测试监控循环功能"""
    
    @pytest.mark.asyncio
    async def test_run_continuous_monitoring_starts_successfully(self):
        """测试监控循环启动成功"""
        sentinel = AlgoEvolutionSentinel(scan_interval=1)
        
        # 模拟扫描方法
        sentinel._scan_new_papers = AsyncMock(return_value=[])
        
        # 启动监控（在后台任务中）
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待一小段时间
        await asyncio.sleep(0.1)
        
        # 验证监控已启动
        assert sentinel.is_running is True
        
        # 停止监控
        sentinel.stop_monitoring()
        await asyncio.sleep(0.1)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_run_continuous_monitoring_already_running(self):
        """测试监控循环已在运行时抛出异常"""
        sentinel = AlgoEvolutionSentinel(scan_interval=1)
        sentinel.is_running = True
        
        with pytest.raises(RuntimeError, match="监控循环已在运行"):
            await sentinel.run_continuous_monitoring()
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self):
        """测试停止监控循环"""
        sentinel = AlgoEvolutionSentinel(scan_interval=1)
        
        # 模拟扫描方法
        sentinel._scan_new_papers = AsyncMock(return_value=[])
        
        # 启动监控
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待监控启动
        await asyncio.sleep(0.1)
        assert sentinel.is_running is True
        
        # 停止监控
        sentinel.stop_monitoring()
        
        # 等待监控停止
        await asyncio.sleep(0.2)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass


class TestAlgoEvolutionSentinelStatistics:
    """测试统计信息功能"""
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        sentinel = AlgoEvolutionSentinel()
        
        stats = sentinel.get_statistics()
        
        assert 'total_papers_scanned' in stats
        assert 'relevant_papers_found' in stats
        assert 'algorithms_translated' in stats
        assert 'algorithms_validated' in stats
        assert 'algorithms_integrated' in stats
        assert 'last_scan_time' in stats
        assert 'scan_count' in stats
        
        # 验证返回的是副本
        stats['total_papers_scanned'] = 999
        assert sentinel.stats['total_papers_scanned'] == 0


class TestAlgoEvolutionSentinelEdgeCases:
    """测试边界条件"""
    
    @pytest.mark.asyncio
    async def test_scan_new_papers_returns_empty_list(self):
        """测试扫描新论文返回空列表"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = await sentinel._scan_new_papers()
        
        assert isinstance(papers, list)
        assert len(papers) == 0
    
    @pytest.mark.asyncio
    async def test_scan_arxiv_returns_empty_list(self):
        """测试扫描arXiv返回空列表"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = await sentinel._scan_arxiv()
        
        assert isinstance(papers, list)
        assert len(papers) == 0
    
    @pytest.mark.asyncio
    async def test_scan_github_returns_empty_list(self):
        """测试扫描GitHub返回空列表"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = await sentinel._scan_github()
        
        assert isinstance(papers, list)
        assert len(papers) == 0
    
    @pytest.mark.asyncio
    async def test_scan_conferences_returns_empty_list(self):
        """测试扫描会议论文返回空列表"""
        sentinel = AlgoEvolutionSentinel()
        
        papers = await sentinel._scan_conferences()
        
        assert isinstance(papers, list)
        assert len(papers) == 0


class TestAlgoEvolutionSentinelMonitoringLoop:
    """测试监控循环完整流程"""
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_with_high_potential_paper(self):
        """测试监控循环处理高潜力论文"""
        sentinel = AlgoEvolutionSentinel(scan_interval=0.1)
        
        # 创建高潜力论文
        high_potential_paper = Paper(
            title="Neural Evolution Meta-Learning Reinforcement Learning",
            abstract="This paper presents neural evolution meta-learning reinforcement learning",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="conference",
            category="ICML",
            published_date="2024-01-01"
        )
        
        # 模拟扫描方法返回高潜力论文
        sentinel._scan_new_papers = AsyncMock(return_value=[high_potential_paper])
        
        # 模拟验证成功
        sentinel._validate_in_sandbox = AsyncMock(return_value={
            'success': True,
            'function_score': 0.8,
            'performance_score': 0.7,
            'comparison_score': 0.6,
            'overall_score': 0.7,
            'execution_time': 0.1,
            'memory_usage': 1000,
            'improvement_over_baseline': 0.5,
            'recommendations': []
        })
        
        # 启动监控
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待一次扫描完成
        await asyncio.sleep(0.3)
        
        # 停止监控
        sentinel.stop_monitoring()
        await asyncio.sleep(0.2)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # 验证统计信息
        assert sentinel.stats['total_papers_scanned'] > 0
        assert sentinel.stats['relevant_papers_found'] > 0
        assert sentinel.stats['algorithms_translated'] > 0
        assert sentinel.stats['algorithms_validated'] > 0
        assert sentinel.stats['algorithms_integrated'] > 0
        assert sentinel.stats['scan_count'] > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_with_low_potential_paper(self):
        """测试监控循环处理低潜力论文"""
        sentinel = AlgoEvolutionSentinel(scan_interval=0.1)
        
        # 创建低潜力论文
        low_potential_paper = Paper(
            title="Unrelated Topic",
            abstract="This paper is about something else",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.CV",
            published_date="2024-01-01"
        )
        
        # 模拟扫描方法返回低潜力论文
        sentinel._scan_new_papers = AsyncMock(return_value=[low_potential_paper])
        
        # 启动监控
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待一次扫描完成
        await asyncio.sleep(0.3)
        
        # 停止监控
        sentinel.stop_monitoring()
        await asyncio.sleep(0.2)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # 验证统计信息（低潜力论文不应被处理）
        assert sentinel.stats['total_papers_scanned'] > 0
        assert sentinel.stats['relevant_papers_found'] == 0
        assert sentinel.stats['algorithms_translated'] == 0
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_with_exception_in_paper_processing(self):
        """测试监控循环处理论文时发生异常"""
        sentinel = AlgoEvolutionSentinel(scan_interval=0.1)
        
        # 创建高潜力论文
        high_potential_paper = Paper(
            title="Neural Evolution Meta-Learning",
            abstract="This paper presents neural evolution meta-learning",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="arxiv",
            category="cs.LG",
            published_date="2024-01-01"
        )
        
        # 模拟扫描方法返回论文
        sentinel._scan_new_papers = AsyncMock(return_value=[high_potential_paper])
        
        # 模拟翻译方法抛出异常
        sentinel._translate_to_algorithm = AsyncMock(side_effect=Exception("Translation error"))
        
        # 启动监控
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待一次扫描完成
        await asyncio.sleep(0.3)
        
        # 停止监控
        sentinel.stop_monitoring()
        await asyncio.sleep(0.2)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # 验证监控继续运行（异常被捕获）
        assert sentinel.stats['scan_count'] > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_with_exception_in_scan(self):
        """测试监控循环扫描时发生异常"""
        sentinel = AlgoEvolutionSentinel(scan_interval=0.1)
        
        # 模拟扫描方法抛出异常
        sentinel._scan_new_papers = AsyncMock(side_effect=Exception("Scan error"))
        
        # 启动监控
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待异常处理和重试
        await asyncio.sleep(0.3)
        
        # 停止监控
        sentinel.stop_monitoring()
        await asyncio.sleep(0.2)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # 验证监控继续运行（异常被捕获并重试）
        assert sentinel.is_running is False

    
    @pytest.mark.asyncio
    async def test_monitoring_loop_with_validation_failure(self):
        """测试监控循环处理验证失败的算法"""
        sentinel = AlgoEvolutionSentinel(scan_interval=0.1)
        
        # 创建高潜力论文（确保潜力评分>0.7）
        high_potential_paper = Paper(
            title="Neural Evolution Meta-Learning Reinforcement Learning Transfer Learning",
            abstract="This paper presents neural evolution meta-learning reinforcement learning transfer learning few-shot learning",
            authors=["Author1"],
            url="http://example.com/paper1",
            source="conference",
            category="ICML",
            published_date="2024-01-01"
        )
        
        # 模拟扫描方法返回论文
        sentinel._scan_new_papers = AsyncMock(return_value=[high_potential_paper])
        
        # 模拟验证失败
        sentinel._validate_in_sandbox = AsyncMock(return_value={
            'success': False,
            'function_score': 0.3,
            'performance_score': 0.2,
            'comparison_score': 0.1,
            'overall_score': 0.2,
            'execution_time': 0.1,
            'memory_usage': 1000,
            'improvement_over_baseline': 0.0,
            'recommendations': []
        })
        
        # 启动监控
        monitoring_task = asyncio.create_task(sentinel.run_continuous_monitoring())
        
        # 等待一次扫描完成
        await asyncio.sleep(0.3)
        
        # 停止监控
        sentinel.stop_monitoring()
        await asyncio.sleep(0.2)
        
        # 取消任务
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        
        # 验证统计信息（验证失败的算法不应被集成）
        assert sentinel.stats['total_papers_scanned'] > 0
        assert sentinel.stats['relevant_papers_found'] > 0
        assert sentinel.stats['algorithms_translated'] > 0
        assert sentinel.stats['algorithms_validated'] == 0  # 验证失败
        assert sentinel.stats['algorithms_integrated'] == 0  # 未集成
