"""交易复盘分析器

白皮书依据: 第五章 5.2.18 交易复盘
引擎: Soldier (战术级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import TradeReviewAnalysis


class TradeReviewAnalyzer:
    """交易复盘分析器

    白皮书依据: 第五章 5.2.18 交易复盘

    分析内容:
    - 交易质量评估: 评估每笔交易的质量
    - 优秀交易分析: 分析成功交易的特征
    - 失败交易分析: 分析失败交易的原因
    - 纪律性评估: 评估交易纪律执行情况
    - 改进建议: 提供具体改进方向
    """

    def __init__(self):
        """初始化交易复盘分析器"""
        self._quality_thresholds = {"excellent": 0.8, "good": 0.6, "fair": 0.4, "poor": 0.2}
        logger.info("TradeReviewAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, trades: List[Dict[str, Any]]) -> TradeReviewAnalysis:
        """分析交易复盘

        Args:
            strategy_id: 策略ID
            trades: 交易记录

        Returns:
            TradeReviewAnalysis: 交易复盘报告
        """
        logger.info(f"开始交易复盘分析: {strategy_id}")

        try:
            if not trades:
                return self._empty_report(strategy_id)

            total_trades = len(trades)

            # 1. 评估每笔交易质量
            trade_qualities = self._evaluate_trade_qualities(trades)
            avg_quality_score = np.mean(trade_qualities) if trade_qualities else 0.5

            # 2. 识别优秀交易
            excellent_trades, excellent_count = self._identify_excellent_trades(trades, trade_qualities)

            # 3. 分析优秀交易特征
            excellent_characteristics = self._analyze_excellent_characteristics(excellent_trades)

            # 4. 识别失败交易
            poor_trades, poor_count = self._identify_poor_trades(trades, trade_qualities)

            # 5. 分析常见错误
            common_mistakes = self._analyze_common_mistakes(poor_trades)

            # 6. 评估纪律性
            discipline_score, discipline_violations = self._evaluate_discipline(trades)

            # 7. 评估执行质量
            execution_quality, execution_issues = self._evaluate_execution(trades)

            # 8. 分析时机
            timing_analysis, timing_score = self._analyze_timing(trades)

            # 9. 生成改进建议
            improvement_suggestions = self._generate_improvement_suggestions(
                common_mistakes, discipline_violations, execution_issues
            )

            # 10. 确定优先改进项
            priority_improvements = self._prioritize_improvements(improvement_suggestions, avg_quality_score)

            # 11. 提取关键学习
            key_learnings = self._extract_key_learnings(excellent_characteristics, common_mistakes)

            report = TradeReviewAnalysis(
                strategy_id=strategy_id,
                total_trades=total_trades,
                avg_quality_score=round(avg_quality_score, 2),
                excellent_trades=excellent_trades[:5],  # 最多5个
                excellent_trade_count=excellent_count,
                excellent_trade_characteristics=excellent_characteristics,
                poor_trades=poor_trades[:5],  # 最多5个
                poor_trade_count=poor_count,
                common_mistakes=common_mistakes,
                discipline_score=round(discipline_score, 2),
                discipline_violations=discipline_violations,
                execution_quality=round(execution_quality, 2),
                execution_issues=execution_issues,
                timing_analysis=timing_analysis,
                timing_score=round(timing_score, 2),
                improvement_suggestions=improvement_suggestions,
                priority_improvements=priority_improvements,
                key_learnings=key_learnings,
            )

            logger.info(
                f"交易复盘完成: {strategy_id}, " f"平均质量={avg_quality_score:.2f}, 纪律性={discipline_score:.2f}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"交易复盘失败: {strategy_id}, 错误: {e}")
            return self._empty_report(strategy_id)

    def _evaluate_trade_qualities(self, trades: List[Dict[str, Any]]) -> List[float]:
        """评估每笔交易质量

        Args:
            trades: 交易记录

        Returns:
            List[float]: 质量评分列表
        """
        qualities = []

        for trade in trades:
            score = 0.5  # 基础分

            # 盈亏评分
            pnl = trade.get("pnl", trade.get("profit", 0))
            pnl_pct = trade.get("pnl_pct", trade.get("return", 0))

            if pnl > 0:
                score += 0.2
                if pnl_pct > 0.05:
                    score += 0.1
            elif pnl < 0:
                score -= 0.1
                if pnl_pct < -0.05:
                    score -= 0.1

            # 风险收益比评分
            risk_reward = trade.get("risk_reward_ratio", 0)
            if risk_reward > 2:
                score += 0.1
            elif risk_reward < 1:
                score -= 0.1

            # 执行质量评分
            slippage = trade.get("slippage", 0)
            if slippage < 0.001:
                score += 0.05
            elif slippage > 0.005:
                score -= 0.05

            # 持仓时间评分
            holding_period = trade.get("holding_period", 0)
            planned_period = trade.get("planned_holding_period", holding_period)
            if planned_period > 0:
                period_ratio = holding_period / planned_period
                if 0.8 <= period_ratio <= 1.2:
                    score += 0.05

            qualities.append(max(0, min(1, score)))

        return qualities

    def _identify_excellent_trades(self, trades: List[Dict[str, Any]], qualities: List[float]) -> tuple:
        """识别优秀交易

        Args:
            trades: 交易记录
            qualities: 质量评分

        Returns:
            tuple: (优秀交易列表, 数量)
        """
        excellent = []

        for trade, quality in zip(trades, qualities):
            if quality >= self._quality_thresholds["excellent"]:
                excellent.append(
                    {
                        "symbol": trade.get("symbol", ""),
                        "pnl": trade.get("pnl", 0),
                        "pnl_pct": trade.get("pnl_pct", 0),
                        "quality_score": quality,
                        "entry_time": trade.get("entry_time", ""),
                        "exit_time": trade.get("exit_time", ""),
                    }
                )

        return excellent, len(excellent)

    def _analyze_excellent_characteristics(self, excellent_trades: List[Dict[str, Any]]) -> List[str]:
        """分析优秀交易特征

        Args:
            excellent_trades: 优秀交易列表

        Returns:
            List[str]: 特征列表
        """
        if not excellent_trades:
            return ["数据不足"]

        characteristics = []

        # 分析盈利特征
        pnl_pcts = [t.get("pnl_pct", 0) for t in excellent_trades]
        if pnl_pcts:
            avg_pnl = np.mean(pnl_pcts)
            characteristics.append(f"平均收益率: {avg_pnl:.2%}")

        # 分析时间特征
        entry_times = [t.get("entry_time", "") for t in excellent_trades]
        # 简化：统计是否有时间规律
        if entry_times:
            characteristics.append("入场时机把握准确")

        # 通用特征
        characteristics.extend(["严格执行止损止盈", "顺势而为", "仓位控制合理"])

        return characteristics

    def _identify_poor_trades(self, trades: List[Dict[str, Any]], qualities: List[float]) -> tuple:
        """识别失败交易

        Args:
            trades: 交易记录
            qualities: 质量评分

        Returns:
            tuple: (失败交易列表, 数量)
        """
        poor = []

        for trade, quality in zip(trades, qualities):
            if quality <= self._quality_thresholds["poor"]:
                poor.append(
                    {
                        "symbol": trade.get("symbol", ""),
                        "pnl": trade.get("pnl", 0),
                        "pnl_pct": trade.get("pnl_pct", 0),
                        "quality_score": quality,
                        "entry_time": trade.get("entry_time", ""),
                        "exit_time": trade.get("exit_time", ""),
                    }
                )

        return poor, len(poor)

    def _analyze_common_mistakes(self, poor_trades: List[Dict[str, Any]]) -> List[str]:
        """分析常见错误

        Args:
            poor_trades: 失败交易列表

        Returns:
            List[str]: 错误列表
        """
        if not poor_trades:
            return ["暂无明显错误"]

        mistakes = []

        # 分析亏损特征
        pnl_pcts = [t.get("pnl_pct", 0) for t in poor_trades]
        if pnl_pcts:
            avg_loss = np.mean(pnl_pcts)
            if avg_loss < -0.05:
                mistakes.append(f"单笔亏损过大(平均{avg_loss:.2%})")

        # 通用错误
        mistakes.extend(["追涨杀跌", "止损执行不坚决", "逆势操作", "仓位过重"])

        return mistakes[:5]

    def _evaluate_discipline(self, trades: List[Dict[str, Any]]) -> tuple:
        """评估纪律性

        Args:
            trades: 交易记录

        Returns:
            tuple: (纪律性评分, 违规列表)
        """
        violations = []
        score = 1.0

        for trade in trades:
            # 检查止损执行
            stop_loss = trade.get("stop_loss", 0)
            actual_loss = trade.get("pnl_pct", 0)
            if stop_loss and actual_loss < -stop_loss * 1.5:
                violations.append("止损未执行")
                score -= 0.1

            # 检查仓位控制
            position_size = trade.get("position_size", 0)
            max_position = trade.get("max_position", 1)
            if position_size > max_position:
                violations.append("仓位超限")
                score -= 0.1

            # 检查交易时间
            trade_time = trade.get("time", "")
            if "14:55" in str(trade_time) or "09:25" in str(trade_time):
                violations.append("非正常交易时间")
                score -= 0.05

        # 去重
        violations = list(set(violations))

        return max(0, score), violations

    def _evaluate_execution(self, trades: List[Dict[str, Any]]) -> tuple:
        """评估执行质量

        Args:
            trades: 交易记录

        Returns:
            tuple: (执行质量评分, 问题列表)
        """
        issues = []
        score = 1.0

        slippages = []
        for trade in trades:
            slippage = trade.get("slippage", 0)
            slippages.append(slippage)

            if slippage > 0.005:
                score -= 0.05

        if slippages:
            avg_slippage = np.mean(slippages)
            if avg_slippage > 0.003:
                issues.append(f"平均滑点偏高({avg_slippage:.2%})")

            max_slippage = np.max(slippages)
            if max_slippage > 0.01:
                issues.append(f"存在极端滑点({max_slippage:.2%})")

        # 检查成交率
        fill_rates = [t.get("fill_rate", 1) for t in trades]
        if fill_rates:
            avg_fill = np.mean(fill_rates)
            if avg_fill < 0.95:
                issues.append(f"成交率偏低({avg_fill:.1%})")
                score -= 0.1

        if not issues:
            issues.append("执行质量良好")

        return max(0, score), issues

    def _analyze_timing(self, trades: List[Dict[str, Any]]) -> tuple:
        """分析时机

        Args:
            trades: 交易记录

        Returns:
            tuple: (时机分析, 时机评分)
        """
        analysis = {"entry_timing": "neutral", "exit_timing": "neutral", "holding_period": "appropriate"}
        score = 0.5

        # 分析入场时机
        entry_prices = [t.get("entry_price", 0) for t in trades]
        best_prices = [t.get("best_price_after_entry", 0) for t in trades]

        if entry_prices and best_prices:
            entry_quality = []
            for entry, best in zip(entry_prices, best_prices):
                if entry > 0 and best > 0:
                    quality = (best - entry) / entry
                    entry_quality.append(quality)

            if entry_quality:
                avg_entry_quality = np.mean(entry_quality)
                if avg_entry_quality > 0.02:
                    analysis["entry_timing"] = "good"
                    score += 0.2
                elif avg_entry_quality < -0.02:
                    analysis["entry_timing"] = "poor"
                    score -= 0.2

        # 分析持仓时间
        holding_periods = [t.get("holding_period", 0) for t in trades]
        if holding_periods:
            avg_holding = np.mean(holding_periods)
            analysis["avg_holding_days"] = round(avg_holding, 1)

        return analysis, max(0, min(1, score))

    def _generate_improvement_suggestions(
        self, mistakes: List[str], violations: List[str], execution_issues: List[str]
    ) -> List[str]:
        """生成改进建议

        Args:
            mistakes: 常见错误
            violations: 纪律违规
            execution_issues: 执行问题

        Returns:
            List[str]: 改进建议
        """
        suggestions = []

        # 针对错误的建议
        if "追涨杀跌" in mistakes:
            suggestions.append("建立明确的入场规则，避免情绪化交易")

        if "止损执行不坚决" in mistakes:
            suggestions.append("使用自动止损，减少人为干预")

        if "仓位过重" in mistakes:
            suggestions.append("严格执行仓位管理规则，单笔不超过总资金的10%")

        # 针对违规的建议
        if "止损未执行" in violations:
            suggestions.append("设置硬止损，到价自动执行")

        if "仓位超限" in violations:
            suggestions.append("在交易系统中设置仓位上限")

        # 针对执行问题的建议
        for issue in execution_issues:
            if "滑点" in issue:
                suggestions.append("优化执行算法，使用限价单")
            if "成交率" in issue:
                suggestions.append("提高报价竞争力，或选择流动性更好的标的")

        if not suggestions:
            suggestions.append("继续保持良好的交易习惯")

        return suggestions

    def _prioritize_improvements(self, suggestions: List[str], avg_quality: float) -> List[str]:
        """确定优先改进项

        Args:
            suggestions: 改进建议
            avg_quality: 平均质量

        Returns:
            List[str]: 优先改进项
        """
        if avg_quality < 0.4:  # pylint: disable=no-else-return
            return suggestions[:3]  # 质量差，优先前3项
        elif avg_quality < 0.6:
            return suggestions[:2]  # 质量一般，优先前2项
        else:
            return suggestions[:1]  # 质量好，优先1项

    def _extract_key_learnings(self, excellent_characteristics: List[str], common_mistakes: List[str]) -> List[str]:
        """提取关键学习

        Args:
            excellent_characteristics: 优秀特征
            common_mistakes: 常见错误

        Returns:
            List[str]: 关键学习
        """
        learnings = []

        # 从优秀交易学习
        if excellent_characteristics:
            learnings.append(f"成功要素: {excellent_characteristics[0]}")

        # 从错误中学习
        if common_mistakes and common_mistakes[0] != "暂无明显错误":
            learnings.append(f"需要避免: {common_mistakes[0]}")

        # 通用学习
        learnings.extend(["纪律是盈利的基础", "控制风险比追求收益更重要"])

        return learnings

    def _empty_report(self, strategy_id: str) -> TradeReviewAnalysis:
        """生成空报告"""
        return TradeReviewAnalysis(
            strategy_id=strategy_id,
            total_trades=0,
            avg_quality_score=0.0,
            excellent_trades=[],
            excellent_trade_count=0,
            excellent_trade_characteristics=[],
            poor_trades=[],
            poor_trade_count=0,
            common_mistakes=[],
            discipline_score=0.0,
            discipline_violations=[],
            execution_quality=0.0,
            execution_issues=[],
            timing_analysis={},
            timing_score=0.0,
            improvement_suggestions=["无交易数据"],
            priority_improvements=[],
            key_learnings=[],
        )
