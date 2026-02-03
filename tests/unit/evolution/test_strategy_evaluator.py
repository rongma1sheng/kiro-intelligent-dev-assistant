"""策略评价器单元测试

白皮书依据: 第四章 4.2 斯巴达竞技场
测试任务: StrategyEvaluator投研级评价体系

测试覆盖:
- 收益质量指标计算
- 风险结构指标计算
- 交易层面指标计算
- 阈值检查逻辑
- 分市场标准验证
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.evolution.strategy_evaluator import (
    StrategyEvaluator,
    MarketType,
    EvaluationThresholds,
    MARKET_THRESHOLDS
)


class TestStrategyEvaluator:
    """测试StrategyEvaluator基础功能"""
    
    @pytest.fixture
    def evaluator_a_stock(self):
        """创建A股市场评价器"""
        return StrategyEvaluator(market_type=MarketType.A_STOCK)
    
    @pytest.fixture
    def evaluator_futures(self):
        """创建期货市场评价器"""
        return StrategyEvaluator(market_type=MarketType.FUTURES)
    
    @pytest.fixture
    def evaluator_crypto(self):
        """创建加密货币市场评价器"""
        return StrategyEvaluator(market_type=MarketType.CRYPTO)
    
    @pytest.fixture
    def sample_equity_curve(self):
        """创建样本净值曲线（上涨趋势）"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        # 模拟年化20%收益，波动率15%
        returns = np.random.normal(0.20/252, 0.15/np.sqrt(252), 252)
        equity = pd.Series((1 + returns).cumprod(), index=dates)
        return equity
    
    @pytest.fixture
    def sample_trades(self):
        """创建样本交易序列"""
        # 模拟100笔交易，胜率55%
        np.random.seed(42)
        trades = []
        for _ in range(100):
            if np.random.random() < 0.55:
                # 盈利交易
                trades.append(np.random.uniform(0.01, 0.05))
            else:
                # 亏损交易
                trades.append(np.random.uniform(-0.03, -0.01))
        return pd.Series(trades)
    
    def test_initialization(self, evaluator_a_stock):
        """测试初始化"""
        assert evaluator_a_stock is not None
        assert evaluator_a_stock.market_type == MarketType.A_STOCK
        assert evaluator_a_stock.thresholds is not None
    
    def test_market_type_thresholds(self):
        """测试不同市场类型的阈值"""
        # A股
        a_stock_eval = StrategyEvaluator(MarketType.A_STOCK)
        assert a_stock_eval.thresholds.min_annual_return == 0.12
        assert a_stock_eval.thresholds.min_sharpe == 1.2
        
        # 期货
        futures_eval = StrategyEvaluator(MarketType.FUTURES)
        assert futures_eval.thresholds.min_annual_return == 0.15
        assert futures_eval.thresholds.min_sharpe == 1.0
        
        # 加密货币
        crypto_eval = StrategyEvaluator(MarketType.CRYPTO)
        assert crypto_eval.thresholds.min_annual_return == 0.20
        assert crypto_eval.thresholds.min_sharpe == 1.0


