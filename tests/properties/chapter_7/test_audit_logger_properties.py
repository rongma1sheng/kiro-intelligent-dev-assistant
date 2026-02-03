"""AuditLogger属性测试

白皮书依据: 第六章 6.2.2 审计日志系统

Property-Based Testing验证AuditLogger的核心属性：
- Property 5: Audit Log Signature Integrity
- Property 6: Audit Entry Round-Trip
- Property 7: Audit Log Entry Completeness
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Any

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.audit.audit_logger import AuditLogger, IntegrityError
from src.audit.data_models import AuditEventType, AuditEntry


# ============================================================================
# 自定义策略
# ============================================================================

# 有效的股票代码策略
stock_symbol_strategy = st.sampled_from([
    '000001.SZ', '000002.SZ', '600000.SH', '600001.SH',
    '300001.SZ', '002001.SZ', '688001.SH', '000858.SZ'
])

# 有效的交易动作策略
trade_action_strategy = st.sampled_from(['buy', 'sell'])

# 有效的事件类型策略
event_type_strategy = st.sampled_from([e.value for e in AuditEventType])

# 正整数策略（数量）
positive_int_strategy = st.integers(min_value=1, max_value=1000000)

# 正浮点数策略（价格）
positive_float_strategy = st.floats(
    min_value=0.01, max_value=10000.0,
    allow_nan=False, allow_infinity=False
)

# 交易数据策略
trade_data_strategy = st.fixed_dictionaries({
    'symbol': stock_symbol_strategy,
    'action': trade_action_strategy,
    'quantity': positive_int_strategy,
    'price': positive_float_strategy,
}).map(lambda d: {**d, 'amount': d['quantity'] * d['price']})


# ============================================================================
# 辅助函数
# ============================================================================

def create_temp_logger():
    """创建临时AuditLogger实例"""
    temp_dir = tempfile.mkdtemp()
    logger = AuditLogger(log_dir=temp_dir)
    return logger, temp_dir


def cleanup_temp_dir(temp_dir):
    """清理临时目录"""
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Property 5: Audit Log Signature Integrity
# ============================================================================

class TestProperty5AuditLogSignatureIntegrity:
    """Property 5: 审计日志签名完整性
    
    白皮书依据: 第六章 6.2.2 审计日志系统
    **Validates: Requirements 4.2**
    
    属性定义：
    对于任意审计条目，其SHA256签名必须满足：
    1. 签名是64字符的十六进制字符串
    2. 相同数据产生相同签名（确定性）
    3. 不同数据产生不同签名（抗碰撞）
    4. 签名计算排除audit_signature字段本身
    """
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=100, deadline=None)
    def test_signature_is_valid_sha256_format(self, trade_data):
        """签名必须是有效的SHA256格式
        
        **Validates: Requirements 4.2**
        """
        logger, temp_dir = create_temp_logger()
        try:
            entry = logger.log_trade(trade_data)
            
            # 签名必须是64字符
            assert len(entry.audit_signature) == 64
            
            # 签名必须是十六进制
            assert all(c in '0123456789abcdef' for c in entry.audit_signature)
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=50, deadline=None)
    def test_signature_is_deterministic(self, trade_data):
        """相同数据必须产生相同签名
        
        **Validates: Requirements 4.2**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 构建相同的审计条目
            entry1 = {
                'timestamp': '2026-01-25T10:00:00',
                'event_type': 'TRADE_EXECUTION',
                'data': trade_data,
            }
            entry2 = {
                'timestamp': '2026-01-25T10:00:00',
                'event_type': 'TRADE_EXECUTION',
                'data': trade_data,
            }
            
            sig1 = logger._generate_signature(entry1)
            sig2 = logger._generate_signature(entry2)
            
            assert sig1 == sig2
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(
        trade_data1=trade_data_strategy,
        trade_data2=trade_data_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_different_data_produces_different_signature(
        self, trade_data1, trade_data2
    ):
        """不同数据必须产生不同签名
        
        **Validates: Requirements 4.2**
        """
        # 确保数据不同
        assume(trade_data1 != trade_data2)
        
        logger, temp_dir = create_temp_logger()
        try:
            entry1 = {
                'timestamp': '2026-01-25T10:00:00',
                'event_type': 'TRADE_EXECUTION',
                'data': trade_data1,
            }
            entry2 = {
                'timestamp': '2026-01-25T10:00:00',
                'event_type': 'TRADE_EXECUTION',
                'data': trade_data2,
            }
            
            sig1 = logger._generate_signature(entry1)
            sig2 = logger._generate_signature(entry2)
            
            assert sig1 != sig2
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=50, deadline=None)
    def test_signature_excludes_signature_field(self, trade_data):
        """签名计算必须排除audit_signature字段
        
        **Validates: Requirements 4.2**
        """
        logger, temp_dir = create_temp_logger()
        try:
            entry_without_sig = {
                'timestamp': '2026-01-25T10:00:00',
                'event_type': 'TRADE_EXECUTION',
                'data': trade_data,
            }
            
            entry_with_sig = {
                'timestamp': '2026-01-25T10:00:00',
                'event_type': 'TRADE_EXECUTION',
                'data': trade_data,
                'audit_signature': 'some_existing_signature_12345678901234567890123456789012',
            }
            
            sig1 = logger._generate_signature(entry_without_sig)
            sig2 = logger._generate_signature(entry_with_sig)
            
            # 签名应该相同（audit_signature被排除）
            assert sig1 == sig2
        finally:
            cleanup_temp_dir(temp_dir)


