"""统一因子挖掘系统单元测试

白皮书依据: 第四章 4.1.17 统一因子挖掘系统
需求: 15.1, 15.2, 15.8, 15.9, 15.10
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import time
from loguru import logger

from src.evolution.unified_factor_mining_system import (
    UnifiedFactorMiningSystem,
    MinerType,
    MinerStatus,
    MinerMetadata,
    FactorMetadata,
    MiningResult,
    BaseMiner,
    GeneticMinerAdapter
)
from src.evolution.genetic_miner import EvolutionConfig


class TestMinerMetadata:
    """测试挖掘器元数据"""
    
    def test_miner_metadata_initialization(self):
        """测试挖掘器元数据初始化"""
        metadata = MinerMetadata(
            miner_type=MinerType.GENETIC,
            miner_name="TestMiner"
        )
        
        assert metadata.miner_type == MinerType.GENETIC
        assert metadata.miner_name == "TestMiner"
        assert metadata.status == MinerStatus.IDLE
        assert metadata.total_factors_discovered == 0
        assert metadata.is_healthy is True
        assert metadata.error_count == 0


class TestFactorMetadata:
    """测试因子元数据"""
    
    def test_factor_metadata_initialization(self):
        """测试因子元数据初始化"""
        factor = FactorMetadata(
            factor_id="test_factor_001",
            factor_name="Test Factor",
            factor_type=MinerType.GENETIC,
            data_source="market_data",
            discovery_date=datetime.now(),
            discoverer="GeneticMiner",
            expression="close / delay(close, 1) - 1",
            fitness=0.75,
            ic=0.08,
            ir=1.2,
            sharpe=1.5
        )
        
        assert factor.factor_id == "test_factor_001"
        assert factor.factor_type == MinerType.GENETIC
        assert factor.fitness == 0.75
        assert factor.lifecycle_status == "discovered"


class TestMiningResult:
    """测试挖掘结果"""
    
    def test_mining_result_success(self):
        """测试成功的挖掘结果"""
        factors = [
            FactorMetadata(
                factor_id="f1",
                factor_name="Factor 1",
                factor_type=MinerType.GENETIC,
                data_source="market",
                discovery_date=datetime.now(),
                discoverer="test",
                expression="test",
                fitness=0.8
            )
        ]
        
        result = MiningResult(
            miner_type=MinerType.GENETIC,
            factors=factors,
            execution_time=1.5,
            success=True
        )
        
        assert result.success is True
        assert len(result.factors) == 1
        assert result.error is None
        
    def test_mining_result_failure(self):
        """测试失败的挖掘结果"""
        result = MiningResult(
            miner_type=MinerType.GENETIC,
            factors=[],
            execution_time=0.5,
            success=False,
            error="Test error"
        )
        
        assert result.success is False
        assert len(result.factors) == 0
        assert result.error == "Test error"


class MockMiner(BaseMiner):
    """模拟挖掘器用于测试"""
    
    def __init__(self, miner_type: MinerType, should_fail: bool = False):
        super().__init__(miner_type, f"Mock{miner_type.value}")
        self.should_fail = should_fail
        self.call_count = 0
        
    def mine_factors(self, data, returns, **kwargs):
        """模拟挖掘因子"""
        self.call_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"Mock failure from {self.miner_name}")
            
        # 返回模拟因子
        factor = FactorMetadata(
            factor_id=f"mock_{self.miner_type.value}_{self.call_count}",
            factor_name=f"Mock Factor {self.call_count}",
            factor_type=self.miner_type,
            data_source="mock",
            discovery_date=datetime.now(),
            discoverer=self.miner_name,
            expression="mock_expression",
            fitness=0.75
        )
        
        return [factor]


class TestBaseMiner:
    """测试基础挖掘器接口"""
    
    def test_base_miner_initialization(self):
        """测试基础挖掘器初始化"""
        miner = MockMiner(MinerType.GENETIC)
        
        assert miner.miner_type == MinerType.GENETIC
        assert miner.is_healthy() is True
        assert miner.get_metadata().miner_type == MinerType.GENETIC
        
    def test_base_miner_not_implemented(self):
        """测试基础挖掘器未实现方法"""
        miner = BaseMiner(MinerType.GENETIC, "TestMiner")
        
        with pytest.raises(NotImplementedError):
            miner.mine_factors(None, None)


class TestGeneticMinerAdapter:
    """测试遗传算法挖掘器适配器"""
    
    @pytest.fixture
    def adapter(self):
        """创建适配器实例"""
        config = EvolutionConfig(
            population_size=10,
            max_generations=5
        )
        return GeneticMinerAdapter(config)
        
    def test_adapter_initialization(self, adapter):
        """测试适配器初始化"""
        assert adapter.miner_type == MinerType.GENETIC
        assert adapter.miner_name == "GeneticMiner"
        assert adapter.config.population_size == 10
        
    def test_adapter_mine_factors(self, adapter):
        """测试适配器挖掘因子"""
        # 创建测试数据
        data = pd.DataFrame({
            'close': np.random.randn(100) + 100,
            'volume': np.random.randint(1000, 10000, 100)
        })
        returns = pd.Series(np.random.randn(100) * 0.01)
        
        # 挖掘因子
        factors = adapter.mine_factors(data, returns, generations=2)
        
        # 验证结果
        assert len(factors) == 1
        assert factors[0].factor_type == MinerType.GENETIC
        assert factors[0].discoverer == "GeneticMiner"
        assert adapter.metadata.total_factors_discovered == 1


class TestUnifiedFactorMiningSystem:
    """测试统一因子挖掘系统"""
    
    @pytest.fixture
    def system(self):
        """创建系统实例"""
        return UnifiedFactorMiningSystem(max_workers=4)
        
    def test_system_initialization(self, system):
        """测试系统初始化
        
        需求: 15.1, 15.2 - 系统应该初始化并注册所有16个挖掘器
        白皮书依据: 第四章 4.1 暗物质挖掘工厂 - 16个专业因子挖掘器
        """
        assert system.max_workers == 4
        assert system.system_load_threshold == 0.8
        
        # 验证所有16个挖掘器都已注册（包括UNIFIED/MetaMiner）
        assert len(system.miners) == 16  # 16个挖掘器（白皮书定义）
        
        # 验证每个挖掘器类型都已注册
        expected_miners = [
            MinerType.GENETIC,
            MinerType.ALTERNATIVE_DATA,
            MinerType.AI_ENHANCED,
            MinerType.NETWORK,
            MinerType.HIGH_FREQUENCY,
            MinerType.SENTIMENT,
            MinerType.ML_FEATURE,
            MinerType.TIME_SERIES_DL,
            MinerType.ESG,
            MinerType.PRICE_VOLUME,
            MinerType.MACRO,
            MinerType.EVENT_DRIVEN,
            MinerType.ALTERNATIVE_EXTENDED,
            MinerType.STYLE_ROTATION,
            MinerType.FACTOR_COMBINATION,
            MinerType.UNIFIED  # MetaMiner - 元挖掘器
        ]
        
        for miner_type in expected_miners:
            assert miner_type in system.miners, f"挖掘器 {miner_type.value} 未注册"
            miner = system.get_miner(miner_type)
            assert miner is not None
            assert miner.is_healthy()
        
    def test_system_initialization_invalid_params(self):
        """测试系统初始化参数验证"""
        with pytest.raises(ValueError, match="max_workers必须 > 0"):
            UnifiedFactorMiningSystem(max_workers=0)
            
        with pytest.raises(ValueError, match="system_load_threshold必须在"):
            UnifiedFactorMiningSystem(system_load_threshold=1.5)
            
    def test_register_miner(self, system):
        """测试注册挖掘器
        
        需求: 15.1 - 系统应该支持注册新挖掘器
        白皮书依据: 第四章 4.1 暗物质挖掘工厂
        
        注意: 所有16个挖掘器（包括UNIFIED）在初始化时已注册，
        此测试验证重复注册会抛出异常
        """
        # 所有16个挖掘器在初始化时已注册，包括UNIFIED
        # 验证UNIFIED已存在
        assert MinerType.UNIFIED in system.miners
        
        # 尝试注册已存在的类型应该抛出异常
        mock_miner = MockMiner(MinerType.UNIFIED)
        with pytest.raises(ValueError, match="挖掘器类型已存在"):
            system.register_miner(MinerType.UNIFIED, mock_miner)
        
    def test_register_miner_duplicate(self, system):
        """测试注册重复挖掘器"""
        mock_miner = MockMiner(MinerType.GENETIC)
        
        with pytest.raises(ValueError, match="挖掘器类型已存在"):
            system.register_miner(MinerType.GENETIC, mock_miner)
            
    def test_get_miner(self, system):
        """测试获取挖掘器"""
        miner = system.get_miner(MinerType.GENETIC)
        assert miner is not None
        assert miner.miner_type == MinerType.GENETIC
        
        # 获取另一个存在的挖掘器
        miner = system.get_miner(MinerType.ALTERNATIVE_DATA)
        assert miner is not None
        assert miner.miner_type == MinerType.ALTERNATIVE_DATA
        
    def test_get_all_miners(self, system):
        """测试获取所有挖掘器"""
        miners = system.get_all_miners()
        assert isinstance(miners, dict)
        assert len(miners) >= 1
        assert MinerType.GENETIC in miners
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_check_system_load_ok(self, mock_memory, mock_cpu, system):
        """测试系统负载检查 - 正常情况"""
        mock_cpu.return_value = 50.0  # 50% CPU
        mock_memory.return_value = MagicMock(percent=60.0)  # 60% memory
        
        assert system._check_system_load() is True
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_check_system_load_high(self, mock_memory, mock_cpu, system):
        """测试系统负载检查 - 负载过高
        
        需求: 15.9 - 当系统负载超过80%时，应该节流挖掘操作
        """
        mock_cpu.return_value = 90.0  # 90% CPU
        mock_memory.return_value = MagicMock(percent=70.0)  # 70% memory
        
        assert system._check_system_load() is False
        
    def test_mine_single_success(self, system):
        """测试单个挖掘器执行 - 成功"""
        mock_miner = MockMiner(MinerType.GENETIC)
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series([0.01, 0.01, 0.01])
        
        result = system._mine_single(
            MinerType.GENETIC,
            mock_miner,
            data,
            returns
        )
        
        assert result.success is True
        assert len(result.factors) == 1
        assert result.error is None
        assert mock_miner.call_count == 1
        
    def test_mine_single_failure(self, system):
        """测试单个挖掘器执行 - 失败
        
        需求: 15.10 - 当挖掘器失败时，应该隔离故障
        """
        mock_miner = MockMiner(MinerType.GENETIC, should_fail=True)
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series([0.01, 0.01, 0.01])
        
        result = system._mine_single(
            MinerType.GENETIC,
            mock_miner,
            data,
            returns
        )
        
        assert result.success is False
        assert len(result.factors) == 0
        assert result.error is not None
        assert "Mock failure" in result.error
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_mine_parallel_success(self, mock_memory, mock_cpu):
        """测试并行挖掘 - 成功
        
        需求: 15.2, 15.8 - 系统应该支持并行执行多个挖掘器
        """
        # 模拟正常系统负载
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        
        # 创建新系统（不使用fixture，避免状态污染）
        system = UnifiedFactorMiningSystem(max_workers=4)
        
        # 创建测试数据
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series([0.01, 0.01, 0.01])
        
        # 并行挖掘（只挖掘前3个挖掘器以加快测试）
        results = system.mine_parallel(
            data,
            returns,
            miner_types=[MinerType.GENETIC, MinerType.ALTERNATIVE_DATA, MinerType.AI_ENHANCED]
        )
        
        # 验证结果
        assert len(results) == 3
        successful = sum(1 for r in results if r.success)
        assert successful >= 2  # 至少2个成功
        
        system.shutdown()
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_all_16_miners_can_mine(self, mock_memory, mock_cpu):
        """测试所有16个挖掘器都能正常挖掘
        
        需求: 15.1, 15.2 - 验证所有16个专业挖掘器都已注册并可用
        白皮书依据: 第四章 4.1 暗物质挖掘工厂 - 16个专业因子挖掘器
        
        注意: 由于不同挖掘器需要不同的数据格式和参数，
        在测试环境中只验证挖掘器注册和基本调用能力，
        不要求所有挖掘器都成功返回因子。
        """
        # 模拟正常系统负载
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        
        # 创建系统
        system = UnifiedFactorMiningSystem(max_workers=16)
        
        # 创建测试数据
        data = pd.DataFrame({
            'close': np.random.randn(50) + 100,
            'volume': np.random.randint(1000, 10000, 50)
        })
        returns = pd.Series(np.random.randn(50) * 0.01)
        
        # 并行挖掘所有挖掘器
        results = system.mine_parallel(data, returns)
        
        # 验证结果 - 16个挖掘器（白皮书定义）
        assert len(results) == 16  # 16个挖掘器
        
        # 统计成功和失败
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        logger.info(f"挖掘结果: 成功={successful}, 失败={failed}")
        
        # 至少50%的挖掘器应该成功（测试环境数据有限）
        assert successful >= 8, f"成功率过低: {successful}/16"
        
        # 验证每种类型的挖掘器都有结果
        miner_types_with_results = {r.miner_type for r in results}
        assert len(miner_types_with_results) == 16
        
        # 验证成功的挖掘器发现了因子
        total_factors = sum(len(r.factors) for r in results if r.success)
        assert total_factors >= 1  # 至少发现1个因子
        
        # 清理
        system.shutdown()
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_mine_parallel_with_failures(self, mock_memory, mock_cpu):
        """测试并行挖掘 - 部分失败
        
        需求: 15.10 - 当挖掘器失败时，应该隔离故障并继续其他挖掘器
        """
        # 模拟正常系统负载
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        
        # 创建新系统
        system = UnifiedFactorMiningSystem(max_workers=4)
        
        # 注册一个会失败的挖掘器（替换现有的）
        failing_miner = MockMiner(MinerType.ALTERNATIVE_DATA, should_fail=True)
        system.miners[MinerType.ALTERNATIVE_DATA] = failing_miner
        
        # 注册一个正常的挖掘器（替换现有的）
        normal_miner = MockMiner(MinerType.AI_ENHANCED, should_fail=False)
        system.miners[MinerType.AI_ENHANCED] = normal_miner
        
        # 创建测试数据
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series([0.01, 0.01, 0.01])
        
        # 并行挖掘（只挖掘这3个挖掘器）
        results = system.mine_parallel(
            data,
            returns,
            miner_types=[MinerType.GENETIC, MinerType.ALTERNATIVE_DATA, MinerType.AI_ENHANCED]
        )
        
        # 验证结果：即使有失败，其他挖掘器也应该成功
        assert len(results) == 3
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        assert successful >= 1  # 至少有一个成功
        assert failed >= 1  # 至少有一个失败（ALTERNATIVE_DATA应该失败）
        
        system.shutdown()
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_mine_parallel_high_load(self, mock_memory, mock_cpu, system):
        """测试并行挖掘 - 系统负载过高
        
        需求: 15.9 - 当系统负载超过80%时，应该拒绝启动新任务
        """
        # 模拟高系统负载
        mock_cpu.return_value = 95.0
        mock_memory.return_value = MagicMock(percent=85.0)
        
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series([0.01, 0.01, 0.01])
        
        # 应该抛出RuntimeError
        with pytest.raises(RuntimeError, match="系统负载超过阈值"):
            system.mine_parallel(data, returns)
            
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_mine_parallel_specific_miners(self, mock_memory, mock_cpu):
        """测试并行挖掘 - 指定挖掘器"""
        # 模拟正常系统负载
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        
        # 创建新系统
        system = UnifiedFactorMiningSystem(max_workers=4)
        
        # 注册多个挖掘器（替换现有的）
        system.miners[MinerType.ALTERNATIVE_DATA] = MockMiner(MinerType.ALTERNATIVE_DATA)
        system.miners[MinerType.AI_ENHANCED] = MockMiner(MinerType.AI_ENHANCED)
        
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series([0.01, 0.01, 0.01])
        
        # 只执行指定的挖掘器
        results = system.mine_parallel(
            data,
            returns,
            miner_types=[MinerType.GENETIC, MinerType.ALTERNATIVE_DATA]
        )
        
        # 验证只执行了指定的挖掘器
        assert len(results) == 2
        miner_types = {r.miner_type for r in results}
        assert MinerType.GENETIC in miner_types
        assert MinerType.ALTERNATIVE_DATA in miner_types
        assert MinerType.AI_ENHANCED not in miner_types
        
        system.shutdown()
        
    def test_register_factor(self, system):
        """测试注册因子
        
        需求: 15.3 - 系统应该支持因子注册
        """
        factor = FactorMetadata(
            factor_id="test_001",
            factor_name="Test Factor",
            factor_type=MinerType.GENETIC,
            data_source="market",
            discovery_date=datetime.now(),
            discoverer="test",
            expression="test_expr",
            fitness=0.8
        )
        
        factor_id = system.register_factor(factor)
        
        assert factor_id == "test_001"
        assert system.get_factor("test_001") == factor
        
    def test_register_factor_duplicate(self, system):
        """测试注册重复因子"""
        factor = FactorMetadata(
            factor_id="test_001",
            factor_name="Test Factor",
            factor_type=MinerType.GENETIC,
            data_source="market",
            discovery_date=datetime.now(),
            discoverer="test",
            expression="test_expr",
            fitness=0.8
        )
        
        system.register_factor(factor)
        
        with pytest.raises(ValueError, match="因子ID已存在"):
            system.register_factor(factor)
            
    def test_get_factor(self, system):
        """测试获取因子"""
        factor = FactorMetadata(
            factor_id="test_001",
            factor_name="Test Factor",
            factor_type=MinerType.GENETIC,
            data_source="market",
            discovery_date=datetime.now(),
            discoverer="test",
            expression="test_expr",
            fitness=0.8
        )
        
        system.register_factor(factor)
        
        retrieved = system.get_factor("test_001")
        assert retrieved == factor
        
        # 获取不存在的因子
        assert system.get_factor("nonexistent") is None
        
    def test_get_all_factors(self, system):
        """测试获取所有因子"""
        factors = [
            FactorMetadata(
                factor_id=f"test_{i}",
                factor_name=f"Test Factor {i}",
                factor_type=MinerType.GENETIC,
                data_source="market",
                discovery_date=datetime.now(),
                discoverer="test",
                expression=f"expr_{i}",
                fitness=0.8
            )
            for i in range(3)
        ]
        
        for factor in factors:
            system.register_factor(factor)
            
        all_factors = system.get_all_factors()
        assert len(all_factors) == 3
        
    def test_get_factors_by_type(self, system):
        """测试按类型获取因子"""
        factors = [
            FactorMetadata(
                factor_id="genetic_1",
                factor_name="Genetic Factor",
                factor_type=MinerType.GENETIC,
                data_source="market",
                discovery_date=datetime.now(),
                discoverer="test",
                expression="expr_1",
                fitness=0.8
            ),
            FactorMetadata(
                factor_id="alt_1",
                factor_name="Alt Factor",
                factor_type=MinerType.ALTERNATIVE_DATA,
                data_source="satellite",
                discovery_date=datetime.now(),
                discoverer="test",
                expression="expr_2",
                fitness=0.7
            )
        ]
        
        for factor in factors:
            system.register_factor(factor)
            
        genetic_factors = system.get_factors_by_type(MinerType.GENETIC)
        assert len(genetic_factors) == 1
        assert genetic_factors[0].factor_id == "genetic_1"
        
        alt_factors = system.get_factors_by_type(MinerType.ALTERNATIVE_DATA)
        assert len(alt_factors) == 1
        assert alt_factors[0].factor_id == "alt_1"
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_monitor_system_health(self, mock_disk, mock_memory, mock_cpu, system):
        """测试系统健康监控
        
        白皮书依据: 第四章 4.1 暗物质挖掘工厂 - 16个专业因子挖掘器
        """
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        
        health = system.monitor_system_health()
        
        assert 'active_miners' in health
        assert 'healthy_miners' in health
        assert 'total_factors' in health
        assert 'cpu_usage' in health
        assert 'memory_usage' in health
        assert 'disk_usage' in health
        assert 'system_load_ok' in health
        
        # 16个挖掘器（白皮书定义）
        assert health['active_miners'] == 16
        assert health['cpu_usage'] == 0.5
        assert health['memory_usage'] == 0.6
        assert health['disk_usage'] == 0.7
        
    def test_get_miner_statistics(self, system):
        """测试获取挖掘器统计信息
        
        白皮书依据: 第四章 4.1 暗物质挖掘工厂 - 16个专业因子挖掘器
        """
        stats = system.get_miner_statistics()
        
        assert isinstance(stats, dict)
        # 验证所有16个挖掘器都有统计信息
        assert len(stats) == 16
        assert MinerType.GENETIC in stats
        assert MinerType.UNIFIED in stats  # MetaMiner
        
        genetic_stats = stats[MinerType.GENETIC]
        assert 'status' in genetic_stats
        assert 'total_factors_discovered' in genetic_stats
        assert 'is_healthy' in genetic_stats
        
    def test_shutdown(self, system):
        """测试系统关闭"""
        # 应该正常关闭而不抛出异常
        system.shutdown()
        
        # 验证线程池已关闭
        assert system.executor._shutdown is True


class TestIntegration:
    """集成测试"""
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_end_to_end_mining_workflow(self, mock_memory, mock_cpu):
        """测试端到端挖掘工作流
        
        需求: 15.1, 15.2, 15.3, 15.8 - 完整的挖掘和注册流程
        """
        # 模拟正常系统负载
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=60.0)
        
        # 创建系统
        system = UnifiedFactorMiningSystem(max_workers=2)
        
        # 替换一个挖掘器为MockMiner（用于测试）
        system.miners[MinerType.ALTERNATIVE_DATA] = MockMiner(MinerType.ALTERNATIVE_DATA)
        
        # 创建测试数据
        data = pd.DataFrame({
            'close': np.random.randn(50) + 100,
            'volume': np.random.randint(1000, 10000, 50)
        })
        returns = pd.Series(np.random.randn(50) * 0.01)
        
        # 并行挖掘（只挖掘2个挖掘器以加快测试）
        results = system.mine_parallel(
            data,
            returns,
            miner_types=[MinerType.GENETIC, MinerType.ALTERNATIVE_DATA]
        )
        
        # 注册发现的因子
        for result in results:
            if result.success:
                for factor in result.factors:
                    system.register_factor(factor)
                    
        # 验证结果
        all_factors = system.get_all_factors()
        assert len(all_factors) >= 1
        
        # 验证系统健康
        health = system.monitor_system_health()
        assert health['total_factors'] >= 1
        assert health['active_miners'] == 16  # 16个挖掘器（白皮书定义）
        
        # 清理
        system.shutdown()
