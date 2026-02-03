# pylint: disable=too-many-lines
"""
MIA系统统一LLM调用网关 (Unified LLM Gateway)

白皮书依据: 第二章 2.8 统一记忆系统 + 第十一章 11.1 防幻觉系统
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心理念: 所有LLM调用必须经过统一的控制单元，确保：
1. 记忆系统集成 - 所有调用都有上下文记忆
2. 防幻觉检测 - 所有响应都经过幻觉过滤
3. 成本控制 - 统一的预算管理和成本追踪
4. 性能监控 - 延迟、成功率、质量指标监控
5. 安全审计 - 所有调用都有完整的审计日志

严禁直接调用LLM API！所有调用必须通过LLMGateway！
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import redis
from loguru import logger

from ..base.exceptions import ResourceError, ValidationError
from ..utils.logger import get_logger
from .adaptive_batch_scheduler import AdaptiveBatchScheduler
from .hallucination_filter import HallucinationFilter
from .memory.unified_memory_system import UnifiedMemorySystem
from .vllm_inference_engine import VLLMInferenceEngine

logger = get_logger(__name__)


class LLMProvider(Enum):
    """LLM提供商"""

    QWEN_LOCAL = "qwen_local"  # 本地Qwen3-30B-MoE
    QWEN_CLOUD = "qwen_cloud"  # 云端Qwen3-Next-80B
    DEEPSEEK = "deepseek"  # DeepSeek-R1/v3.2
    GLM = "glm"  # GLM-4 (智谱AI)
    CLAUDE = "claude"  # Claude-3.5 (如果可用)


class CallType(Enum):
    """调用类型"""

    TRADING_DECISION = "trading_decision"  # 交易决策
    STRATEGY_ANALYSIS = "strategy_analysis"  # 策略分析
    RESEARCH_ANALYSIS = "research_analysis"  # 研究分析
    FACTOR_GENERATION = "factor_generation"  # 因子生成
    CODE_GENERATION = "code_generation"  # 代码生成
    DATA_ANALYSIS = "data_analysis"  # 数据分析
    RISK_ASSESSMENT = "risk_assessment"  # 风险评估
    MARKET_SENTIMENT = "market_sentiment"  # 市场情绪


@dataclass
class LLMRequest:  # pylint: disable=too-many-instance-attributes
    """LLM请求"""

    call_id: str = field(default_factory=lambda: hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8])
    call_type: CallType = CallType.TRADING_DECISION
    provider: LLMProvider = LLMProvider.QWEN_LOCAL
    model: str = "qwen3-30b-moe"
    messages: List[Dict[str, str]] = field(default_factory=list)
    system_prompt: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: float = 30.0

    # 记忆系统配置
    use_memory: bool = True
    memory_context_length: int = 10

    # 安全配置
    enable_hallucination_filter: bool = True
    enable_content_filter: bool = True

    # 成本控制
    max_cost: float = 1.0  # 最大成本（元）
    priority: int = 1  # 优先级 1-5

    # 元数据
    caller_module: str = "unknown"
    caller_function: str = "unknown"
    business_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LLMResponse:  # pylint: disable=too-many-instance-attributes
    """LLM响应"""

    call_id: str
    success: bool
    content: str = ""

    # 质量指标
    hallucination_score: float = 0.0
    confidence_score: float = 0.0
    quality_score: float = 0.0

    # 性能指标
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0

    # 记忆系统
    memory_hits: int = 0
    memory_updates: int = 0

    # 错误信息
    error_message: str = ""
    error_code: str = ""

    # 元数据
    provider_used: LLMProvider = LLMProvider.QWEN_LOCAL
    model_used: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # 审计信息
    audit_log: Dict[str, Any] = field(default_factory=dict)


class LLMGateway:  # pylint: disable=too-many-instance-attributes
    """统一LLM调用网关

    白皮书依据: 第二章 2.8 统一记忆系统 + 第十一章 11.1 防幻觉系统

    核心职责:
    1. 统一所有LLM调用入口
    2. 集成记忆系统 (Engram + 传统记忆)
    3. 防幻觉检测和过滤
    4. 成本控制和预算管理
    5. 性能监控和质量评估
    6. 安全审计和日志记录
    7. 故障转移和降级处理

    使用示例:
        >>> gateway = LLMGateway()
        >>> request = LLMRequest(
        ...     call_type=CallType.TRADING_DECISION,
        ...     messages=[{"role": "user", "content": "分析当前市场"}],
        ...     caller_module="soldier",
        ...     caller_function="make_decision"
        ... )
        >>> response = await gateway.call_llm(request)
        >>> if response.success:
        ...     print(f"决策: {response.content}")
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化LLM网关

        Args:
            redis_client: Redis客户端，用于记忆系统和缓存
        """
        # Redis连接
        self.redis_client = redis_client or redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

        # 核心组件初始化
        self.memory_system = UnifiedMemorySystem(redis_client=self.redis_client)
        self.hallucination_filter = HallucinationFilter()

        # vLLM集成组件 - Task 10.7
        self.vllm_engine: Optional[VLLMInferenceEngine] = None
        self.batch_scheduler: Optional[AdaptiveBatchScheduler] = None

        # 成本控制
        self.cost_tracker = CostTracker(redis_client=self.redis_client)
        self.budget_manager = BudgetManager(daily_budget=50.0, monthly_budget=1500.0)  # 日预算50元  # 月预算1500元

        # 性能监控
        self.performance_monitor = PerformanceMonitor(redis_client=self.redis_client)

        # LLM客户端池
        self.llm_clients = {}
        self._initialize_llm_clients()

        # Task 14.5: 并发控制和请求队列
        self.max_concurrent_calls = 10  # 最大并发数
        self.concurrent_semaphore = asyncio.Semaphore(self.max_concurrent_calls)
        self.request_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        # Task 14.5: 重试配置
        self.max_retries = 3  # 最大重试次数
        self.retry_base_delay = 1.0  # 基础延迟（秒）
        self.retry_max_delay = 10.0  # 最大延迟（秒）

        # 调用统计
        self.call_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "hallucination_detected": 0,
            "budget_exceeded": 0,
            "fallback_used": 0,
            "vllm_calls": 0,
            "batch_calls": 0,
            "retries": 0,
            "timeouts": 0,
            "concurrent_limit_hits": 0,
        }

        logger.info("LLM网关初始化完成 - 统一记忆系统 + 防幻觉系统 + vLLM集成 + 并发控制已就绪")

    async def initialize(self):
        """初始化LLM网关 - 异步初始化方法

        白皮书依据: 第二章 2.1 AI三脑架构 - vLLM集成
        需求: 8.2, 8.8 - vLLM集成到AI三脑
        """
        try:
            logger.info("[LLMGateway] Starting vLLM integration initialization...")

            # 初始化vLLM推理引擎
            self.vllm_engine = VLLMInferenceEngine()
            await self.vllm_engine.initialize()

            # 初始化自适应批处理调度器
            self.batch_scheduler = AdaptiveBatchScheduler()
            await self.batch_scheduler.initialize()

            logger.info("[LLMGateway] vLLM集成初始化完成")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LLMGateway] vLLM集成初始化失败: {e}")  # pylint: disable=logging-fstring-interpolation
            # 降级到传统模式
            logger.warning("[LLMGateway] 降级到传统LLM调用模式")

        logger.info("LLM网关异步初始化完成")

    async def call_llm(self, request: LLMRequest) -> LLMResponse:
        """统一LLM调用接口 - Task 14.5增强版

        这是系统中唯一合法的LLM调用入口！
        所有其他模块必须通过此接口调用LLM。

        白皮书依据: 第二章 2.8 统一记忆系统 + 第十一章 11.1 防幻觉系统
        需求: 7.6 - LLM调用优化（超时、重试、并发控制）

        Args:
            request: LLM请求对象

        Returns:
            LLM响应对象

        Raises:
            ValidationError: 请求参数无效
            ResourceError: 资源不足或预算超限
        """
        # Task 14.5: 并发控制
        async with self.concurrent_semaphore:
            # 检查是否达到并发限制
            if self.concurrent_semaphore.locked():
                self.call_stats["concurrent_limit_hits"] += 1
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"[LLMGateway] 达到并发限制: {self.max_concurrent_calls}"
                )  # pylint: disable=logging-fstring-interpolation

            # Task 14.5: 重试机制（指数退避）
            return await self._call_llm_with_retry(request)

    async def _call_llm_with_retry(self, request: LLMRequest) -> LLMResponse:
        """带重试机制的LLM调用

        白皮书依据: 第七章 7.6 LLM调用优化
        需求: 7.6 - 重试机制（指数退避）

        Args:
            request: LLM请求对象

        Returns:
            LLM响应对象
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # 执行实际调用
                response = await self._execute_call_with_timeout(request)

                # 成功则返回
                if response.success:
                    if attempt > 0:
                        logger.info(  # pylint: disable=logging-fstring-interpolation
                            f"[LLMGateway] 重试成功: {request.call_id}, 尝试次数: {attempt + 1}"
                        )  # pylint: disable=logging-fstring-interpolation
                    return response

                # 如果是不可重试的错误，直接返回
                if response.error_code in ["VALIDATION_ERROR", "BUDGET_EXCEEDED", "HALLUCINATION_DETECTED"]:
                    return response

                # 记录失败，准备重试
                last_error = response.error_message

            except asyncio.TimeoutError as e:
                last_error = f"超时: {str(e)}"
                self.call_stats["timeouts"] += 1
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"[LLMGateway] 调用超时: {request.call_id}, 尝试: {attempt + 1}/{self.max_retries + 1}"
                )  # pylint: disable=logging-fstring-interpolation

            except Exception as e:  # pylint: disable=broad-exception-caught
                last_error = str(e)
                logger.error(  # pylint: disable=logging-fstring-interpolation
                    f"[LLMGateway] 调用异常: {request.call_id}, 错误: {e}, 尝试: {attempt + 1}/{self.max_retries + 1}"
                )

            # 如果还有重试机会，等待后重试
            if attempt < self.max_retries:
                # 指数退避
                delay = min(self.retry_base_delay * (2**attempt), self.retry_max_delay)
                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"[LLMGateway] 等待 {delay:.1f}s 后重试..."
                )  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(delay)
                self.call_stats["retries"] += 1

        # 所有重试都失败
        error_response = LLMResponse(
            call_id=request.call_id,
            success=False,
            error_message=f"重试{self.max_retries}次后仍失败: {last_error}",
            error_code="MAX_RETRIES_EXCEEDED",
        )

        self.call_stats["failed_calls"] += 1
        logger.error(f"[LLMGateway] 调用最终失败: {request.call_id}")  # pylint: disable=logging-fstring-interpolation

        return error_response

    async def _execute_call_with_timeout(self, request: LLMRequest) -> LLMResponse:
        """带超时控制的LLM调用

        白皮书依据: 第七章 7.6 LLM调用优化
        需求: 7.6 - 超时控制

        Args:
            request: LLM请求对象

        Returns:
            LLM响应对象

        Raises:
            asyncio.TimeoutError: 调用超时
        """
        start_time = time.perf_counter()

        try:
            # Task 14.5: 超时控制
            response = await asyncio.wait_for(self._execute_call_internal(request), timeout=request.timeout)

            return response

        except asyncio.TimeoutError:
            # 超时处理
            error_response = LLMResponse(  # pylint: disable=unused-variable
                call_id=request.call_id,
                success=False,
                error_message=f"调用超时: {request.timeout}秒",
                error_code="TIMEOUT_ERROR",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

            logger.warning(  # pylint: disable=logging-fstring-interpolation
                f"[LLMGateway] 调用超时: {request.call_id}, 超时设置: {request.timeout}s"
            )  # pylint: disable=logging-fstring-interpolation
            raise

    async def _execute_call_internal(self, request: LLMRequest) -> LLMResponse:
        """内部调用执行逻辑（原call_llm的核心逻辑）

        Args:
            request: LLM请求对象

        Returns:
            LLM响应对象
        """
        start_time = time.perf_counter()

        try:
            # 1. 请求验证
            self._validate_request(request)

            # 2. 预算检查
            await self._check_budget(request)

            # 3. 记忆系统增强
            enhanced_request = await self._enhance_with_memory(request)

            # 4. 执行LLM调用
            raw_response = await self._execute_llm_call(enhanced_request)

            # 5. 防幻觉检测
            filtered_response = await self._filter_hallucination(raw_response, enhanced_request)

            # 6. 更新记忆系统
            await self._update_memory(enhanced_request, filtered_response)

            # 7. 成本记录
            await self._record_cost(enhanced_request, filtered_response)

            # 8. 性能监控
            latency = (time.perf_counter() - start_time) * 1000
            await self._record_performance(enhanced_request, filtered_response, latency)

            # 9. 审计日志
            await self._log_audit(enhanced_request, filtered_response)

            # 10. 更新统计
            self._update_stats(filtered_response)

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"LLM调用完成: {request.call_id}, 延迟: {latency:.2f}ms, 成本: ¥{filtered_response.cost:.4f}"
            )  # pylint: disable=logging-fstring-interpolation

            return filtered_response

        except Exception as e:  # pylint: disable=broad-exception-caught
            # 错误处理
            error_response = LLMResponse(
                call_id=request.call_id,
                success=False,
                error_message=str(e),
                error_code=type(e).__name__,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

            # 记录错误
            await self._log_error(request, error_response, e)

            logger.error(f"LLM调用失败: {request.call_id}, 错误: {e}")  # pylint: disable=logging-fstring-interpolation

            return error_response

    def _validate_request(self, request: LLMRequest) -> None:
        """验证请求参数"""
        if not request.messages:
            raise ValidationError("消息列表不能为空")

        if request.max_tokens <= 0 or request.max_tokens > 8000:
            raise ValidationError(f"max_tokens必须在1-8000之间，当前: {request.max_tokens}")

        if not 0 <= request.temperature <= 2:
            raise ValidationError(f"temperature必须在0-2之间，当前: {request.temperature}")

        if request.timeout <= 0 or request.timeout > 300:
            raise ValidationError(f"timeout必须在0-300秒之间，当前: {request.timeout}")

        if not request.caller_module or not request.caller_function:
            raise ValidationError("必须指定caller_module和caller_function")

    async def _check_budget(self, request: LLMRequest) -> None:
        """检查预算限制"""
        # 估算调用成本
        estimated_cost = self._estimate_cost(request)

        # 检查预算
        if not await self.budget_manager.check_budget(estimated_cost):
            raise ResourceError(f"预算不足，估算成本: ¥{estimated_cost:.4f}")

        # 检查单次调用成本限制
        if estimated_cost > request.max_cost:
            raise ResourceError(f"单次调用成本超限: ¥{estimated_cost:.4f} > ¥{request.max_cost:.4f}")

    async def _enhance_with_memory(self, request: LLMRequest) -> LLMRequest:
        """使用记忆系统增强请求"""
        if not request.use_memory:
            return request

        try:
            # 构建查询上下文
            query_context = {
                "call_type": request.call_type.value,
                "caller_module": request.caller_module,
                "business_context": request.business_context,
                "messages": request.messages[-3:],  # 最近3条消息
            }

            # 查询Engram记忆
            memory_vector = await self.memory_system.engram_memory.query_memory(
                text=json.dumps(query_context), context=query_context
            )

            # 查询传统记忆
            traditional_context = await self.memory_system.get_relevant_context(
                query_context, max_items=request.memory_context_length
            )

            # 增强系统提示
            enhanced_system_prompt = self._build_enhanced_system_prompt(
                request.system_prompt, memory_vector, traditional_context, request.call_type
            )

            # 创建增强请求
            enhanced_request = LLMRequest(
                call_id=request.call_id,
                call_type=request.call_type,
                provider=request.provider,
                model=request.model,
                messages=request.messages.copy(),
                system_prompt=enhanced_system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                timeout=request.timeout,
                use_memory=request.use_memory,
                memory_context_length=request.memory_context_length,
                enable_hallucination_filter=request.enable_hallucination_filter,
                enable_content_filter=request.enable_content_filter,
                max_cost=request.max_cost,
                priority=request.priority,
                caller_module=request.caller_module,
                caller_function=request.caller_function,
                business_context=request.business_context,
                created_at=request.created_at,
            )

            logger.debug(f"记忆系统增强完成: {request.call_id}")  # pylint: disable=logging-fstring-interpolation
            return enhanced_request

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"记忆系统增强失败: {e}, 使用原始请求")  # pylint: disable=logging-fstring-interpolation
            return request

    def _build_enhanced_system_prompt(
        self,
        original_prompt: Optional[str],
        memory_vector: Optional[Dict],
        traditional_context: List[Dict],
        call_type: CallType,
    ) -> str:
        """构建增强的系统提示"""

        # 基础系统提示
        base_prompt = original_prompt or self._get_default_system_prompt(call_type)

        # 记忆增强部分
        memory_enhancement = ""

        if memory_vector:
            memory_enhancement += f"""
## 🧠 相关记忆 (Engram)
基于历史经验，以下信息可能相关：
{memory_vector.get('summary', '暂无相关记忆')}

关键模式: {memory_vector.get('patterns', [])}
置信度: {memory_vector.get('confidence', 0.0):.2f}
"""

        if traditional_context:
            memory_enhancement += """  # pylint: disable=w1309
## 📚 上下文记忆 (Traditional)
最近相关的决策和分析：
"""
            for i, ctx in enumerate(traditional_context[:3], 1):
                memory_enhancement += f"{i}. {ctx.get('summary', '无摘要')}\n"

        # 组合增强提示
        enhanced_prompt = f"""{base_prompt}

{memory_enhancement}

## ⚠️ 重要提醒
1. 基于上述记忆和上下文进行分析
2. 如果记忆中的信息与当前情况冲突，优先考虑当前数据
3. 明确说明你的推理过程和依据
4. 避免产生与历史记录矛盾的结论
"""

        return enhanced_prompt

    def _get_default_system_prompt(self, call_type: CallType) -> str:
        """获取默认系统提示"""
        prompts = {
            CallType.TRADING_DECISION: """你是MIA系统的交易决策AI。基于市场数据和技术分析，提供准确的交易建议。
要求：1) 明确的买入/卖出/持有建议 2) 详细的理由说明 3) 风险评估 4) 止损建议""",
            CallType.STRATEGY_ANALYSIS: """你是MIA系统的策略分析AI。深度分析交易策略的有效性、风险和改进建议。
要求：1) 策略优缺点分析 2) 历史表现评估 3) 风险因子识别 4) 优化建议""",
            CallType.RESEARCH_ANALYSIS: """你是MIA系统的研究分析AI。分析学术论文、研报和市场研究，提取可执行的投资洞察。
要求：1) 核心观点提取 2) 投资机会识别 3) 风险提示 4) 实施建议""",
            CallType.FACTOR_GENERATION: """你是MIA系统的因子生成AI。基于理论研究和市场数据，设计有效的量化因子。
要求：1) 因子逻辑说明 2) 完整Python代码 3) 预期效果评估 4) 风险控制""",
            CallType.CODE_GENERATION: """你是MIA系统的代码生成AI。生成高质量、可执行的Python代码。
要求：1) 完整可运行代码 2) 详细注释 3) 错误处理 4) 性能优化""",
            CallType.DATA_ANALYSIS: """你是MIA系统的数据分析AI。深度分析市场数据，发现模式和异常。
要求：1) 数据质量评估 2) 模式识别 3) 异常检测 4) 投资含义""",
            CallType.RISK_ASSESSMENT: """你是MIA系统的风险评估AI。全面评估投资风险，提供风控建议。
要求：1) 风险类型识别 2) 风险量化 3) 缓解措施 4) 监控指标""",
            CallType.MARKET_SENTIMENT: """你是MIA系统的市场情绪AI。分析市场情绪和投资者行为。
要求：1) 情绪指标分析 2) 行为模式识别 3) 情绪转折点 4) 交易含义""",
        }

        return prompts.get(call_type, "你是MIA系统的AI助手，请提供专业、准确的分析和建议。")

    async def _execute_llm_call(self, request: LLMRequest) -> LLMResponse:
        """执行实际的LLM调用

        白皮书依据: 第二章 2.1 AI三脑架构 - vLLM集成优化
        需求: 8.2, 8.8 - vLLM集成到AI三脑
        """
        try:
            # 优先使用vLLM引擎（如果可用且适合）
            if self._should_use_vllm(request):
                return await self._execute_vllm_call(request)

            # 回退到传统LLM调用
            return await self._execute_traditional_llm_call(request)

        except Exception as e:
            logger.error(f"LLM调用执行失败: {e}")  # pylint: disable=logging-fstring-interpolation
            raise

    def _should_use_vllm(self, request: LLMRequest) -> bool:
        """判断是否应该使用vLLM

        Args:
            request: LLM请求

        Returns:
            bool: 是否使用vLLM
        """
        # vLLM可用性检查
        if not self.vllm_engine or not self.batch_scheduler:
            return False

        # 本地推理优先使用vLLM
        if request.provider == LLMProvider.QWEN_LOCAL:
            return True

        # 高频调用（Soldier）优先使用vLLM
        if request.call_type == CallType.TRADING_DECISION:
            return True

        # 批处理友好的调用类型
        batch_friendly_types = {CallType.STRATEGY_ANALYSIS, CallType.FACTOR_GENERATION, CallType.DATA_ANALYSIS}

        if request.call_type in batch_friendly_types:
            return True

        return False

    async def _execute_vllm_call(self, request: LLMRequest) -> LLMResponse:
        """执行vLLM调用

        白皮书依据: 第二章 2.1 AI三脑架构 - vLLM优化
        需求: 8.2, 8.8 - vLLM集成优化
        """
        start_time = time.perf_counter()

        try:
            # 确定调用者模块以设置优先级
            caller_module = request.caller_module.lower()

            # 构建vLLM推理请求
            vllm_request = {
                "prompt": self._build_vllm_prompt(request),
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "caller_module": caller_module,
                "request_id": request.call_id,
            }

            # 通过批处理调度器提交请求
            if self.batch_scheduler:
                # 异步提交到批处理队列
                await self.batch_scheduler.submit_request(
                    request_id=request.call_id,
                    source_module=caller_module,
                    prompt=vllm_request["prompt"],
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                )

                # 等待批处理结果（简化实现）
                await asyncio.sleep(0.1)  # 等待批处理完成

                # 模拟vLLM批处理结果
                content = f"[vLLM批处理响应] {caller_module}模块请求处理完成"
                tokens_used = min(request.max_tokens, 200)

                self.call_stats["batch_calls"] += 1

            else:
                # 直接调用vLLM引擎
                result = await self.vllm_engine.generate_async(  # pylint: disable=e1123,e1120
                    prompt=vllm_request["prompt"],
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    caller_module=caller_module,
                )

                content = result.get("text", "")
                tokens_used = result.get("tokens_used", 0)

            latency = (time.perf_counter() - start_time) * 1000

            # 构建响应
            response = LLMResponse(
                call_id=request.call_id,
                success=True,
                content=content,
                latency_ms=latency,
                tokens_used=tokens_used,
                cost=0.0,  # vLLM本地推理无成本
                provider_used=LLMProvider.QWEN_LOCAL,
                model_used="qwen3-30b-moe-vllm",
            )

            self.call_stats["vllm_calls"] += 1

            logger.debug(  # pylint: disable=logging-fstring-interpolation
                f"[LLMGateway] vLLM调用完成: {request.call_id}, 延迟: {latency:.2f}ms"
            )  # pylint: disable=logging-fstring-interpolation

            return response

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LLMGateway] vLLM调用失败: {e}")  # pylint: disable=logging-fstring-interpolation
            # 回退到传统调用
            logger.info(
                f"[LLMGateway] 回退到传统LLM调用: {request.call_id}"
            )  # pylint: disable=logging-fstring-interpolation
            return await self._execute_traditional_llm_call(request)

    def _build_vllm_prompt(self, request: LLMRequest) -> str:
        """构建vLLM提示

        Args:
            request: LLM请求

        Returns:
            str: 格式化的提示
        """
        # 系统提示
        system_prompt = request.system_prompt or self._get_default_system_prompt(request.call_type)

        # 构建对话历史
        conversation = []

        if system_prompt:
            conversation.append(f"System: {system_prompt}")

        for message in request.messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                conversation.append(f"System: {content}")
            elif role == "user":
                conversation.append(f"Human: {content}")
            elif role == "assistant":
                conversation.append(f"Assistant: {content}")

        # 添加Assistant提示
        conversation.append("Assistant:")

        return "\n\n".join(conversation)

    async def _execute_traditional_llm_call(self, request: LLMRequest) -> LLMResponse:
        """执行传统LLM调用（原有逻辑）"""
        # 选择最佳提供商
        provider = await self._select_best_provider(request)

        # 获取客户端
        client = self.llm_clients.get(provider)
        if not client:
            raise ResourceError(f"LLM客户端未初始化: {provider}")

        # 执行调用
        start_time = time.perf_counter()

        if provider == LLMProvider.QWEN_LOCAL:
            result = await self._call_qwen_local(client, request)
        elif provider == LLMProvider.QWEN_CLOUD:
            result = await self._call_qwen_cloud(client, request)
        elif provider == LLMProvider.DEEPSEEK:
            result = await self._call_deepseek(client, request)
        elif provider == LLMProvider.GLM:
            result = await self._call_glm(client, request)
        else:
            raise ResourceError(f"不支持的LLM提供商: {provider}")

        latency = (time.perf_counter() - start_time) * 1000

        # 构建响应
        response = LLMResponse(
            call_id=request.call_id,
            success=True,
            content=result["content"],
            latency_ms=latency,
            tokens_used=result.get("tokens_used", 0),
            cost=result.get("cost", 0.0),
            provider_used=provider,
            model_used=result.get("model_used", request.model),
        )

        return response

    async def _filter_hallucination(self, response: LLMResponse, request: LLMRequest) -> LLMResponse:
        """防幻觉检测和过滤"""
        if not request.enable_hallucination_filter or not response.success:
            return response

        try:
            # 构建检测上下文
            context = {
                "call_type": request.call_type.value,
                "business_context": request.business_context,
                "messages": request.messages,
                "historical_accuracy": await self._get_historical_accuracy(request.caller_module),
            }

            # 执行幻觉检测
            detection_result = self.hallucination_filter.detect_hallucination(response.content, context)

            # 更新响应
            response.hallucination_score = detection_result["confidence"]
            response.quality_score = 1.0 - detection_result["confidence"]

            # 如果检测到幻觉
            if detection_result["is_hallucination"]:
                logger.warning(  # pylint: disable=logging-fstring-interpolation
                    f"检测到幻觉: {request.call_id}, 置信度: {detection_result['confidence']:.3f}"
                )  # pylint: disable=logging-fstring-interpolation

                # 记录幻觉
                self.call_stats["hallucination_detected"] += 1

                # 根据严重程度处理
                if detection_result["confidence"] > 0.8:
                    # 严重幻觉：拒绝响应
                    response.success = False
                    response.error_message = f"检测到严重幻觉 (置信度: {detection_result['confidence']:.3f})"
                    response.error_code = "HALLUCINATION_DETECTED"
                elif detection_result["confidence"] > 0.6:
                    # 中等幻觉：添加警告
                    response.content = f"⚠️ 警告：此响应可能包含不准确信息 (幻觉置信度: {detection_result['confidence']:.3f})\n\n{response.content}"  # pylint: disable=line-too-long

                # 记录到审计日志
                response.audit_log["hallucination_detection"] = detection_result

            return response

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"幻觉检测失败: {e}")  # pylint: disable=logging-fstring-interpolation
            # 检测失败时，降低质量评分但不阻止响应
            response.quality_score = 0.5
            return response

    async def _update_memory(self, request: LLMRequest, response: LLMResponse) -> None:
        """更新记忆系统"""
        if not request.use_memory or not response.success:
            return

        try:
            # 构建记忆条目
            memory_entry = {
                "call_id": request.call_id,
                "call_type": request.call_type.value,
                "caller_module": request.caller_module,
                "caller_function": request.caller_function,
                "request_summary": self._summarize_request(request),
                "response_summary": self._summarize_response(response),
                "business_context": request.business_context,
                "quality_score": response.quality_score,
                "timestamp": datetime.now().isoformat(),
                "success": response.success,
            }

            # 更新Engram记忆
            await self.memory_system.engram_memory.store_memory(
                text=json.dumps(memory_entry),
                context=memory_entry,
                importance=self._calculate_importance(request, response),
            )

            # 更新传统记忆
            await self.memory_system.add_to_memory(
                memory_type="episodic", content=memory_entry, importance=self._calculate_importance(request, response)
            )

            response.memory_updates = 1
            logger.debug(f"记忆系统更新完成: {request.call_id}")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"记忆系统更新失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def _calculate_importance(self, request: LLMRequest, response: LLMResponse) -> float:
        """计算记忆重要性"""
        importance = 0.5  # 基础重要性

        # 根据调用类型调整
        type_weights = {
            CallType.TRADING_DECISION: 0.9,
            CallType.STRATEGY_ANALYSIS: 0.8,
            CallType.RISK_ASSESSMENT: 0.8,
            CallType.RESEARCH_ANALYSIS: 0.7,
            CallType.FACTOR_GENERATION: 0.7,
            CallType.DATA_ANALYSIS: 0.6,
            CallType.CODE_GENERATION: 0.5,
            CallType.MARKET_SENTIMENT: 0.6,
        }

        importance *= type_weights.get(request.call_type, 0.5)

        # 根据质量调整
        importance *= response.quality_score

        # 根据成功状态调整
        if not response.success:
            importance *= 0.3

        return min(max(importance, 0.0), 1.0)

    def _initialize_llm_clients(self) -> None:
        """初始化LLM客户端"""
        # 这里应该初始化各种LLM客户端
        # 为了演示，使用模拟客户端
        self.llm_clients = {
            LLMProvider.QWEN_LOCAL: "qwen_local_client",
            LLMProvider.QWEN_CLOUD: "qwen_cloud_client",
            LLMProvider.DEEPSEEK: "deepseek_client",
            LLMProvider.GLM: "glm_client",
        }

        logger.info("LLM客户端池初始化完成")

    async def _select_best_provider(self, request: LLMRequest) -> LLMProvider:
        """选择最佳LLM提供商"""
        # 简化版本：直接返回请求中指定的提供商
        # 实际实现应该考虑可用性、成本、性能等因素
        return request.provider

    def _estimate_cost(self, request: LLMRequest) -> float:
        """估算调用成本"""
        # 简化的成本估算
        token_estimate = len(str(request.messages)) * 1.3  # 估算token数

        cost_per_1k_tokens = {
            LLMProvider.QWEN_LOCAL: 0.0,  # 本地免费
            LLMProvider.QWEN_CLOUD: 0.001,  # ¥0.001/1K tokens
            LLMProvider.DEEPSEEK: 0.0005,  # ¥0.0005/1K tokens
            LLMProvider.GLM: 0.0008,  # ¥0.0008/1K tokens
        }

        rate = cost_per_1k_tokens.get(request.provider, 0.001)
        return (token_estimate / 1000) * rate

    async def _call_qwen_local(self, client, request: LLMRequest) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """调用本地Qwen模型"""
        # 模拟本地调用
        await asyncio.sleep(0.02)  # 模拟20ms延迟

        return {
            "content": f"[本地Qwen响应] 基于请求: {request.messages[-1]['content'][:50]}...",
            "tokens_used": 150,
            "cost": 0.0,
            "model_used": "qwen3-30b-moe-local",
        }

    async def _call_qwen_cloud(self, client, request: LLMRequest) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """调用云端Qwen模型"""
        # 模拟云端调用
        await asyncio.sleep(0.5)  # 模拟500ms延迟

        return {
            "content": f"[云端Qwen响应] 基于请求: {request.messages[-1]['content'][:50]}...",
            "tokens_used": 200,
            "cost": 0.002,
            "model_used": "qwen3-next-80b",
        }

    async def _call_deepseek(self, client, request: LLMRequest) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """调用DeepSeek模型"""
        # 模拟DeepSeek调用
        await asyncio.sleep(0.3)  # 模拟300ms延迟

        return {
            "content": f"[DeepSeek响应] 基于请求: {request.messages[-1]['content'][:50]}...",
            "tokens_used": 180,
            "cost": 0.0009,
            "model_used": "deepseek-chat",
        }

    async def _call_glm(self, client, request: LLMRequest) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """调用GLM模型"""
        # 模拟GLM调用
        await asyncio.sleep(0.4)  # 模拟400ms延迟

        return {
            "content": f"[GLM响应] 基于请求: {request.messages[-1]['content'][:50]}...",
            "tokens_used": 160,
            "cost": 0.0013,
            "model_used": "glm-4",
        }

    def _summarize_request(self, request: LLMRequest) -> str:
        """总结请求内容"""
        if not request.messages:
            return "空请求"

        last_message = request.messages[-1]["content"]
        return last_message[:100] + "..." if len(last_message) > 100 else last_message

    def _summarize_response(self, response: LLMResponse) -> str:
        """总结响应内容"""
        if not response.content:
            return "空响应"

        return response.content[:100] + "..." if len(response.content) > 100 else response.content

    async def _get_historical_accuracy(self, caller_module: str) -> float:
        """获取历史准确率"""
        try:
            # 从Redis获取历史准确率
            key = f"llm_accuracy:{caller_module}"
            accuracy = self.redis_client.get(key)
            return float(accuracy) if accuracy else 0.7  # 默认70%
        except:  # pylint: disable=w0702
            return 0.7

    async def _record_cost(self, request: LLMRequest, response: LLMResponse) -> None:
        """记录成本"""
        try:
            await self.cost_tracker.record_cost(
                call_id=request.call_id,
                provider=response.provider_used.value,
                model=response.model_used,
                tokens=response.tokens_used,
                cost=response.cost,
                call_type=request.call_type.value,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"成本记录失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _record_performance(self, request: LLMRequest, response: LLMResponse, latency: float) -> None:
        """记录性能指标"""
        try:
            await self.performance_monitor.record_call(
                call_id=request.call_id,
                provider=response.provider_used.value,
                latency_ms=latency,
                success=response.success,
                quality_score=response.quality_score,
                call_type=request.call_type.value,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"性能记录失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _log_audit(self, request: LLMRequest, response: LLMResponse) -> None:
        """记录审计日志"""
        try:
            audit_entry = {
                "call_id": request.call_id,
                "timestamp": datetime.now().isoformat(),
                "caller_module": request.caller_module,
                "caller_function": request.caller_function,
                "call_type": request.call_type.value,
                "provider": response.provider_used.value,
                "model": response.model_used,
                "success": response.success,
                "latency_ms": response.latency_ms,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "quality_score": response.quality_score,
                "hallucination_score": response.hallucination_score,
                "request_summary": self._summarize_request(request),
                "response_summary": self._summarize_response(response),
            }

            # 存储到Redis
            key = f"llm_audit:{datetime.now().strftime('%Y%m%d')}:{request.call_id}"
            self.redis_client.setex(key, 86400 * 7, json.dumps(audit_entry))  # 保存7天

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"审计日志记录失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _log_error(
        self, request: LLMRequest, response: LLMResponse, error: Exception  # pylint: disable=unused-argument
    ) -> None:  # pylint: disable=unused-argument
        """记录错误日志"""
        try:
            error_entry = {
                "call_id": request.call_id,
                "timestamp": datetime.now().isoformat(),
                "caller_module": request.caller_module,
                "caller_function": request.caller_function,
                "call_type": request.call_type.value,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "request_summary": self._summarize_request(request),
            }

            # 存储到Redis
            key = f"llm_error:{datetime.now().strftime('%Y%m%d')}:{request.call_id}"
            self.redis_client.setex(key, 86400 * 30, json.dumps(error_entry))  # 保存30天

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"错误日志记录失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def _update_stats(self, response: LLMResponse) -> None:
        """更新统计信息"""
        self.call_stats["total_calls"] += 1

        if response.success:
            self.call_stats["successful_calls"] += 1
        else:
            self.call_stats["failed_calls"] += 1

    async def generate_cloud(  # pylint: disable=too-many-positional-arguments
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        call_type: CallType = CallType.STRATEGY_ANALYSIS,
        caller_module: str = "unknown",
        caller_function: str = "unknown",
    ) -> str:
        """生成云端响应 - 兼容接口

        白皮书依据: 第二章 2.1 AI三脑架构 - vLLM集成
        需求: 8.2, 8.8 - vLLM集成到AI三脑

        Args:
            prompt: 提示文本
            temperature: 温度参数
            max_tokens: 最大token数
            call_type: 调用类型
            caller_module: 调用模块
            caller_function: 调用函数

        Returns:
            str: 生成的响应文本
        """
        try:
            # 构建LLM请求
            request = LLMRequest(
                call_type=call_type,
                provider=LLMProvider.QWEN_CLOUD,  # 默认使用云端
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                caller_module=caller_module,
                caller_function=caller_function,
            )

            # 执行调用
            response = await self.call_llm(request)

            if response.success:  # pylint: disable=no-else-return
                return response.content
            else:
                logger.error(  # pylint: disable=logging-fstring-interpolation
                    f"[LLMGateway] Cloud generation failed: {response.error_message}"
                )  # pylint: disable=logging-fstring-interpolation
                return f"生成失败: {response.error_message}"

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LLMGateway] Cloud generation error: {e}")  # pylint: disable=logging-fstring-interpolation
            return f"生成错误: {str(e)}"

    async def generate_local(  # pylint: disable=too-many-positional-arguments
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        call_type: CallType = CallType.TRADING_DECISION,
        caller_module: str = "soldier",
        caller_function: str = "decide",
    ) -> str:
        """生成本地响应 - vLLM优化

        白皮书依据: 第二章 2.1 AI三脑架构 - vLLM本地推理
        需求: 8.2, 8.8 - vLLM集成优化

        Args:
            prompt: 提示文本
            temperature: 温度参数
            max_tokens: 最大token数
            call_type: 调用类型
            caller_module: 调用模块
            caller_function: 调用函数

        Returns:
            str: 生成的响应文本
        """
        try:
            # 构建LLM请求
            request = LLMRequest(
                call_type=call_type,
                provider=LLMProvider.QWEN_LOCAL,  # 强制使用本地vLLM
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                caller_module=caller_module,
                caller_function=caller_function,
            )

            # 执行调用
            response = await self.call_llm(request)

            if response.success:  # pylint: disable=no-else-return
                return response.content
            else:
                logger.error(  # pylint: disable=logging-fstring-interpolation
                    f"[LLMGateway] Local generation failed: {response.error_message}"
                )  # pylint: disable=logging-fstring-interpolation
                return f"生成失败: {response.error_message}"

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LLMGateway] Local generation error: {e}")  # pylint: disable=logging-fstring-interpolation
            return f"生成错误: {str(e)}"

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        白皮书依据: 第七章 7.6 LLM调用优化
        需求: 7.6 - 性能监控和统计

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        stats = {
            **self.call_stats,
            "success_rate": self.call_stats["successful_calls"] / max(self.call_stats["total_calls"], 1),
            "hallucination_rate": self.call_stats["hallucination_detected"] / max(self.call_stats["total_calls"], 1),
            "vllm_usage_rate": self.call_stats["vllm_calls"] / max(self.call_stats["total_calls"], 1),
            "batch_usage_rate": self.call_stats["batch_calls"] / max(self.call_stats["total_calls"], 1),
            "retry_rate": self.call_stats["retries"] / max(self.call_stats["total_calls"], 1),
            "timeout_rate": self.call_stats["timeouts"] / max(self.call_stats["total_calls"], 1),
            "concurrent_limit_rate": self.call_stats["concurrent_limit_hits"] / max(self.call_stats["total_calls"], 1),
            "avg_retries_per_call": self.call_stats["retries"] / max(self.call_stats["total_calls"], 1),
        }

        # 添加vLLM和批处理调度器统计
        if self.vllm_engine:
            stats["vllm_engine_stats"] = self.vllm_engine.get_stats()

        if self.batch_scheduler:
            stats["batch_scheduler_stats"] = self.batch_scheduler.get_statistics()

        return stats


# 辅助类定义
class CostTracker:
    """成本追踪器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def record_cost(  # pylint: disable=too-many-positional-arguments
        self, call_id: str, provider: str, model: str, tokens: int, cost: float, call_type: str
    ) -> None:
        """记录成本"""
        # 实现成本记录逻辑


class BudgetManager:
    """预算管理器"""

    def __init__(self, daily_budget: float, monthly_budget: float):
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

    async def check_budget(self, estimated_cost: float) -> bool:  # pylint: disable=unused-argument
        """检查预算"""
        # 实现预算检查逻辑
        return True  # 简化实现


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def record_call(  # pylint: disable=too-many-positional-arguments
        self, call_id: str, provider: str, latency_ms: float, success: bool, quality_score: float, call_type: str
    ) -> None:
        """记录调用性能"""
        # 实现性能记录逻辑
