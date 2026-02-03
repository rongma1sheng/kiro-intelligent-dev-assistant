"""数据模型 - 智能数据探针与桥接系统

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 1.1-1.10, 2.1-2.10
设计: design.md 核心组件设计 - 数据模型

本模块定义了数据探针与桥接系统的核心数据模型，包括：
- 数据源类型和状态枚举
- 数据源配置
- 探测结果
- 降级链配置
- 质量指标
- 路由策略
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class DataSourceType(Enum):
    """数据源类型枚举

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 1.1, 2.1

    定义系统支持的数据源类型，用于数据源分类和路由决策。

    Attributes:
        MARKET_DATA: 市场行情数据（日线、分钟线、Tick）
        FINANCIAL_DATA: 财务数据（资产负债表、利润表、现金流量表）
        ALTERNATIVE_DATA: 替代数据（卫星数据、信用卡消费、供应链）
        SENTIMENT_DATA: 情绪数据（社交媒体、新闻情绪、搜索趋势）
        EVENT_DATA: 事件数据（公司公告、新闻事件、宏观事件）
        MACRO_DATA: 宏观数据（GDP、CPI、利率、汇率）
    """

    MARKET_DATA = "market_data"
    FINANCIAL_DATA = "financial_data"
    ALTERNATIVE_DATA = "alternative_data"
    SENTIMENT_DATA = "sentiment_data"
    EVENT_DATA = "event_data"
    MACRO_DATA = "macro_data"


class DataSourceStatus(Enum):
    """数据源状态枚举

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 1.2, 1.3

    定义数据源的运行状态，用于健康检查和路由决策。

    Attributes:
        AVAILABLE: 数据源可用，响应正常
        UNAVAILABLE: 数据源不可用，连接失败或认证失败
        DEGRADED: 数据源降级，响应缓慢或数据质量下降
        TESTING: 数据源测试中，正在进行探测验证
    """

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    TESTING = "testing"


@dataclass
class DataSourceConfig:
    """数据源配置

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 1.1, 1.5
    设计: design.md - DataSourceConfig

    定义数据源的完整配置信息，包括连接参数、性能参数和成本参数。

    Attributes:
        source_id: 数据源唯一标识符（如 "akshare", "yahoo_finance"）
        source_name: 数据源显示名称（如 "AKShare", "Yahoo Finance"）
        source_type: 数据源类型（市场数据、财务数据等）
        api_endpoint: API端点URL
        api_key: API密钥（加密存储，可选）
        rate_limit: 速率限制（请求/秒），用于流量控制
        cost_per_request: 每次请求成本（美元），用于成本优化路由
        priority: 优先级（0-10，10最高），用于路由排序
        is_free: 是否免费数据源，用于成本优先路由
        requires_auth: 是否需要认证，用于探测验证

    Example:
        >>> config = DataSourceConfig(
        ...     source_id="akshare",
        ...     source_name="AKShare",
        ...     source_type=DataSourceType.MARKET_DATA,
        ...     api_endpoint="https://akshare.akfamily.xyz",
        ...     rate_limit=100,
        ...     is_free=True,
        ...     requires_auth=False
        ... )
    """

    source_id: str
    source_name: str
    source_type: DataSourceType
    api_endpoint: str
    api_key: Optional[str] = None
    rate_limit: int = 100
    cost_per_request: float = 0.0
    priority: int = 5
    is_free: bool = True
    requires_auth: bool = False

    def __post_init__(self):
        """初始化后验证

        验证配置参数的有效性，确保数据完整性。

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not self.source_id:
            raise ValueError("source_id不能为空")

        if not self.source_name:
            raise ValueError("source_name不能为空")

        if not self.api_endpoint:
            raise ValueError("api_endpoint不能为空")

        if self.rate_limit <= 0:
            raise ValueError(f"rate_limit必须 > 0，当前: {self.rate_limit}")

        if self.cost_per_request < 0:
            raise ValueError(f"cost_per_request必须 >= 0，当前: {self.cost_per_request}")

        if not 0 <= self.priority <= 10:
            raise ValueError(f"priority必须在 [0, 10]，当前: {self.priority}")


