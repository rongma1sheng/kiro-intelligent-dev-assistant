"""RiskControlSystem单元测试

白皮书依据: 第六章 6.3 风险控制系统

测试覆盖:
- 仓位限制检查
- 止损止盈机制
- 流动性约束
- 紧急熔断
- 风险限额管理
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from enum import Enum

from src.execution.risk_control_system import (
    RiskControlSystem,
    RiskLevel,
    RiskCheckType,
    RiskCheckResult,
    PositionRisk,
    RiskLimit,
    Position,
    RiskControlError,
    RiskViolationError,
    EmergencyShutdownError,
)


# ============== 测试夹具 ==============

class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class MockOrder:
    """模拟订单"""
    symbol: str
    quantity: float
    price: float
    side: OrderSide
    sector: str = ""
    avg_volume: float = 0


@pytest.fixture
def risk_control_system():
    """创建风控系统实例"""
    return RiskControlSystem(
        total_capital=1000000.0,
        max_position_ratio=0.20,
        max_single_stock_ratio=0.10,
        max_sector_ratio=0.30,
        stop_loss_ratio=0.08,
        take_profit_ratio=0.20,
        daily_loss_limit=0.05,
        margin_limit=0.30,
        min_liquidity_ratio=0.01,
    )


@pytest.fixture
def risk_control_with_event_bus():
    """创建带事件总线的风控系统"""
    event_bus = AsyncMock()
    return RiskControlSystem(
        total_capital=1000000.0,
        event_bus=event_bus
    )


@pytest.fixture
def sample_buy_order():
    """创建买入订单"""
    return MockOrder(
        symbol="600000.SH",
        quantity=1000,
        price=10.0,
        side=OrderSide.BUY,
        sector="金融",
        avg_volume=10000000
    )


@pytest.fixture
def sample_sell_order():
    """创建卖出订单"""
    return MockOrder(
        symbol="600000.SH",
        quantity=500,
        price=10.0,
        side=OrderSide.SELL,
        sector="金融",
        avg_volume=10000000
    )


# ============== 初始化测试 ==============

class TestRiskControlSystemInit:
    """测试风控系统初始化"""
    
    def test_init_with_default_params(self):
        """测试默认参数初始化"""
        rcs = RiskControlSystem()
        
        assert rcs.total_capital == 1000000.0
        assert rcs.risk_limits['max_position_ratio'] == 0.20
        assert rcs.risk_limits['max_single_stock_ratio'] == 0.10
        assert rcs.risk_limits['stop_loss_ratio'] == 0.08
        assert rcs.risk_level == RiskLevel.LOW
        assert not rcs.emergency_shutdown_active
    
    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        rcs = RiskControlSystem(
            total_capital=500000.0,
            max_position_ratio=0.50,
            max_single_stock_ratio=0.15,
            stop_loss_ratio=0.10
        )
        
        assert rcs.total_capital == 500000.0
        assert rcs.risk_limits['max_position_ratio'] == 0.50
        assert rcs.risk_limits['max_single_stock_ratio'] == 0.15
        assert rcs.risk_limits['stop_loss_ratio'] == 0.10
    
    def test_init_invalid_total_capital(self):
        """测试无效总资本"""
        with pytest.raises(ValueError, match="总资本必须大于0"):
            RiskControlSystem(total_capital=0)
        
        with pytest.raises(ValueError, match="总资本必须大于0"):
            RiskControlSystem(total_capital=-100000)
    
    def test_init_invalid_position_ratio(self):
        """测试无效仓位比例"""
        with pytest.raises(ValueError, match="最大仓位比例必须在"):
            RiskControlSystem(max_position_ratio=0)
        
        with pytest.raises(ValueError, match="最大仓位比例必须在"):
            RiskControlSystem(max_position_ratio=1.5)
    
    def test_init_invalid_single_stock_ratio(self):
        """测试无效单股比例"""
        with pytest.raises(ValueError, match="单股最大仓位比例必须在"):
            RiskControlSystem(max_single_stock_ratio=0)
        
        with pytest.raises(ValueError, match="单股最大仓位比例必须在"):
            RiskControlSystem(max_single_stock_ratio=1.5)
    
    def test_init_invalid_stop_loss_ratio(self):
        """测试无效止损比例"""
        with pytest.raises(ValueError, match="止损比例必须在"):
            RiskControlSystem(stop_loss_ratio=0)
        
        with pytest.raises(ValueError, match="止损比例必须在"):
            RiskControlSystem(stop_loss_ratio=1.5)


# ============== 订单风控检查测试 ==============

class TestCheckOrder:
    """测试订单风控检查"""
    
    @pytest.mark.asyncio
    async def test_check_order_pass(self, risk_control_system, sample_buy_order):
        """测试订单检查通过"""
        result = await risk_control_system.check_order(sample_buy_order)
        
        assert result['passed'] is True
        assert result['reason'] == ''
        assert result['risk_level'] == 'low'
    
    @pytest.mark.asyncio
    async def test_check_order_emergency_shutdown(self, risk_control_system, sample_buy_order):
        """测试紧急熔断时拒绝订单"""
        await risk_control_system.emergency_shutdown("测试熔断")
        
        result = await risk_control_system.check_order(sample_buy_order)
        
        assert result['passed'] is False
        assert "紧急熔断已激活" in result['reason']
        assert result['risk_level'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_check_order_capital_insufficient(self, risk_control_system):
        """测试资金不足"""
        # 创建超大订单
        large_order = MockOrder(
            symbol="600000.SH",
            quantity=100000,
            price=100.0,  # 1000万，超过总资本
            side=OrderSide.BUY
        )
        
        result = await risk_control_system.check_order(large_order)
        
        assert result['passed'] is False
        assert "资金不足" in result['reason']
    
    @pytest.mark.asyncio
    async def test_check_order_position_limit_exceeded(self, risk_control_system):
        """测试总仓位超限"""
        # 先添加一些持仓
        risk_control_system.update_position(
            symbol="600001.SH",
            quantity=10000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        # 创建会超过20%仓位限制的订单
        order = MockOrder(
            symbol="600002.SH",
            quantity=15000,
            price=10.0,  # 15万，加上已有10万=25万，超过20%
            side=OrderSide.BUY
        )
        
        result = await risk_control_system.check_order(order)
        
        assert result['passed'] is False
        assert "总仓位超限" in result['reason']
    
    @pytest.mark.asyncio
    async def test_check_order_single_stock_limit_exceeded(self, risk_control_system):
        """测试单股仓位超限"""
        # 创建超过10%单股限制的订单
        order = MockOrder(
            symbol="600000.SH",
            quantity=15000,
            price=10.0,  # 15万，超过10%
            side=OrderSide.BUY
        )
        
        result = await risk_control_system.check_order(order)
        
        assert result['passed'] is False
        assert "单股仓位超限" in result['reason']
    
    @pytest.mark.asyncio
    async def test_check_order_sector_limit_exceeded(self, risk_control_system):
        """测试行业仓位超限"""
        # 先添加同行业持仓
        risk_control_system.update_position(
            symbol="600001.SH",
            quantity=20000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        # 创建会超过30%行业限制的订单
        order = MockOrder(
            symbol="600002.SH",
            quantity=15000,
            price=10.0,  # 15万，加上已有20万=35万，超过30%
            side=OrderSide.BUY,
            sector="金融"
        )
        
        result = await risk_control_system.check_order(order)
        
        assert result['passed'] is False
        assert "行业仓位超限" in result['reason']
    
    @pytest.mark.asyncio
    async def test_check_order_liquidity_insufficient(self, risk_control_system):
        """测试流动性不足"""
        # 创建订单量超过日均成交量1%的订单
        order = MockOrder(
            symbol="600000.SH",
            quantity=200000,  # 20万股
            price=10.0,
            side=OrderSide.BUY,
            avg_volume=1000000  # 日均100万股，订单占20%
        )
        
        result = await risk_control_system.check_order(order)
        
        assert result['passed'] is False
        assert "流动性不足" in result['reason']
    
    @pytest.mark.asyncio
    async def test_check_order_daily_loss_limit(self, risk_control_system, sample_buy_order):
        """测试日亏损限制"""
        # 设置日亏损超过5%
        risk_control_system.update_daily_pnl(-60000)  # 6%亏损
        
        result = await risk_control_system.check_order(sample_buy_order)
        
        assert result['passed'] is False
        assert "日亏损超限" in result['reason']
        assert result['risk_level'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_check_order_sell_always_pass(self, risk_control_system, sample_sell_order):
        """测试卖出订单总是通过仓位检查"""
        # 先添加持仓
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0
        )
        
        result = await risk_control_system.check_order(sample_sell_order)
        
        assert result['passed'] is True


# ============== 止损止盈测试 ==============

class TestStopLossTakeProfit:
    """测试止损止盈机制"""
    
    @pytest.mark.asyncio
    async def test_check_stop_loss_triggered(self, risk_control_with_event_bus):
        """测试止损触发"""
        rcs = risk_control_with_event_bus
        
        # 创建亏损超过8%的持仓
        position = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0  # 亏损10%
        )
        
        result = await rcs.check_stop_loss(position)
        
        assert result is True
        rcs.event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_stop_loss_not_triggered(self, risk_control_system):
        """测试止损未触发"""
        # 创建亏损未超过8%的持仓
        position = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.5  # 亏损5%
        )
        
        result = await risk_control_system.check_stop_loss(position)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_take_profit_triggered(self, risk_control_with_event_bus):
        """测试止盈触发"""
        rcs = risk_control_with_event_bus
        
        # 创建盈利超过20%的持仓
        position = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=12.5  # 盈利25%
        )
        
        result = await rcs.check_take_profit(position)
        
        assert result is True
        rcs.event_bus.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_take_profit_not_triggered(self, risk_control_system):
        """测试止盈未触发"""
        # 创建盈利未超过20%的持仓
        position = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=11.5  # 盈利15%
        )
        
        result = await risk_control_system.check_take_profit(position)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_monitor_position_stop_loss_alert(self, risk_control_with_event_bus):
        """测试持仓监控止损告警"""
        rcs = risk_control_with_event_bus
        
        # 添加亏损持仓
        rcs.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0,  # 亏损10%
            sector="金融"
        )
        
        position_risk = await rcs.monitor_position("600000.SH")
        
        assert position_risk.stop_loss_triggered is True
        assert position_risk.risk_level == RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_monitor_position_take_profit_alert(self, risk_control_with_event_bus):
        """测试持仓监控止盈告警"""
        rcs = risk_control_with_event_bus
        
        # 添加盈利持仓
        rcs.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=12.5,  # 盈利25%
            sector="金融"
        )
        
        position_risk = await rcs.monitor_position("600000.SH")
        
        assert position_risk.take_profit_triggered is True
    
    @pytest.mark.asyncio
    async def test_monitor_position_not_found(self, risk_control_system):
        """测试监控不存在的持仓"""
        with pytest.raises(ValueError, match="持仓不存在"):
            await risk_control_system.monitor_position("999999.SH")


# ============== 风险限额测试 ==============

class TestRiskLimits:
    """测试风险限额管理"""
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_all_ok(self, risk_control_system):
        """测试所有限额正常"""
        limits = await risk_control_system.check_risk_limits()
        
        assert 'total_position' in limits
        assert limits['total_position'].breached is False
        assert limits['daily_loss'].breached is False
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_position_breached(self, risk_control_system):
        """测试仓位限额突破"""
        # 添加超过20%的持仓
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=25000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        limits = await risk_control_system.check_risk_limits()
        
        assert limits['total_position'].breached is True
        assert risk_control_system.risk_level == RiskLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_single_stock_breached(self, risk_control_system):
        """测试单股限额突破"""
        # 添加超过10%的单股持仓
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=15000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        limits = await risk_control_system.check_risk_limits()
        
        assert limits['single_stock_600000.SH'].breached is True
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_sector_breached(self, risk_control_system):
        """测试行业限额突破"""
        # 添加同行业多只股票，超过30%
        risk_control_system.update_position(
            symbol="600001.SH",
            quantity=20000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        risk_control_system.update_position(
            symbol="600002.SH",
            quantity=15000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        limits = await risk_control_system.check_risk_limits()
        
        assert limits['sector_金融'].breached is True
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_daily_loss_breached(self, risk_control_system):
        """测试日亏损限额突破"""
        risk_control_system.update_daily_pnl(-60000)  # 6%亏损
        
        limits = await risk_control_system.check_risk_limits()
        
        assert limits['daily_loss'].breached is True
    
    def test_update_risk_limits(self, risk_control_system):
        """测试更新风险限额"""
        risk_control_system.update_risk_limits(
            max_position_ratio=0.30,
            stop_loss_ratio=0.10
        )
        
        assert risk_control_system.risk_limits['max_position_ratio'] == 0.30
        assert risk_control_system.risk_limits['stop_loss_ratio'] == 0.10
    
    def test_update_risk_limits_unknown_param(self, risk_control_system):
        """测试更新未知参数"""
        # 不应该抛出异常，只是警告
        risk_control_system.update_risk_limits(unknown_param=0.5)
        
        assert 'unknown_param' not in risk_control_system.risk_limits


# ============== 紧急熔断测试 ==============

class TestEmergencyShutdown:
    """测试紧急熔断机制"""
    
    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, risk_control_with_event_bus):
        """测试激活紧急熔断"""
        rcs = risk_control_with_event_bus
        
        await rcs.emergency_shutdown("市场异常波动")
        
        assert rcs.emergency_shutdown_active is True
        assert rcs.shutdown_reason == "市场异常波动"
        assert rcs.risk_level == RiskLevel.CRITICAL
        rcs.event_bus.publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_deactivate_emergency_shutdown(self, risk_control_with_event_bus):
        """测试解除紧急熔断"""
        rcs = risk_control_with_event_bus
        
        await rcs.emergency_shutdown("测试熔断")
        await rcs.deactivate_emergency_shutdown()
        
        assert rcs.emergency_shutdown_active is False
        assert rcs.shutdown_reason == ""
        assert rcs.risk_level == RiskLevel.LOW
    
    @pytest.mark.asyncio
    async def test_deactivate_when_not_active(self, risk_control_system):
        """测试未激活时解除熔断"""
        # 不应该抛出异常
        await risk_control_system.deactivate_emergency_shutdown()
        
        assert risk_control_system.emergency_shutdown_active is False
    
    @pytest.mark.asyncio
    async def test_emergency_shutdown_blocks_orders(self, risk_control_system, sample_buy_order):
        """测试熔断后阻止订单"""
        await risk_control_system.emergency_shutdown("测试")
        
        result = await risk_control_system.check_order(sample_buy_order)
        
        assert result['passed'] is False
        assert "紧急熔断已激活" in result['reason']


# ============== 持仓管理测试 ==============

class TestPositionManagement:
    """测试持仓管理"""
    
    def test_update_position_add(self, risk_control_system):
        """测试添加持仓"""
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.5,
            sector="金融",
            strategy_id="strategy_001"
        )
        
        position = risk_control_system.get_position("600000.SH")
        
        assert position is not None
        assert position.symbol == "600000.SH"
        assert position.quantity == 1000
        assert position.cost_basis == 10.0
        assert position.current_price == 10.5
        assert position.sector == "金融"
        assert position.strategy_id == "strategy_001"
    
    def test_update_position_modify(self, risk_control_system):
        """测试修改持仓"""
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0
        )
        
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=2000,
            cost_basis=10.5,
            current_price=11.0
        )
        
        position = risk_control_system.get_position("600000.SH")
        
        assert position.quantity == 2000
        assert position.cost_basis == 10.5
        assert position.current_price == 11.0
    
    def test_update_position_clear(self, risk_control_system):
        """测试清仓"""
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0
        )
        
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=0,
            cost_basis=10.0,
            current_price=10.0
        )
        
        position = risk_control_system.get_position("600000.SH")
        
        assert position is None
    
    def test_update_price(self, risk_control_system):
        """测试更新价格"""
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0
        )
        
        risk_control_system.update_price("600000.SH", 11.0)
        
        position = risk_control_system.get_position("600000.SH")
        
        assert position.current_price == 11.0
    
    def test_update_price_nonexistent(self, risk_control_system):
        """测试更新不存在的持仓价格"""
        # 不应该抛出异常
        risk_control_system.update_price("999999.SH", 10.0)
    
    def test_get_all_positions(self, risk_control_system):
        """测试获取所有持仓"""
        risk_control_system.update_position(
            symbol="600001.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0
        )
        risk_control_system.update_position(
            symbol="600002.SH",
            quantity=2000,
            cost_basis=20.0,
            current_price=20.0
        )
        
        positions = risk_control_system.get_all_positions()
        
        assert len(positions) == 2
    
    def test_get_position_nonexistent(self, risk_control_system):
        """测试获取不存在的持仓"""
        position = risk_control_system.get_position("999999.SH")
        
        assert position is None


# ============== 资本管理测试 ==============

class TestCapitalManagement:
    """测试资本管理"""
    
    def test_update_total_capital(self, risk_control_system):
        """测试更新总资本"""
        risk_control_system.update_total_capital(2000000.0)
        
        assert risk_control_system.total_capital == 2000000.0
    
    def test_update_total_capital_invalid(self, risk_control_system):
        """测试无效总资本"""
        with pytest.raises(ValueError, match="总资本必须大于0"):
            risk_control_system.update_total_capital(0)
        
        with pytest.raises(ValueError, match="总资本必须大于0"):
            risk_control_system.update_total_capital(-100000)
    
    def test_update_daily_pnl(self, risk_control_system):
        """测试更新日盈亏"""
        risk_control_system.update_daily_pnl(10000)
        risk_control_system.update_daily_pnl(-5000)
        
        assert risk_control_system.daily_pnl == 5000
    
    def test_get_portfolio_summary(self, risk_control_system):
        """测试获取投资组合摘要"""
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=11.0,
            sector="金融"
        )
        risk_control_system.update_daily_pnl(1000)
        
        summary = risk_control_system.get_portfolio_summary()
        
        assert summary['total_capital'] == 1000000.0
        assert summary['total_position_value'] == 11000.0
        assert summary['position_ratio'] == 0.011
        assert summary['cash'] == 989000.0
        assert summary['total_unrealized_pnl'] == 1000.0
        assert summary['daily_pnl'] == 1000
        assert summary['position_count'] == 1
        assert '金融' in summary['sector_distribution']
        assert summary['risk_level'] == 'low'
        assert summary['emergency_shutdown_active'] is False


# ============== 风控回调测试 ==============

class TestRiskCallbacks:
    """测试风控回调"""
    
    @pytest.mark.asyncio
    async def test_register_and_trigger_callback(self, risk_control_system):
        """测试注册和触发回调"""
        callback_results = []
        
        def callback(result: RiskCheckResult):
            callback_results.append(result)
        
        risk_control_system.register_risk_callback(callback)
        
        # 触发日亏损超限
        risk_control_system.update_daily_pnl(-60000)
        
        order = MockOrder(
            symbol="600000.SH",
            quantity=100,
            price=10.0,
            side=OrderSide.BUY
        )
        
        await risk_control_system.check_order(order)
        
        assert len(callback_results) > 0
        assert callback_results[0].check_type == RiskCheckType.DAILY_LOSS
    
    @pytest.mark.asyncio
    async def test_callback_exception_handling(self, risk_control_system):
        """测试回调异常处理"""
        def bad_callback(result: RiskCheckResult):
            raise Exception("回调异常")
        
        risk_control_system.register_risk_callback(bad_callback)
        
        # 触发风控检查
        risk_control_system.update_daily_pnl(-60000)
        
        order = MockOrder(
            symbol="600000.SH",
            quantity=100,
            price=10.0,
            side=OrderSide.BUY
        )
        
        # 不应该抛出异常
        result = await risk_control_system.check_order(order)
        
        assert result['passed'] is False


# ============== 数据类测试 ==============

class TestDataClasses:
    """测试数据类"""
    
    def test_position_properties(self):
        """测试Position属性计算"""
        position = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=11.0
        )
        
        assert position.market_value == 11000.0
        assert position.unrealized_pnl == 1000.0
        assert position.unrealized_pnl_pct == 0.1
    
    def test_position_zero_cost_basis(self):
        """测试零成本价"""
        position = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=0,
            current_price=10.0
        )
        
        assert position.unrealized_pnl_pct == 0.0
    
    def test_risk_check_result_to_dict(self):
        """测试RiskCheckResult转字典"""
        result = RiskCheckResult(
            passed=False,
            check_type=RiskCheckType.POSITION_LIMIT,
            reason="仓位超限",
            risk_level=RiskLevel.HIGH,
            details={'current': 0.25, 'limit': 0.20}
        )
        
        d = result.to_dict()
        
        assert d['passed'] is False
        assert d['check_type'] == 'position_limit'
        assert d['reason'] == "仓位超限"
        assert d['risk_level'] == 'high'
        assert d['details']['current'] == 0.25
    
    def test_position_risk_to_dict(self):
        """测试PositionRisk转字典"""
        risk = PositionRisk(
            symbol="600000.SH",
            quantity=1000,
            market_value=11000.0,
            cost_basis=10.0,
            unrealized_pnl=1000.0,
            unrealized_pnl_pct=0.1,
            position_ratio=0.011,
            sector="金融",
            risk_level=RiskLevel.LOW,
            stop_loss_triggered=False,
            take_profit_triggered=False
        )
        
        d = risk.to_dict()
        
        assert d['symbol'] == "600000.SH"
        assert d['quantity'] == 1000
        assert d['risk_level'] == 'low'
    
    def test_risk_limit_to_dict(self):
        """测试RiskLimit转字典"""
        limit = RiskLimit(
            limit_type='total_position',
            current_value=0.15,
            limit_value=0.20,
            utilization=0.75,
            breached=False
        )
        
        d = limit.to_dict()
        
        assert d['limit_type'] == 'total_position'
        assert d['utilization'] == 0.75
        assert d['breached'] is False


# ============== 重置测试 ==============

class TestReset:
    """测试重置功能"""
    
    def test_reset(self, risk_control_system):
        """测试重置风控系统"""
        # 添加一些状态
        risk_control_system.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0
        )
        risk_control_system.update_daily_pnl(10000)
        risk_control_system.risk_level = RiskLevel.HIGH
        
        # 重置
        risk_control_system.reset()
        
        assert len(risk_control_system.positions) == 0
        assert risk_control_system.daily_pnl == 0.0
        assert risk_control_system.risk_level == RiskLevel.LOW
        assert risk_control_system.emergency_shutdown_active is False


# ============== 辅助方法测试 ==============

class TestHelperMethods:
    """测试辅助方法"""
    
    def test_get_sector(self, risk_control_system):
        """测试获取行业"""
        assert risk_control_system._get_sector("600000.SH") == "上海主板"
        assert risk_control_system._get_sector("000001.SZ") == "深圳主板"
        assert risk_control_system._get_sector("300001.SZ") == "创业板"
        assert risk_control_system._get_sector("688001.SH") == "科创板"
        assert risk_control_system._get_sector("999999.XX") == ""
    
    def test_get_avg_volume(self, risk_control_system):
        """测试获取日均成交量"""
        volume = risk_control_system._get_avg_volume("600000.SH")
        
        assert volume == 10000000.0
    
    def test_calculate_position_risk_level(self, risk_control_system):
        """测试计算持仓风险等级"""
        # 亏损超过止损线
        position_critical = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0  # 亏损10%
        )
        assert risk_control_system._calculate_position_risk_level(position_critical) == RiskLevel.CRITICAL
        
        # 亏损超过止损线一半
        position_high = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.5  # 亏损5%
        )
        assert risk_control_system._calculate_position_risk_level(position_high) == RiskLevel.HIGH
        
        # 亏损超过止损线四分之一
        position_medium = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.75  # 亏损2.5%
        )
        assert risk_control_system._calculate_position_risk_level(position_medium) == RiskLevel.MEDIUM
        
        # 正常
        position_low = Position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.0  # 无亏损
        )
        assert risk_control_system._calculate_position_risk_level(position_low) == RiskLevel.LOW


# ============== 日盈亏重置测试 ==============

class TestDailyPnlReset:
    """测试日盈亏重置"""
    
    def test_daily_pnl_reset_on_new_day(self, risk_control_system):
        """测试新的一天重置日盈亏"""
        risk_control_system.update_daily_pnl(10000)
        
        # 模拟昨天的重置时间
        risk_control_system.daily_pnl_reset_time = datetime.now() - timedelta(days=1)
        
        # 触发重置检查
        risk_control_system._reset_daily_pnl_if_needed()
        
        assert risk_control_system.daily_pnl == 0.0
    
    def test_daily_pnl_no_reset_same_day(self, risk_control_system):
        """测试同一天不重置日盈亏"""
        risk_control_system.update_daily_pnl(10000)
        
        # 触发重置检查
        risk_control_system._reset_daily_pnl_if_needed()
        
        assert risk_control_system.daily_pnl == 10000


# ============== 枚举测试 ==============

class TestEnums:
    """测试枚举类"""
    
    def test_risk_level_values(self):
        """测试风险等级枚举值"""
        assert RiskLevel.LOW.name.lower() == "low"
        assert RiskLevel.MEDIUM.name.lower() == "medium"
        assert RiskLevel.HIGH.name.lower() == "high"
        assert RiskLevel.CRITICAL.name.lower() == "critical"
        # 测试比较功能
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL
    
    def test_risk_check_type_values(self):
        """测试风控检查类型枚举值"""
        assert RiskCheckType.POSITION_LIMIT.value == "position_limit"
        assert RiskCheckType.SECTOR_LIMIT.value == "sector_limit"
        assert RiskCheckType.STOP_LOSS.value == "stop_loss"
        assert RiskCheckType.TAKE_PROFIT.value == "take_profit"
        assert RiskCheckType.LIQUIDITY.value == "liquidity"
        assert RiskCheckType.DAILY_LOSS.value == "daily_loss"


# ============== 异常类测试 ==============

class TestExceptions:
    """测试异常类"""
    
    def test_risk_control_error(self):
        """测试风控系统异常"""
        error = RiskControlError("测试异常")
        assert str(error) == "测试异常"
    
    def test_risk_violation_error(self):
        """测试风控违规异常"""
        error = RiskViolationError("仓位超限")
        assert str(error) == "仓位超限"
        assert isinstance(error, RiskControlError)
    
    def test_emergency_shutdown_error(self):
        """测试紧急熔断异常"""
        error = EmergencyShutdownError("市场异常")
        assert str(error) == "市场异常"
        assert isinstance(error, RiskControlError)
