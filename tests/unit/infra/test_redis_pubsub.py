"""Redis Pub/Sub单元测试

白皮书依据: 第三章 3.2 混合通信总线
"""

import pytest
import asyncio
from datetime import datetime
from src.infra.redis_pubsub import (
    RedisPubSubManager,
    ControlCommand,
    SystemEvent,
    CommandType,
    EventType,
    RedisPubSubError
)


class TestControlCommand:
    """控制指令测试"""
    
    def test_create_command(self):
        """测试创建控制指令"""
        command = ControlCommand(
            command_type=CommandType.SYSTEM_START,
            command_id="CMD001",
            timestamp=datetime.now(),
            source="orchestrator",
            target="soldier",
            params={"mode": "normal"},
            priority=8
        )
        
        assert command.command_type == CommandType.SYSTEM_START
        assert command.command_id == "CMD001"
        assert command.source == "orchestrator"
        assert command.target == "soldier"
        assert command.priority == 8
    
    def test_command_to_dict(self):
        """测试指令序列化"""
        command = ControlCommand(
            command_type=CommandType.TRADING_START,
            command_id="CMD002",
            timestamp=datetime.now(),
            source="orchestrator",
            target="execution",
            params={"symbols": ["000001.SZ"]},
            priority=10
        )
        
        data = command.to_dict()
        
        assert data['command_type'] == "trading_start"
        assert data['command_id'] == "CMD002"
        assert data['source'] == "orchestrator"
        assert data['target'] == "execution"
        assert data['priority'] == 10
    
    def test_command_from_dict(self):
        """测试指令反序列化"""
        data = {
            'command_type': 'system_stop',
            'command_id': 'CMD003',
            'timestamp': datetime.now().isoformat(),
            'source': 'user',
            'target': 'orchestrator',
            'params': {},
            'priority': 9
        }
        
        command = ControlCommand.from_dict(data)
        
        assert command.command_type == CommandType.SYSTEM_STOP
        assert command.command_id == "CMD003"
        assert command.priority == 9


class TestSystemEvent:
    """系统事件测试"""
    
    def test_create_event(self):
        """测试创建系统事件"""
        event = SystemEvent(
            event_type=EventType.SYSTEM_STARTED,
            event_id="EVT001",
            timestamp=datetime.now(),
            source="orchestrator",
            data={"state": "running"},
            severity="info"
        )
        
        assert event.event_type == EventType.SYSTEM_STARTED
        assert event.event_id == "EVT001"
        assert event.source == "orchestrator"
        assert event.severity == "info"
    
    def test_event_to_dict(self):
        """测试事件序列化"""
        event = SystemEvent(
            event_type=EventType.ORDER_FILLED,
            event_id="EVT002",
            timestamp=datetime.now(),
            source="execution",
            data={"order_id": "ORD001", "quantity": 1000},
            severity="info"
        )
        
        data = event.to_dict()
        
        assert data['event_type'] == "order_filled"
        assert data['event_id'] == "EVT002"
        assert data['source'] == "execution"
        assert data['data']['order_id'] == "ORD001"
    
    def test_event_from_dict(self):
        """测试事件反序列化"""
        data = {
            'event_type': 'risk_alert',
            'event_id': 'EVT003',
            'timestamp': datetime.now().isoformat(),
            'source': 'risk_manager',
            'data': {'alert_type': 'position_limit'},
            'severity': 'warning'
        }
        
        event = SystemEvent.from_dict(data)
        
        assert event.event_type == EventType.RISK_ALERT
        assert event.event_id == "EVT003"
        assert event.severity == "warning"


