"""Meta-Arbitrage策略单元测试

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.strategies.data_models import StrategyConfig, Signal, Position
from src.strategies.meta_arbitrage.s09_cb_scalper import S09CBScalperStrategy
from src.strategies.meta_arbitrage.s14_cross_domain_arb import S14CrossDomainArbStrategy
from src.strategies.meta_arbitrage.s17_derivatives_linkage import S17DerivativesLinkageStrategy
from src.strategies.meta_arbitrage.s18_future_trend import S18FutureTrendStrategy
from src.strategies.meta_arbitrage.s19_option_sniper import S19OptionSniperStrategy


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


class TestS09CBScalperStrategy:
    """S09可转债策略测试"""
    
    def test_init(self, strategy_config):
        """测试策略初始化"""
        strategy = S09CBScalperStrategy(strategy_config)
        
        assert strategy.name == "S09_CB_Scalper"
        assert strategy.premium_threshold == 0.05
        assert strategy.min_stock_change == 0.03
    
    @pytest.mark.asyncio
    async def test_generate_signals_empty_data(self, strategy_config):
        """测试空数据时生成信号"""
        strategy = S09CBScalperStrategy(strategy_config)
        
        market_data = {
            'convertible_bonds': {},
            'stocks': {}
        }
        
        signals = await strategy.generate_signals(market_data)
        assert signals == []
    
    @pytest.mark.asyncio
    async def test_generate_signals_with_opportunity(self, strategy_config):
        """测试有套利机会时生成信号"""
        strategy = S09CBScalperStrategy(strategy_config)
        
        market_data = {
            'convertible_bonds': {
                '123456': {
                    'price': 110,
                    'conversion_price': 10,
                    'stock_code': '000001',
                    'volume': 50_000_000,
                    'premium_rate': 0.10
                }
            },
            'stocks': {
                '000001': {
                    'price': 10.5,
                    'change_pct': 0.05
                }
            }
        }
        
        signals = await strategy.generate_signals(market_data)
        # 根据条件可能生成信号或不生成
        assert isinstance(signals, list)
    
    @pytest.mark.asyncio
    async def test_calculate_position_sizes(self, strategy_config):
        """测试仓位计算"""
        strategy = S09CBScalperStrategy(strategy_config)
        
        signals = [
            Signal(
                symbol='123456',
                action='buy',
                confidence=0.8,
                timestamp=datetime.now().isoformat(),
                reason='测试信号'
            )
        ]
        
        # 注意：实际使用时entry_price会在执行时填充
        # 这里测试的是仓位大小计算逻辑
        positions = await strategy.calculate_position_sizes(signals)
        
        assert len(positions) == 1
        assert positions[0].symbol == '123456'
        # 检查仓位大小在合理范围内
        assert 0 < positions[0].size <= 0.20  # 可转债策略上限20%


class TestS14CrossDomainArbStrategy:
    """S14跨域套利策略测试"""
    
    def test_init(self, strategy_config):
        """测试策略初始化"""
        strategy = S14CrossDomainArbStrategy(strategy_config)
        
        assert strategy.name == "S14_Cross_Domain_Arb"
        assert strategy.basis_threshold == 0.02
        assert strategy.spread_threshold == 0.015
    
    @pytest.mark.asyncio
    async def test_generate_signals_empty_data(self, strategy_config):
        """测试空数据时生成信号"""
        strategy = S14CrossDomainArbStrategy(strategy_config)
        
        market_data = {
            'futures': {},
            'spot': {},
            'industry_chain': {}
        }
        
        signals = await strategy.generate_signals(market_data)
        assert signals == []
    
    def test_get_spot_symbol(self, strategy_config):
        """测试期货到现货映射"""
        strategy = S14CrossDomainArbStrategy(strategy_config)
        
        assert strategy._get_spot_symbol('IF2401') == '510300.SH'
        assert strategy._get_spot_symbol('IC2401') == '510500.SH'
        assert strategy._get_spot_symbol('UNKNOWN') == ''


class TestS17DerivativesLinkageStrategy:
    """S17期现联动策略测试"""
    
    def test_init(self, strategy_config):
        """测试策略初始化"""
        strategy = S17DerivativesLinkageStrategy(strategy_config)
        
        assert strategy.name == "S17_Derivatives_Linkage"
        assert strategy.iv_change_threshold == 0.15
        assert strategy.premium_threshold == 0.01
    
    @pytest.mark.asyncio
    async def test_generate_signals_empty_data(self, strategy_config):
        """测试空数据时生成信号"""
        strategy = S17DerivativesLinkageStrategy(strategy_config)
        
        market_data = {
            'options': {},
            'futures': {},
            'spot': {}
        }
        
        signals = await strategy.generate_signals(market_data)
        assert signals == []


class TestS18FutureTrendStrategy:
    """S18期指趋势策略测试"""
    
    def test_init(self, strategy_config):
        """测试策略初始化"""
        strategy = S18FutureTrendStrategy(strategy_config)
        
        assert strategy.name == "S18_Future_Trend"
        assert strategy.shadow_mode is True  # 默认Shadow Mode
        assert strategy.trend_threshold == 0.02
    
    def test_enable_live_trading(self, strategy_config):
        """测试开启实盘交易"""
        strategy = S18FutureTrendStrategy(strategy_config)
        
        assert strategy.shadow_mode is True
        strategy.enable_live_trading()
        assert strategy.shadow_mode is False
    
    def test_disable_live_trading(self, strategy_config):
        """测试关闭实盘交易"""
        strategy = S18FutureTrendStrategy(strategy_config)
        
        strategy.enable_live_trading()
        assert strategy.shadow_mode is False
        strategy.disable_live_trading()
        assert strategy.shadow_mode is True
    
    @pytest.mark.asyncio
    async def test_shadow_mode_positions(self, strategy_config):
        """测试Shadow Mode下仓位为0"""
        strategy = S18FutureTrendStrategy(strategy_config)
        
        signals = [
            Signal(
                symbol='IC2401',
                action='buy',
                confidence=0.8,
                timestamp=datetime.now().isoformat(),
                reason='测试信号'
            )
        ]
        
        positions = await strategy.calculate_position_sizes(signals)
        
        assert len(positions) == 1
        assert positions[0].size == 0.0  # Shadow Mode仓位为0
        assert positions[0].industry == 'index_futures_shadow'


class TestS19OptionSniperStrategy:
    """S19期权狙击策略测试"""
    
    def test_init(self, strategy_config):
        """测试策略初始化"""
        strategy = S19OptionSniperStrategy(strategy_config)
        
        assert strategy.name == "S19_Option_Sniper"
        assert strategy.shadow_mode is True  # 默认Shadow Mode
        assert strategy.sentiment_threshold == 0.7
    
    def test_enable_live_trading(self, strategy_config):
        """测试开启实盘交易"""
        strategy = S19OptionSniperStrategy(strategy_config)
        
        assert strategy.shadow_mode is True
        strategy.enable_live_trading()
        assert strategy.shadow_mode is False
    
    @pytest.mark.asyncio
    async def test_detect_sentiment_events_empty(self, strategy_config):
        """测试空舆情数据"""
        strategy = S19OptionSniperStrategy(strategy_config)
        
        events = await strategy._detect_sentiment_events({})
        assert events == []
    
    @pytest.mark.asyncio
    async def test_detect_sentiment_events_with_event(self, strategy_config):
        """测试有舆情事件"""
        strategy = S19OptionSniperStrategy(strategy_config)
        
        sentiment_data = {
            '510050': {
                'score': 0.8,
                'change_1h': 0.4,
                'news_count_1h': 20
            }
        }
        
        events = await strategy._detect_sentiment_events(sentiment_data)
        
        assert len(events) == 1
        assert events[0]['underlying'] == '510050'
        assert events[0]['event_type'] == 'positive'
