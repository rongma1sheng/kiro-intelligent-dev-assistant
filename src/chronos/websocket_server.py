"""
WebSocket服务器实现

白皮书依据: 第一章 1.1, 第三章 3.2 混合通信总线
实现Binary WebSocket (Protobuf/MessagePack)雷达数据推流
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Set

import msgpack
import websockets
from loguru import logger
from websockets.server import WebSocketServerProtocol  # pylint: disable=e0611


class MessageType(Enum):
    """消息类型枚举

    白皮书依据: 第三章 3.2
    """

    RADAR_SIGNAL = "radar_signal"
    MARKET_DATA = "market_data"
    SYSTEM_STATUS = "system_status"
    HEARTBEAT = "heartbeat"
    CONTROL = "control"


@dataclass
class RadarSignal:
    """雷达信号数据

    白皮书依据: 第二章 2.3 Algo Hunter

    Attributes:
        symbol: 标的代码
        timestamp: 时间戳
        main_force_probability: 主力概率 (0-1)
        volume: 成交量
        price: 价格
        signal_strength: 信号强度
    """

    symbol: str
    timestamp: float
    main_force_probability: float
    volume: int
    price: float
    signal_strength: float = 0.0


@dataclass
class MarketData:
    """市场数据

    Attributes:
        symbol: 标的代码
        timestamp: 时间戳
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
    """

    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SystemStatus:
    """系统状态

    Attributes:
        timestamp: 时间戳
        state: 系统状态
        services: 服务状态
        performance: 性能指标
    """

    timestamp: float
    state: str
    services: Dict[str, str]
    performance: Dict[str, float]


@dataclass
class WebSocketMessage:
    """WebSocket消息

    Attributes:
        type: 消息类型
        timestamp: 时间戳
        data: 消息数据
        sequence_id: 序列号
    """

    type: str
    timestamp: float
    data: Dict[str, Any]
    sequence_id: int = 0


class WebSocketServer:
    """WebSocket服务器

    白皮书依据: 第一章 1.1, 第三章 3.2

    实现Binary WebSocket推流，支持雷达数据、市场数据和系统状态的实时推送。

    Attributes:
        host: 服务器地址
        port: 服务器端口
        clients: 连接的客户端集合
        message_queue: 消息队列
        sequence_counter: 消息序列计数器
        server: WebSocket服务器实例
        is_running: 运行状态

    Performance:
        吞吐量: > 1000 msg/s
        延迟: < 10ms
    """

    def __init__(self, host: str = "localhost", port: int = 8502):
        """初始化WebSocket服务器

        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.sequence_counter = 0
        self.server = None
        self.is_running = False

        # 性能统计
        self.messages_sent = 0
        self.bytes_sent = 0
        self.start_time = time.time()

        # 线程池用于消息处理
        self.executor = ThreadPoolExecutor(max_workers=4)

        logger.info(f"WebSocket服务器初始化: {host}:{port}")

    async def start(self) -> bool:
        """启动WebSocket服务器

        Returns:
            启动是否成功
        """
        try:
            logger.info(f"启动WebSocket服务器: {self.host}:{self.port}")

            # 启动WebSocket服务器
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                max_size=1024 * 1024,  # 1MB
                compression=None,  # 禁用压缩以提高性能
            )

            self.is_running = True
            self.start_time = time.time()

            # 启动消息广播任务
            asyncio.create_task(self.broadcast_messages())

            logger.info("WebSocket服务器启动成功")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动WebSocket服务器失败: {e}")
            return False

    async def stop(self) -> bool:
        """停止WebSocket服务器

        Returns:
            停止是否成功
        """
        try:
            logger.info("停止WebSocket服务器...")

            self.is_running = False

            # 关闭所有客户端连接
            if self.clients:
                await asyncio.gather(*[client.close() for client in self.clients.copy()], return_exceptions=True)

            # 关闭服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()

            # 关闭线程池
            self.executor.shutdown(wait=True)

            logger.info("WebSocket服务器已停止")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"停止WebSocket服务器失败: {e}")
            return False

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):  # pylint: disable=unused-argument
        """处理客户端连接

        Args:
            websocket: WebSocket连接
            path: 请求路径
        """
        client_addr = websocket.remote_address
        logger.info(f"新客户端连接: {client_addr}")

        # 添加到客户端集合
        self.clients.add(websocket)

        try:
            # 发送欢迎消息
            welcome_msg = WebSocketMessage(
                type=MessageType.SYSTEM_STATUS.value,
                timestamp=time.time(),
                data={"status": "connected", "server_time": time.time()},
            )
            await self.send_to_client(websocket, welcome_msg)

            # 处理客户端消息
            async for message in websocket:
                try:
                    await self.handle_client_message(websocket, message)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"处理客户端消息失败: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端断开连接: {client_addr}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"客户端连接异常: {client_addr}, {e}")
        finally:
            # 从客户端集合中移除
            self.clients.discard(websocket)
            logger.info(f"客户端连接已清理: {client_addr}")

    async def handle_client_message(self, websocket: WebSocketServerProtocol, message):
        """处理客户端消息

        Args:
            websocket: WebSocket连接
            message: 客户端消息
        """
        try:
            # 尝试解析JSON消息
            if isinstance(message, str):
                data = json.loads(message)
            else:
                # 二进制消息，使用msgpack解析
                data = msgpack.unpackb(message, raw=False)

            msg_type = data.get("type")

            if msg_type == MessageType.HEARTBEAT.value:
                # 心跳响应
                response = WebSocketMessage(
                    type=MessageType.HEARTBEAT.value, timestamp=time.time(), data={"pong": True}
                )
                await self.send_to_client(websocket, response)

            elif msg_type == MessageType.CONTROL.value:
                # 控制消息
                await self.handle_control_message(websocket, data)

            else:
                logger.warning(f"未知消息类型: {msg_type}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"解析客户端消息失败: {e}")

    async def handle_control_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """处理控制消息

        Args:
            websocket: WebSocket连接
            data: 控制消息数据
        """
        command = data.get("command")

        if command == "subscribe":
            # 订阅消息类型
            msg_types = data.get("message_types", [])
            logger.info(f"客户端订阅消息类型: {msg_types}")

        elif command == "get_status":
            # 获取服务器状态
            status = self.get_server_status()
            response = WebSocketMessage(type=MessageType.SYSTEM_STATUS.value, timestamp=time.time(), data=status)
            await self.send_to_client(websocket, response)

        else:
            logger.warning(f"未知控制命令: {command}")

    async def send_to_client(self, websocket: WebSocketServerProtocol, message: WebSocketMessage):
        """发送消息到客户端

        Args:
            websocket: WebSocket连接
            message: 消息对象
        """
        try:
            # 设置序列号
            message.sequence_id = self._get_next_sequence()

            # 序列化消息
            data = msgpack.packb(asdict(message))

            # 发送消息
            await websocket.send(data)

            # 更新统计
            self.messages_sent += 1
            self.bytes_sent += len(data)

        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，从客户端集合中移除
            self.clients.discard(websocket)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发送消息到客户端失败: {e}")

    async def broadcast_message(self, message: WebSocketMessage):
        """广播消息到所有客户端

        Args:
            message: 消息对象
        """
        if not self.clients:
            return

        # 设置序列号
        message.sequence_id = self._get_next_sequence()

        # 序列化消息
        data = msgpack.packb(asdict(message))

        # 并发发送到所有客户端
        tasks = []
        for client in self.clients.copy():
            tasks.append(self._send_data_to_client(client, data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

            # 更新统计
            self.messages_sent += len(tasks)
            self.bytes_sent += len(data) * len(tasks)

    async def _send_data_to_client(self, websocket: WebSocketServerProtocol, data: bytes):
        """发送数据到客户端（内部方法）

        Args:
            websocket: WebSocket连接
            data: 序列化数据
        """
        try:
            await websocket.send(data)
        except websockets.exceptions.ConnectionClosed:
            # 连接已关闭，从客户端集合中移除
            self.clients.discard(websocket)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发送数据到客户端失败: {e}")
            self.clients.discard(websocket)

    async def broadcast_messages(self):
        """消息广播任务"""
        logger.info("启动消息广播任务")

        while self.is_running:
            try:
                # 从队列获取消息
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)

                # 广播消息
                await self.broadcast_message(message)

            except asyncio.TimeoutError:
                # 超时，继续循环
                continue
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"消息广播任务异常: {e}")
                await asyncio.sleep(1)

        logger.info("消息广播任务已停止")

    async def send_radar_signal(self, signal: RadarSignal):
        """发送雷达信号

        Args:
            signal: 雷达信号
        """
        message = WebSocketMessage(type=MessageType.RADAR_SIGNAL.value, timestamp=time.time(), data=asdict(signal))

        await self.message_queue.put(message)

    async def send_market_data(self, data: MarketData):
        """发送市场数据

        Args:
            data: 市场数据
        """
        message = WebSocketMessage(type=MessageType.MARKET_DATA.value, timestamp=time.time(), data=asdict(data))

        await self.message_queue.put(message)

    async def send_system_status(self, status: SystemStatus):
        """发送系统状态

        Args:
            status: 系统状态
        """
        message = WebSocketMessage(type=MessageType.SYSTEM_STATUS.value, timestamp=time.time(), data=asdict(status))

        await self.message_queue.put(message)

    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态

        Returns:
            服务器状态信息
        """
        uptime = time.time() - self.start_time

        return {
            "is_running": self.is_running,
            "client_count": len(self.clients),
            "messages_sent": self.messages_sent,
            "bytes_sent": self.bytes_sent,
            "uptime_seconds": uptime,
            "messages_per_second": self.messages_sent / uptime if uptime > 0 else 0,
            "queue_size": self.message_queue.qsize(),
        }

    def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标

        Returns:
            性能指标
        """
        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "messages_per_second": self.messages_sent / uptime if uptime > 0 else 0,
            "bytes_per_second": self.bytes_sent / uptime if uptime > 0 else 0,
            "client_count": len(self.clients),
            "queue_size": self.message_queue.qsize(),
        }

    def _get_next_sequence(self) -> int:
        """获取下一个序列号

        Returns:
            序列号
        """
        self.sequence_counter += 1
        return self.sequence_counter


# 全局WebSocket服务器实例
websocket_server = WebSocketServer()


async def start_websocket_server(host: str = "localhost", port: int = 8502) -> bool:
    """启动WebSocket服务器

    Args:
        host: 服务器地址
        port: 服务器端口

    Returns:
        启动是否成功
    """
    global websocket_server  # pylint: disable=w0603
    websocket_server = WebSocketServer(host, port)
    return await websocket_server.start()


async def stop_websocket_server() -> bool:
    """停止WebSocket服务器

    Returns:
        停止是否成功
    """
    global websocket_server  # pylint: disable=w0602
    if websocket_server:
        return await websocket_server.stop()
    return True


def get_websocket_server() -> WebSocketServer:
    """获取WebSocket服务器实例

    Returns:
        WebSocket服务器实例
    """
    return websocket_server
