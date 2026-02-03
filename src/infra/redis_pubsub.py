"""Redis Pub/Sub控制总线

白皮书依据: 第三章 3.2 混合通信总线 - Control Plane (Redis Pub/Sub)

实现基于Redis的发布订阅机制，用于传输低频控制指令和事件通知。
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not available, using mock implementation")


class CommandType(Enum):
    """控制指令类型

    白皮书依据: 第三章 3.2 控制指令
    """

    # 系统控制
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_RESTART = "system_restart"
    SYSTEM_PAUSE = "system_pause"
    SYSTEM_RESUME = "system_resume"

    # 状态切换
    STATE_CHANGE = "state_change"

    # 交易控制
    TRADING_START = "trading_start"
    TRADING_STOP = "trading_stop"
    EMERGENCY_STOP = "emergency_stop"

    # 策略控制
    STRATEGY_ENABLE = "strategy_enable"
    STRATEGY_DISABLE = "strategy_disable"
    STRATEGY_RELOAD = "strategy_reload"

    # 数据控制
    DATA_REFRESH = "data_refresh"
    DATA_CLEAR_CACHE = "data_clear_cache"

    # 风控控制
    RISK_LIMIT_UPDATE = "risk_limit_update"
    POSITION_CLOSE = "position_close"


class EventType(Enum):
    """事件类型

    白皮书依据: 第三章 3.2 事件通知
    """

    # 系统事件
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    SYSTEM_ERROR = "system_error"

    # 状态事件
    STATE_CHANGED = "state_changed"

    # 交易事件
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    TRADE_EXECUTED = "trade_executed"

    # 策略事件
    STRATEGY_SIGNAL = "strategy_signal"
    STRATEGY_ERROR = "strategy_error"

    # 数据事件
    DATA_UPDATED = "data_updated"
    DATA_ERROR = "data_error"

    # 风控事件
    RISK_ALERT = "risk_alert"
    POSITION_LIMIT_REACHED = "position_limit_reached"

    # 市场事件
    MARKET_REGIME_CHANGED = "market_regime_changed"


@dataclass
class ControlCommand:
    """控制指令

    白皮书依据: 第三章 3.2 控制指令

    Attributes:
        command_type: 指令类型
        command_id: 指令ID
        timestamp: 时间戳
        source: 来源模块
        target: 目标模块
        params: 参数
        priority: 优先级 (0-10, 10最高)
    """

    command_type: CommandType
    command_id: str
    timestamp: datetime
    source: str
    target: str
    params: Dict[str, Any]
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "command_type": self.command_type.value,
            "command_id": self.command_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "target": self.target,
            "params": self.params,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlCommand":
        """从字典创建"""
        return cls(
            command_type=CommandType(data["command_type"]),
            command_id=data["command_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            target=data["target"],
            params=data["params"],
            priority=data.get("priority", 5),
        )


@dataclass
class SystemEvent:
    """系统事件

    白皮书依据: 第三章 3.2 事件通知

    Attributes:
        event_type: 事件类型
        event_id: 事件ID
        timestamp: 时间戳
        source: 来源模块
        data: 事件数据
        severity: 严重程度 (info/warning/error/critical)
    """

    event_type: EventType
    event_id: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    severity: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemEvent":
        """从字典创建"""
        return cls(
            event_type=EventType(data["event_type"]),
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            data=data["data"],
            severity=data.get("severity", "info"),
        )


class RedisPubSubError(Exception):
    """Redis Pub/Sub错误"""


class RedisPubSubManager:
    """Redis Pub/Sub管理器

    白皮书依据: 第三章 3.2 混合通信总线 - Control Plane

    实现基于Redis的发布订阅机制，用于：
    - 控制指令传输
    - 事件通知
    - 模块间通信

    Attributes:
        redis_url: Redis连接URL
        redis_client: Redis客户端
        pubsub: PubSub对象
        command_handlers: 指令处理器
        event_handlers: 事件处理器
        running: 是否运行中

    Example:
        >>> manager = RedisPubSubManager("redis://localhost:6379")
        >>> await manager.connect()
        >>> await manager.subscribe_commands("soldier", handler)
        >>> await manager.publish_event(event)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        command_channel: str = "mia:commands",
        event_channel: str = "mia:events",
    ):
        """初始化Redis Pub/Sub管理器

        Args:
            redis_url: Redis连接URL
            command_channel: 指令频道前缀
            event_channel: 事件频道前缀

        Raises:
            RedisPubSubError: 当Redis不可用时
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using mock mode")
            self._mock_mode = True
            self._mock_subscribers: Dict[str, List[Callable]] = {}
            self._mock_messages: List[Dict[str, Any]] = []
        else:
            self._mock_mode = False

        self.redis_url = redis_url
        self.command_channel = command_channel
        self.event_channel = event_channel

        self.redis_client: Optional[Any] = None
        self.pubsub: Optional[Any] = None

        self.command_handlers: Dict[str, List[Callable]] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}

        self.running = False
        self._tasks: List[asyncio.Task] = []

        logger.info(
            f"RedisPubSubManager initialized: "
            f"url={redis_url}, "
            f"command_channel={command_channel}, "
            f"event_channel={event_channel}, "
            f"mock_mode={self._mock_mode}"
        )

    async def connect(self) -> None:
        """连接到Redis

        白皮书依据: 第三章 3.2

        Raises:
            RedisPubSubError: 当连接失败时
        """
        if self._mock_mode:
            logger.info("Mock mode: skipping Redis connection")
            return

        try:
            self.redis_client = await aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

            # 测试连接
            await self.redis_client.ping()

            self.pubsub = self.redis_client.pubsub()

            logger.info(f"Connected to Redis: {self.redis_url}")

        except Exception as e:
            raise RedisPubSubError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """断开Redis连接"""
        if self._mock_mode:
            return

        try:
            # 停止所有任务
            self.running = False
            for task in self._tasks:
                task.cancel()

            # 等待任务完成
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

            # 关闭pubsub
            if self.pubsub:
                await self.pubsub.close()

            # 关闭客户端
            if self.redis_client:
                await self.redis_client.close()

            logger.info("Disconnected from Redis")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error disconnecting from Redis: {e}")

    async def publish_command(self, command: ControlCommand, target_module: Optional[str] = None) -> None:
        """发布控制指令

        白皮书依据: 第三章 3.2 控制指令

        Args:
            command: 控制指令
            target_module: 目标模块，None表示广播

        Raises:
            RedisPubSubError: 当发布失败时
        """
        try:
            # 构造频道名
            if target_module:
                channel = f"{self.command_channel}:{target_module}"
            else:
                channel = self.command_channel

            # 序列化指令
            message = json.dumps(command.to_dict())

            if self._mock_mode:
                # Mock模式：直接调用处理器
                self._mock_messages.append({"channel": channel, "message": message, "type": "command"})

                # 触发处理器
                handlers = self._mock_subscribers.get(channel, [])
                for handler in handlers:
                    await handler(command)
            else:
                # 发布到Redis
                await self.redis_client.publish(channel, message)

            logger.debug(f"Published command: {command.command_type.value} " f"to {channel}")

        except Exception as e:
            raise RedisPubSubError(f"Failed to publish command: {e}") from e

    async def publish_event(self, event: SystemEvent, event_category: Optional[str] = None) -> None:
        """发布系统事件

        白皮书依据: 第三章 3.2 事件通知

        Args:
            event: 系统事件
            event_category: 事件分类，None表示广播

        Raises:
            RedisPubSubError: 当发布失败时
        """
        try:
            # 构造频道名
            if event_category:
                channel = f"{self.event_channel}:{event_category}"
            else:
                channel = self.event_channel

            # 序列化事件
            message = json.dumps(event.to_dict())

            if self._mock_mode:
                # Mock模式：直接调用处理器
                self._mock_messages.append({"channel": channel, "message": message, "type": "event"})

                # 触发处理器
                handlers = self._mock_subscribers.get(channel, [])
                for handler in handlers:
                    await handler(event)
            else:
                # 发布到Redis
                await self.redis_client.publish(channel, message)

            logger.debug(f"Published event: {event.event_type.value} " f"to {channel}")

        except Exception as e:
            raise RedisPubSubError(f"Failed to publish event: {e}") from e

    async def subscribe_commands(self, module_name: str, handler: Callable[[ControlCommand], None]) -> None:
        """订阅控制指令

        白皮书依据: 第三章 3.2 控制指令

        Args:
            module_name: 模块名称
            handler: 指令处理器
        """
        channel = f"{self.command_channel}:{module_name}"

        if self._mock_mode:
            # Mock模式：注册处理器
            if channel not in self._mock_subscribers:
                self._mock_subscribers[channel] = []
            self._mock_subscribers[channel].append(handler)
        else:
            # 订阅频道
            await self.pubsub.subscribe(channel)

            # 注册处理器
            if channel not in self.command_handlers:
                self.command_handlers[channel] = []
            self.command_handlers[channel].append(handler)

        logger.info(f"Subscribed to commands: {channel}")

    async def subscribe_events(self, event_category: str, handler: Callable[[SystemEvent], None]) -> None:
        """订阅系统事件

        白皮书依据: 第三章 3.2 事件通知

        Args:
            event_category: 事件分类
            handler: 事件处理器
        """
        channel = f"{self.event_channel}:{event_category}"

        if self._mock_mode:
            # Mock模式：注册处理器
            if channel not in self._mock_subscribers:
                self._mock_subscribers[channel] = []
            self._mock_subscribers[channel].append(handler)
        else:
            # 订阅频道
            await self.pubsub.subscribe(channel)

            # 注册处理器
            if channel not in self.event_handlers:
                self.event_handlers[channel] = []
            self.event_handlers[channel].append(handler)

        logger.info(f"Subscribed to events: {channel}")

    async def start_listening(self) -> None:
        """开始监听消息

        白皮书依据: 第三章 3.2
        """
        if self._mock_mode:
            logger.info("Mock mode: message listening simulated")
            return

        if self.running:
            logger.warning("Already listening")
            return

        self.running = True

        # 创建监听任务
        task = asyncio.create_task(self._listen_loop())
        self._tasks.append(task)

        logger.info("Started listening for messages")

    async def _listen_loop(self) -> None:
        """消息监听循环"""
        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] != "message":
                    continue

                channel = message["channel"]
                data = message["data"]

                try:
                    # 解析消息
                    msg_dict = json.loads(data)

                    # 判断消息类型
                    if channel.startswith(self.command_channel):
                        # 控制指令
                        command = ControlCommand.from_dict(msg_dict)
                        await self._handle_command(channel, command)

                    elif channel.startswith(self.event_channel):
                        # 系统事件
                        event = SystemEvent.from_dict(msg_dict)
                        await self._handle_event(channel, event)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Error processing message: {e}")

        except asyncio.CancelledError:
            logger.info("Listen loop cancelled")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error in listen loop: {e}")

    async def _handle_command(self, channel: str, command: ControlCommand) -> None:
        """处理控制指令"""
        handlers = self.command_handlers.get(channel, [])

        for handler in handlers:
            try:
                await handler(command)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Error in command handler: {e}, " f"command={command.command_type.value}")

    async def _handle_event(self, channel: str, event: SystemEvent) -> None:
        """处理系统事件"""
        handlers = self.event_handlers.get(channel, [])

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Error in event handler: {e}, " f"event={event.event_type.value}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "redis_url": self.redis_url,
            "command_channel": self.command_channel,
            "event_channel": self.event_channel,
            "mock_mode": self._mock_mode,
            "running": self.running,
            "command_handlers": len(self.command_handlers),
            "event_handlers": len(self.event_handlers),
            "active_tasks": len([t for t in self._tasks if not t.done()]),
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
