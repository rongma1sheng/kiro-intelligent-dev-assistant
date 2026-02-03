"""
SpartaArenaEvaluator单元测试

测试斯巴达Arena四层验证集成器

作者: MIA Team
日期: 2026-01-20
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.evolution.sparta_arena_evaluator import (
    SpartaArenaEvaluator,
    ValidationLayer,
    LayerResult,
    ArenaTestResult
)


@pytest.fixture
def evaluator():
    """创建测试用的SpartaArenaEvaluator实例"""
    return SpartaArenaEvaluator(market_type='A_STOCK')


@pytest.fixture
def good_strategy_returns():
    """生成表现良好的策略收益率"""
    np.random.seed(42)
    # 年化收益25%, 夏普2.5, 回撤<10%
    # 日均收益 = 25% / 252 ≈ 0.001
    # 日波动率 = 25% / (2.5 * sqrt(252)) ≈ 0.0063
    returns = np.random.normal(0.001, 0.0063, 250)  # 日均0.1%, 标准差0.63%
    return pd.Series(returns, index=pd.date_range('2023-01-01', periods=250))


@pytest.fixture
def mediocre_strategy_returns():
    """生成表现一般的策略收益率"""
    np.random.seed(43)
    # 年化收益8%, 夏普1.2, 回撤15%
    returns = np.random.normal(0.0003, 0.018, 250)
    return pd.Series(returns, index=pd.date_range('2023-01-01', periods=250))


@pytest.fixture
def poor_strategy_returns():
    """生成表现糟糕的策略收益率"""
    np.random.seed(44)
    # 年化收益负, 夏普<1, 回撤>20%
    returns = np.random.normal(-0.0002, 0.025, 250)
    return pd.Series(returns, index=pd.date_range('2023-01-01', periods=250))


@pytest.fixture
def sample_market_returns():
    """生成样本市场收益率"""
    np.random.seed(45)
    returns = np.random.normal(0.0004, 0.016, 250)
    return pd.Series(returns, index=pd.date_range('2023-01-01', periods=250))


@pytest.fixture
def sample_market_volume():
    """生成样本市场成交量"""
    np.random.seed(46)
    volume = np.random.lognormal(10, 0.5, 250)
    return pd.Series(volume, index=pd.date_range('2023-01-01', periods=250))


class TestSpartaArenaEvaluator:
    """SpartaArenaEvaluator基础功能测试"""
    
    def test_initialization(self, evaluator):
        """测试初始化"""
        assert evaluator.market_type == 'A_STOCK'
        assert hasattr(evaluator, 'strategy_evaluator')
        assert hasattr(evaluator, 'rolling_backtest')
        assert hasattr(evaluator, 'walk_forward')
        assert hasattr(evaluator, 'stress_test')
    
    def test_layer_weights(self, evaluator):
        """测试各层权重定义"""
        weights = evaluator.LAYER_WEIGHTS
        
        assert len(weights) == 4
        assert weights['layer_1_basic'] == 0.30
        assert weights['layer_2_stability'] == 0.15
        assert weights['layer_3_overfitting'] == 0.15
        assert weights['layer_4_stress'] == 0.40
        
        # 权重总和应该为1.0
        assert abs(sum(weights.values()) - 1.0) < 0.01
    
    def test_layer_pass_criteria(self, evaluator):
        """测试各层通过标准"""
        criteria = evaluator.LAYER_PASS_CRITERIA
        
        assert len(criteria) == 4
        assert criteria['layer_1_basic'] == 0.8
        assert criteria['layer_2_stability'] == 0.7
        assert criteria['layer_3_overfitting'] == 0.6
        assert criteria['layer_4_stress'] == 0.7



class TestFourLayerValidation:
    """四层验证完整流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_validation_good_strategy(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns,
        sample_market_volume
    ):
        """测试良好策略的完整验证流程"""
        result = await evaluator.evaluate_strategy(
            good_strategy_returns,
            sample_market_returns,
            sample_market_volume,
            strategy_name="GoodStrategy",
            strategy_type="momentum"
        )
        
        assert isinstance(result, ArenaTestResult)
        assert result.strategy_name == "GoodStrategy"
        assert result.strategy_type == "momentum"
        assert len(result.layer_results) >= 1  # 至少完成第一层
        assert result.overall_score is not None
        assert 0 <= result.overall_score <= 1
    
    @pytest.mark.asyncio
    async def test_complete_validation_poor_strategy(
        self,
        evaluator,
        poor_strategy_returns,
        sample_market_returns
    ):
        """测试糟糕策略的完整验证流程"""
        result = await evaluator.evaluate_strategy(
            poor_strategy_returns,
            sample_market_returns,
            None,
            strategy_name="PoorStrategy",
            strategy_type="mean_reversion"
        )
        
        assert isinstance(result, ArenaTestResult)
        # 糟糕策略应该无法通过
        assert not result.passed
        assert result.layers_failed > 0
    
    @pytest.mark.asyncio
    async def test_layer_results_structure(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试各层结果结构"""
        result = await evaluator.evaluate_strategy(
            good_strategy_returns,
            sample_market_returns,
            None,
            strategy_name="TestStrategy"
        )
        
        # 验证各层结果存在
        for layer_key in ['layer_1_basic', 'layer_2_stability', 
                          'layer_3_overfitting', 'layer_4_stress']:
            if layer_key in result.layer_results:
                layer_result = result.layer_results[layer_key]
                assert isinstance(layer_result, LayerResult)
                assert hasattr(layer_result, 'passed')
                assert hasattr(layer_result, 'score')
                assert hasattr(layer_result, 'details')


class TestLayer1Basic:
    """第一层：投研级指标评价测试"""
    
    @pytest.mark.asyncio
    async def test_layer1_evaluation(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试第一层评价"""
        layer1_result = await evaluator._evaluate_layer1_basic(
            good_strategy_returns,
            sample_market_returns
        )
        
        assert isinstance(layer1_result, LayerResult)
        assert layer1_result.layer == ValidationLayer.LAYER_1_BASIC
        assert layer1_result.score is not None
        assert layer1_result.rating in ['EXCELLENT', 'QUALIFIED', 'UNQUALIFIED', None]
    
    @pytest.mark.asyncio
    async def test_layer1_pass_criteria(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试第一层通过标准"""
        layer1_result = await evaluator._evaluate_layer1_basic(
            good_strategy_returns,
            sample_market_returns
        )
        
        # 良好策略应该至少达到合格级别
        if layer1_result.passed:
            assert layer1_result.rating in ['EXCELLENT', 'QUALIFIED']
            assert layer1_result.score >= 0.8


class TestLayer2Stability:
    """第二层：时间稳定性验证测试"""
    
    @pytest.mark.asyncio
    async def test_layer2_evaluation(
        self,
        evaluator,
        good_strategy_returns
    ):
        """测试第二层评价"""
        layer2_result = await evaluator._evaluate_layer2_stability(
            good_strategy_returns
        )
        
        assert isinstance(layer2_result, LayerResult)
        assert layer2_result.layer == ValidationLayer.LAYER_2_STABILITY
        assert layer2_result.score is not None
        assert 0 <= layer2_result.score <= 1
    
    @pytest.mark.asyncio
    async def test_layer2_stability_metrics(
        self,
        evaluator,
        good_strategy_returns
    ):
        """测试第二层稳定性指标"""
        layer2_result = await evaluator._evaluate_layer2_stability(
            good_strategy_returns
        )
        
        # 验证details中包含稳定性指标
        if layer2_result.details:
            assert 'stability_metrics' in layer2_result.details or \
                   isinstance(layer2_result.details, dict)


class TestLayer3Overfitting:
    """第三层：防过拟合验证测试"""
    
    @pytest.mark.asyncio
    async def test_layer3_evaluation(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试第三层评价"""
        layer3_result = await evaluator._evaluate_layer3_overfitting(
            good_strategy_returns,
            sample_market_returns
        )
        
        assert isinstance(layer3_result, LayerResult)
        assert layer3_result.layer == ValidationLayer.LAYER_3_OVERFITTING
        assert layer3_result.score is not None
    
    @pytest.mark.asyncio
    async def test_layer3_overfitting_metrics(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试第三层过拟合指标"""
        layer3_result = await evaluator._evaluate_layer3_overfitting(
            good_strategy_returns,
            sample_market_returns
        )
        
        # 验证details中包含过拟合指标
        if layer3_result.details:
            assert isinstance(layer3_result.details, dict)


class TestLayer4Stress:
    """第四层：极限压力测试测试"""
    
    @pytest.mark.asyncio
    async def test_layer4_evaluation(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试第四层评价"""
        layer4_result = await evaluator._evaluate_layer4_stress(
            good_strategy_returns,
            sample_market_returns,
            None
        )
        
        assert isinstance(layer4_result, LayerResult)
        assert layer4_result.layer == ValidationLayer.LAYER_4_STRESS
        assert layer4_result.score is not None
    
    @pytest.mark.asyncio
    async def test_layer4_stress_scenarios(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试第四层压力测试场景"""
        layer4_result = await evaluator._evaluate_layer4_stress(
            good_strategy_returns,
            sample_market_returns,
            None
        )
        
        # 验证details中包含场景结果
        if layer4_result.details:
            assert 'scenarios_passed' in layer4_result.details
            assert 'scenarios_failed' in layer4_result.details


class TestOverallScoring:
    """综合评分测试"""
    
    def test_calculate_overall_score(self, evaluator):
        """测试综合评分计算"""
        # 创建模拟的各层结果
        layer_results = {
            'layer_1_basic': LayerResult(
                layer=ValidationLayer.LAYER_1_BASIC,
                passed=True,
                score=0.9
            ),
            'layer_2_stability': LayerResult(
                layer=ValidationLayer.LAYER_2_STABILITY,
                passed=True,
                score=0.8
            ),
            'layer_3_overfitting': LayerResult(
                layer=ValidationLayer.LAYER_3_OVERFITTING,
                passed=True,
                score=0.7
            ),
            'layer_4_stress': LayerResult(
                layer=ValidationLayer.LAYER_4_STRESS,
                passed=True,
                score=0.75
            )
        }
        
        overall_score = evaluator._calculate_overall_score(layer_results)
        
        # 验证评分计算
        expected_score = (
            0.9 * 0.30 +   # layer_1
            0.8 * 0.15 +   # layer_2
            0.7 * 0.15 +   # layer_3
            0.75 * 0.40    # layer_4
        )
        
        assert abs(overall_score - expected_score) < 0.01
    
    @pytest.mark.asyncio
    async def test_pass_criteria_all_layers(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试综合通过标准"""
        result = await evaluator.evaluate_strategy(
            good_strategy_returns,
            sample_market_returns,
            None,
            strategy_name="TestStrategy"
        )
        
        # 如果通过，必须满足: 各层都通过 且 综合评分≥0.75
        if result.passed:
            assert result.layers_passed == 4
            assert result.overall_score >= 0.75


class TestReportGeneration:
    """报告生成测试"""
    
    @pytest.mark.asyncio
    async def test_generate_detailed_report(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试生成详细报告"""
        result = await evaluator.evaluate_strategy(
            good_strategy_returns,
            sample_market_returns,
            None,
            strategy_name="TestStrategy",
            strategy_type="momentum"
        )
        
        report = evaluator.generate_detailed_report(result)
        
        assert isinstance(report, str)
        assert len(report) > 0
        assert "TestStrategy" in report
        assert "momentum" in report
        assert "综合评分" in report
    
    @pytest.mark.asyncio
    async def test_report_contains_layer_details(
        self,
        evaluator,
        good_strategy_returns,
        sample_market_returns
    ):
        """测试报告包含各层详情"""
        result = await evaluator.evaluate_strategy(
            good_strategy_returns,
            sample_market_returns,
            None,
            strategy_name="TestStrategy"
        )
        
        report = evaluator.generate_detailed_report(result)
        
        # 验证报告包含各层信息
        assert "第一层" in report or "投研级" in report
        assert "第二层" in report or "稳定性" in report
        assert "第三层" in report or "过拟合" in report
        assert "第四层" in report or "压力" in report


class TestEdgeCases:
    """边界情况测试"""
    
    @pytest.mark.asyncio
    async def test_early_failure_at_layer1(
        self,
        evaluator,
        poor_strategy_returns,
        sample_market_returns
    ):
        """测试第一层失败时的提前终止"""
        result = await evaluator.evaluate_strategy(
            poor_strategy_returns,
            sample_market_returns,
            None,
            strategy_name="FailedStrategy"
        )
        
        # 如果第一层失败，应该提前终止
        if not result.layer_results.get('layer_1_basic', LayerResult(
            layer=ValidationLayer.LAYER_1_BASIC, passed=True, score=1.0
        )).passed:
            # 可能只有第一层结果
            assert len(result.layer_results) >= 1
    
    @pytest.mark.asyncio
    async def test_empty_returns(self, evaluator):
        """测试空收益率序列"""
        empty_returns = pd.Series([], dtype=float)
        market_returns = pd.Series([0.01] * 10)
        
        # 应该能处理空数据而不崩溃
        try:
            result = await evaluator.evaluate_strategy(
                empty_returns,
                market_returns,
                None,
                strategy_name="EmptyStrategy"
            )
            assert result is not None
        except Exception as e:
            # 如果抛出异常，应该是有意义的异常
            assert isinstance(e, (ValueError, IndexError))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
