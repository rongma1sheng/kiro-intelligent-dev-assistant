"""信噪比分析器

白皮书依据: 第五章 5.2.15 信噪比分析
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import SignalNoiseAnalysis, SNRQuality


class SignalNoiseAnalyzer:
    """信噪比分析器

    白皮书依据: 第五章 5.2.15 信噪比分析

    分析内容:
    - 信号强度: 策略信号的强度
    - 信号一致性: 信号的稳定程度
    - 噪声水平: 市场噪声的影响
    - 信噪比: 信号与噪声的比值
    - 改进建议: 提高信噪比的方法
    """

    def __init__(self):
        """初始化信噪比分析器"""
        self._snr_thresholds = {"excellent": 3.0, "good": 2.0, "fair": 1.0, "poor": 0.0}
        logger.info("SignalNoiseAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> SignalNoiseAnalysis:
        """分析信噪比

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            SignalNoiseAnalysis: 信噪比分析报告
        """
        logger.info(f"开始信噪比分析: {strategy_id}")

        try:
            signals = strategy_data.get("signals", [])
            returns = strategy_data.get("returns", [])
            predictions = strategy_data.get("predictions", [])
            actuals = strategy_data.get("actuals", returns)

            # 1. 计算信号强度
            signal_strength = self._calculate_signal_strength(signals, returns)

            # 2. 计算信号一致性
            signal_consistency = self._calculate_signal_consistency(signals)

            # 3. 计算信号清晰度
            signal_clarity = self._calculate_signal_clarity(predictions, actuals)

            # 4. 计算噪声水平
            noise_level = self._calculate_noise_level(returns, signals)

            # 5. 计算信噪比
            signal_to_noise_ratio = self._calculate_snr(signal_strength, noise_level)

            # 6. 确定信噪比质量
            snr_quality = self._determine_snr_quality(signal_to_noise_ratio)

            # 7. 计算整体质量
            overall_quality = self._calculate_overall_quality(
                signal_strength, signal_consistency, signal_clarity, noise_level
            )

            # 8. 计算时间稳定性
            temporal_stability = self._calculate_temporal_stability(signals, returns)

            # 9. 识别噪声来源
            noise_sources = self._identify_noise_sources(returns, signals, noise_level)

            # 10. 生成改进建议
            improvement_suggestions = self._generate_suggestions(
                signal_strength, signal_consistency, noise_level, snr_quality, noise_sources
            )

            # 11. 估算改进空间
            expected_improvement = self._estimate_improvement(overall_quality, noise_sources)

            report = SignalNoiseAnalysis(
                strategy_id=strategy_id,
                signal_strength=round(signal_strength, 2),
                signal_consistency=round(signal_consistency, 2),
                signal_clarity=round(signal_clarity, 2),
                noise_level=round(noise_level, 2),
                signal_to_noise_ratio=round(signal_to_noise_ratio, 2),
                snr_quality=snr_quality,
                overall_quality=round(overall_quality, 2),
                temporal_stability=round(temporal_stability, 2),
                noise_sources=noise_sources,
                improvement_suggestions=improvement_suggestions,
                expected_improvement=round(expected_improvement, 2),
            )

            logger.info(f"信噪比分析完成: {strategy_id}, " f"SNR={signal_to_noise_ratio:.2f}, 质量={snr_quality.value}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"信噪比分析失败: {strategy_id}, 错误: {e}")
            return SignalNoiseAnalysis(
                strategy_id=strategy_id,
                signal_strength=0.5,
                signal_consistency=0.5,
                signal_clarity=0.5,
                noise_level=0.5,
                signal_to_noise_ratio=1.0,
                snr_quality=SNRQuality.FAIR,
                overall_quality=0.5,
                temporal_stability=0.5,
                noise_sources=["分析失败"],
                improvement_suggestions=["建议人工审核"],
                expected_improvement=0.0,
            )

    def _calculate_signal_strength(self, signals: List[float], returns: List[float]) -> float:
        """计算信号强度

        Args:
            signals: 信号序列
            returns: 收益率序列

        Returns:
            float: 信号强度 0-1
        """
        if not signals or not returns:
            return 0.5

        signals_array = np.array(signals)
        returns_array = np.array(returns)

        # 确保长度一致
        min_len = min(len(signals_array), len(returns_array))
        signals_array = signals_array[:min_len]
        returns_array = returns_array[:min_len]

        # 信号强度 = 信号与收益的相关性
        if np.std(signals_array) > 0 and np.std(returns_array) > 0:
            correlation = np.corrcoef(signals_array, returns_array)[0, 1]
            strength = abs(correlation)
        else:
            strength = 0.5

        return strength

    def _calculate_signal_consistency(self, signals: List[float]) -> float:
        """计算信号一致性

        Args:
            signals: 信号序列

        Returns:
            float: 一致性 0-1
        """
        if not signals or len(signals) < 10:
            return 0.5

        signals_array = np.array(signals)

        # 计算信号的自相关性
        if len(signals_array) > 1:
            autocorr = np.corrcoef(signals_array[:-1], signals_array[1:])[0, 1]
            if np.isnan(autocorr):
                autocorr = 0
        else:
            autocorr = 0

        # 计算信号的稳定性（变异系数的倒数）
        if np.mean(np.abs(signals_array)) > 0:
            cv = np.std(signals_array) / np.mean(np.abs(signals_array))
            stability = 1 / (1 + cv)
        else:
            stability = 0.5

        # 综合一致性
        consistency = (abs(autocorr) + stability) / 2

        return consistency

    def _calculate_signal_clarity(self, predictions: List[float], actuals: List[float]) -> float:
        """计算信号清晰度

        Args:
            predictions: 预测值
            actuals: 实际值

        Returns:
            float: 清晰度 0-1
        """
        if not predictions or not actuals:
            return 0.5

        predictions_array = np.array(predictions)
        actuals_array = np.array(actuals)

        min_len = min(len(predictions_array), len(actuals_array))
        predictions_array = predictions_array[:min_len]
        actuals_array = actuals_array[:min_len]

        # 方向准确率
        if len(predictions_array) > 0:
            direction_correct = np.sum(np.sign(predictions_array) == np.sign(actuals_array)) / len(predictions_array)
        else:
            direction_correct = 0.5

        # 幅度准确率
        if np.std(actuals_array) > 0:
            mse = np.mean((predictions_array - actuals_array) ** 2)
            rmse = np.sqrt(mse)
            magnitude_accuracy = 1 / (1 + rmse / np.std(actuals_array))
        else:
            magnitude_accuracy = 0.5

        clarity = direction_correct * 0.6 + magnitude_accuracy * 0.4

        return clarity

    def _calculate_noise_level(self, returns: List[float], signals: List[float]) -> float:
        """计算噪声水平

        Args:
            returns: 收益率序列
            signals: 信号序列

        Returns:
            float: 噪声水平 0-1
        """
        if not returns:
            return 0.5

        returns_array = np.array(returns)

        # 基于收益率的波动性估算噪声
        volatility = np.std(returns_array)

        # 如果有信号，计算残差噪声
        if signals and len(signals) == len(returns):
            signals_array = np.array(signals)

            # 简单线性回归
            if np.std(signals_array) > 0:
                beta = np.cov(signals_array, returns_array)[0, 1] / np.var(signals_array)
                alpha = np.mean(returns_array) - beta * np.mean(signals_array)
                predicted = alpha + beta * signals_array
                residuals = returns_array - predicted
                noise = np.std(residuals)
            else:
                noise = volatility
        else:
            noise = volatility

        # 归一化噪声水平
        noise_level = min(1.0, noise / (volatility + 1e-10))

        return noise_level

    def _calculate_snr(self, signal_strength: float, noise_level: float) -> float:
        """计算信噪比

        Args:
            signal_strength: 信号强度
            noise_level: 噪声水平

        Returns:
            float: 信噪比
        """
        if noise_level <= 0:
            return 10.0  # 最大值

        snr = signal_strength / noise_level
        return min(10.0, snr)

    def _determine_snr_quality(self, snr: float) -> SNRQuality:
        """确定信噪比质量

        Args:
            snr: 信噪比

        Returns:
            SNRQuality: 质量等级
        """
        if snr >= self._snr_thresholds["excellent"]:  # pylint: disable=no-else-return
            return SNRQuality.EXCELLENT
        elif snr >= self._snr_thresholds["good"]:
            return SNRQuality.GOOD
        elif snr >= self._snr_thresholds["fair"]:
            return SNRQuality.FAIR
        else:
            return SNRQuality.POOR

    def _calculate_overall_quality(
        self, signal_strength: float, signal_consistency: float, signal_clarity: float, noise_level: float
    ) -> float:
        """计算整体质量

        Args:
            signal_strength: 信号强度
            signal_consistency: 信号一致性
            signal_clarity: 信号清晰度
            noise_level: 噪声水平

        Returns:
            float: 整体质量 0-1
        """
        # 加权平均
        quality = signal_strength * 0.3 + signal_consistency * 0.2 + signal_clarity * 0.3 + (1 - noise_level) * 0.2

        return quality

    def _calculate_temporal_stability(self, signals: List[float], returns: List[float]) -> float:
        """计算时间稳定性

        Args:
            signals: 信号序列
            returns: 收益率序列

        Returns:
            float: 时间稳定性 0-1
        """
        if not signals or not returns or len(signals) < 60:
            return 0.5

        signals_array = np.array(signals)
        returns_array = np.array(returns)

        min_len = min(len(signals_array), len(returns_array))
        signals_array = signals_array[:min_len]
        returns_array = returns_array[:min_len]

        # 计算滚动相关性
        window = 20
        rolling_corrs = []

        for i in range(window, min_len):
            window_signals = signals_array[i - window : i]
            window_returns = returns_array[i - window : i]

            if np.std(window_signals) > 0 and np.std(window_returns) > 0:
                corr = np.corrcoef(window_signals, window_returns)[0, 1]
                if not np.isnan(corr):
                    rolling_corrs.append(corr)

        if not rolling_corrs:
            return 0.5

        # 稳定性 = 1 - 相关性的变异系数
        corr_array = np.array(rolling_corrs)
        if np.mean(np.abs(corr_array)) > 0:
            cv = np.std(corr_array) / np.mean(np.abs(corr_array))
            stability = 1 / (1 + cv)
        else:
            stability = 0.5

        return stability

    def _identify_noise_sources(self, returns: List[float], signals: List[float], noise_level: float) -> List[str]:
        """识别噪声来源

        Args:
            returns: 收益率序列
            signals: 信号序列
            noise_level: 噪声水平

        Returns:
            List[str]: 噪声来源列表
        """
        sources = []

        if not returns:
            return ["数据不足"]

        returns_array = np.array(returns)

        # 高波动性
        volatility = np.std(returns_array) * np.sqrt(252)
        if volatility > 0.3:
            sources.append("市场高波动性")

        # 异常值
        z_scores = np.abs((returns_array - np.mean(returns_array)) / np.std(returns_array))
        outlier_ratio = np.sum(z_scores > 3) / len(returns_array)
        if outlier_ratio > 0.02:
            sources.append("异常值/极端事件")

        # 信号质量
        if signals and len(signals) == len(returns):
            signals_array = np.array(signals)
            if np.std(signals_array) > 0:
                corr = np.corrcoef(signals_array, returns_array)[0, 1]
                if abs(corr) < 0.1:
                    sources.append("信号与收益相关性低")

        # 噪声水平高
        if noise_level > 0.7:
            sources.append("整体噪声水平过高")

        # 市场微观结构
        if len(returns_array) > 20:
            autocorr = np.corrcoef(returns_array[:-1], returns_array[1:])[0, 1]
            if abs(autocorr) > 0.2:
                sources.append("市场微观结构噪声")

        if not sources:
            sources.append("噪声来源不明显")

        return sources

    def _generate_suggestions(  # pylint: disable=too-many-positional-arguments
        self,
        signal_strength: float,
        signal_consistency: float,
        noise_level: float,
        snr_quality: SNRQuality,
        noise_sources: List[str],
    ) -> List[str]:
        """生成改进建议

        Args:
            signal_strength: 信号强度
            signal_consistency: 信号一致性
            noise_level: 噪声水平
            snr_quality: 信噪比质量
            noise_sources: 噪声来源

        Returns:
            List[str]: 建议列表
        """
        suggestions = []

        # 信号强度建议
        if signal_strength < 0.3:
            suggestions.append("信号强度较弱，建议优化信号生成逻辑")
            suggestions.append("考虑增加更多有效特征")

        # 信号一致性建议
        if signal_consistency < 0.4:
            suggestions.append("信号一致性差，建议增加信号平滑处理")
            suggestions.append("考虑使用多信号确认机制")

        # 噪声水平建议
        if noise_level > 0.6:
            suggestions.append("噪声水平高，建议增加数据过滤")
            suggestions.append("考虑使用更长的回看期")

        # 针对噪声来源的建议
        if "市场高波动性" in noise_sources:
            suggestions.append("在高波动期减少交易或使用波动率过滤")

        if "异常值/极端事件" in noise_sources:
            suggestions.append("增加异常值检测和处理机制")

        if "信号与收益相关性低" in noise_sources:
            suggestions.append("重新评估信号的有效性，考虑更换信号源")

        # 通用建议
        if snr_quality in [SNRQuality.POOR, SNRQuality.FAIR]:
            suggestions.append("整体信噪比较低，建议全面优化策略")

        suggestions.append("考虑使用集成方法提高信号质量")

        return suggestions

    def _estimate_improvement(self, overall_quality: float, noise_sources: List[str]) -> float:
        """估算改进空间

        Args:
            overall_quality: 整体质量
            noise_sources: 噪声来源

        Returns:
            float: 预期改进 0-1
        """
        # 基于当前质量估算改进空间
        improvement_potential = 1 - overall_quality

        # 根据噪声来源调整
        addressable_sources = ["信号与收益相关性低", "异常值/极端事件", "整体噪声水平过高"]

        addressable_count = sum(1 for s in noise_sources if s in addressable_sources)

        # 可解决的噪声源越多，改进空间越大
        improvement = improvement_potential * (0.5 + 0.1 * addressable_count)

        return min(0.5, improvement)  # 最多50%改进
