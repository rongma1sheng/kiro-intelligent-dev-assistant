# -*- coding: utf-8 -*-
"""
Smart Position Builder 缺失行覆盖测试
目标：覆盖第18, 547-552, 558-563行，将覆盖率从95.25%提升到100%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.strategies.smart_position_builder import SmartPositionBuilder, MarketMakerPhase, MarketMakerSignal, PositionProtector


class TestSmartPositionBuilderMissingLines:
    """专门测试Smart Position Builder缺失行的测试套件"""
    
    def setup_method(self):
        """测试前置设置"""
        self.builder = SmartPositionBuilder()
        self.protector = PositionProtector(self.builder)
        
    def test_type_checking_import_line_18(self):
        """测试第18行：TYPE_CHECKING导入的使用"""
        # 验证TYPE_CHECKING相关的导入和类型注解能正常工作
        from typing import TYPE_CHECKING
        
        # 创建一个使用了类型注解的实例
        builder = SmartPositionBuilder()
        protector = PositionProtector(builder)
        
        # 测试设置风险管理器（这会使用TYPE_CHECKING导入的类型）
        mock_risk_manager = Mock()
        protector.set_risk_manager(mock_risk_manager)
        assert protector.risk_manager == mock_risk_manager
        
    def test_distribution_phase_medium_confidence_lines_547_552(self):
        """测试第547-552行：出货阶段中等置信度的处理"""
        # 创建出货阶段的中等置信度信号
        # 出货阶段条件：volume_ratio > 2.0, abs(price_change) < 0.01, large_sell_ratio > 0.35
        # 置信度公式：confidence = min(0.95, volume_ratio * 0.3 + large_sell_ratio * 0.7)
        # 要获得中等置信度（0.70-0.89），设置：volume_ratio=2.1, large_sell_ratio=0.36
        # confidence = 2.1*0.3 + 0.36*0.7 = 0.63 + 0.252 = 0.882
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 2100000,  # volume_ratio = 2.1 > 2.0，满足出货阶段条件
            "avg_volume": 1000000,
            "price_change": 0.005,  # abs(price_change) < 0.01，满足出货阶段条件
            "volatility": 0.02,
            "large_buy_ratio": 0.15,
            "large_sell_ratio": 0.36  # > 0.35，满足出货阶段条件，置信度约0.88
        })
        
        # 验证返回了减仓建议（第547-552行的逻辑）
        assert result["action"] == "reduce"
        assert result["urgency"] == "high"
        assert result["reduce_ratio"] == 0.70
        assert "疑似主力出货" in result["reason"]
        
    def test_distribution_phase_confidence_boundaries(self):
        """测试出货阶段不同置信度边界"""
        # 测试高置信度（>= 0.90）
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 2500000,  # volume_ratio = 2.5
            "avg_volume": 1000000,
            "price_change": 0.005,  # 满足出货阶段条件
            "volatility": 0.02,
            "large_buy_ratio": 0.1,
            "large_sell_ratio": 0.4  # confidence = 2.5*0.3 + 0.4*0.7 = 0.75 + 0.28 = 1.03 -> 0.95
        })
        assert result["action"] == "exit"  # 高置信度应该清仓
        
        # 测试中等置信度（0.70 <= confidence < 0.90）
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 2100000,  # volume_ratio = 2.1 > 2.0，满足出货阶段条件
            "avg_volume": 1000000,
            "price_change": 0.005,  # 满足出货阶段条件
            "volatility": 0.02,
            "large_buy_ratio": 0.15,
            "large_sell_ratio": 0.36  # confidence = 2.1*0.3 + 0.36*0.7 = 0.63 + 0.252 = 0.882
        })
        assert result["action"] == "reduce"  # 中等置信度应该减仓
        assert result["reduce_ratio"] == 0.70
        
    def test_markup_phase_high_confidence_lines_558_563(self):
        """测试第558-563行：拉升阶段高置信度的处理"""
        # 创建拉升阶段的高置信度信号
        # 拉升阶段条件：volume_ratio > 1.2, price_change > 0.03, large_buy_ratio > 0.25
        # 置信度公式：confidence = min(0.9, price_change * 10 * 0.5 + large_buy_ratio * 0.5)
        # 要获得高置信度（>= 0.80），设置：price_change=0.08, large_buy_ratio=0.3
        # confidence = min(0.9, 0.08*10*0.5 + 0.3*0.5) = min(0.9, 0.4 + 0.15) = 0.55 (太低)
        # 设置：price_change=0.12, large_buy_ratio=0.4
        # confidence = min(0.9, 0.12*10*0.5 + 0.4*0.5) = min(0.9, 0.6 + 0.2) = 0.8
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 1500000,  # volume_ratio = 1.5 > 1.2，满足拉升阶段条件
            "avg_volume": 1000000,
            "price_change": 0.12,  # > 0.03，满足拉升阶段条件
            "volatility": 0.03,
            "large_buy_ratio": 0.4,  # > 0.25，满足拉升阶段条件，置信度=0.8
            "large_sell_ratio": 0.1
        })
        
        # 验证返回了减仓建议（第558-563行的逻辑）
        assert result["action"] == "reduce"
        assert result["urgency"] == "medium"
        assert result["reduce_ratio"] == 0.30
        assert "高位拉升" in result["reason"]
        assert "部分止盈" in result["reason"]
        
    def test_markup_phase_confidence_boundaries(self):
        """测试拉升阶段不同置信度边界"""
        # 测试高置信度（>= 0.80）- 触发558-563行
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 1500000,  # volume_ratio = 1.5 > 1.2
            "avg_volume": 1000000,
            "price_change": 0.12,  # > 0.03，满足拉升阶段条件
            "volatility": 0.03,
            "large_buy_ratio": 0.4,  # > 0.25，confidence = 0.12*10*0.5 + 0.4*0.5 = 0.8
            "large_sell_ratio": 0.1
        })
        
        assert result["action"] == "reduce"
        assert result["reduce_ratio"] == 0.30
        assert "高位拉升" in result["reason"]
        
        # 测试中等置信度（< 0.80）
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 1300000,  # volume_ratio = 1.3 > 1.2
            "avg_volume": 1000000,
            "price_change": 0.05,  # > 0.03，满足拉升阶段条件
            "volatility": 0.025,
            "large_buy_ratio": 0.3,  # > 0.25，confidence = 0.05*10*0.5 + 0.3*0.5 = 0.25 + 0.15 = 0.4
            "large_sell_ratio": 0.1
        })
        
        # 应该是hold，因为置信度不够高
        assert result["action"] == "hold"
        
    def test_wash_out_phase_handling(self):
        """测试洗筹阶段的处理"""
        # 创建洗筹阶段信号
        # 洗筹阶段条件：volume_ratio < 0.7, volatility > 0.03, price_change < 0
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 600000,  # volume_ratio = 0.6 < 0.7，满足洗筹阶段条件
            "avg_volume": 1000000,
            "price_change": -0.02,  # < 0，满足洗筹阶段条件
            "volatility": 0.04,  # > 0.03，满足洗筹阶段条件
            "large_buy_ratio": 0.2,
            "large_sell_ratio": 0.2
        })
        
        # 验证洗筹阶段的处理
        assert result["action"] == "hold"
        assert result["urgency"] == "low"
        assert "主力洗筹" in result["reason"]
        
    def test_accumulation_phase_handling(self):
        """测试吸筹阶段的处理"""
        # 创建吸筹阶段信号
        # 吸筹阶段条件：volume_ratio > 1.5, abs(price_change) < 0.02, large_buy_ratio > 0.3
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 1800000,  # volume_ratio = 1.8 > 1.5，满足吸筹阶段条件
            "avg_volume": 1000000,
            "price_change": 0.01,  # abs(0.01) < 0.02，满足吸筹阶段条件
            "volatility": 0.015,
            "large_buy_ratio": 0.35,  # > 0.3，满足吸筹阶段条件
            "large_sell_ratio": 0.15
        })
        
        # 验证吸筹阶段的处理（通常是持有）
        assert result["action"] == "hold"
        assert "主力吸筹" in result["reason"]
        
    def test_edge_case_confidence_values(self):
        """测试边界置信度值"""
        # 测试恰好0.90的置信度（出货阶段）
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 2400000,  # volume_ratio = 2.4
            "avg_volume": 1000000,
            "price_change": 0.005,  # 满足出货阶段条件
            "volatility": 0.02,
            "large_buy_ratio": 0.1,
            "large_sell_ratio": 0.39  # confidence = 2.4*0.3 + 0.39*0.7 = 0.72 + 0.273 = 0.993 -> 0.95
        })
        # 0.95应该被认为是高置信度
        assert result["action"] == "exit"
        
        # 测试恰好低于0.90的置信度
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 2100000,  # volume_ratio = 2.1 > 2.0，满足出货阶段条件
            "avg_volume": 1000000,
            "price_change": 0.005,  # 满足出货阶段条件
            "volatility": 0.02,
            "large_buy_ratio": 0.12,
            "large_sell_ratio": 0.36  # confidence = 2.1*0.3 + 0.36*0.7 = 0.63 + 0.252 = 0.882
        })
        # 应该触发中等置信度的逻辑
        assert result["action"] == "reduce"
        assert result["reduce_ratio"] == 0.70
        
    def test_logging_coverage(self):
        """测试日志记录的覆盖"""
        with patch('src.strategies.smart_position_builder.logger') as mock_logger:
            # 测试出货阶段中等置信度的日志
            result = self.protector.monitor_position("TEST", 1000.0, {
                "volume": 2100000,  # volume_ratio = 2.1 > 2.0，满足出货阶段条件
                "avg_volume": 1000000,
                "price_change": 0.005,  # 满足出货阶段条件
                "volatility": 0.02,
                "large_buy_ratio": 0.15,
                "large_sell_ratio": 0.36  # 满足出货阶段条件
            })
            
            # 验证日志被调用
            assert mock_logger.warning.called or mock_logger.info.called or mock_logger.critical.called
            
            # 测试拉升阶段高置信度的日志
            result = self.protector.monitor_position("TEST", 1000.0, {
                "volume": 1500000,  # volume_ratio = 1.5
                "avg_volume": 1000000,
                "price_change": 0.12,  # 满足拉升阶段条件
                "volatility": 0.03,
                "large_buy_ratio": 0.4,  # 满足拉升阶段条件
                "large_sell_ratio": 0.1
            })
            
            # 验证拉升阶段的日志
            assert mock_logger.info.called or mock_logger.warning.called
            
    def test_comprehensive_phase_coverage(self):
        """全面测试所有阶段的覆盖"""
        phases_and_market_data = [
            # 吸筹阶段
            {
                "volume": 1800000,  # volume_ratio = 1.8 > 1.5
                "avg_volume": 1000000,
                "price_change": 0.01,  # abs(0.01) < 0.02
                "volatility": 0.015,
                "large_buy_ratio": 0.35,  # > 0.3
                "large_sell_ratio": 0.15
            },
            # 洗筹阶段
            {
                "volume": 600000,  # volume_ratio = 0.6 < 0.7
                "avg_volume": 1000000,
                "price_change": -0.02,  # < 0
                "volatility": 0.04,  # > 0.03
                "large_buy_ratio": 0.2,
                "large_sell_ratio": 0.2
            },
            # 拉升阶段（高置信度）
            {
                "volume": 1500000,  # volume_ratio = 1.5 > 1.2
                "avg_volume": 1000000,
                "price_change": 0.12,  # > 0.03
                "volatility": 0.03,
                "large_buy_ratio": 0.4,  # > 0.25
                "large_sell_ratio": 0.1
            },
            # 出货阶段（中等置信度）
            {
                "volume": 2000000,  # volume_ratio = 2.0 > 2.0
                "avg_volume": 1000000,
                "price_change": 0.005,  # abs(0.005) < 0.01
                "volatility": 0.02,
                "large_buy_ratio": 0.15,
                "large_sell_ratio": 0.36  # > 0.35
            }
        ]
        
        for market_data in phases_and_market_data:
            result = self.protector.monitor_position("TEST", 1000.0, market_data)
            
            # 验证每个阶段都有有效的结果
            assert result is not None
            assert "action" in result
            assert "urgency" in result
            assert "reason" in result
            
    def test_risk_manager_integration(self):
        """测试风险管理器集成（涉及TYPE_CHECKING导入）"""
        # 创建模拟的风险管理器
        mock_risk_manager = Mock()
        mock_risk_manager.validate_position.return_value = True
        mock_risk_manager.calculate_max_position.return_value = 0.1
        mock_risk_manager.set_exit_mode = Mock()
        
        # 设置风险管理器
        self.protector.set_risk_manager(mock_risk_manager)
        
        # 创建出货信号并处理
        result = self.protector.monitor_position("TEST", 1000.0, {
            "volume": 2100000,  # volume_ratio = 2.1 > 2.0，满足出货阶段条件
            "avg_volume": 1000000,
            "price_change": 0.005,  # 满足出货阶段条件
            "volatility": 0.02,
            "large_buy_ratio": 0.15,
            "large_sell_ratio": 0.36  # 满足出货阶段条件
        })
        
        # 验证风险管理器被正确使用
        assert result is not None
        # 验证风险管理器的set_exit_mode方法被调用（出货阶段会触发）
        mock_risk_manager.set_exit_mode.assert_called()