"""Soldier本地推理引擎

白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)

本模块实现基于llama.cpp的本地推理引擎，支持GGUF格式的Qwen3-30B-MoE模型。
核心目标：推理延迟 < 20ms (P99)，支持热备切换。
"""

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .core import SoldierMode, TradingDecision


@dataclass
class InferenceConfig:
    """推理引擎配置

    白皮书依据: 第二章 2.1

    Attributes:
        model_path: GGUF模型文件路径
        n_ctx: 上下文长度 (默认4096)
        n_threads: CPU线程数 (默认8)
        n_gpu_layers: GPU层数 (默认-1表示全部)
        temperature: 采样温度 (默认0.1，偏保守)
        top_p: 核采样参数 (默认0.9)
        max_tokens: 最大生成token数 (默认256)
        timeout_ms: 推理超时时间毫秒 (默认200ms)

    Performance:
        目标延迟: < 20ms (P99)
        内存使用: < 24GB (Qwen3-30B-MoE)
        GPU利用率: > 80%
    """

    model_path: str
    n_ctx: int = 4096
    n_threads: int = 8
    n_gpu_layers: int = -1  # 全部GPU加速
    temperature: float = 0.1  # 保守采样
    top_p: float = 0.9
    max_tokens: int = 256
    timeout_ms: int = 200  # 200ms超时

    def __post_init__(self):
        """配置验证"""
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

        if self.timeout_ms <= 0:
            raise ValueError(f"超时时间必须 > 0: {self.timeout_ms}ms")

        if not 0 <= self.temperature <= 2:
            raise ValueError(f"温度必须在[0,2]范围: {self.temperature}")


