"""Unit tests for WebSocketBridgeServer

白皮书依据: 第十五章 15.2 WebSocket侧通道推流

测试覆盖:
- 服务器初始化
- 客户端连接处理
- 雷达数据读取
- 60Hz推流
- 服务器停止
"""

import pytest
import asyncio
import msgpack
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from multiprocessing import shared_memory
from src.infra.websocket_bridge_server import WebSocketBridgeServer


class TestWebSocketBridgeServer:
    """WebSocketBridgeServer单元测试"""
    
    # 初始化测试
    def test_init_success(self):
        """测试正常初始化"""
        server = WebSocketBridgeServer(
            host='127.0.0.1',
            port=8502,
            frame_rate=60
        )
        
        assert server.host == '127.0.0.1'
        assert server.port == 8502
        assert server.frame_rate == 60
        assert server.frame_interval == pytest.approx(1.0 / 60, rel=1e-6)
        assert server.clients == set()
        assert server.running is False
        assert server.shm_radar is None
    
    def test_init_default_values(self):
        """测试默认值"""
        server = WebSocketBridgeServer()
        
        assert server.host == '0.0.0.0'
        assert server.port == 8502
        assert server.frame_rate == 60
    
    def test_init_invalid_frame_rate(self):
        """测试无效的帧率"""
        with pytest.raises(ValueError, match="帧率必须 > 0"):
            WebSocketBridgeServer(frame_rate=0)
        
        with pytest.raises(ValueError, match="帧率必须 > 0"):
            WebSocketBridgeServer(frame_rate=-10)
    
    def test_init_custom_frame_rate(self):
        """测试自定义帧率"""
        server = WebSocketBridgeServer(frame_rate=30)
        
        assert server.frame_rate == 30
        assert server.frame_interval == pytest.approx(1.0 / 30, rel=1e-6)
    
    # 客户端连接处理测试
    @pytest.mark.asyncio
    async def test_handle_client_connection(self):
        """测试客户端连接"""
        server = WebSocketBridgeServer()
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ('127.0.0.1', 12345)
        mock_websocket.wait_closed = AsyncMock()
        
        # 处理客户端连接
        await server.handle_client(mock_websocket, '/radar')
        
        # 验证客户端已被移除（连接结束后）
        assert mock_websocket not in server.clients
    
    @pytest.mark.asyncio
    async def test_handle_client_exception(self):
        """测试客户端连接异常"""
        server = WebSocketBridgeServer()
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ('127.0.0.1', 12345)
        mock_websocket.wait_closed = AsyncMock(
            side_effect=Exception("Connection error")
        )
        
        # 处理客户端连接（不应抛出异常）
        await server.handle_client(mock_websocket, '/radar')
        
        # 验证客户端已被移除
        assert mock_websocket not in server.clients
    
    # 雷达数据读取测试
    def test_read_radar_data_success(self):
        """测试成功读取雷达数据"""
        server = WebSocketBridgeServer()
        
        # Mock共享内存
        mock_shm = Mock()
        radar_data = {
            'probabilities': [0.8, 0.6, 0.4],
            'symbols': ['600519', '000001', '000002'],
            'timestamp': '2024-01-01T10:00:00'
        }
        packed_data = msgpack.packb(radar_data)
        # 创建1024字节的缓冲区，只在开头放置打包的数据
        buffer = bytearray(1024)
        buffer[:len(packed_data)] = packed_data
        mock_shm.buf = buffer
        
        server.shm_radar = mock_shm
        
        # 读取数据
        result = server._read_radar_data()
        
        assert result is not None
        assert result['probabilities'] == [0.8, 0.6, 0.4]
        assert result['symbols'] == ['600519', '000001', '000002']
    
    def test_read_radar_data_shm_not_initialized(self):
        """测试共享内存未初始化"""
        server = WebSocketBridgeServer()
        
        result = server._read_radar_data()
        
        assert result is None
    
    def test_read_radar_data_exception(self):
        """测试读取异常"""
        server = WebSocketBridgeServer()
        
        # Mock共享内存抛出异常
        mock_shm = Mock()
        mock_shm.buf = Mock(side_effect=Exception("Read error"))
        server.shm_radar = mock_shm
        
        result = server._read_radar_data()
        
        assert result is None
    
    # 广播测试
    @pytest.mark.asyncio
    async def test_broadcast_to_clients_success(self):
        """测试成功广播"""
        server = WebSocketBridgeServer()
        
        # Mock客户端
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        server.clients = {mock_client1, mock_client2}
        
        # 广播数据
        test_data = b'test_data'
        await server._broadcast_to_clients(test_data)
        
        # 验证发送
        mock_client1.send.assert_called_once_with(test_data)
        mock_client2.send.assert_called_once_with(test_data)
    
    @pytest.mark.asyncio
    async def test_broadcast_to_clients_no_clients(self):
        """测试无客户端时广播"""
        server = WebSocketBridgeServer()
        
        # 广播数据（不应抛出异常）
        await server._broadcast_to_clients(b'test_data')
    
    @pytest.mark.asyncio
    async def test_broadcast_to_clients_partial_failure(self):
        """测试部分客户端发送失败"""
        server = WebSocketBridgeServer()
        
        # Mock客户端
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client2.send = AsyncMock(side_effect=Exception("Send error"))
        server.clients = {mock_client1, mock_client2}
        
        # 广播数据（不应抛出异常）
        await server._broadcast_to_clients(b'test_data')
        
        # 验证成功的客户端收到数据
        mock_client1.send.assert_called_once()
    
    # 服务器停止测试
    @pytest.mark.asyncio
    async def test_stop_success(self):
        """测试成功停止服务器"""
        server = WebSocketBridgeServer()
        server.running = True
        
        # Mock客户端
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        server.clients = {mock_client1, mock_client2}
        
        # Mock共享内存
        mock_shm = Mock()
        server.shm_radar = mock_shm
        
        # 停止服务器
        await server.stop()
        
        # 验证状态
        assert server.running is False
        assert len(server.clients) == 0
        
        # 验证客户端关闭
        mock_client1.close.assert_called_once()
        mock_client2.close.assert_called_once()
        
        # 验证共享内存关闭
        mock_shm.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_no_clients(self):
        """测试无客户端时停止"""
        server = WebSocketBridgeServer()
        server.running = True
        
        # 停止服务器（不应抛出异常）
        await server.stop()
        
        assert server.running is False
    
    @pytest.mark.asyncio
    async def test_stop_shm_close_exception(self):
        """测试共享内存关闭异常"""
        server = WebSocketBridgeServer()
        server.running = True
        
        # Mock共享内存抛出异常
        mock_shm = Mock()
        mock_shm.close = Mock(side_effect=Exception("Close error"))
        server.shm_radar = mock_shm
        
        # 停止服务器（不应抛出异常）
        await server.stop()
        
        assert server.running is False
    
    # 状态查询测试
    def test_get_status(self):
        """测试获取服务器状态"""
        server = WebSocketBridgeServer(
            host='127.0.0.1',
            port=8502,
            frame_rate=60
        )
        server.running = True
        
        # Mock客户端
        mock_client1 = Mock()
        mock_client2 = Mock()
        server.clients = {mock_client1, mock_client2}
        
        # Mock共享内存
        server.shm_radar = Mock()
        
        # 获取状态
        status = server.get_status()
        
        assert status['running'] is True
        assert status['host'] == '127.0.0.1'
        assert status['port'] == 8502
        assert status['frame_rate'] == 60
        assert status['frame_interval_ms'] == pytest.approx(16.67, rel=0.01)
        assert status['client_count'] == 2
        assert status['shm_connected'] is True
    
    def test_get_status_not_running(self):
        """测试未运行时的状态"""
        server = WebSocketBridgeServer()
        
        status = server.get_status()
        
        assert status['running'] is False
        assert status['client_count'] == 0
        assert status['shm_connected'] is False
    
    # 帧率计算测试
    def test_frame_interval_calculation(self):
        """测试帧间隔计算"""
        # 60Hz
        server = WebSocketBridgeServer(frame_rate=60)
        assert server.frame_interval == pytest.approx(0.01667, rel=1e-3)
        
        # 30Hz
        server = WebSocketBridgeServer(frame_rate=30)
        assert server.frame_interval == pytest.approx(0.03333, rel=1e-3)
        
        # 120Hz
        server = WebSocketBridgeServer(frame_rate=120)
        assert server.frame_interval == pytest.approx(0.00833, rel=1e-3)
    
    # 边界条件测试
    def test_high_frame_rate(self):
        """测试高帧率"""
        server = WebSocketBridgeServer(frame_rate=240)
        
        assert server.frame_rate == 240
        assert server.frame_interval == pytest.approx(1.0 / 240, rel=1e-6)
    
    def test_low_frame_rate(self):
        """测试低帧率"""
        server = WebSocketBridgeServer(frame_rate=1)
        
        assert server.frame_rate == 1
        assert server.frame_interval == 1.0
    
    # 集成测试场景
    @pytest.mark.asyncio
    async def test_client_lifecycle(self):
        """测试客户端完整生命周期"""
        server = WebSocketBridgeServer()
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ('127.0.0.1', 12345)
        
        # 模拟连接保持一段时间后断开
        async def wait_and_close():
            await asyncio.sleep(0.1)
        
        mock_websocket.wait_closed = wait_and_close
        
        # 处理客户端
        await server.handle_client(mock_websocket, '/radar')
        
        # 验证客户端已被移除
        assert mock_websocket not in server.clients
    
    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """测试多客户端场景"""
        server = WebSocketBridgeServer()
        
        # Mock多个客户端
        clients = []
        for i in range(5):
            mock_client = AsyncMock()
            mock_client.remote_address = ('127.0.0.1', 10000 + i)
            clients.append(mock_client)
        
        # 添加到服务器
        server.clients = set(clients)
        
        # 广播数据
        test_data = b'test_data'
        await server._broadcast_to_clients(test_data)
        
        # 验证所有客户端收到数据
        for client in clients:
            client.send.assert_called_once_with(test_data)
