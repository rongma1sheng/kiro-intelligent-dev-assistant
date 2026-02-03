"""Z2H认证系统集成测试

白皮书依据: 第四章 4.2-4.3 Z2H认证系统

本模块测试Z2H认证系统各组件之间的集成，包括：
- Z2HCertificationV2与CertificationLevelEvaluator的集成
- Z2HCertificationV2与CapitalAllocationRulesDeterminer的集成
- Z2HCertificationV2与SimulationManager的集成
- 认证状态管理集成
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from src.evolution.z2h_certification_v2 import Z2HCertificationV2
from src.evolution.certification_level_evaluator import CertificationLevelEvaluator
from src.evolution.capital_allocation_rules_determiner import CapitalAllocationRulesDeterminer
from src.evolution.z2h_data_models import (
    CertificationLevel,
    CertificationStatus,
    CapitalTier,
    SimulationResult,
    TierSimulationResult,
    Z2HGeneCapsule
)


@pytest.fixture
def level_evaluator():
    """创建认证等级评估器"""
    return CertificationLevelEvaluator()


@pytest.fixture
def capital_rules_determiner():
    """创建资金配置规则确定器"""
    return CapitalAllocationRulesDeterminer()


@pytest.fixture
def z2h_certification(level_evaluator, capital_rules_determiner):
    """创建Z2H认证系统"""
    return Z2HCertificationV2(
        level_evaluator=level_evaluator,
        capital_rules_determiner=capital_rules_determiner
    )


@pytest.fixture
def arena_layer_results_platinum():
    """创建白金级Arena层级结果"""
    return {
        'layer1_investment_metrics': {
            'score': 0.95,
            'passed': True,
            'sharpe_ratio': 2.8,
            'max_drawdown': 0.08
        },
        'layer2_time_stability': {
            'score': 0.92,
            'passed': True,
            'rolling_sharpe_std': 0.12
        },
        'layer3_overfitting_prevention': {
            'score': 0.90,
            'passed': True,
            'is_oos_ratio': 0.92
        },
        'layer4_stress_test': {
            'score': 0.93,
            'passed': True,
            'crash_scenario_score': 0.90
        }
    }


@pytest.fixture
def simulation_result_passed():
    """创建通过的模拟盘结果"""
    tier_results = {
        CapitalTier.TIER_1: TierSimulationResult(
            tier=CapitalTier.TIER_1,
            initial_capital=5000.0,
            final_capital=5800.0,
            total_return=0.16,
            sharpe_ratio=2.5,
            max_drawdown=0.08,
            win_rate=0.65,
            profit_factor=1.8,
            var_95=0.03,
            calmar_ratio=2.0,
            information_ratio=1.2,
            daily_pnl=[],
            trades=[]
        ),
        CapitalTier.TIER_2: TierSimulationResult(
            tier=CapitalTier.TIER_2,
            initial_capital=30000.0,
            final_capital=35400.0,
            total_return=0.18,
            sharpe_ratio=2.8,
            max_drawdown=0.07,
            win_rate=0.68,
            profit_factor=2.0,
            var_95=0.025,
            calmar_ratio=2.5,
            information_ratio=1.5,
            daily_pnl=[],
            trades=[]
        )
    }
    
    return SimulationResult(
        passed=True,
        duration_days=30,
        tier_results=tier_results,
        best_tier=CapitalTier.TIER_2,
        overall_metrics={
            'avg_return': 0.17,
            'avg_sharpe': 2.65,
            'avg_drawdown': 0.075,
            # 添加认证评估器需要的键名
            'sharpe_ratio': 2.65,  # 平均夏普比率
            'max_drawdown': 0.075,  # 平均最大回撤
            'win_rate': 0.665  # 平均胜率
        },
        risk_metrics={
            'volatility': 0.15,
            'var_95': 0.028
        },
        market_environment_performance={
            'bull_market': {'return': 0.20, 'sharpe': 3.0},
            'bear_market': {'return': 0.05, 'sharpe': 1.5},
            'sideways_market': {'return': 0.12, 'sharpe': 2.2}
        },
        passed_criteria_count=10,
        failed_criteria=[]
    )


class TestZ2HCertificationIntegration:
    """Z2H认证系统集成测试"""
    
    @pytest.mark.asyncio
    async def test_evaluate_eligibility_with_platinum_level(
        self,
        z2h_certification,
        arena_layer_results_platinum,
        simulation_result_passed
    ):
        """测试白金级认证资格评估"""
        # 评估认证资格
        eligibility = await z2h_certification.evaluate_certification_eligibility(
            arena_overall_score=0.925,
            arena_layer_results=arena_layer_results_platinum,
            simulation_result=simulation_result_passed
        )
        
        # 验证结果
        assert eligibility.eligible is True
        assert eligibility.certification_level == CertificationLevel.PLATINUM
        assert eligibility.arena_score == 0.925
        assert len(eligibility.passed_criteria) > 0
        assert len(eligibility.failed_criteria) == 0

    
    @pytest.mark.asyncio
    async def test_complete_certification_workflow(
        self,
        z2h_certification,
        arena_layer_results_platinum,
        simulation_result_passed
    ):
        """测试完整的认证工作流程"""
        # 1. 评估资格
        eligibility = await z2h_certification.evaluate_certification_eligibility(
            arena_overall_score=0.925,
            arena_layer_results=arena_layer_results_platinum,
            simulation_result=simulation_result_passed
        )
        
        assert eligibility.eligible is True
        
        # 2. 确定认证等级
        level = await z2h_certification.determine_certification_level(
            arena_overall_score=0.925,
            arena_layer_results=arena_layer_results_platinum,
            simulation_result=simulation_result_passed
        )
        
        assert level == CertificationLevel.PLATINUM
        
        # 3. 确定资金配置规则
        capital_rules = await z2h_certification.determine_capital_allocation_rules(
            certification_level=level,
            simulation_result=simulation_result_passed
        )
        
        assert capital_rules.max_allocation_ratio == 0.20
        assert capital_rules.recommended_tier == CapitalTier.TIER_2
        
        # 4. 生成基因胶囊
        gene_capsule = await z2h_certification.generate_z2h_gene_capsule(
            strategy_id="test_strategy_001",
            strategy_name="测试策略",
            strategy_type="multi_factor",
            source_factors=["factor1", "factor2"],
            creation_date=datetime.now(),
            certification_level=level,
            arena_overall_score=0.925,
            arena_layer_results=arena_layer_results_platinum,
            simulation_result=simulation_result_passed,
            capital_rules=capital_rules
        )
        
        assert gene_capsule.strategy_id == "test_strategy_001"
        assert gene_capsule.certification_level == CertificationLevel.PLATINUM
        assert gene_capsule.arena_overall_score == 0.925
        
        # 5. 颁发认证
        certified_strategy = await z2h_certification.grant_certification(
            gene_capsule=gene_capsule
        )
        
        assert certified_strategy.strategy_id == "test_strategy_001"
        assert certified_strategy.status == CertificationStatus.CERTIFIED
        assert certified_strategy.certification_level == CertificationLevel.PLATINUM
    
    @pytest.mark.asyncio
    async def test_certification_status_management(
        self,
        z2h_certification,
        arena_layer_results_platinum,
        simulation_result_passed
    ):
        """测试认证状态管理"""
        # 创建并颁发认证
        level = CertificationLevel.PLATINUM
        capital_rules = await z2h_certification.determine_capital_allocation_rules(
            certification_level=level,
            simulation_result=simulation_result_passed
        )
        
        gene_capsule = await z2h_certification.generate_z2h_gene_capsule(
            strategy_id="test_strategy_002",
            strategy_name="测试策略2",
            strategy_type="multi_factor",
            source_factors=["factor1"],
            creation_date=datetime.now(),
            certification_level=level,
            arena_overall_score=0.925,
            arena_layer_results=arena_layer_results_platinum,
            simulation_result=simulation_result_passed,
            capital_rules=capital_rules
        )
        
        certified_strategy = await z2h_certification.grant_certification(
            gene_capsule=gene_capsule
        )
        
        # 验证初始状态
        assert certified_strategy.status == CertificationStatus.CERTIFIED
        
        # 测试降级
        success = await z2h_certification.downgrade_certification(
            strategy_id="test_strategy_002",
            new_level=CertificationLevel.GOLD,
            reason="性能下降"
        )
        
        assert success is True
        
        # 验证降级后状态
        strategy = z2h_certification.get_certified_strategy("test_strategy_002")
        assert strategy.status == CertificationStatus.DOWNGRADED
        assert strategy.certification_level == CertificationLevel.GOLD
        
        # 测试撤销
        success = await z2h_certification.revoke_certification(
            strategy_id="test_strategy_002",
            reason="严重违规"
        )
        
        assert success is True
        
        # 验证撤销后状态
        strategy = z2h_certification.get_certified_strategy("test_strategy_002")
        assert strategy.status == CertificationStatus.REVOKED

    
    @pytest.mark.asyncio
    async def test_multiple_strategies_certification(
        self,
        z2h_certification,
        arena_layer_results_platinum,
        simulation_result_passed
    ):
        """测试多个策略的认证管理"""
        # 创建3个不同等级的策略
        strategies_data = [
            ("strat_001", "策略1", CertificationLevel.PLATINUM, 0.925),
            ("strat_002", "策略2", CertificationLevel.GOLD, 0.85),
            ("strat_003", "策略3", CertificationLevel.SILVER, 0.78)
        ]
        
        for strategy_id, strategy_name, level, score in strategies_data:
            capital_rules = await z2h_certification.determine_capital_allocation_rules(
                certification_level=level,
                simulation_result=simulation_result_passed
            )
            
            gene_capsule = await z2h_certification.generate_z2h_gene_capsule(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                strategy_type="multi_factor",
                source_factors=["factor1"],
                creation_date=datetime.now(),
                certification_level=level,
                arena_overall_score=score,
                arena_layer_results=arena_layer_results_platinum,
                simulation_result=simulation_result_passed,
                capital_rules=capital_rules
            )
            
            await z2h_certification.grant_certification(gene_capsule=gene_capsule)
        
        # 验证所有策略都已认证
        all_strategies = z2h_certification.list_certified_strategies()
        assert len(all_strategies) >= 3
        
        # 按等级筛选
        platinum_strategies = z2h_certification.list_certified_strategies(
            certification_level=CertificationLevel.PLATINUM
        )
        assert len(platinum_strategies) >= 1
        
        gold_strategies = z2h_certification.list_certified_strategies(
            certification_level=CertificationLevel.GOLD
        )
        assert len(gold_strategies) >= 1
        
        silver_strategies = z2h_certification.list_certified_strategies(
            certification_level=CertificationLevel.SILVER
        )
        assert len(silver_strategies) >= 1
    
    @pytest.mark.asyncio
    async def test_gene_capsule_serialization_integration(
        self,
        z2h_certification,
        arena_layer_results_platinum,
        simulation_result_passed
    ):
        """测试基因胶囊序列化集成"""
        # 生成基因胶囊
        level = CertificationLevel.PLATINUM
        capital_rules = await z2h_certification.determine_capital_allocation_rules(
            certification_level=level,
            simulation_result=simulation_result_passed
        )
        
        gene_capsule = await z2h_certification.generate_z2h_gene_capsule(
            strategy_id="test_strategy_003",
            strategy_name="测试策略3",
            strategy_type="multi_factor",
            source_factors=["factor1", "factor2"],
            creation_date=datetime.now(),
            certification_level=level,
            arena_overall_score=0.925,
            arena_layer_results=arena_layer_results_platinum,
            simulation_result=simulation_result_passed,
            capital_rules=capital_rules
        )
        
        # 序列化
        gene_dict = gene_capsule.to_dict()
        
        # 验证序列化结果
        assert gene_dict['strategy_id'] == "test_strategy_003"
        assert gene_dict['certification_level'] == "platinum"
        assert gene_dict['arena_overall_score'] == 0.925
        
        # 反序列化
        restored_capsule = Z2HGeneCapsule.from_dict(gene_dict)
        
        # 验证反序列化结果
        assert restored_capsule.strategy_id == gene_capsule.strategy_id
        assert restored_capsule.certification_level == gene_capsule.certification_level
        assert restored_capsule.arena_overall_score == gene_capsule.arena_overall_score
