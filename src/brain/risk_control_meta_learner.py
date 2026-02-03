"""风险控制元学习器

白皮书依据: 第二章 2.2.4 风险控制元学习架构

核心理念: 让机器通过对比学习，自动进化出最优风控策略

三层进化架构:
1. 市场实战 - 真实交易数据、盈亏结果、风险事件
2. 双架构对比 - 架构A（Soldier硬编码风控）vs 架构B（策略层风控）
3. 元学习器 - 观察、学习、进化

Author: MIA Team
Date: 2026-01-21
Version: v1.0
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger


class RiskControlStrategy(Enum):
    """风控策略类型

    白皮书依据: 第二章 2.2.4 风险控制元学习架构
    """

    HARDCODED = "hardcoded"  # 硬编码风控（架构A）
    STRATEGY_LAYER = "strategy_layer"  # 策略层风控（架构B）
    HYBRID = "hybrid"  # 混合风控
    EVOLVED = "evolved"  # 进化风控


@dataclass
class MarketContext:
    """市场上下文

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    用于描述当前市场环境的关键特征，帮助元学习器判断
    哪种风控策略在当前环境下更优。

    Attributes:
        volatility: 波动率（年化）
        liquidity: 流动性（平均成交量）
        trend_strength: 趋势强度（-1到1，负值为下跌，正值为上涨）
        regime: 市场状态（bull/bear/choppy/sideways）
        aum: 当前资金规模（Account Under Management）
        portfolio_concentration: 组合集中度（0到1）
        recent_drawdown: 近期回撤（负值）
    """

    volatility: float
    liquidity: float
    trend_strength: float
    regime: str
    aum: float
    portfolio_concentration: float
    recent_drawdown: float


@dataclass
class PerformanceMetrics:
    """性能指标

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    用于评估风控策略的表现，综合多个维度的指标。

    Attributes:
        sharpe_ratio: 夏普比率（风险调整后收益）
        max_drawdown: 最大回撤（负值）
        win_rate: 胜率（0到1）
        profit_factor: 盈亏比（总盈利/总亏损）
        calmar_ratio: 卡玛比率（年化收益/最大回撤）
        sortino_ratio: 索提诺比率（下行风险调整后收益）
        decision_latency_ms: 决策延迟（毫秒）
    """

    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    sortino_ratio: float
    decision_latency_ms: float


@dataclass
class LearningDataPoint:
    """学习数据点

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    记录一次双架构对比的完整数据，用于元学习器的学习。

    Attributes:
        timestamp: 时间戳
        market_context: 市场上下文
        architecture_a_performance: 架构A（硬编码）的性能
        architecture_b_performance: 架构B（策略层）的性能
        winner: 优胜者（strategy_a/strategy_b/tie）
        metadata: 额外的元数据
    """

    timestamp: str
    market_context: MarketContext
    architecture_a_performance: PerformanceMetrics
    architecture_b_performance: PerformanceMetrics
    winner: str
    metadata: Optional[Dict[str, Any]] = None


class RiskControlMetaLearner:
    """风险控制元学习器

    白皮书依据: 第二章 2.2.4 风险控制元学习架构

    核心功能：
    1. 观察两种风控方案在不同市场环境下的表现
    2. 学习市场状态 → 最优风控方案的映射
    3. 自动进化出混合策略或新策略
    4. 持续优化风控参数

    实施流程：
    - Phase 1 (1-3月): 并行运行，收集数据（目标：1000+样本）
    - Phase 2 (3-6月): 智能切换，模式识别（目标：5000+样本）
    - Phase 3 (6-12月): 混合进化，超越单一架构（目标：10000+样本）
    - Phase 4 (12月+): 持续优化，自动进化（目标：20000+样本）

    Attributes:
        experience_db: 经验数据库，存储(市场上下文, 风控方案, 性能指标)
        strategy_selector_model: 策略选择模型（RandomForest/XGBoost）
        param_optimizer_model: 参数优化模型
        current_best_strategy: 当前最优策略类型
        current_best_params: 当前最优策略参数
        learning_stats: 学习统计信息
    """

    def __init__(self):
        """初始化元学习器

        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        """
        # 经验数据库
        self.experience_db: List[LearningDataPoint] = []

        # 学习模型（延迟初始化）
        self.strategy_selector_model = None  # 策略选择模型
        self.param_optimizer_model = None  # 参数优化模型

        # 当前最优策略
        self.current_best_strategy = RiskControlStrategy.HARDCODED
        self.current_best_params: Dict[str, Any] = {}

        # 学习统计
        self.learning_stats = {
            "total_samples": 0,
            "hardcoded_wins": 0,
            "strategy_layer_wins": 0,
            "hybrid_wins": 0,
            "evolved_wins": 0,
            "ties": 0,
            "model_trained": False,
            "model_accuracy": 0.0,
            "last_evolution_sample": 0,
        }

        logger.info("[MetaLearner] 风险控制元学习器初始化完成 - " f"初始策略: {self.current_best_strategy.value}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取学习统计信息

        Returns:
            Dict[str, Any]: 学习统计信息
        """
        return {
            "learning_stats": self.learning_stats.copy(),
            "experience_db_size": len(self.experience_db),
            "current_best_strategy": self.current_best_strategy.value,
            "has_best_params": bool(self.current_best_params),
            "timestamp": datetime.now().isoformat(),
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"RiskControlMetaLearner("
            f"samples={self.learning_stats['total_samples']}, "
            f"best_strategy={self.current_best_strategy.value}, "
            f"model_trained={self.learning_stats['model_trained']})"
        )

    async def observe_and_learn(
        self,
        market_context: MarketContext,
        architecture_a_performance: PerformanceMetrics,
        architecture_b_performance: PerformanceMetrics,
    ) -> str:
        """观察并学习

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        核心学习流程：
        1. 记录市场上下文和两种策略的表现
        2. 判断哪种策略在当前环境下更优
        3. 更新学习模型
        4. 进化出新的策略

        Args:
            market_context: 市场上下文
            architecture_a_performance: 架构A（硬编码）的性能
            architecture_b_performance: 架构B（策略层）的性能

        Returns:
            str: 优胜者（'strategy_a', 'strategy_b', 'tie'）
        """
        from datetime import datetime  # pylint: disable=import-outside-toplevel,w0621,w0404

        # 1. 记录经验
        data_point = LearningDataPoint(
            timestamp=datetime.now().isoformat(),
            market_context=market_context,
            architecture_a_performance=architecture_a_performance,
            architecture_b_performance=architecture_b_performance,
            winner="",  # 将在下一步确定
            metadata=None,
        )

        # 2. 判断优胜者
        winner = self._determine_winner(architecture_a_performance, architecture_b_performance)
        data_point.winner = winner

        # 3. 保存经验
        self.experience_db.append(data_point)
        self.learning_stats["total_samples"] += 1

        # 4. 更新统计
        if winner == "strategy_a":
            self.learning_stats["hardcoded_wins"] += 1
        elif winner == "strategy_b":
            self.learning_stats["strategy_layer_wins"] += 1
        else:
            self.learning_stats["ties"] += 1

        # 5. 学习市场模式（异步）
        await self._learn_market_patterns()

        # 6. 进化新策略（每100个样本进化一次）
        if self.learning_stats["total_samples"] % 100 == 0:
            await self._evolve_new_strategy()
            self.learning_stats["last_evolution_sample"] = self.learning_stats["total_samples"]

        logger.info(
            f"[MetaLearner] 学习完成 - "
            f"样本数: {self.learning_stats['total_samples']}, "
            f"硬编码胜: {self.learning_stats['hardcoded_wins']}, "
            f"策略层胜: {self.learning_stats['strategy_layer_wins']}, "
            f"平局: {self.learning_stats['ties']}, "
            f"优胜者: {winner}"
        )

        return winner

    def _determine_winner(self, perf_a: PerformanceMetrics, perf_b: PerformanceMetrics) -> str:
        """判断优胜者

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        综合评分公式：
        Score = Sharpe * 0.4 + (1 - |MaxDD|) * 0.3 + WinRate * 0.2 + ProfitFactor/3 * 0.1

        Args:
            perf_a: 架构A的性能指标
            perf_b: 架构B的性能指标

        Returns:
            str: 优胜者（'strategy_a', 'strategy_b', 'tie'）
        """
        # 计算架构A的综合评分
        score_a = (
            perf_a.sharpe_ratio * 0.4
            + (1 - abs(perf_a.max_drawdown)) * 0.3
            + perf_a.win_rate * 0.2
            + min(perf_a.profit_factor / 3, 1.0) * 0.1
        )

        # 计算架构B的综合评分
        score_b = (
            perf_b.sharpe_ratio * 0.4
            + (1 - abs(perf_b.max_drawdown)) * 0.3
            + perf_b.win_rate * 0.2
            + min(perf_b.profit_factor / 3, 1.0) * 0.1
        )

        # 判断优胜者（5%阈值）
        if score_a > score_b * 1.05:  # A显著优于B  # pylint: disable=no-else-return
            return "strategy_a"
        elif score_b > score_a * 1.05:  # B显著优于A
            return "strategy_b"
        else:
            return "tie"

    async def _learn_market_patterns(self) -> None:
        """学习市场模式

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        使用机器学习模型学习：
        市场上下文 → 最优风控策略
        """
        if len(self.experience_db) < 50:  # 至少需要50个样本
            logger.debug(f"[MetaLearner] 样本数不足（{len(self.experience_db)}/50），" f"跳过模型训练")
            return

        try:
            # 准备训练数据
            X = []  # 特征：市场上下文
            y = []  # 标签：最优策略

            for data_point in self.experience_db[-1000:]:  # 使用最近1000个样本
                # 特征工程
                features = self._extract_features(data_point.market_context)
                X.append(features)

                # 标签（1=架构A, 0=架构B, 平局随机选择）
                if data_point.winner == "strategy_a":
                    y.append(1)
                elif data_point.winner == "strategy_b":
                    y.append(0)
                else:
                    # 平局随机选择
                    y.append(np.random.randint(0, 2))

            # 训练模型（使用RandomForest）
            from sklearn.ensemble import RandomForestClassifier  # pylint: disable=import-outside-toplevel

            if self.strategy_selector_model is None:
                self.strategy_selector_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)

            self.strategy_selector_model.fit(X, y)

            # 评估模型
            accuracy = self.strategy_selector_model.score(X, y)
            self.learning_stats["model_trained"] = True
            self.learning_stats["model_accuracy"] = accuracy

            logger.info(f"[MetaLearner] 模型训练完成 - " f"样本数: {len(X)}, " f"准确率: {accuracy:.2%}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[MetaLearner] 模型训练失败: {e}")

    def _extract_features(self, context: MarketContext) -> List[float]:
        """特征提取

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            context: 市场上下文

        Returns:
            List[float]: 特征向量
        """
        return [
            context.volatility,
            context.liquidity,
            context.trend_strength,
            1.0 if context.regime == "bull" else 0.0,
            1.0 if context.regime == "bear" else 0.0,
            np.log(max(context.aum, 1.0)),  # 对数化资金规模，避免log(0)
            context.portfolio_concentration,
            abs(context.recent_drawdown),
        ]

    async def _evolve_new_strategy(self) -> Dict[str, Any]:
        """进化新策略

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        基于学习到的模式，进化出混合策略或新策略

        Returns:
            Dict[str, Any]: 混合策略配置
        """
        logger.info("[MetaLearner] 开始进化新策略...")

        # 分析哪种策略在什么情况下更优
        patterns = self._analyze_winning_patterns()

        # 生成混合策略
        hybrid_strategy = self._generate_hybrid_strategy(patterns)

        # 保存进化结果
        self.current_best_strategy = RiskControlStrategy.HYBRID
        self.current_best_params = hybrid_strategy
        self.learning_stats["hybrid_wins"] += 1

        logger.info(
            f"[MetaLearner] 新策略进化完成 - "
            f"类型: {self.current_best_strategy.value}, "
            f"规则数: {len(hybrid_strategy.get('rules', []))}"
        )

        return hybrid_strategy

    def _analyze_winning_patterns(self) -> Dict[str, Any]:
        """分析获胜模式

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Returns:
            Dict[str, Any]: 获胜模式分析结果
        """
        patterns = {
            "hardcoded_wins_when": [],  # 硬编码胜出的条件
            "strategy_layer_wins_when": [],  # 策略层胜出的条件
            "optimal_thresholds": {},  # 最优阈值
        }

        # 分析硬编码胜出的场景
        for data_point in self.experience_db:
            context = data_point.market_context

            if data_point.winner == "strategy_a":
                patterns["hardcoded_wins_when"].append(
                    {
                        "volatility": context.volatility,
                        "aum": context.aum,
                        "regime": context.regime,
                        "drawdown": context.recent_drawdown,
                    }
                )
            elif data_point.winner == "strategy_b":
                patterns["strategy_layer_wins_when"].append(
                    {
                        "volatility": context.volatility,
                        "aum": context.aum,
                        "regime": context.regime,
                        "drawdown": context.recent_drawdown,
                    }
                )

        # 计算最优阈值
        if patterns["hardcoded_wins_when"]:
            hardcoded_volatility = np.mean([p["volatility"] for p in patterns["hardcoded_wins_when"]])
            patterns["optimal_thresholds"]["volatility_threshold"] = hardcoded_volatility

            hardcoded_aum = np.mean([p["aum"] for p in patterns["hardcoded_wins_when"]])
            patterns["optimal_thresholds"]["aum_threshold"] = hardcoded_aum

        return patterns

    def _generate_hybrid_strategy(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """生成混合策略

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        混合策略规则：
        1. 根据市场状态动态选择风控方案
        2. 或者混合两种方案的参数

        Args:
            patterns: 获胜模式分析结果

        Returns:
            Dict[str, Any]: 混合策略配置
        """
        hybrid_strategy = {
            "type": "hybrid",
            "rules": [],
            "default_strategy": "hardcoded",  # 默认使用硬编码（保守）
            "switch_conditions": [],
        }

        # 规则1: 高波动时使用硬编码
        if "volatility_threshold" in patterns["optimal_thresholds"]:
            threshold = patterns["optimal_thresholds"]["volatility_threshold"]
            hybrid_strategy["rules"].append(
                {
                    "condition": f"volatility > {threshold:.4f}",
                    "action": "use_hardcoded",
                    "reason": "高波动环境，使用保守的硬编码风控",
                }
            )

        # 规则2: 大资金时使用策略层
        if "aum_threshold" in patterns["optimal_thresholds"]:
            threshold = patterns["optimal_thresholds"]["aum_threshold"]
            hybrid_strategy["rules"].append(
                {
                    "condition": f"aum > {threshold:.2f}",
                    "action": "use_strategy_layer",
                    "reason": "大资金规模，使用灵活的策略层风控",
                }
            )
        else:
            # 默认阈值
            hybrid_strategy["rules"].append(
                {
                    "condition": "aum > 100000",
                    "action": "use_strategy_layer",
                    "reason": "大资金规模，使用灵活的策略层风控",
                }
            )

        # 规则3: 回撤过大时切换到硬编码
        hybrid_strategy["rules"].append(
            {"condition": "recent_drawdown < -0.10", "action": "use_hardcoded", "reason": "回撤过大，切换到保守风控"}
        )

        return hybrid_strategy

    def predict_best_strategy(self, market_context: MarketContext) -> Tuple[RiskControlStrategy, float]:
        """预测最优风控策略

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        使用训练好的模型预测在当前市场环境下哪种风控策略更优。

        Args:
            market_context: 当前市场上下文

        Returns:
            Tuple[RiskControlStrategy, float]: (最优策略, 置信度)

        Example:
            >>> context = MarketContext(
            ...     volatility=0.25,
            ...     liquidity=1000000.0,
            ...     trend_strength=0.5,
            ...     regime='bull',
            ...     aum=100000.0,
            ...     portfolio_concentration=0.3,
            ...     recent_drawdown=-0.05
            ... )
            >>> strategy, confidence = learner.predict_best_strategy(context)
            >>> print(f"推荐策略: {strategy.value}, 置信度: {confidence:.2%}")
        """
        # 如果模型未训练，返回默认策略（保守）
        if not self.learning_stats["model_trained"] or self.strategy_selector_model is None:
            logger.warning("[MetaLearner] 模型未训练，返回默认策略（硬编码风控）")
            return RiskControlStrategy.HARDCODED, 0.5

        try:
            # 提取特征
            features = self._extract_features(market_context)

            # 预测（返回概率分布）
            proba = self.strategy_selector_model.predict_proba([features])[0]

            # 获取预测结果和置信度
            prediction = self.strategy_selector_model.predict([features])[0]
            confidence = max(proba)  # 最大概率作为置信度

            # 转换为策略类型
            if prediction == 1:
                strategy = RiskControlStrategy.HARDCODED
            else:
                strategy = RiskControlStrategy.STRATEGY_LAYER

            logger.info(f"[MetaLearner] 预测完成 - " f"策略: {strategy.value}, " f"置信度: {confidence:.2%}")

            return strategy, confidence

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[MetaLearner] 预测失败: {e}")
            # 返回默认策略
            return RiskControlStrategy.HARDCODED, 0.5

    def get_learning_report(self) -> Dict[str, Any]:
        """获取学习报告

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        生成详细的学习报告，包括：
        - 学习统计摘要
        - 各策略胜率
        - 进化历史
        - 优化建议

        Returns:
            Dict[str, Any]: 学习报告

        Example:
            >>> report = learner.get_learning_report()
            >>> print(f"总样本数: {report['summary']['total_samples']}")
            >>> print(f"硬编码胜率: {report['win_rates']['hardcoded']:.2%}")
        """
        # 计算胜率
        total_samples = self.learning_stats["total_samples"]

        if total_samples > 0:
            hardcoded_win_rate = self.learning_stats["hardcoded_wins"] / total_samples
            strategy_layer_win_rate = self.learning_stats["strategy_layer_wins"] / total_samples
            tie_rate = self.learning_stats["ties"] / total_samples
        else:
            hardcoded_win_rate = 0.0
            strategy_layer_win_rate = 0.0
            tie_rate = 0.0

        # 生成建议
        recommendations = []

        # 建议1: 样本数量
        if total_samples < 50:
            recommendations.append(
                {
                    "type": "data_collection",
                    "priority": "high",
                    "message": f"样本数不足（{total_samples}/50），建议继续收集数据",
                }
            )
        elif total_samples < 1000:
            recommendations.append(
                {
                    "type": "data_collection",
                    "priority": "medium",
                    "message": f"样本数适中（{total_samples}/1000），可以开始智能切换",
                }
            )
        else:
            recommendations.append(
                {
                    "type": "data_collection",
                    "priority": "low",
                    "message": f"样本数充足（{total_samples}），可以进行混合进化",
                }
            )

        # 建议2: 策略选择
        if hardcoded_win_rate > 0.6:
            recommendations.append(
                {
                    "type": "strategy_selection",
                    "priority": "high",
                    "message": f"硬编码风控表现优异（胜率{hardcoded_win_rate:.2%}），建议优先使用",
                }
            )
        elif strategy_layer_win_rate > 0.6:
            recommendations.append(
                {
                    "type": "strategy_selection",
                    "priority": "high",
                    "message": f"策略层风控表现优异（胜率{strategy_layer_win_rate:.2%}），建议优先使用",
                }
            )
        else:
            recommendations.append(
                {"type": "strategy_selection", "priority": "medium", "message": "两种策略表现相近，建议使用混合策略"}
            )

        # 建议3: 模型训练
        if not self.learning_stats["model_trained"]:
            recommendations.append(
                {"type": "model_training", "priority": "high", "message": "模型未训练，建议收集更多样本后训练模型"}
            )
        elif self.learning_stats["model_accuracy"] < 0.7:
            recommendations.append(
                {
                    "type": "model_training",
                    "priority": "medium",
                    "message": f'模型准确率较低（{self.learning_stats["model_accuracy"]:.2%}），建议优化特征工程',
                }
            )
        else:
            recommendations.append(
                {
                    "type": "model_training",
                    "priority": "low",
                    "message": f'模型表现良好（准确率{self.learning_stats["model_accuracy"]:.2%}）',
                }
            )

        # 构建报告
        report = {
            "summary": {
                "total_samples": total_samples,
                "model_trained": self.learning_stats["model_trained"],
                "model_accuracy": self.learning_stats["model_accuracy"],
                "current_best_strategy": self.current_best_strategy.value,
                "last_evolution_sample": self.learning_stats["last_evolution_sample"],
            },
            "win_rates": {
                "hardcoded": hardcoded_win_rate,
                "strategy_layer": strategy_layer_win_rate,
                "hybrid": self.learning_stats["hybrid_wins"] / max(total_samples, 1),
                "evolved": self.learning_stats["evolved_wins"] / max(total_samples, 1),
                "tie": tie_rate,
            },
            "evolution": {
                "hybrid_strategies_created": self.learning_stats["hybrid_wins"],
                "evolved_strategies_created": self.learning_stats["evolved_wins"],
                "evolution_frequency": 100,  # 每100个样本进化一次
            },
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"[MetaLearner] 学习报告生成完成 - "
            f"样本数: {total_samples}, "
            f"硬编码胜率: {hardcoded_win_rate:.2%}, "
            f"策略层胜率: {strategy_layer_win_rate:.2%}"
        )

        return report
