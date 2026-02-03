"""SecureConfig单元测试

白皮书依据: 第七章 7.1.1 API Key加密存储

测试SecureConfig的核心功能：
- 加密/解密往返测试
- 主密钥文件创建测试
- 缺失密钥错误处理测试
- 文件权限设置测试
- 环境变量集成测试
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from cryptography.fernet import Fernet

from src.security.secure_config import SecureConfig


class TestSecureConfig:
    """SecureConfig单元测试套件
    
    白皮书依据: 第七章 7.1.1 API Key加密存储
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
    """
    
    @pytest.fixture
    def temp_key_file(self):
        """创建临时密钥文件路径（不创建实际文件）"""
        # 只生成路径，不创建文件，让SecureConfig自己创建
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'test_master_{os.getpid()}_{id(self)}.key')
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
    
    @pytest.fixture
    def secure_config(self, temp_key_file):
        """创建SecureConfig实例"""
        return SecureConfig(key_file_path=temp_key_file)
    
    def test_encryption_decryption_round_trip(self, secure_config):
        """测试加密/解密往返
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 加密后的密钥与原始密钥不同
        2. 解密后的密钥与原始密钥相同
        3. 加密结果是Base64编码的字符串
        """
        # 原始API密钥
        original_key = "my_secret_api_key_12345"
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(original_key)
        
        # 验证加密结果
        assert isinstance(encrypted_key, str), "加密结果应该是字符串"
        assert encrypted_key != original_key, "加密后的密钥应该与原始密钥不同"
        assert len(encrypted_key) > 0, "加密结果不应为空"
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证解密结果
        assert decrypted_key == original_key, "解密后的密钥应该与原始密钥相同"
    
    def test_master_key_file_creation(self, temp_key_file):
        """测试主密钥文件创建
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.2, 1.5
        
        验证：
        1. 如果密钥文件不存在，SecureConfig会创建它
        2. 创建的密钥文件包含有效的Fernet密钥
        3. 密钥文件可以被后续实例读取
        """
        # 确保文件不存在
        if os.path.exists(temp_key_file):
            os.remove(temp_key_file)
        
        # 创建SecureConfig实例（应该自动创建密钥文件）
        config = SecureConfig(key_file_path=temp_key_file)
        
        # 验证密钥文件已创建
        assert os.path.exists(temp_key_file), "主密钥文件应该被创建"
        
        # 验证密钥文件内容
        with open(temp_key_file, 'rb') as f:
            key_content = f.read()
        
        assert len(key_content) > 0, "密钥文件不应为空"
        
        # 验证密钥是有效的Fernet密钥
        try:
            Fernet(key_content)
        except Exception as e:
            pytest.fail(f"密钥文件包含无效的Fernet密钥: {e}")
        
        # 验证可以使用该密钥进行加密/解密
        test_data = "test_api_key"
        encrypted = config.encrypt_api_key(test_data)
        decrypted = config.decrypt_api_key(encrypted)
        assert decrypted == test_data, "使用新创建的密钥应该能够正常加密/解密"
    
    def test_master_key_file_reuse(self, temp_key_file):
        """测试主密钥文件重用
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.2
        
        验证：
        1. 第二次创建SecureConfig时会重用现有密钥文件
        2. 使用相同密钥文件的两个实例可以互相解密
        """
        # 确保文件不存在
        if os.path.exists(temp_key_file):
            os.remove(temp_key_file)
        
        # 第一个实例
        config1 = SecureConfig(key_file_path=temp_key_file)
        test_data = "shared_api_key"
        encrypted = config1.encrypt_api_key(test_data)
        
        # 第二个实例（应该重用相同的密钥文件）
        config2 = SecureConfig(key_file_path=temp_key_file)
        decrypted = config2.decrypt_api_key(encrypted)
        
        # 验证两个实例使用相同的密钥
        assert decrypted == test_data, "使用相同密钥文件的实例应该能够互相解密"
    
    def test_missing_key_error_handling(self, secure_config):
        """测试缺失密钥错误处理
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.6
        
        验证：
        1. 当环境变量不存在时，get_api_key抛出ValueError
        2. 错误消息包含有用的信息
        """
        # 测试不存在的环境变量
        with pytest.raises(ValueError) as exc_info:
            secure_config.get_api_key("NONEXISTENT_KEY")
        
        # 验证错误消息
        error_message = str(exc_info.value)
        assert "NONEXISTENT_KEY" in error_message, "错误消息应该包含密钥名称"
        assert "not found" in error_message.lower(), "错误消息应该说明密钥未找到"
        assert "ENCRYPTED_NONEXISTENT_KEY" in error_message, "错误消息应该包含环境变量名称"
    
    def test_empty_api_key_encryption(self, secure_config):
        """测试空API密钥加密
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 空字符串应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            secure_config.encrypt_api_key("")
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_empty_encrypted_key_decryption(self, secure_config):
        """测试空加密密钥解密
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 空字符串应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            secure_config.decrypt_api_key("")
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_invalid_encrypted_key_decryption(self, secure_config):
        """测试无效加密密钥解密
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 无效的加密数据应该抛出RuntimeError
        2. 错误消息应该说明解密失败
        """
        invalid_encrypted_key = "invalid_base64_data_not_encrypted"
        
        with pytest.raises(RuntimeError) as exc_info:
            secure_config.decrypt_api_key(invalid_encrypted_key)
        
        error_message = str(exc_info.value)
        assert "decrypt" in error_message.lower(), "错误消息应该说明解密失败"
    
    def test_get_api_key_from_environment(self, secure_config, monkeypatch):
        """测试从环境变量获取API密钥
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.4
        
        验证：
        1. 可以从环境变量读取加密的API密钥
        2. 自动解密并返回明文密钥
        """
        # 准备测试数据
        original_key = "test_api_key_from_env"
        encrypted_key = secure_config.encrypt_api_key(original_key)
        
        # 设置环境变量
        monkeypatch.setenv("ENCRYPTED_TEST_KEY", encrypted_key)
        
        # 从环境变量获取密钥
        retrieved_key = secure_config.get_api_key("TEST_KEY")
        
        # 验证
        assert retrieved_key == original_key, "应该返回解密后的明文密钥"
    
    def test_get_api_key_empty_name(self, secure_config):
        """测试空密钥名称
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.6
        
        验证：
        1. 空密钥名称应该抛出ValueError
        """
        with pytest.raises(ValueError) as exc_info:
            secure_config.get_api_key("")
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_file_permissions_setting(self, temp_key_file):
        """测试文件权限设置
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.3
        
        验证：
        1. 主密钥文件权限应该设置为0o600（仅所有者可读写）
        
        注意：Windows上文件权限设置可能不完全生效，此测试主要验证代码执行不报错
        """
        # 确保文件不存在
        if os.path.exists(temp_key_file):
            os.remove(temp_key_file)
        
        # 创建SecureConfig实例
        config = SecureConfig(key_file_path=temp_key_file)
        
        # 验证文件存在
        assert os.path.exists(temp_key_file), "密钥文件应该被创建"
        
        # 在Unix系统上验证权限
        if os.name != 'nt':  # 非Windows系统
            file_stat = os.stat(temp_key_file)
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600, f"文件权限应该是0o600，实际是{oct(file_mode)}"
    
    def test_multiple_encryption_produces_different_results(self, secure_config):
        """测试多次加密产生不同结果
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 相同的明文多次加密应该产生不同的密文（Fernet使用随机IV）
        2. 所有密文都可以正确解密回原始明文
        """
        original_key = "test_api_key"
        
        # 多次加密
        encrypted_keys = [secure_config.encrypt_api_key(original_key) for _ in range(5)]
        
        # 验证密文都不相同
        assert len(set(encrypted_keys)) == 5, "多次加密应该产生不同的密文"
        
        # 验证所有密文都可以正确解密
        for encrypted_key in encrypted_keys:
            decrypted_key = secure_config.decrypt_api_key(encrypted_key)
            assert decrypted_key == original_key, "所有密文都应该能正确解密"
    
    def test_unicode_api_key_encryption(self, secure_config):
        """测试Unicode API密钥加密
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 包含Unicode字符的API密钥可以正确加密/解密
        """
        unicode_key = "测试密钥_🔐_test_key_中文"
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(unicode_key)
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证
        assert decrypted_key == unicode_key, "Unicode密钥应该能正确加密/解密"
    
    def test_long_api_key_encryption(self, secure_config):
        """测试长API密钥加密
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 长API密钥（>1000字符）可以正确加密/解密
        """
        long_key = "a" * 2000  # 2000字符的长密钥
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(long_key)
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证
        assert decrypted_key == long_key, "长密钥应该能正确加密/解密"
    
    def test_special_characters_api_key_encryption(self, secure_config):
        """测试特殊字符API密钥加密
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 包含特殊字符的API密钥可以正确加密/解密
        """
        special_key = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(special_key)
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证
        assert decrypted_key == special_key, "特殊字符密钥应该能正确加密/解密"
    
    def test_master_key_file_corruption_handling(self, temp_key_file):
        """测试主密钥文件损坏处理
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.5
        
        验证：
        1. 如果密钥文件损坏，应该抛出RuntimeError
        """
        # 写入无效的密钥数据
        with open(temp_key_file, 'wb') as f:
            f.write(b'invalid_key_data')
        
        # 尝试创建SecureConfig实例
        with pytest.raises(RuntimeError) as exc_info:
            SecureConfig(key_file_path=temp_key_file)
        
        error_message = str(exc_info.value)
        assert "failed to initialize" in error_message.lower(), "错误消息应该说明初始化失败"
    
    def test_concurrent_encryption_operations(self, secure_config):
        """测试并发加密操作
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.1
        
        验证：
        1. 并发加密操作不会相互干扰
        2. 所有加密结果都可以正确解密
        """
        import concurrent.futures
        
        test_keys = [f"test_key_{i}" for i in range(10)]
        
        # 并发加密
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            encrypted_keys = list(executor.map(secure_config.encrypt_api_key, test_keys))
        
        # 验证所有密钥都可以正确解密
        for original, encrypted in zip(test_keys, encrypted_keys):
            decrypted = secure_config.decrypt_api_key(encrypted)
            assert decrypted == original, f"并发加密的密钥应该能正确解密: {original}"
    
    def test_default_key_file_path(self):
        """测试默认密钥文件路径
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.2
        
        验证：
        1. 默认密钥文件路径应该是D:/MIA_Data/.master.key
        
        注意：此测试不实际创建文件，只验证路径设置
        """
        with patch('src.security.secure_config.SecureConfig._load_or_create_key') as mock_load:
            mock_load.return_value = Fernet(Fernet.generate_key())
            
            config = SecureConfig()
            
            # 验证默认路径（Windows使用反斜杠）
            expected_path = str(Path("D:/MIA_Data/.master.key"))
            actual_path = str(config.key_file)
            assert actual_path == expected_path, \
                f"默认密钥文件路径应该是{expected_path}，实际是{actual_path}"


class TestSecureConfigEdgeCases:
    """SecureConfig边界条件测试
    
    白皮书依据: 第七章 7.1.1 API Key加密存储
    """
    
    @pytest.fixture
    def temp_key_file(self):
        """创建临时密钥文件路径（不创建实际文件）"""
        # 只生成路径，不创建文件，让SecureConfig自己创建
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'test_edge_{os.getpid()}_{id(self)}.key')
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
    
    @pytest.fixture
    def secure_config(self, temp_key_file):
        """创建SecureConfig实例"""
        return SecureConfig(key_file_path=temp_key_file)
    
    def test_whitespace_only_api_key(self, secure_config):
        """测试仅包含空白字符的API密钥
        
        验证：
        1. 仅包含空白字符的密钥应该被视为有效（不是空字符串）
        2. 可以正确加密/解密
        """
        whitespace_key = "   \t\n   "
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(whitespace_key)
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证
        assert decrypted_key == whitespace_key, "空白字符密钥应该能正确加密/解密"
    
    def test_newline_in_api_key(self, secure_config):
        """测试包含换行符的API密钥
        
        验证：
        1. 包含换行符的密钥可以正确加密/解密
        """
        newline_key = "line1\nline2\nline3"
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(newline_key)
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证
        assert decrypted_key == newline_key, "包含换行符的密钥应该能正确加密/解密"
    
    def test_binary_like_api_key(self, secure_config):
        """测试类似二进制的API密钥
        
        验证：
        1. 包含所有可打印ASCII字符的密钥可以正确加密/解密
        """
        binary_like_key = ''.join(chr(i) for i in range(32, 127))
        
        # 加密
        encrypted_key = secure_config.encrypt_api_key(binary_like_key)
        
        # 解密
        decrypted_key = secure_config.decrypt_api_key(encrypted_key)
        
        # 验证
        assert decrypted_key == binary_like_key, "类似二进制的密钥应该能正确加密/解密"


class TestSecureConfigExceptionHandling:
    """SecureConfig异常处理测试
    
    白皮书依据: 第七章 7.1.1 API Key加密存储
    Requirements: 1.5, 1.6
    
    验证：
    1. 密钥文件权限异常处理
    2. 加密异常处理
    3. 解密异常处理
    """
    
    @pytest.fixture
    def temp_key_file(self):
        """创建临时密钥文件路径"""
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f'test_exc_{os.getpid()}_{id(self)}.key')
        
        yield temp_path
        
        # 清理
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
    
    def test_load_or_create_key_chmod_exception(self, temp_key_file, monkeypatch):
        """测试密钥文件chmod异常处理
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.5
        
        验证：
        1. 当os.chmod失败时，应该记录警告但不抛出异常
        2. SecureConfig仍然可以正常初始化
        """
        # 确保文件不存在
        if os.path.exists(temp_key_file):
            os.remove(temp_key_file)
        
        # Mock os.chmod to raise exception
        import os as os_module
        original_chmod = os_module.chmod
        
        def mock_chmod(path, mode):
            if "test_exc" in str(path):
                raise OSError("权限设置失败")
            return original_chmod(path, mode)
        
        monkeypatch.setattr("os.chmod", mock_chmod)
        
        # 应该记录警告但不抛出异常
        config = SecureConfig(key_file_path=temp_key_file)
        assert config is not None, "即使chmod失败，SecureConfig也应该能初始化"
        
        # 验证可以正常使用
        test_key = "test_key"
        encrypted = config.encrypt_api_key(test_key)
        decrypted = config.decrypt_api_key(encrypted)
        assert decrypted == test_key
    
    def test_encrypt_api_key_exception(self, temp_key_file, monkeypatch):
        """测试加密API密钥异常处理
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.6
        
        验证：
        1. 当Fernet.encrypt失败时，应该抛出RuntimeError
        2. 错误消息应该包含有用的信息
        """
        config = SecureConfig(key_file_path=temp_key_file)
        
        # Mock Fernet.encrypt to raise exception
        from cryptography.fernet import Fernet
        original_encrypt = Fernet.encrypt
        
        def mock_encrypt(self, data):
            raise Exception("加密失败")
        
        monkeypatch.setattr(Fernet, "encrypt", mock_encrypt)
        
        with pytest.raises(RuntimeError) as exc_info:
            config.encrypt_api_key("test_key")
        
        error_message = str(exc_info.value)
        assert "encrypt" in error_message.lower(), "错误消息应该说明加密失败"
    
    def test_decrypt_api_key_exception(self, temp_key_file, monkeypatch):
        """测试解密API密钥异常处理
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.6
        
        验证：
        1. 当Fernet.decrypt失败时，应该抛出RuntimeError
        2. 错误消息应该包含有用的信息
        """
        config = SecureConfig(key_file_path=temp_key_file)
        
        # 先加密一个密钥
        encrypted = config.encrypt_api_key("test_key")
        
        # Mock Fernet.decrypt to raise exception
        from cryptography.fernet import Fernet
        original_decrypt = Fernet.decrypt
        
        def mock_decrypt(self, token):
            raise Exception("解密失败")
        
        monkeypatch.setattr(Fernet, "decrypt", mock_decrypt)
        
        with pytest.raises(RuntimeError) as exc_info:
            config.decrypt_api_key(encrypted)
        
        error_message = str(exc_info.value)
        assert "decrypt" in error_message.lower(), "错误消息应该说明解密失败"
    
    def test_get_api_key_decrypt_exception(self, temp_key_file, monkeypatch):
        """测试get_api_key解密异常处理
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.6
        
        验证：
        1. 当环境变量中的加密密钥无法解密时，应该抛出RuntimeError
        """
        config = SecureConfig(key_file_path=temp_key_file)
        
        # 设置一个加密的环境变量
        encrypted = config.encrypt_api_key("test_key")
        monkeypatch.setenv("ENCRYPTED_TEST_KEY", encrypted)
        
        # Mock Fernet.decrypt to raise exception
        from cryptography.fernet import Fernet
        original_decrypt = Fernet.decrypt
        
        def mock_decrypt(self, token):
            raise Exception("解密失败")
        
        monkeypatch.setattr(Fernet, "decrypt", mock_decrypt)
        
        with pytest.raises(RuntimeError) as exc_info:
            config.get_api_key("TEST_KEY")
        
        error_message = str(exc_info.value)
        assert "decrypt" in error_message.lower(), "错误消息应该说明解密失败"
    
    def test_get_api_key_invalid_token(self, temp_key_file, monkeypatch):
        """测试获取API密钥时token无效
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.6
        
        验证：
        1. 当环境变量包含无效的加密token时，应该抛出RuntimeError
        """
        config = SecureConfig(key_file_path=temp_key_file)
        
        # 设置一个无效的加密token
        monkeypatch.setenv("ENCRYPTED_INVALID_KEY", "invalid_base64_token")
        
        with pytest.raises(RuntimeError) as exc_info:
            config.get_api_key("INVALID_KEY")
        
        error_message = str(exc_info.value)
        assert "decrypt" in error_message.lower(), "错误消息应该说明解密失败"
    
    def test_key_file_read_permission_error(self, temp_key_file, monkeypatch):
        """测试密钥文件读取权限错误
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.5
        
        验证：
        1. 当无法读取密钥文件时，应该抛出RuntimeError
        """
        # 先创建一个有效的密钥文件
        config = SecureConfig(key_file_path=temp_key_file)
        del config  # 释放文件句柄
        
        # Mock open to raise permission error
        original_open = open
        
        def mock_open(file, mode='r', *args, **kwargs):
            if "test_exc" in str(file) and 'rb' in mode:
                raise PermissionError("无权限读取文件")
            return original_open(file, mode, *args, **kwargs)
        
        monkeypatch.setattr("builtins.open", mock_open)
        
        with pytest.raises(RuntimeError) as exc_info:
            SecureConfig(key_file_path=temp_key_file)
        
        error_message = str(exc_info.value)
        assert "failed to initialize" in error_message.lower(), "错误消息应该说明初始化失败"
    
    def test_key_file_write_permission_error(self, temp_key_file, monkeypatch):
        """测试密钥文件写入权限错误
        
        白皮书依据: 第七章 7.1.1 API Key加密存储
        Requirements: 1.5
        
        验证：
        1. 当无法写入密钥文件时，应该抛出RuntimeError
        """
        # 确保文件不存在
        if os.path.exists(temp_key_file):
            os.remove(temp_key_file)
        
        # Mock open to raise permission error for write
        original_open = open
        
        def mock_open(file, mode='r', *args, **kwargs):
            if "test_exc" in str(file) and 'wb' in mode:
                raise PermissionError("无权限写入文件")
            return original_open(file, mode, *args, **kwargs)
        
        monkeypatch.setattr("builtins.open", mock_open)
        
        with pytest.raises(RuntimeError) as exc_info:
            SecureConfig(key_file_path=temp_key_file)
        
        error_message = str(exc_info.value)
        assert "failed to initialize" in error_message.lower(), "错误消息应该说明初始化失败"
