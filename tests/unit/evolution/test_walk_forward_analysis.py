"""Walk-Forward分析框架单元测试

白皮书依据: 第四章 4.2 斯巴达竞技场 - 防过拟合测试
测试任务: WalkForwardAnalysis框架功能验证

测试覆盖:
- 周期生成逻辑（锚定/滚动）
- 样本内优化和样本外验证
- 过拟合检测指标
- 效率比率计算
- OOS净值曲线合并
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from src.evolution.walk_forward_analysis import (
    WalkForwardAnalysis,
    WalkForwardMode,
    WalkForwardPeriod,
    WalkForwardResult
)
from src.evolution.strategy_evaluator import MarketType


class TestWalkForwardAnalysis:
    """测试WalkForwardAnalysis基础功能"""
    
    @pytest.fixture
    def wfa_anchored(self):
        """创建锚定模式的WFA"""
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ANCHORED,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
        )
    
    @pytest.fixture
    def wfa_rolling(self):
        """创建滚动模式的WFA"""
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
        )
    
    def test_initialization_anchored(self, wfa_anchored):
        """测试锚定模式初始化"""
        assert wfa_anchored is not None
        assert wfa_anchored.mode == WalkForwardMode.ANCHORED
        assert wfa_anchored.is_ratio == 0.7
        assert abs(wfa_anchored.oos_ratio - 0.3) < 0.001
    
    def test_initialization_rolling(self, wfa_rolling):
        """测试滚动模式初始化"""
        assert wfa_rolling is not None
        assert wfa_rolling.mode == WalkForwardMode.ROLLING
        assert wfa_rolling.min_is_days == 252
        assert wfa_rolling.min_oos_days == 63
    
    def test_initialization_invalid_is_ratio(self):
        """测试无效的IS占比"""
        with pytest.raises(ValueError, match="样本内占比必须"):
            WalkForwardAnalysis(is_ratio=1.5)
        
        with pytest.raises(ValueError, match="样本内占比必须"):
            WalkForwardAnalysis(is_ratio=0.0)
    
    def test_initialization_invalid_days(self):
        """测试无效的天数参数"""
        with pytest.raises(ValueError, match="最小样本内天数必须"):
            WalkForwardAnalysis(min_is_days=0)
        
        with pytest.raises(ValueError, match="最小样本外天数必须"):
            WalkForwardAnalysis(min_oos_days=-1)


class TestPeriodGeneration:
    """测试周期生成逻辑"""
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据（3年）"""
        dates = pd.date_range('2021-01-01', periods=756, freq='D')
        data = pd.DataFrame({'value': range(756)}, index=dates)
        return data
    
    def test_generate_periods_anchored(self, sample_data):
        """测试锚定模式周期生成"""
        wfa = WalkForwardAnalysis(
            mode=WalkForwardMode.ANCHORED,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
        )
        
        periods = wfa._generate_periods(sample_data)
        
        # 验证周期数量
        assert len(periods) > 0
        
        # 验证IS起点固定
        for is_data, oos_data in periods:
            assert is_data.index[0] == sample_data.index[0]
        
        # 验证IS递增
        if len(periods) > 1:
            assert len(periods[1][0]) > len(periods[0][0])
    
    def test_generate_periods_rolling(self, sample_data):
        """测试滚动模式周期生成"""
        wfa = WalkForwardAnalysis(
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
        )
        
        periods = wfa._generate_periods(sample_data)
        
        # 验证周期数量
        assert len(periods) > 0
        
        # 验证IS大小固定
        for is_data, oos_data in periods:
            assert len(is_data) == 252
        
        # 验证周期向前滚动
        if len(periods) > 1:
            assert periods[1][0].index[0] > periods[0][0].index[0]
    
    def test_generate_periods_insufficient_data(self):
        """测试数据不足的情况"""
        wfa = WalkForwardAnalysis(
            min_is_days=252,
            min_oos_days=63
        )
        
        # 只有200天数据
        dates = pd.date_range('2022-01-01', periods=200, freq='D')
        data = pd.DataFrame({'value': range(200)}, index=dates)
        
        periods = wfa._generate_periods(data)
        
        # 应该没有周期
        assert len(periods) == 0


