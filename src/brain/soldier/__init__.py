"""Soldier快系统模块

白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)

Soldier是MIA的快速决策系统，负责实时交易决策。采用本地优先、
云端热备的架构，确保低延迟和高可用性。

模块组件:
- SoldierMode: 运行模式枚举
- TradingDecision: 交易决策数据类
- SoldierWithFailover: 支持热备切换的Soldier类
"""

from .core import SoldierMode, SoldierWithFailover, TradingDecision
from .inference_engine import InferenceConfig, LocalInferenceEngine

__all__ = ["SoldierMode", "TradingDecision", "SoldierWithFailover", "LocalInferenceEngine", "InferenceConfig"]
