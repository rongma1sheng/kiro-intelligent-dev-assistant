"""Data Models for Z2H Gene Capsule Certification System

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CertificationLevel(str, Enum):
    """Z2H认证等级

    白皮书依据: 第四章 4.3.2 Z2H认证标准

    认证等级基于Arena四层验证和模拟盘表现综合评定
    """

    PLATINUM = "PLATINUM"  # 白金级：顶级表现
    GOLD = "GOLD"  # 黄金级：优秀表现
    SILVER = "SILVER"  # 白银级：良好表现


@dataclass
class Z2HGeneCapsule:
    """Z2H基因胶囊

    白皮书依据: 第四章 4.3.2 Z2HGeneCapsule

    包含策略的完整认证信息和详细说明

    Attributes:
        strategy_id: 策略唯一标识
        strategy_name: 策略名称
        source_factors: 源因子ID列表
        arena_score: Arena综合评分
        simulation_metrics: 模拟盘指标
        certification_date: 认证日期
        certification_level: 认证等级 (PLATINUM/GOLD/SILVER)
        signature: SHA256签名
        metadata: 额外元数据
    """

    strategy_id: str
    strategy_name: str
    source_factors: List[str]
    arena_score: float
    simulation_metrics: Dict[str, float]
    certification_date: datetime
    certification_level: CertificationLevel
    signature: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据完整性

        白皮书依据: 铁律3 - 完整的错误处理
        """
        # 验证strategy_id
        if not self.strategy_id or not isinstance(self.strategy_id, str):
            raise ValueError(f"strategy_id必须是非空字符串，当前: {self.strategy_id}")

        # 验证strategy_name
        if not self.strategy_name or not isinstance(self.strategy_name, str):
            raise ValueError(f"strategy_name必须是非空字符串，当前: {self.strategy_name}")

        # 验证source_factors
        if not isinstance(self.source_factors, list):
            raise ValueError(f"source_factors必须是列表，当前: {type(self.source_factors)}")

        if not self.source_factors:
            raise ValueError("source_factors不能为空列表")

        # 验证arena_score
        if not isinstance(self.arena_score, (int, float)):
            raise ValueError(f"arena_score必须是数字，当前: {type(self.arena_score)}")

        if not 0.0 <= self.arena_score <= 1.0:
            raise ValueError(f"arena_score必须在[0.0, 1.0]范围内，当前: {self.arena_score}")

        # 验证simulation_metrics
        if not isinstance(self.simulation_metrics, dict):
            raise ValueError(f"simulation_metrics必须是字典，当前: {type(self.simulation_metrics)}")

        required_metrics = ["sharpe_ratio", "max_drawdown", "total_return", "win_rate", "profit_factor"]
        for metric in required_metrics:
            if metric not in self.simulation_metrics:
                raise ValueError(f"simulation_metrics缺少必需指标: {metric}")

        # 验证certification_date
        if not isinstance(self.certification_date, datetime):
            raise ValueError(f"certification_date必须是datetime对象，当前: {type(self.certification_date)}")

        # 验证certification_level
        if isinstance(self.certification_level, str):
            try:
                self.certification_level = CertificationLevel(self.certification_level)
            except ValueError:
                raise ValueError(f"无效的certification_level: {self.certification_level}")  # pylint: disable=w0707

        if not isinstance(self.certification_level, CertificationLevel):
            raise ValueError(f"certification_level必须是CertificationLevel枚举，当前: {type(self.certification_level)}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            字典表示
        """
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "source_factors": self.source_factors,
            "arena_score": self.arena_score,
            "simulation_metrics": self.simulation_metrics,
            "certification_date": self.certification_date.isoformat(),
            "certification_level": self.certification_level.value,
            "signature": self.signature,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Z2HGeneCapsule":
        """从字典创建实例

        Args:
            data: 字典数据

        Returns:
            Z2HGeneCapsule实例
        """
        return cls(
            strategy_id=data["strategy_id"],
            strategy_name=data["strategy_name"],
            source_factors=data["source_factors"],
            arena_score=data["arena_score"],
            simulation_metrics=data["simulation_metrics"],
            certification_date=datetime.fromisoformat(data["certification_date"]),
            certification_level=CertificationLevel(data["certification_level"]),
            signature=data.get("signature", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CertificationCriteria:
    """认证标准

    白皮书依据: 第四章 4.3.2 Z2H认证标准

    Attributes:
        min_sharpe_ratio: 最小夏普比率
        max_drawdown: 最大回撤上限
        min_win_rate: 最小胜率
        min_profit_factor: 最小盈亏比
        min_total_return: 最小总收益率
        min_arena_score: 最小Arena评分
    """

    min_sharpe_ratio: float
    max_drawdown: float
    min_win_rate: float
    min_profit_factor: float
    min_total_return: float
    min_arena_score: float

    def __post_init__(self):
        """验证标准合理性"""
        if self.min_sharpe_ratio < 0:
            raise ValueError(f"min_sharpe_ratio必须≥0，当前: {self.min_sharpe_ratio}")

        if not 0.0 < self.max_drawdown <= 1.0:
            raise ValueError(f"max_drawdown必须在(0.0, 1.0]范围内，当前: {self.max_drawdown}")

        if not 0.0 <= self.min_win_rate <= 1.0:
            raise ValueError(f"min_win_rate必须在[0.0, 1.0]范围内，当前: {self.min_win_rate}")

        if self.min_profit_factor < 0:
            raise ValueError(f"min_profit_factor必须≥0，当前: {self.min_profit_factor}")

        if not 0.0 <= self.min_arena_score <= 1.0:
            raise ValueError(f"min_arena_score必须在[0.0, 1.0]范围内，当前: {self.min_arena_score}")


# 白皮书定义的认证标准
CERTIFICATION_STANDARDS = {
    CertificationLevel.PLATINUM: CertificationCriteria(
        min_sharpe_ratio=2.5,
        max_drawdown=0.10,
        min_win_rate=0.65,
        min_profit_factor=1.8,
        min_total_return=0.10,
        min_arena_score=0.90,
    ),
    CertificationLevel.GOLD: CertificationCriteria(
        min_sharpe_ratio=2.0,
        max_drawdown=0.12,
        min_win_rate=0.60,
        min_profit_factor=1.5,
        min_total_return=0.08,
        min_arena_score=0.80,
    ),
    CertificationLevel.SILVER: CertificationCriteria(
        min_sharpe_ratio=1.5,
        max_drawdown=0.15,
        min_win_rate=0.55,
        min_profit_factor=1.3,
        min_total_return=0.05,
        min_arena_score=0.75,
    ),
}


@dataclass
class CertificationResult:
    """认证结果

    Attributes:
        eligible: 是否符合认证条件
        certification_level: 认证等级（如果符合）
        reason: 不符合原因（如果不符合）
        metrics_summary: 指标摘要
    """

    eligible: bool
    certification_level: Optional[CertificationLevel] = None
    reason: str = ""
    metrics_summary: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证结果一致性"""
        if self.eligible and self.certification_level is None:
            raise ValueError("eligible为True时，certification_level不能为None")

        if not self.eligible and not self.reason:
            raise ValueError("eligible为False时，必须提供reason")
