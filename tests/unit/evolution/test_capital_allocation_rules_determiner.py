"""资金配置规则确定器测试

白皮书依据: 第四章 4.3.2 资金配置规则确定

测试资金配置规则确定器的功能。
"""

import pytest
from typing import Dict, Any

from src.evolution.capital_allocation_rules_determiner import (
    CapitalAllocationRulesDeterminer,
    LiquidityAnalysis,
    MarketImpactAnalysis
)
from src.evolution.z2h_data_models import (
    CertificationLevel,
    CapitalTier,
    CapitalAllocationRules
)


class TestCapitalAllocationRulesDeterminer:
    """测试资金配置规则确定器"""
    
    @pytest.fixture
    def determiner(self) -> CapitalAllocationRulesDeterminer:
        """创建确定器实例"""
        return CapitalAllocationRulesDeterminer()
    
    @pytest.fixture
    def simulation_metrics(self) -> Dict[str, float]:
        """创建模拟盘指标"""
        return {
            'sharpe_ratio': 2.0,
            'max_drawdown': 0.15,
            'win_rate': 0.60,
            'volatility': 0.20,
            'total_return': 0.30
        }
    
    @pytest.fixture
    def strategy_characteristics(self) -> Dict[str, Any]:
        """创建策略特征"""
        return {
            'avg_position_count': 10,
            'avg_holding_period_days': 5,
            'turnover_rate': 2.0
        }
    
    def test_determiner_initialization(self):
        """测试确定器初始化"""
        determiner = CapitalAllocationRulesDeterminer(
            platinum_ratio=0.20,
            gold_ratio=0.15,
            silver_ratio=0.10
        )
        
        assert determiner.platinum_ratio == 0.20
        assert determiner.gold_ratio == 0.15
        assert determiner.silver_ratio == 0.10
    
    def test_determiner_initialization_invalid_ratio_range(self):
        """测试确定器初始化时配置比例范围无效"""
        with pytest.raises(ValueError, match="白金级配置比例必须在\\[0, 1\\]范围内"):
            CapitalAllocationRulesDeterminer(platinum_ratio=1.5)
        
        with pytest.raises(ValueError, match="黄金级配置比例必须在\\[0, 1\\]范围内"):
            CapitalAllocationRulesDeterminer(gold_ratio=-0.1)
        
        with pytest.raises(ValueError, match="白银级配置比例必须在\\[0, 1\\]范围内"):
            CapitalAllocationRulesDeterminer(silver_ratio=2.0)
    
    def test_determiner_initialization_invalid_ratio_order(self):
        """测试确定器初始化时配置比例顺序无效"""
        with pytest.raises(ValueError, match="配置比例顺序必须满足"):
            CapitalAllocationRulesDeterminer(
                platinum_ratio=0.10,
                gold_ratio=0.15,
                silver_ratio=0.20
            )
    
    def test_determine_rules_platinum(
        self,
        determiner,
        simulation_metrics,
        strategy_characteristics
    ):
        """测试确定PLATINUM等级的资金配置规则"""
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_3,
            simulation_metrics=simulation_metrics,
            strategy_characteristics=strategy_characteristics
        )
        
        assert isinstance(rules, CapitalAllocationRules)
        assert rules.max_allocation_ratio == 0.20
        assert rules.recommended_tier == CapitalTier.TIER_3
        assert rules.min_capital == 50000
        assert rules.max_capital <= 500000
        assert rules.optimal_capital > 0
    
    def test_determine_rules_gold(
        self,
        determiner,
        simulation_metrics,
        strategy_characteristics
    ):
        """测试确定GOLD等级的资金配置规则"""
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=simulation_metrics,
            strategy_characteristics=strategy_characteristics
        )
        
        assert rules.max_allocation_ratio == 0.15
        assert rules.recommended_tier == CapitalTier.TIER_2
        assert rules.min_capital == 10000
        assert rules.max_capital <= 50000
    
    def test_determine_rules_silver(
        self,
        determiner,
        simulation_metrics,
        strategy_characteristics
    ):
        """测试确定SILVER等级的资金配置规则"""
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.SILVER,
            best_tier=CapitalTier.TIER_1,
            simulation_metrics=simulation_metrics,
            strategy_characteristics=strategy_characteristics
        )
        
        assert rules.max_allocation_ratio == 0.10
        assert rules.recommended_tier == CapitalTier.TIER_1
        assert rules.min_capital == 1000
        assert rules.max_capital <= 10000
    
    def test_determine_rules_none_level_rejection(
        self,
        determiner,
        simulation_metrics
    ):
        """测试未认证等级拒绝确定规则"""
        with pytest.raises(ValueError, match="未认证策略不能确定资金配置规则"):
            determiner.determine_rules(
                certification_level=CertificationLevel.NONE,
                best_tier=CapitalTier.TIER_1,
                simulation_metrics=simulation_metrics
            )
    
    def test_determine_rules_empty_metrics_rejection(self, determiner):
        """测试空指标拒绝确定规则"""
        with pytest.raises(ValueError, match="模拟盘指标不能为空"):
            determiner.determine_rules(
                certification_level=CertificationLevel.PLATINUM,
                best_tier=CapitalTier.TIER_1,
                simulation_metrics={}
            )
    
    def test_get_max_allocation_ratio_platinum(self, determiner):
        """测试获取PLATINUM最大配置比例"""
        ratio = determiner._get_max_allocation_ratio(CertificationLevel.PLATINUM)
        assert ratio == 0.20
    
    def test_get_max_allocation_ratio_gold(self, determiner):
        """测试获取GOLD最大配置比例"""
        ratio = determiner._get_max_allocation_ratio(CertificationLevel.GOLD)
        assert ratio == 0.15
    
    def test_get_max_allocation_ratio_silver(self, determiner):
        """测试获取SILVER最大配置比例"""
        ratio = determiner._get_max_allocation_ratio(CertificationLevel.SILVER)
        assert ratio == 0.10
    
    def test_get_max_allocation_ratio_none(self, determiner):
        """测试获取NONE最大配置比例"""
        ratio = determiner._get_max_allocation_ratio(CertificationLevel.NONE)
        assert ratio == 0.0
    
    def test_determine_optimal_capital_scale_tier1(
        self,
        determiner,
        simulation_metrics
    ):
        """测试确定TIER1最优资金规模"""
        optimal = determiner._determine_optimal_capital_scale(
            CapitalTier.TIER_1,
            simulation_metrics
        )
        
        assert 1000 <= optimal <= 10000
    
    def test_determine_optimal_capital_scale_tier2(
        self,
        determiner,
        simulation_metrics
    ):
        """测试确定TIER2最优资金规模"""
        optimal = determiner._determine_optimal_capital_scale(
            CapitalTier.TIER_2,
            simulation_metrics
        )
        
        assert 10000 <= optimal <= 50000
    
    def test_determine_optimal_capital_scale_tier3(
        self,
        determiner,
        simulation_metrics
    ):
        """测试确定TIER3最优资金规模"""
        optimal = determiner._determine_optimal_capital_scale(
            CapitalTier.TIER_3,
            simulation_metrics
        )
        
        assert 50000 <= optimal <= 500000
    
    def test_determine_optimal_capital_scale_tier4(
        self,
        determiner,
        simulation_metrics
    ):
        """测试确定TIER4最优资金规模"""
        optimal = determiner._determine_optimal_capital_scale(
            CapitalTier.TIER_4,
            simulation_metrics
        )
        
        assert 500000 <= optimal <= 5000000
    
    def test_determine_optimal_capital_scale_high_performance(self, determiner):
        """测试高性能策略的最优资金规模"""
        high_performance_metrics = {
            'sharpe_ratio': 3.0,
            'max_drawdown': 0.05,
            'win_rate': 0.70
        }
        
        optimal = determiner._determine_optimal_capital_scale(
            CapitalTier.TIER_2,
            high_performance_metrics
        )
        
        # 高性能应该接近上限
        assert optimal > 30000
    
    def test_determine_optimal_capital_scale_low_performance(self, determiner):
        """测试低性能策略的最优资金规模"""
        low_performance_metrics = {
            'sharpe_ratio': 0.5,
            'max_drawdown': 0.30,
            'win_rate': 0.45
        }
        
        optimal = determiner._determine_optimal_capital_scale(
            CapitalTier.TIER_2,
            low_performance_metrics
        )
        
        # 低性能应该接近下限
        assert optimal < 30000
    
    def test_analyze_liquidity_requirements(
        self,
        determiner,
        simulation_metrics,
        strategy_characteristics
    ):
        """测试分析流动性需求"""
        analysis = determiner._analyze_liquidity_requirements(
            simulation_metrics,
            strategy_characteristics
        )
        
        assert isinstance(analysis, LiquidityAnalysis)
        assert analysis.avg_daily_volume > 0
        assert 0.0 <= analysis.liquidity_score <= 1.0
        assert analysis.max_position_size > 0
        assert analysis.recommended_max_capital > 0
    
    def test_analyze_liquidity_requirements_without_characteristics(
        self,
        determiner,
        simulation_metrics
    ):
        """测试没有策略特征时分析流动性需求"""
        analysis = determiner._analyze_liquidity_requirements(
            simulation_metrics,
            None
        )
        
        assert isinstance(analysis, LiquidityAnalysis)
        assert analysis.avg_daily_volume > 0
    
    def test_analyze_market_impact(
        self,
        determiner,
        simulation_metrics,
        strategy_characteristics
    ):
        """测试分析市场冲击"""
        analysis = determiner._analyze_market_impact(
            simulation_metrics,
            strategy_characteristics
        )
        
        assert isinstance(analysis, MarketImpactAnalysis)
        assert 0.0 <= analysis.estimated_impact <= 0.01
        assert analysis.optimal_order_size > 0
        assert analysis.max_order_size > 0
        assert analysis.recommended_split_count >= 1
    
    def test_analyze_market_impact_without_characteristics(
        self,
        determiner,
        simulation_metrics
    ):
        """测试没有策略特征时分析市场冲击"""
        analysis = determiner._analyze_market_impact(
            simulation_metrics,
            None
        )
        
        assert isinstance(analysis, MarketImpactAnalysis)
        assert analysis.estimated_impact >= 0
    
    def test_calculate_performance_score_excellent(self, determiner):
        """测试计算优秀性能评分"""
        score = determiner._calculate_performance_score(
            sharpe_ratio=3.0,
            max_drawdown=0.05,
            win_rate=0.70
        )
        
        assert 0.8 <= score <= 1.0
    
    def test_calculate_performance_score_poor(self, determiner):
        """测试计算较差性能评分"""
        score = determiner._calculate_performance_score(
            sharpe_ratio=0.5,
            max_drawdown=0.30,
            win_rate=0.45
        )
        
        assert 0.0 <= score <= 0.3
    
    def test_calculate_performance_score_average(self, determiner):
        """测试计算平均性能评分"""
        score = determiner._calculate_performance_score(
            sharpe_ratio=1.5,
            max_drawdown=0.15,
            win_rate=0.55
        )
        
        assert 0.3 <= score <= 0.8
    
    def test_calculate_position_limit_platinum(self, determiner, simulation_metrics):
        """测试计算PLATINUM单股仓位限制"""
        limit = determiner._calculate_position_limit(
            CertificationLevel.PLATINUM,
            simulation_metrics
        )
        
        assert limit == 0.10
    
    def test_calculate_position_limit_gold(self, determiner, simulation_metrics):
        """测试计算GOLD单股仓位限制"""
        limit = determiner._calculate_position_limit(
            CertificationLevel.GOLD,
            simulation_metrics
        )
        
        assert limit == 0.08
    
    def test_calculate_position_limit_silver(self, determiner, simulation_metrics):
        """测试计算SILVER单股仓位限制"""
        limit = determiner._calculate_position_limit(
            CertificationLevel.SILVER,
            simulation_metrics
        )
        
        assert limit == 0.05
    
    def test_calculate_position_limit_high_volatility(self, determiner):
        """测试高波动率时的仓位限制"""
        high_vol_metrics = {
            'volatility': 0.35,
            'sharpe_ratio': 2.0
        }
        
        limit = determiner._calculate_position_limit(
            CertificationLevel.PLATINUM,
            high_vol_metrics
        )
        
        # 高波动应该降低仓位
        assert limit < 0.10
    
    def test_calculate_sector_exposure_limit_platinum(self, determiner):
        """测试计算PLATINUM行业敞口限制"""
        limit = determiner._calculate_sector_exposure_limit(
            CertificationLevel.PLATINUM
        )
        
        assert limit == 0.30
    
    def test_calculate_sector_exposure_limit_gold(self, determiner):
        """测试计算GOLD行业敞口限制"""
        limit = determiner._calculate_sector_exposure_limit(
            CertificationLevel.GOLD
        )
        
        assert limit == 0.25
    
    def test_calculate_sector_exposure_limit_silver(self, determiner):
        """测试计算SILVER行业敞口限制"""
        limit = determiner._calculate_sector_exposure_limit(
            CertificationLevel.SILVER
        )
        
        assert limit == 0.20
    
    def test_calculate_max_leverage_platinum(self, determiner):
        """测试计算PLATINUM最大杠杆"""
        leverage = determiner._calculate_max_leverage(
            CertificationLevel.PLATINUM
        )
        
        assert leverage == 2.0
    
    def test_calculate_max_leverage_gold(self, determiner):
        """测试计算GOLD最大杠杆"""
        leverage = determiner._calculate_max_leverage(
            CertificationLevel.GOLD
        )
        
        assert leverage == 1.5
    
    def test_calculate_max_leverage_silver(self, determiner):
        """测试计算SILVER最大杠杆"""
        leverage = determiner._calculate_max_leverage(
            CertificationLevel.SILVER
        )
        
        assert leverage == 1.0
    
    def test_calculate_liquidity_buffer_platinum(self, determiner):
        """测试计算PLATINUM流动性缓冲"""
        liquidity_analysis = LiquidityAnalysis(
            avg_daily_volume=10000000,
            liquidity_score=0.8,
            max_position_size=500000,
            recommended_max_capital=5000000
        )
        
        buffer = determiner._calculate_liquidity_buffer(
            CertificationLevel.PLATINUM,
            liquidity_analysis
        )
        
        assert 0.0 <= buffer <= 0.20
    
    def test_calculate_liquidity_buffer_gold(self, determiner):
        """测试计算GOLD流动性缓冲"""
        liquidity_analysis = LiquidityAnalysis(
            avg_daily_volume=10000000,
            liquidity_score=0.6,
            max_position_size=500000,
            recommended_max_capital=5000000
        )
        
        buffer = determiner._calculate_liquidity_buffer(
            CertificationLevel.GOLD,
            liquidity_analysis
        )
        
        assert 0.0 <= buffer <= 0.20
    
    def test_calculate_liquidity_buffer_silver(self, determiner):
        """测试计算SILVER流动性缓冲"""
        liquidity_analysis = LiquidityAnalysis(
            avg_daily_volume=10000000,
            liquidity_score=0.4,
            max_position_size=500000,
            recommended_max_capital=5000000
        )
        
        buffer = determiner._calculate_liquidity_buffer(
            CertificationLevel.SILVER,
            liquidity_analysis
        )
        
        assert 0.0 <= buffer <= 0.25
    
    def test_tier_capital_ranges(self):
        """测试各档位资金范围"""
        ranges = CapitalAllocationRulesDeterminer.TIER_CAPITAL_RANGES
        
        assert ranges[CapitalTier.TIER_1] == (1000, 10000)
        assert ranges[CapitalTier.TIER_2] == (10000, 50000)
        assert ranges[CapitalTier.TIER_3] == (50000, 500000)
        assert ranges[CapitalTier.TIER_4] == (500000, 5000000)
    
    def test_liquidity_analysis_dataclass(self):
        """测试LiquidityAnalysis数据类"""
        analysis = LiquidityAnalysis(
            avg_daily_volume=10000000,
            liquidity_score=0.8,
            max_position_size=500000,
            recommended_max_capital=5000000
        )
        
        assert analysis.avg_daily_volume == 10000000
        assert analysis.liquidity_score == 0.8
        assert analysis.max_position_size == 500000
        assert analysis.recommended_max_capital == 5000000
    
    def test_market_impact_analysis_dataclass(self):
        """测试MarketImpactAnalysis数据类"""
        analysis = MarketImpactAnalysis(
            estimated_impact=0.005,
            optimal_order_size=100000,
            max_order_size=500000,
            recommended_split_count=5
        )
        
        assert analysis.estimated_impact == 0.005
        assert analysis.optimal_order_size == 100000
        assert analysis.max_order_size == 500000
        assert analysis.recommended_split_count == 5
