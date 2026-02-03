"""安全模块数据模型

白皮书依据: 第七章 7.1 安全架构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

# ============================================================================
# 异常类
# ============================================================================


class AuthenticationError(Exception):
    """认证错误基类

    白皮书依据: 第七章 7.1.2 JWT Token认证
    """


class TokenExpiredError(AuthenticationError):
    """令牌过期错误

    白皮书依据: 第七章 7.1.2 JWT Token认证
    """


class InvalidTokenError(AuthenticationError):
    """无效令牌错误

    白皮书依据: 第七章 7.1.2 JWT Token认证
    """


class AuthorizationHeaderError(AuthenticationError):
    """Authorization头错误

    白皮书依据: 第七章 7.1.2 JWT Token认证
    """


# ============================================================================
# 枚举类
# ============================================================================


class UserRole(Enum):
    """用户角色枚举

    白皮书依据: 第七章 7.1.2 JWT Token认证
    """

    ADMIN = "admin"
    GUEST = "guest"


@dataclass
class JWTPayload:
    """JWT令牌载荷

    白皮书依据: 第七章 7.1.2 JWT Token认证

    Attributes:
        user_id: 用户ID
        role: 用户角色
        exp: 过期时间
        iat: 签发时间
    """

    user_id: str
    role: UserRole
    exp: datetime
    iat: datetime

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "exp": self.exp.timestamp(),
            "iat": self.iat.timestamp(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JWTPayload":
        """从字典创建"""
        return cls(
            user_id=data["user_id"],
            role=UserRole(data["role"]),
            exp=datetime.fromtimestamp(data["exp"]),
            iat=datetime.fromtimestamp(data["iat"]),
        )


@dataclass
class EncryptedAPIKey:
    """加密的API密钥

    白皮书依据: 第七章 7.1.1 API Key加密存储

    Attributes:
        key_name: 密钥名称
        encrypted_value: 加密后的值
        created_at: 创建时间
    """

    key_name: str
    encrypted_value: str
    created_at: datetime


@dataclass
class TokenPayload:
    """JWT令牌载荷（扩展版）

    白皮书依据: 第七章 7.1.2 JWT Token认证

    Attributes:
        user_id: 用户ID
        role: 用户角色
        exp: 过期时间
        iat: 签发时间
        nbf: 生效时间（可选）
        additional_claims: 额外声明
    """

    user_id: str
    role: str
    exp: datetime
    iat: datetime
    nbf: Optional[datetime] = None
    additional_claims: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "user_id": self.user_id,
            "role": self.role,
            "exp": self.exp.timestamp(),
            "iat": self.iat.timestamp(),
        }
        if self.nbf:
            result["nbf"] = self.nbf.timestamp()
        if self.additional_claims:
            result.update(self.additional_claims)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenPayload":
        """从字典创建"""
        core_keys = {"user_id", "role", "exp", "iat", "nbf"}
        additional = {k: v for k, v in data.items() if k not in core_keys}

        return cls(
            user_id=data["user_id"],
            role=data["role"],
            exp=datetime.fromtimestamp(data["exp"]),
            iat=datetime.fromtimestamp(data["iat"]),
            nbf=datetime.fromtimestamp(data["nbf"]) if data.get("nbf") else None,
            additional_claims=additional,
        )

    def is_admin(self) -> bool:
        """检查是否是管理员"""
        return self.role == UserRole.ADMIN.value

    def is_expired(self) -> bool:
        """检查令牌是否已过期"""
        from datetime import timezone  # pylint: disable=import-outside-toplevel

        return datetime.now(timezone.utc) > self.exp
