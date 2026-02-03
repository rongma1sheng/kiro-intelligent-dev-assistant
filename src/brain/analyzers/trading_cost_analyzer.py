"""交易成本分析器

白皮书依据: 第五章 5.2.10 交易成本分析
引擎: Soldier (战术级分析)
"""

from typing import Any, Dict, List

from loguru import logger

from .data_models import TradingCostAnalysis


class TradingCostAnalyzer:
    """交易成本分析器

    白皮书依据: 第五章 5.2.10 交易成本分析

    分析内容:
    - 佣金成本: 交易佣金费用
    - 印花税: 卖出印花税
    - 滑点成本: 实际成交与预期的差异
    - 冲击成本: 大单对市场的影响
    - 成本效率: 成本占收益的比例
    """

    # 默认费率
    DEFAULT_COMMISSION_RATE = 0.0003  # 万三佣金
    DEFAULT_STAMP_DUTY_RATE = 0.001  # 千一印花税（卖出）
    DEFAULT_SLIPPAGE_RATE = 0.001  # 默认滑点

    def __init__(self, commission_rate: float = None, stamp_duty_rate: float = None):
        """初始化交易成本分析器

        Args:
            commission_rate: 佣金费率
            stamp_duty_rate: 印花税费率
        """
        self._commission_rate = commission_rate or self.DEFAULT_COMMISSION_RATE
        self._stamp_duty_rate = stamp_duty_rate or self.DEFAULT_STAMP_DUTY_RATE
        logger.info(
            f"TradingCostAnalyzer初始化完成: " f"佣金={self._commission_rate:.4%}, 印花税={self._stamp_duty_rate:.3%}"
        )

    async def analyze(
        self, strategy_id: str, trades: List[Dict[str, Any]], total_return: float = None
    ) -> TradingCostAnalysis:
        """分析交易成本

        Args:
            strategy_id: 策略ID
            trades: 交易记录列表
            total_return: 总收益（用于计算成本占比）

        Returns:
            TradingCostAnalysis: 交易成本分析报告
        """
        logger.info(f"开始交易成本分析: {strategy_id}")

        try:
            if not trades:
                return self._empty_report(strategy_id)

            total_trades = len(trades)

            # 1. 计算佣金成本
            commission_cost = self._calculate_commission_cost(trades)

            # 2. 计算印花税
            stamp_duty = self._calculate_stamp_duty(trades)

            # 3. 计算滑点成本
            slippage_cost = self._calculate_slippage_cost(trades)

            # 4. 计算冲击成本
            impact_cost = self._calculate_impact_cost(trades)

            # 5. 计算总成本
            total_cost = commission_cost + stamp_duty + slippage_cost + impact_cost

            # 6. 计算成本占收益比
            if total_return and total_return != 0:
                cost_ratio = total_cost / abs(total_return)
            else:
                # 估算收益
                estimated_return = self._estimate_return(trades)
                cost_ratio = total_cost / abs(estimated_return) if estimated_return != 0 else 0

            # 7. 计算成本效率评分
            cost_efficiency = self._calculate_cost_efficiency(cost_ratio, total_trades)

            # 8. 确定成本等级
            cost_level = self._determine_cost_level(cost_ratio)

            # 9. 生成优化建议
            optimization_suggestions = self._generate_optimization_suggestions(
                commission_cost, slippage_cost, impact_cost, total_trades, cost_ratio
            )

            report = TradingCostAnalysis(
                strategy_id=strategy_id,
                total_trades=total_trades,
                commission_cost=round(commission_cost, 2),
                stamp_duty=round(stamp_duty, 2),
                slippage_cost=round(slippage_cost, 2),
                impact_cost=round(impact_cost, 2),
                total_cost=round(total_cost, 2),
                cost_ratio=round(cost_ratio, 4),
                cost_efficiency=round(cost_efficiency, 2),
                cost_level=cost_level,
                optimization_suggestions=optimization_suggestions,
            )

            logger.info(f"交易成本分析完成: {strategy_id}, " f"总成本={total_cost:.2f}, 成本占比={cost_ratio:.2%}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"交易成本分析失败: {strategy_id}, 错误: {e}")
            return self._empty_report(strategy_id)

    def _calculate_commission_cost(self, trades: List[Dict[str, Any]]) -> float:
        """计算佣金成本

        Args:
            trades: 交易记录

        Returns:
            float: 佣金成本
        """
        total_commission = 0.0

        for trade in trades:
            amount = trade.get("amount", 0)
            price = trade.get("price", 0)
            quantity = trade.get("quantity", 0)

            if amount == 0 and price > 0 and quantity > 0:
                amount = price * quantity

            # 买卖双向收取佣金
            commission = amount * self._commission_rate
            # 最低5元
            commission = max(5, commission)
            total_commission += commission

        return total_commission

    def _calculate_stamp_duty(self, trades: List[Dict[str, Any]]) -> float:
        """计算印花税

        Args:
            trades: 交易记录

        Returns:
            float: 印花税
        """
        total_stamp_duty = 0.0

        for trade in trades:
            direction = trade.get("direction", trade.get("side", ""))

            # 只有卖出收取印花税
            if direction.lower() in ["sell", "short", "卖出"]:
                amount = trade.get("amount", 0)
                price = trade.get("price", 0)
                quantity = trade.get("quantity", 0)

                if amount == 0 and price > 0 and quantity > 0:
                    amount = price * quantity

                total_stamp_duty += amount * self._stamp_duty_rate

        return total_stamp_duty

    def _calculate_slippage_cost(self, trades: List[Dict[str, Any]]) -> float:
        """计算滑点成本

        Args:
            trades: 交易记录

        Returns:
            float: 滑点成本
        """
        total_slippage = 0.0

        for trade in trades:
            expected_price = trade.get("expected_price", trade.get("signal_price", 0))
            actual_price = trade.get("price", trade.get("fill_price", 0))
            quantity = trade.get("quantity", 0)
            direction = trade.get("direction", trade.get("side", "buy"))

            if expected_price > 0 and actual_price > 0 and quantity > 0:
                if direction.lower() in ["buy", "long", "买入"]:
                    # 买入时，实际价格高于预期为负滑点
                    slippage = (actual_price - expected_price) * quantity
                else:
                    # 卖出时，实际价格低于预期为负滑点
                    slippage = (expected_price - actual_price) * quantity

                total_slippage += max(0, slippage)  # 只计算负向滑点
            else:
                # 没有预期价格，使用默认滑点率估算
                amount = trade.get("amount", 0)
                if amount == 0 and actual_price > 0 and quantity > 0:
                    amount = actual_price * quantity
                total_slippage += amount * self.DEFAULT_SLIPPAGE_RATE

        return total_slippage

    def _calculate_impact_cost(self, trades: List[Dict[str, Any]]) -> float:
        """计算冲击成本

        Args:
            trades: 交易记录

        Returns:
            float: 冲击成本
        """
        total_impact = 0.0

        for trade in trades:
            amount = trade.get("amount", 0)
            price = trade.get("price", 0)
            quantity = trade.get("quantity", 0)
            avg_volume = trade.get("avg_daily_volume", 0)

            if amount == 0 and price > 0 and quantity > 0:
                amount = price * quantity

            if avg_volume > 0 and quantity > 0:
                # 成交量占日均成交量的比例
                volume_ratio = quantity / avg_volume

                # 冲击成本与成交量比例正相关
                # 简化模型：冲击成本 = 金额 * 成交量比例 * 冲击系数
                impact_coefficient = 0.1  # 冲击系数
                impact = amount * volume_ratio * impact_coefficient
                total_impact += impact
            else:
                # 没有成交量数据，使用固定比例估算
                total_impact += amount * 0.0005  # 0.05%

        return total_impact

    def _estimate_return(self, trades: List[Dict[str, Any]]) -> float:
        """估算收益

        Args:
            trades: 交易记录

        Returns:
            float: 估算收益
        """
        total_pnl = 0.0

        for trade in trades:
            pnl = trade.get("pnl", trade.get("profit", 0))
            total_pnl += pnl

        if total_pnl == 0:
            # 如果没有PnL数据，使用交易金额的1%作为估算
            total_amount = sum(
                trade.get("amount", trade.get("price", 0) * trade.get("quantity", 0)) for trade in trades
            )
            total_pnl = total_amount * 0.01

        return total_pnl

    def _calculate_cost_efficiency(self, cost_ratio: float, total_trades: int) -> float:
        """计算成本效率评分

        Args:
            cost_ratio: 成本占比
            total_trades: 总交易次数

        Returns:
            float: 成本效率评分 0-1
        """
        # 成本占比越低，效率越高
        if cost_ratio <= 0.05:
            ratio_score = 1.0
        elif cost_ratio <= 0.10:
            ratio_score = 0.8
        elif cost_ratio <= 0.20:
            ratio_score = 0.6
        elif cost_ratio <= 0.30:
            ratio_score = 0.4
        else:
            ratio_score = 0.2

        # 交易频率适中为佳
        if 10 <= total_trades <= 100:
            freq_score = 1.0
        elif 5 <= total_trades < 10 or 100 < total_trades <= 200:
            freq_score = 0.8
        elif total_trades < 5 or total_trades > 200:
            freq_score = 0.6
        else:
            freq_score = 0.5

        return ratio_score * 0.7 + freq_score * 0.3

    def _determine_cost_level(self, cost_ratio: float) -> str:
        """确定成本等级

        Args:
            cost_ratio: 成本占比

        Returns:
            str: 成本等级
        """
        if cost_ratio <= 0.05:  # pylint: disable=no-else-return
            return "low"
        elif cost_ratio <= 0.15:
            return "medium"
        elif cost_ratio <= 0.30:
            return "high"
        else:
            return "very_high"

    def _generate_optimization_suggestions(  # pylint: disable=too-many-positional-arguments
        self, commission_cost: float, slippage_cost: float, impact_cost: float, total_trades: int, cost_ratio: float
    ) -> List[str]:
        """生成优化建议

        Args:
            commission_cost: 佣金成本
            slippage_cost: 滑点成本
            impact_cost: 冲击成本
            total_trades: 总交易次数
            cost_ratio: 成本占比

        Returns:
            List[str]: 优化建议列表
        """
        suggestions = []

        # 佣金优化
        if commission_cost > slippage_cost and commission_cost > impact_cost:
            suggestions.append("佣金成本占比较高，建议与券商协商降低佣金费率")
            if total_trades > 100:
                suggestions.append("交易频率较高，考虑减少不必要的交易")

        # 滑点优化
        if slippage_cost > commission_cost:
            suggestions.append("滑点成本较高，建议使用限价单替代市价单")
            suggestions.append("考虑在流动性较好的时段交易")

        # 冲击成本优化
        if impact_cost > commission_cost:
            suggestions.append("冲击成本较高，建议拆分大单分批执行")
            suggestions.append("考虑使用TWAP/VWAP算法降低市场冲击")

        # 整体优化
        if cost_ratio > 0.20:
            suggestions.append("总成本占比过高，严重侵蚀收益，需要全面优化")
        elif cost_ratio > 0.10:
            suggestions.append("成本控制有改善空间，建议关注主要成本来源")

        if total_trades > 200:
            suggestions.append("交易过于频繁，建议提高交易信号质量，减少无效交易")

        if not suggestions:
            suggestions.append("成本控制良好，继续保持")

        return suggestions

    def _empty_report(self, strategy_id: str) -> TradingCostAnalysis:
        """生成空报告

        Args:
            strategy_id: 策略ID

        Returns:
            TradingCostAnalysis: 空报告
        """
        return TradingCostAnalysis(
            strategy_id=strategy_id,
            total_trades=0,
            commission_cost=0.0,
            stamp_duty=0.0,
            slippage_cost=0.0,
            impact_cost=0.0,
            total_cost=0.0,
            cost_ratio=0.0,
            cost_efficiency=0.0,
            cost_level="low",
            optimization_suggestions=["无交易记录"],
        )
