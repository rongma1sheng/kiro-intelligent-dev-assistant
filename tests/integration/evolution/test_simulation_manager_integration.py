"""模拟盘管理器集成测试

白皮书依据: 第四章 4.3.1 模拟盘验证标准

本模块测试模拟盘管理器与其他组件的集成，包括：
- 模拟盘启动和运行
- 多档位并行测试
- 风险监控集成
- 结果评估集成
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.evolution.multi_tier_simulation_manager import SimulationManager
from src.evolution.z2h_data_models import (
    CapitalTier,
    SimulationResult,
    TierSimulationResult
)


@pytest.fixture
def mock_broker_api():
    """创建Mock券商API"""
    from unittest.mock import AsyncMock, MagicMock
    from src.evolution.qmt_broker_api import BrokerSimulationAPI, SimulationStatus, SimulationData
    
    mock_api = AsyncMock(spec=BrokerSimulationAPI)
    
    # Mock create_simulation
    async def mock_create_simulation(strategy_code, initial_capital, duration_days):
        return f"sim_{initial_capital}_{datetime.now().timestamp()}"
    
    mock_api.create_simulation = mock_create_simulation
    
    # Mock get_simulation_data
    async def mock_get_simulation_data(simulation_id):
        data = MagicMock(spec=SimulationData)
        data.performance_metrics = {
            'total_profit': 5000,
            'sharpe_ratio': 2.5,
            'max_drawdown': 0.08,
            'win_rate': 0.65
        }
        data.daily_pnl = [100, 150, -50, 200, 120] * 6  # 30天数据
        data.trades = [
            {'profit': 100, 'symbol': '000001'},
            {'profit': 150, 'symbol': '000002'},
            {'profit': -50, 'symbol': '000003'}
        ]
        return data
    
    mock_api.get_simulation_data = mock_get_simulation_data
    
    # Mock get_simulation_status
    async def mock_get_simulation_status(simulation_id):
        status = MagicMock(spec=SimulationStatus)
        status.current_capital = 55000
        status.total_pnl = 5000
        status.position_count = 5
        status.status = "running"
        return status
    
    mock_api.get_simulation_status = mock_get_simulation_status
    
    # Mock stop_simulation
    async def mock_stop_simulation(simulation_id):
        return True
    
    mock_api.stop_simulation = mock_stop_simulation
    
    return mock_api


@pytest.fixture
def simulation_manager(mock_broker_api):
    """创建模拟盘管理器"""
    return SimulationManager(broker_api=mock_broker_api)


@pytest.fixture
def test_strategy_code():
    """创建测试策略代码"""
    return """
# 简单的动量策略
def on_bar(context, bar_dict):
    # 策略逻辑占位符
    pass
