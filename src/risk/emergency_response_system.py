"""应急响应系统

白皮书依据: 第十九章 19.3 应急响应流程

应急响应分级:
- P0 (紧急): 系统崩溃、资金安全威胁 - 响应时间: 立即
- P1 (重要): 功能降级、性能下降 - 响应时间: 5分钟内
- P2 (一般): 非关键功能异常 - 响应时间: 30分钟内
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional

from loguru import logger


class AlertLevel(Enum):
    """告警级别

    白皮书依据: 第十九章 19.3.1 应急响应分级
    """

    WARNING = "warning"  # P2 - 一般
    DANGER = "danger"  # P1 - 重要
    CRITICAL = "critical"  # P0 - 紧急


@dataclass
class EmergencyProcedure:
    """应急程序

    Attributes:
        procedure_id: 程序ID
        alert_level: 告警级别
        description: 程序描述
        actions: 执行的动作列表
        executed_at: 执行时间
        success: 是否成功执行
    """

    procedure_id: str
    alert_level: AlertLevel
    description: str
    actions: List[str]
    executed_at: datetime
    success: bool


class EmergencyResponseSystem:
    """应急响应系统

    白皮书依据: 第十九章 19.3 应急响应流程

    功能:
    1. 触发告警（WARNING, DANGER, CRITICAL）
    2. 执行应急程序
    3. 记录应急响应历史
    4. 验证响应时间SLA

    Attributes:
        response_time_sla: 响应时间SLA（秒）
        alert_handlers: 告警处理器
        emergency_history: 应急响应历史
    """

    def __init__(self):
        """初始化应急响应系统

        白皮书依据: 第十九章 19.3.1 应急响应分级
        """
        # 响应时间SLA（秒）
        self.response_time_sla = {
            AlertLevel.WARNING: 30 * 60,  # 30分钟
            AlertLevel.DANGER: 5 * 60,  # 5分钟
            AlertLevel.CRITICAL: 0,  # 立即
        }

        # 告警处理器
        self.alert_handlers: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.WARNING: [],
            AlertLevel.DANGER: [],
            AlertLevel.CRITICAL: [],
        }

        # 应急响应历史
        self.emergency_history: List[EmergencyProcedure] = []

        # 程序ID计数器（确保唯一性）
        self._procedure_counter: int = 0

        logger.info("应急响应系统初始化完成")

    def register_alert_handler(self, alert_level: AlertLevel, handler: Callable) -> None:
        """注册告警处理器

        Args:
            alert_level: 告警级别
            handler: 处理器函数

        Raises:
            ValueError: 当alert_level不是AlertLevel枚举时
            ValueError: 当handler不可调用时
        """
        if not isinstance(alert_level, AlertLevel):
            raise ValueError(f"告警级别必须是AlertLevel枚举: {type(alert_level)}")

        if not callable(handler):
            raise ValueError(f"处理器必须是可调用对象: {type(handler)}")

        self.alert_handlers[alert_level].append(handler)
        logger.info(f"注册告警处理器: {alert_level.value} -> {handler.__name__}")

    def trigger_alert(
        self, alert_level: AlertLevel, description: str, context: Optional[Dict] = None
    ) -> EmergencyProcedure:
        """触发告警

        白皮书依据: 第十九章 19.3.1 应急响应分级

        Args:
            alert_level: 告警级别
            description: 告警描述
            context: 上下文信息（可选）

        Returns:
            应急程序执行结果

        Raises:
            ValueError: 当alert_level不是AlertLevel枚举时
            ValueError: 当description为空时
        """
        if not isinstance(alert_level, AlertLevel):
            raise ValueError(f"告警级别必须是AlertLevel枚举: {type(alert_level)}")

        if not description or not description.strip():
            raise ValueError("告警描述不能为空")

        context = context or {}

        # 记录告警时间
        alert_time = datetime.now()

        # 生成程序ID（包含微秒和计数器确保唯一性）
        self._procedure_counter += 1
        procedure_id = f"{alert_level.value}_{alert_time.strftime('%Y%m%d%H%M%S%f')}_{self._procedure_counter}"

        # 记录告警
        logger.warning(f"[Emergency] 触发{alert_level.value}级告警: {description}")

        # 执行应急程序
        actions = []
        success = True

        try:
            # 调用注册的处理器
            handlers = self.alert_handlers.get(alert_level, [])
            for handler in handlers:
                try:
                    handler_name = handler.__name__
                    handler(description, context)
                    actions.append(f"执行处理器: {handler_name}")
                    logger.info(f"[Emergency] 处理器执行成功: {handler_name}")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    actions.append(f"处理器失败: {handler.__name__} - {str(e)}")
                    logger.error(f"[Emergency] 处理器执行失败: {handler.__name__} - {e}")
                    success = False

            # 执行默认应急程序
            default_actions = self._execute_default_procedure(alert_level, description, context)
            actions.extend(default_actions)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[Emergency] 应急程序执行失败: {e}")
            actions.append(f"应急程序失败: {str(e)}")
            success = False

        # 创建应急程序记录
        procedure = EmergencyProcedure(
            procedure_id=procedure_id,
            alert_level=alert_level,
            description=description,
            actions=actions,
            executed_at=alert_time,
            success=success,
        )

        self.emergency_history.append(procedure)

        # 验证响应时间
        response_time = (datetime.now() - alert_time).total_seconds()
        sla = self.response_time_sla[alert_level]

        if response_time > sla:
            logger.warning(f"[Emergency] 响应时间超SLA: {response_time:.2f}s > {sla}s")
        else:
            logger.info(f"[Emergency] 响应时间达标: {response_time:.2f}s <= {sla}s")

        return procedure

    def execute_emergency_procedure(self, procedure_type: str, context: Optional[Dict] = None) -> bool:
        """执行应急程序

        白皮书依据: 第十九章 19.3.2 应急响应SOP

        Args:
            procedure_type: 程序类型 ("stop_trading", "liquidate", "failover", "recovery")
            context: 上下文信息（可选）

        Returns:
            True表示执行成功，False表示执行失败

        Raises:
            ValueError: 当procedure_type不支持时
        """
        valid_types = ["stop_trading", "liquidate", "failover", "recovery"]
        if procedure_type not in valid_types:
            raise ValueError(f"不支持的程序类型: {procedure_type}，有效类型: {valid_types}")

        context = context or {}

        logger.info(f"[Emergency] 执行应急程序: {procedure_type}")

        try:
            if procedure_type == "stop_trading":  # pylint: disable=no-else-return
                return self._stop_trading(context)
            elif procedure_type == "liquidate":
                return self._liquidate_positions(context)
            elif procedure_type == "failover":
                return self._execute_failover(context)
            elif procedure_type == "recovery":
                return self._execute_recovery(context)
            else:
                return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[Emergency] 应急程序执行失败: {procedure_type} - {e}")
            return False

    def get_response_time_sla(self, alert_level: AlertLevel) -> int:
        """获取响应时间SLA

        白皮书依据: 第十九章 19.3.1 应急响应分级

        Args:
            alert_level: 告警级别

        Returns:
            响应时间SLA（秒）

        Raises:
            ValueError: 当alert_level不是AlertLevel枚举时
        """
        if not isinstance(alert_level, AlertLevel):
            raise ValueError(f"告警级别必须是AlertLevel枚举: {type(alert_level)}")

        return self.response_time_sla[alert_level]

    def get_emergency_history(
        self, alert_level: Optional[AlertLevel] = None, hours: int = 24
    ) -> List[EmergencyProcedure]:
        """获取应急响应历史

        Args:
            alert_level: 告警级别过滤（可选）
            hours: 最近多少小时，默认24小时

        Returns:
            应急程序列表

        Raises:
            ValueError: 当hours <= 0时
        """
        if hours <= 0:
            raise ValueError(f"小时数必须 > 0: {hours}")

        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 过滤时间范围
        history = [proc for proc in self.emergency_history if proc.executed_at >= cutoff_time]

        # 过滤告警级别
        if alert_level is not None:
            if not isinstance(alert_level, AlertLevel):
                raise ValueError(f"告警级别必须是AlertLevel枚举: {type(alert_level)}")
            history = [proc for proc in history if proc.alert_level == alert_level]

        return history

    def get_statistics(self) -> Dict[str, any]:
        """获取应急响应统计

        Returns:
            统计信息字典
        """
        # 统计各级别告警数量
        level_counts = {AlertLevel.WARNING: 0, AlertLevel.DANGER: 0, AlertLevel.CRITICAL: 0}

        # 统计成功率
        total_count = len(self.emergency_history)
        success_count = sum(1 for proc in self.emergency_history if proc.success)

        # 统计最近24小时
        recent_history = self.get_emergency_history(hours=24)

        for proc in recent_history:
            level_counts[proc.alert_level] += 1

        return {
            "total_procedures": total_count,
            "success_count": success_count,
            "success_rate": success_count / total_count if total_count > 0 else 1.0,
            "recent_24h": len(recent_history),
            "level_counts": {level.value: count for level, count in level_counts.items()},
            "last_procedure": (
                {
                    "procedure_id": self.emergency_history[-1].procedure_id,
                    "alert_level": self.emergency_history[-1].alert_level.value,
                    "description": self.emergency_history[-1].description,
                    "executed_at": self.emergency_history[-1].executed_at.isoformat(),
                    "success": self.emergency_history[-1].success,
                }
                if self.emergency_history
                else None
            ),
        }

    def clear_old_history(self, days: int = 30) -> None:
        """清理旧的应急响应历史

        Args:
            days: 保留最近多少天的历史，默认30天

        Raises:
            ValueError: 当days <= 0时
        """
        if days <= 0:
            raise ValueError(f"保留天数必须 > 0: {days}")

        cutoff_time = datetime.now() - timedelta(days=days)

        initial_count = len(self.emergency_history)

        self.emergency_history = [proc for proc in self.emergency_history if proc.executed_at >= cutoff_time]

        removed_count = initial_count - len(self.emergency_history)

        if removed_count > 0:
            logger.info(f"清理了 {removed_count} 条旧应急响应记录（保留最近{days}天）")

    def _execute_default_procedure(
        self, alert_level: AlertLevel, description: str, context: Dict  # pylint: disable=unused-argument
    ) -> List[str]:  # pylint: disable=unused-argument
        """执行默认应急程序

        Args:
            alert_level: 告警级别
            description: 告警描述
            context: 上下文信息

        Returns:
            执行的动作列表
        """
        actions = []

        if alert_level == AlertLevel.CRITICAL:
            # P0: 立即响应
            actions.append("记录P0级告警")
            actions.append("发送紧急通知")
            actions.append("触发末日开关（如需要）")
            logger.critical(f"[Emergency] P0级告警: {description}")

        elif alert_level == AlertLevel.DANGER:
            # P1: 5分钟内响应
            actions.append("记录P1级告警")
            actions.append("发送重要通知")
            actions.append("切换备用方案")
            logger.error(f"[Emergency] P1级告警: {description}")

        else:  # WARNING
            # P2: 30分钟内响应
            actions.append("记录P2级告警")
            actions.append("后台修复")
            logger.warning(f"[Emergency] P2级告警: {description}")

        return actions

    def _stop_trading(self, context: Dict) -> bool:  # pylint: disable=unused-argument
        """停止交易

        白皮书依据: 第十九章 19.3.2 应急响应SOP

        Args:
            context: 上下文信息

        Returns:
            True表示成功
        """
        logger.warning("[Emergency] 执行停止交易程序")
        # 实际实现中会调用交易系统API
        return True

    def _liquidate_positions(self, context: Dict) -> bool:  # pylint: disable=unused-argument
        """清仓

        白皮书依据: 第十九章 19.3.2 应急响应SOP

        Args:
            context: 上下文信息

        Returns:
            True表示成功
        """
        logger.warning("[Emergency] 执行清仓程序")
        # 实际实现中会调用交易系统API
        return True

    def _execute_failover(self, context: Dict) -> bool:  # pylint: disable=unused-argument
        """执行故障转移

        白皮书依据: 第十九章 19.3.2 应急响应SOP

        Args:
            context: 上下文信息

        Returns:
            True表示成功
        """
        logger.info("[Emergency] 执行故障转移程序")
        # 实际实现中会切换到备用系统
        return True

    def _execute_recovery(self, context: Dict) -> bool:  # pylint: disable=unused-argument
        """执行系统恢复

        白皮书依据: 第十九章 19.4 灾难恢复计划

        Args:
            context: 上下文信息

        Returns:
            True表示成功
        """
        logger.info("[Emergency] 执行系统恢复程序")
        # 实际实现中会从备份恢复
        return True
