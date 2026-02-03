"""狩猎雷达仪表盘 (Radar Dashboard)

白皮书依据: 附录A 全息指挥台 - 4. 狩猎雷达 (Radar)
优先级: P1 - 高优先级

核心功能:
- 实时信号瀑布流 (WebSocket, 60Hz)
- 今日信号统计
"""

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import websockets

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class SignalType(Enum):
    """信号类型枚举

    白皮书依据: 附录A 狩猎雷达 - 信号类型
    """

    ACCUMULATION = "吸筹"
    WASHOUT = "洗盘"
    BREAKOUT = "突破"
    DIVERGENCE = "背离"
    UNKNOWN = "未知"


@dataclass
class RadarSignal:
    """雷达信号数据模型

    白皮书依据: 附录A 狩猎雷达 - 实时信号瀑布流

    Attributes:
        timestamp: 时间戳
        symbol: 标的代码
        name: 标的名称
        signal_type: 信号类型 (吸筹/洗盘/突破/背离)
        signal_strength: 信号强度 (0-100)
        main_force_prob: 主力概率 (0-100%)
        price: 当前价格
        change_pct: 涨跌幅
    """

    timestamp: datetime
    symbol: str
    name: str
    signal_type: SignalType
    signal_strength: int
    main_force_prob: float
    price: float = 0.0
    change_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "name": self.name,
            "signal_type": self.signal_type.value,
            "signal_strength": self.signal_strength,
            "main_force_prob": self.main_force_prob,
            "price": self.price,
            "change_pct": self.change_pct,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadarSignal":
        """从字典创建"""
        signal_type_str = data.get("signal_type", "UNKNOWN")
        try:
            signal_type = SignalType(signal_type_str)
        except ValueError:
            signal_type = SignalType.UNKNOWN

        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            timestamp=timestamp,
            symbol=data.get("symbol", ""),
            name=data.get("name", ""),
            signal_type=signal_type,
            signal_strength=int(data.get("signal_strength", 0)),
            main_force_prob=float(data.get("main_force_prob", 0)),
            price=float(data.get("price", 0)),
            change_pct=float(data.get("change_pct", 0)),
        )


@dataclass
class SignalStatistics:
    """今日信号统计数据模型

    白皮书依据: 附录A 狩猎雷达 - 今日信号统计

    Attributes:
        total_count: 信号总数
        accuracy_rate: 信号准确率
        avg_response_time_ms: 平均响应时间(毫秒)
        type_distribution: 信号类型分布
    """

    total_count: int = 0
    accuracy_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    type_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_count": self.total_count,
            "accuracy_rate": self.accuracy_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "type_distribution": self.type_distribution,
        }


