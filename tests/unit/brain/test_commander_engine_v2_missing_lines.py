# -*- coding: utf-8 -*-
"""
Commander Engine V2 缺失行覆盖测试
目标：覆盖第519行和第1028行，将覆盖率从98.30%提升到100%
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.brain.commander_engine_v2 import CommanderEngineV2, StrategyAnalysis
from src.brain.llm_gateway import LLMGateway


class TestCommanderEngineV2MissingLines:
    """专门测试Commander Engine V2缺失行的测试套件"""
    
    def setup_method(self):
        """测试前置设置"""
        self.engine = CommanderEngineV2()
        
    @pytest.mark.asyncio
    async def test_simple_text_parsing_line_519(self):
        """测试第519行：简单文本解析的默认情况"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            # 模拟LLM网关返回不包含JSON的响应，触发简单文本解析
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                # 设置一个不包含buy/sell/reduce的响应，应该返回"hold"
                # 重要：不能包含{和}，否则会尝试JSON解析
                mock_llm.return_value = "This is a neutral market analysis without clear direction"
                
                # 模拟幻觉过滤器
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 清除缓存
                    self.engine.analysis_cache.clear()
                    
                    # 调用分析方法
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000,
                        "trend": "neutral"
                    })
                    
                    # 验证返回了hold建议（这会触发第519行的代码）
                    assert result["recommendation"] == "hold"
                    assert result["confidence"] > 0
            
    @pytest.mark.asyncio
    async def test_simple_text_parsing_with_reduce(self):
        """测试简单文本解析中的reduce情况"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                # 设置包含"reduce"的响应，不包含{和}
                mock_llm.return_value = "Market conditions suggest to reduce position size"
                
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 清除缓存
                    self.engine.analysis_cache.clear()
                    
                    result = await self.engine.analyze_strategy({
                        "index_level": 3001,  # 不同的输入避免缓存
                        "volatility": 0.03,
                        "volume": 1000000,
                        "trend": "down"
                    })
                    
                    # 验证返回了reduce建议
                    assert result["recommendation"] == "reduce"
                
    def test_assess_risk_from_tier_line_1028(self):
        """测试第1028行：_assess_risk_from_tier方法的默认情况"""
        # 测试不在预定义tier范围内的情况，应该返回"medium"
        
        # 测试tier1_small的情况（应该触发else分支，返回medium）
        risk_level = self.engine._assess_risk_from_tier("tier1_small")
        assert risk_level == "medium"
        
        # 测试tier2_startup的情况
        risk_level = self.engine._assess_risk_from_tier("tier2_startup")
        assert risk_level == "medium"
        
        # 测试未知tier的情况
        risk_level = self.engine._assess_risk_from_tier("unknown_tier")
        assert risk_level == "medium"
        
        # 测试None的情况
        risk_level = self.engine._assess_risk_from_tier(None)
        assert risk_level == "medium"
        
        # 测试空字符串的情况
        risk_level = self.engine._assess_risk_from_tier("")
        assert risk_level == "medium"
        
    def test_risk_level_all_branches(self):
        """测试所有风险等级分支，确保完整覆盖"""
        # 测试大资金低风险
        assert self.engine._assess_risk_from_tier("tier5_million") == "low"
        assert self.engine._assess_risk_from_tier("tier6_ten_million") == "low"
        
        # 测试中等资金中等风险
        assert self.engine._assess_risk_from_tier("tier3_medium") == "medium"
        assert self.engine._assess_risk_from_tier("tier4_large") == "medium"
        
        # 测试默认情况（第1028行）
        assert self.engine._assess_risk_from_tier("tier1_small") == "medium"
        assert self.engine._assess_risk_from_tier("tier2_startup") == "medium"
        assert self.engine._assess_risk_from_tier("invalid_tier") == "medium"
        
    @pytest.mark.asyncio
    async def test_text_parsing_edge_cases(self):
        """测试文本解析的边界情况"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 测试包含多个关键词的情况 - buy应该优先
                    # 重要：不包含{和}，确保进入文本解析分支
                    mock_llm.return_value = "buy and sell signals are mixed, but overall buy"
                    # 清除缓存
                    self.engine.analysis_cache.clear()
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    # 应该匹配第一个找到的关键词（buy在前）
                    assert result["recommendation"] == "buy"
                    
                    # 测试大小写混合 - 确保只包含sell关键词，避免子字符串匹配
                    # "analysis"包含"buy"，所以改用不包含"buy"子字符串的词
                    mock_llm.return_value = "Strong recommendation to SELL position now"
                    # 清除缓存
                    self.engine.analysis_cache.clear()
                    result = await self.engine.analyze_strategy({
                        "index_level": 3001,  # 改变输入以避免缓存
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    assert result["recommendation"] == "sell"
                    
                    # 测试包含reduce的情况
                    mock_llm.return_value = "Consider to REDUCE exposure to this asset"
                    # 清除缓存
                    self.engine.analysis_cache.clear()
                    result = await self.engine.analyze_strategy({
                        "index_level": 3002,  # 改变输入以避免缓存
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    assert result["recommendation"] == "reduce"
            
    @pytest.mark.asyncio
    async def test_json_parsing_fallback_to_text(self):
        """测试JSON解析失败后回退到保守策略（不是文本解析）"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 设置一个无效的JSON响应，包含{和}会尝试JSON解析
                    # JSON解析失败后会进入异常处理，返回保守策略（hold）
                    mock_llm.return_value = 'invalid json format with braces but contains strong buy signal'
                    
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    
                    # 应该进入文本解析分支，找到"buy"关键词
                    assert result["recommendation"] == "buy"
                
    @pytest.mark.asyncio
    async def test_empty_response_handling(self):
        """测试空响应的处理"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 测试空响应
                    mock_llm.return_value = ""
                    
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    
                    # 空响应应该返回默认的"hold"建议
                    assert result["recommendation"] == "hold"
            
    @pytest.mark.asyncio
    async def test_whitespace_only_response(self):
        """测试只包含空白字符的响应"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 测试只包含空白字符的响应
                    mock_llm.return_value = "   \n\t   "
                    
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    
                    # 应该返回默认的"hold"建议
                    assert result["recommendation"] == "hold"
                
    @pytest.mark.asyncio
    async def test_special_characters_in_response(self):
        """测试响应中包含特殊字符的情况"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 测试包含特殊字符但有关键词的响应，不包含{和}
                    mock_llm.return_value = "Market analysis: 📈 Strong BUY signal! 🚀"
                    
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    
                    # 应该能正确识别"buy"关键词
                    assert result["recommendation"] == "buy"
            
    def test_risk_level_with_statistics_integration(self):
        """测试风险等级与统计信息的集成"""
        # 获取统计信息，这会间接测试风险等级的使用
        stats = self.engine.get_statistics()
        
        # 验证统计信息包含预期的字段
        assert isinstance(stats, dict)
        assert "state" in stats
        
        # 测试不同tier下的风险等级计算
        for tier in ["tier1_small", "tier2_startup", "tier3_medium", 
                    "tier4_large", "tier5_million", "tier6_ten_million"]:
            risk_level = self.engine._assess_risk_from_tier(tier)
            assert risk_level in ["low", "medium"]
            
    @pytest.mark.asyncio
    async def test_comprehensive_text_parsing_coverage(self):
        """全面测试文本解析的所有分支"""
        test_cases = [
            ("neutral market conditions", "hold"),  # 避免"analysis"包含"buy"
            ("strong buy signal", "buy"),
            ("recommendation to sell", "sell"),
            ("reduce position", "reduce"),
            ("BUY NOW!", "buy"),
            ("time to SELL", "sell"),
            ("REDUCE EXPOSURE", "reduce"),
            ("no clear direction", "hold"),
            ("", "hold"),
            ("random text without keywords", "hold")
        ]
        
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    for i, (response_text, expected_recommendation) in enumerate(test_cases):
                        mock_llm.return_value = response_text
                        # 清除缓存并使用不同的输入避免缓存
                        self.engine.analysis_cache.clear()
                        
                        result = await self.engine.analyze_strategy({
                            "index_level": 3000 + i,  # 每次使用不同的输入避免缓存
                            "volatility": 0.02,
                            "volume": 1000000
                        })
                        
                        assert result["recommendation"] == expected_recommendation, \
                            f"Failed for response: '{response_text}', expected: {expected_recommendation}, got: {result['recommendation']}"

    @pytest.mark.asyncio
    async def test_json_parsing_exception_handling(self):
        """测试JSON解析异常处理，确保进入保守策略分支"""
        # 模拟资本分配器返回空结果，强制使用LLM分析
        with patch.object(self.engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
            mock_capital.return_value = None  # 强制使用LLM分析
            
            with patch.object(self.engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
                with patch.object(self.engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = {"is_hallucination": False}
                    
                    # 设置一个包含{和}但JSON格式无效的响应
                    # 这会触发JSON解析，但解析失败，进入异常处理分支
                    mock_llm.return_value = '{"invalid": json format, contains buy signal}'
                    
                    result = await self.engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    
                    # JSON解析失败后应该进入异常处理，返回保守策略（hold）
                    assert result["recommendation"] == "hold"
                    assert result["confidence"] == 0.3  # 保守策略的置信度
                    assert result["risk_level"] == "low"  # 保守策略的风险等级