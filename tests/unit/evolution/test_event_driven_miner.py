"""事件驱动因子挖掘器单元测试

白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

测试覆盖：
1. 配置验证
2. 15种事件驱动算子
3. 盈利事件检测
4. 并购事件检测
5. 公司事件检测
6. 事件影响分析
7. 因子挖掘流程

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.event_driven import (
    EventDrivenFactorMiner,
    EventDrivenConfig,
    EventDrivenOperatorRegistry
)
from src.evolution.genetic_miner import EvolutionConfig


class TestEventDrivenConfig:
    """测试事件驱动配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = EventDrivenConfig()
        
        assert config.event_window == 20
        assert config.earnings_threshold == 0.05
        assert config.merger_spread_threshold == 0.1
        assert config.min_event_impact == 0.01
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = EventDrivenConfig(
            event_window=30,
            earnings_threshold=0.08,
            merger_spread_threshold=0.15,
            min_event_impact=0.02
        )
        
        assert config.event_window == 30
        assert config.earnings_threshold == 0.08
        assert config.merger_spread_threshold == 0.15
        assert config.min_event_impact == 0.02


class TestEventDrivenOperatorRegistry:
    """测试事件驱动算子注册表"""
    
    @pytest.fixture
    def registry(self):
        """创建算子注册表"""
        return EventDrivenOperatorRegistry()
    
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
    
    def test_earnings_surprise(self, registry, sample_data):
        """测试盈利意外"""
        surprise = registry.earnings_surprise(sample_data)
        
        assert isinstance(surprise, pd.Series)
        assert len(surprise) == len(sample_data)
    
    def test_earnings_surprise_with_data(self, registry, sample_data):
        """测试有盈利数据的意外"""
        sample_data['earnings_actual'] = np.random.uniform(1, 5, len(sample_data))
        sample_data['earnings_estimate'] = np.random.uniform(1, 5, len(sample_data))
        surprise = registry.earnings_surprise(sample_data)
        
        assert isinstance(surprise, pd.Series)
        assert len(surprise) == len(sample_data)
    
    def test_earnings_surprise_empty_data(self, registry):
        """测试空数据的盈利意外"""
        empty_data = pd.DataFrame()
        surprise = registry.earnings_surprise(empty_data)
        
        assert isinstance(surprise, pd.Series)
        assert len(surprise) == 0
    
    def test_merger_arbitrage_spread(self, registry, sample_data):
        """测试并购套利价差"""
        spread = registry.merger_arbitrage_spread(sample_data)
        
        assert isinstance(spread, pd.Series)
        assert len(spread) == len(sample_data)
        assert spread.min() >= 0
    
    def test_merger_arbitrage_spread_with_data(self, registry, sample_data):
        """测试有并购数据的套利价差"""
        sample_data['merger_target_price'] = sample_data['close'] * 1.2
        spread = registry.merger_arbitrage_spread(sample_data)
        
        assert isinstance(spread, pd.Series)
        assert len(spread) == len(sample_data)
        assert spread.mean() > 0  # 目标价高于当前价
    
    def test_ipo_lockup_expiry(self, registry, sample_data):
        """测试IPO锁定期到期"""
        lockup_impact = registry.ipo_lockup_expiry(sample_data)
        
        assert isinstance(lockup_impact, pd.Series)
        assert len(lockup_impact) == len(sample_data)
    
    def test_ipo_lockup_expiry_with_data(self, registry, sample_data):
        """测试有锁定期数据的到期影响"""
        # 设置锁定期到期日（50天后）
        sample_data['lockup_expiry_date'] = sample_data.index[50]
        lockup_impact = registry.ipo_lockup_expiry(sample_data)
        
        assert isinstance(lockup_impact, pd.Series)
        assert len(lockup_impact) == len(sample_data)
    
    def test_dividend_announcement(self, registry, sample_data):
        """测试股息公告"""
        dividend_impact = registry.dividend_announcement(sample_data)
        
        assert isinstance(dividend_impact, pd.Series)
        assert len(dividend_impact) == len(sample_data)
    
    def test_dividend_announcement_with_data(self, registry, sample_data):
        """测试有股息数据的公告影响"""
        sample_data['dividend_yield'] = np.random.uniform(0.01, 0.05, len(sample_data))
        dividend_impact = registry.dividend_announcement(sample_data)
        
        assert isinstance(dividend_impact, pd.Series)
        assert len(dividend_impact) == len(sample_data)
    
    def test_share_buyback_signal(self, registry, sample_data):
        """测试股票回购信号"""
        buyback_signal = registry.share_buyback_signal(sample_data)
        
        assert isinstance(buyback_signal, pd.Series)
        assert len(buyback_signal) == len(sample_data)
        assert buyback_signal.min() >= 0
    
    def test_share_buyback_signal_with_data(self, registry, sample_data):
        """测试有回购数据的信号"""
        sample_data['share_buyback'] = np.random.uniform(0, 1000000, len(sample_data))
        buyback_signal = registry.share_buyback_signal(sample_data)
        
        assert isinstance(buyback_signal, pd.Series)
        assert len(buyback_signal) == len(sample_data)
    
    def test_management_change(self, registry, sample_data):
        """测试管理层变动"""
        change_impact = registry.management_change(sample_data)
        
        assert isinstance(change_impact, pd.Series)
        assert len(change_impact) == len(sample_data)
    
    def test_management_change_with_data(self, registry, sample_data):
        """测试有管理层数据的变动影响"""
        sample_data['management_change'] = 0
        sample_data.loc[sample_data.index[30], 'management_change'] = 1
        change_impact = registry.management_change(sample_data)
        
        assert isinstance(change_impact, pd.Series)
        assert len(change_impact) == len(sample_data)
    
    def test_regulatory_approval(self, registry, sample_data):
        """测试监管批准"""
        approval_impact = registry.regulatory_approval(sample_data)
        
        assert isinstance(approval_impact, pd.Series)
        assert len(approval_impact) == len(sample_data)
    
    def test_regulatory_approval_with_data(self, registry, sample_data):
        """测试有监管数据的批准影响"""
        sample_data['regulatory_approval'] = 0
        sample_data.loc[sample_data.index[40], 'regulatory_approval'] = 1
        approval_impact = registry.regulatory_approval(sample_data)
        
        assert isinstance(approval_impact, pd.Series)
        assert len(approval_impact) == len(sample_data)
    
    def test_product_launch(self, registry, sample_data):
        """测试产品发布"""
        launch_impact = registry.product_launch(sample_data)
        
        assert isinstance(launch_impact, pd.Series)
        assert len(launch_impact) == len(sample_data)
        assert launch_impact.min() >= 0
    
    def test_product_launch_with_data(self, registry, sample_data):
        """测试有产品发布数据的影响"""
        sample_data['product_launch'] = 0
        sample_data.loc[sample_data.index[25], 'product_launch'] = 1
        launch_impact = registry.product_launch(sample_data)
        
        assert isinstance(launch_impact, pd.Series)
        assert len(launch_impact) == len(sample_data)
    
    def test_earnings_guidance_revision(self, registry, sample_data):
        """测试业绩指引修正"""
        revision_impact = registry.earnings_guidance_revision(sample_data)
        
        assert isinstance(revision_impact, pd.Series)
        assert len(revision_impact) == len(sample_data)
    
    def test_earnings_guidance_revision_with_data(self, registry, sample_data):
        """测试有指引数据的修正影响"""
        sample_data['earnings_guidance'] = np.random.uniform(1, 5, len(sample_data))
        revision_impact = registry.earnings_guidance_revision(sample_data)
        
        assert isinstance(revision_impact, pd.Series)
        assert len(revision_impact) == len(sample_data)
    
    def test_analyst_upgrade_downgrade(self, registry, sample_data):
        """测试分析师评级变动"""
        rating_impact = registry.analyst_upgrade_downgrade(sample_data)
        
        assert isinstance(rating_impact, pd.Series)
        assert len(rating_impact) == len(sample_data)
    
    def test_analyst_upgrade_downgrade_with_data(self, registry, sample_data):
        """测试有评级数据的变动影响"""
        sample_data['analyst_rating'] = np.random.uniform(1, 5, len(sample_data))
        rating_impact = registry.analyst_upgrade_downgrade(sample_data)
        
        assert isinstance(rating_impact, pd.Series)
        assert len(rating_impact) == len(sample_data)
    
    def test_index_rebalancing(self, registry, sample_data):
        """测试指数再平衡"""
        rebalancing_impact = registry.index_rebalancing(sample_data)
        
        assert isinstance(rebalancing_impact, pd.Series)
        assert len(rebalancing_impact) == len(sample_data)
    
    def test_index_rebalancing_with_data(self, registry, sample_data):
        """测试有指数数据的再平衡影响"""
        sample_data['index_weight'] = np.random.uniform(0, 0.1, len(sample_data))
        rebalancing_impact = registry.index_rebalancing(sample_data)
        
        assert isinstance(rebalancing_impact, pd.Series)
        assert len(rebalancing_impact) == len(sample_data)
    
    def test_corporate_action(self, registry, sample_data):
        """测试公司行动"""
        action_impact = registry.corporate_action(sample_data)
        
        assert isinstance(action_impact, pd.Series)
        assert len(action_impact) == len(sample_data)
    
    def test_corporate_action_with_data(self, registry, sample_data):
        """测试有公司行动数据的影响"""
        sample_data['corporate_action'] = 0
        sample_data.loc[sample_data.index[35], 'corporate_action'] = 1
        action_impact = registry.corporate_action(sample_data)
        
        assert isinstance(action_impact, pd.Series)
        assert len(action_impact) == len(sample_data)
    
    def test_litigation_risk(self, registry, sample_data):
        """测试诉讼风险"""
        risk = registry.litigation_risk(sample_data)
        
        assert isinstance(risk, pd.Series)
        assert len(risk) == len(sample_data)
    
    def test_litigation_risk_with_data(self, registry, sample_data):
        """测试有诉讼数据的风险"""
        sample_data['litigation_events'] = 0
        sample_data.loc[sample_data.index[45], 'litigation_events'] = 1
        risk = registry.litigation_risk(sample_data)
        
        assert isinstance(risk, pd.Series)
        assert len(risk) == len(sample_data)
    
    def test_credit_rating_change(self, registry, sample_data):
        """测试信用评级变动"""
        rating_change = registry.credit_rating_change(sample_data)
        
        assert isinstance(rating_change, pd.Series)
        assert len(rating_change) == len(sample_data)
    
    def test_credit_rating_change_with_data(self, registry, sample_data):
        """测试有评级数据的变动"""
        sample_data['credit_rating'] = np.random.uniform(1, 10, len(sample_data))
        rating_change = registry.credit_rating_change(sample_data)
        
        assert isinstance(rating_change, pd.Series)
        assert len(rating_change) == len(sample_data)
    
    def test_activist_investor_entry(self, registry, sample_data):
        """测试激进投资者进入"""
        activist_impact = registry.activist_investor_entry(sample_data)
        
        assert isinstance(activist_impact, pd.Series)
        assert len(activist_impact) == len(sample_data)
        assert activist_impact.min() >= 0
    
    def test_activist_investor_entry_with_data(self, registry, sample_data):
        """测试有激进投资者数据的影响"""
        sample_data['activist_entry'] = 0
        sample_data.loc[sample_data.index[55], 'activist_entry'] = 1
        activist_impact = registry.activist_investor_entry(sample_data)
        
        assert isinstance(activist_impact, pd.Series)
        assert len(activist_impact) == len(sample_data)