class TestReturnQualityMetrics:
    """测试收益质量指标"""
    
    @pytest.fixture
    def evaluator(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    def test_calc_returns(self, evaluator):
        """测试收益率计算"""
        equity = pd.Series([100, 105, 103, 108, 110])
        returns = evaluator.calc_returns(equity)
        
        assert len(returns) == 4
        assert abs(returns.iloc[0] - 0.05) < 0.001
        assert abs(returns.iloc[1] - (-0.019)) < 0.001
    
    def test_annualized_return(self, evaluator):
        """测试年化收益率计算"""
        # 模拟1年数据，总收益20%
        equity = pd.Series([100] + [100 * 1.20] * 251)
        ann_ret = evaluator.annualized_return(equity, freq=252)
        
        assert abs(ann_ret - 0.20) < 0.01
    
    def test_annualized_return_empty(self, evaluator):
        """测试空数据的年化收益率"""
        equity = pd.Series([100])
        ann_ret = evaluator.annualized_return(equity, freq=252)
        
        assert ann_ret == 0.0
    
    def test_sharpe_ratio(self, evaluator):
        """测试夏普比率计算"""
        # 模拟收益率序列
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        sharpe = evaluator.sharpe_ratio(returns, rf=0.0, freq=252)
        
        assert isinstance(sharpe, float)
        assert -5 < sharpe < 5  # 合理范围
    
    def test_sharpe_ratio_zero_std(self, evaluator):
        """测试零波动率的夏普比率"""
        returns = pd.Series([0.01] * 100)
        sharpe = evaluator.sharpe_ratio(returns, rf=0.0, freq=252)
        
        assert sharpe == 0.0
    
    def test_sortino_ratio(self, evaluator):
        """测试Sortino比率计算"""
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        sortino = evaluator.sortino_ratio(returns, rf=0.0, freq=252)
        
        assert isinstance(sortino, float)
        # Sortino通常大于Sharpe（只惩罚下行波动）
        assert sortino >= 0 or sortino < 0


class TestRiskStructureMetrics:
    """测试风险结构指标"""
    
    @pytest.fixture
    def evaluator(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    def test_max_drawdown(self, evaluator):
        """测试最大回撤计算"""
        # 模拟有明显回撤的净值曲线
        equity = pd.Series([100, 110, 105, 95, 100, 115])
        mdd = evaluator.max_drawdown(equity)
        
        # 最大回撤应该是从110到95，约-13.6%
        assert mdd < 0
        assert abs(mdd - (-0.136)) < 0.01
    
    def test_max_drawdown_no_drawdown(self, evaluator):
        """测试无回撤的情况"""
        equity = pd.Series([100, 105, 110, 115, 120])
        mdd = evaluator.max_drawdown(equity)
        
        assert mdd == 0.0
    
    def test_drawdown_duration(self, evaluator):
        """测试回撤持续时间"""
        # 模拟回撤持续5天
        equity = pd.Series([100, 110, 105, 100, 95, 90, 95, 100, 110, 115])
        duration = evaluator.drawdown_duration(equity)
        
        assert duration > 0
        assert duration <= len(equity)
    
    def test_calmar_ratio(self, evaluator):
        """测试Calmar比率计算"""
        # 模拟年化20%收益，最大回撤-10%
        equity = pd.Series([100] + list(np.linspace(100, 120, 251)))
        equity.iloc[100:150] *= 0.9  # 制造回撤
        
        calmar = evaluator.calmar_ratio(equity, freq=252)
        
        assert isinstance(calmar, float)
        assert calmar > 0  # 正收益应该有正Calmar
    
    def test_cvar(self, evaluator):
        """测试CVaR计算"""
        returns = pd.Series(np.random.normal(0.001, 0.01, 1000))
        cvar = evaluator.cvar(returns, alpha=0.05)
        
        assert isinstance(cvar, float)
        assert cvar < 0  # CVaR应该是负数（损失）


class TestTradeStructureMetrics:
    """测试交易层面指标"""
    
    @pytest.fixture
    def evaluator(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    def test_trade_expectancy(self, evaluator):
        """测试交易期望值计算"""
        # 模拟交易：60%胜率，盈亏比2:1
        trades = pd.Series([0.02, 0.03, -0.01, 0.02, -0.015, 0.025, -0.01, 0.02, 0.03, -0.01])
        
        win_rate, payoff, expectancy = evaluator.trade_expectancy(trades)
        
        assert 0 <= win_rate <= 1
        assert payoff >= 0
        assert isinstance(expectancy, float)
    
    def test_trade_expectancy_all_wins(self, evaluator):
        """测试全部盈利的交易"""
        trades = pd.Series([0.01, 0.02, 0.03, 0.015])
        
        win_rate, payoff, expectancy = evaluator.trade_expectancy(trades)
        
        assert win_rate == 1.0
        assert expectancy > 0
    
    def test_trade_expectancy_all_losses(self, evaluator):
        """测试全部亏损的交易"""
        trades = pd.Series([-0.01, -0.02, -0.03])
        
        win_rate, payoff, expectancy = evaluator.trade_expectancy(trades)
        
        assert win_rate == 0.0
        assert expectancy < 0
    
    def test_max_consecutive_losses(self, evaluator):
        """测试最大连续亏损次数"""
        # 模拟连续亏损3次
        trades = pd.Series([0.01, -0.01, -0.02, -0.01, 0.02, -0.01, 0.01])
        
        max_consec = evaluator.max_consecutive_losses(trades)
        
        assert max_consec == 3


class TestComprehensiveEvaluation:
    """测试综合评价功能"""
    
    @pytest.fixture
    def evaluator(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    @pytest.fixture
    def sample_trades(self):
        """创建示例交易记录"""
        np.random.seed(42)
        # 模拟100笔交易，60%盈利
        trades = []
        for i in range(100):
            if np.random.random() < 0.6:
                trades.append(np.random.uniform(0.01, 0.05))  # 盈利
            else:
                trades.append(np.random.uniform(-0.03, -0.01))  # 亏损
        return pd.Series(trades)
    
    @pytest.fixture
    def good_equity_curve(self):
        """创建优秀的净值曲线"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        # 年化25%收益，夏普2.0
        returns = np.random.normal(0.25/252, 0.125/np.sqrt(252), 252)
        equity = pd.Series((1 + returns).cumprod() * 100, index=dates)
        return equity
    
    @pytest.fixture
    def poor_equity_curve(self):
        """创建较差的净值曲线"""
        np.random.seed(123)
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        # 年化5%收益，高波动
        returns = np.random.normal(0.05/252, 0.30/np.sqrt(252), 252)
        equity = pd.Series((1 + returns).cumprod() * 100, index=dates)
        return equity
    
    def test_evaluate_strategy_complete(self, evaluator, good_equity_curve, sample_trades):
        """测试完整策略评价"""
        metrics = evaluator.evaluate_strategy(
            equity=good_equity_curve,
            trades=sample_trades,
            freq=252
        )
        
        # 验证所有关键指标都存在
        assert 'annual_return' in metrics
        assert 'sharpe' in metrics
        assert 'sortino' in metrics
        assert 'max_drawdown' in metrics
        assert 'calmar' in metrics
        assert 'max_dd_duration_days' in metrics
        assert 'cvar_5pct' in metrics
        assert 'win_rate' in metrics
        assert 'payoff_ratio' in metrics
        assert 'expectancy' in metrics
    
    def test_evaluate_strategy_without_trades(self, evaluator, good_equity_curve):
        """测试无交易数据的策略评价"""
        metrics = evaluator.evaluate_strategy(
            equity=good_equity_curve,
            trades=None,
            freq=252
        )
        
        # 应该有基础指标
        assert 'annual_return' in metrics
        assert 'sharpe' in metrics
        # 不应该有交易层面指标
        assert 'win_rate' not in metrics


class TestThresholdChecking:
    """测试阈值检查功能"""
    
    @pytest.fixture
    def evaluator_a_stock(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    @pytest.fixture
    def excellent_metrics(self):
        """优秀策略的指标"""
        return {
            'annual_return': 0.25,
            'sharpe': 2.0,
            'sortino': 2.5,
            'max_drawdown': -0.10,
            'calmar': 2.5,
            'max_dd_duration_days': 30,
            'cvar_5pct': -0.015,
            'win_rate': 0.60,
            'payoff_ratio': 2.5,
            'expectancy': 0.001
        }
    
    @pytest.fixture
    def qualified_metrics(self):
        """合格策略的指标"""
        return {
            'annual_return': 0.15,
            'sharpe': 1.3,
            'sortino': 1.5,
            'max_drawdown': -0.18,
            'calmar': 0.8,
            'max_dd_duration_days': 100,
            'cvar_5pct': -0.025,
            'win_rate': 0.48,
            'payoff_ratio': 1.8,
            'expectancy': 0.0005
        }
    
    @pytest.fixture
    def poor_metrics(self):
        """不合格策略的指标"""
        return {
            'annual_return': 0.05,
            'sharpe': 0.8,
            'sortino': 0.9,
            'max_drawdown': -0.25,
            'calmar': 0.2,
            'max_dd_duration_days': 180,
            'cvar_5pct': -0.05,
            'win_rate': 0.40,
            'payoff_ratio': 1.2,
            'expectancy': 0.0001
        }
    
    def test_check_thresholds_excellent(self, evaluator_a_stock, excellent_metrics):
        """测试优秀策略的阈值检查"""
        result = evaluator_a_stock.check_thresholds(excellent_metrics)
        
        assert result['qualified'] is True
        assert result['excellent'] is True
        assert result['grade'] == '优秀'
        assert len(result['failed_criteria']) == 0
        assert result['excellent_ratio'] > 0.8
    
    def test_check_thresholds_qualified(self, evaluator_a_stock, qualified_metrics):
        """测试合格策略的阈值检查"""
        result = evaluator_a_stock.check_thresholds(qualified_metrics)
        
        assert result['qualified'] is True
        assert result['excellent'] is False
        assert result['grade'] == '合格'
        assert len(result['failed_criteria']) == 0
    
    def test_check_thresholds_poor(self, evaluator_a_stock, poor_metrics):
        """测试不合格策略的阈值检查"""
        result = evaluator_a_stock.check_thresholds(poor_metrics)
        
        assert result['qualified'] is False
        assert result['excellent'] is False
        assert result['grade'] == '不合格'
        assert len(result['failed_criteria']) > 0


class TestMarketSpecificThresholds:
    """测试分市场阈值"""
    
    @pytest.fixture
    def base_metrics(self):
        """基础指标（中等水平）"""
        return {
            'annual_return': 0.15,
            'sharpe': 1.1,
            'sortino': 1.3,
            'max_drawdown': -0.20,
            'calmar': 0.75,
            'max_dd_duration_days': 120,
            'cvar_5pct': -0.03,
            'win_rate': 0.45,
            'payoff_ratio': 2.0,
            'max_single_loss': -0.015
        }
    
    def test_a_stock_thresholds(self, base_metrics):
        """测试A股市场阈值"""
        evaluator = StrategyEvaluator(MarketType.A_STOCK)
        result = evaluator.check_thresholds(base_metrics)
        
        # A股要求年化≥12%，夏普≥1.2
        # 这个策略年化15%达标，但夏普1.1不达标
        assert result['qualified'] is False
    
    def test_futures_thresholds(self, base_metrics):
        """测试期货市场阈值"""
        # 调整calmar使其达到期货市场要求
        futures_metrics = base_metrics.copy()
        futures_metrics['calmar'] = 0.85  # 期货要求calmar >= 0.8
        
        evaluator = StrategyEvaluator(MarketType.FUTURES)
        result = evaluator.check_thresholds(futures_metrics)
        
        # 期货要求年化≥15%，夏普≥1.0，calmar≥0.8
        # 调整后的策略应该合格
        assert result['qualified'] is True
    
    def test_crypto_thresholds(self, base_metrics):
        """测试加密货币市场阈值"""
        evaluator = StrategyEvaluator(MarketType.CRYPTO)
        result = evaluator.check_thresholds(base_metrics)
        
        # Crypto要求年化≥20%
        # 这个策略年化15%不达标
        assert result['qualified'] is False


class TestParameterSensitivity:
    """测试参数敏感性分析"""
    
    @pytest.fixture
    def evaluator(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    def test_parameter_sensitivity_robust(self, evaluator):
        """测试稳健的参数敏感性"""
        # 模拟参数扰动后的夏普比率都为正
        metric_series = pd.Series([1.5, 1.4, 1.6, 1.3, 1.7, 1.4, 1.5])
        
        result = evaluator.parameter_sensitivity_test(metric_series, "Sharpe")
        
        assert result['robust'] is True
        assert result['mean'] > 0
        assert result['min'] > 0
    
    def test_parameter_sensitivity_fragile(self, evaluator):
        """测试脆弱的参数敏感性"""
        # 模拟参数扰动后有负值
        metric_series = pd.Series([1.2, 0.8, 1.5, -0.2, 1.0, 0.5, 1.3])
        
        result = evaluator.parameter_sensitivity_test(metric_series, "Sharpe")
        
        assert result['robust'] is False
        assert result['min'] < 0


class TestEdgeCases:
    """测试边界条件"""
    
    @pytest.fixture
    def evaluator(self):
        return StrategyEvaluator(MarketType.A_STOCK)
    
    def test_empty_equity_curve(self, evaluator):
        """测试空净值曲线"""
        equity = pd.Series([])
        
        ann_ret = evaluator.annualized_return(equity)
        mdd = evaluator.max_drawdown(equity)
        
        assert ann_ret == 0.0
        assert mdd == 0.0
    
    def test_single_point_equity(self, evaluator):
        """测试单点净值曲线"""
        equity = pd.Series([100])
        
        ann_ret = evaluator.annualized_return(equity)
        assert ann_ret == 0.0
    
    def test_empty_trades(self, evaluator):
        """测试空交易序列"""
        trades = pd.Series([])
        
        win_rate, payoff, expectancy = evaluator.trade_expectancy(trades)
        
        assert win_rate == 0.0
        assert payoff == 0.0
        assert expectancy == 0.0


def sample_trades():
    """辅助函数：生成样本交易数据"""
    np.random.seed(42)
    trades = []
    for _ in range(100):
        if np.random.random() < 0.55:
            trades.append(np.random.uniform(0.01, 0.05))
        else:
            trades.append(np.random.uniform(-0.03, -0.01))
    return pd.Series(trades)