class LocalInferenceEngine:
    """本地推理引擎

    白皮书依据: 第二章 2.1 Soldier (快系统)

    基于llama.cpp实现的高性能本地推理引擎，专门优化用于交易决策。
    采用异步设计，支持并发推理和超时控制。

    核心特性:
    - GGUF格式模型加载 (Qwen3-30B-MoE)
    - GPU加速推理 (CUDA/ROCm)
    - 异步推理接口
    - 超时和错误处理
    - 性能监控和统计

    Performance:
        推理延迟: < 20ms (P99)
        吞吐量: > 50 TPS
        内存使用: < 24GB

    Example:
        >>> config = InferenceConfig(
        ...     model_path="/models/qwen3-30b-moe.gguf",
        ...     timeout_ms=200
        ... )
        >>> engine = LocalInferenceEngine(config)
        >>> await engine.initialize()
        >>> decision = await engine.infer(market_data)
        >>> print(f"Action: {decision.action}, Confidence: {decision.confidence}")
    """

    def __init__(self, config: InferenceConfig):
        """初始化推理引擎

        Args:
            config: 推理配置

        Raises:
            ValueError: 当配置无效时
        """
        self.config = config
        self.model = None
        self.is_loaded = False
        self.inference_count = 0
        self.total_latency = 0.0
        self.error_count = 0
        self._lock = threading.Lock()

        # 性能统计
        self.latency_history: List[float] = []
        self.max_history_size = 1000

        logger.info(
            f"LocalInferenceEngine初始化: model={Path(config.model_path).name}, "
            f"timeout={config.timeout_ms}ms, gpu_layers={config.n_gpu_layers}"
        )

    async def initialize(self) -> None:
        """异步初始化推理引擎

        白皮书依据: 第二章 2.1

        加载GGUF模型并初始化llama.cpp上下文。

        Raises:
            RuntimeError: 当模型加载失败时
            ImportError: 当llama-cpp-python未安装时
        """
        try:
            # 在线程池中加载模型（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)

            self.is_loaded = True
            logger.info(f"模型加载成功: {Path(self.config.model_path).name}")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise RuntimeError(f"模型加载失败: {e}") from e

    def _load_model(self) -> None:
        """加载模型（同步方法，在线程池中执行）

        白皮书依据: 第二章 2.1

        使用llama.cpp加载GGUF格式的Qwen3-30B-MoE模型。

        Raises:
            ImportError: 当llama-cpp-python未安装时
            RuntimeError: 当模型加载失败时
        """
        try:
            # 导入llama-cpp-python
            from llama_cpp import Llama  # pylint: disable=import-outside-toplevel

            logger.info(f"开始加载模型: {self.config.model_path}")
            start_time = time.perf_counter()

            # 创建Llama实例
            self.model = Llama(
                model_path=self.config.model_path,
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                n_gpu_layers=self.config.n_gpu_layers,
                verbose=False,  # 减少日志输出
            )

            load_time = time.perf_counter() - start_time
            logger.info(f"模型加载完成，耗时: {load_time:.2f}s")

        except ImportError as e:
            raise ImportError("llama-cpp-python未安装，请运行: pip install llama-cpp-python") from e
        except Exception as e:
            raise RuntimeError(f"llama.cpp模型加载失败: {e}") from e

    async def infer(self, market_data: Dict[str, Any], timeout_ms: Optional[int] = None) -> TradingDecision:
        """执行推理生成交易决策

        白皮书依据: 第二章 2.1

        基于市场数据生成交易决策，目标延迟 < 20ms (P99)。

        Args:
            market_data: 市场数据字典
            timeout_ms: 超时时间（毫秒），None使用配置默认值

        Returns:
            TradingDecision: 交易决策

        Raises:
            RuntimeError: 当模型未加载时
            TimeoutError: 当推理超时时
            ValueError: 当输入数据无效时
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("模型未加载，请先调用initialize()")

        if not market_data:
            raise ValueError("market_data不能为空")

        # 使用指定超时或配置默认值
        timeout = (timeout_ms or self.config.timeout_ms) / 1000.0

        start_time = time.perf_counter()

        try:
            # 构建推理提示
            prompt = self._build_prompt(market_data)

            # 在线程池中执行推理（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(loop.run_in_executor(None, self._run_inference, prompt), timeout=timeout)

            # 解析结果
            decision = self._parse_result(result, market_data)

            # 记录性能统计
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._update_stats(latency_ms)

            decision.latency_ms = latency_ms
            decision.mode = SoldierMode.NORMAL

            logger.debug(
                f"推理完成: action={decision.action}, "
                f"confidence={decision.confidence:.2f}, "
                f"latency={latency_ms:.2f}ms"
            )

            return decision

        except asyncio.TimeoutError:
            self.error_count += 1
            raise TimeoutError(f"推理超时: {timeout*1000:.0f}ms")  # pylint: disable=w0707
        except Exception as e:
            self.error_count += 1
            logger.error(f"推理失败: {e}")
            raise RuntimeError(f"推理失败: {e}") from e

    def _build_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建推理提示词

        白皮书依据: 第二章 2.1

        根据市场数据构建结构化的推理提示，引导模型生成交易决策。

        Args:
            market_data: 市场数据

        Returns:
            str: 格式化的提示词
        """
        symbol = market_data.get("symbol", "UNKNOWN")
        price = market_data.get("price", 0)
        volume = market_data.get("volume", 0)
        change_pct = market_data.get("change_pct", 0)

        # 获取技术指标（如果有）
        rsi = market_data.get("rsi", 50)
        macd = market_data.get("macd", 0)
        ma20 = market_data.get("ma20", price)

        prompt = f"""你是一个专业的量化交易AI助手，请基于以下市场数据做出交易决策：

股票代码: {symbol}
当前价格: {price:.2f}
成交量: {volume:,}
涨跌幅: {change_pct:.2f}%
RSI: {rsi:.2f}
MACD: {macd:.4f}
20日均线: {ma20:.2f}

请严格按照以下JSON格式输出交易决策：
{{
    "action": "buy/sell/hold",
    "quantity": 数量(整数),
    "confidence": 置信度(0-1),
    "reasoning": "决策理由(简洁明了)"
}}

决策要求：
1. action只能是buy、sell、hold之一
2. quantity必须是非负整数
3. confidence必须在0-1之间
4. reasoning要简洁专业，不超过50字

交易决策："""

        return prompt

    def _run_inference(self, prompt: str) -> str:
        """运行推理（同步方法，在线程池中执行）

        Args:
            prompt: 推理提示词

        Returns:
            str: 模型输出结果

        Raises:
            RuntimeError: 当推理失败时
        """
        try:
            with self._lock:  # 确保线程安全
                response = self.model(
                    prompt,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    stop=["\n\n", "决策完成"],  # 停止词
                    echo=False,
                )

                return response["choices"][0]["text"].strip()

        except Exception as e:
            raise RuntimeError(f"llama.cpp推理失败: {e}") from e

    def _parse_result(self, result: str, market_data: Dict[str, Any]) -> TradingDecision:
        """解析推理结果

        Args:
            result: 模型输出结果
            market_data: 原始市场数据

        Returns:
            TradingDecision: 解析后的交易决策

        Raises:
            ValueError: 当结果解析失败时
        """
        try:
            # 尝试解析JSON
            # 提取JSON部分（可能包含其他文本）
            json_start = result.find("{")
            json_end = result.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("未找到有效的JSON格式")

            json_str = result[json_start:json_end]
            data = json.loads(json_str)

            # 验证必需字段
            required_fields = ["action", "quantity", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"缺少必需字段: {field}")

            # 创建交易决策
            decision = TradingDecision(
                action=str(data["action"]).lower(),
                symbol=market_data.get("symbol", "UNKNOWN"),
                quantity=int(data["quantity"]),
                confidence=float(data["confidence"]),
                reasoning=str(data["reasoning"]),
            )

            return decision

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.warning(f"结果解析失败，使用默认决策: {e}")
            logger.debug(f"原始结果: {result}")

            # 返回保守的默认决策
            return TradingDecision(
                action="hold",
                symbol=market_data.get("symbol", "UNKNOWN"),
                quantity=0,
                confidence=0.3,
                reasoning=f"模型输出解析失败，采用保守策略: {str(e)[:30]}",
            )

    def _update_stats(self, latency_ms: float) -> None:
        """更新性能统计

        Args:
            latency_ms: 推理延迟（毫秒）
        """
        self.inference_count += 1
        self.total_latency += latency_ms

        # 维护延迟历史（用于P99计算）
        self.latency_history.append(latency_ms)
        if len(self.latency_history) > self.max_history_size:
            self.latency_history.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计

        Returns:
            Dict: 性能统计信息
        """
        if self.inference_count == 0:
            return {
                "inference_count": 0,
                "avg_latency_ms": 0,
                "p99_latency_ms": 0,
                "error_count": self.error_count,
                "error_rate": 0,
                "is_loaded": self.is_loaded,
            }

        # 计算P99延迟
        sorted_latencies = sorted(self.latency_history)
        p99_index = int(len(sorted_latencies) * 0.99)
        p99_latency = sorted_latencies[p99_index] if sorted_latencies else 0

        return {
            "inference_count": self.inference_count,
            "avg_latency_ms": self.total_latency / self.inference_count,
            "p99_latency_ms": p99_latency,
            "error_count": self.error_count,
            "error_rate": self.error_count / (self.inference_count + self.error_count),
            "is_loaded": self.is_loaded,
            "model_path": self.config.model_path,
        }

    async def cleanup(self) -> None:
        """清理资源

        释放模型内存和其他资源。
        """
        try:
            if self.model is not None:
                # llama.cpp会自动清理，但我们可以显式设置为None
                self.model = None
                self.is_loaded = False
                logger.info("推理引擎资源已清理")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"资源清理失败: {e}")

    def __del__(self):
        """析构函数"""
        if hasattr(self, "model") and self.model is not None:
            # 注意：在析构函数中不能使用async
            self.model = None
