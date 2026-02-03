"""特征工程分析器

白皮书依据: 第五章 5.2.4 特征工程分析
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import FeatureAnalysisReport


class FeatureAnalyzer:
    """特征工程分析器

    白皮书依据: 第五章 5.2.4 特征工程分析

    分析内容:
    - 特征重要性排名: 各特征对策略的贡献度
    - 相关性矩阵: 特征间的相关关系
    - 共线性问题: 检测多重共线性
    - 稳定性评分: 特征在不同时期的稳定性
    - IC/IR分析: 信息系数和信息比率
    """

    def __init__(self):
        """初始化特征工程分析器"""
        self._ic_threshold = 0.03  # IC有效阈值
        self._correlation_threshold = 0.7  # 高相关阈值
        logger.info("FeatureAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> FeatureAnalysisReport:
        """分析策略特征工程

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据，包含features, returns等

        Returns:
            FeatureAnalysisReport: 特征分析报告
        """
        logger.info(f"开始特征工程分析: {strategy_id}")

        try:
            features = strategy_data.get("features", {})  # Dict[feature_name, values]
            returns = strategy_data.get("returns", [])
            feature_names = list(features.keys()) if features else []

            # 1. 计算特征重要性
            feature_importance = self._calculate_feature_importance(features, returns)

            # 2. 计算相关性矩阵
            correlation_matrix = self._calculate_correlation_matrix(features)

            # 3. 检测共线性问题
            multicollinearity_issues = self._detect_multicollinearity(correlation_matrix, feature_names)

            # 4. 计算稳定性评分
            stability_scores = self._calculate_stability_scores(features)

            # 5. 计算IC值
            ic_values = self._calculate_ic_values(features, returns)

            # 6. 计算IR值
            ir_values = self._calculate_ir_values(features, returns)

            # 7. 生成特征推荐
            recommendations = self._generate_recommendations(
                feature_importance, ic_values, ir_values, multicollinearity_issues, stability_scores
            )

            report = FeatureAnalysisReport(
                strategy_id=strategy_id,
                feature_importance=feature_importance,
                correlation_matrix=correlation_matrix,
                multicollinearity_issues=multicollinearity_issues,
                stability_scores=stability_scores,
                recommendations=recommendations,
                ic_values=ic_values,
                ir_values=ir_values,
            )

            logger.info(f"特征工程分析完成: {strategy_id}, 特征数量: {len(feature_names)}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"特征工程分析失败: {strategy_id}, 错误: {e}")
            return FeatureAnalysisReport(
                strategy_id=strategy_id,
                feature_importance={},
                correlation_matrix={},
                multicollinearity_issues=["分析失败"],
                stability_scores={},
                recommendations=["建议人工审核特征"],
                ic_values={},
                ir_values={},
            )

    def _calculate_feature_importance(self, features: Dict[str, List[float]], returns: List[float]) -> Dict[str, float]:
        """计算特征重要性

        Args:
            features: 特征数据
            returns: 收益率序列

        Returns:
            Dict[str, float]: 特征名 -> 重要性评分
        """
        if not features or not returns:
            return {}

        importance = {}
        returns_array = np.array(returns)

        for name, values in features.items():
            if len(values) != len(returns):
                continue

            feature_array = np.array(values)

            # 使用相关系数作为重要性指标
            if np.std(feature_array) > 0 and np.std(returns_array) > 0:
                corr = np.corrcoef(feature_array, returns_array)[0, 1]
                importance[name] = abs(corr)
            else:
                importance[name] = 0.0

        # 归一化
        if importance:
            max_imp = max(importance.values())
            if max_imp > 0:
                importance = {k: v / max_imp for k, v in importance.items()}

        # 按重要性排序
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

        return importance

    def _calculate_correlation_matrix(self, features: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """计算相关性矩阵

        Args:
            features: 特征数据

        Returns:
            Dict[str, Dict[str, float]]: 相关性矩阵
        """
        if not features:
            return {}

        feature_names = list(features.keys())
        n_features = len(feature_names)

        if n_features == 0:
            return {}

        # 构建特征矩阵
        min_len = min(len(v) for v in features.values())
        feature_matrix = np.array([features[name][:min_len] for name in feature_names])

        # 计算相关系数矩阵
        corr_matrix = {}
        for i, name_i in enumerate(feature_names):
            corr_matrix[name_i] = {}
            for j, name_j in enumerate(feature_names):
                if np.std(feature_matrix[i]) > 0 and np.std(feature_matrix[j]) > 0:
                    corr = np.corrcoef(feature_matrix[i], feature_matrix[j])[0, 1]
                    corr_matrix[name_i][name_j] = round(corr, 4)
                else:
                    corr_matrix[name_i][name_j] = 0.0

        return corr_matrix

    def _detect_multicollinearity(
        self, correlation_matrix: Dict[str, Dict[str, float]], feature_names: List[str]
    ) -> List[str]:
        """检测多重共线性

        Args:
            correlation_matrix: 相关性矩阵
            feature_names: 特征名列表

        Returns:
            List[str]: 共线性问题列表
        """
        issues = []

        if not correlation_matrix:
            return issues

        checked_pairs = set()

        for name_i in feature_names:
            if name_i not in correlation_matrix:
                continue
            for name_j in feature_names:
                if name_i == name_j:
                    continue
                if name_j not in correlation_matrix.get(name_i, {}):
                    continue

                pair = tuple(sorted([name_i, name_j]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                corr = abs(correlation_matrix[name_i][name_j])
                if corr > self._correlation_threshold:
                    issues.append(f"特征'{name_i}'与'{name_j}'高度相关(r={corr:.3f})，" f"建议移除其中一个")

        return issues

    def _calculate_stability_scores(self, features: Dict[str, List[float]]) -> Dict[str, float]:
        """计算特征稳定性评分

        Args:
            features: 特征数据

        Returns:
            Dict[str, float]: 特征名 -> 稳定性评分
        """
        if not features:
            return {}

        stability = {}

        for name, values in features.items():
            if len(values) < 20:
                stability[name] = 0.5  # 数据不足，给中等评分
                continue

            values_array = np.array(values)

            # 计算滚动统计量的稳定性
            window = min(20, len(values) // 5)
            if window < 5:
                stability[name] = 0.5
                continue

            rolling_means = []
            rolling_stds = []

            for i in range(window, len(values_array)):
                window_data = values_array[i - window : i]
                rolling_means.append(np.mean(window_data))
                rolling_stds.append(np.std(window_data))

            if not rolling_means:
                stability[name] = 0.5
                continue

            # 稳定性 = 1 - 变异系数
            mean_cv = np.std(rolling_means) / (np.mean(np.abs(rolling_means)) + 1e-10)
            std_cv = np.std(rolling_stds) / (np.mean(rolling_stds) + 1e-10)

            stability_score = 1 - (mean_cv + std_cv) / 2
            stability[name] = max(0, min(1, stability_score))

        return stability

    def _calculate_ic_values(self, features: Dict[str, List[float]], returns: List[float]) -> Dict[str, float]:
        """计算IC值（信息系数）

        Args:
            features: 特征数据
            returns: 收益率序列

        Returns:
            Dict[str, float]: 特征名 -> IC值
        """
        if not features or not returns:
            return {}

        ic_values = {}
        returns_array = np.array(returns)

        for name, values in features.items():
            if len(values) != len(returns):
                continue

            feature_array = np.array(values)

            # 计算Spearman秩相关系数作为IC
            if np.std(feature_array) > 0:
                from scipy import stats  # pylint: disable=import-outside-toplevel

                ic, _ = stats.spearmanr(feature_array, returns_array)
                ic_values[name] = round(ic, 4) if not np.isnan(ic) else 0.0
            else:
                ic_values[name] = 0.0

        return ic_values

    def _calculate_ir_values(self, features: Dict[str, List[float]], returns: List[float]) -> Dict[str, float]:
        """计算IR值（信息比率）

        Args:
            features: 特征数据
            returns: 收益率序列

        Returns:
            Dict[str, float]: 特征名 -> IR值
        """
        if not features or not returns:
            return {}

        ir_values = {}
        returns_array = np.array(returns)

        for name, values in features.items():
            if len(values) < 20:
                ir_values[name] = 0.0
                continue

            feature_array = np.array(values)

            # 计算滚动IC
            window = min(20, len(values) // 5)
            if window < 5:
                ir_values[name] = 0.0
                continue

            rolling_ics = []
            for i in range(window, len(feature_array)):
                window_feature = feature_array[i - window : i]
                window_returns = returns_array[i - window : i]

                if np.std(window_feature) > 0 and np.std(window_returns) > 0:
                    from scipy import stats  # pylint: disable=import-outside-toplevel

                    ic, _ = stats.spearmanr(window_feature, window_returns)
                    if not np.isnan(ic):
                        rolling_ics.append(ic)

            if rolling_ics:
                ic_mean = np.mean(rolling_ics)
                ic_std = np.std(rolling_ics)
                ir = ic_mean / ic_std if ic_std > 0 else 0.0
                ir_values[name] = round(ir, 4)
            else:
                ir_values[name] = 0.0

        return ir_values

    def _generate_recommendations(  # pylint: disable=too-many-positional-arguments
        self,
        feature_importance: Dict[str, float],  # pylint: disable=unused-argument
        ic_values: Dict[str, float],
        ir_values: Dict[str, float],
        multicollinearity_issues: List[str],
        stability_scores: Dict[str, float],
    ) -> List[str]:
        """生成特征推荐

        Args:
            feature_importance: 特征重要性
            ic_values: IC值
            ir_values: IR值
            multicollinearity_issues: 共线性问题
            stability_scores: 稳定性评分

        Returns:
            List[str]: 推荐列表
        """
        recommendations = []

        # 基于IC值推荐
        high_ic_features = [name for name, ic in ic_values.items() if abs(ic) > self._ic_threshold]
        low_ic_features = [name for name, ic in ic_values.items() if abs(ic) < 0.01]

        if high_ic_features:
            recommendations.append(f"高IC特征（建议保留）: {', '.join(high_ic_features[:5])}")

        if low_ic_features:
            recommendations.append(f"低IC特征（建议移除）: {', '.join(low_ic_features[:5])}")

        # 基于IR值推荐
        high_ir_features = [name for name, ir in ir_values.items() if ir > 0.5]
        if high_ir_features:
            recommendations.append(f"高IR特征（预测稳定）: {', '.join(high_ir_features[:5])}")

        # 基于稳定性推荐
        unstable_features = [name for name, score in stability_scores.items() if score < 0.3]
        if unstable_features:
            recommendations.append(f"不稳定特征（需要关注）: {', '.join(unstable_features[:5])}")

        # 共线性建议
        if multicollinearity_issues:
            recommendations.append(f"存在{len(multicollinearity_issues)}个共线性问题，建议进行特征选择")

        # 通用建议
        if not recommendations:
            recommendations.append("特征工程整体良好，建议持续监控")

        # 新特征建议
        recommendations.append("建议尝试: 动量因子、波动率因子、流动性因子")

        return recommendations
