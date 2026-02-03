"""AUM感知器

白皮书依据: 第0章 资本物理 (Capital Physics)
"""

import asyncio
from datetime import datetime
from typing import Callable, Optional

from loguru import logger


class AUMSensor:
    """AUM感知器

    白皮书依据: 第0章 资本物理 (Capital Physics)

    职责：
    - 实时感知当前AUM
    - 检测AUM变化并触发档位重新评估
    - 发布档位切换事件
    """

    def __init__(
        self, audit_service_client: Optional[any] = None, monitoring_interval: int = 60, change_threshold: float = 0.05
    ):
        """初始化AUM感知器

        Args:
            audit_service_client: 审计服务客户端（可选，用于依赖注入）
            monitoring_interval: 监控间隔（秒），默认60秒
            change_threshold: AUM变化阈值（百分比），默认5%
        """
        self.audit_service_client = audit_service_client
        self.monitoring_interval = monitoring_interval
        self.change_threshold = change_threshold

        # 当前状态
        self.current_aum: float = 0.0
        self.last_check_time: Optional[datetime] = None
        self.is_monitoring: bool = False

        # 事件回调
        self.tier_change_callbacks: list[Callable] = []

        logger.info(
            f"AUMSensor初始化完成 - " f"监控间隔: {monitoring_interval}秒, " f"变化阈值: {change_threshold*100}%"
        )

    async def get_current_aum(self) -> float:
        """获取当前AUM

        白皮书依据: Requirement 1.2

        从审计服务获取实时资金规模

        Returns:
            当前AUM

        Raises:
            AuditServiceUnavailableError: 当审计服务不可用时
        """
        try:
            if self.audit_service_client is not None:
                # 从审计服务获取AUM
                aum = await self._fetch_aum_from_audit_service()
            else:
                # 模拟模式：使用缓存的AUM或默认值
                aum = self.current_aum if self.current_aum > 0 else 10000.0
                logger.warning(f"审计服务未配置，使用模拟AUM: {aum}")

            self.current_aum = aum
            self.last_check_time = datetime.now()

            logger.debug(f"获取当前AUM: {aum:.2f}")
            return aum

        except Exception as e:
            logger.error(f"获取AUM失败: {e}")
            # 如果有缓存值，返回缓存值
            if self.current_aum > 0:
                logger.warning(f"使用缓存的AUM值: {self.current_aum}")
                return self.current_aum
            raise AuditServiceUnavailableError(f"无法获取AUM: {e}") from e

    async def monitor_aum_changes(self) -> None:
        """监控AUM变化

        白皮书依据: Requirement 2.8

        每60秒检查一次AUM，如果变化超过阈值则触发重新评估

        这是一个长期运行的协程，应该在后台任务中运行
        """
        self.is_monitoring = True
        logger.info("开始监控AUM变化")

        try:
            while self.is_monitoring:
                try:
                    # 获取当前AUM
                    old_aum = self.current_aum
                    new_aum = await self.get_current_aum()

                    # 检查变化是否超过阈值
                    if old_aum > 0:
                        change_pct = abs(new_aum - old_aum) / old_aum

                        if change_pct >= self.change_threshold:
                            logger.info(
                                f"AUM变化超过阈值 - "
                                f"旧值: {old_aum:.2f}, "
                                f"新值: {new_aum:.2f}, "
                                f"变化: {change_pct*100:.2f}%"
                            )

                            # 触发档位重新评估
                            await self._trigger_tier_reevaluation(old_aum, new_aum)

                    # 等待下一次检查
                    await asyncio.sleep(self.monitoring_interval)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"AUM监控循环出错: {e}")
                    # 继续监控，不中断
                    await asyncio.sleep(self.monitoring_interval)

        except asyncio.CancelledError:
            logger.info("AUM监控已停止")
            self.is_monitoring = False
            raise

    def stop_monitoring(self) -> None:
        """停止AUM监控"""
        self.is_monitoring = False
        logger.info("停止AUM监控")

    async def publish_tier_change_event(self, old_tier: str, new_tier: str) -> None:
        """发布档位切换事件

        白皮书依据: Requirement 2.7

        Args:
            old_tier: 旧档位
            new_tier: 新档位
        """
        event = {
            "event_type": "tier_change",
            "old_tier": old_tier,
            "new_tier": new_tier,
            "aum": self.current_aum,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"发布档位切换事件: {old_tier} → {new_tier}")

        # 调用所有注册的回调函数
        for callback in self.tier_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"档位切换事件回调失败: {e}")

    def register_tier_change_callback(self, callback: Callable) -> None:
        """注册档位切换事件回调

        Args:
            callback: 回调函数，接收事件字典作为参数
        """
        self.tier_change_callbacks.append(callback)
        logger.debug(f"注册档位切换回调: {callback.__name__}")

    async def _fetch_aum_from_audit_service(self) -> float:
        """从审计服务获取AUM（内部方法）

        Returns:
            当前AUM
        """
        # PRD-REQ: 实现与审计服务的实际集成 (PRD 1.1 代码库审计系统)
        # 这里是模拟实现
        if hasattr(self.audit_service_client, "get_aum"):
            return await self.audit_service_client.get_aum()

        # 模拟返回
        return self.current_aum if self.current_aum > 0 else 10000.0

    async def _trigger_tier_reevaluation(self, old_aum: float, new_aum: float) -> None:
        """触发档位重新评估（内部方法）

        Args:
            old_aum: 旧AUM
            new_aum: 新AUM
        """
        # 导入Tier类
        from src.capital.tier import Tier  # pylint: disable=import-outside-toplevel

        old_tier = Tier.from_aum(old_aum)
        new_tier = Tier.from_aum(new_aum)

        if old_tier != new_tier:
            await self.publish_tier_change_event(old_tier, new_tier)


class AuditServiceUnavailableError(Exception):
    """审计服务不可用异常"""
