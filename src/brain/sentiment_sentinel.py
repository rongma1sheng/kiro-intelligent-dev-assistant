"""
舆情哨兵 (Sentiment Sentinel)

白皮书依据: 第一章 1.5.1 战备态任务调度
- 抓取隔夜要闻
- 分析市场情绪
- 生成情绪报告

功能:
- 收集市场新闻和公告
- 分析情绪倾向
- 生成情绪评分
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class SentimentLevel(Enum):
    """情绪等级"""

    VERY_BULLISH = "极度乐观"
    BULLISH = "乐观"
    NEUTRAL = "中性"
    BEARISH = "悲观"
    VERY_BEARISH = "极度悲观"


class NewsCategory(Enum):
    """新闻类别"""

    POLICY = "政策"
    MARKET = "市场"
    COMPANY = "公司"
    INDUSTRY = "行业"
    MACRO = "宏观"
    INTERNATIONAL = "国际"


@dataclass
class NewsItem:
    """新闻条目

    Attributes:
        title: 标题
        content: 内容摘要
        source: 来源
        category: 类别
        publish_time: 发布时间
        sentiment_score: 情绪评分 (-1到1)
        keywords: 关键词列表
        related_symbols: 相关标的
    """

    title: str
    content: str = ""
    source: str = ""
    category: NewsCategory = NewsCategory.MARKET
    publish_time: datetime = field(default_factory=datetime.now)
    sentiment_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    related_symbols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "category": self.category.value,
            "publish_time": self.publish_time.isoformat(),
            "sentiment_score": self.sentiment_score,
            "keywords": self.keywords,
            "related_symbols": self.related_symbols,
        }


@dataclass
class SentimentReport:
    """情绪报告

    Attributes:
        report_date: 报告日期
        overall_sentiment: 整体情绪等级
        overall_score: 整体情绪评分
        news_count: 新闻数量
        bullish_count: 利好新闻数
        bearish_count: 利空新闻数
        neutral_count: 中性新闻数
        category_scores: 各类别情绪评分
        hot_keywords: 热门关键词
        key_news: 重要新闻列表
        market_outlook: 市场展望
        timestamp: 生成时间
    """

    report_date: date
    overall_sentiment: SentimentLevel
    overall_score: float = 0.0
    news_count: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    category_scores: Dict[str, float] = field(default_factory=dict)
    hot_keywords: List[Tuple[str, int]] = field(default_factory=list)
    key_news: List[NewsItem] = field(default_factory=list)
    market_outlook: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_date": self.report_date.isoformat(),
            "overall_sentiment": self.overall_sentiment.value,
            "overall_score": self.overall_score,
            "news_count": self.news_count,
            "bullish_count": self.bullish_count,
            "bearish_count": self.bearish_count,
            "neutral_count": self.neutral_count,
            "category_scores": self.category_scores,
            "hot_keywords": self.hot_keywords,
            "key_news": [n.to_dict() for n in self.key_news],
            "market_outlook": self.market_outlook,
            "timestamp": self.timestamp.isoformat(),
        }


class SentimentSentinel:
    """舆情哨兵

    白皮书依据: 第一章 1.5.1 战备态任务调度

    负责收集市场新闻，分析情绪倾向，生成情绪报告。

    Attributes:
        bullish_keywords: 利好关键词
        bearish_keywords: 利空关键词
        news_sources: 新闻来源列表

    Example:
        >>> sentinel = SentimentSentinel()
        >>> report = sentinel.analyze_sentiment(news_list)
        >>> print(f"市场情绪: {report.overall_sentiment.value}")
    """

    # 利好关键词
    BULLISH_KEYWORDS = [
        "利好",
        "上涨",
        "突破",
        "新高",
        "增长",
        "盈利",
        "超预期",
        "回暖",
        "复苏",
        "扩张",
        "利润",
        "分红",
        "增持",
        "买入",
        "看好",
        "乐观",
        "强劲",
        "提振",
        "支撑",
        "反弹",
        "走强",
        "牛市",
        "放量",
        "涨停",
        "大涨",
        "暴涨",
        "飙升",
        "创新高",
    ]

    # 利空关键词
    BEARISH_KEYWORDS = [
        "利空",
        "下跌",
        "跌破",
        "新低",
        "下滑",
        "亏损",
        "不及预期",
        "疲软",
        "衰退",
        "收缩",
        "减持",
        "卖出",
        "看空",
        "悲观",
        "疲弱",
        "承压",
        "回调",
        "走弱",
        "熊市",
        "缩量",
        "跌停",
        "大跌",
        "暴跌",
        "崩盘",
        "创新低",
        "风险",
        "警告",
        "危机",
    ]

    def __init__(
        self, custom_bullish_keywords: Optional[List[str]] = None, custom_bearish_keywords: Optional[List[str]] = None
    ):
        """初始化舆情哨兵

        Args:
            custom_bullish_keywords: 自定义利好关键词
            custom_bearish_keywords: 自定义利空关键词
        """
        self.bullish_keywords = set(self.BULLISH_KEYWORDS)
        self.bearish_keywords = set(self.BEARISH_KEYWORDS)

        if custom_bullish_keywords:
            self.bullish_keywords.update(custom_bullish_keywords)
        if custom_bearish_keywords:
            self.bearish_keywords.update(custom_bearish_keywords)

        self._news_cache: List[NewsItem] = []

        logger.info(f"舆情哨兵初始化: " f"利好词={len(self.bullish_keywords)}, " f"利空词={len(self.bearish_keywords)}")

    def analyze_sentiment(self, news_items: List[NewsItem]) -> SentimentReport:
        """分析市场情绪

        白皮书依据: 第一章 1.5.1 抓取隔夜要闻

        Args:
            news_items: 新闻列表

        Returns:
            情绪报告
        """
        logger.info(f"开始情绪分析，新闻数量: {len(news_items)}")

        if not news_items:
            return SentimentReport(
                report_date=date.today(),
                overall_sentiment=SentimentLevel.NEUTRAL,
                market_outlook="无新闻数据，无法判断市场情绪",
            )

        # 分析每条新闻的情绪
        for news in news_items:
            if news.sentiment_score == 0.0:
                news.sentiment_score = self._calculate_sentiment_score(news.title + " " + news.content)

        # 统计情绪分布
        bullish_count = sum(1 for n in news_items if n.sentiment_score > 0.2)
        bearish_count = sum(1 for n in news_items if n.sentiment_score < -0.2)
        neutral_count = len(news_items) - bullish_count - bearish_count

        # 计算整体情绪评分
        overall_score = sum(n.sentiment_score for n in news_items) / len(news_items)

        # 确定情绪等级
        overall_sentiment = self._determine_sentiment_level(overall_score)

        # 按类别统计情绪
        category_scores = self._calculate_category_scores(news_items)

        # 提取热门关键词
        hot_keywords = self._extract_hot_keywords(news_items)

        # 选取重要新闻
        key_news = self._select_key_news(news_items)

        # 生成市场展望
        market_outlook = self._generate_market_outlook(overall_sentiment, overall_score, category_scores)

        report = SentimentReport(
            report_date=date.today(),
            overall_sentiment=overall_sentiment,
            overall_score=overall_score,
            news_count=len(news_items),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            category_scores=category_scores,
            hot_keywords=hot_keywords,
            key_news=key_news,
            market_outlook=market_outlook,
        )

        logger.info(f"情绪分析完成: " f"情绪={overall_sentiment.value}, " f"评分={overall_score:.2f}")

        return report

    def _calculate_sentiment_score(self, text: str) -> float:
        """计算文本情绪评分

        Args:
            text: 文本内容

        Returns:
            情绪评分 (-1到1)
        """
        if not text:
            return 0.0

        bullish_count = 0
        bearish_count = 0

        for keyword in self.bullish_keywords:
            if keyword in text:
                bullish_count += 1

        for keyword in self.bearish_keywords:
            if keyword in text:
                bearish_count += 1

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        # 计算情绪评分
        score = (bullish_count - bearish_count) / total

        # 限制在[-1, 1]范围
        return max(-1.0, min(1.0, score))

    def _determine_sentiment_level(self, score: float) -> SentimentLevel:
        """确定情绪等级

        Args:
            score: 情绪评分

        Returns:
            情绪等级
        """
        if score >= 0.5:  # pylint: disable=no-else-return
            return SentimentLevel.VERY_BULLISH
        elif score >= 0.2:
            return SentimentLevel.BULLISH
        elif score <= -0.5:
            return SentimentLevel.VERY_BEARISH
        elif score <= -0.2:
            return SentimentLevel.BEARISH
        else:
            return SentimentLevel.NEUTRAL

    def _calculate_category_scores(self, news_items: List[NewsItem]) -> Dict[str, float]:
        """计算各类别情绪评分

        Args:
            news_items: 新闻列表

        Returns:
            {类别: 评分}
        """
        category_news: Dict[str, List[float]] = defaultdict(list)

        for news in news_items:
            category_news[news.category.value].append(news.sentiment_score)

        category_scores = {}
        for category, scores in category_news.items():
            if scores:
                category_scores[category] = sum(scores) / len(scores)

        return category_scores

    def _extract_hot_keywords(self, news_items: List[NewsItem], top_n: int = 10) -> List[Tuple[str, int]]:
        """提取热门关键词

        Args:
            news_items: 新闻列表
            top_n: 返回数量

        Returns:
            [(关键词, 出现次数)]
        """
        keyword_counts: Dict[str, int] = defaultdict(int)

        for news in news_items:
            for keyword in news.keywords:
                keyword_counts[keyword] += 1

            # 从标题提取关键词
            for keyword in self.bullish_keywords | self.bearish_keywords:
                if keyword in news.title:
                    keyword_counts[keyword] += 1

        # 排序并返回top_n
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)

        return sorted_keywords[:top_n]

    def _select_key_news(self, news_items: List[NewsItem], top_n: int = 5) -> List[NewsItem]:
        """选取重要新闻

        Args:
            news_items: 新闻列表
            top_n: 返回数量

        Returns:
            重要新闻列表
        """
        # 按情绪评分绝对值排序
        sorted_news = sorted(news_items, key=lambda x: abs(x.sentiment_score), reverse=True)

        return sorted_news[:top_n]

    def _generate_market_outlook(
        self,
        sentiment: SentimentLevel,
        score: float,  # pylint: disable=unused-argument
        category_scores: Dict[str, float],  # pylint: disable=unused-argument
    ) -> str:
        """生成市场展望

        Args:
            sentiment: 情绪等级
            score: 情绪评分
            category_scores: 类别评分

        Returns:
            市场展望文本
        """
        outlook_parts = []

        # 整体情绪描述
        if sentiment == SentimentLevel.VERY_BULLISH:
            outlook_parts.append("市场情绪极度乐观，投资者信心高涨")
        elif sentiment == SentimentLevel.BULLISH:
            outlook_parts.append("市场情绪偏向乐观，整体氛围积极")
        elif sentiment == SentimentLevel.VERY_BEARISH:
            outlook_parts.append("市场情绪极度悲观，投资者信心不足")
        elif sentiment == SentimentLevel.BEARISH:
            outlook_parts.append("市场情绪偏向悲观，需谨慎操作")
        else:
            outlook_parts.append("市场情绪中性，观望情绪浓厚")

        # 类别分析
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            worst_category = min(category_scores.items(), key=lambda x: x[1])

            if best_category[1] > 0.2:
                outlook_parts.append(f"{best_category[0]}板块情绪最为积极")
            if worst_category[1] < -0.2:
                outlook_parts.append(f"{worst_category[0]}板块承压明显")

        return "。".join(outlook_parts) + "。"

    def analyze_single_news(self, news: NewsItem) -> NewsItem:
        """分析单条新闻

        Args:
            news: 新闻条目

        Returns:
            带情绪评分的新闻
        """
        news.sentiment_score = self._calculate_sentiment_score(news.title + " " + news.content)
        return news

    def get_sentiment_for_symbol(self, symbol: str, news_items: List[NewsItem]) -> Tuple[float, List[NewsItem]]:
        """获取特定标的的情绪

        Args:
            symbol: 标的代码
            news_items: 新闻列表

        Returns:
            (情绪评分, 相关新闻列表)
        """
        related_news = [n for n in news_items if symbol in n.related_symbols or symbol in n.title]

        if not related_news:
            return 0.0, []

        avg_score = sum(n.sentiment_score for n in related_news) / len(related_news)

        return avg_score, related_news

    def create_news_item(  # pylint: disable=too-many-positional-arguments
        self,
        title: str,
        content: str = "",
        source: str = "",
        category: NewsCategory = NewsCategory.MARKET,
        related_symbols: Optional[List[str]] = None,
    ) -> NewsItem:
        """创建新闻条目

        Args:
            title: 标题
            content: 内容
            source: 来源
            category: 类别
            related_symbols: 相关标的

        Returns:
            新闻条目
        """
        news = NewsItem(
            title=title, content=content, source=source, category=category, related_symbols=related_symbols or []
        )

        # 自动计算情绪评分
        news.sentiment_score = self._calculate_sentiment_score(title + " " + content)

        return news

    async def analyze_sentiment_async(self, news_items: List[NewsItem]) -> SentimentReport:
        """异步分析市场情绪

        Args:
            news_items: 新闻列表

        Returns:
            情绪报告
        """
        return await asyncio.to_thread(self.analyze_sentiment, news_items)
