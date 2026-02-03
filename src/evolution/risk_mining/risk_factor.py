"""风险因子数据模型

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统

本模块定义了风险因子的核心数据结构和事件类型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from loguru import logger


class RiskEventType(Enum):
    """风险事件类型

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 事件设计

    Attributes:
        RISK_FACTOR_GENERATED: 风险因子生成事件
    """

    RISK_FACTOR_GENERATED = "risk_factor_generated"


@dataclass
class RiskFactor:
    """风险因子

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 核心数据模型

    统一的风险因子数据结构,所有挖掘器生成此类型。

    Attributes:
        factor_type: 因子类型,必须是 'flow', 'microstructure', 'portfolio' 之一
        symbol: 标的代码,如 '000001.SZ'
        risk_value: 风险值,范围 [0, 1],0=无风险,1=极高风险
        confidence: 置信度,范围 [0, 1],表示对风险评估的信心
        timestamp: 时间戳,因子生成时间
        metadata: 元数据,包含具体检测指标和数据源信息

    Example:
        >>> factor = RiskFactor(
        ...     factor_type='flow',
        ...     symbol='000001.SZ',
        ...     risk_value=0.75,
        ...     confidence=0.85,
        ...     timestamp=datetime.now(),
        ...     metadata={'signals': [('capital_retreat', 0.8)]}
        ... )
        >>> assert 0 <= factor.risk_value <= 1
        >>> assert factor.factor_type in ['flow', 'microstructure', 'portfolio']
    """

    factor_type: str
    symbol: str
    risk_value: float
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 数据验证

        验证规则:
        1. risk_value 必须在 [0, 1] 范围内
        2. confidence 必须在 [0, 1] 范围内
        3. factor_type 必须是有效的因子类型
        4. symbol 不能为空

        Raises:
            ValueError: 当任何字段不满足验证规则时
        """
        # 验证 risk_value 范围
        if not 0 <= self.risk_value <= 1:
            raise ValueError(f"risk_value must be in [0, 1], got {self.risk_value}")

        # 验证 confidence 范围
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

        # 验证 factor_type
        valid_types = {"flow", "microstructure", "portfolio"}
        if self.factor_type not in valid_types:
            raise ValueError(f"factor_type must be one of {valid_types}, got '{self.factor_type}'")

        # 验证 symbol
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError(f"symbol must be a non-empty string, got '{self.symbol}'")

        # 验证 timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValueError(f"timestamp must be a datetime object, got {type(self.timestamp)}")

        # 验证 metadata
        if not isinstance(self.metadata, dict):
            raise ValueError(f"metadata must be a dict, got {type(self.metadata)}")

        logger.debug(
            f"RiskFactor validated: type={self.factor_type}, "
            f"symbol={self.symbol}, risk_value={self.risk_value:.3f}, "
            f"confidence={self.confidence:.3f}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            包含所有字段的字典
        """
        return {
            "factor_type": self.factor_type,
            "symbol": self.symbol,
            "risk_value": self.risk_value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskFactor":
        """从字典创建RiskFactor实例

        Args:
            data: 包含因子数据的字典

        Returns:
            RiskFactor实例

        Raises:
            ValueError: 当数据格式不正确时
        """
        try:
            # 解析时间戳
            if isinstance(data["timestamp"], str):
                timestamp = datetime.fromisoformat(data["timestamp"])
            else:
                timestamp = data["timestamp"]

            return cls(
                factor_type=data["factor_type"],
                symbol=data["symbol"],
                risk_value=data["risk_value"],
                confidence=data["confidence"],
                timestamp=timestamp,
                metadata=data.get("metadata", {}),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")  # pylint: disable=w0707
        except Exception as e:
            raise ValueError(f"Failed to create RiskFactor from dict: {e}")  # pylint: disable=w0707

    def __repr__(self) -> str:
        """字符串表示

        Returns:
            可读的字符串表示
        """
        return (
            f"RiskFactor(type={self.factor_type}, symbol={self.symbol}, "
            f"risk={self.risk_value:.3f}, conf={self.confidence:.3f})"
        )

    def __eq__(self, other: object) -> bool:
        """相等性比较

        Args:
            other: 另一个对象

        Returns:
            是否相等
        """
        if not isinstance(other, RiskFactor):
            return False

        return (
            self.factor_type == other.factor_type
            and self.symbol == other.symbol
            and abs(self.risk_value - other.risk_value) < 1e-6
            and abs(self.confidence - other.confidence) < 1e-6
            and self.timestamp == other.timestamp
        )

    def __hash__(self) -> int:
        """哈希值

        Returns:
            哈希值
        """
        return hash(
            (self.factor_type, self.symbol, round(self.risk_value, 6), round(self.confidence, 6), self.timestamp)
        )


@dataclass
class RiskEvent:
    """风险事件

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 事件设计

    用于在EventBus上发布风险因子生成事件。

    Attributes:
        event_type: 事件类型
        symbol: 标的代码
        factor: 风险因子
        timestamp: 事件时间戳

    Example:
        >>> factor = RiskFactor(
        ...     factor_type='flow',
        ...     symbol='000001.SZ',
        ...     risk_value=0.75,
        ...     confidence=0.85,
        ...     timestamp=datetime.now(),
        ...     metadata={}
        ... )
        >>> event = RiskEvent(
        ...     event_type=RiskEventType.RISK_FACTOR_GENERATED,
        ...     symbol='000001.SZ',
        ...     factor=factor,
        ...     timestamp=datetime.now()
        ... )
    """

    event_type: RiskEventType
    symbol: str
    factor: RiskFactor
    timestamp: datetime

    def __post_init__(self):
        """验证数据有效性

        Raises:
            ValueError: 当任何字段不满足验证规则时
        """
        # 验证 event_type
        if not isinstance(self.event_type, RiskEventType):
            raise ValueError(f"event_type must be a RiskEventType, got {type(self.event_type)}")

        # 验证 symbol
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError(f"symbol must be a non-empty string, got '{self.symbol}'")

        # 验证 factor
        if not isinstance(self.factor, RiskFactor):
            raise ValueError(f"factor must be a RiskFactor, got {type(self.factor)}")

        # 验证 timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValueError(f"timestamp must be a datetime object, got {type(self.timestamp)}")

        # 验证 symbol 一致性
        if self.symbol != self.factor.symbol:
            raise ValueError(f"Event symbol '{self.symbol}' does not match " f"factor symbol '{self.factor.symbol}'")

        logger.debug(f"RiskEvent validated: type={self.event_type.value}, " f"symbol={self.symbol}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            包含所有字段的字典
        """
        return {
            "event_type": self.event_type.value,
            "symbol": self.symbol,
            "factor": self.factor.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskEvent":
        """从字典创建RiskEvent实例

        Args:
            data: 包含事件数据的字典

        Returns:
            RiskEvent实例

        Raises:
            ValueError: 当数据格式不正确时
        """
        try:
            # 解析事件类型
            event_type = RiskEventType(data["event_type"])

            # 解析时间戳
            if isinstance(data["timestamp"], str):
                timestamp = datetime.fromisoformat(data["timestamp"])
            else:
                timestamp = data["timestamp"]

            # 解析因子
            factor = RiskFactor.from_dict(data["factor"])

            return cls(event_type=event_type, symbol=data["symbol"], factor=factor, timestamp=timestamp)
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")  # pylint: disable=w0707
        except Exception as e:
            raise ValueError(f"Failed to create RiskEvent from dict: {e}")  # pylint: disable=w0707

    def __repr__(self) -> str:
        """字符串表示

        Returns:
            可读的字符串表示
        """
        return f"RiskEvent(type={self.event_type.value}, symbol={self.symbol}, " f"factor={self.factor})"
