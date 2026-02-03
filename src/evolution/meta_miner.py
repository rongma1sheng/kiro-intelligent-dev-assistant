"""元挖掘器 - 挖掘器的挖掘器

白皮书依据: 第四章 4.1.16 元挖掘与自适应优化
需求: 15.1, 15.2（扩展）
设计文档: design.md - Meta Mining and Adaptive Optimization

元挖掘器分析和优化现有挖掘器的组合使用，实现自适应因子发现。
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from .unified_factor_mining_system import BaseMiner, FactorMetadata, MinerStatus, MinerType, MiningResult


@dataclass
class MinerPerformance:
    """挖掘器性能指标

    Attributes:
        miner_type: 挖掘器类型
        success_rate: 成功率
        avg_fitness: 平均适应度
        avg_ic: 平均IC
        avg_ir: 平均IR
        execution_time: 平均执行时间
        factor_count: 发现因子数
        last_update: 最后更新时间
    """

    miner_type: MinerType
    success_rate: float
    avg_fitness: float
    avg_ic: float
    avg_ir: float
    execution_time: float
    factor_count: int
    last_update: datetime


@dataclass
class MinerRecommendation:
    """挖掘器推荐

    Attributes:
        recommended_miners: 推荐的挖掘器列表
        priority_scores: 优先级得分
        reasoning: 推荐理由
        market_regime: 当前市场状态
        confidence: 推荐置信度
    """

    recommended_miners: List[MinerType]
    priority_scores: Dict[MinerType, float]
    reasoning: str
    market_regime: str
    confidence: float


class MetaMiner(BaseMiner):
    """元挖掘器 - 挖掘器的挖掘器

    白皮书依据: 第四章 4.1.16 元挖掘与自适应优化
    需求: 15.1, 15.2（扩展）

    功能：
    1. 分析各挖掘器的历史表现
    2. 识别最佳挖掘器组合
    3. 根据市场状态推荐挖掘器
    4. 优化挖掘器参数
    5. 自适应调整挖掘策略

    Attributes:
        performance_history: 挖掘器性能历史
        market_regime_detector: 市场状态检测器
        optimization_window: 优化窗口期（默认30天）
        min_samples: 最小样本数（默认10）
    """

    def __init__(self, optimization_window: int = 30, min_samples: int = 10):
        """初始化元挖掘器

        白皮书依据: 第四章 4.1.16

        Args:
            optimization_window: 优化窗口期，默认30天
            min_samples: 最小样本数，默认10

        Raises:
            ValueError: 当参数不在有效范围时
        """
        super().__init__(MinerType.UNIFIED, "MetaMiner")

        if optimization_window <= 0:
            raise ValueError(f"optimization_window必须 > 0，当前: {optimization_window}")

        if min_samples <= 0:
            raise ValueError(f"min_samples必须 > 0，当前: {min_samples}")

        self.optimization_window = optimization_window
        self.min_samples = min_samples

        # 性能历史记录
        self.performance_history: Dict[MinerType, List[MinerPerformance]] = defaultdict(list)

        # 市场状态历史
        self.market_regime_history: List[Tuple[datetime, str]] = []

        logger.info(f"初始化元挖掘器 - " f"optimization_window={optimization_window}, " f"min_samples={min_samples}")

    def record_mining_result(self, result: MiningResult, execution_time: float) -> None:
        """记录挖掘结果

        白皮书依据: 第四章 4.1.16 性能追踪

        Args:
            result: 挖掘结果
            execution_time: 执行时间
        """
        try:
            if not result.success:
                logger.debug(f"跳过失败的挖掘结果: {result.miner_type.value}")
                return

            # 计算性能指标
            if result.factors:
                avg_fitness = sum(f.fitness for f in result.factors) / len(result.factors)
                avg_ic = sum(f.ic for f in result.factors) / len(result.factors)
                avg_ir = sum(f.ir for f in result.factors) / len(result.factors)
            else:
                avg_fitness = 0.0
                avg_ic = 0.0
                avg_ir = 0.0

            # 创建性能记录
            performance = MinerPerformance(
                miner_type=result.miner_type,
                success_rate=1.0 if result.success else 0.0,
                avg_fitness=avg_fitness,
                avg_ic=avg_ic,
                avg_ir=avg_ir,
                execution_time=execution_time,
                factor_count=len(result.factors),
                last_update=datetime.now(),
            )

            # 添加到历史记录
            self.performance_history[result.miner_type].append(performance)

            # 保持窗口大小
            cutoff_date = datetime.now() - timedelta(days=self.optimization_window)
            self.performance_history[result.miner_type] = [
                p for p in self.performance_history[result.miner_type] if p.last_update >= cutoff_date
            ]

            logger.debug(
                f"记录挖掘结果: {result.miner_type.value}, "
                f"因子数={len(result.factors)}, "
                f"平均适应度={avg_fitness:.4f}"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"记录挖掘结果失败: {e}")

    def detect_market_regime(self, data: pd.DataFrame) -> str:
        """检测市场状态

        白皮书依据: 第四章 4.1.16 市场状态识别

        市场状态分类：
        - bull: 牛市（上涨趋势）
        - bear: 熊市（下跌趋势）
        - volatile: 高波动市场
        - stable: 稳定市场
        - crisis: 危机市场

        Args:
            data: 市场数据，包含returns列

        Returns:
            市场状态字符串
        """
        try:
            if "returns" not in data.columns:
                logger.warning("缺少returns列，无法检测市场状态")
                return "unknown"

            # 计算市场指标
            returns = data["returns"]

            # 1. 趋势：使用移动平均
            ma_short = returns.rolling(window=20).mean()
            ma_long = returns.rolling(window=60).mean()
            trend = ma_short.iloc[-1] - ma_long.iloc[-1]

            # 2. 波动率
            volatility = returns.rolling(window=20).std().iloc[-1]
            volatility_ma = returns.rolling(window=60).std().mean()

            # 3. 极端收益
            recent_returns = returns.tail(20)
            max_drawdown = (recent_returns.cumsum() - recent_returns.cumsum().cummax()).min()

            # 状态判断
            if max_drawdown < -0.15:  # 最大回撤 > 15%
                regime = "crisis"
            elif volatility > 2 * volatility_ma:  # 波动率 > 2倍均值
                regime = "volatile"
            elif trend > 0.01:  # 正趋势
                regime = "bull"
            elif trend < -0.01:  # 负趋势
                regime = "bear"
            else:
                regime = "stable"

            # 记录市场状态
            self.market_regime_history.append((datetime.now(), regime))

            # 保持历史记录窗口
            cutoff_date = datetime.now() - timedelta(days=self.optimization_window)
            self.market_regime_history = [
                (date, state) for date, state in self.market_regime_history if date >= cutoff_date
            ]

            logger.info(
                f"市场状态检测: {regime}, "
                f"趋势={trend:.4f}, "
                f"波动率={volatility:.4f}, "
                f"最大回撤={max_drawdown:.4f}"
            )

            return regime

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"市场状态检测失败: {e}")
            return "unknown"

    def analyze_miner_performance(self, miner_type: MinerType) -> Optional[Dict[str, float]]:
        """分析挖掘器性能

        白皮书依据: 第四章 4.1.16 性能分析

        Args:
            miner_type: 挖掘器类型

        Returns:
            性能指标字典，如果样本不足则返回None
        """
        try:
            history = self.performance_history.get(miner_type, [])

            if len(history) < self.min_samples:
                logger.debug(f"挖掘器 {miner_type.value} 样本不足: " f"{len(history)} < {self.min_samples}")
                return None

            # 计算聚合指标
            success_rate = sum(p.success_rate for p in history) / len(history)
            avg_fitness = sum(p.avg_fitness for p in history) / len(history)
            avg_ic = sum(p.avg_ic for p in history) / len(history)
            avg_ir = sum(p.avg_ir for p in history) / len(history)
            avg_execution_time = sum(p.execution_time for p in history) / len(history)
            total_factors = sum(p.factor_count for p in history)

            # 计算趋势（最近vs历史）
            recent_history = history[-5:] if len(history) >= 5 else history
            recent_fitness = sum(p.avg_fitness for p in recent_history) / len(recent_history)
            fitness_trend = recent_fitness - avg_fitness

            return {
                "success_rate": success_rate,
                "avg_fitness": avg_fitness,
                "avg_ic": avg_ic,
                "avg_ir": avg_ir,
                "avg_execution_time": avg_execution_time,
                "total_factors": total_factors,
                "fitness_trend": fitness_trend,
                "sample_count": len(history),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"性能分析失败: {e}")
            return None

    def recommend_miners(self, market_regime: str, top_k: int = 5) -> MinerRecommendation:
        """推荐最佳挖掘器组合

        白皮书依据: 第四章 4.1.16 自适应推荐

        根据市场状态和历史表现推荐挖掘器

        Args:
            market_regime: 当前市场状态
            top_k: 推荐挖掘器数量，默认5

        Returns:
            挖掘器推荐
        """
        try:
            # 分析所有挖掘器性能
            miner_scores: Dict[MinerType, float] = {}

            for miner_type in MinerType:
                if miner_type == MinerType.UNIFIED:
                    continue  # 跳过自己

                performance = self.analyze_miner_performance(miner_type)

                if performance is None:
                    continue

                # 计算综合得分
                # 基础得分：适应度 * 成功率
                base_score = (
                    performance["avg_fitness"] * 0.4
                    + abs(performance["avg_ic"]) * 0.3
                    + abs(performance["avg_ir"]) * 0.3
                ) * performance["success_rate"]

                # 趋势加成
                trend_bonus = max(0, performance["fitness_trend"]) * 0.2

                # 效率加成（快速挖掘器）
                efficiency_bonus = 0.1 if performance["avg_execution_time"] < 10.0 else 0.0

                # 市场状态适配加成
                regime_bonus = self._get_regime_bonus(miner_type, market_regime)

                # 综合得分
                total_score = base_score + trend_bonus + efficiency_bonus + regime_bonus

                miner_scores[miner_type] = total_score

            # 排序并选择top_k
            sorted_miners = sorted(miner_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

            recommended_miners = [miner for miner, _ in sorted_miners]
            priority_scores = dict(sorted_miners)

            # 生成推荐理由
            reasoning = self._generate_reasoning(recommended_miners, priority_scores, market_regime)

            # 计算置信度
            confidence = self._calculate_confidence(miner_scores)

            recommendation = MinerRecommendation(
                recommended_miners=recommended_miners,
                priority_scores=priority_scores,
                reasoning=reasoning,
                market_regime=market_regime,
                confidence=confidence,
            )

            logger.info(
                f"挖掘器推荐完成 - "
                f"市场状态={market_regime}, "
                f"推荐数量={len(recommended_miners)}, "
                f"置信度={confidence:.2%}"
            )

            return recommendation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"挖掘器推荐失败: {e}")
            # 返回默认推荐
            return MinerRecommendation(
                recommended_miners=[MinerType.GENETIC],
                priority_scores={MinerType.GENETIC: 1.0},
                reasoning="默认推荐（推荐系统异常）",
                market_regime=market_regime,
                confidence=0.0,
            )

    def _get_regime_bonus(self, miner_type: MinerType, market_regime: str) -> float:
        """获取市场状态适配加成

        不同挖掘器在不同市场状态下表现不同

        Args:
            miner_type: 挖掘器类型
            market_regime: 市场状态

        Returns:
            加成得分
        """
        # 市场状态-挖掘器适配矩阵
        regime_affinity = {
            "bull": {
                MinerType.SENTIMENT: 0.3,
                MinerType.PRICE_VOLUME: 0.3,  # 替换MOMENTUM
                MinerType.AI_ENHANCED: 0.2,
                MinerType.HIGH_FREQUENCY: 0.2,
            },
            "bear": {
                MinerType.PRICE_VOLUME: 0.3,
                MinerType.ALTERNATIVE_DATA: 0.2,
                MinerType.ESG: 0.2,
                MinerType.NETWORK: 0.2,
            },
            "volatile": {
                MinerType.HIGH_FREQUENCY: 0.3,
                MinerType.EVENT_DRIVEN: 0.3,
                MinerType.NETWORK: 0.2,
                MinerType.STYLE_ROTATION: 0.2,
            },
            "stable": {
                MinerType.ML_FEATURE: 0.3,
                MinerType.TIME_SERIES_DL: 0.3,
                MinerType.FACTOR_COMBINATION: 0.2,
                MinerType.MACRO: 0.2,
            },
            "crisis": {
                MinerType.NETWORK: 0.4,
                MinerType.EVENT_DRIVEN: 0.3,
                MinerType.ALTERNATIVE_DATA: 0.2,
                MinerType.ESG: 0.1,
            },
        }

        affinity_map = regime_affinity.get(market_regime, {})
        return affinity_map.get(miner_type, 0.0)

    def _generate_reasoning(
        self, recommended_miners: List[MinerType], priority_scores: Dict[MinerType, float], market_regime: str
    ) -> str:
        """生成推荐理由

        Args:
            recommended_miners: 推荐的挖掘器列表
            priority_scores: 优先级得分
            market_regime: 市场状态

        Returns:
            推荐理由字符串
        """
        if not recommended_miners:
            return "无可用推荐"

        top_miner = recommended_miners[0]
        top_score = priority_scores[top_miner]

        reasoning = (
            f"基于当前市场状态（{market_regime}）和历史表现分析，"
            f"推荐使用 {top_miner.value} 挖掘器（得分: {top_score:.4f}）"
        )

        if len(recommended_miners) > 1:
            other_miners = ", ".join([m.value for m in recommended_miners[1:3]])
            reasoning += f"。其他推荐: {other_miners}"

        return reasoning

    def _calculate_confidence(self, miner_scores: Dict[MinerType, float]) -> float:
        """计算推荐置信度

        基于得分分布和样本数量

        Args:
            miner_scores: 挖掘器得分字典

        Returns:
            置信度（0-1）
        """
        if not miner_scores:
            return 0.0

        scores = list(miner_scores.values())

        # 得分差异度（top1 vs others）
        if len(scores) > 1:
            sorted_scores = sorted(scores, reverse=True)
            score_gap = sorted_scores[0] - sorted_scores[1]
            gap_confidence = min(1.0, score_gap / 0.5)
        else:
            gap_confidence = 0.5

        # 样本充足度
        total_samples = sum(len(self.performance_history.get(mt, [])) for mt in miner_scores.keys())
        sample_confidence = min(1.0, total_samples / (len(miner_scores) * self.min_samples))

        # 综合置信度
        confidence = 0.6 * gap_confidence + 0.4 * sample_confidence

        return confidence

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, **kwargs) -> List[FactorMetadata]:
        """元挖掘：分析和推荐最佳挖掘器组合

        白皮书依据: 第四章 4.1.16

        Args:
            data: 市场数据DataFrame
            returns: 收益率序列
            **kwargs: 额外参数

        Returns:
            元因子列表（推荐信息）
        """
        if data.empty:
            raise ValueError("输入数据不能为空")

        if len(returns) == 0:
            raise ValueError("收益率数据不能为空")

        try:
            self.metadata.status = MinerStatus.RUNNING
            logger.info("开始元挖掘分析...")

            # 确保数据包含returns列
            if "returns" not in data.columns:
                data = data.copy()
                data["returns"] = returns

            # 1. 检测市场状态
            market_regime = self.detect_market_regime(data)

            # 2. 推荐挖掘器
            recommendation = self.recommend_miners(market_regime, top_k=5)

            # 3. 生成元因子（包含推荐信息）
            factors = []

            # 创建推荐因子
            for i, miner_type in enumerate(recommendation.recommended_miners):  # pylint: disable=unused-variable
                score = recommendation.priority_scores[miner_type]

                factor = FactorMetadata(
                    factor_id=f"meta_recommendation_{miner_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    factor_name=f"MetaRecommendation_{miner_type.value}",
                    factor_type=MinerType.UNIFIED,
                    data_source="meta_analysis",
                    discovery_date=datetime.now(),
                    discoverer=self.miner_name,
                    expression=f"recommend_{miner_type.value}",
                    fitness=score,
                    ic=score * 0.8,  # 估算
                    ir=score * 0.7,  # 估算
                    sharpe=score * 0.6,  # 估算
                )

                factors.append(factor)

            # 更新元数据
            self.metadata.status = MinerStatus.COMPLETED
            self.metadata.total_factors_discovered += len(factors)
            self.metadata.last_run_time = datetime.now()

            if factors:
                avg_fitness = sum(f.fitness for f in factors) / len(factors)
                self.metadata.average_fitness = (
                    self.metadata.average_fitness * (self.metadata.total_factors_discovered - len(factors))
                    + avg_fitness * len(factors)
                ) / self.metadata.total_factors_discovered

            logger.info(
                f"元挖掘完成 - "
                f"市场状态={market_regime}, "
                f"推荐挖掘器数={len(factors)}, "
                f"置信度={recommendation.confidence:.2%}, "
                f"理由={recommendation.reasoning}"
            )

            return factors

        except Exception as e:
            self.metadata.status = MinerStatus.FAILED
            self.metadata.error_count += 1
            self.metadata.last_error = str(e)
            self.metadata.is_healthy = self.metadata.error_count < 5
            logger.error(f"元挖掘失败: {e}")
            raise

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要

        Returns:
            性能摘要字典
        """
        summary = {
            "total_miners_tracked": len(self.performance_history),
            "total_records": sum(len(history) for history in self.performance_history.values()),
            "market_regime_history_length": len(self.market_regime_history),
            "current_market_regime": (self.market_regime_history[-1][1] if self.market_regime_history else "unknown"),
            "top_performers": [],
        }

        # 找出表现最好的挖掘器
        for miner_type in MinerType:
            if miner_type == MinerType.UNIFIED:
                continue

            performance = self.analyze_miner_performance(miner_type)
            if performance:
                summary["top_performers"].append(
                    {
                        "miner_type": miner_type.value,
                        "avg_fitness": performance["avg_fitness"],
                        "success_rate": performance["success_rate"],
                        "total_factors": performance["total_factors"],
                    }
                )

        # 按平均适应度排序
        summary["top_performers"].sort(key=lambda x: x["avg_fitness"], reverse=True)
        summary["top_performers"] = summary["top_performers"][:5]

        return summary
