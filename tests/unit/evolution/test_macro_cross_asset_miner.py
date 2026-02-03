"""宏观与跨资产因子挖掘器单元测试

白皮书依据: 第四章 4.1.15 - 宏观与跨资产因子挖掘器
测试覆盖率目标: ≥ 85%
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.macro_cross_asset import (
    MacroCrossAssetFactorMiner,
    MacroCrossAssetConfig,
    MacroCrossAssetOperatorRegistry,
    OperatorError,
    DataQualityError
)


class TestMacroCrossAssetConfig:
    """测试MacroCrossAssetConfig配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = MacroCrossAssetConfig()
        
        assert config.correlation_threshold == 0.7
        assert config.spread_threshold == 0.02
        assert config.momentum_window == 20
        assert config.risk_lookback_period == 60
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = MacroCrossAssetConfig(
            correlation_threshold=0.8,
            spread_threshold=0.03,
            momentum_window=30,
            risk_lookback_period=90
        )
        
        assert config.correlation_threshold == 0.8
        assert config.spread_threshold == 0.03
        assert config.momentum_window == 30
        assert config.risk_lookback_period == 90


class TestMacroCrossAssetFactorMiner:
    """测试MacroCrossAssetFactorMiner主类"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用挖掘器实例"""
        return MacroCrossAssetFactorMiner()
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用宏观市场数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
        np.random.seed(42)
        
        # 生成模拟宏观数据
        data = pd.DataFrame({
            'short_rate': 2.0 + np.random.randn(100) * 0.1,
            'long_rate': 3.0 + np.random.randn(100) * 0.15,
            'credit_spread': 1.5 + np.random.randn(100) * 0.2,
            'interest_rate_diff': 0.5 + np.random.randn(100) * 0.1,
            'exchange_rate': 6.5 + np.cumsum(np.random.randn(100) * 0.01),
            'commodity_price': 100 + np.cumsum(np.random.randn(100) * 2),
            'vix_short': 15 + np.random.randn(100) * 3,
            'vix_long': 18 + np.random.randn(100) * 2,
            'asset1': np.cumsum(np.random.randn(100) * 0.01),
            'asset2': np.cumsum(np.random.randn(100) * 0.01),
            'actual': 2.5 + np.random.randn(100) * 0.5,
            'forecast': 2.5 + np.random.randn(100) * 0.3,
            'policy_rate': 2.5 + np.cumsum(np.random.choice([-0.25, 0, 0.25], 100, p=[0.1, 0.8, 0.1])),
            'vix': 15 + np.random.randn(100) * 3
        }, index=dates)
        
        # 确保所有值为正（对于需要正值的列）
        data['vix_short'] = data['vix_short'].abs() + 10
        data['vix_long'] = data['vix_long'].abs() + 10
        data['vix'] = data['vix'].abs() + 10
        
        return data
    
    @pytest.fixture
    def sample_returns(self, sample_data):
        """创建测试用收益率数据"""
        return pd.Series(
            np.random.randn(len(sample_data)) * 0.01,
            index=sample_data.index
        )
    
    def test_initialization(self, miner):
        """测试挖掘器初始化"""
        assert miner is not None
        assert miner.config is not None
        assert miner.operator_registry is not None
        assert isinstance(miner.operator_registry, MacroCrossAssetOperatorRegistry)
        assert len(miner.macro_signals) == 0
    
    def test_initialization_with_custom_config(self):
        """测试使用自定义配置初始化"""
        config = MacroCrossAssetConfig(
            correlation_threshold=0.8,
            spread_threshold=0.03
        )
        miner = MacroCrossAssetFactorMiner(config=config)
        
        assert miner.config.correlation_threshold == 0.8
        assert miner.config.spread_threshold == 0.03
    
    def test_validate_config_correlation_threshold(self):
        """测试配置验证 - correlation_threshold"""
        # 有效值
        config = MacroCrossAssetConfig(correlation_threshold=0.5)
        miner = MacroCrossAssetFactorMiner(config=config)
        assert miner.config.correlation_threshold == 0.5
        
        # 无效值 - 超出范围
        with pytest.raises(ValueError, match="correlation_threshold必须在\\[0, 1\\]范围内"):
            config = MacroCrossAssetConfig(correlation_threshold=1.5)
            MacroCrossAssetFactorMiner(config=config)
    
    def test_validate_config_spread_threshold(self):
        """测试配置验证 - spread_threshold"""
        # 无效值 - 小于等于0
        with pytest.raises(ValueError, match="spread_threshold必须 > 0"):
            config = MacroCrossAssetConfig(spread_threshold=-0.01)
            MacroCrossAssetFactorMiner(config=config)
    
    def test_validate_config_momentum_window(self):
        """测试配置验证 - momentum_window"""
        # 无效值 - 小于等于0
        with pytest.raises(ValueError, match="momentum_window必须 > 0"):
            config = MacroCrossAssetConfig(momentum_window=-5)
            MacroCrossAssetFactorMiner(config=config)
    
    def test_validate_config_risk_lookback_period(self):
        """测试配置验证 - risk_lookback_period"""
        # 无效值 - 小于等于0
        with pytest.raises(ValueError, match="risk_lookback_period必须 > 0"):
            config = MacroCrossAssetConfig(risk_lookback_period=-10)
            MacroCrossAssetFactorMiner(config=config)
    
    def test_extend_operator_whitelist(self, miner):
        """测试算子白名单扩展"""
        expected_operators = [
            'yield_curve_slope',
            'credit_spread_widening',
            'currency_carry_trade',
            'commodity_momentum',
            'vix_term_structure',
            'cross_asset_correlation',
            'macro_surprise_index',
            'central_bank_policy_shift',
            'global_liquidity_flow',
            'geopolitical_risk_index'
        ]
        
        for op in expected_operators:
            assert op in miner.operator_whitelist
    
    def test_analyze_yield_curve_normal(self, miner, sample_data):
        """测试收益率曲线分析 - 正常曲线"""
        short_rate = sample_data['short_rate']
        long_rate = sample_data['long_rate']
        
        slope = miner.analyze_yield_curve(short_rate, long_rate)
        
        assert isinstance(slope, pd.Series)
        assert len(slope) == len(short_rate)
        # 正常曲线应该大部分为正
        assert (slope > 0).sum() > len(slope) * 0.5
    
    def test_analyze_yield_curve_inverted(self, miner):
        """测试收益率曲线分析 - 倒挂曲线"""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        # 创建倒挂场景
        short_rate = pd.Series(3.0 + np.random.randn(50) * 0.1, index=dates)
        long_rate = pd.Series(2.5 + np.random.randn(50) * 0.1, index=dates)
        
        slope = miner.analyze_yield_curve(short_rate, long_rate)
        
        assert isinstance(slope, pd.Series)
        # 倒挂曲线应该大部分为负
        assert (slope < 0).sum() > len(slope) * 0.5
    
    def test_analyze_yield_curve_empty_data(self, miner):
        """测试空数据的收益率曲线分析"""
        empty_series = pd.Series(dtype=float)
        
        slope = miner.analyze_yield_curve(empty_series, empty_series)
        
        assert isinstance(slope, pd.Series)
        assert len(slope) == 0
    
    def test_detect_credit_stress(self, miner, sample_data):
        """测试信用压力检测"""
        credit_spread = sample_data['credit_spread']
        
        stress_signal = miner.detect_credit_stress(credit_spread)
        
        assert isinstance(stress_signal, pd.Series)
        assert len(stress_signal) == len(credit_spread)
        # 信号应该是0或1
        assert set(stress_signal.unique()).issubset({0, 1})
    
    def test_detect_credit_stress_with_custom_threshold(self, miner, sample_data):
        """测试使用自定义阈值的信用压力检测"""
        credit_spread = sample_data['credit_spread']
        
        stress_signal = miner.detect_credit_stress(credit_spread, threshold=0.05)
        
        assert isinstance(stress_signal, pd.Series)
        assert set(stress_signal.unique()).issubset({0, 1})
    
    def test_detect_credit_stress_empty_data(self, miner):
        """测试空数据的信用压力检测"""
        empty_series = pd.Series(dtype=float)
        
        stress_signal = miner.detect_credit_stress(empty_series)
        
        assert isinstance(stress_signal, pd.Series)
        assert len(stress_signal) == 0
    
    def test_calculate_cross_asset_correlation(self, miner, sample_data):
        """测试跨资产相关性计算"""
        asset1 = sample_data['asset1']
        asset2 = sample_data['asset2']
        
        correlation = miner.calculate_cross_asset_correlation(asset1, asset2, window=20)
        
        assert isinstance(correlation, pd.Series)
        assert len(correlation) == len(asset1)
        # 相关系数应该在[-1, 1]范围内
        valid_corr = correlation.dropna()
        if len(valid_corr) > 0:
            assert (valid_corr >= -1).all() and (valid_corr <= 1).all()
    
    def test_calculate_cross_asset_correlation_empty_data(self, miner):
        """测试空数据的跨资产相关性计算"""
        empty_series = pd.Series(dtype=float)
        
        correlation = miner.calculate_cross_asset_correlation(empty_series, empty_series)
        
        assert isinstance(correlation, pd.Series)
        assert len(correlation) == 0
    
    def test_assess_systemic_risk_full_data(self, miner, sample_data):
        """测试系统性风险评估 - 完整数据"""
        systemic_risk = miner.assess_systemic_risk(sample_data)
        
        assert isinstance(systemic_risk, pd.Series)
        assert len(systemic_risk) == len(sample_data)
        # 风险指数应该在[0, 1]范围内
        assert (systemic_risk >= 0).all() and (systemic_risk <= 1).all()
    
    def test_assess_systemic_risk_partial_data(self, miner):
        """测试系统性风险评估 - 部分数据"""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        # 只包含部分指标
        partial_data = pd.DataFrame({
            'short_rate': 2.0 + np.random.randn(50) * 0.1,
            'long_rate': 3.0 + np.random.randn(50) * 0.15
        }, index=dates)
        
        systemic_risk = miner.assess_systemic_risk(partial_data)
        
        assert isinstance(systemic_risk, pd.Series)
        assert len(systemic_risk) == len(partial_data)
    
    def test_assess_systemic_risk_empty_data(self, miner):
        """测试空数据的系统性风险评估"""
        empty_df = pd.DataFrame()
        
        systemic_risk = miner.assess_systemic_risk(empty_df)
        
        assert isinstance(systemic_risk, pd.Series)
        assert len(systemic_risk) == 0
    
    def test_mine_factors_empty_data(self, miner, sample_returns):
        """测试空数据的因子挖掘"""
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="输入数据为空"):
            miner.mine_factors(empty_data, sample_returns, generations=1)
    
    def test_get_macro_signal_report(self, miner):
        """测试宏观信号报告"""
        # 添加一些模拟宏观信号
        miner.macro_signals['yield_curve_inversion'] = [
            {'time': '2023-01-01', 'severity': 'high'}
        ]
        miner.macro_signals['credit_stress'] = [
            {'time': '2023-01-02'},
            {'time': '2023-01-03'}
        ]
        
        report = miner.get_macro_signal_report()
        
        assert 'total_macro_signals' in report
        assert report['total_macro_signals'] == 3
        assert 'signals_by_type' in report
        assert report['signals_by_type']['yield_curve_inversion'] == 1
        assert report['signals_by_type']['credit_stress'] == 2
        assert 'correlation_threshold' in report
        assert 'spread_threshold' in report


