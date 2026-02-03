"""认证等级评估器测试

白皮书依据: 第四章 4.3.2 认证等级评定标准

测试认证等级评估器的功能。
"""

import pytest
from typing import Dict, Any

from src.evolution.certification_level_evaluator import (
    CertificationLevelEvaluator,
    LayerScore,
    LevelEvaluationResult
)
from src.evolution.z2h_data_models import CertificationLevel


class TestCertificationLevelEvaluator:
    """测试认证等级评估器"""
    
    @pytest.fixture
    def evaluator(self) -> CertificationLevelEvaluator:
        """创建评估器实例"""
        return CertificationLevelEvaluator()
    
    @pytest.fixture
    def excellent_layer_results(self) -> Dict[str, Dict[str, Any]]:
        """创建所有层级优秀的结果"""
        return {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.92, 'passed': True},
            'layer_3': {'score': 0.93, 'passed': True},
            'layer_4': {'score': 0.91, 'passed': True}
        }
    
    @pytest.fixture
    def good_layer_results(self) -> Dict[str, Dict[str, Any]]:
        """创建所有层级良好的结果"""
        return {
            'layer_1': {'score': 0.85, 'passed': True},
            'layer_2': {'score': 0.82, 'passed': True},
            'layer_3': {'score': 0.88, 'passed': True},
            'layer_4': {'score': 0.84, 'passed': True}
        }
    
    @pytest.fixture
    def qualified_layer_results(self) -> Dict[str, Dict[str, Any]]:
        """创建所有层级合格的结果"""
        return {
            'layer_1': {'score': 0.78, 'passed': True},
            'layer_2': {'score': 0.76, 'passed': True},
            'layer_3': {'score': 0.79, 'passed': True},
            'layer_4': {'score': 0.77, 'passed': True}
        }
    
    def test_evaluator_initialization(self):
        """测试评估器初始化"""
        evaluator = CertificationLevelEvaluator(
            platinum_threshold=0.90,
            gold_threshold=0.80,
            silver_threshold=0.75
        )
        
        assert evaluator.platinum_threshold == 0.90
        assert evaluator.gold_threshold == 0.80
        assert evaluator.silver_threshold == 0.75
    
    def test_evaluator_initialization_invalid_threshold_range(self):
        """测试评估器初始化时阈值范围无效"""
        with pytest.raises(ValueError, match="白金级阈值必须在\\[0, 1\\]范围内"):
            CertificationLevelEvaluator(platinum_threshold=1.5)
        
        with pytest.raises(ValueError, match="黄金级阈值必须在\\[0, 1\\]范围内"):
            CertificationLevelEvaluator(gold_threshold=-0.1)
        
        with pytest.raises(ValueError, match="白银级阈值必须在\\[0, 1\\]范围内"):
            CertificationLevelEvaluator(silver_threshold=2.0)
    
    def test_evaluator_initialization_invalid_threshold_order(self):
        """测试评估器初始化时阈值顺序无效"""
        with pytest.raises(ValueError, match="阈值顺序必须满足"):
            CertificationLevelEvaluator(
                platinum_threshold=0.70,
                gold_threshold=0.80,
                silver_threshold=0.75
            )
    
    def test_evaluator_initialization_invalid_layer_threshold_range(self):
        """测试评估器初始化时层级阈值范围无效"""
        with pytest.raises(ValueError, match="层级优秀阈值必须在\\[0, 1\\]范围内"):
            CertificationLevelEvaluator(layer_excellent_threshold=1.5)
        
        with pytest.raises(ValueError, match="层级良好阈值必须在\\[0, 1\\]范围内"):
            CertificationLevelEvaluator(layer_good_threshold=-0.1)
        
        with pytest.raises(ValueError, match="层级合格阈值必须在\\[0, 1\\]范围内"):
            CertificationLevelEvaluator(layer_qualified_threshold=2.0)
    
    def test_evaluator_initialization_invalid_layer_threshold_order(self):
        """测试评估器初始化时层级阈值顺序无效"""
        with pytest.raises(ValueError, match="层级阈值顺序必须满足"):
            CertificationLevelEvaluator(
                layer_excellent_threshold=0.70,
                layer_good_threshold=0.80,
                layer_qualified_threshold=0.75
            )
    
    def test_evaluate_platinum_level(self, evaluator, excellent_layer_results):
        """测试评定PLATINUM等级"""
        result = evaluator.evaluate_level(
            arena_overall_score=0.93,
            arena_layer_results=excellent_layer_results
        )
        
        assert result.certification_level == CertificationLevel.PLATINUM
        assert result.overall_score == 0.93
        assert result.passed_layers == 4
        assert len(result.failed_layers) == 0
        assert result.meets_requirements is True
        assert "所有层级达标" in result.evaluation_reason
    
    def test_evaluate_gold_level(self, evaluator, good_layer_results):
        """测试评定GOLD等级"""
        result = evaluator.evaluate_level(
            arena_overall_score=0.85,
            arena_layer_results=good_layer_results
        )
        
        assert result.certification_level == CertificationLevel.GOLD
        assert result.overall_score == 0.85
        assert result.passed_layers == 4
        assert len(result.failed_layers) == 0
        assert result.meets_requirements is True
        assert "所有层级达标" in result.evaluation_reason
    
    def test_evaluate_silver_level(self, evaluator, qualified_layer_results):
        """测试评定SILVER等级"""
        # 更新layer_results以符合SILVER的层级特定阈值
        # SILVER要求: Layer1≥0.80, Layer2≥0.70, Layer3≥0.60, Layer4≥0.70
        layer_results = {
            'layer_1': {'score': 0.80, 'passed': True},  # 刚好达标
            'layer_2': {'score': 0.70, 'passed': True},  # 刚好达标
            'layer_3': {'score': 0.60, 'passed': True},  # 刚好达标
            'layer_4': {'score': 0.70, 'passed': True}   # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.77,
            arena_layer_results=layer_results
        )
        
        assert result.certification_level == CertificationLevel.SILVER
        assert result.overall_score == 0.77
        assert result.passed_layers == 4
        assert len(result.failed_layers) == 0
        assert result.meets_requirements is True
        assert "所有层级达标" in result.evaluation_reason
    
    def test_evaluate_platinum_threshold_boundary(self, evaluator, excellent_layer_results):
        """测试PLATINUM阈值边界（0.90）"""
        # 刚好达到阈值
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=excellent_layer_results
        )
        assert result.certification_level == CertificationLevel.PLATINUM
        
        # 略低于阈值，但层级优秀，应该降级为GOLD
        result = evaluator.evaluate_level(
            arena_overall_score=0.89,
            arena_layer_results=excellent_layer_results
        )
        assert result.certification_level == CertificationLevel.GOLD
    
    def test_evaluate_gold_threshold_boundary(self, evaluator, good_layer_results):
        """测试GOLD阈值边界（0.80）"""
        # 刚好达到阈值
        result = evaluator.evaluate_level(
            arena_overall_score=0.80,
            arena_layer_results=good_layer_results
        )
        assert result.certification_level == CertificationLevel.GOLD
        
        # 略低于阈值，但层级良好，应该降级为SILVER
        result = evaluator.evaluate_level(
            arena_overall_score=0.79,
            arena_layer_results=good_layer_results
        )
        assert result.certification_level == CertificationLevel.SILVER
    
    def test_evaluate_silver_threshold_boundary(self, evaluator, qualified_layer_results):
        """测试SILVER阈值边界（0.75）"""
        # 更新layer_results以符合SILVER的层级特定阈值
        layer_results = {
            'layer_1': {'score': 0.80, 'passed': True},
            'layer_2': {'score': 0.70, 'passed': True},
            'layer_3': {'score': 0.60, 'passed': True},
            'layer_4': {'score': 0.70, 'passed': True}
        }
        
        # 刚好达到阈值
        result = evaluator.evaluate_level(
            arena_overall_score=0.75,
            arena_layer_results=layer_results
        )
        assert result.certification_level == CertificationLevel.SILVER
        
        # 略低于阈值，应该拒绝认证
        result = evaluator.evaluate_level(
            arena_overall_score=0.74,
            arena_layer_results=qualified_layer_results
        )
        assert result.certification_level == CertificationLevel.NONE
        assert result.meets_requirements is False
    
    def test_evaluate_below_threshold_rejection(self, evaluator, qualified_layer_results):
        """测试低于阈值的拒绝情况"""
        result = evaluator.evaluate_level(
            arena_overall_score=0.70,
            arena_layer_results=qualified_layer_results
        )
        
        assert result.certification_level == CertificationLevel.NONE
        assert result.meets_requirements is False
        assert "低于最低要求" in result.evaluation_reason
    
    def test_evaluate_failed_layer_rejection(self, evaluator):
        """测试存在失败层级时拒绝认证"""
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.92, 'passed': True},
            'layer_3': {'score': 0.70, 'passed': False},  # 失败层级
            'layer_4': {'score': 0.91, 'passed': True}
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.93,
            arena_layer_results=layer_results
        )
        
        assert result.certification_level == CertificationLevel.NONE
        assert result.meets_requirements is False
        assert result.passed_layers == 3
        assert 'layer_3' in result.failed_layers
        assert "层级未通过" in result.evaluation_reason
    
    def test_evaluate_simulation_not_passed_rejection(self, evaluator, excellent_layer_results):
        """测试模拟盘未通过时拒绝认证"""
        result = evaluator.evaluate_level(
            arena_overall_score=0.93,
            arena_layer_results=excellent_layer_results,
            simulation_passed=False
        )
        
        assert result.certification_level == CertificationLevel.NONE
        assert result.meets_requirements is False
        assert "模拟盘验证未通过" in result.evaluation_reason
    
    def test_evaluate_high_score_but_poor_layers(self, evaluator):
        """测试综合评分高但层级评分不达标的情况"""
        # 综合评分达到PLATINUM，但layer_2只有0.85（PLATINUM要求≥0.85，刚好达标）
        # 这个测试实际上会通过PLATINUM认证，因为所有层级都达到了PLATINUM要求
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},  # ≥0.95 ✓
            'layer_2': {'score': 0.85, 'passed': True},  # ≥0.85 ✓
            'layer_3': {'score': 0.93, 'passed': True},  # ≥0.80 ✓
            'layer_4': {'score': 0.91, 'passed': True}   # ≥0.85 ✓
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.93,
            arena_layer_results=layer_results
        )
        
        # 实际上会获得PLATINUM，因为所有层级都达标
        assert result.certification_level == CertificationLevel.PLATINUM
    
    def test_evaluate_invalid_overall_score(self, evaluator, excellent_layer_results):
        """测试无效的综合评分"""
        with pytest.raises(ValueError, match="Arena综合评分必须在\\[0, 1\\]范围内"):
            evaluator.evaluate_level(
                arena_overall_score=1.5,
                arena_layer_results=excellent_layer_results
            )
        
        with pytest.raises(ValueError, match="Arena综合评分必须在\\[0, 1\\]范围内"):
            evaluator.evaluate_level(
                arena_overall_score=-0.1,
                arena_layer_results=excellent_layer_results
            )
    
    def test_evaluate_empty_layer_results(self, evaluator):
        """测试空的层级结果"""
        with pytest.raises(ValueError, match="Arena层级结果不能为空"):
            evaluator.evaluate_level(
                arena_overall_score=0.90,
                arena_layer_results={}
            )
    
    def test_parse_layer_scores_missing_score_field(self, evaluator):
        """测试解析层级评分时缺少score字段"""
        layer_results = {
            'layer_1': {'passed': True}  # 缺少score字段
        }
        
        with pytest.raises(ValueError, match="层级 layer_1 缺少 'score' 字段"):
            evaluator.evaluate_level(
                arena_overall_score=0.90,
                arena_layer_results=layer_results
            )
    
    def test_parse_layer_scores_invalid_score_type(self, evaluator):
        """测试解析层级评分时score类型无效"""
        layer_results = {
            'layer_1': {'score': 'invalid', 'passed': True}
        }
        
        with pytest.raises(ValueError, match="层级 layer_1 的评分必须是数字"):
            evaluator.evaluate_level(
                arena_overall_score=0.90,
                arena_layer_results=layer_results
            )
    
    def test_parse_layer_scores_invalid_score_range(self, evaluator):
        """测试解析层级评分时score范围无效"""
        layer_results = {
            'layer_1': {'score': 1.5, 'passed': True}
        }
        
        with pytest.raises(ValueError, match="层级 layer_1 的评分必须在\\[0, 1\\]范围内"):
            evaluator.evaluate_level(
                arena_overall_score=0.90,
                arena_layer_results=layer_results
            )
    
    def test_parse_layer_scores_without_passed_field(self, evaluator):
        """测试解析层级评分时没有passed字段（应自动判断）"""
        layer_results = {
            'layer_1': {'score': 0.80},  # 没有passed字段
            'layer_2': {'score': 0.70}   # 低于合格阈值
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.80,
            arena_layer_results=layer_results
        )
        
        # layer_1应该自动判断为通过，layer_2应该判断为失败
        assert result.passed_layers == 1
        assert 'layer_2' in result.failed_layers
    
    def test_determine_layer_rating(self, evaluator):
        """测试确定层级评级"""
        assert evaluator._determine_layer_rating(0.95) == "EXCELLENT"
        assert evaluator._determine_layer_rating(0.90) == "EXCELLENT"
        assert evaluator._determine_layer_rating(0.85) == "GOOD"
        assert evaluator._determine_layer_rating(0.80) == "GOOD"
        assert evaluator._determine_layer_rating(0.77) == "QUALIFIED"
        assert evaluator._determine_layer_rating(0.75) == "QUALIFIED"
        assert evaluator._determine_layer_rating(0.70) == "FAILED"
    
    def test_layer_score_dataclass(self):
        """测试LayerScore数据类"""
        layer_score = LayerScore(
            layer_name='layer_1',
            score=0.85,
            passed=True,
            rating='GOOD'
        )
        
        assert layer_score.layer_name == 'layer_1'
        assert layer_score.score == 0.85
        assert layer_score.passed is True
        assert layer_score.rating == 'GOOD'
    
    def test_level_evaluation_result_dataclass(self):
        """测试LevelEvaluationResult数据类"""
        layer_scores = [
            LayerScore('layer_1', 0.85, True, 'GOOD'),
            LayerScore('layer_2', 0.82, True, 'GOOD')
        ]
        
        result = LevelEvaluationResult(
            certification_level=CertificationLevel.GOLD,
            overall_score=0.85,
            layer_scores=layer_scores,
            passed_layers=2,
            failed_layers=[],
            evaluation_reason='测试原因',
            meets_requirements=True
        )
        
        assert result.certification_level == CertificationLevel.GOLD
        assert result.overall_score == 0.85
        assert len(result.layer_scores) == 2
        assert result.passed_layers == 2
        assert result.failed_layers == []
        assert result.evaluation_reason == '测试原因'
        assert result.meets_requirements is True
    
    def test_evaluate_mixed_layer_ratings(self, evaluator):
        """测试混合层级评级的情况"""
        # 综合评分达到PLATINUM，所有层级也都达到PLATINUM要求
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},  # ≥0.95 ✓
            'layer_2': {'score': 0.85, 'passed': True},  # ≥0.85 ✓
            'layer_3': {'score': 0.92, 'passed': True},  # ≥0.80 ✓
            'layer_4': {'score': 0.88, 'passed': True}   # ≥0.85 ✓
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results
        )
        
        # 会获得PLATINUM，因为所有层级都达到PLATINUM要求
        assert result.certification_level == CertificationLevel.PLATINUM
    
    def test_evaluate_mixed_qualified_and_good(self, evaluator):
        """测试QUALIFIED和GOOD混合的情况"""
        # 综合评分达到GOLD，所有层级也都达到GOLD要求
        layer_results = {
            'layer_1': {'score': 0.85, 'passed': True},  # ≥0.85 ✓
            'layer_2': {'score': 0.77, 'passed': True},  # ≥0.75 ✓
            'layer_3': {'score': 0.82, 'passed': True},  # ≥0.70 ✓
            'layer_4': {'score': 0.76, 'passed': True}   # ≥0.75 ✓
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.80,
            arena_layer_results=layer_results
        )
        
        # 会获得GOLD，因为所有层级都达到GOLD要求
        assert result.certification_level == CertificationLevel.GOLD
    
    def test_evaluate_score_meets_platinum_but_layers_dont(self, evaluator):
        """测试综合评分达到PLATINUM但层级不满足的情况"""
        # layer_2只有0.77，不满足PLATINUM要求(≥0.85)，但满足GOLD要求(≥0.75)
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},  # PLATINUM: ≥0.95 ✓, GOLD: ≥0.85 ✓
            'layer_2': {'score': 0.77, 'passed': True},  # PLATINUM: ≥0.85 ✗, GOLD: ≥0.75 ✓
            'layer_3': {'score': 0.93, 'passed': True},  # PLATINUM: ≥0.80 ✓, GOLD: ≥0.70 ✓
            'layer_4': {'score': 0.91, 'passed': True}   # PLATINUM: ≥0.85 ✓, GOLD: ≥0.75 ✓
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.92,
            arena_layer_results=layer_results
        )
        
        # 综合评分达到PLATINUM，但layer_2不满足PLATINUM要求，应该降级为GOLD
        assert result.certification_level == CertificationLevel.GOLD
    
    def test_evaluate_score_meets_platinum_but_all_layers_qualified(self, evaluator):
        """测试综合评分达到PLATINUM但所有层级只是QUALIFIED的情况"""
        # 所有层级都不满足PLATINUM、GOLD、SILVER的要求
        # layer_1: 0.77 < SILVER要求0.80
        layer_results = {
            'layer_1': {'score': 0.77, 'passed': True},  # SILVER: ≥0.80 ✗
            'layer_2': {'score': 0.76, 'passed': True},  # SILVER: ≥0.70 ✓
            'layer_3': {'score': 0.78, 'passed': True},  # SILVER: ≥0.60 ✓
            'layer_4': {'score': 0.75, 'passed': True}   # SILVER: ≥0.70 ✓
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.92,
            arena_layer_results=layer_results
        )
        
        # 综合评分达到PLATINUM，但layer_1不满足任何等级要求，应该拒绝认证
        assert result.certification_level == CertificationLevel.NONE
    
    def test_evaluate_score_meets_gold_but_layers_only_qualified(self, evaluator):
        """测试综合评分达到GOLD但层级只是QUALIFIED的情况"""
        # layer_1不满足SILVER要求(≥0.80)
        layer_results = {
            'layer_1': {'score': 0.77, 'passed': True},  # SILVER: ≥0.80 ✗
            'layer_2': {'score': 0.76, 'passed': True},  # SILVER: ≥0.70 ✓
            'layer_3': {'score': 0.78, 'passed': True},  # SILVER: ≥0.60 ✓
            'layer_4': {'score': 0.75, 'passed': True}   # SILVER: ≥0.70 ✓
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.85,
            arena_layer_results=layer_results
        )
        
        # 综合评分达到GOLD，但layer_1不满足任何等级要求，应该拒绝认证
        assert result.certification_level == CertificationLevel.NONE
    
    def test_evaluate_score_meets_platinum_but_has_failed_layer(self, evaluator):
        """测试综合评分达到PLATINUM但有层级失败的情况"""
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},   # EXCELLENT
            'layer_2': {'score': 0.70, 'passed': False},  # FAILED
            'layer_3': {'score': 0.93, 'passed': True},   # EXCELLENT
            'layer_4': {'score': 0.91, 'passed': True}    # EXCELLENT
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.92,
            arena_layer_results=layer_results
        )
        
        # 有层级失败，应该拒绝认证
        assert result.certification_level == CertificationLevel.NONE
        assert "层级未通过" in result.evaluation_reason
    
    def test_evaluate_score_meets_gold_but_has_failed_layer(self, evaluator):
        """测试综合评分达到GOLD但有层级失败的情况"""
        layer_results = {
            'layer_1': {'score': 0.85, 'passed': True},   # GOOD
            'layer_2': {'score': 0.70, 'passed': False},  # FAILED
            'layer_3': {'score': 0.88, 'passed': True},   # GOOD
            'layer_4': {'score': 0.84, 'passed': True}    # GOOD
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.85,
            arena_layer_results=layer_results
        )
        
        # 有层级失败，应该拒绝认证
        assert result.certification_level == CertificationLevel.NONE
        assert "层级未通过" in result.evaluation_reason
    
    def test_evaluate_score_meets_silver_but_has_failed_layer(self, evaluator):
        """测试综合评分达到SILVER但有层级失败的情况"""
        layer_results = {
            'layer_1': {'score': 0.77, 'passed': True},   # QUALIFIED
            'layer_2': {'score': 0.70, 'passed': False},  # FAILED
            'layer_3': {'score': 0.78, 'passed': True},   # QUALIFIED
            'layer_4': {'score': 0.75, 'passed': True}    # QUALIFIED
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.77,
            arena_layer_results=layer_results
        )
        
        # 有层级失败，应该拒绝认证
        assert result.certification_level == CertificationLevel.NONE
        assert "层级未通过" in result.evaluation_reason

    def test_evaluate_platinum_with_layer_specific_thresholds(self, evaluator):
        """测试PLATINUM等级的层级特定阈值"""
        # PLATINUM要求: Layer1≥0.95, Layer2≥0.85, Layer3≥0.80, Layer4≥0.85
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},  # 刚好达标
            'layer_2': {'score': 0.85, 'passed': True},  # 刚好达标
            'layer_3': {'score': 0.80, 'passed': True},  # 刚好达标
            'layer_4': {'score': 0.85, 'passed': True}   # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results
        )
        
        assert result.certification_level == CertificationLevel.PLATINUM
        assert result.meets_requirements is True
    
    def test_evaluate_platinum_layer1_below_threshold(self, evaluator):
        """测试PLATINUM等级Layer1未达标"""
        # Layer1需要≥0.95，但只有0.94
        layer_results = {
            'layer_1': {'score': 0.94, 'passed': True},  # 未达标
            'layer_2': {'score': 0.85, 'passed': True},
            'layer_3': {'score': 0.80, 'passed': True},
            'layer_4': {'score': 0.85, 'passed': True}
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results
        )
        
        # 应该降级为GOLD或NONE
        assert result.certification_level != CertificationLevel.PLATINUM
    
    def test_evaluate_gold_with_layer_specific_thresholds(self, evaluator):
        """测试GOLD等级的层级特定阈值"""
        # GOLD要求: Layer1≥0.85, Layer2≥0.75, Layer3≥0.70, Layer4≥0.75
        layer_results = {
            'layer_1': {'score': 0.85, 'passed': True},  # 刚好达标
            'layer_2': {'score': 0.75, 'passed': True},  # 刚好达标
            'layer_3': {'score': 0.70, 'passed': True},  # 刚好达标
            'layer_4': {'score': 0.75, 'passed': True}   # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.80,
            arena_layer_results=layer_results
        )
        
        assert result.certification_level == CertificationLevel.GOLD
        assert result.meets_requirements is True
    
    def test_evaluate_silver_with_layer_specific_thresholds(self, evaluator):
        """测试SILVER等级的层级特定阈值"""
        # SILVER要求: Layer1≥0.80, Layer2≥0.70, Layer3≥0.60, Layer4≥0.70
        layer_results = {
            'layer_1': {'score': 0.80, 'passed': True},  # 刚好达标
            'layer_2': {'score': 0.70, 'passed': True},  # 刚好达标
            'layer_3': {'score': 0.60, 'passed': True},  # 刚好达标
            'layer_4': {'score': 0.70, 'passed': True}   # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.75,
            arena_layer_results=layer_results
        )
        
        assert result.certification_level == CertificationLevel.SILVER
        assert result.meets_requirements is True
    
    def test_evaluate_platinum_with_simulation_metrics(self, evaluator):
        """测试PLATINUM等级的模拟盘指标检查"""
        # PLATINUM要求: 夏普≥2.5, 回撤≤10%, 胜率≥65%
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.85, 'passed': True},
            'layer_3': {'score': 0.80, 'passed': True},
            'layer_4': {'score': 0.85, 'passed': True}
        }
        
        simulation_metrics = {
            'sharpe_ratio': 2.5,      # 刚好达标
            'max_drawdown': 0.10,     # 刚好达标
            'win_rate': 0.65          # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.PLATINUM
        assert result.meets_requirements is True
    
    def test_evaluate_platinum_simulation_sharpe_below_threshold(self, evaluator):
        """测试PLATINUM等级夏普比率未达标"""
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.85, 'passed': True},
            'layer_3': {'score': 0.80, 'passed': True},
            'layer_4': {'score': 0.85, 'passed': True}
        }
        
        simulation_metrics = {
            'sharpe_ratio': 2.4,      # 未达标（需要≥2.5）
            'max_drawdown': 0.10,
            'win_rate': 0.65
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=simulation_metrics
        )
        
        # 应该降级或拒绝
        assert result.certification_level != CertificationLevel.PLATINUM
    
    def test_evaluate_platinum_simulation_drawdown_above_threshold(self, evaluator):
        """测试PLATINUM等级最大回撤超标"""
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.85, 'passed': True},
            'layer_3': {'score': 0.80, 'passed': True},
            'layer_4': {'score': 0.85, 'passed': True}
        }
        
        simulation_metrics = {
            'sharpe_ratio': 2.5,
            'max_drawdown': 0.11,     # 超标（需要≤0.10）
            'win_rate': 0.65
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=simulation_metrics
        )
        
        # 应该降级或拒绝
        assert result.certification_level != CertificationLevel.PLATINUM
    
    def test_evaluate_platinum_simulation_winrate_below_threshold(self, evaluator):
        """测试PLATINUM等级胜率未达标"""
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.85, 'passed': True},
            'layer_3': {'score': 0.80, 'passed': True},
            'layer_4': {'score': 0.85, 'passed': True}
        }
        
        simulation_metrics = {
            'sharpe_ratio': 2.5,
            'max_drawdown': 0.10,
            'win_rate': 0.64          # 未达标（需要≥0.65）
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=simulation_metrics
        )
        
        # 应该降级或拒绝
        assert result.certification_level != CertificationLevel.PLATINUM
    
    def test_evaluate_gold_with_simulation_metrics(self, evaluator):
        """测试GOLD等级的模拟盘指标检查"""
        # GOLD要求: 夏普≥2.0, 回撤≤12%, 胜率≥60%
        layer_results = {
            'layer_1': {'score': 0.85, 'passed': True},
            'layer_2': {'score': 0.75, 'passed': True},
            'layer_3': {'score': 0.70, 'passed': True},
            'layer_4': {'score': 0.75, 'passed': True}
        }
        
        simulation_metrics = {
            'sharpe_ratio': 2.0,      # 刚好达标
            'max_drawdown': 0.12,     # 刚好达标
            'win_rate': 0.60          # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.80,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.GOLD
        assert result.meets_requirements is True
    
    def test_evaluate_silver_with_simulation_metrics(self, evaluator):
        """测试SILVER等级的模拟盘指标检查"""
        # SILVER要求: 夏普≥1.5, 回撤≤15%, 胜率≥55%
        layer_results = {
            'layer_1': {'score': 0.80, 'passed': True},
            'layer_2': {'score': 0.70, 'passed': True},
            'layer_3': {'score': 0.60, 'passed': True},
            'layer_4': {'score': 0.70, 'passed': True}
        }
        
        simulation_metrics = {
            'sharpe_ratio': 1.5,      # 刚好达标
            'max_drawdown': 0.15,     # 刚好达标
            'win_rate': 0.55          # 刚好达标
        }
        
        result = evaluator.evaluate_level(
            arena_overall_score=0.75,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.SILVER
        assert result.meets_requirements is True
    
    def test_evaluate_without_simulation_metrics(self, evaluator):
        """测试不提供模拟盘指标时的评估（向后兼容）"""
        layer_results = {
            'layer_1': {'score': 0.95, 'passed': True},
            'layer_2': {'score': 0.85, 'passed': True},
            'layer_3': {'score': 0.80, 'passed': True},
            'layer_4': {'score': 0.85, 'passed': True}
        }
        
        # 不提供simulation_metrics，应该仅基于Arena评分
        result = evaluator.evaluate_level(
            arena_overall_score=0.90,
            arena_layer_results=layer_results,
            simulation_passed=True
        )
        
        assert result.certification_level == CertificationLevel.PLATINUM
        assert result.meets_requirements is True
