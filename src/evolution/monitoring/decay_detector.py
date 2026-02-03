"""Decay Detector for Factor Performance Degradation

白皮书依据: 第四章 4.6.3 衰减检测
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from src.evolution.monitoring.data_models import (
    DecayAction,
    DecayDetectionResult,
    DecaySeverity,
)
from src.evolution.monitoring.performance_monitor import PerformanceMonitor


class DecayDetector:
    """衰减检测器

    白皮书依据: 第四章 4.6.3 衰减检测

    检测因子性能衰减并推荐响应动作。

    Attributes:
        performance_monitor: 性能监控器
        ic_threshold: IC阈值，默认0.03
        mild_decay_days: 轻度衰减天数阈值，默认7天
        moderate_decay_days: 中度衰减天数阈值，默认15天
        severe_decay_days: 严重衰减天数阈值，默认30天
    """

    def __init__(
        self,
        performance_monitor: PerformanceMonitor,
        ic_threshold: float = 0.03,
        mild_decay_days: int = 7,
        moderate_decay_days: int = 15,
        severe_decay_days: int = 30,
    ):
        """初始化衰减检测器

        Args:
            performance_monitor: 性能监控器
            ic_threshold: IC阈值，默认0.03
            mild_decay_days: 轻度衰减天数阈值，默认7天
            moderate_decay_days: 中度衰减天数阈值，默认15天
            severe_decay_days: 严重衰减天数阈值，默认30天

        Raises:
            ValueError: 当参数无效时
        """
        if not isinstance(performance_monitor, PerformanceMonitor):
            raise TypeError(f"performance_monitor必须是PerformanceMonitor类型，" f"当前: {type(performance_monitor)}")

        if ic_threshold <= 0:
            raise ValueError(f"ic_threshold必须>0，当前: {ic_threshold}")

        if not (0 < mild_decay_days < moderate_decay_days < severe_decay_days):
            raise ValueError(
                f"衰减天数阈值必须满足: 0 < mild < moderate < severe，"
                f"当前: mild={mild_decay_days}, "
                f"moderate={moderate_decay_days}, "
                f"severe={severe_decay_days}"
            )

        self.performance_monitor = performance_monitor
        self.ic_threshold = ic_threshold
        self.mild_decay_days = mild_decay_days
        self.moderate_decay_days = moderate_decay_days
        self.severe_decay_days = severe_decay_days

        logger.info(
            f"初始化DecayDetector: "
            f"ic_threshold={ic_threshold}, "
            f"mild_decay_days={mild_decay_days}, "
            f"moderate_decay_days={moderate_decay_days}, "
            f"severe_decay_days={severe_decay_days}"
        )

    def detect_decay(self, factor_id: str, detection_date: Optional[datetime] = None) -> DecayDetectionResult:
        """检测因子衰减

        白皮书依据: 第四章 4.6.3 衰减检测 - Requirement 8.3

        Args:
            factor_id: 因子ID
            detection_date: 检测日期，None表示当前时间

        Returns:
            衰减检测结果

        Raises:
            ValueError: 当factor_id无效时
        """
        if not factor_id:
            raise ValueError("factor_id不能为空")

        if detection_date is None:
            detection_date = datetime.now()

        # 获取连续低IC天数
        consecutive_days = self.performance_monitor.get_consecutive_low_ic_days(factor_id)

        # 获取当前IC和平均IC
        records = self.performance_monitor.get_factor_records(factor_id)
        if not records:
            raise ValueError(f"因子{factor_id}没有性能记录")

        current_ic = records[-1].ic
        average_ic = self.performance_monitor.get_average_ic(factor_id)

        # 判断衰减严重程度
        severity = self._classify_severity(consecutive_days)

        # 推荐响应动作
        recommended_action = self._recommend_action(severity)

        # 判断是否正在衰减
        is_decaying = consecutive_days >= self.severe_decay_days

        # 创建检测结果
        result = DecayDetectionResult(
            factor_id=factor_id,
            detection_date=detection_date,
            consecutive_low_ic_days=consecutive_days,
            severity=severity,
            recommended_action=recommended_action,
            current_ic=current_ic,
            average_ic=average_ic,
            ic_threshold=self.ic_threshold,
            is_decaying=is_decaying,
        )

        # 记录日志
        if severity != DecaySeverity.NONE:
            logger.warning(
                f"检测到因子衰减: "
                f"factor_id={factor_id}, "
                f"consecutive_days={consecutive_days}, "
                f"severity={severity.value}, "
                f"recommended_action={recommended_action.value}, "
                f"current_ic={current_ic:.4f}, "
                f"average_ic={average_ic:.4f}"
            )
        else:
            logger.debug(f"因子性能正常: " f"factor_id={factor_id}, " f"current_ic={current_ic:.4f}")

        return result

    def _classify_severity(self, consecutive_days: int) -> DecaySeverity:
        """分类衰减严重程度

        白皮书依据: 第四章 4.6.3 衰减严重程度分类

        Args:
            consecutive_days: 连续低IC天数

        Returns:
            衰减严重程度
        """
        if consecutive_days >= self.severe_decay_days:
            return DecaySeverity.SEVERE
        elif consecutive_days >= self.moderate_decay_days:
            return DecaySeverity.MODERATE
        elif consecutive_days >= self.mild_decay_days:
            return DecaySeverity.MILD
        else:
            return DecaySeverity.NONE

    def _recommend_action(self, severity: DecaySeverity) -> DecayAction:
        """推荐响应动作

        白皮书依据: 第四章 4.6.4 衰减响应动作 - Requirements 8.4, 8.5, 8.6

        Args:
            severity: 衰减严重程度

        Returns:
            推荐动作
        """
        if severity == DecaySeverity.SEVERE:
            return DecayAction.RETIRE_IMMEDIATELY
        elif severity == DecaySeverity.MODERATE:
            return DecayAction.PAUSE_AND_RETEST
        elif severity == DecaySeverity.MILD:
            return DecayAction.REDUCE_WEIGHT
        else:
            return DecayAction.NONE

    def apply_weight_reduction(self, factor_id: str, current_weight: float, reduction_ratio: float = 0.3) -> float:
        """应用权重降低

        白皮书依据: 第四章 4.6.4 轻度衰减响应 - Requirement 8.4

        Args:
            factor_id: 因子ID
            current_weight: 当前权重
            reduction_ratio: 降低比例，默认0.3（30%）

        Returns:
            新权重

        Raises:
            ValueError: 当参数无效时
        """
        if not 0 <= current_weight <= 1:
            raise ValueError(f"current_weight必须在[0,1]范围内，当前: {current_weight}")

        if not 0 < reduction_ratio < 1:
            raise ValueError(f"reduction_ratio必须在(0,1)范围内，当前: {reduction_ratio}")

        new_weight = current_weight * (1 - reduction_ratio)

        logger.info(
            f"应用权重降低: "
            f"factor_id={factor_id}, "
            f"current_weight={current_weight:.4f}, "
            f"reduction_ratio={reduction_ratio:.2f}, "
            f"new_weight={new_weight:.4f}"
        )

        return new_weight

    def convert_to_risk_factor(self, factor_id: str) -> str:
        """转换为风险因子

        白皮书依据: 第四章 4.6.7 退役因子转换 - Requirement 8.7

        Args:
            factor_id: 因子ID

        Returns:
            风险因子ID
        """
        risk_factor_id = f"RISK_{factor_id}"

        logger.info(f"转换为风险因子: " f"factor_id={factor_id} → risk_factor_id={risk_factor_id}")

        return risk_factor_id
