"""滚动回测框架单元测试

白皮书依据: 第四章 4.2 斯巴达竞技场 - 稳健性测试
测试任务: RollingBacktest框架功能验证

测试覆盖:
- 窗口生成逻辑（固定/扩展）
- 回测执行流程
- 稳定性指标计算
- 聚合指标计算
- 稳定性检查
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional

from src.evolution.rolling_backtest import (
    RollingBacktest,
    WindowMode,
    WindowResult,
    RollingBacktestResult
)
from src.evolution.strategy_evaluator import MarketType


class TestRollingBacktest:
    """测试RollingBacktest基础功能"""
    
    @pytest.fixture
    def rolling_backtest_fixed(self):
        """创建固定窗口模式的滚动回测"""
        return RollingBacktest(
            market_type=MarketType.A_STOCK,
            window_mode=WindowMode.FIXED,
            window_size_days=252,
            step_size_days=63
        )
    
    @pytest.fixture
    def rolling_backtest_expanding(self):
        """创建扩展窗口模式的滚动回测"""
        return RollingBacktest(
            market_type=MarketType.A_STOCK,
            window_mode=WindowMode.EXPANDING,
            window_size_days=252,
            step_size_days=63,
            min_window_size_days=126
        )
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据（3年）"""
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        data = pd.DataFrame({
            'close': 100 * (1 + np.random.randn(756) * 0.01).cumprod(),
            'volume': np.random.randint(1000000, 10000000, 756)
        }, index=dates)
        return data
    
    @pytest.fixture
    def simple_strategy(self):
        """创建简单策略函数"""
        def strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            # 简单的买入持有策略
            equity = data['close'] / data['close'].iloc[0] * 100
            # 模拟交易
            trades = pd.Series([0.01, -0.005, 0.02, -0.01] * (len(data) // 20))
            return equity, trades
        return strategy
    
    def test_initialization_fixed(self, rolling_backtest_fixed):
        """测试固定窗口模式初始化"""
        assert rolling_backtest_fixed is not None
        assert rolling_backtest_fixed.window_mode == WindowMode.FIXED
        assert rolling_backtest_fixed.window_size_days == 252
        assert rolling_backtest_fixed.step_size_days == 63
    
    def test_initialization_expanding(self, rolling_backtest_expanding):
        """测试扩展窗口模式初始化"""
        assert rolling_backtest_expanding is not None
        assert rolling_backtest_expanding.window_mode == WindowMode.EXPANDING
        assert rolling_backtest_expanding.min_window_size_days == 126
    
    def test_initialization_invalid_window_size(self):
        """测试无效的窗口大小"""
        with pytest.raises(ValueError, match="窗口大小必须"):
            RollingBacktest(
                window_size_days=100,
                min_window_size_days=126
            )
    
    def test_initialization_invalid_step_size(self):
        """测试无效的步长"""
        with pytest.raises(ValueError, match="步长必须"):
            RollingBacktest(
                window_size_days=252,
                step_size_days=0
            )


class TestWindowGeneration:
    """测试窗口生成逻辑"""
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        data = pd.DataFrame({'value': range(756)}, index=dates)
        return data
    
    def test_generate_windows_fixed(self, sample_data):
        """测试固定窗口生成"""
        rb = RollingBacktest(
            window_mode=WindowMode.FIXED,
            window_size_days=252,
            step_size_days=63
        )
        
        windows = rb._generate_windows(sample_data)
        
        # 验证窗口数量
        assert len(windows) > 0
        
        # 验证窗口大小
        for start_idx, end_idx in windows:
            assert end_idx - start_idx == 252
        
        # 验证窗口步长
        if len(windows) > 1:
            assert windows[1][0] - windows[0][0] == 63
    
    def test_generate_windows_expanding(self, sample_data):
        """测试扩展窗口生成"""
        rb = RollingBacktest(
            window_mode=WindowMode.EXPANDING,
            window_size_days=252,
            step_size_days=63,
            min_window_size_days=126
        )
        
        windows = rb._generate_windows(sample_data)
        
        # 验证窗口数量
        assert len(windows) > 0
        
        # 验证起始点固定
        for start_idx, end_idx in windows:
            assert start_idx == 0
        
        # 验证窗口递增
        if len(windows) > 1:
            assert windows[1][1] > windows[0][1]
    
    def test_generate_windows_insufficient_data(self):
        """测试数据不足的情况"""
        rb = RollingBacktest(
            window_size_days=252,
            min_window_size_days=126
        )
        
        # 只有100天数据
        dates = pd.date_range('2021-01-01', periods=100, freq='D')
        data = pd.DataFrame({'value': range(100)}, index=dates)
        
        windows = rb._generate_windows(data)
        
        # 应该没有窗口
        assert len(windows) == 0


class TestBacktestExecution:
    """测试回测执行流程"""
    
    @pytest.fixture
    def rolling_backtest(self):
        return RollingBacktest(
            market_type=MarketType.A_STOCK,
            window_mode=WindowMode.FIXED,
            window_size_days=252,
            step_size_days=126
        )
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据（2年）"""
        dates = pd.date_range('2022-01-01', periods=504, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 504)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod()
        }, index=dates)
        return data
    
    @pytest.fixture
    def profitable_strategy(self):
        """创建盈利策略"""
        def strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            # 模拟稳定盈利
            equity = data['close'] / data['close'].iloc[0] * 100 * 1.1
            trades = pd.Series([0.02, -0.01] * (len(data) // 10))
            return equity, trades
        return strategy
    
    def test_run_backtest_success(self, rolling_backtest, sample_data, profitable_strategy):
        """测试成功运行回测"""
        result = rolling_backtest.run_backtest(
            strategy_func=profitable_strategy,
            data=sample_data,
            freq=252
        )
        
        assert isinstance(result, RollingBacktestResult)
        assert len(result.window_results) > 0
        assert result.stability_metrics is not None
        assert result.aggregated_metrics is not None
    
    def test_run_backtest_insufficient_data(self, rolling_backtest, profitable_strategy):
        """测试数据不足的情况"""
        # 只有100天数据
        dates = pd.date_range('2022-01-01', periods=100, freq='D')
        data = pd.DataFrame({'close': range(100)}, index=dates)
        
        with pytest.raises(ValueError, match="数据长度不足"):
            rolling_backtest.run_backtest(
                strategy_func=profitable_strategy,
                data=data,
                freq=252
            )
    
    def test_window_results_structure(self, rolling_backtest, sample_data, profitable_strategy):
        """测试窗口结果结构"""
        result = rolling_backtest.run_backtest(
            strategy_func=profitable_strategy,
            data=sample_data,
            freq=252
        )
        
        for window_result in result.window_results:
            assert isinstance(window_result, WindowResult)
            assert window_result.window_id >= 0
            assert window_result.start_date < window_result.end_date
            assert len(window_result.equity_curve) > 0
            assert 'annual_return' in window_result.metrics
            assert 'sharpe' in window_result.metrics


class TestStabilityMetrics:
    """测试稳定性指标计算"""
    
    @pytest.fixture
    def rolling_backtest(self):
        return RollingBacktest(
            market_type=MarketType.A_STOCK,
            window_mode=WindowMode.FIXED,
            window_size_days=252,
            step_size_days=126
        )
    
    @pytest.fixture
    def stable_strategy_data(self):
        """创建稳定策略的数据"""
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        np.random.seed(42)
        # 稳定的正收益
        returns = np.random.normal(0.0008, 0.005, 756)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod()
        }, index=dates)
        return data
    
    @pytest.fixture
    def unstable_strategy_data(self):
        """创建不稳定策略的数据"""
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        np.random.seed(123)
        # 波动很大的收益
        returns = np.random.normal(0.0, 0.03, 756)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod()
        }, index=dates)
        return data
    
    @pytest.fixture
    def simple_strategy(self):
        def strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            equity = data['close'] / data['close'].iloc[0] * 100
            return equity, None
        return strategy
    
    def test_stability_metrics_stable_strategy(
        self,
        rolling_backtest,
        stable_strategy_data,
        simple_strategy
    ):
        """测试稳定策略的稳定性指标"""
        result = rolling_backtest.run_backtest(
            strategy_func=simple_strategy,
            data=stable_strategy_data,
            freq=252
        )
        
        stability = result.stability_metrics
        
        # 稳定策略应该有高稳定性
        assert stability['return_stability'] > 0
        assert stability['positive_window_ratio'] > 0.5
        assert 'worst_window_return' in stability
        assert 'best_window_return' in stability
    
    def test_stability_metrics_structure(
        self,
        rolling_backtest,
        stable_strategy_data,
        simple_strategy
    ):
        """测试稳定性指标结构"""
        result = rolling_backtest.run_backtest(
            strategy_func=simple_strategy,
            data=stable_strategy_data,
            freq=252
        )
        
        stability = result.stability_metrics
        
        # 验证所有必需字段
        required_fields = [
            'return_stability',
            'sharpe_stability',
            'positive_window_ratio',
            'worst_window_return',
            'worst_window_period',
            'best_window_return',
            'best_window_period',
            'return_range',
            'sharpe_range'
        ]
        
        for field in required_fields:
            assert field in stability


class TestAggregatedMetrics:
    """测试聚合指标计算"""
    
    @pytest.fixture
    def rolling_backtest(self):
        return RollingBacktest(
            market_type=MarketType.A_STOCK,
            window_mode=WindowMode.FIXED,
            window_size_days=252,
            step_size_days=126
        )
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 756)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod()
        }, index=dates)
        return data
    
    @pytest.fixture
    def simple_strategy(self):
        def strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            equity = data['close'] / data['close'].iloc[0] * 100
            return equity, None
        return strategy
    
    def test_aggregated_metrics_structure(
        self,
        rolling_backtest,
        sample_data,
        simple_strategy
    ):
        """测试聚合指标结构"""
        result = rolling_backtest.run_backtest(
            strategy_func=simple_strategy,
            data=sample_data,
            freq=252
        )
        
        agg = result.aggregated_metrics
        
        # 验证所有必需字段
        required_fields = [
            'mean_annual_return',
            'median_annual_return',
            'std_annual_return',
            'min_annual_return',
            'max_annual_return',
            'mean_sharpe',
            'median_sharpe',
            'std_sharpe',
            'min_sharpe',
            'max_sharpe',
            'mean_sortino',
            'mean_max_drawdown',
            'worst_max_drawdown',
            'num_windows'
        ]
        
        for field in required_fields:
            assert field in agg
    
    def test_aggregated_metrics_values(
        self,
        rolling_backtest,
        sample_data,
        simple_strategy
    ):
        """测试聚合指标值的合理性"""
        result = rolling_backtest.run_backtest(
            strategy_func=simple_strategy,
            data=sample_data,
            freq=252
        )
        
        agg = result.aggregated_metrics
        
        # 验证值的合理性
        assert agg['num_windows'] == len(result.window_results)
        assert agg['min_annual_return'] <= agg['mean_annual_return'] <= agg['max_annual_return']
        assert agg['min_sharpe'] <= agg['mean_sharpe'] <= agg['max_sharpe']
        assert agg['worst_max_drawdown'] <= agg['mean_max_drawdown'] <= 0


class TestStabilityCheck:
    """测试稳定性检查功能"""
    
    @pytest.fixture
    def rolling_backtest(self):
        return RollingBacktest(
            market_type=MarketType.A_STOCK,
            window_mode=WindowMode.FIXED,
            window_size_days=252,
            step_size_days=126
        )
    
    @pytest.fixture
    def stable_result(self, rolling_backtest):
        """创建稳定策略的结果"""
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        np.random.seed(42)
        # 稳定的正收益
        returns = np.random.normal(0.0008, 0.005, 756)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod()
        }, index=dates)
        
        def strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            equity = data['close'] / data['close'].iloc[0] * 100
            return equity, None
        
        return rolling_backtest.run_backtest(strategy, data, freq=252)
    
    def test_check_stability_stable_strategy(self, rolling_backtest, stable_result):
        """测试稳定策略的稳定性检查"""
        check_result = rolling_backtest.check_stability(
            result=stable_result,
            min_positive_ratio=0.7,
            max_return_cv=1.0,
            max_sharpe_cv=0.5
        )
        
        assert 'stable' in check_result
        assert 'passed_criteria' in check_result
        assert 'failed_criteria' in check_result
        assert isinstance(check_result['stable'], bool)
    
    def test_check_stability_criteria(self, rolling_backtest, stable_result):
        """测试稳定性检查标准"""
        check_result = rolling_backtest.check_stability(
            result=stable_result,
            min_positive_ratio=0.7,
            max_return_cv=1.0,
            max_sharpe_cv=0.5
        )
        
        # 验证标准列表
        total_criteria = len(check_result['passed_criteria']) + len(check_result['failed_criteria'])
        assert total_criteria >= 4  # 至少4个检查标准


class TestEdgeCases:
    """测试边界条件"""
    
    def test_minimal_data(self):
        """测试最小数据量"""
        rb = RollingBacktest(
            window_size_days=126,
            step_size_days=63,
            min_window_size_days=126
        )
        
        # 刚好够一个窗口
        dates = pd.date_range('2022-01-01', periods=126, freq='D')
        data = pd.DataFrame({'close': range(126)}, index=dates)
        
        def strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            equity = pd.Series(range(len(data)), index=data.index)
            return equity, None
        
        result = rb.run_backtest(strategy, data, freq=252)
        
        # 应该有1个窗口
        assert len(result.window_results) == 1
    
    def test_large_step_size(self):
        """测试大步长（无重叠窗口）"""
        rb = RollingBacktest(
            window_size_days=126,
            step_size_days=126,  # 步长等于窗口大小
            min_window_size_days=126
        )
        
        dates = pd.date_range('2021-01-01', periods=504, freq='D')
        data = pd.DataFrame({'close': range(504)}, index=dates)
        
        windows = rb._generate_windows(data)
        
        # 验证窗口不重叠
        for i in range(len(windows) - 1):
            assert windows[i][1] == windows[i+1][0]
    
    def test_strategy_exception_handling(self):
        """测试策略异常处理"""
        rb = RollingBacktest(
            window_size_days=252,
            step_size_days=126
        )
        
        dates = pd.date_range('2021-01-01', periods=504, freq='D')
        data = pd.DataFrame({'close': range(504)}, index=dates)
        
        def failing_strategy(data: pd.DataFrame) -> Tuple[pd.Series, Optional[pd.Series]]:
            raise ValueError("策略执行失败")
        
        with pytest.raises(ValueError, match="策略执行失败"):
            rb.run_backtest(failing_strategy, data, freq=252)
