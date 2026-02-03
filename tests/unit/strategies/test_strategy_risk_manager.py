"""Strategy Risk Manager单元测试

白皮书依据: 第四章 4.2 斯巴达竞技场
测试任务: Task 7.1

测试覆盖:
- Property 11: Position Limit Invariants
- Property 12: Stop Loss Trigger Correctness
- Property 13: Take Profit Trigger Correctness
- Property 14: Liquidity-Adjusted Position Sizing
- Property 23: Slippage Scaling with Order Size
- Property 24: Tier-Based Slippage Baseline
- Property 36: Tier5-6 Liquidity Constraints
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import List, Dict

from src.strategies.strategy_risk_manager import StrategyRiskManager
from src.strategies.data_models import Position, StrategyConfig


class TestStrategyRiskManagerInitialization:
    """测试StrategyRiskManager初始化"""
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False,
            liquidity_threshold=1000000.0,
            max_order_pct_of_volume=0.05
        )
    
    def test_initialization(self, config):
        """测试初始化"""
        manager = StrategyRiskManager(config)
        
        assert manager.config == config
        assert manager.max_position == 0.8
        assert manager.max_single_stock == 0.1
        assert manager.max_industry == 0.3
        assert manager.stop_loss_pct == -0.05
        assert manager.take_profit_pct == 0.10
        assert manager.liquidity_threshold == 1000000.0
        assert manager.max_order_pct_of_volume == 0.05



class TestPositionFiltering:
    """测试仓位过滤功能
    
    Property 11: Position Limit Invariants
    """
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager(self, config):
        """创建StrategyRiskManager实例"""
        return StrategyRiskManager(config)
    
    @pytest.mark.asyncio
    async def test_filter_positions_empty(self, manager):
        """测试空仓位列表"""
        positions = []
        filtered = await manager.filter_positions(positions)
        assert filtered == []
    
    @pytest.mark.asyncio
    async def test_filter_single_stock_limit(self, manager):
        """Property 11.1: 单股仓位限制
        
        验证单股仓位不超过max_single_stock
        """
        positions = [
            Position(
                symbol="000001",
                size=0.15,  # 超过0.1限制
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            )
        ]
        
        filtered = await manager.filter_positions(positions)
        
        assert len(filtered) == 1
        assert filtered[0].size == 0.1  # 应该被调整到max_single_stock
        assert filtered[0].symbol == "000001"
    
    @pytest.mark.asyncio
    async def test_filter_industry_limit(self, manager):
        """Property 11.2: 行业仓位限制
        
        验证单行业仓位不超过max_industry
        """
        positions = [
            Position(
                symbol="000001",
                size=0.15,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.20,
                entry_price=20.0,
                current_price=21.0,
                pnl_pct=0.05,
                holding_days=3,
                industry="tech"
            )
        ]
        
        filtered = await manager.filter_positions(positions)
        
        # tech行业总仓位0.35超过0.3限制，应该按比例缩减
        tech_total = sum(p.size for p in filtered if p.industry == "tech")
        assert tech_total <= 0.3 + 0.001  # 允许浮点误差
    
    @pytest.mark.asyncio
    async def test_filter_total_position_limit(self, manager):
        """Property 11.3: 总仓位限制
        
        验证总仓位不超过max_position
        """
        positions = [
            Position(
                symbol="000001",
                size=0.3,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.3,
                entry_price=20.0,
                current_price=21.0,
                pnl_pct=0.05,
                holding_days=3,
                industry="finance"
            ),
            Position(
                symbol="000003",
                size=0.3,
                entry_price=30.0,
                current_price=31.0,
                pnl_pct=0.033,
                holding_days=2,
                industry="consumer"
            )
        ]
        
        filtered = await manager.filter_positions(positions)
        
        # 总仓位0.9超过0.8限制，应该按比例缩减
        total_position = sum(p.size for p in filtered)
        assert total_position <= 0.8 + 0.001  # 允许浮点误差



class TestPositionLimitCheck:
    """测试仓位限制检查
    
    Property 14: Liquidity-Adjusted Position Sizing
    """
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager(self, config):
        """创建StrategyRiskManager实例"""
        return StrategyRiskManager(config)
    
    @pytest.mark.asyncio
    async def test_check_position_limit_within_limit(self, manager):
        """测试仓位在限制内"""
        adjusted_size = await manager.check_position_limit("000001", 0.08)
        assert adjusted_size == 0.08
    
    @pytest.mark.asyncio
    async def test_check_position_limit_exceeds_limit(self, manager):
        """Property 14: 仓位超限时调整
        
        验证仓位超过max_single_stock时被调整
        """
        adjusted_size = await manager.check_position_limit("000001", 0.15)
        assert adjusted_size == 0.1  # 应该被调整到max_single_stock
    
    @pytest.mark.asyncio
    async def test_check_position_limit_at_boundary(self, manager):
        """测试边界值"""
        adjusted_size = await manager.check_position_limit("000001", 0.1)
        assert adjusted_size == 0.1


class TestStopLossTriggers:
    """测试止损触发
    
    Property 12: Stop Loss Trigger Correctness
    """
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,  # -5%止损
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager(self, config):
        """创建StrategyRiskManager实例"""
        return StrategyRiskManager(config)
    
    @pytest.mark.asyncio
    async def test_stop_loss_not_triggered(self, manager):
        """测试止损未触发"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=9.6,  # -4%，未达到-5%止损线
                pnl_pct=-0.04,
                holding_days=5,
                industry="tech"
            )
        ]
        
        stop_loss_symbols = await manager.check_stop_loss_triggers(positions)
        assert stop_loss_symbols == []
    
    @pytest.mark.asyncio
    async def test_stop_loss_triggered(self, manager):
        """Property 12: 止损触发
        
        验证当pnl_pct <= stop_loss_pct时触发止损
        """
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=9.4,  # -6%，超过-5%止损线
                pnl_pct=-0.06,
                holding_days=5,
                industry="tech"
            )
        ]
        
        stop_loss_symbols = await manager.check_stop_loss_triggers(positions)
        assert len(stop_loss_symbols) == 1
        assert "000001" in stop_loss_symbols
    
    @pytest.mark.asyncio
    async def test_stop_loss_at_boundary(self, manager):
        """测试止损边界值"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=9.5,  # 正好-5%
                pnl_pct=-0.05,
                holding_days=5,
                industry="tech"
            )
        ]
        
        stop_loss_symbols = await manager.check_stop_loss_triggers(positions)
        assert len(stop_loss_symbols) == 1  # 边界值应该触发
        assert "000001" in stop_loss_symbols
    
    @pytest.mark.asyncio
    async def test_stop_loss_multiple_positions(self, manager):
        """测试多个仓位的止损触发"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=9.4,  # -6%，触发
                pnl_pct=-0.06,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.1,
                entry_price=20.0,
                current_price=19.2,  # -4%，不触发
                pnl_pct=-0.04,
                holding_days=3,
                industry="finance"
            ),
            Position(
                symbol="000003",
                size=0.1,
                entry_price=30.0,
                current_price=28.2,  # -6%，触发
                pnl_pct=-0.06,
                holding_days=2,
                industry="consumer"
            )
        ]
        
        stop_loss_symbols = await manager.check_stop_loss_triggers(positions)
        assert len(stop_loss_symbols) == 2
        assert "000001" in stop_loss_symbols
        assert "000003" in stop_loss_symbols
        assert "000002" not in stop_loss_symbols



