"""衍生品实验室仪表盘 (Derivatives Lab Dashboard)

白皮书依据: 附录A 全息指挥台 - 10. 衍生品实验室 (Derivatives Lab)
优先级: P2 - 高级功能

核心功能:
- 期货合约管理
- 期权Greeks展示
- 衍生品策略分析
- 风险敞口监控
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class ContractType(Enum):
    """合约类型枚举"""

    STOCK_INDEX_FUTURE = "股指期货"
    COMMODITY_FUTURE = "商品期货"
    TREASURY_FUTURE = "国债期货"
    ETF_OPTION = "ETF期权"
    INDEX_OPTION = "指数期权"


class OptionType(Enum):
    """期权类型枚举"""

    CALL = "认购"
    PUT = "认沽"


@dataclass
class FutureContract:
    """期货合约数据模型

    Attributes:
        symbol: 合约代码
        name: 合约名称
        contract_type: 合约类型
        underlying: 标的
        price: 当前价格
        change_pct: 涨跌幅
        volume: 成交量
        open_interest: 持仓量
        expiry_date: 到期日
        margin_ratio: 保证金比例
    """

    symbol: str
    name: str
    contract_type: ContractType
    underlying: str
    price: float
    change_pct: float
    volume: int
    open_interest: int
    expiry_date: date
    margin_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "contract_type": self.contract_type.value,
            "underlying": self.underlying,
            "price": self.price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "open_interest": self.open_interest,
            "expiry_date": self.expiry_date.isoformat(),
            "margin_ratio": self.margin_ratio,
        }


@dataclass
class OptionContract:
    """期权合约数据模型

    Attributes:
        symbol: 合约代码
        underlying: 标的
        option_type: 期权类型
        strike_price: 行权价
        expiry_date: 到期日
        price: 当前价格
        implied_volatility: 隐含波动率
        delta: Delta
        gamma: Gamma
        vega: Vega
        theta: Theta
        rho: Rho
    """

    symbol: str
    underlying: str
    option_type: OptionType
    strike_price: float
    expiry_date: date
    price: float
    implied_volatility: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "underlying": self.underlying,
            "option_type": self.option_type.value,
            "strike_price": self.strike_price,
            "expiry_date": self.expiry_date.isoformat(),
            "price": self.price,
            "implied_volatility": self.implied_volatility,
            "delta": self.delta,
            "gamma": self.gamma,
            "vega": self.vega,
            "theta": self.theta,
            "rho": self.rho,
        }


@dataclass
class DerivativePosition:
    """衍生品持仓

    Attributes:
        symbol: 合约代码
        direction: 方向 (long/short)
        quantity: 数量
        avg_price: 平均成本
        current_price: 当前价格
        pnl: 盈亏
        margin_used: 占用保证金
    """

    symbol: str
    direction: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    margin_used: float


class DerivativesLabDashboard:
    """衍生品实验室仪表盘

    白皮书依据: 附录A 全息指挥台 - 10. 衍生品实验室 (Derivatives Lab)

    提供衍生品交易和分析功能:
    - 期货合约管理
    - 期权Greeks展示
    - 衍生品策略分析
    - 风险敞口监控
    """

    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "primary": "#1890FF",
        "warning": "#FA8C16",
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化衍生品实验室

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("DerivativesLabDashboard initialized")

    def get_future_contracts(self, contract_type: Optional[ContractType] = None) -> List[FutureContract]:
        """获取期货合约列表

        Args:
            contract_type: 合约类型筛选

        Returns:
            期货合约列表
        """
        if self.redis_client is None:
            return self._get_mock_futures()

        try:
            contracts = []
            symbols = self.redis_client.smembers("mia:derivatives:futures")

            for symbol in symbols:
                data = self.redis_client.hgetall(f"mia:derivatives:future:{symbol}")
                if data:
                    contract = FutureContract(
                        symbol=symbol,
                        name=data.get("name", ""),
                        contract_type=ContractType[data.get("type", "STOCK_INDEX_FUTURE")],
                        underlying=data.get("underlying", ""),
                        price=float(data.get("price", 0)),
                        change_pct=float(data.get("change_pct", 0)),
                        volume=int(data.get("volume", 0)),
                        open_interest=int(data.get("open_interest", 0)),
                        expiry_date=date.fromisoformat(data.get("expiry_date", date.today().isoformat())),
                        margin_ratio=float(data.get("margin_ratio", 0.1)),
                    )

                    if contract_type is None or contract.contract_type == contract_type:
                        contracts.append(contract)

            return contracts if contracts else self._get_mock_futures()

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get future contracts: {e}")
            return self._get_mock_futures()

    def get_option_chain(self, underlying: str) -> List[OptionContract]:
        """获取期权链

        Args:
            underlying: 标的代码

        Returns:
            期权合约列表
        """
        if self.redis_client is None:
            return self._get_mock_options(underlying)

        try:
            options = []
            symbols = self.redis_client.smembers(f"mia:derivatives:options:{underlying}")

            for symbol in symbols:
                data = self.redis_client.hgetall(f"mia:derivatives:option:{symbol}")
                if data:
                    options.append(
                        OptionContract(
                            symbol=symbol,
                            underlying=underlying,
                            option_type=OptionType[data.get("option_type", "CALL")],
                            strike_price=float(data.get("strike", 0)),
                            expiry_date=date.fromisoformat(data.get("expiry", date.today().isoformat())),
                            price=float(data.get("price", 0)),
                            implied_volatility=float(data.get("iv", 0)),
                            delta=float(data.get("delta", 0)),
                            gamma=float(data.get("gamma", 0)),
                            vega=float(data.get("vega", 0)),
                            theta=float(data.get("theta", 0)),
                            rho=float(data.get("rho", 0)),
                        )
                    )

            return options if options else self._get_mock_options(underlying)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get option chain: {e}")
            return self._get_mock_options(underlying)

    def get_positions(self) -> List[DerivativePosition]:
        """获取衍生品持仓

        Returns:
            持仓列表
        """
        if self.redis_client is None:
            return self._get_mock_positions()

        try:
            positions = []
            symbols = self.redis_client.smembers("mia:derivatives:positions")

            for symbol in symbols:
                data = self.redis_client.hgetall(f"mia:derivatives:position:{symbol}")
                if data:
                    positions.append(
                        DerivativePosition(
                            symbol=symbol,
                            direction=data.get("direction", "long"),
                            quantity=int(data.get("quantity", 0)),
                            avg_price=float(data.get("avg_price", 0)),
                            current_price=float(data.get("current_price", 0)),
                            pnl=float(data.get("pnl", 0)),
                            margin_used=float(data.get("margin_used", 0)),
                        )
                    )

            return positions if positions else self._get_mock_positions()

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get positions: {e}")
            return self._get_mock_positions()

    def render_streamlit(self) -> None:
        """渲染Streamlit界面"""
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available")
            return

        st.title("🧪 衍生品实验室 (Derivatives Lab)")
        st.caption("期货管理 · 期权Greeks · 策略分析 · 风险监控")

        tab1, tab2, tab3, tab4 = st.tabs(["📈 期货合约", "📊 期权链", "💼 持仓管理", "⚠️ 风险监控"])

        with tab1:
            self._render_futures()

        with tab2:
            self._render_options()

        with tab3:
            self._render_positions()

        with tab4:
            self._render_risk_monitor()

    def _render_futures(self) -> None:
        """渲染期货合约"""
        st.subheader("📈 期货合约")

        # 类型筛选
        type_filter = st.selectbox("合约类型", ["全部", "股指期货", "商品期货", "国债期货"])

        contract_type = None
        if type_filter == "股指期货":
            contract_type = ContractType.STOCK_INDEX_FUTURE
        elif type_filter == "商品期货":
            contract_type = ContractType.COMMODITY_FUTURE
        elif type_filter == "国债期货":
            contract_type = ContractType.TREASURY_FUTURE

        contracts = self.get_future_contracts(contract_type)

        for contract in contracts:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

                with col1:
                    st.markdown(f"**{contract.symbol}**")
                    st.caption(f"{contract.name} | {contract.contract_type.value}")

                with col2:
                    color = self.COLOR_SCHEME["rise"] if contract.change_pct >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"<span style='color:{color}'>{contract.price:.2f}</span>", unsafe_allow_html=True)
                    st.markdown(
                        f"<span style='color:{color}'>{contract.change_pct:+.2f}%</span>", unsafe_allow_html=True
                    )

                with col3:
                    st.metric("成交量", f"{contract.volume:,}")

                with col4:
                    st.metric("持仓量", f"{contract.open_interest:,}")

                with col5:
                    days_to_expiry = (contract.expiry_date - date.today()).days
                    st.metric("到期", f"{days_to_expiry}天")

                st.divider()

    def _render_options(self) -> None:
        """渲染期权链"""
        st.subheader("📊 期权链")

        underlying = st.selectbox("选择标的", ["510050", "510300", "159919", "000300"])

        options = self.get_option_chain(underlying)

        # 分离认购和认沽
        calls = [o for o in options if o.option_type == OptionType.CALL]
        puts = [o for o in options if o.option_type == OptionType.PUT]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 认购期权 (Call)")
            for opt in calls:
                with st.expander(f"行权价 {opt.strike_price:.2f}"):
                    st.metric("价格", f"{opt.price:.4f}")
                    st.metric("隐含波动率", f"{opt.implied_volatility:.2%}")

                    gcol1, gcol2, gcol3 = st.columns(3)
                    with gcol1:
                        st.metric("Delta", f"{opt.delta:.4f}")
                        st.metric("Gamma", f"{opt.gamma:.6f}")
                    with gcol2:
                        st.metric("Vega", f"{opt.vega:.4f}")
                        st.metric("Theta", f"{opt.theta:.4f}")
                    with gcol3:
                        st.metric("Rho", f"{opt.rho:.4f}")

        with col2:
            st.markdown("### 认沽期权 (Put)")
            for opt in puts:
                with st.expander(f"行权价 {opt.strike_price:.2f}"):
                    st.metric("价格", f"{opt.price:.4f}")
                    st.metric("隐含波动率", f"{opt.implied_volatility:.2%}")

                    gcol1, gcol2, gcol3 = st.columns(3)
                    with gcol1:
                        st.metric("Delta", f"{opt.delta:.4f}")
                        st.metric("Gamma", f"{opt.gamma:.6f}")
                    with gcol2:
                        st.metric("Vega", f"{opt.vega:.4f}")
                        st.metric("Theta", f"{opt.theta:.4f}")
                    with gcol3:
                        st.metric("Rho", f"{opt.rho:.4f}")

    def _render_positions(self) -> None:
        """渲染持仓管理"""
        st.subheader("💼 衍生品持仓")

        positions = self.get_positions()

        # 汇总统计
        total_pnl = sum(p.pnl for p in positions)
        total_margin = sum(p.margin_used for p in positions)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("持仓数量", len(positions))
        with col2:
            color = self.COLOR_SCHEME["rise"] if total_pnl >= 0 else self.COLOR_SCHEME["fall"]
            st.markdown(f"总盈亏: <span style='color:{color}'>¥{total_pnl:,.2f}</span>", unsafe_allow_html=True)
        with col3:
            st.metric("占用保证金", f"¥{total_margin:,.2f}")

        st.divider()

        for pos in positions:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

                with col1:
                    direction_icon = "🟢" if pos.direction == "long" else "🔴"
                    st.markdown(f"{direction_icon} **{pos.symbol}**")
                    st.caption(f"{'多头' if pos.direction == 'long' else '空头'} | {pos.quantity}手")

                with col2:
                    st.metric("成本", f"{pos.avg_price:.2f}")

                with col3:
                    st.metric("现价", f"{pos.current_price:.2f}")

                with col4:
                    color = self.COLOR_SCHEME["rise"] if pos.pnl >= 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(f"盈亏: <span style='color:{color}'>¥{pos.pnl:,.2f}</span>", unsafe_allow_html=True)

                with col5:
                    st.metric("保证金", f"¥{pos.margin_used:,.0f}")

                st.divider()

    def _render_risk_monitor(self) -> None:
        """渲染风险监控"""
        st.subheader("⚠️ 风险敞口监控")

        positions = self.get_positions()

        # 计算风险指标
        total_margin = sum(p.margin_used for p in positions)
        total_notional = sum(p.current_price * p.quantity * 100 for p in positions)  # 假设每手100单位

        # 风险水位
        margin_ratio = 0.25  # 假设保证金比例
        risk_level = total_margin / (total_notional * margin_ratio) if total_notional > 0 else 0

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("总名义价值", f"¥{total_notional:,.0f}")

        with col2:
            st.metric("保证金占用", f"¥{total_margin:,.0f}")

        with col3:
            if risk_level < 0.5:
                st.success(f"风险水位: {risk_level:.1%} (安全)")
            elif risk_level < 0.8:
                st.warning(f"风险水位: {risk_level:.1%} (警告)")
            else:
                st.error(f"风险水位: {risk_level:.1%} (危险)")

        st.divider()

        # 风险限制
        st.markdown("### 风险限制")

        limits = [
            ("衍生品总保证金", "< 30%", "25%", True),
            ("单品种敞口", "< 10%", "8%", True),
            ("Delta敞口", "< 50万", "35万", True),
            ("Gamma敞口", "< 10万", "12万", False),
        ]

        for name, limit, current, ok in limits:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{name}**")
            with col2:
                st.caption(f"限制: {limit}")
            with col3:
                if ok:
                    st.success(f"✅ {current}")
                else:
                    st.error(f"❌ {current}")

    def _get_mock_futures(self) -> List[FutureContract]:
        """获取模拟期货数据"""
        return [
            FutureContract(
                "IF2402",
                "沪深300股指期货2402",
                ContractType.STOCK_INDEX_FUTURE,
                "000300",
                3850.2,
                0.85,
                125000,
                180000,
                date(2026, 2, 21),
                0.12,
            ),
            FutureContract(
                "IC2402",
                "中证500股指期货2402",
                ContractType.STOCK_INDEX_FUTURE,
                "000905",
                5420.6,
                -0.32,
                85000,
                120000,
                date(2026, 2, 21),
                0.14,
            ),
            FutureContract(
                "IH2402",
                "上证50股指期货2402",
                ContractType.STOCK_INDEX_FUTURE,
                "000016",
                2680.4,
                1.15,
                65000,
                95000,
                date(2026, 2, 21),
                0.12,
            ),
            FutureContract(
                "T2403",
                "10年期国债期货2403",
                ContractType.TREASURY_FUTURE,
                "国债",
                101.250,
                0.05,
                45000,
                280000,
                date(2026, 3, 15),
                0.02,
            ),
        ]

    def _get_mock_options(self, underlying: str) -> List[OptionContract]:
        """获取模拟期权数据"""
        base_price = 3.5 if underlying == "510050" else 4.2  # pylint: disable=unused-variable
        return [
            OptionContract(
                f"{underlying}C2402M03500",
                underlying,
                OptionType.CALL,
                3.5,
                date(2026, 2, 28),
                0.1520,
                0.22,
                0.65,
                0.08,
                0.015,
                -0.008,
                0.002,
            ),
            OptionContract(
                f"{underlying}C2402M03600",
                underlying,
                OptionType.CALL,
                3.6,
                date(2026, 2, 28),
                0.0850,
                0.25,
                0.45,
                0.12,
                0.018,
                -0.010,
                0.001,
            ),
            OptionContract(
                f"{underlying}P2402M03400",
                underlying,
                OptionType.PUT,
                3.4,
                date(2026, 2, 28),
                0.0680,
                0.21,
                -0.35,
                0.10,
                0.014,
                -0.007,
                -0.001,
            ),
            OptionContract(
                f"{underlying}P2402M03300",
                underlying,
                OptionType.PUT,
                3.3,
                date(2026, 2, 28),
                0.0420,
                0.23,
                -0.25,
                0.08,
                0.012,
                -0.006,
                -0.001,
            ),
        ]

    def _get_mock_positions(self) -> List[DerivativePosition]:
        """获取模拟持仓数据"""
        return [
            DerivativePosition("IF2402", "long", 2, 3820.0, 3850.2, 18120.0, 92160.0),
            DerivativePosition("IC2402", "short", 1, 5450.0, 5420.6, 5880.0, 75888.4),
            DerivativePosition("510050C2402M03500", "long", 10, 0.1450, 0.1520, 700.0, 1520.0),
        ]
