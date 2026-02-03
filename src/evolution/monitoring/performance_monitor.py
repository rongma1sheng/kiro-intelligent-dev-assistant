"""Performance Monitor for Continuous Monitoring

白皮书依据: 第四章 4.6.1 每日因子监控
"""

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.evolution.monitoring.data_models import (
    FactorPerformanceRecord,
    StrategyPerformanceRecord,
)


class PerformanceMonitor:
    """性能监控器

    白皮书依据: 第四章 4.6.1 每日因子监控

    监控因子和策略的每日性能指标，包括IC、IR、夏普比率等。

    Attributes:
        factor_records: 因子性能记录字典 {factor_id: [records]}
        strategy_records: 策略性能记录字典 {strategy_id: [records]}
        ic_warning_threshold: IC警告阈值，默认0.03
    """

    def __init__(self, ic_warning_threshold: float = 0.03):
        """初始化性能监控器

        Args:
            ic_warning_threshold: IC警告阈值，默认0.03

        Raises:
            ValueError: 当ic_warning_threshold <= 0时
        """
        if ic_warning_threshold <= 0:
            raise ValueError(f"ic_warning_threshold必须>0，当前: {ic_warning_threshold}")

        self.factor_records: Dict[str, List[FactorPerformanceRecord]] = {}
        self.strategy_records: Dict[str, List[StrategyPerformanceRecord]] = {}
        self.ic_warning_threshold = ic_warning_threshold

        logger.info(f"初始化PerformanceMonitor: ic_warning_threshold={ic_warning_threshold}")

    def record_factor_performance(
        self, factor_id: str, date: datetime, ic: float, ir: float, sharpe_ratio: Optional[float] = None
    ) -> FactorPerformanceRecord:
        """记录因子性能

        白皮书依据: 第四章 4.6.1 每日因子监控 - Requirement 8.1

        Args:
            factor_id: 因子ID
            date: 日期
            ic: 信息系数
            ir: 信息比率
            sharpe_ratio: 夏普比率（可选）

        Returns:
            因子性能记录

        Raises:
            ValueError: 当参数无效时
        """
        # 检查是否触发警告
        is_warning = ic < self.ic_warning_threshold

        # 创建性能记录
        record = FactorPerformanceRecord(
            factor_id=factor_id, date=date, ic=ic, ir=ir, sharpe_ratio=sharpe_ratio, is_warning=is_warning
        )

        # 存储记录
        if factor_id not in self.factor_records:
            self.factor_records[factor_id] = []

        self.factor_records[factor_id].append(record)

        # 记录日志
        if is_warning:
            logger.warning(
                f"因子性能警告: "
                f"factor_id={factor_id}, "
                f"date={date.strftime('%Y-%m-%d')}, "
                f"ic={ic:.4f} < threshold={self.ic_warning_threshold}"
            )
        else:
            logger.debug(
                f"记录因子性能: "
                f"factor_id={factor_id}, "
                f"date={date.strftime('%Y-%m-%d')}, "
                f"ic={ic:.4f}, "
                f"ir={ir:.4f}"
            )

        return record

    def record_strategy_performance(
        self, strategy_id: str, date: datetime, sharpe_ratio: float, max_drawdown: float, win_rate: float
    ) -> StrategyPerformanceRecord:
        """记录策略性能

        白皮书依据: 第四章 4.6.5 策略性能监控 - Requirement 8.8

        Args:
            strategy_id: 策略ID
            date: 日期
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率

        Returns:
            策略性能记录

        Raises:
            ValueError: 当参数无效时
        """
        # 检查是否需要进入监控状态
        is_monitoring = sharpe_ratio < 1.0

        # 创建性能记录
        record = StrategyPerformanceRecord(
            strategy_id=strategy_id,
            date=date,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            is_monitoring=is_monitoring,
        )

        # 存储记录
        if strategy_id not in self.strategy_records:
            self.strategy_records[strategy_id] = []

        self.strategy_records[strategy_id].append(record)

        # 记录日志
        if is_monitoring:
            logger.warning(
                f"策略进入监控状态: "
                f"strategy_id={strategy_id}, "
                f"date={date.strftime('%Y-%m-%d')}, "
                f"sharpe_ratio={sharpe_ratio:.4f} < 1.0"
            )
        else:
            logger.debug(
                f"记录策略性能: "
                f"strategy_id={strategy_id}, "
                f"date={date.strftime('%Y-%m-%d')}, "
                f"sharpe_ratio={sharpe_ratio:.4f}, "
                f"max_drawdown={max_drawdown:.4f}, "
                f"win_rate={win_rate:.4f}"
            )

        return record

    def get_factor_records(self, factor_id: str, days: Optional[int] = None) -> List[FactorPerformanceRecord]:
        """获取因子性能记录

        Args:
            factor_id: 因子ID
            days: 获取最近N天的记录，None表示全部

        Returns:
            因子性能记录列表
        """
        if factor_id not in self.factor_records:
            return []

        records = self.factor_records[factor_id]

        if days is None:
            return records

        return records[-days:] if len(records) >= days else records

    def get_strategy_records(self, strategy_id: str, days: Optional[int] = None) -> List[StrategyPerformanceRecord]:
        """获取策略性能记录

        Args:
            strategy_id: 策略ID
            days: 获取最近N天的记录，None表示全部

        Returns:
            策略性能记录列表
        """
        if strategy_id not in self.strategy_records:
            return []

        records = self.strategy_records[strategy_id]

        if days is None:
            return records

        return records[-days:] if len(records) >= days else records

    def get_consecutive_low_ic_days(self, factor_id: str) -> int:
        """获取连续低IC天数

        白皮书依据: 第四章 4.6.3 连续天数衰减检测 - Requirement 8.3

        Args:
            factor_id: 因子ID

        Returns:
            连续低IC天数
        """
        records = self.get_factor_records(factor_id)

        if not records:
            return 0

        # 从最新记录开始向前统计
        consecutive_days = 0
        for record in reversed(records):
            if record.ic < self.ic_warning_threshold:
                consecutive_days += 1
            else:
                break

        return consecutive_days

    def get_average_ic(self, factor_id: str, days: Optional[int] = None) -> float:
        """获取平均IC

        Args:
            factor_id: 因子ID
            days: 计算最近N天的平均IC，None表示全部

        Returns:
            平均IC
        """
        records = self.get_factor_records(factor_id, days)

        if not records:
            return 0.0

        ic_values = [r.ic for r in records]
        return sum(ic_values) / len(ic_values)

    def has_warning(self, factor_id: str) -> bool:
        """检查因子是否有警告

        Args:
            factor_id: 因子ID

        Returns:
            是否有警告
        """
        records = self.get_factor_records(factor_id)

        if not records:
            return False

        # 检查最新记录
        return records[-1].is_warning