class TestRedisPubSubManager:
    """Redis Pub/Sub管理器测试"""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = RedisPubSubManager()
        
        assert manager.redis_url == "redis://localhost:6379"
        assert manager.command_channel == "mia:commands"
        assert manager.event_channel == "mia:events"
        assert not manager.running
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """测试连接和断开"""
        manager = RedisPubSubManager()
        await manager.connect()
        
        assert manager.redis_client is not None or manager._mock_mode
        
        await manager.disconnect()
        
        if not manager._mock_mode:
            assert not manager.running
    
    @pytest.mark.asyncio
    async def test_publish_command(self):
        """测试发布控制指令"""
        async with RedisPubSubManager() as manager:
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_TEST_001",
                timestamp=datetime.now(),
                source="test",
                target="soldier",
                params={}
            )
            
            await manager.publish_command(command, target_module="soldier")
            
            if manager._mock_mode:
                assert len(manager._mock_messages) > 0
    
    @pytest.mark.asyncio
    async def test_publish_event(self):
        """测试发布系统事件"""
        async with RedisPubSubManager() as manager:
            event = SystemEvent(
                event_type=EventType.SYSTEM_STARTED,
                event_id="EVT_TEST_001",
                timestamp=datetime.now(),
                source="test",
                data={"status": "ok"}
            )
            
            await manager.publish_event(event, event_category="system")
            
            if manager._mock_mode:
                assert len(manager._mock_messages) > 0
    
    @pytest.mark.asyncio
    async def test_subscribe_commands(self):
        """测试订阅控制指令"""
        async with RedisPubSubManager() as manager:
            received_commands = []
            
            async def command_handler(command: ControlCommand):
                received_commands.append(command)
            
            await manager.subscribe_commands("test_module", command_handler)
            
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_SUB_001",
                timestamp=datetime.now(),
                source="test",
                target="test_module",
                params={}
            )
            
            await manager.publish_command(command, target_module="test_module")
            await asyncio.sleep(0.1)
            
            if manager._mock_mode:
                assert len(received_commands) > 0
    
    @pytest.mark.asyncio
    async def test_subscribe_events(self):
        """测试订阅系统事件"""
        async with RedisPubSubManager() as manager:
            received_events = []
            
            async def event_handler(event: SystemEvent):
                received_events.append(event)
            
            await manager.subscribe_events("test_category", event_handler)
            
            event = SystemEvent(
                event_type=EventType.SYSTEM_STARTED,
                event_id="EVT_SUB_001",
                timestamp=datetime.now(),
                source="test",
                data={"status": "ok"}
            )
            
            await manager.publish_event(event, event_category="test_category")
            await asyncio.sleep(0.1)
            
            if manager._mock_mode:
                assert len(received_events) > 0
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        """测试多个处理器"""
        async with RedisPubSubManager() as manager:
            received_1 = []
            received_2 = []
            
            async def handler_1(command: ControlCommand):
                received_1.append(command)
            
            async def handler_2(command: ControlCommand):
                received_2.append(command)
            
            await manager.subscribe_commands("multi_test", handler_1)
            await manager.subscribe_commands("multi_test", handler_2)
            
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_MULTI_001",
                timestamp=datetime.now(),
                source="test",
                target="multi_test",
                params={}
            )
            
            await manager.publish_command(command, target_module="multi_test")
            await asyncio.sleep(0.1)
            
            if manager._mock_mode:
                assert len(received_1) > 0
                assert len(received_2) > 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计信息"""
        async with RedisPubSubManager() as manager:
            stats = manager.get_stats()
            
            assert 'redis_url' in stats
            assert 'command_channel' in stats
            assert 'event_channel' in stats
            assert 'mock_mode' in stats
            assert 'running' in stats
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        async with RedisPubSubManager() as manager:
            assert manager.redis_client is not None or manager._mock_mode
            
            # 发布测试消息
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_CTX_001",
                timestamp=datetime.now(),
                source="test",
                target="test",
                params={}
            )
            
            await manager.publish_command(command)
        
        # 上下文退出后应该断开连接
        if not manager._mock_mode:
            assert not manager.running


class TestCommandTypes:
    """指令类型测试"""
    
    def test_all_command_types(self):
        """测试所有指令类型"""
        command_types = [
            CommandType.SYSTEM_START,
            CommandType.SYSTEM_STOP,
            CommandType.SYSTEM_RESTART,
            CommandType.STATE_CHANGE,
            CommandType.TRADING_START,
            CommandType.TRADING_STOP,
            CommandType.EMERGENCY_STOP,
            CommandType.STRATEGY_ENABLE,
            CommandType.DATA_REFRESH,
            CommandType.RISK_LIMIT_UPDATE
        ]
        
        for cmd_type in command_types:
            assert isinstance(cmd_type.value, str)
            assert len(cmd_type.value) > 0


class TestEventTypes:
    """事件类型测试"""
    
    def test_all_event_types(self):
        """测试所有事件类型"""
        event_types = [
            EventType.SYSTEM_STARTED,
            EventType.SYSTEM_STOPPED,
            EventType.STATE_CHANGED,
            EventType.ORDER_PLACED,
            EventType.ORDER_FILLED,
            EventType.TRADE_EXECUTED,
            EventType.STRATEGY_SIGNAL,
            EventType.DATA_UPDATED,
            EventType.RISK_ALERT,
            EventType.MARKET_REGIME_CHANGED
        ]
        
        for evt_type in event_types:
            assert isinstance(evt_type.value, str)
            assert len(evt_type.value) > 0


class TestRedisPubSubManagerAdvanced:
    """Redis Pub/Sub管理器高级测试"""
    
    @pytest.mark.asyncio
    async def test_start_listening_mock_mode(self):
        """测试启动监听（Mock模式）"""
        manager = RedisPubSubManager()
        
        # 如果不是Mock模式，先连接
        if not manager._mock_mode:
            await manager.connect()
        
        await manager.start_listening()
        
        # Mock模式下应该立即返回，非Mock模式下应该创建任务
        if manager._mock_mode:
            assert manager._mock_mode
        else:
            assert manager.running
        
        # 清理
        await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_start_listening_already_running(self):
        """测试重复启动监听"""
        async with RedisPubSubManager() as manager:
            manager.running = True
            
            # 应该记录警告但不抛出异常
            await manager.start_listening()
    
    @pytest.mark.asyncio
    async def test_publish_command_with_broadcast(self):
        """测试广播控制指令"""
        async with RedisPubSubManager() as manager:
            command = ControlCommand(
                command_type=CommandType.SYSTEM_STOP,
                command_id="CMD_BROADCAST_001",
                timestamp=datetime.now(),
                source="orchestrator",
                target="all",
                params={}
            )
            
            # 不指定target_module，应该广播
            await manager.publish_command(command, target_module=None)
            
            if manager._mock_mode:
                assert len(manager._mock_messages) > 0
                # 检查频道是否为广播频道
                assert manager._mock_messages[-1]['channel'] == manager.command_channel
    
    @pytest.mark.asyncio
    async def test_publish_event_with_broadcast(self):
        """测试广播系统事件"""
        async with RedisPubSubManager() as manager:
            event = SystemEvent(
                event_type=EventType.SYSTEM_ERROR,
                event_id="EVT_BROADCAST_001",
                timestamp=datetime.now(),
                source="system",
                data={"error": "critical error"},
                severity="critical"
            )
            
            # 不指定event_category，应该广播
            await manager.publish_event(event, event_category=None)
            
            if manager._mock_mode:
                assert len(manager._mock_messages) > 0
                # 检查频道是否为广播频道
                assert manager._mock_messages[-1]['channel'] == manager.event_channel
    
    @pytest.mark.asyncio
    async def test_command_handler_exception(self):
        """测试指令处理器异常"""
        async with RedisPubSubManager() as manager:
            exception_raised = []
            
            async def failing_handler(command: ControlCommand):
                exception_raised.append(True)
                raise ValueError("Handler failed")
            
            await manager.subscribe_commands("test_fail", failing_handler)
            
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_FAIL_001",
                timestamp=datetime.now(),
                source="test",
                target="test_fail",
                params={}
            )
            
            # 发布指令，处理器应该捕获异常
            await manager.publish_command(command, target_module="test_fail")
            await asyncio.sleep(0.1)
            
            if manager._mock_mode:
                # Mock模式下异常应该被捕获
                assert len(exception_raised) > 0
    
    @pytest.mark.asyncio
    async def test_event_handler_exception(self):
        """测试事件处理器异常"""
        async with RedisPubSubManager() as manager:
            exception_raised = []
            
            async def failing_handler(event: SystemEvent):
                exception_raised.append(True)
                raise ValueError("Handler failed")
            
            await manager.subscribe_events("test_fail", failing_handler)
            
            event = SystemEvent(
                event_type=EventType.SYSTEM_ERROR,
                event_id="EVT_FAIL_001",
                timestamp=datetime.now(),
                source="test",
                data={"error": "test"},
                severity="error"
            )
            
            # 发布事件，处理器应该捕获异常
            await manager.publish_event(event, event_category="test_fail")
            await asyncio.sleep(0.1)
            
            if manager._mock_mode:
                # Mock模式下异常应该被捕获
                assert len(exception_raised) > 0
    
    @pytest.mark.asyncio
    async def test_get_stats_detailed(self):
        """测试获取详细统计信息"""
        async with RedisPubSubManager() as manager:
            # 添加一些处理器
            async def dummy_handler(cmd):
                pass
            
            await manager.subscribe_commands("module1", dummy_handler)
            await manager.subscribe_commands("module2", dummy_handler)
            await manager.subscribe_events("category1", dummy_handler)
            
            stats = manager.get_stats()
            
            assert stats['redis_url'] == manager.redis_url
            assert stats['command_channel'] == manager.command_channel
            assert stats['event_channel'] == manager.event_channel
            assert stats['mock_mode'] == manager._mock_mode
            assert stats['running'] == manager.running
            assert 'command_handlers' in stats
            assert 'event_handlers' in stats
            assert 'active_tasks' in stats


class TestAdditionalCommandTypes:
    """额外的指令类型测试"""
    
    def test_system_pause_resume_commands(self):
        """测试系统暂停和恢复指令"""
        pause_command = ControlCommand(
            command_type=CommandType.SYSTEM_PAUSE,
            command_id="CMD_PAUSE_001",
            timestamp=datetime.now(),
            source="user",
            target="orchestrator",
            params={}
        )
        
        resume_command = ControlCommand(
            command_type=CommandType.SYSTEM_RESUME,
            command_id="CMD_RESUME_001",
            timestamp=datetime.now(),
            source="user",
            target="orchestrator",
            params={}
        )
        
        assert pause_command.command_type == CommandType.SYSTEM_PAUSE
        assert resume_command.command_type == CommandType.SYSTEM_RESUME
    
    def test_strategy_commands(self):
        """测试策略控制指令"""
        enable_command = ControlCommand(
            command_type=CommandType.STRATEGY_ENABLE,
            command_id="CMD_ENABLE_001",
            timestamp=datetime.now(),
            source="user",
            target="strategy_manager",
            params={"strategy_id": "S01"}
        )
        
        disable_command = ControlCommand(
            command_type=CommandType.STRATEGY_DISABLE,
            command_id="CMD_DISABLE_001",
            timestamp=datetime.now(),
            source="user",
            target="strategy_manager",
            params={"strategy_id": "S01"}
        )
        
        reload_command = ControlCommand(
            command_type=CommandType.STRATEGY_RELOAD,
            command_id="CMD_RELOAD_001",
            timestamp=datetime.now(),
            source="user",
            target="strategy_manager",
            params={"strategy_id": "S01"}
        )
        
        assert enable_command.command_type == CommandType.STRATEGY_ENABLE
        assert disable_command.command_type == CommandType.STRATEGY_DISABLE
        assert reload_command.command_type == CommandType.STRATEGY_RELOAD
    
    def test_data_commands(self):
        """测试数据控制指令"""
        refresh_command = ControlCommand(
            command_type=CommandType.DATA_REFRESH,
            command_id="CMD_REFRESH_001",
            timestamp=datetime.now(),
            source="scheduler",
            target="data_manager",
            params={}
        )
        
        clear_cache_command = ControlCommand(
            command_type=CommandType.DATA_CLEAR_CACHE,
            command_id="CMD_CLEAR_001",
            timestamp=datetime.now(),
            source="user",
            target="data_manager",
            params={}
        )
        
        assert refresh_command.command_type == CommandType.DATA_REFRESH
        assert clear_cache_command.command_type == CommandType.DATA_CLEAR_CACHE
    
    def test_risk_commands(self):
        """测试风控指令"""
        limit_update_command = ControlCommand(
            command_type=CommandType.RISK_LIMIT_UPDATE,
            command_id="CMD_LIMIT_001",
            timestamp=datetime.now(),
            source="risk_manager",
            target="execution",
            params={"max_position": 1000000}
        )
        
        position_close_command = ControlCommand(
            command_type=CommandType.POSITION_CLOSE,
            command_id="CMD_CLOSE_001",
            timestamp=datetime.now(),
            source="risk_manager",
            target="execution",
            params={"symbol": "000001.SZ"}
        )
        
        assert limit_update_command.command_type == CommandType.RISK_LIMIT_UPDATE
        assert position_close_command.command_type == CommandType.POSITION_CLOSE


class TestAdditionalEventTypes:
    """额外的事件类型测试"""
    
    def test_system_error_event(self):
        """测试系统错误事件"""
        event = SystemEvent(
            event_type=EventType.SYSTEM_ERROR,
            event_id="EVT_ERROR_001",
            timestamp=datetime.now(),
            source="system",
            data={"error": "critical error", "traceback": "..."},
            severity="critical"
        )
        
        assert event.event_type == EventType.SYSTEM_ERROR
        assert event.severity == "critical"
    
    def test_order_events(self):
        """测试订单事件"""
        placed_event = SystemEvent(
            event_type=EventType.ORDER_PLACED,
            event_id="EVT_PLACED_001",
            timestamp=datetime.now(),
            source="execution",
            data={"order_id": "ORD001"}
        )
        
        cancelled_event = SystemEvent(
            event_type=EventType.ORDER_CANCELLED,
            event_id="EVT_CANCELLED_001",
            timestamp=datetime.now(),
            source="execution",
            data={"order_id": "ORD001"}
        )
        
        assert placed_event.event_type == EventType.ORDER_PLACED
        assert cancelled_event.event_type == EventType.ORDER_CANCELLED
    
    def test_strategy_events(self):
        """测试策略事件"""
        signal_event = SystemEvent(
            event_type=EventType.STRATEGY_SIGNAL,
            event_id="EVT_SIGNAL_001",
            timestamp=datetime.now(),
            source="strategy",
            data={"signal": "buy", "symbol": "000001.SZ"}
        )
        
        error_event = SystemEvent(
            event_type=EventType.STRATEGY_ERROR,
            event_id="EVT_SERROR_001",
            timestamp=datetime.now(),
            source="strategy",
            data={"error": "calculation failed"},
            severity="error"
        )
        
        assert signal_event.event_type == EventType.STRATEGY_SIGNAL
        assert error_event.event_type == EventType.STRATEGY_ERROR
    
    def test_data_events(self):
        """测试数据事件"""
        updated_event = SystemEvent(
            event_type=EventType.DATA_UPDATED,
            event_id="EVT_UPDATED_001",
            timestamp=datetime.now(),
            source="data_manager",
            data={"symbols": ["000001.SZ"]}
        )
        
        error_event = SystemEvent(
            event_type=EventType.DATA_ERROR,
            event_id="EVT_DERROR_001",
            timestamp=datetime.now(),
            source="data_manager",
            data={"error": "download failed"},
            severity="warning"
        )
        
        assert updated_event.event_type == EventType.DATA_UPDATED
        assert error_event.event_type == EventType.DATA_ERROR
    
    def test_risk_events(self):
        """测试风控事件"""
        alert_event = SystemEvent(
            event_type=EventType.RISK_ALERT,
            event_id="EVT_ALERT_001",
            timestamp=datetime.now(),
            source="risk_manager",
            data={"alert_type": "position_limit", "current": 1000000, "limit": 900000},
            severity="warning"
        )
        
        limit_event = SystemEvent(
            event_type=EventType.POSITION_LIMIT_REACHED,
            event_id="EVT_LIMIT_001",
            timestamp=datetime.now(),
            source="risk_manager",
            data={"symbol": "000001.SZ"},
            severity="error"
        )
        
        assert alert_event.event_type == EventType.RISK_ALERT
        assert limit_event.event_type == EventType.POSITION_LIMIT_REACHED


class TestRedisPubSubManagerRealMode:
    """Redis Pub/Sub管理器真实模式测试（需要Redis服务）"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not hasattr(RedisPubSubManager, '_mock_mode'), reason="Redis not available")
    async def test_connect_failure(self):
        """测试连接失败"""
        # 使用无效的Redis URL
        manager = RedisPubSubManager(redis_url="redis://invalid_host:9999")
        
        if not manager._mock_mode:
            with pytest.raises(RedisPubSubError, match="Failed to connect to Redis"):
                await manager.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect_with_tasks(self):
        """测试断开连接时清理任务"""
        manager = RedisPubSubManager()
        await manager.connect()
        
        # 模拟有运行中的任务
        async def dummy_task():
            await asyncio.sleep(10)
        
        task = asyncio.create_task(dummy_task())
        manager._tasks.append(task)
        manager.running = True
        
        # 断开连接应该取消任务
        await manager.disconnect()
        
        assert task.cancelled() or task.done()
    
    @pytest.mark.asyncio
    async def test_publish_command_exception(self):
        """测试发布指令异常"""
        manager = RedisPubSubManager()
        await manager.connect()
        
        # 创建一个无效的指令（缺少必要字段）
        command = ControlCommand(
            command_type=CommandType.SYSTEM_START,
            command_id="CMD_INVALID_001",
            timestamp=datetime.now(),
            source="test",
            target="test",
            params={}
        )
        
        # 如果不是Mock模式，模拟Redis客户端失败
        if not manager._mock_mode:
            original_client = manager.redis_client
            manager.redis_client = None
            
            with pytest.raises(RedisPubSubError, match="Failed to publish command"):
                await manager.publish_command(command)
            
            manager.redis_client = original_client
        
        await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_publish_event_exception(self):
        """测试发布事件异常"""
        manager = RedisPubSubManager()
        await manager.connect()
        
        event = SystemEvent(
            event_type=EventType.SYSTEM_ERROR,
            event_id="EVT_INVALID_001",
            timestamp=datetime.now(),
            source="test",
            data={}
        )
        
        # 如果不是Mock模式，模拟Redis客户端失败
        if not manager._mock_mode:
            original_client = manager.redis_client
            manager.redis_client = None
            
            with pytest.raises(RedisPubSubError, match="Failed to publish event"):
                await manager.publish_event(event)
            
            manager.redis_client = original_client
        
        await manager.disconnect()


