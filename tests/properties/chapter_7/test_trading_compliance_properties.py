"""TradingComplianceManager属性测试

白皮书依据: 第七章 7.3 合规体系

Property 8: Trading Compliance Enforcement
*For any* trade order, the TradingComplianceManager SHALL reject the order if any of the following conditions are true:
- Daily trade count exceeds 200
- Trade amount exceeds 1,000,000 CNY
- Symbol is an ST stock
- Symbol is suspended
- Symbol listed less than 5 days
- Derivative margin ratio exceeds 30%

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

from src.compliance.trading_compliance_manager import (
    TradingComplianceManager,
    ComplianceError,
    ComplianceCheckResult,
)
from src.compliance.data_models import (
    ComplianceCheckType,
    TradeOrder,
    StockInfo,
)


# ========== 策略定义 ==========

# 股票代码策略
stock_symbol_strategy = st.from_regex(r'[0-9]{6}\.(SZ|SH)', fullmatch=True)

# 衍生品代码策略
derivative_symbol_strategy = st.from_regex(r'(IF|IC|IH)[0-9]{4}', fullmatch=True)

# 交易动作策略
action_strategy = st.sampled_from(['buy', 'sell'])

# 正数策略
positive_float_strategy = st.floats(min_value=0.01, max_value=1e9, allow_nan=False, allow_infinity=False)
positive_int_strategy = st.integers(min_value=1, max_value=1000000)

# 比例策略（0-1之间）
ratio_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


class TestProperty8TradingComplianceEnforcement:
    """Property 8: Trading Compliance Enforcement
    
    Feature: chapter-7-security-and-chapter-6-tests
    Property 8: Trading Compliance Enforcement
    
    *For any* trade order, the TradingComplianceManager SHALL reject the order 
    if any of the following conditions are true:
    - Daily trade count exceeds 200
    - Trade amount exceeds 1,000,000 CNY
    - Symbol is an ST stock
    - Symbol is suspended
    - Symbol listed less than 5 days
    - Derivative margin ratio exceeds 30%
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
    """
    
    @given(
        trade_count=st.integers(min_value=200, max_value=1000),
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_daily_trade_limit_exceeded_rejects(
        self,
        trade_count: int,
        quantity: int,
        price: float
    ):
        """Property 8.1: 日交易次数超过200时必须拒绝
        
        **Validates: Requirements 6.1**
        """
        manager = TradingComplianceManager(daily_trade_limit=200)
        today = datetime.now().strftime('%Y%m%d')
        manager.set_trade_count(today, trade_count)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 验证违规类型
        violation_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.DAILY_TRADE_LIMIT in violation_types
    
    @given(
        quantity=st.integers(min_value=1, max_value=100000),
        price=st.floats(min_value=10.01, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_single_amount_exceeded_rejects(
        self,
        quantity: int,
        price: float
    ):
        """Property 8.2: 单笔金额超过1,000,000 CNY时必须拒绝
        
        **Validates: Requirements 6.2**
        """
        # 确保金额超过限制
        amount = quantity * price
        assume(amount > 1_000_000.0)
        
        manager = TradingComplianceManager(single_trade_limit=1_000_000.0)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 验证违规类型
        violation_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.SINGLE_TRADE_AMOUNT in violation_types
    
    @given(
        symbol=stock_symbol_strategy,
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_st_stock_rejects(
        self,
        symbol: str,
        quantity: int,
        price: float
    ):
        """Property 8.3: ST股票必须被拒绝
        
        **Validates: Requirements 6.3**
        """
        manager = TradingComplianceManager()
        manager.add_st_stock(symbol)
        
        order = TradeOrder(
            symbol=symbol,
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 验证违规类型
        violation_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.ST_STOCK in violation_types
    
    @given(
        symbol=stock_symbol_strategy,
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_suspended_stock_rejects(
        self,
        symbol: str,
        quantity: int,
        price: float
    ):
        """Property 8.4: 停牌股票必须被拒绝
        
        **Validates: Requirements 6.4**
        """
        manager = TradingComplianceManager()
        manager.add_suspended_stock(symbol)
        
        order = TradeOrder(
            symbol=symbol,
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 验证违规类型
        violation_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.SUSPENDED_STOCK in violation_types

    
    @given(
        symbol=stock_symbol_strategy,
        days_since_listing=st.integers(min_value=0, max_value=4),
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_new_stock_rejects(
        self,
        symbol: str,
        days_since_listing: int,
        quantity: int,
        price: float
    ):
        """Property 8.5: 上市不足5天的新股必须被拒绝
        
        **Validates: Requirements 6.5**
        """
        manager = TradingComplianceManager(new_stock_days=5)
        
        # 设置上市日期
        list_date = datetime.now() - timedelta(days=days_since_listing)
        stock_info = StockInfo(
            symbol=symbol,
            name="新股测试",
            is_st=False,
            is_suspended=False,
            list_date=list_date
        )
        manager.set_stock_info(stock_info)
        
        order = TradeOrder(
            symbol=symbol,
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 验证违规类型
        violation_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.NEW_STOCK in violation_types
    
    @given(
        margin_ratio=st.floats(min_value=0.30, max_value=1.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=1, max_value=10),
        price=st.floats(min_value=1000.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_margin_ratio_exceeded_rejects(
        self,
        margin_ratio: float,
        quantity: int,
        price: float
    ):
        """Property 8.6: 衍生品保证金比例超过30%时必须拒绝
        
        **Validates: Requirements 6.6**
        """
        manager = TradingComplianceManager(margin_ratio_limit=0.30)
        manager.set_margin_ratio(margin_ratio)
        
        order = TradeOrder(
            symbol="IF2401",
            action="buy",
            quantity=quantity,
            price=price,
            is_derivative=True
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 验证违规类型
        violation_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.MARGIN_RATIO in violation_types


class TestProperty8Inverse:
    """Property 8 逆向测试：合规订单必须通过
    
    Feature: chapter-7-security-and-chapter-6-tests
    Property 8 (Inverse): Trading Compliance Allowance
    
    *For any* trade order that does NOT violate any compliance rules,
    the TradingComplianceManager SHALL approve the order.
    """
    
    @given(
        trade_count=st.integers(min_value=0, max_value=199),
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_compliant_order_passes(
        self,
        trade_count: int,
        quantity: int,
        price: float
    ):
        """Property 8 (Inverse): 合规订单必须通过
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
        """
        # 确保金额不超限
        amount = quantity * price
        assume(amount <= 1_000_000.0)
        
        manager = TradingComplianceManager(
            daily_trade_limit=200,
            single_trade_limit=1_000_000.0,
            new_stock_days=5,
            margin_ratio_limit=0.30
        )
        
        today = datetime.now().strftime('%Y%m%d')
        manager.set_trade_count(today, trade_count)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price,
            is_derivative=False
        )
        
        result = manager.check_trade_compliance(order)
        
        assert result.passed is True
        assert len(result.violations) == 0
    
    @given(
        margin_ratio=st.floats(min_value=0.0, max_value=0.29, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=1, max_value=10),
        price=st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_derivative_with_low_margin_passes(
        self,
        margin_ratio: float,
        quantity: int,
        price: float
    ):
        """Property 8 (Inverse): 保证金比例低于30%的衍生品订单通过
        
        **Validates: Requirements 6.6**
        """
        # 确保金额不超限
        amount = quantity * price
        assume(amount <= 1_000_000.0)
        
        manager = TradingComplianceManager(margin_ratio_limit=0.30)
        manager.set_margin_ratio(margin_ratio)
        
        order = TradeOrder(
            symbol="IF2401",
            action="buy",
            quantity=quantity,
            price=price,
            is_derivative=True
        )
        
        result = manager.check_trade_compliance(order)
        
        assert result.passed is True


class TestComplianceCheckIdempotence:
    """合规检查幂等性测试
    
    Feature: chapter-7-security-and-chapter-6-tests
    Property: Compliance Check Idempotence
    
    *For any* trade order, running compliance check multiple times 
    (without state changes) SHALL produce the same result.
    """
    
    @given(
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_compliance_check_idempotent_pass(
        self,
        quantity: int,
        price: float
    ):
        """合规检查幂等性：通过的订单多次检查结果一致"""
        # 确保金额不超限
        amount = quantity * price
        assume(amount <= 1_000_000.0)
        
        manager = TradingComplianceManager()
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price
        )
        
        # 第一次检查
        result1 = manager.check_trade_compliance(order)
        
        # 重置交易计数（因为通过会增加计数）
        manager.reset_daily_count()
        
        # 第二次检查
        result2 = manager.check_trade_compliance(order)
        
        assert result1.passed == result2.passed
        assert len(result1.violations) == len(result2.violations)
    
    @given(
        symbol=stock_symbol_strategy,
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_compliance_check_idempotent_fail(
        self,
        symbol: str,
        quantity: int,
        price: float
    ):
        """合规检查幂等性：失败的订单多次检查结果一致"""
        manager = TradingComplianceManager()
        manager.add_st_stock(symbol)
        
        order = TradeOrder(
            symbol=symbol,
            action="buy",
            quantity=quantity,
            price=price
        )
        
        # 第一次检查
        try:
            manager.check_trade_compliance(order)
            result1_passed = True
            result1_violations = 0
        except ComplianceError as e:
            result1_passed = False
            result1_violations = len(e.violations)
        
        # 第二次检查
        try:
            manager.check_trade_compliance(order)
            result2_passed = True
            result2_violations = 0
        except ComplianceError as e:
            result2_passed = False
            result2_violations = len(e.violations)
        
        assert result1_passed == result2_passed
        assert result1_violations == result2_violations


class TestComplianceViolationDetails:
    """合规违规详情测试
    
    Feature: chapter-7-security-and-chapter-6-tests
    Property: Compliance Violation Details Completeness
    
    *For any* compliance violation, the violation SHALL contain
    complete details about the failed check.
    """
    
    @given(
        trade_count=st.integers(min_value=200, max_value=500),
        quantity=st.integers(min_value=1, max_value=100),
        price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_daily_limit_violation_has_details(
        self,
        trade_count: int,
        quantity: int,
        price: float
    ):
        """日交易次数违规包含完整详情"""
        manager = TradingComplianceManager(daily_trade_limit=200)
        today = datetime.now().strftime('%Y%m%d')
        manager.set_trade_count(today, trade_count)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.DAILY_TRADE_LIMIT
        )
        
        assert 'current_count' in violation.details
        assert 'limit' in violation.details
        assert violation.details['current_count'] == trade_count
        assert violation.details['limit'] == 200
    
    @given(
        quantity=st.integers(min_value=10001, max_value=100000),
        price=st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_amount_violation_has_details(
        self,
        quantity: int,
        price: float
    ):
        """单笔金额违规包含完整详情"""
        # 确保金额超限
        amount = quantity * price
        assume(amount > 1_000_000.0)
        
        manager = TradingComplianceManager(single_trade_limit=1_000_000.0)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.SINGLE_TRADE_AMOUNT
        )
        
        assert 'amount' in violation.details
        assert 'limit' in violation.details
        assert violation.details['amount'] == amount
        assert violation.details['limit'] == 1_000_000.0


class TestTradeOrderProperties:
    """TradeOrder属性测试"""
    
    @given(
        quantity=st.integers(min_value=1, max_value=1000000),
        price=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_order_amount_calculation(
        self,
        quantity: int,
        price: float
    ):
        """订单金额计算正确性"""
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=quantity,
            price=price
        )
        
        expected_amount = quantity * price
        assert abs(order.amount - expected_amount) < 0.001
    
    @given(
        symbol=stock_symbol_strategy,
        action=action_strategy,
        quantity=st.integers(min_value=1, max_value=1000),
        price=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_order_to_dict_roundtrip(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float
    ):
        """订单序列化包含所有字段"""
        order = TradeOrder(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price
        )
        
        order_dict = order.to_dict()
        
        assert order_dict['symbol'] == symbol
        assert order_dict['action'] == action
        assert order_dict['quantity'] == quantity
        assert order_dict['price'] == price
        assert 'amount' in order_dict
