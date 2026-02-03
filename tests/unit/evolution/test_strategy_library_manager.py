"""策略库集成管理器单元测试

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 策略库集成

测试覆盖：
- 认证策略注册
- 资金配置确定
- 仓位限制设置
- 策略移除
- 策略暂停/激活
- 资金权重更新
- 策略查询
- 历史记录
- 策略库导出

Author: MIA System
Version: 1.0.0
"""

import pytest
from datetime import datetime
import tempfile
import os
import json

from src.evolution.strategy_library_manager import (
    StrategyLibraryManager,
    StrategyStatus,
    StrategyMetadata,
    StrategyQueryResult
)
from src.evolution.z2h_data_models import (
    CertificationLevel,
    CertificationStatus,
    Z2HGeneCapsule,
    CertifiedStrategy,
    CapitalTier
)


class TestStrategyLibraryManager:
    """测试StrategyLibraryManager类"""
    
    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return StrategyLibraryManager()
    
    @pytest.fixture
    def sample_gene_capsule(self):
        """创建示例基因胶囊"""
        return Z2HGeneCapsule(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            strategy_type="momentum",
            source_factors=["factor_1", "factor_2"],
            creation_date=datetime.now(),
            certification_date=datetime.now(),
            certification_level=CertificationLevel.GOLD,
            arena_overall_score=0.85,
            arena_layer_results={
                "reality_track": {"score": 0.85, "passed": True},
                "hell_track": {"score": 0.82, "passed": True},
                "cross_market_track": {"score": 0.88, "passed": True},
                "stress_test": {"score": 0.80, "passed": True}
            },
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={
                "tier_1": {"sharpe": 1.5, "max_drawdown": 0.10},
                "tier_2": {"sharpe": 1.6, "max_drawdown": 0.12},
                "tier_3": {"sharpe": 1.4, "max_drawdown": 0.15},
                "tier_4": {"sharpe": 1.3, "max_drawdown": 0.18}
            },
            simulation_best_tier=CapitalTier.TIER_2,
            simulation_metrics={"sharpe": 1.5, "calmar": 10.0},
            max_allocation_ratio=0.15,
            recommended_capital_scale={"min": 10000.0, "max": 50000.0, "optimal": 30000.0},
            optimal_trade_size=5000.0,
            liquidity_requirements={"min_volume": 1000000},
            market_impact_analysis={"impact_ratio": 0.001},
            avg_holding_period_days=5.0,
            turnover_rate=2.0,
            avg_position_count=10,
            sector_distribution={"tech": 0.4, "finance": 0.3, "consumer": 0.3},
            market_cap_preference="mid_cap",
            var_95=0.02,
            expected_shortfall=0.03,
            max_drawdown=0.15,
            drawdown_duration_days=10,
            volatility=0.15,
            beta=1.0,
            market_correlation=0.7,
            bull_market_performance={"return": 0.20, "sharpe": 1.8},
            bear_market_performance={"return": -0.05, "sharpe": 0.5},
            sideways_market_performance={"return": 0.05, "sharpe": 1.0},
            high_volatility_performance={"return": 0.10, "sharpe": 1.2},
            low_volatility_performance={"return": 0.08, "sharpe": 1.5},
            market_adaptability_score=0.85,
            optimal_deployment_timing=["bull_market", "low_volatility"],
            risk_management_rules={"max_position": 0.10, "stop_loss": 0.05},
            monitoring_indicators=["sharpe_ratio", "drawdown"],
            exit_conditions=["sharpe < 1.0", "drawdown > 0.20"],
            portfolio_strategy_suggestions=["combine_with_mean_reversion"]
        )

    
    @pytest.fixture
    def sample_certified_strategy(self, sample_gene_capsule):
        """创建示例认证策略"""
        return CertifiedStrategy(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            certification_level=CertificationLevel.GOLD,
            gene_capsule=sample_gene_capsule,
            certification_date=datetime.now(),
            status=CertificationStatus.CERTIFIED
        )
    
    def test_initialization(self, manager):
        """测试初始化"""
        assert isinstance(manager.strategy_library, dict)
        assert len(manager.strategy_library) == 0
        assert isinstance(manager.registration_history, list)
        assert len(manager.registration_history) == 0
    
    def test_register_certified_strategy(self, manager, sample_certified_strategy):
        """测试注册认证策略"""
        result = manager.register_certified_strategy(sample_certified_strategy)
        
        assert result is True
        assert "strategy_001" in manager.strategy_library
        
        metadata = manager.strategy_library["strategy_001"]
        assert metadata.strategy_id == "strategy_001"
        assert metadata.strategy_name == "测试策略"
        assert metadata.certification_level == CertificationLevel.GOLD
        assert metadata.status == StrategyStatus.ACTIVE
        assert metadata.monitoring_enabled is True
        assert metadata.alert_enabled is True
        
        # 验证资金配置
        assert metadata.max_capital_ratio == 0.15  # GOLD级别
        assert metadata.capital_allocation_weight > 0
        assert metadata.capital_allocation_weight <= metadata.max_capital_ratio
        
        # 验证仓位限制
        assert metadata.max_position_size > 0
        assert metadata.max_total_position > 0
        
        # 验证注册历史
        assert len(manager.registration_history) == 1
        assert manager.registration_history[0]["action"] == "register"
    
    def test_register_duplicate_strategy(self, manager, sample_certified_strategy):
        """测试注册重复策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        with pytest.raises(ValueError, match="已存在于策略库中"):
            manager.register_certified_strategy(sample_certified_strategy)
    
    def test_capital_configuration_platinum(self, manager, sample_gene_capsule):
        """测试PLATINUM级别资金配置"""
        config = manager._determine_capital_configuration(
            CertificationLevel.PLATINUM,
            sample_gene_capsule
        )
        
        assert config["max_ratio"] == 0.20  # 20%
        assert config["weight"] == 0.10  # 从50%开始
        assert config["recommended_scale"] == 30000.0  # 从基因胶囊中获取
    
    def test_capital_configuration_gold(self, manager, sample_gene_capsule):
        """测试GOLD级别资金配置"""
        config = manager._determine_capital_configuration(
            CertificationLevel.GOLD,
            sample_gene_capsule
        )
        
        assert config["max_ratio"] == 0.15  # 15%
        assert config["weight"] == 0.075  # 从50%开始
    
    def test_capital_configuration_silver(self, manager, sample_gene_capsule):
        """测试SILVER级别资金配置"""
        config = manager._determine_capital_configuration(
            CertificationLevel.SILVER,
            sample_gene_capsule
        )
        
        assert config["max_ratio"] == 0.10  # 10%
        assert config["weight"] == 0.05  # 从50%开始
    
    def test_capital_configuration_missing_optimal(self, manager):
        """测试资金配置 - 缺少optimal字段"""
        # 创建一个没有optimal字段的基因胶囊
        gene_capsule = Z2HGeneCapsule(
            strategy_id="strategy_test",
            strategy_name="测试策略",
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
            recommended_capital_scale={"min": 10000.0, "max": 50000.0},  # 没有optimal
            optimal_trade_size=5000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=2.0,
            avg_position_count=10,
            sector_distribution={},
            market_cap_preference="mid_cap",
            var_95=0.02,
            expected_shortfall=0.03,
            max_drawdown=0.15,
            drawdown_duration_days=10,
            volatility=0.15,
            beta=1.0,
            market_correlation=0.7,
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
        
        config = manager._determine_capital_configuration(
            CertificationLevel.GOLD,
            gene_capsule
        )
        
        assert config["max_ratio"] == 0.15
        assert config["weight"] == 0.075
        assert config["recommended_scale"] == 100000.0  # 默认值

    
    def test_position_limits_platinum(self, manager, sample_gene_capsule):
        """测试PLATINUM级别仓位限制"""
        limits = manager._determine_position_limits(
            CertificationLevel.PLATINUM,
            sample_gene_capsule
        )
        
        assert limits["max_position_size"] == 0.10
        assert limits["max_total_position"] == 0.80
    
    def test_position_limits_gold(self, manager, sample_gene_capsule):
        """测试GOLD级别仓位限制"""
        limits = manager._determine_position_limits(
            CertificationLevel.GOLD,
            sample_gene_capsule
        )
        
        assert limits["max_position_size"] == 0.08
        assert limits["max_total_position"] == 0.70
    
    def test_position_limits_silver(self, manager, sample_gene_capsule):
        """测试SILVER级别仓位限制"""
        limits = manager._determine_position_limits(
            CertificationLevel.SILVER,
            sample_gene_capsule
        )
        
        assert limits["max_position_size"] == 0.05
        assert limits["max_total_position"] == 0.60
    
    def test_remove_revoked_strategy(self, manager, sample_certified_strategy):
        """测试移除被撤销的策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        result = manager.remove_revoked_strategy("strategy_001")
        
        assert result is True
        assert "strategy_001" not in manager.strategy_library
        
        # 验证移除历史
        remove_records = [
            h for h in manager.registration_history
            if h["action"] == "remove"
        ]
        assert len(remove_records) == 1
        assert remove_records[0]["reason"] == "certification_revoked"
    
    def test_remove_nonexistent_strategy(self, manager):
        """测试移除不存在的策略"""
        with pytest.raises(ValueError, match="不存在于策略库中"):
            manager.remove_revoked_strategy("nonexistent")
    
    def test_suspend_strategy(self, manager, sample_certified_strategy):
        """测试暂停策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        result = manager.suspend_strategy("strategy_001", reason="性能下降")
        
        assert result is True
        assert manager.strategy_library["strategy_001"].status == StrategyStatus.SUSPENDED
        
        # 验证暂停历史
        suspend_records = [
            h for h in manager.registration_history
            if h["action"] == "suspend"
        ]
        assert len(suspend_records) == 1
        assert suspend_records[0]["reason"] == "性能下降"
    
    def test_activate_strategy(self, manager, sample_certified_strategy):
        """测试激活策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        manager.suspend_strategy("strategy_001")
        
        result = manager.activate_strategy("strategy_001")
        
        assert result is True
        assert manager.strategy_library["strategy_001"].status == StrategyStatus.ACTIVE
        
        # 验证激活历史
        activate_records = [
            h for h in manager.registration_history
            if h["action"] == "activate"
        ]
        assert len(activate_records) == 1
    
    def test_suspend_nonexistent_strategy(self, manager):
        """测试暂停不存在的策略"""
        with pytest.raises(ValueError, match="不存在于策略库中"):
            manager.suspend_strategy("nonexistent")
    
    def test_activate_nonexistent_strategy(self, manager):
        """测试激活不存在的策略"""
        with pytest.raises(ValueError, match="不存在于策略库中"):
            manager.activate_strategy("nonexistent")

    
    def test_update_capital_weight(self, manager, sample_certified_strategy):
        """测试更新资金权重"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        result = manager.update_capital_weight("strategy_001", 0.12)
        
        assert result is True
        assert manager.strategy_library["strategy_001"].capital_allocation_weight == 0.12
    
    def test_update_capital_weight_exceeds_max(self, manager, sample_certified_strategy):
        """测试更新资金权重超过最大值"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        with pytest.raises(ValueError, match="超过最大比例"):
            manager.update_capital_weight("strategy_001", 0.25)  # 超过GOLD的15%
    
    def test_update_capital_weight_negative(self, manager, sample_certified_strategy):
        """测试更新负数权重"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        with pytest.raises(ValueError, match="不能为负数"):
            manager.update_capital_weight("strategy_001", -0.05)
    
    def test_update_capital_weight_nonexistent_strategy(self, manager):
        """测试更新不存在策略的权重"""
        with pytest.raises(ValueError, match="不存在于策略库中"):
            manager.update_capital_weight("nonexistent", 0.10)
    
    def test_get_strategy(self, manager, sample_certified_strategy):
        """测试获取策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        metadata = manager.get_strategy("strategy_001")
        
        assert metadata is not None
        assert metadata.strategy_id == "strategy_001"
    
    def test_get_nonexistent_strategy(self, manager):
        """测试获取不存在的策略"""
        metadata = manager.get_strategy("nonexistent")
        
        assert metadata is None
    
    def test_query_strategies_no_filter(self, manager, sample_certified_strategy):
        """测试查询策略 - 无过滤"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        result = manager.query_strategies()
        
        assert isinstance(result, StrategyQueryResult)
        assert result.total_count == 1
        assert len(result.strategies) == 1
        assert result.query_time is not None
    
    def test_query_strategies_by_level(self, manager):
        """测试按等级查询策略"""
        # 注册不同等级的策略
        for i, level in enumerate([CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER]):
            gene_capsule = self._create_gene_capsule(f"strategy_{i}", f"策略{i}", level)
            certified = self._create_certified_strategy(f"strategy_{i}", f"策略{i}", level, gene_capsule)
            manager.register_certified_strategy(certified)
        
        # 查询GOLD级别
        result = manager.query_strategies(certification_level=CertificationLevel.GOLD)
        
        assert result.total_count == 1
        assert result.strategies[0].certification_level == CertificationLevel.GOLD
    
    def _create_gene_capsule(self, strategy_id: str, strategy_name: str, level: CertificationLevel) -> Z2HGeneCapsule:
        """辅助方法：创建基因胶囊"""
        return Z2HGeneCapsule(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type="momentum",
            source_factors=["factor_1"],
            creation_date=datetime.now(),
            certification_date=datetime.now(),
            certification_level=level,
            arena_overall_score=0.85,
            arena_layer_results={},
            arena_passed_layers=4,
            arena_failed_layers=[],
            simulation_duration_days=30,
            simulation_tier_results={},
            simulation_best_tier=CapitalTier.TIER_2,
            simulation_metrics={},
            max_allocation_ratio=0.15,
            recommended_capital_scale={"min": 10000.0, "max": 50000.0, "optimal": 30000.0},
            optimal_trade_size=5000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=2.0,
            avg_position_count=10,
            sector_distribution={},
            market_cap_preference="mid_cap",
            var_95=0.02,
            expected_shortfall=0.03,
            max_drawdown=0.15,
            drawdown_duration_days=10,
            volatility=0.15,
            beta=1.0,
            market_correlation=0.7,
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
    
    def _create_certified_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        level: CertificationLevel,
        gene_capsule: Z2HGeneCapsule
    ) -> CertifiedStrategy:
        """辅助方法：创建认证策略"""
        return CertifiedStrategy(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            certification_level=level,
            gene_capsule=gene_capsule,
            certification_date=datetime.now(),
            status=CertificationStatus.CERTIFIED
        )

    
    def test_query_strategies_by_status(self, manager, sample_certified_strategy):
        """测试按状态查询策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        manager.suspend_strategy("strategy_001")
        
        # 查询暂停状态
        result = manager.query_strategies(status=StrategyStatus.SUSPENDED)
        
        assert result.total_count == 1
        assert result.strategies[0].status == StrategyStatus.SUSPENDED
    
    def test_query_strategies_by_min_weight(self, manager, sample_certified_strategy):
        """测试按最小权重查询策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        manager.update_capital_weight("strategy_001", 0.10)
        
        # 查询权重>=0.08的策略
        result = manager.query_strategies(min_weight=0.08)
        
        assert result.total_count == 1
        
        # 查询权重>=0.12的策略
        result = manager.query_strategies(min_weight=0.12)
        
        assert result.total_count == 0
    
    def test_get_active_strategies(self, manager, sample_certified_strategy):
        """测试获取活跃策略"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        active = manager.get_active_strategies()
        
        assert len(active) == 1
        assert active[0].status == StrategyStatus.ACTIVE
    
    def test_get_active_strategies_excludes_suspended(self, manager, sample_certified_strategy):
        """测试获取活跃策略排除暂停的"""
        manager.register_certified_strategy(sample_certified_strategy)
        manager.suspend_strategy("strategy_001")
        
        active = manager.get_active_strategies()
        
        assert len(active) == 0
    
    def test_get_total_capital_weight(self, manager):
        """测试获取总资金权重"""
        # 注册多个策略
        for i in range(3):
            gene_capsule = self._create_gene_capsule(f"strategy_{i}", f"策略{i}", CertificationLevel.GOLD)
            certified = self._create_certified_strategy(f"strategy_{i}", f"策略{i}", CertificationLevel.GOLD, gene_capsule)
            manager.register_certified_strategy(certified)
        
        total_weight = manager.get_total_capital_weight()
        
        assert total_weight > 0
        assert total_weight == pytest.approx(0.075 * 3, rel=1e-6)  # 每个GOLD策略0.075
    
    def test_get_strategy_count_by_level(self, manager):
        """测试获取按等级的策略数量"""
        # 注册不同等级的策略
        levels = [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.GOLD, CertificationLevel.SILVER]
        
        for i, level in enumerate(levels):
            gene_capsule = self._create_gene_capsule(f"strategy_{i}", f"策略{i}", level)
            certified = self._create_certified_strategy(f"strategy_{i}", f"策略{i}", level, gene_capsule)
            manager.register_certified_strategy(certified)
        
        distribution = manager.get_strategy_count_by_level()
        
        assert distribution["platinum"] == 1
        assert distribution["gold"] == 2
        assert distribution["silver"] == 1

    
    def test_get_registration_history_no_filter(self, manager, sample_certified_strategy):
        """测试获取注册历史 - 无过滤"""
        manager.register_certified_strategy(sample_certified_strategy)
        manager.suspend_strategy("strategy_001")
        
        history = manager.get_registration_history()
        
        assert len(history) == 2  # register + suspend
    
    def test_get_registration_history_by_strategy(self, manager, sample_certified_strategy):
        """测试按策略ID获取历史"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        history = manager.get_registration_history(strategy_id="strategy_001")
        
        assert len(history) == 1
        assert history[0]["strategy_id"] == "strategy_001"
    
    def test_get_registration_history_by_action(self, manager, sample_certified_strategy):
        """测试按操作类型获取历史"""
        manager.register_certified_strategy(sample_certified_strategy)
        manager.suspend_strategy("strategy_001")
        manager.activate_strategy("strategy_001")
        
        register_history = manager.get_registration_history(action="register")
        suspend_history = manager.get_registration_history(action="suspend")
        activate_history = manager.get_registration_history(action="activate")
        
        assert len(register_history) == 1
        assert len(suspend_history) == 1
        assert len(activate_history) == 1
    
    def test_export_strategy_library(self, manager, sample_certified_strategy):
        """测试导出策略库"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_path = f.name
        
        try:
            # 导出策略库
            manager.export_strategy_library(output_path)
            
            # 验证文件存在
            assert os.path.exists(output_path)
            
            # 读取并验证JSON内容
            with open(output_path, 'r', encoding='utf-8') as f:
                library_data = json.load(f)
            
            assert library_data["total_strategies"] == 1
            assert library_data["active_strategies"] == 1
            assert library_data["total_capital_weight"] > 0
            assert len(library_data["strategies"]) == 1
            
            strategy = library_data["strategies"][0]
            assert strategy["strategy_id"] == "strategy_001"
            assert strategy["certification_level"] == "gold"
            assert strategy["status"] == "active"
            
        finally:
            # 清理临时文件
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def test_export_strategy_library_invalid_path(self, manager, sample_certified_strategy):
        """测试导出到无效路径"""
        manager.register_certified_strategy(sample_certified_strategy)
        
        # 使用一个在所有平台上都无效的路径
        invalid_path = "Z:\\nonexistent_drive_12345\\invalid\\path\\library.json"
        
        with pytest.raises((IOError, OSError)):
            manager.export_strategy_library(invalid_path)