class RadarDashboard:
    """狩猎雷达仪表盘

    白皮书依据: 附录A 全息指挥台 - 4. 狩猎雷达 (Radar)

    提供实时信号监控功能:
    - 实时信号瀑布流 (WebSocket, 60Hz)
    - 今日信号统计

    Attributes:
        redis_client: Redis客户端
        websocket_url: WebSocket服务器地址
        max_signals: 最大信号缓存数量
    """

    # 色彩方案 (红涨绿跌)
    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "accumulation": "#1890FF",
        "washout": "#722ED1",
        "breakout": "#FA8C16",
        "divergence": "#EB2F96",
    }

    # 信号类型颜色映射
    SIGNAL_COLORS = {
        SignalType.ACCUMULATION: "#1890FF",
        SignalType.WASHOUT: "#722ED1",
        SignalType.BREAKOUT: "#FA8C16",
        SignalType.DIVERGENCE: "#EB2F96",
        SignalType.UNKNOWN: "#8C8C8C",
    }

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        websocket_url: str = "ws://localhost:8502/radar",
        max_signals: int = 100,
    ):
        """初始化狩猎雷达仪表盘

        Args:
            redis_client: Redis客户端
            websocket_url: WebSocket服务器地址
            max_signals: 最大信号缓存数量，默认100
        """
        self.redis_client = redis_client
        self.websocket_url = websocket_url
        self.max_signals = max_signals
        self._signal_buffer: deque = deque(maxlen=max_signals)
        self._ws_connection = None
        self._is_connected = False
        logger.info(f"RadarDashboard initialized, websocket_url={websocket_url}")

    def get_recent_signals(self, limit: int = 100) -> List[RadarSignal]:
        """获取最近的信号列表

        白皮书依据: 附录A 狩猎雷达 - 最多显示最近100条

        Args:
            limit: 返回数量限制

        Returns:
            信号列表（按时间倒序）
        """
        if self.redis_client is None:
            return self._get_mock_signals(limit)

        try:
            # 从Redis获取最近的信号
            signal_data = self.redis_client.lrange("mia:radar:signals", 0, limit - 1)

            signals = []
            for data in signal_data:
                if isinstance(data, bytes):
                    data = data.decode()
                if isinstance(data, str):
                    data = json.loads(data)
                signals.append(RadarSignal.from_dict(data))

            return signals

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get recent signals: {e}")
            return self._get_mock_signals(limit)

    def get_signal_statistics(self) -> SignalStatistics:
        """获取今日信号统计

        白皮书依据: 附录A 狩猎雷达 - 今日信号统计

        Returns:
            信号统计数据
        """
        if self.redis_client is None:
            return self._get_mock_statistics()

        try:
            stats_data = self.redis_client.hgetall("mia:radar:statistics")

            type_dist_raw = self.redis_client.hgetall("mia:radar:type_distribution")
            type_distribution = {k.decode() if isinstance(k, bytes) else k: int(v) for k, v in type_dist_raw.items()}

            return SignalStatistics(
                total_count=int(stats_data.get(b"total_count", stats_data.get("total_count", 0))),
                accuracy_rate=float(stats_data.get(b"accuracy_rate", stats_data.get("accuracy_rate", 0))),
                avg_response_time_ms=float(
                    stats_data.get(b"avg_response_time_ms", stats_data.get("avg_response_time_ms", 0))
                ),
                type_distribution=type_distribution,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get signal statistics: {e}")
            return self._get_mock_statistics()

    async def connect_websocket(self, on_signal: Optional[Callable[[RadarSignal], None]] = None) -> None:
        """连接WebSocket接收实时信号

        白皮书依据: 附录A 狩猎雷达 - WebSocket 60Hz

        Args:
            on_signal: 收到信号时的回调函数
        """
        if not HAS_WEBSOCKETS:
            logger.warning("websockets library not available")
            return

        try:
            async with websockets.connect(self.websocket_url) as ws:
                self._ws_connection = ws
                self._is_connected = True
                logger.info(f"Connected to WebSocket: {self.websocket_url}")

                async for message in ws:
                    try:
                        data = json.loads(message)
                        signal = RadarSignal.from_dict(data)
                        self._signal_buffer.append(signal)

                        if on_signal:
                            on_signal(signal)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON message: {e}")
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.error(f"Error processing signal: {e}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"WebSocket connection error: {e}")
            self._is_connected = False
        finally:
            self._is_connected = False
            self._ws_connection = None

    async def disconnect_websocket(self) -> None:
        """断开WebSocket连接"""
        if self._ws_connection:
            await self._ws_connection.close()
            self._ws_connection = None
            self._is_connected = False
            logger.info("WebSocket disconnected")

    @property
    def is_connected(self) -> bool:
        """是否已连接WebSocket"""
        return self._is_connected

    def get_buffered_signals(self) -> List[RadarSignal]:
        """获取缓冲区中的信号"""
        return list(self._signal_buffer)

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 狩猎雷达
        技术实现: <iframe> + WebSocket
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("🎯 狩猎雷达 (Radar)")
        st.caption("实时信号监控 · WebSocket 60Hz · Admin Only")

        # 连接状态
        col1, col2 = st.columns([3, 1])
        with col1:
            if self._is_connected:
                st.success("🟢 WebSocket已连接")
            else:
                st.warning("🔴 WebSocket未连接")
        with col2:
            st.caption(f"缓冲区: {len(self._signal_buffer)}/{self.max_signals}")

        # Tab布局
        tab1, tab2 = st.tabs(["📡 实时信号", "📊 今日统计"])

        with tab1:
            self._render_signal_stream()

        with tab2:
            self._render_statistics()

    def _render_signal_stream(self) -> None:
        """渲染实时信号瀑布流"""
        st.subheader("📡 实时信号瀑布流")
        st.caption("最多显示最近100条")

        signals = self.get_recent_signals(100)

        if not signals:
            st.info("暂无信号")
            return

        # 信号列表
        for signal in signals[:20]:  # 显示最近20条
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 1])

                with col1:
                    st.caption(signal.timestamp.strftime("%H:%M:%S"))

                with col2:
                    st.markdown(f"**{signal.symbol}** {signal.name}")

                with col3:
                    color = self.SIGNAL_COLORS.get(signal.signal_type, "#8C8C8C")
                    st.markdown(
                        f"<span style='color:{color};font-weight:bold'>{signal.signal_type.value}</span>",
                        unsafe_allow_html=True,
                    )

                with col4:
                    # 信号强度进度条
                    strength_color = self._get_strength_color(signal.signal_strength)
                    st.markdown(
                        f"<span style='color:{strength_color}'>{signal.signal_strength}</span>", unsafe_allow_html=True
                    )

                with col5:
                    st.caption(f"主力: {signal.main_force_prob:.0f}%")

                st.divider()

    def _render_statistics(self) -> None:
        """渲染今日信号统计"""
        st.subheader("📊 今日信号统计")

        stats = self.get_signal_statistics()

        # 统计卡片
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("信号总数", f"{stats.total_count:,}")

        with col2:
            st.metric("信号准确率", f"{stats.accuracy_rate:.1f}%")

        with col3:
            st.metric("平均响应时间", f"{stats.avg_response_time_ms:.1f}ms")

        st.divider()

        # 信号类型分布
        st.markdown("#### 信号类型分布")

        if HAS_PLOTLY and stats.type_distribution:
            labels = list(stats.type_distribution.keys())
            values = list(stats.type_distribution.values())
            colors = [self.SIGNAL_COLORS.get(SignalType(l), "#8C8C8C") for l in labels]

            fig = go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=colors, hole=0.4)])

            fig.update_layout(
                title="信号类型分布",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2),  # pylint: disable=r1735
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            # 文本显示
            for signal_type, count in stats.type_distribution.items():
                st.write(f"- {signal_type}: {count}")

    def _get_strength_color(self, strength: int) -> str:
        """根据信号强度获取颜色"""
        if strength >= 80:  # pylint: disable=no-else-return
            return "#FF4D4F"  # 红色 - 极强
        elif strength >= 60:
            return "#FA8C16"  # 橙色 - 强
        elif strength >= 40:
            return "#FADB14"  # 黄色 - 中
        else:
            return "#8C8C8C"  # 灰色 - 弱

    def _get_mock_signals(self, limit: int) -> List[RadarSignal]:
        """获取模拟信号数据"""
        import random  # pylint: disable=import-outside-toplevel

        symbols = [
            ("000001", "平安银行"),
            ("600519", "贵州茅台"),
            ("000858", "五粮液"),
            ("002594", "比亚迪"),
            ("300750", "宁德时代"),
            ("601318", "中国平安"),
            ("000333", "美的集团"),
            ("600036", "招商银行"),
            ("002415", "海康威视"),
            ("601012", "隆基绿能"),
        ]

        signal_types = list(SignalType)[:4]  # 排除UNKNOWN

        signals = []
        now = datetime.now()

        for i in range(min(limit, 20)):
            symbol, name = random.choice(symbols)
            signals.append(
                RadarSignal(
                    timestamp=now.replace(second=now.second - i),
                    symbol=symbol,
                    name=name,
                    signal_type=random.choice(signal_types),
                    signal_strength=random.randint(30, 95),
                    main_force_prob=random.uniform(40, 95),
                    price=random.uniform(10, 200),
                    change_pct=random.uniform(-5, 8),
                )
            )

        return signals

    def _get_mock_statistics(self) -> SignalStatistics:
        """获取模拟统计数据"""
        return SignalStatistics(
            total_count=1256,
            accuracy_rate=72.5,
            avg_response_time_ms=15.3,
            type_distribution={"吸筹": 425, "洗盘": 312, "突破": 298, "背离": 221},
        )
