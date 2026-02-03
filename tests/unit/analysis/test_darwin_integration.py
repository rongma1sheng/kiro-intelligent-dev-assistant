"""DarwinIntegration单元测试

白皮书依据: 第五章 5.3 达尔文进化体系集成

测试覆盖率目标: 100%
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, MagicMock

from src.analysis.darwin_integration import (
    DarwinIntegration,
    OptimizationSuggestion,
    EvolutionDirection,
    LifecyclePrediction,
    EvolutionReport
)


class TestDarwinIntegration:
    """DarwinIntegration测试类"""
    
    @pytest.fixture
    def darwin_integration(self):
        """创建DarwinIntegration实例"""
        return DarwinIntegration()
    
    @pytest.fixture
    def sample_analysis_results(self):
        """示例分析结果"""
        return {
            'overfitting_risk': {'risk_level': 'high'},
            'parameter_stability': {'stability_score': 0.6},
            'feature_importance': {
                'feature1': 0.3,
                'feature2': 0.02,
                'feature3': 0.01,
                'feature4': 0.01
            },
            'logic_complexity': {'complexity_score': 0.9},
            'factor_performance': {'ic_mean': 0.02},
            'parameter_sensitivity': {'high_sensitivity_params': ['param1']},
            'market_adaptation': {'adaptation_score': 0.6}
        }
    
    @pytest.fixture
    def sample_arena_results(self):
        """示例Arena结果"""
        return {
            'max_drawdown': 0.25,
            'sharpe_ratio': 1.5,
            'annual_return': 0.20
        }
    
    @pytest.fixture
    def sample_performance_history(self):
        """示例历史表现数据"""
        return [
            {'sharpe_ratio': 1.5, 'ic': 0.05, 'market_regime': 'bull'},
            {'sharpe_ratio': 1.4, 'ic': 0.04, 'market_regime': 'bull'},
            {'sharpe_ratio': 1.3, 'ic': 0.04, 'market_regime': 'neutral'},
            {'sharpe_ratio': 1.2, 'ic': 0.03, 'market_regime': 'neutral'},
            {'sharpe_ratio': 1.1, 'ic': 0.03, 'market_regime': 'neutral'},
            {'sharpe_ratio': 1.0, 'ic': 0.02, 'market_regime': 'bear', 'overfitting_risk': 'high'},
            {'sharpe_ratio': 0.9, 'ic': 0.02, 'market_regime': 'bear'},
            {'sharpe_ratio': 0.8, 'ic': 0.01, 'market_regime': 'bear'},
            {'sharpe_ratio': 0.7, 'ic': 0.01, 'market_regime': 'bear'},
            {'sharpe_ratio': 0.6, 'ic': 0.01, 'market_regime': 'bear'}
        ]
    
    # ==================== 初始化测试 ====================
    
    def test_init(self, darwin_integration):
        """测试初始化"""
        assert darwin_integration is not None
        assert darwin_integration.knowledge_base is None
        assert darwin_integration.strategy_analyzer is None
    
    def test_init_with_dependencies(self):
        """测试带依赖的初始化"""
        knowledge_base = Mock()
        strategy_analyzer = Mock()
        
        darwin = DarwinIntegration(
            knowledge_base=knowledge_base,
            strategy_analyzer=strategy_analyzer
        )
        
        assert darwin.knowledge_base == knowledge_base
        assert darwin.strategy_analyzer == strategy_analyzer
    
    # ==================== 优化建议测试 ====================
    
    def test_generate_optimization_suggestions_success(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_arena_results
    ):
        """测试生成优化建议 - 成功"""
        suggestions = darwin_integration.generate_optimization_suggestions(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            arena_results=sample_arena_results
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # 验证建议结构
        for suggestion in suggestions:
            assert isinstance(suggestion, OptimizationSuggestion)
            assert suggestion.strategy_id == 'test_strategy_001'
            assert suggestion.suggestion_type in ['parameter', 'feature', 'logic', 'risk']
            assert suggestion.priority in ['high', 'medium', 'low']
            assert suggestion.implementation_difficulty in ['easy', 'medium', 'hard']
            assert 0 <= suggestion.expected_improvement <= 1
    
    def test_generate_optimization_suggestions_empty_strategy_id(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试生成优化建议 - 空策略ID"""
        with pytest.raises(ValueError, match="策略ID不能为空"):
            darwin_integration.generate_optimization_suggestions(
                strategy_id='',
                analysis_results=sample_analysis_results
            )
    
    def test_generate_optimization_suggestions_empty_analysis(
        self,
        darwin_integration
    ):
        """测试生成优化建议 - 空分析结果"""
        with pytest.raises(ValueError, match="分析结果不能为空"):
            darwin_integration.generate_optimization_suggestions(
                strategy_id='test_strategy_001',
                analysis_results={}
            )
    
    def test_generate_parameter_suggestions(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试生成参数优化建议"""
        suggestions = darwin_integration._generate_parameter_suggestions(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results
        )
        
        assert isinstance(suggestions, list)
        # 应该有2个参数建议 (过拟合 + 参数稳定性)
        assert len(suggestions) == 2
        
        # 验证过拟合建议
        overfitting_suggestion = next(
            s for s in suggestions
            if '过拟合' in s.description
        )
        assert overfitting_suggestion.priority == 'high'
    
    def test_generate_feature_suggestions(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试生成特征优化建议"""
        suggestions = darwin_integration._generate_feature_suggestions(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results
        )
        
        assert isinstance(suggestions, list)
        # 应该有0个或1个特征建议 (取决于低重要性特征数量)
        # 当前有3个低重要性特征 (feature2, feature3, feature4)
        # 但阈值是 > 3, 所以不会生成建议
        assert len(suggestions) == 0
    
    def test_generate_logic_suggestions(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试生成逻辑优化建议"""
        suggestions = darwin_integration._generate_logic_suggestions(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results
        )
        
        assert isinstance(suggestions, list)
        # 应该有1个逻辑建议 (复杂度过高)
        assert len(suggestions) == 1
        assert '简化策略逻辑' in suggestions[0].description
    
    def test_generate_risk_suggestions(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_arena_results
    ):
        """测试生成风险优化建议"""
        suggestions = darwin_integration._generate_risk_suggestions(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            arena_results=sample_arena_results
        )
        
        assert isinstance(suggestions, list)
        # 应该有1个风险建议 (最大回撤过高)
        assert len(suggestions) == 1
        assert '最大回撤' in suggestions[0].description
    
    # ==================== 进化方向测试 ====================
    
    def test_guide_evolution_direction_success(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_performance_history
    ):
        """测试指导进化方向 - 成功"""
        directions = darwin_integration.guide_evolution_direction(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            historical_performance=sample_performance_history
        )
        
        assert isinstance(directions, list)
        assert len(directions) > 0
        
        # 验证方向结构
        for direction in directions:
            assert isinstance(direction, EvolutionDirection)
            assert direction.strategy_id == 'test_strategy_001'
            assert direction.direction_type in ['factor', 'parameter', 'logic', 'ensemble']
            assert 0 <= direction.confidence <= 1
    
    def test_guide_evolution_direction_empty_strategy_id(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试指导进化方向 - 空策略ID"""
        with pytest.raises(ValueError, match="策略ID不能为空"):
            darwin_integration.guide_evolution_direction(
                strategy_id='',
                analysis_results=sample_analysis_results
            )
    
    def test_guide_factor_evolution(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试指导因子进化方向"""
        directions = darwin_integration._guide_factor_evolution(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results
        )
        
        assert isinstance(directions, list)
        # 应该有1个因子方向 (IC值偏低)
        assert len(directions) == 1
        assert '因子IC值' in directions[0].description
    
    def test_guide_parameter_evolution(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试指导参数进化方向"""
        # 添加高敏感参数
        analysis_with_sensitivity = sample_analysis_results.copy()
        analysis_with_sensitivity['parameter_sensitivity'] = {
            'high_sensitivity_params': ['param1', 'param2']
        }
        
        directions = darwin_integration._guide_parameter_evolution(
            strategy_id='test_strategy_001',
            analysis_results=analysis_with_sensitivity
        )
        
        assert isinstance(directions, list)
        assert len(directions) == 1
        assert '高敏感参数' in directions[0].description
    
    def test_guide_logic_evolution(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试指导逻辑进化方向"""
        directions = darwin_integration._guide_logic_evolution(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results
        )
        
        assert isinstance(directions, list)
        # 应该有1个逻辑方向 (市场适配性低)
        assert len(directions) == 1
        assert '市场状态识别' in directions[0].description
    
    def test_guide_ensemble_evolution(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_performance_history
    ):
        """测试指导集成进化方向"""
        directions = darwin_integration._guide_ensemble_evolution(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            historical_performance=sample_performance_history
        )
        
        assert isinstance(directions, list)
        # 应该有1个集成方向 (历史数据充足)
        assert len(directions) == 1
        assert '策略集成' in directions[0].description
    
    # ==================== 生命周期预测测试 ====================
    
    def test_predict_lifecycle_success(
        self,
        darwin_integration,
        sample_performance_history
    ):
        """测试预测生命周期 - 成功"""
        prediction = darwin_integration.predict_lifecycle(
            strategy_id='test_strategy_001',
            performance_history=sample_performance_history
        )
        
        assert isinstance(prediction, LifecyclePrediction)
        assert prediction.strategy_id == 'test_strategy_001'
        assert prediction.current_stage in ['growth', 'mature', 'decline', 'obsolete']
        assert prediction.remaining_days >= 0
        assert 0 <= prediction.decay_rate <= 1
        assert 0 <= prediction.confidence <= 1
        assert isinstance(prediction.factors, list)
        assert len(prediction.factors) > 0
    
    def test_predict_lifecycle_empty_strategy_id(
        self,
        darwin_integration,
        sample_performance_history
    ):
        """测试预测生命周期 - 空策略ID"""
        with pytest.raises(ValueError, match="策略ID不能为空"):
            darwin_integration.predict_lifecycle(
                strategy_id='',
                performance_history=sample_performance_history
            )
    
    def test_predict_lifecycle_insufficient_data(
        self,
        darwin_integration
    ):
        """测试预测生命周期 - 数据不足"""
        with pytest.raises(ValueError, match="历史数据不足"):
            darwin_integration.predict_lifecycle(
                strategy_id='test_strategy_001',
                performance_history=[{'sharpe_ratio': 1.0}]  # 只有1个数据点
            )
    
    def test_calculate_trend(self, darwin_integration):
        """测试计算趋势"""
        # 上升趋势
        upward_series = [1.0, 1.1, 1.2, 1.3, 1.4]
        trend = darwin_integration._calculate_trend(upward_series)
        assert trend > 0
        
        # 下降趋势
        downward_series = [1.4, 1.3, 1.2, 1.1, 1.0]
        trend = darwin_integration._calculate_trend(downward_series)
        assert trend < 0
        
        # 平稳趋势
        flat_series = [1.0, 1.0, 1.0, 1.0, 1.0]
        trend = darwin_integration._calculate_trend(flat_series)
        assert abs(trend) < 0.01
    
    def test_calculate_decay_rate(self, darwin_integration):
        """测试计算衰减率"""
        # 有衰减
        decaying_series = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
        decay_rate = darwin_integration._calculate_decay_rate(decaying_series)
        assert decay_rate > 0
        
        # 无衰减
        stable_series = [1.0] * 10
        decay_rate = darwin_integration._calculate_decay_rate(stable_series)
        assert decay_rate == 0.0
    
    def test_determine_lifecycle_stage(self, darwin_integration):
        """测试判断生命周期阶段"""
        # 成长期
        stage = darwin_integration._determine_lifecycle_stage(
            sharpe_trend=0.02,
            ic_trend=0.002,
            decay_rate=0.05
        )
        assert stage == 'growth'
        
        # 成熟期
        stage = darwin_integration._determine_lifecycle_stage(
            sharpe_trend=0.005,
            ic_trend=0.0005,
            decay_rate=0.15
        )
        assert stage == 'mature'
        
        # 衰退期
        stage = darwin_integration._determine_lifecycle_stage(
            sharpe_trend=-0.02,
            ic_trend=-0.002,
            decay_rate=0.3
        )
        assert stage == 'decline'
        
        # 淘汰期
        stage = darwin_integration._determine_lifecycle_stage(
            sharpe_trend=-0.05,
            ic_trend=-0.005,
            decay_rate=0.6
        )
        assert stage == 'obsolete'
    
    def test_predict_remaining_days(self, darwin_integration):
        """测试预测剩余天数"""
        # 成长期
        days = darwin_integration._predict_remaining_days(
            current_stage='growth',
            decay_rate=0.1,
            sharpe_series=[1.0] * 10
        )
        assert days > 100
        
        # 成熟期
        days = darwin_integration._predict_remaining_days(
            current_stage='mature',
            decay_rate=0.1,
            sharpe_series=[1.0] * 10
        )
        assert 50 < days <= 100
        
        # 衰退期
        days = darwin_integration._predict_remaining_days(
            current_stage='decline',
            decay_rate=0.3,
            sharpe_series=[1.0] * 10
        )
        assert 0 < days <= 60
        
        # 淘汰期
        days = darwin_integration._predict_remaining_days(
            current_stage='obsolete',
            decay_rate=0.6,
            sharpe_series=[1.0] * 10
        )
        assert days == 0
    
    def test_calculate_prediction_confidence(self, darwin_integration):
        """测试计算预测置信度"""
        # 数据充足,衰减率低
        confidence = darwin_integration._calculate_prediction_confidence(
            data_points=100,
            decay_rate=0.1
        )
        assert confidence > 0.8
        
        # 数据不足,衰减率高
        confidence = darwin_integration._calculate_prediction_confidence(
            data_points=10,
            decay_rate=0.5
        )
        assert confidence < 0.5
    
    def test_identify_lifecycle_factors(
        self,
        darwin_integration,
        sample_performance_history
    ):
        """测试识别生命周期因素"""
        factors = darwin_integration._identify_lifecycle_factors(
            performance_history=sample_performance_history,
            current_stage='decline'
        )
        
        assert isinstance(factors, list)
        assert len(factors) > 0
        # 应该包含熊市环境和策略衰退
        assert any('熊市' in f for f in factors)
        assert any('衰退' in f for f in factors)
    
    # ==================== 进化报告测试 ====================
    
    def test_generate_evolution_report_success(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_arena_results,
        sample_performance_history
    ):
        """测试生成进化报告 - 成功"""
        report = darwin_integration.generate_evolution_report(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            arena_results=sample_arena_results,
            historical_performance=sample_performance_history
        )
        
        assert isinstance(report, EvolutionReport)
        assert report.strategy_id == 'test_strategy_001'
        assert isinstance(report.optimization_suggestions, list)
        assert len(report.optimization_suggestions) > 0
        assert isinstance(report.evolution_directions, list)
        assert len(report.evolution_directions) > 0
        assert isinstance(report.lifecycle_prediction, LifecyclePrediction)
        assert report.z2h_status == 'not_certified'
    
    def test_generate_evolution_report_empty_strategy_id(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试生成进化报告 - 空策略ID"""
        with pytest.raises(ValueError, match="策略ID不能为空"):
            darwin_integration.generate_evolution_report(
                strategy_id='',
                analysis_results=sample_analysis_results
            )
    
    def test_generate_evolution_report_empty_analysis(
        self,
        darwin_integration
    ):
        """测试生成进化报告 - 空分析结果"""
        with pytest.raises(ValueError, match="分析结果不能为空"):
            darwin_integration.generate_evolution_report(
                strategy_id='test_strategy_001',
                analysis_results={}
            )
    
    def test_generate_evolution_report_insufficient_history(
        self,
        darwin_integration,
        sample_analysis_results
    ):
        """测试生成进化报告 - 历史数据不足"""
        report = darwin_integration.generate_evolution_report(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            historical_performance=[{'sharpe_ratio': 1.0}]  # 数据不足
        )
        
        # 应该使用默认预测
        assert report.lifecycle_prediction.current_stage == 'unknown'
        assert report.lifecycle_prediction.remaining_days == -1
        assert '数据不足' in report.lifecycle_prediction.factors
    
    def test_generate_evolution_report_with_gene_capsule(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_performance_history
    ):
        """测试生成进化报告 - 包含基因胶囊"""
        analysis_with_capsule = sample_analysis_results.copy()
        analysis_with_capsule['gene_capsule_id'] = 'capsule_001'
        analysis_with_capsule['z2h_status'] = 'certified'
        
        report = darwin_integration.generate_evolution_report(
            strategy_id='test_strategy_001',
            analysis_results=analysis_with_capsule,
            historical_performance=sample_performance_history
        )
        
        assert report.gene_capsule_id == 'capsule_001'
        assert report.z2h_status == 'certified'
    
    # ==================== 性能测试 ====================
    
    def test_performance_optimization_suggestions(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_arena_results
    ):
        """测试优化建议生成性能 < 5秒"""
        import time
        
        start_time = time.time()
        
        suggestions = darwin_integration.generate_optimization_suggestions(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            arena_results=sample_arena_results
        )
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 5.0, f"优化建议生成耗时{elapsed_time:.2f}秒,超过5秒限制"
        assert len(suggestions) > 0
    
    def test_performance_lifecycle_prediction(
        self,
        darwin_integration,
        sample_performance_history
    ):
        """测试生命周期预测性能 < 2秒"""
        import time
        
        start_time = time.time()
        
        prediction = darwin_integration.predict_lifecycle(
            strategy_id='test_strategy_001',
            performance_history=sample_performance_history
        )
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 2.0, f"生命周期预测耗时{elapsed_time:.2f}秒,超过2秒限制"
        assert prediction is not None
    
    def test_performance_evolution_report(
        self,
        darwin_integration,
        sample_analysis_results,
        sample_arena_results,
        sample_performance_history
    ):
        """测试进化报告生成性能 < 10秒"""
        import time
        
        start_time = time.time()
        
        report = darwin_integration.generate_evolution_report(
            strategy_id='test_strategy_001',
            analysis_results=sample_analysis_results,
            arena_results=sample_arena_results,
            historical_performance=sample_performance_history
        )
        
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 10.0, f"进化报告生成耗时{elapsed_time:.2f}秒,超过10秒限制"
        assert report is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/analysis/darwin_integration', '--cov-report=term'])
