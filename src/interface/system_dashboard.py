"""系统中枢仪表盘 (System Dashboard)

白皮书依据: 附录A 全息指挥台 - 7. 系统中枢 (System)
优先级: P1 - 高优先级

核心功能:
- 硬件遥测
- API成本监控
- 热调优
"""

from dataclasses import dataclass, field
from datetime import date, datetime
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

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class RiskPreference(Enum):
    """风险偏好枚举"""

    CONSERVATIVE = "保守"
    BALANCED = "平衡"
    AGGRESSIVE = "激进"


@dataclass
class HardwareTelemetry:
    """硬件遥测数据模型

    白皮书依据: 附录A 系统中枢 - 硬件遥测

    Attributes:
        cpu_usage: CPU使用率 (%)
        memory_usage: 内存使用率 (%)
        gpu_memory_usage: GPU显存使用率 (%)
        gpu_memory_fragmentation: GPU显存碎片率 (%)
        disk_usage: 磁盘使用率 (%)
        disk_free_gb: 磁盘剩余空间 (GB)
        network_latency_ms: 网络延迟 (ms)
        update_time: 更新时间
    """

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_memory_usage: float = 0.0
    gpu_memory_fragmentation: float = 0.0
    disk_usage: float = 0.0
    disk_free_gb: float = 0.0
    network_latency_ms: float = 0.0
    update_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "gpu_memory_usage": self.gpu_memory_usage,
            "gpu_memory_fragmentation": self.gpu_memory_fragmentation,
            "disk_usage": self.disk_usage,
            "disk_free_gb": self.disk_free_gb,
            "network_latency_ms": self.network_latency_ms,
            "update_time": self.update_time.isoformat(),
        }


@dataclass
class APICostData:
    """API成本数据模型

    白皮书依据: 附录A 系统中枢 - API成本监控

    Attributes:
        today_cost: 今日成本 (元)
        month_cost: 本月成本 (元)
        today_calls: 今日调用次数
        month_calls: 本月调用次数
        daily_limit: 日成本预警阈值
        monthly_limit: 月成本预警阈值
        cost_trend: 成本趋势数据
    """

    today_cost: float = 0.0
    month_cost: float = 0.0
    today_calls: int = 0
    month_calls: int = 0
    daily_limit: float = 50.0
    monthly_limit: float = 1500.0
    cost_trend: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def daily_warning(self) -> bool:
        """是否触发日成本预警"""
        return self.today_cost > self.daily_limit

    @property
    def monthly_warning(self) -> bool:
        """是否触发月成本预警"""
        return self.month_cost > self.monthly_limit

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "today_cost": self.today_cost,
            "month_cost": self.month_cost,
            "today_calls": self.today_calls,
            "month_calls": self.month_calls,
            "daily_warning": self.daily_warning,
            "monthly_warning": self.monthly_warning,
        }


@dataclass
class StrategySwitch:
    """策略开关数据模型

    Attributes:
        strategy_id: 策略ID
        strategy_name: 策略名称
        enabled: 是否启用
        position_limit: 仓位上限 (%)
    """

    strategy_id: str
    strategy_name: str
    enabled: bool = True
    position_limit: float = 100.0


@dataclass
class HotTuningConfig:
    """热调优配置数据模型

    白皮书依据: 附录A 系统中枢 - 热调优

    Attributes:
        risk_preference: 风险偏好
        strategy_switches: 策略开关列表
        global_position_limit: 全局仓位上限 (%)
    """

    risk_preference: RiskPreference = RiskPreference.BALANCED
    strategy_switches: List[StrategySwitch] = field(default_factory=list)
    global_position_limit: float = 80.0


