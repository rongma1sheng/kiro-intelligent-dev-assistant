"""
MIA系统斯巴达Arena压力测试标准单元测试

版本: v1.6.0
作者: MIA Team
日期: 2026-01-18
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.evolution.sparta_arena_standards import (
    SpartaArenaStandards,
    TrackType,
    MarketScenario,
    ArenaTestConfig,
    ArenaTestResult
)
from src.base.models import Strategy, SimulationResult


class TestSpartaArenaStandards:
    """斯巴达Arena压力测试标准测试类"""
    
    @pytest.fixture
    def arena_standards(self):
        """创建Arena测试标准实例"""
        return SpartaArenaStandards()
    
    @pytest.fixture
    def mock_strategy(self):
        """创建模拟策略"""
        return Strategy(
            strategy_id="test_strategy_001",
            name="测试策略",
            type="momentum",
            description="用于测试的动量策略"
        )
    
    @pytest.fixture
    def sample_simulation_result(self):
        """创建样本模拟结果"""
        return SimulationResult(
            strategy_id="test_strategy_001",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000.0,
            final_capital=115000.0,
            total_return=0.15,
            annual_return=0.15,
            sharpe_ratio=1.8,
            max_drawdown=0.08,
            volatility=0.18,
            win_rate=0.58,
            daily_returns=[0.001, -0.002, 0.003, 0.001, -0.001] * 50,  # 250个交易日
            calmar_ratio=1.875
        )
    
    def test_initialization(self, arena_standards):
        """测试初始化"""
        assert arena_standards is not None
        assert hasattr(arena_standards, 'test_configs')
        assert hasattr(arena_standards, 'pass_standards')
        assert hasattr(arena_standards, 'scoring_weights')
        
        # 检查测试配置
        assert TrackType.REALITY in arena_standards.test_configs
        assert TrackType.HELL in arena_standards.test_configs
        
        # 检查Reality Track场景
        reality_scenarios = arena_standards.test_configs[TrackType.REALITY]
        assert MarketScenario.BULL_MARKET in reality_scenarios
        assert MarketScenario.BEAR_MARKET in reality_scenarios
        assert MarketScenario.SIDEWAYS_MARKET in reality_scenarios
        assert MarketScenario.VOLATILE_MARKET in reality_scenarios
        
        # 检查Hell Track场景
        hell_scenarios = arena_standards.test_configs[TrackType.HELL]
        assert MarketScenario.FLASH_CRASH in hell_scenarios
        assert MarketScenario.CIRCUIT_BREAKER in hell_scenarios
        assert MarketScenario.LIQUIDITY_CRISIS in hell_scenarios
        assert MarketScenario.BLACK_SWAN in hell_scenarios
        assert MarketScenario.EXTREME_VOLATILITY in hell_scenarios
    
    def test_test_config_validity(self, arena_standards):
        """测试测试配置的有效性"""
        for track_type, scenarios in arena_standards.test_configs.items():
            for scenario, config in scenarios.items():
                # 检查配置完整性
                assert isinstance(config, ArenaTestConfig)
                assert config.track_type == track_type
                assert config.scenario == scenario
                assert config.test_duration_days > 0
                assert config.initial_capital > 0
                assert 0 <= config.max_drawdown_threshold <= 1
                assert config.survival_rate_threshold > 0
                assert config.stress_multiplier > 0
                
                # 检查Hell Track的标准更宽松
                if track_type == TrackType.HELL:
                    reality_config = arena_standards.test_configs[TrackType.REALITY][MarketScenario.BULL_MARKET]
                    assert config.max_drawdown_threshold >= reality_config.max_drawdown_threshold
                    assert config.survival_rate_threshold <= reality_config.survival_rate_threshold
    
    def test_pass_standards_validity(self, arena_standards):
        """测试通过标准的有效性"""
        standards = arena_standards.pass_standards
        
        # 检查Reality Track标准
        reality_std = standards['reality_track']
        assert 0 < reality_std['min_overall_score'] <= 1
        assert 0 < reality_std['min_basic_score'] <= 1
        assert 0 < reality_std['min_stress_score'] <= 1
        assert 0 < reality_std['min_stability_score'] <= 1
        assert reality_std['max_failure_scenarios'] >= 0
        assert 0 < reality_std['min_survival_rate'] <= 1
        
        # 检查Hell Track标准
        hell_std = standards['hell_track']
        assert 0 < hell_std['min_overall_score'] <= 1
        assert 0 < hell_std['min_basic_score'] <= 1
        assert 0 < hell_std['min_stress_score'] <= 1
        assert 0 < hell_std['min_stability_score'] <= 1
        assert hell_std['max_failure_scenarios'] >= 0
        assert 0 < hell_std['min_survival_rate'] <= 1
        
        # Hell Track标准应该比Reality Track更宽松
        assert hell_std['min_overall_score'] <= reality_std['min_overall_score']
        assert hell_std['min_basic_score'] <= reality_std['min_basic_score']
        assert hell_std['min_survival_rate'] <= reality_std['min_survival_rate']
        
        # 检查综合标准
        combined_std = standards['combined']
        assert 0 < combined_std['min_reality_score'] <= 1
        assert 0 < combined_std['min_hell_score'] <= 1
        assert 0 < combined_std['min_combined_score'] <= 1
        assert combined_std['reality_weight'] + combined_std['hell_weight'] == 1.0
    
    @pytest.mark.asyncio
    async def test_generate_reality_data(self, arena_standards):
        """测试Reality Track数据生成"""
        config = arena_standards.test_configs[TrackType.REALITY][MarketScenario.BULL_MARKET]
        
        data = await arena_standards._generate_reality_data(MarketScenario.BULL_MARKET, config)
        
        # 检查数据结构
        assert isinstance(data, pd.DataFrame)
        assert len(data) == config.test_duration_days
        assert 'date' in data.columns
        assert 'close' in data.columns
        assert 'returns' in data.columns
        assert 'volume' in data.columns
        assert 'high' in data.columns
        assert 'low' in data.columns
        assert 'open' in data.columns
        
        # 检查数据合理性
        assert data['close'].iloc[0] > 0
        assert data['volume'].min() > 0
        assert (data['high'] >= data['close']).all()
        assert (data['low'] <= data['close']).all()
        
        # 检查牛市特征 (整体上涨趋势)
        total_return = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1
        assert total_return > -0.5  # 不应该大幅下跌
    
    @pytest.mark.asyncio
    async def test_generate_hell_data(self, arena_standards):
        """测试Hell Track数据生成"""
        config = arena_standards.test_configs[TrackType.HELL][MarketScenario.FLASH_CRASH]
        
        data = await arena_standards._generate_hell_data(MarketScenario.FLASH_CRASH, config)
        
        # 检查数据结构
        assert isinstance(data, pd.DataFrame)
        assert len(data) == config.test_duration_days
        assert 'date' in data.columns
        assert 'close' in data.columns
        assert 'returns' in data.columns
        
        # 检查闪崩特征 (应该有大幅下跌)
        returns = data['returns'].values
        min_return = np.min(returns)
        assert min_return < -0.05  # 应该有超过5%的单日跌幅
        
        # 检查极端值存在
        extreme_count = np.sum(np.abs(returns) > 0.05)
        assert extreme_count > 0  # 应该有极端收益
    
    @pytest.mark.asyncio
    async def test_run_strategy_simulation(self, arena_standards, mock_strategy):
        """测试策略模拟运行"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=10),
            'close': [100, 101, 99, 102, 98, 103, 97, 104, 96, 105],
            'returns': [0.01, -0.02, 0.03, -0.04, 0.05, -0.06, 0.07, -0.08, 0.09, -0.01],
            'volume': [1000000] * 10,
            'high': [101, 102, 100, 103, 99, 104, 98, 105, 97, 106],
            'low': [99, 100, 98, 101, 97, 102, 96, 103, 95, 104],
            'open': [100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
        })
        
        config = arena_standards.test_configs[TrackType.REALITY][MarketScenario.BULL_MARKET]
        
        result = await arena_standards._run_strategy_simulation(mock_strategy, test_data, config)
        
        # 检查结果类型
        assert isinstance(result, SimulationResult)
        assert result.strategy_id == mock_strategy.strategy_id
        assert result.initial_capital == config.initial_capital
        
        # 检查指标合理性
        assert -1 <= result.total_return <= 10  # 合理的收益范围
        assert 0 <= result.max_drawdown <= 1    # 回撤在0-100%之间
        assert 0 <= result.win_rate <= 1        # 胜率在0-100%之间
        assert len(result.daily_returns) == len(test_data)
    
    def test_calculate_stress_metrics(self, arena_standards, sample_simulation_result):
        """测试压力测试指标计算"""
        config = arena_standards.test_configs[TrackType.REALITY][MarketScenario.BULL_MARKET]
        
        stress_metrics = arena_standards._calculate_stress_metrics(sample_simulation_result, config)
        
        # 检查指标存在
        assert 'survival_rate' in stress_metrics
        assert 'recovery_factor' in stress_metrics
        assert 'stress_resistance' in stress_metrics
        assert 'adaptation_speed' in stress_metrics
        assert 'drawdown_series' in stress_metrics
        
        # 检查指标范围
        assert 0 <= stress_metrics['survival_rate'] <= 1
        assert 0 <= stress_metrics['recovery_factor'] <= 2
        assert 0 <= stress_metrics['stress_resistance'] <= 2
        assert 0 <= stress_metrics['adaptation_speed'] <= 1
        assert isinstance(stress_metrics['drawdown_series'], list)
    
    def test_evaluate_pass_status_reality_track(self, arena_standards, sample_simulation_result):
        """测试Reality Track通过状态评估"""
        config = arena_standards.test_configs[TrackType.REALITY][MarketScenario.BULL_MARKET]
        
        # 创建良好的压力测试指标
        stress_metrics = {
            'survival_rate': 0.98,
            'recovery_factor': 1.2,
            'stress_resistance': 0.8,
            'adaptation_speed': 0.6,
            'drawdown_series': [-0.01, -0.02, -0.01, 0.0] * 50
        }
        
        passed, pass_score, failure_reasons = arena_standards._evaluate_pass_status(
            sample_simulation_result, stress_metrics, config
        )
        
        # 检查结果类型
        assert isinstance(passed, bool)
        assert isinstance(pass_score, float)
        assert isinstance(failure_reasons, list)
        
        # 检查评分范围
        assert 0 <= pass_score <= 1
        
        # 好的策略应该通过
        assert passed == True
        assert len(failure_reasons) == 0
    
    def test_evaluate_pass_status_hell_track(self, arena_standards):
        """测试Hell Track通过状态评估"""
        config = arena_standards.test_configs[TrackType.HELL][MarketScenario.FLASH_CRASH]
        
        # 创建Hell Track的模拟结果 (标准更宽松)
        hell_result = SimulationResult(
            strategy_id="test_strategy_001",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 5),
            initial_capital=100000.0,
            final_capital=85000.0,  # 15%亏损
            total_return=-0.15,
            annual_return=-0.15,
            sharpe_ratio=-0.5,      # 负夏普比率
            max_drawdown=0.20,      # 20%回撤
            volatility=0.35,        # 高波动率
            win_rate=0.35,          # 低胜率
            daily_returns=[-0.05, -0.08, 0.02, -0.03, 0.01],
            calmar_ratio=-0.75
        )
        
        stress_metrics = {
            'survival_rate': 0.75,   # Hell Track标准更低
            'recovery_factor': 0.3,
            'stress_resistance': 0.4,
            'adaptation_speed': 0.5,
            'drawdown_series': [-0.05, -0.12, -0.15, -0.18, -0.20]
        }
        
        passed, pass_score, failure_reasons = arena_standards._evaluate_pass_status(
            hell_result, stress_metrics, config
        )
        
        # Hell Track标准更宽松，应该更容易通过
        assert isinstance(passed, bool)
        assert 0 <= pass_score <= 1
        
        # 检查失败原因的合理性
        for reason in failure_reasons:
            assert isinstance(reason, str)
            assert len(reason) > 0
    
    @pytest.mark.asyncio
    async def test_run_single_scenario_test(self, arena_standards, mock_strategy):
        """测试单个场景测试"""
        with patch.object(arena_standards, '_generate_test_data') as mock_generate, \
             patch.object(arena_standards, '_run_strategy_simulation') as mock_simulate:
            
            # 模拟数据生成
            mock_data = pd.DataFrame({
                'date': pd.date_range('2023-01-01', periods=5),
                'close': [100, 95, 90, 85, 80],
                'returns': [-0.05, -0.05, -0.05, -0.05, -0.05]
            })
            mock_generate.return_value = mock_data
            
            # 模拟策略回测结果
            mock_result = SimulationResult(
                strategy_id=mock_strategy.strategy_id,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 5),
                initial_capital=100000.0,
                final_capital=80000.0,
                total_return=-0.20,
                annual_return=-0.20,
                sharpe_ratio=-1.0,
                max_drawdown=0.20,
                volatility=0.25,
                win_rate=0.0,
                daily_returns=[-0.05, -0.05, -0.05, -0.05, -0.05],
                calmar_ratio=-1.0
            )
            mock_simulate.return_value = mock_result
            
            # 运行测试
            result = await arena_standards._run_single_scenario_test(
                mock_strategy, TrackType.HELL, MarketScenario.FLASH_CRASH
            )
            
            # 检查结果
            assert isinstance(result, ArenaTestResult)
            assert result.strategy_id == mock_strategy.strategy_id
            assert result.strategy_name == mock_strategy.name
            assert result.track_type == TrackType.HELL
            assert result.scenario == MarketScenario.FLASH_CRASH
            assert isinstance(result.passed, bool)
            assert 0 <= result.pass_score <= 1
            assert isinstance(result.failure_reasons, list)
    
    @pytest.mark.asyncio
    async def test_run_arena_test_reality_track(self, arena_standards, mock_strategy):
        """测试Reality Track完整测试"""
        with patch.object(arena_standards, '_run_single_scenario_test') as mock_single_test:
            
            # 模拟单个场景测试结果
            def create_mock_result(scenario):
                return ArenaTestResult(
                    strategy_id=mock_strategy.strategy_id,
                    strategy_name=mock_strategy.name,
                    track_type=TrackType.REALITY,
                    scenario=scenario,
                    test_date=datetime.now(),
                    total_return=0.15,
                    annual_return=0.15,
                    sharpe_ratio=1.8,
                    max_drawdown=0.08,
                    volatility=0.18,
                    win_rate=0.58,
                    survival_rate=0.95,
                    recovery_factor=1.2,
                    stress_resistance=0.8,
                    adaptation_speed=0.6,
                    passed=True,
                    pass_score=0.75,
                    failure_reasons=[],
                    daily_returns=[0.001] * 252,
                    drawdown_series=[-0.01] * 252
                )
            
            mock_single_test.side_effect = lambda s, t, sc: create_mock_result(sc)
            
            # 运行Reality Track测试
            results = await arena_standards.run_arena_test(
                mock_strategy, TrackType.REALITY
            )
            
            # 检查结果
            assert isinstance(results, dict)
            assert len(results) == 4  # Reality Track有4个场景
            
            for scenario, result in results.items():
                assert isinstance(scenario, MarketScenario)
                assert isinstance(result, ArenaTestResult)
                assert result.track_type == TrackType.REALITY
                assert result.scenario == scenario
    
    @pytest.mark.asyncio
    async def test_run_arena_test_hell_track(self, arena_standards, mock_strategy):
        """测试Hell Track完整测试"""
        with patch.object(arena_standards, '_run_single_scenario_test') as mock_single_test:
            
            # 模拟Hell Track测试结果 (更严苛的场景)
            def create_hell_result(scenario):
                return ArenaTestResult(
                    strategy_id=mock_strategy.strategy_id,
                    strategy_name=mock_strategy.name,
                    track_type=TrackType.HELL,
                    scenario=scenario,
                    test_date=datetime.now(),
                    total_return=-0.10,
                    annual_return=-0.10,
                    sharpe_ratio=-0.5,
                    max_drawdown=0.25,
                    volatility=0.35,
                    win_rate=0.40,
                    survival_rate=0.70,
                    recovery_factor=0.4,
                    stress_resistance=0.5,
                    adaptation_speed=0.4,
                    passed=True,  # Hell Track标准更宽松
                    pass_score=0.45,
                    failure_reasons=[],
                    daily_returns=[-0.02] * 30,
                    drawdown_series=[-0.05] * 30
                )
            
            mock_single_test.side_effect = lambda s, t, sc: create_hell_result(sc)
            
            # 运行Hell Track测试
            results = await arena_standards.run_arena_test(
                mock_strategy, TrackType.HELL
            )
            
            # 检查结果
            assert isinstance(results, dict)
            assert len(results) == 5  # Hell Track有5个场景
            
            for scenario, result in results.items():
                assert isinstance(scenario, MarketScenario)
                assert isinstance(result, ArenaTestResult)
                assert result.track_type == TrackType.HELL
                assert result.scenario == scenario
    
    def test_calculate_combined_arena_score(self, arena_standards, mock_strategy):
        """测试Arena综合评分计算"""
        # 创建Reality Track结果
        reality_results = {}
        for scenario in [MarketScenario.BULL_MARKET, MarketScenario.BEAR_MARKET]:
            reality_results[scenario] = ArenaTestResult(
                strategy_id=mock_strategy.strategy_id,
                strategy_name=mock_strategy.name,
                track_type=TrackType.REALITY,
                scenario=scenario,
                test_date=datetime.now(),
                total_return=0.15,
                annual_return=0.15,
                sharpe_ratio=1.8,
                max_drawdown=0.08,
                volatility=0.18,
                win_rate=0.58,
                survival_rate=0.95,
                recovery_factor=1.2,
                stress_resistance=0.8,
                adaptation_speed=0.6,
                passed=True,
                pass_score=0.75,
                failure_reasons=[],
                daily_returns=[0.001] * 252,
                drawdown_series=[-0.01] * 252
            )
        
        # 创建Hell Track结果
        hell_results = {}
        for scenario in [MarketScenario.FLASH_CRASH, MarketScenario.BLACK_SWAN]:
            hell_results[scenario] = ArenaTestResult(
                strategy_id=mock_strategy.strategy_id,
                strategy_name=mock_strategy.name,
                track_type=TrackType.HELL,
                scenario=scenario,
                test_date=datetime.now(),
                total_return=-0.10,
                annual_return=-0.10,
                sharpe_ratio=-0.5,
                max_drawdown=0.25,
                volatility=0.35,
                win_rate=0.40,
                survival_rate=0.70,
                recovery_factor=0.4,
                stress_resistance=0.5,
                adaptation_speed=0.4,
                passed=True,
                pass_score=0.45,
                failure_reasons=[],
                daily_returns=[-0.02] * 30,
                drawdown_series=[-0.05] * 30
            )
        
        # 计算综合评分
        combined_result = arena_standards.calculate_combined_arena_score(
            reality_results, hell_results
        )
        
        # 检查结果结构
        assert isinstance(combined_result, dict)
        assert 'combined_passed' in combined_result
        assert 'combined_score' in combined_result
        assert 'grade' in combined_result
        assert 'reality_track' in combined_result
        assert 'hell_track' in combined_result
        assert 'summary' in combined_result
        
        # 检查数值合理性
        assert isinstance(combined_result['combined_passed'], bool)
        assert 0 <= combined_result['combined_score'] <= 1
        assert combined_result['grade'] in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D']
        
        # 检查Reality Track统计
        reality_stats = combined_result['reality_track']
        assert 0 <= reality_stats['avg_score'] <= 1
        assert reality_stats['pass_count'] <= reality_stats['total_scenarios']
        assert 0 <= reality_stats['pass_rate'] <= 1
        
        # 检查Hell Track统计
        hell_stats = combined_result['hell_track']
        assert 0 <= hell_stats['avg_score'] <= 1
        assert hell_stats['pass_count'] <= hell_stats['total_scenarios']
        assert 0 <= hell_stats['pass_rate'] <= 1
        
        # 检查总体统计
        summary = combined_result['summary']
        assert summary['total_scenarios'] == len(reality_results) + len(hell_results)
        assert summary['total_passed'] == reality_stats['pass_count'] + hell_stats['pass_count']
        assert 0 <= summary['overall_pass_rate'] <= 1
    
    def test_scoring_weights_sum_to_one(self, arena_standards):
        """测试评分权重总和为1"""
        weights = arena_standards.scoring_weights
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 1e-6  # 允许浮点误差
    
    def test_scenario_coverage(self, arena_standards):
        """测试场景覆盖完整性"""
        # Reality Track应该覆盖主要市场环境
        reality_scenarios = set(arena_standards.test_configs[TrackType.REALITY].keys())
        expected_reality = {
            MarketScenario.BULL_MARKET,
            MarketScenario.BEAR_MARKET,
            MarketScenario.SIDEWAYS_MARKET,
            MarketScenario.VOLATILE_MARKET
        }
        assert reality_scenarios == expected_reality
        
        # Hell Track应该覆盖极端场景
        hell_scenarios = set(arena_standards.test_configs[TrackType.HELL].keys())
        expected_hell = {
            MarketScenario.FLASH_CRASH,
            MarketScenario.CIRCUIT_BREAKER,
            MarketScenario.LIQUIDITY_CRISIS,
            MarketScenario.BLACK_SWAN,
            MarketScenario.EXTREME_VOLATILITY
        }
        assert hell_scenarios == expected_hell
    
    def test_stress_multiplier_logic(self, arena_standards):
        """测试压力倍数逻辑"""
        # Hell Track的压力倍数应该更高
        for scenario, config in arena_standards.test_configs[TrackType.HELL].items():
            assert config.stress_multiplier >= 2.0  # Hell Track至少2倍压力
        
        # Reality Track的压力倍数相对较低
        for scenario, config in arena_standards.test_configs[TrackType.REALITY].items():
            assert config.stress_multiplier <= 2.0  # Reality Track不超过2倍压力
    
    @pytest.mark.asyncio
    async def test_error_handling_in_scenario_test(self, arena_standards, mock_strategy):
        """测试场景测试中的错误处理"""
        with patch.object(arena_standards, '_generate_test_data') as mock_generate:
            # 模拟数据生成失败
            mock_generate.side_effect = Exception("数据生成失败")
            
            # 运行测试应该捕获异常并返回失败结果
            results = await arena_standards.run_arena_test(
                mock_strategy, TrackType.REALITY, [MarketScenario.BULL_MARKET]
            )
            
            assert len(results) == 1
            result = results[MarketScenario.BULL_MARKET]
            assert result.passed == False
            assert result.pass_score == 0.0
            assert len(result.failure_reasons) > 0
            assert "测试执行失败" in result.failure_reasons[0]
    
    def test_grade_assignment_logic(self, arena_standards):
        """测试评级分配逻辑"""
        # 创建空的测试结果用于测试评级逻辑
        reality_results = {}
        hell_results = {}
        
        # 测试不同评分对应的评级
        test_cases = [
            (0.90, "A+"),
            (0.80, "A"),
            (0.70, "B+"),
            (0.60, "B"),
            (0.50, "C+"),
            (0.40, "C"),
            (0.30, "D")
        ]
        
        for score, expected_grade in test_cases:
            # 通过修改权重来控制综合评分
            original_weights = arena_standards.pass_standards['combined'].copy()
            
            # 临时修改标准以产生特定评分
            arena_standards.pass_standards['combined']['reality_weight'] = 1.0
            arena_standards.pass_standards['combined']['hell_weight'] = 0.0
            
            # 创建具有特定评分的结果
            mock_result = ArenaTestResult(
                strategy_id="test",
                strategy_name="test",
                track_type=TrackType.REALITY,
                scenario=MarketScenario.BULL_MARKET,
                test_date=datetime.now(),
                total_return=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                win_rate=0.0,
                survival_rate=0.0,
                recovery_factor=0.0,
                stress_resistance=0.0,
                adaptation_speed=0.0,
                passed=True,
                pass_score=score,
                failure_reasons=[],
                daily_returns=[],
                drawdown_series=[]
            )
            
            reality_results = {MarketScenario.BULL_MARKET: mock_result}
            
            result = arena_standards.calculate_combined_arena_score(reality_results, {})
            assert result['grade'] == expected_grade
            
            # 恢复原始权重
            arena_standards.pass_standards['combined'] = original_weights


if __name__ == "__main__":
    pytest.main([__file__])