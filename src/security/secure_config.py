"""API密钥加密存储

白皮书依据: 第七章 7.1.1 API Key加密存储

使用Fernet对称加密（基于AES-128-CBC）保护API密钥。
主密钥存储在D盘（数据盘），文件权限设置为0o600（仅当前用户可读）。
"""

import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from loguru import logger


class SecureConfig:
    """安全配置管理器

    白皮书依据: 第七章 7.1.1 API Key加密存储

    使用Fernet对称加密保护API密钥，主密钥存储在数据盘。

    Attributes:
        key_file: 主密钥文件路径
        cipher: Fernet加密器实例

    Example:
        >>> secure_config = SecureConfig()
        >>> encrypted = secure_config.encrypt_api_key("my_secret_key")
        >>> decrypted = secure_config.decrypt_api_key(encrypted)
        >>> assert decrypted == "my_secret_key"
    """

    def __init__(self, key_file_path: Optional[str] = None):
        """初始化安全配置管理器

        白皮书依据: 第七章 7.1.1 API Key加密存储

        Args:
            key_file_path: 主密钥文件路径，默认为D:/MIA_Data/.master.key

        Raises:
            RuntimeError: 当无法创建或读取主密钥文件时
        """
        if key_file_path is None:
            # 默认路径：D盘数据目录
            key_file_path = "D:/MIA_Data/.master.key"

        self.key_file = Path(key_file_path)
        self.cipher = self._load_or_create_key()

        logger.info(
            f"SecureConfig initialized",  # pylint: disable=w1309
            component="security",
            action="init",
            key_file=str(self.key_file),  # pylint: disable=w1309
        )  # pylint: disable=w1309

    def _load_or_create_key(self) -> Fernet:
        """加载或创建主密钥

        白皮书依据: 第七章 7.1.1 API Key加密存储

        如果主密钥文件存在，则加载；否则生成新密钥并保存。
        文件权限设置为0o600（仅当前用户可读写）。

        Returns:
            Fernet加密器实例

        Raises:
            RuntimeError: 当无法创建或读取主密钥文件时
        """
        try:
            if self.key_file.exists():
                # 加载现有密钥
                with open(self.key_file, "rb") as f:
                    key = f.read()

                logger.info(
                    "Loaded existing master key", component="security", action="load_key", key_file=str(self.key_file)
                )
            else:
                # 生成新密钥
                key = Fernet.generate_key()

                # 创建目录
                self.key_file.parent.mkdir(parents=True, exist_ok=True)

                # 保存密钥
                with open(self.key_file, "wb") as f:
                    f.write(key)

                # 设置文件权限（仅当前用户可读写）
                # Windows上使用os.chmod可能不完全生效，但仍然设置
                try:
                    os.chmod(self.key_file, 0o600)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        f"Failed to set file permissions: {e}", component="security", action="chmod", error=str(e)
                    )

                logger.info(
                    "Generated new master key", component="security", action="create_key", key_file=str(self.key_file)
                )

            return Fernet(key)

        except Exception as e:
            logger.error(
                f"Failed to load or create master key: {e}",
                component="security",
                action="load_or_create_key",
                error=str(e),
            )
            raise RuntimeError(f"Failed to initialize SecureConfig: {e}") from e

    def encrypt_api_key(self, api_key: str) -> str:
        """加密API密钥

        白皮书依据: 第七章 7.1.1 API Key加密存储

        Args:
            api_key: 明文API密钥

        Returns:
            加密后的API密钥（Base64编码字符串）

        Raises:
            ValueError: 当api_key为空时
            RuntimeError: 当加密失败时

        Example:
            >>> secure_config = SecureConfig()
            >>> encrypted = secure_config.encrypt_api_key("my_secret_key")
            >>> assert isinstance(encrypted, str)
            >>> assert len(encrypted) > 0
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        try:
            encrypted_bytes = self.cipher.encrypt(api_key.encode("utf-8"))
            encrypted_str = encrypted_bytes.decode("utf-8")

            logger.debug("API key encrypted", component="security", action="encrypt", key_length=len(api_key))

            return encrypted_str

        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}", component="security", action="encrypt", error=str(e))
            raise RuntimeError(f"Failed to encrypt API key: {e}") from e

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """解密API密钥

        白皮书依据: 第七章 7.1.1 API Key加密存储

        Args:
            encrypted_key: 加密的API密钥（Base64编码字符串）

        Returns:
            明文API密钥

        Raises:
            ValueError: 当encrypted_key为空时
            RuntimeError: 当解密失败时（可能是密钥错误或数据损坏）

        Example:
            >>> secure_config = SecureConfig()
            >>> encrypted = secure_config.encrypt_api_key("my_secret_key")
            >>> decrypted = secure_config.decrypt_api_key(encrypted)
            >>> assert decrypted == "my_secret_key"
        """
        if not encrypted_key:
            raise ValueError("Encrypted key cannot be empty")

        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_key.encode("utf-8"))
            decrypted_str = decrypted_bytes.decode("utf-8")

            logger.debug("API key decrypted", component="security", action="decrypt", key_length=len(decrypted_str))

            return decrypted_str

        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}", component="security", action="decrypt", error=str(e))
            raise RuntimeError(f"Failed to decrypt API key: {e}") from e

    def get_api_key(self, key_name: str) -> str:
        """从环境变量获取并解密API密钥

        白皮书依据: 第七章 7.1.1 API Key加密存储

        从环境变量读取加密的API密钥（前缀为ENCRYPTED_），解密后返回。

        Args:
            key_name: 密钥名称（不含ENCRYPTED_前缀）

        Returns:
            明文API密钥

        Raises:
            ValueError: 当环境变量不存在时
            RuntimeError: 当解密失败时

        Example:
            >>> os.environ['ENCRYPTED_TEST_KEY'] = encrypted_value
            >>> secure_config = SecureConfig()
            >>> api_key = secure_config.get_api_key("TEST_KEY")
        """
        if not key_name:
            raise ValueError("Key name cannot be empty")

        env_var_name = f"ENCRYPTED_{key_name}"
        encrypted_value = os.getenv(env_var_name)

        if not encrypted_value:
            logger.error(
                f"API key not found in environment",  # pylint: disable=w1309
                component="security",
                action="get_api_key",
                key_name=key_name,
                env_var=env_var_name,
            )
            raise ValueError(f"API key {key_name} not found in environment. " f"Please set {env_var_name} in .env file")

        try:
            decrypted = self.decrypt_api_key(encrypted_value)

            logger.info(
                "API key retrieved from environment", component="security", action="get_api_key", key_name=key_name
            )

            return decrypted

        except Exception as e:
            logger.error(
                f"Failed to get API key: {e}",
                component="security",
                action="get_api_key",
                key_name=key_name,
                error=str(e),
            )
            raise RuntimeError(f"Failed to get API key {key_name}: {e}") from e
