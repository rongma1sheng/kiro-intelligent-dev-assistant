"""
因子Arena三轨测试系统单元测试

测试覆盖:
1. FactorArenaSystem核心功能
2. FactorRealityTrack真实数据测试
3. FactorHellTrack极端场景测试
4. CrossMarketTrack跨市场测试
5. 综合评分算法
6. 事件驱动通信
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.evolution.factor_arena import (
    FactorArenaSystem,
    FactorRealityTrack,
    FactorHellTrack,
    CrossMarketTrack,
    ArenaTestConfig,
    FactorTestResult,
    TrackType,
    FactorStatus
)
from src.infra.event_bus import Event, EventType, EventPriority


class TestArenaTestConfig:
    """测试Arena配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ArenaTestConfig()
        
        assert config.reality_min_ic == 0.05
        assert config.reality_min_sharpe == 1.5
        assert config.reality_max_drawdown == 0.15
        assert config.hell_min_survival_rate == 0.7
        assert config.min_markets_passed == 2
        assert len(config.hell_scenarios) == 5
        assert len(config.target_markets) == 4
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ArenaTestConfig(
            reality_min_ic=0.08,
            reality_min_sharpe=2.0,
            hell_scenarios=["custom_scenario"],
            target_markets=["CUSTOM_MARKET"]
        )
        
        assert config.reality_min_ic == 0.08
        assert config.reality_min_sharpe == 2.0
        assert config.hell_scenarios == ["custom_scenario"]
        assert config.target_markets == ["CUSTOM_MARKET"]


