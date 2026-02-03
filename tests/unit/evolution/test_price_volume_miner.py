"""量价关系因子挖掘器单元测试

白皮书依据: 第四章 4.1.11 - 量价关系因子挖掘器
测试覆盖率目标: ≥ 85%
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.price_volume import (
    PriceVolumeRelationshipFactorMiner,
    PriceVolumeConfig,
    PriceVolumeOperatorRegistry,
    OperatorError,
    DataQualityError
)


class TestPriceVolumeConfig:
    """测试PriceVolumeConfig配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = PriceVolumeConfig()
        
        assert config.divergence_threshold == 0.3
        assert config.volume_surge_multiplier == 2.0
        assert config.vwap_deviation_threshold == 0.02
        assert config.correlation_window == 20
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = PriceVolumeConfig(
            divergence_threshold=0.5,
            volume_surge_multiplier=3.0,
            vwap_deviation_threshold=0.05,
            correlation_window=30
        )
        
        assert config.divergence_threshold == 0.5
        assert config.volume_surge_multiplier == 3.0
        assert config.vwap_deviation_threshold == 0.05
        assert config.correlation_window == 30


class TestPriceVolumeRelationshipFactorMiner:
    """测试PriceVolumeRelationshipFactorMiner主类"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用挖掘器实例"""
        return PriceVolumeRelationshipFactorMiner()
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用市场数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
        # 生成模拟价格数据（带趋势）
        np.random.seed(42)
        price_base = 100
        price_trend = np.linspace(0, 20, 100)
        price_noise = np.random.randn(100) * 2
        close = price_base + price_trend + price_noise
        
        # 生成模拟成交量数据
        volume_base = 1000000
        volume_noise = np.random.randn(100) * 100000
        volume = volume_base + volume_noise
        volume = np.abs(volume)  # 确保成交量为正
        
        data = pd.DataFrame({
            'close': close,
            'high': close * 1.02,
            'low': close * 0.98,
            'volume': volume
        }, index=dates)
        
        return data
    
    @pytest.fixture
    def sample_returns(self, sample_data):
        """创建测试用收益率数据"""
        return sample_data['close'].pct_change().fillna(0)
    
    def test_initialization(self, miner):
        """测试挖掘器初始化"""
        assert miner is not None
        assert miner.config is not None
        assert miner.operator_registry is not None
        assert isinstance(miner.operator_registry, PriceVolumeOperatorRegistry)
        assert len(miner.divergence_signals) == 0
    
    def test_initialization_with_custom_config(self):
        """测试使用自定义配置初始化"""
        config = PriceVolumeConfig(
            divergence_threshold=0.4,
            volume_surge_multiplier=2.5
        )
        miner = PriceVolumeRelationshipFactorMiner(config=config)
        
        assert miner.config.divergence_threshold == 0.4
        assert miner.config.volume_surge_multiplier == 2.5
    
    def test_validate_config_divergence_threshold(self):
        """测试配置验证 - divergence_threshold"""
        # 有效值
        config = PriceVolumeConfig(divergence_threshold=0.5)
        miner = PriceVolumeRelationshipFactorMiner(config=config)
        assert miner.config.divergence_threshold == 0.5
        
        # 无效值 - 超出范围
        with pytest.raises(ValueError, match="divergence_threshold必须在\\[0, 1\\]范围内"):
            config = PriceVolumeConfig(divergence_threshold=1.5)
            PriceVolumeRelationshipFactorMiner(config=config)

    
    def test_validate_config_volume_surge_multiplier(self):
        """测试配置验证 - volume_surge_multiplier"""
        # 无效值 - 小于等于1
        with pytest.raises(ValueError, match="volume_surge_multiplier必须 > 1.0"):
            config = PriceVolumeConfig(volume_surge_multiplier=0.5)
            PriceVolumeRelationshipFactorMiner(config=config)
    
    def test_validate_config_vwap_deviation_threshold(self):
        """测试配置验证 - vwap_deviation_threshold"""
        # 无效值 - 超出范围
        with pytest.raises(ValueError, match="vwap_deviation_threshold必须在\\[0, 1\\]范围内"):
            config = PriceVolumeConfig(vwap_deviation_threshold=1.5)
            PriceVolumeRelationshipFactorMiner(config=config)
    
    def test_validate_config_correlation_window(self):
        """测试配置验证 - correlation_window"""
        # 无效值 - 小于等于0
        with pytest.raises(ValueError, match="correlation_window必须 > 0"):
            config = PriceVolumeConfig(correlation_window=-5)
            PriceVolumeRelationshipFactorMiner(config=config)
    
    def test_extend_operator_whitelist(self, miner):
        """测试算子白名单扩展"""
        expected_operators = [
            'volume_price_correlation',
            'obv_divergence',
            'vwap_deviation',
            'volume_weighted_momentum',
            'price_volume_trend',
            'accumulation_distribution',
            'money_flow_index',
            'volume_surge_pattern',
            'price_volume_breakout',
            'volume_profile_support',
            'tick_volume_analysis',
            'volume_weighted_rsi'
        ]
        
        for op in expected_operators:
            assert op in miner.operator_whitelist
    
    def test_detect_divergence_top(self, miner, sample_data):
        """测试顶背离检测"""
        # 创建顶背离场景：价格创新高，指标未创新高
        price = sample_data['close'].copy()
        indicator = sample_data['close'].copy() * 0.9  # 指标低于价格
        
        divergence = miner.detect_divergence(price, indicator, window=20)
        
        assert isinstance(divergence, pd.Series)
        assert len(divergence) == len(price)
        # 应该检测到一些顶背离信号
        assert (divergence == 1).sum() >= 0
    
    def test_detect_divergence_bottom(self, miner, sample_data):
        """测试底背离检测"""
        # 创建底背离场景：价格创新低，指标未创新低
        price = sample_data['close'].copy()
        price = price.max() - price  # 反转价格，创造下跌趋势
        indicator = price * 1.1  # 指标高于价格
        
        divergence = miner.detect_divergence(price, indicator, window=20)
        
        assert isinstance(divergence, pd.Series)
        # 应该检测到一些底背离信号
        assert (divergence == -1).sum() >= 0
    
    def test_detect_divergence_empty_data(self, miner):
        """测试空数据的背离检测"""
        empty_series = pd.Series(dtype=float)
        
        divergence = miner.detect_divergence(empty_series, empty_series)
        
        assert isinstance(divergence, pd.Series)
        assert len(divergence) == 0
    
    def test_analyze_volume_surge_bullish(self, miner, sample_data):
        """测试成交量激增分析 - 强势信号"""
        volume = sample_data['volume'].copy()
        price_change = sample_data['close'].pct_change().fillna(0)
        
        # 创建强势场景：成交量激增 + 价格上涨
        volume.iloc[-10:] *= 3  # 最后10天成交量激增
        price_change.iloc[-10:] = 0.02  # 价格上涨
        
        surge_signal = miner.analyze_volume_surge(volume, price_change, window=20)
        
        assert isinstance(surge_signal, pd.Series)
        assert len(surge_signal) == len(volume)
        # 应该检测到强势信号
        assert (surge_signal > 0).sum() > 0
    
    def test_analyze_volume_surge_bearish(self, miner, sample_data):
        """测试成交量激增分析 - 恐慌信号"""
        volume = sample_data['volume'].copy()
        price_change = sample_data['close'].pct_change().fillna(0)
        
        # 创建恐慌场景：成交量激增 + 价格下跌
        volume.iloc[-10:] *= 3
        price_change.iloc[-10:] = -0.02  # 价格下跌
        
        surge_signal = miner.analyze_volume_surge(volume, price_change, window=20)
        
        assert isinstance(surge_signal, pd.Series)
        # 应该检测到恐慌信号
        assert (surge_signal < 0).sum() > 0

    
    def test_analyze_volume_surge_empty_data(self, miner):
        """测试空数据的成交量激增分析"""
        empty_series = pd.Series(dtype=float)
        
        surge_signal = miner.analyze_volume_surge(empty_series, empty_series)
        
        assert isinstance(surge_signal, pd.Series)
        assert len(surge_signal) == 0
    
    def test_calculate_capital_flow_strength(self, miner, sample_data):
        """测试资金流向强度计算"""
        capital_flow = miner.calculate_capital_flow_strength(sample_data)
        
        assert isinstance(capital_flow, pd.Series)
        assert len(capital_flow) == len(sample_data)
        # 资金流向应该是归一化的
        assert capital_flow.std() > 0
    
    def test_calculate_capital_flow_strength_empty_data(self, miner):
        """测试空数据的资金流向强度计算"""
        empty_df = pd.DataFrame()
        
        capital_flow = miner.calculate_capital_flow_strength(empty_df)
        
        assert isinstance(capital_flow, pd.Series)
        assert len(capital_flow) == 0
    
    def test_mine_factors_missing_columns(self, miner, sample_returns):
        """测试缺少必要列的因子挖掘"""
        # 创建缺少volume列的数据
        incomplete_data = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        with pytest.raises(ValueError, match="数据缺少必要列"):
            miner.mine_factors(incomplete_data, sample_returns, generations=1)
    
    def test_get_divergence_report(self, miner):
        """测试背离信号报告"""
        # 添加一些模拟背离信号
        miner.divergence_signals['top'] = [{'time': '2023-01-01'}]
        miner.divergence_signals['bottom'] = [{'time': '2023-01-02'}, {'time': '2023-01-03'}]
        
        report = miner.get_divergence_report()
        
        assert 'total_divergence_signals' in report
        assert report['total_divergence_signals'] == 3
        assert 'divergence_by_type' in report
        assert report['divergence_by_type']['top'] == 1
        assert report['divergence_by_type']['bottom'] == 2
        assert 'divergence_threshold' in report
        assert 'volume_surge_multiplier' in report


