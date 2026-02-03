"""数据异常类 - 智能数据探针与桥接系统

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 1.1-1.10, 2.1-2.10, 3.1-3.10
设计: design.md 核心组件设计 - 异常处理

本模块定义了数据探针与桥接系统的异常类，用于错误处理和降级决策。
所有异常类都继承自基础异常类，提供清晰的错误信息和上下文。
"""

from typing import Any, Dict, Optional


class DataProbeException(Exception):
    """数据探针基础异常类

    白皮书依据: 第三章 3.2 基础设施与数据治理

    所有数据探针与桥接系统的异常都继承自此类。
    提供统一的异常处理接口和错误信息格式。

    Attributes:
        message: 错误信息
        source_id: 数据源ID（可选）
        details: 详细错误信息（可选）
    """

    def __init__(self, message: str, source_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """初始化异常

        Args:
            message: 错误信息
            source_id: 数据源ID
            details: 详细错误信息字典
        """
        self.message = message
        self.source_id = source_id
        self.details = details or {}

        # 构建完整错误信息
        full_message = message
        if source_id:
            full_message = f"[{source_id}] {message}"
        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            full_message = f"{full_message} ({detail_str})"

        super().__init__(full_message)


class DataUnavailableError(DataProbeException):
    """数据不可用异常

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 2.1, 3.1
    设计: design.md - 错误处理策略

    当所有数据源都不可用时抛出此异常。
    这是一个严重错误，表示系统无法获取所需数据。

    使用场景：
    1. 主数据源失败，降级链中的所有备用数据源也失败
    2. 没有配置可用的数据源
    3. 所有数据源都被标记为不可用状态

    Example:
        >>> raise DataUnavailableError(
        ...     "所有市场数据源都不可用",
        ...     source_id="market_data",
        ...     details={"tried_sources": ["akshare", "yahoo_finance", "alpha_vantage"]}
        ... )
    """

    def __init__(
        self, message: str = "数据不可用", source_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """初始化数据不可用异常

        Args:
            message: 错误信息，默认"数据不可用"
            source_id: 数据源ID
            details: 详细错误信息，建议包含：
                    - tried_sources: 尝试过的数据源列表
                    - last_error: 最后一个数据源的错误信息
        """
        super().__init__(message, source_id, details)


class DataFetchError(DataProbeException):
    """数据获取异常

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 2.1, 2.2
    设计: design.md - 错误处理策略

    当从数据源获取数据失败时抛出此异常。
    这是一个可恢复错误，系统应尝试降级到备用数据源。

    使用场景：
    1. API请求失败（网络错误、超时）
    2. API返回错误响应（4xx, 5xx）
    3. 数据解析失败
    4. 数据格式不符合预期

    Example:
        >>> raise DataFetchError(
        ...     "API请求超时",
        ...     source_id="akshare",
        ...     details={
        ...         "endpoint": "https://akshare.akfamily.xyz/stock_zh_a_hist",
        ...         "timeout": 30,
        ...         "symbol": "000001"
        ...     }
        ... )
    """

    def __init__(
        self, message: str = "数据获取失败", source_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """初始化数据获取异常

        Args:
            message: 错误信息，默认"数据获取失败"
            source_id: 数据源ID
            details: 详细错误信息，建议包含：
                    - endpoint: API端点
                    - status_code: HTTP状态码
                    - response: 响应内容
                    - timeout: 超时时间
        """
        super().__init__(message, source_id, details)


class DataQualityError(DataProbeException):
    """数据质量异常

    白皮书依据: 第三章 3.3 深度清洗矩阵
    需求: 5.1, 5.2, 5.3, 5.4, 5.6
    设计: design.md - 数据质量监控器

    当数据质量不达标时抛出此异常。
    这是一个警告级别错误，系统应记录日志并考虑降级。

    使用场景：
    1. 数据完整性不足（缺失值过多）
    2. 数据及时性不足（数据延迟过大）
    3. 数据准确性不足（异常值过多）
    4. 数据一致性不足（逻辑错误过多）
    5. 综合质量评分低于阈值

    Example:
        >>> raise DataQualityError(
        ...     "数据质量评分过低",
        ...     source_id="akshare",
        ...     details={
        ...         "quality_score": 0.45,
        ...         "threshold": 0.50,
        ...         "completeness": 0.60,
        ...         "timeliness": 0.40,
        ...         "accuracy": 0.50,
        ...         "consistency": 0.30
        ...     }
        ... )
    """

    def __init__(
        self, message: str = "数据质量不达标", source_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """初始化数据质量异常

        Args:
            message: 错误信息，默认"数据质量不达标"
            source_id: 数据源ID
            details: 详细错误信息，建议包含：
                    - quality_score: 综合质量评分
                    - threshold: 质量阈值
                    - completeness: 完整性评分
                    - timeliness: 及时性评分
                    - accuracy: 准确性评分
                    - consistency: 一致性评分
        """
        super().__init__(message, source_id, details)


class AuthenticationError(DataProbeException):
    """认证异常

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 1.3
    设计: design.md - 数据探针

    当数据源认证失败时抛出此异常。
    这是一个严重错误，表示API密钥无效或权限不足。

    使用场景：
    1. API密钥无效或过期
    2. API密钥权限不足
    3. 认证请求失败（401, 403）
    4. API配额耗尽

    Example:
        >>> raise AuthenticationError(
        ...     "API密钥无效",
        ...     source_id="alpha_vantage",
        ...     details={
        ...         "api_key": "****1234",
        ...         "status_code": 401,
        ...         "message": "Invalid API key"
        ...     }
        ... )
    """

    def __init__(
        self, message: str = "认证失败", source_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """初始化认证异常

        Args:
            message: 错误信息，默认"认证失败"
            source_id: 数据源ID
            details: 详细错误信息，建议包含：
                    - api_key: API密钥（脱敏）
                    - status_code: HTTP状态码
                    - message: 认证错误信息
                    - quota_remaining: 剩余配额
        """
        super().__init__(message, source_id, details)


class RateLimitError(DataProbeException):
    """速率限制异常

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 1.1, 2.1
    设计: design.md - 错误处理策略

    当触发数据源速率限制时抛出此异常。
    这是一个可恢复错误，系统应等待或降级到其他数据源。

    使用场景：
    1. 超过API速率限制（429 Too Many Requests）
    2. 超过每日/每月配额限制
    3. 并发请求数超限

    Example:
        >>> raise RateLimitError(
        ...     "超过API速率限制",
        ...     source_id="alpha_vantage",
        ...     details={
        ...         "rate_limit": 5,
        ...         "current_rate": 10,
        ...         "reset_time": "2026-01-21 15:30:00",
        ...         "retry_after": 60
        ...     }
        ... )
    """

    def __init__(
        self, message: str = "超过速率限制", source_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None
    ):
        """初始化速率限制异常

        Args:
            message: 错误信息，默认"超过速率限制"
            source_id: 数据源ID
            details: 详细错误信息，建议包含：
                    - rate_limit: 速率限制（请求/秒）
                    - current_rate: 当前请求速率
                    - reset_time: 限制重置时间
                    - retry_after: 建议重试等待时间（秒）
        """
        super().__init__(message, source_id, details)
