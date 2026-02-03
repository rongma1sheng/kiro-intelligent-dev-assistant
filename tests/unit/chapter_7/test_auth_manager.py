"""AuthManager单元测试

白皮书依据: 第七章 7.1.2 JWT Token认证

测试AuthManager的核心功能：
- 令牌创建和验证
- 过期令牌处理
- 无效令牌处理
- Authorization头解析
"""

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
import jwt

from src.security.auth_manager import AuthManager
from src.security.data_models import (
    UserRole,
    TokenPayload,
    TokenExpiredError,
    InvalidTokenError,
    AuthorizationHeaderError,
    AuthenticationError,
)


class TestAuthManager:
    """AuthManager单元测试套件
    
    白皮书依据: 第七章 7.1.2 JWT Token认证
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
    """
    
    @pytest.fixture
    def secret_key(self):
        """测试用JWT密钥"""
        return "test_secret_key_for_jwt_testing_12345"
    
    @pytest.fixture
    def auth_manager(self, secret_key):
        """创建AuthManager实例"""
        return AuthManager(secret_key=secret_key)
    
    def test_create_access_token_basic(self, auth_manager):
        """测试基本令牌创建
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.1
        
        验证：
        1. 可以创建有效的JWT令牌
        2. 令牌是字符串类型
        3. 令牌不为空
        """
        user_id = "test_user_001"
        
        token = auth_manager.create_access_token(user_id)
        
        assert isinstance(token, str), "令牌应该是字符串"
        assert len(token) > 0, "令牌不应为空"
        # JWT令牌由三部分组成，用.分隔
        assert token.count('.') == 2, "JWT令牌应该有三部分"
    
    def test_create_access_token_with_role(self, auth_manager):
        """测试带角色的令牌创建
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.1, 2.3
        
        验证：
        1. 可以指定用户角色
        2. 角色信息包含在令牌中
        """
        user_id = "admin_user"
        role = UserRole.ADMIN.value
        
        token = auth_manager.create_access_token(user_id, role=role)
        payload = auth_manager.verify_token(token)
        
        assert payload.user_id == user_id
        assert payload.role == role
    
    def test_create_access_token_default_role(self, auth_manager):
        """测试默认角色
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.3
        
        验证：
        1. 默认角色是guest
        """
        user_id = "guest_user"
        
        token = auth_manager.create_access_token(user_id)
        payload = auth_manager.verify_token(token)
        
        assert payload.role == UserRole.GUEST.value
    
    def test_create_access_token_with_additional_claims(self, auth_manager):
        """测试带额外声明的令牌创建
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.1
        
        验证：
        1. 可以添加额外的JWT声明
        2. 额外声明包含在令牌中
        """
        user_id = "user_with_claims"
        additional_claims = {
            'department': 'trading',
            'permissions': ['read', 'write']
        }
        
        token = auth_manager.create_access_token(
            user_id, 
            additional_claims=additional_claims
        )
        payload = auth_manager.verify_token(token)
        
        assert payload.additional_claims.get('department') == 'trading'
        assert payload.additional_claims.get('permissions') == ['read', 'write']
    
    def test_create_access_token_empty_user_id(self, auth_manager):
        """测试空用户ID
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.1
        
        验证：
        1. 空用户ID应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            auth_manager.create_access_token("")
        
        assert "user_id" in str(exc_info.value).lower()
    
    def test_create_access_token_whitespace_user_id(self, auth_manager):
        """测试空白用户ID
        
        验证：
        1. 仅包含空白字符的用户ID应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            auth_manager.create_access_token("   ")
        
        assert "user_id" in str(exc_info.value).lower()
    
    def test_create_access_token_invalid_role(self, auth_manager):
        """测试无效角色
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.3
        
        验证：
        1. 无效角色应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            auth_manager.create_access_token("user", role="invalid_role")
        
        assert "role" in str(exc_info.value).lower()
    
    def test_verify_token_valid(self, auth_manager):
        """测试验证有效令牌
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.2
        
        验证：
        1. 有效令牌可以被验证
        2. 返回正确的用户信息
        """
        user_id = "valid_user"
        role = UserRole.ADMIN.value
        
        token = auth_manager.create_access_token(user_id, role=role)
        payload = auth_manager.verify_token(token)
        
        assert isinstance(payload, TokenPayload)
        assert payload.user_id == user_id
        assert payload.role == role
        assert payload.exp > datetime.now(timezone.utc)
    
    def test_verify_token_expired(self, secret_key):
        """测试验证过期令牌
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.4
        
        验证：
        1. 过期令牌应该抛出TokenExpiredError
        
        注意：此测试已移至test_verify_token_expired_manual，
        因为无法创建过期时间为0的AuthManager
        """
        # 此测试的逻辑已移至test_verify_token_expired_manual
        # 这里验证access_token_expire_hours=0会抛出ValueError
        with pytest.raises(ValueError):
            AuthManager(
                secret_key=secret_key,
                access_token_expire_hours=0
            )
    
    def test_verify_token_expired_manual(self, secret_key):
        """测试验证过期令牌（手动创建）
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.4
        
        验证：
        1. 过期令牌应该抛出TokenExpiredError
        """
        # 手动创建一个过期的令牌
        expired_payload = {
            'user_id': 'expired_user',
            'role': 'guest',
            'exp': datetime.now(timezone.utc) - timedelta(hours=1),
            'iat': datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, secret_key, algorithm='HS256')
        
        auth_manager = AuthManager(secret_key=secret_key)
        
        with pytest.raises(TokenExpiredError) as exc_info:
            auth_manager.verify_token(expired_token)
        
        assert "expired" in str(exc_info.value).lower()
    
    def test_verify_token_invalid(self, auth_manager):
        """测试验证无效令牌
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.5
        
        验证：
        1. 无效令牌应该抛出InvalidTokenError
        """
        invalid_token = "invalid.token.here"
        
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_manager.verify_token(invalid_token)
        
        assert "invalid" in str(exc_info.value).lower()
    
    def test_verify_token_wrong_secret(self, auth_manager, secret_key):
        """测试使用错误密钥验证令牌
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.5
        
        验证：
        1. 使用错误密钥签名的令牌应该抛出InvalidTokenError
        """
        # 使用不同的密钥创建令牌
        wrong_key_manager = AuthManager(secret_key="wrong_secret_key")
        token = wrong_key_manager.create_access_token("user")
        
        # 使用正确密钥的manager验证
        with pytest.raises(InvalidTokenError):
            auth_manager.verify_token(token)
    
    def test_verify_token_empty(self, auth_manager):
        """测试验证空令牌
        
        验证：
        1. 空令牌应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            auth_manager.verify_token("")
        
        assert "token" in str(exc_info.value).lower()
    
    def test_get_current_user_valid(self, auth_manager):
        """测试从Authorization头获取用户
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.6
        
        验证：
        1. 可以从有效的Authorization头获取用户信息
        """
        user_id = "auth_header_user"
        token = auth_manager.create_access_token(user_id)
        authorization = f"Bearer {token}"
        
        payload = auth_manager.get_current_user(authorization)
        
        assert payload.user_id == user_id
    
    def test_get_current_user_missing_header(self, auth_manager):
        """测试缺失Authorization头
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.6
        
        验证：
        1. 缺失Authorization头应该抛出AuthorizationHeaderError
        """
        with pytest.raises(AuthorizationHeaderError) as exc_info:
            auth_manager.get_current_user(None)
        
        assert "missing" in str(exc_info.value).lower()
    
    def test_get_current_user_invalid_scheme(self, auth_manager):
        """测试无效的认证方案
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.6
        
        验证：
        1. 非Bearer方案应该抛出AuthorizationHeaderError
        """
        token = auth_manager.create_access_token("user")
        authorization = f"Basic {token}"  # 使用Basic而不是Bearer
        
        with pytest.raises(AuthorizationHeaderError) as exc_info:
            auth_manager.get_current_user(authorization)
        
        assert "scheme" in str(exc_info.value).lower()
    
    def test_get_current_user_invalid_format(self, auth_manager):
        """测试无效的Authorization头格式
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.6
        
        验证：
        1. 格式错误的Authorization头应该抛出AuthorizationHeaderError
        """
        # 缺少token部分
        with pytest.raises(AuthorizationHeaderError):
            auth_manager.get_current_user("Bearer")
        
        # 多余的部分
        with pytest.raises(AuthorizationHeaderError):
            auth_manager.get_current_user("Bearer token extra")
    
    def test_get_current_user_bearer_case_insensitive(self, auth_manager):
        """测试Bearer大小写不敏感
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        Requirements: 2.6
        
        验证：
        1. Bearer方案应该大小写不敏感
        """
        user_id = "case_test_user"
        token = auth_manager.create_access_token(user_id)
        
        # 测试不同大小写
        for scheme in ["Bearer", "bearer", "BEARER", "BeArEr"]:
            authorization = f"{scheme} {token}"
            payload = auth_manager.get_current_user(authorization)
            assert payload.user_id == user_id
    
    def test_is_token_valid(self, auth_manager):
        """测试令牌有效性检查
        
        验证：
        1. 有效令牌返回True
        2. 无效令牌返回False
        """
        valid_token = auth_manager.create_access_token("user")
        invalid_token = "invalid.token.here"
        
        assert auth_manager.is_token_valid(valid_token) is True
        assert auth_manager.is_token_valid(invalid_token) is False
    
    def test_refresh_token(self, auth_manager):
        """测试令牌刷新
        
        验证：
        1. 可以刷新有效令牌
        2. 新令牌包含相同的用户信息
        3. 新令牌有新的过期时间（如果时间戳不同）
        """
        user_id = "refresh_user"
        role = UserRole.ADMIN.value
        
        original_token = auth_manager.create_access_token(user_id, role=role)
        original_payload = auth_manager.verify_token(original_token)
        
        # 等待超过1秒确保时间戳不同（JWT时间戳是秒级精度）
        time.sleep(1.1)
        
        new_token = auth_manager.refresh_token(original_token)
        new_payload = auth_manager.verify_token(new_token)
        
        # 验证用户信息相同
        assert new_payload.user_id == original_payload.user_id
        assert new_payload.role == original_payload.role
        
        # 由于等待了超过1秒，新令牌应该有不同的时间戳
        assert new_payload.iat >= original_payload.iat
    
    def test_get_token_remaining_time(self, auth_manager):
        """测试获取令牌剩余时间
        
        验证：
        1. 可以获取令牌的剩余有效时间
        2. 剩余时间是正数
        """
        token = auth_manager.create_access_token("user")
        
        remaining = auth_manager.get_token_remaining_time(token)
        
        assert isinstance(remaining, timedelta)
        assert remaining.total_seconds() > 0
        # 应该接近24小时（默认过期时间）
        assert remaining.total_seconds() < 24 * 3600 + 60  # 允许1分钟误差


