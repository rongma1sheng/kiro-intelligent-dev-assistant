"""
行情数据订阅器 (Market Data Subscriber)

白皮书依据: 第一章 1.5.2 战争态任务调度
- 订阅行情数据流
- 启动Tick处理循环

功能:
- 订阅实时行情数据
- 处理Tick数据流
- 提供数据回调接口
"""

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from loguru import logger


class DataSource(Enum):
    """数据源类型"""

    QMT = "QMT"  # 迅投QMT
    SIMULATION = "模拟"  # 模拟数据
    REPLAY = "回放"  # 历史回放


class SubscriptionStatus(Enum):
    """订阅状态"""

    DISCONNECTED = "未连接"
    CONNECTING = "连接中"
    CONNECTED = "已连接"
    SUBSCRIBED = "已订阅"
    ERROR = "错误"


@dataclass
class TickData:
    """Tick数据

    白皮书依据: 第三章 数据模型

    Attributes:
        symbol: 标的代码
        price: 最新价
        volume: 成交量
        amount: 成交额
        bid_price: 买一价
        ask_price: 卖一价
        bid_volume: 买一量
        ask_volume: 卖一量
        timestamp: 时间戳
    """

    symbol: str
    price: float
    volume: int = 0
    amount: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_volume: int = 0
    ask_volume: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "amount": self.amount,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BarData:
    """K线数据

    Attributes:
        symbol: 标的代码
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        amount: 成交额
        timestamp: 时间戳
    """

    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    amount: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat(),
        }


