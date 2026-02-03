#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试文本解析逻辑
"""

def test_text_parsing(response):
    """测试文本解析逻辑"""
    print(f"Testing: '{response}'")
    print(f"Lower case: '{response.lower()}'")
    
    recommendation = "hold"
    if "buy" in response.lower():
        recommendation = "buy"
        print(f"Found 'buy' in response")
    elif "sell" in response.lower():
        recommendation = "sell"
        print(f"Found 'sell' in response")
    elif "reduce" in response.lower():
        recommendation = "reduce"
        print(f"Found 'reduce' in response")
    else:
        print(f"No keywords found, defaulting to 'hold'")
    
    print(f"Result: {recommendation}")
    print("-" * 50)
    return recommendation

# 测试用例
test_cases = [
    "Strong recommendation to SELL position now",
    "Strong recommendation for analysis to SELL position",
    "buy and sell signals are mixed, but overall buy",
    "strong buy signal",
    "neutral market conditions",
    "recommendation to sell",
    "reduce position",
    "BUY NOW!",
    "time to SELL",
    "REDUCE EXPOSURE",
    "no clear direction",
    "",
    "random text without keywords"
]

for case in test_cases:
    test_text_parsing(case)