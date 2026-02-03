"""JWT认证管理器

白皮书依据: 第六章 6.1.2 JWT Token认证

AuthManager负责API端点保护，防止未授权访问。
使用JWT令牌进行身份验证和授权。
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from loguru import logger

from src.security.data_models import (
    AuthenticationError,
    AuthorizationHeaderError,
    InvalidTokenError,
    TokenExpiredError,
    TokenPayload,
    UserRole,
)
from src.security.secure_config import SecureConfig


class AuthManager:
    """JWT认证管理器

    白皮书依据: 第六章 6.1.2 JWT Token认证

    负责：
    - JWT令牌创建和验证
    - 用户身份认证
    - Bearer scheme验证
    - 访问控制

    Attributes:
        secret_key: JWT签名密钥
        algorithm: JWT签名算法，默认HS256
        access_token_expire_hours: 访问令牌过期时间（小时），默认24
    """

    # 默认配置
    DEFAULT_ALGORITHM = "HS256"
    DEFAULT_EXPIRE_HOURS = 24

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = DEFAULT_ALGORITHM,
        access_token_expire_hours: int = DEFAULT_EXPIRE_HOURS,
        secure_config: Optional[SecureConfig] = None,
    ):
        """初始化AuthManager

        白皮书依据: 第六章 6.1.2 JWT Token认证

        Args:
            secret_key: JWT签名密钥，如果为None则从SecureConfig读取
            algorithm: JWT签名算法，默认HS256
            access_token_expire_hours: 访问令牌过期时间（小时），默认24
            secure_config: SecureConfig实例，用于读取加密的JWT密钥

        Raises:
            ValueError: 当access_token_expire_hours <= 0时
            AuthenticationError: 当无法获取JWT密钥时
        """
        if access_token_expire_hours <= 0:
            raise ValueError(f"access_token_expire_hours必须大于0，当前值: {access_token_expire_hours}")

        self.algorithm: str = algorithm
        self.access_token_expire_hours: int = access_token_expire_hours

        # 获取JWT密钥
        if secret_key is not None:
            self.secret_key: str = secret_key
            logger.debug("使用提供的JWT密钥")
        else:
            try:
                # 从SecureConfig读取加密的JWT密钥
                config = secure_config or SecureConfig()
                self.secret_key = config.get_api_key("JWT_SECRET")
                logger.debug("从SecureConfig读取JWT密钥")
            except ValueError as e:
                # 如果环境变量不存在，尝试生成一个临时密钥（仅用于开发）
                env_key = os.environ.get("JWT_SECRET")
                if env_key:
                    self.secret_key = env_key
                    logger.warning("使用环境变量JWT_SECRET作为密钥（不推荐用于生产环境）")
                else:
                    raise AuthenticationError(
                        f"无法获取JWT密钥: {e}. " "请设置ENCRYPTED_JWT_SECRET环境变量或提供secret_key参数"
                    ) from e

        logger.info(f"AuthManager初始化完成: algorithm={algorithm}, " f"expire_hours={access_token_expire_hours}")

    def create_access_token(
        self, user_id: str, role: str = UserRole.GUEST.value, additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建访问令牌

        白皮书依据: 第六章 6.1.2 JWT Token认证

        Args:
            user_id: 用户ID
            role: 用户角色，默认'guest'，可选'admin'
            additional_claims: 额外的JWT声明

        Returns:
            JWT令牌字符串

        Raises:
            ValueError: 当user_id为空时
            ValueError: 当role不是有效的UserRole时
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id不能为空")

        # 验证角色
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"无效的角色: {role}. 有效角色: {valid_roles}")

        # 计算过期时间
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=self.access_token_expire_hours)

        # 构建payload
        payload: Dict[str, Any] = {
            "user_id": user_id.strip(),
            "role": role,
            "exp": expire,
            "iat": now,
            "nbf": now,  # Not Before: 令牌生效时间
        }

        # 添加额外声明
        if additional_claims:
            for key, value in additional_claims.items():
                if key not in payload:  # 不覆盖核心声明
                    payload[key] = value

        # 生成令牌
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"创建访问令牌: user_id={user_id}, role={role}, " f"expire={expire.isoformat()}")

        return token

    def verify_token(self, token: str) -> TokenPayload:
        """验证令牌

        白皮书依据: 第六章 6.1.2 JWT Token认证

        Args:
            token: JWT令牌字符串

        Returns:
            TokenPayload对象，包含解码后的令牌信息

        Raises:
            ValueError: 当token为空时
            TokenExpiredError: 当令牌已过期时
            InvalidTokenError: 当令牌无效时
        """
        if not token or not token.strip():
            raise ValueError("token不能为空")

        try:
            payload = jwt.decode(token.strip(), self.secret_key, algorithms=[self.algorithm])

            # 构建TokenPayload对象
            token_payload = TokenPayload(
                user_id=payload.get("user_id", ""),
                role=payload.get("role", UserRole.GUEST.value),
                exp=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
                nbf=datetime.fromtimestamp(payload.get("nbf", 0), tz=timezone.utc) if payload.get("nbf") else None,
                additional_claims={
                    k: v for k, v in payload.items() if k not in ("user_id", "role", "exp", "iat", "nbf")
                },
            )

            logger.debug(f"令牌验证成功: user_id={token_payload.user_id}")

            return token_payload

        except jwt.ExpiredSignatureError as e:
            logger.warning(f"令牌已过期: {e}")
            raise TokenExpiredError("Token expired") from e

        except jwt.InvalidTokenError as e:
            logger.warning(f"无效令牌: {e}")
            raise InvalidTokenError(f"Invalid token: {e}") from e

    def get_current_user(self, authorization: Optional[str]) -> TokenPayload:
        """从请求头获取当前用户

        白皮书依据: 第六章 6.1.2 JWT Token认证

        Args:
            authorization: Authorization请求头值，格式: "Bearer <token>"

        Returns:
            TokenPayload对象，包含当前用户信息

        Raises:
            AuthorizationHeaderError: 当Authorization头缺失或格式错误时
            TokenExpiredError: 当令牌已过期时
            InvalidTokenError: 当令牌无效时
        """
        if not authorization:
            raise AuthorizationHeaderError("Authorization header missing")

        # 解析Authorization头
        try:
            scheme, token = self._parse_authorization_header(authorization)
        except ValueError as e:
            raise AuthorizationHeaderError(str(e)) from e

        # 验证scheme
        if scheme.lower() != "bearer":
            raise AuthorizationHeaderError(f"Invalid authentication scheme: {scheme}. Expected: Bearer")

        # 验证令牌
        return self.verify_token(token)

    def _parse_authorization_header(self, authorization: str) -> Tuple[str, str]:
        """解析Authorization请求头

        Args:
            authorization: Authorization请求头值

        Returns:
            (scheme, token) 元组

        Raises:
            ValueError: 当格式错误时
        """
        parts = authorization.split()

        if len(parts) != 2:
            raise ValueError(
                f"Invalid authorization header format. " f"Expected: 'Bearer <token>', got: '{authorization}'"
            )

        return parts[0], parts[1]

    def is_token_valid(self, token: str) -> bool:
        """检查令牌是否有效

        Args:
            token: JWT令牌字符串

        Returns:
            True如果令牌有效，否则False
        """
        try:
            self.verify_token(token)
            return True
        except (ValueError, TokenExpiredError, InvalidTokenError):
            return False

    def refresh_token(self, token: str) -> str:
        """刷新令牌

        使用现有令牌的信息创建新令牌。

        Args:
            token: 现有的JWT令牌

        Returns:
            新的JWT令牌

        Raises:
            TokenExpiredError: 当令牌已过期时
            InvalidTokenError: 当令牌无效时
        """
        payload = self.verify_token(token)

        return self.create_access_token(
            user_id=payload.user_id, role=payload.role, additional_claims=payload.additional_claims
        )

    def get_token_remaining_time(self, token: str) -> timedelta:
        """获取令牌剩余有效时间

        Args:
            token: JWT令牌字符串

        Returns:
            剩余有效时间

        Raises:
            TokenExpiredError: 当令牌已过期时
            InvalidTokenError: 当令牌无效时
        """
        payload = self.verify_token(token)
        now = datetime.now(timezone.utc)

        remaining = payload.exp - now

        if remaining.total_seconds() < 0:
            raise TokenExpiredError("Token expired")

        return remaining
