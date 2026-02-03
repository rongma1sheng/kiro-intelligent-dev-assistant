"""
本地LLM推理引擎 - llama.cpp集成

白皮书依据: 第二章 2.1.2 Local Mode - 本地Qwen3-30B-MoE (GGUF/llama.cpp)

功能:
- 集成llama.cpp Python绑定
- 实现GGUF模型加载
- 提供高性能推理接口
- 支持批量推理优化

性能目标:
- 推理延迟: P99 < 20ms
- 支持批量推理: batch_size=4
- 内存优化: 使用量化模型
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    logger.warning("[LLMLocalInference] llama-cpp-python not installed")
    LLAMA_CPP_AVAILABLE = False


class ModelStatus(Enum):
    """模型状态"""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@dataclass
class InferenceConfig:  # pylint: disable=too-many-instance-attributes
    """推理配置

    白皮书依据: 第二章 2.1.3 决策流程
    """

    # 模型路径
    model_path: str = "models/qwen3-30b-moe-q4_k_m.gguf"

    # 推理参数 - 优化后的默认值
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 512

    # 性能参数
    n_ctx: int = 4096  # 上下文窗口
    n_batch: int = 512  # 批处理大小
    n_threads: int = 8  # CPU线程数
    n_gpu_layers: int = 35  # GPU层数（AMD ROCm）

    # 超时控制
    inference_timeout: float = 5.0  # 5秒超时

    # 缓存配置 - 优化后的LRU缓存
    cache_enabled: bool = True
    cache_max_size: int = 1000  # 最大1000项
    cache_ttl: int = 5  # 5秒TTL

    # 批量推理配置
    batch_inference_enabled: bool = True
    batch_size: int = 4  # 批量推理大小
    batch_timeout: float = 0.1  # 批量等待超时（100ms）

    # Token生成优化
    use_mirostat: bool = False  # Mirostat采样
    mirostat_tau: float = 5.0
    mirostat_eta: float = 0.1
    repeat_penalty: float = 1.1  # 重复惩罚
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


@dataclass
class InferenceResult:
    """推理结果"""

    text: str
    tokens: int
    latency_ms: float
    cached: bool
    metadata: Dict[str, Any]


class LLMLocalInference:
    """本地LLM推理引擎

    白皮书依据: 第二章 2.1.2 Local Mode

    功能:
    - GGUF模型加载和管理
    - 高性能推理接口
    - 结果缓存优化（LRU Cache）
    - 批量推理支持
    - Token生成优化

    性能优化:
    - 推理结果缓存（LRU Cache，最大1000项）
    - Token生成策略优化（temperature, top_p, top_k, repeat_penalty）
    - 批量推理（batch_size=4）
    - 推理超时控制（timeout=5s）
    """

    def __init__(self, config: Optional[InferenceConfig] = None):
        """初始化本地推理引擎

        Args:
            config: 推理配置，None使用默认配置
        """
        self.config = config or InferenceConfig()
        self.model: Optional[Llama] = None
        self.status = ModelStatus.UNLOADED

        # 推理缓存 (LRU Cache)
        self.cache: Dict[str, InferenceResult] = {}
        self.cache_access_times: Dict[str, float] = {}

        # 批量推理队列
        self.batch_queue: List[Dict[str, Any]] = []
        self.batch_lock = asyncio.Lock()
        self.batch_event = asyncio.Event()

        # 统计信息
        self.stats = {
            "total_inferences": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0.0,
            "error_count": 0,
            "batch_inferences": 0,
            "p50_latency_ms": 0.0,
            "p90_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }

        # 延迟历史（用于计算P50/P90/P99）
        self.latency_history: List[float] = []
        self.max_latency_history = 1000  # 保留最近1000次推理的延迟

        logger.info(f"[LLMLocalInference] Initialized with config: {self.config.model_path}")
        logger.info(
            f"[LLMLocalInference] Batch inference: {self.config.batch_inference_enabled}, batch_size: {self.config.batch_size}"  # pylint: disable=line-too-long
        )

    async def load_model(self) -> bool:
        """加载GGUF模型

        白皮书依据: 第二章 2.1.2 Local Mode - GGUF模型加载

        Returns:
            bool: 加载成功返回True，失败返回False
        """
        if not LLAMA_CPP_AVAILABLE:
            logger.error("[LLMLocalInference] llama-cpp-python not available")
            self.status = ModelStatus.ERROR
            return False

        try:
            self.status = ModelStatus.LOADING
            logger.info(f"[LLMLocalInference] Loading model: {self.config.model_path}")

            # 检查模型文件是否存在
            model_path = Path(self.config.model_path)
            if not model_path.exists():
                logger.error(f"[LLMLocalInference] Model file not found: {model_path}")
                self.status = ModelStatus.ERROR
                return False

            # 加载模型
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=self.config.n_ctx,
                n_batch=self.config.n_batch,
                n_threads=self.config.n_threads,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False,
            )

            self.status = ModelStatus.READY
            logger.info(f"[LLMLocalInference] Model loaded successfully")  # pylint: disable=w1309
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.status = ModelStatus.ERROR
            logger.error(f"[LLMLocalInference] Failed to load model: {e}")
            return False

    async def infer(
        self, prompt: str, temperature: Optional[float] = None, max_tokens: Optional[int] = None, use_cache: bool = True
    ) -> Optional[InferenceResult]:
        """执行推理（优化版）

        白皮书依据: 第二章 2.1.3 决策流程

        性能优化:
        - 推理结果缓存（LRU Cache）
        - 超时控制（5秒）
        - 批量推理支持
        - Token生成优化

        Args:
            prompt: 输入提示词
            temperature: 温度参数，None使用配置默认值
            max_tokens: 最大token数，None使用配置默认值
            use_cache: 是否使用缓存

        Returns:
            Optional[InferenceResult]: 推理结果，失败返回None
        """
        if self.status != ModelStatus.READY:
            logger.error(f"[LLMLocalInference] Model not ready: {self.status.value}")
            return None

        # 检查缓存
        if use_cache and self.config.cache_enabled:
            cache_key = self._generate_cache_key(prompt, temperature, max_tokens)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self.stats["cache_hits"] += 1
                self.stats["total_inferences"] += 1
                logger.debug(f"[LLMLocalInference] Cache hit: {cache_key[:32]}...")
                return cached_result
            # 只有在启用缓存时才记录cache_misses
            self.stats["cache_misses"] += 1

        try:
            start_time = time.perf_counter()

            # 执行推理（带超时控制）
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._run_inference_optimized,
                    prompt,
                    temperature or self.config.temperature,
                    max_tokens or self.config.max_tokens,
                ),
                timeout=self.config.inference_timeout,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # 创建结果
            result = InferenceResult(
                text=response["text"],
                tokens=response["tokens"],
                latency_ms=latency_ms,
                cached=False,
                metadata={
                    "model": self.config.model_path,
                    "temperature": temperature or self.config.temperature,
                    "max_tokens": max_tokens or self.config.max_tokens,
                },
            )

            # 更新统计
            self.stats["total_inferences"] += 1
            self.stats["total_tokens"] += response["tokens"]
            self._update_latency_stats(latency_ms)

            # 缓存结果
            if use_cache and self.config.cache_enabled:
                self._add_to_cache(cache_key, result)

            logger.debug(f"[LLMLocalInference] Inference completed: {latency_ms:.2f}ms, {response['tokens']} tokens")
            return result

        except asyncio.TimeoutError:
            self.stats["error_count"] += 1
            logger.error(f"[LLMLocalInference] Inference timeout: {self.config.inference_timeout}s")
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["error_count"] += 1
            logger.error(f"[LLMLocalInference] Inference failed: {e}")
            return None

    def _run_inference_optimized(self, prompt: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
        """运行推理（优化版，同步方法，在线程池中执行）

        白皮书依据: 第二章 2.1.3 决策流程

        性能优化:
        - Token生成策略优化（temperature, top_p, top_k）
        - 重复惩罚（repeat_penalty）
        - Mirostat采样（可选）

        Args:
            prompt: 输入提示词
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            Dict[str, Any]: 推理结果
        """
        if not self.model:
            raise RuntimeError("Model not loaded")

        # 构建推理参数
        inference_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "repeat_penalty": self.config.repeat_penalty,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "echo": False,
        }

        # 可选：使用Mirostat采样
        if self.config.use_mirostat:
            inference_params["mirostat_mode"] = 2
            inference_params["mirostat_tau"] = self.config.mirostat_tau
            inference_params["mirostat_eta"] = self.config.mirostat_eta

        # 调用llama.cpp推理
        output = self.model(prompt, **inference_params)

        # 提取结果
        text = output["choices"][0]["text"]
        tokens = output["usage"]["completion_tokens"]

        return {"text": text.strip(), "tokens": tokens}

    async def infer_batch(
        self,
        prompts: List[str],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[Optional[InferenceResult]]:
        """批量推理（优化版）

        白皮书依据: 第二章 2.1.3 决策流程 - 批量推理优化

        性能优化:
        - 批量处理（batch_size=4）
        - 并行推理
        - 缓存复用

        Args:
            prompts: 输入提示词列表
            temperature: 温度参数，None使用配置默认值
            max_tokens: 最大token数，None使用配置默认值
            use_cache: 是否使用缓存

        Returns:
            List[Optional[InferenceResult]]: 推理结果列表
        """
        if not self.config.batch_inference_enabled:
            # 批量推理未启用，逐个推理
            results = []
            for prompt in prompts:
                result = await self.infer(prompt, temperature, max_tokens, use_cache)
                results.append(result)
            return results

        # 批量推理
        results: List[Optional[InferenceResult]] = []

        # 分批处理
        for i in range(0, len(prompts), self.config.batch_size):
            batch = prompts[i : i + self.config.batch_size]

            # 并行推理
            batch_tasks = [self.infer(prompt, temperature, max_tokens, use_cache) for prompt in batch]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # 处理结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"[LLMLocalInference] Batch inference error: {result}")
                    results.append(None)
                else:
                    results.append(result)

            self.stats["batch_inferences"] += 1

        logger.debug(f"[LLMLocalInference] Batch inference completed: {len(prompts)} prompts")
        return results

    def _generate_cache_key(self, prompt: str, temperature: Optional[float], max_tokens: Optional[int]) -> str:
        """生成缓存键

        Args:
            prompt: 输入提示词
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            str: 缓存键
        """
        import hashlib  # pylint: disable=import-outside-toplevel

        key_str = f"{prompt}_{temperature}_{max_tokens}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[InferenceResult]:
        """从缓存获取结果

        Args:
            cache_key: 缓存键

        Returns:
            Optional[InferenceResult]: 缓存结果，不存在或过期返回None
        """
        if cache_key not in self.cache:
            return None

        # 检查TTL
        access_time = self.cache_access_times.get(cache_key, 0)
        if time.time() - access_time > self.config.cache_ttl:
            # 过期，删除
            del self.cache[cache_key]
            del self.cache_access_times[cache_key]
            return None

        # 更新访问时间
        self.cache_access_times[cache_key] = time.time()

        # 返回缓存结果（标记为cached）
        result = self.cache[cache_key]
        result.cached = True
        return result

    def _add_to_cache(self, cache_key: str, result: InferenceResult):
        """添加到缓存

        Args:
            cache_key: 缓存键
            result: 推理结果
        """
        # 检查缓存大小
        if len(self.cache) >= self.config.cache_max_size:
            # LRU淘汰：删除最旧的条目
            oldest_key = min(self.cache_access_times, key=self.cache_access_times.get)
            del self.cache[oldest_key]
            del self.cache_access_times[oldest_key]

        # 添加到缓存
        self.cache[cache_key] = result
        self.cache_access_times[cache_key] = time.time()

    def _update_latency_stats(self, latency_ms: float):
        """更新延迟统计（包括P50/P90/P99）

        白皮书依据: 第二章 2.1.4 性能目标 - P99 < 20ms

        Args:
            latency_ms: 本次推理延迟（毫秒）
        """
        # 更新平均延迟
        total = self.stats["total_inferences"]
        if total == 1:
            self.stats["avg_latency_ms"] = latency_ms
        else:
            # 增量更新平均值
            old_avg = self.stats["avg_latency_ms"]
            self.stats["avg_latency_ms"] = (old_avg * (total - 1) + latency_ms) / total

        # 添加到延迟历史
        self.latency_history.append(latency_ms)

        # 限制历史大小
        if len(self.latency_history) > self.max_latency_history:
            self.latency_history.pop(0)

        # 计算P50/P90/P99
        if len(self.latency_history) >= 10:  # 至少10个样本
            sorted_latencies = sorted(self.latency_history)
            n = len(sorted_latencies)

            self.stats["p50_latency_ms"] = sorted_latencies[int(n * 0.50)]
            self.stats["p90_latency_ms"] = sorted_latencies[int(n * 0.90)]
            self.stats["p99_latency_ms"] = sorted_latencies[int(n * 0.99)]

    def _update_avg_latency(self, latency_ms: float):
        """更新平均延迟（简化版，用于测试兼容性）

        白皮书依据: 第二章 2.1.4 性能目标

        Args:
            latency_ms: 本次推理延迟（毫秒）
        """
        total = self.stats["total_inferences"]
        if total == 1:
            self.stats["avg_latency_ms"] = latency_ms
        else:
            # 增量更新平均值
            old_avg = self.stats["avg_latency_ms"]
            self.stats["avg_latency_ms"] = (old_avg * (total - 1) + latency_ms) / total

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（包含性能指标）

        白皮书依据: 第二章 2.1.4 性能目标

        Returns:
            Dict[str, Any]: 统计信息，包含:
                - total_inferences: 总推理次数
                - cache_hits: 缓存命中次数
                - cache_misses: 缓存未命中次数
                - cache_hit_rate: 缓存命中率
                - total_tokens: 总token数
                - avg_latency_ms: 平均延迟（毫秒）
                - p50_latency_ms: P50延迟（毫秒）
                - p90_latency_ms: P90延迟（毫秒）
                - p99_latency_ms: P99延迟（毫秒）
                - error_count: 错误次数
                - batch_inferences: 批量推理次数
                - cache_size: 当前缓存大小
                - model_status: 模型状态
        """
        cache_hit_rate = 0.0
        if self.stats["total_inferences"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["total_inferences"]

        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.cache),
            "model_status": self.status.value,
            "latency_history_size": len(self.latency_history),
        }

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.cache_access_times.clear()
        logger.info("[LLMLocalInference] Cache cleared")

    async def unload_model(self):
        """卸载模型"""
        if self.model:
            self.model = None
            self.status = ModelStatus.UNLOADED
            logger.info("[LLMLocalInference] Model unloaded")


# 测试代码
if __name__ == "__main__":
    print("LLMLocalInference module loaded")
    print(f"llama-cpp-python available: {LLAMA_CPP_AVAILABLE}")
    print("Classes defined:")
    print(f"  LLMLocalInference: {'LLMLocalInference' in globals()}")
    print(f"  InferenceConfig: {'InferenceConfig' in globals()}")
    print(f"  InferenceResult: {'InferenceResult' in globals()}")
    print(f"  ModelStatus: {'ModelStatus' in globals()}")
