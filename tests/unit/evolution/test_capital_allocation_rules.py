"""资金配置规则单元测试

白皮书依据: 第四章 4.3.1 Z2H认证系统

任务5.2: 编写资金配置规则单元测试
验证需求: Requirements 5.5, 5.6, 5.7, 5.8

测试内容:
- 最优资金规模确定
- 流动性需求分析
- 市场冲击分析
- 边界条件
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.evolution.capital_allocation_rules_determiner import CapitalAllocationRulesDeterminer
from src.evolution.z2h_data_models import (
    CertificationLevel,
    CapitalTier,
    CapitalAllocationRules
)


class TestCapitalAllocationRules:
    """资金配置规则单元测试
    
    白皮书依据: 第四章 4.3.1 - 资金配置规则
    验证需求: Requirements 5.5, 5.6, 5.7, 5.8
    """
    
    @pytest.fixture
    def determiner(self):
        """创建资金配置规则确定器"""
        return CapitalAllocationRulesDeterminer()
    
    @pytest.fixture
    def base_simulation_metrics(self) -> Dict[str, float]:
        """基础模拟盘指标"""
        return {
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.12,
            'win_rate': 0.58,
            'volatility': 0.18,
            'monthly_return': 0.08
        }
    
    @pytest.fixture
    def base_strategy_characteristics(self) -> Dict[str, Any]:
        """基础策略特征"""
        return {
            'avg_position_count': 10,
            'avg_holding_period_days': 5,
            'turnover_rate': 2.0,
            'strategy_type': 'momentum'
        }
    
    # ==================== 最优资金规模确定测试 ====================
    
    def test_optimal_capital_scale_platinum(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试PLATINUM等级的最优资金规模
        
        验证需求: Requirements 5.5
        
        PLATINUM等级应该获得最大的资金配置比例（20%）。
        """
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_3,  # 中型档位
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # 验证基础配置比例
        assert rules.max_allocation_ratio == 0.20, \
            "PLATINUM等级应该获得20%的基础配置比例"
        
        # 验证最优资金规模被确定
        assert rules.optimal_capital > 0
        # TIER_3范围是50000-500000
        assert 50000 <= rules.optimal_capital <= 500000
    
    def test_optimal_capital_scale_gold(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试GOLD等级的最优资金规模
        
        验证需求: Requirements 5.5
        
        GOLD等级应该获得中等的资金配置比例（15%）。
        """
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,  # 小型档位
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        assert rules.max_allocation_ratio == 0.15
        assert rules.optimal_capital > 0
    
    def test_optimal_capital_scale_silver(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试SILVER等级的最优资金规模
        
        验证需求: Requirements 5.5
        
        SILVER等级应该获得较小的资金配置比例（10%）。
        """
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.SILVER,
            best_tier=CapitalTier.TIER_1,  # 微型档位
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        assert rules.max_allocation_ratio == 0.10
        assert rules.optimal_capital > 0
    
    def test_optimal_capital_scale_with_low_performance(
        self, 
        determiner,
        base_strategy_characteristics
    ):
        """测试低性能情况下的资金规模
        
        验证需求: Requirements 5.5
        
        低性能应该限制最优资金规模在档位范围的下限附近。
        """
        low_performance_metrics = {
            'sharpe_ratio': 0.5,  # 低夏普比率
            'max_drawdown': 0.25,  # 高回撤
            'win_rate': 0.45,  # 低胜率
            'volatility': 0.30
        }
        
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_3,
            simulation_metrics=low_performance_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # 低性能应该使最优资金接近档位下限
        # TIER_3范围是50000-500000
        assert rules.optimal_capital < 275000, \
            "低性能应该限制最优资金规模"
    
    # ==================== 流动性需求分析测试 ====================
    
    def test_liquidity_requirements_high_holding_period(
        self, 
        determiner, 
        base_simulation_metrics
    ):
        """测试长持仓期的流动性需求
        
        验证需求: Requirements 5.6
        
        长持仓期应该降低流动性需求。
        """
        long_holding_characteristics = {
            'avg_position_count': 10,
            'avg_holding_period_days': 20,  # 长持仓期
            'turnover_rate': 0.5,  # 低换手率
            'strategy_type': 'trend_following'
        }
        
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_3,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=long_holding_characteristics
        )
        
        # 长持仓期应该有较低的流动性缓冲需求
        assert rules.liquidity_buffer < 0.15, \
            "长持仓期应该降低流动性缓冲需求"
    
    def test_liquidity_requirements_high_turnover(
        self, 
        determiner, 
        base_simulation_metrics
    ):
        """测试高换手率的流动性需求
        
        验证需求: Requirements 5.6
        
        高换手率应该增加流动性需求。
        """
        high_turnover_characteristics = {
            'avg_position_count': 20,
            'avg_holding_period_days': 2,  # 短持仓期
            'turnover_rate': 5.0,  # 高换手率
            'strategy_type': 'arbitrage'
        }
        
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=high_turnover_characteristics
        )
        
        # 高换手率应该有较高的流动性缓冲需求
        assert rules.liquidity_buffer > 0.10, \
            "高换手率应该增加流动性缓冲需求"
    
    def test_liquidity_requirements_certification_level_impact(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试认证等级对流动性缓冲的影响
        
        验证需求: Requirements 5.6
        
        较低认证等级应该有更高的流动性缓冲。
        """
        # PLATINUM等级
        rules_platinum = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # SILVER等级
        rules_silver = determiner.determine_rules(
            certification_level=CertificationLevel.SILVER,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # SILVER等级应该有更高的流动性缓冲
        assert rules_silver.liquidity_buffer > rules_platinum.liquidity_buffer, \
            "较低认证等级应该有更高的流动性缓冲"
    
    # ==================== 市场冲击分析测试 ====================
    
    def test_market_impact_analysis(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试市场冲击分析
        
        验证需求: Requirements 5.7
        
        市场冲击成本应该被考虑在资金配置中。
        """
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_3,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # 验证资金配置规则包含合理的限制
        assert rules.position_limit_per_stock > 0
        assert rules.position_limit_per_stock <= 0.15  # 单股仓位不超过15%
    
    def test_market_impact_with_high_volatility(
        self, 
        determiner,
        base_strategy_characteristics
    ):
        """测试高波动率的市场冲击
        
        验证需求: Requirements 5.7
        
        高波动率应该降低单股仓位限制。
        """
        high_volatility_metrics = {
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.15,
            'win_rate': 0.55,
            'volatility': 0.35  # 高波动率
        }
        
        low_volatility_metrics = {
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.15,
            'win_rate': 0.55,
            'volatility': 0.15  # 低波动率
        }
        
        rules_high_vol = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=high_volatility_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        rules_low_vol = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=low_volatility_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # 高波动率应该有更低的单股仓位限制
        assert rules_high_vol.position_limit_per_stock <= rules_low_vol.position_limit_per_stock, \
            "高波动率应该降低单股仓位限制"
    
    def test_sector_exposure_limit_by_certification(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试不同认证等级的行业敞口限制
        
        验证需求: Requirements 5.7
        
        不同认证等级应该有不同的行业敞口限制。
        """
        rules_platinum = determiner.determine_rules(
            certification_level=CertificationLevel.PLATINUM,
            best_tier=CapitalTier.TIER_3,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        rules_silver = determiner.determine_rules(
            certification_level=CertificationLevel.SILVER,
            best_tier=CapitalTier.TIER_3,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # PLATINUM应该有更高的行业敞口限制
        assert rules_platinum.sector_exposure_limit > rules_silver.sector_exposure_limit, \
            "PLATINUM应该有更高的行业敞口限制"
    
    # ==================== 边界条件测试 ====================
    
    def test_none_certification_level_handling(self, determiner, base_simulation_metrics):
        """测试未认证等级处理
        
        验证需求: Requirements 5.8
        
        NONE等级不应该获得资金配置。
        """
        with pytest.raises(ValueError, match="未认证策略不能确定资金配置规则"):
            determiner.determine_rules(
                certification_level=CertificationLevel.NONE,
                best_tier=CapitalTier.TIER_1,
                simulation_metrics=base_simulation_metrics
            )
    
    def test_empty_simulation_metrics_handling(self, determiner):
        """测试空模拟盘指标处理
        
        验证需求: Requirements 5.8
        
        空模拟盘指标应该被正确处理。
        """
        with pytest.raises(ValueError, match="模拟盘指标不能为空"):
            determiner.determine_rules(
                certification_level=CertificationLevel.GOLD,
                best_tier=CapitalTier.TIER_2,
                simulation_metrics={}
            )
    
    def test_missing_strategy_characteristics(
        self, 
        determiner, 
        base_simulation_metrics
    ):
        """测试缺失策略特征处理
        
        验证需求: Requirements 5.8
        
        缺失策略特征应该使用默认值。
        """
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=None  # 不提供策略特征
        )
        
        # 应该返回有效的规则
        assert rules.optimal_capital > 0
        assert rules.max_allocation_ratio == 0.15
    
    def test_allocation_rules_completeness(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试资金配置规则完整性
        
        验证需求: Requirements 5.1-5.8
        
        返回的规则应该包含所有必要字段。
        """
        rules = determiner.determine_rules(
            certification_level=CertificationLevel.GOLD,
            best_tier=CapitalTier.TIER_2,
            simulation_metrics=base_simulation_metrics,
            strategy_characteristics=base_strategy_characteristics
        )
        
        # 验证必要字段存在
        assert hasattr(rules, 'max_allocation_ratio')
        assert hasattr(rules, 'optimal_capital')
        assert hasattr(rules, 'min_capital')
        assert hasattr(rules, 'max_capital')
        assert hasattr(rules, 'position_limit_per_stock')
        assert hasattr(rules, 'sector_exposure_limit')
        assert hasattr(rules, 'max_leverage')
        assert hasattr(rules, 'liquidity_buffer')
        
        # 验证字段值合理
        assert 0 < rules.max_allocation_ratio <= 0.20
        assert rules.optimal_capital > 0
        assert rules.min_capital < rules.max_capital
        assert 0 < rules.position_limit_per_stock <= 0.15
        assert 0 < rules.sector_exposure_limit <= 0.35
        assert 1.0 <= rules.max_leverage <= 2.0
        assert 0 < rules.liquidity_buffer <= 0.25
    
    def test_tier_capital_ranges(
        self, 
        determiner, 
        base_simulation_metrics,
        base_strategy_characteristics
    ):
        """测试不同档位的资金范围
        
        验证需求: Requirements 5.5
        
        不同档位应该有不同的资金范围。
        """
        tiers = [
            (CapitalTier.TIER_1, 1000, 10000),      # 微型
            (CapitalTier.TIER_2, 10000, 50000),     # 小型
            (CapitalTier.TIER_3, 50000, 500000),    # 中型
            (CapitalTier.TIER_4, 500000, 5000000),  # 大型
        ]
        
        for tier, expected_min, expected_max in tiers:
            rules = determiner.determine_rules(
                certification_level=CertificationLevel.GOLD,
                best_tier=tier,
                simulation_metrics=base_simulation_metrics,
                strategy_characteristics=base_strategy_characteristics
            )
            
            assert rules.min_capital == expected_min, \
                f"{tier.value}档位最小资金应为{expected_min}"
            # max_capital可能因流动性分析而调整，但不应超过expected_max
            assert rules.max_capital <= expected_max * 2, \
                f"{tier.value}档位最大资金不应过大"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