class TestTakeProfitTriggers:
    """测试止盈触发
    
    Property 13: Take Profit Trigger Correctness
    """
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,  # 10%止盈
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager(self, config):
        """创建StrategyRiskManager实例"""
        return StrategyRiskManager(config)
    
    @pytest.mark.asyncio
    async def test_take_profit_not_triggered(self, manager):
        """测试止盈未触发"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.9,  # +9%，未达到10%止盈线
                pnl_pct=0.09,
                holding_days=5,
                industry="tech"
            )
        ]
        
        take_profit_symbols = await manager.check_take_profit_triggers(positions)
        assert take_profit_symbols == []
    
    @pytest.mark.asyncio
    async def test_take_profit_triggered(self, manager):
        """Property 13: 止盈触发
        
        验证当pnl_pct >= take_profit_pct时触发止盈
        """
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=11.2,  # +12%，超过10%止盈线
                pnl_pct=0.12,
                holding_days=5,
                industry="tech"
            )
        ]
        
        take_profit_symbols = await manager.check_take_profit_triggers(positions)
        assert len(take_profit_symbols) == 1
        assert "000001" in take_profit_symbols
    
    @pytest.mark.asyncio
    async def test_take_profit_at_boundary(self, manager):
        """测试止盈边界值"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=11.0,  # 正好+10%
                pnl_pct=0.10,
                holding_days=5,
                industry="tech"
            )
        ]
        
        take_profit_symbols = await manager.check_take_profit_triggers(positions)
        assert len(take_profit_symbols) == 1  # 边界值应该触发
        assert "000001" in take_profit_symbols
    
    @pytest.mark.asyncio
    async def test_take_profit_multiple_positions(self, manager):
        """测试多个仓位的止盈触发"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=11.2,  # +12%，触发
                pnl_pct=0.12,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.1,
                entry_price=20.0,
                current_price=21.8,  # +9%，不触发
                pnl_pct=0.09,
                holding_days=3,
                industry="finance"
            ),
            Position(
                symbol="000003",
                size=0.1,
                entry_price=30.0,
                current_price=33.3,  # +11%，触发
                pnl_pct=0.11,
                holding_days=2,
                industry="consumer"
            )
        ]
        
        take_profit_symbols = await manager.check_take_profit_triggers(positions)
        assert len(take_profit_symbols) == 2
        assert "000001" in take_profit_symbols
        assert "000003" in take_profit_symbols
        assert "000002" not in take_profit_symbols



class TestSlippageAndImpactCost:
    """测试滑点和冲击成本计算
    
    Property 23: Slippage Scaling with Order Size
    Property 24: Tier-Based Slippage Baseline
    """
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager(self, config):
        """创建StrategyRiskManager实例"""
        return StrategyRiskManager(config)
    
    @pytest.mark.asyncio
    async def test_slippage_tier1_baseline(self, manager):
        """Property 24: Tier1基础滑点
        
        验证Tier1的基础滑点为0.15%
        """
        result = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=1000.0,
            daily_volume=1000000.0,
            tier="tier1_micro"
        )
        
        # 订单占成交量0.1%，滑点应该接近基础滑点0.15%
        assert 0.0015 <= result['slippage_pct'] <= 0.002
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tier,expected_base_slippage", [
        ("tier1_micro", 0.0015),
        ("tier2_small", 0.002),
        ("tier3_medium", 0.004),
        ("tier4_large", 0.005),
        ("tier5_million", 0.010),
        ("tier6_ten_million", 0.020),
    ])
    async def test_slippage_tier_baselines(self, manager, tier, expected_base_slippage):
        """Property 24: 各档位基础滑点
        
        验证不同档位的基础滑点正确
        """
        result = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=1000.0,
            daily_volume=10000000.0,  # 大成交量，订单占比很小
            tier=tier
        )
        
        # 订单占比很小时，滑点应该接近基础滑点
        assert result['slippage_pct'] >= expected_base_slippage
        assert result['slippage_pct'] <= expected_base_slippage * 1.2
    
    @pytest.mark.asyncio
    async def test_slippage_scales_with_order_size(self, manager):
        """Property 23: 滑点随订单大小增加
        
        验证订单越大，滑点越高
        """
        # 小订单
        result_small = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=1000.0,
            daily_volume=1000000.0,
            tier="tier1_micro"
        )
        
        # 中等订单
        result_medium = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=10000.0,
            daily_volume=1000000.0,
            tier="tier1_micro"
        )
        
        # 大订单
        result_large = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=100000.0,
            daily_volume=1000000.0,
            tier="tier1_micro"
        )
        
        # 滑点应该递增
        assert result_small['slippage_pct'] < result_medium['slippage_pct']
        assert result_medium['slippage_pct'] < result_large['slippage_pct']
    
    @pytest.mark.asyncio
    async def test_impact_cost_calculation(self, manager):
        """测试冲击成本计算"""
        result = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=50000.0,
            daily_volume=1000000.0,
            tier="tier1_micro"
        )
        
        assert 'impact_cost_pct' in result
        assert result['impact_cost_pct'] > 0
        # 冲击成本应该小于滑点
        assert result['impact_cost_pct'] < result['slippage_pct']
    
    @pytest.mark.asyncio
    async def test_zero_volume_handling(self, manager):
        """测试零成交量的处理"""
        result = await manager.calculate_slippage_and_impact(
            symbol="000001",
            order_size=1000.0,
            daily_volume=0.0,  # 零成交量
            tier="tier1_micro"
        )
        
        # 应该返回较高的滑点（因为订单占比被视为100%）
        # 实际计算：base_slippage=0.0015, order_volume_ratio=1.0
        # slippage = 0.0015 * (1 + 1.0^0.5) = 0.0015 * 2 = 0.003
        assert result['slippage_pct'] > 0.002



class TestLiquidityFiltering:
    """测试流动性过滤
    
    Property 36: Tier5-6 Liquidity Constraints
    """
    
    @pytest.fixture
    def config_tier5(self):
        """创建Tier5配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier5_million",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def config_tier6(self):
        """创建Tier6配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier6_ten_million",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager_tier5(self, config_tier5):
        """创建Tier5 StrategyRiskManager实例"""
        return StrategyRiskManager(config_tier5)
    
    @pytest.fixture
    def manager_tier6(self, config_tier6):
        """创建Tier6 StrategyRiskManager实例"""
        return StrategyRiskManager(config_tier6)
    
    @pytest.mark.asyncio
    async def test_tier1_no_liquidity_filtering(self):
        """测试Tier1-4不进行流动性过滤"""
        config = StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
        manager = StrategyRiskManager(config)
        
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            )
        ]
        
        market_data = {
            "000001": {
                "daily_volume": 1000000.0,  # 100万，低于Tier5要求
                "turnover_rate": 0.005  # 0.5%，低于Tier5要求
            }
        }
        
        filtered = await manager.filter_by_liquidity(positions, market_data, tier="tier1_micro")
        
        # Tier1不过滤，应该返回所有仓位
        assert len(filtered) == 1
    
    @pytest.mark.asyncio
    async def test_tier5_liquidity_volume_requirement(self, manager_tier5):
        """Property 36.1: Tier5日均成交额要求 >= 5000万
        
        验证Tier5过滤日均成交额 < 5000万的标的
        """
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.1,
                entry_price=20.0,
                current_price=21.0,
                pnl_pct=0.05,
                holding_days=3,
                industry="finance"
            )
        ]
        
        market_data = {
            "000001": {
                "daily_volume": 30_000_000.0,  # 3000万，不满足
                "turnover_rate": 0.02  # 2%，满足
            },
            "000002": {
                "daily_volume": 60_000_000.0,  # 6000万，满足
                "turnover_rate": 0.02  # 2%，满足
            }
        }
        
        filtered = await manager_tier5.filter_by_liquidity(
            positions, market_data, tier="tier5_million"
        )
        
        # 只有000002满足要求
        assert len(filtered) == 1
        assert filtered[0].symbol == "000002"
    
    @pytest.mark.asyncio
    async def test_tier5_liquidity_turnover_requirement(self, manager_tier5):
        """Property 36.2: Tier5换手率要求 >= 1%
        
        验证Tier5过滤换手率 < 1%的标的
        """
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.1,
                entry_price=20.0,
                current_price=21.0,
                pnl_pct=0.05,
                holding_days=3,
                industry="finance"
            )
        ]
        
        market_data = {
            "000001": {
                "daily_volume": 60_000_000.0,  # 6000万，满足
                "turnover_rate": 0.005  # 0.5%，不满足
            },
            "000002": {
                "daily_volume": 60_000_000.0,  # 6000万，满足
                "turnover_rate": 0.015  # 1.5%，满足
            }
        }
        
        filtered = await manager_tier5.filter_by_liquidity(
            positions, market_data, tier="tier5_million"
        )
        
        # 只有000002满足要求
        assert len(filtered) == 1
        assert filtered[0].symbol == "000002"
    
    @pytest.mark.asyncio
    async def test_tier6_liquidity_volume_requirement(self, manager_tier6):
        """Property 36.3: Tier6日均成交额要求 >= 2亿
        
        验证Tier6过滤日均成交额 < 2亿的标的
        """
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.1,
                entry_price=20.0,
                current_price=21.0,
                pnl_pct=0.05,
                holding_days=3,
                industry="finance"
            )
        ]
        
        market_data = {
            "000001": {
                "daily_volume": 150_000_000.0,  # 1.5亿，不满足
                "turnover_rate": 0.03  # 3%，满足
            },
            "000002": {
                "daily_volume": 250_000_000.0,  # 2.5亿，满足
                "turnover_rate": 0.03  # 3%，满足
            }
        }
        
        filtered = await manager_tier6.filter_by_liquidity(
            positions, market_data, tier="tier6_ten_million"
        )
        
        # 只有000002满足要求
        assert len(filtered) == 1
        assert filtered[0].symbol == "000002"
    
    @pytest.mark.asyncio
    async def test_tier6_liquidity_turnover_requirement(self, manager_tier6):
        """Property 36.4: Tier6换手率要求 >= 2%
        
        验证Tier6过滤换手率 < 2%的标的
        """
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            ),
            Position(
                symbol="000002",
                size=0.1,
                entry_price=20.0,
                current_price=21.0,
                pnl_pct=0.05,
                holding_days=3,
                industry="finance"
            )
        ]
        
        market_data = {
            "000001": {
                "daily_volume": 250_000_000.0,  # 2.5亿，满足
                "turnover_rate": 0.015  # 1.5%，不满足
            },
            "000002": {
                "daily_volume": 250_000_000.0,  # 2.5亿，满足
                "turnover_rate": 0.025  # 2.5%，满足
            }
        }
        
        filtered = await manager_tier6.filter_by_liquidity(
            positions, market_data, tier="tier6_ten_million"
        )
        
        # 只有000002满足要求
        assert len(filtered) == 1
        assert filtered[0].symbol == "000002"
    
    @pytest.mark.asyncio
    async def test_missing_market_data(self, manager_tier5):
        """测试缺少市场数据的处理"""
        positions = [
            Position(
                symbol="000001",
                size=0.1,
                entry_price=10.0,
                current_price=10.5,
                pnl_pct=0.05,
                holding_days=5,
                industry="tech"
            )
        ]
        
        market_data = {}  # 空市场数据
        
        filtered = await manager_tier5.filter_by_liquidity(
            positions, market_data, tier="tier5_million"
        )
        
        # 缺少市场数据的标的应该被过滤掉
        assert len(filtered) == 0



class TestEnhancedImpactCost:
    """测试增强版市场冲击成本计算（Tier5-6专用）"""
    
    @pytest.fixture
    def config_tier5(self):
        """创建Tier5配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier5_million",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def config_tier6(self):
        """创建Tier6配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier6_ten_million",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager_tier5(self, config_tier5):
        """创建Tier5 StrategyRiskManager实例"""
        return StrategyRiskManager(config_tier5)
    
    @pytest.fixture
    def manager_tier6(self, config_tier6):
        """创建Tier6 StrategyRiskManager实例"""
        return StrategyRiskManager(config_tier6)
    
    @pytest.mark.asyncio
    async def test_enhanced_impact_cost_tier5(self, manager_tier5):
        """测试Tier5增强版冲击成本计算"""
        market_data = {
            "daily_volume": 100_000_000.0,  # 1亿
            "bid_ask_spread": 0.002  # 0.2%
        }
        
        result = await manager_tier5.calculate_enhanced_impact_cost(
            symbol="000001",
            order_size=5_000_000.0,  # 500万，占5%
            market_data=market_data,
            tier="tier5_million"
        )
        
        assert 'slippage_pct' in result
        assert 'impact_cost_pct' in result
        assert 'total_cost_pct' in result
        assert 'recommended_split' in result
        
        # 验证总成本 = 滑点 + 冲击成本
        assert abs(result['total_cost_pct'] - (result['slippage_pct'] + result['impact_cost_pct'])) < 0.0001
    
    @pytest.mark.asyncio
    async def test_enhanced_impact_cost_tier6(self, manager_tier6):
        """测试Tier6增强版冲击成本计算"""
        market_data = {
            "daily_volume": 200_000_000.0,  # 2亿
            "bid_ask_spread": 0.001  # 0.1%
        }
        
        result = await manager_tier6.calculate_enhanced_impact_cost(
            symbol="000001",
            order_size=20_000_000.0,  # 2000万，占10%
            market_data=market_data,
            tier="tier6_ten_million"
        )
        
        assert 'slippage_pct' in result
        assert 'impact_cost_pct' in result
        assert 'total_cost_pct' in result
        assert 'recommended_split' in result
        
        # Tier6的基础滑点应该更高
        assert result['slippage_pct'] > 0.02
    
    @pytest.mark.asyncio
    async def test_order_split_recommendation_small_order(self, manager_tier5):
        """测试小订单的拆分建议"""
        market_data = {
            "daily_volume": 100_000_000.0,
            "bid_ask_spread": 0.001
        }
        
        result = await manager_tier5.calculate_enhanced_impact_cost(
            symbol="000001",
            order_size=2_000_000.0,  # 200万，占2%
            market_data=market_data,
            tier="tier5_million"
        )
        
        # 小订单不需要拆分
        assert result['recommended_split'] == 1
    
    @pytest.mark.asyncio
    async def test_order_split_recommendation_medium_order(self, manager_tier5):
        """测试中等订单的拆分建议"""
        market_data = {
            "daily_volume": 100_000_000.0,
            "bid_ask_spread": 0.001
        }
        
        result = await manager_tier5.calculate_enhanced_impact_cost(
            symbol="000001",
            order_size=7_000_000.0,  # 700万，占7%
            market_data=market_data,
            tier="tier5_million"
        )
        
        # 中等订单建议拆分3单
        assert result['recommended_split'] == 3
    
    @pytest.mark.asyncio
    async def test_order_split_recommendation_large_order(self, manager_tier5):
        """测试大订单的拆分建议"""
        market_data = {
            "daily_volume": 100_000_000.0,
            "bid_ask_spread": 0.001
        }
        
        result = await manager_tier5.calculate_enhanced_impact_cost(
            symbol="000001",
            order_size=15_000_000.0,  # 1500万，占15%
            market_data=market_data,
            tier="tier5_million"
        )
        
        # 大订单建议拆分更多
        assert result['recommended_split'] >= 5
    
    @pytest.mark.asyncio
    async def test_tier1_fallback_to_simple_model(self):
        """测试Tier1-4使用简化模型"""
        config = StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
        manager = StrategyRiskManager(config)
        
        market_data = {
            "daily_volume": 10_000_000.0,
            "bid_ask_spread": 0.001
        }
        
        result = await manager.calculate_enhanced_impact_cost(
            symbol="000001",
            order_size=1_000_000.0,
            market_data=market_data,
            tier="tier1_micro"
        )
        
        # Tier1应该使用简化模型，不返回recommended_split
        assert 'slippage_pct' in result
        assert 'impact_cost_pct' in result
        # 简化模型不返回total_cost_pct和recommended_split
        assert 'total_cost_pct' not in result
        assert 'recommended_split' not in result


class TestExecutionAlgorithmSuggestion:
    """测试执行算法建议（Tier6专用）"""
    
    @pytest.fixture
    def config_tier6(self):
        """创建Tier6配置"""
        return StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier6_ten_million",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
    
    @pytest.fixture
    def manager_tier6(self, config_tier6):
        """创建Tier6 StrategyRiskManager实例"""
        return StrategyRiskManager(config_tier6)
    
    def test_market_algorithm_for_small_order(self, manager_tier6):
        """测试小订单使用MARKET算法"""
        algorithm = manager_tier6.suggest_execution_algorithm(
            order_size=2_000_000.0,  # 200万
            daily_volume=200_000_000.0,  # 2亿，占1%
            tier="tier6_ten_million"
        )
        
        assert algorithm == "MARKET"
    
    def test_twap_algorithm_for_medium_order(self, manager_tier6):
        """测试中等订单使用TWAP算法"""
        algorithm = manager_tier6.suggest_execution_algorithm(
            order_size=6_000_000.0,  # 600万
            daily_volume=200_000_000.0,  # 2亿，占3%
            tier="tier6_ten_million"
        )
        
        assert algorithm == "TWAP"
    
    def test_vwap_algorithm_for_large_order(self, manager_tier6):
        """测试大订单使用VWAP算法"""
        algorithm = manager_tier6.suggest_execution_algorithm(
            order_size=14_000_000.0,  # 1400万
            daily_volume=200_000_000.0,  # 2亿，占7%
            tier="tier6_ten_million"
        )
        
        assert algorithm == "VWAP"
    
    def test_pov_algorithm_for_very_large_order(self, manager_tier6):
        """测试超大订单使用POV算法"""
        algorithm = manager_tier6.suggest_execution_algorithm(
            order_size=25_000_000.0,  # 2500万
            daily_volume=200_000_000.0,  # 2亿，占12.5%
            tier="tier6_ten_million"
        )
        
        assert algorithm == "POV"
    
    def test_tier1_always_market(self):
        """测试Tier1-5始终使用MARKET算法"""
        config = StrategyConfig(
            strategy_name="test_strategy",
            capital_tier="tier1_micro",
            max_position=0.8,
            max_single_stock=0.1,
            max_industry=0.3,
            stop_loss_pct=-0.05,
            take_profit_pct=0.10,
            trailing_stop_enabled=False
        )
        manager = StrategyRiskManager(config)
        
        # 即使是大订单，Tier1也使用MARKET
        algorithm = manager.suggest_execution_algorithm(
            order_size=5_000_000.0,
            daily_volume=10_000_000.0,  # 占50%
            tier="tier1_micro"
        )
        
        assert algorithm == "MARKET"
    
    def test_zero_volume_handling(self, manager_tier6):
        """测试零成交量的处理"""
        algorithm = manager_tier6.suggest_execution_algorithm(
            order_size=1_000_000.0,
            daily_volume=0.0,  # 零成交量
            tier="tier6_ten_million"
        )
        
        # 零成交量时，订单占比视为100%，应该使用POV
        assert algorithm == "POV"
