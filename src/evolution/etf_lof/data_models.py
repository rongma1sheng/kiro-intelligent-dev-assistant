"""Data models for ETF and LOF factor mining

白皮书依据: 第四章 4.1.17 (ETFFactorMiner) 和 4.1.18 (LOFFactorMiner)
版本: v1.6.1
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class ETFMarketData:
    """ETF market data container

    白皮书依据: 第四章 4.1.17 - ETF Data Model

    Contains all necessary data for ETF factor calculation including:
    - Market price and NAV for premium/discount calculation
    - Creation/redemption data for flow analysis
    - Constituent weights for rebalancing detection
    - Volume and spread data for liquidity analysis

    Attributes:
        symbol: ETF ticker symbol (e.g., '510050.SH')
        date: Trading date
        price: Market price (close price)
        nav: Net Asset Value
        volume: Trading volume
        constituent_weights: Dictionary mapping constituent symbols to weights
        creation_units: Number of creation units on this date
        redemption_units: Number of redemption units on this date
        bid_price: Best bid price (optional, for spread calculation)
        ask_price: Best ask price (optional, for spread calculation)
        index_price: Underlying index price (optional, for tracking error)

    Raises:
        ValueError: If required fields are missing or invalid
        TypeError: If field types are incorrect
    """

    symbol: str
    date: date
    price: float
    nav: float
    volume: float
    constituent_weights: Dict[str, float] = field(default_factory=dict)
    creation_units: float = 0.0
    redemption_units: float = 0.0
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    index_price: Optional[float] = None

    def __post_init__(self):
        """Validate data after initialization

        白皮书依据: 第四章 4.1 - Data Validation Standards
        """
        # Validate symbol
        if not isinstance(self.symbol, str) or not self.symbol:
            raise ValueError(f"Invalid symbol: {self.symbol}")

        # Validate date
        if not isinstance(self.date, date):
            raise TypeError(f"date must be datetime.date, got {type(self.date)}")

        # Validate price (must be positive)
        if not isinstance(self.price, (int, float)) or self.price <= 0:
            raise ValueError(f"price must be positive, got {self.price}")

        # Validate NAV (must be positive)
        if not isinstance(self.nav, (int, float)) or self.nav <= 0:
            raise ValueError(f"nav must be positive, got {self.nav}")

        # Validate volume (must be non-negative)
        if not isinstance(self.volume, (int, float)) or self.volume < 0:
            raise ValueError(f"volume must be non-negative, got {self.volume}")

        # Validate creation/redemption units (must be non-negative)
        if not isinstance(self.creation_units, (int, float)) or self.creation_units < 0:
            raise ValueError(f"creation_units must be non-negative, got {self.creation_units}")

        if not isinstance(self.redemption_units, (int, float)) or self.redemption_units < 0:
            raise ValueError(f"redemption_units must be non-negative, got {self.redemption_units}")

        # Validate bid/ask prices if provided
        if self.bid_price is not None:
            if not isinstance(self.bid_price, (int, float)) or self.bid_price <= 0:
                raise ValueError(f"bid_price must be positive, got {self.bid_price}")

        if self.ask_price is not None:
            if not isinstance(self.ask_price, (int, float)) or self.ask_price <= 0:
                raise ValueError(f"ask_price must be positive, got {self.ask_price}")

            # Validate bid <= ask
            if self.bid_price is not None and self.bid_price > self.ask_price:
                raise ValueError(f"bid_price ({self.bid_price}) must be <= ask_price ({self.ask_price})")

        # Validate index price if provided
        if self.index_price is not None:
            if not isinstance(self.index_price, (int, float)) or self.index_price <= 0:
                raise ValueError(f"index_price must be positive, got {self.index_price}")

        # Validate constituent weights
        if not isinstance(self.constituent_weights, dict):
            raise TypeError(f"constituent_weights must be dict, got {type(self.constituent_weights)}")

        # Validate weight values (must be between 0 and 1, sum to ~1.0)
        if self.constituent_weights:
            for symbol, weight in self.constituent_weights.items():
                if not isinstance(weight, (int, float)) or not (0 <= weight <= 1):  # pylint: disable=superfluous-parens
                    raise ValueError(f"Invalid weight for {symbol}: {weight} (must be in [0, 1])")

            total_weight = sum(self.constituent_weights.values())
            if not (0.95 <= total_weight <= 1.05):  # Allow 5% tolerance  # pylint: disable=superfluous-parens
                raise ValueError(f"Constituent weights sum to {total_weight}, expected ~1.0")


@dataclass
class LOFMarketData:
    """LOF market data container

    白皮书依据: 第四章 4.1.18 - LOF Data Model

    Contains all necessary data for LOF factor calculation including:
    - Onmarket and offmarket prices for arbitrage analysis
    - Fund manager data for alpha calculation
    - Holdings data for concentration analysis
    - Performance data for persistence analysis

    Attributes:
        symbol: LOF ticker symbol (e.g., '163406')
        date: Trading date
        onmarket_price: Exchange trading price
        offmarket_price: Subscription/redemption price (NAV-based)
        onmarket_volume: Exchange trading volume
        offmarket_volume: Subscription/redemption volume (optional)
        fund_manager_id: Fund manager identifier (optional)
        holdings: Dictionary mapping stock symbols to positions (optional)
        nav: Net Asset Value
        benchmark_price: Benchmark index price (optional)

    Raises:
        ValueError: If required fields are missing or invalid
        TypeError: If field types are incorrect
    """

    symbol: str
    date: date
    onmarket_price: float
    offmarket_price: float
    onmarket_volume: float
    nav: float
    offmarket_volume: Optional[float] = None
    fund_manager_id: Optional[str] = None
    holdings: Dict[str, float] = field(default_factory=dict)
    benchmark_price: Optional[float] = None

    def __post_init__(self):
        """Validate data after initialization

        白皮书依据: 第四章 4.1 - Data Validation Standards
        """
        # Validate symbol
        if not isinstance(self.symbol, str) or not self.symbol:
            raise ValueError(f"Invalid symbol: {self.symbol}")

        # Validate date
        if not isinstance(self.date, date):
            raise TypeError(f"date must be datetime.date, got {type(self.date)}")

        # Validate onmarket price (must be positive)
        if not isinstance(self.onmarket_price, (int, float)) or self.onmarket_price <= 0:
            raise ValueError(f"onmarket_price must be positive, got {self.onmarket_price}")

        # Validate offmarket price (must be positive)
        if not isinstance(self.offmarket_price, (int, float)) or self.offmarket_price <= 0:
            raise ValueError(f"offmarket_price must be positive, got {self.offmarket_price}")

        # Validate NAV (must be positive)
        if not isinstance(self.nav, (int, float)) or self.nav <= 0:
            raise ValueError(f"nav must be positive, got {self.nav}")

        # Validate onmarket volume (must be non-negative)
        if not isinstance(self.onmarket_volume, (int, float)) or self.onmarket_volume < 0:
            raise ValueError(f"onmarket_volume must be non-negative, got {self.onmarket_volume}")

        # Validate offmarket volume if provided
        if self.offmarket_volume is not None:
            if not isinstance(self.offmarket_volume, (int, float)) or self.offmarket_volume < 0:
                raise ValueError(f"offmarket_volume must be non-negative, got {self.offmarket_volume}")

        # Validate benchmark price if provided
        if self.benchmark_price is not None:
            if not isinstance(self.benchmark_price, (int, float)) or self.benchmark_price <= 0:
                raise ValueError(f"benchmark_price must be positive, got {self.benchmark_price}")

        # Validate holdings
        if not isinstance(self.holdings, dict):
            raise TypeError(f"holdings must be dict, got {type(self.holdings)}")

        # Validate holding values (must be non-negative)
        if self.holdings:
            for symbol, position in self.holdings.items():
                if not isinstance(position, (int, float)) or position < 0:
                    raise ValueError(f"Invalid position for {symbol}: {position} (must be non-negative)")


@dataclass
class FactorExpression:
    """Factor expression container

    白皮书依据: 第四章 4.1 - Factor Expression Definition

    Represents a factor as a mathematical expression that can be evaluated
    on market data to produce factor values.

    Attributes:
        expression_string: Human-readable expression (e.g., "etf_premium_discount(close, nav)")
        operator_tree: Parsed operator tree for evaluation
        parameter_dict: Dictionary of parameters used in the expression

    Example:
        >>> expr = FactorExpression(
        ...     expression_string="etf_premium_discount(close, nav)",
        ...     operator_tree={'op': 'etf_premium_discount', 'args': ['close', 'nav']},
        ...     parameter_dict={}
        ... )
    """

    expression_string: str
    operator_tree: Dict[str, Any]
    parameter_dict: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate expression after initialization"""
        if not isinstance(self.expression_string, str) or not self.expression_string:
            raise ValueError(f"Invalid expression_string: {self.expression_string}")

        if not isinstance(self.operator_tree, dict):
            raise TypeError(f"operator_tree must be dict, got {type(self.operator_tree)}")

        if not isinstance(self.parameter_dict, dict):
            raise TypeError(f"parameter_dict must be dict, got {type(self.parameter_dict)}")


