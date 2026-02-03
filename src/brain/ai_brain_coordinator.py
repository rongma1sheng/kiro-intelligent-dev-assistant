# pylint: disable=too-many-lines
"""
AI三脑协调器 - 解决循环依赖的核心组件

白皮书依据: 第二章 2.1 AI三脑架构 + 架构审计报告循环依赖修复
通过事件驱动架构和依赖注入，彻底解决Soldier/Commander/Scholar之间的循环依赖
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from ..core.dependency_container import DIContainer, get_container
from ..infra.event_bus import Event, EventBus, EventPriority, EventType, get_event_bus
from .interfaces import ICommanderEngine, IScholarEngine, ISoldierEngine


@dataclass
class BrainDecision:
    """AI三脑决策结果"""

    decision_id: str
    primary_brain: str  # soldier/commander/scholar
    action: str
    confidence: float
    reasoning: str
    supporting_data: Dict[str, Any]
    timestamp: datetime
    correlation_id: str


class AIBrainCoordinator:  # pylint: disable=too-many-instance-attributes
    """AI三脑协调器

    白皮书依据: 第二章 2.1 AI三脑架构
    架构审计修复: 解决AI三脑循环依赖问题

    核心功能:
    1. 协调三个AI大脑的工作流程
    2. 通过事件总线实现解耦通信
    3. 管理决策优先级和冲突解决
    4. 提供统一的对外接口

    解决的循环依赖:
    - 原问题: Soldier → Commander → Scholar → Soldier (循环调用)
    - 解决方案: 通过事件总线异步通信，各脑独立工作
    """

    def __init__(self, event_bus: EventBus, container: DIContainer):
        self.event_bus = event_bus
        self.container = container

        # 三脑实例 (通过依赖注入获取)
        self.soldier: Optional[ISoldierEngine] = None
        self.commander: Optional[ICommanderEngine] = None
        self.scholar: Optional[IScholarEngine] = None

        # 决策历史
        self.decision_history: List[BrainDecision] = []
        self.max_history = 1000

        # 协调状态
        self.coordination_active = False
        self.pending_decisions: Dict[str, BrainDecision] = {}

        # Task 14.7: 并发决策处理
        self.max_concurrent_decisions = 20  # 最大并发决策数
        self.concurrent_semaphore = asyncio.Semaphore(self.max_concurrent_decisions)
        self.decision_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        # Task 14.7: vLLM批处理优化
        self.enable_batch_processing = True  # 启用批处理
        self.batch_size = 5  # 批处理大小
        self.batch_timeout = 0.1  # 批处理超时（秒）
        self.pending_batch: List[Tuple[Dict[str, Any], str, asyncio.Future]] = []
        self.batch_lock = asyncio.Lock()

        # 统计信息
        self.stats = {
            "total_decisions": 0,
            "soldier_decisions": 0,
            "commander_decisions": 0,
            "scholar_decisions": 0,
            "coordination_conflicts": 0,
            "concurrent_decisions": 0,
            "batch_decisions": 0,
            "concurrent_limit_hits": 0,
            "queue_full_hits": 0,
            "start_time": datetime.now(),
        }

    async def initialize(self):
        """初始化协调器"""
        try:
            # 解析AI三脑实例
            if self.container.is_registered(ISoldierEngine):
                self.soldier = self.container.resolve(ISoldierEngine)

            if self.container.is_registered(ICommanderEngine):
                self.commander = self.container.resolve(ICommanderEngine)

            if self.container.is_registered(IScholarEngine):
                self.scholar = self.container.resolve(IScholarEngine)

            # 订阅事件
            await self._setup_event_subscriptions()

            self.coordination_active = True
            logger.info("[AIBrainCoordinator] Initialized successfully")

        except Exception as e:
            logger.error(f"[AIBrainCoordinator] Initialization failed: {e}")
            raise

    async def _setup_event_subscriptions(self):
        """设置事件订阅"""
        # 订阅各脑的决策事件
        await self.event_bus.subscribe(
            EventType.DECISION_MADE, self._handle_brain_decision, "coordinator_decision_handler"
        )

        # 订阅分析完成事件
        await self.event_bus.subscribe(
            EventType.ANALYSIS_COMPLETED, self._handle_analysis_completed, "coordinator_analysis_handler"
        )

        # 订阅因子发现事件
        await self.event_bus.subscribe(
            EventType.FACTOR_DISCOVERED, self._handle_factor_discovered, "coordinator_factor_handler"
        )

        logger.debug("[AIBrainCoordinator] Event subscriptions setup completed")

    async def request_decision(self, context: Dict[str, Any], primary_brain: str = "soldier") -> BrainDecision:
        """请求AI决策 - 实现决策路由机制（Task 14.7增强版）

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.1, 3.2, 3.3 - 决策路由机制、超时处理、备用决策
        需求: 7.7 - 并发决策处理、vLLM批处理优化

        Args:
            context: 决策上下文
            primary_brain: 主要决策脑 (soldier/commander/scholar)

        Returns:
            BrainDecision: 决策结果

        Raises:
            ValueError: 当primary_brain不支持时
        """
        # Task 14.7: 并发控制
        async with self.concurrent_semaphore:
            # 检查是否达到并发限制
            if self.concurrent_semaphore.locked():
                self.stats["concurrent_limit_hits"] += 1
                logger.warning(f"[AIBrainCoordinator] 达到并发限制: {self.max_concurrent_decisions}")

            self.stats["concurrent_decisions"] += 1

            # 执行决策请求
            return await self._execute_decision_request(context, primary_brain)

    async def _execute_decision_request(self, context: Dict[str, Any], primary_brain: str) -> BrainDecision:
        """执行决策请求 - 内部实现

        Args:
            context: 决策上下文
            primary_brain: 主要决策脑

        Returns:
            BrainDecision: 决策结果
        """
        # 验证primary_brain参数
        valid_brains = ["soldier", "commander", "scholar"]
        if primary_brain not in valid_brains:
            raise ValueError(f"不支持的决策脑: {primary_brain}，支持的类型: {valid_brains}")

        try:
            # 生成correlation_id
            correlation_id = self._generate_correlation_id()

            logger.info(f"[AIBrainCoordinator] 开始决策请求: brain={primary_brain}, correlation_id={correlation_id}")

            # Task 14.7: 批处理优化
            if self.enable_batch_processing and primary_brain in ["commander", "scholar"]:
                # Commander和Scholar适合批处理
                decision = await self._request_decision_with_batch(context, primary_brain, correlation_id)
            else:
                # Soldier需要低延迟，不使用批处理
                decision = await self._request_decision_direct(context, primary_brain, correlation_id)

            if decision:  # pylint: disable=no-else-return
                # 决策成功
                self._add_to_history(decision)
                self.stats["total_decisions"] += 1
                self.stats[f"{primary_brain}_decisions"] += 1

                logger.info(
                    f"[AIBrainCoordinator] 决策完成: {decision.action} "
                    f"(confidence: {decision.confidence:.2f}, brain: {primary_brain})"
                )
                return decision
            else:
                # 超时处理 - 生成备用决策
                logger.warning(f"[AIBrainCoordinator] 决策超时，生成备用决策: correlation_id={correlation_id}")
                fallback_decision = self._create_fallback_decision(context, correlation_id, primary_brain)

                # 记录超时统计
                self.stats["total_decisions"] += 1
                self.stats.setdefault("timeout_decisions", 0)
                self.stats["timeout_decisions"] += 1

                return fallback_decision

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AIBrainCoordinator] 决策请求失败: {e}")
            error_correlation_id = f"error_{datetime.now().timestamp()}"

            # 记录错误统计
            self.stats.setdefault("error_decisions", 0)
            self.stats["error_decisions"] += 1

            return self._create_fallback_decision(context, error_correlation_id, primary_brain)

    async def _request_decision_direct(
        self, context: Dict[str, Any], primary_brain: str, correlation_id: str
    ) -> Optional[BrainDecision]:
        """直接请求决策 - 不使用批处理

        Args:
            context: 决策上下文
            primary_brain: 主要决策脑
            correlation_id: 关联ID

        Returns:
            Optional[BrainDecision]: 决策结果
        """
        # 优先直接调用已注入的AI脑实例（避免事件超时）
        if primary_brain == "soldier" and self.soldier:
            try:
                result = await self.soldier.decide(context)
                # 将Soldier返回的dict转换为BrainDecision
                decision_data = result.get("decision", {})
                return BrainDecision(
                    decision_id=f"soldier_{datetime.now().timestamp()}",
                    primary_brain="soldier",
                    action=decision_data.get("action", "hold"),
                    confidence=decision_data.get("confidence", 0.5),
                    reasoning=decision_data.get("reasoning", ""),
                    supporting_data=result.get("metadata", {}),
                    timestamp=datetime.now(),
                    correlation_id=correlation_id,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[AIBrainCoordinator] Soldier直接调用失败: {e}, 回退到事件模式")

        elif primary_brain == "commander" and self.commander:
            try:
                result = await self.commander.analyze(context)
                return BrainDecision(
                    decision_id=f"commander_{datetime.now().timestamp()}",
                    primary_brain="commander",
                    action=result.get("recommendation", "hold"),
                    confidence=result.get("confidence", 0.5),
                    reasoning=result.get("analysis", ""),
                    supporting_data=result,
                    timestamp=datetime.now(),
                    correlation_id=correlation_id,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[AIBrainCoordinator] Commander直接调用失败: {e}, 回退到事件模式")

        elif primary_brain == "scholar" and self.scholar:
            try:
                result = await self.scholar.research(context)
                return BrainDecision(
                    decision_id=f"scholar_{datetime.now().timestamp()}",
                    primary_brain="scholar",
                    action=result.get("recommendation", "hold"),
                    confidence=result.get("confidence", 0.5),
                    reasoning=result.get("research_summary", ""),
                    supporting_data=result,
                    timestamp=datetime.now(),
                    correlation_id=correlation_id,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[AIBrainCoordinator] Scholar直接调用失败: {e}, 回退到事件模式")

        # 回退到事件模式
        # 发布决策请求事件
        try:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.DECISION_REQUEST,
                    source_module="coordinator",
                    target_module=primary_brain,
                    priority=EventPriority.HIGH,
                    data={
                        "action": "request_decision",
                        "context": context,
                        "correlation_id": correlation_id,
                        "primary_brain": primary_brain,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AIBrainCoordinator] 事件发布失败: {e}")
            return None

        # 等待决策结果 (超时处理: 5秒)
        decision = await self._wait_for_decision(correlation_id, timeout=5.0)

        return decision

    async def _request_decision_with_batch(
        self, context: Dict[str, Any], primary_brain: str, correlation_id: str
    ) -> Optional[BrainDecision]:
        """使用批处理请求决策 - vLLM优化

        白皮书依据: 第二章 2.1 AI三脑协调 - vLLM批处理优化
        需求: 7.7 - vLLM批处理优化

        Args:
            context: 决策上下文
            primary_brain: 主要决策脑
            correlation_id: 关联ID

        Returns:
            Optional[BrainDecision]: 决策结果
        """
        # 创建Future用于等待批处理结果
        future: asyncio.Future = asyncio.Future()

        should_process = False
        async with self.batch_lock:
            # 添加到批处理队列
            self.pending_batch.append((context, primary_brain, correlation_id, future))

            logger.debug(
                f"[AIBrainCoordinator] 添加到批处理队列: {correlation_id}, 队列大小: {len(self.pending_batch)}"
            )

            # 检查是否达到批处理大小
            should_process = len(self.pending_batch) >= self.batch_size

        # 在锁外处理批次
        if should_process:
            await self._process_batch()

        # 等待批处理结果
        try:
            decision = await asyncio.wait_for(future, timeout=5.0)
            self.stats["batch_decisions"] += 1
            return decision
        except asyncio.TimeoutError:
            logger.warning(f"[AIBrainCoordinator] 批处理决策超时: {correlation_id}")
            return None

    async def _process_batch(self):
        """处理批处理队列 - vLLM批处理优化

        白皮书依据: 第二章 2.1 AI三脑协调 - vLLM批处理
        需求: 7.7 - vLLM批处理优化
        """
        # 获取当前批次（需要加锁）
        async with self.batch_lock:
            if not self.pending_batch:
                return

            batch = self.pending_batch.copy()
            self.pending_batch.clear()

        logger.info(f"[AIBrainCoordinator] 处理批处理: 批次大小={len(batch)}")

        # 并发处理批次中的所有请求
        tasks = []
        for context, primary_brain, correlation_id, future in batch:
            task = self._process_batch_item(context, primary_brain, correlation_id, future)
            tasks.append(task)

        # 并发执行所有任务
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_batch_item(
        self, context: Dict[str, Any], primary_brain: str, correlation_id: str, future: asyncio.Future
    ):
        """处理批处理中的单个项目

        Args:
            context: 决策上下文
            primary_brain: 主要决策脑
            correlation_id: 关联ID
            future: 用于返回结果的Future
        """
        try:
            # 发布决策请求事件
            await self.event_bus.publish(
                Event(
                    event_type=EventType.DECISION_REQUEST,
                    source_module="coordinator",
                    target_module=primary_brain,
                    priority=EventPriority.NORMAL,  # 批处理使用普通优先级
                    data={
                        "action": "request_decision",
                        "context": context,
                        "correlation_id": correlation_id,
                        "primary_brain": primary_brain,
                        "batch_processing": True,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            )

            # 等待决策结果
            decision = await self._wait_for_decision(correlation_id, timeout=5.0)

            # 设置Future结果
            if not future.done():
                if decision:
                    future.set_result(decision)
                else:
                    future.set_result(None)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AIBrainCoordinator] 批处理项目失败: {correlation_id}, 错误: {e}")
            if not future.done():
                future.set_exception(e)

    async def request_decisions_batch(self, requests: List[Tuple[Dict[str, Any], str]]) -> List[BrainDecision]:
        """批量请求决策 - 并发处理多个决策请求

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 7.7 - 并发决策处理

        Args:
            requests: 决策请求列表，每个元素为(context, primary_brain)元组

        Returns:
            List[BrainDecision]: 决策结果列表
        """
        logger.info(f"[AIBrainCoordinator] 批量决策请求: 数量={len(requests)}")

        # 并发处理所有请求
        tasks = [self.request_decision(context, primary_brain) for context, primary_brain in requests]

        # 等待所有任务完成
        decisions = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        valid_decisions = []
        for i, decision in enumerate(decisions):
            if isinstance(decision, Exception):
                logger.error(f"[AIBrainCoordinator] 批量决策失败: 索引={i}, 错误={decision}")
                # 生成备用决策
                context, primary_brain = requests[i]
                fallback = self._create_fallback_decision(context, f"batch_error_{i}", primary_brain)
                valid_decisions.append(fallback)
            else:
                valid_decisions.append(decision)

        logger.info(f"[AIBrainCoordinator] 批量决策完成: 成功={len(valid_decisions)}/{len(requests)}")

        return valid_decisions

    def _generate_correlation_id(self) -> str:
        """生成correlation_id

        Returns:
            str: 唯一的correlation_id
        """
        timestamp = datetime.now().timestamp()
        return f"decision_{timestamp}_{id(self)}"

    async def _wait_for_decision(self, correlation_id: str, timeout: float) -> Optional[BrainDecision]:
        """等待决策结果 - 异步等待机制

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.2, 3.3 - 异步等待、超时处理

        Args:
            correlation_id: 关联ID
            timeout: 超时时间（秒）

        Returns:
            Optional[BrainDecision]: 决策结果，超时返回None
        """
        start_time = asyncio.get_event_loop().time()
        check_interval = 0.05  # 50ms检查间隔，确保响应性

        logger.debug(f"[AIBrainCoordinator] 等待决策结果: correlation_id={correlation_id}, timeout={timeout}s")

        while asyncio.get_event_loop().time() - start_time < timeout:
            # 检查是否有对应的决策结果
            if correlation_id in self.pending_decisions:
                decision = self.pending_decisions.pop(correlation_id)
                elapsed = asyncio.get_event_loop().time() - start_time

                logger.debug(
                    f"[AIBrainCoordinator] 收到决策结果: correlation_id={correlation_id}, elapsed={elapsed:.3f}s"
                )
                return decision

            # 异步等待，不阻塞事件循环
            await asyncio.sleep(check_interval)

        # 超时处理
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.warning(f"[AIBrainCoordinator] 决策等待超时: correlation_id={correlation_id}, elapsed={elapsed:.3f}s")

        # 清理可能的残留决策
        self.pending_decisions.pop(correlation_id, None)

        return None

    async def _handle_brain_decision(self, event: Event):
        """处理AI脑决策事件"""
        try:
            data = event.data

            if data.get("action") == "decision_result":
                # 创建决策对象
                decision = BrainDecision(
                    decision_id=data.get("decision_id", ""),
                    primary_brain=data.get("primary_brain", "unknown"),
                    action=data.get("decision_action", "hold"),
                    confidence=data.get("confidence", 0.0),
                    reasoning=data.get("reasoning", ""),
                    supporting_data=data.get("supporting_data", {}),
                    timestamp=datetime.now(),
                    correlation_id=data.get("correlation_id", ""),
                )

                # 存储待处理决策
                correlation_id = decision.correlation_id
                if correlation_id:
                    self.pending_decisions[correlation_id] = decision

                logger.debug(f"[AIBrainCoordinator] Received decision from {decision.primary_brain}: {decision.action}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AIBrainCoordinator] Failed to handle brain decision: {e}")

    async def _handle_analysis_completed(self, event: Event):
        """处理分析完成事件"""
        try:
            data = event.data
            analysis_type = data.get("analysis_type", "unknown")

            logger.debug(f"[AIBrainCoordinator] Analysis completed: {analysis_type}")

            # 根据分析类型触发相应的后续动作
            if analysis_type == "market_analysis":
                # 市场分析完成，可以触发策略调整
                await self._trigger_strategy_adjustment(data)
            elif analysis_type == "factor_analysis":
                # 因子分析完成，可以触发因子验证
                await self._trigger_factor_validation(data)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AIBrainCoordinator] Failed to handle analysis completed: {e}")

    async def _handle_factor_discovered(self, event: Event):
        """处理因子发现事件"""
        try:
            data = event.data
            factor_info = data.get("factor_info", {})

            logger.info(f"[AIBrainCoordinator] Factor discovered: {factor_info.get('name', 'unknown')}")

            # 触发因子验证流程
            await self.event_bus.publish(
                Event(
                    event_type=EventType.ANALYSIS_COMPLETED,
                    source_module="coordinator",
                    target_module="auditor",
                    priority=EventPriority.NORMAL,
                    data={"action": "validate_factor", "factor_info": factor_info, "source": "scholar_discovery"},
                )
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[AIBrainCoordinator] Failed to handle factor discovered: {e}")

    async def _trigger_strategy_adjustment(self, analysis_data: Dict[str, Any]):
        """触发策略调整"""
        await self.event_bus.publish(
            Event(
                event_type=EventType.ANALYSIS_COMPLETED,
                source_module="coordinator",
                target_module="commander",
                priority=EventPriority.HIGH,
                data={
                    "action": "adjust_strategy",
                    "analysis_data": analysis_data,
                    "trigger": "market_analysis_completed",
                },
            )
        )

    async def _trigger_factor_validation(self, analysis_data: Dict[str, Any]):
        """触发因子验证"""
        await self.event_bus.publish(
            Event(
                event_type=EventType.ANALYSIS_COMPLETED,
                source_module="coordinator",
                target_module="auditor",
                priority=EventPriority.NORMAL,
                data={
                    "action": "validate_factor",
                    "analysis_data": analysis_data,
                    "trigger": "factor_analysis_completed",
                },
            )
        )

    def _create_fallback_decision(
        self, context: Dict[str, Any], correlation_id: str, primary_brain: str = "coordinator"
    ) -> BrainDecision:
        """创建备用决策 - 超时和错误时的保守策略

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.3 - 备用决策生成

        Args:
            context: 决策上下文
            correlation_id: 关联ID
            primary_brain: 原始决策脑

        Returns:
            BrainDecision: 备用决策（保守策略）
        """
        # 根据上下文生成保守的备用决策
        fallback_action = "hold"  # 默认保守策略
        fallback_confidence = 0.1  # 低置信度
        fallback_reasoning = "备用决策：由于超时或错误，采用保守策略"

        # 根据上下文调整备用策略
        if context.get("current_position", 0) > 0.8:
            # 如果当前仓位过高，建议减仓
            fallback_action = "reduce"
            fallback_reasoning = "备用决策：当前仓位过高，建议减仓"
            fallback_confidence = 0.3
        elif context.get("risk_level") == "high":
            # 如果风险过高，建议卖出
            fallback_action = "sell"
            fallback_reasoning = "备用决策：风险过高，建议卖出"
            fallback_confidence = 0.4

        decision = BrainDecision(
            decision_id=f"fallback_{datetime.now().timestamp()}",
            primary_brain=f"coordinator_fallback_{primary_brain}",
            action=fallback_action,
            confidence=fallback_confidence,
            reasoning=fallback_reasoning,
            supporting_data={
                "fallback_reason": "timeout_or_error",
                "original_brain": primary_brain,
                "context_summary": {
                    "position": context.get("current_position", 0),
                    "risk_level": context.get("risk_level", "unknown"),
                },
            },
            timestamp=datetime.now(),
            correlation_id=correlation_id,
        )

        logger.info(f"[AIBrainCoordinator] 生成备用决策: {fallback_action} (confidence: {fallback_confidence})")

        # 添加到历史记录
        self._add_to_history(decision)

        return decision

    def _add_to_history(self, decision: BrainDecision):
        """添加到决策历史 - 历史记录管理

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.6 - 决策历史管理（最大1000条限制）

        Args:
            decision: 要添加的决策记录
        """
        self.decision_history.append(decision)

        # 维护最大历史记录限制
        if len(self.decision_history) > self.max_history:
            removed_count = len(self.decision_history) - self.max_history
            self.decision_history = self.decision_history[-self.max_history :]

            logger.debug(f"[AIBrainCoordinator] 历史记录超限，移除 {removed_count} 条旧记录")

        logger.debug(
            f"[AIBrainCoordinator] 添加决策历史: {decision.decision_id} ({len(self.decision_history)}/{self.max_history})"
        )

    def get_decision_history(
        self, limit: Optional[int] = None, brain_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取决策历史记录 - 历史记录查询接口

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.6 - 决策历史管理

        Args:
            limit: 返回记录数限制，None表示返回所有
            brain_filter: 按脑类型过滤 (soldier/commander/scholar)

        Returns:
            List[Dict[str, Any]]: 决策历史记录列表
        """
        history = self.decision_history.copy()

        # 按脑类型过滤
        if brain_filter:
            history = [d for d in history if d.primary_brain.startswith(brain_filter)]

        # 限制返回数量
        if limit:
            history = history[-limit:]

        # 转换为字典格式
        return [
            {
                "decision_id": d.decision_id,
                "primary_brain": d.primary_brain,
                "action": d.action,
                "confidence": d.confidence,
                "reasoning": d.reasoning,
                "timestamp": d.timestamp.isoformat(),
                "correlation_id": d.correlation_id,
                "supporting_data_keys": list(d.supporting_data.keys()) if d.supporting_data else [],
            }
            for d in history
        ]

    async def resolve_conflicts(self, decisions: List[BrainDecision]) -> BrainDecision:
        """冲突解决机制 - 多脑决策冲突处理

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.4 - 冲突解决机制

        优先级规则:
        1. Soldier决策优先 (实时性最高)
        2. Commander决策次之 (战略指导)
        3. Scholar决策最后 (研究支持)

        置信度规则:
        - 如果最高置信度>0.8，直接采用该决策
        - 如果置信度差异<0.1，检测为冲突，采用保守策略
        - 记录冲突日志用于分析

        Args:
            decisions: 多个AI脑的决策列表

        Returns:
            BrainDecision: 解决冲突后的最终决策
        """
        if not decisions:
            logger.warning("[AIBrainCoordinator] 无决策可解决冲突，返回默认决策")
            return self._create_fallback_decision({}, f"no_decisions_{datetime.now().timestamp()}")

        if len(decisions) == 1:
            # 只有一个决策，直接返回
            return decisions[0]

        # 优先级排序
        priority_order = {"soldier": 3, "commander": 2, "scholar": 1}

        def get_priority_score(decision: BrainDecision) -> Tuple[int, float]:
            brain_name = decision.primary_brain.split("_")[0]  # 处理 "coordinator_fallback_soldier" 等情况
            priority = priority_order.get(brain_name, 0)
            return (priority, decision.confidence)

        sorted_decisions = sorted(decisions, key=get_priority_score, reverse=True)

        top_decision = sorted_decisions[0]

        logger.info(f"[AIBrainCoordinator] 冲突解决 - 候选决策数: {len(decisions)}")

        # 检查高置信度决策
        if top_decision.confidence > 0.8:
            logger.info(
                f"[AIBrainCoordinator] 高置信度决策采用: {top_decision.action} (confidence: {top_decision.confidence:.2f})"
            )
            return top_decision

        # 检查冲突情况
        if len(sorted_decisions) > 1:
            confidence_diff = abs(sorted_decisions[0].confidence - sorted_decisions[1].confidence)

            if confidence_diff < 0.1:
                # 冲突检测 - 置信度相近
                self.stats["coordination_conflicts"] += 1

                conflict_info = {
                    "decisions": [
                        {"brain": d.primary_brain, "action": d.action, "confidence": d.confidence}
                        for d in sorted_decisions[:3]  # 记录前3个决策
                    ],
                    "confidence_diff": confidence_diff,
                    "timestamp": datetime.now().isoformat(),
                }

                logger.warning(f"[AIBrainCoordinator] 检测到决策冲突: {conflict_info}")

                # 生成保守策略
                conservative_decision = self._create_conservative_decision(decisions)
                return conservative_decision

        # 无冲突，返回最高优先级决策
        logger.info(f"[AIBrainCoordinator] 采用最高优先级决策: {top_decision.primary_brain} - {top_decision.action}")
        return top_decision

    def _create_conservative_decision(self, conflicting_decisions: List[BrainDecision]) -> BrainDecision:
        """生成保守策略 - 冲突时的安全决策

        Args:
            conflicting_decisions: 冲突的决策列表

        Returns:
            BrainDecision: 保守决策
        """
        # 分析冲突决策的行动类型
        actions = [d.action for d in conflicting_decisions]
        confidences = [d.confidence for d in conflicting_decisions]

        # 保守策略逻辑
        if "sell" in actions and "buy" in actions:
            # 买卖冲突 -> 持有
            conservative_action = "hold"
            reasoning = f"买卖决策冲突，采用保守持有策略。冲突决策: {actions}"
        elif all(action in ["buy", "hold"] for action in actions):
            # 都是买入或持有 -> 持有（更保守）
            conservative_action = "hold"
            reasoning = f"买入/持有决策，采用保守持有策略。决策: {actions}"
        elif "reduce" in actions:
            # 有减仓建议 -> 减仓（风险控制）
            conservative_action = "reduce"
            reasoning = f"存在减仓建议，采用风险控制策略。决策: {actions}"
        else:
            # 默认保守策略
            conservative_action = "hold"
            reasoning = f"决策冲突，采用默认保守策略。决策: {actions}"

        # 计算平均置信度，但降低以反映不确定性
        avg_confidence = sum(confidences) / len(confidences) * 0.6  # 降低60%

        decision = BrainDecision(
            decision_id=f"conservative_{datetime.now().timestamp()}",
            primary_brain="coordinator_conflict_resolution",
            action=conservative_action,
            confidence=avg_confidence,
            reasoning=reasoning,
            supporting_data={
                "conflict_resolution": True,
                "conflicting_decisions": [
                    {"brain": d.primary_brain, "action": d.action, "confidence": d.confidence}
                    for d in conflicting_decisions
                ],
                "resolution_strategy": "conservative",
            },
            timestamp=datetime.now(),
            correlation_id=f"conflict_{datetime.now().timestamp()}",
        )

        logger.info(f"[AIBrainCoordinator] 生成保守决策: {conservative_action} (confidence: {avg_confidence:.2f})")

        return decision

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息 - 协调器运行统计（Task 14.7增强版）

        白皮书依据: 第二章 2.1 AI三脑协调
        需求: 3.7 - 统计信息管理
        需求: 7.7 - 并发决策处理统计

        Returns:
            Dict[str, Any]: 详细的统计信息
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        # 计算各脑决策占比
        total_decisions = self.stats["total_decisions"]

        brain_percentages = {}
        if total_decisions > 0:
            brain_percentages = {
                "soldier_percentage": (self.stats.get("soldier_decisions", 0) / total_decisions) * 100,
                "commander_percentage": (self.stats.get("commander_decisions", 0) / total_decisions) * 100,
                "scholar_percentage": (self.stats.get("scholar_decisions", 0) / total_decisions) * 100,
            }

        # 计算平均置信度
        recent_decisions = self.decision_history[-100:] if self.decision_history else []
        avg_confidence = 0.0
        if recent_decisions:
            avg_confidence = sum(d.confidence for d in recent_decisions) / len(recent_decisions)

        # 计算决策频率
        decisions_per_minute = 0.0
        if uptime > 0:
            decisions_per_minute = (total_decisions / uptime) * 60

        # Task 14.7: 并发和批处理统计
        concurrent_rate = 0.0
        batch_rate = 0.0
        if total_decisions > 0:
            concurrent_rate = (self.stats.get("concurrent_decisions", 0) / total_decisions) * 100
            batch_rate = (self.stats.get("batch_decisions", 0) / total_decisions) * 100

        statistics = {
            # 基础统计
            "total_decisions": total_decisions,
            "soldier_decisions": self.stats.get("soldier_decisions", 0),
            "commander_decisions": self.stats.get("commander_decisions", 0),
            "scholar_decisions": self.stats.get("scholar_decisions", 0),
            # 异常统计
            "coordination_conflicts": self.stats.get("coordination_conflicts", 0),
            "timeout_decisions": self.stats.get("timeout_decisions", 0),
            "error_decisions": self.stats.get("error_decisions", 0),
            # Task 14.7: 并发统计
            "concurrent_decisions": self.stats.get("concurrent_decisions", 0),
            "batch_decisions": self.stats.get("batch_decisions", 0),
            "concurrent_limit_hits": self.stats.get("concurrent_limit_hits", 0),
            "queue_full_hits": self.stats.get("queue_full_hits", 0),
            # 百分比统计
            **brain_percentages,
            "concurrent_rate": concurrent_rate,
            "batch_rate": batch_rate,
            # 质量统计
            "average_confidence": avg_confidence,
            "conflict_rate": (self.stats.get("coordination_conflicts", 0) / max(total_decisions, 1)) * 100,
            # 性能统计
            "uptime_seconds": uptime,
            "uptime_hours": uptime / 3600,
            "decisions_per_minute": decisions_per_minute,
            # 状态信息
            "coordination_active": self.coordination_active,
            "pending_decisions_count": len(self.pending_decisions),
            "decision_history_count": len(self.decision_history),
            "max_history_limit": self.max_history,
            "pending_batch_count": len(self.pending_batch),
            "max_concurrent_decisions": self.max_concurrent_decisions,
            "batch_size": self.batch_size,
            "enable_batch_processing": self.enable_batch_processing,
            # 时间信息
            "start_time": self.stats["start_time"].isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

        return statistics

    async def get_coordination_status(self) -> Dict[str, Any]:
        """获取协调状态 - 兼容性方法

        Returns:
            Dict[str, Any]: 协调状态信息
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {
            "coordination_active": self.coordination_active,
            "brains_available": {
                "soldier": self.soldier is not None,
                "commander": self.commander is not None,
                "scholar": self.scholar is not None,
            },
            "pending_decisions": len(self.pending_decisions),
            "decision_history_count": len(self.decision_history),
            "stats": {
                **self.stats,
                "uptime_seconds": uptime,
                "decisions_per_minute": self.stats["total_decisions"] / max(uptime / 60, 1),
            },
            "recent_decisions": [
                {
                    "decision_id": d.decision_id,
                    "primary_brain": d.primary_brain,
                    "action": d.action,
                    "confidence": d.confidence,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in self.decision_history[-5:]
            ],
        }
        """获取协调状态"""  # pylint: disable=w0101,w0105
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {
            "coordination_active": self.coordination_active,
            "brains_available": {
                "soldier": self.soldier is not None,
                "commander": self.commander is not None,
                "scholar": self.scholar is not None,
            },
            "pending_decisions": len(self.pending_decisions),
            "decision_history_count": len(self.decision_history),
            "stats": {
                **self.stats,
                "uptime_seconds": uptime,
                "decisions_per_minute": self.stats["total_decisions"] / max(uptime / 60, 1),
            },
            "recent_decisions": [
                {
                    "decision_id": d.decision_id,
                    "primary_brain": d.primary_brain,
                    "action": d.action,
                    "confidence": d.confidence,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in self.decision_history[-5:]
            ],
        }

    async def shutdown(self):
        """关闭协调器"""
        self.coordination_active = False
        self.pending_decisions.clear()
        logger.info("[AIBrainCoordinator] Shutdown completed")


# 全局协调器实例
_global_coordinator: Optional[AIBrainCoordinator] = None


async def get_ai_brain_coordinator() -> AIBrainCoordinator:
    """获取全局AI三脑协调器"""
    global _global_coordinator  # pylint: disable=w0603

    if _global_coordinator is None:
        event_bus = await get_event_bus()
        container = get_container()

        _global_coordinator = AIBrainCoordinator(event_bus, container)
        await _global_coordinator.initialize()

    return _global_coordinator


# 便捷函数
async def request_ai_decision(context: Dict[str, Any], primary_brain: str = "soldier") -> BrainDecision:
    """请求AI决策的便捷函数"""
    coordinator = await get_ai_brain_coordinator()
    return await coordinator.request_decision(context, primary_brain)


async def get_ai_coordination_status() -> Dict[str, Any]:
    """获取AI协调状态的便捷函数"""
    coordinator = await get_ai_brain_coordinator()
    return await coordinator.get_coordination_status()
