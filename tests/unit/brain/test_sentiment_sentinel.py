"""
舆情哨兵单元测试

白皮书依据: 第一章 1.5.1 战备态任务调度
测试范围: SentimentSentinel的新闻收集和情绪分析功能
"""

import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from src.brain.sentiment_sentinel import (
    SentimentSentinel,
    NewsItem,
    SentimentReport,
    SentimentLevel,
    NewsCategory
)


class TestNewsItem:
    """NewsItem数据类测试"""
    
    def test_news_item_creation(self):
        """测试新闻条目创建"""
        news = NewsItem(
            title="市场大涨，投资者信心高涨",
            content="今日A股市场全面上涨",
            source="财经新闻",
            category=NewsCategory.MARKET
        )
        
        assert news.title == "市场大涨，投资者信心高涨"
        assert news.source == "财经新闻"
        assert news.category == NewsCategory.MARKET
    
    def test_news_item_defaults(self):
        """测试新闻条目默认值"""
        news = NewsItem(title="测试新闻")
        
        assert news.content == ""
        assert news.source == ""
        assert news.category == NewsCategory.MARKET
        assert news.sentiment_score == 0.0
    
    def test_news_item_to_dict(self):
        """测试新闻条目转字典"""
        news = NewsItem(
            title="测试新闻",
            sentiment_score=0.5
        )
        
        result = news.to_dict()
        
        assert result["title"] == "测试新闻"
        assert result["sentiment_score"] == 0.5
        assert "publish_time" in result


class TestSentimentLevel:
    """SentimentLevel枚举测试"""
    
    def test_sentiment_level_values(self):
        """测试情绪等级枚举值"""
        assert SentimentLevel.VERY_BULLISH.value == "极度乐观"
        assert SentimentLevel.BULLISH.value == "乐观"
        assert SentimentLevel.NEUTRAL.value == "中性"
        assert SentimentLevel.BEARISH.value == "悲观"
        assert SentimentLevel.VERY_BEARISH.value == "极度悲观"


class TestNewsCategory:
    """NewsCategory枚举测试"""
    
    def test_news_category_values(self):
        """测试新闻类别枚举值"""
        assert NewsCategory.POLICY.value == "政策"
        assert NewsCategory.MARKET.value == "市场"
        assert NewsCategory.COMPANY.value == "公司"
        assert NewsCategory.INDUSTRY.value == "行业"
        assert NewsCategory.MACRO.value == "宏观"


