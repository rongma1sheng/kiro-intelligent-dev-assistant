"""AI增强因子挖掘器单元测试

白皮书依据: 第四章 4.1.7 AI增强因子挖掘器
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.ai_enhanced import (
    AIEnhancedFactorMiner,
    AIEnhancedConfig,
    transformer_attention,
    gnn_node_embedding,
    rl_adaptive_weight,
    multimodal_fusion,
    gan_synthetic_feature,
    lstm_hidden_state,
    cnn_feature_map,
    attention_mechanism,
)
from src.evolution.genetic_miner import EvolutionConfig


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    data = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(100) * 2),
        'volume': np.random.randint(1000000, 10000000, 100),
        'high': 102 + np.cumsum(np.random.randn(100) * 2),
        'low': 98 + np.cumsum(np.random.randn(100) * 2),
    }, index=dates)
    
    # 确保HLOC关系正确
    data['high'] = data[['close', 'high']].max(axis=1)
    data['low'] = data[['close', 'low']].min(axis=1)
    
    return data


@pytest.fixture
def sample_returns(sample_data):
    """生成测试收益率"""
    return sample_data['close'].pct_change().shift(-1).fillna(0)


@pytest.fixture
def ai_miner():
    """创建AI增强因子挖掘器实例"""
    config = EvolutionConfig(population_size=10, mutation_rate=0.2)
    ai_config = AIEnhancedConfig()
    return AIEnhancedFactorMiner(config=config, ai_config=ai_config)


# ==================== 算子测试 ====================

class TestAIEnhancedOperators:
    """AI增强算子测试"""
    
    def test_transformer_attention(self, sample_data):
        """测试Transformer注意力机制"""
        result = transformer_attention(sample_data, window=20, num_heads=4, d_model=64)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        assert result.dtype in [np.float64, np.float32]
    
    def test_transformer_attention_missing_close(self):
        """测试缺少close列的情况"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = transformer_attention(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert (result == 0.0).all()
    
    def test_gnn_node_embedding(self, sample_data):
        """测试图神经网络节点嵌入"""
        result = gnn_node_embedding(
            sample_data,
            correlation_window=60,
            embedding_dim=32,
            num_iterations=3
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_gnn_node_embedding_missing_close(self):
        """测试GNN缺少close列"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = gnn_node_embedding(data)
        
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()
    
    def test_rl_adaptive_weight(self, sample_data):
        """测试强化学习自适应权重"""
        result = rl_adaptive_weight(
            sample_data,
            learning_rate=0.01,
            discount_factor=0.95,
            exploration_rate=0.1
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        # 权重应该在[0, 1]范围内
        assert result.min() >= 0.0
        assert result.max() <= 1.0
    
    def test_rl_adaptive_weight_missing_close(self):
        """测试RL缺少close列"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = rl_adaptive_weight(data)
        
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()
    
    def test_multimodal_fusion(self, sample_data):
        """测试多模态融合"""
        result = multimodal_fusion(
            sample_data,
            price_weight=0.4,
            volume_weight=0.3,
            volatility_weight=0.3
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_multimodal_fusion_missing_volume(self, sample_data):
        """测试多模态融合缺少volume列"""
        data = sample_data[['close']].copy()
        result = multimodal_fusion(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
    
    def test_gan_synthetic_feature(self, sample_data):
        """测试GAN生成合成特征"""
        result = gan_synthetic_feature(
            sample_data,
            noise_dim=10,
            num_samples=100
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_gan_synthetic_feature_missing_close(self):
        """测试GAN缺少close列"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = gan_synthetic_feature(data)
        
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()
    
    def test_lstm_hidden_state(self, sample_data):
        """测试LSTM隐藏状态"""
        result = lstm_hidden_state(
            sample_data,
            hidden_dim=64,
            sequence_length=20
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_lstm_hidden_state_missing_close(self):
        """测试LSTM缺少close列"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = lstm_hidden_state(data)
        
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()
    
    def test_cnn_feature_map(self, sample_data):
        """测试CNN特征图"""
        result = cnn_feature_map(
            sample_data,
            kernel_size=5,
            num_filters=16
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
        # CNN输出应该非负（ReLU激活）
        assert result.min() >= 0.0
    
    def test_cnn_feature_map_missing_close(self):
        """测试CNN缺少close列"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = cnn_feature_map(data)
        
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()
    
    def test_attention_mechanism(self, sample_data):
        """测试注意力机制"""
        result = attention_mechanism(
            sample_data,
            attention_window=20
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_attention_mechanism_missing_close(self):
        """测试注意力机制缺少close列"""
        data = pd.DataFrame({'volume': [1000, 2000, 3000]})
        result = attention_mechanism(data)
        
        assert isinstance(result, pd.Series)
        assert (result == 0.0).all()


# ==================== 挖掘器测试 ====================

class TestAIEnhancedFactorMiner:
    """AI增强因子挖掘器测试"""
    
    def test_initialization(self, ai_miner):
        """测试初始化"""
        assert ai_miner is not None
        assert isinstance(ai_miner.ai_config, AIEnhancedConfig)
        assert len(ai_miner.ai_operators) == 8
        assert 'transformer_attention' in ai_miner.ai_operators
        assert 'gnn_node_embedding' in ai_miner.ai_operators
        assert 'rl_adaptive_weight' in ai_miner.ai_operators
    
    def test_register_ai_operators(self, ai_miner):
        """测试AI算子注册"""
        assert len(ai_miner.ai_operators) == 8
        
        expected_operators = [
            'transformer_attention',
            'gnn_node_embedding',
            'rl_adaptive_weight',
            'multimodal_fusion',
            'gan_synthetic_feature',
            'lstm_hidden_state',
            'cnn_feature_map',
            'attention_mechanism',
        ]
        
        for op in expected_operators:
            assert op in ai_miner.ai_operators
            assert op in ai_miner.operator_whitelist
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, ai_miner, sample_data, sample_returns):
        """测试因子挖掘"""
        factors = await ai_miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2
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
            assert factor['type'] == 'ai_enhanced'
            assert factor['miner'] == 'AIEnhancedFactorMiner'
    
    @pytest.mark.asyncio
    async def test_mine_factors_empty_data(self, ai_miner):
        """测试空数据挖掘"""
        empty_data = pd.DataFrame()
        empty_returns = pd.Series()
        
        factors = await ai_miner.mine_factors(
            data=empty_data,
            returns=empty_returns,
            generations=1
        )
        
        assert isinstance(factors, list)
    
    def test_analyze_ai_features(self, ai_miner, sample_data):
        """测试AI特征分析"""
        analysis = ai_miner.analyze_ai_features(sample_data)
        
        assert isinstance(analysis, dict)
        assert 'transformer_attention' in analysis
        assert 'gnn_embedding' in analysis
        assert 'rl_weights' in analysis
        assert 'multimodal_fusion' in analysis
        assert 'gan_features' in analysis
        assert 'lstm_states' in analysis
        assert 'cnn_features' in analysis
        assert 'attention_weights' in analysis
        
        # 检查Transformer分析
        transformer_analysis = analysis['transformer_attention']
        assert 'mean' in transformer_analysis
        assert 'std' in transformer_analysis
        assert 'min' in transformer_analysis
        assert 'max' in transformer_analysis
        
        # 检查GNN分析
        gnn_analysis = analysis['gnn_embedding']
        assert 'mean' in gnn_analysis
        assert 'std' in gnn_analysis
        assert 'embedding_dim' in gnn_analysis
        
        # 检查RL分析
        rl_analysis = analysis['rl_weights']
        assert 'mean_weight' in rl_analysis
        assert 'weight_std' in rl_analysis
        assert 'learning_rate' in rl_analysis
    
    def test_analyze_ai_features_empty_data(self, ai_miner):
        """测试空数据特征分析"""
        empty_data = pd.DataFrame()
        analysis = ai_miner.analyze_ai_features(empty_data)
        
        assert isinstance(analysis, dict)
    
    def test_get_ai_model_summary(self, ai_miner):
        """测试获取AI模型摘要"""
        summary = ai_miner.get_ai_model_summary()
        
        assert isinstance(summary, dict)
        assert summary['miner_type'] == 'AIEnhancedFactorMiner'
        assert summary['num_operators'] == 8
        assert 'operators' in summary
        assert 'config' in summary
        
        # 检查配置
        config = summary['config']
        assert 'transformer' in config
        assert 'gnn' in config
        assert 'rl' in config
        assert 'multimodal' in config
        assert 'gan' in config
        assert 'lstm' in config
        assert 'cnn' in config
        assert 'attention' in config
        
        # 检查Transformer配置
        transformer_config = config['transformer']
        assert 'window' in transformer_config
        assert 'heads' in transformer_config
        assert 'd_model' in transformer_config


# ==================== 配置测试 ====================

class TestAIEnhancedConfig:
    """AI增强配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AIEnhancedConfig()
        
        # Transformer配置
        assert config.transformer_window == 20
        assert config.transformer_heads == 4
        assert config.transformer_d_model == 64
        
        # GNN配置
        assert config.gnn_correlation_window == 60
        assert config.gnn_embedding_dim == 32
        assert config.gnn_iterations == 3
        
        # RL配置
        assert config.rl_learning_rate == 0.01
        assert config.rl_discount_factor == 0.95
        assert config.rl_exploration_rate == 0.1
        
        # 多模态配置
        assert config.multimodal_price_weight == 0.4
        assert config.multimodal_volume_weight == 0.3
        assert config.multimodal_volatility_weight == 0.3
        
        # GAN配置
        assert config.gan_noise_dim == 10
        assert config.gan_num_samples == 100
        
        # LSTM配置
        assert config.lstm_hidden_dim == 64
        assert config.lstm_sequence_length == 20
        
        # CNN配置
        assert config.cnn_kernel_size == 5
        assert config.cnn_num_filters == 16
        
        # 注意力配置
        assert config.attention_window == 20
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = AIEnhancedConfig(
            transformer_window=30,
            gnn_embedding_dim=64,
            rl_learning_rate=0.05
        )
        
        assert config.transformer_window == 30
        assert config.gnn_embedding_dim == 64
        assert config.rl_learning_rate == 0.05


# ==================== 集成测试 ====================

class TestAIEnhancedIntegration:
    """AI增强因子挖掘器集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_mining_pipeline(self, sample_data, sample_returns):
        """测试完整挖掘流程"""
        # 创建挖掘器
        config = EvolutionConfig(population_size=5, mutation_rate=0.2)
        ai_config = AIEnhancedConfig()
        miner = AIEnhancedFactorMiner(config=config, ai_config=ai_config)
        
        # 挖掘因子
        factors = await miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2
        )
        
        # 验证结果
        assert len(factors) > 0
        assert all(f['type'] == 'ai_enhanced' for f in factors)
        
        # 分析AI特征
        analysis = miner.analyze_ai_features(sample_data)
        assert len(analysis) == 8
        
        # 获取模型摘要
        summary = miner.get_ai_model_summary()
        assert summary['num_operators'] == 8
    
    def test_all_operators_work(self, sample_data):
        """测试所有算子都能正常工作"""
        operators = [
            transformer_attention,
            gnn_node_embedding,
            rl_adaptive_weight,
            multimodal_fusion,
            gan_synthetic_feature,
            lstm_hidden_state,
            cnn_feature_map,
            attention_mechanism,
        ]
        
        for op in operators:
            result = op(sample_data)
            assert isinstance(result, pd.Series)
            assert len(result) == len(sample_data)
            assert not result.isna().all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
