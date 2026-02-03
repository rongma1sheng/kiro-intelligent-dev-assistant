"""机器学习特征工程因子挖掘器单元测试

白皮书依据: 第四章 4.1.8 机器学习特征工程因子挖掘器

测试覆盖:
1. MLFeatureEngineeringFactorMiner初始化
2. 8个ML算子功能测试
3. 因子挖掘流程测试
4. ML特征分析测试
5. 异常检测测试
6. 降维处理测试
7. 特征重要性评估测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.ml_feature_engineering import (
    MLFeatureEngineeringFactorMiner,
    MLFeatureConfig,
    autoencoder_latent_feature,
    pca_principal_component,
    tsne_embedding,
    isolation_forest_anomaly,
    xgboost_feature_importance,
    neural_network_activation,
    ensemble_prediction_variance,
    meta_learning_adaptation,
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
    
    # 生成价格数据（带趋势和噪声）
    trend = np.linspace(100, 120, 200)
    noise = np.random.randn(200) * 2
    close = trend + noise
    
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


class TestMLFeatureConfig:
    """测试MLFeatureConfig配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = MLFeatureConfig()
        
        assert config.autoencoder_latent_dim == 8
        assert config.autoencoder_encoding_layers == 2
        assert config.pca_n_components == 3
        assert config.pca_window == 60
        assert config.tsne_perplexity == 30
        assert config.tsne_n_components == 2
        assert config.isolation_n_estimators == 100
        assert config.isolation_contamination == 0.1
        assert config.xgboost_n_estimators == 50
        assert config.xgboost_max_depth == 3
        assert config.nn_hidden_units == 32
        assert config.nn_num_layers == 2
        assert config.nn_activation == 'relu'
        assert config.ensemble_n_models == 10
        assert config.meta_adaptation_rate == 0.1
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = MLFeatureConfig(
            autoencoder_latent_dim=16,
            pca_n_components=5,
            tsne_perplexity=50,
            isolation_contamination=0.05,
            xgboost_max_depth=5,
            nn_hidden_units=64,
            ensemble_n_models=20,
            meta_adaptation_rate=0.05
        )
        
        assert config.autoencoder_latent_dim == 16
        assert config.pca_n_components == 5
        assert config.tsne_perplexity == 50
        assert config.isolation_contamination == 0.05
        assert config.xgboost_max_depth == 5
        assert config.nn_hidden_units == 64
        assert config.ensemble_n_models == 20
        assert config.meta_adaptation_rate == 0.05


