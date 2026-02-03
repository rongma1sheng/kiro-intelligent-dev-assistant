"""个股结论性建议引擎

白皮书依据: 第五章 5.2.9 个股结论性建议
引擎: Soldier (战术级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import ActionType, HoldingPeriod, PositionSize, StockRecommendation


class RecommendationEngine:
    """个股结论性建议引擎

    白皮书依据: 第五章 5.2.9 个股结论性建议

    分析内容:
    - 操作建议: 买入/卖出/持有/观望
    - 置信度评估: 建议的可靠程度
    - 价格目标: 入场价/止损价/目标价
    - 仓位建议: 轻仓/标准/重仓
    - 持有周期: 短期/中期/长期
    """

    def __init__(self):
        """初始化建议引擎"""
        self._risk_reward_threshold = 2.0  # 风险收益比阈值
        logger.info("RecommendationEngine初始化完成")

    async def analyze(
        self, symbol: str, stock_data: Dict[str, Any], analysis_results: Dict[str, Any] = None
    ) -> StockRecommendation:
        """生成个股建议

        Args:
            symbol: 股票代码
            stock_data: 股票数据
            analysis_results: 其他分析结果（可选）

        Returns:
            StockRecommendation: 个股建议
        """
        logger.info(f"开始生成个股建议: {symbol}")

        try:
            prices = stock_data.get("prices", [])
            volumes = stock_data.get("volumes", [])
            fundamentals = stock_data.get("fundamentals", {})
            technicals = stock_data.get("technicals", {})
            current_price = prices[-1] if prices else 0

            # 1. 确定操作建议
            action, confidence = self._determine_action(prices, volumes, fundamentals, technicals)

            # 2. 收集支持原因
            reasons = self._collect_reasons(action, fundamentals, technicals, analysis_results)

            # 3. 识别风险
            risks = self._identify_risks(prices, volumes, fundamentals)

            # 4. 计算价格目标
            entry_price, stop_loss, target_price = self._calculate_price_targets(prices, action, current_price)

            # 5. 确定仓位建议
            position_size = self._determine_position_size(confidence, risks, action)

            # 6. 确定持有周期
            holding_period = self._determine_holding_period(action, technicals, fundamentals)

            # 7. 计算综合评分
            overall_score = self._calculate_overall_score(fundamentals, technicals, confidence)

            report = StockRecommendation(
                symbol=symbol,
                action=action,
                confidence=confidence,
                reasons=reasons,
                risks=risks,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                position_size=position_size,
                holding_period=holding_period,
                overall_score=overall_score,
            )

            logger.info(f"个股建议生成完成: {symbol}, 操作={action.value}, " f"置信度={confidence:.2f}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"个股建议生成失败: {symbol}, 错误: {e}")
            return StockRecommendation(
                symbol=symbol,
                action=ActionType.WATCH,
                confidence=0.0,
                reasons=["分析失败"],
                risks=["数据不足"],
                entry_price=0.0,
                stop_loss=0.0,
                target_price=0.0,
                position_size=PositionSize.LIGHT,
                holding_period=HoldingPeriod.SHORT,
                overall_score={},
            )

    def _determine_action(  # pylint: disable=too-many-branches
        self,
        prices: List[float],
        volumes: List[float],  # pylint: disable=unused-argument
        fundamentals: Dict[str, Any],
        technicals: Dict[str, Any],  # pylint: disable=unused-argument
    ) -> tuple:
        """确定操作建议

        Args:
            prices: 价格序列
            volumes: 成交量序列
            fundamentals: 基本面数据
            technicals: 技术指标

        Returns:
            tuple: (操作建议, 置信度)
        """
        if not prices:
            return ActionType.WATCH, 0.0

        buy_signals = 0
        sell_signals = 0
        total_signals = 0

        prices_array = np.array(prices)

        # 技术信号
        if len(prices_array) >= 20:
            ma20 = np.mean(prices_array[-20:])
            current = prices_array[-1]

            if current > ma20:
                buy_signals += 1
            else:
                sell_signals += 1
            total_signals += 1

        if len(prices_array) >= 60:
            ma60 = np.mean(prices_array[-60:])
            if prices_array[-1] > ma60:
                buy_signals += 1
            else:
                sell_signals += 1
            total_signals += 1

        # 趋势信号
        if len(prices_array) >= 10:
            recent_return = prices_array[-1] / prices_array[-10] - 1
            if recent_return > 0.05:
                buy_signals += 1
            elif recent_return < -0.05:
                sell_signals += 1
            total_signals += 1

        # 基本面信号
        pe = fundamentals.get("pe", 0)
        if pe > 0:
            if pe < 20:
                buy_signals += 1
            elif pe > 50:
                sell_signals += 1
            total_signals += 1

        roe = fundamentals.get("roe", 0)
        if roe > 15:
            buy_signals += 1
        elif roe < 5:
            sell_signals += 1
        total_signals += 1

        # 技术指标信号
        rsi = technicals.get("rsi", 50)
        if rsi < 30:
            buy_signals += 1
        elif rsi > 70:
            sell_signals += 1
        total_signals += 1

        macd_signal = technicals.get("macd_signal", "neutral")
        if macd_signal == "bullish":
            buy_signals += 1
        elif macd_signal == "bearish":
            sell_signals += 1
        total_signals += 1

        # 确定操作
        if total_signals == 0:
            return ActionType.WATCH, 0.5

        buy_ratio = buy_signals / total_signals
        sell_ratio = sell_signals / total_signals

        if buy_ratio > 0.6:  # pylint: disable=no-else-return
            confidence = buy_ratio
            return ActionType.BUY, confidence
        elif sell_ratio > 0.6:
            confidence = sell_ratio
            return ActionType.SELL, confidence
        elif buy_ratio > sell_ratio:
            return ActionType.HOLD, 0.5 + (buy_ratio - sell_ratio) / 2
        else:
            return ActionType.WATCH, 0.5

    def _collect_reasons(
        self,
        action: ActionType,
        fundamentals: Dict[str, Any],
        technicals: Dict[str, Any],
        analysis_results: Dict[str, Any],  # pylint: disable=unused-argument
    ) -> List[str]:
        """收集支持原因

        Args:
            action: 操作建议
            fundamentals: 基本面数据
            technicals: 技术指标
            analysis_results: 其他分析结果

        Returns:
            List[str]: 原因列表
        """
        reasons = []

        if action == ActionType.BUY:
            pe = fundamentals.get("pe", 0)
            if pe > 0 and pe < 20:  # pylint: disable=r1716
                reasons.append(f"估值合理，PE={pe:.1f}")

            roe = fundamentals.get("roe", 0)
            if roe > 15:
                reasons.append(f"盈利能力强，ROE={roe:.1f}%")

            rsi = technicals.get("rsi", 50)
            if rsi < 40:
                reasons.append(f"技术面超卖，RSI={rsi:.0f}")

            if technicals.get("macd_signal") == "bullish":
                reasons.append("MACD金叉，趋势向上")

        elif action == ActionType.SELL:
            pe = fundamentals.get("pe", 0)
            if pe > 50:
                reasons.append(f"估值偏高，PE={pe:.1f}")

            rsi = technicals.get("rsi", 50)
            if rsi > 70:
                reasons.append(f"技术面超买，RSI={rsi:.0f}")

            if technicals.get("macd_signal") == "bearish":
                reasons.append("MACD死叉，趋势向下")

        elif action == ActionType.HOLD:
            reasons.append("当前持仓，建议继续持有")

        else:
            reasons.append("信号不明确，建议观望")

        if not reasons:
            reasons.append("综合分析结果")

        return reasons

    def _identify_risks(
        self, prices: List[float], volumes: List[float], fundamentals: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> List[str]:  # pylint: disable=unused-argument
        """识别风险

        Args:
            prices: 价格序列
            volumes: 成交量序列
            fundamentals: 基本面数据

        Returns:
            List[str]: 风险列表
        """
        risks = []

        if prices and len(prices) >= 20:
            prices_array = np.array(prices)
            volatility = np.std(prices_array[-20:]) / np.mean(prices_array[-20:])
            if volatility > 0.1:
                risks.append(f"波动率较高({volatility:.1%})，注意风险控制")

        pe = fundamentals.get("pe", 0)
        if pe > 100:
            risks.append(f"估值极高(PE={pe:.0f})，存在回调风险")
        elif pe < 0:
            risks.append("公司亏损，基本面风险")

        debt_ratio = fundamentals.get("debt_ratio", 0)
        if debt_ratio > 70:
            risks.append(f"负债率较高({debt_ratio:.0f}%)，财务风险")

        market_cap = fundamentals.get("market_cap", 0)
        if market_cap < 20e8:
            risks.append("小市值股票，流动性风险")

        if not risks:
            risks.append("暂无明显风险")

        return risks

    def _calculate_price_targets(self, prices: List[float], action: ActionType, current_price: float) -> tuple:
        """计算价格目标

        Args:
            prices: 价格序列
            action: 操作建议
            current_price: 当前价格

        Returns:
            tuple: (入场价, 止损价, 目标价)
        """
        if not prices or current_price <= 0:
            return 0.0, 0.0, 0.0

        prices_array = np.array(prices)

        # 计算支撑阻力位
        if len(prices_array) >= 20:
            recent_high = np.max(prices_array[-20:])
            recent_low = np.min(prices_array[-20:])
            atr = np.mean(np.abs(np.diff(prices_array[-20:])))
        else:
            recent_high = np.max(prices_array)
            recent_low = np.min(prices_array)
            atr = np.mean(np.abs(np.diff(prices_array))) if len(prices_array) > 1 else current_price * 0.02

        if action == ActionType.BUY:
            # 买入建议
            entry_price = current_price  # 当前价买入
            stop_loss = max(recent_low, current_price - 2 * atr)  # 止损
            target_price = current_price + 3 * atr  # 目标价（风险收益比1:1.5）
        elif action == ActionType.SELL:
            # 卖出建议
            entry_price = current_price
            stop_loss = min(recent_high, current_price + 2 * atr)
            target_price = current_price - 3 * atr
        else:
            entry_price = current_price
            stop_loss = current_price * 0.95
            target_price = current_price * 1.1

        return round(entry_price, 2), round(stop_loss, 2), round(target_price, 2)

    def _determine_position_size(self, confidence: float, risks: List[str], action: ActionType) -> PositionSize:
        """确定仓位建议

        Args:
            confidence: 置信度
            risks: 风险列表
            action: 操作建议

        Returns:
            PositionSize: 仓位建议
        """
        if action in [ActionType.WATCH, ActionType.SELL]:
            return PositionSize.LIGHT

        risk_count = len([r for r in risks if "风险" in r])

        if confidence > 0.8 and risk_count == 0:  # pylint: disable=no-else-return
            return PositionSize.HEAVY
        elif confidence > 0.6 and risk_count <= 1:
            return PositionSize.STANDARD
        else:
            return PositionSize.LIGHT

    def _determine_holding_period(
        self, action: ActionType, technicals: Dict[str, Any], fundamentals: Dict[str, Any]
    ) -> HoldingPeriod:
        """确定持有周期

        Args:
            action: 操作建议
            technicals: 技术指标
            fundamentals: 基本面数据

        Returns:
            HoldingPeriod: 持有周期
        """
        if action == ActionType.SELL:
            return HoldingPeriod.SHORT

        # 基于基本面判断
        pe = fundamentals.get("pe", 0)
        roe = fundamentals.get("roe", 0)

        # 价值股适合长期持有
        if pe > 0 and pe < 15 and roe > 15:  # pylint: disable=r1716
            return HoldingPeriod.LONG

        # 成长股适合中期持有
        profit_growth = fundamentals.get("profit_growth", 0)
        if profit_growth > 30:
            return HoldingPeriod.MEDIUM

        # 技术面判断
        trend = technicals.get("trend", "neutral")
        if trend == "strong_up":
            return HoldingPeriod.MEDIUM

        return HoldingPeriod.SHORT

    def _calculate_overall_score(
        self,
        fundamentals: Dict[str, Any],
        technicals: Dict[str, Any],
        confidence: float,  # pylint: disable=unused-argument
    ) -> Dict[str, float]:
        """计算综合评分

        Args:
            fundamentals: 基本面数据
            technicals: 技术指标
            confidence: 置信度

        Returns:
            Dict[str, float]: 各维度评分
        """
        scores = {}

        # 估值评分
        pe = fundamentals.get("pe", 0)
        if pe > 0:
            if pe < 15:
                scores["valuation"] = 90
            elif pe < 25:
                scores["valuation"] = 70
            elif pe < 40:
                scores["valuation"] = 50
            else:
                scores["valuation"] = 30
        else:
            scores["valuation"] = 20

        # 盈利能力评分
        roe = fundamentals.get("roe", 0)
        if roe > 20:
            scores["profitability"] = 90
        elif roe > 15:
            scores["profitability"] = 75
        elif roe > 10:
            scores["profitability"] = 60
        elif roe > 5:
            scores["profitability"] = 45
        else:
            scores["profitability"] = 30

        # 成长性评分
        profit_growth = fundamentals.get("profit_growth", 0)
        if profit_growth > 50:
            scores["growth"] = 90
        elif profit_growth > 30:
            scores["growth"] = 75
        elif profit_growth > 15:
            scores["growth"] = 60
        elif profit_growth > 0:
            scores["growth"] = 45
        else:
            scores["growth"] = 30

        # 技术面评分
        rsi = technicals.get("rsi", 50)
        macd = technicals.get("macd_signal", "neutral")

        tech_score = 50
        if 30 < rsi < 70:
            tech_score += 10
        if macd == "bullish":
            tech_score += 20
        elif macd == "bearish":
            tech_score -= 20
        scores["technical"] = max(0, min(100, tech_score))

        # 综合评分
        scores["overall"] = round(
            scores.get("valuation", 50) * 0.25
            + scores.get("profitability", 50) * 0.25
            + scores.get("growth", 50) * 0.25
            + scores.get("technical", 50) * 0.25,
            1,
        )

        return scores
