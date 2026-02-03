"""独立审计进程

白皮书依据: 第七章 6.2.1 独立审计进程

Auditor负责维护影子账本，验证交易执行，对账发现差异。
作为独立进程运行，确保交易执行的正确性和资金安全。

特性：
- 影子账本（Shadow Ledger）维护
- 交易验证（卖出前检查持仓）
- 对账（比对执行记录与影子账本）
- Redis同步
- 告警发送
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.audit.data_models import AuditEventType, ReconciliationDiscrepancy, ShadowPosition


class AuditError(Exception):
    """审计错误

    白皮书依据: 第七章 6.2.1 独立审计进程
    """


class InsufficientPositionError(AuditError):
    """持仓不足错误"""


class ReconciliationError(AuditError):
    """对账错误"""


class Auditor:
    """独立审计进程

    白皮书依据: 第七章 6.2.1 独立审计进程

    维护影子账本，验证交易执行，对账发现差异。

    Attributes:
        shadow_ledger: 影子账本（symbol -> ShadowPosition）
        redis_client: Redis客户端
        broker_api: 券商API接口
        audit_logger: 审计日志记录器
    """

    REDIS_KEY_PREFIX = "mia:audit:shadow_ledger"

    def __init__(
        self, redis_client: Optional[Any] = None, broker_api: Optional[Any] = None, audit_logger: Optional[Any] = None
    ):
        """初始化Auditor

        白皮书依据: 第七章 6.2.1 独立审计进程

        Args:
            redis_client: Redis客户端，用于持久化影子账本
            broker_api: 券商API接口，用于同步真实持仓
            audit_logger: 审计日志记录器
        """
        self.shadow_ledger: Dict[str, ShadowPosition] = {}
        self.redis_client = redis_client
        self.broker_api = broker_api
        self.audit_logger = audit_logger

        # 从Redis加载影子账本
        self._load_from_redis()

        logger.info(
            f"Auditor初始化完成: "
            f"redis_enabled={redis_client is not None}, "
            f"broker_enabled={broker_api is not None}, "
            f"positions={len(self.shadow_ledger)}"
        )

    def _load_from_redis(self) -> None:
        """从Redis加载影子账本"""
        if self.redis_client is None:
            return

        try:
            data = self.redis_client.hgetall(self.REDIS_KEY_PREFIX)
            if data:
                for symbol, position_json in data.items():
                    if isinstance(symbol, bytes):
                        symbol = symbol.decode("utf-8")
                    if isinstance(position_json, bytes):
                        position_json = position_json.decode("utf-8")

                    position_data = json.loads(position_json)
                    self.shadow_ledger[symbol] = ShadowPosition(
                        symbol=position_data["symbol"],
                        quantity=position_data["quantity"],
                        avg_cost=position_data["avg_cost"],
                        last_sync=position_data["last_sync"],
                    )
                logger.info(f"从Redis加载影子账本: {len(self.shadow_ledger)}个持仓")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"从Redis加载影子账本失败: {e}")

    def _save_to_redis(self) -> None:
        """保存影子账本到Redis"""
        if self.redis_client is None:
            return

        try:
            # 清空旧数据
            self.redis_client.delete(self.REDIS_KEY_PREFIX)

            # 保存新数据
            for symbol, position in self.shadow_ledger.items():
                position_data = {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "avg_cost": position.avg_cost,
                    "last_sync": position.last_sync,
                }
                self.redis_client.hset(self.REDIS_KEY_PREFIX, symbol, json.dumps(position_data, ensure_ascii=False))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"保存影子账本到Redis失败: {e}")

    async def sync_from_broker(self) -> None:
        """从券商同步真实持仓到影子账本

        白皮书依据: 第七章 6.2.1 独立审计进程

        Raises:
            AuditError: 当券商API不可用时
        """
        if self.broker_api is None:
            raise AuditError("券商API未配置，无法同步持仓")

        try:
            # 获取券商持仓
            broker_positions = await self.broker_api.get_positions()

            # 更新影子账本
            sync_time = datetime.now().isoformat()
            new_ledger: Dict[str, ShadowPosition] = {}

            for pos in broker_positions:
                symbol = pos["symbol"]
                new_ledger[symbol] = ShadowPosition(
                    symbol=symbol, quantity=pos["quantity"], avg_cost=pos.get("avg_cost", 0.0), last_sync=sync_time
                )

            self.shadow_ledger = new_ledger

            # 保存到Redis
            self._save_to_redis()

            # 记录审计日志
            if self.audit_logger:
                self.audit_logger.log_event(
                    {
                        "event_type": AuditEventType.POSITION_CHANGE.value,
                        "action": "sync_from_broker",
                        "positions_count": len(new_ledger),
                        "sync_time": sync_time,
                    }
                )

            logger.info(f"从券商同步持仓完成: {len(new_ledger)}个持仓")

        except Exception as e:
            logger.error(f"从券商同步持仓失败: {e}")
            raise AuditError(f"同步持仓失败: {e}") from e

    def verify_trade(self, trade_request: Dict[str, Any]) -> bool:
        """验证交易请求

        白皮书依据: 第七章 6.2.1 独立审计进程

        对于卖出交易，验证影子账本中是否有足够的持仓。
        对于买入交易，直接通过（资金检查由其他组件负责）。

        Args:
            trade_request: 交易请求，必须包含symbol, action, quantity

        Returns:
            验证是否通过

        Raises:
            ValueError: 当必需字段缺失时
            InsufficientPositionError: 当卖出持仓不足时
        """
        # 验证必需字段
        required_fields = ["symbol", "action", "quantity"]
        missing_fields = [f for f in required_fields if f not in trade_request]
        if missing_fields:
            raise ValueError(f"交易请求缺少必需字段: {missing_fields}")

        symbol = trade_request["symbol"]
        action = trade_request["action"]
        quantity = trade_request["quantity"]

        # 验证action
        if action not in ("buy", "sell"):
            raise ValueError(f"无效的交易动作: {action}. 必须是'buy'或'sell'")

        # 验证quantity
        if quantity <= 0:
            raise ValueError(f"交易数量必须大于0，当前值: {quantity}")

        # 买入交易直接通过
        if action == "buy":
            logger.debug(f"买入交易验证通过: {symbol}, quantity={quantity}")
            return True

        # 卖出交易检查持仓
        position = self.shadow_ledger.get(symbol)

        if position is None:
            raise InsufficientPositionError(f"卖出验证失败: {symbol}不在影子账本中")

        if position.quantity < quantity:
            raise InsufficientPositionError(
                f"卖出验证失败: {symbol}持仓不足. " f"请求卖出{quantity}，实际持仓{position.quantity}"
            )

        logger.debug(f"卖出交易验证通过: {symbol}, " f"quantity={quantity}, available={position.quantity}")
        return True

    def update_position(self, symbol: str, action: str, quantity: float, price: float) -> None:
        """更新影子账本持仓

        白皮书依据: 第七章 6.2.1 独立审计进程

        Args:
            symbol: 股票代码
            action: 交易动作（buy/sell）
            quantity: 交易数量
            price: 交易价格

        Raises:
            ValueError: 当参数无效时
        """
        if action not in ("buy", "sell"):
            raise ValueError(f"无效的交易动作: {action}")

        if quantity <= 0:
            raise ValueError(f"交易数量必须大于0: {quantity}")

        if price <= 0:
            raise ValueError(f"交易价格必须大于0: {price}")

        current_time = datetime.now().isoformat()

        if action == "buy":
            # 买入：增加持仓
            if symbol in self.shadow_ledger:
                position = self.shadow_ledger[symbol]
                # 计算新的平均成本
                total_cost = position.quantity * position.avg_cost + quantity * price
                new_quantity = position.quantity + quantity
                new_avg_cost = total_cost / new_quantity

                position.quantity = new_quantity
                position.avg_cost = new_avg_cost
                position.last_sync = current_time
            else:
                # 新建持仓
                self.shadow_ledger[symbol] = ShadowPosition(
                    symbol=symbol, quantity=quantity, avg_cost=price, last_sync=current_time
                )
        else:
            # 卖出：减少持仓
            if symbol not in self.shadow_ledger:
                raise ValueError(f"无法卖出: {symbol}不在影子账本中")

            position = self.shadow_ledger[symbol]
            if position.quantity < quantity:
                raise ValueError(f"无法卖出: {symbol}持仓不足. " f"请求{quantity}，实际{position.quantity}")

            position.quantity -= quantity
            position.last_sync = current_time

            # 如果持仓为0，删除记录
            if position.quantity == 0:
                del self.shadow_ledger[symbol]

        # 保存到Redis
        self._save_to_redis()

        logger.debug(f"更新影子账本: {symbol}, action={action}, " f"quantity={quantity}, price={price}")

    def reconcile(self, execution_ledger: Optional[Dict[str, float]] = None) -> List[ReconciliationDiscrepancy]:
        """对账：比对执行进程记录与影子账本

        白皮书依据: 第七章 6.2.1 独立审计进程

        Args:
            execution_ledger: 执行进程的持仓记录（symbol -> quantity）
                            如果为None，则从broker_api获取

        Returns:
            差异列表

        Raises:
            AuditError: 当无法获取执行记录时
        """
        if execution_ledger is None:
            if self.broker_api is None:
                raise AuditError("无法对账: 未提供执行记录且券商API未配置")
            # 这里应该异步获取，但为了简化，假设已经有数据
            raise AuditError("无法对账: 请提供执行记录或先调用sync_from_broker")

        discrepancies: List[ReconciliationDiscrepancy] = []

        # 获取所有涉及的股票代码
        all_symbols = set(self.shadow_ledger.keys()) | set(execution_ledger.keys())

        for symbol in all_symbols:
            shadow_qty = self.shadow_ledger.get(symbol)
            shadow_quantity = shadow_qty.quantity if shadow_qty else 0.0
            execution_quantity = execution_ledger.get(symbol, 0.0)

            # 检查差异（使用小数点精度容差）
            difference = shadow_quantity - execution_quantity
            if abs(difference) > 0.001:  # 容差0.001
                discrepancies.append(
                    ReconciliationDiscrepancy(
                        symbol=symbol,
                        shadow_quantity=shadow_quantity,
                        execution_quantity=execution_quantity,
                        difference=difference,
                    )
                )

        # 记录审计日志
        if self.audit_logger and discrepancies:
            self.audit_logger.log_event(
                {
                    "event_type": AuditEventType.ALERT_TRIGGERED.value,
                    "alert_type": "reconciliation_discrepancy",
                    "discrepancies_count": len(discrepancies),
                    "discrepancies": [
                        {
                            "symbol": d.symbol,
                            "shadow": d.shadow_quantity,
                            "execution": d.execution_quantity,
                            "diff": d.difference,
                        }
                        for d in discrepancies
                    ],
                }
            )

        if discrepancies:
            logger.warning(f"对账发现{len(discrepancies)}个差异")
            for d in discrepancies:
                logger.warning(
                    f"  {d.symbol}: 影子账本={d.shadow_quantity}, "
                    f"执行记录={d.execution_quantity}, 差异={d.difference}"
                )
        else:
            logger.info("对账完成: 无差异")

        return discrepancies

    def get_position(self, symbol: str) -> Optional[ShadowPosition]:
        """获取指定股票的持仓

        Args:
            symbol: 股票代码

        Returns:
            持仓信息，如果不存在返回None
        """
        return self.shadow_ledger.get(symbol)

    def get_all_positions(self) -> Dict[str, ShadowPosition]:
        """获取所有持仓

        Returns:
            所有持仓的字典
        """
        return self.shadow_ledger.copy()

    def get_total_value(self, prices: Dict[str, float]) -> float:
        """计算持仓总市值

        Args:
            prices: 股票代码到当前价格的字典

        Returns:
            总市值
        """
        total = 0.0
        for symbol, position in self.shadow_ledger.items():
            price = prices.get(symbol, position.avg_cost)
            total += position.quantity * price
        return total

    def clear_ledger(self) -> None:
        """清空影子账本（仅用于测试）"""
        self.shadow_ledger.clear()
        self._save_to_redis()
        logger.warning("影子账本已清空")
