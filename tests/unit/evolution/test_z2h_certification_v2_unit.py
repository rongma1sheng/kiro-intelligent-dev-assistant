"""Z2H认证系统V2单元测试

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

测试Z2H认证系统V2的核心功能：
- 资格评估逻辑
- Arena结果集成
- 基因胶囊生成
- 认证颁发
- 认证撤销和降级

Requirements: 1.1-1.5, 4.6, 7.2, 7.3, 7.4
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.evolution.z2h_certification_v2 import Z2HCertificationV2
from src.evolution.z2h_data_models import (
    CertificationLevel,
    CertificationStatus,
    CapitalTier,
    Z2HGeneCapsule,
    CertificationEligibility,
    CapitalAllocationRules,
    SimulationResult,
    TierSimulationResult,
    CertifiedStrategy
)
from src.evolution.certification_level_evaluator import (
    CertificationLevelEvaluator,
    LevelEvaluationResult
)
from src.evolution.capital_allocation_rules_determiner import (
    CapitalAllocationRulesDeterminer
)


class TestZ2HCertificationV2Unit:
    """Z2H认证系统V2单元测试
    
    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
    """
    
    @pytest.fixture
    def certification_system(self):
        """创建认证系统实例"""
        return Z2HCertificationV2()
    
    @pytest.fixture
    def sample_arena_results(self):
        """创建示例Arena结果"""
        return {
            'layer1_reality': {
                'passed': True,
                'score': 0.96,  # PLATINUM要求layer_1 >= 0.95
                'metrics': {'ic': 0.08, 'ir': 1.5}
            },
            'layer2_hell': {
                'passed': True,
                'score': 0.88,  # PLATINUM要求layer_2 >= 0.85
                'metrics': {'stress_test_pass_rate': 0.85}
            },
            'layer3_cross_market': {
                'passed': True,
                'score': 0.90,  # PLATINUM要求layer_3 >= 0.80
                'metrics': {'adaptability': 0.90}
            },
            'layer4_stress': {
                'passed': True,
                'score': 0.91,  # PLATINUM要求layer_4 >= 0.85
                'metrics': {'resilience': 0.91}
            }
        }
    
    @pytest.fixture
    def sample_simulation_result(self):
        """创建示例模拟盘结果"""
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=5500,
                total_return=0.10,
                sharpe_ratio=2.6,  # PLATINUM要求 >= 2.5
                max_drawdown=0.08,  # PLATINUM要求 <= 0.10
                win_rate=0.68,  # PLATINUM要求 >= 0.65
                profit_factor=2.0,
                var_95=0.03,
                calmar_ratio=1.25,
                information_ratio=1.5,
                daily_pnl=[10, 20, -5, 15, 30],
                trades=[]
            )
        }
        
        return SimulationResult(
            passed=True,
            duration_days=30,
            tier_results=tier_results,
            best_tier=CapitalTier.TIER_1,
            overall_metrics={
                'sharpe_ratio': 2.6,  # PLATINUM要求 >= 2.5
                'max_drawdown': 0.08,  # PLATINUM要求 <= 0.10
                'win_rate': 0.68,  # PLATINUM要求 >= 0.65
                'avg_return': 0.10
            },
            risk_metrics={
                'var_95': 0.03,
                'volatility': 0.15
            },
            market_environment_performance={
                'bull_market': {'return': 0.12, 'sharpe': 2.5},
                'bear_market': {'return': 0.02, 'sharpe': 1.0},
                'sideways_market': {'return': 0.08, 'sharpe': 1.8}
            },
            passed_criteria_count=10,
            failed_criteria=[]
        )
    
    @pytest.fixture
    def sample_capital_rules(self):
        """创建示例资金配置规则"""
        return CapitalAllocationRules(
            max_allocation_ratio=0.20,
            min_capital=1000,
            max_capital=10000,
            optimal_capital=5000,
            recommended_tier=CapitalTier.TIER_1,
            position_limit_per_stock=0.10,
            sector_exposure_limit=0.30,
            max_leverage=2.0,
            liquidity_buffer=0.10
        )
    
    # ==================== 任务7.3.1: 资格评估逻辑 ====================
    
    @pytest.mark.asyncio
    async def test_eligibility_evaluation_all_pass(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result
    ):
        """测试所有条件都通过的资格评估
        
        Requirements: 1.1, 1.2
        """
        eligibility = await certification_system.evaluate_certification_eligibility(
            arena_overall_score=0.90,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result
        )
        
        # 验证符合条件
        assert eligibility.eligible is True
        assert eligibility.certification_level != CertificationLevel.NONE
        assert eligibility.arena_score == 0.90
        assert len(eligibility.passed_criteria) > 0
        assert len(eligibility.failed_criteria) == 0
    
    @pytest.mark.asyncio
    async def test_eligibility_evaluation_arena_fail(
        self,
        certification_system,
        sample_simulation_result
    ):
        """测试Arena未通过的资格评估
        
        Requirements: 1.3
        """
        # Arena结果不达标
        arena_results = {
            'layer1_reality': {'passed': False, 'score': 0.60},
            'layer2_hell': {'passed': True, 'score': 0.80},
            'layer3_cross_market': {'passed': True, 'score': 0.75},
            'layer4_stress': {'passed': True, 'score': 0.70}
        }
        
        eligibility = await certification_system.evaluate_certification_eligibility(
            arena_overall_score=0.70,
            arena_layer_results=arena_results,
            simulation_result=sample_simulation_result
        )
        
        # 验证不符合条件
        assert eligibility.eligible is False
        assert eligibility.certification_level == CertificationLevel.NONE
        assert len(eligibility.failed_criteria) > 0
    
    @pytest.mark.asyncio
    async def test_eligibility_evaluation_simulation_fail(
        self,
        certification_system,
        sample_arena_results
    ):
        """测试模拟盘未通过的资格评估
        
        Requirements: 1.4
        """
        # 模拟盘结果不达标
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=4500,
                total_return=-0.10,
                sharpe_ratio=0.5,
                max_drawdown=0.25,
                win_rate=0.40,
                profit_factor=0.8,
                var_95=0.10,
                calmar_ratio=-0.4,
                information_ratio=0.2,
                daily_pnl=[-10, -20, 5, -15, -30],
                trades=[]
            )
        }
        
        simulation_result = SimulationResult(
            passed=False,
            duration_days=30,
            tier_results=tier_results,
            best_tier=CapitalTier.TIER_1,
            overall_metrics={'sharpe_ratio': 0.5, 'max_drawdown': 0.25, 'win_rate': 0.40},
            risk_metrics={'var_95': 0.10, 'volatility': 0.30},
            market_environment_performance={},
            passed_criteria_count=3,
            failed_criteria=['月收益不达标', '夏普比率不达标', '最大回撤过大']
        )
        
        eligibility = await certification_system.evaluate_certification_eligibility(
            arena_overall_score=0.90,
            arena_layer_results=sample_arena_results,
            simulation_result=simulation_result
        )
        
        # 验证不符合条件
        assert eligibility.eligible is False
        assert eligibility.certification_level == CertificationLevel.NONE
        assert len(eligibility.failed_criteria) > 0
        assert len(eligibility.failure_reasons) > 0
    
    @pytest.mark.asyncio
    async def test_eligibility_evaluation_invalid_inputs(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result
    ):
        """测试无效输入的错误处理
        
        Requirements: 1.5
        """
        # Arena评分超出范围
        with pytest.raises(ValueError, match="Arena综合评分必须在"):
            await certification_system.evaluate_certification_eligibility(
                arena_overall_score=1.5,
                arena_layer_results=sample_arena_results,
                simulation_result=sample_simulation_result
            )
        
        # Arena结果为空
        with pytest.raises(ValueError, match="Arena层级结果不能为空"):
            await certification_system.evaluate_certification_eligibility(
                arena_overall_score=0.90,
                arena_layer_results={},
                simulation_result=sample_simulation_result
            )
        
        # 模拟盘结果为空
        with pytest.raises(ValueError, match="模拟盘结果不能为空"):
            await certification_system.evaluate_certification_eligibility(
                arena_overall_score=0.90,
                arena_layer_results=sample_arena_results,
                simulation_result=None
            )
    
    # ==================== 任务7.3.2: Arena结果集成 ====================
    
    @pytest.mark.asyncio
    async def test_arena_result_integration_platinum(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result
    ):
        """测试PLATINUM等级的Arena结果集成
        
        Requirements: 4.6
        """
        level = await certification_system.determine_certification_level(
            arena_overall_score=0.92,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result
        )
        
        assert level == CertificationLevel.PLATINUM
    
    @pytest.mark.asyncio
    async def test_arena_result_integration_gold(
        self,
        certification_system,
        sample_simulation_result
    ):
        """测试GOLD等级的Arena结果集成
        
        Requirements: 4.6
        """
        # GOLD级别Arena结果
        arena_results = {
            'layer1_reality': {'passed': True, 'score': 0.85},
            'layer2_hell': {'passed': True, 'score': 0.82},
            'layer3_cross_market': {'passed': True, 'score': 0.83},
            'layer4_stress': {'passed': True, 'score': 0.84}
        }
        
        level = await certification_system.determine_certification_level(
            arena_overall_score=0.84,
            arena_layer_results=arena_results,
            simulation_result=sample_simulation_result
        )
        
        assert level == CertificationLevel.GOLD
    
    @pytest.mark.asyncio
    async def test_arena_result_integration_silver(
        self,
        certification_system,
        sample_simulation_result
    ):
        """测试SILVER等级的Arena结果集成
        
        Requirements: 4.6
        """
        # SILVER级别Arena结果 - 需要满足SILVER层级阈值
        # SILVER阈值: layer_1 >= 0.80, layer_2 >= 0.70, layer_3 >= 0.60, layer_4 >= 0.70
        arena_results = {
            'layer1_reality': {'passed': True, 'score': 0.82},  # SILVER要求 >= 0.80
            'layer2_hell': {'passed': True, 'score': 0.76},     # SILVER要求 >= 0.70
            'layer3_cross_market': {'passed': True, 'score': 0.77},  # SILVER要求 >= 0.60
            'layer4_stress': {'passed': True, 'score': 0.75}    # SILVER要求 >= 0.70
        }
        
        # 创建SILVER级别的模拟盘结果
        # SILVER阈值: min_sharpe >= 1.5, max_drawdown <= 0.15, min_win_rate >= 0.55
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=5300,
                total_return=0.06,
                sharpe_ratio=1.6,  # SILVER要求 >= 1.5
                max_drawdown=0.12,  # SILVER要求 <= 0.15
                win_rate=0.58,  # SILVER要求 >= 0.55
                profit_factor=1.5,
                var_95=0.04,
                calmar_ratio=0.8,
                information_ratio=1.0,
                daily_pnl=[5, 10, -3, 8, 15],
                trades=[]
            )
        }
        
        silver_simulation_result = SimulationResult(
            passed=True,
            duration_days=30,
            tier_results=tier_results,
            best_tier=CapitalTier.TIER_1,
            overall_metrics={
                'sharpe_ratio': 1.6,  # SILVER要求 >= 1.5
                'max_drawdown': 0.12,  # SILVER要求 <= 0.15
                'win_rate': 0.58,  # SILVER要求 >= 0.55
                'avg_return': 0.06
            },
            risk_metrics={
                'var_95': 0.04,
                'volatility': 0.18
            },
            market_environment_performance={
                'bull_market': {'return': 0.08, 'sharpe': 1.8},
                'bear_market': {'return': 0.01, 'sharpe': 0.8},
                'sideways_market': {'return': 0.05, 'sharpe': 1.2}
            },
            passed_criteria_count=8,
            failed_criteria=[]
        )
        
        level = await certification_system.determine_certification_level(
            arena_overall_score=0.77,
            arena_layer_results=arena_results,
            simulation_result=silver_simulation_result
        )
        
        assert level == CertificationLevel.SILVER
    
    # ==================== 任务7.3.3: 基因胶囊生成 ====================
    
    @pytest.mark.asyncio
    async def test_gene_capsule_generation_complete(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试完整的基因胶囊生成
        
        Requirements: 3.1-3.8
        """
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_001",
            strategy_name="测试策略",
            strategy_type="momentum",
            source_factors=["factor1", "factor2"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.PLATINUM,
            arena_overall_score=0.92,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        
        # 验证基本信息
        assert gene_capsule.strategy_id == "test_strategy_001"
        assert gene_capsule.strategy_name == "测试策略"
        assert gene_capsule.certification_level == CertificationLevel.PLATINUM
        
        # 验证Arena结果
        assert gene_capsule.arena_overall_score == 0.92
        assert gene_capsule.arena_passed_layers == 4
        assert len(gene_capsule.arena_failed_layers) == 0
        
        # 验证模拟盘结果
        assert gene_capsule.simulation_duration_days == 30
        assert gene_capsule.simulation_best_tier == CapitalTier.TIER_1
        
        # 验证资金配置规则
        assert gene_capsule.max_allocation_ratio == 0.20
        assert 'min' in gene_capsule.recommended_capital_scale
        assert 'max' in gene_capsule.recommended_capital_scale
        assert 'optimal' in gene_capsule.recommended_capital_scale
    
    @pytest.mark.asyncio
    async def test_gene_capsule_generation_with_failed_layers(
        self,
        certification_system,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试包含失败层级的基因胶囊生成
        
        Requirements: 3.8
        """
        # Arena结果包含失败层级
        arena_results = {
            'layer1_reality': {'passed': True, 'score': 0.85},
            'layer2_hell': {'passed': False, 'score': 0.65},
            'layer3_cross_market': {'passed': True, 'score': 0.80},
            'layer4_stress': {'passed': True, 'score': 0.78}
        }
        
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_002",
            strategy_name="测试策略2",
            strategy_type="mean_reversion",
            source_factors=["factor3"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.SILVER,
            arena_overall_score=0.77,
            arena_layer_results=arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        
        # 验证失败层级被记录
        assert gene_capsule.arena_passed_layers == 3
        assert len(gene_capsule.arena_failed_layers) == 1
        assert 'layer2_hell' in gene_capsule.arena_failed_layers
    
    # ==================== 任务7.3.4: 认证颁发 ====================
    
    @pytest.mark.asyncio
    async def test_certification_grant_success(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试成功颁发认证
        
        Requirements: 7.2
        """
        # 生成基因胶囊
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_003",
            strategy_name="测试策略3",
            strategy_type="arbitrage",
            source_factors=["factor4", "factor5"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        
        # 颁发认证
        certified_strategy = await certification_system.grant_certification(gene_capsule)
        
        # 验证认证策略
        assert certified_strategy.strategy_id == "test_strategy_003"
        assert certified_strategy.certification_level == CertificationLevel.GOLD
        assert certified_strategy.status == CertificationStatus.CERTIFIED
        assert certified_strategy.next_review_date is not None
        
        # 验证已保存到系统
        saved_strategy = certification_system.get_certified_strategy("test_strategy_003")
        assert saved_strategy is not None
        assert saved_strategy.strategy_id == "test_strategy_003"
    
    @pytest.mark.asyncio
    async def test_certification_grant_sets_review_date(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试认证颁发设置复核日期
        
        Requirements: 7.2
        """
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_004",
            strategy_name="测试策略4",
            strategy_type="momentum",
            source_factors=["factor6"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.PLATINUM,
            arena_overall_score=0.92,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        
        certified_strategy = await certification_system.grant_certification(gene_capsule)
        
        # 验证复核日期（应该是30天后）
        assert certified_strategy.next_review_date is not None
        expected_review_date = gene_capsule.certification_date + timedelta(days=30)
        assert certified_strategy.next_review_date.date() == expected_review_date.date()
    
    # ==================== 任务7.3.5: 认证撤销 ====================
    
    @pytest.mark.asyncio
    async def test_certification_revoke_success(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试成功撤销认证
        
        Requirements: 7.3
        """
        # 先颁发认证
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_005",
            strategy_name="测试策略5",
            strategy_type="momentum",
            source_factors=["factor7"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        await certification_system.grant_certification(gene_capsule)
        
        # 撤销认证
        success = await certification_system.revoke_certification(
            strategy_id="test_strategy_005",
            reason="实盘表现不达标"
        )
        
        # 验证撤销成功
        assert success is True
        
        # 验证状态更新
        strategy = certification_system.get_certified_strategy("test_strategy_005")
        assert strategy.status == CertificationStatus.REVOKED
        assert strategy.last_review_date is not None
    
    @pytest.mark.asyncio
    async def test_certification_revoke_nonexistent(
        self,
        certification_system
    ):
        """测试撤销不存在的认证
        
        Requirements: 7.3
        """
        success = await certification_system.revoke_certification(
            strategy_id="nonexistent_strategy",
            reason="测试"
        )
        
        # 验证撤销失败
        assert success is False
    
    # ==================== 任务7.3.6: 认证降级 ====================
    
    @pytest.mark.asyncio
    async def test_certification_downgrade_success(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试成功降级认证
        
        Requirements: 7.4
        """
        # 先颁发PLATINUM认证
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_006",
            strategy_name="测试策略6",
            strategy_type="momentum",
            source_factors=["factor8"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.PLATINUM,
            arena_overall_score=0.92,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        await certification_system.grant_certification(gene_capsule)
        
        # 降级到GOLD
        success = await certification_system.downgrade_certification(
            strategy_id="test_strategy_006",
            new_level=CertificationLevel.GOLD,
            reason="近期表现下降"
        )
        
        # 验证降级成功
        assert success is True
        
        # 验证等级更新
        strategy = certification_system.get_certified_strategy("test_strategy_006")
        assert strategy.certification_level == CertificationLevel.GOLD
        assert strategy.status == CertificationStatus.DOWNGRADED
        assert strategy.last_review_date is not None
    
    @pytest.mark.asyncio
    async def test_certification_downgrade_invalid(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试无效的降级操作
        
        Requirements: 7.4
        """
        # 先颁发GOLD认证
        gene_capsule = await certification_system.generate_z2h_gene_capsule(
            strategy_id="test_strategy_007",
            strategy_name="测试策略7",
            strategy_type="momentum",
            source_factors=["factor9"],
            creation_date=datetime(2026, 1, 1),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results=sample_arena_results,
            simulation_result=sample_simulation_result,
            capital_rules=sample_capital_rules
        )
        await certification_system.grant_certification(gene_capsule)
        
        # 尝试"降级"到PLATINUM（实际是升级）
        success = await certification_system.downgrade_certification(
            strategy_id="test_strategy_007",
            new_level=CertificationLevel.PLATINUM,
            reason="测试"
        )
        
        # 验证降级失败
        assert success is False
        
        # 验证等级未变
        strategy = certification_system.get_certified_strategy("test_strategy_007")
        assert strategy.certification_level == CertificationLevel.GOLD
    
    @pytest.mark.asyncio
    async def test_certification_downgrade_nonexistent(
        self,
        certification_system
    ):
        """测试降级不存在的认证
        
        Requirements: 7.4
        """
        success = await certification_system.downgrade_certification(
            strategy_id="nonexistent_strategy",
            new_level=CertificationLevel.SILVER,
            reason="测试"
        )
        
        # 验证降级失败
        assert success is False
    
    # ==================== 任务7.3.7: 策略查询 ====================
    
    @pytest.mark.asyncio
    async def test_list_certified_strategies_all(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试列出所有已认证策略
        
        Requirements: 7.2
        """
        # 颁发多个认证
        for i in range(3):
            gene_capsule = await certification_system.generate_z2h_gene_capsule(
                strategy_id=f"test_strategy_{i}",
                strategy_name=f"测试策略{i}",
                strategy_type="momentum",
                source_factors=[f"factor{i}"],
                creation_date=datetime(2026, 1, 1),
                certification_level=CertificationLevel.GOLD,
                arena_overall_score=0.85,
                arena_layer_results=sample_arena_results,
                simulation_result=sample_simulation_result,
                capital_rules=sample_capital_rules
            )
            await certification_system.grant_certification(gene_capsule)
        
        # 列出所有策略
        strategies = certification_system.list_certified_strategies()
        
        # 验证数量
        assert len(strategies) == 3
    
    @pytest.mark.asyncio
    async def test_list_certified_strategies_by_level(
        self,
        certification_system,
        sample_arena_results,
        sample_simulation_result,
        sample_capital_rules
    ):
        """测试按等级筛选已认证策略
        
        Requirements: 7.2
        """
        # 颁发不同等级的认证
        levels = [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER]
        for i, level in enumerate(levels):
            gene_capsule = await certification_system.generate_z2h_gene_capsule(
                strategy_id=f"test_strategy_level_{i}",
                strategy_name=f"测试策略{i}",
                strategy_type="momentum",
                source_factors=[f"factor{i}"],
                creation_date=datetime(2026, 1, 1),
                certification_level=level,
                arena_overall_score=0.85,
                arena_layer_results=sample_arena_results,
                simulation_result=sample_simulation_result,
                capital_rules=sample_capital_rules
            )
            await certification_system.grant_certification(gene_capsule)
        
        # 筛选GOLD等级
        gold_strategies = certification_system.list_certified_strategies(
            certification_level=CertificationLevel.GOLD
        )
        
        # 验证筛选结果
        assert len(gold_strategies) == 1
        assert gold_strategies[0].certification_level == CertificationLevel.GOLD