class MarketDataSubscriber:
    """行情数据订阅器

    白皮书依据: 第一章 1.5.2 战争态任务调度

    负责订阅和处理实时行情数据。

    Attributes:
        data_source: 数据源类型
        status: 订阅状态
        subscribed_symbols: 已订阅标的集合
        on_tick: Tick数据回调
        on_bar: K线数据回调
        on_status_change: 状态变化回调

    Example:
        >>> subscriber = MarketDataSubscriber()
        >>> subscriber.on_tick = lambda tick: print(tick.symbol, tick.price)
        >>> subscriber.connect()
        >>> subscriber.subscribe(["000001.SZ", "600000.SH"])
    """

    def __init__(self, data_source: DataSource = DataSource.SIMULATION, buffer_size: int = 10000):
        """初始化行情订阅器

        Args:
            data_source: 数据源类型
            buffer_size: 数据缓冲区大小
        """
        self.data_source = data_source
        self.buffer_size = buffer_size

        self.status = SubscriptionStatus.DISCONNECTED
        self.subscribed_symbols: Set[str] = set()

        # 数据缓冲区
        self._tick_buffer: Dict[str, deque] = {}
        self._bar_buffer: Dict[str, deque] = {}

        # 回调函数
        self.on_tick: Optional[Callable[[TickData], None]] = None
        self.on_bar: Optional[Callable[[BarData], None]] = None
        self.on_status_change: Optional[Callable[[SubscriptionStatus], None]] = None

        self._is_running = False
        self._stop_event = threading.Event()
        self._data_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # 统计信息
        self._tick_count = 0
        self._last_tick_time: Optional[datetime] = None

        logger.info(f"行情订阅器初始化: 数据源={data_source.value}")

    def connect(self) -> bool:
        """连接数据源

        Returns:
            连接是否成功
        """
        if self.status in [SubscriptionStatus.CONNECTED, SubscriptionStatus.SUBSCRIBED]:
            logger.warning("已连接数据源")
            return True

        try:
            self._set_status(SubscriptionStatus.CONNECTING)

            # 根据数据源类型连接
            if self.data_source == DataSource.QMT:
                success = self._connect_qmt()
            elif self.data_source == DataSource.SIMULATION:
                success = self._connect_simulation()
            elif self.data_source == DataSource.REPLAY:
                success = self._connect_replay()
            else:
                success = False

            if success:
                self._set_status(SubscriptionStatus.CONNECTED)
                logger.info("数据源连接成功")
            else:
                self._set_status(SubscriptionStatus.ERROR)
                logger.error("数据源连接失败")

            return success

        except Exception as e:  # pylint: disable=broad-exception-caught
            self._set_status(SubscriptionStatus.ERROR)
            logger.error(f"连接数据源异常: {e}")
            return False

    def disconnect(self) -> bool:
        """断开数据源

        Returns:
            断开是否成功
        """
        try:
            self.unsubscribe_all()
            self._stop_data_thread()
            self._set_status(SubscriptionStatus.DISCONNECTED)
            logger.info("数据源已断开")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"断开数据源异常: {e}")
            return False

    def subscribe(self, symbols: List[str]) -> bool:
        """订阅标的

        Args:
            symbols: 标的代码列表

        Returns:
            订阅是否成功
        """
        if self.status not in [SubscriptionStatus.CONNECTED, SubscriptionStatus.SUBSCRIBED]:
            logger.error("未连接数据源，无法订阅")
            return False

        try:
            with self._lock:
                for symbol in symbols:
                    if symbol not in self.subscribed_symbols:
                        self.subscribed_symbols.add(symbol)
                        self._tick_buffer[symbol] = deque(maxlen=self.buffer_size)
                        self._bar_buffer[symbol] = deque(maxlen=self.buffer_size)
                        logger.info(f"订阅标的: {symbol}")

            if self.subscribed_symbols:
                self._set_status(SubscriptionStatus.SUBSCRIBED)
                self._start_data_thread()

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"订阅标的异常: {e}")
            return False

    def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅

        Args:
            symbols: 标的代码列表

        Returns:
            取消是否成功
        """
        try:
            with self._lock:
                for symbol in symbols:
                    if symbol in self.subscribed_symbols:
                        self.subscribed_symbols.remove(symbol)
                        if symbol in self._tick_buffer:
                            del self._tick_buffer[symbol]
                        if symbol in self._bar_buffer:
                            del self._bar_buffer[symbol]
                        logger.info(f"取消订阅: {symbol}")

            if not self.subscribed_symbols:
                self._set_status(SubscriptionStatus.CONNECTED)

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"取消订阅异常: {e}")
            return False

    def unsubscribe_all(self) -> bool:
        """取消所有订阅

        Returns:
            取消是否成功
        """
        return self.unsubscribe(list(self.subscribed_symbols))

    def _connect_qmt(self) -> bool:
        """连接QMT数据源"""
        try:
            # 尝试导入QMT模块
            # from xtquant import xtdata
            # xtdata.connect()
            logger.info("QMT数据源连接 (模拟)")
            return True
        except ImportError:
            logger.warning("QMT模块未安装，使用模拟模式")
            return True
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"QMT连接失败: {e}")
            return False

    def _connect_simulation(self) -> bool:
        """连接模拟数据源"""
        logger.info("模拟数据源连接成功")
        return True

    def _connect_replay(self) -> bool:
        """连接回放数据源"""
        logger.info("回放数据源连接成功")
        return True

    def _set_status(self, status: SubscriptionStatus) -> None:
        """设置状态"""
        old_status = self.status
        self.status = status

        if old_status != status and self.on_status_change:
            try:
                self.on_status_change(status)  # pylint: disable=e1102
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"状态变化回调失败: {e}")

    def _start_data_thread(self) -> None:
        """启动数据处理线程"""
        if self._is_running:
            return

        self._is_running = True
        self._stop_event.clear()

        self._data_thread = threading.Thread(target=self._data_loop, name="MarketDataThread", daemon=True)
        self._data_thread.start()

    def _stop_data_thread(self) -> None:
        """停止数据处理线程"""
        if not self._is_running:
            return

        self._stop_event.set()

        if self._data_thread and self._data_thread.is_alive():
            self._data_thread.join(timeout=5)

        self._is_running = False

    def _data_loop(self) -> None:
        """数据处理循环"""
        while not self._stop_event.is_set():
            try:
                if self.data_source == DataSource.SIMULATION:
                    self._generate_simulation_data()
                elif self.data_source == DataSource.QMT:
                    self._fetch_qmt_data()
                elif self.data_source == DataSource.REPLAY:
                    self._fetch_replay_data()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"数据处理异常: {e}")

            self._stop_event.wait(0.1)  # 100ms间隔

    def _generate_simulation_data(self) -> None:
        """生成模拟数据"""
        import random  # pylint: disable=import-outside-toplevel

        with self._lock:
            for symbol in self.subscribed_symbols:
                # 生成模拟Tick
                base_price = 10.0 + hash(symbol) % 100
                price = base_price * (1 + random.uniform(-0.001, 0.001))

                tick = TickData(
                    symbol=symbol,
                    price=round(price, 2),
                    volume=random.randint(100, 10000),
                    amount=round(price * random.randint(100, 10000), 2),
                    bid_price=round(price * 0.999, 2),
                    ask_price=round(price * 1.001, 2),
                    bid_volume=random.randint(100, 5000),
                    ask_volume=random.randint(100, 5000),
                )

                self._process_tick(tick)

    def _fetch_qmt_data(self) -> None:
        """获取QMT数据"""
        # 实际实现需要调用QMT API

    def _fetch_replay_data(self) -> None:
        """获取回放数据"""
        # 实际实现需要从历史数据读取

    def _process_tick(self, tick: TickData) -> None:
        """处理Tick数据"""
        # 存入缓冲区
        if tick.symbol in self._tick_buffer:
            self._tick_buffer[tick.symbol].append(tick)

        # 更新统计
        self._tick_count += 1
        self._last_tick_time = tick.timestamp

        # 触发回调
        if self.on_tick:
            try:
                self.on_tick(tick)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Tick回调失败: {e}")

    def _process_bar(self, bar: BarData) -> None:  # pylint: disable=c0104
        """处理K线数据"""
        # 存入缓冲区
        if bar.symbol in self._bar_buffer:
            self._bar_buffer[bar.symbol].append(bar)

        # 触发回调
        if self.on_bar:
            try:
                self.on_bar(bar)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Bar回调失败: {e}")

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新Tick

        Args:
            symbol: 标的代码

        Returns:
            最新Tick数据
        """
        with self._lock:
            if symbol in self._tick_buffer and self._tick_buffer[symbol]:
                return self._tick_buffer[symbol][-1]
        return None

    def get_tick_history(self, symbol: str, count: int = 100) -> List[TickData]:
        """获取Tick历史

        Args:
            symbol: 标的代码
            count: 返回数量

        Returns:
            Tick数据列表
        """
        with self._lock:
            if symbol in self._tick_buffer:
                return list(self._tick_buffer[symbol])[-count:]
        return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "status": self.status.value,
            "data_source": self.data_source.value,
            "subscribed_count": len(self.subscribed_symbols),
            "tick_count": self._tick_count,
            "last_tick_time": self._last_tick_time.isoformat() if self._last_tick_time else None,
        }

    def is_connected(self) -> bool:
        """检查是否已连接

        Returns:
            是否已连接
        """
        return self.status in [SubscriptionStatus.CONNECTED, SubscriptionStatus.SUBSCRIBED]

    def is_subscribed(self) -> bool:
        """检查是否已订阅

        Returns:
            是否已订阅
        """
        return self.status == SubscriptionStatus.SUBSCRIBED