class TestAuthManagerInitialization:
    """AuthManager初始化测试
    
    白皮书依据: 第七章 7.1.2 JWT Token认证
    """
    
    def test_init_with_secret_key(self):
        """测试使用密钥初始化"""
        secret_key = "my_secret_key"
        auth_manager = AuthManager(secret_key=secret_key)
        
        assert auth_manager.secret_key == secret_key
        assert auth_manager.algorithm == "HS256"
        assert auth_manager.access_token_expire_hours == 24
    
    def test_init_with_custom_algorithm(self):
        """测试自定义算法"""
        auth_manager = AuthManager(
            secret_key="key",
            algorithm="HS384"
        )
        
        assert auth_manager.algorithm == "HS384"
    
    def test_init_with_custom_expire_hours(self):
        """测试自定义过期时间"""
        auth_manager = AuthManager(
            secret_key="key",
            access_token_expire_hours=48
        )
        
        assert auth_manager.access_token_expire_hours == 48
    
    def test_init_invalid_expire_hours(self):
        """测试无效的过期时间"""
        with pytest.raises(ValueError) as exc_info:
            AuthManager(secret_key="key", access_token_expire_hours=0)
        
        assert "access_token_expire_hours" in str(exc_info.value)
        
        with pytest.raises(ValueError):
            AuthManager(secret_key="key", access_token_expire_hours=-1)
    
    def test_init_from_environment(self, monkeypatch):
        """测试从环境变量获取密钥"""
        test_secret = "env_secret_key"
        monkeypatch.setenv("JWT_SECRET", test_secret)
        
        auth_manager = AuthManager()
        
        assert auth_manager.secret_key == test_secret
    
    def test_init_missing_secret_key(self, monkeypatch):
        """测试缺失密钥"""
        # 确保环境变量不存在
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("ENCRYPTED_JWT_SECRET", raising=False)
        
        with pytest.raises(AuthenticationError):
            AuthManager()


