"""
Scholar引擎 v2.0 单元测试

白皮书依据: 第二章 2.3 AI三脑架构 - Scholar引擎
需求: 2.1-2.8 ScholarEngineV2完善实现

测试覆盖:
1. 因子研究核心流程
2. IC/IR计算正确性
3. 事件驱动通信（属性测试）
4. 论文分析功能
5. 因子库管理
6. 缓存机制
7. 统计信息
"""

import pytest
import pytest_asyncio
import asyncio
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.brain.scholar_engine_v2 import (
    ScholarEngineV2,
    FactorResearch,
    PaperAnalysis
)
from src.infra.event_bus import Event, EventType, EventPriority


class TestFactorResearch:
    """测试FactorResearch数据类"""
    
    def test_factor_research_creation(self):
        """测试因子研究结果创建"""
        research = FactorResearch(
            factor_name="momentum_factor",
            factor_score=0.75,
            ic_mean=0.05,
            ic_std=0.02,
            ir=2.5,
            insight="Strong momentum effect",
            confidence=0.8,
            risk_metrics={'volatility': 0.15},
            theoretical_basis="Price momentum theory",
            metadata={'test': 'data'}
        )
        
        assert research.factor_name == "momentum_factor"
        assert research.factor_score == 0.75
        assert research.ic_mean == 0.05
        assert research.ic_std == 0.02
        assert research.ir == 2.5
        assert research.confidence == 0.8


class TestPaperAnalysis:
    """测试PaperAnalysis数据类"""
    
    def test_paper_analysis_creation(self):
        """测试论文分析结果创建"""
        analysis = PaperAnalysis(
            paper_title="Test Paper",
            key_insights=["Insight 1", "Insight 2"],
            practical_applications=["App 1"],
            implementation_difficulty="medium",
            relevance_score=0.8,
            innovation_level="high",
            summary="Test summary",
            metadata={'test': 'data'}
        )
        
        assert analysis.paper_title == "Test Paper"
        assert len(analysis.key_insights) == 2
        assert analysis.relevance_score == 0.8
        assert analysis.innovation_level == "high"


class TestScholarEngineV2:
    """测试Scholar引擎v2.0"""
    
    @pytest_asyncio.fixture
    async def scholar(self):
        """创建Scholar引擎实例"""
        # Mock LLM Gateway和Hallucination Filter
        llm_gateway = AsyncMock()
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(return_value="Test LLM response")
        
        hallucination_filter = AsyncMock()
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={'is_hallucination': False, 'confidence': 0.9}
        )
        
        scholar = ScholarEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter
        )
        
        # Mock event bus
        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        scholar.event_bus = event_bus
        
        await scholar.initialize()
        
        return scholar
    
    @pytest.mark.asyncio
    async def test_initialization(self, scholar):
        """测试Scholar引擎初始化
        
        需求: 2.1 - Scholar应该正确初始化
        """
        assert scholar.state == "READY"
        assert scholar.event_bus is not None
        assert len(scholar.factor_library) == 6  # 六大类因子
        assert 'momentum' in scholar.factor_library
        assert 'value' in scholar.factor_library
        assert 'quality' in scholar.factor_library
        assert 'growth' in scholar.factor_library
        assert 'volatility' in scholar.factor_library
        assert 'liquidity' in scholar.factor_library
    
    @pytest.mark.asyncio
    async def test_factor_library_structure(self, scholar):
        """测试因子库结构
        
        需求: 2.6 - 维护因子库，包含六大类
        """
        # 验证因子库包含所有六大类
        expected_categories = ['momentum', 'value', 'quality', 'growth', 'volatility', 'liquidity']
        
        for category in expected_categories:
            assert category in scholar.factor_library
            assert isinstance(scholar.factor_library[category], list)
            assert len(scholar.factor_library[category]) > 0
        
        # 验证momentum类因子
        assert 'price_momentum' in scholar.factor_library['momentum']
        assert 'earnings_momentum' in scholar.factor_library['momentum']
        
        # 验证value类因子
        assert 'pe_ratio' in scholar.factor_library['value']
        assert 'pb_ratio' in scholar.factor_library['value']