class TestAnalysisExecution:
    """测试分析执行流程"""
    
    @pytest.fixture
    def wfa(self):
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
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
    def simple_optimizer(self):
        """创建简单的参数优化器"""
        def optimize(data: pd.DataFrame) -> Dict[str, Any]:
            # 简单返回固定参数
            return {'param1': 1.0, 'param2': 0.5}
        return optimize
    
    @pytest.fixture
    def simple_backtest(self):
        """创建简单的回测函数"""
        def backtest(
            data: pd.DataFrame,
            params: Dict[str, Any]
        ) -> Tuple[pd.Series, Optional[pd.Series]]:
            # 简单的买入持有
            equity = data['close'] / data['close'].iloc[0] * 100
            trades = pd.Series([0.01, -0.005] * (len(data) // 10))
            return equity, trades
        return backtest
    
    def test_run_analysis_success(
        self,
        wfa,
        sample_data,
        simple_optimizer,
        simple_backtest
    ):
        """测试成功运行分析"""
        result = wfa.run_analysis(
            optimize_func=simple_optimizer,
            backtest_func=simple_backtest,
            data=sample_data,
            freq=252
        )
        
        assert isinstance(result, WalkForwardResult)
        assert len(result.periods) > 0
        assert result.combined_oos_equity is not None
        assert result.combined_oos_metrics is not None
        assert result.overfitting_metrics is not None
    
    def test_run_analysis_insufficient_data(
        self,
        wfa,
        simple_optimizer,
        simple_backtest
    ):
        """测试数据不足的情况"""
        # 只有200天数据
        dates = pd.date_range('2022-01-01', periods=200, freq='D')
        data = pd.DataFrame({'close': range(200)}, index=dates)
        
        with pytest.raises(ValueError, match="数据长度不足"):
            wfa.run_analysis(
                optimize_func=simple_optimizer,
                backtest_func=simple_backtest,
                data=data,
                freq=252
            )
    
    def test_period_structure(
        self,
        wfa,
        sample_data,
        simple_optimizer,
        simple_backtest
    ):
        """测试周期结构"""
        result = wfa.run_analysis(
            optimize_func=simple_optimizer,
            backtest_func=simple_backtest,
            data=sample_data,
            freq=252
        )
        
        for period in result.periods:
            assert isinstance(period, WalkForwardPeriod)
            assert period.period_id >= 0
            assert period.is_start_date < period.is_end_date
            assert period.oos_start_date < period.oos_end_date
            assert period.is_end_date <= period.oos_start_date
            assert period.optimal_params is not None
            assert 'annual_return' in period.is_metrics
            assert 'annual_return' in period.oos_metrics


class TestOOSEquityCombination:
    """测试OOS净值曲线合并"""
    
    @pytest.fixture
    def wfa(self):
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
        )
    
    @pytest.fixture
    def sample_periods(self):
        """创建样本周期数据"""
        periods = []
        
        # 创建3个周期
        for i in range(3):
            dates = pd.date_range(f'2022-{i+1:02d}-01', periods=63, freq='D')
            oos_equity = pd.Series(
                100 * (1 + np.random.randn(63) * 0.01).cumprod(),
                index=dates
            )
            
            period = WalkForwardPeriod(
                period_id=i,
                is_start_date=dates[0],
                is_end_date=dates[0],
                oos_start_date=dates[0],
                oos_end_date=dates[-1],
                is_data=pd.DataFrame(),
                oos_data=pd.DataFrame(),
                optimal_params={},
                is_metrics={},
                oos_metrics={},
                is_equity=pd.Series(),
                oos_equity=oos_equity
            )
            periods.append(period)
        
        return periods
    
    def test_combine_oos_equity(self, wfa, sample_periods):
        """测试OOS净值曲线合并"""
        combined = wfa._combine_oos_equity(sample_periods)
        
        # 验证合并后的长度
        expected_length = sum(len(p.oos_equity) for p in sample_periods) - (len(sample_periods) - 1)
        assert len(combined) == expected_length
        
        # 验证连续性（第一个点应该是100）
        assert combined.iloc[0] == sample_periods[0].oos_equity.iloc[0]
    
    def test_combine_oos_equity_single_period(self, wfa, sample_periods):
        """测试单个周期的合并"""
        combined = wfa._combine_oos_equity([sample_periods[0]])
        
        # 应该等于原始净值曲线
        pd.testing.assert_series_equal(combined, sample_periods[0].oos_equity)


class TestOverfittingMetrics:
    """测试过拟合检测指标"""
    
    @pytest.fixture
    def wfa(self):
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7
        )
    
    @pytest.fixture
    def good_periods(self):
        """创建未过拟合的周期（IS和OOS表现接近）"""
        periods = []
        for i in range(5):
            period = WalkForwardPeriod(
                period_id=i,
                is_start_date=datetime(2022, 1, 1),
                is_end_date=datetime(2022, 12, 31),
                oos_start_date=datetime(2023, 1, 1),
                oos_end_date=datetime(2023, 3, 31),
                is_data=pd.DataFrame(),
                oos_data=pd.DataFrame(),
                optimal_params={},
                is_metrics={
                    'annual_return': 0.15 + np.random.randn() * 0.02,
                    'sharpe': 1.5 + np.random.randn() * 0.1
                },
                oos_metrics={
                    'annual_return': 0.13 + np.random.randn() * 0.02,
                    'sharpe': 1.3 + np.random.randn() * 0.1
                },
                is_equity=pd.Series(),
                oos_equity=pd.Series()
            )
            periods.append(period)
        return periods
    
    @pytest.fixture
    def overfitted_periods(self):
        """创建过拟合的周期（IS好，OOS差）"""
        periods = []
        for i in range(5):
            period = WalkForwardPeriod(
                period_id=i,
                is_start_date=datetime(2022, 1, 1),
                is_end_date=datetime(2022, 12, 31),
                oos_start_date=datetime(2023, 1, 1),
                oos_end_date=datetime(2023, 3, 31),
                is_data=pd.DataFrame(),
                oos_data=pd.DataFrame(),
                optimal_params={},
                is_metrics={
                    'annual_return': 0.25,
                    'sharpe': 2.0
                },
                oos_metrics={
                    'annual_return': -0.05 if i % 2 == 0 else 0.05,
                    'sharpe': 0.3 if i % 2 == 0 else 0.5
                },
                is_equity=pd.Series(),
                oos_equity=pd.Series()
            )
            periods.append(period)
        return periods
    
    def test_overfitting_metrics_good_strategy(self, wfa, good_periods):
        """测试未过拟合策略的指标"""
        metrics = wfa._calculate_overfitting_metrics(good_periods)
        
        # 验证指标结构
        assert 'sharpe_degradation' in metrics
        assert 'return_degradation' in metrics
        assert 'consistency_ratio' in metrics
        assert 'failure_ratio' in metrics
        assert 'is_overfitted' in metrics
        
        # 未过拟合策略应该有较小的衰减
        assert metrics['sharpe_degradation'] < 0.5
        assert metrics['consistency_ratio'] > 0.6
        assert metrics['is_overfitted'] is False
    
    def test_overfitting_metrics_overfitted_strategy(self, wfa, overfitted_periods):
        """测试过拟合策略的指标"""
        metrics = wfa._calculate_overfitting_metrics(overfitted_periods)
        
        # 过拟合策略应该有大的衰减
        assert metrics['sharpe_degradation'] > 0.5
        assert metrics['failure_ratio'] > 0
        assert metrics['is_overfitted'] == True