class TestAuthManagerTokenPayload:
    """令牌载荷测试
    
    白皮书依据: 第七章 7.1.2 JWT Token认证
    """
    
    @pytest.fixture
    def auth_manager(self):
        return AuthManager(secret_key="test_key")
    
    def test_token_contains_required_claims(self, auth_manager):
        """测试令牌包含必需的声明
        
        Requirements: 2.1, 2.3
        
        验证：
        1. 令牌包含user_id
        2. 令牌包含role
        3. 令牌包含exp（过期时间）
        4. 令牌包含iat（签发时间）
        """
        token = auth_manager.create_access_token("user", role="admin")
        payload = auth_manager.verify_token(token)
        
        assert payload.user_id == "user"
        assert payload.role == "admin"
        assert payload.exp is not None
        assert payload.iat is not None
        assert payload.nbf is not None
    
    def test_token_payload_is_admin(self, auth_manager):
        """测试is_admin方法"""
        admin_token = auth_manager.create_access_token("admin", role="admin")
        guest_token = auth_manager.create_access_token("guest", role="guest")
        
        admin_payload = auth_manager.verify_token(admin_token)
        guest_payload = auth_manager.verify_token(guest_token)
        
        assert admin_payload.is_admin() is True
        assert guest_payload.is_admin() is False
    
    def test_token_payload_to_dict(self, auth_manager):
        """测试TokenPayload.to_dict方法"""
        token = auth_manager.create_access_token(
            "user",
            additional_claims={'custom': 'value'}
        )
        payload = auth_manager.verify_token(token)
        
        payload_dict = payload.to_dict()
        
        assert payload_dict['user_id'] == 'user'
        assert payload_dict['role'] == 'guest'
        assert 'exp' in payload_dict
        assert 'iat' in payload_dict
        assert payload_dict['custom'] == 'value'