@dataclass
class ProbeResult:
    """探测结果

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 1.2, 1.3, 1.4
    设计: design.md - ProbeResult

    记录数据源探测的结果，包括可用性、性能和质量指标。

    Attributes:
        source_id: 数据源ID
        status: 数据源状态（可用、不可用、降级、测试中）
        response_time: 响应时间（毫秒），用于延迟优先路由
        data_available: 数据是否可用（连接成功且有数据返回）
        error_message: 错误信息（如果探测失败）
        quality_score: 质量评分（0-1），综合评估数据质量
        last_probe_time: 最后探测时间，用于缓存和定期探测

    Example:
        >>> result = ProbeResult(
        ...     source_id="akshare",
        ...     status=DataSourceStatus.AVAILABLE,
        ...     response_time=150.5,
        ...     data_available=True,
        ...     quality_score=0.95,
        ...     last_probe_time=datetime.now()
        ... )
    """

    source_id: str
    status: DataSourceStatus
    response_time: float
    data_available: bool
    error_message: Optional[str] = None
    quality_score: float = 0.0
    last_probe_time: Optional[datetime] = None

    def __post_init__(self):
        """初始化后验证

        验证探测结果的有效性。

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if not self.source_id:
            raise ValueError("source_id不能为空")

        if self.response_time < 0:
            raise ValueError(f"response_time必须 >= 0，当前: {self.response_time}")

        if not 0 <= self.quality_score <= 1:
            raise ValueError(f"quality_score必须在 [0, 1]，当前: {self.quality_score}")

        if self.last_probe_time is None:
            self.last_probe_time = datetime.now()


@dataclass
class FallbackChain:
    """降级链配置

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 3.1, 3.2, 3.3
    设计: design.md - FallbackChain

    定义数据源的降级策略，当主数据源失败时自动切换到备用数据源。

    Attributes:
        data_type: 数据类型（市场数据、财务数据等）
        primary_source: 主数据源ID（优先使用）
        fallback_sources: 降级数据源ID列表（按优先级排序）

    Example:
        >>> chain = FallbackChain(
        ...     data_type=DataSourceType.MARKET_DATA,
        ...     primary_source="akshare",
        ...     fallback_sources=["yahoo_finance", "alpha_vantage"]
        ... )
    """

    data_type: DataSourceType
    primary_source: str
    fallback_sources: List[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后验证

        验证降级链配置的有效性。

        Raises:
            ValueError: 当参数无效时
        """
        if not self.primary_source:
            raise ValueError("primary_source不能为空")

        if not self.fallback_sources:
            raise ValueError("fallback_sources不能为空，至少需要一个备用数据源")

        if self.primary_source in self.fallback_sources:
            raise ValueError("primary_source不能出现在fallback_sources中")

    def get_all_sources(self) -> List[str]:
        """获取所有数据源（主源 + 降级源）

        Returns:
            按优先级排序的数据源ID列表
        """
        return [self.primary_source] + self.fallback_sources


@dataclass
class QualityMetrics:
    """数据质量指标

    白皮书依据: 第三章 3.3 深度清洗矩阵
    需求: 5.1, 5.2, 5.3, 5.4
    设计: design.md - QualityMetrics

    定义数据质量的多维度评估指标，用于数据质量监控和路由决策。

    Attributes:
        completeness: 完整性（0-1），衡量缺失值比例
        timeliness: 及时性（0-1），衡量数据延迟
        accuracy: 准确性（0-1），衡量异常值和错误数据比例
        consistency: 一致性（0-1），衡量逻辑错误（如 high < low）
        overall_score: 综合评分（0-1），加权平均所有指标

    Example:
        >>> metrics = QualityMetrics(
        ...     completeness=0.98,
        ...     timeliness=0.95,
        ...     accuracy=0.92,
        ...     consistency=0.99,
        ...     overall_score=0.96
        ... )
    """

    completeness: float
    timeliness: float
    accuracy: float
    consistency: float
    overall_score: float

    def __post_init__(self):
        """初始化后验证

        验证质量指标的有效性。

        Raises:
            ValueError: 当指标不在 [0, 1] 范围时
        """
        metrics = {
            "completeness": self.completeness,
            "timeliness": self.timeliness,
            "accuracy": self.accuracy,
            "consistency": self.consistency,
            "overall_score": self.overall_score,
        }

        for name, value in metrics.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name}必须在 [0, 1]，当前: {value}")

    def is_acceptable(self, threshold: float = 0.5) -> bool:
        """判断数据质量是否可接受

        Args:
            threshold: 质量阈值，默认0.5

        Returns:
            True表示质量可接受，False表示质量不达标
        """
        return self.overall_score >= threshold


class RoutingStrategy(Enum):
    """路由策略枚举

    白皮书依据: 第三章 3.2 基础设施与数据治理
    需求: 2.1, 2.2, 2.5
    设计: design.md - RoutingStrategy

    定义智能路由器的路由策略，用于选择最佳数据源。

    Attributes:
        QUALITY_FIRST: 质量优先，选择质量评分最高的数据源
        COST_FIRST: 成本优先，优先选择免费数据源，然后按成本升序
        LATENCY_FIRST: 延迟优先，选择响应时间最短的数据源
        REGION_AWARE: 地域感知，根据市场类型选择最佳数据源
                      （A股用AKShare，美股用Yahoo Finance）

    Example:
        >>> strategy = RoutingStrategy.COST_FIRST
        >>> print(strategy.value)
        'cost_first'
    """

    QUALITY_FIRST = "quality_first"
    COST_FIRST = "cost_first"
    LATENCY_FIRST = "latency_first"
    REGION_AWARE = "region_aware"