class TestMLFeatureOperators:
    """测试ML特征工程算子"""
    
    def test_autoencoder_latent_feature(self, sample_data):
        """测试自编码器潜在特征算子"""
        result = autoencoder_latent_feature(sample_data, latent_dim=8, encoding_layers=2)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert result.dtype in [np.float64, np.float32]
    
    def test_pca_principal_component(self, sample_data):
        """测试PCA主成分算子"""
        result = pca_principal_component(sample_data, n_components=3, window=60)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_tsne_embedding(self, sample_data):
        """测试t-SNE嵌入算子"""
        result = tsne_embedding(sample_data, perplexity=30, n_components=2, window=100)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_isolation_forest_anomaly(self, sample_data):
        """测试孤立森林异常检测算子"""
        result = isolation_forest_anomaly(
            sample_data,
            n_estimators=100,
            contamination=0.1,
            window=100
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert (result >= 0).all()  # 异常分数应该非负
    
    def test_xgboost_feature_importance(self, sample_data):
        """测试XGBoost特征重要性算子"""
        result = xgboost_feature_importance(
            sample_data,
            n_estimators=50,
            max_depth=3,
            window=100
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_neural_network_activation(self, sample_data):
        """测试神经网络激活值算子"""
        result = neural_network_activation(
            sample_data,
            hidden_units=32,
            num_layers=2,
            activation='relu'
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_ensemble_prediction_variance(self, sample_data):
        """测试集成预测方差算子"""
        result = ensemble_prediction_variance(sample_data, n_models=10, window=60)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert (result >= 0).all()  # 方差应该非负
    
    def test_meta_learning_adaptation(self, sample_data):
        """测试元学习自适应算子"""
        result = meta_learning_adaptation(
            sample_data,
            adaptation_rate=0.1,
            meta_window=100
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()


class TestMLFeatureEngineeringFactorMiner:
    """测试MLFeatureEngineeringFactorMiner类"""
    
    def test_initialization_default(self):
        """测试默认初始化"""
        miner = MLFeatureEngineeringFactorMiner()
        
        assert miner is not None
        assert isinstance(miner.ml_config, MLFeatureConfig)
        assert hasattr(miner, 'ml_operators')
        assert len(miner.ml_operators) == 8
        assert hasattr(miner, 'operator_whitelist')
        assert len(miner.operator_whitelist) >= 8
    
    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        evolution_config = EvolutionConfig(population_size=30)
        ml_config = MLFeatureConfig(
            autoencoder_latent_dim=16,
            pca_n_components=5
        )
        
        miner = MLFeatureEngineeringFactorMiner(
            config=evolution_config,
            ml_config=ml_config
        )
        
        assert miner.config.population_size == 30
        assert miner.ml_config.autoencoder_latent_dim == 16
        assert miner.ml_config.pca_n_components == 5
    
    def test_register_ml_operators(self):
        """测试ML算子注册"""
        miner = MLFeatureEngineeringFactorMiner()
        
        expected_operators = [
            'autoencoder_latent_feature',
            'pca_principal_component',
            'tsne_embedding',
            'isolation_forest_anomaly',
            'xgboost_feature_importance',
            'neural_network_activation',
            'ensemble_prediction_variance',
            'meta_learning_adaptation'
        ]
        
        for op_name in expected_operators:
            assert op_name in miner.ml_operators
            assert op_name in miner.operator_whitelist
            assert callable(miner.ml_operators[op_name])
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, sample_data, sample_returns):
        """测试因子挖掘流程"""
        miner = MLFeatureEngineeringFactorMiner()
        
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
            assert factor['type'] == 'ml_feature_engineering'
            assert factor['miner'] == 'MLFeatureEngineeringFactorMiner'
    
    def test_analyze_ml_features(self, sample_data):
        """测试ML特征分析"""
        miner = MLFeatureEngineeringFactorMiner()
        
        analysis = miner.analyze_ml_features(sample_data)
        
        assert isinstance(analysis, dict)
        assert 'autoencoder' in analysis
        assert 'pca' in analysis
        assert 'tsne' in analysis
        assert 'isolation_forest' in analysis
        assert 'xgboost' in analysis
        assert 'neural_network' in analysis
        assert 'ensemble' in analysis
        assert 'meta_learning' in analysis
        
        # 检查自编码器分析
        assert 'mean' in analysis['autoencoder']
        assert 'std' in analysis['autoencoder']
        assert 'latent_dim' in analysis['autoencoder']
        
        # 检查PCA分析
        assert 'mean' in analysis['pca']
        assert 'n_components' in analysis['pca']
        
        # 检查孤立森林分析
        assert 'mean_anomaly_score' in analysis['isolation_forest']
        assert 'contamination' in analysis['isolation_forest']
    
    def test_get_ml_model_summary(self):
        """测试获取ML模型摘要"""
        miner = MLFeatureEngineeringFactorMiner()
        
        summary = miner.get_ml_model_summary()
        
        assert isinstance(summary, dict)
        assert summary['miner_type'] == 'MLFeatureEngineeringFactorMiner'
        assert summary['num_operators'] == 8
        assert 'operators' in summary
        assert len(summary['operators']) == 8
        assert 'config' in summary
        
        # 检查配置信息
        config = summary['config']
        assert 'autoencoder' in config
        assert 'pca' in config
        assert 'tsne' in config
        assert 'isolation_forest' in config
        assert 'xgboost' in config
        assert 'neural_network' in config
        assert 'ensemble' in config
        assert 'meta_learning' in config
    
    def test_detect_anomalies(self, sample_data):
        """测试异常检测"""
        miner = MLFeatureEngineeringFactorMiner()
        
        is_anomaly = miner.detect_anomalies(sample_data, threshold=2.0)
        
        assert isinstance(is_anomaly, pd.Series)
        assert len(is_anomaly) == len(sample_data)
        assert is_anomaly.dtype == bool
        
        # 应该检测到一些异常点
        num_anomalies = is_anomaly.sum()
        assert num_anomalies >= 0
        assert num_anomalies < len(sample_data) * 0.2  # 异常点不应超过20%
    
    def test_reduce_dimensions_pca(self, sample_data):
        """测试PCA降维"""
        miner = MLFeatureEngineeringFactorMiner()
        
        reduced = miner.reduce_dimensions(sample_data, method='pca', n_components=3)
        
        assert isinstance(reduced, pd.DataFrame)
        assert len(reduced) == len(sample_data)
        assert 'pc1' in reduced.columns
    
    def test_reduce_dimensions_tsne(self, sample_data):
        """测试t-SNE降维"""
        miner = MLFeatureEngineeringFactorMiner()
        
        reduced = miner.reduce_dimensions(sample_data, method='tsne', n_components=2)
        
        assert isinstance(reduced, pd.DataFrame)
        assert len(reduced) == len(sample_data)
        assert 'tsne1' in reduced.columns
    
    def test_reduce_dimensions_invalid_method(self, sample_data):
        """测试无效降维方法"""
        miner = MLFeatureEngineeringFactorMiner()
        
        with pytest.raises(ValueError, match="不支持的降维方法"):
            miner.reduce_dimensions(sample_data, method='invalid')
    
    def test_evaluate_feature_importance(self, sample_data, sample_returns):
        """测试特征重要性评估"""
        miner = MLFeatureEngineeringFactorMiner()
        
        importance = miner.evaluate_feature_importance(sample_data, sample_returns)
        
        assert isinstance(importance, dict)
        assert len(importance) > 0
        
        # 检查重要性值
        for feature, score in importance.items():
            assert isinstance(score, (int, float))
            assert 0 <= score <= 1  # 相关系数的绝对值应该在[0, 1]


class TestMLFeatureOperatorsEdgeCases:
    """测试ML算子的边界情况"""
    
    def test_operators_with_missing_close(self):
        """测试缺少close列的情况"""
        data = pd.DataFrame({
            'volume': [1000, 2000, 3000]
        })
        
        # 所有算子应该返回零序列而不是崩溃
        result1 = autoencoder_latent_feature(data)
        result2 = pca_principal_component(data)
        result3 = tsne_embedding(data)
        result4 = isolation_forest_anomaly(data)
        result5 = xgboost_feature_importance(data)
        result6 = neural_network_activation(data)
        result7 = ensemble_prediction_variance(data)
        result8 = meta_learning_adaptation(data)
        
        assert (result1 == 0).all()
        assert (result2 == 0).all()
        assert (result3 == 0).all()
        assert (result4 == 0).all()
        assert (result5 == 0).all()
        assert (result6 == 0).all()
        assert (result7 == 0).all()
        assert (result8 == 0).all()
    
    def test_operators_with_small_data(self):
        """测试小数据集"""
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104]
        })
        
        # 算子应该能处理小数据集
        result1 = autoencoder_latent_feature(data, latent_dim=2)
        result2 = pca_principal_component(data, window=3)
        result3 = tsne_embedding(data, window=3)
        result4 = isolation_forest_anomaly(data, window=3)
        result5 = xgboost_feature_importance(data, window=3)
        result6 = neural_network_activation(data)
        result7 = ensemble_prediction_variance(data, window=3)
        result8 = meta_learning_adaptation(data, meta_window=3)
        
        assert len(result1) == 5
        assert len(result2) == 5
        assert len(result3) == 5
        assert len(result4) == 5
        assert len(result5) == 5
        assert len(result6) == 5
        assert len(result7) == 5
        assert len(result8) == 5


class TestMLFeatureIntegration:
    """测试ML特征工程集成"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_data, sample_returns):
        """测试完整的ML特征工程流程"""
        # 1. 初始化挖掘器
        miner = MLFeatureEngineeringFactorMiner()
        
        # 2. 分析ML特征
        analysis = miner.analyze_ml_features(sample_data)
        assert len(analysis) == 8
        
        # 3. 检测异常
        anomalies = miner.detect_anomalies(sample_data)
        assert isinstance(anomalies, pd.Series)
        
        # 4. 降维
        reduced_pca = miner.reduce_dimensions(sample_data, method='pca')
        assert isinstance(reduced_pca, pd.DataFrame)
        
        # 5. 评估特征重要性
        importance = miner.evaluate_feature_importance(sample_data, sample_returns)
        assert isinstance(importance, dict)
        
        # 6. 挖掘因子
        factors = await miner.mine_factors(sample_data, sample_returns, generations=2)
        assert len(factors) > 0
        
        # 7. 获取模型摘要
        summary = miner.get_ml_model_summary()
        assert summary['num_operators'] == 8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
