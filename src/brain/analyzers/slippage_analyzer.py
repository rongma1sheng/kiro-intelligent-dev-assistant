"""滑点分析器

白皮书依据: 第五章 5.2.13 滑点分析
引擎: Soldier (战术级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import SlippageAnalysis


class SlippageAnalyzer:
    """滑点分析器

    白皮书依据: 第五章 5.2.13 滑点分析

    分析内容:
    - 滑点统计: 平均/中位数/最大滑点
    - 滑点分布: 滑点的分布情况
    - 时段分析: 不同时段的滑点差异
    - 市值影响: 不同市值股票的滑点
    - 优化建议: 降低滑点的方法
    """

    def __init__(self):
        """初始化滑点分析器"""
        self._time_slots = [
            "09:30-10:00",
            "10:00-10:30",
            "10:30-11:00",
            "11:00-11:30",
            "13:00-13:30",
            "13:30-14:00",
            "14:00-14:30",
            "14:30-15:00",
        ]
        logger.info("SlippageAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, trades: List[Dict[str, Any]]) -> SlippageAnalysis:
        """分析滑点

        Args:
            strategy_id: 策略ID
            trades: 交易记录

        Returns:
            SlippageAnalysis: 滑点分析报告
        """
        logger.info(f"开始滑点分析: {strategy_id}")

        try:
            if not trades:
                return self._empty_report(strategy_id)

            # 1. 计算滑点数据
            slippages = self._calculate_slippages(trades)

            if not slippages:
                return self._empty_report(strategy_id)

            slippage_array = np.array(slippages)

            # 2. 基本统计
            avg_slippage = np.mean(slippage_array)
            median_slippage = np.median(slippage_array)
            max_slippage = np.max(slippage_array)

            # 3. 滑点分布
            slippage_distribution = self._calculate_distribution(slippage_array)

            # 4. 百分位数
            percentiles = self._calculate_percentiles(slippage_array)

            # 5. 总滑点成本
            total_slippage_cost = self._calculate_total_cost(trades, slippages)

            # 6. 滑点成本占比
            total_amount = sum(t.get("amount", t.get("price", 0) * t.get("quantity", 0)) for t in trades)
            slippage_cost_ratio = total_slippage_cost / total_amount if total_amount > 0 else 0

            # 7. 时段分析
            time_of_day_analysis = self._analyze_by_time(trades, slippages)

            # 8. 最差/最佳时段
            worst_time_slots, best_time_slots = self._identify_best_worst_times(time_of_day_analysis)

            # 9. 市值影响分析
            market_cap_impact = self._analyze_by_market_cap(trades, slippages)

            # 10. 流动性影响分析
            liquidity_impact = self._analyze_by_liquidity(trades, slippages)

            # 11. 优化建议
            optimization_suggestions = self._generate_suggestions(
                avg_slippage, worst_time_slots, market_cap_impact, liquidity_impact
            )

            # 12. 潜在降低空间
            potential_reduction = self._estimate_potential_reduction(
                avg_slippage, worst_time_slots, time_of_day_analysis
            )

            report = SlippageAnalysis(
                strategy_id=strategy_id,
                avg_slippage=round(avg_slippage, 2),
                median_slippage=round(median_slippage, 2),
                max_slippage=round(max_slippage, 2),
                slippage_distribution=slippage_distribution,
                percentiles=percentiles,
                total_slippage_cost=round(total_slippage_cost, 2),
                slippage_cost_ratio=round(slippage_cost_ratio, 6),
                time_of_day_analysis=time_of_day_analysis,
                worst_time_slots=worst_time_slots,
                best_time_slots=best_time_slots,
                market_cap_impact=market_cap_impact,
                liquidity_impact=liquidity_impact,
                optimization_suggestions=optimization_suggestions,
                potential_reduction=round(potential_reduction, 2),
            )

            logger.info(f"滑点分析完成: {strategy_id}, " f"平均滑点={avg_slippage:.2f}bp")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"滑点分析失败: {strategy_id}, 错误: {e}")
            return self._empty_report(strategy_id)

    def _calculate_slippages(self, trades: List[Dict[str, Any]]) -> List[float]:
        """计算滑点列表

        Args:
            trades: 交易记录

        Returns:
            List[float]: 滑点列表（基点）
        """
        slippages = []

        for trade in trades:
            expected_price = trade.get("expected_price", trade.get("signal_price", 0))
            actual_price = trade.get("price", trade.get("fill_price", 0))
            direction = trade.get("direction", trade.get("side", "buy"))

            if expected_price > 0 and actual_price > 0:
                if direction.lower() in ["buy", "long", "买入"]:
                    slippage = (actual_price - expected_price) / expected_price * 10000
                else:
                    slippage = (expected_price - actual_price) / expected_price * 10000

                slippages.append(max(0, slippage))  # 只计算负向滑点
            else:
                # 使用默认滑点估算
                slippages.append(10)  # 默认10bp

        return slippages

    def _calculate_distribution(self, slippages: np.ndarray) -> Dict[str, int]:
        """计算滑点分布

        Args:
            slippages: 滑点数组

        Returns:
            Dict[str, int]: 分布统计
        """
        distribution = {"0-5bp": 0, "5-10bp": 0, "10-20bp": 0, "20-50bp": 0, ">50bp": 0}

        for s in slippages:
            if s <= 5:
                distribution["0-5bp"] += 1
            elif s <= 10:
                distribution["5-10bp"] += 1
            elif s <= 20:
                distribution["10-20bp"] += 1
            elif s <= 50:
                distribution["20-50bp"] += 1
            else:
                distribution[">50bp"] += 1

        return distribution

    def _calculate_percentiles(self, slippages: np.ndarray) -> Dict[str, float]:
        """计算百分位数

        Args:
            slippages: 滑点数组

        Returns:
            Dict[str, float]: 百分位数
        """
        return {
            "p50": round(np.percentile(slippages, 50), 2),
            "p75": round(np.percentile(slippages, 75), 2),
            "p90": round(np.percentile(slippages, 90), 2),
            "p95": round(np.percentile(slippages, 95), 2),
            "p99": round(np.percentile(slippages, 99), 2),
        }

    def _calculate_total_cost(self, trades: List[Dict[str, Any]], slippages: List[float]) -> float:
        """计算总滑点成本

        Args:
            trades: 交易记录
            slippages: 滑点列表

        Returns:
            float: 总滑点成本
        """
        total_cost = 0.0

        for trade, slippage in zip(trades, slippages):
            amount = trade.get("amount", 0)
            if amount == 0:
                price = trade.get("price", 0)
                quantity = trade.get("quantity", 0)
                amount = price * quantity

            cost = amount * slippage / 10000
            total_cost += cost

        return total_cost

    def _analyze_by_time(self, trades: List[Dict[str, Any]], slippages: List[float]) -> Dict[str, float]:
        """按时段分析滑点

        Args:
            trades: 交易记录
            slippages: 滑点列表

        Returns:
            Dict[str, float]: 时段 -> 平均滑点
        """
        time_slippages = {slot: [] for slot in self._time_slots}

        for trade, slippage in zip(trades, slippages):
            trade_time = trade.get("time", trade.get("timestamp", ""))

            if isinstance(trade_time, str) and ":" in trade_time:
                # 提取时间部分
                time_part = trade_time.split(" ")[-1] if " " in trade_time else trade_time
                hour_min = time_part[:5]

                # 匹配时段
                for slot in self._time_slots:
                    start, end = slot.split("-")
                    if start <= hour_min < end:
                        time_slippages[slot].append(slippage)
                        break

        # 计算各时段平均滑点
        result = {}
        for slot, slips in time_slippages.items():
            if slips:
                result[slot] = round(np.mean(slips), 2)
            else:
                result[slot] = 0.0

        return result

    def _identify_best_worst_times(self, time_analysis: Dict[str, float]) -> tuple:
        """识别最佳和最差时段

        Args:
            time_analysis: 时段分析结果

        Returns:
            tuple: (最差时段列表, 最佳时段列表)
        """
        if not time_analysis:
            return [], []

        # 过滤有数据的时段
        valid_slots = {k: v for k, v in time_analysis.items() if v > 0}

        if not valid_slots:
            return [], []

        sorted_slots = sorted(valid_slots.items(), key=lambda x: x[1])

        best_slots = [s[0] for s in sorted_slots[:2]]
        worst_slots = [s[0] for s in sorted_slots[-2:]]

        return worst_slots, best_slots

    def _analyze_by_market_cap(self, trades: List[Dict[str, Any]], slippages: List[float]) -> Dict[str, float]:
        """按市值分析滑点

        Args:
            trades: 交易记录
            slippages: 滑点列表

        Returns:
            Dict[str, float]: 市值类别 -> 平均滑点
        """
        cap_slippages = {
            "micro": [],  # <20亿
            "small": [],  # 20-50亿
            "medium": [],  # 50-200亿
            "large": [],  # 200-1000亿
            "mega": [],  # >1000亿
        }

        for trade, slippage in zip(trades, slippages):
            market_cap = trade.get("market_cap", 0)

            if market_cap < 20e8:
                cap_slippages["micro"].append(slippage)
            elif market_cap < 50e8:
                cap_slippages["small"].append(slippage)
            elif market_cap < 200e8:
                cap_slippages["medium"].append(slippage)
            elif market_cap < 1000e8:
                cap_slippages["large"].append(slippage)
            else:
                cap_slippages["mega"].append(slippage)

        result = {}
        for cap, slips in cap_slippages.items():
            if slips:
                result[cap] = round(np.mean(slips), 2)

        return result

    def _analyze_by_liquidity(self, trades: List[Dict[str, Any]], slippages: List[float]) -> Dict[str, float]:
        """按流动性分析滑点

        Args:
            trades: 交易记录
            slippages: 滑点列表

        Returns:
            Dict[str, float]: 流动性类别 -> 平均滑点
        """
        liquidity_slippages = {"high": [], "medium": [], "low": []}  # 高流动性  # 中等流动性  # 低流动性

        for trade, slippage in zip(trades, slippages):
            turnover = trade.get("turnover_rate", trade.get("turnover", 0))
            volume = trade.get("volume", 0)
            avg_volume = trade.get("avg_volume", volume)

            # 根据换手率或成交量比判断流动性
            if turnover > 5 or (avg_volume > 0 and volume > avg_volume * 1.5):
                liquidity_slippages["high"].append(slippage)
            elif turnover > 2 or (avg_volume > 0 and volume > avg_volume * 0.5):
                liquidity_slippages["medium"].append(slippage)
            else:
                liquidity_slippages["low"].append(slippage)

        result = {}
        for liq, slips in liquidity_slippages.items():
            if slips:
                result[liq] = round(np.mean(slips), 2)

        return result

    def _generate_suggestions(
        self,
        avg_slippage: float,
        worst_times: List[str],
        market_cap_impact: Dict[str, float],
        liquidity_impact: Dict[str, float],
    ) -> List[str]:
        """生成优化建议

        Args:
            avg_slippage: 平均滑点
            worst_times: 最差时段
            market_cap_impact: 市值影响
            liquidity_impact: 流动性影响

        Returns:
            List[str]: 建议列表
        """
        suggestions = []

        # 整体滑点建议
        if avg_slippage > 20:
            suggestions.append("平均滑点较高，建议优先使用限价单")
        elif avg_slippage > 10:
            suggestions.append("滑点处于中等水平，有优化空间")

        # 时段建议
        if worst_times:
            suggestions.append(f"避免在{', '.join(worst_times)}时段交易，滑点较高")

        # 市值建议
        if market_cap_impact:
            high_slip_caps = [k for k, v in market_cap_impact.items() if v > avg_slippage * 1.5]
            if high_slip_caps:
                suggestions.append(f"{'、'.join(high_slip_caps)}市值股票滑点较高，建议减少交易或拆单")

        # 流动性建议
        if liquidity_impact:
            low_liq_slip = liquidity_impact.get("low", 0)
            if low_liq_slip > avg_slippage * 1.5:
                suggestions.append("低流动性股票滑点显著偏高，建议增加流动性筛选")

        # 通用建议
        suggestions.append("考虑使用TWAP/VWAP算法执行大单")
        suggestions.append("在流动性充足时段集中交易")

        return suggestions

    def _estimate_potential_reduction(
        self, avg_slippage: float, worst_times: List[str], time_analysis: Dict[str, float]
    ) -> float:
        """估算潜在降低空间

        Args:
            avg_slippage: 平均滑点
            worst_times: 最差时段
            time_analysis: 时段分析

        Returns:
            float: 潜在降低（基点）
        """
        if not time_analysis:
            return avg_slippage * 0.2  # 默认20%改善空间

        # 如果避开最差时段，可以降低的滑点
        valid_times = {k: v for k, v in time_analysis.items() if v > 0}
        if not valid_times:
            return avg_slippage * 0.2

        best_avg = np.mean([v for k, v in valid_times.items() if k not in worst_times])
        potential = avg_slippage - best_avg

        return max(0, potential)

    def _empty_report(self, strategy_id: str) -> SlippageAnalysis:
        """生成空报告"""
        return SlippageAnalysis(
            strategy_id=strategy_id,
            avg_slippage=0.0,
            median_slippage=0.0,
            max_slippage=0.0,
            slippage_distribution={},
            percentiles={},
            total_slippage_cost=0.0,
            slippage_cost_ratio=0.0,
            time_of_day_analysis={},
            worst_time_slots=[],
            best_time_slots=[],
            market_cap_impact={},
            liquidity_impact={},
            optimization_suggestions=["无交易数据"],
            potential_reduction=0.0,
        )