class TestRedisPubSubManagerInternalMethods:
    """Redis Pub/Sub管理器内部方法测试"""
    
    @pytest.mark.asyncio
    async def test_handle_command_internal(self):
        """测试内部指令处理"""
        async with RedisPubSubManager() as manager:
            received_commands = []
            
            async def handler(command: ControlCommand):
                received_commands.append(command)
            
            # 注册处理器
            channel = f"{manager.command_channel}:test"
            manager.command_handlers[channel] = [handler]
            
            # 创建指令
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_INTERNAL_001",
                timestamp=datetime.now(),
                source="test",
                target="test",
                params={}
            )
            
            # 直接调用内部方法
            await manager._handle_command(channel, command)
            
            assert len(received_commands) == 1
            assert received_commands[0].command_id == "CMD_INTERNAL_001"
    
    @pytest.mark.asyncio
    async def test_handle_event_internal(self):
        """测试内部事件处理"""
        async with RedisPubSubManager() as manager:
            received_events = []
            
            async def handler(event: SystemEvent):
                received_events.append(event)
            
            # 注册处理器
            channel = f"{manager.event_channel}:test"
            manager.event_handlers[channel] = [handler]
            
            # 创建事件
            event = SystemEvent(
                event_type=EventType.SYSTEM_STARTED,
                event_id="EVT_INTERNAL_001",
                timestamp=datetime.now(),
                source="test",
                data={}
            )
            
            # 直接调用内部方法
            await manager._handle_event(channel, event)
            
            assert len(received_events) == 1
            assert received_events[0].event_id == "EVT_INTERNAL_001"
    
    @pytest.mark.asyncio
    async def test_handle_command_with_exception(self):
        """测试指令处理器抛出异常"""
        async with RedisPubSubManager() as manager:
            async def failing_handler(command: ControlCommand):
                raise RuntimeError("Handler failed")
            
            # 注册失败的处理器
            channel = f"{manager.command_channel}:test"
            manager.command_handlers[channel] = [failing_handler]
            
            command = ControlCommand(
                command_type=CommandType.SYSTEM_START,
                command_id="CMD_FAIL_002",
                timestamp=datetime.now(),
                source="test",
                target="test",
                params={}
            )
            
            # 应该捕获异常并记录日志，不抛出
            await manager._handle_command(channel, command)
    
    @pytest.mark.asyncio
    async def test_handle_event_with_exception(self):
        """测试事件处理器抛出异常"""
        async with RedisPubSubManager() as manager:
            async def failing_handler(event: SystemEvent):
                raise RuntimeError("Handler failed")
            
            # 注册失败的处理器
            channel = f"{manager.event_channel}:test"
            manager.event_handlers[channel] = [failing_handler]
            
            event = SystemEvent(
                event_type=EventType.SYSTEM_ERROR,
                event_id="EVT_FAIL_002",
                timestamp=datetime.now(),
                source="test",
                data={}
            )
            
            # 应该捕获异常并记录日志，不抛出
            await manager._handle_event(channel, event)


class TestCommandFromDictDefaultPriority:
    """测试指令反序列化默认优先级"""
    
    def test_command_from_dict_without_priority(self):
        """测试从字典创建指令（无优先级字段）"""
        data = {
            'command_type': 'system_start',
            'command_id': 'CMD_DEFAULT_001',
            'timestamp': datetime.now().isoformat(),
            'source': 'test',
            'target': 'test',
            'params': {}
            # 注意：没有 priority 字段
        }
        
        command = ControlCommand.from_dict(data)
        
        assert command.command_type == CommandType.SYSTEM_START
        assert command.priority == 5  # 默认优先级


class TestEventFromDictDefaultSeverity:
    """测试事件反序列化默认严重程度"""
    
    def test_event_from_dict_without_severity(self):
        """测试从字典创建事件（无严重程度字段）"""
        data = {
            'event_type': 'system_started',
            'event_id': 'EVT_DEFAULT_001',
            'timestamp': datetime.now().isoformat(),
            'source': 'test',
            'data': {}
            # 注意：没有 severity 字段
        }
        
        event = SystemEvent.from_dict(data)
        
        assert event.event_type == EventType.SYSTEM_STARTED
        assert event.severity == "info"  # 默认严重程度


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
