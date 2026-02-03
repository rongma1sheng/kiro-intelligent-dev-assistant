"""时序深度学习因子挖掘器单元测试

白皮书依据: 第四章 4.1.9 时序深度学习因子挖掘器

测试覆盖:
1. TimeSeriesDeepLearningFactorMiner初始化
2. 8个时序DL算子功能测试
3. 因子挖掘流程测试
4. 时序特征分析测试
5. 序列预测测试
6. 时序分解测试
7. 不确定性量化测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.timeseries_dl import (
    TimeSeriesDeepLearningFactorMiner,
    TimeSeriesDLConfig,
    timeseries_dl_operators
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
    
    # 生成价格数据（带趋势和季节性）
    trend = np.linspace(100, 120, 200)
    seasonality = 5 * np.sin(np.arange(200) * 2 * np.pi / 20)
    noise = np.random.randn(200) * 2
    close = trend + seasonality + noise
    
    # 生成成交量数据
    volume = np.random.randint(1000000, 5000000, 200)
    
    data = pd.DataFrame({
        'close': close,
        'open': close * (1 + np.random.randn(200) * 0.01),
        'high': close * (1 + abs(np.random.randn(200)) * 0.02),
        'low': close * (1 - abs(np.random.randn(200)) * 0.02),
        'volume': volume
    }, index=dates)
    
    return data


@pytest.fixture
def sample_returns(sample_data):
    """生成测试收益率"""
    returns = sample_data['close'].pct_change().fillna(0)
    return returns


class TestTimeSeriesDLConfig:
    """测试TimeSeriesDLConfig配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = TimeSeriesDLConfig()
        
        assert config.lstm_hidden_dim == 64
        assert config.lstm_sequence_length == 20
        assert config.tcn_kernel_size == 3
        assert config.tcn_num_filters == 32
        assert config.wavenet_num_layers == 4
        assert config.attention_window == 20
        assert config.attention_num_heads == 4
        assert config.seq2seq_encoder_length == 20
        assert config.transformer_d_model == 64
        assert config.nbeats_num_blocks == 3
        assert config.deepar_hidden_dim == 40
        assert config.deepar_num_samples == 100
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = TimeSeriesDLConfig(
            lstm_hidden_dim=128,
            tcn_num_filters=64,
            wavenet_num_layers=6,
            attention_num_heads=8,
            deepar_num_samples=200
        )
        
        assert config.lstm_hidden_dim == 128
        assert config.tcn_num_filters == 64
        assert config.wavenet_num_layers == 6
        assert config.attention_num_heads == 8
        assert config.deepar_num_samples == 200


