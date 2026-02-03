"""Margin Watchdog (风险门闸) - 衍生品保证金监控

白皮书依据: 第六章 5.4 风险门闸

核心功能：
- 衍生品总保证金 < 30%
- 风险度 > 85% 强制平仓
- 实时监控保证金风险
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class RiskLevel(Enum):
    """风险等级"""

    SAFE = "safe"  # 安全 (< 50%)
    WARNING = "warning"  # 警告 (50% - 70%)
    DANGER = "danger"  # 危险 (70% - 85%)
    CRITICAL = "critical"  # 临界 (> 85%)


@dataclass
class MarginWatchdogConfig:
    """Margin Watchdog配置

    白皮书依据: 第六章 5.4 风险门闸
    """

    # 保证金比例阈值
    max_margin_ratio: float = 0.30  # 最大保证金比例30%

    # 风险度阈值
    warning_risk_ratio: float = 0.50  # 警告阈值50%
    danger_risk_ratio: float = 0.70  # 危险阈值70%
    critical_risk_ratio: float = 0.85  # 临界阈值85%（强制平仓）

    # 监控间隔（秒）
    monitor_interval: int = 5

    # 是否启用自动平仓
    auto_liquidation_enabled: bool = True

    # 平仓优先级（按风险从高到低）
    liquidation_priority: List[str] = field(
        default_factory=lambda: ["option", "futures", "margin_stock"]  # 期权优先平仓  # 期货次之  # 融资融券最后
    )


@dataclass
class MarginPosition:
    """保证金持仓"""

    symbol: str
    position_type: str  # 'option', 'futures', 'margin_stock'
    quantity: float
    margin_required: float  # 占用保证金
    market_value: float  # 市值
    unrealized_pnl: float  # 未实现盈亏
    risk_contribution: float  # 风险贡献度


@dataclass
class MarginWatchdogState:
    """Margin Watchdog状态"""

    current_margin_ratio: float = 0.0  # 当前保证金比例
    current_risk_ratio: float = 0.0  # 当前风险度
    risk_level: RiskLevel = RiskLevel.SAFE
    total_margin_used: float = 0.0  # 已用保证金
    total_margin_available: float = 0.0  # 可用保证金
    positions: List[MarginPosition] = field(default_factory=list)
    last_check_time: Optional[str] = None
    alert_history: List[Dict[str, Any]] = field(default_factory=list)
    liquidation_history: List[Dict[str, Any]] = field(default_factory=list)


class MarginWatchdog:
    """Margin Watchdog (风险门闸) - 衍生品保证金监控系统

    白皮书依据: 第六章 5.4 风险门闸

    核心功能：
    1. 实时监控衍生品保证金比例
    2. 多级风险预警
    3. 风险度超过85%自动强制平仓
    4. 记录风险事件和平仓历史

    Attributes:
        config: 配置
        state: 状态
        execution_engine: 执行引擎
        alert_callback: 告警回调函数
    """

    def __init__(
        self,
        config: Optional[MarginWatchdogConfig] = None,
        execution_engine: Optional[Any] = None,
        alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """初始化Margin Watchdog

        Args:
            config: 配置
            execution_engine: 执行引擎
            alert_callback: 告警回调函数
        """
        self.config = config or MarginWatchdogConfig()
        self.state = MarginWatchdogState()
        self.execution_engine = execution_engine
        self.alert_callback = alert_callback
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        logger.info(
            f"MarginWatchdog初始化 - "
            f"最大保证金比例: {self.config.max_margin_ratio*100:.0f}%, "
            f"强制平仓阈值: {self.config.critical_risk_ratio*100:.0f}%"
        )

    async def start_monitoring(self) -> None:
        """启动监控"""
        if self._monitoring:
            logger.warning("MarginWatchdog已在运行中")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("MarginWatchdog监控已启动")

    async def stop_monitoring(self) -> None:
        """停止监控"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("MarginWatchdog监控已停止")

    async def _monitor_loop(self) -> None:
        """监控循环"""
        while self._monitoring:
            try:
                await self.check_margin_risk()
                await asyncio.sleep(self.config.monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"MarginWatchdog监控异常: {e}")
                await asyncio.sleep(self.config.monitor_interval)

    async def check_margin_risk(self, account_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """检查保证金风险

        白皮书依据: 第六章 5.4 风险门闸

        Args:
            account_data: 账户数据（可选，如果不提供则从执行引擎获取）

        Returns:
            风险检查结果
        """
        # 获取账户数据
        if account_data is None:
            account_data = await self._get_account_data()

        # 计算保证金比例
        total_assets = account_data.get("total_assets", 0)
        margin_used = account_data.get("margin_used", 0)
        margin_available = account_data.get("margin_available", 0)

        if total_assets <= 0:
            logger.warning("总资产为0，无法计算保证金比例")
            return {"success": False, "message": "总资产为0"}

        margin_ratio = margin_used / total_assets

        # 计算风险度
        total_margin = margin_used + margin_available
        risk_ratio = margin_used / total_margin if total_margin > 0 else 0

        # 更新状态
        self.state.current_margin_ratio = margin_ratio
        self.state.current_risk_ratio = risk_ratio
        self.state.total_margin_used = margin_used
        self.state.total_margin_available = margin_available
        self.state.last_check_time = datetime.now().isoformat()

        # 更新持仓信息
        await self._update_positions(account_data)

        # 判断风险等级
        old_risk_level = self.state.risk_level
        self.state.risk_level = self._calculate_risk_level(risk_ratio)

        # 记录风险等级变化
        if self.state.risk_level != old_risk_level:
            await self._handle_risk_level_change(old_risk_level, self.state.risk_level)

        # 检查是否需要强制平仓
        if risk_ratio >= self.config.critical_risk_ratio:
            logger.critical(
                f"风险度{risk_ratio*100:.1f}%超过临界阈值{self.config.critical_risk_ratio*100:.0f}%，" f"触发强制平仓！"
            )
            if self.config.auto_liquidation_enabled:
                await self._execute_forced_liquidation()

        # 检查保证金比例
        if margin_ratio > self.config.max_margin_ratio:
            logger.warning(f"保证金比例{margin_ratio*100:.1f}%超过最大阈值{self.config.max_margin_ratio*100:.0f}%")
            await self._send_alert(
                {
                    "type": "margin_ratio_exceeded",
                    "margin_ratio": margin_ratio,
                    "threshold": self.config.max_margin_ratio,
                    "message": f"保证金比例{margin_ratio*100:.1f}%超过阈值",
                }
            )

        return {
            "success": True,
            "margin_ratio": margin_ratio,
            "risk_ratio": risk_ratio,
            "risk_level": self.state.risk_level.value,
            "margin_used": margin_used,
            "margin_available": margin_available,
            "positions_count": len(self.state.positions),
        }

    def _calculate_risk_level(self, risk_ratio: float) -> RiskLevel:
        """计算风险等级

        Args:
            risk_ratio: 风险度

        Returns:
            风险等级
        """
        if risk_ratio >= self.config.critical_risk_ratio:  # pylint: disable=no-else-return
            return RiskLevel.CRITICAL
        elif risk_ratio >= self.config.danger_risk_ratio:
            return RiskLevel.DANGER
        elif risk_ratio >= self.config.warning_risk_ratio:
            return RiskLevel.WARNING
        else:
            return RiskLevel.SAFE

    async def _handle_risk_level_change(self, old_level: RiskLevel, new_level: RiskLevel) -> None:
        """处理风险等级变化

        Args:
            old_level: 旧风险等级
            new_level: 新风险等级
        """
        logger.info(f"风险等级变化: {old_level.value} -> {new_level.value}")

        # 发送告警
        await self._send_alert(
            {
                "type": "risk_level_change",
                "old_level": old_level.value,
                "new_level": new_level.value,
                "risk_ratio": self.state.current_risk_ratio,
                "message": f"风险等级从{old_level.value}变为{new_level.value}",
            }
        )

    async def _update_positions(self, account_data: Dict[str, Any]) -> None:
        """更新持仓信息

        Args:
            account_data: 账户数据
        """
        positions_data = account_data.get("derivative_positions", [])

        self.state.positions = []
        for pos in positions_data:
            margin_position = MarginPosition(
                symbol=pos.get("symbol", ""),
                position_type=pos.get("type", "unknown"),
                quantity=pos.get("quantity", 0),
                margin_required=pos.get("margin_required", 0),
                market_value=pos.get("market_value", 0),
                unrealized_pnl=pos.get("unrealized_pnl", 0),
                risk_contribution=pos.get("risk_contribution", 0),
            )
            self.state.positions.append(margin_position)

    async def _execute_forced_liquidation(self) -> Dict[str, Any]:
        """执行强制平仓

        白皮书依据: 第六章 5.4 风险门闸 - 风险度 > 85% 强制平仓

        Returns:
            平仓结果
        """
        logger.critical("开始执行强制平仓！")

        liquidation_results: List[Dict[str, Any]] = []

        # 按优先级排序持仓
        sorted_positions = self._sort_positions_by_priority()

        for position in sorted_positions:
            # 检查是否已降低到安全水平
            if self.state.current_risk_ratio < self.config.danger_risk_ratio:
                logger.info("风险度已降至安全水平，停止平仓")
                break

            try:
                result = await self._liquidate_position(position)
                liquidation_results.append(result)

                # 重新检查风险度
                await self.check_margin_risk()

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"平仓{position.symbol}失败: {e}")
                liquidation_results.append({"symbol": position.symbol, "success": False, "error": str(e)})

        # 记录平仓历史
        liquidation_record = {
            "timestamp": datetime.now().isoformat(),
            "trigger_risk_ratio": self.state.current_risk_ratio,
            "positions_liquidated": len([r for r in liquidation_results if r.get("success")]),
            "results": liquidation_results,
        }
        self.state.liquidation_history.append(liquidation_record)

        # 发送告警
        await self._send_alert(
            {
                "type": "forced_liquidation",
                "positions_count": len(liquidation_results),
                "success_count": len([r for r in liquidation_results if r.get("success")]),
                "message": f"强制平仓完成，共平仓{len(liquidation_results)}个持仓",
            }
        )

        return {"success": True, "liquidation_count": len(liquidation_results), "results": liquidation_results}

    def _sort_positions_by_priority(self) -> List[MarginPosition]:
        """按优先级排序持仓（风险高的优先平仓）

        Returns:
            排序后的持仓列表
        """
        priority_map = {pos_type: idx for idx, pos_type in enumerate(self.config.liquidation_priority)}

        def get_priority(position: MarginPosition) -> tuple:
            type_priority = priority_map.get(position.position_type, 999)
            # 风险贡献度高的优先
            return (type_priority, -position.risk_contribution)

        return sorted(self.state.positions, key=get_priority)

    async def _liquidate_position(self, position: MarginPosition) -> Dict[str, Any]:
        """平仓单个持仓

        Args:
            position: 持仓信息

        Returns:
            平仓结果
        """
        logger.warning(f"平仓: {position.symbol}, 数量: {position.quantity}")

        if self.execution_engine:  # pylint: disable=no-else-return
            # 执行平仓
            result = await self.execution_engine.place_order(
                symbol=position.symbol,
                action="sell" if position.quantity > 0 else "buy",
                quantity=abs(position.quantity),
                price=None,  # 市价
                order_type="market",
            )

            return {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "success": result.get("success", False),
                "order_id": result.get("order_id"),
                "message": result.get("message", ""),
            }
        else:
            # 模拟平仓
            logger.info(f"[模拟] 平仓 {position.symbol}: {position.quantity}")
            return {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "success": True,
                "order_id": f'SIM_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                "message": "模拟平仓成功",
            }

    async def _get_account_data(self) -> Dict[str, Any]:
        """获取账户数据

        Returns:
            账户数据
        """
        if self.execution_engine:  # pylint: disable=no-else-return
            return await self.execution_engine.get_account_info()
        else:
            # 返回模拟数据
            return {
                "total_assets": 1000000,
                "margin_used": 100000,
                "margin_available": 200000,
                "derivative_positions": [],
            }

    async def _send_alert(self, alert_data: Dict[str, Any]) -> None:
        """发送告警

        Args:
            alert_data: 告警数据
        """
        alert_data["timestamp"] = datetime.now().isoformat()

        # 记录告警历史
        self.state.alert_history.append(alert_data)

        # 调用回调函数
        if self.alert_callback:
            try:
                self.alert_callback(alert_data)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"告警回调失败: {e}")

        # 记录日志
        alert_type = alert_data.get("type", "unknown")
        message = alert_data.get("message", "")

        if alert_type == "forced_liquidation":
            logger.critical(f"[告警] {message}")
        elif alert_type == "risk_level_change":
            new_level = alert_data.get("new_level", "")
            if new_level in ["danger", "critical"]:
                logger.error(f"[告警] {message}")
            else:
                logger.warning(f"[告警] {message}")
        else:
            logger.warning(f"[告警] {message}")

    def get_state(self) -> Dict[str, Any]:
        """获取Watchdog状态

        Returns:
            状态字典
        """
        return {
            "margin_ratio": self.state.current_margin_ratio,
            "risk_ratio": self.state.current_risk_ratio,
            "risk_level": self.state.risk_level.value,
            "margin_used": self.state.total_margin_used,
            "margin_available": self.state.total_margin_available,
            "positions_count": len(self.state.positions),
            "last_check_time": self.state.last_check_time,
            "alert_count": len(self.state.alert_history),
            "liquidation_count": len(self.state.liquidation_history),
            "monitoring": self._monitoring,
            "config": {
                "max_margin_ratio": self.config.max_margin_ratio,
                "critical_risk_ratio": self.config.critical_risk_ratio,
                "auto_liquidation_enabled": self.config.auto_liquidation_enabled,
            },
        }

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史

        Args:
            limit: 返回记录数量限制

        Returns:
            告警历史列表
        """
        return self.state.alert_history[-limit:]

    def get_liquidation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取平仓历史

        Args:
            limit: 返回记录数量限制

        Returns:
            平仓历史列表
        """
        return self.state.liquidation_history[-limit:]

    def reset_state(self) -> None:
        """重置状态（仅用于测试）"""
        self.state = MarginWatchdogState()
        logger.warning("MarginWatchdog状态已重置")