# ============================================================================
# Property 6: Audit Entry Round-Trip
# ============================================================================

class TestProperty6AuditEntryRoundTrip:
    """Property 6: 审计条目往返一致性
    
    白皮书依据: 第六章 6.2.2 审计日志系统
    **Validates: Requirements 4.3**
    
    属性定义：
    对于任意审计条目，写入后读取必须保持数据一致：
    1. 写入的数据可以完整读取
    2. 读取的数据与写入的数据一致
    3. 签名验证通过
    """
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=50, deadline=None)
    def test_trade_entry_round_trip(self, trade_data):
        """交易条目写入后读取必须一致
        
        **Validates: Requirements 4.3**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 写入
            entry = logger.log_trade(trade_data)
            
            # 读取
            logs = logger.get_recent_logs(1)
            
            assert len(logs) == 1
            
            read_entry = logs[0]
            
            # 验证关键字段
            assert read_entry['symbol'] == trade_data['symbol']
            assert read_entry['action'] == trade_data['action']
            assert read_entry['quantity'] == trade_data['quantity']
            assert abs(read_entry['price'] - trade_data['price']) < 0.001
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(event_type=event_type_strategy)
    @settings(max_examples=50, deadline=None)
    def test_event_entry_round_trip(self, event_type):
        """事件条目写入后读取必须一致
        
        **Validates: Requirements 4.3**
        """
        logger, temp_dir = create_temp_logger()
        try:
            event_data = {
                'event_type': event_type,
                'test_field': 'test_value',
            }
            
            # 写入
            entry = logger.log_event(event_data)
            
            # 读取
            logs = logger.get_recent_logs(1)
            
            assert len(logs) == 1
            
            read_entry = logs[0]
            
            # 验证事件类型
            assert read_entry['event_type'] == event_type
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=30, deadline=None)
    def test_integrity_verification_after_round_trip(self, trade_data):
        """往返后完整性验证必须通过
        
        **Validates: Requirements 4.3, 4.5**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 写入
            logger.log_trade(trade_data)
            
            # 验证完整性
            result = logger.verify_integrity()
            
            assert result is True
        finally:
            cleanup_temp_dir(temp_dir)


# ============================================================================
# Property 7: Audit Log Entry Completeness
# ============================================================================

