"""市场情绪分析器

白皮书依据: 第五章 5.2.19 市场情绪
引擎: Commander (战略级分析)
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import SentimentAnalysis, SentimentCategory, SentimentTrend


class SentimentAnalyzer:
    """市场情绪分析器

    白皮书依据: 第五章 5.2.19 市场情绪

    分析内容:
    - 整体情绪: 市场整体情绪水平
    - 情绪分类: 恐慌/中性/贪婪
    - 情绪趋势: 情绪变化方向
    - 极端情绪: 是否处于极端状态
    - 投资建议: 基于情绪的操作建议
    """

    def __init__(self):
        """初始化情绪分析器"""
        self._sentiment_thresholds = {
            "extreme_fear": 0.2,
            "fear": 0.4,
            "neutral_low": 0.45,
            "neutral_high": 0.55,
            "greed": 0.6,
            "extreme_greed": 0.8,
        }
        logger.info("SentimentAnalyzer初始化完成")

    async def analyze(self, market_data: Dict[str, Any], analysis_date: str = None) -> SentimentAnalysis:
        """分析市场情绪

        Args:
            market_data: 市场数据
            analysis_date: 分析日期

        Returns:
            SentimentAnalysis: 情绪分析报告
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"开始市场情绪分析: {analysis_date}")

        try:
            prices = market_data.get("prices", [])
            volumes = market_data.get("volumes", [])
            advance_decline = market_data.get("advance_decline", {})
            put_call_ratio = market_data.get("put_call_ratio", 0)
            vix = market_data.get("vix", 0)
            margin_data = market_data.get("margin_data", {})

            # 1. 计算各项情绪指标
            sentiment_indicators = self._calculate_sentiment_indicators(
                prices, volumes, advance_decline, put_call_ratio, vix, margin_data
            )

            # 2. 计算整体情绪
            overall_sentiment = self._calculate_overall_sentiment(sentiment_indicators)

            # 3. 确定情绪分类
            sentiment_category = self._determine_sentiment_category(overall_sentiment)

            # 4. 计算情绪强度
            sentiment_strength = self._calculate_sentiment_strength(overall_sentiment, sentiment_indicators)

            # 5. 确定情绪趋势
            sentiment_trend = self._determine_sentiment_trend(prices, sentiment_indicators)

            # 6. 检测极端情绪
            extreme_sentiment, extreme_type = self._detect_extreme_sentiment(overall_sentiment, sentiment_category)

            # 7. 计算恐惧贪婪指数
            fear_greed_index = self._calculate_fear_greed_index(sentiment_indicators, overall_sentiment)

            # 8. 生成投资建议
            investment_advice = self._generate_investment_advice(sentiment_category, sentiment_trend, extreme_sentiment)

            # 9. 生成风险警告
            risk_warnings = self._generate_risk_warnings(sentiment_category, extreme_sentiment, sentiment_indicators)

            report = SentimentAnalysis(
                analysis_date=analysis_date,
                overall_sentiment=round(overall_sentiment, 2),
                sentiment_category=sentiment_category,
                sentiment_strength=round(sentiment_strength, 2),
                sentiment_trend=sentiment_trend,
                extreme_sentiment=extreme_sentiment,
                extreme_sentiment_type=extreme_type,
                sentiment_indicators=sentiment_indicators,
                fear_greed_index=fear_greed_index,
                investment_advice=investment_advice,
                risk_warnings=risk_warnings,
            )

            logger.info(f"情绪分析完成: {analysis_date}, " f"情绪={sentiment_category.value}, 指数={fear_greed_index}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"情绪分析失败: {e}")
            return SentimentAnalysis(
                analysis_date=analysis_date,
                overall_sentiment=0.5,
                sentiment_category=SentimentCategory.NEUTRAL,
                sentiment_strength=0.5,
                sentiment_trend=SentimentTrend.STABLE,
                extreme_sentiment=False,
                extreme_sentiment_type=None,
                sentiment_indicators={},
                fear_greed_index=50,
                investment_advice=["分析失败，建议谨慎操作"],
                risk_warnings=["数据不足"],
            )

    def _calculate_sentiment_indicators(  # pylint: disable=too-many-positional-arguments
        self,
        prices: List[float],
        volumes: List[float],
        advance_decline: Dict[str, int],
        put_call_ratio: float,
        vix: float,
        margin_data: Dict[str, float],
    ) -> Dict[str, float]:
        """计算情绪指标

        Args:
            prices: 价格序列
            volumes: 成交量序列
            advance_decline: 涨跌家数
            put_call_ratio: 看跌看涨比率
            vix: 波动率指数
            margin_data: 融资融券数据

        Returns:
            Dict[str, float]: 情绪指标
        """
        indicators = {}

        # 价格动量指标
        if prices and len(prices) >= 20:
            prices_array = np.array(prices)
            momentum_5d = (  # pylint: disable=unused-variable
                (prices_array[-1] / prices_array[-5] - 1) if len(prices_array) >= 5 else 0
            )  # pylint: disable=unused-variable
            momentum_20d = prices_array[-1] / prices_array[-20] - 1

            # 转换为0-1情绪值
            indicators["price_momentum"] = round(0.5 + momentum_20d * 5, 2)  # 假设20%涨幅对应1

        # 成交量指标
        if volumes and len(volumes) >= 20:
            volumes_array = np.array(volumes)
            vol_ratio = volumes_array[-5:].mean() / volumes_array[-20:].mean()
            indicators["volume_sentiment"] = round(min(1, vol_ratio / 2), 2)

        # 涨跌比指标
        if advance_decline:
            advances = advance_decline.get("advances", 0)
            declines = advance_decline.get("declines", 0)
            total = advances + declines
            if total > 0:
                indicators["advance_decline_ratio"] = round(advances / total, 2)

        # 看跌看涨比率
        if put_call_ratio > 0:
            # 高put/call比率表示恐慌
            indicators["put_call_sentiment"] = round(max(0, 1 - put_call_ratio), 2)

        # VIX指标
        if vix > 0:
            # VIX越高，恐慌越强
            if vix < 15:
                indicators["vix_sentiment"] = 0.8
            elif vix < 20:
                indicators["vix_sentiment"] = 0.6
            elif vix < 30:
                indicators["vix_sentiment"] = 0.4
            else:
                indicators["vix_sentiment"] = 0.2

        # 融资融券指标
        if margin_data:
            margin_balance = margin_data.get("margin_balance", 0)
            margin_change = margin_data.get("margin_change", 0)
            if margin_balance > 0:
                change_ratio = margin_change / margin_balance
                indicators["margin_sentiment"] = round(0.5 + change_ratio * 10, 2)

        return indicators

    def _calculate_overall_sentiment(self, indicators: Dict[str, float]) -> float:
        """计算整体情绪

        Args:
            indicators: 情绪指标

        Returns:
            float: 整体情绪 0-1
        """
        if not indicators:
            return 0.5

        # 加权平均
        weights = {
            "price_momentum": 0.25,
            "volume_sentiment": 0.15,
            "advance_decline_ratio": 0.20,
            "put_call_sentiment": 0.15,
            "vix_sentiment": 0.15,
            "margin_sentiment": 0.10,
        }

        total_weight = 0
        weighted_sum = 0

        for indicator, value in indicators.items():
            weight = weights.get(indicator, 0.1)
            weighted_sum += value * weight
            total_weight += weight

        if total_weight > 0:
            return weighted_sum / total_weight

        return 0.5

    def _determine_sentiment_category(self, overall_sentiment: float) -> SentimentCategory:
        """确定情绪分类

        Args:
            overall_sentiment: 整体情绪

        Returns:
            SentimentCategory: 情绪分类
        """
        if overall_sentiment <= self._sentiment_thresholds["extreme_fear"]:  # pylint: disable=no-else-return
            return SentimentCategory.EXTREME_FEAR
        elif overall_sentiment <= self._sentiment_thresholds["fear"]:
            return SentimentCategory.FEAR
        elif overall_sentiment <= self._sentiment_thresholds["neutral_high"]:
            return SentimentCategory.NEUTRAL
        elif overall_sentiment <= self._sentiment_thresholds["greed"]:
            return SentimentCategory.GREED
        else:
            return SentimentCategory.EXTREME_GREED

    def _calculate_sentiment_strength(self, overall_sentiment: float, indicators: Dict[str, float]) -> float:
        """计算情绪强度

        Args:
            overall_sentiment: 整体情绪
            indicators: 情绪指标

        Returns:
            float: 情绪强度 0-1
        """
        # 偏离中性的程度
        deviation = abs(overall_sentiment - 0.5) * 2

        # 指标一致性
        if indicators:
            values = list(indicators.values())
            consistency = 1 - np.std(values)
        else:
            consistency = 0.5

        strength = deviation * 0.7 + consistency * 0.3
        return min(1, strength)

    def _determine_sentiment_trend(
        self, prices: List[float], indicators: Dict[str, float]  # pylint: disable=unused-argument
    ) -> SentimentTrend:  # pylint: disable=unused-argument
        """确定情绪趋势

        Args:
            prices: 价格序列
            indicators: 情绪指标

        Returns:
            SentimentTrend: 情绪趋势
        """
        if not prices or len(prices) < 10:
            return SentimentTrend.STABLE

        prices_array = np.array(prices)

        # 计算近期趋势
        recent_return = prices_array[-1] / prices_array[-5] - 1

        if recent_return > 0.02:  # pylint: disable=no-else-return
            return SentimentTrend.IMPROVING
        elif recent_return < -0.02:
            return SentimentTrend.DETERIORATING
        else:
            return SentimentTrend.STABLE

    def _detect_extreme_sentiment(
        self, overall_sentiment: float, category: SentimentCategory  # pylint: disable=unused-argument
    ) -> tuple:  # pylint: disable=unused-argument
        """检测极端情绪

        Args:
            overall_sentiment: 整体情绪
            category: 情绪分类

        Returns:
            tuple: (是否极端, 极端类型)
        """
        if category == SentimentCategory.EXTREME_FEAR:  # pylint: disable=no-else-return
            return True, "extreme_fear"
        elif category == SentimentCategory.EXTREME_GREED:
            return True, "extreme_greed"
        else:
            return False, None

    def _calculate_fear_greed_index(
        self, indicators: Dict[str, float], overall_sentiment: float  # pylint: disable=unused-argument
    ) -> int:  # pylint: disable=unused-argument
        """计算恐惧贪婪指数

        Args:
            indicators: 情绪指标
            overall_sentiment: 整体情绪

        Returns:
            int: 恐惧贪婪指数 0-100
        """
        # 转换为0-100的指数
        index = int(overall_sentiment * 100)
        return max(0, min(100, index))

    def _generate_investment_advice(
        self, category: SentimentCategory, trend: SentimentTrend, extreme: bool  # pylint: disable=unused-argument
    ) -> List[str]:
        """生成投资建议

        Args:
            category: 情绪分类
            trend: 情绪趋势
            extreme: 是否极端

        Returns:
            List[str]: 投资建议
        """
        advice = []

        if category == SentimentCategory.EXTREME_FEAR:
            advice.append("市场极度恐慌，可能是逆向投资机会")
            advice.append("分批建仓优质资产")
            advice.append("保持耐心，等待情绪修复")
        elif category == SentimentCategory.FEAR:
            advice.append("市场情绪偏悲观，可适度布局")
            advice.append("关注超跌反弹机会")
        elif category == SentimentCategory.NEUTRAL:
            advice.append("市场情绪中性，按计划操作")
            advice.append("保持均衡配置")
        elif category == SentimentCategory.GREED:
            advice.append("市场情绪偏乐观，注意风险")
            advice.append("适度减仓锁定利润")
        else:  # EXTREME_GREED
            advice.append("市场极度贪婪，高度警惕")
            advice.append("大幅减仓，保留现金")
            advice.append("避免追高")

        # 根据趋势调整
        if trend == SentimentTrend.DETERIORATING and category in [
            SentimentCategory.GREED,
            SentimentCategory.EXTREME_GREED,
        ]:
            advice.append("情绪见顶回落，加速减仓")
        elif trend == SentimentTrend.IMPROVING and category in [SentimentCategory.FEAR, SentimentCategory.EXTREME_FEAR]:
            advice.append("情绪触底回升，可加大布局")

        return advice

    def _generate_risk_warnings(
        self, category: SentimentCategory, extreme: bool, indicators: Dict[str, float]
    ) -> List[str]:
        """生成风险警告

        Args:
            category: 情绪分类
            extreme: 是否极端
            indicators: 情绪指标

        Returns:
            List[str]: 风险警告
        """
        warnings = []

        if extreme:
            if category == SentimentCategory.EXTREME_FEAR:
                warnings.append("【警告】市场恐慌可能继续，注意流动性风险")
            else:
                warnings.append("【警告】市场过热，回调风险极高")

        # 检查指标异常
        vix_sentiment = indicators.get("vix_sentiment", 0.5)
        if vix_sentiment < 0.3:
            warnings.append("波动率指数偏高，市场不确定性大")

        put_call = indicators.get("put_call_sentiment", 0.5)
        if put_call < 0.3:
            warnings.append("看跌期权比例偏高，市场避险情绪浓")

        if not warnings:
            warnings.append("当前无重大风险警告")

        return warnings
