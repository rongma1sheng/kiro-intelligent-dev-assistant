"""
仓位限制控制测试 - Task 21.4

白皮书依据: 第二章 2.2.3 风险控制矩阵

测试目标:
- 测试最大仓位控制
- 测试单股限制
- 测试行业限制
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from src.brain.soldier_engine_v2 import SoldierEngineV2, SoldierConfig


class TestMaxPositionControl:
    """测试最大仓位控制"""
    
    @pytest.mark.asyncio
    async def test_total_position_within_limit(self):
        """测试总仓位在限制内"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 当前总仓位50%，目标增加10%（但受单股5%限制）
        current_portfolio = {
            'total_position': 0.50,
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        result = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        
        # 验证允许（但被单股限制调整到5%）
        assert result['allowed'] is True
        assert result['adjusted_position'] == 0.05  # 单股限制
        assert len(result['violations']) > 0

    
    @pytest.mark.asyncio
    async def test_total_position_exceeds_limit(self):
        """测试总仓位超限"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 当前总仓位90%，目标增加10%（超过95%限制）
        current_portfolio = {
            'total_position': 0.90,
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        result = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        
        # 验证调整（只能增加5%）
        assert result['allowed'] is True
        assert pytest.approx(result['adjusted_position'], 0.001) == 0.05
        assert len(result['violations']) > 0
        assert any('总仓位超限' in v for v in result['violations'])
    
    @pytest.mark.asyncio
    async def test_different_risk_levels_max_position(self):
        """测试不同风险等级的最大仓位"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.85,
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险：95%限制，但单股限制5%
        result_low = await soldier.check_position_limits(
            '000001', 0.15, current_portfolio, 'low'
        )
        assert result_low['adjusted_position'] == 0.05  # 单股限制
        
        # 中风险：80%限制（已超限）
        result_medium = await soldier.check_position_limits(
            '000001', 0.15, current_portfolio, 'medium'
        )
        assert result_medium['adjusted_position'] == 0.0  # 85% > 80%
        
        # 高风险：60%限制（已超限）
        result_high = await soldier.check_position_limits(
            '000001', 0.15, current_portfolio, 'high'
        )
        assert result_high['adjusted_position'] == 0.0  # 85% > 60%


class TestSingleStockLimit:
    """测试单股限制"""
    
    @pytest.mark.asyncio
    async def test_single_stock_within_limit(self):
        """测试单股仓位在限制内"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险单股限制5%
        result = await soldier.check_position_limits(
            '000001', 0.04, current_portfolio, 'low'
        )
        
        assert result['allowed'] is True
        assert result['adjusted_position'] == 0.04
        assert len(result['violations']) == 0

    
    @pytest.mark.asyncio
    async def test_single_stock_exceeds_limit(self):
        """测试单股仓位超限"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险单股限制5%，目标10%
        result = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        
        assert result['allowed'] is True
        assert result['adjusted_position'] == 0.05  # 调整到5%
        assert any('单股仓位超限' in v for v in result['violations'])
    
    @pytest.mark.asyncio
    async def test_different_risk_levels_single_stock(self):
        """测试不同风险等级的单股限制"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.20,
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险：5%限制
        result_low = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        assert result_low['adjusted_position'] == 0.05
        
        # 中风险：3%限制
        result_medium = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'medium'
        )
        assert result_medium['adjusted_position'] == 0.03
        
        # 高风险：2%限制
        result_high = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'high'
        )
        assert result_high['adjusted_position'] == 0.02


class TestSectorLimit:
    """测试行业限制"""
    
    @pytest.mark.asyncio
    async def test_sector_within_limit(self):
        """测试行业仓位在限制内"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {'finance': 0.20},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险行业限制30%，当前20%，增加5%
        result = await soldier.check_position_limits(
            '000001', 0.05, current_portfolio, 'low'
        )
        
        assert result['allowed'] is True
        assert result['adjusted_position'] == 0.05
        assert len(result['violations']) == 0

    
    @pytest.mark.asyncio
    async def test_sector_exceeds_limit(self):
        """测试行业仓位超限"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {'finance': 0.25},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险行业限制30%，当前25%，目标增加10%
        result = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        
        assert result['allowed'] is True
        assert pytest.approx(result['adjusted_position'], abs=0.001) == 0.05  # 单股限制或行业限制
        assert len(result['violations']) > 0  # 有违规项
    
    @pytest.mark.asyncio
    async def test_different_risk_levels_sector(self):
        """测试不同风险等级的行业限制"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.20,
            'sector_positions': {'finance': 0.18},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险：30%限制
        result_low = await soldier.check_position_limits(
            '000001', 0.15, current_portfolio, 'low'
        )
        assert result_low['adjusted_position'] == 0.05  # 单股限制5%
        
        # 中风险：20%限制
        result_medium = await soldier.check_position_limits(
            '000001', 0.15, current_portfolio, 'medium'
        )
        assert pytest.approx(result_medium['adjusted_position'], 0.001) == 0.02  # 18% + 2% = 20%
        
        # 高风险：15%限制（已超限）
        result_high = await soldier.check_position_limits(
            '000001', 0.15, current_portfolio, 'high'
        )
        assert result_high['adjusted_position'] == 0.0  # 18% > 15%


class TestMultipleConstraints:
    """测试多重约束"""
    
    @pytest.mark.asyncio
    async def test_multiple_constraints_applied(self):
        """测试多重约束同时生效"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 设置接近多个限制的场景
        current_portfolio = {
            'total_position': 0.92,  # 接近95%总仓位限制
            'sector_positions': {'finance': 0.28},  # 接近30%行业限制
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 目标增加10%
        result = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        
        # 应该被多个约束限制
        assert result['adjusted_position'] <= 0.03  # 总仓位限制3%
        assert result['adjusted_position'] <= 0.05  # 单股限制5%
        assert result['adjusted_position'] <= 0.02  # 行业限制2%
        assert len(result['violations']) >= 2



class TestApplyPositionLimits:
    """测试应用仓位限制到交易列表"""
    
    @pytest.mark.asyncio
    async def test_apply_limits_to_trades(self):
        """测试应用限制到交易列表"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        trades = [
            {'symbol': '000001', 'position': 0.04},
            {'symbol': '000002', 'position': 0.03},
            {'symbol': '000003', 'position': 0.02}
        ]
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {},
            'symbol_sectors': {
                '000001': 'finance',
                '000002': 'technology',
                '000003': 'healthcare'
            }
        }
        
        adjusted_trades = await soldier.apply_position_limits(
            trades, current_portfolio, 'low'
        )
        
        # 验证所有交易都通过
        assert len(adjusted_trades) == 3
        assert all(t['position'] <= 0.05 for t in adjusted_trades)
    
    @pytest.mark.asyncio
    async def test_apply_limits_filters_invalid_trades(self):
        """测试过滤无效交易"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        trades = [
            {'symbol': '000001', 'position': 0.10},  # 超过单股限制
            {'symbol': '000002', 'position': 0.03},  # 正常
        ]
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {},
            'symbol_sectors': {
                '000001': 'finance',
                '000002': 'technology'
            }
        }
        
        adjusted_trades = await soldier.apply_position_limits(
            trades, current_portfolio, 'low'
        )
        
        # 验证第一个交易被调整
        assert len(adjusted_trades) == 2
        assert adjusted_trades[0]['adjusted'] is True
        assert adjusted_trades[0]['position'] == 0.05
        assert adjusted_trades[1]['adjusted'] is False


class TestCalculateMaxPosition:
    """测试计算最大可用仓位"""
    
    def test_max_position_calculation(self):
        """测试最大仓位计算"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.50,
            'sector_positions': {'finance': 0.20},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险：总95%，单股5%，行业30%
        max_pos = soldier.calculate_max_position(
            '000001', current_portfolio, 'low'
        )
        
        # 应该取最小值：min(45%, 5%, 10%) = 5%
        assert max_pos == 0.05
    
    def test_max_position_with_sector_constraint(self):
        """测试行业约束下的最大仓位"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.30,
            'sector_positions': {'finance': 0.28},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        # 低风险：行业限制30%，当前28%
        max_pos = soldier.calculate_max_position(
            '000001', current_portfolio, 'low'
        )
        
        # 应该是2%（行业剩余空间）
        assert pytest.approx(max_pos, 0.001) == 0.02
    
    def test_max_position_zero_when_limits_reached(self):
        """测试限制达到时返回0"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        current_portfolio = {
            'total_position': 0.95,  # 已达上限
            'sector_positions': {},
            'symbol_sectors': {'000001': 'finance'}
        }
        
        max_pos = soldier.calculate_max_position(
            '000001', current_portfolio, 'low'
        )
        
        assert max_pos == 0.0


class TestPositionLimitsErrorHandling:
    """测试仓位限制错误处理"""
    
    @pytest.mark.asyncio
    async def test_check_limits_with_invalid_data(self):
        """测试无效数据的错误处理"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 缺少必要字段
        current_portfolio = {}
        
        result = await soldier.check_position_limits(
            '000001', 0.10, current_portfolio, 'low'
        )
        
        # 应该返回结果（使用默认值）
        assert 'allowed' in result
        assert 'adjusted_position' in result
    
    @pytest.mark.asyncio
    async def test_apply_limits_with_empty_trades(self):
        """测试空交易列表"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        trades = []
        current_portfolio = {'total_position': 0.30}
        
        adjusted_trades = await soldier.apply_position_limits(
            trades, current_portfolio, 'low'
        )
        
        assert len(adjusted_trades) == 0
