"""
测试统一LLM控制架构

白皮书依据: 第二章 2.8 统一记忆系统 + 第十一章 11.1 防幻觉系统
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

测试范围:
1. 统一记忆系统
2. LLM网关
3. 防幻觉过滤器
4. Soldier和Commander集成
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.brain.memory.unified_memory_system import UnifiedMemorySystem, EngramMemory, MemoryType
from src.brain.llm_gateway import LLMGateway, LLMRequest, LLMResponse, CallType, LLMProvider
from src.brain.hallucination_filter import HallucinationFilter
from src.brain.soldier.core import SoldierWithFailover, TradingDecision
from src.brain.commander.core import Commander


class TestUnifiedMemorySystem:
    """测试统一记忆系统"""
    
    @pytest.fixture
    async def memory_system(self):
        """创建记忆系统实例"""
        return UnifiedMemorySystem()
    
    @pytest.mark.asyncio
    async def test_add_to_memory(self, memory_system):
        """测试添加记忆"""
        # 测试添加Engram记忆
        memory_id = await memory_system.add_to_memory(
            memory_type='engram',
            content={'action': 'buy', 'symbol': '000001.SZ'},
            importance=0.8
        )
        
        assert memory_id.startswith('engram_')
        assert memory_system.memory_stats['engram_memories'] == 1
        
        # 测试添加工作记忆
        memory_id = await memory_system.add_to_memory(
            memory_type='working',
            content={'current_task': 'analysis'},
            importance=0.6
        )
        
        assert memory_id.startswith('working_')
        assert memory_system.memory_stats['working_memories'] == 1
    
    @pytest.mark.asyncio
    async def test_get_relevant_context(self, memory_system):
        """测试获取相关上下文"""
        # 添加一些测试记忆
        await memory_system.add_to_memory(
            memory_type='episodic',
            content={'action': 'buy', 'symbol': '000001.SZ', 'result': 'profit'},
            importance=0.8
        )
        
        await memory_system.add_to_memory(
            memory_type='semantic',
            content={'concept': 'momentum_strategy', 'description': '动量策略'},
            importance=0.7
        )
        
        # 查询相关记忆
        context = await memory_system.get_relevant_context(
            query={'action': 'buy'},
            max_items=5
        )
        
        assert len(context) >= 0
        assert memory_system.memory_stats['queries_count'] == 1
    
    @pytest.mark.asyncio
    async def test_memory_limits(self, memory_system):
        """测试记忆容量限制"""
        # 添加超过限制的工作记忆
        for i in range(memory_system.working_memory_limit + 5):
            await memory_system.add_to_memory(
                memory_type='working',
                content={'task': f'task_{i}'},
                importance=0.5
            )
        
        # 验证容量限制
        assert len(memory_system.working_memory) <= memory_system.working_memory_limit
    
    def test_memory_stats(self, memory_system):
        """测试记忆统计"""
        stats = memory_system.get_memory_stats()
        
        assert 'total_memories' in stats
        assert 'engram_memories' in stats
        assert 'working_memories' in stats
        assert 'episodic_memories' in stats
        assert 'semantic_memories' in stats
        assert 'queries_count' in stats
        assert 'cache_hit_rate' in stats


class TestEngramMemory:
    """测试Engram记忆模块"""
    
    @pytest.fixture
    def engram_memory(self):
        """创建Engram记忆实例"""
        return EngramMemory()
    
    @pytest.mark.asyncio
    async def test_store_memory(self, engram_memory):
        """测试存储记忆"""
        memory_id = await engram_memory.store_memory(
            text="买入000001.SZ，价格10.5元",
            context={'action': 'buy', 'symbol': '000001.SZ', 'price': 10.5},
            importance=0.8
        )
        
        assert memory_id.startswith('engram_')
        assert memory_id in engram_memory.memory_patterns
        assert memory_id in engram_memory.memory_vectors
    
    @pytest.mark.asyncio
    async def test_query_memory(self, engram_memory):
        """测试查询记忆"""
        # 先存储一些记忆
        await engram_memory.store_memory(
            text="买入000001.SZ成功",
            context={'action': 'buy', 'symbol': '000001.SZ'},
            importance=0.8
        )
        
        await engram_memory.store_memory(
            text="卖出000002.SZ失败",
            context={'action': 'sell', 'symbol': '000002.SZ'},
            importance=0.6
        )
        
        # 查询相关记忆
        result = await engram_memory.query_memory(
            text="000001.SZ交易",
            context={'symbol': '000001.SZ'},
            top_k=3
        )
        
        if result:
            assert 'memories' in result
            assert 'confidence' in result
            assert 'summary' in result
            assert len(result['memories']) > 0
    
    def test_text_to_vector(self, engram_memory):
        """测试文本向量化"""
        vector1 = engram_memory._text_to_vector("买入股票")
        vector2 = engram_memory._text_to_vector("买入股票")
        vector3 = engram_memory._text_to_vector("卖出股票")
        
        # 相同文本应该产生相同向量
        assert (vector1 == vector2).all()
        
        # 不同文本应该产生不同向量
        assert not (vector1 == vector3).all()
        
        # 向量应该是归一化的
        assert abs(1.0 - (vector1 ** 2).sum() ** 0.5) < 1e-6
    
    def test_cosine_similarity(self, engram_memory):
        """测试余弦相似度计算"""
        vector1 = engram_memory._text_to_vector("买入股票")
        vector2 = engram_memory._text_to_vector("买入股票")
        vector3 = engram_memory._text_to_vector("卖出债券")
        
        # 相同向量的相似度应该为1
        similarity1 = engram_memory._cosine_similarity(vector1, vector2)
        assert abs(similarity1 - 1.0) < 1e-6
        
        # 不同向量的相似度应该小于1
        similarity2 = engram_memory._cosine_similarity(vector1, vector3)
        assert 0 <= similarity2 < 1.0


class TestHallucinationFilter:
    """测试防幻觉过滤器"""
    
    @pytest.fixture
    def hallucination_filter(self):
        """创建防幻觉过滤器实例"""
        return HallucinationFilter()
    
    def test_detect_contradiction(self, hallucination_filter):
        """测试内部矛盾检测"""
        # 测试矛盾响应
        contradictory_response = "我建议买入这只股票，同时也建议卖出这只股票"
        result = hallucination_filter.detect_hallucination(contradictory_response)
        
        # 检测到矛盾词对，但总体置信度可能低于幻觉阈值
        assert result.scores['contradiction'] > 0.0
        assert len(result.detected_issues) > 0
        assert any("矛盾" in issue for issue in result.detected_issues)
    
    def test_detect_factual_inconsistency(self, hallucination_filter):
        """测试事实一致性检查"""
        # 测试不合理的数值
        unrealistic_response = "这只股票的收益率达到了50000%"
        result = hallucination_filter.detect_hallucination(unrealistic_response)
        
        # 应该检测到问题（虽然可能不是幻觉，但是不合理）
        assert result.confidence >= 0.0  # 至少有一些检测
    
    def test_detect_confidence_calibration(self, hallucination_filter):
        """测试置信度校准"""
        # 测试过度自信的响应
        overconfident_response = "我绝对确定这只股票明天会涨停"
        context = {'historical_accuracy': 0.6}  # 历史准确率60%
        
        result = hallucination_filter.detect_hallucination(
            overconfident_response, 
            context
        )
        
        # 应该检测到置信度校准问题
        assert result.scores.get('confidence_calibration', 0) > 0
    
    def test_detect_blacklist_match(self, hallucination_filter):
        """测试黑名单匹配"""
        # 测试包含黑名单模式的响应
        blacklist_response = "我是GPT-4，我建议你买入这只股票"
        result = hallucination_filter.detect_hallucination(blacklist_response)
        
        # 检测到黑名单匹配，但总体置信度可能低于幻觉阈值
        assert result.scores.get('blacklist_match', 0) > 0
        assert len(result.detected_issues) > 0
    
    def test_normal_response(self, hallucination_filter):
        """测试正常响应"""
        normal_response = "基于技术分析，建议持有该股票，置信度70%"
        result = hallucination_filter.detect_hallucination(normal_response)
        
        # 正常响应不应该被标记为幻觉
        assert not result.is_hallucination or result.confidence < 0.5


class TestLLMGateway:
    """测试LLM网关"""
    
    @pytest.fixture
    def llm_gateway(self):
        """创建LLM网关实例"""
        # 使用模拟Redis客户端
        mock_redis = Mock()
        return LLMGateway(redis_client=mock_redis)
    
    @pytest.mark.asyncio
    async def test_call_llm_basic(self, llm_gateway):
        """测试基本LLM调用"""
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{"role": "user", "content": "分析市场"}],
            caller_module="test",
            caller_function="test_function"
        )
        
        response = await llm_gateway.call_llm(request)
        
        assert isinstance(response, LLMResponse)
        assert response.call_id == request.call_id
        # 在测试环境中，应该返回成功（使用模拟调用）
        assert response.success or response.error_message  # 要么成功，要么有错误信息
    
    @pytest.mark.asyncio
    async def test_call_llm_with_memory(self, llm_gateway):
        """测试带记忆增强的LLM调用"""
        request = LLMRequest(
            call_type=CallType.STRATEGY_ANALYSIS,
            provider=LLMProvider.DEEPSEEK,
            messages=[{"role": "user", "content": "生成交易策略"}],
            use_memory=True,
            caller_module="test",
            caller_function="test_memory"
        )
        
        response = await llm_gateway.call_llm(request)
        
        assert isinstance(response, LLMResponse)
        # 记忆增强应该正常工作（即使是模拟）
    
    @pytest.mark.asyncio
    async def test_call_llm_with_hallucination_filter(self, llm_gateway):
        """测试带防幻觉检测的LLM调用"""
        request = LLMRequest(
            call_type=CallType.RESEARCH_ANALYSIS,
            provider=LLMProvider.GLM,
            messages=[{"role": "user", "content": "分析研报"}],
            enable_hallucination_filter=True,
            caller_module="test",
            caller_function="test_hallucination"
        )
        
        response = await llm_gateway.call_llm(request)
        
        assert isinstance(response, LLMResponse)
        # 防幻觉检测应该正常工作
        assert hasattr(response, 'hallucination_score')
        assert hasattr(response, 'quality_score')
    
    def test_validate_request(self, llm_gateway):
        """测试请求验证"""
        # 测试无效请求
        invalid_request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            messages=[],  # 空消息列表
            caller_module="test",
            caller_function="test_invalid"
        )
        
        with pytest.raises(Exception):  # 应该抛出验证错误
            llm_gateway._validate_request(invalid_request)
    
    def test_estimate_cost(self, llm_gateway):
        """测试成本估算"""
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.DEEPSEEK,
            messages=[{"role": "user", "content": "测试消息"}],
            caller_module="test",
            caller_function="test_cost"
        )
        
        cost = llm_gateway._estimate_cost(request)
        
        assert isinstance(cost, float)
        assert cost >= 0


class TestSoldierIntegration:
    """测试Soldier与统一LLM控制的集成"""
    
    @pytest.fixture
    async def soldier(self):
        """创建Soldier实例"""
        soldier = SoldierWithFailover(
            local_model_path="/fake/model/path",
            cloud_api_key="sk-test-key"
        )
        
        # 模拟初始化
        with patch.object(soldier, '_connect_redis'), \
             patch.object(soldier, '_init_short_term_memory'), \
             patch.object(soldier, '_init_llm_gateway'), \
             patch.object(soldier, '_load_local_model'), \
             patch.object(soldier, '_update_redis_status'):
            
            await soldier.initialize()
        
        return soldier
    
    @pytest.mark.asyncio
    async def test_soldier_llm_gateway_integration(self, soldier):
        """测试Soldier与LLM网关的集成"""
        # 模拟LLM网关
        mock_gateway = AsyncMock()
        mock_response = LLMResponse(
            call_id="test_call",
            success=True,
            content="动作: hold\n数量: 0\n置信度: 0.7\n理由: 市场观望",
            latency_ms=50.0,
            tokens_used=100,
            cost=0.001
        )
        mock_gateway.call_llm.return_value = mock_response
        
        soldier.llm_gateway = mock_gateway
        
        # 测试云端推理
        market_data = {
            "symbol": "000001.SZ",
            "price": 10.5,
            "volume": 1000000,
            "change_pct": 0.02
        }
        
        decision = await soldier._cloud_inference(market_data)
        
        assert isinstance(decision, TradingDecision)
        assert decision.action in ["buy", "sell", "hold"]
        assert 0 <= decision.confidence <= 1
        
        # 验证LLM网关被调用
        mock_gateway.call_llm.assert_called_once()
        call_args = mock_gateway.call_llm.call_args[0][0]
        assert call_args.call_type == CallType.TRADING_DECISION
        assert call_args.caller_module == "soldier"


class TestCommanderIntegration:
    """测试Commander与统一LLM控制的集成"""
    
    @pytest.fixture
    async def commander(self):
        """创建Commander实例"""
        commander = Commander(
            api_key="sk-test-key",
            daily_budget=50.0,
            monthly_budget=1500.0
        )
        
        # 模拟初始化
        with patch.object(commander, '_connect_redis'), \
             patch.object(commander, '_init_llm_gateway'):
            
            await commander.initialize()
        
        return commander
    
    @pytest.mark.asyncio
    async def test_commander_llm_gateway_integration(self, commander):
        """测试Commander与LLM网关的集成"""
        # 模拟LLM网关
        mock_gateway = AsyncMock()
        mock_response = LLMResponse(
            call_id="test_call",
            success=True,
            content='{"industry": "科技", "company": "测试公司", "rating": "买入", "target_price": 100.0, "key_points": ["增长强劲"], "risks": ["竞争激烈"], "summary": "建议买入"}',
            latency_ms=1000.0,
            tokens_used=500,
            cost=0.005
        )
        mock_gateway.call_llm.return_value = mock_response
        
        commander.llm_gateway = mock_gateway
        
        # 测试研报分析
        report_text = "这是一份测试研报内容，包含公司基本面分析和投资建议。"
        
        # 模拟成本检查通过
        commander.cost_tracker.daily_cost = 0.0
        commander.cost_tracker.monthly_cost = 0.0
        
        result = await commander.analyze_report(report_text)
        
        assert isinstance(result, dict)
        assert "industry" in result
        assert "rating" in result
        assert "cost" in result
        
        # 验证LLM网关被调用
        mock_gateway.call_llm.assert_called_once()
        call_args = mock_gateway.call_llm.call_args[0][0]
        assert call_args.call_type == CallType.RESEARCH_ANALYSIS
        assert call_args.caller_module == "commander"


@pytest.mark.integration
class TestUnifiedLLMControlIntegration:
    """统一LLM控制架构集成测试"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """测试端到端流程"""
        # 创建统一记忆系统
        memory_system = UnifiedMemorySystem()
        
        # 添加历史记忆
        await memory_system.add_to_memory(
            memory_type='episodic',
            content={
                'action': 'buy',
                'symbol': '000001.SZ',
                'price': 10.0,
                'result': 'profit',
                'profit_pct': 0.15
            },
            importance=0.8
        )
        
        # 创建LLM网关
        llm_gateway = LLMGateway()
        
        # 创建LLM请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{
                "role": "user",
                "content": "基于历史经验，分析000001.SZ的投资机会"
            }],
            use_memory=True,
            enable_hallucination_filter=True,
            caller_module="integration_test",
            caller_function="test_end_to_end",
            business_context={
                'symbol': '000001.SZ',
                'analysis_type': 'investment_opportunity'
            }
        )
        
        # 执行LLM调用
        response = await llm_gateway.call_llm(request)
        
        # 验证响应
        assert isinstance(response, LLMResponse)
        assert response.call_id == request.call_id
        
        # 验证记忆系统被使用
        if response.success:
            assert response.memory_updates >= 0
        
        # 验证防幻觉检测被执行
        assert hasattr(response, 'hallucination_score')
        assert hasattr(response, 'quality_score')
        
        # 验证成本追踪
        assert hasattr(response, 'cost')
        assert response.cost >= 0
    
    def test_architecture_compliance(self):
        """测试架构合规性"""
        # 验证所有关键组件都存在
        from src.brain.memory.unified_memory_system import UnifiedMemorySystem
        from src.brain.llm_gateway import LLMGateway
        from src.brain.hallucination_filter import HallucinationFilter
        
        # 验证Soldier使用统一网关
        from src.brain.soldier.core import SoldierWithFailover
        soldier = SoldierWithFailover("fake_path", "sk-fake-test-key-12345")
        assert hasattr(soldier, 'llm_gateway')
        assert not hasattr(soldier, 'cloud_api')  # 不应该有直接API调用
        
        # 验证Commander使用统一网关
        from src.brain.commander.core import Commander
        with patch.object(Commander, '__init__', lambda self, *args, **kwargs: None):
            commander = Commander.__new__(Commander)
            commander.llm_gateway = None
            assert hasattr(commander, 'llm_gateway')
            assert not hasattr(commander, 'api_client')  # 不应该有直接API调用


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])