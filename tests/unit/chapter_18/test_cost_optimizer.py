"""Unit Tests for CostOptimizer

白皮书依据: 第十八章 18.3 成本优化策略

测试覆盖:
- 优先使用本地模型
- 响应缓存
- 批量调用
- Prompt压缩
- 模型选择
- 边界条件和异常情况
"""

import pytest
import time
from src.optimization.cost_optimizer import CostOptimizer


class TestCostOptimizer:
    """测试CostOptimizer类"""
    
    @pytest.fixture
    def optimizer(self):
        """测试夹具：创建成本优化器实例"""
        return CostOptimizer(cache_ttl=300, batch_size=10)
    
    def test_init_success(self):
        """测试初始化成功"""
        optimizer = CostOptimizer(cache_ttl=300, batch_size=10)
        
        assert optimizer.cache_ttl == 300
        assert optimizer.batch_size == 10
        assert len(optimizer.cache) == 0
        assert optimizer.cache_hits == 0
        assert optimizer.cache_misses == 0
    
    def test_init_invalid_cache_ttl(self):
        """测试初始化失败：无效的缓存TTL"""
        with pytest.raises(ValueError, match="缓存过期时间必须 > 0"):
            CostOptimizer(cache_ttl=0, batch_size=10)
    
    def test_init_invalid_batch_size(self):
        """测试初始化失败：无效的批量大小"""
        with pytest.raises(ValueError, match="批量大小必须 > 0"):
            CostOptimizer(cache_ttl=300, batch_size=-1)
    
    def test_prefer_local_over_cloud_local_available(self, optimizer):
        """测试优先使用本地模型：本地可用"""
        model = optimizer.prefer_local_over_cloud(
            local_available=True,
            budget_exceeded=False
        )
        
        assert model == 'local'
        assert optimizer.local_model_uses == 1
    
    def test_prefer_local_over_cloud_budget_exceeded(self, optimizer):
        """测试优先使用本地模型：预算超限"""
        model = optimizer.prefer_local_over_cloud(
            local_available=False,
            budget_exceeded=True
        )
        
        assert model == 'local'  # 即使不可用也返回local
    
    def test_prefer_local_over_cloud_use_cloud(self, optimizer):
        """测试优先使用本地模型：使用云端"""
        model = optimizer.prefer_local_over_cloud(
            local_available=False,
            budget_exceeded=False
        )
        
        assert model == 'cloud'
        assert optimizer.cloud_model_uses == 1
    
    def test_implement_response_caching_store(self, optimizer):
        """测试响应缓存：存储"""
        result = optimizer.implement_response_caching(
            request_key='test_request',
            response={'result': 'test_response'}
        )
        
        assert result is None  # 存储时返回None
        assert len(optimizer.cache) == 1
    
    def test_implement_response_caching_hit(self, optimizer):
        """测试响应缓存：命中"""
        # 先存储
        optimizer.implement_response_caching(
            request_key='test_request',
            response={'result': 'test_response'}
        )
        
        # 再查询
        cached = optimizer.implement_response_caching(
            request_key='test_request'
        )
        
        assert cached == {'result': 'test_response'}
        assert optimizer.cache_hits == 1
    
    def test_implement_response_caching_miss(self, optimizer):
        """测试响应缓存：未命中"""
        cached = optimizer.implement_response_caching(
            request_key='nonexistent_request'
        )
        
        assert cached is None
        assert optimizer.cache_misses == 1
    
    def test_implement_response_caching_expired(self, optimizer):
        """测试响应缓存：过期"""
        # 使用短TTL
        optimizer_short = CostOptimizer(cache_ttl=1, batch_size=10)
        
        # 存储
        optimizer_short.implement_response_caching(
            request_key='test_request',
            response={'result': 'test_response'}
        )
        
        # 等待过期
        time.sleep(1.5)
        
        # 查询应该未命中
        cached = optimizer_short.implement_response_caching(
            request_key='test_request'
        )
        
        assert cached is None
        assert optimizer_short.cache_misses == 1
    
    def test_implement_response_caching_empty_key(self, optimizer):
        """测试响应缓存失败：空请求键"""
        with pytest.raises(ValueError, match="请求键不能为空"):
            optimizer.implement_response_caching(request_key='')
    
    def test_batch_api_calls_single_batch(self, optimizer):
        """测试批量API调用：单个批次"""
        requests = ['req1', 'req2', 'req3']
        batches = optimizer.batch_api_calls(requests)
        
        assert len(batches) == 1
        assert batches[0] == requests
        assert optimizer.batch_calls == 1
    
    def test_batch_api_calls_multiple_batches(self, optimizer):
        """测试批量API调用：多个批次"""
        requests = [f'req{i}' for i in range(25)]
        batches = optimizer.batch_api_calls(requests)
        
        assert len(batches) == 3  # 10, 10, 5
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5
    
    def test_batch_api_calls_custom_size(self, optimizer):
        """测试批量API调用：自定义批量大小"""
        requests = [f'req{i}' for i in range(25)]
        batches = optimizer.batch_api_calls(requests, max_batch_size=5)
        
        assert len(batches) == 5  # 5个批次，每个5个
        for batch in batches:
            assert len(batch) == 5
    
    def test_batch_api_calls_empty_requests(self, optimizer):
        """测试批量API调用失败：空请求列表"""
        with pytest.raises(ValueError, match="请求列表不能为空"):
            optimizer.batch_api_calls([])
    
    def test_use_cheaper_models_simple(self, optimizer):
        """测试使用更便宜的模型：简单任务"""
        model_prices = {
            'cheap-model': 0.1,
            'medium-model': 0.5,
            'expensive-model': 1.0
        }
        
        model = optimizer.use_cheaper_models('simple', model_prices)
        assert model == 'cheap-model'
    
    def test_use_cheaper_models_medium(self, optimizer):
        """测试使用更便宜的模型：中等任务"""
        model_prices = {
            'cheap-model': 0.1,
            'medium-model': 0.5,
            'expensive-model': 1.0
        }
        
        model = optimizer.use_cheaper_models('medium', model_prices)
        assert model == 'medium-model'
    
    def test_use_cheaper_models_complex(self, optimizer):
        """测试使用更便宜的模型：复杂任务"""
        model_prices = {
            'cheap-model': 0.1,
            'medium-model': 0.5,
            'expensive-model': 1.0
        }
        
        model = optimizer.use_cheaper_models('complex', model_prices)
        assert model == 'expensive-model'
    
    def test_use_cheaper_models_invalid_complexity(self, optimizer):
        """测试使用更便宜的模型失败：无效的任务复杂度"""
        with pytest.raises(ValueError, match="无效的任务复杂度"):
            optimizer.use_cheaper_models('invalid', {'model': 0.1})
    
    def test_use_cheaper_models_empty_prices(self, optimizer):
        """测试使用更便宜的模型失败：空价格表"""
        with pytest.raises(ValueError, match="模型价格表不能为空"):
            optimizer.use_cheaper_models('simple', {})
    
    def test_compress_prompt_basic(self, optimizer):
        """测试Prompt压缩：基本压缩"""
        prompt = "请分析股票代码000001的交易量和市盈率"
        compressed = optimizer.compress_prompt(prompt)
        
        assert len(compressed) < len(prompt)
        assert '分析' in compressed
        assert '代码' in compressed
        assert '量' in compressed
        assert 'PE' in compressed
    
    def test_compress_prompt_empty(self, optimizer):
        """测试Prompt压缩：空字符串"""
        compressed = optimizer.compress_prompt('')
        assert compressed == ''
    
    def test_compress_prompt_no_replacements(self, optimizer):
        """测试Prompt压缩：无可替换内容"""
        prompt = "simple text"
        compressed = optimizer.compress_prompt(prompt)
        assert compressed == prompt
    
    def test_compress_prompt_multiple_spaces(self, optimizer):
        """测试Prompt压缩：多余空格"""
        prompt = "text   with    multiple     spaces"
        compressed = optimizer.compress_prompt(prompt)
        assert '  ' not in compressed
    
    def test_get_cache_hit_rate_no_data(self, optimizer):
        """测试获取缓存命中率：无数据"""
        rate = optimizer.get_cache_hit_rate()
        assert rate == 0.0
    
    def test_get_cache_hit_rate_with_data(self, optimizer):
        """测试获取缓存命中率：有数据"""
        # 存储
        optimizer.implement_response_caching('req1', {'result': 'resp1'})
        optimizer.implement_response_caching('req2', {'result': 'resp2'})
        
        # 命中
        optimizer.implement_response_caching('req1')
        optimizer.implement_response_caching('req2')
        
        # 未命中
        optimizer.implement_response_caching('req3')
        
        rate = optimizer.get_cache_hit_rate()
        assert rate == 2 / 3  # 2命中，1未命中
    
    def test_get_statistics(self, optimizer):
        """测试获取统计信息"""
        # 模拟一些操作
        optimizer.prefer_local_over_cloud(True, False)
        optimizer.prefer_local_over_cloud(False, False)
        optimizer.implement_response_caching('req1', {'result': 'resp1'})
        optimizer.implement_response_caching('req1')
        optimizer.batch_api_calls(['req1', 'req2'])
        
        stats = optimizer.get_statistics()
        
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 0
        assert stats['cache_size'] == 1
        assert stats['local_model_uses'] == 1
        assert stats['cloud_model_uses'] == 1
        assert stats['batch_calls'] == 1
        assert stats['cache_ttl'] == 300
        assert stats['batch_size'] == 10
    
    def test_clear_cache(self, optimizer):
        """测试清空缓存"""
        optimizer.implement_response_caching('req1', {'result': 'resp1'})
        optimizer.implement_response_caching('req2', {'result': 'resp2'})
        
        assert len(optimizer.cache) == 2
        
        optimizer.clear_cache()
        
        assert len(optimizer.cache) == 0
    
    def test_clear_expired_cache(self, optimizer):
        """测试清理过期缓存"""
        # 使用短TTL
        optimizer_short = CostOptimizer(cache_ttl=1, batch_size=10)
        
        # 存储
        optimizer_short.implement_response_caching('req1', {'result': 'resp1'})
        optimizer_short.implement_response_caching('req2', {'result': 'resp2'})
        
        # 等待过期
        time.sleep(1.5)
        
        # 清理
        count = optimizer_short.clear_expired_cache()
        
        assert count == 2
        assert len(optimizer_short.cache) == 0
    
    def test_clear_expired_cache_no_expired(self, optimizer):
        """测试清理过期缓存：无过期"""
        optimizer.implement_response_caching('req1', {'result': 'resp1'})
        
        count = optimizer.clear_expired_cache()
        
        assert count == 0
        assert len(optimizer.cache) == 1
    
    def test_generate_cache_key(self, optimizer):
        """测试生成缓存键"""
        key1 = optimizer._generate_cache_key('request1')
        key2 = optimizer._generate_cache_key('request2')
        key3 = optimizer._generate_cache_key('request1')  # 相同请求
        
        assert key1 != key2
        assert key1 == key3  # 相同请求生成相同键
        assert len(key1) == 32  # MD5哈希长度
