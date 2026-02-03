"""认证通知服务

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 通知管理

本模块实现认证流程关键节点的通知功能，支持多渠道通知（邮件、短信、系统消息）。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class NotificationChannel(Enum):
    """通知渠道"""

    EMAIL = "email"
    SMS = "sms"
    SYSTEM = "system"
    WECHAT = "wechat"


class NotificationPriority(Enum):
    """通知优先级"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationEventType(Enum):
    """通知事件类型"""

    CERTIFICATION_STARTED = "certification_started"
    ARENA_COMPLETED = "arena_completed"
    SIMULATION_COMPLETED = "simulation_completed"
    CERTIFICATION_GRANTED = "certification_granted"
    CERTIFICATION_FAILED = "certification_failed"
    CERTIFICATION_REVOKED = "certification_revoked"
    CERTIFICATION_DOWNGRADED = "certification_downgraded"


@dataclass
class NotificationMessage:
    """通知消息

    Attributes:
        event_type: 事件类型
        title: 通知标题
        content: 通知内容
        priority: 优先级
        channels: 通知渠道列表
        metadata: 附加元数据
        timestamp: 发送时间
    """

    event_type: NotificationEventType
    title: str
    content: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class NotificationRecord:
    """通知记录

    Attributes:
        message_id: 消息ID
        message: 通知消息
        sent_channels: 已发送的渠道
        failed_channels: 发送失败的渠道
        sent_at: 发送时间
        status: 发送状态
    """

    message_id: str
    message: NotificationMessage
    sent_channels: List[NotificationChannel]
    failed_channels: List[NotificationChannel]
    sent_at: datetime
    status: str


class CertificationNotificationService:
    """认证通知服务

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 通知管理

    实现认证流程关键节点的通知功能：
    - 认证流程启动通知
    - Arena验证完成通知
    - 模拟盘验证完成通知
    - 认证颁发通知
    - 认证失败通知
    - 认证撤销/降级通知
    - 多渠道通知支持（邮件、短信、系统消息）
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        default_channels: Optional[List[NotificationChannel]] = None,
        enable_email: bool = True,
        enable_sms: bool = False,
        enable_system: bool = True,
        enable_wechat: bool = False,
    ):
        """初始化认证通知服务

        Args:
            default_channels: 默认通知渠道列表
            enable_email: 是否启用邮件通知
            enable_sms: 是否启用短信通知
            enable_system: 是否启用系统消息通知
            enable_wechat: 是否启用企业微信通知
        """
        self.default_channels = default_channels or [NotificationChannel.SYSTEM]
        self.enable_email = enable_email
        self.enable_sms = enable_sms
        self.enable_system = enable_system
        self.enable_wechat = enable_wechat

        # 通知历史记录
        self.notification_history: List[NotificationRecord] = []

        # 消息ID计数器
        self._message_id_counter = 0

        logger.info(
            f"初始化CertificationNotificationService: "
            f"default_channels={[c.value for c in self.default_channels]}, "
            f"email={enable_email}, sms={enable_sms}, "
            f"system={enable_system}, wechat={enable_wechat}"
        )

    def notify_certification_started(
        self, strategy_id: str, strategy_name: str, channels: Optional[List[NotificationChannel]] = None
    ) -> NotificationRecord:
        """发送认证流程启动通知

        白皮书依据: 第四章 4.3.2 认证流程通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            channels: 通知渠道列表，None表示使用默认渠道

        Returns:
            NotificationRecord: 通知记录
        """
        title = f"认证流程已启动: {strategy_name}"
        content = f"""
策略 {strategy_name} (ID: {strategy_id}) 的Z2H认证流程已启动。

认证流程包括以下阶段：
1. 因子Arena三轨测试
2. 因子组合策略生成
3. 斯巴达Arena策略考核
4. 模拟盘1个月验证
5. Z2H基因胶囊认证
6. 实盘交易部署

预计完成时间：30-45天

