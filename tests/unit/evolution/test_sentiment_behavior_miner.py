"""情绪与行为因子挖掘器单元测试

白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

测试覆盖：
1. 配置验证
2. 12种情绪行为算子
3. 恐慌性抛售检测
4. 羊群行为检测
5. 市场情绪分析
6. 因子挖掘流程

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.sentiment_behavior import (
    SentimentBehaviorFactorMiner,
    SentimentBehaviorConfig,
    SentimentBehaviorOperatorRegistry
)
from src.evolution.genetic_miner import EvolutionConfig


class TestSentimentBehaviorConfig:
    """测试情绪与行为配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SentimentBehaviorConfig()
        
        assert config.panic_threshold == 0.7
        assert config.herding_threshold == 0.6
        assert config.sentiment_window == 20
        assert config.fear_greed_neutral == 0.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SentimentBehaviorConfig(
            panic_threshold=0.8,
            herding_threshold=0.7,
            sentiment_window=30,
            fear_greed_neutral=0.1
        )
        
        assert config.panic_threshold == 0.8
        assert config.herding_threshold == 0.7
        assert config.sentiment_window == 30
        assert config.fear_greed_neutral == 0.1


class TestSentimentBehaviorOperatorRegistry:
    """测试情绪与行为算子注册表"""
    
    @pytest.fixture
    def registry(self):
        """创建算子注册表"""
        return SentimentBehaviorOperatorRegistry()
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 2),
            'volume': np.random.randint(1000000, 5000000, 100),
            'high': 100 + np.cumsum(np.random.randn(100) * 2) + 1,
            'low': 100 + np.cumsum(np.random.randn(100) * 2) - 1
        }, index=dates)
        
        return data
    
    def test_retail_panic_index(self, registry, sample_data):
        """测试散户恐慌指数"""
        panic_index = registry.retail_panic_index(sample_data)
        
        assert isinstance(panic_index, pd.Series)
        assert len(panic_index) == len(sample_data)
        assert panic_index.min() >= 0
        assert panic_index.max() <= 1
    
    def test_retail_panic_index_empty_data(self, registry):
        """测试空数据的散户恐慌指数"""
        empty_data = pd.DataFrame()
        panic_index = registry.retail_panic_index(empty_data)
        
        assert isinstance(panic_index, pd.Series)
        assert len(panic_index) == 0
    
    def test_institutional_herding(self, registry, sample_data):
        """测试机构羊群效应"""
        herding_index = registry.institutional_herding(sample_data)
        
        assert isinstance(herding_index, pd.Series)
        assert len(herding_index) == len(sample_data)
        assert herding_index.min() >= 0
        assert herding_index.max() <= 1
    
    def test_analyst_revision_momentum(self, registry, sample_data):
        """测试分析师修正动量"""
        # 测试没有分析师数据的情况（使用价格动量代理）
        revision_momentum = registry.analyst_revision_momentum(sample_data)
        
        assert isinstance(revision_momentum, pd.Series)
        assert len(revision_momentum) == len(sample_data)
    
    def test_analyst_revision_momentum_with_data(self, registry, sample_data):
        """测试有分析师数据的修正动量"""
        sample_data['analyst_revision'] = np.random.randn(len(sample_data))
        revision_momentum = registry.analyst_revision_momentum(sample_data)
        
        assert isinstance(revision_momentum, pd.Series)
        assert len(revision_momentum) == len(sample_data)
    
    def test_insider_trading_signal(self, registry, sample_data):
        """测试内部交易信号"""
        # 测试没有内部交易数据的情况（使用代理）
        insider_signal = registry.insider_trading_signal(sample_data)
        
        assert isinstance(insider_signal, pd.Series)
        assert len(insider_signal) == len(sample_data)
    
    def test_insider_trading_signal_with_data(self, registry, sample_data):
        """测试有内部交易数据的信号"""
        sample_data['insider_trading'] = np.random.randn(len(sample_data))
        insider_signal = registry.insider_trading_signal(sample_data)
        
        assert isinstance(insider_signal, pd.Series)
        assert len(insider_signal) == len(sample_data)
    
    def test_short_interest_squeeze(self, registry, sample_data):
        """测试空头挤压"""
        squeeze_index = registry.short_interest_squeeze(sample_data)
        
        assert isinstance(squeeze_index, pd.Series)
        assert len(squeeze_index) == len(sample_data)
        assert squeeze_index.min() >= 0
        assert squeeze_index.max() <= 1
    
    def test_short_interest_squeeze_with_data(self, registry, sample_data):
        """测试有空头持仓数据的挤压指数"""
        sample_data['short_interest'] = np.random.uniform(0.1, 0.3, len(sample_data))
        squeeze_index = registry.short_interest_squeeze(sample_data)
        
        assert isinstance(squeeze_index, pd.Series)
        assert len(squeeze_index) == len(sample_data)
    
    def test_options_sentiment_skew(self, registry, sample_data):
        """测试期权情绪偏斜"""
        # 测试没有期权数据的情况（使用波动率代理）
        sentiment_skew = registry.options_sentiment_skew(sample_data)
        
        assert isinstance(sentiment_skew, pd.Series)
        assert len(sentiment_skew) == len(sample_data)
    
    def test_options_sentiment_skew_with_data(self, registry, sample_data):
        """测试有期权数据的情绪偏斜"""
        sample_data['put_call_ratio'] = np.random.uniform(0.5, 1.5, len(sample_data))
        sentiment_skew = registry.options_sentiment_skew(sample_data)
        
        assert isinstance(sentiment_skew, pd.Series)
        assert len(sentiment_skew) == len(sample_data)
    
    def test_social_media_buzz(self, registry, sample_data):
        """测试社交媒体热度"""
        # 测试没有社交媒体数据的情况（使用成交量代理）
        buzz = registry.social_media_buzz(sample_data)
        
        assert isinstance(buzz, pd.Series)
        assert len(buzz) == len(sample_data)
    
    def test_social_media_buzz_with_data(self, registry, sample_data):
        """测试有社交媒体数据的热度"""
        sample_data['social_buzz'] = np.random.randint(100, 10000, len(sample_data))
        buzz = registry.social_media_buzz(sample_data)
        
        assert isinstance(buzz, pd.Series)
        assert len(buzz) == len(sample_data)
    
    def test_news_tone_shift(self, registry, sample_data):
        """测试新闻基调转变"""
        # 测试没有新闻数据的情况（使用价格动量代理）
        tone_shift = registry.news_tone_shift(sample_data)
        
        assert isinstance(tone_shift, pd.Series)
        assert len(tone_shift) == len(sample_data)
    
    def test_news_tone_shift_with_data(self, registry, sample_data):
        """测试有新闻数据的基调转变"""
        sample_data['news_sentiment'] = np.random.uniform(-1, 1, len(sample_data))
        tone_shift = registry.news_tone_shift(sample_data)
        
        assert isinstance(tone_shift, pd.Series)
        assert len(tone_shift) == len(sample_data)
    
    def test_earnings_call_sentiment(self, registry, sample_data):
        """测试财报电话会情绪"""
        # 测试没有财报数据的情况（使用价格表现代理）
        earnings_sentiment = registry.earnings_call_sentiment(sample_data)
        
        assert isinstance(earnings_sentiment, pd.Series)
        assert len(earnings_sentiment) == len(sample_data)
    
    def test_earnings_call_sentiment_with_data(self, registry, sample_data):
        """测试有财报数据的情绪"""
        sample_data['earnings_sentiment'] = np.random.uniform(-1, 1, len(sample_data))
        earnings_sentiment = registry.earnings_call_sentiment(sample_data)
        
        assert isinstance(earnings_sentiment, pd.Series)
        assert len(earnings_sentiment) == len(sample_data)
    
    def test_ceo_confidence_index(self, registry, sample_data):
        """测试CEO信心指数"""
        # 测试没有CEO数据的情况（使用回购代理）
        confidence = registry.ceo_confidence_index(sample_data)
        
        assert isinstance(confidence, pd.Series)
        assert len(confidence) == len(sample_data)
    
    def test_ceo_confidence_index_with_data(self, registry, sample_data):
        """测试有CEO数据的信心指数"""
        sample_data['ceo_confidence'] = np.random.uniform(-1, 1, len(sample_data))
        confidence = registry.ceo_confidence_index(sample_data)
        
        assert isinstance(confidence, pd.Series)
        assert len(confidence) == len(sample_data)
    
    def test_market_attention_allocation(self, registry, sample_data):
        """测试市场注意力分配"""
        # 测试没有注意力数据的情况（使用成交量代理）
        attention = registry.market_attention_allocation(sample_data)
        
        assert isinstance(attention, pd.Series)
        assert len(attention) == len(sample_data)
    
    def test_market_attention_allocation_with_data(self, registry, sample_data):
        """测试有注意力数据的分配"""
        sample_data['market_attention'] = np.random.randint(100, 10000, len(sample_data))
        attention = registry.market_attention_allocation(sample_data)
        
        assert isinstance(attention, pd.Series)
        assert len(attention) == len(sample_data)
    
    def test_fear_greed_oscillator(self, registry, sample_data):
        """测试恐惧贪婪振荡器"""
        fear_greed = registry.fear_greed_oscillator(sample_data)
        
        assert isinstance(fear_greed, pd.Series)
        assert len(fear_greed) == len(sample_data)
        assert fear_greed.min() >= -1
        assert fear_greed.max() <= 1
    
    def test_fear_greed_oscillator_empty_data(self, registry):
        """测试空数据的恐惧贪婪振荡器"""
        empty_data = pd.DataFrame()
        fear_greed = registry.fear_greed_oscillator(empty_data)
        
        assert isinstance(fear_greed, pd.Series)
        assert len(fear_greed) == 0


