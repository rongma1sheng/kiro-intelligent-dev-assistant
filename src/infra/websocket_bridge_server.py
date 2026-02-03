"""WebSocket Bridge Server - 60Hz Radar Data Streaming

白皮书依据: 第十五章 15.2 WebSocket侧通道推流

核心功能:
- 启动WebSocket服务器（端口8502）
- 60Hz实时雷达数据推流（16.67ms间隔）
- 处理客户端连接和断开
- 从SharedMemory读取雷达数据
"""

import asyncio
from multiprocessing import shared_memory
from typing import Any, Dict, Optional, Set

import msgpack
import websockets
from loguru import logger
from websockets.server import WebSocketServerProtocol  # pylint: disable=e0611


class WebSocketBridgeServer:
    """WebSocket桥接服务器 - 60Hz雷达数据推流

    白皮书依据: 第十五章 15.2 WebSocket侧通道推流

    三位一体架构: The Eye (Client Terminals) 通过WebSocket接收来自
    The Body (AMD AI Max) 的实时雷达数据。纯粹可视化终端，不承担计算任务。

    Attributes:
        host: 服务器主机地址（默认0.0.0.0）
        port: 服务器端口（默认8502）
        clients: 已连接的客户端集合
        running: 服务器运行状态
        shm_radar: 雷达数据共享内存
        frame_rate: 推流帧率（默认60Hz）
        frame_interval: 帧间隔（1/60 = 16.67ms）
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8502, frame_rate: int = 60):
        """初始化WebSocket桥接服务器

        Args:
            host: 服务器主机地址
            port: 服务器端口
            frame_rate: 推流帧率（Hz）

        Raises:
            ValueError: 当frame_rate <= 0时
        """
        if frame_rate <= 0:
            raise ValueError(f"帧率必须 > 0: {frame_rate}")

        self.host: str = host
        self.port: int = port
        self.frame_rate: int = frame_rate
        self.frame_interval: float = 1.0 / frame_rate

        self.clients: Set[WebSocketServerProtocol] = set()
        self.running: bool = False
        self.shm_radar: Optional[shared_memory.SharedMemory] = None

        logger.info(
            f"[WebSocket] 初始化完成 - "
            f"地址: {host}:{port}, "
            f"帧率: {frame_rate}Hz, "
            f"帧间隔: {self.frame_interval*1000:.2f}ms"
        )

    async def start(self) -> None:
        """启动WebSocket服务器

        白皮书依据: 第十五章 15.2 WebSocket侧通道推流

        启动流程:
        1. 设置运行状态
        2. 打开雷达数据共享内存
        3. 启动WebSocket服务器
        4. 启动广播循环

        Raises:
            FileNotFoundError: 当共享内存不存在时
            RuntimeError: 当服务器启动失败时
        """
        self.running = True

        # 打开共享内存
        try:
            self.shm_radar = shared_memory.SharedMemory(name="radar_data")
            logger.info(f"[WebSocket] 共享内存已连接 - " f"名称: radar_data, " f"大小: {self.shm_radar.size} bytes")
        except FileNotFoundError as e:
            logger.error(f"[WebSocket] 共享内存不存在: {e}")
            raise

        logger.info(f"[WebSocket] 服务器启动中 - {self.host}:{self.port}")

        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                logger.info(f"[WebSocket] ✅ 服务器已启动 - " f"{self.host}:{self.port}")

                # 启动广播循环和保持服务运行
                await asyncio.gather(self.broadcast_loop(), asyncio.Future())  # 永不完成的Future，保持服务运行
        except Exception as e:
            logger.error(f"[WebSocket] 服务器启动失败: {e}")
            raise RuntimeError(f"WebSocket服务器启动失败: {e}") from e

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """处理客户端连接

        白皮书依据: 第十五章 15.2 WebSocket侧通道推流

        处理流程:
        1. 添加客户端到集合
        2. 记录连接日志
        3. 等待客户端断开
        4. 从集合中移除客户端
        5. 记录断开日志

        Args:
            websocket: WebSocket连接对象
            path: 请求路径
        """
        # 添加客户端
        self.clients.add(websocket)

        client_addr = websocket.remote_address
        logger.info(
            f"[WebSocket] 客户端已连接 - " f"地址: {client_addr}, " f"路径: {path}, " f"总数: {len(self.clients)}"
        )

        try:
            # 等待客户端断开
            await websocket.wait_closed()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[WebSocket] 客户端连接异常: {client_addr}, {e}")
        finally:
            # 移除客户端
            self.clients.discard(websocket)
            logger.info(f"[WebSocket] 客户端已断开 - " f"地址: {client_addr}, " f"剩余: {len(self.clients)}")

    async def broadcast_loop(self) -> None:
        """推流循环 - 60Hz

        白皮书依据: 第十五章 15.2 WebSocket侧通道推流

        推流流程:
        1. 从共享内存读取雷达数据
        2. 使用msgpack打包数据
        3. 广播到所有已连接客户端
        4. 等待帧间隔（16.67ms）
        5. 重复

        性能要求:
        - 帧率: 60Hz
        - 帧间隔: 16.67ms
        - 延迟: < 20ms
        """
        logger.info(f"[WebSocket] 广播循环已启动 - " f"帧率: {self.frame_rate}Hz")

        frame_count = 0

        while self.running:
            try:
                # 读取雷达数据
                radar_data = self._read_radar_data()

                # 如果有数据且有客户端，则广播
                if radar_data and self.clients:
                    # 打包数据
                    packed_data = msgpack.packb(radar_data)

                    # 广播到所有客户端
                    await self._broadcast_to_clients(packed_data)

                    frame_count += 1

                    if frame_count % 600 == 0:  # 每10秒记录一次
                        logger.debug(f"[WebSocket] 已推送 {frame_count} 帧 - " f"客户端数: {len(self.clients)}")

                # 等待帧间隔
                await asyncio.sleep(self.frame_interval)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"[WebSocket] 广播循环错误: {e}")
                await asyncio.sleep(self.frame_interval)

    def _read_radar_data(self) -> Optional[Dict[str, Any]]:
        """从SharedMemory读取雷达数据

        白皮书依据: 第十五章 15.2 WebSocket侧通道推流

        读取流程:
        1. 从共享内存读取字节数据
        2. 使用msgpack解包
        3. 返回雷达数据字典

        Returns:
            雷达数据字典，包含:
            - probabilities: 主力概率列表
            - symbols: 股票代码列表
            - timestamp: 时间戳

            如果读取失败返回None
        """
        if self.shm_radar is None:
            logger.warning("[WebSocket] 共享内存未初始化")
            return None

        try:
            # 读取数据（假设使用SPSC协议，前1024字节）
            data_bytes = bytes(self.shm_radar.buf[:1024])

            # 解包（使用strict=False允许额外数据）
            unpacker = msgpack.Unpacker(raw=False)
            unpacker.feed(data_bytes)
            radar_data = next(unpacker)

            return radar_data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[WebSocket] 读取雷达数据失败: {e}")
            return None

    async def _broadcast_to_clients(self, packed_data: bytes) -> None:
        """广播数据到所有客户端

        Args:
            packed_data: 打包后的数据
        """
        if not self.clients:
            return

        # 并发发送到所有客户端
        results = await asyncio.gather(*[client.send(packed_data) for client in self.clients], return_exceptions=True)

        # 检查发送结果
        failed_count = sum(1 for r in results if isinstance(r, Exception))
        if failed_count > 0:
            logger.warning(f"[WebSocket] 广播失败 - " f"失败: {failed_count}/{len(self.clients)}")

    async def stop(self) -> None:
        """停止WebSocket服务器

        停止流程:
        1. 设置运行状态为False
        2. 关闭所有客户端连接
        3. 关闭共享内存
        """
        logger.info("[WebSocket] 服务器停止中...")

        self.running = False

        # 关闭所有客户端
        if self.clients:
            await asyncio.gather(*[client.close() for client in self.clients], return_exceptions=True)
            self.clients.clear()

        # 关闭共享内存
        if self.shm_radar:
            try:
                self.shm_radar.close()
                logger.info("[WebSocket] 共享内存已关闭")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"[WebSocket] 关闭共享内存失败: {e}")

        logger.info("[WebSocket] ✅ 服务器已停止")

    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态

        Returns:
            状态字典，包含:
            - running: 运行状态
            - host: 主机地址
            - port: 端口
            - frame_rate: 帧率
            - client_count: 客户端数量
            - shm_connected: 共享内存连接状态
        """
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "frame_rate": self.frame_rate,
            "frame_interval_ms": self.frame_interval * 1000,
            "client_count": len(self.clients),
            "shm_connected": self.shm_radar is not None,
        }


# 使用示例
async def main():
    """主函数示例"""
    server = WebSocketBridgeServer(host="0.0.0.0", port=8502, frame_rate=60)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("[WebSocket] 收到中断信号")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
