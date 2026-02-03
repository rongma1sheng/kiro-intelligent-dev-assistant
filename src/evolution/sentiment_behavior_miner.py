"""情绪与行为因子挖掘器

白皮书依据: 第四章 4.1.7 情绪与行为因子挖掘
需求: 6.1-6.14

实现12个情绪行为算子，NLP情绪分析，行为模式识别，
数据新鲜度监控（>1小时标记过期）。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class SentimentData:
    """情绪数据

    Attributes:
        timestamp: 时间戳
        symbol: 股票代码
        source: 数据源（news/social/analyst/insider）
        sentiment_score: 情绪评分（-1到1）
        volume: 数据量（文章数、帖子数等）
        keywords: 关键词列表
    """

    timestamp: datetime
    symbol: str
    source: str
    sentiment_score: float
    volume: int
    keywords: List[str]

    def is_fresh(self, max_age_hours: float = 1.0) -> bool:
        """检查数据是否新鲜

        需求: 6.14 - 数据延迟>1小时标记过期

        Args:
            max_age_hours: 最大年龄（小时）

        Returns:
            是否新鲜
        """
        age = (datetime.now() - self.timestamp).total_seconds() / 3600.0
        return age <= max_age_hours


@dataclass
class BehaviorData:
    """行为数据

    Attributes:
        timestamp: 时间戳
        symbol: 股票代码
        behavior_type: 行为类型（retail/institutional/insider）
        action: 动作（buy/sell/hold）
        volume: 交易量
        price: 价格
    """

    timestamp: datetime
    symbol: str
    behavior_type: str
    action: str
    volume: float
    price: float


class SentimentBehaviorFactorMiner:
    """情绪与行为因子挖掘器

    白皮书依据: 第四章 4.1.7 情绪与行为因子挖掘
    需求: 6.1-6.14

    实现12个情绪行为算子：
    1. retail_panic_index: 散户恐慌指数
    2. institutional_herding: 机构羊群效应
    3. analyst_revision_momentum: 分析师修正动量
    4. insider_trading_signal: 内部交易信号
    5. short_interest_squeeze: 空头挤压
    6. options_sentiment_skew: 期权情绪偏斜
    7. social_media_buzz: 社交媒体热度
    8. news_tone_shift: 新闻基调转变
    9. earnings_call_sentiment: 财报电话会议情绪
    10. ceo_confidence_index: CEO信心指数
    11. market_attention_allocation: 市场注意力分配
    12. fear_greed_oscillator: 恐惧贪婪振荡器

    数据新鲜度监控: >1小时标记过期

    Attributes:
        operators: 算子字典
        sentiment_cache: 情绪数据缓存
        behavior_cache: 行为数据缓存
        freshness_threshold: 新鲜度阈值（小时）
    """

    def __init__(self, freshness_threshold: float = 1.0, cache_size: int = 10000):
        """初始化情绪与行为因子挖掘器

        Args:
            freshness_threshold: 新鲜度阈值（小时），默认1.0
            cache_size: 缓存大小

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if freshness_threshold <= 0:
            raise ValueError(f"新鲜度阈值必须 > 0，当前: {freshness_threshold}")

        if cache_size <= 0:
            raise ValueError(f"缓存大小必须 > 0，当前: {cache_size}")

        self.freshness_threshold = freshness_threshold
        self.cache_size = cache_size

        # 初始化算子
        self.operators = self._initialize_operators()

        # 初始化缓存
        self.sentiment_cache: List[SentimentData] = []
        self.behavior_cache: List[BehaviorData] = []

        # 数据新鲜度统计
        self.freshness_stats = {"total_checks": 0, "stale_data_count": 0, "stale_data_ratio": 0.0}

        logger.info(
            f"初始化SentimentBehaviorFactorMiner: "
            f"freshness_threshold={freshness_threshold}h, "
            f"cache_size={cache_size}"
        )

        # 健康状态跟踪
        self._is_healthy = True
        self._error_count = 0

    def is_healthy(self) -> bool:
        """检查挖掘器健康状态

        Returns:
            是否健康
        """
        return self._is_healthy and self._error_count < 5

    def get_metadata(self) -> Dict:
        """获取挖掘器元数据

        Returns:
            元数据字典
        """
        return {
            "miner_type": "sentiment",
            "miner_name": "SentimentBehaviorFactorMiner",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "freshness_threshold": self.freshness_threshold,
            "cache_size": self.cache_size,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化12个情绪行为算子

        白皮书依据: 第四章 4.1.7
        需求: 6.1-6.13

        Returns:
            算子字典
        """
        return {
            "retail_panic_index": self._retail_panic_index,
            "institutional_herding": self._institutional_herding,
            "analyst_revision_momentum": self._analyst_revision_momentum,
            "insider_trading_signal": self._insider_trading_signal,
            "short_interest_squeeze": self._short_interest_squeeze,
            "options_sentiment_skew": self._options_sentiment_skew,
            "social_media_buzz": self._social_media_buzz,
            "news_tone_shift": self._news_tone_shift,
            "earnings_call_sentiment": self._earnings_call_sentiment,
            "ceo_confidence_index": self._ceo_confidence_index,
            "market_attention_allocation": self._market_attention_allocation,
            "fear_greed_oscillator": self._fear_greed_oscillator,
        }

    def mine_factors(
        self, sentiment_data: List[SentimentData], behavior_data: List[BehaviorData], symbols: List[str]
    ) -> pd.DataFrame:
        """挖掘情绪与行为因子

        白皮书依据: 第四章 4.1.7
        需求: 6.1-6.14

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            因子数据框，索引为股票代码，列为因子名称

        Raises:
            ValueError: 当输入数据无效时
        """
        if not sentiment_data:
            raise ValueError("情绪数据不能为空")

        if not behavior_data:
            raise ValueError("行为数据不能为空")

        if not symbols:
            raise ValueError("股票代码列表不能为空")

        logger.info(
            f"开始挖掘情绪与行为因子: "
            f"sentiment_data={len(sentiment_data)}, "
            f"behavior_data={len(behavior_data)}, "
            f"symbols={len(symbols)}"
        )

        # 检查数据新鲜度
        self._check_data_freshness(sentiment_data)

        # 更新缓存
        self.sentiment_cache.extend(sentiment_data)
        self.behavior_cache.extend(behavior_data)

        # 限制缓存大小
        if len(self.sentiment_cache) > self.cache_size:
            self.sentiment_cache = self.sentiment_cache[-self.cache_size :]
        if len(self.behavior_cache) > self.cache_size:
            self.behavior_cache = self.behavior_cache[-self.cache_size :]

        # 计算所有因子
        factors = {}
        for operator_name, operator_func in self.operators.items():
            try:
                factor_values = operator_func(sentiment_data, behavior_data, symbols)
                factors[operator_name] = factor_values
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"算子 {operator_name} 执行失败: {e}")
                factors[operator_name] = pd.Series(0.0, index=symbols)

        # 构建因子数据框
        factor_df = pd.DataFrame(factors, index=symbols)

        logger.info(
            f"情绪与行为因子挖掘完成: "
            f"factors={len(factors)}, "
            f"stale_ratio={self.freshness_stats['stale_data_ratio']:.2%}"
        )

        return factor_df

    def _check_data_freshness(self, sentiment_data: List[SentimentData]):
        """检查数据新鲜度

        需求: 6.14 - 数据延迟>1小时标记过期

        Args:
            sentiment_data: 情绪数据列表
        """
        stale_count = 0

        for data in sentiment_data:
            self.freshness_stats["total_checks"] += 1

            if not data.is_fresh(self.freshness_threshold):
                stale_count += 1
                self.freshness_stats["stale_data_count"] += 1
                logger.warning(
                    f"数据过期: symbol={data.symbol}, "
                    f"source={data.source}, "
                    f"age={(datetime.now() - data.timestamp).total_seconds() / 3600.0:.2f}h"
                )

        # 更新过期比率
        if self.freshness_stats["total_checks"] > 0:
            self.freshness_stats["stale_data_ratio"] = (
                self.freshness_stats["stale_data_count"] / self.freshness_stats["total_checks"]
            )

    def _retail_panic_index(
        self,
        sentiment_data: List[SentimentData],  # pylint: disable=unused-argument
        behavior_data: List[BehaviorData],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算散户恐慌指数

        白皮书依据: 第四章 4.1.7
        需求: 6.1

        散户恐慌指数 = 散户卖出压力 / 总交易量

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            散户恐慌指数因子
        """
        panic_indices = {}

        for symbol in symbols:
            # 筛选散户行为数据
            retail_behaviors = [b for b in behavior_data if b.symbol == symbol and b.behavior_type == "retail"]

            if not retail_behaviors:
                panic_indices[symbol] = 0.0
                continue

            # 计算散户卖出压力
            retail_sell_volume = sum(b.volume for b in retail_behaviors if b.action == "sell")

            # 计算总交易量
            total_volume = sum(b.volume for b in retail_behaviors)

            # 计算恐慌指数
            if total_volume > 0:
                panic_index = retail_sell_volume / total_volume
            else:
                panic_index = 0.0

            panic_indices[symbol] = panic_index

        return pd.Series(panic_indices)

    def _institutional_herding(
        self,
        sentiment_data: List[SentimentData],  # pylint: disable=unused-argument
        behavior_data: List[BehaviorData],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """检测机构羊群效应

        白皮书依据: 第四章 4.1.7
        需求: 6.2

        机构羊群效应 = 机构同向交易的集中度

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            机构羊群效应因子
        """
        herding_scores = {}

        for symbol in symbols:
            # 筛选机构行为数据
            institutional_behaviors = [
                b for b in behavior_data if b.symbol == symbol and b.behavior_type == "institutional"
            ]

            if not institutional_behaviors:
                herding_scores[symbol] = 0.0
                continue

            # 计算买入和卖出数量
            buy_count = sum(1 for b in institutional_behaviors if b.action == "buy")
            sell_count = sum(1 for b in institutional_behaviors if b.action == "sell")
            total_count = len(institutional_behaviors)

            # 羊群效应 = |买入比例 - 卖出比例|
            # 高值表示机构行为高度一致
            if total_count > 0:
                buy_ratio = buy_count / total_count
                sell_ratio = sell_count / total_count
                herding_score = abs(buy_ratio - sell_ratio)
            else:
                herding_score = 0.0

            herding_scores[symbol] = herding_score

        return pd.Series(herding_scores)

    def _analyst_revision_momentum(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算分析师修正动量

        白皮书依据: 第四章 4.1.7
        需求: 6.3

        分析师修正动量 = 评级上调数 - 评级下调数

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            分析师修正动量因子
        """
        revision_momentums = {}

        for symbol in symbols:
            # 筛选分析师情绪数据
            analyst_sentiments = [s for s in sentiment_data if s.symbol == symbol and s.source == "analyst"]

            if not analyst_sentiments:
                revision_momentums[symbol] = 0.0
                continue

            # 计算情绪变化
            # 正值表示上调，负值表示下调
            upgrades = sum(1 for s in analyst_sentiments if s.sentiment_score > 0.5)
            downgrades = sum(1 for s in analyst_sentiments if s.sentiment_score < -0.5)

            revision_momentum = upgrades - downgrades

            revision_momentums[symbol] = revision_momentum

        return pd.Series(revision_momentums)

    def _insider_trading_signal(
        self,
        sentiment_data: List[SentimentData],  # pylint: disable=unused-argument
        behavior_data: List[BehaviorData],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """提取内部交易信号

        白皮书依据: 第四章 4.1.7
        需求: 6.4

        内部交易信号 = 内部人买入 - 内部人卖出

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            内部交易信号因子
        """
        insider_signals = {}

        for symbol in symbols:
            # 筛选内部交易数据
            insider_behaviors = [b for b in behavior_data if b.symbol == symbol and b.behavior_type == "insider"]

            if not insider_behaviors:
                insider_signals[symbol] = 0.0
                continue

            # 计算净买入量
            buy_volume = sum(b.volume for b in insider_behaviors if b.action == "buy")
            sell_volume = sum(b.volume for b in insider_behaviors if b.action == "sell")

            net_buy = buy_volume - sell_volume

            insider_signals[symbol] = net_buy

        return pd.Series(insider_signals)

    def _short_interest_squeeze(
        self, sentiment_data: List[SentimentData], behavior_data: List[BehaviorData], symbols: List[str]
    ) -> pd.Series:
        """计算空头挤压概率

        白皮书依据: 第四章 4.1.7
        需求: 6.5

        空头挤压 = 空头比例 × 价格上涨动量

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            空头挤压因子
        """
        squeeze_scores = {}

        for symbol in symbols:
            # 筛选卖空相关情绪数据
            short_sentiments = [s for s in sentiment_data if s.symbol == symbol and "short" in s.keywords]

            # 筛选价格行为数据
            price_behaviors = [b for b in behavior_data if b.symbol == symbol]

            if not short_sentiments or not price_behaviors:
                squeeze_scores[symbol] = 0.0
                continue

            # 估算空头比例（从情绪数据）
            short_ratio = len(short_sentiments) / max(len(sentiment_data), 1)

            # 计算价格动量
            if len(price_behaviors) >= 2:
                recent_price = price_behaviors[-1].price
                old_price = price_behaviors[0].price
                price_momentum = (recent_price - old_price) / old_price if old_price > 0 else 0.0
            else:
                price_momentum = 0.0

            # 空头挤压分数
            squeeze_score = short_ratio * max(0, price_momentum)

            squeeze_scores[symbol] = squeeze_score

        return pd.Series(squeeze_scores)

    def _options_sentiment_skew(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算期权情绪偏斜

        白皮书依据: 第四章 4.1.7
        需求: 6.6

        期权情绪偏斜 = Put/Call比率偏离度

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            期权情绪偏斜因子
        """
        skew_scores = {}

        for symbol in symbols:
            # 筛选期权相关情绪数据
            options_sentiments = [s for s in sentiment_data if s.symbol == symbol and "options" in s.keywords]

            if not options_sentiments:
                skew_scores[symbol] = 0.0
                continue

            # 从情绪数据估算Put/Call比率
            # 负面情绪对应Put，正面情绪对应Call
            put_count = sum(1 for s in options_sentiments if s.sentiment_score < 0)
            call_count = sum(1 for s in options_sentiments if s.sentiment_score > 0)

            if call_count > 0:
                put_call_ratio = put_count / call_count
                # 偏斜度 = 比率偏离1.0的程度
                skew = abs(put_call_ratio - 1.0)
            else:
                skew = 0.0

            skew_scores[symbol] = skew

        return pd.Series(skew_scores)

    def _social_media_buzz(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """量化社交媒体热度

        白皮书依据: 第四章 4.1.7
        需求: 6.7

        社交媒体热度 = 提及量 × 情绪强度

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            社交媒体热度因子
        """
        buzz_scores = {}

        for symbol in symbols:
            # 筛选社交媒体情绪数据
            social_sentiments = [s for s in sentiment_data if s.symbol == symbol and s.source == "social"]

            if not social_sentiments:
                buzz_scores[symbol] = 0.0
                continue

            # 计算总提及量
            total_volume = sum(s.volume for s in social_sentiments)

            # 计算平均情绪强度
            avg_sentiment = np.mean([abs(s.sentiment_score) for s in social_sentiments])

            # 热度 = 提及量 × 情绪强度
            buzz = total_volume * avg_sentiment

            buzz_scores[symbol] = buzz

        return pd.Series(buzz_scores)

    def _news_tone_shift(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """追踪新闻基调转变

        白皮书依据: 第四章 4.1.7
        需求: 6.8

        新闻基调转变 = 当前情绪 - 历史平均情绪

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            新闻基调转变因子
        """
        tone_shifts = {}

        for symbol in symbols:
            # 筛选新闻情绪数据
            news_sentiments = [s for s in sentiment_data if s.symbol == symbol and s.source == "news"]

            if len(news_sentiments) < 2:
                tone_shifts[symbol] = 0.0
                continue

            # 按时间排序
            news_sentiments.sort(key=lambda x: x.timestamp)

            # 计算最近情绪
            recent_sentiment = np.mean([s.sentiment_score for s in news_sentiments[-5:]])

            # 计算历史平均情绪
            historical_sentiment = (
                np.mean([s.sentiment_score for s in news_sentiments[:-5]]) if len(news_sentiments) > 5 else 0.0
            )

            # 基调转变
            tone_shift = recent_sentiment - historical_sentiment

            tone_shifts[symbol] = tone_shift

        return pd.Series(tone_shifts)

    def _earnings_call_sentiment(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """提取财报电话会议情绪

        白皮书依据: 第四章 4.1.7
        需求: 6.9

        财报电话会议情绪 = 管理层语气分析

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            财报电话会议情绪因子
        """
        call_sentiments = {}

        for symbol in symbols:
            # 筛选财报电话会议情绪数据
            earnings_sentiments = [s for s in sentiment_data if s.symbol == symbol and "earnings_call" in s.keywords]

            if not earnings_sentiments:
                call_sentiments[symbol] = 0.0
                continue

            # 使用最新的财报电话会议情绪
            latest_sentiment = max(earnings_sentiments, key=lambda x: x.timestamp).sentiment_score

            call_sentiments[symbol] = latest_sentiment

        return pd.Series(call_sentiments)

    def _ceo_confidence_index(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算CEO信心指数

        白皮书依据: 第四章 4.1.7
        需求: 6.10

        CEO信心指数 = CEO公开声明的情绪分析

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            CEO信心指数因子
        """
        confidence_indices = {}

        for symbol in symbols:
            # 筛选CEO相关情绪数据
            ceo_sentiments = [s for s in sentiment_data if s.symbol == symbol and "ceo" in s.keywords]

            if not ceo_sentiments:
                confidence_indices[symbol] = 0.0
                continue

            # 计算平均信心指数
            avg_confidence = np.mean([s.sentiment_score for s in ceo_sentiments])

            confidence_indices[symbol] = avg_confidence

        return pd.Series(confidence_indices)

    def _market_attention_allocation(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """测量市场注意力分配

        白皮书依据: 第四章 4.1.7
        需求: 6.11

        市场注意力分配 = 该股票的关注度 / 总关注度

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            市场注意力分配因子
        """
        attention_scores = {}

        # 计算总关注度
        total_attention = sum(s.volume for s in sentiment_data)

        for symbol in symbols:
            # 计算该股票的关注度
            symbol_sentiments = [s for s in sentiment_data if s.symbol == symbol]

            symbol_attention = sum(s.volume for s in symbol_sentiments)

            # 注意力分配比例
            if total_attention > 0:
                attention_ratio = symbol_attention / total_attention
            else:
                attention_ratio = 0.0

            attention_scores[symbol] = attention_ratio

        return pd.Series(attention_scores)

    def _fear_greed_oscillator(
        self,
        sentiment_data: List[SentimentData],
        behavior_data: List[BehaviorData],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算恐惧贪婪振荡器

        白皮书依据: 第四章 4.1.7
        需求: 6.12

        恐惧贪婪振荡器 = 综合多个情绪指标

        Args:
            sentiment_data: 情绪数据列表
            behavior_data: 行为数据列表
            symbols: 股票代码列表

        Returns:
            恐惧贪婪振荡器因子
        """
        oscillator_scores = {}

        for symbol in symbols:
            # 收集多个情绪指标
            symbol_sentiments = [s for s in sentiment_data if s.symbol == symbol]

            if not symbol_sentiments:
                oscillator_scores[symbol] = 0.0
                continue

            # 计算各个维度的情绪
            news_sentiment = (
                np.mean([s.sentiment_score for s in symbol_sentiments if s.source == "news"])
                if any(s.source == "news" for s in symbol_sentiments)
                else 0.0
            )

            social_sentiment = (
                np.mean([s.sentiment_score for s in symbol_sentiments if s.source == "social"])
                if any(s.source == "social" for s in symbol_sentiments)
                else 0.0
            )

            analyst_sentiment = (
                np.mean([s.sentiment_score for s in symbol_sentiments if s.source == "analyst"])
                if any(s.source == "analyst" for s in symbol_sentiments)
                else 0.0
            )

            # 综合振荡器（加权平均）
            oscillator = 0.4 * news_sentiment + 0.3 * social_sentiment + 0.3 * analyst_sentiment

            oscillator_scores[symbol] = oscillator

        return pd.Series(oscillator_scores)

    def get_freshness_statistics(self) -> Dict[str, Any]:
        """获取数据新鲜度统计

        需求: 6.14 - 监控数据新鲜度

        Returns:
            新鲜度统计字典
        """
        return {
            "total_checks": self.freshness_stats["total_checks"],
            "stale_data_count": self.freshness_stats["stale_data_count"],
            "stale_data_ratio": self.freshness_stats["stale_data_ratio"],
            "freshness_threshold_hours": self.freshness_threshold,
        }

    def analyze_sentiment_patterns(self, sentiment_data: List[SentimentData], symbol: str) -> Dict[str, Any]:
        """分析情绪模式

        白皮书依据: 第四章 4.1.7 - 行为模式识别
        需求: 6.13

        Args:
            sentiment_data: 情绪数据列表
            symbol: 股票代码

        Returns:
            情绪模式分析结果
        """
        symbol_sentiments = [s for s in sentiment_data if s.symbol == symbol]

        if not symbol_sentiments:
            return {"pattern": "no_data", "trend": "neutral", "volatility": 0.0, "consensus": 0.0}

        # 按时间排序
        symbol_sentiments.sort(key=lambda x: x.timestamp)

        # 提取情绪分数
        scores = [s.sentiment_score for s in symbol_sentiments]

        # 分析趋势
        if len(scores) >= 2:
            recent_avg = np.mean(scores[-5:])
            historical_avg = np.mean(scores[:-5]) if len(scores) > 5 else 0.0

            if recent_avg > historical_avg + 0.2:
                trend = "bullish"
            elif recent_avg < historical_avg - 0.2:
                trend = "bearish"
            else:
                trend = "neutral"
        else:
            trend = "neutral"

        # 计算波动性
        volatility = np.std(scores) if len(scores) > 1 else 0.0

        # 计算共识度（情绪一致性）
        if len(scores) > 0:
            positive_ratio = sum(1 for s in scores if s > 0) / len(scores)
            consensus = abs(positive_ratio - 0.5) * 2  # 0到1，1表示完全一致
        else:
            consensus = 0.0

        return {
            "pattern": "identified",
            "trend": trend,
            "volatility": volatility,
            "consensus": consensus,
            "sample_size": len(scores),
        }
