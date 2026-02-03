"""Correlation Analyzer for Factor Redundancy Detection

白皮书依据: 第四章 4.2.2 因子相关性分析
"""

from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.data_models import FactorTestResult
from src.evolution.converter.data_models import FactorCorrelationMatrix


class CorrelationAnalyzer:
    """Analyzes factor correlations to avoid redundancy

    白皮书依据: 第四章 4.2.2 因子相关性分析

    This class calculates correlation matrices between factors and identifies
    highly correlated factor pairs to avoid redundancy in multi-factor strategies.

    Attributes:
        correlation_threshold: Threshold for high correlation (default 0.7)
    """

    def __init__(self, correlation_threshold: float = 0.7):
        """Initialize correlation analyzer

        Args:
            correlation_threshold: Threshold for high correlation (0-1)

        Raises:
            ValueError: If threshold not in valid range
        """
        if not 0.0 <= correlation_threshold <= 1.0:
            raise ValueError(f"Correlation threshold must be in [0, 1], got {correlation_threshold}")

        self.correlation_threshold = correlation_threshold
        logger.info(f"Initialized CorrelationAnalyzer with threshold={correlation_threshold}")

    async def calculate_correlation_matrix(
        self, factor_results: List[FactorTestResult], factor_values: Dict[str, pd.Series]
    ) -> FactorCorrelationMatrix:
        """Calculate correlation matrix between factors

        白皮书依据: 第四章 4.2.2 因子相关性计算

        Args:
            factor_results: List of factor test results
            factor_values: Dictionary mapping factor_id to factor value series

        Returns:
            FactorCorrelationMatrix object

        Raises:
            ValueError: If inputs are invalid or empty
        """
        if not factor_results:
            raise ValueError("Factor results cannot be empty")

        if not factor_values:
            raise ValueError("Factor values cannot be empty")

        factor_ids = [result.factor_id for result in factor_results]

        # Verify all factor IDs have values
        missing_ids = set(factor_ids) - set(factor_values.keys())
        if missing_ids:
            raise ValueError(f"Missing factor values for IDs: {missing_ids}")

        logger.info(f"Calculating correlation matrix for {len(factor_ids)} factors")

        # Build DataFrame with all factor values
        factor_df = pd.DataFrame({factor_id: factor_values[factor_id] for factor_id in factor_ids})

        # Calculate correlation matrix
        corr_matrix = factor_df.corr(method="spearman").values

        # Handle NaN values (replace with 0)
        corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

        correlation_matrix = FactorCorrelationMatrix(factor_ids=factor_ids, correlation_matrix=corr_matrix)

        logger.info(
            f"Correlation matrix calculated: shape={corr_matrix.shape}, "
            f"mean_abs_corr={np.abs(corr_matrix[np.triu_indices_from(corr_matrix, k=1)]).mean():.4f}"
        )

        return correlation_matrix

    async def filter_redundant_factors(
        self, factor_results: List[FactorTestResult], correlation_matrix: FactorCorrelationMatrix
    ) -> List[str]:
        """Filter out redundant factors based on correlation

        白皮书依据: 第四章 4.2.2 冗余因子过滤

        When two factors are highly correlated, keep the one with higher Arena score.

        Args:
            factor_results: List of factor test results
            correlation_matrix: Factor correlation matrix

        Returns:
            List of non-redundant factor IDs

        Raises:
            ValueError: If inputs are invalid
        """
        if not factor_results:
            raise ValueError("Factor results cannot be empty")

        logger.info(f"Filtering redundant factors with threshold={self.correlation_threshold}")

        # Build factor score map
        factor_scores = {result.factor_id: result.overall_score for result in factor_results}

        # Get highly correlated pairs
        high_corr_pairs = correlation_matrix.get_highly_correlated_pairs(threshold=self.correlation_threshold)

        logger.info(f"Found {len(high_corr_pairs)} highly correlated factor pairs")

        # Track factors to remove
        factors_to_remove = set()

        for factor_id1, factor_id2, corr in high_corr_pairs:
            # Skip if either factor already marked for removal
            if factor_id1 in factors_to_remove or factor_id2 in factors_to_remove:
                continue

            # Keep factor with higher Arena score
            score1 = factor_scores.get(factor_id1, 0.0)
            score2 = factor_scores.get(factor_id2, 0.0)

            if score1 >= score2:
                factors_to_remove.add(factor_id2)
                logger.debug(
                    f"Removing {factor_id2} (score={score2:.4f}) "
                    f"due to high correlation ({corr:.4f}) with "
                    f"{factor_id1} (score={score1:.4f})"
                )
            else:
                factors_to_remove.add(factor_id1)
                logger.debug(
                    f"Removing {factor_id1} (score={score1:.4f}) "
                    f"due to high correlation ({corr:.4f}) with "
                    f"{factor_id2} (score={score2:.4f})"
                )

        # Return non-redundant factors
        non_redundant = [factor_id for factor_id in correlation_matrix.factor_ids if factor_id not in factors_to_remove]

        logger.info(
            f"Filtered {len(factors_to_remove)} redundant factors, " f"kept {len(non_redundant)} non-redundant factors"
        )

        return non_redundant

    async def select_diverse_factors(
        self, factor_results: List[FactorTestResult], correlation_matrix: FactorCorrelationMatrix, max_factors: int = 5
    ) -> List[str]:
        """Select diverse factors for combination strategy

        白皮书依据: 第四章 4.2.2 多样化因子选择

        Selects factors with low mutual correlation and high Arena scores.

        Args:
            factor_results: List of factor test results
            correlation_matrix: Factor correlation matrix
            max_factors: Maximum number of factors to select

        Returns:
            List of selected factor IDs

        Raises:
            ValueError: If inputs are invalid
        """
        if not factor_results:
            raise ValueError("Factor results cannot be empty")

        if max_factors < 1:
            raise ValueError(f"Max factors must be >= 1, got {max_factors}")

        logger.info(f"Selecting up to {max_factors} diverse factors")

        # Sort factors by Arena score (descending)
        sorted_factors = sorted(factor_results, key=lambda x: x.overall_score, reverse=True)

        selected_ids = []

        for factor_result in sorted_factors:
            if len(selected_ids) >= max_factors:
                break

            factor_id = factor_result.factor_id

            # Check correlation with already selected factors
            is_diverse = True
            for selected_id in selected_ids:
                corr = abs(correlation_matrix.get_correlation(factor_id, selected_id))
                if corr >= self.correlation_threshold:
                    is_diverse = False
                    logger.debug(f"Skipping {factor_id} due to high correlation " f"({corr:.4f}) with {selected_id}")
                    break

            if is_diverse:
                selected_ids.append(factor_id)
                logger.debug(f"Selected {factor_id} (score={factor_result.overall_score:.4f})")

        logger.info(f"Selected {len(selected_ids)} diverse factors: {selected_ids}")

        return selected_ids

    async def calculate_factor_weights(
        self, factor_results: List[FactorTestResult], selected_factor_ids: List[str]
    ) -> Dict[str, float]:
        """Calculate weights for selected factors

        白皮书依据: 第四章 4.2.2 因子权重计算

        Weights are proportional to Arena scores, normalized to sum to 1.0.

        Args:
            factor_results: List of factor test results
            selected_factor_ids: List of selected factor IDs

        Returns:
            Dictionary mapping factor_id to weight

        Raises:
            ValueError: If inputs are invalid
        """
        if not factor_results:
            raise ValueError("Factor results cannot be empty")

        if not selected_factor_ids:
            raise ValueError("Selected factor IDs cannot be empty")

        logger.info(f"Calculating weights for {len(selected_factor_ids)} factors")

        # Build score map
        score_map = {result.factor_id: result.overall_score for result in factor_results}

        # Calculate weights proportional to scores
        scores = [score_map[factor_id] for factor_id in selected_factor_ids]
        total_score = sum(scores)

        if total_score == 0:
            # Equal weights if all scores are zero
            weights = {factor_id: 1.0 / len(selected_factor_ids) for factor_id in selected_factor_ids}
        else:
            weights = {factor_id: score / total_score for factor_id, score in zip(selected_factor_ids, scores)}

        logger.info(f"Calculated factor weights: {weights}")

        return weights