class TestSentimentBehaviorFactorMiner:
    """测试情绪与行为因子挖掘器"""
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 2),
            'volume': np.random.randint(1000000, 5000000, 100),
            'high': 100 + np.cumsum(np.random.randn(100) * 2) + 1,
            'low': 100 + np.cumsum(np.random.randn(100) * 2) - 1
        }, index=dates)
        
        return data
    
    @pytest.fixture
    def sample_returns(self, sample_data):
        """创建样本收益率"""
        return sample_data['close'].pct_change().fillna(0)
    
    def test_initialization_default_config(self):
        """测试默认配置初始化"""
        miner = SentimentBehaviorFactorMiner()
        
        assert miner.sentiment_config.panic_threshold == 0.7
        assert miner.sentiment_config.herding_threshold == 0.6
        assert isinstance(miner.operator_registry, SentimentBehaviorOperatorRegistry)
        assert len(miner.sentiment_signals) == 0
    
    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        config = SentimentBehaviorConfig(
            panic_threshold=0.8,
            herding_threshold=0.7
        )
        evolution_config = EvolutionConfig(population_size=30)
        
        miner = SentimentBehaviorFactorMiner(
            config=config,
            evolution_config=evolution_config
        )
        
        assert miner.sentiment_config.panic_threshold == 0.8
        assert miner.sentiment_config.herding_threshold == 0.7
    
    def test_invalid_panic_threshold(self):
        """测试无效的恐慌阈值"""
        config = SentimentBehaviorConfig(panic_threshold=1.5)
        
        with pytest.raises(ValueError, match="panic_threshold必须在\\[0, 1\\]范围内"):
            SentimentBehaviorFactorMiner(config=config)
    
    def test_invalid_herding_threshold(self):
        """测试无效的羊群阈值"""
        config = SentimentBehaviorConfig(herding_threshold=-0.1)
        
        with pytest.raises(ValueError, match="herding_threshold必须在\\[0, 1\\]范围内"):
            SentimentBehaviorFactorMiner(config=config)
    
    def test_invalid_sentiment_window(self):
        """测试无效的情绪窗口"""
        config = SentimentBehaviorConfig(sentiment_window=0)
        
        with pytest.raises(ValueError, match="sentiment_window必须 > 0"):
            SentimentBehaviorFactorMiner(config=config)
    
    def test_invalid_fear_greed_neutral(self):
        """测试无效的恐惧贪婪中性值"""
        config = SentimentBehaviorConfig(fear_greed_neutral=2.0)
        
        with pytest.raises(ValueError, match="fear_greed_neutral必须在\\[-1, 1\\]范围内"):
            SentimentBehaviorFactorMiner(config=config)
    
    def test_operator_whitelist_extension(self):
        """测试算子白名单扩展"""
        miner = SentimentBehaviorFactorMiner()
        
        expected_operators = [
            'retail_panic_index',
            'institutional_herding',
            'analyst_revision_momentum',
            'insider_trading_signal',
            'short_interest_squeeze',
            'options_sentiment_skew',
            'social_media_buzz',
            'news_tone_shift',
            'earnings_call_sentiment',
            'ceo_confidence_index',
            'market_attention_allocation',
            'fear_greed_oscillator'
        ]
        
        for operator in expected_operators:
            assert operator in miner.operator_whitelist
    
    def test_detect_panic_selling(self, sample_data):
        """测试恐慌性抛售检测"""
        miner = SentimentBehaviorFactorMiner()
        panic_signal = miner.detect_panic_selling(sample_data)
        
        assert isinstance(panic_signal, pd.Series)
        assert len(panic_signal) == len(sample_data)
        assert set(panic_signal.unique()).issubset({0, 1})
    
    def test_detect_panic_selling_empty_data(self):
        """测试空数据的恐慌性抛售检测"""
        miner = SentimentBehaviorFactorMiner()
        empty_data = pd.DataFrame()
        panic_signal = miner.detect_panic_selling(empty_data)
        
        assert isinstance(panic_signal, pd.Series)
        assert len(panic_signal) == 0
    
    def test_detect_herding_behavior(self, sample_data):
        """测试羊群行为检测"""
        miner = SentimentBehaviorFactorMiner()
        herding_signal = miner.detect_herding_behavior(sample_data)
        
        assert isinstance(herding_signal, pd.Series)
        assert len(herding_signal) == len(sample_data)
        assert set(herding_signal.unique()).issubset({0, 1})
    
    def test_detect_herding_behavior_empty_data(self):
        """测试空数据的羊群行为检测"""
        miner = SentimentBehaviorFactorMiner()
        empty_data = pd.DataFrame()
        herding_signal = miner.detect_herding_behavior(empty_data)
        
        assert isinstance(herding_signal, pd.Series)
        assert len(herding_signal) == 0
    
    def test_analyze_market_sentiment(self, sample_data):
        """测试市场情绪分析"""
        miner = SentimentBehaviorFactorMiner()
        sentiment_indicators = miner.analyze_market_sentiment(sample_data)
        
        assert isinstance(sentiment_indicators, dict)
        assert 'fear_greed' in sentiment_indicators
        assert 'panic' in sentiment_indicators
        assert 'herding' in sentiment_indicators
        assert 'social_buzz' in sentiment_indicators
        
        for indicator in sentiment_indicators.values():
            assert isinstance(indicator, pd.Series)
            assert len(indicator) == len(sample_data)
    
    def test_analyze_market_sentiment_empty_data(self):
        """测试空数据的市场情绪分析"""
        miner = SentimentBehaviorFactorMiner()
        empty_data = pd.DataFrame()
        sentiment_indicators = miner.analyze_market_sentiment(empty_data)
        
        assert isinstance(sentiment_indicators, dict)
        assert len(sentiment_indicators) == 0
    
    def test_calculate_sentiment_composite_score(self, sample_data):
        """测试情绪综合评分"""
        miner = SentimentBehaviorFactorMiner()
        composite_score = miner.calculate_sentiment_composite_score(sample_data)
        
        assert isinstance(composite_score, pd.Series)
        assert len(composite_score) == len(sample_data)
        assert composite_score.min() >= -1
        assert composite_score.max() <= 1
    
    def test_calculate_sentiment_composite_score_empty_data(self):
        """测试空数据的情绪综合评分"""
        miner = SentimentBehaviorFactorMiner()
        empty_data = pd.DataFrame()
        composite_score = miner.calculate_sentiment_composite_score(empty_data)
        
        assert isinstance(composite_score, pd.Series)
        assert len(composite_score) == 0
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, sample_data, sample_returns):
        """测试因子挖掘"""
        evolution_config = EvolutionConfig(population_size=10)
        miner = SentimentBehaviorFactorMiner(evolution_config=evolution_config)
        
        factors = await miner.mine_factors(sample_data, sample_returns, generations=2)
        
        assert isinstance(factors, list)
        assert len(factors) <= 10
        assert all(hasattr(f, 'fitness') for f in factors)
    
    @pytest.mark.asyncio
    async def test_mine_factors_empty_data(self, sample_returns):
        """测试空数据的因子挖掘"""
        miner = SentimentBehaviorFactorMiner()
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="输入数据为空"):
            await miner.mine_factors(empty_data, sample_returns)
    
    def test_get_sentiment_report(self):
        """测试情绪信号报告"""
        miner = SentimentBehaviorFactorMiner()
        report = miner.get_sentiment_report()
        
        assert isinstance(report, dict)
        assert 'total_sentiment_signals' in report
        assert 'signals_by_type' in report
        assert 'panic_threshold' in report
        assert 'herding_threshold' in report
        assert 'sentiment_window' in report
        assert 'fear_greed_neutral' in report
        
        assert report['panic_threshold'] == 0.7
        assert report['herding_threshold'] == 0.6
        assert report['sentiment_window'] == 20
        assert report['fear_greed_neutral'] == 0.0


