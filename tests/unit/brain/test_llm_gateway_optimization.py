"""
LLM网关优化功能单元测试

白皮书依据: 第七章 7.6 LLM调用优化
需求: 7.6 - 超时控制、重试机制、并发限制
测试覆盖: Task 14.5, Task 14.6

测试内容:
1. 超时控制测试
2. 重试机制测试（指数退避）
3. 并发限制测试
4. vLLM集成效果测试
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.brain.llm_gateway import (
    LLMGateway,
    LLMRequest,
    LLMResponse,
    LLMProvider,
    CallType
)
from src.base.exceptions import ValidationError, ResourceError


class TestTimeoutControl:
    """测试超时控制
    
    白皮书依据: 第七章 7.6 LLM调用优化
    需求: 7.6 - 超时控制
    """
    
    @pytest.fixture
    def gateway(self):
        """创建LLM网关实例"""
        with patch('redis.Redis'):
            gateway = LLMGateway()
            return gateway
    
    @pytest.mark.asyncio
    async def test_timeout_triggers_correctly(self, gateway):
        """测试超时正确触发
        
        验证: 当调用超过timeout时间时，应该触发超时
        """
        # 创建一个会超时的请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{"role": "user", "content": "测试超时"}],
            timeout=0.1,  # 100ms超时
            caller_module="test",
            caller_function="test_timeout"
        )
        
        # Mock一个慢速的LLM调用
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms延迟
            return LLMResponse(
                call_id=request.call_id,
                success=True,
                content="不应该返回这个"
            )
        
        gateway._execute_call_internal = slow_call
        
        # 执行调用
        response = await gateway.call_llm(request)
        
        # 验证超时
        assert not response.success
        assert "超时" in response.error_message or "MAX_RETRIES_EXCEEDED" in response.error_code
        assert gateway.call_stats['timeouts'] > 0
    
    @pytest.mark.asyncio
    async def test_timeout_does_not_trigger_for_fast_calls(self, gateway):
        """测试快速调用不会超时
        
        验证: 当调用在timeout时间内完成时，不应该触发超时
        """
        # 创建一个正常的请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{"role": "user", "content": "测试正常"}],
            timeout=5.0,  # 5秒超时
            caller_module="test",
            caller_function="test_normal"
        )
        
        # Mock一个快速的LLM调用
        async def fast_call(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms延迟
            return LLMResponse(
                call_id=request.call_id,
                success=True,
                content="正常响应"
            )
        
        gateway._execute_call_internal = fast_call
        
        # 执行调用
        response = await gateway.call_llm(request)
        
        # 验证成功
        assert response.success
        assert response.content == "正常响应"
        assert gateway.call_stats['timeouts'] == 0
    
    @pytest.mark.asyncio
    async def test_timeout_value_is_configurable(self, gateway):
        """测试超时值可配置
        
        验证: 不同的请求可以设置不同的超时值
        """
        # 短超时请求
        short_timeout_request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            messages=[{"role": "user", "content": "短超时"}],
            timeout=0.1,
            caller_module="test",
            caller_function="test_short"
        )
        
        # 长超时请求
        long_timeout_request = LLMRequest(
            call_type=CallType.STRATEGY_ANALYSIS,
            messages=[{"role": "user", "content": "长超时"}],
            timeout=10.0,
            caller_module="test",
            caller_function="test_long"
        )
        
        # 验证超时值
        assert short_timeout_request.timeout == 0.1
        assert long_timeout_request.timeout == 10.0


class TestRetryMechanism:
    """测试重试机制
    
    白皮书依据: 第七章 7.6 LLM调用优化
    需求: 7.6 - 重试机制（指数退避）
    """
    
    @pytest.fixture
    def gateway(self):
        """创建LLM网关实例"""
        with patch('redis.Redis'):
            gateway = LLMGateway()
            return gateway
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, gateway):
        """测试失败时重试
        
        验证: 当调用失败时，应该自动重试
        """
        # 创建请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            messages=[{"role": "user", "content": "测试重试"}],
            timeout=5.0,
            caller_module="test",
            caller_function="test_retry"
        )
        
        # Mock一个会失败的调用
        call_count = 0
        
        async def failing_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # 前2次失败
                raise Exception("模拟失败")
            else:
                # 第3次成功
                return LLMResponse(
                    call_id=request.call_id,
                    success=True,
                    content="重试成功"
                )
        
        gateway._execute_call_internal = failing_call
        
        # 执行调用
        response = await gateway.call_llm(request)
        
        # 验证重试
        assert call_count == 3  # 应该调用3次
        assert response.success
        assert response.content == "重试成功"
        assert gateway.call_stats['retries'] >= 2  # 至少重试2次
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, gateway):
        """测试指数退避
        
        验证: 重试延迟应该呈指数增长
        """
        # 创建请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            messages=[{"role": "user", "content": "测试指数退避"}],
            timeout=5.0,
            caller_module="test",
            caller_function="test_backoff"
        )
        
        # 记录重试时间
        retry_times = []
        
        async def failing_call(*args, **kwargs):
            retry_times.append(time.time())
            raise Exception("模拟失败")
        
        gateway._execute_call_internal = failing_call
        
        # 执行调用
        start_time = time.time()
        response = await gateway.call_llm(request)
        total_time = time.time() - start_time
        
        # 验证指数退避
        # 第1次重试: 等待1秒
        # 第2次重试: 等待2秒
        # 第3次重试: 等待4秒
        # 总等待时间应该约为7秒
        assert total_time >= 7.0  # 至少7秒
        assert total_time < 10.0  # 不超过10秒
        
        # 验证失败
        assert not response.success
        assert "MAX_RETRIES_EXCEEDED" in response.error_code
    
    @pytest.mark.asyncio
    async def test_max_retries_limit(self, gateway):
        """测试最大重试次数限制
        
        验证: 重试次数不应超过max_retries
        """
        # 创建请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            messages=[{"role": "user", "content": "测试最大重试"}],
            timeout=5.0,
            caller_module="test",
            caller_function="test_max_retries"
        )
        
        # Mock一个总是失败的调用
        call_count = 0
        
        async def always_failing_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("总是失败")
        
        gateway._execute_call_internal = always_failing_call
        
        # 执行调用
        response = await gateway.call_llm(request)
        
        # 验证最大重试次数
        assert call_count == gateway.max_retries + 1  # 初始调用 + 重试次数
        assert not response.success
        assert "MAX_RETRIES_EXCEEDED" in response.error_code
    
    @pytest.mark.asyncio
    async def test_no_retry_for_validation_errors(self, gateway):
        """测试验证错误不重试
        
        验证: 对于验证错误，不应该重试
        """
        # 创建请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            messages=[{"role": "user", "content": "测试验证错误"}],
            timeout=5.0,
            caller_module="test",
            caller_function="test_no_retry"
        )
        
        # Mock一个返回验证错误的调用
        call_count = 0
        
        async def validation_error_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                call_id=request.call_id,
                success=False,
                error_message="验证错误",
                error_code="VALIDATION_ERROR"
            )
        
        gateway._execute_call_internal = validation_error_call
        
        # 执行调用
        response = await gateway.call_llm(request)
        
        # 验证不重试
        assert call_count == 1  # 只调用1次
        assert not response.success
        assert response.error_code == "VALIDATION_ERROR"


class TestConcurrencyControl:
    """测试并发控制
    
    白皮书依据: 第七章 7.6 LLM调用优化
    需求: 7.6 - 并发限制（最大10个并发）
    """
    
    @pytest.fixture
    def gateway(self):
        """创建LLM网关实例"""
        with patch('redis.Redis'):
            gateway = LLMGateway()
            return gateway
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_enforced(self, gateway):
        """测试并发限制生效
        
        验证: 并发调用数不应超过max_concurrent_calls
        """
        # 创建多个请求
        requests = [
            LLMRequest(
                call_type=CallType.TRADING_DECISION,
                messages=[{"role": "user", "content": f"请求{i}"}],
                timeout=5.0,
                caller_module="test",
                caller_function=f"test_concurrent_{i}"
            )
            for i in range(20)  # 20个并发请求
        ]
        
        # 记录并发数
        max_concurrent = 0
        current_concurrent = 0
        
        async def slow_call(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            
            await asyncio.sleep(0.1)  # 模拟慢速调用
            
            current_concurrent -= 1
            
            return LLMResponse(
                call_id=args[0].call_id,
                success=True,
                content="并发响应"
            )
        
        gateway._execute_call_internal = slow_call
        
        # 并发执行所有请求
        responses = await asyncio.gather(*[gateway.call_llm(req) for req in requests])
        
        # 验证并发限制
        assert max_concurrent <= gateway.max_concurrent_calls
        assert len(responses) == 20
        assert all(r.success for r in responses)
    
    @pytest.mark.asyncio
    async def test_concurrent_limit_statistics(self, gateway):
        """测试并发限制统计
        
        验证: 应该正确记录并发限制命中次数
        """
        # 创建多个请求
        requests = [
            LLMRequest(
                call_type=CallType.TRADING_DECISION,
                messages=[{"role": "user", "content": f"请求{i}"}],
                timeout=5.0,
                caller_module="test",
                caller_function=f"test_stats_{i}"
            )
            for i in range(15)  # 15个并发请求
        ]
        
        # Mock慢速调用
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(0.2)
            return LLMResponse(
                call_id=args[0].call_id,
                success=True,
                content="统计响应"
            )
        
        gateway._execute_call_internal = slow_call
        
        # 并发执行
        await asyncio.gather(*[gateway.call_llm(req) for req in requests])
        
        # 验证统计
        stats = gateway.get_statistics()
        assert 'concurrent_limit_hits' in stats
        assert 'concurrent_limit_rate' in stats


class TestVLLMIntegration:
    """测试vLLM集成效果
    
    白皮书依据: 第二章 2.1 AI三脑架构 - vLLM集成
    需求: 8.2, 8.8 - vLLM集成优化
    """
    
    @pytest.fixture
    def gateway(self):
        """创建LLM网关实例"""
        with patch('redis.Redis'):
            gateway = LLMGateway()
            return gateway
    
    @pytest.mark.asyncio
    async def test_vllm_used_for_local_calls(self, gateway):
        """测试本地调用使用vLLM
        
        验证: 本地推理应该优先使用vLLM引擎
        """
        # 初始化vLLM引擎（Mock）
        gateway.vllm_engine = AsyncMock()
        gateway.vllm_engine.generate_async = AsyncMock(return_value={
            'text': 'vLLM响应',
            'tokens_used': 100
        })
        
        # 初始化批处理调度器（Mock）
        gateway.batch_scheduler = AsyncMock()
        
        # 创建本地请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{"role": "user", "content": "测试vLLM"}],
            caller_module="test",
            caller_function="test_vllm"
        )
        
        # Mock内部调用
        gateway._execute_call_internal = AsyncMock(return_value=LLMResponse(
            call_id=request.call_id,
            success=True,
            content="vLLM响应",
            provider_used=LLMProvider.QWEN_LOCAL
        ))
        
        # 执行调用
        response = await gateway.call_llm(request)
        
        # 验证使用vLLM
        assert response.success
        assert gateway._should_use_vllm(request)  # 现在应该返回True
    
    @pytest.mark.asyncio
    async def test_vllm_fallback_to_traditional(self, gateway):
        """测试vLLM故障回退
        
        验证: 当vLLM失败时，应该回退到传统LLM调用
        """
        # 初始化vLLM引擎（Mock失败）
        gateway.vllm_engine = AsyncMock()
        gateway.vllm_engine.generate_async = AsyncMock(side_effect=Exception("vLLM失败"))
        
        # Mock传统调用
        gateway._execute_traditional_llm_call = AsyncMock(return_value=LLMResponse(
            call_id="test",
            success=True,
            content="传统LLM响应"
        ))
        
        # 创建请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{"role": "user", "content": "测试回退"}],
            caller_module="test",
            caller_function="test_fallback"
        )
        
        # 执行调用
        response = await gateway._execute_vllm_call(request)
        
        # 验证回退
        assert response.success
        assert response.content == "传统LLM响应"
        assert gateway.call_stats['fallback_used'] >= 0
    
    @pytest.mark.asyncio
    async def test_vllm_statistics_tracking(self, gateway):
        """测试vLLM统计跟踪
        
        验证: 应该正确记录vLLM调用统计
        """
        # 初始化vLLM引擎（Mock）
        gateway.vllm_engine = AsyncMock()
        gateway.vllm_engine.generate_async = AsyncMock(return_value={
            'text': 'vLLM响应',
            'tokens_used': 100
        })
        gateway.vllm_engine.get_statistics = Mock(return_value={
            'total_requests': 10,
            'avg_latency_ms': 15.5
        })
        
        # 创建请求
        request = LLMRequest(
            call_type=CallType.TRADING_DECISION,
            provider=LLMProvider.QWEN_LOCAL,
            messages=[{"role": "user", "content": "测试统计"}],
            caller_module="test",
            caller_function="test_stats"
        )
        
        # Mock内部调用
        gateway._execute_call_internal = AsyncMock(return_value=LLMResponse(
            call_id=request.call_id,
            success=True,
            content="vLLM响应"
        ))
        
        # 执行调用
        await gateway.call_llm(request)
        
        # 获取统计
        stats = gateway.get_statistics()
        
        # 验证统计
        assert 'vllm_calls' in stats
        assert 'vllm_usage_rate' in stats
        assert 'vllm_engine_stats' in stats


class TestRequestQueue:
    """测试请求队列
    
    白皮书依据: 第七章 7.6 LLM调用优化
    需求: 7.6 - 请求队列管理
    """
    
    @pytest.fixture
    def gateway(self):
        """创建LLM网关实例"""
        with patch('redis.Redis'):
            gateway = LLMGateway()
            return gateway
    
    def test_request_queue_initialized(self, gateway):
        """测试请求队列已初始化
        
        验证: 请求队列应该在初始化时创建
        """
        assert hasattr(gateway, 'request_queue')
        assert isinstance(gateway.request_queue, asyncio.Queue)
        assert gateway.request_queue.maxsize == 100
    
    @pytest.mark.asyncio
    async def test_queue_handles_burst_requests(self, gateway):
        """测试队列处理突发请求
        
        验证: 队列应该能够缓冲突发请求
        """
        # 创建大量请求
        requests = [
            LLMRequest(
                call_type=CallType.TRADING_DECISION,
                messages=[{"role": "user", "content": f"突发请求{i}"}],
                caller_module="test",
                caller_function=f"test_burst_{i}"
            )
            for i in range(50)
        ]
        
        # Mock快速调用
        gateway._execute_call_internal = AsyncMock(return_value=LLMResponse(
            call_id="test",
            success=True,
            content="突发响应"
        ))
        
        # 并发提交所有请求
        responses = await asyncio.gather(*[gateway.call_llm(req) for req in requests])
        
        # 验证所有请求都被处理
        assert len(responses) == 50
        assert all(r.success for r in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
