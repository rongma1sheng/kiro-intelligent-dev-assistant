"""事件驱动因子挖掘模块

白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

本模块实现基于公司事件的因子挖掘。

Author: MIA Team
Date: 2026-01-25
"""


# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "EventDrivenFactorMiner":  # pylint: disable=no-else-return
        from src.evolution.event_driven.event_driven_miner import (  # pylint: disable=import-outside-toplevel
            EventDrivenFactorMiner,
        )

        return EventDrivenFactorMiner
    elif name == "EventDrivenConfig":
        from src.evolution.event_driven.event_driven_miner import (  # pylint: disable=import-outside-toplevel
            EventDrivenConfig,
        )

        return EventDrivenConfig
    elif name == "EventDrivenOperatorRegistry":
        from src.evolution.event_driven.event_driven_operators import (  # pylint: disable=import-outside-toplevel
            EventDrivenOperatorRegistry,
        )

        return EventDrivenOperatorRegistry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["EventDrivenFactorMiner", "EventDrivenConfig", "EventDrivenOperatorRegistry"]  # pylint: disable=e0603
