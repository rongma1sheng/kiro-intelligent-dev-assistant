"""数据模型单元测试

白皮书依据: 第七章 7.2 审计系统 & 7.3 安全系统
Requirements: 7.2.1, 7.3.1

测试所有数据模型的辅助方法，确保100%覆盖率。
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.audit.data_models import (
    AuditEntry,
    AuditEventType,
    ShadowLedgerEntry,
)
from src.security.data_models import (
    JWTPayload,
    TokenPayload,
    UserRole,
    EncryptedAPIKey,
)


class TestAuditEntryHelpers:
    """AuditEntry辅助方法测试
    
    白皮书依据: 第七章 7.2.1 审计日志
    Requirements: 7.2.1
    
    验证：
    1. to_dict方法正确序列化
    2. from_dict方法正确反序列化
    """
    
    def test_audit_entry_to_dict(self):
        """测试AuditEntry的to_dict方法"""
        timestamp = datetime(2024, 1, 1, 10, 0, 0)
        entry = AuditEntry(
            timestamp=timestamp,
            event_type=AuditEventType.TRADE_EXECUTION,
            data={"symbol": "000001.SZ", "quantity": 100},
            audit_signature="sig123",
            user_id="user123",
        )
        
        data = entry.to_dict()
        
        assert data["event_type"] == "TRADE_EXECUTION"
        assert data["user_id"] == "user123"
        assert data["data"]["symbol"] == "000001.SZ"
        assert data["audit_signature"] == "sig123"
        assert "timestamp" in data
    
    def test_audit_entry_from_dict(self):
        """测试AuditEntry的from_dict方法"""
        data = {
            "timestamp": "2024-01-01T10:00:00",
            "event_type": "TRADE_EXECUTION",
            "data": {"symbol": "600000.SH", "price": 10.5},
            "audit_signature": "sig456",
            "user_id": "trader1",
        }
        
        entry = AuditEntry.from_dict(data)
        
        assert entry.event_type == AuditEventType.TRADE_EXECUTION
        assert entry.user_id == "trader1"
        assert entry.data["symbol"] == "600000.SH"
        assert entry.audit_signature == "sig456"
        assert isinstance(entry.timestamp, datetime)
    
    def test_audit_entry_from_dict_default_user(self):
        """测试AuditEntry的from_dict方法 - 默认用户"""
        data = {
            "timestamp": "2024-01-01T10:00:00",
            "event_type": "USER_LOGIN",
            "data": {},
            "audit_signature": "sig789",
        }
        
        entry = AuditEntry.from_dict(data)
        
        assert entry.user_id == "system", "缺少user_id时应使用默认值'system'"
    
    def test_audit_entry_round_trip(self):
        """测试AuditEntry的序列化和反序列化往返"""
        original = AuditEntry(
            timestamp=datetime.now(),
            event_type=AuditEventType.ALERT_TRIGGERED,
            data={"alert_type": "margin_call", "severity": "high"},
            audit_signature="sig_alert",
            user_id="system",
        )
        
        # 序列化后反序列化
        data = original.to_dict()
        restored = AuditEntry.from_dict(data)
        
        assert restored.event_type == original.event_type
        assert restored.user_id == original.user_id
        assert restored.data == original.data
        assert restored.audit_signature == original.audit_signature


class TestShadowLedgerEntryHelpers:
    """ShadowLedgerEntry辅助方法测试
    
    白皮书依据: 第七章 7.2.2 影子账本
    Requirements: 7.2.2
    
    验证：
    1. to_dict方法正确序列化
    2. from_dict方法正确反序列化
    """
    
    def test_shadow_ledger_entry_to_dict(self):
        """测试ShadowLedgerEntry的to_dict方法"""
        timestamp = datetime(2024, 1, 1, 10, 0, 0)
        entry = ShadowLedgerEntry(
            symbol="000001.SZ",
            quantity=100,
            avg_cost=10.50,
            last_sync=timestamp,
        )
        
        data = entry.to_dict()
        
        assert data["symbol"] == "000001.SZ"
        assert data["quantity"] == 100
        assert data["avg_cost"] == 10.50
        assert "last_sync" in data
    
    def test_shadow_ledger_entry_from_dict(self):
        """测试ShadowLedgerEntry的from_dict方法"""
        data = {
            "symbol": "600000.SH",
            "quantity": 200,
            "avg_cost": 15.75,
            "last_sync": "2024-01-01T10:00:00",
        }
        
        entry = ShadowLedgerEntry.from_dict(data)
        
        assert entry.symbol == "600000.SH"
        assert entry.quantity == 200
        assert entry.avg_cost == 15.75
        assert isinstance(entry.last_sync, datetime)
    
    def test_shadow_ledger_entry_round_trip(self):
        """测试ShadowLedgerEntry的序列化和反序列化往返"""
        original = ShadowLedgerEntry(
            symbol="000002.SZ",
            quantity=500,
            avg_cost=20.00,
            last_sync=datetime.now(),
        )
        
        # 序列化后反序列化
        data = original.to_dict()
        restored = ShadowLedgerEntry.from_dict(data)
        
        assert restored.symbol == original.symbol
        assert restored.quantity == original.quantity
        assert restored.avg_cost == original.avg_cost


class TestJWTPayloadHelpers:
    """JWTPayload辅助方法测试
    
    白皮书依据: 第七章 7.3.1 认证管理
    Requirements: 7.3.1
    
    验证：
    1. to_dict方法正确序列化
    2. from_dict方法正确反序列化
    """
    
    def test_jwt_payload_to_dict(self):
        """测试JWTPayload的to_dict方法"""
        exp_time = datetime.now() + timedelta(hours=1)
        iat_time = datetime.now()
        payload = JWTPayload(
            user_id="trader1",
            role=UserRole.ADMIN,
            exp=exp_time,
            iat=iat_time,
        )
        
        data = payload.to_dict()
        
        assert data["user_id"] == "trader1"
        assert data["role"] == "admin"
        assert "exp" in data
        assert "iat" in data
    
    def test_jwt_payload_from_dict(self):
        """测试JWTPayload的from_dict方法"""
        exp_timestamp = (datetime.now() + timedelta(hours=1)).timestamp()
        iat_timestamp = datetime.now().timestamp()
        
        data = {
            "user_id": "viewer1",
            "role": "guest",
            "exp": exp_timestamp,
            "iat": iat_timestamp,
        }
        
        payload = JWTPayload.from_dict(data)
        
        assert payload.user_id == "viewer1"
        assert payload.role == UserRole.GUEST
        assert isinstance(payload.exp, datetime)
        assert isinstance(payload.iat, datetime)
    
    def test_jwt_payload_round_trip(self):
        """测试JWTPayload的序列化和反序列化往返"""
        original = JWTPayload(
            user_id="system",
            role=UserRole.ADMIN,
            exp=datetime.now() + timedelta(hours=2),
            iat=datetime.now(),
        )
        
        # 序列化后反序列化
        data = original.to_dict()
        restored = JWTPayload.from_dict(data)
        
        assert restored.user_id == original.user_id
        assert restored.role == original.role


class TestTokenPayloadHelpers:
    """TokenPayload辅助方法测试
    
    白皮书依据: 第七章 7.3.1 认证管理
    Requirements: 7.3.1
    
    验证：
    1. to_dict方法正确序列化
    2. from_dict方法正确反序列化
    3. is_admin方法正确判断
    4. is_expired方法正确判断
    """
    
    def test_token_payload_to_dict_without_nbf(self):
        """测试TokenPayload的to_dict方法 - 无nbf"""
        exp_time = datetime.now(timezone.utc) + timedelta(hours=1)
        iat_time = datetime.now(timezone.utc)
        
        payload = TokenPayload(
            user_id="user123",
            role="admin",
            exp=exp_time,
            iat=iat_time,
        )
        
        data = payload.to_dict()
        
        assert data["user_id"] == "user123"
        assert data["role"] == "admin"
        assert "exp" in data
        assert "iat" in data
        assert "nbf" not in data
    
    def test_token_payload_to_dict_with_nbf(self):
        """测试TokenPayload的to_dict方法 - 有nbf"""
        exp_time = datetime.now(timezone.utc) + timedelta(hours=1)
        iat_time = datetime.now(timezone.utc)
        nbf_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        payload = TokenPayload(
            user_id="user123",
            role="guest",
            exp=exp_time,
            iat=iat_time,
            nbf=nbf_time,
        )
        
        data = payload.to_dict()
        
        assert "nbf" in data
        assert data["nbf"] == nbf_time.timestamp()
    
    def test_token_payload_to_dict_with_additional_claims(self):
        """测试TokenPayload的to_dict方法 - 有额外声明"""
        exp_time = datetime.now(timezone.utc) + timedelta(hours=1)
        iat_time = datetime.now(timezone.utc)
        
        payload = TokenPayload(
            user_id="user123",
            role="admin",
            exp=exp_time,
            iat=iat_time,
            additional_claims={"custom_field": "custom_value", "level": 5},
        )
        
        data = payload.to_dict()
        
        assert data["custom_field"] == "custom_value"
        assert data["level"] == 5
    
    def test_token_payload_from_dict_without_nbf(self):
        """测试TokenPayload的from_dict方法 - 无nbf"""
        exp_timestamp = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        iat_timestamp = datetime.now(timezone.utc).timestamp()
        
        data = {
            "user_id": "viewer1",
            "role": "guest",
            "exp": exp_timestamp,
            "iat": iat_timestamp,
        }
        
        payload = TokenPayload.from_dict(data)
        
        assert payload.user_id == "viewer1"
        assert payload.role == "guest"
        assert payload.nbf is None
    
    def test_token_payload_from_dict_with_nbf(self):
        """测试TokenPayload的from_dict方法 - 有nbf"""
        exp_timestamp = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        iat_timestamp = datetime.now(timezone.utc).timestamp()
        nbf_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()
        
        data = {
            "user_id": "viewer1",
            "role": "admin",
            "exp": exp_timestamp,
            "iat": iat_timestamp,
            "nbf": nbf_timestamp,
        }
        
        payload = TokenPayload.from_dict(data)
        
        assert payload.nbf is not None
        assert isinstance(payload.nbf, datetime)
    
    def test_token_payload_from_dict_with_additional_claims(self):
        """测试TokenPayload的from_dict方法 - 有额外声明"""
        exp_timestamp = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
        iat_timestamp = datetime.now(timezone.utc).timestamp()
        
        data = {
            "user_id": "viewer1",
            "role": "guest",
            "exp": exp_timestamp,
            "iat": iat_timestamp,
            "custom_field": "custom_value",
            "level": 5,
        }
        
        payload = TokenPayload.from_dict(data)
        
        assert payload.additional_claims["custom_field"] == "custom_value"
        assert payload.additional_claims["level"] == 5
    
    def test_token_payload_is_admin_true(self):
        """测试TokenPayload的is_admin方法 - 管理员"""
        payload = TokenPayload(
            user_id="admin",
            role=UserRole.ADMIN.value,
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
        )
        
        assert payload.is_admin() is True
    
    def test_token_payload_is_admin_false(self):
        """测试TokenPayload的is_admin方法 - 非管理员"""
        payload = TokenPayload(
            user_id="trader1",
            role="guest",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
        )
        
        assert payload.is_admin() is False
    
    def test_token_payload_is_expired_false(self):
        """测试TokenPayload的is_expired方法 - 未过期"""
        payload = TokenPayload(
            user_id="user123",
            role="admin",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
        )
        
        assert payload.is_expired() is False
    
    def test_token_payload_is_expired_true(self):
        """测试TokenPayload的is_expired方法 - 已过期"""
        payload = TokenPayload(
            user_id="user123",
            role="guest",
            exp=datetime.now(timezone.utc) - timedelta(hours=1),  # 1小时前过期
            iat=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        
        assert payload.is_expired() is True
    
    def test_token_payload_round_trip(self):
        """测试TokenPayload的序列化和反序列化往返"""
        original = TokenPayload(
            user_id="system",
            role=UserRole.ADMIN.value,
            exp=datetime.now(timezone.utc) + timedelta(hours=2),
            iat=datetime.now(timezone.utc),
            nbf=datetime.now(timezone.utc) - timedelta(minutes=5),
            additional_claims={"custom": "value"},
        )
        
        # 序列化后反序列化
        data = original.to_dict()
        restored = TokenPayload.from_dict(data)
        
        assert restored.user_id == original.user_id
        assert restored.role == original.role
        assert restored.additional_claims == original.additional_claims


class TestEncryptedAPIKey:
    """EncryptedAPIKey测试
    
    白皮书依据: 第七章 7.1.1 API Key加密存储
    Requirements: 7.1.1
    
    验证：
    1. 数据类正确创建
    """
    
    def test_encrypted_api_key_creation(self):
        """测试EncryptedAPIKey创建"""
        created_time = datetime.now()
        key = EncryptedAPIKey(
            key_name="broker_api_key",
            encrypted_value="encrypted_value_123",
            created_at=created_time,
        )
        
        assert key.key_name == "broker_api_key"
        assert key.encrypted_value == "encrypted_value_123"
        assert key.created_at == created_time


class TestDataModelsEdgeCases:
    """数据模型边界条件测试
    
    白皮书依据: 第七章 7.2 & 7.3
    Requirements: 7.2.1, 7.3.1
    
    验证：
    1. 空值处理
    2. 特殊字符处理
    3. 大数值处理
    """
    
    def test_audit_entry_with_empty_data(self):
        """测试AuditEntry空数据"""
        entry = AuditEntry(
            timestamp=datetime.now(),
            event_type=AuditEventType.USER_LOGIN,
            data={},
            audit_signature="sig_empty",
            user_id="user123",
        )
        
        data = entry.to_dict()
        restored = AuditEntry.from_dict(data)
        
        assert restored.data == {}
    
    def test_audit_entry_with_special_characters(self):
        """测试AuditEntry特殊字符"""
        entry = AuditEntry(
            timestamp=datetime.now(),
            event_type=AuditEventType.CONFIG_CHANGE,
            data={"message": "测试中文\\n换行\\t制表符"},
            audit_signature="sig_special",
            user_id="user@example.com",
        )
        
        data = entry.to_dict()
        restored = AuditEntry.from_dict(data)
        
        assert restored.user_id == "user@example.com"
        assert "测试中文" in restored.data["message"]
    
    def test_shadow_ledger_entry_with_large_quantity(self):
        """测试ShadowLedgerEntry大数量"""
        entry = ShadowLedgerEntry(
            symbol="000001.SZ",
            quantity=1000000000,  # 10亿股
            avg_cost=0.01,
            last_sync=datetime.now(),
        )
        
        data = entry.to_dict()
        restored = ShadowLedgerEntry.from_dict(data)
        
        assert restored.quantity == 1000000000
    
    def test_token_payload_with_empty_additional_claims(self):
        """测试TokenPayload空额外声明"""
        payload = TokenPayload(
            user_id="user123",
            role="admin",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            additional_claims={},
        )
        
        data = payload.to_dict()
        
        # 空的additional_claims不应该添加额外字段
        assert "user_id" in data
        assert "role" in data
        assert "exp" in data
        assert "iat" in data
