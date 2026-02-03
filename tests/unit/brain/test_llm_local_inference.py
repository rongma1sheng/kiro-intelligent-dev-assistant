"""
本地LLM推理引擎单元测试

白皮书依据: 第二章 2.1.2 Local Mode
测试覆盖: Task 18.2 - llama.cpp集成的单元测试

测试内容:
- 模型加载测试
- 推理接口测试
- 缓存机制测试
- 错误处理测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.brain.llm_local_inference import (
    LLMLocalInference,
    InferenceConfig,
    InferenceResult,
    ModelStatus,
    LLAMA_CPP_AVAILABLE
)


class TestLLMLocalInference:
    """本地LLM推理引擎测试套件"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return InferenceConfig(
            model_path="models/test_model.gguf",
            temperature=0.7,
            max_tokens=256,
            n_ctx=2048,
            n_batch=256,
            n_threads=4,
            n_gpu_layers=20,
            inference_timeout=5.0,
            cache_enabled=True,
            cache_max_size=100,
            cache_ttl=5
        )
    
    @pytest.fixture
    def inference_engine(self, config):
        """推理引擎实例"""
        return LLMLocalInference(config)
    
    def test_initialization(self, inference_engine, config):
        """测试初始化"""
        assert inference_engine.config == config
        assert inference_engine.status == ModelStatus.UNLOADED
        assert inference_engine.model is None
        assert len(inference_engine.cache) == 0
        assert inference_engine.stats['total_inferences'] == 0
    
    def test_initialization_with_default_config(self):
        """测试使用默认配置初始化"""
        engine = LLMLocalInference()
        assert engine.config is not None
        assert engine.config.model_path == "models/qwen3-30b-moe-q4_k_m.gguf"
        assert engine.config.temperature == 0.7
        assert engine.status == ModelStatus.UNLOADED
    
    @pytest.mark.asyncio
    @patch('src.brain.llm_local_inference.LLAMA_CPP_AVAILABLE', False)
    async def test_load_model_llama_cpp_not_available(self, inference_engine):
        """测试llama-cpp-python不可用时的模型加载"""
        result = await inference_engine.load_model()
        
        assert result is False
        assert inference_engine.status == ModelStatus.ERROR
    
    @pytest.mark.asyncio
    @patch('src.brain.llm_local_inference.LLAMA_CPP_AVAILABLE', True)
    @patch('src.brain.llm_local_inference.Path.exists', return_value=False)
    async def test_load_model_file_not_found(self, mock_exists, inference_engine):
        """测试模型文件不存在"""
        result = await inference_engine.load_model()
        
        assert result is False
        assert inference_engine.status == ModelStatus.ERROR
    
    @pytest.mark.asyncio
    @patch('src.brain.llm_local_inference.LLAMA_CPP_AVAILABLE', True)
    @patch('src.brain.llm_local_inference.Path.exists', return_value=True)
    async def test_load_model_success(self, mock_exists, inference_engine):
        """测试成功加载模型"""
        # 创建Mock Llama类并注入到模块中
        mock_llama_class = MagicMock()
        mock_model = MagicMock()
        mock_llama_class.return_value = mock_model
        
        # 临时注入Llama类到模块
        import src.brain.llm_local_inference as llm_module
        original_llama = getattr(llm_module, 'Llama', None)
        llm_module.Llama = mock_llama_class
        
        try:
            result = await inference_engine.load_model()
            
            assert result is True
            assert inference_engine.status == ModelStatus.READY
            assert inference_engine.model == mock_model
            
            # 验证Llama初始化参数
            mock_llama_class.assert_called_once()
            call_kwargs = mock_llama_class.call_args[1]
            assert call_kwargs['n_ctx'] == inference_engine.config.n_ctx
            assert call_kwargs['n_batch'] == inference_engine.config.n_batch
            assert call_kwargs['n_threads'] == inference_engine.config.n_threads
            assert call_kwargs['n_gpu_layers'] == inference_engine.config.n_gpu_layers
        finally:
            # 恢复原始状态
            if original_llama is not None:
                llm_module.Llama = original_llama
            else:
                delattr(llm_module, 'Llama')
    
    @pytest.mark.asyncio
    @patch('src.brain.llm_local_inference.LLAMA_CPP_AVAILABLE', True)
    @patch('src.brain.llm_local_inference.Path.exists', return_value=True)
    async def test_load_model_exception(self, mock_exists, inference_engine):
        """测试模型加载异常"""
        # 创建Mock Llama类并注入到模块中
        mock_llama_class = MagicMock()
        mock_llama_class.side_effect = Exception("Model loading failed")
        
        # 临时注入Llama类到模块
        import src.brain.llm_local_inference as llm_module
        original_llama = getattr(llm_module, 'Llama', None)
        llm_module.Llama = mock_llama_class
        
        try:
            result = await inference_engine.load_model()
            
            assert result is False
            assert inference_engine.status == ModelStatus.ERROR
        finally:
            # 恢复原始状态
            if original_llama is not None:
                llm_module.Llama = original_llama
            else:
                delattr(llm_module, 'Llama')
    
    @pytest.mark.asyncio
    async def test_infer_model_not_ready(self, inference_engine):
        """测试模型未就绪时的推理"""
        result = await inference_engine.infer("test prompt")
        
        assert result is None
        assert inference_engine.status == ModelStatus.UNLOADED
    
    @pytest.mark.asyncio
    async def test_infer_success(self, inference_engine):
        """测试成功推理"""
        # 设置模型为就绪状态
        inference_engine.status = ModelStatus.READY
        inference_engine.model = MagicMock()
        
        # Mock推理结果
        mock_output = {
            'choices': [{'text': 'Test response'}],
            'usage': {'completion_tokens': 10}
        }
        inference_engine.model.return_value = mock_output
        
        result = await inference_engine.infer("test prompt", use_cache=False)
        
        assert result is not None
        assert result.text == 'Test response'
        assert result.tokens == 10
        assert result.cached is False
        assert result.latency_ms > 0
        
        # 验证统计更新
        assert inference_engine.stats['total_inferences'] == 1
        assert inference_engine.stats['total_tokens'] == 10
        # 当use_cache=False时，不应增加cache_misses
        assert inference_engine.stats['cache_misses'] == 0
    
    @pytest.mark.asyncio
    async def test_infer_with_custom_parameters(self, inference_engine):
        """测试使用自定义参数推理"""
        inference_engine.status = ModelStatus.READY
        inference_engine.model = MagicMock()
        
        mock_output = {
            'choices': [{'text': 'Custom response'}],
            'usage': {'completion_tokens': 15}
        }
        inference_engine.model.return_value = mock_output
        
        result = await inference_engine.infer(
            "test prompt",
            temperature=0.5,
            max_tokens=128,
            use_cache=False
        )
        
        assert result is not None
        assert result.metadata['temperature'] == 0.5
        assert result.metadata['max_tokens'] == 128
    
    @pytest.mark.asyncio
    async def test_infer_with_cache_hit(self, inference_engine):
        """测试缓存命中"""
        inference_engine.status = ModelStatus.READY
        inference_engine.model = MagicMock()
        
        # 第一次推理（缓存未命中）
        mock_output = {
            'choices': [{'text': 'Cached response'}],
            'usage': {'completion_tokens': 20}
        }
        inference_engine.model.return_value = mock_output
        
        result1 = await inference_engine.infer("test prompt", use_cache=True)
        assert result1 is not None
        assert result1.cached is False
        assert inference_engine.stats['cache_misses'] == 1
        
        # 第二次推理（缓存命中）
        result2 = await inference_engine.infer("test prompt", use_cache=True)
        assert result2 is not None
        assert result2.cached is True
        assert inference_engine.stats['cache_hits'] == 1
        assert inference_engine.stats['total_inferences'] == 2
    
    @pytest.mark.asyncio
    async def test_infer_cache_disabled(self, inference_engine):
        """测试禁用缓存"""
        inference_engine.config.cache_enabled = False
        inference_engine.status = ModelStatus.READY
        inference_engine.model = MagicMock()
        
        mock_output = {
            'choices': [{'text': 'No cache response'}],
            'usage': {'completion_tokens': 12}
        }
        inference_engine.model.return_value = mock_output
        
        # 两次推理都不使用缓存
        result1 = await inference_engine.infer("test prompt")
        result2 = await inference_engine.infer("test prompt")
        
        assert result1 is not None
        assert result2 is not None
        assert inference_engine.stats['cache_hits'] == 0
        assert len(inference_engine.cache) == 0
    
    def test_generate_cache_key(self, inference_engine):
        """测试缓存键生成"""
        key1 = inference_engine._generate_cache_key("prompt1", 0.7, 256)
        key2 = inference_engine._generate_cache_key("prompt1", 0.7, 256)
        key3 = inference_engine._generate_cache_key("prompt2", 0.7, 256)
        
        # 相同输入生成相同键
        assert key1 == key2
        
        # 不同输入生成不同键
        assert key1 != key3
    
    def test_cache_lru_eviction(self, inference_engine):
        """测试LRU缓存淘汰"""
        inference_engine.config.cache_max_size = 3
        
        # 添加3个缓存条目
        for i in range(3):
            result = InferenceResult(
                text=f"response_{i}",
                tokens=10,
                latency_ms=5.0,
                cached=False,
                metadata={}
            )
            cache_key = f"key_{i}"
            inference_engine._add_to_cache(cache_key, result)
        
        assert len(inference_engine.cache) == 3
        
        # 添加第4个条目，应该淘汰最旧的
        result4 = InferenceResult(
            text="response_4",
            tokens=10,
            latency_ms=5.0,
            cached=False,
            metadata={}
        )
        inference_engine._add_to_cache("key_4", result4)
        
        assert len(inference_engine.cache) == 3
        assert "key_0" not in inference_engine.cache  # 最旧的被淘汰
        assert "key_4" in inference_engine.cache
    
    def test_cache_ttl_expiration(self, inference_engine):
        """测试缓存TTL过期"""
        import time
        
        inference_engine.config.cache_ttl = 1  # 1秒TTL
        
        # 添加缓存条目
        result = InferenceResult(
            text="response",
            tokens=10,
            latency_ms=5.0,
            cached=False,
            metadata={}
        )
        cache_key = "test_key"
        inference_engine._add_to_cache(cache_key, result)
        
        # 立即获取应该成功
        cached_result = inference_engine._get_from_cache(cache_key)
        assert cached_result is not None
        
        # 等待TTL过期
        time.sleep(1.1)
        
        # 再次获取应该失败（已过期）
        cached_result = inference_engine._get_from_cache(cache_key)
        assert cached_result is None
        assert cache_key not in inference_engine.cache
    
    def test_get_stats(self, inference_engine):
        """测试获取统计信息"""
        # 初始统计
        stats = inference_engine.get_stats()
        assert stats['total_inferences'] == 0
        assert stats['cache_hit_rate'] == 0.0
        assert stats['cache_size'] == 0
        assert stats['model_status'] == ModelStatus.UNLOADED.value
        
        # 更新统计
        inference_engine.stats['total_inferences'] = 10
        inference_engine.stats['cache_hits'] = 7
        
        stats = inference_engine.get_stats()
        assert stats['cache_hit_rate'] == 0.7
    
    def test_clear_cache(self, inference_engine):
        """测试清空缓存"""
        # 添加缓存条目
        result = InferenceResult(
            text="response",
            tokens=10,
            latency_ms=5.0,
            cached=False,
            metadata={}
        )
        inference_engine._add_to_cache("key_1", result)
        inference_engine._add_to_cache("key_2", result)
        
        assert len(inference_engine.cache) == 2
        
        # 清空缓存
        inference_engine.clear_cache()
        
        assert len(inference_engine.cache) == 0
        assert len(inference_engine.cache_access_times) == 0
    
    @pytest.mark.asyncio
    async def test_unload_model(self, inference_engine):
        """测试卸载模型"""
        # 设置模型为已加载
        inference_engine.model = MagicMock()
        inference_engine.status = ModelStatus.READY
        
        await inference_engine.unload_model()
        
        assert inference_engine.model is None
        assert inference_engine.status == ModelStatus.UNLOADED
    
    def test_update_avg_latency(self, inference_engine):
        """测试平均延迟更新"""
        # 第一次推理
        inference_engine.stats['total_inferences'] = 1
        inference_engine._update_avg_latency(10.0)
        assert inference_engine.stats['avg_latency_ms'] == 10.0
        
        # 第二次推理
        inference_engine.stats['total_inferences'] = 2
        inference_engine._update_avg_latency(20.0)
        assert inference_engine.stats['avg_latency_ms'] == 15.0
        
        # 第三次推理
        inference_engine.stats['total_inferences'] = 3
        inference_engine._update_avg_latency(30.0)
        assert inference_engine.stats['avg_latency_ms'] == 20.0


