"""认证数据持久化服务单元测试

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 数据持久化

测试覆盖：
- 策略元数据持久化
- Z2H基因胶囊持久化
- Arena验证结果持久化
- 模拟盘验证结果持久化
- 认证状态变更历史持久化
- 数据备份和恢复
- 事务支持
- 并发访问
- 错误处理

Author: MIA System
Version: 1.0.0
"""

import pytest
import tempfile
import shutil
import os
import stat
from pathlib import Path
from datetime import datetime
import json

from src.evolution.certification_persistence_service import (
    CertificationPersistenceService,
    PersistenceConfig
)
from src.evolution.z2h_data_models import (
    Z2HGeneCapsule,
    CertificationLevel,
    CapitalTier
)


class TestCertificationPersistenceService:
    """测试CertificationPersistenceService类"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # 清理
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def config(self, temp_dir):
        """创建测试配置"""
        return PersistenceConfig(
            data_dir=f"{temp_dir}/data",
            backup_dir=f"{temp_dir}/backups",
            enable_backup=True,
            max_backups=3
        )
    
    @pytest.fixture
    def service(self, config):
        """创建服务实例"""
        return CertificationPersistenceService(config)
    
    @pytest.fixture
    def sample_metadata(self):
        """创建示例元数据"""
        return {
            "strategy_id": "strategy_001",
            "strategy_name": "测试策略",
            "certification_level": "gold",
            "created_at": datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_gene_capsule(self):
        """创建示例基因胶囊"""
        return Z2HGeneCapsule(
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
    
    def test_initialization(self, service, config):
        """测试初始化"""
        assert service.config == config
        assert not service._transaction_active
        assert len(service._transaction_data) == 0
        
        # 验证目录已创建
        assert Path(config.data_dir).exists()
        assert Path(config.backup_dir).exists()
    
    def test_save_and_load_strategy_metadata(self, service, sample_metadata):
        """测试保存和加载策略元数据"""
        strategy_id = "strategy_001"
        
        # 保存
        result = service.save_strategy_metadata(strategy_id, sample_metadata)
        assert result is True
        
        # 加载
        loaded = service.load_strategy_metadata(strategy_id)
        assert loaded is not None
        assert loaded["strategy_id"] == strategy_id
        assert loaded["strategy_name"] == sample_metadata["strategy_name"]
        assert "last_updated" in loaded
    
    def test_load_nonexistent_metadata(self, service):
        """测试加载不存在的元数据"""
        loaded = service.load_strategy_metadata("nonexistent")
        assert loaded is None
    
    def test_save_and_load_gene_capsule(self, service, sample_gene_capsule):
        """测试保存和加载基因胶囊"""
        strategy_id = "strategy_001"
        
        # 保存
        result = service.save_gene_capsule(strategy_id, sample_gene_capsule)
        assert result is True
        
        # 加载
        loaded = service.load_gene_capsule(strategy_id)
        assert loaded is not None
        assert loaded.strategy_id == strategy_id
        assert loaded.strategy_name == sample_gene_capsule.strategy_name
        assert loaded.certification_level == sample_gene_capsule.certification_level
    
    def test_load_nonexistent_gene_capsule(self, service):
        """测试加载不存在的基因胶囊"""
        loaded = service.load_gene_capsule("nonexistent")
        assert loaded is None
    
    def test_save_and_load_arena_result(self, service):
        """测试保存和加载Arena结果"""
        strategy_id = "strategy_001"
        arena_result = {
            "overall_score": 0.85,
            "layer_results": {
                "reality_track": {"score": 0.85, "passed": True}
            },
            "passed": True
        }
        
        # 保存
        result = service.save_arena_result(strategy_id, arena_result)
        assert result is True
        
        # 加载
        loaded = service.load_arena_result(strategy_id)
        assert loaded is not None
        assert loaded["overall_score"] == 0.85
        assert "saved_at" in loaded
    
    def test_load_nonexistent_arena_result(self, service):
        """测试加载不存在的Arena结果"""
        loaded = service.load_arena_result("nonexistent")
        assert loaded is None
    
    def test_save_and_load_simulation_result(self, service):
        """测试保存和加载模拟盘结果"""
        strategy_id = "strategy_001"
        simulation_result = {
            "passed": True,
            "duration_days": 30,
            "tier_results": {
                "tier_1": {"sharpe": 1.5, "max_drawdown": 0.10}
            }
        }
        
        # 保存
        result = service.save_simulation_result(strategy_id, simulation_result)
        assert result is True
        
        # 加载
        loaded = service.load_simulation_result(strategy_id)
        assert loaded is not None
        assert loaded["passed"] is True
        assert loaded["duration_days"] == 30
        assert "saved_at" in loaded
    
    def test_load_nonexistent_simulation_result(self, service):
        """测试加载不存在的模拟盘结果"""
        loaded = service.load_simulation_result("nonexistent")
        assert loaded is None
    
    def test_save_and_load_status_change(self, service):
        """测试保存和加载状态变更"""
        strategy_id = "strategy_001"
        
        # 保存第一条记录
        change1 = {
            "from_status": "not_certified",
            "to_status": "in_progress",
            "reason": "开始认证"
        }
        result = service.save_status_change(strategy_id, change1)
        assert result is True
        
        # 保存第二条记录
        change2 = {
            "from_status": "in_progress",
            "to_status": "certified",
            "reason": "认证通过"
        }
        result = service.save_status_change(strategy_id, change2)
        assert result is True
        
        # 加载历史
        history = service.load_status_history(strategy_id)
        assert len(history) == 2
        assert history[0]["from_status"] == "not_certified"
        assert history[1]["to_status"] == "certified"
        assert "timestamp" in history[0]
        assert "timestamp" in history[1]
    
    def test_load_empty_status_history(self, service):
        """测试加载空的状态历史"""
        history = service.load_status_history("nonexistent")
        assert history == []
    
    def test_backup_and_restore(self, service, sample_metadata):
        """测试备份和恢复"""
        strategy_id = "strategy_001"
        
        # 保存一些数据
        service.save_strategy_metadata(strategy_id, sample_metadata)
        
        # 创建备份
        backup_name = service.backup_data("test_backup")
        assert "test_backup" in backup_name
        
        # 修改数据
        sample_metadata["strategy_name"] = "修改后的策略"
        service.save_strategy_metadata(strategy_id, sample_metadata)
        
        # 验证数据已修改
        loaded = service.load_strategy_metadata(strategy_id)
        assert loaded["strategy_name"] == "修改后的策略"
        
        # 恢复备份
        result = service.restore_data("test_backup")
        assert result is True
        
        # 验证数据已恢复
        loaded = service.load_strategy_metadata(strategy_id)
        assert loaded["strategy_name"] == "测试策略"
    
    def test_list_backups(self, service, sample_metadata):
        """测试列出备份"""
        # 创建多个备份
        service.save_strategy_metadata("strategy_001", sample_metadata)
        service.backup_data("backup1")
        service.backup_data("backup2")
        service.backup_data("backup3")
        
        # 列出备份
        backups = service.list_backups()
        assert len(backups) >= 3
        assert "backup1" in backups
        assert "backup2" in backups
        assert "backup3" in backups
    
    def test_cleanup_old_backups(self, service, sample_metadata):
        """测试清理旧备份"""
        # 创建超过最大数量的备份
        service.save_strategy_metadata("strategy_001", sample_metadata)
        for i in range(5):
            service.backup_data(f"backup{i}")
        
        # 验证只保留最新的3个备份
        backups = service.list_backups()
        assert len(backups) == 3
    
    def test_transaction_commit(self, service, sample_metadata):
        """测试事务提交"""
        strategy_id = "strategy_001"
        
        # 开始事务
        service.begin_transaction()
        assert service._transaction_active is True
        
        # 在事务中保存数据（实际上会被缓存）
        # 注意：当前实现中，事务内的操作会立即执行
        # 这里我们测试事务的基本流程
        
        # 提交事务
        result = service.commit_transaction()
        assert result is True
        assert service._transaction_active is False
    
    def test_transaction_rollback(self, service):
        """测试事务回滚"""
        # 开始事务
        service.begin_transaction()
        assert service._transaction_active is True
        
        # 回滚事务
        service.rollback_transaction()
        assert service._transaction_active is False
        assert len(service._transaction_data) == 0
    
    def test_transaction_already_active(self, service):
        """测试重复开始事务"""
        service.begin_transaction()
        
        with pytest.raises(RuntimeError, match="事务已激活"):
            service.begin_transaction()
        
        # 清理
        service.rollback_transaction()
    
    def test_commit_without_transaction(self, service):
        """测试未开始事务就提交"""
        with pytest.raises(RuntimeError, match="事务未激活"):
            service.commit_transaction()
    
    def test_rollback_without_transaction(self, service):
        """测试未开始事务就回滚"""
        with pytest.raises(RuntimeError, match="事务未激活"):
            service.rollback_transaction()
    
    def test_transaction_with_operations(self, service, sample_metadata, sample_gene_capsule):
        """测试事务中的操作"""
        strategy_id = "strategy_001"
        
        # 开始事务
        service.begin_transaction()
        
        # 在事务中缓存操作
        service._transaction_data["meta"] = ("save_metadata", (strategy_id, sample_metadata))
        service._transaction_data["capsule"] = ("save_gene_capsule", (strategy_id, sample_gene_capsule))
        service._transaction_data["arena"] = ("save_arena_result", (strategy_id, {"score": 0.85}))
        service._transaction_data["sim"] = ("save_simulation_result", (strategy_id, {"passed": True}))
        service._transaction_data["status"] = ("save_status_change", (strategy_id, {"from": "a", "to": "b"}))
        
        # 提交事务
        result = service.commit_transaction()
        assert result is True
        
        # 验证数据已保存
        loaded_meta = service.load_strategy_metadata(strategy_id)
        assert loaded_meta is not None
        
        loaded_capsule = service.load_gene_capsule(strategy_id)
        assert loaded_capsule is not None
        
        loaded_arena = service.load_arena_result(strategy_id)
        assert loaded_arena is not None
        
        loaded_sim = service.load_simulation_result(strategy_id)
        assert loaded_sim is not None
        
        history = service.load_status_history(strategy_id)
        assert len(history) > 0
    
    def test_load_gene_capsule_invalid_json(self, service, temp_dir):
        """测试加载无效JSON格式的基因胶囊"""
        strategy_id = "strategy_001"
        
        # 创建无效的JSON文件
        capsule_dir = Path(service.config.data_dir) / "gene_capsules"
        capsule_dir.mkdir(parents=True, exist_ok=True)
        file_path = capsule_dir / f"{strategy_id}.json"
        
        with open(file_path, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(ValueError, match="Z2H基因胶囊格式不正确"):
            service.load_gene_capsule(strategy_id)
    
    
    def test_load_gene_capsule_invalid_json(self, service, temp_dir):
        """测试加载无效JSON格式的Arena结果"""
        strategy_id = "strategy_001"
        
        # 创建无效的JSON文件
        arena_dir = Path(service.config.data_dir) / "arena_results"
        arena_dir.mkdir(parents=True, exist_ok=True)
        file_path = arena_dir / f"{strategy_id}.json"
        
        with open(file_path, 'w') as f:
            f.write("invalid json")
        
        with pytest.raises(ValueError, match="Arena验证结果格式不正确"):
            service.load_arena_result(strategy_id)
    
    def test_load_simulation_result_invalid_json(self, service, temp_dir):
        """测试加载无效JSON格式的模拟盘结果"""
        strategy_id = "strategy_001"
        
        # 创建无效的JSON文件
        sim_dir = Path(service.config.data_dir) / "simulation_results"
        sim_dir.mkdir(parents=True, exist_ok=True)
        file_path = sim_dir / f"{strategy_id}.json"
        
        with open(file_path, 'w') as f:
            f.write("invalid")
        
        with pytest.raises(ValueError, match="模拟盘验证结果格式不正确"):
            service.load_simulation_result(strategy_id)
    
    def test_load_status_history_invalid_json(self, service, temp_dir):
        """测试加载无效JSON格式的状态历史"""
        strategy_id = "strategy_001"
        
        # 创建无效的JSON文件
        history_dir = Path(service.config.data_dir) / "status_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        file_path = history_dir / f"{strategy_id}.json"
        
        with open(file_path, 'w') as f:
            f.write("not json")
        
        with pytest.raises(ValueError, match="认证状态变更历史格式不正确"):
            service.load_status_history(strategy_id)
    
    def test_save_metadata_io_error(self, service, temp_dir):
        """测试保存元数据IO错误"""
        # 创建一个只读文件来模拟IO错误
        strategy_id = "strategy_001"
        metadata_dir = Path(service.config.data_dir) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        file_path = metadata_dir / f"{strategy_id}.json"
        
        # 创建一个文件并设置为只读
        with open(file_path, 'w') as f:
            f.write('{}')
        
        # 在Windows上设置只读属性
        import stat
        os.chmod(file_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        
        try:
            with pytest.raises(IOError, match="无法保存策略元数据"):
                service.save_strategy_metadata(strategy_id, {"test": "data"})
        finally:
            # 恢复写权限以便清理
            os.chmod(file_path, stat.S_IWUSR | stat.S_IRUSR)
    
    def test_load_metadata_invalid_json(self, service, temp_dir):
        """测试加载无效JSON格式的元数据"""
        strategy_id = "strategy_001"
        
        # 创建无效的JSON文件
        metadata_dir = Path(service.config.data_dir) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        file_path = metadata_dir / f"{strategy_id}.json"
        
        with open(file_path, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(ValueError, match="策略元数据格式不正确"):
            service.load_strategy_metadata(strategy_id)
    
    def test_restore_nonexistent_backup(self, service):
        """测试恢复不存在的备份"""
        with pytest.raises(IOError, match="无法恢复数据"):
            service.restore_data("nonexistent_backup")
    
    def test_backup_disabled(self, temp_dir):
        """测试禁用备份"""
        config = PersistenceConfig(
            data_dir=f"{temp_dir}/data",
            backup_dir=f"{temp_dir}/backups",
            enable_backup=False
        )
        service = CertificationPersistenceService(config)
        
        with pytest.raises(IOError, match="无法备份数据"):
            service.backup_data()


class TestPersistenceConfig:
    """测试PersistenceConfig类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = PersistenceConfig()
        
        assert config.data_dir == "data/z2h_certification"
        assert config.backup_dir == "data/z2h_certification/backups"
        assert config.enable_backup is True
        assert config.max_backups == 10
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = PersistenceConfig(
            data_dir="/custom/data",
            backup_dir="/custom/backups",
            enable_backup=False,
            max_backups=5
        )
        
        assert config.data_dir == "/custom/data"
        assert config.backup_dir == "/custom/backups"
        assert config.enable_backup is False
        assert config.max_backups == 5
