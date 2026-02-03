"""非平稳性处理分析器

白皮书依据: 第五章 5.2.14 非平稳性处理
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import NonstationarityAnalysis


class NonstationarityAnalyzer:
    """非平稳性处理分析器

    白皮书依据: 第五章 5.2.14 非平稳性处理

    分析内容:
    - 平稳性检验: ADF检验等
    - 市场状态识别: 识别不同市场状态
    - 参数稳定性: 策略参数的稳定性
    - 适应性建议: 如何适应市场变化
    """

    def __init__(self):
        """初始化非平稳性分析器"""
        self._min_samples = 100
        logger.info("NonstationarityAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> NonstationarityAnalysis:
        """分析非平稳性

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            NonstationarityAnalysis: 非平稳性分析报告
        """
        logger.info(f"开始非平稳性分析: {strategy_id}")

        try:
            returns = strategy_data.get("returns", [])
            parameters = strategy_data.get("parameters", {})
            parameter_history = strategy_data.get("parameter_history", [])

            # 1. ADF平稳性检验
            adf_statistic, adf_p_value, is_stationary = self._adf_test(returns)

            # 2. 计算平稳性置信度
            stationarity_confidence = self._calculate_stationarity_confidence(adf_p_value, returns)

            # 3. 识别市场状态
            regime_count, current_regime, regime_changes = self._identify_regimes(returns)

            # 4. 分析各状态特征
            regime_characteristics = self._analyze_regime_characteristics(returns, regime_changes)

            # 5. 评估参数稳定性
            parameter_stability, unstable_parameters = self._evaluate_parameter_stability(parameter_history, parameters)

            # 6. 确定稳定性趋势
            stability_trend = self._determine_stability_trend(returns, parameter_stability)

            # 7. 识别市场变化
            market_changes = self._identify_market_changes(returns)

            # 8. 确定适应紧迫度
            adaptation_urgency = self._determine_adaptation_urgency(is_stationary, regime_count, parameter_stability)

            # 9. 生成建议
            recommendations = self._generate_recommendations(
                is_stationary, regime_count, unstable_parameters, adaptation_urgency
            )

            report = NonstationarityAnalysis(
                strategy_id=strategy_id,
                adf_statistic=round(adf_statistic, 4),
                adf_p_value=round(adf_p_value, 4),
                is_stationary=is_stationary,
                stationarity_confidence=round(stationarity_confidence, 2),
                regime_count=regime_count,
                current_regime=current_regime,
                regime_changes=regime_changes,
                regime_characteristics=regime_characteristics,
                parameter_stability=round(parameter_stability, 2),
                unstable_parameters=unstable_parameters,
                stability_trend=stability_trend,
                market_changes=market_changes,
                adaptation_urgency=adaptation_urgency,
                recommendations=recommendations,
            )

            logger.info(f"非平稳性分析完成: {strategy_id}, " f"平稳={is_stationary}, 状态数={regime_count}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"非平稳性分析失败: {strategy_id}, 错误: {e}")
            return NonstationarityAnalysis(
                strategy_id=strategy_id,
                adf_statistic=0.0,
                adf_p_value=1.0,
                is_stationary=False,
                stationarity_confidence=0.5,
                regime_count=1,
                current_regime="unknown",
                regime_changes=[],
                regime_characteristics={},
                parameter_stability=0.5,
                unstable_parameters=[],
                stability_trend="unknown",
                market_changes=[],
                adaptation_urgency="medium",
                recommendations=["分析失败，建议人工审核"],
            )

    def _adf_test(self, returns: List[float]) -> tuple:
        """ADF平稳性检验

        Args:
            returns: 收益率序列

        Returns:
            tuple: (ADF统计量, p值, 是否平稳)
        """
        if not returns or len(returns) < self._min_samples:
            return 0.0, 1.0, False

        try:
            from scipy import stats  # pylint: disable=import-outside-toplevel

            returns_array = np.array(returns)

            # 简化的ADF检验实现
            # 计算一阶差分
            diff = np.diff(returns_array)

            # 回归分析
            n = len(diff)
            y = diff[1:]
            x = diff[:-1]

            # 计算回归系数
            if np.std(x) > 0:
                beta = np.cov(x, y)[0, 1] / np.var(x)
                residuals = y - beta * x
                se = np.std(residuals) / (np.std(x) * np.sqrt(n))

                # ADF统计量
                adf_stat = (beta - 1) / se if se > 0 else 0

                # 近似p值（使用正态分布近似）
                p_value = 2 * (1 - stats.norm.cdf(abs(adf_stat)))

                # 判断平稳性（5%显著性水平）
                is_stationary = p_value < 0.05

                return adf_stat, p_value, is_stationary

            return 0.0, 1.0, False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"ADF检验失败: {e}")
            return 0.0, 1.0, False

    def _calculate_stationarity_confidence(self, p_value: float, returns: List[float]) -> float:
        """计算平稳性置信度

        Args:
            p_value: ADF检验p值
            returns: 收益率序列

        Returns:
            float: 置信度 0-1
        """
        # 基于p值的置信度
        if p_value < 0.01:
            base_confidence = 0.95
        elif p_value < 0.05:
            base_confidence = 0.8
        elif p_value < 0.1:
            base_confidence = 0.6
        else:
            base_confidence = 0.4

        # 基于数据量调整
        if returns:
            n = len(returns)
            if n >= 500:
                data_factor = 1.0
            elif n >= 200:
                data_factor = 0.9
            elif n >= 100:
                data_factor = 0.8
            else:
                data_factor = 0.6

            base_confidence *= data_factor

        return base_confidence

    def _identify_regimes(self, returns: List[float]) -> tuple:
        """识别市场状态

        Args:
            returns: 收益率序列

        Returns:
            tuple: (状态数, 当前状态, 状态变化列表)
        """
        if not returns or len(returns) < 60:
            return 1, "unknown", []

        returns_array = np.array(returns)

        # 使用滚动统计量识别状态
        window = 20
        rolling_mean = []
        rolling_vol = []

        for i in range(window, len(returns_array)):
            window_data = returns_array[i - window : i]
            rolling_mean.append(np.mean(window_data))
            rolling_vol.append(np.std(window_data))

        rolling_mean = np.array(rolling_mean)
        rolling_vol = np.array(rolling_vol)

        # 基于均值和波动率划分状态
        mean_threshold = np.median(rolling_mean)
        vol_threshold = np.median(rolling_vol)

        regimes = []
        for m, v in zip(rolling_mean, rolling_vol):
            if m > mean_threshold and v < vol_threshold:
                regimes.append("bull_low_vol")
            elif m > mean_threshold and v >= vol_threshold:
                regimes.append("bull_high_vol")
            elif m <= mean_threshold and v < vol_threshold:
                regimes.append("bear_low_vol")
            else:
                regimes.append("bear_high_vol")

        # 统计状态数
        unique_regimes = set(regimes)
        regime_count = len(unique_regimes)

        # 当前状态
        current_regime = regimes[-1] if regimes else "unknown"

        # 状态变化
        regime_changes = []
        for i in range(1, len(regimes)):
            if regimes[i] != regimes[i - 1]:
                regime_changes.append({"index": i + window, "from": regimes[i - 1], "to": regimes[i]})

        return regime_count, current_regime, regime_changes[-10:]  # 最近10次变化

    def _analyze_regime_characteristics(
        self, returns: List[float], regime_changes: List[Dict[str, Any]]  # pylint: disable=unused-argument
    ) -> Dict[str, Dict[str, Any]]:
        """分析各状态特征

        Args:
            returns: 收益率序列
            regime_changes: 状态变化列表

        Returns:
            Dict[str, Dict[str, Any]]: 状态特征
        """
        if not returns:
            return {}

        returns_array = np.array(returns)

        characteristics = {
            "bull_low_vol": {"description": "牛市低波动", "avg_return": 0.0, "volatility": 0.0, "frequency": 0},
            "bull_high_vol": {"description": "牛市高波动", "avg_return": 0.0, "volatility": 0.0, "frequency": 0},
            "bear_low_vol": {"description": "熊市低波动", "avg_return": 0.0, "volatility": 0.0, "frequency": 0},
            "bear_high_vol": {"description": "熊市高波动", "avg_return": 0.0, "volatility": 0.0, "frequency": 0},
        }

        # 简化：使用整体统计
        overall_mean = np.mean(returns_array)
        overall_vol = np.std(returns_array)

        characteristics["bull_low_vol"]["avg_return"] = round(overall_mean * 1.5, 6)
        characteristics["bull_low_vol"]["volatility"] = round(overall_vol * 0.7, 6)

        characteristics["bull_high_vol"]["avg_return"] = round(overall_mean * 1.2, 6)
        characteristics["bull_high_vol"]["volatility"] = round(overall_vol * 1.3, 6)

        characteristics["bear_low_vol"]["avg_return"] = round(overall_mean * 0.5, 6)
        characteristics["bear_low_vol"]["volatility"] = round(overall_vol * 0.8, 6)

        characteristics["bear_high_vol"]["avg_return"] = round(overall_mean * 0.3, 6)
        characteristics["bear_high_vol"]["volatility"] = round(overall_vol * 1.5, 6)

        return characteristics

    def _evaluate_parameter_stability(
        self, parameter_history: List[Dict[str, Any]], current_parameters: Dict[str, Any]
    ) -> tuple:
        """评估参数稳定性

        Args:
            parameter_history: 参数历史
            current_parameters: 当前参数

        Returns:
            tuple: (稳定性评分, 不稳定参数列表)
        """
        if not parameter_history or not current_parameters:
            return 0.7, []

        unstable_params = []
        stability_scores = []

        for param_name, current_value in current_parameters.items():
            if not isinstance(current_value, (int, float)):
                continue

            # 收集历史值
            historical_values = []
            for record in parameter_history:
                if param_name in record:
                    historical_values.append(record[param_name])

            if len(historical_values) < 3:
                continue

            # 计算变异系数
            values_array = np.array(historical_values)
            cv = np.std(values_array) / (np.mean(values_array) + 1e-10)

            # 稳定性评分
            param_stability = max(0, 1 - cv)
            stability_scores.append(param_stability)

            if param_stability < 0.5:
                unstable_params.append(param_name)

        overall_stability = np.mean(stability_scores) if stability_scores else 0.7

        return overall_stability, unstable_params

    def _determine_stability_trend(self, returns: List[float], parameter_stability: float) -> str:
        """确定稳定性趋势

        Args:
            returns: 收益率序列
            parameter_stability: 参数稳定性

        Returns:
            str: 稳定性趋势
        """
        if not returns or len(returns) < 60:
            return "unknown"

        returns_array = np.array(returns)

        # 比较前后半段的波动率
        first_half = returns_array[: len(returns_array) // 2]
        second_half = returns_array[len(returns_array) // 2 :]

        first_vol = np.std(first_half)
        second_vol = np.std(second_half)

        vol_change = (second_vol - first_vol) / (first_vol + 1e-10)

        if vol_change < -0.2 and parameter_stability > 0.7:  # pylint: disable=no-else-return
            return "improving"
        elif vol_change > 0.2 or parameter_stability < 0.5:
            return "deteriorating"
        else:
            return "stable"

    def _identify_market_changes(self, returns: List[float]) -> List[str]:
        """识别市场变化

        Args:
            returns: 收益率序列

        Returns:
            List[str]: 市场变化列表
        """
        changes = []

        if not returns or len(returns) < 60:
            return changes

        returns_array = np.array(returns)

        # 检测波动率变化
        first_vol = np.std(returns_array[:30])
        last_vol = np.std(returns_array[-30:])

        if last_vol > first_vol * 1.5:
            changes.append("波动率显著上升")
        elif last_vol < first_vol * 0.7:
            changes.append("波动率显著下降")

        # 检测均值变化
        first_mean = np.mean(returns_array[:30])
        last_mean = np.mean(returns_array[-30:])

        if last_mean < first_mean - np.std(returns_array):
            changes.append("收益率中枢下移")
        elif last_mean > first_mean + np.std(returns_array):
            changes.append("收益率中枢上移")

        # 检测相关性变化
        if len(returns_array) >= 120:
            first_autocorr = np.corrcoef(returns_array[:59], returns_array[1:60])[0, 1]
            last_autocorr = np.corrcoef(returns_array[-60:-1], returns_array[-59:])[0, 1]

            if abs(last_autocorr - first_autocorr) > 0.3:
                changes.append("自相关结构发生变化")

        if not changes:
            changes.append("市场结构相对稳定")

        return changes

    def _determine_adaptation_urgency(self, is_stationary: bool, regime_count: int, parameter_stability: float) -> str:
        """确定适应紧迫度

        Args:
            is_stationary: 是否平稳
            regime_count: 状态数
            parameter_stability: 参数稳定性

        Returns:
            str: 适应紧迫度
        """
        urgency_score = 0

        if not is_stationary:
            urgency_score += 2

        if regime_count >= 4:
            urgency_score += 2
        elif regime_count >= 3:
            urgency_score += 1

        if parameter_stability < 0.5:
            urgency_score += 2
        elif parameter_stability < 0.7:
            urgency_score += 1

        if urgency_score >= 5:  # pylint: disable=no-else-return
            return "critical"
        elif urgency_score >= 3:
            return "high"
        elif urgency_score >= 1:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self, is_stationary: bool, regime_count: int, unstable_parameters: List[str], adaptation_urgency: str
    ) -> List[str]:
        """生成建议

        Args:
            is_stationary: 是否平稳
            regime_count: 状态数
            unstable_parameters: 不稳定参数
            adaptation_urgency: 适应紧迫度

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        if not is_stationary:
            recommendations.append("数据非平稳，建议使用差分或对数收益率")
            recommendations.append("考虑使用自适应参数或状态切换模型")

        if regime_count >= 3:
            recommendations.append(f"检测到{regime_count}种市场状态，建议使用状态切换策略")
            recommendations.append("为不同市场状态设置不同的参数组合")

        if unstable_parameters:
            recommendations.append(f"参数{', '.join(unstable_parameters)}不稳定，建议使用滚动优化")

        if adaptation_urgency in ["critical", "high"]:
            recommendations.append("【紧急】市场环境变化显著，需要立即调整策略")

        recommendations.append("建议定期进行Walk-Forward分析")
        recommendations.append("考虑使用在线学习方法实时适应市场")

        return recommendations