class TestEventDrivenFactorMiner:
    """测试事件驱动因子挖掘器"""
    
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
        miner = EventDrivenFactorMiner()
        
        assert miner.event_config.event_window == 20
        assert miner.event_config.earnings_threshold == 0.05
        assert isinstance(miner.operator_registry, EventDrivenOperatorRegistry)
        assert len(miner.event_history) == 0
    
    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        config = EventDrivenConfig(
            event_window=30,
            earnings_threshold=0.08
        )
        evolution_config = EvolutionConfig(population_size=30)
        
        miner = EventDrivenFactorMiner(
            config=config,
            evolution_config=evolution_config
        )
        
        assert miner.event_config.event_window == 30
        assert miner.event_config.earnings_threshold == 0.08
    
    def test_invalid_event_window(self):
        """测试无效的事件窗口"""
        config = EventDrivenConfig(event_window=0)
        
        with pytest.raises(ValueError, match="event_window必须 > 0"):
            EventDrivenFactorMiner(config=config)
    
    def test_invalid_earnings_threshold(self):
        """测试无效的盈利阈值"""
        config = EventDrivenConfig(earnings_threshold=1.5)
        
        with pytest.raises(ValueError, match="earnings_threshold必须在\\[0, 1\\]范围内"):
            EventDrivenFactorMiner(config=config)
    
    def test_invalid_merger_spread_threshold(self):
        """测试无效的并购价差阈值"""
        config = EventDrivenConfig(merger_spread_threshold=-0.1)
        
        with pytest.raises(ValueError, match="merger_spread_threshold必须在\\[0, 1\\]范围内"):
            EventDrivenFactorMiner(config=config)
    
    def test_invalid_min_event_impact(self):
        """测试无效的最小事件影响"""
        config = EventDrivenConfig(min_event_impact=2.0)
        
        with pytest.raises(ValueError, match="min_event_impact必须在\\[0, 1\\]范围内"):
            EventDrivenFactorMiner(config=config)
    
    def test_operator_whitelist_extension(self):
        """测试算子白名单扩展"""
        miner = EventDrivenFactorMiner()
        
        expected_operators = [
            'earnings_surprise',
            'merger_arbitrage_spread',
            'ipo_lockup_expiry',
            'dividend_announcement',
            'share_buyback_signal',
            'management_change',
            'regulatory_approval',
            'product_launch',
            'earnings_guidance_revision',
            'analyst_upgrade_downgrade',
            'index_rebalancing',
            'corporate_action',
            'litigation_risk',
            'credit_rating_change',
            'activist_investor_entry'
        ]
        
        for operator in expected_operators:
            assert operator in miner.operator_whitelist
    
    def test_detect_earnings_events(self, sample_data):
        """测试盈利事件检测"""
        miner = EventDrivenFactorMiner()
        earnings_events = miner.detect_earnings_events(sample_data)
        
        assert isinstance(earnings_events, pd.Series)
        assert len(earnings_events) == len(sample_data)
        assert set(earnings_events.unique()).issubset({0, 1})
    
    def test_detect_earnings_events_empty_data(self):
        """测试空数据的盈利事件检测"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        earnings_events = miner.detect_earnings_events(empty_data)
        
        assert isinstance(earnings_events, pd.Series)
        assert len(earnings_events) == 0
    
    def test_detect_ma_events(self, sample_data):
        """测试并购事件检测"""
        miner = EventDrivenFactorMiner()
        ma_events = miner.detect_ma_events(sample_data)
        
        assert isinstance(ma_events, pd.Series)
        assert len(ma_events) == len(sample_data)
        assert set(ma_events.unique()).issubset({0, 1})
    
    def test_detect_ma_events_empty_data(self):
        """测试空数据的并购事件检测"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        ma_events = miner.detect_ma_events(empty_data)
        
        assert isinstance(ma_events, pd.Series)
        assert len(ma_events) == 0
    
    def test_detect_corporate_events(self, sample_data):
        """测试公司事件检测"""
        miner = EventDrivenFactorMiner()
        corporate_events = miner.detect_corporate_events(sample_data)
        
        assert isinstance(corporate_events, pd.Series)
        assert len(corporate_events) == len(sample_data)
        assert set(corporate_events.unique()).issubset({0, 1})
    
    def test_detect_corporate_events_empty_data(self):
        """测试空数据的公司事件检测"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        corporate_events = miner.detect_corporate_events(empty_data)
        
        assert isinstance(corporate_events, pd.Series)
        assert len(corporate_events) == 0
    
    def test_analyze_event_impact(self, sample_data):
        """测试事件影响分析"""
        miner = EventDrivenFactorMiner()
        event_impacts = miner.analyze_event_impact(sample_data)
        
        assert isinstance(event_impacts, dict)
        assert 'earnings_surprise' in event_impacts
        assert 'merger_spread' in event_impacts
        assert 'dividend' in event_impacts
        assert 'buyback' in event_impacts
        assert 'analyst_rating' in event_impacts
        assert 'index_rebalancing' in event_impacts
        assert 'litigation' in event_impacts
        assert 'credit_rating' in event_impacts
        
        for impact in event_impacts.values():
            assert isinstance(impact, pd.Series)
            assert len(impact) == len(sample_data)
    
    def test_analyze_event_impact_empty_data(self):
        """测试空数据的事件影响分析"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        event_impacts = miner.analyze_event_impact(empty_data)
        
        assert isinstance(event_impacts, dict)
        assert len(event_impacts) == 0
    
    def test_calculate_event_composite_score(self, sample_data):
        """测试事件综合评分"""
        miner = EventDrivenFactorMiner()
        composite_score = miner.calculate_event_composite_score(sample_data)
        
        assert isinstance(composite_score, pd.Series)
        assert len(composite_score) == len(sample_data)
    
    def test_calculate_event_composite_score_empty_data(self):
        """测试空数据的事件综合评分"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        composite_score = miner.calculate_event_composite_score(empty_data)
        
        assert isinstance(composite_score, pd.Series)
        assert len(composite_score) == 0
    
    def test_identify_catalyst_events(self, sample_data):
        """测试催化剂事件识别"""
        miner = EventDrivenFactorMiner()
        catalysts = miner.identify_catalyst_events(sample_data, threshold=0.3)
        
        assert isinstance(catalysts, list)
        for catalyst in catalysts:
            assert 'date' in catalyst
            assert 'score' in catalyst
            assert 'type' in catalyst
            assert 'magnitude' in catalyst
            assert catalyst['type'] in ['positive', 'negative']
    
    def test_identify_catalyst_events_empty_data(self):
        """测试空数据的催化剂事件识别"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        catalysts = miner.identify_catalyst_events(empty_data)
        
        assert isinstance(catalysts, list)
        assert len(catalysts) == 0
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, sample_data, sample_returns):
        """测试因子挖掘"""
        evolution_config = EvolutionConfig(population_size=10)
        miner = EventDrivenFactorMiner(evolution_config=evolution_config)
        
        factors = await miner.mine_factors(sample_data, sample_returns, generations=2)
        
        assert isinstance(factors, list)
        assert len(factors) <= 10
        assert all(hasattr(f, 'fitness') for f in factors)
    
    @pytest.mark.asyncio
    async def test_mine_factors_empty_data(self, sample_returns):
        """测试空数据的因子挖掘"""
        miner = EventDrivenFactorMiner()
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="输入数据为空"):
            await miner.mine_factors(empty_data, sample_returns)
    
    def test_get_event_report(self):
        """测试事件报告"""
        miner = EventDrivenFactorMiner()
        report = miner.get_event_report()
        
        assert isinstance(report, dict)
        assert 'total_events' in report
        assert 'events_by_type' in report
        assert 'event_window' in report
        assert 'earnings_threshold' in report
        assert 'merger_spread_threshold' in report
        assert 'min_event_impact' in report
        
        assert report['event_window'] == 20
        assert report['earnings_threshold'] == 0.05
        assert report['merger_spread_threshold'] == 0.1
        assert report['min_event_impact'] == 0.01


