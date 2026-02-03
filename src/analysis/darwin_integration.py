"""达尔文进化集成系统

白皮书依据: 第五章 5.3 达尔文进化体系集成

DarwinIntegration作为LLM策略分析系统与达尔文进化体系的桥梁，
负责策略优化建议、进化方向指导和生命周期预测。

核心功能:
- 策略优化建议生成
- 进化方向指导
- 生命周期预测
- 基因胶囊管理
- 演化树构建
- 反向黑名单管理

性能要求:
- 优化建议生成 < 5秒
- 生命周期预测 < 2秒
- 进化报告生成 < 10秒
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger


@dataclass
class OptimizationSuggestion:
    """优化建议数据模型

    Attributes:
        suggestion_id: 建议ID
        strategy_id: 策略ID
        suggestion_type: 建议类型 (parameter/feature/logic/risk)
        description: 建议描述
        expected_improvement: 预期改进幅度
        priority: 优先级 (high/medium/low)
        implementation_difficulty: 实施难度 (easy/medium/hard)
        created_at: 创建时间
    """

    suggestion_id: str
    strategy_id: str
    suggestion_type: str
    description: str
    expected_improvement: float
    priority: str
    implementation_difficulty: str
    created_at: str


@dataclass
class EvolutionDirection:
    """进化方向数据模型

    Attributes:
        direction_id: 方向ID
        strategy_id: 策略ID
        direction_type: 方向类型 (factor/parameter/logic/ensemble)
        description: 方向描述
        confidence: 置信度
        rationale: 理由
        created_at: 创建时间
    """

    direction_id: str
    strategy_id: str
    direction_type: str
    description: str
    confidence: float
    rationale: str
    created_at: str


@dataclass
class LifecyclePrediction:
    """生命周期预测数据模型

    Attributes:
        prediction_id: 预测ID
        strategy_id: 策略ID
        current_stage: 当前阶段 (growth/mature/decline/obsolete)
        remaining_days: 预计剩余有效天数
        decay_rate: 衰减率
        confidence: 预测置信度
        factors: 影响因素
        created_at: 创建时间
    """

    prediction_id: str
    strategy_id: str
    current_stage: str
    remaining_days: int
    decay_rate: float
    confidence: float
    factors: List[str]
    created_at: str


@dataclass
class EvolutionReport:
    """进化报告数据模型

    Attributes:
        report_id: 报告ID
        strategy_id: 策略ID
        optimization_suggestions: 优化建议列表
        evolution_directions: 进化方向列表
        lifecycle_prediction: 生命周期预测
        gene_capsule_id: 基因胶囊ID
        z2h_status: Z2H钢印状态
        created_at: 创建时间
    """

    report_id: str
    strategy_id: str
    optimization_suggestions: List[OptimizationSuggestion]
    evolution_directions: List[EvolutionDirection]
    lifecycle_prediction: LifecyclePrediction
    gene_capsule_id: Optional[str]
    z2h_status: str
    created_at: str


class DarwinIntegration:
    """达尔文进化集成系统

    白皮书依据: 第五章 5.3 达尔文进化体系集成

    作为LLM策略分析系统与达尔文进化体系的桥梁，负责：
    1. 生成策略优化建议
    2. 指导进化方向
    3. 预测策略生命周期
    4. 管理基因胶囊和演化树
    5. 维护反向黑名单

    Attributes:
        knowledge_base: 知识库系统
        strategy_analyzer: 策略分析器
    """

    def __init__(self, knowledge_base=None, strategy_analyzer=None):
        """初始化达尔文进化集成系统

        Args:
            knowledge_base: 知识库系统实例
            strategy_analyzer: 策略分析器实例
        """
        self.knowledge_base = knowledge_base
        self.strategy_analyzer = strategy_analyzer

        logger.info("初始化DarwinIntegration")

    # ==================== 策略优化建议 ====================

    def generate_optimization_suggestions(
        self, strategy_id: str, analysis_results: Dict[str, Any], arena_results: Optional[Dict[str, Any]] = None
    ) -> List[OptimizationSuggestion]:
        """生成策略优化建议

        白皮书依据: 第五章 5.3.1 进化协同流程

        基于策略分析结果和Arena测试结果，生成具体的优化建议。

        Args:
            strategy_id: 策略ID
            analysis_results: 29维度分析结果
            arena_results: Arena测试结果

        Returns:
            优化建议列表

        Raises:
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        if not analysis_results:
            raise ValueError("分析结果不能为空")

        suggestions = []

        try:
            # 1. 参数优化建议
            param_suggestions = self._generate_parameter_suggestions(strategy_id, analysis_results)
            suggestions.extend(param_suggestions)

            # 2. 特征优化建议
            feature_suggestions = self._generate_feature_suggestions(strategy_id, analysis_results)
            suggestions.extend(feature_suggestions)

            # 3. 逻辑优化建议
            logic_suggestions = self._generate_logic_suggestions(strategy_id, analysis_results)
            suggestions.extend(logic_suggestions)

            # 4. 风险优化建议
            risk_suggestions = self._generate_risk_suggestions(strategy_id, analysis_results, arena_results)
            suggestions.extend(risk_suggestions)

            # 按优先级和预期改进排序
            suggestions.sort(key=lambda s: ({"high": 0, "medium": 1, "low": 2}[s.priority], -s.expected_improvement))

            logger.info(f"生成优化建议: strategy_id={strategy_id}, " f"建议数={len(suggestions)}")

            return suggestions

        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            raise

    def _generate_parameter_suggestions(
        self, strategy_id: str, analysis_results: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """生成参数优化建议"""
        suggestions = []

        # 检查过拟合风险
        overfitting_risk = analysis_results.get("overfitting_risk", {})
        if overfitting_risk.get("risk_level") == "high":
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=f"param_{strategy_id}_001",
                    strategy_id=strategy_id,
                    suggestion_type="parameter",
                    description="降低模型复杂度，减少参数数量以降低过拟合风险",
                    expected_improvement=0.15,
                    priority="high",
                    implementation_difficulty="medium",
                    created_at=datetime.now().isoformat(),
                )
            )

        # 检查参数稳定性
        param_stability = analysis_results.get("parameter_stability", {})
        if param_stability.get("stability_score", 1.0) < 0.7:
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=f"param_{strategy_id}_002",
                    strategy_id=strategy_id,
                    suggestion_type="parameter",
                    description="优化参数稳定性，使用滚动窗口验证参数鲁棒性",
                    expected_improvement=0.10,
                    priority="medium",
                    implementation_difficulty="medium",
                    created_at=datetime.now().isoformat(),
                )
            )

        return suggestions

    def _generate_feature_suggestions(
        self, strategy_id: str, analysis_results: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """生成特征优化建议"""
        suggestions = []

        # 检查特征重要性
        feature_importance = analysis_results.get("feature_importance", {})
        low_importance_features = [f for f, score in feature_importance.items() if score < 0.05]

        if len(low_importance_features) > 3:
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=f"feature_{strategy_id}_001",
                    strategy_id=strategy_id,
                    suggestion_type="feature",
                    description=f"移除{len(low_importance_features)}个低重要性特征，简化模型",
                    expected_improvement=0.08,
                    priority="medium",
                    implementation_difficulty="easy",
                    created_at=datetime.now().isoformat(),
                )
            )

        return suggestions

    def _generate_logic_suggestions(
        self, strategy_id: str, analysis_results: Dict[str, Any]
    ) -> List[OptimizationSuggestion]:
        """生成逻辑优化建议"""
        suggestions = []

        # 检查策略逻辑复杂度
        logic_complexity = analysis_results.get("logic_complexity", {})
        if logic_complexity.get("complexity_score", 0) > 0.8:
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_id=f"logic_{strategy_id}_001",
                    strategy_id=strategy_id,
                    suggestion_type="logic",
                    description="简化策略逻辑，拆分复杂条件为多个简单规则",
                    expected_improvement=0.12,
                    priority="high",
                    implementation_difficulty="hard",
                    created_at=datetime.now().isoformat(),
                )
            )

        return suggestions

    def _generate_risk_suggestions(
        self,
        strategy_id: str,
        analysis_results: Dict[str, Any],  # pylint: disable=unused-argument
        arena_results: Optional[Dict[str, Any]],  # pylint: disable=unused-argument
    ) -> List[OptimizationSuggestion]:
        """生成风险优化建议"""
        suggestions = []

        # 检查最大回撤
        if arena_results:
            max_drawdown = arena_results.get("max_drawdown", 0)
            if max_drawdown > 0.20:  # 超过20%
                suggestions.append(
                    OptimizationSuggestion(
                        suggestion_id=f"risk_{strategy_id}_001",
                        strategy_id=strategy_id,
                        suggestion_type="risk",
                        description="加强风险控制，降低最大回撤至15%以内",
                        expected_improvement=0.20,
                        priority="high",
                        implementation_difficulty="medium",
                        created_at=datetime.now().isoformat(),
                    )
                )

        return suggestions

    # ==================== 进化方向指导 ====================

    def guide_evolution_direction(
        self,
        strategy_id: str,
        analysis_results: Dict[str, Any],
        historical_performance: Optional[List[Dict[str, Any]]] = None,
    ) -> List[EvolutionDirection]:
        """指导进化方向

        白皮书依据: 第五章 5.3.1 进化协同流程

        基于策略分析和历史表现，指导下一步进化方向。

        Args:
            strategy_id: 策略ID
            analysis_results: 分析结果
            historical_performance: 历史表现数据

        Returns:
            进化方向列表

        Raises:
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        directions = []

        try:
            # 1. 因子进化方向
            factor_directions = self._guide_factor_evolution(strategy_id, analysis_results)
            directions.extend(factor_directions)

            # 2. 参数进化方向
            param_directions = self._guide_parameter_evolution(strategy_id, analysis_results)
            directions.extend(param_directions)

            # 3. 逻辑进化方向
            logic_directions = self._guide_logic_evolution(strategy_id, analysis_results)
            directions.extend(logic_directions)

            # 4. 集成进化方向
            ensemble_directions = self._guide_ensemble_evolution(strategy_id, analysis_results, historical_performance)
            directions.extend(ensemble_directions)

            # 按置信度排序
            directions.sort(key=lambda d: d.confidence, reverse=True)

            logger.info(f"指导进化方向: strategy_id={strategy_id}, " f"方向数={len(directions)}")

            return directions

        except Exception as e:
            logger.error(f"指导进化方向失败: {e}")
            raise

    def _guide_factor_evolution(self, strategy_id: str, analysis_results: Dict[str, Any]) -> List[EvolutionDirection]:
        """指导因子进化方向"""
        directions = []

        # 分析因子表现
        factor_performance = analysis_results.get("factor_performance", {})

        if factor_performance.get("ic_mean", 0) < 0.03:
            directions.append(
                EvolutionDirection(
                    direction_id=f"factor_{strategy_id}_001",
                    strategy_id=strategy_id,
                    direction_type="factor",
                    description="探索新的因子组合，提高因子IC值",
                    confidence=0.85,
                    rationale="当前因子IC值偏低，需要引入更有效的因子",
                    created_at=datetime.now().isoformat(),
                )
            )

        return directions

    def _guide_parameter_evolution(
        self, strategy_id: str, analysis_results: Dict[str, Any]
    ) -> List[EvolutionDirection]:
        """指导参数进化方向"""
        directions = []

        # 分析参数敏感性
        param_sensitivity = analysis_results.get("parameter_sensitivity", {})

        if param_sensitivity.get("high_sensitivity_params"):
            directions.append(
                EvolutionDirection(
                    direction_id=f"param_{strategy_id}_001",
                    strategy_id=strategy_id,
                    direction_type="parameter",
                    description="优化高敏感参数，使用自适应参数调整",
                    confidence=0.78,
                    rationale="部分参数对结果影响较大，需要动态调整",
                    created_at=datetime.now().isoformat(),
                )
            )

        return directions

    def _guide_logic_evolution(self, strategy_id: str, analysis_results: Dict[str, Any]) -> List[EvolutionDirection]:
        """指导逻辑进化方向"""
        directions = []

        # 分析市场适配性
        market_adaptation = analysis_results.get("market_adaptation", {})

        if market_adaptation.get("adaptation_score", 1.0) < 0.7:
            directions.append(
                EvolutionDirection(
                    direction_id=f"logic_{strategy_id}_001",
                    strategy_id=strategy_id,
                    direction_type="logic",
                    description="引入市场状态识别，实现自适应策略逻辑",
                    confidence=0.82,
                    rationale="策略在不同市场环境下表现差异较大",
                    created_at=datetime.now().isoformat(),
                )
            )

        return directions

    def _guide_ensemble_evolution(
        self,
        strategy_id: str,
        analysis_results: Dict[str, Any],  # pylint: disable=unused-argument
        historical_performance: Optional[List[Dict[str, Any]]],  # pylint: disable=unused-argument
    ) -> List[EvolutionDirection]:
        """指导集成进化方向"""
        directions = []

        # 分析策略多样性
        if historical_performance and len(historical_performance) > 5:
            directions.append(
                EvolutionDirection(
                    direction_id=f"ensemble_{strategy_id}_001",
                    strategy_id=strategy_id,
                    direction_type="ensemble",
                    description="构建策略集成，提高稳定性和鲁棒性",
                    confidence=0.75,
                    rationale="单一策略风险较高，集成可以降低波动",
                    created_at=datetime.now().isoformat(),
                )
            )

        return directions

    # ==================== 生命周期预测 ====================

    def predict_lifecycle(self, strategy_id: str, performance_history: List[Dict[str, Any]]) -> LifecyclePrediction:
        """预测策略生命周期

        白皮书依据: 第五章 5.3.1 进化协同流程

        基于策略的历史表现数据,预测策略当前所处的生命周期阶段、
        预计剩余有效天数和衰减率。

        Args:
            strategy_id: 策略ID
            performance_history: 历史表现数据列表

        Returns:
            生命周期预测结果

        Raises:
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        if not performance_history or len(performance_history) < 10:
            raise ValueError("历史数据不足,至少需要10个数据点")

        try:
            # 提取性能指标时间序列
            sharpe_series = [p.get("sharpe_ratio", 0) for p in performance_history]
            ic_series = [p.get("ic", 0) for p in performance_history]

            # 计算趋势
            sharpe_trend = self._calculate_trend(sharpe_series)
            ic_trend = self._calculate_trend(ic_series)

            # 计算衰减率
            decay_rate = self._calculate_decay_rate(sharpe_series)

            # 判断生命周期阶段
            current_stage = self._determine_lifecycle_stage(sharpe_trend, ic_trend, decay_rate)

            # 预测剩余天数
            remaining_days = self._predict_remaining_days(current_stage, decay_rate, sharpe_series)

            # 计算预测置信度
            confidence = self._calculate_prediction_confidence(len(performance_history), decay_rate)

            # 识别影响因素
            factors = self._identify_lifecycle_factors(performance_history, current_stage)

            prediction = LifecyclePrediction(
                prediction_id=f"lifecycle_{strategy_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                strategy_id=strategy_id,
                current_stage=current_stage,
                remaining_days=remaining_days,
                decay_rate=decay_rate,
                confidence=confidence,
                factors=factors,
                created_at=datetime.now().isoformat(),
            )

            logger.info(
                f"预测生命周期: strategy_id={strategy_id}, "
                f"stage={current_stage}, remaining_days={remaining_days}, "
                f"decay_rate={decay_rate:.4f}"
            )

            return prediction

        except Exception as e:
            logger.error(f"预测生命周期失败: {e}")
            raise

    def _calculate_trend(self, series: List[float]) -> float:
        """计算时间序列趋势"""
        if len(series) < 2:
            return 0.0

        # 简单线性回归
        n = len(series)
        x = np.arange(n)
        y = np.array(series)

        # 计算斜率
        x_mean = x.mean()
        y_mean = y.mean()

        numerator = ((x - x_mean) * (y - y_mean)).sum()
        denominator = ((x - x_mean) ** 2).sum()

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        return slope

    def _calculate_decay_rate(self, series: List[float]) -> float:
        """计算衰减率"""
        if len(series) < 2:
            return 0.0

        # 计算最近30%数据的平均值 vs 最早30%数据的平均值
        n = len(series)
        window_size = max(3, n // 3)

        early_avg = np.mean(series[:window_size])
        recent_avg = np.mean(series[-window_size:])

        if early_avg == 0:
            return 0.0

        # 衰减率 = (早期 - 近期) / 早期
        decay_rate = (early_avg - recent_avg) / abs(early_avg)

        return max(0.0, decay_rate)  # 只返回正衰减率

    def _determine_lifecycle_stage(self, sharpe_trend: float, ic_trend: float, decay_rate: float) -> str:
        """判断生命周期阶段

        Returns:
            阶段: growth/mature/decline/obsolete
        """
        # 成长期: 趋势向上,衰减率低
        if sharpe_trend > 0.01 and ic_trend > 0.001 and decay_rate < 0.1:
            return "growth"

        # 成熟期: 趋势平稳,衰减率低
        if abs(sharpe_trend) <= 0.01 and abs(ic_trend) <= 0.001 and decay_rate < 0.2:
            return "mature"

        # 衰退期: 趋势向下,衰减率中等
        if sharpe_trend < -0.01 or ic_trend < -0.001 or decay_rate >= 0.2:
            if decay_rate < 0.5:
                return "decline"

        # 淘汰期: 严重衰减
        return "obsolete"

    def _predict_remaining_days(
        self, current_stage: str, decay_rate: float, sharpe_series: List[float]  # pylint: disable=unused-argument
    ) -> int:  # pylint: disable=unused-argument
        """预测剩余有效天数"""
        # 根据阶段和衰减率预测
        if current_stage == "growth":  # pylint: disable=no-else-return
            # 成长期: 预计还有较长时间
            return int(180 * (1 - decay_rate))

        elif current_stage == "mature":
            # 成熟期: 预计还有中等时间
            return int(90 * (1 - decay_rate))

        elif current_stage == "decline":
            # 衰退期: 预计还有较短时间
            if decay_rate < 0.3:  # pylint: disable=no-else-return
                return 60
            elif decay_rate < 0.4:
                return 30
            else:
                return 15

        else:  # obsolete
            # 淘汰期: 建议立即退役
            return 0

    def _calculate_prediction_confidence(self, data_points: int, decay_rate: float) -> float:
        """计算预测置信度"""
        # 数据点越多,置信度越高
        data_confidence = min(1.0, data_points / 100)

        # 衰减率越稳定,置信度越高
        decay_confidence = 1.0 - min(1.0, decay_rate)

        # 综合置信度
        confidence = data_confidence * 0.6 + decay_confidence * 0.4

        return confidence

    def _identify_lifecycle_factors(self, performance_history: List[Dict[str, Any]], current_stage: str) -> List[str]:
        """识别影响生命周期的因素"""
        factors = []

        # 分析最近的表现
        recent_performance = performance_history[-10:]

        # 检查波动性
        sharpe_values = [p.get("sharpe_ratio", 0) for p in recent_performance]
        volatility = np.std(sharpe_values)

        if volatility > 0.5:
            factors.append("高波动性")

        # 检查市场环境变化
        if any(p.get("market_regime") == "bear" for p in recent_performance):
            factors.append("熊市环境")

        # 检查因子失效
        ic_values = [p.get("ic", 0) for p in recent_performance]
        if np.mean(ic_values) < 0.02:
            factors.append("因子失效")

        # 检查过拟合
        if any(p.get("overfitting_risk") == "high" for p in recent_performance):
            factors.append("过拟合风险")

        # 根据阶段添加特定因素
        if current_stage == "decline":
            factors.append("策略衰退")
        elif current_stage == "obsolete":
            factors.append("策略淘汰")

        return factors if factors else ["正常运行"]

    # ==================== 进化报告生成 ====================

    def generate_evolution_report(
        self,
        strategy_id: str,
        analysis_results: Dict[str, Any],
        arena_results: Optional[Dict[str, Any]] = None,
        historical_performance: Optional[List[Dict[str, Any]]] = None,
    ) -> EvolutionReport:
        """生成完整进化报告

        白皮书依据: 第五章 5.3.1 进化协同流程

        整合优化建议、进化方向、生命周期预测等信息,生成完整的
        策略进化报告。

        Args:
            strategy_id: 策略ID
            analysis_results: 29维度分析结果
            arena_results: Arena测试结果
            historical_performance: 历史表现数据

        Returns:
            进化报告

        Raises:
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        if not analysis_results:
            raise ValueError("分析结果不能为空")

        try:
            # 1. 生成优化建议
            optimization_suggestions = self.generate_optimization_suggestions(
                strategy_id, analysis_results, arena_results
            )

            # 2. 指导进化方向
            evolution_directions = self.guide_evolution_direction(strategy_id, analysis_results, historical_performance)

            # 3. 预测生命周期
            if historical_performance and len(historical_performance) >= 10:
                lifecycle_prediction = self.predict_lifecycle(strategy_id, historical_performance)
            else:
                # 数据不足,使用默认预测
                lifecycle_prediction = LifecyclePrediction(
                    prediction_id=f"lifecycle_{strategy_id}_default",
                    strategy_id=strategy_id,
                    current_stage="unknown",
                    remaining_days=-1,
                    decay_rate=0.0,
                    confidence=0.0,
                    factors=["数据不足"],
                    created_at=datetime.now().isoformat(),
                )

            # 4. 获取基因胶囊ID (如果有)
            gene_capsule_id = analysis_results.get("gene_capsule_id")

            # 5. 获取Z2H状态
            z2h_status = analysis_results.get("z2h_status", "not_certified")

            # 6. 构建进化报告
            report = EvolutionReport(
                report_id=f"evolution_{strategy_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                strategy_id=strategy_id,
                optimization_suggestions=optimization_suggestions,
                evolution_directions=evolution_directions,
                lifecycle_prediction=lifecycle_prediction,
                gene_capsule_id=gene_capsule_id,
                z2h_status=z2h_status,
                created_at=datetime.now().isoformat(),
            )

            logger.info(
                f"生成进化报告: strategy_id={strategy_id}, "
                f"建议数={len(optimization_suggestions)}, "
                f"方向数={len(evolution_directions)}, "
                f"生命周期={lifecycle_prediction.current_stage}"
            )

            return report

        except Exception as e:
            logger.error(f"生成进化报告失败: {e}")
            raise