class TestDataModels:
    """测试数据模型"""
    
    def test_strategy_metadata_creation(self):
        """测试StrategyMetadata创建"""
        gene_capsule = Z2HGeneCapsule(
            strategy_id="strategy_001",
            strategy_name="测试策略",
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
            recommended_capital_scale={"min": 10000.0, "max": 50000.0, "optimal": 30000.0},
            optimal_trade_size=5000.0,
            liquidity_requirements={},
            market_impact_analysis={},
            avg_holding_period_days=5.0,
            turnover_rate=2.0,
            avg_position_count=10,
            sector_distribution={},
            market_cap_preference="mid_cap",
            var_95=0.02,
            expected_shortfall=0.03,
            max_drawdown=0.15,
            drawdown_duration_days=10,
            volatility=0.15,
            beta=1.0,
            market_correlation=0.7,
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
        
        metadata = StrategyMetadata(
            strategy_id="strategy_001",
            strategy_name="测试策略",
            certification_level=CertificationLevel.GOLD,
            gene_capsule=gene_capsule,
            registration_date=datetime.now(),
            status=StrategyStatus.ACTIVE,
            capital_allocation_weight=0.10,
            max_capital_ratio=0.15,
            recommended_capital_scale=1000000.0,
            max_position_size=0.08,
            max_total_position=0.70
        )
        
        assert metadata.strategy_id == "strategy_001"
        assert metadata.certification_level == CertificationLevel.GOLD
        assert metadata.status == StrategyStatus.ACTIVE
        assert metadata.capital_allocation_weight == 0.10
    
    def test_strategy_query_result_creation(self):
        """测试StrategyQueryResult创建"""
        result = StrategyQueryResult(
            total_count=5,
            strategies=[],
            query_time=datetime.now()
        )
        
        assert result.total_count == 5
        assert len(result.strategies) == 0
        assert result.query_time is not None