启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.CERTIFICATION_STARTED,
            title=title,
            content=content,
            priority=NotificationPriority.NORMAL,
            channels=channels or self.default_channels,
            metadata={"strategy_id": strategy_id, "strategy_name": strategy_name},
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def notify_arena_completed(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        arena_passed: bool,
        arena_score: float,
        layer_results: Dict[str, Dict[str, Any]],
        channels: Optional[List[NotificationChannel]] = None,
    ) -> NotificationRecord:
        """发送Arena验证完成通知

        白皮书依据: 第四章 4.3.2 Arena验证通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            arena_passed: Arena是否通过
            arena_score: Arena综合评分
            layer_results: 各层验证结果
            channels: 通知渠道列表

        Returns:
            NotificationRecord: 通知记录
        """
        status_text = "通过" if arena_passed else "未通过"
        priority = NotificationPriority.NORMAL if arena_passed else NotificationPriority.HIGH

        # 构建层级结果摘要
        layer_summary = []
        for layer_name, result in layer_results.items():
            passed = result.get("passed", False)
            score = result.get("score", 0.0)
            status = "✅ 通过" if passed else "❌ 未通过"
            layer_summary.append(f"  {layer_name}: {status} (评分: {score:.2f})")

        title = f"Arena验证{status_text}: {strategy_name}"
        content = f"""
策略 {strategy_name} (ID: {strategy_id}) 的斯巴达Arena验证已完成。

验证结果: {status_text}
综合评分: {arena_score:.2f}

各层验证结果:
{chr(10).join(layer_summary)}

完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.ARENA_COMPLETED,
            title=title,
            content=content,
            priority=priority,
            channels=channels or self.default_channels,
            metadata={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "arena_passed": arena_passed,
                "arena_score": arena_score,
                "layer_results": layer_results,
            },
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def notify_simulation_completed(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        simulation_passed: bool,
        duration_days: int,
        best_tier: str,
        overall_metrics: Dict[str, float],
        channels: Optional[List[NotificationChannel]] = None,
    ) -> NotificationRecord:
        """发送模拟盘验证完成通知

        白皮书依据: 第四章 4.3.2 模拟盘验证通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            simulation_passed: 模拟盘是否通过
            duration_days: 验证天数
            best_tier: 最佳档位
            overall_metrics: 综合指标
            channels: 通知渠道列表

        Returns:
            NotificationRecord: 通知记录
        """
        status_text = "通过" if simulation_passed else "未通过"
        priority = NotificationPriority.NORMAL if simulation_passed else NotificationPriority.HIGH

        # 构建指标摘要
        metrics_summary = []
        for metric_name, value in overall_metrics.items():
            if isinstance(value, float):
                metrics_summary.append(f"  {metric_name}: {value:.4f}")
            else:
                metrics_summary.append(f"  {metric_name}: {value}")

        title = f"模拟盘验证{status_text}: {strategy_name}"
        content = f"""
策略 {strategy_name} (ID: {strategy_id}) 的模拟盘验证已完成。

验证结果: {status_text}
验证天数: {duration_days}天
最佳档位: {best_tier}

综合指标:
{chr(10).join(metrics_summary)}

完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.SIMULATION_COMPLETED,
            title=title,
            content=content,
            priority=priority,
            channels=channels or self.default_channels,
            metadata={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "simulation_passed": simulation_passed,
                "duration_days": duration_days,
                "best_tier": best_tier,
                "overall_metrics": overall_metrics,
            },
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def notify_certification_granted(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        certification_level: str,
        max_allocation_ratio: float,
        arena_score: float,
        simulation_metrics: Dict[str, float],
        channels: Optional[List[NotificationChannel]] = None,
    ) -> NotificationRecord:
        """发送认证颁发通知

        白皮书依据: 第四章 4.3.2 认证颁发通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            certification_level: 认证等级
            max_allocation_ratio: 最大资金配置比例
            arena_score: Arena评分
            simulation_metrics: 模拟盘指标
            channels: 通知渠道列表

        Returns:
            NotificationRecord: 通知记录
        """
        level_emoji = {"platinum": "🏆", "gold": "🥇", "silver": "🥈"}.get(certification_level.lower(), "✅")

        title = f"{level_emoji} Z2H认证颁发: {strategy_name}"
        content = f"""
恭喜！策略 {strategy_name} (ID: {strategy_id}) 已获得Z2H认证。

认证等级: {certification_level.upper()}
最大资金配置比例: {max_allocation_ratio:.1%}
Arena综合评分: {arena_score:.2f}

模拟盘关键指标:
  夏普比率: {simulation_metrics.get('sharpe_ratio', 0):.2f}
  最大回撤: {simulation_metrics.get('max_drawdown', 0):.2%}
  胜率: {simulation_metrics.get('win_rate', 0):.2%}

该策略已注册到策略库，可用于实盘交易。

颁发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.CERTIFICATION_GRANTED,
            title=title,
            content=content,
            priority=NotificationPriority.HIGH,
            channels=channels or self.default_channels,
            metadata={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "certification_level": certification_level,
                "max_allocation_ratio": max_allocation_ratio,
                "arena_score": arena_score,
                "simulation_metrics": simulation_metrics,
            },
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def notify_certification_failed(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        failed_stage: str,
        failure_reason: str,
        failure_details: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
    ) -> NotificationRecord:
        """发送认证失败通知

        白皮书依据: 第四章 4.3.2 认证失败通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            failed_stage: 失败阶段
            failure_reason: 失败原因
            failure_details: 失败详情
            channels: 通知渠道列表

        Returns:
            NotificationRecord: 通知记录
        """
        title = f"❌ 认证失败: {strategy_name}"
        content = f"""
