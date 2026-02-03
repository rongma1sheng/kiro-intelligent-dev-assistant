"""模拟盘管理器单元测试

白皮书依据: 第四章 4.3.1 模拟盘验证标准

测试模拟盘管理器的核心功能：
- 30天模拟盘启动
- 每日数据记录
- 风险监控
- 止损触发和暂停
- 10项达标标准评估

Requirements: 6.1, 6.3, 6.4, 6.5, 6.7
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

from src.evolution.multi_tier_simulation_manager import (
    SimulationManager,
    SimulationInstance
)
from src.evolution.z2h_data_models import (
    CapitalTier,
    TierSimulationResult,
    SimulationResult
)
from src.evolution.qmt_broker_api import (
    BrokerSimulationAPI,
    SimulationStatus,
    SimulationData
)


class TestSimulationManagerUnit:
    """模拟盘管理器单元测试
    
    白皮书依据: 第四章 4.3.1 模拟盘验证标准
    """
    
    @pytest.fixture
    def mock_broker_api(self):
        """创建模拟券商API"""
        api = AsyncMock(spec=BrokerSimulationAPI)
        return api
    
    @pytest.fixture
    def simulation_manager(self, mock_broker_api):
        """创建模拟盘管理器实例"""
        return SimulationManager(broker_api=mock_broker_api)
    
    @pytest.fixture
    def sample_simulation_instance(self):
        """创建示例模拟盘实例"""
        return SimulationInstance(
            instance_id="sim_test_20260120120000",
            strategy_id="test_strategy",
            strategy_code="def strategy(): pass",
            tier_simulations={
                CapitalTier.TIER_1: "sim_tier1_001",
                CapitalTier.TIER_2: "sim_tier2_001",
                CapitalTier.TIER_3: "sim_tier3_001",
                CapitalTier.TIER_4: "sim_tier4_001"
            },
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),
            duration_days=30,
            status="running"
        )
    
    # ==================== 任务6.1: 30天模拟盘启动 ====================
    
    @pytest.mark.asyncio
    async def test_30_day_simulation_startup_success(
        self,
        simulation_manager,
        mock_broker_api
    ):
        """测试30天模拟盘成功启动
        
        Requirements: 6.1
        """
        # 配置mock
        mock_broker_api.create_simulation.return_value = "sim_001"
        
        # 启动模拟盘
        instance = await simulation_manager.start_simulation(
            strategy_id="test_strategy",
            strategy_code="def strategy(): pass",
            duration_days=30
        )
        
        # 验证实例创建
        assert instance is not None
        assert instance.strategy_id == "test_strategy"
        assert instance.duration_days == 30
        assert instance.status == "running"
        
        # 验证四个档位都创建了模拟盘
        assert len(instance.tier_simulations) == 4
        assert CapitalTier.TIER_1 in instance.tier_simulations
        assert CapitalTier.TIER_2 in instance.tier_simulations
        assert CapitalTier.TIER_3 in instance.tier_simulations
        assert CapitalTier.TIER_4 in instance.tier_simulations
        
        # 验证API调用次数
        assert mock_broker_api.create_simulation.call_count == 4
    
    @pytest.mark.asyncio
    async def test_simulation_startup_with_custom_duration(
        self,
        simulation_manager,
        mock_broker_api
    ):
        """测试自定义天数的模拟盘启动
        
        Requirements: 6.1
        """
        mock_broker_api.create_simulation.return_value = "sim_002"
        
        # 启动60天模拟盘
        instance = await simulation_manager.start_simulation(
            strategy_id="test_strategy",
            strategy_code="def strategy(): pass",
            duration_days=60
        )
        
        assert instance.duration_days == 60
        assert (instance.end_date - instance.start_date).days == 60
    
    @pytest.mark.asyncio
    async def test_simulation_startup_invalid_parameters(
        self,
        simulation_manager
    ):
        """测试无效参数时启动失败
        
        Requirements: 6.1
        """
        # 空策略ID
        with pytest.raises(ValueError, match="strategy_id不能为空"):
            await simulation_manager.start_simulation(
                strategy_id="",
                strategy_code="def strategy(): pass"
            )
        
        # 空策略代码
        with pytest.raises(ValueError, match="strategy_code不能为空"):
            await simulation_manager.start_simulation(
                strategy_id="test",
                strategy_code=""
            )
        
        # 无效天数
        with pytest.raises(ValueError, match="duration_days必须大于0"):
            await simulation_manager.start_simulation(
                strategy_id="test",
                strategy_code="def strategy(): pass",
                duration_days=0
            )
    
    @pytest.mark.asyncio
    async def test_simulation_startup_api_failure(
        self,
        simulation_manager,
        mock_broker_api
    ):
        """测试API失败时的错误处理
        
        Requirements: 6.1
        """
        # 配置API抛出异常
        mock_broker_api.create_simulation.side_effect = Exception("API连接失败")
        
        # 验证抛出RuntimeError
        with pytest.raises(RuntimeError, match="启动模拟盘失败"):
            await simulation_manager.start_simulation(
                strategy_id="test",
                strategy_code="def strategy(): pass"
            )
    
    # ==================== 任务6.3: 风险监控 ====================
    
    @pytest.mark.asyncio
    async def test_risk_monitoring_normal_operation(
        self,
        simulation_manager,
        mock_broker_api,
        sample_simulation_instance
    ):
        """测试正常运行时的风险监控
        
        Requirements: 6.4
        """
        # 配置mock返回正常状态
        mock_status = MagicMock(spec=SimulationStatus)
        mock_status.current_capital = 5500
        mock_status.total_pnl = 500
        mock_status.position_count = 5
        mock_status.status = "running"
        
        mock_broker_api.get_simulation_status.return_value = mock_status
        
        # 监控风险
        result = await simulation_manager.monitor_simulation_risk(
            sample_simulation_instance
        )
        
        # 验证结果
        assert result['instance_id'] == sample_simulation_instance.instance_id
        assert len(result['risk_alerts']) == 0  # 无风险告警
        assert len(result['tier_risks']) == 4  # 四个档位都有数据
    
    @pytest.mark.asyncio
    async def test_risk_monitoring_high_drawdown_alert(
        self,
        simulation_manager,
        mock_broker_api,
        sample_simulation_instance
    ):
        """测试高回撤告警
        
        Requirements: 6.4, 6.5
        
        注意：回撤比例是相对于各档位的初始资金计算的。
        TIER_1初始资金5000，total_pnl=-1500时回撤30%，触发止损。
        其他档位初始资金更大，同样的total_pnl不会触发止损。
        """
        # 配置mock返回高回撤状态（相对于TIER_1的5000初始资金）
        mock_status = MagicMock(spec=SimulationStatus)
        mock_status.current_capital = 3500
        mock_status.total_pnl = -1500  # 对于TIER_1(5000)是30%回撤
        mock_status.position_count = 3
        mock_status.status = "running"
        
        mock_broker_api.get_simulation_status.return_value = mock_status
        
        # 监控风险
        result = await simulation_manager.monitor_simulation_risk(
            sample_simulation_instance
        )
        
        # 验证告警 - 只有TIER_1会触发（1500/5000=30%>20%）
        # 其他档位：TIER_2(1500/50000=3%), TIER_3(1500/250000=0.6%), TIER_4(1500/750000=0.2%)
        assert len(result['risk_alerts']) >= 1
        
        # 验证告警内容
        alert = result['risk_alerts'][0]
        assert alert['type'] == 'high_drawdown'
        assert alert['value'] > 0.20
        assert alert['action'] == 'pause'
        
        # 验证暂停调用 - 只有TIER_1触发止损
        assert mock_broker_api.stop_simulation.call_count == 1
    
    @pytest.mark.asyncio
    async def test_risk_monitoring_multiple_tiers(
        self,
        simulation_manager,
        mock_broker_api,
        sample_simulation_instance
    ):
        """测试多档位风险监控
        
        Requirements: 6.4
        
        注意：tier_risks的key使用CapitalTier.value，即小写的'tier_1'等。
        """
        # 配置不同档位返回不同状态
        def get_status_side_effect(simulation_id):
            status = MagicMock(spec=SimulationStatus)
            if "tier1" in simulation_id:
                status.current_capital = 5500
                status.total_pnl = 500
            elif "tier2" in simulation_id:
                status.current_capital = 48000
                status.total_pnl = -2000
            elif "tier3" in simulation_id:
                status.current_capital = 260000
                status.total_pnl = 10000
            else:  # tier4
                status.current_capital = 700000
                status.total_pnl = -50000
            status.position_count = 5
            status.status = "running"
            return status
        
        mock_broker_api.get_simulation_status.side_effect = get_status_side_effect
        
        # 监控风险
        result = await simulation_manager.monitor_simulation_risk(
            sample_simulation_instance
        )
        
        # 验证所有档位都被监控（使用小写的tier.value作为key）
        assert len(result['tier_risks']) == 4
        assert 'tier_1' in result['tier_risks']
        assert 'tier_2' in result['tier_risks']
        assert 'tier_3' in result['tier_risks']
        assert 'tier_4' in result['tier_risks']
    
    # ==================== 任务6.5: 止损触发和暂停 ====================
    
    @pytest.mark.asyncio
    async def test_stop_loss_trigger_at_20_percent(
        self,
        simulation_manager,
        mock_broker_api,
        sample_simulation_instance
    ):
        """测试20%回撤触发止损
        
        Requirements: 6.5
        
        注意：回撤比例是相对于各档位的初始资金计算的。
        total_pnl=-1000对于TIER_1(5000)是20%回撤，刚好触发止损（>20%才触发）。
        源代码使用 > 0.20 判断，所以精确20%不会触发。
        需要设置略高于20%的回撤才能触发。
        """
        # 配置mock返回略高于20%的回撤（对于TIER_1的5000初始资金）
        mock_status = MagicMock(spec=SimulationStatus)
        mock_status.current_capital = 3900
        mock_status.total_pnl = -1100  # 对于TIER_1(5000)是22%回撤，>20%触发
        mock_status.position_count = 2
        mock_status.status = "running"
        
        mock_broker_api.get_simulation_status.return_value = mock_status
        
        # 监控风险
        result = await simulation_manager.monitor_simulation_risk(
            sample_simulation_instance
        )
        
        # 验证触发止损 - 只有TIER_1会触发（1100/5000=22%>20%）
        # 其他档位：TIER_2(1100/50000=2.2%), TIER_3(1100/250000=0.44%), TIER_4(1100/750000=0.15%)
        assert len(result['risk_alerts']) >= 1
        
        # 验证暂停调用 - 只有TIER_1触发止损
        assert mock_broker_api.stop_simulation.call_count == 1
    
    @pytest.mark.asyncio
    async def test_stop_loss_not_triggered_below_threshold(
        self,
        simulation_manager,
        mock_broker_api,
        sample_simulation_instance
    ):
        """测试低于阈值时不触发止损
        
        Requirements: 6.5
        """
        # 配置mock返回19%回撤（低于阈值）
        mock_status = MagicMock(spec=SimulationStatus)
        mock_status.current_capital = 4100
        mock_status.total_pnl = -900  # 18%回撤
        mock_status.position_count = 3
        mock_status.status = "running"
        
        mock_broker_api.get_simulation_status.return_value = mock_status
        
        # 监控风险
        result = await simulation_manager.monitor_simulation_risk(
            sample_simulation_instance
        )
        
        # 验证不触发止损
        assert len(result['risk_alerts']) == 0
        assert mock_broker_api.stop_simulation.call_count == 0
    
    # ==================== 任务6.7: 10项达标标准评估 ====================
    
    @pytest.mark.asyncio
    async def test_10_criteria_evaluation_all_pass(
        self,
        simulation_manager,
        sample_simulation_instance
    ):
        """测试所有标准都通过
        
        Requirements: 6.7
        """
        # 创建优秀的档位结果
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=5500,
                total_return=0.10,  # 10%收益
                sharpe_ratio=2.0,   # 优秀
                max_drawdown=0.08,  # 8%回撤
                win_rate=0.65,      # 65%胜率
                profit_factor=2.0,  # 优秀
                var_95=0.03,        # 3% VaR
                calmar_ratio=1.25,  # 优秀
                information_ratio=1.5,  # 优秀
                daily_pnl=[10, 20, -5, 15, 30],
                trades=[]
            )
        }
        
        # 添加其他档位（简化）
        for tier in [CapitalTier.TIER_2, CapitalTier.TIER_3, CapitalTier.TIER_4]:
            tier_results[tier] = tier_results[CapitalTier.TIER_1]
        
        # 评估结果
        result = await simulation_manager.evaluate_simulation_result(
            sample_simulation_instance,
            tier_results
        )
        
        # 验证通过
        assert result.passed is True
        assert result.passed_criteria_count >= 8  # 至少8项通过
        assert len(result.failed_criteria) <= 2
    
    @pytest.mark.asyncio
    async def test_10_criteria_evaluation_partial_pass(
        self,
        simulation_manager,
        sample_simulation_instance
    ):
        """测试部分标准通过
        
        Requirements: 6.7
        """
        # 创建中等表现的档位结果
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=5250,
                total_return=0.05,  # 5%收益（刚好达标）
                sharpe_ratio=1.2,   # 刚好达标
                max_drawdown=0.15,  # 15%回撤（刚好达标）
                win_rate=0.55,      # 55%胜率（刚好达标）
                profit_factor=1.3,  # 刚好达标
                var_95=0.05,        # 5% VaR（刚好达标）
                calmar_ratio=0.33,  # 未达标
                information_ratio=0.5,  # 未达标
                daily_pnl=[5, 10, -3, 8, 15],
                trades=[]
            )
        }
        
        for tier in [CapitalTier.TIER_2, CapitalTier.TIER_3, CapitalTier.TIER_4]:
            tier_results[tier] = tier_results[CapitalTier.TIER_1]
        
        # 评估结果
        result = await simulation_manager.evaluate_simulation_result(
            sample_simulation_instance,
            tier_results
        )
        
        # 验证通过（至少8项）
        assert result.passed is True
        assert result.passed_criteria_count >= 8
    
    @pytest.mark.asyncio
    async def test_10_criteria_evaluation_fail(
        self,
        simulation_manager,
        sample_simulation_instance
    ):
        """测试未达标情况
        
        Requirements: 6.7
        """
        # 创建表现不佳的档位结果
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=4800,
                total_return=-0.04,  # 负收益
                sharpe_ratio=0.5,    # 低夏普
                max_drawdown=0.25,   # 高回撤
                win_rate=0.40,       # 低胜率
                profit_factor=0.8,   # 低盈利因子
                var_95=0.10,         # 高VaR
                calmar_ratio=-0.16,  # 负值
                information_ratio=0.2,  # 低信息比率
                daily_pnl=[-10, -20, 5, -15, -30],
                trades=[]
            )
        }
        
        for tier in [CapitalTier.TIER_2, CapitalTier.TIER_3, CapitalTier.TIER_4]:
            tier_results[tier] = tier_results[CapitalTier.TIER_1]
        
        # 评估结果
        result = await simulation_manager.evaluate_simulation_result(
            sample_simulation_instance,
            tier_results
        )
        
        # 验证未通过
        assert result.passed is False
        assert result.passed_criteria_count < 8
        assert len(result.failed_criteria) > 2
    
    @pytest.mark.asyncio
    async def test_criteria_evaluation_boundary_values(
        self,
        simulation_manager,
        sample_simulation_instance
    ):
        """测试边界值情况
        
        Requirements: 6.7
        """
        # 创建边界值档位结果
        tier_results = {
            CapitalTier.TIER_1: TierSimulationResult(
                tier=CapitalTier.TIER_1,
                initial_capital=5000,
                final_capital=5250,
                total_return=0.05,   # 精确5%
                sharpe_ratio=1.2,    # 精确1.2
                max_drawdown=0.15,   # 精确15%
                win_rate=0.55,       # 精确55%
                profit_factor=1.3,   # 精确1.3
                var_95=0.05,         # 精确5%
                calmar_ratio=1.0,    # 精确1.0
                information_ratio=0.8,  # 精确0.8
                daily_pnl=[5, 10, -3, 8, 15],
                trades=[]
            )
        }
        
        for tier in [CapitalTier.TIER_2, CapitalTier.TIER_3, CapitalTier.TIER_4]:
            tier_results[tier] = tier_results[CapitalTier.TIER_1]
        
        # 评估结果
        result = await simulation_manager.evaluate_simulation_result(
            sample_simulation_instance,
            tier_results
        )
        
        # 验证边界值被正确处理
        assert result.passed is True
        assert result.passed_criteria_count >= 8