class TestEventDrivenIntegration:
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
        
        # 添加事件（盈利公告导致跳空）
        close[60] = close[59] * 1.08  # 盈利超预期
        close[120] = close[119] * 0.95  # 盈利低于预期
        close[180] = close[179] * 1.05  # 并购公告
        
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
        config = EventDrivenConfig(
            event_window=20,
            earnings_threshold=0.05,
            merger_spread_threshold=0.1
        )
        evolution_config = EvolutionConfig(population_size=20)
        miner = EventDrivenFactorMiner(
            config=config,
            evolution_config=evolution_config
        )
        
        # 2. 检测盈利事件
        earnings_events = miner.detect_earnings_events(realistic_data)
        assert len(earnings_events) == len(realistic_data)
        
        # 3. 检测并购事件
        ma_events = miner.detect_ma_events(realistic_data)
        assert len(ma_events) == len(realistic_data)
        
        # 4. 检测公司事件
        corporate_events = miner.detect_corporate_events(realistic_data)
        assert len(corporate_events) == len(realistic_data)
        
        # 5. 分析事件影响
        event_impacts = miner.analyze_event_impact(realistic_data)
        assert len(event_impacts) == 8
        
        # 6. 计算综合评分
        composite_score = miner.calculate_event_composite_score(realistic_data)
        assert len(composite_score) == len(realistic_data)
        
        # 7. 识别催化剂事件
        catalysts = miner.identify_catalyst_events(realistic_data, threshold=0.3)
        assert isinstance(catalysts, list)
        
        # 8. 挖掘因子
        returns = realistic_data['close'].pct_change().fillna(0)
        factors = await miner.mine_factors(realistic_data, returns, generations=2)
        assert len(factors) > 0
        
        # 9. 获取报告
        report = miner.get_event_report()
        assert report['total_events'] >= 0
