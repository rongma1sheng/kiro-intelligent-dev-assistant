"""认证配置管理器单元测试

测试CertificationConfigManager的所有功能。
"""

import pytest
from datetime import datetime, timedelta
from src.evolution.certification_config_manager import (
    CertificationConfigManager,
    ArenaWeightConfig,
    ValidationThresholdConfig,
    CertificationLevelStandard,
    CapitalAllocationConfig,
    SimulationStandard,
    MarketType,
    StrategyType,
    ConfigChangeRecord
)


class TestCertificationConfigManager:
    """测试CertificationConfigManager类"""
    
    @pytest.fixture
    def manager(self):
        """创建配置管理器实例"""
        return CertificationConfigManager()
    
    def test_initialization(self, manager):
        """测试初始化"""
        assert manager.arena_weights is not None
        assert manager.validation_thresholds is not None
        assert len(manager.certification_standards) == 3
        assert manager.capital_allocation is not None
        assert manager.simulation_standards is not None
        assert len(manager.market_configs) > 0
        assert len(manager.strategy_configs) > 0
        assert len(manager.change_history) == 0
    
    def test_arena_weight_config_validation(self):
        """测试Arena权重配置验证"""
        # 正常情况
        config = ArenaWeightConfig(
            layer1_weight=0.35,
            layer2_weight=0.25,
            layer3_weight=0.20,
            layer4_weight=0.20
        )
        assert config.layer1_weight == 0.35
        
        # 权重总和不为1.0应该抛出异常
        with pytest.raises(ValueError, match="权重总和必须为1.0"):
            ArenaWeightConfig(
                layer1_weight=0.30,
                layer2_weight=0.30,
                layer3_weight=0.30,
                layer4_weight=0.30
            )
    
    def test_update_arena_weights(self, manager):
        """测试更新Arena权重"""
        # 更新部分权重
        new_config = manager.update_arena_weights(
            layer1_weight=0.40,
            layer2_weight=0.30,
            layer3_weight=0.15,
            layer4_weight=0.15,
            changed_by="admin",
            reason="调整权重"
        )
        
        assert new_config.layer1_weight == 0.40
        assert new_config.layer2_weight == 0.30
        assert len(manager.change_history) == 1
        assert manager.change_history[0].config_type == "arena_weights"
    
    def test_update_arena_weights_invalid_sum(self, manager):
        """测试更新Arena权重（总和不为1.0）"""
        with pytest.raises(ValueError, match="权重总和必须为1.0"):
            manager.update_arena_weights(
                layer1_weight=0.50,
                layer2_weight=0.30,
                layer3_weight=0.20,
                layer4_weight=0.20
            )
        
        # 验证配置未被修改
        assert manager.arena_weights.layer1_weight == 0.35
    
    def test_update_validation_thresholds(self, manager):
        """测试更新验证阈值"""
        new_config = manager.update_validation_thresholds(
            layer1_threshold=0.80,
            overall_threshold=0.78,
            changed_by="admin",
            reason="提高标准"
        )
        
        assert new_config.layer1_threshold == 0.80
        assert new_config.overall_threshold == 0.78
        assert len(manager.change_history) == 1
    
    def test_update_certification_standard(self, manager):
        """测试更新认证等级标准"""
        new_standard = CertificationLevelStandard(
            min_arena_score=0.92,
            min_layer1_score=0.96,
            min_layer2_score=0.88,
            min_layer3_score=0.82,
            min_layer4_score=0.88,
            min_simulation_sharpe=2.8,
            max_simulation_drawdown=0.08,
            min_simulation_win_rate=0.68
        )
        
        updated = manager.update_certification_standard(
            level="platinum",
            standard=new_standard,
            changed_by="admin",
            reason="提高白金级标准"
        )
        
        assert updated.min_arena_score == 0.92
        assert manager.certification_standards['platinum'].min_arena_score == 0.92
        assert len(manager.change_history) == 1
    
    def test_update_certification_standard_invalid_level(self, manager):
        """测试更新不存在的认证等级"""
        standard = CertificationLevelStandard(
            min_arena_score=0.90,
            min_layer1_score=0.95,
            min_layer2_score=0.85,
            min_layer3_score=0.80,
            min_layer4_score=0.85,
            min_simulation_sharpe=2.5,
            max_simulation_drawdown=0.10,
            min_simulation_win_rate=0.65
        )
        
        with pytest.raises(ValueError, match="未知的认证等级"):
            manager.update_certification_standard(
                level="diamond",
                standard=standard
            )
    
    def test_update_capital_allocation(self, manager):
        """测试更新资金配置规则"""
        new_config = manager.update_capital_allocation(
            platinum_max_ratio=0.25,
            gold_max_ratio=0.18,
            position_limit_per_stock=0.08,
            changed_by="admin",
            reason="放宽限制"
        )
        
        assert new_config.platinum_max_ratio == 0.25
        assert new_config.gold_max_ratio == 0.18
        assert new_config.position_limit_per_stock == 0.08
        assert len(manager.change_history) == 1
    
    def test_update_simulation_standards(self, manager):
        """测试更新模拟盘达标标准"""
        new_standards = {
            'min_monthly_return': 0.08,
            'min_sharpe_ratio': 1.5,
            'max_drawdown': 0.12
        }
        
        updated = manager.update_simulation_standards(
            standards=new_standards,
            changed_by="admin",
            reason="调整标准"
        )
        
        assert updated.min_monthly_return == 0.08
        assert updated.min_sharpe_ratio == 1.5
        assert updated.max_drawdown == 0.12
        assert len(manager.change_history) == 1
    
    def test_update_market_config(self, manager):
        """测试更新市场类型配置"""
        new_config = {
            'trading_hours': '09:00-15:30',
            'min_liquidity': 2000000
        }
        
        updated = manager.update_market_config(
            market_type=MarketType.A_STOCK,
            config=new_config,
            changed_by="admin",
            reason="调整市场配置"
        )
        
        assert updated['trading_hours'] == '09:00-15:30'
        assert updated['min_liquidity'] == 2000000
        assert len(manager.change_history) == 1
    
    def test_update_market_config_new_market(self, manager):
        """测试更新新市场类型配置"""
        new_config = {
            'trading_hours': '00:00-24:00',
            'min_liquidity': 10000000
        }
        
        updated = manager.update_market_config(
            market_type=MarketType.CRYPTO,
            config=new_config,
            changed_by="admin",
            reason="添加加密货币市场"
        )
        
        assert MarketType.CRYPTO in manager.market_configs
        assert updated['trading_hours'] == '00:00-24:00'
    
    def test_update_strategy_config(self, manager):
        """测试更新策略类型配置"""
        new_config = {
            'min_holding_period': 10,
            'max_turnover': 2.0
        }
        
        updated = manager.update_strategy_config(
            strategy_type=StrategyType.MOMENTUM,
            config=new_config,
            changed_by="admin",
            reason="调整动量策略配置"
        )
        
        assert updated['min_holding_period'] == 10
        assert updated['max_turnover'] == 2.0
        assert len(manager.change_history) == 1
    
    def test_update_strategy_config_new_strategy(self, manager):
        """测试更新新策略类型配置"""
        new_config = {
            'min_holding_period': 0.5,
            'max_turnover': 20.0
        }
        
        updated = manager.update_strategy_config(
            strategy_type=StrategyType.EVENT_DRIVEN,
            config=new_config,
            changed_by="admin",
            reason="添加事件驱动策略"
        )
        
        assert StrategyType.EVENT_DRIVEN in manager.strategy_configs
        assert updated['min_holding_period'] == 0.5
    
    def test_get_change_history_all(self, manager):
        """测试查询所有变更历史"""
        # 执行多次配置更新
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15)
        manager.update_validation_thresholds(layer1_threshold=0.80)
        manager.update_capital_allocation(platinum_max_ratio=0.25)
        
        history = manager.get_change_history()
        assert len(history) == 3
    
    def test_get_change_history_by_config_type(self, manager):
        """测试按配置类型查询变更历史"""
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15)
        manager.update_validation_thresholds(layer1_threshold=0.80)
        manager.update_arena_weights(layer1_weight=0.38, layer2_weight=0.32, layer3_weight=0.15, layer4_weight=0.15)
        
        history = manager.get_change_history(config_type="arena_weights")
        assert len(history) == 2
        assert all(r.config_type == "arena_weights" for r in history)
    
    def test_get_change_history_by_date_range(self, manager):
        """测试按日期范围查询变更历史"""
        now = datetime.now()
        
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15)
        
        # 查询今天的变更
        history = manager.get_change_history(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1)
        )
        assert len(history) == 1
        
        # 查询未来的变更（应该为空）
        history = manager.get_change_history(
            start_date=now + timedelta(days=1)
        )
        assert len(history) == 0
    
    def test_get_change_history_by_changed_by(self, manager):
        """测试按变更人查询变更历史"""
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15, changed_by="admin")
        manager.update_validation_thresholds(layer1_threshold=0.80, changed_by="user")
        manager.update_capital_allocation(platinum_max_ratio=0.25, changed_by="admin")
        
        history = manager.get_change_history(changed_by="admin")
        assert len(history) == 2
        assert all(r.changed_by == "admin" for r in history)
    
    def test_get_change_history_combined_filters(self, manager):
        """测试组合过滤条件查询变更历史"""
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15, changed_by="admin")
        manager.update_validation_thresholds(layer1_threshold=0.80, changed_by="admin")
        manager.update_arena_weights(layer1_weight=0.38, layer2_weight=0.32, layer3_weight=0.15, layer4_weight=0.15, changed_by="user")
        
        history = manager.get_change_history(
            config_type="arena_weights",
            changed_by="admin"
        )
        assert len(history) == 1
        assert history[0].config_type == "arena_weights"
        assert history[0].changed_by == "admin"
    
    def test_export_config(self, manager):
        """测试导出配置"""
        config = manager.export_config()
        
        assert 'arena_weights' in config
        assert 'validation_thresholds' in config
        assert 'certification_standards' in config
        assert 'capital_allocation' in config
        assert 'simulation_standards' in config
        assert 'market_configs' in config
        assert 'strategy_configs' in config
        
        # 验证数据结构
        assert config['arena_weights']['layer1_weight'] == 0.35
        assert 'platinum' in config['certification_standards']
        assert 'a_stock' in config['market_configs']
    
    def test_import_config(self, manager):
        """测试导入配置"""
        # 准备配置数据
        config = {
            'arena_weights': {
                'layer1_weight': 0.40,
                'layer2_weight': 0.30,
                'layer3_weight': 0.15,
                'layer4_weight': 0.15
            },
            'validation_thresholds': {
                'layer1_threshold': 0.80,
                'layer2_threshold': 0.75,
                'layer3_threshold': 0.70,
                'layer4_threshold': 0.75,
                'overall_threshold': 0.78
            }
        }
        
        # 导入配置
        manager.import_config(config, changed_by="admin", reason="批量导入")
        
        # 验证配置已更新
        assert manager.arena_weights.layer1_weight == 0.40
        assert manager.validation_thresholds.layer1_threshold == 0.80
        assert len(manager.change_history) == 1
        assert manager.change_history[0].config_type == "全局配置"
    
    def test_change_record_generation(self, manager):
        """测试变更记录生成"""
        manager.update_arena_weights(
            layer1_weight=0.40,
            layer2_weight=0.30,
            layer3_weight=0.15,
            layer4_weight=0.15,
            changed_by="admin",
            reason="测试变更"
        )
        
        record = manager.change_history[0]
        
        assert record.change_id.startswith("CONFIG-")
        assert record.config_type == "arena_weights"
        assert record.changed_by == "admin"
        assert record.reason == "测试变更"
        assert isinstance(record.changed_at, datetime)
        assert isinstance(record.effective_at, datetime)
        assert record.old_value is not None
        assert record.new_value is not None
    
    def test_change_id_uniqueness(self, manager):
        """测试变更ID唯一性"""
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15)
        manager.update_validation_thresholds(layer1_threshold=0.80)
        
        change_ids = [record.change_id for record in manager.change_history]
        assert len(change_ids) == len(set(change_ids))  # 所有ID都是唯一的
    
    def test_config_persistence_across_updates(self, manager):
        """测试配置在多次更新后的持久性"""
        # 第一次更新
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15)
        
        # 第二次更新
        manager.update_arena_weights(layer1_weight=0.38, layer2_weight=0.32, layer3_weight=0.15, layer4_weight=0.15)
        
        # 验证最终配置
        assert manager.arena_weights.layer1_weight == 0.38
        assert manager.arena_weights.layer2_weight == 0.32
        
        # 验证历史记录
        assert len(manager.change_history) == 2
    
    def test_default_certification_standards(self, manager):
        """测试默认认证等级标准"""
        # 验证白金级标准
        platinum = manager.certification_standards['platinum']
        assert platinum.min_arena_score == 0.90
        assert platinum.min_layer1_score == 0.95
        assert platinum.min_simulation_sharpe == 2.5
        
        # 验证黄金级标准
        gold = manager.certification_standards['gold']
        assert gold.min_arena_score == 0.80
        assert gold.min_layer1_score == 0.85
        
        # 验证白银级标准
        silver = manager.certification_standards['silver']
        assert silver.min_arena_score == 0.75
        assert silver.min_layer1_score == 0.80
    
    def test_default_capital_allocation(self, manager):
        """测试默认资金配置规则"""
        assert manager.capital_allocation.platinum_max_ratio == 0.20
        assert manager.capital_allocation.gold_max_ratio == 0.15
        assert manager.capital_allocation.silver_max_ratio == 0.10
        assert manager.capital_allocation.position_limit_per_stock == 0.05
        assert manager.capital_allocation.sector_exposure_limit == 0.30
        assert manager.capital_allocation.max_leverage == 1.0
    
    def test_default_simulation_standards(self, manager):
        """测试默认模拟盘达标标准"""
        assert manager.simulation_standards.min_monthly_return == 0.05
        assert manager.simulation_standards.min_sharpe_ratio == 1.2
        assert manager.simulation_standards.max_drawdown == 0.15
        assert manager.simulation_standards.min_win_rate == 0.55
        assert manager.simulation_standards.max_var_95 == 0.05
    
    def test_market_config_defaults(self, manager):
        """测试默认市场配置"""
        assert MarketType.A_STOCK in manager.market_configs
        assert MarketType.US_STOCK in manager.market_configs
        assert MarketType.HK_STOCK in manager.market_configs
        
        a_stock_config = manager.market_configs[MarketType.A_STOCK]
        assert 'trading_hours' in a_stock_config
        assert 'min_liquidity' in a_stock_config
    
    def test_strategy_config_defaults(self, manager):
        """测试默认策略配置"""
        assert StrategyType.MOMENTUM in manager.strategy_configs
        assert StrategyType.MEAN_REVERSION in manager.strategy_configs
        assert StrategyType.ARBITRAGE in manager.strategy_configs
        
        momentum_config = manager.strategy_configs[StrategyType.MOMENTUM]
        assert 'min_holding_period' in momentum_config
        assert 'max_turnover' in momentum_config
    
    def test_update_validation_thresholds_all_parameters(self, manager):
        """测试更新所有验证阈值参数"""
        new_config = manager.update_validation_thresholds(
            layer1_threshold=0.80,
            layer2_threshold=0.75,
            layer3_threshold=0.70,
            layer4_threshold=0.75,
            overall_threshold=0.78,
            changed_by="admin",
            reason="全面调整"
        )
        
        assert new_config.layer1_threshold == 0.80
        assert new_config.layer2_threshold == 0.75
        assert new_config.layer3_threshold == 0.70
        assert new_config.layer4_threshold == 0.75
        assert new_config.overall_threshold == 0.78
    
    def test_update_capital_allocation_all_parameters(self, manager):
        """测试更新所有资金配置参数"""
        new_config = manager.update_capital_allocation(
            platinum_max_ratio=0.25,
            gold_max_ratio=0.18,
            silver_max_ratio=0.12,
            position_limit_per_stock=0.08,
            sector_exposure_limit=0.35,
            max_leverage=1.5,
            changed_by="admin",
            reason="全面调整"
        )
        
        assert new_config.platinum_max_ratio == 0.25
        assert new_config.gold_max_ratio == 0.18
        assert new_config.silver_max_ratio == 0.12
        assert new_config.position_limit_per_stock == 0.08
        assert new_config.sector_exposure_limit == 0.35
        assert new_config.max_leverage == 1.5
    
    def test_import_config_with_all_sections(self, manager):
        """测试导入包含所有配置节的完整配置"""
        config = {
            'arena_weights': {
                'layer1_weight': 0.40,
                'layer2_weight': 0.30,
                'layer3_weight': 0.15,
                'layer4_weight': 0.15
            },
            'validation_thresholds': {
                'layer1_threshold': 0.80,
                'layer2_threshold': 0.75,
                'layer3_threshold': 0.70,
                'layer4_threshold': 0.75,
                'overall_threshold': 0.78
            },
            'certification_standards': {
                'platinum': {
                    'min_arena_score': 0.92,
                    'min_layer1_score': 0.96,
                    'min_layer2_score': 0.88,
                    'min_layer3_score': 0.82,
                    'min_layer4_score': 0.88,
                    'min_simulation_sharpe': 2.8,
                    'max_simulation_drawdown': 0.08,
                    'min_simulation_win_rate': 0.68
                }
            },
            'capital_allocation': {
                'platinum_max_ratio': 0.25,
                'gold_max_ratio': 0.18,
                'silver_max_ratio': 0.12,
                'position_limit_per_stock': 0.08,
                'sector_exposure_limit': 0.35,
                'max_leverage': 1.5
            },
            'simulation_standards': {
                'min_monthly_return': 0.08,
                'min_sharpe_ratio': 1.5,
                'max_drawdown': 0.12,
                'min_win_rate': 0.58,
                'max_var_95': 0.04,
                'min_profit_factor': 1.5,
                'max_turnover_rate': 4.0,
                'min_calmar_ratio': 1.2,
                'max_benchmark_correlation': 0.65,
                'min_information_ratio': 0.9
            }
        }
        
        manager.import_config(config, changed_by="admin", reason="完整导入")
        
        # 验证所有配置都已更新
        assert manager.arena_weights.layer1_weight == 0.40
        assert manager.validation_thresholds.layer1_threshold == 0.80
        assert manager.certification_standards['platinum'].min_arena_score == 0.92
        assert manager.capital_allocation.platinum_max_ratio == 0.25
        assert manager.simulation_standards.min_monthly_return == 0.08
    
    def test_get_change_history_end_date_filter(self, manager):
        """测试按结束日期过滤变更历史"""
        now = datetime.now()
        
        manager.update_arena_weights(layer1_weight=0.40, layer2_weight=0.30, layer3_weight=0.15, layer4_weight=0.15)
        
        # 查询过去的变更（应该为空）
        history = manager.get_change_history(
            end_date=now - timedelta(hours=1)
        )
        assert len(history) == 0
        
        # 查询未来的变更（应该有结果）
        history = manager.get_change_history(
            end_date=now + timedelta(hours=1)
        )
        assert len(history) == 1
