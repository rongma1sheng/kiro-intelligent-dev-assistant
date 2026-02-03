"""Integration Tests for Sparta Evolution System

白皮书依据: 第四章 Sparta Evolution System

This module provides integration tests for the data storage, configuration,
logging, and metrics components.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Import components
from src.evolution.storage.data_storage_manager import DataStorageManager
from src.evolution.config.configuration_manager import ConfigurationManager
from src.evolution.observability.structured_logger import StructuredLogger, LogLevel
from src.evolution.observability.metrics_collector import MetricsCollector


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_storage():
    """创建临时存储目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage_manager(temp_storage):
    """创建存储管理器"""
    return DataStorageManager(storage_root=temp_storage)


@pytest.fixture
def config_manager():
    """创建配置管理器"""
    return ConfigurationManager()


@pytest.fixture
def logger_instance():
    """创建日志器"""
    return StructuredLogger("integration_test", LogLevel.DEBUG)


@pytest.fixture
def metrics_collector():
    """创建指标收集器"""
    return MetricsCollector()


# ============================================================================
# Integration Test: Data Storage and Retrieval
# ============================================================================

class TestDataStorageIntegration:
    """数据存储集成测试"""
    
    def test_arena_result_storage_and_retrieval(self, storage_manager):
        """测试Arena结果存储和检索
        
        白皮书依据: 第四章 4.8 数据存储与检索
        """
        result_id = 'ARENA_RESULT_001'
        arena_data = {
            'factor_id': 'FACTOR_001',
            'arena_score': 0.85,
            'passed': True,
            'metrics': {
                'ic': 0.05,
                'ir': 1.2,
                'sharpe': 1.8
            }
        }
        
        # 存储
        success = storage_manager.store_arena_result(result_id, arena_data)
        assert success, "Arena结果存储应该成功"
        
        # 检索
        retrieved = storage_manager.retrieve_arena_result(result_id)
        assert retrieved is not None, "应该能够检索Arena结果"
        assert retrieved['factor_id'] == arena_data['factor_id'], "数据应该一致"
        assert retrieved['arena_score'] == arena_data['arena_score'], "分数应该一致"
    
    def test_z2h_capsule_storage_and_retrieval(self, storage_manager):
        """测试Z2H胶囊存储和检索
        
        白皮书依据: 第四章 4.8 数据存储与检索
        """
        capsule_id = 'Z2H_CAPSULE_001'
        capsule_data = {
            'strategy_id': 'STRATEGY_001',
            'certification_level': 'GOLD',
            'sharpe_ratio': 2.5,
            'metrics': {
                'total_return': 0.15,
                'max_drawdown': 0.08
            }
        }
        
        # 存储
        success = storage_manager.store_z2h_capsule(capsule_id, capsule_data)
        assert success, "Z2H胶囊存储应该成功"
        
        # 检索
        retrieved = storage_manager.retrieve_z2h_capsule(capsule_id)
        assert retrieved is not None, "应该能够检索Z2H胶囊"
        assert retrieved['strategy_id'] == capsule_data['strategy_id'], "数据应该一致"
        assert retrieved['certification_level'] == capsule_data['certification_level'], "认证级别应该一致"
    
    def test_simulation_data_storage(self, storage_manager):
        """测试模拟数据存储
        
        白皮书依据: 第四章 4.8 数据存储与检索
        """
        simulation_id = 'SIM_001'
        sim_data = {
            'strategy_id': 'STRATEGY_001',
            'total_return': 0.12,
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.08,
            'daily_results': [
                {'date': '2026-01-01', 'return': 0.01},
                {'date': '2026-01-02', 'return': 0.02}
            ]
        }
        
        # 存储
        success = storage_manager.store_simulation_data(simulation_id, sim_data)
        assert success, "模拟数据存储应该成功"


# ============================================================================
# Integration Test: Configuration Management
# ============================================================================

class TestConfigurationIntegration:
    """配置管理集成测试"""
    
    def test_config_affects_arena_thresholds(self, temp_storage):
        """测试配置影响Arena阈值
        
        白皮书依据: 第四章 4.9 配置管理
        """
        # 创建配置管理器
        config_manager = ConfigurationManager()
        
        # 获取默认Arena配置
        arena_config = config_manager.arena
        
        # 验证：默认配置应该有合理的值
        assert arena_config.min_ic == 0.03, "默认min_ic应该是0.03"
        assert arena_config.pass_score == 0.7, "默认pass_score应该是0.7"
        
        # 更新配置
        success = config_manager.update_config({
            'arena': {
                'min_ic': 0.05,
                'pass_score': 0.8
            }
        })
        
        assert success, "配置更新应该成功"
        
        # 验证：配置已更新
        assert config_manager.arena.min_ic == 0.05, "min_ic应该更新为0.05"
        assert config_manager.arena.pass_score == 0.8, "pass_score应该更新为0.8"
    
    def test_config_validation(self, config_manager):
        """测试配置验证
        
        白皮书依据: 第四章 4.9 配置管理
        """
        # 尝试更新无效配置
        success = config_manager.update_config({
            'arena': {
                'min_ic': -0.5  # 无效值
            }
        })
        
        # 验证：更新应该失败
        assert not success, "无效配置更新应该失败"
        
        # 验证：原配置保持不变
        assert config_manager.arena.min_ic == 0.03, "原配置应该保持不变"


# ============================================================================
# Integration Test: Logging and Metrics
# ============================================================================

