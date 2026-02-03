"""情绪与行为因子挖掘模块

白皮书依据: 第四章 4.1.8 情绪与行为因子挖掘器

本模块实现基于市场情绪和投资者行为的因子挖掘。

Author: MIA Team
Date: 2026-01-25
"""

from src.evolution.sentiment_behavior.sentiment_behavior_miner import (
    SentimentBehaviorConfig,
    SentimentBehaviorFactorMiner,
)
from src.evolution.sentiment_behavior.sentiment_behavior_operators import SentimentBehaviorOperatorRegistry

__all__ = ["SentimentBehaviorFactorMiner", "SentimentBehaviorConfig", "SentimentBehaviorOperatorRegistry"]
