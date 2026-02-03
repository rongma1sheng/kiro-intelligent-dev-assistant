"""Data Models for Strategy Library Management System

白皮书依据: 第四章 4.4 策略库管理系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class StrategyType(Enum):
    """策略类型

    白皮书依据: 第四章 4.4.1 策略分类
    """

    MOMENTUM = "momentum"  # 动量策略
    MEAN_REVERSION = "mean_reversion"  # 均值回归策略
    FACTOR_BASED = "factor_based"  # 因子策略
    ARBITRAGE = "arbitrage"  # 套利策略
    MARKET_NEUTRAL = "market_neutral"  # 市场中性策略
    TREND_FOLLOWING = "trend_following"  # 趋势跟踪策略
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"  # 统计套利策略
    MULTI_FACTOR = "multi_factor"  # 多因子策略


class MarketRegime(Enum):
    """市场状态

    白皮书依据: 第四章 4.4.2 市场状态分类
    """

    BULL = "bull"  # 牛市
    BEAR = "bear"  # 熊市
    SIDEWAYS = "sideways"  # 震荡市
    HIGH_VOL = "high_vol"  # 高波动
    LOW_VOL = "low_vol"  # 低波动
    CRISIS = "crisis"  # 危机


class LifecycleState(Enum):
    """策略生命周期状态

    白皮书依据: 第四章 4.4.3 策略生命周期
    """

    ACTIVE = "active"  # 活跃：正常运行
    MONITORING = "monitoring"  # 监控：性能下降，需要密切关注
    DEPRECATED = "deprecated"  # 废弃：性能严重下降，禁止新资金
    RETIRED = "retired"  # 退役：完全停用


@dataclass
class StrategyMetadata:  # pylint: disable=too-many-instance-attributes
    """策略元数据

    白皮书依据: 第四章 4.4.4 策略元数据
    """

    # 基本信息
    strategy_id: str
    strategy_name: str
    strategy_type: StrategyType
    description: str = ""

    # Z2H认证信息
    z2h_certified: bool = False
    z2h_certification_level: Optional[str] = None
    z2h_certification_date: Optional[datetime] = None

    # 源因子信息
    source_factors: List[str] = field(default_factory=list)

    # 性能指标
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    annual_return: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0

    # Arena测试结果
    arena_score: float = 0.0
    arena_test_date: Optional[datetime] = None

    # 模拟盘结果
    simulation_passed: bool = False
    simulation_metrics: Dict[str, float] = field(default_factory=dict)
    simulation_end_date: Optional[datetime] = None

    # 适用市场状态
    suitable_regimes: List[MarketRegime] = field(default_factory=list)

    # 生命周期信息
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # 性能监控
    recent_ic: Optional[float] = None  # 最近IC值
    ic_below_threshold_days: int = 0  # IC低于阈值的连续天数

    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据完整性"""
        if not self.strategy_id:
            raise ValueError("strategy_id不能为空")

        if not self.strategy_name:
            raise ValueError("strategy_name不能为空")

        if not isinstance(self.strategy_type, StrategyType):
            raise ValueError(f"strategy_type必须是StrategyType枚举，当前: {type(self.strategy_type)}")

        if not isinstance(self.lifecycle_state, LifecycleState):
            raise ValueError(f"lifecycle_state必须是LifecycleState枚举，当前: {type(self.lifecycle_state)}")

        # 验证性能指标范围
        if self.sharpe_ratio < -10 or self.sharpe_ratio > 10:
            logger.warning(f"夏普比率超出合理范围: {self.sharpe_ratio}")

        if self.max_drawdown > 0:
            logger.warning(f"最大回撤应该是负数: {self.max_drawdown}")

        if self.win_rate < 0 or self.win_rate > 1:
            raise ValueError(f"胜率必须在[0, 1]范围内: {self.win_rate}")

        if self.profit_factor < 0:
            raise ValueError(f"盈亏比不能为负数: {self.profit_factor}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type.value,
            "description": self.description,
            "z2h_certified": self.z2h_certified,
            "z2h_certification_level": self.z2h_certification_level,
            "z2h_certification_date": self.z2h_certification_date.isoformat() if self.z2h_certification_date else None,
            "source_factors": self.source_factors,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "annual_return": self.annual_return,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "arena_score": self.arena_score,
            "arena_test_date": self.arena_test_date.isoformat() if self.arena_test_date else None,
            "simulation_passed": self.simulation_passed,
            "simulation_metrics": self.simulation_metrics,
            "simulation_end_date": self.simulation_end_date.isoformat() if self.simulation_end_date else None,
            "suitable_regimes": [regime.value for regime in self.suitable_regimes],
            "lifecycle_state": self.lifecycle_state.value,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "recent_ic": self.recent_ic,
            "ic_below_threshold_days": self.ic_below_threshold_days,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyMetadata":
        """从字典创建"""
        return cls(
            strategy_id=data["strategy_id"],
            strategy_name=data["strategy_name"],
            strategy_type=StrategyType(data["strategy_type"]),
            description=data.get("description", ""),
            z2h_certified=data.get("z2h_certified", False),
            z2h_certification_level=data.get("z2h_certification_level"),
            z2h_certification_date=(
                datetime.fromisoformat(data["z2h_certification_date"]) if data.get("z2h_certification_date") else None
            ),
            source_factors=data.get("source_factors", []),
            sharpe_ratio=data.get("sharpe_ratio", 0.0),
            max_drawdown=data.get("max_drawdown", 0.0),
            annual_return=data.get("annual_return", 0.0),
            win_rate=data.get("win_rate", 0.0),
            profit_factor=data.get("profit_factor", 0.0),
            arena_score=data.get("arena_score", 0.0),
            arena_test_date=datetime.fromisoformat(data["arena_test_date"]) if data.get("arena_test_date") else None,
            simulation_passed=data.get("simulation_passed", False),
            simulation_metrics=data.get("simulation_metrics", {}),
            simulation_end_date=(
                datetime.fromisoformat(data["simulation_end_date"]) if data.get("simulation_end_date") else None
            ),
            suitable_regimes=[MarketRegime(regime) for regime in data.get("suitable_regimes", [])],
            lifecycle_state=LifecycleState(data.get("lifecycle_state", "active")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_updated=datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else datetime.now(),
            recent_ic=data.get("recent_ic"),
            ic_below_threshold_days=data.get("ic_below_threshold_days", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StrategyRecord:
    """策略记录（包含元数据和策略代码）

    白皮书依据: 第四章 4.4.5 策略记录
    """

    metadata: StrategyMetadata
    strategy_code: str = ""  # 策略代码

    def __post_init__(self):
        """验证数据完整性"""
        if not isinstance(self.metadata, StrategyMetadata):
            raise ValueError(f"metadata必须是StrategyMetadata类型，当前: {type(self.metadata)}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": self.metadata.to_dict(),
            "strategy_code": self.strategy_code,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyRecord":
        """从字典创建"""
        return cls(
            metadata=StrategyMetadata.from_dict(data["metadata"]),
            strategy_code=data.get("strategy_code", ""),
        )
