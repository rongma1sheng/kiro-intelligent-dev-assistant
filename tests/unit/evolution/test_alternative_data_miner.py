"""替代数据因子挖掘器单元测试

白皮书依据: 第四章 4.1.3 - 替代数据因子挖掘器
测试覆盖率目标: ≥ 85%
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.evolution.alternative_data import (
    AlternativeDataFactorMiner,
    AlternativeDataConfig,
    AlternativeDataOperatorRegistry,
    OperatorError,
    DataQualityError
)


class TestAlternativeDataConfig:
    """测试替代数据配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AlternativeDataConfig(
            data_sources=['satellite', 'social']
        )
        
        assert config.data_sources == ['satellite', 'social']
        assert config.quality_threshold == 0.7
        assert config.freshness_hours == 24
        assert config.uniqueness_threshold == 0.3
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = AlternativeDataConfig(
            data_sources=['web', 'news'],
            quality_threshold=0.8,
            freshness_hours=12,
            uniqueness_threshold=0.4
        )
        
        assert config.data_sources == ['web', 'news']
        assert config.quality_threshold == 0.8
        assert config.freshness_hours == 12
        assert config.uniqueness_threshold == 0.4


class TestAlternativeDataOperatorRegistry:
    """测试替代数据算子注册表"""
    
    @pytest.fixture
    def registry(self):
        """创建算子注册表"""
        return AlternativeDataOperatorRegistry()
    
    def test_registry_initialization(self, registry):
        """测试注册表初始化"""
        assert len(registry.operators) == 8
        assert len(registry.operator_metadata) == 8
    
    def test_get_operator_names(self, registry):
        """测试获取算子名称列表"""
        names = registry.get_operator_names()
        
        assert len(names) == 8
        assert 'satellite_parking_count' in names
        assert 'social_sentiment_momentum' in names
        assert 'web_traffic_growth' in names
        assert 'supply_chain_disruption' in names
        assert 'foot_traffic_anomaly' in names
        assert 'news_sentiment_shock' in names
        assert 'search_trend_leading' in names
        assert 'shipping_volume_change' in names
    
    def test_get_operator(self, registry):
        """测试获取算子函数"""
        operator = registry.get_operator('satellite_parking_count')
        
        assert operator is not None
        assert callable(operator)
    
    def test_get_operator_not_found(self, registry):
        """测试获取不存在的算子"""
        operator = registry.get_operator('nonexistent_operator')
        
        assert operator is None
    
    def test_get_operators_by_category(self, registry):
        """测试按类别获取算子"""
        satellite_ops = registry.get_operators_by_category('satellite')
        
        assert len(satellite_ops) == 1
        assert 'satellite_parking_count' in satellite_ops
    
    def test_validate_operator_input_success(self, registry):
        """测试输入验证成功"""
        data = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [4, 5, 6]
        })
        
        # 不应抛出异常
        registry.validate_operator_input(data, ['col1', 'col2'])
    
    def test_validate_operator_input_empty_data(self, registry):
        """测试空数据验证"""
        data = pd.DataFrame()
        
        with pytest.raises(OperatorError, match="输入数据为空"):
            registry.validate_operator_input(data, ['col1'])
    
    def test_validate_operator_input_missing_columns(self, registry):
        """测试缺失列验证"""
        data = pd.DataFrame({'col1': [1, 2, 3]})
        
        with pytest.raises(OperatorError, match="缺少必需列"):
            registry.validate_operator_input(data, ['col1', 'col2'])
    
    def test_validate_operator_input_too_many_nans(self, registry):
        """测试过多NaN值验证"""
        data = pd.DataFrame({
            'col1': [1, np.nan, np.nan, np.nan, np.nan]
        })
        
        with pytest.raises(DataQualityError, match="NaN值"):
            registry.validate_operator_input(data, ['col1'])