class TestSentimentSentinel:
    """SentimentSentinel哨兵测试"""
    
    @pytest.fixture
    def sentinel(self):
        """创建哨兵实例"""
        return SentimentSentinel()
    
    def test_init_default(self):
        """测试默认初始化"""
        sentinel = SentimentSentinel()
        
        assert len(sentinel.bullish_keywords) > 0
        assert len(sentinel.bearish_keywords) > 0
    
    def test_init_custom_keywords(self):
        """测试自定义关键词"""
        sentinel = SentimentSentinel(
            custom_bullish_keywords=["自定义利好"],
            custom_bearish_keywords=["自定义利空"]
        )
        
        assert "自定义利好" in sentinel.bullish_keywords
        assert "自定义利空" in sentinel.bearish_keywords
    
    def test_analyze_sentiment_empty(self, sentinel):
        """测试空新闻分析"""
        report = sentinel.analyze_sentiment([])
        
        assert report.overall_sentiment == SentimentLevel.NEUTRAL
        assert report.news_count == 0
    
    def test_analyze_sentiment_bullish(self, sentinel):
        """测试利好新闻分析"""
        news_items = [
            NewsItem(title="市场大涨，创新高"),
            NewsItem(title="利好消息，股价上涨"),
            NewsItem(title="盈利超预期，增长强劲")
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert report.overall_score > 0
        assert report.bullish_count > 0
    
    def test_analyze_sentiment_bearish(self, sentinel):
        """测试利空新闻分析"""
        news_items = [
            NewsItem(title="市场大跌，创新低"),
            NewsItem(title="利空消息，股价下跌"),
            NewsItem(title="亏损严重，风险警告")
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert report.overall_score < 0
        assert report.bearish_count > 0
    
    def test_analyze_sentiment_mixed(self, sentinel):
        """测试混合新闻分析"""
        news_items = [
            NewsItem(title="市场上涨，利好"),
            NewsItem(title="市场下跌，利空"),
            NewsItem(title="市场平稳运行")
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert report.bullish_count >= 1
        assert report.bearish_count >= 1
    
    def test_calculate_sentiment_score_bullish(self, sentinel):
        """测试利好文本评分"""
        text = "市场大涨，创新高，利好消息不断"
        score = sentinel._calculate_sentiment_score(text)
        
        assert score > 0
    
    def test_calculate_sentiment_score_bearish(self, sentinel):
        """测试利空文本评分"""
        text = "市场大跌，创新低，利空消息频出"
        score = sentinel._calculate_sentiment_score(text)
        
        assert score < 0
    
    def test_calculate_sentiment_score_neutral(self, sentinel):
        """测试中性文本评分"""
        text = "今日市场正常交易"
        score = sentinel._calculate_sentiment_score(text)
        
        assert score == 0.0
    
    def test_determine_sentiment_level_very_bullish(self, sentinel):
        """测试极度乐观等级判断"""
        level = sentinel._determine_sentiment_level(0.6)
        assert level == SentimentLevel.VERY_BULLISH
    
    def test_determine_sentiment_level_bullish(self, sentinel):
        """测试乐观等级判断"""
        level = sentinel._determine_sentiment_level(0.3)
        assert level == SentimentLevel.BULLISH
    
    def test_determine_sentiment_level_neutral(self, sentinel):
        """测试中性等级判断"""
        level = sentinel._determine_sentiment_level(0.0)
        assert level == SentimentLevel.NEUTRAL
    
    def test_determine_sentiment_level_bearish(self, sentinel):
        """测试悲观等级判断"""
        level = sentinel._determine_sentiment_level(-0.3)
        assert level == SentimentLevel.BEARISH
    
    def test_determine_sentiment_level_very_bearish(self, sentinel):
        """测试极度悲观等级判断"""
        level = sentinel._determine_sentiment_level(-0.6)
        assert level == SentimentLevel.VERY_BEARISH
    
    def test_category_scores(self, sentinel):
        """测试类别评分"""
        news_items = [
            NewsItem(title="政策利好", category=NewsCategory.POLICY),
            NewsItem(title="市场大涨", category=NewsCategory.MARKET),
            NewsItem(title="公司亏损", category=NewsCategory.COMPANY)
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert "政策" in report.category_scores
        assert "市场" in report.category_scores
        assert "公司" in report.category_scores
    
    def test_hot_keywords(self, sentinel):
        """测试热门关键词提取"""
        news_items = [
            NewsItem(title="市场大涨", keywords=["大涨", "牛市"]),
            NewsItem(title="股价上涨", keywords=["上涨", "牛市"]),
            NewsItem(title="利好消息", keywords=["利好"])
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert len(report.hot_keywords) > 0
    
    def test_key_news_selection(self, sentinel):
        """测试重要新闻选取"""
        news_items = [
            NewsItem(title="普通新闻"),
            NewsItem(title="市场大涨创新高利好不断"),  # 高情绪
            NewsItem(title="市场大跌创新低利空频出")   # 高情绪
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert len(report.key_news) > 0
    
    def test_market_outlook_generation(self, sentinel):
        """测试市场展望生成"""
        news_items = [
            NewsItem(title="市场大涨，利好消息")
        ]
        
        report = sentinel.analyze_sentiment(news_items)
        
        assert report.market_outlook != ""
        assert len(report.market_outlook) > 0
    
    def test_analyze_single_news(self, sentinel):
        """测试单条新闻分析"""
        news = NewsItem(title="市场大涨，创新高")
        
        result = sentinel.analyze_single_news(news)
        
        assert result.sentiment_score > 0
    
    def test_get_sentiment_for_symbol(self, sentinel):
        """测试获取特定标的情绪"""
        news_items = [
            NewsItem(
                title="000001.SZ大涨",
                related_symbols=["000001.SZ"]
            ),
            NewsItem(
                title="600000.SH下跌",
                related_symbols=["600000.SH"]
            )
        ]
        
        # 先分析情绪
        for news in news_items:
            sentinel.analyze_single_news(news)
        
        score, related = sentinel.get_sentiment_for_symbol("000001.SZ", news_items)
        
        assert len(related) == 1
        assert "000001.SZ" in related[0].related_symbols or "000001.SZ" in related[0].title
    
    def test_get_sentiment_for_symbol_not_found(self, sentinel):
        """测试获取不存在标的的情绪"""
        news_items = [
            NewsItem(title="市场新闻", related_symbols=["000001.SZ"])
        ]
        
        score, related = sentinel.get_sentiment_for_symbol("999999.SZ", news_items)
        
        assert score == 0.0
        assert len(related) == 0
    
    def test_create_news_item(self, sentinel):
        """测试创建新闻条目"""
        news = sentinel.create_news_item(
            title="市场大涨",
            content="今日市场全面上涨",
            source="财经新闻",
            category=NewsCategory.MARKET
        )
        
        assert news.title == "市场大涨"
        assert news.sentiment_score > 0  # 自动计算


class TestSentimentReport:
    """SentimentReport报告类测试"""
    
    def test_report_creation(self):
        """测试报告创建"""
        report = SentimentReport(
            report_date=date.today(),
            overall_sentiment=SentimentLevel.BULLISH,
            overall_score=0.5,
            news_count=10
        )
        
        assert report.report_date == date.today()
        assert report.overall_sentiment == SentimentLevel.BULLISH
        assert report.overall_score == 0.5
    
    def test_report_to_dict(self):
        """测试报告转字典"""
        report = SentimentReport(
            report_date=date.today(),
            overall_sentiment=SentimentLevel.NEUTRAL,
            news_count=5
        )
        
        result = report.to_dict()
        
        assert result["overall_sentiment"] == "中性"
        assert result["news_count"] == 5
        assert "timestamp" in result


class TestSentimentSentinelAsync:
    """异步功能测试"""
    
    @pytest.fixture
    def sentinel(self):
        """创建哨兵实例"""
        return SentimentSentinel()
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_async(self, sentinel):
        """测试异步情绪分析"""
        news_items = [
            NewsItem(title="市场大涨，利好消息")
        ]
        
        report = await sentinel.analyze_sentiment_async(news_items)
        
        assert isinstance(report, SentimentReport)
        assert report.news_count == 1
