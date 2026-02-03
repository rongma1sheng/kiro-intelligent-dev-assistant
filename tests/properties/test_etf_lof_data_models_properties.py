"""Property-based tests for ETF and LOF data models

白皮书依据: 第四章 4.1.17, 4.1.18 - Data Model Validation
版本: v1.6.1

Tests:
- Property 16: Data Model Type Validation
- Property 17: Data Model Value Validation
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import date, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.evolution.etf_lof.data_models import (
    ETFMarketData,
    LOFMarketData,
    FactorExpression,
    ArenaTestResult,
)


# Strategy for generating valid dates
@st.composite
def valid_dates(draw):
    """Generate valid dates for testing"""
    days_offset = draw(st.integers(min_value=0, max_value=3650))  # 0-10 years
    return date.today() - timedelta(days=days_offset)


# Strategy for generating valid prices (positive floats)
valid_prices = st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)

# Strategy for generating valid volumes (non-negative floats)
valid_volumes = st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)

# Strategy for generating valid weights (0 to 1)
valid_weights = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for generating valid IC values (-1 to 1)
valid_ic = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for generating valid drawdowns (negative or zero)
valid_drawdowns = st.floats(min_value=-1.0, max_value=0.0, allow_nan=False, allow_infinity=False)


class TestETFMarketDataProperties:
    """Property tests for ETFMarketData
    
    **Validates: Requirements 9.1, 9.7, 9.8**
    **Property 16: Data Model Type Validation**
    **Property 17: Data Model Value Validation**
    """
    
    @given(
        symbol=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        test_date=valid_dates(),
        price=valid_prices,
        nav=valid_prices,
        volume=valid_volumes,
    )
    def test_property_16_etf_type_validation(self, symbol, test_date, price, nav, volume):
        """Property 16: ETFMarketData accepts correct types
        
        白皮书依据: 第四章 4.1.17 - ETF Data Model
        
        Property: For all valid inputs of correct types, ETFMarketData
        should be created successfully without raising TypeError.
        """
        # Create ETFMarketData with valid types
        data = ETFMarketData(
            symbol=symbol,
            date=test_date,
            price=price,
            nav=nav,
            volume=volume
        )
        
        # Verify types are preserved
        assert isinstance(data.symbol, str)
        assert isinstance(data.date, date)
        assert isinstance(data.price, (int, float))
        assert isinstance(data.nav, (int, float))
        assert isinstance(data.volume, (int, float))
    
    @given(
        symbol=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        test_date=valid_dates(),
        price=valid_prices,
        nav=valid_prices,
        volume=valid_volumes,
    )
    def test_property_17_etf_value_validation(self, symbol, test_date, price, nav, volume):
        """Property 17: ETFMarketData validates value ranges
        
        白皮书依据: 第四章 4.1.17 - ETF Data Model
        
        Property: For all valid inputs, ETFMarketData should validate that:
        - price > 0
        - nav > 0
        - volume >= 0
        """
        # Create ETFMarketData
        data = ETFMarketData(
            symbol=symbol,
            date=test_date,
            price=price,
            nav=nav,
            volume=volume
        )
        
        # Verify value constraints
        assert data.price > 0, "Price must be positive"
        assert data.nav > 0, "NAV must be positive"
        assert data.volume >= 0, "Volume must be non-negative"
    
    @given(
        symbol=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        test_date=valid_dates(),
        price=valid_prices,
        nav=valid_prices,
        volume=valid_volumes,
        bid_price=valid_prices,
        ask_price=valid_prices,
    )
    def test_property_17_etf_bid_ask_validation(self, symbol, test_date, price, nav, volume, bid_price, ask_price):
        """Property 17: ETFMarketData validates bid <= ask
        
        白皮书依据: 第四章 4.1.17 - ETF Data Model
        
        Property: When both bid and ask prices are provided, bid must be <= ask.
        """
        # Ensure bid <= ask
        if bid_price > ask_price:
            bid_price, ask_price = ask_price, bid_price
        
        # Create ETFMarketData with bid/ask
        data = ETFMarketData(
            symbol=symbol,
            date=test_date,
            price=price,
            nav=nav,
            volume=volume,
            bid_price=bid_price,
            ask_price=ask_price
        )
        
        # Verify bid <= ask
        assert data.bid_price <= data.ask_price, "Bid price must be <= ask price"
    
    def test_property_16_etf_rejects_invalid_types(self):
        """Property 16: ETFMarketData rejects invalid types
        
        白皮书依据: 第四章 4.1.17 - ETF Data Model
        
        Property: ETFMarketData should raise TypeError for invalid input types.
        """
        # Test invalid date type
        with pytest.raises(TypeError):
            ETFMarketData(
                symbol="TEST",
                date="2024-01-01",  # String instead of date
                price=100.0,
                nav=100.0,
                volume=1000.0
            )
    
    def test_property_17_etf_rejects_invalid_values(self):
        """Property 17: ETFMarketData rejects invalid values
        
        白皮书依据: 第四章 4.1.17 - ETF Data Model
        
        Property: ETFMarketData should raise ValueError for invalid value ranges.
        """
        # Test negative price
        with pytest.raises(ValueError, match="price must be positive"):
            ETFMarketData(
                symbol="TEST",
                date=date.today(),
                price=-100.0,  # Negative price
                nav=100.0,
                volume=1000.0
            )
        
        # Test negative volume
        with pytest.raises(ValueError, match="volume must be non-negative"):
            ETFMarketData(
                symbol="TEST",
                date=date.today(),
                price=100.0,
                nav=100.0,
                volume=-1000.0  # Negative volume
            )


class TestLOFMarketDataProperties:
    """Property tests for LOFMarketData
    
    **Validates: Requirements 9.2, 9.7, 9.8**
    **Property 16: Data Model Type Validation**
    **Property 17: Data Model Value Validation**
    """
    
    @given(
        symbol=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        test_date=valid_dates(),
        onmarket_price=valid_prices,
        offmarket_price=valid_prices,
        onmarket_volume=valid_volumes,
        nav=valid_prices,
    )
    def test_property_16_lof_type_validation(self, symbol, test_date, onmarket_price, offmarket_price, onmarket_volume, nav):
        """Property 16: LOFMarketData accepts correct types
        
        白皮书依据: 第四章 4.1.18 - LOF Data Model
        
        Property: For all valid inputs of correct types, LOFMarketData
        should be created successfully without raising TypeError.
        """
        # Create LOFMarketData with valid types
        data = LOFMarketData(
            symbol=symbol,
            date=test_date,
            onmarket_price=onmarket_price,
            offmarket_price=offmarket_price,
            onmarket_volume=onmarket_volume,
            nav=nav
        )
        
        # Verify types are preserved
        assert isinstance(data.symbol, str)
        assert isinstance(data.date, date)
        assert isinstance(data.onmarket_price, (int, float))
        assert isinstance(data.offmarket_price, (int, float))
        assert isinstance(data.onmarket_volume, (int, float))
        assert isinstance(data.nav, (int, float))
    
    @given(
        symbol=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        test_date=valid_dates(),
        onmarket_price=valid_prices,
        offmarket_price=valid_prices,
        onmarket_volume=valid_volumes,
        nav=valid_prices,
    )
    def test_property_17_lof_value_validation(self, symbol, test_date, onmarket_price, offmarket_price, onmarket_volume, nav):
        """Property 17: LOFMarketData validates value ranges
        
        白皮书依据: 第四章 4.1.18 - LOF Data Model
        
        Property: For all valid inputs, LOFMarketData should validate that:
        - onmarket_price > 0
        - offmarket_price > 0
        - onmarket_volume >= 0
        - nav > 0
        """
        # Create LOFMarketData
        data = LOFMarketData(
            symbol=symbol,
            date=test_date,
            onmarket_price=onmarket_price,
            offmarket_price=offmarket_price,
            onmarket_volume=onmarket_volume,
            nav=nav
        )
        
        # Verify value constraints
        assert data.onmarket_price > 0, "Onmarket price must be positive"
        assert data.offmarket_price > 0, "Offmarket price must be positive"
        assert data.onmarket_volume >= 0, "Onmarket volume must be non-negative"
        assert data.nav > 0, "NAV must be positive"
    
    def test_property_16_lof_rejects_invalid_types(self):
        """Property 16: LOFMarketData rejects invalid types
        
        白皮书依据: 第四章 4.1.18 - LOF Data Model
        
        Property: LOFMarketData should raise TypeError for invalid input types.
        """
        # Test invalid date type
        with pytest.raises(TypeError):
            LOFMarketData(
                symbol="TEST",
                date="2024-01-01",  # String instead of date
                onmarket_price=100.0,
                offmarket_price=100.0,
                onmarket_volume=1000.0,
                nav=100.0
            )
    
    def test_property_17_lof_rejects_invalid_values(self):
        """Property 17: LOFMarketData rejects invalid values
        
        白皮书依据: 第四章 4.1.18 - LOF Data Model
        
        Property: LOFMarketData should raise ValueError for invalid value ranges.
        """
        # Test negative onmarket price
        with pytest.raises(ValueError, match="onmarket_price must be positive"):
            LOFMarketData(
                symbol="TEST",
                date=date.today(),
                onmarket_price=-100.0,  # Negative price
                offmarket_price=100.0,
                onmarket_volume=1000.0,
                nav=100.0
            )


class TestFactorExpressionProperties:
    """Property tests for FactorExpression
    
    **Validates: Requirements 9.5, 9.7, 9.8**
    **Property 16: Data Model Type Validation**
    """
    
    @given(
        expression_string=st.text(min_size=1, max_size=200),
        operator_tree=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False))
        )
    )
    def test_property_16_factor_expression_type_validation(self, expression_string, operator_tree):
        """Property 16: FactorExpression accepts correct types
        
        白皮书依据: 第四章 4.1 - Factor Expression Definition
        
        Property: For all valid inputs of correct types, FactorExpression
        should be created successfully without raising TypeError.
        """
        # Create FactorExpression
        expr = FactorExpression(
            expression_string=expression_string,
            operator_tree=operator_tree
        )
        
        # Verify types are preserved
        assert isinstance(expr.expression_string, str)
        assert isinstance(expr.operator_tree, dict)
        assert isinstance(expr.parameter_dict, dict)


class TestArenaTestResultProperties:
    """Property tests for ArenaTestResult
    
    **Validates: Requirements 9.6, 9.7, 9.8**
    **Property 16: Data Model Type Validation**
    **Property 17: Data Model Value Validation**
    """
    
    @given(
        factor_id=st.text(min_size=1, max_size=50),
        track_name=st.sampled_from(['Reality Track', 'Hell Track', 'Cross-Market Track']),
        ic=valid_ic,
        ir=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        sharpe=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        max_drawdown=valid_drawdowns,
        pass_status=st.booleans(),
        test_date=valid_dates(),
    )
    def test_property_16_arena_result_type_validation(self, factor_id, track_name, ic, ir, sharpe, max_drawdown, pass_status, test_date):
        """Property 16: ArenaTestResult accepts correct types
        
        白皮书依据: 第四章 4.2 - Factor Arena Testing
        
        Property: For all valid inputs of correct types, ArenaTestResult
        should be created successfully without raising TypeError.
        """
        # Create ArenaTestResult
        result = ArenaTestResult(
            factor_id=factor_id,
            track_name=track_name,
            ic=ic,
            ir=ir,
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            pass_status=pass_status,
            test_date=test_date
        )
        
        # Verify types are preserved
        assert isinstance(result.factor_id, str)
        assert isinstance(result.track_name, str)
        assert isinstance(result.ic, (int, float))
        assert isinstance(result.ir, (int, float))
        assert isinstance(result.sharpe, (int, float))
        assert isinstance(result.max_drawdown, (int, float))
        assert isinstance(result.pass_status, bool)
        assert isinstance(result.test_date, date)
    
    @given(
        factor_id=st.text(min_size=1, max_size=50),
        track_name=st.sampled_from(['Reality Track', 'Hell Track', 'Cross-Market Track']),
        ic=valid_ic,
        ir=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        sharpe=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        max_drawdown=valid_drawdowns,
        pass_status=st.booleans(),
        test_date=valid_dates(),
    )
    def test_property_17_arena_result_value_validation(self, factor_id, track_name, ic, ir, sharpe, max_drawdown, pass_status, test_date):
        """Property 17: ArenaTestResult validates value ranges
        
        白皮书依据: 第四章 4.2 - Factor Arena Testing
        
        Property: For all valid inputs, ArenaTestResult should validate that:
        - ic in [-1, 1]
        - max_drawdown <= 0
        """
        # Create ArenaTestResult
        result = ArenaTestResult(
            factor_id=factor_id,
            track_name=track_name,
            ic=ic,
            ir=ir,
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            pass_status=pass_status,
            test_date=test_date
        )
        
        # Verify value constraints
        assert -1 <= result.ic <= 1, "IC must be in [-1, 1]"
        assert result.max_drawdown <= 0, "Max drawdown must be <= 0"
    
    def test_property_17_arena_result_rejects_invalid_values(self):
        """Property 17: ArenaTestResult rejects invalid values
        
        白皮书依据: 第四章 4.2 - Factor Arena Testing
        
        Property: ArenaTestResult should raise ValueError for invalid value ranges.
        """
        # Test IC out of range
        with pytest.raises(ValueError, match="IC must be in"):
            ArenaTestResult(
                factor_id="test",
                track_name="Reality Track",
                ic=1.5,  # Out of range
                ir=1.0,
                sharpe=1.0,
                max_drawdown=-0.1,
                pass_status=True,
                test_date=date.today()
            )
        
        # Test positive max_drawdown
        with pytest.raises(ValueError, match="max_drawdown must be"):
            ArenaTestResult(
                factor_id="test",
                track_name="Reality Track",
                ic=0.5,
                ir=1.0,
                sharpe=1.0,
                max_drawdown=0.1,  # Positive (invalid)
                pass_status=True,
                test_date=date.today()
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
