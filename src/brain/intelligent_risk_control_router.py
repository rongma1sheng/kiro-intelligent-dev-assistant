"""智能风控路由器

白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 2 智能切换

核心功能：
1. 根据元学习器的预测，智能选择风控架构
2. 实现置信度阈值检查
3. 实现自适应路由策略
4. 记录路由决策历史

实施流程：
- Phase 2 (3-6月): 智能切换，模式识别（目标：5000+样本）
- 路由策略：
  * 高置信度（>0.8）：直接使用预测的架构
  * 中置信度（0.6-0.8）：使用混合策略
  * 低置信度（<0.6）：使用保守策略（架构A）

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from src.brain.risk_control_meta_learner import MarketContext, RiskControlMetaLearner, RiskControlStrategy


@dataclass
class RoutingDecision:
    """路由决策

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    Attributes:
        selected_strategy: 选择的策略类型
        confidence: 预测置信度（0-1）
        routing_reason: 路由原因
        fallback_used: 是否使用了回退策略
        timestamp: 决策时间戳
    """

    selected_strategy: RiskControlStrategy
    confidence: float
    routing_reason: str
    fallback_used: bool
    timestamp: str


class IntelligentRiskControlRouter:
    """智能风控路由器

    白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 2 智能切换

    核心职责：
    1. 根据元学习器的预测，智能选择风控架构
    2. 实现置信度阈值检查
    3. 实现自适应路由策略
    4. 记录路由决策历史
    5. 提供路由统计信息

    路由策略：
    - 高置信度（>0.8）：直接使用预测的架构
    - 中置信度（0.6-0.8）：使用混合策略
    - 低置信度（<0.6）：使用保守策略（架构A）

    Attributes:
        meta_learner: 元学习器实例
        high_confidence_threshold: 高置信度阈值（默认0.8）
        low_confidence_threshold: 低置信度阈值（默认0.6）
        routing_history: 路由决策历史
        stats: 路由统计信息
    """

    def __init__(
        self,
        meta_learner: RiskControlMetaLearner,
        high_confidence_threshold: float = 0.8,
        low_confidence_threshold: float = 0.6,
    ):
        """初始化智能路由器

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            meta_learner: 元学习器实例
            high_confidence_threshold: 高置信度阈值（默认0.8）
            low_confidence_threshold: 低置信度阈值（默认0.6）

        Raises:
            ValueError: 当阈值不在有效范围时
        """
        if not 0 <= low_confidence_threshold <= high_confidence_threshold <= 1:
            raise ValueError(
                f"阈值必须满足: 0 <= low_threshold <= high_threshold <= 1, "
                f"当前: low={low_confidence_threshold}, high={high_confidence_threshold}"
            )

        self.meta_learner = meta_learner
        self.high_confidence_threshold = high_confidence_threshold
        self.low_confidence_threshold = low_confidence_threshold

        # 路由决策历史
        self.routing_history: List[RoutingDecision] = []

        # 统计信息
        self.stats = {
            "total_routes": 0,
            "hardcoded_selected": 0,
            "strategy_layer_selected": 0,
            "hybrid_selected": 0,
            "fallback_used": 0,
            "high_confidence_routes": 0,
            "medium_confidence_routes": 0,
            "low_confidence_routes": 0,
        }

        logger.info(
            f"[IntelligentRouter] 初始化完成 - "
            f"高置信度阈值: {high_confidence_threshold}, "
            f"低置信度阈值: {low_confidence_threshold}"
        )

    async def route_decision(self, market_context: MarketContext) -> RoutingDecision:
        """路由决策

        白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 2 智能切换

        核心流程：
        1. 使用元学习器预测最优策略
        2. 根据置信度选择路由策略
        3. 记录路由决策
        4. 更新统计信息

        路由策略：
        - 高置信度（>0.8）：直接使用预测的架构
        - 中置信度（0.6-0.8）：使用混合策略
        - 低置信度（<0.6）：使用保守策略（架构A）

        Args:
            market_context: 市场上下文

        Returns:
            RoutingDecision: 路由决策

        Example:
            >>> router = IntelligentRiskControlRouter(meta_learner)
            >>> context = MarketContext(...)
            >>> decision = await router.route_decision(context)
            >>> print(f"选择策略: {decision.selected_strategy.value}")
            >>> print(f"置信度: {decision.confidence:.2%}")
        """
        self.stats["total_routes"] += 1

        # 1. 使用元学习器预测最优策略
        predicted_strategy, confidence = self.meta_learner.predict_best_strategy(market_context)

        # 2. 根据置信度选择路由策略
        if confidence >= self.high_confidence_threshold:
            # 高置信度：直接使用预测的架构
            selected_strategy = predicted_strategy
            routing_reason = f"高置信度预测（{confidence:.2%}），直接使用{predicted_strategy.value}"
            fallback_used = False
            self.stats["high_confidence_routes"] += 1

        elif confidence >= self.low_confidence_threshold:
            # 中置信度：使用混合策略
            selected_strategy = RiskControlStrategy.HYBRID
            routing_reason = f"中置信度预测（{confidence:.2%}），使用混合策略"
            fallback_used = False
            self.stats["medium_confidence_routes"] += 1
            self.stats["hybrid_selected"] += 1

        else:
            # 低置信度：使用保守策略（架构A）
            selected_strategy = RiskControlStrategy.HARDCODED
            routing_reason = f"低置信度预测（{confidence:.2%}），回退到保守策略（硬编码风控）"
            fallback_used = True
            self.stats["low_confidence_routes"] += 1
            self.stats["fallback_used"] += 1

        # 3. 更新策略选择统计
        if selected_strategy == RiskControlStrategy.HARDCODED:
            self.stats["hardcoded_selected"] += 1
        elif selected_strategy == RiskControlStrategy.STRATEGY_LAYER:
            self.stats["strategy_layer_selected"] += 1
        elif selected_strategy == RiskControlStrategy.HYBRID:
            # 已在上面更新
            pass

        # 4. 创建路由决策
        decision = RoutingDecision(
            selected_strategy=selected_strategy,
            confidence=confidence,
            routing_reason=routing_reason,
            fallback_used=fallback_used,
            timestamp=datetime.now().isoformat(),
        )

        # 5. 记录路由历史
        self.routing_history.append(decision)

        # 6. 限制历史记录大小（保留最近10000条）
        if len(self.routing_history) > 10000:
            self.routing_history = self.routing_history[-10000:]

        logger.info(
            f"[IntelligentRouter] 路由决策完成 - "
            f"策略: {selected_strategy.value}, "
            f"置信度: {confidence:.2%}, "
            f"回退: {fallback_used}"
        )

        return decision

    def get_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息

        Returns:
            Dict[str, Any]: 路由统计信息
        """
        total_routes = self.stats["total_routes"]

        if total_routes > 0:
            hardcoded_rate = self.stats["hardcoded_selected"] / total_routes
            strategy_layer_rate = self.stats["strategy_layer_selected"] / total_routes
            hybrid_rate = self.stats["hybrid_selected"] / total_routes
            fallback_rate = self.stats["fallback_used"] / total_routes
            high_confidence_rate = self.stats["high_confidence_routes"] / total_routes
            medium_confidence_rate = self.stats["medium_confidence_routes"] / total_routes
            low_confidence_rate = self.stats["low_confidence_routes"] / total_routes
        else:
            hardcoded_rate = 0.0
            strategy_layer_rate = 0.0
            hybrid_rate = 0.0
            fallback_rate = 0.0
            high_confidence_rate = 0.0
            medium_confidence_rate = 0.0
            low_confidence_rate = 0.0

        return {
            "total_routes": total_routes,
            "strategy_selection": {
                "hardcoded": self.stats["hardcoded_selected"],
                "strategy_layer": self.stats["strategy_layer_selected"],
                "hybrid": self.stats["hybrid_selected"],
                "hardcoded_rate": hardcoded_rate,
                "strategy_layer_rate": strategy_layer_rate,
                "hybrid_rate": hybrid_rate,
            },
            "confidence_distribution": {
                "high_confidence": self.stats["high_confidence_routes"],
                "medium_confidence": self.stats["medium_confidence_routes"],
                "low_confidence": self.stats["low_confidence_routes"],
                "high_confidence_rate": high_confidence_rate,
                "medium_confidence_rate": medium_confidence_rate,
                "low_confidence_rate": low_confidence_rate,
            },
            "fallback": {"fallback_used": self.stats["fallback_used"], "fallback_rate": fallback_rate},
            "thresholds": {
                "high_confidence_threshold": self.high_confidence_threshold,
                "low_confidence_threshold": self.low_confidence_threshold,
            },
            "routing_history_size": len(self.routing_history),
            "timestamp": datetime.now().isoformat(),
        }

    def get_recent_decisions(self, n: int = 10) -> List[RoutingDecision]:
        """获取最近的路由决策

        Args:
            n: 返回的决策数量（默认10）

        Returns:
            List[RoutingDecision]: 最近的路由决策列表
        """
        return self.routing_history[-n:]

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"IntelligentRiskControlRouter("
            f"total_routes={self.stats['total_routes']}, "
            f"high_threshold={self.high_confidence_threshold}, "
            f"low_threshold={self.low_confidence_threshold})"
        )
