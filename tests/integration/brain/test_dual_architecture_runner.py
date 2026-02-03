"""双架构运行器集成测试

白皮书依据: 第二章 2.2.4 风险控制元学习架构

测试目标：
1. 测试并行运行流程
2. 测试性能评估准确性
3. 测试元学习器集成
4. 测试不同执行模式（conservative/aggressive/balanced）

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.brain.dual_architecture_runner import (
    DualArchitectureRunner,
    ArchitectureDecision
)
from src.brain.risk_control_meta_learner import (
    RiskControlMetaLearner,
    MarketContext,
    PerformanceMetrics
)


class TestDualArchitectureRunnerIntegration:
    """双架构运行器集成测试
    
    白皮书依据: 第二章 2.2.4 风险控制元学习架构
    """
    
    @pytest.fixture
    def meta_learner(self):
        """创建元学习器实例"""
        return RiskControlMetaLearner()
    
    @pytest.fixture
    def mock_architecture_a(self):
        """创建模拟的架构A（Soldier硬编码风控）"""
        arch = Mock()
        arch.decide = AsyncMock(return_value={
            'positions': [
                {'symbol': '000001', 'weight': 0.05},
                {'symbol': '000002', 'weight': 0.03}
            ],
            'risk_level': 'low',
            'confidence': 0.75,
            'metadata': {'strategy': 'hardcoded'}
        })
        return arch
    
    @pytest.fixture
    def mock_architecture_b(self):
        """创建模拟的架构B（策略层风控）"""
        arch = Mock()
        arch.decide = AsyncMock(return_value={
            'positions': [
                {'symbol': '000001', 'weight': 0.08},
                {'symbol': '000002', 'weight': 0.05},
                {'symbol': '000003', 'weight': 0.04}
            ],
            'risk_level': 'medium',
            'confidence': 0.85,
            'metadata': {'strategy': 'strategy_layer'}
        })
        return arch
    
    @pytest.fixture
    def sample_market_data(self):
        """创建示例市场数据"""
        return {
            'volatility': 0.25,
            'avg_volume': 1500000.0,
            'trend_strength': 0.3,
            'regime': 'bull',
            'prices': {
                '000001': 10.5,
                '000002': 15.2,
                '000003': 8.7
            }
        }
    
    @pytest.fixture
    def sample_portfolio(self):
        """创建示例投资组合"""
        return {
            'total_value': 150000.0,
            'cash': 50000.0,
            'positions': {
                '000001': {'shares': 1000, 'value': 10500.0},
                '000002': {'shares': 500, 'value': 7600.0}
            },
            'recent_drawdown': -0.05
        }
    
    @pytest.mark.asyncio
    async def test_parallel_running_conservative_mode(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试保守模式的并行运行
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 两种架构都被调用
        2. 保守模式选择架构A
        3. 市场上下文正确提取
        4. 决策历史正确记录
        """
        # 创建运行器（保守模式）
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='conservative'
        )
        
        # 运行并行测试
        result = await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 验证两种架构都被调用
        mock_architecture_a.decide.assert_called_once()
        mock_architecture_b.decide.assert_called_once()
        
        # 验证保守模式选择架构A
        assert result['selected_decision'].strategy == 'hardcoded'
        assert result['execution_mode'] == 'conservative'
        
        # 验证市场上下文
        market_context = result['market_context']
        assert isinstance(market_context, MarketContext)
        assert market_context.volatility == 0.25
        assert market_context.regime == 'bull'
        assert market_context.aum == 150000.0
        
        # 验证决策历史
        assert len(runner.decision_history) == 1
        assert runner.stats['total_runs'] == 1
        assert runner.stats['architecture_a_selected'] == 1
    
    @pytest.mark.asyncio
    async def test_parallel_running_aggressive_mode(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试激进模式的并行运行
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 激进模式选择架构B
        2. 统计信息正确更新
        """
        # 创建运行器（激进模式）
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='aggressive'
        )
        
        # 运行并行测试
        result = await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 验证激进模式选择架构B
        assert result['selected_decision'].strategy == 'strategy_layer'
        assert result['execution_mode'] == 'aggressive'
        
        # 验证统计信息
        assert runner.stats['architecture_b_selected'] == 1
    
    @pytest.mark.asyncio
    async def test_parallel_running_balanced_mode(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试平衡模式的并行运行
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 平衡模式根据置信度选择
        2. 选择置信度更高的架构B（0.85 > 0.75）
        """
        # 创建运行器（平衡模式）
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='balanced'
        )
        
        # 运行并行测试
        result = await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 验证平衡模式选择置信度更高的架构B
        assert result['selected_decision'].strategy == 'strategy_layer'
        assert result['selected_decision'].confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_performance_evaluation(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试性能评估功能
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 性能指标正确计算
        2. 元学习器正确接收数据
        3. 性能历史正确记录
        """
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='conservative'
        )
        
        # 运行并行测试
        await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 创建模拟的决策和市场上下文
        decision_a = ArchitectureDecision(
            strategy='hardcoded',
            positions=[],
            risk_level='low',
            confidence=0.75,
            latency_ms=15.0
        )
        
        decision_b = ArchitectureDecision(
            strategy='strategy_layer',
            positions=[],
            risk_level='medium',
            confidence=0.85,
            latency_ms=25.0
        )
        
        market_context = MarketContext(
            volatility=0.25,
            liquidity=1500000.0,
            trend_strength=0.3,
            regime='bull',
            aum=150000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        actual_returns = {
            '000001': 0.02,
            '000002': 0.01,
            '000003': -0.01
        }
        
        # 评估性能
        perf_a, perf_b = await runner._evaluate_performance(
            decision_a,
            decision_b,
            market_context,
            actual_returns
        )
        
        # 验证性能指标
        assert isinstance(perf_a, PerformanceMetrics)
        assert isinstance(perf_b, PerformanceMetrics)
        assert perf_a.decision_latency_ms == 15.0
        assert perf_b.decision_latency_ms == 25.0
        
        # 验证性能历史
        assert len(runner.performance_history) == 1
        
        # 验证元学习器接收到数据
        assert meta_learner.learning_stats['total_samples'] == 1
    
    @pytest.mark.asyncio
    async def test_market_context_extraction(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b
    ):
        """测试市场上下文提取
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 波动率正确提取
        2. 流动性正确提取
        3. 组合集中度正确计算
        4. 资金规模正确提取
        """
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='conservative'
        )
        
        market_data = {
            'volatility': 0.30,
            'avg_volume': 2000000.0,
            'trend_strength': -0.2,
            'regime': 'bear'
        }
        
        portfolio = {
            'total_value': 200000.0,
            'positions': {
                '000001': {'value': 50000.0},
                '000002': {'value': 30000.0},
                '000003': {'value': 20000.0}
            },
            'recent_drawdown': -0.08
        }
        
        # 提取市场上下文
        context = runner._extract_market_context(market_data, portfolio)
        
        # 验证提取结果
        assert context.volatility == 0.30
        assert context.liquidity == 2000000.0
        assert context.trend_strength == -0.2
        assert context.regime == 'bear'
        assert context.aum == 200000.0
        assert context.recent_drawdown == -0.08
        
        # 验证组合集中度计算（HHI）
        # HHI = (50000/100000)^2 + (30000/100000)^2 + (20000/100000)^2
        # = 0.5^2 + 0.3^2 + 0.2^2 = 0.25 + 0.09 + 0.04 = 0.38
        assert abs(context.portfolio_concentration - 0.38) < 0.01
    
    @pytest.mark.asyncio
    async def test_architecture_failure_handling(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试架构失败处理
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 架构A失败时返回保守决策
        2. 架构B失败时返回保守决策
        3. 系统继续运行不崩溃
        """
        # 模拟架构A失败
        mock_architecture_a.decide = AsyncMock(
            side_effect=Exception("架构A失败")
        )
        
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='conservative'
        )
        
        # 运行并行测试
        result = await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 验证系统继续运行
        assert result is not None
        assert result['architecture_a_decision'].confidence == 0.0
        assert result['architecture_a_decision'].risk_level == 'low'
        assert 'error' in result['architecture_a_decision'].metadata
    
    @pytest.mark.asyncio
    async def test_multiple_runs_statistics(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试多次运行的统计信息
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 统计信息正确累积
        2. 选择率正确计算
        3. 历史记录正确保存
        """
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='balanced'
        )
        
        # 运行多次
        for _ in range(5):
            await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 获取统计信息
        stats = runner.get_statistics()
        
        # 验证统计信息
        assert stats['total_runs'] == 5
        assert stats['decision_history_size'] == 5
        assert stats['execution_mode'] == 'balanced'
        
        # 验证选择率（平衡模式下，架构B置信度更高，应该全部选择B）
        assert stats['architecture_b_selected'] == 5
        assert stats['architecture_b_selection_rate'] == 1.0
    
    @pytest.mark.asyncio
    async def test_meta_learner_integration(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试元学习器集成
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 元学习器正确接收数据
        2. 元学习器学习统计正确更新
        3. 性能评估数据正确传递
        """
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='conservative'
        )
        
        # 运行并行测试
        await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 创建性能评估数据
        decision_a = ArchitectureDecision(
            strategy='hardcoded',
            positions=[],
            risk_level='low',
            confidence=0.75,
            latency_ms=15.0
        )
        
        decision_b = ArchitectureDecision(
            strategy='strategy_layer',
            positions=[],
            risk_level='medium',
            confidence=0.85,
            latency_ms=25.0
        )
        
        market_context = MarketContext(
            volatility=0.25,
            liquidity=1500000.0,
            trend_strength=0.3,
            regime='bull',
            aum=150000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        actual_returns = {'000001': 0.02}
        
        # 评估性能（会自动调用元学习器）
        await runner._evaluate_performance(
            decision_a,
            decision_b,
            market_context,
            actual_returns
        )
        
        # 验证元学习器接收到数据
        assert meta_learner.learning_stats['total_samples'] == 1
        assert len(meta_learner.experience_db) == 1
        
        # 验证经验数据
        data_point = meta_learner.experience_db[0]
        assert data_point.market_context.volatility == 0.25
        assert data_point.market_context.regime == 'bull'
    
    def test_invalid_execution_mode(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b
    ):
        """测试无效的执行模式
        
        验证：
        1. 无效模式抛出ValueError
        2. 错误信息清晰
        """
        with pytest.raises(ValueError, match="execution_mode必须是"):
            DualArchitectureRunner(
                meta_learner=meta_learner,
                architecture_a=mock_architecture_a,
                architecture_b=mock_architecture_b,
                execution_mode='invalid_mode'
            )
    
    @pytest.mark.asyncio
    async def test_decision_selection_tie_breaking(
        self,
        meta_learner,
        mock_architecture_a,
        mock_architecture_b,
        sample_market_data,
        sample_portfolio
    ):
        """测试置信度相同时的决策选择
        
        白皮书依据: 第二章 2.2.4 风险控制元学习架构
        
        验证：
        1. 置信度相同时选择保守策略（架构A）
        """
        # 修改mock使两个架构置信度相同
        mock_architecture_a.decide = AsyncMock(return_value={
            'positions': [],
            'risk_level': 'low',
            'confidence': 0.80,
            'metadata': {}
        })
        
        mock_architecture_b.decide = AsyncMock(return_value={
            'positions': [],
            'risk_level': 'medium',
            'confidence': 0.80,
            'metadata': {}
        })
        
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_architecture_a,
            architecture_b=mock_architecture_b,
            execution_mode='balanced'
        )
        
        # 运行并行测试
        result = await runner.run_parallel(sample_market_data, sample_portfolio)
        
        # 验证选择保守策略（架构A）
        assert result['selected_decision'].strategy == 'hardcoded'


