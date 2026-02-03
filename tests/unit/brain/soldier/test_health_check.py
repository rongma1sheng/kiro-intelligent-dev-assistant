"""
Soldier健康检查单元测试 - Task 19.2

白皮书依据: 第十二章 12.1.3 Soldier热备切换

测试内容:
- 健康检查超时检测
- 失败计数器逻辑
- 健康状态查询
- 降级触发机制
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

# 导入Soldier引擎和相关类型
from src.brain.soldier_engine_v2 import (
    SoldierEngineV2,
    SoldierMode,
    SoldierConfig,
    SoldierDecision
)
from src.brain.llm_local_inference import InferenceResult, ModelStatus


@pytest.fixture
def soldier_config():
    """测试配置"""
    return SoldierConfig(
        local_inference_timeout=0.02,  # 20ms
        failure_threshold=3,
        recovery_check_interval=0.1  # 100ms for faster testing
    )


@pytest.fixture
def soldier_engine(soldier_config):
    """Soldier引擎fixture"""
    engine = SoldierEngineV2(config=soldier_config)
    
    # Mock事件总线
    engine.event_bus = AsyncMock()
    
    # Mock LLM推理引擎
    engine.llm_inference = AsyncMock()
    engine.llm_inference.status = ModelStatus.READY
    
    return engine


class TestHealthCheckBasics:
    """基础健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_health_check_initialization(self, soldier_engine):
        """测试健康检查初始化"""
        # 启动健康检查
        await soldier_engine._start_health_check()
        
        # 验证任务已创建
        assert soldier_engine.health_check_task is not None
        assert not soldier_engine.health_check_task.done()
        
        # 清理
        await soldier_engine.stop_health_check()
    
    @pytest.mark.asyncio
    async def test_health_check_prevents_duplicate_start(self, soldier_engine):
        """测试防止重复启动健康检查"""
        # 第一次启动
        await soldier_engine._start_health_check()
        first_task = soldier_engine.health_check_task
        
        # 第二次启动（应该被忽略）
        await soldier_engine._start_health_check()
        second_task = soldier_engine.health_check_task
        
        # 验证是同一个任务
        assert first_task is second_task
        
        # 清理
        await soldier_engine.stop_health_check()
    
    @pytest.mark.asyncio
    async def test_health_check_stop(self, soldier_engine):
        """测试停止健康检查"""
        # 启动健康检查
        await soldier_engine._start_health_check()
        assert not soldier_engine.health_check_task.done()
        
        # 停止健康检查
        await soldier_engine.stop_health_check()
        
        # 验证任务已取消
        assert soldier_engine.health_check_task.done()


class TestHealthCheckLogic:
    """健康检查逻辑测试"""
    
    @pytest.mark.asyncio
    async def test_check_local_model_health_success(self, soldier_engine):
        """测试本地模型健康检查成功"""
        # Mock推理成功
        soldier_engine.llm_inference.infer.return_value = InferenceResult(
            text="test",
            tokens=10,
            latency_ms=15.0,  # 15ms < 20ms threshold
            cached=False,
            metadata={}
        )
        
        # 执行健康检查
        is_healthy = await soldier_engine._check_local_model_health()
        
        # 验证结果
        assert is_healthy is True
        
        # 验证调用参数
        soldier_engine.llm_inference.infer.assert_called_once()
        call_kwargs = soldier_engine.llm_inference.infer.call_args.kwargs
        assert call_kwargs['max_tokens'] == 10
        assert call_kwargs['use_cache'] is False
    
    @pytest.mark.asyncio
    async def test_check_local_model_health_timeout(self, soldier_engine):
        """测试本地模型健康检查超时"""
        # Mock推理超时
        async def slow_infer(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms > 20ms threshold
            return InferenceResult(
                text="test",
                tokens=10,
                latency_ms=100.0,
                cached=False,
                metadata={}
            )
        
        soldier_engine.llm_inference.infer.side_effect = slow_infer
        
        # 执行健康检查
        is_healthy = await soldier_engine._check_local_model_health()
        
        # 验证结果
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_check_local_model_health_returns_none(self, soldier_engine):
        """测试本地模型健康检查返回None"""
        # Mock推理返回None
        soldier_engine.llm_inference.infer.return_value = None
        
        # 执行健康检查
        is_healthy = await soldier_engine._check_local_model_health()
        
        # 验证结果
        assert is_healthy is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
