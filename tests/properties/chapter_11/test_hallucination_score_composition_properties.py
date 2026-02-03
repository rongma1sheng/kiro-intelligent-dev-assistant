"""
Property-Based Tests for Hallucination Score Composition

白皮书依据: 第十一章 11.1 防幻觉系统
测试属性: Property 8 - Hallucination Score Composition

验证需求:
- Requirements 3.3: Layer 1 - 内部矛盾检测 (25%权重)
- Requirements 3.4: Layer 2 - 事实一致性检查 (30%权重)
- Requirements 3.5: Layer 3 - 置信度校准 (20%权重)
- Requirements 3.6: Layer 4 - 语义漂移检测 (15%权重)
- Requirements 3.7: Layer 5 - 黑名单匹配 (10%权重)
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis import HealthCheck
from src.brain.hallucination_filter import HallucinationFilter


class TestHallucinationScoreComposition:
    """Property 8: Hallucination Score Composition
    
    **Validates: Requirements 3.3-3.7**
    
    验证幻觉分数组成的正确性:
    - 加权平均计算必须正确
    - 权重总和必须为1.0
    - 各层分数必须在[0, 1]范围内
    - 总分必须在[0, 1]范围内
    """
    
    @pytest.fixture
    def filter(self):
        """创建HallucinationFilter实例"""
        return HallucinationFilter()
    
    def test_weights_sum_to_one(self, filter):
        """Property: 权重总和必须为1.0
        
        5层检测的权重总和必须精确等于1.0
        """
        weights = filter.weights
        
        total_weight = sum(weights.values())
        
        # Property: 权重总和必须为1.0
        assert abs(total_weight - 1.0) < 1e-10, (
            f"权重总和应该为1.0，实际为 {total_weight:.10f}\n"
            f"权重详情: {weights}"
        )
    
    def test_weights_match_specification(self, filter):
        """Property: 权重必须匹配白皮书规范
        
        验证各层权重符合白皮书定义:
        - Layer 1 (contradiction): 25% = 0.25
        - Layer 2 (factual_consistency): 30% = 0.30
        - Layer 3 (confidence_calibration): 20% = 0.20
        - Layer 4 (semantic_drift): 15% = 0.15
        - Layer 5 (blacklist_match): 10% = 0.10
        """
        weights = filter.weights
        
        expected_weights = {
            'contradiction': 0.25,
            'factual_consistency': 0.30,
            'confidence_calibration': 0.20,
            'semantic_drift': 0.15,
            'blacklist_match': 0.10
        }
        
        for layer, expected_weight in expected_weights.items():
            actual_weight = weights.get(layer)
            
            assert actual_weight is not None, (
                f"缺少层 '{layer}' 的权重定义"
            )
            
            assert abs(actual_weight - expected_weight) < 1e-10, (
                f"层 '{layer}' 的权重应该为 {expected_weight}，"
                f"实际为 {actual_weight}"
            )
    
    @given(
        contradiction_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        factual_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        confidence_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        drift_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        blacklist_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weighted_average_calculation(
        self,
        filter,
        contradiction_score,
        factual_score,
        confidence_score,
        drift_score,
        blacklist_score
    ):
        """Property: 加权平均计算必须正确
        
        对于任意的5层分数，总分必须等于加权平均值
        """
        # 计算期望的加权平均
        weights = filter.weights
        expected_total = (
            contradiction_score * weights['contradiction'] +
            factual_score * weights['factual_consistency'] +
            confidence_score * weights['confidence_calibration'] +
            drift_score * weights['semantic_drift'] +
            blacklist_score * weights['blacklist_match']
        )
        
        # 模拟检测结果
        original_check_contradiction = filter._check_contradiction
        original_check_factual = filter._check_factual_consistency
        original_check_confidence = filter._check_confidence_calibration
        original_check_drift = filter._check_semantic_drift
        original_check_blacklist = filter._check_blacklist
        
        try:
            filter._check_contradiction = lambda r: (contradiction_score, [])
            filter._check_factual_consistency = lambda r, c: (factual_score, [])
            filter._check_confidence_calibration = lambda r, c: (confidence_score, [])
            filter._check_semantic_drift = lambda r, c: (drift_score, [])
            filter._check_blacklist = lambda r: (blacklist_score, [])
            
            result = filter.detect_hallucination("test response", {})
            
            # Property: 总分必须等于加权平均
            assert abs(result.confidence - expected_total) < 1e-6, (
                f"加权平均计算错误:\n"
                f"期望: {expected_total:.6f}\n"
                f"实际: {result.confidence:.6f}\n"
                f"分数: contradiction={contradiction_score:.4f}, "
                f"factual={factual_score:.4f}, "
                f"confidence={confidence_score:.4f}, "
                f"drift={drift_score:.4f}, "
                f"blacklist={blacklist_score:.4f}"
            )
            
            # Property: 总分必须在[0, 1]范围内
            assert 0.0 <= result.confidence <= 1.0, (
                f"总分 {result.confidence:.6f} 超出[0, 1]范围"
            )
            
        finally:
            # 恢复原始方法
            filter._check_contradiction = original_check_contradiction
            filter._check_factual_consistency = original_check_factual
            filter._check_confidence_calibration = original_check_confidence
            filter._check_semantic_drift = original_check_drift
            filter._check_blacklist = original_check_blacklist
    
    @given(
        response_text=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_individual_scores_in_valid_range(self, filter, response_text):
        """Property: 各层分数必须在[0, 1]范围内
        
        每一层的检测分数都必须在有效范围[0, 1]内
        """
        result = filter.detect_hallucination(response_text, {})
        
        for layer, score in result.scores.items():
            # Property: 每层分数必须在[0, 1]范围内
            assert 0.0 <= score <= 1.0, (
                f"层 '{layer}' 的分数 {score:.6f} 超出[0, 1]范围"
            )
    
    @given(
        response_text=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_total_score_in_valid_range(self, filter, response_text):
        """Property: 总分必须在[0, 1]范围内
        
        无论输入如何，总分都必须在有效范围[0, 1]内
        """
        result = filter.detect_hallucination(response_text, {})
        
        # Property: 总分必须在[0, 1]范围内
        assert 0.0 <= result.confidence <= 1.0, (
            f"总分 {result.confidence:.6f} 超出[0, 1]范围\n"
            f"各层分数: {result.scores}"
        )
    
    @given(
        layer_index=st.integers(min_value=0, max_value=4)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_single_layer_contribution(self, filter, layer_index):
        """Property: 单层贡献度
        
        当只有一层有分数时，总分应该等于该层分数乘以权重
        """
        layers = ['contradiction', 'factual_consistency', 'confidence_calibration', 
                  'semantic_drift', 'blacklist_match']
        active_layer = layers[layer_index]
        
        # 设置只有一层有分数1.0，其他层为0
        scores = {layer: (1.0 if layer == active_layer else 0.0) for layer in layers}
        
        # 模拟检测结果
        original_check_contradiction = filter._check_contradiction
        original_check_factual = filter._check_factual_consistency
        original_check_confidence = filter._check_confidence_calibration
        original_check_drift = filter._check_semantic_drift
        original_check_blacklist = filter._check_blacklist
        
        try:
            filter._check_contradiction = lambda r: (scores['contradiction'], [])
            filter._check_factual_consistency = lambda r, c: (scores['factual_consistency'], [])
            filter._check_confidence_calibration = lambda r, c: (scores['confidence_calibration'], [])
            filter._check_semantic_drift = lambda r, c: (scores['semantic_drift'], [])
            filter._check_blacklist = lambda r: (scores['blacklist_match'], [])
            
            result = filter.detect_hallucination("test response", {})
            
            # Property: 总分应该等于该层权重
            expected_score = filter.weights[active_layer]
            assert abs(result.confidence - expected_score) < 1e-6, (
                f"单层 '{active_layer}' 贡献度错误:\n"
                f"期望: {expected_score:.6f} (权重)\n"
                f"实际: {result.confidence:.6f}"
            )
            
        finally:
            # 恢复原始方法
            filter._check_contradiction = original_check_contradiction
            filter._check_factual_consistency = original_check_factual
            filter._check_confidence_calibration = original_check_confidence
            filter._check_semantic_drift = original_check_drift
            filter._check_blacklist = original_check_blacklist
    
    def test_all_layers_max_score(self, filter):
        """Property: 所有层最大分数
        
        当所有层分数都为1.0时，总分应该为1.0
        """
        # 模拟所有层分数为1.0
        original_check_contradiction = filter._check_contradiction
        original_check_factual = filter._check_factual_consistency
        original_check_confidence = filter._check_confidence_calibration
        original_check_drift = filter._check_semantic_drift
        original_check_blacklist = filter._check_blacklist
        
        try:
            filter._check_contradiction = lambda r: (1.0, [])
            filter._check_factual_consistency = lambda r, c: (1.0, [])
            filter._check_confidence_calibration = lambda r, c: (1.0, [])
            filter._check_semantic_drift = lambda r, c: (1.0, [])
            filter._check_blacklist = lambda r: (1.0, [])
            
            result = filter.detect_hallucination("test response", {})
            
            # Property: 所有层最大分数时，总分应该为1.0
            assert abs(result.confidence - 1.0) < 1e-6, (
                f"所有层最大分数时，总分应该为1.0，实际为 {result.confidence:.6f}"
            )
            
        finally:
            # 恢复原始方法
            filter._check_contradiction = original_check_contradiction
            filter._check_factual_consistency = original_check_factual
            filter._check_confidence_calibration = original_check_confidence
            filter._check_semantic_drift = original_check_drift
            filter._check_blacklist = original_check_blacklist
    
    def test_all_layers_min_score(self, filter):
        """Property: 所有层最小分数
        
        当所有层分数都为0.0时，总分应该为0.0
        """
        # 模拟所有层分数为0.0
        original_check_contradiction = filter._check_contradiction
        original_check_factual = filter._check_factual_consistency
        original_check_confidence = filter._check_confidence_calibration
        original_check_drift = filter._check_semantic_drift
        original_check_blacklist = filter._check_blacklist
        
        try:
            filter._check_contradiction = lambda r: (0.0, [])
            filter._check_factual_consistency = lambda r, c: (0.0, [])
            filter._check_confidence_calibration = lambda r, c: (0.0, [])
            filter._check_semantic_drift = lambda r, c: (0.0, [])
            filter._check_blacklist = lambda r: (0.0, [])
            
            result = filter.detect_hallucination("test response", {})
            
            # Property: 所有层最小分数时，总分应该为0.0
            assert abs(result.confidence - 0.0) < 1e-6, (
                f"所有层最小分数时，总分应该为0.0，实际为 {result.confidence:.6f}"
            )
            
        finally:
            # 恢复原始方法
            filter._check_contradiction = original_check_contradiction
            filter._check_factual_consistency = original_check_factual
            filter._check_confidence_calibration = original_check_confidence
            filter._check_semantic_drift = original_check_drift
            filter._check_blacklist = original_check_blacklist
    
    @given(
        weight_multiplier=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weight_update_validation(self, filter, weight_multiplier):
        """Property: 权重更新验证
        
        更新权重时必须验证总和为1.0
        """
        # 尝试更新权重（不满足总和为1.0）
        invalid_weights = {
            'contradiction': 0.25 * weight_multiplier,
            'factual_consistency': 0.30 * weight_multiplier,
            'confidence_calibration': 0.20 * weight_multiplier,
            'semantic_drift': 0.15 * weight_multiplier,
            'blacklist_match': 0.10 * weight_multiplier
        }
        
        total_weight = sum(invalid_weights.values())
        
        if abs(total_weight - 1.0) > 0.01:
            # Property: 权重总和不为1.0时，更新应该失败
            with pytest.raises(ValueError, match="权重总和必须为1.0"):
                filter.update_weights(invalid_weights)
        else:
            # Property: 权重总和为1.0时，更新应该成功
            filter.update_weights(invalid_weights)
            
            # 验证权重已更新
            for layer, weight in invalid_weights.items():
                assert abs(filter.weights[layer] - weight) < 1e-6, (
                    f"权重更新失败: {layer}"
                )
    
    def test_score_composition_consistency(self, filter):
        """Property: 分数组成一致性
        
        返回的scores字典必须包含所有5层的分数
        """
        result = filter.detect_hallucination("test response", {})
        
        expected_layers = {
            'contradiction',
            'factual_consistency',
            'confidence_calibration',
            'semantic_drift',
            'blacklist_match'
        }
        
        actual_layers = set(result.scores.keys())
        
        # Property: 必须包含所有5层
        assert actual_layers == expected_layers, (
            f"分数组成不完整:\n"
            f"期望层: {expected_layers}\n"
            f"实际层: {actual_layers}\n"
            f"缺失层: {expected_layers - actual_layers}\n"
            f"多余层: {actual_layers - expected_layers}"
        )