class TestAlternativeDataOperators:
    """测试替代数据算子"""
    
    @pytest.fixture
    def registry(self):
        """创建算子注册表"""
        return AlternativeDataOperatorRegistry()
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        return pd.DataFrame({
            'parking_count': np.random.randint(50, 150, 100),
            'baseline_count': np.full(100, 100),
            'sentiment_score': np.random.uniform(-1, 1, 100),
            'mention_volume': np.random.randint(100, 1000, 100),
            'web_traffic': np.random.randint(1000, 5000, 100),
            'disruption_events': np.random.randint(0, 5, 100),
            'severity_score': np.random.uniform(0, 1, 100),
            'foot_traffic': np.random.randint(500, 2000, 100),
            'news_sentiment': np.random.uniform(-1, 1, 100),
            'news_importance': np.random.uniform(0, 1, 100),
            'search_volume': np.random.randint(100, 1000, 100),
            'returns': np.random.uniform(-0.05, 0.05, 100),
            'shipping_volume': np.random.randint(1000, 5000, 100),
            'baseline_volume': np.full(100, 3000)
        }, index=dates)
    
    def test_satellite_parking_count(self, registry, sample_data):
        """测试卫星停车场计数算子"""
        result = registry.satellite_parking_count(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert result.mean() > 0
    
    def test_social_sentiment_momentum(self, registry, sample_data):
        """测试社交媒体情绪动量算子"""
        result = registry.social_sentiment_momentum(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        # 第一个值应该是NaN（因为diff）
        assert pd.isna(result.iloc[0])
    
    def test_web_traffic_growth(self, registry, sample_data):
        """测试网站流量增长算子"""
        result = registry.web_traffic_growth(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        # 前window个值应该是NaN
        assert result.iloc[30:].notna().any()
    
    def test_supply_chain_disruption(self, registry, sample_data):
        """测试供应链中断指数算子"""
        result = registry.supply_chain_disruption(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert result.min() >= 0  # 中断指数应该非负
    
    def test_foot_traffic_anomaly(self, registry, sample_data):
        """测试人流量异常检测算子"""
        result = registry.foot_traffic_anomaly(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert result.min() >= 0  # Z-score的绝对值应该非负
    
    def test_news_sentiment_shock(self, registry, sample_data):
        """测试新闻情绪冲击算子"""
        result = registry.news_sentiment_shock(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert result.min() >= 0  # 冲击强度应该非负
    
    def test_search_trend_leading(self, registry, sample_data):
        """测试搜索趋势领先指标算子"""
        result = registry.search_trend_leading(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        # 相关系数应该在[-1, 1]范围内
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert valid_values.min() >= -1
            assert valid_values.max() <= 1
    
    def test_shipping_volume_change(self, registry, sample_data):
        """测试航运量变化率算子"""
        result = registry.shipping_volume_change(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        # 变化率应该是合理的
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert valid_values.min() > -1  # 不应该下降超过100%


class TestAlternativeDataFactorMiner:
    """测试替代数据因子挖掘器"""
    
    @pytest.fixture
    def config(self):
        """创建配置"""
        return AlternativeDataConfig(
            data_sources=['satellite', 'social', 'web'],
            quality_threshold=0.7,
            freshness_hours=24,
            uniqueness_threshold=0.3
        )
    
    @pytest.fixture
    def miner(self, config):
        """创建挖掘器"""
        return AlternativeDataFactorMiner(alt_config=config)
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        return pd.DataFrame({
            'close': np.random.uniform(10, 20, 100),
            'volume': np.random.randint(1000, 10000, 100),
            'source': np.random.choice(['satellite', 'social', 'web'], 100),
            'timestamp': dates
        }, index=dates)
    
    @pytest.fixture
    def sample_returns(self):
        """创建示例收益率"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        return pd.Series(
            np.random.uniform(-0.05, 0.05, 100),
            index=dates
        )
    
    def test_miner_initialization(self, miner, config):
        """测试挖掘器初始化"""
        assert miner.alt_config == config
        assert isinstance(miner.operator_registry, AlternativeDataOperatorRegistry)
        assert len(miner.operator_whitelist) >= 8
        assert miner.data_quality_scores == {}
    
    def test_miner_initialization_default_config(self):
        """测试默认配置初始化"""
        miner = AlternativeDataFactorMiner()
        
        assert miner.alt_config is not None
        assert len(miner.alt_config.data_sources) > 0
    
    def test_validate_config_success(self, miner):
        """测试配置验证成功"""
        # 不应抛出异常
        miner._validate_config()
    
    def test_validate_config_invalid_quality_threshold(self):
        """测试无效的质量阈值"""
        config = AlternativeDataConfig(
            data_sources=['satellite'],
            quality_threshold=1.5  # 无效值
        )
        
        with pytest.raises(ValueError, match="quality_threshold必须在"):
            AlternativeDataFactorMiner(alt_config=config)
    
    def test_validate_config_invalid_freshness_hours(self):
        """测试无效的新鲜度小时数"""
        config = AlternativeDataConfig(
            data_sources=['satellite'],
            freshness_hours=-1  # 无效值
        )
        
        with pytest.raises(ValueError, match="freshness_hours必须"):
            AlternativeDataFactorMiner(alt_config=config)
    
    def test_validate_config_invalid_uniqueness_threshold(self):
        """测试无效的独特性阈值"""
        config = AlternativeDataConfig(
            data_sources=['satellite'],
            uniqueness_threshold=1.5  # 无效值
        )
        
        with pytest.raises(ValueError, match="uniqueness_threshold必须在"):
            AlternativeDataFactorMiner(alt_config=config)
    
    def test_validate_config_invalid_data_source(self):
        """测试无效的数据源"""
        config = AlternativeDataConfig(
            data_sources=['invalid_source']
        )
        
        with pytest.raises(ValueError, match="不支持的数据源"):
            AlternativeDataFactorMiner(alt_config=config)
    
    def test_extend_operator_whitelist(self, miner):
        """测试扩展算子白名单"""
        assert 'satellite_parking_count' in miner.operator_whitelist
        assert 'social_sentiment_momentum' in miner.operator_whitelist
        assert 'web_traffic_growth' in miner.operator_whitelist
        assert 'supply_chain_disruption' in miner.operator_whitelist
        assert 'foot_traffic_anomaly' in miner.operator_whitelist
        assert 'news_sentiment_shock' in miner.operator_whitelist
        assert 'search_trend_leading' in miner.operator_whitelist
        assert 'shipping_volume_change' in miner.operator_whitelist
    
    def test_evaluate_data_quality_empty_data(self, miner):
        """测试空数据质量评估"""
        data = pd.DataFrame()
        
        quality = miner.evaluate_data_quality(data, 'test_source')
        
        assert quality == 0.0
    
    def test_evaluate_data_quality_with_timestamp(self, miner, sample_data):
        """测试带时间戳的数据质量评估"""
        quality = miner.evaluate_data_quality(sample_data, 'satellite')
        
        assert 0 <= quality <= 1
        assert 'satellite' in miner.data_quality_scores
    
    def test_evaluate_signal_uniqueness_no_traditional_factors(self, miner):
        """测试无传统因子时的独特性评估"""
        factor_values = pd.Series([1, 2, 3, 4, 5])
        traditional_factors = pd.DataFrame()
        
        uniqueness = miner.evaluate_signal_uniqueness(
            factor_values, traditional_factors
        )
        
        assert uniqueness == 1.0
    
    def test_evaluate_signal_uniqueness_with_traditional_factors(self, miner):
        """测试有传统因子时的独特性评估"""
        np.random.seed(42)
        factor_values = pd.Series(np.random.randn(100))
        traditional_factors = pd.DataFrame({
            'factor1': np.random.randn(100),
            'factor2': np.random.randn(100)
        })
        
        uniqueness = miner.evaluate_signal_uniqueness(
            factor_values, traditional_factors
        )
        
        assert 0 <= uniqueness <= 1
    
    def test_get_data_quality_report(self, miner):
        """测试获取数据质量报告"""
        miner.data_quality_scores = {
            'satellite': 0.8,
            'social': 0.7,
            'web': 0.9
        }
        
        report = miner.get_data_quality_report()
        
        assert 'data_sources' in report
        assert 'quality_scores' in report
        assert 'quality_threshold' in report
        assert 'average_quality' in report
        assert report['average_quality'] == pytest.approx(0.8, abs=0.01)
    
    def test_get_data_quality_report_empty(self, miner):
        """测试空数据质量报告"""
        report = miner.get_data_quality_report()
        
        assert report['average_quality'] == 0.0


class TestAlternativeDataFactorMinerIntegration:
    """测试替代数据因子挖掘器集成"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器"""
        config = AlternativeDataConfig(
            data_sources=['satellite', 'social'],
            quality_threshold=0.5,
            uniqueness_threshold=0.2
        )
        return AlternativeDataFactorMiner(alt_config=config)
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        
        return pd.DataFrame({
            'close': np.random.uniform(10, 20, 50),
            'volume': np.random.randint(1000, 10000, 50),
            'source': np.random.choice(['satellite', 'social'], 50),
            'timestamp': dates
        }, index=dates)
    
    @pytest.fixture
    def sample_returns(self):
        """创建示例收益率"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        
        return pd.Series(
            np.random.uniform(-0.05, 0.05, 50),
            index=dates
        )
    
    @pytest.mark.asyncio
    async def test_mine_factors_basic(self, miner, sample_data, sample_returns):
        """测试基本因子挖掘"""
        # 初始化种群
        await miner.initialize_population(['close', 'volume'])
        
        # 评估适应度
        await miner.evaluate_fitness(sample_data, sample_returns)
        
        # 验证种群
        assert len(miner.population) > 0
        assert all(ind.fitness >= 0 for ind in miner.population)


class TestEdgeCases:
    """测试边界情况"""
    
    def test_operator_with_all_nan_data(self):
        """测试全NaN数据"""
        from src.evolution.alternative_data.alternative_data_operators import DataQualityError
        
        registry = AlternativeDataOperatorRegistry()
        data = pd.DataFrame({
            'parking_count': [np.nan] * 10,
            'baseline_count': [100] * 10
        })
        
        # 全NaN数据应该抛出DataQualityError
        with pytest.raises(DataQualityError, match="NaN值"):
            registry.satellite_parking_count(data)
    
    def test_operator_with_zero_baseline(self):
        """测试零基准值"""
        registry = AlternativeDataOperatorRegistry()
        data = pd.DataFrame({
            'parking_count': [50, 60, 70],
            'baseline_count': [0, 0, 0]
        })
        
        result = registry.satellite_parking_count(data)
        
        assert isinstance(result, pd.Series)
        # 应该处理除零错误
        assert not np.isinf(result).any()
    
    def test_miner_with_minimal_data(self):
        """测试最小数据集"""
        config = AlternativeDataConfig(
            data_sources=['satellite']
        )
        miner = AlternativeDataFactorMiner(alt_config=config)
        
        data = pd.DataFrame({
            'close': [10, 11, 12],
            'source': ['satellite', 'satellite', 'satellite']
        })
        
        quality = miner.evaluate_data_quality(data, 'satellite')
        
        assert 0 <= quality <= 1
