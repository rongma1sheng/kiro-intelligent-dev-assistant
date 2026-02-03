"""资金容量评估分析器

白皮书依据: 第五章 5.2.16 资金容量评估
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import CapacityAnalysis


class CapacityAnalyzer:
    """资金容量评估分析器

    白皮书依据: 第五章 5.2.16 资金容量评估

    分析内容:
    - 最大容量: 策略能承载的最大资金
    - 容量利用率: 当前资金占最大容量的比例
    - 衰减曲线: 资金增加对收益的影响
    - 瓶颈识别: 限制容量的主要因素
    - 扩容建议: 如何提高资金容量
    """

    def __init__(self):
        """初始化容量分析器"""
        self._decay_model = "sqrt"  # 衰减模型：sqrt, linear, exponential
        logger.info("CapacityAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> CapacityAnalysis:
        """分析资金容量

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            CapacityAnalysis: 容量分析报告
        """
        logger.info(f"开始资金容量分析: {strategy_id}")

        try:
            trades = strategy_data.get("trades", [])
            current_capital = strategy_data.get("current_capital", 0)
            avg_daily_volume = strategy_data.get("avg_daily_volume", 0)
            avg_trade_size = strategy_data.get("avg_trade_size", 0)
            returns = strategy_data.get("returns", [])

            # 1. 估算最大容量
            max_capacity = self._estimate_max_capacity(trades, avg_daily_volume, avg_trade_size)

            # 2. 计算容量置信度
            capacity_confidence = self._calculate_capacity_confidence(trades, avg_daily_volume)

            # 3. 计算容量利用率
            capacity_utilization = self._calculate_utilization(current_capital, max_capacity)

            # 4. 生成衰减曲线
            decay_curve = self._generate_decay_curve(max_capacity, returns)

            # 5. 计算衰减率
            decay_rate = self._calculate_decay_rate(decay_curve)

            # 6. 计算最优容量
            optimal_capacity = self._calculate_optimal_capacity(max_capacity, decay_curve)

            # 7. 计算可扩展性评分
            scalability_score = self._calculate_scalability_score(max_capacity, decay_rate, avg_daily_volume)

            # 8. 识别瓶颈
            primary_bottleneck, bottlenecks = self._identify_bottlenecks(trades, avg_daily_volume, max_capacity)

            # 9. 生成扩容建议
            expansion_recommendations = self._generate_expansion_recommendations(
                bottlenecks, scalability_score, capacity_utilization
            )

            # 10. 估算扩容潜力
            expansion_potential = self._estimate_expansion_potential(max_capacity, optimal_capacity, bottlenecks)

            report = CapacityAnalysis(
                strategy_id=strategy_id,
                max_capacity=round(max_capacity, 2),
                capacity_confidence=round(capacity_confidence, 2),
                current_capital=current_capital,
                capacity_utilization=round(capacity_utilization, 2),
                decay_curve=decay_curve,
                decay_rate=round(decay_rate, 4),
                optimal_capacity=round(optimal_capacity, 2),
                scalability_score=round(scalability_score, 2),
                primary_bottleneck=primary_bottleneck,
                bottlenecks=bottlenecks,
                expansion_recommendations=expansion_recommendations,
                expansion_potential=round(expansion_potential, 2),
            )

            logger.info(
                f"容量分析完成: {strategy_id}, " f"最大容量={max_capacity/1e8:.2f}亿, 利用率={capacity_utilization:.1%}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"容量分析失败: {strategy_id}, 错误: {e}")
            return CapacityAnalysis(
                strategy_id=strategy_id,
                max_capacity=0.0,
                capacity_confidence=0.0,
                current_capital=0.0,
                capacity_utilization=0.0,
                decay_curve=[],
                decay_rate=0.0,
                optimal_capacity=0.0,
                scalability_score=0.0,
                primary_bottleneck="分析失败",
                bottlenecks=["分析失败"],
                expansion_recommendations=["建议人工审核"],
                expansion_potential=0.0,
            )

    def _estimate_max_capacity(
        self, trades: List[Dict[str, Any]], avg_daily_volume: float, avg_trade_size: float
    ) -> float:
        """估算最大容量

        Args:
            trades: 交易记录
            avg_daily_volume: 日均成交量
            avg_trade_size: 平均交易规模

        Returns:
            float: 最大容量
        """
        # 方法1：基于日均成交量
        # 假设策略最多占用日均成交量的5%
        volume_based_capacity = avg_daily_volume * 0.05 if avg_daily_volume > 0 else 0

        # 方法2：基于交易规模
        # 假设可以放大10倍
        trade_based_capacity = avg_trade_size * 10 if avg_trade_size > 0 else 0

        # 方法3：基于历史交易
        if trades:
            max_trade = max(t.get("amount", t.get("price", 0) * t.get("quantity", 0)) for t in trades)
            historical_capacity = max_trade * 20
        else:
            historical_capacity = 0

        # 取最小值作为保守估计
        capacities = [c for c in [volume_based_capacity, trade_based_capacity, historical_capacity] if c > 0]

        if capacities:
            max_capacity = min(capacities)
        else:
            max_capacity = 1e8  # 默认1亿

        return max_capacity

    def _calculate_capacity_confidence(self, trades: List[Dict[str, Any]], avg_daily_volume: float) -> float:
        """计算容量置信度

        Args:
            trades: 交易记录
            avg_daily_volume: 日均成交量

        Returns:
            float: 置信度 0-1
        """
        confidence = 0.5  # 基础置信度

        # 交易数据量
        if trades:
            if len(trades) >= 100:
                confidence += 0.2
            elif len(trades) >= 50:
                confidence += 0.1

        # 成交量数据
        if avg_daily_volume > 0:
            confidence += 0.2

        # 交易规模多样性
        if trades and len(trades) >= 10:
            sizes = [t.get("amount", t.get("price", 0) * t.get("quantity", 0)) for t in trades]
            if np.std(sizes) / (np.mean(sizes) + 1e-10) > 0.5:
                confidence += 0.1

        return min(1.0, confidence)

    def _calculate_utilization(self, current_capital: float, max_capacity: float) -> float:
        """计算容量利用率

        Args:
            current_capital: 当前资金
            max_capacity: 最大容量

        Returns:
            float: 利用率 0-1
        """
        if max_capacity <= 0:
            return 0.0

        return min(1.0, current_capital / max_capacity)

    def _generate_decay_curve(self, max_capacity: float, returns: List[float]) -> List[Dict[str, float]]:
        """生成衰减曲线

        Args:
            max_capacity: 最大容量
            returns: 收益率序列

        Returns:
            List[Dict[str, float]]: 衰减曲线数据点
        """
        if max_capacity <= 0:
            return []

        # 计算基准收益率
        if returns:
            base_return = np.mean(returns) * 252  # 年化
        else:
            base_return = 0.15  # 默认15%

        # 生成不同资金规模下的预期收益
        curve = []
        capital_levels = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]

        for level in capital_levels:
            capital = max_capacity * level

            # 衰减模型
            if self._decay_model == "sqrt":
                decay_factor = 1 / np.sqrt(max(1, level))
            elif self._decay_model == "linear":
                decay_factor = max(0, 1 - 0.3 * (level - 1))
            else:  # exponential
                decay_factor = np.exp(-0.5 * max(0, level - 1))

            expected_return = base_return * decay_factor

            curve.append(
                {
                    "capital": round(capital, 2),
                    "capital_ratio": level,
                    "expected_return": round(expected_return, 4),
                    "decay_factor": round(decay_factor, 4),
                }
            )

        return curve

    def _calculate_decay_rate(self, decay_curve: List[Dict[str, float]]) -> float:
        """计算衰减率

        Args:
            decay_curve: 衰减曲线

        Returns:
            float: 衰减率
        """
        if not decay_curve or len(decay_curve) < 2:
            return 0.0

        # 计算从100%容量到200%容量的收益衰减
        returns_at_100 = None
        returns_at_200 = None

        for point in decay_curve:
            if point["capital_ratio"] == 1.0:
                returns_at_100 = point["expected_return"]
            elif point["capital_ratio"] == 2.0:
                returns_at_200 = point["expected_return"]

        if returns_at_100 and returns_at_200 and returns_at_100 > 0:
            decay_rate = (returns_at_100 - returns_at_200) / returns_at_100
            return max(0, decay_rate)

        return 0.3  # 默认30%衰减

    def _calculate_optimal_capacity(self, max_capacity: float, decay_curve: List[Dict[str, float]]) -> float:
        """计算最优容量

        Args:
            max_capacity: 最大容量
            decay_curve: 衰减曲线

        Returns:
            float: 最优容量
        """
        if not decay_curve:
            return max_capacity * 0.7

        # 找到收益/资金比最优的点
        best_ratio = 0
        optimal_capital = max_capacity * 0.7

        for point in decay_curve:
            if point["capital"] > 0:
                ratio = point["expected_return"] / point["capital_ratio"]
                if ratio > best_ratio:
                    best_ratio = ratio
                    optimal_capital = point["capital"]

        return optimal_capital

    def _calculate_scalability_score(self, max_capacity: float, decay_rate: float, avg_daily_volume: float) -> float:
        """计算可扩展性评分

        Args:
            max_capacity: 最大容量
            decay_rate: 衰减率
            avg_daily_volume: 日均成交量

        Returns:
            float: 可扩展性评分 0-1
        """
        score = 0.5  # 基础分

        # 容量大小
        if max_capacity >= 10e8:  # 10亿以上
            score += 0.2
        elif max_capacity >= 1e8:  # 1亿以上
            score += 0.1

        # 衰减率
        if decay_rate < 0.2:
            score += 0.2
        elif decay_rate < 0.4:
            score += 0.1
        elif decay_rate > 0.6:
            score -= 0.1

        # 流动性
        if avg_daily_volume > 0 and max_capacity > 0:
            liquidity_ratio = avg_daily_volume / max_capacity
            if liquidity_ratio > 20:
                score += 0.1

        return max(0, min(1, score))

    def _identify_bottlenecks(
        self, trades: List[Dict[str, Any]], avg_daily_volume: float, max_capacity: float
    ) -> tuple:
        """识别瓶颈

        Args:
            trades: 交易记录
            avg_daily_volume: 日均成交量
            max_capacity: 最大容量

        Returns:
            tuple: (主要瓶颈, 瓶颈列表)
        """
        bottlenecks = []

        # 流动性瓶颈
        if avg_daily_volume > 0 and max_capacity > 0:
            if max_capacity / avg_daily_volume > 0.1:
                bottlenecks.append("市场流动性不足")

        # 交易频率瓶颈
        if trades:
            avg_holding_period = np.mean([t.get("holding_period", 1) for t in trades])
            if avg_holding_period < 1:
                bottlenecks.append("交易频率过高")

        # 集中度瓶颈
        if trades:
            symbols = [t.get("symbol", "") for t in trades]
            unique_symbols = len(set(symbols))
            if unique_symbols < 10:
                bottlenecks.append("标的集中度过高")

        # 滑点瓶颈
        if trades:
            slippages = [t.get("slippage", 0) for t in trades if "slippage" in t]
            if slippages and np.mean(slippages) > 0.002:
                bottlenecks.append("滑点成本过高")

        if not bottlenecks:
            bottlenecks.append("暂无明显瓶颈")

        primary_bottleneck = bottlenecks[0]

        return primary_bottleneck, bottlenecks

    def _generate_expansion_recommendations(
        self, bottlenecks: List[str], scalability_score: float, capacity_utilization: float
    ) -> List[str]:
        """生成扩容建议

        Args:
            bottlenecks: 瓶颈列表
            scalability_score: 可扩展性评分
            capacity_utilization: 容量利用率

        Returns:
            List[str]: 扩容建议
        """
        recommendations = []

        # 针对瓶颈的建议
        if "市场流动性不足" in bottlenecks:
            recommendations.append("增加交易标的数量，分散流动性需求")
            recommendations.append("选择流动性更好的标的")

        if "交易频率过高" in bottlenecks:
            recommendations.append("降低交易频率，减少市场冲击")
            recommendations.append("使用TWAP/VWAP算法执行")

        if "标的集中度过高" in bottlenecks:
            recommendations.append("增加策略覆盖的标的范围")
            recommendations.append("考虑多市场/多品种扩展")

        if "滑点成本过高" in bottlenecks:
            recommendations.append("优化执行算法，降低滑点")
            recommendations.append("在流动性好的时段交易")

        # 基于利用率的建议
        if capacity_utilization > 0.8:
            recommendations.append("当前容量利用率较高，建议控制资金增长")
        elif capacity_utilization < 0.3:
            recommendations.append("当前容量利用率较低，有较大扩容空间")

        # 基于可扩展性的建议
        if scalability_score < 0.4:
            recommendations.append("策略可扩展性较差，建议优化策略逻辑")

        return recommendations

    def _estimate_expansion_potential(
        self, max_capacity: float, optimal_capacity: float, bottlenecks: List[str]
    ) -> float:
        """估算扩容潜力

        Args:
            max_capacity: 最大容量
            optimal_capacity: 最优容量
            bottlenecks: 瓶颈列表

        Returns:
            float: 扩容潜力（倍数）
        """
        if max_capacity <= 0:
            return 1.0

        # 基础扩容潜力
        base_potential = max_capacity / optimal_capacity if optimal_capacity > 0 else 1.0

        # 根据瓶颈调整
        addressable_bottlenecks = ["标的集中度过高", "交易频率过高", "滑点成本过高"]

        addressable_count = sum(1 for b in bottlenecks if b in addressable_bottlenecks)

        # 可解决的瓶颈越多，扩容潜力越大
        potential_multiplier = 1 + 0.2 * addressable_count

        return min(5.0, base_potential * potential_multiplier)
