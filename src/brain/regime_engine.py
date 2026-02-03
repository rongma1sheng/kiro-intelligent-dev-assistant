"""
市场状态引擎 (Regime Engine)

白皮书依据: 第一章 1.5.2 战争态任务调度
- 每60秒更新市场状态
- 识别牛市/熊市/震荡等市场状态

功能:
- 实时监控市场状态
- 使用多种方法检测状态变化
- 提供状态转换信号
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from loguru import logger


class MarketRegime(Enum):
    """市场状态枚举

    白皮书依据: 第一章 全域感知 (Omni-Perception)
    """

    BULL = "牛市"  # 上涨趋势
    BEAR = "熊市"  # 下跌趋势
    SIDEWAYS = "震荡"  # 横盘整理
    TRANSITION = "转折"  # 状态转换中
    UNKNOWN = "未知"  # 无法判断


class VolatilityLevel(Enum):
    """波动率水平"""

    LOW = "低波动"
    MEDIUM = "中波动"
    HIGH = "高波动"
    EXTREME = "极端波动"


@dataclass
class RegimeState:
    """市场状态数据

    Attributes:
        regime: 当前市场状态
        volatility: 波动率水平
        trend_strength: 趋势强度 (-1到1)
        confidence: 判断置信度 (0到1)
        duration: 当前状态持续时间(秒)
        last_update: 最后更新时间
        probabilities: 各状态概率分布
    """

    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility: VolatilityLevel = VolatilityLevel.MEDIUM
    trend_strength: float = 0.0
    confidence: float = 0.0
    duration: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)
    probabilities: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "regime": self.regime.value,
            "volatility": self.volatility.value,
            "trend_strength": self.trend_strength,
            "confidence": self.confidence,
            "duration": self.duration,
            "last_update": self.last_update.isoformat(),
            "probabilities": self.probabilities,
        }


class RegimeEngine:
    """市场状态引擎

    白皮书依据: 第一章 1.5.2 战争态任务调度

    负责实时监控和判断市场状态，为策略选择提供依据。

    Attributes:
        update_interval: 更新间隔(秒)，默认60秒
        current_state: 当前市场状态
        state_history: 状态历史记录
        on_regime_change: 状态变化回调

    Example:
        >>> engine = RegimeEngine(update_interval=60)
        >>> engine.on_regime_change = lambda old, new: print(f"{old} -> {new}")
        >>> engine.start()
    """

    def __init__(self, update_interval: int = 60, lookback_period: int = 20, volatility_window: int = 20):
        """初始化市场状态引擎

        Args:
            update_interval: 更新间隔(秒)
            lookback_period: 回看周期(天)
            volatility_window: 波动率计算窗口

        Raises:
            ValueError: 当参数无效时
        """
        if update_interval <= 0:
            raise ValueError(f"更新间隔必须 > 0，当前: {update_interval}")

        self.update_interval = update_interval
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window

        self.current_state = RegimeState()
        self.state_history: List[RegimeState] = []
        self.on_regime_change: Optional[Callable[[MarketRegime, MarketRegime], None]] = None

        self._is_running = False
        self._stop_event = threading.Event()
        self._update_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # 市场数据缓存
        self._price_cache: List[float] = []
        self._volume_cache: List[float] = []
        self._regime_start_time: datetime = datetime.now()

        logger.info(f"市场状态引擎初始化: " f"更新间隔={update_interval}秒, " f"回看周期={lookback_period}天")

    def start(self) -> bool:
        """启动市场状态引擎

        Returns:
            启动是否成功
        """
        if self._is_running:
            logger.warning("市场状态引擎已在运行")
            return True

        try:
            self._is_running = True
            self._stop_event.clear()

            self._update_thread = threading.Thread(target=self._update_loop, name="RegimeEngineThread", daemon=True)
            self._update_thread.start()

            logger.info("市场状态引擎已启动")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self._is_running = False
            logger.error(f"启动市场状态引擎失败: {e}")
            return False

    def stop(self) -> bool:
        """停止市场状态引擎

        Returns:
            停止是否成功
        """
        if not self._is_running:
            return True

        try:
            self._stop_event.set()

            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=5)

            self._is_running = False
            logger.info("市场状态引擎已停止")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"停止市场状态引擎失败: {e}")
            return False

    def _update_loop(self) -> None:
        """更新循环"""
        while not self._stop_event.is_set():
            try:
                self._update_regime()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"更新市场状态失败: {e}")

            self._stop_event.wait(self.update_interval)

    def _update_regime(self) -> None:
        """更新市场状态"""
        with self._lock:
            old_regime = self.current_state.regime

            # 计算新状态
            new_state = self._calculate_regime()

            # 检查状态是否变化
            if new_state.regime != old_regime:
                logger.info(f"市场状态变化: {old_regime.value} -> {new_state.regime.value}")
                self._regime_start_time = datetime.now()

                # 触发回调
                if self.on_regime_change:
                    try:
                        self.on_regime_change(old_regime, new_state.regime)
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.error(f"状态变化回调失败: {e}")

            # 更新持续时间
            new_state.duration = (datetime.now() - self._regime_start_time).total_seconds()

            # 保存历史
            self.state_history.append(self.current_state)
            if len(self.state_history) > 1000:
                self.state_history = self.state_history[-500:]

            self.current_state = new_state

    def _calculate_regime(self) -> RegimeState:
        """计算市场状态

        使用多种方法综合判断:
        1. 趋势判断 (移动平均)
        2. 波动率判断
        3. 动量判断
        """
        state = RegimeState(last_update=datetime.now())

        # 如果没有足够数据，返回未知状态
        if len(self._price_cache) < self.lookback_period:
            state.regime = MarketRegime.UNKNOWN
            state.confidence = 0.0
            return state

        prices = np.array(self._price_cache[-self.lookback_period :])

        # 1. 计算趋势强度
        trend_strength = self._calculate_trend_strength(prices)
        state.trend_strength = trend_strength

        # 2. 计算波动率
        volatility = self._calculate_volatility(prices)
        state.volatility = self._classify_volatility(volatility)

        # 3. 判断市场状态
        regime, confidence, probabilities = self._classify_regime(trend_strength, volatility)
        state.regime = regime
        state.confidence = confidence
        state.probabilities = probabilities

        return state

    def _calculate_trend_strength(self, prices: np.ndarray) -> float:
        """计算趋势强度

        使用线性回归斜率归一化

        Returns:
            趋势强度 (-1到1)
        """
        if len(prices) < 2:
            return 0.0

        # 线性回归
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)

        # 归一化到 [-1, 1]
        price_range = prices.max() - prices.min()
        if price_range > 0:
            normalized_slope = slope * len(prices) / price_range
            return np.clip(normalized_slope, -1, 1)

        return 0.0

    def _calculate_volatility(self, prices: np.ndarray) -> float:
        """计算波动率

        使用收益率标准差年化
        """
        if len(prices) < 2:
            return 0.0

        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # 年化

        return volatility

    def _classify_volatility(self, volatility: float) -> VolatilityLevel:
        """分类波动率水平"""
        if volatility < 0.15:  # pylint: disable=no-else-return
            return VolatilityLevel.LOW
        elif volatility < 0.25:
            return VolatilityLevel.MEDIUM
        elif volatility < 0.40:
            return VolatilityLevel.HIGH
        else:
            return VolatilityLevel.EXTREME

    def _classify_regime(self, trend_strength: float, volatility: float) -> tuple:
        """分类市场状态

        Returns:
            (状态, 置信度, 概率分布)
        """
        # 计算各状态概率
        bull_prob = max(0, trend_strength) * (1 - min(volatility, 1))
        bear_prob = max(0, -trend_strength) * (1 - min(volatility, 1))
        sideways_prob = (1 - abs(trend_strength)) * (1 - min(volatility * 0.5, 1))
        transition_prob = min(volatility, 1) * 0.5

        # 归一化
        total = bull_prob + bear_prob + sideways_prob + transition_prob
        if total > 0:
            bull_prob /= total
            bear_prob /= total
            sideways_prob /= total
            transition_prob /= total

        probabilities = {
            "牛市": round(bull_prob, 3),
            "熊市": round(bear_prob, 3),
            "震荡": round(sideways_prob, 3),
            "转折": round(transition_prob, 3),
        }

        # 选择最高概率的状态
        max_prob = max(bull_prob, bear_prob, sideways_prob, transition_prob)

        if max_prob == bull_prob:
            regime = MarketRegime.BULL
        elif max_prob == bear_prob:
            regime = MarketRegime.BEAR
        elif max_prob == sideways_prob:
            regime = MarketRegime.SIDEWAYS
        else:
            regime = MarketRegime.TRANSITION

        return regime, max_prob, probabilities

    def update_price(self, price: float) -> None:
        """更新价格数据

        Args:
            price: 最新价格
        """
        with self._lock:
            self._price_cache.append(price)
            # 保留最近1000个数据点
            if len(self._price_cache) > 1000:
                self._price_cache = self._price_cache[-500:]

    def update_prices(self, prices: List[float]) -> None:
        """批量更新价格数据

        Args:
            prices: 价格列表
        """
        with self._lock:
            self._price_cache.extend(prices)
            if len(self._price_cache) > 1000:
                self._price_cache = self._price_cache[-500:]

    def get_current_regime(self) -> MarketRegime:
        """获取当前市场状态

        Returns:
            当前市场状态
        """
        with self._lock:
            return self.current_state.regime

    def get_state(self) -> RegimeState:
        """获取完整状态信息

        Returns:
            当前状态数据
        """
        with self._lock:
            return self.current_state

    def get_regime_duration(self) -> float:
        """获取当前状态持续时间(秒)

        Returns:
            持续时间
        """
        with self._lock:
            return self.current_state.duration

    def is_running(self) -> bool:
        """检查引擎是否运行中

        Returns:
            是否运行中
        """
        return self._is_running
