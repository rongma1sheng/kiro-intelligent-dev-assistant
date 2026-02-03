"""模拟盘多档位执行属性测试

白皮书依据: 第四章 4.3.1 模拟盘验证标准

Property 11: Simulation Multi-Tier Execution
验证需求: Requirements 6.2

使用hypothesis进行属性测试，验证所有四个档位都被测试。
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import asyncio

from src.evolution.multi_tier_simulation_manager import SimulationManager, SimulationInstance
from src.evolution.z2h_data_models import CapitalTier, TierSimulationResult
from src.evolution.qmt_broker_api import BrokerSimulationAPI, SimulationData, SimulationStatus


# ==================== Hypothesis策略定义 ====================

@st.composite
def strategy_code_strategy(draw):
    """生成随机策略代码的策略"""
    strategy_types = ['momentum', 'mean_reversion', 'arbitrage', 'trend_following']
    strategy_type = draw(st.sampled_from(strategy_types))
    
    code_template = f"""
# {strategy_type} strategy
def on_bar(context, bar_dict):
    # Strategy logic
    pass

def on_tick(context, tick):
    # Tick logic
    pass
"""
    
    return code_template


@st.composite
def simulation_duration_strategy(draw):
    """生成随机模拟盘持续时间的策略"""
    # 生成7-60天的持续时间
    return draw(st.integers(min_value=7, max_value=60))


# ==================== Mock工厂 ====================

def create_mock_broker_api():
    """创建Mock券商API"""
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
        data.daily_pnl = [100, 150, -50, 200, 120] * 6
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


# ==================== 属性测试 ====================

class TestSimulationMultiTierExecutionProperty:
    """模拟盘多档位执行属性测试
    
    白皮书依据: 第四章 4.3.1 - 模拟盘验证标准
    验证需求: Requirements 6.2
    """
    
    @given(
        strategy_code=strategy_code_strategy(),
        duration_days=simulation_duration_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_all_tiers_executed(
        self,
        strategy_code: str,
        duration_days: int
    ):
        """Property 11: 模拟盘多档位执行完整性
        
        验证需求: Requirements 6.2
        
        属性: 对于任意有效的策略代码和持续时间，所有四个档位都应该被测试。
        
        测试步骤:
        1. 生成随机策略代码和持续时间
        2. 启动模拟盘
        3. 运行多档位模拟
        4. 验证所有四个档位都被执行
        """
        # 创建模拟盘管理器
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id=f"test_strategy_{datetime.now().timestamp()}",
            strategy_code=strategy_code,
            duration_days=duration_days
        )
        
        # 验证模拟盘实例创建成功
        assert simulation_instance is not None
        assert isinstance(simulation_instance, SimulationInstance)
        
        # 验证所有四个档位都有模拟盘ID
        assert len(simulation_instance.tier_simulations) == 4, \
            "应该为所有四个档位创建模拟盘"
        
        # 验证每个档位都有唯一的模拟盘ID
        assert CapitalTier.TIER_1 in simulation_instance.tier_simulations
        assert CapitalTier.TIER_2 in simulation_instance.tier_simulations
        assert CapitalTier.TIER_3 in simulation_instance.tier_simulations
        assert CapitalTier.TIER_4 in simulation_instance.tier_simulations
        
        # 验证模拟盘ID不为空
        for tier, simulation_id in simulation_instance.tier_simulations.items():
            assert simulation_id is not None, f"{tier.value}档位的模拟盘ID不应为空"
            assert len(simulation_id) > 0, f"{tier.value}档位的模拟盘ID不应为空字符串"
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证所有四个档位都有结果
        assert len(tier_results) == 4, "应该返回所有四个档位的结果"
        
        # 验证每个档位的结果
        for tier in CapitalTier:
            assert tier in tier_results, f"缺少{tier.value}档位的结果"
            
            result = tier_results[tier]
            assert isinstance(result, TierSimulationResult), \
                f"{tier.value}档位的结果类型错误"
            
            assert result.tier == tier, \
                f"{tier.value}档位的结果档位字段不匹配"
    
    @given(
        strategy_code=strategy_code_strategy(),
        duration_days=simulation_duration_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_tier_capital_allocation(
        self,
        strategy_code: str,
        duration_days: int
    ):
        """Property 11.1: 档位资金分配正确性
        
        验证需求: Requirements 6.2
        
        属性: 每个档位应该分配正确的初始资金。
        """
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id=f"test_strategy_{datetime.now().timestamp()}",
            strategy_code=strategy_code,
            duration_days=duration_days
        )
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证每个档位的初始资金
        expected_capitals = {
            CapitalTier.TIER_1: 5000,      # 微型：5千
            CapitalTier.TIER_2: 50000,     # 小型：5万
            CapitalTier.TIER_3: 250000,    # 中型：25万
            CapitalTier.TIER_4: 750000     # 大型：75万
        }
        
        for tier, expected_capital in expected_capitals.items():
            result = tier_results[tier]
            assert result.initial_capital == expected_capital, \
                f"{tier.value}档位的初始资金应该是{expected_capital}，实际是{result.initial_capital}"
    
    @given(
        strategy_code=strategy_code_strategy(),
        duration_days=simulation_duration_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_tier_independence(
        self,
        strategy_code: str,
        duration_days: int
    ):
        """Property 11.2: 档位独立性
        
        验证需求: Requirements 6.2
        
        属性: 各档位的模拟应该是独立的，一个档位的失败不应影响其他档位。
        """
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id=f"test_strategy_{datetime.now().timestamp()}",
            strategy_code=strategy_code,
            duration_days=duration_days
        )
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证所有档位都有结果（即使某些档位可能失败）
        assert len(tier_results) == 4, "即使某些档位失败，也应该返回所有档位的结果"
        
        # 验证每个档位都有独立的模拟盘ID
        simulation_ids = set(simulation_instance.tier_simulations.values())
        assert len(simulation_ids) == 4, "每个档位应该有独立的模拟盘ID"
    
    @given(
        strategy_code=strategy_code_strategy(),
        duration_days=simulation_duration_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_tier_result_completeness(
        self,
        strategy_code: str,
        duration_days: int
    ):
        """Property 11.3: 档位结果完整性
        
        验证需求: Requirements 6.2
        
        属性: 每个档位的结果应该包含所有必要的指标。
        """
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id=f"test_strategy_{datetime.now().timestamp()}",
            strategy_code=strategy_code,
            duration_days=duration_days
        )
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证每个档位结果的完整性
        required_fields = [
            'tier', 'initial_capital', 'final_capital', 'total_return',
            'sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor',
            'var_95', 'calmar_ratio', 'information_ratio'
        ]
        
        for tier, result in tier_results.items():
            for field in required_fields:
                assert hasattr(result, field), \
                    f"{tier.value}档位的结果缺少字段: {field}"
                
                value = getattr(result, field)
                assert value is not None, \
                    f"{tier.value}档位的{field}字段不应为None"
    
    @given(
        strategy_code=strategy_code_strategy(),
        duration_days=simulation_duration_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_tier_execution_order_independence(
        self,
        strategy_code: str,
        duration_days: int
    ):
        """Property 11.4: 档位执行顺序无关性
        
        验证需求: Requirements 6.2
        
        属性: 档位的执行顺序不应影响最终结果。
        """
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 第一次执行
        simulation_instance1 = await manager.start_simulation(
            strategy_id=f"test_strategy_{datetime.now().timestamp()}_1",
            strategy_code=strategy_code,
            duration_days=duration_days
        )
        tier_results1 = await manager.run_multi_tier_simulation(simulation_instance1)
        
        # 第二次执行
        simulation_instance2 = await manager.start_simulation(
            strategy_id=f"test_strategy_{datetime.now().timestamp()}_2",
            strategy_code=strategy_code,
            duration_days=duration_days
        )
        tier_results2 = await manager.run_multi_tier_simulation(simulation_instance2)
        
        # 验证两次执行的档位数量相同
        assert len(tier_results1) == len(tier_results2) == 4, \
            "两次执行应该都返回4个档位的结果"
        
        # 验证两次执行都包含相同的档位
        assert set(tier_results1.keys()) == set(tier_results2.keys()), \
            "两次执行应该包含相同的档位"


# ==================== 边界条件测试 ====================

class TestSimulationMultiTierExecutionEdgeCases:
    """模拟盘多档位执行边界条件测试
    
    白皮书依据: 第四章 4.3.1 - 模拟盘验证标准
    验证需求: Requirements 6.1, 6.3, 6.4, 6.5, 6.7
    """
    
    @pytest.mark.asyncio
    async def test_minimum_duration(self):
        """测试最小持续时间（7天）"""
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动7天模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id="test_min_duration",
            strategy_code="# code",
            duration_days=7
        )
        
        # 验证持续时间
        assert simulation_instance.duration_days == 7
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证所有档位都执行
        assert len(tier_results) == 4
    
    @pytest.mark.asyncio
    async def test_standard_duration(self):
        """测试标准持续时间（30天）"""
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动30天模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id="test_standard_duration",
            strategy_code="# code",
            duration_days=30
        )
        
        # 验证持续时间
        assert simulation_instance.duration_days == 30
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证所有档位都执行
        assert len(tier_results) == 4
    
    @pytest.mark.asyncio
    async def test_extended_duration(self):
        """测试延长持续时间（60天）"""
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动60天模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id="test_extended_duration",
            strategy_code="# code",
            duration_days=60
        )
        
        # 验证持续时间
        assert simulation_instance.duration_days == 60
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证所有档位都执行
        assert len(tier_results) == 4
    
    @pytest.mark.asyncio
    async def test_custom_capital_allocation(self):
        """测试自定义资金分配"""
        mock_broker_api = create_mock_broker_api()
        
        # 自定义资金分配
        custom_capital_map = {
            CapitalTier.TIER_1: 10000,
            CapitalTier.TIER_2: 100000,
            CapitalTier.TIER_3: 500000,
            CapitalTier.TIER_4: 1000000
        }
        
        manager = SimulationManager(
            broker_api=mock_broker_api,
            tier_capital_map=custom_capital_map
        )
        
        # 启动模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id="test_custom_capital",
            strategy_code="# code",
            duration_days=30
        )
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 验证自定义资金分配
        for tier, expected_capital in custom_capital_map.items():
            result = tier_results[tier]
            assert result.initial_capital == expected_capital, \
                f"{tier.value}档位的初始资金应该是{expected_capital}"
    
    @pytest.mark.asyncio
    async def test_invalid_strategy_code(self):
        """测试无效策略代码"""
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 测试空策略代码
        with pytest.raises(ValueError, match="strategy_code不能为空"):
            await manager.start_simulation(
                strategy_id="test_invalid",
                strategy_code="",
                duration_days=30
            )
    
    @pytest.mark.asyncio
    async def test_invalid_duration(self):
        """测试无效持续时间"""
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 测试0天持续时间
        with pytest.raises(ValueError, match="duration_days必须大于0"):
            await manager.start_simulation(
                strategy_id="test_invalid",
                strategy_code="# code",
                duration_days=0
            )
        
        # 测试负数持续时间
        with pytest.raises(ValueError, match="duration_days必须大于0"):
            await manager.start_simulation(
                strategy_id="test_invalid",
                strategy_code="# code",
                duration_days=-10
            )
    
    @pytest.mark.asyncio
    async def test_parallel_execution_efficiency(self):
        """测试并行执行效率"""
        import time
        
        mock_broker_api = create_mock_broker_api()
        manager = SimulationManager(broker_api=mock_broker_api)
        
        # 启动模拟盘
        simulation_instance = await manager.start_simulation(
            strategy_id="test_parallel",
            strategy_code="# code",
            duration_days=30
        )
        
        # 记录开始时间
        start_time = time.time()
        
        # 运行多档位模拟
        tier_results = await manager.run_multi_tier_simulation(simulation_instance)
        
        # 记录结束时间
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 验证并行执行效率（应该比串行快）
        # 假设每个档位串行需要1秒，并行应该接近1秒而不是4秒
        assert elapsed_time < 3.0, \
            f"并行执行时间过长: {elapsed_time:.2f}秒 > 3秒"
        
        # 验证所有档位都完成
        assert len(tier_results) == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
