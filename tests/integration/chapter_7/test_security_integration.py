"""Security Components Integration Tests

白皮书依据: 第七章 安全、审计与交互

测试安全组件之间的集成：
- SecureConfig → AuthManager集成
- AuthManager → API端点集成
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import time

from src.security.secure_config import SecureConfig
from src.security.auth_manager import AuthManager
from src.security.data_models import (
    AuthorizationHeaderError,
    TokenExpiredError,
    InvalidTokenError
)


class TestSecureConfigAuthManagerIntegration:
    """SecureConfig → AuthManager集成测试
    
    白皮书依据: 第七章 6.1 安全基础
    验证需求: Requirements 1.4, 2.1
    """
    
    @pytest.fixture
    def temp_key_file(self, tmp_path):
        """临时密钥文件fixture"""
        key_file = tmp_path / ".master.key"
        return key_file
    
    @pytest.fixture
    def secure_config(self, temp_key_file):
        """SecureConfig实例fixture"""
        return SecureConfig(key_file_path=str(temp_key_file))
    
    def test_auth_manager_uses_secure_config_key(self, secure_config, temp_key_file):
        """测试AuthManager使用SecureConfig加密的JWT密钥
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        验证需求: Requirements 1.4, 2.1
        
        集成流程：
        1. SecureConfig加密JWT密钥
        2. AuthManager从SecureConfig获取解密后的密钥
        3. AuthManager使用该密钥创建和验证令牌
        """
        # 1. 使用SecureConfig加密JWT密钥
        jwt_secret = "test_jwt_secret_key_12345"
        encrypted_key = secure_config.encrypt_api_key(jwt_secret)
        
        # 模拟环境变量
        with patch.dict(os.environ, {'ENCRYPTED_JWT_SECRET': encrypted_key}):
            # 2. AuthManager从SecureConfig获取密钥
            with patch('src.security.auth_manager.SecureConfig', return_value=secure_config):
                auth_manager = AuthManager()
                
                # 3. 验证AuthManager可以正常创建和验证令牌
                token = auth_manager.create_access_token(
                    user_id="test_user",
                    role="admin"
                )
                
                assert token is not None
                assert isinstance(token, str)
                
                # 验证令牌
                payload = auth_manager.verify_token(token)
                assert payload.user_id == "test_user"
                assert payload.role == "admin"
    
    def test_secure_config_key_rotation(self, temp_key_file):
        """测试密钥轮换场景
        
        白皮书依据: 第七章 6.1.1 API Key加密存储
        
        集成流程：
        1. 使用旧密钥加密
        2. 轮换主密钥
        3. 使用新密钥重新加密
        """
        # 1. 使用旧密钥
        old_config = SecureConfig(key_file_path=str(temp_key_file))
        jwt_secret = "test_jwt_secret"
        old_encrypted = old_config.encrypt_api_key(jwt_secret)
        
        # 验证旧密钥可以解密
        decrypted = old_config.decrypt_api_key(old_encrypted)
        assert decrypted == jwt_secret
        
        # 2. 模拟密钥轮换（删除旧密钥文件）
        temp_key_file.unlink()
        
        # 3. 创建新配置（生成新主密钥）
        new_config = SecureConfig(key_file_path=str(temp_key_file))
        new_encrypted = new_config.encrypt_api_key(jwt_secret)
        
        # 验证新密钥可以解密
        decrypted = new_config.decrypt_api_key(new_encrypted)
        assert decrypted == jwt_secret
        
        # 验证新旧加密结果不同
        assert old_encrypted != new_encrypted
    
    def test_multiple_api_keys_management(self, secure_config):
        """测试管理多个API密钥
        
        白皮书依据: 第七章 6.1.1 API Key加密存储
        
        集成流程：
        1. 加密多个不同的API密钥
        2. 从环境变量获取并解密
        3. 验证每个密钥都正确
        """
        # 1. 加密多个API密钥
        keys = {
            'JWT_SECRET': 'jwt_secret_12345',
            'BROKER_API_KEY': 'broker_key_67890',
            'DATA_API_KEY': 'data_key_abcde'
        }
        
        encrypted_keys = {}
        for key_name, key_value in keys.items():
            encrypted_keys[f'ENCRYPTED_{key_name}'] = secure_config.encrypt_api_key(key_value)
        
        # 2. 模拟环境变量并获取密钥
        with patch.dict(os.environ, encrypted_keys):
            for key_name, expected_value in keys.items():
                decrypted = secure_config.get_api_key(key_name)
                assert decrypted == expected_value


class TestAuthManagerAPIIntegration:
    """AuthManager → API端点集成测试
    
    白皮书依据: 第七章 6.1.2 JWT Token认证
    验证需求: Requirements 2.1
    """
    
    @pytest.fixture
    def auth_manager(self):
        """AuthManager实例fixture"""
        return AuthManager(secret_key="test_secret_key")
    
    def test_api_endpoint_authentication_flow(self, auth_manager):
        """测试API端点认证流程
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        验证需求: Requirements 2.1
        
        集成流程：
        1. 用户登录获取令牌
        2. 使用令牌访问受保护的API端点
        3. 验证用户身份
        """
        # 1. 模拟用户登录
        user_id = "test_user"
        role = "admin"
        token = auth_manager.create_access_token(user_id=user_id, role=role)
        
        # 2. 模拟API请求（带Authorization头）
        authorization_header = f"Bearer {token}"
        
        # 3. 验证用户身份
        user_info = auth_manager.get_current_user(authorization=authorization_header)
        
        assert user_info.user_id == user_id
        assert user_info.role == role
        assert user_info.exp is not None
        assert user_info.iat is not None
    
    def test_api_endpoint_invalid_token(self, auth_manager):
        """测试无效令牌被拒绝
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        验证需求: Requirements 2.5
        
        集成流程：
        1. 使用无效令牌访问API
        2. 验证被拒绝并抛出InvalidTokenError
        """
        # 使用无效令牌
        invalid_token = "invalid.token.here"
        authorization_header = f"Bearer {invalid_token}"
        
        # 验证被拒绝
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_manager.get_current_user(authorization=authorization_header)
        
        assert "Invalid token" in str(exc_info.value)
    
    def test_api_endpoint_expired_token(self, auth_manager):
        """测试过期令牌被拒绝
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        验证需求: Requirements 2.4
        
        集成流程：
        1. 创建短期令牌
        2. 等待令牌过期
        3. 验证被拒绝并抛出TokenExpiredError
        """
        # 创建短期令牌（1秒过期）
        short_lived_auth = AuthManager(
            secret_key="test_secret",
            access_token_expire_hours=1/3600  # 1秒
        )
        
        token = short_lived_auth.create_access_token(
            user_id="test_user",
            role="guest"
        )
        
        # 等待令牌过期
        time.sleep(2)
        
        # 验证被拒绝
        authorization_header = f"Bearer {token}"
        with pytest.raises(TokenExpiredError) as exc_info:
            short_lived_auth.get_current_user(authorization=authorization_header)
        
        assert "Token expired" in str(exc_info.value)
    
    def test_api_endpoint_missing_authorization(self, auth_manager):
        """测试缺少Authorization头
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        验证需求: Requirements 2.6
        
        集成流程：
        1. 不提供Authorization头访问API
        2. 验证被拒绝并抛出AuthorizationHeaderError
        """
        # 不提供Authorization头
        with pytest.raises(AuthorizationHeaderError) as exc_info:
            auth_manager.get_current_user(authorization=None)
        
        assert "Authorization header missing" in str(exc_info.value)
    
    def test_api_endpoint_invalid_bearer_scheme(self, auth_manager):
        """测试无效的Bearer scheme
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        验证需求: Requirements 2.6
        
        集成流程：
        1. 使用错误的认证scheme访问API
        2. 验证被拒绝并抛出AuthorizationHeaderError
        """
        # 使用错误的scheme
        token = auth_manager.create_access_token(user_id="test_user", role="guest")
        invalid_header = f"Basic {token}"  # 应该是Bearer
        
        with pytest.raises(AuthorizationHeaderError) as exc_info:
            auth_manager.get_current_user(authorization=invalid_header)
        
        assert "Invalid authentication scheme" in str(exc_info.value)
    
    def test_role_based_access_control(self, auth_manager):
        """测试基于角色的访问控制
        
        白皮书依据: 第七章 6.1.2 JWT Token认证
        
        集成流程：
        1. 创建不同角色的令牌
        2. 验证角色信息正确传递
        3. 模拟基于角色的权限检查
        """
        # 创建admin令牌
        admin_token = auth_manager.create_access_token(
            user_id="admin_user",
            role="admin"
        )
        
        # 创建guest令牌
        guest_token = auth_manager.create_access_token(
            user_id="guest_user",
            role="guest"
        )
        
        # 验证admin角色
        admin_info = auth_manager.get_current_user(
            authorization=f"Bearer {admin_token}"
        )
        assert admin_info.role == "admin"
        
        # 验证guest角色
        guest_info = auth_manager.get_current_user(
            authorization=f"Bearer {guest_token}"
        )
        assert guest_info.role == "guest"
        
        # 模拟权限检查
        def check_admin_permission(user_info):
            return user_info.role == 'admin'
        
        assert check_admin_permission(admin_info) is True
        assert check_admin_permission(guest_info) is False


class TestEndToEndSecurityFlow:
    """端到端安全流程测试
    
    白皮书依据: 第七章 6.1 安全基础
    """
    
    def test_complete_security_flow(self, tmp_path):
        """测试完整的安全流程
        
        白皮书依据: 第七章 6.1 安全基础
        
        完整流程：
        1. 初始化SecureConfig，生成主密钥
        2. 加密JWT密钥
        3. AuthManager使用加密的JWT密钥
        4. 创建访问令牌
        5. 验证令牌
        6. 提取用户信息
        """
        # 1. 初始化SecureConfig
        key_file = tmp_path / ".master.key"
        secure_config = SecureConfig(key_file_path=str(key_file))
        
        # 2. 加密JWT密钥
        jwt_secret = "production_jwt_secret_key"
        encrypted_jwt = secure_config.encrypt_api_key(jwt_secret)
        
        # 3. 模拟环境变量
        with patch.dict(os.environ, {'ENCRYPTED_JWT_SECRET': encrypted_jwt}):
            # 4. AuthManager使用加密的JWT密钥
            with patch('src.security.auth_manager.SecureConfig', return_value=secure_config):
                auth_manager = AuthManager()
                
                # 5. 创建访问令牌
                token = auth_manager.create_access_token(
                    user_id="production_user",
                    role="admin"
                )
                
                # 6. 验证令牌
                user_info = auth_manager.get_current_user(
                    authorization=f"Bearer {token}"
                )
                
                # 7. 验证用户信息
                assert user_info.user_id == "production_user"
                assert user_info.role == "admin"
                assert user_info.exp is not None
                assert user_info.iat is not None
    
    def test_security_failure_scenarios(self, tmp_path):
        """测试安全失败场景
        
        白皮书依据: 第七章 6.1 安全基础
        
        失败场景：
        1. 主密钥文件损坏
        2. 加密密钥不匹配
        3. 令牌被篡改
        """
        # 场景1：主密钥文件损坏
        key_file = tmp_path / ".master.key"
        secure_config = SecureConfig(key_file_path=str(key_file))
        
        # 损坏密钥文件
        with open(key_file, 'w') as f:
            f.write("corrupted_key_data")
        
        # 尝试创建新的SecureConfig应该抛出RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            new_config = SecureConfig(key_file_path=str(key_file))
        
        assert "Failed to initialize SecureConfig" in str(exc_info.value)
        
        # 场景2：使用错误的密钥解密
        jwt_secret = "test_secret"
        encrypted = secure_config.encrypt_api_key(jwt_secret)
        
        # 创建新的SecureConfig（不同的主密钥）
        new_key_file = tmp_path / ".master2.key"
        new_config = SecureConfig(key_file_path=str(new_key_file))
        
        # 尝试用新密钥解密旧数据应该失败
        with pytest.raises(Exception):
            new_config.decrypt_api_key(encrypted)
        
        # 场景3：令牌被篡改
        auth_manager = AuthManager(secret_key="test_secret")
        token = auth_manager.create_access_token(user_id="test_user", role="admin")
        
        # 篡改令牌
        tampered_token = token[:-10] + "tampered123"
        
        # 验证应该失败
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_manager.get_current_user(authorization=f"Bearer {tampered_token}")
        
        assert "Invalid token" in str(exc_info.value)
