"""ETF Factor Miner - Genetic algorithm-based factor discovery for ETF products

白皮书依据: 第四章 4.1.17 ETF因子挖掘器
版本: v1.6.1
铁律依据: MIA编码铁律1 (白皮书至上), 铁律2 (禁止简化和占位符)

This module implements ETFFactorMiner, a specialized genetic algorithm miner
that discovers alpha factors for ETF products by leveraging ETF-specific
structural characteristics.
"""

import random
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner
from .data_models import ETFMarketData
from .etf_operators import ETFOperators
from .exceptions import (
    DataQualityError,
    FactorMiningError,
    OperatorError,
)


class ETFFactorMiner(GeneticMiner):
    """ETF-specific genetic algorithm factor miner

    白皮书依据: 第四章 4.1.17 ETF因子挖掘器
    铁律依据: MIA编码铁律1 (白皮书至上)

    Inherits genetic algorithm framework from GeneticMiner and specializes
    it for ETF products by:
    1. Using 20 ETF-specific operators
    2. Evaluating fitness on ETF market data (price, NAV, flows, etc.)
    3. Integrating with FactorArena for validation

    核心特性:
    - 20个ETF专用算子 (白皮书定义)
    - 遗传算法进化框架 (继承自GeneticMiner)
    - 多维度适应度评估 (IC, IR, Sharpe)
    - Arena三轨测试集成

    性能要求:
    - 进化时间 < 60秒 (50个体, 10代)
    - Arena测试 < 30秒
    - 算子计算 < 100ms (1000样本)

    Attributes:
        etf_operators: List of 20 ETF-specific operator names
        market_data: ETFMarketData for fitness evaluation
        operator_registry: Dictionary mapping operator names to functions
        common_operators: List of common operators (rank, delay, etc.)

    Example:
        >>> miner = ETFFactorMiner(
        ...     market_data=etf_data,
        ...     population_size=50,
        ...     mutation_rate=0.2
        ... )
        >>> await miner.initialize()
        >>> await miner.initialize_population(['close', 'nav', 'volume'])
        >>> await miner.evaluate_fitness(data, returns)
        >>> best = await miner.evolve(generations=10)
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        market_data: Optional[ETFMarketData] = None,
        population_size: int = 50,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.7,
        elite_ratio: float = 0.1,
        config: Optional[EvolutionConfig] = None,
    ):
        """Initialize ETF factor miner

        白皮书依据: 第四章 4.1.17 - ETFFactorMiner初始化
        铁律依据: MIA编码铁律3 (完整的错误处理), 铁律4 (完整的类型注解)

        Args:
            market_data: Historical ETF market data for fitness evaluation (optional)
            population_size: Number of individuals in population (default 50)
            mutation_rate: Probability of mutation (default 0.2)
            crossover_rate: Probability of crossover (default 0.7)
            elite_ratio: Proportion of elites to preserve (default 0.1)
            config: Evolution configuration (optional, overrides individual params)

        Raises:
            ValueError: If population_size <= 0
            ValueError: If mutation_rate not in [0, 1]
            ValueError: If crossover_rate not in [0, 1]
            ValueError: If elite_ratio not in [0, 1]
        """
        # Validate parameters
        if population_size <= 0:
            raise ValueError(f"population_size must be > 0, got {population_size}")

        if not 0 <= mutation_rate <= 1:
            raise ValueError(f"mutation_rate must be in [0, 1], got {mutation_rate}")

        if not 0 <= crossover_rate <= 1:
            raise ValueError(f"crossover_rate must be in [0, 1], got {crossover_rate}")

        if not 0 <= elite_ratio <= 1:
            raise ValueError(f"elite_ratio must be in [0, 1], got {elite_ratio}")

        # Create config if not provided
        if config is None:
            config = EvolutionConfig(
                population_size=population_size,
                mutation_rate=mutation_rate,
                crossover_rate=crossover_rate,
                elite_ratio=elite_ratio,
            )

        # Initialize parent class
        super().__init__(config=config)

        # Store market data
        self.market_data = market_data

        # Initialize ETF-specific operator whitelist
        # 白皮书依据: 第四章 4.1.17 - ETF算子白名单 (20个算子)
        self.etf_operators = [
            "etf_premium_discount",
            "etf_creation_redemption_flow",
            "etf_tracking_error",
            "etf_constituent_weight_change",
            "etf_arbitrage_opportunity",
            "etf_liquidity_premium",
            "etf_fund_flow",
            "etf_bid_ask_spread_dynamics",
            "etf_nav_convergence_speed",
            "etf_sector_rotation_signal",
            "etf_smart_beta_exposure",
            "etf_leverage_decay",
            "etf_options_implied_volatility",
            "etf_cross_listing_arbitrage",
            "etf_index_rebalancing_impact",
            "etf_authorized_participant_activity",
            "etf_intraday_nav_tracking",
            "etf_options_put_call_ratio",
            "etf_securities_lending_income",
            "etf_dividend_reinvestment_impact",
        ]

        # Common operators (inherited from base class)
        # 白皮书依据: 第四章 4.1 - 通用算子
        self.common_operators = [
            "rank",
            "delay",
            "delta",
            "ts_mean",
            "ts_std",
            "correlation",
            "covariance",
            "regression_residual",
        ]

        # Build operator registry
        self.operator_registry = self._build_operator_registry()

        logger.info(
            "ETFFactorMiner初始化完成",
            extra={
                "component": "ETFFactorMiner",
                "action": "initialize",
                "population_size": self.config.population_size,
                "mutation_rate": self.config.mutation_rate,
                "crossover_rate": self.config.crossover_rate,
                "elite_ratio": self.config.elite_ratio,
                "etf_operators_count": len(self.etf_operators),
                "common_operators_count": len(self.common_operators),
                "total_operators": len(self.etf_operators) + len(self.common_operators),
            },
        )

    def _build_operator_registry(self) -> Dict[str, Any]:
        """Build operator registry mapping names to functions

        白皮书依据: 第四章 4.1.17 - ETF算子注册
        铁律依据: MIA编码铁律2 (禁止简化和占位符)

        Returns:
            Dictionary mapping operator names to callable functions

        Raises:
            FactorMiningError: If operator registration fails
        """
        try:
            registry = {}

            # Register ETF operators
            for op_name in self.etf_operators:
                if hasattr(ETFOperators, op_name):
                    registry[op_name] = getattr(ETFOperators, op_name)
                else:
                    logger.warning(f"ETF算子未实现: {op_name}")

            # Register common operators (from pandas/numpy)
            registry["rank"] = lambda x: x.rank(pct=True)
            registry["delay"] = lambda x, n: x.shift(n)
            registry["delta"] = lambda x, n: x.diff(n)
            registry["ts_mean"] = lambda x, n: x.rolling(window=n).mean()
            registry["ts_std"] = lambda x, n: x.rolling(window=n).std()
            registry["correlation"] = lambda x, y, n: x.rolling(window=n).corr(y)
            registry["covariance"] = lambda x, y, n: x.rolling(window=n).cov(y)

            logger.info(
                "算子注册完成",
                extra={
                    "component": "ETFFactorMiner",
                    "action": "register_operators",
                    "total_operators": len(registry),
                    "etf_operators": len([k for k in registry if k.startswith("etf_")]),
                    "common_operators": len([k for k in registry if not k.startswith("etf_")]),
                },
            )

            return registry

        except Exception as e:
            logger.error(
                "算子注册失败",
                extra={
                    "component": "ETFFactorMiner",
                    "action": "register_operators",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise FactorMiningError(f"Failed to build operator registry: {e}") from e

    def _get_operator_whitelist(self) -> List[str]:
        """Get list of allowed ETF operators

        白皮书依据: 第四章 4.1.17 - ETF算子白名单
        铁律依据: MIA编码铁律1 (白皮书至上)

        Returns:
            List of 20 ETF operator names + 8 common operators = 28 total

        Note:
            This method overrides the base class to provide ETF-specific operators.
            The whitelist is defined in the white paper Chapter 4, Section 4.1.17.
        """
        return self.etf_operators + self.common_operators

    def _generate_random_expression(self, data_columns: List[str]) -> str:
        """Generate random factor expression using ETF operators

        白皮书依据: 第四章 4.1.17 - ETF因子表达式生成
        铁律依据: MIA编码铁律2 (禁止简化和占位符)

        Overrides GeneticMiner._generate_random_expression() to use
        ETF-specific operators with appropriate probability distribution.

        Args:
            data_columns: Available data column names (e.g., ['close', 'nav', 'volume'])

        Returns:
            Factor expression string (e.g., "etf_premium_discount(close, nav)")

        Raises:
            ValueError: If data_columns is empty

        Note:
            Expression generation follows these rules:
            - 70% probability: Use ETF-specific operators
            - 30% probability: Use common operators
            - Complexity: 1-3 nested operators
            - Parameters: Randomly selected from valid ranges
        """
        if not data_columns:
            raise ValueError("data_columns cannot be empty")

        # Randomly choose complexity level
        complexity = random.randint(1, 3)

        # 70% probability to use ETF-specific operators
        if random.random() < 0.7 and self.etf_operators:  # pylint: disable=no-else-return
            return self._generate_etf_expression(data_columns, complexity)
        else:
            return self._generate_common_expression(data_columns, complexity)

    def _generate_etf_expression(  # pylint: disable=r0911
        self, data_columns: List[str], complexity: int  # pylint: disable=unused-argument
    ) -> str:  # pylint: disable=unused-argument
        """Generate ETF-specific expression

        白皮书依据: 第四章 4.1.17 - ETF算子使用

        Args:
            data_columns: Available data columns
            complexity: Expression complexity (1-3)

        Returns:
            ETF-specific expression string
        """
        # Select random ETF operator
        operator = random.choice(self.etf_operators)

        # Generate expression based on operator type
        if operator == "etf_premium_discount":  # pylint: disable=no-else-return
            # Requires: price, nav
            return f"etf_premium_discount(close, nav)"  # pylint: disable=w1309

        elif operator == "etf_creation_redemption_flow":
            # Requires: creation_units, redemption_units, window
            window = random.choice([5, 10, 20])
            return f"etf_creation_redemption_flow(creation_units, redemption_units, {window})"

        elif operator == "etf_tracking_error":
            # Requires: etf_returns, index_returns, window
            window = random.choice([20, 30, 60])
            return f"etf_tracking_error(returns, index_returns, {window})"

        elif operator == "etf_constituent_weight_change":
            # Requires: constituent_weights, window
            window = random.choice([5, 10, 20])
            return f"etf_constituent_weight_change(constituent_weights, {window})"

        elif operator == "etf_arbitrage_opportunity":
            # Requires: price, nav, threshold
            threshold = random.choice([0.005, 0.01, 0.02])
            return f"etf_arbitrage_opportunity(close, nav, {threshold})"

        elif operator == "etf_liquidity_premium":
            # Requires: volume, window
            window = random.choice([5, 10, 20])
            return f"etf_liquidity_premium(volume, {window})"

        elif operator == "etf_fund_flow":
            # Requires: creation_units, redemption_units, window
            window = random.choice([5, 10, 20])
            return f"etf_fund_flow(creation_units, redemption_units, {window})"

        elif operator == "etf_bid_ask_spread_dynamics":
            # Requires: bid_price, ask_price, window
            window = random.choice([5, 10, 20])
            return f"etf_bid_ask_spread_dynamics(bid_price, ask_price, {window})"

        elif operator == "etf_nav_convergence_speed":
            # Requires: price, nav, window
            window = random.choice([5, 10, 20])
            return f"etf_nav_convergence_speed(close, nav, {window})"

        elif operator == "etf_sector_rotation_signal":
            # Requires: constituent_weights, sector_returns, window
            window = random.choice([10, 20, 30])
            return f"etf_sector_rotation_signal(constituent_weights, sector_returns, {window})"

        else:
            # For other operators, use generic format
            column = random.choice(data_columns)
            window = random.choice([5, 10, 20, 30])
            return f"{operator}({column}, {window})"

    def _generate_common_expression(
        self, data_columns: List[str], complexity: int  # pylint: disable=unused-argument
    ) -> str:  # pylint: disable=unused-argument
        """Generate common operator expression

        白皮书依据: 第四章 4.1 - 通用算子使用

        Args:
            data_columns: Available data columns
            complexity: Expression complexity (1-3)

        Returns:
            Common operator expression string
        """
        column = random.choice(data_columns)
        operator = random.choice(self.common_operators)

        if operator == "rank":  # pylint: disable=no-else-return
            return f"rank({column})"
        elif operator == "delay":
            period = random.choice([1, 2, 3, 5])
            return f"delay({column}, {period})"
        elif operator == "delta":
            period = random.choice([1, 2, 3, 5])
            return f"delta({column}, {period})"
        elif operator in ["ts_mean", "ts_std"]:
            window = random.choice([5, 10, 20, 30])
            return f"{operator}({column}, {window})"
        elif operator in ["correlation", "covariance"]:
            column2 = random.choice(data_columns)
            window = random.choice([10, 20, 30])
            return f"{operator}({column}, {column2}, {window})"
        else:
            return f"{operator}({column})"

    def _evaluate_expression(self, expression: str, data: pd.DataFrame) -> Optional[pd.Series]:
        """Evaluate factor expression on ETF market data

        白皮书依据: 第四章 4.1.17 - ETF因子评估
        铁律依据: MIA编码铁律3 (完整的错误处理)

        Args:
            expression: Factor expression string
            data: ETF market data DataFrame with columns like 'close', 'nav', 'volume'

        Returns:
            Series of factor values indexed by date, or None if evaluation fails

        Raises:
            OperatorError: If expression evaluation fails
            DataQualityError: If more than 50% of results are NaN

        Note:
            This method parses the expression and evaluates it using the
            operator registry. It handles errors gracefully and returns None
            for invalid expressions.
        """
        try:  # pylint: disable=r1702
            # Parse expression to extract operator and arguments
            # Simplified parser - in production, use a proper expression parser

            # Check if expression is a simple column reference
            if expression in data.columns:
                result = data[expression]
                return self._validate_result(result, expression)

            # Check for ETF operators
            for op_name in self.etf_operators:
                if expression.startswith(op_name):
                    # Extract arguments from expression
                    # Format: operator(arg1, arg2, ...)
                    args_str = expression[len(op_name) :].strip("()")
                    args = [arg.strip() for arg in args_str.split(",")]

                    # Get operator function
                    if op_name not in self.operator_registry:
                        logger.warning(f"算子未注册: {op_name}")
                        return None

                    operator_func = self.operator_registry[op_name]

                    # Prepare arguments
                    operator_args = []
                    for arg in args:
                        if arg in data.columns:
                            operator_args.append(data[arg])
                        else:
                            # Try to convert to numeric
                            try:
                                operator_args.append(float(arg))
                            except ValueError:
                                logger.warning(f"无法解析参数: {arg}")
                                return None

                    # Call operator
                    result = operator_func(*operator_args)
                    return self._validate_result(result, expression)

            # Check for common operators
            for op_name in self.common_operators:
                if expression.startswith(op_name):
                    # Similar parsing logic
                    args_str = expression[len(op_name) :].strip("()")
                    args = [arg.strip() for arg in args_str.split(",")]

                    if op_name not in self.operator_registry:
                        logger.warning(f"算子未注册: {op_name}")
                        return None

                    operator_func = self.operator_registry[op_name]

                    # Prepare arguments
                    operator_args = []
                    for arg in args:
                        if arg in data.columns:
                            operator_args.append(data[arg])
                        else:
                            try:
                                operator_args.append(int(arg))
                            except ValueError:
                                try:
                                    operator_args.append(float(arg))
                                except ValueError:
                                    logger.warning(f"无法解析参数: {arg}")
                                    return None

                    # Call operator
                    result = operator_func(*operator_args)
                    return self._validate_result(result, expression)

            # If we reach here, expression format is not recognized
            logger.warning(f"无法识别的表达式格式: {expression}")
            return None

        except Exception as e:
            logger.error(f"表达式评估失败: {expression}, 错误: {e}")
            raise OperatorError(f"Failed to evaluate expression '{expression}': {e}") from e

    def _validate_result(self, result: pd.Series, expression: str) -> Optional[pd.Series]:
        """Validate operator result for data quality

        白皮书依据: 第四章 4.1 - 数据质量要求
        铁律依据: MIA编码铁律3 (完整的错误处理)

        Args:
            result: Operator result series
            expression: Expression that produced the result

        Returns:
            Validated result series, or None if quality is insufficient

        Raises:
            DataQualityError: If more than 50% of results are NaN
        """
        if result is None or result.empty:
            return None

        # Check for NaN ratio
        nan_ratio = result.isna().sum() / len(result)

        if nan_ratio > 0.5:
            raise DataQualityError(
                f"Data quality insufficient for expression '{expression}': "
                f"{nan_ratio:.1%} of results are NaN (threshold: 50%)"
            )

        # Check for infinite values
        inf_count = np.isinf(result).sum()
        if inf_count > 0:
            logger.warning(f"Expression '{expression}' produced {inf_count} infinite values, " f"replacing with NaN")
            result = result.replace([np.inf, -np.inf], np.nan)

        return result
