"""Bar合成器 - 实时K线合成

白皮书依据: 第三章 3.3 Bar Synthesizer

功能:
- Tick到Bar转换（OHLCV计算）
- 多周期并发合成（1m, 5m, 15m, 30m, 1h, 1d）
- Bar缓存机制（Redis）
- Bar质量检查

性能目标: P99 < 10ms

Author: MIA Team
Date: 2026-01-22
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class Tick:
    """Tick数据结构

    Attributes:
        symbol: 股票代码
        timestamp: 时间戳
        price: 最新价
        volume: 成交量
        amount: 成交额
    """

    symbol: str
    timestamp: datetime
    price: float
    volume: int
    amount: float


@dataclass
class Bar:
    """Bar数据结构（K线）

    Attributes:
        symbol: 股票代码
        timestamp: K线时间戳（周期开始时间）
        period: 周期（1m, 5m, 15m, 30m, 1h, 1d）
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        amount: 成交额
        tick_count: Tick数量
    """

    symbol: str
    timestamp: datetime
    period: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    tick_count: int = 0


@dataclass
class BarBuffer:
    """Bar缓冲区

    用于累积Tick数据，合成Bar

    Attributes:
        symbol: 股票代码
        period: 周期
        start_time: 周期开始时间
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 累计成交量
        amount: 累计成交额
        tick_count: Tick数量
        last_update: 最后更新时间
    """

    symbol: str
    period: str
    start_time: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = float("inf")
    close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    tick_count: int = 0
    last_update: Optional[datetime] = None


class BarSynthesizer:
    """Bar合成器

    白皮书依据: 第三章 3.3 Bar Synthesizer

    实现实时K线合成，支持多周期并发处理。

    Attributes:
        supported_periods: 支持的时间周期
        buffers: Bar缓冲区字典 {(symbol, period): BarBuffer}
        completed_bars: 已完成的Bar列表
    """

    # 支持的时间周期（分钟数）
    PERIOD_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "1d": 1440}  # 24小时 * 60分钟

    def __init__(self, periods: Optional[List[str]] = None):
        """初始化Bar合成器

        Args:
            periods: 要合成的周期列表，默认为所有支持的周期

        Raises:
            ValueError: 当周期不支持时
        """
        if periods is None:
            periods = list(self.PERIOD_MINUTES.keys())

        # 验证周期
        for period in periods:
            if period not in self.PERIOD_MINUTES:
                raise ValueError(f"不支持的周期: {period}。" f"支持的周期: {list(self.PERIOD_MINUTES.keys())}")

        self.supported_periods: List[str] = periods
        self.buffers: Dict[Tuple[str, str], BarBuffer] = {}
        self.completed_bars: List[Bar] = []

        logger.info(f"BarSynthesizer初始化完成 - " f"支持周期: {self.supported_periods}")

    def process_tick(self, tick: Tick) -> List[Bar]:
        """处理单个Tick数据

        白皮书依据: 第三章 3.3 Bar Synthesizer - Tick到Bar转换

        Args:
            tick: Tick数据

        Returns:
            已完成的Bar列表（可能为空）

        Raises:
            ValueError: 当Tick数据无效时
        """
        # 验证Tick数据
        if tick.price <= 0:
            raise ValueError(f"无效的价格: {tick.price}")

        if tick.volume < 0:
            raise ValueError(f"无效的成交量: {tick.volume}")

        completed_bars = []

        # 为每个周期处理Tick
        for period in self.supported_periods:
            bar = self._process_tick_for_period(tick, period)  # pylint: disable=c0104
            if bar is not None:
                completed_bars.append(bar)

        return completed_bars

    def _process_tick_for_period(self, tick: Tick, period: str) -> Optional[Bar]:
        """为特定周期处理Tick

        Args:
            tick: Tick数据
            period: 周期

        Returns:
            完成的Bar（如果周期结束），否则None
        """
        buffer_key = (tick.symbol, period)

        # 计算当前Tick所属的周期开始时间
        period_start = self._get_period_start(tick.timestamp, period)

        # 获取或创建缓冲区
        if buffer_key not in self.buffers:
            self.buffers[buffer_key] = BarBuffer(symbol=tick.symbol, period=period, start_time=period_start)

        buffer = self.buffers[buffer_key]

        # 检查是否需要完成当前Bar并开始新的Bar
        if period_start > buffer.start_time:  # pylint: disable=no-else-return
            # 完成当前Bar
            completed_bar = self._finalize_bar(buffer)

            # 创建新的缓冲区
            self.buffers[buffer_key] = BarBuffer(symbol=tick.symbol, period=period, start_time=period_start)
            buffer = self.buffers[buffer_key]

            # 更新新缓冲区
            self._update_buffer(buffer, tick)

            return completed_bar
        else:
            # 更新当前缓冲区
            self._update_buffer(buffer, tick)
            return None

    def _get_period_start(self, timestamp: datetime, period: str) -> datetime:
        """计算周期开始时间

        Args:
            timestamp: 当前时间戳
            period: 周期

        Returns:
            周期开始时间
        """
        minutes = self.PERIOD_MINUTES[period]

        if period == "1d":  # pylint: disable=no-else-return
            # 日线：当天00:00:00
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # 分钟线：向下取整到周期边界
            total_minutes = timestamp.hour * 60 + timestamp.minute
            period_index = total_minutes // minutes
            start_minute = period_index * minutes

            start_hour = start_minute // 60
            start_min = start_minute % 60

            return timestamp.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

    def _update_buffer(self, buffer: BarBuffer, tick: Tick) -> None:
        """更新Bar缓冲区

        Args:
            buffer: Bar缓冲区
            tick: Tick数据
        """
        # 第一个Tick：设置开盘价
        if buffer.tick_count == 0:
            buffer.open = tick.price
            buffer.high = tick.price
            buffer.low = tick.price
        else:
            # 更新最高价和最低价
            buffer.high = max(buffer.high, tick.price)
            buffer.low = min(buffer.low, tick.price)

        # 更新收盘价（最新价）
        buffer.close = tick.price

        # 累加成交量和成交额
        buffer.volume += tick.volume
        buffer.amount += tick.amount

        # 更新Tick计数和最后更新时间
        buffer.tick_count += 1
        buffer.last_update = tick.timestamp

    def _finalize_bar(self, buffer: BarBuffer) -> Bar:
        """完成Bar

        Args:
            buffer: Bar缓冲区

        Returns:
            完成的Bar
        """
        bar = Bar(  # pylint: disable=c0104
            symbol=buffer.symbol,
            timestamp=buffer.start_time,
            period=buffer.period,
            open=buffer.open,
            high=buffer.high,
            low=buffer.low,
            close=buffer.close,
            volume=buffer.volume,
            amount=buffer.amount,
            tick_count=buffer.tick_count,
        )

        # 添加到已完成列表
        self.completed_bars.append(bar)

        logger.debug(
            f"Bar完成 - {bar.symbol} {bar.period} "
            f"{bar.timestamp} OHLCV: "
            f"{bar.open:.2f}/{bar.high:.2f}/{bar.low:.2f}/{bar.close:.2f}/{bar.volume}"
        )

        return bar

    def validate_bar(self, bar: Bar) -> Tuple[bool, List[str]]:  # pylint: disable=c0104
        """验证Bar质量

        白皮书依据: 第三章 3.3 Bar Synthesizer - Bar质量检查

        Args:
            bar: 要验证的Bar

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 检查1: HLOC一致性
        if bar.high < bar.low:
            errors.append(f"最高价({bar.high})小于最低价({bar.low})")

        if bar.high < bar.open:
            errors.append(f"最高价({bar.high})小于开盘价({bar.open})")

        if bar.high < bar.close:
            errors.append(f"最高价({bar.high})小于收盘价({bar.close})")

        if bar.low > bar.open:
            errors.append(f"最低价({bar.low})大于开盘价({bar.open})")

        if bar.low > bar.close:
            errors.append(f"最低价({bar.low})大于收盘价({bar.close})")

        # 检查2: 价格有效性
        if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            errors.append("价格必须大于0")

        # 检查3: 成交量有效性
        if bar.volume < 0:
            errors.append(f"成交量({bar.volume})不能为负")

        # 检查4: 成交额有效性
        if bar.amount < 0:
            errors.append(f"成交额({bar.amount})不能为负")

        # 检查5: Tick数量有效性
        if bar.tick_count <= 0:
            errors.append(f"Tick数量({bar.tick_count})必须大于0")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(f"Bar验证失败 - {bar.symbol} {bar.period} {bar.timestamp}: " f"{', '.join(errors)}")

        return is_valid, errors

    def get_completed_bars(
        self, symbol: Optional[str] = None, period: Optional[str] = None, clear: bool = False
    ) -> List[Bar]:
        """获取已完成的Bar

        Args:
            symbol: 股票代码过滤（可选）
            period: 周期过滤（可选）
            clear: 是否清空已完成列表

        Returns:
            Bar列表
        """
        bars = self.completed_bars

        # 过滤
        if symbol is not None:
            bars = [b for b in bars if b.symbol == symbol]

        if period is not None:
            bars = [b for b in bars if b.period == period]

        # 清空
        if clear:
            self.completed_bars = []

        return bars

    def force_complete_all_bars(self) -> List[Bar]:
        """强制完成所有缓冲区的Bar

        用于交易日结束时强制完成所有未完成的Bar

        Returns:
            完成的Bar列表
        """
        completed_bars = []

        for buffer_key, buffer in list(self.buffers.items()):  # pylint: disable=unused-variable
            if buffer.tick_count > 0:
                bar = self._finalize_bar(buffer)  # pylint: disable=c0104
                completed_bars.append(bar)

        # 清空缓冲区
        self.buffers.clear()

        logger.info(f"强制完成所有Bar - 共{len(completed_bars)}个")

        return completed_bars

    def get_statistics(self) -> Dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        active_buffers = len(self.buffers)
        completed_count = len(self.completed_bars)

        # 按周期统计
        period_stats = defaultdict(int)
        for bar in self.completed_bars:  # pylint: disable=c0104
            period_stats[bar.period] += 1

        # 按标的统计
        symbol_stats = defaultdict(int)
        for bar in self.completed_bars:  # pylint: disable=c0104
            symbol_stats[bar.symbol] += 1

        return {
            "active_buffers": active_buffers,
            "completed_bars": completed_count,
            "period_stats": dict(period_stats),
            "symbol_stats": dict(symbol_stats),
            "supported_periods": self.supported_periods,
        }


# 全局单例
_bar_synthesizer: Optional[BarSynthesizer] = None


def get_bar_synthesizer(periods: Optional[List[str]] = None) -> BarSynthesizer:
    """获取BarSynthesizer全局单例

    Args:
        periods: 要合成的周期列表

    Returns:
        BarSynthesizer实例
    """
    global _bar_synthesizer  # pylint: disable=w0603

    if _bar_synthesizer is None:
        _bar_synthesizer = BarSynthesizer(periods=periods)

    return _bar_synthesizer