class TestFactorResearchFlow:
    """测试因子研究流程"""
    
    @pytest_asyncio.fixture
    async def scholar(self):
        """创建Scholar引擎实例"""
        llm_gateway = AsyncMock()
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(
            return_value="该因子显示出正向预测能力，具有一定的Alpha潜力。基于历史价格数据的统计规律。"
        )
        
        hallucination_filter = AsyncMock()
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={'is_hallucination': False, 'confidence': 0.9}
        )
        
        scholar = ScholarEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter
        )
        
        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        scholar.event_bus = event_bus
        
        await scholar.initialize()
        
        return scholar
    
    @pytest.mark.asyncio
    async def test_research_factor_basic(self, scholar):
        """测试基本因子研究流程
        
        需求: 2.1 - 执行完整的因子研究流程
        """
        factor_expression = "close/delay(close,1)-1"
        
        result = await scholar.research_factor(factor_expression)
        
        # 验证返回结果结构
        assert 'factor_name' in result
        assert 'factor_score' in result
        assert 'ic_mean' in result
        assert 'ic_std' in result
        assert 'ir' in result
        assert 'insight' in result
        assert 'confidence' in result
        assert 'risk_metrics' in result
        assert 'theoretical_basis' in result
        assert 'metadata' in result
        
        # 验证统计信息更新
        assert scholar.stats['total_researches'] == 1
        assert scholar.stats['factor_analyses'] == 1
    
    @pytest.mark.asyncio
    async def test_factor_expression_parsing(self, scholar):
        """测试因子表达式解析
        
        需求: 2.1 - 解析因子表达式
        """
        # 测试简单表达式
        parsed = scholar._parse_factor_expression("close/delay(close,1)-1")
        
        assert 'name' in parsed
        assert 'expression' in parsed
        assert 'operators' in parsed
        assert 'variables' in parsed
        assert 'category' in parsed
        
        # 验证操作符提取
        assert 'delay' in parsed['operators']
        
        # 验证变量提取
        assert 'close' in parsed['variables']
        
        # 验证分类
        assert parsed['category'] in ['momentum', 'value', 'quality', 'growth', 'volatility', 'liquidity']
    
    @pytest.mark.asyncio
    async def test_factor_classification(self, scholar):
        """测试因子分类
        
        需求: 2.6 - 因子分类到六大类
        """
        # Momentum因子
        category = scholar._classify_factor("close/delay(close,1)-1", ['delay'], ['close'])
        assert category == 'momentum'
        
        # Volatility因子
        category = scholar._classify_factor("std(close, 20)", ['std'], ['close'])
        assert category == 'volatility'
        
        # Liquidity因子
        category = scholar._classify_factor("volume/mean(volume, 20)", [], ['volume'])
        assert category == 'liquidity'
        
        # Value因子 - 需要包含pe变量
        category = scholar._classify_factor("pe_ratio", [], ['pe'])
        assert category == 'value'
    
    @pytest.mark.asyncio
    async def test_ic_ir_calculation(self, scholar):
        """测试IC/IR计算正确性
        
        需求: 2.3 - 返回IC均值、IC标准差和信息比率
        属性7: IC/IR计算正确性
        """
        # 创建测试数据
        np.random.seed(42)
        factor_values = pd.Series(np.random.randn(100))
        returns = pd.Series(np.random.randn(100) * 0.01)
        
        # 计算IC/IR
        ic_mean, ic_std, ir = scholar._calculate_ic_ir(factor_values, returns)
        
        # 验证返回值类型
        assert isinstance(ic_mean, float)
        assert isinstance(ic_std, float)
        assert isinstance(ir, float)
        
        # 验证IC在合理范围内 [-1, 1]
        assert -1.0 <= ic_mean <= 1.0
        
        # 验证IC标准差非负
        assert ic_std >= 0
        
        # 验证IR计算正确性: IR = IC均值 / IC标准差
        if ic_std > 0:
            expected_ir = ic_mean / ic_std
            assert abs(ir - expected_ir) < 0.0001  # 允许浮点误差
    
    @pytest.mark.asyncio
    async def test_ic_ir_with_perfect_correlation(self, scholar):
        """测试完美相关的IC/IR计算
        
        属性7: IC/IR计算正确性 - 边界条件
        """
        # 创建完美正相关的数据
        factor_values = pd.Series(range(100))
        returns = pd.Series(range(100))
        
        ic_mean, ic_std, ir = scholar._calculate_ic_ir(factor_values, returns)
        
        # 完美正相关，IC应该接近1
        assert ic_mean > 0.9
    
    @pytest.mark.asyncio
    async def test_ic_ir_with_no_correlation(self, scholar):
        """测试无相关的IC/IR计算
        
        属性7: IC/IR计算正确性 - 边界条件
        """
        np.random.seed(42)
        # 创建完全随机的数据
        factor_values = pd.Series(np.random.randn(100))
        returns = pd.Series(np.random.randn(100))
        
        ic_mean, ic_std, ir = scholar._calculate_ic_ir(factor_values, returns)
        
        # 随机数据，IC应该接近0
        assert abs(ic_mean) < 0.3  # 允许一定的随机波动


