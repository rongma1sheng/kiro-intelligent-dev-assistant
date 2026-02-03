"""大盘判断与宏观分析器

白皮书依据: 第五章 5.2.5 大盘判断与宏观分析
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import MacroAnalysisReport, MarketScenario


class MacroAnalyzer:
    """大盘判断与宏观分析器

    白皮书依据: 第五章 5.2.5 大盘判断与宏观分析

    分析内容:
    - 市场阶段判断: 牛市/熊市/震荡市
    - 技术分析: 均线、趋势、支撑阻力
    - 情绪分析: 市场情绪指标
    - 宏观指标: 经济数据、政策影响
    - 资金流向: 北向资金、主力资金
    - 板块轮动: 行业轮动预测
    """

    def __init__(self):
        """初始化宏观分析器"""
        self._ma_periods = [5, 10, 20, 60, 120, 250]
        logger.info("MacroAnalyzer初始化完成")

    async def analyze(self, market_data: Dict[str, Any]) -> MacroAnalysisReport:
        """分析大盘和宏观环境

        Args:
            market_data: 市场数据，包含index_prices, volumes, indicators等

        Returns:
            MacroAnalysisReport: 宏观分析报告
        """
        logger.info("开始大盘宏观分析")

        try:
            index_prices = market_data.get("index_prices", [])
            volumes = market_data.get("volumes", [])
            north_flow = market_data.get("north_flow", [])
            macro_indicators = market_data.get("macro_indicators", {})
            policy_events = market_data.get("policy_events", [])
            sector_data = market_data.get("sector_data", {})

            # 1. 判断市场阶段
            market_stage, confidence = self._determine_market_stage(index_prices, volumes)

            # 2. 技术分析
            technical_analysis = self._perform_technical_analysis(index_prices, volumes)

            # 3. 情绪分析
            sentiment_analysis = self._analyze_sentiment(index_prices, volumes, north_flow)

            # 4. 宏观指标分析
            macro_analysis = self._analyze_macro_indicators(macro_indicators)

            # 5. 政策影响分析
            policy_impact = self._analyze_policy_impact(policy_events)

            # 6. 资金流向分析
            capital_flow = self._analyze_capital_flow(north_flow, volumes)

            # 7. 板块轮动分析
            sector_rotation = self._analyze_sector_rotation(sector_data)

            # 8. 生成仓位建议
            position_recommendation = self._generate_position_recommendation(
                market_stage, confidence, sentiment_analysis
            )

            # 9. 生成策略类型建议
            strategy_type_recommendation = self._generate_strategy_recommendation(market_stage, technical_analysis)

            report = MacroAnalysisReport(
                market_stage=market_stage,
                confidence=confidence,
                technical_analysis=technical_analysis,
                sentiment_analysis=sentiment_analysis,
                macro_indicators=macro_analysis,
                policy_impact=policy_impact,
                capital_flow=capital_flow,
                sector_rotation=sector_rotation,
                position_recommendation=position_recommendation,
                strategy_type_recommendation=strategy_type_recommendation,
            )

            logger.info(f"宏观分析完成: 市场阶段={market_stage.value}, 置信度={confidence:.2f}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"宏观分析失败: {e}")
            return MacroAnalysisReport(
                market_stage=MarketScenario.SIDEWAYS,
                confidence=0.5,
                technical_analysis={},
                sentiment_analysis={},
                macro_indicators={},
                policy_impact={},
                capital_flow={},
                sector_rotation={},
                position_recommendation="半仓",
                strategy_type_recommendation=["均衡配置"],
            )

    def _determine_market_stage(  # pylint: disable=too-many-branches
        self, prices: List[float], volumes: List[float]  # pylint: disable=unused-argument
    ) -> tuple:  # pylint: disable=unused-argument
        """判断市场阶段

        Args:
            prices: 价格序列
            volumes: 成交量序列

        Returns:
            tuple: (市场阶段, 置信度)
        """
        if not prices or len(prices) < 60:
            return MarketScenario.SIDEWAYS, 0.5

        prices_array = np.array(prices)

        # 计算各周期均线
        ma_values = {}
        for period in self._ma_periods:
            if len(prices_array) >= period:
                ma_values[period] = np.mean(prices_array[-period:])

        current_price = prices_array[-1]

        # 判断趋势
        bull_signals = 0
        bear_signals = 0

        # 价格与均线关系
        for period, ma in ma_values.items():
            if current_price > ma:
                bull_signals += 1
            else:
                bear_signals += 1

        # 均线排列
        if len(ma_values) >= 3:
            ma_list = [ma_values.get(p, 0) for p in sorted(ma_values.keys())]
            if all(ma_list[i] >= ma_list[i + 1] for i in range(len(ma_list) - 1)):
                bull_signals += 2  # 多头排列
            elif all(ma_list[i] <= ma_list[i + 1] for i in range(len(ma_list) - 1)):
                bear_signals += 2  # 空头排列

        # 近期涨跌幅
        if len(prices_array) >= 20:
            recent_return = prices_array[-1] / prices_array[-20] - 1
            if recent_return > 0.05:
                bull_signals += 1
            elif recent_return < -0.05:
                bear_signals += 1

        # 波动率判断
        if len(prices_array) >= 20:
            returns = np.diff(prices_array[-21:]) / prices_array[-21:-1]
            volatility = np.std(returns) * np.sqrt(252)

            if volatility > 0.30:
                # 高波动
                if bull_signals > bear_signals:  # pylint: disable=no-else-return
                    return MarketScenario.HIGH_VOLATILITY, 0.6
                else:
                    return MarketScenario.HIGH_VOLATILITY, 0.6
            elif volatility < 0.15:
                return MarketScenario.LOW_VOLATILITY, 0.7

        # 综合判断
        total_signals = bull_signals + bear_signals
        if total_signals == 0:
            return MarketScenario.SIDEWAYS, 0.5

        bull_ratio = bull_signals / total_signals

        if bull_ratio > 0.7:  # pylint: disable=no-else-return
            return MarketScenario.BULL, bull_ratio
        elif bull_ratio < 0.3:
            return MarketScenario.BEAR, 1 - bull_ratio
        else:
            return MarketScenario.SIDEWAYS, 0.5 + abs(bull_ratio - 0.5)

    def _perform_technical_analysis(self, prices: List[float], volumes: List[float]) -> Dict[str, Any]:
        """执行技术分析

        Args:
            prices: 价格序列
            volumes: 成交量序列

        Returns:
            Dict[str, Any]: 技术分析结果
        """
        if not prices:
            return {}

        prices_array = np.array(prices)
        analysis = {}

        # 均线分析
        ma_analysis = {}
        for period in self._ma_periods:
            if len(prices_array) >= period:
                ma = np.mean(prices_array[-period:])
                ma_analysis[f"MA{period}"] = round(ma, 2)
                ma_analysis[f"MA{period}_position"] = "above" if prices_array[-1] > ma else "below"
        analysis["moving_averages"] = ma_analysis

        # 趋势分析
        if len(prices_array) >= 20:
            trend_slope = np.polyfit(range(20), prices_array[-20:], 1)[0]
            analysis["trend"] = {
                "direction": "up" if trend_slope > 0 else "down",
                "strength": abs(trend_slope) / prices_array[-1] * 100,
            }

        # 支撑阻力位
        if len(prices_array) >= 60:
            recent_high = np.max(prices_array[-60:])
            recent_low = np.min(prices_array[-60:])
            analysis["support_resistance"] = {
                "resistance": round(recent_high, 2),
                "support": round(recent_low, 2),
                "current": round(prices_array[-1], 2),
                "position_pct": round((prices_array[-1] - recent_low) / (recent_high - recent_low + 0.01) * 100, 1),
            }

        # 成交量分析
        if volumes and len(volumes) >= 20:
            volumes_array = np.array(volumes)
            avg_volume = np.mean(volumes_array[-20:])
            current_volume = volumes_array[-1]
            analysis["volume"] = {
                "current": current_volume,
                "average_20d": round(avg_volume, 0),
                "ratio": round(current_volume / avg_volume, 2) if avg_volume > 0 else 1.0,
            }

        return analysis

    def _analyze_sentiment(self, prices: List[float], volumes: List[float], north_flow: List[float]) -> Dict[str, Any]:
        """分析市场情绪

        Args:
            prices: 价格序列
            volumes: 成交量序列
            north_flow: 北向资金流向

        Returns:
            Dict[str, Any]: 情绪分析结果
        """
        sentiment = {}

        # 价格动量情绪
        if prices and len(prices) >= 20:
            prices_array = np.array(prices)
            momentum_5d = (prices_array[-1] / prices_array[-5] - 1) * 100
            momentum_20d = (prices_array[-1] / prices_array[-20] - 1) * 100

            sentiment["price_momentum"] = {
                "5d": round(momentum_5d, 2),
                "20d": round(momentum_20d, 2),
                "signal": (
                    "bullish"
                    if momentum_5d > 0 and momentum_20d > 0
                    else "bearish" if momentum_5d < 0 and momentum_20d < 0 else "neutral"
                ),
            }

        # 成交量情绪
        if volumes and len(volumes) >= 20:
            volumes_array = np.array(volumes)
            vol_ratio = volumes_array[-5:].mean() / volumes_array[-20:].mean()
            sentiment["volume_sentiment"] = {
                "ratio": round(vol_ratio, 2),
                "signal": "active" if vol_ratio > 1.2 else "quiet" if vol_ratio < 0.8 else "normal",
            }

        # 北向资金情绪
        if north_flow and len(north_flow) >= 5:
            north_array = np.array(north_flow)
            recent_flow = np.sum(north_array[-5:])
            sentiment["north_flow"] = {
                "recent_5d": round(recent_flow / 1e8, 2),  # 亿元
                "signal": "inflow" if recent_flow > 0 else "outflow",
            }

        # 综合情绪指数
        bullish_count = sum(
            1 for v in sentiment.values() if isinstance(v, dict) and v.get("signal") in ["bullish", "active", "inflow"]
        )
        bearish_count = sum(
            1 for v in sentiment.values() if isinstance(v, dict) and v.get("signal") in ["bearish", "quiet", "outflow"]
        )

        total = bullish_count + bearish_count
        if total > 0:
            sentiment["overall_index"] = round((bullish_count - bearish_count) / total * 50 + 50, 1)
        else:
            sentiment["overall_index"] = 50

        return sentiment

    def _analyze_macro_indicators(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """分析宏观指标

        Args:
            indicators: 宏观指标数据

        Returns:
            Dict[str, Any]: 宏观分析结果
        """
        if not indicators:
            return {
                "gdp_growth": {"value": None, "trend": "unknown"},
                "cpi": {"value": None, "trend": "unknown"},
                "pmi": {"value": None, "signal": "unknown"},
                "interest_rate": {"value": None, "trend": "unknown"},
            }

        analysis = {}

        # GDP增速
        if "gdp_growth" in indicators:
            gdp = indicators["gdp_growth"]
            analysis["gdp_growth"] = {
                "value": gdp,
                "trend": "positive" if gdp > 5 else "moderate" if gdp > 3 else "weak",
            }

        # CPI
        if "cpi" in indicators:
            cpi = indicators["cpi"]
            analysis["cpi"] = {"value": cpi, "trend": "high" if cpi > 3 else "moderate" if cpi > 1 else "low"}

        # PMI
        if "pmi" in indicators:
            pmi = indicators["pmi"]
            analysis["pmi"] = {"value": pmi, "signal": "expansion" if pmi > 50 else "contraction"}

        # 利率
        if "interest_rate" in indicators:
            rate = indicators["interest_rate"]
            analysis["interest_rate"] = {
                "value": rate,
                "trend": "high" if rate > 4 else "moderate" if rate > 2 else "low",
            }

        return analysis

    def _analyze_policy_impact(self, policy_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析政策影响

        Args:
            policy_events: 政策事件列表

        Returns:
            Dict[str, Any]: 政策影响分析
        """
        if not policy_events:
            return {"recent_policies": [], "overall_impact": "neutral", "affected_sectors": []}

        positive_count = 0
        negative_count = 0
        affected_sectors = set()

        for event in policy_events[-10:]:  # 最近10个政策
            impact = event.get("impact", "neutral")
            if impact == "positive":
                positive_count += 1
            elif impact == "negative":
                negative_count += 1

            sectors = event.get("affected_sectors", [])
            affected_sectors.update(sectors)

        overall_impact = (
            "positive"
            if positive_count > negative_count
            else "negative" if negative_count > positive_count else "neutral"
        )

        return {
            "recent_policies": policy_events[-5:],
            "overall_impact": overall_impact,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "affected_sectors": list(affected_sectors),
        }

    def _analyze_capital_flow(self, north_flow: List[float], volumes: List[float]) -> Dict[str, Any]:
        """分析资金流向

        Args:
            north_flow: 北向资金流向
            volumes: 成交量

        Returns:
            Dict[str, Any]: 资金流向分析
        """
        flow_analysis = {}

        # 北向资金分析
        if north_flow and len(north_flow) >= 5:
            north_array = np.array(north_flow)
            flow_analysis["north_fund"] = {
                "today": round(north_array[-1] / 1e8, 2),
                "week": round(np.sum(north_array[-5:]) / 1e8, 2),
                "month": round(np.sum(north_array[-20:]) / 1e8, 2) if len(north_array) >= 20 else None,
                "trend": "inflow" if np.sum(north_array[-5:]) > 0 else "outflow",
            }

        # 成交量趋势
        if volumes and len(volumes) >= 20:
            volumes_array = np.array(volumes)
            flow_analysis["volume_trend"] = {
                "recent_avg": round(np.mean(volumes_array[-5:]) / 1e8, 2),
                "month_avg": round(np.mean(volumes_array[-20:]) / 1e8, 2),
                "trend": "increasing" if np.mean(volumes_array[-5:]) > np.mean(volumes_array[-20:]) else "decreasing",
            }

        return flow_analysis

    def _analyze_sector_rotation(self, sector_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析板块轮动

        Args:
            sector_data: 板块数据

        Returns:
            Dict[str, Any]: 板块轮动分析
        """
        if not sector_data:
            return {"hot_sectors": [], "cold_sectors": [], "rotation_prediction": []}

        # 按涨幅排序
        sector_returns = sector_data.get("returns", {})
        if sector_returns:
            sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
            hot_sectors = [s[0] for s in sorted_sectors[:5]]
            cold_sectors = [s[0] for s in sorted_sectors[-5:]]
        else:
            hot_sectors = []
            cold_sectors = []

        # 轮动预测（简化版）
        rotation_prediction = []
        if cold_sectors:
            rotation_prediction.append(f"关注超跌板块: {', '.join(cold_sectors[:3])}")
        if hot_sectors:
            rotation_prediction.append(f"警惕高位板块: {', '.join(hot_sectors[:3])}")

        return {
            "hot_sectors": hot_sectors,
            "cold_sectors": cold_sectors,
            "sector_returns": sector_returns,
            "rotation_prediction": rotation_prediction,
        }

    def _generate_position_recommendation(  # pylint: disable=r0911
        self, market_stage: MarketScenario, confidence: float, sentiment: Dict[str, Any]
    ) -> str:
        """生成仓位建议

        Args:
            market_stage: 市场阶段
            confidence: 置信度
            sentiment: 情绪分析

        Returns:
            str: 仓位建议
        """
        sentiment_index = sentiment.get("overall_index", 50)

        if market_stage == MarketScenario.BULL:
            if confidence > 0.7 and sentiment_index > 60:  # pylint: disable=no-else-return
                return "满仓"
            elif confidence > 0.5:
                return "八成仓"
            else:
                return "六成仓"
        elif market_stage == MarketScenario.BEAR:
            if confidence > 0.7 and sentiment_index < 40:  # pylint: disable=no-else-return
                return "空仓或一成仓"
            elif confidence > 0.5:
                return "三成仓"
            else:
                return "四成仓"
        elif market_stage == MarketScenario.HIGH_VOLATILITY:
            return "四成仓（控制风险）"
        elif market_stage == MarketScenario.LOW_VOLATILITY:
            return "六成仓"
        else:
            return "半仓"

    def _generate_strategy_recommendation(
        self, market_stage: MarketScenario, technical_analysis: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> List[str]:
        """生成策略类型建议

        Args:
            market_stage: 市场阶段
            technical_analysis: 技术分析结果

        Returns:
            List[str]: 策略类型建议
        """
        recommendations = []

        if market_stage == MarketScenario.BULL:
            recommendations.extend(["趋势跟踪策略", "动量策略", "成长股策略"])
        elif market_stage == MarketScenario.BEAR:
            recommendations.extend(["防御型策略", "高股息策略", "对冲策略"])
        elif market_stage == MarketScenario.SIDEWAYS:
            recommendations.extend(["均值回归策略", "网格交易策略", "套利策略"])
        elif market_stage == MarketScenario.HIGH_VOLATILITY:
            recommendations.extend(["波动率策略", "期权策略", "短线交易策略"])
        elif market_stage == MarketScenario.LOW_VOLATILITY:
            recommendations.extend(["价值投资策略", "长期持有策略", "定投策略"])

        return recommendations
