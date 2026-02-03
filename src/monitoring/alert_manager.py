"""Alert Manager for Prometheus alerts and routing

白皮书依据: 第十三章 13.4 告警规则配置
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
from loguru import logger


class AlertLevel(Enum):
    """Alert severity levels

    白皮书依据: 第十三章 13.4 告警规则配置
    """

    EMERGENCY = "emergency"  # Phone + WeChat
    CRITICAL = "critical"  # WeChat
    WARNING = "warning"  # WeChat (work hours only)
    INFO = "info"  # Log only


@dataclass
class Alert:
    """Alert data structure

    Attributes:
        name: Alert name
        level: Alert severity level
        message: Alert message
        timestamp: Alert timestamp
        labels: Additional labels
        annotations: Additional annotations
    """

    name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None


class AlertManager:
    """Manages Prometheus alerts and routing

    白皮书依据: 第十三章 13.4 告警规则配置

    Routes alerts based on severity:
    - Emergency: Phone + WeChat
    - Critical: WeChat
    - Warning: WeChat (work hours only)
    - Info: Log only

    Attributes:
        wechat_webhook_url: WeChat webhook URL for alerts
        phone_webhook_url: Phone webhook URL for emergency alerts
        work_hours_start: Work hours start (hour)
        work_hours_end: Work hours end (hour)
        alert_rules: Configured Prometheus alert rules
    """

    def __init__(
        self,
        wechat_webhook_url: Optional[str] = None,
        phone_webhook_url: Optional[str] = None,
        work_hours_start: int = 9,
        work_hours_end: int = 18,
    ):
        """Initialize AlertManager

        Args:
            wechat_webhook_url: WeChat webhook URL
            phone_webhook_url: Phone webhook URL for emergencies
            work_hours_start: Work hours start (hour, 0-23)
            work_hours_end: Work hours end (hour, 0-23)

        Raises:
            ValueError: When work hours are invalid
        """
        if not 0 <= work_hours_start <= 23:
            raise ValueError(f"work_hours_start must be 0-23, got {work_hours_start}")

        if not 0 <= work_hours_end <= 23:
            raise ValueError(f"work_hours_end must be 0-23, got {work_hours_end}")

        if work_hours_start >= work_hours_end:
            raise ValueError(f"work_hours_start ({work_hours_start}) must be < " f"work_hours_end ({work_hours_end})")

        self.wechat_webhook_url: Optional[str] = wechat_webhook_url
        self.phone_webhook_url: Optional[str] = phone_webhook_url
        self.work_hours_start: int = work_hours_start
        self.work_hours_end: int = work_hours_end
        self.alert_rules: List[Dict[str, str]] = []

        logger.info(
            f"AlertManager initialized - "
            f"work_hours={work_hours_start}-{work_hours_end}, "
            f"wechat_configured={wechat_webhook_url is not None}, "
            f"phone_configured={phone_webhook_url is not None}"
        )

    def configure_alerts(self) -> None:
        """Configure Prometheus alert rules

        白皮书依据: 第十三章 13.4 告警规则配置

        Configures alert rules for:
        - Redis down (>3 failures)
        - Soldier degraded (>10min)
        - GPU overheating (>85°C)
        - High memory (>90%)
        - Low disk (<10%)
        - Daily loss (>5%)
        - Critical loss (>10%)
        """
        self.alert_rules = [
            {
                "alert": "RedisDown",
                "expr": "redis_connection_failures >= 3",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "Redis连接失败", "description": "Redis连接失败次数 >= 3"},
            },
            {
                "alert": "SoldierDegraded",
                "expr": "soldier_mode_status == 1",
                "for": "10m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "Soldier降级运行", "description": "Soldier已切换到Cloud模式超过10分钟"},
            },
            {
                "alert": "GPUOverheating",
                "expr": "gpu_temperature_celsius > 85",
                "for": "5m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "GPU温度过高", "description": "GPU温度 > 85°C"},
            },
            {
                "alert": "HighMemoryUsage",
                "expr": "system_memory_percent > 90",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "内存使用率过高", "description": "内存使用率 > 90%"},
            },
            {
                "alert": "LowDiskSpace",
                "expr": "system_disk_percent > 90",
                "for": "10m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "磁盘空间不足", "description": "磁盘使用率 > 90%"},
            },
            {
                "alert": "DailyLossExceeded",
                "expr": "portfolio_daily_pnl_percent < -5",
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {"summary": "日内亏损超过5%", "description": "日内亏损 > 5%，需要暂停新开仓"},
            },
            {
                "alert": "CriticalLoss",
                "expr": "portfolio_daily_pnl_percent < -10",
                "for": "1m",
                "labels": {"severity": "emergency"},
                "annotations": {"summary": "日内亏损超过10%", "description": "日内亏损 > 10%，触发紧急锁定"},
            },
        ]

        logger.info(f"Configured {len(self.alert_rules)} alert rules")

    def _is_work_hours(self) -> bool:
        """Check if current time is within work hours

        Returns:
            True if within work hours, False otherwise
        """
        current_hour = datetime.now().hour
        return self.work_hours_start <= current_hour < self.work_hours_end

    async def route_alert(self, alert: Alert) -> None:
        """Route alert based on severity

        白皮书依据: 第十三章 13.4 告警规则配置

        Routing logic:
        - Emergency: Phone + WeChat
        - Critical: WeChat
        - Warning: WeChat (work hours only)
        - Info: Log only

        Args:
            alert: Alert to route

        Raises:
            ValueError: When alert level is invalid
        """
        if not isinstance(alert.level, AlertLevel):
            raise ValueError(f"Invalid alert level: {alert.level}")

        logger.info(f"Routing alert: name={alert.name}, level={alert.level.value}, " f"message={alert.message}")

        # Always log the alert
        log_message = (
            f"[{alert.level.value.upper()}] {alert.name}: {alert.message} " f"(timestamp={alert.timestamp.isoformat()})"
        )

        if alert.level == AlertLevel.EMERGENCY:
            logger.critical(log_message)
            # Send to both phone and WeChat
            await self._send_phone_alert(alert)
            await self.send_wechat_alert(alert)

        elif alert.level == AlertLevel.CRITICAL:
            logger.error(log_message)
            # Send to WeChat
            await self.send_wechat_alert(alert)

        elif alert.level == AlertLevel.WARNING:
            logger.warning(log_message)
            # Send to WeChat only during work hours
            if self._is_work_hours():
                await self.send_wechat_alert(alert)
            else:
                logger.info(f"Alert {alert.name} not sent (outside work hours)")

        elif alert.level == AlertLevel.INFO:
            logger.info(log_message)
            # Log only, no external notification

        else:
            raise ValueError(f"Unknown alert level: {alert.level}")

    async def send_wechat_alert(self, alert: Alert) -> None:
        """Send alert to WeChat webhook

        白皮书依据: 第十三章 13.4 告警规则配置

        Args:
            alert: Alert to send

        Raises:
            RuntimeError: When WeChat webhook is not configured
            aiohttp.ClientError: When HTTP request fails
        """
        if not self.wechat_webhook_url:
            logger.warning(f"WeChat webhook not configured, skipping alert: {alert.name}")
            return

        # Format WeChat message
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": (
                    f"## 🚨 {alert.name}\n\n"
                    f"**级别**: {alert.level.value.upper()}\n\n"
                    f"**消息**: {alert.message}\n\n"
                    f"**时间**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
            },
        }

        # Add labels if present
        if alert.labels:
            labels_str = "\n".join(f"- {k}: {v}" for k, v in alert.labels.items())
            message["markdown"]["content"] += f"**标签**:\n{labels_str}\n\n"

        # Add annotations if present
        if alert.annotations:
            annotations_str = "\n".join(f"- {k}: {v}" for k, v in alert.annotations.items())
            message["markdown"]["content"] += f"**详情**:\n{annotations_str}\n\n"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.wechat_webhook_url, json=message, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info(f"WeChat alert sent successfully: {alert.name}")
                    else:
                        error_text = await response.text()
                        logger.error(f"WeChat alert failed: status={response.status}, " f"error={error_text}")
                        raise RuntimeError(f"WeChat webhook returned status {response.status}")

        except asyncio.TimeoutError as e:
            logger.error(f"WeChat alert timeout: {alert.name}")
            raise RuntimeError("WeChat webhook timeout") from e

        except aiohttp.ClientError as e:
            logger.error(f"WeChat alert HTTP error: {e}")
            raise

    async def _send_phone_alert(self, alert: Alert) -> None:
        """Send alert to phone webhook (internal method)

        Args:
            alert: Alert to send
        """
        if not self.phone_webhook_url:
            logger.warning(f"Phone webhook not configured, skipping alert: {alert.name}")
            return

        # Format phone message (SMS-style, keep it short)
        message = {
            "msgtype": "text",
            "text": {"content": (f"🚨 {alert.name}\n" f"{alert.message}\n" f"{alert.timestamp.strftime('%H:%M:%S')}")},
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.phone_webhook_url, json=message, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Phone alert sent successfully: {alert.name}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Phone alert failed: status={response.status}, " f"error={error_text}")

        except asyncio.TimeoutError:
            logger.error(f"Phone alert timeout: {alert.name}")

        except aiohttp.ClientError as e:
            logger.error(f"Phone alert HTTP error: {e}")

    def get_alert_rules(self) -> List[Dict[str, str]]:
        """Get configured alert rules

        Returns:
            List of alert rule configurations
        """
        return self.alert_rules.copy()

    def get_alert_rule_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """Get alert rule by name

        Args:
            name: Alert rule name

        Returns:
            Alert rule configuration or None if not found
        """
        for rule in self.alert_rules:
            if rule["alert"] == name:
                return rule.copy()
        return None
