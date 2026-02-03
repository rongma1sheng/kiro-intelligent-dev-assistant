"""双架构对比运行器

白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 1 并行运行

核心功能：
1. 同时运行架构A（Soldier硬编码风控）和架构B（策略层风控）
2. 收集两种架构的性能数据
3. 提取市场上下文
4. 选择实际执行的决策（保守/激进/平衡）
5. 将对比数据提供给元学习器学习

实施流程：
- Phase 1 (1-3月): 并行运行，收集数据（目标：1000+样本）
- 实际执行策略：保守（默认使用硬编码）、激进（使用策略层）、平衡（混合）

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from src.brain.risk_control_meta_learner import MarketContext, PerformanceMetrics, RiskControlMetaLearner


@dataclass
class ArchitectureDecision:
    """架构决策

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    Attributes:
        strategy: 策略类型（hardcoded/strategy_layer）
        positions: 建议的仓位列表
        risk_level: 风险等级（low/medium/high）
        confidence: 决策置信度（0-1）
        latency_ms: 决策延迟（毫秒）
        metadata: 额外的元数据
    """

    strategy: str
    positions: List[Dict[str, Any]]
    risk_level: str
    confidence: float
    latency_ms: float
    metadata: Optional[Dict[str, Any]] = None


class DualArchitectureRunner:
    """双架构对比运行器

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    核心职责：
    1. 并行运行架构A（Soldier硬编码风控）和架构B（策略层风控）
    2. 收集两种架构的决策和性能数据
    3. 提取市场上下文特征
    4. 选择实际执行的决策（保守/激进/平衡模式）
    5. 评估两种架构的性能表现
    6. 将对比数据提供给元学习器学习

    实施流程：
    - Phase 1 (1-3月): 并行运行，收集数据（目标：1000+样本）
    - 实际执行策略：
      * 保守模式（conservative）：默认使用架构A（硬编码风控）
      * 激进模式（aggressive）：默认使用架构B（策略层风控）
      * 平衡模式（balanced）：根据置信度选择

    Attributes:
        meta_learner: 元学习器实例
        architecture_a: 架构A（Soldier硬编码风控）
        architecture_b: 架构B（策略层风控）
        execution_mode: 实际执行模式（conservative/aggressive/balanced）
        performance_history: 性能历史记录
        decision_history: 决策历史记录
    """

    def __init__(
        self,
        meta_learner: RiskControlMetaLearner,
        architecture_a: Any,  # SoldierEngineV2实例
        architecture_b: Any,  # StrategyRiskManager实例
        execution_mode: str = "conservative",
    ):
        """初始化双架构运行器

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            meta_learner: 元学习器实例
            architecture_a: 架构A（Soldier硬编码风控）
            architecture_b: 架构B（策略层风控）
            execution_mode: 实际执行模式（conservative/aggressive/balanced）

        Raises:
            ValueError: 当execution_mode不在有效值中时
        """
        if execution_mode not in ["conservative", "aggressive", "balanced"]:
            raise ValueError(f"execution_mode必须是conservative/aggressive/balanced之一，" f"当前: {execution_mode}")

        self.meta_learner = meta_learner
        self.architecture_a = architecture_a
        self.architecture_b = architecture_b
        self.execution_mode = execution_mode

        # 性能历史记录
        self.performance_history: List[Dict[str, Any]] = []

        # 决策历史记录
        self.decision_history: List[Dict[str, Any]] = []

        # 统计信息
        self.stats = {
            "total_runs": 0,
            "architecture_a_selected": 0,
            "architecture_b_selected": 0,
            "architecture_a_wins": 0,
            "architecture_b_wins": 0,
            "ties": 0,
        }

        logger.info(f"[DualArchitectureRunner] 初始化完成 - " f"执行模式: {execution_mode}")

    async def run_parallel(self, market_data: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """并行运行两种架构

        白皮书依据: 第二章 2.2.4 风险控制元学习架构 - Phase 1 并行运行

        核心流程：
        1. 提取市场上下文
        2. 并行运行架构A和架构B
        3. 选择实际执行的决策
        4. 执行交易
        5. 评估性能
        6. 提供给元学习器学习

        Args:
            market_data: 市场数据（价格、成交量、波动率等）
            portfolio: 当前投资组合（持仓、资金等）

        Returns:
            Dict[str, Any]: 运行结果，包含：
                - selected_decision: 实际执行的决策
                - architecture_a_decision: 架构A的决策
                - architecture_b_decision: 架构B的决策
                - market_context: 市场上下文
                - execution_mode: 执行模式

        Example:
            >>> runner = DualArchitectureRunner(meta_learner, arch_a, arch_b)
            >>> result = await runner.run_parallel(market_data, portfolio)
            >>> print(f"选择的架构: {result['selected_decision']['strategy']}")
        """
        self.stats["total_runs"] += 1

        # 1. 提取市场上下文
        market_context = self._extract_market_context(market_data, portfolio)

        # 2. 并行运行架构A和架构B
        decision_a = await self._run_architecture_a(market_data, portfolio)
        decision_b = await self._run_architecture_b(market_data, portfolio)

        # 3. 选择实际执行的决策
        selected_decision = self._select_decision(decision_a, decision_b, market_context)

        # 4. 执行交易
        execution_result = await self._execute_trades(selected_decision, market_data, portfolio)

        # 5. 记录决策历史
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "market_context": market_context,
            "decision_a": decision_a,
            "decision_b": decision_b,
            "selected_decision": selected_decision,
            "execution_result": execution_result,
        }
        self.decision_history.append(decision_record)

        # 6. 评估性能（异步，不阻塞）
        # 注意：性能评估需要等待交易结果，通常在下一个周期进行

        logger.info(
            f"[DualArchitectureRunner] 并行运行完成 - "
            f"选择架构: {selected_decision.strategy}, "
            f"执行模式: {self.execution_mode}"
        )

        return {
            "selected_decision": selected_decision,
            "architecture_a_decision": decision_a,
            "architecture_b_decision": decision_b,
            "market_context": market_context,
            "execution_mode": self.execution_mode,
            "execution_result": execution_result,
        }

    def _extract_market_context(self, market_data: Dict[str, Any], portfolio: Dict[str, Any]) -> MarketContext:
        """提取市场上下文

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        从市场数据和投资组合中提取关键特征，用于元学习器的学习。

        Args:
            market_data: 市场数据
            portfolio: 投资组合

        Returns:
            MarketContext: 市场上下文
        """
        # 提取波动率（年化）
        volatility = market_data.get("volatility", 0.2)

        # 提取流动性（平均成交量）
        liquidity = market_data.get("avg_volume", 1000000.0)

        # 提取趋势强度（-1到1）
        trend_strength = market_data.get("trend_strength", 0.0)

        # 提取市场状态
        regime = market_data.get("regime", "sideways")

        # 提取资金规模
        aum = portfolio.get("total_value", 100000.0)

        # 计算组合集中度
        positions = portfolio.get("positions", {})
        if positions:
            position_values = [pos.get("value", 0) for pos in positions.values()]
            total_value = sum(position_values)
            if total_value > 0:
                # 赫芬达尔指数（HHI）
                concentration = sum((v / total_value) ** 2 for v in position_values)
            else:
                concentration = 0.0
        else:
            concentration = 0.0

        # 提取近期回撤
        recent_drawdown = portfolio.get("recent_drawdown", 0.0)

        return MarketContext(
            volatility=volatility,
            liquidity=liquidity,
            trend_strength=trend_strength,
            regime=regime,
            aum=aum,
            portfolio_concentration=concentration,
            recent_drawdown=recent_drawdown,
        )

    async def _run_architecture_a(self, market_data: Dict[str, Any], portfolio: Dict[str, Any]) -> ArchitectureDecision:
        """运行架构A（Soldier硬编码风控）

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            market_data: 市场数据
            portfolio: 投资组合

        Returns:
            ArchitectureDecision: 架构A的决策
        """
        import time  # pylint: disable=import-outside-toplevel

        start_time = time.perf_counter()

        try:
            # 调用Soldier的决策接口
            context = {"market_data": market_data, "portfolio": portfolio}

            decision = await self.architecture_a.decide(context)

            latency_ms = (time.perf_counter() - start_time) * 1000

            return ArchitectureDecision(
                strategy="hardcoded",
                positions=decision.get("positions", []),
                risk_level=decision.get("risk_level", "medium"),
                confidence=decision.get("confidence", 0.7),
                latency_ms=latency_ms,
                metadata=decision.get("metadata", {}),
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[DualArchitectureRunner] 架构A运行失败: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000

            # 返回保守的默认决策
            return ArchitectureDecision(
                strategy="hardcoded",
                positions=[],
                risk_level="low",
                confidence=0.0,
                latency_ms=latency_ms,
                metadata={"error": str(e)},
            )

    async def _run_architecture_b(self, market_data: Dict[str, Any], portfolio: Dict[str, Any]) -> ArchitectureDecision:
        """运行架构B（策略层风控）

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            market_data: 市场数据
            portfolio: 投资组合

        Returns:
            ArchitectureDecision: 架构B的决策
        """
        import time  # pylint: disable=import-outside-toplevel

        start_time = time.perf_counter()

        try:
            # 调用策略层的风控接口
            # 注意：这里假设architecture_b有decide方法
            # 如果architecture_b是StrategyRiskManager实例，需要根据具体接口调整

            context = {"market_data": market_data, "portfolio": portfolio}

            # 尝试调用decide方法（如果存在）
            if hasattr(self.architecture_b, "decide"):
                decision = await self.architecture_b.decide(context)
            else:
                # 如果没有decide方法，使用默认决策
                decision = {"positions": [], "risk_level": "medium", "confidence": 0.8}

            latency_ms = (time.perf_counter() - start_time) * 1000

            return ArchitectureDecision(
                strategy="strategy_layer",
                positions=decision.get("positions", []),
                risk_level=decision.get("risk_level", "medium"),
                confidence=decision.get("confidence", 0.8),
                latency_ms=latency_ms,
                metadata=decision.get("metadata", {}),
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[DualArchitectureRunner] 架构B运行失败: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000

            # 返回保守的默认决策
            return ArchitectureDecision(
                strategy="strategy_layer",
                positions=[],
                risk_level="low",
                confidence=0.0,
                latency_ms=latency_ms,
                metadata={"error": str(e)},
            )

    def _select_decision(
        self,
        decision_a: ArchitectureDecision,
        decision_b: ArchitectureDecision,
        market_context: MarketContext,  # pylint: disable=unused-argument
    ) -> ArchitectureDecision:
        """选择实际执行的决策

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        根据执行模式选择实际执行的决策：
        - conservative: 默认使用架构A（硬编码风控，保守）
        - aggressive: 默认使用架构B（策略层风控，激进）
        - balanced: 根据置信度选择

        Args:
            decision_a: 架构A的决策
            decision_b: 架构B的决策
            market_context: 市场上下文

        Returns:
            ArchitectureDecision: 选择的决策
        """
        if self.execution_mode == "conservative":
            # 保守模式：默认使用架构A
            selected = decision_a
            self.stats["architecture_a_selected"] += 1

        elif self.execution_mode == "aggressive":
            # 激进模式：默认使用架构B
            selected = decision_b
            self.stats["architecture_b_selected"] += 1

        else:  # balanced
            # 平衡模式：根据置信度选择
            if decision_a.confidence > decision_b.confidence:
                selected = decision_a
                self.stats["architecture_a_selected"] += 1
            elif decision_b.confidence > decision_a.confidence:
                selected = decision_b
                self.stats["architecture_b_selected"] += 1
            else:
                # 置信度相同，使用保守策略（架构A）
                selected = decision_a
                self.stats["architecture_a_selected"] += 1

        logger.info(
            f"[DualArchitectureRunner] 决策选择完成 - "
            f"选择: {selected.strategy}, "
            f"置信度: {selected.confidence:.2f}, "
            f"模式: {self.execution_mode}"
        )

        return selected

    async def _execute_trades(
        self,
        decision: ArchitectureDecision,
        market_data: Dict[str, Any],  # pylint: disable=unused-argument
        portfolio: Dict[str, Any],  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """执行交易

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            decision: 选择的决策
            market_data: 市场数据
            portfolio: 投资组合

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 注意：这里只是模拟执行，实际实现中需要调用真实的交易接口

        execution_result = {
            "success": True,
            "executed_positions": decision.positions,
            "timestamp": datetime.now().isoformat(),
            "strategy": decision.strategy,
        }

        logger.info(
            f"[DualArchitectureRunner] 交易执行完成 - "
            f"策略: {decision.strategy}, "
            f"仓位数: {len(decision.positions)}"
        )

        return execution_result

    async def _evaluate_performance(
        self,
        decision_a: ArchitectureDecision,
        decision_b: ArchitectureDecision,
        market_context: MarketContext,
        actual_returns: Dict[str, float],
    ) -> Tuple[PerformanceMetrics, PerformanceMetrics]:
        """评估两种架构的性能

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        计算两种架构的性能指标，用于元学习器的学习。

        Args:
            decision_a: 架构A的决策
            decision_b: 架构B的决策
            market_context: 市场上下文
            actual_returns: 实际收益率

        Returns:
            Tuple[PerformanceMetrics, PerformanceMetrics]: (架构A性能, 架构B性能)
        """
        # 计算架构A的性能
        perf_a = self._calculate_performance_metrics(decision_a, actual_returns)

        # 计算架构B的性能
        perf_b = self._calculate_performance_metrics(decision_b, actual_returns)

        # 记录性能历史
        performance_record = {
            "timestamp": datetime.now().isoformat(),
            "market_context": market_context,
            "architecture_a_performance": perf_a,
            "architecture_b_performance": perf_b,
        }
        self.performance_history.append(performance_record)

        # 提供给元学习器学习
        await self.meta_learner.observe_and_learn(market_context, perf_a, perf_b)

        logger.info(
            f"[DualArchitectureRunner] 性能评估完成 - "
            f"架构A夏普: {perf_a.sharpe_ratio:.2f}, "
            f"架构B夏普: {perf_b.sharpe_ratio:.2f}"
        )

        return perf_a, perf_b

    def _calculate_performance_metrics(
        self, decision: ArchitectureDecision, actual_returns: Dict[str, float]  # pylint: disable=unused-argument
    ) -> PerformanceMetrics:
        """计算性能指标

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            decision: 架构决策
            actual_returns: 实际收益率

        Returns:
            PerformanceMetrics: 性能指标
        """
        # 注意：这里是简化实现，实际需要根据真实交易数据计算

        # 模拟计算夏普比率
        sharpe_ratio = np.random.uniform(0.5, 2.0)

        # 模拟计算最大回撤
        max_drawdown = -np.random.uniform(0.05, 0.15)

        # 模拟计算胜率
        win_rate = np.random.uniform(0.5, 0.7)

        # 模拟计算盈亏比
        profit_factor = np.random.uniform(1.2, 2.5)

        # 模拟计算卡玛比率
        calmar_ratio = sharpe_ratio / abs(max_drawdown) if max_drawdown != 0 else 0.0

        # 模拟计算索提诺比率
        sortino_ratio = sharpe_ratio * 1.2

        # 决策延迟
        decision_latency_ms = decision.latency_ms

        return PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            decision_latency_ms=decision_latency_ms,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_runs = self.stats["total_runs"]

        if total_runs > 0:
            a_selection_rate = self.stats["architecture_a_selected"] / total_runs
            b_selection_rate = self.stats["architecture_b_selected"] / total_runs
        else:
            a_selection_rate = 0.0
            b_selection_rate = 0.0

        return {
            "total_runs": total_runs,
            "architecture_a_selected": self.stats["architecture_a_selected"],
            "architecture_b_selected": self.stats["architecture_b_selected"],
            "architecture_a_selection_rate": a_selection_rate,
            "architecture_b_selection_rate": b_selection_rate,
            "execution_mode": self.execution_mode,
            "decision_history_size": len(self.decision_history),
            "performance_history_size": len(self.performance_history),
        }