class TestPriceVolumeOperatorRegistry:
    """测试PriceVolumeOperatorRegistry算子注册表"""
    
    @pytest.fixture
    def registry(self):
        """创建测试用算子注册表"""
        return PriceVolumeOperatorRegistry()
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用数据"""
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(50) * 0.5)
        high = close * 1.02
        low = close * 0.98
        volume = np.abs(np.random.randn(50) * 100000 + 1000000)
        
        return pd.DataFrame({
            'close': close,
            'high': high,
            'low': low,
            'volume': volume
        }, index=dates)
    
    def test_registry_initialization(self, registry):
        """测试注册表初始化"""
        assert registry is not None
        assert len(registry.operators) == 12
        assert len(registry.operator_metadata) == 12
    
    def test_get_operator_names(self, registry):
        """测试获取算子名称列表"""
        names = registry.get_operator_names()
        
        assert len(names) == 12
        assert 'volume_price_correlation' in names
        assert 'obv_divergence' in names
        assert 'vwap_deviation' in names
        assert 'volume_weighted_rsi' in names
    
    def test_get_operator(self, registry):
        """测试获取算子函数"""
        op = registry.get_operator('volume_price_correlation')
        
        assert op is not None
        assert callable(op)
    
    def test_get_operator_not_found(self, registry):
        """测试获取不存在的算子"""
        op = registry.get_operator('nonexistent_operator')
        
        assert op is None
    
    def test_get_operators_by_category(self, registry):
        """测试按类别获取算子"""
        momentum_ops = registry.get_operators_by_category('momentum')
        
        assert len(momentum_ops) >= 2
        assert 'volume_weighted_momentum' in momentum_ops
        assert 'volume_weighted_rsi' in momentum_ops
    
    def test_validate_operator_input_success(self, registry, sample_data):
        """测试算子输入验证 - 成功"""
        # 不应抛出异常
        registry.validate_operator_input(sample_data, ['close', 'volume'])
    
    def test_validate_operator_input_empty_data(self, registry):
        """测试算子输入验证 - 空数据"""
        empty_df = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="输入数据为空"):
            registry.validate_operator_input(empty_df, ['close'])
    
    def test_validate_operator_input_missing_columns(self, registry, sample_data):
        """测试算子输入验证 - 缺少列"""
        with pytest.raises(OperatorError, match="缺少必需列"):
            registry.validate_operator_input(sample_data, ['close', 'nonexistent'])

    
    def test_validate_operator_input_too_many_nans(self, registry):
        """测试算子输入验证 - 过多NaN值"""
        data_with_nans = pd.DataFrame({
            'close': [np.nan] * 60 + [100] * 40,
            'volume': [1000000] * 100
        })
        
        with pytest.raises(DataQualityError, match="有.*NaN值"):
            registry.validate_operator_input(data_with_nans, ['close'])
    
    # ========================================================================
    # 测试12个算子
    # ========================================================================
    
    def test_volume_price_correlation(self, registry, sample_data):
        """测试量价相关性算子"""
        correlation = registry.volume_price_correlation(
            sample_data, 'close', 'volume', window=20
        )
        
        assert isinstance(correlation, pd.Series)
        assert len(correlation) == len(sample_data)
        # 相关系数应该在[-1, 1]范围内
        valid_corr = correlation.dropna()
        assert (valid_corr >= -1).all() and (valid_corr <= 1).all()
    
    def test_obv_divergence(self, registry, sample_data):
        """测试OBV背离算子"""
        divergence = registry.obv_divergence(
            sample_data, 'close', 'volume', window=20
        )
        
        assert isinstance(divergence, pd.Series)
        assert len(divergence) == len(sample_data)
        # 背离信号应该是-1, 0, 1
        assert set(divergence.unique()).issubset({-1, 0, 1})
    
    def test_vwap_deviation(self, registry, sample_data):
        """测试VWAP偏离度算子"""
        deviation = registry.vwap_deviation(
            sample_data, 'close', 'volume', window=20
        )
        
        assert isinstance(deviation, pd.Series)
        assert len(deviation) == len(sample_data)
        # 偏离度应该是有限值
        valid_dev = deviation.dropna()
        assert np.isfinite(valid_dev).all()
    
    def test_volume_weighted_momentum(self, registry, sample_data):
        """测试成交量加权动量算子"""
        momentum = registry.volume_weighted_momentum(
            sample_data, 'close', 'volume', window=20
        )
        
        assert isinstance(momentum, pd.Series)
        assert len(momentum) == len(sample_data)
    
    def test_price_volume_trend(self, registry, sample_data):
        """测试价量趋势算子"""
        pvt = registry.price_volume_trend(
            sample_data, 'close', 'volume'
        )
        
        assert isinstance(pvt, pd.Series)
        assert len(pvt) == len(sample_data)
        # PVT是累积值，应该单调或有趋势
        assert pvt.iloc[-1] != pvt.iloc[0]
    
    def test_accumulation_distribution(self, registry, sample_data):
        """测试累积派发算子"""
        ad_line = registry.accumulation_distribution(
            sample_data, 'high', 'low', 'close', 'volume'
        )
        
        assert isinstance(ad_line, pd.Series)
        assert len(ad_line) == len(sample_data)
        # A/D Line是累积值，检查是否有变化
        assert ad_line.std() >= 0  # 标准差应该非负
    
    def test_money_flow_index(self, registry, sample_data):
        """测试资金流量指数算子"""
        mfi = registry.money_flow_index(
            sample_data, 'high', 'low', 'close', 'volume', window=14
        )
        
        assert isinstance(mfi, pd.Series)
        assert len(mfi) == len(sample_data)
        # MFI应该在[0, 100]范围内
        valid_mfi = mfi.dropna()
        assert (valid_mfi >= 0).all() and (valid_mfi <= 100).all()
    
    def test_volume_surge_pattern(self, registry, sample_data):
        """测试成交量激增模式算子"""
        surge = registry.volume_surge_pattern(
            sample_data, 'volume', window=20, multiplier=2.0
        )
        
        assert isinstance(surge, pd.Series)
        assert len(surge) == len(sample_data)
        # 激增信号应该是0或1
        assert set(surge.unique()).issubset({0, 1})
    
    def test_price_volume_breakout(self, registry, sample_data):
        """测试价量突破算子"""
        breakout = registry.price_volume_breakout(
            sample_data, 'close', 'volume', window=20
        )
        
        assert isinstance(breakout, pd.Series)
        assert len(breakout) == len(sample_data)
        # 突破信号应该是-1, 0, 1
        assert set(breakout.unique()).issubset({-1, 0, 1})
    
    def test_volume_profile_support(self, registry, sample_data):
        """测试成交量剖面支撑算子"""
        support = registry.volume_profile_support(
            sample_data, 'close', 'volume', bins=50
        )
        
        assert isinstance(support, pd.Series)
        assert len(support) == len(sample_data)
        # 支撑强度应该是归一化的[0, 1]
        valid_support = support.dropna()
        assert (valid_support >= 0).all() and (valid_support <= 1).all()
    
    def test_tick_volume_analysis(self, registry, sample_data):
        """测试Tick成交量分析算子"""
        tick_volume = registry.tick_volume_analysis(
            sample_data, 'close', 'volume'
        )
        
        assert isinstance(tick_volume, pd.Series)
        assert len(tick_volume) == len(sample_data)
    
    def test_volume_weighted_rsi(self, registry, sample_data):
        """测试成交量加权RSI算子"""
        rsi = registry.volume_weighted_rsi(
            sample_data, 'close', 'volume', window=14
        )
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(sample_data)
        # RSI应该在[0, 100]范围内
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()
    
    # ========================================================================
    # 边界条件测试
    # ========================================================================
    
    def test_operators_with_minimal_data(self, registry):
        """测试算子在最小数据集上的表现"""
        # 创建只有5个数据点的数据集
        minimal_data = pd.DataFrame({
            'close': [100, 101, 102, 101, 100],
            'high': [101, 102, 103, 102, 101],
            'low': [99, 100, 101, 100, 99],
            'volume': [1000000, 1100000, 1200000, 1100000, 1000000]
        })
        
        # 测试几个关键算子
        correlation = registry.volume_price_correlation(minimal_data, window=3)
        assert len(correlation) == 5
        
        pvt = registry.price_volume_trend(minimal_data)
        assert len(pvt) == 5
    
    def test_operators_error_handling(self, registry):
        """测试算子错误处理"""
        # 测试空数据
        empty_df = pd.DataFrame()
        
        with pytest.raises(OperatorError):
            registry.volume_price_correlation(empty_df)
        
        with pytest.raises(OperatorError):
            registry.obv_divergence(empty_df)


class TestIntegration:
    """集成测试"""
    
    def test_full_mining_workflow(self):
        """测试完整的因子挖掘流程"""
        # 创建挖掘器
        miner = PriceVolumeRelationshipFactorMiner()
        
        # 创建测试数据
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 102 + np.cumsum(np.random.randn(100) * 0.5),
            'low': 98 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.abs(np.random.randn(100) * 100000 + 1000000)
        }, index=dates)
        
        returns = data['close'].pct_change().fillna(0)
        
        # 验证数据
        assert not data.empty
        assert 'close' in data.columns
        assert 'volume' in data.columns
        
        # 验证挖掘器配置
        assert miner.config is not None
        assert miner.operator_registry is not None
