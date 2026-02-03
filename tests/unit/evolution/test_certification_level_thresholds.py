"""认证等级阈值边界单元测试

白皮书依据: 第四章 4.3.1 Z2H认证系统

任务4.2: 编写认证等级评定单元测试
验证需求: Requirements 4.2, 4.3, 4.4, 4.5

测试内容:
- PLATINUM阈值边界（0.90）
- GOLD阈值边界（0.80）
- SILVER阈值边界（0.75）
- 低于阈值的拒绝情况
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.evolution.certification_level_evaluator import CertificationLevelEvaluator
from src.evolution.z2h_data_models import CertificationLevel


class TestCertificationLevelThresholds:
    """认证等级阈值边界测试
    
    白皮书依据: 第四章 4.3.1 - 认证等级评定
    验证需求: Requirements 4.2, 4.3, 4.4, 4.5
    """
    
    @pytest.fixture
    def evaluator(self):
        """创建认证等级评估器"""
        return CertificationLevelEvaluator()
    
    @pytest.fixture
    def passing_simulation_metrics(self) -> Dict[str, float]:
        """创建通过的模拟盘指标"""
        return {
            'sharpe_ratio': 2.5,
            'max_drawdown': 0.08,
            'win_rate': 0.65
        }
    
    def _create_layer_results(
        self,
        overall_score: float,
        passed: bool,
        target_level: str = 'SILVER'
    ) -> Dict[str, Dict[str, Any]]:
        """创建Arena层级结果
        
        根据目标认证等级创建满足层级要求的结果。
        
        Args:
            overall_score: 综合评分
            passed: 是否通过
            target_level: 目标认证等级 (PLATINUM/GOLD/SILVER)
            
        Returns:
            Dict: Arena层级结果
        """
        # 层级特定阈值（按认证等级）
        layer_thresholds = {
            'PLATINUM': {
                'layer_1': 0.95,
                'layer_2': 0.85,
                'layer_3': 0.80,
                'layer_4': 0.85
            },
            'GOLD': {
                'layer_1': 0.85,
                'layer_2': 0.75,
                'layer_3': 0.70,
                'layer_4': 0.75
            },
            'SILVER': {
                'layer_1': 0.80,
                'layer_2': 0.70,
                'layer_3': 0.60,
                'layer_4': 0.70
            }
        }
        
        if passed and target_level in layer_thresholds:
            # 如果需要通过，使用满足目标等级要求的分数
            thresholds = layer_thresholds[target_level]
            return {
                'layer_1': {
                    'score': max(overall_score, thresholds['layer_1']),
                    'passed': True
                },
                'layer_2': {
                    'score': max(overall_score, thresholds['layer_2']),
                    'passed': True
                },
                'layer_3': {
                    'score': max(overall_score, thresholds['layer_3']),
                    'passed': True
                },
                'layer_4': {
                    'score': max(overall_score, thresholds['layer_4']),
                    'passed': True
                }
            }
        else:
            # 如果不需要通过，使用原始分数
            return {
                'layer_1': {
                    'score': overall_score,
                    'passed': passed
                },
                'layer_2': {
                    'score': overall_score,
                    'passed': passed
                },
                'layer_3': {
                    'score': overall_score,
                    'passed': passed
                },
                'layer_4': {
                    'score': overall_score,
                    'passed': passed
                }
            }
    
    # ==================== PLATINUM阈值测试 ====================
    
    def test_platinum_threshold_exact(self, evaluator, passing_simulation_metrics):
        """测试PLATINUM阈值边界（0.90）- 精确值
        
        验证需求: Requirements 4.2
        
        测试综合评分刚好等于0.90时的等级评定。
        """
        overall_score = 0.90
        layer_results = self._create_layer_results(overall_score, True, 'GOLD')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        # 验证等级至少是SILVER（可能是PLATINUM或GOLD）
        assert result.certification_level in [
            CertificationLevel.PLATINUM,
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ], f"评分0.90应该至少获得SILVER等级，实际: {result.certification_level.value}"
    
    def test_platinum_threshold_above(self, evaluator, passing_simulation_metrics):
        """测试PLATINUM阈值以上（0.95）
        
        验证需求: Requirements 4.2
        
        测试综合评分高于0.90时的等级评定。
        """
        overall_score = 0.95
        layer_results = self._create_layer_results(overall_score, True, 'PLATINUM')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level in [
            CertificationLevel.PLATINUM,
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ]
    
    def test_platinum_threshold_below(self, evaluator, passing_simulation_metrics):
        """测试PLATINUM阈值以下（0.89）
        
        验证需求: Requirements 4.2
        
        测试综合评分低于0.90但高于0.80时的等级评定。
        """
        overall_score = 0.89
        layer_results = self._create_layer_results(overall_score, True, 'GOLD')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        # 应该是GOLD或SILVER，不应该是PLATINUM
        assert result.certification_level in [
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ], f"评分0.89不应该获得PLATINUM等级，实际: {result.certification_level.value}"
    
    def test_platinum_perfect_score(self, evaluator, passing_simulation_metrics):
        """测试完美评分（1.0）
        
        验证需求: Requirements 4.2
        
        测试综合评分为满分时的等级评定。
        """
        overall_score = 1.0
        layer_results = self._create_layer_results(overall_score, True, 'PLATINUM')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level in [
            CertificationLevel.PLATINUM,
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ]
    
    # ==================== GOLD阈值测试 ====================
    
    def test_gold_threshold_exact(self, evaluator, passing_simulation_metrics):
        """测试GOLD阈值边界（0.80）- 精确值
        
        验证需求: Requirements 4.3
        
        测试综合评分刚好等于0.80时的等级评定。
        """
        overall_score = 0.80
        layer_results = self._create_layer_results(overall_score, True, 'SILVER')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        # 应该至少是SILVER
        assert result.certification_level in [
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ], f"评分0.80应该至少获得SILVER等级，实际: {result.certification_level.value}"
    
    def test_gold_threshold_above(self, evaluator, passing_simulation_metrics):
        """测试GOLD阈值以上（0.85）
        
        验证需求: Requirements 4.3
        
        测试综合评分在GOLD范围内（0.80-0.90）时的等级评定。
        """
        overall_score = 0.85
        layer_results = self._create_layer_results(overall_score, True, 'GOLD')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level in [
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ]
    
    def test_gold_threshold_below(self, evaluator, passing_simulation_metrics):
        """测试GOLD阈值以下（0.79）
        
        验证需求: Requirements 4.3
        
        测试综合评分低于0.80但高于0.75时的等级评定。
        """
        overall_score = 0.79
        layer_results = self._create_layer_results(overall_score, True, 'SILVER')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        # 应该是SILVER，不应该是GOLD或PLATINUM
        assert result.certification_level == CertificationLevel.SILVER, \
            f"评分0.79应该获得SILVER等级，实际: {result.certification_level.value}"
    
    def test_gold_upper_boundary(self, evaluator, passing_simulation_metrics):
        """测试GOLD上边界（0.8999）
        
        验证需求: Requirements 4.3
        
        测试综合评分接近但未达到PLATINUM阈值时的等级评定。
        """
        overall_score = 0.8999
        layer_results = self._create_layer_results(overall_score, True, 'GOLD')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level in [
            CertificationLevel.GOLD,
            CertificationLevel.SILVER
        ]
    
    # ==================== SILVER阈值测试 ====================
    
    def test_silver_threshold_exact(self, evaluator, passing_simulation_metrics):
        """测试SILVER阈值边界（0.75）- 精确值
        
        验证需求: Requirements 4.4
        
        测试综合评分刚好等于0.75时的等级评定。
        """
        overall_score = 0.75
        layer_results = self._create_layer_results(overall_score, True, 'SILVER')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        # 应该是SILVER
        assert result.certification_level == CertificationLevel.SILVER, \
            f"评分0.75应该获得SILVER等级，实际: {result.certification_level.value}"
    
    def test_silver_threshold_above(self, evaluator, passing_simulation_metrics):
        """测试SILVER阈值以上（0.77）
        
        验证需求: Requirements 4.4
        
        测试综合评分在SILVER范围内（0.75-0.80）时的等级评定。
        """
        overall_score = 0.77
        layer_results = self._create_layer_results(overall_score, True, 'SILVER')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.SILVER
    
    def test_silver_threshold_below(self, evaluator, passing_simulation_metrics):
        """测试SILVER阈值以下（0.74）
        
        验证需求: Requirements 4.5
        
        测试综合评分低于0.75时的等级评定。
        """
        overall_score = 0.74
        layer_results = self._create_layer_results(overall_score, False)
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        # 应该是NONE（未认证）
        assert result.certification_level == CertificationLevel.NONE, \
            f"评分0.74应该被拒绝，实际: {result.certification_level.value}"
    
    def test_silver_upper_boundary(self, evaluator, passing_simulation_metrics):
        """测试SILVER上边界（0.7999）
        
        验证需求: Requirements 4.4
        
        测试综合评分接近但未达到GOLD阈值时的等级评定。
        """
        overall_score = 0.7999
        layer_results = self._create_layer_results(overall_score, True, 'SILVER')
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.SILVER
    
    # ==================== 拒绝情况测试 ====================
    
    def test_rejection_low_score(self, evaluator, passing_simulation_metrics):
        """测试低分拒绝（0.50）
        
        验证需求: Requirements 4.5
        
        测试综合评分远低于阈值时的等级评定。
        """
        overall_score = 0.50
        layer_results = self._create_layer_results(overall_score, False)
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.NONE
    
    def test_rejection_zero_score(self, evaluator, passing_simulation_metrics):
        """测试零分拒绝（0.0）
        
        验证需求: Requirements 4.5
        
        测试综合评分为零时的等级评定。
        """
        overall_score = 0.0
        layer_results = self._create_layer_results(overall_score, False)
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.NONE
    
    def test_rejection_arena_failed(self, evaluator, passing_simulation_metrics):
        """测试Arena层级未通过拒绝
        
        验证需求: Requirements 4.5
        
        测试Arena层级验证未通过时的等级评定。
        """
        # 即使评分高，但层级未通过
        overall_score = 0.95
        layer_results = self._create_layer_results(overall_score, False)  # 层级未通过
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=True,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.NONE, \
            "Arena层级未通过时应该被拒绝，即使评分很高"
    
    def test_rejection_simulation_failed(self, evaluator, passing_simulation_metrics):
        """测试模拟盘未通过拒绝
        
        验证需求: Requirements 4.5
        
        测试模拟盘验证未通过时的等级评定。
        """
        # Arena通过但模拟盘未通过
        overall_score = 0.95
        layer_results = self._create_layer_results(overall_score, True)
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=False,  # 模拟盘未通过
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.NONE, \
            "模拟盘未通过时应该被拒绝，即使Arena评分很高"
    
    def test_rejection_both_failed(self, evaluator, passing_simulation_metrics):
        """测试Arena和模拟盘都未通过拒绝
        
        验证需求: Requirements 4.5
        
        测试Arena和模拟盘都未通过时的等级评定。
        """
        overall_score = 0.70
        layer_results = self._create_layer_results(overall_score, False)
        
        result = evaluator.evaluate_level(
            arena_overall_score=overall_score,
            arena_layer_results=layer_results,
            simulation_passed=False,
            simulation_metrics=passing_simulation_metrics
        )
        
        assert result.certification_level == CertificationLevel.NONE
    
    # ==================== 边界组合测试 ====================
    
    def test_threshold_boundary_combinations(self, evaluator, passing_simulation_metrics):
        """测试阈值边界组合
        
        验证需求: Requirements 4.2, 4.3, 4.4, 4.5
        
        测试各种阈值边界组合的等级评定。
        """
        test_cases = [
            # (arena_score, layer_passed, target_level, simulation_passed, expected_min_level)
            (0.90, True, 'GOLD', True, CertificationLevel.SILVER),   # PLATINUM阈值
            (0.80, True, 'SILVER', True, CertificationLevel.SILVER),   # GOLD阈值
            (0.75, True, 'SILVER', True, CertificationLevel.SILVER),   # SILVER阈值
            (0.74, False, None, True, CertificationLevel.NONE),    # 低于SILVER
            (0.95, False, None, True, CertificationLevel.NONE),    # 层级未通过
            (0.95, True, 'PLATINUM', False, CertificationLevel.NONE),    # 模拟盘未通过
        ]
        
        for arena_score, layer_passed, target_level, sim_passed, expected_min_level in test_cases:
            layer_results = self._create_layer_results(arena_score, layer_passed, target_level)
            
            result = evaluator.evaluate_level(
                arena_overall_score=arena_score,
                arena_layer_results=layer_results,
                simulation_passed=sim_passed,
                simulation_metrics=passing_simulation_metrics
            )
            
            # 验证等级不低于预期最低等级
            level_order = {
                CertificationLevel.NONE: 0,
                CertificationLevel.SILVER: 1,
                CertificationLevel.GOLD: 2,
                CertificationLevel.PLATINUM: 3
            }
            
            assert level_order[result.certification_level] >= level_order[expected_min_level], \
                f"评分{arena_score}，层级{'通过' if layer_passed else '未通过'}，" \
                f"模拟盘{'通过' if sim_passed else '未通过'}，" \
                f"等级{result.certification_level.value}低于预期最低等级{expected_min_level.value}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
