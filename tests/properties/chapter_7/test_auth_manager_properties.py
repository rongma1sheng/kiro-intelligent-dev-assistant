"""AuthManager属性测试

白皮书依据: 第七章 7.1.2 JWT Token认证

Property 2: JWT Token Claims Completeness
- 对于任意有效的用户ID和角色，创建的令牌必须包含所有必需的声明
- 令牌必须可以被正确验证并返回原始信息

Validates: Requirements 2.1, 2.3
"""

from datetime import datetime, timezone

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.security.auth_manager import AuthManager
from src.security.data_models import UserRole, TokenPayload


class TestAuthManagerProperties:
    """AuthManager属性测试套件
    
    白皮书依据: 第七章 7.1.2 JWT Token认证
    """
    
    @pytest.fixture(scope="class")
    def auth_manager(self):
        """创建AuthManager实例（类级别共享以提高性能）"""
        return AuthManager(secret_key="test_property_secret_key_12345")
    
    @given(
        user_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'P')),
            min_size=1,
            max_size=100
        ).filter(lambda x: x.strip()),
        role=st.sampled_from([UserRole.ADMIN.value, UserRole.GUEST.value])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_jwt_token_claims_completeness(
        self, 
        user_id: str, 
        role: str, 
        auth_manager
    ):
        """Property 2: JWT Token Claims Completeness
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        **Validates: Requirements 2.1, 2.3**
        
        属性定义:
        ∀ user_id ∈ NonEmptyString, role ∈ {admin, guest}:
            let token = create_access_token(user_id, role)
            let payload = verify_token(token)
            payload.user_id == user_id ∧
            payload.role == role ∧
            payload.exp > now ∧
            payload.iat <= now ∧
            payload.nbf <= now
        
        验证:
        1. 创建的令牌包含正确的user_id
        2. 创建的令牌包含正确的role
        3. 令牌有有效的过期时间（未来）
        4. 令牌有有效的签发时间（过去或现在）
        5. 令牌有有效的生效时间（过去或现在）
        """
        # 前置条件
        assume(len(user_id.strip()) > 0)
        
        # 创建令牌
        token = auth_manager.create_access_token(user_id.strip(), role=role)
        
        # 验证令牌
        payload = auth_manager.verify_token(token)
        
        # 验证声明完整性
        now = datetime.now(timezone.utc)
        
        # 1. user_id正确
        assert payload.user_id == user_id.strip(), \
            f"user_id不匹配: expected={user_id.strip()}, got={payload.user_id}"
        
        # 2. role正确
        assert payload.role == role, \
            f"role不匹配: expected={role}, got={payload.role}"
        
        # 3. exp在未来
        assert payload.exp > now, \
            f"exp应该在未来: exp={payload.exp}, now={now}"
        
        # 4. iat在过去或现在
        assert payload.iat <= now, \
            f"iat应该在过去或现在: iat={payload.iat}, now={now}"
        
        # 5. nbf在过去或现在（如果存在）
        if payload.nbf:
            assert payload.nbf <= now, \
                f"nbf应该在过去或现在: nbf={payload.nbf}, now={now}"
    
    @given(
        user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        additional_claims=st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=('L',)),
                min_size=1,
                max_size=20
            ).filter(lambda x: x not in ('user_id', 'role', 'exp', 'iat', 'nbf')),
            values=st.one_of(
                st.text(max_size=50),
                st.integers(min_value=-1000, max_value=1000),
                st.booleans()
            ),
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_additional_claims_preserved(
        self,
        user_id: str,
        additional_claims: dict,
        auth_manager
    ):
        """Property 2b: Additional Claims Preserved
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        **Validates: Requirements 2.1**
        
        属性定义:
        ∀ user_id ∈ NonEmptyString, claims ∈ Dict:
            let token = create_access_token(user_id, additional_claims=claims)
            let payload = verify_token(token)
            ∀ (k, v) ∈ claims: payload.additional_claims[k] == v
        
        验证:
        1. 额外声明被正确保存在令牌中
        2. 额外声明可以被正确恢复
        """
        assume(len(user_id.strip()) > 0)
        
        # 创建带额外声明的令牌
        token = auth_manager.create_access_token(
            user_id.strip(),
            additional_claims=additional_claims
        )
        
        # 验证令牌
        payload = auth_manager.verify_token(token)
        
        # 验证额外声明
        for key, value in additional_claims.items():
            assert key in payload.additional_claims, \
                f"额外声明缺失: {key}"
            assert payload.additional_claims[key] == value, \
                f"额外声明值不匹配: key={key}, expected={value}, got={payload.additional_claims[key]}"
    
    @given(user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    @settings(max_examples=30, deadline=None)
    def test_property_token_verification_idempotent(
        self,
        user_id: str,
        auth_manager
    ):
        """Property 2c: Token Verification Idempotent
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        **Validates: Requirements 2.2**
        
        属性定义:
        ∀ token ∈ ValidToken:
            verify_token(token) == verify_token(token)
        
        验证:
        1. 多次验证同一令牌返回相同结果
        """
        assume(len(user_id.strip()) > 0)
        
        token = auth_manager.create_access_token(user_id.strip())
        
        # 多次验证
        payload1 = auth_manager.verify_token(token)
        payload2 = auth_manager.verify_token(token)
        payload3 = auth_manager.verify_token(token)
        
        # 验证结果相同
        assert payload1.user_id == payload2.user_id == payload3.user_id
        assert payload1.role == payload2.role == payload3.role
        assert payload1.exp == payload2.exp == payload3.exp
        assert payload1.iat == payload2.iat == payload3.iat
    
    @given(
        user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        role=st.sampled_from([UserRole.ADMIN.value, UserRole.GUEST.value])
    )
    @settings(max_examples=30, deadline=None)
    def test_property_authorization_header_round_trip(
        self,
        user_id: str,
        role: str,
        auth_manager
    ):
        """Property 2d: Authorization Header Round-Trip
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        **Validates: Requirements 2.6**
        
        属性定义:
        ∀ user_id ∈ NonEmptyString, role ∈ {admin, guest}:
            let token = create_access_token(user_id, role)
            let header = "Bearer " + token
            let payload = get_current_user(header)
            payload.user_id == user_id ∧ payload.role == role
        
        验证:
        1. 通过Authorization头可以正确获取用户信息
        """
        assume(len(user_id.strip()) > 0)
        
        # 创建令牌
        token = auth_manager.create_access_token(user_id.strip(), role=role)
        
        # 构建Authorization头
        authorization = f"Bearer {token}"
        
        # 获取用户
        payload = auth_manager.get_current_user(authorization)
        
        # 验证
        assert payload.user_id == user_id.strip()
        assert payload.role == role


class TestAuthManagerSecurityProperties:
    """AuthManager安全属性测试
    
    白皮书依据: 第七章 7.1.2 JWT Token认证
    """
    
    @pytest.fixture(scope="class")
    def auth_manager(self):
        return AuthManager(secret_key="security_test_key_12345")
    
    @given(user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    @settings(max_examples=20, deadline=None)
    def test_property_different_secrets_produce_incompatible_tokens(
        self,
        user_id: str
    ):
        """Property 2e: Different Secrets Produce Incompatible Tokens
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        **Validates: Requirements 2.5**
        
        属性定义:
        ∀ user_id ∈ NonEmptyString, secret1 ≠ secret2:
            let manager1 = AuthManager(secret1)
            let manager2 = AuthManager(secret2)
            let token = manager1.create_access_token(user_id)
            manager2.verify_token(token) raises InvalidTokenError
        
        验证:
        1. 使用不同密钥创建的令牌不能被其他密钥验证
        """
        assume(len(user_id.strip()) > 0)
        
        manager1 = AuthManager(secret_key="secret_key_1_abc123")
        manager2 = AuthManager(secret_key="secret_key_2_xyz789")
        
        # 使用manager1创建令牌
        token = manager1.create_access_token(user_id.strip())
        
        # manager1可以验证
        payload = manager1.verify_token(token)
        assert payload.user_id == user_id.strip()
        
        # manager2不能验证
        from src.security.data_models import InvalidTokenError
        with pytest.raises(InvalidTokenError):
            manager2.verify_token(token)
    
    @given(user_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    @settings(max_examples=20, deadline=None)
    def test_property_token_validity_check_consistent(
        self,
        user_id: str,
        auth_manager
    ):
        """Property 2f: Token Validity Check Consistent
        
        白皮书依据: 第七章 7.1.2 JWT Token认证
        **Validates: Requirements 2.2**
        
        属性定义:
        ∀ token ∈ String:
            is_token_valid(token) == (verify_token(token) does not raise)
        
        验证:
        1. is_token_valid与verify_token的结果一致
        """
        assume(len(user_id.strip()) > 0)
        
        valid_token = auth_manager.create_access_token(user_id.strip())
        invalid_token = "invalid.token.here"
        
        # 有效令牌
        assert auth_manager.is_token_valid(valid_token) is True
        try:
            auth_manager.verify_token(valid_token)
            verify_succeeded = True
        except:
            verify_succeeded = False
        assert verify_succeeded is True
        
        # 无效令牌
        assert auth_manager.is_token_valid(invalid_token) is False
        try:
            auth_manager.verify_token(invalid_token)
            verify_succeeded = True
        except:
            verify_succeeded = False
        assert verify_succeeded is False
