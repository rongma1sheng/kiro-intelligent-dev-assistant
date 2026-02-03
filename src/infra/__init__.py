"""数据基础设施

白皮书依据: 第三章 基础设施与数据治理

数据基础设施是MIA系统的数据处理核心，负责高性能数据管道、数据清洗、
数据探针和SPSC队列。

核心组件:
- pipeline: 数据管道
- sanitizer: 数据清洗器
- spsc_queue: SPSC无锁环形队列
- data_probe: 数据探针
- data_models: 数据模型（数据源配置、探测结果、降级链等）
- data_exceptions: 数据异常类（数据不可用、认证失败等）
"""

from .data_exceptions import (
    AuthenticationError,
    DataFetchError,
    DataProbeException,
    DataQualityError,
    DataUnavailableError,
    RateLimitError,
)
from .data_models import (
    DataSourceConfig,
    DataSourceStatus,
    DataSourceType,
    FallbackChain,
    ProbeResult,
    QualityMetrics,
    RoutingStrategy,
)
from .data_probe import DataProbe
from .pipeline import DataPipeline, DataProcessor, DataSink, DataSource
from .sanitizer import AssetType, DataSanitizer
from .spsc_queue import SPSCQueue

__all__ = [
    # 数据管道
    "DataPipeline",
    "DataSource",
    "DataProcessor",
    "DataSink",
    # 数据清洗
    "DataSanitizer",
    "AssetType",
    # SPSC队列
    "SPSCQueue",
    # 数据探针
    "DataProbe",
    # 数据模型
    "DataSourceType",
    "DataSourceStatus",
    "DataSourceConfig",
    "ProbeResult",
    "FallbackChain",
    "QualityMetrics",
    "RoutingStrategy",
    # 数据异常
    "DataProbeException",
    "DataUnavailableError",
    "DataFetchError",
    "DataQualityError",
    "AuthenticationError",
    "RateLimitError",
]
