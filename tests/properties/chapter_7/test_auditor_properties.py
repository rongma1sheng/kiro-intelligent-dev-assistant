"""Auditor属性测试

白皮书依据: 第七章 6.2.1 独立审计进程

Property-Based Testing验证Auditor的核心属性：
- Property 3: Shadow Ledger Position Verification
- Property 4: Reconciliation Discrepancy Detection
"""

from typing import Dict

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.audit.auditor import Auditor, InsufficientPositionError
from src.audit.data_models import ShadowPosition


# ============================================================================
# 自定义策略
# ============================================================================

# 有效的股票代码策略
stock_symbol_strategy = st.sampled_from([
    '000001.SZ', '000002.SZ', '600000.SH', '600001.SH',
    '300001.SZ', '002001.SZ', '688001.SH', '000858.SZ'
])

# 正整数策略（数量）
positive_quantity_strategy = st.floats(
    min_value=1.0, max_value=1000000.0,
    allow_nan=False, allow_infinity=False
)

# 正浮点数策略（价格）
positive_price_strategy = st.floats(
    min_value=0.01, max_value=10000.0,
    allow_nan=False, allow_infinity=False
)

# 持仓字典策略
position_dict_strategy = st.dictionaries(
    keys=stock_symbol_strategy,
    values=positive_quantity_strategy,
    min_size=0,
    max_size=10
)


# ============================================================================
# 辅助函数
# ============================================================================

def create_auditor_with_positions(positions: Dict[str, float]) -> Auditor:
    """创建带指定持仓的Auditor"""
    auditor = Auditor()
    for symbol, quantity in positions.items():
        auditor.shadow_ledger[symbol] = ShadowPosition(
            symbol=symbol,
            quantity=quantity,
            avg_cost=10.0,  # 默认成本
            last_sync='2026-01-25T10:00:00'
        )
    return auditor


# ============================================================================
# Property 3: Shadow Ledger Position Verification
# ============================================================================

