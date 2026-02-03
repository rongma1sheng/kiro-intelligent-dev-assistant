"""因子暴露分析器

白皮书依据: 第五章 5.2.16 因子暴露分析
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.linear_model import LinearRegression

from .data_models import FactorExposureAnalysis


class FactorExposureAnalyzer:
    """因子暴露分析器

    白皮书依据: 第五章 5.2.16 因子暴露分析

    核心功能：
    1. 多因子回归分析
    2. Fama-French三因子/五因子模型
    3. Carhart四因子模型
    4. 风险归因（方差分解）
    5. 因子择时分析
    6. 因子选择分析

    性能要求:
    - 因子回归延迟: <3秒
    - 风险分解延迟: <2秒
    - 因子择时分析: <4秒
    """

    def __init__(self):
        """初始化分析器"""
        logger.info("初始化FactorExposureAnalyzer")

    def analyze(
        self,
        strategy_id: str,
        returns: pd.Series,
        factor_returns: pd.DataFrame,
        holdings: Optional[pd.DataFrame] = None,
    ) -> FactorExposureAnalysis:
        """执行因子暴露分析

        白皮书依据: 第五章 5.2.16 因子暴露分析

        Args:
            strategy_id: 策略ID
            returns: 策略收益率序列
            factor_returns: 因子收益率数据（列为因子名）
            holdings: 持仓数据（可选）

        Returns:
            FactorExposureAnalysis对象

        Raises:
            ValueError: 当输入数据无效时
        """
        start_time = datetime.now()
        logger.info(f"开始因子暴露分析: {strategy_id}")

        try:
            # 1. 数据验证和对齐
            aligned_returns, aligned_factors = self._align_data(returns, factor_returns)

            # 2. 多因子回归
            regression_results = self._perform_factor_regression(aligned_returns, aligned_factors)

            # 3. 提取因子暴露度
            factor_exposures = regression_results["exposures"]

            # 4. 提取关键因子暴露
            market_beta = factor_exposures.get("market", 0.0)
            size_exposure = factor_exposures.get("size", 0.0)
            value_exposure = factor_exposures.get("value", 0.0)
            momentum_exposure = factor_exposures.get("momentum", 0.0)
            quality_exposure = factor_exposures.get("quality", 0.0)
            volatility_exposure = factor_exposures.get("volatility", 0.0)
            liquidity_exposure = factor_exposures.get("liquidity", 0.0)

            # 5. 行业和风格暴露
            sector_exposures = self._calculate_sector_exposures(holdings) if holdings is not None else {}
            style_exposures = self._calculate_style_exposures(factor_exposures)

            # 6. 因子收益贡献
            factor_contribution = self._calculate_factor_contribution(factor_exposures, aligned_factors)

            # 7. Alpha和R²
            alpha = regression_results["alpha"]
            r_squared = regression_results["r_squared"]

            # 8. 跟踪误差和信息比率
            tracking_error = self._calculate_tracking_error(aligned_returns, regression_results["fitted_values"])
            information_ratio = alpha / tracking_error if tracking_error > 0 else 0.0

            # 9. 因子择时和选择能力
            factor_timing = self._calculate_factor_timing(aligned_returns, aligned_factors, factor_exposures)
            factor_selection = self._calculate_factor_selection(factor_exposures, factor_contribution)

            # 10. 风险分解
            risk_decomposition = self._decompose_risk(aligned_returns, aligned_factors, factor_exposures)
            systematic_risk = risk_decomposition["systematic"]
            idiosyncratic_risk = risk_decomposition["idiosyncratic"]

            # 11. 因子集中度分析
            concentration_analysis = self._analyze_concentration(factor_exposures)

            # 12. 因子相关性矩阵
            factor_correlation = self._calculate_factor_correlation(aligned_factors)

            # 13. 暴露度稳定性和漂移
            exposure_stability, exposure_drift = self._analyze_exposure_stability(aligned_returns, aligned_factors)

            # 14. 再平衡需求
            rebalancing_needs = self._identify_rebalancing_needs(factor_exposures, exposure_drift)

            # 15. 对冲建议
            hedging_recommendations = self._generate_hedging_recommendations(factor_exposures, risk_decomposition)

            # 16. 因子轮动信号
            factor_rotation_signals = self._detect_factor_rotation_signals(aligned_factors, factor_exposures)

            # 17. 构建分析结果
            analysis = FactorExposureAnalysis(
                strategy_id=strategy_id,
                factor_exposures=factor_exposures,
                market_beta=market_beta,
                size_exposure=size_exposure,
                value_exposure=value_exposure,
                momentum_exposure=momentum_exposure,
                quality_exposure=quality_exposure,
                volatility_exposure=volatility_exposure,
                liquidity_exposure=liquidity_exposure,
                sector_exposures=sector_exposures,
                style_exposures=style_exposures,
                factor_contribution=factor_contribution,
                alpha=alpha,
                r_squared=r_squared,
                tracking_error=tracking_error,
                information_ratio=information_ratio,
                factor_timing=factor_timing,
                factor_selection=factor_selection,
                risk_decomposition=risk_decomposition,
                systematic_risk=systematic_risk,
                idiosyncratic_risk=idiosyncratic_risk,
                concentration_analysis=concentration_analysis,
                factor_correlation=factor_correlation,
                exposure_stability=exposure_stability,
                exposure_drift=exposure_drift,
                rebalancing_needs=rebalancing_needs,
                hedging_recommendations=hedging_recommendations,
                factor_rotation_signals=factor_rotation_signals,
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"因子暴露分析完成: {strategy_id}, 耗时: {elapsed:.2f}秒")

            return analysis

        except Exception as e:
            logger.error(f"因子暴露分析失败: {strategy_id}, 错误: {e}")
            raise

    def _align_data(self, returns: pd.Series, factor_returns: pd.DataFrame) -> tuple:
        """对齐数据

        Args:
            returns: 策略收益率
            factor_returns: 因子收益率

        Returns:
            (对齐后的收益率, 对齐后的因子收益率)
        """
        # 找到共同的日期索引
        common_index = returns.index.intersection(factor_returns.index)

        if len(common_index) == 0:
            raise ValueError("策略收益率和因子收益率没有共同的日期")

        aligned_returns = returns.loc[common_index]
        aligned_factors = factor_returns.loc[common_index]

        return aligned_returns, aligned_factors

    def _perform_factor_regression(self, returns: pd.Series, factor_returns: pd.DataFrame) -> Dict[str, Any]:
        """执行多因子回归

        白皮书依据: 第五章 5.2.16 多因子回归

        Args:
            returns: 策略收益率
            factor_returns: 因子收益率

        Returns:
            回归结果字典
        """
        logger.debug("执行多因子回归")

        # 准备数据
        X = factor_returns.values
        y = returns.values

        # 线性回归
        model = LinearRegression()
        model.fit(X, y)

        # 提取结果
        alpha = float(model.intercept_)
        exposures = {factor: float(coef) for factor, coef in zip(factor_returns.columns, model.coef_)}

        # 拟合值和残差
        fitted_values = model.predict(X)
        residuals = y - fitted_values

        # R²
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return {
            "alpha": alpha,
            "exposures": exposures,
            "fitted_values": fitted_values,
            "residuals": residuals,
            "r_squared": float(r_squared),
        }

    def _calculate_sector_exposures(self, holdings: pd.DataFrame) -> Dict[str, float]:
        """计算行业暴露度

        Args:
            holdings: 持仓数据

        Returns:
            行业暴露度字典
        """
        # 简化实现：假设holdings包含sector列
        if "sector" in holdings.columns and "weight" in holdings.columns:  # pylint: disable=no-else-return
            sector_exposure = holdings.groupby("sector")["weight"].sum().to_dict()
            return {k: float(v) for k, v in sector_exposure.items()}
        else:
            return {}

    def _calculate_style_exposures(self, factor_exposures: Dict[str, float]) -> Dict[str, float]:
        """计算风格暴露度

        Args:
            factor_exposures: 因子暴露度

        Returns:
            风格暴露度字典
        """
        # 将因子暴露映射到风格
        style_mapping = {
            "growth": ["momentum", "quality"],
            "value": ["value"],
            "size": ["size"],
            "quality": ["quality"],
        }

        style_exposures = {}
        for style, factors in style_mapping.items():
            exposure = sum(factor_exposures.get(f, 0.0) for f in factors)
            style_exposures[style] = float(exposure / len(factors))

        return style_exposures

    def _calculate_factor_contribution(
        self, factor_exposures: Dict[str, float], factor_returns: pd.DataFrame
    ) -> Dict[str, float]:
        """计算因子收益贡献

        Args:
            factor_exposures: 因子暴露度
            factor_returns: 因子收益率

        Returns:
            因子贡献字典
        """
        contribution = {}

        for factor, exposure in factor_exposures.items():
            if factor in factor_returns.columns:
                factor_return = factor_returns[factor].mean()
                contribution[factor] = float(exposure * factor_return)
            else:
                contribution[factor] = 0.0

        return contribution

    def _calculate_tracking_error(self, returns: pd.Series, fitted_values: np.ndarray) -> float:
        """计算跟踪误差

        Args:
            returns: 实际收益率
            fitted_values: 拟合值

        Returns:
            跟踪误差
        """
        tracking_diff = returns.values - fitted_values
        tracking_error = np.std(tracking_diff)
        return float(tracking_error)

    def _calculate_factor_timing(
        self,
        returns: pd.Series,  # pylint: disable=unused-argument
        factor_returns: pd.DataFrame,
        factor_exposures: Dict[str, float],  # pylint: disable=unused-argument
    ) -> float:
        """计算因子择时能力

        白皮书依据: 第五章 5.2.16 因子择时

        Args:
            returns: 策略收益率
            factor_returns: 因子收益率
            factor_exposures: 因子暴露度

        Returns:
            择时能力评分（0-1）
        """
        # 简化实现：计算暴露度与因子收益的相关性
        timing_scores = []

        for factor, exposure in factor_exposures.items():
            if factor in factor_returns.columns:
                # 计算滚动暴露度（简化为固定暴露）
                factor_ret = factor_returns[factor]

                # 如果暴露度与因子收益同向，说明择时能力好
                correlation = np.corrcoef([exposure] * len(factor_ret), factor_ret)[0, 1]

                if not np.isnan(correlation):
                    timing_scores.append(abs(correlation))

        if timing_scores:  # pylint: disable=no-else-return
            return float(np.mean(timing_scores))
        else:
            return 0.5

    def _calculate_factor_selection(
        self,
        factor_exposures: Dict[str, float],  # pylint: disable=unused-argument
        factor_contribution: Dict[str, float],  # pylint: disable=unused-argument
    ) -> float:
        """计算因子选择能力

        Args:
            factor_exposures: 因子暴露度
            factor_contribution: 因子贡献

        Returns:
            选择能力评分（0-1）
        """
        # 计算正贡献因子的比例
        positive_contributions = sum(1 for contrib in factor_contribution.values() if contrib > 0)
        total_factors = len(factor_contribution)

        if total_factors > 0:  # pylint: disable=no-else-return
            selection_score = positive_contributions / total_factors
            return float(selection_score)
        else:
            return 0.5

    def _decompose_risk(
        self, returns: pd.Series, factor_returns: pd.DataFrame, factor_exposures: Dict[str, float]
    ) -> Dict[str, float]:
        """分解风险

        白皮书依据: 第五章 5.2.16 风险分解

        Args:
            returns: 策略收益率
            factor_returns: 因子收益率
            factor_exposures: 因子暴露度

        Returns:
            风险分解字典
        """
        # 总风险
        total_risk = float(returns.std())

        # 系统性风险（因子解释的风险）
        factor_variance = 0.0
        for factor, exposure in factor_exposures.items():
            if factor in factor_returns.columns:
                factor_var = factor_returns[factor].var()
                factor_variance += (exposure**2) * factor_var

        systematic_risk = float(np.sqrt(factor_variance))

        # 特异性风险（残差风险）
        idiosyncratic_risk = float(np.sqrt(max(0, total_risk**2 - systematic_risk**2)))

        return {
            "total": total_risk,
            "systematic": systematic_risk,
            "idiosyncratic": idiosyncratic_risk,
            "systematic_pct": systematic_risk / total_risk if total_risk > 0 else 0.0,
            "idiosyncratic_pct": idiosyncratic_risk / total_risk if total_risk > 0 else 0.0,
        }

    def _analyze_concentration(self, factor_exposures: Dict[str, float]) -> Dict[str, Any]:
        """分析因子集中度

        Args:
            factor_exposures: 因子暴露度

        Returns:
            集中度分析字典
        """
        exposures = np.array(list(factor_exposures.values()))
        abs_exposures = np.abs(exposures)

        # Herfindahl指数
        total_exposure = abs_exposures.sum()
        if total_exposure > 0:
            normalized_exposures = abs_exposures / total_exposure
            herfindahl = float(np.sum(normalized_exposures**2))
        else:
            herfindahl = 0.0

        # 最大暴露
        max_exposure = float(abs_exposures.max()) if len(abs_exposures) > 0 else 0.0

        # 前3大因子占比
        top3_exposure = float(np.sort(abs_exposures)[-3:].sum() / total_exposure) if total_exposure > 0 else 0.0

        return {"herfindahl_index": herfindahl, "max_exposure": max_exposure, "top3_concentration": top3_exposure}

    def _calculate_factor_correlation(self, factor_returns: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """计算因子相关性矩阵

        Args:
            factor_returns: 因子收益率

        Returns:
            相关性矩阵字典
        """
        corr_matrix = factor_returns.corr()

        return {
            factor1: {factor2: float(corr_matrix.loc[factor1, factor2]) for factor2 in corr_matrix.columns}
            for factor1 in corr_matrix.index
        }

    def _analyze_exposure_stability(self, returns: pd.Series, factor_returns: pd.DataFrame) -> tuple:
        """分析暴露度稳定性

        Args:
            returns: 策略收益率
            factor_returns: 因子收益率

        Returns:
            (稳定性评分, 漂移评分)
        """
        # 简化实现：使用滚动窗口回归
        window = min(60, len(returns) // 2)

        if len(returns) < window:
            return 0.5, 0.0

        exposures_over_time = []

        for i in range(window, len(returns)):
            window_returns = returns.iloc[i - window : i]
            window_factors = factor_returns.iloc[i - window : i]

            try:
                regression = self._perform_factor_regression(window_returns, window_factors)
                exposures_over_time.append(list(regression["exposures"].values()))
            except:  # pylint: disable=w0702
                continue

        if len(exposures_over_time) > 1:
            exposures_array = np.array(exposures_over_time)

            # 稳定性：暴露度的标准差（越小越稳定）
            stability = 1.0 - min(1.0, np.mean(np.std(exposures_array, axis=0)))

            # 漂移：暴露度的趋势（线性回归斜率）
            time_index = np.arange(len(exposures_array))
            drifts = []
            for j in range(exposures_array.shape[1]):
                slope = np.polyfit(time_index, exposures_array[:, j], 1)[0]
                drifts.append(abs(slope))
            drift = float(np.mean(drifts))
        else:
            stability = 0.5
            drift = 0.0

        return float(stability), drift

    def _identify_rebalancing_needs(self, factor_exposures: Dict[str, float], exposure_drift: float) -> List[str]:
        """识别再平衡需求

        Args:
            factor_exposures: 因子暴露度
            exposure_drift: 暴露度漂移

        Returns:
            再平衡需求列表
        """
        needs = []

        # 如果漂移较大，建议再平衡
        if exposure_drift > 0.1:
            needs.append("因子暴露度漂移较大，建议进行再平衡")

        # 如果某个因子暴露过大
        for factor, exposure in factor_exposures.items():
            if abs(exposure) > 2.0:
                needs.append(f"{factor}因子暴露度过高({exposure:.2f})，建议降低")

        return needs

    def _generate_hedging_recommendations(
        self, factor_exposures: Dict[str, float], risk_decomposition: Dict[str, float]
    ) -> List[str]:
        """生成对冲建议

        Args:
            factor_exposures: 因子暴露度
            risk_decomposition: 风险分解

        Returns:
            对冲建议列表
        """
        recommendations = []

        # 如果系统性风险过高
        if risk_decomposition["systematic_pct"] > 0.7:
            recommendations.append(
                f"系统性风险占比({risk_decomposition['systematic_pct']:.1%})较高，" "建议考虑对冲市场风险"
            )

        # 如果市场Beta过高
        market_beta = factor_exposures.get("market", 0.0)
        if abs(market_beta) > 1.5:
            recommendations.append(f"市场Beta({market_beta:.2f})较高，建议使用股指期货对冲")

        return recommendations

    def _detect_factor_rotation_signals(
        self, factor_returns: pd.DataFrame, factor_exposures: Dict[str, float]
    ) -> List[str]:
        """检测因子轮动信号

        Args:
            factor_returns: 因子收益率
            factor_returns: 因子暴露度

        Returns:
            轮动信号列表
        """
        signals = []

        # 计算近期因子表现
        recent_window = min(20, len(factor_returns))
        recent_performance = factor_returns.iloc[-recent_window:].mean()

        # 识别表现最好和最差的因子
        best_factor = recent_performance.idxmax()
        worst_factor = recent_performance.idxmin()

        # 如果当前暴露与表现不匹配，发出轮动信号
        if best_factor in factor_exposures:
            if factor_exposures[best_factor] < 0.5:
                signals.append(f"{best_factor}因子近期表现优异，建议增加暴露")

        if worst_factor in factor_exposures:
            if factor_exposures[worst_factor] > 0.5:
                signals.append(f"{worst_factor}因子近期表现不佳，建议降低暴露")

        return signals
