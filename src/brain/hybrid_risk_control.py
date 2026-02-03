"""混合风控系统

白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 3 混合进化

核心功能：
1. 融合架构A（硬编码风控）和架构B（策略层风控）的决策
2. 实现动态权重调整
3. 实现规则评估引擎
4. 支持混合策略规则

实施流程：
- Phase 3 (6-12月): 混合进化，超越单一架构（目标：10000+样本）
- 混合策略：
  * 根据市场状态动态调整两种架构的权重
  * 执行混合策略规则（如：高波动时增加硬编码权重）

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.brain.risk_control_meta_learner import MarketContext


@dataclass
class HybridDecision:
    """混合决策

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    Attributes:
        positions: 混合后的仓位列表
        risk_level: 风险等级
        confidence: 决策置信度
        architecture_a_weight: 架构A的权重（0-1）
        architecture_b_weight: 架构B的权重（0-1）
        blending_reason: 混合原因
        rules_applied: 应用的规则列表
        timestamp: 决策时间戳
    """

    positions: List[Dict[str, Any]]
    risk_level: str
    confidence: float
    architecture_a_weight: float
    architecture_b_weight: float
    blending_reason: str
    rules_applied: List[str]
    timestamp: str


class HybridRiskControl:
    """混合风控系统

    白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 3 混合进化

    核心职责：
    1. 融合架构A（硬编码风控）和架构B（策略层风控）的决策
    2. 实现动态权重调整
    3. 实现规则评估引擎
    4. 支持混合策略规则
    5. 记录混合决策历史

    混合策略规则：
    - 高波动时：增加硬编码权重（保守）
    - 大资金时：增加策略层权重（灵活）
    - 回撤过大时：切换到硬编码（保守）
    - 趋势明确时：增加策略层权重（激进）

    Attributes:
        hybrid_rules: 混合策略规则列表
        decision_history: 混合决策历史
        stats: 混合统计信息
    """

    def __init__(self, hybrid_rules: Optional[List[Dict[str, Any]]] = None):
        """初始化混合风控系统

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            hybrid_rules: 混合策略规则列表（可选）
        """
        # 混合策略规则
        if hybrid_rules is None:
            # 使用默认规则
            self.hybrid_rules = self._get_default_rules()
        else:
            self.hybrid_rules = hybrid_rules

        # 混合决策历史
        self.decision_history: List[HybridDecision] = []

        # 统计信息
        self.stats = {
            "total_decisions": 0,
            "rules_triggered": {},
            "avg_architecture_a_weight": 0.0,
            "avg_architecture_b_weight": 0.0,
        }

        logger.info(f"[HybridRiskControl] 初始化完成 - " f"规则数: {len(self.hybrid_rules)}")

    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """获取默认混合策略规则

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Returns:
            List[Dict[str, Any]]: 默认规则列表
        """
        return [
            {
                "name": "high_volatility_conservative",
                "condition": "volatility > 0.30",
                "action": "increase_hardcoded_weight",
                "weight_adjustment": 0.3,  # 增加30%硬编码权重
                "reason": "高波动环境，增加保守风控权重",
            },
            {
                "name": "large_aum_flexible",
                "condition": "aum > 1000000",
                "action": "increase_strategy_layer_weight",
                "weight_adjustment": 0.2,  # 增加20%策略层权重
                "reason": "大资金规模，增加灵活风控权重",
            },
            {
                "name": "large_drawdown_conservative",
                "condition": "recent_drawdown < -0.10",
                "action": "use_hardcoded_only",
                "weight_adjustment": 1.0,  # 100%硬编码权重
                "reason": "回撤过大，切换到保守风控",
            },
            {
                "name": "strong_trend_aggressive",
                "condition": "abs(trend_strength) > 0.7",
                "action": "increase_strategy_layer_weight",
                "weight_adjustment": 0.25,  # 增加25%策略层权重
                "reason": "趋势明确，增加激进风控权重",
            },
            {
                "name": "low_liquidity_conservative",
                "condition": "liquidity < 500000",
                "action": "increase_hardcoded_weight",
                "weight_adjustment": 0.2,  # 增加20%硬编码权重
                "reason": "流动性不足，增加保守风控权重",
            },
        ]

    async def decide(
        self, market_context: MarketContext, decision_a: Dict[str, Any], decision_b: Dict[str, Any]
    ) -> HybridDecision:
        """混合决策

        白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 3 混合进化

        核心流程：
        1. 评估混合策略规则
        2. 计算动态权重
        3. 融合两种架构的决策
        4. 记录混合决策
        5. 更新统计信息

        Args:
            market_context: 市场上下文
            decision_a: 架构A的决策
            decision_b: 架构B的决策

        Returns:
            HybridDecision: 混合决策

        Example:
            >>> hybrid = HybridRiskControl()
            >>> context = MarketContext(...)
            >>> decision_a = {'positions': [...], 'risk_level': 'low'}
            >>> decision_b = {'positions': [...], 'risk_level': 'medium'}
            >>> hybrid_decision = await hybrid.decide(context, decision_a, decision_b)
            >>> print(f"架构A权重: {hybrid_decision.architecture_a_weight:.2%}")
            >>> print(f"架构B权重: {hybrid_decision.architecture_b_weight:.2%}")
        """
        self.stats["total_decisions"] += 1

        # 1. 评估混合策略规则
        rules_applied, weight_a, weight_b = self._evaluate_rules(market_context)

        # 2. 融合两种架构的决策
        blended_positions = self._blend_decisions(decision_a, decision_b, weight_a, weight_b)

        # 3. 计算混合后的风险等级
        risk_level = self._blend_risk_level(
            decision_a.get("risk_level", "medium"), decision_b.get("risk_level", "medium"), weight_a, weight_b
        )

        # 4. 计算混合后的置信度
        confidence = self._blend_confidence(
            decision_a.get("confidence", 0.7), decision_b.get("confidence", 0.8), weight_a, weight_b
        )

        # 5. 生成混合原因
        if rules_applied:
            blending_reason = f"应用{len(rules_applied)}条规则: " + ", ".join([rule["name"] for rule in rules_applied])
        else:
            blending_reason = "使用默认权重（50/50）"

        # 6. 创建混合决策
        decision = HybridDecision(
            positions=blended_positions,
            risk_level=risk_level,
            confidence=confidence,
            architecture_a_weight=weight_a,
            architecture_b_weight=weight_b,
            blending_reason=blending_reason,
            rules_applied=[rule["name"] for rule in rules_applied],
            timestamp=datetime.now().isoformat(),
        )

        # 7. 记录混合决策历史
        self.decision_history.append(decision)

        # 8. 限制历史记录大小（保留最近10000条）
        if len(self.decision_history) > 10000:
            self.decision_history = self.decision_history[-10000:]

        # 9. 更新统计信息
        self._update_statistics(decision, rules_applied)

        logger.info(
            f"[HybridRiskControl] 混合决策完成 - "
            f"架构A权重: {weight_a:.2%}, "
            f"架构B权重: {weight_b:.2%}, "
            f"规则数: {len(rules_applied)}"
        )

        return decision

    def _evaluate_rules(self, market_context: MarketContext) -> Tuple[List[Dict[str, Any]], float, float]:
        """评估混合策略规则

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            market_context: 市场上下文

        Returns:
            Tuple[List[Dict[str, Any]], float, float]: (应用的规则列表, 架构A权重, 架构B权重)
        """
        # 初始权重（默认50/50）
        weight_a = 0.5
        weight_b = 0.5

        # 应用的规则列表
        rules_applied = []

        # 评估每条规则
        for rule in self.hybrid_rules:
            condition = rule["condition"]

            # 评估条件
            if self._evaluate_condition(condition, market_context):
                rules_applied.append(rule)

                # 应用权重调整
                action = rule["action"]
                adjustment = rule["weight_adjustment"]

                if action == "increase_hardcoded_weight":
                    weight_a += adjustment
                    weight_b -= adjustment
                elif action == "increase_strategy_layer_weight":
                    weight_b += adjustment
                    weight_a -= adjustment
                elif action == "use_hardcoded_only":
                    weight_a = 1.0
                    weight_b = 0.0
                elif action == "use_strategy_layer_only":
                    weight_a = 0.0
                    weight_b = 1.0

        # 归一化权重（确保和为1）
        total_weight = weight_a + weight_b
        if total_weight > 0:
            weight_a /= total_weight
            weight_b /= total_weight
        else:
            # 如果权重和为0，使用默认权重
            weight_a = 0.5
            weight_b = 0.5

        # 限制权重范围（0-1）
        weight_a = max(0.0, min(1.0, weight_a))
        weight_b = max(0.0, min(1.0, weight_b))

        return rules_applied, weight_a, weight_b

    def _evaluate_condition(self, condition: str, market_context: MarketContext) -> bool:
        """评估条件

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        支持的条件：
        - volatility > 0.30
        - aum > 1000000
        - recent_drawdown < -0.10
        - abs(trend_strength) > 0.7
        - liquidity < 500000

        Args:
            condition: 条件字符串
            market_context: 市场上下文

        Returns:
            bool: 条件是否满足
        """
        try:
            # 构建评估环境
            eval_env = {
                "volatility": market_context.volatility,
                "liquidity": market_context.liquidity,
                "trend_strength": market_context.trend_strength,
                "aum": market_context.aum,
                "portfolio_concentration": market_context.portfolio_concentration,
                "recent_drawdown": market_context.recent_drawdown,
                "abs": abs,
                "max": max,
                "min": min,
            }

            # 评估条件
            result = eval(condition, {"__builtins__": {}}, eval_env)  # pylint: disable=w0123

            return bool(result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[HybridRiskControl] 条件评估失败: {condition}, 错误: {e}")
            return False

    def _blend_decisions(
        self, decision_a: Dict[str, Any], decision_b: Dict[str, Any], weight_a: float, weight_b: float
    ) -> List[Dict[str, Any]]:
        """融合两种架构的决策

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        融合策略：
        1. 合并两种架构的仓位列表
        2. 对于相同股票，按权重调整仓位大小
        3. 对于不同股票，按权重保留

        Args:
            decision_a: 架构A的决策
            decision_b: 架构B的决策
            weight_a: 架构A的权重
            weight_b: 架构B的权重

        Returns:
            List[Dict[str, Any]]: 混合后的仓位列表
        """
        positions_a = decision_a.get("positions", [])
        positions_b = decision_b.get("positions", [])

        # 构建股票代码到仓位的映射
        positions_map = {}

        # 添加架构A的仓位
        for pos in positions_a:
            symbol = pos.get("symbol", "")
            if symbol:
                positions_map[symbol] = {
                    "symbol": symbol,
                    "size": pos.get("size", 0) * weight_a,
                    "source": "architecture_a",
                }

        # 添加架构B的仓位
        for pos in positions_b:
            symbol = pos.get("symbol", "")
            if symbol:
                if symbol in positions_map:
                    # 相同股票，累加仓位
                    positions_map[symbol]["size"] += pos.get("size", 0) * weight_b
                    positions_map[symbol]["source"] = "both"
                else:
                    # 不同股票，添加新仓位
                    positions_map[symbol] = {
                        "symbol": symbol,
                        "size": pos.get("size", 0) * weight_b,
                        "source": "architecture_b",
                    }

        # 转换为列表
        blended_positions = list(positions_map.values())

        return blended_positions

    def _blend_risk_level(self, risk_level_a: str, risk_level_b: str, weight_a: float, weight_b: float) -> str:
        """融合风险等级

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            risk_level_a: 架构A的风险等级
            risk_level_b: 架构B的风险等级
            weight_a: 架构A的权重
            weight_b: 架构B的权重

        Returns:
            str: 混合后的风险等级
        """
        # 风险等级映射
        risk_map = {"low": 1, "medium": 2, "high": 3}

        # 计算加权平均
        risk_a = risk_map.get(risk_level_a, 2)
        risk_b = risk_map.get(risk_level_b, 2)

        blended_risk = risk_a * weight_a + risk_b * weight_b

        # 转换回风险等级
        if blended_risk < 1.5:  # pylint: disable=no-else-return
            return "low"
        elif blended_risk < 2.5:
            return "medium"
        else:
            return "high"

    def _blend_confidence(self, confidence_a: float, confidence_b: float, weight_a: float, weight_b: float) -> float:
        """融合置信度

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            confidence_a: 架构A的置信度
            confidence_b: 架构B的置信度
            weight_a: 架构A的权重
            weight_b: 架构B的权重

        Returns:
            float: 混合后的置信度
        """
        # 加权平均
        blended_confidence = confidence_a * weight_a + confidence_b * weight_b

        # 限制范围（0-1）
        blended_confidence = max(0.0, min(1.0, blended_confidence))

        return blended_confidence

    def _update_statistics(self, decision: HybridDecision, rules_applied: List[Dict[str, Any]]) -> None:
        """更新统计信息

        Args:
            decision: 混合决策
            rules_applied: 应用的规则列表
        """
        # 更新规则触发统计
        for rule in rules_applied:
            rule_name = rule["name"]
            if rule_name not in self.stats["rules_triggered"]:
                self.stats["rules_triggered"][rule_name] = 0
            self.stats["rules_triggered"][rule_name] += 1

        # 更新平均权重
        total_decisions = self.stats["total_decisions"]
        self.stats["avg_architecture_a_weight"] = (
            self.stats["avg_architecture_a_weight"] * (total_decisions - 1) + decision.architecture_a_weight
        ) / total_decisions
        self.stats["avg_architecture_b_weight"] = (
            self.stats["avg_architecture_b_weight"] * (total_decisions - 1) + decision.architecture_b_weight
        ) / total_decisions

    def get_statistics(self) -> Dict[str, Any]:
        """获取混合统计信息

        Returns:
            Dict[str, Any]: 混合统计信息
        """
        return {
            "total_decisions": self.stats["total_decisions"],
            "avg_architecture_a_weight": self.stats["avg_architecture_a_weight"],
            "avg_architecture_b_weight": self.stats["avg_architecture_b_weight"],
            "rules_triggered": self.stats["rules_triggered"].copy(),
            "total_rules": len(self.hybrid_rules),
            "decision_history_size": len(self.decision_history),
            "timestamp": datetime.now().isoformat(),
        }

    def get_recent_decisions(self, n: int = 10) -> List[HybridDecision]:
        """获取最近的混合决策

        Args:
            n: 返回的决策数量（默认10）

        Returns:
            List[HybridDecision]: 最近的混合决策列表
        """
        return self.decision_history[-n:]

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"HybridRiskControl("
            f"total_decisions={self.stats['total_decisions']}, "
            f"rules={len(self.hybrid_rules)})"
        )