class TestEventDrivenCommunication:
    """测试事件驱动通信（属性测试）
    
    属性2: 事件驱动通信
    验证: 需求2.5 - 通过事件总线异步请求市场数据
    """
    
    @pytest_asyncio.fixture
    async def scholar_with_event_bus(self):
        """创建带事件总线的Scholar引擎"""
        llm_gateway = AsyncMock()
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(return_value="Test insight")
        
        hallucination_filter = AsyncMock()
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={'is_hallucination': False}
        )
        
        scholar = ScholarEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter
        )
        
        # 创建真实的事件总线Mock - 使用AsyncMock而不是真实EventBus
        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        # 直接设置event_bus，跳过initialize中的get_event_bus调用
        scholar.event_bus = event_bus
        scholar.state = "READY"
        
        # 手动调用_setup_event_subscriptions来记录订阅
        await scholar._setup_event_subscriptions()
        
        return scholar
    
    @pytest.mark.asyncio
    async def test_market_data_request_via_event_bus(self, scholar_with_event_bus):
        """测试通过事件总线请求市场数据
        
        属性2: 事件驱动通信
        需求: 2.5 - 通过事件总线异步请求市场数据
        
        验证: 对于任意因子研究请求，应该通过事件总线请求市场数据，不应该直接调用
        """
        scholar = scholar_with_event_bus
        factor_expression = "close/delay(close,1)-1"
        
        # 执行因子研究
        await scholar.research_factor(factor_expression)
        
        # 验证事件总线的publish方法被调用
        assert scholar.event_bus.publish.call_count > 0
        
        # 获取所有publish调用
        publish_calls = scholar.event_bus.publish.call_args_list
        
        # 验证至少有一个调用是请求市场数据
        market_data_request_found = False
        for call in publish_calls:
            event = call[0][0]  # 获取Event对象
            if hasattr(event, 'data') and isinstance(event.data, dict):
                if event.data.get('action') == 'request_market_data_for_factor':
                    market_data_request_found = True
                    # 验证请求包含必要信息
                    assert 'factor_expression' in event.data
                    assert 'correlation_id' in event.data
                    assert event.data['factor_expression'] == factor_expression
                    break
        
        assert market_data_request_found, "未找到市场数据请求事件"
    
    @pytest.mark.asyncio
    async def test_factor_discovered_event_published(self, scholar_with_event_bus):
        """测试因子发现事件发布
        
        属性2: 事件驱动通信
        需求: 2.4 - 发布FACTOR_DISCOVERED事件
        
        验证: 对于任意成功的因子研究，应该发布FACTOR_DISCOVERED事件
        """
        scholar = scholar_with_event_bus
        factor_expression = "close/delay(close,1)-1"
        
        # 执行因子研究
        result = await scholar.research_factor(factor_expression)
        
        # 验证事件总线的publish方法被调用
        assert scholar.event_bus.publish.call_count > 0
        
        # 获取所有publish调用
        publish_calls = scholar.event_bus.publish.call_args_list
        
        # 验证FACTOR_DISCOVERED事件被发布
        factor_discovered_found = False
        for call in publish_calls:
            event = call[0][0]
            if hasattr(event, 'event_type') and event.event_type == EventType.FACTOR_DISCOVERED:
                factor_discovered_found = True
                # 验证事件包含必要信息
                assert 'factor_name' in event.data
                assert 'ic_mean' in event.data
                assert 'ir' in event.data
                assert 'factor_score' in event.data
                break
        
        assert factor_discovered_found, "未找到FACTOR_DISCOVERED事件"
    
    @pytest.mark.asyncio
    async def test_async_non_blocking_data_request(self, scholar_with_event_bus):
        """测试异步非阻塞数据请求
        
        属性3: 异步非阻塞
        需求: 2.5 - 异步请求，不阻塞主流程
        
        验证: 对于任意外部数据请求，应该异步进行，主流程不应该被阻塞超过超时时间
        """
        scholar = scholar_with_event_bus
        factor_expression = "close/delay(close,1)-1"
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 执行因子研究（即使没有市场数据响应，也应该继续）
        result = await scholar.research_factor(factor_expression)
        
        # 记录结束时间
        elapsed_time = time.time() - start_time
        
        # 验证研究完成（即使没有外部数据）
        assert result is not None
        assert 'factor_name' in result
        
        # 验证没有被长时间阻塞（应该在合理时间内完成）
        # 考虑到LLM调用等，允许最多5秒
        assert elapsed_time < 5.0, f"因子研究耗时过长: {elapsed_time}秒"
    
    @pytest.mark.asyncio
    async def test_event_subscription_setup(self, scholar_with_event_bus):
        """测试事件订阅设置
        
        属性2: 事件驱动通信
        
        验证: Scholar应该订阅相关事件以接收外部数据
        """
        scholar = scholar_with_event_bus
        
        # 验证subscribe方法被调用
        assert scholar.event_bus.subscribe.call_count > 0
        
        # 获取所有subscribe调用
        subscribe_calls = scholar.event_bus.subscribe.call_args_list
        
        # 验证订阅了必要的事件类型
        subscribed_event_types = set()
        for call in subscribe_calls:
            event_type = call[0][0]  # 第一个参数是event_type
            subscribed_event_types.add(event_type)
        
        # 验证订阅了MARKET_DATA_RECEIVED事件
        assert EventType.MARKET_DATA_RECEIVED in subscribed_event_types
        
        # 验证订阅了ANALYSIS_COMPLETED事件（用于接收研究请求）
        assert EventType.ANALYSIS_COMPLETED in subscribed_event_types


