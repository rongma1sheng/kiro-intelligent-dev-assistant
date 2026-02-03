"""Custom exceptions for ETF and LOF factor mining

白皮书依据: 第四章 4.1 - Error Handling Standards
版本: v1.6.1
"""


class FactorMiningError(Exception):
    """Base exception for all factor mining errors

    白皮书依据: 第四章 4.1 - Error Handling Standards
    """


class OperatorError(FactorMiningError):
    """Exception raised when operator calculation fails

    白皮书依据: 第四章 4.1.17, 4.1.18 - Operator Definitions

    This exception is raised when:
    - Operator receives invalid input (missing data, wrong type)
    - Operator calculation encounters mathematical errors (division by zero, etc.)
    - Operator cannot produce valid output
    """


class DataQualityError(FactorMiningError):
    """Exception raised when data quality is insufficient

    白皮书依据: 第四章 4.1 - Data Quality Requirements

    This exception is raised when:
    - More than 50% of samples return NaN for an operator
    - Data contains too many missing values
    - Data fails validation checks
    """


class InsufficientDataError(FactorMiningError):
    """Exception raised when insufficient data is available

    白皮书依据: 第四章 4.2 - Arena Testing Requirements

    This exception is raised when:
    - Arena test requires minimum data but not enough is available
    - Cross-market test cannot find sufficient overlap
    - Historical data is too short for backtesting
    """


class MarketDataMismatchError(FactorMiningError):
    """Exception raised when market data cannot be aligned

    白皮书依据: 第四章 4.2 - Cross-Market Track

    This exception is raised when:
    - Cross-market test cannot align data from different markets
    - Market-specific data formats are incompatible
    - Date ranges do not overlap sufficiently
    """


class ArenaSubmissionError(FactorMiningError):
    """Exception raised when Arena submission fails

    白皮书依据: 第四章 4.2.1 - Arena Submission

    This exception is raised when:
    - Factor validation fails before submission
    - Arena queue is full
    - Network connection to Arena fails
    - Submission is rejected by Arena system
    """


class ArenaTestError(FactorMiningError):
    """Exception raised when Arena test execution fails

    白皮书依据: 第四章 4.2.1 - Arena Testing

    This exception is raised when:
    - Arena test result is invalid or incomplete
    - Test execution encounters errors
    - Test result processing fails
    """
