"""基础适配器接口 - 智能数据探针与桥接系统

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 6.1-6.10
设计: design.md 核心组件设计 - 适配器层

本模块定义了数据源适配器的抽象基类，所有具体的数据源适配器都必须继承此类。
提供统一的接口规范和通用的工具方法，确保数据获取的一致性和可靠性。

适配器职责：
1. 从外部数据源获取数据
2. 将数据标准化为统一格式
3. 处理连接性和认证测试
4. 实现重试和速率限制机制
5. 提供完整的错误处理和日志记录
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd
from loguru import logger

from src.infra.data_exceptions import AuthenticationError, DataFetchError, RateLimitError


class BaseAdapter(ABC):
    """数据源适配器抽象基类

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 6.1-6.10
    设计: design.md - 适配器层

    所有数据源适配器的基类，定义了统一的接口规范。
    子类必须实现所有抽象方法，以确保接口一致性。

    通用功能：
    - 重试机制（指数退避）
    - 速率限制处理
    - 错误日志记录
    - 性能监控

    子类需要实现：
    - fetch_data(): 获取数据的核心逻辑
    - test_connectivity(): 测试连接性
    - test_authentication(): 测试认证
    - standardize_data(): 数据标准化

    Attributes:
        source_id: 数据源唯一标识符
        max_retries: 最大重试次数，默认3次
        retry_delays: 重试延迟列表（秒），默认[1, 2, 4]（指数退避）
        rate_limit: 速率限制（请求/秒），默认100
        last_request_time: 最后一次请求时间，用于速率限制

    Example:
        >>> class MyAdapter(BaseAdapter):
        ...     def __init__(self):
        ...         super().__init__(source_id="my_source")
        ...
        ...     async def fetch_data(self, request_params):
        ...         # 实现数据获取逻辑
        ...         pass
        ...
        ...     async def test_connectivity(self):
        ...         # 实现连接性测试
        ...         pass
        ...
        ...     async def test_authentication(self):
        ...         # 实现认证测试
        ...         pass
        ...
        ...     def standardize_data(self, raw_data):
        ...         # 实现数据标准化
        ...         pass
    """

    def __init__(
        self, source_id: str, max_retries: int = 3, retry_delays: Optional[list] = None, rate_limit: int = 100
    ):
        """初始化基础适配器

        Args:
            source_id: 数据源唯一标识符
            max_retries: 最大重试次数，默认3次
            retry_delays: 重试延迟列表（秒），默认[1, 2, 4]（指数退避）
            rate_limit: 速率限制（请求/秒），默认100

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not source_id:
            raise ValueError("source_id不能为空")

        if max_retries < 0:
            raise ValueError(f"max_retries必须 >= 0，当前: {max_retries}")

        if rate_limit <= 0:
            raise ValueError(f"rate_limit必须 > 0，当前: {rate_limit}")

        self.source_id = source_id
        self.max_retries = max_retries
        self.retry_delays = retry_delays or [1, 2, 4]  # 指数退避：1s, 2s, 4s
        self.rate_limit = rate_limit
        self.last_request_time: float = 0.0

        logger.info(f"初始化适配器: {source_id}, " f"max_retries={max_retries}, " f"rate_limit={rate_limit}")

    @abstractmethod
    async def fetch_data(self, request_params: Dict[str, Any]) -> pd.DataFrame:
        """获取数据（抽象方法）

        白皮书依据: 第三章 3.2 基础设施与数据治理
        需求: 6.1, 6.2

        从数据源获取数据的核心方法，子类必须实现。

        Args:
            request_params: 请求参数字典，包含：
                - symbol: 股票代码（必需）
                - start_date: 开始日期（可选）
                - end_date: 结束日期（可选）
                - frequency: 数据频率（可选，如 '1d', '1h', '5m'）
                - 其他数据源特定参数

        Returns:
            标准化的数据DataFrame，必须包含以下列：
            - datetime: 时间戳（pd.Timestamp）
            - open: 开盘价（float）
            - high: 最高价（float）
            - low: 最低价（float）
            - close: 收盘价（float）
            - volume: 成交量（float）

        Raises:
            DataFetchError: 当数据获取失败时
            AuthenticationError: 当认证失败时
            RateLimitError: 当超过速率限制时
        """

    @abstractmethod
    async def test_connectivity(self) -> bool:
        """测试连接性（抽象方法）

        白皮书依据: 第三章 3.2 基础设施与数据治理
        需求: 1.3

        测试数据源的连接性，验证API端点是否可访问。
        子类必须实现此方法。

        Returns:
            True表示连接正常，False表示连接失败

        Example:
            >>> adapter = MyAdapter()
            >>> is_connected = await adapter.test_connectivity()
            >>> print(f"连接状态: {'正常' if is_connected else '失败'}")
        """

    @abstractmethod
    async def test_authentication(self) -> bool:
        """测试认证（抽象方法）

        白皮书依据: 第三章 3.2 基础设施与数据治理
        需求: 1.3

        测试数据源的认证状态，验证API密钥是否有效。
        子类必须实现此方法。

        Returns:
            True表示认证成功，False表示认证失败

        Example:
            >>> adapter = MyAdapter()
            >>> is_authenticated = await adapter.test_authentication()
            >>> print(f"认证状态: {'成功' if is_authenticated else '失败'}")
        """

    @abstractmethod
    def standardize_data(self, raw_data: Any) -> pd.DataFrame:
        """数据标准化（抽象方法）

        白皮书依据: 第三章 3.3 深度清洗矩阵
        需求: 4.3

        将原始数据转换为标准格式，确保数据一致性。
        子类必须实现此方法。

        Args:
            raw_data: 原始数据，格式由具体数据源决定

        Returns:
            标准化的DataFrame，必须包含以下列：
            - datetime: 时间戳（pd.Timestamp）
            - open: 开盘价（float）
            - high: 最高价（float）
            - low: 最低价（float）
            - close: 收盘价（float）
            - volume: 成交量（float）

        Raises:
            DataFetchError: 当数据格式无法解析时

        Example:
            >>> raw_data = {"date": ["2024-01-01"], "price": [100.0]}
            >>> df = adapter.standardize_data(raw_data)
            >>> print(df.columns.tolist())
            ['datetime', 'open', 'high', 'low', 'close', 'volume']
        """

    async def fetch_data_with_retry(self, request_params: Dict[str, Any]) -> pd.DataFrame:
        """带重试机制的数据获取

        白皮书依据: 第三章 3.2 基础设施与数据治理
        需求: 3.1, 3.3
        设计: design.md - 错误处理策略

        使用指数退避策略重试数据获取，提高系统可靠性。

        重试策略：
        1. 第1次失败：等待1秒后重试
        2. 第2次失败：等待2秒后重试
        3. 第3次失败：等待4秒后重试
        4. 仍然失败：抛出异常

        Args:
            request_params: 请求参数字典

        Returns:
            标准化的数据DataFrame

        Raises:
            DataFetchError: 当所有重试都失败时

        Example:
            >>> adapter = MyAdapter()
            >>> data = await adapter.fetch_data_with_retry({
            ...     "symbol": "000001.SZ",
            ...     "start_date": "2024-01-01",
            ...     "end_date": "2024-12-31"
            ... })
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # 速率限制检查
                await self._check_rate_limit()

                # 尝试获取数据
                logger.debug(f"[{self.source_id}] 尝试获取数据 " f"(第 {attempt + 1}/{self.max_retries + 1} 次)")

                data = await self.fetch_data(request_params)

                # 成功获取数据
                logger.info(f"[{self.source_id}] 数据获取成功 " f"(尝试 {attempt + 1} 次)")

                return data

            except (DataFetchError, AuthenticationError, RateLimitError) as e:
                last_error = e

                # 如果是最后一次尝试，直接抛出异常
                if attempt >= self.max_retries:
                    logger.error(
                        f"[{self.source_id}] 数据获取失败，已达最大重试次数 " f"({self.max_retries + 1} 次): {e}"
                    )
                    raise DataFetchError(
                        f"数据获取失败（已重试 {self.max_retries + 1} 次）",
                        source_id=self.source_id,
                        details={"last_error": str(e), "attempts": attempt + 1, "request_params": request_params},
                    ) from e

                # 计算重试延迟
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]

                logger.warning(
                    f"[{self.source_id}] 数据获取失败，{delay}秒后重试 "
                    f"(第 {attempt + 1}/{self.max_retries + 1} 次): {e}"
                )

                # 等待后重试
                await asyncio.sleep(delay)

            except Exception as e:
                # 未预期的异常，记录日志并抛出
                logger.error(f"[{self.source_id}] 数据获取遇到未预期错误: {e}", exc_info=True)
                raise DataFetchError(
                    f"数据获取遇到未预期错误: {e}", source_id=self.source_id, details={"request_params": request_params}
                ) from e

        # 理论上不会到达这里，但为了类型检查完整性
        raise DataFetchError("数据获取失败", source_id=self.source_id, details={"last_error": str(last_error)})

    async def _check_rate_limit(self) -> None:
        """检查速率限制

        白皮书依据: 第三章 3.2 基础设施与数据治理
        需求: 10.1, 10.2
        设计: design.md - API速率限制管理

        使用令牌桶算法实现速率限制，避免超过API限制。
        如果请求过快，自动等待到允许的时间。

        Raises:
            RateLimitError: 当速率限制检查失败时（理论上不会抛出，会自动等待）
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        # 计算最小请求间隔（秒）
        min_interval = 1.0 / self.rate_limit

        # 如果请求过快，等待
        if time_since_last_request < min_interval:
            wait_time = min_interval - time_since_last_request

            logger.debug(f"[{self.source_id}] 速率限制：等待 {wait_time:.3f}秒 " f"(限制: {self.rate_limit} 请求/秒)")

            await asyncio.sleep(wait_time)

        # 更新最后请求时间
        self.last_request_time = time.time()

    def _log_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """记录错误日志

        白皮书依据: 第三章 3.2 基础设施与数据治理
        需求: 3.4

        统一的错误日志记录方法，确保错误信息格式一致。

        Args:
            error_type: 错误类型（如 "ConnectionError", "AuthenticationError"）
            message: 错误信息
            details: 详细错误信息字典（可选）

        Example:
            >>> self._log_error(
            ...     "ConnectionError",
            ...     "无法连接到API",
            ...     {"endpoint": "https://api.example.com", "timeout": 30}
            ... )
        """
        log_message = f"[{self.source_id}] {error_type}: {message}"

        if details:
            detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
            log_message = f"{log_message} ({detail_str})"

        logger.error(log_message)

    def _validate_standard_data(self, data: pd.DataFrame) -> None:
        """验证标准化数据格式

        白皮书依据: 第三章 3.3 深度清洗矩阵
        需求: 5.1, 5.3

        验证数据是否符合标准格式要求，确保数据质量。

        Args:
            data: 待验证的DataFrame

        Raises:
            DataFetchError: 当数据格式不符合要求时

        Example:
            >>> df = pd.DataFrame({
            ...     'datetime': [pd.Timestamp('2024-01-01')],
            ...     'open': [100.0],
            ...     'high': [105.0],
            ...     'low': [99.0],
            ...     'close': [103.0],
            ...     'volume': [1000000.0]
            ... })
            >>> self._validate_standard_data(df)  # 验证通过
        """
        required_columns = ["datetime", "open", "high", "low", "close", "volume"]

        # 检查必需列
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise DataFetchError(
                f"数据缺少必需列: {missing_columns}",
                source_id=self.source_id,
                details={"required_columns": required_columns, "actual_columns": data.columns.tolist()},
            )

        # 检查数据类型
        if not pd.api.types.is_datetime64_any_dtype(data["datetime"]):
            raise DataFetchError(
                "datetime列必须是datetime类型",
                source_id=self.source_id,
                details={"actual_dtype": str(data["datetime"].dtype)},
            )

        # 检查数值列
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                raise DataFetchError(
                    f"{col}列必须是数值类型", source_id=self.source_id, details={"actual_dtype": str(data[col].dtype)}
                )

        # 检查数据是否为空
        if data.empty:
            raise DataFetchError("数据为空", source_id=self.source_id)

        logger.debug(f"[{self.source_id}] 数据格式验证通过: " f"{len(data)} 行, {len(data.columns)} 列")

    def __repr__(self) -> str:
        """字符串表示

        Returns:
            适配器的字符串表示
        """
        return (
            f"{self.__class__.__name__}("
            f"source_id='{self.source_id}', "
            f"max_retries={self.max_retries}, "
            f"rate_limit={self.rate_limit})"
        )