class TestLoggingMetricsIntegration:
    """日志和指标集成测试"""
    
    def test_logging_and_metrics_integration(
        self,
        logger_instance,
        metrics_collector
    ):
        """测试日志和指标集成
        
        白皮书依据: 第四章 4.10 日志和可观测性
        """
        # 记录日志
        entry = logger_instance.log_arena_start(
            arena_type='factor',
            entity_id='FACTOR_001',
            parameters={'min_ic': 0.03}
        )
        
        # 记录指标
        metrics_collector.record_arena_result(
            arena_type='factor',
            passed=True,
            score=0.85
        )
        
        # 验证：日志应该被记录
        assert entry is not None, "日志应该被记录"
        assert entry.context['entity_id'] == 'FACTOR_001', "日志应该包含正确的entity_id"
        
        # 验证：指标应该被记录
        pass_rate = metrics_collector.get_arena_pass_rate('factor')
        assert pass_rate == 1.0, "通过率应该是100%"
    
    def test_metrics_health_status(self, metrics_collector):
        """测试指标健康状态
        
        白皮书依据: 第四章 4.10 日志和可观测性
        """
        # 记录一些指标
        metrics_collector.record_arena_result('factor', True, 0.85)
        metrics_collector.record_arena_result('factor', True, 0.75)
        metrics_collector.record_arena_result('factor', False, 0.55)
        
        metrics_collector.record_simulation_result(True, 1.8, 0.12)
        metrics_collector.record_simulation_result(False, 0.8, -0.05)
        
        # 获取健康状态
        health = metrics_collector.get_health_status()
        
        # 验证：健康状态应该有效
        assert health['status'] in ['healthy', 'degraded'], "健康状态应该有效"
        assert 'metrics' in health, "应该包含指标"
        assert 'counters' in health, "应该包含计数器"
        
        # 验证：通过率计算正确
        factor_pass_rate = health['metrics']['factor_arena_pass_rate']
        assert abs(factor_pass_rate - 2/3) < 0.01, "因子Arena通过率应该是2/3"
    
    def test_structured_logging_json_format(self, logger_instance):
        """测试结构化日志JSON格式
        
        白皮书依据: 第四章 4.10.6 结构化日志
        """
        # 记录各种类型的日志
        logger_instance.log_arena_start('factor', 'F001', {'min_ic': 0.03})
        logger_instance.log_track_completion('reality', 'F001', 0.85, {'ic': 0.05})
        logger_instance.log_validation_failure('arena', 'F002', 'IC too low', {'ic': 0.01})
        logger_instance.log_z2h_certification('S001', 'GOLD', 'C001', {'sharpe': 2.5})
        logger_instance.log_decay_detection('F003', 'SEVERE', 0.01, 35)
        
        # 获取所有日志
        entries = logger_instance.get_entries()
        
        # 验证：应该有5条日志
        assert len(entries) == 5, "应该有5条日志"
        
        # 验证：每条日志都可以转换为JSON
        for entry in entries:
            json_str = entry.to_json()
            assert json_str is not None, "日志应该可以转换为JSON"
            assert len(json_str) > 0, "JSON字符串不应为空"


# ============================================================================
# Integration Test: End-to-End Flow
# ============================================================================

class TestEndToEndFlow:
    """端到端流程测试"""
    
    def test_complete_pipeline_with_logging_and_storage(self, temp_storage):
        """测试完整流水线（日志和存储）
        
        白皮书依据: 第四章 完整系统集成
        """
        # 创建组件
        logger = StructuredLogger("e2e_test", LogLevel.DEBUG)
        metrics = MetricsCollector()
        storage = DataStorageManager(storage_root=temp_storage)
        config = ConfigurationManager()
        
        # 1. 记录开始
        logger.info("E2E测试开始", test_id="E2E_001")
        
        # 2. 模拟因子Arena测试
        factor_id = 'E2E_FACTOR_001'
        
        logger.log_arena_start(
            arena_type='factor',
            entity_id=factor_id,
            parameters={'min_ic': config.arena.min_ic}
        )
        
        # 模拟Arena结果
        arena_result = {
            'factor_id': factor_id,
            'passed': True,
            'overall_score': 0.85,
            'metrics': {'ic': 0.05, 'ir': 1.2}
        }
        
        # 记录Track完成
        logger.log_track_completion('reality', factor_id, 0.85, arena_result['metrics'])
        
        # 记录指标
        metrics.record_arena_result(
            arena_type='factor',
            passed=arena_result['passed'],
            score=arena_result['overall_score']
        )
        
        # 存储结果
        storage.store_arena_result(f"arena_{factor_id}", arena_result)
        
        # 3. 模拟Z2H认证
        capsule_id = 'E2E_CAPSULE_001'
        capsule_data = {
            'strategy_id': 'E2E_STRATEGY_001',
            'certification_level': 'GOLD',
            'sharpe_ratio': 2.5
        }
        
        logger.log_z2h_certification(
            strategy_id=capsule_data['strategy_id'],
            certification_level=capsule_data['certification_level'],
            capsule_id=capsule_id,
            metrics={'sharpe_ratio': capsule_data['sharpe_ratio']}
        )
        
        storage.store_z2h_capsule(capsule_id, capsule_data)
        
        # 4. 验证日志和指标
        entries = logger.get_entries()
        assert len(entries) >= 4, "应该有多条日志记录"
        
        health = metrics.get_health_status()
        assert health['status'] == 'healthy', "健康状态应该是healthy"
        
        # 5. 验证存储
        retrieved_arena = storage.retrieve_arena_result(f"arena_{factor_id}")
        assert retrieved_arena is not None, "应该能检索Arena结果"
        
        retrieved_capsule = storage.retrieve_z2h_capsule(capsule_id)
        assert retrieved_capsule is not None, "应该能检索Z2H胶囊"
        
        # 6. 记录完成
        logger.info("E2E测试完成", test_id="E2E_001", status="success")
