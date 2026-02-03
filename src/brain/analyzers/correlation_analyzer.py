"""相关性分析器

白皮书依据: 第五章 5.2.21 相关性分析
引擎: Commander (战略级分析)
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from .data_models import CorrelationAnalysis


class CorrelationAnalyzer:
    """相关性分析器

    白皮书依据: 第五章 5.2.21 相关性分析

    分析内容:
    - 策略间相关性矩阵计算
    - 高相关性策略对识别
    - 低相关性策略对识别
    - 分散化评分计算
    - 最优权重推荐
    - 风险降低评估
    """

    # 相关性阈值
    HIGH_CORRELATION_THRESHOLD: float = 0.7
    LOW_CORRELATION_THRESHOLD: float = 0.3

    def __init__(self):
        """初始化相关性分析器"""
        logger.info("CorrelationAnalyzer初始化完成")

    async def analyze(self, strategy_returns: Dict[str, List[float]]) -> CorrelationAnalysis:
        """分析策略间相关性

        Args:
            strategy_returns: 策略收益字典 {strategy_id: [returns]}

        Returns:
            CorrelationAnalysis: 相关性分析报告

        Raises:
            ValueError: 当策略数量不足时
        """
        if len(strategy_returns) < 2:
            raise ValueError("相关性分析至少需要2个策略")

        logger.info(f"开始相关性分析，策略数量: {len(strategy_returns)}")

        try:
            # 转换为DataFrame
            returns_df = self._prepare_returns_dataframe(strategy_returns)

            # 1. 计算相关性矩阵
            correlation_matrix = self._calculate_correlation_matrix(returns_df)

            # 2. 识别高相关性策略对
            high_correlation_pairs = self._find_high_correlation_pairs(correlation_matrix)

            # 3. 识别低相关性策略对
            low_correlation_pairs = self._find_low_correlation_pairs(correlation_matrix)

            # 4. 计算平均相关性
            avg_correlation = self._calculate_average_correlation(correlation_matrix)

            # 5. 计算分散化评分
            diversification_score = self._calculate_diversification_score(correlation_matrix, avg_correlation)

            # 6. 生成组合建议
            portfolio_recommendations = self._generate_portfolio_recommendations(
                correlation_matrix, high_correlation_pairs, low_correlation_pairs, diversification_score
            )

            # 7. 计算最优权重
            optimal_weights = self._calculate_optimal_weights(returns_df, correlation_matrix)

            # 8. 评估风险降低
            risk_reduction = self._estimate_risk_reduction(returns_df, optimal_weights)

            # 转换相关性矩阵为字典格式
            correlation_matrix_dict = self._matrix_to_dict(correlation_matrix)

            report = CorrelationAnalysis(
                strategy_count=len(strategy_returns),
                correlation_matrix=correlation_matrix_dict,
                high_correlation_pairs=high_correlation_pairs,
                low_correlation_pairs=low_correlation_pairs,
                avg_correlation=avg_correlation,
                diversification_score=diversification_score,
                portfolio_recommendations=portfolio_recommendations,
                optimal_weights=optimal_weights,
                risk_reduction=risk_reduction,
            )

            logger.info(
                f"相关性分析完成 - 平均相关性: {avg_correlation:.3f}, " f"分散化评分: {diversification_score:.3f}"
            )
            return report

        except Exception as e:
            logger.error(f"相关性分析失败: {e}")
            raise

    def _prepare_returns_dataframe(self, strategy_returns: Dict[str, List[float]]) -> pd.DataFrame:
        """准备收益率DataFrame

        Args:
            strategy_returns: 策略收益字典

        Returns:
            pd.DataFrame: 收益率DataFrame
        """
        # 找到最短的收益序列长度
        min_length = min(len(returns) for returns in strategy_returns.values())

        # 截取相同长度
        aligned_returns = {strategy_id: returns[:min_length] for strategy_id, returns in strategy_returns.items()}

        return pd.DataFrame(aligned_returns)

    def _calculate_correlation_matrix(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """计算相关性矩阵

        Args:
            returns_df: 收益率DataFrame

        Returns:
            pd.DataFrame: 相关性矩阵
        """
        # 使用Pearson相关系数
        correlation_matrix = returns_df.corr(method="pearson")

        # 处理NaN值
        correlation_matrix = correlation_matrix.fillna(0)

        return correlation_matrix

    def _find_high_correlation_pairs(self, correlation_matrix: pd.DataFrame) -> List[Tuple[str, str, float]]:
        """找出高相关性策略对

        Args:
            correlation_matrix: 相关性矩阵

        Returns:
            List[Tuple]: 高相关性策略对列表 [(strategy1, strategy2, correlation)]
        """
        high_pairs = []
        strategies = correlation_matrix.columns.tolist()

        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies):
                if i < j:  # 避免重复
                    corr = correlation_matrix.loc[strategy1, strategy2]
                    if abs(corr) >= self.HIGH_CORRELATION_THRESHOLD:
                        high_pairs.append((strategy1, strategy2, round(corr, 4)))

        # 按相关性绝对值降序排序
        high_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        return high_pairs

    def _find_low_correlation_pairs(self, correlation_matrix: pd.DataFrame) -> List[Tuple[str, str, float]]:
        """找出低相关性策略对

        Args:
            correlation_matrix: 相关性矩阵

        Returns:
            List[Tuple]: 低相关性策略对列表 [(strategy1, strategy2, correlation)]
        """
        low_pairs = []
        strategies = correlation_matrix.columns.tolist()

        for i, strategy1 in enumerate(strategies):
            for j, strategy2 in enumerate(strategies):
                if i < j:  # 避免重复
                    corr = correlation_matrix.loc[strategy1, strategy2]
                    if abs(corr) <= self.LOW_CORRELATION_THRESHOLD:
                        low_pairs.append((strategy1, strategy2, round(corr, 4)))

        # 按相关性绝对值升序排序
        low_pairs.sort(key=lambda x: abs(x[2]))

        return low_pairs

    def _calculate_average_correlation(self, correlation_matrix: pd.DataFrame) -> float:
        """计算平均相关性

        Args:
            correlation_matrix: 相关性矩阵

        Returns:
            float: 平均相关性（不包括对角线）
        """
        n = len(correlation_matrix)
        if n <= 1:
            return 0.0

        # 获取上三角矩阵（不包括对角线）
        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
        upper_triangle = correlation_matrix.values[mask]

        if len(upper_triangle) == 0:
            return 0.0

        return float(np.mean(upper_triangle))

    def _calculate_diversification_score(self, correlation_matrix: pd.DataFrame, avg_correlation: float) -> float:
        """计算分散化评分

        Args:
            correlation_matrix: 相关性矩阵
            avg_correlation: 平均相关性

        Returns:
            float: 分散化评分 0-1
        """
        # 分散化评分 = 1 - 平均相关性
        # 相关性越低，分散化越好
        base_score = 1 - abs(avg_correlation)

        # 考虑负相关的额外加分
        n = len(correlation_matrix)
        if n > 1:
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
            upper_triangle = correlation_matrix.values[mask]

            # 负相关比例
            negative_ratio = np.sum(upper_triangle < 0) / len(upper_triangle)

            # 负相关可以提供额外的分散化效果
            bonus = negative_ratio * 0.1
            base_score = min(1.0, base_score + bonus)

        return round(max(0, min(1, base_score)), 4)

    def _generate_portfolio_recommendations(
        self,
        correlation_matrix: pd.DataFrame,  # pylint: disable=unused-argument
        high_correlation_pairs: List[Tuple],
        low_correlation_pairs: List[Tuple],
        diversification_score: float,
    ) -> List[str]:
        """生成组合建议

        Args:
            correlation_matrix: 相关性矩阵
            high_correlation_pairs: 高相关性策略对
            low_correlation_pairs: 低相关性策略对
            diversification_score: 分散化评分

        Returns:
            List[str]: 组合建议列表
        """
        recommendations = []

        # 根据分散化评分给出总体建议
        if diversification_score >= 0.7:
            recommendations.append("组合分散化程度良好，策略间相关性较低")
        elif diversification_score >= 0.5:
            recommendations.append("组合分散化程度中等，建议适当调整策略配置")
        else:
            recommendations.append("组合分散化程度较差，策略间相关性过高，需要优化")

        # 针对高相关性策略对的建议
        if high_correlation_pairs:
            top_high = high_correlation_pairs[:3]
            for s1, s2, corr in top_high:
                recommendations.append(f"策略 {s1} 与 {s2} 相关性过高({corr:.2f})，" f"建议降低其中一个的权重或替换")

        # 针对低相关性策略对的建议
        if low_correlation_pairs:
            top_low = low_correlation_pairs[:3]
            for s1, s2, corr in top_low:
                recommendations.append(f"策略 {s1} 与 {s2} 相关性较低({corr:.2f})，" f"适合组合配置以分散风险")

        # 负相关策略建议
        negative_pairs = [p for p in low_correlation_pairs if p[2] < 0]
        if negative_pairs:
            recommendations.append(f"发现{len(negative_pairs)}对负相关策略，" f"可用于对冲风险")

        return recommendations

    def _calculate_optimal_weights(
        self, returns_df: pd.DataFrame, correlation_matrix: pd.DataFrame
    ) -> Dict[str, float]:
        """计算最优权重（简化版均值-方差优化）

        Args:
            returns_df: 收益率DataFrame
            correlation_matrix: 相关性矩阵

        Returns:
            Dict[str, float]: 最优权重字典
        """
        strategies = returns_df.columns.tolist()
        n = len(strategies)

        if n == 0:
            return {}

        # 计算各策略的夏普比率作为权重基础
        sharpe_ratios = {}
        for strategy in strategies:
            returns = returns_df[strategy].values
            mean_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return > 0:
                sharpe = mean_return / std_return * np.sqrt(252)
            else:
                sharpe = 0

            sharpe_ratios[strategy] = max(0, sharpe)  # 只考虑正夏普

        # 根据相关性调整权重
        adjusted_weights = {}
        total_sharpe = sum(sharpe_ratios.values())

        if total_sharpe > 0:
            for strategy in strategies:
                # 基础权重
                base_weight = sharpe_ratios[strategy] / total_sharpe

                # 相关性惩罚：与其他策略相关性越高，权重越低
                avg_corr_with_others = 0
                for other in strategies:
                    if other != strategy:
                        avg_corr_with_others += abs(correlation_matrix.loc[strategy, other])

                if n > 1:
                    avg_corr_with_others /= n - 1

                # 调整因子：相关性越高，调整因子越小
                adjustment = 1 - avg_corr_with_others * 0.3
                adjusted_weights[strategy] = base_weight * adjustment
        else:
            # 如果所有夏普比率都为0或负，使用等权重
            for strategy in strategies:
                adjusted_weights[strategy] = 1.0 / n

        # 归一化权重
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            for strategy in adjusted_weights:
                adjusted_weights[strategy] = round(adjusted_weights[strategy] / total_weight, 4)

        return adjusted_weights

    def _estimate_risk_reduction(self, returns_df: pd.DataFrame, optimal_weights: Dict[str, float]) -> float:
        """估算风险降低程度

        Args:
            returns_df: 收益率DataFrame
            optimal_weights: 最优权重

        Returns:
            float: 风险降低比例 0-1
        """
        if not optimal_weights or returns_df.empty:
            return 0.0

        strategies = list(optimal_weights.keys())

        # 计算等权重组合的风险
        equal_weights = {s: 1.0 / len(strategies) for s in strategies}
        equal_portfolio_returns = sum(returns_df[s] * w for s, w in equal_weights.items())
        np.std(equal_portfolio_returns)

        # 计算最优权重组合的风险
        optimal_portfolio_returns = sum(returns_df[s] * w for s, w in optimal_weights.items())
        optimal_risk = np.std(optimal_portfolio_returns)

        # 计算单策略平均风险
        avg_single_risk = np.mean([np.std(returns_df[s]) for s in strategies])

        if avg_single_risk > 0:
            # 风险降低 = (单策略平均风险 - 组合风险) / 单策略平均风险
            risk_reduction = (avg_single_risk - optimal_risk) / avg_single_risk
            return round(max(0, min(1, risk_reduction)), 4)

        return 0.0

    def _matrix_to_dict(self, correlation_matrix: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """将相关性矩阵转换为字典格式

        Args:
            correlation_matrix: 相关性矩阵DataFrame

        Returns:
            Dict[str, Dict[str, float]]: 嵌套字典格式的相关性矩阵
        """
        result = {}
        for strategy1 in correlation_matrix.columns:
            result[strategy1] = {}
            for strategy2 in correlation_matrix.columns:
                result[strategy1][strategy2] = round(float(correlation_matrix.loc[strategy1, strategy2]), 4)
        return result
