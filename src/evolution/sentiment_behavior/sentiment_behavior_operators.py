"""情绪与行为因子算子库

白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

本模块实现12种核心情绪与行为算子，用于挖掘市场情绪和投资者行为模式。

Author: MIA Team
Date: 2026-01-25
"""

import numpy as np
import pandas as pd
from loguru import logger


class SentimentBehaviorOperatorRegistry:
    """情绪与行为算子注册表

    白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

    提供12种核心情绪与行为算子：
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
    """

    def __init__(self):
        """初始化情绪与行为算子注册表"""
        logger.debug("初始化SentimentBehaviorOperatorRegistry")

    def retail_panic_index(
        self, data: pd.DataFrame, volume_col: str = "volume", price_col: str = "close", window: int = 20
    ) -> pd.Series:
        """计算散户恐慌指数

        白皮书依据: 第四章 4.1.8 散户恐慌指数

        散户恐慌指数衡量散户投资者的恐慌程度，通过以下指标综合计算：
        1. 成交量激增（恐慌性抛售）
        2. 价格急跌
        3. 波动率飙升

        Args:
            data: 市场数据
            volume_col: 成交量列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            散户恐慌指数 (0-1，越高越恐慌)
        """
        if data.empty or volume_col not in data.columns or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 1. 成交量激增指标
        volume = data[volume_col]
        volume_ma = volume.rolling(window=window).mean()
        volume_surge = (volume / (volume_ma + 1e-8)).clip(0, 5) / 5  # 归一化到[0, 1]

        # 2. 价格急跌指标
        price = data[price_col]
        price_change = price.pct_change()
        price_drop = (-price_change).clip(0, 0.1) / 0.1  # 归一化到[0, 1]

        # 3. 波动率飙升指标
        volatility = price_change.rolling(window=window).std()
        vol_ma = volatility.rolling(window=window).mean()
        vol_surge = (volatility / (vol_ma + 1e-8)).clip(0, 3) / 3  # 归一化到[0, 1]

        # 综合恐慌指数（加权平均）
        panic_index = volume_surge * 0.3 + price_drop * 0.4 + vol_surge * 0.3

        return panic_index

    def institutional_herding(
        self, data: pd.DataFrame, price_col: str = "close", volume_col: str = "volume", window: int = 20
    ) -> pd.Series:
        """计算机构羊群效应

        白皮书依据: 第四章 4.1.8 机构羊群效应

        机构羊群效应衡量机构投资者的跟风行为，通过以下指标计算：
        1. 大单成交占比
        2. 价格趋势一致性
        3. 成交量集中度

        Args:
            data: 市场数据
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            机构羊群效应指数 (0-1，越高羊群效应越强)
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 1. 价格趋势一致性（连续同向变动）
        price = data[price_col]
        price_change = price.pct_change()
        price_direction = np.sign(price_change)

        # 计算滚动窗口内方向一致性
        direction_consistency = price_direction.rolling(window=window).apply(
            lambda x: abs(x.sum()) / len(x) if len(x) > 0 else 0
        )

        # 2. 成交量集中度（大单占比的代理指标）
        volume = data[volume_col]
        volume_ma = volume.rolling(window=window).mean()
        volume_concentration = (volume / (volume_ma + 1e-8)).clip(0, 3) / 3

        # 3. 价格动量强度
        momentum = price.pct_change(window)
        momentum_strength = abs(momentum).clip(0, 0.2) / 0.2

        # 综合羊群效应指数
        herding_index = direction_consistency * 0.4 + volume_concentration * 0.3 + momentum_strength * 0.3

        return herding_index

    def analyst_revision_momentum(
        self, data: pd.DataFrame, revision_col: str = "analyst_revision", window: int = 20
    ) -> pd.Series:
        """计算分析师修正动量

        白皮书依据: 第四章 4.1.8 分析师修正动量

        分析师修正动量衡量分析师评级和目标价的修正趋势。

        Args:
            data: 市场数据（需包含分析师修正数据）
            revision_col: 分析师修正列名
            window: 计算窗口

        Returns:
            分析师修正动量 (正值=上调，负值=下调)
        """
        if data.empty or revision_col not in data.columns:
            # 如果没有分析师数据，使用价格动量作为代理
            if "close" in data.columns:
                price = data["close"]
                return price.pct_change(window)
            return pd.Series(0, index=data.index)

        # 计算分析师修正的动量
        revision = data[revision_col]
        revision_momentum = revision.rolling(window=window).mean()

        return revision_momentum

    def insider_trading_signal(
        self, data: pd.DataFrame, insider_col: str = "insider_trading", window: int = 20
    ) -> pd.Series:
        """计算内部交易信号

        白皮书依据: 第四章 4.1.8 内部交易信号

        内部交易信号衡量公司内部人员（高管、董事）的交易行为。
        内部人买入通常是看涨信号，卖出则是看跌信号。

        Args:
            data: 市场数据（需包含内部交易数据）
            insider_col: 内部交易列名
            window: 计算窗口

        Returns:
            内部交易信号 (正值=买入，负值=卖出)
        """
        if data.empty or insider_col not in data.columns:
            # 如果没有内部交易数据，使用大单净流入作为代理
            if "volume" in data.columns and "close" in data.columns:
                volume = data["volume"]
                price_change = data["close"].pct_change()
                # 大单净流入 = 成交量 * 价格变化方向
                proxy_signal = volume * np.sign(price_change)
                return proxy_signal.rolling(window=window).mean()
            return pd.Series(0, index=data.index)

        # 计算内部交易信号的累积效应
        insider_trading = data[insider_col]
        insider_signal = insider_trading.rolling(window=window).sum()

        return insider_signal

    def short_interest_squeeze(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        short_interest_col: str = "short_interest",
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 20,
    ) -> pd.Series:
        """计算空头挤压指数

        白皮书依据: 第四章 4.1.8 空头挤压

        空头挤压发生在：
        1. 高空头持仓
        2. 价格快速上涨
        3. 成交量放大

        Args:
            data: 市场数据
            short_interest_col: 空头持仓列名
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            空头挤压指数 (0-1，越高挤压风险越大)
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 1. 空头持仓水平（如果没有数据，使用代理指标）
        if short_interest_col in data.columns:
            short_interest = data[short_interest_col]
            short_level = (short_interest - short_interest.rolling(window=window).mean()) / (
                short_interest.rolling(window=window).std() + 1e-8
            )
            short_level = short_level.clip(-3, 3) / 3  # 归一化
        else:
            # 使用价格下跌幅度作为空头持仓的代理
            price = data[price_col]
            price_change = price.pct_change(window)
            short_level = (-price_change).clip(0, 0.2) / 0.2

        # 2. 价格快速上涨
        price = data[price_col]
        price_surge = price.pct_change(5).clip(0, 0.1) / 0.1  # 5日涨幅

        # 3. 成交量放大
        volume = data[volume_col]
        volume_ma = volume.rolling(window=window).mean()
        volume_surge = (volume / (volume_ma + 1e-8)).clip(0, 3) / 3

        # 综合空头挤压指数
        squeeze_index = short_level * 0.4 + price_surge * 0.3 + volume_surge * 0.3

        return squeeze_index

    def options_sentiment_skew(
        self, data: pd.DataFrame, put_call_ratio_col: str = "put_call_ratio", window: int = 20
    ) -> pd.Series:
        """计算期权情绪偏斜

        白皮书依据: 第四章 4.1.8 期权情绪偏斜

        期权情绪偏斜通过Put/Call比率衡量市场情绪：
        - 高Put/Call比率 = 看跌情绪
        - 低Put/Call比率 = 看涨情绪

        Args:
            data: 市场数据（需包含期权数据）
            put_call_ratio_col: Put/Call比率列名
            window: 计算窗口

        Returns:
            期权情绪偏斜 (正值=看跌，负值=看涨)
        """
        if data.empty or put_call_ratio_col not in data.columns:
            # 如果没有期权数据，使用波动率作为代理
            if "close" in data.columns:
                price = data["close"]
                returns = price.pct_change()
                volatility = returns.rolling(window=window).std()
                vol_ma = volatility.rolling(window=window * 2).mean()
                # 波动率偏离均值表示情绪变化
                return (volatility - vol_ma) / (vol_ma + 1e-8)
            return pd.Series(0, index=data.index)

        # 计算Put/Call比率的偏离
        put_call_ratio = data[put_call_ratio_col]
        pc_ma = put_call_ratio.rolling(window=window).mean()
        sentiment_skew = (put_call_ratio - pc_ma) / (pc_ma + 1e-8)

        return sentiment_skew

    def social_media_buzz(self, data: pd.DataFrame, buzz_col: str = "social_buzz", window: int = 20) -> pd.Series:
        """计算社交媒体热度

        白皮书依据: 第四章 4.1.8 社交媒体热度

        社交媒体热度衡量股票在社交媒体上的讨论热度和情绪。

        Args:
            data: 市场数据（需包含社交媒体数据）
            buzz_col: 社交媒体热度列名
            window: 计算窗口

        Returns:
            社交媒体热度指数
        """
        if data.empty or buzz_col not in data.columns:
            # 如果没有社交媒体数据，使用成交量作为关注度代理
            if "volume" in data.columns:
                volume = data["volume"]
                volume_ma = volume.rolling(window=window).mean()
                return (volume - volume_ma) / (volume_ma + 1e-8)
            return pd.Series(0, index=data.index)

        # 计算社交媒体热度的变化
        buzz = data[buzz_col]
        buzz_ma = buzz.rolling(window=window).mean()
        buzz_momentum = (buzz - buzz_ma) / (buzz_ma + 1e-8)

        return buzz_momentum

    def news_tone_shift(
        self, data: pd.DataFrame, news_sentiment_col: str = "news_sentiment", window: int = 20
    ) -> pd.Series:
        """计算新闻基调转变

        白皮书依据: 第四章 4.1.8 新闻基调转变

        新闻基调转变衡量新闻情绪的变化趋势。

        Args:
            data: 市场数据（需包含新闻情绪数据）
            news_sentiment_col: 新闻情绪列名
            window: 计算窗口

        Returns:
            新闻基调转变指数 (正值=转正面，负值=转负面)
        """
        if data.empty or news_sentiment_col not in data.columns:
            # 如果没有新闻数据，使用价格动量作为代理
            if "close" in data.columns:
                price = data["close"]
                momentum = price.pct_change(window)
                momentum_change = momentum.diff()
                return momentum_change
            return pd.Series(0, index=data.index)

        # 计算新闻情绪的变化
        news_sentiment = data[news_sentiment_col]
        sentiment_change = news_sentiment.diff()
        sentiment_momentum = sentiment_change.rolling(window=window).mean()

        return sentiment_momentum

    def earnings_call_sentiment(
        self, data: pd.DataFrame, earnings_sentiment_col: str = "earnings_sentiment", window: int = 20
    ) -> pd.Series:
        """计算财报电话会情绪

        白皮书依据: 第四章 4.1.8 财报电话会情绪

        财报电话会情绪通过NLP分析管理层语气和用词。

        Args:
            data: 市场数据（需包含财报情绪数据）
            earnings_sentiment_col: 财报情绪列名
            window: 计算窗口

        Returns:
            财报电话会情绪指数
        """
        if data.empty or earnings_sentiment_col not in data.columns:
            # 如果没有财报数据，使用价格在财报后的表现作为代理
            if "close" in data.columns:
                price = data["close"]
                # 假设每季度有财报（约60个交易日）
                earnings_return = price.pct_change(60)
                return earnings_return
            return pd.Series(0, index=data.index)

        # 计算财报情绪的持续效应
        earnings_sentiment = data[earnings_sentiment_col]
        sentiment_impact = earnings_sentiment.rolling(window=window).mean()

        return sentiment_impact

    def ceo_confidence_index(
        self, data: pd.DataFrame, ceo_confidence_col: str = "ceo_confidence", window: int = 20
    ) -> pd.Series:
        """计算CEO信心指数

        白皮书依据: 第四章 4.1.8 CEO信心指数

        CEO信心指数通过以下指标衡量：
        1. CEO增持/减持行为
        2. 业绩指引
        3. 公开发言基调

        Args:
            data: 市场数据（需包含CEO信心数据）
            ceo_confidence_col: CEO信心列名
            window: 计算窗口

        Returns:
            CEO信心指数
        """
        if data.empty or ceo_confidence_col not in data.columns:
            # 如果没有CEO数据，使用公司回购作为代理
            if "close" in data.columns and "volume" in data.columns:
                price = data["close"]
                volume = data["volume"]
                # 价格上涨 + 成交量放大 = 公司可能在回购
                price_momentum = price.pct_change(window)
                volume_surge = volume / volume.rolling(window=window).mean()
                confidence_proxy = price_momentum * volume_surge
                return confidence_proxy
            return pd.Series(0, index=data.index)

        # 计算CEO信心的趋势
        ceo_confidence = data[ceo_confidence_col]
        confidence_trend = ceo_confidence.rolling(window=window).mean()

        return confidence_trend

    def market_attention_allocation(
        self, data: pd.DataFrame, attention_col: str = "market_attention", window: int = 20
    ) -> pd.Series:
        """计算市场注意力分配

        白皮书依据: 第四章 4.1.8 市场注意力分配

        市场注意力分配衡量投资者对特定股票的关注度。

        Args:
            data: 市场数据（需包含注意力数据）
            attention_col: 市场注意力列名
            window: 计算窗口

        Returns:
            市场注意力分配指数
        """
        if data.empty or attention_col not in data.columns:
            # 如果没有注意力数据，使用成交量和换手率作为代理
            if "volume" in data.columns:
                volume = data["volume"]
                volume_ma = volume.rolling(window=window).mean()
                attention_proxy = volume / (volume_ma + 1e-8)
                return attention_proxy
            return pd.Series(0, index=data.index)

        # 计算市场注意力的变化
        attention = data[attention_col]
        attention_ma = attention.rolling(window=window).mean()
        attention_change = (attention - attention_ma) / (attention_ma + 1e-8)

        return attention_change

    def fear_greed_oscillator(
        self, data: pd.DataFrame, price_col: str = "close", volume_col: str = "volume", window: int = 20
    ) -> pd.Series:
        """计算恐惧贪婪振荡器

        白皮书依据: 第四章 4.1.8 恐惧贪婪振荡器

        恐惧贪婪振荡器综合多个情绪指标：
        1. 价格动量（贪婪）
        2. 波动率（恐惧）
        3. 成交量（参与度）

        Args:
            data: 市场数据
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            恐惧贪婪指数 (-1到1，负值=恐惧，正值=贪婪)
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 1. 价格动量（贪婪指标）
        price = data[price_col]
        momentum = price.pct_change(window)
        momentum_score = momentum.clip(-0.2, 0.2) / 0.2  # 归一化到[-1, 1]

        # 2. 波动率（恐惧指标，反向）
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()
        vol_ma = volatility.rolling(window=window * 2).mean()
        vol_score = -(volatility - vol_ma) / (vol_ma + 1e-8)
        vol_score = vol_score.clip(-1, 1)

        # 3. 成交量（参与度，正向表示贪婪）
        volume = data[volume_col]
        volume_ma = volume.rolling(window=window).mean()
        volume_score = (volume - volume_ma) / (volume_ma + 1e-8)
        volume_score = volume_score.clip(-1, 1)

        # 综合恐惧贪婪指数
        fear_greed = momentum_score * 0.4 + vol_score * 0.3 + volume_score * 0.3

        return fear_greed
