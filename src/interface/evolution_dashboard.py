"""进化工厂仪表盘 (Evolution Dashboard)

白皮书依据: 附录A 全息指挥台 - 8. 进化工厂 (Evolution)
优先级: P2 - 高级功能

核心功能:
- 因子挖掘进度监控
- Arena测试结果展示
- Z2H认证状态追踪
- 策略进化历史
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


class EvolutionPhase(Enum):
    """进化阶段枚举

    白皮书依据: 第四章 斯巴达进化
    """

    MINING = "因子挖掘"
    ARENA_TESTING = "Arena测试"
    SPARTA_EVALUATION = "斯巴达考核"
    SIMULATION = "模拟盘验证"
    Z2H_CERTIFICATION = "Z2H认证"
    PRODUCTION = "生产部署"


class CertificationLevel(Enum):
    """认证级别枚举"""

    PENDING = "待认证"
    SILVER = "银牌"
    GOLD = "金牌"
    PLATINUM = "铂金"


@dataclass
class FactorMiningStatus:
    """因子挖掘状态

    Attributes:
        miner_name: 挖掘器名称
        factors_discovered: 已发现因子数
        factors_validated: 已验证因子数
        current_generation: 当前进化代数
        best_fitness: 最佳适应度
        status: 运行状态
        start_time: 开始时间
        elapsed_time: 已用时间(秒)
    """

    miner_name: str
    factors_discovered: int
    factors_validated: int
    current_generation: int
    best_fitness: float
    status: str
    start_time: datetime
    elapsed_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "miner_name": self.miner_name,
            "factors_discovered": self.factors_discovered,
            "factors_validated": self.factors_validated,
            "current_generation": self.current_generation,
            "best_fitness": self.best_fitness,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "elapsed_time": self.elapsed_time,
        }


@dataclass
class ArenaTestResult:
    """Arena测试结果

    白皮书依据: 第四章 4.2 因子Arena三轨测试
    """

    factor_id: str
    factor_expression: str
    reality_track_score: float
    hell_track_score: float
    cross_market_score: float
    overall_score: float
    passed: bool
    test_time: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "factor_expression": self.factor_expression,
            "reality_track_score": self.reality_track_score,
            "hell_track_score": self.hell_track_score,
            "cross_market_score": self.cross_market_score,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "test_time": self.test_time.isoformat(),
        }


@dataclass
class Z2HCertification:
    """Z2H基因胶囊认证

    白皮书依据: 第四章 4.3 Z2H基因胶囊
    """

    strategy_id: str
    strategy_name: str
    certification_level: CertificationLevel
    arena_score: float
    simulation_return: float
    simulation_sharpe: float
    simulation_max_drawdown: float
    certification_date: Optional[datetime]
    expiry_date: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "certification_level": self.certification_level.value,
            "arena_score": self.arena_score,
            "simulation_return": self.simulation_return,
            "simulation_sharpe": self.simulation_sharpe,
            "simulation_max_drawdown": self.simulation_max_drawdown,
            "certification_date": self.certification_date.isoformat() if self.certification_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
        }


class EvolutionDashboard:
    """进化工厂仪表盘

    白皮书依据: 附录A 全息指挥台 - 8. 进化工厂 (Evolution)

    提供因子挖掘和策略进化的可视化监控:
    - 20个因子挖掘器状态
    - Arena三轨测试结果
    - Z2H认证进度
    - 策略进化历史
    """

    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "primary": "#1890FF",
        "warning": "#FA8C16",
        "success": "#52C41A",
        "gold": "#FFD700",
        "platinum": "#E5E4E2",
        "silver": "#C0C0C0",
    }

    MINER_NAMES = [
        "GeneticMiner",
        "ETFFactorMiner",
        "LOFFactorMiner",
        "SentimentBehaviorMiner",
        "EventDrivenMiner",
        "ESGIntelligenceMiner",
        "AIEnhancedMiner",
        "NetworkRelationshipMiner",
        "HighFrequencyMicrostructureMiner",
        "PriceVolumeRelationshipMiner",
        "StyleRotationMiner",
        "FactorCombinationMiner",
        "MLFeatureEngineeringMiner",
        "TimeSeriesDLMiner",
        "MacroCrossAssetMiner",
        "MetaMiner",
        "AlternativeDataMiner",
        "EnhancedIlliquidityMiner",
        "FlowRiskMiner",
        "MicrostructureRiskMiner",
    ]

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化进化工厂仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("EvolutionDashboard initialized")

    def get_mining_status(self) -> List[FactorMiningStatus]:
        """获取所有挖掘器状态

        Returns:
            挖掘器状态列表
        """
        if self.redis_client is None:
            return self._get_mock_mining_status()

        try:
            statuses = []
            for miner_name in self.MINER_NAMES:
                data = self.redis_client.hgetall(f"mia:evolution:miner:{miner_name}")
                if data:
                    statuses.append(
                        FactorMiningStatus(
                            miner_name=miner_name,
                            factors_discovered=int(data.get("factors_discovered", 0)),
                            factors_validated=int(data.get("factors_validated", 0)),
                            current_generation=int(data.get("current_generation", 0)),
                            best_fitness=float(data.get("best_fitness", 0)),
                            status=data.get("status", "idle"),
                            start_time=datetime.fromisoformat(data.get("start_time", datetime.now().isoformat())),
                            elapsed_time=float(data.get("elapsed_time", 0)),
                        )
                    )
            return statuses if statuses else self._get_mock_mining_status()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get mining status: {e}")
            return self._get_mock_mining_status()

    def get_arena_results(self, limit: int = 20) -> List[ArenaTestResult]:
        """获取Arena测试结果

        Args:
            limit: 返回数量限制

        Returns:
            测试结果列表
        """
        if self.redis_client is None:
            return self._get_mock_arena_results(limit)

        try:
            results = []
            factor_ids = self.redis_client.lrange("mia:arena:results", 0, limit - 1)
            for factor_id in factor_ids:
                data = self.redis_client.hgetall(f"mia:arena:result:{factor_id}")
                if data:
                    results.append(
                        ArenaTestResult(
                            factor_id=factor_id,
                            factor_expression=data.get("expression", ""),
                            reality_track_score=float(data.get("reality_score", 0)),
                            hell_track_score=float(data.get("hell_score", 0)),
                            cross_market_score=float(data.get("cross_market_score", 0)),
                            overall_score=float(data.get("overall_score", 0)),
                            passed=data.get("passed", "false").lower() == "true",
                            test_time=datetime.fromisoformat(data.get("test_time", datetime.now().isoformat())),
                        )
                    )
            return results if results else self._get_mock_arena_results(limit)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get arena results: {e}")
            return self._get_mock_arena_results(limit)

    def get_z2h_certifications(self) -> List[Z2HCertification]:
        """获取Z2H认证列表

        Returns:
            认证列表
        """
        if self.redis_client is None:
            return self._get_mock_z2h_certifications()

        try:
            certs = []
            strategy_ids = self.redis_client.smembers("mia:z2h:strategies")
            for strategy_id in strategy_ids:
                data = self.redis_client.hgetall(f"mia:z2h:cert:{strategy_id}")
                if data:
                    certs.append(
                        Z2HCertification(
                            strategy_id=strategy_id,
                            strategy_name=data.get("name", ""),
                            certification_level=CertificationLevel[data.get("level", "PENDING")],
                            arena_score=float(data.get("arena_score", 0)),
                            simulation_return=float(data.get("sim_return", 0)),
                            simulation_sharpe=float(data.get("sim_sharpe", 0)),
                            simulation_max_drawdown=float(data.get("sim_drawdown", 0)),
                            certification_date=(
                                datetime.fromisoformat(data["cert_date"]) if data.get("cert_date") else None
                            ),
                            expiry_date=(
                                datetime.fromisoformat(data["expiry_date"]) if data.get("expiry_date") else None
                            ),
                        )
                    )
            return certs if certs else self._get_mock_z2h_certifications()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get Z2H certifications: {e}")
            return self._get_mock_z2h_certifications()

    def render_streamlit(self) -> None:
        """渲染Streamlit界面"""
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available")
            return

        st.title("🧬 进化工厂 (Evolution)")
        st.caption("因子挖掘 · Arena测试 · Z2H认证 · 策略进化")

        tab1, tab2, tab3, tab4 = st.tabs(["⛏️ 因子挖掘", "🏟️ Arena测试", "🏆 Z2H认证", "📈 进化历史"])

        with tab1:
            self._render_mining_status()

        with tab2:
            self._render_arena_results()

        with tab3:
            self._render_z2h_certifications()

        with tab4:
            self._render_evolution_history()

    def _render_mining_status(self) -> None:
        """渲染因子挖掘状态"""
        st.subheader("⛏️ 20个因子挖掘器状态")

        statuses = self.get_mining_status()

        # 统计概览
        col1, col2, col3, col4 = st.columns(4)
        running = sum(1 for s in statuses if s.status == "running")
        total_factors = sum(s.factors_discovered for s in statuses)
        validated = sum(s.factors_validated for s in statuses)
        avg_fitness = sum(s.best_fitness for s in statuses) / len(statuses) if statuses else 0

        with col1:
            st.metric("运行中", f"{running}/{len(statuses)}")
        with col2:
            st.metric("发现因子", total_factors)
        with col3:
            st.metric("已验证", validated)
        with col4:
            st.metric("平均适应度", f"{avg_fitness:.2f}")

        st.divider()

        # 挖掘器列表
        for status in statuses:
            with st.expander(f"🔧 {status.miner_name}", expanded=status.status == "running"):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    status_color = (
                        self.COLOR_SCHEME["success"] if status.status == "running" else self.COLOR_SCHEME["neutral"]
                    )
                    st.markdown(f"<span style='color:{status_color}'>● {status.status}</span>", unsafe_allow_html=True)

                with col2:
                    st.metric("发现/验证", f"{status.factors_discovered}/{status.factors_validated}")

                with col3:
                    st.metric("当前代数", status.current_generation)

                with col4:
                    st.metric("最佳适应度", f"{status.best_fitness:.3f}")

                if status.status == "running":
                    st.progress(min(status.current_generation / 100, 1.0))

    def _render_arena_results(self) -> None:
        """渲染Arena测试结果"""
        st.subheader("🏟️ Arena三轨测试结果")

        results = self.get_arena_results(20)

        # 统计
        passed = sum(1 for r in results if r.passed)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("测试总数", len(results))
        with col2:
            st.metric("通过数", passed)
        with col3:
            pass_rate = (passed / len(results) * 100) if results else 0
            st.metric("通过率", f"{pass_rate:.1f}%")

        st.divider()

        for result in results:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

                with col1:
                    st.markdown(f"**{result.factor_id}**")
                    st.caption(
                        result.factor_expression[:50] + "..."
                        if len(result.factor_expression) > 50
                        else result.factor_expression
                    )

                with col2:
                    st.metric("Reality", f"{result.reality_track_score:.2f}")

                with col3:
                    st.metric("Hell", f"{result.hell_track_score:.2f}")

                with col4:
                    st.metric("Cross-Market", f"{result.cross_market_score:.2f}")

                with col5:
                    if result.passed:
                        st.success(f"✅ {result.overall_score:.2f}")
                    else:
                        st.error(f"❌ {result.overall_score:.2f}")

                st.divider()

    def _render_z2h_certifications(self) -> None:
        """渲染Z2H认证状态"""
        st.subheader("🏆 Z2H基因胶囊认证")

        certs = self.get_z2h_certifications()

        # 按级别统计
        level_counts = {}
        for cert in certs:
            level = cert.certification_level.value
            level_counts[level] = level_counts.get(level, 0) + 1

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🥇 铂金", level_counts.get("铂金", 0))
        with col2:
            st.metric("🥈 金牌", level_counts.get("金牌", 0))
        with col3:
            st.metric("🥉 银牌", level_counts.get("银牌", 0))
        with col4:
            st.metric("⏳ 待认证", level_counts.get("待认证", 0))

        st.divider()

        for cert in certs:
            level_color = {  # pylint: disable=unused-variable
                CertificationLevel.PLATINUM: self.COLOR_SCHEME["platinum"],
                CertificationLevel.GOLD: self.COLOR_SCHEME["gold"],
                CertificationLevel.SILVER: self.COLOR_SCHEME["silver"],
                CertificationLevel.PENDING: self.COLOR_SCHEME["neutral"],
            }.get(cert.certification_level, self.COLOR_SCHEME["neutral"])

            with st.expander(f"📜 {cert.strategy_name} - {cert.certification_level.value}"):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Arena评分", f"{cert.arena_score:.2f}")

                with col2:
                    color = self.COLOR_SCHEME["rise"] if cert.simulation_return > 0 else self.COLOR_SCHEME["fall"]
                    st.markdown(
                        f"模拟收益: <span style='color:{color}'>{cert.simulation_return:.2%}</span>",
                        unsafe_allow_html=True,
                    )

                with col3:
                    st.metric("夏普比率", f"{cert.simulation_sharpe:.2f}")

                with col4:
                    st.metric("最大回撤", f"{cert.simulation_max_drawdown:.2%}")

                if cert.certification_date:
                    st.caption(f"认证日期: {cert.certification_date.strftime('%Y-%m-%d')}")

    def _render_evolution_history(self) -> None:
        """渲染进化历史"""
        st.subheader("📈 策略进化历史")
        st.info("展示策略从因子发现到生产部署的完整进化路径")

        # 进化流程图
        st.markdown("""
        ```
        因子挖掘 → Arena测试 → 斯巴达考核 → 模拟盘验证 → Z2H认证 → 生产部署
           ⛏️         🏟️          ⚔️           📊          🏆         🚀
        ```
        """)

        # 模拟进化历史数据
        history_data = [
            {"date": "2026-01-27", "event": "GeneticMiner发现新因子F001", "phase": "因子挖掘"},
            {"date": "2026-01-26", "event": "因子F001通过Arena三轨测试", "phase": "Arena测试"},
            {"date": "2026-01-25", "event": "策略S001通过斯巴达考核", "phase": "斯巴达考核"},
            {"date": "2026-01-20", "event": "策略S001完成1月模拟盘验证", "phase": "模拟盘验证"},
            {"date": "2026-01-19", "event": "策略S001获得金牌Z2H认证", "phase": "Z2H认证"},
        ]

        for item in history_data:
            st.markdown(f"**{item['date']}** - {item['phase']}")
            st.caption(item["event"])
            st.divider()

    def _get_mock_mining_status(self) -> List[FactorMiningStatus]:
        """获取模拟挖掘状态"""
        import random  # pylint: disable=import-outside-toplevel

        statuses = []
        for i, name in enumerate(self.MINER_NAMES):  # pylint: disable=unused-variable
            statuses.append(
                FactorMiningStatus(
                    miner_name=name,
                    factors_discovered=random.randint(10, 100),
                    factors_validated=random.randint(5, 50),
                    current_generation=random.randint(1, 100),
                    best_fitness=random.uniform(0.5, 0.95),
                    status=random.choice(["running", "idle", "completed"]),
                    start_time=datetime.now(),
                    elapsed_time=random.uniform(100, 3600),
                )
            )
        return statuses

    def _get_mock_arena_results(self, limit: int) -> List[ArenaTestResult]:
        """获取模拟Arena结果"""
        import random  # pylint: disable=import-outside-toplevel

        results = []
        for i in range(limit):
            overall = random.uniform(0.3, 0.9)
            results.append(
                ArenaTestResult(
                    factor_id=f"F{i+1:04d}",
                    factor_expression=f"rank(close/delay(close,{random.randint(1,20)}))",
                    reality_track_score=random.uniform(0.4, 0.9),
                    hell_track_score=random.uniform(0.3, 0.8),
                    cross_market_score=random.uniform(0.4, 0.85),
                    overall_score=overall,
                    passed=overall > 0.6,
                    test_time=datetime.now(),
                )
            )
        return results

    def _get_mock_z2h_certifications(self) -> List[Z2HCertification]:
        """获取模拟Z2H认证"""
        return [
            Z2HCertification(
                "S001", "动量突破策略", CertificationLevel.GOLD, 0.85, 0.25, 2.1, 0.08, datetime.now(), None
            ),
            Z2HCertification(
                "S002", "均值回归策略", CertificationLevel.SILVER, 0.72, 0.18, 1.8, 0.12, datetime.now(), None
            ),
            Z2HCertification(
                "S003", "主力跟随策略", CertificationLevel.PLATINUM, 0.92, 0.35, 2.8, 0.05, datetime.now(), None
            ),
            Z2HCertification("S004", "事件驱动策略", CertificationLevel.PENDING, 0.55, 0.10, 1.2, 0.15, None, None),
        ]
