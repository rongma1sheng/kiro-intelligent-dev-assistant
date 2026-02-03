"""Meta-Event策略模块

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Event系

事件驱动策略系列：
- S16 Theme Hunter (题材猎手): 基于研报与舆情的热点题材挖掘
"""

from src.strategies.meta_event.s16_theme_hunter import S16ThemeHunterStrategy

__all__ = [
    "S16ThemeHunterStrategy",
]
