"""Data Models for Performance Monitoring and Decay Detection

白皮书依据: 第四章 4.6 性能监控与衰减检测
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DecaySeverity(Enum):
    """衰减严重程度

    白皮书依据: 第四章 4.6.3 衰减严重程度分类
    """

    NONE = "none"  # 无衰减
    MILD = "mild"  # 轻度衰减
    MODERATE = "moderate"  # 中度衰减
    SEVERE = "severe"  # 严重衰减


class DecayAction(Enum):
    """衰减响应动作

    白皮书依据: 第四章 4.6.4 衰减响应动作
    """

    NONE = "none"  # 无动作
    REDUCE_WEIGHT = "reduce_weight"  # 降低权重
    PAUSE_AND_RETEST = "pause_and_retest"  # 暂停并重新测试
    RETIRE_IMMEDIATELY = "retire_immediately"  # 立即退役
    CONVERT_TO_RISK_FACTOR = "convert_to_risk_factor"  # 转换为风险因子


@dataclass
class FactorPerformanceRecord:
    """因子性能记录

    白皮书依据: 第四章 4.6.1 每日因子监控

    Attributes:
        factor_id: 因子ID
        date: 日期
        ic: 信息系数
        ir: 信息比率
        sharpe_ratio: 夏普比率
        is_warning: 是否触发警告
    """

    factor_id: str
    date: datetime
    ic: float
    ir: float
    sharpe_ratio: Optional[float] = None
    is_warning: bool = False

    def __post_init__(self):
        """验证数据有效性"""
        if not self.factor_id:
            raise ValueError("factor_id不能为空")

        if not isinstance(self.date, datetime):
            raise TypeError(f"date必须是datetime类型，当前: {type(self.date)}")

        if not -1 <= self.ic <= 1:
            raise ValueError(f"IC必须在[-1,1]范围内，当前: {self.ic}")

        # IR可以是任意值，但通常在合理范围内
        if abs(self.ir) > 10:
            raise ValueError(f"IR超出合理范围[-10,10]，当前: {self.ir}")


@dataclass
class DecayDetectionResult:
    """衰减检测结果

    白皮书依据: 第四章 4.6.3 衰减检测

    Attributes:
        factor_id: 因子ID
        detection_date: 检测日期
        consecutive_low_ic_days: 连续低IC天数
        severity: 衰减严重程度
        recommended_action: 推荐动作
        current_ic: 当前IC
        average_ic: 平均IC
        ic_threshold: IC阈值
        is_decaying: 是否正在衰减
    """

    factor_id: str
    detection_date: datetime
    consecutive_low_ic_days: int
    severity: DecaySeverity
    recommended_action: DecayAction
    current_ic: float
    average_ic: float
    ic_threshold: float = 0.03
    is_decaying: bool = False

    def __post_init__(self):
        """验证数据有效性"""
        if not self.factor_id:
            raise ValueError("factor_id不能为空")

        if not isinstance(self.detection_date, datetime):
            raise TypeError(f"detection_date必须是datetime类型，当前: {type(self.detection_date)}")

        if self.consecutive_low_ic_days < 0:
            raise ValueError(f"consecutive_low_ic_days不能为负数，当前: {self.consecutive_low_ic_days}")

        if not isinstance(self.severity, DecaySeverity):
            raise TypeError(f"severity必须是DecaySeverity类型，当前: {type(self.severity)}")

        if not isinstance(self.recommended_action, DecayAction):
            raise TypeError(f"recommended_action必须是DecayAction类型，当前: {type(self.recommended_action)}")

        if not -1 <= self.current_ic <= 1:
            raise ValueError(f"current_ic必须在[-1,1]范围内，当前: {self.current_ic}")

        if self.ic_threshold <= 0:
            raise ValueError(f"ic_threshold必须>0，当前: {self.ic_threshold}")


@dataclass
class StrategyPerformanceRecord:
    """策略性能记录

    白皮书依据: 第四章 4.6.5 策略性能监控

    Attributes:
        strategy_id: 策略ID
        date: 日期
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 胜率
        is_monitoring: 是否进入监控状态
    """

    strategy_id: str
    date: datetime
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    is_monitoring: bool = False

    def __post_init__(self):
        """验证数据有效性"""
        if not self.strategy_id:
            raise ValueError("strategy_id不能为空")

        if not isinstance(self.date, datetime):
            raise TypeError(f"date必须是datetime类型，当前: {type(self.date)}")

        if self.max_drawdown > 0:
            raise ValueError(f"max_drawdown必须<=0，当前: {self.max_drawdown}")

        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"win_rate必须在[0,1]范围内，当前: {self.win_rate}")
