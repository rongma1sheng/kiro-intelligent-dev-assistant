"""
信号聚合器 (Signal Aggregator)

白皮书依据: 第一章 1.5.2 战争态任务调度
- 19个策略并行生成信号
- 信号聚合与冲突解决

功能:
- 收集多策略信号
- 信号冲突解决
- 生成最终交易信号
"""

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class SignalDirection(Enum):
    """信号方向"""

    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"


class SignalStrength(Enum):
    """信号强度"""

    WEAK = "弱"
    MEDIUM = "中"
    STRONG = "强"


class ConflictResolution(Enum):
    """冲突解决策略"""

    MAJORITY = "多数决"  # 多数信号方向
    WEIGHTED = "加权"  # 按权重加权
    CONSERVATIVE = "保守"  # 有卖出就卖出
    AGGRESSIVE = "激进"  # 有买入就买入
    PRIORITY = "优先级"  # 按策略优先级


@dataclass
class TradingSignal:
    """交易信号

    Attributes:
        symbol: 标的代码
        direction: 信号方向
        strength: 信号强度
        strategy_name: 策略名称
        confidence: 置信度 (0-1)
        target_position: 目标仓位比例
        reason: 信号原因
        timestamp: 时间戳
    """

    symbol: str
    direction: SignalDirection
    strength: SignalStrength = SignalStrength.MEDIUM
    strategy_name: str = ""
    confidence: float = 0.5
    target_position: float = 0.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "strategy_name": self.strategy_name,
            "confidence": self.confidence,
            "target_position": self.target_position,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AggregatedSignal:
    """聚合信号

    Attributes:
        symbol: 标的代码
        direction: 最终方向
        strength: 最终强度
        confidence: 综合置信度
        target_position: 目标仓位
        contributing_strategies: 贡献策略列表
        buy_count: 买入信号数
        sell_count: 卖出信号数
        hold_count: 持有信号数
        timestamp: 时间戳
    """

    symbol: str
    direction: SignalDirection
    strength: SignalStrength = SignalStrength.MEDIUM
    confidence: float = 0.5
    target_position: float = 0.0
    contributing_strategies: List[str] = field(default_factory=list)
    buy_count: int = 0
    sell_count: int = 0
    hold_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "target_position": self.target_position,
            "contributing_strategies": self.contributing_strategies,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "hold_count": self.hold_count,
            "timestamp": self.timestamp.isoformat(),
        }