class TestCachingMechanism:
    """测试缓存机制"""
    
    @pytest_asyncio.fixture
    async def scholar(self):
        """创建Scholar引擎实例"""
        llm_gateway = AsyncMock()
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(return_value="Test insight")
        
        hallucination_filter = AsyncMock()
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={'is_hallucination': False}
        )
        
        scholar = ScholarEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter
        )
        
        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        scholar.event_bus = event_bus
        
        # 设置较短的缓存TTL用于测试
        scholar.cache_ttl = 2  # 2秒
        
        await scholar.initialize()
        
        return scholar
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, scholar):
        """测试缓存命中
        
        属性4: 缓存一致性
        需求: 1.5 - 在TTL内返回缓存结果
        
        验证: 对于任意缓存项，在TTL内应该返回相同的结果
        """
        factor_expression = "close/delay(close,1)-1"
        
        # 第一次研究
        result1 = await scholar.research_factor(factor_expression)
        
        # 第二次研究（应该命中缓存）
        result2 = await scholar.research_factor(factor_expression)
        
        # 验证结果相同
        assert result1['factor_name'] == result2['factor_name']
        assert result1['ic_mean'] == result2['ic_mean']
        assert result1['ir'] == result2['ir']
        
        # 验证缓存命中统计
        assert scholar.stats['cache_hits'] >= 1
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, scholar):
        """测试缓存过期
        
        属性4: 缓存一致性
        
        验证: TTL过期后应该重新计算
        """
        factor_expression = "close/delay(close,1)-1"
        
        # 第一次研究
        result1 = await scholar.research_factor(factor_expression)
        initial_cache_hits = scholar.stats['cache_hits']
        
        # 等待缓存过期
        await asyncio.sleep(2.5)
        
        # 第二次研究（缓存应该已过期）
        result2 = await scholar.research_factor(factor_expression)
        
        # 验证缓存命中次数没有增加（因为缓存已过期）
        assert scholar.stats['cache_hits'] == initial_cache_hits


class TestStatistics:
    """测试统计信息"""
    
    @pytest_asyncio.fixture
    async def scholar(self):
        """创建Scholar引擎实例"""
        llm_gateway = AsyncMock()
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(return_value="Test insight")
        
        hallucination_filter = AsyncMock()
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={'is_hallucination': False}
        )
        
        scholar = ScholarEngineV2(
            llm_gateway=llm_gateway,
            hallucination_filter=hallucination_filter
        )
        
        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        scholar.event_bus = event_bus
        
        await scholar.initialize()
        
        return scholar
    
    @pytest.mark.asyncio
    async def test_statistics_update(self, scholar):
        """测试统计信息更新
        
        需求: 8.2 - 完整的单元测试
        """
        # 初始统计
        initial_stats = scholar.get_statistics()
        assert initial_stats['total_researches'] == 0
        assert initial_stats['factor_analyses'] == 0
        
        # 执行因子研究
        await scholar.research_factor("close/delay(close,1)-1")
        
        # 验证统计更新
        updated_stats = scholar.get_statistics()
        assert updated_stats['total_researches'] == 1
        assert updated_stats['factor_analyses'] == 1
        assert updated_stats['state'] == "READY"
        assert 'cache_size' in updated_stats
        assert 'factor_library_size' in updated_stats
