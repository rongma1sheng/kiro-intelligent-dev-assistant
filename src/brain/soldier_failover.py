"""Soldier热备切换机制 - Soldier Failover

白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

问题: 本地模型故障时交易中断
风险等级: 🔴 高

功能:
1. 本地/云端双模式决策
2. 200ms超时自动切换
3. 连续3次失败切换到Cloud模式
4. 自动恢复机制

性能要求:
- 本地超时: 200ms
- 失败阈值: 3次
- 切换延迟: < 50ms
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional

from loguru import logger


class SoldierMode(Enum):
    """Soldier运行模式

    白皮书依据: 第十二章 12.1.3 Soldier热备切换机制
    """

    NORMAL = "local"  # 本地模型
    DEGRADED = "cloud"  # 云端API
    OFFLINE = "offline"  # 离线规则引擎


@dataclass
class FailoverConfig:
    """热备切换配置

    白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

    Attributes:
        local_timeout: 本地推理超时（秒），默认0.2（200ms）
        failure_threshold: 失败阈值，默认3次
        recovery_check_interval: 恢复检查间隔（秒），默认60
        max_cloud_latency: 云端最大延迟（秒），默认2.0
    """

    local_timeout: float = 0.2  # 200ms
    failure_threshold: int = 3
    recovery_check_interval: float = 60.0
    max_cloud_latency: float = 2.0


@dataclass
class FailoverStats:
    """热备切换统计

    白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

    Attributes:
        total_decisions: 总决策次数
        local_decisions: 本地决策次数
        cloud_decisions: 云端决策次数
        failover_count: 切换次数
        recovery_count: 恢复次数
        avg_local_latency_ms: 平均本地延迟（毫秒）
        avg_cloud_latency_ms: 平均云端延迟（毫秒）
    """

    total_decisions: int = 0
    local_decisions: int = 0
    cloud_decisions: int = 0
    failover_count: int = 0
    recovery_count: int = 0
    avg_local_latency_ms: float = 0.0
    avg_cloud_latency_ms: float = 0.0
    _local_latencies: list = field(default_factory=list)
    _cloud_latencies: list = field(default_factory=list)

    def record_local_decision(self, latency_ms: float) -> None:
        """记录本地决策"""
        self.total_decisions += 1
        self.local_decisions += 1
        self._local_latencies.append(latency_ms)
        if len(self._local_latencies) > 100:
            self._local_latencies.pop(0)
        self.avg_local_latency_ms = sum(self._local_latencies) / len(self._local_latencies)

    def record_cloud_decision(self, latency_ms: float) -> None:
        """记录云端决策"""
        self.total_decisions += 1
        self.cloud_decisions += 1
        self._cloud_latencies.append(latency_ms)
        if len(self._cloud_latencies) > 100:
            self._cloud_latencies.pop(0)
        self.avg_cloud_latency_ms = sum(self._cloud_latencies) / len(self._cloud_latencies)


class SoldierFailover:
    """Soldier热备切换

    白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

    提供本地/云端双模式决策，支持自动故障切换和恢复。

    Attributes:
        redis_client: Redis客户端（可选）
        config: 热备切换配置
        mode: 当前运行模式
        failure_count: 连续失败计数
        stats: 统计信息
        local_decide_func: 本地决策函数
        cloud_decide_func: 云端决策函数
        _lock: 异步锁
    """

    # Redis键常量
    REDIS_KEY_SOLDIER_MODE = "mia:soldier:mode"

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        config: Optional[FailoverConfig] = None,
        local_decide_func: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
        cloud_decide_func: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
    ):
        """初始化Soldier热备切换

        Args:
            redis_client: Redis客户端，用于状态同步
            config: 热备切换配置
            local_decide_func: 本地决策函数
            cloud_decide_func: 云端决策函数

        Raises:
            ValueError: 当配置参数无效时
        """
        self.redis = redis_client
        self.config: FailoverConfig = config or FailoverConfig()

        # 验证配置
        if self.config.local_timeout <= 0:
            raise ValueError(f"本地超时必须 > 0，当前: {self.config.local_timeout}")

        if self.config.failure_threshold <= 0:
            raise ValueError(f"失败阈值必须 > 0，当前: {self.config.failure_threshold}")

        self.mode: SoldierMode = SoldierMode.NORMAL
        self.failure_count: int = 0
        self.stats: FailoverStats = FailoverStats()

        self.local_decide_func = local_decide_func
        self.cloud_decide_func = cloud_decide_func

        self._lock: asyncio.Lock = asyncio.Lock()

        logger.info(
            f"初始化SoldierFailover: "
            f"local_timeout={self.config.local_timeout * 1000:.0f}ms, "
            f"failure_threshold={self.config.failure_threshold}"
        )

    async def decide_with_failover(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """带自动切换的决策

        白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

        Args:
            context: 决策上下文

        Returns:
            决策结果

        Raises:
            RuntimeError: 当本地和云端都失败时
        """
        async with self._lock:
            # 检查当前模式
            if self.mode == SoldierMode.NORMAL:
                try:
                    # 尝试本地推理
                    start_time = time.time()
                    result = await asyncio.wait_for(self._local_decide(context), timeout=self.config.local_timeout)
                    latency_ms = (time.time() - start_time) * 1000

                    # 成功，重置失败计数
                    self.failure_count = 0
                    self.stats.record_local_decision(latency_ms)

                    return result

                except asyncio.TimeoutError:
                    self.failure_count += 1
                    logger.warning(
                        f"[Soldier] Local timeout " f"({self.failure_count}/{self.config.failure_threshold})"
                    )

                    # 达到阈值，切换到Cloud模式
                    if self.failure_count >= self.config.failure_threshold:
                        await self._switch_to_cloud_mode()

                    # 立即使用Cloud作为后备
                    return await self._cloud_decide_with_stats(context)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.failure_count += 1
                    logger.warning(
                        f"[Soldier] Local failed " f"({self.failure_count}/{self.config.failure_threshold}): {e}"
                    )

                    # 达到阈值，切换到Cloud模式
                    if self.failure_count >= self.config.failure_threshold:
                        await self._switch_to_cloud_mode()

                    # 立即使用Cloud作为后备
                    return await self._cloud_decide_with_stats(context)

            else:
                # 已在Cloud模式
                return await self._cloud_decide_with_stats(context)

    async def switch_to_cloud_mode(self) -> None:
        """切换到Cloud模式

        白皮书依据: 第十二章 12.1.3 Soldier热备切换机制
        """
        await self._switch_to_cloud_mode()

    async def _switch_to_cloud_mode(self) -> None:
        """切换到Cloud模式（内部方法）

        白皮书依据: 第十二章 12.1.3 Soldier热备切换机制
        """
        self.mode = SoldierMode.DEGRADED
        self.stats.failover_count += 1

        # 更新Redis状态
        if self.redis is not None:
            try:
                self.redis.set(self.REDIS_KEY_SOLDIER_MODE, "cloud")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[Soldier] Failed to update Redis mode: {e}")

        logger.critical("[Soldier] 🔄 Switched to CLOUD mode")

        # 发送告警
        self._send_alert("Soldier切换到Cloud模式")

    async def switch_to_local_mode(self) -> None:
        """切换回Local模式

        白皮书依据: 第十二章 12.1.3 Soldier热备切换机制
        """
        async with self._lock:
            self.mode = SoldierMode.NORMAL
            self.failure_count = 0
            self.stats.recovery_count += 1

            # 更新Redis状态
            if self.redis is not None:
                try:
                    self.redis.set(self.REDIS_KEY_SOLDIER_MODE, "local")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"[Soldier] Failed to update Redis mode: {e}")

            logger.info("[Soldier] 🔄 Switched back to LOCAL mode")

    async def local_decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """本地模型推理

        白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

        Args:
            context: 决策上下文

        Returns:
            决策结果
        """
        return await self._local_decide(context)

    async def cloud_decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """云端API推理

        白皮书依据: 第十二章 12.1.3 Soldier热备切换机制

        Args:
            context: 决策上下文

        Returns:
            决策结果
        """
        return await self._cloud_decide(context)

    async def _local_decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """本地模型推理（内部方法）

        Args:
            context: 决策上下文

        Returns:
            决策结果
        """
        if self.local_decide_func is not None:
            return await self.local_decide_func(context)

        # 默认实现：返回空决策
        logger.warning("[Soldier] No local_decide_func configured, returning empty decision")
        return {"action": "hold", "confidence": 0.0, "source": "local_default"}

    async def _cloud_decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """云端API推理（内部方法）

        Args:
            context: 决策上下文

        Returns:
            决策结果
        """
        if self.cloud_decide_func is not None:
            return await self.cloud_decide_func(context)

        # 默认实现：返回空决策
        logger.warning("[Soldier] No cloud_decide_func configured, returning empty decision")
        return {"action": "hold", "confidence": 0.0, "source": "cloud_default"}

    async def _cloud_decide_with_stats(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """带统计的云端决策（内部方法）

        Args:
            context: 决策上下文

        Returns:
            决策结果
        """
        start_time = time.time()
        result = await self._cloud_decide(context)
        latency_ms = (time.time() - start_time) * 1000
        self.stats.record_cloud_decision(latency_ms)
        return result

    def _send_alert(self, message: str) -> None:
        """发送告警（内部方法）

        Args:
            message: 告警消息
        """
        # 这里可以集成企业微信等告警渠道
        logger.warning(f"[Alert] {message}")

    def get_mode(self) -> SoldierMode:
        """获取当前运行模式

        Returns:
            当前运行模式
        """
        return self.mode

    def get_failure_count(self) -> int:
        """获取连续失败计数

        Returns:
            连续失败次数
        """
        return self.failure_count

    def get_stats(self) -> FailoverStats:
        """获取统计信息

        Returns:
            统计信息
        """
        return self.stats

    def is_in_failover_mode(self) -> bool:
        """检查是否处于故障切换模式

        Returns:
            是否处于Cloud模式
        """
        return self.mode == SoldierMode.DEGRADED