策略 {strategy_name} (ID: {strategy_id}) 的Z2H认证未通过。

失败阶段: {failed_stage}
失败原因: {failure_reason}

详细信息:
{self._format_failure_details(failure_details)}

建议: 请根据失败分析报告优化策略，然后重新提交认证。

失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.CERTIFICATION_FAILED,
            title=title,
            content=content,
            priority=NotificationPriority.HIGH,
            channels=channels or self.default_channels,
            metadata={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "failed_stage": failed_stage,
                "failure_reason": failure_reason,
                "failure_details": failure_details,
            },
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def notify_certification_revoked(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        revocation_reason: str,
        previous_level: str,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> NotificationRecord:
        """发送认证撤销通知

        白皮书依据: 第四章 4.3.2 认证撤销通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            revocation_reason: 撤销原因
            previous_level: 之前的认证等级
            channels: 通知渠道列表

        Returns:
            NotificationRecord: 通知记录
        """
        title = f"⚠️ 认证撤销: {strategy_name}"
        content = f"""
策略 {strategy_name} (ID: {strategy_id}) 的Z2H认证已被撤销。

之前等级: {previous_level.upper()}
撤销原因: {revocation_reason}

该策略已从策略库中移除，不再用于实盘交易。

撤销时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.CERTIFICATION_REVOKED,
            title=title,
            content=content,
            priority=NotificationPriority.URGENT,
            channels=channels or self.default_channels,
            metadata={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "revocation_reason": revocation_reason,
                "previous_level": previous_level,
            },
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def notify_certification_downgraded(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        strategy_name: str,
        previous_level: str,
        new_level: str,
        downgrade_reason: str,
        new_allocation_ratio: float,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> NotificationRecord:
        """发送认证降级通知

        白皮书依据: 第四章 4.3.2 认证降级通知

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            previous_level: 之前的认证等级
            new_level: 新的认证等级
            downgrade_reason: 降级原因
            new_allocation_ratio: 新的资金配置比例
            channels: 通知渠道列表

        Returns:
            NotificationRecord: 通知记录
        """
        title = f"⚠️ 认证降级: {strategy_name}"
        content = f"""
策略 {strategy_name} (ID: {strategy_id}) 的Z2H认证等级已降级。

之前等级: {previous_level.upper()}
新等级: {new_level.upper()}
降级原因: {downgrade_reason}

新的资金配置比例: {new_allocation_ratio:.1%}

该策略的资金配置已相应调整。

降级时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        message = NotificationMessage(
            event_type=NotificationEventType.CERTIFICATION_DOWNGRADED,
            title=title,
            content=content,
            priority=NotificationPriority.URGENT,
            channels=channels or self.default_channels,
            metadata={
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "previous_level": previous_level,
                "new_level": new_level,
                "downgrade_reason": downgrade_reason,
                "new_allocation_ratio": new_allocation_ratio,
            },
            timestamp=datetime.now(),
        )

        return self._send_notification(message)

    def get_notification_history(
        self,
        strategy_id: Optional[str] = None,
        event_type: Optional[NotificationEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[NotificationRecord]:
        """查询通知历史

        Args:
            strategy_id: 策略ID，None表示所有策略
            event_type: 事件类型，None表示所有类型
            start_date: 开始日期，None表示不限
            end_date: 结束日期，None表示不限

        Returns:
            List[NotificationRecord]: 通知记录列表
        """
        results = []

        for record in self.notification_history:
            # 策略ID过滤
            if strategy_id and record.message.metadata.get("strategy_id") != strategy_id:
                continue

            # 事件类型过滤
            if event_type and record.message.event_type != event_type:
                continue

            # 日期范围过滤
            if start_date and record.sent_at < start_date:
                continue
            if end_date and record.sent_at > end_date:
                continue

            results.append(record)

        return results

    def _send_notification(self, message: NotificationMessage) -> NotificationRecord:
        """发送通知（内部方法）

        Args:
            message: 通知消息

        Returns:
            NotificationRecord: 通知记录
        """
        self._message_id_counter += 1
        message_id = f"NOTIF-{self._message_id_counter:06d}"

        sent_channels = []
        failed_channels = []

        for channel in message.channels:
            try:
                if channel == NotificationChannel.EMAIL and self.enable_email:
                    self._send_email(message)
                    sent_channels.append(channel)
                elif channel == NotificationChannel.SMS and self.enable_sms:
                    self._send_sms(message)
                    sent_channels.append(channel)
                elif channel == NotificationChannel.SYSTEM and self.enable_system:
                    self._send_system_message(message)
                    sent_channels.append(channel)
                elif channel == NotificationChannel.WECHAT and self.enable_wechat:
                    self._send_wechat(message)
                    sent_channels.append(channel)
                else:
                    logger.warning(f"渠道未启用或不支持: {channel.value}")
                    failed_channels.append(channel)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"发送通知失败: channel={channel.value}, error={e}")
                failed_channels.append(channel)

        # 创建通知记录
        record = NotificationRecord(
            message_id=message_id,
            message=message,
            sent_channels=sent_channels,
            failed_channels=failed_channels,
            sent_at=datetime.now(),
            status="success" if sent_channels else "failed",
        )

        # 保存到历史记录
        self.notification_history.append(record)

        logger.info(
            f"通知已发送: message_id={message_id}, "
            f"event={message.event_type.value}, "
            f"sent_channels={[c.value for c in sent_channels]}, "
            f"failed_channels={[c.value for c in failed_channels]}"
        )

        return record

    def _send_email(self, message: NotificationMessage) -> None:
        """发送邮件通知（内部方法）

        Args:
            message: 通知消息
        """
        # 实际实现中应该调用邮件服务API
        logger.info(f"[EMAIL] {message.title}")
        logger.debug(f"[EMAIL] Content: {message.content}")

    def _send_sms(self, message: NotificationMessage) -> None:
        """发送短信通知（内部方法）

        Args:
            message: 通知消息
        """
        # 实际实现中应该调用短信服务API
        logger.info(f"[SMS] {message.title}")
        logger.debug(f"[SMS] Content: {message.content}")

    def _send_system_message(self, message: NotificationMessage) -> None:
        """发送系统消息通知（内部方法）

        Args:
            message: 通知消息
        """
        # 实际实现中应该写入系统消息队列或数据库
        logger.info(f"[SYSTEM] {message.title}")
        logger.debug(f"[SYSTEM] Content: {message.content}")

    def _send_wechat(self, message: NotificationMessage) -> None:
        """发送企业微信通知（内部方法）

        Args:
            message: 通知消息
        """
        # 实际实现中应该调用企业微信API
        logger.info(f"[WECHAT] {message.title}")
        logger.debug(f"[WECHAT] Content: {message.content}")

    def _format_failure_details(self, details: Dict[str, Any]) -> str:
        """格式化失败详情（内部方法）

        Args:
            details: 失败详情字典

        Returns:
            str: 格式化后的字符串
        """
        lines = []
        for key, value in details.items():
            if isinstance(value, dict):
                lines.append(f"  {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"    {sub_key}: {sub_value}")
            else:
                lines.append(f"  {key}: {value}")
        return "\n".join(lines) if lines else "  无详细信息"