@dataclass
class ArenaTestResult:  # pylint: disable=too-many-instance-attributes
    """Arena test result container

    白皮书依据: 第四章 4.2.1 - Factor Arena Testing Results
    版本: v1.6.1 - 扩展支持ETF/LOF因子测试

    包含因子通过Arena三轨测试系统的完整结果。

    三轨测试:
    1. Reality Track: 真实历史数据测试
    2. Hell Track: 极端市场环境测试
    3. Cross-Market Track: 跨市场适应性测试

    Attributes:
        factor_expression: 因子表达式字符串
        factor_type: 因子类型 ('etf', 'lof', 'stock', etc.)
        submission_time: 提交时间
        test_completion_time: 测试完成时间(可选)
        status: 测试状态 ('submitted', 'testing', 'passed', 'failed')

        # Reality Track指标
        reality_ic_mean: IC均值
        reality_ic_std: IC标准差
        reality_ir: 信息比率
        reality_sharpe: 夏普比率
        reality_max_drawdown: 最大回撤
        reality_annual_return: 年化收益
        reality_win_rate: 胜率

        # Hell Track指标
        hell_survival_rate: 存活率
        hell_ic_decay_rate: IC衰减率
        hell_recovery_ability: 恢复能力
        hell_stress_score: 压力得分

        # Cross-Market Track指标
        cross_market_markets_passed: 通过市场数量
        cross_market_adaptability: 适应性评分
        cross_market_consistency: 一致性评分

        # 综合评分
        overall_score: 综合得分 (0-100)
        passed: 是否通过所有测试

        # 队列信息
        queue_position: 队列位置(可选)
        estimated_test_time_minutes: 预计测试时间(分钟,可选)

        # 详细信息
        detailed_metrics: 详细指标字典
        recommendations: 改进建议列表
        metadata: 元数据字典

    Example:
        >>> result = ArenaTestResult(
        ...     factor_expression="etf_premium_discount(close, nav)",
        ...     factor_type="etf",
        ...     submission_time=datetime.now(),
        ...     status="submitted",
        ...     queue_position=5,
        ...     estimated_test_time_minutes=5.0
        ... )
    """

    factor_expression: str
    factor_type: str
    submission_time: datetime
    status: str  # 'submitted', 'testing', 'passed', 'failed'

    # 可选字段 - 测试完成后填充
    test_completion_time: Optional[datetime] = None

    # Reality Track指标
    reality_ic_mean: float = 0.0
    reality_ic_std: float = 0.0
    reality_ir: float = 0.0
    reality_sharpe: float = 0.0
    reality_max_drawdown: float = 0.0
    reality_annual_return: float = 0.0
    reality_win_rate: float = 0.0

    # Hell Track指标
    hell_survival_rate: float = 0.0
    hell_ic_decay_rate: float = 0.0
    hell_recovery_ability: float = 0.0
    hell_stress_score: float = 0.0

    # Cross-Market Track指标
    cross_market_markets_passed: int = 0
    cross_market_adaptability: float = 0.0
    cross_market_consistency: float = 0.0

    # 综合评分
    overall_score: float = 0.0
    passed: bool = False

    # 队列信息
    queue_position: Optional[int] = None
    estimated_test_time_minutes: Optional[float] = None

    # 详细信息
    detailed_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate test result after initialization

        白皮书依据: 第四章 4.1 - Data Validation Standards
        """
        # 验证必填字段
        if not isinstance(self.factor_expression, str) or not self.factor_expression:
            raise ValueError(f"Invalid factor_expression: {self.factor_expression}")

        if not isinstance(self.factor_type, str) or not self.factor_type:
            raise ValueError(f"Invalid factor_type: {self.factor_type}")

        if not isinstance(self.submission_time, datetime):
            raise TypeError(f"submission_time must be datetime, got {type(self.submission_time)}")

        # 验证状态
        valid_statuses = ["submitted", "testing", "passed", "failed"]
        if self.status not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}, got {self.status}")

        # 验证测试完成时间
        if self.test_completion_time is not None:
            if not isinstance(self.test_completion_time, datetime):
                raise TypeError(f"test_completion_time must be datetime, got {type(self.test_completion_time)}")

            if self.test_completion_time < self.submission_time:
                raise ValueError("test_completion_time must be >= submission_time")

        # 验证评分范围
        if not 0 <= self.overall_score <= 100:
            raise ValueError(f"overall_score must be in [0, 100], got {self.overall_score}")

        # 验证队列位置
        if self.queue_position is not None and self.queue_position < 0:
            raise ValueError(f"queue_position must be >= 0, got {self.queue_position}")

        # 验证预计测试时间
        if self.estimated_test_time_minutes is not None and self.estimated_test_time_minutes < 0:
            raise ValueError(f"estimated_test_time_minutes must be >= 0, got {self.estimated_test_time_minutes}")
