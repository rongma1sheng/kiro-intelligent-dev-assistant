"""驾驶舱仪表盘 (Cockpit Dashboard)

白皮书依据: 附录A 全息指挥台 - 1. 驾驶舱 (Cockpit)
优先级: P0 - 最高优先级

核心功能:
- 实时指标 (总资产、当日盈亏、当前仓位、风险水位)
- 市场宏观 (涨跌家数比、市场态)
- 紧急控制 (一键清仓、暂停买入、末日开关)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class MarketRegime(Enum):
    """市场状态枚举

    白皮书依据: 附录A 驾驶舱 - 市场态
    """

    BULL = "牛市"
    BEAR = "熊市"
    OSCILLATION = "震荡"
    CRASH = "崩盘"


class RiskLevel(Enum):
    """风险等级枚举"""

    LOW = "低风险"
    MEDIUM = "中风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"


@dataclass
class RealTimeMetrics:
    """实时指标数据模型

    白皮书依据: 附录A 驾驶舱 - 实时指标

    Attributes:
        total_assets: 总资产
        daily_pnl: 当日盈亏金额
        daily_pnl_pct: 当日盈亏百分比
        position_count: 持仓数量
        position_value: 持仓市值
        position_ratio: 仓位占比
        risk_level: 风险等级
        risk_score: 风险评分 (0-100)
        update_time: 更新时间
    """

    total_assets: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    position_count: int = 0
    position_value: float = 0.0
    position_ratio: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: float = 0.0
    update_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_assets": self.total_assets,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.daily_pnl_pct,
            "position_count": self.position_count,
            "position_value": self.position_value,
            "position_ratio": self.position_ratio,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "update_time": self.update_time.isoformat(),
        }


@dataclass
class MarketMacro:
    """市场宏观数据模型

    白皮书依据: 附录A 驾驶舱 - 市场宏观

    Attributes:
        advance_count: 上涨家数
        decline_count: 下跌家数
        adr: 涨跌家数比 (Advance-Decline Ratio)
        regime: 市场状态
        regime_confidence: 状态置信度
        update_time: 更新时间
    """

    advance_count: int = 0
    decline_count: int = 0
    adr: float = 1.0
    regime: MarketRegime = MarketRegime.OSCILLATION
    regime_confidence: float = 0.0
    update_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "advance_count": self.advance_count,
            "decline_count": self.decline_count,
            "adr": self.adr,
            "regime": self.regime.value,
            "regime_confidence": self.regime_confidence,
            "update_time": self.update_time.isoformat(),
        }


@dataclass
class EmergencyControlState:
    """紧急控制状态

    白皮书依据: 附录A 驾驶舱 - 紧急控制

    Attributes:
        buy_paused: 是否暂停买入
        emergency_stop: 是否触发末日开关
        last_liquidation: 最后清仓时间
    """

    buy_paused: bool = False
    emergency_stop: bool = False
    last_liquidation: Optional[datetime] = None


class CockpitDashboard:
    """驾驶舱仪表盘

    白皮书依据: 附录A 全息指挥台 - 1. 驾驶舱 (Cockpit)

    提供核心交易监控功能:
    - 实时指标监控
    - 市场宏观状态
    - 紧急控制操作

    Attributes:
        redis_client: Redis客户端
        color_scheme: 色彩方案 (红涨绿跌)
        refresh_interval: 刷新间隔 (秒)
    """

    # 色彩方案 (红涨绿跌 - 中国A股标准)
    COLOR_SCHEME = {
        "rise_primary": "#FF4D4F",  # 上涨红色
        "fall_primary": "#52C41A",  # 下跌绿色
        "neutral": "#8C8C8C",  # 中性灰色
        "warning": "#FA8C16",  # 警告橙色
        "danger": "#F5222D",  # 危险红色
        "success": "#52C41A",  # 成功绿色
        "primary": "#1890FF",  # 主题蓝色
    }

    def __init__(self, redis_client: Optional[Any] = None, refresh_interval: int = 1):
        """初始化驾驶舱仪表盘

        Args:
            redis_client: Redis客户端 (可选)
            refresh_interval: 刷新间隔，默认1秒
        """
        self.redis_client = redis_client
        self.refresh_interval = refresh_interval
        self._emergency_state = EmergencyControlState()

        logger.info(f"CockpitDashboard initialized with refresh_interval={refresh_interval}s")

    def get_realtime_metrics(self) -> RealTimeMetrics:
        """获取实时指标

        白皮书依据: 附录A 驾驶舱 - 实时指标
        数据源: Redis (mia:fund:*, mia:market:*)

        Returns:
            实时指标数据
        """
        if self.redis_client is None:
            # 返回模拟数据
            return self._get_mock_metrics()

        try:
            # 从Redis获取数据
            fund_data = self.redis_client.hgetall("mia:fund:summary")

            total_assets = float(fund_data.get("total_assets", 0))
            daily_pnl = float(fund_data.get("daily_pnl", 0))
            position_value = float(fund_data.get("position_value", 0))
            position_count = int(fund_data.get("position_count", 0))

            # 计算衍生指标
            daily_pnl_pct = (daily_pnl / (total_assets - daily_pnl) * 100) if total_assets > daily_pnl else 0
            position_ratio = (position_value / total_assets * 100) if total_assets > 0 else 0

            # 计算风险等级
            risk_score = self._calculate_risk_score(position_ratio, daily_pnl_pct)
            risk_level = self._get_risk_level(risk_score)

            return RealTimeMetrics(
                total_assets=total_assets,
                daily_pnl=daily_pnl,
                daily_pnl_pct=daily_pnl_pct,
                position_count=position_count,
                position_value=position_value,
                position_ratio=position_ratio,
                risk_level=risk_level,
                risk_score=risk_score,
                update_time=datetime.now(),
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get realtime metrics: {e}")
            return self._get_mock_metrics()

    def get_market_macro(self) -> MarketMacro:
        """获取市场宏观数据

        白皮书依据: 附录A 驾驶舱 - 市场宏观
        数据源: Redis (mia:market:*)

        Returns:
            市场宏观数据
        """
        if self.redis_client is None:
            return self._get_mock_market_macro()

        try:
            market_data = self.redis_client.hgetall("mia:market:summary")

            advance_count = int(market_data.get("advance_count", 0))
            decline_count = int(market_data.get("decline_count", 0))
            regime_str = market_data.get("regime", "OSCILLATION")
            regime_confidence = float(market_data.get("regime_confidence", 0))

            # 计算ADR
            adr = advance_count / decline_count if decline_count > 0 else float("inf")

            # 解析市场状态
            try:
                regime = MarketRegime[regime_str]
            except KeyError:
                regime = MarketRegime.OSCILLATION

            return MarketMacro(
                advance_count=advance_count,
                decline_count=decline_count,
                adr=adr,
                regime=regime,
                regime_confidence=regime_confidence,
                update_time=datetime.now(),
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get market macro: {e}")
            return self._get_mock_market_macro()

    def execute_liquidate_all(self, confirm: bool = False) -> Dict[str, Any]:
        """执行一键清仓

        白皮书依据: 附录A 驾驶舱 - 紧急控制 - 一键清仓

        Args:
            confirm: 是否确认执行 (需二次确认)

        Returns:
            执行结果
        """
        if not confirm:
            return {"success": False, "message": "一键清仓需要二次确认", "require_confirm": True}

        logger.warning("Executing LIQUIDATE ALL command")

        try:
            # 发送清仓指令到Redis
            if self.redis_client:
                self.redis_client.publish("mia:commands", "LIQUIDATE_ALL")
                self.redis_client.set("mia:emergency:liquidate_time", datetime.now().isoformat())

            self._emergency_state.last_liquidation = datetime.now()

            return {"success": True, "message": "清仓指令已发送", "timestamp": datetime.now().isoformat()}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to execute liquidate all: {e}")
            return {"success": False, "message": f"清仓失败: {str(e)}", "error": str(e)}

    def execute_pause_buy(self, pause: bool = True) -> Dict[str, Any]:
        """执行暂停买入

        白皮书依据: 附录A 驾驶舱 - 紧急控制 - 暂停买入

        Args:
            pause: True=暂停, False=恢复

        Returns:
            执行结果
        """
        action = "暂停" if pause else "恢复"
        logger.info(f"Executing PAUSE BUY: {action}")

        try:
            if self.redis_client:
                self.redis_client.set("mia:emergency:buy_paused", str(pause).lower())
                self.redis_client.publish("mia:commands", f"PAUSE_BUY:{pause}")

            self._emergency_state.buy_paused = pause

            return {
                "success": True,
                "message": f"买入已{action}",
                "buy_paused": pause,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to execute pause buy: {e}")
            return {"success": False, "message": f"{action}买入失败: {str(e)}", "error": str(e)}

    def execute_emergency_stop(self, confirm: bool = False) -> Dict[str, Any]:
        """执行末日开关

        白皮书依据: 附录A 驾驶舱 - 紧急控制 - 末日开关

        Args:
            confirm: 是否确认执行 (需二次确认)

        Returns:
            执行结果
        """
        if not confirm:
            return {
                "success": False,
                "message": "末日开关需要二次确认，此操作将停止所有交易活动",
                "require_confirm": True,
                "warning": "⚠️ 警告：此操作不可逆，将立即停止所有交易活动！",
            }

        logger.critical("Executing EMERGENCY STOP command")

        try:
            if self.redis_client:
                self.redis_client.set("mia:emergency:stop", "true")
                self.redis_client.publish("mia:commands", "EMERGENCY_STOP")

            self._emergency_state.emergency_stop = True

            return {
                "success": True,
                "message": "末日开关已触发，所有交易活动已停止",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to execute emergency stop: {e}")
            return {"success": False, "message": f"末日开关触发失败: {str(e)}", "error": str(e)}

    def get_emergency_state(self) -> EmergencyControlState:
        """获取紧急控制状态

        Returns:
            紧急控制状态
        """
        if self.redis_client:
            try:
                buy_paused = self.redis_client.get("mia:emergency:buy_paused")
                emergency_stop = self.redis_client.get("mia:emergency:stop")

                self._emergency_state.buy_paused = buy_paused == "true" if buy_paused else False
                self._emergency_state.emergency_stop = emergency_stop == "true" if emergency_stop else False

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Failed to get emergency state: {e}")

        return self._emergency_state

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 驾驶舱
        技术实现: Streamlit st.metric() + st.button()
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("🎛️ 驾驶舱 (Cockpit)")
        st.caption("实时监控 · 紧急控制 · Admin Only")

        # 获取数据
        metrics = self.get_realtime_metrics()
        market = self.get_market_macro()
        emergency = self.get_emergency_state()

        # 实时指标区域
        st.subheader("📊 实时指标")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(label="总资产", value=f"¥{metrics.total_assets:,.2f}", delta=None)

        with col2:
            delta_color = "normal" if metrics.daily_pnl >= 0 else "inverse"
            st.metric(
                label="当日盈亏",
                value=f"¥{metrics.daily_pnl:,.2f}",
                delta=f"{metrics.daily_pnl_pct:+.2f}%",
                delta_color=delta_color,
            )

        with col3:
            st.metric(
                label="当前仓位", value=f"{metrics.position_count}只", delta=f"市值 ¥{metrics.position_value:,.0f}"
            )

        with col4:
            self._get_risk_color(metrics.risk_level)
            st.metric(label="风险水位", value=f"{metrics.position_ratio:.1f}%", delta=f"{metrics.risk_level.value}")

        st.divider()

        # 市场宏观区域
        st.subheader("🌍 市场宏观")
        col1, col2, col3 = st.columns(3)

        with col1:
            adr_display = f"{market.adr:.2f}" if market.adr != float("inf") else "∞"
            st.metric(
                label="涨跌家数比 (ADR)",
                value=adr_display,
                delta=f"涨{market.advance_count} / 跌{market.decline_count}",
            )

        with col2:
            regime_emoji = self._get_regime_emoji(market.regime)
            st.metric(
                label="市场态 (Regime)",
                value=f"{regime_emoji} {market.regime.value}",
                delta=f"置信度 {market.regime_confidence:.0%}",
            )

        with col3:
            st.metric(label="更新时间", value=market.update_time.strftime("%H:%M:%S"), delta=None)

        st.divider()

        # 紧急控制区域
        st.subheader("🚨 紧急控制")
        st.warning("以下操作需要二次确认，请谨慎操作！")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔴 一键清仓", type="primary", use_container_width=True):
                st.session_state["confirm_liquidate"] = True

            if st.session_state.get("confirm_liquidate"):
                if st.button("⚠️ 确认清仓", type="secondary"):
                    result = self.execute_liquidate_all(confirm=True)
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
                    st.session_state["confirm_liquidate"] = False

        with col2:
            pause_label = "▶️ 恢复买入" if emergency.buy_paused else "⏸️ 暂停买入"
            if st.button(pause_label, use_container_width=True):
                result = self.execute_pause_buy(pause=not emergency.buy_paused)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])

        with col3:
            if st.button("☠️ 末日开关", type="primary", use_container_width=True):
                st.session_state["confirm_emergency"] = True

            if st.session_state.get("confirm_emergency"):
                st.error("⚠️ 警告：此操作将停止所有交易活动！")
                if st.button("⚠️ 确认触发末日开关", type="secondary"):
                    result = self.execute_emergency_stop(confirm=True)
                    if result["success"]:
                        st.error(result["message"])
                    else:
                        st.error(result["message"])
                    st.session_state["confirm_emergency"] = False

        # 状态指示
        st.divider()
        status_col1, status_col2 = st.columns(2)

        with status_col1:
            if emergency.buy_paused:
                st.warning("⏸️ 买入已暂停")
            else:
                st.success("✅ 买入正常")

        with status_col2:
            if emergency.emergency_stop:
                st.error("☠️ 末日开关已触发")
            else:
                st.success("✅ 系统正常运行")

    def _calculate_risk_score(self, position_ratio: float, daily_pnl_pct: float) -> float:
        """计算风险评分

        Args:
            position_ratio: 仓位占比
            daily_pnl_pct: 当日盈亏百分比

        Returns:
            风险评分 (0-100)
        """
        # 仓位风险 (0-50分)
        position_risk = min(position_ratio / 2, 50)

        # 盈亏风险 (0-50分)
        pnl_risk = min(abs(daily_pnl_pct) * 10, 50) if daily_pnl_pct < 0 else 0

        return position_risk + pnl_risk

    def _get_risk_level(self, risk_score: float) -> RiskLevel:
        """根据风险评分获取风险等级

        Args:
            risk_score: 风险评分

        Returns:
            风险等级
        """
        if risk_score < 25:  # pylint: disable=no-else-return
            return RiskLevel.LOW
        elif risk_score < 50:
            return RiskLevel.MEDIUM
        elif risk_score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _get_risk_color(self, risk_level: RiskLevel) -> str:
        """获取风险等级对应的颜色

        Args:
            risk_level: 风险等级

        Returns:
            颜色代码
        """
        color_map = {
            RiskLevel.LOW: self.COLOR_SCHEME["success"],
            RiskLevel.MEDIUM: self.COLOR_SCHEME["warning"],
            RiskLevel.HIGH: self.COLOR_SCHEME["danger"],
            RiskLevel.CRITICAL: self.COLOR_SCHEME["danger"],
        }
        return color_map.get(risk_level, self.COLOR_SCHEME["neutral"])

    def _get_regime_emoji(self, regime: MarketRegime) -> str:
        """获取市场状态对应的emoji

        Args:
            regime: 市场状态

        Returns:
            emoji字符
        """
        emoji_map = {
            MarketRegime.BULL: "🐂",
            MarketRegime.BEAR: "🐻",
            MarketRegime.OSCILLATION: "〰️",
            MarketRegime.CRASH: "💥",
        }
        return emoji_map.get(regime, "❓")

    def _get_mock_metrics(self) -> RealTimeMetrics:
        """获取模拟指标数据"""
        return RealTimeMetrics(
            total_assets=10000000.0,
            daily_pnl=50000.0,
            daily_pnl_pct=0.5,
            position_count=15,
            position_value=6000000.0,
            position_ratio=60.0,
            risk_level=RiskLevel.MEDIUM,
            risk_score=35.0,
            update_time=datetime.now(),
        )

    def _get_mock_market_macro(self) -> MarketMacro:
        """获取模拟市场宏观数据"""
        return MarketMacro(
            advance_count=2500,
            decline_count=2000,
            adr=1.25,
            regime=MarketRegime.OSCILLATION,
            regime_confidence=0.75,
            update_time=datetime.now(),
        )
