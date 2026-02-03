"""AI增强因子挖掘器模块

白皮书依据: 第四章 4.1.7 AI增强因子挖掘器
"""

from .ai_enhanced_miner import AIEnhancedConfig, AIEnhancedFactorMiner
from .ai_enhanced_operators import (
    attention_mechanism,
    cnn_feature_map,
    gan_synthetic_feature,
    gnn_node_embedding,
    lstm_hidden_state,
    multimodal_fusion,
    rl_adaptive_weight,
    transformer_attention,
)

__all__ = [
    "AIEnhancedFactorMiner",
    "AIEnhancedConfig",
    "transformer_attention",
    "gnn_node_embedding",
    "rl_adaptive_weight",
    "multimodal_fusion",
    "gan_synthetic_feature",
    "lstm_hidden_state",
    "cnn_feature_map",
    "attention_mechanism",
]
