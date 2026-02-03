# pylint: disable=too-many-lines
"""
Commander引擎 v2.0 - 解决循环依赖版本 (资本分配器集成版本)

白皮书依据: 第二章 2.2 AI三脑架构 + 架构审计报告循环依赖修复
Requirement 16: 集成资本分配器，移除硬编码风险控制矩阵

核心改进:
1. 集成CommanderCapitalIntegration，实现档位感知的策略建议
2. 移除硬编码的风险控制矩阵，风险控制由StrategyRiskManager处理
3. 通过事件总线与其他AI脑通信，消除直接调用
4. 支持多种分析模式和市场环境识别

架构变更:
- 旧架构: Commander硬编码风险规则 → 违背"资本物理"理念
- 新架构: Commander提供策略建议 → StrategyRiskManager执行风险控制
- 职责分离: Commander(慢系统) → 策略分析，Soldier(快系统) → 快速执行

⚠️ 当前状态: 生产就绪版本 (功能完成度: ~80%)
📋 待完善功能: Qwen API集成、高级市场分析、多因子融合
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from ..core.dependency_container import LifecycleScope, injectable
from ..infra.event_bus import Event, EventBus, EventPriority, EventType, get_event_bus
from .cache_manager import LRUCache
from .commander_capital_integration import CommanderCapitalIntegration
from .hallucination_filter import HallucinationFilter
from .interfaces import ICommanderEngine
from .llm_gateway import LLMGateway


@dataclass
class StrategyAnalysis:
    """策略分析结果"""

    recommendation: str  # buy/sell/hold/reduce
    confidence: float  # 0.0-1.0
    risk_level: str  # low/medium/high
    allocation: Dict[str, float]  # 资产配置建议
    reasoning: str  # 分析推理
    market_regime: str  # 市场状态
    time_horizon: str  # 投资时间范围
    metadata: Dict[str, Any]


@injectable(LifecycleScope.SINGLETON)
class CommanderEngineV2(ICommanderEngine):
    """Commander引擎 v2.0 - 资本分配器集成版本

    白皮书依据: 第二章 2.2 AI三脑架构
    Requirement 16: 集成资本分配器，移除硬编码风险控制矩阵

    核心职责:
    1. 策略分析：基于市场数据和资本上下文生成策略建议
    2. 档位感知：通过资本分配器获取当前档位和推荐策略
    3. 市场环境识别：识别牛市/熊市/震荡市/横盘市
    4. 跨脑协调：通过事件总线与Soldier/Scholar通信

    架构改进:
    - 集成CommanderCapitalIntegration，实现档位感知
    - 移除硬编码风险控制矩阵（现由StrategyRiskManager处理）
    - 返回策略建议而非直接执行风险控制
    - 支持资本上下文优先，LLM分析作为fallback

    解决的循环依赖:
    - 原问题: Commander → Scholar.get_research() → Soldier.get_market_data() → Commander.get_strategy()
    - 解决方案: 通过事件发布需求，异步接收其他脑的数据和分析结果
    """

    def __init__(
        self,
        llm_gateway: LLMGateway = None,
        hallucination_filter: HallucinationFilter = None,
        vllm_memory_pool: Optional[Any] = None,
    ):
        # 核心组件
        self.llm_gateway = llm_gateway or LLMGateway()
        self.hallucination_filter = hallucination_filter or HallucinationFilter()

        # 资本分配器集成（新增）
        self.capital_integration = CommanderCapitalIntegration()

        # 运行状态
        self.state = "IDLE"
        self.last_analysis_time = None

        # 事件总线
        self.event_bus: Optional[EventBus] = None

        # LRU缓存（优化版 - Task 14.1）
        self.analysis_cache = LRUCache(max_size=1000, ttl_seconds=300.0, vllm_memory_pool=vllm_memory_pool)  # 5分钟缓存

        # 外部数据缓存 (来自Soldier/Scholar)
        self.external_data: Dict[str, Any] = {}
        self.data_timeout = 3.0  # 3秒超时

        # 风险控制参数（已废弃 - 现在由StrategyRiskManager处理）
        # 保留用于向后兼容，但不再使用
        self.risk_limits = {"max_position": 0.95, "max_single_stock": 0.05, "max_sector": 0.30, "stop_loss": -0.03}
        self._risk_limits_deprecated = True  # 标记为已废弃

        # 统计信息
        self.stats = {
            "total_analyses": 0,
            "strategy_recommendations": 0,
            "risk_alerts": 0,
            "cache_hits": 0,
            "avg_analysis_time_ms": 0.0,
            "error_count": 0,
        }

        logger.info("[CommanderV2] Initialized without circular dependencies (with LRU cache)")

    async def initialize(self):
        """初始化Commander引擎"""
        try:
            # 获取事件总线
            self.event_bus = await get_event_bus()

            # 订阅相关事件
            await self._setup_event_subscriptions()

            # 初始化LLM网关
            await self.llm_gateway.initialize()

            self.state = "READY"
            logger.info("[CommanderV2] Initialization completed")

        except Exception as e:
            logger.error(f"[CommanderV2] Initialization failed: {e}")
            self.state = "ERROR"
            raise

    async def _setup_event_subscriptions(self):
        """设置事件订阅"""
        if not self.event_bus:
            return

        # 订阅Soldier的市场数据
        await self.event_bus.subscribe(EventType.DECISION_MADE, self._handle_soldier_data, "commander_soldier_data")

        # 订阅Scholar的研究结果
        await self.event_bus.subscribe(
            EventType.ANALYSIS_COMPLETED, self._handle_scholar_research, "commander_scholar_research"
        )

        # 订阅市场数据更新
        await self.event_bus.subscribe(
            EventType.MARKET_DATA_RECEIVED, self._handle_market_data, "commander_market_data"
        )

        # 订阅策略分析请求
        await self.event_bus.subscribe(
            EventType.ANALYSIS_COMPLETED, self._handle_analysis_request, "commander_analysis_request"
        )

        logger.debug("[CommanderV2] Event subscriptions setup completed")

    async def analyze_strategy(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """策略分析 - ICommanderEngine接口实现

        白皮书依据: 第二章 2.2 Commander引擎
        Requirement 16.2: 集成资本分配器，提供档位感知的策略建议

        Args:
            market_data: 市场数据，包含价格、成交量、技术指标等

        Returns:
            Dict: 策略分析结果，包含档位信息和推荐策略
        """
        start_time = time.time()

        try:
            self.state = "ANALYZING"

            # 检查缓存
            cache_key = self._generate_cache_key(market_data)
            cached_analysis = self._get_cached_analysis(cache_key)

            if cached_analysis:
                self.stats["cache_hits"] += 1
                return self._format_analysis_output(cached_analysis)

            # 使用资本分配器集成进行策略分析（新方法）
            capital_context = await self.capital_integration.analyze_strategy_with_capital_context(
                market_data=market_data
            )

            # 请求外部数据 (异步，不阻塞)
            await self._request_external_data(market_data)

            # 执行策略分析（融合资本上下文）
            analysis = await self._execute_strategy_analysis_with_capital(
                market_data=market_data, capital_context=capital_context
            )

            # 缓存分析结果
            self._cache_analysis(cache_key, analysis)

            # 更新统计
            analysis_time_ms = (time.time() - start_time) * 1000
            self._update_stats(analysis_time_ms)

            # 发布分析事件
            await self._publish_analysis_event(analysis, market_data)

            self.state = "READY"
            self.last_analysis_time = datetime.now()

            return self._format_analysis_output(analysis)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["error_count"] += 1
            self.state = "ERROR"
            logger.error(f"[CommanderV2] Strategy analysis failed: {e}")

            # 返回保守策略
            return self._create_fallback_strategy(market_data)

    async def get_allocation(self) -> Dict[str, Any]:
        """获取资产配置 - ICommanderEngine接口实现"""
        try:
            # 获取当前持仓
            current_positions = self.external_data.get("positions", {})

            # 获取市场状态
            market_regime = self.external_data.get("market_regime", "normal")

            # 根据市场状态调整配置
            allocation = await self._calculate_optimal_allocation(current_positions, market_regime)

            return {
                "allocation": allocation,
                "market_regime": market_regime,
                "risk_level": self._assess_portfolio_risk(allocation),
                "rebalance_needed": self._check_rebalance_needed(current_positions, allocation),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Get allocation failed: {e}")
            return self._create_default_allocation()

    async def _request_external_data(self, market_data: Dict[str, Any]):
        """请求外部数据 (Soldier/Scholar) - 异步非阻塞"""
        if not self.event_bus:
            return

        correlation_id = f"commander_request_{time.time()}"

        # 请求Soldier的实时信号
        await self.event_bus.publish(
            Event(
                event_type=EventType.ANALYSIS_COMPLETED,
                source_module="commander",
                target_module="soldier",
                priority=EventPriority.NORMAL,
                data={
                    "action": "request_market_signals",
                    "market_data": market_data,
                    "correlation_id": correlation_id,
                    "timeout": self.data_timeout,
                },
            )
        )

        # 请求Scholar的因子研究
        await self.request_scholar_research(market_data, correlation_id)

        logger.debug(f"[CommanderV2] Requested external data: {correlation_id}")

    async def request_scholar_research(
        self, market_data: Dict[str, Any], correlation_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """请求Scholar因子研究 - Task 7.6 跨脑事件通信

        白皮书依据: 第二章 2.2 Commander引擎 - 跨脑协调
        需求: 4.7 - 实现跨脑事件通信

        Args:
            market_data: 市场数据
            correlation_id: 关联ID，可选

        Returns:
            Optional[Dict[str, Any]]: Scholar的研究结果，超时返回None
        """
        if not self.event_bus:
            logger.warning("[CommanderV2] Event bus not available")
            return None

        try:
            if correlation_id is None:
                correlation_id = f"commander_scholar_request_{time.time()}"

            logger.debug(f"[CommanderV2] Requesting Scholar research: {correlation_id}")

            # 发布因子研究请求事件
            await self.event_bus.publish(
                Event(
                    event_type=EventType.ANALYSIS_COMPLETED,
                    source_module="commander",
                    target_module="scholar",
                    priority=EventPriority.NORMAL,
                    data={
                        "action": "request_factor_analysis",
                        "market_data": market_data,
                        "correlation_id": correlation_id,
                        "timeout": self.data_timeout,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            )

            # 等待Scholar响应
            research_result = await self._wait_for_scholar_response(correlation_id)

            if research_result:  # pylint: disable=no-else-return
                logger.info(
                    f"[CommanderV2] Received Scholar research: factor_score={research_result.get('factor_score', 0.0):.2f}"  # pylint: disable=line-too-long
                )
                return research_result
            else:
                logger.warning(f"[CommanderV2] Scholar research request timeout: {correlation_id}")
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to request Scholar research: {e}")
            return None

    async def _wait_for_scholar_response(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """等待Scholar响应

        Args:
            correlation_id: 关联ID

        Returns:
            Optional[Dict[str, Any]]: Scholar响应，超时返回None
        """
        start_time = asyncio.get_event_loop().time()
        check_interval = 0.05  # 50ms检查间隔

        while asyncio.get_event_loop().time() - start_time < self.data_timeout:
            # 检查是否收到Scholar响应
            scholar_key = f"scholar_response_{correlation_id}"
            if scholar_key in self.external_data:
                response = self.external_data.pop(scholar_key)
                return response

            await asyncio.sleep(check_interval)

        return None

    async def _execute_strategy_analysis(self, market_data: Dict[str, Any]) -> StrategyAnalysis:
        """执行策略分析逻辑（旧版本，保留用于向后兼容）"""
        return await self._execute_strategy_analysis_with_capital(market_data, None)

    async def _execute_strategy_analysis_with_capital(
        self, market_data: Dict[str, Any], capital_context: Optional[Dict[str, Any]] = None
    ) -> StrategyAnalysis:
        """执行策略分析逻辑（融合资本上下文）

        白皮书依据: Requirement 16.3, 16.4

        Args:
            market_data: 市场数据
            capital_context: 资本上下文（包含档位、推荐策略等）

        Returns:
            StrategyAnalysis: 策略分析结果
        """
        try:
            # 如果有资本上下文，优先使用
            if capital_context:
                recommendation = capital_context.get("recommendation", {})
                recommended_strategies = recommendation.get("recommended_strategies", [])
                weights = recommendation.get("weights", {})
                current_tier = capital_context.get("current_tier", "tier1_micro")
                market_regime = capital_context.get("market_regime", "neutral")

                # 基于资本分配器的建议构建分析结果
                if recommended_strategies:
                    # 使用推荐的策略组合
                    allocation = self._convert_strategy_weights_to_allocation(weights)
                    confidence = self._calculate_confidence_from_strategies(recommended_strategies)
                    risk_level = self._assess_risk_from_tier(current_tier)

                    return StrategyAnalysis(
                        recommendation="buy" if market_regime in ["bull", "neutral"] else "hold",
                        confidence=confidence,
                        risk_level=risk_level,
                        allocation=allocation,
                        reasoning=recommendation.get("rationale", "基于资本分配器的策略建议"),
                        market_regime=market_regime,
                        time_horizon="medium",
                        metadata={
                            "capital_context": capital_context,
                            "strategies": [
                                s.name if hasattr(s, "name") else s.get("strategy_name", "unknown")
                                for s in recommended_strategies
                            ],
                            "tier": current_tier,
                            "analysis_time": datetime.now(),
                        },
                    )

            # 如果没有资本上下文，使用原有的LLM分析逻辑
            # 构建分析提示词
            prompt = self._build_analysis_prompt(market_data)

            # 调用LLM
            response = await self.llm_gateway.generate_cloud(prompt)

            # 检测幻觉
            hallucination_result = await self.hallucination_filter.detect_hallucination(response, {"query": prompt})

            if hallucination_result["is_hallucination"]:
                logger.warning("[CommanderV2] Hallucination detected, using conservative strategy")
                return self._create_conservative_strategy(market_data)

            # 解析分析结果
            analysis = self._parse_llm_response(response, market_data)

            # 融合外部数据
            analysis = await self._enhance_with_external_data(analysis, market_data)

            # 风险控制检查
            analysis = self._apply_risk_controls(analysis)

            return analysis

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Strategy analysis execution failed: {e}")
            return self._create_conservative_strategy(market_data)

    def _build_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """构建策略分析提示词"""
        # 获取外部数据
        soldier_signals = self.external_data.get("soldier", {})
        scholar_factors = self.external_data.get("scholar", {})

        # 市场数据摘要
        market_summary = {
            "index_level": market_data.get("index_level", 0),
            "volatility": market_data.get("volatility", 0),
            "volume": market_data.get("volume", 0),
            "trend": market_data.get("trend", "neutral"),
        }

        prompt = f"""