class SignalAggregator:
    """信号聚合器

    白皮书依据: 第一章 1.5.2 战争态任务调度

    负责收集多策略信号，解决冲突，生成最终交易信号。

    Attributes:
        resolution_strategy: 冲突解决策略
        strategy_weights: 策略权重字典
        strategy_priorities: 策略优先级字典
        on_signal: 聚合信号回调

    Example:
        >>> aggregator = SignalAggregator()
        >>> aggregator.register_strategy("momentum", weight=1.5)
        >>> aggregator.add_signal(signal)
        >>> result = aggregator.aggregate("000001.SZ")
    """

    def __init__(
        self,
        resolution_strategy: ConflictResolution = ConflictResolution.WEIGHTED,
        min_confidence: float = 0.3,
        signal_timeout: float = 60.0,
    ):
        """初始化信号聚合器

        Args:
            resolution_strategy: 冲突解决策略
            min_confidence: 最小置信度阈值
            signal_timeout: 信号超时时间(秒)
        """
        self.resolution_strategy = resolution_strategy
        self.min_confidence = min_confidence
        self.signal_timeout = signal_timeout

        # 策略配置
        self.strategy_weights: Dict[str, float] = {}
        self.strategy_priorities: Dict[str, int] = {}

        # 信号缓存 {symbol: [signals]}
        self._signal_cache: Dict[str, List[TradingSignal]] = defaultdict(list)

        # 回调函数
        self.on_signal: Optional[Callable[[AggregatedSignal], None]] = None

        self._lock = threading.RLock()
        self._is_running = False

        logger.info(f"信号聚合器初始化: " f"冲突解决策略={resolution_strategy.value}")

    def register_strategy(self, strategy_name: str, weight: float = 1.0, priority: int = 5) -> None:
        """注册策略

        Args:
            strategy_name: 策略名称
            weight: 策略权重 (默认1.0)
            priority: 策略优先级 (1-10，越大越优先)
        """
        with self._lock:
            self.strategy_weights[strategy_name] = weight
            self.strategy_priorities[strategy_name] = priority
            logger.info(f"注册策略: {strategy_name}, 权重={weight}, 优先级={priority}")

    def unregister_strategy(self, strategy_name: str) -> None:
        """注销策略

        Args:
            strategy_name: 策略名称
        """
        with self._lock:
            if strategy_name in self.strategy_weights:
                del self.strategy_weights[strategy_name]
            if strategy_name in self.strategy_priorities:
                del self.strategy_priorities[strategy_name]
            logger.info(f"注销策略: {strategy_name}")

    def add_signal(self, signal: TradingSignal) -> None:
        """添加信号

        Args:
            signal: 交易信号
        """
        with self._lock:
            # 清理过期信号
            self._cleanup_expired_signals(signal.symbol)

            # 添加新信号
            self._signal_cache[signal.symbol].append(signal)

            logger.debug(f"添加信号: {signal.symbol} {signal.direction.value} " f"from {signal.strategy_name}")

    def add_signals(self, signals: List[TradingSignal]) -> None:
        """批量添加信号

        Args:
            signals: 信号列表
        """
        for signal in signals:
            self.add_signal(signal)

    def aggregate(self, symbol: str) -> Optional[AggregatedSignal]:
        """聚合信号

        Args:
            symbol: 标的代码

        Returns:
            聚合后的信号
        """
        with self._lock:
            # 清理过期信号
            self._cleanup_expired_signals(symbol)

            signals = self._signal_cache.get(symbol, [])

            if not signals:
                return None

            # 过滤低置信度信号
            valid_signals = [s for s in signals if s.confidence >= self.min_confidence]

            if not valid_signals:
                return None

            # 根据策略聚合
            if self.resolution_strategy == ConflictResolution.MAJORITY:
                result = self._aggregate_majority(symbol, valid_signals)
            elif self.resolution_strategy == ConflictResolution.WEIGHTED:
                result = self._aggregate_weighted(symbol, valid_signals)
            elif self.resolution_strategy == ConflictResolution.CONSERVATIVE:
                result = self._aggregate_conservative(symbol, valid_signals)
            elif self.resolution_strategy == ConflictResolution.AGGRESSIVE:
                result = self._aggregate_aggressive(symbol, valid_signals)
            elif self.resolution_strategy == ConflictResolution.PRIORITY:
                result = self._aggregate_priority(symbol, valid_signals)
            else:
                result = self._aggregate_majority(symbol, valid_signals)

            # 触发回调
            if result and self.on_signal:
                try:
                    self.on_signal(result)  # pylint: disable=e1102
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"信号回调失败: {e}")

            return result

    def aggregate_all(self) -> Dict[str, AggregatedSignal]:
        """聚合所有标的信号

        Returns:
            {symbol: AggregatedSignal}
        """
        results = {}

        with self._lock:
            symbols = list(self._signal_cache.keys())

        for symbol in symbols:
            result = self.aggregate(symbol)
            if result:
                results[symbol] = result

        return results

    def _cleanup_expired_signals(self, symbol: str) -> None:
        """清理过期信号"""
        now = datetime.now()

        if symbol in self._signal_cache:
            self._signal_cache[symbol] = [
                s for s in self._signal_cache[symbol] if (now - s.timestamp).total_seconds() < self.signal_timeout
            ]

    def _aggregate_majority(self, symbol: str, signals: List[TradingSignal]) -> AggregatedSignal:
        """多数决聚合"""
        buy_count = sum(1 for s in signals if s.direction == SignalDirection.BUY)
        sell_count = sum(1 for s in signals if s.direction == SignalDirection.SELL)
        hold_count = sum(1 for s in signals if s.direction == SignalDirection.HOLD)

        # 确定方向
        if buy_count > sell_count and buy_count > hold_count:
            direction = SignalDirection.BUY
        elif sell_count > buy_count and sell_count > hold_count:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.HOLD

        # 计算置信度
        total = len(signals)
        if direction == SignalDirection.BUY:
            confidence = buy_count / total
        elif direction == SignalDirection.SELL:
            confidence = sell_count / total
        else:
            confidence = hold_count / total

        # 计算目标仓位
        target_positions = [s.target_position for s in signals if s.direction == direction]
        target_position = sum(target_positions) / len(target_positions) if target_positions else 0.0

        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            strength=self._calculate_strength(confidence),
            confidence=confidence,
            target_position=target_position,
            contributing_strategies=[s.strategy_name for s in signals if s.direction == direction],
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
        )

    def _aggregate_weighted(self, symbol: str, signals: List[TradingSignal]) -> AggregatedSignal:
        """加权聚合"""
        buy_weight = 0.0
        sell_weight = 0.0
        hold_weight = 0.0

        buy_count = 0
        sell_count = 0
        hold_count = 0

        for signal in signals:
            weight = self.strategy_weights.get(signal.strategy_name, 1.0)
            weighted_score = weight * signal.confidence

            if signal.direction == SignalDirection.BUY:
                buy_weight += weighted_score
                buy_count += 1
            elif signal.direction == SignalDirection.SELL:
                sell_weight += weighted_score
                sell_count += 1
            else:
                hold_weight += weighted_score
                hold_count += 1

        # 确定方向
        if buy_weight > sell_weight and buy_weight > hold_weight:
            direction = SignalDirection.BUY
            confidence = buy_weight / (buy_weight + sell_weight + hold_weight)
        elif sell_weight > buy_weight and sell_weight > hold_weight:
            direction = SignalDirection.SELL
            confidence = sell_weight / (buy_weight + sell_weight + hold_weight)
        else:
            direction = SignalDirection.HOLD
            confidence = (
                hold_weight / (buy_weight + sell_weight + hold_weight)
                if (buy_weight + sell_weight + hold_weight) > 0
                else 0.5
            )

        # 计算目标仓位
        target_positions = [s.target_position for s in signals if s.direction == direction]
        target_position = sum(target_positions) / len(target_positions) if target_positions else 0.0

        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            strength=self._calculate_strength(confidence),
            confidence=confidence,
            target_position=target_position,
            contributing_strategies=[s.strategy_name for s in signals if s.direction == direction],
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
        )

    def _aggregate_conservative(self, symbol: str, signals: List[TradingSignal]) -> AggregatedSignal:
        """保守聚合 - 有卖出就卖出"""
        sell_signals = [s for s in signals if s.direction == SignalDirection.SELL]

        if sell_signals:
            direction = SignalDirection.SELL
            confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)
            target_position = sum(s.target_position for s in sell_signals) / len(sell_signals)
            contributing = [s.strategy_name for s in sell_signals]
        else:
            return self._aggregate_majority(symbol, signals)

        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            strength=self._calculate_strength(confidence),
            confidence=confidence,
            target_position=target_position,
            contributing_strategies=contributing,
            buy_count=sum(1 for s in signals if s.direction == SignalDirection.BUY),
            sell_count=len(sell_signals),
            hold_count=sum(1 for s in signals if s.direction == SignalDirection.HOLD),
        )

    def _aggregate_aggressive(self, symbol: str, signals: List[TradingSignal]) -> AggregatedSignal:
        """激进聚合 - 有买入就买入"""
        buy_signals = [s for s in signals if s.direction == SignalDirection.BUY]

        if buy_signals:
            direction = SignalDirection.BUY
            confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)
            target_position = sum(s.target_position for s in buy_signals) / len(buy_signals)
            contributing = [s.strategy_name for s in buy_signals]
        else:
            return self._aggregate_majority(symbol, signals)

        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            strength=self._calculate_strength(confidence),
            confidence=confidence,
            target_position=target_position,
            contributing_strategies=contributing,
            buy_count=len(buy_signals),
            sell_count=sum(1 for s in signals if s.direction == SignalDirection.SELL),
            hold_count=sum(1 for s in signals if s.direction == SignalDirection.HOLD),
        )

    def _aggregate_priority(self, symbol: str, signals: List[TradingSignal]) -> AggregatedSignal:
        """优先级聚合 - 按策略优先级"""
        # 按优先级排序
        sorted_signals = sorted(signals, key=lambda s: self.strategy_priorities.get(s.strategy_name, 5), reverse=True)

        # 取最高优先级的信号
        top_signal = sorted_signals[0]

        return AggregatedSignal(
            symbol=symbol,
            direction=top_signal.direction,
            strength=top_signal.strength,
            confidence=top_signal.confidence,
            target_position=top_signal.target_position,
            contributing_strategies=[top_signal.strategy_name],
            buy_count=sum(1 for s in signals if s.direction == SignalDirection.BUY),
            sell_count=sum(1 for s in signals if s.direction == SignalDirection.SELL),
            hold_count=sum(1 for s in signals if s.direction == SignalDirection.HOLD),
        )

    def _calculate_strength(self, confidence: float) -> SignalStrength:
        """计算信号强度"""
        if confidence >= 0.7:  # pylint: disable=no-else-return
            return SignalStrength.STRONG
        elif confidence >= 0.4:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

    def clear_signals(self, symbol: Optional[str] = None) -> None:
        """清除信号

        Args:
            symbol: 标的代码，None表示清除所有
        """
        with self._lock:
            if symbol:
                if symbol in self._signal_cache:
                    del self._signal_cache[symbol]
            else:
                self._signal_cache.clear()

    def get_signal_count(self, symbol: Optional[str] = None) -> int:
        """获取信号数量

        Args:
            symbol: 标的代码，None表示所有

        Returns:
            信号数量
        """
        with self._lock:
            if symbol:  # pylint: disable=no-else-return
                return len(self._signal_cache.get(symbol, []))
            else:
                return sum(len(signals) for signals in self._signal_cache.values())

    def get_registered_strategies(self) -> List[str]:
        """获取已注册策略列表

        Returns:
            策略名称列表
        """
        return list(self.strategy_weights.keys())