class TestEfficiencyRatio:
    """测试效率比率计算"""
    
    @pytest.fixture
    def wfa(self):
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ROLLING
        )
    
    def test_efficiency_ratio_high(self, wfa):
        """测试高效率比率（OOS接近IS）"""
        periods = []
        for i in range(5):
            period = WalkForwardPeriod(
                period_id=i,
                is_start_date=datetime(2022, 1, 1),
                is_end_date=datetime(2022, 12, 31),
                oos_start_date=datetime(2023, 1, 1),
                oos_end_date=datetime(2023, 3, 31),
                is_data=pd.DataFrame(),
                oos_data=pd.DataFrame(),
                optimal_params={},
                is_metrics={'sharpe': 1.5},
                oos_metrics={'sharpe': 1.4},
                is_equity=pd.Series(),
                oos_equity=pd.Series()
            )
            periods.append(period)
        
        efficiency = wfa._calculate_efficiency_ratio(periods)
        
        # 效率比率应该接近1
        assert 0.8 < efficiency <= 1.0
    
    def test_efficiency_ratio_low(self, wfa):
        """测试低效率比率（OOS远低于IS）"""
        periods = []
        for i in range(5):
            period = WalkForwardPeriod(
                period_id=i,
                is_start_date=datetime(2022, 1, 1),
                is_end_date=datetime(2022, 12, 31),
                oos_start_date=datetime(2023, 1, 1),
                oos_end_date=datetime(2023, 3, 31),
                is_data=pd.DataFrame(),
                oos_data=pd.DataFrame(),
                optimal_params={},
                is_metrics={'sharpe': 2.0},
                oos_metrics={'sharpe': 0.5},
                is_equity=pd.Series(),
                oos_equity=pd.Series()
            )
            periods.append(period)
        
        efficiency = wfa._calculate_efficiency_ratio(periods)
        
        # 效率比率应该较低
        assert 0.0 <= efficiency < 0.5
    
    def test_efficiency_ratio_negative_is(self, wfa):
        """测试IS为负的情况"""
        periods = []
        for i in range(5):
            period = WalkForwardPeriod(
                period_id=i,
                is_start_date=datetime(2022, 1, 1),
                is_end_date=datetime(2022, 12, 31),
                oos_start_date=datetime(2023, 1, 1),
                oos_end_date=datetime(2023, 3, 31),
                is_data=pd.DataFrame(),
                oos_data=pd.DataFrame(),
                optimal_params={},
                is_metrics={'sharpe': -0.5},
                oos_metrics={'sharpe': 0.5},
                is_equity=pd.Series(),
                oos_equity=pd.Series()
            )
            periods.append(period)
        
        efficiency = wfa._calculate_efficiency_ratio(periods)
        
        # IS为负时，效率比率应该为0
        assert efficiency == 0.0


