#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的文本解析测试
"""

import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.brain.commander_engine_v2 import CommanderEngineV2

async def test_text_parsing_directly():
    """直接测试文本解析方法"""
    engine = CommanderEngineV2()
    
    # 测试用例
    test_cases = [
        ("Strong recommendation to SELL position now", "sell"),
        ("strong buy signal", "buy"),
        ("reduce position", "reduce"),
        ("neutral market conditions", "hold"),
        ("", "hold")
    ]
    
    market_data = {
        "index_level": 3000,
        "volatility": 0.02,
        "volume": 1000000
    }
    
    for response_text, expected in test_cases:
        print(f"\nTesting: '{response_text}'")
        result = engine._parse_llm_response(response_text, market_data)
        print(f"Expected: {expected}, Got: {result.recommendation}")
        assert result.recommendation == expected, f"Failed for '{response_text}'"
    
    print("\n✅ All direct text parsing tests passed!")

async def test_full_analysis_with_mocks():
    """测试完整的分析流程"""
    engine = CommanderEngineV2()
    
    # 模拟所有依赖
    with patch.object(engine.capital_integration, 'analyze_strategy_with_capital_context', new_callable=AsyncMock) as mock_capital:
        mock_capital.return_value = None  # 强制使用LLM分析
        
        with patch.object(engine.llm_gateway, 'generate_cloud', new_callable=AsyncMock) as mock_llm:
            with patch.object(engine.hallucination_filter, 'detect_hallucination', new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = {"is_hallucination": False}
                
                # 测试用例
                test_cases = [
                    ("Strong recommendation to SELL position now", "sell"),
                    ("strong buy signal", "buy"),
                    ("reduce position", "reduce"),
                    ("neutral market conditions", "hold")
                ]
                
                for response_text, expected in test_cases:
                    print(f"\nTesting full analysis: '{response_text}'")
                    mock_llm.return_value = response_text
                    
                    result = await engine.analyze_strategy({
                        "index_level": 3000,
                        "volatility": 0.02,
                        "volume": 1000000
                    })
                    
                    print(f"Expected: {expected}, Got: {result['recommendation']}")
                    if result['recommendation'] != expected:
                        print(f"❌ FAILED for '{response_text}'")
                        print(f"Full result: {result}")
                    else:
                        print(f"✅ PASSED")

if __name__ == "__main__":
    print("Testing direct text parsing...")
    asyncio.run(test_text_parsing_directly())
    
    print("\n" + "="*50)
    print("Testing full analysis with mocks...")
    asyncio.run(test_full_analysis_with_mocks())