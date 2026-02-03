#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试SmartPositionBuilder的阶段检测逻辑
"""

from src.strategies.smart_position_builder import SmartPositionBuilder, PositionProtector

def test_distribution_phase_detection():
    """测试出货阶段检测"""
    builder = SmartPositionBuilder()
    protector = PositionProtector(builder)
    
    # 测试不同的参数组合
    test_cases = [
        {
            "name": "测试1: volume_ratio=2.0, price_change=0.005, large_sell_ratio=0.36",
            "data": {
                "volume": 2000000,
                "avg_volume": 1000000,
                "price_change": 0.005,
                "volatility": 0.02,
                "large_buy_ratio": 0.15,
                "large_sell_ratio": 0.36
            }
        },
        {
            "name": "测试2: volume_ratio=2.1, price_change=0.008, large_sell_ratio=0.4",
            "data": {
                "volume": 2100000,
                "avg_volume": 1000000,
                "price_change": 0.008,
                "volatility": 0.02,
                "large_buy_ratio": 0.1,
                "large_sell_ratio": 0.4
            }
        },
        {
            "name": "测试3: volume_ratio=2.5, price_change=0.005, large_sell_ratio=0.4",
            "data": {
                "volume": 2500000,
                "avg_volume": 1000000,
                "price_change": 0.005,
                "volatility": 0.02,
                "large_buy_ratio": 0.1,
                "large_sell_ratio": 0.4
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print("=" * 60)
        
        # 先测试阶段检测
        signal = builder.detect_market_maker_phase("TEST", test_case['data'])
        print(f"检测到的阶段: {signal.phase}")
        print(f"置信度: {signal.confidence:.3f}")
        print(f"成交量比率: {signal.volume_ratio:.2f}")
        
        # 再测试仓位监控
        result = protector.monitor_position("TEST", 1000.0, test_case['data'])
        print(f"建议操作: {result['action']}")
        print(f"紧急程度: {result['urgency']}")
        print(f"减仓比例: {result.get('reduce_ratio', 0)}")
        print(f"原因: {result['reason']}")

if __name__ == "__main__":
    test_distribution_phase_detection()