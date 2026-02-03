"""
DeepSeek API客户端 - Task 19.5

白皮书依据: 第二章 2.1.2 Cloud Mode, 第十二章 12.1.3 Soldier热备切换

功能:
- DeepSeek-v3.2 API调用封装
- API限流控制（QPS限制）
- 错误处理和重试机制
- 成本统计
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger


@dataclass
class DeepSeekConfig:
    """DeepSeek API配置

    白皮书依据: 第十八章 18.1 成本分析模型
    """

    api_key: str = ""  # API密钥（从环境变量读取）
    api_base: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"  # deepseek-chat 或 deepseek-r1
    max_tokens: int = 50  # 最大生成token数
    temperature: float = 0.7
    timeout: float = 2.0  # 2秒超时
    max_retries: int = 3  # 最大重试次数
    qps_limit: int = 10  # QPS限制（每秒请求数）
    price_per_million_tokens: float = 0.1  # ¥0.1/M tokens


@dataclass
class DeepSeekResponse:
    """DeepSeek API响应

    白皮书依据: 第二章 2.1.3 决策流程
    """

    text: str
    tokens: int
    latency_ms: float
    cost: float  # 成本（元）
    model: str
    metadata: Dict[str, Any]


class RateLimiter:
    """速率限制器

    白皮书依据: 第十八章 18.2 熔断机制

    实现滑动窗口算法，限制QPS
    """

    def __init__(self, qps_limit: int):
        """初始化速率限制器

        Args:
            qps_limit: 每秒请求数限制
        """
        self.qps_limit = qps_limit
        self.requests: deque = deque()  # 请求时间戳队列
        self.lock = asyncio.Lock()

    async def acquire(self):
        """获取请求许可

        如果超过QPS限制，等待直到可以发送请求
        """
        async with self.lock:
            now = time.time()

            # 移除1秒前的请求记录
            while self.requests and self.requests[0] < now - 1.0:
                self.requests.popleft()

            # 检查是否超过限制
            if len(self.requests) >= self.qps_limit:
                # 计算需要等待的时间
                oldest_request = self.requests[0]
                wait_time = 1.0 - (now - oldest_request)

                if wait_time > 0:
                    logger.debug(f"[RateLimiter] QPS limit reached, waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)
                    now = time.time()

                    # 再次清理过期记录
                    while self.requests and self.requests[0] < now - 1.0:
                        self.requests.popleft()

            # 记录本次请求
            self.requests.append(now)


class DeepSeekClient:
    """DeepSeek API客户端

    白皮书依据: 第二章 2.1.2 Cloud Mode

    功能:
    - API调用封装
    - 限流控制
    - 错误处理和重试
    - 成本统计
    """

    def __init__(self, config: Optional[DeepSeekConfig] = None):
        """初始化DeepSeek客户端

        Args:
            config: API配置
        """
        self.config = config or DeepSeekConfig()
        self.rate_limiter = RateLimiter(self.config.qps_limit)

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,  # 总成本（元）
            "avg_latency_ms": 0.0,
            "retry_count": 0,
        }

        logger.info(
            f"[DeepSeekClient] Initialized - " f"model={self.config.model}, " f"qps_limit={self.config.qps_limit}"
        )

    async def chat_completion(
        self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None
    ) -> DeepSeekResponse:
        """调用DeepSeek Chat API

        白皮书依据: 第二章 2.1.3 决策流程

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            temperature: 温度参数

        Returns:
            DeepSeekResponse: API响应

        Raises:
            RuntimeError: API调用失败
        """
        if not prompt:
            raise ValueError("Prompt不能为空")

        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature or self.config.temperature

        # 限流控制
        await self.rate_limiter.acquire()

        # 重试机制
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self._call_api(prompt, max_tokens, temperature)

                # 更新统计
                self.stats["total_requests"] += 1
                self.stats["successful_requests"] += 1
                self.stats["total_tokens"] += response.tokens
                self.stats["total_cost"] += response.cost

                # 更新平均延迟
                total_latency = (
                    self.stats["avg_latency_ms"] * (self.stats["successful_requests"] - 1) + response.latency_ms
                )
                self.stats["avg_latency_ms"] = total_latency / self.stats["successful_requests"]

                return response

            except Exception as e:  # pylint: disable=broad-exception-caught
                last_error = e
                self.stats["retry_count"] += 1

                if attempt < self.config.max_retries - 1:
                    # 指数退避
                    wait_time = 2**attempt
                    logger.warning(
                        f"[DeepSeekClient] API call failed (attempt {attempt + 1}/{self.config.max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[DeepSeekClient] API call failed after {self.config.max_retries} attempts: {e}")

        # 所有重试都失败
        self.stats["total_requests"] += 1
        self.stats["failed_requests"] += 1

        raise RuntimeError(f"DeepSeek API调用失败: {last_error}") from last_error

    async def _call_api(self, prompt: str, max_tokens: int, temperature: float) -> DeepSeekResponse:
        """实际的API调用

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            temperature: 温度参数

        Returns:
            DeepSeekResponse: API响应
        """
        start_time = time.perf_counter()

        # 构建请求
        url = f"{self.config.api_base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}

        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # 发送请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"API返回错误状态码 {response.status}: {error_text}")

                data = await response.json()

        # 解析响应
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if "choices" not in data or not data["choices"]:
            raise RuntimeError("API响应格式错误: 缺少choices字段")

        text = data["choices"][0]["message"]["content"]

        # 计算token数和成本
        usage = data.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)
        cost = (total_tokens / 1_000_000) * self.config.price_per_million_tokens

        logger.debug(
            f"[DeepSeekClient] API call successful - "
            f"tokens={total_tokens}, "
            f"latency={elapsed_ms:.2f}ms, "
            f"cost=¥{cost:.4f}"
        )

        return DeepSeekResponse(
            text=text,
            tokens=total_tokens,
            latency_ms=elapsed_ms,
            cost=cost,
            model=self.config.model,
            metadata={"usage": usage, "finish_reason": data["choices"][0].get("finish_reason", "unknown")},
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        白皮书依据: 第十八章 18.1 成本分析模型

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0
                else 0.0
            ),
            "total_tokens": self.stats["total_tokens"],
            "total_cost": self.stats["total_cost"],
            "avg_latency_ms": self.stats["avg_latency_ms"],
            "retry_count": self.stats["retry_count"],
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_latency_ms": 0.0,
            "retry_count": 0,
        }
        logger.info("[DeepSeekClient] Statistics reset")


# 显式导出列表
__all__ = ["DeepSeekConfig", "DeepSeekResponse", "DeepSeekClient", "RateLimiter"]
