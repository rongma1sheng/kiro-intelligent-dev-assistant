"""重点关注仪表盘 (Watchlist Dashboard)

白皮书依据: 附录A 全息指挥台 - 6. 重点关注 (Watchlist)
优先级: P1 - 高优先级

核心功能:
- AI核心池
- 自选股
- 板块热力图
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import plotly.express as px

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


class RankingType(Enum):
    """排名类型枚举"""

    SOLDIER = "Soldier评分"
    COMMANDER = "Commander评分"
    COMBINED = "综合评分"


@dataclass
class CorePoolStock:
    """AI核心池股票数据模型

    白皮书依据: 附录A 重点关注 - AI核心池

    Attributes:
        rank: 排名
        symbol: 股票代码
        name: 股票名称
        score: 评分
        price: 当前价格
        change_pct: 涨跌幅
        ranking_type: 排名类型
    """

    rank: int
    symbol: str
    name: str
    score: float
    price: float
    change_pct: float
    ranking_type: RankingType = RankingType.COMBINED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "name": self.name,
            "score": self.score,
            "price": self.price,
            "change_pct": self.change_pct,
            "ranking_type": self.ranking_type.value,
        }


@dataclass
class WatchlistStock:
    """自选股数据模型

    白皮书依据: 附录A 重点关注 - 自选股

    Attributes:
        symbol: 股票代码
        name: 股票名称
        price: 当前价格
        change_pct: 涨跌幅
        group: 分组名称
        sort_order: 排序顺序
        added_time: 添加时间
    """

    symbol: str
    name: str
    price: float
    change_pct: float
    group: str = "默认"
    sort_order: int = 0
    added_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "price": self.price,
            "change_pct": self.change_pct,
            "group": self.group,
            "sort_order": self.sort_order,
            "added_time": self.added_time.isoformat() if self.added_time else None,
        }


@dataclass
class SectorHeat:
    """板块热度数据模型

    白皮书依据: 附录A 重点关注 - 板块热力图

    Attributes:
        sector_name: 板块名称
        sector_type: 板块类型 (行业/概念)
        heat_score: 热度评分
        change_pct: 涨跌幅
        money_flow: 资金流向 (正为流入)
        sentiment_score: 舆情热度
    """

    sector_name: str
    sector_type: str
    heat_score: float
    change_pct: float
    money_flow: float = 0.0
    sentiment_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sector_name": self.sector_name,
            "sector_type": self.sector_type,
            "heat_score": self.heat_score,
            "change_pct": self.change_pct,
            "money_flow": self.money_flow,
            "sentiment_score": self.sentiment_score,
        }


class WatchlistDashboard:
    """重点关注仪表盘

    白皮书依据: 附录A 全息指挥台 - 6. 重点关注 (Watchlist)

    提供股票关注和板块分析功能:
    - AI核心池 (Soldier/Commander/综合评分 Top 20)
    - 自选股 (手动添加/删除, 分组管理)
    - 板块热力图 (行业/概念/舆情/资金流向)

    Attributes:
        redis_client: Redis客户端
    """

    # 色彩方案 (红涨绿跌)
    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "hot": "#FF4D4F",
        "cold": "#1890FF",
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化重点关注仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("WatchlistDashboard initialized")

    def get_core_pool(self, ranking_type: RankingType, limit: int = 20) -> List[CorePoolStock]:
        """获取AI核心池

        白皮书依据: 附录A 重点关注 - AI核心池
        数据源: Redis (mia:core_pool:*)
        刷新频率: 5分钟

        Args:
            ranking_type: 排名类型
            limit: 返回数量限制

        Returns:
            核心池股票列表
        """
        if self.redis_client is None:
            return self._get_mock_core_pool(ranking_type, limit)

        try:
            key_map = {
                RankingType.SOLDIER: "mia:core_pool:soldier",
                RankingType.COMMANDER: "mia:core_pool:commander",
                RankingType.COMBINED: "mia:core_pool:combined",
            }

            pool_key = key_map[ranking_type]
            pool_data = self.redis_client.zrevrange(pool_key, 0, limit - 1, withscores=True)

            stocks = []
            for rank, (symbol, score) in enumerate(pool_data, 1):
                if isinstance(symbol, bytes):
                    symbol = symbol.decode()

                stock_data = self.redis_client.hgetall(f"mia:stock:{symbol}")

                stocks.append(
                    CorePoolStock(
                        rank=rank,
                        symbol=symbol,
                        name=stock_data.get("name", ""),
                        score=float(score),
                        price=float(stock_data.get("price", 0)),
                        change_pct=float(stock_data.get("change_pct", 0)),
                        ranking_type=ranking_type,
                    )
                )

            return stocks

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get core pool: {e}")
            return self._get_mock_core_pool(ranking_type, limit)

    def get_watchlist(self, group: Optional[str] = None) -> List[WatchlistStock]:
        """获取自选股列表

        白皮书依据: 附录A 重点关注 - 自选股
        数据源: Redis (mia:watchlist:*)
        刷新频率: 5秒

        Args:
            group: 分组筛选

        Returns:
            自选股列表
        """
        if self.redis_client is None:
            return self._get_mock_watchlist(group)

        try:
            watchlist_data = self.redis_client.hgetall("mia:watchlist:stocks")

            stocks = []
            for symbol, data in watchlist_data.items():
                if isinstance(symbol, bytes):
                    symbol = symbol.decode()
                if isinstance(data, bytes):
                    data = data.decode()

                import json  # pylint: disable=import-outside-toplevel

                stock_info = json.loads(data)

                stock_group = stock_info.get("group", "默认")
                if group and stock_group != group:
                    continue

                # 获取实时价格
                price_data = self.redis_client.hgetall(f"mia:stock:{symbol}")

                stocks.append(
                    WatchlistStock(
                        symbol=symbol,
                        name=stock_info.get("name", ""),
                        price=float(price_data.get("price", 0)),
                        change_pct=float(price_data.get("change_pct", 0)),
                        group=stock_group,
                        sort_order=int(stock_info.get("sort_order", 0)),
                        added_time=(
                            datetime.fromisoformat(stock_info["added_time"]) if "added_time" in stock_info else None
                        ),
                    )
                )

            # 按排序顺序排列
            stocks.sort(key=lambda x: x.sort_order)
            return stocks

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get watchlist: {e}")
            return self._get_mock_watchlist(group)

    def add_to_watchlist(self, symbol: str, name: str, group: str = "默认") -> Dict[str, Any]:
        """添加自选股

        Args:
            symbol: 股票代码
            name: 股票名称
            group: 分组名称

        Returns:
            操作结果
        """
        logger.info(f"Adding to watchlist: {symbol} ({name}) -> {group}")

        try:
            if self.redis_client:
                import json  # pylint: disable=import-outside-toplevel

                stock_data = {"name": name, "group": group, "sort_order": 0, "added_time": datetime.now().isoformat()}
                self.redis_client.hset("mia:watchlist:stocks", symbol, json.dumps(stock_data))

            return {"success": True, "message": f"{symbol} 已添加到自选股", "symbol": symbol, "group": group}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to add to watchlist: {e}")
            return {"success": False, "message": f"添加失败: {str(e)}", "error": str(e)}

    def remove_from_watchlist(self, symbol: str) -> Dict[str, Any]:
        """删除自选股

        Args:
            symbol: 股票代码

        Returns:
            操作结果
        """
        logger.info(f"Removing from watchlist: {symbol}")

        try:
            if self.redis_client:
                self.redis_client.hdel("mia:watchlist:stocks", symbol)

            return {"success": True, "message": f"{symbol} 已从自选股删除", "symbol": symbol}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to remove from watchlist: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}", "error": str(e)}

    def get_sector_heatmap(self, sector_type: str = "行业") -> List[SectorHeat]:
        """获取板块热力图数据

        白皮书依据: 附录A 重点关注 - 板块热力图
        数据源: Redis (mia:sectors:*)
        刷新频率: 1分钟

        Args:
            sector_type: 板块类型 (行业/概念)

        Returns:
            板块热度列表
        """
        if self.redis_client is None:
            sectors = self._get_mock_sector_heatmap(sector_type)
            sectors.sort(key=lambda x: x.heat_score, reverse=True)
            return sectors

        try:
            sector_key = f"mia:sectors:{sector_type}"
            sector_data = self.redis_client.hgetall(sector_key)

            sectors = []
            for name, data in sector_data.items():
                if isinstance(name, bytes):
                    name = name.decode()
                if isinstance(data, bytes):
                    data = data.decode()

                import json  # pylint: disable=import-outside-toplevel

                info = json.loads(data)

                sectors.append(
                    SectorHeat(
                        sector_name=name,
                        sector_type=sector_type,
                        heat_score=float(info.get("heat_score", 0)),
                        change_pct=float(info.get("change_pct", 0)),
                        money_flow=float(info.get("money_flow", 0)),
                        sentiment_score=float(info.get("sentiment_score", 0)),
                    )
                )

            # 按热度排序
            sectors.sort(key=lambda x: x.heat_score, reverse=True)
            return sectors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get sector heatmap: {e}")
            return self._get_mock_sector_heatmap(sector_type)

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 重点关注
        技术实现: Streamlit + Plotly Treemap
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("🔭 重点关注 (Watchlist)")
        st.caption("AI核心池 · 自选股 · 板块热力图 · Admin Only")

        # Tab布局
        tab1, tab2, tab3 = st.tabs(["🎯 AI核心池", "⭐ 自选股", "🔥 板块热力图"])

        with tab1:
            self._render_core_pool()

        with tab2:
            self._render_watchlist()

        with tab3:
            self._render_sector_heatmap()

    def _render_core_pool(self) -> None:
        """渲染AI核心池"""
        st.subheader("🎯 AI核心池")
        st.caption("刷新频率: 5分钟")

        # 排名类型选择
        ranking_type = st.selectbox(
            "排名类型",
            options=[RankingType.COMBINED, RankingType.SOLDIER, RankingType.COMMANDER],
            format_func=lambda x: x.value,
        )

        stocks = self.get_core_pool(ranking_type, 20)

        if not stocks:
            st.info("暂无数据")
            return

        # 股票列表
        for stock in stocks:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1, 1, 1])

                with col1:
                    st.markdown(f"**{stock.rank}**")

                with col2:
                    st.markdown(f"**{stock.symbol}** {stock.name}")

                with col3:
                    st.metric("评分", f"{stock.score:.1f}")

                with col4:
                    st.write(f"¥{stock.price:.2f}")

                with col5:
                    color = self.COLOR_SCHEME["rise"] if stock.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<span style='color:{color}'>{stock.change_pct:+.2f}%</span>", unsafe_allow_html=True)

                st.divider()

    def _render_watchlist(self) -> None:
        """渲染自选股"""
        st.subheader("⭐ 自选股")
        st.caption("刷新频率: 5秒")

        # 添加自选股
        with st.expander("➕ 添加自选股"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_symbol = st.text_input("股票代码", key="new_symbol")
            with col2:
                new_name = st.text_input("股票名称", key="new_name")
            with col3:
                new_group = st.selectbox("分组", ["默认", "重点", "观察"], key="new_group")

            if st.button("添加"):
                if new_symbol and new_name:
                    result = self.add_to_watchlist(new_symbol, new_name, new_group)
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
                else:
                    st.warning("请输入股票代码和名称")

        # 分组筛选
        groups = ["全部", "默认", "重点", "观察"]
        selected_group = st.selectbox("分组筛选", groups)

        group_filter = None if selected_group == "全部" else selected_group
        stocks = self.get_watchlist(group_filter)

        if not stocks:
            st.info("暂无自选股")
            return

        # 自选股列表
        for stock in stocks:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 0.5])

                with col1:
                    st.markdown(f"**{stock.symbol}** {stock.name}")
                    st.caption(f"分组: {stock.group}")

                with col2:
                    st.write(f"¥{stock.price:.2f}")

                with col3:
                    color = self.COLOR_SCHEME["rise"] if stock.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<span style='color:{color}'>{stock.change_pct:+.2f}%</span>", unsafe_allow_html=True)

                with col4:
                    if stock.added_time:
                        st.caption(stock.added_time.strftime("%m-%d"))

                with col5:
                    if st.button("🗑️", key=f"del_{stock.symbol}"):
                        result = self.remove_from_watchlist(stock.symbol)
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()

                st.divider()

    def _render_sector_heatmap(self) -> None:
        """渲染板块热力图"""
        st.subheader("🔥 板块热力图")
        st.caption("刷新频率: 1分钟")

        # 板块类型选择
        sector_type = st.selectbox("板块类型", ["行业", "概念"])

        sectors = self.get_sector_heatmap(sector_type)

        if not sectors:
            st.info("暂无数据")
            return

        # Treemap热力图
        if HAS_PLOTLY:
            names = [s.sector_name for s in sectors]
            values = [abs(s.heat_score) for s in sectors]
            colors = [s.change_pct for s in sectors]

            fig = px.treemap(
                names=names,
                parents=[""] * len(names),
                values=values,
                color=colors,
                color_continuous_scale=["#52C41A", "#FFFFFF", "#FF4D4F"],
                color_continuous_midpoint=0,
            )

            fig.update_layout(
                title=f"{sector_type}板块热力图", coloraxis_colorbar=dict(title="涨跌幅%")  # pylint: disable=r1735
            )  # pylint: disable=r1735

            st.plotly_chart(fig, use_container_width=True)

        # 板块列表
        st.markdown("#### 板块详情")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**热门板块 Top 5**")
            for sector in sectors[:5]:
                color = self.COLOR_SCHEME["rise"] if sector.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                st.markdown(
                    f"- {sector.sector_name}: "
                    f"<span style='color:{color}'>{sector.change_pct:+.2f}%</span> "
                    f"(热度: {sector.heat_score:.0f})",
                    unsafe_allow_html=True,
                )

        with col2:
            st.markdown("**资金流向 Top 5**")
            sorted_by_flow = sorted(sectors, key=lambda x: x.money_flow, reverse=True)[:5]
            for sector in sorted_by_flow:
                flow_color = self.COLOR_SCHEME["rise"] if sector.money_flow >= 0 else self.COLOR_SCHEME["fall"]
                st.markdown(
                    f"- {sector.sector_name}: " f"<span style='color:{flow_color}'>{sector.money_flow:+.1f}亿</span>",
                    unsafe_allow_html=True,
                )

    def _get_mock_core_pool(self, ranking_type: RankingType, limit: int) -> List[CorePoolStock]:
        """获取模拟核心池数据"""
        stocks = [
            ("000001", "平安银行", 92.5, 12.50, 2.35),
            ("600519", "贵州茅台", 91.2, 1850.00, 1.25),
            ("000858", "五粮液", 89.8, 168.50, 3.15),
            ("002594", "比亚迪", 88.5, 265.00, -1.85),
            ("300750", "宁德时代", 87.2, 198.00, 2.50),
            ("601318", "中国平安", 86.5, 48.50, 1.05),
            ("000333", "美的集团", 85.8, 62.30, 0.85),
            ("600036", "招商银行", 84.5, 35.20, 1.45),
            ("002415", "海康威视", 83.2, 32.80, -0.65),
            ("601012", "隆基绿能", 82.5, 28.50, 2.15),
            ("600900", "长江电力", 81.8, 26.80, 0.55),
            ("000568", "泸州老窖", 80.5, 185.00, 1.85),
            ("002304", "洋河股份", 79.2, 128.50, 0.95),
            ("600276", "恒瑞医药", 78.5, 42.30, -1.25),
            ("000651", "格力电器", 77.8, 38.50, 0.65),
            ("601888", "中国中免", 76.5, 85.20, 2.85),
            ("002352", "顺丰控股", 75.2, 42.80, 1.15),
            ("600309", "万华化学", 74.5, 82.50, -0.45),
            ("002475", "立讯精密", 73.8, 28.50, 1.95),
            ("300059", "东方财富", 72.5, 18.50, 3.25),
        ]

        return [
            CorePoolStock(
                rank=i + 1, symbol=s[0], name=s[1], score=s[2], price=s[3], change_pct=s[4], ranking_type=ranking_type
            )
            for i, s in enumerate(stocks[:limit])
        ]

    def _get_mock_watchlist(self, group: Optional[str]) -> List[WatchlistStock]:
        """获取模拟自选股数据"""
        stocks = [
            WatchlistStock("000001", "平安银行", 12.50, 2.35, "重点", 1, datetime.now()),
            WatchlistStock("600519", "贵州茅台", 1850.00, 1.25, "重点", 2, datetime.now()),
            WatchlistStock("000858", "五粮液", 168.50, 3.15, "默认", 3, datetime.now()),
            WatchlistStock("002594", "比亚迪", 265.00, -1.85, "观察", 4, datetime.now()),
            WatchlistStock("300750", "宁德时代", 198.00, 2.50, "默认", 5, datetime.now()),
        ]

        if group:
            stocks = [s for s in stocks if s.group == group]

        return stocks

    def _get_mock_sector_heatmap(self, sector_type: str) -> List[SectorHeat]:
        """获取模拟板块热力图数据"""
        if sector_type == "行业":
            sectors = [
                SectorHeat("银行", "行业", 95, 2.35, 15.5, 82),
                SectorHeat("白酒", "行业", 92, 3.15, 12.3, 88),
                SectorHeat("新能源", "行业", 88, 1.85, 8.5, 75),
                SectorHeat("医药", "行业", 75, -1.25, -5.2, 62),
                SectorHeat("房地产", "行业", 65, -2.15, -12.5, 45),
                SectorHeat("半导体", "行业", 85, 2.50, 10.2, 78),
                SectorHeat("汽车", "行业", 80, 1.05, 6.8, 70),
                SectorHeat("家电", "行业", 72, 0.85, 3.5, 65),
            ]
        else:
            sectors = [
                SectorHeat("人工智能", "概念", 98, 4.25, 25.5, 95),
                SectorHeat("ChatGPT", "概念", 95, 3.85, 18.2, 92),
                SectorHeat("新能源车", "概念", 88, 2.15, 12.5, 80),
                SectorHeat("光伏", "概念", 82, 1.55, 8.2, 72),
                SectorHeat("储能", "概念", 78, 1.25, 5.5, 68),
                SectorHeat("元宇宙", "概念", 65, -0.85, -3.2, 55),
                SectorHeat("数字货币", "概念", 72, 0.95, 2.8, 62),
                SectorHeat("碳中和", "概念", 75, 1.05, 4.5, 65),
            ]

        return sectors
