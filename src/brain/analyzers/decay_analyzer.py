"""策略衰减分析器

白皮书依据: 第五章 5.2.11 策略衰减分析
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import DecayAnalysis, DecayStage, DecayTrend


class DecayAnalyzer:
    """策略衰减分析器

    白皮书依据: 第五章 5.2.11 策略衰减分析

    分析内容:
    - 收益率衰减: 策略收益随时间的变化
    - 夏普比率衰减: 风险调整收益的变化
    - 胜率衰减: 交易胜率的变化
    - 生命周期预测: 预计策略有效期
    - 更新紧迫度: 策略更新的优先级
    """

    def __init__(self):
        """初始化衰减分析器"""
        self._min_periods = 60  # 最少需要60个周期的数据
        self._decay_threshold = 0.1  # 10%衰减阈值
        logger.info("DecayAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, performance_data: Dict[str, Any]) -> DecayAnalysis:
        """分析策略衰减

        Args:
            strategy_id: 策略ID
            performance_data: 性能数据，包含returns, sharpe_history, win_rates等

        Returns:
            DecayAnalysis: 衰减分析报告
        """
        logger.info(f"开始策略衰减分析: {strategy_id}")

        try:
            returns = performance_data.get("returns", [])
            sharpe_history = performance_data.get("sharpe_history", [])
            win_rates = performance_data.get("win_rates", [])
            performance_data.get("start_date")

            # 1. 计算收益率衰减率
            return_decay_rate = self._calculate_return_decay_rate(returns)

            # 2. 计算夏普比率衰减率
            sharpe_decay_rate = self._calculate_sharpe_decay_rate(sharpe_history, returns)

            # 3. 计算胜率衰减率
            win_rate_decay_rate = self._calculate_win_rate_decay_rate(win_rates)

            # 4. 确定衰减趋势
            decay_trend = self._determine_decay_trend(return_decay_rate, sharpe_decay_rate, win_rate_decay_rate)

            # 5. 估算生命周期
            estimated_lifetime = self._estimate_lifetime(return_decay_rate, sharpe_decay_rate, returns)

            # 6. 确定衰减阶段
            decay_stage = self._determine_decay_stage(return_decay_rate, sharpe_decay_rate, estimated_lifetime)

            # 7. 确定更新紧迫度
            update_urgency = self._determine_update_urgency(decay_stage, decay_trend, estimated_lifetime)

            # 8. 识别衰减因素
            decay_factors = self._identify_decay_factors(returns, sharpe_history, win_rates)

            # 9. 生成更新建议
            update_recommendations = self._generate_update_recommendations(decay_stage, decay_factors, update_urgency)

            report = DecayAnalysis(
                strategy_id=strategy_id,
                return_decay_rate=round(return_decay_rate * 100, 2),
                sharpe_decay_rate=round(sharpe_decay_rate * 100, 2),
                win_rate_decay_rate=round(win_rate_decay_rate * 100, 2),
                decay_trend=decay_trend,
                estimated_lifetime=estimated_lifetime,
                decay_stage=decay_stage,
                update_urgency=update_urgency,
                decay_factors=decay_factors,
                update_recommendations=update_recommendations,
            )

            logger.info(f"衰减分析完成: {strategy_id}, " f"阶段={decay_stage.value}, 紧迫度={update_urgency}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"衰减分析失败: {strategy_id}, 错误: {e}")
            return DecayAnalysis(
                strategy_id=strategy_id,
                return_decay_rate=0.0,
                sharpe_decay_rate=0.0,
                win_rate_decay_rate=0.0,
                decay_trend=DecayTrend.STABLE,
                estimated_lifetime=365,
                decay_stage=DecayStage.EARLY,
                update_urgency="low",
                decay_factors=["分析失败"],
                update_recommendations=["建议人工审核"],
            )

    def _calculate_return_decay_rate(self, returns: List[float]) -> float:
        """计算收益率衰减率

        Args:
            returns: 收益率序列

        Returns:
            float: 年化衰减率
        """
        if not returns or len(returns) < self._min_periods:
            return 0.0

        returns_array = np.array(returns)
        n = len(returns_array)

        # 分成前后两半比较
        first_half = returns_array[: n // 2]
        second_half = returns_array[n // 2 :]

        first_mean = np.mean(first_half)
        second_mean = np.mean(second_half)

        if first_mean == 0:
            return 0.0

        # 计算衰减率
        decay_rate = (first_mean - second_mean) / abs(first_mean)

        # 年化（假设数据是日频）
        periods_per_year = 252
        actual_periods = n / 2
        annualized_decay = decay_rate * (periods_per_year / actual_periods)

        return max(0, annualized_decay)  # 只返回正衰减

    def _calculate_sharpe_decay_rate(self, sharpe_history: List[float], returns: List[float]) -> float:
        """计算夏普比率衰减率

        Args:
            sharpe_history: 夏普比率历史
            returns: 收益率序列

        Returns:
            float: 年化衰减率
        """
        # 如果有夏普历史数据
        if sharpe_history and len(sharpe_history) >= 10:
            sharpe_array = np.array(sharpe_history)
            n = len(sharpe_array)

            first_half = sharpe_array[: n // 2]
            second_half = sharpe_array[n // 2 :]

            first_mean = np.mean(first_half)
            second_mean = np.mean(second_half)

            if first_mean == 0:
                return 0.0

            decay_rate = (first_mean - second_mean) / abs(first_mean)
            return max(0, decay_rate)

        # 否则从收益率计算滚动夏普
        if not returns or len(returns) < self._min_periods:
            return 0.0

        returns_array = np.array(returns)
        window = 60

        rolling_sharpes = []
        for i in range(window, len(returns_array)):
            window_returns = returns_array[i - window : i]
            if np.std(window_returns) > 0:
                sharpe = np.mean(window_returns) / np.std(window_returns) * np.sqrt(252)
                rolling_sharpes.append(sharpe)

        if len(rolling_sharpes) < 10:
            return 0.0

        sharpe_array = np.array(rolling_sharpes)
        n = len(sharpe_array)

        first_half = sharpe_array[: n // 2]
        second_half = sharpe_array[n // 2 :]

        first_mean = np.mean(first_half)
        second_mean = np.mean(second_half)

        if first_mean == 0:
            return 0.0

        decay_rate = (first_mean - second_mean) / abs(first_mean)
        return max(0, decay_rate)

    def _calculate_win_rate_decay_rate(self, win_rates: List[float]) -> float:
        """计算胜率衰减率

        Args:
            win_rates: 胜率序列

        Returns:
            float: 年化衰减率
        """
        if not win_rates or len(win_rates) < 10:
            return 0.0

        win_array = np.array(win_rates)
        n = len(win_array)

        first_half = win_array[: n // 2]
        second_half = win_array[n // 2 :]

        first_mean = np.mean(first_half)
        second_mean = np.mean(second_half)

        if first_mean == 0:
            return 0.0

        decay_rate = (first_mean - second_mean) / first_mean
        return max(0, decay_rate)

    def _determine_decay_trend(self, return_decay: float, sharpe_decay: float, win_rate_decay: float) -> DecayTrend:
        """确定衰减趋势

        Args:
            return_decay: 收益衰减率
            sharpe_decay: 夏普衰减率
            win_rate_decay: 胜率衰减率

        Returns:
            DecayTrend: 衰减趋势
        """
        avg_decay = (return_decay + sharpe_decay + win_rate_decay) / 3

        if avg_decay < 0.05:  # pylint: disable=no-else-return
            return DecayTrend.STABLE
        elif avg_decay < 0.15:
            return DecayTrend.DECLINING
        else:
            return DecayTrend.ACCELERATING_DECLINE

    def _estimate_lifetime(self, return_decay: float, sharpe_decay: float, returns: List[float]) -> int:
        """估算生命周期

        Args:
            return_decay: 收益衰减率
            sharpe_decay: 夏普衰减率
            returns: 收益率序列

        Returns:
            int: 预计剩余生命周期（天）
        """
        if return_decay <= 0 and sharpe_decay <= 0:
            return 365 * 3  # 无衰减，预计3年

        avg_decay = (return_decay + sharpe_decay) / 2

        if avg_decay <= 0:
            return 365 * 2

        # 假设策略在收益降到0时失效
        # 当前收益水平
        if returns and len(returns) > 60:
            current_return = np.mean(returns[-60:])
            if current_return > 0:
                # 预计多少年后收益降到0
                years_to_zero = current_return / (current_return * avg_decay)
                return int(min(365 * 3, max(30, years_to_zero * 365)))

        # 默认根据衰减率估算
        if avg_decay > 0.3:  # pylint: disable=no-else-return
            return 90  # 3个月
        elif avg_decay > 0.2:
            return 180  # 6个月
        elif avg_decay > 0.1:
            return 365  # 1年
        else:
            return 365 * 2  # 2年

    def _determine_decay_stage(self, return_decay: float, sharpe_decay: float, estimated_lifetime: int) -> DecayStage:
        """确定衰减阶段

        Args:
            return_decay: 收益衰减率
            sharpe_decay: 夏普衰减率
            estimated_lifetime: 预计生命周期

        Returns:
            DecayStage: 衰减阶段
        """
        avg_decay = (return_decay + sharpe_decay) / 2

        if estimated_lifetime < 60:  # pylint: disable=no-else-return
            return DecayStage.CRITICAL
        elif estimated_lifetime < 180 or avg_decay > 0.25:
            return DecayStage.LATE
        elif estimated_lifetime < 365 or avg_decay > 0.15:
            return DecayStage.MIDDLE
        else:
            return DecayStage.EARLY

    def _determine_update_urgency(
        self,
        decay_stage: DecayStage,
        decay_trend: DecayTrend,
        estimated_lifetime: int,  # pylint: disable=unused-argument
    ) -> str:
        """确定更新紧迫度

        Args:
            decay_stage: 衰减阶段
            decay_trend: 衰减趋势
            estimated_lifetime: 预计生命周期

        Returns:
            str: 更新紧迫度
        """
        if decay_stage == DecayStage.CRITICAL:  # pylint: disable=no-else-return
            return "critical"
        elif decay_stage == DecayStage.LATE:
            if decay_trend == DecayTrend.ACCELERATING_DECLINE:
                return "critical"
            return "high"
        elif decay_stage == DecayStage.MIDDLE:
            if decay_trend == DecayTrend.ACCELERATING_DECLINE:
                return "high"
            return "medium"
        else:
            if decay_trend == DecayTrend.ACCELERATING_DECLINE:
                return "medium"
            return "low"

    def _identify_decay_factors(
        self,
        returns: List[float],
        sharpe_history: List[float],  # pylint: disable=unused-argument
        win_rates: List[float],  # pylint: disable=unused-argument
    ) -> List[str]:
        """识别衰减因素

        Args:
            returns: 收益率序列
            sharpe_history: 夏普历史
            win_rates: 胜率序列

        Returns:
            List[str]: 衰减因素列表
        """
        factors = []

        if returns and len(returns) >= self._min_periods:
            returns_array = np.array(returns)

            # 检查收益波动性变化
            first_vol = np.std(returns_array[: len(returns_array) // 2])
            second_vol = np.std(returns_array[len(returns_array) // 2 :])
            if second_vol > first_vol * 1.5:
                factors.append("收益波动性显著增加")

            # 检查负收益频率
            first_neg_ratio = np.sum(returns_array[: len(returns_array) // 2] < 0) / (len(returns_array) // 2)
            second_neg_ratio = np.sum(returns_array[len(returns_array) // 2 :] < 0) / (len(returns_array) // 2)
            if second_neg_ratio > first_neg_ratio * 1.3:
                factors.append("负收益交易频率增加")

        if win_rates and len(win_rates) >= 10:
            win_array = np.array(win_rates)
            if np.mean(win_array[-5:]) < np.mean(win_array[:5]) * 0.9:
                factors.append("近期胜率下降")

        # 通用因素
        factors.extend(["市场环境变化", "策略逻辑被市场学习", "参数失效"])

        return factors[:5]

    def _generate_update_recommendations(
        self, decay_stage: DecayStage, decay_factors: List[str], update_urgency: str  # pylint: disable=unused-argument
    ) -> List[str]:
        """生成更新建议

        Args:
            decay_stage: 衰减阶段
            decay_factors: 衰减因素
            update_urgency: 更新紧迫度

        Returns:
            List[str]: 更新建议列表
        """
        recommendations = []

        if update_urgency == "critical":
            recommendations.append("【紧急】立即停止策略运行，进行全面审查")
            recommendations.append("考虑使用备用策略替代")
        elif update_urgency == "high":
            recommendations.append("【高优先级】尽快进行策略参数优化")
            recommendations.append("减少策略资金配置")
        elif update_urgency == "medium":
            recommendations.append("【中优先级】计划进行策略更新")
            recommendations.append("监控策略表现，准备备选方案")
        else:
            recommendations.append("【低优先级】定期监控即可")

        # 根据衰减因素给出具体建议
        if "收益波动性显著增加" in decay_factors:
            recommendations.append("考虑增加波动率过滤条件")

        if "负收益交易频率增加" in decay_factors:
            recommendations.append("优化入场信号，提高信号质量")

        if "近期胜率下降" in decay_factors:
            recommendations.append("检查市场环境是否发生变化")

        recommendations.append("建议进行Walk-Forward优化")

        return recommendations