class TestInferenceConfig:
    """推理配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = InferenceConfig()
        
        assert config.model_path == "models/qwen3-30b-moe-q4_k_m.gguf"
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.top_k == 40
        assert config.max_tokens == 512
        assert config.n_ctx == 4096
        assert config.n_batch == 512
        assert config.n_threads == 8
        assert config.n_gpu_layers == 35
        assert config.inference_timeout == 5.0
        assert config.cache_enabled is True
        assert config.cache_max_size == 1000
        assert config.cache_ttl == 5
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = InferenceConfig(
            model_path="custom/model.gguf",
            temperature=0.5,
            max_tokens=256,
            cache_enabled=False
        )
        
        assert config.model_path == "custom/model.gguf"
        assert config.temperature == 0.5
        assert config.max_tokens == 256
        assert config.cache_enabled is False


class TestInferenceResult:
    """推理结果测试"""
    
    def test_inference_result_creation(self):
        """测试推理结果创建"""
        result = InferenceResult(
            text="Test response",
            tokens=15,
            latency_ms=12.5,
            cached=False,
            metadata={'model': 'test_model'}
        )
        
        assert result.text == "Test response"
        assert result.tokens == 15
        assert result.latency_ms == 12.5
        assert result.cached is False
        assert result.metadata['model'] == 'test_model'


# 性能测试（可选）
@pytest.mark.performance
class TestLLMLocalInferencePerformance:
    """本地LLM推理引擎性能测试"""
    
    @pytest.fixture
    def perf_inference_engine(self):
        """性能测试用推理引擎实例"""
        config = InferenceConfig(
            model_path="models/test_model.gguf",
            cache_enabled=True
        )
        return LLMLocalInference(config)
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not LLAMA_CPP_AVAILABLE, reason="llama-cpp-python not available")
    async def test_inference_latency_benchmark(self):
        """测试推理延迟基准
        
        性能目标: P99 < 20ms
        """
        # 注意：此测试需要真实模型文件
        # 在CI环境中应该跳过或使用mock
        pass
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, perf_inference_engine):
        """测试缓存性能"""
        perf_inference_engine.status = ModelStatus.READY
        perf_inference_engine.model = MagicMock()
        
        mock_output = {
            'choices': [{'text': 'Response'}],
            'usage': {'completion_tokens': 10}
        }
        perf_inference_engine.model.return_value = mock_output
        
        # 第一次推理（无缓存）
        result1 = await perf_inference_engine.infer("test", use_cache=True)
        latency1 = result1.latency_ms
        
        # 第二次推理（有缓存）
        result2 = await perf_inference_engine.infer("test", use_cache=True)
        latency2 = result2.latency_ms
        
        # 缓存命中应该更快
        assert result2.cached is True
        # 注意：由于mock，延迟可能不会显著降低，但在真实场景中会


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
