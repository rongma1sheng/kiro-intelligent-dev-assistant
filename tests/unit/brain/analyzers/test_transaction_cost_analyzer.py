"""交易成本深度分析器单元测试

白皮书依据: 第五章 5.2.17 交易成本深度分析
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.brain.analyzers.transaction_cost_analyzer import TransactionCostAnalyzer
from src.brain.analyzers.data_models import TransactionCostAnalysis


class TestTransactionCostAnalyzer:
    """交易成本深度分析器测试类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return TransactionCostAnalyzer(
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_duty_rate=0.001
        )
    
    @pytest.fixture
    def sample_trades(self):
        """创建样本交易记录"""
        trades = []
        base_time = datetime(2023, 1, 1, 9, 30)
        
        for i in range(10):
            trade = {
                'symbol': f'00000{i % 3 + 1}',
                'side': 'buy' if i % 2 == 0 else 'sell',
                'price': 10.0 + i * 0.5,
                'quantity': 1000 + i * 100,
                'timestamp': base_time + timedelta(minutes=i * 30)
            }
            trades.append(trade)
        
        return trades
    
    @pytest.fixture
    def sample_returns(self):
        """创建样本收益率序列"""
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.015, 10), index=dates)
        return returns
    
    @pytest.fixture
    def sample_market_data(self):
        """创建样本市场数据"""
        data = {
            '000001': {'avg_volume': 1000000, 'volatility': 0.02},
            '000002': {'avg_volume': 1500000, 'volatility': 0.025},
            '000003': {'avg_volume': 800000, 'volatility': 0.018}
        }
        return pd.DataFrame(data).T
    
    @pytest.fixture
    def sample_execution_data(self):
        """创建样本执行数据"""
        return {
            'expected_prices': {
                '000001': 10.0,
                '000002': 10.5,
                '000003': 11.0
            },
            'vwap': {
                '000001': 10.05,
                '000002': 10.55,
                '000003': 11.05
            },
            'decision_prices': {
                '000001': 9.95,
                '000002': 10.45,
                '000003': 10.95
            }
        }
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.commission_rate == 0.0003
        assert analyzer.min_commission == 5.0
        assert analyzer.stamp_duty_rate == 0.001
        assert isinstance(analyzer, TransactionCostAnalyzer)
    
    def test_analyze_basic(self, analyzer, sample_trades, sample_returns):
        """测试基本分析功能"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证返回类型
        assert isinstance(result, TransactionCostAnalysis)
        assert result.strategy_id == 'test_strategy'
        assert result.total_trades == len(sample_trades)
        
        # 验证各类成本
        assert isinstance(result.commission_cost, float)
        assert isinstance(result.stamp_duty, float)
        assert isinstance(result.slippage_cost, float)
        assert isinstance(result.impact_cost, float)
        assert isinstance(result.opportunity_cost, float)
        assert isinstance(result.timing_cost, float)
        
        # 验证总成本
        assert isinstance(result.total_cost, float)
        assert result.total_cost > 0
    
    def test_analyze_with_market_data(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试带市场数据的分析"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证结果
        assert isinstance(result, TransactionCostAnalysis)
        assert result.impact_cost > 0
    
    def test_analyze_with_execution_data(self, analyzer, sample_trades, sample_returns, sample_execution_data):
        """测试带执行数据的分析"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            execution_data=sample_execution_data
        )
        
        # 验证执行质量分析
        assert isinstance(result.execution_quality_score, float)
        assert 0 <= result.execution_quality_score <= 1
        
        # 验证VWAP偏离度
        assert isinstance(result.vwap_deviation, float)
        assert result.vwap_deviation >= 0
        
        # 验证实施缺口
        assert isinstance(result.implementation_shortfall, float)
    
    def test_commission_calculation(self, analyzer, sample_trades, sample_returns):
        """测试佣金计算"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证佣金计算
        assert result.commission_cost > 0
        
        # 手动计算验证
        expected_commission = 0.0
        for trade in sample_trades:
            amount = trade['price'] * trade['quantity']
            commission = max(amount * analyzer.commission_rate, analyzer.min_commission)
            expected_commission += commission
        
        assert abs(result.commission_cost - expected_commission) < 0.01
    
    def test_stamp_duty_calculation(self, analyzer, sample_trades, sample_returns):
        """测试印花税计算"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证印花税计算（仅卖出）
        assert result.stamp_duty >= 0
        
        # 手动计算验证
        expected_stamp_duty = 0.0
        for trade in sample_trades:
            if trade['side'] == 'sell':
                amount = trade['price'] * trade['quantity']
                expected_stamp_duty += amount * analyzer.stamp_duty_rate
        
        assert abs(result.stamp_duty - expected_stamp_duty) < 0.01
    
    def test_cost_ratio(self, analyzer, sample_trades, sample_returns):
        """测试成本比率"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证成本比率
        assert isinstance(result.cost_ratio, float)
        assert result.cost_ratio >= 0
    
    def test_cost_efficiency(self, analyzer, sample_trades, sample_returns):
        """测试成本效率"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证成本效率（可以是int或float）
        assert isinstance(result.cost_efficiency, (int, float))
        assert 0 <= result.cost_efficiency <= 1
    
    def test_cost_level_classification(self, analyzer, sample_trades, sample_returns):
        """测试成本水平分类"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证成本水平
        assert isinstance(result.cost_level, str)
        assert result.cost_level in ['low', 'medium', 'high', 'very_high']
    
    def test_cost_breakdown_by_type(self, analyzer, sample_trades, sample_returns):
        """测试按类型分解成本"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证成本分解
        assert isinstance(result.cost_breakdown_by_type, dict)
        assert 'commission' in result.cost_breakdown_by_type
        assert 'stamp_duty' in result.cost_breakdown_by_type
        assert 'slippage' in result.cost_breakdown_by_type
        assert 'impact' in result.cost_breakdown_by_type
        assert 'opportunity' in result.cost_breakdown_by_type
        assert 'timing' in result.cost_breakdown_by_type
    
    def test_cost_breakdown_by_time(self, analyzer, sample_trades, sample_returns):
        """测试按时间分解成本"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证按时间分解
        assert isinstance(result.cost_breakdown_by_time, dict)
    
    def test_cost_breakdown_by_symbol(self, analyzer, sample_trades, sample_returns):
        """测试按股票分解成本"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证按股票分解
        assert isinstance(result.cost_breakdown_by_symbol, dict)
        assert len(result.cost_breakdown_by_symbol) > 0
    
    def test_cost_breakdown_by_size(self, analyzer, sample_trades, sample_returns):
        """测试按交易规模分解成本"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证按规模分解
        assert isinstance(result.cost_breakdown_by_size, dict)
        assert 'small' in result.cost_breakdown_by_size
        assert 'medium' in result.cost_breakdown_by_size
        assert 'large' in result.cost_breakdown_by_size
        assert 'xlarge' in result.cost_breakdown_by_size
    
    def test_high_cost_trades_identification(self, analyzer, sample_trades, sample_returns):
        """测试高成本交易识别"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证高成本交易
        assert isinstance(result.high_cost_trades, list)
    
    def test_cost_outliers_identification(self, analyzer, sample_trades, sample_returns):
        """测试成本异常值识别"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证成本异常值
        assert isinstance(result.cost_outliers, list)
    
    def test_optimal_execution_strategy(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试最优执行策略"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证最优执行策略
        assert isinstance(result.optimal_execution_strategy, str)
        assert result.optimal_execution_strategy in ['aggressive_twap', 'iceberg_vwap', 'standard_vwap']
    
    def test_execution_algorithm_recommendation(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试执行算法推荐"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证执行算法推荐
        assert isinstance(result.execution_algorithm_recommendation, str)
        assert result.execution_algorithm_recommendation in ['IS', 'POV', 'TWAP', 'VWAP']
    
    def test_order_splitting_strategy(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试订单拆分策略"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证订单拆分策略
        assert isinstance(result.order_splitting_strategy, dict)
        assert 'num_splits' in result.order_splitting_strategy
        assert 'split_interval_minutes' in result.order_splitting_strategy
        assert 'split_method' in result.order_splitting_strategy
    
    def test_timing_optimization(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试时机优化建议"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证时机优化
        assert isinstance(result.timing_optimization, list)
    
    def test_liquidity_seeking_strategy(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试流动性寻求策略"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证流动性寻求策略
        assert isinstance(result.liquidity_seeking_strategy, dict)
        assert 'strategy_type' in result.liquidity_seeking_strategy
    
    def test_dark_pool_opportunities(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试暗池交易机会"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证暗池交易机会
        assert isinstance(result.dark_pool_opportunities, list)
    
    def test_cost_reduction_potential(self, analyzer, sample_trades, sample_returns, sample_market_data):
        """测试成本降低潜力"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns,
            market_data=sample_market_data
        )
        
        # 验证成本降低潜力
        assert isinstance(result.cost_reduction_potential, float)
        assert 0 <= result.cost_reduction_potential <= 1
        
        # 验证预期节省
        assert isinstance(result.expected_savings, float)
        assert result.expected_savings >= 0
    
    def test_optimization_suggestions(self, analyzer, sample_trades, sample_returns):
        """测试优化建议"""
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        
        # 验证优化建议
        assert isinstance(result.optimization_suggestions, list)
        assert len(result.optimization_suggestions) > 0
    
    def test_invalid_input_empty_trades(self, analyzer, sample_returns):
        """测试无效输入：空交易列表"""
        with pytest.raises(ValueError, match="交易记录列表不能为空"):
            analyzer.analyze(
                strategy_id='test_strategy',
                trades=[],
                returns=sample_returns
            )
    
    def test_invalid_input_missing_fields(self, analyzer, sample_returns):
        """测试无效输入：缺少必需字段"""
        incomplete_trades = [
            {'symbol': '000001', 'side': 'buy'}  # 缺少price, quantity, timestamp
        ]
        
        with pytest.raises(ValueError, match="交易记录缺少必需字段"):
            analyzer.analyze(
                strategy_id='test_strategy',
                trades=incomplete_trades,
                returns=sample_returns
            )
    
    def test_performance_requirement(self, analyzer, sample_trades, sample_returns):
        """测试性能要求：成本分析延迟 < 3秒"""
        start_time = datetime.now()
        result = analyzer.analyze(
            strategy_id='test_strategy',
            trades=sample_trades,
            returns=sample_returns
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 验证性能要求
        assert elapsed < 3.0, f"成本分析延迟({elapsed:.2f}秒)超过3秒要求"
        assert isinstance(result, TransactionCostAnalysis)
