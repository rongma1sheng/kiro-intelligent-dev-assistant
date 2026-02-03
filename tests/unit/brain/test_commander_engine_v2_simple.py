# -*- coding: utf-8 -*-
"""
Commander Engine V2 简化测试 - 专注覆盖缺失行
"""

import pytest
from unittest.mock import Mock, patch
from src.brain.commander_engine_v2 import CommanderEngineV2


class TestCommanderEngineV2Simple:
    """简化的Commander Engine V2测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.engine = CommanderEngineV2()
        
    def test_text_parsing_default_hold(self):
        """测试文本解析默认返回hold"""
        with patch.object(self.engine, '_call_llm') as mock_llm:
            # 设置不包含关键词的响应
            mock_llm.return_value = "neutral market analysis"
            
            # 这应该触发简单文本解析并返回hold
            result = self.engine.analyze_strategy({
                "symbol": "TEST",
                "price": 100.0,
                "volume": 1000
            })
            
            assert result.recommendation == "hold"
            
    def test_risk_level_default_medium(self):
        """测试风险等级默认返回medium"""
        # 测试未知tier返回medium
        risk_level = self.engine._determine_risk_level("unknown_tier")
        assert risk_level == "medium"
        
        # 测试tier1_small返回medium
        risk_level = self.engine._determine_risk_level("tier1_small")
        assert risk_level == "medium"