class TestOverfittingCheck:
    """测试过拟合检查功能"""
    
    @pytest.fixture
    def wfa(self):
        return WalkForwardAnalysis(
            market_type=MarketType.A_STOCK,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7,
            min_is_days=252,
            min_oos_days=63
        )
    
    @pytest.fixture
    def good_result(self):
        """创建未过拟合的结果"""
        return WalkForwardResult(
            periods=[],
            combined_oos_equity=pd.Series(),
            combined_oos_metrics={},
            overfitting_metrics={
                'sharpe_degradation': 0.2,
                'return_degradation': 0.02,
                'consistency_ratio': 0.8,
                'failure_ratio': 0.1,
                'is_overfitted': False
            },
            efficiency_ratio=0.8,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7
        )
    
    @pytest.fixture
    def overfitted_result(self):
        """创建过拟合的结果"""
        return WalkForwardResult(
            periods=[],
            combined_oos_equity=pd.Series(),
            combined_oos_metrics={},
            overfitting_metrics={
                'sharpe_degradation': 1.0,
                'return_degradation': 0.15,
                'consistency_ratio': 0.4,
                'failure_ratio': 0.5,
                'is_overfitted': True
            },
            efficiency_ratio=0.3,
            mode=WalkForwardMode.ROLLING,
            is_ratio=0.7
        )
    
    def test_check_overfitting_good_strategy(self, wfa, good_result):
        """测试未过拟合策略的检查"""
        check_result = wfa.check_overfitting(
            result=good_result,
            min_efficiency_ratio=0.5,
            max_sharpe_degradation=0.5,
            min_consistency_ratio=0.6
        )
        
        assert check_result['not_overfitted'] is True
        assert len(check_result['passed_criteria']) > 0
        assert len(check_result['failed_criteria']) == 0
    
    def test_check_overfitting_overfitted_strategy(self, wfa, overfitted_result):
        """测试过拟合策略的检查"""
        check_result = wfa.check_overfitting(
            result=overfitted_result,
            min_efficiency_ratio=0.5,
            max_sharpe_degradation=0.5,
            min_consistency_ratio=0.6
        )
        
        assert check_result['not_overfitted'] is False
        assert len(check_result['failed_criteria']) > 0


class TestEdgeCases:
    """测试边界条件"""
    
    def test_minimal_data(self):
        """测试最小数据量"""
        wfa = WalkForwardAnalysis(
            min_is_days=126,
            min_oos_days=63
        )
        
        # 刚好够一个周期
        dates = pd.date_range('2022-01-01', periods=189, freq='D')
        data = pd.DataFrame({'close': range(189)}, index=dates)
        
        def optimize(data: pd.DataFrame) -> Dict[str, Any]:
            return {'param': 1.0}
        
        def backtest(
            data: pd.DataFrame,
            params: Dict[str, Any]
        ) -> Tuple[pd.Series, Optional[pd.Series]]:
            equity = pd.Series(range(len(data)), index=data.index)
            return equity, None
        
        result = wfa.run_analysis(optimize, backtest, data, freq=252)
        
        # 应该有1个周期
        assert len(result.periods) == 1
    
    def test_optimizer_exception_handling(self):
        """测试优化器异常处理"""
        wfa = WalkForwardAnalysis(
            min_is_days=252,
            min_oos_days=63
        )
        
        dates = pd.date_range('2021-01-01', periods=504, freq='D')
        data = pd.DataFrame({'close': range(504)}, index=dates)
        
        def failing_optimizer(data: pd.DataFrame) -> Dict[str, Any]:
            raise ValueError("优化失败")
        
        def backtest(
            data: pd.DataFrame,
            params: Dict[str, Any]
        ) -> Tuple[pd.Series, Optional[pd.Series]]:
            equity = pd.Series(range(len(data)), index=data.index)
            return equity, None
        
        with pytest.raises(ValueError, match="优化失败"):
            wfa.run_analysis(failing_optimizer, backtest, data, freq=252)
    
    def test_backtest_exception_handling(self):
        """测试回测异常处理"""
        wfa = WalkForwardAnalysis(
            min_is_days=252,
            min_oos_days=63
        )
        
        dates = pd.date_range('2021-01-01', periods=504, freq='D')
        data = pd.DataFrame({'close': range(504)}, index=dates)
        
        def optimize(data: pd.DataFrame) -> Dict[str, Any]:
            return {'param': 1.0}
        
        def failing_backtest(
            data: pd.DataFrame,
            params: Dict[str, Any]
        ) -> Tuple[pd.Series, Optional[pd.Series]]:
            raise ValueError("回测失败")
        
        with pytest.raises(ValueError, match="回测失败"):
            wfa.run_analysis(optimize, failing_backtest, data, freq=252)
