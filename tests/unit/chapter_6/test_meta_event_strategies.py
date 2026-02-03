"""Meta-Event策略单元测试

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Event系
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.strategies.data_models import StrategyConfig, Signal, Position
from src.strategies.meta_event.s16_theme_hunter import S16ThemeHunterStrategy


@pytest.fixture
def strategy_config():
    """策略配置fixture"""
    return StrategyConfig(
        strategy_name="test_strategy",
        capital_tier="tier3_medium",
        max_position=0.8,
        max_single_stock=0.1,
        max_industry=0.3,
        stop_loss_pct=-0.05,
        take_profit_pct=0.10,
        trailing_stop_enabled=False
    )


class TestS16ThemeHunterStrategy:
    """S16题材猎手策略测试"""
    
    def test_init(self, strategy_config):
        """测试策略初始化"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        assert strategy.name == "S16_Theme_Hunter"
        assert strategy.theme_heat_threshold == 0.6
        assert strategy.news_count_threshold == 10
        assert strategy.report_count_threshold == 3
    
    @pytest.mark.asyncio
    async def test_generate_signals_empty_data(self, strategy_config):
        """测试空数据时生成信号"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        market_data = {
            'scholar': {
                'research_reports': [],
                'news': []
            },
            'sentiment': {},
            'stocks': {}
        }
        
        signals = await strategy.generate_signals(market_data)
        assert signals == []
    
    @pytest.mark.asyncio
    async def test_identify_hot_themes_empty(self, strategy_config):
        """测试空数据识别热点题材"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        themes = await strategy._identify_hot_themes([], [], {})
        assert themes == []
    
    @pytest.mark.asyncio
    async def test_identify_hot_themes_with_data(self, strategy_config):
        """测试有数据时识别热点题材"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        research_reports = [
            {'themes': ['AI芯片', '人工智能'], 'related_stocks': ['000001', '000002']},
            {'themes': ['AI芯片'], 'related_stocks': ['000001', '000003']},
            {'themes': ['AI芯片'], 'related_stocks': ['000004']},
            {'themes': ['新能源'], 'related_stocks': ['000005']},
        ]
        
        news_data = [
            {'themes': ['AI芯片'], 'related_stocks': ['000001']},
            {'themes': ['AI芯片'], 'related_stocks': ['000002']},
            {'themes': ['AI芯片'], 'related_stocks': ['000003']},
            {'themes': ['AI芯片'], 'related_stocks': ['000004']},
            {'themes': ['AI芯片'], 'related_stocks': ['000005']},
            {'themes': ['AI芯片'], 'related_stocks': ['000006']},
            {'themes': ['AI芯片'], 'related_stocks': ['000007']},
            {'themes': ['AI芯片'], 'related_stocks': ['000008']},
            {'themes': ['AI芯片'], 'related_stocks': ['000009']},
            {'themes': ['AI芯片'], 'related_stocks': ['000010']},
        ]
        
        themes = await strategy._identify_hot_themes(research_reports, news_data, {})
        
        assert len(themes) > 0
        # AI芯片应该是最热的题材
        assert themes[0]['name'] == 'AI芯片'
        assert themes[0]['report_count'] == 3
        assert themes[0]['news_count'] == 10
    
    def test_calculate_theme_heat(self, strategy_config):
        """测试题材热度计算"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        theme_info = {
            'report_count': 3,
            'news_count': 10,
            'related_stocks': ['000001', '000002', '000003', '000004', '000005']
        }
        
        heat = strategy._calculate_theme_heat(theme_info)
        
        assert 0 <= heat <= 1.0
        assert heat >= 0.6  # 应该超过阈值
    
    def test_calculate_leader_score(self, strategy_config):
        """测试龙头得分计算"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        stock_info = {
            'change_pct': 0.05,
            'volume_ratio': 2.0,
            'market_cap': 20e9,  # 200亿
            'theme_relevance': 0.8
        }
        
        score = strategy._calculate_leader_score('000001', stock_info, {})
        
        assert 0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_position_sizes(self, strategy_config):
        """测试仓位计算"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        signals = [
            Signal(
                symbol='000001',
                action='buy',
                confidence=0.8,
                timestamp=datetime.now().isoformat(),
                reason='测试信号'
            ),
            Signal(
                symbol='000002',
                action='buy',
                confidence=0.7,
                timestamp=datetime.now().isoformat(),
                reason='测试信号'
            )
        ]
        
        positions = await strategy.calculate_position_sizes(signals)
        
        assert len(positions) == 2
        total_size = sum(p.size for p in positions)
        assert total_size <= 0.25  # 题材策略总仓位上限25%
    
    def test_get_tracked_themes(self, strategy_config):
        """测试获取追踪题材"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        # 初始应该为空
        themes = strategy.get_tracked_themes()
        assert themes == {}
    
    def test_clear_theme_blacklist(self, strategy_config):
        """测试清空题材黑名单"""
        strategy = S16ThemeHunterStrategy(strategy_config)
        
        # 添加一些黑名单
        strategy.theme_blacklist.add('过期题材1')
        strategy.theme_blacklist.add('过期题材2')
        
        assert len(strategy.theme_blacklist) == 2
        
        strategy.clear_theme_blacklist()
        
        assert len(strategy.theme_blacklist) == 0
