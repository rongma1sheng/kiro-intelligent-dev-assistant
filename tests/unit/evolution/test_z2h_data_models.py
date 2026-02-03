"""Z2H数据模型单元测试

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

测试Z2H认证系统v2.0的核心数据模型：
- 枚举类型的有效性
- 数据类的创建和字段验证
- 数据类的相等性比较
- Z2HGeneCapsule的序列化和反序列化
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any

from src.evolution.z2h_data_models import (
    CertificationLevel,
    CertificationStatus,
    CapitalTier,
    Z2HGeneCapsule,
    CertificationEligibility,
    CapitalAllocationRules,
    TierSimulationResult,
    SimulationResult,
    CertificationResult,
    CertifiedStrategy
)


class TestCertificationLevel:
    """测试CertificationLevel枚举"""
    
    def test_certification_level_values(self):
        """测试认证等级枚举值"""
        assert CertificationLevel.PLATINUM.value == "platinum"
        assert CertificationLevel.GOLD.value == "gold"
        assert CertificationLevel.SILVER.value == "silver"
        assert CertificationLevel.NONE.value == "none"
    
    def test_certification_level_from_string(self):
        """测试从字符串创建认证等级"""
        assert CertificationLevel("platinum") == CertificationLevel.PLATINUM
        assert CertificationLevel("gold") == CertificationLevel.GOLD
        assert CertificationLevel("silver") == CertificationLevel.SILVER
        assert CertificationLevel("none") == CertificationLevel.NONE
    
    def test_certification_level_invalid_value(self):
        """测试无效的认证等级值"""
        with pytest.raises(ValueError):
            CertificationLevel("invalid")
    
    def test_certification_level_comparison(self):
        """测试认证等级比较"""
        assert CertificationLevel.PLATINUM == CertificationLevel.PLATINUM
        assert CertificationLevel.PLATINUM != CertificationLevel.GOLD


class TestCertificationStatus:
    """测试CertificationStatus枚举"""
    
    def test_certification_status_values(self):
        """测试认证状态枚举值"""
        assert CertificationStatus.NOT_CERTIFIED.value == "not_certified"
        assert CertificationStatus.IN_PROGRESS.value == "in_progress"
        assert CertificationStatus.CERTIFIED.value == "certified"
        assert CertificationStatus.REVOKED.value == "revoked"
        assert CertificationStatus.DOWNGRADED.value == "downgraded"
    
    def test_certification_status_from_string(self):
        """测试从字符串创建认证状态"""
        assert CertificationStatus("not_certified") == CertificationStatus.NOT_CERTIFIED
        assert CertificationStatus("in_progress") == CertificationStatus.IN_PROGRESS
        assert CertificationStatus("certified") == CertificationStatus.CERTIFIED
        assert CertificationStatus("revoked") == CertificationStatus.REVOKED
        assert CertificationStatus("downgraded") == CertificationStatus.DOWNGRADED
    
    def test_certification_status_invalid_value(self):
        """测试无效的认证状态值"""
        with pytest.raises(ValueError):
            CertificationStatus("invalid")


class TestCapitalTier:
    """测试CapitalTier枚举"""
    
    def test_capital_tier_values(self):
        """测试资金档位枚举值"""
        assert CapitalTier.TIER_1.value == "tier_1"
        assert CapitalTier.TIER_2.value == "tier_2"
        assert CapitalTier.TIER_3.value == "tier_3"
        assert CapitalTier.TIER_4.value == "tier_4"
    
    def test_capital_tier_from_string(self):
        """测试从字符串创建资金档位"""
        assert CapitalTier("tier_1") == CapitalTier.TIER_1
        assert CapitalTier("tier_2") == CapitalTier.TIER_2
        assert CapitalTier("tier_3") == CapitalTier.TIER_3
        assert CapitalTier("tier_4") == CapitalTier.TIER_4
    
    def test_capital_tier_invalid_value(self):
        """测试无效的资金档位值"""
        with pytest.raises(ValueError):
            CapitalTier("tier_5")


class TestZ2HGeneCapsule:
    """测试Z2HGeneCapsule数据类"""
    
    @pytest.fixture
    def sample_gene_capsule(self) -> Z2HGeneCapsule:
        """创建示例基因胶囊"""
        return Z2HGeneCapsule(
            # 基本信息
            strategy_id="strategy_001",
            strategy_name="Momentum Strategy Alpha",
            strategy_type="momentum",
            source_factors=["factor_1", "factor_2", "factor_3"],
            creation_date=datetime(2024, 1, 1, 10, 0, 0),
            certification_date=datetime(2024, 2, 1, 15, 30, 0),
            certification_level=CertificationLevel.PLATINUM,
            
            # Arena验证结果
            arena_overall_score=0.92,
            arena_layer_results={
                "layer_1": {"score": 0.95, "passed": True},
                "layer_2": {"score": 0.88, "passed": True},
                "layer_3": {"score": 0.85, "passed": True},
                "layer_4": {"score": 0.90, "passed": True}
            },
            arena_passed_layers=4,
            arena_failed_layers=[],
            
            # 模拟盘验证结果
            simulation_duration_days=30,
            simulation_tier_results={
                "tier_1": {"return": 0.15, "sharpe": 2.5},
                "tier_2": {"return": 0.18, "sharpe": 2.8},
                "tier_3": {"return": 0.16, "sharpe": 2.6},
                "tier_4": {"return": 0.14, "sharpe": 2.3}
            },
            simulation_best_tier=CapitalTier.TIER_2,
            simulation_metrics={
                "avg_return": 0.1575,
                "avg_sharpe": 2.55,
                "avg_win_rate": 0.65
            },
            
            # 资金配置规则
            max_allocation_ratio=0.20,
            recommended_capital_scale={
                "min": 10000.0,
                "optimal": 50000.0,
                "max": 500000.0
            },
            optimal_trade_size=5000.0,
            liquidity_requirements={
                "min_daily_volume": 1000000.0,
                "min_market_cap": 1000000000.0
            },
            market_impact_analysis={
                "estimated_slippage": 0.001,
                "max_position_size": 0.05
            },
            
            # 交易特征
            avg_holding_period_days=5.5,
            turnover_rate=3.5,
            avg_position_count=15,
            sector_distribution={
                "technology": 0.30,
                "finance": 0.25,
                "consumer": 0.20,
                "healthcare": 0.15,
                "other": 0.10
            },
            market_cap_preference="large_cap",
            
            # 风险分析
            var_95=0.025,
            expected_shortfall=0.035,
            max_drawdown=0.12,
            drawdown_duration_days=15,
            volatility=0.18,
            beta=0.85,
            market_correlation=0.65,
            
            # 市场环境表现
            bull_market_performance={"return": 0.25, "sharpe": 3.0},
            bear_market_performance={"return": -0.05, "sharpe": 1.5},
            sideways_market_performance={"return": 0.08, "sharpe": 2.0},
            high_volatility_performance={"return": 0.12, "sharpe": 2.2},
            low_volatility_performance={"return": 0.10, "sharpe": 2.5},
            market_adaptability_score=0.85,
            
            # 使用建议
            optimal_deployment_timing=["bull_market", "low_volatility"],
            risk_management_rules={
                "max_position_size": 0.05,
                "stop_loss": 0.02,
                "take_profit": 0.05
            },
            monitoring_indicators=["sharpe_ratio", "max_drawdown", "win_rate"],
            exit_conditions=["sharpe < 1.5", "drawdown > 0.15"],
            portfolio_strategy_suggestions=["pair_with_mean_reversion", "hedge_with_index"]
        )
    
    def test_gene_capsule_creation(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊创建"""
        assert sample_gene_capsule.strategy_id == "strategy_001"
        assert sample_gene_capsule.strategy_name == "Momentum Strategy Alpha"
        assert sample_gene_capsule.certification_level == CertificationLevel.PLATINUM
        assert sample_gene_capsule.arena_overall_score == 0.92
        assert sample_gene_capsule.simulation_best_tier == CapitalTier.TIER_2
    
    def test_gene_capsule_to_dict(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊转换为字典"""
        data = sample_gene_capsule.to_dict()
        
        # 验证基本字段
        assert data['strategy_id'] == "strategy_001"
        assert data['strategy_name'] == "Momentum Strategy Alpha"
        assert data['certification_level'] == "platinum"
        
        # 验证日期时间序列化
        assert isinstance(data['creation_date'], str)
        assert isinstance(data['certification_date'], str)
        
        # 验证枚举序列化
        assert data['simulation_best_tier'] == "tier_2"
        
        # 验证嵌套字典
        assert 'layer_1' in data['arena_layer_results']
        assert data['arena_layer_results']['layer_1']['score'] == 0.95
    
    def test_gene_capsule_from_dict(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试从字典创建基因胶囊"""
        data = sample_gene_capsule.to_dict()
        restored = Z2HGeneCapsule.from_dict(data)
        
        # 验证基本字段
        assert restored.strategy_id == sample_gene_capsule.strategy_id
        assert restored.strategy_name == sample_gene_capsule.strategy_name
        assert restored.certification_level == sample_gene_capsule.certification_level
        
        # 验证日期时间反序列化
        assert restored.creation_date == sample_gene_capsule.creation_date
        assert restored.certification_date == sample_gene_capsule.certification_date
        
        # 验证枚举反序列化
        assert restored.simulation_best_tier == sample_gene_capsule.simulation_best_tier
        
        # 验证数值字段
        assert restored.arena_overall_score == sample_gene_capsule.arena_overall_score
        assert restored.max_allocation_ratio == sample_gene_capsule.max_allocation_ratio
    
    def test_gene_capsule_serialization_round_trip(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊序列化往返
        
        验证: to_dict() -> from_dict() 产生等价对象
        """
        data = sample_gene_capsule.to_dict()
        restored = Z2HGeneCapsule.from_dict(data)
        
        # 验证所有关键字段
        assert restored.strategy_id == sample_gene_capsule.strategy_id
        assert restored.strategy_name == sample_gene_capsule.strategy_name
        assert restored.strategy_type == sample_gene_capsule.strategy_type
        assert restored.source_factors == sample_gene_capsule.source_factors
        assert restored.certification_level == sample_gene_capsule.certification_level
        assert restored.arena_overall_score == sample_gene_capsule.arena_overall_score
        assert restored.simulation_best_tier == sample_gene_capsule.simulation_best_tier
        assert restored.max_allocation_ratio == sample_gene_capsule.max_allocation_ratio
    
    def test_gene_capsule_from_dict_missing_field(self):
        """测试从缺少字段的字典创建基因胶囊"""
        incomplete_data = {
            'strategy_id': 'test_001',
            'strategy_name': 'Test Strategy'
            # 缺少其他必需字段
        }
        
        with pytest.raises(ValueError, match="缺少必需字段"):
            Z2HGeneCapsule.from_dict(incomplete_data)
    
    def test_gene_capsule_from_dict_invalid_type(self):
        """测试从包含无效类型的字典创建基因胶囊"""
        # 创建一个完整的数据字典，但certification_level是无效的
        sample_data = {
            'strategy_id': 'test_001',
            'strategy_name': 'Test Strategy',
            'strategy_type': 'momentum',
            'source_factors': ['factor_1'],
            'creation_date': '2024-01-01T10:00:00',
            'certification_date': '2024-02-01T15:30:00',
            'certification_level': 'invalid_level',  # 无效的认证等级
            'arena_overall_score': 0.85,
            'arena_layer_results': {},
            'arena_passed_layers': 4,
            'arena_failed_layers': [],
            'simulation_duration_days': 30,
            'simulation_tier_results': {},
            'simulation_best_tier': 'tier_2',
            'simulation_metrics': {},
            'max_allocation_ratio': 0.15,
            'recommended_capital_scale': {},
            'optimal_trade_size': 5000.0,
            'liquidity_requirements': {},
            'market_impact_analysis': {},
            'avg_holding_period_days': 5.0,
            'turnover_rate': 3.0,
            'avg_position_count': 15,
            'sector_distribution': {},
            'market_cap_preference': 'large_cap',
            'var_95': 0.025,
            'expected_shortfall': 0.035,
            'max_drawdown': 0.12,
            'drawdown_duration_days': 15,
            'volatility': 0.18,
            'beta': 0.85,
            'market_correlation': 0.65,
            'bull_market_performance': {},
            'bear_market_performance': {},
            'sideways_market_performance': {},
            'high_volatility_performance': {},
            'low_volatility_performance': {},
            'market_adaptability_score': 0.85,
            'optimal_deployment_timing': [],
            'risk_management_rules': {},
            'monitoring_indicators': [],
            'exit_conditions': [],
            'portfolio_strategy_suggestions': []
        }
        
        with pytest.raises(ValueError, match="数据格式不正确"):
            Z2HGeneCapsule.from_dict(sample_data)
    
    def test_gene_capsule_to_json(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊转换为JSON"""
        json_str = sample_gene_capsule.to_json()
        
        # 验证是JSON字符串
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # 验证可以解析为字典
        import json
        data = json.loads(json_str)
        assert isinstance(data, dict)
        assert data['strategy_id'] == "strategy_001"
    
    def test_gene_capsule_from_json(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试从JSON创建基因胶囊"""
        json_str = sample_gene_capsule.to_json()
        restored = Z2HGeneCapsule.from_json(json_str)
        
        # 验证基本字段
        assert restored.strategy_id == sample_gene_capsule.strategy_id
        assert restored.strategy_name == sample_gene_capsule.strategy_name
        assert restored.certification_level == sample_gene_capsule.certification_level
    
    def test_gene_capsule_json_round_trip(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊JSON序列化往返"""
        json_str = sample_gene_capsule.to_json()
        restored = Z2HGeneCapsule.from_json(json_str)
        
        # 验证所有关键字段
        assert restored.strategy_id == sample_gene_capsule.strategy_id
        assert restored.strategy_name == sample_gene_capsule.strategy_name
        assert restored.certification_level == sample_gene_capsule.certification_level
        assert restored.arena_overall_score == sample_gene_capsule.arena_overall_score
        assert restored.simulation_best_tier == sample_gene_capsule.simulation_best_tier
    
    def test_gene_capsule_from_json_invalid(self):
        """测试从无效JSON创建基因胶囊"""
        invalid_json = "{ invalid json }"
        
        with pytest.raises(ValueError, match="JSON解析失败"):
            Z2HGeneCapsule.from_json(invalid_json)
    
    def test_gene_capsule_validate_success(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证成功"""
        assert sample_gene_capsule.validate() is True
    
    def test_gene_capsule_validate_invalid_arena_score(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - Arena评分无效"""
        sample_gene_capsule.arena_overall_score = 1.5  # 超出范围
        
        with pytest.raises(ValueError, match="arena_overall_score必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_dates(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 日期无效"""
        # 认证日期早于创建日期
        sample_gene_capsule.certification_date = datetime(2023, 1, 1)
        sample_gene_capsule.creation_date = datetime(2024, 1, 1)
        
        with pytest.raises(ValueError, match="certification_date不能早于creation_date"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_allocation_ratio(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 资金配置比例无效"""
        sample_gene_capsule.max_allocation_ratio = 1.5  # 超出范围
        
        with pytest.raises(ValueError, match="max_allocation_ratio必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_negative_values(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 负值"""
        sample_gene_capsule.turnover_rate = -1.0  # 不能为负
        
        with pytest.raises(ValueError, match="turnover_rate不能为负数"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_empty_strategy_id(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 空策略ID"""
        sample_gene_capsule.strategy_id = ""
        
        with pytest.raises(ValueError, match="strategy_id必须是非空字符串"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_empty_strategy_name(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 空策略名称"""
        sample_gene_capsule.strategy_name = ""
        
        with pytest.raises(ValueError, match="strategy_name必须是非空字符串"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_empty_strategy_type(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 空策略类型"""
        sample_gene_capsule.strategy_type = ""
        
        with pytest.raises(ValueError, match="strategy_type必须是非空字符串"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_empty_source_factors(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 空因子列表"""
        sample_gene_capsule.source_factors = []
        
        with pytest.raises(ValueError, match="source_factors必须是非空列表"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_creation_date(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 无效创建日期"""
        sample_gene_capsule.creation_date = "not a datetime"
        
        with pytest.raises(ValueError, match="creation_date必须是datetime对象"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_certification_date(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 无效认证日期"""
        sample_gene_capsule.certification_date = "not a datetime"
        
        with pytest.raises(ValueError, match="certification_date必须是datetime对象"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_certification_level(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 无效认证等级"""
        sample_gene_capsule.certification_level = "not an enum"
        
        with pytest.raises(ValueError, match="certification_level必须是CertificationLevel枚举"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_arena_passed_layers(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - Arena通过层数无效"""
        sample_gene_capsule.arena_passed_layers = 5  # 超出范围
        
        with pytest.raises(ValueError, match="arena_passed_layers必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_simulation_duration(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 模拟盘天数无效"""
        sample_gene_capsule.simulation_duration_days = 0
        
        with pytest.raises(ValueError, match="simulation_duration_days必须大于0"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_simulation_tier(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 模拟盘档位无效"""
        sample_gene_capsule.simulation_best_tier = "not an enum"
        
        with pytest.raises(ValueError, match="simulation_best_tier必须是CapitalTier枚举"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_trade_size(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 交易规模无效"""
        sample_gene_capsule.optimal_trade_size = 0
        
        with pytest.raises(ValueError, match="optimal_trade_size必须大于0"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_holding_period(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 持仓天数无效"""
        sample_gene_capsule.avg_holding_period_days = 0
        
        with pytest.raises(ValueError, match="avg_holding_period_days必须大于0"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_position_count(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 持仓数量无效"""
        sample_gene_capsule.avg_position_count = 0
        
        with pytest.raises(ValueError, match="avg_position_count必须大于0"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_var(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - VaR无效"""
        sample_gene_capsule.var_95 = 1.5
        
        with pytest.raises(ValueError, match="var_95必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_expected_shortfall(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 预期损失无效"""
        sample_gene_capsule.expected_shortfall = 1.5
        
        with pytest.raises(ValueError, match="expected_shortfall必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_max_drawdown(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 最大回撤无效"""
        sample_gene_capsule.max_drawdown = 1.5
        
        with pytest.raises(ValueError, match="max_drawdown必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_negative_drawdown_duration(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 回撤持续天数为负"""
        sample_gene_capsule.drawdown_duration_days = -1
        
        with pytest.raises(ValueError, match="drawdown_duration_days不能为负数"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_negative_volatility(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 波动率为负"""
        sample_gene_capsule.volatility = -0.1
        
        with pytest.raises(ValueError, match="volatility不能为负数"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_validate_invalid_market_adaptability(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊验证失败 - 市场适应性评分无效"""
        sample_gene_capsule.market_adaptability_score = 1.5
        
        with pytest.raises(ValueError, match="market_adaptability_score必须在"):
            sample_gene_capsule.validate()
    
    def test_gene_capsule_to_json_error(self, sample_gene_capsule: Z2HGeneCapsule):
        """测试基因胶囊JSON序列化错误处理"""
        # 创建一个无法序列化的对象
        sample_gene_capsule.arena_layer_results = {
            'layer_1': object()  # 不可序列化的对象
        }
        
        with pytest.raises(ValueError, match="JSON序列化失败"):
            sample_gene_capsule.to_json()
    
    def test_gene_capsule_from_json_value_error(self):
        """测试基因胶囊从JSON反序列化时的ValueError"""
        # JSON有效但数据无效
        invalid_json = json.dumps({
            'strategy_id': 'test',
            # 缺少其他必需字段
        })
        
        with pytest.raises(ValueError, match="JSON反序列化失败"):
            Z2HGeneCapsule.from_json(invalid_json)


class TestCertificationEligibility:
    """测试CertificationEligibility数据类"""
    
    def test_eligibility_creation(self):
        """测试认证资格创建"""
        eligibility = CertificationEligibility(
            eligible=True,
            certification_level=CertificationLevel.GOLD,
            arena_score=0.85,
            simulation_score=0.82,
            passed_criteria=["criterion_1", "criterion_2", "criterion_3"],
            failed_criteria=[],
            failure_reasons=[]
        )
        
        assert eligibility.eligible is True
        assert eligibility.certification_level == CertificationLevel.GOLD
        assert eligibility.arena_score == 0.85
        assert eligibility.simulation_score == 0.82
        assert len(eligibility.passed_criteria) == 3
        assert len(eligibility.failed_criteria) == 0
    
    def test_eligibility_not_eligible(self):
        """测试不符合认证条件"""
        eligibility = CertificationEligibility(
            eligible=False,
            certification_level=CertificationLevel.NONE,
            arena_score=0.70,
            simulation_score=0.68,
            passed_criteria=["criterion_1"],
            failed_criteria=["criterion_2", "criterion_3"],
            failure_reasons=["Arena评分不达标", "模拟盘表现不佳"]
        )
        
        assert eligibility.eligible is False
        assert eligibility.certification_level == CertificationLevel.NONE
        assert len(eligibility.failed_criteria) == 2
        assert len(eligibility.failure_reasons) == 2


class TestCapitalAllocationRules:
    """测试CapitalAllocationRules数据类"""
    
    def test_capital_rules_creation(self):
        """测试资金配置规则创建"""
        rules = CapitalAllocationRules(
            max_allocation_ratio=0.20,
            min_capital=10000.0,
            max_capital=500000.0,
            optimal_capital=50000.0,
            recommended_tier=CapitalTier.TIER_2,
            position_limit_per_stock=0.05,
            sector_exposure_limit=0.30,
            max_leverage=1.5,
            liquidity_buffer=0.10
        )
        
        assert rules.max_allocation_ratio == 0.20
        assert rules.min_capital == 10000.0
        assert rules.max_capital == 500000.0
        assert rules.optimal_capital == 50000.0
        assert rules.recommended_tier == CapitalTier.TIER_2
        assert rules.position_limit_per_stock == 0.05
        assert rules.sector_exposure_limit == 0.30
        assert rules.max_leverage == 1.5
        assert rules.liquidity_buffer == 0.10
    
    def test_capital_rules_platinum_level(self):
        """测试白金级资金配置规则"""
        rules = CapitalAllocationRules(
            max_allocation_ratio=0.20,  # 白金级最大20%
            min_capital=50000.0,
            max_capital=5000000.0,
            optimal_capital=500000.0,
            recommended_tier=CapitalTier.TIER_4,
            position_limit_per_stock=0.10,
            sector_exposure_limit=0.40,
            max_leverage=2.0,
            liquidity_buffer=0.15
        )
        
        assert rules.max_allocation_ratio == 0.20
        assert rules.recommended_tier == CapitalTier.TIER_4


class TestTierSimulationResult:
    """测试TierSimulationResult数据类"""
    
    def test_tier_result_creation(self):
        """测试档位模拟结果创建"""
        result = TierSimulationResult(
            tier=CapitalTier.TIER_2,
            initial_capital=50000.0,
            final_capital=59000.0,
            total_return=0.18,
            sharpe_ratio=2.8,
            max_drawdown=0.10,
            win_rate=0.65,
            profit_factor=2.5,
            var_95=0.022,
            calmar_ratio=1.8,
            information_ratio=1.2,
            daily_pnl=[100.0, 150.0, -50.0, 200.0, 100.0],
            trades=[
                {"date": "2024-01-01", "symbol": "000001", "pnl": 100.0},
                {"date": "2024-01-02", "symbol": "000002", "pnl": 150.0}
            ]
        )
        
        assert result.tier == CapitalTier.TIER_2
        assert result.initial_capital == 50000.0
        assert result.final_capital == 59000.0
        assert result.total_return == 0.18
        assert result.sharpe_ratio == 2.8
        assert len(result.daily_pnl) == 5
        assert len(result.trades) == 2


class TestSimulationResult:
    """测试SimulationResult数据类"""
    
    @pytest.fixture
    def sample_tier_result(self) -> TierSimulationResult:
        """创建示例档位结果"""
        return TierSimulationResult(
            tier=CapitalTier.TIER_2,
            initial_capital=50000.0,
            final_capital=59000.0,
            total_return=0.18,
            sharpe_ratio=2.8,
            max_drawdown=0.10,
            win_rate=0.65,
            profit_factor=2.5,
            var_95=0.022,
            calmar_ratio=1.8,
            information_ratio=1.2,
            daily_pnl=[100.0, 150.0, -50.0, 200.0, 100.0],
            trades=[]
        )
    
    def test_simulation_result_creation(self, sample_tier_result: TierSimulationResult):
        """测试模拟盘结果创建"""
        result = SimulationResult(
            passed=True,
            duration_days=30,
            tier_results={"tier_2": sample_tier_result},
            best_tier=CapitalTier.TIER_2,
            overall_metrics={
                "avg_return": 0.18,
                "avg_sharpe": 2.8,
                "avg_win_rate": 0.65
            },
            risk_metrics={
                "max_drawdown": 0.10,
                "var_95": 0.022,
                "volatility": 0.15
            },
            market_environment_performance={
                "bull_market": {"return": 0.25, "sharpe": 3.0},
                "bear_market": {"return": -0.05, "sharpe": 1.5}
            },
            passed_criteria_count=10,
            failed_criteria=[]
        )
        
        assert result.passed is True
        assert result.duration_days == 30
        assert result.best_tier == CapitalTier.TIER_2
        assert len(result.tier_results) == 1
        assert result.passed_criteria_count == 10
        assert len(result.failed_criteria) == 0
    
    def test_simulation_result_failed(self):
        """测试模拟盘验证失败"""
        result = SimulationResult(
            passed=False,
            duration_days=30,
            tier_results={},
            best_tier=CapitalTier.TIER_1,
            overall_metrics={},
            risk_metrics={},
            market_environment_performance={},
            passed_criteria_count=7,
            failed_criteria=["月收益<5%", "夏普比率<1.2", "胜率<55%"]
        )
        
        assert result.passed is False
        assert result.passed_criteria_count == 7
        assert len(result.failed_criteria) == 3


class TestCertificationResult:
    """测试CertificationResult数据类"""
    
    def test_certification_result_success(self):
        """测试认证成功"""
        gene_capsule = Z2HGeneCapsule(
            strategy_id="strategy_001",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            source_factors=["factor_1"],
            creation_date=datetime.now(),
            certification_date=datetime.now(),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results={},
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={},
            simulation_best_tier=CapitalTier.TIER_2,
            simulation_metrics={},
            max_allocation_ratio=0.15,
            recommended_capital_scale={},
            optimal_trade_size=5000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=3.0,
            avg_position_count=15,
            sector_distribution={},
            market_cap_preference="large_cap",
            var_95=0.025,
            expected_shortfall=0.035,
            max_drawdown=0.12,
            drawdown_duration_days=15,
            volatility=0.18,
            beta=0.85,
            market_correlation=0.65,
            bull_market_performance={},
            bear_market_performance={},
            sideways_market_performance={},
            high_volatility_performance={},
            low_volatility_performance={},
            market_adaptability_score=0.85,
            optimal_deployment_timing=[],
            risk_management_rules={},
            monitoring_indicators=[],
            exit_conditions=[],
            portfolio_strategy_suggestions=[]
        )
        
        result = CertificationResult(
            passed=True,
            strategy_id="strategy_001",
            certification_level=CertificationLevel.GOLD,
            gene_capsule=gene_capsule,
            failed_stage=None,
            failure_reason=None,
            certification_date=datetime.now()
        )
        
        assert result.passed is True
        assert result.strategy_id == "strategy_001"
        assert result.certification_level == CertificationLevel.GOLD
        assert result.gene_capsule is not None
        assert result.failed_stage is None
        assert result.failure_reason is None
    
    def test_certification_result_failure(self):
        """测试认证失败"""
        result = CertificationResult(
            passed=False,
            strategy_id="strategy_002",
            certification_level=None,
            gene_capsule=None,
            failed_stage="Stage 3: Sparta Arena Evaluation",
            failure_reason="Arena综合评分不达标: 0.70 < 0.75",
            certification_date=None
        )
        
        assert result.passed is False
        assert result.strategy_id == "strategy_002"
        assert result.certification_level is None
        assert result.gene_capsule is None
        assert result.failed_stage == "Stage 3: Sparta Arena Evaluation"
        assert "Arena综合评分不达标" in result.failure_reason


class TestCertifiedStrategy:
    """测试CertifiedStrategy数据类"""
    
    def test_certified_strategy_creation(self):
        """测试已认证策略创建"""
        gene_capsule = Z2HGeneCapsule(
            strategy_id="strategy_001",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            source_factors=["factor_1"],
            creation_date=datetime.now(),
            certification_date=datetime.now(),
            certification_level=CertificationLevel.PLATINUM,
            arena_overall_score=0.92,
            arena_layer_results={},
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={},
            simulation_best_tier=CapitalTier.TIER_3,
            simulation_metrics={},
            max_allocation_ratio=0.20,
            recommended_capital_scale={},
            optimal_trade_size=10000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=3.0,
            avg_position_count=15,
            sector_distribution={},
            market_cap_preference="large_cap",
            var_95=0.025,
            expected_shortfall=0.035,
            max_drawdown=0.10,
            drawdown_duration_days=12,
            volatility=0.16,
            beta=0.80,
            market_correlation=0.60,
            bull_market_performance={},
            bear_market_performance={},
            sideways_market_performance={},
            high_volatility_performance={},
            low_volatility_performance={},
            market_adaptability_score=0.90,
            optimal_deployment_timing=[],
            risk_management_rules={},
            monitoring_indicators=[],
            exit_conditions=[],
            portfolio_strategy_suggestions=[]
        )
        
        certified = CertifiedStrategy(
            strategy_id="strategy_001",
            strategy_name="Test Strategy",
            certification_level=CertificationLevel.PLATINUM,
            gene_capsule=gene_capsule,
            certification_date=datetime(2024, 2, 1),
            status=CertificationStatus.CERTIFIED,
            last_review_date=datetime(2024, 3, 1),
            next_review_date=datetime(2024, 4, 1)
        )
        
        assert certified.strategy_id == "strategy_001"
        assert certified.certification_level == CertificationLevel.PLATINUM
        assert certified.status == CertificationStatus.CERTIFIED
        assert certified.last_review_date is not None
        assert certified.next_review_date is not None
    
    def test_certified_strategy_status_transitions(self):
        """测试认证状态转换"""
        gene_capsule = Z2HGeneCapsule(
            strategy_id="strategy_001",
            strategy_name="Test Strategy",
            strategy_type="momentum",
            source_factors=["factor_1"],
            creation_date=datetime.now(),
            certification_date=datetime.now(),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results={},
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={},
            simulation_best_tier=CapitalTier.TIER_2,
            simulation_metrics={},
            max_allocation_ratio=0.15,
            recommended_capital_scale={},
            optimal_trade_size=5000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=3.0,
            avg_position_count=15,
            sector_distribution={},
            market_cap_preference="large_cap",
            var_95=0.025,
            expected_shortfall=0.035,
            max_drawdown=0.12,
            drawdown_duration_days=15,
            volatility=0.18,
            beta=0.85,
            market_correlation=0.65,
            bull_market_performance={},
            bear_market_performance={},
            sideways_market_performance={},
            high_volatility_performance={},
            low_volatility_performance={},
            market_adaptability_score=0.85,
            optimal_deployment_timing=[],
            risk_management_rules={},
            monitoring_indicators=[],
            exit_conditions=[],
            portfolio_strategy_suggestions=[]
        )
        
        # 初始状态：已认证
        certified = CertifiedStrategy(
            strategy_id="strategy_001",
            strategy_name="Test Strategy",
            certification_level=CertificationLevel.GOLD,
            gene_capsule=gene_capsule,
            certification_date=datetime.now(),
            status=CertificationStatus.CERTIFIED
        )
        assert certified.status == CertificationStatus.CERTIFIED
        
        # 状态转换：降级
        certified.status = CertificationStatus.DOWNGRADED
        assert certified.status == CertificationStatus.DOWNGRADED
        
        # 状态转换：撤销
        certified.status = CertificationStatus.REVOKED
        assert certified.status == CertificationStatus.REVOKED