class TestTimeSeriesDLOperators:
    """测试时序深度学习算子"""
    
    def test_lstm_forecast_residual(self, sample_data):
        """测试LSTM预测残差算子"""
        result = timeseries_dl_operators.lstm_forecast_residual(
            sample_data,
            hidden_dim=64,
            sequence_length=20,
            forecast_horizon=1
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_tcn_temporal_pattern(self, sample_data):
        """测试TCN时序模式算子"""
        result = timeseries_dl_operators.tcn_temporal_pattern(
            sample_data,
            kernel_size=3,
            num_filters=32,
            dilation_rates=[1, 2, 4, 8]
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_wavenet_receptive_field(self, sample_data):
        """测试WaveNet感受野算子"""
        result = timeseries_dl_operators.wavenet_receptive_field(
            sample_data,
            num_layers=4,
            kernel_size=2
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_attention_temporal_weight(self, sample_data):
        """测试注意力时序权重算子"""
        result = timeseries_dl_operators.attention_temporal_weight(
            sample_data,
            attention_window=20,
            num_heads=4
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_seq2seq_prediction_error(self, sample_data):
        """测试Seq2Seq预测误差算子"""
        result = timeseries_dl_operators.seq2seq_prediction_error(
            sample_data,
            encoder_length=20,
            decoder_length=5,
            hidden_dim=32
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_transformer_time_embedding(self, sample_data):
        """测试Transformer时间嵌入算子"""
        result = timeseries_dl_operators.transformer_time_embedding(
            sample_data,
            d_model=64,
            max_len=100
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_nbeats_trend_seasonality(self, sample_data):
        """测试N-BEATS趋势季节性算子"""
        result = timeseries_dl_operators.nbeats_trend_seasonality(
            sample_data,
            stack_types=['trend', 'seasonality'],
            num_blocks=3,
            forecast_length=5
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_deepar_probabilistic_forecast(self, sample_data):
        """测试DeepAR概率预测算子"""
        result = timeseries_dl_operators.deepar_probabilistic_forecast(
            sample_data,
            hidden_dim=40,
            num_samples=100,
            forecast_horizon=1
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()


class TestTimeSeriesDeepLearningFactorMiner:
    """测试TimeSeriesDeepLearningFactorMiner类"""
    
    def test_initialization_default(self):
        """测试默认初始化"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        assert miner is not None
        assert isinstance(miner.ts_config, TimeSeriesDLConfig)
        assert hasattr(miner, 'ts_operators')
        assert len(miner.ts_operators) == 8
        assert hasattr(miner, 'operator_whitelist')
        assert len(miner.operator_whitelist) >= 8
    
    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        evolution_config = EvolutionConfig(population_size=30)
        ts_config = TimeSeriesDLConfig(
            lstm_hidden_dim=128,
            tcn_num_filters=64
        )
        
        miner = TimeSeriesDeepLearningFactorMiner(
            config=evolution_config,
            ts_config=ts_config
        )
        
        assert miner.config.population_size == 30
        assert miner.ts_config.lstm_hidden_dim == 128
        assert miner.ts_config.tcn_num_filters == 64
    
    def test_register_ts_operators(self):
        """测试时序DL算子注册"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        expected_operators = [
            'lstm_forecast_residual',
            'tcn_temporal_pattern',
            'wavenet_receptive_field',
            'attention_temporal_weight',
            'seq2seq_prediction_error',
            'transformer_time_embedding',
            'nbeats_trend_seasonality',
            'deepar_probabilistic_forecast'
        ]
        
        for op_name in expected_operators:
            assert op_name in miner.ts_operators
            assert op_name in miner.operator_whitelist
            assert callable(miner.ts_operators[op_name])
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, sample_data, sample_returns):
        """测试因子挖掘流程"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2  # 使用较少代数加快测试
        )
        
        assert isinstance(factors, list)
        assert len(factors) > 0
        
        # 检查因子结构
        for factor in factors:
            assert 'expression' in factor
            assert 'fitness' in factor
            assert 'ic' in factor
            assert 'ir' in factor
            assert 'type' in factor
            assert 'miner' in factor
            assert factor['type'] == 'timeseries_dl'
            assert factor['miner'] == 'TimeSeriesDeepLearningFactorMiner'
    
    def test_analyze_ts_features(self, sample_data):
        """测试时序特征分析"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        analysis = miner.analyze_ts_features(sample_data)
        
        assert isinstance(analysis, dict)
        assert 'lstm' in analysis
        assert 'tcn' in analysis
        assert 'wavenet' in analysis
        assert 'attention' in analysis
        assert 'seq2seq' in analysis
        assert 'transformer' in analysis
        assert 'nbeats' in analysis
        assert 'deepar' in analysis
        
        # 检查LSTM分析
        assert 'mean_residual' in analysis['lstm']
        assert 'hidden_dim' in analysis['lstm']
        
        # 检查TCN分析
        assert 'mean' in analysis['tcn']
        assert 'num_filters' in analysis['tcn']
    
    def test_get_ts_model_summary(self):
        """测试获取时序DL模型摘要"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        summary = miner.get_ts_model_summary()
        
        assert isinstance(summary, dict)
        assert summary['miner_type'] == 'TimeSeriesDeepLearningFactorMiner'
        assert summary['num_operators'] == 8
        assert 'operators' in summary
        assert len(summary['operators']) == 8
        assert 'config' in summary
        
        # 检查配置信息
        config = summary['config']
        assert 'lstm' in config
        assert 'tcn' in config
        assert 'wavenet' in config
        assert 'attention' in config
        assert 'seq2seq' in config
        assert 'transformer' in config
        assert 'nbeats' in config
        assert 'deepar' in config
    
    def test_forecast_sequence_lstm(self, sample_data):
        """测试LSTM序列预测"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        forecast = miner.forecast_sequence(sample_data, forecast_horizon=5, method='lstm')
        
        assert isinstance(forecast, pd.Series)
        assert len(forecast) == len(sample_data)
    
    def test_forecast_sequence_invalid_method(self, sample_data):
        """测试无效预测方法"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        with pytest.raises(ValueError, match="不支持的预测方法"):
            miner.forecast_sequence(sample_data, method='invalid')
    
    def test_decompose_timeseries(self, sample_data):
        """测试时序分解"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        components = miner.decompose_timeseries(sample_data)
        
        assert isinstance(components, dict)
        assert 'trend' in components or 'residual' in components
        
        if 'trend' in components:
            assert isinstance(components['trend'], pd.Series)
            assert len(components['trend']) == len(sample_data)
    
    def test_quantify_uncertainty(self, sample_data):
        """测试不确定性量化"""
        miner = TimeSeriesDeepLearningFactorMiner()
        
        uncertainty = miner.quantify_uncertainty(sample_data)
        
        assert isinstance(uncertainty, pd.Series)
        assert len(uncertainty) == len(sample_data)
        assert (uncertainty >= 0).all()  # 不确定性应该非负


class TestTimeSeriesDLOperatorsEdgeCases:
    """测试时序DL算子的边界情况"""
    
    def test_operators_with_missing_close(self):
        """测试缺少close列的情况"""
        data = pd.DataFrame({
            'volume': [1000, 2000, 3000]
        })
        
        # 所有算子应该返回零序列而不是崩溃
        result1 = timeseries_dl_operators.lstm_forecast_residual(data)
        result2 = timeseries_dl_operators.tcn_temporal_pattern(data)
        result3 = timeseries_dl_operators.wavenet_receptive_field(data)
        result4 = timeseries_dl_operators.attention_temporal_weight(data)
        result5 = timeseries_dl_operators.seq2seq_prediction_error(data)
        result6 = timeseries_dl_operators.transformer_time_embedding(data)
        result7 = timeseries_dl_operators.nbeats_trend_seasonality(data)
        result8 = timeseries_dl_operators.deepar_probabilistic_forecast(data)
        
        assert (result1 == 0).all()
        assert (result2 == 0).all()
        assert (result3 == 0).all()
        assert (result4 == 0).all()
        assert (result5 == 0).all()
        assert (result6 == 0).all()
        assert (result7 == 0).all()
        assert (result8 == 0).all()


class TestTimeSeriesDLIntegration:
    """测试时序深度学习集成"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_data, sample_returns):
        """测试完整的时序深度学习流程"""
        # 1. 初始化挖掘器
        miner = TimeSeriesDeepLearningFactorMiner()
        
        # 2. 分析时序特征
        analysis = miner.analyze_ts_features(sample_data)
        assert len(analysis) == 8
        
        # 3. 序列预测
        forecast = miner.forecast_sequence(sample_data, forecast_horizon=5, method='lstm')
        assert isinstance(forecast, pd.Series)
        
        # 4. 时序分解
        components = miner.decompose_timeseries(sample_data)
        assert isinstance(components, dict)
        
        # 5. 不确定性量化
        uncertainty = miner.quantify_uncertainty(sample_data)
        assert isinstance(uncertainty, pd.Series)
        
        # 6. 挖掘因子
        factors = await miner.mine_factors(sample_data, sample_returns, generations=2)
        assert len(factors) > 0
        
        # 7. 获取模型摘要
        summary = miner.get_ts_model_summary()
        assert summary['num_operators'] == 8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