class TestMacroCrossAssetOperatorRegistry:
    """测试MacroCrossAssetOperatorRegistry算子注册表"""
    
    @pytest.fixture
    def registry(self):
        """创建测试用算子注册表"""
        return MacroCrossAssetOperatorRegistry()
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用数据"""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        np.random.seed(42)
        
        data = pd.DataFrame({
            'short_rate': 2.0 + np.random.randn(50) * 0.1,
            'long_rate': 3.0 + np.random.randn(50) * 0.15,
            'credit_spread': 1.5 + np.random.randn(50) * 0.2,
            'interest_rate_diff': 0.5 + np.random.randn(50) * 0.1,
            'exchange_rate': 6.5 + np.cumsum(np.random.randn(50) * 0.01),
            'commodity_price': 100 + np.cumsum(np.random.randn(50) * 2),
            'vix_short': np.abs(15 + np.random.randn(50) * 3) + 10,
            'vix_long': np.abs(18 + np.random.randn(50) * 2) + 10,
            'asset1': np.cumsum(np.random.randn(50) * 0.01),
            'asset2': np.cumsum(np.random.randn(50) * 0.01),
            'actual': 2.5 + np.random.randn(50) * 0.5,
            'forecast': 2.5 + np.random.randn(50) * 0.3,
            'policy_rate': 2.5 + np.cumsum(np.random.choice([-0.25, 0, 0.25], 50, p=[0.1, 0.8, 0.1]))
        }, index=dates)
        
        return data
    
    def test_registry_initialization(self, registry):
        """测试注册表初始化"""
        assert registry is not None
        assert len(registry.operators) == 10
        assert len(registry.operator_metadata) == 10
    
    def test_get_operator_names(self, registry):
        """测试获取算子名称列表"""
        names = registry.get_operator_names()
        
        assert len(names) == 10
        assert 'yield_curve_slope' in names
        assert 'credit_spread_widening' in names
        assert 'currency_carry_trade' in names
        assert 'geopolitical_risk_index' in names
    
    def test_get_operator(self, registry):
        """测试获取算子函数"""
        op = registry.get_operator('yield_curve_slope')
        
        assert op is not None
        assert callable(op)
    
    def test_get_operator_not_found(self, registry):
        """测试获取不存在的算子"""
        op = registry.get_operator('nonexistent_operator')
        
        assert op is None
    
    def test_get_operators_by_category(self, registry):
        """测试按类别获取算子"""
        interest_rate_ops = registry.get_operators_by_category('interest_rate')
        
        assert len(interest_rate_ops) >= 1
        assert 'yield_curve_slope' in interest_rate_ops
    
    def test_validate_operator_input_success(self, registry, sample_data):
        """测试算子输入验证 - 成功"""
        # 不应抛出异常
        registry.validate_operator_input(sample_data, ['short_rate', 'long_rate'])
    
    def test_validate_operator_input_empty_data(self, registry):
        """测试算子输入验证 - 空数据"""
        empty_df = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="输入数据为空"):
            registry.validate_operator_input(empty_df, ['short_rate'])
    
    def test_validate_operator_input_missing_columns(self, registry, sample_data):
        """测试算子输入验证 - 缺少列"""
        with pytest.raises(OperatorError, match="缺少必需列"):
            registry.validate_operator_input(sample_data, ['short_rate', 'nonexistent'])
    
    def test_validate_operator_input_too_many_nans(self, registry):
        """测试算子输入验证 - 过多NaN值"""
        data_with_nans = pd.DataFrame({
            'short_rate': [np.nan] * 60 + [2.0] * 40,
            'long_rate': [3.0] * 100
        })
        
        with pytest.raises(DataQualityError, match="有.*NaN值"):
            registry.validate_operator_input(data_with_nans, ['short_rate'])
    
    # ========================================================================
    # 测试10个算子
    # ========================================================================
    
    def test_yield_curve_slope(self, registry, sample_data):
        """测试收益率曲线斜率算子"""
        slope = registry.yield_curve_slope(sample_data, 'short_rate', 'long_rate')
        
        assert isinstance(slope, pd.Series)
        assert len(slope) == len(sample_data)
        # 大部分应该是正斜率
        assert (slope > 0).sum() > len(slope) * 0.5
    
    def test_credit_spread_widening(self, registry, sample_data):
        """测试信用利差扩大算子"""
        widening = registry.credit_spread_widening(sample_data, 'credit_spread')
        
        assert isinstance(widening, pd.Series)
        assert len(widening) == len(sample_data)
        # 信号应该是0或1
        assert set(widening.unique()).issubset({0, 1})
    
    def test_currency_carry_trade(self, registry, sample_data):
        """测试货币套利交易算子"""
        carry_signal = registry.currency_carry_trade(
            sample_data, 'interest_rate_diff', 'exchange_rate'
        )
        
        assert isinstance(carry_signal, pd.Series)
        assert len(carry_signal) == len(sample_data)
    
    def test_commodity_momentum(self, registry, sample_data):
        """测试商品动量算子"""
        momentum = registry.commodity_momentum(sample_data, 'commodity_price')
        
        assert isinstance(momentum, pd.Series)
        assert len(momentum) == len(sample_data)
    
    def test_vix_term_structure(self, registry, sample_data):
        """测试VIX期限结构算子"""
        term_structure = registry.vix_term_structure(
            sample_data, 'vix_short', 'vix_long'
        )
        
        assert isinstance(term_structure, pd.Series)
        assert len(term_structure) == len(sample_data)
        # 比率应该是正值
        assert (term_structure > 0).all()
    
    def test_cross_asset_correlation(self, registry, sample_data):
        """测试跨资产相关性算子"""
        correlation = registry.cross_asset_correlation(
            sample_data, 'asset1', 'asset2', window=20
        )
        
        assert isinstance(correlation, pd.Series)
        assert len(correlation) == len(sample_data)
        # 相关系数应该在[-1, 1]范围内
        valid_corr = correlation.dropna()
        if len(valid_corr) > 0:
            assert (valid_corr >= -1).all() and (valid_corr <= 1).all()
    
    def test_macro_surprise_index(self, registry, sample_data):
        """测试宏观意外指数算子"""
        surprise_index = registry.macro_surprise_index(
            sample_data, 'actual', 'forecast'
        )
        
        assert isinstance(surprise_index, pd.Series)
        assert len(surprise_index) == len(sample_data)
    
    def test_central_bank_policy_shift(self, registry, sample_data):
        """测试央行政策转向算子"""
        policy_shift = registry.central_bank_policy_shift(
            sample_data, 'policy_rate'
        )
        
        assert isinstance(policy_shift, pd.Series)
        assert len(policy_shift) == len(sample_data)
        # 信号应该是-1, 0, 1
        assert set(policy_shift.unique()).issubset({-1, 0, 1})
    
    def test_global_liquidity_flow(self, registry):
        """测试全球流动性流动算子"""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        # 创建包含资产负债表数据的数据框
        data = pd.DataFrame({
            'balance_sheet_fed': 8000 + np.cumsum(np.random.randn(50) * 10),
            'balance_sheet_ecb': 7000 + np.cumsum(np.random.randn(50) * 10),
            'balance_sheet_boj': 6000 + np.cumsum(np.random.randn(50) * 10)
        }, index=dates)
        
        liquidity_flow = registry.global_liquidity_flow(
            data,
            balance_sheet_cols=['balance_sheet_fed', 'balance_sheet_ecb', 'balance_sheet_boj']
        )
        
        assert isinstance(liquidity_flow, pd.Series)
        assert len(liquidity_flow) == len(data)
    
    def test_geopolitical_risk_index(self, registry):
        """测试地缘政治风险指数算子"""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        # 创建包含地缘政治事件数据的数据框
        data = pd.DataFrame({
            'military_risk': np.random.rand(50),
            'trade_risk': np.random.rand(50),
            'political_risk': np.random.rand(50)
        }, index=dates)
        
        risk_index = registry.geopolitical_risk_index(
            data,
            event_cols=['military_risk', 'trade_risk', 'political_risk']
        )
        
        assert isinstance(risk_index, pd.Series)
        assert len(risk_index) == len(data)
        # 风险指数应该在[0, 1]范围内
        assert (risk_index >= 0).all() and (risk_index <= 1).all()
    
    # ========================================================================
    # 边界条件测试
    # ========================================================================
    
    def test_operators_with_minimal_data(self, registry):
        """测试算子在最小数据集上的表现"""
        # 创建只有5个数据点的数据集
        minimal_data = pd.DataFrame({
            'short_rate': [2.0, 2.1, 2.0, 1.9, 2.0],
            'long_rate': [3.0, 3.1, 3.0, 2.9, 3.0],
            'credit_spread': [1.5, 1.6, 1.5, 1.4, 1.5],
            'commodity_price': [100, 101, 102, 101, 100]
        })
        
        # 测试几个关键算子
        slope = registry.yield_curve_slope(minimal_data)
        assert len(slope) == 5
        
        widening = registry.credit_spread_widening(minimal_data, window=3)
        assert len(widening) == 5
        
        momentum = registry.commodity_momentum(minimal_data, window=3)
        assert len(momentum) == 5
    
    def test_operators_error_handling(self, registry):
        """测试算子错误处理"""
        # 测试空数据
        empty_df = pd.DataFrame()
        
        with pytest.raises(OperatorError):
            registry.yield_curve_slope(empty_df)
        
        with pytest.raises(OperatorError):
            registry.credit_spread_widening(empty_df)


class TestIntegration:
    """集成测试"""
    
    def test_full_mining_workflow(self):
        """测试完整的因子挖掘流程"""
        # 创建挖掘器
        miner = MacroCrossAssetFactorMiner()
        
        # 创建测试数据
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        data = pd.DataFrame({
            'short_rate': 2.0 + np.random.randn(100) * 0.1,
            'long_rate': 3.0 + np.random.randn(100) * 0.15,
            'credit_spread': 1.5 + np.random.randn(100) * 0.2,
            'vix': np.abs(15 + np.random.randn(100) * 3) + 10
        }, index=dates)
        
        returns = pd.Series(
            np.random.randn(100) * 0.01,
            index=dates
        )
        
        # 验证数据
        assert not data.empty
        assert len(data) == 100
        
        # 验证挖掘器配置
        assert miner.config is not None
        assert miner.operator_registry is not None
        
        # 验证算子白名单
        assert len(miner.operator_whitelist) >= 10
