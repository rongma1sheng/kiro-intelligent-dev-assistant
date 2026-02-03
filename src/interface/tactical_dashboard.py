"""战术复盘仪表盘 (Tactical Dashboard)

白皮书依据: 附录A 全息指挥台 - 5. 战术复盘 (Tactical)
优先级: P1 - 高优先级

核心功能:
- K线图 + AI标记
- 交易日志
- 复盘统计
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class TradeDirection(Enum):
    """交易方向枚举"""

    BUY = "买入"
    SELL = "卖出"


class OrderStatus(Enum):
    """订单状态枚举"""

    FILLED = "成交"
    REJECTED = "废单"
    PARTIAL = "部分成交"
    CANCELLED = "已撤销"


@dataclass
class TradeRecord:
    """交易记录数据模型

    白皮书依据: 附录A 战术复盘 - 交易日志

    Attributes:
        trade_id: 交易ID
        timestamp: 成交时间
        symbol: 股票代码
        name: 股票名称
        direction: 交易方向
        price: 成交价格
        quantity: 成交数量
        amount: 成交金额
        status: 订单状态
        strategy_id: 策略ID
        audit_opinion: 审计意见
    """

    trade_id: str
    timestamp: datetime
    symbol: str
    name: str
    direction: TradeDirection
    price: float
    quantity: int
    amount: float
    status: OrderStatus = OrderStatus.FILLED
    strategy_id: str = ""
    audit_opinion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "name": self.name,
            "direction": self.direction.value,
            "price": self.price,
            "quantity": self.quantity,
            "amount": self.amount,
            "status": self.status.value,
            "strategy_id": self.strategy_id,
            "audit_opinion": self.audit_opinion,
        }


@dataclass
class AIMarker:
    """AI标记数据模型

    白皮书依据: 附录A 战术复盘 - K线图AI标记

    Attributes:
        timestamp: 标记时间
        marker_type: 标记类型 (buy/sell/stop_loss)
        price: 标记价格
        reason: Commander思维流
    """

    timestamp: datetime
    marker_type: str  # buy, sell, stop_loss
    price: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "marker_type": self.marker_type,
            "price": self.price,
            "reason": self.reason,
        }


@dataclass
class ReviewStatistics:
    """复盘统计数据模型

    白皮书依据: 附录A 战术复盘 - 复盘统计

    Attributes:
        win_rate: 交易胜率
        profit_loss_ratio: 盈亏比
        avg_holding_days: 平均持仓时长(天)
        max_consecutive_wins: 最大连续盈利次数
        max_consecutive_losses: 最大连续亏损次数
        total_trades: 总交易次数
        profitable_trades: 盈利交易次数
        losing_trades: 亏损交易次数
    """

    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    avg_holding_days: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "win_rate": self.win_rate,
            "profit_loss_ratio": self.profit_loss_ratio,
            "avg_holding_days": self.avg_holding_days,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "total_trades": self.total_trades,
            "profitable_trades": self.profitable_trades,
            "losing_trades": self.losing_trades,
        }


@dataclass
class KLineData:
    """K线数据模型"""

    dates: List[str] = field(default_factory=list)
    opens: List[float] = field(default_factory=list)
    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    closes: List[float] = field(default_factory=list)
    volumes: List[int] = field(default_factory=list)


class TacticalDashboard:
    """战术复盘仪表盘

    白皮书依据: 附录A 全息指挥台 - 5. 战术复盘 (Tactical)

    提供交易复盘分析功能:
    - K线图 + AI标记
    - 交易日志
    - 复盘统计

    Attributes:
        redis_client: Redis客户端
    """

    # 色彩方案 (红涨绿跌)
    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "buy_marker": "#52C41A",  # 绿色向上箭头
        "sell_marker": "#FF4D4F",  # 红色向下箭头
        "stop_loss_marker": "#FADB14",  # 黄色叉号
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化战术复盘仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("TacticalDashboard initialized")

    def get_kline_data(self, symbol: str, days: int = 60) -> KLineData:
        """获取K线数据

        Args:
            symbol: 股票代码
            days: 获取天数

        Returns:
            K线数据
        """
        if self.redis_client is None:
            return self._get_mock_kline_data(symbol, days)

        try:
            kline_key = f"mia:kline:{symbol}"
            kline_data = self.redis_client.lrange(kline_key, -days, -1)

            dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []

            for data in kline_data:
                if isinstance(data, bytes):
                    data = data.decode()
                import json  # pylint: disable=import-outside-toplevel

                bar = json.loads(data)  # pylint: disable=c0104
                dates.append(bar["date"])
                opens.append(float(bar["open"]))
                highs.append(float(bar["high"]))
                lows.append(float(bar["low"]))
                closes.append(float(bar["close"]))
                volumes.append(int(bar["volume"]))

            return KLineData(dates=dates, opens=opens, highs=highs, lows=lows, closes=closes, volumes=volumes)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get kline data for {symbol}: {e}")
            return self._get_mock_kline_data(symbol, days)

    def get_ai_markers(self, symbol: str, start_date: Optional[date] = None) -> List[AIMarker]:
        """获取AI标记

        白皮书依据: 附录A 战术复盘 - K线图AI标记

        Args:
            symbol: 股票代码
            start_date: 开始日期

        Returns:
            AI标记列表
        """
        if self.redis_client is None:
            return self._get_mock_ai_markers(symbol)

        try:
            marker_key = f"mia:markers:{symbol}"
            marker_data = self.redis_client.lrange(marker_key, 0, -1)

            markers = []
            for data in marker_data:
                if isinstance(data, bytes):
                    data = data.decode()
                import json  # pylint: disable=import-outside-toplevel

                m = json.loads(data)

                timestamp = datetime.fromisoformat(m["timestamp"])
                if start_date and timestamp.date() < start_date:
                    continue

                markers.append(
                    AIMarker(
                        timestamp=timestamp,
                        marker_type=m["marker_type"],
                        price=float(m["price"]),
                        reason=m.get("reason", ""),
                    )
                )

            return markers

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get AI markers for {symbol}: {e}")
            return self._get_mock_ai_markers(symbol)

    def get_trade_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None,
        include_rejected: bool = True,
    ) -> List[TradeRecord]:
        """获取交易记录

        白皮书依据: 附录A 战术复盘 - 交易日志

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol: 股票代码筛选
            include_rejected: 是否包含废单

        Returns:
            交易记录列表
        """
        if self.redis_client is None:
            return self._get_mock_trade_records(start_date, end_date, symbol, include_rejected)

        try:
            trade_keys = self.redis_client.keys("mia:trades:*")

            records = []
            for key in trade_keys:
                trade_data = self.redis_client.hgetall(key)
                if not trade_data:
                    continue

                timestamp = datetime.fromisoformat(trade_data.get("timestamp", ""))

                # 日期筛选
                if start_date and timestamp.date() < start_date:
                    continue
                if end_date and timestamp.date() > end_date:
                    continue

                # 股票筛选
                trade_symbol = trade_data.get("symbol", "")
                if symbol and trade_symbol != symbol:
                    continue

                # 废单筛选
                status = OrderStatus(trade_data.get("status", "FILLED"))
                if not include_rejected and status == OrderStatus.REJECTED:
                    continue

                records.append(
                    TradeRecord(
                        trade_id=trade_data.get("trade_id", ""),
                        timestamp=timestamp,
                        symbol=trade_symbol,
                        name=trade_data.get("name", ""),
                        direction=TradeDirection(trade_data.get("direction", "BUY")),
                        price=float(trade_data.get("price", 0)),
                        quantity=int(trade_data.get("quantity", 0)),
                        amount=float(trade_data.get("amount", 0)),
                        status=status,
                        strategy_id=trade_data.get("strategy_id", ""),
                        audit_opinion=trade_data.get("audit_opinion", ""),
                    )
                )

            # 按时间倒序排列
            records.sort(key=lambda x: x.timestamp, reverse=True)
            return records

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get trade records: {e}")
            return self._get_mock_trade_records(start_date, end_date, symbol, include_rejected)

    def get_review_statistics(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None  # pylint: disable=unused-argument
    ) -> ReviewStatistics:
        """获取复盘统计

        白皮书依据: 附录A 战术复盘 - 复盘统计

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            复盘统计数据
        """
        if self.redis_client is None:
            return self._get_mock_review_statistics()

        try:
            stats_data = self.redis_client.hgetall("mia:review:statistics")

            return ReviewStatistics(
                win_rate=float(stats_data.get("win_rate", 0)),
                profit_loss_ratio=float(stats_data.get("profit_loss_ratio", 0)),
                avg_holding_days=float(stats_data.get("avg_holding_days", 0)),
                max_consecutive_wins=int(stats_data.get("max_consecutive_wins", 0)),
                max_consecutive_losses=int(stats_data.get("max_consecutive_losses", 0)),
                total_trades=int(stats_data.get("total_trades", 0)),
                profitable_trades=int(stats_data.get("profitable_trades", 0)),
                losing_trades=int(stats_data.get("losing_trades", 0)),
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get review statistics: {e}")
            return self._get_mock_review_statistics()

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 战术复盘
        技术实现: Plotly K线图 + Streamlit表格
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("📈 战术复盘 (Tactical)")
        st.caption("K线分析 · 交易日志 · 复盘统计 · Admin Only")

        # 日期筛选
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_date = st.date_input("开始日期", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("结束日期", value=date.today())
        with col3:
            symbol = st.text_input("股票代码", value="000001")

        # Tab布局
        tab1, tab2, tab3 = st.tabs(["📊 K线图", "📋 交易日志", "📈 复盘统计"])

        with tab1:
            self._render_kline_chart(symbol)

        with tab2:
            self._render_trade_log(start_date, end_date)

        with tab3:
            self._render_review_stats(start_date, end_date)

    def _render_kline_chart(self, symbol: str) -> None:
        """渲染K线图"""
        st.subheader(f"📊 K线图 - {symbol}")

        kline = self.get_kline_data(symbol, 60)
        markers = self.get_ai_markers(symbol)

        if not kline.dates:
            st.info("暂无K线数据")
            return

        if HAS_PLOTLY:
            # 创建K线图
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

            # K线
            fig.add_trace(
                go.Candlestick(
                    x=kline.dates,
                    open=kline.opens,
                    high=kline.highs,
                    low=kline.lows,
                    close=kline.closes,
                    increasing_line_color=self.COLOR_SCHEME["rise"],
                    decreasing_line_color=self.COLOR_SCHEME["fall"],
                    name="K线",
                ),
                row=1,
                col=1,
            )

            # AI标记
            for marker in markers:
                marker_date = marker.timestamp.strftime("%Y-%m-%d")
                if marker_date not in kline.dates:
                    continue

                if marker.marker_type == "buy":
                    fig.add_trace(
                        go.Scatter(
                            x=[marker_date],
                            y=[marker.price],
                            mode="markers",
                            marker=dict(  # pylint: disable=r1735
                                symbol="triangle-up", size=15, color=self.COLOR_SCHEME["buy_marker"]
                            ),  # pylint: disable=r1735
                            name="买入",
                            hovertext=marker.reason,
                            hoverinfo="text",
                        ),
                        row=1,
                        col=1,
                    )
                elif marker.marker_type == "sell":
                    fig.add_trace(
                        go.Scatter(
                            x=[marker_date],
                            y=[marker.price],
                            mode="markers",
                            marker=dict(  # pylint: disable=r1735
                                symbol="triangle-down", size=15, color=self.COLOR_SCHEME["sell_marker"]
                            ),  # pylint: disable=r1735
                            name="卖出",
                            hovertext=marker.reason,
                            hoverinfo="text",
                        ),
                        row=1,
                        col=1,
                    )
                elif marker.marker_type == "stop_loss":
                    fig.add_trace(
                        go.Scatter(
                            x=[marker_date],
                            y=[marker.price],
                            mode="markers",
                            marker=dict(  # pylint: disable=r1735
                                symbol="x", size=15, color=self.COLOR_SCHEME["stop_loss_marker"]
                            ),  # pylint: disable=r1735
                            name="止损",
                            hovertext=marker.reason,
                            hoverinfo="text",
                        ),
                        row=1,
                        col=1,
                    )

            # 成交量
            colors = [
                self.COLOR_SCHEME["rise"] if kline.closes[i] >= kline.opens[i] else self.COLOR_SCHEME["fall"]
                for i in range(len(kline.closes))
            ]

            fig.add_trace(go.Bar(x=kline.dates, y=kline.volumes, marker_color=colors, name="成交量"), row=2, col=1)

            fig.update_layout(
                title=f"{symbol} K线图 + AI标记", xaxis_rangeslider_visible=False, showlegend=True, height=600
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Plotly未安装，无法显示K线图")

    def _render_trade_log(self, start_date: date, end_date: date) -> None:
        """渲染交易日志"""
        st.subheader("📋 交易日志")

        # 筛选选项
        col1, col2 = st.columns(2)
        with col1:
            include_rejected = st.checkbox("包含废单", value=True)
        with col2:
            filter_symbol = st.text_input("筛选股票", value="")

        records = self.get_trade_records(
            start_date=start_date,
            end_date=end_date,
            symbol=filter_symbol if filter_symbol else None,
            include_rejected=include_rejected,
        )

        if not records:
            st.info("暂无交易记录")
            return

        # 成交记录
        st.markdown("#### 成交记录")

        for record in records:
            if record.status == OrderStatus.REJECTED:
                continue

            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1, 1, 1, 1])

                with col1:
                    st.caption(record.timestamp.strftime("%m-%d %H:%M"))

                with col2:
                    st.markdown(f"**{record.symbol}** {record.name}")

                with col3:
                    color = (
                        self.COLOR_SCHEME["rise"]
                        if record.direction == TradeDirection.BUY
                        else self.COLOR_SCHEME["fall"]
                    )
                    st.markdown(f"<span style='color:{color}'>{record.direction.value}</span>", unsafe_allow_html=True)

                with col4:
                    st.write(f"¥{record.price:.2f}")

                with col5:
                    st.write(f"{record.quantity:,}")

                with col6:
                    st.caption(record.strategy_id)

                st.divider()

        # 废单记录
        rejected_records = [r for r in records if r.status == OrderStatus.REJECTED]
        if rejected_records and include_rejected:
            st.markdown("#### 废单记录")

            for record in rejected_records:
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 2, 2, 2])

                    with col1:
                        st.caption(record.timestamp.strftime("%m-%d %H:%M"))

                    with col2:
                        st.markdown(f"**{record.symbol}** {record.name}")

                    with col3:
                        st.write(f"{record.direction.value} {record.quantity:,}股")

                    with col4:
                        st.error(record.audit_opinion or "被拒绝")

                    st.divider()

    def _render_review_stats(self, start_date: date, end_date: date) -> None:
        """渲染复盘统计"""
        st.subheader("📈 复盘统计")

        stats = self.get_review_statistics(start_date, end_date)

        # 核心指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("交易胜率", f"{stats.win_rate:.1f}%")

        with col2:
            st.metric("盈亏比", f"{stats.profit_loss_ratio:.2f}")

        with col3:
            st.metric("平均持仓", f"{stats.avg_holding_days:.1f}天")

        with col4:
            st.metric("总交易次数", f"{stats.total_trades}")

        st.divider()

        # 连续盈亏
        col1, col2 = st.columns(2)

        with col1:
            st.metric("最大连续盈利", f"{stats.max_consecutive_wins}次", delta_color="normal")

        with col2:
            st.metric("最大连续亏损", f"{stats.max_consecutive_losses}次", delta_color="inverse")

        # 盈亏分布
        st.markdown("#### 盈亏分布")

        if HAS_PLOTLY:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["盈利", "亏损"],
                        values=[stats.profitable_trades, stats.losing_trades],
                        marker_colors=[self.COLOR_SCHEME["rise"], self.COLOR_SCHEME["fall"]],
                        hole=0.4,
                    )
                ]
            )

            fig.update_layout(title="交易盈亏分布")
            st.plotly_chart(fig, use_container_width=True)

    def _get_mock_kline_data(self, symbol: str, days: int) -> KLineData:
        """获取模拟K线数据"""
        import random  # pylint: disable=import-outside-toplevel

        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        base_price = 12.0 if symbol == "000001" else random.uniform(10, 200)
        current_date = date.today() - timedelta(days=days)

        for i in range(days):  # pylint: disable=unused-variable
            current_date += timedelta(days=1)
            if current_date.weekday() >= 5:  # 跳过周末
                continue

            dates.append(current_date.strftime("%Y-%m-%d"))

            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            close_price = open_price * (1 + random.uniform(-0.05, 0.05))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))

            opens.append(round(open_price, 2))
            highs.append(round(high_price, 2))
            lows.append(round(low_price, 2))
            closes.append(round(close_price, 2))
            volumes.append(random.randint(5000000, 20000000))

            base_price = close_price

        return KLineData(dates=dates, opens=opens, highs=highs, lows=lows, closes=closes, volumes=volumes)

    def _get_mock_ai_markers(self, symbol: str) -> List[AIMarker]:  # pylint: disable=unused-argument
        """获取模拟AI标记"""
        markers = []
        base_date = date.today() - timedelta(days=30)

        # 买入标记
        markers.append(
            AIMarker(
                timestamp=datetime.combine(base_date + timedelta(days=5), datetime.min.time()),
                marker_type="buy",
                price=11.80,
                reason="Commander: 主力资金持续流入，MACD金叉，建议建仓",
            )
        )

        # 卖出标记
        markers.append(
            AIMarker(
                timestamp=datetime.combine(base_date + timedelta(days=15), datetime.min.time()),
                marker_type="sell",
                price=12.50,
                reason="Commander: 达到目标价位，获利了结",
            )
        )

        # 止损标记
        markers.append(
            AIMarker(
                timestamp=datetime.combine(base_date + timedelta(days=25), datetime.min.time()),
                marker_type="stop_loss",
                price=11.20,
                reason="Commander: 跌破支撑位，触发止损",
            )
        )

        return markers

    def _get_mock_trade_records(
        self,
        start_date: Optional[date],  # pylint: disable=unused-argument
        end_date: Optional[date],  # pylint: disable=unused-argument
        symbol: Optional[str],
        include_rejected: bool,  # pylint: disable=unused-argument
    ) -> List[TradeRecord]:
        """获取模拟交易记录"""
        records = [
            TradeRecord(
                trade_id="T20260127001",
                timestamp=datetime.now() - timedelta(hours=2),
                symbol="000001",
                name="平安银行",
                direction=TradeDirection.BUY,
                price=12.35,
                quantity=5000,
                amount=61750,
                status=OrderStatus.FILLED,
                strategy_id="S01",
            ),
            TradeRecord(
                trade_id="T20260127002",
                timestamp=datetime.now() - timedelta(hours=1),
                symbol="600519",
                name="贵州茅台",
                direction=TradeDirection.SELL,
                price=1850.00,
                quantity=10,
                amount=18500,
                status=OrderStatus.FILLED,
                strategy_id="S03",
            ),
            TradeRecord(
                trade_id="T20260127003",
                timestamp=datetime.now() - timedelta(minutes=30),
                symbol="000858",
                name="五粮液",
                direction=TradeDirection.BUY,
                price=168.50,
                quantity=200,
                amount=33700,
                status=OrderStatus.REJECTED,
                strategy_id="S01",
                audit_opinion="Devil: 风险敞口超限，拒绝执行",
            ),
        ]

        if not include_rejected:
            records = [r for r in records if r.status != OrderStatus.REJECTED]

        if symbol:
            records = [r for r in records if r.symbol == symbol]

        return records

    def _get_mock_review_statistics(self) -> ReviewStatistics:
        """获取模拟复盘统计"""
        return ReviewStatistics(
            win_rate=62.5,
            profit_loss_ratio=1.85,
            avg_holding_days=3.2,
            max_consecutive_wins=8,
            max_consecutive_losses=3,
            total_trades=156,
            profitable_trades=98,
            losing_trades=58,
        )
