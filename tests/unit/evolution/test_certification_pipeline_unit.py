"""认证流程编排器单元测试

白皮书依据: 第四章 4.2-4.3 完整验证流程

测试Z2H认证流程编排器的核心功能：
- 完整6阶段流程
- 各阶段失败场景
- 阶段间数据传递
- 错误处理

Requirements: 2.1-2.8
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.evolution.z2h_certification_pipeline import (
    Z2HCertificationPipeline,
    Factor,
    Strategy,
    FactorArenaResult,
    CandidateStrategy,
    ArenaTestResult,
    CertificationError
)
from src.evolution.z2h_certification_v2 import Z2HCertificationV2
from src.evolution.multi_tier_simulation_manager import SimulationManager
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


class TestCertificationPipelineUnit:
    """认证流程编排器单元测试
    
    白皮书依据: 第四章 4.2-4.3 完整验证流程
    """
    
    @pytest.fixture
    def mock_z2h_certification(self):
        """创建模拟Z2H认证系统"""
        return AsyncMock(spec=Z2HCertificationV2)
    
    @pytest.fixture
    def mock_simulation_manager(self):
        """创建模拟模拟盘管理器"""
        return AsyncMock(spec=SimulationManager)
    
    @pytest.fixture
    def pipeline(self, mock_z2h_certification, mock_simulation_manager):
        """创建认证流程编排器实例"""
        return Z2HCertificationPipeline(
            z2h_certification=mock_z2h_certification,
            simulation_manager=mock_simulation_manager
        )
    
    @pytest.fixture
    def sample_factor(self):
        """创建示例因子"""
        return Factor(
            factor_id="factor_001",
            factor_name="动量因子",
            factor_expression="close / delay(close, 20) - 1",
            creation_date=datetime(2026, 1, 1)
        )
    
    @pytest.fixture
    def sample_strategy(self):
        """创建示例策略"""
        return Strategy(
            strategy_id="strategy_001",
            strategy_name="多因子策略",
            strategy_type="multi_factor",
            strategy_code="# 策略代码",
            source_factors=["factor1", "factor2"],
            creation_date=datetime(2026, 1, 1)
        )
    
    @pytest.fixture
    def sample_simulation_result(self):
        """创建示例模拟盘结果"""
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=5500,
                total_return=0.10,
                sharpe_ratio=2.0,
                max_drawdown=0.08,
                win_rate=0.65,
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
                'sharpe_ratio': 2.0,
                'max_drawdown': 0.08,
                'win_rate': 0.65
            },
            risk_metrics={'var_95': 0.03, 'volatility': 0.15},
            market_environment_performance={
                'bull_market': {'return': 0.12, 'sharpe': 2.5},
                'bear_market': {'return': 0.02, 'sharpe': 1.0},
                'sideways_market': {'return': 0.08, 'sharpe': 1.8}
            },
            passed_criteria_count=10,
            failed_criteria=[]
        )
    
    # ==================== 任务8.3.1: 完整6阶段流程 ====================
    
    @pytest.mark.asyncio
    async def test_complete_6_stage_flow_with_strategy_input(
        self,
        pipeline,
        sample_strategy,
        mock_z2h_certification,
        mock_simulation_manager,
        sample_simulation_result
    ):
        """测试策略输入的完整6阶段流程
        
        Requirements: 2.1-2.8
        """
        # 配置mock返回值
        
        # 阶段3: Arena测试
        arena_result = ArenaTestResult(
            passed=True,
            overall_score=0.90,
            layer_results={
                'layer1': {'score': 0.92, 'passed': True},
                'layer2': {'score': 0.88, 'passed': True},
                'layer3': {'score': 0.90, 'passed': True},
                'layer4': {'score': 0.90, 'passed': True}
            },
            test_date=datetime.now()
        )
        
        # 阶段4: 模拟盘
        mock_simulation_manager.start_simulation.return_value = MagicMock(
            instance_id="sim_001",
            strategy_id=sample_strategy.strategy_id
        )
        mock_simulation_manager.run_multi_tier_simulation.return_value = {
            CapitalTier.TIER_1: sample_simulation_result.tier_results[CapitalTier.TIER_1]
        }
        mock_simulation_manager.monitor_simulation_risk.return_value = {
            'risk_alerts': []
        }
        mock_simulation_manager.evaluate_simulation_result.return_value = sample_simulation_result
        
        # 阶段5: Z2H认证
        eligibility = CertificationEligibility(
            eligible=True,
            certification_level=CertificationLevel.PLATINUM,
            arena_score=0.90,
            simulation_score=1.0,
            passed_criteria=[],
            failed_criteria=[],
            failure_reasons=[]
        )
        mock_z2h_certification.evaluate_certification_eligibility.return_value = eligibility
        mock_z2h_certification.determine_certification_level.return_value = CertificationLevel.PLATINUM
        
        capital_rules = CapitalAllocationRules(
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
        mock_z2h_certification.determine_capital_allocation_rules.return_value = capital_rules
        
        gene_capsule = Z2HGeneCapsule(
            strategy_id=sample_strategy.strategy_id,
            strategy_name=sample_strategy.strategy_name,
            strategy_type=sample_strategy.strategy_type,
            source_factors=sample_strategy.source_factors,
            creation_date=sample_strategy.creation_date,
            certification_date=datetime.now(),
            certification_level=CertificationLevel.PLATINUM,
            arena_overall_score=0.90,
            arena_layer_results={},
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={},
            simulation_best_tier=CapitalTier.TIER_1,
            simulation_metrics={},
            max_allocation_ratio=0.20,
            recommended_capital_scale={'min': 1000, 'max': 10000, 'optimal': 5000},
            optimal_trade_size=500,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=2.0,
            avg_position_count=10,
            sector_distribution={},
            market_cap_preference='mid_cap',
            var_95=0.03,
            expected_shortfall=0.04,
            max_drawdown=0.08,
            drawdown_duration_days=30,
            volatility=0.15,
            beta=1.0,
            market_correlation=0.5,
            bull_market_performance={},
            bear_market_performance={},
            sideways_market_performance={},
            high_volatility_performance={},
            low_volatility_performance={},
            market_adaptability_score=0.8,
            optimal_deployment_timing=[],
            risk_management_rules={},
            monitoring_indicators=[],
            exit_conditions=[],
            portfolio_strategy_suggestions=[]
        )
        mock_z2h_certification.generate_z2h_gene_capsule.return_value = gene_capsule
        
        # 阶段6: 策略库集成
        certified_strategy = CertifiedStrategy(
            strategy_id=sample_strategy.strategy_id,
            strategy_name=sample_strategy.strategy_name,
            certification_level=CertificationLevel.PLATINUM,
            gene_capsule=gene_capsule,
            certification_date=datetime.now(),
            status=CertificationStatus.CERTIFIED,
            last_review_date=None,
            next_review_date=datetime.now()
        )
        mock_z2h_certification.grant_certification.return_value = certified_strategy
        
        # 运行完整流程
        result = await pipeline.run_complete_certification(sample_strategy)
        
        # 验证结果
        assert result.passed is True
        assert result.strategy_id == sample_strategy.strategy_id
        assert result.certification_level == CertificationLevel.PLATINUM
        assert result.gene_capsule is not None
        assert result.failed_stage is None
        assert result.failure_reason is None
    
    @pytest.mark.asyncio
    async def test_complete_6_stage_flow_with_factor_input(
        self,
        pipeline,
        sample_factor,
        sample_simulation_result
    ):
        """测试因子输入的完整6阶段流程
        
        Requirements: 2.1, 2.2
        """
        # Mock阶段1成功
        with patch.object(
            pipeline,
            '_stage1_factor_arena_test',
            return_value=FactorArenaResult(
                passed=True,
                reality_track_score=0.85,
                hell_track_score=0.80,
                cross_market_score=0.82,
                overall_score=0.82,
                validated_factors=[sample_factor]
            )
        ):
            # Mock阶段2成功
            with patch.object(
                pipeline,
                '_stage2_strategy_generation',
                return_value=[CandidateStrategy(
                    strategy=Strategy(
                        strategy_id="strategy_001",
                        strategy_name="测试策略",
                        strategy_type="multi_factor",
                        strategy_code="# code",
                        source_factors=["factor_001"],
                        creation_date=datetime.now()
                    ),
                    factor_combination=["factor_001"],
                    expected_performance={"sharpe": 2.0, "return": 0.15}
                )]
            ):
                # Mock阶段3成功
                with patch.object(
                    pipeline,
                    '_stage3_sparta_arena_evaluation',
                    return_value=ArenaTestResult(
                        passed=True,
                        overall_score=0.85,
                        layer_results={
                            'layer1': {'score': 0.85, 'passed': True},
                            'layer2': {'score': 0.80, 'passed': True},
                            'layer3': {'score': 0.82, 'passed': True},
                            'layer4': {'score': 0.88, 'passed': True}
                        },
                        test_date=datetime.now()
                    )
                ):
                    # Mock阶段4成功
                    with patch.object(
                        pipeline,
                        '_stage4_simulation_validation',
                        return_value=sample_simulation_result
                    ):
                        # Mock阶段5成功
                        with patch.object(
                            pipeline,
                            '_stage5_z2h_certification',
                            return_value=MagicMock()
                        ):
                            # Mock阶段6成功
                            with patch.object(
                                pipeline,
                                '_stage6_strategy_library_integration',
                                return_value=MagicMock()
                            ):
                                # 运行流程
                                result = await pipeline.run_complete_certification(sample_factor)
                                
                                # 验证流程完成
                                assert result is not None
    
    # ==================== 任务8.3.2: 各阶段失败场景 ====================
    
    @pytest.mark.asyncio
    async def test_stage1_factor_arena_failure(
        self,
        pipeline,
        sample_factor
    ):
        """测试阶段1因子Arena失败
        
        Requirements: 2.7
        """
        # Mock阶段1失败
        with patch.object(
            pipeline,
            '_stage1_factor_arena_test',
            return_value=FactorArenaResult(
                passed=False,
                reality_track_score=0.60,
                hell_track_score=0.50,
                cross_market_score=0.55,
                overall_score=0.55,
                validated_factors=[]
            )
        ):
            result = await pipeline.run_complete_certification(sample_factor)
            
            # 验证失败
            assert result.passed is False
            assert result.failed_stage == "stage1_factor_arena"
            assert "因子Arena测试未通过" in result.failure_reason
    
    @pytest.mark.asyncio
    async def test_stage2_strategy_generation_failure(
        self,
        pipeline,
        sample_factor
    ):
        """测试阶段2策略生成失败
        
        Requirements: 2.7
        """
        # Mock阶段1成功
        with patch.object(
            pipeline,
            '_stage1_factor_arena_test',
            return_value=FactorArenaResult(
                passed=True,
                reality_track_score=0.85,
                hell_track_score=0.80,
                cross_market_score=0.82,
                overall_score=0.82,
                validated_factors=[sample_factor]
            )
        ):
            # Mock阶段2失败
            with patch.object(
                pipeline,
                '_stage2_strategy_generation',
                return_value=[]  # 未生成候选策略
            ):
                result = await pipeline.run_complete_certification(sample_factor)
                
                # 验证失败
                assert result.passed is False
                assert result.failed_stage == "stage2_strategy_generation"
                assert "未生成候选策略" in result.failure_reason
    
    @pytest.mark.asyncio
    async def test_stage3_sparta_arena_failure(
        self,
        pipeline,
        sample_strategy
    ):
        """测试阶段3斯巴达Arena失败
        
        Requirements: 2.7
        """
        # Mock阶段3失败
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            return_value=ArenaTestResult(
                passed=False,
                overall_score=0.65,
                layer_results={
                    'layer1': {'score': 0.70, 'passed': True},
                    'layer2': {'score': 0.60, 'passed': False},
                    'layer3': {'score': 0.65, 'passed': True},
                    'layer4': {'score': 0.65, 'passed': True}
                },
                test_date=datetime.now()
            )
        ):
            result = await pipeline.run_complete_certification(sample_strategy)
            
            # 验证失败
            assert result.passed is False
            assert result.failed_stage == "stage3_sparta_arena"
            assert "斯巴达Arena考核未通过" in result.failure_reason
    
    @pytest.mark.asyncio
    async def test_stage4_simulation_failure(
        self,
        pipeline,
        sample_strategy,
        mock_simulation_manager
    ):
        """测试阶段4模拟盘失败
        
        Requirements: 2.7
        """
        # Mock阶段3成功
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            return_value=ArenaTestResult(
                passed=True,
                overall_score=0.90,
                layer_results={
                    'layer1': {'score': 0.90, 'passed': True},
                    'layer2': {'score': 0.90, 'passed': True},
                    'layer3': {'score': 0.90, 'passed': True},
                    'layer4': {'score': 0.90, 'passed': True}
                },
                test_date=datetime.now()
            )
        ):
            # Mock阶段4失败
            failed_simulation_result = SimulationResult(
                passed=False,
                duration_days=30,
                tier_results={},
                best_tier=CapitalTier.TIER_1,
                overall_metrics={},
                risk_metrics={},
                market_environment_performance={},
                passed_criteria_count=5,
                failed_criteria=['月收益不达标', '夏普比率不达标', '最大回撤过大']
            )
            
            mock_simulation_manager.start_simulation.return_value = MagicMock(
                instance_id="sim_001"
            )
            mock_simulation_manager.run_multi_tier_simulation.return_value = {}
            mock_simulation_manager.monitor_simulation_risk.return_value = {'risk_alerts': []}
            mock_simulation_manager.evaluate_simulation_result.return_value = failed_simulation_result
            
            result = await pipeline.run_complete_certification(sample_strategy)
            
            # 验证失败
            assert result.passed is False
            assert result.failed_stage == "stage4_simulation"
            assert "模拟盘验证未通过" in result.failure_reason
    
    @pytest.mark.asyncio
    async def test_stage6_strategy_library_failure(
        self,
        pipeline,
        sample_strategy,
        mock_z2h_certification,
        mock_simulation_manager,
        sample_simulation_result
    ):
        """测试阶段6策略库集成失败
        
        Requirements: 2.7
        """
        # Mock阶段3-5成功
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            return_value=ArenaTestResult(
                passed=True,
                overall_score=0.90,
                layer_results={},
                test_date=datetime.now()
            )
        ):
            mock_simulation_manager.start_simulation.return_value = MagicMock(
                instance_id="sim_001"
            )
            mock_simulation_manager.run_multi_tier_simulation.return_value = {}
            mock_simulation_manager.monitor_simulation_risk.return_value = {'risk_alerts': []}
            mock_simulation_manager.evaluate_simulation_result.return_value = sample_simulation_result
            
            # Mock阶段5成功
            eligibility = CertificationEligibility(
                eligible=True,
                certification_level=CertificationLevel.PLATINUM,
                arena_score=0.90,
                simulation_score=1.0,
                passed_criteria=[],
                failed_criteria=[],
                failure_reasons=[]
            )
            mock_z2h_certification.evaluate_certification_eligibility.return_value = eligibility
            mock_z2h_certification.determine_certification_level.return_value = CertificationLevel.PLATINUM
            mock_z2h_certification.determine_capital_allocation_rules.return_value = MagicMock()
            mock_z2h_certification.generate_z2h_gene_capsule.return_value = MagicMock(
                strategy_id=sample_strategy.strategy_id,
                certification_level=CertificationLevel.PLATINUM
            )
            
            # Mock阶段6失败
            mock_z2h_certification.grant_certification.return_value = None
            
            result = await pipeline.run_complete_certification(sample_strategy)
            
            # 验证失败
            assert result.passed is False
            assert result.failed_stage == "stage6_strategy_library"
            assert "策略库集成失败" in result.failure_reason
    
    # ==================== 任务8.3.3: 阶段间数据传递 ====================
    
    @pytest.mark.asyncio
    async def test_data_transfer_between_stages(
        self,
        pipeline,
        sample_strategy,
        mock_z2h_certification,
        mock_simulation_manager,
        sample_simulation_result
    ):
        """测试阶段间数据正确传递
        
        Requirements: 2.8
        """
        # 配置完整的mock链
        arena_result = ArenaTestResult(
            passed=True,
            overall_score=0.90,
            layer_results={'layer1': {'score': 0.90, 'passed': True}},
            test_date=datetime.now()
        )
        
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            return_value=arena_result
        ) as mock_stage3:
            mock_simulation_manager.start_simulation.return_value = MagicMock(
                instance_id="sim_001"
            )
            mock_simulation_manager.run_multi_tier_simulation.return_value = {}
            mock_simulation_manager.monitor_simulation_risk.return_value = {'risk_alerts': []}
            mock_simulation_manager.evaluate_simulation_result.return_value = sample_simulation_result
            
            eligibility = CertificationEligibility(
                eligible=True,
                certification_level=CertificationLevel.PLATINUM,
                arena_score=0.90,
                simulation_score=1.0,
                passed_criteria=[],
                failed_criteria=[],
                failure_reasons=[]
            )
            mock_z2h_certification.evaluate_certification_eligibility.return_value = eligibility
            mock_z2h_certification.determine_certification_level.return_value = CertificationLevel.PLATINUM
            mock_z2h_certification.determine_capital_allocation_rules.return_value = MagicMock()
            
            gene_capsule = MagicMock(
                strategy_id=sample_strategy.strategy_id,
                certification_level=CertificationLevel.PLATINUM
            )
            mock_z2h_certification.generate_z2h_gene_capsule.return_value = gene_capsule
            mock_z2h_certification.grant_certification.return_value = MagicMock()
            
            # 运行流程
            result = await pipeline.run_complete_certification(sample_strategy)
            
            # 验证数据传递
            # 阶段3接收策略
            mock_stage3.assert_called_once()
            assert mock_stage3.call_args[0][0].strategy_id == sample_strategy.strategy_id
            
            # 阶段5接收Arena和模拟盘结果
            mock_z2h_certification.evaluate_certification_eligibility.assert_called_once()
            call_args = mock_z2h_certification.evaluate_certification_eligibility.call_args
            assert call_args[1]['arena_overall_score'] == 0.90
            assert call_args[1]['simulation_result'] == sample_simulation_result
    
    # ==================== 任务8.3.4: 错误处理 ====================
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_input(
        self,
        pipeline
    ):
        """测试无效输入的错误处理
        
        Requirements: 2.8
        """
        # 空输入
        with pytest.raises(ValueError, match="输入实体不能为空"):
            await pipeline.run_complete_certification(None)
        
        # 不支持的类型
        with pytest.raises(ValueError, match="不支持的输入类型"):
            await pipeline.run_complete_certification("invalid_type")
    
    @pytest.mark.asyncio
    async def test_error_handling_exception_in_stage(
        self,
        pipeline,
        sample_strategy
    ):
        """测试阶段执行异常的错误处理
        
        Requirements: 2.8
        """
        # Mock阶段3抛出异常
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            side_effect=Exception("Arena系统故障")
        ):
            with pytest.raises(CertificationError, match="认证流程异常"):
                await pipeline.run_complete_certification(sample_strategy)
    
    @pytest.mark.asyncio
    async def test_error_handling_simulation_exception(
        self,
        pipeline,
        sample_strategy,
        mock_simulation_manager
    ):
        """测试模拟盘异常的错误处理
        
        Requirements: 2.8
        """
        # Mock阶段3成功
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            return_value=ArenaTestResult(
                passed=True,
                overall_score=0.90,
                layer_results={},
                test_date=datetime.now()
            )
        ):
            # Mock模拟盘启动失败
            mock_simulation_manager.start_simulation.side_effect = Exception("模拟盘系统故障")
            
            with pytest.raises(CertificationError, match="认证流程异常"):
                await pipeline.run_complete_certification(sample_strategy)
    
    @pytest.mark.asyncio
    async def test_error_handling_certification_exception(
        self,
        pipeline,
        sample_strategy,
        mock_z2h_certification,
        mock_simulation_manager,
        sample_simulation_result
    ):
        """测试认证阶段异常的错误处理
        
        Requirements: 2.8
        """
        # Mock阶段3-4成功
        with patch.object(
            pipeline,
            '_stage3_sparta_arena_evaluation',
            return_value=ArenaTestResult(
                passed=True,
                overall_score=0.90,
                layer_results={},
                test_date=datetime.now()
            )
        ):
            mock_simulation_manager.start_simulation.return_value = MagicMock()
            mock_simulation_manager.run_multi_tier_simulation.return_value = {}
            mock_simulation_manager.monitor_simulation_risk.return_value = {'risk_alerts': []}
            mock_simulation_manager.evaluate_simulation_result.return_value = sample_simulation_result
            
            # Mock认证资格评估失败
            mock_z2h_certification.evaluate_certification_eligibility.side_effect = Exception(
                "认证系统故障"
            )
            
            with pytest.raises(CertificationError, match="认证流程异常"):
                await pipeline.run_complete_certification(sample_strategy)
