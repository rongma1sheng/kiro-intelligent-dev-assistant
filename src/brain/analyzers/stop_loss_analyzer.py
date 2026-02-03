"""止损逻辑优化分析器

白皮书依据: 第五章 5.2.12 止损逻辑优化
引擎: Soldier (战术级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import StopLossAnalysis, StopLossType


class StopLossAnalyzer:
    """止损逻辑优化分析器

    白皮书依据: 第五章 5.2.12 止损逻辑优化

    分析内容:
    - 当前止损评估: 评估现有止损策略
    - 最优止损计算: 计算最优止损位
    - 止损有效性: 评估止损的实际效果
    - 替代策略: 提供其他止损方案
    """

    def __init__(self):
        """初始化止损分析器"""
        self._stop_loss_types = [StopLossType.FIXED, StopLossType.ATR, StopLossType.TRAILING, StopLossType.VOLATILITY]
        logger.info("StopLossAnalyzer初始化完成")

    async def analyze(
        self, strategy_id: str, trades: List[Dict[str, Any]], prices: List[float] = None
    ) -> StopLossAnalysis:
        """分析止损逻辑

        Args:
            strategy_id: 策略ID
            trades: 交易记录
            prices: 价格序列（用于计算ATR等）

        Returns:
            StopLossAnalysis: 止损分析报告
        """
        logger.info(f"开始止损逻辑分析: {strategy_id}")

        try:
            # 1. 分析当前止损设置
            current_stop_loss = self._analyze_current_stop_loss(trades)

            # 2. 计算最优止损
            optimal_stop_loss, optimal_type = self._calculate_optimal_stop_loss(trades, prices)

            # 3. 评估止损有效性
            effectiveness = self._evaluate_effectiveness(trades)

            # 4. 统计止损交易
            stopped_trades, avg_stopped_loss = self._analyze_stopped_trades(trades)

            # 5. 生成替代策略
            alternative_strategies = self._generate_alternative_strategies(trades, prices, current_stop_loss)

            # 6. 生成建议
            recommendations = self._generate_recommendations(
                current_stop_loss, optimal_stop_loss, effectiveness, stopped_trades, len(trades)
            )

            report = StopLossAnalysis(
                strategy_id=strategy_id,
                current_stop_loss=current_stop_loss,
                optimal_stop_loss=optimal_stop_loss,
                optimal_stop_loss_type=optimal_type,
                stop_loss_effectiveness=effectiveness,
                stopped_trades=stopped_trades,
                avg_stopped_loss=avg_stopped_loss,
                alternative_strategies=alternative_strategies,
                recommendations=recommendations,
            )

            logger.info(f"止损分析完成: {strategy_id}, " f"当前={current_stop_loss:.2%}, 最优={optimal_stop_loss:.2%}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"止损分析失败: {strategy_id}, 错误: {e}")
            return StopLossAnalysis(
                strategy_id=strategy_id,
                current_stop_loss=0.05,
                optimal_stop_loss=0.05,
                optimal_stop_loss_type=StopLossType.FIXED,
                stop_loss_effectiveness=0.5,
                stopped_trades=0,
                avg_stopped_loss=0.0,
                alternative_strategies=[],
                recommendations=["分析失败，建议人工审核"],
            )

    def _analyze_current_stop_loss(self, trades: List[Dict[str, Any]]) -> float:
        """分析当前止损设置

        Args:
            trades: 交易记录

        Returns:
            float: 当前止损比例
        """
        if not trades:
            return 0.05  # 默认5%

        stop_losses = []
        for trade in trades:
            stop_loss = trade.get("stop_loss_pct", trade.get("stop_loss", 0))
            if stop_loss > 0:
                stop_losses.append(stop_loss)

        if stop_losses:
            return np.mean(stop_losses)

        # 从实际亏损交易推断
        losses = []
        for trade in trades:
            pnl_pct = trade.get("pnl_pct", trade.get("return", 0))
            if pnl_pct < 0:
                losses.append(abs(pnl_pct))

        if losses:
            # 使用最大亏损的中位数作为推断的止损位
            return np.median(losses)

        return 0.05

    def _calculate_optimal_stop_loss(self, trades: List[Dict[str, Any]], prices: List[float]) -> tuple:
        """计算最优止损

        Args:
            trades: 交易记录
            prices: 价格序列

        Returns:
            tuple: (最优止损比例, 止损类型)
        """
        if not trades:
            return 0.05, StopLossType.FIXED

        # 测试不同止损水平的效果
        stop_levels = [0.02, 0.03, 0.05, 0.07, 0.10, 0.15]
        best_level = 0.05
        best_score = float("-inf")

        for level in stop_levels:
            score = self._simulate_stop_loss(trades, level)
            if score > best_score:
                best_score = score
                best_level = level

        # 确定最优止损类型
        if prices and len(prices) >= 20:
            atr = self._calculate_atr(prices)
            avg_price = np.mean(prices[-20:])
            atr_pct = atr / avg_price

            # 如果ATR止损效果更好
            if abs(atr_pct * 2 - best_level) < 0.02:
                return atr_pct * 2, StopLossType.ATR

        return best_level, StopLossType.FIXED

    def _simulate_stop_loss(self, trades: List[Dict[str, Any]], stop_level: float) -> float:
        """模拟止损效果

        Args:
            trades: 交易记录
            stop_level: 止损水平

        Returns:
            float: 效果评分
        """
        total_pnl = 0
        stopped_count = 0

        for trade in trades:
            pnl_pct = trade.get("pnl_pct", trade.get("return", 0))
            max_drawdown = trade.get("max_drawdown", abs(min(0, pnl_pct)))

            if max_drawdown >= stop_level:
                # 触发止损
                total_pnl -= stop_level
                stopped_count += 1
            else:
                total_pnl += pnl_pct

        # 评分 = 总收益 - 止损次数惩罚
        score = total_pnl - stopped_count * 0.01
        return score

    def _calculate_atr(self, prices: List[float], period: int = 14) -> float:
        """计算ATR

        Args:
            prices: 价格序列
            period: ATR周期

        Returns:
            float: ATR值
        """
        if len(prices) < period + 1:
            return np.std(prices) if prices else 0

        prices_array = np.array(prices)
        tr = np.abs(np.diff(prices_array))
        atr = np.mean(tr[-period:])
        return atr

    def _evaluate_effectiveness(self, trades: List[Dict[str, Any]]) -> float:
        """评估止损有效性

        Args:
            trades: 交易记录

        Returns:
            float: 有效性评分 0-1
        """
        if not trades:
            return 0.5

        stopped_trades = []
        non_stopped_losses = []

        for trade in trades:
            is_stopped = trade.get("stopped", trade.get("stop_triggered", False))
            pnl_pct = trade.get("pnl_pct", trade.get("return", 0))

            if is_stopped:
                stopped_trades.append(pnl_pct)
            elif pnl_pct < 0:
                non_stopped_losses.append(pnl_pct)

        if not stopped_trades and not non_stopped_losses:
            return 0.5

        # 有效性 = 止损避免的损失 / 总潜在损失
        avg_stopped_loss = np.mean(stopped_trades) if stopped_trades else 0
        avg_non_stopped_loss = np.mean(non_stopped_losses) if non_stopped_losses else 0

        if avg_non_stopped_loss == 0:
            return 0.8 if stopped_trades else 0.5

        # 如果止损后的平均损失小于未止损的平均损失，说明止损有效
        effectiveness = 1 - (abs(avg_stopped_loss) / abs(avg_non_stopped_loss))
        return max(0, min(1, effectiveness))

    def _analyze_stopped_trades(self, trades: List[Dict[str, Any]]) -> tuple:
        """分析止损交易

        Args:
            trades: 交易记录

        Returns:
            tuple: (止损交易数, 平均止损亏损)
        """
        stopped_trades = []

        for trade in trades:
            is_stopped = trade.get("stopped", trade.get("stop_triggered", False))
            if is_stopped:
                pnl = trade.get("pnl", trade.get("profit", 0))
                stopped_trades.append(pnl)

        count = len(stopped_trades)
        avg_loss = np.mean(stopped_trades) if stopped_trades else 0

        return count, round(avg_loss, 2)

    def _generate_alternative_strategies(
        self, trades: List[Dict[str, Any]], prices: List[float], current_stop: float
    ) -> List[Dict[str, Any]]:
        """生成替代止损策略

        Args:
            trades: 交易记录
            prices: 价格序列
            current_stop: 当前止损

        Returns:
            List[Dict[str, Any]]: 替代策略列表
        """
        alternatives = []

        # 固定比例止损
        for level in [0.03, 0.05, 0.08]:
            if abs(level - current_stop) > 0.01:
                score = self._simulate_stop_loss(trades, level)
                alternatives.append(
                    {
                        "type": StopLossType.FIXED.value,
                        "level": level,
                        "description": f"固定{level:.0%}止损",
                        "estimated_score": round(score, 4),
                    }
                )

        # ATR止损
        if prices and len(prices) >= 20:
            atr = self._calculate_atr(prices)
            avg_price = np.mean(prices[-20:])
            atr_pct = atr / avg_price

            for multiplier in [1.5, 2.0, 2.5]:
                level = atr_pct * multiplier
                score = self._simulate_stop_loss(trades, level)
                alternatives.append(
                    {
                        "type": StopLossType.ATR.value,
                        "level": round(level, 4),
                        "multiplier": multiplier,
                        "description": f"{multiplier}倍ATR止损",
                        "estimated_score": round(score, 4),
                    }
                )

        # 追踪止损
        alternatives.append(
            {
                "type": StopLossType.TRAILING.value,
                "level": current_stop,
                "description": f"追踪止损（回撤{current_stop:.0%}触发）",
                "estimated_score": None,
            }
        )

        # 按评分排序
        alternatives.sort(key=lambda x: x.get("estimated_score", float("-inf")) or float("-inf"), reverse=True)

        return alternatives[:5]

    def _generate_recommendations(  # pylint: disable=too-many-positional-arguments
        self, current_stop: float, optimal_stop: float, effectiveness: float, stopped_trades: int, total_trades: int
    ) -> List[str]:
        """生成建议

        Args:
            current_stop: 当前止损
            optimal_stop: 最优止损
            effectiveness: 有效性
            stopped_trades: 止损交易数
            total_trades: 总交易数

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        # 止损水平建议
        if abs(optimal_stop - current_stop) > 0.02:
            if optimal_stop > current_stop:
                recommendations.append(f"建议放宽止损从{current_stop:.1%}到{optimal_stop:.1%}，" f"减少过早止损")
            else:
                recommendations.append(f"建议收紧止损从{current_stop:.1%}到{optimal_stop:.1%}，" f"更好地控制风险")

        # 有效性建议
        if effectiveness < 0.3:
            recommendations.append("当前止损策略效果不佳，建议重新设计止损逻辑")
        elif effectiveness < 0.5:
            recommendations.append("止损策略有改进空间，考虑使用动态止损")

        # 止损频率建议
        if total_trades > 0:
            stop_ratio = stopped_trades / total_trades
            if stop_ratio > 0.3:
                recommendations.append(f"止损触发率过高({stop_ratio:.1%})，" f"建议检查入场信号质量或放宽止损")
            elif stop_ratio < 0.05 and effectiveness < 0.5:
                recommendations.append("止损很少触发但效果不佳，建议收紧止损位")

        # 通用建议
        recommendations.append("建议结合ATR动态调整止损位")
        recommendations.append("考虑使用追踪止损锁定利润")

        return recommendations
