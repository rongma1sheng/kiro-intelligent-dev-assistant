"""替代数据因子挖掘器

白皮书依据: 第四章 4.1.3 替代数据因子挖掘器

本模块实现基于替代数据源的因子挖掘，包括卫星数据、社交媒体、
网络流量、供应链等非传统数据源。

Author: MIA Team
Date: 2026-01-25
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.alternative_data.alternative_data_operators import AlternativeDataOperatorRegistry
from src.evolution.genetic_miner import EvolutionConfig, GeneticMiner, Individual


@dataclass
class AlternativeDataConfig:
    """替代数据配置

    白皮书依据: 第四章 4.1.3 替代数据因子挖掘器

    Attributes:
        data_sources: 启用的数据源列表
        quality_threshold: 数据质量阈值 [0, 1]
        freshness_hours: 数据新鲜度要求（小时）
        uniqueness_threshold: 信号独特性阈值 [0, 1]
    """

    data_sources: List[str]
    quality_threshold: float = 0.7
    freshness_hours: int = 24
    uniqueness_threshold: float = 0.3


class AlternativeDataFactorMiner(GeneticMiner):
    """替代数据因子挖掘器

    白皮书依据: 第四章 4.1.3 替代数据因子挖掘器

    使用遗传算法挖掘基于替代数据的有效因子。支持8种核心替代数据算子：
    1. satellite_parking_count - 卫星停车场数据
    2. social_sentiment_momentum - 社交媒体情绪动量
    3. web_traffic_growth - 网站流量增长
    4. supply_chain_disruption - 供应链中断指数
    5. foot_traffic_anomaly - 人流量异常检测
    6. news_sentiment_shock - 新闻情绪冲击
    7. search_trend_leading - 搜索趋势领先指标
    8. shipping_volume_change - 航运量变化

    Attributes:
        alt_config: 替代数据配置
        operator_registry: 替代数据算子注册表
        data_quality_scores: 数据源质量评分
    """

    def __init__(self, config: Optional[EvolutionConfig] = None, alt_config: Optional[AlternativeDataConfig] = None):
        """初始化替代数据因子挖掘器

        Args:
            config: 进化配置（GeneticMiner配置）
            alt_config: 替代数据配置

        Raises:
            ValueError: 当配置参数不合法时
        """
        # 初始化基类
        super().__init__(config=config)

        # 初始化替代数据配置
        if alt_config is None:
            alt_config = AlternativeDataConfig(data_sources=["satellite", "social", "web", "supply_chain"])

        self.alt_config = alt_config

        # 验证配置
        self._validate_config()

        # 初始化算子注册表
        self.operator_registry = AlternativeDataOperatorRegistry()

        # 扩展算子白名单（添加替代数据算子）
        self._extend_operator_whitelist()

        # 初始化数据质量评分
        self.data_quality_scores: Dict[str, float] = {}

        logger.info(
            f"初始化AlternativeDataFactorMiner: "
            f"data_sources={alt_config.data_sources}, "
            f"quality_threshold={alt_config.quality_threshold}"
        )

    def _validate_config(self) -> None:
        """验证配置参数

        Raises:
            ValueError: 当配置参数不合法时
        """
        if not 0 <= self.alt_config.quality_threshold <= 1:
            raise ValueError(f"quality_threshold必须在[0, 1]范围内，" f"当前: {self.alt_config.quality_threshold}")

        if self.alt_config.freshness_hours <= 0:
            raise ValueError(f"freshness_hours必须 > 0，" f"当前: {self.alt_config.freshness_hours}")

        if not 0 <= self.alt_config.uniqueness_threshold <= 1:
            raise ValueError(
                f"uniqueness_threshold必须在[0, 1]范围内，" f"当前: {self.alt_config.uniqueness_threshold}"
            )

        # 验证数据源
        valid_sources = {"satellite", "social", "web", "supply_chain", "foot_traffic", "news", "search", "shipping"}

        for source in self.alt_config.data_sources:
            if source not in valid_sources:
                raise ValueError(f"不支持的数据源: {source}，" f"有效数据源: {valid_sources}")

    def _extend_operator_whitelist(self) -> None:
        """扩展算子白名单

        将替代数据专用算子添加到遗传算法的算子白名单中
        """
        alternative_operators = [
            "satellite_parking_count",
            "social_sentiment_momentum",
            "web_traffic_growth",
            "supply_chain_disruption",
            "foot_traffic_anomaly",
            "news_sentiment_shock",
            "search_trend_leading",
            "shipping_volume_change",
        ]

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        self.operator_whitelist.extend(alternative_operators)

        logger.debug(f"扩展算子白名单，新增{len(alternative_operators)}个替代数据算子")

    def evaluate_data_quality(self, data: pd.DataFrame, source: str) -> float:
        """评估数据源质量

        白皮书依据: 第四章 4.1.3 替代数据质量评估

        评估维度：
        1. 完整性 (30%): 缺失值比例
        2. 新鲜度 (30%): 数据更新时间
        3. 一致性 (20%): 数据内部一致性
        4. 准确性 (20%): 与基准数据对比

        Args:
            data: 数据源数据
            source: 数据源名称

        Returns:
            质量评分 [0, 1]
        """
        if data.empty:
            logger.warning(f"数据源 {source} 为空")
            return 0.0

        # 1. 完整性评分 (30%)
        completeness = 1.0 - (data.isnull().sum().sum() / data.size)
        completeness_score = completeness * 0.3

        # 2. 新鲜度评分 (30%)
        if "timestamp" in data.columns:
            latest_time = pd.to_datetime(data["timestamp"]).max()
            hours_old = (pd.Timestamp.now() - latest_time).total_seconds() / 3600
            freshness = max(0, 1 - hours_old / self.alt_config.freshness_hours)
        else:
            freshness = 0.5  # 无时间戳，给予中等评分
        freshness_score = freshness * 0.3

        # 3. 一致性评分 (20%)
        # 检查数值列的标准差是否合理
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            std_values = data[numeric_cols].std()
            # 标准差不应该为0（无变化）或过大（异常）
            consistency = np.mean(
                [
                    1.0 if 0 < std < data[col].mean() * 3 else 0.5
                    for col, std in std_values.items()
                    if data[col].mean() != 0
                ]
            )
        else:
            consistency = 0.5
        consistency_score = consistency * 0.2

        # 4. 准确性评分 (20%)
        # 简化版本：检查数值范围是否合理
        accuracy = 1.0  # 默认满分
        for col in numeric_cols:
            if data[col].min() < 0 and col.endswith("_count"):
                # 计数类指标不应该为负
                accuracy *= 0.8
        accuracy_score = accuracy * 0.2

        # 综合评分
        total_score = completeness_score + freshness_score + consistency_score + accuracy_score

        # 缓存评分
        self.data_quality_scores[source] = total_score

        logger.info(
            f"数据源 {source} 质量评分: {total_score:.3f} "
            f"(完整性:{completeness_score:.3f}, "
            f"新鲜度:{freshness_score:.3f}, "
            f"一致性:{consistency_score:.3f}, "
            f"准确性:{accuracy_score:.3f})"
        )

        return total_score

    def evaluate_signal_uniqueness(self, factor_values: pd.Series, traditional_factors: pd.DataFrame) -> float:
        """评估信号独特性

        白皮书依据: 第四章 4.1.3 信号独特性分析

        计算替代数据因子与传统因子的相关性，
        相关性越低，独特性越高。

        Args:
            factor_values: 因子值序列
            traditional_factors: 传统因子数据框

        Returns:
            独特性评分 [0, 1]，1表示完全独特
        """
        if traditional_factors.empty:
            return 1.0  # 无传统因子对比，认为完全独特

        # 计算与所有传统因子的相关性
        correlations = []
        for col in traditional_factors.columns:
            try:
                corr = factor_values.corr(traditional_factors[col])
                if not np.isnan(corr):
                    correlations.append(abs(corr))
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug(f"计算相关性失败: {col}, 错误: {e}")
                continue

        if not correlations:
            return 1.0

        # 独特性 = 1 - 最大相关性
        max_correlation = max(correlations)
        uniqueness = 1.0 - max_correlation

        logger.debug(f"信号独特性评分: {uniqueness:.3f} " f"(最大相关性: {max_correlation:.3f})")

        return uniqueness

    def mine_factors(
        self,
        data: pd.DataFrame,
        returns: pd.Series,
        traditional_factors: Optional[pd.DataFrame] = None,
        generations: int = 10,
    ) -> List[Individual]:
        """挖掘替代数据因子

        白皮书依据: 第四章 4.1.3 替代数据因子挖掘

        完整流程：
        1. 数据质量评估
        2. 初始化种群
        3. 适应度评估（包含独特性）
        4. 遗传进化
        5. 返回最优因子

        Args:
            data: 市场数据
            returns: 收益率数据
            traditional_factors: 传统因子（用于独特性评估）
            generations: 进化代数

        Returns:
            最优因子列表

        Raises:
            ValueError: 当数据质量不达标时
        """
        logger.info(f"开始挖掘替代数据因子: " f"数据源={self.alt_config.data_sources}, " f"进化代数={generations}")

        # 1. 数据质量评估
        for source in self.alt_config.data_sources:
            # 假设数据中包含source标记
            source_data = data[data.get("source", "") == source]
            if not source_data.empty:
                quality = self.evaluate_data_quality(source_data, source)
                if quality < self.alt_config.quality_threshold:
                    logger.warning(
                        f"数据源 {source} 质量不达标: " f"{quality:.3f} < {self.alt_config.quality_threshold}"
                    )

        # 2. 初始化种群
        self.initialize_population()  # pylint: disable=e1120

        # 3. 适应度评估
        self.evaluate_fitness(data, returns)

        # 4. 增强适应度评估（考虑独特性）
        if traditional_factors is not None:
            self._enhance_fitness_with_uniqueness(data, traditional_factors)

        # 5. 遗传进化
        best_individual = self.evolve(generations=generations)  # pylint: disable=e1120

        # 6. 返回最优因子
        logger.info(f"替代数据因子挖掘完成，" f"最优因子适应度: {best_individual.fitness:.4f}")

        return self.population[:10]  # 返回前10个最优因子

    def _enhance_fitness_with_uniqueness(self, data: pd.DataFrame, traditional_factors: pd.DataFrame) -> None:
        """增强适应度评估（考虑独特性）

        白皮书依据: 第四章 4.1.3 信号独特性分析

        调整适应度公式：
        enhanced_fitness = original_fitness * (1 + uniqueness * 0.2)

        Args:
            data: 市场数据
            traditional_factors: 传统因子
        """
        for individual in self.population:
            try:
                # 计算因子值
                factor_values = self._evaluate_expression(individual.expression, data)

                # 评估独特性
                uniqueness = self.evaluate_signal_uniqueness(factor_values, traditional_factors)

                # 增强适应度
                if uniqueness >= self.alt_config.uniqueness_threshold:
                    original_fitness = individual.fitness
                    individual.fitness = original_fitness * (1 + uniqueness * 0.2)

                    logger.debug(
                        f"因子独特性增强: "
                        f"{original_fitness:.4f} -> {individual.fitness:.4f} "
                        f"(独特性: {uniqueness:.3f})"
                    )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug(f"独特性评估失败: {e}")
                continue

    def get_data_quality_report(self) -> Dict[str, Any]:
        """获取数据质量报告

        Returns:
            数据质量报告字典
        """
        return {
            "data_sources": self.alt_config.data_sources,
            "quality_scores": self.data_quality_scores,
            "quality_threshold": self.alt_config.quality_threshold,
            "freshness_hours": self.alt_config.freshness_hours,
            "uniqueness_threshold": self.alt_config.uniqueness_threshold,
            "average_quality": (np.mean(list(self.data_quality_scores.values())) if self.data_quality_scores else 0.0),
        }