class TestSentimentBehaviorIntegration:
    """集成测试"""
    
    @pytest.fixture
    def realistic_data(self):
        """创建更真实的市场数据"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        
        # 模拟市场周期
        trend = np.linspace(0, 20, 252)
        cycle = 10 * np.sin(np.linspace(0, 4 * np.pi, 252))
        noise = np.random.randn(252) * 2
        
        close = 100 + trend + cycle + noise
        
        data = pd.DataFrame({
            'close': close,
            'volume': np.random.randint(1000000, 5000000, 252),
            'high': close + np.abs(np.random.randn(252)),
            'low': close - np.abs(np.random.randn(252))
        }, index=dates)
        
        return data
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, realistic_data):
        """测试完整流程"""
        # 1. 初始化挖掘器
        config = SentimentBehaviorConfig(
            panic_threshold=0.7,
            herding_threshold=0.6,
            sentiment_window=20
        )
        evolution_config = EvolutionConfig(population_size=20)
        miner = SentimentBehaviorFactorMiner(
            config=config,
            evolution_config=evolution_config
        )
        
        # 2. 检测恐慌性抛售
        panic_signals = miner.detect_panic_selling(realistic_data)
        assert len(panic_signals) == len(realistic_data)
        
        # 3. 检测羊群行为
        herding_signals = miner.detect_herding_behavior(realistic_data)
        assert len(herding_signals) == len(realistic_data)
        
        # 4. 分析市场情绪
        sentiment_indicators = miner.analyze_market_sentiment(realistic_data)
        assert len(sentiment_indicators) == 4
        
        # 5. 计算综合评分
        composite_score = miner.calculate_sentiment_composite_score(realistic_data)
        assert len(composite_score) == len(realistic_data)
        
        # 6. 挖掘因子
        returns = realistic_data['close'].pct_change().fillna(0)
        factors = await miner.mine_factors(realistic_data, returns, generations=2)
        assert len(factors) > 0
        
        # 7. 获取报告
        report = miner.get_sentiment_report()
        assert report['total_sentiment_signals'] >= 0