作为MIA系统的Commander AI，请基于以下信息进行策略分析：

市场数据：
- 指数水平: {market_summary['index_level']}
- 波动率: {market_summary['volatility']:.2%}
- 成交量: {market_summary['volume']}
- 趋势: {market_summary['trend']}

外部分析：
- Soldier信号强度: {soldier_signals.get('signal_strength', '无')}
- Scholar因子评分: {scholar_factors.get('factor_score', '无')}

注意：风险控制由StrategyRiskManager在策略层处理，此处只需提供策略建议。

请返回JSON格式的策略分析：
{{
    "recommendation": "buy/sell/hold/reduce",
    "confidence": 0.0-1.0,
    "risk_level": "low/medium/high",
    "allocation": {{"stocks": 0.0-1.0, "bonds": 0.0-1.0, "cash": 0.0-1.0}},
    "reasoning": "分析推理",
    "market_regime": "bull/bear/sideways/volatile",
    "time_horizon": "short/medium/long"
}}
"""
        return prompt

    def _parse_llm_response(self, response: str, market_data: Dict[str, Any]) -> StrategyAnalysis:
        """解析LLM响应"""
        try:
            # 识别市场状态
            market_regime = self.identify_market_regime(market_data)

            # 尝试解析JSON
            if "{" in response and "}" in response:  # pylint: disable=no-else-return
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]

                data = json.loads(json_str)

                return StrategyAnalysis(
                    recommendation=data.get("recommendation", "hold"),
                    confidence=float(data.get("confidence", 0.5)),
                    risk_level=data.get("risk_level", "medium"),
                    allocation=data.get("allocation", {"stocks": 0.6, "bonds": 0.3, "cash": 0.1}),
                    reasoning=data.get("reasoning", "LLM strategy analysis"),
                    market_regime=data.get("market_regime", market_regime),  # 优先使用LLM判断，否则使用算法判断
                    time_horizon=data.get("time_horizon", "medium"),
                    metadata={
                        "llm_response": response,
                        "market_data": market_data,
                        "analysis_time": datetime.now(),
                        "identified_regime": market_regime,
                    },
                )
            else:
                # 简单文本解析
                recommendation = "hold"
                if "buy" in response.lower():
                    recommendation = "buy"
                elif "sell" in response.lower():
                    recommendation = "sell"
                elif "reduce" in response.lower():
                    recommendation = "reduce"

                return StrategyAnalysis(
                    recommendation=recommendation,
                    confidence=0.6,
                    risk_level="medium",
                    allocation={"stocks": 0.6, "bonds": 0.3, "cash": 0.1},
                    reasoning=response[:200],
                    market_regime=market_regime,  # 使用算法识别的市场状态
                    time_horizon="medium",
                    metadata={"llm_response": response, "market_data": market_data, "identified_regime": market_regime},
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to parse LLM response: {e}")
            return self._create_conservative_strategy(market_data)

    async def _enhance_with_external_data(
        self, analysis: StrategyAnalysis, market_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> StrategyAnalysis:
        """使用外部数据增强策略分析"""
        try:
            # 获取Soldier信号
            soldier_data = self.external_data.get("soldier", {})
            if soldier_data:
                signal_strength = soldier_data.get("signal_strength", 0.5)

                # 调整置信度
                if signal_strength > 0.7:
                    analysis.confidence = min(analysis.confidence * 1.2, 1.0)
                elif signal_strength < 0.3:
                    analysis.confidence *= 0.8

                # 更新推理
                analysis.reasoning += f" Soldier信号强度: {signal_strength:.2f}"

            # 获取Scholar因子
            scholar_data = self.external_data.get("scholar", {})
            if scholar_data:
                factor_score = scholar_data.get("factor_score", 0.5)

                # 调整资产配置
                if factor_score > 0.6:
                    # 因子看好，增加股票配置
                    analysis.allocation["stocks"] = min(analysis.allocation.get("stocks", 0.6) * 1.1, 0.95)
                    analysis.allocation["cash"] = max(analysis.allocation.get("cash", 0.1) * 0.9, 0.05)
                elif factor_score < 0.4:
                    # 因子看淡，减少股票配置
                    analysis.allocation["stocks"] = max(analysis.allocation.get("stocks", 0.6) * 0.9, 0.3)
                    analysis.allocation["cash"] = min(analysis.allocation.get("cash", 0.1) * 1.2, 0.4)

                # 更新推理
                analysis.reasoning += f" Scholar因子评分: {factor_score:.2f}"

            return analysis

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to enhance analysis with external data: {e}")
            return analysis

    def _apply_risk_controls(self, analysis: StrategyAnalysis) -> StrategyAnalysis:
        """应用风险控制机制（已废弃 - 现在由StrategyRiskManager处理）

        白皮书依据: 第二章 2.2 Commander引擎 - 风险控制
        需求: Requirement 16.6 - 移除硬编码的风险控制矩阵

        ⚠️ 废弃说明:
        - 此方法保留用于向后兼容
        - 实际风险控制现在由StrategyRiskManager在策略层处理
        - Commander只负责策略建议，不再直接执行风险控制

        Args:
            analysis: 原始策略分析结果

        Returns:
            StrategyAnalysis: 原样返回（不再修改）
        """
        if self._risk_limits_deprecated:
            logger.debug("[CommanderV2] Risk controls deprecated - handled by StrategyRiskManager")
            # 只记录警告，不再执行风险控制
            if analysis.risk_level == "high":
                logger.warning(f"[CommanderV2] High risk level detected: {analysis.risk_level}")
                self.stats["risk_alerts"] += 1

        return analysis

    async def _trigger_risk_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """触发风险警报

        Args:
            alert_type: 警报类型 ('stop_loss', 'high_risk', 'position_limit')
            alert_data: 警报详细数据
        """
        try:
            if not self.event_bus:
                return

            await self.event_bus.publish(
                Event(
                    event_type=EventType.SYSTEM_ALERT,
                    source_module="commander",
                    priority=EventPriority.HIGH,
                    data={
                        "alert_type": alert_type,
                        "alert_data": alert_data,
                        "timestamp": datetime.now().isoformat(),
                        "action_required": True,
                    },
                )
            )

            logger.info(f"[CommanderV2] Risk alert triggered: {alert_type}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to trigger risk alert: {e}")

    async def _handle_soldier_data(self, event: Event):
        """处理Soldier数据"""
        try:
            data = event.data

            if data.get("source") == "commander_request":
                correlation_id = data.get("correlation_id", "")
                signal_data = data.get("signal_data", {})

                # 存储Soldier数据
                self.external_data["soldier"] = {
                    "signal_strength": signal_data.get("signal_strength", 0.5),
                    "market_sentiment": signal_data.get("market_sentiment", "neutral"),
                    "volatility_signal": signal_data.get("volatility_signal", 0.5),
                    "timestamp": datetime.now(),
                    "correlation_id": correlation_id,
                }

                logger.debug(f"[CommanderV2] Received Soldier data: {correlation_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to handle Soldier data: {e}")

    async def _handle_scholar_research(self, event: Event):
        """处理Scholar研究结果 - Task 7.6 事件响应处理器"""
        try:
            data = event.data

            if data.get("source") == "commander_request":
                correlation_id = data.get("correlation_id", "")
                research_data = data.get("research_data", {})

                # 存储Scholar数据
                self.external_data["scholar"] = {
                    "factor_score": research_data.get("factor_score", 0.5),
                    "sector_rotation": research_data.get("sector_rotation", {}),
                    "style_factor": research_data.get("style_factor", "neutral"),
                    "timestamp": datetime.now(),
                    "correlation_id": correlation_id,
                }

                logger.debug(f"[CommanderV2] Received Scholar research: {correlation_id}")

            elif data.get("action") == "research_result" and data.get("source") == "scholar_response":
                # 新的响应格式 - Task 7.6
                correlation_id = data.get("correlation_id", "")
                research_result = data.get("research_result", {})

                # 存储Scholar响应
                response_key = f"scholar_response_{correlation_id}"
                self.external_data[response_key] = research_result

                logger.debug(f"[CommanderV2] Received Scholar research response: {correlation_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to handle Scholar research: {e}")

    async def _handle_market_data(self, event: Event):
        """处理市场数据更新"""
        try:
            data = event.data
            market_data = data.get("market_data", {})

            # 更新市场数据缓存
            self.external_data["market"] = {
                "index_level": market_data.get("index_level", 0),
                "volatility": market_data.get("volatility", 0),
                "volume": market_data.get("volume", 0),
                "timestamp": datetime.now(),
            }

            # 如果市场出现异常波动，触发风险评估
            volatility = market_data.get("volatility", 0)
            if volatility > 0.05:  # 5%以上波动
                await self._trigger_risk_assessment(market_data)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to handle market data: {e}")

    async def _handle_analysis_request(self, event: Event):
        """处理分析请求"""
        try:
            data = event.data

            if data.get("action") == "request_strategy_analysis" and data.get("target_module") == "commander":
                # 执行策略分析
                context = data.get("context", {})
                correlation_id = data.get("correlation_id", "")

                analysis_result = await self.analyze_strategy(context)

                # 发布分析结果
                await self.event_bus.publish(
                    Event(
                        event_type=EventType.ANALYSIS_COMPLETED,
                        source_module="commander",
                        target_module=event.source_module,
                        priority=EventPriority.NORMAL,
                        data={
                            "action": "analysis_result",
                            "analysis_result": analysis_result,
                            "correlation_id": correlation_id,
                            "source": "commander_response",
                        },
                    )
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to handle analysis request: {e}")

    async def _trigger_risk_assessment(self, market_data: Dict[str, Any]):
        """触发风险评估"""
        self.stats["risk_alerts"] += 1

        await self.event_bus.publish(
            Event(
                event_type=EventType.SYSTEM_ALERT,
                source_module="commander",
                priority=EventPriority.HIGH,
                data={"alert_type": "high_volatility", "market_data": market_data, "action": "risk_assessment_needed"},
            )
        )

    async def _calculate_optimal_allocation(
        self, current_positions: Dict[str, float], market_regime: str  # pylint: disable=unused-argument
    ) -> Dict[str, float]:
        """计算最优资产配置

        根据市场状态调整资产配置策略
        """
        # 如果market_regime是从外部数据获取的，直接使用
        # 否则，尝试从市场数据中识别
        if market_regime == "normal" or not market_regime:
            # 尝试从缓存的市场数据中识别
            market_data = self.external_data.get("market", {})
            if market_data:
                market_regime = self.identify_market_regime(market_data)
            else:
                market_regime = "sideways"  # 默认

        # 根据市场状态调整配置
        if market_regime == "bull":  # pylint: disable=no-else-return
            return {"stocks": 0.8, "bonds": 0.15, "cash": 0.05}
        elif market_regime == "bear":
            return {"stocks": 0.4, "bonds": 0.4, "cash": 0.2}
        elif market_regime == "volatile":
            return {"stocks": 0.5, "bonds": 0.3, "cash": 0.2}
        else:  # sideways
            return {"stocks": 0.6, "bonds": 0.3, "cash": 0.1}

    def _assess_portfolio_risk(self, allocation: Dict[str, float]) -> str:
        """评估投资组合风险"""
        stock_weight = allocation.get("stocks", 0)

        if stock_weight > 0.8:  # pylint: disable=no-else-return
            return "high"
        elif stock_weight > 0.6:
            return "medium"
        else:
            return "low"

    def identify_market_regime(self, market_data: Dict[str, Any]) -> str:
        """识别市场状态（A股优化版本）

        白皮书依据: 第二章 2.2 Commander引擎 - 市场状态识别
        需求: 1.6 - 支持多种市场状态识别

        Args:
            market_data: 市场数据，包含trend、volatility、turnover等

        Returns:
            str: 市场状态 - 'bull'(牛市), 'bear'(熊市), 'volatile'(震荡市), 'sideways'(横盘市)

        A股优化的市场状态定义（趋势优先）:
        - 牛市: 上涨趋势(trend > 0.04)，允许高波动
        - 熊市: 下跌趋势(trend < -0.04)，允许高波动
        - 震荡市: 无明显趋势(|trend| <= 0.04) + 高波动(volatility > 0.05)
        - 横盘市: 无明显趋势(|trend| <= 0.04) + 低波动(volatility <= 0.05)

        设计理念:
        1. 趋势优先于波动（A股趋势行情常伴随高波动）
        2. 震荡市必须同时满足"无趋势+高波动"
        3. 横盘市是A股最常见状态（机构观望、缩量）
        4. 可选：引入换手率/成交量作为情绪维度（待扩展）
        """
        try:
            # 提取市场指标
            volatility = market_data.get("volatility", 0.0)
            trend = market_data.get("trend", 0.0)
            market_data.get("volume", 0)
            turnover = market_data.get("turnover", 0.0)  # 换手率（可选）

            # 计算趋势强度
            trend_strength = abs(trend)

            # 第一优先级：趋势判断（趋势优先）
            # 牛市：明显上涨趋势（不限制波动）
            if trend > 0.04:
                # 可选：根据换手率判断牛市阶段
                if turnover > 0.05:  # 高换手
                    logger.debug(
                        f"[CommanderV2] Market regime: bull (high turnover) - trend={trend:.3f}, vol={volatility:.3f}, turnover={turnover:.3f}"  # pylint: disable=line-too-long
                    )
                else:
                    logger.debug(f"[CommanderV2] Market regime: bull - trend={trend:.3f}, vol={volatility:.3f}")
                return "bull"

            # 熊市：明显下跌趋势（不限制波动，捕捉急跌）
            if trend < -0.04:
                logger.debug(f"[CommanderV2] Market regime: bear - trend={trend:.3f}, vol={volatility:.3f}")
                return "bear"

            # 第二优先级：无趋势时，根据波动区分震荡/横盘
            # 震荡市：无明显趋势 + 高波动（题材轮动、情绪博弈）
            if trend_strength <= 0.04 and volatility > 0.05:
                logger.debug(f"[CommanderV2] Market regime: volatile - trend={trend:.3f}, vol={volatility:.3f}")
                return "volatile"

            # 横盘市：无明显趋势 + 低波动（机构观望、缩量）
            # 这是A股最常见状态
            logger.debug(f"[CommanderV2] Market regime: sideways - trend={trend:.3f}, vol={volatility:.3f}")
            return "sideways"

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[CommanderV2] Failed to identify market regime: {e}")
            return "sideways"  # 默认返回横盘市

    def _check_rebalance_needed(self, current: Dict[str, float], target: Dict[str, float]) -> bool:
        """检查是否需要再平衡"""
        for asset in target:
            current_weight = current.get(asset, 0)
            target_weight = target.get(asset, 0)

            if abs(current_weight - target_weight) > 0.05:  # 5%阈值
                return True

        return False

    def _create_conservative_strategy(self, market_data: Dict[str, Any]) -> StrategyAnalysis:
        """创建保守策略"""
        return StrategyAnalysis(
            recommendation="hold",
            confidence=0.3,
            risk_level="low",
            allocation={"stocks": 0.4, "bonds": 0.4, "cash": 0.2},
            reasoning="Conservative strategy due to uncertainty",
            market_regime="sideways",
            time_horizon="medium",
            metadata={"type": "conservative", "market_data": market_data},
        )

    def _create_default_allocation(self) -> Dict[str, Any]:
        """创建默认资产配置"""
        return {
            "allocation": {"stocks": 0.6, "bonds": 0.3, "cash": 0.1},
            "market_regime": "normal",
            "risk_level": "medium",
            "rebalance_needed": False,
            "timestamp": datetime.now().isoformat(),
        }

    def _create_fallback_strategy(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建备用策略"""
        strategy = self._create_conservative_strategy(market_data)
        return self._format_analysis_output(strategy)

    def _format_analysis_output(self, analysis: StrategyAnalysis) -> Dict[str, Any]:
        """格式化分析输出"""
        return {
            "recommendation": analysis.recommendation,
            "confidence": analysis.confidence,
            "risk_level": analysis.risk_level,
            "allocation": analysis.allocation,
            "reasoning": analysis.reasoning,
            "market_regime": analysis.market_regime,
            "time_horizon": analysis.time_horizon,
            "metadata": analysis.metadata,
            "timestamp": datetime.now().isoformat(),
            "source": "commander_v2",
        }

    async def _publish_analysis_event(self, analysis: StrategyAnalysis, market_data: Dict[str, Any]):
        """发布分析事件"""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            Event(
                event_type=EventType.ANALYSIS_COMPLETED,
                source_module="commander",
                priority=EventPriority.NORMAL,
                data={
                    "action": "strategy_analysis_completed",
                    "recommendation": analysis.recommendation,
                    "confidence": analysis.confidence,
                    "risk_level": analysis.risk_level,
                    "market_data": market_data,
                    "analysis_id": f"commander_{time.time()}",
                },
            )
        )

    def _generate_cache_key(self, market_data: Dict[str, Any]) -> str:
        """生成缓存键"""
        index_level = market_data.get("index_level", 0)
        volatility = market_data.get("volatility", 0)
        # 使用时间窗口确保缓存在TTL内有效
        time_window = int(time.time() / 300)  # 5分钟窗口
        return f"strategy_{index_level:.0f}_{volatility:.3f}_{time_window}"

    def _get_cached_analysis(self, cache_key: str) -> Optional[StrategyAnalysis]:
        """获取缓存分析（使用LRU缓存）"""
        cached_value = self.analysis_cache.get(cache_key)
        if cached_value:
            self.stats["cache_hits"] += 1
            return cached_value
        return None

    def _cache_analysis(self, cache_key: str, analysis: StrategyAnalysis):
        """缓存分析结果（使用LRU缓存）"""
        analysis.metadata["cached_at"] = datetime.now()
        # 根据分析的置信度设置重要性
        importance = min(1.0, analysis.confidence * 1.2)
        self.analysis_cache.put(cache_key, analysis, importance=importance)

    def _update_stats(self, analysis_time_ms: float):
        """更新统计信息"""
        self.stats["total_analyses"] += 1
        self.stats["strategy_recommendations"] += 1

        # 更新平均分析时间
        total_analyses = self.stats["total_analyses"]
        current_avg = self.stats["avg_analysis_time_ms"]
        self.stats["avg_analysis_time_ms"] = (current_avg * (total_analyses - 1) + analysis_time_ms) / total_analyses

    def _convert_strategy_weights_to_allocation(self, weights: Dict[str, float]) -> Dict[str, float]:
        """将策略权重转换为资产配置

        Args:
            weights: 策略权重字典

        Returns:
            资产配置字典 {'stocks': float, 'bonds': float, 'cash': float}
        """
        # 简化版本：假设所有策略都是股票策略
        # 实际应该根据策略类型分配到不同资产类别
        total_weight = sum(weights.values())

        if total_weight > 0:  # pylint: disable=no-else-return
            # 股票配置 = 策略总权重 * 0.9（保留10%现金）
            stocks = min(total_weight * 0.9, 0.95)
            cash = 1.0 - stocks
            return {"stocks": stocks, "bonds": 0.0, "cash": cash}
        else:
            # 无策略时，保守配置
            return {"stocks": 0.3, "bonds": 0.3, "cash": 0.4}

    def _calculate_confidence_from_strategies(self, strategies: List[Any]) -> float:
        """根据策略数量和质量计算置信度

        Args:
            strategies: 策略列表

        Returns:
            置信度 [0.0, 1.0]
        """
        if not strategies:
            return 0.3

        # 基础置信度：根据策略数量
        base_confidence = min(0.5 + len(strategies) * 0.1, 0.9)

        # 根据策略的Arena表现调整
        # 简化版本：假设所有策略都通过了Arena测试
        return base_confidence

    def _assess_risk_from_tier(self, tier: str) -> str:
        """根据资金档位评估风险等级

        Args:
            tier: 资金档位

        Returns:
            风险等级 ('low', 'medium', 'high')
        """
        # 资金规模越大，风险越需要控制
        if tier in ["tier5_million", "tier6_ten_million"]:  # pylint: disable=no-else-return
            return "low"  # 大资金，低风险
        elif tier in ["tier3_medium", "tier4_large"]:
            return "medium"  # 中等资金，中等风险
        else:
            return "medium"  # 小资金，允许中等风险

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_stats = self.analysis_cache.get_stats()
        return {
            **self.stats,
            "state": self.state,
            "cache_size": cache_stats["size"],
            "external_data_count": len(self.external_data),
            "last_analysis_time": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "risk_limits_deprecated": self._risk_limits_deprecated,
            "note": "Risk controls now handled by StrategyRiskManager",
        }
