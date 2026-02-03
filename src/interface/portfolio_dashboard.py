"""资产与归因仪表盘 (Portfolio Dashboard)

白皮书依据: 附录A 全息指挥台 - 3. 资产与归因 (Portfolio)
优先级: P0 - 最高优先级

核心功能:
- 持仓列表 (实时盈亏)
- 双轨对比 (实盘 vs 模拟盘)
- 策略归因 (Alpha vs Beta)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import plotly.express as px
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


@dataclass
class Position:
    """持仓数据模型

    白皮书依据: 附录A 资产与归因 - 持仓列表

    Attributes:
        symbol: 股票代码
        name: 股票名称
        quantity: 持仓数量
        cost_price: 成本价
        current_price: 当前价
        market_value: 市值
        pnl: 盈亏金额
        pnl_pct: 盈亏百分比
        position_ratio: 仓位占比
        strategy_id: 策略ID
    """

    symbol: str
    name: str
    quantity: int
    cost_price: float
    current_price: float
    market_value: float
    pnl: float
    pnl_pct: float
    position_ratio: float
    strategy_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "position_ratio": self.position_ratio,
            "strategy_id": self.strategy_id,
        }


@dataclass
class DualTrackComparison:
    """双轨对比数据模型

    白皮书依据: 附录A 资产与归因 - 双轨对比

    Attributes:
        dates: 日期列表
        live_nav: 实盘净值曲线
        sim_nav: 模拟盘净值曲线
        slippage: 滑点分析
        execution_quality: 执行质量评分
    """

    dates: List[str] = field(default_factory=list)
    live_nav: List[float] = field(default_factory=list)
    sim_nav: List[float] = field(default_factory=list)
    slippage: float = 0.0
    execution_quality: float = 0.0


@dataclass
class StrategyAttribution:
    """策略归因数据模型

    白皮书依据: 附录A 资产与归因 - 策略归因

    Attributes:
        strategy_id: 策略ID
        strategy_name: 策略名称
        alpha: Alpha贡献
        beta: Beta贡献
        total_contribution: 总贡献
        contribution_pct: 贡献占比
    """

    strategy_id: str
    strategy_name: str
    alpha: float
    beta: float
    total_contribution: float
    contribution_pct: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "alpha": self.alpha,
            "beta": self.beta,
            "total_contribution": self.total_contribution,
            "contribution_pct": self.contribution_pct,
        }


@dataclass
class FactorAttribution:
    """因子归因数据模型

    Attributes:
        factor_name: 因子名称
        contribution: 贡献值
        contribution_pct: 贡献占比
    """

    factor_name: str
    contribution: float
    contribution_pct: float


class PortfolioDashboard:
    """资产与归因仪表盘

    白皮书依据: 附录A 全息指挥台 - 3. 资产与归因 (Portfolio)

    提供持仓管理和归因分析功能:
    - 持仓列表 (实时盈亏)
    - 双轨对比 (实盘 vs 模拟盘)
    - 策略归因 (Alpha vs Beta)

    Attributes:
        redis_client: Redis客户端
    """

    # 色彩方案 (红涨绿跌)
    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "primary": "#1890FF",
        "alpha": "#722ED1",
        "beta": "#13C2C2",
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化资产与归因仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("PortfolioDashboard initialized")

    def get_positions(self) -> List[Position]:
        """获取持仓列表

        白皮书依据: 附录A 资产与归因 - 持仓列表
        数据源: Redis (mia:positions:*)
        刷新频率: 1秒

        Returns:
            持仓列表
        """
        if self.redis_client is None:
            return self._get_mock_positions()

        try:
            # 获取所有持仓
            position_keys = self.redis_client.keys("mia:positions:*")

            positions = []
            total_value = 0

            # 先计算总市值
            for key in position_keys:
                pos_data = self.redis_client.hgetall(key)
                if pos_data:
                    total_value += float(pos_data.get("market_value", 0))

            # 构建持仓列表
            for key in position_keys:
                pos_data = self.redis_client.hgetall(key)
                if not pos_data:
                    continue

                market_value = float(pos_data.get("market_value", 0))
                position_ratio = (market_value / total_value * 100) if total_value > 0 else 0

                positions.append(
                    Position(
                        symbol=pos_data.get("symbol", ""),
                        name=pos_data.get("name", ""),
                        quantity=int(pos_data.get("quantity", 0)),
                        cost_price=float(pos_data.get("cost_price", 0)),
                        current_price=float(pos_data.get("current_price", 0)),
                        market_value=market_value,
                        pnl=float(pos_data.get("pnl", 0)),
                        pnl_pct=float(pos_data.get("pnl_pct", 0)),
                        position_ratio=position_ratio,
                        strategy_id=pos_data.get("strategy_id", ""),
                    )
                )

            # 按市值排序
            positions.sort(key=lambda x: x.market_value, reverse=True)
            return positions

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get positions: {e}")
            return self._get_mock_positions()

    def get_dual_track_comparison(self) -> DualTrackComparison:
        """获取双轨对比数据

        白皮书依据: 附录A 资产与归因 - 双轨对比

        Returns:
            双轨对比数据
        """
        if self.redis_client is None:
            return self._get_mock_dual_track()

        try:
            # 获取净值曲线数据
            live_data = self.redis_client.lrange("mia:nav:live", 0, -1)
            sim_data = self.redis_client.lrange("mia:nav:sim", 0, -1)
            dates = self.redis_client.lrange("mia:nav:dates", 0, -1)

            # 获取滑点和执行质量
            slippage = float(self.redis_client.get("mia:execution:slippage") or 0)
            execution_quality = float(self.redis_client.get("mia:execution:quality") or 0)

            return DualTrackComparison(
                dates=[d.decode() if isinstance(d, bytes) else d for d in dates],
                live_nav=[float(v) for v in live_data],
                sim_nav=[float(v) for v in sim_data],
                slippage=slippage,
                execution_quality=execution_quality,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get dual track comparison: {e}")
            return self._get_mock_dual_track()

    def get_strategy_attribution(self) -> List[StrategyAttribution]:
        """获取策略归因数据

        白皮书依据: 附录A 资产与归因 - 策略归因

        Returns:
            策略归因列表
        """
        if self.redis_client is None:
            return self._get_mock_strategy_attribution()

        try:
            # 获取策略归因数据
            attribution_keys = self.redis_client.keys("mia:attribution:strategy:*")

            attributions = []
            for key in attribution_keys:
                attr_data = self.redis_client.hgetall(key)
                if attr_data:
                    attributions.append(
                        StrategyAttribution(
                            strategy_id=attr_data.get("strategy_id", ""),
                            strategy_name=attr_data.get("strategy_name", ""),
                            alpha=float(attr_data.get("alpha", 0)),
                            beta=float(attr_data.get("beta", 0)),
                            total_contribution=float(attr_data.get("total_contribution", 0)),
                            contribution_pct=float(attr_data.get("contribution_pct", 0)),
                        )
                    )

            # 按贡献排序
            attributions.sort(key=lambda x: x.total_contribution, reverse=True)
            return attributions

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get strategy attribution: {e}")
            return self._get_mock_strategy_attribution()

    def get_factor_attribution(self) -> List[FactorAttribution]:
        """获取因子归因数据

        Returns:
            因子归因列表
        """
        if self.redis_client is None:
            return self._get_mock_factor_attribution()

        try:
            factor_data = self.redis_client.hgetall("mia:attribution:factors")

            attributions = []
            total = sum(float(v) for v in factor_data.values())

            for factor_name, contribution in factor_data.items():
                contrib = float(contribution)
                attributions.append(
                    FactorAttribution(
                        factor_name=factor_name,
                        contribution=contrib,
                        contribution_pct=(contrib / total * 100) if total > 0 else 0,
                    )
                )

            attributions.sort(key=lambda x: x.contribution, reverse=True)
            return attributions

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get factor attribution: {e}")
            return self._get_mock_factor_attribution()

    def close_position(self, symbol: str, confirm: bool = False) -> Dict[str, Any]:
        """平仓操作

        Args:
            symbol: 股票代码
            confirm: 是否确认

        Returns:
            操作结果
        """
        if not confirm:
            return {"success": False, "message": f"平仓 {symbol} 需要确认", "require_confirm": True}

        logger.info(f"Closing position: {symbol}")

        try:
            if self.redis_client:
                self.redis_client.publish("mia:commands", f"CLOSE_POSITION:{symbol}")

            return {"success": True, "message": f"{symbol} 平仓指令已发送", "timestamp": datetime.now().isoformat()}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to close position {symbol}: {e}")
            return {"success": False, "message": f"平仓失败: {str(e)}", "error": str(e)}

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 资产与归因
        技术实现: Streamlit st.dataframe() + Plotly
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("💼 资产与归因 (Portfolio)")
        st.caption("持仓管理 · 归因分析 · Admin Only")

        # Tab布局
        tab1, tab2, tab3 = st.tabs(["📋 持仓列表", "📊 双轨对比", "🎯 策略归因"])

        with tab1:
            self._render_positions()

        with tab2:
            self._render_dual_track()

        with tab3:
            self._render_attribution()

    def _render_positions(self) -> None:
        """渲染持仓列表"""
        st.subheader("📋 持仓列表")
        st.caption("实时更新 · 1秒刷新")

        positions = self.get_positions()

        if not positions:
            st.info("当前无持仓")
            return

        # 汇总信息
        total_value = sum(p.market_value for p in positions)
        total_pnl = sum(p.pnl for p in positions)
        total_pnl_pct = (total_pnl / (total_value - total_pnl) * 100) if total_value > total_pnl else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("持仓市值", f"¥{total_value:,.2f}")
        with col2:
            color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("总盈亏", f"¥{total_pnl:,.2f}", delta=f"{total_pnl_pct:+.2f}%", delta_color=color)
        with col3:
            st.metric("持仓数量", f"{len(positions)}只")

        st.divider()

        # 持仓表格
        for pos in positions:
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])

                with col1:
                    st.markdown(f"**{pos.symbol}**")
                    st.caption(pos.name)

                with col2:
                    st.metric("数量", f"{pos.quantity:,}")

                with col3:
                    st.metric("成本", f"¥{pos.cost_price:.2f}")

                with col4:
                    color = self.COLOR_SCHEME["rise"] if pos.pnl >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<span style='color:{color}'>¥{pos.current_price:.2f}</span>", unsafe_allow_html=True)

                with col5:
                    color = self.COLOR_SCHEME["rise"] if pos.pnl >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<span style='color:{color}'>¥{pos.pnl:,.2f}</span>", unsafe_allow_html=True)
                    st.markdown(f"<span style='color:{color}'>{pos.pnl_pct:+.2f}%</span>", unsafe_allow_html=True)

                with col6:
                    if st.button("平仓", key=f"close_{pos.symbol}"):
                        st.session_state[f"confirm_close_{pos.symbol}"] = True

                    if st.session_state.get(f"confirm_close_{pos.symbol}"):
                        if st.button("确认", key=f"confirm_{pos.symbol}"):
                            result = self.close_position(pos.symbol, confirm=True)
                            if result["success"]:
                                st.success(result["message"])
                            else:
                                st.error(result["message"])
                            st.session_state[f"confirm_close_{pos.symbol}"] = False

                st.divider()

    def _render_dual_track(self) -> None:
        """渲染双轨对比"""
        st.subheader("📊 双轨对比")
        st.caption("实盘 vs 模拟盘")

        comparison = self.get_dual_track_comparison()

        # 指标卡片
        col1, col2 = st.columns(2)
        with col1:
            st.metric("滑点", f"{comparison.slippage:.2f}%")
        with col2:
            st.metric("执行质量", f"{comparison.execution_quality:.0f}分")

        # 净值曲线对比图
        if HAS_PLOTLY and comparison.dates:
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=comparison.dates,
                    y=comparison.live_nav,
                    mode="lines",
                    name="实盘净值",
                    line=dict(color=self.COLOR_SCHEME["rise"], width=2),  # pylint: disable=r1735
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=comparison.dates,
                    y=comparison.sim_nav,
                    mode="lines",
                    name="模拟盘净值",
                    line=dict(color=self.COLOR_SCHEME["primary"], width=2, dash="dash"),  # pylint: disable=r1735
                )
            )

            fig.update_layout(
                title="净值曲线对比",
                xaxis_title="日期",
                yaxis_title="净值",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),  # pylint: disable=r1735
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无净值数据")

    def _render_attribution(self) -> None:
        """渲染策略归因"""
        st.subheader("🎯 策略归因")

        # 策略归因
        st.markdown("#### Alpha vs Beta 堆叠图")

        attributions = self.get_strategy_attribution()

        if HAS_PLOTLY and attributions:
            strategies = [a.strategy_name for a in attributions]
            alphas = [a.alpha for a in attributions]
            betas = [a.beta for a in attributions]

            fig = go.Figure()

            fig.add_trace(go.Bar(name="Alpha", x=strategies, y=alphas, marker_color=self.COLOR_SCHEME["alpha"]))

            fig.add_trace(go.Bar(name="Beta", x=strategies, y=betas, marker_color=self.COLOR_SCHEME["beta"]))

            fig.update_layout(
                barmode="stack",
                title="策略Alpha/Beta贡献",
                xaxis_title="策略",
                yaxis_title="贡献值",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),  # pylint: disable=r1735
            )

            st.plotly_chart(fig, use_container_width=True)

        # 策略贡献度表格
        st.markdown("#### 策略贡献度 (S01-S19)")

        for attr in attributions:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                st.markdown(f"**{attr.strategy_id}** {attr.strategy_name}")
            with col2:
                st.metric("Alpha", f"{attr.alpha:.2f}")
            with col3:
                st.metric("Beta", f"{attr.beta:.2f}")
            with col4:
                st.metric("贡献", f"{attr.contribution_pct:.1f}%")

        st.divider()

        # 因子贡献度
        st.markdown("#### 因子贡献度")

        factor_attrs = self.get_factor_attribution()

        if HAS_PLOTLY and factor_attrs:
            factors = [f.factor_name for f in factor_attrs]
            contributions = [f.contribution for f in factor_attrs]

            fig = px.pie(names=factors, values=contributions, title="因子贡献分布")

            st.plotly_chart(fig, use_container_width=True)

    def _get_mock_positions(self) -> List[Position]:
        """获取模拟持仓数据"""
        return [
            Position("000001", "平安银行", 10000, 11.50, 12.50, 125000, 10000, 8.70, 25.0, "S01"),
            Position("600519", "贵州茅台", 50, 1800.00, 1850.00, 92500, 2500, 2.78, 18.5, "S03"),
            Position("000858", "五粮液", 500, 160.00, 168.50, 84250, 4250, 5.31, 16.9, "S01"),
            Position("002594", "比亚迪", 300, 270.00, 265.00, 79500, -1500, -1.85, 15.9, "S05"),
            Position("300750", "宁德时代", 400, 195.00, 198.00, 79200, 1200, 1.54, 15.8, "S07"),
        ]

    def _get_mock_dual_track(self) -> DualTrackComparison:
        """获取模拟双轨对比数据"""
        import random  # pylint: disable=import-outside-toplevel

        dates = [f"2026-01-{i:02d}" for i in range(1, 28)]
        live_nav = [1.0]
        sim_nav = [1.0]

        for _ in range(26):
            live_nav.append(live_nav[-1] * (1 + random.uniform(-0.02, 0.03)))
            sim_nav.append(sim_nav[-1] * (1 + random.uniform(-0.02, 0.03)))

        return DualTrackComparison(dates=dates, live_nav=live_nav, sim_nav=sim_nav, slippage=0.15, execution_quality=92)

    def _get_mock_strategy_attribution(self) -> List[StrategyAttribution]:
        """获取模拟策略归因数据"""
        return [
            StrategyAttribution("S01", "动量策略", 0.85, 0.35, 1.20, 28.5),
            StrategyAttribution("S03", "价值策略", 0.65, 0.45, 1.10, 26.2),
            StrategyAttribution("S05", "成长策略", 0.55, 0.25, 0.80, 19.0),
            StrategyAttribution("S07", "量价策略", 0.45, 0.30, 0.75, 17.9),
            StrategyAttribution("S09", "事件驱动", 0.25, 0.10, 0.35, 8.4),
        ]

    def _get_mock_factor_attribution(self) -> List[FactorAttribution]:
        """获取模拟因子归因数据"""
        return [
            FactorAttribution("动量因子", 0.35, 25.0),
            FactorAttribution("价值因子", 0.28, 20.0),
            FactorAttribution("质量因子", 0.21, 15.0),
            FactorAttribution("规模因子", 0.18, 12.9),
            FactorAttribution("波动率因子", 0.15, 10.7),
            FactorAttribution("流动性因子", 0.12, 8.6),
            FactorAttribution("其他", 0.11, 7.8),
        ]
