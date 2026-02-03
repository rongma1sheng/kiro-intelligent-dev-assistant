"""主力资金深度分析器

白皮书依据: 第五章 5.2.8 主力资金深度分析
引擎: Soldier (战术级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import BehaviorPattern, MainForceType, RiskLevel, SmartMoneyDeepAnalysis


class SmartMoneyAnalyzer:
    """主力资金深度分析器

    白皮书依据: 第五章 5.2.8 主力资金深度分析

    分析内容:
    - 主力建仓成本: 估算主力持仓成本
    - 持股量估算: 估算主力持股比例
    - 主力类型识别: 机构/游资/老庄
    - 行为模式判断: 建仓/洗盘/拉升/出货
    - 跟随风险评估: 评估跟随主力的风险
    """

    def __init__(self):
        """初始化主力分析器"""
        self._volume_threshold = 2.0  # 放量阈值
        self._price_change_threshold = 0.03  # 价格变动阈值
        logger.info("SmartMoneyAnalyzer初始化完成")

    async def analyze(self, symbol: str, stock_data: Dict[str, Any]) -> SmartMoneyDeepAnalysis:
        """分析主力资金

        Args:
            symbol: 股票代码
            stock_data: 股票数据，包含prices, volumes, turnover等

        Returns:
            SmartMoneyDeepAnalysis: 主力分析报告
        """
        logger.info(f"开始主力资金分析: {symbol}")

        try:
            prices = stock_data.get("prices", [])
            volumes = stock_data.get("volumes", [])
            turnover = stock_data.get("turnover", [])
            float_shares = stock_data.get("float_shares", 0)
            current_price = prices[-1] if prices else 0

            # 1. 估算主力建仓成本
            cost_basis, cost_range = self._estimate_cost_basis(prices, volumes, turnover)

            # 2. 估算持股量
            estimated_holdings, holdings_pct = self._estimate_holdings(volumes, turnover, float_shares)

            # 3. 计算主力浮盈浮亏
            profit_loss, profit_loss_pct = self._calculate_profit_loss(cost_basis, current_price, estimated_holdings)

            # 4. 识别主力类型
            main_force_type = self._identify_main_force_type(volumes, turnover, prices)

            # 5. 判断行为模式
            behavior_pattern = self._identify_behavior_pattern(prices, volumes, cost_basis, current_price)

            # 6. 预测下一步动作
            next_action_prediction = self._predict_next_action(behavior_pattern, profit_loss_pct, holdings_pct)

            # 7. 评估跟随风险
            follow_risk = self._assess_follow_risk(behavior_pattern, profit_loss_pct, main_force_type)

            # 8. 计算分析置信度
            confidence = self._calculate_confidence(len(prices), len(volumes), float_shares)

            report = SmartMoneyDeepAnalysis(
                symbol=symbol,
                cost_basis=cost_basis,
                cost_range=cost_range,
                estimated_holdings=estimated_holdings,
                holdings_pct=holdings_pct,
                profit_loss=profit_loss,
                profit_loss_pct=profit_loss_pct,
                main_force_type=main_force_type,
                behavior_pattern=behavior_pattern,
                next_action_prediction=next_action_prediction,
                follow_risk=follow_risk,
                confidence=confidence,
            )

            logger.info(
                f"主力分析完成: {symbol}, 类型={main_force_type.value}, "
                f"行为={behavior_pattern.value}, 风险={follow_risk.value}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"主力分析失败: {symbol}, 错误: {e}")
            return SmartMoneyDeepAnalysis(
                symbol=symbol,
                cost_basis=0.0,
                cost_range=(0.0, 0.0),
                estimated_holdings=0.0,
                holdings_pct=0.0,
                profit_loss=0.0,
                profit_loss_pct=0.0,
                main_force_type=MainForceType.MIXED,
                behavior_pattern=BehaviorPattern.WAITING,
                next_action_prediction="无法预测",
                follow_risk=RiskLevel.HIGH,
                confidence=0.0,
            )

    def _estimate_cost_basis(
        self, prices: List[float], volumes: List[float], turnover: List[float]  # pylint: disable=unused-argument
    ) -> tuple:  # pylint: disable=unused-argument
        """估算主力建仓成本

        Args:
            prices: 价格序列
            volumes: 成交量序列
            turnover: 换手率序列

        Returns:
            tuple: (成本价, 成本区间)
        """
        if not prices or not volumes:
            return 0.0, (0.0, 0.0)

        prices_array = np.array(prices)
        volumes_array = np.array(volumes)

        # 使用成交量加权平均价格作为成本估算
        if len(prices_array) >= 60:
            # 取最近60天
            recent_prices = prices_array[-60:]
            recent_volumes = volumes_array[-60:]
        else:
            recent_prices = prices_array
            recent_volumes = volumes_array

        # 成交量加权平均价
        total_value = np.sum(recent_prices * recent_volumes)
        total_volume = np.sum(recent_volumes)

        if total_volume > 0:
            vwap = total_value / total_volume
        else:
            vwap = np.mean(recent_prices)

        # 成本区间
        cost_low = np.percentile(recent_prices, 25)
        cost_high = np.percentile(recent_prices, 75)

        return round(vwap, 2), (round(cost_low, 2), round(cost_high, 2))

    def _estimate_holdings(
        self, volumes: List[float], turnover: List[float], float_shares: float  # pylint: disable=unused-argument
    ) -> tuple:  # pylint: disable=unused-argument
        """估算主力持股量

        Args:
            volumes: 成交量序列
            turnover: 换手率序列
            float_shares: 流通股本

        Returns:
            tuple: (持股量, 持股比例)
        """
        if not volumes or float_shares <= 0:
            return 0.0, 0.0

        volumes_array = np.array(volumes)

        # 识别大单成交（假设大于平均成交量2倍的为主力成交）
        avg_volume = np.mean(volumes_array)
        large_volume_mask = volumes_array > avg_volume * self._volume_threshold

        # 估算主力成交量（简化模型）
        large_volumes = volumes_array[large_volume_mask]
        estimated_main_volume = np.sum(large_volumes) * 0.3  # 假设30%为净买入

        # 转换为持股比例
        holdings_pct = estimated_main_volume / float_shares if float_shares > 0 else 0
        holdings_pct = min(0.5, holdings_pct)  # 上限50%

        estimated_holdings = holdings_pct * float_shares

        return round(estimated_holdings, 0), round(holdings_pct, 4)

    def _calculate_profit_loss(self, cost_basis: float, current_price: float, holdings: float) -> tuple:
        """计算主力浮盈浮亏

        Args:
            cost_basis: 成本价
            current_price: 当前价
            holdings: 持股量

        Returns:
            tuple: (浮盈浮亏金额, 浮盈浮亏比例)
        """
        if cost_basis <= 0 or holdings <= 0:
            return 0.0, 0.0

        profit_loss_pct = (current_price - cost_basis) / cost_basis
        profit_loss = (current_price - cost_basis) * holdings

        return round(profit_loss, 2), round(profit_loss_pct, 4)

    def _identify_main_force_type(
        self, volumes: List[float], turnover: List[float], prices: List[float]
    ) -> MainForceType:
        """识别主力类型

        Args:
            volumes: 成交量序列
            turnover: 换手率序列
            prices: 价格序列

        Returns:
            MainForceType: 主力类型
        """
        if not volumes or not prices:
            return MainForceType.MIXED

        volumes_array = np.array(volumes)
        prices_array = np.array(prices)

        # 计算特征
        avg_turnover = np.mean(turnover) if turnover else 0
        volume_volatility = np.std(volumes_array) / np.mean(volumes_array) if np.mean(volumes_array) > 0 else 0
        price_volatility = np.std(prices_array) / np.mean(prices_array) if np.mean(prices_array) > 0 else 0

        # 机构特征：换手率低，成交量稳定，价格波动小
        if avg_turnover < 3 and volume_volatility < 0.5 and price_volatility < 0.05:
            return MainForceType.INSTITUTION

        # 游资特征：换手率高，成交量波动大，价格波动大
        if avg_turnover > 10 and volume_volatility > 1.0 and price_volatility > 0.1:
            return MainForceType.HOT_MONEY

        # 老庄特征：长期控盘，换手率极低
        if avg_turnover < 1 and len(prices) > 120:
            return MainForceType.OLD_BANKER

        return MainForceType.MIXED

    def _identify_behavior_pattern(
        self, prices: List[float], volumes: List[float], cost_basis: float, current_price: float
    ) -> BehaviorPattern:
        """识别行为模式

        Args:
            prices: 价格序列
            volumes: 成交量序列
            cost_basis: 成本价
            current_price: 当前价

        Returns:
            BehaviorPattern: 行为模式
        """
        if not prices or not volumes or len(prices) < 20:
            return BehaviorPattern.WAITING

        prices_array = np.array(prices)
        volumes_array = np.array(volumes)

        # 计算近期特征
        recent_prices = prices_array[-20:]
        recent_volumes = volumes_array[-20:]

        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        volume_trend = np.mean(recent_volumes[-5:]) / np.mean(recent_volumes[:5])

        profit_pct = (current_price - cost_basis) / cost_basis if cost_basis > 0 else 0

        # 建仓：价格低位，成交量放大
        if profit_pct < 0.1 and volume_trend > 1.5 and price_trend > -0.05:
            return BehaviorPattern.ACCUMULATING

        # 洗盘：价格震荡，成交量萎缩
        if abs(price_trend) < 0.05 and volume_trend < 0.8:
            return BehaviorPattern.WASHING

        # 拉升：价格上涨，成交量放大
        if price_trend > 0.1 and volume_trend > 1.2:
            return BehaviorPattern.PULLING

        # 出货：价格高位，成交量放大但价格滞涨
        if profit_pct > 0.3 and volume_trend > 1.5 and price_trend < 0.05:
            return BehaviorPattern.DISTRIBUTING

        return BehaviorPattern.WAITING

    def _predict_next_action(
        self,
        behavior_pattern: BehaviorPattern,
        profit_loss_pct: float,
        holdings_pct: float,  # pylint: disable=unused-argument
    ) -> str:
        """预测下一步动作

        Args:
            behavior_pattern: 当前行为模式
            profit_loss_pct: 浮盈浮亏比例
            holdings_pct: 持股比例

        Returns:
            str: 下一步预测
        """
        predictions = {
            BehaviorPattern.ACCUMULATING: "继续吸筹，等待时机拉升",
            BehaviorPattern.WASHING: "洗盘接近尾声，可能即将拉升",
            BehaviorPattern.PULLING: "拉升中，注意高位风险",
            BehaviorPattern.DISTRIBUTING: "出货中，建议回避",
            BehaviorPattern.WAITING: "观望中，等待方向明确",
        }

        base_prediction = predictions.get(behavior_pattern, "无法预测")

        # 根据盈利情况调整
        if profit_loss_pct > 0.5:
            base_prediction += "（主力获利丰厚，注意出货风险）"
        elif profit_loss_pct < -0.1:
            base_prediction += "（主力被套，可能继续护盘）"

        return base_prediction

    def _assess_follow_risk(
        self, behavior_pattern: BehaviorPattern, profit_loss_pct: float, main_force_type: MainForceType
    ) -> RiskLevel:
        """评估跟随风险

        Args:
            behavior_pattern: 行为模式
            profit_loss_pct: 浮盈浮亏比例
            main_force_type: 主力类型

        Returns:
            RiskLevel: 风险等级
        """
        risk_score = 0

        # 行为模式风险
        behavior_risk = {
            BehaviorPattern.ACCUMULATING: 1,
            BehaviorPattern.WASHING: 2,
            BehaviorPattern.PULLING: 2,
            BehaviorPattern.DISTRIBUTING: 4,
            BehaviorPattern.WAITING: 2,
        }
        risk_score += behavior_risk.get(behavior_pattern, 2)

        # 盈利风险
        if profit_loss_pct > 0.5:
            risk_score += 2
        elif profit_loss_pct > 0.3:
            risk_score += 1
        elif profit_loss_pct < -0.2:
            risk_score += 1

        # 主力类型风险
        type_risk = {
            MainForceType.INSTITUTION: 0,
            MainForceType.HOT_MONEY: 2,
            MainForceType.OLD_BANKER: 1,
            MainForceType.MIXED: 1,
        }
        risk_score += type_risk.get(main_force_type, 1)

        # 确定风险等级
        if risk_score >= 6:  # pylint: disable=no-else-return
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_confidence(self, price_count: int, volume_count: int, float_shares: float) -> float:
        """计算分析置信度

        Args:
            price_count: 价格数据点数
            volume_count: 成交量数据点数
            float_shares: 流通股本

        Returns:
            float: 置信度 0-1
        """
        confidence = 0.5  # 基础置信度

        # 数据量影响
        if price_count >= 120:
            confidence += 0.2
        elif price_count >= 60:
            confidence += 0.1

        if volume_count >= 120:
            confidence += 0.1
        elif volume_count >= 60:
            confidence += 0.05

        # 流通股本信息
        if float_shares > 0:
            confidence += 0.1

        return min(1.0, confidence)