class SystemDashboard:
    """系统中枢仪表盘

    白皮书依据: 附录A 全息指挥台 - 7. 系统中枢 (System)

    提供系统监控和调优功能:
    - 硬件遥测 (CPU/内存/GPU/磁盘/网络)
    - API成本监控 (日/月成本, 预警)
    - 热调优 (风险偏好, 策略开关, 仓位上限)

    Attributes:
        redis_client: Redis客户端
    """

    # 色彩方案
    COLOR_SCHEME = {
        "success": "#52C41A",
        "warning": "#FAAD14",
        "danger": "#FF4D4F",
        "info": "#1890FF",
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化系统中枢仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("SystemDashboard initialized")

    def get_hardware_telemetry(self) -> HardwareTelemetry:
        """获取硬件遥测数据

        白皮书依据: 附录A 系统中枢 - 硬件遥测
        数据源: psutil + Redis
        刷新频率: 1秒

        Returns:
            硬件遥测数据
        """
        telemetry = HardwareTelemetry()

        if HAS_PSUTIL:
            try:
                telemetry.cpu_usage = psutil.cpu_percent(interval=0.1)
                telemetry.memory_usage = psutil.virtual_memory().percent

                disk = psutil.disk_usage("D:/" if psutil.WINDOWS else "/")
                telemetry.disk_usage = disk.percent
                telemetry.disk_free_gb = disk.free / (1024**3)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Failed to get system metrics: {e}")

        # 从Redis获取GPU和网络数据
        if self.redis_client:
            try:
                gpu_data = self.redis_client.hgetall("mia:system:gpu")
                telemetry.gpu_memory_usage = float(gpu_data.get("memory_usage", 0))
                telemetry.gpu_memory_fragmentation = float(gpu_data.get("fragmentation", 0))

                network_data = self.redis_client.get("mia:system:network_latency")
                if network_data:
                    telemetry.network_latency_ms = float(network_data)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Failed to get Redis metrics: {e}")
        else:
            # 模拟数据
            import random  # pylint: disable=import-outside-toplevel

            telemetry.gpu_memory_usage = random.uniform(40, 80)
            telemetry.gpu_memory_fragmentation = random.uniform(5, 20)
            telemetry.network_latency_ms = random.uniform(10, 50)

        telemetry.update_time = datetime.now()
        return telemetry

    def get_api_cost_data(self) -> APICostData:
        """获取API成本数据

        白皮书依据: 附录A 系统中枢 - API成本监控
        数据源: Redis (mia:cost:*)
        刷新频率: 实时

        Returns:
            API成本数据
        """
        if self.redis_client is None:
            return self._get_mock_api_cost()

        try:
            cost_data = self.redis_client.hgetall("mia:cost:summary")

            # 获取成本趋势
            trend_data = self.redis_client.lrange("mia:cost:trend", -30, -1)
            cost_trend = []
            for item in trend_data:
                if isinstance(item, bytes):
                    item = item.decode()
                import json  # pylint: disable=import-outside-toplevel

                cost_trend.append(json.loads(item))

            return APICostData(
                today_cost=float(cost_data.get("today_cost", 0)),
                month_cost=float(cost_data.get("month_cost", 0)),
                today_calls=int(cost_data.get("today_calls", 0)),
                month_calls=int(cost_data.get("month_calls", 0)),
                daily_limit=float(cost_data.get("daily_limit", 50)),
                monthly_limit=float(cost_data.get("monthly_limit", 1500)),
                cost_trend=cost_trend,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get API cost data: {e}")
            return self._get_mock_api_cost()

    def get_hot_tuning_config(self) -> HotTuningConfig:
        """获取热调优配置

        白皮书依据: 附录A 系统中枢 - 热调优

        Returns:
            热调优配置
        """
        if self.redis_client is None:
            return self._get_mock_hot_tuning()

        try:
            config_data = self.redis_client.hgetall("mia:config:tuning")

            # 获取策略开关
            strategy_data = self.redis_client.hgetall("mia:config:strategies")
            switches = []
            for sid, data in strategy_data.items():
                if isinstance(sid, bytes):
                    sid = sid.decode()
                if isinstance(data, bytes):
                    data = data.decode()
                import json  # pylint: disable=import-outside-toplevel

                info = json.loads(data)
                switches.append(
                    StrategySwitch(
                        strategy_id=sid,
                        strategy_name=info.get("name", ""),
                        enabled=info.get("enabled", True),
                        position_limit=float(info.get("position_limit", 100)),
                    )
                )

            risk_pref_str = config_data.get("risk_preference", "BALANCED")
            if isinstance(risk_pref_str, bytes):
                risk_pref_str = risk_pref_str.decode()

            return HotTuningConfig(
                risk_preference=RiskPreference[risk_pref_str],
                strategy_switches=switches,
                global_position_limit=float(config_data.get("global_position_limit", 80)),
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get hot tuning config: {e}")
            return self._get_mock_hot_tuning()

    def update_risk_preference(self, preference: RiskPreference, confirm: bool = False) -> Dict[str, Any]:
        """更新风险偏好

        Args:
            preference: 风险偏好
            confirm: 是否确认

        Returns:
            操作结果
        """
        if not confirm:
            return {"success": False, "message": f"修改风险偏好为 {preference.value} 需要确认", "require_confirm": True}

        logger.info(f"Updating risk preference to: {preference.value}")

        try:
            if self.redis_client:
                self.redis_client.hset("mia:config:tuning", "risk_preference", preference.name)

            return {"success": True, "message": f"风险偏好已更新为 {preference.value}", "preference": preference.value}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to update risk preference: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}", "error": str(e)}

    def update_strategy_switch(self, strategy_id: str, enabled: bool, confirm: bool = False) -> Dict[str, Any]:
        """更新策略开关

        Args:
            strategy_id: 策略ID
            enabled: 是否启用
            confirm: 是否确认

        Returns:
            操作结果
        """
        action = "启用" if enabled else "禁用"

        if not confirm:
            return {"success": False, "message": f"{action}策略 {strategy_id} 需要确认", "require_confirm": True}

        logger.info(f"Updating strategy {strategy_id} to enabled={enabled}")

        try:
            if self.redis_client:
                import json  # pylint: disable=import-outside-toplevel

                current = self.redis_client.hget("mia:config:strategies", strategy_id)
                if current:
                    if isinstance(current, bytes):
                        current = current.decode()
                    data = json.loads(current)
                    data["enabled"] = enabled
                    self.redis_client.hset("mia:config:strategies", strategy_id, json.dumps(data))

            return {
                "success": True,
                "message": f"策略 {strategy_id} 已{action}",
                "strategy_id": strategy_id,
                "enabled": enabled,
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to update strategy switch: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}", "error": str(e)}

    def update_position_limit(
        self, limit: float, strategy_id: Optional[str] = None, confirm: bool = False
    ) -> Dict[str, Any]:
        """更新仓位上限

        Args:
            limit: 仓位上限 (0-100%)
            strategy_id: 策略ID (None表示全局)
            confirm: 是否确认

        Returns:
            操作结果
        """
        target = f"策略 {strategy_id}" if strategy_id else "全局"

        if not confirm:
            return {"success": False, "message": f"修改{target}仓位上限为 {limit}% 需要确认", "require_confirm": True}

        if not 0 <= limit <= 100:
            return {"success": False, "message": "仓位上限必须在 0-100% 之间", "error": "Invalid limit"}

        logger.info(f"Updating position limit for {target} to {limit}%")

        try:
            if self.redis_client:
                if strategy_id:
                    import json  # pylint: disable=import-outside-toplevel

                    current = self.redis_client.hget("mia:config:strategies", strategy_id)
                    if current:
                        if isinstance(current, bytes):
                            current = current.decode()
                        data = json.loads(current)
                        data["position_limit"] = limit
                        self.redis_client.hset("mia:config:strategies", strategy_id, json.dumps(data))
                else:
                    self.redis_client.hset("mia:config:tuning", "global_position_limit", str(limit))

            return {"success": True, "message": f"{target}仓位上限已更新为 {limit}%", "limit": limit}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to update position limit: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}", "error": str(e)}

    def render_streamlit(self) -> None:
        """渲染Streamlit界面

        白皮书依据: 附录A 系统中枢
        技术实现: Streamlit st.metric() + st.slider()
        """
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available, skipping render")
            return

        st.title("🛠️ 系统中枢 (System)")
        st.caption("硬件监控 · 成本管理 · 热调优 · Admin Only")

        # Tab布局
        tab1, tab2, tab3 = st.tabs(["📊 硬件遥测", "💰 API成本", "⚙️ 热调优"])

        with tab1:
            self._render_hardware_telemetry()

        with tab2:
            self._render_api_cost()

        with tab3:
            self._render_hot_tuning()

    def _render_hardware_telemetry(self) -> None:
        """渲染硬件遥测"""
        st.subheader("📊 硬件遥测")
        st.caption("刷新频率: 1秒")

        telemetry = self.get_hardware_telemetry()

        # CPU和内存
        col1, col2 = st.columns(2)

        with col1:
            self._get_usage_color(telemetry.cpu_usage)
            st.metric("CPU使用率", f"{telemetry.cpu_usage:.1f}%")
            st.progress(telemetry.cpu_usage / 100)

        with col2:
            self._get_usage_color(telemetry.memory_usage)
            st.metric("内存使用率", f"{telemetry.memory_usage:.1f}%")
            st.progress(telemetry.memory_usage / 100)

        st.divider()

        # GPU
        col1, col2 = st.columns(2)

        with col1:
            st.metric("GPU显存使用率", f"{telemetry.gpu_memory_usage:.1f}%")
            st.progress(telemetry.gpu_memory_usage / 100)

        with col2:
            st.metric("GPU显存碎片率", f"{telemetry.gpu_memory_fragmentation:.1f}%")
            st.progress(telemetry.gpu_memory_fragmentation / 100)

        st.divider()

        # 磁盘和网络
        col1, col2 = st.columns(2)

        with col1:
            st.metric("磁盘使用率 (D:)", f"{telemetry.disk_usage:.1f}%")
            st.caption(f"剩余空间: {telemetry.disk_free_gb:.1f} GB")

        with col2:
            (  # pylint: disable=w0104
                self.COLOR_SCHEME["success"] if telemetry.network_latency_ms < 50 else self.COLOR_SCHEME["warning"]
            )  # pylint: disable=w0104
            st.metric("网络延迟 (Tailscale)", f"{telemetry.network_latency_ms:.1f} ms")

        st.caption(f"更新时间: {telemetry.update_time.strftime('%H:%M:%S')}")

    def _render_api_cost(self) -> None:
        """渲染API成本监控"""
        st.subheader("💰 API成本监控")
        st.caption("成本预警: 日>¥50, 月>¥1500")

        cost_data = self.get_api_cost_data()

        # 成本指标
        col1, col2 = st.columns(2)

        with col1:
            if cost_data.daily_warning:
                st.error(f"⚠️ 今日成本: ¥{cost_data.today_cost:.2f}")
            else:
                st.metric("今日成本", f"¥{cost_data.today_cost:.2f}")
            st.caption(f"调用次数: {cost_data.today_calls:,}")

        with col2:
            if cost_data.monthly_warning:
                st.error(f"⚠️ 本月成本: ¥{cost_data.month_cost:.2f}")
            else:
                st.metric("本月成本", f"¥{cost_data.month_cost:.2f}")
            st.caption(f"调用次数: {cost_data.month_calls:,}")

        st.divider()

        # 成本趋势图
        st.markdown("#### 成本趋势")

        if HAS_PLOTLY and cost_data.cost_trend:
            dates = [item["date"] for item in cost_data.cost_trend]
            costs = [item["cost"] for item in cost_data.cost_trend]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=costs,
                    mode="lines+markers",
                    name="日成本",
                    line=dict(color=self.COLOR_SCHEME["info"]),  # pylint: disable=r1735
                )
            )

            # 预警线
            fig.add_hline(
                y=cost_data.daily_limit,
                line_dash="dash",
                line_color=self.COLOR_SCHEME["danger"],
                annotation_text="日预警线",
            )

            fig.update_layout(
                title="近30日成本趋势", xaxis_title="日期", yaxis_title="成本 (元)", hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无趋势数据")

    def _render_hot_tuning(self) -> None:
        """渲染热调优"""
        st.subheader("⚙️ 热调优")
        st.caption("参数修改需二次确认")

        config = self.get_hot_tuning_config()

        # 风险偏好
        st.markdown("#### 风险偏好")

        risk_options = [RiskPreference.CONSERVATIVE, RiskPreference.BALANCED, RiskPreference.AGGRESSIVE]
        risk_options.index(config.risk_preference)

        new_preference = st.select_slider(
            "风险偏好", options=risk_options, value=config.risk_preference, format_func=lambda x: x.value
        )

        if new_preference != config.risk_preference:
            if st.button("确认修改风险偏好"):
                result = self.update_risk_preference(new_preference, confirm=True)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])

        st.divider()

        # 全局仓位上限
        st.markdown("#### 全局仓位上限")

        new_limit = st.slider(
            "仓位上限 (%)", min_value=0, max_value=100, value=int(config.global_position_limit), step=5
        )

        if new_limit != config.global_position_limit:
            if st.button("确认修改仓位上限"):
                result = self.update_position_limit(float(new_limit), confirm=True)
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.error(result["message"])

        st.divider()

        # 策略开关
        st.markdown("#### 策略开关 (S01-S19)")

        for switch in config.strategy_switches:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"**{switch.strategy_id}** {switch.strategy_name}")

            with col2:
                new_enabled = st.checkbox("启用", value=switch.enabled, key=f"switch_{switch.strategy_id}")

                if new_enabled != switch.enabled:
                    if st.button("确认", key=f"confirm_{switch.strategy_id}"):
                        result = self.update_strategy_switch(switch.strategy_id, new_enabled, confirm=True)
                        if result["success"]:
                            st.success(result["message"])

            with col3:
                st.caption(f"仓位: {switch.position_limit:.0f}%")

    def _get_usage_color(self, usage: float) -> str:
        """根据使用率获取颜色"""
        if usage >= 90:  # pylint: disable=no-else-return
            return self.COLOR_SCHEME["danger"]
        elif usage >= 70:
            return self.COLOR_SCHEME["warning"]
        else:
            return self.COLOR_SCHEME["success"]

    def _get_mock_api_cost(self) -> APICostData:
        """获取模拟API成本数据"""
        import random  # pylint: disable=import-outside-toplevel

        # 生成趋势数据
        cost_trend = []
        for i in range(30):
            day = date.today().replace(day=max(1, date.today().day - 29 + i))
            cost_trend.append({"date": day.strftime("%Y-%m-%d"), "cost": random.uniform(20, 45)})

        return APICostData(
            today_cost=35.50,
            month_cost=856.20,
            today_calls=1256,
            month_calls=38520,
            daily_limit=50.0,
            monthly_limit=1500.0,
            cost_trend=cost_trend,
        )

    def _get_mock_hot_tuning(self) -> HotTuningConfig:
        """获取模拟热调优配置"""
        strategies = [
            StrategySwitch("S01", "动量策略", True, 100),
            StrategySwitch("S02", "均值回归", True, 80),
            StrategySwitch("S03", "价值投资", True, 100),
            StrategySwitch("S04", "成长策略", True, 90),
            StrategySwitch("S05", "事件驱动", False, 50),
            StrategySwitch("S06", "量价策略", True, 70),
            StrategySwitch("S07", "趋势跟踪", True, 85),
        ]

        return HotTuningConfig(
            risk_preference=RiskPreference.BALANCED, strategy_switches=strategies, global_position_limit=80.0
        )