class TestProperty7AuditLogEntryCompleteness:
    """Property 7: 审计日志条目完整性
    
    白皮书依据: 第六章 6.2.2 审计日志系统
    **Validates: Requirements 4.5, 4.7**
    
    属性定义：
    对于任意审计条目，必须包含所有必需字段：
    1. timestamp - 时间戳
    2. event_type - 事件类型
    3. audit_signature - 审计签名
    4. 交易条目必须包含symbol, action, quantity, price
    """
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=50, deadline=None)
    def test_trade_entry_has_all_required_fields(self, trade_data):
        """交易条目必须包含所有必需字段
        
        **Validates: Requirements 4.5**
        """
        logger, temp_dir = create_temp_logger()
        try:
            entry = logger.log_trade(trade_data)
            
            # 验证AuditEntry对象字段
            assert entry.timestamp is not None
            assert isinstance(entry.timestamp, datetime)
            assert entry.event_type == AuditEventType.TRADE_EXECUTION
            assert entry.audit_signature is not None
            assert len(entry.audit_signature) == 64
            
            # 验证数据字段
            assert 'symbol' in entry.data
            assert 'action' in entry.data
            assert 'quantity' in entry.data
            assert 'price' in entry.data
            assert 'amount' in entry.data
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(event_type=event_type_strategy)
    @settings(max_examples=50, deadline=None)
    def test_event_entry_has_all_required_fields(self, event_type):
        """事件条目必须包含所有必需字段
        
        **Validates: Requirements 4.5**
        """
        logger, temp_dir = create_temp_logger()
        try:
            event_data = {
                'event_type': event_type,
            }
            
            entry = logger.log_event(event_data)
            
            # 验证AuditEntry对象字段
            assert entry.timestamp is not None
            assert isinstance(entry.timestamp, datetime)
            assert entry.event_type is not None
            assert entry.audit_signature is not None
            assert len(entry.audit_signature) == 64
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=30, deadline=None)
    def test_log_file_entry_has_all_required_fields(self, trade_data):
        """日志文件中的条目必须包含所有必需字段
        
        **Validates: Requirements 4.5, 4.7**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 写入
            logger.log_trade(trade_data)
            
            # 从文件读取
            with open(logger.log_file, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
            
            entry = json.loads(line)
            
            # 验证必需字段
            assert 'timestamp' in entry
            assert 'event_type' in entry
            assert 'audit_signature' in entry
            assert 'symbol' in entry
            assert 'action' in entry
            assert 'quantity' in entry
            assert 'price' in entry
            assert 'amount' in entry
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(
        trade_data=trade_data_strategy,
        count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_entries_all_complete(self, trade_data, count):
        """多条日志条目都必须完整
        
        **Validates: Requirements 4.5, 4.7**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 写入多条
            for _ in range(count):
                logger.log_trade(trade_data)
            
            # 读取所有
            logs = logger.get_recent_logs(count)
            
            assert len(logs) == count
            
            # 验证每条都完整
            for log in logs:
                assert 'timestamp' in log
                assert 'event_type' in log
                assert 'audit_signature' in log
        finally:
            cleanup_temp_dir(temp_dir)


# ============================================================================
# 篡改检测属性测试
# ============================================================================

class TestTamperDetectionProperties:
    """篡改检测属性测试
    
    白皮书依据: 第六章 6.2.3 完整性验证
    **Validates: Requirements 4.5, 4.6**
    """
    
    @given(
        trade_data=trade_data_strategy,
        tamper_field=st.sampled_from(['quantity', 'price', 'symbol', 'action'])
    )
    @settings(max_examples=30, deadline=None)
    def test_any_field_tampering_detected(
        self, trade_data, tamper_field
    ):
        """任何字段的篡改都必须被检测到
        
        **Validates: Requirements 4.5, 4.6**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 写入
            logger.log_trade(trade_data)
            
            # 读取并篡改
            with open(logger.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entry = json.loads(content.strip())
            
            # 篡改指定字段
            if tamper_field == 'quantity':
                entry['quantity'] = entry['quantity'] + 1
            elif tamper_field == 'price':
                entry['price'] = entry['price'] + 0.01
            elif tamper_field == 'symbol':
                entry['symbol'] = '999999.SZ'
            elif tamper_field == 'action':
                entry['action'] = 'sell' if entry['action'] == 'buy' else 'buy'
            
            # 写回篡改后的内容
            with open(logger.log_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            # 验证应该失败
            with pytest.raises(IntegrityError):
                logger.verify_integrity()
        finally:
            cleanup_temp_dir(temp_dir)
    
    @given(trade_data=trade_data_strategy)
    @settings(max_examples=20, deadline=None)
    def test_signature_tampering_detected(self, trade_data):
        """签名篡改必须被检测到
        
        **Validates: Requirements 4.5, 4.6**
        """
        logger, temp_dir = create_temp_logger()
        try:
            # 写入
            logger.log_trade(trade_data)
            
            # 读取并篡改签名
            with open(logger.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entry = json.loads(content.strip())
            
            # 篡改签名
            original_sig = entry['audit_signature']
            tampered_sig = original_sig[:-1] + ('0' if original_sig[-1] != '0' else '1')
            entry['audit_signature'] = tampered_sig
            
            # 写回
            with open(logger.log_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            # 验证应该失败
            with pytest.raises(IntegrityError):
                logger.verify_integrity()
        finally:
            cleanup_temp_dir(temp_dir)

