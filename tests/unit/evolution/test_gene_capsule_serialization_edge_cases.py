"""基因胶囊序列化边界条件单元测试

白皮书依据: 第四章 4.3.1 Z2H认证系统
"""

import pytest
from datetime import datetime
import json

from src.evolution.z2h_data_models import (
    Z2HGeneCapsule,
    CertificationLevel,
    CapitalTier
)


def create_test_capsule(**overrides) -> Z2HGeneCapsule:
    defaults = {
        'strategy_id': 'test_strategy_001',
        'strategy_name': 'Test Strategy',
        'strategy_type': 'momentum',
        'source_factors': ['factor_1', 'factor_2'],
        'creation_date': datetime.now(),
        'certification_date': datetime.now(),
        'certification_level': CertificationLevel.GOLD,
        'arena_overall_score': 0.85,
        'arena_layer_results': {'layer_1': {'score': 0.90}},
        'arena_passed_layers': 4,
        'arena_failed_layers': [],
        'simulation_duration_days': 30,
        'simulation_tier_results': {'tier_1': {'return': 0.10}},
        'simulation_best_tier': CapitalTier.TIER_2,
        'simulation_metrics': {'avg_return': 0.07},
        'max_allocation_ratio': 0.20,
        'recommended_capital_scale': {'min': 10000, 'max': 100000},
        'optimal_trade_size': 5000.0,
        'liquidity_requirements': {'min_volume': 1000000},
        'market_impact_analysis': {'impact_ratio': 0.001},
        'avg_holding_period_days': 5.0,
        'turnover_rate': 2.0,
        'avg_position_count': 10,
        'sector_distribution': {'tech': 0.3, 'finance': 0.2},
        'market_cap_preference': 'mid_cap',
        'var_95': 0.03,
        'expected_shortfall': 0.04,
        'max_drawdown': 0.10,
        'drawdown_duration_days': 5,
        'volatility': 0.15,
        'beta': 0.8,
        'market_correlation': 0.5,
        'bull_market_performance': {'return': 0.15, 'sharpe': 2.5},
        'bear_market_performance': {'return': -0.02, 'sharpe': 0.5},
        'sideways_market_performance': {'return': 0.05, 'sharpe': 1.0},
        'high_volatility_performance': {'return': 0.08, 'sharpe': 1.2},
        'low_volatility_performance': {'return': 0.06, 'sharpe': 1.5},
        'market_adaptability_score': 0.75,
        'optimal_deployment_timing': ['bull_market', 'low_volatility'],
        'risk_management_rules': {'stop_loss': 0.05, 'take_profit': 0.10},
        'monitoring_indicators': ['sharpe_ratio', 'max_drawdown'],
        'exit_conditions': ['drawdown > 15%', 'sharpe < 1.0'],
        'portfolio_strategy_suggestions': ['diversify', 'hedge'],
        'version': '2.0',
        'created_by': 'Z2HCertificationV2'
    }
    defaults.update(overrides)
    return Z2HGeneCapsule(**defaults)


class TestGeneCapsuleSerializationEdgeCases:

    def test_empty_fields_handling(self):
        capsule = create_test_capsule(
            strategy_id="",
            strategy_name="",
            strategy_type="",
            source_factors=[],
            arena_layer_results={},
            arena_failed_layers=[],
            simulation_tier_results={},
            simulation_metrics={},
            recommended_capital_scale={},
            liquidity_requirements={},
            market_impact_analysis={},
            sector_distribution={},
            bull_market_performance={},
            bear_market_performance={},
            sideways_market_performance={},
            high_volatility_performance={},
            low_volatility_performance={},
            optimal_deployment_timing=[],
            risk_management_rules={},
            monitoring_indicators=[],
            exit_conditions=[],
            portfolio_strategy_suggestions=[]
        )
        serialized = capsule.to_dict()
        assert serialized['strategy_id'] == ""
        assert serialized['source_factors'] == []
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        assert deserialized.strategy_id == ""
        assert deserialized.source_factors == []

    def test_none_values_handling(self):
        capsule = create_test_capsule(strategy_id="test_001")
        serialized = capsule.to_dict()
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        assert deserialized is not None
        assert deserialized.strategy_id == "test_001"

    def test_special_characters_in_strings(self):
        special_chars = "test\nline\ttab"
        capsule = create_test_capsule(
            strategy_id="test_special_chars",
            strategy_name=special_chars,
            arena_layer_results={'note': special_chars}
        )
        serialized = capsule.to_dict()
        json_str = json.dumps(serialized, ensure_ascii=False, default=str)
        parsed = json.loads(json_str)
        deserialized = Z2HGeneCapsule.from_dict(parsed)
        assert deserialized.strategy_name == special_chars
        assert deserialized.arena_layer_results['note'] == special_chars

    def test_large_data_volume(self):
        large_arena_results = {f'metric_{i}': float(i) for i in range(1000)}
        large_factors = [f'factor_{i}' for i in range(100)]
        capsule = create_test_capsule(
            strategy_id="test_large_data",
            source_factors=large_factors,
            arena_layer_results=large_arena_results
        )
        serialized = capsule.to_dict()
        json_str = json.dumps(serialized, ensure_ascii=False, default=str)
        json_size_mb = len(json_str.encode('utf-8')) / (1024 * 1024)
        assert json_size_mb < 10
        parsed = json.loads(json_str)
        deserialized = Z2HGeneCapsule.from_dict(parsed)
        assert len(deserialized.arena_layer_results) == 1000
        assert len(deserialized.source_factors) == 100

    def test_extreme_numeric_values(self):
        capsule = create_test_capsule(
            strategy_id="test_extreme_values",
            arena_overall_score=0.0,
            market_adaptability_score=1.0,
            arena_layer_results={'zero': 0.0, 'large': 1e5},
            var_95=0.0,
            max_drawdown=0.0
        )
        serialized = capsule.to_dict()
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        assert deserialized.arena_overall_score == 0.0
        assert deserialized.market_adaptability_score == 1.0

    def test_date_edge_cases(self):
        past_date = datetime(2020, 1, 1, 0, 0, 0)
        future_date = datetime(2030, 12, 31, 23, 59, 59)
        capsule = create_test_capsule(
            strategy_id="test_dates",
            creation_date=past_date,
            certification_date=future_date
        )
        serialized = capsule.to_dict()
        assert isinstance(serialized['creation_date'], str)
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        assert deserialized.creation_date.date() == past_date.date()

    def test_nested_dict_structures(self):
        nested_data = {'level1': {'level2': {'value': 123}}}
        capsule = create_test_capsule(
            strategy_id="test_nested",
            arena_layer_results=nested_data
        )
        serialized = capsule.to_dict()
        deserialized = Z2HGeneCapsule.from_dict(serialized)
        assert deserialized.arena_layer_results['level1']['level2']['value'] == 123

    def test_enum_serialization_consistency(self):
        for level in CertificationLevel:
            capsule = create_test_capsule(
                strategy_id=f"test_{level.value}",
                certification_level=level
            )
            serialized = capsule.to_dict()
            deserialized = Z2HGeneCapsule.from_dict(serialized)
            assert deserialized.certification_level == level
        for tier in CapitalTier:
            capsule = create_test_capsule(
                strategy_id=f"test_{tier.value}",
                simulation_best_tier=tier
            )
            serialized = capsule.to_dict()
            deserialized = Z2HGeneCapsule.from_dict(serialized)
            assert deserialized.simulation_best_tier == tier
