#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化的AI大脑协调器测试 - 用于验证导入和基本功能
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.brain.ai_brain_coordinator import AIBrainCoordinator, BrainDecision
from src.core.dependency_container import DIContainer
from src.infra.event_bus import Event, EventBus, EventType, EventPriority
from src.brain.interfaces import IScholarEngine, ICommanderEngine, ISoldierEngine


class TestAIBrainCoordinatorSimple:
    """简化的AI大脑协调器测试"""

    @pytest.fixture
    def mock_event_bus(self):
        """Mock事件总线"""
        event_bus = MagicMock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        return event_bus

    @pytest.fixture
    def mock_container(self):
        """Mock依赖容器"""
        container = MagicMock(spec=DIContainer)
        container.is_registered = MagicMock(return_value=True)
        return container

    @pytest.fixture
    def coordinator(self, mock_event_bus, mock_container):
        """创建协调器实例"""
        return AIBrainCoordinator(mock_event_bus, mock_container)

    def test_coordinator_creation(self, coordinator):
        """测试协调器创建"""
        assert coordinator is not None
        assert coordinator.coordination_active is False
        assert len(coordinator.decision_history) == 0

    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, coordinator):
        """测试协调器初始化"""
        await coordinator.initialize()
        assert coordinator.coordination_active is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])