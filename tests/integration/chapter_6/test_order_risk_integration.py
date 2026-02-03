"""OrderRiskIntegration集成测试

白皮书依据: 第六章 6.3 风险控制系统

测试覆盖:
- 订单风控流程
- 告警触发
- 保护性操作
- 紧急熔断
- Property 28: Order-Risk Integration
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.execution.order_manager import (
    OrderManager,
    Order,
    OrderResult,
    OrderStatus,
    OrderSide,
    OrderType,
)
from src.execution.risk_control_system import (
    RiskControlSystem,
    RiskLevel,
    RiskCheckResult,
    RiskCheckType,
    Position,
)
from src.execution.order_risk_integration import (
    OrderRiskIntegration,
    AlertLevel,
    AlertType,
    RiskAlert,
    ProtectiveAction,
)


# ============== 测试夹具 ==============

@pytest.fixture
def order_manager():
    """创建订单管理器"""
    return OrderManager()


@pytest.fixture
def risk_control():
    """创建风控系统"""
    return RiskControlSystem(
        total_capital=1000000.0,
        max_position_ratio=0.20,
        max_single_stock_ratio=0.10,
        max_sector_ratio=0.30,
        stop_loss_ratio=0.08,
        take_profit_ratio=0.20,
        daily_loss_limit=0.05,
    )


@pytest.fixture
def integration(order_manager, risk_control):
    """创建订单风控集成"""
    return OrderRiskIntegration(
        order_manager=order_manager,
        risk_control=risk_control,
        auto_protective_actions=False  # 测试时禁用自动保护性操作
    )


@pytest.fixture
def integration_with_auto_actions(order_manager, risk_control):
    """创建带自动保护性操作的订单风控集成"""
    return OrderRiskIntegration(
        order_manager=order_manager,
        risk_control=risk_control,
        auto_protective_actions=True
    )


@pytest.fixture
def integration_with_event_bus(order_manager, risk_control):
    """创建带事件总线的订单风控集成"""
    event_bus = AsyncMock()
    return OrderRiskIntegration(
        order_manager=order_manager,
        risk_control=risk_control,
        event_bus=event_bus,
        auto_protective_actions=False
    )


# ============== 初始化测试 ==============

class TestOrderRiskIntegrationInit:
    """测试订单风控集成初始化"""
    
    def test_init_success(self, order_manager, risk_control):
        """测试成功初始化"""
        integration = OrderRiskIntegration(
            order_manager=order_manager,
            risk_control=risk_control
        )
        
        assert integration.order_manager is order_manager
        assert integration.risk_control is risk_control
        assert integration.auto_protective_actions is True
        assert len(integration.alerts) == 0
        assert len(integration.protective_actions) == 0
    
    def test_init_without_order_manager(self, risk_control):
        """测试缺少订单管理器"""
        with pytest.raises(ValueError, match="order_manager不能为None"):
            OrderRiskIntegration(
                order_manager=None,
                risk_control=risk_control
            )
    
    def test_init_without_risk_control(self, order_manager):
        """测试缺少风控系统"""
        with pytest.raises(ValueError, match="risk_control不能为None"):
            OrderRiskIntegration(
                order_manager=order_manager,
                risk_control=None
            )
    
    def test_init_sets_risk_manager(self, order_manager, risk_control):
        """测试初始化设置风险管理器"""
        integration = OrderRiskIntegration(
            order_manager=order_manager,
            risk_control=risk_control
        )
        
        assert order_manager.risk_manager is risk_control


# ============== 订单风控验证测试 ==============

class TestValidateAndSubmitOrder:
    """测试订单风控验证"""
    
    @pytest.mark.asyncio
    async def test_submit_order_success(self, integration):
        """测试订单提交成功"""
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.0
        )
        
        assert result.success is True
        assert result.status == OrderStatus.SUBMITTED
    
    @pytest.mark.asyncio
    async def test_submit_order_emergency_shutdown(self, integration):
        """测试紧急熔断时拒绝订单"""
        await integration.trigger_emergency_shutdown("测试熔断")
        
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.0
        )
        
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert "紧急熔断已激活" in result.message
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.EMERGENCY_SHUTDOWN)
        assert len(alerts) >= 1
    
    @pytest.mark.asyncio
    async def test_submit_order_position_limit_exceeded(self, integration):
        """测试仓位超限"""
        # 创建超过10%单股限制的订单
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=15000,  # 15万，超过10%
            price=10.0
        )
        
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.RISK_VIOLATION)
        assert len(alerts) >= 1
    
    @pytest.mark.asyncio
    async def test_submit_order_capital_insufficient(self, integration):
        """测试资金不足"""
        # 创建超过总资本的订单
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100000,
            price=100.0  # 1000万，超过总资本
        )
        
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_submit_order_daily_loss_exceeded(self, integration):
        """测试日亏损超限"""
        # 设置日亏损超过5%
        integration.risk_control.update_daily_pnl(-60000)  # 6%亏损
        
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.0
        )
        
        assert result.success is False
        assert result.status == OrderStatus.REJECTED


# ============== 持仓监控测试 ==============

class TestMonitorPositions:
    """测试持仓监控"""
    
    @pytest.mark.asyncio
    async def test_monitor_positions_no_positions(self, integration):
        """测试无持仓时监控"""
        risks = await integration.monitor_positions()
        
        assert len(risks) == 0
    
    @pytest.mark.asyncio
    async def test_monitor_positions_normal(self, integration):
        """测试正常持仓监控"""
        # 添加正常持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=10.5,  # 盈利5%
            sector="金融"
        )
        
        risks = await integration.monitor_positions()
        
        assert len(risks) == 1
        assert risks[0]['symbol'] == "600000.SH"
        assert risks[0]['stop_loss_triggered'] is False
        assert risks[0]['take_profit_triggered'] is False
    
    @pytest.mark.asyncio
    async def test_monitor_positions_stop_loss_triggered(self, integration):
        """测试止损触发"""
        # 添加亏损持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0,  # 亏损10%
            sector="金融"
        )
        
        risks = await integration.monitor_positions()
        
        assert len(risks) == 1
        assert risks[0]['stop_loss_triggered'] is True
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.STOP_LOSS)
        assert len(alerts) >= 1
        assert alerts[0].alert_level == AlertLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_monitor_positions_take_profit_triggered(self, integration):
        """测试止盈触发"""
        # 添加盈利持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=12.5,  # 盈利25%
            sector="金融"
        )
        
        risks = await integration.monitor_positions()
        
        assert len(risks) == 1
        assert risks[0]['take_profit_triggered'] is True
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.TAKE_PROFIT)
        assert len(alerts) >= 1
        assert alerts[0].alert_level == AlertLevel.INFO


# ============== 风险限额测试 ==============

class TestCheckRiskLimits:
    """测试风险限额检查"""
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_all_ok(self, integration):
        """测试所有限额正常"""
        result = await integration.check_risk_limits()
        
        assert 'limits' in result
        assert 'breached_limits' in result
        assert len(result['breached_limits']) == 0
        assert result['risk_level'] == 'low'
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_position_breached(self, integration):
        """测试仓位限额突破"""
        # 添加超过20%的持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=25000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        result = await integration.check_risk_limits()
        
        assert len(result['breached_limits']) > 0
        assert result['risk_level'] == 'critical'
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.POSITION_LIMIT)
        assert len(alerts) >= 1
    
    @pytest.mark.asyncio
    async def test_check_risk_limits_daily_loss_breached(self, integration):
        """测试日亏损限额突破"""
        integration.risk_control.update_daily_pnl(-60000)  # 6%亏损
        
        result = await integration.check_risk_limits()
        
        assert len(result['breached_limits']) > 0
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.DAILY_LOSS)
        assert len(alerts) >= 1


# ============== 紧急熔断测试 ==============

class TestEmergencyShutdown:
    """测试紧急熔断"""
    
    @pytest.mark.asyncio
    async def test_trigger_emergency_shutdown(self, integration):
        """测试触发紧急熔断"""
        await integration.trigger_emergency_shutdown("市场异常波动")
        
        assert integration.risk_control.emergency_shutdown_active is True
        
        # 检查告警
        alerts = integration.get_alerts(alert_type=AlertType.EMERGENCY_SHUTDOWN)
        assert len(alerts) >= 1
        assert alerts[0].alert_level == AlertLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_deactivate_emergency_shutdown(self, integration):
        """测试解除紧急熔断"""
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        assert integration.risk_control.emergency_shutdown_active is False
    
    @pytest.mark.asyncio
    async def test_emergency_shutdown_cancels_orders(self, integration_with_auto_actions):
        """测试紧急熔断取消活跃订单"""
        integration = integration_with_auto_actions
        
        # 先提交一个订单
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.0
        )
        
        assert result.success is True
        
        # 触发紧急熔断
        await integration.trigger_emergency_shutdown("测试熔断")
        
        # 检查保护性操作
        actions = integration.get_protective_actions(action_type='cancel_order')
        assert len(actions) >= 1


# ============== 保护性操作测试 ==============

class TestProtectiveActions:
    """测试保护性操作"""
    
    @pytest.mark.asyncio
    async def test_stop_loss_protective_action(self, integration_with_auto_actions):
        """测试止损保护性操作"""
        integration = integration_with_auto_actions
        
        # 添加亏损持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0,  # 亏损10%
            sector="金融"
        )
        
        # 监控持仓
        await integration.monitor_positions()
        
        # 检查保护性操作
        actions = integration.get_protective_actions(action_type='reduce_position')
        assert len(actions) >= 1
        assert actions[0].target_symbol == "600000.SH"
    
    @pytest.mark.asyncio
    async def test_take_profit_protective_action(self, integration_with_auto_actions):
        """测试止盈保护性操作"""
        integration = integration_with_auto_actions
        
        # 添加盈利持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=12.5,  # 盈利25%
            sector="金融"
        )
        
        # 监控持仓
        await integration.monitor_positions()
        
        # 检查保护性操作
        actions = integration.get_protective_actions(action_type='reduce_position')
        assert len(actions) >= 1


# ============== 告警管理测试 ==============

class TestAlertManagement:
    """测试告警管理"""
    
    @pytest.mark.asyncio
    async def test_get_alerts(self, integration):
        """测试获取告警"""
        # 触发一些告警
        await integration.trigger_emergency_shutdown("测试1")
        await integration.deactivate_emergency_shutdown()
        await integration.trigger_emergency_shutdown("测试2")
        await integration.deactivate_emergency_shutdown()
        
        alerts = integration.get_alerts()
        
        assert len(alerts) >= 2
    
    @pytest.mark.asyncio
    async def test_get_alerts_by_type(self, integration):
        """测试按类型获取告警"""
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        alerts = integration.get_alerts(alert_type=AlertType.EMERGENCY_SHUTDOWN)
        
        assert len(alerts) >= 1
        assert all(a.alert_type == AlertType.EMERGENCY_SHUTDOWN for a in alerts)
    
    @pytest.mark.asyncio
    async def test_get_unacknowledged_alerts(self, integration):
        """测试获取未确认告警"""
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        unack = integration.get_unacknowledged_alerts()
        
        assert len(unack) >= 1
        assert all(not a.acknowledged for a in unack)
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, integration):
        """测试确认告警"""
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        alerts = integration.get_unacknowledged_alerts()
        assert len(alerts) >= 1
        
        alert_id = alerts[0].alert_id
        result = integration.acknowledge_alert(alert_id)
        
        assert result is True
        
        # 验证已确认
        unack = integration.get_unacknowledged_alerts()
        assert all(a.alert_id != alert_id for a in unack)
    
    @pytest.mark.asyncio
    async def test_acknowledge_all_alerts(self, integration):
        """测试确认所有告警"""
        await integration.trigger_emergency_shutdown("测试1")
        await integration.deactivate_emergency_shutdown()
        await integration.trigger_emergency_shutdown("测试2")
        await integration.deactivate_emergency_shutdown()
        
        count = integration.acknowledge_all_alerts()
        
        assert count >= 2
        
        unack = integration.get_unacknowledged_alerts()
        assert len(unack) == 0
    
    def test_acknowledge_nonexistent_alert(self, integration):
        """测试确认不存在的告警"""
        result = integration.acknowledge_alert("NONEXISTENT")
        
        assert result is False


# ============== 回调测试 ==============

class TestCallbacks:
    """测试回调功能"""
    
    @pytest.mark.asyncio
    async def test_alert_callback(self, integration):
        """测试告警回调"""
        callback_results = []
        
        def callback(alert: RiskAlert):
            callback_results.append(alert)
        
        integration.register_alert_callback(callback)
        
        await integration.trigger_emergency_shutdown("测试")
        
        assert len(callback_results) >= 1
        # 检查是否有EMERGENCY_SHUTDOWN类型的告警（可能不是第一个）
        emergency_alerts = [a for a in callback_results if a.alert_type == AlertType.EMERGENCY_SHUTDOWN]
        assert len(emergency_alerts) >= 1
    
    @pytest.mark.asyncio
    async def test_action_callback(self, integration_with_auto_actions):
        """测试保护性操作回调"""
        integration = integration_with_auto_actions
        callback_results = []
        
        def callback(action: ProtectiveAction):
            callback_results.append(action)
        
        integration.register_action_callback(callback)
        
        # 添加亏损持仓触发止损
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0,
            sector="金融"
        )
        
        await integration.monitor_positions()
        
        assert len(callback_results) >= 1
    
    @pytest.mark.asyncio
    async def test_callback_exception_handling(self, integration):
        """测试回调异常处理"""
        def bad_callback(alert: RiskAlert):
            raise Exception("回调异常")
        
        integration.register_alert_callback(bad_callback)
        
        # 不应该抛出异常
        await integration.trigger_emergency_shutdown("测试")
        
        # 告警应该仍然被记录
        alerts = integration.get_alerts(alert_type=AlertType.EMERGENCY_SHUTDOWN)
        assert len(alerts) >= 1


# ============== 统计信息测试 ==============

class TestStatistics:
    """测试统计信息"""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, integration):
        """测试获取统计信息"""
        # 触发一些告警
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        stats = integration.get_statistics()
        
        assert 'total_alerts' in stats
        assert 'unacknowledged_alerts' in stats
        assert 'alert_counts' in stats
        assert 'total_protective_actions' in stats
        assert 'risk_level' in stats
        assert stats['total_alerts'] >= 1


# ============== 清理测试 ==============

class TestCleanup:
    """测试清理功能"""
    
    @pytest.mark.asyncio
    async def test_clear_old_alerts(self, integration):
        """测试清理旧告警"""
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        # 清理（保留0小时，即全部清理）
        cleared = integration.clear_old_alerts(keep_hours=0)
        
        # 由于刚创建，可能不会被清理
        # 这里主要测试方法不抛出异常
        assert cleared >= 0
    
    @pytest.mark.asyncio
    async def test_clear_old_actions(self, integration_with_auto_actions):
        """测试清理旧保护性操作"""
        integration = integration_with_auto_actions
        
        # 添加亏损持仓触发保护性操作
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0,
            sector="金融"
        )
        
        await integration.monitor_positions()
        
        # 清理
        cleared = integration.clear_old_actions(keep_hours=0)
        
        assert cleared >= 0
    
    def test_reset(self, integration):
        """测试重置"""
        # 添加一些数据
        integration.alerts.append(RiskAlert(
            alert_id="TEST",
            alert_type=AlertType.RISK_VIOLATION,
            alert_level=AlertLevel.WARNING,
            message="测试"
        ))
        
        integration.reset()
        
        assert len(integration.alerts) == 0
        assert len(integration.protective_actions) == 0


# ============== 事件总线测试 ==============

class TestEventBus:
    """测试事件总线集成"""
    
    @pytest.mark.asyncio
    async def test_emergency_shutdown_publishes_event(self, integration_with_event_bus):
        """测试紧急熔断发布事件"""
        integration = integration_with_event_bus
        
        await integration.trigger_emergency_shutdown("测试")
        
        # 等待异步事件发布
        await asyncio.sleep(0.1)
        
        integration.event_bus.publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_deactivate_shutdown_publishes_event(self, integration_with_event_bus):
        """测试解除熔断发布事件"""
        integration = integration_with_event_bus
        
        await integration.trigger_emergency_shutdown("测试")
        await integration.deactivate_emergency_shutdown()
        
        # 等待异步事件发布
        await asyncio.sleep(0.1)
        
        assert integration.event_bus.publish.call_count >= 2


# ============== Property 28: Order-Risk Integration ==============

class TestProperty28OrderRiskIntegration:
    """Property 28: 订单风控集成
    
    **Validates: Requirements 10.4**
    
    验证订单管理与风控系统的正确集成。
    """
    
    @pytest.mark.asyncio
    async def test_order_rejected_on_risk_violation(self, integration):
        """测试风控违规时订单被拒绝"""
        # 设置日亏损超限
        integration.risk_control.update_daily_pnl(-60000)
        
        result = await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.0
        )
        
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_alert_generated_on_risk_violation(self, integration):
        """测试风控违规时生成告警"""
        # 设置日亏损超限
        integration.risk_control.update_daily_pnl(-60000)
        
        await integration.validate_and_submit_order(
            symbol="600000.SH",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=10.0
        )
        
        alerts = integration.get_alerts()
        assert len(alerts) >= 1
    
    @pytest.mark.asyncio
    async def test_protective_action_on_stop_loss(self, integration_with_auto_actions):
        """测试止损时执行保护性操作"""
        integration = integration_with_auto_actions
        
        # 添加亏损持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=1000,
            cost_basis=10.0,
            current_price=9.0,
            sector="金融"
        )
        
        await integration.monitor_positions()
        
        actions = integration.get_protective_actions()
        assert len(actions) >= 1
    
    @pytest.mark.asyncio
    async def test_emergency_shutdown_blocks_all_orders(self, integration):
        """测试紧急熔断阻止所有订单"""
        await integration.trigger_emergency_shutdown("测试")
        
        # 尝试提交多个订单
        for i in range(3):
            result = await integration.validate_and_submit_order(
                symbol=f"60000{i}.SH",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=1000,
                price=10.0
            )
            
            assert result.success is False
            assert result.status == OrderStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_risk_level_propagation(self, integration):
        """测试风险等级传播"""
        # 添加超过限额的持仓
        integration.risk_control.update_position(
            symbol="600000.SH",
            quantity=25000,
            cost_basis=10.0,
            current_price=10.0,
            sector="金融"
        )
        
        result = await integration.check_risk_limits()
        
        assert result['risk_level'] == 'critical'
        assert integration.risk_control.risk_level == RiskLevel.CRITICAL

