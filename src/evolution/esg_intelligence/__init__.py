"""ESG智能因子挖掘模块

白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

本模块实现基于ESG（环境、社会、治理）的因子挖掘。

Author: MIA Team
Date: 2026-01-25
"""


# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "ESGIntelligenceFactorMiner":  # pylint: disable=no-else-return
        from src.evolution.esg_intelligence.esg_intelligence_miner import (  # pylint: disable=import-outside-toplevel
            ESGIntelligenceFactorMiner,
        )

        return ESGIntelligenceFactorMiner
    elif name == "ESGIntelligenceConfig":
        from src.evolution.esg_intelligence.esg_intelligence_miner import (  # pylint: disable=import-outside-toplevel
            ESGIntelligenceConfig,
        )

        return ESGIntelligenceConfig
    elif name == "ESGIntelligenceOperatorRegistry":
        from src.evolution.esg_intelligence.esg_intelligence_operators import (  # pylint: disable=import-outside-toplevel
            ESGIntelligenceOperatorRegistry,
        )

        return ESGIntelligenceOperatorRegistry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ESGIntelligenceFactorMiner",  # pylint: disable=e0603
    "ESGIntelligenceConfig",  # pylint: disable=e0603
    "ESGIntelligenceOperatorRegistry",  # pylint: disable=e0603
]  # pylint: disable=e0603
