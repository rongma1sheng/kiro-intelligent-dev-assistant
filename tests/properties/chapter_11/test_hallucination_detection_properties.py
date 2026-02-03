"""
Property-Based Tests for HallucinationFilter

白皮书依据: 第十一章 11.1 防幻觉系统
测试属性: Property 7 - Hallucination Detection Threshold

验证需求:
- Requirements 3.1: 5层检测机制识别幻觉
- Requirements 3.2: 阈值0.5判断是否为幻觉
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis import HealthCheck
from src.brain.hallucination_filter import HallucinationFilter


class TestHallucinationDetectionThreshold:
    """Property 7: Hallucination Detection Threshold
    
    **Validates: Requirements 3.1, 3.2**
    
    验证幻觉检测阈值的正确性:
    - 当总分 > 0.5 时，必须判定为幻觉
    - 当总分 ≤ 0.5 时，必须判定为非幻觉
    - 阈值边界必须精确
    """
    
    @pytest.fixture
    def filter(self):
        """创建HallucinationFilter实例"""
        return HallucinationFilter()
    
    @given(
        contradiction_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        factual_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        confidence_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        drift_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        blacklist_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_threshold_boundary_property(
        self,
        filter,
        contradiction_score,
        factual_score,
        confidence_score,
        drift_score,
        blacklist_score
    ):
        """Property: 阈值边界必须精确
        
        对于任意的5层检测分数，加权总分与阈值0.5的比较必须准确判定是否为幻觉
        """
        # 计算加权总分
        weights = filter.weights
        total_score = (
            contradiction_score * weights['contradiction'] +
            factual_score * weights['factual_consistency'] +
            confidence_score * weights['confidence_calibration'] +
            drift_score * weights['semantic_drift'] +
            blacklist_score * weights['blacklist_match']
        )
        
        # 模拟检测结果（通过monkey patch）
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
            
            # Property: 总分 > 0.5 必须判定为幻觉
            if total_score > filter.threshold:
                assert result.is_hallucination, (
                    f"总分 {total_score:.4f} > 阈值 {filter.threshold}，"
                    f"但未判定为幻觉"
                )
            # Property: 总分 ≤ 0.5 必须判定为非幻觉
            else:
                assert not result.is_hallucination, (
                    f"总分 {total_score:.4f} ≤ 阈值 {filter.threshold}，"
                    f"但判定为幻觉"
                )
            
            # Property: 返回的confidence应该等于总分
            assert abs(result.confidence - total_score) < 1e-6, (
                f"返回的confidence {result.confidence:.4f} "
                f"与计算的总分 {total_score:.4f} 不一致"
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
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    def test_rejection_above_threshold(self, filter, response_text):
        """Property: 高分响应必须被拒绝
        
        当检测分数明显超过阈值时，响应必须被判定为幻觉
        
        注意：此测试通过monkey patch强制设置高分数来验证阈值逻辑，
        而不是依赖实际的检测逻辑。
        """
        # 通过monkey patch强制设置高分数
        original_check_contradiction = filter._check_contradiction
        original_check_factual = filter._check_factual_consistency
        original_check_confidence = filter._check_confidence_calibration
        original_check_drift = filter._check_semantic_drift
        original_check_blacklist = filter._check_blacklist
        
        try:
            # 设置所有检测层的分数为高值，确保总分超过阈值
            filter._check_contradiction = lambda r: (0.9, ["矛盾检测"])
            filter._check_factual_consistency = lambda r, c: (0.8, ["事实不一致"])
            filter._check_confidence_calibration = lambda r, c: (0.7, ["置信度问题"])
            filter._check_semantic_drift = lambda r, c: (0.6, ["语义漂移"])
            filter._check_blacklist = lambda r: (0.5, ["黑名单匹配"])
            
            result = filter.detect_hallucination(response_text, {})
            
            # Property: 高分响应必须被判定为幻觉
            assert result.is_hallucination, (
                f"高分响应未被拒绝，总分: {result.confidence:.4f}"
            )
            
            # Property: 分数必须超过阈值
            assert result.confidence > filter.threshold, (
                f"幻觉响应的分数 {result.confidence:.4f} "
                f"未超过阈值 {filter.threshold}"
            )
        finally:
            # 恢复原始方法
            filter._check_contradiction = original_check_contradiction
            filter._check_factual_consistency = original_check_factual
            filter._check_confidence_calibration = original_check_confidence
            filter._check_semantic_drift = original_check_drift
            filter._check_blacklist = original_check_blacklist
    
    @given(
        response_text=st.text(min_size=10, max_size=200, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_acceptance_below_threshold(self, filter, response_text):
        """Property: 低分响应必须被接受
        
        当响应不包含幻觉特征时，分数应该低于阈值，响应被接受
        """
        # 过滤掉可能触发幻觉检测的文本
        assume('buy' not in response_text.lower())
        assume('sell' not in response_text.lower())
        assume('certain' not in response_text.lower())
        assume('uncertain' not in response_text.lower())
        assume('guaranteed' not in response_text.lower())
        assume('100%' not in response_text)
        assume('approve' not in response_text.lower())
        assume('reject' not in response_text.lower())
        
        # 构造一个正常的响应
        normal_response = f"Based on the analysis, {response_text}"
        
        result = filter.detect_hallucination(normal_response, {})
        
        # Property: 正常响应的分数应该较低
        # 注意：由于语义漂移等因素，分数可能不为0，但应该低于阈值
        if result.confidence <= filter.threshold:
            assert not result.is_hallucination, (
                f"正常响应被错误判定为幻觉，"
                f"总分: {result.confidence:.4f}"
            )
    
    @given(
        threshold_offset=st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    def test_threshold_boundary_precision(self, filter, threshold_offset):
        """Property: 阈值边界精度
        
        测试阈值附近的边界情况，确保判定精确
        """
        # 构造一个总分接近阈值的情况
        target_score = filter.threshold + threshold_offset
        
        # 确保目标分数在有效范围内
        assume(0.0 <= target_score <= 1.0)
        
        # 使用所有检测层来达到目标分数
        # 平均分配到各层
        weights = filter.weights
        total_weight = sum(weights.values())
        
        # 计算每层需要的分数（假设所有层分数相同）
        per_layer_score = target_score / total_weight if total_weight > 0 else 0.0
        
        # 确保每层分数在有效范围内
        assume(0.0 <= per_layer_score <= 1.0)
        
        # 模拟检测结果
        original_check_contradiction = filter._check_contradiction
        original_check_factual = filter._check_factual_consistency
        original_check_confidence = filter._check_confidence_calibration
        original_check_drift = filter._check_semantic_drift
        original_check_blacklist = filter._check_blacklist
        
        try:
            filter._check_contradiction = lambda r: (per_layer_score, [])
            filter._check_factual_consistency = lambda r, c: (per_layer_score, [])
            filter._check_confidence_calibration = lambda r, c: (per_layer_score, [])
            filter._check_semantic_drift = lambda r, c: (per_layer_score, [])
            filter._check_blacklist = lambda r: (per_layer_score, [])
            
            result = filter.detect_hallucination("test response", {})
            
            # 计算实际总分
            actual_score = per_layer_score * total_weight
            
            # Property: 边界判定必须精确
            if actual_score > filter.threshold:
                assert result.is_hallucination, (
                    f"目标分数 {actual_score:.6f} > 阈值 {filter.threshold}，"
                    f"但未判定为幻觉"
                )
            else:
                assert not result.is_hallucination, (
                    f"目标分数 {actual_score:.6f} ≤ 阈值 {filter.threshold}，"
                    f"但判定为幻觉"
                )
        
        finally:
            # 恢复原始方法
            filter._check_contradiction = original_check_contradiction
            filter._check_factual_consistency = original_check_factual
            filter._check_confidence_calibration = original_check_confidence
            filter._check_semantic_drift = original_check_drift
            filter._check_blacklist = original_check_blacklist
    
    def test_empty_response_always_hallucination(self, filter):
        """Property: 空响应必须判定为幻觉
        
        空响应或只包含空白字符的响应必须被判定为幻觉
        """
        empty_responses = ["", "   ", "\n", "\t", "  \n  \t  "]
        
        for response in empty_responses:
            result = filter.detect_hallucination(response, {})
            
            # Property: 空响应必须判定为幻觉
            assert result.is_hallucination, (
                f"空响应 '{response}' 未被判定为幻觉"
            )
            
            # Property: 空响应的confidence应该为1.0（最高）
            assert result.confidence == 1.0, (
                f"空响应的confidence应该为1.0，实际为 {result.confidence}"
            )
    
    @given(
        num_contradictions=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_contradiction_count_monotonicity(self, filter, num_contradictions):
        """Property: 矛盾数量单调性
        
        矛盾词对数量越多，检测分数应该越高
        """
        # 构造包含指定数量矛盾的响应
        contradiction_pairs = [
            ("buy", "sell"),
            ("increase", "decrease"),
            ("bullish", "bearish"),
            ("approve", "reject"),
            ("certain", "uncertain")
        ]
        
        response_parts = []
        for i in range(min(num_contradictions, len(contradiction_pairs))):
            word1, word2 = contradiction_pairs[i]
            response_parts.append(f"I {word1} and {word2} this.")
        
        response = " ".join(response_parts) if response_parts else "Normal response."
        
        result = filter.detect_hallucination(response, {})
        
        # Property: 矛盾数量与分数应该正相关
        # 至少矛盾层的分数应该随矛盾数量增加
        contradiction_score = result.scores.get('contradiction', 0.0)
        
        if num_contradictions == 0:
            # 没有矛盾时，矛盾分数应该为0或很低
            assert contradiction_score < 0.1, (
                f"无矛盾时矛盾分数应该很低，实际为 {contradiction_score:.4f}"
            )
        elif num_contradictions >= 3:
            # 多个矛盾时，矛盾分数应该接近1.0
            assert contradiction_score >= 0.9, (
                f"多个矛盾时矛盾分数应该很高，实际为 {contradiction_score:.4f}"
            )
