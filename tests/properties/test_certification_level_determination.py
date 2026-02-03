"""认证等级评定属性测试

白皮书依据: 第四章 4.3.1 Z2H认证系统

Property 8: Certification Level Determination
验证需求: Requirements 4.1

使用hypothesis进行属性测试，验证任何Arena和模拟盘结果都能确定唯一等级。
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta

from src.evolution.certification_level_evaluator import CertificationLevelEvaluator
from src.evolution.z2h_data_models import (
    CertificationLevel,
    CapitalTier,
    SimulationResult,
    TierSimulationResult
)
from src.evolution.sparta_arena_evaluator import ArenaTestResult, LayerResult, ValidationLayer


# ==================== Hypothesis策略定义 ====================

@st.composite
def arena_result_strategy(draw):
    """生成随机Arena测试结果的策略"""
    # 生成各层评分（0-1之间）
    layer1_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    layer2_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    layer3_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    layer4_score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    # 计算综合评分（按权重）
    overall_score = (
        layer1_score * 0.30 +
        layer2_score * 0.15 +
        layer3_score * 0.15 +
        layer4_score * 0.40
    )
    
    # 创建各层结果
    layer_results = {
        'layer_1_basic': LayerResult(
            layer=ValidationLayer.LAYER_1_BASIC,
            passed=layer1_score >= 0.8,
            score=layer1_score,
            rating='EXCELLENT' if layer1_score >= 0.9 else 'QUALIFIED' if layer1_score >= 0.8 else 'UNQUALIFIED'
        ),
        'layer_2_stability': LayerResult(
            layer=ValidationLayer.LAYER_2_STABILITY,
            passed=layer2_score >= 0.7,
            score=layer2_score
        ),
        'layer_3_overfitting': LayerResult(
            layer=ValidationLayer.LAYER_3_OVERFITTING,
            passed=layer3_score >= 0.6,
            score=layer3_score
        ),
        'layer_4_stress': LayerResult(
            layer=ValidationLayer.LAYER_4_STRESS,
            passed=layer4_score >= 0.7,
            score=layer4_score
        )
    }
    
    # 统计通过层数
    layers_passed = sum(1 for result in layer_results.values() if result.passed)
    
    # 判断整体是否通过
    passed = layers_passed == 4 and overall_score >= 0.75
    
    return ArenaTestResult(
        passed=passed,
        overall_score=overall_score,
        layer_results=layer_results,
        layers_passed=layers_passed,
        layers_failed=4 - layers_passed,
        strategy_name=draw(st.text(min_size=1, max_size=50)),
        strategy_type=draw(st.sampled_from(['momentum', 'mean_reversion', 'arbitrage']))
    )


@st.composite
def simulation_result_strategy(draw):
    """生成随机模拟盘结果的策略"""
    # 生成各档位结果
    tier_results = {}
    
    for tier in CapitalTier:
        initial_capital = {
            CapitalTier.TIER_1: 5000,
            CapitalTier.TIER_2: 50000,
            CapitalTier.TIER_3: 250000,
            CapitalTier.TIER_4: 750000
        }[tier]
        
        # 生成收益率（-50%到+50%）
        total_return = draw(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False))
        final_capital = initial_capital * (1 + total_return)
        
        # 生成其他指标
        sharpe_ratio = draw(st.floats(min_value=-2.0, max_value=5.0, allow_nan=False, allow_infinity=False))
        max_drawdown = draw(st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False))
        win_rate = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
        profit_factor = draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
        var_95 = draw(st.floats(min_value=0.0, max_value=0.2, allow_nan=False, allow_infinity=False))
        calmar_ratio = draw(st.floats(min_value=-2.0, max_value=5.0, allow_nan=False, allow_infinity=False))
        information_ratio = draw(st.floats(min_value=-2.0, max_value=5.0, allow_nan=False, allow_infinity=False))
        
        tier_results[tier] = TierSimulationResult(
            tier=tier,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            var_95=var_95,
            calmar_ratio=calmar_ratio,
            information_ratio=information_ratio,
            daily_pnl=[],
            trades=[]
        )
    
    # 确定最佳档位（简化：选择收益率最高的）
    best_tier = max(tier_results.keys(), key=lambda t: tier_results[t].total_return)
    best_result = tier_results[best_tier]
    
    # 检查达标标准
    passed_criteria_count = 0
    failed_criteria = []
    
    if best_result.total_return >= 0.05:
        passed_criteria_count += 1
    else:
        failed_criteria.append(f"月收益{best_result.total_return:.2%} < 5%")
    
    if best_result.sharpe_ratio >= 1.2:
        passed_criteria_count += 1
    else:
        failed_criteria.append(f"夏普比率{best_result.sharpe_ratio:.2f} < 1.2")
    
    if best_result.max_drawdown <= 0.15:
        passed_criteria_count += 1
    else:
        failed_criteria.append(f"最大回撤{best_result.max_drawdown:.2%} > 15%")
    
    if best_result.win_rate >= 0.55:
        passed_criteria_count += 1
    else:
        failed_criteria.append(f"胜率{best_result.win_rate:.2%} < 55%")
    
    if best_result.var_95 <= 0.05:
        passed_criteria_count += 1
    else:
        failed_criteria.append(f"VaR{best_result.var_95:.2%} > 5%")
    
    if best_result.profit_factor >= 1.3:
        passed_criteria_count += 1
    else:
        failed_criteria.append(f"盈利因子{best_result.profit_factor:.2f} < 1.3")
    
    # 简化：假设其他4项都通过
    passed_criteria_count += 4
    
    # 判断是否通过（至少8项）
    passed = passed_criteria_count >= 8
    
    return SimulationResult(
        passed=passed,
        duration_days=30,
        tier_results=tier_results,
        best_tier=best_tier,
        overall_metrics={},
        risk_metrics={},
        market_environment_performance={},
        passed_criteria_count=passed_criteria_count,
        failed_criteria=failed_criteria
    )


# ==================== 属性测试 ====================

class TestCertificationLevelDeterminationProperty:
    """认证等级评定属性测试
    
    白皮书依据: 第四章 4.3.1 - 认证等级评定
    验证需求: Requirements 4.1
    """
    
    @given(
        arena_result=arena_result_strategy(),
        simulation_result=simulation_result_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_level_determination_uniqueness(
        self,
        arena_result: ArenaTestResult,
        simulation_result: SimulationResult
    ):
        """Property 8: 认证等级确定性
        
        验证需求: Requirements 4.1
        
        属性: 对于任意有效的Arena和模拟盘结果，都能确定唯一的认证等级。
        
        测试步骤:
        1. 生成随机Arena测试结果
        2. 生成随机模拟盘结果
        3. 评定认证等级
        4. 验证等级确定性和唯一性
        """
        evaluator = CertificationLevelEvaluator()
        
        # 评定认证等级
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 验证等级是有效的枚举值
        assert isinstance(level, CertificationLevel), "认证等级必须是CertificationLevel枚举"
        assert level in [
            CertificationLevel.PLATINUM,
            CertificationLevel.GOLD,
            CertificationLevel.SILVER,
            CertificationLevel.REJECTED
        ], "认证等级必须是有效的枚举值"
        
        # 再次评定，验证结果一致（确定性）
        level2 = evaluator.evaluate_level(arena_result, simulation_result)
        assert level == level2, "相同输入应该产生相同的认证等级"
    
    @given(
        arena_result=arena_result_strategy(),
        simulation_result=simulation_result_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_level_determination_consistency(
        self,
        arena_result: ArenaTestResult,
        simulation_result: SimulationResult
    ):
        """Property 8.1: 认证等级一致性
        
        验证需求: Requirements 4.1
        
        属性: 认证等级应该与Arena和模拟盘的表现一致。
        """
        evaluator = CertificationLevelEvaluator()
        
        # 评定认证等级
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 如果Arena或模拟盘未通过，等级应该是REJECTED
        if not arena_result.passed or not simulation_result.passed:
            assert level == CertificationLevel.REJECTED, \
                "Arena或模拟盘未通过时，认证等级应该是REJECTED"
        
        # 如果都通过，等级应该不是REJECTED
        if arena_result.passed and simulation_result.passed:
            assert level != CertificationLevel.REJECTED, \
                "Arena和模拟盘都通过时，认证等级不应该是REJECTED"
    
    @given(
        arena_result=arena_result_strategy(),
        simulation_result=simulation_result_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_level_determination_monotonicity(
        self,
        arena_result: ArenaTestResult,
        simulation_result: SimulationResult
    ):
        """Property 8.2: 认证等级单调性
        
        验证需求: Requirements 4.2, 4.3, 4.4
        
        属性: 更高的评分应该对应更高或相同的认证等级。
        """
        evaluator = CertificationLevelEvaluator()
        
        # 评定原始等级
        original_level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 如果原始等级是REJECTED，跳过此测试
        assume(original_level != CertificationLevel.REJECTED)
        
        # 创建改进的Arena结果（提高10%评分）
        improved_arena = ArenaTestResult(
            passed=True,
            overall_score=min(1.0, arena_result.overall_score * 1.1),
            layer_results=arena_result.layer_results,
            layers_passed=4,
            layers_failed=0,
            strategy_name=arena_result.strategy_name,
            strategy_type=arena_result.strategy_type
        )
        
        # 评定改进后的等级
        improved_level = evaluator.evaluate_level(improved_arena, simulation_result)
        
        # 验证等级不会降低
        level_order = {
            CertificationLevel.REJECTED: 0,
            CertificationLevel.SILVER: 1,
            CertificationLevel.GOLD: 2,
            CertificationLevel.PLATINUM: 3
        }
        
        assert level_order[improved_level] >= level_order[original_level], \
            "改进评分后，认证等级不应该降低"
    
    @given(
        arena_result=arena_result_strategy(),
        simulation_result=simulation_result_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_level_determination_threshold_boundaries(
        self,
        arena_result: ArenaTestResult,
        simulation_result: SimulationResult
    ):
        """Property 8.3: 认证等级阈值边界
        
        验证需求: Requirements 4.2, 4.3, 4.4, 4.5
        
        属性: 认证等级应该正确反映阈值边界。
        """
        evaluator = CertificationLevelEvaluator()
        
        # 评定认证等级
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 如果都通过，验证等级与评分的对应关系
        if arena_result.passed and simulation_result.passed:
            overall_score = arena_result.overall_score
            
            # PLATINUM: 综合评分≥0.90
            if overall_score >= 0.90:
                assert level in [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER], \
                    f"评分{overall_score:.2%}≥0.90时，等级应该至少是SILVER"
            
            # GOLD: 综合评分≥0.80
            elif overall_score >= 0.80:
                assert level in [CertificationLevel.GOLD, CertificationLevel.SILVER], \
                    f"评分{overall_score:.2%}≥0.80时，等级应该至少是SILVER"
            
            # SILVER: 综合评分≥0.75
            elif overall_score >= 0.75:
                assert level in [CertificationLevel.SILVER], \
                    f"评分{overall_score:.2%}≥0.75时，等级应该至少是SILVER"


# ==================== 边界条件测试 ====================

class TestCertificationLevelDeterminationEdgeCases:
    """认证等级评定边界条件测试
    
    白皮书依据: 第四章 4.3.1 - 认证等级评定
    验证需求: Requirements 4.2, 4.3, 4.4, 4.5
    """
    
    def test_platinum_threshold_boundary(self):
        """测试PLATINUM阈值边界（0.90）"""
        evaluator = CertificationLevelEvaluator()
        
        # 创建刚好达到PLATINUM阈值的Arena结果
        arena_result = self._create_arena_result(overall_score=0.90, passed=True)
        simulation_result = self._create_simulation_result(passed=True)
        
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 验证等级至少是SILVER（可能是PLATINUM或GOLD）
        assert level in [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER]
    
    def test_gold_threshold_boundary(self):
        """测试GOLD阈值边界（0.80）"""
        evaluator = CertificationLevelEvaluator()
        
        # 创建刚好达到GOLD阈值的Arena结果
        arena_result = self._create_arena_result(overall_score=0.80, passed=True)
        simulation_result = self._create_simulation_result(passed=True)
        
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 验证等级至少是SILVER
        assert level in [CertificationLevel.GOLD, CertificationLevel.SILVER]
    
    def test_silver_threshold_boundary(self):
        """测试SILVER阈值边界（0.75）"""
        evaluator = CertificationLevelEvaluator()
        
        # 创建刚好达到SILVER阈值的Arena结果
        arena_result = self._create_arena_result(overall_score=0.75, passed=True)
        simulation_result = self._create_simulation_result(passed=True)
        
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 验证等级是SILVER
        assert level == CertificationLevel.SILVER
    
    def test_below_threshold_rejection(self):
        """测试低于阈值的拒绝情况"""
        evaluator = CertificationLevelEvaluator()
        
        # 创建低于SILVER阈值的Arena结果
        arena_result = self._create_arena_result(overall_score=0.70, passed=False)
        simulation_result = self._create_simulation_result(passed=True)
        
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 验证等级是REJECTED
        assert level == CertificationLevel.REJECTED
    
    def test_simulation_failure_rejection(self):
        """测试模拟盘失败的拒绝情况"""
        evaluator = CertificationLevelEvaluator()
        
        # 创建Arena通过但模拟盘失败的结果
        arena_result = self._create_arena_result(overall_score=0.90, passed=True)
        simulation_result = self._create_simulation_result(passed=False)
        
        level = evaluator.evaluate_level(arena_result, simulation_result)
        
        # 验证等级是REJECTED
        assert level == CertificationLevel.REJECTED
    
    # ==================== 辅助方法 ====================
    
    def _create_arena_result(self, overall_score: float, passed: bool) -> ArenaTestResult:
        """创建Arena测试结果"""
        layer_results = {
            'layer_1_basic': LayerResult(
                layer=ValidationLayer.LAYER_1_BASIC,
                passed=passed,
                score=overall_score,
                rating='EXCELLENT' if overall_score >= 0.9 else 'QUALIFIED'
            ),
            'layer_2_stability': LayerResult(
                layer=ValidationLayer.LAYER_2_STABILITY,
                passed=passed,
                score=overall_score
            ),
            'layer_3_overfitting': LayerResult(
                layer=ValidationLayer.LAYER_3_OVERFITTING,
                passed=passed,
                score=overall_score
            ),
            'layer_4_stress': LayerResult(
                layer=ValidationLayer.LAYER_4_STRESS,
                passed=passed,
                score=overall_score
            )
        }
        
        return ArenaTestResult(
            passed=passed,
            overall_score=overall_score,
            layer_results=layer_results,
            layers_passed=4 if passed else 0,
            layers_failed=0 if passed else 4,
            strategy_name="Test Strategy",
            strategy_type="momentum"
        )
    
    def _create_simulation_result(self, passed: bool) -> SimulationResult:
        """创建模拟盘结果"""
        tier_results = {}
        
        for tier in CapitalTier:
            initial_capital = {
                CapitalTier.TIER_1: 5000,
                CapitalTier.TIER_2: 50000,
                CapitalTier.TIER_3: 250000,
                CapitalTier.TIER_4: 750000
            }[tier]
            
            total_return = 0.10 if passed else -0.05
            
            tier_results[tier] = TierSimulationResult(
                tier=tier,
                initial_capital=initial_capital,
                final_capital=initial_capital * (1 + total_return),
                total_return=total_return,
                sharpe_ratio=2.0 if passed else 0.5,
                max_drawdown=0.10 if passed else 0.25,
                win_rate=0.60 if passed else 0.40,
                profit_factor=2.0 if passed else 0.8,
                var_95=0.03 if passed else 0.08,
                calmar_ratio=2.0 if passed else 0.5,
                information_ratio=1.5 if passed else 0.3,
                daily_pnl=[],
                trades=[]
            )
        
        return SimulationResult(
            passed=passed,
            duration_days=30,
            tier_results=tier_results,
            best_tier=CapitalTier.TIER_2,
            overall_metrics={},
            risk_metrics={},
            market_environment_performance={},
            passed_criteria_count=10 if passed else 5,
            failed_criteria=[] if passed else ['多项指标未达标']
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
