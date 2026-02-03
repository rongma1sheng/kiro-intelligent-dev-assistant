"""
DeepSeek API集成单元测试 - Task 19.6

白皮书依据: 第二章 2.1.2 Cloud Mode, 第十二章 12.1.3 Soldier热备切换

测试内容:
- API调用
- 限流控制
- 错误处理和重试
- 成本统计
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientTimeout, ClientError

from src.brain.deepseek_client import (
    DeepSeekClient,
    DeepSeekConfig,
    DeepSeekResponse,
    RateLimiter
)


@pytest.fixture
def deepseek_config():
    """测试配置"""
    return DeepSeekConfig(
        api_key="test_api_key",
        api_base="https://api.deepseek.com/v1",
        model="deepseek-chat",
        max_tokens=50,
        temperature=0.7,
        timeout=2.0,
        max_retries=3,
        qps_limit=10
    )


@pytest.fixture
def deepseek_client(deepseek_config):
    """DeepSeek客户端fixture"""
    return DeepSeekClient(deepseek_config)


class TestDeepSeekClient:
    """DeepSeek客户端基础测试"""
    
    def test_client_initialization(self, deepseek_client, deepseek_config):
        """测试客户端初始化"""
        assert deepseek_client.config == deepseek_config
        assert deepseek_client.rate_limiter is not None
        assert deepseek_client.stats['total_requests'] == 0
        assert deepseek_client.stats['total_cost'] == 0.0
    
    def test_get_stats(self, deepseek_client):
        """测试获取统计信息"""
        stats = deepseek_client.get_stats()
        
        assert 'total_requests' in stats
        assert 'successful_requests' in stats
        assert 'failed_requests' in stats
        assert 'success_rate' in stats
        assert 'total_tokens' in stats
        assert 'total_cost' in stats
        assert 'avg_latency_ms' in stats
        assert 'retry_count' in stats
    
    def test_reset_stats(self, deepseek_client):
        """测试重置统计信息"""
        # 修改统计信息
        deepseek_client.stats['total_requests'] = 10
        deepseek_client.stats['total_cost'] = 1.5
        
        # 重置
        deepseek_client.reset_stats()
        
        # 验证已重置
        assert deepseek_client.stats['total_requests'] == 0
        assert deepseek_client.stats['total_cost'] == 0.0


class TestAPICall:
    """API调用测试"""
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, deepseek_client):
        """测试成功的API调用"""
        # Mock API响应
        mock_response = {
            'choices': [
                {
                    'message': {'content': '动作: buy\n置信度: 0.8\n理由: 价格上涨'},
                    'finish_reason': 'stop'
                }
            ],
            'usage': {
                'total_tokens': 100,
                'prompt_tokens': 50,
                'completion_tokens': 50
            }
        }
        
        with patch.object(deepseek_client, '_call_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = DeepSeekResponse(
                text='动作: buy\n置信度: 0.8\n理由: 价格上涨',
                tokens=100,
                latency_ms=150.0,
                cost=0.00001,
                model='deepseek-chat',
                metadata={'usage': mock_response['usage'], 'finish_reason': 'stop'}
            )
            
            # 调用API
            response = await deepseek_client.chat_completion(
                prompt="测试提示词",
                max_tokens=50,
                temperature=0.7
            )
            
            # 验证响应
            assert response.text == '动作: buy\n置信度: 0.8\n理由: 价格上涨'
            assert response.tokens == 100
            assert response.latency_ms == 150.0
            assert response.cost == 0.00001
            
            # 验证统计更新
            assert deepseek_client.stats['total_requests'] == 1
            assert deepseek_client.stats['successful_requests'] == 1
            assert deepseek_client.stats['total_tokens'] == 100
    
    @pytest.mark.asyncio
    async def test_chat_completion_empty_prompt(self, deepseek_client):
        """测试空提示词"""
        with pytest.raises(ValueError, match="Prompt不能为空"):
            await deepseek_client.chat_completion(prompt="")
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_retry(self, deepseek_client):
        """测试重试机制"""
        # Mock第一次失败，第二次成功
        call_count = 0
        
        async def mock_call_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise RuntimeError("API调用失败")
            
            return DeepSeekResponse(
                text='成功响应',
                tokens=50,
                latency_ms=100.0,
                cost=0.000005,
                model='deepseek-chat',
                metadata={}
            )
        
        with patch.object(deepseek_client, '_call_api', side_effect=mock_call_with_retry):
            response = await deepseek_client.chat_completion(prompt="测试")
            
            # 验证重试成功
            assert call_count == 2
            assert response.text == '成功响应'
            assert deepseek_client.stats['retry_count'] == 1
    
    @pytest.mark.asyncio
    async def test_chat_completion_max_retries_exceeded(self, deepseek_client):
        """测试超过最大重试次数"""
        # Mock所有调用都失败
        with patch.object(deepseek_client, '_call_api', side_effect=RuntimeError("API失败")):
            with pytest.raises(RuntimeError, match="DeepSeek API调用失败"):
                await deepseek_client.chat_completion(prompt="测试")
            
            # 验证统计
            assert deepseek_client.stats['failed_requests'] == 1
            # 3次尝试（1次初始 + 2次重试）= 3次retry_count增加
            assert deepseek_client.stats['retry_count'] == 3


class TestRateLimiter:
    """限流控制测试"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """测试基本限流功能"""
        limiter = RateLimiter(qps_limit=5)
        
        # 快速发送5个请求（应该都通过）
        start_time = time.time()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.time() - start_time
        
        # 验证延迟很小
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_throttling(self):
        """测试限流节流"""
        limiter = RateLimiter(qps_limit=5)
        
        # 快速发送10个请求
        start_time = time.time()
        for _ in range(10):
            await limiter.acquire()
        elapsed = time.time() - start_time
        
        # 验证被限流（应该至少等待1秒）
        assert elapsed >= 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_sliding_window(self):
        """测试滑动窗口算法"""
        limiter = RateLimiter(qps_limit=3)
        
        # 发送3个请求
        for _ in range(3):
            await limiter.acquire()
        
        # 等待0.5秒
        await asyncio.sleep(0.5)
        
        # 再发送1个请求（应该被限流）
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time
        
        # 验证等待了约0.5秒
        assert 0.4 < elapsed < 0.7


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_api_error_status_code(self, deepseek_client):
        """测试API返回错误状态码"""
        async def mock_call_error(*args, **kwargs):
            raise RuntimeError("API返回错误状态码 500: Internal Server Error")
        
        with patch.object(deepseek_client, '_call_api', side_effect=mock_call_error):
            with pytest.raises(RuntimeError, match="DeepSeek API调用失败"):
                await deepseek_client.chat_completion(prompt="测试")
    
    @pytest.mark.asyncio
    async def test_api_timeout(self, deepseek_client):
        """测试API超时"""
        # Mock超时异常
        async def mock_call_timeout(*args, **kwargs):
            raise asyncio.TimeoutError("API调用超时")
        
        with patch.object(deepseek_client, '_call_api', side_effect=mock_call_timeout):
            # 设置较短的超时时间进行测试
            deepseek_client.config.timeout = 0.5
            
            with pytest.raises(RuntimeError, match="DeepSeek API调用失败"):
                await deepseek_client.chat_completion(prompt="测试")
    
    @pytest.mark.asyncio
    async def test_api_invalid_response(self, deepseek_client):
        """测试API返回无效响应"""
        async def mock_call_invalid(*args, **kwargs):
            raise RuntimeError("API响应格式错误: 缺少choices字段")
        
        with patch.object(deepseek_client, '_call_api', side_effect=mock_call_invalid):
            with pytest.raises(RuntimeError, match="DeepSeek API调用失败"):
                await deepseek_client.chat_completion(prompt="测试")


class TestCostTracking:
    """成本统计测试"""
    
    @pytest.mark.asyncio
    async def test_cost_calculation(self, deepseek_client):
        """测试成本计算"""
        # Mock API响应
        with patch.object(deepseek_client, '_call_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = DeepSeekResponse(
                text='响应',
                tokens=1000,  # 1000 tokens
                latency_ms=100.0,
                cost=0.0001,  # ¥0.1/M * 1000/1M = ¥0.0001
                model='deepseek-chat',
                metadata={}
            )
            
            await deepseek_client.chat_completion(prompt="测试")
            
            # 验证成本统计
            assert deepseek_client.stats['total_tokens'] == 1000
            assert deepseek_client.stats['total_cost'] == 0.0001
    
    @pytest.mark.asyncio
    async def test_cumulative_cost(self, deepseek_client):
        """测试累计成本"""
        # Mock多次API调用
        with patch.object(deepseek_client, '_call_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = DeepSeekResponse(
                text='响应',
                tokens=500,
                latency_ms=100.0,
                cost=0.00005,
                model='deepseek-chat',
                metadata={}
            )
            
            # 调用3次
            for _ in range(3):
                await deepseek_client.chat_completion(prompt="测试")
            
            # 验证累计成本
            assert deepseek_client.stats['total_tokens'] == 1500
            assert abs(deepseek_client.stats['total_cost'] - 0.00015) < 0.000001


class TestPerformanceMetrics:
    """性能指标测试"""
    
    @pytest.mark.asyncio
    async def test_latency_tracking(self, deepseek_client):
        """测试延迟统计"""
        # Mock不同延迟的API调用
        latencies = [100.0, 150.0, 200.0]
        
        for latency in latencies:
            with patch.object(deepseek_client, '_call_api', new_callable=AsyncMock) as mock_call:
                mock_call.return_value = DeepSeekResponse(
                    text='响应',
                    tokens=50,
                    latency_ms=latency,
                    cost=0.000005,
                    model='deepseek-chat',
                    metadata={}
                )
                
                await deepseek_client.chat_completion(prompt="测试")
        
        # 验证平均延迟
        expected_avg = sum(latencies) / len(latencies)
        assert abs(deepseek_client.stats['avg_latency_ms'] - expected_avg) < 1.0
    
    @pytest.mark.asyncio
    async def test_success_rate(self, deepseek_client):
        """测试成功率统计"""
        # Mock 2次成功，1次失败（所有重试都失败）
        call_count = 0
        
        async def mock_call_mixed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # 第2次调用失败（包括所有重试）
            if 2 <= call_count <= 4:  # 第2次请求的3次尝试
                raise RuntimeError("失败")
            
            return DeepSeekResponse(
                text='响应',
                tokens=50,
                latency_ms=100.0,
                cost=0.000005,
                model='deepseek-chat',
                metadata={}
            )
        
        with patch.object(deepseek_client, '_call_api', side_effect=mock_call_mixed):
            # 第一次成功
            await deepseek_client.chat_completion(prompt="测试1")
            
            # 第二次失败（所有重试都失败）
            try:
                await deepseek_client.chat_completion(prompt="测试2")
            except RuntimeError:
                pass
            
            # 第三次成功
            await deepseek_client.chat_completion(prompt="测试3")
        
        # 验证成功率
        stats = deepseek_client.get_stats()
        assert stats['total_requests'] == 3
        assert stats['successful_requests'] == 2
        assert stats['failed_requests'] == 1
        assert abs(stats['success_rate'] - 2/3) < 0.01


class TestAPICallIntegration:
    """API调用集成测试（测试_call_api方法）"""
    
    @pytest.mark.asyncio
    async def test_call_api_response_parsing(self, deepseek_client):
        """测试API响应解析"""
        # Mock aiohttp响应
        mock_response_data = {
            'choices': [
                {
                    'message': {'content': '测试响应内容'},
                    'finish_reason': 'stop'
                }
            ],
            'usage': {
                'total_tokens': 100,
                'prompt_tokens': 50,
                'completion_tokens': 50
            }
        }
        
        # Mock aiohttp响应对象
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        # Mock session.post返回mock_response
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await deepseek_client._call_api(
                prompt="测试提示词",
                max_tokens=50,
                temperature=0.7
            )
            
            # 验证响应
            assert response.text == '测试响应内容'
            assert response.tokens == 100
            assert response.cost > 0
            assert response.model == 'deepseek-chat'
    
    @pytest.mark.asyncio
    async def test_call_api_http_error(self, deepseek_client):
        """测试HTTP错误处理"""
        # Mock HTTP 500错误
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(RuntimeError, match="API返回错误状态码 500"):
                await deepseek_client._call_api(
                    prompt="测试",
                    max_tokens=50,
                    temperature=0.7
                )
    
    @pytest.mark.asyncio
    async def test_call_api_missing_choices(self, deepseek_client):
        """测试缺少choices字段"""
        # Mock无效响应
        mock_response_data = {
            'usage': {'total_tokens': 100}
            # 缺少choices字段
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(RuntimeError, match="API响应格式错误: 缺少choices字段"):
                await deepseek_client._call_api(
                    prompt="测试",
                    max_tokens=50,
                    temperature=0.7
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