"""


class TestSimulationManagerIntegration:
    """模拟盘管理器集成测试"""
    
    @pytest.mark.asyncio
    async def test_start_and_run_simulation(
        self,
        simulation_manager,
        test_strategy_code
    ):
        """测试启动和运行模拟盘"""
        # 启动模拟盘
        simulation_instance = await simulation_manager.start_simulation(
            strategy_id="test_strategy_001",
            strategy_code=test_strategy_code,
            duration_days=30
        )
        
        # 验证模拟盘实例
        assert simulation_instance is not None
        assert simulation_instance.instance_id is not None
        assert simulation_instance.strategy_id == "test_strategy_001"
        assert simulation_instance.duration_days == 30
        assert simulation_instance.status == "running"
        
        # 运行多档位模拟
        tier_results = await simulation_manager.run_multi_tier_simulation(
            simulation_instance
        )
        
        # 验证所有档位都有结果
        assert len(tier_results) == 4
        assert CapitalTier.TIER_1 in tier_results
        assert CapitalTier.TIER_2 in tier_results
        assert CapitalTier.TIER_3 in tier_results
        assert CapitalTier.TIER_4 in tier_results
        
        # 验证每个档位的结果
        for tier, result in tier_results.items():
            assert isinstance(result, TierSimulationResult)
            assert result.tier == tier
            assert result.initial_capital > 0
            assert result.final_capital > 0

    
    @pytest.mark.asyncio
    async def test_risk_monitoring_integration(
        self,
        simulation_manager,
        test_strategy_code
    ):
        """测试风险监控集成"""
        # 启动模拟盘
        simulation_instance = await simulation_manager.start_simulation(
            strategy_id="test_strategy_002",
            strategy_code=test_strategy_code,
            duration_days=30
        )
        
        # 运行模拟
        tier_results = await simulation_manager.run_multi_tier_simulation(
            simulation_instance
        )
        
        # 监控风险
        risk_monitoring = await simulation_manager.monitor_simulation_risk(
            simulation_instance
        )
        
        # 验证风险监控结果
        assert risk_monitoring is not None
        assert 'risk_alerts' in risk_monitoring
        assert 'tier_risks' in risk_monitoring
        assert 'instance_id' in risk_monitoring
    
    @pytest.mark.asyncio
    async def test_simulation_result_evaluation(
        self,
        simulation_manager,
        test_strategy_code
    ):
        """测试模拟盘结果评估"""
        # 启动模拟盘
        simulation_instance = await simulation_manager.start_simulation(
            strategy_id="test_strategy_003",
            strategy_code=test_strategy_code,
            duration_days=30
        )
        
        # 运行模拟
        tier_results = await simulation_manager.run_multi_tier_simulation(
            simulation_instance
        )
        
        # 评估结果
        simulation_result = await simulation_manager.evaluate_simulation_result(
            simulation_instance,
            tier_results
        )
        
        # 验证评估结果
        assert isinstance(simulation_result, SimulationResult)
        assert simulation_result.duration_days == 30
        assert simulation_result.best_tier in [
            CapitalTier.TIER_1,
            CapitalTier.TIER_2,
            CapitalTier.TIER_3,
            CapitalTier.TIER_4
        ]
        assert 0 <= simulation_result.passed_criteria_count <= 10
        
        # 如果通过，验证通过标准数量（至少8项）
        if simulation_result.passed:
            assert simulation_result.passed_criteria_count >= 8
        else:
            assert len(simulation_result.failed_criteria) > 0
    
    @pytest.mark.asyncio
    async def test_multi_tier_parallel_execution(
        self,
        simulation_manager,
        test_strategy_code
    ):
        """测试多档位并行执行"""
        # 启动模拟盘
        simulation_instance = await simulation_manager.start_simulation(
            strategy_id="test_strategy_004",
            strategy_code=test_strategy_code,
            duration_days=30
        )
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        # 运行多档位模拟
        tier_results = await simulation_manager.run_multi_tier_simulation(
            simulation_instance
        )
        
        # 记录结束时间
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 验证并行执行效率（应该比串行快）
        # 假设每个档位串行需要1秒，并行应该接近1秒而不是4秒
        assert elapsed_time < 3.0  # 允许一定的开销
        
        # 验证所有档位都完成
        assert len(tier_results) == 4
    
    @pytest.mark.asyncio
    async def test_simulation_with_different_durations(
        self,
        simulation_manager,
        test_strategy_code
    ):
        """测试不同持续时间的模拟盘"""
        durations = [7, 14, 30]
        
        for duration in durations:
            # 启动模拟盘
            simulation_instance = await simulation_manager.start_simulation(
                strategy_id=f"test_strategy_duration_{duration}",
                strategy_code=test_strategy_code,
                duration_days=duration
            )
            
            # 验证持续时间设置
            assert simulation_instance.duration_days == duration
            
            # 运行模拟
            tier_results = await simulation_manager.run_multi_tier_simulation(
                simulation_instance
            )
            
            # 验证结果
            assert len(tier_results) == 4
    
    @pytest.mark.asyncio
    async def test_simulation_error_handling(
        self,
        simulation_manager
    ):
        """测试模拟盘错误处理"""
        # 测试无效策略代码
        with pytest.raises(ValueError, match="strategy_code不能为空"):
            await simulation_manager.start_simulation(
                strategy_id="test_strategy_invalid",
                strategy_code="",
                duration_days=30
            )
        
        # 测试无效持续时间
        with pytest.raises(ValueError, match="duration_days必须大于0"):
            await simulation_manager.start_simulation(
                strategy_id="test_strategy_invalid",
                strategy_code="# code",
                duration_days=0
            )
