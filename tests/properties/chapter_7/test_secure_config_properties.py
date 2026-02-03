"""SecureConfig属性测试

白皮书依据: 第七章 7.1.1 API Key加密存储

Property 1: Encryption Round-Trip
- 对于任意有效的API密钥字符串，加密后解密应该得到原始字符串
- 这是加密系统的核心正确性属性

Validates: Requirements 1.1
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.security.secure_config import SecureConfig


class TestSecureConfigProperties:
    """SecureConfig属性测试套件
    
    白皮书依据: 第七章 7.1.1 API Key加密存储
    """
    
    @pytest.fixture(scope="class")
    def temp_key_file(self):
        """创建临时密钥文件路径（类级别共享）"""
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'test_property_{os.getpid()}.key')
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
    
    @pytest.fixture(scope="class")
    def secure_config(self, temp_key_file):
        """创建SecureConfig实例（类级别共享以提高性能）"""
        return SecureConfig(key_file_path=temp_key_file)
    
    @given(api_key=st.text(min_size=1, max_size=1000))
    @settings(max_examples=100, deadline=None)
    def test_property_encryption_round_trip(self, api_key: str, secure_config):
        """Property 1: Encryption Round-Trip
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        **Validates: Requirements 1.1**
        
        属性定义:
        ∀ api_key ∈ NonEmptyString:
            decrypt(encrypt(api_key)) == api_key
        
        验证:
        1. 对于任意非空字符串，加密后解密应该得到原始字符串
        2. 加密是可逆的
        3. 不会丢失任何信息
        """
        # 前置条件：API密钥不能为空
        assume(len(api_key.strip()) > 0 or len(api_key) > 0)
        
        # 执行加密
        encrypted = secure_config.encrypt_api_key(api_key)
        
        # 验证加密结果
        assert isinstance(encrypted, str), "加密结果应该是字符串"
        assert len(encrypted) > 0, "加密结果不应为空"
        assert encrypted != api_key, "加密后的密钥应该与原始密钥不同"
        
        # 执行解密
        decrypted = secure_config.decrypt_api_key(encrypted)
        
        # 验证往返属性
        assert decrypted == api_key, \
            f"解密后的密钥应该与原始密钥相同: original={repr(api_key)}, decrypted={repr(decrypted)}"
    
    @given(api_key=st.text(
        alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P', 'S'),
            whitelist_characters=' \t\n'
        ),
        min_size=1,
        max_size=500
    ))
    @settings(max_examples=50, deadline=None)
    def test_property_encryption_preserves_unicode(self, api_key: str, secure_config):
        """Property 1b: Encryption Preserves Unicode
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        **Validates: Requirements 1.1**
        
        属性定义:
        ∀ api_key ∈ UnicodeString:
            decrypt(encrypt(api_key)) == api_key
        
        验证:
        1. Unicode字符（包括中文、日文、emoji等）可以正确加密/解密
        2. 字符编码不会丢失
        """
        assume(len(api_key) > 0)
        
        # 执行加密
        encrypted = secure_config.encrypt_api_key(api_key)
        
        # 执行解密
        decrypted = secure_config.decrypt_api_key(encrypted)
        
        # 验证往返属性
        assert decrypted == api_key, \
            f"Unicode密钥应该能正确往返: original={repr(api_key)}, decrypted={repr(decrypted)}"
    
    @given(api_key=st.text(min_size=1, max_size=100))
    @settings(max_examples=30, deadline=None)
    def test_property_encryption_produces_different_ciphertext(self, api_key: str, secure_config):
        """Property 1c: Encryption Produces Different Ciphertext
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        **Validates: Requirements 1.1**
        
        属性定义:
        ∀ api_key ∈ NonEmptyString:
            encrypt(api_key) != encrypt(api_key) (with high probability)
        
        验证:
        1. 相同的明文多次加密应该产生不同的密文（Fernet使用随机IV）
        2. 这是语义安全的基本要求
        """
        assume(len(api_key) > 0)
        
        # 多次加密
        encrypted1 = secure_config.encrypt_api_key(api_key)
        encrypted2 = secure_config.encrypt_api_key(api_key)
        
        # 验证密文不同（Fernet使用随机IV，所以密文应该不同）
        assert encrypted1 != encrypted2, \
            "相同明文的两次加密应该产生不同的密文"
        
        # 验证两个密文都可以正确解密
        assert secure_config.decrypt_api_key(encrypted1) == api_key
        assert secure_config.decrypt_api_key(encrypted2) == api_key
    
    @given(api_key=st.binary(min_size=1, max_size=500).map(lambda b: b.decode('utf-8', errors='ignore')))
    @settings(max_examples=30, deadline=None)
    def test_property_encryption_handles_arbitrary_bytes(self, api_key: str, secure_config):
        """Property 1d: Encryption Handles Arbitrary Bytes
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        **Validates: Requirements 1.1**
        
        属性定义:
        ∀ api_key ∈ ValidUTF8String:
            decrypt(encrypt(api_key)) == api_key
        
        验证:
        1. 任意有效的UTF-8字符串都可以正确加密/解密
        """
        assume(len(api_key) > 0)
        
        # 执行加密
        encrypted = secure_config.encrypt_api_key(api_key)
        
        # 执行解密
        decrypted = secure_config.decrypt_api_key(encrypted)
        
        # 验证往返属性
        assert decrypted == api_key


class TestSecureConfigKeyManagementProperties:
    """SecureConfig密钥管理属性测试
    
    白皮书依据: 第七章 7.1.1 API Key加密存储
    """
    
    @given(api_key=st.text(min_size=1, max_size=100))
    @settings(max_examples=20, deadline=None)
    def test_property_key_file_consistency(self, api_key: str):
        """Property 1e: Key File Consistency
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        **Validates: Requirements 1.2**
        
        属性定义:
        ∀ api_key ∈ NonEmptyString:
            let config1 = SecureConfig(key_file)
            let config2 = SecureConfig(key_file)
            config2.decrypt(config1.encrypt(api_key)) == api_key
        
        验证:
        1. 使用相同密钥文件的两个实例可以互相解密
        2. 密钥文件的持久化是正确的
        """
        assume(len(api_key) > 0)
        
        # 创建临时密钥文件
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'test_consistency_{os.getpid()}_{id(api_key)}.key')
        
        try:
            # 确保文件不存在
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # 第一个实例加密
            config1 = SecureConfig(key_file_path=temp_path)
            encrypted = config1.encrypt_api_key(api_key)
            
            # 第二个实例解密
            config2 = SecureConfig(key_file_path=temp_path)
            decrypted = config2.decrypt_api_key(encrypted)
            
            # 验证
            assert decrypted == api_key, \
                "使用相同密钥文件的实例应该能互相解密"
        finally:
            # 清理
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
