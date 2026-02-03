"""情绪与行为因子挖掘器

白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

本模块实现基于市场情绪和投资者行为的因子挖掘，增强市场情绪和行为分析能力。

Author: MIA Team
Date: 2026-01-25
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.genetic_miner import GeneticMiner, Individual
from src.evolution.sentiment_behavior.sentiment_behavior_operators import SentimentBehaviorOperatorRegistry


@dataclass
class SentimentBehaviorConfig:
    """情绪与行为配置

    白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

    Attributes:
        panic_threshold: 恐慌阈值 [0, 1]
        herding_threshold: 羊群效应阈值 [0, 1]
        sentiment_window: 情绪计算窗口
        fear_greed_neutral: 恐惧贪婪中性值
    """

    panic_threshold: float = 0.7
    herding_threshold: float = 0.6
    sentiment_window: int = 20
    fear_greed_neutral: float = 0.0


class SentimentBehaviorFactorMiner(GeneticMiner):
    """情绪与行为因子挖掘器

    白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

    使用遗传算法挖掘基于市场情绪和投资者行为的有效因子。支持12种核心情绪行为算子：
    1. retail_panic_index - 散户恐慌指数
    2. institutional_herding - 机构羊群效应
    3. analyst_revision_momentum - 分析师修正动量
    4. insider_trading_signal - 内部交易信号
    5. short_interest_squeeze - 空头挤压
    6. options_sentiment_skew - 期权情绪偏斜
    7. social_media_buzz - 社交媒体热度
    8. news_tone_shift - 新闻基调转变
    9. earnings_call_sentiment - 财报电话会情绪
    10. ceo_confidence_index - CEO信心指数
    11. market_attention_allocation - 市场注意力分配
    12. fear_greed_oscillator - 恐惧贪婪振荡器

    应用场景：
    - 市场情绪监控
    - 反向投资策略
    - 事件驱动交易

    Attributes:
        config: 情绪与行为配置
        operator_registry: 情绪行为算子注册表
        sentiment_signals: 情绪信号记录
    """

    def __init__(self, config: Optional[SentimentBehaviorConfig] = None, evolution_config: Optional[Any] = None):
        """初始化情绪与行为因子挖掘器

        Args:
            config: 情绪与行为配置
            evolution_config: 遗传算法配置（EvolutionConfig对象）

        Raises:
            ValueError: 当配置参数不合法时
        """
        # 初始化基类
        super().__init__(config=evolution_config)

        # 初始化情绪行为配置（存储为sentiment_config，不覆盖self.config）
        if config is None:
            config = SentimentBehaviorConfig()

        self.sentiment_config = config

        # 验证配置
        self._validate_config()

        # 初始化算子注册表
        self.operator_registry = SentimentBehaviorOperatorRegistry()

        # 扩展算子白名单（添加情绪行为算子）
        self._extend_operator_whitelist()

        # 初始化情绪信号记录
        self.sentiment_signals: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(
            f"初始化SentimentBehaviorFactorMiner: "
            f"panic_threshold={self.sentiment_config.panic_threshold}, "
            f"herding_threshold={self.sentiment_config.herding_threshold}"
        )

    def _validate_config(self) -> None:
        """验证配置参数

        Raises:
            ValueError: 当配置参数不合法时
        """
        if not 0 <= self.sentiment_config.panic_threshold <= 1:
            raise ValueError(f"panic_threshold必须在[0, 1]范围内，" f"当前: {self.sentiment_config.panic_threshold}")

        if not 0 <= self.sentiment_config.herding_threshold <= 1:
            raise ValueError(
                f"herding_threshold必须在[0, 1]范围内，" f"当前: {self.sentiment_config.herding_threshold}"
            )

        if self.sentiment_config.sentiment_window <= 0:
            raise ValueError(f"sentiment_window必须 > 0，" f"当前: {self.sentiment_config.sentiment_window}")

        if not -1 <= self.sentiment_config.fear_greed_neutral <= 1:
            raise ValueError(
                f"fear_greed_neutral必须在[-1, 1]范围内，" f"当前: {self.sentiment_config.fear_greed_neutral}"
            )

    def _extend_operator_whitelist(self) -> None:
        """扩展算子白名单

        将情绪行为专用算子添加到遗传算法的算子白名单中
        """
        sentiment_behavior_operators = [
            "retail_panic_index",
            "institutional_herding",
            "analyst_revision_momentum",
            "insider_trading_signal",
            "short_interest_squeeze",
            "options_sentiment_skew",
            "social_media_buzz",
            "news_tone_shift",
            "earnings_call_sentiment",
            "ceo_confidence_index",
            "market_attention_allocation",
            "fear_greed_oscillator",
        ]

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        self.operator_whitelist.extend(sentiment_behavior_operators)

        logger.debug(f"扩展算子白名单，新增{len(sentiment_behavior_operators)}个情绪行为算子")

    def detect_panic_selling(self, data: pd.DataFrame) -> pd.Series:
        """检测恐慌性抛售

        白皮书依据: 第四章 4.1.8 恐慌性抛售检测

        恐慌性抛售特征：
        1. 散户恐慌指数高
        2. 价格急跌
        3. 成交量激增

        Args:
            data: 市场数据

        Returns:
            恐慌性抛售信号 (1=恐慌抛售, 0=正常)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 计算散户恐慌指数
        panic_index = self.operator_registry.retail_panic_index(data, window=self.sentiment_config.sentiment_window)

        # 检测恐慌阈值
        panic_signal = (panic_index > self.sentiment_config.panic_threshold).astype(int)

        panic_count = panic_signal.sum()
        if panic_count > 0:
            logger.info(f"检测到{panic_count}个恐慌性抛售信号 " f"({panic_count / len(panic_signal) * 100:.1f}%)")

        return panic_signal

    def detect_herding_behavior(self, data: pd.DataFrame) -> pd.Series:
        """检测羊群行为

        白皮书依据: 第四章 4.1.8 羊群行为检测

        羊群行为特征：
        1. 机构羊群效应强
        2. 价格趋势一致
        3. 成交量集中

        Args:
            data: 市场数据

        Returns:
            羊群行为信号 (1=羊群行为, 0=正常)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 计算机构羊群效应
        herding_index = self.operator_registry.institutional_herding(
            data, window=self.sentiment_config.sentiment_window
        )

        # 检测羊群阈值
        herding_signal = (herding_index > self.sentiment_config.herding_threshold).astype(int)

        herding_count = herding_signal.sum()
        if herding_count > 0:
            logger.info(f"检测到{herding_count}个羊群行为信号 " f"({herding_count / len(herding_signal) * 100:.1f}%)")

        return herding_signal

    def analyze_market_sentiment(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """综合分析市场情绪

        白皮书依据: 第四章 4.1.8 市场情绪分析

        综合多个情绪指标：
        1. 恐惧贪婪指数
        2. 散户恐慌指数
        3. 机构羊群效应
        4. 社交媒体热度

        Args:
            data: 市场数据

        Returns:
            情绪指标字典
        """
        if data.empty:
            return {}

        sentiment_indicators = {}

        # 1. 恐惧贪婪指数
        fear_greed = self.operator_registry.fear_greed_oscillator(data, window=self.sentiment_config.sentiment_window)
        sentiment_indicators["fear_greed"] = fear_greed

        # 2. 散户恐慌指数
        panic_index = self.operator_registry.retail_panic_index(data, window=self.sentiment_config.sentiment_window)
        sentiment_indicators["panic"] = panic_index

        # 3. 机构羊群效应
        herding_index = self.operator_registry.institutional_herding(
            data, window=self.sentiment_config.sentiment_window
        )
        sentiment_indicators["herding"] = herding_index

        # 4. 社交媒体热度
        social_buzz = self.operator_registry.social_media_buzz(data, window=self.sentiment_config.sentiment_window)
        sentiment_indicators["social_buzz"] = social_buzz

        logger.debug(
            f"市场情绪分析完成: " f"fear_greed_mean={fear_greed.mean():.4f}, " f"panic_mean={panic_index.mean():.4f}"
        )

        return sentiment_indicators

    def calculate_sentiment_composite_score(self, data: pd.DataFrame) -> pd.Series:
        """计算情绪综合评分

        白皮书依据: 第四章 4.1.8 情绪综合评分

        综合多个情绪指标计算总体情绪评分：
        - 正值：乐观情绪
        - 负值：悲观情绪

        Args:
            data: 市场数据

        Returns:
            情绪综合评分 (-1到1)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 获取所有情绪指标
        sentiment_indicators = self.analyze_market_sentiment(data)

        if not sentiment_indicators:
            return pd.Series(0, index=data.index)

        # 加权平均计算综合评分
        weights = {
            "fear_greed": 0.3,
            "panic": -0.2,  # 恐慌是负面情绪
            "herding": -0.1,  # 羊群效应可能导致泡沫
            "social_buzz": 0.2,
        }

        composite_score = pd.Series(0.0, index=data.index)
        total_weight = 0.0

        for indicator_name, weight in weights.items():
            if indicator_name in sentiment_indicators:
                indicator = sentiment_indicators[indicator_name]
                # 归一化到[-1, 1]
                indicator_norm = (indicator - indicator.mean()) / (indicator.std() + 1e-8)
                indicator_norm = indicator_norm.clip(-3, 3) / 3
                composite_score += indicator_norm * weight
                total_weight += abs(weight)

        if total_weight > 0:
            composite_score /= total_weight

        logger.debug(f"情绪综合评分: mean={composite_score.mean():.4f}, " f"std={composite_score.std():.4f}")

        return composite_score

    async def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Individual]:
        """挖掘情绪与行为因子

        白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘

        完整流程：
        1. 数据验证
        2. 初始化种群
        3. 适应度评估
        4. 遗传进化
        5. 返回最优因子

        Args:
            data: 市场数据
            returns: 收益率数据
            generations: 进化代数

        Returns:
            最优因子列表

        Raises:
            ValueError: 当数据格式不正确时
        """
        logger.info(f"开始挖掘情绪与行为因子: " f"进化代数={generations}")

        # 1. 数据验证
        if data.empty:
            raise ValueError("输入数据为空")

        # 2. 初始化种群
        await self.initialize_population(data_columns=data.columns.tolist())

        # 3. 适应度评估
        await self.evaluate_fitness(data, returns)

        # 4. 遗传进化
        best_individual = await self.evolve(data=data, returns=returns, generations=generations)

        # 5. 返回最优因子
        logger.info(f"情绪与行为因子挖掘完成，" f"最优因子适应度: {best_individual.fitness:.4f}")

        return self.population[:10]  # 返回前10个最优因子

    def get_sentiment_report(self) -> Dict[str, Any]:
        """获取情绪信号报告

        Returns:
            情绪信号报告字典
        """
        total_signals = sum(len(signals) for signals in self.sentiment_signals.values())

        return {
            "total_sentiment_signals": total_signals,
            "signals_by_type": {signal_type: len(signals) for signal_type, signals in self.sentiment_signals.items()},
            "panic_threshold": self.sentiment_config.panic_threshold,
            "herding_threshold": self.sentiment_config.herding_threshold,
            "sentiment_window": self.sentiment_config.sentiment_window,
            "fear_greed_neutral": self.sentiment_config.fear_greed_neutral,
        }