class TestDualArchitectureRunnerPerformance:
    """双架构运行器性能测试
    
    白皮书依据: 第二章 2.2.4 风险控制元学习架构
    """
    
    @pytest.mark.asyncio
    async def test_parallel_running_latency(self):
        """测试并行运行延迟
        
        验证：
        1. 并行运行延迟在合理范围内
        2. 不会因为并行而显著增加延迟
        """
        import time
        
        meta_learner = RiskControlMetaLearner()
        
        # 创建快速响应的mock
        mock_arch_a = Mock()
        mock_arch_a.decide = AsyncMock(return_value={
            'positions': [],
            'risk_level': 'low',
            'confidence': 0.75,
            'metadata': {}
        })
        
        mock_arch_b = Mock()
        mock_arch_b.decide = AsyncMock(return_value={
            'positions': [],
            'risk_level': 'medium',
            'confidence': 0.85,
            'metadata': {}
        })
        
        runner = DualArchitectureRunner(
            meta_learner=meta_learner,
            architecture_a=mock_arch_a,
            architecture_b=mock_arch_b,
            execution_mode='conservative'
        )
        
        market_data = {'volatility': 0.25, 'regime': 'bull'}
        portfolio = {'total_value': 100000.0}
        
        # 测量延迟
        start_time = time.perf_counter()
        await runner.run_parallel(market_data, portfolio)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # 验证延迟在合理范围内（<100ms）
        assert elapsed_ms < 100, f"并行运行延迟过高: {elapsed_ms:.2f}ms"