class TestProperty3ShadowLedgerPositionVerification:
    """Property 3: 影子账本持仓验证
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    **Validates: Requirements 3.4**
    
    属性定义：
    对于任意卖出交易请求，Auditor应当：
    - 当影子账本中有足够持仓时，批准交易
    - 当影子账本中持仓不足时，拒绝交易
    """
    
    @given(
        symbol=stock_symbol_strategy,
        position_quantity=positive_quantity_strategy,
        sell_quantity=positive_quantity_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_sell_approved_when_sufficient_position(
        self, symbol, position_quantity, sell_quantity
    ):
        """当持仓足够时，卖出交易应被批准
        
        **Validates: Requirements 3.4**
        """
        # 确保卖出数量不超过持仓
        assume(sell_quantity <= position_quantity)
        
        auditor = create_auditor_with_positions({symbol: position_quantity})
        
        result = auditor.verify_trade({
            'symbol': symbol,
            'action': 'sell',
            'quantity': sell_quantity
        })
        
        assert result is True
    
    @given(
        symbol=stock_symbol_strategy,
        position_quantity=positive_quantity_strategy,
        extra_quantity=st.floats(min_value=0.01, max_value=1000.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_sell_rejected_when_insufficient_position(
        self, symbol, position_quantity, extra_quantity
    ):
        """当持仓不足时，卖出交易应被拒绝
        
        **Validates: Requirements 3.4**
        """
        sell_quantity = position_quantity + extra_quantity
        
        auditor = create_auditor_with_positions({symbol: position_quantity})
        
        with pytest.raises(InsufficientPositionError):
            auditor.verify_trade({
                'symbol': symbol,
                'action': 'sell',
                'quantity': sell_quantity
            })
    
    @given(
        symbol=stock_symbol_strategy,
        sell_quantity=positive_quantity_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_sell_rejected_when_no_position(self, symbol, sell_quantity):
        """当无持仓时，卖出交易应被拒绝
        
        **Validates: Requirements 3.4**
        """
        auditor = Auditor()  # 空账本
        
        with pytest.raises(InsufficientPositionError):
            auditor.verify_trade({
                'symbol': symbol,
                'action': 'sell',
                'quantity': sell_quantity
            })
    
    @given(
        symbol=stock_symbol_strategy,
        buy_quantity=positive_quantity_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_buy_always_approved(self, symbol, buy_quantity):
        """买入交易应总是被批准（不检查持仓）
        
        **Validates: Requirements 3.4**
        """
        auditor = Auditor()  # 空账本
        
        result = auditor.verify_trade({
            'symbol': symbol,
            'action': 'buy',
            'quantity': buy_quantity
        })
        
        assert result is True
    
    @given(
        symbol=stock_symbol_strategy,
        position_quantity=positive_quantity_strategy,
        buy_quantity=positive_quantity_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_buy_approved_regardless_of_position(
        self, symbol, position_quantity, buy_quantity
    ):
        """买入交易应被批准，无论当前持仓多少
        
        **Validates: Requirements 3.4**
        """
        auditor = create_auditor_with_positions({symbol: position_quantity})
        
        result = auditor.verify_trade({
            'symbol': symbol,
            'action': 'buy',
            'quantity': buy_quantity
        })
        
        assert result is True


# ============================================================================
# Property 4: Reconciliation Discrepancy Detection
# ============================================================================

class TestProperty4ReconciliationDiscrepancyDetection:
    """Property 4: 对账差异检测
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    **Validates: Requirements 3.6**
    
    属性定义：
    对于任意执行账本和影子账本的组合，对账应当：
    - 准确报告所有数量不同的股票
    - 正确计算差异值
    """
    
    @given(positions=position_dict_strategy)
    @settings(max_examples=50, deadline=None)
    def test_no_discrepancy_when_ledgers_match(self, positions):
        """当账本完全匹配时，不应报告差异
        
        **Validates: Requirements 3.6**
        """
        auditor = create_auditor_with_positions(positions)
        
        # 执行账本与影子账本相同
        execution_ledger = positions.copy()
        
        discrepancies = auditor.reconcile(execution_ledger)
        
        assert len(discrepancies) == 0
    
    @given(
        symbol=stock_symbol_strategy,
        shadow_qty=positive_quantity_strategy,
        execution_qty=positive_quantity_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_discrepancy_detected_when_quantities_differ(
        self, symbol, shadow_qty, execution_qty
    ):
        """当数量不同时，应检测到差异
        
        **Validates: Requirements 3.6**
        """
        # 确保数量确实不同（超过容差）
        assume(abs(shadow_qty - execution_qty) > 0.001)
        
        auditor = create_auditor_with_positions({symbol: shadow_qty})
        execution_ledger = {symbol: execution_qty}
        
        discrepancies = auditor.reconcile(execution_ledger)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == symbol
        assert abs(discrepancies[0].shadow_quantity - shadow_qty) < 0.001
        assert abs(discrepancies[0].execution_quantity - execution_qty) < 0.001
    
    @given(
        symbol=stock_symbol_strategy,
        shadow_qty=positive_quantity_strategy,
        execution_qty=positive_quantity_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_discrepancy_difference_is_correct(
        self, symbol, shadow_qty, execution_qty
    ):
        """差异值应正确计算为 shadow - execution
        
        **Validates: Requirements 3.6**
        """
        assume(abs(shadow_qty - execution_qty) > 0.001)
        
        auditor = create_auditor_with_positions({symbol: shadow_qty})
        execution_ledger = {symbol: execution_qty}
        
        discrepancies = auditor.reconcile(execution_ledger)
        
        expected_diff = shadow_qty - execution_qty
        actual_diff = discrepancies[0].difference
        
        assert abs(actual_diff - expected_diff) < 0.001
    
    @given(
        symbol=stock_symbol_strategy,
        shadow_qty=positive_quantity_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_discrepancy_when_missing_in_execution(self, symbol, shadow_qty):
        """当执行账本缺少股票时，应检测到差异
        
        **Validates: Requirements 3.6**
        """
        auditor = create_auditor_with_positions({symbol: shadow_qty})
        execution_ledger = {}  # 空执行账本
        
        discrepancies = auditor.reconcile(execution_ledger)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == symbol
        assert discrepancies[0].execution_quantity == 0
        assert abs(discrepancies[0].shadow_quantity - shadow_qty) < 0.001
    
    @given(
        symbol=stock_symbol_strategy,
        execution_qty=positive_quantity_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_discrepancy_when_missing_in_shadow(self, symbol, execution_qty):
        """当影子账本缺少股票时，应检测到差异
        
        **Validates: Requirements 3.6**
        """
        auditor = Auditor()  # 空影子账本
        execution_ledger = {symbol: execution_qty}
        
        discrepancies = auditor.reconcile(execution_ledger)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == symbol
        assert discrepancies[0].shadow_quantity == 0
        assert abs(discrepancies[0].execution_quantity - execution_qty) < 0.001
    
    @given(
        positions1=position_dict_strategy,
        positions2=position_dict_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_all_differing_symbols_reported(self, positions1, positions2):
        """所有数量不同的股票都应被报告
        
        **Validates: Requirements 3.6**
        """
        auditor = create_auditor_with_positions(positions1)
        
        discrepancies = auditor.reconcile(positions2)
        
        # 计算预期差异数量
        all_symbols = set(positions1.keys()) | set(positions2.keys())
        expected_discrepancies = 0
        for symbol in all_symbols:
            shadow_qty = positions1.get(symbol, 0)
            exec_qty = positions2.get(symbol, 0)
            if abs(shadow_qty - exec_qty) > 0.001:
                expected_discrepancies += 1
        
        assert len(discrepancies) == expected_discrepancies


# ============================================================================
# 持仓更新属性测试
# ============================================================================

class TestPositionUpdateProperties:
    """持仓更新属性测试
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    """
    
    @given(
        symbol=stock_symbol_strategy,
        quantity=positive_quantity_strategy,
        price=positive_price_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_buy_increases_position(self, symbol, quantity, price):
        """买入应增加持仓"""
        auditor = Auditor()
        
        auditor.update_position(symbol, 'buy', quantity, price)
        
        position = auditor.get_position(symbol)
        assert position is not None
        assert abs(position.quantity - quantity) < 0.001
    
    @given(
        symbol=stock_symbol_strategy,
        initial_qty=positive_quantity_strategy,
        sell_qty=positive_quantity_strategy,
        price=positive_price_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_sell_decreases_position(self, symbol, initial_qty, sell_qty, price):
        """卖出应减少持仓"""
        assume(sell_qty <= initial_qty)
        
        auditor = create_auditor_with_positions({symbol: initial_qty})
        
        auditor.update_position(symbol, 'sell', sell_qty, price)
        
        position = auditor.get_position(symbol)
        expected_qty = initial_qty - sell_qty
        
        if expected_qty < 0.001:
            # 全部卖出，持仓应被删除
            assert position is None
        else:
            assert position is not None
            assert abs(position.quantity - expected_qty) < 0.001
    
    @given(
        symbol=stock_symbol_strategy,
        qty1=positive_quantity_strategy,
        price1=positive_price_strategy,
        qty2=positive_quantity_strategy,
        price2=positive_price_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_average_cost_calculation(self, symbol, qty1, price1, qty2, price2):
        """平均成本应正确计算"""
        auditor = Auditor()
        
        auditor.update_position(symbol, 'buy', qty1, price1)
        auditor.update_position(symbol, 'buy', qty2, price2)
        
        position = auditor.get_position(symbol)
        
        expected_avg_cost = (qty1 * price1 + qty2 * price2) / (qty1 + qty2)
        
        assert abs(position.avg_cost - expected_avg_cost) < 0.001

