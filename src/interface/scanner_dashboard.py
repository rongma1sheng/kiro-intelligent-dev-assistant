"""全息扫描仪仪表盘 (Scanner Dashboard)

白皮书依据: 附录A 全息指挥台 - 2. 全息扫描仪 (Scanner)
优先级: P0 - 最高优先级

核心功能:
- 上帝筛选器 (多维度股票筛选)
- 全息透视卡 (单个标的详情)
- Top 5信号榜单 (Guest可见)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class RadarStatus(Enum):
    """雷达状态枚举

    白皮书依据: 附录A 全息扫描仪 - AMD雷达状态
    """

    ACCUMULATION = "吸筹"
    WASHOUT = "洗盘"
    NEUTRAL = "中性"
    BREAKOUT = "突破"
    DIVERGENCE = "背离"


class SignalStrength(Enum):
    """信号强度枚举"""

    WEAK = "弱"
    MEDIUM = "中"
    STRONG = "强"
    VERY_STRONG = "极强"


@dataclass
class StockSignal:
    """股票信号数据模型

    白皮书依据: 附录A 全息扫描仪 - Top 5信号榜单

    Attributes:
        symbol: 股票代码
        name: 股票名称
        price: 当前价格
        change_pct: 涨跌幅
        signal_strength: 信号强度 (0-100)
        radar_score: 雷达评分 (0-100)
        sentiment_score: 舆情评分 (0-100)
        radar_status: 雷达状态
        update_time: 更新时间
    """

    symbol: str
    name: str
    price: float
    change_pct: float
    signal_strength: float
    radar_score: float
    sentiment_score: float
    radar_status: RadarStatus = RadarStatus.NEUTRAL
    update_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change_pct": self.change_pct,
            "signal_strength": self.signal_strength,
            "radar_score": self.radar_score,
            "sentiment_score": self.sentiment_score,
            "radar_status": self.radar_status.value,
            "update_time": self.update_time.isoformat(),
        }


@dataclass
class FilterCriteria:
    """筛选条件数据模型

    白皮书依据: 附录A 全息扫描仪 - 上帝筛选器

    Attributes:
        radar_status: 雷达状态筛选
        sentiment_min: 舆情评分最小值
        sentiment_max: 舆情评分最大值
        price_min: 价格最小值
        price_max: 价格最大值
        volume_min: 成交量最小值
        rsi_min: RSI最小值
        rsi_max: RSI最大值
    """

    radar_status: Optional[List[RadarStatus]] = None
    sentiment_min: float = 0
    sentiment_max: float = 100
    price_min: float = 0
    price_max: float = float("inf")
    volume_min: float = 0
    rsi_min: float = 0
    rsi_max: float = 100


@dataclass
class StockDetail:
    """股票详情数据模型

    白皮书依据: 附录A 全息扫描仪 - 全息透视卡

    Attributes:
        symbol: 股票代码
        name: 股票名称
        price: 当前价格
        change_pct: 涨跌幅
        open_price: 开盘价
        high_price: 最高价
        low_price: 最低价
        volume: 成交量
        amount: 成交额
        radar_status: 雷达状态
        radar_score: 雷达评分
        sentiment_score: 舆情评分
        ai_summary: Commander AI分析摘要
        technical_indicators: 技术指标
    """

    symbol: str
    name: str
    price: float
    change_pct: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    amount: float
    radar_status: RadarStatus
    radar_score: float
    sentiment_score: float
    ai_summary: str = ""
    technical_indicators: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change_pct": self.change_pct,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "volume": self.volume,
            "amount": self.amount,
            "radar_status": self.radar_status.value,
            "radar_score": self.radar_score,
            "sentiment_score": self.sentiment_score,
            "ai_summary": self.ai_summary,
            "technical_indicators": self.technical_indicators,
        }


class ScannerDashboard:
    """全息扫描仪仪表盘

    白皮书依据: 附录A 全息指挥台 - 2. 全息扫描仪 (Scanner)

    提供股票筛选和信号展示功能:
    - 上帝筛选器 (多维度筛选)
    - 全息透视卡 (详情展示)
    - Top 5信号榜单

    Attributes:
        redis_client: Redis客户端
        websocket_url: WebSocket URL (雷达波形)
        is_admin: 是否为Admin用户
    """

    # 色彩方案 (红涨绿跌)
    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "primary": "#1890FF",
        "warning": "#FA8C16",
    }

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        websocket_url: str = "ws://localhost:8502/radar",
        is_admin: bool = True,
    ):
        """初始化全息扫描仪

        Args:
            redis_client: Redis客户端
            websocket_url: WebSocket URL
            is_admin: 是否为Admin用户
        """
        self.redis_client = redis_client
        self.websocket_url = websocket_url
        self.is_admin = is_admin

        logger.info(f"ScannerDashboard initialized, is_admin={is_admin}")

    def get_top_signals(self, limit: int = 5) -> List[StockSignal]:
        """获取Top信号榜单

        白皮书依据: 附录A 全息扫描仪 - Top 5信号榜单
        数据源: Redis (mia:signals:*)
        刷新频率: 5秒

        Args:
            limit: 返回数量限制

        Returns:
            信号列表
        """
        if self.redis_client is None:
            return self._get_mock_signals(limit)

        try:
            # 从Redis获取Top信号
            signals_data = self.redis_client.zrevrange("mia:signals:top", 0, limit - 1, withscores=True)

            signals = []
            for symbol, score in signals_data:
                signal_detail = self.redis_client.hgetall(f"mia:signals:{symbol}")
                if signal_detail:
                    signals.append(
                        StockSignal(
                            symbol=symbol,
                            name=signal_detail.get("name", ""),
                            price=float(signal_detail.get("price", 0)),
                            change_pct=float(signal_detail.get("change_pct", 0)),
                            signal_strength=score,
                            radar_score=float(signal_detail.get("radar_score", 0)),
                            sentiment_score=float(signal_detail.get("sentiment_score", 0)),
                            radar_status=RadarStatus[signal_detail.get("radar_status", "NEUTRAL")],
                            update_time=datetime.now(),
                        )
                    )

            return signals

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get top signals: {e}")
            return self._get_mock_signals(limit)

    def filter_stocks(self, criteria: FilterCriteria) -> List[StockSignal]:
        """根据条件筛选股票

        白皮书依据: 附录A 全息扫描仪 - 上帝筛选器

        Args:
            criteria: 筛选条件

        Returns:
            符合条件的股票列表
        """
        if self.redis_client is None:
            return self._get_mock_signals(20)

        try:
            # 获取所有股票
            all_symbols = self.redis_client.smembers("mia:scanner:symbols")

            filtered = []
            for symbol in all_symbols:
                stock_data = self.redis_client.hgetall(f"mia:scanner:{symbol}")
                if not stock_data:
                    continue

                # 应用筛选条件
                sentiment = float(stock_data.get("sentiment_score", 0))
                price = float(stock_data.get("price", 0))
                radar_status_str = stock_data.get("radar_status", "NEUTRAL")

                # 舆情评分筛选
                if not (
                    criteria.sentiment_min <= sentiment <= criteria.sentiment_max
                ):  # pylint: disable=superfluous-parens
                    continue

                # 价格筛选
                if not (criteria.price_min <= price <= criteria.price_max):  # pylint: disable=superfluous-parens
                    continue

                # 雷达状态筛选
                if criteria.radar_status:
                    try:
                        radar_status = RadarStatus[radar_status_str]
                        if radar_status not in criteria.radar_status:
                            continue
                    except KeyError:
                        continue

                filtered.append(
                    StockSignal(
                        symbol=symbol,
                        name=stock_data.get("name", ""),
                        price=price,
                        change_pct=float(stock_data.get("change_pct", 0)),
                        signal_strength=float(stock_data.get("signal_strength", 0)),
                        radar_score=float(stock_data.get("radar_score", 0)),
                        sentiment_score=sentiment,
                        radar_status=RadarStatus[radar_status_str],
                        update_time=datetime.now(),
                    )
                )

            # 按信号强度排序
            filtered.sort(key=lambda x: x.signal_strength, reverse=True)
            return filtered

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to filter stocks: {e}")
            return self._get_mock_signals(20)

    def get_stock_detail(self, symbol: str) -> Optional[StockDetail]:
        """获取股票详情

        白皮书依据: 附录A 全息扫描仪 - 全息透视卡

        Args:
            symbol: 股票代码

        Returns:
            股票详情
        """
        if self.redis_client is None:
            return self._get_mock_stock_detail(symbol)

        try:
            stock_data = self.redis_client.hgetall(f"mia:scanner:{symbol}")
            if not stock_data:
                return None

            # 获取AI分析摘要
            ai_summary = self.redis_client.get(f"mia:ai:summary:{symbol}") or ""

            # 获取技术指标
            tech_data = self.redis_client.hgetall(f"mia:tech:{symbol}")
            technical_indicators = {
                "RSI": float(tech_data.get("rsi", 50)),
                "MACD": float(tech_data.get("macd", 0)),
                "MACD_Signal": float(tech_data.get("macd_signal", 0)),
                "BB_Upper": float(tech_data.get("bb_upper", 0)),
                "BB_Lower": float(tech_data.get("bb_lower", 0)),
            }

            return StockDetail(
                symbol=symbol,
                name=stock_data.get("name", ""),
                price=float(stock_data.get("price", 0)),
                change_pct=float(stock_data.get("change_pct", 0)),
                open_price=float(stock_data.get("open", 0)),
                high_price=float(stock_data.get("high", 0)),
                low_price=float(stock_data.get("low", 0)),
                volume=float(stock_data.get("volume", 0)),
                amount=float(stock_data.get("amount", 0)),
                radar_status=RadarStatus[stock_data.get("radar_status", "NEUTRAL")],
                radar_score=float(stock_data.get("radar_score", 0)),
                sentiment_score=float(stock_data.get("sentiment_score", 0)),
                ai_summary=ai_summary,
                technical_indicators=technical_indicators,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get stock detail for {symbol}: {e}")
            return self._get_mock_stock_detail(symbol)

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 全息扫描仪
        技术实现: Streamlit + WebSocket Iframe
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("🔍 全息扫描仪 (Scanner)")

        if self.is_admin:
            st.caption("多维度选股 · AI信号 · Admin Full Access")
        else:
            st.caption("Top 5信号榜单 · Guest View")

        # Tab布局
        if self.is_admin:
            tab1, tab2, tab3 = st.tabs(["📊 Top信号", "🔎 上帝筛选器", "📋 全息透视卡"])
        else:
            tab1 = st.container()

        # Top信号榜单 (Guest可见)
        with tab1 if self.is_admin else st.container():
            self._render_top_signals()

        # Admin专属功能
        if self.is_admin:
            with tab2:
                self._render_filter()

            with tab3:
                self._render_stock_detail()

    def _render_top_signals(self) -> None:
        """渲染Top信号榜单"""
        st.subheader("🏆 Top 5 信号榜单")
        st.caption("实时更新 · 5秒刷新")

        signals = self.get_top_signals(5)

        for i, signal in enumerate(signals, 1):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])

                with col1:
                    st.markdown(f"**#{i}**")

                with col2:
                    st.markdown(f"**{signal.symbol}**")
                    st.caption(signal.name)

                with col3:
                    color = self.COLOR_SCHEME["rise"] if signal.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<span style='color:{color}'>¥{signal.price:.2f}</span>", unsafe_allow_html=True)
                    st.markdown(f"<span style='color:{color}'>{signal.change_pct:+.2f}%</span>", unsafe_allow_html=True)

                with col4:
                    st.metric("信号强度", f"{signal.signal_strength:.0f}")

                with col5:
                    st.metric("雷达评分", f"{signal.radar_score:.0f}")
                    st.caption(f"舆情: {signal.sentiment_score:.0f}")

                st.divider()

    def _render_filter(self) -> None:
        """渲染上帝筛选器"""
        st.subheader("🔎 上帝筛选器")

        with st.form("filter_form"):
            col1, col2 = st.columns(2)

            with col1:
                radar_options = st.multiselect(
                    "雷达状态", options=[s.value for s in RadarStatus], default=["吸筹", "突破"]
                )

                sentiment_range = st.slider("舆情评分范围", min_value=0, max_value=100, value=(50, 100))

            with col2:
                price_min = st.number_input("最低价格", min_value=0.0, value=5.0)
                price_max = st.number_input("最高价格", min_value=0.0, value=100.0)

                rsi_range = st.slider("RSI范围", min_value=0, max_value=100, value=(30, 70))

            submitted = st.form_submit_button("🔍 筛选", use_container_width=True)

        if submitted:
            # 构建筛选条件
            radar_status_list = [RadarStatus(s) for s in radar_options] if radar_options else None

            criteria = FilterCriteria(
                radar_status=radar_status_list,
                sentiment_min=sentiment_range[0],
                sentiment_max=sentiment_range[1],
                price_min=price_min,
                price_max=price_max,
                rsi_min=rsi_range[0],
                rsi_max=rsi_range[1],
            )

            results = self.filter_stocks(criteria)

            st.success(f"找到 {len(results)} 只符合条件的股票")

            # 显示结果
            if results:
                for signal in results[:20]:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

                    with col1:
                        st.markdown(f"**{signal.symbol}** {signal.name}")

                    with col2:
                        color = self.COLOR_SCHEME["rise"] if signal.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                        st.markdown(
                            f"<span style='color:{color}'>¥{signal.price:.2f} ({signal.change_pct:+.2f}%)</span>",
                            unsafe_allow_html=True,
                        )

                    with col3:
                        st.caption(f"雷达: {signal.radar_status.value}")

                    with col4:
                        st.caption(f"信号: {signal.signal_strength:.0f} | 舆情: {signal.sentiment_score:.0f}")

    def _render_stock_detail(self) -> None:
        """渲染全息透视卡"""
        st.subheader("📋 全息透视卡")

        symbol = st.text_input("输入股票代码", placeholder="例如: 000001")

        if symbol:
            detail = self.get_stock_detail(symbol)

            if detail:
                # 基础信息
                st.markdown(f"### {detail.name} ({detail.symbol})")

                col1, col2, col3 = st.columns(3)

                with col1:
                    color = self.COLOR_SCHEME["rise"] if detail.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<h2 style='color:{color}'>¥{detail.price:.2f}</h2>", unsafe_allow_html=True)
                    st.markdown(f"<span style='color:{color}'>{detail.change_pct:+.2f}%</span>", unsafe_allow_html=True)

                with col2:
                    st.metric("雷达状态", detail.radar_status.value)
                    st.metric("雷达评分", f"{detail.radar_score:.0f}")

                with col3:
                    st.metric("舆情评分", f"{detail.sentiment_score:.0f}")

                st.divider()

                # 价格详情
                st.subheader("📈 价格详情")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("开盘", f"¥{detail.open_price:.2f}")
                with col2:
                    st.metric("最高", f"¥{detail.high_price:.2f}")
                with col3:
                    st.metric("最低", f"¥{detail.low_price:.2f}")
                with col4:
                    st.metric("成交量", f"{detail.volume/10000:.0f}万")

                st.divider()

                # 技术指标
                st.subheader("📊 技术指标")
                col1, col2, col3 = st.columns(3)

                with col1:
                    rsi = detail.technical_indicators.get("RSI", 50)
                    st.metric("RSI", f"{rsi:.1f}")

                with col2:
                    macd = detail.technical_indicators.get("MACD", 0)
                    st.metric("MACD", f"{macd:.3f}")

                with col3:
                    bb_upper = detail.technical_indicators.get("BB_Upper", 0)
                    bb_lower = detail.technical_indicators.get("BB_Lower", 0)
                    st.metric("布林带", f"{bb_lower:.2f} - {bb_upper:.2f}")

                st.divider()

                # AI分析摘要
                if detail.ai_summary:
                    st.subheader("🤖 Commander AI分析")
                    st.info(detail.ai_summary)

                # 交易按钮 (Admin Only)
                if self.is_admin:
                    st.divider()
                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("🟢 买入", type="primary", use_container_width=True):
                            st.success(f"买入指令已发送: {symbol}")

                    with col2:
                        if st.button("🔴 卖出", type="secondary", use_container_width=True):
                            st.warning(f"卖出指令已发送: {symbol}")
            else:
                st.warning(f"未找到股票: {symbol}")

    def _get_mock_signals(self, limit: int) -> List[StockSignal]:
        """获取模拟信号数据"""
        mock_data = [
            ("000001", "平安银行", 12.50, 2.35, 95, 88, 82, RadarStatus.ACCUMULATION),
            ("600519", "贵州茅台", 1850.00, 1.25, 92, 85, 90, RadarStatus.BREAKOUT),
            ("000858", "五粮液", 168.50, 3.15, 88, 82, 78, RadarStatus.ACCUMULATION),
            ("002594", "比亚迪", 265.00, -0.85, 85, 78, 85, RadarStatus.NEUTRAL),
            ("300750", "宁德时代", 198.00, 1.55, 82, 75, 80, RadarStatus.BREAKOUT),
            ("601318", "中国平安", 48.50, 0.65, 78, 72, 75, RadarStatus.NEUTRAL),
            ("000333", "美的集团", 58.20, 1.85, 75, 70, 72, RadarStatus.ACCUMULATION),
        ]

        signals = []
        for symbol, name, price, change, strength, radar, sentiment, status in mock_data[:limit]:
            signals.append(
                StockSignal(
                    symbol=symbol,
                    name=name,
                    price=price,
                    change_pct=change,
                    signal_strength=strength,
                    radar_score=radar,
                    sentiment_score=sentiment,
                    radar_status=status,
                    update_time=datetime.now(),
                )
            )

        return signals

    def _get_mock_stock_detail(self, symbol: str) -> StockDetail:
        """获取模拟股票详情"""
        return StockDetail(
            symbol=symbol,
            name="示例股票",
            price=25.50,
            change_pct=2.35,
            open_price=25.00,
            high_price=26.00,
            low_price=24.80,
            volume=15000000,
            amount=380000000,
            radar_status=RadarStatus.ACCUMULATION,
            radar_score=85,
            sentiment_score=78,
            ai_summary="该股票近期主力资金持续流入，技术面呈现突破形态，建议关注。短期支撑位24.5，压力位27.0。",
            technical_indicators={
                "RSI": 58.5,
                "MACD": 0.125,
                "MACD_Signal": 0.098,
                "BB_Upper": 27.50,
                "BB_Lower": 23.50,
            },
        )