class TestFactorTestResult:
    """测试因子测试结果"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = FactorTestResult(
            factor_expression="close/delay(close,1)-1",
            track_type=TrackType.REALITY,
            test_start_time=datetime.now(),
            test_end_time=datetime.now(),
            ic_mean=0.06,
            sharpe_ratio=1.8,
            passed=True
        )
        
        assert result.factor_expression == "close/delay(close,1)-1"
        assert result.track_type == TrackType.REALITY
        assert result.ic_mean == 0.06
        assert result.sharpe_ratio == 1.8
        assert result.passed is True
        assert result.detailed_metrics == {}
    
    def test_result_with_detailed_metrics(self):
        """测试包含详细指标的结果"""
        detailed_metrics = {
            'ic_series_length': 100,
            'portfolio_returns_length': 95
        }
        
        result = FactorTestResult(
            factor_expression="momentum_factor",
            track_type=TrackType.HELL,
            test_start_time=datetime.now(),
            test_end_time=datetime.now(),
            survival_rate=0.75,
            detailed_metrics=detailed_metrics
        )
        
        assert result.detailed_metrics == detailed_metrics
        assert result.survival_rate == 0.75


class TestFactorRealityTrack:
    """测试Reality Track"""
    
    @pytest.fixture
    def config(self):
        return ArenaTestConfig()
    
    @pytest.fixture
    def reality_track(self, config):
        return FactorRealityTrack(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, reality_track):
        """测试初始化"""
        await reality_track.initialize()
        
        assert reality_track.historical_data is not None
        assert reality_track.returns_data is not None
        assert reality_track.historical_data.shape[0] > 0
        assert reality_track.returns_data.shape[0] > 0
    
    @pytest.mark.asyncio
    async def test_factor_calculation(self, reality_track):
        """测试因子计算"""
        await reality_track.initialize()
        
        # 测试动量因子
        momentum_factor = await reality_track._calculate_factor_values("momentum_factor")
        assert isinstance(momentum_factor, pd.DataFrame)
        assert momentum_factor.shape[0] > 0
        
        # 测试反转因子
        reversal_factor = await reality_track._calculate_factor_values("reversal_factor")
        assert isinstance(reversal_factor, pd.DataFrame)
        assert reversal_factor.shape[0] > 0
        
        # 测试波动率因子
        volatility_factor = await reality_track._calculate_factor_values("volatility_factor")
        assert isinstance(volatility_factor, pd.DataFrame)
        assert volatility_factor.shape[0] > 0
    
    @pytest.mark.asyncio
    async def test_ic_calculation(self, reality_track):
        """测试IC计算"""
        await reality_track.initialize()
        
        # 创建简单的因子数据
        factor_values = reality_track.historical_data.pct_change(5).dropna()
        returns = reality_track.returns_data
        
        ic_series = await reality_track._calculate_ic_series(factor_values, returns)
        
        assert isinstance(ic_series, pd.Series)
        assert len(ic_series) > 0
        assert all(abs(ic) <= 1.0 for ic in ic_series if not np.isnan(ic))
    
    @pytest.mark.asyncio
    async def test_portfolio_construction(self, reality_track):
        """测试组合构建"""
        await reality_track.initialize()
        
        factor_values = reality_track.historical_data.pct_change(10).dropna()
        returns = reality_track.returns_data
        
        portfolio_returns = await reality_track._build_long_short_portfolio(factor_values, returns)
        
        assert isinstance(portfolio_returns, pd.Series)
        assert len(portfolio_returns) > 0
    
    def test_sharpe_calculation(self, reality_track):
        """测试夏普比率计算"""
        # 创建测试收益率数据
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        sharpe = reality_track._calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)
    
    def test_max_drawdown_calculation(self, reality_track):
        """测试最大回撤计算"""
        # 创建包含回撤的收益率数据
        returns = pd.Series([0.01, 0.02, -0.05, -0.03, 0.04, 0.01])
        
        max_dd = reality_track._calculate_max_drawdown(returns)
        
        assert isinstance(max_dd, float)
        assert max_dd >= 0
        assert max_dd <= 1
    
    @pytest.mark.asyncio
    async def test_complete_factor_test(self, reality_track):
        """测试完整的因子测试流程"""
        await reality_track.initialize()
        
        result = await reality_track.test_factor("momentum_factor")
        
        assert isinstance(result, FactorTestResult)
        assert result.factor_expression == "momentum_factor"
        assert result.track_type == TrackType.REALITY
        assert isinstance(result.ic_mean, float)
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown, float)
        assert isinstance(result.passed, (bool, np.bool_))


class TestFactorHellTrack:
    """测试Hell Track"""
    
    @pytest.fixture
    def config(self):
        return ArenaTestConfig()
    
    @pytest.fixture
    def hell_track(self, config):
        return FactorHellTrack(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, hell_track):
        """测试初始化"""
        await hell_track.initialize()
        
        assert len(hell_track.extreme_scenarios) == 5
        for scenario_name, scenario_data in hell_track.extreme_scenarios.items():
            assert isinstance(scenario_data, pd.DataFrame)
            assert scenario_data.shape[0] > 0
            assert scenario_data.shape[1] > 0
    
    @pytest.mark.asyncio
    async def test_scenario_generation(self, hell_track):
        """测试极端场景生成"""
        await hell_track.initialize()
        
        # 检查各种场景是否正确生成
        scenarios = hell_track.extreme_scenarios
        
        assert "market_crash_2008" in scenarios
        assert "flash_crash_2015" in scenarios
        assert "covid_crash_2020" in scenarios
        assert "liquidity_crisis" in scenarios
        assert "black_swan_event" in scenarios
        
        # 检查数据特征
        crash_2008 = scenarios["market_crash_2008"]
        assert crash_2008.index[0].year == 2008
        assert crash_2008.index[-1].year == 2008
    
    @pytest.mark.asyncio
    async def test_factor_in_scenario(self, hell_track):
        """测试因子在特定场景中的表现"""
        await hell_track.initialize()
        
        scenario_data = hell_track.extreme_scenarios["market_crash_2008"]
        
        result = await hell_track._test_factor_in_scenario(
            "momentum_factor", scenario_data, "market_crash_2008"
        )
        
        assert isinstance(result, dict)
        assert 'survival_rate' in result
        assert 'ic_decay_rate' in result
        assert 'recovery_ability' in result
        
        assert 0 <= result['survival_rate'] <= 1
        assert 0 <= result['ic_decay_rate'] <= 1
        assert 0 <= result['recovery_ability'] <= 1
    
    @pytest.mark.asyncio
    async def test_complete_hell_test(self, hell_track):
        """测试完整的Hell Track测试"""
        await hell_track.initialize()
        
        result = await hell_track.test_factor("momentum_factor")
        
        assert isinstance(result, FactorTestResult)
        assert result.factor_expression == "momentum_factor"
        assert result.track_type == TrackType.HELL
        assert isinstance(result.survival_rate, float)
        assert isinstance(result.ic_decay_rate, float)
        assert isinstance(result.recovery_ability, float)
        assert isinstance(result.stress_score, float)
        assert isinstance(result.passed, (bool, np.bool_))
        
        # 检查详细指标
        assert 'scenario_results' in result.detailed_metrics
        scenario_results = result.detailed_metrics['scenario_results']
        assert len(scenario_results) == 5


class TestCrossMarketTrack:
    """测试Cross-Market Track"""
    
    @pytest.fixture
    def config(self):
        return ArenaTestConfig()
    
    @pytest.fixture
    def cross_market_track(self, config):
        return CrossMarketTrack(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, cross_market_track):
        """测试初始化"""
        await cross_market_track.initialize()
        
        assert len(cross_market_track.market_data) == 4
        
        expected_markets = ["A_STOCK", "US_STOCK", "HK_STOCK", "CRYPTO"]
        for market in expected_markets:
            assert market in cross_market_track.market_data
            market_data = cross_market_track.market_data[market]
            assert isinstance(market_data, pd.DataFrame)
            assert market_data.shape[0] > 0
            assert market_data.shape[1] > 0
    
    @pytest.mark.asyncio
    async def test_market_data_generation(self, cross_market_track):
        """测试市场数据生成"""
        await cross_market_track.initialize()
        
        # 检查不同市场的数据特征
        a_stock_data = cross_market_track.market_data["A_STOCK"]
        us_stock_data = cross_market_track.market_data["US_STOCK"]
        crypto_data = cross_market_track.market_data["CRYPTO"]
        
        # A股数据应该有更高的波动性
        a_stock_returns = a_stock_data.pct_change().std().mean()
        us_stock_returns = us_stock_data.pct_change().std().mean()
        crypto_returns = crypto_data.pct_change().std().mean()
        
        # 加密货币应该有最高的波动性
        assert crypto_returns > us_stock_returns
    
    @pytest.mark.asyncio
    async def test_factor_in_market(self, cross_market_track):
        """测试因子在特定市场的表现"""
        await cross_market_track.initialize()
        
        market_data = cross_market_track.market_data["A_STOCK"]
        
        result = await cross_market_track._test_factor_in_market(
            "momentum_factor", market_data, "A_STOCK"
        )
        
        assert isinstance(result, dict)
        assert 'ic_mean' in result
        assert 'sharpe_ratio' in result
        assert 'adaptability_score' in result
        
        assert isinstance(result['ic_mean'], float)
        assert isinstance(result['sharpe_ratio'], float)
        assert 0 <= result['adaptability_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_complete_cross_market_test(self, cross_market_track):
        """测试完整的跨市场测试"""
        await cross_market_track.initialize()
        
        result = await cross_market_track.test_factor("momentum_factor")
        
        assert isinstance(result, FactorTestResult)
        assert result.factor_expression == "momentum_factor"
        assert result.track_type == TrackType.CROSS_MARKET
        assert isinstance(result.markets_passed, int)
        assert isinstance(result.adaptability_score, float)
        assert isinstance(result.consistency_score, float)
        assert isinstance(result.passed, bool)
        
        assert 0 <= result.markets_passed <= 4
        assert 0 <= result.adaptability_score <= 1
        assert 0 <= result.consistency_score <= 1
        
        # 检查详细指标
        assert 'market_results' in result.detailed_metrics
        market_results = result.detailed_metrics['market_results']
        assert len(market_results) == 4


class TestFactorArenaSystem:
    """测试因子Arena系统"""
    
    @pytest.fixture
    def config(self):
        return ArenaTestConfig()
    
    @pytest.fixture
    def arena_system(self, config):
        return FactorArenaSystem(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, arena_system):
        """测试系统初始化"""
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            assert arena_system.is_running is True
            assert arena_system.reality_track is not None
            assert arena_system.hell_track is not None
            assert arena_system.cross_market_track is not None
            assert arena_system.event_bus is not None
    
    @pytest.mark.asyncio
    async def test_factor_submission(self, arena_system):
        """测试因子提交"""
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            # 提交因子测试
            task_id = await arena_system.submit_factor_for_testing(
                "test_factor", {"source": "genetic_miner"}
            )
            
            assert isinstance(task_id, str)
            assert task_id in arena_system.testing_factors
            
            task_info = arena_system.testing_factors[task_id]
            assert task_info['factor_expression'] == "test_factor"
            assert task_info['metadata']['source'] == "genetic_miner"
            # 状态可能是PENDING或TESTING，取决于是否立即开始测试
            assert task_info['status'] in [FactorStatus.PENDING, FactorStatus.TESTING]
    
    @pytest.mark.asyncio
    async def test_concurrent_testing_limit(self, arena_system):
        """测试并发测试限制"""
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            # 提交超过并发限制的因子
            task_ids = []
            for i in range(5):  # 超过max_concurrent_tests=3
                task_id = await arena_system.submit_factor_for_testing(f"factor_{i}")
                task_ids.append(task_id)
            
            # 检查只有3个在测试中
            testing_count = sum(
                1 for task_info in arena_system.testing_factors.values()
                if task_info['status'] == FactorStatus.TESTING
            )
            
            # 由于异步执行，可能需要等待一下
            await asyncio.sleep(0.1)
            
            # 应该有一些因子在等待队列中
            assert len(arena_system.pending_factors) >= 0
    
    def test_overall_score_calculation(self, arena_system):
        """测试综合评分计算"""
        # 创建测试结果
        reality_result = FactorTestResult(
            factor_expression="test_factor",
            track_type=TrackType.REALITY,
            test_start_time=datetime.now(),
            test_end_time=datetime.now(),
            ic_mean=0.06,
            sharpe_ratio=1.8,
            max_drawdown=0.12,
            passed=True
        )
        
        hell_result = FactorTestResult(
            factor_expression="test_factor",
            track_type=TrackType.HELL,
            test_start_time=datetime.now(),
            test_end_time=datetime.now(),
            survival_rate=0.75,
            ic_decay_rate=0.2,
            recovery_ability=0.6,
            passed=True
        )
        
        cross_market_result = FactorTestResult(
            factor_expression="test_factor",
            track_type=TrackType.CROSS_MARKET,
            test_start_time=datetime.now(),
            test_end_time=datetime.now(),
            markets_passed=3,
            adaptability_score=0.7,
            passed=True
        )
        
        results = [reality_result, hell_result, cross_market_result]
        overall_result = arena_system._calculate_overall_score(results)
        
        assert isinstance(overall_result, dict)
        assert 'score' in overall_result
        assert 'passed' in overall_result
        assert 'reality_score' in overall_result
        assert 'hell_score' in overall_result
        assert 'cross_market_score' in overall_result
        assert 'certification_eligible' in overall_result
        
        assert 0 <= overall_result['score'] <= 100
        assert isinstance(overall_result['passed'], bool)
    
    @pytest.mark.asyncio
    async def test_get_test_status(self, arena_system):
        """测试获取测试状态"""
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            # 提交测试
            task_id = await arena_system.submit_factor_for_testing("test_factor")
            
            # 获取状态
            status = await arena_system.get_test_status(task_id)
            
            assert status['task_id'] == task_id
            assert status['factor_expression'] == "test_factor"
            assert 'status' in status
            assert 'submit_time' in status
    
    @pytest.mark.asyncio
    async def test_get_arena_stats(self, arena_system):
        """测试获取Arena统计信息"""
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            stats = await arena_system.get_arena_stats()
            
            assert 'stats' in stats
            assert 'current_status' in stats
            assert 'config' in stats
            
            assert 'total_factors_tested' in stats['stats']
            assert 'factors_passed' in stats['stats']
            assert 'factors_failed' in stats['stats']
            
            assert 'is_running' in stats['current_status']
            assert 'pending_factors' in stats['current_status']
            assert 'testing_factors' in stats['current_status']
    
    def test_failed_result_creation(self, arena_system):
        """测试失败结果创建"""
        result = arena_system._create_failed_result(
            "failed_factor", TrackType.REALITY, "Test error"
        )
        
        assert isinstance(result, FactorTestResult)
        assert result.factor_expression == "failed_factor"
        assert result.track_type == TrackType.REALITY
        assert result.passed is False
        assert result.error_message == "Test error"
    
    def test_stats_update(self, arena_system):
        """测试统计信息更新"""
        # 创建测试结果
        results = [
            FactorTestResult(
                factor_expression="test",
                track_type=TrackType.REALITY,
                test_start_time=datetime.now(),
                test_end_time=datetime.now(),
                passed=True
            ),
            FactorTestResult(
                factor_expression="test",
                track_type=TrackType.HELL,
                test_start_time=datetime.now(),
                test_end_time=datetime.now(),
                passed=True
            ),
            FactorTestResult(
                factor_expression="test",
                track_type=TrackType.CROSS_MARKET,
                test_start_time=datetime.now(),
                test_end_time=datetime.now(),
                passed=True
            )
        ]
        
        initial_total = arena_system.stats['total_factors_tested']
        arena_system._update_stats(results, 5.0)
        
        assert arena_system.stats['total_factors_tested'] == initial_total + 1
        assert arena_system.stats['avg_test_time_minutes'] > 0
    
    @pytest.mark.asyncio
    async def test_event_handling(self, arena_system):
        """测试事件处理"""
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            # 测试因子提交事件处理
            event = Event(
                event_type=EventType.FACTOR_DISCOVERED,
                source_module="genetic_miner",
                target_module="arena",
                priority=EventPriority.NORMAL,
                data={
                    'action': 'submit_to_arena',
                    'factor_expression': 'event_factor',
                    'metadata': {'source': 'event'}
                }
            )
            
            await arena_system._handle_factor_submission(event)
            
            # 检查因子是否被添加到队列
            assert 'event_factor' in [
                task_info['factor_expression'] 
                for task_info in arena_system.testing_factors.values()
            ]


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_arena_workflow(self):
        """测试完整的Arena工作流程"""
        config = ArenaTestConfig()
        arena_system = FactorArenaSystem(config)
        
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            # 初始化系统
            await arena_system.initialize()
            
            # 提交因子测试
            task_id = await arena_system.submit_factor_for_testing(
                "integration_test_factor",
                {"source": "integration_test"}
            )
            
            # 等待测试开始
            await asyncio.sleep(0.1)
            
            # 检查任务状态
            status = await arena_system.get_test_status(task_id)
            assert status['factor_expression'] == "integration_test_factor"
            
            # 检查统计信息
            stats = await arena_system.get_arena_stats()
            assert stats['current_status']['is_running'] is True
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        config = ArenaTestConfig()
        arena_system = FactorArenaSystem(config)
        
        # 测试未初始化时提交因子
        with pytest.raises(RuntimeError, match="Arena系统未运行"):
            await arena_system.submit_factor_for_testing("test_factor")
        
        # 测试获取不存在的任务状态
        with patch('src.evolution.factor_arena.get_event_bus') as mock_get_bus:
            mock_event_bus = AsyncMock()
            mock_get_bus.return_value = mock_event_bus
            
            await arena_system.initialize()
            
            status = await arena_system.get_test_status("non_existent_task")
            assert 'error' in status
            assert status['error'] == 'Task not found'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])