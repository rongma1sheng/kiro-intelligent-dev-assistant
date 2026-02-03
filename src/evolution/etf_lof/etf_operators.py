# pylint: disable=too-many-lines
"""ETF-specific operators for factor mining

白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
版本: v1.6.1

This module implements 20 ETF-specific operators for factor mining:
- 5 arbitrage and pricing operators
- 4 fund flow and trading behavior operators
- 4 tracking and constituent operators
- 2 style and factor operators
- 3 derivatives and special product operators
- 2 income and cost operators
"""

from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

from .exceptions import DataQualityError, OperatorError


class ETFOperators:
    """ETF operator registry and calculation engine

    白皮书依据: 第四章 4.1.17 - ETF因子挖掘器

    This class provides:
    1. Operator registry mechanism for all 20 ETF operators
    2. Operator validation and error handling
    3. Data quality checks
    4. Operator calculation with proper logging

    Attributes:
        operators: Dictionary mapping operator names to calculation functions
        operator_metadata: Dictionary mapping operator names to metadata
    """

    def __init__(self):
        """Initialize ETF operators registry

        白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
        """
        self.operators: Dict[str, Callable] = {}
        self.operator_metadata: Dict[str, Dict[str, Any]] = {}

        # Register all operators
        self._register_all_operators()

        logger.info(f"ETFOperators initialized with {len(self.operators)} operators")

    def _register_all_operators(self) -> None:
        """Register all 20 ETF operators

        白皮书依据: 第四章 4.1.17 - ETF因子挖掘器
        """
        # Category 1: Arbitrage and Pricing (5 operators)
        self._register_operator(
            name="etf_premium_discount",
            func=self.etf_premium_discount,
            category="arbitrage_pricing",
            description="ETF premium/discount rate",
            formula="(market_price - NAV) / NAV",
        )

        self._register_operator(
            name="etf_arbitrage_opportunity",
            func=self.etf_arbitrage_opportunity,
            category="arbitrage_pricing",
            description="ETF arbitrage opportunity",
            formula="abs(premium_discount) - transaction_cost > threshold",
        )

        self._register_operator(
            name="etf_nav_convergence_speed",
            func=self.etf_nav_convergence_speed,
            category="arbitrage_pricing",
            description="ETF NAV convergence speed",
            formula="rolling_regression(premium_discount, time).slope",
        )

        self._register_operator(
            name="etf_cross_listing_arbitrage",
            func=self.etf_cross_listing_arbitrage,
            category="arbitrage_pricing",
            description="ETF cross-market arbitrage",
            formula="(price_market_A - price_market_B) / price_market_B",
        )

        self._register_operator(
            name="etf_liquidity_premium",
            func=self.etf_liquidity_premium,
            category="arbitrage_pricing",
            description="ETF liquidity premium",
            formula="correlation(bid_ask_spread, premium_discount)",
        )

        # Category 2: Fund Flow and Trading Behavior (4 operators)
        self._register_operator(
            name="etf_creation_redemption_flow",
            func=self.etf_creation_redemption_flow,
            category="fund_flow",
            description="ETF creation/redemption flow",
            formula="rolling_sum(creation_units - redemption_units, window)",
        )

        self._register_operator(
            name="etf_fund_flow",
            func=self.etf_fund_flow,
            category="fund_flow",
            description="ETF fund flow",
            formula="(AUM_today - AUM_yesterday) / AUM_yesterday",
        )

        self._register_operator(
            name="etf_bid_ask_spread_dynamics",
            func=self.etf_bid_ask_spread_dynamics,
            category="fund_flow",
            description="ETF bid-ask spread dynamics",
            formula="rolling_std(bid_ask_spread, window) / rolling_mean(bid_ask_spread, window)",
        )

        self._register_operator(
            name="etf_authorized_participant_activity",
            func=self.etf_authorized_participant_activity,
            category="fund_flow",
            description="ETF authorized participant activity (NEW)",
            formula="count(creation_redemption_transactions) / trading_days",
        )

        # Category 3: Tracking and Constituent (4 operators)
        self._register_operator(
            name="etf_tracking_error",
            func=self.etf_tracking_error,
            category="tracking",
            description="ETF tracking error",
            formula="rolling_std(etf_returns - index_returns, window)",
        )

        self._register_operator(
            name="etf_constituent_weight_change",
            func=self.etf_constituent_weight_change,
            category="tracking",
            description="Constituent weight change",
            formula="sum(abs(weight_today - weight_yesterday))",
        )

        self._register_operator(
            name="etf_index_rebalancing_impact",
            func=self.etf_index_rebalancing_impact,
            category="tracking",
            description="ETF index rebalancing impact",
            formula="predict_price_impact(weight_changes, liquidity)",
        )

        self._register_operator(
            name="etf_intraday_nav_tracking",
            func=self.etf_intraday_nav_tracking,
            category="tracking",
            description="ETF intraday NAV tracking (NEW)",
            formula="correlation(intraday_price, intraday_inav)",
        )

        # Category 4: Style and Factor (2 operators)
        self._register_operator(
            name="etf_smart_beta_exposure",
            func=self.etf_smart_beta_exposure,
            category="style_factor",
            description="ETF Smart Beta exposure",
            formula="regression(etf_returns, [value, momentum, quality, size]).coefficients",
        )

        self._register_operator(
            name="etf_sector_rotation_signal",
            func=self.etf_sector_rotation_signal,
            category="style_factor",
            description="ETF sector rotation signal",
            formula="correlation(sector_etf_flows, sector_returns)",
        )

        # Category 5: Derivatives and Special Products (3 operators)
        self._register_operator(
            name="etf_leverage_decay",
            func=self.etf_leverage_decay,
            category="derivatives",
            description="Leveraged ETF decay",
            formula="cumulative_return(leveraged_etf) - leverage_ratio * cumulative_return(index)",
        )

        self._register_operator(
            name="etf_options_implied_volatility",
            func=self.etf_options_implied_volatility,
            category="derivatives",
            description="ETF options implied volatility",
            formula="black_scholes_implied_vol(option_price, spot, strike, time, rate)",
        )

        self._register_operator(
            name="etf_options_put_call_ratio",
            func=self.etf_options_put_call_ratio,
            category="derivatives",
            description="ETF options put/call ratio (NEW)",
            formula="put_volume / call_volume",
        )

        # Category 6: Income and Cost (2 operators)
        self._register_operator(
            name="etf_securities_lending_income",
            func=self.etf_securities_lending_income,
            category="income_cost",
            description="ETF securities lending income (NEW)",
            formula="lending_income / total_assets",
        )

        self._register_operator(
            name="etf_dividend_reinvestment_impact",
            func=self.etf_dividend_reinvestment_impact,
            category="income_cost",
            description="ETF dividend reinvestment impact (NEW)",
            formula="(total_return - price_return) / price_return",
        )

    def _register_operator(  # pylint: disable=too-many-positional-arguments
        self, name: str, func: Callable, category: str, description: str, formula: str
    ) -> None:  # pylint: disable=too-many-positional-arguments
        """Register an operator with metadata

        Args:
            name: Operator name
            func: Operator calculation function
            category: Operator category
            description: Operator description
            formula: Mathematical formula
        """
        self.operators[name] = func
        self.operator_metadata[name] = {"category": category, "description": description, "formula": formula}

        logger.debug(f"Registered operator: {name} ({category})")

    def get_operator(self, name: str) -> Optional[Callable]:
        """Get operator function by name

        Args:
            name: Operator name

        Returns:
            Operator function or None if not found
        """
        return self.operators.get(name)

    def get_operator_names(self) -> list[str]:
        """Get list of all operator names

        Returns:
            List of operator names
        """
        return list(self.operators.keys())

    def get_operators_by_category(self, category: str) -> Dict[str, Callable]:
        """Get all operators in a category

        Args:
            category: Category name

        Returns:
            Dictionary of operator names to functions
        """
        return {
            name: func for name, func in self.operators.items() if self.operator_metadata[name]["category"] == category
        }

    def validate_operator_input(self, data: pd.DataFrame, required_columns: list[str]) -> None:
        """Validate operator input data

        白皮书依据: 第四章 4.1 - Data Quality Requirements

        Args:
            data: Input data
            required_columns: Required column names

        Raises:
            OperatorError: If validation fails
        """
        if data.empty:
            raise OperatorError("Input data is empty")

        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise OperatorError(f"Missing required columns: {missing_columns}")

        # Check for excessive NaN values (>50% threshold)
        for col in required_columns:
            nan_ratio = data[col].isna().sum() / len(data)
            if nan_ratio > 0.5:
                raise DataQualityError(f"Column {col} has {nan_ratio:.1%} NaN values (threshold: 50%)")

    # ========================================================================
    # Category 1: Arbitrage and Pricing Operators (5 operators)
    # ========================================================================

    def etf_premium_discount(self, data: pd.DataFrame, price_col: str = "price", nav_col: str = "nav") -> pd.Series:
        """Calculate ETF premium/discount rate

        白皮书依据: 第四章 4.1.17 - etf_premium_discount
        公式: (market_price - NAV) / NAV

        Args:
            data: DataFrame with price and NAV columns
            price_col: Column name for market price
            nav_col: Column name for NAV

        Returns:
            Premium/discount rate series

        Raises:
            OperatorError: If calculation fails
            DataQualityError: If data quality is insufficient
        """
        try:
            self.validate_operator_input(data, [price_col, nav_col])

            price = data[price_col]
            nav = data[nav_col]

            # Calculate premium/discount
            premium_discount = (price - nav) / nav

            logger.debug(f"Calculated etf_premium_discount: mean={premium_discount.mean():.4f}")

            return premium_discount

        except (OperatorError, DataQualityError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            logger.error(f"etf_premium_discount calculation failed: {e}")
            raise OperatorError(f"etf_premium_discount failed: {e}") from e

    def etf_arbitrage_opportunity(
        self, data: pd.DataFrame, transaction_cost: float = 0.001, threshold: float = 0.0005
    ) -> pd.Series:
        """Calculate ETF arbitrage opportunity

        白皮书依据: 第四章 4.1.17 - etf_arbitrage_opportunity
        公式: abs(premium_discount) - transaction_cost > threshold

        Args:
            data: DataFrame with price and NAV columns
            transaction_cost: Transaction cost rate (default 0.1%)
            threshold: Minimum profit threshold (default 0.05%)

        Returns:
            Arbitrage opportunity indicator (1 if opportunity exists, 0 otherwise)

        Raises:
            OperatorError: If calculation fails
        """
        try:
            # Calculate premium/discount first
            premium_discount = self.etf_premium_discount(data)

            # Calculate arbitrage opportunity
            arbitrage_profit = premium_discount.abs() - transaction_cost
            arbitrage_opportunity = (arbitrage_profit > threshold).astype(int)

            logger.debug(f"Calculated etf_arbitrage_opportunity: opportunities={arbitrage_opportunity.sum()}")

            return arbitrage_opportunity

        except Exception as e:
            logger.error(f"etf_arbitrage_opportunity calculation failed: {e}")
            raise OperatorError(f"etf_arbitrage_opportunity failed: {e}") from e

    def etf_nav_convergence_speed(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate ETF NAV convergence speed

        白皮书依据: 第四章 4.1.17 - etf_nav_convergence_speed
        公式: rolling_regression(premium_discount, time).slope

        Args:
            data: DataFrame with price and NAV columns
            window: Rolling window size (default 20 days)

        Returns:
            Convergence speed series (negative means converging)

        Raises:
            OperatorError: If calculation fails
        """
        try:
            # Calculate premium/discount first
            premium_discount = self.etf_premium_discount(data)

            # Calculate rolling regression slope
            def rolling_slope(series):
                if len(series) < 2:
                    return np.nan
                x = np.arange(len(series))
                y = series.values
                # Remove NaN values
                mask = ~np.isnan(y)
                if mask.sum() < 2:
                    return np.nan
                x_clean = x[mask]
                y_clean = y[mask]
                # Linear regression
                slope = np.polyfit(x_clean, y_clean, 1)[0]
                return slope

            convergence_speed = premium_discount.rolling(window=window).apply(rolling_slope, raw=False)

            logger.debug(f"Calculated etf_nav_convergence_speed: mean={convergence_speed.mean():.6f}")

            return convergence_speed

        except Exception as e:
            logger.error(f"etf_nav_convergence_speed calculation failed: {e}")
            raise OperatorError(f"etf_nav_convergence_speed failed: {e}") from e

    def etf_cross_listing_arbitrage(
        self, data: pd.DataFrame, price_a_col: str = "price_market_a", price_b_col: str = "price_market_b"
    ) -> pd.Series:
        """Calculate ETF cross-market arbitrage opportunity

        白皮书依据: 第四章 4.1.17 - etf_cross_listing_arbitrage
        公式: (price_market_A - price_market_B) / price_market_B

        Args:
            data: DataFrame with prices from two markets
            price_a_col: Column name for market A price
            price_b_col: Column name for market B price

        Returns:
            Cross-market price spread series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [price_a_col, price_b_col])

            price_a = data[price_a_col]
            price_b = data[price_b_col]

            # Calculate cross-market spread
            cross_spread = (price_a - price_b) / price_b

            logger.debug(f"Calculated etf_cross_listing_arbitrage: mean={cross_spread.mean():.4f}")

            return cross_spread

        except Exception as e:
            logger.error(f"etf_cross_listing_arbitrage calculation failed: {e}")
            raise OperatorError(f"etf_cross_listing_arbitrage failed: {e}") from e

    def etf_liquidity_premium(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate ETF liquidity premium

        白皮书依据: 第四章 4.1.17 - etf_liquidity_premium
        公式: correlation(bid_ask_spread, premium_discount)

        Args:
            data: DataFrame with bid, ask, price, and NAV columns
            window: Rolling window size (default 20 days)

        Returns:
            Liquidity premium series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["bid_price", "ask_price", "price", "nav"])

            # Calculate bid-ask spread
            bid_ask_spread = (data["ask_price"] - data["bid_price"]) / data["price"]

            # Calculate premium/discount
            premium_discount = self.etf_premium_discount(data)

            # Calculate rolling correlation
            liquidity_premium = bid_ask_spread.rolling(window=window).corr(premium_discount)

            logger.debug(f"Calculated etf_liquidity_premium: mean={liquidity_premium.mean():.4f}")

            return liquidity_premium

        except Exception as e:
            logger.error(f"etf_liquidity_premium calculation failed: {e}")
            raise OperatorError(f"etf_liquidity_premium failed: {e}") from e

    # ========================================================================
    # Category 2: Fund Flow and Trading Behavior Operators (4 operators)
    # ========================================================================

    def etf_creation_redemption_flow(self, data: pd.DataFrame, window: int = 5) -> pd.Series:
        """Calculate ETF creation/redemption flow

        白皮书依据: 第四章 4.1.17 - etf_creation_redemption_flow
        公式: rolling_sum(creation_units - redemption_units, window)

        Args:
            data: DataFrame with creation_units and redemption_units columns
            window: Rolling window size (default 5 days)

        Returns:
            Net creation/redemption flow series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["creation_units", "redemption_units"])

            net_flow = data["creation_units"] - data["redemption_units"]
            rolling_flow = net_flow.rolling(window=window).sum()

            logger.debug(f"Calculated etf_creation_redemption_flow: mean={rolling_flow.mean():.2f}")

            return rolling_flow

        except Exception as e:
            logger.error(f"etf_creation_redemption_flow calculation failed: {e}")
            raise OperatorError(f"etf_creation_redemption_flow failed: {e}") from e

    def etf_fund_flow(self, data: pd.DataFrame, aum_col: str = "aum") -> pd.Series:
        """Calculate ETF fund flow

        白皮书依据: 第四章 4.1.17 - etf_fund_flow
        公式: (AUM_today - AUM_yesterday) / AUM_yesterday

        Args:
            data: DataFrame with AUM column
            aum_col: Column name for AUM

        Returns:
            Fund flow rate series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [aum_col])

            aum = data[aum_col]
            fund_flow = aum.pct_change()

            logger.debug(f"Calculated etf_fund_flow: mean={fund_flow.mean():.4f}")

            return fund_flow

        except Exception as e:
            logger.error(f"etf_fund_flow calculation failed: {e}")
            raise OperatorError(f"etf_fund_flow failed: {e}") from e

    def etf_bid_ask_spread_dynamics(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate ETF bid-ask spread dynamics

        白皮书依据: 第四章 4.1.17 - etf_bid_ask_spread_dynamics
        公式: rolling_std(bid_ask_spread, window) / rolling_mean(bid_ask_spread, window)

        Args:
            data: DataFrame with bid_price, ask_price, and price columns
            window: Rolling window size (default 20 days)

        Returns:
            Spread dynamics series (coefficient of variation)

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["bid_price", "ask_price", "price"])

            # Calculate bid-ask spread
            bid_ask_spread = (data["ask_price"] - data["bid_price"]) / data["price"]

            # Calculate coefficient of variation
            spread_std = bid_ask_spread.rolling(window=window).std()
            spread_mean = bid_ask_spread.rolling(window=window).mean()
            spread_dynamics = spread_std / spread_mean

            logger.debug(f"Calculated etf_bid_ask_spread_dynamics: mean={spread_dynamics.mean():.4f}")

            return spread_dynamics

        except Exception as e:
            logger.error(f"etf_bid_ask_spread_dynamics calculation failed: {e}")
            raise OperatorError(f"etf_bid_ask_spread_dynamics failed: {e}") from e

    def etf_authorized_participant_activity(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate ETF authorized participant activity (NEW)

        白皮书依据: 第四章 4.1.17 - etf_authorized_participant_activity
        公式: count(creation_redemption_transactions) / trading_days

        Args:
            data: DataFrame with creation_units and redemption_units columns
            window: Rolling window size (default 20 days)

        Returns:
            AP activity rate series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["creation_units", "redemption_units"])

            # Count days with creation or redemption activity
            has_activity = ((data["creation_units"] > 0) | (data["redemption_units"] > 0)).astype(int)
            activity_rate = has_activity.rolling(window=window).mean()

            logger.debug(f"Calculated etf_authorized_participant_activity: mean={activity_rate.mean():.4f}")

            return activity_rate

        except Exception as e:
            logger.error(f"etf_authorized_participant_activity calculation failed: {e}")
            raise OperatorError(f"etf_authorized_participant_activity failed: {e}") from e

    # ========================================================================
    # Category 3: Tracking and Constituent Operators (4 operators)
    # ========================================================================

    def etf_tracking_error(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate ETF tracking error

        白皮书依据: 第四章 4.1.17 - etf_tracking_error
        公式: rolling_std(etf_returns - index_returns, window)

        Args:
            data: DataFrame with price and index_price columns
            window: Rolling window size (default 20 days)

        Returns:
            Tracking error series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["price", "index_price"])

            # Calculate returns
            etf_returns = data["price"].pct_change()
            index_returns = data["index_price"].pct_change()

            # Calculate tracking difference
            tracking_diff = etf_returns - index_returns

            # Calculate rolling standard deviation
            tracking_error = tracking_diff.rolling(window=window).std()

            logger.debug(f"Calculated etf_tracking_error: mean={tracking_error.mean():.6f}")

            return tracking_error

        except Exception as e:
            logger.error(f"etf_tracking_error calculation failed: {e}")
            raise OperatorError(f"etf_tracking_error failed: {e}") from e

    def etf_constituent_weight_change(self, data: pd.DataFrame, weights_col: str = "constituent_weights") -> pd.Series:
        """Calculate constituent weight change

        白皮书依据: 第四章 4.1.17 - etf_constituent_weight_change
        公式: sum(abs(weight_today - weight_yesterday))

        Args:
            data: DataFrame with constituent_weights column (dict of weights)
            weights_col: Column name for constituent weights

        Returns:
            Total weight change series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [weights_col])

            # Calculate weight changes
            def calc_weight_change(row_idx):
                if row_idx == 0:
                    return np.nan

                weights_today = data[weights_col].iloc[row_idx]
                weights_yesterday = data[weights_col].iloc[row_idx - 1]

                if not isinstance(weights_today, dict) or not isinstance(weights_yesterday, dict):
                    return np.nan

                # Get all symbols
                all_symbols = set(weights_today.keys()) | set(weights_yesterday.keys())

                # Calculate total absolute change
                total_change = sum(
                    abs(weights_today.get(symbol, 0) - weights_yesterday.get(symbol, 0)) for symbol in all_symbols
                )

                return total_change

            weight_changes = pd.Series([calc_weight_change(i) for i in range(len(data))], index=data.index)

            logger.debug(f"Calculated etf_constituent_weight_change: mean={weight_changes.mean():.6f}")

            return weight_changes

        except Exception as e:
            logger.error(f"etf_constituent_weight_change calculation failed: {e}")
            raise OperatorError(f"etf_constituent_weight_change failed: {e}") from e

    def etf_index_rebalancing_impact(
        self, data: pd.DataFrame, weights_col: str = "constituent_weights", volume_col: str = "volume"
    ) -> pd.Series:
        """Calculate ETF index rebalancing impact

        白皮书依据: 第四章 4.1.17 - etf_index_rebalancing_impact
        公式: predict_price_impact(weight_changes, liquidity)

        Args:
            data: DataFrame with constituent_weights and volume columns
            weights_col: Column name for constituent weights
            volume_col: Column name for volume

        Returns:
            Rebalancing impact series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [weights_col, volume_col])

            # Calculate weight changes
            weight_changes = self.etf_constituent_weight_change(data, weights_col)

            # Normalize by liquidity (volume)
            volume = data[volume_col]
            rebalancing_impact = weight_changes / (volume + 1e-8)  # Avoid division by zero

            logger.debug(f"Calculated etf_index_rebalancing_impact: mean={rebalancing_impact.mean():.6f}")

            return rebalancing_impact

        except Exception as e:
            logger.error(f"etf_index_rebalancing_impact calculation failed: {e}")
            raise OperatorError(f"etf_index_rebalancing_impact failed: {e}") from e

    def etf_intraday_nav_tracking(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """Calculate ETF intraday NAV tracking (NEW)

        白皮书依据: 第四章 4.1.17 - etf_intraday_nav_tracking
        公式: correlation(intraday_price, intraday_inav)

        Args:
            data: DataFrame with price and nav columns
            window: Rolling window size (default 20 days)

        Returns:
            Intraday tracking quality series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["price", "nav"])

            # Calculate rolling correlation between price and NAV
            price = data["price"]
            nav = data["nav"]

            intraday_tracking = price.rolling(window=window).corr(nav)

            logger.debug(f"Calculated etf_intraday_nav_tracking: mean={intraday_tracking.mean():.4f}")

            return intraday_tracking

        except Exception as e:
            logger.error(f"etf_intraday_nav_tracking calculation failed: {e}")
            raise OperatorError(f"etf_intraday_nav_tracking failed: {e}") from e

    # ========================================================================
    # Category 4: Style and Factor Operators (2 operators)
    # ========================================================================

    def etf_smart_beta_exposure(self, data: pd.DataFrame, factor_returns_cols: list[str] = None) -> pd.Series:
        """Calculate ETF Smart Beta exposure

        白皮书依据: 第四章 4.1.17 - etf_smart_beta_exposure
        公式: regression(etf_returns, [value, momentum, quality, size]).coefficients

        Args:
            data: DataFrame with price and factor return columns
            factor_returns_cols: List of factor return column names

        Returns:
            Composite factor exposure series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            if factor_returns_cols is None:
                factor_returns_cols = ["value_returns", "momentum_returns", "quality_returns", "size_returns"]

            required_cols = ["price"] + factor_returns_cols
            self.validate_operator_input(data, required_cols)

            # Calculate ETF returns
            etf_returns = data["price"].pct_change()

            # Simple average of factor exposures (correlation-based)
            exposures = []
            for factor_col in factor_returns_cols:
                factor_returns = data[factor_col]
                exposure = etf_returns.rolling(window=60).corr(factor_returns)
                exposures.append(exposure)

            # Average exposure across all factors
            smart_beta_exposure = pd.concat(exposures, axis=1).mean(axis=1)

            logger.debug(f"Calculated etf_smart_beta_exposure: mean={smart_beta_exposure.mean():.4f}")

            return smart_beta_exposure

        except Exception as e:
            logger.error(f"etf_smart_beta_exposure calculation failed: {e}")
            raise OperatorError(f"etf_smart_beta_exposure failed: {e}") from e

    def etf_sector_rotation_signal(
        self,
        data: pd.DataFrame,
        sector_flow_col: str = "sector_flow",
        sector_returns_col: str = "sector_returns",
        window: int = 20,
    ) -> pd.Series:
        """Calculate ETF sector rotation signal

        白皮书依据: 第四章 4.1.17 - etf_sector_rotation_signal
        公式: correlation(sector_etf_flows, sector_returns)

        Args:
            data: DataFrame with sector flow and returns columns
            sector_flow_col: Column name for sector flow
            sector_returns_col: Column name for sector returns
            window: Rolling window size (default 20 days)

        Returns:
            Sector rotation signal series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [sector_flow_col, sector_returns_col])

            sector_flow = data[sector_flow_col]
            sector_returns = data[sector_returns_col]

            # Calculate rolling correlation
            rotation_signal = sector_flow.rolling(window=window).corr(sector_returns)

            logger.debug(f"Calculated etf_sector_rotation_signal: mean={rotation_signal.mean():.4f}")

            return rotation_signal

        except Exception as e:
            logger.error(f"etf_sector_rotation_signal calculation failed: {e}")
            raise OperatorError(f"etf_sector_rotation_signal failed: {e}") from e

    # ========================================================================
    # Category 5: Derivatives and Special Products Operators (3 operators)
    # ========================================================================

    def etf_leverage_decay(self, data: pd.DataFrame, leverage_ratio: float = 2.0) -> pd.Series:
        """Calculate leveraged ETF decay

        白皮书依据: 第四章 4.1.17 - etf_leverage_decay
        公式: cumulative_return(leveraged_etf) - leverage_ratio * cumulative_return(index)

        Args:
            data: DataFrame with price and index_price columns
            leverage_ratio: Leverage ratio (default 2.0 for 2x ETF)

        Returns:
            Leverage decay series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["price", "index_price"])

            # Calculate cumulative returns
            etf_returns = data["price"].pct_change()
            index_returns = data["index_price"].pct_change()

            etf_cumulative = (1 + etf_returns).cumprod()
            index_cumulative = (1 + index_returns).cumprod()

            # Calculate decay
            expected_cumulative = index_cumulative**leverage_ratio
            leverage_decay = etf_cumulative - expected_cumulative

            logger.debug(f"Calculated etf_leverage_decay: mean={leverage_decay.mean():.4f}")

            return leverage_decay

        except Exception as e:
            logger.error(f"etf_leverage_decay calculation failed: {e}")
            raise OperatorError(f"etf_leverage_decay failed: {e}") from e

    def etf_options_implied_volatility(
        self, data: pd.DataFrame, option_price_col: str = "option_price", window: int = 20
    ) -> pd.Series:
        """Calculate ETF options implied volatility

        白皮书依据: 第四章 4.1.17 - etf_options_implied_volatility
        公式: black_scholes_implied_vol(option_price, spot, strike, time, rate)

        Note: This is a simplified implementation using historical volatility as proxy

        Args:
            data: DataFrame with price and option_price columns
            option_price_col: Column name for option price
            window: Rolling window size (default 20 days)

        Returns:
            Implied volatility series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, ["price", option_price_col])

            # Simplified: Use historical volatility as proxy for implied volatility
            returns = data["price"].pct_change()
            implied_vol = returns.rolling(window=window).std() * np.sqrt(252)

            logger.debug(f"Calculated etf_options_implied_volatility: mean={implied_vol.mean():.4f}")

            return implied_vol

        except Exception as e:
            logger.error(f"etf_options_implied_volatility calculation failed: {e}")
            raise OperatorError(f"etf_options_implied_volatility failed: {e}") from e

    def etf_options_put_call_ratio(
        self, data: pd.DataFrame, put_volume_col: str = "put_volume", call_volume_col: str = "call_volume"
    ) -> pd.Series:
        """Calculate ETF options put/call ratio (NEW)

        白皮书依据: 第四章 4.1.17 - etf_options_put_call_ratio
        公式: put_volume / call_volume

        Args:
            data: DataFrame with put_volume and call_volume columns
            put_volume_col: Column name for put option volume
            call_volume_col: Column name for call option volume

        Returns:
            Put/call ratio series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [put_volume_col, call_volume_col])

            put_volume = data[put_volume_col]
            call_volume = data[call_volume_col]

            # Calculate put/call ratio (avoid division by zero)
            put_call_ratio = put_volume / (call_volume + 1e-8)

            logger.debug(f"Calculated etf_options_put_call_ratio: mean={put_call_ratio.mean():.4f}")

            return put_call_ratio

        except Exception as e:
            logger.error(f"etf_options_put_call_ratio calculation failed: {e}")
            raise OperatorError(f"etf_options_put_call_ratio failed: {e}") from e

    # ========================================================================
    # Category 6: Income and Cost Operators (2 operators)
    # ========================================================================

    def etf_securities_lending_income(
        self, data: pd.DataFrame, lending_income_col: str = "lending_income", total_assets_col: str = "total_assets"
    ) -> pd.Series:
        """Calculate ETF securities lending income (NEW)

        白皮书依据: 第四章 4.1.17 - etf_securities_lending_income
        公式: lending_income / total_assets

        Args:
            data: DataFrame with lending_income and total_assets columns
            lending_income_col: Column name for lending income
            total_assets_col: Column name for total assets

        Returns:
            Securities lending income rate series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [lending_income_col, total_assets_col])

            lending_income = data[lending_income_col]
            total_assets = data[total_assets_col]

            # Calculate lending income rate
            lending_income_rate = lending_income / (total_assets + 1e-8)

            logger.debug(f"Calculated etf_securities_lending_income: mean={lending_income_rate.mean():.6f}")

            return lending_income_rate

        except Exception as e:
            logger.error(f"etf_securities_lending_income calculation failed: {e}")
            raise OperatorError(f"etf_securities_lending_income failed: {e}") from e

    def etf_dividend_reinvestment_impact(
        self, data: pd.DataFrame, total_return_col: str = "total_return", price_return_col: str = "price_return"
    ) -> pd.Series:
        """Calculate ETF dividend reinvestment impact (NEW)

        白皮书依据: 第四章 4.1.17 - etf_dividend_reinvestment_impact
        公式: (total_return - price_return) / price_return

        Args:
            data: DataFrame with total_return and price_return columns
            total_return_col: Column name for total return
            price_return_col: Column name for price return

        Returns:
            Dividend reinvestment impact series

        Raises:
            OperatorError: If calculation fails
        """
        try:
            self.validate_operator_input(data, [total_return_col, price_return_col])

            total_return = data[total_return_col]
            price_return = data[price_return_col]

            # Calculate dividend impact
            dividend_impact = (total_return - price_return) / (price_return + 1e-8)

            logger.debug(f"Calculated etf_dividend_reinvestment_impact: mean={dividend_impact.mean():.6f}")

            return dividend_impact

        except Exception as e:
            logger.error(f"etf_dividend_reinvestment_impact calculation failed: {e}")
            raise OperatorError(f"etf_dividend_reinvestment_impact failed: {e}") from e
