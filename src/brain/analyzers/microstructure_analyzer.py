"""市场微观结构分析器

白皮书依据: 第五章 5.2.6 市场微观结构分析
引擎: Soldier (战术级分析)
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import MicrostructureReport


class MicrostructureAnalyzer:
    """市场微观结构分析器

    白皮书依据: 第五章 5.2.6 市场微观结构分析

    分析内容:
    - 涨跌停统计: 涨停/跌停家数
    - 封单强度: 涨停封单金额
    - 炸板率: 涨停打开比例
    - 赚钱效应: 市场整体盈利情况
    - 热点分布: 题材/行业/市值分布
    - 情绪强度: 市场情绪判断
    """

    def __init__(self):
        """初始化微观结构分析器"""
        self._limit_up_threshold = 0.095  # 涨停阈值（考虑四舍五入）
        self._limit_down_threshold = -0.095  # 跌停阈值
        logger.info("MicrostructureAnalyzer初始化完成")

    async def analyze(self, market_data: Dict[str, Any], analysis_date: str = None) -> MicrostructureReport:
        """分析市场微观结构

        Args:
            market_data: 市场数据，包含stocks, limit_ups, limit_downs等
            analysis_date: 分析日期

        Returns:
            MicrostructureReport: 微观结构分析报告
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"开始微观结构分析: {analysis_date}")

        try:
            stocks = market_data.get("stocks", [])
            limit_up_stocks = market_data.get("limit_ups", [])
            limit_down_stocks = market_data.get("limit_downs", [])
            sector_data = market_data.get("sectors", {})

            # 1. 统计涨跌停
            limit_up_count = len(limit_up_stocks) if limit_up_stocks else self._count_limit_ups(stocks)
            limit_down_count = len(limit_down_stocks) if limit_down_stocks else self._count_limit_downs(stocks)

            # 2. 计算封单强度
            seal_strength = self._calculate_seal_strength(limit_up_stocks)

            # 3. 计算炸板率
            blow_up_rate = self._calculate_blow_up_rate(market_data)

            # 4. 计算赚钱效应
            money_making_effect = self._calculate_money_making_effect(stocks)

            # 5. 分析分布
            distribution = self._analyze_distribution(stocks, sector_data)

            # 6. 识别热点
            hot_spots = self._identify_hot_spots(limit_up_stocks, sector_data)

            # 7. 判断情绪强度
            sentiment_strength = self._determine_sentiment_strength(
                limit_up_count, limit_down_count, money_making_effect, blow_up_rate
            )

            # 8. 预测次日走势
            next_day_prediction = self._predict_next_day(sentiment_strength, money_making_effect, blow_up_rate)

            report = MicrostructureReport(
                analysis_date=analysis_date,
                limit_up_count=limit_up_count,
                limit_down_count=limit_down_count,
                seal_strength=seal_strength,
                blow_up_rate=blow_up_rate,
                money_making_effect=money_making_effect,
                distribution=distribution,
                hot_spots=hot_spots,
                sentiment_strength=sentiment_strength,
                next_day_prediction=next_day_prediction,
            )

            logger.info(
                f"微观结构分析完成: 涨停{limit_up_count}家, 跌停{limit_down_count}家, " f"情绪{sentiment_strength}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"微观结构分析失败: {e}")
            return MicrostructureReport(
                analysis_date=analysis_date,
                limit_up_count=0,
                limit_down_count=0,
                seal_strength={},
                blow_up_rate=0.0,
                money_making_effect=0.5,
                distribution={},
                hot_spots=[],
                sentiment_strength="中",
                next_day_prediction="不确定",
            )

    def _count_limit_ups(self, stocks: List[Dict[str, Any]]) -> int:
        """统计涨停家数

        Args:
            stocks: 股票数据列表

        Returns:
            int: 涨停家数
        """
        if not stocks:
            return 0

        count = 0
        for stock in stocks:
            change_pct = stock.get("change_pct", 0)
            if change_pct >= self._limit_up_threshold * 100:  # 转换为百分比
                count += 1

        return count

    def _count_limit_downs(self, stocks: List[Dict[str, Any]]) -> int:
        """统计跌停家数

        Args:
            stocks: 股票数据列表

        Returns:
            int: 跌停家数
        """
        if not stocks:
            return 0

        count = 0
        for stock in stocks:
            change_pct = stock.get("change_pct", 0)
            if change_pct <= self._limit_down_threshold * 100:
                count += 1

        return count

    def _calculate_seal_strength(self, limit_up_stocks: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算封单强度

        Args:
            limit_up_stocks: 涨停股票列表

        Returns:
            Dict[str, float]: 封单强度统计
        """
        if not limit_up_stocks:
            return {"avg_seal_amount": 0.0, "max_seal_amount": 0.0, "total_seal_amount": 0.0, "strong_seal_count": 0}

        seal_amounts = []
        for stock in limit_up_stocks:
            seal_amount = stock.get("seal_amount", 0)
            seal_amounts.append(seal_amount)

        seal_array = np.array(seal_amounts)

        return {
            "avg_seal_amount": round(np.mean(seal_array) / 1e8, 2),  # 亿元
            "max_seal_amount": round(np.max(seal_array) / 1e8, 2),
            "total_seal_amount": round(np.sum(seal_array) / 1e8, 2),
            "strong_seal_count": int(np.sum(seal_array > 1e8)),  # 封单超过1亿
        }

    def _calculate_blow_up_rate(self, market_data: Dict[str, Any]) -> float:
        """计算炸板率

        Args:
            market_data: 市场数据

        Returns:
            float: 炸板率 0-1
        """
        touched_limit = market_data.get("touched_limit_count", 0)
        final_limit = market_data.get("final_limit_count", 0)

        if touched_limit == 0:
            return 0.0

        blow_up_count = touched_limit - final_limit
        return blow_up_count / touched_limit

    def _calculate_money_making_effect(self, stocks: List[Dict[str, Any]]) -> float:
        """计算赚钱效应

        Args:
            stocks: 股票数据列表

        Returns:
            float: 赚钱效应指数 0-1
        """
        if not stocks:
            return 0.5

        positive_count = 0
        total_count = len(stocks)

        for stock in stocks:
            change_pct = stock.get("change_pct", 0)
            if change_pct > 0:
                positive_count += 1

        return positive_count / total_count

    def _analyze_distribution(
        self, stocks: List[Dict[str, Any]], sector_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """分析分布情况

        Args:
            stocks: 股票数据列表
            sector_data: 板块数据

        Returns:
            Dict[str, Any]: 分布分析结果
        """
        distribution = {"by_sector": {}, "by_market_cap": {}, "by_theme": {}}

        if not stocks:
            return distribution

        # 按板块分布
        sector_counts = {}
        for stock in stocks:
            sector = stock.get("sector", "其他")
            change_pct = stock.get("change_pct", 0)
            if sector not in sector_counts:
                sector_counts[sector] = {"count": 0, "positive": 0, "avg_change": []}
            sector_counts[sector]["count"] += 1
            if change_pct > 0:
                sector_counts[sector]["positive"] += 1
            sector_counts[sector]["avg_change"].append(change_pct)

        for sector, data in sector_counts.items():
            data["avg_change"] = round(np.mean(data["avg_change"]), 2)
        distribution["by_sector"] = sector_counts

        # 按市值分布
        market_cap_ranges = {
            "micro": (0, 20e8),  # <20亿
            "small": (20e8, 50e8),  # 20-50亿
            "medium": (50e8, 200e8),  # 50-200亿
            "large": (200e8, 1000e8),  # 200-1000亿
            "mega": (1000e8, float("inf")),  # >1000亿
        }

        cap_distribution = {k: 0 for k in market_cap_ranges.keys()}  # pylint: disable=consider-iterating-dictionary
        for stock in stocks:
            market_cap = stock.get("market_cap", 0)
            for cap_type, (low, high) in market_cap_ranges.items():
                if low <= market_cap < high:
                    cap_distribution[cap_type] += 1
                    break
        distribution["by_market_cap"] = cap_distribution

        return distribution

    def _identify_hot_spots(
        self, limit_up_stocks: List[Dict[str, Any]], sector_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> List[str]:  # pylint: disable=unused-argument
        """识别热点

        Args:
            limit_up_stocks: 涨停股票列表
            sector_data: 板块数据

        Returns:
            List[str]: 热点列表
        """
        hot_spots = []

        if not limit_up_stocks:
            return hot_spots

        # 统计涨停股票的板块分布
        sector_limit_ups = {}
        for stock in limit_up_stocks:
            sector = stock.get("sector", "其他")
            themes = stock.get("themes", [])

            if sector not in sector_limit_ups:
                sector_limit_ups[sector] = 0
            sector_limit_ups[sector] += 1

            for theme in themes:
                if theme not in sector_limit_ups:
                    sector_limit_ups[theme] = 0
                sector_limit_ups[theme] += 1

        # 按涨停数量排序
        sorted_sectors = sorted(sector_limit_ups.items(), key=lambda x: x[1], reverse=True)

        # 取前5个热点
        for sector, count in sorted_sectors[:5]:
            if count >= 2:  # 至少2个涨停才算热点
                hot_spots.append(f"{sector}({count}家涨停)")

        return hot_spots

    def _determine_sentiment_strength(
        self, limit_up_count: int, limit_down_count: int, money_making_effect: float, blow_up_rate: float
    ) -> str:
        """判断情绪强度

        Args:
            limit_up_count: 涨停家数
            limit_down_count: 跌停家数
            money_making_effect: 赚钱效应
            blow_up_rate: 炸板率

        Returns:
            str: 情绪强度（强/中/弱）
        """
        score = 0

        # 涨跌停比
        if limit_up_count > limit_down_count * 3:
            score += 2
        elif limit_up_count > limit_down_count:
            score += 1
        elif limit_down_count > limit_up_count * 3:
            score -= 2
        elif limit_down_count > limit_up_count:
            score -= 1

        # 赚钱效应
        if money_making_effect > 0.6:
            score += 2
        elif money_making_effect > 0.5:
            score += 1
        elif money_making_effect < 0.4:
            score -= 2
        elif money_making_effect < 0.5:
            score -= 1

        # 炸板率
        if blow_up_rate < 0.2:
            score += 1
        elif blow_up_rate > 0.5:
            score -= 1

        # 涨停数量
        if limit_up_count > 100:
            score += 1
        elif limit_up_count < 30:
            score -= 1

        if score >= 3:  # pylint: disable=no-else-return
            return "强"
        elif score <= -3:
            return "弱"
        else:
            return "中"

    def _predict_next_day(self, sentiment_strength: str, money_making_effect: float, blow_up_rate: float) -> str:
        """预测次日走势

        Args:
            sentiment_strength: 情绪强度
            money_making_effect: 赚钱效应
            blow_up_rate: 炸板率

        Returns:
            str: 次日预测（延续/反转/震荡）
        """
        if sentiment_strength == "强":
            if money_making_effect > 0.65 and blow_up_rate < 0.3:  # pylint: disable=no-else-return
                return "延续（情绪高涨，预计继续上攻）"
            elif blow_up_rate > 0.4:
                return "震荡（炸板率偏高，注意分化）"
            else:
                return "延续（整体偏强）"
        elif sentiment_strength == "弱":
            if money_making_effect < 0.35:  # pylint: disable=no-else-return
                return "延续（情绪低迷，预计继续调整）"
            else:
                return "反转（超跌后可能反弹）"
        else:
            if money_making_effect > 0.55:  # pylint: disable=no-else-return
                return "震荡偏强"
            elif money_making_effect < 0.45:
                return "震荡偏弱"
            else:
                return "震荡（方向不明）"
