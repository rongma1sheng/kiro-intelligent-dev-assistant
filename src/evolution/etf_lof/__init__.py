"""ETF and LOF Factor Mining Module

白皮书依据: 第四章 4.1.17 (ETFFactorMiner) 和 4.1.18 (LOFFactorMiner)
版本: v1.6.1

This module provides specialized factor miners for ETF and LOF products,
extending the genetic algorithm framework with product-specific operators.
"""

from .arena_integration import (
    ArenaIntegration,
    submit_to_arena,
)
from .data_models import (
    ArenaTestResult,
    ETFMarketData,
    FactorExpression,
    LOFMarketData,
)
from .etf_factor_miner import ETFFactorMiner
from .etf_operators import ETFOperators
from .exceptions import (
    ArenaSubmissionError,
    ArenaTestError,
    DataQualityError,
    FactorMiningError,
    InsufficientDataError,
    MarketDataMismatchError,
    OperatorError,
)
from .lof_factor_miner import LOFFactorMiner
from .lof_operators import LOFOperators

__all__ = [
    # Data Models
    "ETFMarketData",
    "LOFMarketData",
    "FactorExpression",
    "ArenaTestResult",
    # Exceptions
    "FactorMiningError",
    "OperatorError",
    "DataQualityError",
    "InsufficientDataError",
    "MarketDataMismatchError",
    "ArenaSubmissionError",
    "ArenaTestError",
    # Operators
    "ETFOperators",
    "LOFOperators",
    # Miners
    "ETFFactorMiner",
    "LOFFactorMiner",
    # Arena Integration
    "ArenaIntegration",
    "submit_to_arena",
]

__version__ = "1.6.1"
